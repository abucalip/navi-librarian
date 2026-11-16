# Architecture

Last reviewed: 2026-11-15. This is a map of current module ownership, not a roadmap. GitHub `main` is authoritative.

## Server

| Module | Owns |
|---|---|
| `app/main.py`, `app/api/` | FastAPI assembly and HTTP adapters: request validation, authentication dependencies, response/status mapping and route registration. Keep business rules out of route handlers. |
| `app/security/` | Web-session authentication, login middleware, cookies and security boundaries. |
| `app/services/` | Application-lifetime services and background-worker coordination. `app/worker.py` starts worker-owned jobs; `library_enrich.py` and `insights_refresh.py` coordinate their respective loops. |
| `discovery/` | Discovery policy and read models: candidate gathering, list construction/refresh, lenses, feedback (including `genre_block.py`, the blocked-genre rows and the selection-time and read-time exclusion, `artist_lean.py`, the More like this / Less like this rows whose boost, penalty and seed policy live in `recommendation_feedback.py`, and `artist_block.py`, which only lists and lifts the existing "Not this artist" rows, and `discovery_mode.py`, the Safer / Balanced / Deeper knobs that `selection_policy.py` and `lenses.py` read, and `star_seeds.py`, Navidrome stars as a decayed seed weight with its cached read; the switch lives in `settings/service.py`), taste-derived discovery inputs, and `discovery/search/`'s owned-library index, query/ranking, paging and search events. |
| `scripts/discovery_mode_sweep.py` | Offline, no-network sweep of the discovery-mode knobs over frozen private inputs (a pickled lens-build input and a personal-list capture); prints aggregates only. Imports `discovery/` and `recommendation/replay.py`; nothing imports it. |
| `recommendation/` | Recommendation-engine policy: candidate evaluation, scoring/diversity allocation, result shaping, and deterministic capture/replay and comparison tools. |
| `acquisition/` | Acquisition lifecycle and safety: request coordination, source selection/switching, tracking, recovery, completion, cleanup and verified import transactions. |
| `intelligence/` | Server V2 knowledge and enrichment domain: dedicated store/schema, jobs, MusicBrainz imports and enrichment, artwork index, taste/listening analysis, insights, graph/path building and API response builders. |
| `integrations/` | External-system boundaries and protocol clients (Navidrome, slskd, ListenBrainz, Last.fm, MusicBrainz, Discogs and radio). Own provider I/O, parsing and provider-specific transport behavior—not discovery policy. |
| `settings/` | Configuration defaults, validation, settings persistence and generation/version helpers. |
| `navidrome_server.py` | Legacy compatibility and orchestration boundary still used by existing server callers. Do not add code; new behavior belongs in the appropriate package and this module may only shrink. |
| `static/`, `app/templates/` | Browser UI assets and HTML templates. The browser presents server-owned results; it must not duplicate recommendation, discovery, acquisition or import rules. |

## Clients

- `android/`: native Android client. Owns its UI, local playback/queue, device-side state and API integration; streams owned music directly from Navidrome.
  - Android layouts (`ui/theme/Palette.kt` `Layout`): each non-standard theme owns its own `<Theme>*.kt` files and is reached through one `is<Theme>()` branch in a shared control. **Gallery** (`Layout.Gallery`, eight palettes, spec `docs/GALLERY_THEME.md`, package `docs/design/gallery/`): `ui/common/GalleryKit.kt` (rules, type styles, prints, buttons, source switch, tabs, rows, state words, switch, tracker, banner), `ui/common/GalleryIcons.kt`, `ui/common/GalleryShell.kt` (dock bar with sliding marker, mini player, top bars, snackbar host and toast, sheet handle, the page-arrival clock `GalleryArrival`/`galleryArrive`, the dock's slide and `GalleryFlight`, which carries the mini cover's place so Now Playing can fly the cover between the dock and its print), `ui/theme/GalleryMotion.kt` (pure: section 8 motion values pinned to `tokens.json`, the staggered rise), fonts `res/font/fraunces_gallery*.ttf` and `manrope_gallery.ttf`. Screens follow as `Gallery<Screen>.kt` beside each screen: G2 Home is `ui/home/GalleryHome.kt` (arrangement with its own wordmark bar, so the shell draws no top bar on any Gallery page; the hero is a slideshow pager; reached from `HomeScreen`) and `GalleryHomeRules.kt` (pure: pager label, last-heard words, Radio plates and rows, library line); G3 Album, Artist and Genre are `ui/album/GalleryAlbum.kt`, `ui/artist/GalleryArtist.kt` and `ui/GalleryGenre.kt` (each reached from its screen by one `isGallery()` branch), with the pieces they share in `ui/common/GalleryPages.kt` (menu button, note, playing bars, captioned print, artist plate, read more) and the words in `ui/common/GalleryPagesRules.kt` (pure: catalogue lines, tabs, note); G4 Discover, Library and Search are `ui/discover/GalleryDiscover.kt` (head with Flow's one list switch and its list sheet, a two-column grid of tiles that carry the reason for each pick, Insights cards without lens headings, taste card and ranked bars), `ui/library/GalleryLibrary.kt` and `ui/search/GallerySearch.kt` (each reached from its screen by one `isGallery()` branch; the taste sheet and Insights page branch inside `TasteCard.kt` and `InsightsPage.kt`), with the words in `ui/common/GalleryListsRules.kt` (pure: date line, entry and taste lines, sort line, search detail); G5 Now Playing, Queue, Lyrics and Radio are `ui/player/GalleryNowPlaying.kt` (the full-screen page frame that rises and falls, the three views of one page sharing the seek line and transport, `GalleryPlayerRules` pure) and `ui/radio/GalleryRadio.kt` (stations, live radio, Heard; `GalleryRadioRules` pure), reached by one `isGallery()` branch each in `NowPlayingSheet`, `RadioScreen`, `HeardScreen` and `RadioNowPlayingSheet`; G6 Downloads, Stats, Server, Settings, Appearance, Equalizer and Crossfade are `ui/downloads/GalleryDownloads.kt` (`GalleryDownloadsRules` pure), `ui/stats/GalleryStats.kt`, `ui/settings/GallerySettings.kt` (Settings, Server, Appearance and the shared row, switch and head blocks; `GallerySettingsRules` pure) and `ui/player/GalleryEqCrossfade.kt`, reached by one `isGallery()` branch each; the pick and song menus and the confirmation sheet branch in `GalleryPages.kt` and `ConfirmSheet.kt`. No other theme's file changes behaviour.
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
