"""Direct regression tests for completed-download matching and folder diagnostics."""
import tempfile
import unittest
import unicodedata
from pathlib import Path

from acquisition_completion import (
    filename_key,
    inspect_completed_album,
    match_completed_album_files,
    safe_folder_name,
)


def inspect(root, candidate):
    return inspect_completed_album(
        root,
        candidate,
        safe_folder_name=safe_folder_name,
        filename_key=filename_key,
        match_files=match_completed_album_files,
    )


class CompletedFolderEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "downloads"
        self.root.mkdir()
        self.candidate = {
            "folder": "Artist/Reality Awaits",
            "files": [
                {"filename": "Reality Awaits/01 - Intro.flac", "size": 4},
                {"filename": "Reality Awaits/02 - Song.flac", "size": 5},
            ],
        }

    def make_album(self, folder_name="Reality Awaits"):
        folder = self.root / folder_name
        folder.mkdir(parents=True)
        (folder / "01 - Intro.flac").write_bytes(b"1234")
        (folder / "02 - Song.flac").write_bytes(b"12345")
        return folder

    def test_complete_unambiguous_folder_is_selected(self):
        folder = self.make_album()
        result = inspect(self.root, self.candidate)
        self.assertEqual(result["path"], folder)
        self.assertEqual(result["diagnostics"]["folder_diagnostic"], "matched")

    def test_complete_tracks_under_different_folder_name_are_explained_not_imported(self):
        self.make_album("Reality Awaits [MP3 320]")
        result = inspect(self.root, self.candidate)
        self.assertIsNone(result["path"])
        self.assertEqual(
            result["diagnostics"]["folder_diagnostic"],
            "tracks_match_but_folder_name_differs",
        )
        evidence = result["diagnostics"]["diagnostic_candidates"][0]
        self.assertTrue(evidence["track_files_match"])
        self.assertFalse(evidence["folder_name_matches"])

    def test_expected_folder_with_missing_track_reports_exact_filename(self):
        folder = self.root / "Reality Awaits"
        folder.mkdir()
        (folder / "01 - Intro.flac").write_bytes(b"1234")
        result = inspect(self.root, self.candidate)
        self.assertIsNone(result["path"])
        self.assertEqual(
            result["diagnostics"]["folder_diagnostic"],
            "expected_folder_tracks_mismatch",
        )
        evidence = result["diagnostics"]["diagnostic_candidates"][0]
        self.assertEqual(evidence["missing_expected_files"], ["02 - Song.flac"])

    def test_collision_suffixed_track_is_not_reported_missing(self):
        folder = self.make_album()
        original = folder / "01 - Intro.flac"
        original.rename(folder / "01 - Intro_1.flac")
        result = inspect(self.root, self.candidate)
        self.assertEqual(result["path"], folder)
        evidence = result["diagnostics"]["diagnostic_candidates"][0]
        self.assertEqual(evidence["missing_expected_files"], [])

    def test_expected_folder_with_wrong_size_reports_size_mismatch(self):
        folder = self.root / "Reality Awaits"
        folder.mkdir()
        (folder / "01 - Intro.flac").write_bytes(b"wrong-size")
        (folder / "02 - Song.flac").write_bytes(b"12345")
        result = inspect(self.root, self.candidate)
        evidence = result["diagnostics"]["diagnostic_candidates"][0]
        self.assertEqual(evidence["size_mismatches"], ["01 - Intro.flac"])

    def test_missing_download_root_is_distinguished_from_missing_album_folder(self):
        missing_root = self.root / "not-mounted"
        result = inspect(missing_root, self.candidate)
        self.assertEqual(
            result["diagnostics"]["folder_diagnostic"],
            "downloads_root_unavailable",
        )
        self.assertFalse(result["diagnostics"]["downloads_path_available"])

    def test_two_valid_folders_are_reported_as_ambiguous(self):
        self.make_album()
        nested = self.root / "nested" / "Reality Awaits"
        nested.mkdir(parents=True)
        (nested / "01 - Intro.flac").write_bytes(b"1234")
        (nested / "02 - Song.flac").write_bytes(b"12345")
        result = inspect(self.root, self.candidate)
        self.assertIsNone(result["path"])
        self.assertEqual(
            result["diagnostics"]["folder_diagnostic"],
            "ambiguous_named_folder_matches",
        )


class CompletedTrackMatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "01 - Track.flac").write_bytes(b"1234")

    def test_filename_key_normalizes_unicode_and_case(self):
        composed = "Beyoncé.flac"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertEqual(filename_key(composed), filename_key(decomposed.upper()))

    def test_windows_remote_path_matches_local_basename(self):
        candidate = {"files": [{"filename": r"Album\\01 - Track.flac", "size": 4}]}
        matched = match_completed_album_files(self.folder, candidate)
        self.assertEqual(matched["01 - Track.flac"], self.folder / "01 - Track.flac")

    def test_conflicting_duplicate_remote_basenames_fail_closed(self):
        candidate = {"files": [
            {"filename": "A/01.flac", "size": 4},
            {"filename": "B/01.flac", "size": 8},
        ]}
        self.assertIsNone(match_completed_album_files(self.folder, candidate))

    def test_missing_or_non_positive_sizes_fail_closed(self):
        for size in (None, 0, -1, "unknown"):
            with self.subTest(size=size):
                self.assertIsNone(match_completed_album_files(
                    self.folder, {"files": [{"filename": "01 - Track.flac", "size": size}]}
                ))

    def test_unique_collision_suffix_requires_advertised_size(self):
        (self.folder / "01 - Track.flac").unlink()
        (self.folder / "01 - Track_1.flac").write_bytes(b"1234")
        candidate = {"files": [{"filename": "Album/01 - Track.flac", "size": 4}]}
        matched = match_completed_album_files(self.folder, candidate)
        self.assertEqual(matched["01 - Track.flac"].name, "01 - Track_1.flac")

    def test_multiple_collision_candidates_are_ambiguous(self):
        (self.folder / "01 - Track.flac").unlink()
        (self.folder / "01 - Track_1.flac").write_bytes(b"1234")
        (self.folder / "01 - Track_2.flac").write_bytes(b"5678")
        candidate = {"files": [{"filename": "Album/01 - Track.flac", "size": 4}]}
        self.assertIsNone(match_completed_album_files(self.folder, candidate))

    def test_symlinked_track_is_not_accepted(self):
        (self.folder / "01 - Track.flac").unlink()
        target = self.folder / "outside.flac"
        target.write_bytes(b"1234")
        (self.folder / "01 - Track.flac").symlink_to(target)
        candidate = {"files": [{"filename": "Album/01 - Track.flac", "size": 4}]}
        self.assertIsNone(match_completed_album_files(self.folder, candidate))

    def test_folder_name_sanitization_uses_final_component_and_removes_nul(self):
        self.assertEqual(safe_folder_name("Artist\\\\Album\\0."), "Album")




if __name__ == "__main__":
    unittest.main()
