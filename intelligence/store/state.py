"""The owner-state file: decisions that must survive a wipe or rebuild of the knowledge file.

Server V2 data is split in two (docs/efficiency.md section E, D-026 consequence 4):

* the **knowledge file** (``intelligence.sqlite3``): observations, entities, edges, insights, job
  runs. Derived or fetched, so it can be wiped and rebuilt;
* the **state file** (``intelligence.state.sqlite3`` beside it): what the owner decided. Today that is
  card decisions (dismissed, accepted), keyed by a stable card identity (``kind`` plus the card's own
  key), never by a row id, so a generation rebuild cannot lose one.

The state file is attached to the same connection as schema ``state``, so queries read
``state.card_decisions`` and existing function signatures keep working. It has its own
append-only migrations (``PRAGMA state.user_version``). No network.
"""
from __future__ import annotations

import sqlite3
from os import PathLike
from pathlib import Path

STATE_SCHEMA = "state"
STATE_MIGRATIONS: tuple[tuple[int, str, tuple[str, ...]], ...] = (
    (1, "card decisions", (
        """
        CREATE TABLE state.card_decisions (
            kind TEXT NOT NULL,
            key TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('dismissed', 'accepted')),
            payload TEXT NOT NULL,
            decided_at REAL NOT NULL,
            PRIMARY KEY (kind, key, state)
        )
        """,
    )),
)
STATE_LATEST = STATE_MIGRATIONS[-1][0]


class StateError(RuntimeError):
    pass


def default_state_path(database_path: str | PathLike[str]) -> str:
    """``intelligence.sqlite3`` -> ``intelligence.state.sqlite3`` (``:memory:`` stays in memory)."""
    if str(database_path) == ":memory:":
        return ":memory:"
    path = Path(database_path)
    return str(path.with_name(f"{path.stem}.state{path.suffix}"))


def attach_state(db: sqlite3.Connection, state_path: str | PathLike[str]) -> None:
    """Attach and migrate the state file as schema ``state``; move legacy decisions over once."""
    db.execute("ATTACH DATABASE ? AS state", (str(state_path),))
    if str(state_path) != ":memory:":
        db.execute("PRAGMA state.journal_mode = WAL")
    version = int(db.execute("PRAGMA state.user_version").fetchone()[0])
    if version > STATE_LATEST:
        raise StateError(f"state file is version {version}, newer than this code ({STATE_LATEST})")
    for number, _name, statements in STATE_MIGRATIONS:
        if number <= version:
            continue
        with db:
            for statement in statements:
                db.execute(statement)
            db.execute(f"PRAGMA state.user_version = {number}")
    move_legacy_decisions(db)


def move_legacy_decisions(db: sqlite3.Connection) -> int:
    """Copy decisions still stored in ``main.insights`` into the state file, then drop them there.

    Idempotent. The copy is committed to the state file before anything is deleted, so a crash in
    between leaves the decision in both places (harmless) and never in neither.
    """
    with db:
        copied = db.execute(
            "INSERT OR IGNORE INTO state.card_decisions (kind, key, state, payload, decided_at) "
            "SELECT kind, json_extract(payload, '$.subject.key'), dismissed_state, payload, computed_at "
            "FROM main.insights WHERE dismissed_state IN ('dismissed', 'accepted') "
            "AND json_extract(payload, '$.subject.key') IS NOT NULL"
        ).rowcount
    if db.execute("SELECT 1 FROM main.insights WHERE dismissed_state IS NOT NULL LIMIT 1").fetchone():
        with db:
            db.execute(
                "DELETE FROM main.insights WHERE dismissed_state IN ('dismissed', 'accepted') "
                "AND json_extract(payload, '$.subject.key') IS NOT NULL"
            )
    return max(copied, 0)
