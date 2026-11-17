"""The worker's discovery list and lens list entries (efficiency W3, app/services/discovery_schedule.py).

Cadence, due rules, the worker wiring, and that web startup starts no list refresh loop. No provider,
Navidrome or real refresh runs.
"""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app.worker as worker
from app import worker_schedule
from app.services import discovery_schedule
from discovery import lens_service

HOUR = 3600.0


class Entries(unittest.TestCase):
    def setUp(self):
        self.lib = SimpleNamespace()
        self.entries = {e.name: e for e in discovery_schedule.entries(self.lib)}

    def test_two_hourly_entries_in_a_fixed_order(self):
        self.assertEqual([e.name for e in discovery_schedule.entries(self.lib)], ["discovery_lists", "lens_lists"])
        for entry in self.entries.values():
            self.assertTrue(entry.due(1000.0, None))                  # first start after upgrade: due at once
            self.assertFalse(entry.due(1000.0 + HOUR - 1, 1000.0))    # a restart inside the hour waits
            self.assertTrue(entry.due(1000.0 + HOUR, 1000.0))

    def test_the_discovery_entry_runs_one_stale_list_pass(self):
        with mock.patch.object(discovery_schedule, "refresh_stale_lists_once") as once:
            self.entries["discovery_lists"].run()
        once.assert_called_once_with(self.lib)

    def test_the_lens_entry_refreshes_only_when_due(self):
        with mock.patch.object(lens_service, "_due", return_value=False), \
                mock.patch.object(lens_service, "refresh_exclusive") as refresh:
            self.entries["lens_lists"].run()
        refresh.assert_not_called()
        with mock.patch.object(lens_service, "_due", return_value=True), \
                mock.patch.object(lens_service, "refresh_exclusive", return_value={"ok": True}) as refresh:
            self.assertEqual(self.entries["lens_lists"].run(), {"ok": True})
        refresh.assert_called_once_with(self.lib)

    def test_a_failing_lens_pass_is_logged_by_error_type_only(self):
        with mock.patch.object(lens_service, "_due", side_effect=ValueError("http://private.example")), \
                self.assertLogs(discovery_schedule.logger, "ERROR") as logs:
            self.assertIsNone(self.entries["lens_lists"].run())
        self.assertIn("ValueError", logs.output[0])
        self.assertNotIn("private", logs.output[0])

    def test_a_failing_discovery_pass_is_logged_by_error_type_only(self):
        lib = SimpleNamespace(_discovery_settings_read=mock.Mock(side_effect=OSError("/private/path")))
        with self.assertLogs(discovery_schedule.logger, "ERROR") as logs:
            self.assertIsNone(discovery_schedule.refresh_stale_lists_once(lib))
        self.assertIn("OSError", logs.output[0])
        self.assertNotIn("private", logs.output[0])

    def test_a_list_failure_is_logged_and_the_others_still_refresh(self):
        def refresh_one(name):
            if name == "classics":
                raise RuntimeError("secret")
            return {"ok": True}

        lib = SimpleNamespace(_discovery_settings_read=lambda: {}, _discovery_read_list=lambda name: None,
                              _discovery_scheduler_refresh_one=refresh_one)
        with self.assertLogs(discovery_schedule.logger, "WARNING") as logs:
            outcomes = discovery_schedule.refresh_stale_lists_once(lib)
        self.assertEqual([o["status"] for o in outcomes],
                         ["refreshed", "refresh_failed", "refreshed", "refreshed", "refreshed"])
        self.assertEqual(len(logs.output), 1)
        self.assertIn("classics (RuntimeError)", logs.output[0])


class WorkerWiring(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        from discovery import refresh_guard
        self.addCleanup(refresh_guard.set_process, "web")

    def test_the_worker_runs_the_discovery_entries_on_their_own_schedule_thread(self):
        stop = threading.Event()
        stop.set()
        with mock.patch.object(worker.worker_schedule, "start") as start, \
                mock.patch.object(worker.library_enrich, "run_forever"):
            start.return_value.is_alive.return_value = False
            self.assertEqual(worker.main(librarian=SimpleNamespace(DATA_DIR=self.dir), stop=stop), 0)
        names = [call.kwargs.get("name", "worker-schedule") for call in start.call_args_list]
        self.assertEqual(names, ["worker-schedule", discovery_schedule.THREAD_NAME])
        discovery_entries = start.call_args_list[1].args[0]
        self.assertEqual([e.name for e in discovery_entries], ["discovery_lists", "lens_lists"])
        main_entries = start.call_args_list[0].args[0]
        self.assertNotIn("discovery_lists", [e.name for e in main_entries])

    def test_the_start_helper_names_its_thread(self):
        stop = threading.Event()
        stop.set()
        thread = worker_schedule.start((), self.dir / "store.sqlite3", stop, name="named-schedule")
        thread.join(5)
        self.assertEqual(thread.name, "named-schedule")


class WebStartup(unittest.TestCase):
    def test_web_startup_starts_no_list_refresh_loop(self):
        import app.main as main
        from app.api import search

        lib = mock.Mock()
        before = {t.name for t in threading.enumerate()}
        with mock.patch.object(main, "get_librarian", return_value=lib), \
                mock.patch.object(main, "_bump_discogs_generation_at_startup") as bump, \
                mock.patch.object(search, "owned_view"):
            main._discovery_startup()
        bump.assert_called_once_with(lib)                      # the startup action stays in the web
        new = {t.name for t in threading.enumerate()} - before
        self.assertFalse(new & {"navidrome-discovery-scheduler", "navidrome-lens-lists"})
        lib._start_discovery_scheduler.assert_not_called()
        self.assertFalse(hasattr(main, "_start_discovery_background"))
        self.assertFalse(hasattr(main, "_discovery_scheduler_start_timer"))

    def test_a_failing_discogs_bump_does_not_stop_web_startup(self):
        import app.main as main
        from app.api import search

        with mock.patch.object(main, "get_librarian", return_value=mock.Mock()), \
                mock.patch.object(main, "_bump_discogs_generation_at_startup", side_effect=OSError("x")), \
                mock.patch.object(search, "owned_view") as warm:
            main._discovery_startup()
        warm.assert_called_once()


if __name__ == "__main__":
    unittest.main()
