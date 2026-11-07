"""Routes for the manual popularity fill (Server V2 Phase 6 slice 18). Fake post only, no network."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.popularity as routes
from app.api.dependencies import get_librarian
from intelligence.store import open_store
from intelligence.store import repositories as repo
from intelligence.taste import popularity_persistence as pp


def mbid(n):
    return f"00000000-0000-4000-8000-{n:012d}"


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.text = status, body, "x" if body is not None else ""

    def json(self):
        return self._body


def ok_post(calls):
    def post(url, json, headers, timeout):
        calls.append({"n": len(json["artist_mbids"]), "headers": headers})
        return Resp(200, [{"artist_mbid": m, "total_listen_count": 7} for m in json["artist_mbids"]])
    return post


class PopularityRoutes(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp)
        self.client = TestClient(api)
        self.db = open_store(Path(self.tmp) / routes.STORE_FILE)
        self.addCleanup(self.db.close)
        sleep = mock.patch("app.api.popularity.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def add_artists(self, count):
        for n in range(1, count + 1):
            repo.upsert_entity(self.db, "artist", f"A{n}", mbid=mbid(n), navidrome_id=None, owned=True)
        self.db.commit()

    def fill(self, post, body=None):
        with mock.patch("app.api.popularity.httpx.post", post):
            return self.client.post("/api/insights/popularity/fill", json=body)

    def test_success_saves_figures_and_reports_succeeded(self):
        self.add_artists(3)
        calls = []
        r = self.fill(ok_post(calls))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual((body["state"], body["max_requests"]), ("succeeded", 5))
        self.assertEqual(calls[0]["n"], 3)
        self.assertEqual(pp.load_popularity(self.db), {mbid(1): 7, mbid(2): 7, mbid(3): 7})

    def test_resume_continues_a_queued_run(self):
        self.add_artists(250)
        calls = []
        first = self.fill(ok_post(calls), {"max_requests": 1})
        self.assertEqual(first.json()["state"], "queued")
        second = self.fill(ok_post(calls), {"max_requests": 5})
        self.assertEqual(second.json()["state"], "succeeded")
        self.assertEqual(len(pp.load_popularity(self.db)), 250)

    def test_failure_keeps_saved_figures(self):
        self.add_artists(2)
        pp.save_popularity(self.db, {mbid(1): 42}, 1_000.0)  # old enough to be pending again
        r = self.fill(lambda *a, **k: Resp(500))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["state"], "failed")
        self.assertEqual(pp.load_popularity(self.db)[mbid(1)], 42)

    def test_overlap_is_refused_with_409(self):
        self.add_artists(1)
        calls = []
        self.assertTrue(routes._LOCK.acquire(blocking=False))
        try:
            r = self.fill(ok_post(calls))
        finally:
            routes._LOCK.release()
        self.assertEqual(r.status_code, 409)
        self.assertEqual(calls, [])

    def test_cap_is_enforced(self):
        self.add_artists(2100)  # 21 batches of 100 would be needed
        calls = []
        r = self.fill(ok_post(calls), {"max_requests": 50})
        self.assertEqual(r.json()["max_requests"], 20)
        self.assertEqual(len(calls), 20)
        self.assertEqual(r.json()["state"], "queued")

    def test_invalid_max_requests_is_rejected(self):
        self.add_artists(1)
        for bad in (0, -1, "5", True, 2.5):
            with self.subTest(bad=bad):
                r = self.fill(lambda *a, **k: self.fail("no request expected"), {"max_requests": bad})
                self.assertEqual(r.status_code, 422)

    def test_headers_carry_user_agent_and_token_from_config_env_only(self):
        with tempfile.TemporaryDirectory() as cwd:
            (Path(cwd) / "config.env").write_text("LISTENBRAINZ_TOKEN=test-token-123\n")
            with mock.patch.object(routes.Path, "cwd", return_value=Path(cwd)):
                headers = routes._headers()
        self.assertEqual(headers["Authorization"], "Token test-token-123")
        self.assertIn("Discair/", headers["User-Agent"])
        with tempfile.TemporaryDirectory() as cwd:
            with mock.patch.object(routes.Path, "cwd", return_value=Path(cwd)):
                self.assertNotIn("Authorization", routes._headers())

    def test_status_reports_last_run_and_last_good(self):
        self.add_artists(1)
        self.fill(ok_post([]))
        body = self.client.get("/api/insights/popularity/status").json()
        self.assertEqual(body["status"]["state"], "succeeded")
        self.assertEqual(body["last_good"]["state"], "succeeded")
        self.assertFalse(body["running"])

    def test_status_running_comes_from_persisted_job_state(self):
        self.add_artists(1)
        self.fill(ok_post([]))
        self.assertFalse(routes._LOCK.locked())
        self.db.execute("UPDATE job_runs SET state = 'running' WHERE job = ?", (routes.JOB,))
        self.db.commit()
        body = self.client.get("/api/insights/popularity/status").json()
        self.assertTrue(body["running"])
        self.assertEqual(body["status"]["state"], "running")


if __name__ == "__main__":
    unittest.main()
