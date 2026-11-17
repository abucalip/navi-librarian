"""Table-driven worker scheduler (efficiency W1): due rules, restart persistence, stop and failure handling.

A fake clock drives every case; no provider, Navidrome or real job runs.
"""
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app.worker as worker
from app import worker_schedule as ws
from app.services import insights_refresh
from intelligence.store import ensure_store, open_store

HOUR = 3600.0


def local(*parts):
    """A local-time timestamp, so the daily cases hold on a UTC CI runner and on a laptop alike."""
    return datetime(*parts).timestamp()


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


class DueRules(unittest.TestCase):
    def test_interval(self):
        due = ws.interval(6 * HOUR)
        self.assertTrue(due(1000.0, None))
        self.assertFalse(due(1000.0 + 100, 1000.0))
        self.assertFalse(due(1000.0 + 6 * HOUR - 1, 1000.0))
        self.assertTrue(due(1000.0 + 6 * HOUR, 1000.0))      # the window edge is due
        self.assertTrue(due(1000.0, 1000.0 + 5000))         # a stored time ahead of the clock cannot freeze it

    def test_daily_compares_local_dates(self):
        due = ws.daily()
        self.assertTrue(due(local(2026, 11, 17, 9), None))
        self.assertFalse(due(local(2026, 11, 17, 23, 59), local(2026, 11, 17, 0, 1)))
        self.assertTrue(due(local(2026, 11, 18, 0, 1), local(2026, 11, 17, 23, 59)))   # just after midnight
        self.assertTrue(due(local(2026, 11, 17, 9), local(2026, 11, 18, 9)))           # clock stepped back


class Store(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "store.sqlite3"
        ensure_store(self.path)
        self.stop = threading.Event()
        self.calls = []

    def db(self):
        handle = open_store(self.path)
        self.addCleanup(handle.close)
        return handle

    def entry(self, name, due=None, run=None, legacy_key=None):
        def default_run():
            self.calls.append(name)
        return ws.Entry(name, due or ws.interval(HOUR), run or default_run, legacy_key)

    def scheduler(self, entries, now):
        return ws.Scheduler(entries, self.path, clock=Clock(now))


class Persistence(Store):
    def test_a_restart_inside_the_window_does_not_repeat_the_job(self):
        self.assertEqual(self.scheduler([self.entry("a")], 1000.0).run_due(self.stop), ["a"])
        restarted = self.scheduler([self.entry("a")], 1000.0 + HOUR - 1)
        self.assertEqual(restarted.run_due(self.stop), [])
        self.assertEqual(self.calls, ["a"])

    def test_a_restart_after_the_window_runs_the_job(self):
        self.scheduler([self.entry("a")], 1000.0).run_due(self.stop)
        self.assertEqual(self.scheduler([self.entry("a")], 1000.0 + HOUR).run_due(self.stop), ["a"])
        self.assertEqual(self.calls, ["a", "a"])

    def test_the_run_is_stored_under_its_schedule_key(self):
        self.scheduler([self.entry("a")], 1234.0).run_due(self.stop)
        self.assertEqual(ws.last_runs(self.db()), {"a": 1234.0})

    def test_the_legacy_key_is_read_when_the_schedule_key_is_missing(self):
        db = self.db()
        with db:
            db.execute("INSERT INTO meta (key, value) VALUES ('old.last_run_at', '1000.0')")
        entry = self.entry("a", legacy_key="old.last_run_at")
        self.assertEqual(self.scheduler([entry], 1000.0 + 100).run_due(self.stop), [])
        self.assertEqual(self.calls, [])

    def test_the_schedule_key_wins_over_the_legacy_key(self):
        db = self.db()
        with db:
            db.execute("INSERT INTO meta (key, value) VALUES ('old.last_run_at', '1.0')")
        ws.record_run(db, "a", 1000.0)
        entry = self.entry("a", legacy_key="old.last_run_at")
        self.assertEqual(self.scheduler([entry], 1000.0 + 100).run_due(self.stop), [])

    def test_an_unreadable_stored_time_counts_as_never_run(self):
        db = self.db()
        with db:
            db.execute("INSERT INTO meta (key, value) VALUES ('schedule:a', 'not a time')")
        self.assertEqual(self.scheduler([self.entry("a")], 1000.0).run_due(self.stop), ["a"])

    def test_a_failed_write_still_keeps_the_job_from_spinning(self):
        scheduler = self.scheduler([self.entry("a")], 1000.0)
        scheduler.run_due(self.stop)
        with mock.patch.object(ws, "record_run", side_effect=OSError("disk full")), \
                self.assertLogs(ws.logger, "ERROR") as logs:
            scheduler.clock.now += HOUR
            self.assertEqual(scheduler.run_due(self.stop), ["a"])
        self.assertIn("OSError", logs.output[0])
        self.assertEqual(scheduler.run_due(self.stop), [])


class Running(Store):
    def test_entries_run_one_at_a_time_in_order(self):
        names = ["first", "second", "third"]
        self.assertEqual(self.scheduler([self.entry(n) for n in names], 1000.0).run_due(self.stop), names)
        self.assertEqual(self.calls, names)

    def test_an_entry_that_is_not_due_is_skipped(self):
        entries = [self.entry("never", due=lambda now, last: False), self.entry("b")]
        self.assertEqual(self.scheduler(entries, 1000.0).run_due(self.stop), ["b"])
        self.assertNotIn("never", ws.last_runs(self.db()))

    def test_stop_set_by_one_job_starts_no_further_job_and_leaves_it_due(self):
        def first():
            self.calls.append("first")
            self.stop.set()
        self.scheduler([self.entry("first", run=first), self.entry("second")], 1000.0).run_due(self.stop)
        self.assertEqual(self.calls, ["first"])
        self.assertEqual(ws.last_runs(self.db()), {})        # cut short: neither is recorded

    def test_a_raising_job_is_logged_by_type_and_recorded_and_the_next_still_runs(self):
        def broken():
            raise ValueError("secret detail https://example.invalid/?token=x")
        scheduler = self.scheduler([self.entry("broken", run=broken), self.entry("b")], 1000.0)
        with self.assertLogs(ws.logger, "ERROR") as logs:
            self.assertEqual(scheduler.run_due(self.stop), ["broken", "b"])
        self.assertEqual(logs.output, ["ERROR:app.worker_schedule:Scheduled job broken failed (ValueError)"])
        self.assertEqual(ws.last_runs(self.db()), {"b": 1000.0, "broken": 1000.0})
        self.assertEqual(scheduler.run_due(self.stop), [])     # recorded, so it waits for its window

    def test_a_not_ready_run_is_not_recorded_and_waits_its_retry_delay(self):
        results = [ws.NOT_READY, ws.NOT_READY, {"done": 1}]
        entry = ws.Entry("p", ws.daily(), lambda: results.pop(0), retry_seconds=HOUR)
        scheduler = self.scheduler([entry], local(2026, 11, 17, 9))
        self.assertEqual(scheduler.run_due(self.stop), [])
        self.assertIsNone(ws.read_last_run(self.db(), entry))      # the day stays undone
        scheduler.clock.now += HOUR - 1
        self.assertEqual(scheduler.run_due(self.stop), [])          # inside the retry delay: not run
        self.assertEqual(len(results), 2)
        scheduler.clock.now += 1
        self.assertEqual(scheduler.run_due(self.stop), [])          # retried, still not ready
        scheduler.clock.now += HOUR
        self.assertEqual(scheduler.run_due(self.stop), ["p"])       # ready: recorded, done for the day
        scheduler.clock.now += HOUR
        self.assertEqual(scheduler.run_due(self.stop), [])

    def test_a_not_ready_entry_does_not_hold_up_the_next(self):
        entries = [ws.Entry("p", ws.daily(), lambda: ws.NOT_READY), self.entry("b")]
        self.assertEqual(self.scheduler(entries, 1000.0).run_due(self.stop), ["b"])

    def test_a_clock_stepped_back_does_not_freeze_the_retry(self):
        results = [ws.NOT_READY, None]
        entry = ws.Entry("p", ws.daily(), lambda: results.pop(0), retry_seconds=HOUR)
        scheduler = self.scheduler([entry], local(2026, 11, 17, 12))
        scheduler.run_due(self.stop)
        scheduler.clock.now -= 3 * HOUR                             # the retry time is now 4 h away
        self.assertEqual(scheduler.run_due(self.stop), ["p"])

    def test_run_forever_returns_when_stop_is_set_while_it_waits(self):
        scheduler = self.scheduler([self.entry("a")], 1000.0)
        thread = threading.Thread(target=scheduler.run_forever, args=(self.stop, 3600), daemon=True)
        thread.start()
        deadline = time.monotonic() + 2
        while not self.calls and time.monotonic() < deadline:
            time.sleep(0.01)
        self.stop.set()         # the thread now waits out a one-hour tick; stop must end that wait
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.calls, ["a"])


class WorkerEntries(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lib = SimpleNamespace(DATA_DIR=Path(tmp.name))
        self.stop = threading.Event()

    def entries(self):
        return {e.name: e for e in worker.schedule_entries(self.lib, self.stop)}

    def test_maintenance_then_insights_then_prefetch_then_precompute_in_a_fixed_order(self):
        self.assertEqual([e.name for e in worker.schedule_entries(self.lib, self.stop)],
                         ["daily_maintenance", "insights_refresh", "owned_prefetch", "similar_precompute"])

    def test_daily_maintenance_entry_runs_the_maintenance_once_a_day(self):
        entry = self.entries()["daily_maintenance"]
        self.assertFalse(entry.due(local(2026, 11, 17, 23), local(2026, 11, 17, 1)))
        self.assertTrue(entry.due(local(2026, 11, 18, 1), local(2026, 11, 17, 23)))
        with mock.patch.object(worker, "_daily_maintenance") as maintain:
            entry.run()
        maintain.assert_called_once_with(self.lib)

    def test_insights_entry_keeps_the_r5_key_and_passes_stop(self):
        entry = self.entries()["insights_refresh"]
        self.assertEqual(entry.legacy_key, insights_refresh.LAST_RUN_KEY)
        self.assertIs(entry.due, insights_refresh.is_due)
        with mock.patch.object(insights_refresh, "refresh_once") as refresh:
            entry.run()
        refresh.assert_called_once_with(self.lib, stop=self.stop)

    def test_prefetch_entry_is_off_without_caps_and_passes_the_store_and_stop(self):
        from app.services import owned_prefetch, prefetch_state

        entry = self.entries()["owned_prefetch"]
        with mock.patch.dict("os.environ", {}, clear=False) as env:
            env.pop(prefetch_state.ENV_BUDGETS, None)
            self.assertFalse(entry.due(local(2026, 11, 18, 1), None))
        with mock.patch.dict("os.environ", {prefetch_state.ENV_BUDGETS: "musicbrainz=10"}):
            self.assertTrue(entry.due(local(2026, 11, 18, 1), local(2026, 11, 17, 23)))
            self.assertFalse(entry.due(local(2026, 11, 17, 23), local(2026, 11, 17, 1)))
        with mock.patch.object(owned_prefetch, "run_once") as run:
            entry.run()
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], self.lib)
        self.assertEqual(run.call_args.kwargs["stop"], self.stop)

    def test_precompute_entry_is_daily_retries_after_30_minutes_and_passes_stop(self):
        from app.services import similar_precompute

        entry = self.entries()["similar_precompute"]
        self.assertIsNone(entry.legacy_key)          # the old web loop kept its day in memory only
        self.assertEqual(entry.retry_seconds, 1800.0)
        self.assertFalse(entry.due(local(2026, 11, 17, 23), local(2026, 11, 17, 1)))
        self.assertTrue(entry.due(local(2026, 11, 18, 1), local(2026, 11, 17, 23)))
        with mock.patch.object(similar_precompute, "run_once") as run_once:
            entry.run()
        run_once.assert_called_once_with(self.lib, stop=self.stop)


if __name__ == "__main__":
    unittest.main()
