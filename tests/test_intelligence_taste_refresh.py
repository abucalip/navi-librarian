"""Taste refresh: interval, overlap lock, idempotence, failure. Fake listens only, no network."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.insights as insights_routes
import app.api.taste_refresh as routes
from app.api.dependencies import get_librarian
from intelligence.jobs import runner
from intelligence.store import generations, open_store
from intelligence.taste import load_saved_profiles
from intelligence.taste.refresh import JOB, refresh_status, refresh_taste

NOW = 1_000_000.0


def listens(n):
    return lambda: [{"listened_at": NOW - 200000 - i, "track_metadata": {}} for i in range(n)]


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.addCleanup(self.db.close)
        self.clock = Clock()

    def go(self, read, **kw):
        return refresh_taste(self.db, read_listens=read, clock=self.clock, min_interval=100, **kw)

    def test_first_refresh_saves_and_bumps_version(self):
        before = generations.data_versions(self.db).get("insights", 0)
        r = self.go(listens(5))
        self.assertEqual((r.state, r.changed), ("refreshed", True))
        self.assertEqual(load_saved_profiles(self.db)["windows"]["all_time"]["listens"], 5)
        self.assertEqual(generations.data_versions(self.db)["insights"], before + 2)  # profiles row and context row

    def test_refresh_also_saves_context_profiles(self):
        from intelligence.taste.context_persistence import load_saved_context
        self.go(listens(5))
        self.assertEqual(load_saved_context(self.db)["listens"], 5)

    def test_within_interval_is_too_soon_and_reads_nothing(self):
        self.go(listens(5))
        self.clock.t += 40
        read = mock.Mock(return_value=[])
        r = self.go(read)
        self.assertEqual(r.state, "too_soon")
        self.assertEqual(r.retry_after, 60)
        read.assert_not_called()

    def test_replay_after_interval_changes_nothing(self):
        self.go(listens(5))
        version = generations.data_versions(self.db)["insights"]
        self.clock.t += 101
        r = self.go(listens(5))
        self.assertEqual((r.state, r.changed), ("unchanged", False))
        self.assertEqual(generations.data_versions(self.db)["insights"], version)

    def test_failure_keeps_saved_profiles_and_does_not_start_interval(self):
        self.go(listens(5))
        self.clock.t += 101

        def boom():
            raise RuntimeError("store down")
        r = self.go(boom)
        self.assertEqual(r.state, "failed")
        self.assertIn("store down", r.error)
        self.assertEqual(load_saved_profiles(self.db)["windows"]["all_time"]["listens"], 5)
        self.clock.t += 1
        self.assertEqual(self.go(listens(6)).state, "refreshed")

    def test_active_run_blocks_overlap(self):
        runner.enqueue(self.db, JOB)
        self.db.execute("UPDATE job_runs SET state = 'running', started_at = ? WHERE job = ?", (NOW, JOB))
        self.db.commit()
        read = mock.Mock(return_value=[])
        self.assertEqual(self.go(read).state, "skipped")
        read.assert_not_called()

    def test_stale_running_run_is_recovered(self):
        runner.enqueue(self.db, JOB)
        self.db.execute("UPDATE job_runs SET state = 'running', started_at = ? WHERE job = ?", (NOW - 5000, JOB))
        self.db.commit()
        self.assertEqual(self.go(listens(3)).state, "refreshed")

    def test_status_reports_retry_after(self):
        self.assertEqual(refresh_status(self.db, min_interval=100, clock=self.clock)["retry_after"], 0.0)
        self.go(listens(5))
        self.clock.t += 30
        s = refresh_status(self.db, min_interval=100, clock=self.clock)
        self.assertEqual((s["retry_after"], s["running"], s["last_good"]["state"]), (70.0, False, "succeeded"))

    def test_profiles_leave_recommendation_state_alone(self):
        self.go(listens(5))
        tables = {r[0] for r in self.db.execute("SELECT DISTINCT kind FROM insights")}
        self.assertEqual(tables, {"taste_profile", "taste_context"})


class FakeLibrarian:
    username = ""

    def __init__(self, d):
        self.DATA_DIR = Path(d)

    def _listenbrainz_username(self):
        return self.username


class RouteTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.include_router(insights_routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(tmp.name)
        self.client = TestClient(api)

    def test_no_source_answers_without_writing(self):
        body = self.client.post("/api/insights/taste/refresh").json()
        self.assertEqual(body["state"], "no_listens_source")

    def test_username_builds_a_listenbrainz_reader(self):
        lib = FakeLibrarian("x")
        lib.username = "someone"
        with mock.patch.object(routes, "listenbrainz_reader", return_value="reader") as make:
            self.assertEqual(routes.listens_source(lib), "reader")
        self.assertEqual(make.call_args.args, ("someone",))
        self.assertIsNone(routes.listens_source(FakeLibrarian("x")))

    def test_refresh_then_too_soon_then_status(self):
        with mock.patch.object(routes, "listens_source", return_value=lambda: [
                {"listened_at": 1.0 + i, "track_metadata": {}} for i in range(4)]):
            first = self.client.post("/api/insights/taste/refresh").json()
            second = self.client.post("/api/insights/taste/refresh").json()
        self.assertEqual((first["state"], first["changed"]), ("refreshed", True))
        self.assertEqual(second["state"], "too_soon")
        self.assertGreater(second["retry_after"], 0)
        status = self.client.get("/api/insights/taste/refresh/status").json()
        self.assertEqual(status["last_good"]["state"], "succeeded")
        taste = self.client.get("/api/insights/taste").json()
        self.assertIsNotNone(taste["profiles"])

    def test_process_lock_gives_409(self):
        routes._LOCK.acquire()
        try:
            self.assertEqual(self.client.post("/api/insights/taste/refresh").status_code, 409)
        finally:
            routes._LOCK.release()


if __name__ == "__main__":
    unittest.main()
