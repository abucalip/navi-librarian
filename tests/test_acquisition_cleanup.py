"""Direct-import regression tests for destructive acquisition cleanup."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from acquisition_cleanup import clean_acquisition_source as _clean_acquisition_source
from acquisition_completion import safe_folder_name


class FakeHTTPError(Exception):
    pass


class AcquisitionDismissalCleanupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "downloads"
        self.root.mkdir()
        self.folder = self.root / "Album"
        self.folder.mkdir()
        self.track = self.folder / "01.flac"
        self.track.write_bytes(b"1234")
        self.candidate = {
            "username": "peer",
            "folder": "Album",
            "files": [{"filename": "Album/01.flac", "size": 4}],
        }
        self.safe_folder_name = safe_folder_name
        self.http_client = SimpleNamespace(
            HTTPError=FakeHTTPError,
            delete=lambda *args, **kwargs: SimpleNamespace(status_code=204),
        )

    def clean(self, tracked_batches):
        calls = []
        batches = list(tracked_batches)

        def transfers(*args):
            calls.append(args)
            return batches.pop(0) if batches else []

        result = _clean_acquisition_source(
            self.root,
            self.candidate,
            "http://slskd",
            {"X-API-KEY": "test"},
            safe_folder_name=self.safe_folder_name,
            download_transfer_files=transfers,
            http_client=self.http_client,
        )
        return result, calls

    def test_cleanup_removes_only_verified_album_tracks_after_transfer_stops(self):
        active = [{
            "id": "transfer-1",
            "filename": "Album/01.flac",
            "_transfer_directory": "Album",
            "size": 4,
            "state": "transferring",
        }]
        result, calls = self.clean([active, []])
        self.assertTrue(result)
        self.assertFalse(self.track.exists())
        self.assertFalse(self.folder.exists())
        self.assertEqual(len(calls), 2)

    def test_unrelated_entry_refuses_cleanup_without_deleting_anything(self):
        unrelated = self.folder / "cover.jpg"
        unrelated.write_bytes(b"cover")
        result, calls = self.clean([[]])
        self.assertFalse(result)
        self.assertTrue(self.track.exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual(calls, [])

    def test_cleanup_preserves_neighboring_files_and_folders(self):
        neighbor_file = self.root / "Album Artwork.jpg"
        neighbor_file.write_bytes(b"artwork")
        neighbor_folder = self.root / "Other Album"
        neighbor_folder.mkdir()
        neighbor_track = neighbor_folder / "01.flac"
        neighbor_track.write_bytes(b"neighbor")

        result, calls = self.clean([[]])

        self.assertTrue(result)
        self.assertFalse(self.track.exists())
        self.assertFalse(self.folder.exists())
        self.assertTrue(neighbor_file.exists())
        self.assertEqual(neighbor_file.read_bytes(), b"artwork")
        self.assertTrue(neighbor_track.exists())
        self.assertEqual(neighbor_track.read_bytes(), b"neighbor")
        self.assertEqual(len(calls), 2)

    def test_remote_path_traversal_is_rejected_before_transfer_lookup(self):
        self.candidate["files"][0]["filename"] = "Album/../Other/01.flac"
        result, calls = self.clean([[]])
        self.assertFalse(result)
        self.assertTrue(self.track.exists())
        self.assertEqual(calls, [])

    def test_ambiguous_remote_paths_are_rejected_before_transfer_lookup(self):
        for filename in (
            "/Album/01.flac",
            "Album/./01.flac",
            "Album//01.flac",
            r"C:\\Album\\01.flac",
        ):
            with self.subTest(filename=filename):
                self.candidate["files"][0]["filename"] = filename
                result, calls = self.clean([[]])
                self.assertFalse(result)
                self.assertTrue(self.track.exists())
                self.assertEqual(calls, [])

    def test_duplicate_named_folders_are_rejected_as_ambiguous(self):
        self.track.unlink()
        self.folder.rmdir()
        nested_a = self.root / "one" / "Album"
        nested_b = self.root / "two" / "Album"
        nested_a.mkdir(parents=True)
        nested_b.mkdir(parents=True)
        track_a = nested_a / "01.flac"
        track_b = nested_b / "01.flac"
        track_a.write_bytes(b"1234")
        track_b.write_bytes(b"1234")
        result, calls = self.clean([[]])
        self.assertFalse(result)
        self.assertTrue(track_a.exists())
        self.assertTrue(track_b.exists())
        self.assertEqual(calls, [])

    def test_symlinked_album_folder_is_rejected_without_touching_target(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        protected = outside / "01.flac"
        protected.write_bytes(b"keep")
        self.track.unlink()
        self.folder.rmdir()
        self.folder.symlink_to(outside, target_is_directory=True)
        result, calls = self.clean([[]])
        self.assertFalse(result)
        self.assertTrue(protected.exists())
        self.assertEqual(protected.read_bytes(), b"keep")
        self.assertEqual(calls, [])

    def test_directory_replaced_by_symlink_during_transfer_lookup_cannot_delete_outside_files(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        protected = outside / "01.flac"
        protected.write_bytes(b"outside")
        moved = self.root / "Album-original"
        calls = []

        def transfers(*args):
            calls.append(args)
            if len(calls) == 1:
                self.folder.rename(moved)
                self.folder.symlink_to(outside, target_is_directory=True)
            return []

        result = _clean_acquisition_source(
            self.root,
            self.candidate,
            "http://slskd",
            {"X-API-KEY": "test"},
            safe_folder_name=self.safe_folder_name,
            download_transfer_files=transfers,
            http_client=self.http_client,
        )

        self.assertFalse(result)
        self.assertTrue(protected.exists())
        self.assertEqual(protected.read_bytes(), b"outside")
        self.assertTrue((moved / "01.flac").exists())
        self.assertEqual((moved / "01.flac").read_bytes(), b"1234")
        self.assertTrue(self.folder.is_symlink())
        self.assertEqual(len(calls), 2)

    def test_parent_directory_replaced_by_symlink_cannot_redirect_cleanup_root(self):
        container = Path(self.temp.name) / "download-container"
        container.mkdir()
        self.root = container / "downloads"
        self.root.mkdir()
        self.folder = self.root / "Album"
        self.folder.mkdir()
        self.track = self.folder / "01.flac"
        self.track.write_bytes(b"1234")

        outside_container = Path(self.temp.name) / "outside-container"
        outside_container.mkdir()
        outside_root = outside_container / "downloads"
        outside_root.mkdir()
        outside_album = outside_root / "Album"
        outside_album.mkdir()
        protected = outside_album / "01.flac"
        protected.write_bytes(b"outside")
        moved_container = Path(self.temp.name) / "download-container-original"
        calls = []

        def transfers(*args):
            calls.append(args)
            if len(calls) == 1:
                container.rename(moved_container)
                container.symlink_to(outside_container, target_is_directory=True)
            return []

        result = _clean_acquisition_source(
            self.root,
            self.candidate,
            "http://slskd",
            {"X-API-KEY": "test"},
            safe_folder_name=self.safe_folder_name,
            download_transfer_files=transfers,
            http_client=self.http_client,
        )

        self.assertFalse(result)
        self.assertTrue(protected.exists())
        self.assertEqual(protected.read_bytes(), b"outside")
        self.assertTrue((moved_container / "downloads" / "Album" / "01.flac").exists())
        self.assertEqual(
            (moved_container / "downloads" / "Album" / "01.flac").read_bytes(),
            b"1234",
        )
        self.assertTrue(container.is_symlink())
        self.assertEqual(len(calls), 2)

    def test_failed_transfer_cancellation_preserves_local_files(self):
        active = [{
            "id": "transfer-1",
            "filename": "Album/01.flac",
            "_transfer_directory": "Album",
            "size": 4,
            "state": "queued",
        }]
        client = self.http_client
        original_delete = client.delete
        client.delete = lambda *args, **kwargs: SimpleNamespace(status_code=500)
        try:
            result, calls = self.clean([active])
        finally:
            client.delete = original_delete
        self.assertFalse(result)
        self.assertTrue(self.track.exists())
        self.assertEqual(self.track.read_bytes(), b"1234")
        self.assertEqual(len(calls), 1)

