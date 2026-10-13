# Architecture

Last updated: 2026-10-13

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

## Main components

- **`app/main.py`** — FastAPI routes and the web UI. It adapts existing librarian functions for browser/API use.
- **`navidrome_server.py`** — discovery orchestration, Navidrome/slskd integration, acquisition lifecycle, settings, persistence, and legacy MCP tools.
- **`acquisition_completion.py`** — strict completed-track matching, filename identity, and completed-folder inspection.
- **`slskd_search.py` / `slskd_quality.py`** — importable slskd query/candidate helpers and audio-quality classification.
- **`discovery_recommendations.py`** — pure discovery eligibility, normalization, scoring, and diversity helpers with direct-import tests.
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
