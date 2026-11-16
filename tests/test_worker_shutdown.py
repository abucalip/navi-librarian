"""Worker shutdown joins its loop threads inside the grace period and before the lock is released (efficiency R5)."""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app.worker as worker


class FakeThread:
    def __init__(self, name, alive=False, on_join=None):
        self.name, self.alive, self.on_join = name, alive, on_join
        self.timeouts = []

    def join(self, timeout=None):
        self.timeouts.append(timeout)
        if self.on_join:
            self.on_join()

    def is_alive(self):
        return self.alive


class WaitForThreads(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_threads_share_one_deadline(self):
        first, second = FakeThread("a"), FakeThread("b")
        worker._wait_for_threads((first, second), grace=2.0)
        self.assertLessEqual(first.timeouts[0], 2.0)
        self.assertGreater(first.timeouts[0], 1.0)
        # One deadline: the second join gets what is left of the first, never a fresh grace period.
        self.assertLessEqual(second.timeouts[0], first.timeouts[0])

    def test_a_thread_still_running_is_logged(self):
        with self.assertLogs(worker.logger, "ERROR") as logs:
            worker._wait_for_threads((FakeThread("insights-refresh", alive=True),), grace=0.0)
        self.assertIn("insights-refresh", logs.output[0])

    def test_lock_is_still_held_while_joining(self):
        lock = worker.acquire_lock(self.dir)
        self.addCleanup(lock.close)
        seen = []
        thread = FakeThread("t", on_join=lambda: seen.append(worker.acquire_lock(self.dir)))
        worker._wait_for_threads((thread,), grace=1.0)
        self.assertEqual(seen, [None])


class MainShutdown(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.lib = SimpleNamespace(DATA_DIR=self.dir)

    def test_main_joins_loops_while_it_still_holds_the_lock_then_releases_it(self):
        stop = threading.Event()
        stop.set()
        seen = []
        insights = FakeThread("insights-refresh", on_join=lambda: seen.append(worker.acquire_lock(self.dir)))
        with mock.patch.object(worker.insights_refresh, "start", return_value=insights) as start, \
                mock.patch.object(worker.library_enrich, "run_forever"):
            self.assertEqual(worker.main(librarian=self.lib, stop=stop), 0)
        start.assert_called_once_with(self.lib, stop)
        self.assertEqual(seen, [None])
        self.assertLessEqual(insights.timeouts[0], worker.SHUTDOWN_GRACE_SECONDS)
        again = worker.acquire_lock(self.dir)
        self.assertIsNotNone(again)
        again.close()


if __name__ == "__main__":
    unittest.main()
