import unittest

from intelligence.taste import Listen, ProfileConfig, build_headline, build_profiles

NOW = 1_800_000_000.0
DAY = 86400.0


def L(days, genre=("rock",), **kw):
    attrs = {"genre": tuple(genre)}
    attrs.update({k: tuple(v) for k, v in kw.items()})
    return Listen(NOW - days * DAY, attrs)


def head(listens, **kw):
    kw.setdefault("min_listens", 4)
    kw.setdefault("min_attributed", 3)
    return build_headline(build_profiles(listens, ProfileConfig(now=NOW, **kw)))


class HeadlineTests(unittest.TestCase):
    def test_pair_when_one_genre_rises_and_another_falls(self):
        h = head([L(10 + i, ("jazz",)) for i in range(6)] + [L(500 + i, ("rock",)) for i in range(14)])
        self.assertEqual(h.text, "More jazz, less rock lately.")
        self.assertEqual((h.kind, h.window), ("pair", "recent"))
        self.assertEqual([(s["value"], s["direction"]) for s in h.subjects], [("jazz", "up"), ("rock", "down")])

    def test_single_riser_and_single_faller(self):
        # A genre moves while the rest of the mass is spread thinly, so only one value passes min_shift.
        spread = [(f"g{i}",) for i in range(1, 10)]
        up = head([L(10 + i, ("jazz",)) for i in range(9)] + [L(10 + i, g) for i, g in enumerate(spread)]
                  + [L(500 + i, (f"g{i % 10}",)) for i in range(40)], min_shift=0.1)
        self.assertEqual((up.kind, up.text), ("up", "Leaning into jazz lately."))
        down = head([L(10 + i, g) for i, g in enumerate(spread * 2)]
                    + [L(500 + i, ("jazz",)) for i in range(20)] + [L(600 + i, g) for i, g in enumerate(spread)],
                    min_shift=0.1)
        self.assertEqual((down.kind, down.text), ("down", "Drifting from jazz lately."))

    def test_steady_when_window_sound_and_no_shift(self):
        h = head([L(10 + i) for i in range(5)] + [L(500 + i) for i in range(5)])
        self.assertEqual((h.text, h.kind, h.subjects), ("Your taste has held steady.", "steady", ()))

    def test_mid_window_used_when_recent_is_thin(self):
        ls = [L(10, ("jazz",))] + [L(150 + i, ("jazz",)) for i in range(8)] + [L(500 + i, ("rock",)) for i in range(12)]
        h = head(ls)
        self.assertEqual(h.window, "mid")
        self.assertEqual(h.text, "More jazz, less rock this past year.")

    def test_none_when_no_window_is_sound(self):
        self.assertIsNone(head([L(10), L(20)]))
        self.assertIsNone(head([]))
        # Recent and mid are empty-ish and the baseline is thin.
        self.assertIsNone(head([L(500 + i) for i in range(3)]))

    def test_genre_ranks_before_other_dimensions(self):
        ls = ([L(10 + i, ("rock",), era=("2020s",)) for i in range(6)]
              + [L(500 + i, ("rock",), era=("1970s",)) for i in range(14)])
        # Era moves a lot but genre does not move at all: the headline falls through to era.
        h = head(ls)
        self.assertEqual(h.subjects[0]["dimension"], "era")
        ls = ([L(10 + i, ("jazz",), era=("2020s",)) for i in range(6)]
              + [L(500 + i, ("rock",), era=("1970s",)) for i in range(14)])
        self.assertEqual(head(ls).subjects[0]["dimension"], "genre")

    def test_ties_broken_by_value_name_and_deterministic(self):
        ls = ([L(10 + i, ("zeta",)) for i in range(3)] + [L(20 + i, ("alpha",)) for i in range(3)]
              + [L(500 + i, ("rock",)) for i in range(14)])
        h = head(ls)
        self.assertEqual(h.subjects[0]["value"], "alpha")
        self.assertEqual(h, head(list(reversed(ls))))

    def test_as_dict_shape(self):
        d = head([L(10 + i) for i in range(5)] + [L(500 + i) for i in range(5)]).as_dict()
        self.assertEqual(set(d), {"text", "kind", "window", "subjects"})


if __name__ == "__main__":
    unittest.main()
