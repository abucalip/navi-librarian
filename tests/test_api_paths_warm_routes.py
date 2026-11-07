"""Routes for the manual path cache warm-up (Server V2 Phase 7 carry-over)."""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.paths_warm as routes
from app.api.dependencies import get_librarian
from intelligence.store import open_store
from intelligence.store import repositories as repo


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class PathsWarmRoutes(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(tmp.name)
        self.client = TestClient(api)
        db = open_store(Path(tmp.name) / routes.STORE_FILE)
        repo.upsert_entity(db, "artist", "A", mbid="e0000000-0000-0000-0000-000000000001", owned=True)
        db.commit()
        db.close()

    def test_warm_then_status(self):
        r = self.client.post("/api/knowledge/paths/warm", json={"kinds": ["label_path"], "max_seconds": 30})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["state"], "succeeded")
        self.assertEqual(r.json()["kinds"], ["label_path"])
        s = self.client.get("/api/knowledge/paths/warm/status").json()
        self.assertFalse(s["running"])
        self.assertEqual(s["status"]["state"], "succeeded")

    def test_empty_body_uses_defaults(self):
        r = self.client.post("/api/knowledge/paths/warm")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["kinds"]), 5)

    def test_bad_arguments_are_422(self):
        for body in ({"max_seconds": 0}, {"max_seconds": True}, {"kinds": []}, {"kinds": ["nope"]}):
            self.assertEqual(self.client.post("/api/knowledge/paths/warm", json=body).status_code, 422, body)

    def test_busy_is_409(self):
        routes._LOCK.acquire()
        try:
            self.assertEqual(self.client.post("/api/knowledge/paths/warm").status_code, 409)
        finally:
            routes._LOCK.release()


if __name__ == "__main__":
    unittest.main()
