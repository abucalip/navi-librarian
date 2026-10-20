"""Regression tests for the settings API router's injected service boundary."""
import json
import unittest
from unittest.mock import Mock

from fastapi import HTTPException
from fastapi.params import Depends

from app.api import settings
from app.api.dependencies import get_librarian


class SettingsRoutesTests(unittest.TestCase):
    def setUp(self):
        self.librarian = Mock()

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
            ("/api/settings/recommendation-diversity", "GET"),
            ("/api/settings/recommendation-diversity", "PUT"),
            ("/api/settings/automatic-refill", "GET"),
            ("/api/settings/automatic-refill", "PUT"),
        }
        self.assertEqual(actual, expected)

    def test_handlers_use_shared_lazy_dependency_without_importing_server(self):
        self.assertIs(settings.get_librarian, get_librarian)
        for route in settings.router.routes:
            if not getattr(route, "methods", set()).intersection({"GET", "PUT", "POST"}):
                continue
            dependency = next(
                parameter.default
                for parameter in __import__("inspect").signature(route.endpoint).parameters.values()
                if parameter.name == "librarian"
            )
            self.assertIsInstance(dependency, Depends)
            self.assertIs(dependency.dependency, get_librarian)

    def test_get_navidrome_settings_parses_json_string(self):
        self.librarian.discovery_get_navidrome_settings.return_value = '{"ok": true}'
        self.assertEqual(settings.get_navidrome_settings(librarian=self.librarian), {"ok": True})
        self.librarian.discovery_get_navidrome_settings.assert_called_once_with()

    def test_set_navidrome_settings_preserves_payload_mapping(self):
        self.librarian.discovery_set_navidrome_settings.return_value = '{"ok": true}'
        result = settings.set_navidrome_settings({
            "navidrome_url": "http://music.local", "username": "owner",
            "password": "secret", "music_library_path": "/music",
        }, librarian=self.librarian)
        self.assertEqual(result, {"ok": True})
        self.librarian.discovery_set_navidrome_settings.assert_called_once_with(
            navidrome_url="http://music.local", username="owner", password="secret",
            music_library_path="/music",
        )

    def test_set_listenbrainz_returns_client_validation_error(self):
        self.librarian.discovery_set_listenbrainz_settings.return_value = '{"ok": false, "error": "invalid"}'
        with self.assertRaises(HTTPException) as raised:
            settings.set_listenbrainz_settings({"username": "bad"}, librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "invalid")

    def test_slskd_defaults_quality_priority_and_trims_optional_paths(self):
        self.librarian.discovery_set_slskd_settings.return_value = '{"ok": true}'
        result = settings.set_slskd_settings({
            "slskd_url": "http://slskd.local", "api_key": "secret",
            "slskd_downloads_path": " /downloads ", "music_library_path": " /music ",
        }, librarian=self.librarian)
        self.assertEqual(result, {"ok": True})
        kwargs = self.librarian.discovery_set_slskd_settings.call_args.kwargs
        self.assertEqual(kwargs["slskd_url"], "http://slskd.local")
        self.assertEqual(kwargs["api_key"], "secret")
        self.assertEqual(json.loads(kwargs["quality_priority_json"]), [
            "mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"
        ])
        self.assertEqual(kwargs["slskd_downloads_path"], "/downloads")
        self.assertEqual(kwargs["music_library_path"], "/music")

    def test_get_recommendation_diversity_settings_returns_stable_contract(self):
        self.librarian._discovery_settings_read.return_value = {
            "recommendation_diversity": 75,
        }
        self.assertEqual(
            settings.get_recommendation_diversity_settings(librarian=self.librarian),
            {"recommendation_diversity": 75},
        )
        self.librarian._discovery_settings_read.assert_called_once_with()

    def test_set_recommendation_diversity_requires_integer_in_range(self):
        self.librarian._discovery_settings_write.return_value = None
        self.assertEqual(
            settings.set_recommendation_diversity_settings(
                {"recommendation_diversity": 75}, librarian=self.librarian
            ),
            {
                "ok": True,
                "recommendation_diversity": 75,
                "message": "Recommendation diversity preference saved.",
            },
        )
        self.librarian._discovery_settings_write.assert_called_once_with({
            "recommendation_diversity": 75,
        })

        for invalid in ("75", 1.5, True, None, -1, 101, [], {}):
            with self.subTest(invalid=invalid):
                self.librarian._discovery_settings_write.reset_mock()
                with self.assertRaises(HTTPException) as raised:
                    settings.set_recommendation_diversity_settings(
                        {"recommendation_diversity": invalid}, librarian=self.librarian
                    )
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(
                    raised.exception.detail,
                    "recommendation_diversity must be an integer from 0 to 100.",
                )
                self.librarian._discovery_settings_write.assert_not_called()

    def test_connection_error_is_sanitized(self):
        self.librarian.discovery_test_slskd_connection.side_effect = RuntimeError("sensitive upstream detail")
        with self.assertRaises(HTTPException) as raised:
            settings.test_slskd_settings(librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not test the slskd connection.")

    def test_invalid_settings_remain_client_errors(self):
        self.librarian.discovery_set_navidrome_settings.return_value = '{"ok": false, "error": "bad input"}'
        with self.assertRaises(HTTPException) as raised:
            settings.set_navidrome_settings({}, librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "bad input")


    def test_slskd_auto_acquire_requires_json_boolean_and_preserves_explicit_false(self):
        self.librarian.discovery_set_slskd_settings.return_value = '{"ok": true}'
        for invalid in ("false", "true", 0, 1, None, [], {}):
            with self.subTest(invalid=invalid):
                self.librarian.discovery_set_slskd_settings.reset_mock()
                with self.assertRaises(HTTPException) as raised:
                    settings.set_slskd_settings(
                        {"auto_acquire_for_me": invalid}, librarian=self.librarian
                    )
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(
                    raised.exception.detail, "auto_acquire_for_me must be a boolean."
                )
                self.librarian.discovery_set_slskd_settings.assert_not_called()

        for value in (False, True):
            with self.subTest(value=value):
                self.librarian.discovery_set_slskd_settings.reset_mock()
                result = settings.set_slskd_settings(
                    {"auto_acquire_for_me": value}, librarian=self.librarian
                )
                self.assertEqual(result, {"ok": True})
                self.assertIs(
                    self.librarian.discovery_set_slskd_settings.call_args.kwargs[
                        "auto_acquire_for_me"
                    ],
                    value,
                )


if __name__ == "__main__":
    unittest.main()
