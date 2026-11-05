"""Connection helper for the Server V2 database (decision D-7: a dedicated file)."""
from __future__ import annotations

import sqlite3
from os import PathLike

from .migrations import migrate

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


def open_store(database_path: str | PathLike[str]) -> sqlite3.Connection:
    """Open the database and bring its schema up to date."""
    db = connect(database_path)
    try:
        migrate(db)
    except BaseException:
        db.close()
        raise
    return db
