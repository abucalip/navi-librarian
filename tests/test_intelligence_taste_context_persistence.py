"""Context persistence and the morning-vs-night contrast. Fake listens only, no network."""
import unittest

from intelligence.store import generations, open_store
from intelligence.taste import build_context_profiles
from intelligence.taste.context_persistence import (
    CONTRAST_MIN_LISTENS, build_contrast, load_saved_context, save_context_profiles)
from intelligence.taste.profiles import Listen, ProfileConfig

DAY = 86400
MORNING, NIGHT = 8 * 3600, 2 * 3600
CFG = ProfileConfig(min_listens=5, min_attributed=5)


def listens(hour_ts, n, genre):
    return [Listen(ts=hour_ts + i * DAY, attrs={"genre": (genre,)}) for i in range(n)]


class ContextPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.addCleanup(self.db.close)

    def test_nothing_saved_reads_as_none(self):
        self.assertIsNone(load_saved_context(self.db))

    def test_round_trip_and_unchanged_save_keeps_version(self):
        ctx = build_context_profiles(listens(MORNING, 6, "jazz"), config=CFG)
        self.assertTrue(save_context_profiles(self.db, ctx, CFG, now=1.0))
        version = generations.data_versions(self.db)["insights"]
        body = load_saved_context(self.db)
        self.assertEqual(body["lenses"]["time_of_day"]["morning"]["listens"], 6)
        self.assertEqual(body["lenses"]["time_of_day"]["night"]["listens"], 0)
        self.assertFalse(save_context_profiles(self.db, ctx, CFG, now=2.0))
        self.assertEqual(generations.data_versions(self.db)["insights"], version)

    def test_contrast_below_minimum_is_low_sample_with_no_entries(self):
        both = listens(MORNING, 60, "jazz") + listens(NIGHT, 60, "ambient")
        c = build_contrast(build_context_profiles(both, config=CFG), CFG)
        self.assertEqual((c["state"], c["entries"]), ("low_sample", []))

    def test_contrast_states_differing_shares(self):
        n = CONTRAST_MIN_LISTENS
        both = listens(MORNING, n, "jazz") + listens(NIGHT, n, "ambient")
        c = build_contrast(build_context_profiles(both, config=CFG), CFG)
        self.assertEqual(c["state"], "stated")
        self.assertEqual({e["value"] for e in c["entries"]}, {"jazz", "ambient"})

    def test_contrast_with_same_taste_is_no_difference(self):
        n = CONTRAST_MIN_LISTENS
        both = listens(MORNING, n, "jazz") + listens(NIGHT, n, "jazz")
        c = build_contrast(build_context_profiles(both, config=CFG), CFG)
        self.assertEqual((c["state"], c["entries"]), ("no_difference", []))


if __name__ == "__main__":
    unittest.main()
