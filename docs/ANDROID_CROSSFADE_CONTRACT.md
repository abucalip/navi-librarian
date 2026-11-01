# Android crossfade contract (Discair)

Status: **phase X0 (documents) started on the owner's instruction on 2026-11-01. The owner did not answer section 11 point by point, so every proposed default there stands until the owner overrides it before the phase it affects. Nothing is built; X1 (the spike) is the next phase and needs the owner's go-ahead.** This is the "crossfade" item that [`ANDROID_PLAYER_CONTRACT.md`](ANDROID_PLAYER_CONTRACT.md) sections 6 and 14, [`ANDROID_EQ_CONTRACT.md`](ANDROID_EQ_CONTRACT.md) section 1 and `ACTIVE_WORK.md` left for its own contract (proposed `D-021`). It was committed directly to `main` as documentation only (workflow rule 8). No code is written before X1 is approved.

## 1. Purpose and scope

At the end of a song, let the next one fade in while the current one fades out, on the owner's phone, with a length the owner chooses and a switch to turn it off.

In scope:
- An automatic crossfade at song changes made by the player itself (the current song reaching its end), in the service, so it works with the screen off, from the notification and over Bluetooth.
- A length setting (seconds) and an on/off switch, stored on the device.
- A rule that keeps albums that are meant to be continuous gapless (section 5.3).
- Honest states: when a join cannot be crossfaded, it plays as it does today.
- A Settings row and a small screen or sheet section for the setting (section 7).

Out of scope (each would need its own contract):
- The web UI. No Librarian change (D-016 is untouched). The web stays "not a player".
- Crossfade on manual skips (next, previous, tapping a queue row) in version 1 (section 11, question 3).
- Beat matching, tempo matching, DJ-style transitions, "smart" mix points by analysing the audio, silence trimming at song ends, per-song or per-album lengths.
- ReplayGain or volume normalisation (so two songs of different loudness will crossfade at their own levels).
- Radio.

## 2. Facts about the current player

From `PlaybackService.kt`, `PlayerSettings.kt`, `PlayerPort.kt` and `build.gradle.kts` on `main` (`a6c4f4d`):

| Fact | Value |
|---|---|
| Engine | One Media3 `ExoPlayer` 1.11.0 in a `MediaSessionService`, with one `MediaSession` on it |
| Queue | Every song is one item of that player's playlist; the app's queue logic drives it through `PlayerPort` / `Media3Port` |
| Gapless | The player joins items without a gap when the file carries gapless data; `PreloadConfiguration` loads the first 10 s of the next item (PR #666). The owner confirmed it is seamless |
| Audio path | One `DefaultAudioSink` carrying one `EqAudioProcessor` |
| Volume | `PlayerPort.setVolume(Float)` exists; system volume is separate |
| Scrobbling | `ScrobbleTracker` counts media time played for one `Play` (one run of one queue entry) from the player's position; now-playing is sent once per play |
| Audio focus | Held by the single ExoPlayer (`handleAudioFocus = true`) |
| Settings storage | `PrefsPlayerSettings` (ordinary preferences, per device) |
| Built-in crossfade | None known in Media3 1.11.0 (not re-checked against the library source; X1 must confirm) |

Consequences: ExoPlayer plays one item at a time on one audio track, so two songs can never sound together inside one player. A crossfade needs a second audio path alive during the overlap, and everything that assumes one player (the session, the timeline, the scrobbler, the equalizer, audio focus) has to be kept honest about it.

## 3. Binding rules (inherited)

1. `ANDROID_CLIENT_CONTRACT.md` section 2 applies: 48dp targets, TalkBack labels, honest states not by colour alone, **no third-party SDKs or analytics**, no tracking.
2. Every screen goes through `/mobile-design` and is recorded in `android/DESIGN.md` (rule 9).
3. Agents run focused tests only; the owner runs the full suite and CI runs it on the PR head.
4. No new permission is added. No new dependency beyond the Media3 artifacts already used.
5. **Gapless playback, scrobbling counts, the equalizer and the queue must not change** for anyone who leaves crossfade off. Off is today's behaviour, byte for byte in the player path (section 5.4).
6. Nothing is claimed as verified on a device until the owner has tested it.
7. In all documentation and communications, the person directing the project is "the owner".
8. A fault in crossfade must never stop the music (section 8).

## 4. Approach

Four ways to get a crossfade were considered.

| | A. Two players, service-level handover (proposed) | B. One player plus a short helper player for the overlap | C. Fade out then fade in at the join ("dip") | D. Audio-level mixing of two decoded streams |
|---|---|---|---|---|
| How | Two `ExoPlayer` instances; the service owns the queue and moves it from one player to the other. The session is given a wrapper `Player` that presents one queue and one position | The main player keeps the whole playlist. Shortly before the end, a helper `ExoPlayer` prepares the next song and fades in while the main one fades out; at the end the main player is moved to the next item | The one player ramps its volume down over the last seconds and up over the first seconds of the next item | A custom renderer/sink that mixes two decoder outputs into one `AudioTrack` |
| Real overlap of two songs | Yes | Yes | No: there is a dip in the middle, never both at once | Yes |
| Keeps gapless when crossfade is off or skipped | Needs care: both players must still join without a gap when the rule in 5.3 says "no crossfade". Not free | Yes: the main player is untouched | Loses it: the volume dip makes any join audible | Yes, in principle |
| Session, notification, lock screen | The wrapper `Player` must forward everything correctly (timeline, position, commands, errors). Largest surface | Unchanged: the session sits on the main player | Unchanged | Unchanged |
| The hand-over moment | Clean: the second player is already playing | Risky: moving the main player to the next item at the helper's position can glitch or re-buffer | None | None |
| Equalizer | Two sinks, so two processors on the same setting | Two sinks, same | One, unchanged | One, unchanged |
| Cost to build | High | Medium to high, and the hand-over glitch risk is not known to be solvable | Low | Very high; touches ExoPlayer internals that are not stable API |

**Proposed: A, behind a spike (phase X1) that decides it.** A is the only design that gives a true, clean overlap without private ExoPlayer internals. B is the cheaper-looking route but its hand-over can glitch; X1 builds the smallest version of A and of B on the owner's phone and the owner picks by ear and by the checks in section 9 before anything is built for real. C is the honest fallback if A and B both fail: a "fade between songs" that is not a crossfade, called by that name in the screen, and the owner decides whether it is worth shipping. D is rejected: it depends on unstable ExoPlayer internals.

Rules for A (to be confirmed or changed by X1):
- **One owner of the queue.** The existing queue logic (`PlayQueue`, `PlayerController`, `QueueStorage`) stays the single source of truth for the order. The two players each hold the item they are playing and, when it exists, the one they are about to play, and nothing else; the queue is not copied into two playlists.
- **One session, one face.** A wrapper `Player` (a `ForwardingPlayer` over the active player, or `SimpleBasePlayer` if X1 shows forwarding is not enough) is what `MediaSession` sees. Controllers (the app, the notification, the lock screen, Bluetooth) never learn there are two players. Position, duration, the current item and the play state are always those of the **incoming** song from the moment the overlap starts.
- **Audio focus** is taken once. Only the active player holds it; the second player is built with focus handling off and gets the same attributes. When focus is lost, both pause together.
- **Volumes** are set only through `Player.setVolume` on each player (never the system stream). Between songs both are at full volume on the active one; system volume is not touched.
- **Release:** both players are released exactly once with the service (`ReleaseGuard` accounting extended).
- **Failure:** if the second player cannot be created or fails to prepare in time, that join plays as it does today (section 8).

## 5. The crossfade

### 5.1 When it starts
A crossfade starts when the current song has `L` seconds left, where `L` is the length setting for that join (5.2), **provided all of these hold**:
- crossfade is on;
- the change is an automatic one (the song reaching its end), not a manual skip, a seek, a queue tap or a restart;
- the next song exists in the queue, after shuffle and repeat are applied, and is not the same queue entry (so repeat-one never crossfades into itself);
- both songs have a known duration of at least `3 × L` (a very short song gets a shorter fade, see 5.2; a stream whose duration is unknown, for example some converted streams, gets no crossfade);
- the next song is prepared (at least its first `L + 2` seconds are buffered) when the fade is due. If it is not, the join is played as today and the fade is skipped for that join, without delay or a pause.
- the join is not excluded by the album rule (5.3).

### 5.2 The fade
- **Length:** the owner's setting, 1 to 12 seconds in 1-second steps; proposed default **5 s**. At a join the length actually used is `min(setting, shorter song's duration ÷ 3)`, never below 1 s; if that is under 1 s there is no fade.
- **Curve:** equal-power. With progress `t` from 0 to 1, the outgoing gain is `cos(t·π/2)` and the incoming gain is `sin(t·π/2)`, so the sum of their squares is 1 and the loudness does not dip in the middle for unrelated songs. The curve is computed in plain Kotlin and the gain is applied through the player's volume, updated at least every 20 ms (a ramp, not steps).
- **Timing:** the incoming song starts at its own position 0 when the fade starts. The outgoing song ends exactly when the fade ends.
- **No time is added or removed** from either song: the album is not shifted, and the total play time of the queue is shorter by the overlap, which is what a crossfade is.

### 5.3 The album rule (keeps gapless albums gapless)
A live album, a classical work or a continuous mix is meant to join without any change in level. So:
- **"Skip crossfade between songs of the same album when they are consecutive tracks" is on by default.** Two consecutive tracks of one album (same album id, next track number, or the next in the album's order) join as today, gapless. Switch it off to crossfade everywhere.
- Different albums, shuffle and mixed queues crossfade.
- The rule uses data already in the queue item; it adds no server call.

### 5.4 Off means off
With crossfade off, the second player is **not created**, no fade logic runs, and the service behaves exactly as on `main` today (one player, gapless, the same preload). Turning crossfade on or off while playing takes effect at the next join; it never changes the song that is playing.

## 6. Settings and storage

- `PlayerSettings` gains `crossfadeEnabled` (default **off**), `crossfadeSeconds` (default 5, clamped 1 to 12 on read) and `crossfadeSkipSameAlbum` (default on). Stored in the existing per-device preferences; a corrupt or out-of-range value falls back to the default without a crash.
- Sign-out does **not** clear them (like the equalizer; a property of the phone's listening, not of the account). Stated here so it is not "fixed" later by mistake.
- The service reads the settings at start and listens for changes, so a change applies at the next join and is the same with the app closed.

## 7. The screen

- **Settings, Playback section:** a row "Crossfade" that reads "Off" or "5 seconds". It opens a small page or sheet.
- On that page: a switch "Crossfade"; a length control with **minus and plus buttons of at least 48dp** (1 s per press) and a slider as an extra, never the only way; the value in words ("5 seconds"); the switch "Keep albums gapless" with one line of help ("Songs that follow each other on one album play without a fade"); and one line saying what it does *not* do ("Skipping a song yourself is not faded").
- When the quality is below Original, one line: "Converted streams can be crossfaded, but a song whose length the server cannot tell is played without a fade." (Section 8.)
- When crossfade is on, the Now Playing sheet shows the words "Crossfade: 5 s" in the same place and manner as "EQ: <preset>", so the state is visible without opening the screen. The mini-player and the notification show nothing extra.
- During an overlap the sheet shows the **incoming** song (title, art, position) from the start of the overlap; there is no animation of two songs (reduced motion is respected: the change of title is instant).
- States: off (length controls shown but marked unavailable, not hidden), on, and the quality line.

Accessibility: the switch and the keep-gapless switch announce their state; the length control reads "Crossfade length, 5 seconds" with increase and decrease actions; the page scrolls at 200% text and in landscape; the buttons are named.

## 8. Interaction with the rest of the player

- **Manual skip, previous, queue tap, seek:** instant, as today. If one of these happens **during** an overlap, the overlap ends at once: the incoming song becomes the current one at full volume (a skip then acts on it), and the outgoing one stops. No second fade is started.
- **Pause and resume during an overlap:** both players pause together and resume together, with the fade at the same point. A long pause does not skip or restart the fade.
- **Seek during the incoming song's first seconds:** treated as a seek; the overlap ends at once (above).
- **Scrobbling:** the current play changes at the **start of the overlap** (the incoming song is the current one from then on, matching what the screen shows). Now-playing is sent for the incoming song when it starts; the outgoing song's play stops at that moment and keeps the time it had already earned. A song that was heard to its end minus the fade length still reaches its scrobble point first in practice, because the threshold is half the song or four minutes. The tracker's rule "a jump is never credited" holds. **A test must show that a play is scrobbled once and now-playing sent once at every join, crossfaded or not.**
- **Equalizer:** each player has its own `EqAudioProcessor` on the **same** `EqSettings`, so the curve is identical on both songs and a change while playing applies to both. The status line ("Not applied to this song") follows the incoming song. The EQ contract's rules (bit-exact bypass when flat, no click on a change) are unchanged.
- **Streaming quality:** unaffected. A converted stream usually has no gapless data, so crossfading it is audibly the better join; a song whose duration the server does not give gets no fade (5.1).
- **Failure:** if the second player throws, fails to prepare, or the fade logic faults, the service releases the second path, the current song plays on at full volume and the next song starts the way it does today. The Now Playing sheet shows nothing extra for that (an error here is not the owner's to act on), but the cause is logged without any credential. A failure of the incoming song after the overlap has begun is handled by the existing failure path (`PlaybackFailure`) as for any song.
- **Audio focus loss, phone calls, headphones unplugged, Bluetooth disconnect:** behave as today for the pair: both pause (or stop) together.
- **Volume:** follows the system, as today. The fade is relative and never changes the system stream.
- **Sleep or Doze, screen off:** the fade runs in the service; the timer must be a Handler or `Player.createMessage` on the player's own looper, not a UI timer (X3 test on the phone).
- **Bandwidth and battery:** during the overlap two streams are read and two decoders run; the preload (`PreloadConfiguration`) is raised to at least `L + 2` seconds for the next item. This costs extra data on mobile data and a little CPU for `L` seconds per join, only with crossfade on.

## 9. Phases

Each phase is one focused PR from `main`, with tests, no full-suite run by agents (the owner runs it; CI runs it on the PR head), and the `/mobile-design` review recorded for UI. X0 is documentation only and goes direct to `main`.

**X0: documents.** This contract approved by the owner. Then `D-021` in `DECISIONS.md`, `XFADE-01..` rows in `REQUIREMENTS.md`, a Crossfade section in `TEST_PLAN.md`, and a pointer in `ANDROID_PLAYER_CONTRACT.md` and `ACTIVE_WORK.md`.

**X1: the spike (decides the architecture).** A throwaway, clearly marked branch that is **not merged**. It builds the smallest working A and the smallest working B (section 4), each as a hidden switch, and a fixed test: two real songs from different albums, a 5 s fade, repeated. It measures and reports: whether the hand-over is clean, whether the session and notification stayed correct, the position a controller saw, memory and CPU while overlapping, and anything that broke. Exit: a written result in `android/DESIGN.md` and the owner chooses A, B or C (or stops). **No product code of X2 onward is written before this.**

**X2: the pure logic.** In plain Kotlin with no Android types, in `player/crossfade/`:
- `FadeCurve`: equal-power gains from progress; the ramp for a given length and update rate.
- `CrossfadePlanner`: given the two songs (duration, album, track), the setting, shuffle and repeat, and whether the change is automatic, returns "no fade" with the reason or "fade of N seconds starting at T". Contains rules 5.1 to 5.3.
- Tests: gains at 0, 0.5 and 1; sum of squares 1 across the ramp; monotonic, no step larger than a set bound per update; every refusal in 5.1 and 5.3 (each reason has a test); a very short song gets a shorter fade and a 2-second song none; repeat-one, repeat-all at the end of the queue, shuffle, an unknown duration, the album rule on and off; clamping of a hostile length (negative, zero, NaN as text, 10 000).

**X3: the service.** The chosen architecture from X1, wired behind the settings from X4's storage part (so it is switchable). `ReleaseGuard` accounting extended. Tests: with crossfade off, the second path is never created; a join that the planner refuses plays as before; a thrown error in the second path becomes "play as today", not a crash; both players are released exactly once; a manual skip during the overlap snaps; the scrobble and now-playing counts in the section 8 test; the equalizer's two processors follow one setting. Anything that needs a real `ExoPlayer` or `AudioTrack` is a device check, not a unit test (the project has no Robolectric), and is said so.

**X4: settings and screen.** `PlayerSettings` additions (round trip, clamping, corrupt data, defaults), the Settings row, the page, the Now Playing indicator, every state of section 7. Tests: clamping and text for the length ("1 second", "5 seconds"), the TalkBack text, the quality line shown only below Original. Manual device checks in section 10.

**X5: hardening and device run** on the owner's phone: section 10. R8 rules checked on the minified release build.

## 10. Verification

- Unit tests as above; `./gradlew testDebugUnitTest --tests 'app.discair.player.*' assembleDebug lintDebug minifyReleaseWithR8` on JDK 17 per phase (the system default JDK on the owner's Mac fails, set `JAVA_HOME` to the Homebrew `openjdk@17`).
- On the owner's phone over Tailscale. **Nothing is claimed until the owner has tested it.** Items the assistant can drive over adb (the page, the persisted setting, no crash, no underrun) are recorded as that and not as "heard".

**A. Basics**
1. Settings, Playback: a "Crossfade" row reads "Off". Open it: the length controls are marked unavailable, with the reason.
2. Switch it on at 5 s. Let a song end between two different albums: do you hear the two overlap, with no jump in loudness in the middle?
3. Try 1 s, 5 s and 12 s: the length matches what you chose by ear.
4. Switch it off: the next join is the plain join of today.

**B. Rules**
5. Two consecutive tracks of one album with "Keep albums gapless" on: no fade, still seamless (a live album is the best test).
6. The same with the switch off: they fade.
7. Shuffle, repeat all at the end of the queue, repeat one (no fade into itself).
8. A very short song (under 30 s) and a song just over `3 × L`: shorter fade, no glitch.
9. A song whose join is not ready (a slow link, Airplane-mode on a stream not yet buffered): the join is played as today, with no extra pause.

**C. Control during a fade**
10. Press next during an overlap: the incoming song is at full volume at once, and the next press goes to the song after it.
11. Press previous, tap a queue row, and drag the seek bar during an overlap: each ends the overlap and does what it normally does.
12. Pause in the middle of an overlap, wait a minute, resume: both come back together at the same point.
13. The notification and lock screen show the incoming song from the start of the overlap, and their buttons work during it.

**D. With the rest of the app**
14. Equalizer on (a strong preset): both songs are shaped the same way, and the fade makes no click.
15. Streaming quality 128 kbps: crossfades; no extra gap.
16. Scrobbling: after a few crossfaded joins, Navidrome shows each song scrobbled once, in order, and now-playing changed once per join.
17. Phone call in the middle of an overlap; headphones unplugged; Bluetooth connect and disconnect: nothing breaks; both pause together.
18. Screen off for a whole album's worth of joins: they still crossfade.
19. Close the app from recent apps and reopen: the settings are kept, the queue is back, paused.
20. Sign out and in: the crossfade setting is **still there** (by design). Does that feel right?

**E. Accessibility and cost**
21. TalkBack: the switches say on or off, the length reads "Crossfade length, 5 seconds", increase and decrease change it by 1 s.
22. 200% text: the page stays usable.
23. Battery: a long listen (an hour or more) with crossfade on compared with off, if you can. Record the percentage drop for each, and the data used on mobile data if that matters.

**What would send this back to the code:** a click, jump in loudness or dropout at a join; a gap where the album rule says gapless; a controller (notification, lock screen) showing the wrong song or position; a double or missing scrobble; the music stopping because of a fault in the second path; or a visible battery cost. The fallback is C (section 4), named honestly in the screen, or leaving crossfade out.

## 11. Decisions

Proposed defaults. The owner started X0 without changing any of them (2026-11-01), so each applies as written unless the owner changes it before the phase it affects.

1. **Architecture: A (two players), B (a helper player) or C (a dip), decided by the X1 spike?** Proposed: spike both A and B; build whichever sounds clean and keeps the session honest. If neither does, ship C under an honest name or stop.
2. **Default length and range?** Proposed: default 5 s, range 1 to 12 s in 1 s steps. A longer range (up to 20 s) is a later change, not a risk.
3. **Do manual skips crossfade?** Proposed: **no** in version 1. A short fade on a tap of "next" is a common feature but adds the hardest cases (a skip storm, a skip during a fade); it can be a later contract.
4. **Keep same-album consecutive tracks gapless by default?** Proposed: yes (5.3).
5. **Default on or off?** Proposed: off. The owner's library plays untouched until crossfade is switched on.
6. **Curve?** Proposed: equal-power for all joins. A linear curve is not offered: it dips in loudness for unrelated songs.
7. **Keep the setting after sign-out?** Proposed: yes (section 6).
8. **Scrobble identity during the overlap?** Proposed: the incoming song is current from the start of the overlap (section 8). The alternative (the incoming song becomes current at the midpoint of the fade) is rejected because the screen would then disagree with the notification for several seconds.
9. **Extra data on mobile data?** Proposed: accept the extra preload of `L + 2` seconds only when crossfade is on; no separate "Wi-Fi only" switch in version 1.

## 12. Risks

1. **The wrapper `Player` (architecture A)** is the largest risk: a wrong timeline, position or command state would show in the notification and lock screen and could break scrobbling and the queue. Mitigation: the X1 spike, tests of the wrapper's forwarding, and the device checks 10 to 13 and 16.
2. **Gapless regression:** crossfade must not touch the join of two consecutive album tracks or the off path. Mitigation: the album rule, "off means off" (5.4), a planner test per refusal, and device check 5.
3. **Audio-focus and two sinks:** two `AudioTrack`s and two focus holders could pause each other or fight. Mitigation: one focus holder (section 4), checked on a call, Bluetooth and another app's playback in X5.
4. **Timing drift:** the fade must start `L` seconds before the end of a song of any length and must survive Doze and a screen-off service. Mitigation: timer on the player's own looper, and check 18.
5. **Memory, CPU, data:** two decoders and two streams during the overlap, and a longer preload. Small and temporary, unmeasured; battery check 23.
6. **Hand-over glitch (architecture B):** the reason B is only a candidate.
7. **Loudness differences between songs:** crossfading a quiet song into a loud one sounds uneven; this is not fixed here (no normalisation, section 1) and should not be blamed on the fade.
8. **Duration data:** a stream with no known length gets no fade; a wrong duration from the server could start the fade early or late. The planner prefers the player's own duration when it is known, as the scrobbler does.
9. **Scope creep:** crossfade on manual skips, auto-mix points, silence trimming, normalisation and a "gapless vs crossfade per album" memory are tempting neighbours; each is out of scope and needs its own contract.
10. **Release build:** Media3 classes under R8; checked on the minified release build in X5.
