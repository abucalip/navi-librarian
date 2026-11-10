import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.knowledge_update as routes
from app.api.dependencies import get_librarian
from intelligence.musicbrainz import update_requests as ur
from intelligence.store import open_store


class FakeLibrarian:
    def __init__(self, d):
        self.DATA_DIR = Path(d)


class UpdateRequests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(tmp.name)
        self.client = TestClient(api)
        self.tmp = tmp.name

    def test_post_queues_once_and_status_reads(self):
        body = {"subject": "album", "navidrome_id": "al-1"}
        self.assertEqual(self.client.post("/api/knowledge/update-store", json=body).json()["state"], "queued")
        self.assertEqual(self.client.post("/api/knowledge/update-store", json=body).json()["state"], "queued")
        r = self.client.get("/api/knowledge/update-store", params=body).json()
        self.assertEqual(r["state"], "queued")
        self.assertEqual(self.client.get("/api/knowledge/update-store",
                                         params={"subject": "artist", "navidrome_id": "x"}).json(), {"state": "none"})

    def test_artist_by_mbid_queues_and_unknown_fails(self):
        r = self.client.post("/api/knowledge/update-store", json={"subject": "artist", "mbid": "ABC"}).json()
        self.assertEqual(r["state"], "queued")
        self.assertEqual(self.client.get("/api/knowledge/update-store", params={"subject": "artist", "mbid": "abc"}).json()["state"], "queued")
        db = open_store(Path(self.tmp) / routes.STORE_FILE)
        out = ur.process_next(db, get_album=lambda i: None, get_artist=lambda i: None)
        self.assertEqual(out["state"], "failed")
        db.close()

    def test_navidrome_error_is_reported_in_words(self):
        db = open_store(Path(self.tmp) / routes.STORE_FILE)
        ur.enqueue(db, "album", "x")

        def boom(_):
            raise RuntimeError("Navidrome API error 70: Data not found")
        out = ur.process_next(db, get_album=boom, get_artist=boom)
        self.assertEqual(out["state"], "failed")
        self.assertIn("Data not found", out["message"])
        db.close()

    def test_artist_request_uses_each_albums_own_artist(self):
        """An artist's list can hold an album credited to someone else; the credit must not be forced onto the requested artist."""
        asked, other = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
        artists = {"ar-1": {"id": "ar-1", "name": "Asked", "musicBrainzId": asked, "album": [{"id": "al-feat"}, {"id": "al-own"}]},
                   "ar-2": {"id": "ar-2", "name": "Other", "musicBrainzId": other}}
        albums = {
            "al-feat": {"id": "al-feat", "name": "Feature", "artist": "Other", "artistId": "ar-2",
                        "musicBrainzId": "33333333-3333-4333-8333-333333333333", "song": []},
            "al-own": {"id": "al-own", "name": "Own", "artist": "Asked", "artistId": "ar-1",
                       "musicBrainzId": "44444444-4444-4444-8444-444444444444", "song": []},
        }
        db = open_store(Path(self.tmp) / routes.STORE_FILE)
        ur.enqueue(db, "artist", "ar-1")
        out = ur.process_next(db, get_album=albums.get, get_artist=artists.get,
                              fetch=lambda url: (_ for _ in ()).throw(AssertionError("no network")))
        self.assertEqual(out["state"], "done", out)
        self.assertIn("2 albums", out["message"])
        from intelligence.store import repositories as repo
        self.assertIsNotNone(repo.find_entity(db, "artist", mbid=asked))
        self.assertIsNotNone(repo.find_entity(db, "artist", mbid=other))
        db.close()

    def test_bad_subject_is_422(self):
        r = self.client.post("/api/knowledge/update-store", json={"subject": "song", "navidrome_id": "1"})
        self.assertEqual(r.status_code, 422)

    def test_missing_album_fails_cleanly_and_can_requeue(self):
        db = open_store(Path(self.tmp) / routes.STORE_FILE)
        ur.enqueue(db, "album", "gone")
        out = ur.process_next(db, get_album=lambda i: None, get_artist=lambda i: None)
        self.assertEqual(out["state"], "failed")
        self.assertIsNone(ur.process_next(db, get_album=lambda i: None, get_artist=lambda i: None))
        self.assertEqual(ur.enqueue(db, "album", "gone")["state"], "queued")
        db.close()


if __name__ == "__main__":
    unittest.main()
