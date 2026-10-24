"""Direct-import regression tests for acquisition watcher lifecycle behavior."""
import tempfile
import unittest
from pathlib import Path

from acquisition.watcher import watch_and_import_album
from acquisition.watcher_startup import start_import_watcher


class FakeClock:
    def __init__(self): self.value = 0.0
    def monotonic(self): return self.value
    def time(self): return 123.0
    def sleep(self, seconds): self.value += seconds


class AcquisitionWatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = FakeClock()
        self.calls = {"status": [], "imports": [], "transfers": []}
        self.dismissed = False
        self.services = {
            "music_dir": self.root / "music",
            "reconcile_interrupted_import": lambda *_: False,
            "slskd_config": lambda: ("http://slskd", "secret", {}),
            "settings_defaults": {"slskd_downloads_path": str(self.root / "downloads")},
            "is_dismissed": lambda *_: self.dismissed,
            "skip_requested": lambda *_: False,
            "switch_to_next_source": lambda *args: None,
            "locate_completed_album": lambda *_: None,
            "import_completed_source": lambda *args: self.calls["imports"].append(args) or "imported",
            "download_transfer_files": lambda *args: self.calls["transfers"],
            "update_status": lambda *args, **kwargs: self.calls["status"].append((args, kwargs)),
            "inspect_completed_album": lambda *_: {"path": None, "diagnostics": {"reason": "not_found"}},
            "clock": self.clock,
        }
        self.candidate = {
            "username": "peer", "folder": "Artist/Album",
            "files": [{"filename": "Artist/Album/01.flac", "size": 4}],
            "quality_summary": ["flac_cd"],
        }

    def run_watcher(self):
        return watch_and_import_album("Artist", "Album", dict(self.candidate), {}, services=self.services)

    def test_failed_track_is_requeued_alone_without_source_switch(self):
        self.candidate["files"] = [
            {"filename": "Artist/Album/01.flac", "size": 4},
            {"filename": "Artist/Album/02.flac", "size": 4},
        ]
        self.candidate["fallback_candidates"] = [{"username": "other"}]
        self.calls["transfers"][:] = [
            {"filename": "Artist/Album/01.flac", "state": "Succeeded", "bytesTransferred": 4},
            {"filename": "Artist/Album/02.flac", "state": "Completed, Errored"},
        ]
        queued, switched = [], []
        self.services["queue_files"] = lambda *args: queued.append(args)
        self.services["switch_to_next_source"] = lambda *a: switched.append(a)
        self.services["is_dismissed"] = lambda *_: self.clock.value >= 400
        self.run_watcher()
        self.assertEqual(switched, [])
        self.assertEqual(len(queued), 3)
        self.assertEqual([f["filename"] for f in queued[0][3]], ["Artist/Album/02.flac"])
        self.assertFalse(any(a[2] == "download_failed" for a, _ in self.calls["status"]))

    def test_failed_track_gives_up_after_retries_and_grace(self):
        self.calls["transfers"].append({"filename": "Artist/Album/01.flac", "state": "Errored"})
        self.services["queue_files"] = lambda *args: None
        self.run_watcher()
        self.assertTrue(any(a[2] == "download_failed" for a, _ in self.calls["status"]))

    def test_retried_track_not_masked_by_stale_errored_record(self):
        self.calls["transfers"][:] = [
            {"filename": "Artist/Album/01.flac", "state": "Completed, Errored"},
            {"filename": "Artist/Album/01.flac", "state": "InProgress", "bytesTransferred": 1},
        ]
        self.services["queue_files"] = lambda *args: self.fail("should not requeue")
        self.services["is_dismissed"] = lambda *_: self.clock.value >= 10
        self.run_watcher()
        self.assertFalse(any(a[2] == "download_failed" for a, _ in self.calls["status"]))

    def test_dismissal_stops_before_transfer_poll_or_import(self):
        self.dismissed = True
        self.run_watcher()
        self.assertEqual(self.calls["transfers"], [])
        self.assertEqual(self.calls["imports"], [])
        self.assertEqual(self.calls["status"], [])

    def test_successful_interrupted_import_reconciliation_stops_watcher(self):
        self.services["reconcile_interrupted_import"] = lambda *_: True
        self.run_watcher()
        self.assertEqual(self.calls["transfers"], [])
        self.assertEqual(self.calls["imports"], [])

    def test_completed_transfer_without_verified_folder_waits_without_importing(self):
        self.calls["transfers"].append({
            "filename": "Artist/Album/01.flac", "state": "Succeeded", "bytesTransferred": "4",
        })
        self.services["is_dismissed"] = lambda *_: self.clock.value >= 2
        self.run_watcher()
        self.assertEqual(self.calls["imports"], [])
        self.assertTrue(any(args[2] == "download_complete_waiting_for_folder"
                            for args, _kwargs in self.calls["status"]))
        waiting = next(args[3] for args, _kwargs in self.calls["status"]
                       if args[2] == "download_complete_waiting_for_folder")
        self.assertEqual(waiting["downloads_path"], str(self.root / "downloads"))
        self.assertEqual(waiting["expected_files"], 1)
        self.assertEqual(waiting["matched_transfer_records"], 1)

    def test_only_verified_folder_is_passed_to_safe_import_coordinator(self):
        verified = self.root / "downloads" / "verified-album"
        self.services["locate_completed_album"] = lambda *_: verified
        self.run_watcher()
        self.assertEqual(len(self.calls["imports"]), 1)
        self.assertEqual(self.calls["imports"][0][2], verified)



class FakeThread:
    def __init__(self, *, target, args, name, daemon, fail=False):
        self.target, self.args, self.name, self.daemon, self.fail = target, args, name, daemon, fail
        self.started = False

    def start(self):
        if self.fail:
            raise RuntimeError("thread start failed")
        self.started = True


class AcquisitionWatcherStartupTests(unittest.TestCase):
    def setUp(self):
        import threading
        self.identity = ("artist", "album")
        self.active = set()
        self.transition_lock = threading.RLock()
        self.import_lock = threading.Lock()
        self.saved, self.status, self.threads = [], [], []

        def factory(**kwargs):
            thread = FakeThread(**kwargs)
            self.threads.append(thread)
            return thread

        self.services = {
            "music_key": lambda value: value.casefold(),
            "transition_lock": self.transition_lock,
            "import_lock": self.import_lock,
            "active": self.active,
            "is_dismissed": lambda *_: False,
            "save_job": lambda *args, **kwargs: self.saved.append((args, kwargs)),
            "update_status": lambda *args: self.status.append(args),
            "watcher_entry": lambda *_: None,
            "thread_factory": factory,
        }
        self.candidate = {
            "username": "peer", "folder": "Artist/Album",
            "files": [{"filename": "01.flac"}],
        }
        self.settings = {
            "slskd_downloads_path": "/downloads",
            "slskd_api_key": "secret", "api_key": "also-secret",
        }

    def start(self):
        return start_import_watcher(
            "Artist", "Album", self.candidate, self.settings, services=self.services
        )

    def test_reserves_persists_sanitized_settings_and_starts_thread(self):
        self.assertTrue(self.start())
        self.assertEqual(self.active, {self.identity})
        self.assertEqual(self.saved[0][0][2], "downloading")
        self.assertNotIn("slskd_api_key", self.saved[0][1]["settings"])
        self.assertNotIn("api_key", self.saved[0][1]["settings"])
        self.assertEqual(self.status[0][2], "downloading")
        self.assertTrue(self.threads[0].started)
        self.assertTrue(self.threads[0].daemon)

    def test_persists_request_metadata_and_defaults_to_empty(self):
        self.assertTrue(start_import_watcher(
            "Artist", "Album", self.candidate, self.settings, {"lens": "obsessions"},
            services=self.services,
        ))
        self.assertEqual(self.saved[0][0][3]["metadata"], {"lens": "obsessions"})
        self.assertEqual(self.status[0][3]["metadata"], {"lens": "obsessions"})
        self.active.clear()
        self.threads.clear()
        self.saved.clear()
        self.assertTrue(self.start())
        self.assertEqual(self.saved[0][0][3]["metadata"], {})

    def test_dismissed_job_does_not_reserve_or_start(self):
        self.services["is_dismissed"] = lambda *_: True
        self.assertFalse(self.start())
        self.assertEqual(self.active, set())
        self.assertEqual(self.saved, [])
        self.assertEqual(self.threads, [])

    def test_duplicate_start_does_not_overwrite_persisted_state(self):
        self.active.add(self.identity)
        self.assertFalse(self.start())
        self.assertEqual(self.saved, [])
        self.assertEqual(self.threads, [])

    def test_persistence_failure_releases_reservation_and_does_not_start_thread(self):
        self.services["save_job"] = lambda *args, **kwargs: (_ for _ in ()).throw(OSError("db down"))
        with self.assertRaises(OSError):
            self.start()
        self.assertEqual(self.active, set())
        self.assertEqual(self.threads, [])

    def test_thread_start_failure_releases_reservation_and_records_monitor_error(self):
        self.services["thread_factory"] = lambda **kwargs: FakeThread(**kwargs, fail=True)
        self.assertFalse(self.start())
        self.assertEqual(self.active, set())
        self.assertEqual(self.status[-1][2], "monitor_error")


    def test_concurrent_duplicate_start_reserves_and_starts_exactly_one_watcher(self):
        import threading

        gate = threading.Barrier(3)
        results = []
        failures = []

        def start_concurrently():
            try:
                gate.wait(timeout=3)
                results.append(self.start())
            except BaseException as exc:
                failures.append(exc)

        threads = [threading.Thread(target=start_concurrently) for _ in range(2)]
        for thread in threads:
            thread.start()
        gate.wait(timeout=3)
        for thread in threads:
            thread.join(timeout=3)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        self.assertCountEqual(results, [True, False])
        self.assertEqual(self.active, {self.identity})
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(len(self.threads), 1)
        self.assertTrue(self.threads[0].started)


if __name__ == "__main__":
    unittest.main()
