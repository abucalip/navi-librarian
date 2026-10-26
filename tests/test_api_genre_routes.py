"""Route and capability tests for genre pages and the Discogs source (contract sections 3.4, 3.6, 3.8)."""
import json
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.search as search_routes
from app.api.dependencies import get_librarian
from discovery.search.index import OwnedIndex
from discovery.search.network import artist_network, external_search, genre_network
from discovery.search.providers import album_candidate
from tests.test_api_search_routes import FakeLibrarian, parse_sse
from tests.test_discovery_search_genre import FakeDiscogs, FakeMB, TOKEN, genre_network as fake_genre_network


def lists():
    artists = [{"id": "ar1", "name": "Ride", "album_count": 1}]
    albums = [{"id": "al1", "artist": "Ride", "artist_id": "ar1", "album": "Nowhere", "year": 1990,
               "song_count": 8, "genre": "Shoegaze"}]
    return artists, albums


class GenreRouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(search_routes.router)
        app.dependency_overrides[get_librarian] = lambda: FakeLibrarian()
        self.client = TestClient(app)
        self.previous_index = search_routes._owned_index
        self.previous_network = search_routes.genre_network
        self.dg = FakeDiscogs([album_candidate("discogs", "Loveless", "My Bloody Valentine", 1991, None)])
        search_routes.genre_network = lambda **kwargs: fake_genre_network(FakeMB(), self.dg)
        search_routes._owned_index = OwnedIndex(load_library=lists, load_songs=lambda: [], background=False)
        search_routes._owned_index.ensure(1)

    def tearDown(self):
        search_routes._owned_index = self.previous_index
        search_routes.genre_network = self.previous_network

    def test_json_form_has_exactly_capabilities_sections_and_done(self):
        response = self.client.get("/api/genres/Shoegaze")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"capabilities", "sections", "done"})
        self.assertEqual(set(body["sections"]), {"artists", "albums"})
        albums = body["sections"]["albums"]["items"]
        self.assertEqual([(i["name"], i["owned"]) for i in albums], [("Nowhere", True), ("Loveless", False)])
        self.assertNotIn("section", body["sections"]["albums"])
        self.assertNotIn(TOKEN, json.dumps(body))

    def test_stream_form_is_capabilities_two_sections_done(self):
        response = self.client.get("/api/genres/shoegaze", headers={"Accept": "text/event-stream"})
        names = [name for name, _ in parse_sse(response.text)]
        self.assertEqual(names, ["capabilities", "section", "section", "done"])

    def test_blank_or_oversized_tags_are_400(self):
        self.assertEqual(self.client.get("/api/genres/%20").status_code, 400)
        self.assertEqual(self.client.get("/api/genres/" + "x" * 101).status_code, 400)

    def test_failure_is_a_502_with_only_code_and_message(self):
        def boom(**kwargs):
            raise RuntimeError(TOKEN)

        search_routes.genre_network = boom
        response = self.client.get("/api/genres/shoegaze")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(set(response.json()), {"code", "message"})
        self.assertNotIn(TOKEN, response.text)


class DiscogsCapabilityTests(unittest.TestCase):
    def settings(self, **values):
        return lambda: dict(values)

    def search_sources(self, **values):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DISCOGS_TOKEN", None)
            return external_search(
                settings_read=self.settings(**values), cache_read=lambda k: None, cache_write=lambda k, v: None,
            ).source_capabilities()

    def test_search_reports_source_disabled_without_a_token_and_available_with_one(self):
        self.assertEqual(self.search_sources()["discogs"], {"available": False, "reason": "source_disabled"})
        with_token = self.search_sources(discogs_token=TOKEN)
        self.assertEqual(with_token["discogs"], {"available": True, "reason": None})
        self.assertNotIn(TOKEN, json.dumps(with_token))

    def test_environment_token_enables_discogs(self):
        with patch.dict(os.environ, {"DISCOGS_TOKEN": "env-token"}):
            caps = external_search(
                settings_read=self.settings(), cache_read=lambda k: None, cache_write=lambda k, v: None,
            ).source_capabilities()
        self.assertTrue(caps["discogs"]["available"])

    def test_artist_network_states(self):
        base = dict(cache_read=lambda k: None, cache_write=lambda k, v: None, popularity=lambda m, c: {}, bio=lambda n: None)
        self.assertEqual(artist_network(**base).sources["discogs"], {"available": False, "reason": "source_disabled"})
        net = artist_network(**base, discogs_token=TOKEN, discogs_gen=2)
        self.assertEqual(net.sources["discogs"], {"available": True, "reason": None})
        self.assertEqual(net.discogs_generation, 2)

    def test_genre_network_uses_settings_token_and_generation(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DISCOGS_TOKEN", None)
            none = genre_network(settings_read=lambda: {}, cache_read=lambda k: None, cache_write=lambda k, v: None)
            some = genre_network(
                settings_read=lambda: {"discogs_token": TOKEN, "discogs_generation": 4},
                cache_read=lambda k: None, cache_write=lambda k, v: None,
            )
        self.assertIsNone(none.discogs)
        self.assertIsNotNone(some.discogs)
        self.assertEqual(some.discogs_generation, 4)


if __name__ == "__main__":
    unittest.main()
