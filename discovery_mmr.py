"""Deterministic, offline MMR-style re-ranking for personal discovery.

Callers must pass candidates that have already passed hard eligibility checks.
The re-ranker additionally enforces one album per artist in its shortlist.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


def _normalized_tags(values: Iterable[Any]) -> set[str]:
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def tag_jaccard(left: Iterable[Any], right: Iterable[Any]) -> float:
    """Return Jaccard similarity for normalized, case-insensitive tag sets."""
    a = _normalized_tags(left)
    b = _normalized_tags(right)
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def candidate_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    """Return artist/tag similarity without granting novelty for missing tags.

    Exact artist identity is authoritative. For different/unknown artists, an
    empty tag set means similarity is unknown, not evidence of dissimilarity.
    Return the conservative maximum so an untagged candidate cannot win an MMR
    tie merely because metadata is missing. Fully tagged candidates continue to
    use Jaccard similarity, including a zero score for genuinely disjoint tags.
    """
    left_artist = str(left.get("artist_key") or "").strip().casefold()
    right_artist = str(right.get("artist_key") or "").strip().casefold()
    if left_artist and right_artist and left_artist == right_artist:
        return 1.0
    left_tags = _normalized_tags(left.get("tags") or ())
    right_tags = _normalized_tags(right.get("tags") or ())
    if not left_tags or not right_tags:
        return 1.0
    return len(left_tags & right_tags) / len(left_tags | right_tags)


def diversity_setting_to_penalty(value: int) -> float:
    """Map the 0–100 user diversity setting to this implementation's penalty weight.

    Here lambda_ is the penalty subtracted for similarity, so larger values
    produce more diversification (unlike the relevance-weight convention used
    in some MMR descriptions). Keep this mapping pure and explicitly tested.
    """
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError("diversity setting must be an integer from 0 to 100")
    return value / 100.0


def mmr_rerank(
    candidates: Iterable[Mapping[str, Any]],
    *,
    limit: int,
    lambda_: float = 0.25,
    relevance_floor: float = 0.0,
) -> list[dict[str, Any]]:
    """Greedily balance normalized relevance and similarity to selected items.

    Relevance uses descending average ranks normalized to [0, 1], so raw score
    magnitude and isolated outliers do not set lambda's scale. Equal scores get
    equal relevance; selection ties are deterministic by original input order. A blank artist
    key is treated as a unique identity per candidate rather than merging
    unknowns. Input mappings are copied and never mutated.
    """
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a non-negative integer")
    if not math.isfinite(lambda_) or not 0.0 <= lambda_ <= 1.0:
        raise ValueError("lambda_ must be finite and between 0 and 1")
    if not math.isfinite(relevance_floor) or not 0.0 <= relevance_floor <= 1.0:
        raise ValueError("relevance_floor must be finite and between 0 and 1")

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
    ranked = sorted(pool, key=lambda item: item["_mmr_score"], reverse=True)
    rank_by_identity: dict[int, float] = {}
    start = 0
    while start < len(ranked):
        end = start + 1
        while end < len(ranked) and ranked[end]["_mmr_score"] == ranked[start]["_mmr_score"]:
            end += 1
        average_rank = (start + end - 1) / 2.0
        for item in ranked[start:end]:
            rank_by_identity[id(item)] = average_rank
        start = end
    denominator = max(1, len(ranked) - 1)
    constant_pool = ranked[0]["_mmr_score"] == ranked[-1]["_mmr_score"]
    for item in pool:
        item["_mmr_relevance"] = (
            1.0 if constant_pool else 1.0 - rank_by_identity[id(item)] / denominator
        )

    selected: list[dict[str, Any]] = []
    selected_artists: set[str] = set()
    remaining = [item for item in pool if item["_mmr_relevance"] >= relevance_floor]
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
