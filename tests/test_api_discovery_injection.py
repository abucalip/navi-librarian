"""Direct-import regressions for discovery router service injection."""
import json
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_librarian
from app.api.discovery import router


class FakeLibrarian:
    def __init__(self):
        self.calls = []

    def recommend_new_music(self, *, count):
        self.calls.append(("recommend_new_music", count))
        return json.dumps({"items": [{"artist": "A", "album": "B"}]})

    def _discovery_is_album_candidate(self, item):
        return True

    def discovery_get_list(self, *, list_name, count):
        self.calls.append(("discovery_get_list", list_name, count))
        return json.dumps({"list": list_name, "items": []})

    def discovery_refresh_list(self, *, list_name, count):
        self.calls.append(("discovery_refresh_list", list_name, count))
        return json.dumps({"list": list_name, "count": count})

    def discovery_set_feedback(self, *, artist, album, action, metadata_json):
        self.calls.append(("discovery_set_feedback", artist, album, action, json.loads(metadata_json)))
        return json.dumps({"ok": True})


class DiscoveryDependencyInjectionTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeLibrarian()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_librarian] = lambda: self.fake
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def test_recommendations_use_injected_service_and_filter_candidates(self):
        response = self.client.get("/api/recommendations?count=7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": [{"artist": "A", "album": "B"}]})
        self.assertEqual(self.fake.calls, [("recommend_new_music", 7)])

    def test_discovery_list_uses_injected_service(self):
        response = self.client.get("/api/discovery/personal?count=12")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"list": "personal", "items": []})
        self.assertEqual(self.fake.calls, [("discovery_get_list", "personal", 12)])

    def test_refresh_and_feedback_use_injected_service(self):
        refreshed = self.client.post("/api/discovery/classics/refresh", json={"count": 8})
        feedback = self.client.post(
            "/api/discovery/feedback",
            json={"artist": " A ", "album": " B ", "action": "save", "metadata": {"source": "test"}},
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(feedback.status_code, 200)
        self.assertEqual(self.fake.calls, [
            ("discovery_refresh_list", "classics", 8),
            ("discovery_set_feedback", "A", "B", "save", {"source": "test"}),
        ])

    def test_validation_contract_is_preserved(self):
        self.assertEqual(self.client.get("/api/recommendations?count=0").status_code, 400)
        self.assertEqual(self.client.get("/api/discovery/unknown").status_code, 404)
        self.assertEqual(
            self.client.post("/api/discovery/feedback", json={"artist": "A"}).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
