"""``/api/insights/taste`` body: the saved taste profiles (docs/SERVER_V2_CONTRACT.md, Phase 6 item 1).

A pure builder over the saved row. ``profiles`` is null until a run has saved some, so clients can
tell "not computed yet" from "computed, but low sample" (the per-window and per-dimension
``low_sample`` flags). Nothing here fetches data, writes, or touches recommendation weights.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..store import generations
from ..taste.context_persistence import load_saved_context
from ..taste.listens_by_day import load_listens_by_day
from ..taste.persistence import load_saved_profiles


def build_taste_body(db: sqlite3.Connection) -> dict[str, Any]:
    body = {
        "profiles": load_saved_profiles(db),
        "context": load_saved_context(db),
        "data_version": generations.data_versions(db).get("insights", 0),
        "generation": generations.current_generation(db),
    }
    series = load_listens_by_day(db)
    if series is not None:   # absent, not empty, until a refresh has saved it (redesign D2)
        body["listens_by_day"] = series
    return body
