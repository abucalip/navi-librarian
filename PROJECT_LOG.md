## 2026-11-13 — Radio stage 2, S2-1 items 4 to 6: rules, stations model, navigation (PR #1050)

- PR [#1050](https://github.com/abucalip/navi-librarian/pull/1050), merged as `579fbc9268d146674d17e71ebb22754fc3603334`. `macos/Sources/DiscairUI/Model/Stations.swift`: `StationRules` (row sentence, tag chips, tag checks) and `DownloadState` (S2.7 table, Owned first), pure. `StationsModel` (`AppState.stations`, behind a `StationsSource` protocol): list in server order, live titles, tag filter, loading/empty/error states, S2.5 polling (list once a minute, titles every 15 s) driven by `pageVisible`; favourite and tag changes show at once, send, then reload, and a refusal restores the old value with the server's sentence. `Screen.stations` and the sidebar row "Radio" under Library. No server change.
- Changed from the plan: no Go/View menu entry (no other page has one; E2 not chosen). `CupertinoStations` is a placeholder (title and count) so the new `Screen` case compiles. `pageVisible` follows the screen only; window hidden or minimised comes with the page.
- Tests actually run: `swift test --filter "StationRulesTests|StationsModelTests"` passed locally, 37 tests. Full suite not run (owner rule). No macOS CI exists. Nothing was looked at in a window; no render test yet (item 7).
- Not done: S2-1 items 7 to 10 (the page, Edit Tags, states, render test).

## 2026-11-13 — Radio stage 2, S2-1 items 2 and 3: client calls and tests (PR #1049)

- PR [#1049](https://github.com/abucalip/navi-librarian/pull/1049), merged as `8695091a78ce981ff26a703138d6490dd8e53e5d`. `macos/Sources/DiscairLibrarian/RadioClient.swift`: `radioStations`, `radioNow(station:)`, `radioNowAll`, `setRadioFavourite`, `setRadioTags`, `radioLogo(station:size:)`, `radioScrobbling`, `setRadioScrobbling`, `uploadRadioLogo`, `resetRadioLogo`, `radioSettings` (`RadioSettings`, `RadioLogoSize`). No server change.
- `LibrarianClient` send path takes an optional content type (default JSON) so a logo upload sends the raw image; existing calls unchanged. An unreadable `/now` body reads as unavailable; an empty or over-2 MB logo is refused before sending.
- Tests actually run: `swift test --skip-update --filter "RadioClientTests|RadioDecoderTests"` passed locally (all radio fixtures covered, plus paths, bodies, id encoding, refusals, 401 re-login on a write). Full suite not run (owner rule). Required CI (compile, container-smoke, test-and-build, validate-container) passed; no macOS CI exists, so the Swift tests were not run there.
- Not done: S2-1 items 4 to 10 (`StationRules`, `StationsModel`, navigation, the page, Edit Tags, states, render test).

## 2026-11-13 — Radio stage 2, S2-1 item 1: decoders (PR #1048)

- PR [#1048](https://github.com/abucalip/navi-librarian/pull/1048), merged as `8c17aaae5a7a1b8dc770063e72b1dfdfdec4971c`. `macos/Sources/DiscairLibrarian/Radio.swift`: `RadioStation` (no `stream_url`; description, debug description and mirror leave the address out), `RadioNow` with `RadioNowState` (unknown words decode as `unknown`), `RadioNowAll`, `RadioScrobbling`; lossy list decoding.
- Tests actually run: `swift test --skip-update --filter RadioDecoderTests`, 9 passed. Full suite not run (owner rule). No macOS CI exists.
- Not covered yet: the client calls and their per-fixture tests (`RadioClientTests`) and the `radio_station_favourite`, `_tags` and `_logo` fixtures, which belong to item 2.
- Next: S2-1 items 2 to 10.

## 2026-11-13 — Radio stage 2 documents, S2-0 (PR #1047)

- PR [#1047](https://github.com/abucalip/navi-librarian/pull/1047), merged as `567932f50c6a1053e3337deea3543ff55deeb388`. Docs only: `RADIO_PLAYBACK_CONTRACT.md` section 5 (owner choices, corrections, request budget, live playback rules, Download states, slices) and section 11 (owner's deployment report); `MACOS_CLIENT_CONTRACT.md` scope and window list; `macos/DESIGN.md` "Radio (stage 2)"; `ACTIVE_WORK.md` slice lines.
- Checks: relative links in the four files resolve; `git diff --check` clean. No code, tests or CI-relevant files changed.
- The owner's deployment checks are recorded as reported by the owner; not re-run by the agent.
- Follow-up on `main` (docs only, same rule): the active queue now says stage 2 started and S2-0 merged, with this log entry.
- Next: S2-1 (stations, Radio page, favourites, tags) on the Mac.

---

## 2026-11-13 — Archive completed proposals and plans

- Reviewed the current GitHub `main`, recent commits, open PR search results, the project status and active-work queue, requirements, development workflow, test plan, and the candidate proposal/plan documents.
- Moved the full contents of eight closed documents into `docs/archive/completed/`: album and artist page redesign records, album paths, Android art themes, colour palettes, Brut layouts, hard-coded taste replacement, and artwork.
- Kept short pointer files at the original paths because source comments, tests, contracts, or documentation refer to those paths. Updated active-work links and the archive index. Updated the project-status check date and archived palette reference.
- Completion means the planned implementation/build slices are merged; it does not claim outstanding owner device/browser checks, publication, deployment, or runtime verification. Those gates remain explicitly recorded in the active queue and archived document status.
- Documentation-only change, committed directly to `main` under the repository workflow. No application code, tests, configuration, provider traffic, publication, or deployment changed. No application tests or CI were run because no executable files changed.

---

## 2026-11-13 — Colour palettes P4 and P5: Flow night palettes and closeout (PR #1045)

- PR [#1045](https://github.com/abucalip/navi-librarian/pull/1045), merged as `8c10438897f3b16873916848149bde1f3c636028` from head `05967dc67a07872ec191e1cbc82d4d179436b0b7`; required CI passed (compile, container-smoke, test-and-build, validate-container). `Palette.kt` gained `FlowEmber`, `FlowMoss`, `FlowPlum` (in `Palettes.Dark`, after the Soft Brut night palettes). `FlowRules.chevron` has their greys; `FlowRules.barHairline` (new) is white at 10% on a dark palette and black at 8% on a light one, used by `flowBar`. The wash behind the album and player was checked and left as is: artwork tints are always dark, and a dark palette uses them unchanged. P5: `ACTIVE_WORK.md`, `PROJECT_STATUS.md`, this log and `docs/palettes.md` updated; `android/DESIGN.md` has a short palettes note.
- Verified, filtered (JDK 17): `FlowTest` (16), `PaletteTest` (19, counts 42/25/17), `SoftBrutTest` (16), `ExistingLayoutsTest` (3), all passed. Full suite not run. Not seen on a device; no screenshot comparison with the palette PNGs.
- Palettes plan closed (P1 to P5 merged). Next action: the owner's phone check of the 13 palettes.

## 2026-11-13 — Colour palettes P2 and P3: Soft Brut night and Flow day palettes (PR #1044)

- Merged as `e3c804eafa2c5ef608e99646888a3ddceefe7907` from head `e960749b25638ede830db30cb59c35ec0cbf51c6`; required CI passed (compile, container-smoke, test-and-build, validate-container). `Palette.kt` gained `SoftBrutMidnightMint`, `SoftBrutPlumPeach`, `SoftBrutNavySky` (in `Palettes.Dark`) and `FlowForest`, `FlowRaspberry`, `FlowViolet` (after `Flow` in `Palettes.Light`). Cover Stack content on an accent fill now uses `onAccent` (nav cell icon, Home and Discover tags, Discover small buttons). `FlowRules.switchOff` and `FlowRules.chevron` replace the two Flow literals; the current `flow` palette keeps its values.
- Verified, filtered (JDK 17): `SoftBrutTest`, `FlowTest`, `PaletteTest` (counts 39/25/14), `ExistingLayoutsTest`, `AppearanceRulesTest`. Full suite not run. Not seen on a device; no screenshot comparison. On night palettes `accentText` is the accent (it passes 4.5:1 on the dark page), so the test asserts that instead of `text`.
- Next action: P4 (Flow night palettes, the bar hairline and the night checks of section 5.3).

## 2026-11-13 — Colour palettes P1: Soft Brut day palettes (PR #1043)

- Merged as `398cbb0ba925c9875d1f725ded595f9705414c24` from head `6628c4f5aaacb0d7d3ffe52e634df5acc9b38dee`; required CI passed (compile, container-smoke, test-and-build, validate-container). `Palette.kt` gained `SoftBrutMint`, `SoftBrutPeach`, `SoftBrutSky`, `SoftBrutLemon` (values from `docs/design/android-art-themes/palettes/roles.md`), listed after `SoftBrut` in `Palettes.Light`. No screen code changed.
- Verified, filtered (JDK 17): `SoftBrutTest` (12, new cases for spec values, shared status colours, contrast floors), `PaletteTest` (19, counts 33/22/20), `ExistingLayoutsTest`, `AppearanceRulesTest`. Full suite not run. Not seen on a device; no screenshot comparison with `docs/design/android-art-themes/palettes/`.
- Next action: P2 (Soft Brut night palettes and the `onAccent` audit), then the owner's phone check.

## 2026-11-13 — Paths Trail steps 3 to 5: artist sheet, artist pane bodies, album sheet (PR #1031)

- Merged as `04afccf076e9a469c90c08dc5a4d183b4edef623` (steps 1 and 2 had merged in PR #1030). Both Paths sheets now show the Trail from `docs/pathsredesign.md`: header with the start's picture, text tabs with a mark, links with their steps under them, a step that opens in place. `PathDetail`, `AlbumPathDetail`, the Back button, "Step n of N" and the arrows are removed; Back closes an open step first; the saved step stays an index into the server's list. Pane bodies lose their hero rows (the opened step's 72dp header carries them) and their cards sit on the sheet's ground. Sideman and Scene rows say the library state. New `TrailEntry`, `entries()` and `TrailList` (scrolls an opened step into view).
- Verified, filtered (JDK 17): `PathTrailTest` (new cases), `PathsTest`, `AlbumPathStepsTest`, `AlbumPathsTest`. Full suite not run. Not seen on a device.
- Next action: step 6 (`AlbumStep.detail` without the via, with `AlbumPathStepsTest`), the `Text` on `AccentDim` contrast case, then the owner's phone check (section 10 of the proposal).

## 2026-11-13 — Art themes F4 part 1: Flow Now Playing, Queue and Lyrics (PR #1026)

- Merged as `96b2162dfb6e5bd97a6df17c2eb831ff0c2322de` from head `c6cb1a3bfdae41010e2fb412b575588cf7c53b73`; required CI passed (compile, container-smoke, test-and-build, validate-container). `ui/player/FlowNowPlaying.kt` (top bar, 312dp cover at level 3 depth over the pastel wash, plain transport with a round Play, Queue/Lyrics/Equalizer/Crossfade entries), a Flow branch in `SeekBar` (4dp line, round thumb), a `flow` option in `CoverStackLyricsPanel`, one `flow` branch in `NowPlayingSheet`. Queue and Lyrics open as a sheet over Now Playing, as Soft Brut's now do (PR #1017), not as the full pages the mockup draws. Not drawn: the heart (no favourite action) and Sonic path (Crossfade takes its slot). Kept beyond the mockup: quality tag, lyric/fact line, status and sign-in, Earlier songs, long-press row actions, Track images, the sound graph. Other themes unchanged.
- Verified, filtered (JDK 17): `FlowPlayerRulesTest` (new), `FlowTest`, `ExistingLayoutsTest`, `CoverStackPlayerRulesTest`. Full suite not run. Not seen on a device; no screenshot comparison with `flow/player`; the Photos switch over the lyrics is untested.
- Next action: the owner checks Now Playing, Queue and Lyrics on the phone; then the rest of F4 (Radio, Downloads, Stats, Server, Settings, Equalizer, Crossfade).

## 2026-11-13 — Art themes F3 part 2: Flow Discover, Library and Search (PR #1025)

- Merged as `867fc559f9ae6781a46c74e6734b137f38a2b91a` from head `c4ded7e22630f709d67d47247879ccbc78efc17c`. Flow pages from `flow/discover` and `flow/library-search`, behind `isFlow()`; other themes unchanged. Details and differences from the mockups in `docs/ACTIVE_WORK.md` section 2l.
- Verified, filtered (JDK 17): `FlowPagesRulesTest` (new cases), `FlowTest`, `ExistingLayoutsTest`, `SoftBrutTest`, `InsightsTest`, `DiscoveryTest`, `NavRulesTest`. Full suite not run. CI result on the final head not re-checked by the agent. Not seen on a device; no screenshot comparison with the mockups.
- Next action: the owner checks Discover, Library and Search on the phone; then F4 (Flow player and the rest).

## 2026-11-13 — Art themes F3 part 1: Flow Album, Artist and Genre, and the bar blur (PR #1024)

- Merged as `70567d503a16ab50980a5e752b398d94ecb6d6b8` from head `2ab4ee84c8afeac3d94e5546537a586a023cbe2a`. Flow pages from `flow/album-artist-genre` (wash on the album, full-width photo on the artist, Paths beside Play, white status bar icons over the photo, genre grid) and the D3 bar blur on the navigation capsule and mini player. Other themes unchanged. Details in `docs/ACTIVE_WORK.md` section 2l.
- Verified, filtered (JDK 17): `FlowPagesRulesTest` (new), `FlowTest`, `ExistingLayoutsTest`. Full suite not run. CI result on the final head not re-checked by the agent. Not seen on a device; no screenshot comparison with the mockup.
- Next action: the owner checks the album wash, the blur and the artist status bar on the phone; then F3 Discover, Library and Search.

## 2026-11-13 — Art themes F1 follow-up: Flow grouped list and small controls (PR #1021)

- Merged as `7648531aba224cf5b4a188561176d5e432ad2ac2`. `FlowKit.kt` gains `FlowGroup`, `FlowListRow`, `FlowIconTile`, `FlowCircleButton` and `FlowTag` from `flow.css`; depth levels, capsule buttons and chips were already in #1020. No screen uses them yet.
- Verified, filtered (JDK 17): `FlowTest` (new depth and row-number test) and `ExistingLayoutsTest`. No screenshots; not seen on a device.
- Next action: F2 (Flow Home).

## 2026-11-13 — Soft Brut fixes batch 1 and Today's picks from the week's Current tastes lists (PR #1017)

- Merged as `b855d91c5d6724927eb8f892b2a1e40d0070f98b` from head `b8399386944dfd4031986ac3500230532417a8be`. Android (Soft Brut): genre on the same line as year and song count (album, artist); Queue and Lyrics open as sheets over Now Playing (`CoverStackPanel`); radio Now Playing sheet fills the screen, and the Paths step bar's extra rule is hidden in Soft Brut; artist Play narrowed with a Paths button (new `PlayerIcons.Paths`) beside Shuffle; album Paths replaces the album-level download; Home Recently added is a sideways row of the last 30 days, link "More" opens the full list.
- Both clients: `/api/dashboard-picks` draws only from the last 7 days of Current tastes lists and reshuffles on every request. New `discovery/lens_week.py` and `app/services/lens_week_picks.py` keep each day's list under `lens_week:current_tastes:<day>` (written on lens refresh and on read; not pruned); no list means empty picks. `build_dashboard_picks` is no longer called by the route. macOS Home refetches picks on each visit after the first (`LibraryModel.reshufflePicks`); Android reloads on each Home open.
- Verified, filtered: Python `test_lens_week`, `test_dashboard_routes`, `test_dashboard_service`, `test_discovery_lens_storage` (51 passed); Android `CoverStackPlayerRulesTest`, `CoverStackHomeRulesTest`, `SoftBrutTest`; macOS `LibraryModelTests`. Full suites not run. Not seen on a device or the Mac.
- Next action: the owner checks the fixes on the phone and Today's picks on both clients.

## 2026-11-13 — Another booklet button on macOS and Android, `booklets` in the artwork index (PR #1016)

- Merged as `a7f4e658600244282b4fb11b0bb6855aa279c92d`. Server: `intelligence/artwork/index.py` gains `_booklets` (every release's booklet by the existing rule: most pages, then the owned release, then the earlier date, then MBID; at most `BOOKLETS_CAP` = 8) and `to_response` adds `booklets`; `booklet` is unchanged and equals the first entry. Contract section and the five `artwork_index*.json` fixtures updated. macOS: `ArtworkIndex.booklets` and `bookletViews`, `BookletSheet` takes `booklets` and has the button and notice. Android: `ArtworkIndex.booklets`, `BookletView.others`, `anotherBooklet`, button and live-region notice in `BookletTab`.
- Verified, filtered: Python `test_intelligence_artwork_index` and `test_artwork_fixtures` (40 passed); macOS `BookletTests`, `ArtworkTests`, `NowPlayingArtworkTests`, `EditionPickerTests`, `LinerNoteTests` (51 passed); Android (JDK 17) `BookletTest`, `ArtworkIndexTest`, `NowPlayingArtworkTest`, `DiscoverPeekTest`. Full suites not run (owner rule). Not seen in a window or on a device. Not published or deployed.
- Next action: the owner looks at the button on the Mac and on a device.

## 2026-11-13 — macOS: remove Zine, add Night mode and the Appearance tab (PR #1015)

- Merged as `3fc8d652e32d02964158684684028fcb1f97b5b4`. Deleted `Themes/Zine`, the Anton, Space Mono and Source Serif 4 fonts with the `Resources/Fonts` package resource, the Zine Dock icon, the Theme menu and the Zine branches in the shared chrome; `ThemeID` keeps `cupertino`. Added `CUPalette` (Day, Night, optional accent hue; `CU.*` now reads it), `AppearanceModel` (saved in UserDefaults), `CupertinoAppearance` and a `SettingsTab.appearance`. `RootView` rebuilds the window on a change. Night is `#0B0B0D` with coral `#FF7A8F`; Day keeps `#D61F4A`.
- Verified locally, filtered: `AppearanceTests` (new), `CupertinoTokensTests`, `CommandPaletteTests`, `MiniPlayerTests`, `PipelineDockTests`, `ConnectionsServicesTests`, `GraphExplorerTests`, `OfflineTests`, `ScreenshotTests`, `BugBatchTests`, `LiveScreenshotTests`: 150 passed. Every slider hue reaches 4.5:1 for the text and accent pairs in both modes (5 degree steps). Full suite not run (owner rule); `Package.swift` changed, so `select-tests.sh` selects it.
- Night rendered offscreen for Home, Settings, Library and Album and viewed once; no Night screenshot test, because the palette is process-wide. Not checked: VoiceOver, every screen at every hue, a live window on the Mac. Not published or deployed.
- Next action: the owner runs the full macOS suite and looks at Night in the app.

## 2026-11-12 — Android art themes S4 part 2: Soft Brut Radio, Downloads and Library stats (PR #1012)

- Merged as `4652b1007a4e54c610708d765c2016ba9da7a56e` from head `2d7357e416f4950cd2b80ca7130fa064e00ddfba`. Added `ui/radio/CoverStackRadio.kt`, `ui/downloads/CoverStackDownloads.kt`, `ui/stats/CoverStackStats.kt` and `CoverStackRadioDownloadsStatsRulesTest`; `isCoverStack()` branches in the five screens; Cover Stack-only branches in the shared chart frame, line chart and chart style.
- Verified with JDK 17, filtered: `CoverStackRadioDownloadsStatsRulesTest`, `ExistingLayoutsTest`, `SoftBrutTest`, `ChartMathTest`, `RadioScreenTest`, `DownloadsRulesTest`, `StatsModelTest`. Full suite not run (owner rule).
- Differences from the mockups: 3-month range chip kept; decades stay paired-bar rows; Shelf life keeps its "not available" sentence; Download button words unchanged; Sleep timer and stream status kept on the live sheet.
- Not checked: no screenshots beside the mockups and no device check.
- Next action: the owner checks these on the phone; then Server, Settings, Equalizer and Crossfade, or F1.

## 2026-11-12 — Android art themes S3 part 3: Soft Brut Library and Search (PR #1010)

- Merged as `06d107c0cad9ff30390476cc33e0b4d93c408b43` from head `38f846bc5d79834330e0a2d6506e2c9b93804b3a`. Added `ui/library/CoverStackLibrary.kt`, `ui/search/CoverStackSearch.kt` and `PlayerIcons.Sort`; one `isCoverStack()` branch each in `LibraryScreen` and `SearchScreen`; a few helpers made internal.
- Verified with JDK 17, filtered: `compileDebugKotlin`, `ExistingLayoutsTest`, `SoftBrutTest`. Full suite not run (owner rule).
- Differences from the mockup: artist Play and queue actions in a three-dot menu; owned results first within each group; placeholder instead of a floating label.
- Not checked: no screenshots beside the mockup and no device check.
- Next action: the owner checks Library and Search on the phone; then S4 or F1.

## 2026-11-12 — Android art themes S2: Soft Brut Home (PR #1007)

- Merged as `2ea52f6548de9cf49450005876bf900ee918f045` from head `1657a6e9fddd79ca89a606e834cf183e220a62a8`. Added `ui/home/CoverStackHome.kt` and `CoverStackHomeRules.kt`, a `Layout.CoverStack` branch in `HomeScreen.kt`, `onLibrary` in `MainShell.kt`, and an optional shadow offset in `coverStackShadow`. No other theme's Home path changed.
- Verified with JDK 17, filtered: `CoverStackHomeRulesTest`, `HomeArtistsTest`, `SoftBrutTest`, `NavRulesTest`. Full suite not run; no screenshots against the mockup, nothing seen on a device; the composables have no automated test beyond compiling.
- Differences from the mockup: Insight button "Open album" (no Play without a library id); "new this month" is the trailing 30 days; Radio says "Stations" until a song is heard.
- Documents updated: `docs/ACTIVE_WORK.md` section 2l, `docs/PROJECT_STATUS.md`, `docs/ANDROID_ART_THEMES_PROPOSAL.md`. Next: owner phone check, then S3.

## 2026-11-12 — Android art themes S1: Soft Brut palette and shell (PR #1006)

- Merged as `d9417fa7c831c62b64d777ed978066aa30e54640` from head `7e4d2e6838755ffa56b757e03d1135126fa3f981`; compile, container-smoke, test-and-build and validate-container passed. Added palette `softbrut`, `Layout.CoverStack` (`ui/common/CoverStack.kt`, `ui/player/CoverStackPlayer.kt`), the outlined navigation bar and mini player, and layout-guarded branches in buttons, chips, tabs, switch, progress, tags, dividers, snackbar and sheet. `PaletteTest` and `NavRulesTest` were updated for the new theme; every other palette's layout and shape is still pinned by `ExistingLayoutsTest`.
- Verified with JDK 17, filtered: `SoftBrutTest`, `PaletteTest`, `ExistingLayoutsTest`, `NavRulesTest`, `AppearanceRulesTest`, `MotionTest`; `assembleDebug` clean. Full suite not run. No screenshots against the mockups and nothing seen on a device; the new control branches have no automated test beyond compiling.
- D4 taken as proposed (font pair suggested, not forced). D6 still open before F1. Not themed yet: Home, pages, player (S2 to S4).
- Documents updated: `docs/ACTIVE_WORK.md` section 2l, `docs/PROJECT_STATUS.md`, `docs/ANDROID_ART_THEMES_PROPOSAL.md`.

## 2026-11-12 — Android art themes step 0 (PR #1005)

- Merged as `35bb9a75d2d5d5442da3cfb4cce70c50b9401b03`. `ui/home/HomeArtists.kt` (distinct artists from Recent then Frequent, up to 8, unwired), `BrutalShape` now Float with the whole-number constructor kept (D1 as proposed), and `ExistingLayoutsTest` pinning every existing palette's layout and exact shape. `PaletteTest` adjusted for the Float radius. No screen changed.
- Verified with JDK 17, filtered: `HomeArtistsTest`, `ui.theme.*`, `NavRulesTest`; `compileDebugKotlin` clean. Full suite not run; nothing seen on a device.
- Open: D4 (font pair suggested or forced) before S1, D6 (Flow accent `#C2410C`) before F1. Documents updated: `docs/ACTIVE_WORK.md` section 2l, `docs/ANDROID_ART_THEMES_PROPOSAL.md` status and step table.

## 2026-11-12 — Redesign S3: check of D4 (album added dates) and D5 (phone handoff)

- Checked in code and the recorded fixture; no code changed.
- **D4 (added dates):** `GET /api/library/albums` serves `added` on each item, from Navidrome's album `created` (`discovery/search/index.py`, `discovery/search/query.py`). The Android DTO reads it and `RecentlyAdded.kt` uses it. The fixture `android/contract-fixtures/librarian/library_albums.json` has a value on all three items. No server change was needed. The field may be null; clients must treat null as unknown.
- **D5 (phone handoff):** Android did not call `savePlayQueue`. Built in the same PR: `player/NavidromeQueueSaver.kt` (signed `rest/savePlayQueue`, client name `discair-android`), `player/PlayQueueSync.kt` (newest-only send, up to 100 songs from the current one), hooks in `PlayerController` (pause, song change, queue edit, every 30 s while playing), wiring in `AppContainer.kt`, `Subsonic.PHONE_CLIENT`.
- Focused Android tests run locally with JDK 17: `PlayQueueSyncTest` (6), `NavidromeQueueSaverTest` (3), `PlayerQueueSyncTest` (4), `PlayerControllerTest` (22), `NavidromeScrobblerTest` (7); all pass.
- Documents updated: `docs/redesign.md` (sections 9 and 11), `docs/ACTIVE_WORK.md` section 2k.
- Evidence boundary: D4 is static reading and the recorded fixture. D5 is unit-tested only; no live Navidrome call was made, so the `savePlayQueue` request is not yet confirmed against the real server.

## 2026-11-11 — Discair client efficiency proposal

- Added [`docs/client_efficiency.md`](docs/client_efficiency.md), a source-level proposal for macOS and Android CPU, memory and GPU efficiency. It covers the macOS 50 Hz audio ticker and decoded-image cache accounting; Android's per-frame slideshow state updates, Coil hardware-bitmap/cache policy, blur rendering and PDF handling; and ExoPlayer buffer/crossfade measurement.
- GPU guidance: prefer SwiftUI/Core Animation and Compose hardware layers for transforms; consider cached Core Image/Metal or Android RenderEffect only if profiling shows blur is a bottleneck; do not move real-time audio DSP to the GPU without a separate proven design. GPU/texture memory must be counted as part of total memory.
- Baseline source revision: `ce01596fb8f3d6daf615a401e12bf3a5bc38c313`. The four main workflows on that revision passed: Python syntax, container runtime smoke, Docker packaging validation and Docker image validation (publishing paused).
- Evidence boundary: no Instruments, Android Studio Profiler, Perfetto or physical-device/window profiling was run. No application code, settings, artwork behavior or audio buffer values were changed. The proposal is not implementation approval.
- Documentation commits: proposal `950a60089ba8403711f1e102ff71fe20a262ddb2`; status update `6a5d5262735c8a2b6900c5bc03b328629b63a4cd`. Final docs-only closeout and post-push workflow state to be checked on the resulting main head.
- Next: establish repeatable before/after baselines from section 6 of the proposal, then choose one focused optimization slice.

# Project log

## 2026-11-12 — macOS redesign follow-ups F6, F7, F11, F12 (plus F9 and F3 owner decisions)

- F6: Home's Never played tile now opens the Albums tab filtered to never-played albums; tile and list share `HomeDashboard.neverPlayedIndices`. F7: the Services edit sheet's Test asks the service directly with the typed values (`ServiceDraftProbe`, from this Mac); nothing is saved. The server's test routes take no body, so a server-side version was not built. A changed address or username with an empty secret reports that it cannot be tested. F11: `CU.muted/ink/card/fill` aliases removed, backdrop and glass tint are tokens, shell geometry named in `CU.Shell`. F12: `CupertinoTheme.content` is exhaustive over `Screen`.
- Owner decisions built here: F9 (Route and Server contract lines on the Librarian row, from the address and `/api/capabilities` `contract_version` and `generation`) and F3 (work, recording, event and instrument nodes take the sector Crew).
- Tests run (filtered, `swift test --filter`): GraphExplorer, ConnectionsServices, ServicesModel, ServiceDraftProbe, LibrarianStatusLines, HomeDashboard, HomeScreen, CupertinoPages, CupertinoTokens: 142 passed. Not run: full suite, live-data checks, visual comparison against mockups. Route reads "Direct address" for a non-Tailscale address (wording not in the mockup).

## 2026-11-10 — Internet radio playback, slice 5 gap: `in_library` on the Heard list

- PR [#971](https://github.com/abucalip/navi-librarian/pull/971) merged as `5aee5fbd7ded4aa617ab24fdb9697de8abc6ef40`. `GET /api/radio/plays` now adds `in_library` to every play (exact artist and title match through `find_song`), cached per song in `OwnedCache` (found songs kept, misses re-checked after 5 minutes, failed searches not kept, plays without an artist false).
- Tests (focused): two route tests in `tests/test_api_radio_routes.py` plus the existing plays and clear-all tests, passing. Full suite not run by the agent.
- Open: the first Heard list load can run one Navidrome search per distinct song; not seen on a device or against a live library. Not published or deployed.

## 2026-11-10 — Internet radio playback, stage 1 slice 6 (Android reconnect, sleep timer, settings)

- PR [#970](https://github.com/abucalip/navi-librarian/pull/970) merged as `99e33671aa0067ee2f19905dde521e91c25f36cb`. Stage 1 is complete; the deployment gate is next.
- Built: reconnect policy in `RadioPlayback` (drop or 20 s stall, retries after 2, 5, 10, 20, 30 s, then "Station unreachable" with Retry; none in the background or after a pause; relay/station error statuses count as a drop); new generic `SleepTimer` (no timer existed) on the radio Now Playing sheet; Radio settings (scrobbling switch, per-station logo Change/Reset up to 2 MB, app address read only).
- Tests (focused, JDK 17): `RadioPlaybackTest`, `SleepTimerTest`, `RadioTest`, `PlayerControllerTest`, `RadioScreenTest`, all passing. Full suite not run by the agent.
- Open: not seen on a device; a pause during buffering is invisible to the stall watcher and may retry after 20 s; the Heard list lacked `in_library` from the server (fixed in PR #971); `/mobile-design` pass in `android/DESIGN.md` pending.
- Next: record the deployment gate items (image tag, new `radio.sqlite3` tables, logo cache folder, rollback reference) and wait for the owner's authorization.

## 2026-11-10 — Internet radio playback, stage 1 slice 5 (Android playback, live Now Playing, Download and Heard states)

- PR [#969](https://github.com/abucalip/navi-librarian/pull/969) merged as `71ee8602b59005a534be39ee6a9bd77fa319d17d`. Owner merged it; docs closeout follows on `main`.
- Built: a station plays through the existing Media3 service as a live item (`QueueItem.liveUrl`, not saved with the queue; no seek, Navidrome scrobble or duration); `RadioPlayback` asks `/now` every 5 s only while sounding or buffering and updates the title and picture in place (also in the notification and lock screen); Download states (Download, Downloading, Downloaded, Owned, Try again) follow the contract rule, one request per song; new Heard screen; radio Now Playing built like the song sheet (neutral layout for every theme); station tap opens it.
- Tests (focused, JDK 17): `RadioTest` (11), `RadioPlaybackTest` (8, new), `PlayerControllerTest` (22), `QueueCodecTest` (6), `RadioScreenTest` (3). Full suite not run by the agent.
- Open: not seen on a device; in-place notification update relies on Media3 updating the item without a restart; a non-relayed station that redirects may fail (the service client does not follow redirects); `GET /api/radio/plays` does not send `in_library`, so Owned does not show in the Heard list; the `/mobile-design` pass in `android/DESIGN.md` is pending.
- Next: slice 6 (reconnect, sleep timer, settings).

## 2026-11-10 — Internet radio playback, stage 1 slice 4 (Android decoders, Radio page, logos, favourites)

- PR [#968](https://github.com/abucalip/navi-librarian/pull/968) merged as `65ed988b1397002477f38c259eb779ced871b8e0`. Owner merged it; docs closeout follows on `main`.
- Built: `model/Radio.kt` decoders (stations, `/now`, `/api/radio/now`, favourite) read against the shared contract fixtures; repository calls; `ui/radio/RadioScreen.kt` (server logos, favourites first in the server's order, live title strip refreshed every 15 s only while visible, favourite toggle with rollback and message); a Radio row on Home opens it. An unknown `/now` state reads as unreachable.
- Tests (focused, JDK 17): `RadioTest` (8), `RadioScreenTest` (3), `TapeDeckTest`; build passed. Full suite not run by the agent.
- Open: not seen on a device or any theme; the `/mobile-design` pass in `android/DESIGN.md` is pending; not run against the real server. Tapping a station does nothing until slice 5.
- Next: slice 5 (playback service, live Now Playing, Download and Heard states).

## 2026-11-10 — Internet radio playback, stage 1 slice 3 (scrobble on threshold, love)

- PR [#967](https://github.com/abucalip/navi-librarian/pull/967) merged as `ae69fcf0` (head `9f5c9ba3`). Owner merged it; docs closeout follows on `main`.
- Built: `integrations/radio/scrobble.py` sends Last.fm `track.scrobble` and `track.love` directly, signed with `LASTFM_SHARED_SECRET` and `LASTFM_SESSION_KEY`. Scrobbling is off by default (`GET`/`PUT /api/radio/scrobbling`) and cannot be switched on without both keys. `POST /api/radio/plays/{id}/love` works whether or not scrobbling is on. The `ListenTracker` reports each logged play through `on_logged`; the relay hands it to a background thread.
- Once per play: the `scrobbled` flag is claimed before the request, and a failed request is not retried. `radio_plays` gains `scrobbled` and `loved`, added to existing databases with `ALTER TABLE`.
- Deviation: the repository had no Last.fm write code, so the slice added it rather than reusing existing code. Recorded in the contract, section 3.7.
- Tests (focused, run on the branch): `tests/test_radio_scrobble.py` 15 passed; `tests/test_radio_*.py` and `tests/test_api_radio_routes.py` 128 passed in total. Full suite not run by the agent; CI on the PR head.
- Open: `LASTFM_SESSION_KEY` is not in the owner's `config.env`, so scrobble and love cannot run until it is added. The double-count check with Navidrome is by design only; a live check is still needed. Last.fm's guideline (half the track or four minutes) is not applied to radio, which has no length; the owner's 30-second rule stands.
- Not checked: live Last.fm, Docker image, browser.

## 2026-11-10 — Internet radio playback, stage 1 slice 2 (live now holder, /now, /api/radio/now)

- PR [#966](https://github.com/abucalip/navi-librarian/pull/966) merged as `f3a5a2d756ad98d67e0b2b27c72b5b9140e4e093` (head `e12258ef`). Owner merged it; docs closeout follows on `main`.
- Built: in-memory "now" holder (`integrations/radio/now.py`) fed by the relay's `ListenTracker`; `GET /api/radio/stations/{id}/now` and `GET /api/radio/now`, states `ok`, `no_metadata`, `unparsed`, `not_proxied`, `unavailable`, `idle`. A song is logged at 30 seconds of listening, so `play_id` exists while it plays; the rest of the listen is added on change or close (`store.add_listened`). `in_library` and `cover_url` from one Navidrome search per song (`integrations/radio/library_match.py`), cached per song; a failed lookup is retried.
- Decisions recorded in the contract (section 3.2 slice 2 note): `idle` and `unavailable` added to `/now`; `cover_url` only for library songs; `/api/radio/now` items carry `id`.
- Fixtures: eight `android/contract-fixtures/librarian/radio_now_*` files, generated from the real router with a temporary store (not captured from a live server); `captured_at` is the generation time.
- Tests run (focused): `test_radio_*.py` (88, OK), `test_api_radio_routes.py` (25, OK), `test_android_contract_fixtures.py` (6, OK, run after the fixture fix). CI on the final head `e12258ef`: Python syntax check, Container runtime smoke test, Validate Docker packaging, Validate Docker image (publishing paused), Publish Docker release (build only, `push: false`) all passed. Earlier head `2bb2a02` failed the acquisition-regression job on the fixture envelope; fixed in `e12258ef`. Full suite not run (owner rule).
- Open from this slice: not run against a live Navidrome or a real station; the first `/now` for each song makes one Navidrome search; a logged song appears in the Heard list once it passes 30 seconds, even while it still plays; a relay that stops sending data stops showing as live after 20 seconds.
- Next: slice 3 (scrobble on threshold, off by default, and love).

## 2026-11-10 — Internet radio playback, stage 1 slice 1 (server stations list, favourites, tags, logos)

- PR [#965](https://github.com/abucalip/navi-librarian/pull/965) merged as `b3eef2a35eedf57c99b762cd85865e2f5f3499ff` (head `d5f652d0`). Owner merged it; docs closeout follows on `main`.
- Built: stations list fields (`logo_url`, `homepage_url`, `favourite`, `tags`, `last_played_at`, `playable_url`) with favourites-first order; `PUT .../favourite`, `PUT .../tags`; logo resolver (`GET/PUT/DELETE .../logo`: owner override, Radio Browser favicon, homepage icon, generated PNG tile) with on-disk cache and 7-day negative cache; `integrations/radio/safe_fetch.py` (public http(s) only, redirects re-checked, image sniffing, size cap). Additive tables `radio_station_prefs` and `radio_logo_state`.
- Fixtures: five `android/contract-fixtures/librarian/radio_*` files, recorded from a fake Navidrome in a sandbox folder. `test_android_contract_fixtures` now allows PUT.
- Tests run (focused, 92, all passing): `tests.test_radio_stations_contract`, `tests.test_android_contract_fixtures`, `tests.test_api_radio_routes`, `tests.test_radio_stations`, `tests.test_radio_logos`, `tests.test_radio_icy`, `tests.test_radio_log`, `tests.test_radio_ui_contract`, `tests.test_discovery_daily_radio_scope`. Full suite not run (owner rule).
- Open from this slice: Radio Browser endpoint paths are unverified against the live API; logos are not resized (no image library, Pillow not approved); the fetch guard has a DNS-rebinding window.
- Next: slice 2 (live "now" holder, `/now`, `/api/radio/now`, `in_library`, `cover_url`).

## 2026-11-10 — Internet radio playback contract (stage 1, slice 0)

- Docs only, committed directly to `main` per the documentation rule. New `docs/RADIO_PLAYBACK_CONTRACT.md` turns `docs/RADIO_PLAYBACK_PROPOSAL.md` (owner decisions of 2026-11-10) into the server, Android and macOS rules, the slice list and the deployment gate.
- Scope lines lifted to point at the contract: `PRODUCT.md`, `docs/ANDROID_PLAYER_CONTRACT.md`. `docs/MACOS_CLIENT_CONTRACT.md` keeps radio out of scope until stage 2 starts.
- No code, no endpoint, no migration. Checks: link targets exist; no personal names in the new text. No tests run (docs only).
- Next: slice 1 (server stations list fields, favourites, tags, logo resolver and cache).

## 2026-11-10 — Artwork Timeline filmstrip and Atlas disc nodes on macOS (slice 6, idea 11)

- Merged as PR [#958](https://github.com/abucalip/navi-librarian/pull/958), squash `ca38227d0a76788b51dde1b201795ff5da171b95`, and PR [#959](https://github.com/abucalip/navi-librarian/pull/959), squash `a4b3217832ec27101da7b9e1f4f9002e1a7246b2`. macOS only; no server change.
- New: Timeline "Pictures" filmstrip on the selected album card (`ArtworkIndex.filmstrip`, `Chrome/TimelineFilmstrip.swift`); a Discs switch (off by default) for the Atlas place inspector and for album nodes on the Connections graph (`AlbumDisc`, `GraphNodeFace.discs`). Only UUID release groups are asked; nothing is drawn for an album without the pictures.
- Tests actually run, filtered: `swift test --filter` on `ArtworkTests`, `AtlasDiscTests`, `AtlasGeometryTests`, `TimelineGroupingTests`, `ScreenshotTests` (35 pass) and `GraphDiscTests`, `GraphExplorerTests`, `ScreenshotTests` (16 pass). Not run: the full suites. CI: #959 `validate-container` failed once on a Docker Hub 502 (not the change) and passed on re-run. Not seen in a window or against the real server.
- Next: ideas 12 and 13 (liner note of the day, edition check in Get).

## 2026-11-10 — Artwork Paths covers and Same Room on Android and macOS (slice 6, idea 10)

- Merged as PR [#957](https://github.com/abucalip/navi-librarian/pull/957), squash `e84d3327a422a5a1bd422c682c62488d683bbc5a`.
- New: path rows cycle through the album's alternate Front covers (never a PDF, at least two): macOS hover (`Chrome/PathArtwork.swift`, `PathRowThumb`; held still under Reduce Motion), Android long press and a TalkBack action (`ui/common/PathArtwork.kt`, `PathRowCover`), on the album and artist Paths sheets. Same Room (`SameRoomPhotos`) shows the start album's and the step's session photos side by side. Rules in `ArtworkIndex.pathCoverFaces` / `roomPhotos` (macOS) and `model/PathArtwork.kt` (Android). The release group comes from the Librarian album page; no server change.
- Tests actually run, filtered: Android `PathArtworkTest` (5 pass, JDK 17); macOS `swift test --filter ArtworkTests` (30 pass, four new). Not run: the full suites. Not checked on a device or in a window.
- Next: Timeline filmstrip and Atlas disc nodes (rest of slice 6).

## 2026-11-10 — Artwork Discover covers peek on Android and macOS (slice 6, idea 9)

- Merged as PR [#956](https://github.com/abucalip/navi-librarian/pull/956), merge commit `b311115d92839ff9f555ffa52181dadb65d1d9d6` (tested head `7c6942e45be9181a3febfe7ca76564c1d2fa2c92`).
- New: rows show up to three covers (Back, first booklet page never a PDF, Medium) at thumb size. Android: `model/DiscoverPeek.kt`, `ui/common/DiscoverPeek.kt`, a "Covers" control in `RankedRow`. macOS: `Chrome/DiscoverPeek.swift` (hover plus a "Covers" button) in the Cupertino and Zine Discover rows, `ArtworkIndex.discoverPeek`, `DashboardPick` release group fields, `DiscoveryModel` hover state. Release group: `release_group_mbid`, or `mbid` on new releases; non-UUID values are ignored.
- Tests actually run, filtered: Android `DiscoverPeekTest` (6 pass, JDK 17); macOS `swift test --filter ArtworkTests` (26 pass, two new peek cases); `swift build` compiled the whole package. Required CI on the tested head passed: compile, container-smoke, test-and-build, validate-container. Not run: the full suites. Not checked on a device or in a window; Home new-release tiles have no peek.
- Next: Paths covers and Same Room, Timeline filmstrip and Atlas disc nodes (rest of slice 6).

## 2026-11-10 — Artwork artist photo strip on Android (slice 6, idea 8)

- Merged as PR [#955](https://github.com/abucalip/navi-librarian/pull/955), squash `74964145d1dbee98076cc76f19bb143ea28ab49e` (Android only, plus `docs/artwork.md`).
- New: `model/ArtistCollage.kt` (`qualifiesForCollage`, `artistCollage`: the macOS picture rules and round-robin, at most 8 owned albums, 3 per album, 12 in all, nothing under 4), `OwnedAlbum.releaseGroupMbid` (`model/Dto.kt`), `ui/artist/ArtistPhotoStrip.kt` (per-album index lookups in parallel, a row under the bio, each picture opens its album), one line in `ui/artist/ArtistScreen.kt`.
- Tests actually run, filtered, Android with JDK 17: `ArtistCollageTest` (8), `DtoFixtureTest` (8), `ArtworkIndexTest` (11), all pass. Required CI on the PR head passed: compile, container-smoke, test-and-build, validate-container. Not run: the full Android suite (owner runs it). Not checked on a device; not deployed.
- Next: Discover peeks, Paths covers and Same Room, Timeline filmstrip and Atlas disc nodes (rest of slice 6).

## 2026-11-10 — Artwork artist collage on macOS (slice 6, first step)

- Merged as PR [#953](https://github.com/abucalip/navi-librarian/pull/953), squash `caccc9746f133c12e1946e8826a4f44ca3c9f481` (server), and PR [#954](https://github.com/abucalip/navi-librarian/pull/954), squash `cfd674c3ac5b9530bbb8103ac1b1385f33c1be2d` (macOS).
- New: `release_group_mbid` on artist-page `owned_albums` items (`discovery/search/query.py`, contract line in `SEARCH_CONTRACT.md`); macOS `ArtistAlbumEntry` reads `id` and `release_group_mbid`, `RelatedModel.ownedGroups`, `ArtworkStore.artistCollage`, `qualifiesForCollage` and `artistCollage` in `DiscairLibrarian/Artwork.swift`, `Chrome/ArtistCollage.swift` (Zine contact sheet, Cupertino banner that rotates and holds still under Reduce Motion).
- Finding: the artist page `albums` section already carries the album id and release group for owned albums, so the Mac does not need the #953 field; it stays for owned albums missing from `albums`.
- Tests actually run, filtered: `tests.test_discovery_search_query`, `tests.test_api_search_routes` (82 pass); macOS `DiscairLibrarianTests` (155 pass, 7 new in `ArtistCollageTests`), `DiscairUITests` (366 pass). Not run: full suites. Not checked in a window; not deployed.
- Next: Android photo strip, Discover peeks, Paths, Timeline and Atlas (rest of slice 6).

## 2026-11-10 — Artwork flip cover and spine strip (slice 3, first step)

- Merged as PR [#949](https://github.com/abucalip/navi-librarian/pull/949), squash `2c29e6986a41cd8ee6b8b34ec0f50612a372fb3e`.
- New: Android `model/CoverFaces.kt` and `ui/album/FlipCover.kt` (swipe or tap, TalkBack action, cross-fade when animations are off); macOS `Chrome/FlipCover.swift` (click, Reduce Motion cross-fade, Cupertino and Zine headers, 12 pt Spine strip), `ArtworkIndex.coverBackFaces`, and `release_group_mbid` read from the album page into `RelatedModel`. No Back image means no flip.
- Tests actually run, filtered: Android `CoverFacesTest`, `ArtworkIndexTest`; macOS `ArtworkTests`, `FlipCoverTests`, `BugBatchTests`. Not run: full suites, lint, release build. Not checked on a device or in a window; the strip has no test.
- Open: the owned release is not passed to the index lookup, so a Back from another edition can win over the owned one.
- Next: booklet and zoom.

## 2026-11-10 — Artwork client decoders and image store (slice 2)

- Merged as PR [#948](https://github.com/abucalip/navi-librarian/pull/948), squash `d1ac2f79a6a4b5dddaa79b333c811dac9ae2be6e`, tested head `a3755269862a3d13492707ffbaf458a1ce79494f`; required CI passed (compile, container-smoke, test-and-build, validate-container). Not published or deployed. Clients only; server untouched; no screen uses the new code yet.
- New: Android `model/Artwork.kt` (`parseArtworkIndex`, `loadArtworkIndex`), `Repository.artworkIndex` and `artworkImageUrl`; macOS `DiscairLibrarian/Artwork.swift` (`ArtworkIndexResult`, `ArtworkPicture`, `LibrarianClient.artworkIndex` and `artworkImage`) and `ArtworkStore` album images. `unavailable` is never read as `empty`; one bad entry never drops the rest; comments stay plain text; `pending` is read as `not_loaded` to stay compatible with [`efficiency.md`](docs/efficiency.md) part E.
- Tests actually run, filtered: Android `app.discair.ArtworkIndexTest` (11 pass), macOS `ArtworkTests` (8 pass). Not run: the full suites (owner rule). Not covered: the macOS image store has no unit test; nothing checked on a device or in a window.
- Environment note: Gradle needs JDK 17 here (the default JDK 27 breaks the Kotlin compiler) and a copied `android/local.properties` in a worktree.
- Open risk: the contract types `image_id` as an integer while the efficiency plan may move to content-addressed storage; recorded as a rule in `docs/artwork.md`.
- Next: slice 3, flip cover, booklet and zoom (ideas 1 and 2).

## 2026-11-10 — Artwork fixtures, contract section and `format` (slice 1, third step)

- Merged as PR [#947](https://github.com/abucalip/navi-librarian/pull/947), squash `2de5b2931ecdff17a89f07f0e0f48382d15b57e4`, tested head `f78284cad98e2769d11c9b24a085a319b97a7f7e`; required CI passed (compile, container-smoke, test-and-build, validate-container). Not published or deployed. Server and docs only; no client uses the routes yet.
- New: `format` (`jpg`, `png`, `gif`, `webp`, `pdf`) on each index entry, read from the CAA image URL (default `jpg`, as the store does); fixtures `android/contract-fixtures/librarian/artwork_index*.json` (`ok`, `empty`, `unavailable`, `not_loaded`, `truncated` as `partial`, `release_cap`, `served_cap`, and a `400`), written by `scripts/write_artwork_fixtures.py` through the real route with canned provider answers; `tests/test_artwork_fixtures.py`, which rebuilds them to catch drift; and the "Album artwork" section of `docs/SERVER_V2_CONTRACT.md`.
- The fixtures are synthetic: invented ids, dates and comments, no provider traffic and no owner data, so shapes are exact and values are not real. The two cap fixtures use lowered caps (2 releases, 3 images) to stay small. They should be replaced by recorded ones only if the owner approves a live capture.
- Finding: the route rebuilds the index from the per-release cache, where a release the build did not reach counts as failed, so a build that stopped on its time bound is served as `partial`; `time` never reaches clients. Decided with the owner: drop `time` from the docs rather than change the route. The service still sets `time` internally. No `time` fixture.
- Tests actually run, filtered: `tests.test_artwork_fixtures`, `tests.test_android_contract_fixtures`, `tests.test_api_artwork_routes`, `tests.test_intelligence_artwork_index`, `tests.test_intelligence_artwork_cache` (71 pass). Not run locally: the full suite (owner rule; CI ran it).
- Next: slice 2, Android and macOS decoders for the index and the image store, following the album paths decoder pattern (PR #931).

## 2026-11-10 — Artwork cache and endpoints (slice 1, second step)

- Merged as PR [#946](https://github.com/abucalip/navi-librarian/pull/946), squash `f5ea0f6c9ba52c949739cd6dc0c1f50432807cde`, tested head `d1fc1a91963917ae17e9747dd17623abd77fbcee`; required CI passed (compile, container-smoke, test-and-build, validate-container, validate-release-workflow). Not published or deployed. New: `intelligence/artwork/store.py` (SQLite plus `images/` under `DATA_DIR/artwork`), `service.py`, `fetchers.fetch_image`, and `app/api/artwork.py` (`GET /api/artwork/index?rgid=&release=`, `GET /api/artwork/image/{image_id}?size=thumb|display|full`). Session auth comes from the app login middleware (tested: both routes answer 401 without a session). No client uses them yet.
- Index: `not_loaded` (with `retry_after` 5) until a background worker (one at a time, one build per group) has built the group; builds never run in a request. Per-release answers cached with the documented TTLs (30 d images, 7 d empty, 1 d partial, 15 min then 1 h for errors, up to 10% jitter); an errored release or group is stored as `unavailable`, never `empty`. An expired group is served stale and refreshed in the background.
- Images: served from disk; a miss is fetched once (per-image lock, one download at a time), checked by file signature (JPEG, PNG, GIF, WebP, and PDF originals, kept at the owner's request because booklet scans such as Somethin' Else's come as PDFs; a PDF is only stored as `full` and is served with a sandbox CSP; anything else rejected; the upstream Content-Type is not trusted), size-limited per size (2, 4, 100 MB) and stored. Redirects are limited to the CAA and archive.org hosts (existing `_SafeRedirect`). The 1.5 GB budget is shared; eviction drops unprotected full-resolution files first, then least recently used, then protected files last. The best front of a group whose owned release was passed is protected. A file larger than the budget is not stored.
- **Decisions made here, for the owner to confirm:** no image library is in `requirements.txt`, so there is no resizing: `thumb` is the CAA 250 px file and `display` is the CAA 500 px file (not 640); `full` is the original. Adding Pillow would be needed for 640 px. The warm-up is not built (open decision 3 is unanswered). The per-host pacer paces the first host (coverartarchive.org); redirected archive.org hosts are not separately paced. The owned release comes from an optional `release` query parameter; nothing reads the library yet to supply it.
- Tests actually run, filtered: `tests.test_intelligence_artwork_cache`, `tests.test_api_artwork_routes`, `tests.test_intelligence_artwork_index`, `tests.test_intelligence_artwork_fetchers` (56 pass, fake openers, no network). Not run: live CAA image fetch, the full suite (owner rule). Test count after the PDF change: 58. Real byte sizes are still unmeasured.
- PDF booklets: the archive makes thumbnails of PDFs, so `thumb`/`display` are first-page previews and clients need a PDF viewer (PDFKit, `PdfRenderer`) for `full` only; described in `docs/artwork.md` idea 2. Open follow-up: the index entry carries no file `format` yet; add it before client decoders. Thumbnails of a real PDF not yet fetched.
- Next: fixtures (`ok`, `empty`, `unavailable`, `truncated`, plus `not_loaded`) and the contract section.

## 2026-11-10 — Artwork index and merge, and provider fetchers (slice 1, first step, PR #945)

- Merged as `e5131a631eb9f7fb928e18430538264a8c10f526` from tested head `3f2d7477761fb061f57bfdf6360ad26b1839f32c`; required CI passed (compile, container-smoke, test-and-build, validate-container). New package `intelligence/artwork/`; `navidrome_server.py` untouched. Not wired to any endpoint or client; not published or deployed.
- `index.py`: merges the CAA images of every release in a release group (owned release first, then newest; 60-release ceiling, 180 s bound, resume from cached per-release answers), collapses an image shared by several releases, picks the best front (approved, Front type, larger side, earlier date, image id; none when no Front image), per-type slots (owned release preferred, fallback labelled with its edition), the booklet as one ordered set from the release with most pages, 400 stored and 250 served caps, and `truncated` with a reason (`release_cap`, `time`, `partial`, `stored_cap`, `served_cap`). A failed release is `unavailable`, never `empty`.
- `fetchers.py`: one paged MusicBrainz browse per group (`inc=media`), one CAA index per release, per-host 1 request per second pacing, 429/503 back-off (`Retry-After`, else 60 s doubling to 15 minutes), redirects only to coverartarchive.org and archive.org over https, no image bytes.
- Checked live: the release browse rejects `inc=cover-art-archive`, so cover-art counts are unavailable and no release request is skipped.
- Tests actually run, filtered: `tests.test_intelligence_artwork_index` and `tests.test_intelligence_artwork_fetchers` (31 pass, fetchers use a fake opener, no network). Full suite not run (owner rule).
- Limits: CAA indexes carry no width or height, so "larger side" only applies when present; booklet pages per release and image byte sizes are still unmeasured; the time and cache TTL behavior has no persistent per-release cache yet.
- Next: slice 1 cache and endpoints (1.5 GB budget, eviction, byte validation, auth), then fixtures and the contract section.

## 2026-11-10 — Artwork caps, TTLs and rate limits set from the probe (slice 0 closed)

- Documentation only, committed directly to `main`; no code, tests or CI. Set in [`docs/artwork.md`](docs/artwork.md), section "Limits (set from the probe)": 60 releases fetched per group (probe max 59), 400 images stored and 250 served (probe max 341, p90 133) with `truncated_reason`, a 180 s build bound (probe max 120 s), 100 booklet pages shown. TTLs: 30 days with images, 7 days empty, 1 day partial, 15 minutes then 1 hour for errors (never stored as empty). One shared 1 request per second queue per host, foreground before warm-up, warm-up capped at 600 requests per day, 429/503 backoff. Caps limit what is served, not what is fetched.
- Limits: from a 30-group sample. Booklet pages per release, image byte sizes, the 640 px source and whether the MusicBrainz batch lookup exposes cover-art counts (would skip the 21.5% empty releases) were not measured; slice 1 records them. Not published or deployed.
- Next: slice 1 (server index and cache), Opus 5.5.

## 2026-11-10 — Artwork probe (slice 0) merged (PR #944)

- Merged as `42f118f4b084b860af36fcf152adf9f161f9a14e` from tested head `96493c41e95541a3b9b2e579db2e60ea353ac4ea`; required CI passed (compile, container-smoke, test-and-build, validate-container). Adds `scripts/artwork_probe.py` for slice 0 of [`docs/artwork.md`](docs/artwork.md). Not wired into the server or any client; `navidrome_server.py` untouched.
- Live run (30 owned release groups, about 40 minutes, 1 request per second per host, index JSON only): all 30 groups have an image, 21 have a non-Front type; releases per group median 5.5, p90 23, max 59; unique images per group median 7.5, p90 133, max 341; 21.5% of release indexes empty, 0.3% errored. Full numbers in `docs/artwork.md`. The owner approved per-type slots (booklet as a single-release set) on the same day.
- Tests: `py_compile` and a re-run of `summarize()` on the saved results; no unit-test file (live network calls); full suite not run (owner rule). Probe sample is small (30 groups). Not published or deployed.
- Next: set the caps, TTLs and rate limits from the results, then slice 1 (server index and cache).

## 2026-11-10 — Album paths build closed

- All album path kinds are built, wired and shown on both clients (PRs #921 to #937). Docs only in this closeout; no code or tests run.
- Left for the owner after deploy, not queued: screens on a device and in a window; Same Room probe thresholds re-run; Neighbours by Ear wider-sample re-measure.
- Not published or deployed.

## 2026-11-10 — Path row covers merged (PR #937)

- Merged as `68f1a97d10300ba3468f530d177df4092fdd0b2c`. Path rows no longer show placeholders. Android: `ownedAlbumArtwork` (exact title and artist match in the library list, cached) and `PathAlbumCover` put the library's own cover first on the artist and album Paths sheets and panes, then fall back to the `/api/artwork` lookup for albums not owned. macOS: `PathsSheet.item(_:)` borrows the library album's cover id by title and artist, or looks the cover up for albums outside the library. No server or contract change (public responses still carry `mbid` only).
- Tests: Android compile (Homebrew JDK 17) plus `AlbumPathStepsTest`, `AlbumPathsTest`, `PathsTest`, `LibraryViewModelTest`; macOS build plus `PathsModelTests`. No new unit test for `ownedAlbumArtwork`.
- Limits: not checked on a device or in a running window. Not published or deployed.

## 2026-11-10 — Same Room and Gaps client tabs merged (PR #936)

- Merged as `02816e448b6f928102a50814a01d37b49f741eca`. Android and macOS offer Same Room and Listen-through Gaps on the album Paths sheet; decoders read `play` and `history`. Gaps labels only (order is the server's) and says in words when history is thin or unavailable, what was left out, and when every album was already played.
- Tests: filtered only. Android `AlbumPath*` and `PathsTest*` (JDK 17); macOS `AlbumPathsTests` and `PathsModelTests` (24 passed). An old Android test now uses `paths_error_album_unknown_entity` (its 501 fixture was removed in #933).
- Limits: not checked on a device or in a running window; 7 segments in the 820 pt macOS sheet may be tight. Not published or deployed.
- Next: look at the screens; re-run the Same Room probe thresholds; Neighbours by Ear re-measure.

## 2026-11-10 — Same Room album path merged (PR #933)

PR [#933](https://github.com/abucalip/navi-librarian/pull/933), squash `96053809ed55dce79a6c0324dcb3afd44aea7dd5`. `album_room` is built in `intelligence/graph/album_paths.py` and served by `GET /api/knowledge/paths?type=release&kind=album_room` (it no longer answers `501`; `album_gaps` still does). Owned albums with a recording made at a place or event that also holds a recording of the start (`recorded at`, `mixed at`, `engineered at`, credit-grade only, never an area); reason `recorded_at`; hub places keep 50 albums with the rest in `capped[]`; overlap with the artist paths dropped. Fixtures `paths_album_room.json` and `_empty` recorded through the route on a scratch copy of the store; the stale `paths_error_album_room_not_built.json` removed. Contract and proposal updated. Filtered tests only; full suite and required CI ran on the PR. The probe thresholds were not re-run on the built path. Not published or deployed.
## 2026-11-10 — Album and artist Paths screens merged (PR #932)

PR [#932](https://github.com/abucalip/navi-librarian/pull/932), squash `4b69308f1982f0558600d0f193c11e7e541c0411`. Android album Paths button and sheet; macOS Paths sheet for albums and artists with buttons in Cupertino and Zine and a Paths menu; macOS ticker scrolls long lines right to left; only the playing version of a repeated title is marked (macOS song id, Android track and disc); restored queue songs without a cover id show their album's cover. Filtered tests only: Android `AlbumPathStepsTest`, `AlbumPathsTest`, `PathsTest`, `PlayingNowTest`; macOS `PathsModelTests`, `AlbumPathsTests`, `KnowledgeTests`, `QueueItemDecodingTests`, `SameTitleHighlightTests`. Not run on a device or in a window; the artwork fix assumes old saved queue items lacked a cover id. Not published or deployed. Limits: graph rows have no cover art id from the server; an album outside the library has no Paths button.

## 2026-11-09 — Album paths route and fixtures merged (PR #929)

PR [#929](https://github.com/abucalip/navi-librarian/pull/929), squash `cca08807bc93267f784bdffdbafe851c66e905ca`. `GET /api/knowledge/paths` now serves `album_crew`, `album_guests`, `album_works` and `album_moment` for `type=release`; `album_room` and `album_gaps` answer `501`; a kind/type mismatch is `400`; `release_group` is `404` or `400` until a release-group builder exists (the contract said it selects an album start, a gap to settle). Fixtures recorded through the route: `paths_album_*` (`ok` and `_empty` per kind), four `paths_error_*` album cases, and `sonic_album_neighbours*.json` (`ok`, `empty` with a skipped unanalysed seed, `404`) from a copy of the owner's store and the owner's Navidrome (read-only). Contract section updated. Filtered tests only (paths route, album paths, paths, sonic neighbours, sonic routes, Android contract fixtures); full suite and required CI ran on the PR. Not published or deployed. Not done: `album_gaps` and `album_room` route/fixtures, fixture-based server tests, decoders, client screens, the Sonic wider-sample re-measure.

## 2026-11-09 — Listen-through Gaps filter merged (PR #927)

PR #927, squash `b257a07db070e7f1086732015bedc6d90d6723de`. `intelligence/graph/album_gaps.py`: Studio Crew and Guest List stops filtered to fewer than 2 plays, labelled in a `play` field; never adds stops or reorders; thin or unavailable history returns unfiltered stops marked as such. Filtered tests only; not wired to the route, contract or cache; not published or deployed.

## 2026-11-09 — Neighbours by Ear composition merged (PR #926)

- Squash-merged PR [#926](https://github.com/abucalip/navi-librarian/pull/926) to `main` as `934a1c0786f78f4daa2ce257888ee6b189278e3b`. Adds `intelligence/sonic/neighbours.py` (`album_neighbours`) and `GET /api/sonic/album-neighbours`: up to 8 deterministic evenly spaced seeds (first and last included), unanalysed seeds skipped, reported and replaced (max 16 calls), own album dropped, albums ranked by distinct seeds matched then earliest track year then id, `similarity` never read, 5 s bound gives `truncated: "time"` (not cached), one-hour sonic cache.
- Tests: filtered only, `tests/test_sonic_neighbours.py` (9) and `tests/test_api_sonic_routes.py`. Not run against live Navidrome; coverage not re-measured on a wider sample. Not published or deployed. Remaining: route test for the endpoint, wider-sample coverage re-measure (build-time requirement), contract section, Same Room, Listen-through Gaps, fixtures, clients.

## 2026-11-09 — Same Year, Same Scene builder merged (PR #925)

- Squash-merged PR [#925](https://github.com/abucalip/navi-librarian/pull/925) to `main` as `adf7454da321543e78aff8d3526f0987b7e7c497`. Adds `album_moment` to `intelligence/graph/album_paths.py` (2-year window by year, stated label, credited artist or non-country area, overlap with the artist paths dropped, same bounds and cache as the other album kinds).
- Measured read-only on the store copy, 884 owned albums: coverage 58.4% (at least 35%), median stops 3 (at least 3), no `truncated: time` 100% (slowest 1.3 s), label-only share 0% (at most 50%). Label links from a credited start are always dropped because the artist's label path reaches them; the area link requires two different artists, stricter than the probe.
- Tests: filtered only, `tests/test_intelligence_album_paths.py` and `tests/test_intelligence_paths.py` (53 passed). Not published or deployed. Remaining: contract section, route extension, Same Room, Neighbours by Ear, Listen-through Gaps, fixtures, clients.

## 2026-11-09 — Album path builders merged (PR #924)

- Squash-merged PR [#924](https://github.com/abucalip/navi-librarian/pull/924) to `main` as `3901673d599079e80cfa41319d4e6d2fe55751fe`. Adds `intelligence/graph/album_paths.py` (`album_crew`, `album_guests`, `album_works`: credit-grade evidence, per-person and per-work caps, overlap dropped against the artist paths, bounds, cache) and `kind_rows()` in `paths.py` (behaviour unchanged).
- Tests run (filtered): `tests/test_intelligence_album_paths.py` (18) plus `test_intelligence_paths.py`, `test_intelligence_paths_warm.py`, `test_api_knowledge_paths_route.py` (51 passed in total). Full suite not run locally (owner rule); CI status as reported at merge.
- Read-only run on a copy of the owner's store (884 owned albums), after overlap dropping: Studio Crew 54.5% coverage, median 7; Guest List 48.8%, median 11; Covers and Sources 36.7%, median 3; builds within the 2 s bound 100%, 99.8%, 100%. All pass the Balanced thresholds; Covers and Sources is thin.
- Not done: contract section, route extension, fixtures, Android and macOS clients. Not published or deployed. Updated `docs/ALBUM_PATHS_PROPOSAL.md`, `docs/PROJECT_STATUS.md`.

## 2026-11-09 — macOS bug batch 3 and release types on the timeline

- Branch `macos/bug-batch-3`. macOS: gapless/tail segment fix (the display no longer advances mid-song and the next song plays to its own length), quality badge, artwork aligned with the sidebar, space bar, instrumental lyrics, grouped ⌘K palette, whole-library search with punctuation ignored (Somethin' Else), artist search on Connections and Timeline, album cover fallback in Now Playing, Insights layout/font/auto-refresh, Up Next double-click.
- Server: migration 5 adds `release_group_facts` (MusicBrainz primary and secondary type), filled from the dump (`release_group.type` plus the secondary-type join) and from a live release lookup; the timeline page returns `release_type` per album. The macOS Timeline keeps albums typed "Album" with no secondary type, and falls back to title wording only where no type is stored. Existing stores need a dump re-import (or release-group sweep) before types appear.
- Tests run: `python3 -m unittest` for the timeline, release-group, loader, store, migration and API modules; `swift test --filter` for DiscairAudioTests, DiscairNavidromeTests, DiscairLibrarianTests and DiscairUITests. Full suite not run (owner rule). No visual, audio or live-server check was performed. Not published or deployed.

## 2026-11-09 — Server V2 Phase 6 taste presentation closed (slice 9)

- Re-ran the `check_no_weight_effect` guard (`scripts/server_v2_phase6_exit.py`) on `main` at `2fec5809`: it passed, so no module outside the taste, API, store, scripts and tests packages imports `intelligence.taste` and profiles cannot change ranking.
- The owner waived the remaining macOS Cupertino/Zine visual checks, Android device/emulator and accessibility checks, and the live-server refresh (including the Android 30-second timeout concern); none was performed.
- Updated `docs/ServerV2.md` and `docs/PROJECT_STATUS.md`. Not published, deployed or runtime-verified.

## 2026-11-09 — Server V2 Phase 6 macOS Zine taste cards merged (PR #910)

- Squash-merged PR [#910](https://github.com/abucalip/navi-librarian/pull/910) to `main` as `4052f96533bc427e82b6e5dfa5a0159f0ba29142`, from exact PR head `e36bf7d03e226edb33688bb85ac9de7e106071cd`.
- Adds the Zine Insights taste presentation (`ZineTaste`): server-authored headline and shifts, selectable time windows and dimensions, decade comparison, playlist/Library actions for supported genre and decade values, and honest low-sample/empty states. Reuses the shared `TasteModel` and action behavior; no server or recommendation-ranking changes.
- All four required GitHub workflows passed on the exact PR head. No separate focused-test count was recorded in the PR review evidence; full suite not run locally under the owner's rule.
- The owner explicitly waived manual macOS visual verification; it was not performed. No live-server check. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; Phase 6 slice 6 is complete and remaining slice 9 retains its number.

## 2026-11-09 — Server V2 Phase 6 macOS taste card actions merged (PR #909)

- Squash-merged PR [#909](https://github.com/abucalip/navi-librarian/pull/909) to `main` as `872ad8c8ae9a1c5412f92c54484eba5efa3be874`, from exact PR head `e0ae1c3d6b8bd1519e11900b6e336d314032f0af`.
- Adds genre/decade actions to Cupertino taste shift and window cards: create and open a prefilled smart playlist for editing, or open the Library Songs tab with a clearable taste filter. Area, label and collaborator are unsupported because they do not map to a Library song field. The playlist is not saved to Navidrome until the owner saves it; recommendation ranking is unchanged.
- PR-reported focused Swift tests: 7 passed (`TasteActionTests`, `TasteModelTests`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging, and non-publishing image validation.
- No manual visual Mac or live-server verification; no macOS CI exists by owner decision. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; Phase 6 slice 7 is complete and remaining slices 6 and 9 retain their numbers.

## 2026-11-09 — Server V2 work queue condensed

- Rewrote `docs/ServerV2.md` as a concise active tracker containing only remaining Phase 6 client slices and Phase 7 verification.
- Preserved taste presentation slice numbers and names (5–9), including the existing execution order.
- Moved the complete previous Server V2 plan to `docs/archive/ServerV2_HISTORY_2026-11-09.md`.
- Preserved the complete pre-existing project log as `docs/archive/PROJECT_LOG_HISTORY.md`; this root file is now a short current index so the historical log remains intact without keeping a very large active file.
- Updated `docs/PROJECT_STATUS.md` with the active/archive pointers.
- Documentation-only change. No application code or tests changed. No publication or deployment.

## 2026-11-09 — Server V2 Phase 6 macOS taste cards merged (PR #907)

- Squash-merged PR [#907](https://github.com/abucalip/navi-librarian/pull/907) to `main` as `95af941e6b293e010da93926df89760404800f17`, from exact PR head `a41bdce98a19e2660fb0a3ea7167ae00b5230885`.
- Adds the macOS taste response models/client, once-per-launch background refresh, and Cupertino Insights cards for headline/shifts, time windows, dimensions, decades, low-sample and empty states.
- PR-reported focused Swift tests: 16 passed; full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head (Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation). No macOS CI exists by owner decision.
- No live-server or manual visual verification on the Mac. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; slice 5 is complete and remaining slice numbers 6–9 are unchanged.

## 2026-11-09 — Server V2 Phase 6 Android taste cards merged (PR #908)

- Squash-merged PR [#908](https://github.com/abucalip/navi-librarian/pull/908) to `main` as `2e220280ea45d729b9b37afc441673b8ddd752bb`, from exact PR head `598ac7c2f8e73b14ad63f4645e568b621b5c0927`.
- Adds the Android taste response decoder and repository calls, one background refresh per app launch, the compact Insights card, and a bottom sheet with recent, past-year (`mid`) and all-time windows, dimension selection, listed movers, and low-sample/empty states. Server-authored prose is displayed as supplied; no recommendation-ranking behavior changes.
- PR-reported focused Android tests: 17 passed (`TasteTest`, `InsightsTest`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation.
- No device/emulator, accessibility or live-server verification. The shared HTTP client's 30-second read timeout may expire before a long refresh completes; saved profiles remain available. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; slice 8 is complete and remaining slice numbers 6, 7 and 9 are unchanged.

## Historical entries

Earlier project log entries are preserved verbatim in [PROJECT_LOG_HISTORY.md](docs/archive/PROJECT_LOG_HISTORY.md).

## 2026-11-10 — Artwork booklet and zoom (slice 3, second step)

- Merged as PR [#950](https://github.com/abucalip/navi-librarian/pull/950), squash `d76ce6ea1dc29a8ad6922aece19390fc5cfd957b`.
- New: Android `model/Booklet.kt`, `ui/album/Booklet.kt` (Booklet tab, pager, pinch and double-tap zoom with the full file asked for after the first zoom, TalkBack zoom actions, `PdfRenderer` viewer), `LibrarianClient.download`, `artworkDownload`; macOS `Chrome/BookletSheet.swift` (two-page spread, arrow keys, hover zoom lens, PDFKit for PDF booklets, links never opened), `BookletView`, `ArtworkStore.albumPDF`, Booklet button on the Cupertino and Zine headers. Sticker, Obi and Poster follow the pages.
- Tests actually run, filtered: Android `BookletTest`, `CoverFacesTest`; macOS `BookletTests`, `ArtworkTests`, `FlipCoverTests` (21 pass). Not run: full suites, lint, release build. Not checked on a device or in a window; the PDF paths and the lens have no test beyond the pure helpers.
- Open: Android Brut themes share one Booklet tab; macOS has only Cupertino and Zine.
- Next: slice 4, edition picker and grid fallback.

## 2026-11-10 — Artwork edition picker and grid fallback (slice 4)

- Merged as PR [#951](https://github.com/abucalip/navi-librarian/pull/951), squash `641888e64c1f091912597aa611ea52a4391363a9`. The first CI run failed (Python syntax and Docker packaging, two `test_api_search_routes` album tests: a fake librarian without `DATA_DIR`); the album page now treats an unreadable pick as no pick, and all required workflows then passed.
- New: server `album_choice` table (`intelligence/artwork/store.py`), `intelligence/artwork/cover.py` (JPEG/PNG size from the header, Front-only pick rule, best-front fallback), routes in `app/api/artwork.py`, pick and fallback in `app/api/owned_artwork.py`, `artwork_choice` on the album page; contract section in `SERVER_V2_CONTRACT.md`. Android `model/EditionPicker.kt`, `ui/album/EditionPicker.kt`, `LibrarianClient.delete`, `setArtworkChoice`/`clearArtworkChoice`. macOS `Chrome/EditionPicker.swift`, `ArtworkStore` choices, `ownedCover` and the grid fallback in `ArtworkImage`, client calls in `Artwork.swift`.
- Tests actually run, filtered: pytest `test_artwork_choice`, `test_api_owned_artwork`, `test_api_artwork_routes`, `test_artwork_fixtures`, `test_discovery_search_album_page`, `test_discovery_search_query`, `test_api_search_routes`; Android `EditionPickerTest`, `CoverFacesTest`; macOS `EditionPickerTests`, `ArtworkTests`, `FlipCoverTests`. Not run: full suites, lint, release build. Not checked on a device or in a window.
- Open: the small-cover rule assumes Navidrome does not upscale; other lists can show the old cover for up to 5 minutes after a pick; the owned release is still not passed to the index lookup; macOS reads picks from `/choices`, not the album page.
- Next: slice 5 (Now Playing: disc, slideshow, system artwork). Done below.

## 2026-11-10 — Artwork Now Playing (slice 5)

- Merged as PR [#952](https://github.com/abucalip/navi-librarian/pull/952), squash `47acca05d41a56d4437b7f77aa1d5bb1be071362`; required CI passed on the PR head (compile, container-smoke, test-and-build, validate-container).
- New: macOS `Chrome/NowPlayingArtwork.swift` (`DiscView`, `DiscSleeve`, `SlideshowBackdrop`), pure rules in `DiscairLibrarian/Artwork.swift` (`discImage(disc:)`, `slideshowImages`, `slideshowFrame`, `discAngle`), `ArtworkStore.nowPlayingIndex` and `libraryCover` (also used by `ArtworkImage` and `SystemMedia`), `PlayerBarOptions.showSlideshow`; Cupertino chip and Zine disc. Android `model/NowPlayingArtwork.kt`, `ui/player/NowPlayingArtwork.kt` (`rememberAlbumArtIndex`, `DiscImage`, `DiscSleeve`, `SlideshowBackdrop`), Photos button in the sheet header, `PlayerSettings.showSlideshow`, disc on the Standard and Cassette Deck players.
- Tests actually run, filtered: macOS `NowPlayingArtworkTests` (12), `NowPlayingArtworkUITests` (4), `SystemMediaTests`, `ArtworkBackdropTests`, `FlipCoverTests`, `EditionPickerTests`, `PlayerBarRefinementTests`; Android `NowPlayingArtworkTest` (10), `CoverFacesTest`, `PlayerSettingsTest`, `PlayerLineTest`. Not run: full suites, lint, release build. Not checked on a device or in a window.
- Open: disc motion, the blurred drift, the button placement and TalkBack wording are owner checks; the Mac's system tile picks up a new cover pick at the next Now Playing update; no disc on Android Sheet Stack or Sticker Wall; alternate sleeves per play not built (open decision 2).
- Next: slice 6 (artist collage, Discover peeks, Paths, Timeline).

## 2026-11-10 — Artwork liner note of the day and edition covers (slice 7); artwork plan closed

- Merged as PR [#962](https://github.com/abucalip/navi-librarian/pull/962) (idea 12), squash `0b80701f55d60ffcf515bdd1abd0a2090ab4686c`, and PR [#961](https://github.com/abucalip/navi-librarian/pull/961) (idea 13), squash `7eba84257a07a66a2b8ab24150617982ab627d2d`; required CI passed on both heads.
- Review before merge: both diffs read in full; both PRs mergeable with no conflicts (they make the same one-line `MBID` visibility change); Android Get already sends the release group through `pageMetadata`. No defects found.
- Tests actually run, filtered: macOS `swift test --filter LinerNote` (5 pass) and `--filter EditionCover` (6 pass), re-run during review; the authors report Android `LinerNoteTest`, `EditionCoversTest`, `PathArtworkTest` passing. Not run: full suites, anything on a device or in a window.
- Open: the Sticker Wall peel-off look for the liner note is not built; the Downloads covers show the album's editions, not the fetched pressing (the server does not record it); open decisions 1 to 4 in `artwork.md` stay with the owner.
- `docs/artwork.md` marked complete: every slice and client idea is merged. Next: the owner's manual checks; no artwork code is left to build.

## 2026-11-11 — Redesign M1: Cupertino tokens (macOS)

- Merged as PR [#975](https://github.com/abucalip/navi-librarian/pull/975), squash `f0aba3d6`, from head `61fda98a`; GitHub confirms the merge. Plan: `docs/redesign.md` section 11, step M1.
- Changed: `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoTheme.swift` (colour roles from section 4.1, `CU.Font` roles from 4.2 with `Text.cuRole`, `CU.Space` 4/8/16/24/32; old names kept as aliases). New `macos/Tests/DiscairUITests/CupertinoTokensTests.swift`.
- Tests actually run, filtered, on a Mac: `swift test --filter CupertinoTokensTests` (6 pass); `swift test --filter "CupertinoRound1Tests|CupertinoTokensTests"` (11 pass in 2 suites). One of the agent's own assertions failed on first run (a line-height rule not in the plan) and was removed before merge.
- Not checked: a screenshot against `components--tokens-and-controls`; CI on the PR head was not recorded in this session.
- Side effect, accepted by the owner: shared Chrome components that read `CU` (for example `OfflineBanner`, `ArtistPageParts`) change colour, including under the Zine theme. Zine's own tokens are untouched.
- Left for later steps: literal colours outside the table (`Color.green`/`Color.orange` status dots, the `#F6F6F8` row shade, taste colours), to M2, M3 and M10.
- Next: M2 (controls), Sonnet, Medium.

## 2026-11-11 — Redesign M2: Cupertino controls (macOS)

- Merged as PR [#976](https://github.com/abucalip/navi-librarian/pull/976), squash `e3e69220`; GitHub confirms the merge. Plan: `docs/redesign.md` section 11, step M2.
- Changed: new `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoKit.swift` (`CapsuleButtonStyle` moved here from `CupertinoHome.swift`, `CUPanel`, `CUSegmented`, `CUStatus`, `CUStatusLabel`, `CUNotice`, `CUField`, `CUSwitchRow`); `CupertinoSettings.swift` (switches, segmented controls, labelled fields, notices); `CupertinoHome.swift` (error notice, neutral tile Get); `CupertinoLibrary.swift` (old `CUSegmented` removed). New `CupertinoControlsTests`.
- Tests actually run, filtered, on a Mac: `swift build`; `swift test --filter "CupertinoControlsTests|CupertinoTokensTests|LibraryHubTests"` (17 tests, 3 suites, pass).
- Not checked: a screenshot against `components--tokens-and-controls`; CI on the PR head was not recorded in this session; full suite not run (owner rule).
- Side effect: the regular button is 32 high (was 36), also where shared Chrome components use `CapsuleButtonStyle` under Zine.
- Left for later steps: pages with several filled primaries per view (Discover, Gap Radar, Artist, Insights tiles) to M8 and M10.
- Next: M3 (shell), Haiku, Medium.

## 2026-11-11 — Redesign M4: Cupertino charts (macOS)

- Merged as PR [#978](https://github.com/abucalip/navi-librarian/pull/978), squash `2480b3a2`, from head `1902590526c68255bc0fb99773004fab5f35b8e9`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/redesign.md` section 11, step M4.
- Changed: new `macos/Sources/DiscairUI/Chrome/CupertinoCharts.swift` (`CUChartMath`, `CUChartPhase`, `CUValueFormat`, `CUChartFrame`, `CUTooltip`, `CULineChart`, `CUColumnChart`, `CUPairedBars`, `CUDumbbell`, `CURankedBars`, `CUHeatmap`, `CUHeatmapKey`, `CUStageTracker`); `CU.trackerTrack` (`#DCDCE2`) added to `CupertinoTheme.swift`. New `CupertinoChartsTests` (29 tests) and `CupertinoChartSpecimenTests` (renders the `charts--specimens` sheet from the real views).
- Tests actually run, filtered, on a Mac: `swift test --filter "CupertinoChartsTests|CupertinoChartSpecimenTests|CupertinoTokensTests|CupertinoControlsTests"` (40 tests, 4 suites, pass). Full suite not run (owner rule).
- Visual: the rendered specimen sheet was compared by eye with `charts--specimens.png`; every type and state is present. Not signed off by the owner. Not checked: VoiceOver reading, keyboard focus ring, draw-in motion.
- Choices: Swift Charts for the line, column and dumbbell charts, plain SwiftUI for paired bars, ranked bars, heatmap and tracker (fixed geometry); value axes have at most 5 ticks including the baseline; paired bars carry the two-series legend of rule 4.4; heatmap dates are written day first.
- Nothing calls the charts yet; no Zine file changed.
- Next: M5 (home data) or M6 (services data), Sonnet; M8 builds Home from M2, M4 and M5.

## 2026-11-11 — Redesign M10a: drawn pages (macOS)

- Merged as PR [#984](https://github.com/abucalip/navi-librarian/pull/984), squash `16cb3d9d`, from head `62eb745b` (the first commit `90e81523` restyled the five pages; `62eb745b` built the deviations). GitHub confirms the merge. Plan: `docs/redesign.md` sections 5.3 and 11, step M10a.
- Changed: `CupertinoInsights.swift` (lens pills, lens cards with neutral actions), `CupertinoTaste.swift` (four panels, time of day and the morning-vs-night contrast read from the server's `context`, four top-value dimensions), `CupertinoHistory.swift` (`CUHeatmap`, day panels), `CupertinoDownloads.swift` (filter, tracker rows, weekly arrival count, Try again as the only primary), `CupertinoGapRadar.swift` (ink completeness bar, one neutral Get per card), `CupertinoSettings.swift` (Playback rows, Clear confirmation), `DiscairLibrarian/Taste.swift` (`TasteContext`, `TasteContrast`), `Model/TasteModel.swift`.
- Server: no change. `intelligence/api/fixture_set.py` gained the `taste_context` and `taste_context_contrast` cases, which the server's own context builder writes; `scripts/write_intelligence_fixtures.py` regenerated them and the existing fixtures are unchanged.
- Tests actually run, filtered, on a Mac: `swift test --filter Cupertino` (45), `TasteContextClientTests` and `TasteClientTests` (11), the Cupertino, TasteModel and HomeDashboard suites (72), `CupertinoPagesRenderTests` (4, PNGs of Insights, History, Downloads and Gap Radar). Python: `tests/test_intelligence_contract_fixtures.py` and `tests/test_intelligence_api_insights.py` (20). Full suite not run (owner rule).
- Visual check: the four rendered pages were read against the mockups by eye; Settings Playback was not rendered (its tab needs a live session). The owner has not approved the look.
- Limits: no live Librarian run; the morning-vs-night and time-of-day numbers come from fixtures; the Top values picker no longer offers Collaborator (mockup's four); the Clear confirmation and the Playback layout are not exercised in a window.
- Next: M10b (token-only pages), Haiku, High.

## 2026-11-11: Redesign S1, listens by day (D2)

- PR #986 merged as squash `41449e29cb6cc8c6842e130264a564aff6c0d445` from head `e7001cf799137df7a875b89dea22c9d74d8a2a8a`. `listens_by_day` on `GET /api/insights/taste`: 84 complete UTC days before the refresh day, oldest first, zero days included; absent until a refresh saves it. Built by `intelligence/taste/listens_by_day.py`, saved by the taste refresh as one `taste_listens_by_day` row (no migration, no new provider call).
- Tests actually run, filtered: listens-by-day, taste refresh, taste persistence and contract-fixture suites (44 pass). Full suite not run (owner rule). Not checked live or against the macOS client.
- Next: S2, Haiku, High.

## 2026-11-11 — Redesign M9: Connections and Services screens (macOS)

- Merged as PR [#983](https://github.com/abucalip/navi-librarian/pull/983), squash `344252e3`, from head `393e7d4f06fa6d8749ebd63bee20a6482042cc86`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/redesign.md` sections 5.2, 6 and 11, step M9.
- Changed: new `Themes/Cupertino/CupertinoConnections.swift` and `CupertinoServices.swift`, new `Model/ServicesController.swift` and `AppState+Services.swift`; `GraphExplorerView.swift` (`GraphStyle.redesigned`), `GraphExplorer.swift` (view mode, start name, load failure and retry, requested and failed update, summary, footer and truncated wording, Also on), `CupertinoSettings.swift` (four tabs), `CupertinoTheme.swift` (status button), `ServicesModel.swift` (name and noun lookups), `AppState.swift` (`services`, `settingsTab`, a services check after connect), `ServiceSettings.swift` (`saveSlskd` folders, optional).
- Tests actually run, filtered, on a Mac: `ConnectionsScreenModelTests`, `ServicesScreenTests`, `ConnectionsServicesRenderTests`, `GraphLayoutTests`, `GraphExplorer`, `ServicesModel`, `ScreenshotTests`, `CupertinoControlsTests`, `CupertinoTokensTests`, `ServiceSettingsClientTests` (123 in the last run). Full suite not run (owner rule).
- Visual check: sample-data renders of connections graph, selected, list, empty, not loaded, truncated and failed, and services healthy, degraded, Librarian unreachable, edit sheet and popover, compared with the mockups by eye; the graph's labels were moved to the outer side of each node after the first render collided. Zine before and after screenshots were not taken (owner waived).
- Limits: no live server or window run, no VoiceOver or keyboard pass, owner has not approved the look. The server sends no connection total, so the footer counts what was read. Disconnect exists for Discogs and ListenBrainz only. The edit sheet's Test tests the saved settings. Status now shows Answer, Since, Last good read and Checked from the Mac's own history; Route and Server contract are not drawn. "Also on, in your library" is derived from the walk's structure (owned albums next to the node), not from a server field.
- Next: M10 (remaining pages, two PRs), Haiku, High.

## 2026-11-11 — Redesign M8: Home screen (macOS)

- Merged as PR [#982](https://github.com/abucalip/navi-librarian/pull/982), squash `f9bccff8`, from head `1abfecbafcb6dadf0f252aa12b87a5117152ee98`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/redesign.md` sections 5.1 and 11, step M8.
- Changed: `CupertinoHome.swift` rewritten, new `CupertinoHomeParts.swift`, new pure `Model/HomeScreen.swift` (state choice and wording); `HomeDashboard` gains radio rows, a listens figure and the handoff notice; `AppState` gains `loadHomeFeeds()`, capabilities, a once-a-day never-played reading, Never played playlist, Play something unplayed, popularity fill and Continue on this Mac; new `DiscairLibrarian/HomeFeeds.swift` and `DiscairNavidrome/PlayQueue.swift`; `listens_by_day` on the taste body; D2 and D3 contract proposals in `docs/SERVER_V2_CONTRACT.md`.
- Tests actually run, filtered, on a Mac: `HomeScreenTests`, `HomeDashboardTests`, `HomeRenderTests`, `HomeFeedsClientTests`, `PlayQueueTests`, `TasteClientTests`, `TasteModelTests`, `InsightsModelTests`, `CupertinoControlsTests`, `CupertinoTokensTests`, `ScreenshotTests` (110 in the last run). Full suite not run (owner rule).
- Visual check: five sample-data renders (default, first run, Librarian unreachable, loading, stacked) compared with the `home--*` mockups by eye; the degraded mockup is the M9 popover.
- Limits: D2 and D3 are tested from the proposed contract only, the server does not serve them; the handoff needs the Android app to call `savePlayQueue` (D5); no live-data run, no VoiceOver pass, owner has not approved the look; Space plays only an owned album; the collection chart stays when Librarian is down (the mockup omits it).
- Next: M9 (Connections and Services screens), Sonnet, High.

## 2026-11-11 — Redesign M7: Connections model (macOS)

- Merged as PR [#981](https://github.com/abucalip/navi-librarian/pull/981), squash `7e705614`, from head `6d0f06552068f1bd2673401940e862d6537d4c94`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/redesign.md` section 11, step M7.
- Changed: `macos/Sources/DiscairUI/Model/GraphExplorer.swift` (new `GraphSector`, `GraphGroup`, `GraphWording`, `GraphListRow`, `GraphListGroup`; `GraphLayout` gains `Style` with `.classic` (default, the Zine geometry) and `.sectors` (Cupertino: a sector per arc, rings at 188 and 292 pt), `spacing` and `tooManyToDraw` (under 40 pt spacing); `GraphExplorerModel` gains `tooManyToDraw`, `sectorCounts`, `sectorLayout`, `listGroups`); `macos/Tests/DiscairUITests/GraphExplorerTests.swift` (new suites).
- Tests actually run, filtered, on a Mac: `swift test --filter Graph` (44 pass, 9 suites). Full suite not run (owner rule). No UI, so no visual check.
- Limits: nothing calls the new pieces yet (M9 wires them). The 40 pt threshold is average spacing per ring; step-2 nodes are placed by fan, so their real spacing can differ. The relation and match words come from the server's vocabulary in code and fixtures, not live captures. Types the mockup does not draw (work, recording, event, instrument) fall into an "Other" sector. "member_of" reads "Member of", not the mockup's "member of Talk Talk". Zine's explorer keeps the classic geometry, so its look is unchanged.
- Next: M8 (Home screen), Sonnet, High. M9 (Connections and Services screens) is also unblocked, Sonnet, High.

## 2026-11-11 — Redesign M6: Services data (macOS)

- Merged as PR [#980](https://github.com/abucalip/navi-librarian/pull/980), squash `cf175239`, from head `843ebc1cb903d3aab39a8275398906af69872c20`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/redesign.md` sections 6 and 11, step M6.
- Changed: new `macos/Sources/DiscairLibrarian/ServiceSettings.swift` (settings, test, health and capabilities calls; the Discogs test body's `error` is folded into `status` and `message`; saves for Navidrome, Last.fm, slskd and Discogs) and `macos/Sources/DiscairUI/Model/ServicesModel.swift` (pure; state per service, summary, toolbar label, diagram edges, powers, setup fields, local history).
- Tests actually run, filtered, on a Mac: `swift test --filter 'DiscairLibrarianTests.ServiceSettingsClientTests|DiscairUITests.ServicesModelTests'` (36 pass). Full suite not run (owner rule). No UI, so no visual check.
- Limits: bodies in the tests come from the server's serializers, not live captures (only `health` is a recorded fixture); nothing is wired into `AppState` or a view; no client method reads Navidrome's plugin list, so Sonic analysis with the Librarian down needs the caller to supply it; the app must run the tests and Navidrome and SMB checks itself (M9).
- Next: M7 (connections model), Sonnet; M9 builds the Services screens from M6.

## 2026-11-11 — Redesign M5: Home data (macOS)

- Merged as PR [#979](https://github.com/abucalip/navi-librarian/pull/979), squash `3bf66cb2`, from head `c1a530dd161c05340c3a2a06a4c8830e52dd7d32`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/redesign.md` section 11, step M5.
- Changed: new `macos/Sources/DiscairUI/Model/HomeDashboard.swift` (pure; albums owned and added against the 30 days before, never played with change against a saved baseline, six shelf-life bins plus the four longest-unplayed albums, growth series by range, decade shares with recent listen shares only from a sound taste window, arrivals rows capped at four, notice). `AppState` gains `homeDashboard` and `refreshHomeDashboard()` (no request; builds off the main thread from the shared album list). `LibraryModel.allNavidromeAlbums` keeps the raw list; `NavidromeAlbum` gains optional `playCount` and `played`; `AcquisitionModel.statusText` is `nonisolated`.
- Tests actually run, filtered, on a Mac: `swift test --filter HomeDashboardTests` (18 pass) and `--filter "DiscairNavidromeTests|LibraryModelTests|AcquisitionModelTests|OfflineTests|LibraryHubTests|BulkSongLoadTests"` (112 pass). Full suite not run (owner rule). No UI, so no visual check.
- Limits: radio plays in Arrivals not included (no client route); phone handoff (D5) and Listens last 7 days (D2) not produced; absent `playCount` is read as no plays (Navidrome omits it); Librarian reachability is inferred from the picks read until M6.
- Next: M6 (services data) or M7 (connections model), Sonnet; M8 builds Home from M2, M4 and M5.

## 2026-11-12 — A9 merged (PR #1003, squash e4f4ba1b)

- Built: cover to Album shared element (wired on Recently added, Library grid, Artist albums, Album header; off when motion is reduced; Tape 60% linear); `Palette.accentText` / `Ink.AccentText` (accent as text only at 4.5:1 on page and card, else ink text) applied to Album, Radio, the four players, Queue and Equalizer; Equalizer reset on the A5 confirmation sheet; eyebrow tracking +0.08em; `animateItem` on Radio stations.
- Tests run locally (JDK 17, filtered): `MotionTest`, `PaletteTest`, `ConfirmSheetTest`, `RadioPlaybackTest`; all pass. Full suite not run (owner rule).
- Not checked: no emulator or device, so the transition, Night, Tape and Sheet identity and 200% font scale are unseen.
- Next action: the owner reviews Night, Tape and Sheet on a device (A9 acceptance and A8b item 7); the Android track is otherwise built.

## 2026-11-12 — A8b merged (PR #1001, squash d020f7b2)

- Built: Settings rows with icon, state line and chevron; Library search field removed; Downloads tracker, state in words, one action row, Play on an arrived album (owned album id looked up by artist and album); `animateItem` on the Library grid; Taste sheet "Make a X playlist" button drawn but disabled.
- Tests run locally: `DownloadsRulesTest`, `TasteTest`, `LibraryViewModelTest`. Full suite not run (owner rule).
- Not done: item 1 needs a server route that creates a Navidrome playlist (new module), then `TasteCard.PlaylistRouteAvailable` on; item 7 device check of the three mockups and Night, Tape, Sheet (no emulator available). Nothing compared on screen.
- Next action: A9.
