# Project status

Last reviewed: 2026-10-16 (PR #264 merged and verified; size ratchet in progress)  
Documentation branch base: GitHub `main` after merge commit `cb4f5aef3534e06128401ef3eed3e9ce2908b5f4`

## Current focus

Backend modularization remains in progress. Recent work has extracted discrete discovery and application-assembly responsibilities, including New Releases policy/provider helpers and authentication configuration/secret/settings helpers. See the root `PROJECT_LOG.md` for exact PRs, tested SHAs, test evidence, and merge commits.

## Next action

1. Review and verify PR #265 (size ratchet) on its exact final head, then merge only if all four required workflows pass.
2. The verified baseline after PR #264 is `navidrome_server.py`: 3,031 lines. The new guard sets a 3,031-line file ceiling, a 280-line general top-level-function ceiling, and a documented temporary 575-line exception for `recommend_new_music()`; CI reports measured AST function sizes.
3. Audit mutable `MUSIC_DIR`, then settings wrappers and the acquisition coordinator's policy-vs-orchestration seam. Parallelize independent gates only when prerequisites and changed files do not overlap.
4. Obtain the owner's explicit authorization/retention decision for MCP-exposed `restart_server` and `apply_server_patch` before changing their exposure or implementation.
5. Do not force additional classics-builder or size-only slskd extractions.

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