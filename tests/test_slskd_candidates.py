"""Direct-import regression tests for slskd candidate grouping and ranking."""

import unittest

from discovery_recommendations import music_key
from integrations.slskd.quality import quality_tier
from integrations.slskd.search import album_path_match, extract_candidates, track_identity


class SlskdCandidateExtractionTests(unittest.TestCase):
    def test_tinariwen_idrache_source_folder_variants_are_clear_candidates(self):
        priority = ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"]
        tracks = [
            "Soixante Trois", "Assuf Ag Assuf", "Amoss Idjraw", "Azaman Amikankanen",
            "Adounia Nissan", "Amidinin War Hi Toyed", "Imidiwan Ma Tennam",
            "Alkhar Dessouf", "Tenere Maloulat", "Tenhert", "Adounia Ti Chidjret",
            "Tenere Dafeo Nikchan",
        ]
        folders = [
            r"Tinariwen\2024 - Idrache Traces of the Past",
            r"Music\Tinariwen\Tinariwen - Idrache (Traces Of The Past) - 2024",
            r"Tinariwen\2024 - Idrache (Traces Of The Past) [24-44.1]",
            r"Tinariwen\2024 - Idrache (Traces Of The Past)",
        ]
        responses = []
        for index, folder in enumerate(folders):
            files = []
            for track_number, title in enumerate(tracks, 1):
                item = {"filename": f"{folder}\\{track_number:02d} - {title}.flac", "size": 5000000}
                if index == 0:
                    item.update({"sampleRate": 44100, "bitDepth": 16})
                files.append(item)
            responses.append({"username": f"peer-{index}", "files": files})

        candidates = extract_candidates(
            responses, "Tinariwen", "Idrache (Traces of the past)", priority,
            expected_track_count=12,
            music_key=music_key,
            album_path_match=album_path_match,
            quality_tier=quality_tier,
            track_identity=lambda filename: track_identity(filename, music_key),
        )
        self.assertEqual(len(candidates), 4)
        self.assertTrue(all(item["clear_match"] for item in candidates))
        self.assertTrue(all(item["unique_track_count"] == 12 for item in candidates))
        all_tiers = [tier for item in candidates for tier in item["quality_summary"]]
        self.assertIn("flac_16_44", all_tiers)
        self.assertIn("flac_hires", all_tiers)


if __name__ == "__main__":
    unittest.main()
