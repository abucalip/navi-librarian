"""Route and body tests for the client feedback routes (Server V2 Phase 6 slice 10, D-027)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.feedback as routes
from app.api.dependencies import get_librarian
from intelligence.store import open_store

NOW = 1_700_000_000.0
DAY = 86400.0


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


def uid(n):
    return f"{n:08d}-0000-4000-8000-00000000f00d"


def skip(n, age_days=1, **extra):
    return {"event_id": uid(n), "client": "macos", "kind": "skip", "subject_kind": "track", "subject_id": f"tr-{n}",
            "occurred_at": NOW - age_days * DAY, "played_seconds": 10, "duration_seconds": 200, **extra}


class FeedbackRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        patch = mock.patch.object(routes, "_now", lambda: NOW)
        patch.start()
        self.addCleanup(patch.stop)
        self.client = TestClient(api)

    def post(self, events):
        return self.client.post("/api/feedback/events", json={"events": events})

    def stored(self):
        db = open_store(Path(self.tmp.name) / routes.STORE_FILE)
        try:
            return db.execute("SELECT COUNT(*) FROM state.suppression_events").fetchone()[0]
        finally:
            db.close()

    def test_empty_memory_reads_as_empty_list(self):
        body = self.client.get("/api/insights/suppression").json()
        self.assertEqual(body["entries"], [])
        self.assertEqual(body["total"], 0)
        self.assertIsNone(body["next_offset"])
        self.assertTrue(body["record_only"])

    def test_accepts_stores_and_reads_back(self):
        body = self.post([skip(1), skip(2, age_days=3)]).json()
        self.assertEqual((body["received"], body["inserted"], body["accepted"], body["rejected"]), (2, 2, 2, 0))
        entries = self.client.get("/api/insights/suppression").json()["entries"]
        self.assertEqual([e["subject_id"] for e in entries], ["tr-1", "tr-2"])
        self.assertAlmostEqual(entries[0]["weight"], 2 ** (-1 / 14), places=5)

    def test_replay_changes_nothing_and_reports_duplicates_as_accepted(self):
        batch = [skip(1), skip(2)]
        self.post(batch)
        before = self.client.get("/api/insights/suppression").json()
        body = self.post(batch).json()
        self.assertEqual((body["inserted"], body["accepted"]), (0, 2))
        self.assertTrue(all(r["duplicate"] for r in body["results"]))
        self.assertEqual(self.stored(), 2)
        self.assertEqual(self.client.get("/api/insights/suppression").json(), before)

    def test_malformed_event_is_rejected_without_losing_the_rest(self):
        body = self.post([skip(1), {**skip(2), "event_id": "nope"}, skip(3)]).json()
        self.assertEqual([r["status"] for r in body["results"]], ["accepted", "rejected", "accepted"])
        self.assertEqual(body["results"][1]["reason"], "bad_event_id")
        self.assertEqual(self.stored(), 2)

    def test_repeat_inside_one_batch_is_stored_once(self):
        body = self.post([skip(1), skip(1)]).json()
        self.assertEqual((body["inserted"], body["accepted"]), (1, 2))
        self.assertEqual([r.get("duplicate") for r in body["results"]], [False, True])

    def test_same_id_with_different_payload_is_a_conflict(self):
        self.post([skip(1)])
        body = self.post([skip(1, played_seconds=99)]).json()
        self.assertEqual(body["results"][0], {"index": 0, "status": "rejected", "reason": "event_id_conflict"})
        self.assertEqual(self.stored(), 1)

    def test_batch_over_100_is_refused_whole(self):
        response = self.post([skip(n) for n in range(1, 102)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stored(), 0)

    def test_bad_body_shape_is_422(self):
        self.assertEqual(self.client.post("/api/feedback/events", json={"events": "x"}).status_code, 422)
        self.assertEqual(self.client.post("/api/feedback/events", json={}).status_code, 422)

    def test_non_object_items_are_rejected_individually(self):
        body = self.post([5, skip(1)]).json()
        self.assertEqual(body["results"][0]["reason"], "not_a_mapping")
        self.assertEqual(body["inserted"], 1)

    def test_old_events_are_expired_from_the_view(self):
        self.post([skip(1, age_days=61), skip(2)])
        entries = self.client.get("/api/insights/suppression").json()["entries"]
        self.assertEqual([e["subject_id"] for e in entries], ["tr-2"])

    def test_track_skip_does_not_suppress_album_or_artist(self):
        self.post([skip(1, mbid=None)])
        kinds = {e["subject_kind"] for e in self.client.get("/api/insights/suppression").json()["entries"]}
        self.assertEqual(kinds, {"track"})

    def test_paging(self):
        self.post([skip(n, age_days=n) for n in range(1, 6)])
        first = self.client.get("/api/insights/suppression?limit=2").json()
        self.assertEqual([e["subject_id"] for e in first["entries"]], ["tr-1", "tr-2"])
        self.assertEqual((first["total"], first["next_offset"]), (5, 2))
        last = self.client.get("/api/insights/suppression?limit=2&offset=4").json()
        self.assertEqual([e["subject_id"] for e in last["entries"]], ["tr-5"])
        self.assertIsNone(last["next_offset"])

    def test_bad_paging_is_400(self):
        for query in ("limit=0", "limit=201", "offset=-1"):
            self.assertEqual(self.client.get(f"/api/insights/suppression?{query}").status_code, 400)

    def test_store_failure_is_502_without_event_content(self):
        with mock.patch.object(routes, "build_intake_body", side_effect=RuntimeError("secret-subject")):
            response = self.post([skip(1)])
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-subject", response.text)


if __name__ == "__main__":
    unittest.main()
