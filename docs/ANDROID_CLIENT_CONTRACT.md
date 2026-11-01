# Android client contract (Discair)

Status: **proposal, pending owner approval of the PR. Nothing here is implemented.** Owner decisions on the former open items 2, 3 and 6 are recorded in section 9. Written against local `main` (clean, matching `origin/main` at last fetch). Phase 0 is drafted on this branch: payload fixtures, a contract test and `android/DESIGN.md` (section 7).

## 1. Purpose and scope

A native Android app for the owner, named **Discair**, on Android 13. It displays library metadata from Navidrome and recommendation data from Librarian, and it can launch acquisitions and show their progress. It is a thin client: **Librarian is the only component that calculates or recommends** similar artists, albums, discovery lists and ranking. The app renders what it receives, in the order received.

In scope (v1):
- Dashboard, Library, Artist page, Album page, global search.
- Discovery lists: Recommendations, New releases, Personal discoveries, Daily picks (lens lists), Classics, Artist deep dives.
- Launching acquisitions (album and single song) and viewing live progress, retry and dismiss.
- Discovery feedback (save, dismiss, dismiss artist, remove from For me).
- Settings: server addresses, sign-in, sign-out.

Out of scope for v1:
- Playback in the first release. It is now specified in [`ANDROID_PLAYER_CONTRACT.md`](ANDROID_PLAYER_CONTRACT.md) (D-018) and is built in its own phases.
- Radio, Librarian service settings (Navidrome, slskd, Last.fm, ListenBrainz, Discogs), household or multi-user use.
- Any on-device ranking, matching or similarity logic.
- Tailscale itself. The Tailscale app must be connected on the phone.

## 2. Binding rules (inherited from the repo)

1. **Existing API is authoritative.** No endpoint or field is invented. A need the API cannot meet is written up as a contract proposal, not worked around.
2. **Server-enforced safety.** Get, Dismiss and import are enforced by the server. The app never reports success before the server confirms, and never duplicates acquisition logic.
3. **Dismiss deletes files** (ACQ-04). The app asks for explicit confirmation before sending it.
4. **Honest states:** pending, confirmed, failed and recoverable are visibly different, never by colour alone.
5. **Accessibility floor:** WCAG 2.1 AA, 48dp touch targets (Material minimum, which exceeds the web's 44), TalkBack labels, reduced-motion respected.
6. **No third-party runtime assets.** Fonts and icons are bundled in the app. No analytics or crash-reporting SDKs.
7. D-016 (`navidrome_server.py` takes no additions) applies to any backend change that this contract later proposes.
8. In all documentation, comments and communications, refer to the person directing the project as "the owner".
9. **Every design choice goes through `/mobile-design`.** Any decision about layout, navigation, interaction, touch targets, typography, colour, copy, states or accessibility is run past the `/mobile-design` skill before it is built, and re-reviewed with it once built. The outcome is recorded in `android/DESIGN.md`. A design change made without that pass is not accepted, and a phase is not complete until its screens have had the review.
10. **The UI is a port of the mobile web UI.** Before a screen is designed or reviewed, the phone layout in `static/app.css` (the max-width 620px and 760px sections), the matching code in `static/app.js`, the requirement in `docs/REQUIREMENTS.md` and the reference screenshots named in section 6 are read, and the screen is compared with the running mobile web page. Controls that exist only on the desktop layout (such as the slider arrows and count) are not carried over. Every deliberate difference (for example a larger touch target) is written down in `android/DESIGN.md` with its reason.

## 3. Platform

- Android 13 (API 33) minimum and target. No compatibility shims for older versions.
- Kotlin, Jetpack Compose, Material 3 with a custom theme.
- OkHttp and Retrofit with kotlinx.serialization; Coil for images; Room for caching; Hilt for dependency injection; Navigation-Compose.
- Credentials in the Android Keystore through EncryptedSharedPreferences.
- Project lives in `android/` in this repository. Fixtures live in `android/contract-fixtures/` next to the server code.

## 4. Servers and transport

- Two user-entered base URLs, both `https://<name>.ts.net`, served by `tailscale serve`: Librarian and Navidrome.
- Cleartext HTTP is disabled in the network security config. Certificates are validated by the system trust store. No pinning and no "trust all" override.
- When a server is unreachable the app distinguishes "no network", "server unreachable (is Tailscale connected?)", "unauthorised" and "server error", with a retry action.
- Timeouts: connect 10 s, read 30 s; the progress stream has no read timeout while the screen is visible.

### 4.1 Librarian authentication
- `GET /api/auth/status`, then `POST /api/auth/login` with `{username, password}`. The session cookie (strict, HTTP-only, Secure) is kept in a persistent cookie jar that is stored encrypted.
- Any `401` triggers re-login with the stored credentials once; if that fails the app shows the sign-in screen. `429` shows the retry-later message from the server and does not retry automatically.
- First-time account setup (`/api/auth/setup`) is not part of the app. The owner creates the account in the web UI.
- **Open question:** behind `tailscale serve` every request may share one client IP, which would share the login rate limit with the web UI (section 9).

### 4.2 Navidrome authentication
- Subsonic API with token and salt per request, using the owner's Navidrome credentials stored in the Keystore. The password is never sent or logged.
- **Differs from the web app,** where Navidrome credentials stay server-side. Accepted because the owner chose direct access and the Tailscale network is the boundary. If playback is added later, the same credentials serve streaming.

## 5. Data sources: who supplies what

### 5.1 Navidrome, directly (library metadata)
`getArtists`, `getArtist`, `getAlbum`, `getAlbumList2`, `getGenres`, `search3`, `getCoverArt`, `ping`. Used for library browsing, owned-state and cover art of owned albums. The app uses these only for what Navidrome owns.

### 5.2 Librarian (recommendations, detail, acquisition)

| Need | Endpoint |
|---|---|
| Dashboard picks | `GET /api/dashboard-picks?count=` |
| Dashboard shelves, genres | `GET /api/dashboard/albums/{shelf}`, `GET /api/dashboard/genres` |
| Recommendations | `GET /api/recommendations?count=` (1–30) |
| Discovery lists | `GET /api/discovery/{personal\|for_me\|classics\|artist_deep_dive\|new_releases\|<lens>}?count=` (1–150) |
| List refresh | `POST /api/discovery/{list}/refresh` (`count` JSON integer 1–20) |
| Feedback | `POST /api/discovery/feedback` `{artist, album, action, metadata}`; actions `save`, `dismiss`, `dismiss_artist`, `remove_for_me` |
| Lens feedback summary | `GET /api/discovery/lens-feedback` |
| Search | `GET /api/search` (SSE stream, `docs/SEARCH_CONTRACT.md` 3.1, 3.7, 3.8) |
| Artist page | `GET /api/artists/{key}` (`docs/SEARCH_CONTRACT.md` 3.3) |
| Album page | `GET /api/albums/{artist_key}/{album_key}` |
| Genre page | `GET /api/genres/{tag}` |
| Bio, details, links, year | `GET /api/artist-bio`, `/api/album-details`, `/api/album-description`, `/api/album-links`, `/api/album-year` |
| Images | `GET /api/artwork`, `GET /api/artist-image`, owned cover art under `owned_artwork` |
| Library browse | `GET /api/library/artists`, `GET /api/library/albums` (used only if Navidrome direct cannot supply the same fields) |
| Health | `GET /api/health` |

### 5.3 Acquisition (launch and progress)

| Action | Endpoint |
|---|---|
| Launch album | `POST /api/acquire` `{artist, album, metadata, auto_queue}` (`auto_queue` is a JSON boolean) |
| Launch one song | `POST /api/acquire/track` `{artist, album, title, track_number?, year?, metadata?}` |
| Queue a reviewed candidate | `POST /api/acquire/queue` — **not used in v1** (owner decision: automatic only) |
| Status snapshot | `GET /api/acquisitions` |
| Live progress | `GET /api/acquisitions/stream` (SSE, one JSON snapshot per second, `event: error` on a failed read) |
| Switch source | `POST /api/acquisitions/skip` `{artist, album}` |
| Dismiss | `POST /api/acquisitions/dismiss` `{artist, album}` (deletes the associated files) |

Behaviour:
- The progress screen uses the SSE stream while visible and falls back to polling `GET /api/acquisitions` every few seconds if the stream drops. The stream is closed when the screen is not visible, to save battery.
- No notifications, foreground service or background progress in v1 (owner decision). An in-app badge shows the active count, as the web nav does.
- Errors from the server (`400`, `404`, `409`, `502`) show the server's `detail` text. `409` on Dismiss means refusal and is shown as such.
- A Get button shows pending until the server's response arrives and then reflects the returned state. It never shows success optimistically.

## 6. Design and UX

1. **The `/mobile-design` skill is used for every UI decision (binding rule 9).** Before the first screen is built, it is invoked to settle navigation pattern, touch targets, thumb-zone placement, list performance and Android conventions. It is invoked again for each new screen type (list rows, artist and album pages, progress screen, search). Decisions it produces are recorded in `android/DESIGN.md`.
2. Design is a port of the mobile web UI, not a WebView. Visual identity comes from `static/app.css` and `docs/archive/redesign/DESIGN*.md`: the warm dark ink palette, chart-red emphasis, yellow for primary and selected states, artwork-led layouts. Reference screenshots: `album page.jpg`, `artist page.jpg`, `genre tiles.png` (owner's folder, outside the repo).
3. Icons are converted from `static/icons.svg` to vector drawables. Fonts are the self-hosted ones from `static/fonts`.
4. Navigation: bottom bar, icon-only with labels for TalkBack, with a More overflow for the less-used lists, as in the web mobile nav (PRs #546 and #547).
5. Shared "ranked album row": artwork, title, artist, artist bio in the middle with click-to-expand, fixed row height, equal-width ranked rows (web PRs #533, #554).
6. Dark theme only in v1, matching the web UI.

## 7. Phase 0: payload fixtures (gate before any UI work)

**Status: drafted, pending owner review of the shapes.** Fixtures: `android/contract-fixtures/` (see its README for what was and was not captured). Test: `tests/test_android_contract_fixtures.py` (6 tests, run and passing locally; CI not yet run). Design: `android/DESIGN.md`. Findings so far:
- Search, the acquisition stream and every list endpoint behaved as section 5 describes; search ends with a `done` event.
- Album launch and song launch both returned HTTP 200 with `ok: false` and `status: "settings_required"` when slskd is not configured, so the app must read `ok` and `status`, not the HTTP code.
- `POST /api/acquisitions/skip` for an unknown acquisition returned 409.
- Not captured: refresh routes and any acquisition with real items (slskd disabled). The progress item shape remains to be recorded.
- The `tailscale serve` client-IP question (section 9) cannot be answered locally and is still open.

Steps:

1. Run the local test helper (`docs/LOCAL_UI_TESTING.md`, sandbox music paths, slskd disabled) and record one real response from every endpoint in section 5, including an acquisition status snapshot and a captured SSE sample.
2. Store them in `android/contract-fixtures/` with the request that produced them.
3. DTOs are generated from the fixtures, not from guesses. Unknown fields are ignored and missing optional fields tolerated.
4. A contract test in the repository fails if a route's response shape no longer matches its fixture.
5. Resolve the rate-limit question and the Navidrome-versus-Librarian field gaps (section 9).

## 8. Phases and acceptance

**Phase 1 status: built and unit-tested, not verified against your servers.** `android/` holds the Gradle project (package `app.discair`, min and target SDK 33, compile SDK 36). Done: themed shell with the bundled fonts, setup screen, HTTPS-only address validation, Librarian sign-in with a persistent encrypted cookie jar and one re-login on 401, Navidrome Subsonic ping, failure kinds shown as icon plus words (no network, unreachable with Tailscale hint, unauthorised, rate limited, certificate, server), encrypted credential storage, automatic re-check on start, sign-out. A `/mobile-design` review fixed seven items (decisions in `android/DESIGN.md`): off-main-thread storage, confirmed sign-out, an Unavailable screen with retry, Cancel and back, IME actions with autofill and show-password, a non-dead Connect button, and heading semantics. Run so far: `./gradlew testDebugUnitTest assembleDebug lintDebug` (31 unit tests, build and lint succeeded); debug APK started on an Android 36 emulator, the setup screen rendered (also at 200% font scale, and with Required markers on an empty form), and entering unresolvable addresses produced the "Server unreachable. Is Tailscale connected?" state. **Not run:** a successful sign-in against real servers over Tailscale, restart persistence on a device, a rejected-certificate case, and TalkBack. Deviation from section 3: Hilt, Retrofit, Room, Coil and Navigation-Compose are not added yet (manual wiring of one view model); they arrive with the phase that first needs them.


| Phase | Deliverable | Acceptance |
|---|---|---|
| 0 | Fixtures, contract tests, `android/DESIGN.md` from `/mobile-design` | Fixtures committed; owner reviews shapes |
| 1 | Skeleton, theme, server setup, Librarian login, Navidrome connection test | Signs in over Tailscale, survives restart, clear unreachable state |
| 2 | Dashboard, Library, Artist and Album pages | Matches the web pages for the same data |
| 3 | Discovery lists, feedback, search, shared row | Every list shows Librarian's order with no client-side ranking |
| 4 | Acquisitions: launch album and song, live progress, retry, skip, dismiss with confirmation | Progress matches the web UI; no success shown before server confirmation |
| 5 | Caching, offline and error states, session expiry, accessibility pass, signed release build | Works with the network dropped; TalkBack pass; installed on the owner's phone away from home |

Testing: unit tests for repositories and DTO parsing against fixtures; Compose screenshot tests; a manual run over the real Tailscale setup. No claim of live behaviour is made until the owner has tested it. Merge, release and deployment remain separate states, as elsewhere in the project.

**Phase 2 status: built and checked on an emulator, not verified on your phone or against your real servers.** Dashboard (Recommended, Genres, Newly added, Recently played, Most played), Library (artists and albums, server-side search, sort and paging), Artist, Album and Genre pages, bottom navigation and Settings. Decisions are in `android/DESIGN.md`. The first build of the Recommended strip used desktop-only controls (arrows and a count); it was corrected to the web phone strip (swipeable cards with a dot per card), and the genre tiles and similar-artist rows were aligned with the web phone CSS. The Home, Library, Artist and Album pages were then compared side by side with the running mobile web UI and the reference screenshots and aligned (cover-tinted backgrounds, display-face headings with the red rule, the overlaid Back button, the Top songs panel, ranked rows, service links); the remaining differences are listed in `android/DESIGN.md`. This alignment pass was **not** run through `/mobile-design` (rule 9), by the owner's decision on 2026-10-31; the open points are the 32dp recommendation dots, 12sp genre tiles, text contrast over tinted backdrops, the icon-only sort direction button and TalkBack order. Run so far: `./gradlew testDebugUnitTest assembleDebug lintDebug` (45 unit tests, including decoding every recorded page payload and the library paging logic) and a manual run of the debug build on an Android 36 emulator against a local Librarian over HTTPS with your real Navidrome library (a test certificate, removed afterwards). Differences from the plan:
- Section 5.1 had the app read library metadata from Navidrome directly. The pages use Librarian's routes instead, because only they return the artist and album keys the pages need and the cover route. Navidrome direct is not used in Phase 2.
- Not built: grid mode and tile size for the library, the New releases shelf (Phase 3), service links on the album page, Get buttons (Phase 4).
- Not verified: your phone over Tailscale, TalkBack, 200% font scale on these pages, landscape, and the "matches the web pages" acceptance against the web UI side by side.

**Phase 3 status: built, unit-tested, and run on an Android 36 emulator against a local Librarian over HTTPS with your real Navidrome library (a test CA and a fresh Librarian data directory, all removed afterwards); not verified on your phone or over Tailscale.** New: a Discover tab (chips for Personal discoveries, Daily picks, New releases, Add to your collection, Artist deep dives, Saved), a Search tab (`GET /api/search` read as a stream, results grouped as the server sends them, "Not in your library" last), the shared ranked row (lead numeral or release date, 72dp artwork, title, artist, meta lines, artist bio that expands on tap, Save, and a "Not for me" menu), and a New releases shelf on Home. Lists are drawn in the order received; the app does not sort, filter, cap per artist or shuffle (the web page does cap Classics and shuffle on rotate; the app does not, per rule 1 of section 1). Save shows pending, saved and failed by icon and spoken state and changes to Saved only after the server answers `ok`. Dismiss hides the row, offers Undo for 6 s (web: 4.2 s, longer for TalkBack), then sends `dismiss` or `dismiss_artist`; a failure restores the row and says why. Feedback sends the row exactly as the server gave it as `metadata`. Run so far: `./gradlew testDebugUnitTest assembleDebug lintDebug` (51 unit tests, including list parsing against the recorded lists, the feedback body against the recorded request and every recorded search event). Differences from the plan:
- No Get button on rows (Phase 4). Lens rows show no per-lens `rank` and no lens-feedback summary screen.
- Refresh is a "Build this list" button on an empty list, calling `POST /api/discovery/{list}/refresh` with `count: 20`; there is no pull-to-refresh yet. The refresh and lens-list payloads were never captured (section 7), so those two DTO paths are untested against real data.
- Search has no recent-searches list and no type filter. Song results open their album page and need `artist` and `album` in the result; if the server omits them the row is not tappable.
- A `/mobile-design` review of the Phase 3 code (not of the screens running on a device) fixed four items: a dismissal still inside its Undo window was lost when leaving the Discover tab (it is now sent on leaving), the release-date column was too narrow for "26 Mar", the list spinner had no spoken label, and the keyboard stayed open after Search. The skill's audit script does not read Kotlin, so it checked nothing. **Emulator run:** Personal discoveries showed real rows with covers and bios; Save posted to `/api/discovery/feedback` and the heart filled only after the 200; "Not this album" showed Undo and sent nothing until the 6 s window closed, then posted once; both items then disappeared from the list on reload, so the server round trip works; Search streamed owned results first and then "Not in your library"; Daily picks showed the server's "no saved list" message per lens (this test instance had none). Fixed from that run: a gap under the header, the reason text in the mono face, a duplicate empty message on Daily picks, and the keyboard covering search results. At 200% font scale rows held, but the four bottom-bar labels split mid-word, so that bar alone is capped at 130% text. **Not run:** Undo tapped, "Never suggest", Saved and New releases lists with data, TalkBack, landscape, a phone, and the Navidrome check (the test Navidrome address answered `ping` itself, since the in-app Navidrome check is not under test). Screens have not had the `/mobile-design` review on a physical device, so rule 9 is only partly met.

**Phase 4 status: built and unit-tested; not run on an emulator or a phone, and not verified against a live slskd.** New: the cloud Get button (idle, pending, requested, failed, each a different icon and spoken state; requested only after the server accepts; a requested or pending Get is never sent twice) on ranked rows, the Recommended card, the album page (album and each missing song) and the artist page (missing albums and Top songs that name an album); a Downloads page opened from the header, whose cloud icon carries the active count; rows with cover, title, artist, "Song on ...", quality profile, status icon and words, progress bar with percent, speed, size and tracks remaining, Try again (the four web statuses), Use next source (15 s countdown after a stall), and Dismiss behind a confirmation dialog; "Dismiss all successful imports" behind the same dialog. The page reads the SSE stream while visible, falls back to polling every 5 s if it drops, and stops when the screen is left or the app is stopped; the badge is refreshed every 30 s otherwise. A server refusal (for example 409 on Dismiss) is shown in the server's words. Run so far: `./gradlew testDebugUnitTest assembleDebug lintDebug` (81 unit tests; 30 are new: record parsing against `acquisitions` and `acquisitions_stream`, launch replies against `acquire_album` and `acquire_track`, request bodies against the recorded requests, and the hub's states against a fake server). Differences from the plan and the web:
- The Downloads page is a header icon, not a fifth tab (four labelled tabs already needed a text-size cap). Technical lines (source folder, destination, downloads path, transfer states, completion evidence) are not shown; the message, error, peer and update time are.
- The web remembers dismissed imports in the browser; the app does not, because the server removes the record on Dismiss.
- Get on the Recommended card and the pages sends only artist, album, year and release-group id as `metadata`; list rows send the row as the server gave it. The real progress item shape (`live_progress`) was never captured (slskd disabled), so progress parsing follows the web code, not a recording.
- Not verified: a real download, skip, retry or dismiss against slskd; the stream over Tailscale; TalkBack; landscape; 200% text on the Downloads page.

**Phase 5 status: built and run on the owner's phone (2026-10-31); the acceptance is partly met (works with the network dropped: yes; TalkBack pass and use away from home: not yet).** Built and unit-tested (97 tests, all pass): a disk cache of the last good answer of each read-only Librarian route (dashboard, library, artist, album, genre, discovery lists, image lookups; 20 MB, oldest removed first, cleared on sign-out, keyed by full address). It answers only when the phone cannot reach the server (no connection, timeout, unreachable); a server error, a refusal or a bad certificate is never hidden behind a saved copy, and acquisition status, search, launches and feedback are never cached. A banner says "Can't reach Librarian. Showing a copy saved ..." while saved copies are shown. At start with no connection but saved copies, the app opens on them instead of the Unavailable screen. Session expiry: a 401 still triggers one re-login; if Librarian rejects the stored credentials the app returns to setup with the saved values and says why (no repeated login attempts, to protect the shared lockout). Release: `assembleRelease` builds minified and shrunk (R8 failed on Tink's annotations until a rule was added) but unsigned; signing reads `android/keystore.properties` (steps in `android/README.md`). Accessibility, from code review only: every clickable now carries a button role. Not done or not verified:
- Owner's phone run of the signed, minified build over Tailscale (2026-10-31, owner's report; no crash): sign-in to Librarian and Navidrome, Library navigation, search, Home, a Get launched from the app that finished and was imported, and the Downloads page showing progress. In airplane mode the banner "Can't reach Librarian" showed, and a cold start opened on saved pages. First attempt failed with "Unable to parse TLS packet header" until the addresses pointed at `tailscale serve` HTTPS endpoints; the app was not at fault.
- Not run (the UI polish and `/mobile-design` device review are deferred by the owner to a later pass): session expiry on a device (a rejected stored login), skip, retry and dismiss on real jobs, TalkBack, landscape, 200% text, use away from home on mobile data, low-end device.
- Room was not added (section 3); a file cache was enough. Offline writes are not supported: Get, Save and Dismiss need the server, and say so when it cannot be reached.
- Not done: TalkBack, landscape, 200% text on Downloads and the banner, reduced-motion (only tap-triggered pager scrolls and Material indicators animate), pull-to-refresh, a cache for Navidrome-direct calls (unused), per-list "saved at" times beyond the banner.

## 9. Decisions and open items

Decided by the owner:
1. **Album launch is automatic only.** The app sends `POST /api/acquire` with `auto_queue: true`; there is no candidate review and `POST /api/acquire/queue` is not used.
2. **No background notifications** in v1.
3. **Navidrome credentials on the device** are accepted (section 4.2).
4. **This contract goes through a PR**, not directly to `main`.

Still open:
1. **Login rate limit:** confirm whether `tailscale serve` hides the client IP from Librarian. If it does, the shared 15-minute lockout could block the app. Any change would be a backend contract proposal.
2. **Playback — decided by the owner on 2026-11-01:** the app streams directly from Navidrome with the credentials already on the device; the proxy routes in `docs/PLAYER_PROPOSAL.md` are not used. Contract: [`ANDROID_PLAYER_CONTRACT.md`](ANDROID_PLAYER_CONTRACT.md). It adds a media foreground service for playback only; acquisition still has no notifications or background work.
