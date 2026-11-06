import unittest

from intelligence.taste import Listen, ProfileConfig, build_profiles

NOW = 1_800_000_000.0
DAY = 86400.0


def L(days, genre=("rock",), **kw):
    attrs = {"genre": tuple(genre)}
    attrs.update({k: tuple(v) for k, v in kw.items()})
    return Listen(NOW - days * DAY, attrs)


def cfg(**kw):
    kw.setdefault("min_listens", 4)
    kw.setdefault("min_attributed", 3)
    return ProfileConfig(now=NOW, **kw)


class ProfileTests(unittest.TestCase):
    def test_windows_split_by_age_and_future_listens_are_ignored(self):
        ls = [L(10), L(100), L(400), Listen(NOW + DAY, {"genre": ("rock",)})]
        p = build_profiles(ls, cfg())
        self.assertEqual([p.windows[w].listens for w in ("recent", "mid", "all_time")], [1, 2, 3])

    def test_sparse_window_is_low_sample_and_states_no_shift(self):
        ls = [L(10, ("jazz",)), L(20, ("jazz",))] + [L(500 + i) for i in range(10)]
        p = build_profiles(ls, cfg())
        self.assertTrue(p.windows["recent"].low_sample)
        self.assertEqual(p.shifts, ())
        self.assertEqual(p.windows["recent"].dimensions["genre"][0].value, "jazz")  # still listed

    def test_shift_stated_when_both_sides_sound(self):
        ls = [L(10 + i, ("jazz",)) for i in range(6)] + [L(500 + i, ("rock",)) for i in range(14)]
        p = build_profiles(ls, cfg())
        up = [s for s in p.shifts if s.window == "recent" and s.value == "jazz"]
        self.assertEqual(len(up), 1)
        self.assertEqual((up[0].direction, up[0].from_share, up[0].to_share), ("up", 0.3, 1.0))
        self.assertTrue(any(s.value == "rock" and s.direction == "down" for s in p.shifts))

    def test_small_change_is_not_a_shift(self):
        ls = [L(10 + i, ("rock",)) for i in range(5)] + [L(500 + i, ("rock",)) for i in range(5)]
        self.assertEqual(build_profiles(ls, cfg()).shifts, ())

    def test_multi_value_listen_splits_one_unit(self):
        p = build_profiles([L(1, ("rock", "pop"))] * 4, cfg())
        shares = {e.value: e.share for e in p.windows["all_time"].dimensions["genre"]}
        self.assertEqual(shares, {"pop": 0.5, "rock": 0.5})

    def test_missing_metadata_dimension_is_low_sample(self):
        p = build_profiles([L(1)] * 6, cfg())
        w = p.windows["all_time"]
        self.assertFalse(w.dimension_low_sample["genre"])
        self.assertTrue(w.dimension_low_sample["label"])
        self.assertEqual(w.dimensions["label"], ())

    def test_deterministic(self):
        ls = [L(i, ("a", "b")) for i in range(30)]
        self.assertEqual(build_profiles(ls, cfg()), build_profiles(reversed(ls), cfg()))


if __name__ == "__main__":
    unittest.main()
