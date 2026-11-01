# Android equalizer contract (Discair)

Status: **approved by the owner on 2026-11-01: every proposed default in section 11 is accepted (answers 1 to 8). Phase E0 (documents) is done and E1 (the filter) and E2 (settings and service wiring) are built and unit-tested; E3 and E4 are not started.** This is the "EQ" item that [`ANDROID_PLAYER_CONTRACT.md`](ANDROID_PLAYER_CONTRACT.md) section 6 and `ACTIVE_WORK.md` 2g left for its own contract (proposed `D-020`). It goes through a PR, as the Android contracts do.

## 1. Purpose and scope

Let the owner shape the sound of what the Android player plays: a graphic equalizer with a few presets, one switch to turn it off, and a setting that persists on the device.

In scope:
- A 10-band graphic equalizer applied to everything the player plays, in the service, so it works with the screen off, from the notification and over Bluetooth.
- A pre-gain (headroom) control and automatic protection against clipping.
- Built-in presets plus one "Custom" slot that keeps the owner's own band settings.
- An on/off switch with a true bypass.
- An EQ screen reachable from Settings and from the Now Playing sheet.
- Per-device storage; the setting survives restarts and sign-out (it is not account data).

Out of scope (each would need its own contract):
- The web UI. No Librarian change (D-016 is untouched). The web stays "not a player".
- Crossfade, bass boost, virtualizer, loudness enhancer, reverb, ReplayGain or volume normalisation, per-song or per-album EQ, per-output-device profiles (headphones vs speaker), saving or sharing named presets, importing AutoEQ profiles.
- System-wide EQ for other apps.
- Radio.

## 2. Facts about the current player

From `PlaybackService.kt` and `build.gradle.kts` on `main`:

| Fact | Value |
|---|---|
| Engine | Media3 `ExoPlayer` 1.11.0 in a `MediaSessionService`, built with `ExoPlayer.Builder(this)` and no custom renderers factory |
| `minSdk` / `targetSdk` | 33 / 33 |
| Audio path | ExoPlayer decodes to PCM and writes it to `AudioTrack` through its default `DefaultAudioSink` |
| Gapless | Songs are one playlist in one player; the next 10 s are preloaded (PR #666) |
| Formats | Original file by default (FLAC, MP3, M4A, Opus); a lower quality is converted by Navidrome |
| Settings storage | `PrefsPlayerSettings` (ordinary SharedPreferences, per device) |

Consequences: the EQ must live in the service process, must not break gapless joins, and must not depend on the file format.

## 3. Binding rules (inherited)

1. `ANDROID_CLIENT_CONTRACT.md` section 2 applies: 48dp targets, TalkBack labels, honest states not by colour alone, **no third-party SDKs or analytics**, no tracking.
2. Every screen goes through `/mobile-design` and is recorded in `android/DESIGN.md` (rule 9).
3. Agents run focused tests only; the owner runs the full suite and CI runs it on the PR head.
4. No new permission is added by this feature. Specifically, no `RECORD_AUDIO` (see section 4).
5. Nothing is claimed as verified on a device until the owner has tested it.
6. In all documentation and communications, the person directing the project is "the owner".

## 4. Approach

Two ways to build an EQ on Android were considered.

| | A. Own audio processor (proposed) | B. Platform `android.media.audiofx.Equalizer` |
|---|---|---|
| How | A Media3 `AudioProcessor` in the ExoPlayer audio sink: ten peaking biquad filters on the PCM before it reaches `AudioTrack` | The system effect attached to the player's audio session id |
| Bands | Fixed by the app: the same ten on every phone | Chosen by the phone's maker (often 5, ranges and centre frequencies differ) |
| Predictability | Same sound on every device and output; response can be computed and unit-tested in plain Kotlin | Varies by phone; some vendors ship broken or no-op effects |
| Clipping | The app controls pre-gain and can add a limiter | The effect can clip, and the app cannot see the result |
| Sessions | None to track | Must be re-attached when the audio session id changes (it can change with offload and when the player is rebuilt); must be released with the player |
| Permissions / SDKs | None | None (attaching to your own session needs no `RECORD_AUDIO`) |
| CPU | Small but real: 10 filters × samples. Estimated well under 1% of one core at 44.1/48 kHz stereo; not measured | Done by the platform, often in a DSP |
| Offload | Software processing disables ExoPlayer's audio offload while the EQ is on; offload is not used today | Compatible with offload |
| Cost to build | More code (filter maths, format handling) | Less code |

**Proposed: A.** The deciding reasons are the project's own rules: the behaviour is the same on the owner's phone and any other, and it is testable without a device (the project already tests everything it can in plain Kotlin). B is the fallback if A proves too heavy on the owner's phone (section 11, question 1).

Rules for A:
- The processor is installed through a custom `AudioSink`/`DefaultAudioSink.Builder.setAudioProcessors(...)` in the `ExoPlayer.Builder` `RenderersFactory`, in `PlaybackService`. Nothing else in the player changes.
- It accepts 16-bit PCM and float PCM (ExoPlayer's `DefaultAudioSink` can output float for high-resolution files; the processor requests float when available so that 24-bit FLAC is not cut to 16 bits). Any other format is passed through untouched and the EQ shows "Not applied to this song".
- Sample rate and channel count are read from the processor's input format; coefficients are recomputed on a format change. Mono, stereo, and more than two channels (each channel filtered with the same curve) are handled.
- Gapless is preserved: filter state is **not** reset at a song change (that would click), and the processor adds no delay line, so no samples are added or removed at the join. A format change at a join flushes state as ExoPlayer requires.
- Changing a band while playing must not click: coefficients are interpolated over about 20 ms.

## 5. The equalizer

### 5.1 Bands
Ten peaking filters at 31, 62, 125, 250, 500, 1000, 2000, 4000, 8000 and 16000 Hz, constant Q of about 1.41 (one octave apart). Each band is adjustable from −12 dB to +12 dB in 0.5 dB steps (default 0). Bands above 0.45 × the sample rate are bypassed for that stream.

### 5.2 Headroom and clipping
- **Pre-gain** is applied before the filters: by default automatic, equal to the negative of the largest positive band gain (so boosting 6 dB lowers the signal 6 dB first). The owner can switch automatic off and set it by hand from −12 to 0 dB.
- A soft limiter follows the last filter so a manual setting cannot produce harsh digital clipping. It is a safety net, not a feature, and is not shown as a control.
- With every band at 0 dB and pre-gain at 0 dB the processor is bit-exact bypass (it returns the input buffer unchanged).

### 5.3 Presets
Built in and fixed: **Flat, Bass boost, Bass reduce, Treble boost, Vocal, Rock, Classical, Electronic, Late night** (gentle low and high cut at low listening levels). The exact numbers are fixed in code and recorded in `android/DESIGN.md` when built. Choosing a preset sets the ten bands. Moving any band afterwards switches the selection to **Custom**, which holds the last hand-made curve; presets are never overwritten.

### 5.4 Switch and reset
- **Equalizer on/off:** off is a true bypass (section 5.2), and the settings are kept. Default: off.
- **Reset** sets Flat and clears Custom, after a confirmation.

## 6. Settings and storage

- A new `EqualizerSettings` next to `PlayerSettings`, in ordinary preferences: `enabled`, `presetId`, ten band gains, `preGainAuto`, `preGainDb`, and a version number. Values are clamped on read; a corrupt or unknown value falls back to Flat and off, without a crash.
- The service reads the settings at start and listens for changes (the controller writes, the service applies), so a change while playing takes effect at once and is the same when the app is closed.
- Sign-out does **not** clear the EQ (it is a property of the phone's listening, not of the account). This differs from the queue and the lyrics cache and is stated here so it is not "fixed" later by mistake.

## 7. The screen

An **Equalizer** screen, opened from Settings ("Playback" section) and from a button on the Now Playing sheet.

- A switch "Equalizer" at the top, with its state in words.
- A preset chooser as a labelled list or dropdown showing the selected preset by name.
- Ten vertical sliders with the frequency under each ("31 Hz" … "16 kHz") and the value in dB above ("+3.5 dB"). Vertical sliders are hard to use with a screen reader and a thumb, so each band also has **minus and plus buttons of at least 48dp** that move it by 0.5 dB; no gesture is the only way to change a value.
- Pre-gain row: "Automatic" switch and, when off, a slider.
- A line of text when the current song cannot be processed ("Not applied to this song").
- Reset button.
- When the EQ is on, the Now Playing sheet shows the words "EQ: <preset>" so the state is visible without opening the screen.
- States: off (controls shown but marked unavailable, not hidden), on, and the not-applied line.

Accessibility: TalkBack reads each band as "62 hertz, plus 3.5 decibels" with increase and decrease actions; the screen scrolls in portrait, landscape and at 200% text; the switch and presets announce their state; reduced motion removes slider animations. Landscape lays the bands in one row.

## 8. Interaction with the rest of the player

- **Scrobbling, queue, seek, gapless, notification, lock screen:** unchanged. The EQ sits only in the audio sink.
- **Streaming quality:** unaffected. Lower qualities are converted by Navidrome; the EQ is applied after decoding on the phone.
- **Failure:** if the processor throws or cannot be configured, the sink falls back to bypass for that song, playback continues, and the EQ screen shows "Equalizer unavailable for this song". A fault in the EQ must never stop the music.
- **Volume:** follows the system, as today. The EQ is not a volume control.
- **Bluetooth, wired and speaker outputs:** one curve for all outputs in version 1 (section 11, question 4).

## 9. Phases

Each phase is one focused PR from `main`, with tests, no full-suite run by agents (the owner runs it; CI runs it on the PR head), and the `/mobile-design` review recorded for UI.

**E0: documents.** This contract approved by the owner. Then `D-020` in `DECISIONS.md`, `EQ-01..` rows in `REQUIREMENTS.md`, an Equalizer section in `TEST_PLAN.md`, and a pointer in `ANDROID_PLAYER_CONTRACT.md`. Direct to `main` (documentation only).

**E1: the filter.** Pure Kotlin `Biquad` and `EqCurve`/`EqProcessor` logic with no Android types: peaking coefficients, cascade, pre-gain, limiter, and the Media3 `AudioProcessor` adapter around it. Tests:
- Frequency response of each band at several sample rates matches the design within 0.1 dB at the centre; a flat curve is bit-exact bypass.
- Pre-gain: automatic value for several curves; a full-scale sine through +12 dB on one band does not exceed full scale after the limiter.
- 16-bit and float input; mono, stereo and six channels; bands above Nyquist are bypassed; a format change recomputes coefficients.
- No samples are added or removed over a long buffer and across a simulated song change.
- Coefficient change is smooth: no step larger than a set bound at the change point.
- No allocation in the per-buffer path beyond the output buffer (checked by reuse, not by a profiler).

**E2: settings and service wiring.** `EqualizerSettings` (clamping, corrupt data, defaults), the sink in `PlaybackService`, live apply, and fallback to bypass on failure. Tests: settings round trip and hostile values; the sink factory chooses the processor and passes unknown formats through; a thrown error becomes bypass, not a crash; the processor is released with the player (extend `ReleaseGuard` accounting).

**E3: screen.** Settings entry, the Equalizer screen, the Now Playing indicator, every state of section 7. Tests: preset-to-bands mapping and the move-to-Custom rule; the text for dB values and for TalkBack; the manual device list in section 10.

**E4: hardening and device run** on the owner's phone: see section 10. R8 rules checked on the minified release build.

## 10. Verification

- Unit tests as above; `./gradlew testDebugUnitTest assembleDebug lintDebug assembleRelease` on JDK 17 per phase (the system default JDK on the owner's Mac fails, set `JAVA_HOME` to the Homebrew `openjdk@17`).
- On the owner's phone over Tailscale: a bass boost on a known track is audible and Flat sounds identical to EQ off; a +12 dB band with automatic pre-gain does not distort; toggling the switch and moving a band while playing makes no click; the setting survives closing the app and a restart; gapless is still seamless on a live album with the EQ on; a FLAC (including 24-bit if one exists), an MP3, an M4A and an Opus song all work; quality 128 kbps works; Bluetooth headphones and the speaker; headset buttons, lock-screen controls and a phone call interrupting playback still behave; TalkBack through the screen, 200% text and landscape; a battery check over a long listen with the EQ on compared with off; sign-out does not clear the setting.
- Nothing is claimed as verified on a device until the owner has tested it.

## 11. Decisions

The owner approved all proposed answers on 2026-11-01. They are the decisions of record; a change needs the owner's approval before the phase it affects.

1. **Own processor or the platform Equalizer?** Proposed: own processor (section 4); fall back to the platform effect only if the owner's phone shows a CPU or battery problem.
2. **Ten bands, ±12 dB?** Proposed: yes. Fewer bands (five) are simpler to use on a phone; ten gives finer control. The owner may prefer five.
3. **Preset list (section 5.3)?** Proposed: the nine named there. Add, remove or rename before E3.
4. **One curve for all outputs, or a separate curve for headphones vs speaker?** Proposed: one curve in version 1. Per-output profiles are a later contract.
5. **Default on or off?** Proposed: off. The owner's library plays untouched until the EQ is switched on.
6. **Keep EQ after sign-out?** Proposed: yes (section 6).
7. **Limiter and automatic pre-gain on by default?** Proposed: yes, since a boosted EQ without headroom clips and sounds worse than no EQ.
8. **Allow importing curves (for example AutoEQ files)?** Proposed: no. It would add file parsing and a trust surface for little gain now.

## 12. Risks

1. **CPU and battery** of software filtering on a phone that today decodes only: small by estimate, unmeasured; mitigated by the on/off bypass and the battery check in section 10.
2. **Audio quality bugs** (clicks, clipping, wrong curve): mitigated by tests against computed responses, the 20 ms coefficient interpolation, the limiter and a listening check.
3. **Gapless regression:** the processor must not alter sample counts; covered by a test and the live-album check.
4. **High-resolution audio:** requesting float output changes what `AudioTrack` receives; devices differ. Mitigation: fall back to 16-bit and say so, and test a 24-bit file on the phone.
5. **Offload:** enabling the EQ disables any future audio offload; accepted, because offload is not used.
6. **Scope creep:** crossfade, bass boost and normalisation are tempting neighbours; each is out of scope and needs its own contract.
7. **Release build:** Media3 audio classes under R8; checked on the minified release build in E4.

## 13. Phase E1 status

**Built and unit-tested; not wired into the player and not run on a device.** E0 was merged in PR #673. New in `android/app/src/main/kotlin/app/discair/player/eq/`:
- `EqConfig.kt`: the setting as plain data (enabled, ten band gains, automatic or manual pre-gain). Gains are clamped to ±12 dB and rounded to 0.5 dB; NaN and missing values become 0; the manual pre-gain is limited to 0 or below. `isBypass()` is true when off or flat.
- `EqEngine.kt`: RBJ peaking biquads (Q 1.41) at the ten centres, bands above 0.45 × the sample rate bypassed, pre-gain, a soft limiter (transparent up to 0.9, never above 1.0), and a 20 ms linear ramp of coefficients and gain on every change. Filter state is kept across buffers and settings, never reset by the engine; the engine returns exactly the samples it is given.
- `EqAudioProcessor.kt`: the Media3 `AudioProcessor`. It accepts 16-bit and float PCM with 1 to 8 channels, leaves any other format inactive (pass-through), keeps the input encoding, copies bytes unchanged in bypass, and falls back to a plain copy for the rest of the stream if the engine throws. A flush (seek, format change) starts a fresh engine.

Run: `./gradlew testDebugUnitTest --tests 'app.discair.player.eq.*' assembleDebug lintDebug` on JDK 17: 22 tests, 0 failures (16 engine, 6 processor); debug build and lint passed. The full suite was not run (the owner runs it; CI runs it on the PR head).

Not done or not verified:
- Nothing installs the processor in `PlaybackService` yet (E2). The release build and R8 were not run.
- **Deviation from section 4:** the contract says the processor requests float output so 24-bit files are not cut to 16 bits. E1 keeps the input encoding instead (16-bit in, 16-bit out; float in, float out) and does not change what `DefaultAudioSink` is asked for. Whether to request float is decided in E2, with the device check of a 24-bit FLAC.
- The CPU cost is unmeasured. The 20 ms ramp costs per-sample coefficient updates only while a change is in progress.
- No listening test; the tests check computed responses, levels, continuity and lengths, not how it sounds.
- The 250 ms-style "no allocation" rule is met by reusing one scratch array, but this is not measured; the output buffer is allocated by `BaseAudioProcessor` per call.

## 14. Phase E2 status

**Built and unit-tested; the equalizer is now installed in the player but has no screen, so it is always off. Not run on a device.** E1 was merged in PR #674. New or changed:
- `eq/EqSettings.kt`: `EqSettings` (the audio setting plus a validated preset id, default `flat`), the `EqSettingsStore` interface, `PrefsEqSettingsStore` (ordinary preferences file `discair_eq`; version 1; the ten gains in one string so a change is one write; clamped on read; an unknown version or an unreadable value gives Flat and off) and `MemoryEqSettingsStore` for tests. `EqBinding` applies the saved setting to a target at once and after every save, swallows a target's error, and removes its listener on `close()`.
- `AppContainer.eqSettings`: the store. Sign-out does not touch it (contract 6).
- `PlaybackService`: the player is built with a `DefaultRenderersFactory` whose audio sink carries the `EqAudioProcessor`; the binding is closed in the existing `ReleaseGuard`, so release happens once with the player.
- `EqAudioProcessor` now implements `EqTarget`.

Decision recorded for the E1 deviation: **float output is not requested in version 1.** The sink keeps ExoPlayer's default (`enableFloatOutput` as ExoPlayer passes it), and the processor keeps the input encoding. Revisit only if the device check finds a 24-bit file being cut.

Run: `./gradlew testDebugUnitTest --tests 'app.discair.player.eq.*' assembleDebug lintDebug minifyReleaseWithR8` on JDK 17: 29 tests, 0 failures (7 new settings and binding tests); debug build, lint and R8 passed. The full suite and the signed release build were not run.

Not done or not verified:
- The sink wiring in `PlaybackService` is covered only by compiling and R8; no unit test builds a `DefaultAudioSink` (it needs an Android context). Whether audio actually flows through the processor is unconfirmed until a device run.
- `PrefsEqSettingsStore` is tested through the in-memory store's rules only; the SharedPreferences class itself has no test (no Robolectric in the project).
- Nothing sets the settings yet (E3), so nothing can turn the equalizer on.
- The "Not applied to this song" and fault states exist on the processor (`applies`, `hasFaulted`) but are not surfaced.
