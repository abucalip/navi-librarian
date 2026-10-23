"""Offline tests for MBID-keyed Last.fm popularity (no network)."""
import unittest

from discovery.mbid_popularity import (
    ALBUM_CACHE_PREFIX,
    ARTIST_CACHE_PREFIX,
    LASTFM_API_URL,
    MUSICBRAINZ_RELEASE_SEARCH_URL,
    RELEASE_SEARCH_GROUPS,
    fetch_release_mbids,
    fetch_representative_releases,
    order_releases,
    resolve_popularity,
)
from discovery.batch_metadata import LISTENBRAINZ_RELEASE_GROUP_URL


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


class _Cache:
    def __init__(self):
        self.store = {}

    def get(self, key, **kwargs):
        return self.store.get(key)

    def set(self, key, value, **kwargs):
        self.store[key] = value


def _release(rid, group, status="Official", date="2000"):
    return {"id": rid, "status": status, "date": date, "release-group": {"id": group}}


class _Net:
    """Routes the three providers; records calls."""

    def __init__(self, releases=(), count=None, lb=None, album=None, artist=None, mb_status=200):
        self.releases, self.count, self.lb = list(releases), count, lb or {}
        self.album, self.artist, self.mb_status = album or {}, artist or {}, mb_status
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if url == MUSICBRAINZ_RELEASE_SEARCH_URL:
            page = self.releases[params["offset"]:params["offset"] + params["limit"]]
            count = len(self.releases) if self.count is None else self.count
            return _Response({"count": count, "releases": page}, self.mb_status)
        if url == LISTENBRAINZ_RELEASE_GROUP_URL:
            return _Response({g: {"release_group": {"caa_release_mbid": r}} for g, r in self.lb.items()})
        assert url == LASTFM_API_URL
        mbid = params["mbid"]
        if params["method"] == "artist.getInfo":
            stats = self.artist.get(mbid)
            return _Response({"artist": {"stats": {"listeners": str(stats), "playcount": "9"}}} if stats else {"error": 6})
        stats = self.album.get(mbid)
        return _Response({"album": {"listeners": str(stats), "playcount": "5"}} if stats else {"error": 6})

    def lastfm_calls(self, method=None):
        return [p for u, p in self.calls if u == LASTFM_API_URL and (method is None or p["method"] == method)]


def _cand(group, artist):
    return {"release_group_mbid": group, "artist_mbid": artist}


def _resolve(net, candidates, cache=None, **kw):
    cache = cache or _Cache()
    return resolve_popularity(net, candidates, api_key="k", headers={}, cache_get=cache.get,
                              cache_set=cache.set, **kw), cache


class OrderReleasesTests(unittest.TestCase):
    def test_official_first_then_earliest_undated_last(self):
        items = [("a", "Bootleg", "1990"), ("b", "Official", "2005"), ("c", "Official", "1999"), ("d", "Official", "")]
        self.assertEqual(order_releases(items), ["c", "b", "d", "a"])


class FetchReleaseMbidsTests(unittest.TestCase):
    def test_paginates_and_groups_releases(self):
        rels = [_release(f"r{i}", "g1") for i in range(150)] + [_release("x", "g2")]
        net = _Net(rels)
        out = fetch_release_mbids(net, ["g1", "g2"], headers={})
        self.assertEqual(len(out["g1"]), 150)
        self.assertEqual(out["g2"], ["x"])
        self.assertEqual(len(net.calls), 2)
        self.assertEqual(net.calls[0][1]["query"], "rgid:(g1 OR g2)")

    def test_ignores_releases_of_unrequested_groups(self):
        out = fetch_release_mbids(_Net([_release("r", "other")]), ["g1"], headers={})
        self.assertEqual(out, {})

    def test_chunks_groups(self):
        groups = [f"g{i}" for i in range(RELEASE_SEARCH_GROUPS + 1)]
        net = _Net([])
        fetch_release_mbids(net, groups, headers={})
        self.assertEqual(len(net.calls), 2)

    def test_failure_returns_empty_without_raising(self):
        self.assertEqual(fetch_release_mbids(_Net([_release("r", "g1")], mb_status=503), ["g1"], headers={}), {})

        def boom(*a, **k):
            raise RuntimeError("down")
        self.assertEqual(fetch_release_mbids(boom, ["g1"], headers={}), {})

    def test_sleeps_between_calls(self):
        slept = []
        fetch_release_mbids(_Net([_release("r", "g1")]), ["g1"], headers={}, sleep=slept.append)
        self.assertEqual(len(slept), 1)


class RepresentativeReleaseTests(unittest.TestCase):
    def test_returns_caa_release(self):
        net = _Net(lb={"g1": "rel1"})
        self.assertEqual(fetch_representative_releases(net, ["g1", "g2"], headers={}), {"g1": "rel1"})


class ResolvePopularityTests(unittest.TestCase):
    def test_album_found_by_release_mbid(self):
        net = _Net([_release("r1", "g1")], album={"r1": 1200}, artist={"a1": 5000})
        out, cache = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(out["g1"], {"album_listeners": 1200, "artist_listeners": 5000, "basis": "album"})
        self.assertEqual(cache.store[f"{ALBUM_CACHE_PREFIX}g1"]["listeners"], 1200)
        self.assertEqual(cache.store[f"{ARTIST_CACHE_PREFIX}a1"]["listeners"], 5000)

    def test_tries_next_release_until_lastfm_knows_one(self):
        rels = [_release("r1", "g1", date="1990"), _release("r2", "g1", date="1995")]
        net = _Net(rels, album={"r2": 77}, artist={"a1": 10})
        out, _ = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(out["g1"]["album_listeners"], 77)
        self.assertEqual(len(net.lastfm_calls("album.getInfo")), 2)

    def test_release_tries_are_bounded(self):
        rels = [_release(f"r{i}", "g1", date=f"19{i:02d}") for i in range(9)]
        net = _Net(rels, artist={"a1": 10})
        out, _ = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(len(net.lastfm_calls("album.getInfo")), 5)
        self.assertEqual(out["g1"]["basis"], "artist")

    def test_falls_back_to_listenbrainz_release_when_search_misses_group(self):
        net = _Net([], lb={"g1": "lbrel"}, album={"lbrel": 40}, artist={"a1": 10})
        out, _ = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(out["g1"]["album_listeners"], 40)

    def test_album_miss_is_cached_and_not_retried(self):
        net = _Net([_release("r1", "g1")], artist={"a1": 10})
        out, cache = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(cache.store[f"{ALBUM_CACHE_PREFIX}g1"], {"listeners": None})
        before = len(net.calls)
        _resolve(net, [_cand("g1", "a1")], cache=cache)
        self.assertEqual(len(net.calls), before)

    def test_cached_values_cost_no_calls(self):
        cache = _Cache()
        cache.set(f"{ALBUM_CACHE_PREFIX}g1", {"listeners": 5, "playcount": 1})
        cache.set(f"{ARTIST_CACHE_PREFIX}a1", {"listeners": 9, "playcount": 1})
        net = _Net()
        out, _ = _resolve(net, [_cand("g1", "a1")], cache=cache)
        self.assertEqual(net.calls, [])
        self.assertEqual(out["g1"]["album_listeners"], 5)

    def test_distinct_artists_are_looked_up_once(self):
        net = _Net([_release("r1", "g1"), _release("r2", "g2")], album={"r1": 1, "r2": 2}, artist={"a1": 10})
        _resolve(net, [_cand("g1", "a1"), _cand("g2", "a1")])
        self.assertEqual(len(net.lastfm_calls("artist.getInfo")), 1)

    def test_budget_stops_lastfm_and_does_not_cache_unanswered(self):
        net = _Net([_release("r1", "g1")], album={"r1": 1}, artist={"a1": 10})
        out, cache = _resolve(net, [_cand("g1", "a1")], max_lastfm_calls=1)
        self.assertEqual(len(net.lastfm_calls()), 1)
        self.assertNotIn(f"{ALBUM_CACHE_PREFIX}g1", cache.store)
        self.assertEqual(out["g1"]["basis"], "artist")

    def test_lastfm_exception_is_not_cached_and_does_not_raise(self):
        def get(url, params=None, **kw):
            if url == LASTFM_API_URL:
                raise RuntimeError("down")
            return _Response({"count": 0, "releases": []})
        cache = _Cache()
        out = resolve_popularity(get, [_cand("g1", "a1")], api_key="k", headers={},
                                 cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(out["g1"]["basis"], "none")
        self.assertEqual(cache.store, {})

    def test_candidates_without_release_group_are_omitted(self):
        out, _ = _resolve(_Net(), [{"artist_mbid": "a1"}])
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
