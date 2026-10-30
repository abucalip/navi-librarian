# Player proposal: persistent Navidrome player

Status: **proposal, pending owner approval; section 7 holds proposed default answers.** Nothing here is approved or implemented. Written against `main` at `a7ffb88`.

## 0. Gate: approval and policy conflicts

`PRODUCT.md` says Librarian is "not a player" and that a now-playing or streaming bar is out of scope "unless separately approved with an API contract". The owner has chosen *not yet* approved, so this document is that API contract proposal. If approved, the follow-up (docs-only, direct to `main`) is:

1. Amend `PRODUCT.md` (Positioning, Capabilities and Constraints).
2. Add `D-018` to `DECISIONS.md`: playback is in scope; audio is proxied; queue is client-side.
3. Add `PLAYER-01..` rows to `REQUIREMENTS.md` and a Player section to `TEST_PLAN.md`.

Also binding on the design:

- **D-016:** `navidrome_server.py` takes no additions. All new backend code goes in new modules.
- **Safety:** the browser never sees Navidrome credentials. Stream and scrobble routes sit behind the existing login gate.
- **Fonts/icons self-hosted.** Player icons come from the existing `static/icons.svg` (add symbols there); no third-party runtime assets.
- **Accessibility floor:** WCAG 2.1 AA, 44x44 targets, visible focus, keyboard operable, `prefers-reduced-motion`, status never by color alone.

## 1. Decisions taken (from the owner's answers)

| Topic | Decision |
|---|---|
| Audio path | Proxy through the app; Navidrome credentials stay server-side |
| Tile form | Full-width bottom bar, inset and rounded like a tile; pages get bottom padding |
| Entry points | Album modal / Library, artist page, song search results, Navidrome radio stations |
| Queue | Client-side, persisted in `localStorage`, restored paused on reload |
| Scrobbling | Yes: now-playing ping at start, scrobble at 50% or 4 min |
| Format | Original file by default; optional max-bitrate setting |
| v1 extras | Media Session + media keys; shuffle/repeat/seek/volume; queue panel (reorder, remove, play next, add to queue) |
| Deferred | Gapless/crossfade, EQ, lyrics (later phase, own contract) |
| Radio | Play the relayed stream; the Heard log (RADIO-01) works as today |
| Mobile | Mini-bar that expands to a full-screen sheet |

## 2. Architecture

### 2.1 Why this works in this app

`static/app.js` is a single page: `showPage()` toggles `.page` sections without reloading, and the album modal is a fixed overlay. One `<audio>` element created once at the shell level therefore survives all navigation. No router change is needed. The player must be **outside `<main>`** (as a sibling after `<footer>`/before the modal root) so page swaps never touch it.

### 2.2 Backend (new modules only)

- `integrations/navidrome/stream.py`: signed-request helpers reusing `_signed_request` from `client.py` (same salt/token scheme as `cover_art`).
  - `open_stream(config_provider, song_id, *, max_bitrate, range_header)` returns an `httpx` streamed response (not buffered).
  - `scrobble(config_provider, song_id, *, submission, time_ms)` calls `scrobble.view`.
- `app/api/player.py`: router registered next to the other routers.
  - `GET /api/player/stream/{song_id}?maxBitRate=`: relay with `Range` support (206 / `Accept-Ranges`, `Content-Range`, `Content-Length`, `Content-Type` passed through). Streams in chunks and closes the upstream on client disconnect.
  - `POST /api/player/scrobble` body `{id, submission: bool, time_ms}`: validates, forwards to Navidrome, returns `{ok}`.
  - `GET /api/player/song/{song_id}` (only if the front end cannot get metadata from existing payloads; see open question 8).
- Auth: both routes are under `/api/`, so the existing middleware already fails closed with 401 and the session cookie is sent automatically by `<audio src>` (same origin). **Do not** add them to `PUBLIC_PREFIXES`.
- Radio: no new route. The player uses the existing `/radio/stream/<token>` URL of a proxied station (see 2.5).

#### Stream route safety rules

- `song_id` must match a conservative opaque-id pattern (no `/`, `..`, whitespace, or query characters); reject otherwise with 400.
- Only forward whitelisted upstream parameters (`id`, `maxBitRate`, `format`); the browser cannot inject arbitrary Subsonic parameters or choose the Navidrome endpoint.
- `follow_redirects=False`, bounded connect timeout, no read timeout on the body (long songs), upstream error bodies never returned verbatim (Subsonic errors can arrive as 200 with XML/JSON). Detect `content-type` of `application/json`/`xml`/`text` and return 502/404.
- Never log the signed URL or query (it carries the token and salt).
- Verify the id is a song the app knows? Not required for a single-owner app (Navidrome enforces its own ACL), but note it as a decision (open question 9).

### 2.3 Frontend (new files; `app.js` grows minimally)

`app.js` is already 5,115 lines. New code goes in:

- `static/player.js`: loaded after `app.js` like `radio.js`; reuses `$`, `sendJSON`. Exposes `window.Player = {playAlbum, playSongs, enqueue, playNext, playStation}` for entry points.
- `static/player.css` (or a clearly delimited block in `app.css` if the owner prefers one stylesheet).
- `app/templates/index.html`: one `<section id="player" role="region" aria-label="Player">` markup, an `<audio id="playerAudio" preload="metadata">`, plus an `aria-live="polite"` status node for track changes.

Modules inside `player.js` (still one file, ordered sections): queue model, persistence, audio engine, scrobble tracker, Media Session adapter, render/UI, entry-point wiring.

### 2.4 Queue model and persistence

- Item: `{id, title, artist, album, albumId, coverId, duration, kind: 'song' | 'station', url?}`.
- State: `{items, index, position, shuffle, repeat: 'off'|'all'|'one', volume, muted}` stored under one versioned key (`navi.player.v1`), written on change and throttled (~5 s) for position.
- Restore on load: queue + index + position, **paused** (autoplay is blocked until a user gesture). Tolerate corrupt/old JSON (drop silently, never throw).
- Shuffle keeps a permuted order separate from the display order so toggling off returns to the original.
- Cap queue length (e.g. 500) with a visible message rather than silent truncation.
- Stale items: if a song 404s (removed from Navidrome), mark it unavailable, skip to the next, and show a non-color status.

### 2.5 Radio

- A station is played only through its relayed URL when the owner has switched the relay on, so the Heard log keeps working. For a non-relayed station, either play the original URL (no log) or show "Turn on Grab to log songs": see open question 6.
- Station items have no duration or seek; the UI hides the progress bar and shows "Live".
- The live ICY title is shown only if there is a supported way to read it. The relay already parses ICY server-side; exposing the *current title* to the browser would need a new field on `/api/radio/...` (contract addition, open question 7). Without it the tile shows the station name only.

### 2.6 Scrobbling

- On `play` of a new song: send `submission=false` (now playing).
- Track **played time** (accumulate `timeupdate` deltas while not paused and not seeking), not wall-clock or position. Scrobble once per play when played time reaches `min(duration/2, 240 s)` and duration is at least 30 s. Never twice for one play; seeking to the middle must not count.
- Repeat-one: each loop is a new play.
- Failure: retry a small bounded number of times, then drop; never block playback. Persist nothing about scrobbles.
- **Recommendation feedback risk:** plays flow into Navidrome (and Last.fm/ListenBrainz if linked there), which the discovery engine reads for taste and listen counts. This is intended, but the owner should know the player will shift recommendations over time. See open question 10.

### 2.7 Layout and overlay behavior

- Desktop: `position: fixed`, `left` = rail width (`--rail-w`) + gutter, `right`/`bottom` gutters, rounded tile, own elevation. `body` / `main` get `padding-bottom` equal to the bar height **only while the player is visible** (class on `<body>`), so the last card is never hidden.
- Z-order (current: header 20, rail 15, modals 100): the bar sits **above page content and rail, below modals**. The album modal covers the bar, so modal playback controls must exist inside the modal (the tracklist play buttons are the primary entry point and need no bar). Open question 11.
- Hidden until something is queued; fully removed from tab order when hidden. A close/clear action empties the queue and stops audio.
- Mobile (narrow breakpoint): mini-bar (art, title, play/pause, next) sitting above any bottom nav and `env(safe-area-inset-bottom)`; tap expands a full-screen sheet with seek, volume, shuffle/repeat, queue. The sheet is a dialog: focus moves in, Esc/back closes, focus returns.
- Reduced motion: no slide/expand animations.

### 2.8 Accessibility and keyboard

- Real `<button>`s with `aria-label`, `aria-pressed` for shuffle/repeat, `role="slider"` (or `<input type="range">`) for seek and volume with `aria-valuetext` ("1:23 of 4:10").
- Shortcuts only when focus is not in a text field or the modal: Space (play/pause on the bar only when focused), plus Media Session keys globally. No global single-letter shortcuts without owner approval: they collide with the existing `keydown` handlers (`app.js:1246` and others).
- Track changes announced via the polite live region, not on every `timeupdate`.
- Status (loading, buffering, error, unavailable) always has text, not just color.

### 2.9 Media Session

`navigator.mediaSession.metadata` (title, artist, album, artwork from the existing owned-artwork proxy `ARTWORK_PATH + {coverId}` at 96/256/512 sizes) and action handlers for play, pause, previoustrack, nexttrack, seekto, seekbackward/forward. Clear it when the queue is cleared. Station items set metadata without seek handlers.

### 2.10 Settings

New Settings control: **Streaming quality**: "Original" (default) or max bitrate (e.g. 128/192/320 kbps), stored with the other app settings if a settings store pattern exists, else in `localStorage` as a per-device preference (a phone on mobile data differs from the desktop). Recommendation: per-device `localStorage`. Open question 12. Note FLAC/ALAC support varies by browser (Safari lacks FLAC seek in some versions); when `audio.error` fires with `MEDIA_ERR_SRC_NOT_SUPPORTED`, retry once with the transcoded format (e.g. `format=mp3`/`opus`) and tell the user.

## 3. Entry points

| Surface | Control | Behavior |
|---|---|---|
| Album modal tracklist | Play album, per-track play, "Play next", "Add to queue" | Uses song ids from the album payload (owned albums only) |
| Library page | Play / Shuffle on album and artist rows | Needs the track list; fetch via `/api/albums/{artist_key}/{album_key}` |
| Artist page | Play artist, Shuffle artist, play a top song | Owned songs only; unowned albums show no play control (they offer Get) |
| Song search results | Play, Add to queue | Owned songs from the owned index |
| Radio page | Play on each station row | Station item (see 2.5) |

Rule: only owned items get play controls. Recommendations and acquisition cards never offer play (they are not in Navidrome).

## 4. Phased delivery

Each phase is one focused PR, branched from `main`, tests added, no full-suite runs by agents (workflow rule), CI on the final head, UI changes manually verified through `LOCAL_UI_TESTING.md`.

**Phase 0: docs.** Owner approval; PRODUCT.md, DECISIONS (D-018), REQUIREMENTS (PLAYER-01..), TEST_PLAN. Direct to `main`.

**Phase 1: backend.** `integrations/navidrome/stream.py`, `app/api/player.py`, router registration (one import/include line outside the D-016 constraint: confirm where routers are assembled, `app/main.py` is not `navidrome_server.py`). Tests: `tests/test_navidrome_stream.py`, `tests/test_api_player_routes.py` (200/206 range, 401 unauthenticated, bad id, upstream error-as-200, disconnect closes upstream, whitelist, no credential leakage in headers/body/logs), scrobble validation.

**Phase 2: shell and engine.** `player.js` + markup + CSS: queue, audio engine, persistence, transport, seek/volume/shuffle/repeat, desktop bar, body padding, z-order. Tests: `tests/test_player_ui_contract.py` in the style of `test_radio_ui_contract.py`/`test_artwork_loading_ui_contract.py`; if the repo has no JS runner, queue/scrobble logic is kept in pure functions that can be exercised by a small node-free contract test or by Playwright-style manual steps (open question 13).

**Phase 3: entry points.** Album modal, Library, artist page, search results; play next / add to queue.

**Phase 4: queue panel, Media Session, mobile sheet, a11y pass.**

**Phase 5: scrobbling and quality setting.**

**Phase 6: radio.** Station playback via relay; live title only if the contract addition is approved.

**Later (separate contracts):** gapless/crossfade (two-element preload swap), EQ (Web Audio), lyrics (`getLyricsBySongId`).

## 5. Verification plan

- Focused tests only for agents; owner runs the full suite; CI on the PR head.
- Manual browser matrix (Chromium first, as per current policy; add Safari/iOS for FLAC and background audio):
  persistence across all page switches and modal open/close; reload restore (paused); seek in a FLAC and an MP3; queue reorder/remove; scrobble fires once and not on a skip at 10 s; offline/Navidrome-down error states; session expiry mid-playback (401 on a range request: show "Sign in again", don't loop); radio relay logs a Heard entry after 30 s; reduced motion; keyboard-only operation; 44 px targets.
- Docker/package check that `static/player.js` and any new module are included (`Dockerfile`, `.dockerignore`).

## 6. Risks

1. **Session expiry** mid-song: audio element gets a 401/redirect; must be detected (`error` event + status probe) rather than looping.
2. **Proxy cost:** the app now carries all audio bytes. Fine for one owner at home; document that remote use doubles bandwidth through the app host.
3. **Range handling bugs** make seek fail silently; needs explicit tests.
4. **Browser autoplay policy:** first play must come from a gesture; restored sessions start paused.
5. **Multiple tabs:** two tabs could both play and both overwrite `localStorage`. Mitigation: a `BroadcastChannel` that pauses the other tab, or accept last-writer-wins (open question 14).
6. **Recommendation drift** from scrobbles (2.6).
7. **`app.js` size** and the D-016 rule: keep integration hooks in `app.js` to a handful of lines.
8. **CSS collisions:** fixed header (z 20) and rail (z 15, inset from 82px) are already positioned; the bar must not overlap the rail's bottom items.

## 7. Proposed answers to the open questions

These are defaults proposed for the owner's approval; each can be overridden before the phase it affects.

1. **Gate (section 0).** Approval is still the owner's. Phase 0 documentation edits happen only after that approval.
2. **Rail overlap.** The bar starts to the right of the left rail (`--rail-w` plus a gutter) and spans to the right edge. It never covers the rail's items.
3. **Bar while a modal is open.** The modal covers the bar (modals stay at z-index 100, the bar sits below). Playback controls inside the album modal tracklist cover this case.
4. **Queue cap.** 500 items, with a visible message when the cap is hit.
5. **Play album.** Replaces the queue and starts at track 1. "Add to queue" and "Play next" are the explicit append actions.
6. **Non-relayed radio station.** Play the original station URL, and show the text "Songs are not logged. Turn on Grab to log them." The player never changes a station's relay setting.
7. **Live ICY title.** Not in v1. The tile shows the station name and "Live". Exposing the current title is a separate contract addition for Phase 6, if the owner wants it.
8. **Song data in existing payloads.** Verified in `discovery/search/index.py`: owned song entries carry `id`, `album_id`, `artist_id`, `duration` and `track_number`, and `discovery/search/album_page.py` already builds the owned tracklist from them. Cover ids come from the album and artist entries. No new metadata endpoint is planned; Phase 1 must confirm that the album page payload exposes each track's `id` and, if it does not, add only that field. Routers are registered in `app/main.py`, so the new router needs no change to `navidrome_server.py`.
9. **Stream route id check.** Navidrome's own access control is trusted; the route validates the id format only. Verifying against the owned index would couple the stream to index freshness for no gain in a single-owner app.
10. **Scrobbling toggle.** A per-device Settings toggle, on by default, so plays can be kept out of the listening history. The recommendation-drift note in 2.6 stands.
11. **Modal versus bar z-order.** As in answer 3.
12. **Quality setting.** Per-device `localStorage`, default "Original".
13. **Browser JS testing.** Stay with the Python contract tests used by `test_radio_ui_contract.py`, keep queue and scrobble logic in small pure functions, and rely on the manual browser matrix in section 5. No new test runner or dependency is introduced.
14. **Multiple tabs.** A `BroadcastChannel` message pauses playback in other tabs when one starts; `localStorage` stays last-writer-wins.
15. **Visual direction.** Artwork-led tile in the existing dark ink palette, yellow for the primary and selected play state, chart-red used sparingly. A design pass with the existing design tooling happens at the start of Phase 2 and is not a gate on Phases 0 and 1.
