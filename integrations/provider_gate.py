"""Shared provider gate: one reservation point for provider request slots.

Every process (web, worker) reserves a slot here before calling a provider, so the
spacing a provider's terms require holds for the whole host. State lives in its own
SQLite file (``provider_gate.sqlite3``) so a reservation never queues behind a long
knowledge-store write. See docs/efficiency.md section 6.1.

Wall-clock time is used because monotonic clocks are not comparable across processes.
If the gate file cannot be used, an in-process pacer at twice the interval takes over;
a provider is never called unpaced.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

GATE_FILE = "provider_gate.sqlite3"
INTERVALS = {"musicbrainz": 1.1}  # seconds between slots; other providers keep their own pacing
MAX_FUTURE_SLOT = 60.0  # a next_at further ahead than this is a clock step, not a queue
MAX_PENALTY = 3600.0  # also the furthest a block can legitimately sit ahead of now
FALLBACK_FACTOR = 2.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS gate (
  provider TEXT PRIMARY KEY,
  next_at REAL NOT NULL,
  blocked_until REAL NOT NULL DEFAULT 0,
  day TEXT NOT NULL DEFAULT '',
  day_count INTEGER NOT NULL DEFAULT 0
)
"""


class ProviderGate:
    def __init__(self, path, *, clock=time.time, sleep=time.sleep, intervals=None):
        self.path = Path(path)
        self._clock = clock
        self._sleep = sleep
        self._intervals = dict(INTERVALS if intervals is None else intervals)
        self._local = threading.local()
        self._memory = {}  # provider -> [next_at, blocked_until], used only on fallback
        self._memory_lock = threading.Lock()
        self._warned = False

    def interval(self, provider: str) -> float:
        return float(self._intervals.get(provider, 0.0))

    def reserve(self, provider: str, max_wait: float) -> bool:
        """Take the next slot. Sleeps until it starts; returns False if that is beyond max_wait."""
        try:
            wait = self._reserve_shared(provider, max_wait)
        except (sqlite3.Error, OSError) as exc:
            self._warn(exc)
            wait = self._reserve_memory(provider, max_wait)
        if wait is None:
            return False
        if wait > 0:
            self._sleep(wait)
        return True

    def penalize(self, provider: str, seconds: float) -> None:
        """Block the provider for ``seconds`` (after a 429 or 503; use Retry-After when sent)."""
        seconds = max(0.0, min(float(seconds), MAX_PENALTY))
        now = self._clock()
        try:
            conn = self._conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._row(conn, provider, now)
                next_at, blocked = _clamp(now, row[0], row[1])
                blocked = max(blocked, now + seconds)
                conn.execute("UPDATE gate SET next_at=?, blocked_until=? WHERE provider=?",
                             (next_at, blocked, provider))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        except (sqlite3.Error, OSError) as exc:
            self._warn(exc)
            with self._memory_lock:
                state = self._memory.setdefault(provider, [now, 0.0])
                state[0], state[1] = _clamp(now, state[0], state[1])
                state[1] = max(state[1], now + seconds)

    def snapshot(self) -> dict:
        """Per-provider state for diagnostics."""
        try:
            rows = self._conn().execute(
                "SELECT provider, next_at, blocked_until, day, day_count FROM gate").fetchall()
        except (sqlite3.Error, OSError):
            return {}
        return {r[0]: {"next_at": r[1], "blocked_until": r[2], "day": r[3], "day_count": r[4]}
                for r in rows}

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
        self._local.conn = None

    # -- shared (SQLite) path ------------------------------------------------

    def _conn(self):
        pid = os.getpid()
        conn = getattr(self._local, "conn", None)
        if conn is not None and self._local.pid == pid:
            return conn
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            # Two processes opening a new file at once can collide on the WAL switch,
            # which SQLite does not wait for; retry briefly (real time, not the injected clock).
            for attempt in range(20):
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute(_SCHEMA)
                    break
                except sqlite3.OperationalError:
                    if attempt == 19:
                        raise
                    time.sleep(0.05)
            conn.execute("PRAGMA synchronous=NORMAL")
        except BaseException:
            conn.close()
            raise
        self._local.conn, self._local.pid = conn, pid
        return conn

    @staticmethod
    def _row(conn, provider, now):
        conn.execute(
            "INSERT OR IGNORE INTO gate (provider, next_at) VALUES (?, ?)", (provider, now))
        return conn.execute(
            "SELECT next_at, blocked_until, day, day_count FROM gate WHERE provider=?",
            (provider,)).fetchone()

    def _reserve_shared(self, provider, max_wait):
        interval = self.interval(provider)
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            now = self._clock()  # read after the lock, so waiting for it cannot make it stale
            next_at, blocked, day, count = self._row(conn, provider, now)
            next_at, blocked = _clamp(now, next_at, blocked)
            start = max(now, next_at, blocked)
            if start - now > max_wait:
                conn.execute("ROLLBACK")
                return None
            today = time.strftime("%Y-%m-%d", time.localtime(now))
            count = count + 1 if day == today else 1
            conn.execute(
                "UPDATE gate SET next_at=?, blocked_until=?, day=?, day_count=? WHERE provider=?",
                (start + interval, blocked, today, count, provider))
            conn.execute("COMMIT")
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        return start - now

    # -- fallback (in-process) path ------------------------------------------

    def _reserve_memory(self, provider, max_wait):
        interval = self.interval(provider) * FALLBACK_FACTOR
        with self._memory_lock:
            now = self._clock()
            state = self._memory.setdefault(provider, [now, 0.0])
            state[0], state[1] = _clamp(now, state[0], state[1])
            start = max(now, state[0], state[1])
            if start - now > max_wait:
                return None
            state[0] = start + interval
            return start - now

    def _warn(self, exc):
        if not self._warned:
            self._warned = True
            logger.warning("Provider gate %s unavailable (%s); pacing in-process at %gx",
                           self.path, exc, FALLBACK_FACTOR)


def _clamp(now, next_at, blocked):
    """Undo a wall-clock step back so it cannot freeze a provider.

    A block never sits more than MAX_PENALTY ahead and a queued slot never more than
    MAX_FUTURE_SLOT past the block; anything further ahead means the clock moved back.
    A step back smaller than these bounds still delays by the step.
    """
    if blocked - now > MAX_PENALTY:
        blocked = now
    if next_at - max(now, blocked) > MAX_FUTURE_SLOT:
        next_at = now
    return next_at, blocked


_default: ProviderGate | None = None
_default_lock = threading.Lock()


def default_gate(data_dir) -> ProviderGate:
    """Process-wide gate for the configured data directory."""
    global _default
    path = Path(data_dir) / GATE_FILE
    with _default_lock:
        if _default is None or _default.path != path:
            _default = ProviderGate(path)
        return _default
