"""Regression tests for the extracted discovery API router."""
import json
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.api import discovery


class DiscoveryRoutesTests(unittest.TestCase):
    def setUp(self):
        self.librarian = Mock()

    def test_router_preserves_discovery_endpoint_paths_and_methods(self):
        actual = {
            (route.path, method)
            for route in discovery.router.routes
            for method in getattr(route, "methods", set())
        }
        self.assertEqual(actual, {
            ("/api/recommendations", "GET"),
            ("/api/discovery/lens-feedback", "GET"),
            ("/api/discovery/{list_name}", "GET"),
            ("/api/discovery/{list_name}/refresh", "POST"),
            ("/api/discovery/feedback", "POST"),
        })

    def test_recommendations_preserve_default_and_filter_non_album_items(self):
        payload = {"items": [
            {"artist": "A", "album": "Album", "is_album": True},
            {"artist": "B", "album": "Single", "is_album": False},
        ]}
        self.librarian.recommend_new_music.return_value = json.dumps(payload)
        self.librarian._discovery_is_album_candidate.side_effect = lambda item: item["is_album"]
        self.assertEqual(
            discovery.recommendations(librarian=self.librarian),
            {"items": [payload["items"][0]]},
        )
        self.librarian.recommend_new_music.assert_called_once_with(count=10)

    def test_recommendations_reject_invalid_count_and_sanitize_failure(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.recommendations(31, librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 400)
        self.librarian.recommend_new_music.side_effect = RuntimeError("secret")
        with self.assertRaises(HTTPException) as raised:
            discovery.recommendations(librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not generate recommendations.")

    def test_discovery_list_validates_name_count_and_maps_call(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_list("unknown")
        self.assertEqual(raised.exception.status_code, 404)
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_list("personal", 151)
        self.assertEqual(raised.exception.status_code, 400)
        self.librarian.discovery_get_list.return_value = '{"items": []}'
        self.assertEqual(
            discovery.discovery_list("for_me", librarian=self.librarian),
            {"items": []},
        )
        self.librarian.discovery_get_list.assert_called_once_with(list_name="for_me", count=30)

    def test_refresh_defaults_and_validates_count(self):
        self.librarian.discovery_refresh_list.return_value = '{"ok": true}'
        # "all" also starts the lens refresh thread; stub it so no real thread holds the shared
        # lens refresh lock after this test returns.
        with patch("discovery.lens_service.start_refresh") as start_refresh:
            self.assertEqual(
                discovery.refresh_discovery_list("all", librarian=self.librarian),
                {"ok": True},
            )
        start_refresh.assert_called_once_with(self.librarian)
        self.librarian.discovery_refresh_list.assert_called_once_with(list_name="all", count=20)
        for payload in (
            {"count": "bad"},
            {"count": "2"},
            {"count": 2.5},
            {"count": True},
            {"count": None},
            {"count": []},
            {"count": {}},
            {"count": 0},
            {"count": 21},
        ):
            with self.subTest(payload=payload), self.assertRaises(HTTPException) as raised:
                discovery.refresh_discovery_list("personal", payload, librarian=self.librarian)
            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(raised.exception.detail,
                             "count must be an integer" if type(payload.get("count")) is not int
                             else "count must be between 1 and 20")
        self.librarian.discovery_refresh_list.assert_called_once_with(list_name="all", count=20)
        with self.assertRaises(HTTPException) as raised:
            discovery.refresh_discovery_list("for_me")
        self.assertEqual(raised.exception.status_code, 404)

    def test_feedback_validates_and_preserves_payload(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_feedback(
                {"artist": "Artist", "album": "Album", "action": "bad"}
            )
        self.assertEqual(raised.exception.status_code, 400)
        metadata = {"title": "Café"}
        self.librarian.discovery_set_feedback.return_value = '{"ok": true}'
        self.assertEqual(discovery.discovery_feedback({
            "artist": " Artist ", "album": " Album ", "action": "save", "metadata": metadata,
        }, librarian=self.librarian), {"ok": True})
        self.librarian.discovery_set_feedback.assert_called_once_with(
            artist="Artist", album="Album", action="save",
            metadata_json=json.dumps(metadata, ensure_ascii=False),
        )

    def test_feedback_rejects_missing_fields_and_sanitizes_errors(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_feedback({"artist": "Artist", "action": "save"})
        self.assertEqual(raised.exception.status_code, 400)
        self.librarian.discovery_set_feedback.side_effect = RuntimeError("secret")
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_feedback(
                {"artist": "A", "album": "B", "action": "dismiss"},
                librarian=self.librarian,
            )
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not save discovery feedback.")


if __name__ == "__main__":
    unittest.main()
