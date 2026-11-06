"""Owner decisions on insight cards (dismissed, accepted), kept in the state file.

Shared core for :mod:`.persistence`, :mod:`.blind_spot_persistence`, :mod:`.card_persistence` and
:mod:`.outcomes`. Decisions live in ``state.card_decisions`` (see :mod:`intelligence.store.state`),
keyed by ``(kind, key)`` and never by a row id, so wiping or rebuilding the knowledge file cannot
cost the owner a decision. The live cards stay in ``insights`` in the knowledge file.

A decision keeps a snapshot of the card (``payload``) when a live card existed, so the lens
scorecard can still judge a dismissed card; otherwise it is a tombstone holding only the key.
"""
from __future__ import annotations

import json
import sqlite3
import time

DISMISSED = "dismissed"
ACCEPTED = "accepted"
_KEY = "json_extract(payload, '$.subject.key')"


def keys(db: sqlite3.Connection, kind: str, state: str) -> set[str]:
    rows = db.execute("SELECT key FROM state.card_decisions WHERE kind = ? AND state = ?", (kind, state))
    return {r["key"] for r in rows}


def payloads(db: sqlite3.Connection, kind: str, state: str) -> list[dict]:
    rows = db.execute(
        "SELECT payload FROM state.card_decisions WHERE kind = ? AND state = ? ORDER BY decided_at, key", (kind, state)
    )
    return [json.loads(r["payload"]) for r in rows]


def record(db: sqlite3.Connection, kind: str, key: str, state: str, now: float | None, *, hide_live: bool) -> bool:
    """Store a decision (False if it already exists). A dismissal also removes the live card."""
    if db.execute(
        "SELECT 1 FROM state.card_decisions WHERE kind = ? AND key = ? AND state = ?", (kind, key, state)
    ).fetchone():
        return False
    now = time.time() if now is None else now
    live = db.execute(
        f"SELECT payload FROM main.insights WHERE kind = ? AND dismissed_state IS NULL AND {_KEY} = ? LIMIT 1",
        (kind, key),
    ).fetchone()
    payload = live["payload"] if live else json.dumps({"subject": {"key": key}})
    with db:
        db.execute(
            "INSERT INTO state.card_decisions (kind, key, state, payload, decided_at) VALUES (?, ?, ?, ?, ?)",
            (kind, key, state, payload, now),
        )
    if hide_live:
        with db:
            db.execute(
                f"DELETE FROM main.insights WHERE kind = ? AND dismissed_state IS NULL AND {_KEY} = ?", (kind, key)
            )
    return True


def remove(db: sqlite3.Connection, kind: str, key: str, state: str) -> bool:
    with db:
        cur = db.execute(
            "DELETE FROM state.card_decisions WHERE kind = ? AND key = ? AND state = ?", (kind, key, state)
        )
    return bool(cur.rowcount)
