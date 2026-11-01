# Android player contract (Discair)

Status: **Phases 0 to 5 are merged (PRs #661 to #665) and the first device run on the owner's phone worked: playback, next, shuffle, the notification, Now Playing, the queue with covers, seeking and Record plays.** The rest of the device checklist (section 13) is still open. Gapless, crossfade, EQ and lyrics are not started and need their own contract and approval.

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
2. **Scrobble tracker.** (Built; see section 10.) A pure Kotlin class and a `scrobble.view` client. Tests: short tracks, missing or zero duration, duration disagreement, seek, buffering, repeat-one, repeated playback, toggle on and off mid-track, retry classification, and a response lost after the request was sent being **not** retried.
3. **UI.** (Built; see section 11.) Mini-player, Now Playing sheet, queue panel, notification and lock-screen controls.
4. **Entry points.** (Built; see section 12.) Album, Artist, Library and Search, plus play next and add to queue.
5. **Settings and hardening.** (Built; see section 13. The device run is the owner's.) Quality and scrobble toggle, the format fallback, expired sign-in and offline behaviour, TalkBack, landscape, 200 % text, reduced motion, signed release build run on the owner's phone.

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

## 10. Phase 2 status

**Built and unit-tested; not run on an emulator or a phone, and not wired to the player.** Phase 1 was merged in PR #661 (`c2b63ae`; CI passed on head `02f6c81`). In `player/`:
- `ScrobbleTracker.kt`: per-play played-time counting from the player's media position. Only small forward steps (up to 2 s per tick) while advancing are credited; seeks, pauses, buffering and playback speed add or remove nothing. Threshold `min(duration/2, 240 s)`, tracks under 30 s never scrobble, server duration is authoritative, the player's duration is used when the server's is missing, the larger applies when they differ by more than 10 %, and with no duration the limit is 240 s.
- `ScrobbleCoordinator.kt`: one now-playing per play (on first playing), one final scrobble per play, a play id and a submitted flag, retries only for a request that was provably not sent (at most 3, after 2 s, 10 s and 30 s, with the original start time), no retry after an ambiguous outcome, no retry of now-playing, and the Settings toggle (off cancels pending retries and sends nothing for the current play; on mid-track counts from then, with no backfill and no now-playing ping). Errors from the client are swallowed and never reach playback.
- `NavidromeScrobbler.kt`: direct `scrobble` call with `id`, `time` and `submission`. The HTTP client records when it starts writing the request, so a failure before that is `NotSent` and every failure after it is `Ambiguous`; a non-2xx answer or a Subsonic error body is `Ambiguous`. Redirects are not followed. The production factory requires https.

Run: `./gradlew clean testDebugUnitTest assembleDebug lintDebug assembleRelease` on JDK 17: 178 unit tests, 0 failures (52 new), debug build, lint and the minified release build succeeded. The client tests use a local socket server, including a request that arrives and is then dropped without an answer (ambiguous, counted once) and a refused connection (not sent). The coordinator tests use virtual time and include: a lost response after send is not retried; retries stop at 3 and keep the original time; short tracks, repeat-one, repeated playback, seeking, a skip at 10 s, and the toggle off and on mid-track.

Not done or not verified:
- Nothing feeds player events into the coordinator yet (Phase 3), and the Settings toggle and its storage are Phase 5; `enabled` is a constructor flag for now.
- No scrobble was sent to a real Navidrome, so the `time` and `submission` parameters are not confirmed against the owner's server version, and nothing was checked in Navidrome's play counts or Last.fm or ListenBrainz.
- The "request was sent" signal depends on OkHttp's `requestHeadersStart`; a connection reset during that write is counted as sent (ambiguous), which is the safe direction.
- An error returned with a non-2xx status (for example 401) is treated as ambiguous and dropped, not shown as "Sign in again".
- Tick cadence (about 1 s) is assumed by the 2 s cap; the Phase 3 position poller must keep to it.

## 11. Phase 3 status

**Built and unit-tested; not run on an emulator or a phone.** Phase 2 was merged in PR #662 (`67f1c0c`; CI passed on head `90ded07`). New:
- `PlayerPort` / `Media3Port`: the player seen from the controller, and its Media3 `MediaController` adapter. Commands given before the service connects are held and run in order. Items carry only the song id and display text; the service builds the signed stream URL, and a per-item `format=mp3` request (the unsupported-format fallback) is read there.
- `PlayerController`: the queue, saved to disk on change (position about every 5 s), restored paused; failure handling (an unavailable song is marked and skipped with words; a rejected login pauses once and shows "Sign in again"; a lost connection waits and resumes when the connection returns, or on Retry now; an unsupported format retries once with MP3 and then gives the song up); scrobble wiring (a play starts when playback first runs, repeat-one loops are new plays, seeks are not credited). It holds no Android types.
- Screens in `ui/player/`: mini-player, Now Playing sheet (cover, seek bar, shuffle, previous, play or pause, next, repeat, clear queue with confirmation) and the queue panel (play, Move up, Move down, Remove). Mounted in `MainShell` above the bottom navigation on every page; the notification permission is requested once when playback first starts. Sign-out empties the controller before the service is stopped. Design decisions: `android/DESIGN.md`.

Run: `./gradlew testDebugUnitTest assembleDebug lintDebug minifyReleaseWithR8` on JDK 17: 200 unit tests, 0 failures (22 new for the controller), lint clean, R8 succeeded. The signed release build was **not** run: `keystore.properties` points to `~/Documents/andr/discair-release.jks`, which macOS moved into `~/iCloud Drive (Archive)/Documents/andr/` when iCloud sync was switched off; the key was left where it is.

Not done or not verified:
- Nothing in the app calls `playItems`, `enqueue` or `playNext` yet, so there is no way to start playback from the UI until the Phase 4 entry points exist.
- Nothing was run on a device: the service start, the Media3 connection, the media notification, lock-screen and headset controls, audio focus, the sheet, TalkBack, landscape and 200% text.
- The notification has no cover art. The queue items need a cover address; Phase 4 supplies it.
- Playback restore with an empty or changed Navidrome login: the service drops items it cannot sign, and the controller does not yet notice.
- The service reads the encrypted settings on its main thread each time items are added (from Phase 1); worth moving off it.
- The Settings toggle for scrobbling and the streaming quality are Phase 5; the controller's `setScrobbling` exists but nothing calls it.
- The sheet's animation is not switched off for the reduced-motion setting.

## 12. Phase 4 status

**Built and unit-tested; not run on an emulator or a phone.** Phase 3 was merged in PR #663 (`1d41f79`; CI passed on head `8002f5f`; a signed release build also succeeded once the keystore was reachable again).

**Finding that shaped the design:** the Librarian album page does not return song ids (its tracks carry number, title, duration and `owned` only), and the web proposal had left this as a Phase 1 check. No backend change was made. The album page gives the Navidrome album id, and `ANDROID_CLIENT_CONTRACT.md` 5.1 already lists `getAlbum` and `getArtist` as direct Navidrome calls, so the app reads song ids from Navidrome. Song search results already carry `id`, `album_id`, `duration` and `track_number`.

New in `player/`: `SongSource` (`SubsonicSongSource` reads `getAlbum` and `getArtist`; ids are validated and a bad id never makes a request; songs are put in disc then track order) and `PlayActions` (play album, play from a track, shuffle, Play next, Add to queue, play artist, play one search song; one load at a time; failures become messages and leave playback alone). Screens: Play, Shuffle and More on the album page, owned tracks tap to play from there, Play and Shuffle on the artist page and a play button on owned Top songs, a play button on Library album and artist rows, Play and Add to queue on song search results. Messages show in the snackbar. Design notes: `android/DESIGN.md`.

Run: `./gradlew testDebugUnitTest assembleDebug lintDebug assembleRelease` on JDK 17: 223 unit tests, 0 failures (23 new: the recorded `getAlbum` and `getArtist` answers, error bodies, signing without the password, bad ids, track matching, and the play actions against a fake source and player), debug build, lint and the signed release build succeeded.

Not done or not verified:
- No screen was run on a device; nothing has played a real song from Navidrome through the Media3 service, so the whole path from tap to sound is untested.
- Per-track Play next and Add to queue, a Shuffle button on Library rows, and play controls on Home and Discover cards are not built.
- Matching a page track to a Navidrome song uses the normalised title, then the track number. A remastered title with a different number can fail to match and says so.
- The Top song button depends on the artist's library album having the same name as the song's album; otherwise only the owned mark shows.
- Playing a large artist reads one album per request before playback starts; the time over Tailscale is unmeasured.
- The Settings toggles for streaming quality and scrobbling are still Phase 5.

## 13. Phase 5 status

**Built and unit-tested; not run on an emulator or a phone.** Phase 4 was merged in PR #664 (`dd89b51`; CI passed on head `5470011`).

Built:
- Settings, section "Playback": streaming quality (Original or 320, 256, 192, 128, 96, 64 kbps) and "Record plays" (on by default), both per device in ordinary preferences (`PlayerSettings`). The quality is read each time a stream address is made, so a change applies to songs started afterwards; the Record plays switch is applied to the running player at once (off cancels pending retries and sends nothing more for the current play, as in section 4).
- The service no longer opens the encrypted settings on its main thread each time items are added: it uses the servers the signed-in screens already hold, and reads the encrypted store once as a fallback when the service starts without the app open (the gap noted in section 11). The stream address is now made by a function that is tested without Android (`StreamResolver.urlFor`).
- Already built earlier and now the hardening for this phase: the MP3 retry for one song without changing the saved quality (Phase 3), "Sign in again" without a retry loop (Phase 3), resume after a lost connection (Phase 3), sign-out stops the service and deletes the queue (Phases 1 and 3).

Run: `./gradlew testDebugUnitTest assembleDebug lintDebug assembleRelease` on JDK 17: 230 unit tests, 0 failures (7 new), debug build, lint and the signed release build succeeded.

Not done or not verified (the acceptance in section 6 needs the owner's phone, which this environment does not have):
- The whole path from tap to sound has never run: service start, the Media3 connection, a real stream from Navidrome, seek, the notification, lock screen and headset buttons, audio focus, a phone call, airplane mode mid-song, restart restoring paused, a scrobble appearing once in Navidrome, session expiry, TalkBack, landscape, 200% text.
- Reduced motion: standard Compose animations follow the system animator scale; not checked on a device.
- The notification and lock screen cover art: not built on purpose, but the owner's phone shows a cover in the notification anyway (see the first device findings).
- The scrobble `time` and `submission` parameters are unconfirmed against the owner's Navidrome version.

**Owner's device checklist** (install the signed release build; record what you saw in `android/DESIGN.md`):
1. Sign in; open an album in the library; tap Play. Does music start, and does the mini-player show the title?
2. Seek in a FLAC and in an MP3. Pause, resume, next, previous, shuffle, repeat one.
3. Lock the phone: do the notification and lock-screen controls work? Press a headset button.
4. Start a call or another audio app: does playback pause and resume sensibly?
5. Switch to airplane mode mid-song, then back: does it say it is waiting and resume by itself?
6. Close the app from the recent apps list and reopen it: is the queue back, paused, at the same place?
7. Play a song past the halfway point: does Navidrome (or Last.fm) show exactly one play? Skip a song at 10 seconds: no play.
8. Turn Record plays off and play a song past halfway: no play recorded. Change the streaming quality and start a song: does it convert?
9. Turn TalkBack on and go through the mini-player, the sheet, the queue and the Settings section. Try 200% text and landscape.
10. Sign out: does the notification disappear and the queue stay gone after signing in again?

### First device findings (2026-11-01, owner's phone)

- Works: play from an album page, next, shuffle, the media notification.
- **Crash when opening Now Playing from the mini-player (several times).** Cause (found by reading the code, not by a stack trace): the sheet was composed outside the `CompositionLocalProvider` that supplies the image loader, so its cover threw "No image loader". The mini-player is inside the provider, which is why it drew. Fixed by moving the sheet inside the provider. The fix is built and unit tests pass, but it has not been confirmed on the phone; no regression test exists because the screens have no UI tests.
- Covers: shown in the mini-player, the Now Playing sheet and (unexpectedly, since Phase 3 did not build it) the media notification. Missing in the queue list because the queue rows had no cover at all; a 40dp cover was added to each row.
- Confirmed by the owner after the fix: Now Playing opens, the queue shows, the seek bar moves and seeking works, and Record plays works.
