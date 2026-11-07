"""The atlas listing: places with stated coordinates, counted by firmly matched recordings."""
import tempfile
import unittest
from pathlib import Path

from intelligence.knowledge import KnowledgeReader
from intelligence.store import open_store
from intelligence.store import repositories as repo


class AtlasPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = open_store(Path(self.tmp.name) / "store.sqlite3")
        self.addCleanup(self.db.close)
        up = lambda *a, **k: repo.upsert_entity(self.db, *a, **k)[0]
        self.paris = up("place", "Paris Studio", mbid="p1")
        self.bare = up("place", "No Coordinates", mbid="p2")
        self.far = up("place", "Far Hall", mbid="p3")
        self.rec_owned = up("recording", "Owned take", mbid="r1")
        self.rec_other = up("recording", "Other take", mbid="r2")
        self.rec_fuzzy = up("recording", "Guess", mbid="r3")
        release = up("release", "Owned LP", mbid="rel1", owned=True)
        self.edge(self.rec_owned, release, "appears_on")
        with self.db:
            self.db.execute("INSERT INTO place_facts (entity_id, kind, latitude, longitude) VALUES (?, 'studio', 48.85, 2.41)", (self.paris,))
            self.db.execute("INSERT INTO place_facts (entity_id, kind, latitude, longitude) VALUES (?, 'venue', NULL, NULL)", (self.bare,))
            self.db.execute("INSERT INTO place_facts (entity_id, kind, latitude, longitude) VALUES (?, 'venue', -1.5, 36.8)", (self.far,))
        for rec in (self.rec_owned, self.rec_other):
            self.edge(self.paris, rec, "recorded at")
            self.edge(self.bare, rec, "recorded at")
        self.edge(self.far, self.rec_fuzzy, "recorded at", quality="fuzzy_unconfirmed")

    def edge(self, a, b, relation, quality="exact_mbid"):
        repo.add_edge(self.db, a, b, relation, evidence_class="source_explicit", match_quality=quality, source="musicbrainz_dump")

    def page(self, **kw):
        return KnowledgeReader(self.db).atlas_page(**kw)

    def test_only_places_with_both_coordinates_and_firm_recordings(self):
        places = self.page()["places"]
        self.assertEqual([p["entity"]["mbid"] for p in places], ["p1"])
        self.assertEqual((places[0]["recordings"], places[0]["owned_recordings"]), (2, 1))
        self.assertEqual((places[0]["latitude"], places[0]["longitude"]), (48.85, 2.41))

    def test_body_is_public_and_limit_truncates(self):
        page = self.page()
        self.assertNotIn("id", page["places"][0]["entity"])
        self.assertFalse(page["truncated"])
        self.assertEqual(page["sources"]["musicbrainz_dump"]["coverage"], "pending")
        up = repo.upsert_entity(self.db, "place", "Second", mbid="p4")[0]
        with self.db:
            self.db.execute("INSERT INTO place_facts (entity_id, kind, latitude, longitude) VALUES (?, 'venue', 1, 1)", (up,))
        self.edge(up, self.rec_other, "recorded at")
        page = self.page(limit=1)
        self.assertEqual(len(page["places"]), 1)
        self.assertTrue(page["truncated"])


if __name__ == "__main__":
    unittest.main()
