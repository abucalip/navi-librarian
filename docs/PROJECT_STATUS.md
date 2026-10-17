# Project status

Last reviewed: 2026-10-17 (MCP retirement PR #296 merged; repository-level closeout recorded)

## Current focus

**Recommendation Phase 0 diagnostics are in progress.** PR #298 adds private recommendation capture/replay and baseline diagnostics; its real-data capture and offline replay remain pending on the user's isolated Mac test environment. Do not change ranking, candidate selection, or allocation before that baseline gate is complete.

PR #299 addresses a separate, baseline-independent observability gap: scheduled discovery refreshes previously failed silently and one list's exception could prevent later lists from being checked in that hourly cycle. The branch adds deterministic freshness classification, per-list failure isolation, bounded warning logs, and regression tests. It does not change recommendation ranking or user-facing response shapes.

**Next action:** verify PR #299's exact-head CI and diff. Keep PR #298's private capture/replay gate open; publishing and deployment remain paused.

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
