"""Insight lens refresh status (redesign D3): both lens jobs, newest and last good, retry_after, route.

Job runs are written through the real job runner on an in-memory store; no provider call is made.
"""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_librarian
from app.api.insight_lens_status import router as status_router
from app.services.insights_refresh import CHECK_SECONDS
from intelligence.insights.refresh_status import LENS_JOBS, lens_refresh_status
from intelligence.jobs import runner
from intelligence.store import open_store

GEMS, PROVIDER = LENS_JOBS
INTERVAL = 100.0


def succeed(ctx):
    return True


def fail(ctx):
    raise RuntimeError("provider down")


class Clock:
    def __init__(self, t=1_000.0):
        self.t = t

    def __call__(self):
        return self.t


class LensRefreshStatusTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.addCleanup(self.db.close)
        self.clock = Clock()

    def run_at(self, job, fn, t):
        return runner.run_job(self.db, job, fn, clock=lambda: t)

    def status(self):
        return lens_refresh_status(self.db, min_interval=INTERVAL, clock=self.clock)

    def test_empty_store_has_no_run_and_is_due_now(self):
        body = self.status()
        self.assertEqual((body["status"], body["last_good"], body["running"]), (None, None, False))
        self.assertEqual((body["min_interval"], body["retry_after"]), (INTERVAL, 0.0))

    def test_reports_last_good_and_next_due_from_its_finish(self):
        self.run_at(GEMS, succeed, 1_000.0)
        self.clock.t = 1_030.0
        body = self.status()
        self.assertEqual(body["last_good"]["job"], GEMS)
        self.assertEqual(body["last_good"]["state"], "succeeded")
        self.assertEqual(body["retry_after"], 70.0)  # finished at 1000, due at 1100, now 1030

    def test_retry_after_is_zero_once_due(self):
        self.run_at(PROVIDER, succeed, 1_000.0)
        self.clock.t = 5_000.0
        self.assertEqual(self.status()["retry_after"], 0.0)

    def test_newest_run_comes_from_either_job_and_last_good_stays_on_success(self):
        self.run_at(GEMS, succeed, 1_000.0)
        self.run_at(PROVIDER, fail, 1_500.0)
        body = self.status()
        self.assertEqual((body["status"]["job"], body["status"]["state"]), (PROVIDER, "failed"))
        self.assertEqual(body["last_good"]["job"], GEMS)
        self.assertEqual(body["retry_after"], INTERVAL)  # the gems success finished at 1000, now is 1000

    def test_newest_good_run_wins_over_an_older_one(self):
        self.run_at(GEMS, succeed, 1_000.0)
        self.run_at(PROVIDER, succeed, 1_200.0)
        self.assertEqual(self.status()["last_good"]["job"], PROVIDER)

    def test_running_run_is_reported(self):
        run_id, _ = runner.enqueue(self.db, PROVIDER)
        with self.db:
            self.db.execute("UPDATE job_runs SET state = 'running', started_at = 1000 WHERE id = ?", (run_id,))
        body = self.status()
        self.assertTrue(body["running"])
        self.assertEqual(body["status"]["state"], "running")

    def test_other_jobs_are_ignored(self):
        self.run_at("taste_refresh", succeed, 1_000.0)
        body = self.status()
        self.assertEqual((body["status"], body["last_good"]), (None, None))

    def test_loop_cadence_is_six_hours(self):
        self.assertEqual(CHECK_SECONDS, 6 * 3600)


class RouteTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data_dir = Path(tmp.name)

        class FakeLibrarian:
            DATA_DIR = self.data_dir

        api = FastAPI()
        api.include_router(status_router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian()
        self.client = TestClient(api)

    def test_route_answers_read_only_shape_on_empty_store(self):
        body = self.client.get("/api/insights/refresh/status").json()
        self.assertEqual(set(body), {"status", "last_good", "running", "min_interval", "retry_after"})
        self.assertEqual(body["min_interval"], CHECK_SECONDS)
        self.assertEqual((body["status"], body["last_good"], body["retry_after"]), (None, None, 0.0))

    def test_route_reports_a_saved_run(self):
        db = open_store(self.data_dir / "intelligence.sqlite3")
        try:
            runner.run_job(db, GEMS, succeed)
        finally:
            db.close()
        body = self.client.get("/api/insights/refresh/status").json()
        self.assertEqual(body["last_good"]["job"], GEMS)
        self.assertEqual(body["status"]["state"], "succeeded")


if __name__ == "__main__":
    unittest.main()
