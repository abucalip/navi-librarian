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
        self.store = {}
        self.owned = set()

    def api_call(self, method):
        self.calls.append(("api_call", method))
        if self.health_error:
            raise self.health_error
        return {"status": "pong"}

    def _discovery_read_list(self, name):
        payload = self.store.get(name)
        return {"payload": payload, "generated_at": 1.0} if payload is not None else None

    def _discovery_write_list(self, name, payload):
        self.calls.append(("write", name))
        self.store[name] = payload

    def _music_key(self, text):
        return text.strip().casefold()

    def _discovery_settings_read(self):
        return {}

    def _discovery_library_snapshot(self):
        return {"albums": [{"artist": a, "album": b} for a, b in self.owned]}

    def _discovery_feedback_rows(self):
        return []


def lens_payload(day, *albums):
    return {"day": day, "albums": [{"artist": a, "album": b, "tags": ["rock"], "seed_tag": "rock"} for a, b in albums]}


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
            ("/api/dashboard/genres", "GET"),
            ("/api/dashboard/albums/{shelf}", "GET"),
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

    def test_picks_come_only_from_the_weeks_current_tastes_lists(self):
        from datetime import datetime
        from discovery.lens_storage import lens_day
        today = lens_day(datetime.now())
        self.fake.store["lens:current_tastes"] = lens_payload(today, ("Artist A", "Album A"), ("Artist B", "Album B"))
        self.fake.store["lens:deep_cuts"] = lens_payload(today, ("Other", "Not a pick"))
        with patch("app.api.dashboard.random.shuffle", side_effect=lambda values: None):
            response = self.client.get("/api/dashboard-picks?count=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([(i["artist"], i["album"]) for i in payload["items"]], [("Artist A", "Album A"), ("Artist B", "Album B")])
        self.assertEqual({i["dashboard_category"] for i in payload["items"]}, {"Current tastes"})
        self.assertIn(("write", f"lens_week:current_tastes:{today}"), self.fake.calls)

    def test_picks_reshuffle_on_every_request_and_skip_owned_albums(self):
        from datetime import datetime
        from discovery.lens_storage import lens_day
        today = lens_day(datetime.now())
        self.fake.store["lens:current_tastes"] = lens_payload(today, ("A", "1"), ("B", "2"), ("C", "3"))
        self.fake.owned = {("C", "3")}
        seen = []
        def reverse(values):
            seen.append(len(values)); values.reverse()
        with patch("app.api.dashboard.random.shuffle", side_effect=reverse):
            first = self.client.get("/api/dashboard-picks?count=5").json()
            second = self.client.get("/api/dashboard-picks?count=5").json()
        self.assertEqual(seen, [2, 2])
        self.assertEqual([i["artist"] for i in first["items"]], ["B", "A"])
        self.assertEqual(first, second)
        self.assertEqual(first["pool_size"], 2)

    def test_no_list_means_no_picks(self):
        response = self.client.get("/api/dashboard-picks?count=5")
        self.assertEqual(response.json()["items"], [])

    def test_dashboard_rejects_invalid_count(self):
        response = self.client.get("/api/dashboard-picks?count=21")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "count must be between 1 and 20")


if __name__ == "__main__":
    unittest.main()
