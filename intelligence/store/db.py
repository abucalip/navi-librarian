"""Connection helper for the Server V2 database (decision D-7: a dedicated file)."""
from __future__ import annotations

import sqlite3
import threading
import time
from os import PathLike
from pathlib import Path

from .migrations import migrate
from .state import attach_state, default_state_path

BUSY_TIMEOUT_SECONDS = 10

_observer = None


def set_observer(fn) -> None:
    """Report each open as ``fn(operation, seconds, locked)`` (runtime metrics)."""
    global _observer
    _observer = fn


def _observed(operation, opener):
    started = time.perf_counter()
    locked = False
    try:
        return opener()
    except sqlite3.OperationalError as exc:
        locked = "locked" in str(exc)
        raise
    finally:
        if _observer is not None:
            try:
                _observer(operation, time.perf_counter() - started, locked)
            except Exception:  # metrics must never break a request
                pass


_ensured: set[tuple[str, str]] = set()
_ensure_lock = threading.Lock()


def connect(database_path: str | PathLike[str]) -> sqlite3.Connection:
    """Open a connection with this store's conventions; does not migrate.

    Foreign keys are enforced, rows are addressable by column name, and writers wait
    up to ``BUSY_TIMEOUT_SECONDS`` instead of failing at once. WAL keeps readers
    unblocked while a job writes.
    """
    db = sqlite3.connect(database_path, timeout=BUSY_TIMEOUT_SECONDS)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    if str(database_path) != ":memory:":
        db.execute("PRAGMA journal_mode = WAL")
    return db


def _open_store(
    database_path: str | PathLike[str], state_path: str | PathLike[str] | None = None
) -> sqlite3.Connection:
    """Open the knowledge database, bring its schema up to date and attach the owner-state file.

    ``state_path`` defaults to a file beside the database (``:memory:`` stays in memory). Decisions
    live in schema ``state`` (see :mod:`.state`); everything else is rebuildable.
    """
    db = connect(database_path)
    try:
        migrate(db)
        attach_state(db, state_path if state_path is not None else default_state_path(database_path))
    except BaseException:
        db.close()
        raise
    return db


def ensure_store(
    database_path: str | PathLike[str], state_path: str | PathLike[str] | None = None
) -> None:
    """Migrate and attach once per process and path, then close (call at web and worker startup).

    Afterwards the knowledge and state files exist at the current version, so request handlers can use
    :func:`open_readonly` and :func:`open_writer`. A failure is not remembered, so the next call retries.
    """
    key = (str(Path(database_path).resolve()), str(state_path))
    with _ensure_lock:
        if key in _ensured:
            return
        open_store(database_path, state_path).close()
        _ensured.add(key)


def _open_writer(
    database_path: str | PathLike[str], state_path: str | PathLike[str] | None = None
) -> sqlite3.Connection:
    """Open for writing without migrating or moving legacy rows (the store was prepared by :func:`ensure_store`)."""
    db = connect(database_path)
    try:
        db.execute("ATTACH DATABASE ? AS state", (str(state_path if state_path is not None else default_state_path(database_path)),))
    except BaseException:
        db.close()
        raise
    return db


def _open_readonly(
    database_path: str | PathLike[str], state_path: str | PathLike[str] | None = None
) -> sqlite3.Connection:
    """Open the knowledge file and the state file read-only (for the web process).

    Does not migrate or create anything; the files must exist and be at the current version.
    Any write on this connection fails.
    """
    db = sqlite3.connect(f"file:{Path(database_path).resolve()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS)
    db.row_factory = sqlite3.Row
    state = state_path if state_path is not None else default_state_path(database_path)
    db.execute("ATTACH DATABASE ? AS state", (f"file:{Path(state).resolve()}?mode=ro",))
    return db


def open_store(database_path, state_path=None):
    """Migrate and open (worker and scripts); see :func:`_open_store`."""
    return _observed("open_store", lambda: _open_store(database_path, state_path))


def open_writer(database_path, state_path=None):
    """Open for writing without migrating; see :func:`_open_writer`."""
    return _observed("open_writer", lambda: _open_writer(database_path, state_path))


def open_readonly(database_path, state_path=None):
    """Open read-only; see :func:`_open_readonly`."""
    return _observed("open_readonly", lambda: _open_readonly(database_path, state_path))
