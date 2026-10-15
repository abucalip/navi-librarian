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
        "_slskd_album_path_match",
        "_slskd_search_queries",
        "_slskd_search_response_items",
        "_slskd_path_match_diagnostics",
        "_slskd_quality_tier",
        "_slskd_track_identity",
        "_slskd_extract_candidates",
        "_slskd_candidate_start_state",
        "_discovery_import_completed_source",
        "_discovery_import_completed_source_locked",
        "_discovery_acquire_album_impl",
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
    def test_acquisition_retries_broader_query_when_exact_search_has_no_payload(self):
        posted_queries = []
        posted_timeouts = []
        other_peer = {
            "username": "peer",
            "files": [{"filename": "Other Artist/Other Album/01 - Track.flac", "size": 1000}],
        }

        def fake_response(payload=None, status_code=200):
            return SimpleNamespace(
                status_code=status_code,
                json=lambda: payload,
                raise_for_status=lambda: None,
            )

        def fake_post(_url, headers=None, json=None, timeout=None):
            posted_queries.append(json["searchText"])
            posted_timeouts.append(json["searchTimeout"])
            return fake_response({})

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/responses"):
                return fake_response([])
            search_id = url.rsplit("/", 1)[-1]
            query_index = len(posted_queries) - 1
            state = {"isComplete": True, "responseCount": 0, "fileCount": 0}
            if query_index == 1:
                state = {
                    "isComplete": True,
                    "responseCount": 1,
                    "fileCount": 1,
                    "responses": [other_peer],
                }
            return fake_response(state)

        client = HELPERS["httpx"]
        original_post = client.post
        original_get = getattr(client, "get", None)
        original_status_error = getattr(client, "HTTPStatusError", None)
        client.post = fake_post
        client.get = fake_get
        client.HTTPStatusError = FakeHTTPError
        try:
            result = json.loads(HELPERS["_discovery_acquire_album_impl"](
                "Tinariwen", "Idrache (Traces of the Past)"
            ))
        finally:
            client.post = original_post
            if original_get is None:
                delattr(client, "get")
            else:
                client.get = original_get
            if original_status_error is None:
                delattr(client, "HTTPStatusError")
            else:
                client.HTTPStatusError = original_status_error

        self.assertEqual(posted_queries, [
            "Tinariwen Idrache (Traces of the Past)",
            "Tinariwen Idrache Traces of the Past",
        ])
        self.assertEqual(posted_timeouts, [15000, 6000])
        self.assertEqual(
            [item["query"] for item in result["search_queries_attempted"]],
            posted_queries,
        )
        self.assertEqual(result["search_queries_attempted"][0]["collected_peer_response_count"], 0)
        self.assertEqual(result["search_queries_attempted"][1]["collected_peer_response_count"], 1)
        self.assertIn("Queries tried: Tinariwen Idrache (Traces of the Past)", result["message"])
        self.assertIn("Tinariwen Idrache Traces of the Past", result["message"])


class AcquisitionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_helpers()

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

        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

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
        result = json.loads(self.ns["discovery_acquire_album"](
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
        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

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

        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

        self.assertEqual(result["status"], "recovery_started")
        self.assertEqual(impl_calls, [])
        self.assertIn(("artist", "album"), self.ns["_DISCOVERY_IMPORT_ACTIVE"])


if __name__ == "__main__":
    unittest.main()
