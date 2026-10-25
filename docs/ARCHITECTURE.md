# Architecture overview

Last reviewed: 2026-10-25 (global search P1 backend added)

This document describes current architectural responsibilities at a useful level. It is not a chronological extraction log; see root `PROJECT_LOG.md` for PR-by-PR history and verification evidence. Confirm all details against current GitHub `main` and source before changing a boundary.

## Main layers

### Web application

- `app/main.py` assembles the FastAPI application, dependencies, authentication integration, middleware, and route registration.
- `app/api/` contains HTTP route adapters. Routes validate requests, invoke domain/service logic, and shape HTTP responses; they should not duplicate domain policy.
- `app/security/` owns authentication/security helpers. Keep persisted secret loading, configuration predicates, sessions, cookies, and route/middleware behavior behind their existing contracts.
- `app/services/` owns reusable application/domain services. Provider access and persistence should remain explicit dependencies rather than hidden app initialization.
- `app/api/search.py` and `app/api/library.py` are the global search, artist page and library browsing adapters. They call `discovery/search/` and hold no matching or ranking logic.

### Global search (`discovery/search/`)

- `normalize.py` owns name keys and query normalization; `index.py` owns the in-process owned index, its single-flight background build, last-known-good state, and song paging; `query.py` owns matching, ranking, library pages, cursors and artist lookup; `events.py` owns capabilities, SSE framing and the search stream; `artist_page.py` owns artist sections.
- The index is keyed by the Navidrome credential generation (`navidrome_generation` in settings). Requests read the last completed build and never wait for one. Provider sources are not wired yet (contract P2).
- Contract: `docs/SEARCH_CONTRACT.md`, section 11 for the P1 record.

### Legacy server and domain helpers

- `navidrome_server.py` remains a large compatibility/orchestration boundary used by existing callers. It coordinates provider/library access, cache and persistence dependencies, discovery routes/tools, and acquisition wiring.
- Root-level `discovery_*.py` modules own extracted discovery policies and payload transformations, including New Releases candidate selection/merge/window/query/response rules, classics candidate collection/rating/genre stages, personal recommendation allocation/payload shaping, and cached discovery-list projection.
- Root-level `acquisition_*.py` modules own extracted acquisition state, candidate validation/start, request coordination, lifecycle, orchestration, recovery, watcher, progress accounting/snapshots, diagnostics, completion, import, cleanup, and source-switch responsibilities.
- `navidrome_client.py`, `integrations/lastfm/client.py`, `integrations/listenbrainz/client.py`, `slskd_client.py`, `musicbrainz_*.py`, `slskd_*.py`, and cache/settings modules isolate provider protocols or supporting policies where extracted.
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

## Modularization disposition

The planned domain modularization and Python package-layout migrations are complete. Do not resume size-only extraction work. Historical boundaries and closeout evidence are retained in [the archive](archive/completed/MODULARIZATION_ROADMAP.md) and root `PROJECT_LOG.md`. Current outstanding work is listed in [`ACTIVE_WORK.md`](ACTIVE_WORK.md); required verification is in [`TEST_PLAN.md`](TEST_PLAN.md) and release gates are in [`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md).
