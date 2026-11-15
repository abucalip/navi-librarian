"""Star Operation S2c: list and lift "Not this artist"."""
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import discovery as routes
from app.api.dependencies import get_librarian
from discovery import artist_block
from discovery.list_payload import dismissed_predicate
from recommendation.music_key import music_key
from recommendation_feedback import feedback_penalty


def init_db(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE discovery_feedback (scope TEXT NOT NULL, artist_key TEXT NOT NULL,
            album_key TEXT NOT NULL DEFAULT '', artist TEXT NOT NULL, album TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL,
            updated_at REAL NOT NULL, PRIMARY KEY (scope, artist_key, album_key))""")


def add(path, scope, artist, album, status, stamp):
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO discovery_feedback VALUES (?,?,?,?,?,?,'{}',?,?)",
                   (scope, music_key(artist), music_key(album), artist, album, status, stamp, stamp))


def rows(path):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute("SELECT * FROM discovery_feedback")]


class FakeLibrarian:
    def __init__(self, path):
        self.DISCOVERY_DB = path

    def _discovery_init(self):
        pass

    _music_key = staticmethod(music_key)


class ArtistBlockTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "d.sqlite3")
        init_db(self.db)
        self.now = time.time()
        add(self.db, "artist", "Slowdive", "", "not_for_me_artist", self.now - 10)
        add(self.db, "artist", "Ride", "", "not_for_me_artist", self.now)
        add(self.db, "album", "Slowdive", "Souvlaki", "not_for_me", self.now - 10)
        add(self.db, "artist_lean", "Lush", "", "more_like_this", self.now)
        add(self.db, "genre", "Shoegaze", "", "blocked_genre", self.now)

    def test_lists_only_artist_rows_newest_first(self):
        self.assertEqual([a["artist"] for a in artist_block.list_blocked(self.db)], ["Ride", "Slowdive"])

    def test_unblock_removes_only_that_artist_row_and_lifts_hide_and_penalty(self):
        before = rows(self.db)
        hidden = dismissed_predicate(before, music_key)
        self.assertTrue(hidden({"artist": "Slowdive", "album": "Other"}))
        self.assertGreater(feedback_penalty(music_key("Slowdive"), music_key("Other"), (), frozenset(),
                                            before, now=self.now), 0)
        self.assertTrue(artist_block.unblock_artist(self.db, " slowdive ", music_key))
        after = rows(self.db)
        self.assertFalse(dismissed_predicate(after, music_key)({"artist": "Slowdive", "album": "Other"}))
        self.assertEqual(feedback_penalty(music_key("Slowdive"), music_key("Other"), (), frozenset(),
                                          after, now=self.now), 0)
        self.assertEqual(len(after), len(before) - 1)
        # The album row, the other artist, the lean and the genre block are untouched.
        self.assertTrue(dismissed_predicate(after, music_key)({"artist": "Slowdive", "album": "Souvlaki"}))
        self.assertTrue(dismissed_predicate(after, music_key)({"artist": "Ride", "album": "X"}))
        self.assertEqual({r["scope"] for r in after}, {"artist", "album", "artist_lean", "genre"})

    def test_unblock_unknown_artist_is_false_and_blank_is_an_error(self):
        self.assertFalse(artist_block.unblock_artist(self.db, "Nobody", music_key))
        with self.assertRaises(ValueError):
            artist_block.unblock_artist(self.db, " ", music_key)

    def test_routes(self):
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.db)
        client = TestClient(api)
        listed = client.get("/api/discovery/blocked-artists").json()["artists"]
        self.assertEqual([a["artist"] for a in listed], ["Ride", "Slowdive"])
        done = client.request("DELETE", "/api/discovery/blocked-artists", json={"artist": "Ride"}).json()
        self.assertEqual((done["ok"], done["removed"]), (True, True))
        self.assertEqual([a["artist"] for a in client.get("/api/discovery/blocked-artists").json()["artists"]], ["Slowdive"])
        self.assertEqual(client.request("DELETE", "/api/discovery/blocked-artists", json={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
