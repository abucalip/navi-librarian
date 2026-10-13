import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from discovery_store import read_list, write_list


class DiscoveryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "discovery.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_list_returns_none_and_initializes_schema(self):
        self.assertIsNone(read_list(self.database_path, "personal"))
        with sqlite3.connect(self.database_path) as db:
            table = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='discovery_lists'"
            ).fetchone()
        self.assertIsNotNone(table)

    def test_round_trip_preserves_unicode_payload_and_timestamp(self):
        payload = {"items": [{"artist": "Beyoncé", "album": "Déjà vu"}], "count": 1}
        write_list(self.database_path, "classics", payload, generated_at=1234.5)
        self.assertEqual(
            read_list(self.database_path, "classics"),
            {"payload": payload, "generated_at": 1234.5},
        )

    def test_lists_are_isolated_and_write_replaces_existing_payload(self):
        write_list(self.database_path, "personal", {"items": [1]}, generated_at=1)
        write_list(self.database_path, "classics", {"items": [2]}, generated_at=2)
        write_list(self.database_path, "personal", {"items": [3]}, generated_at=3)
        self.assertEqual(read_list(self.database_path, "personal")["payload"], {"items": [3]})
        self.assertEqual(read_list(self.database_path, "classics")["payload"], {"items": [2]})

    def test_malformed_json_returns_none(self):
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                "CREATE TABLE discovery_lists (name TEXT PRIMARY KEY, payload_json TEXT NOT NULL, generated_at REAL NOT NULL)"
            )
            db.execute(
                "INSERT INTO discovery_lists VALUES (?, ?, ?)",
                ("personal", "{not-json", 42),
            )
        self.assertIsNone(read_list(self.database_path, "personal"))


if __name__ == "__main__":
    unittest.main()
