import tempfile
import unittest
from pathlib import Path

from intelligence.jobs import (
    cancel, enqueue, last_good, list_runs, prune_finished, recover_stale, run_job, status,
)
from intelligence.store import generations, open_store


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class JobTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = open_store(Path(self.temp_dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)
        self.clock = Clock()


class EnqueueTests(JobTestCase):
    def test_second_enqueue_returns_existing_run(self):
        a, created_a = enqueue(self.db, "health")
        b, created_b = enqueue(self.db, "health")
        self.assertEqual(a, b)
        self.assertTrue(created_a)
        self.assertFalse(created_b)

    def test_different_scopes_are_separate_runs(self):
        a, _ = enqueue(self.db, "health", "album:1")
        b, created = enqueue(self.db, "health", "album:2")
        self.assertNotEqual(a, b)
        self.assertTrue(created)

    def test_blank_job_name_rejected(self):
        with self.assertRaises(ValueError):
            enqueue(self.db, " ")

    def test_new_run_after_finish(self):
        first = run_job(self.db, "health", lambda ctx: True, clock=self.clock)
        second = run_job(self.db, "health", lambda ctx: True, clock=self.clock)
        self.assertNotEqual(first.run_id, second.run_id)


class RunTests(JobTestCase):
    def test_success_records_state_and_bumps_version(self):
        def job(ctx):
            ctx.checkpoint({"done": 3}, items=3)
            return True

        result = run_job(self.db, "health", job, resource="health", clock=self.clock)
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(status(self.db, "health")["progress"], {"done": 3})
        self.assertEqual(status(self.db, "health")["finished_at"], 1000.0)
        self.assertEqual(generations.data_version(self.db, "health"), 1)

    def test_failure_keeps_last_good_and_version(self):
        run_job(self.db, "health", lambda ctx: True, resource="health", clock=self.clock)
        good = last_good(self.db, "health")

        def boom(ctx):
            raise RuntimeError("provider down " + "x" * 2000)

        result = run_job(self.db, "health", boom, resource="health", clock=self.clock)
        self.assertEqual(result.state, "failed")
        self.assertLessEqual(len(result.error), 500)
        self.assertEqual(status(self.db, "health")["state"], "failed")
        self.assertEqual(last_good(self.db, "health")["id"], good["id"])
        self.assertEqual(generations.data_version(self.db, "health"), 1)

    def test_failed_run_can_be_retried(self):
        run_job(self.db, "j", lambda ctx: 1 / 0, clock=self.clock)
        self.assertEqual(run_job(self.db, "j", lambda ctx: True, clock=self.clock).state, "succeeded")

    def test_item_budget_stops_early_and_resumes(self):
        items = list(range(10))

        def job(ctx):
            i = ctx.progress.get("next", 0)
            while i < len(items) and ctx.has_budget():
                i += 1
                ctx.checkpoint({"next": i}, items=1)
            return i >= len(items)

        r1 = run_job(self.db, "j", job, resource="r", max_items=4, clock=self.clock)
        self.assertEqual((r1.state, r1.progress), ("queued", {"next": 4}))
        self.assertEqual(generations.data_version(self.db, "r"), 0)
        r2 = run_job(self.db, "j", job, resource="r", max_items=4, clock=self.clock)
        self.assertEqual(r2.run_id, r1.run_id)
        self.assertEqual(r2.progress, {"next": 8})
        r3 = run_job(self.db, "j", job, resource="r", max_items=4, clock=self.clock)
        self.assertEqual((r3.state, r3.progress), ("succeeded", {"next": 10}))
        self.assertEqual(generations.data_version(self.db, "r"), 1)

    def test_time_budget(self):
        def job(ctx):
            self.clock.t += 5
            return ctx.has_budget()

        self.assertEqual(run_job(self.db, "j", job, max_seconds=3, clock=self.clock).state, "queued")

    def test_already_running_is_skipped(self):
        run_id, _ = enqueue(self.db, "j")
        self.db.execute("UPDATE job_runs SET state = 'running' WHERE id = ?", (run_id,))
        called = []
        result = run_job(self.db, "j", lambda ctx: called.append(1) or True, clock=self.clock)
        self.assertEqual(result.state, "skipped")
        self.assertEqual(called, [])

    def test_cancel_during_run(self):
        def job(ctx):
            cancel(self.db, ctx.run_id)
            return ctx.has_budget()

        result = run_job(self.db, "j", job, resource="r", clock=self.clock)
        self.assertEqual(result.state, "cancelled")
        self.assertEqual(status(self.db, "j")["state"], "cancelled")
        self.assertEqual(generations.data_version(self.db, "r"), 0)

    def test_cancel_then_raise_stays_cancelled(self):
        def job(ctx):
            cancel(self.db, ctx.run_id)
            raise RuntimeError("late")

        self.assertEqual(run_job(self.db, "j", job, clock=self.clock).state, "cancelled")

    def test_cancel_queued_and_finished(self):
        run_id, _ = enqueue(self.db, "j")
        self.assertTrue(cancel(self.db, run_id))
        self.assertFalse(cancel(self.db, run_id))

    def test_runs_are_stamped_with_generation(self):
        generations.bump_generation(self.db)
        run_job(self.db, "j", lambda ctx: True, clock=self.clock)
        self.assertEqual(status(self.db, "j")["generation"], 2)


class RecoveryAndRetentionTests(JobTestCase):
    def test_recover_stale_requeues_crashed_run_with_progress(self):
        run_id, _ = enqueue(self.db, "j")
        self.db.execute(
            "UPDATE job_runs SET state = 'running', started_at = 100, progress = '{\"next\": 2}' WHERE id = ?",
            (run_id,),
        )
        self.assertEqual(recover_stale(self.db, now=1000, older_than=3600), 0)
        self.assertEqual(recover_stale(self.db, now=5000, older_than=3600), 1)
        result = run_job(self.db, "j", lambda ctx: ctx.progress == {"next": 2}, clock=self.clock)
        self.assertEqual((result.run_id, result.state), (run_id, "succeeded"))

    def test_list_runs_filters_and_orders(self):
        run_job(self.db, "a", lambda ctx: True, clock=self.clock)
        run_job(self.db, "b", lambda ctx: True, clock=self.clock)
        self.assertEqual([r["job"] for r in list_runs(self.db)], ["b", "a"])
        self.assertEqual([r["job"] for r in list_runs(self.db, "a")], ["a"])

    def test_status_of_unknown_job_is_none(self):
        self.assertIsNone(status(self.db, "nope"))
        self.assertIsNone(last_good(self.db, "nope"))

    def test_prune_keeps_newest_and_last_good(self):
        run_job(self.db, "j", lambda ctx: True, clock=self.clock)
        good = last_good(self.db, "j")["id"]
        for _ in range(4):
            run_job(self.db, "j", lambda ctx: 1 / 0, clock=self.clock)
        self.assertEqual(prune_finished(self.db, keep=2), 2)
        ids = {r["id"] for r in list_runs(self.db)}
        self.assertIn(good, ids)
        self.assertEqual(len(ids), 3)

    def test_prune_leaves_active_runs(self):
        run_id, _ = enqueue(self.db, "j")
        prune_finished(self.db, keep=0)
        self.assertEqual(status(self.db, "j")["id"], run_id)


if __name__ == "__main__":
    unittest.main()
