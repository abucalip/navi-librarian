"""Evaluation metrics for lens lists and for the set of lists (docs/engine2.md).

Pure functions over allocation results and the candidates they refer to. They
describe a list (spread, score, tags, obscurity); they do not judge listening
quality.
"""
from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from statistics import median
from typing import Any, Mapping, Sequence

from discovery.allocation_contract import AllocationCandidate, AllocationResult
from discovery.mmr import tag_jaccard

DEFAULT_OBSCURE_CEILING = 50_000


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def lens_list_metrics(
    result: AllocationResult,
    candidates: Sequence[AllocationCandidate],
    *,
    obscure_ceiling: int = DEFAULT_OBSCURE_CEILING,
) -> dict[str, Any]:
    """Metrics for one list: families, entropy, tag overlap, score, obscurity."""
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    picks = [by_id[cid] for cid in result.selected_candidate_ids]
    families = Counter(pick.genre_family for pick in picks if pick.genre_family)
    tagged = sum(families.values())
    entropy = -sum((n / tagged) * math.log2(n / tagged) for n in families.values()) if tagged else 0.0
    pairs = [tag_jaccard(a.tags, b.tags) for a, b in combinations(picks, 2)
             if a.tags and b.tags]
    scores = [pick.score for pick in picks]
    audiences = [pick.audience for pick in picks if pick.audience is not None]
    return {
        "lens": result.lens,
        "size": len(picks),
        "distinct_families": len(families),
        "largest_family": max(families.values(), default=0),
        "family_entropy": _round(entropy),
        "mean_pairwise_tag_jaccard": _round(sum(pairs) / len(pairs)) if pairs else None,
        "mean_score": _round(sum(scores) / len(scores)) if scores else None,
        "min_score": _round(min(scores)) if scores else None,
        "untagged_picks": sum(1 for pick in picks if not pick.tags),
        "unknown_family_picks": sum(1 for pick in picks if not pick.genre_family),
        "adventurous_picks": sum(1 for pick in picks if pick.category == "adventurous"),
        "known_audience_picks": len(audiences),
        "median_audience": median(audiences) if audiences else None,
        "obscure_share": (_round(sum(1 for a in audiences if a <= obscure_ceiling) / len(audiences))
                          if audiences else None),
    }


def lens_set_metrics(
    results: Sequence[AllocationResult],
    candidates: Sequence[AllocationCandidate],
    *,
    reference: AllocationResult | None = None,
) -> dict[str, Any]:
    """Metrics across lists: union size and pairwise overlap of albums and artists.

    ``reference`` (for example the production list) adds each list's overlap with it.
    Albums are matched by ``album_key``; all results must refer to ``candidates``.
    """
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    # Albums are compared by normalized album identity, not by request-local IDs.
    ids = {r.lens: {by_id[cid].album_key for cid in r.selected_candidate_ids} for r in results}
    artists = {r.lens: {by_id[cid].artist_key for cid in r.selected_candidate_ids} for r in results}
    if len(ids) != len(results):
        raise ValueError("results must have unique lens names")

    def overlap(a: set, b: set) -> int:
        return len(a & b)

    pairwise = {
        f"{left}|{right}": {"albums": overlap(ids[left], ids[right]),
                            "artists": overlap(artists[left], artists[right])}
        for left, right in combinations(ids, 2)
    }
    out: dict[str, Any] = {
        "lists": len(results),
        "total_picks": sum(len(v) for v in ids.values()),
        "union_albums": len(set().union(*ids.values())) if ids else 0,
        "union_artists": len(set().union(*artists.values())) if artists else 0,
        "pairwise_overlap": pairwise,
    }
    if reference is not None:
        ref = {by_id[cid].album_key for cid in reference.selected_candidate_ids}
        out["overlap_with_reference"] = {lens: overlap(chosen, ref) for lens, chosen in ids.items()}
    return out


def lens_evaluation(
    results: Sequence[AllocationResult],
    candidates: Sequence[AllocationCandidate],
    *,
    reference: AllocationResult | None = None,
    obscure_ceiling: int = DEFAULT_OBSCURE_CEILING,
) -> Mapping[str, Any]:
    """Per-list metrics plus set metrics, as one JSON-serializable mapping."""
    return {
        "lists": [lens_list_metrics(r, candidates, obscure_ceiling=obscure_ceiling) for r in results],
        "set": lens_set_metrics(results, candidates, reference=reference),
    }
