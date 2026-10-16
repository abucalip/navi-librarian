# Project status

Last reviewed: 2026-10-16 (PR #268 merged; import-completion service extraction in PR #269)  
Documentation branch base: GitHub `main` at commit `5a05ca4a389673896f8263758aacecaad79f28b0`

## Current focus

Backend modularization remains in progress. Recent work has extracted discrete discovery and application-assembly responsibilities, including New Releases policy/provider helpers and authentication configuration/secret/settings helpers. See the root `PROJECT_LOG.md` for exact PRs, tested SHAs, test evidence, and merge commits.

## Next action

1. Audit `_discovery_acquire_album_impl()` on current main and record exact evidence for whether candidate selection, source-switch thresholds, retry rules, or state transitions remain inline; retain it if it is orchestration only.
2. Obtain the owner's explicit authorization/retention decision for MCP-exposed `restart_server` and `apply_server_patch` before changing their exposure or implementation.
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