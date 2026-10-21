"""Direct-import tests for reviewed slskd candidate payload normalization."""
import unittest

from acquisition.candidate_queue import normalize_reviewed_candidate_files


class ReviewedCandidateNormalizationTests(unittest.TestCase):
    def test_normalizes_file_names_and_sizes_and_preserves_quality_summary(self):
        files, quality, error = normalize_reviewed_candidate_files(
            [{"filename": "Artist/Album/01.flac", "size": "2048"}, {"filename": "02.flac"}],
            '[{"tier":"FLAC CD"}]',
        )
        self.assertIsNone(error)
        self.assertEqual(files, [
            {"filename": "Artist/Album/01.flac", "size": 2048},
            {"filename": "02.flac", "size": 0},
        ])
        self.assertEqual(quality, [{"tier": "FLAC CD"}])

    def test_rejects_missing_or_empty_file_list(self):
        for value in (None, {}, [], "not a list"):
            with self.subTest(value=value):
                files, quality, error = normalize_reviewed_candidate_files(value)
                self.assertIsNone(files)
                self.assertEqual(quality, [])
                self.assertEqual(error, "files_json must be a non-empty JSON list.")

    def test_rejects_items_without_a_filename(self):
        for value in ([{}], ["track.flac"], [{"filename": ""}]):
            with self.subTest(value=value):
                files, quality, error = normalize_reviewed_candidate_files(value)
                self.assertIsNone(files)
                self.assertEqual(error, "Each file requires a filename.")

    def test_invalid_quality_summary_falls_back_to_empty_list(self):
        files, quality, error = normalize_reviewed_candidate_files(
            [{"filename": "track.flac"}], "invalid json"
        )
        self.assertIsNone(error)
        self.assertEqual(files, [{"filename": "track.flac", "size": 0}])
        self.assertEqual(quality, [])

    def test_invalid_file_size_keeps_raising_for_compatibility_adapter(self):
        with self.assertRaises(ValueError):
            normalize_reviewed_candidate_files([{"filename": "track.flac", "size": "bad"}])


if __name__ == "__main__":
    unittest.main()
