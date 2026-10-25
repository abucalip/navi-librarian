import unittest

from discovery.artist_profiles import ARTIST_PROFILE_CACHE_PREFIX, MUSICBRAINZ_ARTIST_SEARCH_URL, fetch_artist_profiles


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


class _Get:
    def __init__(self, artists=(), status=200, raises=False):
        self.artists, self.status, self.raises = list(artists), status, raises
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if self.raises:
            raise OSError("dropped")
        return _Response({"artists": self.artists}, self.status)


class _Cache:
    def __init__(self):
        self.store = {}

    def get(self, key, ttl_seconds=None, **_kwargs):
        return self.store.get(key)

    def set(self, key, value, **_kwargs):
        self.store[key] = value


def artist(mbid, area=None, begin=None):
    entry = {"id": mbid}
    if area:
        entry["area"] = {"name": area}
    if begin:
        entry["life-span"] = {"begin": begin}
    return entry


class ArtistProfileTests(unittest.TestCase):
    def test_area_and_first_year_come_from_one_batched_search(self):
        get, cache = _Get([artist("a", "Ethiopia", "1969-05-01"), artist("b")]), _Cache()
        found = fetch_artist_profiles(get, ["a", "b"], headers={}, cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(found["a"], {"area": "Ethiopia", "begin_year": 1969})
        self.assertEqual(found["b"], {"area": None, "begin_year": None})
        self.assertEqual(len(get.calls), 1)
        self.assertEqual(get.calls[0][0], MUSICBRAINZ_ARTIST_SEARCH_URL)
        self.assertEqual(get.calls[0][1]["query"], "arid:(a OR b)")

    def test_cached_artists_cost_no_call(self):
        get, cache = _Get([artist("a", "Mali")]), _Cache()
        fetch_artist_profiles(get, ["a"], headers={}, cache_get=cache.get, cache_set=cache.set)
        again = fetch_artist_profiles(_Get(), ["a"], headers={}, cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(again["a"], {"area": "Mali", "begin_year": None})
        self.assertIn(f"{ARTIST_PROFILE_CACHE_PREFIX}a", cache.store)

    def test_failed_search_leaves_artists_uncached_and_never_raises(self):
        cache = _Cache()
        found = fetch_artist_profiles(_Get(status=503), ["a"], headers={}, cache_get=cache.get, cache_set=cache.set)
        self.assertEqual(found, {})
        self.assertEqual(cache.store, {})
        self.assertEqual(fetch_artist_profiles(_Get(raises=True), ["a"], headers={},
                                               cache_get=cache.get, cache_set=cache.set), {})


if __name__ == "__main__":
    unittest.main()
