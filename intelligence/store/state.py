"""The owner-state file: decisions that must survive a wipe or rebuild of the knowledge file.

Server V2 data is split in two (docs/efficiency.md section E, D-026 consequence 4):

* the **knowledge file** (``intelligence.sqlite3``): observations, entities, edges, insights, job
  runs. Derived or fetched, so it can be wiped and rebuilt;
* the **state file** (``intelligence.state.sqlite3`` beside it): what the owner decided. Today that is
  card decisions (dismissed, accepted), keyed by a stable card identity (``kind`` plus the card's own
  key), never by a row id, so a generation rebuild cannot lose one; and skip/dismiss suppression
  events (append-only, D-027); and smart playlist rule sets (mutable, explicit delete only).

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
    # Skip and dismissal events (Phase 6 item 5, D-027). Append-only: UPDATE is refused by trigger, and
    # DELETE is used only by the bounded retention sweep in intelligence.taste.suppression_persistence.
    # The CHECKs are the contract's shape only; validation (suppression.py) decides what is accepted.
    (2, "suppression events", (
        """
        CREATE TABLE state.suppression_events (
            event_id TEXT PRIMARY KEY CHECK (length(event_id) = 36 AND event_id = lower(event_id)),
            client TEXT NOT NULL CHECK (client IN ('macos', 'android')),
            kind TEXT NOT NULL CHECK (kind IN ('skip', 'dismiss')),
            subject_kind TEXT NOT NULL CHECK (subject_kind IN ('track', 'album', 'artist', 'card')),
            subject_id TEXT NOT NULL CHECK (length(subject_id) BETWEEN 1 AND 200),
            mbid TEXT CHECK (mbid IS NULL OR (length(mbid) = 36 AND mbid = lower(mbid))),
            occurred_at REAL NOT NULL CHECK (occurred_at > 0),
            played_seconds REAL CHECK (played_seconds IS NULL OR played_seconds >= 0),
            duration_seconds REAL CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
            CHECK (kind <> 'skip' OR subject_kind = 'track'),
            CHECK (subject_kind = 'track' OR (played_seconds IS NULL AND duration_seconds IS NULL))
        )
        """,
        "CREATE INDEX state.suppression_events_time ON suppression_events (occurred_at, event_id)",
        """
        CREATE TRIGGER state.suppression_events_no_update BEFORE UPDATE ON suppression_events
        BEGIN SELECT RAISE(ABORT, 'suppression events are append-only'); END
        """,
    )),
    # Smart playlist rule sets (Phase 6 item 6, slice 13). A normal mutable table: rule sets are owner
    # configuration, with no retention and explicit delete only (see intelligence.taste.smart_playlist_persistence).
    # The CHECKs are the contract's shape only; intelligence.taste.smart_playlist decides what is accepted.
    # "order" and "limit" are SQL keywords, so they are quoted. There is no refresh flag and no stored result.
    (3, "smart playlist rule sets", (
        """
        CREATE TABLE state.smart_playlists (
            rule_id TEXT PRIMARY KEY CHECK (length(rule_id) = 36 AND rule_id = lower(rule_id)),
            name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
            "match" TEXT NOT NULL CHECK ("match" IN ('all', 'any')),
            rules TEXT NOT NULL CHECK (json_valid(rules) AND json_type(rules) = 'array'
                AND json_array_length(rules) <= 20),
            "order" TEXT NOT NULL CHECK ("order" IN (
                'random', 'newest_added', 'most_played', 'least_played', 'highest_rated', 'title')),
            "limit" INTEGER CHECK ("limit" IS NULL OR "limit" BETWEEN 25 AND 250),
            created_at REAL NOT NULL CHECK (created_at > 0),
            updated_at REAL NOT NULL CHECK (updated_at > 0)
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
    _apply_pending(db, version)
    move_legacy_decisions(db)


def _apply_pending(db: sqlite3.Connection, version: int) -> None:
    """Run each newer migration in its own explicit transaction, with its version bump.

    Python's sqlite3 does not open a transaction before DDL, so one is opened here (as the knowledge
    file's runner does). A failure rolls the whole migration back, leaving the previous version.
    """
    previous_isolation = db.isolation_level
    db.isolation_level = None
    try:
        for number, _name, statements in STATE_MIGRATIONS:
            if number <= version:
                continue
            db.execute("BEGIN IMMEDIATE")
            try:
                for statement in statements:
                    db.execute(statement)
                db.execute(f"PRAGMA state.user_version = {int(number)}")
                db.execute("COMMIT")
            except BaseException as exc:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                if isinstance(exc, sqlite3.Error):
                    raise StateError(f"state migration {number} ({_name}) failed: {exc}") from exc
                raise
    finally:
        db.isolation_level = previous_isolation


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
