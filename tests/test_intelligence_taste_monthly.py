import copy
import unittest
from datetime import datetime, timezone

from intelligence.taste import ArtistListen, Listen, ProfileConfig
from intelligence.taste.monthly import build_monthly_snapshot, month_bounds

UTC = timezone.utc


def at(y, mo, d, h=0, mi=0, s=0, tz=UTC):
    return datetime(y, mo, d, h, mi, s, tzinfo=tz).timestamp()


def L(ts, **attrs):
    return Listen(ts, {k: tuple(v) for k, v in attrs.items()})


def cfg(**kw):
    kw.setdefault("min_listens", 4)
    kw.setdefault("min_attributed", 3)
    return ProfileConfig(**kw)


def month_of(listens, y=2026, mo=1, tz="UTC", **kw):
    return build_monthly_snapshot(listens, y, mo, tz, profile_config=kw.pop("config", cfg()), **kw)


class MonthBoundaryTests(unittest.TestCase):
    def test_utc_month_is_first_midnight_to_next_first_midnight(self):
        b = month_bounds(2026, 2, "UTC")
        self.assertEqual((b.start, b.end), (at(2026, 2, 1), at(2026, 3, 1)))

    def test_start_inclusive_end_exclusive(self):
        ls = [L(at(2026, 1, 1) - 1, genre=["a"]), L(at(2026, 1, 1), genre=["b"]),
              L(at(2026, 2, 1) - 1, genre=["c"]), L(at(2026, 2, 1), genre=["d"])]
        s = month_of(ls, 2026, 1)
        self.assertEqual(s.listens, 2)
        self.assertEqual({e.value for e in s.profile.dimensions["genre"]}, {"b", "c"})

    def test_december_to_january_transition(self):
        dec, jan = month_bounds(2026, 12), month_bounds(2027, 1)
        self.assertEqual(dec.end, jan.start)
        ls = [L(at(2026, 12, 31, 23, 59, 59), genre=["late-dec"]), L(at(2027, 1, 1), genre=["new-year"])]
        self.assertEqual(month_of(ls, 2026, 12).listens, 1)
        self.assertEqual(month_of(ls, 2027, 1).listens, 1)
        self.assertEqual(
            [e.value for e in month_of(ls, 2027, 1).profile.dimensions["genre"]], ["new-year"])

    def test_leap_february_length(self):
        b = month_bounds(2028, 2, "UTC")
        self.assertEqual((b.end - b.start) / 86400, 29)

    def test_timezone_moves_the_boundary(self):
        # 2026-03-01 00:00 New York is 05:00 UTC; 04:59:59 UTC is still Feb 28 local.
        ls = [L(at(2026, 3, 1, 4, 59, 59), genre=["before"]), L(at(2026, 3, 1, 5), genre=["inside"])]
        self.assertEqual(month_of(ls, 2026, 3, "America/New_York").listens, 1)
        self.assertEqual(month_of(ls, 2026, 2, "America/New_York").listens, 1)
        self.assertEqual(month_of(ls, 2026, 3, "UTC").listens, 2)

    def test_dst_month_is_one_hour_shorter(self):
        # March 2026 in New York has a spring-forward change: 31 days minus one hour.
        b = month_bounds(2026, 3, "America/New_York")
        self.assertEqual(b.start, at(2026, 3, 1, 5))  # midnight EST is 05:00 UTC
        self.assertEqual((b.end - b.start) / 3600, 31 * 24 - 1)

    def test_midnight_that_does_not_exist_still_starts_the_month(self):
        # Asuncion switched to DST at 00:00 on 1 Oct 2023 (local midnight does not exist).
        b = month_bounds(2023, 10, "America/Asuncion")
        self.assertEqual(b.start, at(2023, 10, 1, 4))  # 01:00 -03 is the same instant as 04:00 UTC
        ls = [L(at(2023, 10, 1, 3, 30), genre=["sep-30-local"]), L(at(2023, 10, 1, 4), genre=["oct"])]
        self.assertEqual(month_of(ls, 2023, 10, "America/Asuncion").listens, 1)

    def test_invalid_inputs_are_refused(self):
        for args in [(2026, 0), (2026, 13), (2026, True), (0, 1), (9999, 1), ("2026", 1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                month_bounds(*args)
        with self.assertRaises(ValueError):
            month_bounds(2026, 1, "Not/AZone")


class SnapshotTests(unittest.TestCase):
    def test_empty_month_is_low_sample_with_no_values(self):
        ls = [L(at(2025, 6, 1), genre=["jazz"])] * 10
        s = month_of(ls, 2026, 1)
        self.assertEqual(s.listens, 0)
        self.assertTrue(s.profile.low_sample)
        self.assertEqual(s.profile.attributed, {d: 0 for d in s.profile.attributed})
        self.assertTrue(all(v == () for v in s.profile.dimensions.values()))
        self.assertTrue(all(s.profile.dimension_low_sample.values()))

    def test_empty_input_is_empty_snapshot(self):
        s = month_of([], 2026, 1)
        self.assertEqual((s.listens, s.profile.low_sample), (0, True))

    def test_sparse_month_is_listed_but_flagged(self):
        ls = [L(at(2026, 1, d), genre=["jazz"]) for d in (1, 2, 3)]
        s = month_of(ls, 2026, 1)
        self.assertTrue(s.profile.low_sample)
        self.assertEqual(s.profile.dimensions["genre"][0].value, "jazz")
        self.assertEqual(s.profile.dimensions["genre"][0].count, 3)

    def test_missing_dimensions_are_low_sample_not_zero(self):
        ls = [L(at(2026, 1, d), genre=["rock"]) for d in range(1, 7)]
        s = month_of(ls, 2026, 1)
        self.assertFalse(s.profile.dimension_low_sample["genre"])
        self.assertTrue(s.profile.dimension_low_sample["label"])
        self.assertEqual(s.profile.dimensions["label"], ())
        self.assertEqual(s.profile.attributed["label"], 0)

    def test_values_are_not_truncated(self):
        ls = [L(at(2026, 1, 1), genre=[f"g{i:02d}"]) for i in range(15)]
        self.assertEqual(len(month_of(ls, 2026, 1).profile.dimensions["genre"]), 15)

    def test_shares_split_multi_value_listens(self):
        ls = [L(at(2026, 1, d), genre=["rock", "pop"]) for d in range(1, 5)]
        shares = {e.value: e.share for e in month_of(ls, 2026, 1).profile.dimensions["genre"]}
        self.assertEqual(shares, {"pop": 0.5, "rock": 0.5})

    def test_deterministic_for_identical_input_in_any_order(self):
        ls = [L(at(2026, 1, 1) + i * 3600, genre=["a", "b", "c"][: 1 + i % 3],
                era=["1970s"] if i % 2 else ["1980s", "1990s"]) for i in range(60)]
        first = month_of(ls, 2026, 1)
        self.assertEqual(first, month_of(list(reversed(ls)), 2026, 1))
        self.assertEqual(first, month_of(ls[::-1][::2] + ls[::-1][1::2], 2026, 1))

    def test_materially_different_months_give_different_snapshots(self):
        jan = [L(at(2026, 1, 1 + i % 28), genre=["jazz"]) for i in range(20)]
        feb = [L(at(2026, 2, 1 + i % 28), genre=["metal"]) for i in range(20)]
        a, b = month_of(jan + feb, 2026, 1), month_of(jan + feb, 2026, 2)
        self.assertNotEqual(a, b)
        self.assertEqual([e.value for e in a.profile.dimensions["genre"]], ["jazz"])
        self.assertEqual([e.value for e in b.profile.dimensions["genre"]], ["metal"])

    def test_snapshot_does_not_depend_on_later_listens_or_library_changes(self):
        ls = [L(at(2026, 1, 1 + i % 20), genre=["jazz"], area=["Chicago"]) for i in range(10)]
        before = month_of(ls, 2026, 1)
        later = ls + [L(at(2026, 6, 1), genre=["metal"], area=["Oslo"])] * 30
        self.assertEqual(before, month_of(later, 2026, 1))

    def test_later_mutation_of_source_objects_does_not_change_snapshot(self):
        attrs = {"genre": ("jazz",)}
        ls = [Listen(at(2026, 1, 1 + i), attrs) for i in range(5)]
        before = month_of(ls, 2026, 1)
        attrs["genre"] = ("metal",)  # the library/source changes after the snapshot was built
        self.assertEqual([e.value for e in before.profile.dimensions["genre"]], ["jazz"])

    def test_input_is_not_mutated(self):
        ls = [L(at(2026, 1, 1 + i), genre=["b", "a"], era=["1990s"]) for i in range(5)]
        ab = [ArtistListen(at(2026, 1, 2), "artist-1"), ArtistListen(at(2026, 1, 3), None)]
        pop = {"artist-1": 5000}
        snapshot_inputs = (copy.deepcopy(ls), copy.deepcopy(ab), copy.deepcopy(pop))
        build_monthly_snapshot(ls, 2026, 1, "UTC", artist_listens=ab, popularity=pop, profile_config=cfg())
        self.assertEqual((ls, ab, pop), snapshot_inputs)

    def test_profile_config_thresholds_are_honoured(self):
        ls = [L(at(2026, 1, 1), genre=["x"])] * 2
        self.assertTrue(month_of(ls, 2026, 1, config=ProfileConfig(min_listens=3)).profile.low_sample)
        self.assertFalse(month_of(ls, 2026, 1, config=ProfileConfig(min_listens=2, min_attributed=2)).profile.low_sample)

    def test_listens_outside_the_month_do_not_count_toward_attribution(self):
        ls = [L(at(2025, 12, 31), genre=["old"])] * 50 + [L(at(2026, 1, 5), label=["Lab"])] * 3
        s = month_of(ls, 2026, 1)
        self.assertEqual(s.listens, 3)
        self.assertEqual(s.profile.attributed["genre"], 0)
        self.assertEqual(s.profile.attributed["label"], 3)


class ObscurityPartTests(unittest.TestCase):
    POP = {"big": 5_000_000, "tiny": 100}

    def test_not_supplied_when_no_popularity(self):
        self.assertIsNone(month_of([L(at(2026, 1, 1), genre=["x"])], 2026, 1).obscurity)

    def test_buckets_and_unknown_artists_are_not_obscure(self):
        arts = [ArtistListen(at(2026, 1, 1 + i), "tiny") for i in range(4)] + \
               [ArtistListen(at(2026, 1, 9), "big"), ArtistListen(at(2026, 1, 10), "ghost")]
        s = build_monthly_snapshot([], 2026, 1, artist_listens=arts, popularity=self.POP,
                                   profile_config=cfg(min_listens=1))
        w = s.obscurity
        self.assertEqual((w.listens, w.known, w.unknown), (6, 5, 1))
        self.assertAlmostEqual(w.shares["obscure"], 4 / 5)

    def test_artist_listens_outside_the_month_are_excluded(self):
        arts = [ArtistListen(at(2025, 12, 31), "tiny"), ArtistListen(at(2026, 2, 1), "tiny")]
        s = build_monthly_snapshot([], 2026, 1, artist_listens=arts, popularity=self.POP)
        self.assertEqual(s.obscurity.listens, 0)
        self.assertTrue(s.obscurity.low_sample)

    def test_empty_month_obscurity_is_low_sample(self):
        s = build_monthly_snapshot([], 2026, 1, artist_listens=[], popularity=self.POP)
        self.assertTrue(s.obscurity.low_sample)
        self.assertEqual(s.obscurity.known, 0)


if __name__ == "__main__":
    unittest.main()
