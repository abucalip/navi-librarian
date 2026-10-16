# Project status

Last reviewed: 2026-10-16 (PR #288 merged; direct Docker import audit refreshed)
Documentation base: GitHub `main` at commit `047822df81b134084383ed370205b1a3554c706a`

## Current focus

The recommendation policy seams and acquisition AST-test migration are complete. No further extraction currently has a sufficiently narrow boundary to justify added indirection. The completion audit checked the current lazy web-to-legacy import in `app/api/dependencies.py`, the CI import-boundary guard, the AST inventory, and Docker's explicit root-module copy list.

PR #286 added `acquisition_import_service.py`, and PR #288 added `discovery_candidate_gathering.py`. The Docker packaging regression now AST-inspects `navidrome_server.py` and checks that every imported root-level Python module is listed among the Docker COPY sources. A follow-up comparison on current main found all 48 distinct root-level modules imported by `navidrome_server.py` are now included. The isolated runtime smoke test may not exercise this delayed import path.

## Next action

1. Fix the Docker image's missing `acquisition_import_service.py` and add a regression test that prevents this omission from recurring.
2. Verify all four required workflows on the exact final PR-head SHA, especially the container runtime and packaging checks; do not claim local tests unless run.
3. After merge, repeat the completion audit against exact current `main`: review the generated dependency map/artifact, app-to-legacy references, dynamic imports, Docker inclusion, and compatibility/safety tests. If no further gap remains, record modularization complete without inventing another extraction.

The `MUSIC_DIR` read/write audit remains closed: existing persistence callbacks and invocation-time path snapshots are sufficient; a separate settings object is not justified. The recommendation diagnostic projection and acquisition coordinator remain orchestration unless a concrete behavior change establishes a smaller testable seam.

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
