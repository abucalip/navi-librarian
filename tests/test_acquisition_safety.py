"""Regression tests for acquisition safety and legacy lifecycle integration.

Pure discovery and slskd policies are covered through direct-import tests in their
own modules. The remaining AST harness is limited to legacy orchestration that
still needs the monolithic adapter's shared state and injected I/O stubs.
"""
import ast
import json
import tempfile
import threading
import unicodedata
import acquisition_lifecycle as _acquisition_lifecycle
import acquisition_orchestration as _acquisition_orchestration
from acquisition_candidate_start import candidate_start_state as _module_candidate_start_state
from slskd_search import (
    album_path_match as _slskd_album_path_match_impl,
    search_queries as _slskd_search_queries_impl,
    response_items as _slskd_search_response_items_impl,
    path_match_diagnostics as _slskd_path_match_diagnostics_impl,
    extract_candidates as _slskd_extract_candidates_impl,
    track_identity as _slskd_track_identity_impl,
)
from slskd_quality import quality_tier as _slskd_quality_tier_impl
from acquisition_request_coordinator import acquire_album_request as _module_acquire_album_request

from acquisition_completion import (
    filename_key as _module_filename_key,
    match_completed_album_files as _module_match_completed_album_files,
)
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


class FakeHTTPError(Exception):
    pass


def load_helpers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "_slskd_candidate_start_state",
        "_discovery_import_completed_source",
        "_discovery_import_completed_source_locked",
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
        "_acquisition_lifecycle": _acquisition_lifecycle,
        "_acquisition_orchestration": _acquisition_orchestration,
        "_acquire_album_request": _module_acquire_album_request,
        "_module_candidate_start_state": _module_candidate_start_state,
        "unicodedata": unicodedata,
        "_discovery_filename_key": _module_filename_key,
        "_discovery_match_completed_album_files": _module_match_completed_album_files,
        "json": json,
        "threading": threading,
        "_DISCOVERY_IMPORT_TRANSITION_LOCK": threading.RLock(),
        "_DISCOVERY_IMPORT_LOCK": threading.Lock(),
        "_DISCOVERY_IMPORT_ACTIVE": set(),
        "_DISCOVERY_ACQUIRE_ACTIVE": set(),
        "jobs": [],
        "time": SimpleNamespace(monotonic=lambda: 0, sleep=lambda _seconds: None, time=lambda: 123.0),
        "MUSIC_DIR": Path("/music"),
        "httpx": SimpleNamespace(
            HTTPError=FakeHTTPError,
            delete=lambda *args, **kwargs: SimpleNamespace(status_code=204),
            post=lambda *args, **kwargs: SimpleNamespace(
                status_code=200, raise_for_status=lambda: None
            ),
        ),
        "_slskd_download_transfer_files": lambda *_args, **_kwargs: [],
        "_slskd_config": lambda: ("http://slskd", None, {}),
        "_DISCOVERY_SETTINGS_DEFAULTS": {"quality_priority": ["mp3_320", "flac_cd"]},
        "_discovery_expected_track_count": lambda _metadata: None,
        "_discovery_cancel_and_clean_source": lambda *_args, **_kwargs: True,
        "_discovery_switch_to_next_source_locked": lambda *_args, **_kwargs: None,
        "_discovery_reactivate_dismissed_acquisition": lambda *_args, **_kwargs: False,
        "_discovery_safe_folder_name": lambda value: str(value).replace("/", "_"),
        "_discovery_import_matched_album_files": lambda *_args, **_kwargs: None,
        "saved_jobs": [],
        "status_updates": [],
        "_discovery_save_acquisition_job": lambda *args, **kwargs: namespace["saved_jobs"].append((args, kwargs)),
        "_discovery_update_acquisition_status": lambda *args, **kwargs: (namespace["status_updates"].append((args, kwargs)) or True),
        "_slskd_candidate_start_state": lambda *args, **kwargs: True,
        "_music_key": lambda value: str(value or "").strip().casefold(),
    }
    # Pure slskd helpers use their extracted production modules; only lifecycle
    # and orchestration functions remain compiled from the legacy adapter.
    namespace["_slskd_album_path_match"] = _slskd_album_path_match_impl
    namespace["_slskd_search_queries"] = _slskd_search_queries_impl
    namespace["_slskd_search_response_items"] = _slskd_search_response_items_impl
    namespace["_slskd_quality_tier"] = _slskd_quality_tier_impl
    namespace["_slskd_track_identity"] = lambda filename: _slskd_track_identity_impl(
        filename, namespace["_music_key"]
    )
    namespace["_slskd_path_match_diagnostics"] = lambda payload, artist, album, limit=10: (
        _slskd_path_match_diagnostics_impl(
            payload, artist, album, limit,
            music_key=namespace["_music_key"],
            album_path_match=namespace["_slskd_album_path_match"],
        )
    )
    namespace["_slskd_extract_candidates"] = lambda payload, artist, album, priority, expected_track_count=None: (
        _slskd_extract_candidates_impl(
            payload, artist, album, priority, expected_track_count,
            music_key=namespace["_music_key"],
            album_path_match=namespace["_slskd_album_path_match"],
            quality_tier=namespace["_slskd_quality_tier"],
            track_identity=namespace["_slskd_track_identity"],
        )
    )
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


class SlskdSearchQueryTests(unittest.TestCase):

class AcquisitionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_helpers()

    def acquire(self, artist, album, metadata_json="{}", auto_queue=True):
        """Exercise the real request coordinator with the lifecycle's injected state."""
        return _module_acquire_album_request(
            artist, album, metadata_json, auto_queue,
            music_key=self.ns["_music_key"],
            transition_lock=self.ns["_DISCOVERY_IMPORT_TRANSITION_LOCK"],
            watcher_lock=self.ns["_DISCOVERY_IMPORT_LOCK"],
            active_watchers=self.ns["_DISCOVERY_IMPORT_ACTIVE"],
            active_requests=self.ns["_DISCOVERY_ACQUIRE_ACTIVE"],
            list_jobs=self.ns["_discovery_list_acquisition_jobs"],
            is_dismissed=self.ns["_discovery_is_dismissed"],
            reactivate=self.ns["_discovery_reactivate_dismissed_acquisition"],
            start_watcher=self.ns["_discovery_start_import_watcher"],
            lifecycle=_acquisition_lifecycle,
            json_module=json,
            acquire_impl=self.ns["_discovery_acquire_album_impl"],
        )

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
            self.acquire("Artist", "Album")
        ))
        first.start()
        self.assertTrue(entered_impl.wait(timeout=2))
        second_result = self.acquire("Artist", "Album")
        release_impl.set()
        first.join(timeout=3)

        self.assertFalse(first.is_alive())
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(second_result)["status"], "already_in_progress")
        self.assertEqual(json.loads(first_result[0])["status"], "queued")




    def test_import_does_not_move_files_if_importing_status_cannot_be_persisted(self):
        status_calls = []
        import_calls = []
        self.ns["_discovery_is_dismissed"] = lambda artist, album: False
        self.ns["_discovery_update_acquisition_status"] = lambda *args, **kwargs: (
            status_calls.append(args) or False
        )
        self.ns["_discovery_import_matched_album_files"] = lambda *args, **kwargs: import_calls.append(args)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            music = root / "music"
            music.mkdir()
            source = root / "downloaded-album"
            source.mkdir()
            result = self.ns["_discovery_import_completed_source"](
                "Artist", "Album", source, music,
                {"username": "peer", "files": [{"filename": "Album/01.flac", "size": 4}]},
            )

        self.assertEqual(result, "failed")
        self.assertEqual(import_calls, [])
        self.assertEqual(status_calls[0][2], "importing")

    def test_incomplete_saved_download_details_do_not_start_or_requeue(self):
        self.ns["jobs"].append({
            "artist": "Artist",
            "album": "Album",
            "artist_key": "artist",
            "album_key": "album",
            "status": "downloading",
            "candidate": {"username": "peer", "files": []},
            "settings": {},
        })
        impl_calls = []
        watcher_calls = []
        self.ns["_discovery_acquire_album_impl"] = lambda *args: impl_calls.append(args)
        self.ns["_discovery_start_import_watcher"] = lambda *args: watcher_calls.append(args)

        result = json.loads(self.acquire("Artist", "Album"))

        self.assertEqual(result["status"], "recovery_unavailable")
        self.assertEqual(impl_calls, [])
        self.assertEqual(watcher_calls, [])

    def test_explicit_get_reactivates_safely_dismissed_job(self):
        job = {
            "artist": "Artist",
            "album": "Album",
            "artist_key": "artist",
            "album_key": "album",
            "status": "dismissed",
            "candidate": {"username": "old-peer", "files": [{"filename": "old/01.flac"}]},
            "settings": {"slskd_downloads_path": "/old"},
        }
        self.ns["jobs"].append(job)
        calls = []

        def reactivate(artist, album, metadata):
            calls.append((artist, album, metadata))
            job.update(status="retry_requested", candidate={}, settings={})
            return True

        self.ns["_discovery_reactivate_dismissed_acquisition"] = reactivate
        self.ns["_discovery_acquire_album_impl"] = lambda *args: json.dumps({
            "ok": True, "status": "implementation_called"
        })
        result = json.loads(self.acquire(
            "Artist", "Album", json.dumps({"mbid": "release-id"})
        ))

        self.assertEqual(result["status"], "implementation_called")
        self.assertEqual(calls, [("Artist", "Album", {"mbid": "release-id"})])
        self.assertEqual(job["status"], "retry_requested")
        self.assertEqual(job["candidate"], {})
        self.assertEqual(job["settings"], {})

    def test_dismissed_job_stays_blocked_if_reactivation_fails(self):
        self.ns["jobs"].append({
            "artist": "Artist", "album": "Album",
            "artist_key": "artist", "album_key": "album",
            "status": "dismissed",
        })
        self.ns["_discovery_reactivate_dismissed_acquisition"] = lambda *_args, **_kwargs: False
        result = json.loads(self.acquire("Artist", "Album"))

        self.assertEqual(result["status"], "dismissed")
        self.assertEqual(result["ok"], False)

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

        result = json.loads(self.acquire("Artist", "Album"))

        self.assertEqual(result["status"], "recovery_started")
        self.assertEqual(impl_calls, [])
        self.assertIn(("artist", "album"), self.ns["_DISCOVERY_IMPORT_ACTIVE"])


if __name__ == "__main__":
    unittest.main()
