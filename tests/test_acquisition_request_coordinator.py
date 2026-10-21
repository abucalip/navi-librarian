"""Direct-import tests for top-level acquisition request coordination."""
import json
import threading
import unittest
from types import SimpleNamespace

from acquisition.lifecycle import should_resume_monitor
from acquisition.request_coordinator import acquire_album_request


class AcquisitionRequestCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.transition_lock = threading.RLock()
        self.watcher_lock = threading.RLock()
        self.active_watchers = set()
        self.active_requests = set()
        self.jobs = []
        self.acquire_calls = []
        self.watcher_calls = []
        self.dismissed = False
        self.reactivation_result = True

    def start_watcher(self, artist, album, candidate, settings):
        self.watcher_calls.append((artist, album, candidate, settings))
        with self.watcher_lock:
            self.active_watchers.add((artist.casefold(), album.casefold()))

    def acquire_impl(self, *args):
        self.acquire_calls.append(args)
        return json.dumps({"ok": True, "status": "queued"})

    def call(self, artist="Artist", album="Album", metadata_json="{}", auto_queue=True, **overrides):
        return acquire_album_request(
            artist, album, metadata_json, auto_queue,
            **self._dependencies(overrides),
        )

    def _dependencies(self, overrides):
        # Keep each call's stateful dependencies bound to this fixture.
        return {
            "music_key": lambda value: value.casefold().strip(),
            "transition_lock": self.transition_lock,
            "watcher_lock": self.watcher_lock,
            "active_watchers": self.active_watchers,
            "active_requests": self.active_requests,
            "list_jobs": lambda: self.jobs,
            "is_dismissed": lambda *_args: self.dismissed,
            "reactivate": lambda *_args: self.reactivation_result,
            "start_watcher": self.start_watcher,
            "lifecycle": SimpleNamespace(should_resume_monitor=should_resume_monitor),
            "json_module": json,
            "acquire_impl": self.acquire_impl,
        } | overrides

    def test_blank_artist_or_album_refuses_without_acquisition(self):
        result = json.loads(self.call(" ", "Album"))
        self.assertEqual(result, {"ok": False, "error": "Artist and album are required."})
        self.assertEqual(self.acquire_calls, [])

    def test_failed_dismissed_reactivation_refuses_new_search(self):
        self.dismissed = True
        self.reactivation_result = False
        result = json.loads(self.call(metadata_json='{"mbid":"release-id"}'))
        self.assertEqual(result["status"], "dismissed")
        self.assertFalse(result["ok"])
        self.assertEqual(self.acquire_calls, [])

    def test_incomplete_saved_source_refuses_recovery_without_requeue(self):
        self.jobs.append({
            "artist": "Artist", "album": "Album",
            "artist_key": "artist", "album_key": "album",
            "status": "downloading",
            "candidate": {"username": "peer", "files": []},
            "settings": {},
        })
        result = json.loads(self.call())
        self.assertEqual(result["status"], "recovery_unavailable")
        self.assertEqual(self.watcher_calls, [])
        self.assertEqual(self.acquire_calls, [])

    def test_valid_saved_source_resumes_watcher_without_requeue(self):
        candidate = {"username": "peer", "files": [{"filename": "Album/01.flac"}]}
        settings = {"slskd_downloads_path": "/downloads"}
        self.jobs.append({
            "artist": "Artist", "album": "Album",
            "artist_key": "artist", "album_key": "album",
            "status": "downloading", "candidate": candidate, "settings": settings,
        })
        result = json.loads(self.call())
        self.assertEqual(result["status"], "recovery_started")
        self.assertEqual(self.watcher_calls, [("Artist", "Album", candidate, settings)])
        self.assertEqual(self.acquire_calls, [])

    def test_new_request_releases_reservation_after_success(self):
        result = json.loads(self.call(metadata_json='{"mbid":"id"}', auto_queue=False))
        self.assertEqual(result["status"], "queued")
        self.assertEqual(self.acquire_calls, [("Artist", "Album", '{"mbid":"id"}', False)])
        self.assertEqual(self.active_requests, set())

    def test_new_request_releases_reservation_after_exception(self):
        def fail(*_args):
            raise RuntimeError("acquisition failed")
        with self.assertRaisesRegex(RuntimeError, "acquisition failed"):
            self.call(acquire_impl=fail)
        self.assertEqual(self.active_requests, set())

    def test_simultaneous_requests_do_not_run_two_acquisition_searches(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []

        def slow_impl(*args):
            calls.append(args)
            entered.set()
            if not release.wait(timeout=3):
                raise AssertionError("test did not release first acquisition")
            return json.dumps({"ok": True, "status": "queued"})

        first_result = []
        first = threading.Thread(target=lambda: first_result.append(
            self.call(acquire_impl=slow_impl)
        ))
        first.start()
        self.assertTrue(entered.wait(timeout=2))
        second_result = json.loads(self.call(acquire_impl=slow_impl))
        release.set()
        first.join(timeout=3)

        self.assertFalse(first.is_alive())
        self.assertEqual(len(calls), 1)
        self.assertEqual(second_result["status"], "already_in_progress")
        self.assertEqual(json.loads(first_result[0])["status"], "queued")
        self.assertEqual(self.active_requests, set())


if __name__ == "__main__":
    unittest.main()
