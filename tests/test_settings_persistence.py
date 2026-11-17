"""Direct-import regression tests for settings SQLite persistence and migrations."""
import json
import sqlite3
import tempfile
import threading
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
        self.addCleanup(self.store.close)

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


    def _count_selects(self):
        """Trace the cached read connection and count settings SELECTs."""
        self.store.read()
        statements = []
        self.store._reader.set_trace_callback(statements.append)
        return lambda: sum(1 for sql in statements if "FROM discovery_settings" in sql)

    def test_unchanged_reads_run_one_select(self):
        selects = self._count_selects()
        self.store._cached = None
        for _ in range(10):
            self.store.read()
        self.assertEqual(selects(), 1)

    def test_write_through_another_connection_is_visible_on_next_read(self):
        self.store.write({"navidrome_password": "old"})
        self.assertEqual(self.store.read()["navidrome_password"], "old")
        with sqlite3.connect(self.database) as db:
            db.execute(
                "INSERT OR REPLACE INTO discovery_settings VALUES (?, ?, ?)",
                ("navidrome_password", json.dumps("new"), 2),
            )
        self.assertEqual(self.store.read()["navidrome_password"], "new")

    def test_write_from_a_second_instance_is_visible(self):
        # Models the worker and the web process each holding their own instance.
        other = SettingsPersistence(
            self.database, self.defaults, lambda: self.music_dir, lambda path: None,
        )
        self.addCleanup(other.close)
        self.assertEqual(self.store.read()["navidrome_password"], "")
        other.write({"navidrome_password": "changed"})
        self.assertEqual(self.store.read()["navidrome_password"], "changed")

    def test_password_change_through_auth_reader_takes_effect_on_next_read(self):
        from app.security.auth_settings import AuthSettingsReader

        reader = AuthSettingsReader(settings_getter=self.store.read)
        self.store.write({"navidrome_password": "first"})
        self.assertEqual(reader.get()["navidrome_password"], "first")
        self.store.write({"navidrome_password": "second"})
        self.assertEqual(reader.get()["navidrome_password"], "second")

    def test_local_write_invalidates_cache(self):
        selects = self._count_selects()
        self.store.read()
        self.store.write({"recommendation_diversity": 10})
        self.assertEqual(self.store.read()["recommendation_diversity"], 10)
        self.assertEqual(selects(), 1)

    def test_mutating_the_result_does_not_change_the_next_read(self):
        first = self.store.read()
        first["navidrome_password"] = "tampered"
        first["quality_priority"].append("tampered")
        second = self.store.read()
        self.assertEqual(second["navidrome_password"], "")
        self.assertNotIn("tampered", second["quality_priority"])
        self.assertNotIn("tampered", self.defaults["quality_priority"])

    def test_legacy_downloads_path_migrates_without_deadlock(self):
        legacy = str(self.music_dir.parent.parent / "downloads")
        self.store.write({"slskd_downloads_path": legacy})
        result = {}
        worker = threading.Thread(target=lambda: result.update(self.store.read()))
        worker.start()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive(), "read() deadlocked in the legacy migration")
        self.assertEqual(result["slskd_downloads_path"], str(self.downloads))
        with sqlite3.connect(self.database) as db:
            saved = db.execute(
                "SELECT value_json FROM discovery_settings WHERE setting_key='slskd_downloads_path'"
            ).fetchone()[0]
        self.assertEqual(json.loads(saved), str(self.downloads))
        self.assertEqual(self.store.read()["slskd_downloads_path"], str(self.downloads))

    def test_replaced_database_file_is_reopened(self):
        self.store.write({"navidrome_password": "old"})
        self.assertEqual(self.store.read()["navidrome_password"], "old")
        replacement = self.root / "replacement.sqlite3"
        with sqlite3.connect(replacement) as db:
            db.execute(
                "CREATE TABLE discovery_settings (setting_key TEXT PRIMARY KEY, "
                "value_json TEXT NOT NULL, updated_at REAL NOT NULL)"
            )
            db.execute(
                "INSERT INTO discovery_settings VALUES (?, ?, ?)",
                ("navidrome_password", json.dumps("restored"), 1),
            )
        replacement.replace(self.database)
        self.assertEqual(self.store.read()["navidrome_password"], "restored")

    def test_deleted_database_file_is_recreated_with_defaults(self):
        self.store.write({"navidrome_password": "old"})
        self.store.read()
        self.database.unlink()
        self.assertEqual(self.store.read()["navidrome_password"], "")
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)

    def test_reads_run_initialize_once(self):
        calls = []
        original = self.store.initialize

        def counting_initialize():
            calls.append(1)
            original()

        self.store.initialize = counting_initialize
        for _ in range(5):
            self.store.read()
        self.store.write({"recommendation_diversity": 5})
        self.store.read()
        self.assertEqual(len(calls), 1)

if __name__ == "__main__":
    unittest.main()
