"""Pure policy allocator for personal recommendation shortlists.

All enrichment, identity normalization, ownership lookup, and response shaping
must happen outside this module. The allocator consumes immutable prepared
values and returns stable candidate IDs plus policy diagnostics.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from recommendation_run_metrics import timed_stage

from discovery.mmr import candidate_similarity

from discovery.allocation_contract import (
    AllocationCandidate,
    AllocationRequest,
    AllocationResult,
    CandidateDecision,
    OwnershipStatus,
)


@timed_stage('allocation')
def allocate_personal_recommendations(request: AllocationRequest) -> AllocationResult:
    """Allocate a shortlist using the established multi-pass recommendation policy (parity verification pending)."""
    candidates = request.candidates
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    ordered_by_category = {
        category: sorted(
            (candidate for candidate in candidates if candidate.category == category),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        for category in ("adjacent", "cross_genre", "adventurous", "unclassified")
    }
    eligible_scores = [
        candidate.score for candidate in candidates
        if candidate.ownership is OwnershipStatus.CLEAR
    ]
    score_low = min(eligible_scores, default=0.0)
    score_span = max(eligible_scores, default=0.0) - score_low
    selected: list[str] = []
    review: list[str] = []
    selected_counts: Counter[str] = Counter()
    selected_styles: Counter[str] = Counter()
    selected_families: Counter[str] = Counter()
    selected_genres: Counter[str] = Counter()
    coverage_policy = request.genre_family_cap is not None
    processed: set[tuple[str, str]] = set()
    decisions: dict[str, CandidateDecision] = {}
    checked = 0
    phase_diagnostics = {
        "diversity_reservation_attempts": 0,
        "category_quota_attempts": 0,
        "family_cap_relaxation_attempts": 0,
        "quota_retry_attempts": 0,
        "unclassified_fallback_attempts": 0,
        "final_fallback_entered": 0,
        "final_fallback_attempts": 0,
    }
    if coverage_policy:
        phase_diagnostics.update({
            "category_floor_attempts": 0,
            "family_coverage_attempts": 0,
            "score_fill_attempts": 0,
        })

    def ranked_candidates(items):
        """Apply MMR only to ownership-clear candidates at each selection step."""
        ordered_items = list(items)
        if request.diversity_penalty == 0:
            yield from ordered_items
            return
        remaining_eligible = [
            candidate for candidate in ordered_items
            if candidate.ownership is OwnershipStatus.CLEAR
        ]
        for item in ordered_items:
            if item.ownership is not OwnershipStatus.CLEAR:
                # Preserve the legacy position and review/rejection behavior for
                # owned and ambiguous-title candidates; MMR is a soft preference
                # only among candidates that passed the hard ownership gate.
                yield item
                continue
            selected_candidates = [by_id[candidate_id] for candidate_id in selected]

            def marginal_score(candidate):
                relevance = (
                    1.0 if score_span == 0.0
                    else (candidate.score - score_low) / score_span
                )
                similarity = max(
                    (
                        candidate_similarity(
                            {"artist_key": candidate.artist_key, "tags": candidate.tags},
                            {"artist_key": chosen.artist_key, "tags": chosen.tags},
                        )
                        for chosen in selected_candidates
                    ),
                    default=0.0,
                )
                return relevance - request.diversity_penalty * similarity

            best = max(remaining_eligible, key=marginal_score)
            remaining_eligible.remove(best)
            yield best

    def record(candidate: AllocationCandidate, status: str, reason: str) -> None:
        previous = decisions.get(candidate.candidate_id)
        if previous and previous.status == "selected":
            return
        decisions[candidate.candidate_id] = CandidateDecision(
            candidate.candidate_id, status, reason
        )

    def consider(
        candidate: AllocationCandidate,
        *,
        allow_over_quota: bool = False,
        allow_over_family_cap: bool = False,
        allow_over_style_target: bool = False,
        allow_over_genre_cap: bool = False,
    ) -> None:
        nonlocal checked
        category = candidate.category
        style = candidate.diversity_style

        # Identity is a hard eligibility constraint, so report it before soft
        # diversity/category caps. Otherwise a duplicate can retain a stale
        # recent-family rejection even after final fallback has relaxed that cap.
        identity = (candidate.artist_key, candidate.album_key)
        if identity in processed:
            # Preserve the more important ownership diagnostic for an owned
            # duplicate; otherwise a duplicate row could hide an ownership
            # rejection in the candidate-level report.
            if candidate.ownership is OwnershipStatus.EXACT_OWNED:
                record(candidate, "already_owned",
                       "A normalized album-title and artist-credit match exists in the indexed Navidrome inventory.")
            elif candidate.ownership is OwnershipStatus.TITLE_CONFLICT:
                if candidate.candidate_id not in review:
                    review.append(candidate.candidate_id)
                record(candidate, "held_for_ownership_review",
                       "The album title exists in Navidrome under a different artist credit; manual review is recommended.")
            else:
                record(candidate, "duplicate_candidate",
                       "The same artist and album identity was already processed.")
            return

        style_target = request.diversity_style_targets.get(style, 0)
        if not allow_over_style_target and style_target and selected_styles[style] >= style_target:
            record(candidate, "diversity_style_target_filled",
                   f"The target of {style_target} recommendation for the {style} diversity slot was already filled.")
            return

        if coverage_policy and not allow_over_genre_cap:
            genre = candidate.genre_family
            genre_cap = request.genre_family_cap if genre else request.unknown_family_cap
            if selected_genres[genre or ""] >= genre_cap:
                record(candidate, "genre_family_cap_reached",
                       f"The genre family {genre or 'unknown'} already has {genre_cap} "
                       "recommendation(s); another family is preferred.")
                return

        family = candidate.recent_profile_family
        if (not coverage_policy and not allow_over_family_cap
                and style not in request.diversity_style_targets
                and family and selected_families[family] >= request.family_cap):
            record(candidate, "recent_genre_cap_reached",
                   f"The recent-listening family {family} already has a recommendation; another family is preferred.")
            return
        if checked >= request.max_checks:
            record(candidate, "not_considered",
                   f"The candidate search limit of {request.max_checks} checks was reached.")
            return
        quota = request.category_targets.get(category)
        if not allow_over_quota and quota is not None and selected_counts[category] >= quota:
            record(candidate, "category_quota_filled",
                   f"The target of {quota} recommendations for the {category} category was already filled.")
            return
        if len(selected) >= request.count:
            record(candidate, "not_considered",
                   "The requested number of recommendations was already reached.")
            return

        processed.add(identity)
        if any(by_id[item].artist_key == candidate.artist_key for item in selected):
            record(candidate, "artist_already_selected",
                   "Another album by this artist has already been selected.")
            return

        # Ownership is precomputed, so under the coverage policy only candidates
        # that could be selected use the check budget; owned ones are free to skip.
        if not coverage_policy or candidate.ownership is OwnershipStatus.CLEAR:
            checked += 1
        if candidate.ownership is OwnershipStatus.EXACT_OWNED:
            record(candidate, "already_owned",
                   "A normalized album-title and artist-credit match exists in the indexed Navidrome inventory.")
            return
        if candidate.ownership is OwnershipStatus.TITLE_CONFLICT:
            review.append(candidate.candidate_id)
            record(candidate, "held_for_ownership_review",
                   "The album title exists in Navidrome under a different artist credit; manual review is recommended.")
            return

        selected.append(candidate.candidate_id)
        record(candidate, "selected",
               "Passed the ownership checks and was added to the recommendations.")
        selected_counts[category] += 1
        selected_styles[style] += 1
        selected_genres[candidate.genre_family or ""] += 1
        if style not in request.diversity_style_targets and family:
            selected_families[family] += 1

    def consider_in_phase(candidate: AllocationCandidate, phase: str, **kwargs) -> None:
        phase_diagnostics[f"{phase}_attempts"] += 1
        consider(candidate, **kwargs)

    # Reserve configured diversity slots first, in mapping insertion order.
    for style, target in request.diversity_style_targets.items():
        if len(selected) >= request.count or checked >= request.max_checks:
            break
        if selected_styles[style] >= target:
            continue
        for candidate in ranked_candidates(
            sorted(
                (item for item in candidates if item.diversity_style == style),
                key=lambda item: item.score,
                reverse=True,
            )
        ):
            if selected_styles[style] >= target:
                break
            consider_in_phase(candidate, "diversity_reservation")
            if len(selected) >= request.count or checked >= request.max_checks:
                break

    def done() -> bool:
        return len(selected) >= request.count or checked >= request.max_checks

    if coverage_policy:
        # Category floors keep exploration alive without fixed quotas.
        for category, floor in request.category_floors.items():
            for candidate in ranked_candidates(ordered_by_category[category]):
                if done() or selected_counts[category] >= floor:
                    break
                consider_in_phase(candidate, "category_floor")

        # Coverage: the best candidate of each not-yet-represented genre family,
        # above a relevance floor, so extra supply can add families rather than
        # more of the families already selected.
        top_score = max(eligible_scores, default=0.0)
        coverage_floor = request.coverage_floor_ratio * top_score if top_score > 0 else float("-inf")
        by_score = sorted(candidates, key=lambda item: item.score, reverse=True)
        for candidate in ranked_candidates(by_score):
            if done() or len(selected) >= request.coverage_target:
                break
            if (candidate.ownership is OwnershipStatus.CLEAR
                    and (not candidate.genre_family
                         or selected_genres[candidate.genre_family]
                         or candidate.score < coverage_floor)):
                continue
            consider_in_phase(candidate, "family_coverage")

        for candidate in ranked_candidates(by_score):
            if done():
                break
            consider_in_phase(candidate, "score_fill")
    else:
        # Normal category quota pass.
        for category in ("adjacent", "cross_genre", "adventurous"):
            for candidate in ranked_candidates(ordered_by_category[category]):
                target = request.category_targets.get(category, 0)
                if selected_counts[category] >= target:
                    break
                consider_in_phase(candidate, "category_quota")
                if len(selected) >= request.count or checked >= request.max_checks:
                    break
            if len(selected) >= request.count or checked >= request.max_checks:
                break

        # Relax recent-family caps before category balance.
        for category in ("adjacent", "cross_genre", "adventurous"):
            if len(selected) >= request.count or checked >= request.max_checks:
                break
            for candidate in ranked_candidates(ordered_by_category[category]):
                if selected_counts[category] >= request.category_targets.get(category, 0):
                    break
                consider_in_phase(candidate, "family_cap_relaxation", allow_over_family_cap=True)
                if len(selected) >= request.count or checked >= request.max_checks:
                    break

        # Retry unmet category slots without exceeding their quotas.
        if len(selected) < request.count and checked < request.max_checks:
            for category in ("adjacent", "cross_genre", "adventurous"):
                if selected_counts[category] >= request.category_targets.get(category, 0):
                    continue
                for candidate in ranked_candidates(ordered_by_category[category]):
                    if selected_counts[category] >= request.category_targets.get(category, 0):
                        break
                    consider_in_phase(candidate, "quota_retry")
                    if len(selected) >= request.count or checked >= request.max_checks:
                        break
                if len(selected) >= request.count or checked >= request.max_checks:
                    break

        # Use unclassified candidates before relaxing all remaining policy limits.
        if len(selected) < request.count and checked < request.max_checks:
            for candidate in ranked_candidates(ordered_by_category["unclassified"]):
                consider_in_phase(candidate, "unclassified_fallback", allow_over_quota=True)
                if len(selected) >= request.count or checked >= request.max_checks:
                    break

    if len(selected) < request.count and checked < request.max_checks:
        phase_diagnostics["final_fallback_entered"] = 1
        category_order = {
            "adjacent": 0,
            "cross_genre": 1,
            "adventurous": 2,
            "unclassified": 3,
        }
        # The legacy fallback first concatenates category lists (each already
        # score-sorted), then performs a stable global score sort. Preserve
        # that category/source ordering for equal-score candidates.
        fallback_base = sorted(
            candidates,
            key=lambda item: (
                category_order[item.category],
                -item.score,
                item.source_order,
            ),
        )
        remaining: Iterable[AllocationCandidate] = sorted(
            fallback_base, key=lambda item: item.score, reverse=True
        )
        for candidate in ranked_candidates(remaining):
            consider_in_phase(candidate, "final_fallback", allow_over_quota=True,
                              allow_over_family_cap=True, allow_over_style_target=True,
                              allow_over_genre_cap=True)
            if len(selected) >= request.count or checked >= request.max_checks:
                break

    return AllocationResult(
        requested_count=request.count,
        selected_candidate_ids=tuple(selected),
        ownership_review_candidate_ids=tuple(review),
        decisions=tuple(decisions.values()),
        category_counts=dict(selected_counts),
        checked_count=checked,
        phase_diagnostics=phase_diagnostics,
        lens=request.lens,
    )
