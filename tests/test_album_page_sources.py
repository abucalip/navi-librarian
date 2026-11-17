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

    def test_a_definite_no_match_is_stored_by_the_worker_only_as_a_no_match_mark(self):
        store = Store()
        get = lambda url, **kw: Resp({"data": []})
        self.assertEqual(aps.prefetch_tracks(store.read, store.write, get, ARTIST, ALBUM), [])
        self.assertEqual(list(store.data), [aps.no_match_store_key("deezer", ARTIST, ALBUM)])


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


def no_match_get(deezer=None, itunes=None, down=()):
    """A ``get`` whose Deezer and iTunes searches answer with the given payloads (default: nothing matches)."""
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        if any(host in url for host in down):
            raise RuntimeError("refused")
        if "api.deezer.com/search/album" in url:
            return Resp(deezer if deezer is not None else {"data": []})
        if "itunes.apple.com" in url:
            return Resp(itunes if itunes is not None else {"results": []})
        raise AssertionError(url)
    get.calls = calls
    return get


class NoMatchTests(unittest.TestCase):
    """Efficiency K5: a definitive Deezer or Apple no-match is remembered for an hour; a failure is not."""

    def setUp(self):
        self.store = Store()
        self.now = [1_000_000.0]
        clock = patch.object(aps.negative_marks.time, "time", lambda: self.now[0])
        clock.start()
        self.addCleanup(clock.stop)

    def tracks(self, get):
        return aps.prefetch_tracks(self.store.read, self.store.write, get, ARTIST, ALBUM)

    def apple(self, get):
        return aps.apple_page_url(self.store.read, self.store.write, get, ARTIST, ALBUM)

    def test_a_deezer_no_match_is_skipped_within_the_hour_and_asked_again_after_it(self):
        get = no_match_get()
        self.tracks(get)
        self.now[0] += aps.NO_MATCH_TTL - 60
        self.tracks(get)
        self.assertEqual(len(get.calls), 1)
        self.now[0] += 120
        self.tracks(get)
        self.assertEqual(len(get.calls), 2, "the mark does not renew itself")

    def test_a_deezer_failure_or_error_body_writes_no_mark(self):
        self.tracks(no_match_get(down=("deezer",)))
        self.tracks(no_match_get(deezer={"error": {"type": "Exception", "message": "Quota limit exceeded", "code": 4}}))
        self.assertEqual(self.store.data, {})

    def test_a_deezer_match_is_unaffected(self):
        self.assertEqual([t["title"] for t in self.tracks(fake_get())], ["Mysterons"])
        self.assertEqual(list(self.store.data), [aps.details_store_key(ARTIST, ALBUM)])

    def test_an_apple_no_match_is_skipped_within_the_hour_and_never_stored_as_a_page(self):
        get = no_match_get()
        self.assertEqual(self.apple(get), (None, True))
        self.assertEqual(self.apple(get), (None, True))
        self.assertEqual(len(get.calls), 1)
        self.assertNotIn(aps.apple_url_store_key(ARTIST, ALBUM), self.store.data)
        self.now[0] += aps.NO_MATCH_TTL + 1
        self.apple(get)
        self.assertEqual(len(get.calls), 2)

    def test_an_apple_failure_writes_no_mark_and_a_match_is_stored_as_before(self):
        self.assertEqual(self.apple(no_match_get(down=("itunes",))), (None, False))
        self.assertEqual(self.store.data, {})
        url, answered = self.apple(fake_get())
        self.assertEqual((url, answered), ("https://music.apple.com/us/album/dummy/1", True))
        self.assertEqual(list(self.store.data), [aps.apple_url_store_key(ARTIST, ALBUM)])

    def test_links_skip_both_marked_services_and_the_set_is_not_stored(self):
        get = no_match_get()
        links = aps.prefetch_links(self.store.read, self.store.write, get, ARTIST, ALBUM, MBID)
        self.assertEqual(set(links), {"musicbrainz", "listenbrainz"})
        self.assertEqual(len(get.calls), 2)
        self.assertEqual(sorted(self.store.data), sorted(
            [aps.no_match_store_key("deezer", ARTIST, ALBUM), aps.no_match_store_key("apple", ARTIST, ALBUM)]),
            "only the marks: an incomplete set is never kept for the links' week")
        aps.prefetch_links(self.store.read, self.store.write, get, ARTIST, ALBUM, MBID)
        self.assertEqual(len(get.calls), 2, "no Deezer or Apple request within the hour")

    def test_a_refused_links_lookup_writes_no_mark(self):
        aps.prefetch_links(self.store.read, self.store.write, no_match_get(down=("deezer", "itunes")), ARTIST, ALBUM, MBID)
        self.assertEqual(self.store.data, {})

    def test_the_album_details_mark_also_spares_the_links_deezer_search(self):
        self.tracks(no_match_get())
        get = no_match_get(itunes=ITUNES)
        aps.prefetch_links(self.store.read, self.store.write, get, ARTIST, ALBUM, MBID)
        self.assertEqual([url for url in get.calls if "deezer" in url], [])

    def test_a_deezer_year_without_a_year_is_skipped_within_the_hour(self):
        get = no_match_get()
        for _ in range(2):
            self.assertIsNone(aps.deezer_year_remembered(self.store.read, self.store.write, get, ARTIST, ALBUM))
        self.assertEqual(len(get.calls), 1)
        self.assertEqual(list(self.store.data), [aps.no_match_store_key("deezer-year", ARTIST, ALBUM)])
        self.now[0] += aps.NO_MATCH_TTL + 1
        aps.deezer_year_remembered(self.store.read, self.store.write, get, ARTIST, ALBUM)
        self.assertEqual(len(get.calls), 2)

    def test_a_failed_deezer_year_writes_no_mark_and_a_found_year_is_unaffected(self):
        self.assertIsNone(aps.deezer_year_remembered(
            self.store.read, self.store.write, no_match_get(down=("deezer",)), ARTIST, ALBUM))
        self.assertEqual(self.store.data, {})
        self.assertEqual(aps.deezer_year_remembered(self.store.read, self.store.write, fake_get(), ARTIST, ALBUM), 1994)
        self.assertEqual(self.store.data, {})


class RouteNoMatchTests(unittest.TestCase):
    """Efficiency K5 on the routes: a restart within the hour sends no Deezer or Apple request for a no-match."""

    def setUp(self):
        self.store = Store()
        persistent_metadata.attach(self.store.read, self.store.write)
        self.addCleanup(persistent_metadata.detach)
        self.caches = (metadata._album_details_cache, metadata._apple_url_cache, metadata._album_links_cache,
                       metadata._album_description_cache)
        self.clear()
        self.addCleanup(self.clear)

    def clear(self):
        for cache in self.caches:
            cache.clear()

    def test_album_details_links_and_apple_page_read_the_marks(self):
        get = no_match_get()
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = get
            self.assertEqual(metadata.album_details(artist=ARTIST, album=ALBUM)["tracks"], [])
            self.assertIsNone(metadata._apple_album_url(ARTIST, ALBUM))
            sent = len(get.calls)
            self.clear()
            self.assertEqual(metadata.album_details(artist=ARTIST, album=ALBUM)["tracks"], [])
            self.assertEqual(set(metadata.album_page_links(ARTIST, ALBUM, mbid=MBID)), {"musicbrainz", "listenbrainz"})
            self.assertIsNone(metadata._apple_album_url(ARTIST, ALBUM))
        self.assertEqual(sent, 2)
        self.assertEqual(len(get.calls), 2, "nothing asked again within the hour")
        self.assertNotIn("album-links:v1:" + "|".join((ARTIST.casefold(), ALBUM.casefold(), MBID)), self.store.data)

    def test_the_year_route_skips_the_deezer_fallback_within_the_hour(self):
        get = no_match_get()
        with patch.object(metadata, "_musicbrainz_album_year", return_value=None), \
                patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = get
            for _ in range(2):
                self.assertIsNone(metadata.album_year(artist=ARTIST, album=ALBUM, librarian=None)["year"])
        self.assertEqual(len(get.calls), 1)

    def test_a_failed_route_lookup_writes_no_mark(self):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = no_match_get(down=("deezer", "itunes"))
            metadata.album_details(artist=ARTIST, album=ALBUM)
            metadata._apple_album_url(ARTIST, ALBUM)
        self.assertEqual(self.store.data, {})


class K6Tests(unittest.TestCase):
    """Efficiency K6: a found Deezer page is kept on its own; a Wikipedia no-article answer is marked for an hour."""

    def setUp(self):
        self.store = Store()
        self.now = [1_000_000.0]
        clock = patch.object(aps.negative_marks.time, "time", lambda: self.now[0])
        clock.start()
        self.addCleanup(clock.stop)

    def links(self, get):
        return aps.prefetch_links(self.store.read, self.store.write, get, ARTIST, ALBUM, MBID)

    def test_a_found_deezer_page_is_stored_and_reused_while_the_set_stays_incomplete(self):
        get = no_match_get(deezer=DEEZER_SEARCH)
        self.assertEqual(self.links(get)["deezer"], "https://www.deezer.com/album/7")
        self.assertEqual(self.store.data[aps.deezer_url_store_key(ARTIST, ALBUM)], "https://www.deezer.com/album/7")
        self.assertNotIn(aps.links_store_key(ARTIST, ALBUM, MBID), self.store.data, "the incomplete set is not stored")
        before = len([u for u in get.calls if "deezer" in u])
        self.assertEqual(self.links(get)["deezer"], "https://www.deezer.com/album/7")
        self.assertEqual(len([u for u in get.calls if "deezer" in u]), before, "no second Deezer request")

    def test_a_deezer_failure_stores_no_page(self):
        self.links(no_match_get(down=("deezer",)))
        self.assertNotIn(aps.deezer_url_store_key(ARTIST, ALBUM), self.store.data)

    def wikipedia(self, get):
        return aps.wikipedia_description_remembered(self.store.read, self.store.write, get, ARTIST, ALBUM)

    def test_a_wikipedia_no_article_is_skipped_within_the_hour_and_asked_after_it(self):
        get = lambda url, **kw: (calls.append(url), Resp({"pages": []}))[1]
        calls = []
        self.assertEqual(self.wikipedia(get), (None, True))
        self.assertEqual(self.wikipedia(get), (None, True))
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(self.store.data), [aps.no_match_store_key("wikipedia", ARTIST, ALBUM)])
        self.now[0] += aps.NO_MATCH_TTL + 1
        self.wikipedia(get)
        self.assertEqual(len(calls), 2, "the mark does not renew itself")

    def test_a_wikipedia_failure_or_a_found_article_writes_no_mark(self):
        self.assertEqual(self.wikipedia(fake_get(down=("wikipedia",))), (None, False))
        self.assertEqual(self.wikipedia(fake_get())[1], True)
        self.assertEqual(self.store.data, {})


if __name__ == "__main__":
    unittest.main()
