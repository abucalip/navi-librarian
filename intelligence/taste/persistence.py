"""Persist computed taste profiles in the ``insights`` table (Phase 6 item 1, slice 3; no migration).

One live row of kind ``taste_profile`` holds the latest profiles and the loader's counts, so the
numbers a client shows can be reproduced and explained. ``subject_id`` stays NULL. A new save replaces
the previous row; an unchanged payload is not rewritten and does not bump the data version, so
ETags stay stable between identical runs. Nothing here fetches data, and nothing here touches
ownership flags or recommendation weights.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from typing import Any

from ..store import generations
from .headline import build_headline
from .loader import LoadResult
from .profiles import TasteProfiles

CARD_KIND = "taste_profile"
RESOURCE = "insights"


def profiles_payload(profiles: TasteProfiles, load: LoadResult | None = None) -> dict[str, Any]:
    """Plain JSON body for the profiles: windows, stated shifts, the headline, thresholds and (optionally) loader counts."""
    headline = build_headline(profiles)
    body: dict[str, Any] = {
        "kind": CARD_KIND,
        "headline": headline.as_dict() if headline is not None else None,
        "windows": {
            name: {
                "listens": w.listens,
                "low_sample": w.low_sample,
                "attributed": dict(w.attributed),
                "dimension_low_sample": dict(w.dimension_low_sample),
                "dimensions": {d: [asdict(e) for e in entries] for d, entries in w.dimensions.items()},
            }
            for name, w in profiles.windows.items()
        },
        "shifts": [asdict(s) for s in profiles.shifts],
        "config": asdict(profiles.config),
    }
    if load is not None:
        body["load"] = {"total": load.total, "unusable": load.unusable, "unmatched": load.unmatched,
                        "attributed": dict(load.attributed)}
    return body


def save_profiles(db: sqlite3.Connection, profiles: TasteProfiles, load: LoadResult | None = None,
                  now: float | None = None) -> bool:
    """Replace the live taste profile row. Returns False when the payload is unchanged (nothing written)."""
    now = time.time() if now is None else now
    payload = json.dumps(profiles_payload(profiles, load), sort_keys=True)
    row = db.execute("SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL", (CARD_KIND,)).fetchone()
    if row is not None and row["payload"] == payload:
        return False
    with db:
        generation = generations.current_generation(db)
        db.execute("DELETE FROM insights WHERE kind = ?", (CARD_KIND,))
        db.execute(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
            "VALUES (?, NULL, ?, '[]', ?, ?)",
            (CARD_KIND, payload, generation, now),
        )
    generations.bump_data_version(db, RESOURCE)
    return True


def load_saved_profiles(db: sqlite3.Connection) -> dict[str, Any] | None:
    """The saved profiles with ``computed_at`` and ``generation``, or None when none were computed yet."""
    row = db.execute(
        "SELECT payload, generation, computed_at FROM insights WHERE kind = ? AND dismissed_state IS NULL "
        "ORDER BY id DESC LIMIT 1", (CARD_KIND,)).fetchone()
    if row is None:
        return None
    body = json.loads(row["payload"])
    body["computed_at"] = row["computed_at"]
    body["generation"] = row["generation"]
    return body
