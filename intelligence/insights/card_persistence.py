"""Persist series, hidden-canon and anniversary cards and dismissals in the ``insights`` table.

Same pattern as :mod:`.blind_spot_persistence` (no migration): a live card is a generic insight
card with ``subject_id`` NULL, keyed by its ``subject.key``. A dismissed row is the per-user
suppression memory; it survives every refresh, and its key is what the finders receive as
``dismissed`` (via the ``dismissed_*_keys`` helpers). Dismissing a key with no live card writes a
tombstone row so the dismissal still suppresses it later. Nothing here fetches data or touches
ownership flags or recommendation weights.

The three kinds share one core keyed by ``kind``; the public functions are thin wrappers so
callers cannot mix up kinds. Keys are the finders' own ``dismiss_key`` form, passed in whole.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Iterable

from ..store import generations
from . import decisions
from .anniversaries import CARD_KIND as ANNIVERSARY_KIND, AnniversaryResult, anniversary_card
from .hidden_canon import CARD_KIND as CANON_KIND, CanonResult, canon_card
from .series_completion import CARD_KIND as SERIES_KIND, SeriesResult, series_card

DISMISSED = "dismissed"
RESOURCE = "insights"
_KEY = "json_extract(payload, '$.subject.key')"
_ORDER = "json_extract(payload, '$.score') DESC, json_extract(payload, '$.subject.key'), id"


def _dismissed(db: sqlite3.Connection, kind: str) -> set[str]:
    return decisions.keys(db, kind, DISMISSED)


def _save(db: sqlite3.Connection, kind: str, cards: Iterable[dict[str, Any]], now: float | None) -> int:
    now = time.time() if now is None else now
    blocked = _dismissed(db, kind)
    kept = [c for c in cards if c["subject"]["key"] not in blocked]
    with db:
        generation = generations.current_generation(db)
        db.execute("DELETE FROM insights WHERE kind = ? AND dismissed_state IS NULL", (kind,))
        db.executemany(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
            "VALUES (?, NULL, ?, ?, ?, ?)",
            [(kind, json.dumps(c, sort_keys=True), json.dumps(c["reasons"], sort_keys=True), generation, now)
             for c in kept],
        )
    generations.bump_data_version(db, RESOURCE)
    return len(kept)


def _list(db: sqlite3.Connection, kind: str, limit: int) -> list[dict[str, Any]]:
    blocked = _dismissed(db, kind)
    rows = db.execute(
        f"SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL ORDER BY {_ORDER}", (kind,)
    ).fetchall()
    cards = [json.loads(r["payload"]) for r in rows]
    return [c for c in cards if c["subject"]["key"] not in blocked][: max(limit, 0)]


def _dismiss(db: sqlite3.Connection, kind: str, key: str, now: float | None) -> bool:
    if not decisions.record(db, kind, key, DISMISSED, now, hide_live=True):
        return False
    generations.bump_data_version(db, RESOURCE)
    return True


def _restore(db: sqlite3.Connection, kind: str, key: str) -> bool:
    if not decisions.remove(db, kind, key, DISMISSED):
        return False
    generations.bump_data_version(db, RESOURCE)
    return True


# Series completion ------------------------------------------------------------------------------
def dismissed_series_keys(db: sqlite3.Connection) -> set[str]:
    """Dismissed keys in the ``series_completion:<set key>`` form ``find_series_progress`` expects."""
    return _dismissed(db, SERIES_KIND)


def save_series(db: sqlite3.Connection, result: SeriesResult, now: float | None = None) -> int:
    """Replace live series cards with ``result``; dismissed rows are kept. An empty result clears them."""
    return _save(db, SERIES_KIND, (series_card(p, result.config) for p in result.progress), now)


def list_series_cards(db: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    return _list(db, SERIES_KIND, limit)


def dismiss_series(db: sqlite3.Connection, key: str, now: float | None = None) -> bool:
    return _dismiss(db, SERIES_KIND, key, now)


def restore_series(db: sqlite3.Connection, key: str) -> bool:
    return _restore(db, SERIES_KIND, key)


# Hidden canon -----------------------------------------------------------------------------------
def dismissed_canon_keys(db: sqlite3.Connection) -> set[str]:
    """Dismissed keys in the ``hidden_canon:<group mbid>`` form ``find_hidden_canon`` expects."""
    return _dismissed(db, CANON_KIND)


def save_canon(db: sqlite3.Connection, result: CanonResult, now: float | None = None) -> int:
    return _save(db, CANON_KIND, (canon_card(p) for p in result.picks), now)


def list_canon_cards(db: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    return _list(db, CANON_KIND, limit)


def dismiss_canon(db: sqlite3.Connection, key: str, now: float | None = None) -> bool:
    return _dismiss(db, CANON_KIND, key, now)


def restore_canon(db: sqlite3.Connection, key: str) -> bool:
    return _restore(db, CANON_KIND, key)


# Anniversaries ----------------------------------------------------------------------------------
def dismissed_anniversary_keys(db: sqlite3.Connection) -> set[str]:
    """Dismissed keys in the ``anniversary:<kind>:<mbid>:<year>`` form ``find_anniversaries`` expects.

    The key includes the anniversary year, so dismissing this year's card does not hide the next.
    """
    return _dismissed(db, ANNIVERSARY_KIND)


def save_anniversaries(db: sqlite3.Connection, result: AnniversaryResult, now: float | None = None) -> int:
    return _save(db, ANNIVERSARY_KIND, (anniversary_card(i) for i in result.items), now)


def list_anniversary_cards(db: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    return _list(db, ANNIVERSARY_KIND, limit)


def dismiss_anniversary(db: sqlite3.Connection, key: str, now: float | None = None) -> bool:
    return _dismiss(db, ANNIVERSARY_KIND, key, now)


def restore_anniversary(db: sqlite3.Connection, key: str) -> bool:
    return _restore(db, ANNIVERSARY_KIND, key)
