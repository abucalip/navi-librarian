"""Neighbours by Ear composition (docs/ALBUM_PATHS_PROPOSAL.md, path 8): seeds, grouping, ranking, skips, bounds."""
import unittest

from intelligence.sonic.neighbours import album_neighbours, pick_seeds

NOT_ANALYSED = "Navidrome API error 0: AudioMuse-AI returned status 404"
PLUGIN_FAILED = "Navidrome API error 0: plugin call failed"


def track(i, album="al-X", artist="A", year=2000, title=None):
    return {"id": i, "title": title or f"T{i}", "artist": artist, "artistId": f"ar-{artist}", "album": album,
            "albumId": album, "year": year, "track": int(i[1:]) if i[1:].isdigit() else 0}


class Fake:
    def __init__(self, n=4):
        self.own = [track(f"s{i}", artist="Own") for i in range(1, n + 1)]
        self.matches = {}  # seed id -> list of (entry, similarity)
        self.fail = {}
        self.calls = []

    def api_call(self, method, **p):
        self.calls.append((method, p))
        f = self.fail.get(method)
        if isinstance(f, str):
            raise RuntimeError(f)
        if isinstance(f, dict) and p.get("id") in f:
            raise RuntimeError(f[p["id"]])
        if method == "getAlbum":
            return {"album": {"id": "own", "name": "Own LP", "artist": "Own", "year": 1999, "song": self.own}}
        if method == "getSong":
            return {"song": next(s for s in self.own if s["id"] == p["id"])}
        return {"sonicMatch": [{"entry": e, "similarity": s} for e, s in self.matches.get(p["id"], [])]}


class Neighbours(unittest.TestCase):
    def test_groups_and_ranks_by_distinct_seed_count(self):
        f = Fake()
        f.matches = {
            "s1": [(track("b1", "al-B", "B", 1990), 0.99), (track("c1", "al-C", "C", 1980), 0.5)],
            "s2": [(track("b2", "al-B", "B", 1990), 0.1), (track("b3", "al-B", "B", 1990), 0.1)],
            "s3": [(track("c2", "al-C", "C", 1980), 0.9)],
        }
        r = album_neighbours(f.api_call, "own")
        self.assertEqual(r["status"], "ok")
        # B: seeds s1,s2 (2); C: seeds s1,s3 (2); tie breaks by earlier year -> C first. b3 is the same seed s2.
        self.assertEqual([s["album_id"] for s in r["stops"]], ["al-C", "al-B"])
        self.assertEqual([s["match_count"] for s in r["stops"]], [2, 2])
        self.assertEqual(r["stops"][1]["reasons"][0]["code"], "sonic_neighbour")
        self.assertNotIn("similarity", str(r["stops"]))

    def test_similarity_never_orders_the_result(self):
        f = Fake()
        f.matches = {"s1": [(track("b1", "al-B", "B", 2001), 0.01)],
                     "s2": [(track("c1", "al-C", "C", 2001), 0.99)]}
        r = album_neighbours(f.api_call, "own")
        self.assertEqual([s["album_id"] for s in r["stops"]], ["al-B", "al-C"])  # tie: same year, id order

    def test_own_album_is_dropped(self):
        f = Fake()
        f.matches = {"s1": [(track("x", "own", "Own"), 0.9)]}
        self.assertEqual(album_neighbours(f.api_call, "own")["status"], "empty")

    def test_unanalysed_seed_is_skipped_reported_and_replaced(self):
        f = Fake(n=3)
        f.fail = {"getSonicSimilarTracks": {"s1": NOT_ANALYSED}}
        f.matches = {"s2": [(track("b1", "al-B", "B"), 0.9)]}
        r = album_neighbours(f.api_call, "own", max_seeds=2)
        self.assertEqual([s["navidrome_id"] for s in r["skipped"]], ["s1"])
        self.assertEqual(r["skipped"][0]["reason"], "no_analysis")
        self.assertEqual(len(r["seeds"]), 2)  # s1 did not count against the cap; spare s2 took its place

    def test_plugin_failure_is_unavailable(self):
        f = Fake()
        f.fail = {"getSonicSimilarTracks": PLUGIN_FAILED}
        self.assertEqual(album_neighbours(f.api_call, "own")["status"], "unavailable")

    def test_unknown_album(self):
        f = Fake()
        f.fail = {"getAlbum": "Navidrome API error 70: data not found"}
        self.assertEqual(album_neighbours(f.api_call, "nope")["status"], "not_found")

    def test_time_bound_truncates(self):
        f = Fake()
        f.matches = {"s1": [(track("b1", "al-B", "B"), 0.9)]}
        ticks = iter([0, 0, 99, 99, 99, 99, 99, 99, 99, 99])
        r = album_neighbours(f.api_call, "own", time_limit=1, clock=lambda: next(ticks))
        self.assertEqual(r["truncated"], "time")
        self.assertEqual(len(r["seeds"]), 1)

    def test_pick_seeds_even_with_first_and_last(self):
        ids = [f"t{i}" for i in range(20)]
        seeds = pick_seeds(ids, 8)
        self.assertEqual(seeds[0], "t0")
        self.assertIn("t19", seeds[:8])
        self.assertEqual(len(set(seeds)), 20)
        self.assertEqual(seeds, pick_seeds(ids, 8))
        self.assertEqual(pick_seeds(ids[:5], 8), ids[:5])

    def test_at_most_eight_seeds_called(self):
        f = Fake(n=20)
        album_neighbours(f.api_call, "own")
        self.assertEqual(len([c for c in f.calls if c[0] == "getSonicSimilarTracks"]), 8)


if __name__ == "__main__":
    unittest.main()
