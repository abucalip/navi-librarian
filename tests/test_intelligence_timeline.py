"""The artist timeline: dated albums and events, undated last, nothing placed without a stated date."""
import tempfile
import unittest
from pathlib import Path

from intelligence.knowledge import KnowledgeReader
from intelligence.store import open_store
from intelligence.store import repositories as repo


class TimelinePage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = open_store(Path(self.tmp.name) / "store.sqlite3")
        self.addCleanup(self.db.close)
        up = lambda *a, **k: repo.upsert_entity(self.db, *a, **k)[0]
        self.artist = up("artist", "Mulatu", mbid="a1")
        self.late = up("release_group", "Late LP", mbid="g1")
        self.early = up("release_group", "Early LP", mbid="g2", owned=True)
        self.nodate = up("release_group", "No Date", mbid="g3")
        self.ed_a, self.ed_b = up("release", "Late 2nd", mbid="e1"), up("release", "Late 1st", mbid="e2")
        self.ev = up("event", "Session", mbid="v1")
        self.ev_nodate = up("event", "Gig", mbid="v2")
        for g in (self.late, self.early, self.nodate):
            self.edge(self.artist, g, "main performer")
        self.edge(self.artist, self.ev, "main performer")
        self.edge(self.artist, self.ev_nodate, "main performer")
        self.edge(self.ed_a, self.late, REL)
        self.edge(self.ed_b, self.late, REL)
        with self.db:
            self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, '1974-05')", (self.ed_a,))
            self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, '1974')", (self.ed_b,))
            self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, '1966-03-02')", (self.early,))
            self.db.execute("INSERT INTO event_facts (entity_id, kind, begin_date) VALUES (?, 'concert', '1970-06')", (self.ev,))
            self.db.execute("INSERT INTO event_facts (entity_id, kind) VALUES (?, 'concert')", (self.ev_nodate,))

    def edge(self, a, b, relation):
        repo.add_edge(self.db, a, b, relation, evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")

    def page(self):
        return KnowledgeReader(self.db).timeline_page(mbid="a1")

    def test_dated_in_order_then_undated(self):
        page = self.page()
        self.assertEqual([i["entity"]["mbid"] for i in page["items"]], ["g2", "v1", "g1", "v2", "g3"])
        self.assertEqual(page["undated"], 2)
        self.assertEqual(page["items"][2]["date"], "1974")  # earliest edition date
        self.assertEqual(page["items"][1]["kind"], "event")

    def test_owned_flag_and_public_body(self):
        items = {i["entity"]["mbid"]: i for i in self.page()["items"]}
        self.assertTrue(items["g2"]["owned"])
        self.assertFalse(items["g1"]["owned"])
        self.assertNotIn("id", items["g1"]["entity"])
        self.assertEqual(items["g1"]["evidence"][0]["match_quality"], "exact_mbid")

    def test_release_type_comes_from_the_release_group_or_its_edition(self):
        with self.db:
            self.db.execute("INSERT INTO release_group_facts (entity_id, primary_type, secondary_types) VALUES (?, 'Album', '[]')", (self.early,))
            self.db.execute("INSERT INTO release_group_facts (entity_id, primary_type, secondary_types) VALUES (?, 'Album', '[\"Live\"]')", (self.late,))
        items = {i["entity"]["mbid"]: i for i in self.page()["items"]}
        self.assertEqual(items["g2"]["release_type"], {"primary": "Album", "secondary": []})
        self.assertEqual(items["g1"]["release_type"], {"primary": "Album", "secondary": ["Live"]})
        self.assertIsNone(items["g3"]["release_type"])
        self.assertIsNone(items["v1"].get("release_type"))

    def test_unknown_is_none_and_wrong_type_raises(self):
        self.assertIsNone(KnowledgeReader(self.db).timeline_page(mbid="nope"))
        with self.assertRaises(ValueError):
            KnowledgeReader(self.db).timeline_page(mbid="g1", type="release_group")


REL = "member_of"
if __name__ == "__main__":
    unittest.main()
