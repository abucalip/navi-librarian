# Architecture

Last reviewed: 2026-11-14. This is a map of current module ownership, not a roadmap. GitHub `main` is authoritative.

## Server

| Module | Owns |
|---|---|
| `app/main.py`, `app/api/` | FastAPI assembly and HTTP adapters: request validation, authentication dependencies, response/status mapping and route registration. Keep business rules out of route handlers. |
| `app/security/` | Web-session authentication, login middleware, cookies and security boundaries. |
| `app/services/` | Application-lifetime services and background-worker coordination. `app/worker.py` starts worker-owned jobs; `library_enrich.py` and `insights_refresh.py` coordinate their respective loops. |
| `discovery/` | Discovery policy and read models: candidate gathering, list construction/refresh, lenses, feedback, taste-derived discovery inputs, and `discovery/search/`'s owned-library index, query/ranking, paging and search events. |
| `recommendation/` | Recommendation-engine policy: candidate evaluation, scoring/diversity allocation, result shaping, and deterministic capture/replay and comparison tools. |
| `acquisition/` | Acquisition lifecycle and safety: request coordination, source selection/switching, tracking, recovery, completion, cleanup and verified import transactions. |
| `intelligence/` | Server V2 knowledge and enrichment domain: dedicated store/schema, jobs, MusicBrainz imports and enrichment, artwork index, taste/listening analysis, insights, graph/path building and API response builders. |
| `integrations/` | External-system boundaries and protocol clients (Navidrome, slskd, ListenBrainz, Last.fm, MusicBrainz, Discogs and radio). Own provider I/O, parsing and provider-specific transport behavior—not discovery policy. |
| `settings/` | Configuration defaults, validation, settings persistence and generation/version helpers. |
| `navidrome_server.py` | Legacy compatibility and orchestration boundary still used by existing server callers. Do not add code; new behavior belongs in the appropriate package and this module may only shrink. |
| `static/`, `app/templates/` | Browser UI assets and HTML templates. The browser presents server-owned results; it must not duplicate recommendation, discovery, acquisition or import rules. |

## Clients

- `android/`: native Android client. Owns its UI, local playback/queue, device-side state and API integration; streams owned music directly from Navidrome.
- `macos/`: native macOS client, split into audio, API/library, model and UI packages. Owns desktop presentation and local playback behavior.
- Both clients consume server contracts; neither is a second implementation of server recommendation or acquisition policy.

## Runtime and data boundaries

- The web process serves requests. The separate worker process owns scheduled/background enrichment and insight refresh work.
- SQLite application settings/authentication data and the dedicated Server V2 intelligence store persist under the configured data directory, outside the container image.
- Provider clients are called through `integrations/`; domain packages decide what to request and how returned data affects the product.
- Acquisition/import/cleanup are safety-critical: canonicalize paths under configured roots, reject traversal, symlink escapes and ambiguous targets, and never overwrite or remove unrelated files.

## Dependency rules

1. HTTP adapters call services/domain modules; they do not contain domain policy.
2. Domain modules use explicit provider and persistence dependencies rather than hidden app initialization.
3. Keep provider I/O in `integrations/`, recommendation policy in `recommendation/`, discovery policy in `discovery/`, and knowledge/enrichment state in `intelligence/`.
4. Preserve established API shapes, persistence semantics and client compatibility when changing ownership.
5. Do not resume size-only modularization. See `docs/DECISIONS.md` for binding decisions, `docs/TEST_PLAN.md` for verification, and `PROJECT_LOG.md` for implementation history.
