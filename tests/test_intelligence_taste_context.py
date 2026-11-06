import unittest
from datetime import datetime, timezone

from intelligence.taste import Listen, ProfileConfig, build_context_profiles
from intelligence.taste.context import day_type, time_of_day

UTC = timezone.utc


def at(y, mo, d, h=0, mi=0, tz=UTC):
    return datetime(y, mo, d, h, mi, tzinfo=tz).timestamp()


def L(ts, **attrs):
    return Listen(ts, {k: tuple(v) for k, v in attrs.items()})


CFG = ProfileConfig(min_listens=2, min_attributed=2)


class BucketTests(unittest.TestCase):
    def test_hour_boundaries(self):
        got = [time_of_day(h) for h in (0, 5, 6, 11, 12, 17, 18, 23)]
        self.assertEqual(got, ["night", "night", "morning", "morning", "afternoon", "afternoon", "evening", "evening"])

    def test_day_type(self):
        self.assertEqual([day_type(d) for d in range(7)], ["weekday"] * 5 + ["weekend"] * 2)


class ProfileTests(unittest.TestCase):
    def test_listens_land_in_one_context_per_lens(self):
        # 2026-01-03 is a Saturday, 2026-01-05 a Monday
        ls = [L(at(2026, 1, 3, 23, 59), genre=["a"]), L(at(2026, 1, 5, 6, 0), genre=["b"])]
        r = build_context_profiles(ls, config=CFG)
        tod, dt = r.lenses["time_of_day"], r.lenses["day_type"]
        self.assertEqual((tod["evening"].listens, tod["morning"].listens, tod["night"].listens), (1, 1, 0))
        self.assertEqual((dt["weekend"].listens, dt["weekday"].listens), (1, 1))
        self.assertEqual(sum(p.listens for p in tod.values()), r.listens)
        self.assertEqual(sum(p.listens for p in dt.values()), r.listens)

    def test_timezone_moves_the_context(self):
        ts = at(2026, 1, 5, 23, 30)  # Monday 23:30 UTC = Tuesday 08:30 in Tokyo (UTC+9)
        utc = build_context_profiles([L(ts)], "UTC", CFG).lenses["time_of_day"]
        tok = build_context_profiles([L(ts)], "Asia/Tokyo", CFG).lenses["time_of_day"]
        self.assertEqual(utc["evening"].listens, 1)
        self.assertEqual(tok["morning"].listens, 1)

    def test_weekend_follows_local_date(self):
        ts = at(2026, 1, 2, 20, 0)  # Friday 20:00 UTC = Saturday 09:00 in Sydney
        self.assertEqual(build_context_profiles([L(ts)], "UTC", CFG).lenses["day_type"]["weekday"].listens, 1)
        self.assertEqual(build_context_profiles([L(ts)], "Australia/Sydney", CFG).lenses["day_type"]["weekend"].listens, 1)

    def test_dst_uses_wall_clock(self):
        # 2026-03-08 US spring forward: 07:00 UTC is 03:00 EDT, still night
        ts = at(2026, 3, 8, 7, 0)
        self.assertEqual(build_context_profiles([L(ts)], "America/New_York", CFG).lenses["time_of_day"]["night"].listens, 1)

    def test_empty_contexts_present_and_low_sample(self):
        r = build_context_profiles([], config=CFG)
        self.assertEqual(r.listens, 0)
        self.assertEqual(set(r.lenses["time_of_day"]), {"night", "morning", "afternoon", "evening"})
        for lens in r.lenses.values():
            for p in lens.values():
                self.assertTrue(p.low_sample)
                self.assertEqual(p.listens, 0)

    def test_low_sample_flags_and_all_values_kept(self):
        ls = [L(at(2026, 1, 5, 9, i), genre=[f"g{i}"]) for i in range(12)] + [L(at(2026, 1, 5, 13), genre=["x"])]
        r = build_context_profiles(ls, config=CFG)
        morning, afternoon = r.lenses["time_of_day"]["morning"], r.lenses["time_of_day"]["afternoon"]
        self.assertFalse(morning.low_sample)
        self.assertEqual(len(morning.dimensions["genre"]), 12)   # no top-N cut
        self.assertTrue(afternoon.low_sample)
        self.assertTrue(afternoon.dimension_low_sample["genre"])

    def test_input_order_and_inputs_untouched(self):
        ls = [L(at(2026, 1, 5, 9, i), genre=["a", "b", "c"][: i % 3 + 1]) for i in range(9)]
        a = build_context_profiles(ls, config=CFG)
        b = build_context_profiles(list(reversed(ls)), config=CFG)
        self.assertEqual(a, b)
        self.assertEqual(len(ls), 9)

    def test_unknown_timezone_rejected(self):
        for bad in ("Mars/Base", "", None):
            with self.assertRaises(ValueError):
                build_context_profiles([], bad)

    def test_no_shift_or_weight_fields(self):
        r = build_context_profiles([], config=CFG)
        self.assertFalse(hasattr(r, "shifts"))


if __name__ == "__main__":
    unittest.main()
