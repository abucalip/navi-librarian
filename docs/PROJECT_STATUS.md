# Project status

Last reviewed: 2026-10-16 (PR #250 pure-helper test migration merged)  
GitHub source of truth: `main` includes pure-helper test migration merge `c71a330ee6b5d44595c0c70299e8a61a45b15ab4` (PR #250)

## Current focus

Backend modularization remains in progress. Recent work has extracted discrete discovery and application-assembly responsibilities, including New Releases policy/provider helpers and authentication configuration/secret/settings helpers. See the root `PROJECT_LOG.md` for exact PRs, tested SHAs, test evidence, and merge commits.

## Next action

1. Map the remaining acquisition-safety lifecycle tests to direct production interfaces where a real owner exists; preserve concurrency, persistence, recovery, and unsafe-failure coverage.
2. Add an allowlist-aware app-import boundary guard that recognizes the reviewed lazy adapter in `app/api/dependencies.py` and preserves the app-import isolation regression.
3. Then evaluate `service_settings.py` wrappers and the acquisition coordinator's policy-vs-orchestration seam.
4. Do not force additional classics-builder or size-only slskd extractions.

The active candidate list and acceptance criteria live in `docs/MODULARIZATION_ROADMAP.md`. The AST/source-coupling inventory is `docs/architecture/AST_TEST_INVENTORY.md`.

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