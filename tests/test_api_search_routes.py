"""Route-level regressions for global search, artist pages and library browsing."""
import json
import threading
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.search as search_routes
from app.api.dependencies import get_librarian
from app.api.library import router as library_router
from app.api.search import router as search_router
from discovery.search.index import OwnedIndex


def library_lists():
    artists = [
        {"id": "ar1", "name": "Ash", "album_count": 1},
        {"id": "ar2", "name": "Ash", "album_count": 3},
        {"id": "ar3", "name": "Radiohead", "album_count": 2},
    ]
    albums = [
        {"id": "al1", "artist": "Radiohead", "artist_id": "ar3", "album": "Kid A", "year": 2000, "song_count": 10},
        {"id": "al2", "artist": "Radiohead", "artist_id": "ar3", "album": "Airbag", "year": None, "song_count": 1},
        {"id": "al3", "artist": "Ash", "artist_id": "ar2", "album": "1977", "year": 1996, "song_count": 13},
    ]
    return artists, albums


class FakeLibrarian:
    def __init__(self):
        self.store = {}

    def _discovery_settings_read(self):
        return {"navidrome_generation": 1}

    def _discovery_read_list(self, name):
        # Same shape as discovery.store.read_list: the stored payload sits under "payload".
        if name not in self.store:
            return None
        return {"payload": self.store[name], "generated_at": "2026-10-26T00:00:00"}

    def _discovery_write_list(self, name, payload):
        self.store[name] = payload


class NoNetworkSearch:
    """Stands in for the provider side so route tests never reach a real provider."""

    calls = []

    def __init__(self, **kwargs):
        NoNetworkSearch.calls.append(kwargs)

    def source_capabilities(self):
        return {name: {"available": name == "navidrome" or name == "musicbrainz", "reason": None}
                for name in ("navidrome", "musicbrainz", "lastfm", "listenbrainz", "discogs")}

    def stream(self, **kwargs):
        return iter(())


class FakeLoaders:
    def __init__(self, fail=False):
        self.fail = fail

    def load_library(self):
        return library_lists()

    def load_songs(self):
        if self.fail:
            raise RuntimeError("boom")
        return [{"id": "s1", "title": "Kid A", "artist": "Radiohead", "artistId": "ar3",
                 "album": "Kid A", "albumId": "al1", "duration": 284, "track": 1}]


def parse_sse(body):
    events = []
    for block in body.strip().split("\n\n"):
        name = None
        data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        events.append((name, data))
    return events


class ProviderCacheReaderTests(unittest.TestCase):
    def test_entries_written_by_the_cache_are_read_back_through_the_store_shape(self):
        from discovery.search.cache import read_cached, write_cached

        librarian = FakeLibrarian()
        key = "search:lastfm:0:ash:artist:depth50"
        self.assertIsNone(read_cached(search_routes._cache_reader(librarian), key, 1000.0))
        write_cached(librarian._discovery_write_list, key, [{"name": "Ash"}], 1000.0)
        self.assertEqual(read_cached(search_routes._cache_reader(librarian), key, 1001.0), [{"name": "Ash"}])

    def test_a_missing_or_malformed_entry_reads_as_absent(self):
        librarian = FakeLibrarian()
        librarian._discovery_read_list = lambda name: "not a mapping"
        self.assertIsNone(search_routes._cache_reader(librarian)("anything"))


class SearchRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(search_router)
        self.app.include_router(library_router)
        self.app.dependency_overrides[get_librarian] = lambda: FakeLibrarian()
        self.client = TestClient(self.app)
        self.previous_index = search_routes._owned_index
        self.previous_external = search_routes.external_search
        search_routes.external_search = NoNetworkSearch
        self.previous_artist_network = search_routes.artist_network_for
        search_routes.artist_network_for = lambda librarian: None  # no network sections in these tests
        NoNetworkSearch.calls = []
        self.release = threading.Event()
        self.loaders = FakeLoaders()
        self.set_index(self.loaders)

    def tearDown(self):
        self.release.set()
        search_routes._owned_index = self.previous_index
        search_routes.external_search = self.previous_external
        search_routes.artist_network_for = self.previous_artist_network

    def building_index(self):
        """An index whose first build never finishes until teardown, so it stays building."""
        def blocked_songs():
            self.release.wait(10)
            return []

        search_routes._owned_index = OwnedIndex(
            load_library=self.loaders.load_library,
            load_songs=blocked_songs,
            background=True,
        )
        search_routes._owned_index.ensure(1)

    def set_index(self, loaders):
        search_routes._owned_index = OwnedIndex(
            load_library=loaders.load_library,
            load_songs=loaders.load_songs,
            background=False,
        )
        search_routes._owned_index.ensure(1)

    def search(self, params, accept="text/event-stream"):
        return self.client.get("/api/search", params=params, headers={"Accept": accept})

    # --- /api/search validation (400 before streaming) -------------------------

    def test_owned_scope_never_builds_the_network_side(self):
        response = self.search({"q": "ash", "scope": "owned"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(NoNetworkSearch.calls, [])
        self.assertNotIn("source", [name for name, _ in parse_sse(response.text)])

    def test_all_scope_builds_the_network_side_with_the_provider_cache(self):
        self.search({"q": "ash"})
        self.assertEqual(len(NoNetworkSearch.calls), 1)
        self.assertIn("cache_read", NoNetworkSearch.calls[0])

    def test_bad_parameters_are_400_before_any_stream_starts(self):
        for params in (
            {},
            {"q": ""},
            {"q": "x" * 201},
            {"q": "!!!"},
            {"q": "ash", "types": "artist,podcast"},
            {"q": "ash", "types": ""},
            {"q": "ash", "scope": "everything"},
            {"q": "ash", "limit": "0"},
            {"q": "ash", "limit": "51"},
            {"q": "ash", "limit": "many"},
        ):
            with self.subTest(params=params):
                response = self.search(params)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("text/event-stream", response.headers["content-type"])

    # --- /api/search stream ----------------------------------------------------

    def test_stream_starts_with_capabilities_then_owned_results_then_one_done(self):
        response = self.search({"q": "ash"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        events = parse_sse(response.text)
        names = [name for name, _ in events]
        self.assertEqual(names[0], "capabilities")
        self.assertEqual(names[-1], "done")
        self.assertEqual(names.count("done"), 1)
        self.assertEqual(set(names[1:-1]), {"result"})
        self.assertNotIn("source", names)
        self.assertNotIn("error", names)

        capabilities = events[0][1]
        self.assertEqual(set(capabilities), {"types", "sources", "owned_index"})
        self.assertEqual(list(capabilities["sources"]),
                         ["navidrome", "musicbrainz", "lastfm", "listenbrainz", "discogs"])
        self.assertEqual(capabilities["types"]["genre"], {"available": True, "reason": None})
        self.assertEqual(capabilities["owned_index"]["state"], "fresh")

        results = [data for name, data in events if name == "result"]
        self.assertEqual({r["id"] for r in results if r["type"] == "artist"}, {"ar1", "ar2"})
        self.assertTrue(all(r["owned"] and r["sources"] == ["navidrome"] for r in results))
        self.assertIs(events[-1][1]["partial"], False)
        self.assertIs(events[-1][1]["deadline_hit"], False)

    def test_owned_results_are_emitted_in_type_order_and_limit_applies_per_type(self):
        events = parse_sse(self.search({"q": "a", "limit": "1"}).text)
        results = [data for name, data in events if name == "result"]
        self.assertLessEqual(sum(1 for r in results if r["type"] == "artist"), 1)
        self.assertLessEqual(sum(1 for r in results if r["type"] == "album"), 1)
        order = [r["type"] for r in results]
        self.assertEqual(order, sorted(order, key=["artist", "album", "song"].index))

    def test_types_filter_limits_results(self):
        events = parse_sse(self.search({"q": "kid", "types": "song"}).text)
        results = [data for name, data in events if name == "result"]
        self.assertEqual([r["type"] for r in results], ["song"])

    def test_json_accept_is_not_a_stream_for_search(self):
        response = self.search({"q": "ash"}, accept="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))

    def test_index_building_still_streams_with_partial_done_and_no_results(self):
        self.building_index()
        events = parse_sse(self.search({"q": "ash", "scope": "owned"}).text)
        names = [name for name, _ in events]
        self.assertEqual(names[0], "capabilities")
        self.assertEqual(names[-1], "done")
        self.assertNotIn("result", names)
        capabilities = events[0][1]
        self.assertEqual(capabilities["types"]["artist"]["reason"], "index_building")
        self.assertIs(events[-1][1]["partial"], True)

    def test_unavailable_index_reports_index_unavailable_not_an_http_error(self):
        loaders = FakeLoaders(fail=True)
        search_routes._owned_index = OwnedIndex(
            load_library=loaders.load_library,
            load_songs=loaders.load_songs,
            background=False,
        )
        response = self.search({"q": "ash"})
        self.assertEqual(response.status_code, 200)
        events = parse_sse(response.text)
        capabilities = events[0][1]
        self.assertEqual(capabilities["owned_index"]["state"], "unavailable")
        self.assertEqual(capabilities["types"]["album"]["reason"], "index_unavailable")
        self.assertIs(events[-1][1]["partial"], True)

    # --- /api/artists/{key} ------------------------------------------------------

    def test_artist_json_form_has_exactly_three_top_level_keys(self):
        response = self.client.get("/api/artists/radiohead")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"capabilities", "sections", "done"})
        self.assertEqual(body["sections"]["artist"]["artist"]["name"], "Radiohead")
        self.assertNotIn("section", body["sections"]["artist"])
        self.assertEqual([a["name"] for a in body["sections"]["owned_albums"]["items"]],
                         ["Kid A", "Airbag"])
        self.assertEqual(set(body["done"]), {"elapsed_ms", "deadline_hit", "partial"})

    def test_unknown_key_is_404_with_the_contract_body(self):
        response = self.client.get("/api/artists/nobody")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"code": "unknown_artist", "message": "No artist matches this key."})

    def test_ambiguous_key_is_409_with_candidates_and_id_resolves_it(self):
        response = self.client.get("/api/artists/ash")
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["code"], "ambiguous_artist")
        self.assertEqual({c["id"] for c in body["candidates"]}, {"ar1", "ar2"})
        self.assertEqual(set(body["candidates"][0]), {"id", "name", "album_count"})

        resolved = self.client.get("/api/artists/ash", params={"id": "ar2"})
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["sections"]["artist"]["artist"]["id"], "ar2")

    def test_artist_route_failure_is_502_with_only_code_and_message(self):
        from unittest import mock
        with mock.patch.object(search_routes, "artist_page", side_effect=RuntimeError("boom")):
            response = self.client.get("/api/artists/radiohead")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"code": "artist_failed", "message": "Owned index read failed."})

    def test_various_artists_is_unknown_to_the_artist_route(self):
        response = self.client.get("/api/artists/various-artists")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "unknown_artist")

    def test_mbid_never_selects_the_owned_artist(self):
        response = self.client.get("/api/artists/ash", params={"mbid": "a74b1b7f-71a5-4011-9441-d0b5e4122711"})
        self.assertEqual(response.status_code, 409)

    def test_artist_stream_form_emits_capabilities_eight_sections_then_done(self):
        response = self.client.get("/api/artists/radiohead", headers={"Accept": "text/event-stream"})
        events = parse_sse(response.text)
        names = [name for name, _ in events]
        self.assertEqual(names[0], "capabilities")
        self.assertEqual(names[-1], "done")
        sections = [data["section"] for name, data in events if name == "section"]
        # Owned sections lead; network sections follow in the order they finish.
        self.assertEqual(sections[:2], ["artist", "owned_albums"])
        self.assertEqual(sorted(sections[2:]), ["albums", "bio", "missing_albums", "similar", "tags", "top_songs"])

    def test_artist_answers_200_while_the_index_is_building(self):
        self.building_index()
        response = self.client.get("/api/artists/nobody")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sections"]["artist"]["reason"], "index_building")
        self.assertIs(response.json()["done"]["partial"], True)

    # --- /api/library/artists ---------------------------------------------------

    def test_library_pages_with_opaque_cursor_and_reports_index_state(self):
        first = self.client.get("/api/library/artists", params={"limit": "2"}).json()
        self.assertEqual(first["index_state"], "fresh")
        self.assertEqual(first["total"], 3)
        self.assertEqual([a["id"] for a in first["items"]], ["ar1", "ar2"])
        self.assertIsNotNone(first["next_cursor"])
        self.assertIsNotNone(first["snapshot_at"])

        second = self.client.get("/api/library/artists", params={"limit": "2", "cursor": first["next_cursor"]}).json()
        self.assertEqual([a["id"] for a in second["items"]], ["ar3"])
        self.assertIsNone(second["next_cursor"])

    def test_library_building_is_not_an_empty_library(self):
        self.building_index()
        body = self.client.get("/api/library/artists").json()
        self.assertEqual(body, {"items": [], "next_cursor": None, "total": None,
                                "index_state": "building", "snapshot_at": None})

    def test_library_rejects_bad_sort_limit_and_foreign_cursor(self):
        self.assertEqual(self.client.get("/api/library/artists", params={"sort": "year"}).status_code, 400)
        self.assertEqual(self.client.get("/api/library/artists", params={"limit": "201"}).status_code, 400)
        first = self.client.get("/api/library/artists", params={"limit": "1"}).json()
        response = self.client.get(
            "/api/library/artists",
            params={"limit": "1", "cursor": first["next_cursor"], "sort": "album_count"},
        )
        self.assertEqual(response.status_code, 400)

    def test_library_albums_sort_order_and_validation(self):
        body = self.client.get("/api/library/albums", params={"sort": "year", "order": "asc"}).json()
        self.assertEqual([a["name"] for a in body["items"]], ["1977", "Kid A", "Airbag"])
        self.assertEqual(body["total"], 3)
        self.assertEqual(self.client.get("/api/library/albums", params={"sort": "album_count"}).status_code, 400)
        self.assertEqual(self.client.get("/api/library/albums", params={"order": "up"}).status_code, 400)
        first = self.client.get("/api/library/albums", params={"limit": "1", "sort": "year"}).json()
        self.assertEqual(self.client.get(
            "/api/library/albums",
            params={"limit": "1", "sort": "year", "order": "asc", "cursor": first["next_cursor"]},
        ).status_code, 400)

    def test_library_albums_building_is_not_an_empty_library(self):
        self.building_index()
        self.assertEqual(self.client.get("/api/library/albums").json()["index_state"], "building")


class AlbumAndUnownedArtistRouteTests(SearchRouteTests):
    def setUp(self):
        super().setUp()
        from discovery.search.artist_sections import ArtistNetwork

        class Mb:
            def artists(self, query, *, remaining, cancelled):
                return []

        self.network = ArtistNetwork(
            musicbrainz=Mb(), popularity=lambda mbids, can_cache: {}, bio=lambda name: "Public bio.",
            cache_read=lambda key: None, cache_write=lambda key, value: None,
            deezer_tracks=lambda artist, album: [{"track_number": 1, "title": "Found", "duration_seconds": 10}],
            sources={"navidrome": {"available": True, "reason": None}},
            deadline_seconds=2.0,
        )
        search_routes.artist_network_for = lambda librarian: self.network

    def test_owned_album_page_uses_the_index_tracks(self):
        body = self.client.get("/api/albums/radiohead/kid a").json()
        self.assertEqual(body["sections"]["album"]["album"]["id"], "al1")
        self.assertTrue(body["sections"]["album"]["album"]["owned"])
        # The provider lists "Found"; the library's song "Kid A" matches no track and is appended as owned.
        self.assertEqual([(t["title"], t["owned"]) for t in body["sections"]["tracks"]["items"]],
                         [("Found", False), ("Kid A", True)])
        self.assertEqual(set(body["sections"]), {"album", "year", "genre", "description", "tracks", "similar_artists", "similar_albums"})

    def test_unowned_album_needs_artist_and_name(self):
        response = self.client.get("/api/albums/portishead/dummy")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "unknown_album")

    def test_unowned_album_page_races_for_tracks(self):
        body = self.client.get(
            "/api/albums/portishead/dummy",
            params={"artist": "Portishead", "name": "Dummy", "year": 1994, "mbid": "rg-9"},
        ).json()
        album = body["sections"]["album"]["album"]
        self.assertFalse(album["owned"])
        self.assertEqual(album["year"], 1994)
        self.assertEqual(body["sections"]["tracks"]["items"][0]["title"], "Found")

    def test_album_stream_emits_capabilities_sections_then_done(self):
        response = self.client.get("/api/albums/radiohead/kid a", headers={"Accept": "text/event-stream"})
        names = [name for name, _ in parse_sse(response.text)]
        self.assertEqual(names[0], "capabilities")
        self.assertEqual(names[-1], "done")
        self.assertEqual({d["section"] for n, d in parse_sse(response.text) if n == "section"},
                         {"album", "year", "genre", "description", "tracks", "similar_artists", "similar_albums"})

    def test_unknown_key_with_a_name_is_served_as_an_unowned_artist(self):
        body = self.client.get("/api/artists/portishead", params={"name": "Portishead", "mbid": "mb-p"}).json()
        artist = body["sections"]["artist"]["artist"]
        self.assertEqual((artist["owned"], artist["id"], artist["mbid"]), (False, None, "mb-p"))
        self.assertEqual(body["sections"]["owned_albums"]["items"], [])
        self.assertEqual(body["sections"]["bio"]["bio"]["text"], "Public bio.")

    def test_unknown_key_without_a_name_is_still_404(self):
        self.assertEqual(self.client.get("/api/artists/portishead").status_code, 404)



if __name__ == "__main__":
    unittest.main()
