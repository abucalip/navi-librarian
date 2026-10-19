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


def _numeric_summary(values: Sequence[Any]) -> dict[str, Any]:
    numbers = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(number):
            numbers.append(number)
    if not numbers:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(numbers),
        "min": round(min(numbers), 6),
        "mean": round(sum(numbers) / len(numbers), 6),
        "max": round(max(numbers), 6),
    }


def summarize_candidate_diagnostics(
    gathered: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return bounded aggregate telemetry without candidate identities or raw tags."""
    from collections import Counter

    rows = list(candidates)
    decisions = Counter(str(row.get("selection_decision") or "unknown") for row in rows)
    sources = Counter()
    allowed_sources = {
        "listenbrainz_cf", "profile_tag_search", "exploration_tag_search",
        "similar_artist_lookup", "library_gap", "new_release",
        "lastfm_popularity_fallback", "listenbrainz", "musicbrainz_tag_search",
    }
    for row in rows:
        provenance = row.get("discovery_sources")
        if isinstance(provenance, (list, tuple, set)):
            normalized = {
                str(source) for source in provenance if str(source) in allowed_sources
            }
            if normalized:
                sources.update(normalized)
                continue
        legacy_source = str(row.get("discovery_source") or "listenbrainz")
        sources[legacy_source if legacy_source in allowed_sources else "unknown"] += 1
    owned = sum(bool(row.get("exact_owned")) for row in rows)
    title_conflicts = sum(int(row.get("same_title_library_matches") or 0) > 0 for row in rows)
    unclassified = sum(row.get("assigned_category") == "unclassified" for row in rows)
    genre_available = sum(bool(row.get("genre_metadata_available")) for row in rows)
    raw_profile_counts = gathered.get("recent_family_counts") or {}
    valid_profile_counts = [
        max(0, int(value))
        for key, value in raw_profile_counts.items()
        if str(key) and isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    recent_counts = []
    familiarity_factors = []
    exploration_factors = []
    for row in rows:
        try:
            recent_count = max(0, int(row.get("recent_artist_play_count", 0)))
        except (TypeError, ValueError, OverflowError):
            recent_count = 0
        recent_counts.append(recent_count)
        familiarity_factors.append(
            1.35 if recent_count == 0 else
            1.20 if recent_count <= 2 else
            1.05 if recent_count <= 5 else
            0.90 if recent_count <= 10 else 0.75
        )
        exploration_factors.append(1.10 if row.get("exploration_family_match") else 1.0)

    return {
        "candidate_count": len(rows),
        "candidate_counts_by_source": dict(sorted(sources.items())),
        "score_components": {
            "base_score": _numeric_summary([row.get("score") for row in rows]),
            "familiarity_factor": _numeric_summary(familiarity_factors),
            "exploration_family_bonus": _numeric_summary(exploration_factors),
            "recent_artist_play_count": _numeric_summary(recent_counts),
            "final_discovery_score": _numeric_summary([row.get("discovery_score") for row in rows]),
            "recent_profile_bonus": _numeric_summary([row.get("recent_profile_bonus") for row in rows]),
            "lastfm_popularity_bonus": _numeric_summary([row.get("lastfm_popularity_bonus") for row in rows]),
        },
        "profile_evidence": {
            "listens_seen": len(gathered.get("listens") or []),
            "distinct_recent_artists": len(gathered.get("recent_artists") or {}),
            "artist_mbids_with_recent_listens": len(gathered.get("recent_artist_mbid_counts") or {}),
            "candidate_count_with_genre_metadata": genre_available,
            # Keep profile evidence useful without persisting raw family/tag names.
            "recent_family_count": len(valid_profile_counts),
            "recent_family_listen_count": sum(valid_profile_counts),
        },
        "eligibility_rejections": {
            "exact_owned": owned,
            "same_title_artist_conflicts": title_conflicts,
            "unclassified": unclassified,
            "selection_decisions": dict(sorted(decisions.items())),
        },
        # Gathering-stage aggregates (CF recording/album shares, supplementary yield).
        "candidate_supply": dict(gathered.get("candidate_supply") or {}),
        "cache": {
            "supplementary_hits": max(0, int(gathered.get("supplementary_cache_hits", 0))),
            "supplementary_misses": max(0, int(gathered.get("supplementary_cache_misses", 0))),
        },
    }


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
