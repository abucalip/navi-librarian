"""Direct regression tests for per-acquisition progress snapshots."""
import unittest

from acquisition_progress_snapshots import ProgressSnapshots


class ProgressSnapshotsTests(unittest.TestCase):
    def test_first_sample_has_no_prior_and_second_sample_reuses_prior_shape(self):
        snapshots = ProgressSnapshots()
        seen = []

        def estimator(current, prior, now):
            seen.append((current, prior, now))
            return len(seen)

        first = {"track.flac": 100}
        second = {"track.flac": 250}
        key = ("artist", "album", "peer")
        self.assertEqual(snapshots.estimate(key, first, 1.0, estimator), 1)
        self.assertEqual(snapshots.estimate(key, second, 2.5, estimator), 2)
        self.assertEqual(seen[0], (first, None, 1.0))
        self.assertEqual(seen[1], (second, {"at": 1.0, "files": first}, 2.5))

    def test_snapshots_are_isolated_by_key(self):
        snapshots = ProgressSnapshots()
        seen = []

        def estimator(current, prior, now):
            seen.append(prior)
            return 0

        snapshots.estimate("album-a", {"a.flac": 10}, 1.0, estimator)
        snapshots.estimate("album-b", {"b.flac": 20}, 2.0, estimator)
        snapshots.estimate("album-a", {"a.flac": 30}, 3.0, estimator)
        self.assertIsNone(seen[0])
        self.assertIsNone(seen[1])
        self.assertEqual(seen[2], {"at": 1.0, "files": {"a.flac": 10}})

    def test_estimator_exception_does_not_drop_recorded_current_snapshot(self):
        snapshots = ProgressSnapshots()

        def failing(*args):
            raise RuntimeError("expected")

        with self.assertRaisesRegex(RuntimeError, "expected"):
            snapshots.estimate("album", {"a.flac": 12}, 4.0, failing)

        seen = []
        snapshots.estimate(
            "album", {"a.flac": 18}, 5.0,
            lambda current, prior, now: seen.append(prior) or 1,
        )
        self.assertEqual(seen, [{"at": 4.0, "files": {"a.flac": 12}}])
