"""Direct tests for persisted acquisition lifecycle transitions."""
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from acquisition_orchestration import request_skip_acquisition_source, switch_source_unless_dismissed
from acquisition_lifecycle import skip_request_error


class AcquisitionSkipTransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "acquisitions.sqlite"
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "CREATE TABLE discovery_acquisitions ("
                "artist_key TEXT, album_key TEXT, status TEXT, details_json TEXT, "
                "candidate_json TEXT, updated_at REAL, PRIMARY KEY(artist_key, album_key))"
            )
        self.initialized = []
        self.lock = threading.RLock()

    def tearDown(self):
        self.temp.cleanup()

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def seed(self, status="downloading", candidate=None, details=None):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO discovery_acquisitions "
                "(artist_key, album_key, status, details_json, candidate_json, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("artist", "album", status, json.dumps(details or {}),
                 json.dumps({"fallback_candidates": [{"username": "peer"}]} if candidate is None else candidate), 0),
            )

    def request(self):
        return request_skip_acquisition_source(
            "Artist", "Album",
            initialize=lambda: self.initialized.append(True),
            transition_lock=self.lock,
            connect=self.connect,
            music_key=lambda value: value.casefold(),
            lifecycle=SimpleNamespace(skip_request_error=skip_request_error),
            now=lambda: 123.0,
            json_module=json,
        )

    def test_records_skip_request_only_for_downloading_job_with_fallback(self):
        self.seed()
        result = self.request()
        self.assertTrue(result["ok"])
        with self.connect() as db:
            row = db.execute(
                "SELECT status, details_json, updated_at FROM discovery_acquisitions"
            ).fetchone()
        self.assertEqual(row[0], "downloading")
        self.assertEqual(json.loads(row[1]), {"skip_requested": True, "skip_requested_at": 123.0})
        self.assertEqual(row[2], 123.0)
        self.assertEqual(self.initialized, [True])

    def test_missing_non_downloading_and_no_fallback_jobs_are_rejected_without_mutation(self):
        self.assertFalse(self.request()["ok"])
        for status, candidate, expected in (
            ("dismissed", {}, "This acquisition has been dismissed."),
            ("importing", {"fallback_candidates": [{}]}, "This acquisition is not downloading."),
            ("downloading", {}, "No eligible fallback source remains."),
        ):
            with self.subTest(status=status):
                self.seed(status=status, candidate=candidate)
                result = self.request()
                self.assertEqual(result["error"], expected)
                with self.connect() as db:
                    row = db.execute("SELECT details_json FROM discovery_acquisitions").fetchone()
                self.assertEqual(json.loads(row[0]), {})


class AcquisitionSourceSwitchGuardTests(unittest.TestCase):
    def test_dismissal_check_and_switch_run_inside_same_transition_lock(self):
        events = []

        class TrackingLock:
            def __enter__(self):
                events.append("lock-enter")
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("lock-exit")

        result = switch_source_unless_dismissed(
            "Artist", "Album",
            transition_lock=TrackingLock(),
            is_dismissed=lambda artist, album: events.append(("check", artist, album)) or False,
            switch_source=lambda: events.append("switch") or {"queued": True},
        )
        self.assertEqual(result, {"queued": True})
        self.assertEqual(events, [
            "lock-enter", ("check", "Artist", "Album"), "switch", "lock-exit",
        ])

    def test_dismissed_acquisition_never_calls_switch_source(self):
        events = []
        result = switch_source_unless_dismissed(
            "Artist", "Album",
            transition_lock=threading.RLock(),
            is_dismissed=lambda _artist, _album: True,
            switch_source=lambda: events.append("switch"),
        )
        self.assertIsNone(result)
        self.assertEqual(events, [])

    def test_switch_result_and_exceptions_are_not_hidden(self):
        expected = object()
        self.assertIs(
            switch_source_unless_dismissed(
                "Artist", "Album", transition_lock=threading.RLock(),
                is_dismissed=lambda _artist, _album: False,
                switch_source=lambda: expected,
            ),
            expected,
        )
        failure = RuntimeError("switch failed")
        def fail():
            raise failure
        with self.assertRaisesRegex(RuntimeError, "switch failed"):
            switch_source_unless_dismissed(
                "Artist", "Album", transition_lock=threading.RLock(),
                is_dismissed=lambda _artist, _album: False,
                switch_source=fail,
            )


if __name__ == "__main__":
    unittest.main()
