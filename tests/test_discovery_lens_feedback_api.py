"""Per-lens feedback summary: service gate and the route that serves it (Engine 2, Phase 5)."""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_librarian
from app.api.discovery import router
from discovery import lens_service
from settings.service import ENGINE2_LENS_LISTS_KEY


class FakeLibrarian:
    def __init__(self, *, enabled):
        self.settings = {ENGINE2_LENS_LISTS_KEY: enabled}
        self.feedback_reads = 0
        self.rows = [
            {"scope": "album", "status": "for_me", "metadata": {"lens": "deep_cuts"}},
            {"scope": "album", "status": "not_for_me", "metadata": {"lens": "deep_cuts"}},
            {"scope": "album", "status": "for_me", "metadata": {}},
        ]

    def _discovery_settings_read(self):
        return self.settings

    def _discovery_feedback_rows(self):
        self.feedback_reads += 1
        return self.rows

    def _discovery_list_acquisition_jobs(self):
        return [
            {"status": "no_matches", "details": {"metadata": {"lens": "deep_cuts"}}},
            {"status": "imported", "details": {"metadata": {"lens": "deep_cuts"}}},
            {"status": "queued", "details": {}},
        ]


class LensFeedbackServiceTests(unittest.TestCase):
    def test_disabled_setting_answers_without_reading_feedback(self):
        librarian = FakeLibrarian(enabled=False)
        self.assertEqual(lens_service.feedback_summary(librarian), {"disabled": True, "lenses": {}})
        self.assertEqual(librarian.feedback_reads, 0)

    def test_enabled_setting_counts_each_lens(self):
        summary = lens_service.feedback_summary(FakeLibrarian(enabled=True))
        self.assertFalse(summary["disabled"])
        self.assertEqual({k: v for k, v in summary["lenses"]["deep_cuts"].items() if k != "acquisitions"},
                         {"saved": 1, "dismissed": 1, "actions": 2, "save_rate": 0.5})
        self.assertEqual(summary["lenses"]["obsessions"]["actions"], 0)
        self.assertEqual(summary["lenses"]["deep_cuts"]["acquisitions"],
                         {"requests": 2, "by_status": {"no_matches": 1, "imported": 1}})
        self.assertEqual(summary["lenses"]["obsessions"]["acquisitions"],
                         {"requests": 0, "by_status": {}})


class LensFeedbackRouteTests(unittest.TestCase):
    def setUp(self):
        self.librarian = FakeLibrarian(enabled=True)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_librarian] = lambda: self.librarian
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def test_route_is_not_shadowed_by_the_list_route(self):
        response = self.client.get("/api/discovery/lens-feedback")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lenses"]["deep_cuts"]["saved"], 1)


if __name__ == "__main__":
    unittest.main()
