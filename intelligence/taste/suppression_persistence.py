"""Persist skip and dismissal events in the owner-state file (Phase 6 item 5, slice 9, D-027).

Input is already-validated :class:`~intelligence.taste.suppression.SuppressionEvent` values; this module
never validates raw mappings and never computes weights. Events live in ``state.suppression_events``
(see :mod:`intelligence.store.state`), never in the rebuildable knowledge file.

Insert rules
------------
* a batch is written in one transaction: either every event is stored or none is;
* an ``event_id`` that is already stored is never overwritten. A replay of the same payload is reported
  as ``duplicate``; the same ``event_id`` with a different payload is reported as ``conflict`` and the
  original row is kept. Both leave the table unchanged;
* outcomes come back in input order, so a caller can tell new rows from replays and from conflicts.

Retention
---------
Rows whose ``occurred_at`` is strictly older than ``now - RETENTION_SECONDS`` (180 days) are deleted by
:func:`sweep_expired`. A row exactly on the cutoff is kept, as are newer rows and future rows. Each call
deletes at most ``limit`` rows and is safe to repeat; nothing runs it automatically. The caller supplies
``now``, so the boundary is deterministic.

Nothing here calls a provider, defines a route, runs a job, feeds a ranking, or touches other tables.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from .suppression import MAX_BATCH, SuppressionEvent

RETENTION_DAYS = 180
RETENTION_SECONDS = RETENTION_DAYS * 86400
SWEEP_LIMIT_MAX = 10_000

INSERTED = "inserted"
DUPLICATE = "duplicate"
CONFLICT = "conflict"

_COLUMNS = (
    "event_id", "client", "kind", "subject_kind", "subject_id", "mbid",
    "occurred_at", "played_seconds", "duration_seconds",
)
_INSERT = (
    f"INSERT INTO state.suppression_events ({', '.join(_COLUMNS)}) "
    f"VALUES ({', '.join('?' * len(_COLUMNS))}) ON CONFLICT (event_id) DO NOTHING"
)
_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM state.suppression_events WHERE event_id = ?"


@dataclass(frozen=True)
class InsertOutcome:
    event_id: str
    status: str  # INSERTED, DUPLICATE or CONFLICT


def _params(event: SuppressionEvent) -> tuple:
    return (
        event.event_id, event.client, event.kind, event.subject_kind, event.subject_id, event.mbid,
        event.occurred_at, event.played_seconds, event.duration_seconds,
    )


def insert_events(db: sqlite3.Connection, events: Sequence[SuppressionEvent]) -> tuple[InsertOutcome, ...]:
    """Store validated events atomically and report each one as inserted, duplicate or conflict.

    Raises ``TypeError`` for anything that is not a ``SuppressionEvent`` and ``ValueError`` for a batch
    over ``MAX_BATCH``, before writing. A database error (for example a CHECK the event breaks) raises
    and rolls back the whole batch, so nothing is partially committed.
    """
    if not isinstance(events, (list, tuple)):
        raise TypeError("events must be a list or tuple of SuppressionEvent")
    if len(events) > MAX_BATCH:
        raise ValueError(f"batch of {len(events)} exceeds {MAX_BATCH}")
    for event in events:
        if not isinstance(event, SuppressionEvent):
            raise TypeError("events must contain only SuppressionEvent values")

    outcomes: list[InsertOutcome] = []
    with db:
        for event in events:
            cursor = db.execute(_INSERT, _params(event))
            if cursor.rowcount == 1:
                outcomes.append(InsertOutcome(event.event_id, INSERTED))
                continue
            row = db.execute(_SELECT, (event.event_id,)).fetchone()
            same = row is not None and tuple(row[column] for column in _COLUMNS) == _params(event)
            outcomes.append(InsertOutcome(event.event_id, DUPLICATE if same else CONFLICT))
    return tuple(outcomes)


def get_event(db: sqlite3.Connection, event_id: str) -> SuppressionEvent | None:
    """The stored event with this id, or None."""
    row = db.execute(_SELECT, (event_id,)).fetchone()
    if row is None:
        return None
    return SuppressionEvent(**{column: row[column] for column in _COLUMNS})


def retention_cutoff(now: float) -> float:
    """Epoch seconds before which rows are deleted: ``now`` minus 180 days (the cutoff itself is kept)."""
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        raise ValueError("now must be a finite number of epoch seconds")
    return float(now) - RETENTION_SECONDS


def sweep_expired(db: sqlite3.Connection, now: float, limit: int) -> int:
    """Delete up to ``limit`` events older than the 180-day cutoff and return how many were deleted.

    Oldest rows go first. Repeat the call until it returns fewer than ``limit`` to finish the sweep.
    Only ``state.suppression_events`` is touched.
    """
    cutoff = retention_cutoff(now)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= SWEEP_LIMIT_MAX:
        raise ValueError(f"limit must be an integer from 1 to {SWEEP_LIMIT_MAX}")
    with db:
        cursor = db.execute(
            "DELETE FROM state.suppression_events WHERE event_id IN ("
            "SELECT event_id FROM state.suppression_events WHERE occurred_at < ? "
            "ORDER BY occurred_at, event_id LIMIT ?)",
            (cutoff, limit),
        )
    return max(cursor.rowcount, 0)
