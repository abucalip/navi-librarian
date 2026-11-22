# FirstFM — Removing Last.fm API Dependencies

**Status:** Proposed plan (2026-11-22). Ready to execute in ordered slices before Last.fm's December API paywall.  
**Owner decisions recorded (2026-11-22):**
1. **Radio scrobbling & love:** migrate to **ListenBrainz** (reusing `LISTENBRAINZ_TOKEN`).
2. **Deezer fallback:** add **Deezer** as a fallback for MBID-less or ListenBrainz-empty artists (similar artists, top songs), paced and cached.
3. **Field renames & `navidrome_server.py` shrinkage:** rename `lastfm_*` payload fields to provider-neutral names (`listeners`, `playcount`, `popularity_bonus`, etc.) in a coordinated server + client pass, and detach Last.fm callers from `navidrome_server.py` into new modules (per D-016, `navidrome_server.py` must only shrink).

---

## 1. Goal and Scope

Remove every runtime dependency on `ws.audioscrobbler.com` across **Librarian** (server + worker) and **Discair** (web, Android, macOS) without regressing recommendation quality, artist/album page richness, or radio scrobbling.

Non-goals:
- Do not introduce new paid APIs or require new user accounts.
- Do not break existing SQLite caches on upgrade (old `lastfm:*` / `discovery:lastfm:*` rows simply expire unused; no destructive migration required).
- Do not add code to `navidrome_server.py`.

---

## 2. Replacement Services Matrix

| Capability | Current Last.fm Method | Primary Replacement | Fallback | Batch Support & Pacing |
|---|---|---|---|---|
| **Album popularity** (recommendations, lenses, classics, deep dives, new releases) | `album.getInfo`, `artist.getTopAlbums` | **ListenBrainz** `POST /1/popularity/release-group` (already in `integrations/listenbrainz/popularity.py`) | None needed (missing release groups simply get no popularity bonus) | **Batched** (50 release-group MBIDs per POST, 30-day cache + 1-hour negative mark). |
| **Artist popularity & top albums** (classics, deep dives, lens pool, artist page) | `artist.getInfo`, `artist.getTopAlbums` | **ListenBrainz** `POST /1/popularity/artist` + `GET /1/popularity/top-release-groups-for-artist/{mbid}` | **MusicBrainz** release groups (already used on artist page) | `popularity/artist` is **batched** (50 artist MBIDs per POST); `top-release-groups` is per-artist, cached 30 days. |
| **Similar artists** (artist page, deep dives, lens links) | `artist.getSimilar` | **ListenBrainz** `lb-radio/artist` + MusicBrainz tags + Discogs styles (already fused in `discovery/search/similar.py`) | **Deezer** `GET /artist/{id}/related` (resolved via `/search/artist`) | **No Deezer batch endpoint.** Deezer REST API (`api.deezer.com`) allows ~50 req / 5 s per IP. Pace and cache 30 days + 1-hour no-match mark. |
| **Artist top songs** (artist page) | `artist.getTopTracks` | **ListenBrainz** `GET /1/popularity/top-recordings-for-artist/{mbid}` (already primary in `discovery/search/top_songs.py`) | **Deezer** `GET /artist/{id}/top` | **No Deezer batch endpoint.** Single-artist GET (up to 50 tracks), paced and cached 30 days. |
| **Artist genre / tag fallback** (lens pool) | `artist.getTopTags` | **MusicBrainz** genres (via ListenBrainz artist metadata batch) | **Discogs** artist/release styles filtered through the MusicBrainz genre vocabulary | Existing Discogs pacing & 90-day cache. |
| **Artist bio, album tracklists, search** | `artist.getInfo`, `album.getInfo`, `album.search` | **Wikipedia**, **Apple Music**, **Deezer**, **MusicBrainz**, **Discogs** (all already wired) | — | Already covered by `album_page_sources.py` and `discovery/search/providers.py`. |
| **Listening history** (Lenses) | `user.getrecenttracks` | **ListenBrainz** listens (already primary in `discovery/history_fetch.py`) | Navidrome play counts / stars (already used elsewhere) | Already paginated & cached. |
| **Radio scrobbling & love** | `track.scrobble`, `track.love` | **ListenBrainz** `POST /1/submit-listens` (`listen_type: "single"`) and `POST /1/feedback/recording-feedback` (`score: 1`) | Local radio store love if recording MBID cannot be resolved | Single-event background POSTs, reusing `LISTENBRAINZ_TOKEN`. |

### Note on Deezer Batching
Deezer's public REST API (`https://api.deezer.com`) **does not provide a multi-artist batch endpoint** for `/artist/{id}/related` or `/artist/{id}/top`. Because Deezer is used **only as a fallback** (when ListenBrainz returns no data or the artist has no MBID), request volume is low. All Deezer artist calls will live in a single new module (`integrations/deezer/artist.py`) with:
- A shared pacing guard staying well under Deezer's 50 req / 5 s ceiling (e.g., 0.15 s spacing).
- 30-day positive caching and 1-hour negative marks (`album-no-match`-style) for artist search misses.
- Integration with `app/services/runtime_metrics.py` (already tracks `api.deezer.com` as `deezer`) and `owned_prefetch.py` (`deezer` budget cap).

---

## 3. Detaching Callers from `navidrome_server.py` (D-016)

Removing Last.fm is a direct opportunity to shrink `navidrome_server.py`. Every Last.fm symbol currently in `navidrome_server.py` will be removed or moved to a dedicated module with direct-import tests:

- **Remove completely:**
  - `from integrations.lastfm import client as _lastfm_client_module`
  - `_lastfm_client` instantiation and `LASTFM_LAST_ERROR`
  - `_lastfm_album_popularity`, `_lastfm_top_albums`, `_lastfm_artist_genres`
  - `"lastfm_api_key"` default in settings dict
  - `_lastfm_popularity_fn`, `_lastfm_available_override`, `prepare_lastfm_callback`, `lastfm_api_configured`, `lastfm_albums_checked`, `lastfm_last_error`
- **Detach into new/existing modules:**
  - Move the Classics / Deep Dives / New Releases provider-lookup wiring (`top_albums_lookup`, `similar_artists_lookup`, `artist_genres`) out of `navidrome_server.py` into a small `discovery/provider_wiring.py` (or directly into `discovery/popularity.py` + `integrations/listenbrainz/popularity.py`), so `navidrome_server.py` only passes the clean dependency bundle or delegates outright.
  - Update `docs/ARCHITECTURE.md` in the same PR whenever a new module is added.

---

## 4. API Contract & Field Renames

To keep the wire format clean and provider-agnostic, rename Last.fm-specific fields across server responses, contract fixtures, and clients:

| Old Field | New Field | Where Used |
|---|---|---|
| `lastfm_listeners` | `listeners` | `discovery/recommendation_payload.py`, `discovery/deep_dive_candidates.py`, `discovery/new_releases.py`, `discovery/lens_week.py`, `discovery/pick_why.py`, `navidrome_server.py`, web, Android (`Discovery.kt`, `Dto.kt`), macOS, contract fixtures |
| `lastfm_playcount` | `playcount` | Same as above |
| `lastfm_tags` | `popularity_tags` (or drop if unused) | `discovery/recommendation_payload.py`, `discovery/recommendations.py` |
| `lastfm_popularity_bonus` | `popularity_bonus` | `discovery/recommendation_payload.py`, `navidrome_server.py` |
| `lastfm_api_configured` / `lastfm_albums_checked` / `lastfm_last_error` | `popularity_provider_configured` / `popularity_albums_checked` / `popularity_last_error` (in diagnostics) | `navidrome_server.py`, `recommendation/diagnostics.py`, `recommendation/replay.py` |
| `lastfm_api_key` / `lastfm_username` (settings) | Removed | `settings/service.py`, `app/api/settings.py`, `.env.example`, `compose.yaml`, web, Android, macOS |
| Radio scrobbling settings (`LASTFM_API_KEY`, `LASTFM_SHARED_SECRET`, `LASTFM_SESSION_KEY`) | `LISTENBRAINZ_TOKEN` (existing) | `integrations/radio/scrobble.py`, `app/api/radio.py`, web, Android (`RadioSettings.kt`), macOS (`CupertinoRadioSettings.swift`, `RadioSettingsModel.swift`) |

**Compatibility rule:** If the owner deploys server and clients on different schedules, we can either (a) ship the server emitting the new fields alongside the client PRs in the same release train, or (b) have clients decode `listeners ?? lastfm_listeners` during the transition PR and drop the old keys on the server in Phase 5. The plan below uses **(b)** so no client ever breaks against an older or newer server during rollout.

---

## 5. Phased Execution Plan

Each phase is one or two small, reviewable PRs with focused unit/regression tests.

### Phase 1 — ListenBrainz Popularity Expansion & `navidrome_server.py` Detachment (Server)
- **1a. ListenBrainz popularity client:** Extend `integrations/listenbrainz/popularity.py` with:
  - `fetch_artist_popularity(post, cache_get, cache_set, mbids)` (`POST /1/popularity/artist`, batched 50/chunk, 30-day cache + 1-hour negative mark).
  - `fetch_artist_top_release_groups(get, cache_get, cache_set, artist_mbid)` (`GET /1/popularity/top-release-groups-for-artist/{mbid}`, 30-day cache).
- **1b. Replace `discovery/mbid_popularity.py` & candidate pipelines:**
  - Switch `discovery/mbid_popularity.py`, `discovery/lens_pool_gatherer.py`, `discovery/classics_candidates.py`, `discovery/classics_ratings.py`, `discovery/deep_dive_candidates.py`, `discovery/new_releases.py`, and `discovery/recommendations.py` from Last.fm to ListenBrainz popularity.
  - Detach the Last.fm popularity & lookup wrappers from `navidrome_server.py` into `discovery/popularity.py` (shrinking `navidrome_server.py`).
  - Update `recommendation/replay.py`, `recommendation/diagnostics.py`, and `recommendation/profile_comparison.py`.
  - Emit new field names (`listeners`, `playcount`, `popularity_bonus`) alongside temporary compatibility aliases until Phase 5, or switch directly once clients are updated in Phase 4.

### Phase 2 — Deezer Fallback, Search, Artist/Album Pages & Tag Fallback (Server)
- **2a. Deezer artist fallback client:** Add `integrations/deezer/artist.py` with paced, cached:
  - `search_artist_id(name)`
  - `related_artists(artist_id, limit)` (`/artist/{id}/related`)
  - `top_tracks(artist_id, limit)` (`/artist/{id}/top`)
  - Register in `docs/ARCHITECTURE.md`.
- **2b. Wire into artist/album pages & search:**
  - Remove `LastFmProvider` from `discovery/search/providers.py`, `discovery/search/network.py`, `discovery/search/artist_page.py`, `discovery/search/artist_sections.py`, `discovery/search/album_page.py`, `app/api/search.py`, and `app/services/similar_precompute.py`.
  - Update `discovery/search/similar.py` to fuse ListenBrainz + Deezer fallback + MusicBrainz tags + Discogs styles (with clear reason strings, e.g., `"Deezer similar artist"`).
  - Update `discovery/search/top_songs.py` to use ListenBrainz first, Deezer fallback second.
  - Update `discovery/artist_links.py` to use ListenBrainz / Deezer instead of `artist.getSimilar`.
  - Replace `artist.getTopTags` in `discovery/artist_tag_fallback.py` with Discogs styles filtered through the MusicBrainz genre vocabulary.
  - Remove `lastfm` from `app/services/owned_prefetch.py` and `app/services/prefetch_state.py`.

### Phase 3 — Listening History & Radio Scrobbling to ListenBrainz (Server)
- **3a. Listening history:** Remove `lastfm_window` and `LastFmResponseError` from `discovery/history_fetch.py` and `discovery/lens_service.py`.
- **3b. Radio scrobbling & love:** Rewrite `integrations/radio/scrobble.py` (and `app/api/radio.py`) to submit to ListenBrainz:
  - `POST https://api.listenbrainz.org/1/submit-listens` (`listen_type: "single"`) using `Authorization: Token <LISTENBRAINZ_TOKEN>` and the logged track's artist, title, and timestamp.
  - `POST https://api.listenbrainz.org/1/feedback/recording-feedback` (`score: 1`) for radio love when a recording MBID is available (or resolve via MusicBrainz/ListenBrainz lookup; always keep local radio love state).
  - Gate `scrobble_enabled` on `LISTENBRAINZ_TOKEN` being configured instead of `LASTFM_*`.
  - Update radio API response copy/status fields so clients display ListenBrainz instead of Last.fm.

### Phase 4 — Client Updates (Web, Android, macOS)
- **4a. Web (`static/app.js`, `static/layout-zine.js`, `app/templates/index.html`):**
  - Read `listeners` / `playcount` (with fallback to `lastfm_listeners` / `lastfm_playcount` if needed).
  - Remove Last.fm API key / username inputs and status badges from Settings; update Radio scrobbling copy to ListenBrainz.
- **4b. Android (`android/`):**
  - Update `model/Discovery.kt`, `model/Dto.kt`, `model/Server.kt`, `model/Radio.kt`, `data/ServerRead.kt`, `data/Repository.kt`, `ui/settings/ServerModel.kt`, `ui/settings/RadioSettings.kt`.
  - Update `android/contract-fixtures/librarian/*.json` and `docs/contracts/ANDROID_CLIENT_CONTRACT.md`.
- **4c. macOS (`macos/`):**
  - Update `DiscairLibrarian` (`ServiceSettings.swift`, `RadioClient.swift`, `Radio.swift`), `DiscairNavidrome` (`AlbumSpread.swift`), and `DiscairUI` (`ServicesModel.swift`, `ServicesController.swift`, `AppState+Services.swift`, `ServiceDraftProbe.swift`, `RadioSettingsModel.swift`, `CupertinoServices.swift`, `CupertinoRadioSettings.swift`, `CupertinoHome.swift`, `CupertinoAlbumSpread.swift`, `GraphExplorer.swift`, `ListeningHistory.swift`).
  - Update `docs/contracts/MACOS_CLIENT_CONTRACT.md`.

### Phase 5 — Final Last.fm Removal & Cleanup (Server + Docs)
- Delete `integrations/lastfm/` (`__init__.py`, `client.py`).
- Remove `lastfm_api_key` / `lastfm_username` / `lastfm` probe from `settings/service.py` and `app/api/settings.py`.
- Remove `audioscrobbler.com` from `app/services/runtime_metrics.py`, `.env.example`, and `compose.yaml`.
- Drop temporary `lastfm_*` payload aliases from server responses (leaving only `listeners`, `playcount`, `popularity_bonus`).
- Update `docs/ARCHITECTURE.md`, `docs/contracts/SERVER_V2_CONTRACT.md`, `PRODUCT.md`, and `docs/ACTIVE_WORK.md`.

---

## 6. Verification Strategy

- **Unit & regression tests:** Each PR adds/updates focused tests (`pytest <changed_tests>`, `swift test --disable-sandbox --filter <ChangedSuites>`, `./gradlew testDebugUnitTest --tests '<filter>'`) covering:
  - ListenBrainz batched artist/release-group popularity (hits, misses, negative marks, network errors).
  - Deezer fallback pacing, caching, and no-match handling.
  - ListenBrainz radio scrobble & love payload formatting, auth header, and missing-token refusal.
  - Client JSON decoding of renamed fields and updated Settings/Radio UI.
- **Linting:** Run `python scripts/check_lint_changed.py --base origin/main` on every Python PR.
- **Boundary check:** Confirm zero remaining references to `ws.audioscrobbler.com` or `integrations.lastfm` across the repository at Phase 5 closeout.
