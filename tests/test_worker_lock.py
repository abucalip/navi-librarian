import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app.worker as worker
from intelligence.jobs import enqueue, status
from intelligence.store import open_store


class WorkerLockTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.lib = SimpleNamespace(DATA_DIR=self.dir)

    def test_lock_is_exclusive_and_released_on_close(self):
        first = worker.acquire_lock(self.dir)
        self.assertIsNotNone(first)
        self.assertIsNone(worker.acquire_lock(self.dir))
        first.close()
        again = worker.acquire_lock(self.dir)
        self.assertIsNotNone(again)
        again.close()

    def test_second_worker_in_another_process_exits_nonzero_quickly(self):
        first = worker.acquire_lock(self.dir)
        self.addCleanup(first.close)
        code = ("import sys; from pathlib import Path; from types import SimpleNamespace as N; import app.worker as w; "
                "sys.exit(w.main(librarian=N(DATA_DIR=Path(sys.argv[1]))))")
        done = subprocess.run([sys.executable, "-c", code, str(self.dir)], timeout=20, capture_output=True,
                              cwd=Path(__file__).parent.parent)
        self.assertEqual(done.returncode, 1)

    def test_main_returns_1_without_starting_jobs_when_lock_is_held(self):
        held = worker.acquire_lock(self.dir)
        self.addCleanup(held.close)
        with mock.patch.object(worker.insights_refresh, "start") as insights:
            self.assertEqual(worker.main(librarian=self.lib, stop=threading.Event()), 1)
        insights.assert_not_called()

    def test_start_requeues_worker_jobs_fails_slice_and_leaves_web_jobs(self):
        db = open_store(self.dir / worker.STORE_FILE)
        ids = {}
        for name in (worker.API_FILL_JOB, worker.SLICE_JOB, "taste_refresh"):
            ids[name], _ = enqueue(db, name)
            db.execute("UPDATE job_runs SET state = 'running' WHERE id = ?", (ids[name],))
        db.commit()
        db.close()
        stop = threading.Event()
        stop.set()
        with mock.patch.object(worker.insights_refresh, "start"), \
                mock.patch.object(worker.library_enrich, "run_forever"):
            self.assertEqual(worker.main(librarian=self.lib, stop=stop), 0)
        db = open_store(self.dir / worker.STORE_FILE)
        self.addCleanup(db.close)
        self.assertEqual(status(db, worker.API_FILL_JOB)["state"], "queued")
        self.assertEqual(status(db, worker.SLICE_JOB)["state"], "failed")
        self.assertEqual(status(db, "taste_refresh")["state"], "running")

    def test_lock_is_released_when_main_returns(self):
        stop = threading.Event()
        stop.set()
        with mock.patch.object(worker.insights_refresh, "start"), mock.patch.object(worker.library_enrich, "run_forever"):
            worker.main(librarian=self.lib, stop=stop)
        again = worker.acquire_lock(self.dir)
        self.assertIsNotNone(again)
        again.close()


if __name__ == "__main__":
    unittest.main()
