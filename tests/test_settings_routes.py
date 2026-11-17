"""Regression tests for the settings API router's injected service boundary."""
import json
import unittest
from unittest.mock import Mock, patch

import httpx

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
            ("/api/settings/discogs", "GET"),
            ("/api/settings/discogs", "PUT"),
            ("/api/settings/discogs/test", "POST"),
            ("/api/settings/slskd", "GET"),
            ("/api/settings/slskd", "PUT"),
            ("/api/settings/slskd/test", "POST"),
            ("/api/settings/library-resync", "GET"),
            ("/api/settings/library-resync", "PUT"),
            ("/api/settings/recommendation-diversity", "GET"),
            ("/api/settings/recommendation-diversity", "PUT"),
            ("/api/settings/automatic-refill", "GET"),
            ("/api/settings/automatic-refill", "PUT"),
            ("/api/settings/discovery-mode", "GET"),
            ("/api/settings/discovery-mode", "PUT"),
            ("/api/settings/star-seed", "GET"),
            ("/api/settings/star-seed", "PUT"),
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

    def test_get_navidrome_settings_reads_the_librarian_store(self):
        self.librarian._discovery_settings_read.return_value = {
            "navidrome_url": "http://music.local", "navidrome_user": "owner", "navidrome_password": "x",
        }
        self.librarian.MUSIC_DIR = "/music"
        self.assertEqual(settings.get_navidrome_settings(librarian=self.librarian), {
            "navidrome_url": "http://music.local", "username": "owner",
            "password_configured": True, "music_library_path": "/music",
        })

    def test_set_navidrome_settings_preserves_payload_mapping(self):
        with patch.object(settings, "_set_navidrome_settings", return_value='{"ok": true}') as call:
            result = settings.set_navidrome_settings({
                "navidrome_url": "http://music.local", "username": "owner",
                "password": "secret", "music_library_path": "/music",
            }, librarian=self.librarian)
        self.assertEqual(result, {"ok": True})
        args, kwargs = call.call_args
        self.assertIs(args[0], self.librarian._discovery_settings_read)
        self.assertIs(args[1], self.librarian._discovery_settings_write)
        self.librarian.MUSIC_DIR = "/now"
        self.assertEqual(args[2](), "/now")
        self.assertIs(args[3], self.librarian._set_music_dir)
        self.assertEqual(kwargs, {
            "navidrome_url": "http://music.local", "username": "owner", "password": "secret",
            "music_library_path": "/music",
        })

    def test_test_connections_pass_the_librarian_callbacks(self):
        with patch.object(settings, "_test_navidrome_connection", return_value='{"ok": true}') as call:
            self.assertEqual(settings.test_navidrome_settings(librarian=self.librarian), {"ok": True})
        call.assert_called_once_with(self.librarian.api_call, json.dumps)
        with patch.object(settings, "_test_lastfm_connection", return_value='{"ok": true}') as call:
            settings.test_lastfm_settings(librarian=self.librarian)
        call.assert_called_once_with(self.librarian._discovery_settings_read, httpx.get, json.dumps)
        with patch.object(settings, "_test_listenbrainz_connection", return_value='{"ok": true}') as call:
            settings.test_listenbrainz_settings(librarian=self.librarian)
        call.assert_called_once_with(self.librarian._listenbrainz_username, httpx.get, json.dumps)
        with patch.object(settings, "_test_slskd_connection", return_value='{"ok": true}') as call:
            settings.test_slskd_settings(librarian=self.librarian)
        call.assert_called_once_with(self.librarian._slskd_config)

    def test_get_lastfm_listenbrainz_and_slskd_settings_use_the_librarian_store(self):
        self.librarian._discovery_settings_read.return_value = {"listenbrainz_token": "t"}
        self.librarian._listenbrainz_username.return_value = "lb_user"
        self.assertEqual(settings.get_listenbrainz_settings(librarian=self.librarian),
                         {"username": "lb_user", "token_configured": True})
        with patch.object(settings, "_get_lastfm_settings", return_value='{"ok": true}') as call:
            settings.get_lastfm_settings(librarian=self.librarian)
        call.assert_called_once_with(self.librarian._discovery_settings_read)
        with patch.object(settings, "_get_slskd_settings", return_value='{"ok": true}') as call:
            settings.get_slskd_settings(librarian=self.librarian)
        call.assert_called_once_with(
            self.librarian._discovery_settings_read, self.librarian.MUSIC_DIR,
            self.librarian._DISCOVERY_SETTINGS_DEFAULTS,
        )

    def test_set_listenbrainz_returns_client_validation_error(self):
        with self.assertRaises(HTTPException) as raised:
            settings.set_listenbrainz_settings({"username": "bad user"}, librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("valid ListenBrainz username", raised.exception.detail)
        self.librarian._discovery_settings_write.assert_not_called()

    def test_set_lastfm_returns_400_with_message_for_invalid_username(self):
        with self.assertRaises(HTTPException) as raised:
            settings.set_lastfm_settings({"api_key": "", "username": "bad user"}, librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(
            raised.exception.detail,
            "Enter a valid Last.fm username (letters, numbers, hyphen or underscore).",
        )

    def test_set_lastfm_returns_saved_username_and_forwards_it(self):
        with patch.object(settings, "_set_lastfm_settings",
                          return_value='{"ok": true, "username": "listener_fm"}') as call:
            result = settings.set_lastfm_settings({"api_key": "", "username": "listener_fm"}, librarian=self.librarian)
        self.assertEqual(result, {"ok": True, "username": "listener_fm"})
        call.assert_called_once_with(
            self.librarian._discovery_settings_read, self.librarian._discovery_settings_write,
            api_key="", username="listener_fm",
        )

    def test_set_lastfm_without_username_leaves_it_unchanged(self):
        with patch.object(settings, "_set_lastfm_settings", return_value='{"ok": true}') as call:
            settings.set_lastfm_settings({"api_key": "k"}, librarian=self.librarian)
        self.assertEqual(call.call_args.kwargs, {"api_key": "k", "username": None})

    def test_set_listenbrainz_forwards_token_to_the_store(self):
        with patch.object(settings, "_set_listenbrainz_settings", return_value='{"ok": true}') as call:
            settings.set_listenbrainz_settings({"username": "u", "token": "tok"}, librarian=self.librarian)
        call.assert_called_once_with(self.librarian._discovery_settings_write, username="u", token="tok")

    def test_slskd_defaults_quality_priority_and_trims_optional_paths(self):
        with patch.object(settings, "_set_slskd_settings", return_value='{"ok": true}') as call:
            result = settings.set_slskd_settings({
                "slskd_url": "http://slskd.local", "api_key": "secret",
                "slskd_downloads_path": " /downloads ", "music_library_path": " /music ",
            }, librarian=self.librarian)
        self.assertEqual(result, {"ok": True})
        args, kwargs = call.call_args
        self.assertIs(args[0], self.librarian._discovery_settings_read)
        self.assertIs(args[1], self.librarian._discovery_settings_write)
        self.assertIs(args[3], self.librarian._set_music_dir)
        self.assertIs(args[4], self.librarian._DISCOVERY_SETTINGS_DEFAULTS)
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
        with patch.object(settings, "_test_slskd_connection",
                          side_effect=RuntimeError("sensitive upstream detail")), \
                self.assertRaises(HTTPException) as raised:
            settings.test_slskd_settings(librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not test the slskd connection.")

    def test_invalid_settings_remain_client_errors(self):
        with self.assertRaises(HTTPException) as raised:
            settings.set_navidrome_settings({}, librarian=self.librarian)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("URL", raised.exception.detail)
        self.librarian._discovery_settings_write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
