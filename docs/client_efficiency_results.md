# Client efficiency — baseline protocol and results

**Status:** protocol and tables. macOS S2 to S7 (and the S7 Reduce Motion reference) have been measured (2026-11-14); S1 and S8 to S11 and every Android cell stay blank until a Phase 0 step (P0-2 macOS, P0-3 Android) fills it from a real run.
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
| S2 | 1 | 28.20 | 2.90 | 0.72 | 28.25 | 2.90 | 115 MB | Firefox closed, no other audio |
| S2 | 2 | 31.70 | 5.60 | 0.02 | 31.70 | 5.60 | 115 MB | |
| S2 | 3 | 31.80 | 5.40 | 0.02 | 31.80 | 5.50 | 115 MB | |
| S2 | **median** | 31.70 (spread 3.60) | 5.40 (spread 2.70) | 0.02 (spread 0.70) | 31.70 (spread 3.55) | 5.50 (spread 2.70) | 115 MB (spread 0) | Run 1 lower than runs 2 and 3; see S2 note |
| S3 | 1 | 29.05 | 8.60 | 2.71 | 29.20 | 8.70 | 184 MB | Library, playing, window visible, Now Playing closed. Marquee scrolling. |
| S3 | 2 | 29.00 | 8.65 | 2.68 | 29.10 | 8.70 | 183 MB |  |
| S3 | 3 | 38.40 | 32.35 | 2.88 | 38.60 | 32.75 | 190 MB | Playback moved on to a track with a spinning disc in the player bar; likely cause of the jump, not confirmed |
| S3 | **median** | 29.05 (spread 9.40) | 8.65 (spread 23.75) | 2.71 (spread 0.20) | 29.20 (spread 9.50) | 8.70 (spread 24.05) | 184 MB (spread 7) | Run 3 is an outlier; runs 1 and 2 agree |
| S4 | 1 | 26.60 | 33.35 | 2.93 | 26.80 | 33.65 | 207 MB | Now Playing, Photos off, playing; disc spinning throughout |
| S4 | 2 | 21.90 | 31.10 | 2.74 | 22.10 | 31.40 | 185 MB |  |
| S4 | 3 | 21.60 | 30.35 | 2.33 | 21.75 | 30.60 | 208 MB |  |
| S4 | **median** | 21.90 (spread 5.00) | 31.10 (spread 3.00) | 2.74 (spread 0.60) | 22.10 (spread 5.05) | 31.40 (spread 3.05) | 207 MB (spread 23) |  |
| S5 | 1 | 18.80 | 3.30 | 2.01 | 18.85 | 3.35 | 353 MB | Photos on, disc spinning; WindowServer low here and about 29 % in runs 2 and 3 with nothing changed |
| S5 | 2 | 22.05 | 29.50 | 2.81 | 22.25 | 29.80 | 376 MB |  |
| S5 | 3 | 21.80 | 29.10 | 2.74 | 21.90 | 29.35 | 376 MB |  |
| S5 | **median** | 21.80 (spread 3.25) | 29.10 (spread 26.20) | 2.74 (spread 0.80) | 21.90 (spread 3.40) | 29.35 (spread 26.45) | 376 MB (spread 23) | WindowServer bimodal |
| S6 | 1 | 13.75 | 5.60 | 2.04 | 13.80 | 5.70 | 377 MB | Paused, Now Playing open, Photos on |
| S6 | 2 | 14.20 | 5.80 | 1.90 | 14.25 | 5.95 | 377 MB |  |
| S6 | 3 | 13.00 | 2.80 | 1.60 | 13.05 | 2.80 | 377 MB |  |
| S6 | **median** | 13.75 (spread 1.20) | 5.60 (spread 3.00) | 1.90 (spread 0.44) | 13.80 (spread 1.20) | 5.70 (spread 3.15) | 377 MB (spread 0) | Work continues while paused |
| S7 | 1 | 26.80 | 8.65 | 3.05 | 26.90 | 8.70 | 169 MB | Window minimized (AXMinimized confirmed), playing |
| S7 | 2 | 26.70 | 8.90 | 2.63 | 26.80 | 8.95 | 169 MB |  |
| S7 | 3 | 27.50 | 8.80 | 2.52 | 27.60 | 8.85 | 176 MB |  |
| S7 | **median** | 26.80 (spread 0.80) | 8.80 (spread 0.25) | 2.63 (spread 0.53) | 26.90 (spread 0.80) | 8.85 (spread 0.25) | 169 MB (spread 7) |  |
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

**S2 run header (macOS, 2026-11-14).** App SHA `fab8032d` (inferred: the installed Release binary was built 03:16, three minutes after that merge, and `macos/` has not changed since; the owner could not name the commit). Release build, installed in `/Applications`. Apple M2, 16 GB, macOS 26.2 (25C56), 2560 x 1664 Retina; refresh rate not read. AC power, battery 97 % charging, Low Power Mode off. Tailscale connected. Server version and library: not recorded. One minute warm-up, then three back-to-back five-minute runs (30 samples at 10 s, the first sample dropped), started 12:14 after the owner quit and reopened Discair on Home with nothing played.

**Discarded attempts.** (1) 11:45 to 12:00: the app was not on Home (Discair 23.4 %, WindowServer 2.8 %, footprint 212 MB). (2) 12:15 to 12:30: on Home, but Firefox helpers and `coreaudiod` were busy (Discair median 41.8 %, WindowServer 31.6 %). Neither is in the table; raw output is kept outside the repository. The table holds the third attempt (12:33 to 12:48): Firefox closed, nothing else playing audio, Discair reopened on Home earlier by the owner, nothing played.

**S2 note.** On Home with nothing else running, Discair used a median 31.7 % of one core (runs 28.2, 31.7, 31.8) and WindowServer 5.4 % (2.9, 5.6, 5.4), with about 0.02 idle wakeups per second (run 1: 0.72). Almost no wakeups with a high steady load points to continuous rendering or computing, not a timer. The 4-point gap between run 1 and runs 2 and 3, and the WindowServer step from 2.9 to 5.6 %, are not explained; the spread is larger than the plan's other thresholds would like. The cause is not named: a Time Profiler and SwiftUI instrument trace on idle Home is the next step. Comparing S7 (window minimized) would show how much of this is drawing. The wakeups column is now a rate: `macos_cheap.sh` first printed top's running IDLEW total, and was fixed in this PR.

**S2 profile (macOS, 2026-11-14, `sample` 5 s on the running Release build; one sample, not a Time Profiler trace).** Discair read 37.7 % in the same minute. Main thread: about 1,790 of 3,050 samples were idle in the run loop; about 700 were in `CA::Transaction::flush` (display cycle, layout) and about 590 in `ViewGraphRootValueUpdater.render`, almost all in AttributeGraph (`propagate_dirty`, `Subgraph::update`, `UpdateStack::update`). `TimelineView.UpdateFilter.updateValue()` appears under it, with `CupertinoPlayerBar.barRow` and `CupertinoPlayerBar.Line` equality beside it.

**Correction: the marquee lead is not supported.** The first version of this note named `MarqueeLine` (`TimelineView(.animation)`, `CupertinoPlayerBar.swift:394`). The owner confirmed that no title overflowed during S2, and a screenshot of the window showed the bar with a paused track (not "nothing played"; a track was loaded at 3:04 / 5:27), plain truncation of the artist, and an empty middle line, so no `MarqueeLine` was on screen. The `TimelineView` frames in the sample are the 4 Hz `PlaybackClock` driving `line(at:)` (the `Line` equality frames), which does not explain per-frame work. Other candidates visible in that state, none tested: the coloured `PlayerBarGraph` waveform behind the bar, the paused cover, and the "Playing on your phone" banner on Home. Also note S2's "nothing played since launch" step did not hold: a track was loaded in the bar, so the S2 rows should be read as "Home, paused track loaded". A SwiftUI-instrument trace, or toggling each element in turn, is needed before naming a cause. The sample file is kept outside the repository.


**S7 Reduce Motion reference (S7-RM, macOS, 2026-11-14), window minimized, same song, Reduce Motion on:** Discair 24.80, 24.80, 27.10 %, median 24.80 (spread 2.30); WindowServer 3.00 % in all three; wakeups 2.65, 2.74, 3.20 (median 2.74); footprint 180 MB (169 to 181).

**Probes, 1 run of 60 s each (not scenarios; paused track loaded):** Home 35.6 % / WindowServer 23.9 %; Library overview 28.3 / 25.0; Settings 25.8 / 23.6; Settings with facts off 25.8 / 23.7; minimized 25.7 / 23.0. WindowServer was about 24 % in all of them and 3 to 9 % in the later scenario runs; the cause was not found (other apps were closed for probes 4 and 5).

**Main finding (2026-11-14).** Discair uses roughly 25 to 29 % of one core in every state tried: any screen, paused or playing, window visible or minimized, Reduce Motion on or off. Wakeups stay near 2 to 3 per second, so the load is continuous rendering or computing, not a timer. The 5 s `sample` of the minimized window shows the main thread in `NSDisplayCycleFlush` and `ViewGraphRootValueUpdater.render`, nearly all in AttributeGraph, with almost no Discair frames. Only Now Playing with the song paused (S6) is lower, at 13.75 %. What keeps invalidating the SwiftUI graph is not yet identified; needs a SwiftUI-instrument trace.

**Gate decisions (P0-2)**

| Gate | Condition (plan section 8.5) | Measured value | Met? |
|---|---|---|---|
| G1 | S5 minus S4, Discair plus WindowServer > 3 points of one core, or power > 20 % higher | S4 21.90 + 31.10 = 53.00; S5 21.80 + 29.10 = 50.90; difference −2.10 points. Power 53.5 vs 51.3 (−4 %). Footprint 207 → 376 MB (+169 MB) | **Not met.** M5 closes without work. The footprint gain belongs to M3. |
| G2 | S7 Discair CPU > 0.5 points above Reduce Motion reference, or any `TimelineView` body evaluations while hidden | S7 26.80 (26.7 to 27.5) vs S7-RM 24.80 (24.8 to 27.1): +2.0 points; WindowServer 8.80 vs 3.00. No SwiftUI-instrument count taken | **Met by the letter (2.0 > 0.5), marginal:** the run ranges overlap and about 25 points remain with Reduce Motion on. The owner opened M6 on 2026-11-14. |

**Deeper traces (P0-2, required):** SwiftUI instrument during S3 and S5 (views whose bodies run on a timer); Allocations with generation marks around S8 and S9; Time Profiler during S6. Record the decoded pixel size of the largest images after S8 here: _(blank)_. None of the three traces has been taken; the `sample` findings above are not a substitute.

## 6. Android results (P0-3)

Device: Galaxy S20 FE at 120 Hz. Emulator numbers are not accepted.

Columns: total PSS, native heap, graphics (from `meminfo`); RenderThread CPU % and main-thread CPU % (from `top -H`); frame percentiles and janky frames (from `gfxinfo`); notes.

| Scenario | Run | Total PSS (KB) | Native heap (KB) | Graphics (KB) | Main thread CPU % | RenderThread CPU % | Frames total / janky | p50 / p90 / p99 frame ms | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 (median of 5 `TotalTime`) | — | | | | | | | | |
| S2 | 1 | 28.20 | 2.90 | 0.72 | 28.25 | 2.90 | 115 MB | Firefox closed, no other audio |
| S2 | 2 | 31.70 | 5.60 | 0.02 | 31.70 | 5.60 | 115 MB | |
| S2 | 3 | 31.80 | 5.40 | 0.02 | 31.80 | 5.50 | 115 MB | |
| S2 | **median** | 31.70 (spread 3.60) | 5.40 (spread 2.70) | 0.02 (spread 0.70) | 31.70 (spread 3.55) | 5.50 (spread 2.70) | 115 MB (spread 0) | Run 1 lower than runs 2 and 3; see S2 note |
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
