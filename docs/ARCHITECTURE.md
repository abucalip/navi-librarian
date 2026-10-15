## 2026-10-15 — Acquisition cleanup directory identity guard

- Dismissal cleanup is a destructive boundary. A successful read-only preflight does not authorize later path-based unlink if the album directory can be replaced in between.
- Re-open the configured root and target directory chain with no-follow flags, compare device/inode identities, revalidate the exact planned file set, and unlink relative to the pinned directory descriptor. Fail closed on changed paths, file identities, unexpected entries, or symlinks. Never recursively delete a directory.

---

## 2026-10-15 — PR #98 merged: acquisition request coordinator

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`; all four required workflows passed on that head.
- The coordinator keeps the legacy MCP/web adapter and persistence ownership in `navidrome_server.py` while moving request decisions behind injected dependencies.

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
