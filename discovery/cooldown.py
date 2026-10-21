"""Soft, time-limited repeat penalty for personal recommendation ranking.

This policy only adjusts the score of candidates that have already passed the
hard ownership gate. It never excludes an item or changes candidate count.
Defaults are explicit policy constants, not fixture-calibrated quality claims.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from discovery.store import recommendation_identity_hash

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



def read_history_for_cooldown(database_path: str, *, now: float) -> list[dict[str, Any]]:
    """Read the exact history input for ranking, preserving fail-open behavior."""
    import sqlite3
    from discovery.store import recent_recommendation_history

    try:
        return recent_recommendation_history(database_path, now=now)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        # History is a soft preference; storage failures must not block discovery.
        return []


def apply_history_cooldown(
    allocation_candidates: Iterable[Any],
    candidate_by_id: Mapping[str, Mapping[str, Any]],
    database_path: str,
    *,
    now: float,
    history_override: Iterable[Mapping[str, Any]] | None = None,
) -> list[Any]:
    """Apply cooldown to ownership-clear allocation inputs, failing open on storage errors."""
    from dataclasses import replace

    candidates = list(allocation_candidates)
    history = list(history_override) if history_override is not None else read_history_for_cooldown(database_path, now=now)
    if not history:
        return candidates

    adjusted = []
    for candidate in candidates:
        if getattr(candidate.ownership, "value", None) != "clear":
            adjusted.append(candidate)
            continue
        source = candidate_by_id.get(candidate.candidate_id)
        if not isinstance(source, Mapping):
            adjusted.append(candidate)
            continue
        score = cooldown_adjusted_score(
            candidate.score,
            str(source.get("artist") or source.get("primary_artist") or ""),
            str(source.get("album") or ""),
            history,
            now=now,
        )
        adjusted.append(replace(candidate, score=score))
    return adjusted



def prepare_ranking_inputs(
    allocation_candidates: Iterable[Any],
    candidate_by_id: Mapping[str, Mapping[str, Any]],
    database_path: str,
    ranking_context_override: Mapping[str, Any] | None,
    *,
    now_fn: Callable[[], float],
    diversity_setting_fn: Callable[[], int],
    feedback_fn: Callable[[], list[dict[str, Any]]] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Resolve frozen or live ranking inputs and return cooldown-adjusted candidates.

    Feedback is frozen into the context only when the signal is enabled or the
    override already carries it, so captures without feedback keep their shape.
    """
    from recommendation_feedback import FEEDBACK_SIGNAL_ENABLED, apply_feedback_signal

    if ranking_context_override is None:
        ranking_now = now_fn()
        ranking_history = read_history_for_cooldown(database_path, now=ranking_now)
        diversity_setting = diversity_setting_fn()
        feedback = feedback_fn() if FEEDBACK_SIGNAL_ENABLED and feedback_fn is not None else None
    else:
        ranking_now = float(ranking_context_override["ranking_now"])
        ranking_history = list(ranking_context_override["history"])
        diversity_setting = ranking_context_override["diversity_setting"]
        feedback = ranking_context_override.get("feedback")
    context = {
        "ranking_now": ranking_now,
        "history": ranking_history,
        "diversity_setting": diversity_setting,
    }
    adjusted = apply_history_cooldown(
        allocation_candidates, candidate_by_id, database_path,
        now=ranking_now, history_override=ranking_history,
    )
    if feedback is not None:
        context["feedback"] = list(feedback)
        adjusted = apply_feedback_signal(adjusted, candidate_by_id, feedback, now=ranking_now)
    return adjusted, context
