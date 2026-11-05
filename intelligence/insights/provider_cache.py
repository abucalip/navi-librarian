"""Provider document cache for the insight lenses, kept in the store's ``meta`` table (no migration).

One row per ``(kind, id)``: ``{"fetched_at": <epoch>, "doc": <document or null>}``. A ``null`` document
is a remembered "the provider has nothing" so a 404 is not asked again until it goes stale. Markers
(a document of ``{}``) record that a step ran. Nothing here touches the network.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

PREFIX = "doc:"
DAY = 86400.0


def _key(kind: str, ident: str) -> str:
    return f"{PREFIX}{kind}:{str(ident).lower()}"


def get(db: sqlite3.Connection, kind: str, ident: str) -> tuple[float, Any] | None:
    """``(fetched_at, document)`` or None when never stored."""
    row = db.execute("SELECT value FROM meta WHERE key = ?", (_key(kind, ident),)).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(row["value"])
        return float(data["fetched_at"]), data.get("doc")
    except (ValueError, KeyError, TypeError):
        return None


def put(db: sqlite3.Connection, kind: str, ident: str, doc: Any, now: float) -> None:
    value = json.dumps({"fetched_at": now, "doc": doc}, sort_keys=True)
    with db:
        db.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_key(kind, ident), value),
        )


def is_fresh(entry: tuple[float, Any] | None, now: float, ttl: float) -> bool:
    return entry is not None and now - entry[0] < ttl
