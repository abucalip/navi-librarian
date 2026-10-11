"""Regression tests for acquisition path/import safety and lifecycle guards.

The tests compile selected real function definitions from navidrome_server.py into
a small stubbed namespace, avoiding import-time initialization of the full MCP app.
"""
import ast
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


class FakeHTTPError(Exception):
    pass


def load_helpers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "_discovery_match_completed_album_files",
        "_discovery_import_matched_album_files",
        "_slskd_candidate_start_state",
        "_discovery_queue_candidate_unless_dismissed",
        "discovery_acquire_album",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    found = {node.name for node in selected}
    if found != wanted:
        raise AssertionError(f"Missing acquisition helpers: {sorted(wanted - found)}")
    # The public MCP decorator is an app-registration detail; exercise the actual
    # function body without importing/initializing MCPServer.
    for node in selected:
        node.decorator_list = []

    namespace = {
        "Path": Path,
        "json": json,
        "threading": threading,
        "_DISCOVERY_IMPORT_TRANSITION_LOCK": threading.RLock(),
        "_DISCOVERY_IMPORT_LOCK": threading.Lock(),
        "_DISCOVERY_IMPORT_ACTIVE": set(),
        "_DISCOVERY_ACQUIRE_ACTIVE": set(),
        "jobs": [],
        "time": SimpleNamespace(monotonic=lambda: 0, sleep=lambda _seconds: None),
        "httpx": SimpleNamespace(
            HTTPError=FakeHTTPError,
            delete=lambda *args, **kwargs: SimpleNamespace(status_code=204),
            post=lambda *args, **kwargs: SimpleNamespace(
                status_code=200, raise_for_status=lambda: None
            ),
        ),
        "_slskd_download_transfer_files": lambda *_args, **_kwargs: [],
        "_music_key": lambda value: str(value or "").strip().casefold(),
    }
    namespace["_discovery_list_acquisition_jobs"] = lambda: namespace["jobs"]
    namespace["_discovery_is_dismissed"] = lambda artist, album: any(
        row.get("artist_key") == namespace["_music_key"](artist)
        and row.get("album_key") == namespace["_music_key"](album)
        and row.get("status") == "dismissed"
        for row in namespace["jobs"]
    )

    def start_watcher(artist, album, candidate, settings):
        identity = (namespace["_music_key"](artist), namespace["_music_key"](album))
        with namespace["_DISCOVERY_IMPORT_LOCK"]:
            namespace["_DISCOVERY_IMPORT_ACTIVE"].add(identity)

    namespace["_discovery_start_import_watcher"] = start_watcher
    namespace["_discovery_acquire_album_impl"] = lambda *args: json.dumps({
        "ok": True, "status": "implementation_called"
    })
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


class AcquisitionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_helpers()

    def test_parent_traversal_is_rejected_before_transfer_lookup(self):
        calls = []
        self.ns["_slskd_download_transfer_files"] = lambda *args: calls.append(args) or []
        candidate = {"username": "peer", "files": [
            {"filename": "Album/../Other/01.flac"}
        ]}
        result = self.ns["_slskd_candidate_start_state"](
            "http://slskd", {}, candidate, timeout=1
        )
        self.assertIsNone(result)
        self.assertEqual(calls, [])

    def test_files_from_multiple_remote_directories_are_rejected(self):
        calls = []
        self.ns["_slskd_download_transfer_files"] = lambda *args: calls.append(args) or []
        candidate = {"username": "peer", "files": [
            {"filename": "Album/01.flac"},
            {"filename": "Other/02.flac"},
        ]}
        result = self.ns["_slskd_candidate_start_state"](
            "http://slskd", {}, candidate, timeout=1
        )
        self.assertIsNone(result)
        self.assertEqual(calls, [])

    def test_dismissed_acquisition_is_not_queued(self):
        posts = []
        self.ns["httpx"].post = lambda *args, **kwargs: posts.append(args)
        self.ns["jobs"].append({
            "artist_key": "artist", "album_key": "album", "status": "dismissed"
        })
        result = self.ns["_discovery_queue_candidate_unless_dismissed"](
            "Artist", "Album", "http://slskd", {}, "peer", ["Album/01.flac"]
        )
        self.assertIsNone(result)
        self.assertEqual(posts, [])

    def test_simultaneous_requests_do_not_run_two_acquisition_searches(self):
        entered_impl = threading.Event()
        release_impl = threading.Event()
        calls = []

        def slow_impl(*args):
            calls.append(args)
            entered_impl.set()
            if not release_impl.wait(timeout=3):
                raise AssertionError("test did not release first acquisition")
            return json.dumps({"ok": True, "status": "queued"})

        self.ns["_discovery_acquire_album_impl"] = slow_impl
        first_result = []
        first = threading.Thread(target=lambda: first_result.append(
            self.ns["discovery_acquire_album"]("Artist", "Album")
        ))
        first.start()
        self.assertTrue(entered_impl.wait(timeout=2))
        second_result = self.ns["discovery_acquire_album"]("Artist", "Album")
        release_impl.set()
        first.join(timeout=3)

        self.assertFalse(first.is_alive())
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(second_result)["status"], "already_in_progress")
        self.assertEqual(json.loads(first_result[0])["status"], "queued")

    def test_stale_downloading_job_recovers_watcher_without_requeueing(self):
        self.ns["jobs"].append({
            "artist": "Artist",
            "album": "Album",
            "artist_key": "artist",
            "album_key": "album",
            "status": "downloading",
            "candidate": {"username": "peer", "files": [{"filename": "Album/01.flac"}]},
            "settings": {"slskd_downloads_path": "/downloads"},
        })
        impl_calls = []
        self.ns["_discovery_acquire_album_impl"] = lambda *args: impl_calls.append(args)

        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

        self.assertEqual(result["status"], "recovery_started")
        self.assertEqual(impl_calls, [])
        self.assertIn(("artist", "album"), self.ns["_DISCOVERY_IMPORT_ACTIVE"])


if __name__ == "__main__":
    unittest.main()
