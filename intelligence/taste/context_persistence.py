"""Persist the listening-context profiles and a stated morning-vs-night contrast (Phase 6 presentation slice 4).

One live ``taste_context`` row in ``insights`` (no migration) holds both lenses of
``build_context_profiles`` and the contrast. A new save replaces the row; an unchanged payload is
not rewritten and does not bump the data version. Nothing here fetches data or touches ranking.

Contrast honesty: a contrast between ``morning`` and ``night`` is stated for a dimension only when
both contexts hold at least ``CONTRAST_MIN_LISTENS`` listens and both are sound for that dimension
(``min_attributed``). A value is listed only when its share differs by at least ``min_shift``.
Otherwise the contrast carries a ``state`` of ``low_sample`` and no entries.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from typing import Any

from ..store import generations
from .context import ContextProfiles
from .profiles import DIMENSIONS, ProfileConfig, WindowProfile

CONTEXT_KIND = "taste_context"
RESOURCE = "insights"
CONTRAST_MIN_LISTENS = 100   # starting value, not measured; stricter than ProfileConfig.min_listens
CONTRAST_PAIR = ("morning", "night")


def _shares(profile: WindowProfile, dim: str) -> dict[str, float]:
    return {e.value: e.share for e in profile.dimensions.get(dim, ())}


def build_contrast(ctx: ContextProfiles, config: ProfileConfig | None = None) -> dict[str, Any]:
    c = config or ProfileConfig()
    a, b = (ctx.lenses["time_of_day"][name] for name in CONTRAST_PAIR)
    out: dict[str, Any] = {"between": list(CONTRAST_PAIR), "min_listens": CONTRAST_MIN_LISTENS,
                           "listens": {CONTRAST_PAIR[0]: a.listens, CONTRAST_PAIR[1]: b.listens}}
    if a.listens < CONTRAST_MIN_LISTENS or b.listens < CONTRAST_MIN_LISTENS:
        return {**out, "state": "low_sample", "entries": []}
    entries = []
    for dim in DIMENSIONS:
        if a.dimension_low_sample.get(dim, True) or b.dimension_low_sample.get(dim, True):
            continue
        sa, sb = _shares(a, dim), _shares(b, dim)
        for value in sorted(set(sa) | set(sb)):
            first, second = sa.get(value, 0.0), sb.get(value, 0.0)
            if abs(first - second) >= c.min_shift:
                entries.append({"dimension": dim, "value": value, CONTRAST_PAIR[0]: first,
                                CONTRAST_PAIR[1]: second})
    entries.sort(key=lambda e: (-abs(e[CONTRAST_PAIR[0]] - e[CONTRAST_PAIR[1]]), e["dimension"], e["value"]))
    return {**out, "state": "stated" if entries else "no_difference", "entries": entries}


def context_payload(ctx: ContextProfiles, config: ProfileConfig | None = None) -> dict[str, Any]:
    return {
        "kind": CONTEXT_KIND,
        "timezone": ctx.timezone,
        "listens": ctx.listens,
        "lenses": {
            lens: {
                name: {
                    "listens": p.listens,
                    "low_sample": p.low_sample,
                    "attributed": dict(p.attributed),
                    "dimension_low_sample": dict(p.dimension_low_sample),
                    "dimensions": {d: [asdict(e) for e in entries] for d, entries in p.dimensions.items()},
                }
                for name, p in contexts.items()
            }
            for lens, contexts in ctx.lenses.items()
        },
        "contrast": build_contrast(ctx, config),
    }


def save_context_profiles(db: sqlite3.Connection, ctx: ContextProfiles, config: ProfileConfig | None = None,
                          now: float | None = None) -> bool:
    """Replace the live context row. Returns False when the payload is unchanged (nothing written)."""
    now = time.time() if now is None else now
    payload = json.dumps(context_payload(ctx, config), sort_keys=True)
    row = db.execute("SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL",
                     (CONTEXT_KIND,)).fetchone()
    if row is not None and row["payload"] == payload:
        return False
    with db:
        generation = generations.current_generation(db)
        db.execute("DELETE FROM insights WHERE kind = ?", (CONTEXT_KIND,))
        db.execute(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
            "VALUES (?, NULL, ?, '[]', ?, ?)",
            (CONTEXT_KIND, payload, generation, now),
        )
    generations.bump_data_version(db, RESOURCE)
    return True


def load_saved_context(db: sqlite3.Connection) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT payload, generation, computed_at FROM insights WHERE kind = ? AND dismissed_state IS NULL "
        "ORDER BY id DESC LIMIT 1", (CONTEXT_KIND,)).fetchone()
    if row is None:
        return None
    body = json.loads(row["payload"])
    body["computed_at"] = row["computed_at"]
    body["generation"] = row["generation"]
    return body
