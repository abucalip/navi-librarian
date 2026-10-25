import unittest

from discovery.artist_links import (
    COLLABORATOR_CACHE_PREFIX, LINK_MAX_CALLS, SIMILAR_CACHE_PREFIX, fetch_collaborators, fetch_similar_artists,
)
from discovery.artist_tag_fallback import LASTFM_API_URL


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


class _Get:
    def __init__(self, payload=None, status=200, raises=False):
        self.payload, self.status, self.raises = payload, status, raises
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if self.raises:
            raise OSError("dropped")
        return _Response(self.payload(params) if callable(self.payload) else self.payload, self.status)


class _Cache:
    def __init__(self):
        self.store = {}

    def get(self, key, ttl_seconds=None, **_kwargs):
        return self.store.get(key)

    def set(self, key, value, **_kwargs):
        self.store[key] = value


def similar_body(*mbids):
    return {"similarartists": {"artist": [{"name": m, "mbid": m} for m in mbids] + [{"name": "no-mbid"}]}}


def relations(*items):
    return {"relations": [{"type": t, "target-type": tt, "artist": {"id": i}} for t, tt, i in items]}


class SimilarArtistTests(unittest.TestCase):
    def test_similar_mbids_come_from_last_fm_and_skip_entries_without_one(self):
        get, cache = _Get(similar_body("s1", "s2")), _Cache()
        found = fetch_similar_artists(get, ["a"], api_key="k", cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(found, {"a": ["s1", "s2"]})
        url, params = get.calls[0]
        self.assertEqual(url, LASTFM_API_URL)
        self.assertEqual((params["method"], params["mbid"], params["api_key"]), ("artist.getSimilar", "a", "k"))

    def test_no_api_key_asks_nothing(self):
        get = _Get(similar_body("s1"))
        self.assertEqual(fetch_similar_artists(get, ["a"], api_key="", cache_get=_Cache().get,
                                               cache_set=_Cache().set), {})
        self.assertEqual(get.calls, [])

    def test_cached_answer_costs_no_call_and_failure_is_not_cached(self):
        cache = _Cache()
        fetch_similar_artists(_Get(similar_body("s1")), ["a"], api_key="k", cache_get=cache.get, cache_set=cache.set)
        again = _Get(similar_body("x"))
        self.assertEqual(fetch_similar_artists(again, ["a"], api_key="k", cache_get=cache.get,
                                               cache_set=cache.set), {"a": ["s1"]})
        self.assertEqual(again.calls, [])
        failing, fresh = _Get(raises=True), _Cache()
        self.assertEqual(fetch_similar_artists(failing, ["b"], api_key="k", cache_get=fresh.get,
                                               cache_set=fresh.set), {})
        self.assertEqual(fresh.store, {})

    def test_provider_calls_are_capped_per_run(self):
        get, cache = _Get(similar_body()), _Cache()
        mbids = [f"m{i}" for i in range(LINK_MAX_CALLS + 5)]
        fetch_similar_artists(get, mbids, api_key="k", cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(len(get.calls), LINK_MAX_CALLS)
        self.assertTrue(all(key.startswith(SIMILAR_CACHE_PREFIX) for key in cache.store))


class CollaboratorTests(unittest.TestCase):
    def test_only_artist_relations_of_music_making_types_are_kept(self):
        def body(params):
            return relations(("member of band", "artist", "c1"), ("collaboration", "artist", "c2"),
                             ("streaming", "url", "u1"), ("label", "label", "l1"),
                             ("performer", "artist", "c1"))
        get, cache = _Get(body), _Cache()
        found = fetch_collaborators(get, ["a"], headers={"User-Agent": "t"}, cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(found, {"a": ["c1", "c2"]})
        url, params = get.calls[0]
        self.assertTrue(url.endswith("/a"))
        self.assertEqual(params["inc"], "artist-rels")
        self.assertIn(f"{COLLABORATOR_CACHE_PREFIX}a", cache.store)

    def test_a_non_200_answer_is_not_cached(self):
        cache = _Cache()
        self.assertEqual(fetch_collaborators(_Get({}, status=503), ["a"], headers={}, cache_get=cache.get,
                                             cache_set=cache.set), {})
        self.assertEqual(cache.store, {})


if __name__ == "__main__":
    unittest.main()
