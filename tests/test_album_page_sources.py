"""Efficiency K3 part 2: the album page's Deezer, Apple and Wikipedia loaders shared by the routes and the worker.

No test reaches the network: every ``get`` is a fake. The parity test prefetches into a fake store, then asks the
route functions (with their HTTP client set to fail on any request) and expects them to answer from that store.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api import metadata
from app.services import album_page_sources as aps
from app.services import owned_prefetch as op
from app.services import persistent_metadata
from app.services import prefetch_state as ps

ARTIST, ALBUM = "Portishead", "Dummy"
DEEZER_SEARCH = {"data": [{"id": 7, "title": ALBUM, "artist": {"name": ARTIST}, "cover_xl": "https://x/c.jpg",
                           "release_date": "1994-08-22"}]}
DEEZER_ALBUM = {"tracks": {"data": [{"id": 1, "title": "Mysterons", "duration": 300, "track_position": 1,
                                     "artist": {"name": ARTIST}}]}}
ITUNES = {"results": [{"collectionName": ALBUM, "artistName": ARTIST,
                       "collectionViewUrl": "https://music.apple.com/us/album/dummy/1?uo=4"}]}
WIKI_SEARCH = {"pages": [{"key": "Dummy_(album)", "title": "Dummy (album)", "description": "1994 studio album by Portishead"}]}
WIKI_SUMMARY = {"extract": "Dummy is an album.", "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Dummy_(album)"}}}
APPLE_PAGE = '<script id="serialized-server-data" type="application/json">{}</script>'


class Resp:
    def __init__(self, payload=None, text=""):
        self.payload, self.text = payload, text

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class Store:
    def __init__(self):
        self.data = {}

    def read(self, key, ttl):
        return self.data.get(key)

    def write(self, key, value):
        self.data[key] = value


def fake_get(down=()):
    """A ``get`` answering by host; hosts in ``down`` raise like a refused or failed request."""
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        if any(host in url for host in down):
            raise RuntimeError("refused")
        if "api.deezer.com/search/album" in url:
            return Resp(DEEZER_SEARCH)
        if "api.deezer.com/album/" in url:
            return Resp(DEEZER_ALBUM)
        if "itunes.apple.com" in url:
            return Resp(ITUNES)
        if "music.apple.com" in url:
            return Resp(text=APPLE_PAGE)
        if "rest.php/v1/search/page" in url:
            return Resp(WIKI_SEARCH)
        if "rest_v1/page/summary" in url:
            return Resp(WIKI_SUMMARY)
        raise AssertionError(url)
    get.calls = calls
    return get


class TracklistTests(unittest.TestCase):
    def test_a_complete_answer_is_stored_under_the_routes_key(self):
        store, get = Store(), fake_get()
        tracks = aps.prefetch_tracks(store.read, store.write, get, ARTIST, ALBUM)
        self.assertEqual([t["title"] for t in tracks], ["Mysterons"])
        self.assertEqual(list(store.data), ["album-details:v1:portishead:dummy"])

    def test_a_stored_row_costs_no_request(self):
        store = Store()
        store.data["album-details:v1:portishead:dummy"] = {"tracks": [{"title": "Stored"}]}
        get = fake_get(down=("deezer",))
        self.assertEqual(aps.prefetch_tracks(store.read, store.write, get, ARTIST, ALBUM), [{"title": "Stored"}])
        self.assertEqual(get.calls, [])

    def test_a_refused_request_stores_nothing(self):
        store = Store()
        self.assertEqual(aps.prefetch_tracks(store.read, store.write, fake_get(down=("deezer",)), ARTIST, ALBUM), [])
        self.assertEqual(store.data, {})

    def test_a_definite_no_match_is_not_stored_by_the_worker(self):
        store = Store()
        get = lambda url, **kw: Resp({"data": []})
        self.assertEqual(aps.prefetch_tracks(store.read, store.write, get, ARTIST, ALBUM), [])
        self.assertEqual(store.data, {})


class DescriptionTests(unittest.TestCase):
    def test_apple_notes_are_stored_and_the_page_address_too(self):
        store = Store()
        with patch.object(aps, "parse_editorial_notes", return_value=["Apple notes."]):
            found = aps.prefetch_description(store.read, store.write, aps.counting_get(fake_get()), ARTIST, ALBUM)
        self.assertEqual(found["source"], "Apple Music")
        self.assertEqual(set(store.data), {"album-description:v1:portishead:dummy",
                                           "apple-album-url:v1:portishead:dummy"})
        self.assertEqual(store.data["apple-album-url:v1:portishead:dummy"], "https://music.apple.com/us/album/dummy/1")

    def test_wikipedia_is_used_when_apple_answered_with_no_notes(self):
        store = Store()
        with patch.object(aps, "parse_editorial_notes", return_value=[]):
            found = aps.prefetch_description(store.read, store.write, aps.counting_get(fake_get()), ARTIST, ALBUM)
        self.assertEqual(found["source"], "Wikipedia")
        self.assertIn("album-description:v1:portishead:dummy", store.data)

    def test_a_refused_apple_request_never_becomes_a_stored_wikipedia_answer(self):
        store, get = Store(), fake_get(down=("itunes.apple.com",))
        found = aps.prefetch_description(store.read, store.write, aps.counting_get(get), ARTIST, ALBUM)
        self.assertEqual(found["paragraphs"], [])
        self.assertEqual(store.data, {})
        self.assertFalse(any("wikipedia" in url for url in get.calls))

    def test_a_failed_apple_page_fetch_stores_no_description(self):
        store = Store()
        found = aps.prefetch_description(store.read, store.write, aps.counting_get(fake_get(down=("music.apple.com",))),
                                         ARTIST, ALBUM)
        self.assertEqual(found["paragraphs"], [])
        self.assertNotIn("album-description:v1:portishead:dummy", store.data)

    def test_the_route_still_keeps_a_wikipedia_lead_when_apple_failed(self):
        value = aps.load_description(lambda: (dict(aps.EMPTY_DESCRIPTION), False), lambda: ({"paragraphs": ["w"]}, True))
        self.assertTrue(value.persist)

    def test_counting_get_adds_the_client_headers_and_timeout(self):
        seen = {}
        aps.counting_get(lambda url, **kw: seen.update(kw))("https://x", headers={"Accept": "text/html"})
        self.assertEqual(seen["headers"]["Accept"], "text/html")
        self.assertIn("Discair", seen["headers"]["User-Agent"])
        self.assertEqual(seen["timeout"], aps.EXTERNAL_TIMEOUT)


class HookGatingTests(unittest.TestCase):
    def hooks(self, caps):
        librarian = SimpleNamespace(_metadata_cache_get=lambda k, t: None, _metadata_cache_set=lambda k, v: None)
        return op.album_page_hooks(librarian, ps.Spend(caps))

    def test_no_new_hook_without_caps(self):
        self.assertEqual(self.hooks({"musicbrainz": 5, "listenbrainz": 5, "lastfm": 5}), {})

    def test_tracklist_needs_deezer_and_description_needs_apple_and_wikipedia(self):
        self.assertEqual(set(self.hooks({"deezer": 1})), {"deezer_tracks"})
        self.assertEqual(set(self.hooks({"apple": 1})), set())
        self.assertEqual(set(self.hooks({"apple": 1, "wikipedia": 1})), {"album_description"})

    def test_a_request_past_the_cap_is_refused_before_it_is_sent(self):
        sent = []
        spend = ps.Spend({"deezer": 1}, get=lambda url, **kw: sent.append(url) or Resp(DEEZER_SEARCH))
        librarian = SimpleNamespace(_metadata_cache_get=lambda k, t: None, _metadata_cache_set=lambda k, v: None)
        hooks = op.album_page_hooks(librarian, spend)
        hooks["deezer_tracks"](ARTIST, ALBUM)       # the search spends the one request; the tracklist fetch is refused
        self.assertEqual(len(sent), 1)
        self.assertEqual(spend.snapshot()["deezer"], 1)
        self.assertIn("deezer", spend.cap_reached)


class RouteParityTests(unittest.TestCase):
    """What the worker stores is what the routes read, with no request of their own."""

    def setUp(self):
        self.store = Store()
        persistent_metadata.attach(self.store.read, self.store.write)
        self.addCleanup(persistent_metadata.detach)
        for cache in (metadata._album_details_cache, metadata._album_description_cache, metadata._apple_url_cache):
            cache.clear()

    def test_routes_answer_from_the_rows_the_prefetch_stored(self):
        get = aps.counting_get(fake_get())
        with patch.object(aps, "parse_editorial_notes", return_value=["Apple notes."]):
            tracks = aps.prefetch_tracks(self.store.read, self.store.write, get, ARTIST, ALBUM)
            described = aps.prefetch_description(self.store.read, self.store.write, get, ARTIST, ALBUM)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = AssertionError("a request was sent")
            self.assertEqual(metadata.album_details(artist=ARTIST, album=ALBUM)["tracks"], tracks)
            self.assertEqual(metadata.album_description(ARTIST, ALBUM), described)
            self.assertEqual(metadata._apple_album_url(ARTIST, ALBUM), "https://music.apple.com/us/album/dummy/1")


if __name__ == "__main__":
    unittest.main()
