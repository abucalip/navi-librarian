import sqlite3
import unittest

from intelligence.store import migrations


def v3_store():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    for migration in migrations.MIGRATIONS[:3]:
        migrations._apply(db, migration)
    return db


class Migration4Tests(unittest.TestCase):
    def setUp(self):
        self.db = v3_store()
        self.assertEqual(migrations.current_version(self.db), 3)
        for name in ("A", "B"):
            self.db.execute("INSERT INTO entities (type, mbid, canonical_name, owned) VALUES ('artist', ?, ?, 1)",
                            (name.lower(), name))
        self.db.execute("INSERT INTO entity_aliases (entity_id, alias) VALUES (1, 'Alpha')")
        obs = self.db.execute("INSERT INTO observations (source, payload_hash, payload, fetched_at) "
                              "VALUES ('x', 'h', '{}', 1)").lastrowid
        self.db.execute("INSERT INTO edges (from_id, to_id, relation, evidence_class, match_quality, source, "
                        "observation_id) VALUES (1, 2, 'member of band', 'source_explicit', 'exact_mbid', 'x', ?)",
                        (obs,))
        self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (1, '1970')")
        migrations.migrate(self.db)

    def test_rows_survive_the_rebuild(self):
        self.assertEqual(migrations.current_version(self.db), migrations.LATEST_VERSION)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT alias FROM entity_aliases").fetchone()[0], "Alpha")
        self.assertEqual(self.db.execute("SELECT date FROM release_facts").fetchone()[0], "1970")
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_foreign_keys_are_back_on_and_cascade_still_works(self):
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.db.execute("DELETE FROM entities WHERE id = 2")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0], 0)

    def test_event_type_is_allowed_and_junk_is_not(self):
        self.db.execute("INSERT INTO entities (type, canonical_name) VALUES ('event', 'Gig')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO entities (type, canonical_name) VALUES ('nonsense', 'X')")

    def test_indexes_are_back(self):
        names = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertTrue({"entities_mbid", "entities_navidrome", "entities_name"} <= names)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO entities (type, mbid, canonical_name) VALUES ('artist', 'a', 'dup')")

    def test_fresh_store_has_the_same_shape(self):
        fresh = sqlite3.connect(":memory:")
        fresh.row_factory = sqlite3.Row
        migrations.migrate(fresh)
        tables = lambda d: {r[0] for r in d.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables(fresh), tables(self.db))


if __name__ == "__main__":
    unittest.main()
