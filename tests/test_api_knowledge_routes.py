"""Route tests for /api/knowledge/* (Server V2 Phase 4): lookups, 404, validation, read-only."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.knowledge as routes
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.store import open_store
from intelligence.store import repositories as repo


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class KnowledgeRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        self.artist = repo.upsert_entity(db, "artist", "Alpha", mbid="a-gid", owned=True)[0]
        self.label = repo.upsert_entity(db, "label", "Lab", mbid="l-gid")[0]
        self.work = repo.upsert_entity(db, "work", "Song", mbid="w-gid")[0]
        self.group = repo.upsert_entity(db, "release_group", "Record", mbid="rg-gid", owned=True)[0]
        self.recording = repo.upsert_entity(db, "recording", "Take", mbid="r-gid")[0]
        db.close()

    def test_each_page_answers_for_a_known_entity(self):
        for path, params in (
            ("/api/knowledge/person", {"mbid": "a-gid"}),
            ("/api/knowledge/label", {"mbid": "l-gid"}),
            ("/api/knowledge/work", {"mbid": "w-gid"}),
            ("/api/knowledge/album", {"mbid": "rg-gid", "type": "release_group"}),
            ("/api/knowledge/recording-works", {"mbid": "r-gid"}),
        ):
            with self.subTest(path=path):
                response = self.client.get(path, params=params)
                self.assertEqual(response.status_code, 200, response.text)

    def test_unknown_entity_is_404(self):
        for path in ("person", "label", "work", "album", "recording-works"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"/api/knowledge/{path}", params={"mbid": "nope"}).status_code, 404)

    def test_missing_identifier_is_400(self):
        for path in ("person", "album", "recording-works"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"/api/knowledge/{path}").status_code, 400)

    def test_label_and_work_need_an_mbid(self):
        for path in ("label", "work"):
            self.assertEqual(self.client.get(f"/api/knowledge/{path}").status_code, 422)

    def test_bad_type_and_limit_are_400_or_422(self):
        self.assertEqual(self.client.get("/api/knowledge/album", params={"mbid": "x", "type": "track"}).status_code, 400)
        self.assertEqual(self.client.get("/api/knowledge/person", params={"mbid": "x", "type": "label"}).status_code, 400)
        self.assertEqual(self.client.get("/api/knowledge/person", params={"mbid": "a-gid", "limit": 0}).status_code, 422)
        self.assertEqual(self.client.get("/api/knowledge/person", params={"mbid": "a-gid", "limit": 501}).status_code, 422)

    def test_store_failure_is_502(self):
        with mock.patch.object(routes, "open_store", side_effect=OSError("boom")):
            self.assertEqual(self.client.get("/api/knowledge/label", params={"mbid": "l-gid"}).status_code, 502)

    def test_routes_do_not_write(self):
        path = Path(self.tmp.name) / STORE_FILE
        before = path.read_bytes()
        self.client.get("/api/knowledge/person", params={"mbid": "a-gid"})
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
