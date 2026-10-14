"""Direct regression tests for acquisition lifecycle policy."""
import unittest
from types import SimpleNamespace
from acquisition_lifecycle import (
    CLEANUP_REQUIRED_STATUSES, RESUMABLE_ACQUISITION_STATUSES, cleanup_required,
    fallback_candidate_is_usable, normalized_candidate_files, queue_failure_action,
    should_resume_monitor, skip_request_error,
)


class AcquisitionLifecyclePolicyTests(unittest.TestCase):
    def test_monitor_recovery_requires_resumable_state_source_inventory_and_no_active_watcher(self):
        candidate = {"username": "peer", "files": [{"filename": "track.flac", "size": 42}]}
        for status in RESUMABLE_ACQUISITION_STATUSES:
            with self.subTest(status=status):
                self.assertTrue(should_resume_monitor(status, candidate, False))
                self.assertFalse(should_resume_monitor(status, candidate, True))
        self.assertFalse(should_resume_monitor("dismissed", candidate, False))
        self.assertFalse(should_resume_monitor("downloading", {"username": "peer"}, False))
        self.assertFalse(should_resume_monitor("downloading", {"files": candidate["files"]}, False))

    def test_cleanup_requirement_is_conservative_for_lifecycle_states_and_folder_evidence(self):
        for status in CLEANUP_REQUIRED_STATUSES:
            with self.subTest(status=status):
                self.assertTrue(cleanup_required(status, {}))
        self.assertTrue(cleanup_required("queued", {"source_folder": "/downloads/album"}))
        self.assertTrue(cleanup_required("queued", {"expected_folder": "album"}))
        self.assertFalse(cleanup_required("queued", {}))
        self.assertFalse(cleanup_required("dismissed", {}))

    def test_skip_request_rejects_missing_dismissed_non_downloading_and_no_fallback(self):
        self.assertEqual(skip_request_error(None, {}), "Acquisition not found.")
        self.assertEqual(skip_request_error("dismissed", {}), "This acquisition has been dismissed.")
        self.assertEqual(skip_request_error("importing", {"fallback_candidates": [{}]}),
                         "This acquisition is not downloading.")
        self.assertEqual(skip_request_error("downloading", {}), "No eligible fallback source remains.")
        self.assertIsNone(skip_request_error("downloading", {"fallback_candidates": [{"username": "peer"}]}))

    def test_queue_failure_classification_never_retries_uncertain_errors(self):
        def error(status):
            return SimpleNamespace(response=SimpleNamespace(status_code=status))
        for status in (400, 404, 422):
            with self.subTest(status=status):
                self.assertEqual(queue_failure_action(error(status)), "retry_source")
        for status in (401, 403):
            with self.subTest(status=status):
                self.assertEqual(queue_failure_action(error(status)), "fatal")
        for status in (None, 408, 429, 500, 503):
            with self.subTest(status=status):
                self.assertEqual(queue_failure_action(error(status)), "uncertain")
        self.assertEqual(queue_failure_action(OSError("connection reset")), "uncertain")

    def test_fallback_payload_requires_peer_and_named_files_and_preserves_sizes(self):
        candidate = {"username": "peer", "files": [
            {"filename": "folder/one.flac", "size": "100"}, {"filename": "", "size": 99},
            {"size": 12}, {"filename": "two.mp3", "size": None},
        ]}
        self.assertTrue(fallback_candidate_is_usable(candidate))
        self.assertEqual(normalized_candidate_files(candidate), [
            {"filename": "folder/one.flac", "size": 100}, {"filename": "two.mp3", "size": 0},
        ])
        self.assertFalse(fallback_candidate_is_usable({"username": "peer", "files": []}))
        self.assertFalse(fallback_candidate_is_usable({"files": [{"filename": "x.flac"}]}))


if __name__ == "__main__":
    unittest.main()
