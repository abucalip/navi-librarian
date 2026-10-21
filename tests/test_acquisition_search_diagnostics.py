"""Direct regression tests for slskd search diagnostics."""
import unittest

from acquisition.search_diagnostics import (
    candidate_diagnostics,
    count_audio_files,
    no_match_message,
)


class AcquisitionSearchDiagnosticsTests(unittest.TestCase):
    def test_candidate_diagnostics_are_bounded_projected_and_copied(self):
        summary = ["MP3 320"]
        candidates = [
            {
                "username": f"peer-{index}", "folder": "Artist - Album",
                "file_count": 12, "unique_track_count": 11,
                "expected_track_count": 11, "quality_summary": summary,
                "clear_match": index == 0, "eligibility_reason": None,
                "private_field": "must not leak",
            }
            for index in range(12)
        ]
        result = candidate_diagnostics(candidates)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], {
            "username": "peer-0", "folder": "Artist - Album",
            "file_count": 12, "unique_track_count": 11,
            "expected_track_count": 11, "quality_summary": ["MP3 320"],
            "clear_match": True, "eligibility_reason": None,
        })
        result[0]["quality_summary"].append("changed")
        self.assertEqual(summary, ["MP3 320"])
        self.assertEqual(candidate_diagnostics(candidates, limit=0), [])

    def test_audio_count_accepts_filename_or_path_and_known_extensions(self):
        payloads = {
            "peer-a": {"files": [
                {"filename": "one.MP3"}, {"path": "two.flac"},
                {"filename": "cover.jpg"}, {"filename": "notes.txt"},
                "not-a-record", {},
            ]},
            "peer-b": {"files": [{"filename": "three.OGG"}, {"filename": "no-extension"}]},
            "peer-c": {"files": None},
        }
        self.assertEqual(count_audio_files(payloads), 3)

    def test_no_match_message_preserves_counts_and_query_order(self):
        message = no_match_message(
            response_count=2, audio_file_count=5,
            reported_response_count=8, reported_file_count=40,
            search_attempts=[{"query": "Artist Album"}, {"query": "Album Artist"}],
        )
        self.assertEqual(
            message,
            "No matching album folders were found among 2 collected peer responses "
            "(5 audio files). slskd reported up to 8 responses and 40 files across the "
            "search attempts. If the counts are zero, no peers answered the attempted "
            "queries; otherwise the response payloads may not have been available to "
            "Librarian. Queries tried: Artist Album -> Album Artist.",
        )
