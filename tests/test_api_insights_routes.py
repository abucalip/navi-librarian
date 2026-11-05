"""Route tests for /api/insights (Server V2 Phase 3): body, enabling, dismiss, restore, accept."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.insights as routes
from app.api.dependencies import get_librarian
from intelligence.insights.series_completion import CARD_KIND as SERIES_KIND
from intelligence.store import open_store


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


def seed_card(db, kind, key, score=1.0):
    import json
    card = {"kind": kind, "title": key, "body": "", "subject": {"key": key, "type": "x", "title": key},
            "reasons": [], "actions": [{"kind": "dismiss"}], "dismissible": True, "score": score}
    with db:
        db.execute(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
            "VALUES (?, NULL, ?, '[]', 1, 0)", (kind, json.dumps(card)))


class InsightRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)
        self.db = open_store(Path(self.tmp.name) / routes.STORE_FILE)
        self.addCleanup(self.db.close)

    def lenses(self, env=""):
        with mock.patch.dict("os.environ", {routes.LENSES_ENV: env}):
            return self.client.get("/api/insights").json()["lenses"]

    def test_all_off_by_default_even_with_saved_cards(self):
        seed_card(self.db, SERIES_KIND, "s1")
        lenses = self.lenses()
        self.assertEqual(set(lenses), {"forgotten_gem", "blind_spot", "series_completion", "hidden_canon", "anniversary"})
        self.assertTrue(all(not l["enabled"] and l["cards"] == [] for l in lenses.values()))

    def test_enabled_lens_returns_cards(self):
        seed_card(self.db, SERIES_KIND, "s1")
        lens = self.lenses(SERIES_KIND)[SERIES_KIND]
        self.assertTrue(lens["enabled"])
        self.assertEqual([c["subject"]["key"] for c in lens["cards"]], ["s1"])

    def test_limit_validation(self):
        for bad in (0, 101):
            self.assertEqual(self.client.get("/api/insights", params={"limit": bad}).status_code, 400)

    def test_dismiss_restore_round_trip(self):
        seed_card(self.db, SERIES_KIND, "s1")
        path = f"/api/insights/{SERIES_KIND}"
        self.assertEqual(self.client.post(path + "/dismiss", json={"key": "s1"}).json(), {"changed": True})
        self.assertEqual(self.lenses(SERIES_KIND)[SERIES_KIND]["cards"], [])
        self.assertEqual(self.client.post(path + "/dismiss", json={"key": "s1"}).json(), {"changed": False})
        self.assertEqual(self.client.post(path + "/restore", json={"key": "s1"}).json(), {"changed": True})
        # Restore lifts the suppression; the card itself returns at the next refresh.
        self.assertEqual(self.client.post(path + "/restore", json={"key": "s1"}).json(), {"changed": False})
        self.assertEqual(self.client.post(path + "/dismiss", json={"key": "s1"}).json(), {"changed": True})

    def test_accept_then_unaccept_and_dismissed_cannot_be_accepted(self):
        seed_card(self.db, SERIES_KIND, "s1")
        path = f"/api/insights/{SERIES_KIND}"
        self.assertTrue(self.client.post(path + "/accept", json={"key": "s1"}).json()["changed"])
        self.assertFalse(self.client.post(path + "/accept", json={"key": "s1"}).json()["changed"])
        self.assertTrue(self.client.post(path + "/unaccept", json={"key": "s1"}).json()["changed"])
        self.client.post(path + "/dismiss", json={"key": "s1"})
        self.assertFalse(self.client.post(path + "/accept", json={"key": "s1"}).json()["changed"])

    def test_blind_spot_card_key_dismisses_the_live_card(self):
        from intelligence.insights.blind_spots import CARD_KIND as BLIND
        key = "blind_spot:artist:abc:studio"   # the form a saved card carries in subject.key
        seed_card(self.db, BLIND, key)
        path = f"/api/insights/{BLIND}"
        self.assertTrue(self.client.post(path + "/dismiss", json={"key": key}).json()["changed"])
        self.assertEqual(self.lenses(BLIND)[BLIND]["cards"], [])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM insights WHERE kind = ? AND dismissed_state = 'dismissed'", (BLIND,)).fetchone()[0], 1)
        self.assertTrue(self.client.post(path + "/restore", json={"key": key}).json()["changed"])

    def test_unknown_kind_and_bad_body(self):
        self.assertEqual(self.client.post("/api/insights/nope/dismiss", json={"key": "a"}).status_code, 404)
        self.assertEqual(self.client.post(f"/api/insights/{SERIES_KIND}/dismiss", json={}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
