"""Direct-import regression tests for acquisition source-switch orchestration."""
import unittest
from pathlib import Path
from types import SimpleNamespace

import acquisition_lifecycle
from acquisition_source_switch import switch_to_next_source_locked


class FakeHTTPError(Exception):
    pass


class AcquisitionSourceSwitchTests(unittest.TestCase):
    def setUp(self):
        self.posts = []
        self.saved_jobs = []
        self.status_updates = []
        self.cleanup_calls = []
        self.cleanup_results = [True]
        self.start_state = True
        self.post_exception = None
        self.jobs = [{
            "artist_key": "artist",
            "album_key": "album",
            "details": {"source_switches": 2},
        }]
        self.http_client = SimpleNamespace(HTTPError=FakeHTTPError, post=self.post)
        self.current = {
            "username": "original-peer",
            "folder": "Album",
            "files": [{"filename": "Album/01.flac", "size": 4}],
            "fallback_candidates": [],
        }

    def post(self, *args, **kwargs):
        self.posts.append((args, kwargs))
        if self.post_exception is not None:
            raise self.post_exception
        return SimpleNamespace(raise_for_status=lambda: None)

    def cleanup(self, root, candidate, base_url, headers):
        self.cleanup_calls.append((root, candidate, base_url, headers))
        return self.cleanup_results.pop(0) if self.cleanup_results else True

    def start_state_check(self, *args, **kwargs):
        return self.start_state

    def save_job(self, *args, **kwargs):
        self.saved_jobs.append((args, kwargs))

    def update_status(self, *args, **kwargs):
        self.status_updates.append((args, kwargs))
        return True

    def switch(self, candidate=None):
        return switch_to_next_source_locked(
            "Artist", "Album", candidate or self.current, {},
            Path("/downloads"), {"X-API-KEY": "test"}, "stalled",
            get_slskd_config=lambda: ("http://slskd", None, {}),
            lifecycle=acquisition_lifecycle,
            cleanup_source=self.cleanup,
            update_status=self.update_status,
            http_client=self.http_client,
            candidate_start_state=self.start_state_check,
            save_job=self.save_job,
            list_jobs=lambda: self.jobs,
            music_key=lambda value: str(value or "").strip().casefold(),
        )

    @staticmethod
    def fallback(username):
        return {
            "username": username,
            "folder": "Album",
            "files": [{"filename": "Album/01.flac", "size": 4}],
            "quality_summary": ["FLAC"],
        }

    def test_ambiguous_fallback_queue_is_monitored_without_trying_another_peer(self):
        self.post_exception = FakeHTTPError("connection dropped after request")
        self.start_state = None
        first = self.fallback("peer-one")
        second = self.fallback("peer-two")
        self.current["fallback_candidates"] = [first, second]

        result = self.switch()

        self.assertEqual(result["username"], "peer-one")
        self.assertEqual(len(self.posts), 1, "must not queue peer-two after an ambiguous response")
        self.assertEqual(len(self.saved_jobs), 1)
        args, kwargs = self.saved_jobs[0]
        self.assertEqual(args[2], "downloading")
        self.assertEqual(kwargs["candidate"]["username"], "peer-one")
        self.assertEqual(args[3]["queue_error"], "FakeHTTPError")
        self.assertEqual(kwargs["candidate"]["fallback_candidates"], [second])

    def test_cleanup_failure_stops_before_any_fallback_is_queued(self):
        self.cleanup_results = [False]
        self.current["fallback_candidates"] = [self.fallback("peer-one")]

        result = self.switch()

        self.assertIsNone(result)
        self.assertEqual(self.posts, [])
        self.assertEqual(len(self.cleanup_calls), 1)
        self.assertEqual(self.status_updates[-1][0][2], "source_switch_failed")

    def test_no_fallback_reports_terminal_state_without_cleanup(self):
        result = self.switch()

        self.assertIsNone(result)
        self.assertEqual(self.cleanup_calls, [])
        self.assertEqual(self.posts, [])
        self.assertEqual(self.status_updates[-1][0][2], "download_stalled_no_fallback")

    def test_failed_fallback_cleanup_prevents_trying_another_peer(self):
        first = self.fallback("peer-one")
        second = self.fallback("peer-two")
        self.current["fallback_candidates"] = [first, second]
        self.cleanup_results = [True, False]
        self.start_state = False

        result = self.switch()

        self.assertIsNone(result)
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(len(self.cleanup_calls), 2)
        self.assertEqual(self.status_updates[-1][0][2], "source_switch_failed")

    def test_confirmed_fallback_increments_switch_count_and_keeps_remaining_candidates(self):
        first = self.fallback("peer-one")
        second = self.fallback("peer-two")
        self.current["fallback_candidates"] = [first, second]

        result = self.switch()

        self.assertEqual(result["username"], "peer-one")
        self.assertEqual(result["fallback_candidates"], [second])
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(len(self.saved_jobs), 1)
        args, kwargs = self.saved_jobs[0]
        self.assertEqual(args[2], "downloading")
        self.assertEqual(args[3]["source_switches"], 3)
        self.assertEqual(kwargs["candidate"]["username"], "peer-one")


