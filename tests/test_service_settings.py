"""Direct-import tests for service-settings policy and secret redaction."""
import json
import tempfile
import unittest
from pathlib import Path

from service_settings import (
    get_lastfm_settings,
    get_navidrome_settings,
    listenbrainz_username,
    navidrome_config,
    set_listenbrainz_settings,
    set_navidrome_settings,
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
        }
        self.writes = []

    def read_settings(self):
        return dict(self.state)

    def write_settings(self, values):
        self.writes.append(dict(values))
        self.state.update(values)

    def set_music_dir(self, path):
        self.music_dir = path

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

    def test_listenbrainz_username_validation_and_save(self):
        self.assertEqual(listenbrainz_username(self.read_settings), "listener")
        result = json.loads(set_listenbrainz_settings(self.write_settings, "new.listener"))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["listenbrainz_username"], "new.listener")
        before = list(self.writes)
        result = json.loads(set_listenbrainz_settings(self.write_settings, "not a username"))
        self.assertFalse(result["ok"])
        self.assertEqual(self.state["listenbrainz_username"], "new.listener")
        self.assertEqual(self.writes, before)



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
                True, "/downloads", directory,
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


if __name__ == "__main__":
    unittest.main()
