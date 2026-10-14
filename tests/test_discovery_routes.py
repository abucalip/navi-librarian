"""Regression tests for the extracted discovery API router."""
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api import discovery


class DiscoveryRoutesTests(unittest.TestCase):
    def test_router_preserves_discovery_endpoint_paths_and_methods(self):
        actual = {
            (route.path, method)
            for route in discovery.router.routes
            for method in getattr(route, "methods", set())
        }
        self.assertEqual(actual, {
            ("/api/recommendations", "GET"),
            ("/api/discovery/{list_name}", "GET"),
            ("/api/discovery/{list_name}/refresh", "POST"),
            ("/api/discovery/feedback", "POST"),
        })

    def test_recommendations_preserve_default_and_filter_non_album_items(self):
        payload = {"items": [
            {"artist": "A", "album": "Album", "is_album": True},
            {"artist": "B", "album": "Single", "is_album": False},
        ]}
        with patch.object(discovery.librarian, "recommend_new_music", return_value=json.dumps(payload)) as call, \
             patch.object(discovery.librarian, "_discovery_is_album_candidate",
                          side_effect=lambda item: item["is_album"]):
            self.assertEqual(discovery.recommendations(), {"items": [payload["items"][0]]})
        call.assert_called_once_with(count=10)

    def test_recommendations_reject_invalid_count_and_sanitize_failure(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.recommendations(31)
        self.assertEqual(raised.exception.status_code, 400)
        with patch.object(discovery.librarian, "recommend_new_music", side_effect=RuntimeError("secret")):
            with self.assertRaises(HTTPException) as raised:
                discovery.recommendations()
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not generate recommendations.")

    def test_discovery_list_validates_name_count_and_maps_call(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_list("unknown")
        self.assertEqual(raised.exception.status_code, 404)
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_list("personal", 151)
        self.assertEqual(raised.exception.status_code, 400)
        with patch.object(discovery.librarian, "discovery_get_list", return_value='{"items": []}') as call:
            self.assertEqual(discovery.discovery_list("for_me"), {"items": []})
        call.assert_called_once_with(list_name="for_me", count=30)

    def test_refresh_defaults_and_validates_count(self):
        with patch.object(discovery.librarian, "discovery_refresh_list", return_value='{"ok": true}') as call:
            self.assertEqual(discovery.refresh_discovery_list("all"), {"ok": True})
        call.assert_called_once_with(list_name="all", count=20)
        for payload, status in (({"count": "bad"}, 400), ({"count": 21}, 400)):
            with self.subTest(payload=payload), self.assertRaises(HTTPException) as raised:
                discovery.refresh_discovery_list("personal", payload)
            self.assertEqual(raised.exception.status_code, status)
        with self.assertRaises(HTTPException) as raised:
            discovery.refresh_discovery_list("for_me")
        self.assertEqual(raised.exception.status_code, 404)

    def test_feedback_validates_and_preserves_payload(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_feedback({"artist": "Artist", "album": "Album", "action": "bad"})
        self.assertEqual(raised.exception.status_code, 400)
        metadata = {"title": "Café"}
        with patch.object(discovery.librarian, "discovery_set_feedback", return_value='{"ok": true}') as call:
            self.assertEqual(discovery.discovery_feedback({
                "artist": " Artist ", "album": " Album ", "action": "save", "metadata": metadata,
            }), {"ok": True})
        call.assert_called_once_with(
            artist="Artist", album="Album", action="save",
            metadata_json=json.dumps(metadata, ensure_ascii=False),
        )

    def test_feedback_rejects_missing_fields_and_sanitizes_errors(self):
        with self.assertRaises(HTTPException) as raised:
            discovery.discovery_feedback({"artist": "Artist", "action": "save"})
        self.assertEqual(raised.exception.status_code, 400)
        with patch.object(discovery.librarian, "discovery_set_feedback", side_effect=RuntimeError("secret")):
            with self.assertRaises(HTTPException) as raised:
                discovery.discovery_feedback({"artist": "A", "album": "B", "action": "dismiss"})
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not save discovery feedback.")


if __name__ == "__main__":
    unittest.main()
