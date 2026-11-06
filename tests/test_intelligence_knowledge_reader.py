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


class DossierTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.release = repo.upsert_entity(self.db, "release", "Kind of Blue", mbid="r-gid", owned=True)[0]
        self.group = repo.upsert_entity(self.db, "release_group", "Kind of Blue", mbid="g-gid")[0]
        self.rec = repo.upsert_entity(self.db, "recording", "So What", mbid="rec-gid")[0]
        self.miles = repo.upsert_entity(self.db, "artist", "Miles Davis", mbid="m-gid")[0]
        self.label = repo.upsert_entity(self.db, "label", "Columbia", mbid="l-gid")[0]
        common = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        repo.add_edge(self.db, self.release, self.group, "member_of", **{**common, "source": "musicbrainz"})
        repo.add_edge(self.db, self.rec, self.release, "appears_on", role="1/1", **{**common, "source": "musicbrainz"})
        repo.add_edge(self.db, self.miles, self.release, "producer", role="executive", **common)
        repo.add_edge(self.db, self.miles, self.rec, "instrument", role="trumpet", **common)
        repo.add_edge(self.db, self.label, self.release, "publisher", **common)
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_unknown_album_is_none(self):
        self.assertIsNone(self.reader.album_dossier(mbid="nope"))

    def test_dossier_groups_credits_labels_and_family(self):
        self.load_slice()
        d = self.reader.album_dossier(mbid="r-gid")
        self.assertEqual(d["release_group"]["canonical_name"], "Kind of Blue")
        self.assertEqual(d["release_family"]["count"], 1)
        self.assertEqual([t["title"] for t in d["tracks"]], ["So What"])
        self.assertEqual([p["entity"]["canonical_name"] for p in d["people"]], ["Miles Davis"])
        scopes = {(c["scope"], c["relation"], c["role"], c["track"]) for c in d["people"][0]["credits"]}
        self.assertEqual(scopes, {("album", "producer", "executive", None), ("recording", "instrument", "trumpet", "So What")})
        self.assertEqual(d["people"][0]["credits"][0]["source"], "musicbrainz_dump")
        self.assertEqual([l["entity"]["canonical_name"] for l in d["labels"]], ["Columbia"])
        self.assertEqual(d["sources"]["musicbrainz_dump"]["coverage"], "loaded")
        self.assertIn("catalogue_numbers", d["not_loaded"])

    def test_inferred_edge_is_never_a_credit(self):
        other = repo.upsert_entity(self.db, "artist", "Guess", mbid="x-gid")[0]
        repo.add_edge(self.db, other, self.release, "producer", evidence_class="inferred",
                      match_quality="fuzzy_confirmed", source="derived")
        names = [p["entity"]["canonical_name"] for p in self.reader.album_dossier(mbid="r-gid")["people"]]
        self.assertEqual(names, ["Miles Davis"])

    def test_pending_without_slice_and_group_dossier(self):
        self.assertEqual(self.reader.album_dossier(mbid="r-gid")["sources"]["musicbrainz_dump"]["coverage"], "pending")
        d = self.reader.album_dossier(type="release_group", mbid="g-gid")
        self.assertEqual(d["album"]["mbid"], "g-gid")
        self.assertEqual(d["tracks"], [])
        self.assertEqual(d["release_family"]["count"], 1)

    def test_wrong_type_is_refused(self):
        with self.assertRaises(ValueError):
            self.reader.album_dossier(type="artist", mbid="m-gid")


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
