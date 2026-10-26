"""Discogs client, genre pages and Discogs styles in similar artists (contract sections 3.4, 5.2, 7)."""

import json
import threading
import unittest

from discovery.search.artist_sections import ArtistNetwork, similar_items
from discovery.search.cache import genre_cache_key, purge_stale_generations
from discovery.search.genre_page import (
    GenreNetwork,
    genre_capabilities,
    genre_sections,
    json_sections,
    normalize_tag,
)
from discovery.search.index import STATE_BUILDING, STATE_FRESH, IndexView, build_owned_data
from discovery.search.limiter import SourceLimiter
from discovery.search.merge import OwnedKeys
from discovery.search.providers import (
    DISCOGS_ATTRIBUTION,
    DiscogsSearch,
    MusicBrainzSearch,
    ProviderError,
    album_candidate,
    artist_candidate,
)

TOKEN = "tok_secret-123"


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class Get:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.requests.append((url, params, headers))
        return self.responses.pop(0)


def plenty():
    return 10.0


def discogs(get):
    return DiscogsSearch(get=get, limiter=SourceLimiter({"discogs": 0.0}), token=TOKEN)


MASTERS = {"results": [
    {"title": "Slowdive - Souvlaki", "year": "1993", "style": ["Shoegaze", "Dream Pop"]},
    {"title": "Slowdive - Just for a Day", "year": "1991", "style": ["Shoegaze"]},
    {"title": "Slowdive & Friends - Other", "year": "1995", "style": ["Ambient"]},
    {"title": "No separator here", "year": "1990"},
]}


class DiscogsSearchTests(unittest.TestCase):
    def test_token_is_sent_in_the_header_and_never_in_the_url_or_params(self):
        get = Get(Response(payload=MASTERS))
        discogs(get).style_albums("Shoegaze", remaining=plenty, cancelled=threading.Event())
        url, params, headers = get.requests[0]
        self.assertEqual(headers["Authorization"], f"Discogs token={TOKEN}")
        self.assertNotIn(TOKEN, url + json.dumps(params))
        self.assertEqual(params["style"], "Shoegaze")
        self.assertEqual(params["type"], "master")

    def test_style_albums_split_artist_and_title_and_skip_unparseable_titles(self):
        get = Get(Response(payload=MASTERS))
        albums = discogs(get).style_albums("shoegaze", remaining=plenty, cancelled=threading.Event())
        self.assertEqual(
            [(a["artist"], a["name"], a["year"], a["source"]) for a in albums],
            [("Slowdive", "Souvlaki", 1993, "discogs"), ("Slowdive", "Just for a Day", 1991, "discogs"),
             ("Slowdive & Friends", "Other", 1995, "discogs")],
        )

    def test_artist_styles_count_only_that_artists_masters_most_frequent_first(self):
        get = Get(Response(payload=MASTERS))
        styles = discogs(get).artist_styles("Slowdive", remaining=plenty, cancelled=threading.Event())
        self.assertEqual(styles, [{"name": "shoegaze"}, {"name": "dream pop"}])

    def test_429_is_rate_limited_and_other_failures_are_failed(self):
        for response, state in ((Response(429), "rate_limited"), (Response(500), "failed")):
            with self.assertRaises(ProviderError) as caught:
                discogs(Get(response)).style_albums("x", remaining=plenty, cancelled=threading.Event())
            self.assertEqual(caught.exception.state, state)

    def test_pacing_refusal_makes_no_request(self):
        get = Get()
        limiter = SourceLimiter({"discogs": 100.0}, clock=lambda: 0.0, sleep=lambda s: None)
        limiter.admit("discogs", 1.0)
        client = DiscogsSearch(get=get, limiter=limiter, token=TOKEN)
        with self.assertRaises(ProviderError) as caught:
            client.style_albums("x", remaining=lambda: 1.0, cancelled=threading.Event())
        self.assertEqual(caught.exception.state, "rate_limited")
        self.assertEqual(get.requests, [])

    def test_text_search_reads_artists_without_the_disambiguation_suffix_and_albums_from_masters(self):
        get = Get(
            Response(payload={"results": [{"title": "Ash (2)"}, {"title": "Ride"}]}),
            Response(payload=MASTERS),
        )
        client = discogs(get)
        cancelled = threading.Event()
        artists = client.artists("ash", remaining=plenty, cancelled=cancelled)
        albums = client.albums("slowdive", remaining=plenty, cancelled=cancelled)
        self.assertEqual([(a["name"], a["source"], a["mbid"]) for a in artists], [("Ash", "discogs", None), ("Ride", "discogs", None)])
        self.assertEqual(albums[0]["artist"], "Slowdive")
        self.assertEqual(get.requests[0][1]["type"], "artist")
        self.assertEqual(get.requests[1][1]["type"], "master")
        self.assertEqual(get.requests[1][1]["q"], "slowdive")

    def test_musicbrainz_tag_queries(self):
        get = Get(
            Response(payload={"artists": [{"id": "a1", "name": "Slowdive"}]}),
            Response(payload={"release-groups": [
                {"id": "r1", "title": "Souvlaki", "first-release-date": "1993-06-01",
                 "artist-credit": [{"name": "Slowdive"}]},
                {"id": "r2", "title": "Live", "secondary-types": ["Live"], "artist-credit": [{"name": "Slowdive"}]},
            ]}),
        )
        mb = MusicBrainzSearch(get=get, limiter=SourceLimiter({}), pause=lambda s: None)
        cancelled = threading.Event()
        artists = mb.artists_by_tag("shoegaze", remaining=plenty, cancelled=cancelled)
        albums = mb.albums_by_tag("shoegaze", remaining=plenty, cancelled=cancelled)
        self.assertEqual([a["name"] for a in artists], ["Slowdive"])
        self.assertEqual([a["name"] for a in albums], ["Souvlaki"])
        self.assertEqual(get.requests[0][1]["query"], 'tag:"shoegaze"')
        self.assertEqual(get.requests[1][1]["query"], 'tag:"shoegaze" AND primarytype:album')


class Store:
    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, payload):
        self.data[key] = payload


class FakeMB:
    def __init__(self, artists=(), albums=(), fail=False):
        self.artists, self.albums, self.fail, self.calls = list(artists), list(albums), fail, 0

    def artists_by_tag(self, tag, *, remaining, cancelled):
        self.calls += 1
        if self.fail:
            raise ProviderError("failed")
        return self.artists

    def albums_by_tag(self, tag, *, remaining, cancelled):
        if self.fail:
            raise ProviderError("failed")
        return self.albums


class FakeDiscogs:
    def __init__(self, albums=()):
        self.albums, self.calls = list(albums), 0

    def style_albums(self, style, *, remaining, cancelled):
        self.calls += 1
        return self.albums


def owned_view(state=STATE_FRESH):
    if state != STATE_FRESH:
        return IndexView(STATE_BUILDING, None, "index_building")
    data = build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Ride", "album_count": 1}, {"id": "ar2", "name": "Adele", "album_count": 1}],
        albums=[
            {"id": "al1", "artist": "Ride", "artist_id": "ar1", "album": "Nowhere", "year": 1990,
             "song_count": 8, "genre": "Shoegaze"},
            {"id": "al2", "artist": "Adele", "artist_id": "ar2", "album": "21", "year": 2011,
             "song_count": 11, "genre": "Pop"},
        ],
        songs=[],
    )
    return IndexView(STATE_FRESH, data, None)


def genre_network(mb=None, dg=None, store=None, generation=0):
    store = store or Store()
    return GenreNetwork(
        musicbrainz=mb or FakeMB(), discogs=dg, discogs_generation=generation,
        cache_read=store.read, cache_write=store.write,
    )


class GenreSectionsTests(unittest.TestCase):
    def test_owned_items_match_album_genre_case_insensitively_and_come_first(self):
        mb = FakeMB(
            artists=[artist_candidate("musicbrainz", "Slowdive", "m1"), artist_candidate("musicbrainz", "Ride", "m2")],
            albums=[album_candidate("musicbrainz", "Souvlaki", "Slowdive", 1993, "rg1")],
        )
        sections, partial, _ = genre_sections(owned_view(), genre_network(mb), normalize_tag("  SHOEGAZE "))
        artists = sections["artists"]["items"]
        self.assertEqual([(i["name"], i["owned"]) for i in artists], [("Ride", True), ("Slowdive", False)])
        albums = sections["albums"]["items"]
        self.assertEqual([(i["name"], i["owned"]) for i in albums], [("Nowhere", True), ("Souvlaki", False)])
        self.assertFalse(partial)

    def test_discogs_items_are_merged_deduplicated_and_attributed(self):
        mb = FakeMB(albums=[album_candidate("musicbrainz", "Souvlaki", "Slowdive", 1993, "rg1")])
        dg = FakeDiscogs([
            album_candidate("discogs", "Souvlaki", "Slowdive", 1993, None),
            album_candidate("discogs", "Loveless", "My Bloody Valentine", 1991, None),
        ])
        sections, _, _ = genre_sections(owned_view(), genre_network(mb, dg), "shoegaze")
        by_name = {i["name"]: i for i in sections["albums"]["items"]}
        self.assertEqual(by_name["Souvlaki"]["sources"], ["musicbrainz", "discogs"])
        self.assertEqual(by_name["Souvlaki"]["attribution"], DISCOGS_ATTRIBUTION)
        self.assertEqual(by_name["Loveless"]["sources"], ["discogs"])
        self.assertEqual(by_name["Loveless"]["attribution"], DISCOGS_ATTRIBUTION)
        self.assertNotIn("attribution", by_name["Nowhere"])
        artist_names = [i["name"] for i in sections["artists"]["items"]]
        self.assertIn("My Bloody Valentine", artist_names)

    def test_musicbrainz_only_items_have_no_attribution(self):
        mb = FakeMB(albums=[album_candidate("musicbrainz", "Souvlaki", "Slowdive", 1993, "rg1")])
        sections, _, _ = genre_sections(owned_view(), genre_network(mb), "shoegaze")
        self.assertTrue(all("attribution" not in i for i in sections["albums"]["items"]))

    def test_failed_source_makes_the_sections_incomplete_and_the_page_partial(self):
        sections, partial, _ = genre_sections(owned_view(), genre_network(FakeMB(fail=True)), "shoegaze")
        self.assertEqual(sections["albums"]["reason"], "source_failed")
        self.assertFalse(sections["albums"]["complete"])
        self.assertEqual([i["name"] for i in sections["albums"]["items"]], ["Nowhere"])
        self.assertTrue(partial)

    def test_building_index_still_serves_network_items_and_is_partial(self):
        mb = FakeMB(artists=[artist_candidate("musicbrainz", "Slowdive", "m1")])
        sections, partial, _ = genre_sections(owned_view(STATE_BUILDING), genre_network(mb), "shoegaze")
        self.assertEqual([i["name"] for i in sections["artists"]["items"]], ["Slowdive"])
        self.assertTrue(partial)

    def test_results_are_cached_by_source_generation_and_a_new_generation_refetches(self):
        store = Store()
        dg = FakeDiscogs([album_candidate("discogs", "Loveless", "My Bloody Valentine", 1991, None)])
        for generation, expected_calls in ((1, 1), (1, 1), (2, 2)):
            genre_sections(owned_view(), genre_network(FakeMB(), dg, store, generation), "shoegaze")
            self.assertEqual(dg.calls, expected_calls)
        self.assertIn(genre_cache_key("discogs", 1, "shoegaze", "album"), store.data)
        self.assertIn(genre_cache_key("discogs", 2, "shoegaze", "album"), store.data)
        self.assertNotIn(TOKEN, json.dumps(store.data))

    def test_failures_are_not_cached(self):
        store = Store()
        genre_sections(owned_view(), genre_network(FakeMB(fail=True), None, store), "shoegaze")
        self.assertEqual(store.data, {})

    def test_a_source_that_misses_the_deadline_reports_deadline_and_deadline_hit(self):
        release = threading.Event()
        self.addCleanup(release.set)

        class SlowMB(FakeMB):
            def artists_by_tag(self, tag, *, remaining, cancelled):
                release.wait(5)
                return []

        net = genre_network(SlowMB(albums=[album_candidate("musicbrainz", "Souvlaki", "Slowdive", 1993, "rg1")]))
        net.deadline_seconds = 0.05
        sections, partial, deadline_hit = genre_sections(owned_view(), net, "shoegaze")
        self.assertEqual(sections["artists"]["reason"], "deadline")
        self.assertFalse(sections["artists"]["complete"])
        self.assertIsNone(sections["albums"]["reason"])
        self.assertTrue(partial)
        self.assertTrue(deadline_hit)

    def test_no_deadline_hit_when_every_source_answers(self):
        _, _, deadline_hit = genre_sections(owned_view(), genre_network(), "shoegaze")
        self.assertFalse(deadline_hit)

    def test_json_sections_drop_the_section_key(self):
        sections, _, _ = genre_sections(owned_view(), genre_network(), "shoegaze")
        self.assertTrue(all("section" not in s for s in json_sections(sections).values()))

    def test_purge_covers_genre_entries_of_old_generations(self):
        calls = []
        purge_stale_generations(lambda prefix, keep: calls.append((prefix, keep)) or 0, "discogs", 3)
        self.assertIn(("genre:discogs:", "genre:discogs:3:"), calls)
        self.assertIn(("search:discogs:", "search:discogs:3:"), calls)


class GenreCapabilitiesTests(unittest.TestCase):
    def test_discogs_states(self):
        without = genre_capabilities(owned_view(), genre_network())
        self.assertEqual(without["sources"]["discogs"], {"available": False, "reason": "source_disabled"})
        withit = genre_capabilities(owned_view(), genre_network(dg=FakeDiscogs()))
        self.assertEqual(withit["sources"]["discogs"], {"available": True, "reason": None})
        self.assertNotIn(TOKEN, json.dumps(withit))

    def test_sections_are_available_from_the_network_while_the_index_builds(self):
        caps = genre_capabilities(owned_view(STATE_BUILDING), genre_network())
        self.assertTrue(caps["sections"]["artists"]["available"])
        self.assertFalse(caps["owned_index"]["available"])


GENRE_MASTERS = {"results": [
    {"title": "Slowdive - Souvlaki", "style": ["Shoegaze", "Dream Pop"], "genre": ["Rock"]},
    {"title": "Ride - Nowhere", "style": ["Shoegaze", "Indie Rock"], "genre": ["Rock"]},
]}


class GenreSearchTests(unittest.TestCase):
    def test_discogs_genres_are_the_styles_and_genres_on_results_that_contain_the_query(self):
        client = discogs(Get(Response(payload=GENRE_MASTERS)))
        found = client.genres("shoe", remaining=plenty, cancelled=threading.Event())
        self.assertEqual([(g["name"], g["source"], g["type"]) for g in found], [("Shoegaze", "discogs", "genre")])
        found = discogs(Get(Response(payload=GENRE_MASTERS))).genres("rock", remaining=plenty, cancelled=threading.Event())
        self.assertEqual(sorted(g["key"] for g in found), ["indie rock", "rock"])

    def test_musicbrainz_genre_list_is_one_plain_text_request(self):
        get = Get(Response(payload={}))
        get.responses[0].text = "2 tone\nshoegaze\n\nacid jazz\n"
        mb = MusicBrainzSearch(get=get, limiter=SourceLimiter({}), pause=lambda s: None)
        names = mb.genre_names(remaining=plenty, cancelled=threading.Event())
        self.assertEqual(names, ["2 tone", "shoegaze", "acid jazz"])
        self.assertEqual(get.requests[0][0], "https://musicbrainz.org/ws/2/genre/all")
        self.assertEqual(get.requests[0][1], {"fmt": "txt"})

    def test_an_empty_musicbrainz_list_is_a_failure_not_an_answer(self):
        get = Get(Response(payload={}))
        get.responses[0].text = "\n"
        mb = MusicBrainzSearch(get=get, limiter=SourceLimiter({}), pause=lambda s: None)
        with self.assertRaises(ProviderError):
            mb.genre_names(remaining=plenty, cancelled=threading.Event())

    def search(self, store, get, settings=None):
        from discovery.search.network import external_search

        return external_search(
            settings_read=lambda: settings or {}, cache_read=store.read, cache_write=store.write, http_get=get,
            limiter=SourceLimiter({}),
        )

    def run_parts(self, search, query="shoe"):
        cancelled = threading.Event()
        return {
            (part.source, part.kind): part.fetch(remaining=plenty, cancelled=cancelled)
            for part in search._parts_for(query, ["genre"])
        }

    def test_musicbrainz_list_is_fetched_once_cached_and_filtered_per_query(self):
        store = Store()
        get = Get(Response(payload={}))
        get.responses[0].text = "2 tone\nshoegaze\nacid jazz\nshoegaze revival\n"
        search = self.search(store, get)
        first = self.run_parts(search, "shoegaze")
        self.assertEqual([g["name"] for g in first[("musicbrainz", "genre")]], ["shoegaze", "shoegaze revival"])
        second = self.run_parts(search, "jazz")  # served from the cached list: no second request
        self.assertEqual([g["name"] for g in second[("musicbrainz", "genre")]], ["acid jazz"])
        self.assertEqual(len(get.requests), 1)

    def test_discogs_genre_part_exists_only_with_a_token(self):
        self.assertEqual(sorted(k for k in self.run_parts_keys({})), [("musicbrainz", "genre")])
        self.assertEqual(sorted(self.run_parts_keys({"discogs_token": TOKEN})),
                         [("discogs", "genre"), ("musicbrainz", "genre")])

    def run_parts_keys(self, settings):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DISCOGS_TOKEN", None)
            search = self.search(Store(), Get(), settings)
        return [(p.source, p.kind) for p in search._parts_for("shoe", ["genre"])]

    def test_genre_results_have_the_contract_fields_and_skip_genres_the_library_has(self):
        from discovery.search.merge import fresh_candidates, shape_result
        from discovery.search.providers import genre_candidate

        candidates = [genre_candidate("musicbrainz", "Shoegaze"), genre_candidate("musicbrainz", "Shoegaze revival")]
        owned = OwnedKeys(owned_view().data)
        fresh = fresh_candidates(candidates, query="shoegaze", owned=owned, emitted=[])
        self.assertEqual([c["name"] for c in fresh], ["Shoegaze revival"])  # "Shoegaze" is an owned genre
        result = shape_result(fresh[0])
        self.assertEqual(result["type"], "genre")
        self.assertEqual(result["tag"], "shoegaze revival")
        self.assertEqual(result["tag_source"], "musicbrainz")
        self.assertFalse(result["owned"])
        self.assertEqual(result["sources"], ["musicbrainz"])
        self.assertIsNone(result["artwork_url"])
        discogs_result = shape_result(genre_candidate("discogs", "Dream Pop"))
        self.assertEqual(discogs_result["attribution"], DISCOGS_ATTRIBUTION)
        self.assertEqual(discogs_result["tag_source"], "discogs")

    def test_dedupes_the_same_genre_from_two_sources_keeping_the_first(self):
        from discovery.search.merge import fresh_candidates
        from discovery.search.providers import genre_candidate

        emitted = []
        fresh = fresh_candidates(
            [genre_candidate("musicbrainz", "dream pop"), genre_candidate("discogs", "Dream Pop")],
            query="dream", owned=OwnedKeys(None), emitted=emitted,
        )
        self.assertEqual([c["source"] for c in fresh], ["musicbrainz"])


class SearchWiringTests(unittest.TestCase):
    def parts(self, settings):
        from discovery.search.network import external_search
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DISCOGS_TOKEN", None)
            search = external_search(
                settings_read=lambda: settings, cache_read=lambda k: None, cache_write=lambda k, v: None,
                http_get=Get(),
            )
        return search._parts_for("ash", ["artist", "album"])

    def test_discogs_is_queried_exactly_when_it_is_reported_available(self):
        with_token = self.parts({"discogs_token": TOKEN, "discogs_generation": 3})
        self.assertEqual(sorted((p.source, p.kind) for p in with_token if p.source == "discogs"),
                         [("discogs", "album"), ("discogs", "artist")])
        self.assertTrue(all(":3:" in p.key for p in with_token if p.source == "discogs"))
        self.assertNotIn(TOKEN, json.dumps([p.key for p in with_token]))
        self.assertFalse([p for p in self.parts({}) if p.source == "discogs"])

    def test_discogs_search_results_carry_the_attribution(self):
        from discovery.search.merge import shape_result

        artist = shape_result(artist_candidate("discogs", "Ride", None))
        album = shape_result(album_candidate("discogs", "Nowhere", "Ride", 1990, None))
        other = shape_result(artist_candidate("musicbrainz", "Ride", "m1"))
        self.assertEqual(artist["attribution"], DISCOGS_ATTRIBUTION)
        self.assertEqual(album["attribution"], DISCOGS_ATTRIBUTION)
        self.assertNotIn("attribution", other)


class SimilarStylesTests(unittest.TestCase):
    class Lastfm:
        def similar(self, name, *, remaining, cancelled):
            return [{"name": "Ride", "mbid": "m-ride", "match": 0.5}]

    class Styles:
        def artist_styles(self, name, *, remaining, cancelled):
            return [{"name": "shoegaze"}]

    class MB:
        def artist_tags(self, mbid, *, remaining, cancelled):
            return []

        def artists(self, query, *, remaining, cancelled):
            return [artist_candidate("musicbrainz", "Slowdive", "m-sd")]

    def run_similar(self, with_discogs):
        store = Store()
        net = ArtistNetwork(
            musicbrainz=self.MB(), popularity=lambda m, c: {}, bio=lambda n: None,
            cache_read=store.read, cache_write=store.write,
            lastfm=self.Lastfm(), discogs=self.Styles() if with_discogs else None,
        )
        return similar_items(
            net, "Slowdive", None, OwnedKeys(None),
            remaining=plenty, cancelled=threading.Event(), known_mbid="m-sd",
        ), store

    def test_discogs_styles_add_shared_tags_with_attribution(self):
        section, store = self.run_similar(True)
        item = section["items"][0]
        self.assertIn("Shared tags: shoegaze", item["reasons"])
        self.assertEqual(item["attribution"], DISCOGS_ATTRIBUTION)
        self.assertTrue(any(k.startswith("search:discogs:0:artist-styles:") for k in store.data))

    def test_styles_of_one_candidate_never_attribute_another_candidates_tag(self):
        from discovery.search.similar import fuse_similar

        records = [
            {"source": "lastfm", "name": "Ride", "mbid": "m-ride", "match": 0.5},
            {"source": "lastfm", "name": "Lush", "mbid": "m-lush", "match": 0.4},
        ]
        items = {
            item["name"]: item
            for item in fuse_similar(
                records, "Slowdive", "m-sd", OwnedKeys(None),
                seed_tags={"shoegaze"},
                candidate_tags={"m-ride": {"shoegaze"}, "m-lush": {"shoegaze"}},
                seed_styles=set(),
                candidate_styles={"m-ride": {"shoegaze"}},  # Discogs supplied the tag for Ride only
            )
        }
        self.assertEqual(items["Ride"]["attribution"], DISCOGS_ATTRIBUTION)
        self.assertNotIn("attribution", items["Lush"])
        self.assertIn("Shared tags: shoegaze", items["Lush"]["reasons"])

    def test_without_a_token_there_is_no_discogs_call_or_attribution(self):
        section, store = self.run_similar(False)
        self.assertNotIn("attribution", section["items"][0])
        self.assertFalse(any(k.startswith("search:discogs") for k in store.data))


if __name__ == "__main__":
    unittest.main()
