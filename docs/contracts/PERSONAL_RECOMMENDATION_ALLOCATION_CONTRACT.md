# Personal recommendation allocation contract

Status: **interface contract only; shortlist-selection loops have not been moved.**

## Purpose

Create a narrow, independently testable seam around the final personal-recommendation shortlist policy without relocating provider access, enrichment, library inventory retrieval, or legacy response construction.

## Boundary

The future allocator receives one immutable `AllocationRequest`:

- A tuple of prepared `AllocationCandidate` values.
- Stable candidate IDs unique within the request.
- Normalized artist and album identity keys.
- Final category, score, diversity style, recent-profile family, and precomputed ownership status.
- Requested count, category targets, diversity-style targets, family cap, and bounded check limit.

Ownership is an explicit value (`clear`, `exact_owned`, or `title_conflict`), not a callback. The caller performs the existing normalized-title/artist comparison against the completed Navidrome inventory before allocation. The allocator must not query providers, read caches, call Navidrome, or mutate candidate dictionaries.

The future `AllocationResult` contains ordered selected candidate IDs, ordered ownership-review IDs, candidate decision reasons, category counts, and the number of candidates checked. The existing `recommend_new_music()` adapter maps those IDs back to the enriched candidates and constructs the current JSON response. The interface intentionally carries no response payload and no shared mutable counters.

## Non-goals for this contract PR

- Do not move or rewrite the shortlist-selection loops.
- Do not change ranking, quota, fallback, ownership, diagnostic, or response semantics.
- Do not change the legacy `recommend_new_music(count)` signature or route/MCP callers.
- Do not add callbacks for ownership, identity normalization, payload shaping, or mutable state.
- Do not claim the allocation algorithm itself is tested by contract-model tests.

## Why the loops remain in place

The current nested `consider()` both applies allocation policy and performs identity de-duplication, the 60-check budget, ownership decisions, manual-review routing, response payload assembly, and diagnostics. The contract separates those concerns at the data boundary first. The next extraction is justified only if a pure allocator can consume these values and return this result without reintroducing callbacks or shared mutable state. If preserving current semantics needs more inputs than this, refine the boundary rather than expanding the interface indefinitely.

## Acceptance criteria for a future allocator extraction

1. Direct-import tests exercise regional/style reservations, category quotas, duplicates, per-artist limits, ownership statuses, family-cap relaxation, unclassified fallback, final fallback ordering, count bounds, and the 60-check limit.
2. Decision reasons and checked-count semantics remain compatible with current diagnostics.
3. The legacy adapter preserves response fields, order, ownership-review behavior, error handling, and callers.
4. Provider I/O, cache access, library retrieval, ranking/enrichment, and response serialization remain outside the allocator.
5. No callbacks or shared mutable state are required by the allocation function.

## Family-coverage policy (opt-in)

`AllocationRequest.genre_family_cap` selects a second policy; when it is `None` the quota policy above is unchanged. The policy uses `AllocationCandidate.genre_family` (computed by the caller with `primary_genre_family`), `unknown_family_cap`, `category_floors`, `coverage_target` and `coverage_floor_ratio`. Phases: category floors, family coverage (best candidate of each unseen family at or above `coverage_floor_ratio` x the top clear score), score fill, then the existing relaxed final fallback. The recent-family cap and category quotas do not apply, and owned or conflicting candidates do not consume the check budget. Tests: `FamilyCoveragePolicyTests`.

The adapter pieces live outside `recommend_new_music`: `discovery/allocation_inputs.py` (ownership classification and `AllocationCandidate` construction, including `genre_family`) and `discovery/selection_policy.py` (quota targets, family-coverage request options, and the response diagnostics emitted only under the opt-in policy). Tests: `tests/test_discovery_selection_inputs.py` and the policy cases in `tests/test_recommend_new_music_characterization.py`.

## Lenses (Engine 2)

`AllocationRequest.lens` and `AllocationResult.lens` name the list a result belongs to (default `now`). `discovery/lenses.py` defines the Now (quota), Genre spread (family coverage) and Deep cuts lenses, `run_lens` and `partition_lenses`; partitioning removes the artists and album titles an earlier lens selected before the next lens runs. Deep cuts reads `AllocationCandidate.audience` (album-level listeners only), `seed` and `tag_strength` (the radio `tag_count`), filled by `deep_cuts_fields` in `discovery/allocation_inputs.py` for tag-lane candidates only. Tests: `tests/test_discovery_lenses.py`, `tests/test_discovery_selection_inputs.py`, `tests/test_discovery_lb_tag_lane.py`.
