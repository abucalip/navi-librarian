import unittest
from unittest.mock import patch

import httpx

import musicbrainz_rating_client as legacy_client
from integrations.musicbrainz.rating_client import critical_rating


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 404:
            raise httpx.HTTPStatusError("bad response", request=None, response=None)

    def json(self):
        return self.payload


class MusicBrainzRatingClientTests(unittest.TestCase):
    def test_legacy_shim_reexports_canonical_implementation(self):
        self.assertIs(legacy_client.critical_rating, critical_rating)

    def setUp(self):
        self.cache = {}
        self.requests = []
        self.sleeps = []

        def cache_get(key, ttl_seconds):
            self.requests.append(("cache_get", key, ttl_seconds))
            return self.cache.get(key)

        def cache_set(key, value):
            self.requests.append(("cache_set", key, value))
            self.cache[key] = value

        self.cache_get = cache_get
        self.cache_set = cache_set

    def test_fetches_rating_year_and_caches_with_expected_request(self):
        def http_get(url, **kwargs):
            self.requests.append(("http_get", url, kwargs))
            return FakeResponse({
                "rating": {"value": 4.25, "votes-count": 12},
                "first-release-date": "1998-04-02",
            })
        result = critical_rating(
            "mbid-1", include_year=True, cache_get=self.cache_get,
            cache_set=self.cache_set, http_get=http_get, sleep=self.sleeps.append,
        )
        self.assertEqual(result, {"rating": 4.25, "votes": 12, "year": 1998})
        request = next(row for row in self.requests if row[0] == "http_get")
        self.assertEqual(request[1], "https://musicbrainz.org/ws/2/release-group/mbid-1")
        self.assertEqual(request[2]["params"], {"fmt": "json", "inc": "ratings"})
        self.assertEqual(request[2]["headers"], {
            "User-Agent": "Discair/1.0 (personal music discovery)"
        })
        self.assertEqual(request[2]["timeout"], 15)
        self.assertEqual(self.sleeps, [1.1])
        self.assertEqual(self.cache["discovery:mb-release-group-rating:mbid-1"], result)

    def test_cached_rating_without_year_refetches_only_when_year_requested(self):
        key = "discovery:mb-release-group-rating:mbid-2"
        self.cache[key] = {"rating": 3.5, "votes": 4}
        http_calls = []
        http_get = lambda *args, **kwargs: (http_calls.append((args, kwargs)) or FakeResponse({
            "rating": {"value": 3.5, "votes-count": 4}, "first-release-date": "2001"
        }))
        cached = critical_rating("mbid-2", cache_get=self.cache_get, cache_set=self.cache_set,
                                 http_get=http_get, sleep=self.sleeps.append)
        self.assertEqual(cached, {"rating": 3.5, "votes": 4})
        self.assertEqual(http_calls, [])
        refreshed = critical_rating("mbid-2", include_year=True, cache_get=self.cache_get,
                                    cache_set=self.cache_set, http_get=http_get,
                                    sleep=self.sleeps.append)
        self.assertEqual(refreshed["year"], 2001)
        self.assertEqual(len(http_calls), 1)

    def test_404_is_cached_as_empty_result(self):
        result = critical_rating("missing", cache_get=self.cache_get, cache_set=self.cache_set,
                                 http_get=lambda *_a, **_k: FakeResponse(status_code=404),
                                 sleep=self.sleeps.append)
        self.assertEqual(result, {"rating": None, "votes": 0, "year": None})
        self.assertEqual(self.cache["discovery:mb-release-group-rating:missing"], result)

    def test_empty_id_and_http_errors_are_safe(self):
        http_calls = []
        self.assertIsNone(critical_rating("", cache_get=self.cache_get, cache_set=self.cache_set,
                                          http_get=lambda *a, **k: http_calls.append((a, k))))
        self.assertEqual(http_calls, [])
        self.assertIsNone(critical_rating("offline", cache_get=self.cache_get, cache_set=self.cache_set,
                                          http_get=lambda *_a, **_k: (_ for _ in ()).throw(httpx.ConnectError("offline")),
                                          sleep=self.sleeps.append))

    def test_legacy_server_adapter_delegates(self):
        import navidrome_server
        expected = {"rating": 4, "votes": 1, "year": 2000}
        with patch.object(navidrome_server._musicbrainz_rating_client, "critical_rating",
                          return_value=expected) as call:
            self.assertIs(navidrome_server._musicbrainz_critical_rating("mbid", include_year=True), expected)
        call.assert_called_once_with(
            "mbid", include_year=True,
            cache_get=navidrome_server._metadata_cache_get,
            cache_set=navidrome_server._metadata_cache_set,
        )


if __name__ == "__main__":
    unittest.main()
