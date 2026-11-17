"""Table-driven worker scheduler (docs/efficiency.md section 6.2, step W1).

Not a queue. A fixed list of ``Entry(name, due, run)`` evaluated in order by one scheduler thread. Jobs
run one at a time on that thread. ``due(now, last_run)`` decides whether an entry runs now; ``last_run``
is the time the entry's last run returned, kept in the knowledge store's ``meta`` table under
``schedule:<name>``, so a restart neither repeats a job that is not due nor skips one that is.

Rules:

- A run that returns, or raises, is recorded. A raising run is logged by error type only and still
  records its time, so a broken job waits for its next window instead of spinning.
- A run that returns while ``stop`` is set was cut short by shutdown: it is not recorded and stays due.
- A run that returns ``NOT_READY`` could not do its work yet (its input is unavailable): it is not recorded
  and is tried again after the entry's ``retry_seconds`` (kept in memory only; a restart makes it due again).
- ``stop`` is checked before each entry, so shutdown never starts the next job.

This module imports no job module: ``app/worker.py`` builds the entries, and the diagnostics route reads
``last_runs`` without loading worker code.
"""
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from intelligence.store import open_store

logger = logging.getLogger(__name__)

KEY_PREFIX = "schedule:"
TICK_SECONDS = 60.0      # how often the scheduler thread evaluates the due rules
NOT_READY = object()     # returned by a run whose input is not usable yet: not recorded, retried later


@dataclass(frozen=True)
class Entry:
    name: str
    due: Callable[[float, Optional[float]], bool]
    run: Callable[[], object]
    legacy_key: Optional[str] = None     # meta key read when ``schedule:<name>`` is missing (upgrade path)
    retry_seconds: float = 1800.0        # wait after a ``NOT_READY`` return before trying again


def interval(seconds: float) -> Callable[[float, Optional[float]], bool]:
    """Due when never run, after ``seconds`` have passed, or when the stored time is ahead of the clock."""
    def due(now: float, last_run: Optional[float]) -> bool:
        if last_run is None:
            return True
        return not 0 <= now - last_run < seconds     # a time in the future (clock stepped back) cannot freeze it
    return due


def daily() -> Callable[[float, Optional[float]], bool]:
    """Due when never run or when the local date of the last run is not today's."""
    def due(now: float, last_run: Optional[float]) -> bool:
        if last_run is None:
            return True
        return datetime.fromtimestamp(last_run).date() != datetime.fromtimestamp(now).date()
    return due


def _as_time(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read(db, key: str) -> Optional[float]:
    row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if row is None else _as_time(row["value"])


def read_last_run(db, entry: Entry) -> Optional[float]:
    """The stored last run of ``entry``; falls back to its legacy key. An unreadable value counts as never run."""
    row = db.execute("SELECT value FROM meta WHERE key = ?", (KEY_PREFIX + entry.name,)).fetchone()
    if row is not None:
        return _as_time(row["value"])
    return _read(db, entry.legacy_key) if entry.legacy_key else None


def record_run(db, name: str, when: float) -> None:
    with db:
        db.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (KEY_PREFIX + name, str(float(when))),
        )


def last_runs(db) -> dict:
    """Every recorded entry's last run time, by entry name (read by ``/api/diagnostics/runtime``)."""
    rows = db.execute("SELECT key, value FROM meta WHERE substr(key, 1, ?) = ? ORDER BY key",
                      (len(KEY_PREFIX), KEY_PREFIX)).fetchall()
    return {row["key"][len(KEY_PREFIX):]: _as_time(row["value"]) for row in rows}


class Scheduler:
    """Runs due entries in their fixed order. Last-run times are loaded once and written after each run."""

    def __init__(self, entries, store_path, clock=time.time):
        self.entries = tuple(entries)
        self.store_path = store_path
        self.clock = clock
        self._last = None
        self._retry_at = {}      # entry name -> clock time before which a NOT_READY entry is not retried

    def _load(self):
        db = open_store(self.store_path)
        try:
            self._last = {entry.name: read_last_run(db, entry) for entry in self.entries}
        finally:
            db.close()

    def _save(self, name, when):
        self._last[name] = when      # kept in memory even if the write fails, so the job does not spin
        try:
            db = open_store(self.store_path)
            try:
                record_run(db, name, when)
            finally:
                db.close()
        except Exception as exc:
            logger.error("Could not record scheduled run of %s (%s)", name, type(exc).__name__)

    def run_due(self, stop) -> list:
        """Run every entry that is due now, one at a time; returns the names that ran and were recorded."""
        if self._last is None:
            self._load()
        ran = []
        for entry in self.entries:
            if stop.is_set():
                break
            if not entry.due(self.clock(), self._last.get(entry.name)):
                continue
            retry_at = self._retry_at.get(entry.name)
            if retry_at is not None and 0 < retry_at - self.clock() <= entry.retry_seconds:
                continue     # waiting to retry; a wait longer than retry_seconds means the clock stepped back
            result = None
            try:
                result = entry.run()
            except Exception as exc:
                logger.error("Scheduled job %s failed (%s)", entry.name, type(exc).__name__)
            if stop.is_set():
                break        # cut short by shutdown: not recorded, so it stays due
            if result is NOT_READY:
                self._retry_at[entry.name] = self.clock() + entry.retry_seconds
                continue
            self._retry_at.pop(entry.name, None)
            self._save(entry.name, self.clock())
            ran.append(entry.name)
        return ran

    def run_forever(self, stop, tick=TICK_SECONDS):
        while not stop.is_set():
            try:
                self.run_due(stop)
            except Exception as exc:
                logger.error("Worker schedule failed (%s)", type(exc).__name__)
            stop.wait(tick)


def start(entries, store_path, stop):
    """Start the scheduler on its own daemon thread and return the thread."""
    scheduler = Scheduler(entries, store_path)
    thread = threading.Thread(target=scheduler.run_forever, args=(stop,), name="worker-schedule", daemon=True)
    thread.start()
    return thread
