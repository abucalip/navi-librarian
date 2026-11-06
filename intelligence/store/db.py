"""Connection helper for the Server V2 database (decision D-7: a dedicated file)."""
from __future__ import annotations

import sqlite3
from os import PathLike

from .migrations import migrate
from .state import attach_state, default_state_path

BUSY_TIMEOUT_SECONDS = 10


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


def open_store(
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
