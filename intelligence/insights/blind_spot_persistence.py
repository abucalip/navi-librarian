"""Persist blind-spot cards and dismissals in the ``insights`` table (no migration).

Mirrors :mod:`.persistence` for the ``blind_spot`` kind. A live card is a generic insight
card (``subject_id`` NULL; the set is keyed by ``blind_spot:<set key>`` in the payload). A
dismissed row is the per-user suppression memory: it survives every refresh, and its set key
is what :func:`find_blind_spots` receives as ``dismissed`` (via :func:`dismissed_set_keys`).
Nothing here fetches data or touches ownership flags or recommendation weights.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ..store import generations
from .blind_spots import CARD_KIND, BlindSpotsConfig, BlindSpotsResult, blind_spot_card, dismiss_key

DISMISSED = "dismissed"
RESOURCE = "insights"
_KEY = "json_extract(payload, '$.subject.key')"


def dismissed_set_keys(db: sqlite3.Connection) -> set[str]:
    """Dismissed set keys, in the ``blind_spot:<set key>`` form ``find_blind_spots`` expects."""
    rows = db.execute(
        f"SELECT {_KEY} AS key FROM insights WHERE kind = ? AND dismissed_state = ?", (CARD_KIND, DISMISSED)
    ).fetchall()
    return {r["key"] for r in rows if r["key"]}


def save_blind_spots(db: sqlite3.Connection, result: BlindSpotsResult, now: float | None = None) -> int:
    """Replace the live blind-spot cards with ``result``; dismissed rows are kept. Returns cards stored.

    An empty result clears the live cards: a stale gap is never shown once the evidence
    (the sets, or what the library owns) no longer supports it.
    """
    now = time.time() if now is None else now
    blocked = dismissed_set_keys(db)
    cards = [blind_spot_card(s, result.config) for s in result.spots if dismiss_key(s.set.key) not in blocked]
    with db:
        generation = generations.current_generation(db)
        db.execute("DELETE FROM insights WHERE kind = ? AND dismissed_state IS NULL", (CARD_KIND,))
        db.executemany(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
            "VALUES (?, NULL, ?, ?, ?, ?)",
            [(CARD_KIND, json.dumps(c, sort_keys=True), json.dumps(c["reasons"], sort_keys=True), generation, now)
             for c in cards],
        )
    generations.bump_data_version(db, RESOURCE)
    return len(cards)


def list_blind_spot_cards(db: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL "
        "ORDER BY json_extract(payload, '$.score') DESC, json_extract(payload, '$.subject.key'), id LIMIT ?",
        (CARD_KIND, max(limit, 0)),
    ).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def dismiss_blind_spot(db: sqlite3.Connection, set_key: str, now: float | None = None) -> bool:
    """Dismiss a set by its set key. Returns False if it was already dismissed.

    If the card is no longer live a tombstone row is written, so the dismissal still
    suppresses the set on later refreshes.
    """
    now = time.time() if now is None else now
    key = dismiss_key(set_key)
    if key in dismissed_set_keys(db):
        return False
    with db:
        cur = db.execute(
            f"UPDATE insights SET dismissed_state = ? WHERE kind = ? AND dismissed_state IS NULL AND {_KEY} = ?",
            (DISMISSED, CARD_KIND, key),
        )
        if not cur.rowcount:
            db.execute(
                "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at, dismissed_state) "
                "VALUES (?, NULL, ?, '[]', ?, ?, ?)",
                (CARD_KIND, json.dumps({"subject": {"key": key}}), generations.current_generation(db), now, DISMISSED),
            )
    generations.bump_data_version(db, RESOURCE)
    return True


def restore_blind_spot(db: sqlite3.Connection, set_key: str) -> bool:
    """Undo a dismissal; the set returns at the next refresh. Returns False if it was not dismissed."""
    with db:
        cur = db.execute(
            f"DELETE FROM insights WHERE kind = ? AND dismissed_state = ? AND {_KEY} = ?",
            (CARD_KIND, DISMISSED, dismiss_key(set_key)),
        )
    if cur.rowcount:
        generations.bump_data_version(db, RESOURCE)
    return bool(cur.rowcount)
