"""Insights refresh cadence and stop handling (efficiency R5, scheduled by W1). No real provider or Navidrome call is made."""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import app.worker as worker
from app import worker_schedule
from app.api.insights import LENSES_ENV, STORE_FILE
from app.services import insights_refresh as ir
from intelligence.insights.forgotten_gems import CARD_KIND as GEMS_KIND
from intelligence.insights.provider_runtime import BudgetSpent, CountingGet
from intelligence.store import ensure_store, open_store

NOW = 1_800_000_000.0
CHECK = ir.CHECK_SECONDS
BLIND_ENV = {LENSES_ENV: "blind_spot"}
GEMS_ENV = {LENSES_ENV: "forgotten_gem"}


class Lib:
    """Navidrome stand-in: one owned artist with one album, so a provider tick has requests to make."""

    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)

    def api_call(self, method, **params):
        if method == "getArtists":
            return {"artists": {"index": [{"artist": [
                {"id": "ar1", "name": "A", "musicBrainzId": "11111111-1111-4111-8111-111111111111"}]}]}}
        if method == "getArtist":
            return {"artist": {"album": [{"id": "al1"}]}}
        return {"album": {"id": "al1", "name": "X", "artistId": "ar1", "artist": "A",
                          "musicBrainzId": "aaaaaaaa-0000-4000-8000-000000000001", "song": []}}

    def items(self, value):
        return value or []

    def _discovery_settings_read(self):
        return {}


class Resp:
    status_code = 404

    def json(self):
        return {}


class Due(unittest.TestCase):
    """``is_due`` is the scheduler's rule for this job: R5's window and edge cases, now with the last run passed in."""

    def test_lens_off_is_never_due(self):
        self.assertFalse(ir.is_due(NOW, None, {LENSES_ENV: ""}))

    def test_never_refreshed_is_due(self):
        self.assertTrue(ir.is_due(NOW, None, GEMS_ENV))

    def test_recent_refresh_waits_the_rest_of_the_window(self):
        self.assertFalse(ir.is_due(NOW + 100, NOW, GEMS_ENV))
        self.assertFalse(ir.is_due(NOW + CHECK - 1, NOW, GEMS_ENV))

    def test_refresh_at_the_window_edge_is_due(self):
        self.assertTrue(ir.is_due(NOW + CHECK, NOW, GEMS_ENV))

    def test_stored_time_ahead_of_the_clock_is_due_not_frozen(self):
        self.assertTrue(ir.is_due(NOW, NOW + 5000, GEMS_ENV))


class CountingStop(unittest.TestCase):
    def test_stop_refuses_the_request_before_it_is_made(self):
        calls = []
        get = CountingGet(lambda url, **kw: calls.append(url), budget=5, should_stop=lambda: True)
        with self.assertRaises(BudgetSpent):
            get("https://musicbrainz.org/ws/2/x")
        self.assertEqual(calls, [])
        self.assertEqual(get.used, 0)

    def test_without_stop_the_budget_is_unchanged(self):
        get = CountingGet(lambda url, **kw: "ok", budget=2)
        self.assertEqual(get("a"), "ok")
        self.assertEqual(get("b"), "ok")
        with self.assertRaises(BudgetSpent):
            get("c")
        self.assertEqual(get.used, 2)


class ScheduledRun(unittest.TestCase):
    """The worker's insights entry under the real scheduler (efficiency W1)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lib = Lib(tmp.name)
        self.path = self.lib.DATA_DIR / STORE_FILE
        ensure_store(self.path)
        self.stop = threading.Event()
        lenses = mock.patch.object(ir, "enabled_lenses", return_value={GEMS_KIND})
        lenses.start()
        self.addCleanup(lenses.stop)

    def scheduler(self, now):
        entries = [e for e in worker.schedule_entries(self.lib, self.stop) if e.name == "insights_refresh"]
        return worker_schedule.Scheduler(entries, self.path, clock=lambda: now)

    def stored(self):
        db = open_store(self.path)
        self.addCleanup(db.close)
        return worker_schedule.last_runs(db)

    def test_run_cut_short_by_shutdown_is_not_recorded(self):
        def cut_short(librarian, environ=None, stop=None):
            stop.set()
            return {}

        with mock.patch.object(ir, "refresh_once", side_effect=cut_short):
            self.assertEqual(self.scheduler(NOW).run_due(self.stop), [])
        self.assertEqual(self.stored(), {})

    def test_completed_run_is_recorded_and_the_next_start_waits(self):
        with mock.patch.object(ir, "refresh_once", return_value={"forgotten_gem": "succeeded"}) as refresh:
            self.assertEqual(self.scheduler(NOW).run_due(self.stop), ["insights_refresh"])
            self.assertEqual(self.scheduler(NOW + CHECK - 1).run_due(self.stop), [])   # restart inside the window
            self.assertEqual(self.scheduler(NOW + CHECK).run_due(self.stop), ["insights_refresh"])
        self.assertEqual(refresh.call_count, 2)
        self.assertEqual(self.stored(), {"insights_refresh": NOW + CHECK})

    def test_first_start_after_the_upgrade_honours_the_r5_time(self):
        db = open_store(self.path)
        with db:
            db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (ir.LAST_RUN_KEY, str(NOW)))
        db.close()
        with mock.patch.object(ir, "refresh_once") as refresh:
            self.assertEqual(self.scheduler(NOW + 100).run_due(self.stop), [])
        refresh.assert_not_called()

    def test_lens_off_runs_and_records_nothing(self):
        with mock.patch.object(ir, "enabled_lenses", return_value=set()), \
                mock.patch.object(ir, "refresh_once") as refresh:
            self.assertEqual(self.scheduler(NOW).run_due(self.stop), [])
        refresh.assert_not_called()
        self.assertEqual(self.stored(), {})


class ProviderStop(unittest.TestCase):
    def test_stop_during_a_provider_run_ends_it_before_the_next_request(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        lib = Lib(tmp.name)
        stop = threading.Event()
        seen = []

        def fake_get(url, **kwargs):
            seen.append(url)
            stop.set()          # shutdown arrives while the first provider request is in flight
            return Resp()

        with mock.patch.object(ir.httpx, "get", fake_get), mock.patch.object(ir.time, "sleep"):
            out = ir.refresh_once(lib, BLIND_ENV, stop=stop)

        self.assertEqual(out, {"provider_lenses": "succeeded"})
        self.assertEqual(len(seen), 1)
        running = open_store(lib.DATA_DIR / STORE_FILE).execute(
            "SELECT COUNT(*) FROM job_runs WHERE state = 'running'").fetchone()[0]
        self.assertEqual(running, 0)


if __name__ == "__main__":
    unittest.main()
