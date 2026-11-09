import tempfile
import unittest
from pathlib import Path

from intelligence.graph.album_gaps import MIN_PLAYED_ALBUMS, build_gaps_path
from intelligence.insights.forgotten_gems import PlayRecord
from intelligence.store import open_store
from intelligence.store import repositories as repo

DUMP = "musicbrainz_dump"


class GapsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = open_store(Path(self._tmp.name) / "a.sqlite3")
        self.n = 0

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def ent(self, kind, name, **kw):
        self.n += 1
        return repo.upsert_entity(self.db, kind, name, mbid=f"e0000000-0000-0000-0000-{self.n:012d}", **kw)[0]

    def edge(self, a, b, rel, *, ec="source_explicit", mq="exact_mbid", src=DUMP):
        return repo.add_edge(self.db, a, b, rel, source=src, evidence_class=ec, match_quality=mq)[0]

    def album(self, name, credit=True):
        """``credit=False``: no credited artist, so the artist paths reach nothing and overlap dropping is moot."""
        rel = self.ent("release", name, owned=True, navidrome_id=f"nd-{name}")
        if credit:
            artist = self.ent("artist", name + " Artist", owned=True)
            self.edge(rel, artist, "credited_to", ec="library_tag", src="navidrome")
        rec = self.ent("recording", f"{name}: T", owned=True)
        self.edge(rec, rel, "appears_on", ec="library_tag", src="navidrome")
        return rel, rec

    def rec(self, name, plays):
        return PlayRecord(key=f"album:nd-{name}", kind="album", title=name, play_count=plays)

    def history(self, **plays):
        """Enough played filler albums for usable history, plus the named albums' counts."""
        out = [PlayRecord(key=f"album:filler{i}", kind="album", title="f", play_count=5) for i in range(MIN_PLAYED_ALBUMS)]
        return out + [self.rec(n, c) for n, c in plays.items()]

    def setup_three(self):
        """A1 (start); A2 shares crew with it, A3 shares crew and a guest. A1 has no credited artist,
        so no stop is overlap-dropped."""
        a1, r1 = self.album("A1", credit=False)
        a2, r2 = self.album("A2")
        a3, r3 = self.album("A3")
        eng, prod, guest = (self.ent("person", n) for n in ("Engineer", "Producer", "Guest"))
        self.edge(eng, r1, "engineer")
        self.edge(eng, r2, "engineer")
        self.edge(prod, a1, "producer")
        self.edge(prod, a3, "producer")
        self.edge(guest, r1, "instrument")
        self.edge(guest, r3, "instrument")
        return a1, a2, a3

    def test_keeps_only_unplayed_or_barely_played_stops_with_their_credit_reasons(self):
        a1, a2, a3 = self.setup_three()
        r = build_gaps_path(self.db, a1, self.history(A2=0, A3=1))
        self.assertEqual(r["history"]["state"], "ok")
        self.assertEqual({s["entity"]["id"] for s in r["stops"]}, {a2, a3})
        by = {s["entity"]["id"]: s for s in r["stops"]}
        self.assertEqual(by[a2]["play"]["state"], "never")
        self.assertEqual(by[a3]["play"]["state"], "little")
        self.assertEqual({x["code"] for x in by[a3]["reasons"]}, {"crew_on", "guest_on"})
        self.assertTrue(all(x["code"] in ("crew_on", "guest_on") for s in r["stops"] for x in s["reasons"]))

    def test_a_played_album_is_filtered_out_and_counted(self):
        a1, a2, a3 = self.setup_three()
        r = build_gaps_path(self.db, a1, self.history(A2=0, A3=9))
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a2])
        self.assertEqual(r["history"]["filtered_out"], 1)

    def test_order_is_the_base_order_not_play_count(self):
        a1, a2, a3 = self.setup_three()
        r1 = build_gaps_path(self.db, a1, self.history(A2=1, A3=0))
        r2 = build_gaps_path(self.db, a1, self.history(A2=0, A3=1))
        self.assertEqual([s["entity"]["id"] for s in r1["stops"]], [s["entity"]["id"] for s in r2["stops"]])

    def test_never_adds_a_stop_the_base_paths_lack(self):
        a1, a2, a3 = self.setup_three()
        lone, _ = self.album("Lone", credit=False)   # unplayed but no credit link to the start
        r = build_gaps_path(self.db, a1, self.history(A2=0, A3=0, Lone=0))
        self.assertNotIn(lone, {s["entity"]["id"] for s in r["stops"]})

    def test_thin_history_returns_unfiltered_stops_marked_so(self):
        a1, a2, a3 = self.setup_three()
        r = build_gaps_path(self.db, a1, [self.rec("A2", 9), self.rec("A3", 9)])
        self.assertEqual(r["history"]["state"], "thin")
        self.assertEqual({s["entity"]["id"] for s in r["stops"]}, {a2, a3})
        self.assertTrue(all(s["play"] is None for s in r["stops"]))
        self.assertFalse(r["history"]["filtered"])

    def test_unavailable_history_returns_unfiltered_stops(self):
        a1, a2, a3 = self.setup_three()
        r = build_gaps_path(self.db, a1, None)
        self.assertEqual(r["history"]["state"], "unavailable")
        self.assertEqual(len(r["stops"]), 2)

    def test_an_album_with_no_play_record_is_unknown_not_unplayed(self):
        a1, a2, a3 = self.setup_three()
        r = build_gaps_path(self.db, a1, self.history(A2=0))   # no record for A3
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a2])
        self.assertEqual(r["history"]["unknown"], 1)

    def test_no_stops_at_all_is_empty_and_unknown_start_is_none(self):
        a1, _ = self.album("Solo", credit=False)
        self.assertEqual(build_gaps_path(self.db, a1, self.history())["status"], "empty")
        self.assertIsNone(build_gaps_path(self.db, 99999, self.history()))


if __name__ == "__main__":
    unittest.main()
