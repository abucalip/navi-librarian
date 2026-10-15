"""Direct-import regression tests for the extracted metadata cache."""
import tempfile
import unittest
from pathlib import Path

from metadata_cache import MetadataCache


class MetadataCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "metadata.sqlite3"
        self.now = 1_000.0
        self.cache = MetadataCache(self.database, clock=lambda: self.now)

    def test_round_trip_preserves_unicode_json(self):
        value = {"artist": "Björk", "album": "موسيقى", "items": [1, None]}
        self.cache.set("release-group:1", value)
        self.assertEqual(self.cache.get("release-group:1", 60), value)

    def test_missing_and_expired_entries_are_cache_misses(self):
        self.assertIsNone(self.cache.get("missing", 60))
        self.cache.set("stale", {"ok": True})
        self.now += 61
        self.assertIsNone(self.cache.get("stale", 60))

    def test_invalid_json_is_a_cache_miss(self):
        import sqlite3
        with sqlite3.connect(self.database) as db:
            db.execute(
                "INSERT INTO metadata_cache (cache_key, value_json, cached_at) "
                "VALUES (?, ?, ?)",
                ("bad-json", "{", self.now),
            )
        self.assertIsNone(self.cache.get("bad-json", 60))

    def test_invalid_database_path_is_non_fatal(self):
        cache = MetadataCache(Path(self.temp.name) / "missing" / "cache.sqlite3",
                              clock=lambda: self.now)
        self.assertIsNone(cache.get("key", 60))
        cache.set("key", {"value": 1})


if __name__ == "__main__":
    unittest.main()
