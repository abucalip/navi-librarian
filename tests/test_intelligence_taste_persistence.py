import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.insights as routes
from app.api.dependencies import get_librarian
from intelligence.api import build_taste_body
from intelligence.insights import list_gem_cards
from intelligence.store import generations, open_store
from intelligence.taste import (
    Listen, ProfileConfig, build_headline, build_profiles, load_saved_profiles, save_profiles,
)
from intelligence.taste.loader import LoadResult
from intelligence.taste.persistence import CARD_KIND, profiles_payload

DAY = 86400.0


def profiles(n=60):
    listens = [Listen(1000.0 - i * DAY, {"area": ("Sweden",)}) for i in range(n)]
    return build_profiles(listens, ProfileConfig(now=1000.0))


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.addCleanup(self.db.close)

    def test_nothing_saved_reads_as_none(self):
        self.assertIsNone(load_saved_profiles(self.db))
        self.assertIsNone(build_taste_body(self.db)["profiles"])

    def test_round_trip_keeps_counts_and_low_sample_flags(self):
        load = LoadResult((), 70, 3, 7, {"area": 60, "genre": 0})
        self.assertTrue(save_profiles(self.db, profiles(), load, now=5.0))
        saved = load_saved_profiles(self.db)
        self.assertEqual(saved["computed_at"], 5.0)
        self.assertEqual(saved["load"], {"total": 70, "unusable": 3, "unmatched": 7,
                                         "attributed": {"area": 60, "genre": 0}})
        all_time = saved["windows"]["all_time"]
        self.assertEqual(all_time["listens"], 60)
        self.assertFalse(all_time["low_sample"])
        self.assertTrue(all_time["dimension_low_sample"]["genre"])
        self.assertEqual(all_time["dimensions"]["area"][0], {"value": "Sweden", "count": 60, "share": 1.0})

    def test_sparse_history_is_saved_as_low_sample_not_dropped(self):
        save_profiles(self.db, profiles(5), now=1.0)
        self.assertTrue(load_saved_profiles(self.db)["windows"]["all_time"]["low_sample"])

    def test_identical_save_writes_nothing_and_keeps_the_data_version(self):
        save_profiles(self.db, profiles(), now=1.0)
        before = generations.data_versions(self.db).get("insights", 0)
        self.assertFalse(save_profiles(self.db, profiles(), now=2.0))
        self.assertEqual(generations.data_versions(self.db).get("insights", 0), before)
        self.assertEqual(load_saved_profiles(self.db)["computed_at"], 1.0)

    def test_changed_save_replaces_the_single_row_and_bumps_the_version(self):
        save_profiles(self.db, profiles(60), now=1.0)
        before = generations.data_versions(self.db)["insights"]
        self.assertTrue(save_profiles(self.db, profiles(80), now=2.0))
        rows = self.db.execute("SELECT COUNT(*) FROM insights WHERE kind = ?", (CARD_KIND,)).fetchone()[0]
        self.assertEqual(rows, 1)
        self.assertEqual(generations.data_versions(self.db)["insights"], before + 1)

    def test_saved_body_carries_the_headline_or_null(self):
        # One area value over a sound window: no stated shift, so the headline is the steady sentence.
        save_profiles(self.db, profiles(60), now=1.0)
        self.assertEqual(load_saved_profiles(self.db)["headline"]["kind"], "steady")
        self.assertIsNone(profiles_payload(profiles(5))["headline"])  # nothing sound: null

    def test_headline_in_payload_matches_the_builder(self):
        listens = [Listen(1000.0 - i * DAY, {"genre": ("jazz",)}) for i in range(6)] + [
            Listen(1000.0 - (400 + i) * DAY, {"genre": ("rock",)}) for i in range(14)]
        built = build_profiles(listens, ProfileConfig(now=1000.0, min_listens=4, min_attributed=3))
        self.assertEqual(profiles_payload(built)["headline"], build_headline(built).as_dict())
        self.assertEqual(profiles_payload(built)["headline"]["text"], "More jazz, less rock lately.")

    def test_taste_row_is_not_a_lens_card(self):
        save_profiles(self.db, profiles(), now=1.0)
        self.assertEqual(list_gem_cards(self.db), [])


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class TasteRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)
        self.db = open_store(Path(self.tmp.name) / routes.STORE_FILE)
        self.addCleanup(self.db.close)

    def test_empty_store_answers_null_profiles(self):
        r = self.client.get("/api/insights/taste")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["profiles"])

    def test_saved_profiles_are_served(self):
        save_profiles(self.db, profiles(), now=1.0)
        body = self.client.get("/api/insights/taste").json()
        self.assertEqual(body["profiles"]["windows"]["all_time"]["listens"], 60)
        self.assertGreaterEqual(body["data_version"], 1)

    def test_read_failure_is_a_502(self):
        with mock.patch.object(routes, "build_taste_body", side_effect=RuntimeError("x")):
            self.assertEqual(self.client.get("/api/insights/taste").status_code, 502)

    def test_insights_list_route_is_unchanged(self):
        save_profiles(self.db, profiles(), now=1.0)
        self.assertNotIn("taste", self.client.get("/api/insights").json())


if __name__ == "__main__":
    unittest.main()
