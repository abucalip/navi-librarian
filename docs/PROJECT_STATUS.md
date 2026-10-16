# Project status

Last reviewed: 2026-10-16 (PR #283 merged as `767ac3efd4e02eab15c04fd033fabeb619f4b1ff`)
Documentation base: GitHub `main` at commit `767ac3efd4e02eab15c04fd033fabeb619f4b1ff`

## Current focus

PRs #278, #280, and #281 extracted category, Last.fm, and familiarity/exploration scoring policies; PR #283 tightened the recommendation size exception from 575 to 450 lines. `recommend_new_music()` is 396 AST lines, the server is 2,596 lines, and `_discovery_acquire_album_impl()` is 278 lines. Current-main dependency map artifact `12077488636` (SHA-256 `39b6b2854789f0273b117adb1b9357e4765e420f87f61b05b4932f4b45c5ad49`) covers 171 modules and a 73-module app import closure; the sole app-to-legacy import is the intentionally lazy edge at `app/api/dependencies.py:10`. The completion audit found no further extraction worth the dependency surface without a concrete behavior seam. See `PROJECT_LOG.md`.

## Next action

1. Verify and merge PR #282 only after all four required workflows pass on its exact final PR head; it tightens the temporary recommendation exception from 575 to 450 lines.
2. Then review the remaining `recommend_new_music()` body for independently testable policy seams; retain orchestration/diagnostic projection if no narrower boundary justifies extraction.
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