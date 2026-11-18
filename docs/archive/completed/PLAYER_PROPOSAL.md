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
  - `GET /api/player/stream/{song_id}?maxBitRate=&format=`: relay with `Range` support (206 / `Accept-Ranges`, `Content-Range`, `Content-Length`, `Content-Type` passed through). Streams in chunks and closes the upstream on client disconnect.
  - `POST /api/player/scrobble` body `{id, submission: bool, time_ms}`: validates, forwards to Navidrome, returns `{ok}`.
  - `GET /api/player/song/{song_id}` (only if the front end cannot get metadata from existing payloads; see open question 8).
- Auth: both routes are under `/api/`, so the existing middleware already fails closed with 401 and the session cookie is sent automatically by `<audio src>` (same origin). **Do not** add them to `PUBLIC_PREFIXES`.
- Radio: no new route. The player uses the existing `/radio/stream/<token>` URL of a proxied station (see 2.5).

#### Streaming lifecycle and failure behavior

The existing `client.py` calls use a synchronous `httpx.Client` context manager that closes when the call returns. A stream must instead keep the upstream response open while the browser reads, so `stream.py` owns a distinct lifecycle:

- `open_stream` creates its own `httpx.Client` (not the shared one) and sends the request with `client.build_request` + `client.send(request, stream=True)`. It returns a small handle that owns both the response and the client and exposes one idempotent `close()` (response first, then client).
- The route returns a `StreamingResponse` whose body is an async generator over `response.aiter_raw()` (or `iter_raw()` in a threadpool if the client stays synchronous) with `try/finally: handle.close()`. If the response is never started (an exception between `open_stream` and the response being returned), the route closes the handle in its own `except`/`finally`, and a `BackgroundTask` calls `close()` as a second, idempotent guard.
- **Normal completion:** generator is exhausted, `finally` closes.
- **Client disconnect or cancellation:** `GeneratorExit` / `asyncio.CancelledError` / `ClientDisconnect` unwinds through the `finally` and closes the upstream. The cancellation is re-raised, never swallowed.
- **Upstream failure before the first byte** (connect error, timeout, non-2xx, a 200 whose `content-type` is JSON/XML/text because Subsonic reports errors that way): close the handle and return 502 (or 404 for a Subsonic "not found"), with a generic body. The upstream body is never returned.
- **Upstream failure mid-body** (`httpx.ReadError`, `RemoteProtocolError`, premature close): headers are already sent, so the generator stops, closes, and logs a redacted event. It never pads or fabricates bytes. A response with `Content-Length` that ends short is aborted at the transport so the browser sees a failed transfer, not a truncated file presented as complete. The player recovers by re-requesting from the current position with a `Range` request.
- **Range requests:**
  - A single `bytes=` range is passed through as-is, and 206, `Content-Range`, `Content-Length` and `Accept-Ranges` come from the upstream response.
  - Multi-range, malformed or non-`bytes` units: 416 without contacting Navidrome. Reject syntactically before forwarding.
  - Unsatisfiable range: if Navidrome answers 416, relay 416 with its `Content-Range: bytes */N`, and close.
  - If the upstream ignores `Range` and answers 200, relay 200 (the browser handles it) and never relabel it as 206.
  - A transcoded stream (`maxBitRate` or `format`) may not support ranges; relay whatever the upstream sends and send `Accept-Ranges: none` if it did not advertise bytes.
- **Leak protection:** timeouts are bounded for connect and pool acquisition; the read timeout on the body is unbounded only while the client stays connected. A cap on concurrent open streams (default 8) returns 429 on the ninth so a stuck player or a retry loop cannot exhaust connections. Slots are released in the same `close()`.

#### Stream route safety rules

- `song_id` must match a conservative opaque-id pattern (no `/`, `..`, whitespace, or query characters); reject otherwise with 400.
- Only forward whitelisted upstream parameters (`id`, `maxBitRate`, `format`); the browser cannot inject arbitrary Subsonic parameters or choose the Navidrome endpoint.
- **`maxBitRate` and `format` are validated, not passed through.** `maxBitRate` is omitted (original) or one of `64, 96, 128, 192, 256, 320` (kbps); `format` is omitted (original file, no transcoding) or one of `mp3`, `opus`. Any other value, a repeated parameter, or `format` without a transcode-capable value returns 400 with zero upstream requests. `format=raw` is not accepted: "original" is expressed by omitting both parameters. The values are re-emitted from the allowlist, never copied from the query string.
- `follow_redirects=False`, bounded connect timeout, no read timeout on the body (long songs), upstream error bodies never returned verbatim (Subsonic errors can arrive as 200 with XML/JSON). Detect `content-type` of `application/json`/`xml`/`text` and return 502/404.
- Never log the signed URL or query (it carries the token and salt).

#### Song ownership check (stream and scrobble)

The app's login session and the server-side Navidrome credentials are separate authorization boundaries, and the Navidrome account may reach more than the app's library. Format validation alone is therefore not enough. Both `GET /api/player/stream/{song_id}` and `POST /api/player/scrobble` must resolve the id against the owned index (`OwnedIndex.view().data.songs`, `discovery/search/index.py`) **before any request is made to Navidrome**.

- Lookup uses a set of ids built from the current `OwnedData` (cached on the data object, not rebuilt per request).
- Order of checks: session (401) -> id format (400) -> owned lookup (404) -> forward. An unknown, unowned or malformed id never reaches Navidrome, and the 404 body does not distinguish "not owned" from "does not exist".
- **Index not ready** (`IndexView.state` is building or unavailable, no `data`): respond 503 with `Retry-After`. There is no fallback to forwarding unchecked, and no fallback to a last-known-good index from a different Navidrome generation (`ensure()` already drops that data).
- **Stale entries** (song deleted from Navidrome but still indexed): the lookup passes, Navidrome answers 404, and the route returns 404 without exposing the upstream body. The player marks the item unavailable (2.4). The index is not trusted to prove existence, only ownership.
- **Recently added songs** (not yet indexed): 404 until the next index build. The route never refreshes the index itself and never retries with a looser check. The client treats this like an unavailable item; a library refresh makes the song playable.
- Scrobble applies the same lookup, so a client cannot write plays for songs outside the library.

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
- **Contract details:**
  - *Duration.* The server's `duration` (owned index) is authoritative. If it is missing, zero or negative, use `audio.duration` once it is finite and positive; if neither is available, the threshold falls back to 240 s of played time. If the two disagree by more than 10 %, the larger of the two applies (an over-short threshold would scrobble early; a long one only delays). Tracks under 30 s never scrobble, but still send now-playing.
  - *Played time* accumulates only while the element is actually advancing: `playing` and not paused, not seeking, not buffering (`waiting`/`stalled`). Each `timeupdate` delta is capped (for example 2 s) so a throttled background tab cannot credit a jump. The tracker counts media seconds advanced, not wall-clock time, so a `playbackRate` other than 1 neither speeds up nor slows down the count, and the 4 minute limit is media time.
  - *Seeking* never adds played time and never resets it. Seeking forward past the threshold does not scrobble; seeking backward does not subtract.
  - *Now-playing* is sent once per play, when the element first reaches `playing` for that item, not on `play` intent, so a track that fails to load sends nothing. Pausing does not resend; resuming after a pause does not start a new play.
  - *New play identity.* A play is a `(queue entry, play-start time)` pair. Repeat-one restarts, replaying the same item from the queue, and choosing the same song again each begin a new play with a reset tracker. Restoring the queue after a reload starts no play until the user presses play, and played time from before the reload is not carried over.
  - *Duplicates and retries.* Navidrome's `scrobble.view` has no idempotency key, so if Navidrome records a scrobble and the response is lost, the app cannot know whether it succeeded, and a retry could record the play twice. The contract therefore **never retries an ambiguous outcome**; losing one scrobble is preferred to double-counting a play in the listening history that discovery reads.
    - The route classifies every failure. `{ok: false, retryable: true}` is returned only when the route knows the request was **not accepted**: the ownership check or validation rejected it (no retry, 4xx), the index was not ready (503), the concurrency or rate cap applied (429), or the connection to Navidrome failed before any request bytes were sent (connect error or connect timeout). Everything after the request was sent (read timeout, reset, a 5xx, a response that fails to parse, a Subsonic error body) is `retryable: false`, because Navidrome may have recorded it.
    - The client retries only `retryable: true`, at most 3 times with backoff (for example 2 s, 10 s, 30 s) while the page is open. An unretryable failure drops that scrobble. The now-playing ping (`submission=false`) does not create a play, so it is never retried.
    - Each play carries a client-generated play id and a `submitted` flag set at the first send; a play that has been sent once is never sent again except through the `retryable: true` path above. The retry keeps the original `time_ms` (the play start).
    - Retry state is in memory only; a reload drops a pending retry. Multiple tabs cannot double-scrobble: only one tab plays at a time (open question 14).
    - Trade-off, stated plainly: a scrobble can be lost on a network fault after send; a duplicate is not possible through the app's own retries. Server-side deduplication (a play-id store) is deliberately not proposed, since it would add persisted state to the backend for a low-frequency failure. The owner may override this in section 7, answer 10.
  - *Disabling.* The Settings toggle suppresses **both** the now-playing ping and the final scrobble. Turning it off mid-track cancels any pending retry and sends nothing for the current play, even if the threshold was passed earlier but unsent. Turning it on mid-track starts counting from that moment and does not backfill. Radio stations never scrobble.
  - *Server side.* `POST /api/player/scrobble` rejects ids outside the owned index (ownership check above), `time_ms` that is not an integer within a sane window (not in the future, not older than 24 h), and `submission` that is not a boolean.
- Failure never blocks playback.
- **Listening history:** with scrobbling on, playback in this app writes plays to Navidrome (and Last.fm/ListenBrainz if linked there). That history is exactly what the discovery engine uses for taste and listen counts, so enabling playback scrobbling feeds recommendations and will shift them over time.
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

New Settings control: **Streaming quality**: "Original" (default) or max bitrate (e.g. 128/192/320 kbps), stored with the other app settings if a settings store pattern exists, else in `localStorage` as a per-device preference (a phone on mobile data differs from the desktop). Recommendation: per-device `localStorage`. Open question 12. Note FLAC/ALAC support varies by browser (Safari lacks FLAC seek in some versions); when `audio.error` fires with `MEDIA_ERR_SRC_NOT_SUPPORTED`, retry once with `format=mp3` (the first allowed value in the stream route's `format` allowlist, section 2.2; `opus` is selectable in the same way) and tell the user. The fallback uses only values the endpoint contract allows, and never changes the saved quality setting.

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

**Phase 1: backend.** `integrations/navidrome/stream.py`, `app/api/player.py`, router registration (one import/include line outside the D-016 constraint: confirm where routers are assembled, `app/main.py` is not `navidrome_server.py`). Authorization and lifecycle contracts (2.2) are settled before any code. Tests: `tests/test_navidrome_stream.py`, `tests/test_api_player_routes.py`:
  - *Ownership (stream and scrobble):* owned id forwarded; unknown, unowned and malformed ids return 404/400 and the mocked Navidrome transport records **zero** requests; index building/unavailable returns 503 with zero upstream requests; stale entry (owned, upstream 404) returns 404 with no upstream body; recently added song (not indexed) returns 404; index generation change drops access to the old ids.
  - *Lifecycle (mocked upstream that records open/close):* normal completion closes; client disconnect mid-body closes; task cancellation closes and re-raises; upstream error before first byte (connect error, timeout, non-2xx, error-as-200 JSON/XML) closes and returns 502/404 with a generic body; mid-body `ReadError`/short body closes and aborts without fabricating bytes; exception between `open_stream` and response start closes; double `close()` is a no-op; after every test the mock reports zero open responses and clients, and the concurrent-stream counter returns to zero. A test that only passes the happy path must fail this open-handle assertion.
  - *Range:* single range 206 passthrough; multi-range, malformed and non-bytes 416 with zero upstream requests; upstream 416 relayed; upstream 200 to a Range request relayed as 200; headers passed through.
  - *Parameters:* `maxBitRate` and `format` accept only the allowlisted values; others, repeats and `format=raw` return 400 with zero upstream requests; forwarded values come from the allowlist.
  - *Other:* 401 unauthenticated, upstream whitelist, 429 over the concurrency cap, no credential leakage in headers/body/logs.
  - *Scrobble route:* `submission`/`time_ms` validation and ownership.

**Phase 2: shell and engine.** `player.js` + markup + CSS: queue, audio engine, persistence, transport, seek/volume/shuffle/repeat, desktop bar, body padding, z-order. Tests: `tests/test_player_ui_contract.py` in the style of `test_radio_ui_contract.py`/`test_artwork_loading_ui_contract.py`; if the repo has no JS runner, queue/scrobble logic is kept in pure functions that can be exercised by a small node-free contract test or by Playwright-style manual steps (open question 13).

**Phase 3: entry points.** Album modal, Library, artist page, search results; play next / add to queue.

**Phase 4: queue panel, Media Session, mobile sheet, a11y pass.**

**Phase 5: scrobbling and quality setting.** The scrobble tracker is a pure function over (event, now, duration) and is tested for: short tracks (under 30 s send now-playing only), missing/zero/inaccurate duration, repeat-one (each loop scrobbles once), seeking (forward, backward, to the middle), pause/resume, buffering stalls, playback-rate changes, repeated playback of the same song, retry without duplicates, and the toggle suppressing both pings. A regression test simulates Navidrome accepting a scrobble while the response is lost (read timeout or connection reset after send) and asserts that the route returns `retryable: false`, the client sends exactly one submission, and the mocked Navidrome records exactly one scrobble. Companion tests assert that a connect failure before send is retried and then succeeds once, that a 5xx after send is not retried, and that `submission=false` is never retried. Route tests for ownership and validation are in Phase 1.

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
6. **Recommendation drift** from scrobbles: playback writes to the listening history that discovery reads (2.6).
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
9. **Stream route id check.** Revised after plan review. The stream and scrobble routes validate the id format and then require the id to be an owned song in the app's index, before anything is forwarded to Navidrome. Unknown, unowned or invalid ids are rejected; index-not-ready returns 503; stale and recently added entries are handled as in "Song ownership check" (section 2.2), with no unsafe fallback.
10. **Scrobbling toggle.** A per-device Settings toggle, on by default, so plays can be kept out of the listening history. Turning it off suppresses both now-playing and final scrobbles. Enabling it means playback feeds the listening history that discovery reads; the recommendation-drift note in 2.6 stands. The threshold stays at half the track or four minutes, whichever comes first, with the edge cases defined in 2.6. Ambiguous scrobble outcomes are not retried, so a lost response can drop a scrobble but cannot duplicate one; the owner may instead request server-side deduplication with a play id.
11. **Modal versus bar z-order.** As in answer 3.
12. **Quality setting.** Per-device `localStorage`, default "Original".
13. **Browser JS testing.** Stay with the Python contract tests used by `test_radio_ui_contract.py`, keep queue and scrobble logic in small pure functions, and rely on the manual browser matrix in section 5. No new test runner or dependency is introduced.
14. **Multiple tabs.** A `BroadcastChannel` message pauses playback in other tabs when one starts; `localStorage` stays last-writer-wins.
15. **Visual direction.** Artwork-led tile in the existing dark ink palette, yellow for the primary and selected play state, chart-red used sparingly. A design pass with the existing design tooling happens at the start of Phase 2 and is not a gate on Phases 0 and 1.
