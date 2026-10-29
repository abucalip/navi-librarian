"""Direct-import regressions for the Navidrome-backed dashboard sections."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dashboard import router
from app.api.dependencies import get_librarian
from app.services.dashboard_sections import album_shelf, genre_tiles


class GenreTileTests(unittest.TestCase):
    def test_ranks_by_album_count_and_folds_case_variants(self):
        genres = {"genres": {"genre": [
            {"value": "Jazz", "albumCount": 3},
            {"value": "jazz", "albumCount": 2},
            {"value": "Metal", "albumCount": 4},
            {"value": "Empty", "albumCount": 0},
            {"value": "  ", "albumCount": 9},
        ]}}
        tiles = genre_tiles(lambda method, **p: genres, 10)
        self.assertEqual([t["name"] for t in tiles], ["Jazz", "Metal"])
        self.assertEqual(tiles[0]["album_count"], 5)
        self.assertEqual(tiles[0]["tag"], "jazz")

    def test_single_genre_object_and_limit(self):
        one = {"genres": {"genre": {"value": "Rock", "albumCount": 1}}}
        self.assertEqual(len(genre_tiles(lambda m, **p: one, 5)), 1)
        many = {"genres": {"genre": [{"value": f"g{i}", "albumCount": i + 1} for i in range(5)]}}
        self.assertEqual(len(genre_tiles(lambda m, **p: many, 2)), 2)

    def test_no_genres(self):
        self.assertEqual(genre_tiles(lambda m, **p: {}, 5), [])


class AlbumShelfTests(unittest.TestCase):
    def test_maps_albums_and_passes_the_navidrome_type(self):
        calls = []

        def api_call(method, **params):
            calls.append((method, params))
            return {"albumList2": {"album": [
                {"id": "a1", "name": "One", "artist": "A", "artistId": "x", "year": 1999, "coverArt": "al-a1"},
                {"id": "a2", "name": "Two", "artist": "B", "year": 0},
                {"id": "", "name": "Skipped"},
            ]}}

        albums = album_shelf(api_call, "frequent", 7)
        self.assertEqual(calls, [("getAlbumList2", {"type": "frequent", "size": 7, "offset": 0})])
        self.assertEqual([a["name"] for a in albums], ["One", "Two"])
        self.assertEqual(albums[0]["artwork_url"], "/api/owned/artwork/al-a1")
        self.assertEqual(albums[1]["artwork_url"], "/api/owned/artwork/a2")
        self.assertIsNone(albums[1]["year"])
        self.assertTrue(all(a["owned"] for a in albums))


class Librarian:
    def __init__(self, fail=False):
        self.fail = fail

    def api_call(self, method, **params):
        if self.fail:
            raise RuntimeError("down")
        if method == "getGenres":
            return {"genres": {"genre": [{"value": "Jazz", "albumCount": 1}]}}
        return {"albumList2": {"album": []}}


class DashboardSectionRouteTests(unittest.TestCase):
    def client(self, fail=False):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_librarian] = lambda: Librarian(fail)
        return TestClient(app)

    def test_routes(self):
        client = self.client()
        self.assertEqual(client.get("/api/dashboard/genres").json()["items"][0]["name"], "Jazz")
        self.assertEqual(client.get("/api/dashboard/albums/newest").json(), {"items": []})
        self.assertEqual(client.get("/api/dashboard/albums/bogus").status_code, 404)
        self.assertEqual(client.get("/api/dashboard/albums/recent?count=0").status_code, 400)
        self.assertEqual(client.get("/api/dashboard/genres?limit=0").status_code, 400)

    def test_navidrome_failure_is_a_502(self):
        client = self.client(fail=True)
        self.assertEqual(client.get("/api/dashboard/genres").status_code, 502)
        self.assertEqual(client.get("/api/dashboard/albums/newest").status_code, 502)


if __name__ == "__main__":
    unittest.main()
