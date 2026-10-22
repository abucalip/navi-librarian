"""Direct-import regression tests for extracted slskd search and quality helpers."""

import unittest

from integrations.slskd.quality import quality_tier
from integrations.slskd.search import (
    album_path_match,
    extract_candidates,
    path_match_diagnostics,
    response_items,
    search_queries,
    track_identity,
)

QUALITY_PRIORITY = [
    "mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"
]


def music_key(value):
    import re
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


class SlskdQualityModuleTests(unittest.TestCase):
    def test_mp3_bitrate_tiers_and_unknown_fallback(self):
        self.assertEqual(quality_tier({"bitRate": 320}, "track.mp3", QUALITY_PRIORITY), (0, "mp3_320"))
        self.assertEqual(quality_tier({"bitrate": 256}, "track.mp3", QUALITY_PRIORITY), (1, "mp3_193_319"))
        self.assertEqual(quality_tier({}, "track 192kbps.mp3", QUALITY_PRIORITY), (2, "mp3_192"))
        self.assertEqual(quality_tier({}, "track.mp3", QUALITY_PRIORITY), (len(QUALITY_PRIORITY) + 1, "other"))

    def test_flac_metadata_and_filename_resolution_labels(self):
        self.assertEqual(quality_tier({"sampleRate": 44100, "bitDepth": 16}, "track.flac", QUALITY_PRIORITY), (4, "flac_16_44"))
        self.assertEqual(quality_tier({}, "Album [24-44.1] track.flac", QUALITY_PRIORITY), (5, "flac_hires"))
        self.assertEqual(quality_tier({}, "track.flac", QUALITY_PRIORITY), (3, "flac_cd"))

    def test_priority_order_is_respected(self):
        priority = ["flac_hires", "flac_16_44", "flac_cd", "mp3_192", "mp3_193_319", "mp3_320"]
        self.assertEqual(quality_tier({"bitRate": 320}, "track.mp3", priority), (5, "mp3_320"))
        self.assertEqual(quality_tier({}, "track.flac", priority), (2, "flac_cd"))


class SlskdSearchModuleTests(unittest.TestCase):
    def test_query_fallback_order_and_deduplication(self):
        self.assertEqual(search_queries("Tinariwen", "Idrache (Traces of the Past)"), [
            "Tinariwen Idrache (Traces of the Past)",
            "*inariwen Idrache (Traces of the Past)",
            "Tinariwen Idrache Traces of the Past",
            "Tinariwen Idrache",
        ])
        self.assertEqual(search_queries("", "Album"), [])
        self.assertEqual(search_queries("Artist", "Album"), ["Artist Album", "*rtist Album"])

    def test_response_normalization_handles_supported_shapes(self):
        first, second = {"username": "a"}, {"username": "b"}
        self.assertEqual(response_items([first, None, second]), [first, second])
        self.assertEqual(response_items({"responses": [first]}), [first])
        self.assertEqual(response_items({"items": [second]}), [second])
        self.assertEqual(response_items({"responses": "bad", "items": [second]}), [second])
        self.assertEqual(response_items(None), [])

    def test_path_matching_and_track_identity(self):
        self.assertTrue(album_path_match("Idrache (Traces of the Past)", "Tinariwen/Idrache - Traces of the Past"))
        self.assertEqual(track_identity(r"Folder\\01 - Track_1.FLAC", music_key), "01track")

    def test_candidate_extraction_keeps_quality_and_track_dedup_rules(self):
        payload = [{
            "username": "peer", "uploadSpeed": 1000,
            "files": [
                {"filename": "Tinariwen/Idrache/01 - Song.mp3", "size": 100, "bitRate": 192},
                {"filename": "Tinariwen/Idrache/01 - Song_1.flac", "size": 200},
                {"filename": "Tinariwen/Idrache/02 - Song.flac", "size": 200},
                {"filename": "Tinariwen/Idrache/03 - Song.flac", "size": 200},
                {"filename": "Tinariwen/Idrache/04 - Song.flac", "size": 200},
                {"filename": "Tinariwen/Idrache/05 - Song.flac", "size": 200},
            ],
        }]
        candidates = extract_candidates(
            payload, "Tinariwen", "Idrache", QUALITY_PRIORITY, None,
            music_key=music_key, album_path_match=album_path_match,
            quality_tier=quality_tier, track_identity=lambda name: track_identity(name, music_key),
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["unique_track_count"], 5)
        self.assertEqual(candidates[0]["file_count"], 5)
        self.assertIn("flac_cd", candidates[0]["quality_summary"])

    def test_path_diagnostics_are_bounded_and_include_match_evidence(self):
        payload = [{"username": "peer", "files": [
            {"filename": "Tinariwen/Idrache/01.flac"},
            {"filename": "Tinariwen/Other/cover.jpg"},
        ]}]
        result = path_match_diagnostics(
            payload, "Tinariwen", "Idrache", limit=99,
            music_key=music_key, album_path_match=album_path_match,
        )
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["album_path_match"])
        self.assertTrue(result[0]["artist_path_match"])


if __name__ == "__main__":
    unittest.main()
