"""Regression tests for acquisition safety and legacy lifecycle integration.

Behavior is tested through the production coordinator, orchestration guards,
and import-completion service with injected state and I/O dependencies.
"""
import json
import tempfile
import threading
import unittest
from pathlib import Path

import acquisition_lifecycle as _acquisition_lifecycle
import acquisition_orchestration as _acquisition_orchestration
from acquisition_request_coordinator import acquire_album_request as _module_acquire_album_request
from acquisition_import_service import import_completed_source_locked

def load_helpers():
    """Build isolated state/dependency fixtures without parsing legacy source."""
    namespace = {
        "_acquisition_lifecycle": _acquisition_lifecycle,
        "_acquire_album_request": _module_acquire_album_request,
        "_DISCOVERY_IMPORT_TRANSITION_LOCK": threading.RLock(),
        "_DISCOVERY_IMPORT_LOCK": threading.Lock(),
        "_DISCOVERY_IMPORT_ACTIVE": set(),
        "_DISCOVERY_ACQUIRE_ACTIVE": set(),
        "jobs": [],
        "_discovery_reactivate_dismissed_acquisition": lambda *_args, **_kwargs: False,
        "_discovery_safe_folder_name": lambda value: str(value).replace("/", "_"),
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
    return namespace

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
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            music = root / "music"
            music.mkdir()
            source = root / "downloaded-album"
            source.mkdir()
            result = _acquisition_orchestration.import_source_unless_dismissed(
                "Artist", "Album",
                transition_lock=self.ns["_DISCOVERY_IMPORT_TRANSITION_LOCK"],
                is_dismissed=self.ns["_discovery_is_dismissed"],
                import_source=lambda: import_completed_source_locked(
                    "Artist", "Album", source, music,
                    {"username": "peer", "files": [{"filename": "Album/01.flac", "size": 4}]},
                    safe_folder_name=self.ns["_discovery_safe_folder_name"],
                    update_status=lambda *args, **kwargs: (
                        status_calls.append(args) or False
                    ),
                    import_matched_album_files=lambda *args, **kwargs: import_calls.append(args),
                    now=lambda: 123.0,
                ),
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
