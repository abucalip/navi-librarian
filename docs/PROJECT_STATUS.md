# Project status

Last reviewed: 2026-10-16 (PRs #222, #279, and #282 merged)
Documentation base: GitHub `main` at commit `71eb20bc734f1113f81b62eef35e17d53b8adf8e`; status update is being recorded on a documentation PR branch.

## Current focus

PRs #278, #280, and #281 extracted recommendation category, Last.fm, and familiarity/exploration scoring policies; PR #283 tightened the temporary recommendation size exception to 450 lines. `recommend_new_music()` is 396 AST lines, `navidrome_server.py` is 2,596 lines, and `_discovery_acquire_album_impl()` is 278 lines. The current dependency map covers 171 modules and a 73-module app import closure; the sole app-to-legacy import is the intentionally lazy edge at `app/api/dependencies.py:10`. The AST/source-layout test migration is complete. See `PROJECT_LOG.md`.

The UI PRs #222 (dashboard coverflow ring), #279 (async Get-button state machine), and #282 (uniform acquisition-toast border) are now merged. All four required workflows passed on each exact PR head, and the owner confirmed manual UI testing. Publishing remains paused.

## Next action

1. Continue from `docs/MODULARIZATION_ROADMAP.md` only where a concrete behavior/testability seam justifies further work; the latest completion audit found no additional extraction worth the dependency surface without such a seam.
2. Keep the remaining acquisition coordinator orchestration intact unless a narrower policy boundary can be extracted without duplicating retry, concurrency, source-switching, or filesystem-safety rules.
3. Do not force additional classics-builder or size-only slskd extractions.

The MUSIC_DIR read/write audit is complete: persistence already injects path getter/setter callbacks, while operational adapters intentionally snapshot the current path at invocation time. A separate settings object would add indirection without removing the legacy compatibility dependency today; see the roadmap and PROJECT_LOG.md.

## Delivery and verification state

- **Implemented / merged:** see `PROJECT_LOG.md` and current GitHub history for exact revisions.
- **Automated verification:** the four required workflows passed on exact PR heads for #222 (`5b55527ec3a13aaa137ed3d56341fb029913f09f`), #279 (`b3f44942724b6f9c6865f6c9160a69e58715b28a`), and #282 (`cbe30a5bf26e503f1cb455861b32a5064b3604ab`).
- **Manual UI verification:** owner reports all three PRs were manually tested; the older manual-report format was waived by the owner for this merge request.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** not implied by merge or CI. No deployment or production-runtime verification is claimed.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred because it has not been reproducibly demonstrated.
- **MCP:** the early-development operational tools `restart_server` and `apply_server_patch` have been retired by PR #276. Preserve remaining compatibility seams unless a separately approved migration changes them.

## Documentation map

| Need | Canonical document |
|---|---|
| Current snapshot and next action | This file |
| Remaining extraction work and exit criteria | `docs/MODULARIZATION_ROADMAP.md` |
| Detailed historical PR, commit, and verification evidence | Root `PROJECT_LOG.md` |
| User-visible behavior and product invariants | `docs/REQUIREMENTS.md` |
| Required automated and manual verification | `docs/TEST_PLAN.md` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
| Current module boundaries and rationale | `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and source code |

## Status update rule

Keep this file short and current. Update it after meaningful development sessions with the present state, verified blockers, and one next action. Do not copy long historical extraction reports here; put those in `PROJECT_LOG.md`.
