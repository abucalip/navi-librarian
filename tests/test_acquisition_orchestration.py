"""Direct tests for persisted acquisition lifecycle transitions."""
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from acquisition_orchestration import request_skip_acquisition_source, switch_source_unless_dismissed, queue_candidate_unless_dismissed, import_source_unless_dismissed, existing_acquisition_response
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



class AcquisitionQueueGuardTests(unittest.TestCase):
    def test_dismissal_check_and_queue_are_serialized(self):
        events = []

        class TrackingLock:
            def __enter__(self):
                events.append("lock-enter")
            def __exit__(self, exc_type, exc, tb):
                events.append("lock-exit")

        result = queue_candidate_unless_dismissed(
            "Artist", "Album", transition_lock=TrackingLock(),
            is_dismissed=lambda artist, album: events.append(("check", artist, album)) or False,
            queue_source=lambda: events.append("queue") or {"queued": True},
        )
        self.assertEqual(result, {"queued": True})
        self.assertEqual(events, [
            "lock-enter", ("check", "Artist", "Album"), "queue", "lock-exit",
        ])

    def test_dismissed_acquisition_does_not_queue(self):
        calls = []
        result = queue_candidate_unless_dismissed(
            "Artist", "Album", transition_lock=threading.RLock(),
            is_dismissed=lambda _artist, _album: True,
            queue_source=lambda: calls.append("queue"),
        )
        self.assertIsNone(result)
        self.assertEqual(calls, [])

    def test_queue_result_and_exceptions_are_preserved(self):
        expected = object()
        self.assertIs(queue_candidate_unless_dismissed(
            "Artist", "Album", transition_lock=threading.RLock(),
            is_dismissed=lambda _artist, _album: False,
            queue_source=lambda: expected,
        ), expected)
        failure = RuntimeError("queue failed")
        def fail():
            raise failure
        with self.assertRaisesRegex(RuntimeError, "queue failed"):
            queue_candidate_unless_dismissed(
                "Artist", "Album", transition_lock=threading.RLock(),
                is_dismissed=lambda _artist, _album: False, queue_source=fail,
            )



class AcquisitionImportGuardTests(unittest.TestCase):
    def test_dismissal_check_and_import_run_inside_same_transition_lock(self):
        events = []

        class TrackingLock:
            def __enter__(self):
                events.append("lock-enter")
            def __exit__(self, exc_type, exc, tb):
                events.append("lock-exit")

        result = import_source_unless_dismissed(
            "Artist", "Album",
            transition_lock=TrackingLock(),
            is_dismissed=lambda artist, album: events.append(("check", artist, album)) or False,
            import_source=lambda: events.append("import") or "imported",
        )
        self.assertEqual(result, "imported")
        self.assertEqual(events, [
            "lock-enter", ("check", "Artist", "Album"), "import", "lock-exit",
        ])

    def test_dismissed_source_never_calls_import_callback(self):
        calls = []
        result = import_source_unless_dismissed(
            "Artist", "Album",
            transition_lock=threading.RLock(),
            is_dismissed=lambda _artist, _album: True,
            import_source=lambda: calls.append("import"),
        )
        self.assertEqual(result, "dismissed")
        self.assertEqual(calls, [])

    def test_import_result_and_exceptions_are_preserved(self):
        expected = object()
        self.assertIs(import_source_unless_dismissed(
            "Artist", "Album", transition_lock=threading.RLock(),
            is_dismissed=lambda _artist, _album: False,
            import_source=lambda: expected,
        ), expected)
        failure = RuntimeError("import guard callback failed")
        def fail():
            raise failure
        with self.assertRaisesRegex(RuntimeError, "import guard callback failed"):
            import_source_unless_dismissed(
                "Artist", "Album", transition_lock=threading.RLock(),
                is_dismissed=lambda _artist, _album: False, import_source=fail,
            )



class ExistingAcquisitionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.identity = ("artist", "album")
        self.active_requests = set()
        self.active_watchers = set()
        self.watcher_lock = threading.RLock()
        self.start_calls = []

    def run_decision(self, job=None, status=None, watcher_active=False, start=None):
        def start_watcher(*args):
            self.start_calls.append(args)
            if start is not None:
                return start(*args)
            self.active_watchers.add(self.identity)
        return existing_acquisition_response(
            "Artist", "Album", self.identity, job, status, watcher_active,
            active_requests=self.active_requests,
            start_watcher=start_watcher,
            watcher_lock=self.watcher_lock,
            active_watchers=self.active_watchers,
            lifecycle=SimpleNamespace(should_resume_monitor=__import__(
                "acquisition_lifecycle"
            ).should_resume_monitor),
            json_module=json,
        )

    def test_incomplete_saved_source_refuses_recovery_without_starting_watcher(self):
        result = json.loads(self.run_decision({
            "artist": "Artist", "album": "Album",
            "candidate": {"username": "peer", "files": []}, "settings": {},
        }, status="downloading"))
        self.assertEqual(result["status"], "recovery_unavailable")
        self.assertEqual(self.start_calls, [])
        self.assertEqual(self.active_watchers, set())

    def test_valid_saved_source_resumes_watcher_without_requeue(self):
        candidate = {"username": "peer", "files": [{"filename": "Album/01.flac"}]}
        result = json.loads(self.run_decision({
            "artist": "Artist", "album": "Album",
            "candidate": candidate, "settings": {"slskd_downloads_path": "/downloads"},
        }, status="downloading"))
        self.assertEqual(result["status"], "recovery_started")
        self.assertEqual(self.start_calls, [(
            "Artist", "Album", candidate, {"slskd_downloads_path": "/downloads"},
        )])
        self.assertEqual(self.active_watchers, {self.identity})

    def test_watcher_start_failure_is_reported_without_requeue(self):
        def fail(*_args):
            raise RuntimeError("thread start failed")
        result = json.loads(self.run_decision({
            "artist": "Artist", "album": "Album",
            "candidate": {"username": "peer", "files": [{"filename": "Album/01.flac"}]},
            "settings": {},
        }, status="downloading", start=fail))
        self.assertEqual(result["status"], "monitor_recovery_failed")
        self.assertEqual(result["error"], "RuntimeError")
        self.assertEqual(self.active_watchers, set())

    def test_importing_imported_and_active_requests_short_circuit(self):
        for status in ("importing", "imported"):
            with self.subTest(status=status):
                result = json.loads(self.run_decision(status=status))
                self.assertEqual(result["status"], status)
        self.active_requests.add(self.identity)
        result = json.loads(self.run_decision())
        self.assertEqual(result["status"], "already_in_progress")

    def test_no_existing_job_or_active_request_allows_new_search(self):
        self.assertIsNone(self.run_decision())


if __name__ == "__main__":
    unittest.main()
