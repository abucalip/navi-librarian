"""Direct-import regression tests for acquisition watcher lifecycle behavior."""
import tempfile
import unittest
from pathlib import Path

from acquisition_watcher import watch_and_import_album


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
        waiting = next(kwargs for args, kwargs in self.calls["status"]
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


if __name__ == "__main__":
    unittest.main()
