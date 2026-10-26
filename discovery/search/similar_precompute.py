"""Daily precompute of similar artists for the library (contract sections 5.2 and 7, P3b).

Each library artist goes through the on-demand path with ``refresh=True``, so a complete result
overwrites the cached entry. A partial or failed result writes nothing, which keeps the previous
entry (contract section 5.2). The run stops at its time budget; artists it does not reach keep
their entries and are reached on a later run.

The network and the owned data are injected, so the scheduling stays in the app layer.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from discovery.search.artist_sections import ArtistNetwork, similar_items
from discovery.search.merge import OwnedKeys

PRECOMPUTE_BUDGET_SECONDS = 6 * 60 * 60
PRECOMPUTE_ARTIST_SECONDS = 120.0


def run_precompute(
    artists: Sequence[Mapping[str, Any]],
    network: ArtistNetwork,
    owned: OwnedKeys,
    *,
    clock: Callable[[], float] = time.monotonic,
    budget_seconds: float = PRECOMPUTE_BUDGET_SECONDS,
    artist_seconds: float = PRECOMPUTE_ARTIST_SECONDS,
    similar: Callable[..., dict[str, Any]] = similar_items,
) -> dict[str, int]:
    """Compute and store similar artists for each artist, in order, until the budget ends.

    Returns counts only: ``complete`` (stored), ``partial`` and ``unavailable`` (nothing stored),
    ``failed`` (an exception; nothing stored) and ``not_reached`` (budget ended first).
    """
    counts = {"complete": 0, "partial": 0, "unavailable": 0, "failed": 0, "not_reached": 0}
    stop_at = clock() + budget_seconds
    for position, artist in enumerate(artists):
        if clock() >= stop_at:
            counts["not_reached"] = len(artists) - position
            break
        deadline_at = clock() + artist_seconds
        try:
            section = similar(
                network,
                artist["name"],
                artist["id"],
                owned,
                remaining=lambda deadline_at=deadline_at: deadline_at - clock(),
                cancelled=threading.Event(),
                known_mbid=artist.get("mbid"),
                refresh=True,
            )
        except Exception:
            counts["failed"] += 1
            continue
        if not section["available"]:
            counts["unavailable"] += 1
        elif section["complete"]:
            counts["complete"] += 1
        else:
            counts["partial"] += 1
    return counts
