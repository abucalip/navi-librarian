"""Listens per UTC day (redesign D2): builder, persistence and the taste body field. Fake listens only, no network."""
import unittest

from intelligence.api.taste import build_taste_body
from intelligence.store import generations, open_store
from intelligence.taste.listens_by_day import DAYS, build_listens_by_day, load_listens_by_day, save_listens_by_day
from intelligence.taste.profiles import Listen

DAY = 86400
NOW = 20_000 * DAY + 5 * 3600   # 05:00 UTC on day 20000; "today" is not counted


def at(day, hour=12):
    return Listen(ts=day * DAY + hour * 3600)


class BuilderTests(unittest.TestCase):
    def test_always_84_days_oldest_first_with_zero_days(self):
        series = build_listens_by_day([], NOW)
        self.assertEqual(len(series), DAYS)
        self.assertTrue(all(e["count"] == 0 for e in series))
        self.assertEqual(series[-1]["date"], "2024-10-03")   # day 19999, the day before today
        self.assertEqual([e["date"] for e in series], sorted(e["date"] for e in series))

    def test_counts_land_on_their_utc_day_and_today_is_excluded(self):
        listens = [at(19999, 0), at(19999, 23), at(19998), at(20000), at(20000 - DAYS), at(20000 - DAYS - 1)]
        series = build_listens_by_day(listens, NOW)
        self.assertEqual(series[-1]["count"], 2)        # both ends of the same UTC day
        self.assertEqual(series[-2]["count"], 1)
        self.assertEqual(series[0]["count"], 1)         # the oldest complete day is in
        self.assertEqual(sum(e["count"] for e in series), 4)   # today and the day before the span are out

    def test_midnight_boundary_belongs_to_the_new_day(self):
        series = build_listens_by_day([Listen(ts=19999 * DAY)], NOW)
        self.assertEqual(series[-1]["count"], 1)
        self.assertEqual(series[-2]["count"], 0)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.addCleanup(self.db.close)

    def test_taste_body_omits_the_field_until_saved(self):
        self.assertNotIn("listens_by_day", build_taste_body(self.db))
        self.assertIsNone(load_listens_by_day(self.db))

    def test_round_trip_and_unchanged_save_keeps_version(self):
        series = build_listens_by_day([at(19999), at(19999)], NOW)
        self.assertTrue(save_listens_by_day(self.db, series, now=1.0))
        version = generations.data_versions(self.db)["insights"]
        self.assertEqual(build_taste_body(self.db)["listens_by_day"], series)
        self.assertFalse(save_listens_by_day(self.db, series, now=2.0))
        self.assertEqual(generations.data_versions(self.db)["insights"], version)
        self.assertTrue(save_listens_by_day(self.db, build_listens_by_day([at(19998)], NOW), now=3.0))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM insights WHERE kind = 'taste_listens_by_day'").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
