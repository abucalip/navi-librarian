"""Lenses: named list-selection strategies run over one shared candidate pool.

Every lens is a pure function of an immutable pool, so many lists cost no extra
provider calls. `partition_lenses` runs lenses in order and removes what each one
selected (by artist) before the next, so an album appears in at most one list.
See docs/engine2.md (Phase 2).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from discovery.allocation_contract import (
    MAX_CANDIDATE_CHECKS,
    AllocationCandidate,
    AllocationRequest,
    AllocationResult,
    CandidateDecision,
    OwnershipStatus,
)
from discovery.personal_allocator import allocate_personal_recommendations
from discovery.selection_policy import quota_targets, selection_request_options

# Starting values from the owner-approved Deep cuts definition.
DEEP_CUTS_MIN_AUDIENCE = 300
DEEP_CUTS_MAX_AUDIENCE = 50_000
DEEP_CUTS_MIN_TAGS = 2
DEEP_CUTS_MAX_PER_SEED = 2


@dataclass(frozen=True)
class Lens:
    name: str
    label: str
    kind: str  # "quota", "family_coverage" or "deep_cuts"


NOW = Lens("now", "Now", "quota")
GENRE_SPREAD = Lens("genre_spread", "Genre spread", "family_coverage")
DEEP_CUTS = Lens("deep_cuts", "Deep cuts", "deep_cuts")
LENSES = {lens.name: lens for lens in (NOW, GENRE_SPREAD, DEEP_CUTS)}
# Scarcest supply first, so the broader lenses do not take its few candidates.
DEFAULT_LENS_ORDER = (DEEP_CUTS, NOW, GENRE_SPREAD)


def select_deep_cuts(
    candidates: Iterable[AllocationCandidate],
    count: int,
    *,
    min_audience: int = DEEP_CUTS_MIN_AUDIENCE,
    max_audience: int = DEEP_CUTS_MAX_AUDIENCE,
    min_tags: int = DEEP_CUTS_MIN_TAGS,
    max_per_seed: int = DEEP_CUTS_MAX_PER_SEED,
) -> AllocationResult:
    """Gate by audience and tag count, rank by radio tag strength, one album per
    artist and at most `max_per_seed` per seed. Candidates without an audience
    figure are never selected: unknown is not obscure."""
    pool = tuple(candidates)
    ranked = sorted(pool, key=lambda item: (-item.tag_strength, item.source_order))
    selected: list[str] = []
    review: list[str] = []
    decisions: dict[str, CandidateDecision] = {}
    artists: set[str] = set()
    per_seed: Counter[str] = Counter()
    counts: Counter[str] = Counter()

    def record(item: AllocationCandidate, status: str, reason: str) -> None:
        decisions[item.candidate_id] = CandidateDecision(item.candidate_id, status, reason)

    for item in ranked:
        if len(selected) >= count:
            record(item, "not_considered", "The requested number of recommendations was already reached.")
        elif item.ownership is OwnershipStatus.EXACT_OWNED:
            record(item, "already_owned", "A normalized album-title and artist-credit match exists in the indexed Navidrome inventory.")
        elif item.ownership is OwnershipStatus.TITLE_CONFLICT:
            review.append(item.candidate_id)
            record(item, "held_for_ownership_review", "The album title exists in Navidrome under a different artist credit; manual review is recommended.")
        elif item.audience is None:
            record(item, "audience_unknown", "No listener count is available, so the album cannot be called obscure.")
        elif not min_audience <= item.audience <= max_audience:
            record(item, "audience_out_of_range",
                   f"The audience of {item.audience} is outside {min_audience} to {max_audience}.")
        elif len(item.tags) < min_tags:
            record(item, "too_few_tags", f"The artist has fewer than {min_tags} tags.")
        elif item.artist_key in artists:
            record(item, "artist_already_selected", "Another album by this artist has already been selected.")
        elif item.seed and per_seed[item.seed] >= max_per_seed:
            record(item, "seed_cap_reached", f"The seed {item.seed} already has {max_per_seed} recommendations.")
        else:
            selected.append(item.candidate_id)
            artists.add(item.artist_key)
            if item.seed:
                per_seed[item.seed] += 1
            counts[item.category] += 1
            record(item, "selected", "Passed the deep-cuts gates and was added to the recommendations.")
    return AllocationResult(
        requested_count=count,
        selected_candidate_ids=tuple(selected),
        ownership_review_candidate_ids=tuple(review),
        decisions=tuple(decisions.values()),
        category_counts=dict(counts),
        checked_count=min(len(pool), MAX_CANDIDATE_CHECKS),
        lens=DEEP_CUTS.name,
    )


def run_lens(
    lens: Lens,
    candidates: Sequence[AllocationCandidate],
    count: int,
    *,
    diversity_penalty: float = 0.0,
    max_checks: int = MAX_CANDIDATE_CHECKS,
) -> AllocationResult:
    """Run one lens over a pool; the result carries the lens name."""
    if lens.kind == "deep_cuts":
        return select_deep_cuts(candidates, count)
    if lens.kind == "family_coverage":
        targets, options = selection_request_options("family_coverage", count)
    elif lens.kind == "quota":
        targets, options = quota_targets(count), {}
    else:
        raise ValueError(f"unsupported lens kind: {lens.kind}")
    return allocate_personal_recommendations(AllocationRequest(
        candidates=tuple(candidates), count=count, category_targets=targets,
        diversity_style_targets={}, family_cap=1, max_checks=max_checks,
        diversity_penalty=diversity_penalty, lens=lens.name, **options,
    ))


def partition_lenses(
    candidates: Sequence[AllocationCandidate],
    count: int,
    lenses: Sequence[Lens] = DEFAULT_LENS_ORDER,
    *,
    diversity_penalty: float = 0.0,
) -> tuple[AllocationResult, ...]:
    """Run lenses in order over one pool, each on what earlier lenses left.

    An artist chosen by one lens is removed for the rest, so no artist or album
    appears in two lists. Results come back in the order given.
    """
    if len({lens.name for lens in lenses}) != len(lenses):
        raise ValueError("lens names must be unique")
    taken_artists: set[str] = set()
    results: list[AllocationResult] = []
    for lens in lenses:
        remaining = tuple(item for item in candidates if item.artist_key not in taken_artists)
        result = run_lens(lens, remaining, count, diversity_penalty=diversity_penalty)
        by_id = {item.candidate_id: item for item in remaining}
        taken_artists.update(by_id[cid].artist_key for cid in result.selected_candidate_ids)
        results.append(result)
    return tuple(results)
