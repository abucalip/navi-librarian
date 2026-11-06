"""Persist Forgotten Gems cards and dismissals in the ``insights`` table (no migration).

A gem row is a generic insight card (``subject_id`` stays NULL: gems are keyed by a
Navidrome key such as ``album:<id>``, kept in the payload). A dismissed row is the
per-user suppression memory: it survives every refresh, and its key is what
:func:`find_forgotten_gems` receives as ``dismissed``. Nothing here fetches data, and
nothing here touches ownership flags or recommendation weights.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ..store import generations
from . import decisions
from .forgotten_gems import CARD_KIND, GemsResult, gem_card

DISMISSED = "dismissed"
RESOURCE = "insights"
_KEY = "json_extract(payload, '$.subject.key')"


def dismissed_keys(db: sqlite3.Connection) -> set[str]:
    return decisions.keys(db, CARD_KIND, DISMISSED)


def save_gems(db: sqlite3.Connection, result: GemsResult, now: float | None = None) -> int:
    """Replace the live gem cards with ``result``; dismissed rows are kept. Returns cards stored.

    An empty result (sparse history, no candidates) clears the live cards: stale gems are
    never shown once the evidence no longer supports them.
    """
    now = time.time() if now is None else now
    blocked = dismissed_keys(db)
    cards = [gem_card(g) for g in result.gems if g.record.key not in blocked]
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


def list_gem_cards(db: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    blocked = dismissed_keys(db)
    rows = db.execute(
        "SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL "
        "ORDER BY json_extract(payload, '$.score') DESC, id",
        (CARD_KIND,),
    ).fetchall()
    cards = [json.loads(r["payload"]) for r in rows]
    return [c for c in cards if c["subject"]["key"] not in blocked][: max(limit, 0)]


def dismiss_gem(db: sqlite3.Connection, key: str, now: float | None = None) -> bool:
    """Dismiss a gem by key. Returns False if it was already dismissed.

    The decision is stored in the owner-state file (a tombstone if the card is no longer live), so
    it suppresses the key on later refreshes and survives a rebuild of the knowledge file.
    """
    if not decisions.record(db, CARD_KIND, key, DISMISSED, now, hide_live=True):
        return False
    generations.bump_data_version(db, RESOURCE)
    return True


def restore_gem(db: sqlite3.Connection, key: str) -> bool:
    """Undo a dismissal; the gem returns at the next refresh. Returns False if it was not dismissed."""
    if not decisions.remove(db, CARD_KIND, key, DISMISSED):
        return False
    generations.bump_data_version(db, RESOURCE)
    return True
