"""Direct-import regressions for acquisition monitor payload preparation."""

import unittest

from acquisition.monitor_payload import prepare_candidate_for_monitor


class AcquisitionMonitorPayloadTests(unittest.TestCase):
    def test_normalizes_selected_and_fallback_file_records_without_mutating_inputs(self):
        selected = {
            "username": "peer-a",
            "folder": "Artist/Album",
            "files": [
                {"filename": "Artist/Album/01.flac", "size": 100, "extra": "drop"},
            ],
            "quality_summary": ("flac_cd",),
            "upload_speed": 123,
        }
        fallback = {
            "username": "peer-b",
            "files": [
                {"filename": "Artist/Album/01.flac", "size": 100, "extra": "drop"},
            ],
            "candidate_score": 42,
        }

        result = prepare_candidate_for_monitor(selected, [fallback])

        self.assertEqual(result, {
            "username": "peer-a",
            "folder": "Artist/Album",
            "files": [{"filename": "Artist/Album/01.flac", "size": 100}],
            "quality_summary": ["flac_cd"],
            "upload_speed": 123,
            "fallback_candidates": [{
                "username": "peer-b",
                "files": [{"filename": "Artist/Album/01.flac", "size": 100}],
                "candidate_score": 42,
            }],
        })
        self.assertEqual(selected["files"][0]["extra"], "drop")
        self.assertEqual(selected["quality_summary"], ("flac_cd",))
        self.assertEqual(fallback["files"][0]["extra"], "drop")

    def test_missing_quality_summary_and_fallbacks_become_empty_lists(self):
        result = prepare_candidate_for_monitor({
            "username": "peer", "files": [{"filename": "Album/01.mp3", "size": 1}],
        }, [])
        self.assertEqual(result["quality_summary"], [])
        self.assertEqual(result["fallback_candidates"], [])
        self.assertEqual(result["files"], [{"filename": "Album/01.mp3", "size": 1}])


if __name__ == "__main__":
    unittest.main()
