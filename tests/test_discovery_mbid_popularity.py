"""Offline tests for MBID-keyed ListenBrainz popularity (no network)."""
import unittest

from discovery.mbid_popularity import resolve_popularity
from integrations.listenbrainz.popularity import (
    ARTIST_POPULARITY_CACHE_PREFIX,
    LISTENBRAINZ_ARTIST_POPULARITY_URL,
    LISTENBRAINZ_POPULARITY_URL,
    POPULARITY_CACHE_PREFIX,
)


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


class _PostNet:
    """Stubs ListenBrainz release-group and artist popularity POST endpoints."""

    def __init__(self, *, album=None, artist=None, status=200):
        self.album = album or {}
        self.artist = artist or {}
        self.status = status
        self.calls = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        payload = dict(json or {})
        self.calls.append((url, payload))
        if self.status != 200:
            return _Response({}, self.status)
        if url == LISTENBRAINZ_POPULARITY_URL:
            return _Response([
                {
                    "release_group_mbid": mbid,
                    "total_user_count": self.album[mbid],
                    "total_listen_count": self.album[mbid] * 5,
                }
                for mbid in payload["release_group_mbids"]
                if mbid in self.album
            ])
        assert url == LISTENBRAINZ_ARTIST_POPULARITY_URL, url
        return _Response([
            {
                "artist_mbid": mbid,
                "total_user_count": self.artist[mbid],
                "total_listen_count": self.artist[mbid] * 9,
            }
            for mbid in payload["artist_mbids"]
            if mbid in self.artist
        ])

    def calls_to(self, url):
        return [payload for u, payload in self.calls if u == url]


def _cand(group, artist):
    return {"release_group_mbid": group, "artist_mbid": artist}


def _resolve(net, candidates, cache=None, **kw):
    cache = cache or _Cache()
    return resolve_popularity(
        net, candidates, headers={}, cache_get=cache.get, cache_set=cache.set, **kw
    ), cache


class ResolvePopularityTests(unittest.TestCase):
    def test_album_and_artist_found_by_mbid(self):
        net = _PostNet(album={"g1": 1200}, artist={"a1": 5000})
        out, cache = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(
            out["g1"],
            {"album_listeners": 1200, "release_year": None, "artist_listeners": 5000, "basis": "album"},
        )
        self.assertEqual(cache.store[f"{POPULARITY_CACHE_PREFIX}g1"]["listeners"], 1200)
        self.assertEqual(cache.store[f"{ARTIST_POPULARITY_CACHE_PREFIX}a1"]["listeners"], 5000)

    def test_artist_fallback_when_album_unknown(self):
        net = _PostNet(album={}, artist={"a1": 500})
        out, _ = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(
            out["g1"],
            {"album_listeners": None, "release_year": None, "artist_listeners": 500, "basis": "artist"},
        )

    def test_basis_none_when_both_unknown(self):
        net = _PostNet()
        out, _ = _resolve(net, [_cand("g1", "a1")])
        self.assertEqual(
            out["g1"],
            {"album_listeners": None, "release_year": None, "artist_listeners": None, "basis": "none"},
        )

    def test_cached_values_cost_no_calls(self):
        cache = _Cache()
        cache.set(f"{POPULARITY_CACHE_PREFIX}g1", {"listeners": 5, "playcount": 10, "tags": []})
        cache.set(f"{ARTIST_POPULARITY_CACHE_PREFIX}a1", {"listeners": 9, "playcount": 20, "tags": []})
        net = _PostNet()
        out, _ = _resolve(net, [_cand("g1", "a1")], cache=cache)
        self.assertEqual(net.calls, [])
        self.assertEqual(out["g1"]["album_listeners"], 5)
        self.assertEqual(out["g1"]["artist_listeners"], 9)

    def test_distinct_artists_are_batched_once(self):
        net = _PostNet(album={"g1": 1, "g2": 2}, artist={"a1": 10})
        _resolve(net, [_cand("g1", "a1"), _cand("g2", "a1")])
        artist_calls = net.calls_to(LISTENBRAINZ_ARTIST_POPULARITY_URL)
        self.assertEqual(artist_calls, [{"artist_mbids": ["a1"]}])

    def test_http_failure_and_exception_are_not_cached_and_never_raise(self):
        out, cache = _resolve(_PostNet(status=503), [_cand("g1", "a1")])
        self.assertEqual(out["g1"]["basis"], "none")
        self.assertEqual(cache.store, {})

        def boom(*_a, **_k):
            raise RuntimeError("down")

        cache2 = _Cache()
        out2 = resolve_popularity(boom, [_cand("g1", "a1")], cache_get=cache2.get, cache_set=cache2.set)
        self.assertEqual(out2["g1"]["basis"], "none")
        self.assertEqual(cache2.store, {})

    def test_candidates_without_release_group_are_omitted_with_no_calls(self):
        net = _PostNet()
        out, _ = _resolve(net, [{"artist_mbid": "a1"}])
        self.assertEqual(out, {})
        self.assertEqual(net.calls, [])

    def test_album_only_mode_skips_artist_batch(self):
        net = _PostNet(album={"g1": 900}, artist={"a1": 5})
        out, _ = _resolve(net, [_cand("g1", "a1")], with_artist_listeners=False)
        self.assertEqual(out["g1"]["album_listeners"], 900)
        self.assertIsNone(out["g1"]["artist_listeners"])
        self.assertEqual(net.calls_to(LISTENBRAINZ_ARTIST_POPULARITY_URL), [])


if __name__ == "__main__":
    unittest.main()
