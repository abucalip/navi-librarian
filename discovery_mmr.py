"""Deterministic, offline MMR-style re-ranking for personal discovery.

Callers must pass candidates that have already passed hard eligibility checks.
The re-ranker additionally enforces one album per artist in its shortlist.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


def tag_jaccard(left: Iterable[Any], right: Iterable[Any]) -> float:
    """Return Jaccard similarity for normalized, case-insensitive tag sets."""
    a = {str(value).strip().casefold() for value in left if str(value).strip()}
    b = {str(value).strip().casefold() for value in right if str(value).strip()}
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def candidate_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    """Use exact artist identity first, otherwise genre-tag Jaccard overlap."""
    left_artist = str(left.get("artist_key") or "").strip().casefold()
    right_artist = str(right.get("artist_key") or "").strip().casefold()
    if left_artist and right_artist and left_artist == right_artist:
        return 1.0
    return tag_jaccard(left.get("tags") or (), right.get("tags") or ())


def mmr_rerank(
    candidates: Iterable[Mapping[str, Any]],
    *,
    limit: int,
    lambda_: float = 0.25,
) -> list[dict[str, Any]]:
    """Greedily balance normalized relevance and similarity to selected items.

    Scores are min-max normalized within the pool so lambda has a bounded
    scale. Ties are deterministic: original input order wins. A blank artist
    key is treated as a unique identity per candidate rather than merging
    unknowns. Input mappings are copied and never mutated.
    """
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a non-negative integer")
    if not math.isfinite(lambda_) or not 0.0 <= lambda_ <= 1.0:
        raise ValueError("lambda_ must be finite and between 0 and 1")

    pool: list[dict[str, Any]] = []
    for index, source in enumerate(candidates):
        item = dict(source)
        try:
            score = float(item["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("every candidate must have a numeric score") from exc
        if not math.isfinite(score):
            raise ValueError("candidate scores must be finite")
        item["_mmr_input_order"] = index
        item["_mmr_score"] = score
        pool.append(item)

    if not pool or limit == 0:
        return []
    scores = [item["_mmr_score"] for item in pool]
    low, high = min(scores), max(scores)
    span = high - low
    for item in pool:
        item["_mmr_relevance"] = 1.0 if span == 0.0 else (item["_mmr_score"] - low) / span

    selected: list[dict[str, Any]] = []
    selected_artists: set[str] = set()
    remaining = list(pool)
    while remaining and len(selected) < limit:
        best_index: int | None = None
        best_value = -math.inf
        for index, item in enumerate(remaining):
            artist = str(item.get("artist_key") or "").strip().casefold()
            if artist and artist in selected_artists:
                continue
            similarity = max(
                (candidate_similarity(item, chosen) for chosen in selected),
                default=0.0,
            )
            value = item["_mmr_relevance"] - lambda_ * similarity
            if value > best_value:
                best_value = value
                best_index = index
        if best_index is None:
            break
        chosen = remaining.pop(best_index)
        selected.append(chosen)
        artist = str(chosen.get("artist_key") or "").strip().casefold()
        if artist:
            selected_artists.add(artist)

    for item in selected:
        item.pop("_mmr_input_order", None)
        item.pop("_mmr_score", None)
        item.pop("_mmr_relevance", None)
    return selected


def diversity_metrics(candidates: Iterable[Mapping[str, Any]]) -> dict[str, float | int]:
    """Summarize shortlist diversity and relevance for offline comparisons."""
    items = list(candidates)
    artists = [str(item.get("artist_key") or "").strip().casefold() for item in items]
    similarities = [
        candidate_similarity(items[i], items[j])
        for i in range(len(items))
        for j in range(i + 1, len(items))
    ]
    scores = []
    for item in items:
        try:
            score = float(item["score"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(score):
            scores.append(score)
    return {
        "count": len(items),
        "unique_artists": len({artist for artist in artists if artist}),
        "mean_pairwise_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
        "mean_relevance_score": sum(scores) / len(scores) if scores else 0.0,
    }
