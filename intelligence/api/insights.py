"""``/api/insights`` body: generic insight cards for every Phase 3 lens (docs/SERVER_V2_CONTRACT.md).

A pure builder. Saved cards are read from the store, but a lens contributes cards only when the
caller lists it in ``enabled`` (the scorecard rule: only a lens whose verdict is ``pass`` is on by
default, and today none is). A lens that is off still appears with ``enabled: false`` and no cards,
so clients can tell "off" from "on but nothing to show". Nothing here fetches data, writes, or
touches ownership flags or recommendation weights.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Callable, Iterable

from ..insights import (
    list_anniversary_cards, list_blind_spot_cards, list_canon_cards, list_gem_cards, list_series_cards,
)
from ..insights.anniversaries import CARD_KIND as ANNIVERSARY_KIND
from ..insights.blind_spots import CARD_KIND as BLIND_SPOT_KIND
from ..insights.forgotten_gems import CARD_KIND as GEM_KIND
from ..insights.hidden_canon import CARD_KIND as CANON_KIND
from ..insights.series_completion import CARD_KIND as SERIES_KIND
from ..store import generations

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

LISTERS: dict[str, Callable[[sqlite3.Connection, int], list[dict[str, Any]]]] = {
    GEM_KIND: list_gem_cards,
    BLIND_SPOT_KIND: list_blind_spot_cards,
    SERIES_KIND: list_series_cards,
    CANON_KIND: list_canon_cards,
    ANNIVERSARY_KIND: list_anniversary_cards,
}


def build_insights_body(
    db: sqlite3.Connection, *, enabled: Iterable[str] = (), limit: int = DEFAULT_LIMIT
) -> dict[str, Any]:
    """Saved cards per lens; lenses not in ``enabled`` carry no cards. Unknown names are ignored."""
    limit = min(max(int(limit), 1), MAX_LIMIT)
    on = set(enabled)
    lenses = {
        kind: {"enabled": kind in on, "cards": lister(db, limit) if kind in on else []}
        for kind, lister in sorted(LISTERS.items())
    }
    return {
        "lenses": lenses,
        "data_version": generations.data_versions(db).get("insights", 0),
        "generation": generations.current_generation(db),
    }
