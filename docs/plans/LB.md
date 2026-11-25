# ListenBrainz discovery and playlists

**Status:** Implementation plan (revised with live probe) · 2026-11-24 · `LB-01` and `LB-02` merged (`#1270`, `#1271`)

Discair will automatically bring ListenBrainz mixes (`Created for Me` and collaborative-filtering recommendations) and Discair-generated local mixes into Navidrome as private, managed rolling playlists. In Discair, each mix shows its full track list, owned/missing state, and a per-track Download action for unowned tracks; Android and macOS play the owned subset in order through their native queues, while Web manages browsing, downloads, and Navidrome sync (Web has no audio player). The same server-side recording matcher will support owned-first Artist Radio, an LB Radio discovery mix, Fresh Releases (personal + upcoming), ListenBrainz feedback/essentials features, and an optional cover-color browser.

## Owner decisions (approved 2026-11-24)

- **D1 · Navidrome playlist retention:** Maintain one rolling private Navidrome playlist per recurring feed (for example `Discair · Daily Jams`, `Discair · Weekly Exploration`) updated in place to the latest edition, while keeping recent dated snapshots in Discair's Inbox.
- **D2 · Owner deletes a managed Navidrome playlist:** Treat manual deletion in Navidrome as opt-out (mark unlinked in Discair, keep the Inbox snapshot, and do not silently recreate unless the owner re-enables sync).
- **D3 · Artist Radio unowned tracks and coverage:** Return the full matched track list (owned + unowned) and base playback design on live library coverage (see probe finding below: raw LB Radio matched only 0–5% of the library, so playable Artist Radio must be owned-first, with LB Radio positioned as a discovery mix).
- **D4 · Global Fresh Releases feed:** Omit the 1,879-entry global `/1/explore/fresh-releases` feed from initial scope; ship only the personal ListenBrainz feed (`past` + `future`) alongside existing MusicBrainz library-artist New Releases.

## Live probe evidence (2026-11-24)

### Navidrome (`0.64.2`, OpenSubsonic `true`)

| Check | Result |
| --- | --- |
| Song inventory (`search3`) | 13,205 songs total; **11,439 (86.6%) already carry `musicBrainzId`** directly in `search3`. 13,204 have `duration`, 13,205 have `album`. `isrc`, `bpm`, `moods`, and `artists` are also present. |
| Empty playlist creation | `createPlaylist(name=...)` with 0 songs succeeded (`status: ok`, returned playlist ID). Discair can create managed playlists immediately even when 0 tracks are owned. |
| Privacy (`public=false`) | `updatePlaylist(playlistId=..., public="false")` succeeded (`status: ok`; Navidrome omits `public` / returns `null` for private playlists). |
| Atomic replace, order & repeats | `createPlaylist(playlistId=..., songId=[s0, s1, s0])` atomically replaced the playlist in exact order and preserved duplicate `songId` entries (3 entries). A follow-up `createPlaylist(playlistId=..., songId=[s1, s0])` shrank and reordered atomically (2 entries). Disposable playlist deleted cleanly afterwards. |

### ListenBrainz (authenticated against the owner's configured account)

| Endpoint | Result |
| --- | --- |
| Token validation (`/1/validate-token`) | HTTP 200, valid. |
| Created for Me (`/1/user/{u}/playlists/createdfor`) | HTTP 200, `playlist_count: 0` (account follows `troi-bot`; Daily Jams not yet generated). Keep sanitized fixture until the first edition arrives. |
| **CF Recording Recs** (`/1/cf/recommendation/user/{u}/recording`) | HTTP 200, 25 tracks actively updated; **12/25 (48%) owned by exact MBID** and 13/25 unowned discovery tracks. Works immediately even while `Created for Me` is empty. |
| Fresh Releases personal (`days=30&past=true&future=true`) | HTTP 200, 38 entries (**34 past/today, 4 upcoming**): 16 albums, 18 singles, 4 EPs. 38/38 have `release_group_mbid`; 36/38 have `caa_id`. |
| **LB Radio real-library coverage** (`/1/explore/lb-radio`) | Portishead MBID: `easy` **1/50** (2%), `medium` **1/47** (2%), `hard` **2/39** (5%). `tag:(jazz)`: `easy` **0/50** (0%), `medium` **1/50** (2%). All tracks included `album`. **Conclusion:** LB Radio is a discovery/download mix, NOT a playable owned-library radio queue on its own. |
| Top recordings for artist (`/1/popularity/top-recordings-for-artist/{mbid}`) | HTTP 200, **319 ranked recordings** for Portishead in a single call. Viable for owned-first Artist Radio and "Missing Essentials". |
| MBID Mapper (`/1/metadata/lookup/`) | HTTP 200, returns `recording_mbid`, `release_mbid`, `release_name`, `artist_mbids` in one call without touching MusicBrainz's 1.1 s gate. |
| Cover color (`/1/explore/color/3b82f6`) | HTTP 200, 12 releases with `release_mbid`, `caa_id`, `color`, `dist`, `artist_name`, `release_name`, `recordings`. |
| User feedback (`/1/feedback/user/{u}/get-feedback`) | HTTP 200, 10 loved recordings (`score: 1`). |
| Similar users & Feed (`/similar-users`, `/feed/events`) | HTTP 200: 25 similar users; feed returns `follow` and `recording_pin` events. |
| Stats (`/stats/user/{u}/artist-map`, `daily-activity`) | HTTP 200: **47 countries** in artist map; full hour-of-day listening distribution available. (`release-groups` `this_year` returned 204; `pins` returned 404; `year-in-music/2025` returned empty keys.) |

## Codebase constraints verified against `main`

- **Web has no audio player or playback queue.** Android and macOS stream owned music directly from Navidrome (`docs/ARCHITECTURE.md`). Web manages browsing, per-track downloads, and saving/inspecting Navidrome playlists.
- **Reuse `discovery/search/index.py` for the song index.** `OwnedData.songs` already pages and caches the full Navidrome song inventory (up to 200,000 songs, atomic swap, sanity-drop guard). Extend `_song_entry` to retain `recording_mbid` from Subsonic `musicBrainzId` (verified present on 86.6% of songs in `search3`). Subsonic `duration` is in seconds; JSPF `duration_ms` is in milliseconds.
- **Single-track acquisition requires an album name.** `acquisition/track_service.py::request_track` rejects empty `album`. When a track omits `album`, resolve it via ListenBrainz `/1/metadata/lookup/` first, falling back to MusicBrainz through `integrations/provider_gate.py` (mirroring `app/api/radio.py::radio_get_play`), or refuse safely.
- **Navidrome indexing is asynchronous after import.** `acquisition/import_hooks.py::notify_imported` runs before Navidrome finishes indexing. Reconcile managed playlists when Navidrome's `getScanStatus` marker advances and on scheduled worker passes.
- **Architecture and store boundaries.** `navidrome_server.py` takes no additions (D-016). New playlist snapshots and managed-copy mappings live in new tables in `intelligence.sqlite3` (migrated via `intelligence/store/migrations.py`, covered by `scripts/backup_stores.py`, `open_readonly`/`open_writer`). Scheduled refreshes run on `worker-schedule-discovery` (`app/services/discovery_schedule.py`).
- **Keep the 6-package server dependency footprint.** Do not add the third-party `troi` Python package to `requirements.txt`; build Discair-generated local mixes directly in Python over local data.
- **Graceful degradation when ListenBrainz is unconfigured.** Every ListenBrainz-backed feature must return a clean, non-error unconfigured state when no username or token is set.
- **Multi-theme clients.** Web targets Listening Room (`L0`–`L10`), and Android spans multiple themes; client slices must update `docs/contracts/` when adding fields or routes.

## 1. Shared track matching and acquisition

- `LB-01` (`integrations/listenbrainz/jspf.py`) is merged. Extend it in `LB-04` to also parse JSPF playlist/track extensions (`last_modified_at`, `source_patch`, `creator`, `artist_identifiers`, `release_identifier`, `caa_id`).
- Extend `discovery/search/index.py::_song_entry` to retain normalized `recording_mbid` (from `musicBrainzId`), and build the pure track matcher over `OwnedData.songs` (worker builds `OwnedData` synchronously like `app/services/similar_precompute.py`).
- Match `recording_mbid` first (covers ~86.6% of the library directly). LB-03 requires a unique normalized artist credit and full title, corroborated by release title or a duration difference of at most 2 seconds (`duration_ms` vs `duration * 1000`). When both forms of evidence are available, both must agree. Conflicting IDs, conflicting metadata, insufficient corroboration, or competing versions yield `ambiguous`. Release identifiers are parsed in LB-04.
- Return source identity, zero-based track position, display metadata, match state (`owned`, `missing`, `ambiguous`), owned Navidrome `song_id` when owned, and acquisition state separately.
- Every unowned row exposes Download. The server resolves the track from its stored edition and position, rechecks ownership on click, and reuses any active acquisition. If `album` is missing, resolve via ListenBrainz `/1/metadata/lookup/` first, then MusicBrainz via `musicbrainz_lane()`; refuse safely with a clear explanation if identity remains ambiguous or no album can be resolved.
- Track acquisition is safety-critical: keep existing canonical-path, destination, and import checks untouched, and test both safe success and unsafe refusal.
- Reconcile affected playlists when Navidrome's `getScanStatus` marker advances after imports and on periodic worker checks, inserting newly indexed tracks in original source order.

## 2. Automatic Playlist Inbox

- The worker (`worker-schedule-discovery` in `app/services/discovery_schedule.py`) periodically reads:
  1. The configured profile's paginated **Created for Me** collection (`Daily Jams`, `Weekly Jams`, `Weekly Exploration`, etc.), fetching details only when `last_modified_at` / `date` changes.
  2. **ListenBrainz Collaborative-Filtering Recording Recommendations** (`/1/cf/recommendation/user/{u}/recording`), turned into a rolling Inbox mix (`Discair · ListenBrainz Picks`). Unlike `Created for Me` (which can be empty or stalled), this already returns a ~50/50 mix of owned tracks and downloadable discoveries today.
  3. **Discair-generated local mixes** (section 5).
- Store complete source snapshots and managed-copy mappings in `intelligence.sqlite3`. Key hosted playlists by upstream playlist MBID and rolling/local mixes by recipe + edition ID.
- Sync the owned subset to one rolling private Navidrome playlist per recurring feed (D1):
  - Persist a unique creation token and create an empty playlist with a temporary name containing the token. Link its ID, then set the final name, the management comment, and `public="false"` in one request. Verify privacy before populating the copy.
  - Update atomically in source order (preserving repeats) via `createPlaylist(playlistId=..., songId=...)`. On Navidrome `0.64.2`, use one `updatePlaylist` request with every existing track position to clear a nonempty copy.
  - Recover a lost create reply by looking up the exact temporary marker for the same owner. Keep the create pending if the outcome remains unknown. If the owner manually deletes a linked playlist, report it missing so LB-08 can record the unlink decision (D2).
- Keep previous successful snapshots during upstream failures. An empty `Created for Me` fetch explains that ListenBrainz has not generated playlists yet and links to `troi-bot` (while `ListenBrainz Picks` and local mixes still populate the Inbox).
- **Client surfaces:**
  - **Web (Listening Room):** Inbox shelf and track detail with source, generation date, owned/total count, Navidrome sync badge, ordered track rows, and per-track Download/retry (no browser audio player).
  - **Android & macOS:** Inbox shelf and track detail with ordered native playback of owned tracks, per-track Download/retry, and source metadata.

**Acceptance:** Sync a representative fixture twice and after a simulated interrupted write. Confirm a single private rolling Navidrome copy, preserved source order including repeats, and a missing track joining in order after import and Navidrome scan completion. Exercise unconfigured ListenBrainz, zero `Created for Me` playlists, zero owned tracks, timeouts, manual deletion (D2), and stale editions.

## 3. Artist Radio (owned-first) & LB Radio Discovery Mix

The live probe showed that raw ListenBrainz `/1/explore/lb-radio` matches only **0–5% of tracks** in the owner's 13,205-song library (`0–2` owned songs out of 50 across `easy`/`medium`/`hard` and `tag:(jazz)`). Treating LB Radio as an owned-only radio queue would leave the player nearly empty. Split the experience cleanly into two complementary tools, both kept distinct from Discair's live internet **Radio** player:

- **3a. Owned-first Artist Radio (playable queue):**
  - Seeded from an artist page (artist MBID). Combines the seed artist and Discair's precomputed similar artists (`similar_precompute`), ranks candidate recordings using ListenBrainz `/1/popularity/top-recordings-for-artist/{mbid}` (319 ranked tracks per call) and local play counts, and intersects with `OwnedData.songs` so the resulting 25–50 track queue is **100% playable** from the owner's library, with configurable familiarity (`Familiar`, `Explore`, `Deep cuts` controlling seed-vs-similar ratio and play-count weighting).
  - **Android & macOS:** Plays directly in the existing native queue; preserves the current queue on failure or zero matches.
  - **Web:** Previews the mix and offers **Save to Navidrome**.
- **3b. LB Radio Discovery Mix (discovery & download):**
  - Calls `/1/explore/lb-radio` with structured artist MBID or tag seeds and mode (`easy`/`medium`/`hard`), caches briefly, coalesces concurrent requests, and matches against `OwnedData.songs` returning the **full track list** (owned + unowned) (D3).
  - Positioned honestly as a **"Discover a mix"** surface where unowned tracks are the primary value: every unowned track has one-click Download, owned tracks can be played (Android/macOS) or saved to Navidrome (Web).

**Acceptance:** Verify owned-first Artist Radio produces a full playable queue with artist diversity and no wrong versions; verify LB Radio Discovery Mix returns full matched/unmatched rows, preserves existing native queues on error, and handles unconfigured tokens cleanly.

## 4. Fresh Releases

- Extend existing `New Releases` with **From your ListenBrainz listening** and **Coming soon**, alongside the current MusicBrainz library-artist results.
- Use ListenBrainz personal `/1/user/{user_name}/fresh_releases` (`days=30&past=true&future=true`) in one cached call (probed: 38 entries, 34 past + 4 upcoming, 100% `release_group_mbid`, 95% `caa_id`). Omit the 1,879-entry global feed (D4).
- Deduplicate by `release_group_mbid`, preserve date precision (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`), join ownership via `OwnedData.albums`, label `Owned`, `Out now`, or `Upcoming`, and offer `Album`, `EP`, and `Single` filters. Upcoming releases remain browsable with acquisition clearly unavailable until release.
- Retain the existing MusicBrainz library-artist view unchanged when ListenBrainz is unconfigured or unavailable.

**Acceptance:** Verify duplicate editions, partial dates, local day boundaries, type filters, unconfigured/unavailable fallback, and owned/unowned navigation across clients.

## 5. Discair-generated local mixes (no `troi` dependency)

- Implement local mixes as pure, deterministic Python generators in `discovery/` using local data Discair already owns (`OwnedData.songs`, Navidrome play counts/years, `intelligence/insights/` Forgotten Gems, and ListenBrainz listen history / feedback) with zero new dependencies.
- Start with **Rediscover your library**, blending older favorites with neglected owned tracks (100% playable, zero extra external API calls).
- Route generated output through the exact same Inbox snapshot and rolling private Navidrome sync pipeline, keyed by `recipe + scheduled edition` and labeled clearly as a Discair mix. Retain the prior edition on failure or empty output.

**Acceptance:** With fixed fixtures, verify deterministic eligibility, repeatable edition identity, clear Discair attribution, and retention of the prior playable edition on failure.

## 6. High-value ListenBrainz additions inspired by the live probe

These reuse the exact same matching, Inbox, and ListenBrainz client infrastructure with minimal new surface area:

- **6a. Missing Essentials on Artist Pages (`/1/popularity/top-recordings-for-artist/{mbid}`):** Intersect an artist's top ListenBrainz recordings (cached 30 days, reusing the same endpoint as section 3a) with `OwnedData.songs` to surface the top unowned tracks on artist pages with one-click Download.
- **6b. ListenBrainz Feedback Integration (`/1/feedback/user/{u}/get-feedback`):** Import ListenBrainz loves (`score=1`, 10 live on the owner's account) as an optional discovery seed alongside Navidrome stars (`discovery/star_seeds.py`) and optional rolling Navidrome playlist (`Discair · ListenBrainz Loved`), and honor hates (`score=-1`) as a negative exclusion in mixes and discovery.
- **6c. Browse by cover color (low-priority / optional):** Bounded, cached server read of `/1/explore/color/{color}` preserving similarity order, collapsing duplicate releases, and joining ownership via `OwnedData.albums` using `release_mbid` and normalized `(artist, album)` with no N+1 MusicBrainz calls. Accessible swatches on Web, Android, and macOS.

## Implementation slices

Each row is one PR. Start from current `main` once the listed dependencies have merged. Server slices use focused `pytest` runs and sanitized fixtures; client slices build against the merged server contract, update `docs/contracts/` when adding fields or routes, and test one client only.

### Playlist Inbox and shared recording matching

LB-06's shared route contract and fixtures are in [Playlist Inbox API](../contracts/PLAYLIST_INBOX_CONTRACT.md).

| Slice | Status | Depends on | PR scope and acceptance |
| --- | --- | --- | --- |
| LB-01 · Parse playlist tracks | **Merged (`#1270`)** | — | Added `integrations/listenbrainz/jspf.py` and sanitized fixture `tests/fixtures/listenbrainz_daily_jams.json`. |
| LB-02 · Match exact recording IDs | **Merged (`#1271`)** | LB-01 | Added `recording_mbid` to `discovery/search/index.py::_song_entry` and pure recording-MBID matching over `OwnedData.songs`. Tests cover ordered owned/missing results and duplicate occurrences. |
| LB-03 · Match untagged tracks | Ready | LB-02 | Accept a unique artist/title candidate with agreeing release title or duration evidence. Fixtures separate safe matches from ambiguous live, studio, and remastered versions. |
| LB-04 · Read Created for Me & CF Recs | Ready | LB-01 | Add paced `httpx` upstream adapter for paginated `Created for Me`, `/1/cf/recommendation/user/{u}/recording`, and JSPF extension parsing (`last_modified_at`, `source_patch`, `creator`, track MBIDs/CAA). Verify pagination, unconfigured account, empty account, and failed detail reads. |
| LB-05 · Store playlist editions | Ready after LB-04 | LB-04 | Add `intelligence.sqlite3` migration and repository for full source snapshots and managed-copy metadata (no `navidrome_server.py` additions). Verify idempotent retry, change detection, and retention of prior snapshots on partial refresh. |
| LB-06 · Read the Inbox | Ready after LB-03, LB-05 | LB-03, LB-05 | Add authenticated Inbox list and detail endpoints (read-only store access) with shared fixtures for owned, missing, ambiguous, unconfigured, empty, and stale results, preserving source order and acquisition state. |
| LB-07 · Save rolling private copies | Ready after LB-03, LB-05 | LB-03, LB-05 | Create and atomically replace rolling private Navidrome playlists (`createPlaylist` + `updatePlaylist(public="false")` + `createPlaylist(playlistId=...)`) per D1. Verify retry after uncertain create produces one copy, repeats survive, and unrelated playlists are never adopted. |
| LB-08 · Reconcile managed copies | Implemented, pending review | LB-07 | `PlaylistReconciler.run_once` checks the idle Navidrome scan marker and refreshes already-linked copies. Pass `worker_refresh=True` for a refresh even when the marker is unchanged. Confirmed missing copies are marked unlinked (D2). LB-10 registers the recurring job and runs the live check. |
| LB-09 · Download an Inbox track | Ready after LB-06 | LB-06 | Add server action for a stored edition + position, reusing `acquisition/track_service.py::request_track`. Resolve missing `album` via ListenBrainz `/1/metadata/lookup/` first, falling back to MusicBrainz via `musicbrainz_lane()`. Verify ownership recheck, safe refusal of unresolved/ambiguous tracks, and deduplication of concurrent clicks. |
| LB-10 · Schedule hosted import | Implemented, pending review | LB-08, LB-09 | Refresh `Created for Me` and `CF Recs` hourly on `worker-schedule-discovery`. Check for completed Navidrome scans every five minutes and recheck linked copies hourly even when the scan marker is unchanged. The owner verified the disposable live check before the schedule was wired. |
| LB-11 · Web Inbox browse | Implemented, pending review | LB-06 | Browse the Playlist Inbox under Discover in Listening Room. The shelf and edition details show source, generation date, owned count, and recorded Navidrome copy linkage. The ordered track list preserves repeats and distinguishes zero owned tracks from unavailable ownership. |
| LB-12 · Web Inbox downloads | Implemented, pending review | LB-09, LB-11 | Connect per-track Download, progress, and retry in Web Inbox. Verify unresolved rows explain why acquisition cannot start and completed tracks show as owned after refresh. |
| LB-13 · Android Inbox playback | Implemented, pending review | LB-06 | Discover shows a Playlist Inbox shelf and edition detail with source, generation date, and owned count. The native queue uses only owned tracks and preserves source order and repeated occurrences. Zero and unknown ownership leave the queue alone. |
| LB-14 · Android Inbox downloads | Implemented, pending review | LB-09, LB-13 | Wire per-track Download, status, and retry to existing Android acquisition UI. Verify unresolved and newly playable rows. |
| LB-15 · macOS Inbox playback | Implemented, pending review | LB-06 | Add Inbox shelf and track detail in macOS with source date, owned count, empty state, and ordered native playback of owned tracks. Check mixed and zero-owned fixtures. |
| LB-16 · macOS Inbox downloads | Ready after LB-09, LB-15 | LB-09, LB-15 | Wire per-track Download, status, and retry to existing macOS acquisition UI. Verify unresolved and newly playable rows. |

**LB-10 live check:** Use isolated Navidrome and slskd instances and a disposable music root. Seed an edition with an owned track repeated around a known missing test recording. Confirm the linked copy is private and initially shows the owned track twice. Request the missing track through LB-09 and confirm two simultaneous requests produce one download. After import, wait for an idle Navidrome scan with a new marker and run reconciliation once. Confirm the same private playlist ID now contains all three positions in order, and another download click reports the middle track as owned. The LB-09 fixture covers this sequence with simulated provider transports.

**Live result, 2026-11-25:** The owner confirmed one real Soulseek queue operation for two concurrent requests, a successful import and Navidrome scan, and reconciliation of all three positions into the original private playlist. The middle track was subsequently reported as owned.

### Owned-first Artist Radio & LB Radio Discovery Mix

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-17 · Owned-first Artist Radio API | LB-03 | Add authenticated server endpoint generating a playable 25–50 track library queue from seed artist + precomputed similar artists ranked by cached `/1/popularity/top-recordings-for-artist/{mbid}` and local play counts (`Familiar`/`Explore`/`Deep cuts`). Verify queue diversity, zero-match handling, and no unowned tracks leaking into the playable queue. |
| LB-18 · LB Radio Discovery Mix API | LB-03 | Add authenticated `/1/explore/lb-radio` endpoint for structured artist MBID and tag seeds + mode (`easy`/`medium`/`hard`), short caching, and request coalescing, returning full matched list (owned + unowned) for discovery and download (D3). Verify auth, throttle, and error handling. |
| LB-19 · Web Artist Radio & Discovery Mix | LB-17, LB-18 | Add Artist Radio (preview + Save to Navidrome) and Discovery Mix (preview + per-track Download + Save owned to Navidrome) on Web artist pages and Discover. No browser queue. |
| LB-20 · Android Artist Radio & Discovery Mix | LB-17, LB-18 | Add Start Artist Radio (queues owned tracks natively, preserves queue on error/empty) on artist pages and Discovery Mix (play owned / download unowned) in Discover. |
| LB-21 · macOS Artist Radio & Discovery Mix | LB-17, LB-18 | Add Start Artist Radio (queues owned tracks natively, preserves queue on error/empty) on artist pages and Discovery Mix (play owned / download unowned) in Discover. |

### Fresh Releases

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-22 · Fetch and compare personal releases | — | Add bounded, cached ListenBrainz personal `fresh_releases` read (`past=true&future=true`). Capture aggregate comparison of overlap, unique eligible entries, and date precision against the existing MusicBrainz `New Releases` list (no global feed per D4). |
| LB-23 · Serve personal and upcoming releases | LB-22 | Add Discover read model with `release_group_mbid` deduplication, date precision, `OwnedData.albums` ownership join, `Owned`/`Out now`/`Upcoming` labels, and album/EP/single filters. Verify local date boundaries and graceful fallback when ListenBrainz is unconfigured or unavailable. |
| LB-24 · Web Fresh Releases | LB-23 | Add personal and upcoming views to Web New Releases. Verify type filters, ownership, upcoming browse-only state, and album navigation. |
| LB-25 · Android Fresh Releases | LB-23 | Add personal and upcoming views and filters to Android Discover. Verify upcoming and owned entries open the right destination. |
| LB-26 · macOS Fresh Releases | LB-23 | Add personal and upcoming views and filters to macOS Discover. Verify upcoming and owned entries open the right destination. |

### Discair-generated local mixes

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-27 · Build Rediscover your library generator | LB-02 | Add a pure, deterministic local mix generator in `discovery/` using `OwnedData.songs`, `intelligence/insights/` Forgotten Gems, and ListenBrainz listen history (zero new dependencies). Compare coverage and variety against existing Discair selection; verify eligibility against fixed fixtures. |
| LB-28 · Save local mix editions to the Inbox | LB-08, LB-27 | Route the generator through the shared Inbox snapshot and rolling Navidrome copy services, keyed by `recipe + scheduled edition`. Verify retry, Discair attribution, and reuse of the same Navidrome copy. |
| LB-29 · Schedule the first local mix | LB-10, LB-28 | Register the local mix on `worker-schedule-discovery` with its own cadence. Verify failure or empty generation retains the prior playable edition and clients display Discair attribution. |

### ListenBrainz Feedback, Missing Essentials & Cover Color (optional / lower priority)

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-30 · Missing Essentials on artist pages | LB-02, LB-17 | Reuse cached `/1/popularity/top-recordings-for-artist/{mbid}` intersected with `OwnedData.songs` to expose top unowned recordings on the artist page API with Download eligibility. |
| LB-31 · ListenBrainz feedback sync | LB-02, LB-07 | Read `/1/feedback/user/{u}/get-feedback` (loves `score=1` and hates `score=-1`); exclude hated recordings from mixes/discovery and optionally expose loved tracks as a discovery seed or rolling Navidrome playlist (`Discair · ListenBrainz Loved`). |
| LB-32 · Serve cover-color results | — | Add bounded, cached server read of `/1/explore/color/{color}` by normalized hex color. Preserve similarity order, collapse duplicate releases, join ownership via `OwnedData.albums` without N+1 MusicBrainz calls, and test missing art and malformed input. |
| LB-33 · Web cover-color browser | LB-32 | Add accessible swatches and result cards in Web Discover. Verify keyboard selection and owned/unowned album navigation. |
| LB-34 · Android cover-color browser | LB-32 | Add swatches and results in Android Discover. Verify TalkBack labels, selection, and retry. |
| LB-35 · macOS cover-color browser | LB-32 | Add swatches and results in macOS Discover. Verify keyboard and VoiceOver selection, retry, and album navigation. |

## Phase 2 / Exploratory candidates (not scheduled)

Scope these only after Phase 1 is evaluated in daily use:

- **Taste Neighbors & Following Feed (`/1/user/{u}/similar-users`, `/1/user/{u}/feed/events`):** Surface pinned recordings and top discoveries from the owner's 25 closest ListenBrainz taste neighbors and followed accounts, matched against `OwnedData.songs` for one-click Download.
- **Stats & Atlas enrichment (`/1/stats/user/{u}/artist-map`, `daily-activity`):** Feed ListenBrainz's 47-country artist map into Stats/Atlas and use hour-of-day `daily-activity` profiles for time-aware local mixes (e.g., Morning vs. Late Night).
- **LB Radio expansion:** Weighted multi-seed prompts, saved discovery recipes, and Inbox playlist continuation.
- **Additional local mixes & Fresh Releases:** Artist deep cuts, World Trip, release watchlist, and Friday digest.

## Execution order

`LB-01` and `LB-02` are merged and `D1`–`D4` are approved. `LB-03` (untagged recordings), `LB-04` (`Created for Me` + `CF Recs` adapter), and `LB-22` (Fresh Releases) can proceed independently.

[ListenBrainz API](https://listenbrainz.readthedocs.io/en/latest/users/api/index.html) · [Playlists](https://listenbrainz.readthedocs.io/en/latest/users/api/playlist.html) · [Fresh Releases and cover color](https://listenbrainz.readthedocs.io/en/latest/users/api/misc.html) · [LB Radio prompts](https://troi.readthedocs.io/en/latest/lb_radio.html)
