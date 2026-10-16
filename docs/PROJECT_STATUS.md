# Project status

Last reviewed: 2026-10-16 (PR #272 merged as `9b97f447adc602a3be3b5ac496633430f3eb3cb4`)
Documentation base: GitHub `main` at commit `5a74b12d489ae30cfad923af7b68985ebede87dc`

## Current focus

Backend modularization remains in progress. PR #272 migrated broader-query fallback tests to direct imports and merged as `9b97f447adc602a3be3b5ac496633430f3eb3cb4`. The next focused PR removes the final AST/source-layout coupling from `tests/test_acquisition_safety.py` while retaining production-owner coverage for import persistence, dismissal locking, concurrency/recovery, and filesystem safety. Exact-head CI is pending.

## Next action

1. Verify and merge the final acquisition AST-coupling migration only after all four required workflows pass on its exact final PR head.
2. Then request the owner decision on MCP-exposed `restart_server` and `apply_server_patch`; do not refactor or remove them before that decision.
3. Do not force additional classics-builder or size-only slskd extractions.

The MUSIC_DIR read/write audit is complete: persistence already injects path getter/setter callbacks, but operational adapters intentionally snapshot the current path at invocation time. A separate settings object would add indirection without removing the legacy compatibility dependency today; see the roadmap and PROJECT_LOG.md audit entry.

The active candidate list and acceptance criteria live in `docs/MODULARIZATION_ROADMAP.md`. The AST/source-coupling inventory is `docs/architecture/AST_TEST_INVENTORY.md`. Request coordination lifecycle tests now exercise `acquisition_request_coordinator.acquire_album_request()` directly; the legacy AST harness remains only for behaviors without a suitable extracted owner.

## Delivery and verification state

- **Implemented / merged:** see `PROJECT_LOG.md` and current GitHub history for exact revisions.
- **Automated verification:** required CI gates must be checked on each exact final PR-head SHA; historical success is not evidence for a new revision.
- **Local execution:** do not claim assistant-side local tests unless actually run. Record unavailable or skipped checks explicitly.
- **Publishing:** paused; multi-architecture validation must remain non-publishing (`push: false`).
- **Deployment / production runtime:** not implied by merge or CI. No new deployment or production-runtime verification is claimed by this documentation update.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred because it has not been reproducibly demonstrated.
- **MCP:** preserve current compatibility seams during routine modularization. Retirement requires a separate explicit decision and migration gate.

## Documentation map

| Need | Canonical document |
|---|---|
| Current snapshot and next action | This file |
| Remaining extraction work and exit criteria | `docs/MODULARIZATION_ROADMAP.md` |
| Detailed historical PR, commit, and verification evidence | Root `PROJECT_LOG.md` |
| User-visible behavior and product invariants | `docs/REQUIREMENTS.md` |
| Required automated and manual verification | `docs/TEST_PLAN.md` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
| Current module boundaries and architectural decisions | `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and source code |

## Status update rule

Keep this file short and current. Update it after meaningful development sessions with the present state, verified blockers, and one next action. Do not copy long historical extraction reports here; put those in `PROJECT_LOG.md`.