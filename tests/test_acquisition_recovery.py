"""Direct-import regression tests for interrupted acquisition-import recovery."""
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from acquisition_cleanup import clean_acquisition_source
from acquisition_completion import match_completed_album_files, safe_folder_name
from acquisition_recovery import reconcile_interrupted_import


class InterruptedImportRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.ns = {"MUSIC_DIR": Path("/music"), "jobs": [], "status_updates": []}
        self.transition_lock = threading.RLock()

        def is_dismissed(artist, album):
            return any(
                row.get("artist_key") == str(artist).casefold()
                and row.get("album_key") == str(album).casefold()
                and row.get("status") == "dismissed"
                for row in self.ns["jobs"]
            )

        def update_status(*args, **kwargs):
            self.ns["status_updates"].append((args, kwargs))
            return True

        self.ns["_discovery_reconcile_interrupted_import"] = lambda artist, album, candidate: (
            reconcile_interrupted_import(
                artist,
                album,
                candidate,
                transition_lock=self.transition_lock,
                is_dismissed=is_dismissed,
                music_key=lambda value: str(value or "").strip().casefold(),
                list_acquisition_jobs=lambda: self.ns["jobs"],
                music_dir=self.ns["MUSIC_DIR"],
                safe_folder_name=safe_folder_name,
                match_completed_album_files=match_completed_album_files,
                update_status=update_status,
                json_module=json,
                now=lambda: 123.0,
                move_file=shutil.move,
            )
        )

    def test_interrupted_import_is_reconciled_when_destination_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            music = Path(temp)
            destination = music / "Artist" / "Album"
            destination.mkdir(parents=True)
            (destination / "01.flac").write_bytes(b"1234")
            (destination / ".navidrome-import.json").write_text(json.dumps({
                "source": str(Path("/downloads/Album").resolve()),
                "destination": str(destination),
                "tracks": {"01.flac": 4},
            }), encoding="utf-8")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": "/downloads/Album",
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev,
                },
            })
            candidate = {
                "username": "peer",
                "files": [{"filename": "Album/01.flac", "size": 4}],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )

        self.assertTrue(recovered)
        self.assertEqual(self.ns["status_updates"][-1][0][2], "imported")
        self.assertTrue(self.ns["status_updates"][-1][0][3]["recovered_after_restart"])
        self.assertFalse((destination / ".navidrome-import.json").exists())

    def test_restart_reconciliation_refuses_changed_library_filesystem(self):
        with tempfile.TemporaryDirectory() as temp:
            music = Path(temp)
            destination = music / "Artist" / "Album"
            destination.mkdir(parents=True)
            (destination / "01.flac").write_bytes(b"1234")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": "/downloads/Album",
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev + 1,
                },
            })
            candidate = {
                "username": "peer",
                "files": [{"filename": "Album/01.flac", "size": 4}],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )
            self.assertTrue((destination / "01.flac").exists())

        self.assertFalse(recovered)
        self.assertEqual(self.ns["status_updates"], [])

    def test_partial_staging_is_rolled_back_to_download_folder_after_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            music = root / "music"
            artist_dir = music / "Artist"
            artist_dir.mkdir(parents=True)
            source = root / "downloads" / "Album"
            source.mkdir(parents=True)
            (source / "02.flac").write_bytes(b"567")
            staging = artist_dir / ".navidrome-import-interrupted"
            staging.mkdir()
            (staging / "01.flac").write_bytes(b"1234")
            destination = artist_dir / "Album"
            (staging / ".navidrome-import.json").write_text(json.dumps({
                "source": str(source.resolve()),
                "destination": str(destination),
                "tracks": {"01.flac": 4, "02.flac": 3},
            }), encoding="utf-8")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": str(source),
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev,
                },
            })
            candidate = {
                "username": "peer",
                "files": [
                    {"filename": "Album/01.flac", "size": 4},
                    {"filename": "Album/02.flac", "size": 3},
                ],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )

            self.assertFalse(recovered)
            self.assertEqual((source / "01.flac").read_bytes(), b"1234")
            self.assertEqual((source / "02.flac").read_bytes(), b"567")
            self.assertFalse(staging.exists())
            self.assertFalse(destination.exists())
            self.assertEqual(self.ns["status_updates"], [])

    def test_interrupted_import_does_not_reconcile_wrong_or_incomplete_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            music = Path(temp)
            destination = music / "Artist" / "Album"
            destination.mkdir(parents=True)
            (destination / "01.flac").write_bytes(b"bad")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": "/downloads/Album",
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev,
                },
            })
            candidate = {
                "username": "peer",
                "files": [{"filename": "Album/01.flac", "size": 4}],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )

        self.assertFalse(recovered)
        self.assertEqual(self.ns["status_updates"], [])

    def test_reconciliation_refuses_dismissed_or_non_importing_jobs(self):
        candidate = {"username": "peer", "files": [{"filename": "Album/01.flac", "size": 4}]}
        for status in ("dismissed", "downloading"):
            with self.subTest(status=status):
                self.ns["jobs"][:] = [{
                    "artist_key": "artist",
                    "album_key": "album",
                    "status": status,
                    "details": {"destination": "/tmp/Artist/Album"},
                }]
                self.ns["status_updates"].clear()
                self.assertFalse(self.ns["_discovery_reconcile_interrupted_import"]("Artist", "Album", candidate))
                self.assertEqual(self.ns["status_updates"], [])
