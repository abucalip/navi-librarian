import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from intelligence.store import LATEST_VERSION, MigrationError, connect, current_version, migrate, open_store
from intelligence.store import migrations

TABLES = {
    "observations", "entities", "entity_aliases", "edges", "unresolved",
    "insights", "snapshots", "job_runs", "meta",
}


def _tables(db):
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "intelligence.sqlite3"
        self.db = open_store(self.path)
        self.addCleanup(self.db.close)

    def entity(self, name="A", type_="artist", **kw):
        cols = {"type": type_, "canonical_name": name, **kw}
        cur = self.db.execute(
            f"INSERT INTO entities ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            tuple(cols.values()),
        )
        return cur.lastrowid


class MigrationTests(StoreTestCase):
    def test_creates_all_tables_and_sets_version(self):
        self.assertTrue(TABLES <= _tables(self.db))
        self.assertEqual(current_version(self.db), LATEST_VERSION)

    def test_migrate_is_idempotent(self):
        self.entity("Keep")
        self.assertEqual(migrate(self.db), LATEST_VERSION)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 1)

    def test_reopen_preserves_data(self):
        self.entity("Keep")
        self.db.commit()
        self.db.close()
        again = open_store(self.path)
        self.addCleanup(again.close)
        self.assertEqual(again.execute("SELECT canonical_name FROM entities").fetchone()[0], "Keep")

    def test_newer_database_is_refused(self):
        self.db.execute(f"PRAGMA user_version = {LATEST_VERSION + 1}")
        with self.assertRaises(MigrationError):
            migrate(self.db)

    def test_failed_migration_rolls_back_and_keeps_version(self):
        bad = migrations.Migration(
            LATEST_VERSION + 1, "bad", ("CREATE TABLE half (x)", "INSERT INTO missing VALUES (1)")
        )
        with mock.patch.object(migrations, "MIGRATIONS", migrations.MIGRATIONS + (bad,)), \
                mock.patch.object(migrations, "LATEST_VERSION", bad.version):
            with self.assertRaises(MigrationError):
                migrate(self.db)
        self.assertEqual(current_version(self.db), LATEST_VERSION)
        self.assertNotIn("half", _tables(self.db))

    def test_open_store_closes_connection_on_failure(self):
        other = Path(self.temp_dir.name) / "new.sqlite3"
        with mock.patch("intelligence.store.db.migrate", side_effect=MigrationError("x")):
            with self.assertRaises(MigrationError):
                open_store(other)

    def test_versions_are_contiguous(self):
        self.assertEqual([m.version for m in migrations.MIGRATIONS], list(range(1, LATEST_VERSION + 1)))

    def test_connection_conventions(self):
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        fresh = connect(":memory:")
        self.addCleanup(fresh.close)
        self.assertEqual(current_version(fresh), 0)


class SchemaRuleTests(StoreTestCase):
    def test_observations_are_append_only(self):
        self.db.execute(
            "INSERT INTO observations (source, payload_hash, payload, fetched_at) VALUES ('mb','h','{}',1)"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE observations SET payload='{\"x\":1}'")

    def test_identical_document_is_stored_once_per_source(self):
        sql = "INSERT INTO observations (source, payload_hash, payload, fetched_at) VALUES (?,?,?,1)"
        self.db.execute(sql, ("mb", "h", "{}"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(sql, ("mb", "h", "{}"))
        self.db.execute(sql, ("lb", "h", "{}"))

    def test_entity_type_is_constrained(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.entity(type_="album")

    def test_mbid_is_unique_per_type_but_null_is_free(self):
        self.entity("A", mbid="m1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.entity("B", mbid="m1")
        self.entity("C", type_="release", mbid="m1")
        self.entity("D")
        self.entity("E")

    def _edge(self, a, b, **kw):
        row = {
            "from_id": a, "to_id": b, "relation": "member_of", "evidence_class": "source_explicit",
            "match_quality": "exact_mbid", "source": "mb", **kw,
        }
        self.db.execute(
            f"INSERT INTO edges ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values())
        )

    def test_edge_evidence_and_quality_are_constrained(self):
        a, b = self.entity("A"), self.entity("B", type_="group")
        with self.assertRaises(sqlite3.IntegrityError):
            self._edge(a, b, evidence_class="guess")
        with self.assertRaises(sqlite3.IntegrityError):
            self._edge(a, b, match_quality="0.93")

    def test_duplicate_edge_rejected_including_null_role(self):
        a, b = self.entity("A"), self.entity("B", type_="group")
        self._edge(a, b)
        with self.assertRaises(sqlite3.IntegrityError):
            self._edge(a, b)
        self._edge(a, b, role="drums")
        self._edge(a, b, generation=2)

    def test_edge_needs_existing_entities(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self._edge(1, 2)

    def test_deleting_entity_cascades_edges_and_aliases(self):
        a, b = self.entity("A"), self.entity("B", type_="group")
        self._edge(a, b)
        self.db.execute("INSERT INTO entity_aliases (entity_id, alias) VALUES (?, 'a')", (a,))
        self.db.execute("DELETE FROM entities WHERE id = ?", (a,))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entity_aliases").fetchone()[0], 0)

    def test_unresolved_status_and_uniqueness(self):
        sql = "INSERT INTO unresolved (kind, navidrome_ref, reason, first_seen, status) VALUES (?,?,?,1,?)"
        self.db.execute(sql, ("album", "n1", "ambiguous", "open"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(sql, ("album", "n1", "ambiguous", "open"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(sql, ("album", "n2", "ambiguous", "accepted"))

    def test_one_active_job_per_scope_but_history_is_free(self):
        sql = "INSERT INTO job_runs (job, entity_scope, state) VALUES (?,?,?)"
        self.db.execute(sql, ("health", "", "running"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(sql, ("health", "", "queued"))
        self.db.execute(sql, ("health", "artist:1", "running"))
        self.db.execute("UPDATE job_runs SET state='succeeded' WHERE job='health' AND entity_scope=''")
        self.db.execute(sql, ("health", "", "queued"))
        self.db.execute(sql, ("health", "", "failed"))

    def test_generation_starts_at_one(self):
        self.assertEqual(self.db.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0], "1")


if __name__ == "__main__":
    unittest.main()
