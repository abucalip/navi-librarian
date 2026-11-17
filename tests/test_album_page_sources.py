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


MBID = "11111111-2222-3333-4444-555555555555"
DEEZER_ARTISTS = {"data": [{"name": ARTIST, "picture_xl": "http://x/xl.jpg", "picture_big": "http://x/b.jpg"}]}
YEAR_GROUPS = [{"title": ALBUM, "artist-credit": [{"artist": {"name": ARTIST}}], "first-release-date": "1994-08-22"}]


def mb_fetch(groups=None, fail=False):
    calls = []

    def fetch(query, limit):
        calls.append(query)
        if fail:
            raise RuntimeError("refused")
        return YEAR_GROUPS if groups is None else groups
    fetch.calls = calls
    return fetch


class YearTests(unittest.TestCase):
    def test_a_found_year_is_stored_under_the_routes_key(self):
        store = Store()
        self.assertEqual(aps.prefetch_year(store.read, store.write, mb_fetch(), None, ARTIST, ALBUM), 1994)
        self.assertEqual(store.data, {"album-year:v1:portishead:dummy": 1994})

    def test_a_stored_year_costs_no_request(self):
        store = Store()
        store.data["album-year:v1:portishead:dummy"] = 1994
        fetch = mb_fetch(fail=True)
        self.assertEqual(aps.prefetch_year(store.read, store.write, fetch, None, ARTIST, ALBUM), 1994)
        self.assertEqual(fetch.calls, [])

    def test_a_refused_musicbrainz_request_stores_nothing_and_does_not_fall_back_to_deezer(self):
        store, deezer = Store(), fake_get()
        self.assertIsNone(aps.prefetch_year(store.read, store.write, mb_fetch(fail=True), deezer, ARTIST, ALBUM))
        self.assertEqual(store.data, {})
        self.assertEqual(deezer.calls, [])

    def test_no_musicbrainz_match_falls_back_to_deezer_only_when_given(self):
        store = Store()
        self.assertIsNone(aps.prefetch_year(store.read, store.write, mb_fetch([]), None, ARTIST, ALBUM))
        self.assertEqual(store.data, {})
        self.assertEqual(aps.prefetch_year(store.read, store.write, mb_fetch([]), fake_get(), ARTIST, ALBUM), 1994)
        self.assertEqual(store.data, {"album-year:v1:portishead:dummy": 1994})


class LinksTests(unittest.TestCase):
    def test_a_complete_set_is_stored_under_the_clients_key(self):
        store = Store()
        links = aps.prefetch_links(store.read, store.write, aps.counting_get(fake_get()), ARTIST, ALBUM, MBID)
        self.assertEqual(set(links), {"apple_music", "deezer", "musicbrainz", "listenbrainz"})
        self.assertIn("album-links:v1:portishead|dummy|" + MBID, store.data)

    def test_a_refused_service_leaves_an_incomplete_set_that_is_not_stored(self):
        for down in ("api.deezer.com", "itunes.apple.com"):
            store = Store()
            links = aps.prefetch_links(store.read, store.write, aps.counting_get(fake_get(down=(down,))),
                                       ARTIST, ALBUM, MBID)
            self.assertNotEqual(len(links), 4)
            self.assertNotIn("album-links:v1:portishead|dummy|" + MBID, store.data)

    def test_the_stored_set_costs_no_request(self):
        store, get = Store(), fake_get(down=("deezer", "apple"))
        store.data["album-links:v1:portishead|dummy|"] = {"deezer": "https://www.deezer.com/album/7"}
        self.assertEqual(aps.prefetch_links(store.read, store.write, get, ARTIST, ALBUM, ""),
                         {"deezer": "https://www.deezer.com/album/7"})
        self.assertEqual(get.calls, [])


class ArtistImageTests(unittest.TestCase):
    def test_a_found_photo_is_stored_and_a_refusal_is_not(self):
        store = Store()
        ok = lambda url, **kw: Resp(DEEZER_ARTISTS)
        found = aps.prefetch_artist_image(store.read, store.write, ok, ARTIST)
        self.assertTrue(found["artwork_url"].startswith("https://"))
        self.assertIn("artist-image:v2:portishead", store.data)
        refused = Store()
        down = lambda url, **kw: (_ for _ in ()).throw(RuntimeError("refused"))
        self.assertTrue(aps.prefetch_artist_image(refused.read, refused.write, down, ARTIST)["retryable"])
        self.assertEqual(refused.data, {})


class ExtrasGatingTests(unittest.TestCase):
    def extras(self, caps):
        librarian = SimpleNamespace(_metadata_cache_get=lambda k, t: None, _metadata_cache_set=lambda k, v: None)
        found = op.entity_extras(librarian, ps.Spend(caps))
        return len(found["artists"]), len(found["albums"])

    def test_extras_follow_their_caps(self):
        self.assertEqual(self.extras({"musicbrainz": 1}), (0, 0))
        self.assertEqual(self.extras({"deezer": 1}), (1, 0))
        self.assertEqual(self.extras({"deezer": 1, "apple": 1}), (1, 0))
        self.assertEqual(self.extras({"deezer": 1, "apple": 1, "musicbrainz": 1}), (1, 1))


class HookGatingTests(unittest.TestCase):
    def hooks(self, caps):
        librarian = SimpleNamespace(_metadata_cache_get=lambda k, t: None, _metadata_cache_set=lambda k, v: None)
        return op.album_page_hooks(librarian, ps.Spend(caps))

    def test_without_new_caps_only_the_year_hook_is_given(self):
        self.assertEqual(set(self.hooks({"musicbrainz": 5, "listenbrainz": 5, "lastfm": 5})), {"album_year"})

    def test_tracklist_needs_deezer_and_description_needs_apple_and_wikipedia(self):
        self.assertEqual(set(self.hooks({"deezer": 1})), {"album_year", "deezer_tracks"})
        self.assertEqual(set(self.hooks({"apple": 1})), {"album_year"})
        self.assertEqual(set(self.hooks({"apple": 1, "wikipedia": 1})), {"album_year", "album_description"})

    def test_the_year_hooks_musicbrainz_request_is_counted_and_capped(self):
        store = Store()
        librarian = SimpleNamespace(_metadata_cache_get=store.read, _metadata_cache_set=store.write)
        spend = ps.Spend({"musicbrainz": 1})
        hook = op.album_page_hooks(librarian, spend)["album_year"]
        with patch.object(op.mb_year, "fetch_release_groups", return_value=YEAR_GROUPS) as fetch:
            self.assertEqual(hook(ARTIST, ALBUM), 1994)
            self.assertIsNone(hook("Other", "Album"))     # past the cap: refused before it is sent
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(spend.snapshot()["musicbrainz"], 1)
        self.assertEqual(list(store.data), ["album-year:v1:portishead:dummy"])

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

    def test_year_links_and_image_routes_answer_from_the_prefetched_rows(self):
        get = aps.counting_get(fake_get())
        for cache in (metadata._album_links_cache, metadata._artist_image_cache):
            cache.clear()
        links = aps.prefetch_links(self.store.read, self.store.write, get, ARTIST, ALBUM, MBID)
        year = aps.prefetch_year(self.store.read, self.store.write, mb_fetch(), None, ARTIST, ALBUM)
        image = aps.prefetch_artist_image(self.store.read, self.store.write,
                                          lambda url, **kw: Resp(DEEZER_ARTISTS), ARTIST)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client, \
                patch.object(metadata, "_musicbrainz_album_year", side_effect=AssertionError("a request was sent")):
            client.get.side_effect = AssertionError("a request was sent")
            self.assertEqual(metadata.album_page_links(ARTIST, ALBUM, MBID), links)
            self.assertEqual(metadata.album_year(ARTIST, ALBUM)["year"], year)
            self.assertEqual(metadata.artist_image(ARTIST), image)


if __name__ == "__main__":
    unittest.main()
