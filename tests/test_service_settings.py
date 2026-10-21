"""Direct-import tests for service-settings policy and secret redaction."""
import json
import tempfile
import unittest
from pathlib import Path

from service_settings import (
    automatic_refill_enabled_value,
    get_automatic_refill_settings,
    set_automatic_refill_settings,
    get_lastfm_settings,
    get_recommendation_diversity_settings,
    recommendation_diversity_value,
    set_recommendation_diversity_settings,
    get_navidrome_settings,
    listenbrainz_username,
    navidrome_config,
    set_listenbrainz_settings,
    set_lastfm_settings,
    set_navidrome_settings,
    test_navidrome_connection,
    test_lastfm_connection,
    test_listenbrainz_connection,
)


class ServiceSettingsTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "navidrome_url": "http://navidrome:4533",
            "navidrome_user": "test-user",
            "navidrome_password": "super-secret",
            "lastfm_api_key": "lastfm-secret",
            "listenbrainz_username": "listener",
            "music_library_path": "",
            "recommendation_diversity": 0,
        }
        self.writes = []

    def read_settings(self):
        return dict(self.state)

    def write_settings(self, values):
        self.writes.append(dict(values))
        self.state.update(values)

    def set_music_dir(self, path):
        self.music_dir = path

    def test_recommendation_diversity_setting_is_bounded_persistent_and_fail_safe(self):
        self.assertEqual(recommendation_diversity_value(self.read_settings), 0)
        self.assertEqual(
            json.loads(get_recommendation_diversity_settings(self.read_settings)),
            {"recommendation_diversity": 0},
        )

        for value in (0, 75, 100):
            result = json.loads(set_recommendation_diversity_settings(self.write_settings, value))
            self.assertTrue(result["ok"])
            self.assertEqual(result["recommendation_diversity"], value)
            self.assertEqual(recommendation_diversity_value(self.read_settings), value)

        before = list(self.writes)
        for invalid in ("75", 1.5, True, None, -1, 101, [], {}):
            with self.subTest(invalid=invalid):
                result = json.loads(set_recommendation_diversity_settings(self.write_settings, invalid))
                self.assertFalse(result["ok"])
                self.assertEqual(self.writes, before)

        for invalid_stored in ("75", 1.5, True, None, -1, 101, [], {}):
            self.state["recommendation_diversity"] = invalid_stored
            with self.subTest(invalid_stored=invalid_stored):
                self.assertEqual(recommendation_diversity_value(self.read_settings), 0)
                self.assertEqual(
                    json.loads(get_recommendation_diversity_settings(self.read_settings)),
                    {"recommendation_diversity": 0},
                )

    def test_navidrome_settings_never_return_password(self):
        result = json.loads(get_navidrome_settings(self.read_settings, Path("/music")))
        self.assertEqual(result["username"], "test-user")
        self.assertTrue(result["password_configured"])
        self.assertNotIn("password", result)
        self.assertNotIn("super-secret", json.dumps(result))

    def test_navidrome_config_requires_valid_url_and_credentials(self):
        self.assertEqual(
            navidrome_config(self.read_settings),
            ("http://navidrome:4533", "test-user", "super-secret"),
        )
        self.state["navidrome_password"] = ""
        with self.assertRaisesRegex(ValueError, "username and password"):
            navidrome_config(self.read_settings)
        self.state.update({
            "navidrome_url": "file:///tmp/navidrome",
            "navidrome_password": "super-secret",
        })
        with self.assertRaisesRegex(ValueError, "valid HTTP or HTTPS"):
            navidrome_config(self.read_settings)
        self.state["navidrome_url"] = ""
        with self.assertRaisesRegex(ValueError, "valid HTTP or HTTPS"):
            navidrome_config(self.read_settings)

    def test_navidrome_save_preserves_password_and_does_not_return_it(self):
        with tempfile.TemporaryDirectory() as directory:
            result = json.loads(set_navidrome_settings(
                self.read_settings, self.write_settings, lambda: Path("/music"),
                self.set_music_dir, "http://navidrome:4533/", "new-user", "", directory,
            ))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["navidrome_password"], "super-secret")
        self.assertNotIn("super-secret", json.dumps(result))
        self.assertEqual(result["music_library_path"], directory)
        self.assertEqual(self.music_dir, Path(directory))

    def test_navidrome_invalid_settings_do_not_write_or_change_path(self):
        self.music_dir = Path("/music")
        result = json.loads(set_navidrome_settings(
            self.read_settings, self.write_settings, lambda: self.music_dir,
            self.set_music_dir, "file:///invalid", "user", "password",
        ))
        self.assertFalse(result["ok"])
        self.assertEqual(self.writes, [])
        self.assertEqual(self.music_dir, Path("/music"))

        result = json.loads(set_navidrome_settings(
            self.read_settings, self.write_settings, lambda: self.music_dir,
            self.set_music_dir, "http://navidrome:4533", "", "password",
        ))
        self.assertFalse(result["ok"])
        self.assertEqual(self.writes, [])

    def test_navidrome_rejects_nonexistent_or_relative_library_path(self):
        for path in ("relative/music", "/this/path/should/not/exist/navidrome-librarian"):
            with self.subTest(path=path):
                result = json.loads(set_navidrome_settings(
                    self.read_settings, self.write_settings, lambda: Path("/music"),
                    self.set_music_dir, "http://navidrome:4533", "user", "",
                    path,
                ))
                self.assertFalse(result["ok"])
        self.assertEqual(self.writes, [])

    def test_lastfm_settings_only_return_configured_flag(self):
        result = json.loads(get_lastfm_settings(self.read_settings))
        self.assertTrue(result["api_key_configured"])
        self.assertNotIn("lastfm-secret", json.dumps(result))
        self.assertNotIn("lastfm_api_key", result)

    def test_lastfm_save_preserves_blank_key_and_never_returns_secret(self):
        result = json.loads(set_lastfm_settings(self.read_settings, self.write_settings, "  new-key  "))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["lastfm_api_key"], "new-key")
        self.assertNotIn("new-key", json.dumps(result))
        self.assertNotIn("lastfm_api_key", result)

        before = len(self.writes)
        result = json.loads(set_lastfm_settings(self.read_settings, self.write_settings, "   "))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["lastfm_api_key"], "new-key")
        self.assertEqual(len(self.writes), before + 1)
        self.assertNotIn("new-key", json.dumps(result))

    def test_listenbrainz_username_validation_and_save(self):
        self.assertEqual(listenbrainz_username(self.read_settings), "listener")
        self.state["listenbrainz_username"] = ""
        with self.assertRaisesRegex(ValueError, "Configure a valid ListenBrainz username"):
            listenbrainz_username(self.read_settings)
        self.state["listenbrainz_username"] = "listener"
        result = json.loads(set_listenbrainz_settings(self.write_settings, "new.listener"))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["listenbrainz_username"], "new.listener")
        before = list(self.writes)
        result = json.loads(set_listenbrainz_settings(self.write_settings, "not a username"))
        self.assertFalse(result["ok"])
        self.assertEqual(self.state["listenbrainz_username"], "new.listener")
        self.assertEqual(self.writes, before)

    def test_listenbrainz_token_saved_preserved_validated_and_never_returned(self):
        from service_settings import get_listenbrainz_settings
        result = json.dumps(json.loads(set_listenbrainz_settings(self.write_settings, "listener", "abc-123_XYZ")))
        self.assertEqual(self.state["listenbrainz_token"], "abc-123_XYZ")
        self.assertNotIn("abc-123_XYZ", result)
        json.loads(set_listenbrainz_settings(self.write_settings, "listener", ""))
        self.assertEqual(self.state["listenbrainz_token"], "abc-123_XYZ")
        before = list(self.writes)
        bad = json.loads(set_listenbrainz_settings(self.write_settings, "listener", "bad token\r\nX: y"))
        self.assertFalse(bad["ok"])
        self.assertEqual(self.writes, before)
        status = get_listenbrainz_settings(self.read_settings, "listener")
        self.assertTrue(json.loads(status)["token_configured"])
        self.assertNotIn("abc-123_XYZ", status)
        self.state["listenbrainz_token"] = ""
        self.assertFalse(json.loads(get_listenbrainz_settings(self.read_settings, "listener"))["token_configured"])

    def test_slskd_settings_redact_key_and_use_defaults(self):
        from service_settings import get_slskd_settings
        result = json.loads(get_slskd_settings(
            self.read_settings, Path("/music"),
            {
                "slskd_url": "http://slskd:5030",
                "slskd_downloads_path": "/downloads",
                "quality_priority": ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
            },
        ))
        self.assertFalse(result["api_key_configured"])
        self.assertNotIn("api_key", result)
        self.assertIn("quality_labels", result)

    def test_slskd_config_requires_valid_url_and_api_key(self):
        from service_settings import slskd_config
        self.state.update({"slskd_url": "http://slskd:5030", "slskd_api_key": "slskd-secret"})
        self.assertEqual(slskd_config(self.read_settings)[:2], ("http://slskd:5030", "slskd-secret"))
        self.state["slskd_url"] = "file:///bad"
        with self.assertRaisesRegex(ValueError, "valid HTTP or HTTPS"):
            slskd_config(self.read_settings)
        self.state["slskd_url"] = ""
        with self.assertRaisesRegex(ValueError, "valid HTTP or HTTPS"):
            slskd_config(self.read_settings)
        self.state.update({"slskd_url": "http://slskd:5030", "slskd_api_key": ""})
        with self.assertRaisesRegex(ValueError, "API key"):
            slskd_config(self.read_settings)

    def test_slskd_save_preserves_key_and_validates_all_inputs_before_write(self):
        from service_settings import set_slskd_settings
        defaults = {
            "slskd_url": "http://slskd:5030",
            "slskd_downloads_path": "/downloads",
            "quality_priority": ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
        }
        self.state.update({"slskd_api_key": "slskd-secret", "slskd_url": "http://slskd:5030"})
        with tempfile.TemporaryDirectory() as directory:
            result = json.loads(set_slskd_settings(
                self.read_settings, self.write_settings, lambda: Path("/music"),
                self.set_music_dir, defaults, "http://slskd:5030/", "",
                '["mp3_320","mp3_193_319","mp3_192","flac_cd","flac_16_44","flac_hires"]',
                "/downloads", directory,
            ))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["slskd_api_key"], "slskd-secret")
        self.assertNotIn("slskd-secret", json.dumps(result))
        self.assertEqual(result["music_library_path"], directory)
        self.assertEqual(self.music_dir, Path(directory))
        before = list(self.writes)
        for kwargs in (
            {"slskd_url": "file:///bad"},
            {"quality_priority_json": "not-json"},
            {"quality_priority_json": '["mp3_320"]'},
            {"quality_priority_json": '[{"unexpected": "unhashable"}]'},
            {"slskd_downloads_path": "relative/downloads"},
            {"music_library_path": "relative/music"},
            {"music_library_path": "/definitely/not/a/real/library/path"},
        ):
            args = {
                "settings_read": self.read_settings, "settings_write": self.write_settings,
                "get_music_dir": lambda: Path("/music"), "set_music_dir": self.set_music_dir,
                "defaults": defaults,
            }
            args.update(kwargs)
            result = json.loads(set_slskd_settings(**args))
            self.assertFalse(result["ok"], kwargs)
            self.assertEqual(self.writes, before, kwargs)


    def test_navidrome_connection_service_preserves_result_contract(self):
        result = json.loads(test_navidrome_connection(
            lambda method: self.assertEqual(method, "ping"), json.dumps
        ))
        self.assertEqual(result["status"], "connected")
        failed = json.loads(test_navidrome_connection(
            lambda method: (_ for _ in ()).throw(ValueError("Configure credentials")),
            json.dumps,
        ))
        self.assertEqual(failed["message"], "Configure credentials")
        self.assertNotIn("password", json.dumps(failed))

    def test_lastfm_connection_service_redacts_key_and_handles_auth_failure(self):
        calls = []
        class Response:
            def raise_for_status(self): pass
            def json(self): return {"error": 10}
        def http_get(*args, **kwargs):
            calls.append((args, kwargs))
            return Response()
        result = json.loads(test_lastfm_connection(self.read_settings, http_get, json.dumps))
        self.assertEqual(result["status"], "authentication_failed")
        self.assertNotIn("lastfm-secret", json.dumps(result))
        self.assertEqual(calls[0][1]["params"]["api_key"], "lastfm-secret")
        empty = json.loads(test_lastfm_connection(
            lambda: {"lastfm_api_key": ""}, http_get, json.dumps
        ))
        self.assertEqual(empty["status"], "not_configured")

    def test_listenbrainz_connection_service_handles_missing_profile_and_errors(self):
        class Response:
            status_code = 404
            def raise_for_status(self): pass
        result = json.loads(test_listenbrainz_connection(
            lambda: "listener", lambda *args, **kwargs: Response(), json.dumps
        ))
        self.assertEqual(result["status"], "not_found")
        self.assertNotIn("api_key", json.dumps(result))

    def test_automatic_refill_defaults_on_and_fails_safe_on_corrupt_values(self):
        self.assertTrue(automatic_refill_enabled_value(lambda: {}))
        for corrupt in ("false", 0, 1, None, [], {"enabled": False}):
            with self.subTest(corrupt=corrupt):
                self.assertTrue(
                    automatic_refill_enabled_value(lambda c=corrupt: {"automatic_refill_enabled": c})
                )
        self.assertFalse(
            automatic_refill_enabled_value(lambda: {"automatic_refill_enabled": False})
        )
        self.assertEqual(
            json.loads(get_automatic_refill_settings(lambda: {})),
            {"automatic_refill_enabled": True},
        )

    def test_automatic_refill_setting_accepts_only_booleans_and_persists_them(self):
        writes = []
        result = json.loads(set_automatic_refill_settings(writes.append, False))
        self.assertTrue(result["ok"])
        self.assertEqual(writes, [{"automatic_refill_enabled": False}])

        writes.clear()
        for invalid in (0, 1, "false", None):
            with self.subTest(invalid=invalid):
                result = json.loads(set_automatic_refill_settings(writes.append, invalid))
                self.assertFalse(result["ok"])
        self.assertEqual(writes, [])


if __name__ == "__main__":
    unittest.main()
