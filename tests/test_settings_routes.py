"""Regression tests for the extracted settings API router."""
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api import settings


class SettingsRoutesTests(unittest.TestCase):
    def test_router_preserves_all_settings_endpoint_paths_and_methods(self):
        actual = {
            (route.path, method)
            for route in settings.router.routes
            for method in getattr(route, "methods", set())
        }
        expected = {
            ("/api/settings/navidrome", "GET"),
            ("/api/settings/navidrome", "PUT"),
            ("/api/settings/navidrome/test", "POST"),
            ("/api/settings/lastfm", "GET"),
            ("/api/settings/lastfm", "PUT"),
            ("/api/settings/lastfm/test", "POST"),
            ("/api/settings/listenbrainz", "GET"),
            ("/api/settings/listenbrainz", "PUT"),
            ("/api/settings/listenbrainz/test", "POST"),
            ("/api/settings/slskd", "GET"),
            ("/api/settings/slskd", "PUT"),
            ("/api/settings/slskd/test", "POST"),
        }
        self.assertEqual(actual, expected)
    def test_get_navidrome_settings_parses_json_string(self):
        with patch.object(settings.librarian, "discovery_get_navidrome_settings", return_value='{"ok": true}') as call:
            self.assertEqual(settings.get_navidrome_settings(), {"ok": True})
        call.assert_called_once_with()

    def test_set_navidrome_settings_preserves_payload_mapping(self):
        with patch.object(settings.librarian, "discovery_set_navidrome_settings", return_value='{"ok": true}') as call:
            result = settings.set_navidrome_settings({
                "navidrome_url": "http://music.local",
                "username": "owner",
                "password": "secret",
                "music_library_path": "/music",
            })
        self.assertEqual(result, {"ok": True})
        call.assert_called_once_with(
            navidrome_url="http://music.local",
            username="owner",
            password="secret",
            music_library_path="/music",
        )

    def test_set_listenbrainz_returns_client_validation_error(self):
        with patch.object(settings.librarian, "discovery_set_listenbrainz_settings", return_value='{"ok": false, "error": "invalid"}'):
            with self.assertRaises(HTTPException) as raised:
                settings.set_listenbrainz_settings({"username": "bad"})
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "invalid")

    def test_slskd_defaults_quality_priority_and_trims_optional_paths(self):
        with patch.object(settings.librarian, "discovery_set_slskd_settings", return_value='{"ok": true}') as call:
            result = settings.set_slskd_settings({
                "slskd_url": "http://slskd.local",
                "api_key": "secret",
                "slskd_downloads_path": " /downloads ",
                "music_library_path": " /music ",
            })
        self.assertEqual(result, {"ok": True})
        kwargs = call.call_args.kwargs
        self.assertEqual(kwargs["slskd_url"], "http://slskd.local")
        self.assertEqual(kwargs["api_key"], "secret")
        self.assertEqual(json.loads(kwargs["quality_priority_json"]), [
            "mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"
        ])
        self.assertEqual(kwargs["slskd_downloads_path"], "/downloads")
        self.assertEqual(kwargs["music_library_path"], "/music")

    def test_connection_error_is_sanitized(self):
        with patch.object(settings.librarian, "discovery_test_slskd_connection", side_effect=RuntimeError("sensitive upstream detail")):
            with self.assertRaises(HTTPException) as raised:
                settings.test_slskd_settings()
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not test the slskd connection.")


if __name__ == "__main__":
    unittest.main()
