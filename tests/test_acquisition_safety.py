"""Focused filesystem and remote-path safety regressions for acquisition helpers.

These tests compile the actual helper definitions from navidrome_server.py without
importing the full MCP server (which initializes application integrations at import).
"""
import ast
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


class FakeHTTPError(Exception):
    pass


def load_helpers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "_discovery_match_completed_album_files",
        "_discovery_import_matched_album_files",
        "_slskd_candidate_start_state",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    found = {node.name for node in selected}
    if found != wanted:
        raise AssertionError(f"Missing acquisition helpers: {sorted(wanted - found)}")

    namespace = {
        "Path": Path,
        "time": SimpleNamespace(monotonic=lambda: 0, sleep=lambda _seconds: None),
        "httpx": SimpleNamespace(
            HTTPError=FakeHTTPError,
            delete=lambda *args, **kwargs: SimpleNamespace(status_code=204),
        ),
        "_slskd_download_transfer_files": lambda *_args, **_kwargs: [],
    }
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


HELPERS = load_helpers()


class CompletedAlbumMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "downloads"
        self.source.mkdir()
        self.destination_parent = self.root / "music"
        self.destination_parent.mkdir()
        self.destination = self.destination_parent / "Artist - Album"
        self.candidate = {
            "files": [
                {"filename": "Artist - Album/01 - Track.flac", "size": 4},
                {"filename": "Artist - Album/02 - Track.flac", "size": 3},
            ]
        }
        (self.source / "01 - Track.flac").write_bytes(b"1234")
        (self.source / "02 - Track.flac").write_bytes(b"567")

    def test_import_moves_only_expected_tracks_and_leaves_unrelated_files(self):
        unrelated = self.source / "cover.jpg"
        unrelated.write_bytes(b"cover")

        HELPERS["_discovery_import_matched_album_files"](
            self.source, self.destination, self.candidate
        )

        self.assertEqual((self.destination / "01 - Track.flac").read_bytes(), b"1234")
        self.assertEqual((self.destination / "02 - Track.flac").read_bytes(), b"567")
        self.assertTrue(unrelated.exists())
        self.assertFalse(self.source.joinpath("01 - Track.flac").exists())

    def test_existing_destination_is_never_overwritten(self):
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, self.destination, self.candidate
            )

        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        self.assertTrue((self.source / "01 - Track.flac").exists())

    def test_broken_destination_symlink_is_never_overwritten(self):
        self.destination.symlink_to(self.root / "missing-target")

        with self.assertRaises(FileExistsError):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, self.destination, self.candidate
            )

        self.assertTrue(self.destination.is_symlink())
        self.assertTrue((self.source / "01 - Track.flac").exists())

    def test_symlinked_destination_parent_is_rejected(self):
        real_parent = self.root / "real-music"
        real_parent.mkdir()
        link_parent = self.root / "linked-music"
        link_parent.symlink_to(real_parent, target_is_directory=True)

        with self.assertRaises(OSError):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, link_parent / "Artist - Album", self.candidate
            )

        self.assertFalse((real_parent / "Artist - Album").exists())

    def test_conflicting_duplicate_remote_basenames_are_ambiguous(self):
        candidate = {"files": [
            {"filename": "A/01.flac", "size": 4},
            {"filename": "B/01.flac", "size": 8},
        ]}
        self.assertIsNone(
            HELPERS["_discovery_match_completed_album_files"](self.source, candidate)
        )

    def test_unique_collision_suffixed_file_can_be_matched_by_size(self):
        (self.source / "01 - Track_1.flac").write_bytes(b"1234")
        (self.source / "01 - Track.flac").unlink()
        candidate = {"files": [{"filename": "Album/01 - Track.flac", "size": 4}]}

        matched = HELPERS["_discovery_match_completed_album_files"](self.source, candidate)

        self.assertEqual(matched["01 - Track.flac"].name, "01 - Track_1.flac")


class RemoteTransferPathTests(unittest.TestCase):
    def test_parent_traversal_is_rejected_before_transfer_lookup(self):
        calls = []
        namespace = dict(HELPERS)
        namespace["_slskd_download_transfer_files"] = lambda *args: calls.append(args) or []
        candidate = {"username": "peer", "files": [
            {"filename": "Album/../Other/01.flac"}
        ]}

        result = namespace["_slskd_candidate_start_state"](
            "http://slskd", {}, candidate, timeout=1
        )

        self.assertIsNone(result)
        self.assertEqual(calls, [])

    def test_files_from_multiple_remote_directories_are_rejected(self):
        calls = []
        namespace = dict(HELPERS)
        namespace["_slskd_download_transfer_files"] = lambda *args: calls.append(args) or []
        candidate = {"username": "peer", "files": [
            {"filename": "Album/01.flac"},
            {"filename": "Other/02.flac"},
        ]}

        result = namespace["_slskd_candidate_start_state"](
            "http://slskd", {}, candidate, timeout=1
        )

        self.assertIsNone(result)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
