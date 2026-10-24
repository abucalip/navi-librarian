"""Offline tests for the daily lens pool gatherer (Engine 2, Phase 4, slice 2).

Every provider is a stub: no network call is made. Albums, artists and tags are placeholder data.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from discovery import lens_pool_gatherer as gatherer
from discovery.batch_metadata import LISTENBRAINZ_ARTIST_URL
from discovery.lens_lists import LENS_LIST_SIZE, build_lens_lists
from discovery.lenses import DEEP_CUTS, OBSESSIONS, REPEATED_TRACKS
from discovery.mbid_popularity import LASTFM_API_URL, MUSICBRAINZ_RELEASE_SEARCH_URL
from discovery.artist_tag_fallback import MUSICBRAINZ_GENRE_URL
from discovery.recommendations import music_key

DAY = "2026-10-24"
ON = {"engine2_lens_lists_enabled": True}
SEEDS = [("tag-a", "fam-a", "profile:a"), ("tag-b", "fam-b", "explore:b")]
HEADERS = {"User-Agent": "test"}


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


class _Net:
    """Routes MusicBrainz, ListenBrainz and Last.fm stubs and records every call."""

    def __init__(self, *, album=None, toptags=None, artist_genres=None, vocabulary=()):
        self.album = album or {}              # release MBID -> album listeners
        self.toptags = toptags or {}          # artist MBID -> [(tag, count)]
        self.artist_genres = artist_genres or {}  # artist MBID -> [genre names]
        self.vocabulary = list(vocabulary)
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params))
        if url == MUSICBRAINZ_RELEASE_SEARCH_URL:
            groups = params["query"][len("rgid:("):-1].split(" OR ")
            releases = [{"id": f"rel-{g}", "status": "Official", "date": "2001",
                         "release-group": {"id": g}} for g in groups]
            return _Response({"count": len(releases), "releases": releases})
        if url == MUSICBRAINZ_GENRE_URL:
            return _Response({"genres": [{"name": n} for n in self.vocabulary],
                              "genre-count": len(self.vocabulary)})
        if url == LISTENBRAINZ_ARTIST_URL:
            entries = [{"artist_mbid": m, "tag": {"artist": [
                {"tag": g, "genre_mbid": f"id-{g}"} for g in self.artist_genres[m]]}}
                for m in params["artist_mbids"].split(",") if m in self.artist_genres]
            return _Response(entries)
        assert url == LASTFM_API_URL, url
        if params["method"] == "album.getInfo":
            listeners = self.album.get(params["mbid"])
            return _Response({"album": {"listeners": str(listeners), "playcount": "1"}}
                             if listeners else {"error": 6})
        if params["method"] == "artist.gettoptags":
            tags = self.toptags.get(params["mbid"], [])
            return _Response({"toptags": {"tag": [{"name": n, "count": c} for n, c in tags]}})
        raise AssertionError(f"unexpected Last.fm method {params['method']}")

    def calls_to(self, url, method=None):
        return [p for u, p in self.calls if u == url and (method is None or p.get("method") == method)]


class _Cache:
    def __init__(self):
        self.store = {}

    def get(self, key, ttl_seconds=None, **_kwargs):
        return self.store.get(key)

    def set(self, key, value, **_kwargs):
        self.store[key] = value


def _album(n, artist_mbid, rgid):
    return {"artist": f"Artist {n}", "primary_artist": f"Artist {n}", "artist_mbid": artist_mbid,
            "album": f"Album {n}", "release_group_mbid": rgid, "score": 0.035, "tag_strength": 5.0,
            "tracks": [], "discovery_source": "listenbrainz_tag_radio",
            "discovery_sources": ["exploration_tag_search"], "regional_families": ["fam-a"],
            "regional_styles": ["profile:a"]}


def _listen(stamp, artist_mbid, name="Artist"):
    return {"listened_at": stamp, "track_metadata": {
        "artist_name": name, "track_name": "Track",
        "mbid_mapping": {"artist_mbids": [artist_mbid]}}}


class _Harness(unittest.TestCase):
    """Patches the radio supply (returns the given pools) and the seed builder (fixed seeds)."""

    def setUp(self):
        self.supply_calls = []
        self.pools = {}
        self.cache = _Cache()
        self.net = _Net()
        self.providers = SimpleNamespace(
            http_get=self.net, http_post=None, http_client=None, sleep=lambda _s: None,
            music_key=music_key, is_album_candidate=lambda *a, **k: True,
            metadata_cache_get=self.cache.get, metadata_cache_set=self.cache.set)
        self.seed_listens = []

    def supply(self, queries, *, providers, headers, albums, failures, state, lens, day):
        self.supply_calls.append({"lens": lens, "day": day, "queries": [q for q, _f, _s in queries],
                                  "headers": headers, "providers": providers})
        for album in self.pools.get(lens, []):
            albums[(album["primary_artist"], album["album"])] = dict(album)
        state["added"] = len(albums)
        return [(1, None) for _ in queries]

    def seeds(self, listens, artist_tags, **_kwargs):
        self.seed_listens.append(list(listens))
        return {lens.name: list(SEEDS) for lens in (REPEATED_TRACKS, DEEP_CUTS, OBSESSIONS)}

    def gather(self, listens=(), *, settings=ON, day=DAY):
        with mock.patch.object(gatherer, "run_deep_cuts_tag_supply", side_effect=self.supply), \
                mock.patch.object(gatherer, "lens_seed_queries", side_effect=self.seeds):
            return gatherer.gather_lens_pools(
                list(listens), day=day, providers=self.providers, headers=HEADERS,
                lastfm_api_key="key", settings_read=lambda: dict(settings))


class SettingGateTests(_Harness):
    def test_off_by_default_and_for_non_boolean_values_without_any_call(self):
        for settings in ({}, {"engine2_lens_lists_enabled": "true"}, {"engine2_lens_lists_enabled": 1},
                         {"engine2_lens_lists_enabled": False}):
            with self.subTest(settings=settings):
                self.pools = {DEEP_CUTS.name: [_album(1, "a1", "g1")]}
                out = self.gather([_listen(1_700_000_000, "a1")], settings=settings)
                self.assertEqual(out, {"status": "disabled", "day": DAY})
                self.assertEqual(self.net.calls, [])
                self.assertEqual(self.supply_calls, [])
                self.assertEqual(self.cache.store, {})

    def test_bad_day_is_refused_before_any_work(self):
        for day in ("2026-02-30", "20261024", "yesterday", 20261024, None):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.gather(day=day)
        self.assertEqual(self.net.calls, [])
        self.assertEqual(self.supply_calls, [])


class GatherTests(_Harness):
    def test_each_lens_runs_its_own_radio_scope_and_day(self):
        out = self.gather()
        self.assertEqual(out["status"], "gathered")
        self.assertEqual([c["lens"] for c in self.supply_calls],
                         [lens.name for lens in gatherer.LENS_LIST_ORDER])
        self.assertEqual({c["day"] for c in self.supply_calls}, {DAY})
        self.assertTrue(all(c["queries"] == ["tag-a", "tag-b"] for c in self.supply_calls))
        self.assertTrue(all(c["headers"] == HEADERS for c in self.supply_calls))
        self.assertEqual(out["seeds"][DEEP_CUTS.name], SEEDS)

    def test_lens_without_seeds_is_not_supplied(self):
        with mock.patch.object(gatherer, "lens_seed_queries",
                               return_value={DEEP_CUTS.name: [], REPEATED_TRACKS.name: SEEDS,
                                             OBSESSIONS.name: []}):
            with mock.patch.object(gatherer, "run_deep_cuts_tag_supply", side_effect=self.supply):
                out = gatherer.gather_lens_pools(
                    [], day=DAY, providers=self.providers, headers=HEADERS, lastfm_api_key="key",
                    settings_read=lambda: dict(ON))
        self.assertEqual([c["lens"] for c in self.supply_calls], [REPEATED_TRACKS.name])
        self.assertEqual(out["pools"][DEEP_CUTS.name], [])

    def test_popularity_uses_release_search_and_album_listeners_not_artist_lookups(self):
        self.pools = {DEEP_CUTS.name: [_album(1, "a1", "g1"), _album(2, "a2", "g2")]}
        self.net.album = {"rel-g1": 900}
        out = self.gather()
        self.assertEqual(out["popularity"]["g1"]["album_listeners"], 900)
        self.assertIsNone(out["popularity"]["g2"]["album_listeners"])
        self.assertEqual(self.net.calls_to(LASTFM_API_URL, "artist.getInfo"), [])
        self.assertTrue(self.net.calls_to(MUSICBRAINZ_RELEASE_SEARCH_URL))
        self.assertEqual(out["lenses"][DEEP_CUTS.name]["album_listeners"], 1)

    def test_last_fm_album_lookups_stay_within_the_lens_budget(self):
        self.pools = {DEEP_CUTS.name: [_album(n, f"a{n}", f"g{n}") for n in range(90)]}
        out = self.gather()
        album_calls = self.net.calls_to(LASTFM_API_URL, "album.getInfo")
        self.assertLessEqual(len(album_calls), gatherer.LENS_LASTFM_CALL_BUDGET)
        self.assertEqual(out["lenses"][DEEP_CUTS.name]["albums"], 90)

    def test_artist_genres_come_from_one_batch_per_lens_and_fallback_fills_thin_artists(self):
        self.pools = {DEEP_CUTS.name: [_album(1, "a1", "g1"), _album(2, "a2", "g2")]}
        self.net.artist_genres = {"a1": ["indie rock", "dream pop"], "a2": []}
        self.net.vocabulary = ["desert blues", "indie rock"]
        self.net.toptags = {"a2": [("desert blues", 50), ("seen live", 99)]}
        out = self.gather()
        self.assertEqual(out["artist_tags"]["a1"], ["dream pop", "indie rock"])
        self.assertEqual(out["artist_tags"]["a2"], [], "a2 has no MusicBrainz genre tags")
        self.assertEqual(out["fallback_tags"], {"a2": ["desert blues"]})
        batch_calls = self.net.calls_to(LISTENBRAINZ_ARTIST_URL)
        self.assertEqual([c["artist_mbids"] for c in batch_calls], ["a1,a2"],
                         "one artist batch for the pool, with no history artists to prefetch")

    def test_repeat_run_reuses_cached_album_listeners(self):
        self.pools = {DEEP_CUTS.name: [_album(1, "a1", "g1")]}
        self.net.album = {"rel-g1": 900}
        self.gather()
        self.net.calls.clear()
        out = self.gather()
        self.assertEqual(out["popularity"]["g1"]["album_listeners"], 900)
        self.assertEqual(self.net.calls_to(MUSICBRAINZ_RELEASE_SEARCH_URL), [])
        self.assertEqual(self.net.calls_to(LASTFM_API_URL, "album.getInfo"), [])

    def test_listens_stamped_in_1970_are_dropped_before_any_profile(self):
        self.pools = {}
        listens = [_listen(0, "zero-artist"), _listen(1_700_000_000, "recent-artist"),
                   _listen(1_700_000_100, "recent-artist")]
        self.gather(listens)
        self.assertEqual(len(self.seed_listens), 1)
        stamps = [listen["listened_at"] for listen in self.seed_listens[0]]
        self.assertEqual(stamps, [1_700_000_000, 1_700_000_100])
        batch = self.net.calls_to(LISTENBRAINZ_ARTIST_URL)[0]["artist_mbids"].split(",")
        self.assertIn("recent-artist", batch)
        self.assertNotIn("zero-artist", batch)

    def test_gathered_output_is_the_input_the_list_builder_takes(self):
        self.pools = {DEEP_CUTS.name: [_album(1, "a1", "g1")]}
        self.net.album = {"rel-g1": 900}
        self.net.artist_genres = {"a1": ["indie rock", "dream pop"]}
        out = self.gather()
        lists = build_lens_lists(
            out["pools"], day=out["day"], popularity=out["popularity"],
            artist_tags=out["artist_tags"], library_by_title={}, fallback_tags=out["fallback_tags"],
            seeds=out["seeds"], count=LENS_LIST_SIZE)
        self.assertEqual(set(lists), {lens.name for lens in gatherer.LENS_LIST_ORDER})
        self.assertTrue(all(payload["day"] == DAY for payload in lists.values()))


if __name__ == "__main__":
    unittest.main()
