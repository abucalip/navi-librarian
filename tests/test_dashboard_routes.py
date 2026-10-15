"""Direct-import regressions for dashboard and health route injection."""
import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dashboard import router
from app.api.dependencies import get_librarian


class FakeLibrarian:
    def __init__(self):
        self.calls = []
        self.health_error = None
        self.lists = {
            "personal": {"items": [{"artist": "Artist A", "album": "Album A"}]},
            "classics": {"items": [{"artist": "Artist B", "album": "Album B"}]},
            "artist_deep_dive": {"items": [{"artist": "Artist C", "album": "Album C"}]},
        }

    def api_call(self, method):
        self.calls.append(("api_call", method))
        if self.health_error:
            raise self.health_error
        return {"status": "pong"}

    def discovery_get_list(self, *, list_name, count):
        self.calls.append(("discovery_get_list", list_name, count))
        return json.dumps(self.lists[list_name])

    def _discovery_is_album_candidate(self, item):
        return item.get("album") != "Exclude"


class DashboardRoutesTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeLibrarian()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_librarian] = lambda: self.fake
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def test_router_preserves_health_and_dashboard_paths(self):
        actual = {
            (route.path, method)
            for route in router.routes
            for method in getattr(route, "methods", set())
        }
        self.assertEqual(actual, {
            ("/api/health", "GET"),
            ("/api/dashboard-picks", "GET"),
        })

    def test_health_uses_injected_service_and_preserves_response(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "ok", "service": "Navidrome", "message": "pong",
        })
        self.assertEqual(self.fake.calls, [("api_call", "ping")])

    def test_health_failure_is_sanitized(self):
        self.fake.health_error = RuntimeError("sensitive upstream error")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"],
                         "Navidrome is unavailable or authentication failed.")
        self.assertNotIn("sensitive", response.text)

    def test_dashboard_balances_categories_and_maps_service_calls(self):
        with patch("app.api.dashboard.random.shuffle", side_effect=lambda values: None):
            response = self.client.get("/api/dashboard-picks?count=3")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 3)
        self.assertEqual(payload["pool_size"], 3)
        self.assertEqual(
            {item["dashboard_category"] for item in payload["items"]},
            {"Personal discoveries", "Add to your collection", "Artist Deep Dives"},
        )
        self.assertEqual(self.fake.calls, [
            ("discovery_get_list", "personal", 150),
            ("discovery_get_list", "classics", 150),
            ("discovery_get_list", "artist_deep_dive", 150),
        ])

    def test_dashboard_deduplicates_and_filters_non_album_candidates(self):
        self.fake.lists["classics"] = {"recommendations": [
            {"artist": " artist a ", "album": "album a"},
            {"artist": "Artist D", "album": "Exclude"},
            {"artist": "Artist D", "album": "Album D"},
        ]}
        with patch("app.api.dashboard.random.shuffle", side_effect=lambda values: None):
            response = self.client.get("/api/dashboard-picks?count=20")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["pool_size"], 3)
        identities = [(item["artist"].casefold(), item["album"].casefold())
                      for item in payload["items"]]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertNotIn(("artist d", "exclude"), identities)

    def test_dashboard_rejects_invalid_count(self):
        response = self.client.get("/api/dashboard-picks?count=21")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "count must be between 1 and 20")


if __name__ == "__main__":
    unittest.main()
