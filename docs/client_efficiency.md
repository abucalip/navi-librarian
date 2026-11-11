# Discair client efficiency proposal

**Status:** proposal only; not an implementation authorization.  
**Baseline reviewed:** GitHub `main`, `ce01596fb8f3d6daf615a401e12bf3a5bc38c313` (2026-11-11).  
**Scope:** macOS and Android client CPU, application memory, image rendering and GPU use.  
**Evidence boundary:** this is a source-level survey. No Instruments, Android Studio Profiler, Perfetto or device/window profiling was performed for this document. The items below are measured code characteristics and hypotheses to validate, not proof that any one item accounts for a particular RAM or CPU figure.

## 1. Objective

Reduce Discair's idle and playback CPU use, keep memory predictable during long browsing and Now Playing sessions, and use the GPU deliberately for visual work where it is likely to help. Preserve audio fidelity, artwork quality, playback continuity, accessibility, reduced-motion behavior and the existing client/server contracts.

The goal is not to remove the artwork-rich presentation. It is to make the expensive parts demand-driven, bounded and measurable.

## 2. Findings at a glance

| Priority | Client | Finding in current source | Proposed direction |
|---|---|---|---|
| P1 | macOS CPU | Audio output starts a 20 ms (50 Hz) ticker on play. Ordinary pause does not cancel it; stop does. | Run the ticker only while a growing file, crossfade, pending transition or other time-sensitive work needs it. |
| P1 | Android CPU | Now Playing slideshow advances elapsed time through `withFrameNanosCompat()` and writes Compose state on every display frame. | Move frame-varying reads into a graphics/draw layer or use an animation primitive that does not recompose the full slideshow subtree each frame. |
| P1 | Both GPU/CPU | Large animated blurred artwork is used in Now Playing and player surfaces. | Keep motion and blur in the rendering pipeline, avoid repeated CPU image processing, and cache only useful derived images. |
| P1 | macOS RAM | Main `NSCache<NSString, NSImage>` has a 400-item count limit but no total-cost limit. The album cache's 96 MiB cost is calculated from compressed data length. | Bound decoded-image cost using pixel storage, not compressed file size; set a budget for the main cache too. |
| P1 | Android RAM | Shared Coil loader globally sets `allowHardware(false)`; the application does not declare an explicit memory-cache budget or a client-level decode-size policy in its builder. | Measure the reason for software-only bitmaps; enable hardware-backed images where compatible and scope software decoding to transformations that require it. Add explicit cache and request sizing. |
| P2 | Android RAM | Now Playing asks for up to 1000 px artwork; slideshow selection can contain up to 12 display images. Only the current and transition image need to be visible, but image-loader caching can retain decoded results. | Keep prefetch bounded to current/next; use display-sized requests and avoid eager loading of the whole slideshow. |
| P2 | Both RAM | Full-resolution artwork is fetched for zoom; PDFs and large originals can add transient memory. | Keep full resolution on-demand, release it when the viewer closes or zoom ends, and measure PDF decode/render peaks. |
| P2 | Android RAM | ExoPlayer buffers 30–60 seconds and a second player can exist during crossfade. | Measure memory for lossless/high-bitrate streams and crossfade before changing buffer policy. |
| P3 | Both | Several small periodic clocks/tickers exist. | Retain low-frequency updates that serve visible UI or playback semantics; stop them when their owning surface or task is inactive. |

## 3. macOS client

### 3.1 CPU: make the audio ticker conditional

**Current behavior**

`macos/Sources/DiscairAudio/AudioOutput.swift` sets `tick = 0.02` seconds. `play()` starts a task that calls `step()` every 20 ms. `pause()` pauses the audio node but does not stop the ticker; `stop()` cancels it. The ticker is useful for growing downloads, crossfade progression, pending transitions and related playback housekeeping, but normal steady-state playback may not need 50 checks per second.

**Proposal**

1. Separate the work that genuinely needs frequent polling from ordinary playback state.
2. Start the 50 Hz ticker only while a growing file, an active fade, a pending transition or another explicitly identified operation needs it.
3. Cancel or suspend it on pause when no such operation needs to progress; restart it on resume if required.
4. Prefer audio-engine scheduling/completion callbacks for events that can be driven by the engine rather than polled.
5. Preserve the exact transition, gapless, growing-download and cancellation semantics. Do not simply lower the tick rate without tests.

**Acceptance:** tests prove that a paused ordinary track has no active ticker; growing playback still resumes when bytes arrive; crossfade reaches the same end state and timing tolerance; queued transitions do not introduce gaps; stop/replacement cancels work exactly once.

### 3.2 RAM: bound decoded artwork, not compressed files

**Current behavior**

`macos/Sources/DiscairUI/Model/ArtworkStore.swift` has a primary `NSCache` with `countLimit = 400` and no `totalCostLimit`. Its separate album-art cache has a 96 MiB cost limit, but entries are inserted with `data.count` as the cost. That is the compressed response size, not the decoded bitmap's memory footprint.

**Proposal**

- Give both caches explicit, independently justified budgets.
- Calculate image cost from decoded pixel storage where available (for example, `CGImage.bytesPerRow * height`), with a safe fallback when the backing representation is unavailable.
- Keep cache limits advisory: handle eviction and reloading correctly, and do not rely on `NSCache` as a hard process-memory ceiling.
- Downsample before decoding when the view needs a thumbnail or display image; do not decode a full original and then scale it down for a small card.
- Keep full-resolution originals out of the general-purpose cache, or place them in a separately bounded, short-lived zoom cache.
- Avoid retaining duplicate `Data`, `NSImage` and PDF representations longer than necessary.

The artwork cache is shared by many screens, so budgets should be based on measured decoded sizes and the app's total footprint, not chosen solely from the number of albums.

### 3.3 GPU: use the Apple rendering stack for image presentation

The Mac's Apple Silicon GPU is appropriate for compositing, transforms, rotation, opacity, scaling and image effects. SwiftUI/Core Animation already perform much of this work through the system rendering pipeline. The first optimization should be to keep animated changes as layer properties rather than repeatedly rebuilding image content.

**Recommendations**

- Keep disc rotation, slideshow pan/zoom, cross-fades and view transforms in SwiftUI/Core Animation layer animations wherever possible.
- For the blurred artwork backdrop in `macos/Sources/DiscairUI/Chrome/CoverView.swift`, profile the cost before replacing SwiftUI's blur. If blur is a material bottleneck, test a cached Core Image or Metal-rendered blurred derivative generated when the source artwork changes, not on every animation frame.
- Cache a blurred derivative by source image identity and target dimensions; invalidate it when the artwork or required output size changes. Keep the unblurred source for foreground display and zoom.
- Avoid creating a new Metal texture or converting a bitmap on every frame. Texture upload, intermediate render targets and retained textures can increase unified-memory pressure.
- Use GPU acceleration for image effects only where the result is a genuine improvement in frame time, CPU use or energy. Measure both GPU activity and total memory/energy.

Do not introduce a custom Metal renderer just because the app has image-heavy screens. The system compositor is the preferred baseline; Core Image/Metal is a targeted option after profiling.

### 3.4 Now Playing motion

`macos/Sources/DiscairUI/Chrome/NowPlayingArtwork.swift` runs the disc at a 30 FPS TimelineView and the slideshow at a 20 FPS TimelineView. The slideshow is already paused when playback stops, Reduce Motion is enabled, Low Power Mode is active or screenshot rendering is in progress. Keep these safeguards.

- Compare 30 FPS disc motion with 15–20 FPS on the target Mac; select the lowest rate that still looks smooth.
- Compare the slideshow's 20 FPS updates with 8–12 FPS, or use compositor-driven animation for slow pan/zoom and only update slide state at transition boundaries.
- Keep the existing rule that only the active and incoming images are needed for a transition. Avoid turning the full slide list into eagerly decoded `NSImage` objects.
- Do not lower the 4 Hz playback clock in `PlaybackClock.swift` unless profiling shows it matters; it is a small, user-visible time display.

### 3.5 Booklets and PDFs

The booklet view retains display and full-resolution images for zoom, and PDFKit receives the PDF data to create a document. The recent main change (#973) now presents one centred PDF page at a time rather than a two-page spread; preserve that lower-workload behavior.

- Keep the PDF document scoped to the visible booklet session and release it on dismissal.
- Request full-resolution page images only after an explicit zoom action.
- Avoid keeping both the full PDF byte buffer and redundant rendered page images alive after the viewer closes.
- Profile page changes, zoom and large PDFs separately; PDFKit may retain decoded/rendered resources beyond the lifetime of a single SwiftUI view value.

## 4. Android client

### 4.1 CPU: remove per-frame Compose state churn

**Current behavior**

`android/app/src/main/kotlin/app/discair/ui/player/NowPlayingArtwork.kt` advances slideshow elapsed time in an infinite `withFrameNanosCompat()` loop and writes to `mutableFloatStateOf` on every display frame. That can mean 60 or 120 state writes per second and cause recomposition work even though the desired change is mostly image position, scale and alpha.

**Proposal**

- Keep the animation clock, but read frame-varying values inside a `graphicsLayer` or draw lambda so Compose can update the layer without recomposing the full content tree on every frame.
- Alternatively use `Animatable`/infinite transition primitives with state reads confined to the layer that actually animates.
- Update the slide index only at transition boundaries; do not make the slide-selection model itself a per-frame state.
- Keep the existing stop conditions: paused playback, reduced motion and Battery Saver. Also ensure the effect is cancelled when the Now Playing surface leaves composition.
- Profile the 6-second disc rotation separately; it already uses an animation primitive and a graphics layer, so it is a lower-priority suspect.

**Acceptance:** frame time and CPU use improve during a 10-minute slideshow; no visible stutter or incorrect slide timing; no slideshow work continues after the surface is removed or playback pauses.

### 4.2 RAM: establish a deliberate Coil policy

**Current behavior**

`android/app/src/main/kotlin/app/discair/AppContainer.kt` builds one shared Coil `ImageLoader` and sets `allowHardware(false)`. The builder does not declare an app-specific memory-cache budget. `NowPlayingSheet.kt` requests player artwork at up to 1000 px. The slideshow model selects at most 12 display images; the composable draws the current image and, during a cross-fade, the next image. The pager in `ui/album/Booklet.kt` already uses `beyondViewportPageCount = 0` and fetches full resolution only after zoom.

**Proposal**

1. Establish why hardware bitmaps were disabled. Check all Coil transformations, software readbacks and screenshot/test paths before changing the shared setting.
2. Where compatible, allow hardware bitmaps for ordinary display-only artwork. If a particular transformation requires software pixels, request software decoding for that request rather than forcing every image in the app to be software-backed.
3. Configure a measured Coil memory-cache budget and explicit request sizing. Keep disk caching separate from decoded-memory caching.
4. Use the smallest server size that satisfies the rendered surface:
   - tiny avatars and list thumbnails: thumb;
   - album cards and ordinary grids: thumb or display according to rendered pixel dimensions;
   - Now Playing: display, with the current 1000 px ceiling retained only if measurements show it is useful on the target device;
   - slideshow backdrop: display-sized images only;
   - booklet zoom: full only after a deliberate zoom gesture.
5. Prefetch only the next image when a transition is imminent. Do not decode all 12 slideshow candidates at once.
6. Clear or allow eviction of large transient images when a sheet/viewer closes; avoid application-level maps that retain bitmap objects after their UI has gone away.

A 1000 × 1000 RGBA bitmap is approximately 3.8 MiB before row alignment and other overhead. A handful of retained images, PDF page bitmaps, GPU textures and player buffers can therefore add up quickly. This is an illustration of decoded size, not a measured Discair allocation.

### 4.3 GPU: accelerate presentation, not the entire image pipeline

Android already uses hardware-accelerated rendering for normal Compose drawing. Use it rather than adding a custom renderer.

- Keep rotation, translation, scale, alpha and cross-fade in `graphicsLayer` or Compose animation APIs.
- The slideshow applies a 36 dp blur and the player line applies a 28 dp blur. Profile these on the actual target GPU and Android versions. If blur dominates, test a hardware-backed `RenderEffect`/Compose rendering path on supported Android versions, with the existing no-blur/tint fallback on older devices.
- Apply blur to a low-resolution backdrop, not a full-resolution source. Reuse the result while the source image and output size remain unchanged.
- Keep blur and backdrop work inactive when Now Playing is hidden, photos are off, playback is paused, or reduced motion/Battery Saver requires stillness.
- Use `graphicsLayer` for animated transforms so the image is not repeatedly decoded or redrawn from scratch.
- Do not add custom OpenGL/Vulkan/compute code unless Perfetto or GPU profiling demonstrates a specific bottleneck that platform effects cannot address.

Hardware bitmaps and GPU textures are not free memory. They may move pressure from the Java heap to graphics/native or shared device memory, and can complicate pixel readback. Compare total process PSS/RSS, graphics memory where available, frame time and energy—not just Java heap size.

### 4.4 PDF booklet rendering

`android/app/src/main/kotlin/app/discair/ui/album/Booklet.kt` already renders one pager page at a time (`beyondViewportPageCount = 0`) and loads the original only after zoom. Keep that architecture.

- Derive the raster target from the actual display pixel size and density, with a sensible maximum; avoid rendering every page at a fixed oversized resolution.
- Keep a single active page bitmap plus, at most, a small adjacent-page prefetch if measurements justify it.
- Close `PdfRenderer`, page and file-descriptor resources on dismissal and cancellation.
- Do not retain both the PDF's full byte array and every rendered page bitmap.
- Verify that zoom remains sharp; memory savings must not silently degrade the owner's explicit zoom action.

### 4.5 Playback buffers and crossfade

`PlaybackService.kt` configures ExoPlayer for 30 seconds minimum and 60 seconds maximum buffering, with time prioritized over the byte threshold. This was chosen to prevent repeated stalls for lossless streams over a home/Tailscale connection. Crossfade can create a second player while the overlap is active.

Do not reduce these values based on a generic memory target. First measure MP3, FLAC and high-bitrate FLAC at normal playback, buffering/rebuffering and crossfade. If memory is excessive, evaluate a combined byte-and-time budget or a smaller crossfade-only second-player buffer, but only if playback remains reliable on the owner's actual network. The audio service's stability takes precedence over a small idle-memory reduction.

The Android controller's one-second position/scrobble ticker is comparatively low frequency. Verify its lifecycle and cancellation, but do not prioritize it ahead of the per-frame slideshow loop.

## 5. Cross-platform GPU and memory principles

1. **Decode once at the size needed.** A GPU blur cannot recover memory already wasted decoding a 4000 px original for a 300 px card.
2. **Separate source, display and derived images.** Keep the original for explicit zoom; use a bounded display decode; create a blurred derivative only when needed.
3. **Prefer compositor transforms.** Rotation, scale, translation, alpha and simple transitions should stay in the platform rendering system.
4. **Use GPU effects selectively.** Blur is the strongest candidate. Cache its output and compare GPU time, CPU time, frame pacing, memory and battery.
5. **Do not use the GPU for audio DSP by default.** EQ and crossfade operate on real-time audio buffers. Moving this work to the GPU would add buffer transfers, synchronization and latency, and would complicate the real-time audio path. Keep audio processing on the established CPU/audio-engine path unless a separate, measured design proves a GPU implementation safe and worthwhile.
6. **Avoid per-frame CPU/GPU conversions.** Repeated bitmap-to-texture uploads, readbacks and new offscreen surfaces can cost more than the effect itself.
7. **Respect low-power and accessibility modes.** Keep Reduce Motion, Battery Saver/Low Power Mode and pause behavior as hard constraints, not optional tuning switches.
8. **Treat GPU memory as part of total memory.** On Apple Silicon, CPU and GPU share unified physical memory. On Android, hardware bitmaps and render targets still consume device memory even when they are not counted in the Java heap.

## 6. Measurement plan

No optimization should be accepted on source inspection alone. Establish a reproducible before/after baseline on the same app revision, device, display refresh rate, server, network and library.

### 6.1 Scenarios

Run each scenario for at least 10 minutes after a consistent warm-up, and record cold-start and steady-state separately:

1. Cold launch, Home idle, no playback.
2. Browse 20–30 albums with mixed artwork sizes; open and close several album pages.
3. Now Playing with photos off; playback paused.
4. Now Playing with disc rotation and photos/slideshow enabled during playback.
5. Repeatedly open booklet pages, zoom in/out and dismiss; include a large PDF.
6. Play a local/LAN MP3, then FLAC and high-bitrate FLAC over the same network.
7. Play with crossfade disabled and enabled; include an actual overlap.
8. Pause for five minutes, then resume; verify background/hidden surfaces are not animating.

### 6.2 Tools and metrics

**macOS**
- Instruments: Time Profiler, Allocations, VM Tracker and Energy Log.
- Record process physical footprint/resident memory, peak memory, decoded image/cache estimates, CPU time by hot path, main-thread stalls, GPU activity/frame pacing and energy impact.
- Inspect allocations while navigating and after dismissing the booklet/Now Playing views to find objects that remain retained.

**Android**
- Android Studio Profiler: Memory, CPU and Energy where available.
- Perfetto/System Trace and FrameTimeline for Compose recomposition, main/render thread scheduling, frame misses and GPU/render work.
- Record total PSS/RSS, Java heap, native/graphics memory where available, bitmap allocations, CPU time, frame time/jank and battery/thermal behavior.
- Repeat on the owner's Galaxy S20 FE and one lower-memory or lower-performance Android device if available. Do not infer device behavior from an emulator alone.

### 6.3 Report format

For each scenario, record:
- exact GitHub application SHA and build type;
- OS/device, display refresh rate and power mode;
- peak and steady-state memory (including native/graphics categories where available);
- average and peak CPU use, plus hot functions;
- frame-time distribution/jank and GPU activity;
- network format/bitrate and whether crossfade was active;
- visible regressions, errors and whether resources were released after leaving the screen.

Compare medians across repeated runs. Do not claim a percentage improvement from a single run. Keep the test library and private media outside the repository.

## 7. Recommended implementation sequence

This is a prioritization proposal, not a commitment to implement all items in one change.

### Phase 0 — establish baselines

- Profile the scenarios in section 6 before modifying code.
- Confirm whether the macOS ticker continues to run while paused and quantify its CPU cost.
- Quantify Android slideshow recomposition and blur cost at the actual refresh rate.
- Identify the largest decoded-image and PDF allocations and whether they remain after navigation.
- Record whether GPU time, CPU time, memory or network buffering is the dominant constraint for each scenario.

### Phase 1 — high-confidence CPU fixes

1. macOS: make the audio ticker demand-driven and pause-aware, with transition/growing-download regression tests.
2. Android: eliminate full-subtree per-frame recomposition in the slideshow; retain the same visual timing and pause rules.
3. Profile blur and animation paths on both clients; change frame cadence only where a measured gain is visible.

### Phase 2 — predictable artwork memory

1. macOS: add decoded-cost accounting and explicit budgets to both artwork caches.
2. Android: introduce an explicit Coil memory-cache/decode-size policy and permit hardware images where safe.
3. Bound slideshow prefetch and full-resolution zoom retention.
4. Keep PDF rendering one-page-at-a-time and validate resource closure.

### Phase 3 — targeted GPU improvements

1. Benchmark current SwiftUI/Core Animation and Compose hardware rendering first.
2. If blur is a measured bottleneck, prototype cached Core Image/Metal on macOS and a cached hardware RenderEffect path on Android.
3. Compare CPU/GPU frame time, memory and energy; retain the simplest implementation that wins.
4. Do not introduce custom GPU audio processing.

### Phase 4 — playback memory tuning, only if needed

- Measure ExoPlayer buffer and dual-player overlap memory for each format.
- Adjust only with playback continuity tests on LAN and Tailscale.
- Preserve audio quality and the current crossfade contract.

## 8. Acceptance criteria

A performance change is acceptable only when all applicable points hold:

- The target scenario has a repeatable before/after measurement on the exact GitHub revision.
- Memory is bounded by decoded cost or explicit loader policy; leaving a screen releases transient full-resolution and PDF resources.
- CPU work stops when playback is paused or the owning UI is hidden, except for explicitly required playback work.
- Animation remains smooth at supported refresh rates, with no increase in dropped frames or visible artifacts.
- GPU changes improve measured frame time, CPU use or energy without increasing total memory unacceptably.
- Playback remains gapless/correct, crossfade behavior is unchanged, and no buffering regressions appear on the owner's network.
- Reduced Motion, Low Power Mode/Battery Saver, accessibility labels and all existing client/server contracts remain intact.
- Focused regression tests pass; the required CI workflows pass on the exact final PR-head SHA. UI changes receive the manual checks required by `docs/LOCAL_UI_TESTING.md`.

## 9. Source files reviewed

- macOS artwork cache: `macos/Sources/DiscairUI/Model/ArtworkStore.swift`
- macOS Now Playing animation: `macos/Sources/DiscairUI/Chrome/NowPlayingArtwork.swift`
- macOS booklet/PDF: `macos/Sources/DiscairUI/Chrome/BookletSheet.swift`
- macOS audio ticker: `macos/Sources/DiscairAudio/AudioOutput.swift`
- macOS playback clock and blur: `macos/Sources/DiscairUI/Chrome/PlaybackClock.swift`, `macos/Sources/DiscairUI/Chrome/CoverView.swift`
- Android shared image loader: `android/app/src/main/kotlin/app/discair/AppContainer.kt`
- Android slideshow and disc: `android/app/src/main/kotlin/app/discair/ui/player/NowPlayingArtwork.kt`
- Android player artwork sizing: `android/app/src/main/kotlin/app/discair/ui/player/NowPlayingSheet.kt`
- Android blurred player line: `android/app/src/main/kotlin/app/discair/ui/player/PlayerLineUi.kt`
- Android booklet/PDF: `android/app/src/main/kotlin/app/discair/ui/album/Booklet.kt`
- Android player buffers and ticker: `android/app/src/main/kotlin/app/discair/player/PlaybackService.kt`, `android/app/src/main/kotlin/app/discair/player/PlayerController.kt`
- Android slideshow selection: `android/app/src/main/kotlin/app/discair/model/NowPlayingArtwork.kt`
- Related contracts and artwork design: `docs/MACOS_CLIENT_CONTRACT.md`, `docs/ANDROID_PLAYER_CONTRACT.md`, `docs/ANDROID_CROSSFADE_CONTRACT.md`, `docs/artwork.md`, `docs/TEST_PLAN.md`

## 10. Current verification boundary

At the baseline revision, the four repository main-branch workflows (Python syntax check, container runtime smoke test, Docker packaging validation and Docker image validation with publishing paused) completed successfully. Those workflows validate the repository revision, not client runtime performance.

No client profiler session, physical-device performance run, macOS window verification or Android device verification was performed as part of this survey. No code, runtime settings, audio buffer values or artwork behavior have been changed by this proposal.
