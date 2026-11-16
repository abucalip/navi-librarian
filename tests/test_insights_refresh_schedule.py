"""Insights refresh cadence and stop handling (efficiency R5). No real provider or Navidrome call is made."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

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


class Schedule(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lib = Lib(tmp.name)
        self.store_path = self.lib.DATA_DIR / STORE_FILE
        ensure_store(self.store_path)

    def stored(self):
        db = open_store(self.store_path)
        self.addCleanup(db.close)
        return db

    def test_lens_off_opens_no_store(self):
        fresh = tempfile.TemporaryDirectory()
        self.addCleanup(fresh.cleanup)
        lib = Lib(fresh.name)
        self.assertEqual(ir._seconds_until_due(lib, NOW, {LENSES_ENV: ""}), 0.0)
        self.assertFalse((Path(fresh.name) / STORE_FILE).exists())

    def test_never_refreshed_is_due(self):
        self.assertEqual(ir._seconds_until_due(self.lib, NOW, GEMS_ENV), 0.0)

    def test_recent_refresh_waits_the_rest_of_the_window(self):
        ir._record_run(self.lib, NOW)
        self.assertEqual(ir._seconds_until_due(self.lib, NOW + 100, GEMS_ENV), CHECK - 100)

    def test_refresh_at_the_window_edge_is_due(self):
        ir._record_run(self.lib, NOW)
        self.assertEqual(ir._seconds_until_due(self.lib, NOW + CHECK, GEMS_ENV), 0.0)

    def test_stored_time_ahead_of_the_clock_is_due_not_frozen(self):
        ir._record_run(self.lib, NOW + 5000)
        self.assertEqual(ir._seconds_until_due(self.lib, NOW, GEMS_ENV), 0.0)

    def test_unreadable_stored_time_is_due(self):
        db = self.stored()
        db.execute("INSERT INTO meta (key, value) VALUES (?, 'not a time')", (ir.LAST_RUN_KEY,))
        db.commit()
        self.assertEqual(ir._seconds_until_due(self.lib, NOW, GEMS_ENV), 0.0)

    def test_record_overwrites_the_previous_time(self):
        ir._record_run(self.lib, NOW)
        ir._record_run(self.lib, NOW + 10)
        rows = self.stored().execute("SELECT value FROM meta WHERE key = ?", (ir.LAST_RUN_KEY,)).fetchall()
        self.assertEqual([float(r["value"]) for r in rows], [NOW + 10])


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


class Loop(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lib = Lib(tmp.name)
        ensure_store(self.lib.DATA_DIR / STORE_FILE)

    def run_loop(self, stop):
        thread = threading.Thread(target=ir._loop, args=(self.lib, stop), daemon=True)
        thread.start()
        return thread

    def test_stop_ends_the_loop_while_it_waits(self):
        entered, stop = threading.Event(), threading.Event()

        def lens_off(environ=None):
            entered.set()
            return set()

        with mock.patch.object(ir, "enabled_lenses", side_effect=lens_off):
            thread = self.run_loop(stop)
            self.assertTrue(entered.wait(2))
            stop.set()
            thread.join(2)
        # With time.sleep(CHECK) this join would time out after 2 s.
        self.assertFalse(thread.is_alive())

    def test_run_cut_short_by_shutdown_is_not_recorded(self):
        stop = threading.Event()

        def cut_short(librarian, environ=None, stop=None):
            stop.set()
            return {}

        with mock.patch.object(ir, "enabled_lenses", return_value={GEMS_KIND}), \
                mock.patch.object(ir, "refresh_once", side_effect=cut_short):
            self.run_loop(stop).join(2)
        self.assertEqual(ir._seconds_until_due(self.lib, time.time(), GEMS_ENV), 0.0)
        rows = open_store(self.lib.DATA_DIR / STORE_FILE).execute(
            "SELECT 1 FROM meta WHERE key = ?", (ir.LAST_RUN_KEY,)).fetchall()
        self.assertEqual(rows, [])

    def test_completed_run_is_recorded_and_the_next_start_waits(self):
        stop = threading.Event()

        def done(librarian, environ=None, stop=None):
            return {"forgotten_gem": "succeeded"}

        with mock.patch.object(ir, "enabled_lenses", return_value={GEMS_KIND}), \
                mock.patch.object(ir, "refresh_once", side_effect=done):
            thread = self.run_loop(stop)
            deadline = time.time() + 5
            while time.time() < deadline and ir._seconds_until_due(self.lib, time.time(), GEMS_ENV) == 0.0:
                time.sleep(0.02)
            stop.set()
            thread.join(2)
        self.assertGreater(ir._seconds_until_due(self.lib, time.time(), GEMS_ENV), 0.0)


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
