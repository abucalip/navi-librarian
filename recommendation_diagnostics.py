"""Deterministic metrics for frozen recommendation replay fixtures."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


def jaccard_overlap(left: Sequence[str], right: Sequence[str]) -> float | None:
    """Return set Jaccard overlap, or None when both sets are empty."""
    a, b = set(left), set(right)
    if not a and not b:
        return None
    return round(len(a & b) / len(a | b), 6)


def _fingerprint(values: Sequence[str]) -> str:
    import hashlib
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


def evaluate_replay_case(case: Mapping[str, Any], *, k: int = 10) -> dict[str, Any]:
    """Score a frozen T-to-T+14-day replay case without provider access.

    Future-window listens are evaluation outcomes only and must not be included
    in profile or candidate-generation inputs for the replay timestamp.
    """
    if k < 1:
        raise ValueError("k must be positive")
    ranked = list(case.get("recommendations", []))[:k]
    future = {str(value) for value in case.get("future_listened_unowned_artists", [])}
    owned = {str(value) for value in case.get("owned_artists", [])}
    eligible = [item for item in ranked if str(item.get("artist", "")) not in owned]
    relevant_ranks = [rank for rank, item in enumerate(eligible, start=1)
                      if str(item.get("artist", "")) in future]
    hit_rate = len(relevant_ranks) / len(eligible) if eligible else 0.0
    dcg = sum(1.0 / math.log2(rank + 1) for rank in relevant_ranks)
    ideal = sum(1.0 / math.log2(rank + 1)
                for rank in range(1, min(len(future), len(eligible)) + 1))
    styles = {str(item.get("style", "unknown")) for item in eligible}
    artists = [str(item.get("artist", "")) for item in eligible]
    return {
        "case_id": str(case.get("case_id", "unnamed")),
        "recommendations_evaluated": len(eligible),
        "artist_hit_rate_at_k": round(hit_rate, 6),
        "artist_ndcg_at_k": round(dcg / ideal, 6) if ideal else 0.0,
        "unique_artists": len(set(artists)),
        "style_spread": len(styles - {"unknown", ""}),
        "owned_artist_recommendations_excluded": len(ranked) - len(eligible),
        "eligibility_rejections": int(case.get("eligibility_rejections", 0)),
        "ambiguous_releases": int(case.get("ambiguous_releases", 0)),
        "ranking_fingerprint": _fingerprint([str(item.get("album_key", "")) for item in eligible]),
    }


def evaluate_replay_fixture(fixture: Mapping[str, Any], *, k: int = 10) -> dict[str, Any]:
    """Evaluate cases and compare candidate/ranking responsiveness."""
    cases = [evaluate_replay_case(case, k=k) for case in fixture.get("cases", [])]
    inputs = list(fixture.get("cases", []))
    pool_overlaps, ranking_overlaps = [], []
    for index, left in enumerate(inputs):
        for right in inputs[index + 1:]:
            pool_overlap = jaccard_overlap(left.get("candidate_pool_keys", []), right.get("candidate_pool_keys", []))
            ranking_overlap = jaccard_overlap(
                [str(item.get("album_key", "")) for item in left.get("recommendations", [])[:k]],
                [str(item.get("album_key", "")) for item in right.get("recommendations", [])[:k]],
            )
            if pool_overlap is not None:
                pool_overlaps.append(pool_overlap)
            if ranking_overlap is not None:
                ranking_overlaps.append(ranking_overlap)
    return {
        "fixture_version": fixture.get("version", 1),
        "cases": cases,
        "case_count": len(cases),
        "mean_artist_hit_rate_at_k": round(sum(x["artist_hit_rate_at_k"] for x in cases) / len(cases), 6) if cases else 0.0,
        "mean_artist_ndcg_at_k": round(sum(x["artist_ndcg_at_k"] for x in cases) / len(cases), 6) if cases else 0.0,
        "mean_candidate_pool_overlap": round(sum(pool_overlaps) / len(pool_overlaps), 6) if pool_overlaps else None,
        "mean_ranking_overlap": round(sum(ranking_overlaps) / len(ranking_overlaps), 6) if ranking_overlaps else None,
        "deterministic": True,
        "fixture_limitations": fixture.get("limitations", []),
    }
