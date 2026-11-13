"""Direct-import tests for the week of Current tastes lists behind Today's picks."""
import unittest

from discovery import lens_week


def stored(day, *albums):
    return {"payload": {"day": day, "albums": [{"artist": a, "album": b} for a, b in albums]}, "generated_at": 1.0}


KEY = lambda text: text.strip().casefold()


class ArchiveTests(unittest.TestCase):
    def test_keeps_a_day_once_and_never_overwrites_it(self):
        db = {}
        read = lambda name: ({"payload": db[name]} if name in db else None)
        write = db.__setitem__
        self.assertEqual(lens_week.archive_current(stored("2026-11-10", ("A", "1")), read, write), "2026-11-10")
        self.assertIsNone(lens_week.archive_current(stored("2026-11-10", ("A", "1"), ("B", "2")), read, write))
        self.assertEqual(len(db["lens_week:current_tastes:2026-11-10"]["albums"]), 1)

    def test_skips_empty_malformed_and_undated_lists(self):
        write = lambda *_: self.fail("nothing should be written")
        for bad in (None, {}, {"payload": {"day": "2026-11-10", "albums": []}}, {"payload": {"day": "soon", "albums": [{}]}}):
            self.assertIsNone(lens_week.archive_current(bad, lambda _n: None, write))


class PoolTests(unittest.TestCase):
    def test_window_is_seven_days_newest_first(self):
        days = lens_week.week_days("2026-11-13")
        self.assertEqual((days[0], days[-1], len(days)), ("2026-11-13", "2026-11-07", 7))

    def test_pool_covers_the_week_dedupes_and_drops_owned_and_dismissed(self):
        db = {
            lens_week.archive_name("2026-11-12"): stored("2026-11-12", ("A", "1"), ("B", "2"))["payload"],
            lens_week.archive_name("2026-11-06"): stored("2026-11-06", ("Old", "Out of the week"))["payload"],
        }
        read = lambda name: ({"payload": db[name]} if name in db else None)
        live = stored("2026-11-13", (" a ", "1"), ("C", "3"), ("D", "4"), ("E", "5"))
        pool = lens_week.week_pool(
            "2026-11-13", live, read, KEY,
            is_owned=lambda a: a["artist"] == "D", is_dismissed=lambda a: a["artist"] == "E",
        )
        self.assertEqual([a["artist"] for a in pool], [" a ", "C", "B"])

    def test_picks_use_the_pick_shape_and_a_fresh_shuffle(self):
        pool = [{"artist": "A", "album": "1", "tags": ["x", "y"], "seed_tag": "x"}, {"artist": "B", "album": "2"}]
        out = lens_week.build_week_picks(pool, 1, lambda v: v.reverse())
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["pool_size"], 2)
        self.assertEqual(out["items"][0]["artist"], "B")
        self.assertEqual(out["items"][0]["dashboard_category"], "Current tastes")
        self.assertEqual(pool[0]["artist"], "A")  # the pool itself is not reordered


if __name__ == "__main__":
    unittest.main()
