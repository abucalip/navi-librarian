"""Request options and diagnostics for the final-list selection policies.

"quota" is the default 4/3/3 category-quota policy. "family_coverage" replaces
the quotas with a genre-family cap, an adventurous floor and a coverage phase
(see PERSONAL_RECOMMENDATION_ALLOCATION_CONTRACT.md).
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from discovery.allocation_contract import AllocationCandidate

GENRE_FAMILY_CAP = 2
COVERAGE_FLOOR_RATIO = 0.4


def quota_targets(count: int) -> dict[str, int]:
    """The 40% / 30% / remainder category split."""
    targets = {
        "adjacent": (count * 4) // 10,
        "cross_genre": (count * 3) // 10,
    }
    targets["adventurous"] = count - sum(targets.values())
    return targets


def selection_request_options(policy: str, count: int) -> tuple[dict[str, int], dict[str, Any]]:
    """Return (category_targets, extra AllocationRequest keyword arguments)."""
    if policy != "family_coverage":
        return quota_targets(count), {}
    return {}, {
        "genre_family_cap": GENRE_FAMILY_CAP,
        "category_floors": {"adventurous": count // 5},
        "coverage_target": count,
        "coverage_floor_ratio": COVERAGE_FLOOR_RATIO,
    }


def selection_policy_report(
    policy: str,
    selected_ids: Iterable[str],
    candidates: Iterable[AllocationCandidate],
) -> Mapping[str, Any]:
    """Diagnostics added to the response only under the opt-in policy."""
    if policy != "family_coverage":
        return {}
    family_by_id = {candidate.candidate_id: candidate.genre_family for candidate in candidates}
    return {
        "selection_policy": policy,
        "selected_genre_families": [family_by_id.get(candidate_id) for candidate_id in selected_ids],
    }
