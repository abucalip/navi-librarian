"""Focused unit tests for discovery.popularity (FirstFM F1.4)."""
from __future__ import annotations

import unittest

from discovery.popularity import (
    apply_popularity_bonus,
    build_discovery_lookups,
    candidate_popularity_fields,
    run_personal_popularity_pass,
)
from discovery.recommendation_payload import build_personal_recommendation_payload


class DiscoveryPopularityTests(unittest.TestCase):
    def test_apply_popularity_bonus_emits_neutral_and_legacy_fields(self):
        candidate = {
            "artist": "Artist A",
            "primary_artist": "Artist A",
            "album": "Album One",
            "discovery_score": 10.0,
            "recent_profile_bonus": 1.0,
        }
        checked = apply_popularity_bonus(
            [candidate],
            {"jazz": 4},
            lambda artist, album: {"listeners": 1000, "playcount": 5000, "tags": ["jazz"]},
        )
        self.assertEqual(checked, 1)
        self.assertEqual(candidate["listeners"], 1000)
        self.assertEqual(candidate["playcount"], 5000)
        self.assertEqual(candidate["popularity_tags"], ["jazz"])
        self.assertGreater(candidate["popularity_bonus"], 1.0)
        self.assertNotIn("lastfm_listeners", candidate)
        self.assertNotIn("lastfm_playcount", candidate)
        self.assertNotIn("lastfm_tags", candidate)
        self.assertNotIn("lastfm_popularity_bonus", candidate)

    def test_candidate_popularity_fields_reads_neutral_fields(self):
        neutral = candidate_popularity_fields({
            "listeners": 42,
            "playcount": 99,
            "popularity_bonus": 1.0556,
        })
        self.assertEqual(neutral, {
            "listeners": 42,
            "playcount": 99,
            "popularity_bonus": 1.056,
        })

    def test_recommendation_payload_emits_neutral_fields_only(self):
        payload = build_personal_recommendation_payload(
            {
                "artist": "Artist A",
                "album": "Album One",
                "discovery_category": "adjacent",
                "genres": ["jazz"],
                "genre_families": ["jazz"],
                "genre_metadata_available": True,
                "score": 0.9,
                "discovery_score": 1.234567,
                "listeners": 500,
                "playcount": 2000,
                "popularity_tags": ["jazz"],
                "popularity_bonus": 1.0456,
                "tracks": ["Track 1"],
            },
            recent_artist_listens=2,
        )
        self.assertEqual(payload["listeners"], 500)
        self.assertEqual(payload["playcount"], 2000)
        self.assertEqual(payload["popularity_tags"], ["jazz"])
        self.assertEqual(payload["popularity_bonus"], 1.046)
        self.assertNotIn("lastfm_listeners", payload)
        self.assertNotIn("lastfm_playcount", payload)
        self.assertNotIn("lastfm_tags", payload)
        self.assertNotIn("lastfm_popularity_bonus", payload)

    def test_run_personal_popularity_pass_uses_supplied_callback(self):
        albums = {
            ("a", "b"): {
                "artist": "Artist A",
                "primary_artist": "Artist A",
                "album": "Album B",
                "discovery_score": 5.0,
            }
        }
        checked, calls = run_personal_popularity_pass(
            albums,
            {},
            metadata_cache_get=lambda _k, _t: None,
            metadata_cache_set=lambda _k, _v: None,
            music_key=lambda s: str(s).lower(),
            popularity_fn=lambda _a, _b: {"listeners": 100, "playcount": 300, "tags": []},
        )
        self.assertEqual(checked, 1)
        self.assertEqual(calls, [])
        self.assertEqual(albums[("a", "b")]["listeners"], 100)

    def test_build_discovery_lookups_filters_top_albums_and_uses_lb_deezer_discogs(self):
        class FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload

            def json(self):
                return self._payload

        class OpenLane:
            def acquire(self):
                return True

        def fake_get(url, **kwargs):
            if "musicbrainz.org/ws/2/artist/" in url:
                query = (kwargs.get("params") or {}).get("query", "")
                if "NoMbid" in query:
                    return FakeResponse(200, {"artists": []})
                return FakeResponse(200, {"artists": [{"id": "mbid-1", "name": "Artist"}]})
            if "top-release-groups-for-artist/mbid-1" in url:
                return FakeResponse(200, [
                    {"release_group_mbid": "rg-1", "release_group_name": "Valid",
                     "total_user_count": 10, "total_listen_count": 20},
                    {"release_group_mbid": "rg-2", "release_group_name": "Various Artists",
                     "total_user_count": 30, "total_listen_count": 40},
                ])
            if "lb-radio/artist/mbid-1" in url:
                return FakeResponse(200, {
                    "mbid-1": [{"similar_artist_mbid": "mbid-2", "similar_artist_name": "Peer"}]
                })
            if "api.deezer.com/search/artist" in url:
                return FakeResponse(200, {"data": [{"id": 99, "name": "NoMbid"}]})
            if "api.deezer.com/artist/99/related" in url:
                return FakeResponse(200, {"data": [{"id": 100, "name": "Deezer Peer"}]})
            if "musicbrainz.org/ws/2/genre/all" in url:
                return FakeResponse(200, {"genres": [{"name": "ambient"}]})
            if "api.discogs.com/database/search" in url:
                return FakeResponse(200, {"results": [{"title": "Artist - Album", "style": ["Ambient"]}]})
            raise AssertionError(f"Unexpected URL: {url}")

        cache = {}
        lookups = build_discovery_lookups(
            cache_get=lambda k, _t: cache.get(k),
            cache_set=cache.__setitem__,
            is_album_candidate=lambda item: item["album"] == "Valid",
            settings_reader=lambda: {"discogs_token": "tok"},
            http_get=fake_get,
            lane=OpenLane(),
        )
        self.assertEqual(
            lookups.top_albums("Artist", limit=2),
            [{"artist": "Artist", "album": "Valid", "mbid": "rg-1", "listeners": 10, "playcount": 20}],
        )
        self.assertEqual(
            lookups.similar_artists("Artist", limit=5),
            [{"artist": "Peer", "similarity": 1.0}],
        )
        self.assertEqual(
            lookups.similar_artists("NoMbid", limit=5),
            [{"artist": "Deezer Peer", "similarity": 1.0}],
        )
        self.assertEqual(lookups.artist_genres("Artist"), ["ambient"])

    def test_navidrome_server_has_no_lastfm_client_or_adapters(self):
        import navidrome_server

        for symbol in (
            "_lastfm_client",
            "_lastfm_album_popularity",
            "_lastfm_top_albums",
            "_lastfm_artist_genres",
            "LASTFM_LAST_ERROR",
        ):
            self.assertFalse(hasattr(navidrome_server, symbol), f"Unexpected symbol: {symbol}")


if __name__ == "__main__":
    unittest.main()
