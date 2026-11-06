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
        repo.upsert_entity(db, "place", "Studio", mbid="p-gid")
        repo.upsert_entity(db, "event", "Night", mbid="e-gid")
        db.close()

    def test_each_page_answers_for_a_known_entity(self):
        for path, params in (
            ("/api/knowledge/person", {"mbid": "a-gid"}),
            ("/api/knowledge/label", {"mbid": "l-gid"}),
            ("/api/knowledge/work", {"mbid": "w-gid"}),
            ("/api/knowledge/album", {"mbid": "rg-gid", "type": "release_group"}),
            ("/api/knowledge/recording-works", {"mbid": "r-gid"}),
            ("/api/knowledge/place", {"mbid": "p-gid"}),
            ("/api/knowledge/event", {"mbid": "e-gid"}),
        ):
            with self.subTest(path=path):
                response = self.client.get(path, params=params)
                self.assertEqual(response.status_code, 200, response.text)

    def test_unknown_entity_is_404(self):
        for path in ("person", "label", "work", "album", "recording-works", "place", "event"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"/api/knowledge/{path}", params={"mbid": "nope"}).status_code, 404)

    def test_missing_identifier_is_400(self):
        for path in ("person", "album", "recording-works"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"/api/knowledge/{path}").status_code, 400)

    def test_label_and_work_need_an_mbid(self):
        for path in ("label", "work", "place", "event"):
            self.assertEqual(self.client.get(f"/api/knowledge/{path}").status_code, 422)

    def test_place_and_event_are_not_interchangeable(self):
        self.assertEqual(self.client.get("/api/knowledge/place", params={"mbid": "e-gid"}).status_code, 404)
        self.assertEqual(self.client.get("/api/knowledge/event", params={"mbid": "p-gid"}).status_code, 404)

    def test_bad_type_and_limit_are_400_or_422(self):
        self.assertEqual(self.client.get("/api/knowledge/album", params={"mbid": "x", "type": "track"}).status_code, 400)
        self.assertEqual(self.client.get("/api/knowledge/person", params={"mbid": "x", "type": "label"}).status_code, 400)
        self.assertEqual(self.client.get("/api/knowledge/person", params={"mbid": "a-gid", "limit": 0}).status_code, 422)
        self.assertEqual(self.client.get("/api/knowledge/person", params={"mbid": "a-gid", "limit": 501}).status_code, 422)

    def _link(self):
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        for rel, role in (("producer", "exec"), ("instrument", "guitar")):
            repo.add_edge(db, self.artist, self.recording, rel, role=role, source="musicbrainz_dump",
                          evidence_class="source_explicit", match_quality="exact_mbid")
        db.close()

    def test_connections_lists_public_hops_with_via_mbid(self):
        self._link()
        r = self.client.get("/api/knowledge/connections", params={"mbid": "a-gid", "type": "artist"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["start"]["mbid"], "a-gid")
        self.assertEqual([h["entity"]["mbid"] for h in body["hops"]], ["r-gid"])
        self.assertEqual(body["hops"][0]["via_mbid"], "a-gid")
        self.assertEqual(len(body["hops"][0]["evidence"]), 2)
        self.assertNotIn('"id"', r.text)
        self.assertIs(body["start"]["owned"], True)

    def test_connections_pages_with_a_cursor(self):
        self._link()
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        repo.add_edge(db, self.artist, self.work, "composer", source="musicbrainz_dump",
                      evidence_class="source_explicit", match_quality="exact_mbid")
        db.close()
        first = self.client.get("/api/knowledge/connections", params={"mbid": "a-gid", "type": "artist", "limit": 1}).json()
        self.assertEqual(len(first["hops"]), 1)
        self.assertTrue(first["next_cursor"])
        second = self.client.get("/api/knowledge/connections", params={
            "mbid": "a-gid", "type": "artist", "limit": 1, "cursor": first["next_cursor"]}).json()
        self.assertEqual(len(second["hops"]), 1)
        self.assertNotEqual(first["hops"][0]["entity"]["mbid"], second["hops"][0]["entity"]["mbid"])

    def test_connections_filters_and_validation(self):
        self._link()
        only = self.client.get("/api/knowledge/connections",
                               params={"mbid": "a-gid", "type": "artist", "relation": "composer"}).json()
        self.assertEqual(only["hops"], [])
        get = self.client.get
        base = {"mbid": "a-gid", "type": "artist"}
        self.assertEqual(get("/api/knowledge/connections", params={**base, "cursor": "!!"}).status_code, 400)
        self.assertEqual(get("/api/knowledge/connections", params={**base, "direction": "up"}).status_code, 400)
        self.assertEqual(get("/api/knowledge/connections", params={"mbid": "a-gid"}).status_code, 400)
        self.assertEqual(get("/api/knowledge/connections", params={"type": "artist"}).status_code, 400)
        self.assertEqual(get("/api/knowledge/connections", params={**base, "depth": 4}).status_code, 422)
        self.assertEqual(get("/api/knowledge/connections", params={"mbid": "nope", "type": "artist"}).status_code, 404)

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
