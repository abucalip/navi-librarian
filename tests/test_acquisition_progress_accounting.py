"""Direct-import contract tests for watcher progress accounting."""
import unittest

from acquisition_progress_accounting import observe_progress


class AcquisitionProgressAccountingTests(unittest.TestCase):
    def test_increased_bytes_reset_timer_and_clear_stall_marker(self):
        result = observe_progress(12, 8, 10.0, 123.0, 15.0)
        self.assertEqual(result, {
            "last_progress_bytes": 12,
            "last_progress_at": 15.0,
            "stall_detected_at": None,
            "stalled_for": 0.0,
        })

    def test_unchanged_bytes_preserve_timer_and_stall_marker(self):
        result = observe_progress(8, 8, 10.0, 123.0, 135.0)
        self.assertEqual(result, {
            "last_progress_bytes": 8,
            "last_progress_at": 10.0,
            "stall_detected_at": 123.0,
            "stalled_for": 125.0,
        })

    def test_decreased_counter_does_not_reset_progress_timer(self):
        result = observe_progress(3, 8, 10.0, None, 130.0)
        self.assertEqual(result["last_progress_bytes"], 8)
        self.assertEqual(result["last_progress_at"], 10.0)
        self.assertEqual(result["stalled_for"], 120.0)
        self.assertIsNone(result["stall_detected_at"])

    def test_exact_two_minute_boundary_is_preserved(self):
        result = observe_progress(0, 0, 20.0, None, 140.0)
        self.assertEqual(result["stalled_for"], 120.0)


if __name__ == "__main__":
    unittest.main()
