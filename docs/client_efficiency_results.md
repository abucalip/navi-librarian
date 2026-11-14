# Client efficiency — baseline protocol and results

**Status:** protocol and tables. Only the macOS S2 row has been measured (2026-11-14); every other cell stays blank until a Phase 0 step (P0-2 macOS, P0-3 Android) fills it from a real run.
**Plan:** [`docs/client_efficiency.md`](client_efficiency.md), step P0-1. Scenario IDs (S1–S11) and cheap-tool commands are copied from its section 8; the plan remains the authority if the two ever disagree.
**Scripts:** [`scripts/perf/macos_cheap.sh`](../scripts/perf/macos_cheap.sh) and [`scripts/perf/android_cheap.sh`](../scripts/perf/android_cheap.sh). Each prints one markdown table row per run. Raw tool output goes to `$DISCAIR_PERF_RAW` (default `~/discair-perf-raw`), never into the repository.

## 1. Rules (from the plan, section 8.1)

- Release builds only. Debug builds are used only for Compose recomposition counts (P0-3).
- Same device, OS, display refresh rate, power state, server, network and library for every before and after run. Record all of them in the run header (section 2).
- Three runs per scenario. Report the median and the spread (max minus min) beside it. One run proves nothing.
- Warm up for one minute, then measure. Ten-minute runs are needed only for S8 (memory stability).
- Start with the cheap tools. Use a full Instruments or Perfetto trace only to explain a number that needs it.
- Do not commit traces, screenshots of the owner's library, or the test library. Commit only the result tables.
- Refer to the person directing the project only as "the owner".

## 2. Run header

Copy this block once per run and fill every field. A run with a blank field is not comparable and must be marked as such.

```
Run ID:            <client>-<scenario>-<run n>-<YYYY-MM-DD>
App SHA:           <GitHub commit the release build was made from>
Build type:        release (macOS: Release configuration; Android: release variant)
Device:            <Mac model / chip, RAM> or <Galaxy S20 FE, serial withheld>
OS version:        <macOS or Android version and build>
Display refresh:   <Hz, and whether 120 Hz is set on Android>
Power state:       <plugged / battery %, Low Power Mode or Battery Saver on/off>
Network:           <Wi-Fi / Tailscale / offline>
Server version:    <Navidrome-side server build or commit>
Library:           <library identifier from the owner, not file paths>
Thermal:           <Android battery temperature, or "n/a">
Notes:             <anything unusual: other apps, a sync, a download>
```

## 3. Scenarios

Every step is manual unless it names a script. "Owner" means the owner performs it; "agent" means the agent runs the command and reads the output. Pick the album, song and duration in the run header so a later run can repeat them exactly.

Test selection for every scenario: one album with a long title, one album with a short title, one song with a long title (for the marquee), and one song with no artwork. Record which ones were used.

### S1 — Cold launch to Home, five times (both)

1. Quit the app completely.
2. macOS: start Discair from the Dock or `open`. Android: `adb shell am force-stop app.discair`.
3. Wait until Home shows its first content. Record the time from the start command.
4. Repeat steps 1–3 five times with a 30-second pause between launches.
5. Android: `adb shell am start -W -n app.discair/.MainActivity` after `am force-stop`, five times; record `TotalTime`.
6. Record the median of the five launches.

### S2 — Home idle, nothing played since launch (both)

1. Launch the app and leave it on Home. Do not play anything.
2. Wait one minute (warm-up).
3. Agent: run the cheap tool for five minutes.
4. Owner: do not touch the app during the measurement.

### S3 — Playing, main window or screen visible, Now Playing closed (both)

1. Play a song with a long title and artwork.
2. macOS: keep the main window visible, not minimized. Android: keep the screen on, Now Playing sheet closed.
3. Wait one minute (warm-up).
4. Agent: run the cheap tool for five minutes.
5. macOS: the player bar marquee should run during this scenario. Record whether it does.

### S4 — Now Playing, photos off, playing (both)

1. Open Now Playing with the slideshow turned off (macOS: `barOptions.showSlideshow` off in Now Playing; Android: the Now Playing photos toggle off).
2. Play the song with artwork.
3. Wait one minute (warm-up).
4. Agent: run the cheap tool for five minutes.

### S5 — Now Playing, photos on, playing (both)

1. Same song as S4.
2. Turn the slideshow on in Now Playing. Confirm that at least two slides have loaded.
3. Wait one minute (warm-up).
4. Agent: run the cheap tool for five minutes.
5. Compare directly with S4 in the same session. The difference is the slideshow and its blur.

### S6 — Paused for five minutes after S5 (both)

1. From the end of S5, pause playback. Leave Now Playing open.
2. Wait one minute.
3. Agent: run the cheap tool for five minutes.
4. macOS: this is the scenario that shows work that should have stopped.

### S7 — Hidden work (macOS: window minimized or fully covered; Android: app in background)

1. macOS: play a song, minimize the Discair window (or cover it fully with another window). Android: play a song, press Home so Discair is in the background.
2. Wait one minute.
3. Agent: run the cheap tool for five minutes.
4. Android: the `gfxinfo` frame count must stay flat across the window. Record the before and after counts.
5. Optional comparison (macOS, for gate G2): repeat with Reduce Motion on, same song.

### S8 — Browse 30 albums and 10 artists, open and close each, twice (both)

1. Start from a fresh launch (S1 state).
2. Open each of 30 albums and each of 10 artists in turn, then close them. Use the same list for every run; record it.
3. Repeat step 2 once more.
4. Agent: capture memory after the second pass (see the memory line of the cheap tool), then wait one minute and capture again.
5. Ten-minute run: the agent may repeat step 4 at 10 minutes for the memory-stability check.

### S9 — Booklet, turn ten pages, zoom, large PDF, close (both)

1. Open a booklet with a large PDF (record its page count and size).
2. Turn ten pages. Zoom three times on one page.
3. Close the booklet.
4. Agent: capture memory before opening, while open (after step 2), and one minute after closing.
5. Android: keep one `meminfo` capture before and after, as the plan requires.

### S10 — Playback formats and crossfade (both)

1. Play one MP3, one CD-quality FLAC and one hi-res FLAC, each for three minutes. Record the file type and bitrate.
2. Repeat with crossfade on and a real overlap (crossfade length set in settings; record the value).
3. Agent: capture memory per format and during the crossfade overlap.
4. Note any rebuffering or stall.

### S11 — Growing download (macOS only)

1. Start a download on a throttled link (record the throttle setting).
2. Once the song is playable, start playing it while it still downloads.
3. Agent: run the cheap tool for five minutes while the download is still growing.
4. Note any audible gap at the moment the download completes.

## 4. Cheap-tool commands

macOS (`scripts/perf/macos_cheap.sh <scenario> <run>`):

| Question | Command |
|---|---|
| CPU and wakeups, Discair and WindowServer | `top -l 6 -s 10 -pid <pid> -stats pid,cpu,idlew,power` |
| Memory | `footprint <pid>` and `vmmap --summary <pid>` |
| Leaks | `leaks <pid>` after S8 and S9 |
| Energy | `top` power column; `sudo powermetrics --show-process-energy -i 10000 -n 6` (owner runs it; needs an administrator password) |

Android (`scripts/perf/android_cheap.sh <scenario> <run>`):

| Question | Command |
|---|---|
| Memory | `adb shell dumpsys meminfo app.discair` |
| Frame pacing | `adb shell dumpsys gfxinfo app.discair reset`, run the scenario, then `adb shell dumpsys gfxinfo app.discair` |
| CPU by thread | `adb shell top -H -b -n 6 -d 10 -p $(adb shell pidof app.discair)` |
| Start-up | `adb shell am start -W -n app.discair/.MainActivity` after `am force-stop`, five times |
| Energy | `adb shell dumpsys batterystats --reset`, unplug, run 10 minutes, `adb shell dumpsys batterystats app.discair` |

The deeper tools in plan section 8.3 and 8.4 (Instruments, Perfetto, Layout Inspector, Macrobenchmark, Allocations) are used only where a step's own protocol asks for them, and their output stays outside the repository.

## 5. macOS results (P0-2)

Columns: Discair CPU %, WindowServer CPU %, Discair wakeups/s, Discair power, WindowServer power, Discair footprint, notes. The script fills the per-run row; the medians are computed across the three runs.

| Scenario | Run | Discair CPU % | WindowServer CPU % | Discair wakeups/s | Discair power | WindowServer power | Footprint | Notes |
|---|---|---|---|---|---|---|---|---|
| S1 (median of 5 launches) | — | | | | | | | |
| S2 | 1 | 23.30 | 2.95 | 1.84 | 23.40 | 3.00 | 212 MB | 30 samples at 10 s |
| S2 | 2 | 23.40 | 2.70 | 1.16 | 23.45 | 2.70 | 212 MB | |
| S2 | 3 | 23.40 | 2.80 | 1.16 | 23.45 | 2.80 | 212 MB | |
| S2 | **median** | 23.40 (spread 0.10) | 2.80 (spread 0.25) | 1.16 (spread 0.68) | 23.45 (spread 0.05) | 2.80 (spread 0.30) | 212 MB (spread 0) | Idle Home sits at about 23 % of one core; see the S2 note below |
| S3 | 1 | | | | | | | |
| S3 | 2 | | | | | | | |
| S3 | 3 | | | | | | | |
| S3 | **median** | | | | | | | |
| S4 | 1 | | | | | | | |
| S4 | 2 | | | | | | | |
| S4 | 3 | | | | | | | |
| S4 | **median** | | | | | | | |
| S5 | 1 | | | | | | | |
| S5 | 2 | | | | | | | |
| S5 | 3 | | | | | | | |
| S5 | **median** | | | | | | | |
| S6 | 1 | | | | | | | |
| S6 | 2 | | | | | | | |
| S6 | 3 | | | | | | | |
| S6 | **median** | | | | | | | |
| S7 | 1 | | | | | | | |
| S7 | 2 | | | | | | | |
| S7 | 3 | | | | | | | |
| S7 | **median** | | | | | | | |
| S8 | 1 | | | | | | | |
| S8 | 2 | | | | | | | |
| S8 | 3 | | | | | | | |
| S8 | **median** | | | | | | | |
| S9 | 1 | | | | | | | |
| S9 | 2 | | | | | | | |
| S9 | 3 | | | | | | | |
| S9 | **median** | | | | | | | |
| S10 | 1 | | | | | | | |
| S10 | 2 | | | | | | | |
| S10 | 3 | | | | | | | |
| S10 | **median** | | | | | | | |
| S11 | 1 | | | | | | | |
| S11 | 2 | | | | | | | |
| S11 | 3 | | | | | | | |
| S11 | **median** | | | | | | | |

**S2 run header (macOS, 2026-11-14).** App SHA `fab8032d` (inferred: the installed Release binary was built 03:16, three minutes after that merge, and `macos/` has not changed since; the owner could not name the commit). Release build, installed in `/Applications`. Apple M2, 16 GB, macOS 26.2 (25C56), 2560 x 1664 Retina; refresh rate not read. AC power, battery 97 % charging, Low Power Mode off. Tailscale connected. Server version and library: not recorded. One minute warm-up, then three back-to-back five-minute runs (30 samples at 10 s, the first sample dropped). Whether the app was on Home with nothing played since launch was taken on the owner's instruction, not checked by the agent.

**S2 note.** An app left idle on Home used about 23 % of one core and about 2.8 % in WindowServer, steadily across all 90 samples, with only about 1 to 2 idle wakeups per second. A constant load with few wakeups points to something redrawing or computing continuously (an animation or a busy thread) rather than a timer. This is a measurement, not a diagnosis; the SwiftUI instrument and Time Profiler traces are needed to name the cause. The plan's section 3 hypotheses do not predict this on Home, so it is a new finding. The `macos_cheap.sh` wakeups column printed the running IDLEW total (about 38,000) in the first version; the script now reports a rate, and the table above was computed from the raw `top` output with the same formula.

**Gate decisions (P0-2)**

| Gate | Condition (plan section 8.5) | Measured value | Met? |
|---|---|---|---|
| G1 | S5 minus S4, Discair plus WindowServer > 3 points of one core, or power > 20 % higher | | |
| G2 | S7 Discair CPU > 0.5 points above Reduce Motion reference, or any `TimelineView` body evaluations while hidden | | |

**Deeper traces (P0-2, required):** SwiftUI instrument during S3 and S5 (views whose bodies run on a timer); Allocations with generation marks around S8 and S9; Time Profiler during S6. Record the decoded pixel size of the largest images after S8 here: _(blank)_.

## 6. Android results (P0-3)

Device: Galaxy S20 FE at 120 Hz. Emulator numbers are not accepted.

Columns: total PSS, native heap, graphics (from `meminfo`); RenderThread CPU % and main-thread CPU % (from `top -H`); frame percentiles and janky frames (from `gfxinfo`); notes.

| Scenario | Run | Total PSS (KB) | Native heap (KB) | Graphics (KB) | Main thread CPU % | RenderThread CPU % | Frames total / janky | p50 / p90 / p99 frame ms | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 (median of 5 `TotalTime`) | — | | | | | | | | |
| S2 | 1 | | | | | | | | |
| S2 | 2 | | | | | | | | |
| S2 | 3 | | | | | | | | |
| S2 | **median** | | | | | | | | |
| S3 | 1 | | | | | | | | |
| S3 | 2 | | | | | | | | |
| S3 | 3 | | | | | | | | |
| S3 | **median** | | | | | | | | |
| S4 | 1 | | | | | | | | |
| S4 | 2 | | | | | | | | |
| S4 | 3 | | | | | | | | |
| S4 | **median** | | | | | | | | |
| S5 | 1 | | | | | | | | |
| S5 | 2 | | | | | | | | |
| S5 | 3 | | | | | | | | |
| S5 | **median** | | | | | | | | |
| S6 | 1 | | | | | | | | |
| S6 | 2 | | | | | | | | |
| S6 | 3 | | | | | | | | |
| S6 | **median** | | | | | | | | |
| S7 | 1 | | | | | | | | |
| S7 | 2 | | | | | | | | |
| S7 | 3 | | | | | | | | |
| S7 | **median** | | | | | | | | |
| S8 | 1 | | | | | | | | |
| S8 | 2 | | | | | | | | |
| S8 | 3 | | | | | | | | |
| S8 | **median** | | | | | | | | |
| S9 | 1 | | | | | | | | |
| S9 | 2 | | | | | | | | |
| S9 | 3 | | | | | | | | |
| S9 | **median** | | | | | | | | |
| S10 | 1 | | | | | | | | |
| S10 | 2 | | | | | | | | |
| S10 | 3 | | | | | | | | |
| S10 | **median** | | | | | | | | |

**Recomposition counts (P0-3, debug build, Layout Inspector, 10 seconds, counts only):**

| Composable | Count over 10 s during S5 | Notes |
|---|---|---|
| `SlideshowBackdrop` | | |
| Disc | | |
| Playing-bars indicators (three) | | |

**Gate decisions (P0-3)**

| Gate | Condition (plan section 8.5) | Measured value | Met? |
|---|---|---|---|
| G3 (provisional, confirm after A1) | S5 minus S4 RenderThread CPU > 5 points of one core, or 90th-percentile frame time over the frame budget | | |
| G4 | S1 median `TotalTime` > 1000 ms, or the owner judges start-up slow | | |

**Background check (P0-3, S7):** `gfxinfo` frame count flat while backgrounded: _(blank)_.

## 7. Run log

One line per run, in the order run.

| Run ID | Date | Scenario | Script output saved to | Notes |
|---|---|---|---|---|
| | | | | |
