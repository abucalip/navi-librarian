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



    def test_album_popularity_fetches_normalizes_tags_and_caches_legacy_key(self):
        payload = {
            "album": {
                "name": "Post",
                "stats": {"listeners": "123", "playcount": "456"},
                "tags": {"tag": {"name": "Trip Hop"}},
            }
        }
        def http_get(url, **kwargs):
            self.calls.append(("http_get", url, kwargs))
            return FakeResponse(payload)

        client = self.make_client(http_get=http_get)
        result, error = client.album_popularity("Björk", "Post")
        self.assertIsNone(error)
        self.assertEqual(result, {"listeners": 123, "playcount": 456, "tags": ["trip hop"]})
        cache_key = "lastfm:album-info-v2:bjork:post"
        self.assertIn(cache_key, self.cache)
        self.assertEqual(self.cache[cache_key], result)
        request = next(row for row in self.calls if row[0] == "http_get")
        self.assertEqual(request[2]["params"], {
            "method": "album.getInfo", "api_key": "key", "artist": "Björk",
            "album": "Post", "autocorrect": 1, "format": "json",
        })
        self.assertEqual(request[2]["timeout"], 12)

    def test_album_popularity_accepts_direct_stats_and_cache_hits(self):
        cached = {"listeners": 9, "playcount": 10, "tags": []}
        client = self.make_client(cache_get=lambda _key, _ttl: cached)
        self.assertEqual(client.album_popularity("Artist", "Album"), (cached, None))
        self.assertFalse(any(row[0] == "http_get" for row in self.calls))

        payload = {"album": {"listeners": "7", "playcount": 8, "tags": {"tag": []}}}
        client = self.make_client(http_get=lambda *_a, **_k: FakeResponse(payload))
        self.assertEqual(client.album_popularity("Artist", "Album"), (
            {"listeners": 7, "playcount": 8, "tags": []}, None
        ))

    def test_album_popularity_reports_provider_and_missing_stats_errors(self):
        client = self.make_client(http_get=lambda *_a, **_k: FakeResponse({
            "error": 6, "message": "Album not found"
        }))
        self.assertEqual(client.album_popularity("Artist", "Album"), (
            None, "Last.fm API error 6: Album not found"
        ))
        client = self.make_client(http_get=lambda *_a, **_k: FakeResponse({"album": {"name": "Empty"}}))
        self.assertEqual(client.album_popularity("Artist", "Album"), (
            None, "Last.fm returned no album statistics for a lookup."
        ))

    def test_album_popularity_404_is_silent_but_other_http_errors_are_reported(self):
        not_found = httpx.HTTPStatusError(
            "not found", request=httpx.Request("GET", "https://example.test"),
            response=httpx.Response(404),
        )
        client = self.make_client(http_get=lambda *_a, **_k: (_ for _ in ()).throw(not_found))
        self.assertEqual(client.album_popularity("Artist", "Album"), (None, None))
        server_error = httpx.HTTPStatusError(
            "server error", request=httpx.Request("GET", "https://example.test"),
            response=httpx.Response(503),
        )
        client = self.make_client(http_get=lambda *_a, **_k: (_ for _ in ()).throw(server_error))
        self.assertEqual(client.album_popularity("Artist", "Album"), (
            None, "Last.fm returned HTTP 503."
        ))

    def test_album_popularity_legacy_adapter_preserves_error_state(self):
        import navidrome_server
        with patch.object(navidrome_server, "LASTFM_LAST_ERROR", "previous"), patch.object(
            navidrome_server._lastfm_client, "album_popularity",
            return_value=(None, "Last.fm returned HTTP 503."),
        ) as lookup:
            self.assertIsNone(navidrome_server._lastfm_album_popularity("Artist", "Album"))
            self.assertEqual(navidrome_server.LASTFM_LAST_ERROR, "Last.fm returned HTTP 503.")
        lookup.assert_called_once_with("Artist", "Album")


    def test_artist_genres_normalizes_deduplicates_and_limits_tags(self):
        payload = {"toptags": {"tag": [
            {"name": " Jazz "}, {"name": "jazz"}, {"name": "Bossa Nova"},
            {"name": "Soul"}, {"name": "Funk"}, {"name": "Rock"},
            {"name": "Pop"}, {"name": "Afrobeat"}, {"name": "Blues"},
            {"name": "Country"}, {"name": "Ignored"},
        ]}}
        def http_get(url, **kwargs):
            self.calls.append(("http_get", url, kwargs))
            return FakeResponse(payload)

        client = self.make_client(http_get=http_get)
        self.assertEqual(client.artist_genres("Artist"), [
            "Jazz", "Bossa Nova", "Soul", "Funk", "Rock", "Pop", "Afrobeat", "Blues",
        ])
        request = next(row for row in self.calls if row[0] == "http_get")
        self.assertEqual(request[2]["params"]["method"], "artist.getTopTags")
        self.assertEqual(request[2]["params"]["artist"], "Artist")
        self.assertEqual(request[2]["timeout"], 15)

    def test_artist_genres_handles_scalar_tags_cache_hits_and_missing_payload(self):
        client = self.make_client(http_get=lambda *_a, **_k: FakeResponse({
            "toptags": {"tag": {"name": " Rai "}}
        }))
        self.assertEqual(client.artist_genres("Artist"), ["Rai"])
        cached = self.make_client(cache_get=lambda _key, _ttl: {
            "toptags": {"tag": [{"name": "Jazz"}]}
        })
        self.assertEqual(cached.artist_genres("Artist"), ["Jazz"])
        self.assertFalse(any(row[0] == "http_get" for row in self.calls))
        missing = self.make_client(http_get=lambda *_a, **_k: FakeResponse({"error": 6}))
        self.assertEqual(missing.artist_genres("Artist"), [])

    def test_artist_genres_legacy_adapter_delegates(self):
        import navidrome_server
        with patch.object(navidrome_server._lastfm_client, "artist_genres",
                          return_value=["Jazz"]) as call:
            self.assertEqual(navidrome_server._lastfm_artist_genres("Artist"), ["Jazz"])
        call.assert_called_once_with("Artist")


    def test_artist_top_albums_normalizes_records_and_preserves_request_contract(self):
        payload = {"topalbums": {"album": [
            {"name": " Album One ", "mbid": "abc", "listeners": "12",
             "playcount": "345", "url": "https://last.fm/one"},
            {"name": "", "listeners": 1},
            {"name": "Album Two", "listeners": None, "playcount": None},
        ]}}
        def http_get(url, **kwargs):
            self.calls.append(("http_get", url, kwargs))
            return FakeResponse(payload)

        client = self.make_client(http_get=http_get)
        self.assertEqual(client.artist_top_albums("Artist", limit=5), [
            {"artist": "Artist", "album": "Album One", "mbid": "abc",
             "lastfm_listeners": 12, "lastfm_playcount": 345,
             "lastfm_url": "https://last.fm/one"},
            {"artist": "Artist", "album": "Album Two", "mbid": None,
             "lastfm_listeners": 0, "lastfm_playcount": 0, "lastfm_url": None},
        ])
        request = next(row for row in self.calls if row[0] == "http_get")
        self.assertEqual(request[2]["params"]["method"], "artist.getTopAlbums")
        self.assertEqual(request[2]["params"]["artist"], "Artist")
        self.assertEqual(request[2]["params"]["limit"], 5)
        self.assertEqual(request[2]["timeout"], 15)
        self.assertEqual(next(row for row in self.calls if row[0] == "cache_get")[2], 30 * 24 * 60 * 60)

    def test_artist_top_albums_supports_scalar_payload_cache_and_missing_payload(self):
        client = self.make_client(http_get=lambda *_a, **_k: FakeResponse({
            "topalbums": {"album": {"name": "Solo", "listeners": "7"}}
        }))
        self.assertEqual(client.artist_top_albums("Artist")[0]["album"], "Solo")
        cached = self.make_client(cache_get=lambda _key, _ttl: {
            "topalbums": {"album": [{"name": "Cached"}]}
        })
        self.assertEqual(cached.artist_top_albums("Artist")[0]["album"], "Cached")
        self.assertFalse(any(row[0] == "http_get" for row in self.calls))
        missing = self.make_client(http_get=lambda *_a, **_k: FakeResponse({"error": 6}))
        self.assertEqual(missing.artist_top_albums("Artist"), [])

    def test_artist_top_albums_legacy_adapter_keeps_discovery_filter(self):
        import navidrome_server
        records = [
            {"artist": "Artist", "album": "Valid", "mbid": None,
             "lastfm_listeners": 1, "lastfm_playcount": 2, "lastfm_url": None},
            {"artist": "Artist", "album": "Various Artists", "mbid": None,
             "lastfm_listeners": 3, "lastfm_playcount": 4, "lastfm_url": None},
        ]
        with patch.object(navidrome_server._lastfm_client, "artist_top_albums",
                          return_value=records) as call, patch.object(
                              navidrome_server, "_discovery_is_album_candidate",
                              side_effect=lambda item: item["album"] == "Valid"):
            self.assertEqual(navidrome_server._lastfm_top_albums("Artist", limit=2), [records[0]])
        call.assert_called_once_with("Artist", limit=2)

if __name__ == "__main__":
    unittest.main()
