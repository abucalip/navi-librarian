"""Listens per UTC day for the Home "Listens last 7 days" stat (redesign D2, docs/SERVER_V2_CONTRACT.md).

A pure builder plus one live ``taste_listens_by_day`` row in ``insights`` (no migration), saved by the taste
refresh from the listens it already read. Nothing here fetches data, calls a provider or touches ranking.

The series has one ``{date, count}`` entry for each of the ``DAYS`` complete UTC days before the day of
``now`` (oldest first), zero days included, so a client can compare the last 7 days with the 7 before.
A listen older or newer than that span is not counted, and a listen with no timestamp never reaches here.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Iterable

from ..store import generations
from .profiles import Listen

KIND = "taste_listens_by_day"
RESOURCE = "insights"
DAYS = 84
DAY = 86400


def _date(day_start: float) -> str:
    return datetime.fromtimestamp(day_start, timezone.utc).strftime("%Y-%m-%d")


def build_listens_by_day(listens: Iterable[Listen], now: float, days: int = DAYS) -> list[dict[str, Any]]:
    """Counts for the ``days`` complete UTC days before the day of ``now``, oldest first, zero days included."""
    today = int(now // DAY)
    first = today - days
    counts = [0] * days
    for item in listens:
        day = int(item.ts // DAY)
        if first <= day < today:
            counts[day - first] += 1
    return [{"date": _date((first + i) * DAY), "count": n} for i, n in enumerate(counts)]


def save_listens_by_day(db: sqlite3.Connection, series: list[dict[str, Any]], now: float | None = None) -> bool:
    """Replace the live row. Returns False when the series is unchanged (nothing written)."""
    now = time.time() if now is None else now
    payload = json.dumps({"kind": KIND, "listens_by_day": series}, sort_keys=True)
    row = db.execute("SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL", (KIND,)).fetchone()
    if row is not None and row["payload"] == payload:
        return False
    with db:
        generation = generations.current_generation(db)
        db.execute("DELETE FROM insights WHERE kind = ?", (KIND,))
        db.execute(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
            "VALUES (?, NULL, ?, '[]', ?, ?)",
            (KIND, payload, generation, now),
        )
    generations.bump_data_version(db, RESOURCE)
    return True


def load_listens_by_day(db: sqlite3.Connection) -> list[dict[str, Any]] | None:
    """The saved series, or None when no refresh has saved one (the taste body then omits the field)."""
    row = db.execute("SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL "
                     "ORDER BY id DESC LIMIT 1", (KIND,)).fetchone()
    return None if row is None else json.loads(row["payload"])["listens_by_day"]
