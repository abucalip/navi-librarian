"""The worker's daily metadata-cache prune uses the 400-day cutoff and cannot stop the job-history prune (efficiency P3)."""
import unittest
from types import SimpleNamespace
from unittest import mock

import app.worker as worker
import metadata_cache


class FakeCache:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def prune(self, older_than_seconds):
        self.calls.append(older_than_seconds)
        if self.error is not None:
            raise self.error
        return 7


class PruneMetadataCache(unittest.TestCase):
    def test_prunes_with_the_400_day_cutoff(self):
        cache = FakeCache()
        worker._prune_metadata_cache(SimpleNamespace(_metadata_cache=cache))
        self.assertEqual(cache.calls, [metadata_cache.PRUNE_AFTER_SECONDS])
        self.assertEqual(cache.calls, [400 * 24 * 60 * 60])

    def test_a_librarian_without_a_cache_is_a_no_op(self):
        worker._prune_metadata_cache(SimpleNamespace())  # must not raise


class DailyMaintenance(unittest.TestCase):
    def test_a_failing_metadata_prune_is_logged_by_type_and_job_history_still_ran(self):
        lib = SimpleNamespace(DATA_DIR="unused", _metadata_cache=FakeCache(error=OSError("disk gone")))
        with mock.patch.object(worker, "_maintain") as maintain, \
                self.assertLogs(worker.logger, "ERROR") as logs:
            worker._daily_maintenance(lib)
        maintain.assert_called_once_with("unused")
        self.assertEqual(logs.output, ["ERROR:app.worker:Metadata cache prune failed (OSError)"])

    def test_a_failing_job_history_prune_does_not_stop_the_metadata_prune(self):
        cache = FakeCache()
        lib = SimpleNamespace(DATA_DIR="unused", _metadata_cache=cache)
        with mock.patch.object(worker, "_maintain", side_effect=RuntimeError("locked")), \
                self.assertLogs(worker.logger, "ERROR") as logs:
            worker._daily_maintenance(lib)
        self.assertEqual(cache.calls, [metadata_cache.PRUNE_AFTER_SECONDS])
        self.assertEqual(logs.output, ["ERROR:app.worker:Job history prune failed (RuntimeError)"])


if __name__ == "__main__":
    unittest.main()
