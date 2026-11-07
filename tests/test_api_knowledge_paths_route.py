"""Route tests for GET /api/knowledge/paths (Server V2 Phase 5): public shape, validation, cache."""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.knowledge as routes
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.store import open_store
from intelligence.store import repositories as repo

DUMP = "musicbrainz_dump"


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class PathsRoute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        up = lambda t, n, g, **kw: repo.upsert_entity(db, t, n, mbid=g, **kw)[0]
        artist, release = up("artist", "Alpha", "a-gid", owned=True), up("release", "Alpha LP", "rel-gid", owned=True)
        rec, player = up("recording", "Alpha Song", "rec-gid", owned=True), up("artist", "Player", "p-gid")
        other = up("recording", "Other Take", "o-gid")
        add = lambda a, b, rel, **kw: repo.add_edge(db, a, b, rel, evidence_class=kw.pop("ec", "source_explicit"),
                                                    match_quality="exact_mbid", **kw)
        add(release, artist, "credited_to", source="navidrome", ec="library_tag")
        add(rec, release, "appears_on", source="navidrome", ec="library_tag")
        add(player, rec, "instrument", source=DUMP, role="guitar")
        add(player, other, "instrument", source=DUMP, role="guitar")
        db.close()
        self.params = {"mbid": "a-gid", "type": "artist", "kind": "follow_the_musician"}

    def get(self, **over):
        return self.client.get("/api/knowledge/paths", params={**self.params, **over})

    def test_path_is_public_with_reasons_and_evidence(self):
        r = self.get()
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["start"]["mbid"], "a-gid")
        stop = body["stops"][0]
        self.assertEqual(stop["entity"]["mbid"], "o-gid")
        reason = stop["reasons"][0]
        self.assertEqual(reason["code"], "shared_musician")
        self.assertTrue(reason["evidence"])
        self.assertIn({"label": "Recording", "value": "Alpha Song"}, reason["details"])
        self.assertIn({"label": "Connecting credit", "value": "guitar"}, reason["details"])
        self.assertIsInstance(stop["entity"]["owned"], bool)
        text = r.text
        for leaked in ('"id"', "navidrome_id", "built_from", "generation_id", "presentation_version"):
            self.assertNotIn(leaked, text)

    def test_empty_when_nothing_is_evidenced(self):
        r = self.get(kind="scene_path")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["status"], r.json()["stops"]), ("empty", []))

    def test_second_request_is_served_from_the_cache(self):
        first = self.get().json()
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        n = db.execute("SELECT COUNT(*) FROM insights WHERE kind = 'path:follow_the_musician'").fetchone()[0]
        db.close()
        self.assertEqual(n, 1)
        self.assertEqual(self.get().json(), first)

    def test_validation(self):
        for over, code in (({"kind": "same_studio_different_decade"}, 400),
                           ({"kind": "nope"}, 400), ({"type": "label"}, 400), ({"type": None}, 400),
                           ({"mbid": "nope"}, 404)):
            with self.subTest(over=over):
                params = {k: v for k, v in {**self.params, **over}.items() if v is not None}
                self.assertEqual(self.client.get("/api/knowledge/paths", params=params).status_code, code)
        self.assertEqual(self.client.get("/api/knowledge/paths", params={"kind": "scene_path", "type": "artist"}).status_code, 400)
        self.assertEqual(self.client.get("/api/knowledge/paths", params={"mbid": "a-gid", "type": "artist"}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
