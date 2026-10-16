## slskd connectivity probe — extraction in progress (PR #187)

`slskd_client.test_connection(config_reader, http_get=...)` owns the connection probe request and the established JSON status mapping. `navidrome_server.discovery_test_slskd_connection()` remains the compatibility adapter and supplies the existing configuration reader. The API-key header is used only for the outbound request and is not returned in responses. Direct-import regressions and Docker packaging are added. Exact-head CI and merge are pending; no live slskd call was made.

## slskd live progress calculations — extracted (PRs #182–#183)

`slskd_transfers.summarize_transfer_progress()` owns pure aggregation of matched expected/tracked records into completed-track count, total/transferred bytes, and actual-counter snapshots. Completed states may infer a file's transferred bytes for display totals, but those inferred bytes are deliberately excluded from speed snapshots. `slskd_transfers.estimate_transfer_speed()` calculates the delta-based bytes/second estimate from current counters and a prior snapshot/time. `navidrome_server.py` still owns the HTTP call, expected/tracked matching invocation, snapshot key, shared snapshot storage/lock, and public progress response.

- PR #182 tested head `045131f58365dd0e6538c1712f37f56f639c65ad`, merged `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`; all four required exact-head workflows passed.
- PR #183 final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`, merged `e4e9bd1fad9536f00f3908d753b66147d30ca03f`; all four required exact-head workflows passed. Docker packaging CI ran 342 unit tests successfully.
- The legacy progress response, snapshot locking, and counter-reset behavior remain in place. No publication, deployment, or production runtime verification is claimed.

## Recommendation style classification — extracted (PR #171)

`discovery_recommendations.py` owns the pure `genre_families()`, `recent_style_families()`, `primary_recent_family()`, and `classify_diversity_style()` rules used by `recommend_new_music()`. The server imports these helpers inside the recommendation operation; scoring, provider I/O, candidate quotas, persistence, and the legacy MCP response remain in their existing owners. PR #171 merged at `6d00562405320affcb1a04b4359397b332cd5bf5` from exact tested head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9`. All four required workflows passed on that exact head.

## Last.fm album popularity — extracted (PR #172)

`lastfm_client.LastFmClient.album_popularity()` owns the cached Last.fm `album.getInfo` request, statistics/tag normalization, and lookup diagnostic mapping. It preserves the legacy `lastfm:album-info-v2` cache identity, 30-day TTL, 12-second timeout, direct/nested stats compatibility, and 404-as-silent-miss behavior. `navidrome_server._lastfm_album_popularity()` remains the compatibility adapter that updates `LASTFM_LAST_ERROR`. PR #172 merged at `d5153a3fe0625bc52b5896e87846b55cabe58e81` from exact tested head `d2808d44825e949ff71ed8471d25cee6570b54f1`; all four required workflows passed on that exact head.

## MusicBrainz tag audit — extracted (PR #170)

`music_tag_audit.scan_missing_mbids()` owns the bounded, read-only scan and receives the audio reader as a dependency. `navidrome_server.find_missing_mbids()` remains the legacy JSON/error-string adapter. The module is included in Docker packaging; direct-import tests cover tag interpretation, pagination, unreadable files, validation, and read-only behavior. PR #170 merged at `dbbdda35792fd569cfdeec2c4c7b42fc106f84e3` from exact tested head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07`; all four required workflows passed on that exact head.

---

## slskd transfer listing service — extracted (PR #157)

`slskd_transfers.py` owns the HTTP transfer-list request and recursive normalization into flat file records carrying `_transfer_directory`. It receives the HTTP client as an injected dependency and does not initialize the application. `navidrome_server._slskd_download_transfer_files(base_url, headers, username)` remains the compatibility adapter used by candidate-start validation. PR #157 merged at `17922f878f0ea391b47652012a38530e9eb044fc` from exact tested head `504b10392061dbc44d28d66e663b88cbefb8f1a4`. All four required workflows passed on that exact head. Deployment remains unverified.

## Expected slskd track count — extracted (PR #155)

`slskd_search.py` owns expected track-count metadata parsing. `navidrome_server._discovery_expected_track_count()` remains a compatibility adapter for the acquisition coordinator. PR #155 merged at `d732241de9edfd3c643a8fa89fb25c42b2a93c67` after all four required workflows passed on exact head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`. Deployment remains unverified.

## Music path default policy — extracted (PR #151)

`music_paths.py` owns the pure decision policy for configured music path and host mount fallback. It receives environment and directory-existence behavior from the caller, so importing it does not initialize application state. `navidrome_server._default_music_dir()` remains a compatibility adapter. Direct-import tests and Docker packaging are included; all four required exact-head workflows passed before merge. Deployment remains unverified.

## 2026-10-15 — Navidrome HTTP client extraction in progress

- `navidrome_client.py` owns Subsonic-compatible request authentication, HTTP request execution, and API response error interpretation.
- The client receives the existing settings provider as a dependency; it does not load settings or initialize the application itself.
- `navidrome_server.api_call(method, **params)` remains the compatibility adapter, preserving the legacy callable signature and existing callers, including MCP-facing discovery functions.
- Direct-import tests cover deterministic token generation, request parameters/options, successful payloads, and API error formatting. Docker packaging includes the module. CI and merge are pending; no test result is claimed before workflows run on the exact final PR head.

## 2026-10-15 — MCP tool registration separated from shared service imports

- Moved the 27 existing MCP tool registrations into the new mcp_registry.py; navidrome_server.py no longer imports MCPServer, constructs an MCP server, or decorates service functions at import time.
- The legacy MCP entry point remains compatible: when navidrome_server.py is executed directly, it creates the server through create_mcp_server() and runs on the existing streamable HTTP host/port. Tool names and function objects are kept in an explicit ordered registry.
- The web service can now import navidrome_server.py without loading mcp.server.mcpserver. MCP registration is deferred to explicit server startup; the MCP package and legacy tool surface are retained.
- Added tests/test_mcp_registry.py to assert the registry contains 27 unique tools, registers each provided function exactly once, and importing the legacy service keeps all registered functions callable without importing the MCP SDK.
- Branch: refactor/separate-mcp-tool-registration. All four required workflows passed on exact implementation/documentation head fe71a9a19188a018a2ee65d5b313a99413d239f2: Python syntax/acquisition safety run 38783091362; Docker packaging/full suite/build run 38783091326; container runtime smoke run 38783091309; validation-only multi-architecture run 38783091337. Publishing remains paused. No separate local test execution, deployment, or production runtime verification is claimed. PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00 from exact final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f. All four required workflows passed on that exact head: syntax/acquisition safety 38783296279; Docker packaging/full suite/build 38783296173; container runtime smoke 38783296256; validation-only multi-architecture 38783296249. Publishing/deployment remain paused; no production runtime verification is claimed.

## Proxmox MCP command allowlist — PR #114 merged

The separate root-level `server.py` is a host-side Proxmox MCP entry point and is not copied into the Librarian application image. Its `run(command)` tool previously forwarded arbitrary caller input to SSH despite describing the input as allowlisted. PR #114 adds a standalone strict allowlist for the documented diagnostic forms and refuses all other input before subprocess invocation. The MCP tool schema, SSH target/options, timeout, and output truncation for accepted commands are unchanged.

PR #114 exact head `cd8319696180875a3cb6f0dc151d88e0c8c490d7` passed syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`. Squash merge: `6ab848d444373dfa37e6d46528a2840a53a8f763`. No live Proxmox command, publication, or deployment was performed.


---

## 2026-10-15 — PR #108 merged: discovery router service injection

- `app/api/discovery.py` uses `Depends(get_librarian)` from the shared lazy dependency module, matching the acquisition router. Importing the discovery router no longer imports `navidrome_server.py` directly.
- Existing discovery functions still own recommendations, list generation, candidate filtering, and feedback persistence. `app/main.py`, settings routes, and MCP runtime retain their legacy server integration; no MCP tools or domain behavior were removed.
- PR #108 merged at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` from tested head `a5170e50080c0ca94b4068155ace83fd33c6f029`; all four required CI workflows passed. PR #112 was squash-merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No publication, deployment, or production runtime verification.

---

## 2026-10-15 — Web/MCP dependency boundary audit

- Direct server coupling remains in `app/main.py`, `app/api/acquisitions.py`, `app/api/discovery.py`, and `app/api/settings.py`. These are adapters around the existing `discovery_*` service surface, and preserving that surface is important for MCP compatibility.
- `app/api/auth.py` already uses a router factory with injected settings/session/password dependencies; `app/api/metadata.py` is independent of the legacy server. These are useful patterns for a future service-injection boundary.
- The main app still uses server-owned `DATA_DIR`, settings access, Navidrome ping, discovery list retrieval, and album-candidate filtering. Route tests currently patch each module's `librarian` binding, so an injection refactor must migrate these test seams deliberately.
- This was a read-only audit. No MCP retirement, domain relocation, route behavior change, or code extraction was performed.

---

## 2026-10-15 — Import source-root safety merged (PR #103)

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- Import pins source and destination-parent directory chains with no-follow flags, validates matched file identities, and uses descriptor-relative staging, publication, and rollback. Cross-filesystem copy fallback remains supported.
- The source-root symlink-swap, collision-suffix, cross-filesystem, and rollback regressions pass with all four exact-head workflows. No production-folder test or deployment is claimed.

---

## 2026-10-15 — Cleanup root traversal hardening merged (PR #100)

- PR #100 extends the directory-swap defense by opening the configured absolute root from `/` one component at a time with no-follow directory flags and checking its preflight device/inode identity after external callbacks.
- Cleanup validates the exact planned entries and file identities/sizes, then unlinks relative to the pinned target descriptor. Regressions cover target-folder and ancestor-folder symlink swaps. Exact-head CI passed; no production-folder deletion test is claimed.

---

## 2026-10-15 — Acquisition cleanup filesystem boundary hardened

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- `acquisition_cleanup.py` now uses no-follow directory descriptors and descriptor-relative unlink/rmdir after external transfer callbacks; device/inode checks reject a changed directory or file. The symlink-swap regression and all four required exact-head workflows passed. No production deletion test or deployment is claimed.

---

## 2026-10-15 — Acquisition request coordinator merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- The coordinator owns request decision sequencing through injected dependencies. The legacy MCP/web adapter, shared locks/state, persistence, watcher lifecycle, and acquisition implementation retain their existing ownership boundaries. All four required workflows passed on the exact PR head.

---

## 2026-10-15 — Last.fm settings policy boundary merged

- PR #97 merged at `ad239a59b77612b812ca842406fee7b47cf80889` from exact tested head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`.
- `service_settings.py` owns Last.fm API-key update policy behind injected settings read/write callbacks. `discovery_set_lastfm_settings` remains the MCP/web adapter with its existing signature and JSON response; SQLite persistence/schema and connectivity testing remain in `navidrome_server.py`.
- Responses expose only `api_key_configured`, never the key. Exact-head CI passed all four required workflows; no publication, deployment, or production runtime verification.

---

## 2026-10-15 — slskd settings policy extracted (PR #96)

- `service_settings.py` now owns the pure slskd configuration validation, safe settings serialization, and update policy behind injected persistence/path callbacks. `navidrome_server.py` retains MCP adapters and remains the owner of SQLite persistence, connection tests, and runtime `MUSIC_DIR`.
- Quality priority validation rejects invalid tiers before writes. The API key remains write-only in settings responses, and the runtime music directory changes only after settings persistence succeeds.
- Exact implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four required workflows; the documentation-updated head must be checked again before merge. The web app still imports the legacy module, so MCP retirement is not in scope.

---

## 2026-10-15 — Settings-policy boundary follow-up

- PR #95 moved Navidrome, ListenBrainz, and Last.fm settings policy to direct-import `service_settings.py`; legacy MCP/web adapters and persistence ownership remain in `navidrome_server.py`.
- The next extraction moves only slskd configuration validation and settings read/update policy behind injected callbacks. HTTP connection testing, SQLite persistence, and the global music-path owner stay in the legacy module. This remains an incremental boundary; the web app still imports `navidrome_server.py` and MCP retirement is not in scope.

---

## 2026-10-15 — Service settings policy extracted

- `service_settings.py` now owns injected, directly testable policy for Navidrome configuration validation/settings serialization/update, ListenBrainz username validation/settings update, and Last.fm configured-status serialization.
- `navidrome_server.py` keeps its existing MCP-decorated public functions and private compatibility helpers as adapters. It remains the owner of SQLite settings persistence, global `MUSIC_DIR` updates via an injected callback, network connectivity checks, and the remaining settings functions.
- The Dockerfile copies `service_settings.py`; tests now import it directly rather than AST-executing functions from the legacy server. This is an incremental seam, not removal of MCP initialization from the web import path.

---

## 2026-10-15 — Web dependency audit: settings-policy boundary

- The web layer currently imports `navidrome_server.py` directly in `app/main.py` and in the acquisitions, discovery, and settings routers. Main uses legacy persistence/configuration, Navidrome API access, discovery-list retrieval, and album eligibility; routers delegate to the corresponding legacy settings/discovery/acquisition functions.
- The legacy module both owns domain orchestration and registers MCP tools, so the web process imports MCP setup as a side effect. Separately, `server.py` starts a read-only MCP server and `requirements.txt` pins `mcp==2.3.0`; the Docker image does not include `server.py`. These are distinct compatibility/deployment facts, not authorization to remove MCP.
- The first small seam is settings policy currently covered by AST execution in `tests/test_service_settings.py`. Move the six functions to a directly importable module using injected persistence and path dependencies. Keep database lifecycle, global `MUSIC_DIR` updates, connection tests, and the existing MCP-facing adapters in the legacy layer for now.
- Do not make a broad import inversion in the same change. Expand service/domain separation incrementally with direct tests for each extracted behavior.

---

## 2026-10-15 — Dismissal-serialized import guard merged (PR #78)

- `acquisition_orchestration.import_source_unless_dismissed` owns the transition-lock/dismissal/callback guard. `navidrome_server.py` retains the compatibility adapter and the filesystem-safe import coordinator.
- PR #78 exact tested head `e6a609ca7381d0751d529b52f55aeebd56d76661` passed all four required workflows; squash merge `5d638c7adf5a42fdac8052cb4fc223236564cd72`. No filesystem safety logic was moved.

---


## 2026-10-15 — Search polling extraction merged (PR #76)

- `slskd_search_polling.py` now owns progressive query submission, search-state/response polling, count aggregation, peer payload deduplication, delayed-payload waiting, and per-attempt diagnostics behind injected external dependencies.
- `navidrome_server.py` remains responsible for configuration, candidate interpretation, acquisition status, queueing, and lifecycle transitions. The legacy MCP/web adapter contract is unchanged.
- PR #76 exact tested head `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6` passed all four required workflows; squash merge `a55a9fa7eed1e221f52434b50f44d0c415fd491a`.

---

## 2026-10-15 — Search polling boundary

- `slskd_search_polling.py` owns the slskd progressive-query/poll/wait algorithm behind injected HTTP, clock, sleep, ID-generation, and response-normalization dependencies. The server coordinator continues to own configuration, candidate interpretation, status reporting, queueing, and acquisition state transitions.
- The Docker image and Python syntax workflow must include this module. Keep the legacy server adapter and MCP/web return contract unchanged.

---

# Architecture

Last updated: 2026-10-14

## Overview

```text
Browser
  │ HTTP
  ▼
FastAPI web app (app/main.py) ───────► Navidrome API
  │                                    (external service)
  │ calls existing Python functions
  ▼
navidrome_server.py ─────────────────► slskd API
  │                                    (external service)
  ├── discovery orchestration and external-data enrichment
  │     └── discovery_recommendations.py (pure eligibility/scoring/diversity rules)
  ├── acquisition and import helpers
  ├── settings and persistent state
  └── MCP tool definitions (separate entry point)

Docker volume /data  ──► app database and authentication key
Host music directory ──► /music
Host completed downloads ──► /downloads
```

The diagram is logical, not a promise that every helper uses only those mount paths. Confirm actual path resolution in code before changing mounts or permissions.

## Remaining legacy-server coupling (audit 2026-10-14)

The diagram above shows the logical boundary, but the current implementation still imports `navidrome_server.py` from `app/main.py`, `app/api/settings.py`, `app/api/discovery.py`, and `app/api/acquisitions.py`. Metadata routes have been separated. These imports make the web runtime initialize MCP-related code because the legacy module creates an `MCPServer` and registers tools.

The web application still delegates settings persistence and service checks, discovery generation/list/feedback behavior, and acquisition lifecycle orchestration to the monolith. The Dockerfile copies the legacy module and `requirements.txt` includes MCP. `server.py` is also an MCP-related entry point and needs a caller/usage check before MCP dependencies are removed.

`tests/test_acquisition_safety.py` is coupled to the monolith's source layout through AST extraction. Migrate this coverage incrementally to direct-import tests of extracted domain modules; do not drop safety or lifecycle cases during migration.

Retirement condition: all web-required behavior must have an independent tested domain/service owner, all web callers must use those interfaces, and a repository-wide audit of imports, entry points, dependencies, tests, docs, and compatibility must establish that MCP-specific code can be removed safely.

## Main components

- **`app/main.py`** — FastAPI routes and the web UI. It adapts existing librarian functions for browser/API use.
- **`navidrome_server.py`** — discovery orchestration, Navidrome/slskd integration, acquisition lifecycle, settings, persistence, and legacy MCP tools.
- **`acquisition_completion.py`** — strict completed-track matching, filename identity, and completed-folder inspection.
- **`slskd_search.py` / `slskd_quality.py`** — importable slskd query/candidate helpers and audio-quality classification.
- **`discovery_refresh.py`** — refresh coordination for personal and named cached discovery lists; list builders, provider calls, server-owned locks, and persistence are injected.
- **`discovery_recommendations.py`** — pure discovery eligibility, normalization, scoring, and diversity helpers with direct-import tests.
- **`acquisition_lifecycle.py`** — importable lifecycle policy for monitor recovery, cleanup-required classification, skip validation, fallback payload normalization, and queue-error classification. The legacy server adapts these policies while database/network/filesystem orchestration is extracted incrementally.
- **`acquisition_state.py`** — dependency-injected SQLite persistence and decoding for acquisition job rows; legacy server adapters retain transition locks, conditional state transitions, and secondary feedback projections.
- **`acquisition_watcher_startup.py`** — dependency-injected watcher reservation, persisted state/status, and thread startup; the legacy adapter supplies locks and runtime callbacks.
- **`acquisition_import.py`** — staged filesystem import of verified album tracks, no-overwrite checks, storage-identity guards, and rollback; acquisition status/orchestration remains in `navidrome_server.py`.
- **`server.py`** — MCP/server entry point; inspect it before changing how the MCP integration is launched.
- **`tests/`** — automated tests, including acquisition safety, authentication, and service settings.
- **`Dockerfile` / `compose.yaml`** — web-app image and local Compose deployment.
- **`.github/workflows/`** — Python syntax, test/build, and image publishing automation.
- **`PROJECT_LOG.md`** — chronological development handoff; update at the end of each session.

## Runtime boundaries

- Navidrome and slskd are separate services. In the Docker Compose network, use service DNS names where services share that network; otherwise use a reachable LAN URL.
- The app container exposes port 8080 internally. The host port is configurable using `WEB_PORT`.
- `/data` must be persistent. It stores application state and authentication material; deleting the volume can reset both.
- `/music` and `/downloads` are bind mounts. Their host paths are deployment-specific.
- The image runs as UID/GID 1000. File operations depend on host ownership, mount options, and permissions.
- The web app is started with Uvicorn as `app.main:app`; this does not start the separate MCP server.

## Data and integrations

- Navidrome supplies the user's library context and service API.
- slskd is used for acquisition search, candidate selection/queueing, and download status.
- Last.fm and ListenBrainz are optional discovery/listening-profile integrations, depending on configured credentials and username.
- External metadata/artwork/year/biography lookups are enrichment only. Network failures or missing matches should not break the core discovery flow.
- Some responses are cached in memory for performance; persistent application state is held under the configured data directory. Check the implementation before relying on a particular cache's lifetime.

## Security and file safety

- Never bake `.env`, credentials, auth keys, or local databases into the image.
- Never log or return API keys/passwords to the browser.
- Validate user-provided artist/album/folder data at the API boundary and again where it becomes a filesystem path.
- Acquisition imports and dismiss cleanup are write/destructive operations. Limit them to configured roots and retain tests for traversal, ambiguous paths, incomplete albums, and unrelated files.
- Do not expose the web port directly to the public internet. Prefer LAN access or a trusted private overlay/VPN.

## Architecture change rules

1. Reuse existing domain logic instead of duplicating recommendation/acquisition behavior in the UI layer.
2. Keep route handlers thin: validate input, call a domain function, translate the result to an HTTP response.
3. Add tests at the domain/safety boundary and API boundary for behavior changes.
4. Preserve MCP behavior when refactoring code shared with the web app.
5. Do not modify unrelated services or replace the host's whole Compose file for a one-service change.


## Settings route boundary — PR #33

The settings endpoints for Navidrome, Last.fm, ListenBrainz, and slskd are grouped in app/api/settings.py. The route module adapts HTTP payloads and delegates behavior to existing librarian domain functions. app/api/utils.py owns the shared parse_result adapter; app.main imports that symbol to preserve callers while registering the router. Authentication middleware, URL paths, methods, and response/error contracts are intended to remain unchanged.


## Acquisition route boundary — merged PR #34

The acquisition endpoints (`/api/acquisitions*` and `/api/acquire*`) are being moved to `app/api/acquisitions.py`. The router delegates to existing `navidrome_server` acquisition functions; it does not duplicate lifecycle, slskd, streaming state, or filesystem safety logic. `app.main` registers the router alongside settings routes. This behavior-preserving route extraction is merged. Direct-import regression tests cover route inventory, payload/default mapping, input validation, skip/dismiss status translation, streaming headers, and sanitized errors. All required CI workflows passed on exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`; merge commit is `3aac576c42465420b9c2144c2cd2f4377c5e0ff1`.


## Discovery API route boundary — merged PR #35

The recommendations, cached discovery-list, refresh, and feedback HTTP handlers are grouped in `app/api/discovery.py`. The router adapts request parameters and responses while delegating recommendation filtering, ownership behavior, persistence, refresh coordination, and feedback semantics to existing `navidrome_server` functions. `app.main` registers the router alongside settings and acquisition routes. Direct-import route tests cover route inventory, defaults, validation, payload mapping, and sanitized failures. This extraction preserves existing URLs and delegates domain behavior to existing functions. All four required CI workflows passed on exact PR head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`; merge commit is `d61162b29c6f0cccc97aefe9c779567e671651b2`.


## Metadata API route boundary — merged PR #36

Artist biography, album-year, album-details, and artwork endpoints plus their external-provider HTTP client and in-memory cache/rate-limit helpers are being separated into `app/api/metadata.py`. The router preserves provider matching rules, cache TTLs, MusicBrainz request pacing, and the non-fatal fallback behavior for optional metadata. Regression coverage is in `tests/test_metadata_routes.py` and `tests/test_artwork_retry.py`. All four required workflows passed on exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`; merge commit is `15011614649470c9c71734422b95ee048fbf9f3c`. The initial CI run exposed an AST-based test coupled to the old handler location; the test was updated to exercise the extracted module directly, and all required workflows passed on the corrected head.


## Authentication security primitives — merged PR #37

Pure authentication primitives are being separated into `app/security/auth.py`: persistent signing-secret loading, username/password policy checks, PBKDF2 password digest, and signed-session creation/validation. `app/main.py` retains compatibility wrappers and continues to own persistent-settings access, cookie policy, login/setup/logout routes, rate limiting, and HTTP middleware. The split intentionally avoids changing middleware ordering or public-path behavior. Direct tests cover token signing/expiry, username binding, password hashing, signing-secret persistence, file permissions, and fail-closed handling of an invalid secret; All four required workflows passed on exact PR head `192b084850ecbe0137b64b3dae9d07e0471198b4`; merge commit is `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3`.


## Persisted acquisition orchestration seam — reconstructed PR #48

`acquisition_orchestration.py` owns the persisted manual source-skip transition through injected initialization, lock, database connection, key normalization, lifecycle policy, clock, and JSON dependencies. `navidrome_server.py` retains the MCP-compatible `discovery_skip_acquisition_source` adapter. The shared transition lock and conditional update requiring `status='downloading'` are preserved. Filesystem cleanup/import authorities are unchanged; watcher orchestration, source switching, interrupted-import recovery, and top-level acquisition coordination remain outstanding.


## Acquisition state persistence extraction — PR #59 merged

`acquisition_state.py` now owns SQLite save/list mechanics for acquisition rows behind injected dependencies. Legacy server adapters remain. Shared transition locking, conditional dismissed-state checks, feedback projection, dismissal/import coordination, and filesystem safety remain in `navidrome_server.py`. PR #59 exact head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed all four required workflows and was squash-merged at `730ae16e613f3962c488f87c8de54034db7463dd`. Publishing/deployment/runtime verification are not claimed.

## Settings router dependency seam (2026-10-15)

The settings router now obtains the existing librarian service through `app.api.dependencies.get_librarian`, consistent with acquisition and discovery routers. It no longer imports `navidrome_server.py` directly. The existing service functions remain responsible for settings policy, persistence, and live connectivity checks; HTTP handlers retain request/response adaptation and error mapping. This change does not retire MCP or change the application assembly dependency in `app/main.py`.


## Dashboard and health router boundary (2026-10-15)

The `/api/health` and `/api/dashboard-picks` handlers are grouped in `app/api/dashboard.py` and use the shared lazy `get_librarian` dependency. Navidrome ping, discovery-list reads, and album-candidate eligibility remain delegated to the existing service. Response shapes, count validation, category balancing, deduplication, randomization, and sanitized health errors are preserved. `app/main.py` still imports the legacy server for authentication settings and secret data-directory setup; this extraction is not MCP retirement.


## Dashboard and health router boundary — PR #110 merged

PR #110 moved `/api/health` and `/api/dashboard-picks` into `app/api/dashboard.py` behind the shared lazy `get_librarian` dependency. The extraction preserves the legacy service calls, response shapes, count validation, category balance, deduplication, randomization, and sanitized health errors. Exact tested head `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e` passed all four required workflows and was squash-merged at `b4015b8619f3c0db169722c347f72612996b9a1c`. `app/main.py` still imports the legacy module for authentication settings and data-directory/auth-secret initialization; MCP compatibility and persistence ownership remain unchanged.



## Lazy authentication service dependency — PR #112 verification

`app/main.py` no longer imports `navidrome_server.py` to define the web app. Authentication settings access and signing-key initialization call the existing service lazily through `get_librarian`. SQLite persistence, `DATA_DIR` ownership, settings migrations, MCP wrappers, and auth semantics remain unchanged. Direct integration coverage verifies app import does not initialize the legacy server and auth routes work with an injected fake service.

PR #112 exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed all four required workflows: syntax `38737672741`, Docker packaging/full suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture image validation `38737672689`. No publication, deployment, or production runtime verification.


## Listening profile aggregation — completed (PR #167)

The pure aggregation of ListenBrainz history into the recent-listening profile payload lives in `listening_profile.py`; `recent_listening_profile(days)` remains the legacy MCP-facing adapter. Direct-import tests cover payload shape, counts, empty history, and stable tie order. All four required workflows passed on exact head `ca8f9e4b7decb3404c78f1ee8b8d3078815fd71f`; PR #167 merged at `6b656dc7218280aa0d37e738a881061ceefde55e`.

## Discovery library snapshot — completed (PR #168)

`discovery_library_snapshot.py` owns cached artist/album inventory assembly with injected Navidrome API, collection-normalization, and discovery-store callbacks. The legacy `_discovery_library_snapshot()` wrapper remains in `navidrome_server.py`. Direct-import tests cover cache reuse/schema compatibility, album-ID deduplication, pagination, and the 50,000-album safety stop. All four required workflows passed on exact head `fc69943301c5065a54a0128c8b82ae214cd69dd1`; PR #168 merged at `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`. Publishing/deployment remain paused and unverified.


## Last.fm artist genre parsing — completed (PR #174)

`LastFmClient.artist_genres()` owns cached top-tag retrieval, normalization, case-insensitive deduplication, and the existing eight-tag limit. `navidrome_server._lastfm_artist_genres()` remains a compatibility adapter. Exact-head CI passed on `08c260e2a166a744bbde4009196b53d238afb647`; merged to main at `4dd8b926a7a6cf76e248420860d7c29c892da3c0`. Cache/pacing behavior and discovery grouping remain unchanged.


## Last.fm top albums — extraction in progress

`LastFmClient.artist_top_albums()` owns cached `artist.getTopAlbums` retrieval and response normalization. The legacy `_lastfm_top_albums()` adapter retains discovery-specific eligibility filtering. Exact-head CI and merge pending.


## Last.fm top album retrieval — completed (PR #175)

`LastFmClient.artist_top_albums()` owns cached `artist.getTopAlbums` requests and normalization of returned album metadata. The legacy `navidrome_server._lastfm_top_albums()` remains a compatibility adapter and continues applying discovery-specific album-candidate eligibility filtering. The extraction preserves request pacing, timeout, the 30-day cache TTL, caller-requested limit, and normalized output contract. Exact tested head `6b5e32b1144e9f3517247110ea4383b287ce33f4`; merged to main at `f922631e0393063bde02b1e0bd93d30b2d38bd2a`. All four required CI workflows passed on the exact head. No publication, deployment, or production runtime verification is claimed.
