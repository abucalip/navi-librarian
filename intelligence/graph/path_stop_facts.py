"""Years together and shared albums for an artist path stop (Index theme I0).

Pure reads of the knowledge store: no provider call, no write. Used for the ``sideman_to_leader`` kind, whose
stops are artists and whose reasons name the release (``via``) the start played on and the stop led.
"""
from __future__ import annotations

import sqlite3
from typing import Any

MAX_SHARED_ALBUMS = 12


def _year(text: str | None) -> int | None:
    head = (text or "")[:4]
    return int(head) if head.isdigit() and int(head) > 0 else None


def shared_albums(db: sqlite3.Connection, release_ids: list[int]) -> list[dict[str, Any]]:
    """The releases behind a stop's reasons as ``{album, year, owned}``, oldest first (undated last), one per title."""
    ids = list(dict.fromkeys(i for i in release_ids if i is not None))
    if not ids:
        return []
    marks = ", ".join("?" for _ in ids)
    rows = db.execute(
        f"SELECT r.canonical_name AS name, r.owned AS owned, f.date AS date FROM entities r "
        f"LEFT JOIN release_facts f ON f.entity_id = r.id WHERE r.type = 'release' AND r.id IN ({marks})",
        ids,
    ).fetchall()
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row["name"] or ""
        if not name:
            continue
        item = {"album": name, "year": _year(row["date"]), "owned": bool(row["owned"])}
        kept = best.get(name.casefold())
        if kept is None:
            best[name.casefold()] = item
            continue
        kept["owned"] = kept["owned"] or item["owned"]
        if item["year"] and (kept["year"] is None or item["year"] < kept["year"]):
            kept["year"] = item["year"]
    ordered = sorted(best.values(), key=lambda a: (a["year"] is None, a["year"] or 0, a["album"].casefold()))
    return ordered[:MAX_SHARED_ALBUMS]


def years_together(albums: list[dict[str, Any]]) -> dict[str, int] | None:
    """The first and last year of the dated shared albums, or None when none is dated."""
    years = [a["year"] for a in albums if a.get("year")]
    return {"from": min(years), "to": max(years)} if years else None
