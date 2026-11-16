import unittest

from integrations.listenbrainz.popularity import (
    NEGATIVE_TTL_SECONDS,
    POPULARITY_CACHE_PREFIX,
    POPULARITY_CHUNK,
    build_popularity_lookup,
    fetch_release_group_popularity,
)

A, B, C = (f"{n}" * 8 + "-1111-2222-3333-" + f"{n}" * 12 for n in "abc")


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.cache, self.posts, self.now = {}, [], 1_000_000.0

    def _get(self, key, ttl_seconds):
        return self.cache.get(key)

    def _fetch(self, body, mbids, status=200):
        def post(url, json, headers, timeout):
            self.posts.append(json["release_group_mbids"])
            return FakeResponse(status, body)
        return fetch_release_group_popularity(
            post, self._get, self.cache.__setitem__, mbids, headers={},
            clock=lambda: self.now)

    def _key(self, mbid):
        return f"{POPULARITY_CACHE_PREFIX}{mbid}"

    def test_maps_counts_skips_nulls_and_caches(self):
        body = [
            {"release_group_mbid": A, "total_listen_count": 900, "total_user_count": 40},
            {"release_group_mbid": B, "total_listen_count": None, "total_user_count": None},
        ]
        found = self._fetch(body, [A, B])
        self.assertEqual(found, {A: {"listeners": 40, "playcount": 900, "tags": []}})
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.cache[self._key(A)], {"listeners": 40, "playcount": 900, "tags": []})
        self.assertEqual(self.cache[self._key(B)], {"negative": True, "at": self.now})
        self._fetch(body, [A])
        self.assertEqual(len(self.posts), 1, "cached group must not be requested again")
        self._fetch(body, [A, B])
        self.assertEqual(len(self.posts), 1, "fresh negative group must not be requested again")

    def test_chunks_and_failure_is_best_effort(self):
        many = [f"{i:08x}-1111-2222-3333-444444444444" for i in range(POPULARITY_CHUNK + 1)]
        self.assertEqual(self._fetch([], many), {})
        self.assertEqual([len(p) for p in self.posts], [POPULARITY_CHUNK, 1])
        self.assertEqual(len(self.cache), POPULARITY_CHUNK + 1, "a 200 with no counts is negative")
        before = dict(self.cache)
        self.assertEqual(self._fetch(None, [A], status=502), {})
        self.assertEqual(self._fetch({"x": 1}, [C]), {})
        self.assertEqual(self.cache, before, "non-200 and non-list answers write nothing")

    def test_server_error_writes_no_negative_entry(self):
        self.assertEqual(self._fetch(None, [A], status=500), {})
        self.assertEqual(self.cache, {})

    def test_malformed_counts_write_nothing(self):
        body = [
            {"release_group_mbid": A, "total_listen_count": "many", "total_user_count": 1},
        ]
        self.assertEqual(self._fetch(body, [A, B]), {})
        self.assertEqual(self.cache, {}, "a malformed 200 body is a failure, not no-data")

    def test_negative_group_is_not_resent_within_ttl(self):
        body = [{"release_group_mbid": A, "total_listen_count": None, "total_user_count": None}]
        self._fetch(body, [A])
        self.now += NEGATIVE_TTL_SECONDS - 1
        self.assertEqual(self._fetch(body, [A]), {})
        self.assertEqual(len(self.posts), 1)

    def test_negative_group_becomes_positive_after_expiry(self):
        self._fetch([], [A])
        self.now += NEGATIVE_TTL_SECONDS
        body = [{"release_group_mbid": A, "total_listen_count": 5, "total_user_count": 2}]
        found = self._fetch(body, [A])
        self.assertEqual(len(self.posts), 2, "an expired negative entry is requested again")
        self.assertEqual(found, {A: {"listeners": 2, "playcount": 5, "tags": []}})
        self.assertEqual(self.cache[self._key(A)], {"listeners": 2, "playcount": 5, "tags": []})

    def test_lookup_uses_top_candidates_only_and_identity(self):
        candidates = [
            {"artist": "X", "album": "One", "discovery_score": 2.0, "release_group_mbid": A},
            {"artist": "Y", "album": "Two", "discovery_score": 1.0, "release_group_mbid": B},
            {"artist": "Z", "album": "Three", "discovery_score": 3.0, "release_group_mbid": None},
        ]
        asked = []
        stats = {A: {"listeners": 1, "playcount": 2, "tags": []}}
        lookup = build_popularity_lookup(
            candidates, 2, lambda m: asked.append(m) or stats, lambda v: str(v).lower())
        self.assertEqual(asked, [[A]], "limit 2 keeps Z (no mbid) and X; Y is cut")
        self.assertEqual(lookup("x", "ONE"), stats[A])
        self.assertIsNone(lookup("Y", "Two"))


if __name__ == "__main__":
    unittest.main()
