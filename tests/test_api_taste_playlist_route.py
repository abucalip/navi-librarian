"""Route and body tests for POST /api/playlists/taste (docs/redesign.md A8b item 1)."""
import random
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.taste_playlist as routes
from app.api.dependencies import get_librarian
from intelligence.api.taste_playlist import PAGE, PLAYLIST_SIZE, clean_genre, pick_song_ids


class FakeLibrarian:
    def __init__(self, songs=(), fail_on=None, playlist_id="pl-1"):
        self.songs = list(songs)
        self.fail_on = fail_on
        self.playlist_id = playlist_id
        self.calls = []

    def api_call(self, method, **params):
        self.calls.append((method, params))
        if method == self.fail_on:
            raise RuntimeError("boom")
        if method == "getSongsByGenre":
            o = params["offset"]
            return {"songsByGenre": {"song": self.songs[o:o + params["count"]]}}
        return {"playlist": {"id": self.playlist_id}}

    def items(self, value):
        return value or []


def songs(n):
    return [{"id": f"tr-{i}"} for i in range(n)]


class TastePlaylistRoute(unittest.TestCase):
    def client(self, lib):
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: lib
        return TestClient(api)

    def test_creates_playlist_of_fifty_distinct_songs(self):
        lib = FakeLibrarian(songs(120))
        r = self.client(lib).post("/api/playlists/taste", json={"genre": " Ambient "})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual((body["playlist_id"], body["genre"], body["song_count"]), ("pl-1", "Ambient", PLAYLIST_SIZE))
        create = [c for c in lib.calls if c[0] == "createPlaylist"][0][1]
        self.assertEqual(create["name"], "Ambient (Discair)")
        self.assertEqual(len(set(create["songId"])), PLAYLIST_SIZE)

    def test_fewer_songs_than_the_size_uses_all(self):
        body = self.client(FakeLibrarian(songs(3))).post("/api/playlists/taste", json={"genre": "Dub"}).json()
        self.assertEqual(body["song_count"], 3)

    def test_pages_past_one_page(self):
        lib = FakeLibrarian(songs(PAGE + 10))
        self.client(lib).post("/api/playlists/taste", json={"genre": "Rock"})
        self.assertEqual([c[1]["offset"] for c in lib.calls if c[0] == "getSongsByGenre"], [0, PAGE])

    def test_no_songs_is_404_and_nothing_is_created(self):
        lib = FakeLibrarian([])
        r = self.client(lib).post("/api/playlists/taste", json={"genre": "Polka"})
        self.assertEqual(r.status_code, 404)
        self.assertNotIn("createPlaylist", [c[0] for c in lib.calls])

    def test_bad_genre_is_400(self):
        c = self.client(FakeLibrarian(songs(5)))
        for body in ({}, {"genre": ""}, {"genre": "  "}, {"genre": 5}, {"genre": "x" * 101}):
            self.assertEqual(c.post("/api/playlists/taste", json=body).status_code, 400, body)

    def test_navidrome_failure_is_502_with_a_fixed_message(self):
        for method in ("getSongsByGenre", "createPlaylist"):
            r = self.client(FakeLibrarian(songs(5), fail_on=method)).post("/api/playlists/taste", json={"genre": "Rock"})
            self.assertEqual((r.status_code, "boom" in r.text), (502, False), method)

    def test_missing_playlist_id_is_502(self):
        r = self.client(FakeLibrarian(songs(5), playlist_id="")).post("/api/playlists/taste", json={"genre": "Rock"})
        self.assertEqual(r.status_code, 502)

    def test_helpers(self):
        self.assertIsNone(clean_genre(None))
        self.assertEqual(pick_song_ids([{"id": "a"}, {"id": "a"}, {"id": None}], rng=random.Random(1)), ["a"])


if __name__ == "__main__":
    unittest.main()
