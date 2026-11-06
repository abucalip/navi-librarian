import ast
import sqlite3
import tempfile
import unittest
from pathlib import Path

from intelligence import knowledge
from intelligence.graph import Limits
from intelligence.knowledge import KnowledgeReader, slice_status
from intelligence.store import open_store
from intelligence.store import repositories as repo
from intelligence.store.db import open_readonly


def add_edge(db, a, b, relation="producer", source="musicbrainz_dump", evidence="source_explicit", match="exact_mbid", role=None):
    repo.add_edge(db, a, b, relation, role=role, evidence_class=evidence, match_quality=match, source=source,
                  source_url=f"https://musicbrainz.org/artist/{a}")


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.alpha = repo.upsert_entity(self.db, "artist", "Alpha", mbid="a-gid", owned=True)[0]
        self.beta = repo.upsert_entity(self.db, "artist", "Beta", mbid="b-gid")[0]
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_entity_lookup_forms(self):
        self.assertEqual(self.reader.entity("artist", mbid="A-GID")["canonical_name"], "Alpha")
        self.assertEqual(self.reader.entity(id=self.beta)["canonical_name"], "Beta")
        self.assertIsNone(self.reader.entity("artist", mbid="nope"))
        with self.assertRaises(ValueError):
            self.reader.entity("artist")

    def test_profile_missing_entity_is_none(self):
        self.assertIsNone(self.reader.profile("artist", mbid="nope"))

    def test_profile_pending_without_a_slice(self):
        profile = self.reader.profile("artist", mbid="a-gid")
        self.assertEqual(profile["sources"]["musicbrainz_dump"]["coverage"], "pending")
        self.assertEqual(profile["relationships"], [])

    def test_profile_with_slice_but_no_relationships(self):
        self.load_slice()
        profile = self.reader.profile("artist", mbid="a-gid")
        self.assertEqual(profile["sources"]["musicbrainz_dump"]["coverage"], "no_relationships_in_slice")

    def test_profile_carries_provenance_and_credit_flag(self):
        self.load_slice()
        add_edge(self.db, self.beta, self.alpha, "producer", role="mix")
        gamma = repo.upsert_entity(self.db, "artist", "Gamma", mbid="g-gid")[0]
        add_edge(self.db, gamma, self.alpha, "collaboration", source="derived", evidence="inferred")
        profile = self.reader.profile("artist", mbid="a-gid")
        self.assertEqual(profile["sources"]["musicbrainz_dump"]["coverage"], "loaded")
        by_name = {h["entity"]["canonical_name"]: h for h in profile["relationships"]}
        self.assertTrue(by_name["Beta"]["credit"])
        self.assertEqual(by_name["Beta"]["evidence"][0]["source"], "musicbrainz_dump")
        self.assertEqual(by_name["Beta"]["evidence"][0]["role"], "mix")
        self.assertFalse(by_name["Gamma"]["credit"])  # inferred is never a credit

    def test_connections_are_bounded_and_credits_only(self):
        add_edge(self.db, self.beta, self.alpha)
        gamma = repo.upsert_entity(self.db, "artist", "Gamma", mbid="g-gid")[0]
        add_edge(self.db, gamma, self.alpha, evidence="inferred", source="derived")
        page = self.reader.connections(self.alpha, credits_only=True, limits=Limits(max_depth=1))
        self.assertEqual([h["entity"]["canonical_name"] for h in page["hops"]], ["Beta"])

    def test_slice_status(self):
        self.assertFalse(slice_status(self.db)["loaded"])
        self.load_slice()
        status = self.reader.slice_status()
        self.assertEqual((status["loaded"], status["dump_timestamp"], status["schema_sequence"], status["age_seconds"]),
                         (True, "2026-11-04", 31, 1000.0))


class ReadOnlyTests(unittest.TestCase):
    def test_readonly_connection_reads_both_files_and_refuses_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intelligence.sqlite3"
            db = open_store(path)
            repo.upsert_entity(db, "artist", "Alpha", mbid="a-gid")[0]
            db.close()
            ro = open_readonly(path)
            self.assertEqual(KnowledgeReader(ro).entity("artist", mbid="a-gid")["canonical_name"], "Alpha")
            self.assertEqual(ro.execute("SELECT COUNT(*) FROM state.card_decisions").fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                ro.execute("INSERT INTO meta (key, value) VALUES ('x', 'y')")
            with self.assertRaises(sqlite3.OperationalError):
                ro.execute("INSERT INTO state.card_decisions VALUES ('k', 'a', 'dismissed', '{}', 0)")
            ro.close()


class BoundaryTests(unittest.TestCase):
    FORBIDDEN = ("integrations", "requests", "httpx", "urllib", "http", "socket", "discovery", "app",
                 "navidrome_client", "navidrome_server", "acquisition", "recommendation")

    def test_knowledge_package_imports_no_provider_or_web_module(self):
        for path in Path(knowledge.__file__).parent.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""] if isinstance(node, ast.ImportFrom) and not node.level else [])
                for name in names:
                    self.assertNotIn(name.split(".")[0], self.FORBIDDEN, f"{path.name} imports {name}")


if __name__ == "__main__":
    unittest.main()
