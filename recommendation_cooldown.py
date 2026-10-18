"""Soft, time-limited repeat penalty for personal recommendation ranking.

This policy only adjusts the score of candidates that have already passed the
hard ownership gate. It never excludes an item. Defaults are explicit policy
constants, not fixture-calibrated quality claims.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from discovery_store import recommendation_identity_hash

COOLDOWN_HALF_LIFE_SECONDS = 7 * 24 * 60 * 60
COOLDOWN_EXPIRY_SECONDS = 30 * 24 * 60 * 60
COOLDOWN_PER_EXPOSURE = 0.10
COOLDOWN_MAX_PENALTY = 0.25
MAX_BATCH_RANK = 20


def cooldown_adjusted_score(
    score: float,
    artist: str,
    album: str,
    history: Iterable[Mapping[str, Any]],
    *,
    now: float,
) -> float:
    """Return a deterministic, bounded score adjustment for recent repeats.

    Each prior exposure contributes up to 10%, weighted by its rank (rank 1
    has full weight, rank 20 has 5%) and decayed with a seven-day half-life.
    Contributions sum to at most a 25% penalty. Entries older than 30 days,
    future-dated entries, malformed rows, and other identities are ignored.
    The caller is responsible for applying this only to ownership-clear items.
    """
    value = float(score)
    timestamp = float(now)
    if not math.isfinite(value):
        raise ValueError("score must be finite")
    if not math.isfinite(timestamp):
        raise ValueError("now must be finite")

    identity_hash = recommendation_identity_hash({"artist": artist, "album": album})
    if identity_hash is None:
        return value

    penalty = 0.0
    for row in history:
        if not isinstance(row, Mapping) or row.get("identity_hash") != identity_hash:
            continue
        try:
            seen_at = float(row["generated_at"])
            rank = row["rank"]
            if (
                not math.isfinite(seen_at)
                or isinstance(rank, bool)
                or not isinstance(rank, int)
                or not 1 <= rank <= MAX_BATCH_RANK
            ):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        age = timestamp - seen_at
        if age < 0 or age > COOLDOWN_EXPIRY_SECONDS:
            continue
        rank_weight = (MAX_BATCH_RANK + 1 - rank) / MAX_BATCH_RANK
        decay = 2.0 ** (-age / COOLDOWN_HALF_LIFE_SECONDS)
        penalty += COOLDOWN_PER_EXPOSURE * rank_weight * decay
        if penalty >= COOLDOWN_MAX_PENALTY:
            penalty = COOLDOWN_MAX_PENALTY
            break

    return value * (1.0 - penalty)
