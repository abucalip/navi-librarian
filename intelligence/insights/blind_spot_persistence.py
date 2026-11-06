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
from . import decisions
from .blind_spots import CARD_KIND, BlindSpotsConfig, BlindSpotsResult, blind_spot_card, dismiss_key

DISMISSED = "dismissed"
RESOURCE = "insights"
_KEY = "json_extract(payload, '$.subject.key')"


def dismissed_set_keys(db: sqlite3.Connection) -> set[str]:
    """Dismissed set keys, in the ``blind_spot:<set key>`` form ``find_blind_spots`` expects."""
    return decisions.keys(db, CARD_KIND, DISMISSED)


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
    blocked = dismissed_set_keys(db)
    rows = db.execute(
        "SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL "
        "ORDER BY json_extract(payload, '$.score') DESC, json_extract(payload, '$.subject.key'), id",
        (CARD_KIND,),
    ).fetchall()
    cards = [json.loads(r["payload"]) for r in rows]
    return [c for c in cards if c["subject"]["key"] not in blocked][: max(limit, 0)]


def dismiss_blind_spot(db: sqlite3.Connection, set_key: str, now: float | None = None) -> bool:
    """Dismiss a set by its set key. Returns False if it was already dismissed.

    The decision is stored in the owner-state file (a tombstone if the card is no longer live).
    """
    if not decisions.record(db, CARD_KIND, dismiss_key(set_key), DISMISSED, now, hide_live=True):
        return False
    generations.bump_data_version(db, RESOURCE)
    return True


def restore_blind_spot(db: sqlite3.Connection, set_key: str) -> bool:
    """Undo a dismissal; the set returns at the next refresh. Returns False if it was not dismissed."""
    if not decisions.remove(db, CARD_KIND, dismiss_key(set_key), DISMISSED):
        return False
    generations.bump_data_version(db, RESOURCE)
    return True
