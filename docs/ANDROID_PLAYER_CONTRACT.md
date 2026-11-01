# Android player contract (Discair)

Status: **Phase 0 documentation. The owner approved the direct-streaming approach on 2026-11-01. Nothing in this document is implemented.** Each later phase still needs its own PR and review.

This contract adapts the web proposal in [`PLAYER_PROPOSAL.md`](PLAYER_PROPOSAL.md) (PR #645) to the Android app only. The web UI gets no player under this contract, and no Librarian backend change is made (D-016 is untouched). Where the two documents disagree for Android, this one governs. Playback is Android-only: the web UI remains "not a player".

## 1. Decisions taken

| Topic | Decision |
|---|---|
| Audio path | **Direct from Navidrome** with Subsonic `stream.view`, using the credentials already on the device (`ANDROID_CLIENT_CONTRACT.md` 4.2). No Librarian proxy route. |
| Engine | AndroidX Media3 `ExoPlayer` inside a `MediaSessionService` (foreground service, media notification, lock-screen, Bluetooth and headset controls, audio focus). |
| Queue | On the device only, in a private app file written atomically (changed from DataStore in Phase 1 to avoid a new dependency for one small document), restored **paused** after a restart. |
| Form | Mini-player above the bottom bar, expanding to a Now Playing sheet (seek, shuffle, repeat, queue). |
| Entry points | Album page, Artist page, Library rows, song search results. Owned items only. |
| Scrobbling | Yes, per-device toggle in Settings, on by default. |
| Format | Original file by default; optional maximum bitrate in Settings. |
| Out of scope | Radio, live titles, gapless, crossfade, EQ, lyrics (each needs its own contract), any change to the web UI. |

## 2. Rules this contract inherits

- `ANDROID_CLIENT_CONTRACT.md` section 2 applies in full: 48dp targets, TalkBack labels, no third-party SDKs or analytics, bundled assets, honest states (not by colour alone), and the `/mobile-design` pass for every screen, recorded in `android/DESIGN.md` (rule 9).
- Exception requested and recorded here: the v1 decision "no foreground service or background progress" applied to acquisition. Playback needs a media foreground service. This exception covers playback only; acquisition still has no notifications or background work.
- Never log or display a stream URL, token or salt. Credentials never go in crash text, analytics or `Log` output.

## 3. Playback

### 3.1 Stream URLs
- Built only by one function in `net/` using the existing Subsonic token and salt scheme. A fresh salt and token are generated for each request URL, and the password is never sent.
- Parameters: `id`, and optionally `maxBitRate` and `format`. Nothing else is accepted from callers.
- `maxBitRate` is omitted (original) or one of `64, 96, 128, 192, 256, 320`. `format` is omitted (original file) or one of `mp3`, `opus`. `format=raw` is not used; original is expressed by omitting both. Values are emitted from the allowlist, never copied from input.
- Song ids come only from Librarian or Navidrome owned-album payloads that the screens already hold. The player takes ids, not free text.
- HTTPS only, per the network security config. Redirects are not followed to another host.

### 3.2 Failure and lifecycle (replaces the web streaming-lifecycle section)
The player layer owns connection lifetime, so these must be tested:
- Service stop, task removal and sign-out release the player, clear the notification and cancel in-flight loads. No player or connection survives `onDestroy`.
- Audio focus loss pauses; transient loss resumes only if the player was playing; permanent loss stops. "Becoming noisy" (headphones unplugged) pauses.
- Network drop mid-song: buffering state with words, then resume from the current position when the connection returns. A failed song is marked unavailable, skipped, and shown with text, not only colour.
- Navidrome answers 404 or a Subsonic error body (these arrive as HTTP 200 with JSON or XML, not audio): the item is marked unavailable and is not retried in a loop.
- 401 or Subsonic auth codes (40, 41, 44, 50): playback stops and the app shows "Sign in again" once; no retry loop.
- Server ignores `Range` and returns 200: seeking may restart the stream; the UI must not show a false position.
- Unsupported-format error (`ERROR_CODE_DECODING_FORMAT_UNSUPPORTED` or equivalent): retry once for that song with `format=mp3`, tell the user, and never change the saved quality setting.

### 3.3 Queue and persistence
- Item: `{songId, title, artist, album, albumId, coverId, durationSec}`. Cover art goes through the existing artwork loading.
- State: `{items, index, positionMs, shuffle, repeat: off|all|one, volume}` in one versioned JSON document. Position is written about every 5 s and on pause and stop.
- Restore on start: queue, index and position, **paused**. Corrupt or old data is dropped without a crash.
- Shuffle keeps a permuted order separate from display order so turning it off restores the original.
- Cap 500 items with a visible message at the cap.
- Play album replaces the queue and starts at track 1. "Add to queue" and "Play next" are the explicit append actions.
- Only owned items have play controls. Recommendation and acquisition cards never do.

### 3.4 Navigation and surfaces
- The mini-player sits above the bottom bar and `WindowInsets`, hidden and out of the accessibility tree when the queue is empty. A clear action empties the queue and stops audio.
- Tapping it opens the Now Playing sheet: seek bar with spoken value ("1:23 of 4:10"), shuffle and repeat as toggles with state, volume follows the system, queue panel with reorder, remove and play next. Back closes the sheet.
- Track changes are announced once through the accessibility live region, not on every position update.
- Reduced motion: no expand or slide animation when the system setting is on.
- The Downloads header icon and the four bottom tabs are unchanged.

## 4. Scrobbling

The app calls Navidrome's `scrobble.view` directly. This writes to the listening history that discovery reads, and to Last.fm or ListenBrainz if linked in Navidrome. **Enabling scrobbling therefore feeds recommendations and will shift them over time.**

- *Now playing:* one `submission=false` call per play, when the player first reaches playing for that item (not on tap), so a track that fails to load sends nothing. Pausing and resuming do not resend.
- *Final scrobble:* one `submission=true` call per play when **played time** reaches `min(duration/2, 240 s)`, for tracks of at least 30 s. Shorter tracks send now-playing only.
- *Played time* counts media seconds advanced while actually playing, not paused, not seeking and not buffering. Seeking never adds or subtracts played time, and seeking forward past the threshold does not scrobble. Playback speed does not change the count.
- *Duration:* the server's `duration` is authoritative. If it is missing, zero or negative, use the player's duration once finite and positive; if neither exists, the threshold falls back to 240 s of played time. If the two disagree by more than 10 %, the larger applies.
- *New play identity:* repeat-one loops, replaying the same queue entry, and choosing the same song again each start a new play with a reset tracker. A restore after a restart starts no play until the user presses play, and earlier played time is not carried over.
- *Time stamp:* each scrobble sends the play start time as `time` (milliseconds).
- *Duplicates and retries:* `scrobble.view` has no idempotency key, so a lost response is ambiguous. **An ambiguous outcome is never retried.** A retry is allowed only when the request was provably not sent (DNS failure or connect failure or connect timeout before any request bytes). At most 3 retries with backoff (2 s, 10 s, 30 s) while the app process lives, keeping the original `time`. Anything after the request was sent (read timeout, reset, 5xx, unparseable or error body) drops that scrobble. Each play has a client-generated play id and a `submitted` flag set at the first send. The now-playing call is never retried. Retry state is in memory only.
- *Toggle:* Settings, per device, default on. Off suppresses both now-playing and final scrobble. Turning it off mid-track cancels any pending retry and sends nothing for that play, even if the threshold was passed earlier but unsent. Turning it on mid-track starts counting from that moment with no backfill.
- Scrobble failure never blocks or interrupts playback.
- Trade-off stated plainly: a scrobble can be lost on a network fault after send; the app's own retries cannot create a duplicate. Server-side de-duplication is not proposed.

## 5. Settings
- **Streaming quality:** Original (default) or a maximum bitrate from the allowlist, per device. It applies to songs started afterwards.
- **Scrobble plays:** on or off, per device, default on, with one line explaining that it feeds discovery.
- Both live with the existing Settings screen and are stored in the encrypted or ordinary preferences already used, not on the server.

## 6. Phases

Each phase is one focused PR from `main`. Agents run focused tests only (the owner runs the full suite; CI runs it on the PR head). UI phases get the `/mobile-design` review and a device check, and those are not claimed until done.

0. **Docs** (this change). `PRODUCT.md`, `D-018`, `PLAYER-01..` rows, a Player section in `TEST_PLAN.md`, and amendments to `ANDROID_CLIENT_CONTRACT.md`. Direct to `main` by the documentation-only rule.
1. **Playback core.** Media3 dependencies, `PlaybackService`, the stream URL builder with the allowlist, queue model and persistence, failure handling in 3.2. **Status: built and unit-tested; not run on a device (see "Phase 1 status" below).** Tests: URL building (allowlist, no credentials in logs or errors), queue logic including restore and corrupt data, failure classification against recorded Subsonic error bodies, and release on service stop with fakes that report open handles at the end.
2. **Scrobble tracker.** A pure Kotlin class and a `scrobble.view` client. Tests: short tracks, missing or zero duration, duration disagreement, seek, buffering, repeat-one, repeated playback, toggle on and off mid-track, retry classification, and a response lost after the request was sent being **not** retried.
3. **UI.** Mini-player, Now Playing sheet, queue panel, notification and lock-screen controls.
4. **Entry points.** Album, Artist, Library and Search, plus play next and add to queue.
5. **Settings and hardening.** Quality and scrobble toggle, the format fallback, expired sign-in and offline behaviour, TalkBack, landscape, 200 % text, reduced motion, signed release build run on the owner's phone.

Later, each with its own contract: gapless and crossfade, EQ, lyrics.

## 7. Verification

- Unit tests for URL building, queue, failure classification and scrobble tracker, in the existing `android/app/src/test` style.
- `./gradlew testDebugUnitTest assembleDebug lintDebug` per phase.
- Manual on the owner's phone over Tailscale: play and seek in a FLAC and an MP3, background and lock-screen controls, headset buttons, a phone call interrupting playback, airplane mode mid-song, restart restores paused, a scrobble appears once and not after a skip at 10 s, session expiry shows "Sign in again" without looping, TalkBack, 200 % text, landscape.
- Release build keeps the R8 rules working for Media3.
- Nothing is claimed as verified on a device until the owner has tested it.

## 8. Risks
1. Credentials and tokens appearing in logs or notification text: covered by tests that search error and log output.
2. Playback feeding discovery: the toggle and the notice in section 4 are the mitigation.
3. Foreground-service and battery behaviour on Android 13 and later (notification permission, service type `mediaPlayback`): decided in Phase 1.
4. Direct streaming puts the Navidrome account's full access behind the app; accepted by the owner (`ANDROID_CLIENT_CONTRACT.md` section 9, decision 3).
5. FLAC seek and codec support varies by device; the format fallback is the mitigation.

## 9. Phase 1 status

**Built and unit-tested; not run on an emulator or a phone.** In `android/app/src/main/kotlin/app/discair/player/`:
- `StreamUrl.kt`: the stream URL builder (allowlisted `id`, `maxBitRate`, `format`; fresh salt per URL; https only; no password in the URL) and `redactSecrets`.
- `PlayQueue.kt`, `QueueStorage.kt`: the queue (replace, enqueue, play next, remove, move, shuffle, repeat, unavailable songs, 500 cap) and its versioned JSON codec, which clamps hostile values and returns an empty queue for corrupt or old data; an atomic file store.
- `PlaybackFailure.kt`, `RefusedBodyInterceptor.kt`: failure classification (Subsonic errors arriving as 200 JSON or XML, HTTP statuses, auth codes 40/41/44/50 as "Sign in again", 70 as unavailable). The interceptor stops an error body reaching the decoder and never puts the URL or token in the exception.
- `PlaybackService.kt`, `StreamResolver.kt`: a `MediaSessionService` with ExoPlayer (audio focus, becoming-noisy pause, own OkHttp client with no cookies and no redirects). Controllers add items by song id only; the service builds the signed URL. Only this app and trusted system controllers may connect. The task being removed pauses and stops the service; destroy releases the player and session once (`ReleaseGuard`). Sign-out stops the service and deletes the saved queue.
- Manifest: `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS`, and the service with type `mediaPlayback`.

Run: `./gradlew clean testDebugUnitTest assembleDebug lintDebug assembleRelease` (136 unit tests, 0 failures, of which the player tests are new; the debug build and lint passed, and the minified release build succeeded with Media3). Not done or not verified:
- Nothing connects the queue to the player yet (that is Phase 3), so the service has no caller other than sign-out. The `POST_NOTIFICATIONS` runtime prompt is not requested yet.
- A real stream, seek, focus loss, headset unplug, network drop and resume, the unsupported-format retry with `format=mp3`, and the 401 "Sign in again" path are covered only as classification and URL logic, not against a device or the real Navidrome.
- The `ReleaseGuard` test uses a fake that counts open handles; it does not prove the real ExoPlayer is released.
- The interceptor reads error bodies only for answers whose content type is not audio. A Navidrome that returns an error with an audio content type would not be caught.
- The Gradle build needs JDK 17; the system default on the owner's Mac is JDK 27 and fails, so set `JAVA_HOME` to the Homebrew `openjdk@17`.
