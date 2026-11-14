# Discair client efficiency plan

**Status:** plan only; not an implementation authorization. Each step needs the owner's go-ahead.
**Revision:** 2 (2026-11-11). Replaces the first source survey of the same date.
**Source reviewed:** GitHub `main` at `88a8f70e1b33f31b966004ede74467d2abd2d96f`. The macOS and Android client sources are unchanged since the first survey's baseline (`ce01596f`).
**Scope:** macOS and Android clients: CPU, memory, rendering, playback buffers, energy and start-up.
**Progress:** P0-1 done (commit `84d3d5b4`, direct to `main` on the owner's instruction): protocol and empty results tables in [`client_efficiency_results.md`](client_efficiency_results.md), per-client cheap-tool scripts in `scripts/perf/`. P0-2 in progress: macOS S2 to S7 measured (PRs #1066, #1067) and S1 and S8 to S10 measured on a short, one-run protocol (PR #1069, `43a29414`); S11 (no throttling tool), three-run repeats of S8 to S10, the three required traces and the G2 hidden-window check remain. P0-3 not started. Both need the owner's device time. First finding: idle Discair on Home uses about 32 % of one core with almost no wakeups, which the plan did not predict (see the results file, S2 note).

## 1. Executive summary and objectives

**Objectives.** Lower idle and playback CPU and wakeups, keep memory bounded over long sessions, and keep rendering cheap, without changing what the owner sees or hears.

**What this revision concludes.**

1. No profiling has been done yet. Every cost in this document is either a source fact or a hypothesis. Phase 0 (three short measurement steps) comes before any code change.
2. Three source-verified defects are worth fixing regardless of their measured size, because the fix is small and the behaviour is plainly unintended:
   - macOS: the audio engine's 20 ms ticker keeps running after pause, for as long as the song stays open (step M1).
   - macOS: the player bar's title marquee redraws at the full display refresh rate with no cap and no pause (step M2).
   - Android: the Now Playing slideshow recomposes on every display frame (step A1).
3. The first survey's memory concerns were partly overstated. The Librarian's `display` images are 500 px and `thumb` images 250 px (`docs/artwork.md`), so a 12-image slideshow is about 11 MiB decoded (arithmetic, not a measurement). The real unbounded cases on macOS are originals: artist photos, looked-up covers and full-resolution booklet pages, none of which are downsampled or costed correctly (step M3).
4. Custom GPU work (Metal, OpenGL, Vulkan) is not recommended anywhere. The one GPU question worth measuring is live blur over moving content. If it is costly, the fix is to blur less (a small pre-blurred image on macOS, a downscaled layer on Android), not to add a renderer (steps M5 and A3, both conditional).
5. Playback buffering on Android stays as it is. It was tuned for lossless streams over Tailscale, and no evidence suggests the memory is a problem.

**Roadmap in one view.** 14 steps: 3 measurement, 3 mandatory CPU fixes, 3 memory steps, 4 conditional steps that run only if a measured gate is met, and 1 closeout. Model allocation: 9 Sonnet, 5 Haiku (section 9).

## 2. Scope and evidence boundaries

**In scope:** the files listed in section 14 and the behaviour they implement. **Out of scope:** the server, the web client, the widget, and any other efficiency plan.

Every claim in this document carries one of these labels:

| Label | Meaning |
|---|---|
| **Source fact** | Read directly in the code at the reviewed revision. |
| **Arithmetic** | Computed from source facts (for example pixels × 4 bytes). Not a measurement of Discair. |
| **Hypothesis** | A plausible cost or benefit that has not been measured. |
| **Measured** | Recorded by a Phase 0 or later step. None exist yet. |
| **Verified** | A before/after comparison that met its acceptance criteria. None exist yet. |

No percentage improvement is promised anywhere. Gate thresholds in section 8.5 are decision rules, not predictions, and the owner may change them.

## 3. Critical review of the first survey

| # | First survey said | Verdict | Reason |
|---|---|---|---|
| 1 | macOS 50 Hz ticker is a P1 CPU cost | **Partly right, reframed** | Source fact: `play()` starts it, only `stop()` cancels it, so it survives pause. In steady playback `step()` is three early returns, so CPU time is likely tiny (hypothesis). The real cost is 50 main-thread wakeups per second, including while paused for hours. This is an energy and wakeup issue. |
| 2 | "Start the ticker only while a pending transition needs it" | **Insufficient** | Source fact: with crossfade on, or a gapless join across formats, a non-queued `pending` exists for almost the whole song, so the ticker would still run all the time. The poll must become a deadline (step M1). |
| 3 | Cost macOS images with `CGImage.bytesPerRow * height` | **Wrong as stated** | Source fact: images are made with `NSImage(data:)`, which decodes lazily at first draw, on the main thread. There is no decoded bitmap to cost at insert time, and asking for one makes a copy. The decode must move to ImageIO off the main thread; cost then follows for free (step M3). |
| 4 | "Keep the existing rule that only the active and incoming images are needed" on macOS | **Wrong** | Source fact: `SlideshowBackdrop` loads every slide into `@State` up front. But at 500 px each this is about 11 MiB (arithmetic), so it is not worth a step. |
| 5 | Android: "no explicit memory-cache budget" | **Overstated** | Coil 3 applies a default bounded memory cache (a fraction of the app's memory class) and `AsyncImage` already decodes to the laid-out size. No new policy is needed unless measurement shows a problem. |
| 6 | Android: find out why `allowHardware(false)` is set | **Answered** | Source fact: `dominantColor` in `ui/common/Common.kt` and `radioArtworkBytes` in `ui/MainShell.kt` read pixels through `toBitmap()`. Those two requests need software bitmaps; the rest do not (step A2). |
| 7 | Android blur: keep "the no-blur fallback on older devices" | **Dead concern** | Source fact: `minSdk = 33`, and `canBlur` is `SDK_INT >= 31`, so blur is always available. |
| 8 | Compare 30 FPS disc rotation with 15–20 FPS | **Rejected** | Arithmetic: at 10 rpm the disc turns 60° per second; at 15 FPS that is 4° per frame, a visible step at the rim. Lowering the rate trades quality for an unmeasured gain. If the disc is costly, make each frame cheaper instead (section 7). |
| 9 | Lower the slideshow rate to 8–12 FPS | **Kept in part** | A slow drift under a 36-point blur tolerates a low rate. Android goes to about 30 Hz in step A1 (from up to 120). macOS already runs at 20 FPS; going lower is not worth a step. |
| 10 | Android PDF: derive the raster size from the display | **Rejected** | Source fact: pages render at up to 2048 px wide and zoom scales that bitmap. Rendering at display width would blur zoomed pages, which breaks full-resolution booklet zoom. One page is about 23 MiB for an A4-shaped page (arithmetic), held only while the booklet is open. |
| 11 | Test Core Image or Metal for blur on macOS; cached `RenderEffect` on Android | **Narrowed** | A static, heavily blurred backdrop needs very few pixels. A small bitmap blurred once on the CPU or with Core Image is simpler than any per-frame GPU path. No Metal. On Android a `RenderEffect` is applied each time the layer is drawn, so "caching" it is not available; shrinking the blurred layer is (step A3). |
| 12 | ExoPlayer buffers: measure, then maybe reduce | **Kept as measure-only** | The buffer holds compressed audio and is bounded by 60 s. At about 3 Mbit/s (hi-res FLAC) that is roughly 22 MiB per player (arithmetic). Changing it risks the stalls it was tuned to stop. No step. |
| 13 | Phase 3 "targeted GPU improvements" as a standing phase | **Removed** | Replaced by two conditional steps behind measured gates. |

## 4. macOS strategy

### 4.1 Audio engine ticker (`DiscairAudio/AudioOutput.swift`)

**Source facts.** `EngineOutput.startTicker()` runs `step()` every 20 ms. `step()` does real work in three cases only: a growing download (`feedGrowth`, which limits itself to once per 0.25 s), an active fade (volume steps), and a `pending` song that is not queued on the node (crossfade, or a gapless join across formats), where it waits for the last moments of the song. `pause()` does not stop the ticker. `PlayerModel`'s own 250 ms tick does stop on pause.

**Strategy.** Run the ticker only while one of the three cases is live, and replace the long wait before a transition with one sleep to a deadline. Keep the 20 ms cadence inside a fade and near the join; do not lower it. Step M1.

**Alternatives rejected.**
- Starting the second node at an exact sample time (`play(at:)`) would remove the poll for joins, but it changes how transitions are timed and needs its own spike. Not justified by an efficiency goal.
- Engine-side volume ramps: `AVAudioPlayerNode` has no ramp. A custom render path adds risk to the real-time thread for no audible gain.
- A slower global tick: coarser fade steps and later joins.

**Also noted, no step.** `feedGrowth` and `readableFrames` open and test-read files on the main actor, and `attach` sleeps the main thread 150 ms after a device rate change. Both are short, happen between songs or during a download, and touching them risks growing-download playback. Leave them unless Phase 0 shows main-thread hitches there.

### 4.2 Artwork memory (`DiscairUI/Model/ArtworkStore.swift`)

**Source facts.**
- Main cache: 400 entries, no cost limit, no costs passed.
- Album cache: 120 entries, 96 MiB, but cost is the compressed byte count.
- Library covers are sized by the server (`size=px`, 300 by default, 600 for blurred backdrops). Looked-up covers (`lookup|…`) and artist photos (`artist|…`) are fetched as whatever the remote URL serves and their keys ignore `px`.
- `albumImage(_, size: .full)` puts full-resolution originals in the album cache.
- `albumPDF` keeps the last PDF's bytes (which the code notes can be tens of MB) in `lastPDF` until another PDF replaces it.

**Arithmetic.** A 300 px cover is about 0.34 MiB decoded and a 600 px one about 1.4 MiB, so 400 server-sized covers stay within about 140–550 MiB in the worst case and far less in practice. A 3000 px original is about 34 MiB, yet it counts as a few MB in the album cache and as nothing in the main cache.

**Strategy.** Decode with ImageIO off the main actor, capped to the size the caller needs, and cost each entry by its decoded bytes (step M3). Keep full-resolution originals out of the shared cache; the booklet page that asked for one owns it. Release PDF bytes when the booklet closes (step M4). Budgets are provisional until Phase 0 records real sizes.

`NSCache` limits are advisory and it evicts under memory pressure by itself. Do not add a second pressure handler.

### 4.3 Rendering and animation

**Source facts.**
- Disc: `TimelineView` at 30 FPS, paused when not playing or under Reduce Motion. It also spins in the player bar.
- Slideshow: `TimelineView` at 20 FPS; a live 36-point blur wraps layers whose scale and offset change each tick. Paused when not playing, under Reduce Motion, in Low Power Mode and in screenshot capture.
- `BlurredArtwork` (five call sites) and `CollageHeroBackdrop` apply a live blur to static images.
- The player bar marquee uses `TimelineView(.animation)` with no minimum interval and no pause.
- `PlaybackClock` redraws at 4 Hz. `PlayerModel` writes its observable `position` at 4 Hz while playing.
- No code reacts to the window being hidden, minimized or occluded.

**Strategy.**
- SwiftUI's blur, transforms and opacity already run in the system compositor. That is the right baseline and stays.
- Hypothesis: because the slideshow's moving layers sit inside the blur, the blur is recomputed on every tick. Its cost appears in the WindowServer process, not in Discair, so Phase 0 must measure both.
- If that cost passes gate G1, replace live blur with a small image blurred once (step M5). Blur commutes with the pan and, near enough, with the 10 % zoom, so the motion can stay outside the blur.
- Cap and pause the marquee now (step M2).
- Whether timelines keep ticking when the window is not visible is unknown. Measure it; fix only if they do (step M6).
- Keep the 4 Hz clock. Keep Reduce Motion, Low Power Mode and pause as hard stops.

### 4.4 Booklets and PDFs (`DiscairUI/Chrome/BookletSheet.swift`)

**Source facts.** A page loads `display` first and `full` only after the first zoom; both live in the page's `@State`. `PDFDocument(data:)` is built from bytes that `ArtworkStore.lastPDF` also holds. `MediaCache.file(for:ext:)` can return the on-disk file.

**Strategy.** Keep the one-page design and on-demand full resolution. Open the PDF from its cached file when there is one, and clear `lastPDF` on dismissal (step M4). Whether PDFKit holds rendered pages after dismissal is a Phase 0 check, not a step.

## 5. Android strategy

### 5.1 Slideshow recomposition (`ui/player/NowPlayingArtwork.kt`)

**Source facts.** A `withFrameNanos` loop adds to a `mutableFloatStateOf` every display frame. `SlideshowBackdrop` reads that state in composition, so the function, both `layer` calls and their modifiers recompose every frame: up to 120 times per second on the owner's phone. The alpha goes through `Modifier.alpha(value)`, also a composition-time read. A 36 dp blur wraps both layers.

**Strategy (step A1).** Read the clock only inside `graphicsLayer` blocks, so a tick invalidates the layer and nothing else. Let composition see only the slide indices, which change at boundaries. Advance the clock at about 30 Hz instead of every vsync; the drift is slow and sits under a heavy blur. The disc is already correct: an `Animatable` read inside `graphicsLayer`.

### 5.2 Image loading (`AppContainer.kt`, Coil 3.0.4)

**Source facts.** One shared `ImageLoader` with `allowHardware(false)`. Two call sites read pixels (section 3, row 6). The player cover asks the server for 1000 px (about 3.8 MiB decoded, arithmetic).

**Strategy.** Hypothesis: a software bitmap that is drawn also gets uploaded as a GPU texture, so it is held twice, where a hardware bitmap is held once. Turn hardware bitmaps on by default and keep software decoding on the two requests that read pixels (step A2). This is an experiment: it stays only if total PSS falls. A fall in native heap matched by a rise in graphics memory is not a win.

Leave Coil's default memory cache and automatic sizing alone. Keep the 1000 px player cover: it is one image, and it is the sharpest thing on the screen.

### 5.3 Blur and rendering

**Source facts.** Blur is a `RenderEffect` (Android 12 and up, always available here). Slideshow: 36 dp over moving content. Player line and Now Playing backdrop: 28 dp over a static image, scaled 1.3×. Three small infinite transitions drive the playing-bars indicators.

**Strategy.** Compose already renders through the hardware pipeline; transforms and alpha in `graphicsLayer` are the cheapest path there is. A `RenderEffect` blur is reapplied whenever its layer is drawn, so its cost scales with the layer's pixel area and how often the frame redraws. Step A1 cuts the redraw rate. If RenderThread or GPU cost still passes gate G3, blur a quarter-size layer and scale it up (step A3). No custom shaders.

### 5.4 PDF booklet (`ui/album/Booklet.kt`)

**Source facts.** One `PdfRenderer` and descriptor per open booklet, closed in `awaitDispose`. One page bitmap at a time, up to 2048 px wide; `beyondViewportPageCount = 0`. Full-size images load only past a zoom threshold.

**Strategy.** No change. Phase 0 confirms that memory returns to its earlier level after the booklet closes.

### 5.5 Playback (`player/PlaybackService.kt`, Media3 1.11.0)

**Source facts.** 30 s minimum and 60 s maximum buffer, time prioritized over bytes, 1.5 s to start, 8 s to resume after a stall. The next song preloads 10 s. A second player exists only while crossfade is on. Both players share one `DefaultLoadControl`; recent Media3 versions track buffers per player, so each gets its own 60 s ceiling. The controller's 1 s ticker is started and cancelled with the playing state.

**Strategy.** No change. Phase 0 records memory for MP3, CD-quality FLAC and hi-res FLAC, with and without a crossfade overlap, so that a later decision has numbers. If the owner then wants a lower ceiling, it needs its own design: a `LoadControl` cannot be swapped on a built player, and the fading-in player becomes the main one.

## 6. Cross-platform rendering and memory principles

1. **Decode once, at the size shown.** Downsampling at decode is the only way to save decoded memory; nothing later can recover it.
2. **Count all memory.** On Apple Silicon the GPU shares system memory, so use physical footprint. On Android use total PSS, with the graphics and native lines read together. Moving bytes between lines is not an improvement.
3. **The compositor is the default.** Rotation, scale, translation, opacity and cross-fades belong in SwiftUI and Core Animation, or in Compose `graphicsLayer`. Neither client needs Metal, OpenGL or Vulkan.
4. **Blur is the only costly effect here, and its cost is area × redraws.** Cut redraws first (pause, lower cadence), then area (small source, small layer). A blur over static content should be computed once.
5. **Measure the right process.** On macOS, compositor work is charged to WindowServer. On Android it is charged to the app's RenderThread and to the GPU.
6. **Lower frame rates only where the eye cannot tell.** Slow blurred drift: yes. Rotation and scrolling text: only with the owner's visual check.
7. **Audio stays on the CPU audio path.** EQ and crossfade run on real-time buffers; a GPU round trip adds latency and risk for no gain.
8. **Stillness rules are hard constraints.** Reduce Motion, Low Power Mode, Battery Saver and pause stop motion. No step may weaken them.
9. **The two clients share principles, not code.** The macOS ticker has no Android twin; the Android recomposition problem has no macOS twin.

## 7. Additional opportunities

These came from this review, not the first survey. Those marked "step" are in the roadmap. The rest are recorded so they are not rediscovered, and get a step only if Phase 0 points at them.

| Opportunity | Client | Evidence | Disposition |
|---|---|---|---|
| Marquee redraws at display rate, never pauses | macOS | Source fact | Step M2 |
| Main-thread image decode at first draw (scroll hitches) | macOS | Source fact; hitch size is a hypothesis | Solved by step M3 |
| Originals for artist photos and looked-up covers kept at full size | macOS | Source fact | Step M3 |
| PDF bytes kept after the booklet closes | macOS | Source fact | Step M4 |
| Animations may run while the window is hidden or occluded | macOS | Unknown | Phase 0 check; step M6 if gate G2 is met |
| No Baseline Profile (R8 is on) | Android | Source fact; start-up cost unknown | Step A4 if gate G4 is met |
| `PlayerModel.position` written at 4 Hz invalidates every view that reads it | macOS | Source fact; cost unknown | Phase 0 check with the SwiftUI instrument. No step yet. |
| Disc redraws a masked image 30 times per second | macOS | Hypothesis | If Phase 0 shows it, flatten the disc once (`drawingGroup()` or a pre-cut bitmap). No step yet. |
| Playing-bars indicators may read animation values in composition | Android | Unknown | Phase 0 recomposition count. No step yet. |
| A new `OkHttpClient` per scrobble send, and separate clients for offline songs and lyrics | Android | Source fact; a few sends per song | Low value. Share one base client only when that file is next edited. |
| Slideshow could load `thumb` (250 px) instead of `display` (500 px) | Both | Arithmetic: saves about 8 MiB | Not worth the visual risk by itself. Folded into M5 if that step runs. |

## 8. Profiling and measurement methodology

### 8.1 Rules

- Measure release builds. Debug builds are used only for Compose recomposition counts.
- Same device, OS, display refresh rate, power state, server, network and library for before and after. Record all of them.
- Three runs per scenario; compare medians. One run proves nothing.
- Warm up for one minute, then measure for five. Ten-minute runs are needed only for the memory-stability scenario (S8).
- Start cheap. Use a full Instruments or Perfetto trace only when a cheap number shows something to explain.
- Keep traces and the test library out of the repository. Commit only the result tables.

### 8.2 Scenarios

| ID | Scenario | Answers |
|---|---|---|
| S1 | Cold launch to Home, five times | Start-up time |
| S2 | Home idle, nothing played since launch | Idle floor |
| S3 | Playing, main window or screen visible, Now Playing closed | Bar disc, marquee, clock, tickers |
| S4 | Now Playing, photos off, playing | Disc and static backdrop |
| S5 | Now Playing, photos on, playing | Slideshow and blur (compare with S4) |
| S6 | Paused for five minutes after S5 | Work that should have stopped |
| S7 | Playing with the window minimized or fully covered (macOS); app in background (Android) | Hidden work |
| S8 | Browse 30 albums and 10 artists, open and close each, twice | Cache growth and return |
| S9 | Open a booklet, turn 10 pages, zoom 3, open a large PDF, close | Peak and release |
| S10 | MP3, CD-quality FLAC, hi-res FLAC; then crossfade with a real overlap | Buffer memory, playback health |
| S11 | Growing download: play a song that is still downloading (macOS) | Ticker behaviour, continuity |

### 8.3 macOS tools

| Question | Cheap tool | Deeper tool |
|---|---|---|
| CPU and wakeups | `top -l 6 -s 10 -pid <pid> -stats pid,cpu,idlew,power` for Discair **and** WindowServer | Instruments Time Profiler (`xcrun xctrace record --template 'Time Profiler' --attach <pid> --time-limit 60s`) |
| Memory | `footprint <pid>` (physical footprint with graphics categories); `vmmap --summary <pid>` | Instruments Allocations and VM Tracker, with generation marks before and after S8 and S9 |
| Which views redraw | none | Instruments SwiftUI template (view body counts) |
| Frame pacing | visual check | Instruments Animation Hitches |
| Energy | `top` power column; Activity Monitor Energy tab | `sudo powermetrics --show-process-energy -i 10000 -n 6` (the owner runs it; it needs an administrator password) |
| Leaks and retention | `leaks <pid>` after S8 and S9 | Allocations, "persistent" filter on `NSImage`, `CGImage`, `PDFDocument` |

### 8.4 Android tools

| Question | Cheap tool | Deeper tool |
|---|---|---|
| Memory | `adb shell dumpsys meminfo app.discair` (Java heap, native heap, graphics, total PSS) | Android Studio Memory Profiler heap dump after S8 and S9 |
| Frame pacing | `adb shell dumpsys gfxinfo app.discair reset`, run the scenario, then `adb shell dumpsys gfxinfo app.discair` (percentiles, janky frames) | Perfetto with FrameTimeline (`android.surfaceflinger.frametimeline`), plus `sched`, `gfx`, `view` and `freq` categories |
| CPU by thread | `adb shell top -H -b -n 6 -d 10 -p $(adb shell pidof app.discair)` (main thread and RenderThread separately) | Perfetto CPU scheduling; Android Studio CPU Profiler |
| Recomposition | none | Layout Inspector recomposition counts (debug build; counts only, never timings) |
| Start-up | `adb shell am start -W -n app.discair/.MainActivity` after `am force-stop`, five times, `TotalTime` | Macrobenchmark `StartupTimingMetric` (only inside step A4) |
| Energy | `adb shell dumpsys batterystats --reset`, unplug, run 10 minutes, `dumpsys batterystats app.discair` | Android Studio Power Profiler needs on-device power rails, which the Galaxy S20 FE lacks; use CPU time and batterystats as the proxy |

**Devices.** The owner's Mac and the owner's Galaxy S20 FE, at its 120 Hz setting, are required. A second, slower Android phone is welcome but not required. Emulator numbers are not accepted for memory, frames or energy.

### 8.5 Gates for conditional steps

Provisional thresholds; the owner may change them after seeing Phase 0.

| Gate | Opens | Condition (medians) |
|---|---|---|
| G1 | M5 | S5 minus S4, Discair plus WindowServer: more than 3 percentage points of one core, or the `top` power figure more than 20 % higher |
| G2 | M6 | S7: Discair CPU more than 0.5 percentage points above S7 repeated with Reduce Motion on (audio-only reference), or any `TimelineView` body evaluations in the SwiftUI instrument while hidden |
| G3 | A3 | After A1, S5 minus S4: RenderThread CPU more than 5 percentage points of one core, or the 90th-percentile frame time over the display's frame budget |
| G4 | A4 | S1 median `TotalTime` over 1000 ms, or the owner judges start-up slow |

### 8.6 When to measure

- **Before any code:** P0-1 to P0-3. They produce the baseline tables and settle the gates.
- **After each step:** only that step's scenarios, three runs, with the cheap tools. Each step lists them.
- **At the end:** P4-1 reruns the whole baseline once.

## 9. Prioritized roadmap

Ordered by expected value, then risk. "Mandatory" means do it once Phase 0 has a baseline to compare against. "Experimental" means keep the change only if its own measurement passes. "Conditional" means do not start unless the gate is met.

| Order | Step | Client | Kind | Class | Model | Effort |
|---|---|---|---|---|---|---|
| 1 | P0-1 Baseline protocol and results file | Both | Measurement prep | Mandatory | Haiku | Low |
| 2 | P0-2 macOS baseline and gate decisions | macOS | Profiling | Mandatory | Sonnet | Medium |
| 3 | P0-3 Android baseline and gate decisions | Android | Profiling | Mandatory | Sonnet | Medium |
| 4 | A1 Slideshow without per-frame recomposition | Android | Straightforward | Mandatory | Sonnet | Medium |
| 5 | M7 `PlaybackClock` does not tick while paused | macOS | Straightforward | Mandatory | Sonnet | Medium |
| 6 | M1 Demand-driven engine ticker | macOS | Complex (audio) | Mandatory | Sonnet | High |
| 7 | M2 Marquee cap and pause | macOS | Straightforward | Mandatory | Haiku | Low |
| 8 | M3 Off-main decode, real costs, budgets | macOS | Complex (memory) | Mandatory | Sonnet | High |
| 9 | M4 Release PDF bytes; open PDFs from file | macOS | Straightforward | Mandatory | Haiku | Medium |
| 10 | A2 Hardware bitmaps by default | Android | Experimental | Keep only if it wins | Sonnet | Medium |
| 11 | M5 Pre-blurred backdrops | macOS | Experimental | Conditional on G1 | Sonnet | High |
| 12 | A3 Quarter-size blur layer | Android | Experimental | Conditional on G3 | Sonnet | Medium |
| 13 | M6 Pause motion when the window is hidden | macOS | Straightforward | Conditional on G2 | Haiku | Medium |
| 14 | A4 Baseline Profile | Android | Straightforward | Conditional on G4 | Haiku | Medium |
| 15 | P4-1 Final comparison and closeout | Both | Profiling | Mandatory | Sonnet | Low |

Steps on different clients are independent and can be interleaved. Each code step is one branch and one PR under `docs/DEVELOPMENT_WORKFLOW.md`.

## 10. Implementation steps

### Phase 0: measurement

#### P0-1 Baseline protocol and results file

- **Objective:** make every later measurement repeatable and comparable.
- **Current problem:** no baseline exists and no agreed way to take one.
- **Proposed solution:** add `docs/client_efficiency_results.md` with the scenario scripts, exact commands and empty result tables.
- **Implementation details:** copy scenarios S1–S11 and the cheap-tool commands from section 8. For each scenario write numbered manual steps (which album, which song, how long). Add a header block per run: app SHA, build type, device, OS, refresh rate, power state, network, server version. One table per client with a row per scenario and columns for CPU, wakeups or RenderThread CPU, memory lines, frame percentiles and notes. Add a small shell script per client under `scripts/perf/` that runs the cheap commands and prints a table row; it must not need a private path or credential.
- **Dependencies:** none.
- **Risks:** none to the app. A vague scenario script makes later numbers incomparable.
- **Verification:** a second agent or the owner can run S2 from the file alone and fill one row. **Not yet done.** Script checks so far: `bash -n` on both; the macOS script on a live process; the Android script's error path with no device and its parsing against a mock `adb`.
- **Acceptance criteria:** the results file and both scripts exist (met); every scenario has numbered steps (met); no measured values are invented (met); the file refers to the owner only as "the owner" (met).
- **Status:** done, except the second-person S2 check above. Scripts: `scripts/perf/macos_cheap.sh` and `scripts/perf/android_cheap.sh`. Open point: `docs/DEVELOPMENT_WORKFLOW.md` routes code changes through a PR; these scripts went direct to `main` on the owner's instruction.
- **Model: Haiku | Effort: Low**

#### P0-2 macOS baseline and gate decisions

- **Objective:** replace the macOS hypotheses with measurements and decide gates G1 and G2.
- **Current problem:** every macOS cost in sections 3 and 4 is unmeasured.
- **Proposed solution:** run S1–S11 on a release build with the cheap tools; take a deeper trace only where a number needs explaining.
- **Implementation details:** always sample WindowServer beside Discair. Required deeper traces: (a) the SwiftUI instrument during S3 and S5 to list views whose bodies run on a timer; (b) Allocations with generation marks around S8 and S9 to see what stays; (c) a Time Profiler run of S6 to confirm what runs while paused. Record the decoded pixel sizes of the largest images in memory after S8 (Allocations, `CGImage` and `NSImage` by size). State for each row of section 3 whether the measurement supports it. The owner drives the UI and runs `powermetrics`; the agent runs the scripts and reads the traces.
- **Dependencies:** P0-1. A release build of the reviewed SHA.
- **Risks:** an attached profiler changes timing; use the cheap tools for the headline numbers and the traces for explanation only.
- **Verification:** three runs per scenario; the spread between runs is recorded beside each median.
- **Acceptance criteria:** the macOS table is complete; G1 and G2 are each marked met or not met with the numbers; any hypothesis the data contradicts is marked so in the results file; no code is changed.
- **Status (2026-11-14):** in progress. Done: S2 to S7 and the S7 Reduce Motion reference, three runs each (S3 run 3 is an outlier, flagged). **G1 not met** (S5 − S4 = −2.1 points), so M5 closes without work. **G2 met by the letter but marginal** (S7 26.8 % vs 24.8 % with Reduce Motion); **the owner opened M6 on 2026-11-14**, expecting a gain of about 2 points at most, with the main cost elsewhere. Main finding: Discair uses about 25 to 29 % of one core in every state (S6 paused 13.75 %), unaffected by hiding the window or Reduce Motion; the cause is unidentified and needs a SwiftUI-instrument trace. S5 photos add about 170 MB (207 → 376 MB). Marquee hypothesis rejected. S1 and S8 to S10 measured 2026-11-14 on a short, one-run protocol (S1 0.88 s to first window; S8 footprint 147 to 380 MB, nothing released; S9 +31 MB open, 14 MB retained; S10 CPU does not track bitrate; a hang during S10 is unexplained). Not done: S11 (no throttling tool), the three required traces, three-run repeats of S8 to S10. S2 had a paused track loaded, because the app has no way to clear Now Playing. SwiftUI-instrument trace and element bisect of idle Home done (2026-11-14): the main thread is saturated by AttributeGraph updates about 120 times a second, and **the cause is the two 4 Hz `PlaybackClock` timelines in the player bar running while paused**: making the clock static, or not rendering it unless the phase is `.playing`, takes idle CPU from about 26 % to 0 % and SwiftUI updates to 0. Glass, waveform, blurred plate, covers, banner, sidebar and marquee are refuted (results file, S2 bisect). No code changed. The fix is recorded as step **M7** (to implement, not started); S3 and S5 traces with the clock running, the hidden-window check for G2, S1, S8 to S11 and the other traces remain.
- **Model: Sonnet | Effort: Medium**

#### P0-3 Android baseline and gate decisions

- **Objective:** the same for Android, deciding G3 (provisionally, to be confirmed after A1) and G4.
- **Current problem:** every Android cost in sections 3 and 5 is unmeasured.
- **Proposed solution:** run S1–S10 on the Galaxy S20 FE at 120 Hz with a release build and the cheap tools; one Perfetto trace of S5; one debug-build Layout Inspector session for recomposition counts.
- **Implementation details:** for S5 record main-thread and RenderThread CPU separately and the gfxinfo percentiles. In Layout Inspector note recomposition counts over 10 seconds for `SlideshowBackdrop`, the disc, and the three playing-bars indicators. For S8 and S9 record meminfo before, at peak and one minute after returning Home. For S10 record meminfo per format and during a crossfade overlap, and note any rebuffering. Confirm in S7 that the app draws no frames in the background (`gfxinfo` frame count stays flat).
- **Dependencies:** P0-1. The phone connected by USB with debugging on.
- **Risks:** thermal throttling skews later runs; let the phone cool between scenarios and note the battery temperature.
- **Verification:** three runs per scenario; spread recorded.
- **Acceptance criteria:** the Android table is complete; G4 is decided; the S5 numbers needed for G3 are recorded; recomposition counts are recorded; no code is changed.
- **Model: Sonnet | Effort: Medium**

### Phase 1: mandatory CPU fixes

#### A1 Android slideshow without per-frame recomposition

- **Objective:** stop composition work on every frame of the slideshow and lower its redraw rate.
- **Current problem:** `SlideshowBackdrop` reads a per-frame state in composition (section 5.1).
- **Proposed solution:** composition reads only slide indices; `graphicsLayer` blocks read the clock; the clock advances at about 30 Hz.
- **Implementation details:** in `ui/player/NowPlayingArtwork.kt`:
  1. Keep `elapsed` as a `MutableFloatState` but never read it in the composable body.
  2. Add `val slots by remember(slides) { derivedStateOf { slideshowFrame(elapsed.floatValue.toDouble(), slides.size)?.let { Triple(it.index, it.next, it.mix > 0f) } } }`. It changes only at slide and cross-fade boundaries.
  3. In each layer, replace `Modifier.alpha(...)` and the captured `progress` with one `graphicsLayer { }` block that calls `slideshowFrame` itself and sets `alpha`, `scaleX`, `scaleY` and `translationX`. Keep the `loaded` check inside the block so an unloaded image stays at alpha 0.
  4. Replace the every-vsync loop with `while (true) { delay(33); val now = withFrameNanos { it }; elapsed.floatValue += … }`.
  5. Keep the `running` key (pause, Reduce Motion, Battery Saver) exactly as it is. Do not change `slideshowFrame`, the blur, the scrim or the 30 px pan.
- **Dependencies:** P0-3.
- **Risks:** an off-by-one at a slide boundary (a flash of the wrong image); the incoming layer missing during a cross-fade; 30 Hz looking steppy.
- **Verification:** existing `slideshowFrame` unit tests still pass (`./gradlew testDebugUnitTest --tests '*NowPlayingArtwork*'` or the matching model test). Layout Inspector count for `SlideshowBackdrop` over 10 seconds. S5 and S6 with the cheap tools, three runs. The owner watches two full slide changes.
- **Acceptance criteria:** `SlideshowBackdrop` recomposes only at slide and cross-fade boundaries (a handful of times per slide, not per frame); S5 main-thread CPU median is lower than baseline; S5 frame percentiles are no worse; S6 shows no slideshow work; slide order, hold time and cross-fade length are unchanged; the owner sees no stepping.
- **Model: Sonnet | Effort: Medium**

#### M1 macOS demand-driven engine ticker

- **Objective:** no periodic engine work unless a growing download, a fade or an imminent transition needs it; none at all while an ordinary song is paused.
- **Current problem:** the 20 ms ticker runs from the first `play()` until `stop()` (section 4.1).
- **Proposed solution:** one private `rearmTicker()` that decides, from engine state, whether a ticker is needed and when it must first fire.
- **Implementation details:** in `DiscairAudio/AudioOutput.swift`:
  1. Define the need: (a) `growth != nil`: tick every 20 ms as today, including while paused, because the download continues and the hand-over to a whole file must still happen; (b) `fade != nil` and the current node is playing: tick every 20 ms; (c) a `pending` song not queued on the node and the current node is playing: sleep until `remaining − max(fadeLength, 0.03) − 0.25` seconds from now, then tick every 20 ms; (d) otherwise no ticker.
  2. `rearmTicker()` cancels the running task and starts a new one with that first delay, or none. Call it at the end of `play`, `pause`, `seek`, `preload`, `cancelPreload`, `open`, `openGrowing`, `beginFade`, `endFade`, and wherever `growth`, `fade` or `pending` is set or cleared inside `step`, `feedGrowth` and `segmentEnded`. `stop()` keeps cancelling.
  3. Leave `step()`, `feedGrowth()`, the fade curve, the audio-clock rule for fade progress, and `segmentEnded`'s late-join fallback untouched. The fallback stays as the safety net for a missed deadline.
  4. Add an internal `tickerActiveForTests` beside `levelsForTests`.
  5. The deadline in (c) assumes playback at normal speed, which is the only speed the engine has. A seek or a pause changes `remaining`, which is why both must rearm.
- **Dependencies:** P0-2.
- **Risks:** a missed rearm path makes a crossfade start late or fall back to a hard join; a growing download that stalls and never resumes; a double ticker. This is the highest-risk step in the plan.
- **Verification:** `swift test --filter DiscairAudioTests` (covers `EngineOutputTests` and `GrowingPlaybackTests`). New tests listed below. S6 and S11 with `top` (wakeups), three runs. Manual listening: one crossfade, one same-format gapless join, one cross-format join, one seek to ten seconds before the end with crossfade on, one pause and resume inside a fade, one growing download on a throttled link.
- **Acceptance criteria:** new tests prove: no ticker while an ordinary song is paused; no ticker during ordinary playback with a queued gapless follower; a ticker during a fade and none after it; a crossfade starts within the existing tolerance of its due time after a seek and after pause and resume; a stalled growing download resumes when bytes arrive, playing or paused; `stop()` and `open()` leave no ticker. All existing audio tests pass unchanged. In S6 the paused app's wakeups are within run-to-run noise of S2. No audible change in the manual checks.
- **Model: Sonnet | Effort: High**

#### M2 macOS marquee cap and pause

- **Objective:** stop the player bar title from redrawing at display rate forever.
- **Current problem:** `TimelineView(.animation)` in `Themes/Cupertino/CupertinoPlayerBar.swift` (the overflow branch) has no minimum interval and no pause.
- **Proposed solution:** cap the schedule and pause it under the same stillness rules as the slideshow.
- **Implementation details:** use `.animation(minimumInterval: 1.0 / 30, paused: lowPower)`. Read Low Power Mode the way `SlideshowBackdrop` does (initial `ProcessInfo` value plus `NSProcessInfoPowerStateDidChange`). While paused, show the text at its current offset. Reduce Motion already takes the non-scrolling branch; keep that. If the owner finds 30 FPS text scrolling uneven, use `1.0 / 60` and record that choice.
- **Dependencies:** P0-2.
- **Risks:** text scrolling that looks less smooth on a 120 Hz display.
- **Verification:** S3 with a long title, `top` for Discair and WindowServer, three runs. The owner's visual check. `swift test --filter DiscairUITests` only if a UI test touches the player bar.
- **Acceptance criteria:** the marquee does not advance in Low Power Mode; S3 CPU median (Discair plus WindowServer) is not higher than baseline; the owner accepts the motion; Reduce Motion behaviour is unchanged.
- **Model: Haiku | Effort: Low**

### Phase 2: memory

#### M3 macOS off-main decode, real costs and budgets

- **Objective:** every cached image is decoded once, off the main thread, no larger than needed, and costed by its decoded bytes.
- **Current problem:** lazy main-thread decode, uncosted or mis-costed entries, originals kept at full size (section 4.2).
- **Proposed solution:** one decode helper built on ImageIO, used by every `ArtworkStore` path; cost limits on both caches; full-resolution originals kept out of the shared cache.
- **Implementation details:** in `DiscairUI/Model/ArtworkStore.swift`:
  1. Add a `nonisolated` async helper `decode(_ data: Data, maxPixel: Int?) -> (CGImage, cost: Int)?`. Use `CGImageSourceCreateWithData` with `kCGImageSourceShouldCache: false`, then `CGImageSourceCreateThumbnailAtIndex` with `kCGImageSourceCreateThumbnailFromImageAlways`, `kCGImageSourceCreateThumbnailWithTransform`, `kCGImageSourceShouldCacheImmediately` all true and `kCGImageSourceThumbnailMaxPixelSize` when `maxPixel` is set. This never upscales. Cost is `bytesPerRow * height`. Wrap the result in `NSImage(cgImage:size:)` on the main actor.
  2. Caps: server-sized covers (`coverArt@px`, `owned|…`) pass `px`; looked-up covers pass their `px` argument and add it to the cache key; artist photos get a cap equal to the largest size any call site draws, in pixels at 2× (find the call sites; add a size argument if they differ widely); `thumb` and `display` album images pass no cap (they are already 250 and 500 px).
  3. `size: .full` decodes at full size with no cap, off the main actor, and is returned without being stored in `albumCache`. `BookletPage` already holds it in `@State`. The disk media cache still stores the bytes.
  4. Pass `cost:` on every `setObject`. Set `cache.totalCostLimit` and keep `albumCache`'s limit, now in real bytes. Provisional values: 128 MiB main, 64 MiB album. Replace them with values from the P0-2 size table and record the reasoning in a comment.
  5. `isSmall` reads `representations.first.pixelsWide`; confirm it still works for a `CGImage`-backed image, or read the `CGImage` width instead.
  6. Keep the disk-cache writes, the `failed` set, the joined album loads and the cancellation behaviour exactly as they are.
- **Dependencies:** P0-2 (size table).
- **Risks:** a cap set too low softens artwork; the wrong orientation without the transform flag; a changed cache key causing one refetch per cover; `isSmall` misjudging and swapping covers; an actor-isolation mistake around the non-`Sendable` `NSImage`.
- **Verification:** new unit tests for the helper (cap respected, no upscale, cost equals decoded bytes, EXIF orientation applied) and for `isSmall`. `swift test --filter DiscairUITests` for the store's existing tests. S8 and S9 with `footprint`, three runs. Side-by-side screenshots of Home, an album page, an artist page and a zoomed booklet page at the same window size, before and after.
- **Acceptance criteria:** no `NSImage(data:)` remains in `ArtworkStore`; every cache insert carries a decoded-byte cost; both caches have a cost limit; after S8 the footprint returns to within run-to-run noise of its pre-browse level plus the cache budgets; S9 peak falls back after the booklet closes; screenshots show no visible loss of sharpness; a zoomed booklet page is pixel-identical in size to before; Time Profiler shows no image decode on the main thread during scrolling.
- **Model: Sonnet | Effort: High**

#### M4 macOS release PDF bytes; open PDFs from file

- **Objective:** a closed booklet holds no PDF memory.
- **Current problem:** `lastPDF` keeps the last PDF's bytes for the rest of the session, and `PDFDocument(data:)` is built from a second reference to them (section 4.4).
- **Proposed solution:** prefer the cached file; drop the bytes on dismissal.
- **Implementation details:** in `ArtworkStore`, add a method that returns the PDF's file URL when `media?.file(for:ext:)` has it, and a `releasePDF()` that clears `lastPDF`. In `DiscairUI/Chrome/BookletSheet.swift`, build `PDFDocument(url:)` when a file URL exists and fall back to `PDFDocument(data:)` when the media cache is off. Call `releasePDF()` when the sheet is dismissed. Keep the one-page presentation from #973 and the link-click delegate.
- **Dependencies:** none (independent of M3; do it after M3 only to avoid merge conflicts in the same file).
- **Risks:** a PDF that fails to open from the file path; reopening the same booklet refetches when the media cache is off (accepted: it is the price of releasing the memory).
- **Verification:** S9 with a large PDF, `footprint` before opening, while open and one minute after closing, three runs. A test that `releasePDF()` clears the held bytes. `swift test --filter DiscairUITests`.
- **Acceptance criteria:** one minute after closing, the footprint is within run-to-run noise of the pre-open level; the PDF opens with the media cache on and off; page turning and zoom are unchanged.
- **Model: Haiku | Effort: Medium**

#### A2 Android hardware bitmaps by default (experimental)

- **Objective:** find out whether hardware bitmaps lower total memory, and keep them only if they do.
- **Current problem:** every image is a software bitmap because two call sites read pixels (section 5.2).
- **Proposed solution:** remove the global `allowHardware(false)`; set it on the two requests that need it.
- **Implementation details:** in `AppContainer.kt` delete `.allowHardware(false)`. In `ui/common/Common.kt`, when `Cover` is given `onColor`, build an `ImageRequest` with `allowHardware(false)`. In `ui/MainShell.kt` add `allowHardware(false)` to the `radioArtworkBytes` request. Search the Android sources for `toBitmap`, `asAndroidBitmap`, `getPixel`, `copyPixelsToBuffer`, `drawToBitmap`, `PixelCopy` and `Canvas(` over a bitmap; every hit that touches a Coil image needs the same per-request setting. Check that the media notification artwork path is covered.
- **Dependencies:** P0-3. Do after A1 so S5 numbers are not confounded.
- **Risks:** a missed pixel read crashes with "Software rendering doesn't support hardware bitmaps" or returns no colour; memory only moves from native heap to graphics.
- **Verification:** S4, S5, S8 and a radio station with artwork: meminfo (total PSS, native heap, graphics) and gfxinfo, three runs each. Manual: the Now Playing tint still follows the cover in every theme; the notification and lock screen show radio artwork; no crash in a 15-minute mixed session.
- **Acceptance criteria:** keep the change only if S8 total PSS median falls by more than the run-to-run spread and frame percentiles are no worse. Otherwise revert and record the numbers in the results file. In both cases: no crash, tint and notification artwork unchanged.
- **Model: Sonnet | Effort: Medium**

### Phase 3: conditional steps

#### M5 macOS pre-blurred backdrops (only if G1 is met)

- **Objective:** remove live blur from moving backdrops.
- **Current problem:** measured in P0-2 as the S5 minus S4 cost. If G1 is not met, this step is closed without work.
- **Proposed solution:** blur a small copy of each image once and draw it without a blur filter; keep the motion.
- **Implementation details:** add a `nonisolated` backdrop renderer: take the `thumb` image, downsample to about 128 px on its longer side with the M3 helper, then with Core Image apply `clampedToExtent`, `CIGaussianBlur` with the radius scaled by (derivative pixels ÷ on-screen points), `CIColorControls` for the same saturation, crop to the original extent and render with one shared `CIContext`. Cache the result in a small dedicated `NSCache` keyed by image id and blur class. In `SlideshowBackdrop` draw the derivative with `.interpolation(.medium)`, remove `.blur` and `.saturation`, keep `scaleEffect`, `offset`, the opacity cross-fade, the 20 FPS timeline and every pause rule. Apply the same derivative to `CollageHeroBackdrop` and then `BlurredArtwork`, each as its own commit and measurement, and stop at the first one that shows no gain. Check how `RenderMode.offscreenScreenshot` tests expect backdrops to look, since a baked blur will now appear in captures.
- **Dependencies:** P0-2 with G1 met; M3 (decode helper).
- **Risks:** a backdrop that looks different (banding, softer or harder blur, edge darkening); screenshot tests changing; more code for a gain that may be small.
- **Verification:** S4 and S5 for Discair plus WindowServer, three runs. Side-by-side screenshots of three albums at two window sizes for the owner. `swift test --filter DiscairUITests`.
- **Acceptance criteria:** S5 minus S4 (Discair plus WindowServer) falls below the G1 threshold or by more than the run-to-run spread; footprint in S5 is not higher; the owner approves the screenshots; pause, Reduce Motion and Low Power Mode still hold the backdrop still. If the gain is within noise, revert.
- **Model: Sonnet | Effort: High**

#### A3 Android quarter-size blur layer (only if G3 is met after A1)

- **Objective:** cut the pixel area the blur processes.
- **Current problem:** measured after A1 as the S5 minus S4 RenderThread and frame-time cost. If G3 is not met, this step is closed without work.
- **Proposed solution:** lay the blurred box out at a quarter of the width and height, blur it with a quarter of the radius, and scale it up four times in a parent `graphicsLayer`.
- **Implementation details:** in `SlideshowBackdrop`, wrap the blurred `Box` in a layout modifier that measures it at one quarter of the incoming constraints and places it at the origin, with `graphicsLayer { scaleX = 4f; scaleY = 4f; transformOrigin = TransformOrigin(0f, 0f) }` on the parent. Use `blur(9.dp)`. Divide the pan by four so the on-screen drift is unchanged. Coil will then decode the slides at the smaller layout size by itself. If S4 alone (static backdrop) is costly, apply the same wrapper to the 28 dp backdrops in `PlayerLineUi.kt` and `NowPlayingSheet.kt` as a second commit.
- **Dependencies:** A1; P0-3 numbers; G3 met.
- **Risks:** visible softness or shimmer from upscaling; edges showing at the screen border; a wrong pan distance.
- **Verification:** S4 and S5 gfxinfo and RenderThread CPU, three runs. Screenshots before and after for the owner.
- **Acceptance criteria:** S5 RenderThread CPU median and 90th-percentile frame time both improve by more than the run-to-run spread; total PSS is not higher; the owner approves the look. Otherwise revert.
- **Model: Sonnet | Effort: Medium**

#### M6 macOS pause motion when the window is hidden (only if G2 is met)

- **Status (2026-11-14):** G2 met by the letter (marginal); **opened by the owner**. Not started. Expected gain is about 2 points of one core at most (P0-2, S7 against S7 with Reduce Motion); the larger idle cost is M7 (PlaybackClock).

- **Objective:** no animation work while nothing is visible.
- **Current problem:** measured in P0-2 scenario S7. If timelines already stop when the window is hidden, this step is closed without work.
- **Proposed solution:** one environment value, "window visible", fed from `NSWindow.occlusionState`, added to every `paused:` condition.
- **Implementation details:** observe `NSWindow.didChangeOcclusionStateNotification` for the main window and publish `occlusionState.contains(.visible)` through the SwiftUI environment. Add it to the `paused:` argument of the disc, slideshow and marquee timelines and to `PlaybackClock` (switch it to a schedule that can pause, or skip its content update). Hold angles and elapsed time the same way the existing `running` handlers do, so nothing jumps on return.
- **Dependencies:** P0-2 with G2 met; M2 (same marquee code).
- **Risks:** motion that does not resume, or jumps, when the window comes back; a second window (booklet sheet) confusing the visible state.
- **Verification:** S7 with `top`, three runs. Manual: minimize, switch Space, cover fully, then return; the disc and slideshow continue from where they stopped.
- **Acceptance criteria:** S7 Discair CPU is within run-to-run noise of S7 with Reduce Motion on; no visible jump on return; Reduce Motion and Low Power Mode behaviour unchanged.
- **Model: Haiku | Effort: Medium**

#### M7 macOS `PlaybackClock` does not tick while paused

- **Status (2026-11-14):** **to implement; not started; needs the owner's go-ahead.** Added from the P0-2 element bisect ([`client_efficiency_results.md`](client_efficiency_results.md), "S2 bisect").
- **Objective:** remove the idle cost of a paused player: about 26 % of one core on Home with a paused track (25 to 29 % in every state tried).
- **Current problem:** `macos/Sources/DiscairUI/Chrome/PlaybackClock.swift` wraps `TimelineView(.periodic(from: .now, by: 0.25))`, used twice in `CupertinoPlayerBar` (the time readout, and the middle line for lyrics and facts). While paused, the schedule still drives a full SwiftUI graph update about 120 times a second (measured: 0 % CPU and 0 updates in a 10 s trace when it was static or gated; unchanged with a fixed start date instead of `.now`). Why a 4 Hz schedule updates at display rate is not understood.
- **Proposed solution:** render the `TimelineView` only while `player.phase == .playing`; otherwise call `content(player.position)` directly. Bisect variant "gate" did exactly this.
- **Implementation details:** in `PlaybackClock.body`, branch on `player.phase` (a stored, observed property, so the view re-evaluates when playback starts or stops). Check every other `TimelineView(.periodic…)` in `DiscairUI` for the same pattern (the 1 s timelines in `CupertinoPlayerBar`, `CupertinoStations`, `CupertinoNowPlayingLive`, `CupertinoDownloadButton`, `CupertinoSleepTimer`, `MenuBarPopover`) and measure before touching them; do not change them speculatively. Check that the middle line's lyric transitions and the time readout still update promptly on play, pause, seek and song change, and that the live-station bar is unchanged.
- **Dependencies:** P0-2 (done). Do before re-measuring S3 to S5, so their numbers are not confounded by this cost.
- **Risks:** the readout or lyric line stuck after a state change; a paused clock showing a stale position after a seek while paused (`position` must update on seek). Understand why a 4 Hz timeline updates at display rate before assuming the gate also cures the playing state; the playing state still ticks and is measured in S3.
- **Verification:** S2 and S6 with `macos_cheap.sh`, three runs each, and a SwiftUI-instrument trace of idle Home (expect near-zero updates). Then S3 (playing) to see the cost that remains. Filtered tests only (`swift test --filter` for the player and bar tests).
- **Acceptance criteria:** S2 Discair CPU falls from about 26 % to near zero (within noise of the audio-only reference) with no visible change on play, pause, seek, song change or station start; S3 not worse than before.
- **Model: Sonnet | Effort: Medium**

#### A4 Android Baseline Profile (only if G4 is met)

- **Objective:** faster cold start and fewer first-use janky frames.
- **Current problem:** the release build has R8 but no Baseline Profile, so start-up code is interpreted or JIT-compiled on first runs. Its size is measured in S1.
- **Proposed solution:** the standard AndroidX Baseline Profile set-up.
- **Implementation details:** add a `baselineprofile` module with the `androidx.baselineprofile` plugin and `profileinstaller` to the app. One generator journey: cold start, scroll Home, open an album, start a song, open Now Playing. Generate on the owner's phone or an API 33+ emulator with a rooted or userdebug image, commit the generated profile, and build the release with it. Sign-in in the journey must use a local test server, never real credentials in the repository.
- **Dependencies:** P0-3 with G4 met.
- **Risks:** build-time and module overhead; a journey that cannot sign in without credentials; the profile going stale as code changes (regenerate at releases).
- **Verification:** S1 five times before and after on the same install path, plus gfxinfo for the first Home scroll after install.
- **Acceptance criteria:** S1 median `TotalTime` improves by more than the run-to-run spread; the release build and existing unit tests still pass; no credential is committed. Otherwise remove the module.
- **Model: Haiku | Effort: Medium**

### Phase 4: closeout

#### P4-1 Final comparison and closeout

- **Objective:** one honest before/after record.
- **Current problem:** per-step measurements do not show the combined effect or interactions.
- **Proposed solution:** rerun the full baseline once on the final SHA and write the comparison.
- **Implementation details:** rerun S1–S11 on macOS and S1–S10 on Android with the P0-1 scripts. Fill a before/after table in `docs/client_efficiency_results.md`. Change each hypothesis in this document's section 13 to "verified", "refuted" or "still open", with the numbers. Update `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md` as the workflow requires.
- **Dependencies:** all steps that were carried out.
- **Risks:** drift in the test library or network since the baseline; note any difference.
- **Verification:** three runs per scenario.
- **Acceptance criteria:** every scenario has before and after medians with spread; every reverted or skipped step is listed with its reason; no claim is made without a number behind it.
- **Model: Sonnet | Effort: Low**

## 11. Regression testing requirements

These apply on top of each step's own verification. A step that touches an area must pass that area's row.

| Area to preserve | Check | Steps |
|---|---|---|
| Audio fidelity | No change to the EQ, mixer, sample-rate matching or decode path in any step; bit-identical playback is assumed because those files are not edited. A step that edits them is out of scope. | M1 |
| Gapless playback | `EngineOutputTests` gapless cases; manual same-format and cross-format album joins | M1 |
| Crossfade | Fade level tests through `levelsForTests`; manual fade after seek, and pause and resume inside a fade. Android crossfade is untouched; `docs/ANDROID_CROSSFADE_CONTRACT.md` checks apply only if a step edits the player package. | M1 |
| Growing-download playback | `GrowingPlaybackTests`; S11 on a throttled link, including a forced stall and a pause during the stall | M1 |
| Playback continuity | S10 on LAN and Tailscale with no new rebuffering; a 30-minute mixed session per client at closeout | M1, A2, P4-1 |
| Artwork quality | Side-by-side screenshots at the same window or screen size; the owner's sign-off | M3, M5, A2, A3 |
| Full-resolution booklet zoom | A zoomed page shows the original's pixel size (macOS); zoomed image and PDF pages are as sharp as before (both) | M3, M4 |
| Accessibility | Labels on the disc, booklet badge, player bar cover and booklet pages unchanged; decorative backdrops stay hidden from VoiceOver and TalkBack | A1, M2, M5, M6, A3 |
| Reduce Motion | With it on: no disc spin, no slideshow drift, no marquee, on both clients | A1, M2, M5, M6, A3 |
| macOS Low Power Mode | Slideshow still; marquee still (new in M2) | M2, M5, M6 |
| Android Battery Saver | Slideshow still | A1, A3 |
| Client/server contracts | No request, size parameter or endpoint changes except the `thumb` request in M5, which is an existing size. Check `docs/MACOS_CLIENT_CONTRACT.md`, `docs/ANDROID_PLAYER_CONTRACT.md` and `docs/artwork.md`. | M3, M5 |

Testing rules from `docs/DEVELOPMENT_WORKFLOW.md` apply: focused tests only (`swift test --filter …`, `./gradlew testDebugUnitTest --tests …` with JDK 17), never the full suite; Swift tests run locally on the Mac; report exactly what ran.

## 12. Acceptance criteria and definition of done

**A step is done when:**

1. Its own acceptance criteria are met, with three-run medians and spread recorded in the results file against the exact SHA.
2. Its rows in section 11 pass.
3. Total resource use fell or stayed level: no shift from CPU to GPU, or from one memory line to another, is counted as a gain.
4. Focused tests pass and required CI passes on the final PR head.
5. An experimental or conditional step that did not beat run-to-run noise is reverted, and the result is recorded.

**The plan is done when:**

- P0-1 to P0-3, A1, M1, M2, M3, M4 and M7 are complete.
- A2 is kept or reverted on its numbers.
- Each of M5, M6, A3 and A4 is either complete or closed with its gate recorded as not met.
- P4-1 is recorded and section 13 is updated.

## 13. Remaining uncertainties and decisions needing evidence

| Question | Settled by | Affects |
|---|---|---|
| How much do 50 wakeups per second cost in energy, playing and paused? | P0-2, S3 and S6 | Size of M1's benefit (M1 is done either way) |
| Does live blur over moving layers cost meaningful WindowServer time on the owner's Mac? | P0-2, S4 against S5 | G1, M5 |
| Do SwiftUI timelines keep running when the window is hidden? | P0-2, S7 | G2, M6 |
| Does the disc redraw its masked image every frame? | P0-2 SwiftUI and Time Profiler traces | A possible later step (section 7) |
| Does the 4 Hz `position` write redraw more than the time readout? | P0-2 SwiftUI trace | A possible later step |
| What are the real decoded sizes of artist photos, looked-up covers and booklet originals? | P0-2 size table | M3 caps and budgets |
| Does PDFKit keep rendered pages after dismissal? | P0-2, S9 | Whether M4 is enough |
| How much of the Android slideshow cost is composition and how much is blur? | P0-3, then A1 | G3, A3 |
| Do hardware bitmaps lower total PSS on the Galaxy S20 FE? | A2 | Whether A2 stays |
| Is cold start slow enough to justify a profile module? | P0-3, S1 | G4, A4 |
| How much memory do the ExoPlayer buffers hold for hi-res FLAC and during a crossfade? | P0-3, S10 | A future owner decision; no step planned |
| Is 30 FPS acceptable for the macOS marquee and 30 Hz for the Android drift? | The owner's visual check in M2 and A1 | Final cadence values |

## 14. Source files reviewed

- macOS audio: `macos/Sources/DiscairAudio/AudioOutput.swift`; tests in `macos/Tests/DiscairAudioTests/`
- macOS artwork: `macos/Sources/DiscairUI/Model/ArtworkStore.swift`, `macos/Sources/DiscairUI/Chrome/CoverView.swift`
- macOS Now Playing and booklet: `macos/Sources/DiscairUI/Chrome/NowPlayingArtwork.swift`, `BookletSheet.swift`, `PlaybackClock.swift`, `ArtistCollage.swift`
- macOS player model and bar (ticks and marquee only): `macos/Sources/DiscairUI/Model/PlayerModel.swift`, `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoPlayerBar.swift`
- Android image loader and build: `android/app/src/main/kotlin/app/discair/AppContainer.kt`, `android/app/build.gradle.kts`
- Android Now Playing: `ui/player/NowPlayingArtwork.kt`, `ui/player/NowPlayingSheet.kt`, `ui/player/PlayerLineUi.kt`
- Android pixel reads: `ui/common/Common.kt` (`dominantColor`), `ui/MainShell.kt` (`radioArtworkBytes`)
- Android booklet: `ui/album/Booklet.kt`
- Android playback: `player/PlaybackService.kt`, `player/PlayerController.kt`
- Image sizes: `docs/artwork.md` (thumb 250 px, display 500 px)

**Verification boundary.** This revision is a source review. No profiler, device run or listening test was performed, and no code, setting or buffer value was changed.
