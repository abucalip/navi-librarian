"""Focused unit tests for discovery.popularity (FirstFM F1.4)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

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
        self.assertEqual(candidate["lastfm_listeners"], 1000)
        self.assertEqual(candidate["lastfm_playcount"], 5000)
        self.assertEqual(candidate["lastfm_tags"], ["jazz"])
        self.assertGreater(candidate["popularity_bonus"], 1.0)
        self.assertEqual(candidate["popularity_bonus"], candidate["lastfm_popularity_bonus"])

    def test_candidate_popularity_fields_reads_neutral_or_legacy(self):
        neutral = candidate_popularity_fields({
            "listeners": 42,
            "playcount": 99,
            "popularity_bonus": 1.0556,
        })
        self.assertEqual(neutral["listeners"], 42)
        self.assertEqual(neutral["lastfm_listeners"], 42)
        self.assertEqual(neutral["playcount"], 99)
        self.assertEqual(neutral["lastfm_playcount"], 99)
        self.assertEqual(neutral["popularity_bonus"], 1.056)
        self.assertEqual(neutral["lastfm_popularity_bonus"], 1.056)

        legacy = candidate_popularity_fields({
            "lastfm_listeners": 7,
            "lastfm_playcount": 14,
            "lastfm_popularity_bonus": 1.02,
        })
        self.assertEqual(legacy["listeners"], 7)
        self.assertEqual(legacy["playcount"], 14)
        self.assertEqual(legacy["popularity_bonus"], 1.02)

    def test_recommendation_payload_emits_neutral_and_legacy_aliases(self):
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
        self.assertEqual(payload["lastfm_listeners"], 500)
        self.assertEqual(payload["playcount"], 2000)
        self.assertEqual(payload["lastfm_playcount"], 2000)
        self.assertEqual(payload["popularity_tags"], ["jazz"])
        self.assertEqual(payload["lastfm_tags"], ["jazz"])
        self.assertEqual(payload["popularity_bonus"], 1.046)
        self.assertEqual(payload["lastfm_popularity_bonus"], 1.046)

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

    def test_build_discovery_lookups_filters_top_albums(self):
        records = [
            {"artist": "Artist", "album": "Valid", "mbid": None,
             "lastfm_listeners": 1, "lastfm_playcount": 2, "lastfm_url": None},
            {"artist": "Artist", "album": "Various Artists", "mbid": None,
             "lastfm_listeners": 3, "lastfm_playcount": 4, "lastfm_url": None},
        ]
        with patch("integrations.lastfm.client.LastFmClient.artist_top_albums", return_value=records):
            lookups = build_discovery_lookups(
                settings_reader=dict,
                cache_get=lambda _k, _t: None,
                cache_set=lambda _k, _v: None,
                is_album_candidate=lambda item: item["album"] == "Valid",
            )
            self.assertEqual(lookups.top_albums("Artist", limit=2), [records[0]])

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
