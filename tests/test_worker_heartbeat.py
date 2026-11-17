"""Worker heartbeat and healthcheck logic (efficiency C3)."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from app.services import worker_heartbeat as hb


def alive_thread():
    release = threading.Event()
    thread = threading.Thread(target=release.wait, daemon=True)
    thread.start()
    return thread, release


class Heartbeat(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_missing_unparseable_old_and_future_stamps_are_not_fresh(self):
        self.assertFalse(hb.is_fresh(self.dir))
        (self.dir / hb.HEARTBEAT_FILE).write_text("junk")
        self.assertFalse(hb.is_fresh(self.dir))
        hb.write_stamp(self.dir, now=1000.0)
        self.assertTrue(hb.is_fresh(self.dir, now=1000.0 + hb.MAX_AGE_SECONDS))
        self.assertFalse(hb.is_fresh(self.dir, now=1000.0 + hb.MAX_AGE_SECONDS + 1))
        self.assertFalse(hb.is_fresh(self.dir, now=900.0))

    def test_writes_while_threads_alive_and_stop_ends_it(self):
        worker, release = alive_thread()
        self.addCleanup(release.set)
        stop = threading.Event()
        thread = hb.start(self.dir, (worker,), stop, every=0.01)
        deadline = time.time() + 5
        while not hb.is_fresh(self.dir) and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(hb.is_fresh(self.dir))
        stop.set()
        thread.join(5)
        self.assertFalse(thread.is_alive())

    def test_never_writes_when_a_scheduler_thread_is_dead(self):
        alive, release = alive_thread()
        self.addCleanup(release.set)
        dead = threading.Thread(target=lambda: None)
        dead.start()
        dead.join()
        stop = threading.Event()
        thread = hb.start(self.dir, (alive, dead), stop, every=0.01)
        time.sleep(0.2)
        stop.set()
        thread.join(5)
        self.assertFalse((self.dir / hb.HEARTBEAT_FILE).exists())

    def test_stamp_stops_advancing_after_a_thread_dies_mid_run(self):
        worker, release = alive_thread()
        stop = threading.Event()
        thread = hb.start(self.dir, (worker,), stop, every=0.01)
        time.sleep(0.1)
        release.set()
        worker.join(5)
        time.sleep(0.1)
        before = (self.dir / hb.HEARTBEAT_FILE).read_text()
        time.sleep(0.2)
        self.assertEqual(before, (self.dir / hb.HEARTBEAT_FILE).read_text())
        stop.set()
        thread.join(5)

    def test_main_reads_the_configured_data_dir(self):
        with mock.patch.dict("os.environ", {"DISCAIR_DATA_DIR": str(self.dir)}):
            self.assertEqual(hb.main(), 1)
            hb.write_stamp(self.dir)
            self.assertEqual(hb.main(), 0)


if __name__ == "__main__":
    unittest.main()
