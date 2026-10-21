# Architecture overview

Last reviewed: 2026-10-16 (AST test inventory added)

This document describes current architectural responsibilities at a useful level. It is not a chronological extraction log; see root `PROJECT_LOG.md` for PR-by-PR history and verification evidence. Confirm all details against current GitHub `main` and source before changing a boundary.

## Main layers

### Web application

- `app/main.py` assembles the FastAPI application, dependencies, authentication integration, middleware, and route registration.
- `app/api/` contains HTTP route adapters. Routes validate requests, invoke domain/service logic, and shape HTTP responses; they should not duplicate domain policy.
- `app/security/` owns authentication/security helpers. Keep persisted secret loading, configuration predicates, sessions, cookies, and route/middleware behavior behind their existing contracts.
- `app/services/` owns reusable application/domain services. Provider access and persistence should remain explicit dependencies rather than hidden app initialization.

### Legacy server and domain helpers

- `navidrome_server.py` remains a large compatibility/orchestration boundary used by existing callers. It coordinates provider/library access, cache and persistence dependencies, discovery routes/tools, and acquisition wiring.
- Root-level `discovery_*.py` modules own extracted discovery policies and payload transformations, including New Releases candidate selection/merge/window/query/response rules, classics candidate collection/rating/genre stages, personal recommendation allocation/payload shaping, and cached discovery-list projection.
- Root-level `acquisition_*.py` modules own extracted acquisition state, candidate validation/start, request coordination, lifecycle, orchestration, recovery, watcher, progress accounting/snapshots, diagnostics, completion, import, cleanup, and source-switch responsibilities.
- `navidrome_client.py`, `integrations/lastfm/client.py`, `listenbrainz_client.py`, `slskd_client.py`, `musicbrainz_*.py`, `slskd_*.py`, and cache/settings modules isolate provider protocols or supporting policies where extracted.
- `server.py` and `mcp_registry.py` are part of the existing server/MCP compatibility surface. Routine modularization must preserve that behavior unless a separate approved retirement plan changes it.

These are responsibility summaries, not an assertion that every dependency is already ideal. Inspect actual imports and call sites before moving code.

## Boundary rules

1. Keep HTTP routing, application assembly, domain policy, provider I/O, persistence, and UI concerns distinct.
2. Prefer pure helpers or small explicit dependency-injected interfaces that can be tested by direct import.
3. Keep provider/cache/rate-limit ownership and orchestration at the layer that already owns them unless the extraction contract explicitly and safely changes that boundary.
4. Preserve existing signatures, response shapes, side effects, persistence semantics, and compatibility adapters unless an approved requirement says otherwise.
5. Treat acquisition, import, cleanup, and deletion as safety-critical. Validate canonical paths under configured roots, reject traversal/symlink escapes and ambiguous targets, and prove unrelated files remain untouched.
6. Do not extract code solely to reduce file size. Avoid broad callback surfaces, duplicate policy, and extra layers that make the system harder to understand.
7. Review package/Docker inclusion and AST-coupled test assumptions whenever modules or imports move.
8. Keep MCP compatibility during modularization. Retirement is a separate decision and migration gate.

## Completion audit

Before declaring modularization complete:
- run `scripts/dep_map.py` and review the generated import graph for `app/main.py`, API modules, and `navidrome_server.py`;
- trace `app/main.py` and API dependencies on `navidrome_server.py`;
- distinguish intentional compatibility adapters from accidental coupling;
- inventory AST/source-reading tests in `docs/architecture/AST_TEST_INVENTORY.md` and move behavioral assertions to direct-import tests without weakening safety coverage;
- run `grep -r "navidrome_server" app/ --include="*.py"` and allow only explicitly documented compatibility adapters. Current known web edge: `app/api/dependencies.py` lazily imports the legacy server inside `get_librarian()`; preserve the app-import isolation regression in `tests/test_auth_routes_integration.py`.
- verify direct-import and adapter-level regressions for extracted boundaries;
- identify remaining responsibilities that are justified orchestration/provider wiring rather than forcing further extraction.

The active candidate list and acceptance criteria are in `docs/MODULARIZATION_ROADMAP.md`. Required checks are in `docs/TEST_PLAN.md`; workflow and release gates are in `docs/DEVELOPMENT_WORKFLOW.md`.