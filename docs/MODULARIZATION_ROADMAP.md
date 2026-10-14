## 2026-10-14 — PR #57 merged: acquisition watcher lifecycle

PR #57 was squash-merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. The watcher loop now lives in acquisition_watcher.py behind injected services, with the legacy MCP/web adapter preserved. Direct-import regression tests cover dismissal/recovery exits, completed transfer evidence without a verified folder (no import), and verified-path handoff to the existing safe import coordinator. Docker packaging is updated. All four required workflows passed on that exact head: syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, runtime smoke 38605511271, and validation-only multi-architecture 38605510906 (publishing paused). No separate local test run, live slskd test, production filesystem action, publication, deployment, or production runtime verification is claimed.

**Next priority:** persistent acquisition-state coordination after extracting watcher startup. Keep the strict completion matcher, safe import coordinator, cancellation/cleanup refusal behavior, and MCP compatibility unchanged.

# Modularization Roadmap

Last updated: 2026-10-14

## Acquisition state persistence extraction (PR in progress)

`acquisition_state.py` owns the SQLite mechanics for saving and listing acquisition rows behind injected initialization, database path, identity-key, and clock dependencies. Legacy `_discovery_save_acquisition_job` and `_discovery_list_acquisition_jobs` remain compatibility adapters. The transition lock, conditional dismissed-state checks, secondary For Me feedback projection, dismissal/import coordination, and all filesystem safety operations remain in `navidrome_server.py`; this extraction must not be interpreted as moving those responsibilities. Direct-import tests cover round-trip persistence, normalized identity, preservation of candidate/settings/quality metadata on partial updates, invalid identity rejection, and malformed stored JSON. Exact-head CI and final diff review remain required before merge.


## Priority override — acquisition lifecycle correctness and safety

PR #51 and PR #53 established refusal and neighbor-preservation coverage for destructive dismissal cleanup. PR #54 extracted cleanup to `acquisition_cleanup.py` with direct-import regression tests; exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows and merged at `982e39122a401b8b68d75e38423dbb93711b4abd`. PR #55 extracted interrupted-import recovery to `acquisition_recovery.py`; exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed all four workflows and merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`. PR #56 extracted source-switch orchestration to `acquisition_source_switch.py`; exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed all four workflows and merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`. All three retain the legacy MCP/web adapters and were added to Docker packaging. The next safety priority is to extract the watcher loop and top-level acquisition coordination with direct-import tests, while preserving cleanup refusal, mount identity, manifest/rollback, and uncertain-queue invariants. The reported HTTP 409 remains deferred because it was not reproduced. No live slskd or production-folder recovery/cleanup is claimed.

## Goal and guardrails

Reduce coupling in the Python application through small, behavior-preserving extractions. GitHub is the source of truth. Preserve the web API/UI, authentication, settings and persistent state, acquisition safety, and any existing caller until its replacement is verified. New extracted modules should have direct-import regression tests. Do not remove tests simply because their current AST-based setup is awkward.

The delivered product's target is web-only. MCP retirement is a later step: the web application still imports navidrome_server.py, so do not remove the legacy module/runtime until web callers have been redirected to importable domain/service modules and a repository-wide usage audit confirms MCP-only code can be removed safely.

## Completed domain extractions

- PR #24 — acquisition completion matching: acquisition_completion.py; direct tests for filename identity and completed-folder inspection.
- PR #25 — slskd search and quality: slskd_search.py and slskd_quality.py.
- PR #27 — acquisition import safety: acquisition_import.py, including path/storage guards, no-overwrite behavior and rollback.
- PR #28 — discovery recommendation rules: discovery_recommendations.py.
- PR #29 — discovery list persistence: discovery_store.py.
- PR #30 — discovery refresh coordination: discovery_refresh.py.

These extractions are merged to main. They do not mean the monolithic server or web module is fully modularized.

## Acquisition lifecycle extraction — in progress

PR #47 introduces `acquisition_lifecycle.py` as a dependency-light, directly importable owner for monitor-resume eligibility, conservative cleanup classification, skip-request validation, fallback queue payload normalization, and uncertain queue-error classification. Legacy MCP functions remain compatibility adapters and continue to own database/network/filesystem I/O.

This is the first lifecycle seam, not completion of the whole orchestration extraction. Cleanup, interrupted-import recovery, and source-switching now have directly importable implementations with compatibility adapters. The watcher loop, persistent state coordination, watcher startup, and top-level acquire coordinator still live in `navidrome_server.py`. Next, extract those paths behind injected service dependencies and migrate remaining AST-coupled tests incrementally. Keep the existing completion/import safety modules as the filesystem authorities.

## Current route-separation stage

1. Settings routes (merged in PR #33): move the Navidrome, Last.fm, ListenBrainz and slskd settings handlers to app/api/settings.py; preserve URLs, methods, payload defaults, error codes/messages and calls into existing domain functions. Keep parse_result importable from app.main while moving its implementation to app/api/utils.py.
2. Acquisition routes: extract /api/acquire* and /api/acquisitions* with safety and streaming tests. Keep destructive logic in domain services. **PR #34 (`refactor/acquisition-api-router`):** merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`. Syntax, Docker packaging/full unit tests, runtime smoke, and validation-only multi-architecture checks all passed on that exact head.
3. Discovery routes: **PR #35 merged** at `d61162b29c6f0cccc97aefe9c779567e671651b2` from exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`. Extracted recommendations, discovery-list retrieval, refresh, and feedback handlers into `app/api/discovery.py`; direct-import regression coverage is in `tests/test_discovery_routes.py`. All four required workflows passed on that exact head. Preserve ownership filtering and refresh/feedback semantics.
4. Metadata routes/services: **PR #36 merged** at `15011614649470c9c71734422b95ee048fbf9f3c` from exact head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`. Artist bio, artwork, album details/year, and external HTTP/cache helpers now live in `app/api/metadata.py`; regression coverage is in `tests/test_metadata_routes.py` and `tests/test_artwork_retry.py`. All four required workflows passed on the corrected exact head.
5. Authentication and app assembly: only split auth after explicit dependencies for persistent settings, session signing and middleware have been identified and covered. Keep middleware/public-path behavior unchanged. **PR #37 merged** at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3` from exact head `192b084850ecbe0137b64b3dae9d07e0471198b4`. Security primitives (persistent signing secret, username/password validation, PBKDF2 digest, signed-session generation/validation) now live in `app/security/auth.py`; routes, cookie setup, and middleware remain in `app/main.py`. All four required workflows passed on the exact head. PR #38 merged at `84da7ebfe51199a5caf63f7689fe89df8d61b553` after all four exact-head workflows passed; its new `tests/test_auth_routes_integration.py` covers setup, login/logout, rate limiting, cookie policy, session reuse/tampering, and public/protected paths. PR #39 (`refactor/auth-api-router`) was squash-merged at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact head `9187a51380d2a7ed7d27276ce4505827becaed32`. It extracts status/setup/login/logout and the login page into `app/api/auth.py`; middleware and signing helpers remain in `app/main.py` and `app/security/auth.py`. All four required workflows passed on the exact final head: syntax (`38492677728`), Docker packaging/full suite (`38492677704`), runtime smoke (`38492677708`), and validation-only multi-architecture (`38492677825`).
6. Frontend assets: **completed in PR #41**, squash-merged to `main` at `410506ea76d7181aa300edb9c05ebbd337dd7159` from exact tested head `b94dde68cccef776cea3813dbe7310eb857d170b`. Login/main HTML is in `app/templates/`; CSS/JavaScript is in `static/`; Docker packaging and auth middleware public-asset rules are updated, with regression coverage for asset delivery and external references. All four required exact-head workflows passed, and the manual report recorded eight checklist items passing. User reports navigation is noticeably snappier and no errors occurred. A distinct deliberately induced error/recovery scenario was not reported and is not claimed. See `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md` for the verification boundary.
7. MCP retirement: audit all imports, entry points, dependencies, tests and docs. Remove MCP registration and MCP-only runtime/dependencies only after the web app no longer relies on navidrome_server.py as its domain API. Keep compatibility wrappers until every consumer is migrated.

## Remaining `navidrome_server.py` dependencies — audit 2026-10-14

The current web application still imports the monolith as its domain API. Treat this as the dependency inventory and sequence for remaining work; re-check current `main` and callers before implementation.

### Direct web callers

- `app/main.py`: imports `navidrome_server as librarian`; uses `DATA_DIR`, settings read/write, `api_call` for health, discovery-list retrieval, and album-candidate filtering for dashboard picks.
- `app/api/settings.py`: delegates Navidrome, Last.fm, ListenBrainz, and slskd settings reads/writes and connection tests to legacy functions.
- `app/api/discovery.py`: delegates recommendation generation, discovery-list retrieval/refresh, feedback, and album eligibility.
- `app/api/acquisitions.py`: delegates acquisition status, source skipping, dismissal, album acquisition, and slskd candidate queueing.
- `app/api/metadata.py` no longer imports the monolith; its route/provider helpers are extracted.

### Hidden runtime and test coupling

- Importing `navidrome_server.py` also imports/instantiates `MCPServer` and registers MCP tools. Therefore the FastAPI runtime pulls in MCP code despite the web Docker entry point running Uvicorn.
- The web Dockerfile copies `navidrome_server.py`; `requirements.txt` includes the MCP package. `server.py` is another MCP-related entry point and must be checked before any repository-wide claim that MCP is unused.
- `tests/test_acquisition_safety.py` uses AST parsing to extract named functions from `navidrome_server.py`, remove decorators, and execute them in a stub namespace. This makes tests sensitive to function location and names. Replace this coverage incrementally with direct-import tests of extracted implementations; preserve lifecycle, cleanup, path-validation, no-overwrite, rollback, and unsafe-failure cases.

### Recommended implementation order

1. **Acquisition lifecycle/orchestration and test migration.** Extract state transitions, persistence coordination, candidate/source selection, queue/skip/dismiss/failover, completed-import coordination, and recovery behind importable domain interfaces. Keep destructive operations fail-safe and preserve existing callers with adapters until verified.
2. **Settings, configuration, and service access.** Separate persistent settings operations and Navidrome/slskd/Last.fm/ListenBrainz integration from MCP registration. Preserve secret handling, data-directory behavior, defaults, validation, and errors.
3. **Discovery orchestration.** Connect existing recommendation, store, and refresh modules through service interfaces; extract remaining list construction, feedback, provider integration, and inventory access without duplicating domain logic in routes.
4. **Application assembly.** Remove `app/main.py`'s remaining dependency on the monolith for settings/auth persistence, health checks, and dashboard discovery behavior. Keep middleware and public/protected route behavior unchanged.
5. **MCP retirement.** Only after web callers and tests no longer depend on the monolith, audit all imports, entry points, dependencies, tests, docs, and compatibility needs. Remove MCP registration/runtime dependencies only when each web-required behavior has an independent tested owner.

### Acceptance gates for each extraction

- Direct-import regression tests exercise the extracted implementation; no parallel copy of domain behavior in the web layer.
- Preserve MCP compatibility until the separately verified retirement step.
- For acquisition changes, cover both successful behavior and unsafe failure cases, including traversal/symlink escape, ambiguous targets, unrelated files, cleanup refusals, import rollback, and interrupted lifecycle recovery where applicable.
- Run focused tests, `python -m unittest discover -s tests -v`, syntax checks, and applicable Docker/API/runtime checks. Verify all required CI on the exact final PR-head SHA.
- Review all changed callers and the complete diff. Update this roadmap, project status/log, and test/architecture docs with actual evidence; never infer test success from compilation or a successful container start.

## Testing and release gates

For each route extraction:
- Add direct-import tests for payload adaptation, status codes, sanitized failures and compatibility defaults.
- Run focused tests, full python -m unittest discover -s tests -v, syntax checks, and Docker build/runtime CI.
- Review the complete diff and verify CI on the exact final PR head.
- UI-affecting changes require manual browser testing after automated CI succeeds.

Docker runtime smoke and multi-architecture build validation remain enabled. GHCR publication is intentionally disabled until the modularization roadmap is complete and the user explicitly authorizes release. Validation/build success does not mean an image was published or deployed.

## Current status

Domain extractions through PR #30 and route/frontend stages through PR #41 are merged as recorded above. Acquisition safety/orchestration has since advanced through merged PRs #47, #50, and #54–#56. PR #54 extracted safe dismissal cleanup, PR #55 extracted interrupted-import recovery, and PR #56 extracted source-switch orchestration; each exact PR head passed all four required workflows and each final diff was reviewed before merge. The watcher loop, persistent acquisition-state coordination, watcher startup, and top-level acquire coordinator remain in `navidrome_server.py`. The next implementation priority is to extract those lifecycle paths behind injected dependencies with direct-import regression tests, preserving cancellation/cleanup refusal, uncertain queue outcomes, import rollback and filesystem identity checks, persistent state transitions, and MCP compatibility. Then continue with settings/service boundaries, discovery orchestration, application assembly, and only then assess MCP retirement. GHCR publication remains disabled until the roadmap is complete and release is explicitly authorized. No local test run, live slskd interaction, production filesystem recovery/cleanup, publication, deployment, or production runtime verification is claimed for PRs #54–#56.


## Stage 7 — FastAPI route separation: settings routes

PR #33 extracts settings handlers to app/api/settings.py and the shared response adapter to app/api/utils.py. The app.main.parse_result symbol remains available as an imported compatibility name. Regression coverage in tests/test_settings_routes.py checks all 12 endpoint/method pairs, payload mapping, defaults, validation failures, and sanitized errors. Remaining route groups and later MCP retirement stay separate roadmap items; do not remove the legacy server until callers and compatibility are verified.


## 2026-10-14 — Acquisition lifecycle/orchestration dependency status

- PR #47's lifecycle policy extraction is merged at `1877dca3187f7cbde85b211d5414e558f12da502`.
- PR #48's orchestration extraction remains pending. Its current branch/head `refactor/acquisition-lifecycle-orchestration` / `115e1f9373744d361a20f0ba20c35589db0ca099` retains the pre-squash PR #47 history; the diff against current `main` includes both lifecycle and orchestration changes, and GitHub reports it is not mergeable.
- The four required workflows passed on that existing head only; do not carry that CI claim over to a reconstructed branch. No merge of PR #48, publication, deployment, or runtime verification is claimed.
- **Required next step:** reconstruct PR #48 as an orchestration-only change based on current `main`; inspect all callers, direct regression tests, Docker packaging, MCP compatibility, and filesystem safety behavior; then verify all required workflows on the exact new head before merge.


## 2026-10-14 — Reconstructed acquisition orchestration slice

PR #49 has been merged to `main` at `c972278566d8ec68f3755f464df1afb5a8a18f56`. PR #48's original branch still contains pre-squash history and is not the source for a direct merge. The reconstructed branch `refactor/acquisition-orchestration-reconstructed` starts from updated `main` and carries only the persisted source-skip orchestration seam, its direct regression tests, Docker packaging, and focused documentation. Keep the MCP adapter, shared transition lock, conditional downloading-state update, and existing filesystem safety modules unchanged. All four required workflows passed on final PR #50 head `9185f3c12ace7c82a61ff04c062044ab9c33cdf6` (syntax `38587910860`, Docker packaging/full unit suite `38587910842`, runtime smoke `38587911440`, multi-architecture validation `38587911187`). The reconstructed diff is ready for merge review; no reviewer submissions or inline threads were present at the time of inspection. PR #50 remains unmerged.


## 2026-10-14 — Persisted acquisition source-skip orchestration merged (PR #50)

PR #50 was squash-merged at `a37d29cf11657dce6d5cbc6cb928ca840fe5b206` from exact PR head `c8610fdc44ea93bcfb55a654598792aee78e7ecb`. All four required workflows passed on that exact head: Python syntax `38589006636`, Docker packaging/full unit suite `38589006609`, container runtime smoke `38589006569`, and validation-only multi-architecture image validation `38589006620`. The extracted module owns only the persisted manual source-skip transition; the MCP adapter, shared transition lock, conditional downloading-state update, and existing filesystem safety authorities remain. Watcher orchestration, source switching, cleanup execution, interrupted-import recovery, and top-level acquisition coordination remain future work. No image publication, deployment, or production runtime verification occurred.


## 2026-10-14 — Watcher extraction merged (PR #57)

PR #57 was squash-merged at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. The watcher loop now lives in acquisition_watcher.py behind injected services, with the legacy adapter preserved. All four required workflows passed on the exact head. See the merge closeout below for run IDs and verification boundaries.


## Acquisition watcher startup extraction — PR #58

- PR: https://github.com/abucalip/navi-librarian/pull/58; branch `refactor/acquisition-watcher-startup`; tested head `3f072159ef9e61f70554d315277a612005b8de4e`.
- Extracted reserve → persist → status → start into `acquisition_watcher_startup.py` with injected locks, active set, persistence/status callbacks, and watcher entry point. `navidrome_server.py` retains `_discovery_start_import_watcher` as a compatibility adapter with its existing return contract.
- Direct-import regressions cover dismissed/duplicate starts, credential filtering in persisted settings, persistence failure releasing the reservation, and thread-start failure recording `monitor_error` and releasing the active marker. Docker packaging and architecture documentation are updated.
- All four required workflows passed on the exact head: syntax/acquisition safety `38609940832`, Docker packaging/full unit suite/build `38609940860`, container runtime smoke `38609940739`, and validation-only multi-architecture build `38609940737` (publishing paused).
- State: implementation and CI passed; PR remains open/unmerged. No separate local test run, live slskd test, publication, deployment, or production runtime verification is claimed.
- Next priority: persistent acquisition-state coordination with direct-import regression coverage, preserving conditional writes, shared transition-lock behavior, and dismissal/import safety.
