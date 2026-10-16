# Project status

Last reviewed: 2026-10-17 (orphan-script and size-ratchet follow-up)
Documentation base: GitHub `main`; audit reviewed source at PR #288 final code head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c` plus subsequent documentation-only closeout.

## Current focus

**Modularization roadmap complete.** The final audit found no remaining concrete correctness, safety, or testability gap that justifies another extraction. Remaining recommendation and acquisition code is documented orchestration/compatibility wiring. No further size-only extraction is planned.

The transitive dependency-map review is recorded in `PROJECT_LOG.md`. The app-to-legacy import remains the single intentional lazy edge in `app/api/dependencies.py:get_librarian()`; AST/source-reading tests have been inventoried and behavior tests migrated to direct imports. The Docker regression checks every root-level module imported by `navidrome_server.py` against the explicit COPY list; the final audit found all 48 imported modules included, including the two omissions corrected by PRs #286 and #288.

**Next action:** none for modularization. The post-closeout hygiene follow-up removes two unreferenced root patch scripts and tightens the server ceiling to 2,650 lines. Resume further work only for a concrete correctness, security, verification, or product requirement. Keep publishing paused until separately authorized.

## Delivery and verification state

- **Implemented / merged:** PR #286 added `acquisition_import_service.py`; PR #288 added `discovery_candidate_gathering.py` and generalized the Docker packaging regression.
- **CI:** all four required workflows passed on exact PR #288 head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c`: syntax (`38978049684`), Docker packaging/full unit suite/build (`38978049670`), runtime smoke (`38978049793`), and non-publishing multi-architecture validation (`38978049589`). No local test commands were run.
- **Publishing:** paused; multi-architecture validation must remain non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP:** `restart_server` and `apply_server_patch` were retired by PR #276; preserve the remaining MCP compatibility surface unless a separately approved migration changes it.

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
