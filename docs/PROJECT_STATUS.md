# Project status

Last reviewed: 2026-10-16 (modularization audit on `d6e32aadfbca6e1d746ced657bdc124b9d472251`)
Documentation base: GitHub `main` at commit `d6e32aadfbca6e1d746ced657bdc124b9d472251`

## Current focus

Backend modularization remains in progress. PR #274 removed the final AST/source-layout coupling and PR #276 retired the two risky operational MCP tools. The current-main audit found the dependency-map artifact covers 168 repository modules and a 73-module app import closure; `app.api.dependencies` is the only app module with an AST-visible local import of `navidrome_server`, at its intentionally lazy line 10. The size guard passes at 2,768 server lines; `recommend_new_music()` is 568 AST lines and `_discovery_acquire_album_impl()` 278. PR in review centralizes duplicated recommendation category policy. See `PROJECT_LOG.md`.

## Next action

1. Verify and merge the shared recommendation-category policy extraction only after all four required workflows pass on its exact final PR head.
2. Then refresh the dependency map and repeat the completion audit; current map is artifact `12077720422` from main SHA `d6e32aadfbca6e1d746ced657bdc124b9d472251`.
3. Do not force additional classics-builder or size-only slskd extractions.

The MUSIC_DIR read/write audit is complete: persistence already injects path getter/setter callbacks, but operational adapters intentionally snapshot the current path at invocation time. A separate settings object would add indirection without removing the legacy compatibility dependency today; see the roadmap and PROJECT_LOG.md audit entry.

The active candidate list and acceptance criteria live in `docs/MODULARIZATION_ROADMAP.md`. The AST/source-coupling inventory is `docs/architecture/AST_TEST_INVENTORY.md`; no direct AST/source-layout coupling remains in the audited test suite. Request coordination lifecycle tests exercise `acquisition_request_coordinator.acquire_album_request()` directly.

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