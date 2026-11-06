"""Freshness ledger: the last fetch outcome per source, operation and key.

Lets the worker choose what to refresh, back off after failures, and lets a page say
"pending" (never tried) versus "not found" (tried, absent). Stored data stays in
``observations``; this table only records what happened. No network, no decisions about
what a source means.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from .migrations import SOURCE_OUTCOMES

PENDING = "pending"

# Failed attempts back off exponentially from a base delay up to a cap (seconds).
_BACKOFF_BASE = {"error": 300.0, "blocked": 3600.0}
_BACKOFF_CAP = 86400.0


def backoff_seconds(outcome: str, attempts: int) -> float:
    base = _BACKOFF_BASE[outcome]
    return min(base * (2 ** max(attempts - 1, 0)), _BACKOFF_CAP)


def record_outcome(
    db: sqlite3.Connection,
    source: str,
    operation: str,
    key: str,
    outcome: str,
    *,
    now: float,
    ttl: float | None = None,
    observation_id: int | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
) -> dict[str, Any]:
    """Record one attempt. ``ok`` and ``not_found`` reset the failure count and refresh after ``ttl``
    (no refresh scheduled when ``ttl`` is None); ``error`` and ``blocked`` count up and back off.

    A failure keeps the last good ``observation_id``, ``etag`` and ``last_modified``, so the
    last-known-good data stays reachable while the source is down.
    """
    if outcome not in SOURCE_OUTCOMES:
        raise ValueError(f"unknown outcome {outcome!r}")
    previous = get_state(db, source, operation, key)
    if outcome in ("ok", "not_found"):
        attempts = 0
        next_refresh = None if ttl is None else now + ttl
    else:
        attempts = (previous["attempts"] if previous else 0) + 1
        next_refresh = now + backoff_seconds(outcome, attempts)
        if previous:
            observation_id = observation_id if observation_id is not None else previous["observation_id"]
            etag = etag if etag is not None else previous["etag"]
            last_modified = last_modified if last_modified is not None else previous["last_modified"]
    with db:
        db.execute(
            "INSERT INTO source_state (source, operation, key, outcome, observation_id, attempts, "
            "last_attempt_at, next_refresh_at, etag, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (source, operation, key) DO UPDATE SET outcome = excluded.outcome, "
            "observation_id = excluded.observation_id, attempts = excluded.attempts, "
            "last_attempt_at = excluded.last_attempt_at, next_refresh_at = excluded.next_refresh_at, "
            "etag = excluded.etag, last_modified = excluded.last_modified",
            (source, operation, key, outcome, observation_id, attempts, now, next_refresh, etag, last_modified),
        )
    return get_state(db, source, operation, key)


def get_state(db: sqlite3.Connection, source: str, operation: str, key: str) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT * FROM source_state WHERE source = ? AND operation = ? AND key = ?", (source, operation, key)
    ).fetchone()
    return dict(row) if row else None


def status(db: sqlite3.Connection, source: str, operation: str, key: str) -> str:
    """``pending`` when never attempted, otherwise the last outcome."""
    row = get_state(db, source, operation, key)
    return row["outcome"] if row else PENDING


def due(db: sqlite3.Connection, source: str, operation: str, now: float, limit: int = 100) -> list[dict[str, Any]]:
    """Keys whose refresh time has passed, most overdue first, for a bounded refresh job."""
    rows = db.execute(
        "SELECT * FROM source_state WHERE source = ? AND operation = ? "
        "AND next_refresh_at IS NOT NULL AND next_refresh_at <= ? ORDER BY next_refresh_at, key LIMIT ?",
        (source, operation, now, int(limit)),
    ).fetchall()
    return [dict(r) for r in rows]
