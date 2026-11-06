import unittest

from intelligence.taste.obscurity import (
    ArtistListen, ObscurityConfig, artist_mbids, build_obscurity, bucket_of, popularity_from_response,
)

DAY = 86400.0
NOW = 1_000_000_000.0
POP = {"big": 5_000_000, "mid": 50_000, "tiny": 100, "none": None}


def listens(artist, n, start_days=0):
    return [ArtistListen(NOW - (start_days + i) * DAY, artist) for i in range(n)]


class ObscurityTests(unittest.TestCase):
    def cfg(self, **kw):
        return ObscurityConfig(now=NOW, **kw)

    def test_bucket_boundaries(self):
        c = self.cfg()
        self.assertEqual(
            [bucket_of(n, c) for n in (1_000_000, 999_999, 100_000, 10_000, 9_999, 0)],
            ["mainstream", "known", "known", "niche", "obscure", "obscure"])

    def test_unknown_listens_are_not_counted_as_obscure(self):
        p = build_obscurity(listens("none", 60) + listens("ghost", 10) + listens(None, 5), POP, self.cfg())
        w = p.windows["all_time"]
        self.assertEqual((w.listens, w.known, w.unknown, w.low_sample), (75, 0, 75, True))
        self.assertEqual(w.shares["obscure"], 0.0)
        self.assertIsNone(w.median_listens)

    def test_shares_and_median(self):
        p = build_obscurity(listens("big", 30) + listens("tiny", 30) + listens("none", 5), POP, self.cfg())
        w = p.windows["all_time"]
        self.assertFalse(w.low_sample)
        self.assertEqual(w.shares["mainstream"], 0.5)
        self.assertEqual(w.shares["obscure"], 0.5)
        self.assertEqual(w.unknown, 5)
        self.assertEqual(w.median_listens, round((100 + 5_000_000) / 2))

    def test_low_sample_window_states_no_shift(self):
        old = listens("big", 100, start_days=400)
        recent = listens("tiny", 10)          # below min_known
        p = build_obscurity(old + recent, POP, self.cfg())
        self.assertTrue(p.windows["recent"].low_sample)
        self.assertEqual(p.shifts, ())

    def test_shift_toward_obscure_is_stated(self):
        old = listens("big", 100, start_days=400)
        recent = listens("tiny", 60)
        p = build_obscurity(old + recent, POP, self.cfg())
        shifts = {(s.window, s.direction) for s in p.shifts}
        self.assertIn(("recent", "more_obscure"), shifts)

    def test_small_change_is_not_a_shift(self):
        base = listens("big", 100, start_days=400) + listens("tiny", 5, start_days=400)
        recent = listens("big", 58) + listens("tiny", 2)
        p = build_obscurity(base + recent, POP, self.cfg(min_shift=0.5))
        self.assertEqual(p.shifts, ())

    def test_future_listens_ignored(self):
        p = build_obscurity([ArtistListen(NOW + DAY, "big")] * 100, POP, self.cfg())
        self.assertEqual(p.windows["all_time"].listens, 0)

    def test_deterministic(self):
        data = listens("big", 40) + listens("tiny", 40)
        self.assertEqual(build_obscurity(data, POP, self.cfg()), build_obscurity(list(data), dict(POP), self.cfg()))

    def test_batch_helpers(self):
        self.assertEqual(artist_mbids(listens("a", 2) + listens(None, 1) + listens("b", 1) + listens("a", 1)), ["a", "b"])
        rows = [{"artist_mbid": "a", "total_listen_count": 7}, {"artist_mbid": "b", "total_listen_count": None},
                {"artist_mbid": "c", "total_listen_count": True}, {"nope": 1}, "junk"]
        self.assertEqual(popularity_from_response(rows), {"a": 7, "b": None, "c": None})
        self.assertEqual(popularity_from_response({"error": "x"}), {})


if __name__ == "__main__":
    unittest.main()
