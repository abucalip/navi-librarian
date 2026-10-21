"""Direct-import regression tests for settings SQLite persistence and migrations."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from settings.persistence import SettingsPersistence


class SettingsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "settings.sqlite3"
        self.music_dir = self.root / "music"
        self.music_dir.mkdir()
        self.downloads = self.root / "downloads"
        self.downloads.mkdir()
        self.defaults = {
            "music_library_path": "",
            "slskd_downloads_path": str(self.downloads),
            "quality_priority": ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
            "navidrome_password": "",
            "recommendation_diversity": 0,
        }
        self.store = SettingsPersistence(
            self.database, self.defaults, lambda: self.music_dir,
            lambda path: setattr(self, "music_dir", path), clock=lambda: 123.0,
        )

    def test_direct_import_round_trip_unicode_values_and_secret_storage(self):
        self.store.write({"listenbrainz_username": "Björk", "navidrome_password": "secret"})
        self.assertEqual(self.store.read()["listenbrainz_username"], "Björk")
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute("SELECT value_json FROM discovery_settings WHERE setting_key='navidrome_password'").fetchone()[0], '"secret"')

    def test_recommendation_diversity_defaults_and_persists(self):
        self.assertEqual(self.store.read()["recommendation_diversity"], 0)
        self.store.write({"recommendation_diversity": 75})
        self.assertEqual(self.store.read()["recommendation_diversity"], 75)

    def test_corrupt_json_is_ignored_and_defaults_survive(self):
        self.store.initialize()
        with sqlite3.connect(self.database) as db:
            db.execute("INSERT INTO discovery_settings VALUES (?, ?, ?)", ("navidrome_password", "{", 1))
        self.assertEqual(self.store.read()["navidrome_password"], "")

    def test_legacy_quality_order_is_preserved_while_new_tiers_append(self):
        legacy = ["flac_cd", "mp3_192", "mp3_320", "mp3_193_319"]
        self.store.write({"quality_priority": legacy})
        self.assertEqual(self.store.read()["quality_priority"], legacy + ["flac_16_44", "flac_hires"])

    def test_absolute_saved_music_path_is_applied(self):
        target = self.root / "alternate"
        target.mkdir()
        self.store.write({"music_library_path": str(target)})
        self.store.read()
        self.assertEqual(self.music_dir, target)

    def test_database_permissions_are_restricted_when_supported(self):
        self.store.initialize()
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
