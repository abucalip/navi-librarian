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

## 5. Bite-Sized Implementation Steps

Each step is scoped as a single, small PR so it can be implemented reliably by **Hydrogen (low)** or **Hydrogen (medium)** with focused tests.

### Phase 1 — ListenBrainz Popularity Expansion & `navidrome_server.py` Detachment

- **F1.1 — Add batched artist popularity & top release groups to ListenBrainz client**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** `integrations/listenbrainz/popularity.py`, `tests/test_listenbrainz_popularity.py`  
  - **Scope:** Add `fetch_artist_popularity(post, cache_get, cache_set, mbids)` (`POST /1/popularity/artist`, 50/chunk, 30-day cache + 1-hour negative mark) and `fetch_artist_top_release_groups(get, cache_get, cache_set, artist_mbid)` (`GET /1/popularity/top-release-groups-for-artist/{mbid}`, 30-day cache). Pure functions with injected HTTP/cache callables, matching the existing `fetch_release_group_popularity` pattern.

- **F1.2 — Switch `discovery/mbid_popularity.py` and `discovery/lens_pool_gatherer.py` to ListenBrainz**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** `discovery/mbid_popularity.py`, `discovery/lens_pool_gatherer.py`, `tests/test_mbid_popularity.py`, `tests/test_lens_pool_gatherer.py`  
  - **Scope:** Replace Last.fm `artist.getInfo` / `album.getInfo` calls with `fetch_artist_popularity` and `fetch_release_group_popularity`. Drop MusicBrainz release-search indirection that was only needed because Last.fm rejected release-group MBIDs.

- **F1.3 — Switch Classics, Deep Dives, and New Releases popularity & top albums to ListenBrainz**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** `discovery/classics_candidates.py`, `discovery/classics_ratings.py`, `discovery/deep_dive_candidates.py`, `discovery/new_releases.py`, `discovery/lens_week.py`, `discovery/pick_why.py`, plus their focused unit tests  
  - **Scope:** Read/emit `listeners` and `playcount` (keeping temporary `lastfm_listeners` / `lastfm_playcount` aliases in payloads until F5.2) and source top-album rankings from ListenBrainz popularity instead of Last.fm.

- **F1.4 — Detach Last.fm popularity & lookup wiring from `navidrome_server.py`**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** new `discovery/popularity.py`, `discovery/recommendations.py`, `discovery/recommendation_payload.py`, `recommendation/replay.py`, `recommendation/diagnostics.py`, `recommendation/profile_comparison.py`, `navidrome_server.py`, `docs/ARCHITECTURE.md`, plus focused tests  
  - **Scope:** Move the popularity bonus pass and Classics/Deep Dives/New Releases provider-lookup wiring out of `navidrome_server.py` into `discovery/popularity.py`. Remove `_lastfm_client`, `_lastfm_album_popularity`, `_lastfm_top_albums`, `_lastfm_artist_genres`, and `LASTFM_LAST_ERROR` from `navidrome_server.py` (net line reduction per D-016). Emit `listeners`, `playcount`, `popularity_bonus` (with temporary `lastfm_*` aliases until F5.2).

### Phase 2 — Deezer Fallback, Search, Artist/Album Pages & Tag Fallback

- **F2.1 — Add paced, cached Deezer artist fallback module**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** new `integrations/deezer/artist.py`, `docs/ARCHITECTURE.md`, new `tests/test_deezer_artist.py`  
  - **Scope:** Implement `search_artist_id(name)`, `related_artists(artist_id, limit)`, and `top_tracks(artist_id, limit)` against `https://api.deezer.com` with 0.15 s spacing, 30-day positive cache, and 1-hour no-match negative marks.

- **F2.2 — Replace Last.fm in `top_songs.py` and `similar.py` with Deezer fallback**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** `discovery/search/top_songs.py`, `discovery/search/similar.py`, `discovery/search/providers.py`, `discovery/search/network.py`, plus focused search tests  
  - **Scope:** Wire `integrations/deezer/artist.py` into `discovery/search/providers.py` / `network.py` as the fallback after ListenBrainz for `top_songs` and `similar` (reason `"Deezer similar artist"`). Remove `LastFmProvider` from `providers.py` and `network.py`.

- **F2.3 — Remove Last.fm from artist/album pages, `artist_links.py`, precompute, and prefetch**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** `discovery/search/artist_page.py`, `discovery/search/artist_sections.py`, `discovery/search/album_page.py`, `discovery/artist_links.py`, `app/api/search.py`, `app/services/similar_precompute.py`, `app/services/owned_prefetch.py`, `app/services/prefetch_state.py`, plus focused tests  
  - **Scope:** Drop all remaining `lastfm` arguments, cache keys, and prefetch budgets from artist/album page builders and `artist_links.py` (using ListenBrainz + Deezer fallback).

- **F2.4 — Replace `artist.getTopTags` in `discovery/artist_tag_fallback.py` with Discogs**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** `discovery/artist_tag_fallback.py`, `tests/test_artist_tag_fallback.py`  
  - **Scope:** Replace Last.fm top-tag lookups with Discogs artist/release styles filtered through the existing MusicBrainz genre vocabulary, keeping the same bounded best-effort contract and 90-day cache.

### Phase 3 — Listening History & Radio Scrobbling to ListenBrainz

- **F3.1 — Remove Last.fm listening history window**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** `discovery/history_fetch.py`, `discovery/lens_service.py`, `tests/test_history_fetch.py`, `tests/test_lens_service.py`  
  - **Scope:** Remove `lastfm_window`, `LastFmResponseError`, and `_lastfm_username` wiring so Lenses read history exclusively from ListenBrainz.

- **F3.2 — Migrate radio scrobbling and love to ListenBrainz**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** `integrations/radio/scrobble.py`, `app/api/radio.py`, `tests/test_radio_scrobble.py`, `tests/test_radio_api.py`  
  - **Scope:** Replace Last.fm `track.scrobble` / `track.love` with ListenBrainz `POST /1/submit-listens` (`listen_type: "single"`) and `POST /1/feedback/recording-feedback` (`score: 1`), authenticated with `LISTENBRAINZ_TOKEN`. Gate `scrobble_enabled` on `LISTENBRAINZ_TOKEN` and update user-facing error/status copy to mention ListenBrainz.

### Phase 4 — Client Updates (Web, Android, macOS)

- **F4.1 — Update Web client for renamed fields and ListenBrainz radio scrobbling**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** `static/app.js`, `static/layout-zine.js`, `app/templates/index.html`, plus focused UI contract tests  
  - **Scope:** Read `listeners` / `playcount` (with fallback to `lastfm_listeners` / `lastfm_playcount`), remove Last.fm API key / username inputs from Settings, and update Radio scrobbling copy to ListenBrainz.

- **F4.2 — Update Android client models, settings, radio UI, and contract fixtures**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** `android/app/src/main/kotlin/app/discair/model/{Discovery,Dto,Server,Radio}.kt`, `data/{ServerRead,Repository}.kt`, `ui/settings/{ServerModel,RadioSettings}.kt`, `android/contract-fixtures/librarian/*.json`, `docs/contracts/ANDROID_CLIENT_CONTRACT.md`, plus `RadioTest.kt` and `ServerModelTest.kt`  
  - **Scope:** Decode `listeners` / `playcount` (with fallback), remove Last.fm server settings fields, update Radio scrobbling copy to ListenBrainz, and refresh contract fixtures.

- **F4.3 — Update macOS client models, settings, probes, and radio UI**  
  - **Model / effort:** `Hydrogen (medium)`  
  - **Files:** `macos/Sources/DiscairLibrarian/{ServiceSettings,RadioClient,Radio}.swift`, `DiscairNavidrome/AlbumSpread.swift`, `DiscairUI/Model/{ServicesModel,ServicesController,AppState+Services,ServiceDraftProbe,RadioSettingsModel,AlbumSpread,GraphExplorer,ListeningHistory}.swift`, `DiscairUI/Themes/Cupertino/{CupertinoServices,CupertinoRadioSettings,CupertinoHome,CupertinoAlbumSpread}.swift`, `docs/contracts/MACOS_CLIENT_CONTRACT.md`, plus focused macOS unit tests  
  - **Scope:** Decode `listeners` / `playcount`, remove Last.fm service settings and `ws.audioscrobbler.com` draft probe, and update Radio scrobbling copy to ListenBrainz.

### Phase 5 — Final Last.fm Removal & Cleanup

- **F5.1 — Delete `integrations/lastfm/`, settings, probes, and metrics host**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** delete `integrations/lastfm/__init__.py` and `integrations/lastfm/client.py`, update `settings/service.py`, `app/api/settings.py`, `app/services/runtime_metrics.py`, `.env.example`, `compose.yaml`, `navidrome_server.py` (drop `"lastfm_api_key"` default), plus focused tests  
  - **Scope:** Remove the Last.fm client package, settings keys, health probe, and `audioscrobbler.com` metrics entry.

- **F5.2 — Drop temporary `lastfm_*` payload aliases and close out docs**  
  - **Model / effort:** `Hydrogen (low)`  
  - **Files:** `discovery/recommendation_payload.py`, `discovery/deep_dive_candidates.py`, `discovery/new_releases.py`, `discovery/lens_week.py`, `docs/ARCHITECTURE.md`, `docs/contracts/SERVER_V2_CONTRACT.md`, `PRODUCT.md`, `docs/ACTIVE_WORK.md`  
  - **Scope:** Remove temporary `lastfm_listeners` / `lastfm_playcount` / `lastfm_popularity_bonus` aliases once clients are updated, verify zero `ws.audioscrobbler.com` or `integrations.lastfm` references remain, and update documentation.

---

## 6. Verification Strategy

- **Unit & regression tests:** Each PR adds/updates focused tests (`pytest <changed_tests>`, `swift test --disable-sandbox --filter <ChangedSuites>`, `./gradlew testDebugUnitTest --tests '<filter>'`) covering:
  - ListenBrainz batched artist/release-group popularity (hits, misses, negative marks, network errors).
  - Deezer fallback pacing, caching, and no-match handling.
  - ListenBrainz radio scrobble & love payload formatting, auth header, and missing-token refusal.
  - Client JSON decoding of renamed fields and updated Settings/Radio UI.
- **Linting:** Run `python scripts/check_lint_changed.py --base origin/main` on every Python PR.
- **Boundary check:** Confirm zero remaining references to `ws.audioscrobbler.com` or `integrations.lastfm` across the repository at Phase 5 closeout.
