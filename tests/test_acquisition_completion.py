"""Focused tests for completed-download folder evidence and diagnostics."""
import tempfile
import unicodedata
import unittest
from pathlib import Path

from acquisition_completion import inspect_completed_album


def filename_key(value):
    return unicodedata.normalize("NFC", str(value or "")).casefold()


def safe_folder_name(value):
    return str(value or "").replace("\\", "/").split("/")[-1].strip(". ") or "Unknown"


def match_files(folder, candidate):
    """Small strict matcher contract: every advertised basename and size must match."""
    folder = Path(folder)
    actual = [
        path for path in folder.iterdir()
        if path.is_file() and not path.is_symlink()
    ]
    matched = {}
    used = set()
    for item in candidate.get("files") or []:
        name = str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1]
        if not name:
            return None
        try:
            size = int(item.get("size"))
        except (TypeError, ValueError):
            return None
        options = [
            path for path in actual
            if filename_key(path.name) == filename_key(name)
            and path not in used
            and size > 0
            and path.stat().st_size == size
        ]
        if len(options) != 1:
            return None
        matched[name] = options[0]
        used.add(options[0])
    return matched or None


def inspect(root, candidate):
    return inspect_completed_album(
        root,
        candidate,
        safe_folder_name=safe_folder_name,
        filename_key=filename_key,
        match_files=match_files,
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


if __name__ == "__main__":
    unittest.main()
