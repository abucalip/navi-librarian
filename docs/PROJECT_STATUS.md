# Project status

Last reviewed: 2026-10-17 (Phase 3.1 MMR evaluation helper opened for review)

## Current focus

**Recommendation roadmap — Phase 3.1 MMR evaluation.** Branch `recommendation/phase-3-1-mmr-evaluation` adds a pure deterministic MMR selector and shortlist diversity metrics with focused tests. The helper is not integrated into production ranking; replay-based relevance/diversity evaluation and exact-head CI remain pending. Prior Phase 2.2 work (PR #314) is merged at `295da73b9d279e944501c5c3d28866e8b1b7123f`; provider genre tags take precedence over artist-name fallbacks, and source provenance remains private. The owner's sustained real-world report is sufficient to proceed without further diagnostic snapshots.

PR #308 (bounded diagnostic history) was closed unmerged at the owner's direction because longitudinal collection is no longer needed. PR #309 merged at `d11dce4d981af4c34aa60a4d9caedb15eb8b6d58` from exact final PR head `e00d07363c72fcbe971cb9b08432cd1f5bddf46e`. It adds deterministic 14-day half-life listen weights, a smooth familiarity curve peaking at low-but-nonzero familiarity, and raises the profile relevance multiplier cap from 10% to 25%. Raw play counts remain intact for payload/display fields; weighted counts drive scoring/profile evidence. Ownership/release eligibility and the public API response shape remain unchanged by intent.

All four required workflows passed on exact final PR head `e00d07363c72fcbe971cb9b08432cd1f5bddf46e`: Python syntax/size/import-boundary run 1560 (`39047871211`); Docker packaging/full unit suite/build run 1468 (`39047871243`, 626 tests passed); container runtime smoke run 1277 (`39047871304`); validation-only multi-architecture image validation run 1321 (`39047871378`). No assistant-side local tests were run. Publishing remains paused; no deployment or production-runtime verification is claimed.

PR #310 merged at `31315a54255762f821cdd9d9949ee11a3ce17fb1` from exact final PR head `2fb8ce7e45188f7f02104cd171ac0d08102279ca`. The contrasting-profile regression reverses both score ordering and the top recommendation when recent listening shifts between artists, with candidate/provider inputs and cached genre metadata held constant. All four required workflows passed on that exact final head: Python syntax `39048493243`, Docker packaging/full unit suite/build `39048493246` (627 tests passed), container runtime smoke `39048493238`, and validation-only multi-architecture image validation `39048493239` (publishing paused). No assistant-side local tests were run; no live provider calls or private captures were used.

PR #312 merged at `5b23b08556c467a67b0b6cdbe7148dc069eda6f1` from exact final PR head `dc957f9eb1d817fcc2117f819c0d12be6663b142`. It replaces the 20 fixed regional MusicBrainz queries with up to six listening-profile-weighted queries and two candidate-pool exploration queries, selected by a pure tested helper. It also removes four hidden regional one-slot allocation targets; measured diversity re-ranking remains for Phase 3.

All four required workflows passed on exact final PR head `dc957f9eb1d817fcc2117f819c0d12be6663b142`: Python syntax/size/import-boundary `39049404041`, Docker packaging/full unit suite/build `39049404031`, container runtime smoke `39049404044`, and validation-only multi-architecture image validation `39049404139` (publishing paused). On preceding code/documentation head `f4eaa44642003ea233cd1f66274746286732d6d4`, the full unit suite reported 631 tests passed. No assistant-side local tests were run; publishing, deployment, and production-runtime verification remain unperformed.

**Next action:** begin Phase 3.1 with a deterministic offline evaluation of MMR-style diversity re-ranking. Preserve hard eligibility and artist constraints; measure relevance and diversity against the existing replay harness. Do not collect further live diagnostic snapshots.

## Recommendation baseline and prior work

**Recommendation Phase 0 capture/replay is implemented and the private baseline replay succeeded.** On capture/source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`, offline replay reproduced 10/10 recommendations, consumed 197 provider events and 40 Last.fm events, and used zero network providers. The comparator checks all stable top-level fields except `pool_diagnostics` and `lastfm_last_error`. PR #298 merged at `68a0ee365778dab790ec54e04b54c8c72bd4552c` from final PR head `a3bdfd7bff6785c1fd17e422a26a7fde36170fad`; all four required workflows passed on that exact head. The owner has directed the project to proceed from Phase 0 using sustained real-world evidence of poor profile responsiveness; further diagnostic collection is not required.

PR #299 is merged and provides baseline-independent scheduled-refresh diagnostics: freshness classification for missing, expired, malformed, and non-finite timestamps; per-list cache/read/refresh failure isolation; bounded warnings that omit exception messages; and regression coverage. It preserves the 24-hour threshold, hourly cadence, list order, refresh callbacks, and API response contracts. Ranking and candidate selection are unchanged.

**PR #299 verification:** final PR head `e830adc7b014a915d31756619e5fadc90106696c`; merge commit `22820fb534ce243c78b1bb30d1f7cbbaaabd36cd`. All four required workflows passed on the exact final head: Python syntax run 1497, Docker packaging/full unit suite/build run 1405, container runtime smoke run 1214, and validation-only multi-architecture validation run 1258. No assistant-side local tests were run. Publishing, deployment, and production-runtime verification are not claimed.

## Delivery and verification state

- **Recommendation Phase 0 diagnostics/capture/replay merged:** PR #298, final PR head `a3bdfd7bff6785c1fd17e422a26a7fde36170fad`, merge commit `68a0ee365778dab790ec54e04b54c8c72bd4552c`. Exact-head workflows passed: Python syntax/size guard `39037807384`, Docker packaging/full unit suite/build `39037807392`, container runtime smoke `39037807378`, validation-only multi-architecture build `39037807401`. Publishing remains paused.
- **MCP retirement plan merged:** PR #295, final PR head `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`, merge commit `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- **CI on exact PR head:** all four required workflows passed: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remains paused.
- **Local tests:** not run in this GitHub-only workflow.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP retirement:** repository-level plan complete; PR #296 merged at `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. External client/config migration and production runtime are unverified.

## Documentation map

| Need | Canonical document |
|---|---|
| Current snapshot and next action | This file |
| MCP retirement evidence and migration gates | `docs/MCP_RETIREMENT_PLAN.md` |
| Recommendation engine audit and next-session proposals | `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` |
| Remaining extraction work and exit criteria | `docs/MODULARIZATION_ROADMAP.md` |
| Detailed historical PR, commit, and verification evidence | Root `PROJECT_LOG.md` |
| User-visible behavior and product invariants | `docs/REQUIREMENTS.md` |
| Required automated and manual verification | `docs/TEST_PLAN.md` |
| Focused documentation/code retrieval for agent sessions | `docs/SESSION_CONTEXT_SEARCH.md` and `scripts/session_search.py` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
