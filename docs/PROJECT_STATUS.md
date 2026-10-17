# Project status

Last reviewed: 2026-10-18 (backend recommendation-diversity contract and allocator integration implemented in PR #326; settings UI remains separate)

## Current focus

**Recommendation diversity backend — PR #326 open.** The identity-free evaluator CLI completed successfully against the existing private fixture. Its actual output contains six lambda results and no relevance-floor dimension; the earlier 35-combination/floor-sweep reproduction is dismissed as a decision input. Do not run another fixture test for that discrepancy. The fixture and identity-bearing report remain private.

PR #326 adds persistent `recommendation_diversity` preference storage, strict `GET/PUT /api/settings/recommendation-diversity` validation for integer values 0–100, a safe default of 0 for absent/corrupt values, and MMR marginal ranking inside the existing allocator passes. Setting 0 preserves legacy candidate ordering; nonzero values affect only ownership-clear candidates. Existing ownership checks, category/style/family policy, artist cap, deterministic ties, and the 60-check budget remain in place. The settings UI is intentionally not part of this PR.

The code/test revision `84a0f626da5c0293279755b2e2a0111960b19304` passed all four required workflows: Python syntax, Docker packaging/full unit suite, container runtime smoke test, and validation-only Docker image checks (publishing paused). The documentation-updated PR head `7366e9933ab268deba14d83b6e2309deb53b0e98` also passed all four required workflows; the final merge head must still be checked before merge. PR #326 is not yet merged.

Production deployment is not authorized or claimed. Publishing remains paused; no production runtime verification is claimed.

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
| Recommendation diversity preference, slider semantics, calibration, and rollout gates | `docs/DIVERSITY_SETTING_ROADMAP.md` |
| User-visible behavior and product invariants | `docs/REQUIREMENTS.md` |
| Required automated and manual verification | `docs/TEST_PLAN.md` |
| Focused documentation/code retrieval for agent sessions | `docs/SESSION_CONTEXT_SEARCH.md` and `scripts/session_search.py` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
