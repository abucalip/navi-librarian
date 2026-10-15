import hashlib
import json
import unittest
from unittest.mock import patch

import httpx

from lastfm_client import LastFmClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class LastFmClientTests(unittest.TestCase):
    def make_client(self, **overrides):
        self.cache = {}
        self.calls = []
        self.sleeps = []
        settings = overrides.pop("settings_reader", lambda: {"lastfm_api_key": " key "})

        def cache_get(key, ttl):
            self.calls.append(("cache_get", key, ttl))
            return self.cache.get(key)

        def cache_set(key, value):
            self.calls.append(("cache_set", key, value))
            self.cache[key] = value

        def http_get(url, **kwargs):
            self.calls.append(("http_get", url, kwargs))
            return FakeResponse({"artist": {"name": "Test"}})

        return LastFmClient(
            settings_reader=settings,
            cache_get=overrides.pop("cache_get", cache_get),
            cache_set=overrides.pop("cache_set", cache_set),
            http_get=overrides.pop("http_get", http_get),
            monotonic=overrides.pop("monotonic", lambda: 10.0),
            sleep=overrides.pop("sleep", self.sleeps.append),
            **overrides,
        )

    def test_fetches_and_caches_with_legacy_request_contract(self):
        client = self.make_client()
        result = client.cached_call("artist.getTopTags", artist="Björk")
        self.assertEqual(result, {"artist": {"name": "Test"}})
        request = next(row for row in self.calls if row[0] == "http_get")
        self.assertEqual(request[1], "https://ws.audioscrobbler.com/2.0/")
        self.assertEqual(request[2]["params"], {
            "method": "artist.getTopTags", "api_key": "key", "format": "json",
            "autocorrect": 1, "artist": "Björk",
        })
        self.assertEqual(request[2]["headers"], {"User-Agent": "NavidromeLibrarian/1.0"})
        self.assertEqual(request[2]["timeout"], 15)
        expected_key = "discovery:lastfm:" + hashlib.sha256(
            json.dumps({"method": "artist.getTopTags", "params": {"artist": "Björk"}},
                       sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertIn(expected_key, self.cache)
        self.assertEqual(self.calls[-1], ("cache_set", expected_key, result))

    def test_returns_cached_payload_without_http_request(self):
        payload = {"cached": True}
        client = self.make_client(cache_get=lambda _key, _ttl: payload)
        self.assertEqual(client.cached_call("artist.getSimilar", artist="A"), payload)
        self.assertFalse(any(row[0] == "http_get" for row in self.calls))

    def test_missing_key_and_provider_error_return_none(self):
        no_key = self.make_client(settings_reader=lambda: {"lastfm_api_key": " "})
        self.assertIsNone(no_key.cached_call("artist.getTopAlbums", artist="A"))
        provider_error = self.make_client(http_get=lambda *_a, **_k: FakeResponse({"error": 6}))
        self.assertIsNone(provider_error.cached_call("artist.getTopAlbums", artist="A"))

    def test_http_and_json_errors_are_non_fatal(self):
        def fail_http(*_args, **_kwargs):
            raise httpx.ConnectError("offline")
        client = self.make_client(http_get=fail_http)
        self.assertIsNone(client.cached_call("artist.getTopAlbums", artist="A"))
        bad_json = self.make_client(http_get=lambda *_a, **_k: FakeResponse(ValueError("bad json")))
        self.assertIsNone(bad_json.cached_call("artist.getTopAlbums", artist="A"))

    def test_legacy_server_adapter_delegates(self):
        import navidrome_server
        expected = {"ok": True}
        with patch.object(navidrome_server._lastfm_client, "cached_call", return_value=expected) as call:
            self.assertIs(navidrome_server._lastfm_cached_call("artist.getSimilar", ttl_seconds=60, artist="A"), expected)
        call.assert_called_once_with("artist.getSimilar", ttl_seconds=60, artist="A")


if __name__ == "__main__":
    unittest.main()
