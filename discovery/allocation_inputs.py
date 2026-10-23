"""Adapter helpers that turn enriched candidates into immutable allocation inputs.

Ownership is decided here against the completed library inventory, so the
allocator never queries the library or receives callbacks.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
from discovery.derived_profile import primary_genre_family


def classify_ownership(
    candidate: Mapping[str, Any],
    library_by_title: Mapping[str, list],
    music_key: Callable[[Any], str],
) -> tuple[str, OwnershipStatus]:
    """Return the candidate's normalized title key and its ownership status.

    A same-title library album by the same normalized artist is an exact match;
    the same title under another artist credit is a conflict for manual review.
    """
    title_key = music_key(candidate["album"])
    same_title = library_by_title.get(title_key, [])
    artist_key = music_key(candidate["primary_artist"])
    if any(music_key(match.get("artist", "")) == artist_key for match in same_title):
        return title_key, OwnershipStatus.EXACT_OWNED
    if same_title:
        return title_key, OwnershipStatus.TITLE_CONFLICT
    return title_key, OwnershipStatus.CLEAR


def build_allocation_inputs(
    albums: Iterable[Mapping[str, Any]],
    *,
    library_by_title: Mapping[str, list],
    genre_cache: Mapping[Any, Iterable[Any]],
    music_key: Callable[[Any], str],
    artist_identity: Callable[[Mapping[str, Any]], str],
) -> tuple[dict[str, Mapping[str, Any]], list[AllocationCandidate]]:
    """Map enriched candidates to allocation candidates, keyed by stable ID."""
    candidate_by_id: dict[str, Mapping[str, Any]] = {}
    allocation_candidates: list[AllocationCandidate] = []
    for source_order, candidate in enumerate(albums):
        candidate_id = str(source_order)
        candidate_by_id[candidate_id] = candidate
        title_key, ownership = classify_ownership(candidate, library_by_title, music_key)
        tags = tuple(
            str(tag)
            for tag in genre_cache.get(candidate.get("artist_mbid"), [])
            if tag is not None
        )
        allocation_candidates.append(AllocationCandidate(
            candidate_id=candidate_id,
            artist_key=artist_identity(candidate),
            album_key=title_key,
            category=candidate["discovery_category"],
            score=float(candidate["discovery_score"]),
            source_order=source_order,
            diversity_style=candidate.get("diversity_style", "other"),
            recent_profile_family=candidate.get("recent_profile_family"),
            genre_family=primary_genre_family(tags),
            tags=tags,
            ownership=ownership,
        ))
    return candidate_by_id, allocation_candidates
