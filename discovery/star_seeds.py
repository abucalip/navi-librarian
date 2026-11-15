"""Navidrome stars as a taste seed (Star Operation, S3b).

A starred artist, or the artist of a starred album, adds a decayed weight to the same
seed map that saves and "More like this" use, so it can steer which supplementary tag
queries run. A star never makes an owned album a candidate and never adds a query
(the caller keeps the existing query budget). Pure, apart from the cached read in
``cached_starred``, whose callables are injected.

The constants are stated policy, proposed for the owner's approval after the replay
comparison; they are not fixture-calibrated quality claims. The setting is on by default (owner decision, 2026-11-15).
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

from integrations.navidrome.starred import fetch_starred

# Equal to a save's seed weight (SAVE_SEED_WEIGHT is 1.0), by owner decision (2026-11-15).
# A star lasts longer than a save, so it decays more slowly below.
STAR_SEED_WEIGHT = 1.0
# A star is a standing judgement, so it decays slower and expires later than a save.
STAR_HALF_LIFE_SECONDS = 180 * 24 * 60 * 60
STAR_EXPIRY_SECONDS = 365 * 24 * 60 * 60
# Navidrome sometimes gives no star date; such a star counts at a flat fraction of the weight.
UNDATED_STAR_FACTOR = 0.5
# One request per cache window, shared by every recommendation run in it.
STARRED_CACHE_KEY = "navidrome:starred"
STARRED_CACHE_TTL_SECONDS = 6 * 60 * 60


def _star_weight(starred_at: Any, now: float) -> float:
    """Decayed seed weight of one star, 0 once it is past the expiry window."""
    if starred_at is None:
        return STAR_SEED_WEIGHT * UNDATED_STAR_FACTOR
    try:
        age = float(now) - float(starred_at)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(age) or age < 0 or age > STAR_EXPIRY_SECONDS:
        return 0.0
    return STAR_SEED_WEIGHT * 2.0 ** (-age / STAR_HALF_LIFE_SECONDS)


def starred_seed_weights(
    starred: Mapping[str, Any],
    music_key: Callable[[str], str],
    *,
    now: float,
) -> dict[str, float]:
    """Return artist_key -> seed weight from parsed starred artists and albums.

    The larger weight wins per artist, as with saves. Rows with no artist name are skipped.
    """
    seeds: dict[str, float] = {}
    rows = [(row.get("name"), row) for row in starred.get("artists") or []]
    rows += [(row.get("artist"), row) for row in starred.get("albums") or []]
    for name, row in rows:
        key = music_key(name) if isinstance(name, str) and name.strip() else ""
        weight = _star_weight(row.get("starred_at"), now)
        if key and weight > 0.0:
            seeds[key] = max(seeds.get(key, 0.0), weight)
    return seeds


def cached_starred(
    api_call: Callable[..., dict[str, Any]],
    items: Callable[[Any], list[Any]],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], Any],
) -> dict[str, list[dict[str, Any]]]:
    """Starred artists and albums, from the metadata cache while it is fresh.

    A miss costs one ``getStarred2`` call. Errors from the call propagate."""
    cached = cache_get(STARRED_CACHE_KEY, ttl_seconds=STARRED_CACHE_TTL_SECONDS)
    if isinstance(cached, dict) and isinstance(cached.get("artists"), list) \
            and isinstance(cached.get("albums"), list):
        return cached
    starred = fetch_starred(api_call, items)
    cache_set(STARRED_CACHE_KEY, starred)
    return starred

