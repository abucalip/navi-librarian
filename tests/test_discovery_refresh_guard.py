"""Cross-process exclusion of discovery list refreshes (efficiency W3, discovery/refresh_guard.py).

A scheduled refresh in the worker and a manual or read-triggered refresh in the web must never refresh the
same list at once. The other process is played by a second store connection (a ``running`` row) or by a real
subprocess. Every store is a temporary file; no provider, Navidrome or real recommendation run is made.
"""
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import navidrome_server as server
from discovery import lens_service, refresh_guard
from intelligence.jobs import enqueue, status
from intelligence.store import ensure_store, open_store

ROOT = Path(__file__).resolve().parents[1]
JOB = refresh_guard.JOB
BUSY_PERSONAL = {"ok": False, "status": "already_running", "list": "personal"}

# The other process: holds the "personal" refresh until the test creates the release file.
HOLDER = """
import sys, time
from pathlib import Path
from discovery import refresh_guard
d = Path(sys.argv[1])
def run():
    (d / "started").write_text("1")
    deadline = time.time() + 20
    while not (d / "release").exists() and time.time() < deadline:
        time.sleep(0.02)
    return {"ok": True}
print(refresh_guard.run_exclusive(d, "personal", run, lambda: {"busy": True}))
"""


class StoreCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.store = self.dir / refresh_guard.STORE_FILE
        ensure_store(self.store)
        self.addCleanup(refresh_guard.set_process, "web")

    def hold(self, scope, started_at=None, process="worker"):
        """A ``running`` row for ``scope``, as the other process leaves it while it refreshes."""
        db = open_store(self.store)
        try:
            run_id, _ = enqueue(db, JOB, scope)
            db.execute("UPDATE job_runs SET state = 'running', started_at = ?, progress = ? WHERE id = ?",
                       (time.time() if started_at is None else started_at, '{"process": "%s"}' % process, run_id))
            db.commit()
        finally:
            db.close()
        return run_id

    def state(self, scope, job=JOB):
        db = open_store(self.store)
        try:
            return status(db, job, scope)
        finally:
            db.close()


class PersonalRefreshes(StoreCase):
    """The web's manual and read-triggered personal refreshes and the worker's scheduled one."""

    def setUp(self):
        super().setUp()
        self.recommend = mock.Mock(return_value={"recommendations": [{"artist": "A", "album": "B"}]})
        self.outcomes, self.writes = [], []
        for patcher in (
            mock.patch.object(server, "DATA_DIR", self.dir),
            mock.patch.object(server, "recommend_new_music", self.recommend),
            mock.patch.object(server, "_discovery_read_list", lambda name: None),
            mock.patch.object(server, "_discovery_write_list", lambda name, payload: self.writes.append(name)),
            mock.patch.object(server.discovery_store, "record_discovery_refresh_outcome",
                              lambda path, **outcome: self.outcomes.append(outcome)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_a_manual_refresh_while_the_worker_refreshes_the_list_runs_nothing(self):
        self.hold("personal")
        self.assertEqual(server._discovery_refresh_personal(20), BUSY_PERSONAL)
        self.recommend.assert_not_called()
        self.assertEqual(self.writes, [])
        # The answer and the outcome row are the ones the in-process lock already gave.
        self.assertEqual([o["status"] for o in self.outcomes], ["already_running"])
        self.assertEqual(self.outcomes[0]["origin"], "manual")

    def test_a_read_triggered_refresh_is_guarded_too(self):
        self.hold("personal")
        self.assertEqual(server._discovery_refresh_personal(20, origin="read"), BUSY_PERSONAL)
        self.recommend.assert_not_called()

    def test_a_scheduled_refresh_while_the_web_refreshes_the_list_runs_nothing(self):
        self.hold("personal", process="web")
        self.assertEqual(server._discovery_scheduler_refresh_one("personal"), BUSY_PERSONAL)
        self.recommend.assert_not_called()
        self.assertEqual(self.outcomes[0]["origin"], "scheduler")

    def test_another_list_running_does_not_block_this_one(self):
        self.hold("classics")
        result = server._discovery_refresh_personal(20)
        self.assertTrue(result["ok"])
        self.assertEqual(self.writes, ["personal"])

    def test_the_scheduled_refresh_keeps_its_origin_and_records_a_finished_run(self):
        refresh_guard.set_process("worker")
        result = server._discovery_scheduler_refresh_one("personal")
        self.assertTrue(result["ok"])
        self.assertEqual(self.recommend.call_args.kwargs["_refresh_origin"], "scheduler")
        run = self.state("personal")
        self.assertEqual(run["state"], "succeeded")
        self.assertEqual(run["progress"], {"process": "worker"})

    def test_a_raising_refresh_still_raises_and_the_run_stores_only_the_error_type(self):
        self.recommend.side_effect = ValueError("http://private.example/secret")
        with self.assertRaises(ValueError):
            server._discovery_refresh_personal(20)
        run = self.state("personal")
        self.assertEqual(run["state"], "failed")
        self.assertNotIn("private", run["error"])
        self.assertIn("ValueError", run["error"])
        # The list is free again afterwards.
        self.recommend.side_effect = None
        self.assertTrue(server._discovery_refresh_personal(20)["ok"])

    def test_a_refresh_in_another_process_blocks_the_manual_refresh_until_it_ends(self):
        holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(self.dir)], cwd=ROOT,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: holder.poll() is None and holder.kill())
        deadline = time.time() + 20
        while not (self.dir / "started").exists():
            self.assertIsNone(holder.poll(), holder.stderr.read() if holder.poll() is not None else "")
            self.assertLess(time.time(), deadline, "the other process did not start its refresh")
            time.sleep(0.02)
        self.assertEqual(server._discovery_refresh_personal(20), BUSY_PERSONAL)
        self.recommend.assert_not_called()
        (self.dir / "release").write_text("1")
        out, err = holder.communicate(timeout=20)
        self.assertEqual(holder.returncode, 0, err)
        self.assertIn("'ok': True", out)
        self.assertTrue(server._discovery_refresh_personal(20)["ok"])
        self.recommend.assert_called_once()


class OtherListRefreshes(StoreCase):
    def setUp(self):
        super().setUp()
        self.built = []
        for patcher in (
            mock.patch.object(server, "DATA_DIR", self.dir),
            mock.patch.object(server, "_build_classics_list", lambda: self.built.append("classics") or {"items": []}),
            mock.patch.object(server, "_discovery_write_list", lambda name, payload: None),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_a_running_list_gives_the_existing_busy_answer_and_builds_nothing(self):
        self.hold("classics")
        self.assertEqual(server._discovery_refresh_other("classics"),
                         {"ok": False, "status": "already_running", "list": "classics"})
        self.assertEqual(self.built, [])

    def test_a_free_list_is_built_once(self):
        result = server._discovery_refresh_other("classics")
        self.assertTrue(result["ok"])
        self.assertEqual(self.built, ["classics"])
        self.assertEqual(self.state("classics")["state"], "succeeded")

    def test_an_unknown_list_keeps_its_answer_and_queues_no_run(self):
        self.assertEqual(server._discovery_refresh_other("nope"), {"ok": False, "error": "Unknown discovery list"})
        self.assertIsNone(self.state("nope"))

    def test_the_manual_route_still_answers_started_while_the_list_runs(self):
        self.hold("classics")
        started = []
        with mock.patch("threading.Thread") as thread:
            thread.return_value.start.side_effect = lambda: started.append(thread.call_args.kwargs["target"])
            answer = server.discovery_refresh_list("classics")
        self.assertIn('"status": "started"', answer)
        self.assertEqual(started[0]("classics"), {"ok": False, "status": "already_running", "list": "classics"})
        self.assertEqual(self.built, [])


class LensRefreshes(StoreCase):
    def test_a_running_lens_refresh_gives_the_existing_busy_answer_and_runs_nothing(self):
        self.hold(lens_service.LENS_SCOPE)
        with mock.patch.object(lens_service, "refresh") as refresh:
            result = lens_service.refresh_exclusive(SimpleNamespace(DATA_DIR=self.dir))
        self.assertEqual(result, {"ok": False, "status": "already_running", "list": "lens_lists"})
        refresh.assert_not_called()

    def test_the_manual_lens_refresh_goes_through_the_guard(self):
        self.hold(lens_service.LENS_SCOPE)
        with mock.patch.object(lens_service, "refresh") as refresh:
            lens_service.start_refresh(SimpleNamespace(DATA_DIR=self.dir)).join(5)
        refresh.assert_not_called()

    def test_a_free_lens_refresh_runs(self):
        librarian = SimpleNamespace(DATA_DIR=self.dir)
        with mock.patch.object(lens_service, "refresh", return_value={"ok": True}) as refresh:
            self.assertEqual(lens_service.refresh_exclusive(librarian), {"ok": True})
        refresh.assert_called_once_with(librarian)


class GuardMechanics(StoreCase):
    def test_threads_with_separate_locks_still_refresh_a_list_once(self):
        entered, release, ran = threading.Event(), threading.Event(), []

        def slow():
            ran.append("first")
            entered.set()
            release.wait(5)
            return "first"

        first = threading.Thread(target=lambda: refresh_guard.run_exclusive(self.dir, "personal", slow, lambda: "busy"))
        first.start()
        self.assertTrue(entered.wait(5))
        second = refresh_guard.run_exclusive(self.dir, "personal", lambda: ran.append("second"), lambda: "busy")
        release.set()
        first.join(5)
        self.assertEqual(second, "busy")
        self.assertEqual(ran, ["first"])

    def test_a_stale_running_row_is_failed_and_the_refresh_runs(self):
        old = self.hold("personal", started_at=time.time() - refresh_guard.STALE_AFTER_SECONDS - 60)
        self.assertEqual(refresh_guard.run_exclusive(self.dir, "personal", lambda: "ran", lambda: "busy"), "ran")
        db = open_store(self.store)
        try:
            self.assertEqual(db.execute("SELECT state FROM job_runs WHERE id = ?", (old,)).fetchone()[0], "failed")
        finally:
            db.close()

    def test_a_recent_running_row_is_left_alone(self):
        self.hold("personal", started_at=time.time() - refresh_guard.STALE_AFTER_SECONDS + 600)
        self.assertEqual(refresh_guard.run_exclusive(self.dir, "personal", lambda: "ran", lambda: "busy"), "busy")
        self.assertEqual(self.state("personal")["state"], "running")

    def test_the_stale_rule_leaves_other_jobs_alone(self):
        db = open_store(self.store)
        try:
            run_id, _ = enqueue(db, "musicbrainz_slice_import")
            db.execute("UPDATE job_runs SET state = 'running', started_at = 1 WHERE id = ?", (run_id,))
            db.commit()
        finally:
            db.close()
        refresh_guard.run_exclusive(self.dir, "personal", lambda: "ran", lambda: "busy")
        self.assertEqual(self.state("", job="musicbrainz_slice_import")["state"], "running")

    def test_restart_recovery_fails_only_this_process_rows_of_this_job(self):
        self.hold("personal", process="worker")
        self.hold("classics", process="web")
        db = open_store(self.store)
        try:
            other, _ = enqueue(db, "taste_refresh")
            db.execute("UPDATE job_runs SET state = 'running', progress = '{\"process\": \"worker\"}' WHERE id = ?",
                       (other,))
            db.commit()
        finally:
            db.close()
        self.assertEqual(refresh_guard.recover_process(self.store, "worker"), 1)
        self.assertEqual(self.state("personal")["state"], "failed")
        self.assertEqual(self.state("classics")["state"], "running")
        self.assertEqual(self.state("", job="taste_refresh")["state"], "running")
        self.assertEqual(refresh_guard.run_exclusive(self.dir, "personal", lambda: "ran", lambda: "busy"), "ran")

    def test_without_a_store_the_refresh_runs_and_no_file_is_created(self):
        empty = self.dir / "empty"
        empty.mkdir()
        self.assertEqual(refresh_guard.run_exclusive(empty, "personal", lambda: "ran", lambda: "busy"), "ran")
        self.assertEqual(refresh_guard.run_exclusive(None, "personal", lambda: "ran", lambda: "busy"), "ran")
        self.assertEqual(list(empty.iterdir()), [])
        self.assertEqual(refresh_guard.recover_process(empty / refresh_guard.STORE_FILE, "web"), 0)
        self.assertEqual(list(empty.iterdir()), [])

    def test_an_unmigrated_store_runs_the_refresh_unguarded(self):
        bare = self.dir / "bare"
        bare.mkdir()
        (bare / refresh_guard.STORE_FILE).write_bytes(b"")
        self.assertEqual(refresh_guard.run_exclusive(bare, "personal", lambda: "ran", lambda: "busy"), "ran")


if __name__ == "__main__":
    unittest.main()
