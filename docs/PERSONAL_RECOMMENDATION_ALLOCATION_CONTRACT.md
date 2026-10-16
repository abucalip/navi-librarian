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
