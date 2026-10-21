"""Direct-import regression tests for safe album filesystem imports."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from acquisition.import_files import import_matched_album_files
from acquisition.import_service import import_completed_source_locked


class AcquisitionImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "downloads"
        self.source.mkdir()
        self.music = self.root / "music"
        self.music.mkdir()
        self.destination = self.music / "Artist - Album"
        self.candidate = {
            "files": [
                {"filename": "Artist - Album/01 - Track.flac", "size": 4},
                {"filename": "Artist - Album/02 - Track.flac", "size": 3},
            ]
        }
        (self.source / "01 - Track.flac").write_bytes(b"1234")
        (self.source / "02 - Track.flac").write_bytes(b"567")

    def test_imports_only_expected_tracks_and_preserves_unrelated_files(self):
        unrelated = self.source / "cover.jpg"
        unrelated.write_bytes(b"cover")

        import_matched_album_files(self.source, self.destination, self.candidate)

        self.assertEqual((self.destination / "01 - Track.flac").read_bytes(), b"1234")
        self.assertEqual((self.destination / "02 - Track.flac").read_bytes(), b"567")
        self.assertTrue(unrelated.exists())
        self.assertFalse((self.destination / ".navidrome-import.json").exists())
        self.assertFalse((self.source / "01 - Track.flac").exists())

    def test_existing_destination_is_not_overwritten(self):
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            import_matched_album_files(self.source, self.destination, self.candidate)

        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        self.assertTrue((self.source / "01 - Track.flac").exists())

    def test_partial_move_failure_rolls_tracks_back(self):
        import os
        original_rename = os.rename
        calls = {"count": 0}

        def fail_on_second_move(src, dst, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("simulated second-track move failure")
            return original_rename(src, dst, *args, **kwargs)

        with patch("os.rename", side_effect=fail_on_second_move):
            with self.assertRaisesRegex(OSError, "simulated second-track move failure"):
                import_matched_album_files(self.source, self.destination, self.candidate)

        self.assertFalse(self.destination.exists())
        self.assertEqual((self.source / "01 - Track.flac").read_bytes(), b"1234")
        self.assertEqual((self.source / "02 - Track.flac").read_bytes(), b"567")
        self.assertEqual(list(self.music.glob(".navidrome-import-*")), [])

    def test_import_preserves_collision_suffixed_source_matching(self):
        self.candidate = {
            "files": [{"filename": "Album/01 - Track.flac", "size": 4}]
        }
        (self.source / "01 - Track.flac").unlink()
        (self.source / "02 - Track.flac").unlink()
        (self.source / "01 - Track_1.flac").write_bytes(b"1234")

        import_matched_album_files(self.source, self.destination, self.candidate)

        self.assertEqual((self.destination / "01 - Track.flac").read_bytes(), b"1234")
        self.assertFalse((self.source / "01 - Track_1.flac").exists())

    def test_cross_filesystem_fallback_copies_then_removes_only_verified_source(self):
        import errno
        import os
        original_rename = os.rename
        calls = {"count": 0}

        def force_first_cross_device_move(src, dst, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError(errno.EXDEV, "simulated cross-filesystem move")
            return original_rename(src, dst, *args, **kwargs)

        with patch("os.rename", side_effect=force_first_cross_device_move):
            import_matched_album_files(self.source, self.destination, self.candidate)

        self.assertEqual((self.destination / "01 - Track.flac").read_bytes(), b"1234")
        self.assertEqual((self.destination / "02 - Track.flac").read_bytes(), b"567")
        self.assertFalse((self.source / "01 - Track.flac").exists())
        self.assertFalse((self.source / "02 - Track.flac").exists())
        self.assertFalse((self.destination / ".navidrome-import.json").exists())

    def test_source_directory_replaced_by_symlink_after_matching_cannot_move_outside_files(self):
        outside = self.root / "outside"
        outside.mkdir()
        outside_first = outside / "01 - Track.flac"
        outside_second = outside / "02 - Track.flac"
        outside_first.write_bytes(b"OUT!")
        outside_second.write_bytes(b"OUT")

        moved_source = self.root / "downloads-original"

        def match_then_swap(source, candidate):
            matched = {
                name: Path(source) / name
                for name in ("01 - Track.flac", "02 - Track.flac")
            }
            self.source.rename(moved_source)
            self.source.symlink_to(outside, target_is_directory=True)
            return matched

        with self.assertRaises(OSError):
            import_matched_album_files(
                self.source,
                self.destination,
                self.candidate,
                match_files=match_then_swap,
            )

        self.assertTrue(outside_first.exists())
        self.assertEqual(outside_first.read_bytes(), b"OUT!")
        self.assertTrue(outside_second.exists())
        self.assertEqual(outside_second.read_bytes(), b"OUT")
        self.assertTrue((moved_source / "01 - Track.flac").exists())
        self.assertEqual((moved_source / "01 - Track.flac").read_bytes(), b"1234")
        self.assertTrue((moved_source / "02 - Track.flac").exists())
        self.assertEqual((moved_source / "02 - Track.flac").read_bytes(), b"567")
        self.assertFalse(self.destination.exists())
        self.assertTrue(self.source.is_symlink())

    def test_storage_identity_mismatch_aborts_before_staging(self):
        with self.assertRaisesRegex(OSError, "filesystem changed"):
            import_matched_album_files(
                self.source,
                self.destination,
                self.candidate,
                expected_music_root=self.music,
                expected_device=self.music.stat().st_dev + 1,
            )

        self.assertTrue((self.source / "01 - Track.flac").exists())
        self.assertTrue((self.source / "02 - Track.flac").exists())
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.music.iterdir()), [])

    def test_rejects_reserved_manifest_filename(self):
        candidate = {
            "files": [
                {"filename": "Album/.NAVIDROME-IMPORT.JSON", "size": 4},
            ]
        }
        (self.source / ".NAVIDROME-IMPORT.JSON").write_bytes(b"1234")

        with self.assertRaisesRegex(OSError, "reserved import manifest"):
            import_matched_album_files(self.source, self.destination, candidate)

        self.assertTrue((self.source / ".NAVIDROME-IMPORT.JSON").exists())
        self.assertFalse(self.destination.exists())


class ImportCompletionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "downloads"
        self.source.mkdir()
        self.music = self.root / "music"
        self.music.mkdir()
        self.candidate = {"username": "peer", "files": []}
        self.statuses = []
        self.import_calls = []

    def run_import(self, music_root=None, status_result=True):
        def update_status(artist, album, status, details):
            self.statuses.append((artist, album, status, details))
            if status == "importing":
                return status_result
            return True

        def import_files(source, destination, candidate, **kwargs):
            self.import_calls.append((source, destination, candidate, kwargs))

        return import_completed_source_locked(
            "Artist", "Album", self.source,
            self.music if music_root is None else music_root,
            self.candidate,
            safe_folder_name=lambda value: value.replace("/", "_"),
            update_status=update_status,
            import_matched_album_files=import_files,
            now=lambda: 123.0,
        )

    def test_importing_status_persistence_failure_prevents_filesystem_mutation(self):
        self.assertEqual(self.run_import(status_result=False), "failed")
        self.assertEqual([row[2] for row in self.statuses], ["importing"])
        self.assertEqual(self.import_calls, [])
        self.assertFalse((self.music / "Artist").exists())
        self.assertTrue(self.source.is_dir())

    def test_success_persists_importing_before_import_and_then_imported(self):
        self.assertEqual(self.run_import(), "imported")
        self.assertEqual([row[2] for row in self.statuses], ["importing", "imported"])
        self.assertEqual(len(self.import_calls), 1)
        source, destination, candidate, kwargs = self.import_calls[0]
        self.assertEqual(source, self.source)
        self.assertEqual(destination, self.music / "Artist" / "Album")
        self.assertIs(candidate, self.candidate)
        self.assertEqual(kwargs["expected_music_root"], self.music.resolve())
        self.assertEqual(kwargs["expected_device"], self.music.stat().st_dev)
        self.assertEqual(self.statuses[-1][3]["imported_at"], 123.0)

    def test_symlinked_artist_destination_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.music / "Artist").symlink_to(outside, target_is_directory=True)

        self.assertEqual(self.run_import(), "failed")
        self.assertEqual(self.statuses[-1][2], "download_complete_move_failed")
        self.assertEqual(self.import_calls, [])
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_album_destination_is_not_overwritten(self):
        destination = self.music / "Artist" / "Album"
        destination.mkdir(parents=True)
        marker = destination / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")

        self.assertEqual(self.run_import(), "failed")
        self.assertEqual(self.statuses[-1][2], "destination_exists")
        self.assertEqual(self.import_calls, [])
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_unavailable_library_mount_refuses_import(self):
        self.assertEqual(self.run_import(music_root=self.root / "missing"), "failed")
        self.assertEqual(self.statuses[-1][2], "library_mount_unavailable")
        self.assertEqual(self.import_calls, [])


if __name__ == "__main__":
    unittest.main()
