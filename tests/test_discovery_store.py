import sqlite3
import tempfile
import unittest
from pathlib import Path

from discovery_store import read_list, recent_recommendation_history, write_list


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

    def test_personal_list_write_records_only_hashed_identity_and_rank(self):
        payload = {"recommendations": [
            {"artist": "Beyoncé", "album": "Déjà vu"},
            {"artist": "Fela Kuti", "album": "Zombie"},
        ]}
        write_list(self.database_path, "personal", payload, generated_at=1000.0)

        history = recent_recommendation_history(self.database_path, now=1001.0)
        self.assertEqual(len(history), 2)
        self.assertEqual([row["rank"] for row in history], [2, 1])
        self.assertTrue(all(len(row["identity_hash"]) == 64 for row in history))
        with sqlite3.connect(self.database_path) as db:
            stored = db.execute(
                "SELECT identity_hash FROM recommendation_history"
            ).fetchall()
        serialized_hashes = repr(stored)
        self.assertNotIn("Beyoncé", serialized_hashes)
        self.assertNotIn("Déjà vu", serialized_hashes)

    def test_history_is_bounded_by_retention_window_and_future_rows_are_hidden(self):
        write_list(self.database_path, "personal", {
            "recommendations": [{"artist": "Old Artist", "album": "Old Album"}],
        }, generated_at=100.0)
        write_list(self.database_path, "personal", {
            "recommendations": [{"artist": "New Artist", "album": "New Album"}],
        }, generated_at=200_000.0)

        history = recent_recommendation_history(
            self.database_path, now=200_001.0, within_seconds=10_000.0
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["generated_at"], 200_000.0)
        self.assertEqual(recent_recommendation_history(
            self.database_path, now=150_000.0, within_seconds=1_000.0
        ), [])

    def test_history_row_count_is_capped(self):
        for batch in range(101):
            write_list(self.database_path, "personal", {
                "recommendations": [
                    {"artist": f"Artist {batch}-{rank}", "album": f"Album {rank}"}
                    for rank in range(20)
                ],
            }, generated_at=1000.0 + batch)
        history = recent_recommendation_history(
            self.database_path, now=1100.0, within_seconds=10_000.0
        )
        self.assertEqual(len(history), 2000)

    def test_non_personal_lists_do_not_record_recommendation_history(self):
        write_list(self.database_path, "classics", {
            "recommendations": [{"artist": "Artist", "album": "Album"}],
        }, generated_at=1234.0)
        self.assertEqual(recent_recommendation_history(self.database_path, now=1235.0), [])

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
