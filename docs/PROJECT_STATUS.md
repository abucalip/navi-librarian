# Project status

Last reviewed: 2026-10-17 (PR #299 merged; recommendation baseline gate remains open)

## Current focus

**Recommendation Phase 0 is implemented but not complete.** PR #298 adds private recommendation capture/replay and deterministic synthetic metrics; a real private capture and successful offline replay still need to be run in the user's isolated Mac test environment. Until that gate is satisfied and the baseline reviewed, do not change ranking, candidate selection, scoring, or allocation.

PR #299 is merged and provides baseline-independent scheduled-refresh diagnostics: freshness classification for missing, expired, malformed, and non-finite timestamps; per-list cache/read/refresh failure isolation; bounded warnings that omit exception messages; and regression coverage. It preserves the 24-hour threshold, hourly cadence, list order, refresh callbacks, and API response contracts. Ranking and candidate selection are unchanged.

**PR #299 verification:** final PR head `e830adc7b014a915d31756619e5fadc90106696c`; merge commit `22820fb534ce243c78b1bb30d1f7cbbaaabd36cd`. All four required workflows passed on the exact final head: Python syntax run 1497, Docker packaging/full unit suite/build run 1405, container runtime smoke run 1214, and validation-only multi-architecture validation run 1258. No assistant-side local tests were run. Publishing, deployment, and production-runtime verification are not claimed.

## Delivery and verification state

- **MCP retirement plan merged:** PR #295, final PR head `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`, merge commit `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- **CI on exact PR head:** all four required workflows passed: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remains paused.
- **Local tests:** not run; this was a documentation-only planning change.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP retirement:** repository-level plan complete; PR #296 merged at `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. Four required workflows were reported passing on the final PR head. External client/config migration and production runtime are unverified.

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
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
