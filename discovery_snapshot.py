"""Pure policy for the last-known-good personal snapshot (roadmap 3.4).

No I/O happens here. Callers pass the stored payload, the candidate build, and
an ownership predicate. The module decides whether a build may replace the
stored list and filters a stored list at read time. Counters are aggregate
only: they never carry identities, artists, or albums.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from discovery_store import recommendation_identity_hash

REASON_NO_PREVIOUS = "no_previous"
REASON_ACCEPTED = "accepted"
REASON_BUILD_ERROR = "build_error"
REASON_PROVIDER_FAILURES = "provider_failures"
REASON_EMPTY_BUILD = "empty_build"
REASON_FEWER_THAN_SNAPSHOT = "fewer_items_than_snapshot"


def _recommendations(payload: Any) -> list[Any] | None:
    """Return the recommendation list of a well-formed payload, else None."""
    if not isinstance(payload, Mapping) or payload.get("error"):
        return None
    recommendations = payload.get("recommendations")
    return recommendations if isinstance(recommendations, list) else None


def _eligible_count(
    recommendations: list[Any],
    is_excluded: Callable[[Mapping[str, Any]], bool] | None,
) -> int:
    if is_excluded is None:
        return len(recommendations)
    return len(filter_snapshot(recommendations, is_excluded)[0])


def replacement_decision(
    previous: Any,
    candidate: Any,
    *,
    provider_failures: int = 0,
    is_excluded: Callable[[Mapping[str, Any]], bool] | None = None,
) -> tuple[bool, str]:
    """Return ``(replace, reason)`` for a candidate build against the stored list.

    A degraded build never replaces a usable stored list: a malformed or errored
    build, a build with provider failures, or an empty build is rejected. A build
    with fewer currently eligible items than the stored snapshot is also rejected.
    ``is_excluded`` should report owned or duplicate identities, so that the
    comparison counts only items the user could still be shown.
    """
    candidate_items = _recommendations(candidate)
    if candidate_items is None:
        return False, REASON_BUILD_ERROR
    if provider_failures > 0:
        return False, REASON_PROVIDER_FAILURES
    if not candidate_items:
        return False, REASON_EMPTY_BUILD

    previous_items = _recommendations(previous)
    if previous_items is None:
        return True, REASON_NO_PREVIOUS

    if _eligible_count(candidate_items, is_excluded) < _eligible_count(
        previous_items, is_excluded
    ):
        return False, REASON_FEWER_THAN_SNAPSHOT
    return True, REASON_ACCEPTED


def filter_snapshot(
    recommendations: list[Any],
    is_excluded: Callable[[Mapping[str, Any]], bool],
) -> tuple[list[Any], dict[str, int]]:
    """Drop owned, duplicate, and unidentifiable items from a stored list.

    Kept items are returned unchanged, including their stored ``rank`` values, so
    ranks still reflect the order the build produced. Ownership is decided by the
    caller's predicate against the current library on every read.
    """
    kept: list[Any] = []
    seen: set[str] = set()
    counts = {"kept": 0, "owned": 0, "duplicate": 0, "unidentified": 0}
    for item in recommendations:
        if not isinstance(item, Mapping):
            counts["unidentified"] += 1
            continue
        identity = recommendation_identity_hash(item)
        if identity is None:
            counts["unidentified"] += 1
            continue
        if is_excluded(item):
            counts["owned"] += 1
            continue
        if identity in seen:
            counts["duplicate"] += 1
            continue
        seen.add(identity)
        kept.append(item)
    counts["kept"] = len(kept)
    return kept, counts


def serve_snapshot(
    payload: Mapping[str, Any],
    is_excluded: Callable[[Mapping[str, Any]], bool],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return a copy of a stored personal payload with excluded items removed."""
    recommendations = _recommendations(payload)
    if recommendations is None:
        return dict(payload), {"kept": 0, "owned": 0, "duplicate": 0, "unidentified": 0}
    kept, counts = filter_snapshot(recommendations, is_excluded)
    served = dict(payload)
    served["recommendations"] = kept
    return served, counts
