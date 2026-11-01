## 2026-11-01 — Android crossfade X1: spike run on the phone

- **Done:** a throwaway branch `spike/crossfade-x1` (not merged, not pushed) with two designs, run on the owner's phone over adb with a signed release build installed over the app. Evidence and rules: `docs/ANDROID_CROSSFADE_CONTRACT.md` section 13.
- **Results:** the queue lives inside the player (contract corrected). A helper player cannot be aligned with the main player (position noise about 250 ms): rejected. Twin full-playlist players with a mirror wrapper and `MediaSession.setPlayer` swap worked in 7 joins: the session followed the incoming song, no crash, next during a fade aborts correctly. Bugs found for the build: audio-focus order, the outgoing player advancing at its end, pause not reaching the tail, shuffle order not mirrored.
- **Not done or not claimed:** nothing was heard; scrobbling on the server, the equalizer sound, Bluetooth, calls, Doze, data and CPU cost were not checked. No unit tests were written (a spike). The full suite was not run.
- **Phone state:** the spike build is installed over the owner's release app; sign-in kept.
- **Owner's listening result:** the owner reported the A2 overlap sounds clean (first message "it sounds wlean", confirmed by the owner as "clean"). X1 closed; A2 decided; D-021 updated.
- **Next action:** X2, when the owner schedules it.

## 2026-11-01 — Android crossfade X0: documents

- **Done:** `docs/ANDROID_CROSSFADE_CONTRACT.md` (proposed architecture: two players behind one session wrapper, decided by a spike; album rule keeps same-album joins gapless; automatic changes only), `D-021`, `XFADE-01..04`, the crossfade section of `TEST_PLAN.md`, pointers in `ANDROID_PLAYER_CONTRACT.md`, `ACTIVE_WORK.md` and `PROJECT_STATUS.md`. Documentation only, committed directly to `main` per the workflow.
- **Not done:** no code, no tests, no device check. Whether Media3 1.11.0 offers a crossfade was not checked against the library source; X1 must confirm.
- **Owner input:** the owner asked for the contract to be pushed and X0 started; section 11 was not answered point by point, so its proposed defaults stand.
- **Next action:** X1, the spike, when the owner schedules it.

## 2026-11-01 — Android equalizer E1 to E4: built, merged, first listening test passed

- **Merged:** contract PR #673 (`86e173f`), E1 filter and processor #674 (`64fb9bc`), E2 settings and service wiring #675 (`906f446`), E3 screen #676 (`85b379d`), and the E4 follow-up #677 (`5741e2a`). Required checks (compile, container-smoke, test-and-build, validate-container) passed on each PR head before merge. Governing documents: `docs/ANDROID_EQ_CONTRACT.md`, D-020, `EQ-01..04`, the equalizer section of `TEST_PLAN.md`.
- **Tests actually run (local, JDK 17):** `testDebugUnitTest --tests 'app.discair.player.eq.*'` (41 tests, 0 failures), `assembleDebug`, `lintDebug`, `minifyReleaseWithR8`, `assembleRelease`. The full suite was not run by the assistant (owner rule); CI ran it on each PR head.
- **Device (owner's phone, SM-G781B):** the assistant drove the app over adb (screen, switch, presets, Custom, Reset, restart persistence, 200% text, 48dp touch area, playback stable under changes with no crash and no underrun; one defect, the slider step marks, found and fixed in #677). The owner then did a listening test: switched the equalizer on mid-song and reported that the presets change the sound noticeably and that all was good.
- **Not reported, so not claimed:** FLAC, M4A, Opus and 24-bit files, 128 kbps, gapless on a live album, lock screen, headset buttons, a phone call, Bluetooth, TalkBack, one-handed reach, battery, high-gain distortion at +12 dB with and without automatic headroom, and sign-out keeping the setting.
- **Deviations from the contract (recorded in it):** bands are horizontal rows rather than vertical sliders and there is no landscape layout; the processor keeps the input encoding and float output is not requested.
- **Next action:** none queued; the owner's choice. Crossfade still needs its own contract.

## 2026-11-01 — Android polish pass on built screens: PR #672 merged

- **Merged:** PR #672, squash `ae0eb4fb06fa30ad83071443e696406836687ff3`; required checks (compile, container-smoke, test-and-build, validate-container) passed on the exact head before merge; the full suite ran in CI only.
- **Method:** the `/mobile-design` checklist run over adb on the owner's phone against the release build: tappable elements on Home, Discover, Search, Library, Downloads, Settings and Now Playing measured from the accessibility tree, plus screenshots at default text size (deleted afterwards). Landscape dismissed by the owner. Details and the not-changed list: `android/DESIGN.md`, "Polish pass on built screens".
- **Changed:** header Downloads and Settings buttons 44dp to 48dp wide; Discover card three-dot menu on a dark round backing; 12dp under the Player / Lyrics / Queue tabs in every view.
- **Tests actually run (local, JDK 17):** `testDebugUnitTest --tests 'app.discair.lyrics.*' --tests 'app.discair.player.*'`, `lintDebug`, `assembleDebug`, `assembleRelease`, all passed. On the phone: Discover screen (no element under 48dp, menu readable on a light cover) and the sheet's Player and Lyrics views checked. Not checked: the plain-lyrics note after the spacing change, TalkBack, thumb reach, album and artist pages at 200% text, the offline banner. No UI tests exist for these screens. Not published, not deployed.
- **Next action:** none queued; the owner's choice of what to work on next.

## 2026-11-01 — Android lyrics L4: first device run (owner's phone)

- **Done:** the release APK built from `main` at `8c2808c` was installed over wireless debugging on the owner's phone (SM-G781B, `adb install -r`, success). The owner reported: the Lyrics tab works, timed lyrics follow the music, and everything looked good.
- **Not reported, so not claimed:** plain and no-lyrics songs, the slowest lookup over Tailscale, airplane mode with cached and uncached songs, a song change with the view open (prefetch), TalkBack, 200% text, landscape, hand scrolling and the return button, a tap on a line, battery, sign-out clearing the cache.
- **Agent-driven checks over adb (same day, owner's phone, screen kept awake; screenshots deleted afterwards because they show lyrics):** (1) The sheet reopened on the Lyrics tab (last view remembered) and a plain-lyrics song showed "These lyrics are not timed." with the lines. (2) At font scale 2.0 the three tabs still fit, lines wrap and the list scrolls; "Queue" sits close to the right edge. (3) In landscape at font scale 2.0 the sheet fits but only about three lines are visible at once; the list scrolls inside it. Font scale and rotation were put back (0.9 and portrait). (4) A logcat capture of about 80 s covering those steps contained no lyric text, no address or token from the app's own process, and no crash; the only app-process warnings were framework `Parcel` notices. That capture did not include a fresh network lyrics fetch, so it does not cover the request path.
- **Observed, not fixed:** the "not timed" note sits tight under the tabs (no top padding). Cosmetic; left for the deferred polish pass.
- **Owner's device results (same day):** a no-lyrics song showed "Can't reach Navidrome. Is Tailscale connected?" instead of a no-lyrics message (bug); the slowest lookup was about 7 s; next-song prefetch arrived in time; TalkBack works; hand scrolling and "Back to the current line" work; a tap on a line does nothing; sign-out clears the cache. Airplane mode is irrelevant while songs cannot be streamed offline; battery skipped by the owner for now.
- **Bug cause and fix (PR #671, `ad68d1a`):** a read-only probe of 30 random songs on the owner's server (structure and timing only) showed songs with no lyrics get an empty `lyricsList` after 7 to 23.4 s; the 20 s read timeout cut off the slowest and a `SocketTimeoutException` was reported as unreachable. Timeout raised to 45 s, new timed-out state with its own words. Required CI passed on the exact head. The fixed build was installed on the phone and the owner confirmed that a no-lyrics song now shows "No lyrics for this song." quickly (Navidrome may have answered faster this time; the slow case over 20 s was not reproduced, so the timed-out state was not seen on the device).
- **L4 closed (2026-11-01):** all section 10 checks are done or explicitly skipped by the owner (battery; airplane mode not applicable). Open: the `/mobile-design` polish pass on built screens (deferred by the owner), the note spacing, and a tighter landscape layout.
- **Next action:** the owner runs the rest of contract section 10 when convenient and reports problems; the `/mobile-design` polish pass on built screens stays deferred (owner decision, 2026-10-31).

## 2026-11-01 — Android lyrics L1 to L3 merged (PRs #668, #669, #670)

- **Merged:** #668 `ecdea99be4eed8d947561b9c5da2d2493509fdc8` (head `853a191`), #669 `27a5d3d08e99f0869b9174d8235251333bd00915` (head `44d3391`), #670 `8c2808cbfc87d03d552b5652f2f5e6a45e47a8b6`. Required checks (compile, container-smoke, test-and-build, validate-container) passed on each exact head before merge; the full suite ran in CI only.
- **Built:** `lyrics/` package: Navidrome source with once-per-session `songLyrics` check, choosing and cleaning rules, hashed on-device cache (300 songs or 5 MB, none for 24 h, cleared at sign-out); `LyricsTimeline` and the visible-only 250 ms `LyricsFollower`; `LyricsController` (cache first, one request at a time, next-song prefetch, cancel on close); Player / Lyrics / Queue tabs and `LyricsPanel`; `PlayerController.livePositionMs()`.
- **Tests actually run (local, JDK 17):** `./gradlew testDebugUnitTest --tests 'app.discair.lyrics.*' --tests 'app.discair.player.*' lintDebug assembleDebug assembleRelease` all passed (lyrics: 68 tests). R8 output inspected: the three lyrics serializers are present in the minified build.
- **Not done:** any emulator or phone run, Compose UI tests, release-build cache read/write on a device, the `/mobile-design` review on built screens. No publication or deployment.
- **Next action:** L4, the owner's device run per contract section 10; record results here and in `android/DESIGN.md`.

## 2026-11-01 — Android lyrics, phase L0 (documents)

- **Done:** documentation only, committed directly to `main` per the workflow. Added D-019 to `docs/DECISIONS.md`, `LYRICS-01` to `LYRICS-04` to `docs/REQUIREMENTS.md`, an "Android lyrics focused checks" section to `docs/TEST_PLAN.md`, and replaced the "pending approval" pointer in `docs/ANDROID_PLAYER_CONTRACT.md` with the approved-contract reference. `docs/ACTIVE_WORK.md` records L0 as done.
- **Not done:** no code, no tests run (none apply), no PR, no publication, no deployment. Nothing is implemented; the requirement rows say "Contract only".
- **Next action:** phase L1 (data layer) when the owner schedules it.

## 2026-11-01 — Android header button group: PR #660 merged

- **Change:** PR [#660](https://github.com/abucalip/navi-librarian/pull/660), squash `c2fa8dab1f342a5dcfb6279de8813463babb8318`. Downloads and Settings in the app header are one joined group in the web action-group style (6dp radius, 1px edge, divider, 38dp tall, 44dp buttons). The wordmark no longer shares weight with the spacer, which had left the group about 28dp short of the right edge; it now sits 16dp from the edge, level with the wordmark's left margin.
- **Tests run:** `assembleRelease` locally (JDK 17). Compile, container-smoke, test-and-build and validate-container passed in CI on the PR head.
- **Device results:** signed build installed on the owner's phone over wireless debugging; the owner confirmed the alignment. No TalkBack or large-font check.
- **Limits:** the group is 38dp tall, below the 48dp touch target, matching the web at the owner's earlier request. Not published, not deployed.

## 2026-11-01 — Android Discover tab redesign, card menu, icon-only bar, tab swiping: PR #659 merged

- **Change:** PR [#659](https://github.com/abucalip/navi-librarian/pull/659), squash `52431e041b6fa76d71cbd884383a775c77751447`. Home tag chip text centred; Discover cards get a top-right three-dot menu (Download, Save, Not this album, Not this artist) and a one-line shrinking Peace Sans title; Discover opens on Daily picks with a segmented control (short labels first, Saved last, "Deep dives") and editor-style sub-tabs for Daily picks and Deep dives; bottom bar is icons only; swiping on Discover moves through sub-tabs then main tabs and never leaves for Home or Search.
- **Tests run:** `:app:compileDebugKotlin`, `assembleRelease` and `DiscoveryTest` locally (JDK 17). Compile, container-smoke, test-and-build and validate-container passed in CI on the PR head.
- **Device results:** signed release build installed on the owner's phone over wireless debugging; the owner confirmed the swipe behaviour (Saved back to Personal discoveries, last Daily picks sub-tab on to Deep dives). Other changes were not reviewed on a device; no emulator, TalkBack or large-font check.
- **Limits:** the three dots have no backing and may be faint on very light covers. Not published, not deployed. No unit tests were added for the new tab components or swipe logic.

## 2026-11-01 — Peace Sans for album titles: PR #658 merged

- **Change:** PR [#658](https://github.com/abucalip/navi-librarian/pull/658), squash `cafbaf32cff8c6080e8d52db1daea240ac7e72e8`, from tested head `b488527f09e1750be265a0534b6cf1a910a75f20`, at the owner's direction. Album titles on cards (`.card h3`), ranked list rows (`.ranked-row h3`: Recommendations, New releases, Daily picks, Deep Dives), acquisition rows (`.acq-row h3`), artist-page album rows and library album names use the `--title` face (Peace Sans, weight 400) with the shared title tracking and leading. Big Shoulders Display stays for numerals (rank numerals, dates, top-song and list counters, the empty-artwork placeholder text). CSS only, in `static/app.css`.
- **Tests run:** focused UI-contract modules passed locally: acquisition, new releases, login, button group, add to collection, classics card, artist deep dive, album modal, album tabs, Discogs genre. The full suite ran in CI only.
- **CI:** compile, container-smoke, test-and-build, validate-container and validate-release-workflow passed on the tested head; publish-release was skipped.
- **UI results:** the owner viewed the card titles on the local test server and said they looked good. The list-row and acquisition-row changes were served locally but not confirmed by the owner.
- **Limits:** the shared -.085em tracking was designed for large titles and may look tight on long card titles. Not published, not deployed.

## 2026-11-01 — Android launcher icon uses the Discair wordmark: PR #656 merged

- **Change:** PR [#656](https://github.com/abucalip/navi-librarian/pull/656), squash `fecb7e7fe43ac4aa19d4e291cbb06a28a2039568`, from tested head `54799de36fffac8e704d3e43891eea8388f5e52d`, at the owner's direction. The launcher foreground is the Discair wordmark (cream with the two yellow dots), 60dp wide and centred in the adaptive-icon safe zone, on the existing dark background; the themed-icon layer uses the same vector. The yellow D and the unused `launcher_foreground` colour are removed.
- **Tests run:** `./gradlew assembleRelease` built the signed APK, which was installed on the owner's phone with `adb install -r` over wireless debugging. No unit tests apply.
- **CI:** compile ([run](https://github.com/abucalip/navi-librarian/actions/runs/41308523353)), test-and-build ([run](https://github.com/abucalip/navi-librarian/actions/runs/41308523380)), validate-container ([run](https://github.com/abucalip/navi-librarian/actions/runs/41308523360)) and container-smoke ([run](https://github.com/abucalip/navi-librarian/actions/runs/41308523350)) passed. CI does not build the Android project.
- **UI results:** installed on the phone; the owner has not yet reviewed the icon on the home screen or in themed-icon mode.
- **Limits:** the wordmark is wide, so it is small inside the safe zone; a tighter crop or a "Di" mark is the fallback. Not published or distributed.

## 2026-11-01 — Android client (Discair): PR #651 merged with the font, wordmark and album tabs update

- **Change:** PR [#651](https://github.com/abucalip/navi-librarian/pull/651), squash `31ee9f6486161d2063a6df720873625339f96d52`, from tested head `c576f79`, at the owner's direction. The branch was reconciled with `main` (conflicts only in `PROJECT_LOG.md` and `docs/PROJECT_STATUS.md`, resolved to the `main` versions) and brought level with #652 and #654: Peace Sans titles (-0.085em tracking, 1.05 line height) and Open Sans body in place of Schibsted Grotesk, with Big Shoulders Display kept for rank numerals; the Discair wordmark (`ic_wordmark`, traced from `static/discair-logo.svg`) in the top bar and setup screens; the album Info and Reviews tabs (Reviews calls `GET /api/album-reviews` on first open, shows up to three outlet lines, Try again when partial or failed; Info shows the source and the Wikipedia licence). New `license` field on the description DTO. Licences for Open Sans and Peace Sans replace the Schibsted one; `android/DESIGN.md` updated.
- **Tests run:** `./gradlew testDebugUnitTest assembleDebug lintDebug assembleRelease` with JDK 17 passed locally. No new unit tests for the tabs.
- **CI:** compile ([run](https://github.com/abucalip/navi-librarian/actions/runs/41299684252)), test-and-build ([run](https://github.com/abucalip/navi-librarian/actions/runs/41299684336)), validate-container ([run](https://github.com/abucalip/navi-librarian/actions/runs/41299684242)) and container-smoke ([run](https://github.com/abucalip/navi-librarian/actions/runs/41299684272)) passed. CI does not build the Android project.
- **UI results:** none. Not run on a device or emulator.
- **Limits:** "No description found" on the Info tab relies on the stream's `done` marker being non-default once the stream ends; if it is not, the tab shows "Loading description…" until Reviews is opened. A partial reviews answer may be kept in the saved-copy cache. Signed release APK built locally, not published or distributed.

## 2026-11-01 — Require a beginner Python lesson after every successful merge

- **Change:** Updated `docs/DEVELOPMENT_WORKFLOW.md` on GitHub `main` at `0bf04aa71a07c4c6814cca2241fcbcf777fb3364`. After every successfully merged PR, the agent's final response must include a **Did you know?** section teaching one basic Python idea in beginner-friendly language. Lessons should be short, use a tiny example when helpful, explain it plainly, and vary topics. This applies to documentation-only merges too; no lesson is required when nothing was merged.
- **Documentation closeout:** Recorded the new rule in `docs/PROJECT_STATUS.md` (commit `ab8afaaf4ab28c611d7cdf219a24e9b1a99e0b76`) and this log entry.
- **Verification:** Read the current workflow, project status, requirements, test plan, active work, architecture and decisions documentation; checked recent GitHub commits and open PRs. Documentation-only direct-to-`main` is the existing workflow rule. No tests were run because this change affects workflow documentation only. The final documentation changes are on `main`; no PR was opened.
- **Next action:** Apply the new learning section after the next successful merge.

## 2026-10-31 — Heard list Clear all: PR #653 merged

- **Change:** PR [#653](https://github.com/abucalip/navi-librarian/pull/653), squash `7e1ebeca2935ecdf674eba96dff3b7df7acf2b26`, from tested head `1c309dca362a2acd46c23e674f13bb8c22c05f76`, at the owner's direction. The Heard list on the Radio page has a centred action group above the list with Refresh and Clear all (trash icon, browser confirm); the bottom Refresh is removed. New `DELETE /api/radio/plays` and `RadioStore.clear_plays` empty the log; `navidrome_server.py` is untouched. A follow-up commit centred the group and added 24px between it and the first row.
- **Tests run:** radio modules (log, API routes, UI contract, stations, ICY): 40 passed locally, with new tests for the store method, the route and the toolbar order. The full suite ran in CI only.
- **CI:** compile ([https://github.com/abucalip/navi-librarian/actions/runs/41246170799](https://github.com/abucalip/navi-librarian/actions/runs/41246170799)), test-and-build ([https://github.com/abucalip/navi-librarian/actions/runs/41246170621](https://github.com/abucalip/navi-librarian/actions/runs/41246170621)), container-smoke ([https://github.com/abucalip/navi-librarian/actions/runs/41246170670](https://github.com/abucalip/navi-librarian/actions/runs/41246170670)), validate-container ([https://github.com/abucalip/navi-librarian/actions/runs/41246170576](https://github.com/abucalip/navi-librarian/actions/runs/41246170576)) and validate-release-workflow ([https://github.com/abucalip/navi-librarian/actions/runs/41246170622](https://github.com/abucalip/navi-librarian/actions/runs/41246170622)) passed on the head; publish-release was skipped.
- **UI results:** none. Not browser-checked.
- **Limits:** Clear all cannot be undone and uses the browser's native confirm. After the `index.html` and CSS change the app must be restarted or the image rebuilt. Not published, not deployed.

## 2026-10-31 — Album page Info and Reviews tabs: PR #652 merged

- **Change:** PR [#652](https://github.com/abucalip/navi-librarian/pull/652), squash `f352e6fcf3b7ed0d7ebcd84388e34e5689e07781`, from tested head `9be5cb20d11fc19ba7bb59e0c98a75c25896dcd7`. The album page description area is two tabs. Info: Apple Music notes, else the Wikipedia lead (exact title, album, artist named) with its source link and CC BY-SA 4.0; the `description` stream section keeps its shape, `source` may be Wikipedia and the answer adds `license`. Reviews: new `GET /api/album-reviews` asked on first open (not a stream section; the Android contract is unchanged), up to three outlets' own summary lines with links, from Pitchfork, The Guardian (only with `GUARDIAN_API_KEY`), PopMatters, Consequence, The Quietus, Treble and Angry Metal Guy; exact artist and album match only. Per-outlet answers are cached (review 30 days, confirmed nothing 3 days, failure not at all); a partial answer is kept 10 minutes and marked retryable.
- **Tests run:** focused modules per the PR description (new `test_album_reviews`, `test_album_wikipedia`, `test_metadata_album_info_reviews`, `test_album_tabs_ui_contract`). The full suite ran in CI only.
- **CI:** compile (https://github.com/abucalip/navi-librarian/actions/runs/41236169195), test-and-build (https://github.com/abucalip/navi-librarian/actions/runs/41236169301), container-smoke (https://github.com/abucalip/navi-librarian/actions/runs/41236169250), validate-container (https://github.com/abucalip/navi-librarian/actions/runs/41236169200) and validate-release-workflow (https://github.com/abucalip/navi-librarian/actions/runs/41236169194) passed on the head; publish-release was skipped.
- **UI results:** the PR author drove the real app in Chrome and the owner tried it by hand (some albums showed one review, one showed three). The `LOCAL_UI_TESTING.md` checklist (reduced motion, screen readers, rotation across 620px) was not done.
- **Limits:** Guardian hit rates measured low (3 of 5 well-known albums, 2 of 60 mixed library albums, 0 of 33 jazz); other outlets answered intermittently. A `DECISIONS.md` entry for reading public outlet pages is left to the owner. Not published, not deployed.

## 2026-10-30 — Image v0.3.1 published

- **Published:** annotated tag `v0.3.1` at `a0358e3d35ab97633ed08965604cc7717108b0ff` (the exact `main` after PR #650 and its docs commit), with the owner's authorization; release run [41134598870](https://github.com/abucalip/navi-librarian/actions/runs/41134598870) succeeded. Image `ghcr.io/abucalip/navi-librarian:v0.3.1`, digest `sha256:2fb12eabdb0395707409df67fab9953c84618688904ce195be39eb5bc89871f2`. It adds PR #650 (Library albums, owned-only search, sorting, list/grid) to v0.3, which is the rollback reference. The version label on a running v0.3.1 container was not checked.
- **Not done:** deployment and runtime verification (separate owner authorization); the Library browser check.

## 2026-10-30 — Library albums, owned-only search, sorting and list/grid: PR #650 merged

- **Change:** PR [#650](https://github.com/abucalip/navi-librarian/pull/650), squash `22de224129a5ace834155967b167446235cf92a9`, from tested head `22a4aaf9b42a6c1c4f4f7b61708b96e781cfb4d8`, at the owner's direction. The Library page searches owned music only (`/api/search?scope=owned`, same streamed groups as the top bar, no "Not in your library" group) with a clear (X) button; Escape clears it. Without a query it browses Artists or Albums (new `GET /api/library/albums`; both library routes take `sort` and `order`). Artist sorts: name, album count, date added (newest album). Album sorts: name, artist, album year, date added (Navidrome `created`), track count. A direction button flips the order; entries with no value stay last. List and grid display, with a tile-size slider (110 to 320 px) in grid mode; tab, sort, direction, display and size are kept in localStorage. The library snapshot cache refreshes itself for the new `created` field. The top-bar search code was refactored into search surfaces (`makeSearchSurface`, `startSearch`) so both pages share it. New sprite icons `list` and `layout-grid`. Requirement: `REQUIREMENTS.md` LIB-06.
- **Tests run:** focused modules one at a time: library UI contract, icon sprite contract, button group, shell rail, search query, search routes, search index, library snapshot (188 passed). New tests for album paging, sort order, missing values last, cursor bound to order, and the UI contract. `node --check static/app.js`. The full suite ran in CI only.
- **CI:** compile, container-smoke, test-and-build, validate-container and validate-release-workflow passed on the head; publish-release was skipped.
- **UI results:** none. Not browser-checked.
- **Limits:** the artist "date added" is its newest album's, an owner-visible choice not yet confirmed. After the `index.html` change the app must be restarted or the image rebuilt. Not published, not deployed.
- **Next action:** the owner runs the browser check of the Library page (list, grid, slider, tabs, sorts, search, X) on desktop and phone widths.

## 2026-10-30 — Unified icon-only button groups: PR #649 merged

- **Change:** PR [#649](https://github.com/abucalip/navi-librarian/pull/649), squash `0c7b8aaa39675ad23ec41258f762e3029c8f02dc`, from tested head `95ee5aa154a5ff7ecec54dde81b44753408ed344`, at the owner's direction. Every button on Grab the radio, Settings, Saved, Library, Discover music, New releases, Personal Discoveries, Add to your collection and Artist Deep Dives is now an icon-only button in the joined action-group frame (name in `title` and `aria-label`), 38 px tall. Icons: save (Save settings, Save token, radio Save), plug-zap (Test connection), trash-2 (Remove saved token), sparkles (Generate recommendations), list-plus (Load buttons), rotate-cw (Refresh, Refresh in background, Try again), plus (Library Load more), chevrons (dashboard carousel, Deep Dive row arrows, dropdown arrow, quality-priority move buttons). Added to the sprite: save, plug-zap, sparkles, list-plus, plus, chevron-up, chevron-down (path data written by hand from Lucide shapes, not copied from the package). Discover music selects hide the native arrow and show the chevron-down as an inlined data URI. Dashboard arrows were text glyphs and are now sprite icons. Settings groups sit in `.settings-actions` (a `div` inside a `p` had closed the paragraph and stretched the group). The radio address field is 38 px tall to match its Save button; the quality-priority move group is 28 px tall. `.btn-primary` and its contract test are retired, so Save and Generate are no longer yellow; Generate shows `aria-busy` (spinning icon) instead of "Generating…". Changed: `app/templates/index.html`, `static/app.css`, `static/app.js`, `static/icons.svg`, and the affected contract tests.
- **Tests run:** every `tests/test_*ui_contract.py` module one at a time; new `tests/test_button_group_ui_contract.py`; `node --check static/app.js`. The full suite ran in CI only. The markup was also rendered in headless Chrome against the real CSS.
- **CI:** compile, container-smoke, test-and-build, validate-container and validate-release-workflow passed on the head; publish-release was skipped.
- **UI results:** the owner saw the result locally and said the buttons were much better after the settings and radio fixes. No `LOCAL_UI_TESTING.md` checklist recorded.
- **Limits:** buttons are 38 px (28 px for the move arrows), under the 44 px target in `PRODUCT.md`, at the owner's request. The Acquisitions refresh button (already an icon square) was left alone; the Saved page's Refresh was converted though not on the list. Not published, not deployed.
- **Next action:** the owner runs the phone and desktop browser checks.

## 2026-10-30 — Sprite icons for the gear and search: PR #648 merged

- **Change:** PR [#648](https://github.com/abucalip/navi-librarian/pull/648), squash `84b8b2ff53f36ef64663a345fa20fc80a9d59445`, from tested head `e4a9ac965fa60ba8581ee13dbf6130ed41e8c936`. The header gear and the three magnifiers (top-bar toggle, top-bar submit, Library filter) were inline SVG copies; they now use the vendored Lucide sprite (`/static/icons.svg#settings`, `#search`) on phone and desktop. Search icon colour moves from `fill` to `color` (sprite icons are stroke-based) and is the gear's `--text-muted` grey, with the yellow hover and focus kept. Changed: `app/templates/index.html`, `static/app.css`.
- **Tests run:** every `*_ui_contract` module and `test_ui_keyboard_and_feedback_contract`, one at a time; the flat-surfaces test again after the colour change. The full suite ran in CI only.
- **CI:** compile, container-smoke, test-and-build, validate-container and validate-release-workflow passed on the head; publish-release was skipped.
- **UI results:** the owner saw the icons in the local app after a server restart and asked for the lighter grey, which is included. No checklist from `LOCAL_UI_TESTING.md` was recorded.
- **Limitation:** `index.html` is read once at server start, so a running server needs a restart for the HTML change.
- **Not done:** the browser checklist, publication, deployment.
- **Next action:** the owner runs the phone and desktop browser checks (see the PR #647 entry).

## 2026-10-30 — Phone UI pass: PR #647 merged

- **Change:** PR [#647](https://github.com/abucalip/navi-librarian/pull/647), squash `1fe4a60a42e0dd8108ce438a691e9373f3a8ddb7`, from tested head `a1f4242550603ecd94f06159519888424219b05b`. Phone layout only (620px and under); the desktop UI is unchanged. Top bar: a magnifier beside the gear grows into the search field and hides the title text (cassette stays). Dashboard picks: swipeable cards with dots (no arrows or count), tags "discovery" and "deep dive", artwork at 60% of the card, album / artist / year and listens order; genre tiles four to a line. A round "i" button on card artwork toggles the artist bio overlay. New releases, Recommendations, Personal Discoveries, Add to your collection and Saved are sideways-scrolling album cards; Daily picks shows its four lists in sequence with no lens picker. Similar artists swipe in one row with larger circles and wrapping names. Acquisition button groups and the Acquisitions and Radio refresh buttons are centred. Changed: `static/app.js`, `static/app.css`, `app/templates/index.html`. The layout is chosen with a `matchMedia` query and lists rebuild when the breakpoint is crossed.
- **Tests run:** `node --check static/app.js`; every `*_ui_contract` module and `test_ui_keyboard_and_feedback_contract`, one at a time; a simulated-DOM run of `app.js` against the template, which built the picks at desktop and phone widths. The full suite ran in CI only. No new regression tests were added.
- **CI:** compile, container-smoke, test-and-build, validate-container and validate-release-workflow passed on the head; publish-release was skipped.
- **UI results:** the owner looked at the changes in a local browser while they were built and asked for the follow-up adjustments in the PR; no checklist from `LOCAL_UI_TESTING.md` was recorded, and the desktop regression check, keyboard and focus checks, and rotation across the breakpoint were not run.
- **Limitation:** `index.html` is read once at server start, so a running local server needs a restart to pick up template changes.
- **Not done:** the browser checklist, publication, deployment.
- **Next action:** the owner runs the phone and desktop browser checks against `1fe4a60`.

## 2026-10-30 — Metadata caching: PR #646 merged

- **Change:** PR [#646](https://github.com/abucalip/navi-librarian/pull/646), squash `b369c87b74121aab9fe4717dcdd8d7c79a2c313a`, from tested head `67f4c35aaac8eb4c01559e405be28a89b35d953a`. New `app/services/persistent_metadata.py` is attached to the metadata cache in `app/main.py`; found bios, album and artist artwork, album details with a tracklist, descriptions and links persist for 30 days (Apple and links 7 days). Failures, retryable and incomplete answers are not stored. `/api/album-details` had no cache and now has one; artist-page album years use the stored copy. The album modal and artist hero use the page request caches. New `app/api/http_cache.py` adds `Cache-Control: private, max-age=86400` to successful metadata GETs that found something. `navidrome_server.py` untouched (D-016).
- **Tests run:** 386 focused tests locally (metadata routes, persistent cache, HTTP cache, artwork, album links, Deezer, and every test that reads `static/app.js`); the full suite ran in CI only. Two existing tests were adjusted.
- **CI:** compile, container-smoke, test-and-build, validate-container and validate-release-workflow passed on the head; publish-release was skipped.
- **Not done:** browser check, live provider calls, publication, deployment. Radio recording lookups remain uncached.
- **Next action:** the owner checks the caching in a browser after a restart.

## 2026-10-30 — Card, dashboard and acquisitions UI pass: PR #643 merged; image v0.3 published

- **Change:** (1) Discovery cards and the New releases shelf cards: action group centred below the text, smaller; the artist bio is a hover overlay on the artwork cut at the last full stop that fits the square; year on its own line under the title with the listen count beside it; list rows keep the year beside the name (12 px gap) with the listen count after it; the "Last.fm playcount" text lines were removed. (2) New releases items get Last.fm listens from the existing Last.fm cache only (`LastFmClient.cached_album_popularity`, applied in the discovery route; no provider requests, nothing added to `navidrome_server.py`). (3) `/api/artist-bio` reads the saved copy, then Navidrome's own biography for library artists, then Wikipedia. (4) Release years found by `/api/album-years` and `/api/album-year` are kept in the persistent metadata cache. (5) Dashboard: icon-square shuffle button beside the status text; the picks strip takes the feature cover's dominant colour (same `dominantColor`/`backdropTint` as the album and artist pages). (6) Acquisitions: one icon action group (try again, use next source, dismiss), a "Dismiss all successful imports" bar, an icon refresh button, shorter page description. (7) Build version shown at the bottom of the rail (`APP_VERSION`, else `git describe`); the release workflow now passes the tag as `APP_VERSION`.
- **Tests run:** focused Python tests for the Last.fm client, new releases, metadata routes, discovery routes and page routes, plus every `*_ui_contract` module one at a time; contract tests were updated where the markup changed (icon sprite list, acquisition buttons, year helper, one extra allowed gradient for the carousel tint). The full suite was not run locally (owner rule); CI runs it on the PR head.
- **Browser:** the owner viewed the cards, carousel tint, shuffle button and acquisitions group on the local app while iterating. The Dismiss all successful imports bar, the refresh icon and the version label were not browser-checked.
- **Merge:** PR [#643](https://github.com/abucalip/navi-librarian/pull/643), squash `c89a777689e914105d126de4009533baaa27bd5e`, from tested head `7e6da1b64a26101376d3f6530b8d83f4d801bdcb`; all required checks passed on that head (compile, test-and-build, container-smoke, validate-container, validate-release-workflow; `publish-release` skipped), and the full suite ran in CI only.
- **Published:** annotated tag `v0.3` at `c89a777689e914105d126de4009533baaa27bd5e` (the exact current `main`), with the owner's authorization; release run [41081520481](https://github.com/abucalip/navi-librarian/actions/runs/41081520481) succeeded. Image `ghcr.io/abucalip/navi-librarian:v0.3`, digest `sha256:b09f561a77db277e6e03bce7e2aacf935b933543b88d2f39d1b53d18b5b1fdca`. Rollback reference: v0.2.9. The rail shows the tag as its version because the workflow now passes it as `APP_VERSION`; this was not checked on a running v0.3 container.
- **Not done:** deployment. The carousel tint cross-fade between slides was dropped because the motion contract allows only transform and opacity transitions.

## 2026-10-30 — Cloud Get everywhere and cover-tinted backdrops: PR #642 merged

- **Change:** PR [#642](https://github.com/abucalip/navi-librarian/pull/642), squash `04f14744ea20f914de1acfbe0bae380abd357b5f`, from tested head `213b8d256579f899fd85ecd474b190284d55cc19`; all required checks passed (compile, test-and-build, container-smoke, validate-container, validate-release-workflow; `publish-release` skipped). (1) The remaining lone Get buttons (album page cover and per-song Get, dashboard shelf cards, album pop-up) are seated in the action group, so every Get uses the cloud face. (2) The album and artist page backdrop takes the cover's dominant colour (32x32 canvas, bucketed pixel count weighted toward saturated pixels, lightness capped at 30% and saturation at 70%) and fades from it to the page ground (`tintPage`, `.tint-backdrop`, `--page-tint`). A cover the browser cannot read (a host without CORS headers) keeps the default background. (3) The artist Top songs panel is 70% opaque. The owner asked for the one new gradient, so `test_flat_surfaces_ui_contract` now allows exactly two (the artist photo scrim and this backdrop).
- **Tests run:** UI, contract, card, dashboard, modal, album and artist tests locally (1,154 passed); the full suite ran in CI only. `tests/test_acquisition_import.py::ImportCompletionServiceTests::test_success_persists_importing_before_import_and_then_imported` failed locally before and after this change (no Python changed) and its cause was not examined; it passed in CI.
- **Browser:** the owner viewed the album page backdrop on the local app and said it looks much better. The artist page backdrop, the pop-up Get, the shelf-card Get, the song-row Gets and the translucent Top songs panel were not browser-checked. Not checked: whether Deezer covers (unowned albums and artists) can be read through CORS.
- **Not done:** publication, deployment.
- **Next action:** the owner checks the artist page backdrop and the unowned-cover case in a browser; if Deezer covers do not tint, decide whether to proxy them through the app.

## 2026-10-30 — Radio app address: PR #641 merged; image v0.2.9 published

- **Change:** PR [#641](https://github.com/abucalip/navi-librarian/pull/641), squash `b885b0ecb7689333fe7bd30d557034e95884ed23`, from tested head `1bf75397687bb9ffaa5b79fbcaea6081dd54facf`; all required checks passed. The Radio page has a saved "App address" (for example a Tailscale address) that relayed stations use instead of the browser tab's address; saving a new one moves stations that are already relayed.
- **Tests run:** focused radio station, route, log and UI-contract tests locally; the full suite ran in CI only.
- **Published:** annotated tag `v0.2.9` at `b885b0ecb7689333fe7bd30d557034e95884ed23`; release run [41049514958](https://github.com/abucalip/navi-librarian/actions/runs/41049514958) succeeded. Image `ghcr.io/abucalip/navi-librarian:v0.2.9`, digest `sha256:203c6b116297186a9601e96ef2c54cc6fabe85a6339a94c178a715c680b9e67d`. Rollback reference: v0.2.8. Not deployed.
- **Not done:** browser check and a phone test away from home.
- **Next action:** the owner deploys v0.2.9, saves the Tailscale address on the Radio page and tests a relayed station from a phone away from home.

## 2026-10-30 — Pill search fields: PR #640 merged; image v0.2.8 published

- **Merged:** PR [#640](https://github.com/abucalip/navi-librarian/pull/640), squash commit `fb5f7b13a1944705f31d08ce290ed05081998d10`, from tested head `31883a8`, at the owner's direction. All five required checks passed on that head. The first head failed `compile` and `test-and-build` on three UI contract tests (`test_motion_ui_contract` allows only transform and opacity transitions on the motion tokens; the header-menu contract requires `focusable="false"` on SVGs); the glow became an opacity fade on a pseudo-element and the attribute was added.
- **What changed:** the top-bar search is a pill with an inline submit icon (`.search-field`); focusing the empty field lists the last three searches from localStorage `navidrome-recent-searches`, saved on submit, on picking a recent term and in `openFromSearch` before the field is cleared. The Library filter (capped at 420 px) and the Sort by select share the rounded style.
- **Verification:** focused tests only (full suite not run by the agent): `tests/*ui_contract*.py` (365 passed) and `node --check static/app.js`. No browser check is recorded.
- **Published:** annotated tag `v0.2.8` at `fb5f7b13a1944705f31d08ce290ed05081998d10`; release run [40979128615](https://github.com/abucalip/navi-librarian/actions/runs/40979128615) succeeded. Image `ghcr.io/abucalip/navi-librarian:v0.2.8`, digest `sha256:6c7d00b327066ac77b2477b64f302a458f28b4bfdd5f7c566a0297af2a18d2f8`. It also carries PRs #638 and #639. Rollback reference: v0.2.7.
- **Not done:** deployment, runtime verification of the image, browser checks of the search fields.
- **Next action:** the owner checks the search fields in a browser and decides on deploying v0.2.8.

## 2026-10-30 — Action button group: PR #639 merged

- **Merged:** PR [#639](https://github.com/abucalip/navi-librarian/pull/639), squash commit `a6a8cb29fd5e97a724d422b6286176cdc327427d`, from tested head `1724c41`, at the owner's direction. All five required checks passed on that head.
- **What changed:** `createActionGroup()` in `static/app.js` builds one joined control (cloud-download Get, bookmark Save, trash Not for me; 44 px wide, 38 px tall, 1.5 px icons) used by the ranked rows, the editorial cards (centered over the artwork), the dashboard picks and New releases shelf (removed on Not for me, restored on Undo or a failed request), and the Heard list in Grab the radio (Remove takes the song out of the log; a song with no album is saved under its title). `wrapInActionGroup()` seats a lone download button in the same frame on Top songs and the album rows (artist-page missing albums, album-page lists), with a larger icon. Ranked rows keep the group as far from the right edge as from the top and bottom. Dismiss artist is gone from the UI; the server `dismiss_artist` action is unchanged. Heard-list song, artist and album names open their pages. The radio switch is 46x26 and dark grey when off. The artwork group is named "Album artwork".
- **Verification:** focused UI contract tests (`tests/test_*ui_contract.py`, 365) pass; `node --check` clean; the markup was rendered in headless Chrome against the real CSS. CI ran the full suite on the PR head. No browser check of the running app is recorded, and the undo and restore path of the dashboard dismissals was not exercised.
- **Limits:** the buttons are 38 px tall, under the 44 px target in `PRODUCT.md`, at the owner's request. Not published or deployed; not in v0.2.7.

## 2026-10-29 — Radio switch restyled: PR #638 merged

- **Merged:** PR [#638](https://github.com/abucalip/navi-librarian/pull/638), squash commit `0c08d5d1d793fb01d5d5ecdd8ec599e3a2ebcd78`, from tested head `241b5f5bddda97d4c37d6a84aa403e6d7fd0591b`, at the owner's direction. All five required checks passed on that head.
- **What changed:** the station switch on the Radio page (the only toggle in the app) uses the Uiverse "happy-warthog-87" design by Galahhad: 60x30 pill, wide knob sliding behind the clipped edge, pressed state centres it. It stays a `role="switch"` button. Colours follow the app (light-gray off; yellow track with a black knob on). Only the knob's `transform` animates, with the `--dur-slow` token, to satisfy the motion contract.
- **Verification:** focused tests only (full suite not run by the agent): `test_motion_ui_contract`, `test_radio_ui_contract`, `test_ui_keyboard_and_feedback_contract`. No browser check of the new look is recorded.
- **Not published or deployed:** it is not in image v0.2.7 (tag at `f7d8e44`); it needs a later version.

## 2026-10-29 — Image v0.2.7 published

- **Authorization:** the owner directed publication of current `main` as the next version, v0.2.7.
- **Checked before tagging:** local `main` equal to `origin/main` at `f7d8e446ef755427ccb6b50fa53cd0a1d2ef72f0` (the PR #637 merge `3edd12c` plus the docs commit `f7d8e44`); the four workflows on `main` at that commit (Python syntax check, Validate Docker image, Container runtime smoke test, Validate Docker packaging) succeeded; no change besides documentation sits between `3edd12c` and the tag.
- **Published:** annotated tag `v0.2.7` at `f7d8e446ef755427ccb6b50fa53cd0a1d2ef72f0`; release workflow run [40967761510](https://github.com/abucalip/navi-librarian/actions/runs/40967761510) succeeded (`publish-release` success; `validate-release-workflow` skipped as designed). `ghcr.io/abucalip/navi-librarian:v0.2.7` and `:sha-f7d8e446ef755427ccb6b50fa53cd0a1d2ef72f0`; package version digest `sha256:05eda76010842352788eb8a9093c1e616175cedd0ccf95041b7f9f301c9907cd` (GitHub Packages API). It carries Grab the radio (PR #637). v0.2.6 is the rollback reference. `latest` was not moved and not checked; per-platform manifests were not inspected.
- **Not done:** deployment; runtime verification of the published image; the browser and phone-client checks of Grab the radio.
- **Next action:** the owner decides on deploying v0.2.7.

## 2026-10-29 — Grab the radio: PR #637 merged

- **Merged:** PR [#637](https://github.com/abucalip/navi-librarian/pull/637), squash commit `3edd12c3d1fd40c69a286572bbf549fee4c75aec`, from tested head `4b3eeb0a7f234ea3eafc77089bad6c8b5af8215d`, at the owner's direction. All five required checks passed on that head. The first head (`71ee71e`) failed `compile` and `test-and-build` on `test_motion_ui_contract` because the switch knob also transitioned `background`; fixed in `4b3eeb0` (transform only) and CI passed.
- **What changed (RADIO-01):** Navidrome cannot see what a client plays on a web radio, so a station is switched on in the Radio page and its Navidrome address becomes `<app>/radio/stream/<token>` (the original is stored and restored when it is switched off). The relay (`integrations/radio/relay.py`, `app/api/radio.py`) passes the audio through and reads ICY titles (`icy.py`) while a client is connected; a client that asks for metadata gets the stream unchanged, one that does not gets audio only. `listening.py` logs a song only after 30 s on it; `store.py` keeps `radio.sqlite3` and merges the same title on the same station within 10 minutes. `stations.py` lists, enables and disables stations through Navidrome's radio API. `integrations/musicbrainz/recording_album.py` finds the album for Get, which then uses the song-only Get (ACQ-08). `/radio/stream/` is public to the login gate, with the per-station token as the credential; a disabled station's token stops working. `static/radio.js` renders the page: a switch per station, the app's Get button, an X to remove. `navidrome_server.py` is untouched (D-016).
- **Owner decisions recorded:** proxy approach (the app relays the stream) over polling stations; download through the existing song-only Get; the switch's on state is a black track with a yellow knob.
- **Verification:** focused tests only (full suite not run by the agent): `test_radio_icy`, `test_radio_log`, `test_radio_stations`, `test_api_radio_routes`, `test_radio_ui_contract`, `test_app_login_middleware`, `test_app_legacy_import_boundary`, `test_motion_ui_contract`, `test_acquisition_ui_contract`, `test_acquisition_stable_render_ui_contract`, `test_artwork_cache_isolation`; `check_app_legacy_imports.py` and `check_server_size.py`. A real-socket relay check against a fake ICY server logged both songs and saved the last on disconnect. The owner confirmed it works with the local test environment and a Navidrome client; no browser checklist is recorded.
- **Limits:** see `ACTIVE_WORK.md` section 2e. Not published or deployed.

## 2026-10-29 — Song-only Get and new Get button: PR #636 merged

- **Merged:** PR [#636](https://github.com/abucalip/navi-librarian/pull/636), squash commit `63b695efb05c4cbe7470077a6ed9f07ebccd3e00`, from tested head `ed62d9e2e8721b818f20ae438116eae0ab00cfab`, at the owner's direction. All five required checks passed on that head (`compile`, `container-smoke`, `test-and-build`, `validate-container`, `validate-release-workflow`; publishing skipped).
- **What changed (ACQ-08):** `POST /api/acquire/track` searches slskd for one song, chooses the best clear single file automatically, downloads it and files it in the folder the library already uses for the album (year-suffixed names recognised) or a new `<artist>/<album>/`. New modules `acquisition/track_search.py`, `track_destination.py`, `track_import.py`, `track_service.py`; `navidrome_server.py` unchanged (D-016). A song is one row of the acquisition table (album name `<title> (song on <album>)`, `kind: "track"`, candidate under `track_file` so the album watcher never recovers it). Retry and fallback sources, restart resume, live progress and dismissal that removes only the song's own file (fails closed) are included.
- **UI:** a Get on each missing track of the album page and each Top song that names an album; the album-level Get becomes the check only when every track is owned (the owner's decision); song acquisition cards. Every Get button app wide is now the smaller circular download-arrow design with a 1 px ring.
- **Owner decisions recorded:** automatic candidate choice; create the album folder when none exists; album Get hides only when all tracks are owned.
- **Verification:** focused tests only (full suite not run, per workflow): `test_acquisition_track.py`, `test_track_get_ui_contract.py`, `test_acquisition_routes.py`, all `*ui_contract*` and `test_acquisition_*`. `test_acquisition_import.py` `test_success_persists_importing_before_import_and_then_imported` fails locally on a macOS `/private/var` path mismatch, also on clean `main`; CI passed. Live slskd and browser checks were not done.
- **Limits:** the album-level Get on a partly owned album ends in `destination_exists`; a song's dismissal is refused while another download shares its remote folder; a song interrupted while `importing` is not resumed. Not published or deployed.

## 2026-10-29 — Album page redesign: PR #635 merged

- **Merged:** PR [#635](https://github.com/abucalip/navi-librarian/pull/635), squash commit `58a8148b05066d7008d8b1f3eabdecb5fcf0c7d6`, from tested head `0741da3276ef1a1ef256efe4d991ae3bd9af74c6`, at the owner's direction. All five required checks passed (compile, test-and-build, container-smoke, validate-container, validate-release-workflow; `publish-release` skipped).
- **What changed:** the album page is one centered column: large cover, bold title, artist, genre and year, description (three lines on desktop, six on a phone, plain-text Read more only when there is more), tracklist with number, title, length and an owned check, a centered summary line ("N songs, H hour M minutes · X in your library"), a centered row of service links, ranked similar albums with numerals, similar-artist circles. The Library heading and text Back button are gone (icon-only back button).
- **Backend:** per-track `owned` on the `tracks` section (title match, or track number plus length within 3 s; library-only songs appended; owned albums fall back to the library tracklist when providers fail). New `genre` section (library genre, else first artist tag); the owner approved a genre field, built as its own section like `year`. Contract: `SEARCH_CONTRACT.md` 14.4.
- **Not built:** the per-track Get button. Song-only acquisition is a new pipeline; the draft is in `ALBUM_PAGE_REDESIGN_PROPOSAL.md` section 3 and waits for the owner's decisions.
- **Verification:** focused album, search-route and UI-contract tests passed; the browser checklist and live provider checks were not done. `tests/test_acquisition_import.py` `test_success_persists_importing_before_import_and_then_imported` fails on a local clean `main` too and passed in CI.

## 2026-10-29 — Artist page redesign: PR #634 merged

- **Merged:** PR [#634](https://github.com/abucalip/navi-librarian/pull/634), squash commit `2ca07f86e931a7aee5c84a2bcd80e81da9834803`, from tested head `ac18b86e8352ada5a2ac01b1eaa8772869e47c8e`, at the owner's direction.
- **What changed:** the library artist page follows the owner's layout: large photo with the name over it (one dark scrim, the only gradient in the stylesheet; `test_flat_surfaces_ui_contract.py` allows exactly that), up to three plain-text genre links, "N albums in your library", Top songs beside the photo, bio clamped to three lines on desktop (six on a phone) with Read more only when it overflows, owned album cards with check marks, missing albums ranked by listens, similar artists as circles. Removed: the Library heading, the text Back button (an icon-only button sits on the photo) and the owned-only toggle. The show-all links and Read more are plain text.
- **Backend:** new `top_songs` section (`discovery/search/top_songs.py`; ListenBrainz `top-recordings-for-artist`, checked live, then Last.fm `artist.getTopTracks`; one scale per list; 24 h cache; `owned` recomputed per read). `missing_albums` items add `key` and `popularity_source`. Ownership matching ignores one trailing `(YYYY)` or `[YYYY]` (`album_match_key`), found on the owner's library, where albums are tagged like "Re-Foc (2002)" and MusicBrainz lists them without the year; this also applies to search.
- **CI finding:** the first head (`53961ff`) failed `compile` and `test-and-build` on `test_classics_card_ui_contract` because the bio clamp added two `-webkit-line-clamp` rules to a count guard. The count and its comment were updated in `ac18b86`; all required checks then passed.
- **Tests actually run (agent, locally):** `test_discovery_search_*`, `test_api_search_routes`, `test_library_search_ui_contract`, `test_discogs_genre_ui_contract`, `test_refresh_keeps_page_ui_contract`, `test_flat_surfaces_ui_contract`, `test_album_modal_ui_contract`, `test_artwork_loading_ui_contract`, `test_album_modal_artist_bio_ui_contract`, `test_fonts_and_icons_ui_contract` (405 passed), `test_classics_card_ui_contract` (6 passed); `node --check static/app.js`; `compileall`. The full suite ran in CI only. The Impeccable detector reported three findings, all in code this PR does not touch. The Web Interface Guidelines source could not be fetched, so that review was done from memory (one finding fixed: the hero photo no longer lazy-loads).
- **UI results:** layout checked in headless Chrome at 1440 px and in a 390 px frame on a static page with the real CSS and mock data. The manual checklist (`LOCAL_UI_TESTING.md`) has not been done against the running app, and `top_songs` was not run through the app against live providers.
- **State:** merged only. Not published or deployed.
- **Next action:** the owner checks the artist page in a browser and decides on the follow-ups listed in `ACTIVE_WORK.md` section 2d.

## 2026-10-29 — Quality priority drag replaced: PR #633 merged

- **Merged:** PR [#633](https://github.com/abucalip/navi-librarian/pull/633), squash commit `852cc9ad66381c46d2bb157156c2143fa2e64f8c`, from tested head `3ae1a6e5bedeb4cd866c106e027d3d68e4ac4d4f`, at the owner's direction.
- **What changed:** the Settings audio quality priority list (`static/app.js`, `static/app.css`, hint in `app/templates/index.html`) uses a pointer-event drag-to-reorder adapted from a public example: the grip is a 44px handle with `touch-action: none`, the grabbed row follows the pointer, passed rows slide aside by transform, and the row glides into its slot on release. Pointer cancel ends the drag at the last pointer position. The glide uses the `--dur-slow` and `--ease-out` tokens and is off under `prefers-reduced-motion`. Move up / Move down buttons, focus return, the polite announcement and the save payload are unchanged. `tests/test_quality_priority.py` now asserts pointer events and the grip instead of `draggable` and `dragover`.
- **CI finding:** the first head (`4d6eb2b`) failed `compile` and `test-and-build` on `test_motion_ui_contract` because the row transition used a literal `.25s`; durations must be motion tokens. Fixed in `3ae1a6e`; all required checks then passed.
- **Tests actually run (agent, locally):** `tests/test_quality_priority.py`, `tests/test_settings_ui_contract.py` and `tests/test_motion_ui_contract.py` (33 passed); `node --check static/app.js`. The full suite ran in CI only, per workflow policy.
- **UI results:** none. The drag was not exercised in a browser and the manual checklist (`LOCAL_UI_TESTING.md`) has not been done.
- **State:** merged only. Not published or deployed.
- **Next action:** the owner runs the manual browser check of the drag (mouse and touch) and the Move buttons on Settings, then decides on the next release.

## 2026-10-29 — Image v0.2.6 published

- **Authorization:** the owner reported that all manual browser tests were done and directed publication of current `main` as v0.2.6.
- **Checked before tagging:** local `main` equal to `origin/main` at `de8ba76107875ee4c158e4b16e94a6f86d21c07a` (the PR #632 merge `b4dc227` plus the docs commit `de8ba76`); all required checks had passed on the PR head and on `b4dc227` (compile, test-and-build, container-smoke, validate-container); no change besides documentation sits between `b4dc227` and the tag.
- **Published:** annotated tag `v0.2.6` at `de8ba76107875ee4c158e4b16e94a6f86d21c07a`; release workflow run [40884649738](https://github.com/abucalip/navi-librarian/actions/runs/40884649738) succeeded (`publish-release` success; `validate-release-workflow` skipped as designed). `ghcr.io/abucalip/navi-librarian:v0.2.6` and `:sha-de8ba76107875ee4c158e4b16e94a6f86d21c07a`; package version digest `sha256:4876c6a67817d6ad8a53c8d614d9c4ddcebb4920383e20ddcd5ab9e4408226cc` (GitHub Packages API). v0.2.5 is the rollback reference. `latest` was not moved and not checked; per-platform manifests were not inspected.
- **Not done:** deployment; runtime verification of the published image.
- **Next action:** the owner decides on deploying v0.2.6.

## 2026-10-29 — Dashboard genres and shelves, Recommended slider, library page tweaks: PR #632 merged

- **Merged:** PR [#632](https://github.com/abucalip/navi-librarian/pull/632), squash commit `b4dc2274c90b61d144ee6e2820f741100d976fb1`, from tested head `5849b95c198188f617bff03d6817d460e4d8a030`. Required checks passed on that head: `compile`, `test-and-build`, `container-smoke`, `validate-container`, `validate-release-workflow` (`publish-release` skipped, publishing paused). Checks on the merge commit were not looked at.
- **What changed:**
  - Dashboard: a Genres tile grid (Navidrome genres by album count, 12 shown, "View more" for up to 60; a tile opens the genre page) and four card shelves: New releases (the discovery list), Newly added, Recently played and Most played (Navidrome `getAlbumList2` newest, recent, frequent). Each card shows a check when owned and Get otherwise. New routes `GET /api/dashboard/genres` and `GET /api/dashboard/albums/{newest|recent|frequent}` live in `app/api/dashboard.py`, with the logic in the new `app/services/dashboard_sections.py`; `navidrome_server.py` was not touched (D-016).
  - Recommended row: a slider with one feature slide and three blurred coming-up thumbnails; Previous, Next, Left and Right keys, and thumbnail clicks. Plain CSS and JS. A first attempt with `::scroll-button` and `::scroll-marker` was dropped because Firefox does not support it.
  - Copy: search placeholder and label "Search your library or discover new music"; heading "Recommended"; the top-bar tagline, the gesture hint and the status bullet are gone.
  - Artist and album pages: five random similar artists as circles; the "Not in your library" line under them is gone; similar albums and artist albums show seven with an "All albums" button; unowned album pages show "Not in your library" under the year; the year is yellow and that line and the Apple Music source link are grey.
- **Tests actually run (agent, locally):** `tests/test_dashboard_sections.py` (new), `test_dashboard_routes.py`, `test_dashboard_service.py`, `test_library_search_ui_contract.py`, `test_ui_keyboard_and_feedback_contract.py`, `test_motion_ui_contract.py`, and a keyword-selected set (`library or search_ui or ui_ or dashboard or motion`); all passed. The full suite was run by CI only, per workflow policy. Existing assertions were updated to match the intended changes (route set, search copy, similar-artist photo size, the dashboard strip becoming a slider).
- **UI results:** checked in headless Chrome (and the slider in Firefox) against stubbed data at 760, 1100 and 1500 px; click, Previous and thumbnail rotation checked in Chrome. Not run against a live Navidrome. The manual browser checklist (`LOCAL_UI_TESTING.md`) has not been done.
- **Defect found and fixed during review:** `app/main.py` reads `index.html` once at startup, so a running server kept the old markup while `app.js` was served fresh; the new script then threw on the missing buttons and the artist and album pages rendered empty until the app was restarted. After a restart the pages worked. Restart or rebuild after any `index.html` change.
- **Limits:** the Newly added, Recently played and Most played shelves are always owned, so they show checks; a New releases card shows a check only if the server marks it owned. The similar-artist pick is made in the browser from the server's list of up to 20. The slider is built for about ten items and was not applied to the other scrolling card rows.
- **State:** merged only. Not published or deployed.
- **Next action:** the owner runs the manual browser checklist on the dashboard and the library pages; then decide whether to extend the slider to other card lists.

## 2026-10-28 — Refresh keeps the page: PR #631 merged; image v0.2.5 published

- **Merged:** PR [#631](https://github.com/abucalip/navi-librarian/pull/631), squash `5873e576ae6c04261e93431209dbf24de7c5e6b1`, tested head `aa51d05e02e0d04b609f3730e74294ba55a5086a`, at the owner's direction. Required checks (compile, container-smoke, test-and-build, validate-container, validate-release-workflow) passed on the head; the four workflows on `main` passed on the merge commit.
- **Built:** address hash for the page (`#<page>`, `#library/artist|album|genre?...`, URI-encoded, no secret); startup and `popstate` apply it with a dashboard fallback; `pushState` per page change so browser Back and Forward work, `replaceState` for the in-app library Back; login keeps the hash.
- **Bug found by the owner after the first build:** a blue rectangle around the artist or album name after a refresh. It was the browser focus ring on the heading the library views focus on navigation. Restoring from the address now skips that focus.
- **Tests run (agent, focused only):** `test_refresh_keeps_page_ui_contract` (9, including a Node round-trip of the hash helpers), `test_login_ui_contract`, `test_library_search_ui_contract`, `test_header_menu_ui_contract`, `test_album_modal_ui_contract`, `test_artist_deep_dive_ui_contract`; `node --check`. The grep-based run of every module that reads `app.js` (TEST_PLAN) was not done locally; CI ran the full suite and passed. A first `LIB-02` row clashed with the existing LIB-02 and was renumbered into LIB-04.
- **Published:** annotated tag `v0.2.5` at the merge commit; release workflow run [40753975898](https://github.com/abucalip/navi-librarian/actions/runs/40753975898) succeeded. `ghcr.io/abucalip/navi-librarian:v0.2.5` and `:sha-5873e576ae6c04261e93431209dbf24de7c5e6b1`; package version digest `sha256:543d16bb3ef3b95e9253d057055ce793d10f38cf8b9565f00f0b8096c287ec1c` (GitHub Packages API). v0.2.4 is the rollback reference. `latest` was not checked or moved; per-platform manifests were not inspected; the image was not pulled or run; no GitHub Release was created.
- **Not done:** manual refresh, Back and Forward check on each page type; deployment; runtime verification.
- **Next action:** the owner runs the browser checklist (`LOCAL_UI_TESTING.md`), or authorizes deployment of v0.2.5.

## 2026-10-28 — Library pages: PR #630 merged

- **Merged:** PR [#630](https://github.com/abucalip/navi-librarian/pull/630), squash `70b5330bb2c9ba46d7645427e3d943a268df7ab8`, tested head `327c477fdb9862670c78c7b94d0711c62f08de5e`, at the owner's direction. Scope: contract section 14.
- **Problems found in the owner's report:** search results did nothing when clicked for albums and unowned artists; the artist page showed only a name and owned albums; there was no album page. Causes: P1 deliberately made those rows inert (`SEARCH_CONTRACT.md` 11.5); the artist route returned 404 for an artist the library lacks; the UI discarded the `bio`, `missing_albums` and `similar` sections the API already returned.
- **Built:** a shared back stack over the artist, album and genre pages; links on every artist, album and genre name across the app; unowned artist pages (`?name=`); `tags` and `albums` sections (top 20 by listens, owned albums ticked, Get on the rest, a toggle for library-only); an album page (`/api/albums/...`: tracklist raced across Deezer, Last.fm and MusicBrainz, year, Apple Music editorial notes with Read more, logo-only service links, similar artists and albums); `/api/artist-image`, `/api/album-links`, `/api/album-description`; Navidrome as the bio source for owned artists; Library sidebar tab.
- **Bug found in live checks:** `albums_by_artist` used a MusicBrainz browse limited to 100 results; for Radiohead (388 album-type release groups) the first 100 were all live recordings, so the filtered list was empty and the page fell back to Last.fm albums with no year or ListenBrainz count. Fixed with a studio-album search query; the affected cache entries were renamed.
- **Performance changes:** artist and album pages stream sections as they finish; the artist's MusicBrainz ID is resolved once per page (three jobs had queued for it behind the 1 req/s limit); page deadline 8 s; tag lookups per similar-artist list cut from 10 to 4. Live sample: Radiohead page, albums and tags within a few seconds, similar artists last at 6 to 8 s.
- **Tests run (agent, focused only):** `test_api_search_routes`, `test_metadata_routes`, `test_album_links`, `test_apple_description`, `test_discovery_search_artist_sections`, `test_discovery_search_album_page`, `test_discovery_search_similar`, `test_discovery_search_query`, `test_discovery_search_providers`, `test_discovery_search_similar_precompute`, `test_discovery_search_index`, `test_discovery_search_genre`, and the 35 test modules that read `app.js`, `app.css`, `index.html` or `icons.svg`; compileall and `node --check`.
- **CI:** the first push failed `compile` and `test-and-build` on two source-contract tests in `test_ui_keyboard_and_feedback_contract.py` (a moved line in `openAlbumModal`, and the dashboard tile text no longer `aria-hidden` because its names are now links). That file does not match the `*ui_contract*` name pattern the agent had used to find UI tests, so it was not run locally. Both tests were updated; the new head passed all required workflows.
- **Live checks (isolated instance, owner's Navidrome, public providers):** Navidrome `getArtistInfo2` bios; unowned artist pages; album tracklists in about 0.4 s; exact Apple Music, Deezer, MusicBrainz and ListenBrainz album URLs; Apple notes for Daft Punk, Radiohead and Portishead albums (none for Frank Ocean "Blonde"); artist photos from Deezer. The Odesli (song.link) API returned 401 (deprecated) and was dropped.
- **Not done:** the manual browser checklist (`LOCAL_UI_TESTING.md`), so layout, focus, narrow widths and Safari are unchecked; publication; deployment; runtime verification.
- **Limits:** Spotify, Qobuz and Bandcamp keep search links; Qobuz and ListenBrainz use drawn monograms; Apple notes depend on the public page layout; several same-name library artists open the one with the most albums when linked from a card.
- **Next action:** the owner runs the browser checklist, then decides on the refresh-keeps-the-page task (`ACTIVE_WORK.md` section 2e).

## 2026-10-26 — Published image v0.2.4

- Owner explicitly authorized publication of current `main`. Annotated tag `v0.2.4` was pushed at `b79a229dbca2e36bb96e523be12dff0a579139db`, the `main` head (`docs: close out P5, add P2-P4 focused checks to the test plan`). The four required workflows had passed on that commit.
- Release workflow "Publish Docker release" run [40261391680](https://github.com/abucalip/navi-librarian/actions/runs/40261391680) succeeded.
- **Published:** `ghcr.io/abucalip/navi-librarian:v0.2.4` and `ghcr.io/abucalip/navi-librarian:sha-b79a229dbca2e36bb96e523be12dff0a579139db`; package version digest `sha256:3ec82f0d1c20260c0d8f4e82d075972a704673fee54bda5b33d6ad9086827203` (from the GitHub Packages API). `latest` was not checked or moved by this step.
- **Contents:** global search P1 to P5 (owned index, network sources, similar artists, Discogs and genre pages, latency script), the provider-cache read fix (PR #628), the MusicBrainz throttle change (PR #627), and the precompute cursor (PR #629), plus other changes merged since v0.2.3. The v0.2.3 image is the rollback reference.
- **Not verified:** per-platform manifests were not inspected, the image was not pulled or run, no GitHub Release was created. Not deployed; no live-runtime verification. Real-browser checks for global search remain deferred by the owner.

## 2026-10-26 — P5 closeout; PRs #628 and #629 merged

- **Merged at the owner's direction:** PR [#628](https://github.com/abucalip/navi-librarian/pull/628) (`2ce6f02`) and PR [#629](https://github.com/abucalip/navi-librarian/pull/629) (`1984d3b`). Required CI passed on each exact head (`83bb39b`, `6b72bbd`): compile, container-smoke, test-and-build, validate-container, validate-release-workflow.
- **#628 fixes a bug found by the P5 runs:** the search routes passed `_discovery_read_list` straight to the provider cache, but the store wraps each entry as `{"payload": entry, ...}`, so every provider-cache read missed. Repeat searches re-queried every source, and artist pages never read cached similar-artist, tag or bio entries. After the fix a repeated `radiohead` search went from 651 ms to 14 ms with both sources `cached` (live, isolated data directory). The `FakeLibrarian` test double now returns the real shape. This likely also explains part of the "partial artist pages until the tag cache is warm" follow-up; not re-measured on an artist page.
- **#629 (P3 follow-up, fixed precompute order):** a pass continues where the last one stopped (cursor `similar-precompute-cursor`) instead of restarting at the first artist.
- **Cache decision:** finished sources are cached per source and now actually served. A source that times out is still not cached (contract 8.1), so a repeat search with a slow MusicBrainz still waits for it; the 3.0 s `done` target is not reliably met in that case.
- **Live precompute sample (12 library artists, live providers, two runs):** 11 to 16 s per artist, 91 to 159 MusicBrainz calls, 8 to 10 ListenBrainz and 10 Last.fm calls for 12 artists; 10 complete and 2 `failed` each time (error type not examined). The first run saw 6 MusicBrainz 503s of 159. A full pass of 732 artists extrapolates to about 2.3 to 3.2 h. Not a measured full pass.
- **Not done, deferred by the owner:** weight and scale tuning, the 61-artist evaluation (started, stopped), the cause of the 2 failed artists, the full-library precompute timing, partial artist pages re-check, a settings switch for precompute, and all real-browser checks.
- **Release state:** no image publication, deployment, or runtime verification. Full suite not run by the agent (owner rule).
- **Next action:** the owner's next priority; P5 is closed with the exceptions above.

## 2026-10-26 — P5: live run tests and the MusicBrainz throttle change

- **PR #626 merged** (`1a8c062`). **PR [#627](https://github.com/abucalip/navi-librarian/pull/627) open** (owner decision: accept partial results when MusicBrainz throttles): a 503 backoff that cannot fit in the remaining deadline now reports `rate_limited` at once. Focused tests: 136 OK; the full suite was not run. Live re-measure, 6 searches 8 s apart: deadline hit on 1 of 6 (3 to 5 of 5-6 before); `done` p50 2.3 s, p95 3.0 s, so the 3.0 s and cache-hit targets are still not reliably met while MusicBrainz is slow.
- **Live run tests (real Discogs token, real Navidrome library, live MusicBrainz and Last.fm; an isolated data directory; slskd disabled):**
  - **Discogs genre extraction:** `genres("shoegaze")` returned 1 (`Shoegaze`), `genres("jazz")` 11 (`Jazz`, `Free Jazz`, `Soul-Jazz`, …), a nonsense query 0; 0.4 to 1.6 s.
  - **`Ash (2)` suffix:** raw Discogs artist titles included `Ash (3)`, `Ash (35)`, `Ben Ash (2)`; the app's cleaner returned `Ash`, `Ash`, `Ben Ash`; none of the 50 `artists("ash")` candidates kept a `(`.
  - **Real 429:** an unpaced burst got `rate_limited` on call 62 after 21.4 s, matching the documented 60 per minute; the paced client never hit it.
  - **Settings Test:** `POST /api/settings/discogs/test` (the route the button calls) returned `{"ok": true}` with the token from `DISCOGS_TOKEN` (source `environment`). The button itself was not clicked: no browser was available.
  - **Whole app against live providers, through the API with a signed-in session:** search `shoegaze` showed Discogs, Last.fm and MusicBrainz sources and a Discogs genre result, with MusicBrainz `rate_limited` after 2.7 s and `partial: true`; search `slowdive` ended at 3.0 s with `deadline_hit` (MusicBrainz `timeout`); the `shoegaze` genre page returned 30 artists (`source_failed`, partial) and 30 albums (complete); an owned artist page returned `artist`, `owned_albums` and `bio` but `missing_albums` and `similar` as `deadline` (the known cold-cache behavior). No tracebacks in the app log.
- **Not done:** any check in a real browser (Settings button, keyboard and focus, narrow widths, Safari, VoiceOver); ListenBrainz-backed similar results with a warm cache; the P3 precompute timing. No image publication, deployment, or runtime verification.
- **Next action:** the owner reviews and merges PR #627.

## 2026-10-26 — P5: latency measurement (PR #626 open, not merged)

- **Tool:** `scripts/search_latency.py` with `tests/test_search_latency_script.py`, in [PR #626](https://github.com/abucalip/navi-librarian/pull/626) (head `5f8cf3dc567eef74ba22a03169779a8e41196dff`; compile, container-smoke, test-and-build and validate-container passed). It serves the real search router in a throwaway app with an isolated data directory and times real HTTP/SSE requests. The merge was not done: the permission check denied it, so it waits for the owner. Focused tests run: the new module, `test_discovery_search_runner`, `test_api_search_routes` (45 tests, OK). The full suite was not run (owner rule).
- **Setup:** the owner's Navidrome library (12,097 songs, 732 artists, 1,745 albums), read-only, from the owner's machine over the network, not from the server host. Browser-side targets were not measured.
- **Index build (target ≤ 10 s):** cold 2.67 s, warm 1.95 s and 2.15 s (a first run recorded 2.64 s). Met on this library.
- **Owned search, warm index (server, over HTTP):** 40 library-derived queries, first result p50 6.8 ms, p95 8.3 ms, max 25 ms (target p95 ≤ 100 ms); `done` p95 10 ms. No query returned nothing. Met.
- **External search, live MusicBrainz and Last.fm, 5 to 6 queries per run, three runs:** first external result p95 0.64 to 0.84 s (target ≤ 1.5 s): met. `done` is **not** met: `deadline_hit` on 4 of 5, 5 of 5 and 3 of 6 cache-miss searches, `done` at 3.0 s. Cause for the album part: MusicBrainz often answers the release-group search with 503 on the first call (the app's own provider class got a 503 on the first call for 2 of 3 queries, and direct curl calls of the same query got a 503 for 2 of 3 in one sitting and 2 of 11 in another), and the app's retry waits of 1 s and 2 s use the whole 3.0 s deadline; one run had MusicBrainz at 3.0 s `timeout` every time. Artist and genre parts finished in 0.24 to 0.31 s; Last.fm in 0.56 to 0.95 s. Direct calls varied from 0.2 s to 4.7 s. My own repeated test calls may have raised the 503 rate; the sample is small and not a statistically valid p95.
- **Cache-hit target (`done` ≤ 300 ms, every source `cached`): not met.** A search that hits the deadline is not cached, so the repeat also waited for MusicBrainz (`done` p50 2.5 to 3.0 s).
- **Open for the owner:** whether to change the MusicBrainz retry (for example, no wait-and-retry that cannot fit in the remaining deadline) or accept `partial` results when MusicBrainz is throttled. Not changed here: P5 measures and does not alter provider behavior.
- **Not done:** the other live run tests the owner scheduled for the end of P5 (Discogs genre extraction, a real 429, the `Ash (2)` suffix, the Settings Test button, the app in a browser). No image publication, deployment, or runtime verification.
- **Next action:** the owner reviews and merges PR #626, then decides on the MusicBrainz retry; then the remaining live run tests.

## 2026-10-26 — P4 owner decisions recorded

- **Approved by the owner:** `tag_source: "navidrome"` for owned genre results (contract 3.8 amendment), and owned items before unowned on genre pages. Recorded in `docs/SEARCH_CONTRACT.md` 3.4, 3.8 and 13.3; no code change, since both were built that way.
- **Scheduled by the owner:** the remaining live run tests (Discogs genre extraction, a real 429, the `Ash (2)` suffix, the Settings Test button, the app against live providers) run at the end of P5.
- **Next action:** P5.

## 2026-10-26 — Global search P4 closed out; partial live Discogs check

- **P4 is complete:** PRs #623 (`2f66598`), #624 (`13cb7d3`) and #625 (`afade38`) are merged. Exact heads and CI runs are in the entries below. The P4 record is `docs/SEARCH_CONTRACT.md` section 13, which also now holds the genre page design (3.4), the `tag_source` rule (3.8), and the closed header-format item (5.2, 9).
- **Live Discogs check, run with the app's own client code and a real personal access token:** the Settings Test call returned `ok`; the `Authorization: Discogs token=…` header was accepted; `artist_styles("Slowdive")` returned 9 styles in 0.7 s; `style_albums("Shoegaze")` returned 50 masters in 1.2 s; `artists("slowdive")` returned 50 records in 0.4 s; `albums("souvlaki")` returned 48 usable records of 50 in 2.0 s; a wrong token failed with `ProviderError("failed")` rather than an empty list. MusicBrainz `/genre/all?fmt=txt` returned 2,216 names including `shoegaze`.
- **Not exercised live:** Discogs genre extraction; a real HTTP 429; the `Ash (2)` suffix; the Settings Test button in the app; the whole app against live providers. Manual browser checks were waived by the owner and not performed. The live run reads and does not change any state; the token file used for it was a local file outside the repository.
- **Open owner decisions:** `tag_source: "navidrome"` for owned genre results; owned-before-unowned ordering on genre pages.
- **Release state:** no image publication, deployment, or runtime verification.
- **Next action:** P5 (latency measurement against section 2.1 and `TEST_PLAN.md` entries). The P3 and P4 follow-ups in `ACTIVE_WORK.md` section 2d stay open.

## 2026-10-26 — P4 review and PR #623 merge; PRs #624–#625 held

- **Merged:** PR #623, P4a Discogs token settings, squash commit `2f6659978195cd314faa26dbc259fd9ae68ad751`, from exact reviewed head `19549f14101fbe6a8a7e4b94707b63cf4af6235b`.
- **CI evidence:** all five associated workflows passed on that exact head: `test-and-build` / full unit suite and image build (run `40254517946`), Python syntax/safety (run `40254517856`), container smoke (run `40254517841`), non-publishing image validation (run `40254517876`), and release-workflow validation (run `40254517937`; publish job skipped). No full suite was run manually.
- **Integration limitation:** no live Discogs request with a real token was performed. The contract's open verification of `Authorization: Discogs token=…` remains outstanding for the provider integration; mocked tests establish only the header shape.
- **PR #624:** re-reviewed exact head `33e20afb263469e2032116a6d60554972ad6ec05`. Previous deadline-reporting, Discogs global artist/album query, and cross-candidate attribution findings appear fixed with regression tests. Held because global `genre` search remains `not_in_this_build` despite the approved P4 contract, and no GitHub Actions runs/statuses exist on this exact head. Base was retargeted to `main` after #623 merged.
- **PR #625:** re-reviewed exact head `628270e0716212dad67e4ea04f796db1849837d2`. Genre-to-artist return navigation appears fixed. The owner waived manual browser testing for this batch; no Actions runs/statuses exist on this exact head, so automated CI remains a merge gate. Also held while the P4 global-genre contract gap in #624 remains unresolved.
- **Release state:** no publishing, deployment, or runtime verification. PR #624 and #625 remain open and unmerged.
- **Next action:** implement and regression-test the contracted global genre results, then run all required workflows on the final #624/#625 heads; retain the live Discogs-token integration check as an explicit outstanding verification item.

## 2026-10-26 — Global search P3 closed (PRs #621 and #622)

- **Merged:** PR #621 (squash `7f1b44f`), the similar-artist fusion slice, after the owner narrowed P3 on 2026-10-26. PR #622 (squash `05b259c`), P3b: shared MusicBrainz tags, owner play-count boost, and daily precompute.
- **Verification:** each PR's required workflows passed on its exact final head. The full unit suite ran in CI, not locally. Focused modules were run by the agent at each step (165 tests in the final P3b set). Size and legacy-import guards passed.
- **Not verified:** no live MusicBrainz, ListenBrainz or Last.fm calls; nothing against the owner's library. Weights and budgets are starting values.
- **Known gaps:** listed in `docs/ACTIVE_WORK.md` section 2d (live check and timing, tuning, partial artist pages until the tag cache is warm, fixed precompute order).
- **Release state:** not published, deployed, or runtime verified.
- **Next:** P4 (Discogs and genre pages), per the owner's direction on 2026-10-26.

## 2026-10-26 — Global search P2 complete (PRs #613 to #620)

- **Merged:** PR #620 (squash `262486e`), slice F: the first identity pass on the owner's library, the identity cleanup, and the correction path. PR #620 includes a generation-race fix from review, so the cleanup reads the current generation at delete time.
- **P2 summary:** section 12.10 of `docs/SEARCH_CONTRACT.md`.
- **Superseded:** PR #617 (closed) and PR #619 (docs-only, superseded by #620; open).
- **Next:** P3 only when the owner starts it.

## 2026-10-26 — Review, full CI suite, and merge PR #620

- **Reviewed final PR head:** `de8376b55435264c31ff5408179bafdf4c6535f5`. The previous blocking generation-cleanup race is addressed: cleanup reads the current generation at the point of deletion and removes only numerically older records; the pass checks the generation again before starting identity resolution. A deterministic regression test flips generation between the initial check and cleanup and asserts that the new-generation manual record survives.
- **Tests and CI:** all four required workflows passed on the exact PR head. Docker packaging/full unit suite/image build passed (run `40247599274`, job `test-and-build`, including the `Run unit tests` step); Python syntax and acquisition-safety checks passed (run `40247599271`); container runtime smoke passed (run `40247599291`); non-publishing multi-architecture validation passed (run `40247599292`, publish disabled). Release workflow validation passed (run `40247599282`); its `publish-release` job was skipped. Manual browser verification was waived by the owner.
- **Merged:** PR #620 by squash as `262486e7ce11bd11f74e5204990dfcc48ee99891`. GitHub confirms merged. Documentation status was updated in commit `ce8cb05328f3a79fc3605963b6d106938629d850`.
- **Delivered:** global search P2 is complete through slice F: generation-safe identity cleanup, identity correction/reset endpoints, and transport-error handling in the identity pass.
- **Release state:** no image publication, deployment, or runtime verification occurred. The full unit suite was run by CI on the exact reviewed PR head, not manually in this environment.
- **Next action:** start P3 (similar artists) only when the owner directs it.

## 2026-10-26 — Global search P2 complete; first identity pass (branch `search-p2f`)

- **First identity pass on the owner's library:** 409 artists and 1745 albums processed (744 unresolved). Artists with an MBID: 609 of 732. Albums with a release-group MBID: 1114 of 1745. 103 MusicBrainz requests, 195 s. A second pass made no calls.
- **Fixed in this slice:** a MusicBrainz timeout no longer aborts the pass; the background pass uses a 30 s timeout.
- **Added:** cleanup of old-generation identity records; the correction path (`PUT` and `DELETE /api/identities/{kind}/{id}`).
- **Closed:** PR #617 (superseded by #618).
- **Contract:** section 12.11.

## 2026-10-26 — Global search P2 slice E merged (PR #618)

- **Merged:** PR #618 (squash `a37f804`) at head `77993e2`. Required workflows passed on that head; the unit-test step reported `Ran 1870 tests … OK`.
- **Contract:** section 12.9 now says merged. Section 12.10 lists what remains in P2.
- **Replaced:** PR #617 (base `search-p2d`, so it had no checks) was superseded by #618. Close #617 when convenient.

## 2026-10-26 — Global search P2, slice E (branch `search-p2e`, stacked on `search-p2d`)

- **Approved:** permanent storage of MusicBrainz identities; a background pass after each owned-index build; artists and albums.
- **Built:** `discovery/identity.py` (the resolve pass and a single-flight job); batched release-to-release-group and album-title lookups (`providers.py`); store prefix read and batch write (`store.py`); the snapshot keeps each album's release MBID; owned entries carry MBIDs; owned matches use MBIDs when both sides have one; the artist page uses the stored MBID.
- **Verification:** focused modules pass (218). Guards pass. The release-to-group batch was checked live with three library IDs. Not run: the full suite (CI), a live identity pass over the whole library.
- **Contract:** section 12.9.

## 2026-10-26 — Global search P2, slice D (branch `search-p2d`)

- **Probe:** Navidrome serves `musicBrainzId` on 43% of artists (314 of 733) and 49% of albums (858 of 1745). Not a majority. Artist MBIDs need one `getArtist` call each. Album MBIDs are release IDs, not release-group IDs.
- **Built:** artist-page identity from Navidrome's tag when present. Last.fm top albums on the artist page, merged with MusicBrainz. Batched MusicBrainz identity lookup (built, not called yet). Background prefix delete of old-generation cache entries.
- **Verification:** focused modules pass (192). Guards pass. Not run: the full suite (CI), live Last.fm and MusicBrainz calls, the artist route against a live server.
- **Contract:** section 12.8.

## 2026-10-25 — Search panel shows two sections only (branch `search-p2c`)

- **Owner direction:** the search panel shows only "In your library" and "Not in your library". Provider names, per-provider status and popularity do not appear in it.
- **Done:** the per-provider status lines added in slice C are removed from the UI. The `source` events still reach the stream. The contract (section 8 and 12.6) is updated to match.
- **Resolved:** ListenBrainz is not a search source. Search reports it `not_in_this_build`. Its only use is popularity on the artist page's `missing_albums`, which orders the album list.

## 2026-10-25 — Global search P2, slice C (branch `search-p2c`)

- **Fixed:** the search UI showed provider results as "in your library". Results now split into "Not in your library", and each provider's state shows on its own line. The summary counts owned and external results separately. Artists not in the library do not open the artist view.
- **Fixed:** an artist page whose album list is known before the deadline keeps that list when popularity is late.
- **Tests:** UI contract assertions for the split, source status and owned-only artist click; the Last.fm generation test. Focused modules pass (171), guards pass, `static/app.js` parses. Not run: the full suite (CI), a browser check of the UI.
- **Deferred with reasons:** `SEARCH_CONTRACT.md` section 12.7.

## 2026-10-25 — Global search P2, slice B (branch `search-p2b`)

- **Merge:** PR [#614](https://github.com/abucalip/navi-librarian/pull/614) squash-merged as `f2da69505bce733f62980881fd993ed02e722914` from reviewed head `1da2c0ba710d7abe0a82f3f3a846d9c31a5c7976`. No publication, deployment, or runtime verification.

- **Built:** the artist page's `bio` and `missing_albums` sections, run on separate threads under the 3.0 s deadline. `missing_albums` resolves the owned artist's MusicBrainz identity by exact name, browses its studio albums, drops owned and duplicate albums, and orders by ListenBrainz listen count (`discovery/search/artist_sections.py`, `providers.py` browse, `network.py` `artist_network`). `bio` reuses the existing bio service through a route adapter (`app/api/search.py`).
- **Contract:** section 8.0 rule (agents never run the full unit suite); section 12.3 to 12.5 record slice B, its deviations and what is still open.
- **Verification:** focused modules reported 164 passed, including the new artist-section and browse tests. On exact PR head `1da2c0ba710d7abe0a82f3f3a846d9c31a5c7976`, all four required workflows passed: Docker packaging/full unit suite/image build (`40241617604`; unit tests and image build succeeded), Python syntax and safety checks (`40241617609`), container runtime smoke (`40241617581`), and validation-only multi-architecture image validation (`40241617635`, publishing paused). The full unit suite passed in CI and was not run manually. Release workflow validation passed (`40241617634`); publishing was skipped. Not verified: live provider calls and the artist route against the real Navidrome server. No browser test was applicable.
- **Still open:** the "Not in your library" UI group; Last.fm on the artist page.

## 2026-10-25 — Global search P2, slice A (branch `search-p2`)

- **Built:** external text search for not-owned artists and albums from MusicBrainz (artist and release-group search, 503 backoff and retry) and Last.fm (artist and album search, only when a key is saved). New modules: `discovery/search/limiter.py` (per-source pacing; a call that cannot start within the deadline is `rate_limited`), `cache.py` (depth-50 provider entries, 24 h, 1 h for definitive empty answers), `providers.py`, `merge.py` (owned suppression, dedupe by MBID then key plus year, ranking), `runner.py` (3.0 s deadline, shared calls with reference counting, cancellation when the last consumer leaves, complete-only caching) and `network.py` (wiring). `GET /api/search` streams `source` and `result` events when `scope=all`; `scope=owned` touches no provider and no cache.
- **Settings:** `lastfm_generation` counter, incremented when the saved Last.fm key changes (`settings/service.py`).
- **Verification:** focused tests `test_discovery_search_providers.py`, `_merge.py`, `_runner.py`, and the existing search route, event, index, query and normalize tests (119 passed). Settings tests pass except three collection errors that also occur on `main`. `check_server_size` and `check_app_legacy_imports` pass. An end-to-end run through the real wiring with a fake HTTP layer showed owned suppression, source states and a repeat search served from cache with no provider call. Not run: the full unit suite (CI runs it), real provider calls, browser checks.
- **Not in this slice (P2 slice B):** ListenBrainz (reported `not_in_this_build` for now), the artist page `bio` and `missing_albums` sections, and the "Not in your library" UI group.
- **Deviations, recorded in `docs/SEARCH_CONTRACT.md` section 11.9.**

## 2026-10-25 — Global search P1 closed (docs)

- **Closed:** P1 of `docs/SEARCH_CONTRACT.md`, with PRs #609 (backend), #610 (UI, checklist waived), #611 (artist genre) and #612 (Various Artists and 502 gaps) merged.
- **Carried forward:** build-time record (P5), the manual refresh route and album artwork (both proposals, not approved), the "Not in your library" group (P2), the recommendation snapshot gap, and real-browser checks in Safari, VoiceOver and keyboard-only use.
- **Next:** the owner chooses the next phase.

## 2026-10-25 — P1 follow-ups recorded (main)

- **Recorded in `docs/SEARCH_CONTRACT.md` section 11.8:** build-time measurement on the owner's server (P5), and a proposed `POST /api/library/refresh` route that is not approved and not built.

## 2026-10-25 — P1 gaps closed (branch `p1-gaps`)

- **Closed:** "Various Artists" never becomes an artist result. The index reuses `is_various_artists` (section 4.2), so search, the library list and the artist route all exclude it. The artist route's 502 body is tested to contain only `code` and `message`.
- **Verification:** the index, query, route, snapshot, normalize and events modules pass, including the new tests. Boundary, app-start and guard checks pass, and `navidrome_server` is still not loaded by the search code. All 29 UI contract modules pass.
- **Recorded in section 11.7:** the artwork route's file location and the grouping deviation. Build-time recording moves to P5 (it needs the owner's Navidrome server).

## 2026-10-25 — Artist genre on search results (branch `artist-genre`)

- **Owner decisions:** the disambiguator is "Artist (genre)". The source is the Navidrome album genre tag. An artist with no genre falls back to the album count.
- **Change:** the library snapshot keeps each album's `genre`, and the owned index gives each artist the most common album genre. Artist search results carry `genre` (string or null). The UI shows "Name (genre)" when a genre exists. Contract section 11.6 and section 3.8.
- **Verification:** focused backend modules pass (search, routes, snapshot, artwork, Navidrome client and generation, legacy boundary, size guard). All 29 UI contract modules pass. The jsdom harness passes 55 checks, including "Ash (Rock)" and a name alone without a genre. Live stub run: the artist with genre-tagged albums returns `"genre": "Rock"`; the artist with none returns `null`.
- **Not verified:** the genre field on a real Navidrome server (the owner's server was not queried; the tag is assumed from the Subsonic album record), and browser rendering of the new name.

## 2026-10-25 — Search UI layout pass (branch `search-ui`)

- **Scope:** step 4 of the critique (`/impeccable layout`): the artist view's hierarchy and artwork.
- **Changes:** the artist view leads with an artwork hero (160 px, 128 px on phones) from the clicked row's `artwork_url`, so the artist API gains no field. The artist name takes page-title styling (the `.panel h2` treatment, with its chart-red rule) and stays an `h3`, so heading order is unchanged. The Library intro is hidden while the artist view is open and returns with the list.
- **Verification:** the jsdom harness passes 53 checks, including the hero image source and the intro toggle. Chromium at 1280 px and 390 px: the hero and albums render, no horizontal overflow, and the intro is hidden. All 29 `*ui_contract*` modules pass.
- **Not verified:** album art (needs the contract proposal in 11.6), long artist names beyond the checked case, Safari, and screen readers. The hero art is blank in screenshots because the stub returns an invalid JPEG.

## 2026-10-25 — Search UI polish pass (branch `search-ui`)

- **Scope:** step 3 of the critique (`/impeccable polish`): streamed results, running count, and no flicker between queries.
- **Changes:** each result is placed in its type group as it arrives, and groups stay in Artists, Albums, Songs order. The status shows "Searching… N matches so far", with `aria-live` off while streaming and polite at the end. Previous results stay until the new stream's first event. A server error keeps the results already shown.
- **Verification:** the jsdom harness passes 50 checks, including results before `done`, the running count, group order, the partial results on error, and the live-region state. Chromium: keyboard, focus, hover and copy checks pass with no errors; the phone heading and status are visible. All 29 `*ui_contract*` modules pass. The stub responds too fast to observe streaming in a real browser, so the streaming behaviour is verified in jsdom only.
- **Not verified:** streaming against a slow real Navidrome, screen-reader output, Safari.

## 2026-10-25 — Search UI clarify pass (branch `search-ui`)

- **Scope:** step 2 of the critique (`/impeccable clarify`): dead album and song rows and the copy that promised them.
- **Changes:** album and song rows are plain rows with no hover state. Only artist buttons highlight. The placeholder is "Search your library", and the library intro is "Select an artist to see their albums." The header tagline rules are scoped to `.header-tools > p`, because the bare `header p` rule right-aligned and, on phones, hid the search status and group headings.
- **Verification:** the jsdom harness passes 43 checks. Chromium: album rows have a transparent hover background, artist buttons keep theirs, the new copy renders, and there are no page errors. Phone width: the group heading and status are visible and the tagline stays hidden. All 29 `*ui_contract*` modules pass, including the new copy and tagline tests.
- **Not verified:** Safari, VoiceOver, and a real Navidrome library.

## 2026-10-25 — Search UI harden pass (branch `search-ui`)

- **Scope:** step 1 of the critique (`/impeccable harden`): search keyboard and ARIA, heading order, and load-more retry.
- **Changes:** the searchbox has no combobox ARIA; Escape is handled on the form; focus leaving the form to a real outside element closes it, while a null target does not (Safari click path); group headings are `<p>` instead of `<h3>`; a failed append retries the append instead of resetting the list.
- **Verification:** the jsdom harness passes 43 checks, including Escape from a result, the focus-out rules, and the append-failure retry. Headless Chromium: Escape from a result and Tab out close the panel, a mouse click still opens the artist, the console is clean, and overflow is 0 at both widths. `tests/test_library_search_ui_contract.py` (13) and all 29 `*ui_contract*` modules pass. The detector no longer reports the search heading skip; its one remaining finding is the pre-existing settings-tabs warning.
- **Not verified:** Safari and VoiceOver. The null-target focus rule is written for Safari's click behaviour but was not tested in Safari.

## 2026-10-25 — Global search P1 UI (branch `search-ui`)

- **Merged before this work:** PR #609 (squash `52b0010`), after the owner approved it. The review finding on SVG artwork was fixed in `62fd363` (raster allowlist plus nosniff), and CI passed on that head.
- **Change:** top-bar search (`GET /api/search` over SSE, debounced, grouped results, Escape and outside-click close), a Library page from the header menu (filter, sort, Load more, index-state messages), and an artist view with owned albums. `static/app.js`, `app/templates/index.html`, `static/app.css`. Contract section 11.5.
- **Tests run:** `tests/test_library_search_ui_contract.py` (9). All 29 existing `test_*ui_contract*.py` modules pass, after updating one pinned phone margin in `test_shell_rail_ui_contract.py` for the new header row.
- **Browser checks run by the agent (not the owner's checklist):** a jsdom harness drove the page script against stub API and stream responses (36 checks: library paging, filter and sort, artist view and back, search streaming, superseded and error streams, index states, search-to-artist, 404). Headless Chromium at 1280 px and 390 px: no console errors, no horizontal overflow, screenshots reviewed.
- **Not verified:** the owner's manual checklist, keyboard-only pass, reduced motion, screen readers, a real Navidrome library.
- **Release state:** branch only. No merge, publication or deployment.

## 2026-10-25 — Global search P1: artwork and approvals (PR #609)

- **Owner decisions:** the 10% sanity threshold is approved; the recommendation snapshot's unscoped key is accepted as a deferred follow-up; owned artwork must be served.
- **Change:** `GET /api/owned/artwork/{id}` (`app/api/owned_artwork.py`) returns Navidrome cover art through a signed `getCoverArt` request made on the server. `integrations/navidrome/client.py` gained `cover_art()`, and its request signing is shared with `api_call`. Owned results carry `artwork_url` pointing at this route.
- **Tests run (focused):** `test_navidrome_cover_art.py` (10, including the raster allowlist and SVG refusal), `test_api_owned_artwork.py` (5), `test_navidrome_client.py`, `test_discovery_search_query.py` (20), plus the earlier P1 modules. The stub end-to-end check returned 200 `image/jpeg` with `Cache-Control: private, max-age=3600`.
- **Not verified:** browser rendering of artwork (no UI yet); behavior against a real Navidrome cover endpoint.

## 2026-10-25 — Global search P1 backend (PR #609)

- **Scope:** `docs/SEARCH_CONTRACT.md` P1 backend, approved by the owner on 2026-10-25 against `main` `ddb58a8` (PR #608). Adds the owned index (`discovery/search/`), `GET /api/search` (SSE, owned results only), `GET /api/artists/{key}` (JSON and SSE, owned sections), and `GET /api/library/artists`, with routes in `app/api/search.py` and `app/api/library.py`. Supporting changes: album `artist_id` in the library snapshot; a `navidrome_generation` counter in settings, bumped on any Navidrome URL, user or password change.
- **Decisions:** recorded in `docs/SEARCH_CONTRACT.md` section 11 and `docs/DECISIONS.md` D-017.
- **Tests run (focused, by the agent):** `test_discovery_search_*.py` (46 tests at last run), `test_api_search_routes.py`, `test_navidrome_generation.py`, `test_discovery_library_snapshot.py`, `test_service_settings.py`, `test_settings_routes.py`, `test_app_legacy_import_boundary.py`, `test_auth_routes_integration.py`, `test_api_discovery_injection.py`, all passing. The full unit suite was not run by the agent (owner rule); CI runs it on the PR head.
- **Guards:** `scripts/check_server_size.py` passes (`navidrome_server.py` 2,457 lines, ceiling 2,650); `scripts/check_app_legacy_imports.py` passes.
- **Local end-to-end check (not a repository test):** a throwaway Subsonic stub on localhost with an app account created through `/api/auth/setup`. Library paging reported `fresh`; search streamed `capabilities`, owned `result` events and one `done` with `partial: false`; an ambiguous artist key returned `409` and `?id=` resolved it.
- **Not verified:** the UI (not built), browser behavior, latency targets in section 2.1, behavior against the owner's real Navidrome server, and CI on the PR head.
- **Release state:** branch only. No merge, publication or deployment.

## 2026-10-25 — Current tastes replaces Now (PR #607)

- **Merged:** PR [#607](https://github.com/abucalip/navi-librarian/pull/607), squash commit `690c718d8f89dfb9a1d5d28482b8335f4fde4f59`, from reviewed head `2b5e3f62540710a9487ad5fb2858a7eb167750d7`.
- **Change:** Replaced the Now daily-picks lens with Current tastes. It builds seeds from a recent listening window, adds similar-artist and collaborator links, and ranks with regional and era signals. Release-year metadata now enriches legacy popularity-cache entries missing a year; tests cover legacy cache enrichment and the no-extra-search fast path when a year is already present.
- **Review follow-up:** The prior medium-severity cache finding was addressed in the updated head. The legacy path searches for years without refetching album popularity, then rewrites cache entries; cached entries already containing a year avoid that extra search.
- **Verification:** CI passed on exact PR head `2b5e3f62540710a9487ad5fb2858a7eb167750d7`: Docker packaging/full unit suite/image build (run `40205211049`), Python syntax/acquisition-safety (run `40205211052`), container runtime smoke (run `40205211051`), and validation-only multi-architecture image validation (run `40205211070`). Release validation (run `40205211056`) passed with publishing skipped. PR reports 299 focused tests; the full unit suite was run by CI, not manually.
- **UI gate:** The owner waived manual UI review. No browser test was performed.
- **Release state:** Merged only. No publication, deployment, or runtime verification.

## 2026-10-24 — Published image v0.2.3

- Owner explicitly authorized publication after PR #605 merged. Annotated tag `v0.2.3` was pushed at `7883fe93a0559ca46381e6ef8bd91eaab556ca31`, the then-current `main` head (`docs: record lens lists default-on decision`). All four required workflows had passed on that exact commit.
- Release workflow "Publish Docker release" run [40127930984](https://github.com/abucalip/navi-librarian/actions/runs/40127930984) succeeded (`publish-release`; the validation job was skipped for a tag push). It enforced tag == current `main`, ran the container smoke test, and built `linux/amd64` and `linux/arm64` with provenance and SBOM.
- **Published:** `ghcr.io/abucalip/navi-librarian:v0.2.3` and `ghcr.io/abucalip/navi-librarian:sha-7883fe93a0559ca46381e6ef8bd91eaab556ca31`; package version digest `sha256:814f91237de4e969307f6c085513a580d127a61c62b9fb90627988222403e148` (from the GitHub Packages API). `latest` was not moved.
- **Contents:** daily lens lists (Daily picks) on by default (PR #605), plus the Engine 2 Phase 4 and Phase 5 work and the other changes merged since v0.2.2. The v0.2.2 image remains the rollback reference.
- **Not verified:** per-platform manifests were not inspected, the image was not pulled or run, and no GitHub Release was created. Not deployed; no live-runtime verification. Daily picks browser checks (keyboard/focus, Get, Save/dismiss, reduced motion, screen readers) remain deferred by the owner.

## 2026-10-24 — Lens storage test isolation fix (PR #604)

- **Merged:** PR #604, squash commit `102a2d9e842d9887b15c7ce7fe266a63c5c0d056`, from CI-green head `6b0db0b5feabec357dbf864caab632e8173fd90f`.
- **Cause:** the routes test called `POST /api/discovery/all/refresh`, which starts a real lens refresh thread; that thread could still hold the module-level refresh lock when the lens storage tests ran, so they reported `already_running`.
- **Change:** the routes test patches `lens_service.start_refresh` and asserts the call. No production code changed.
- **Verification:** the lock was free before the routes tests and held after them; the lens test modules passed together in three consecutive runs. CI passed on the head: compile, container smoke, full unit suite and image build, validate-container.
- **Not done:** no publication, deployment or runtime verification.

## 2026-10-24 — Engine 2 Phase 5 closed (PRs #600 to #603)

- **Merged:** PR #600 (`bb6cb97`), #601 (`f60268b`), #602 (`46d8cb2`), #603 (`b1454b8`), each squash-merged from a CI-green head.
- **Delivered:** lens-tagged albums and per-lens saves/dismissals; a read-only `GET /api/discovery/lens-feedback`; acquisition request metadata kept on success statuses; per-lens acquisition request and status counts.
- **Closed by owner decision:** play/download attribution dropped; no UI display of the summary. The read API is the only consumer.
- **Limits:** counts are current stored state, not history; pre-#602 jobs are not attributed; no quality claim.
- **Known issue (not fixed here):** `tests/test_discovery_lens_storage.py` fails in some unittest orderings with `already_running` from the refresh lock. CI's full suite passes; the issue predates Phase 5.
- **Not done:** no publication, deployment or runtime verification.

## 2026-10-24 — Engine 2 Phase 5 feedback read API (PR #601)

- **Merged:** PR [#601](https://github.com/abucalip/navi-librarian/pull/601), squash commit `f60268b17d2e28f47e08fbcbc57f3667ec5d6694`, from reviewed head `171efc4a7a074c093ccb6da4cc92964abd4bd44c`.
- **Changes:** Added read-only `GET /api/discovery/lens-feedback` and `lens_service.feedback_summary()`, reusing the Phase 5 summary helper from PR #600. The route is registered before `/api/discovery/{list_name}` so the catch-all cannot shadow it. When `engine2_lens_lists_enabled` is off, the service returns `{"disabled": true, "lenses": {}}` without reading feedback rows; enabled mode reports current per-lens save/dismiss counts and save rate.
- **Review/regressions:** Reviewed all four changed files, route ordering, service setting gate, existing API contracts, and error path. Regression coverage verifies disabled mode performs no feedback read, enabled mode counts correctly, the route resolves rather than hitting the list catch-all, and the route inventory is updated.
- **Verification:** All required CI workflows passed on exact PR head: Python syntax/acquisition-safety (`40122515028`), Docker packaging including the full unit suite and image build (`40122515044`), container runtime smoke (`40122514974`), and non-publishing multi-architecture validation (`40122514971`). Release-workflow validation succeeded (`40122514987`) with publishing skipped. PR author reports 33 focused tests passed; no separate local full-suite run was performed. Backend-only; no browser test required.
- **Limits/status:** Read-only API only; no UI, provider call, publication, deployment, or independent runtime verification. Counts reflect current feedback state rather than historical event totals. No quality claim is made. Next action: determine whether and how to consume the summary in the UI, while keeping any quality evaluation separate from raw counts.

## 2026-10-24 — Engine 2 Phase 5 groundwork (PR #600)

- **Merged:** PR [#600](https://github.com/abucalip/navi-librarian/pull/600), squash commit `bb6cb97062fece9236f964802f9ef705c99809ea`, from reviewed head `2a9b856d0f23b4edbe87fa8a89a088f86cedd22e`.
- **Changes:** `discovery/lens_lists.py` includes each album's lens name; new pure `discovery/lens_feedback.py` counts current album-scope `for_me` saves and `not_for_me` dismissals per known lens and reports a save rate when actions exist. Unknown lens metadata, non-album scopes, and other statuses are ignored.
- **Review and regression coverage:** reviewed all four changed files and existing feedback API/payload contracts. New tests cover per-lens counts/rates, empty lenses, invalid/missing lens metadata, non-album scope, and unsupported statuses; list payload regression verifies the `lens` field.
- **Verification:** GitHub CI on exact PR head passed all four required workflows: Python syntax and acquisition-safety checks (`40121772726`), Docker packaging including the full unit suite and image build (`40121772668`), container runtime smoke (`40121772704`), and non-publishing multi-architecture image validation (`40121772683`). The PR author reports 147 focused tests passed; I did not run a separate local full suite. No browser test was needed for this backend/payload-only change.
- **Limits/status:** the summary helper is intentionally not wired into a route or UI yet; Get/play/download attribution and any quality claim remain out of scope. No publication, deployment, or runtime verification. Next action: implement the read/API integration for the summary with tests, then evaluate what feedback events can be reliably attributed to a lens.

## 2026-10-24 — Phase 4 live run, browser checks, and Last.fm username control

- **Last.fm username control (PR #599, branch `feat/lastfm-username-setting`, head `2fad9b2`):** the Settings Last.fm panel has a username field, saved with the API key; blank clears the stored value so `LASTFM_USERNAME` applies again; invalid usernames are refused before any write. `navidrome_server.py` keeps 2457 lines (adapter signature only). Focused tests: `tests.test_service_settings`, `tests.test_settings_ui_contract`, `tests.test_settings_routes`, `tests.test_discovery_history_fetch`, `tests.test_lens_lists_ui_contract`, `tests.test_discovery_lens_pool_gatherer` (95 tests, pass). CI green on `2fad9b2`: compile `40118706314`, test-and-build `40118706315`, container-smoke `40118706301`, validate-container `40118706294`, validate-release-workflow `40118706303` (publish skipped).
- **Merge not done:** `gh pr merge 599 --squash` was refused by the permission check ("Merge Without Review"). The PR is open and clean; the merge is for the owner or a permitted action.
- **Setting:** `engine2_lens_lists_enabled` is `true` in the owner's `local-test/data` and in the isolated run copy. The code default stays `false`. The setting has no Settings control; it was written to `discovery_settings` directly.
- **Live run (isolated copy, port 8092, scratch data directory, throwaway account, slskd disabled, Navidrome and providers live):** a manual "all" refresh stored Repeated tracks 8, Deep cuts 10, Obsessions 9. A reload kept the Last.fm username.
- **Artwork (`/api/artwork`, 27 albums):** 26 with an image, no provider errors or retry flags. The one miss, "(sic)monic" by "Somnambulist", is a name mismatch: Deezer lists the artist as "Sicmonic", and that query returns the cover. The earlier "empty artwork on every row" note did not reproduce; its cause is unknown.
- **Browser (desktop 1280 px, phone 390 px):** 0 console errors, 0 failed responses, no horizontal overflow. Keyboard: 14 focus stops reached the row actions, each with a visible 2 px outline. Save worked; Not for me removed one album server-side (8 to 7, `dismissed: 1`). Not run: Get (it starts an acquisition request), screen-reader output, and a reduced-motion check beyond loading the page.
- **Note:** the browser run used Chrome through Playwright from a scratch virtualenv outside the repository. Port 8091 was already held by another uvicorn process (started 2026-10-22); it was not touched.
- No publication or deployment.

## 2026-10-24 — Lens artwork investigation (Phase 4 item 3): no code defect found

- Path traced: lens rows call `buildRecommendationRow` → `attachArtwork` with the stored `artist` and `album` (`static/app.js`), then `/api/artwork` (`app/api/metadata.py`), which runs a Deezer album search with an artist-photo fallback. Lens rows use the same loader as the other rows; no lens-specific skip was found.
- Handler check (local, no list data): `album_artwork(artist='Miles Davis', album='Kind of Blue')` returns a Deezer cover; a nonsense name returns `artwork_url: None` with no `retryable` flag. Deezer's album search answered from this environment.
- Failure handling: a provider exception sets `retryable` and is not cached, so an outage cannot leave a row blank for five minutes.
- Conclusion: the empty rows are most likely "no Deezer match with score 9 or more, and no exact artist photo" for these albums. This is not confirmed: the local database has no lens rows (the live run used an isolated copy), and no lens album names were available to query. Confirming needs the artist and album pairs from one stored lens list, run through the handler.
- No code or test change. Nothing published or deployed.

## 2026-10-24 — Phase 4 closeout: what is left

- Built and merged: Phase 4 slices 1 to 4 (PRs #590 to #595), the dismissal read filter and Daily picks rename (#596), the dynamic history walk with its Last.fm error fix (#597), and the ListenBrainz recent-listens paging fix (#598).
- Left: the owner's decision on `engine2_lens_lists_enabled`; the Last.fm account Settings control (parked); browser checks for keyboard, focus, actions, reduced motion and screen readers; empty artwork on lens rows; a quality measurement of the lists; Phase 5. No publication or deployment in this entry.

## 2026-10-24 — Deeper lens history (PR #597); correction to the live-run entry; PR #596 review fixes

- Correction: the live-run entry below says the history was capped at 100 listens by the ListenBrainz page limit. That was wrong. A `min_ts` query returns the oldest page after the bound in ascending order, and the client paged backwards from there and stopped, so the one-year read kept only the oldest two days of the year. `recent_listens` (Discover, `days=30`) has the same behaviour and is not changed; it needs an owner decision.
- PR #597 (`feat/engine2-dynamic-history`): dynamic 365-day walk back from now, to a 13-year floor, until 2000 usable listens (starting value). Windows alternate between ListenBrainz and Last.fm, a failing source is answered by the other, duplicates counted once, windows at the 5,000-listen page cap flagged. Tests: `tests/test_discovery_history_fetch.py` (14). Live: 6,866 listens over 13 windows; all three lenses built; the 2014 window reached.
- PR #596 review (`d6261439`): malformed cache entries no longer make an unchecked read fail; two regression tests. Browser check on that head: pass at 1280 and 390 px.
- Not merged, both PRs open. No publication or deployment.

## 2026-10-24 — Daily picks dismissal filtering (PR #596)

- Re-reviewed PR [#596](https://github.com/abucalip/navi-librarian/pull/596) after the robustness fix. The unchecked-cache response now drops malformed non-mapping entries safely and handles a non-list `albums` field; regression tests cover both-checks-unavailable and malformed-cache cases.
- Final PR head: `d62614393244c4ee33726d9401704c339edd5440`. Required workflows passed on that exact head: Python syntax (`40111186933`), Docker packaging/full unit suite/image build (`40111186947`), container runtime smoke (`40111186946`), and validation-only multi-architecture image validation (`40111186939`). Release workflow run `40111186943` reported success; publication/deployment status is not inferred from this.
- Manual UI/browser testing was explicitly waived by the owner and was not performed. Squash-merged as `3e2e8bc2c3e3882596fc1a398706e1b9f3f72f5e`. No deployment or runtime verification claimed.

---

## 2026-10-24 — Daily picks: live run, browser check, dismissals (PR #596)

- Opened PR #596 (`feat/daily-picks-dismissals`): lens lists drop "Not for me" albums and artists at read time (`discovery/list_payload.py` `dismissed_predicate`, `discovery/lens_storage.py` `serve_lens_list`), and the read filter counts them as `dismissed`. Ranks restart at 01 after a removal (follow-up commit `f3f88bdb`). The page and copy are renamed "Daily picks". Focused tests: the lens storage tests (33), list payload, lens list, pool, lens, and metric tests, and all UI contract tests; full suite left to CI. Open; not merged.
- Live run on an isolated copy of the local data directory, port 8192, with live providers. The owner's running instances (other ports) were not used or changed. One lens build selected 10 Deep cuts albums from a pool of 60. Repeated tracks and Obsessions stored nothing: the ListenBrainz history fetch returned 100 listens for the 365-day window, too few to produce seeds. Details and aggregates in `docs/engine2.md`, Phase 4.
- Browser check (Chrome via Playwright, scratch virtualenv, not in the repository) at 1280 px and 390 px: navigation, the Daily picks page, toggle state, list semantics, and rows rendered; no console or page errors, no failed responses, no horizontal overflow. Not covered: keyboard and focus, the action controls in the browser, reduced motion, screen readers. Lens artwork was empty and was not investigated.
- Owner decisions recorded: 10-minute library cache stays; no daily acquisition cap; the name Daily picks.
- No publication, deployment, or merge of PR #596 in this entry.

## 2026-10-24 — PR #595 merged; Engine 2 Phase 4 Daily lists UI

- Re-reviewed exact PR head `01ca4428c7c07dda111086ea4942124f2ef24172`. The SVG sprite now has valid attribute spacing, and `tests/test_lens_lists_ui_contract.py` parses the sprite as XML. The Daily lists UI uses the shared recommendation row, ignores stale lens responses, reports disabled/empty states as status text, and routes dismiss feedback back to the active lens.
- The diff also removes the ranked-row hover stripe and creates the album artwork image in JavaScript rather than shipping an `<img>` without a source; contract tests explicitly cover these choices.
- All required workflows passed on the exact head: Python syntax (`40108409642`), Docker packaging/full unit suite/image build (`40108409602`, including `Run unit tests`), container runtime smoke (`40108409585`), and validation-only multi-architecture image validation (`40108409651`, publishing paused). Release workflow validation (`40108409597`) passed with the `publish-release` job skipped.
- Squash-merged PR #595 as `9ac74da768e93b592ac070814b69a6a7ffa4f964`. The owner waived manual browser testing; no browser check was performed. No live provider run, publication, deployment, or runtime verification. `engine2_lens_lists_enabled` remains off by default.
- Next: perform the waived browser checks against a pinned deployed/test environment when appropriate; otherwise continue the planned Engine 2 Phase 4 follow-up.

## 2026-10-24 — Re-review, full CI suite, and merge PR #594

- Reviewed exact PR head `b79ff64cf65e51bfa38e8203b722961ff0be077c`. The manual `all` discovery refresh now starts a lens-list build through `discovery/lens_service.py:start_refresh` in a daemon thread; other list refreshes do not trigger it. The refresh shares the daily loop's lock, and the existing setting gate means the feature remains inert while `engine2_lens_lists_enabled` is off. Regression tests cover the `all` trigger, non-`all` behavior, and execution on a separate thread. No blocker found in the changed code.
- All required workflows passed on the exact PR head: Python syntax/acquisition safety (`40106635627`), Docker packaging/full unit suite/image build (`40106635948`, including successful `Run unit tests` and `Build Docker image` steps), container runtime smoke (`40106635598`), and validation-only multi-architecture image validation (`40106635703`, non-publishing). Release workflow validation (`40106635611`) succeeded; its `publish-release` job was skipped. Per repository workflow policy, the full unit suite ran in CI, not manually.
- Squash-merged PR #594 as `5299ac03f04c8718a64adc1c557c09b367f7d266`; GitHub confirms the PR is closed and merged. Updated `docs/PROJECT_STATUS.md` to record the merge and set the next action to define the bounded Phase 4 slice 4 (UI) scope.
- Lens lists remain behind the default-off setting. No live provider run, publication, deployment, browser check, or runtime verification was performed.

## 2026-10-24 — PR #593 merged; manual lens trigger in the app layer

- PR #593 (move the lens adapters out of `navidrome_server.py`) squash-merged as `8ef9eb6e1f6e7099ae0369f0bd2471872fab816b`. Its review fixes: the read path checks `engine2_lens_lists_enabled` before any store or library access, with regression tests for the disabled path (service and route) and the enabled path.
- Owner decisions: the daily loop's hourly retries while a lens list is missing or not from today are acceptable; the manual trigger goes in the app layer.
- Manual trigger: `POST /api/discovery/all/refresh` also starts a background lens build (`discovery/lens_service.py:start_refresh`), which returns at once and shares the daily loop's lock. Other list refreshes do not start it. Tests cover the trigger, the other refreshes, and background execution.
- `navidrome_server.py` is unchanged by this work (zero diff against its pre-PR-592 content, D-016).
- Next: define the bounded slice 4 (UI) scope before implementation.

## 2026-10-24 — Engine 2 Phase 4 slice 3 merged; server module rule

- PR #592 (storage and serving for the daily lens lists) squash-merged as `0a8f9090fbb218f6508b33d9e72ebedbcdc64fd1` from exact head `09fb6e8d907d49fdefad4925a6b91c2e394abe5d`. All four required workflows passed on that head. Feature stays off by default (`engine2_lens_lists_enabled`); no live provider run, publication or deployment.
- Owner rule recorded as D-016 (`docs/DECISIONS.md`) and in `docs/DEVELOPMENT_WORKFLOW.md`: `navidrome_server.py` takes no additions; new code goes in new modules.
- Debt: PR #592 added the lens build and read adapters to `navidrome_server.py` before the rule existed. They must move to a new module before slice 4. The size guard does not enforce the rule yet.
- Docs updated: `docs/engine2.md` (slice 3 status and debt), `docs/ACTIVE_WORK.md`, `docs/PROJECT_STATUS.md`.
- Next: move the adapters out of `navidrome_server.py`, then slice 4 (UI).

## 2026-10-24 — Engine 2 Phase 4: owner decisions on the slice 2 review

- The owner approved: the setting name `engine2_lens_lists_enabled`; about three MusicBrainz release searches per lens (25 release groups per query) in place of the planned one; the per-run history-artist genre prefetch (cached 90 days) and the one-time MusicBrainz genre vocabulary load (about 25 requests when its cache is empty); the missing attribution trailers on the PR #591 feature-branch commit (the squash-merge body carries them).
- Day boundary decided: the day rolls over at 4am local time. Slice 3 must derive the lens-list `day` (and the radio scope) from the local time minus four hours; slice 2 currently takes `day` from the caller.
- Still open: how often the Navidrome library artists are refreshed for the known-artist check (the 10-minute snapshot cache stays for now).
- Documentation only; no code, tests, provider calls, publication or deployment.
- Next: slice 3, storage and serving, in a new session.

## 2026-10-24 — PR #591: Engine 2 Phase 4 slice 2, the pool gatherer

- PR #591 squash-merged as `cca42e3cfde534571d319206eff8ab4fa0c461ff` from exact head `3a7ab611c5cdca432a4ebf3769f1e756de719cb5`. All four required workflows succeeded on that head: Python syntax check (`40104361233`), Docker packaging (`40104361217`; `test-and-build`, including `Run unit tests` and `Build Docker image`, passed in CI), container runtime smoke (`40104361193`), and validation-only image validation (`40104361177`, publishing paused). Unwired; no publication or deployment.
- Added `discovery/lens_pool_gatherer.py`: `gather_lens_pools(listens, *, day, providers, headers, lastfm_api_key, settings_read)`. For each lens in `LENS_LIST_ORDER` it runs `run_deep_cuts_tag_supply` with the lens name and the ISO day as the radio scope, then gathers album listeners (MusicBrainz release search and Last.fm `album.getInfo`, capped at 60 Last.fm lookups per lens, artist lookups skipped), artist genres (one ListenBrainz artist batch per lens, cached), and fallback tags for pool artists with fewer than two genre tags. The output keys match the inputs of `build_lens_lists`.
- Setting `engine2_lens_lists_enabled` (`settings/service.py`, `engine2_lens_lists_enabled_value`), default off, boolean only. When off the gatherer returns `{"status": "disabled"}` before any provider call. No route, recommendation path, personal list, or history/cooldown reads or writes it.
- Starting-note fixes: `fetch_release_mbids` retries a release-search page that is rate-limited (429), 5xx, or dropped, after an 8 s pause, up to three tries (`RELEASE_SEARCH_ATTEMPTS`); other client errors are not retried, and successful pages make the same calls as before. `usable_listens` (`discovery/lens_lists.py`) drops listens stamped before 1971, and the gatherer applies it before building any profile or history-artist set. `resolve_popularity` gains `with_artist_listeners` (default `True`, unchanged).
- Tests (stubbed providers, placeholder data, no network): focused runs only, all passing locally: `test_discovery_lens_pool_gatherer` (10 new), `test_discovery_mbid_popularity` (25, including 5 new retry and album-only tests), `test_discovery_lens_lists` (29), `test_service_settings` (20, including the new setting test), `test_discovery_deep_cuts_supply` (11), `test_discovery_lenses` (27). `scripts/check_server_size.py` and `scripts/check_app_legacy_imports.py` passed. The full unit suite was not run locally; CI ran it on the exact head. No live provider calls.
- Budget notes, to confirm with the owner: `fetch_release_mbids` batches 25 release groups per query, so a 60-album pool costs about three release searches per lens, not the one in the approved plan. History artists are prefetched for genres on each run (cached 90 days, so this costs calls on first run or after expiry). The fallback vocabulary (MusicBrainz genre list, about 25 requests) loads once per run when its 90-day cache is empty.
- Open: the setting name is a draft choice for the owner to confirm; the day boundary (local or UTC) and the library-refresh rate are still open; slices 3 (storage and serving) and 4 (UI) are not started.
- Next: slice 3, storage and serving, in a new session.

## 2026-10-24 — PR #590: Engine 2 Phase 4 slice 1, the pure lens-list builder

- PR #590 squash-merged as `eadbd8a1f7b3515ffbed6ec65d4b34e95adaedf2` from exact final head `29659aea4c6b0a159db72a6b546a8b428e4746d0`. The builder was written by a delegated agent from the approved plan; the owner's follow-up decision (below) was added as a second commit on the same branch. All four required workflows succeeded on the final head: compile (`120898813524`), test-and-build (`120898813251`), container-smoke (`120898813582`), validate-container (`120898813244`). Local checks were focused tests only: the agent ran 151 lens-related tests and a 609-test keyword-filtered subset on the first head; the follow-up ran 84 and a 612-test subset. The full suite ran in CI. Unwired; no publication or deployment.
- Added `discovery/lens_lists.py`: `build_lens_lists(pools, *, day, popularity, artist_tags, library_by_title, fallback_tags, known_artist_mbids, library_artist_mbids, seeds, lenses, count)` takes precomputed pools per lens, merges the fallback tags after the genre tags, builds candidates with `build_allocation_inputs`, runs each lens's own gates through `run_lens`, and returns one JSON-serialisable payload per lens (lens, label, day, requested, albums, seed tags, pool size, skipped entries, checked count, decisions by status). It reads no clock and makes no provider calls; an entry without an album title or primary artist is skipped and counted. Helpers: `lens_seed_queries` (seeds for all three lenses; Deep cuts from the densest 30-day window with flat weights, or all recent activity when the history is shorter, after dropping listens stamped before 1971), `history_artist_mbids`, `merge_artist_tags`.
- `discovery/lenses.py`: `partition_lens_pools` partitions separately gathered pools so one lens cannot pick from another lens's supply; `partition_lenses` delegates to it with unchanged behaviour. Owner decisions on review: lens order Repeated tracks, Deep cuts, Obsessions; the Deep cuts seed window above; known artists do not count against the 60-candidate check limit. The selection now rejects an unowned album by a known artist as `artist_already_known` without using a check (owned albums still count), so `checked_count` is lower than before for pools with known artists.
- Tests: new `tests/test_discovery_lens_lists.py` (29 tests, placeholder data only: partitioning across lenses, known-artist exclusion by library name, library artist MBID and history MBID including a same-name-different-MBID case, fallback tags rescuing a candidate, empty pools, determinism, serialisability, bad input) and additions to `tests/test_discovery_lenses.py`.
- Limits: a local run of the builder on saved real-history pools (aggregates only) produced 6 seeds per lens and about 16 to 17 known artists excluded per lens but no finished list, because those saved files carry no album listeners or genre tags; end-to-end behaviour on real data is unchecked until slice 2 gathers full pools. Where the history is read from at runtime, the day boundary, the setting name, the library refresh rate and the UI wording remain open.
- Next: slice 2, the pool gatherer, with the MusicBrainz release-search retry and the 1970-timestamp fix noted in `docs/engine2.md`.

## 2026-10-24 — Engine 2 Phase 4 plan approved

- The owner approved the Phase 4 plan (precompute and serve the lens lists) with these decisions: the first lenses are Deep cuts, Repeated tracks and Obsessions; the daily provider budget is approved (about 25 s and roughly 6 radio calls, 1 batch POST, 1 release search and 40 to 60 Last.fm lookups per lens); one list of 10 per lens per day, no "next list"; lens lists keep their cooldown apart from the existing recommendation history and cooldown; everything sits behind a setting that defaults to off.
- The plan, its four slices (pure list builder, pool gatherer, storage and serving, UI), the open questions and the starting notes for the next session are in `docs/engine2.md`, Phase 4. No code was written; nothing is wired into runtime; no publication or deployment.
- Next: slice 1, the pure list builder, in a new session.

## 2026-10-24 — Engine 2 Phase 3 closeout: tier fall-through, albums per seed, merges

- Merges: PR #588 (Last.fm fallback genre tags, `discovery/artist_tag_fallback.py`) merged as `c2c346da406df79803405824929b99cf55bff332` from head `d0778412367e21a4652425c2c9bf74ce601c2966`, on which all four required workflows (compile, test-and-build, container-smoke, validate-container) were successful before the merge; PR #589 (10 albums per seed in the Deep cuts radio tiers) merged as `972912f`. This corrects the entry above, which was written before the #588 merge and says it was unmerged and that the merge was blocked. Both are unwired; no publication or deployment.
- Tier fall-through, measured (owner-approved live runs, one listener, aggregates only): fetching the 75 to 100% band for every seed in addition to the 50 to 75% band doubled the pool (30 to 59 albums for Repeated tracks, 30 to 55 for Obsessions) but added only one selected album per lens (7 to 8 and 4 to 5), because the deeper band mostly returned known artists and albums outside 300 to 50,000 listeners. Fall-through is unchanged: the second band is tried only when the first returns no album for a seed.
- Albums kept per seed, one radio draw each (the radio is redrawn per run, so about 2 of noise): 5 gave 7 (Repeated tracks) and 8 (Obsessions) selected of 10; 10 gave 9 and 9; 15 gave 5 and 7, because a pool over 60 exceeds the selection's limit of 60 checked candidates (29 candidates not considered in one run). The radio returns 20 recordings per call, so keeping more costs no extra radio or batch calls. After #589 (unpatched supply, 60 albums per lens, none from the tail): Repeated tracks selected 8 of 10 without the fallback tags and 10 with them; Obsessions selected 10 of 10 either way.
- Fallback tags: the Last.fm tags restricted to MusicBrainz genre names brought 41 of 95 untagged history artists to two or more tags (raw Last.fm tags reach 71 but include non-genres); in the lens runs the fallback extended 3 to 5 artists per lens. Tag quality for ranking and list quality were not judged.
- Limits: one listener; single radio draws; fallback tags merged by the harness, not by pipeline code; the radio band that supplied each album is not recorded per candidate (not needed while the radio supplies everything); all of it is unwired.
- Phase 3 is complete. Not Phase 3: wiring the lenses, the known-artist inputs and the fallback tags into a precomputed, daily-served pipeline is Phase 4. Next: a Phase 4 plan for the owner's approval.

## 2026-10-24 — Engine 2 Phase 3: live runs of Repeated tracks and Obsessions with the radio working and the tag fallback

- Owner-approved, read-only live runs on one listener's history, from the branch of PR #588 (the fallback was not yet merged; the owner's merge instruction could not be carried out by the agent because the merge command was blocked). Throwaway harness and data outside the repository; aggregates only. Each lens: seeds, `run_deep_cuts_tag_supply` (lens name and day as the radio scope), album listeners by one MusicBrainz release search plus Last.fm lookups, genres by one ListenBrainz artist batch, the Last.fm fallback tags (vocabulary: the MusicBrainz genre list, count 10 or more), the Navidrome library (1,739 albums) and the listening-history artists as known artists, then the lens selection for a list of 10.
- First run in this series where the radio worked: every seed returned 5 albums from the 50 to 75% band, 30 albums per lens, none from the tail, no failures. The whole run took 22 s (Repeated tracks) and 21 s (Obsessions), against 100 s or more in the earlier runs that fell back to the tail.
- Repeated tracks: without the fallback tags 4 were selected; with them 6 (8 artists had fewer than 2 genre tags, the fallback extended 3, leaving 5; candidates rejected for too few tags fell from 5 to 3). Of the 30 albums: 9 by known artists, 4 already owned, 7 outside 300 to 50,000 listeners, 1 per-seed cap, 3 too few tags. The raï and desert blues seeds produced no selection: their radio candidates were all artists already in the library or the history, or had too few tags.
- Obsessions: 5 selected without the fallback and 6 with it (5 artists extended, artists with fewer than 2 tags 5 to 1). Of the 30 albums: 13 by known artists, 10 outside 300 to 50,000 listeners (broad tags return well-known albums), 1 with unknown listeners.
- Reading: with a working radio both lenses fill 6 of 10, not 10. The limits are the known-artist exclusion (a third to a half of the radio's candidates are artists the listener already has), the audience ceiling for broad tags, and a pool of only 30 albums. Tier fall-through to the 75 to 100% band happens only when the 50 to 75% band returns no album for a seed, not when every returned album is rejected downstream, so a seed whose candidates are all known artists never reaches the less popular band.
- Limits: one listener and one day's radio draw (answers are fixed per lens and day); the fallback tags were merged by the harness, not by pipeline code; tag quality and list quality were not judged.
- Next: the owner merges PR #588; decide whether tier fall-through should consider downstream rejections or whether the pool needs more albums per seed; wiring is Phase 4.

## 2026-10-24 — Engine 2 Phase 3: Obsessions definition approved

- The owner approved the Obsessions lens definition after PR #587 merged: seeds from artists with at least 20 listens, 70% or more of them inside one 30-day span; the broad seed tags are kept as they come (no dominant-tag or generic-tag filter); the Deep cuts gates apply (album listeners 300 to 50,000, at least 2 artist tags, one album per artist, at most 2 per seed, owned albums and known artists excluded). The approval reached `main` as a separate docs commit because it was made after the PR's squash merge; the draft wording in `docs/engine2.md`, `ACTIVE_WORK.md` and `PROJECT_STATUS.md` is replaced.
- The lens remains unwired and outside the default lens order. No code, provider calls, publication or deployment.
- Open: a tag source or an exception for artists with no genre tags; a live run of Repeated tracks and Obsessions with the radio path working (needs owner approval).

## 2026-10-24 — Engine 2 Phase 3: Repeated tracks lens, live runs and owner decisions

- Owner-approved, read-only live runs of the Repeated tracks lens on one listener's history, with throwaway harnesses and data outside the repository; aggregates only. Seeds: the six tags in the lens catalog. Supply: `run_deep_cuts_tag_supply` with lens `repeated_tracks`; album listeners by one MusicBrainz release search plus four parallel Last.fm lookups; genres by one ListenBrainz artist batch.
- Run 1 (before PR #585): the lens returned 23 albums in 96 s, all from the MusicBrainz tail: five radio calls were dropped as stragglers or failed on the connection, so the radio tiers added nothing, and the most distinctive seed tag returned nothing after a connection error. Album listeners were found for 21 of 22. Selection reached 5 of 10: 8 rejected for fewer than 2 artist tags, 7 for album listeners outside 300 to 50,000, 2 for unknown listeners, 1 for the per-seed cap. One selected album was by an artist in the listening history, which showed that the Deep cuts selection checked album ownership only and did not exclude known artists.
- Navidrome check (PR #585): the library has 1,739 albums by 694 artists, fetched in 0.4 s. `getArtists` returns a MusicBrainz ID for 311 of 730 artists; albums carry `artistId`. With the known-artist exclusion and a tag minimum of 1, the same pool reached 5 of 10 again: 2 candidates rejected as known artists, 2 as already owned, 1 held for ownership review. Five candidates had no genre tags at all, so lowering the minimum to 1 rescued only 2 of the 8 that the minimum of 2 had rejected. After the MBID-aware match (same name with different artist MBIDs is not the same artist) the exclusion decisions were unchanged; the Last.fm lookups failed on every attempt in that last rerun, so its final list was not compared.
- Limits: one listener; two runs on one pool (the radio path was never exercised for this lens); no library ownership check in run 1; the 5 selected albums were not judged for quality and one title looked like possible junk the gates cannot catch.
- Owner decisions (2026-10-24): the Repeated tracks gates are approved (album listeners 300 to 50,000, one album per artist, at most 2 per seed, known artists excluded); the tag minimum of 1 is dropped, so the lens returns to the Deep cuts minimum of 2 (code revert to follow); Obsessions becomes a lens, definition to be written; the radio-path secondary-type fix is skipped; another tag source or an exception for artists with no genre tags is to be explored.
- Tail follow-up: the owner confirmed on 2026-10-24 that the MusicBrainz tail runs daily, so no separate repeat-run test of the tail is planned. The code revert of the tag minimum is PR #586.
- Next: revert the tag minimum for Repeated tracks, write the Obsessions definition, explore the no-tag candidates, and rerun the lens live with the radio path working (needs owner approval).

## 2026-10-24 — PR #587: Obsessions lens and seed builder

- Reviewed the complete five-file diff at `fedd943ee214354ab75b6e880bdde1851860113e`; no blocking correctness or compatibility issues found. `obsession_seed_queries` reuses `burst_artist_weights` and the established supplementary-tag query shape. Tests cover burst qualification, thresholds/limit, empty and untagged inputs, and invalid arguments. `OBSESSIONS` reuses the Deep cuts selection gates, including known-artist exclusion, is registered under its own name, and remains outside `DEFAULT_LENS_ORDER` so default partitions/runtime behavior are unchanged.
- All four required CI workflows passed on the exact PR head: syntax (`40094978423`), Docker packaging/full unit suite/image build (`40094978481`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40094978473`), and validation-only multi-architecture image validation (`40094978442`, publishing paused). No separate agent-run full suite per workflow policy.
- Squash-merged PR #587 as `a97cdc0363cb324f9005aa21fa3c691843eadf17`. The Obsessions definition is still a draft pending owner approval; the lens is not in the default order and is not wired into runtime. No publication, deployment, or runtime verification.

## 2026-10-24 — Engine 2 Phase 3: history profiles through the real seed selection

- Offline check, no provider calls: the merged-branch profile helpers (PR #583) and the existing `select_supplementary_tag_queries` over one listener's full ListenBrainz history (40,798 listens, 36,231 with an artist MBID through the `mbid_mapping` fallback) and cached genre tags for 504 of 599 artists. Aggregates only; the data and harness stay outside the repository.
- Profiles and the six seed tags each produced: Now (30 days): jazz, pop, rock, alternative rock, hip hop, indie rock. Long-term: progressive rock, metal, progressive metal, rock, art rock, acoustic rock. Rediscovery (dormant 365 days): metal, progressive metal, progressive rock, acoustic rock, death metal, rock. Repeated tracks outside the dominant tags (54 artists): raï, folk, traditional pop, desert blues, jazz fusion, folk rock. Obsessions (67 artists): rock, rock and roll, blues rock, progressive rock, blues, alternative rock. New since 2018 (88 artists): jazz, hip hop, pop, raï, rock, r&b.
- Shared seed tags (of 6): Long-term and Rediscovery 5; Now and New since 2018 4; Obsessions 2 with each of Now, Long-term and Rediscovery; Repeated tracks 0 with Now, Long-term, Rediscovery and Obsessions, and 1 with New since 2018.
- Reading: the repeated-track profile is the only clearly separate one; New since 2018 is largely redundant with Now; Long-term and Rediscovery are near-duplicates; Obsessions gives broad, popular tags, so obscurity would rest on the Deep cuts gates. As earlier, a profile changes the seed tags, not which albums a tag returns.
- Limits: one listener; 95 of 599 artists have no genre tags and add nothing to the seeds; thresholds (5 plays, 20 listens, 70% in 30 days) are untuned; seed tags only, no albums were fetched; no quality judgment. Nothing is wired into runtime.
- Next: the owner decides which profiles become lenses and their gates.

## 2026-10-24 — Engine 2 Phase 3: title-marker check, size of the known radio-path gap

- The title-marker check itself was done and logged on 2026-10-23: the radio path applies `batch_title_marker_rejection`, the MusicBrainz path uses release-group secondary types, and an unmarked live or compilation album still passes the radio path. The Christmas album noted in the first 2026-10-24 live-run entry is not a filter failure, since "Christmas" was never a marker. This entry measures how often the known gap lets an excluded type through.
- Owner-approved, read-only, throwaway harness outside the repository, aggregates only. A radio-led Deep cuts pool from the same five seed tags (krautrock returned nothing after a connection error) gave 20 albums. One MusicBrainz release-group search per 25 groups, unauthenticated with the app `User-Agent` (two connection retries), returned secondary types for all 20.
- Result: 18 of 20 had no secondary type; 1 was a Soundtrack and 1 a Compilation (a discography), 2 of 20 (10%). Neither title carried a batch marker, so both passed the radio-path title filter and would have been excluded on the MusicBrainz path.
- Limits: one run, one listener, five hand-picked tags, a small pool; the 10% is an observation, not an estimate. The radio band that supplied each album was not recorded.
- Possible fix, not started and needing an owner decision: a bounded secondary-type check on radio candidates before the Deep cuts gates, about one MusicBrainz call per 25 albums, applying the existing excluded secondary types. Nothing is wired into runtime; no publication or deployment.

## 2026-10-24 — Engine 2 Phase 3: MusicBrainz tail of the Deep cuts supply, measured alone

- The tail was added in PR #581 and is covered by unit tests (including radio unavailable and no `http_post`). This entry adds a live measurement of the tail on its own: owner-approved, read-only, throwaway harness outside the repository, aggregates only. Same five seed tags as the entry above, `run_deep_cuts_tag_supply` with `http_post` unset so the radio tiers are skipped and the MusicBrainz tag search serves every query, then the fast album-listener path (one MusicBrainz release search, Last.fm album lookups on four threads).
- Supply: 20 albums in 26 s (post-rock lost to a `No route to host` error; the other four tags returned 5 each), against 74 s for the radio tiers in the previous entry. Album listeners were found for 20 of 20 in 3.4 s (median 1,360): 13 inside the 300 to 50,000 gate, 5 under 300 (as low as 19), 2 over 50,000. The radio-led run had median 810 and 14 of 25 in the gate.
- Overlap: 12 of the 20 tail albums also appeared in the earlier radio-led run's 25. The harness recorded neither the radio band nor whether the tail served each album there, so the cause is unknown. A possible explanation, not tested, is that the MusicBrainz tag search returns the same top results each time, while radio answers are redrawn daily (PR #582); the tail would then give a nearly fixed list.
- Limits: one listener, five hand-picked tags, one run each, a flaky network (one tag lost), album-listener gates only, no quality judgment. Nothing is wired into runtime; no publication or deployment.
- Next (not started): repeat the tail on two days or two runs to test whether it is stable; record the radio band per candidate.

## 2026-10-24 — Engine 2 Phase 3: live run of the Deep cuts tiered supply, with batch lookups

- Owner-approved live run of `run_deep_cuts_tag_supply` (radio 50–75%, then 75–100%, then the MusicBrainz tail) with real providers, five seed tags (post-rock, shoegaze, doom metal, jazz fusion, krautrock), lens `deep_cuts`, today's scope. ListenBrainz calls carried the configured token and `User-Agent`; Last.fm used the configured key; MusicBrainz was unauthenticated. Read-only; throwaway harness outside the repository; aggregates only.
- The first two attempts lost tags to connection errors (`No route to host`, `ConnectError`); a connectivity check passed in between, so the drops looked transient. Later runs completed: every tag returned 5 albums (25 total), all with release-group and artist MBIDs.
- Album listeners (Last.fm, by release MBID): 21 of 25 found with the existing `resolve_popularity` (median 810); 25 of 25 with the faster path below (median 810; 14 in the 300–50,000 gate, 8 under 300, 3 over 50,000). One album with a "Christmas" title passed the batch title-marker filter, which is a concrete case for the deferred title-marker check.
- Speed: 129 s end to end with `resolve_popularity` (supply 78 s, popularity 52 s). With album-only lookups, one MusicBrainz release search for all 25 groups, and four parallel Last.fm threads, popularity took about 4 s (0.4 s plus 3.8 s) and the run 78 s. Pre-gating (title marker, one album per artist) removed nothing here.
- The remaining time is ListenBrainz latency: 10 radio GETs summed to 282 s (slowest 40 s) and 2 recording-batch POSTs to 60 s (one at its 30 s timeout). A tag that misses the 4 s straggler window in the 50–75 band falls to the 75–100 band and waits again. Recording batches already carry 100 recordings per call (larger sizes are unverified). The release-group endpoint fails above 80 IDs and was not needed. A batch endpoint for the tag radio is not known; passing several tags in one call would lose per-seed attribution and was not tested.
- Limits: one listener, five hand-picked tags (not derived from a window), one day's radio samples, a flaky network, album-listener gates only; the lists were not judged for quality. The tier that supplied each album was not recorded. A same-day repeat run, which should hit the radio and batch caches, was not measured. Nothing is wired into runtime; no publication or deployment.

## 2026-10-24 — Engine 2 Phase 3 gate: repeated tag-radio samples, replayed through the production lane

- Owner-approved live run, cheaper design than the previous repeat: 8 unique seed tags across five windows (four dense 30-day windows and all time), 6 independent tag-radio samples per tag (50–75 band, 20 recordings each), one batch resolution of 943 recordings (780 usable), then the production `run_lb_tag_queries` replayed offline for each window and repetition. 48 radio calls, no failures; no MusicBrainz tail (radio tier only).
- The first attempt failed at batch resolution (no route to host) after its radio samples had been lost; the rerun checkpointed samples to disk and reused them. Raw output is outside the repository.
- Every pool has 30 albums (6 seeds × the 5-per-query cap).
- Same window, different repetitions: 1.1 shared albums on average (of 30); top-10 overlap 0.3. Radio samples are redrawn on each call.
- Different windows, same repetition: 25 shared albums on average. This is explained by shared seed tags, not by the window: each shared tag contributes exactly 5 albums at that repetition (for example, 5 shared tags gave 25 shared albums, 6 gave 30, 4 gave 20).
- Conclusion: a window changes the pool only through its seed set (which tags are queried). The albums contributed by a given tag are a fresh random sample each time, so run-to-run variation of a list is larger than the window-to-window difference in seed sets. The Phase 3 gate ("a window changes the candidate pool, not only ranks") is met only at the seed level; the album-level effect is dominated by radio sampling noise. A stable window list would need a fixed sample per tag (or a deterministic candidate source), which is a design decision for the owner.
- No change to code, defaults, or runtime. No publication or deployment.

## 2026-10-24 — Re-review, CI verification, and merge PR #582

- Re-reviewed exact PR head `48532b774af01e895de1a7ef41c823b07b94edd1`. Daily cache scope is passed through the radio lane and included in cache keys; the original unscoped 0–100 key and existing band-specific key remain unchanged. New tests cover same-day reuse, next-day refresh, separate lens samples, and invalid lens/day input. The feature remains unwired into runtime.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety (`40041573624`), Docker packaging/full unit suite/image build (`40041573588`), container runtime smoke (`40041573555`), and validation-only multi-architecture image validation (`40041573534`; publishing paused). Full unit suite ran in CI; it was not run manually, consistent with the repository workflow.
- Squash-merged PR #582 as `5018446c45c000fefcde6a4955a6bcb6e1943f77`. No live provider calls, publication, deployment, or runtime verification.

## 2026-10-24 — Daily radio scope for Deep cuts (unwired)

- Radio answers can now be keyed by a scope (`lens:date`). `run_deep_cuts_tag_supply` requires `lens` and an ISO `day`, so each tag gives one fixed sample per lens per day, a fresh draw the next day, and a separate draw for each lens that shares the tag. The default key (no scope, default band) is unchanged, so existing cache entries stay valid.
- Old daily entries are not deleted; they expire with the existing 30-day TTL.
- The MusicBrainz tail is deterministic per query and is not scoped.
- Focused tests: 123 passed (new `tests/test_discovery_daily_radio_scope.py`, plus updated Deep cuts, tag-lane, gathering, lens and size-guard tests). The full suite is left to CI.
- Not wired into runtime; no live calls in this change; defaults unchanged.
## 2026-10-23 — Engine 2 Phase 3 gate: repeat live run of the Deep cuts tiered supply (gate not met)

- Owner-approved live run: `run_deep_cuts_tag_supply` (radio 50–75, radio 75–100, MusicBrainz tail) over five history windows (four dense 30-day windows and all time), twice. Each run started from a fresh copy of the metadata cache, so tag radio and MusicBrainz calls were live. Raw output stays outside the repository.
- Within a run, the windows' album pools overlap heavily: 20–25 shared of 30–40 (run 1) and 10–30 shared of 30–45 (run 2). These overlaps are inflated by the run's shared cache: all windows reuse the same tags (4–6 of 6 seeds are shared), and a repeated tag returns its cached answer. The same-window timings in run 2 (0.0–4.3 s after the first windows) are cache hits, not provider latency.
- Across runs, the same window shares almost nothing: 0–2 of about 30 albums, and 0–2 of the top 10. The seeds were identical, so the tag radio answers differed between runs. A single-tag repeat to isolate sampling from drift was attempted but the network dropped (no route to host) before it could run.
- Consequence: the 2026-10-23 entry above that says a window "changes the candidate pool in most pairs" is not supported once run-to-run variation is counted. Lists built from one window's radio sample do not differ from another window's by more than the sample noise can explain. The Phase 3 gate (a window changes the candidate pool, not only ranks) is not met by this evidence.
- Operational findings: tag-radio stragglers were dropped after the 4 s window (1 in run 1, 5 in run 2, first window only). The MusicBrainz tail ran once (run 2, first window: 5 albums). One MusicBrainz search failed with no route to host (run 1, first window). One radio query per run in the first window ended in a connection error, leaving 5 of 6 queries filled.
- No change to code, defaults, or runtime. No publication or deployment.
- Next action (needs owner decision): either measure window effects with repeated radio samples per tag (more live calls, owner approval), or treat window-driven seeds as unproven and stop Phase 3 at the seed level.

## 2026-10-23 — Engine 2 Phase 3: Deep cuts tiered supply with MusicBrainz tail (unwired)

- Added `discovery/deep_cuts_supply.py`: `run_deep_cuts_tag_supply` runs the ListenBrainz tag radio at the owner-approved 50–75% band, then the 75–100% band for queries still empty, then the MusicBrainz tag search for queries still empty. A query no tier reached is marked `not_attempted`.
- A radio tier that marks the lane unavailable (retryable HTTP failure) skips the remaining radio tiers, but not the MusicBrainz tail; the flag is cleared before the tail, which is a different provider. Regression test added (PR #581 review). Without `http_post` the radio tiers are skipped.
- `discovery/candidate_gathering.py`: the radio branch of `_run_tag_lane` moved into `run_radio_lane(..., pop_begin, pop_end)`; default behaviour and cache keys are unchanged.
- Focused tests: 158 passed across gathering, tag lane, replenishment, supply, lenses, title filter, packaging and the size guard. The full unit suite was not run here (CI runs it on the PR head).
- Title-marker check (Phase 2 deferral): the radio path applies `batch_title_marker_rejection` in `synthesize_recording`; the MusicBrainz path relies on the release-group secondary types (`CF_EXCLUDED_SECONDARY_TYPES`). Known gap: an unmarked live album still passes the radio path. Minor: "unplugged" and "bootleg" are batch markers but not in the MusicBrainz title phrases.
- Not wired into runtime; defaults unchanged. No live provider calls, publication or deployment.

## 2026-10-23 — Engine 2 Phase 3 slices 1–2: window helpers merged; live window-pool check (partial gate)

- PR #579 squash-merged as `aea328c`: pure `windowed_listen_weights` (bounded window anchored to the newest listen, optional half-life, flat all-time default) and a tag-radio popularity band parameter. The default 0–100 band keeps the original request and cache key. Focused tests: 69 passed. Not wired into runtime.
- PR #580 (above) added `window_artist_weights` and `densest_window_listens`. The dense-window choice follows the owner's direction: the history ends in 2019, so a last-N-days window is empty.
- Offline, no provider calls by the code: the local history (about 22k rows; about 19k with valid timestamps, 2010–2019) had cached artist tags for 35 of 447 all-time artists. Batch-filling the rest through the existing ListenBrainz artist prefetch reached 447 of 447 in a scratch copy of the metadata cache. Network "No route to host" errors were retried. The source cache was not modified.
- Seed probe (cached tags only): four non-overlapping dense 30-day windows and the all-time window each produce 6 profile seeds, and each pair shares 4–6 of them. Windows reorder seeds and swap one or two genres.
- Live tag-radio run (owner-approved; ListenBrainz tag radio, batch recording lookups, release-group metadata; cache writes to the scratch copy only): five windows, six seeds each, 30 albums each (the 5-per-query cap). No provider failures were recorded. Album-level overlap: dense1 and all-time share 30 of 30; dense3 and dense4 share 30 of 30; other pairs share 20–25 of 35–40. The window changes the candidate pool in most pairs, but only modestly.
- Gate status: partly met. One live run, one profile, profile seeds only (no CF or exploration pool). The Phase 3 gate needs repeat runs and an evaluation of whether the changed pools change any list.
- Probe scripts, raw results and the scratch cache live outside the repository because they derive from the owner's private listening history. Only these aggregates are recorded here.
- Limitation found during the run: a first attempt returned zero albums because the probe skipped the production batch-to-recording conversion. The fixed probe uses the production resolver shape; the earlier results were discarded.
- No publication, deployment, or runtime verification. The CI status of PR #579 was not recorded in this session.

## 2026-10-23 — Re-review, CI verification, and merge PR #580

- Re-reviewed final PR head `f2ca7a9822af0dac592c0e36cd81a7bcee8c25f8`. The earlier findings were addressed: `listen_artist_mbid()` now validates nested metadata as mappings and rejects malformed MBID values safely; `densest_window_listens()` normalizes non-numeric/boolean window widths to `ValueError`. Regression tests cover malformed nesting and invalid widths. The helper remains pure and is not wired into runtime.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40029108109`), Docker packaging/full unit suite/image build (`40029108024`; the unit-test step and image build succeeded), container runtime smoke (`40029108017`), and validation-only multi-architecture image validation (`40029108075`; publishing paused). The full unit suite ran in CI; it was not run manually, in accordance with the repository workflow.
- Squash-merged PR #580 as `ede38e969956d1907ba25e579203c6d4b5805c3b`. The feature remains unwired; defaults unchanged. No publication, deployment, or runtime verification. Phase 3 continues with time-range profiles/window-driven tag-lane seeds and the previously deferred Deep cuts items.

## 2026-10-23 — Engine 2 Phase 2 closeout: Deep cuts band, filter check and tail deferred to Phase 3

- Phase 2 is complete: lens framework and Deep cuts adapter (PRs #575, #577) and evaluation metrics (PR #578). Nothing is wired into runtime.
- The owner decided to leave the 50 to 75% radio band request (it needs a band-keyed radio cache and a decision on live provider use), the check that the title-marker filter covers both candidate sources (`lb_tag_lane.py` states the filter applies to radio candidates; not verified for the MusicBrainz tail), and the MusicBrainz tail for Phase 3. Defaults are unchanged.
- Next action: Phase 3, time-range profiles and window-driven seeds.

## 2026-10-23 — Engine 2 Phase 2 (part 1): lens framework and Deep cuts pool adapter merged

- PR #575 (squash-merged as `85efa95b32ecd1ce42d7afd5293a60cbfcf9f391`): `lens` name on `AllocationRequest` and `AllocationResult` (default `now`); new pure `discovery/lenses.py` with the Now (quota), Genre spread (family coverage) and Deep cuts lenses and `partition_lenses`, which removes the artists and album titles an earlier lens selected before the next lens runs. Deep cuts follows the approved definition (album audience 300 to 50,000, at least 2 tags, one album per artist, at most 2 per seed, ranked by tag strength, unknown audience never selected). After review, partitioning also excludes by album title, and Deep cuts validates `count`, `max_checks` and candidate IDs, enforces the 60-check bound and reports the real checked count.
- PR #577 (squash-merged as `513a4589387a7667569b854c37ace1bf028ab012`): `build_allocation_inputs` takes an optional `popularity` map and fills `audience`, `seed` and `tag_strength` through `deep_cuts_fields`. After review: audience is the album-level listener count only (an artist-level count never passes the album gate), and the tag lane now keeps the radio's per-recording `tag_count` as `tag_strength`. Radio cache entries are now `[recording MBID, tag_count]` pairs; older plain-MBID entries still load with a count of 0.
- Tests actually run by the agent: focused suites only (lenses, allocation contract, allocator, selection inputs, characterization, tag lane, candidate gathering and supply, tag-lane early stop); server-size ratchet. The full suite was not run by the agent. Review reports stated CI was green on earlier heads (`2ebaf61`, `5a8a063`); the final reconciled heads (`1d7c729`, `c1556b0`) were not confirmed by the agent because the GitHub API was unreachable, so confirm required workflows on `main`.
- Not done: nothing is wired into `recommend_new_music` or any route; the lane still requests the full popularity range (0 to 100%), not the approved 50 to 75% band; the title-marker filter and the MusicBrainz tail are not part of the lens; window-profile seeds are Phase 3; per-lens and set evaluation metrics were still open when this entry was written (merged afterwards in PR #578); the lens is not stored on recommendations (Phase 4/5). Not published or deployed; no live-runtime verification.
- Next action: Phase 2 evaluation metrics per lens and across the set.

## 2026-10-23 — Engine 2 Phase 1 closeout; Deep cuts lens approved

- The owner approved the Deep cuts lens as proposed: dense-month or recent window; ListenBrainz tag radio at the 50 to 75% popularity band as the main source, with the 75 to 100% band and the MusicBrainz tag search as the tail; title-marker filter; album listeners about 300 to 50,000; one album per artist; at most 2 per seed. The definition is recorded in `docs/engine2.md`.
- Phase 1 outputs: merged popularity module (PR #574, unwired); measurements and prototype results in the 2026-10-23 entries above; no ranking weight, default or provider budget changed; no code beyond PR #574. Throwaway harnesses and private data files stay outside the repository.
- Not claimed: list quality beyond aggregates and spot checks; behavior for other listeners; any publication or deployment.
- Next action: Phase 2, the lens framework (a design of how lenses enter the allocator request and result, and how lists are partitioned, before code).

## 2026-10-23 — Engine 2: fast end-to-end Deep cuts test across five windows (50-75% radio band plus tails)

Prompted by the owner: the earlier five-window runs took too long. This run was tuned to about 35 s per window (about 3 minutes for all five, sequentially). Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed.

- **Tuning that made it fast:** the recording-batch response already carries the release MBID (`release.mbid`), so no MusicBrainz release search is needed; album listeners only (no artist-level lookup); a pre-gated shortlist (title-marker filter, tag count at least 2, one candidate per artist, 6 from the 50-75% band and 3 from the 75-100% band per seed) of about 30 candidates per window; four parallel Last.fm threads under a 4-per-second limit; one retry with short timeouts; the MusicBrainz tail reused from the earlier harvest (no new MusicBrainz calls). The first two attempts failed for two avoidable reasons: a wrong field name dropped every radio candidate, and swallowed batch errors hid a dropped connection. Both were fixed in the harness.
- **Result (gates: 300 to 50,000 album listeners, one album per artist, at most 2 per seed, tag count at least 2; radio 50-75% first, then radio 75-100%, then the MusicBrainz tail):** four windows reached lists of 10 (2012-04: 9 from the 50-75% band, 1 from the tail, 5 seeds, median 21,534 listeners, 1 album under 1,000; 2012-06: 9 and 1, 5 seeds, median 19,911, none under 1,000; 2014-02: 6 from 50-75%, 2 from 75-100%, 2 tail, 5 seeds, median 12,118; 2011-02: 6 and 4 from 75-100%, 5 seeds, median 6,890, 2 under 1,000). The current profile reached 7 (4 from 50-75%, 2 from 75-100%, 1 tail; 4 seeds; median 1,825). Artist overlap between the first four windows is 0 for all six pairs.
- **Conclusion:** with the 50-75% band as the main source and the title-marker filter and listener gates, the window mechanism produces full, distinct, mostly mid-obscure lists quickly. The first-pass cost is one radio GET per seed per band, one recording batch POST per window and about one Last.fm album lookup per shortlisted candidate (about 30 per window, 150 for five windows); with the windows run in parallel under the same Last.fm limit this is about 40 s.
- **Limits:** one listener; four windows from the same metal and world-music period plus one current profile (which gave a shorter list); the network dropped repeatedly and the harness retried or skipped; tag assignments in the radio are noisy and were only spot-checked; thresholds are untuned; the lists were not judged for quality beyond aggregates and spot checks.
- **Next:** the owner decides the Deep cuts lens definition (window, band, gates); then Phase 2 (lens framework and partitioning).

## 2026-10-23 — Engine 2: ListenBrainz tag-radio popularity band is inverted; 50-75% is the sweet spot (corrects the previous entry)

Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed. Network intermittent again (one radio request failed in the 0-10% run and was skipped; the 2012-06 window was rerun after a total failure).

- **Correction:** the previous entry suggested a lower band (0 to 10%) for more obscure results. That was wrong. In `GET /1/lb-radio/tags` a low `pop_begin`/`pop_end` returns the MOST popular recordings of the tag. Run over the five windows, the 0-10% band returned 310 candidates with median album listeners 539,928 and 232 at 200k or more, against median 224,104 and 177 for 0-25%. Title-marker rejects were 0 of 310.
- **Probe (3 tags, 4 bands, 15 recordings each, album listeners by release MBID):** progressive rock median album listeners 259,203 / 43,474 / 26,934 / 28,813 for bands 0-10 / 25-50 / 50-75 / 75-100; jazz 537,015 / 31,577 / 23,791 / 2,569; metal 280,826 / 75,561 / 17,940 / 1,958. Albums under 50k listeners: 0-10% band 0, 2, 2 of 9 to 13; 50-75% band 10, 12, 10 of 13 to 15; 75-100% band 7, 13, 8 of 12 to 15. Albums under 1,000 listeners: none in the 50-75% band except 1 in jazz; 4, 6 and 5 in the 75-100% band. The upper band gets obscure but also reaches the junk-risk range.
- **Combined lists (0-10% radio plus the MusicBrainz tail, gates 300 to 50,000 listeners, one album per artist, 2 per seed, title-marker filter):** list lengths 8, 10, 8, 8, 7 across the five windows; the radio contributed 1 to 6 per list (it was mostly outside the listener ceiling), the MusicBrainz tail the rest; artist overlap between windows 0 to 2 per pair. The band, not the combination, was the problem, so these lists say little about a final design.
- **Conclusion:** for a Deep cuts lens use the radio with a band around 50 to 75% as the main source (obscure, few junk-range albums), the title-marker filter, a listener floor of about 300 and a ceiling of about 50k; the 75-100% band and the MusicBrainz tag search are the tail for obscure artists, with the floor guarding against junk. This is not yet tested end to end across the windows.
- **Limits:** three tags and 15 recordings per cell in the probe; one listener; the `percent` field's exact meaning is inferred from results (low is popular), not from documentation; the endpoint is undocumented; thresholds are descriptive and untuned.
- **Next:** rerun the five windows with the 50 to 75% band plus the MusicBrainz tail, then decide the lens definition.

## 2026-10-23 — Engine 2 Phase 1 step 4: deep-cuts prototype across listening windows (offline plus read-only calls; no code)

The owner clarified the criterion: the application suggests music to acquire, so predicting later listening is not the goal; what matters is that a dense window changes the tag-lane seeds and that the resulting deep-cuts list is obscure, varied and not junk. The earlier prediction check (previous entry) is therefore informational only. Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed; network intermittent (11 of 30 MusicBrainz searches and 1 radio request failed and were skipped).

- **Windows:** four months from the scrobble export (2012-04, 2012-06, 2014-02, 2011-02) plus the current 15-artist profile. Seeds come from the repo's `select_supplementary_tag_queries`; candidates exclude every artist already in the history or the current pool. Album listeners by release MBID come from the merged `discovery/mbid_popularity.py`.
- **Candidate source A, MusicBrainz tag search (about 8 new artists per seed, secondary types excluded):** 152 candidates; album listeners median 444; 39 of 142 known under 100 and 83 under 1,000 (junk risk: tribute and cover albums appear); 2 of 142 over 200k. After gates (300 to 50,000 listeners, at most 2 per seed, one per artist) lists reach only 4 to 9 of 10. MusicBrainz ratings were absent from search results, so the rating signal was not testable without extra lookups.
- **Candidate source B, ListenBrainz tag radio, popularity band 0 to 25% (30 recordings per seed, resolved through the batch recording endpoint):** 339 candidates; album listeners median 224,104; only 2 under 100 and 10 under 1,000; 177 of 327 known at 200k or more. After the same gates, lists of 6 to 10 reach 4 to 6 seeds. The band is relative within the tag, so for large tags it is still well-known music; the gated survivors are deep cuts by moderately known artists rather than obscure artists. The radio's tag assignment is noisy (a pop album under hip hop, a hard-rock album under metal), and live or greatest-hits albums appear, since the batch endpoints carry no secondary types (the repo's batch title-marker filter exists for this).
- **Windows differ, which was the question:** artist overlap between the window lists is 0 for 9 of 10 pairs and 1 for the tenth (tag-radio lists); with the MusicBrainz source the pairs share 0 to 2 artists, through a few recurring albums for overlapping seeds such as progressive rock.
- **Signals compared for ranking the gated pool:** tag strength (radio `tag_count`), plays per listener, and their product. They select nearly the same lists (overlap 4 to 9 of 6 to 10, identical in five of the ten comparisons made), so the ranking signal matters less than the gates. Plays per listener has median about 11 (quartiles 8 and 17) and separates devoted small audiences from drive-by ones; it is unvalidated.
- **Conclusion:** the window mechanism works; a usable deep-cuts list needs (1) the batch title-marker and secondary-type filter, (2) a listener floor (about 300) and ceiling (about 50k), (3) one album per artist and a per-seed cap, (4) a lower popularity band than 0 to 25% or a combination of both sources to reach obscure artists with enough supply, and (5) seed-tag quality control (tag count minimum) to avoid mislabelled albums. List length of 10 was reached for only one window (current profile), so supply per seed needs to grow before lists of 10 are reliable.
- **Limits:** one listener; four windows from a metal and world-music period plus one current profile; MusicBrainz searches partly failed; no quality judgement beyond aggregates and spot checks; thresholds are descriptive and untuned; the album listener count is a Last.fm audience measure, not a quality measure.
- **Next:** decide the lens definition for Deep cuts (window, source, band, gates), then Phase 2 (lens framework and partitioning).

## 2026-10-23 — Engine 2 Phase 1: taste fit checked against the listening history across four months (offline plus read-only calls)

Prompted by the owner: a dense listening period should give better results whatever the genre, so four months with different tastes were tested against the scrobble export (2010-10 to 2019-05 after dropping 3,031 rows stamped January 1970). Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed. No code, ranking weight or default changed. The network was intermittent during the run (see limits).

- **Method:** profile = flat play counts by artist MBID in one month; fit = the same tag/family cosine as before. Ground truth from the history: positives are artists whose first scrobble falls in the three months after the window; negatives are artists first scrobbled at least 12 months after it; AUC of fit, positives against negatives. Tags for 406 artists came from the ListenBrainz artist batch (95 s).
- **Fit against what was played next (AUC; 0.5 is chance):** 2012-04 progressive metal 0.60 (52 positives, 87 negatives); 2012-06 Maghreb and Tuareg 0.43 (31, 78); 2014-02 progressive and classic rock 0.44 (5, 26); 2011-02 metal with folk and world 0.55 (45, 256). Tag-only and family-only variants fall between 0.41 and 0.60 the same way.
- **Conclusion:** the tag/family fit does not predict the next new artists reliably. It is slightly above chance for two months and below chance for two. It is not validated for ranking and should not be used as a ranking score. The below-chance months may partly reflect the negatives (artists first heard a year or more later, when taste had moved), and 2014-02 has only 5 positives, so the test is crude; the result is "no evidence it works", not proof that it cannot.
- **Seeds do change with the window and follow the taste:** 2012-04 gives progressive rock, progressive metal, metal, ambient, art rock, post-metal; 2012-06 gives rock, progressive rock, raï, gnawa, punk, reggae; 2014-02 gives progressive rock, progressive metal, metal, rock, psychedelic rock, space rock; 2011-02 gives metal, progressive rock, rock, art rock, progressive metal, acoustic rock. The top root families come out as rock and metal in almost every month, so the family labels are too coarse to tell these months apart.
- **Lane stage incomplete:** 13 of the 24 MusicBrainz seed searches failed on the network, leaving 5 to 15 candidates per month; of those, the artists with known audiences were mostly obscure (medians 8k to 153k Last.fm artist listeners) and 1 to 4 per month were both fit >= 0.45 and under 200k. Too few and too uneven to count as a result; to be rerun with a stable connection.
- **Limits:** one listener; four windows; tiny positive set for 2014-02; negatives confounded with later taste; family labels coarse; fit formula untuned; lane stage partial.
- **Next:** rerun the lane stage when the network is stable, then try a signal other than tag cosine (similar-artist links, or co-listening within the history itself) against the same ground truth before building a deep-cuts list.

## 2026-10-23 — Engine 2 Phase 1: dense-month window (2012-04) drives the tag lane (offline plus small read-only calls)

Prompted by the owner: the last 30 days are only about two weeks of listening, so a dense month from the scrobble export was used. Aggregates only; private files outside the repository (mode 600). Small, throwaway harness (not committed): 6 MusicBrainz release-group searches, 2 ListenBrainz artist-tag batch GETs, about 20 Last.fm `artist.getInfo` calls by artist MBID. No code, ranking weight or default changed.

- **Export check:** 22,185 scrobbles, 2010 to 2019; 3,031 rows carry a January 1970 timestamp (bad data, excluded). Densest months: 2012-04 (1,743 scrobbles, 98 artists, 84% with an artist MBID), 2012-05 (1,505), 2012-03 (1,322). That period is progressive metal and rock (Pain of Salvation, Devin Townsend, Opeth, Pink Floyd), unlike the current hip-hop, jazz and pop profile.
- **Window profile:** flat play counts by artist MBID for 2012-04 (75 artists with MBIDs, 67 tagged). The repo's own `select_supplementary_tag_queries` on the top 15 artists gave six seeds: progressive rock, progressive metal, metal, ambient, art rock, post-metal. The current profile's seeds were hip hop, pop, jazz, east coast hip hop, art pop, pop rock. No seed is shared, so **a window changes the tag-lane seeds completely.** This is the Phase 3 gate for the tag lane; the CF pool is still not windowed.
- **Resulting candidates (crude lane: first 5 albums per query, 25 candidates, 18 distinct artists):** only 3 of the 18 artists appear in the current 274-candidate pool. Artist listeners by artist MBID: median 9,889; 21 of 24 known are under 200k and 18 under 50k, against a median of 4.2M for the current CF pool. The lane under a window is where obscure supply is.
- **Fit under the window profile (same tag/family cosine as before):** 17 of 18 artists tagged; quintile cuts 0.00, 0.36, 0.53, 0.64; 6 candidates are both well fit (>= 0.45) and under 200k artist listeners. The current CF pool has a median fit of 0.51 under this profile against 0.41 for the windowed lane. Fit remains an unvalidated, weak taste signal (see the earlier entry).
- **Limits and open issues:** one window, one profile; the harness is not the app's lane (no owned or duplicate filtering; one query returned five albums by a single artist; the ambient seed returned five albums by one artist with fit 0.00); the progressive metal seed produced no candidates and was not investigated; fit is not validated; two-week and one-month windows were not compared for stability; the 1970 rows mean any window code must drop timestamps before 2000.
- **Next:** a deep-cuts prototype that joins fit, obscurity and artist de-duplication under both profiles, then a decision on whether the tag lane alone is enough.

## 2026-10-23 — Engine 2 Phase 1 steps 2 and 3: tag-lane taste fit and seeding (offline, docs only)

Offline analysis of the 8-page / 120-tag capture plus one read-only ListenBrainz artist-tag batch GET for the 38 tag-lane artists (the only new provider call). One profile, one capture. No code, ranking weight or default changed.

- **Step 3, seeding (read from `discovery/candidate_gathering.py`, `discovery/tag_queries.py`):** tag-lane queries come from the 15 highest-weight artists in `recent_artist_mbid_counts`; their cached genre tags are weighted by that artist weight and the top 6 become `profile:` queries, plus 2 `explore:` tags from the CF pool, 5 candidates kept per query (40 in total here). So a history window can drive the seeds: replace the weight map and the profile tags change. Saved-album feedback can already reorder or replace a seed. The CF pool is not affected by a window (ListenBrainz builds it from the whole history).
- **The tag-lane candidates carry no tags in the capture:** 2 of 40 have genres, because the 120-lookup tag budget goes to the CF pool. Their `genre_families` is only the seed's family, so candidates from the same seed are indistinguishable until their artists are tagged. After the batch GET, 25 of 38 artists (66%) have genre tags; the untagged third are the data-poor ones.
- **Fit score tried:** cosine similarity between the candidate's tags and the recent-listening tag vector (weights from the 19 recent artists), at tag level, at root-family level (`fallback_family`), and a mix.
- **It is a weak signal.** On 233 tagged CF candidates the fit has Spearman 0.09 with the engine score (the engine score is mostly collaborative filtering and popularity). As a taste check, owned against unowned CF candidates: AUC 0.59 for tag-level fit, 0.53 for family-level, 0.58 for the mix, against 0.71 for the engine score. Owned albums are only a rough proxy for taste.
- **Tag-lane fit values** (25 tagged artists) range 0.21 to 0.50 with quintile cut points 0.36 to 0.48, similar to the CF candidates (0.35 to 0.52). Within one seed the score orders candidates (for example jazz 0.21 to 0.40), but several seeds give near-identical values (east-coast hip hop: four candidates at 0.48), and `explore:` seeds score lower than `profile:` seeds as expected.
- **Conclusion:** tag overlap with the recent profile can break ties and gate out clear mismatches, but it is not enough alone to rank the tag lane; its discrimination of taste is weak on this profile. Candidates without tags cannot be scored, and they are the obscure ones. A second signal is needed before a deep-cuts list: candidates would need tags (about one ListenBrainz batch call per 75 artists, cacheable) and possibly similar-artist links to the profile artists (not yet tested).
- **Limits:** one profile; the profile vector uses 19 recent artists; owned-versus-unowned is a proxy; the tag-lane sample is 38 artists; the fit formula and the 0.5 mix were not tuned; similar-artist links, MusicBrainz tag counts and the full listening history were not tried.

## 2026-10-23 — Engine 2 Phase 1 step 1: MBID-keyed popularity measured (PR #574, merged)

Owner-approved read-only provider calls on the 203 unowned candidates of the 8-page / 120-tag capture (artist MBIDs 143 distinct). Private results outside the repository (mode 600); aggregates only. One profile, one capture.

- **Last.fm artist listeners by artist MBID:** 203 of 203. Median 4.2M; 17 candidates under 10k, 23 under 50k, 32 under 200k (matches the earlier name-based run).
- **Last.fm album listeners by release-group MBID:** 0 of 203 (error 6, not found). Last.fm's `mbid` wants a release MBID.
- **Release MBIDs:** MusicBrainz release search used as a batch (`rgid:(a OR b ...)`, 25 groups per query, 100 releases per page, so paginated) worked; the ListenBrainz release-group batch (`inc=release`) returns one `caa_release_mbid` per group. On a 25-candidate sample Last.fm resolved 23 via the MusicBrainz release (official first, then earliest) and 19 via the ListenBrainz release.
- **Full run (MusicBrainz search, up to 5 releases tried per group):** 57 MusicBrainz calls covered 175 of 203 groups; 228 Last.fm calls found 166 albums (82%). Median album listeners 1.2M; 32 under 10k, 41 under 50k, 45 under 200k. Tag-lane candidates: 36 of 40 matched, 31 under 50k; ListenBrainz candidates: 130 of 163 matched, 10 under 50k. Ten albums have under 50k listeners though their artist has over 1M. The 37 unmatched are mostly popular (median artist audience 5.1M; 5 under 200k). The 28 groups the paginated search did not cover were not filled in that run.
- **Deezer (name search, no batch endpoint; 8 parallel threads under a 40-per-5-seconds limiter, 52 s):** album fans for 198 of 203. 46 of 163 ListenBrainz candidates show under 1,000 fans though only 4 have a small artist audience, so fan counts mislead for popular artists.
- **Discogs (consumer key and secret, master search, 60 requests a minute, 4 minutes):** `have` counts for 188 of 203.
- **Agreement (Spearman, on candidates both sides matched):** album listeners vs artist listeners 0.62; vs Discogs 0.50; vs Deezer 0.38. Artist vs Deezer 0.38; artist vs Discogs 0.42; Deezer vs Discogs 0.30.
- **Conclusion:** use album listeners by MBID as the obscurity signal with artist listeners by artist MBID as fallback; Deezer and Discogs are optional cross-checks only.
- **Code:** `discovery/mbid_popularity.py` with 20 offline tests after the review fix (PR #574, merged as `eb4cb16`, not wired into any runtime path; no ranking weight, default or provider budget changed). Tests run: `tests.test_discovery_mbid_popularity` plus `test_discovery_artist_genre_batch`, `test_discovery_batch_lookup`, `test_metadata_cache` (50 total, repo venv); size ratchet and legacy-import checks pass. Full suite not run by the agent; CI on the merged head is recorded in the PR #574 review entry below.
- **Module run live on the same 203 candidates (fresh cache, 307 s):** 186 albums found (92%) against 166 above, 17 candidates on artist-level fallback, none without a signal. Calls: 143 Last.fm artist, 233 Last.fm album, 19 MusicBrainz release searches, 2 ListenBrainz release-group batches. The MusicBrainz call count differs from the 57 above (different script); the cause was not investigated.
- **Limits:** one profile; 25-candidate release-resolution sample; correlations only on mutually matched candidates; Last.fm's matched edition not verified; album and obscurity thresholds are descriptive, not tuned.

## 2026-10-23 — PR #573 merged: opt-in family-coverage policy

- Squash-merged as `9b1dab53f2fc480fd74f4e24560ebb6dd7ed14e1` from exact tested PR head `1c67f61add223274a898aeb3061d95a1664139f8`.
- The final review fix moved ownership classification and allocation-input construction to `discovery/allocation_inputs.py`, and quota/coverage request options and diagnostics to `discovery/selection_policy.py`; `recommend_new_music()` is 418 lines. The enforced limit was not raised.
- Regression coverage checks ownership classification and stable allocation inputs, legacy quota targets/default response shape, opt-in family-coverage options/diagnostics, and fallback for unknown setting values.
- Required CI passed on the exact PR head: Python syntax/acquisition safety run `39944738730`; Docker packaging, full unit suite and image build `39944738753`; container runtime smoke `39944738722`; non-publishing multi-architecture validation `39944738756`. Release workflow validation `39944738733` passed with the publishing job skipped. The full unit suite was run by CI, not locally. No browser check was performed.
- Remaining evidence limits: one profile and individual captures; no listening-quality claim; replay captures do not freeze the selection-policy setting; the per-artist MusicBrainz fallback path was not exercised. No publication or deployment.

## 2026-10-23 — PR #573 review fix: legacy-server size ratchet

- The reviewer found `recommend_new_music()` at 474 lines against the 450-line exception (the Python syntax workflow failed at the size ratchet). `main` was exactly at 450, so any addition inside the function failed. The limit was not raised.
- Fix: ownership classification and `AllocationCandidate` construction moved to `discovery/allocation_inputs.py`; quota targets, the family-coverage request options and the opt-in response diagnostics moved to `discovery/selection_policy.py`. `recommend_new_music()` is now 418 lines. Behavior is unchanged for both policies.
- Tests added: `tests/test_discovery_selection_inputs.py` (ownership statuses, input building and genre family, quota split, policy options and report) and three server-level cases (default policy keeps quotas and the response shape; opt-in policy sets the allocator options and reports genre families; unknown value falls back to quota).
- Run locally: the steps of the Python syntax workflow (py_compile list, size ratchet, app import boundary, dependency map) and the focused test modules touching the change. The full suite was not run locally; CI results for the updated head are recorded in the PR.

## 2026-10-23 — Obscurity measurements and Engine 2 roadmap (docs only)

Owner-approved read-only provider calls (Last.fm `album.getInfo` for 203 unowned candidates, `artist.getInfo` for 144 artists, about 20 Deezer lookups); private result files outside the repository (mode 600); aggregates only. One capture (8 CF pages, 120 tag lookups), one profile. No code or default changed by this entry.

- **Popularity data is nearly absent from captures.** The engine looks up Last.fm popularity for about 40 candidates per run; 12 unowned candidates carried listener counts and the smallest was 9,382.
- **Album-level Last.fm lookups mismatch** on titles with brackets, curly quotes or edition suffixes, making well-known albums look obscure. Artist-level lookups are better but mismatch on "feat." credits and non-ASCII hyphens. MBID lookups are needed.
- **Artist listeners, 203 candidates:** median 4.2M; 33 (16%) under 200k; 22 under 50k; 17 under 10k.
- **Obscure candidates come from the MusicBrainz tag lane:** 29 of 40 (73%), against 4 of 163 (2%) from ListenBrainz CF. All tag-lane candidates share the base score 0.035 (no taste bonus), so they never rank.
- **Score tracks popularity:** median album listeners 2.7M for the top 20 by score, 75k for ranks 120 and below.
- **Deezer (no key):** 15 of 20 sampled albums matched; 0 to 132 fans for albums with 1 to 554 Last.fm listeners, 54 to 348,362 for 4.0M to 5.3M. Separates extremes, noisy mid-range.
- **Roadmap:** `docs/engine2.md` (lenses, other data sources, phases, evaluation metrics, open decisions). `ACTIVE_WORK.md` section 2c lists Phase 1 as the next priority.
- **Limits:** one profile and one capture; album-level counts unreliable; the tag-lane seeding code was not read; Deezer/Discogs/others unverified beyond the Deezer sample; no listener-quality measurement.

## 2026-10-23 — Family-coverage selection policy and genre-tag budget (PR #573, merged)

Owner-approved live captures (read-only, slskd off, aggregates only, private captures outside the repo, mode 600). Single profile, one capture per arm; no recommendation-quality claim.

- **Finding.** With the quota policy the wider CF pool barely reaches the final list: genre-tag lookups were capped at 60 (+15 recent) artists whatever the pool size, so extra candidates arrived untagged, scored low, and never ranked. Untagged unowned candidates at 4 / 8 / 12 CF pages: 40 / 97 / 128 (60 lookups), 15 / 39 / 61 (120), 15 / 13 / 15 (220). 220 gained nothing over 120.
- **Label correction.** The first experiments labelled families by the alphabetically first tag through the rules table ("alternative rock" -> "alternative"), which inflated family counts. The final label is `primary_genre_family`: plurality of `fallback_family` (trailing root word, then the Wikidata ancestry table) across all tags.
- **Offline (real allocator, 9 captures, count 10).** Cap 2 alone is about level with 4/3/3 on spread and higher on engine score (0.158 vs 0.14 to 0.145). The coverage phase is what uses the wider pool: with 8+ CF pages and 120 tags, coverage at floor 0.4 reached 9 families (entropy 3.12, mean score 0.147 vs 0.145 for 4/3/3, 6 families). At 4 pages the pool cannot exceed 7.
- **Live end to end (new code, tag budget 120).** quota @4 pages: 7 families, 4 rock; family_coverage @4: 7 families, max 2 per family; family_coverage @8: 9 families, max 2. 10 recommendations and 10 artists in each, no provider failures.
- **Change.** Commit 1: tag budget 60/75 -> 120/135 (named constants). Commit 2: opt-in `recommendation_selection_policy = family_coverage` (default `quota`, legacy path unchanged): genre-family cap 2 (unknown 1), adventurous floor `count // 5`, coverage phase above 0.4 x top score, score fill, relaxed final fallback; owned candidates do not use the 60-check budget under this policy. `CF_MAX_PAGES` left at 4.
- **Limits.** Replay captures do not freeze the policy setting, so family_coverage captures do not reproduce under default settings. Coverage lists lean toward higher-scoring, better-known albums than the quota list in the one live comparison (the quota list had a jazz and two lesser-known picks the coverage list lacked); whether that is better or worse is not measured. No setting UI, no browser check, not published or deployed. Engine score is not a listening-quality measure.

## 2026-10-23 — CF freshness repeat, deeper CF pages, and recent-vs-all-time profile comparison (docs only)

All live runs were approved by the owner; slskd off; aggregate only; harnesses were one-off scripts and are not committed; temporary data dirs deleted. No code, default, or ranking weight changed. Single samples throughout; none supports a recommendation-quality claim.

- **P0h repeat (CF freshness).** 4 CF pages, 3 recent-listen pages, 1 `stats/.../recordings` GET (200). CF pool 400 of 1,000; recent 30 days 100 listens / 89 distinct mapped recordings; all-time top 1,000 items / 902 with a recording MBID. CF in recent: 2 (0.5%). CF in all-time: 44 (11.0%), all of it all-time-only (X = 11.0%). All-time matches per CF page 10, 11, 13, 10 (baseline of 2026-10-21: 23, 10, 1, 3 on page 1). Decision-table outcome: **mixed; keep defaults.** The even spread across pages, against the page-1 concentration of the baseline, is consistent with ListenBrainz having recomputed CF; this was not independently verified (the baseline CF recordings were not retained).
- **P1a repeat (deeper CF pages), `CF_MAX_PAGES` 4 / 6 / 8.** Test-only override, fresh data dir per arm, one cold and one warm run per arm, 10-minute pause between arms (the 2026-10-21 run had none).

| Pages | Cold | Warm | CF recordings resolved | LB candidate albums | Final list overlap with 4-page (cold / warm) |
| --- | --- | --- | --- | --- | --- |
| 4 | 27.7 s | 11.4 s | 400 | 117 | n/a |
| 6 | 38.9 s | 9.9 s | 600 | 180 | 9/10, 9/10 |
| 8 | 34.0 s | 10.2 s | 800 | 234 | 9/10, 9/10 |

  Final list 10 albums / 10 artists in every run; no ListenBrainz 429 or 502; one MusicBrainz 503 (6-page cold run). The 6-page cold run missed the +10 s threshold by 1.2 s; the 8-page cold run passed (+6.3 s). Eligible unowned albums were **not** captured, so candidate albums stand in for them. Each extra 2 pages cost 2 CF GETs and 2 recording-batch GETs, with no fallback to per-recording lookups. The 2026-10-21 cold-run failure (429s, fallback, 183.6 s) did not recur. **Decision: keep `CF_MAX_PAGES = 4`.** The larger pool changes the final list by one album; 8 pages is the candidate if more supply is wanted later.
- **Recent 30 days vs all-time profile (full-engine responsiveness; offline replay of one live capture).** One live capture (cold, 22.1 s, 10 recommendations, 152 ranked candidates), then `recommendation.profile_comparison` building blocks with a one-off driver. History: the owner's 22,185-scrobble export (2002-10-01 to 2019-05-26; artist MBIDs on 18,023 rows; 3,031 rows carry a 1970 timestamp in the raw export, so dates came from the cleaned export, which aligns row for row). Profiles: recent 30 days (100 listens, 24 artists, 76 genre-classified listens, 8 families) vs all-time (22,285 listens, 721 artists, 18,112 with an artist MBID, 3,060 genre-classified, 8 families).
  - All-time with **flat** weights vs recent: 9/10 final overlap (Jaccard 0.82), 5 positions changed, 143 of 152 shared candidates changed rank, maximum displacement 55; category split unchanged (4 adjacent / 3 adventurous / 3 cross-genre); 10 distinct artists in both.
  - All-time with the **production** 14-day half-life vs recent: identical (10/10, 0 rank changes), because decay is anchored to the newest listen and the older history weighs about zero. The app today effectively ignores history older than a few weeks.
  - Allocator: about 90 of 152 candidates are blocked by the recent-genre cap in both profiles (88 and 90); only 1 to 2 of the 10 selections come from the top 10 by score.
  - Limits: one frozen pool and one capture; candidate generation not varied (the CF pool is built by ListenBrainz from the whole history); genre data exists only for artists already looked up in the snapshot, so the all-time family profile is partial; 11 popularity lookups had no captured data in the all-time arm and were treated as no bonus (no live request).
  - Reading: ranking responds to listening habits; the final list barely does. Same shape as the 2026-10-18 result (PR #361 harness). No weight change is justified by this.
- The private capture contains listening history and stays outside the repository (owner-only directory).
- Next: optional, owner's decision. Investigate why the recent-genre cap removes about 60% of candidates in both profiles, or request approval for 8 CF pages if more candidate supply is wanted. Neither is started.

## 2026-10-23 — Genre ancestry table extended to 398 tags (PR #572)

- PR #572 squash-merged as `133a510627d42fecf86241a3f4f04a189950a65c` from exact head `344b8775863ba55a13bca3951b45e9f62080ccaa`; all four required workflows passed, including the full unit suite (test-and-build run `39873873438`). CI was not re-checked on the merge commit.
- `settings/genre_ancestry.json` grew from 205 to 398 tags, built with `scripts/build_genre_ancestry.py` from a broad seed list plus all tags seen in the owner's captures (263 of 284 new tags resolved on Wikidata). New roots: gospel, latin, and ska (mapped to reggae). Wikidata's wrong placements were corrected with curated `OVERRIDES` (metalcore/deathcore/grindcore/mathcore/djent/post-metal to metal; amapiano/gqom/kwaito/kuduro/afrobeats to african; choro/forro to brazilian; lovers rock to reggae; and others). No existing entry changed. The build script now backs off when Wikidata throttles.
- A frozen-capture check on the owner's latest capture is unchanged (28 adventurous / 88 adjacent / 32 cross-genre / 12 unclassified; targets met) because the owner's tags were already covered. Known soft spots: darkwave/coldwave map to rock and bare `minimal` to electronic. Focused tests only run locally; not published or deployed.

## 2026-10-23 — Derived taste profile follow-ups: labels, ancestry fixes, fixed tables removed (PRs #570, #571)

- **#570** squash-merged as `b0a0132578e729edfaeec2303f68e67366c78fda` from head `c143451f891cb541d66aca0133d9f50a4f755c0d` (all four required workflows passed). Deep Dives rows and tag-query family labels now use the derived family vocabulary; the Deep Dives rule table is gone. A row's key is the family of the artist's first tag that yields one. The Wikidata ancestry table was corrected (metal subgenres wrongly under rock, punk rock, soul-adjacent entries under pop, unresolved baroque/dub/dance/k-pop and others) and `scripts/build_genre_ancestry.py` now applies trailing-root-word normalization and a curated `OVERRIDES` map on every build.
- **#571** squash-merged as `ba2f235a4f9e82fdb98139c50b5c512c83438824` from head `2fcce6759e5d8071f66a35781dd834192f66b403`; all four required workflows passed, including the full unit suite (test-and-build run `39872383954`). CI was not re-checked on the merge commits. It removes the default core/exploration family sets, the regional artist-name list, the adventurous-tag list, the diversity-style artist and region lists, the `taste_profile_mode` setting and the fixed-vs-derived comparison tooling. `classify_diversity_style` now returns the candidate's primary derived family. Sparse listening history derives the core from the candidate pool (`candidate_pool_sparse_history`); no history and no pool gives an empty profile (`no_profile`).
- **Kept, deliberately:** the tag-to-family grouping rules, recent-style terms and display labels in `settings/taste_defaults.json`; they group and name genres rather than decide taste. Removing them would lose regional families such as African and Brazilian.
- **Category rule (owner chose "option 2"):** two or more core taste clusters = cross_genre; otherwise any exploration-family overlap = adventurous (still receiving the x1.10 bonus), even when the candidate also touches a core family; otherwise core overlap = adjacent; no overlap = adventurous. Reason: after #570 the old adventurous candidates were revealed as vocabulary-miss artifacts (labelled family `other`), leaving the category empty with its target unmet.
- **Exploration bonus review:** on the owner's capture the exploration set is only `electronic`; disabling the bonus changed 1 of the top 10. No weight change.
- **Replay:** captures now record taste clusters (a derived capture could not otherwise reproduce); a live capture on the #571 branch replayed with `reproduced: true`. Captures taken before this change no longer reproduce. Frozen-capture check of the final rule (160 candidates): adjacent 88, cross_genre 32, adventurous 28, unclassified 12; selected top 10 = 4/3/3 with all targets met and 7 of 10 picks unchanged. Two additional read-only live captures of the owner's profile were taken during this work (private, outside the repository, mode 600).
- **Limitations:** one real, jazz-leaning profile; no browser check of the new Deep Dives rows or the "Style:" label; no publication or deployment; focused tests only run locally.

## 2026-10-23 — Derived taste profile made the default (PR #569)

- The owner decided that derived mode becomes the default. PR #569 squash-merged as `b5c77c0b9f88782cc16d3971b5ab56d6f5e2f9aa` from exact head `5a38d1a4e8f658347c05703cebbef56db5573de6`; all four required workflows passed on that head (test-and-build, including the full unit suite, run `39870109947`). CI was not re-checked on the merge commit.
- `DEFAULT_TASTE_PROFILE_MODE` is now `derived`; absent or unknown stored values mean `derived`, and `taste_profile_mode=fixed` restores the shipped tables. Sparse listening history still falls back to the complete fixed behavior.
- **Kept, not removed:** the fixed tables, regional artist list and adventurous tags (they back the `fixed` option and the sparse fallback). Deep Dives rows and tag-query labels still use the fixed vocabulary. Removing the fixed tables remains a separate owner decision.
- Expected effect for a user with no stored setting, from the owner's capture: adventurous candidates 47 to 15, 44 candidates receive the x1.10 exploration bonus where none did, 8 of the top 10 unchanged. Focused tests only were run locally; not published or deployed; no live-runtime or browser verification.

## 2026-10-23 — Derived taste profile: Phases 2-4 evidence merged (PRs #565-#568)

- Squash-merged to `main` in order, each brought up to date with `main` and merged only after the four required workflows passed on its exact head (compile, container-smoke, test-and-build with the full unit suite, validate-container; publishing skipped): #565 `218ce4cdfc6b152ef1cbe614e4fb661894bf8603` (head `603541dca892540474520c4a995ff9731b07b6b8`, test-and-build run `39868468298`), #566 `f81443bfe4ce8b26cce818bfa8ef7055523b3640` (head `55b13d9ee3809002351536cf7349cd8e84b45df8`, run `39868728929`), #567 `9d7a0e7e6459738af61ee7fa1d18251f7a511760` (head `83be06b4e97050ba6e4096a4cd8c3ad7bb3ee1ca`, run `39868997784`), #568 `4c2a95e19cc8c4e83ad34fce9f6e2e4f3aab3748` (head `85ab821a11d3b4d3b744abef1f3950f5e4f1560b`, run `39869256200`). CI was not re-checked on the merge commits. Phase 2 (defaults in `settings/taste_defaults.json`) was #563; the opt-in mode was #564.
- **What changed (derived mode only; `taste_profile_mode` stays `fixed` by default):** #565 adds `recommendation/taste_profile_evaluation.py` (synthetic fixed-vs-derived comparison). #566 groups unmatched tags by trailing root word, then a static Wikidata ancestry table (`settings/genre_ancestry.json`, rebuilt with `scripts/build_genre_ancestry.py`), then the head-noun fallback. #567 merges core families whose listens overlap (Jaccard >= 0.5) into taste clusters, so cross-genre needs two clusters. #568 adds `python -m recommendation.replay <capture> --compare-profile-modes`.
- **Live captures:** two captures of the owner's profile were taken with the owner's approval (read-only provider calls, isolated data directory, slskd disabled). The files are private, outside the repository, mode 600, and were not committed. The second capture replays to identical output.
- **Evidence on the owner's profile (155 candidates, aggregates only):** fixed vs derived with ancestry and clusters: adjacent 65 vs 101, cross_genre 36 vs 32, adventurous 47 vs 15, unclassified 12 vs 12; exploration-bonus candidates 0 vs 44. Frozen-capture ranking comparison of the top 10: the fixed run reproduces the capture; 8 of 10 recommendations are shared, mean rank shift 1.0, identical selected category mix, 7 vs 14 distinct families. The derived run had 8 Last.fm lookups absent from the capture (no popularity adjustment), so the 2 differing picks may partly reflect that.
- **Synthetic profiles (hand-written, not real listeners), adventurous share fixed to derived:** metal 0.9 to 0.3, classical 0.9 to 0.3, k-pop 0.5 to 0.2, mixed 0.5 to 0.4, jazz 0.4 to 0.5.
- **Limitations:** only one real profile (jazz-leaning) exists; no non-jazz capture. The ancestry table has errors (some metal subgenres map to rock) and 36 searched tags did not resolve. Deep Dives and tag-query labels still use the fixed vocabulary. Manual browser checks: none performed. No publication or deployment.
- **Next action:** the owner decides whether derived mode should ever become the default. Open levers if so: the exploration bonus (44 candidates vs 0) and the jazz-profile adventurous increase.

## 2026-10-22 — PR #560 merged: artist bios for instrumentalists

- PR #560 squash-merged as `ffff550c2336ca3dcd56a301c9ae7fffe9f0104b` from exact head `0f2ae27562a175e237a7c7364d380dae7b49f5a0`. Root cause of the missing album-panel bio: `_ARTIST_DESCRIPTION_RE` in `app/services/artist_bio.py` had no instrument terms, so Wikidata descriptions such as "American jazz saxophonist" were rejected and the bio came back empty. Added instrumentalist and ensemble terms.
- Tests actually run: `tests/test_artist_bio_service.py` (7 pass), plus a direct endpoint call returning bios for John Coltrane, Bill Evans, and Art Blakey. Required CI (compile, container-smoke, test-and-build, validate-container, validate-release-workflow) passed on that exact head; publishing skipped. No browser check; not published or deployed.
- The owner confirmed the section-label size and Deep Dives card spacing items are done, which closes the 2a list.

## 2026-10-22 — Published image v0.2.2

- Owner explicitly authorized publication. Annotated tag `v0.2.2` was pushed at `0b1111114e0e751928312e76a287123061640343`, the then-current `main` head. All four required workflows had passed on that exact commit.
- Release workflow "Publish Docker release" run [39835121956](https://github.com/abucalip/navi-librarian/actions/runs/39835121956) succeeded (`publish-release`; the validation job was skipped for a tag push). It enforces tag == current `main`, runs the container smoke test, and builds `linux/amd64` and `linux/arm64` with provenance and SBOM.
- **Published:** `ghcr.io/abucalip/navi-librarian:v0.2.2` and `ghcr.io/abucalip/navi-librarian:sha-0b1111114e0e751928312e76a287123061640343`; package version digest `sha256:8ec36eaea585292f73ff7ec3546d96e4c5bc135b08fb3ccbcee789675f3f3ea2` (from the GitHub Packages API). `latest` was not moved.
- **Not verified:** per-platform manifests were not inspected, the image was not pulled or run, and no GitHub Release was created. Not deployed; no live-runtime verification. Manual browser checks for the included UI changes remain waived/not performed; PR #526/#527 runtime checks remain outstanding.

## 2026-10-22 — PR #558 merged: Deep Dives artwork loading improvements

- PR [#558](https://github.com/abucalip/navi-librarian/pull/558) squash-merged to `main` as `d44c01669611bd11acfaa4f1197905afed7f9f08`, from exact tested PR head `976c86e77034322e53cc7aea9691fa840c2d6146`.
- Review blockers were resolved before merge: capped MusicBrainz result sets are recursively split so a truncated response cannot cause a missing album year to be negatively cached, and regression coverage exercises that case. The PR was aligned to current `main`.
- **Automated verification on the exact PR head:** full unit suite and Docker build passed in workflow `39827794898`; Python syntax passed in `39827794888`; container runtime smoke passed in `39827794833`; validation-only multi-architecture image check passed in `39827794825`; release-workflow validation passed in `39827794824`. The publishing job was skipped as intended.
- **Manual browser verification:** explicitly waived by the owner and not performed. Deep Dives artwork performance was not re-measured in a browser, so UI behavior/performance is not claimed as verified.
- No image was published, no deployment occurred, and live runtime was not verified. Publishing/deployment remain paused.
- Documentation closeout commits: `docs/PROJECT_STATUS.md` `05cd398b17055cf8724c44f9fdf5fd3892a704eb`; `docs/ACTIVE_WORK.md` `64fd0b6f9b29dab956ef14656dbf8a84e14b8a7c`; `PROJECT_LOG.md` `1ecf065b69384711de24cba31c71e7bd89f272a5`.

## 2026-10-22 — PR #557 merged: similar-to discovery labels

- Merged PR [#557](https://github.com/abucalip/navi-librarian/pull/557) by squash. Merge commit on `main`: `45cf5abe0257e70fe0d0573365259c2d0c7c2c10`; exact tested PR head: `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`.
- Adds `discovery/similar_artists.py` and tests for similar-artist matching; the server includes `similar_to` in recommendation payloads, and Recommendations/Personal discovery rows show “Similar to: …” when related listening-profile artists are available.
- Required workflows passed on the exact PR head: Python syntax/acquisition safety run 39807842253; container runtime smoke 39807842257; Docker packaging, full unit suite and image build 39807842282; release workflow validation 39807842267 (the `publish-release` job was skipped); validation-only multi-architecture image check 39807842351. No claim that the suite was rerun on the merge commit.
- The owner explicitly waived manual browser verification; it was not performed. No image was published, no deployment occurred, and production runtime was not verified.
- Also retired the old `~/navi-librarian-test/test-pr.sh` workflow in `docs/LOCAL_UI_TESTING.md`; the guide now refers to the replacement local test environment without relying on the obsolete helper.
- Documentation closeout commits: `docs/PROJECT_STATUS.md` bfd8a25d06f7475a88f2e1bfc8c8fa10570ff653; `docs/ACTIVE_WORK.md` 8cbed8f810792d713be9cb30b843c79c484099ec; `PROJECT_LOG.md` pending this entry.

## 2026-10-22 — Retire obsolete local UI test helper instructions

- Updated `docs/LOCAL_UI_TESTING.md` in commit `a8a63764036c265a30e322adccf134b5485f8f6d`: explicitly marked `~/navi-librarian-test/test-pr.sh` obsolete, removed its commands and helper-specific setup/report assumptions, and retained a current browser checklist requiring exact-SHA identification, isolated test data, disabled acquisition services unless authorized, and recording pass/fail/skip results. The document points to the replacement local test environment without inventing an unverified launcher command.
- Updated `docs/PROJECT_STATUS.md` in commit `ee15bacdac965442c85fd4999faf15343024b581` to reflect the documentation change and PR #557's outstanding manual browser gate.
- PR #557 head remains `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`; automated full-suite and required CI evidence previously passed on that head. Manual browser testing has not been performed. The instruction to merge did not explicitly waive the documented manual UI gate, so the PR remains unmerged pending the browser check or an explicit waiver. No publishing or deployment occurred.

## 2026-10-22 — PR #556 review; reconciled replacement PR #557

- Reviewed PR #556, “Add ‘Similar to’ labels to Recommendations and Personal rows.” Its base was the feature branch from merged PR #555, so retargeting it to `main` would include duplicated/conflicting stacked changes. Closed #556 as superseded and created replacement PR [#557](https://github.com/abucalip/navi-librarian/pull/557) directly from current `main`, preserving only the intended four-file change.
- Replacement PR head: `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`. It adds a directly tested `build_similar_to_lookup` helper, attaches `similar_to` to normal and ownership-review payloads, and updates the UI labels. No provider calls or recommendation ranking budgets were added.
- The first syntax/guard run failed because `recommend_new_music()` reached 461 lines, above its 450-line ceiling. The lookup construction was moved into the reusable helper, with a regression test. The next run showed 452 lines, so redundant blank lines were removed; the final exact-head syntax/size guard passed. No guard thresholds were changed.
- **Full unit suite:** passed on the exact final head in Docker packaging workflow run `39807842282`, job `test-and-build`; Docker image build also passed.
- **Required workflows on exact final head:** Python syntax/acquisition-safety run `39807842253` passed; container runtime smoke `39807842257` passed; Docker packaging/full unit suite/build `39807842282` passed; validation-only multi-architecture image check `39807842351` passed. Release workflow validation `39807842267` passed with its publishing job skipped.
- **Manual UI verification:** not performed in this session. `docs/LOCAL_UI_TESTING.md` requires browser checks against the exact tested SHA for UI-facing changes. PR #557 remains open and unmerged pending that gate. The owner may test with `~/navi-librarian-test/test-pr.sh 557` or explicitly waive the manual gate.
- No image publication, deployment, or live-runtime verification.
- **Next action:** complete or explicitly waive manual browser testing for exact head `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`; then recheck PR state and merge only if the gate is satisfied.

## 2026-10-22 — PR #555: artist bios and dashboard discovery UI refinements

- **PR #555** squash-merged as `f80254550369ed56b66e114faebb2b9fb72ed6bf` from exact head `58bbe0e4ef7320c14146a6fa4ea5a3ef0d266953`.
- Changes include the Wikidata `Accept: application/json` header and avoiding a 24-hour empty-bio cache when the Wikidata search request fails; artist bios on dashboard and discovery cards; removal of New Releases source/reason text; more specific low-confidence genre messaging; consistent “Adventurous discovery” labels; responsive row artwork sizing; Deep Dives album-year placement; smaller one-line category tags; and yellow year styling. Three artist-bio regression tests were added.
- **Full unit suite:** passed in GitHub Actions on the exact PR head, run `39806088731`, job `test-and-build` (“Run unit tests” succeeded). Docker image build succeeded in the same job.
- **Required workflows on exact head:** Python syntax check `39806088756` passed; container runtime smoke test `39806088730` passed; Docker packaging/full unit suite/build `39806088731` passed; validation-only multi-architecture image check `39806088814` passed. Release workflow validation `39806088786` passed with the publishing job skipped.
- **Manual UI verification:** the owner reported the PR was manually tested in the browser and all is working well. No separate browser test was run in this session.
- No image publication, deployment, or live-runtime verification. The existing publication/deployment pause remains in effect.
- **Next action:** retain the runtime-verification priority in `docs/ACTIVE_WORK.md`; do not publish or deploy.

## 2026-10-22 — PR #554: larger row artwork and artist bio on discovery rows

- **PR #554** squash-merged as `c9fcf3289f37984258aca5b62891d700c569d5c1` from exact head `8c8d473f3b9576fbf0dc278c702b9843b422d991` (branch `feat/dashboard-row-bios`, two feature commits plus one review fix). Ranked-row artwork is 96px (80px up to 1200px wide, 64px up to 620px wide). The artist bio now shows in the middle of every row on Recommendations, New releases, and Personal discoveries (previously only genre-connected Personal rows). "Add to your collection" and Saved rows are unchanged.
- Rows keep one height (the artwork size). The bio is clamped to two lines with an ellipsis; a bio that does not fit becomes a keyboard-operable toggle (`role="button"`, `aria-expanded`, Enter/Space) that grows only its own row and does not open the album panel. A review pass caught that the first CSS edit had also enlarged acquisition-row artwork; this was reverted before merge.
- **Tests run (focused only):** all `tests/*ui_contract.py` (251 passed) and `node --check static/app.js`. New contract file `tests/test_row_bio_expand_ui_contract.py`; the title-clamp count test now allows the bio clamp. The full unit suite was not run locally.
- **CI on the exact head:** Python syntax check, container runtime smoke test, and release-workflow validation passed. Docker packaging (`Validate Docker packaging`, run `39796796155`, which runs the full unit suite) and `Validate Docker image (publishing paused)` (run `39796795957`) had **not completed** when this entry was written, and the PR was merged before they finished. Their results are not recorded here; check them on `main`.
- **Manual browser check (`LOCAL_UI_TESTING.md`, `test-pr.sh 554`):** performed by the owner against this head, reported as "tested and working". Specific checklist items were not itemized, and performance was not measured.
- No image publication, deployment, or live-runtime verification.
- **Next action:** confirm the remaining CI runs for `c9fcf3289f37984258aca5b62891d700c569d5c1` finished green, then continue with the next item in `docs/ACTIVE_WORK.md` section 2a ("Similar to:" labels).

## 2026-10-22 — Live-runtime verification attempt for PRs #526 and #527 blocked by access

- Re-read current project status, requirements, development workflow, test plan, active work, and the merged PRs. Current `main` before this documentation update was `fbc806badd9006853d2ccab45af19101809cb15a`.
- Confirmed PR #526 is merged as `4fcd5ff78dc7cfebe99d289a49cd8505c6ca9138`; it retries only failed tracks from the same source, at most three times 30 seconds apart, and keeps a 15-minute recovery grace. Its automated regression tests and CI do not establish behavior against real slskd state strings or queue operations.
- Confirmed PR #527 is merged as `e03f4b35c66745f71b45f01481dbed5547c7a45e`; masked artist variants are inserted after the unmasked query. Its automated tests do not establish live search behavior or real no-match diagnostics.
- **Runtime verification not performed:** this session has no connection to the running Librarian host or slskd API. These changes have not been published/deployed. No live search was issued, no transfer was queued, and no production data was changed. Publishing/deployment remain paused.
- **Next action:** arrange authorized access to an isolated Librarian test instance connected to the real slskd service. Test failed-track retry/recovery using an isolated test acquisition, then test masked queries and no-match diagnostics. Do not claim completion until results are captured; do not use a production transfer as a test substitute.

## 2026-10-22 — Reconciled and merged PRs #530–#535

- **PR #530 — imported-album filtering:** squash-merged as `0b2bda011b86d2c08a0179e5df801c7891c10f9a` from exact tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`. Required workflow runs passed: syntax/acquisition safety `39780311719`, Docker packaging/full unit suite/build `39780311736`, container smoke `39780311752`, validation-only multi-architecture `39780311800`, and release validation `39780311809` (publishing skipped).
- **PR #531 — mobile navigation:** original stacked PR closed as superseded. Reconciled replacement PR #546 merged as `f884f004de83a6c373c16699b560e25312b41a3d`, tested head `53026bcbff794c04b6f901aefeb4fa939403cd7e`. Required workflows passed on that exact head: syntax `39782554896`, Docker packaging/full unit suite/build `39782554899`, container smoke `39782554893`, validation-only multi-architecture `39782554867`, release validation `39782554862` (publishing skipped).
- **PR #532 — artist bio in album panel:** original stacked PR closed as superseded. Reconciled replacement PR #547 merged as `4e11053ae5d203a4287a27abb162b4a9d093bf60`, tested head `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a`. Required workflows passed on that exact head: syntax `39782630505`, Docker packaging/full unit suite/build `39782630071`, container smoke `39782630499`, validation-only multi-architecture `39782630190`, release validation `39782630442` (publishing skipped).
- **PR #533 — equal-width ranked rows:** reconciled original branch without force-pushing and merged as `8beb5baac431e6916d434efd111d96d98c4b8d9b` from exact final head `2948e56185608c8c3d798f38690f022253831940`. Required workflows passed on that exact head: syntax `39783301040`, Docker packaging/full unit suite/build `39783300845`, container smoke `39783300851`, validation-only multi-architecture `39783300775`, release validation `39783301000` (publishing skipped).
- **PR #534 — stable acquisition rendering:** reconciled original branch without force-pushing and merged as `871d3dd4401e493315e38f021bcdeec7918e0900` from exact final head `aea6b57045f2de06cf2eba89d99663d58b6dc699`. Required workflows passed on that exact head: syntax `39783571973`, Docker packaging/full unit suite/build `39783572017`, container smoke `39783571955`, validation-only multi-architecture `39783572002`, release validation `39783571972` (publishing skipped).
- **PR #535 — card artwork loading:** reconciled original branch without force-pushing and merged as `785715320c45b0e79d5f93873953b85859d4891f` from exact final head `15a2195685af26eaab69246a4069e928336692a6`. Required workflows passed on that exact head: syntax `39783827113`, Docker packaging/full unit suite/build `39783827065`, container smoke `39783827116`, validation-only multi-architecture `39783827092`, release validation `39783827150` (publishing skipped).
- The owner explicitly waived manual browser checks for this merge batch; none were performed. No artwork before/after performance measurement was made. No image publication, deployment, or live-runtime verification occurred. All temporary validation PRs were closed. The original #531/#532 PRs were closed as superseded; #530 and #533–#535 were merged directly.
- **Next action:** verify the already-merged #526 and #527 behavior against the live slskd runtime only with appropriate authorization; do not publish or deploy.

## 2026-10-22 — Open PR review and full-suite validation for PRs #530–#535

- Reviewed all six open product PRs. PR #530 (imported-album cache filtering) has no code-review blocker identified and its exact final head `df3dd651051826f483831b5a868dd16483f75fa4` passed all required CI, including the full unit suite: syntax/acquisition-safety run 39772679218; Docker packaging/full suite/build 39772679339; container smoke 39772679292; validation-only multi-architecture image 39772679145; release workflow 39772679160 (publishing job skipped; validation-only job passed).
- Reviewed UI stack PRs #531–#535. Main findings: all five are stacked on branches rather than `main`, starting from closed stale PR #529; required workflows filter pull requests to `main`, so there were no CI runs on their original head SHAs. Manual browser checks required by `docs/LOCAL_UI_TESTING.md` have not been performed. Do not merge these original PR heads until the stack is rebased/reconciled and final-head CI plus browser checks are complete.
- To exercise the cumulative UI changes against current `main` without altering original PR branches, created temporary validation-only commits by overlaying the changed-file state through each PR onto current main, then closed the temporary validation PRs after testing. These commits are integration test candidates, not the original PR heads:
  - Through #531: `53026bcbff794c04b6f901aefeb4fa939403cd7e`; all four workflows passed (syntax 39779026542; full suite/build 39779026314; smoke 39779026388; non-publishing multi-arch 39779026309; release validation 39779026400).
  - Through #532: `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a`; all four passed (syntax 39779175672; full suite/build 39779175738; smoke 39779175835; non-publishing multi-arch 39779175783; release validation 39779175705).
  - Through #533: `da4a3e72146ec60c8c0c700f4ed5f387bf864723`; all four passed (syntax 39779276986; full suite/build 39779276674; smoke 39779276863; non-publishing multi-arch 39779276675; release validation 39779276967).
  - Through #534: `d319d8c5cc5f661a834035dabf99a26a1431655a`; all four passed (syntax 39779388308; full suite/build 39779388280; smoke 39779388596; non-publishing multi-arch 39779388383; release validation 39779388204).
  - Through #535: `1d803c6f1daf198d3c77741cbbb5c51eb5c490e0`; all four passed (syntax 39779671933; full suite/build 39779672016; smoke 39779672162; non-publishing multi-arch 39779671942; release validation 39779672201).
- Release workflow publishing jobs were skipped; validation-only multi-architecture builds passed. No image was published, no deployment occurred, and no manual browser or live-runtime verification is claimed. The local checkout attempt failed because the environment could not resolve github.com; full-suite evidence above comes from GitHub Actions.
- No product PR was merged. Next action: review/merge #530 if desired, then reconcile #531–#535 onto current main and run required checks on the actual final PR heads plus manual browser checks.

## 2026-10-22 — PR #529 reconciled; full CI suite passed on replacement PR #530

- Closed stale PR #529 because its branch predated the current `main` and its `discovery/list_payload.py` version omitted PR #528's cached future-release filter. Replacement PR #530 is based on current `main` and retains both behaviors.
- Exact tested PR #530 head: `34b926249a6e71aeab4e2243500fa91eb47e226b`; compare reported 3 commits ahead, 0 behind at review time. Changed files: `discovery/list_payload.py`, `navidrome_server.py`, `tests/test_discovery_list_payload.py`.
- Regression coverage hides imported acquisition identities across lists, excludes library-owned items from non-personal lists, preserves the future-date filter, and keeps imported items hidden when the library snapshot fails.
- Exact-head CI: Python syntax/acquisition safety run 39772357314 passed; Docker packaging/full unit suite/image build run 39772357012 passed (the full unit-test step succeeded); container runtime smoke run 39772356995 passed; validation-only multi-architecture image run 39772356972 passed. Release workflow run 39772357053 skipped the publishing job; its validation-only build completed successfully. No image was published.
- PR #530 remains open and unmerged. No manual browser or live-library/runtime check was performed; not published or deployed. Next action: review final PR state and merge #530 if all gates remain green, then continue live-runtime verification of #526/#527.

## 2026-10-22 — PR #528 merged: hide future-dated New Releases

- Squash merge commit on `main`: `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750`; exact tested PR head: `295148dcf817479f4098195200ada4c4173733fe`.
- Candidate selection now excludes release groups dated after today, including partial dates using their earliest possible day. Cached New Releases responses also hide stored future-dated items, so stale cached lists are corrected on read.
- Regression coverage: `tests/test_discovery_new_releases.py` and `tests/test_discovery_list_payload.py`; PR report records 46 focused tests passing and `py_compile` on `navidrome_server.py`.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety run 39770936745; Docker packaging/full unit suite/build 39770936858 (unit tests and image build passed); container runtime smoke 39770936556; validation-only multi-architecture image validation 39770936564. The release workflow's publishing job was skipped; its validation job passed.
- Full unit suite was run by CI on the exact PR head, not separately in the agent environment. No manual browser check or live-library verification was performed. Not published, deployed, or runtime-verified.
- Removed the resolved future-release bug from `docs/ACTIVE_WORK.md`; `docs/PROJECT_STATUS.md` records the merge. Next action remains live-runtime verification of PRs #526 and #527.

## 2026-10-22 — Exclusive “the owner” reference convention

- Added a permanent rule requiring all repository documentation, source comments, commit/PR text, reviews, issues, and other project communications to refer to the person directing the project exclusively as “the owner”; personal names and account usernames/handles must not be used for that person.
- Recorded the rule in `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, and `handoff.md`. Documentation-only changes committed directly to `main` as required. No application code changed; no application tests or CI were run.

## 2026-10-22 — Wildcard-masked artist queries for blocked slskd searches (PR #527 merged)

- PR #527 squash-merged as `e03f4b3` from head `8f51626677473aa069c81e34eaa9007f18cd6623`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Why: slskd blocks some artist names (e.g. "Gorillaz Plastic Beach" returns zero) although the music is on the network; replacing a first letter with `*` ("*orillaz Plastic Beach") bypasses it.
- Change: `integrations/slskd/search.py` adds `masked_artist_variants()`; `search_queries()` inserts the first-word-masked and every-word-masked artist queries right after the unmasked one, before the existing punctuation/parenthetical fallbacks. Words under 3 characters are not masked. No change to `search_polling.py`, candidate extraction or diagnostics.
- Tests: new cases in `tests/test_slskd_search.py` (single word, multi-word, short words); old query-list expectations updated in `test_slskd_search`, `test_slskd_search_modules` and `test_slskd_search_polling` (the latter two were missed on the first head and failed CI). Focused run of five slskd/acquisition modules with `.venv`: 32 OK. Live slskd behavior not verified.

## 2026-10-22 — Failed-track retry in the acquisition watcher (PR #526 merged)

- PR #526 squash-merged as `4fcd5ff78dc7cfebe99d289a49cd8505c6ca9138` from head `360e84287c01622fc19ba844954f55594a218ea9`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Bug: one errored slskd track stopped byte progress, so the watcher ended in `download_failed` or, after 120s, switched to a fallback source and re-downloaded the whole album. `acquisition/watcher.py` now re-queues failed tracks alone from the same source (3 tries, 30s apart) through the injected `queue_files` service, suppresses the stall switch meanwhile, keeps watching 15 minutes before `download_failed` so a manual slskd retry can recover, and ranks completed > live > failed records per file. Without `queue_files` the old immediate-failure behavior is kept.
- Tests: three regression tests in `tests/test_acquisition_watcher.py`; focused run only (13 OK). Not verified against a live slskd; real failure state strings are assumed (`Errored`, `Failed`, `Cancelled`, `TimedOut`, including slskd's `Completed, Errored` form).

## 2026-10-21 — Discovery package PR 4: gathering core (PR #524 merged); layout roadmap complete

- PR #524 squash-merged as `a5b14191c02007db376b0642ecceeef0426bdbd5` from head `69c9359e80aa4ff192a073f69b39bf6ffcdc02f1`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `candidate_gathering`, `batch_metadata`, `lb_tag_lane`, `tag_queries`, `library_snapshot`, `recommendations` into `discovery/`; `mock.patch` string targets rewritten. Root Python modules 9. Focused tests and `py_compile` only.

## 2026-10-21 — Discovery package PR 3: store, refresh and cooldown (PR #523 merged)

- PR #523 squash-merged as `04c0798ea528e53ce5485ea0410b4620b00b3098` from head `279eeee39559dd469238c60be84faef95e8fdbe4`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `store`, `snapshot`, `refresh`, `list_payload`, `candidate_supply` and `recommendation_cooldown` (as `discovery/cooldown.py`) into `discovery/`; root Python modules 15. `navidrome_server.py` keeps the `discovery_store` and `discovery_refresh` names via `from discovery import ... as`. Focused tests and `py_compile` only.

## 2026-10-21 — Discovery package PR 2: allocator (PR #522 merged)

- PR #522 squash-merged as `bcd34c956e177ae43fcb895cb79dbfb095ec6463` from head `d989557adb9d78f83cfc73bb50b212faef4ad984`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `allocation_contract`, `personal_allocator`, `mmr` into `discovery/`; root Python modules 21. Focused tests and `py_compile` only (104 tests OK locally).

## 2026-10-21 — Discovery package PR 1: leaf cluster (PR #521 merged)

- PR #521 squash-merged as `7fbea3a22d65cb5e3406981803392e91b7c15288` from head `2cf623a6ad24e4a8014eef9f4dae3ec8e7960d1d`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.

- Moved `classics_candidates`, `classics_genres`, `classics_ratings`, `deep_dive_candidates`, `new_releases`, `recommendation_payload` from `discovery_*.py` into the new `discovery/` package (no re-export shims; the only callers were `navidrome_server.py` and five test modules, all updated). Dockerfile gains `discovery/ ./discovery/` and drops the six root names. Root Python modules 24. Packaging test `test_discovery_leaf_modules_live_in_discovery_package` added.
- Local: `py_compile`, `scripts/check_server_size.py` and the focused modules (`test_docker_packaging` plus the five moved-module tests) pass except 4 `test_discovery_new_releases` provider tests that need `httpx`, which the local python3 lacks (same 4 errors on clean `main`). Full suite not run. CI, merge, publish and deploy not done.

## 2026-10-21 — Acquisition PR 3 merged (PR #519); music_key inversion (PR #520 merged)

- PR #519 squash-merged as `6e12466` after compile, test-and-build, container-smoke and validate-container passed on head `c2f584b4f09e9e264268fb644f7f4b4900a7a27f`. Not published or deployed.
- PR #520 squash-merged as `b5e0622043737c89ccd4d4bfacb9881c366594f9` from head `886fb03c3a354738b1b51ced393783fe1aac80d5`; four checks passed; not published or deployed.
- `music_key` moved to stdlib-only `recommendation/music_key.py`; `integrations/lastfm/client.py`, `recommendation_feedback.py` and `recommendation/profile_comparison.py` import it from there. `discovery_recommendations` re-exports the same function (other callers and tests use it). `tests/test_music_key.py` proves output identical to the previous implementation. Behavior unchanged; focused tests only; `httpx` missing locally so the Last.fm client was checked by AST, not import.

## 2026-10-21 — Acquisition package PR 3 (open, not merged)

- Moved the five import/cleanup modules into `acquisition/`: `completion`, `import_files` (was `acquisition_import`; `import` is a Python keyword, so `acquisition/import.py` is not importable), `import_service`, `cleanup`, `recovery`. Callers, tests, Dockerfile COPY line and the `python-syntax.yml` compile entry updated; packaging test added. Behavior unchanged. Focused tests and `py_compile` only; the one failure is the known macOS `/var` case. Root Python modules 30. Not merged, published or deployed.

## 2026-10-21 — Acquisition package PR 2 (PR #518 merged)

- Moved five monitor modules into `acquisition/`; details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `32b23176e1c22317ad1ce662b8ca22cb8970409d` from head `29e7879beb162098cc612e27e4781e1ba40bf6e4`; four required checks passed. Not published or deployed.

## 2026-10-21 — Acquisition package PR 1 (PR #517 merged)

- Moved eight request/queue modules into `acquisition/`; owner approved this order and the `music_key` fix, and `recommendation_cooldown` moving with the store modules. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `2411740dc74d57b1a4fddbd33eeef80a461b40dd`, exact head `cd39e83ee7abe50378c015d4486b6306d4690270`, four required workflows passed. Root modules 40. Publication, deployment and runtime verification not performed. Next steps in `CLAUDE_CLI.md`.

## 2026-10-21 — Package layout design note (docs-only)

- Audited `main` `f84dfce` with an AST import graph plus grep. slskd: nothing left to move. `acquisition_*` (18): no outward dependencies, only `navidrome_server.py` calls them; proposed `acquisition/` in three PRs. `discovery_*` (20): six server-only leaves and the 3-module allocator are safe; store/refresh and the gathering core are blocked by the `integrations/lastfm` -> `discovery_recommendations.music_key` inversion (needs an owner decision). `navidrome_server` stays. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. No code changed, no tests run. Next: owner picks the first move (recommended: `acquisition/` PR 1).

## 2026-10-21 — Listening profile move (PR #516 merged)

- Moved `listening_profile` into `recommendation/listening_profile.py` (no shim). Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `adc66e88d522b0240ffc1c271643d7ba0a90e403`, exact head `462ffcb28456ff734522266c7f5fc4f8cae7ff93`, all four required workflows passed. Root modules 48. Next: design note for slskd leftovers, acquisition, discovery and the legacy server. See `CLAUDE_CLI.md`.


## 2026-10-21 — Settings package move (PR #515 merged)

- Moved `service_settings`, `settings_persistence`, `music_paths`, `data_directory` into `settings/` (no shims). Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only; Also archived `diagnose_categories.py` to `docs/archive/`; `read_only_command_policy` stays in root. Squash merge `766ffe487baa28f23f3880e42f6aa4689a9284ad`, exact head `1e5020dfcd7bd6551bf705588f9bb34f1b3c17d8`, all four required workflows passed. Root modules 49. Next: `listening_profile` -> `recommendation/`. See `CLAUDE_CLI.md`.
## 2026-10-21 — Recommendation replay/diagnostics package move (PR #514 merged)

- Moved `recommendation_replay`, `recommendation_diagnostics`, `recommendation_mmr_evaluate`, `recommendation_profile_comparison` into `recommendation/` (no shims). `replay._REPOSITORY_ROOT` adjusted to the repo root. Merge `431c152642809e2aad1a36a556ac47610d0ddaa2`, exact final head `b636fcf2298f27b76befc3285034fe03285a32a0`, four required workflows passed. Root Python modules 54. `run_metrics`, `cooldown`, `feedback` stay in root. Focused tests and `py_compile` run locally; full suite not run. Publishing, deployment and runtime verification not performed.
- Next task: audit settings/paths group. See `CLAUDE_CLI.md`.

## 2026-10-21 — ListenBrainz integration package move (PR #513 merged)

- Moved `listenbrainz_client.py` and `listenbrainz_popularity.py` into `integrations/listenbrainz/` with canonical imports, no shims. Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Merge `4e392e6660706191d080a5a2e9c66739377a5c33` from head `935d8984002bc6d690a2a6c09c315816dea9e16e` (owner named PR 513). Not published, deployed or runtime-verified.

## 2026-10-21 — PR #512 merged: Last.fm integration package

- Squash merge commit on `main`: `7282cbb740dba6e27fa79aecfe0de5519c18d859`; exact final PR head `84b4f04b27025f35d1f8f353b152a78ee886ef59`, all four required workflows passed on it (syntax 39653199481, Docker packaging/full unit suite/build 39653199482, container smoke 39653199327, validation-only multi-architecture 39653199280). Merged on the owner's instruction naming PR 512.
- Owner rules added to `CLAUDE_CLI.md` (2026-10-21): agents never run the full test suite; documentation-only updates are pushed directly to `main`.
- Main also contains owner-merged PR #506 (`8e29044`, tag-triggered release workflow); out of scope here. Publishing, deployment and production-runtime verification remain unperformed.
- Next task: audit the ListenBrainz modules as their own boundary. See `CLAUDE_CLI.md`.

## Last.fm integration package move details (before merge)

- Base: `main` `13790f8` (all four workflows green on it). Moved `lastfm_client.py` to `integrations/lastfm/client.py` (new `integrations/lastfm/__init__.py`); `navidrome_server.py` now imports the canonical module and keeps its `_lastfm_*` adapters unchanged. No root shim: AST/grep audit found exactly one production importer (`navidrome_server.py`) and one direct test module (`tests/test_lastfm_client.py`, switched to the canonical path); no dynamic/string imports, no `__file__` or path assumptions, no workflow or script references besides the syntax compile list.
- Dependencies: the client imports `recommendation_run_metrics` and `discovery_recommendations.music_key` from the root. Both are stdlib-only leaf modules (no cycle) and resolve from `/app` in the image. `music_key` is only the default for the injectable `key_normalizer`; left as is to keep behavior unchanged. Decoupling it is a possible later cleanup, not part of this move.
- ListenBrainz modules (`listenbrainz_client`, `listenbrainz_popularity`) were inspected separately and not moved: three production call sites across `navidrome_server.py` and `discovery_candidate_gathering.py`, plus lazy imports, so they need their own audit.
- Docker: root `COPY` list drops `lastfm_client.py`; `integrations/` is already copied. Added a packaging regression test. Root-level Python modules: 61 to 60.
- Agent-side checks (macOS, venv from `requirements.txt`): `py_compile` on changed Python files; focused `tests.test_lastfm_client`, `tests.test_docker_packaging`, `tests.test_lastfm_recommendation_scoring` (26 tests OK); `scripts/check_server_size.py` OK. Full suite not run. CI on code head `76e5979d` (before this docs-only evidence commit): syntax [39652945862](https://github.com/abucalip/navi-librarian/actions/runs/39652945862), Docker packaging/full unit suite/build [39652945820](https://github.com/abucalip/navi-librarian/actions/runs/39652945820), container smoke [39652945713](https://github.com/abucalip/navi-librarian/actions/runs/39652945713), validation-only multi-architecture [39652945728](https://github.com/abucalip/navi-librarian/actions/runs/39652945728): all passed. PR is #512; the final head after this commit is re-verified in the PR checks.
- Not merged, published, deployed, or runtime-verified.

## 2026-10-21 — PR #511 merged: slskd integration package

- Squash merge commit on `main`: `84fbb68afa7929a0bedae4e178d37ad2b6255c5a`; exact final PR head: `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`.
- Moved `slskd_client.py`, `slskd_quality.py`, `slskd_search.py`, `slskd_search_polling.py`, and `slskd_transfers.py` to `integrations/slskd/{client,quality,search,search_polling,transfers}.py`. Updated production imports in `navidrome_server.py`, preserving its adapters; updated direct-import tests, Docker packaging regression coverage, and the syntax workflow compile list. No old root-level shims were retained because the caller audit found no remaining direct imports requiring them.
- Root-level Python module count: 61 after the move, down from 66 before it.
- Four required workflows passed on exact PR head `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`: syntax/acquisition safety [39649756998](https://github.com/abucalip/navi-librarian/actions/runs/39649756998); Docker packaging/full unit suite/build [39649757098](https://github.com/abucalip/navi-librarian/actions/runs/39649757098); container runtime smoke [39649756971](https://github.com/abucalip/navi-librarian/actions/runs/39649756971); validation-only multi-architecture image [39649757030](https://github.com/abucalip/navi-librarian/actions/runs/39649757030).
- The Docker packaging workflow's full unit suite passed. Agent-side focused tests and `py_compile` were not run because no fresh isolated checkout was available. Do not infer tests on the merge commit beyond the verified PR-head evidence.
- Published, deployed, and production-runtime verified: no. Publishing/deployment remain paused.
- Next task: refresh the dependency map on post-merge `main` and audit `lastfm_client.py` plus its callers, direct tests, dynamic imports, path assumptions, and Docker/CI references before deciding whether to move it to `integrations/lastfm/`. See `CLAUDE_CLI.md`.

## 2026-10-21 — Python package-layout PR #509 merged

- Squash merge commit on `main`: `8fe825a41c0122bd3fd6d3260ca8978cdbf0d27f`; tested PR head `c045865fea13e8944512fc5c987e609cbc41e443`.
- Moved the canonical MusicBrainz album-year and rating helpers into `integrations/musicbrainz/`; retained `musicbrainz_rating_client.py` as a compatibility shim for the legacy server; updated the album-year caller, focused tests, and Docker COPY list.
- Four required workflows passed on the exact PR head: syntax 39646429894, Docker packaging/full unit suite/build 39646429876, container smoke 39646429872, and non-publishing multi-architecture image validation 39646429885. Agent-side focused tests and `py_compile` were not run because a fresh checkout was unavailable.
- Root-level Python module count decreased from 67 to 66. Publishing/deployment remain paused; no release or production runtime verification was performed.
- Next action: audit the five `slskd_*` modules and all callers/tests before deciding whether a cohesive package move is safe; see `CLAUDE_CLI.md`.

## 2026-10-21 — v0.2 release preparation (PR #505)

- PR #505 merged by squash as `99c0b88ed885de8b3c36686d63736b19a9235392`, exact PR head `fb34440b4893cc7f65678c90ba6e333616c0479d`. Added `docs/RELEASE_v0.2.md`: draft user-facing notes, configuration migration cautions, and a release/deployment checklist. No application code changed.
- All four required workflows passed on exact merge SHA `99c0b88ed885de8b3c36686d63736b19a9235392`: Python syntax `39634236552`; Docker packaging/full unit suite/build `39634236630`; container runtime smoke `39634236733`; validation-only multi-architecture image validation `39634236750` (`push: false`).
- Modularization roadmap is closed. No GitHub Release was present at preparation time; an existing tag was not confirmed. The current workflow remains validation-only; no tag, release, image publication, deployment, or runtime verification was performed.
- Release state is prepared, not released. The release notes disclose that the PR #503/#504 Settings browser checks were waived. After this closeout commit, the exact final main SHA still needs all four required workflows checked before tagging. A deliberate publishing workflow path and explicit authorization are still required before publication/deployment.

## 2026-10-21 — PRs #504 and #503 merged

- **PR #504 — neutral LAN defaults:** squash merge `af78c9e9796c27c65f9503a64d61ca9c58357dba`; exact tested PR head `4263f9c5bf3400cf6a5846c0f81a253a177e9543`. Removes the private LAN IP default and uses neutral placeholders/docs; blank slskd URLs fail validation. All four required workflows passed on the exact head: Python syntax `39631742346`, Docker packaging/full unit suite/build `39631742366`, runtime smoke `39631742152`, and validation-only multi-architecture validation `39631742470`.
- **PR #503 — ListenBrainz token setting:** reconciled after #504, then squash merged as `c3d5e02a4e5f113bb2914b12986cdef41e5863b5` from exact final PR head `cd0d53cb9f962b361f7ea84abba12b32b7efb17a`. Reconciliation commits `f1b136669dc790842d86aa9e16a56abd28fc5aee` and `cd0d53cb9f962b361f7ea84abba12b32b7efb17a` carried the token API/service changes onto current main while preserving #504's blank-URL validation. Token is optional, validated against `[A-Za-z0-9_-]{1,200}`, stored in the existing settings DB, never returned by the API, and not sent to MusicBrainz; blank input preserves a saved token and the environment fallback remains. All four required workflows passed on the exact final head: Python syntax `39632632729`, Docker packaging/full unit suite/build `39632632823`, runtime smoke `39632632791`, and validation-only multi-architecture validation `39632633039`.
- The Docker packaging workflow ran the full unit suite for each tested head. No separate agent-side full-suite run was performed (standing workflow rule). Manual UI checks were waived by the owner and not performed. Publishing remains paused; no image publication, deployment, or production-runtime verification is claimed.

## 2026-10-21 — P1a deeper CF pool measured (PR #502, docs only)

- Owner waived P0h and approved one cold plus one warm run for `CF_MAX_PAGES` 4 vs 6 (test-only harness, not committed, fresh data dirs, slskd off, aggregate only).
- 4 pages: cold 25.2 s, warm 5.1 s, 117 candidate albums / 85 artists, 0 uncached recording lookups. 6 pages: cold 183.6 s (2 ListenBrainz 429s, batch fallback, 100 lookups, 47 albums), warm 10.0 s (162 albums / 109 artists). Final list 10 in all runs; overlap 4 of 10.
- Decision: keep `CF_MAX_PAGES = 4`. Single samples, order effect not excluded. No code change. PR #502 merged by squash as `6e0718699740ce96539321e6b82ce15c0f632c06` from exact final PR head `ba29be2429484620415232db91ef97471470826a`.

## 2026-10-21 — PRs #500 and #501 merged

- **PR #500** (`ui/deepdive-save-render-check`) merged by squash as `e911a26b87cf8d9c11bb2502d8f1c074190b7a4c`, from exact final head `97e0bbbffbf3efb7c47860d980e49b023323bd0c`. Docs-only rendered verification record: Playwright/Chromium observed four 44 px Save controls, unobstructed hit targets, `save`/`remove_for_me` behavior without acquire or list reload, retry state on HTTP 500, and no overflow at 375 px. Screen-reader/live-data checks not done. All four required workflows passed on exact head: Python syntax/acquisition safety `39622877712`, Docker packaging `39622877775`, runtime smoke `39622877823`, validation-only multi-architecture image `39622877814` (publishing paused).
- **PR #501** (`ui/saved-page`) merged by squash as `990c83d3c0fdee816d7b511a7c6bd347bc715532`, from exact final head `10d0defec37479606ebb9bca143a21eb9d5cfd7c`. Adds the Saved page to the header menu, reading existing `/api/discovery/for_me`; supports refresh/revisit, saved dates, owned-album indication, remove/undo, loading/empty/error states, and hides Get for owned albums. Also removes the footer copy per owner request. PR report says 5 focused UI-contract tests and all UI-contract modules passed, `node --check static/app.js` passed, and Playwright/Chromium checks covered menu/navigation, rows, save/remove without acquisition/reload, refresh/revisit, empty/failure states, and 375 px layout. Live Navidrome data and screen-reader checks not done. All four required workflows passed on exact head: Python syntax `39626079394`, Docker packaging/full unit suite/build `39626079244`, runtime smoke `39626079346`, validation-only multi-architecture image `39626079497` (publishing paused).
- Publishing, deployment, and production-runtime verification remain unperformed. Exact PR heads were CI-verified before merge; no separate local full-suite run was performed.

## 2026-10-21 — PR #499 merged: P0i stale-flag audit (documentation only)

- PR #499 (`docs/p0i-stale-flag-audit`) merged by squash from exact final head `b5404cfcb80f65d36d61f309bb8c90b54d40b091`; merge commit `90d127eb46b0528a12ea0255ba81f25e1617ac4a`.
- Updated active status wording to reflect the current genre circuit-breaker and batch/title-filter defaults after PRs #495–#498. Corrected the tag-lane early-stop test docstring. No application code or defaults changed; dated historical experiment records were retained.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `39621883615`; Docker packaging/full unit suite/build `39621883770` (`test-and-build`, unit tests and image build succeeded); container runtime smoke `39621883534`; validation-only multi-architecture image validation `39621883758` (non-publishing).
- No separate local full-suite run (owner rule); CI ran the full suite. Publishing, deployment, and production-runtime verification remain unperformed.
- Next action: continue the active recommendation-engine roadmap from its top item; do not infer recommendation-quality or stable performance improvements from single samples.

## 2026-10-21 — Handoff: next task P0i (stale-flag audit, read-only then docs PR) (docs only)

- Pushed straight to `main` at the owner's instruction. `CLAUDE_CLI.md` hands off P0i: audit docs and comments against the post-#495 to #498 code defaults (known suspect: `docs/PROJECT_STATUS.md` still says the batch/breaker PRs are off by default), fix contradictions in a docs PR, no code or default changes, no network. P0h stays parked until ListenBrainz recomputes CF. No tests run (docs only).


## 2026-10-21 — Python package layout, first slice (PR #508 open)

- Branch: `refactor/package-navidrome-client`, based on main `86ad8de2bc1f08b86c4821969e017c15c3ef97bd`. PR: https://github.com/abucalip/navi-librarian/pull/508.
- Moved the Navidrome client implementation to `integrations/navidrome/client.py`, added package initializers, updated production imports, retained `navidrome_client.py` as a compatibility shim, updated direct-import tests, and added the package to Docker COPY.
- Regression coverage added for identity of the legacy re-export and canonical callable. Agent-side focused tests and `py_compile` were not run: the execution environment could not resolve github.com for a fresh checkout. No stale local checkout was used.
- All four required workflows passed on exact head `cffb5486d6fedb091979e397ff545a22fd0502cf`: Python syntax/acquisition safety `39639446692`; Docker packaging/full unit suite/build `39639446681` (unit tests and image build succeeded); container runtime smoke `39639446683`; validation-only multi-architecture image validation `39639446720` (non-publishing). This documentation closeout advances the PR head, so the four workflows must be checked again on the new exact head. Not merged, published, deployed, or runtime-verified.


## 2026-10-21 — Python package-layout first move merged (PR #508)

- Squash merge: `f171a4e73915222292642ba17d6dcb568b8c929a`; exact tested PR head: `a6fe1bd656f77ae4fbd65cb94c067949d14cf140`.
- Moved the Navidrome/Subsonic client implementation to `integrations/navidrome/client.py`; added package initializers, switched production imports, retained and tested `navidrome_client.py` as a compatibility shim, updated direct-import tests, and added `integrations/` to Docker packaging. ASGI entry point unchanged.
- Required CI passed on exact PR head: syntax/acquisition safety run 39639612889; Docker packaging/full unit suite/build 39639612870; container runtime smoke 39639612822; non-publishing multi-architecture validation 39639612866.
- Agent-side focused tests and `py_compile` not run because the execution environment could not obtain a fresh GitHub checkout. No stale local checkout used. No publishing, deployment, or production runtime verification.
- Next: regenerate/review the dependency map against post-merge main, finish the remaining module/caller/path/test inventory, and choose the next cohesive move only after checking dynamic imports, compatibility, and Docker assumptions.


## 2026-10-21 — slskd integration package move opened as PR #511

- Code commit: `2530192b703cdc023406ad8415008a5aa37fcbd5`, based on current main `ea4d50e2384617ba365d11b93f5f4f789af6e019`. Moved the five slskd modules into `integrations/slskd/`, updated lazy/top-level legacy-server imports and direct-import test paths, removed the root module copies, added a Docker package-presence regression test, and updated the syntax workflow compile list.
- Refreshed dependency-map artifact ID `12368421891` from the audit workflow confirms independent module imports; exact artifact SHA-256 is `22440f9cabed53f77f21abbdeb0593a9553fbdcc5bc0791d0ff46498d5185ca5`. The artifact source SHA is audit head `8ba095c17040ea5dd40ab19ad36e132acb4ab2ee`, whose application source matches the main baseline.
- All four required workflows passed on code head `664639724ef9d1cbf5edd1603a41ccb14a372ce3`: syntax/acquisition safety `39649449299`, Docker packaging/full unit suite/build `39649449147`, container smoke `39649449405`, and validation-only multi-architecture `39649449373`. A docs-only follow-up changes the PR head, so exact-final-head CI must be rechecked. Agent-side focused tests and `py_compile` were not run due lack of a fresh checkout. Not merged; publishing/deployment/runtime verification not performed.


## 2026-10-22 — Documentation consolidation and redesign archive

- Documentation-only commits on `main`: `96e2c0d445e6b63523700dbb209849fef69ab14a` (archive and active-doc rewrite) and `04d5be51aa6d54e17499517a31ad731c09c6771a` (remove stale redesign/modularization references). This log closeout is a follow-up commit.
- Created `docs/ACTIVE_WORK.md` as the short current task queue; reduced `CLAUDE_CLI.md` to a pointer; shortened `docs/PROJECT_STATUS.md` to a current snapshot; reduced `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` to remaining gates; moved permanent process and UI safety/accessibility rules into `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`.
- Archived redesign-specific files, including root `AGENTS.md`, `DESIGN.md`, the Impeccable surface brief, design system, front-end guide, roadmap, UI backlog, and status-icon task notes. Archived completed modularization/package-layout/MCP-retirement plans, historical recommendation research, parked diversity/backlog proposals, CF/repeat-rate reports, and v0.2 release preparation under `docs/archive/`. Original file blobs were preserved.
- Updated `PRODUCT.md`, `docs/ARCHITECTURE.md`, and `docs/TEST_PLAN.md` to remove stale references to active redesign and modularization roadmaps.
- Closed superseded documentation PRs [#358](https://github.com/abucalip/navi-librarian/pull/358) and [#368](https://github.com/abucalip/navi-librarian/pull/368) with explanatory comments; their proposed status corrections are retained in the archive.
- Verification: re-read the resulting GitHub tree and active work/handoff/workflow files; confirmed archived files exist at their new paths and active handoff no longer points to redesign roadmaps. No automated link checker or application tests were run because this was documentation-only. No CI, publication, deployment, or runtime verification is claimed.
- Next action remains live-runtime verification of merged PRs #526 and #527; see `docs/ACTIVE_WORK.md`. Image publication/deployment remain paused.


## 2026-10-22 — Rename agent entry point

- Renamed the root `CLAUDE_CLI.md` handoff pointer to `handoff.md` in two documentation-only commits: `c2df9e820fff4ee3610eeb88988af51c0706a8ca` (add new path) and `b931899cca0b02cf27fb728865ce6d62b17a3fc0` (remove old path). The handoff content is unchanged; current queue and permanent rules remain in `docs/ACTIVE_WORK.md` and `docs/DEVELOPMENT_WORKFLOW.md`.
- No application tests or CI run; this was a documentation-only rename. No publication, deployment, or runtime verification performed.


## 2026-10-22 — Full test suite requires owner approval

- Updated `docs/TEST_PLAN.md` to state that manually running `python -m unittest discover -s tests -v` requires explicit owner approval. Without approval, agents run focused tests only; CI's `test-and-build` workflow continues to run the full suite on the PR head. Updated the stale handoff reference to `handoff.md`.
- Documentation-only commit: `841c8b2d912eac7032473558601bd7ec7ee87138`. No tests or CI run for this documentation-only change; no publication, deployment, or runtime verification performed.

## 2026-10-22 — Reconcile and merge PR #562

- Reconciled stacked branch `taste-families-server-labels` with the then-current `main` after PR #561 merged, preserving the PR branch as a parent and avoiding a force-push. Final tested PR head: `76142e1d0f2d48b59a1355e36c7372c4ed6f7123`.
- Reviewed the final diff: server API adds `genre_row` and `genre_row_label`; the UI consumes those fields rather than maintaining duplicate classification rules. The fallback behavior change for a small set of tags is described in the PR.
- Required workflows on the exact final head all passed: Python syntax (`39860454090`), Docker packaging/full unit suite (`39860454167`), container runtime smoke (`39860454213`), and validation-only Docker image validation (`39860454082`). Release-workflow validation (`39860454120`) passed; the publishing job was skipped. Manual browser verification was explicitly waived by the owner and was not performed.
- PR #562 squash-merged as `650a72718bfcd40a63ce67c5f869e71fd3a18d85`. Documentation closeout commit: `82f9be0c41455c035a1abf729d7a290483e1fdce`. No image publication, deployment, or live-runtime verification.



## 2026-10-23 — Review, test, and merge PR #574

- Re-reviewed the reconciled PR head `cc23a8005e554713f31eb0ab8594d2efa70b8d1e`. The cache correction now reads misses with the 7-day TTL first and only falls back to the 30-day TTL for positive values; Last.fm error 6 is treated as definitive not-found, while other errors, non-200 responses, malformed payloads, and exceptions remain uncached. Regression tests cover miss expiry, positive-value expiry, and transient failures.
- All four required workflows passed on that exact PR head: Python syntax/acquisition safety (`39954186109`), Docker packaging/full unit suite/image build (`39954186084`), container runtime smoke (`39954186218`), and validation-only multi-architecture image validation (`39954186167`, publishing paused). The full unit suite therefore ran in CI on the exact reviewed revision; no separate local full-suite run was performed.
- Squash-merged PR #574 as `eb4cb16ec5b932b4dc21a8978149f200931b1334`. The module remains unwired into runtime recommendation paths. No publication, deployment, or runtime behavior verification was performed.
- Review caveat: cache and provider behavior is covered offline with stubs; live provider behavior was measured in the prior capture but not re-run as part of this PR review.

## 2026-10-22 — Close approved runtime verification tasks

- The owner confirmed that failed-track retry/recovery and masked slskd artist-query behavior have been tested and approved. These are removed from the active work queue; no further verification task remains for those behaviors.
- Updated `docs/ACTIVE_WORK.md` in `22c54d99e118eb89ba9fff143c26419b78fbf8b6` and `docs/PROJECT_STATUS.md` in `6157b273155264db880dbecc78b53239465e29c5` to reflect the confirmation and remove stale outstanding-verification references.
- The v0.2.2 image remains published and not deployed. Approval of the behavior tests does not itself authorize deployment.
- Next eligible repository task: begin the behavior-preserving taste-family vocabulary consolidation described in `docs/HARDCODE_REPLACEMENT.md`; document current mapping differences and do not change canonical behavior without the owner's decision.


## 2026-10-22 — Merge PR #563 and review PR #564

- PR #563 externalized the existing taste-family defaults to `settings/taste_defaults.json`; squash-merged as `9a659f6e9da175e475aa22f86c69492f40206869` from exact PR head `0de6a16c6058c053f0948c6b46c74f50092b7bf9`. All four required workflows passed on that head: Python syntax `39861151203`, Docker packaging/full unit suite/build `39861151000`, container runtime smoke `39861150857`, and validation-only multi-architecture image validation `39861150831`. The Docker packaging workflow's full unit suite passed on the exact head. No publication or deployment.
- Retargeted PR #564 to `main` after #563 merged. Review of head `9cae06937a4dc65e9a3f12be484f008a0a49d839` found that sparse-history fallback returns fixed core/exploration sets but retains `profile_mode="derived"`, so fixed-mode classification exceptions remain disabled. Posted a review comment requesting an effective-mode fix and regression coverage. GitHub rejected a formal REQUEST_CHANGES review because the PR was authored by the connected account; the finding was posted as a COMMENT review instead.
- No workflow runs are visible for PR #564's current head after retargeting, so the requested full suite and four required CI workflows are **not verified** on that head. The repository workflow says agents do not run the full suite manually; it must run in CI. PR #564 remains open and unmerged. Derived mode remains off by default; multi-profile replay evidence and owner approval are still required before enabling it.
- No manual UI checks, publication, deployment, or runtime verification were performed.


## 2026-10-22 — PR #564 merged: opt-in derived taste profile

- PR #564 squash-merged to `main` as `508269f1177e35075330c903775f74e23c2f14af`, from exact tested PR head `6c08e385dccb21a28dd3b1e54531cb554ef26db8`.
- The sparse-history fallback issue was corrected: when derived profiling falls back to shipped defaults, the effective mode is now `fixed`, preserving fixed adventurous-tag and regional artist fallback behavior. Regression coverage checks effective mode, classification, and exploration bonus.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `39862938840`; Docker packaging, full unit suite and image build `39862938736`; container runtime smoke `39862938685`; validation-only multi-architecture image build `39862938695` (`push: false`). The full unit-test and Docker-build steps succeeded. These runs are associated with the PR head, not the squash merge commit.
- The stacked branch's review diff included already-merged #563 changes, but comparison of the squash merge commit against pre-merge `main` shows only the seven derived-profile files changed; #563 defaults are not duplicated in the net merge diff. No separate branch reconciliation commit was created before merge.
- Derived mode remains off by default. Multi-profile replay evidence is not supplied and enabling the mode requires a separate owner decision. No image publication, deployment, or runtime verification was performed.


## 2026-10-23 — Re-review, full CI suite, and merge PR #578

- Re-reviewed final PR head `f15dbde3fe78ddb4974178b84f863de85de0fd69`. The earlier album-identity correction uses normalized `album_key` for album overlap, union, and reference overlap; the latest fix calculates `total_picks` from selected candidate IDs rather than unique album keys. Regression coverage includes duplicate album identity within one list and across lists/reference.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40007720479`), Docker packaging/full unit suite/image build (`40007720478`; unit tests and image build succeeded), container runtime smoke (`40007720476`), and validation-only multi-architecture image validation (`40007720523`; publishing paused). The full unit suite ran in CI; no separate local run was performed.
- Squash-merged PR #578 as `3aebacbd40d80386199e0e5cb9b1b0ca94ca430d`. The metrics are pure evaluation code, not wired into runtime; they describe list composition and do not measure listening quality. No image publication, deployment, or runtime verification.
- Phase 2 evaluation metrics are complete. Next action: Phase 3 time-range profiles and window-driven tag-lane seeds. Any live capture or provider-budget increase still requires owner approval.

## 2026-10-24 — PR #583: Engine 2 Phase 3 history profiles

- PR #583 squash-merged from exact reviewed head `e4635b5b06e7dc04c6c6a9c3613c6bef531f2a69` as merge commit `09a958dfb39411f5b31f4ca9a79899e27221e6ef`.
- Added pure, unwired helpers for repeated-track artist weights, dominant-tag selection, tag-filtered artists, listening bursts, newly heard artists, dormant artists, and ListenBrainz artist-MBID mapping fallback. No runtime wiring, publication, or deployment.
- All four required workflows passed on the exact PR head: syntax/acquisition safety (`40087423103`), Docker packaging/full unit suite/image build (`40087423092`), container runtime smoke (`40087423107`), and non-publishing multi-architecture image validation (`40087423108`). Focused tests were reported as 35 tests plus a filtered 551-test subset; not rerun locally. The PR notes one existing unrelated test-collection error in `tests/test_service_settings.py::test_listenbrainz_connection` when running locally; CI's full suite passed.
- Post-merge container smoke workflow is running; publishing/deployment and runtime verification are not complete.

## 2026-10-24 — Re-review and merge PR #584: repeated-tracks lens

- Re-reviewed final PR head `2e59968bf1e78abe37ea75a8c0ee80023eb400fd` against `main` `d5107bda20f400fe46914ec67ad492fc403a9b6e`. The earlier concern about colliding normalized tag style identifiers was addressed: `select_supplementary_tag_queries` assigns deterministic unique suffixes to distinct selected tags, with regressions for `raï`/`rai` and `hip hop`/`hip-hop` plus separate profile/exploration namespaces.
- The repeated-track seed builder uses cached artist tags and listening history only, applies the configurable play threshold and dominant-tag exclusion, and performs no I/O. `REPEATED_TRACKS` reuses the Deep cuts gates but is not in `DEFAULT_LENS_ORDER`; runtime recommendation paths and default partitions remain unchanged. The proposed gates are still pending owner approval, and no provider/live-album evaluation was performed for this lens.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety (`40089767320`), Docker packaging/full unit suite/image build (`40089767317`; `Run unit tests` and `Build Docker image` both succeeded), container runtime smoke (`40089767356`), and validation-only multi-architecture image validation (`40089767293`, non-publishing). No separate manual full-suite run was performed; repository workflow says CI runs the full suite and agents do not run it manually. No manual UI check was applicable.
- Squash-merged PR #584 as `82e06c6321107d3803761b65cab9a985bb686e42`. No publication, deployment, or runtime verification; image publication remains paused.
- Next action: owner decision on the proposed repeated-tracks lens gates before any runtime wiring; keep this lens unwired until that decision.


## 2026-10-24 — Re-review, full CI suite, and merge PR #585

- Re-reviewed the updated PR head `34ec1a962a809cac86f735dfcf32422dc92f8646`. The prior same-name artist concern is addressed by comparing MusicBrainz IDs when both candidate and library artist IDs are available, with a name fallback when either identity is unresolved. Regression tests cover distinct same-name MBIDs, shared library identity, missing IDs, unresolved same-name library records, and history-MBID matching. Known artists are rejected before consuming seed/artist slots. Repeated tracks accepts one tag while Deep cuts retains the two-tag minimum. No runtime wiring was added.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40092120752`), Docker packaging/full unit suite/image build (`40092120821`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40092120755`), and validation-only multi-architecture image validation (`40092120772`, non-publishing). CI ran the full unit suite on the exact reviewed head. No separate agent-run full suite was performed, per repository workflow rules.
- Squash-merged PR #585 as `2706dda68c594a6d683cd6c6bc00feb2d9869d00`. The new lens remains unwired; no provider calls, publication, deployment, or runtime verification were performed.
- Next action remains owner decision on the proposed Repeated tracks selection gates before any runtime wiring.


## 2026-10-24 — Re-review, full CI suite, and merge PR #586

- Re-reviewed PR #586 at exact head `3007590f0214c94b3694ad6a4ff8da089fb11f80`. The diff cleanly removes `Lens.min_tags`, restores Repeated tracks to the shared Deep cuts two-tag minimum, and updates the regression test to cover zero, one, and two tags for both lenses. The known-artist exclusion from PR #585 is untouched; the repeated-tracks lens remains outside `DEFAULT_LENS_ORDER`, so no runtime/default recommendation behavior changes.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40093298924`), Docker packaging/full unit suite/image build (`40093299008`; unit tests and image build succeeded), container runtime smoke (`40093299033`), and validation-only multi-architecture image validation (`40093299077`, non-publishing). CI ran the full unit suite on the exact reviewed head. No separate agent-run full suite was performed, per repository workflow rules.
- Squash-merged PR #586 as `f53a2cf2d3c1a1ce65703ded66c421ae2434d274`. No provider calls, publication, deployment, or runtime verification were performed.
- Next action: write the owner-approved Obsessions lens definition; separately explore another tag source or an exception for artists with no genre tags. Any new live run still requires owner approval.


## 2026-10-24 — Re-review, full CI suite, and merge PR #592

- Re-reviewed the updated PR head `09fb6e8d907d49fdefad4925a6b91c2e394abe5d`. Both findings from the previous review were fixed: `refresh_lens_lists` now calls the build/gate before ownership or storage access, and a non-gathered result reports `failed` rather than `disabled`. Regression tests assert the setting-off path touches no library, ListenBrainz, gatherer, or store, and that failed gathering preserves stored lists and reports failure. Diff review covered all five changed files; storage keys are namespaced as `lens:<name>`, read-time ownership filtering preserves ranks, and the replacement policy keeps previous usable lists when candidates are invalid/partial.
- All four required workflows passed on exact PR head `09fb6e8d907d49fdefad4925a6b91c2e394abe5d`: Python syntax (`40105619986`), Docker packaging/full unit suite/image build (`40105619974`, with `Run unit tests` and `Build Docker image` successful), container runtime smoke (`40105620007`), and validation-only multi-architecture image validation (`40105619975`, publishing paused). Release workflow `40105620017` succeeded with its publish job skipped. Per workflow policy, the full unit suite was run by CI, not manually by the agent.
- Squash-merged PR #592 as `0a8f9090fbb218f6508b33d9e72ebedbcdc64fd1`. Lens lists are now refresh/serve-wired but remain behind `engine2_lens_lists_enabled`, default off. No live provider run, publication, deployment, or runtime verification was performed.
- Next action: inspect the Phase 4 roadmap and define the next bounded slice before implementation.


## 2026-10-24 — Re-review, full CI suite, and merge PR #593

- Re-reviewed final PR head `1004251872937e3d6eef8cbcd2db033fbe5c0da3`. The previous blocker was fixed: `discovery.lens_service.list_response()` now checks `engine2_lens_lists_enabled` before reading the store or checking library ownership. Regression tests cover all three lens names through both the service and API route, asserting the disabled response without store/library access.
- All required checks passed on the exact final head: Python syntax (`40106383183`), Docker packaging/full unit suite/image build (`40106383162`, including successful `Run unit tests` and `Build Docker image` steps), container runtime smoke (`40106383137`), and validation-only multi-architecture image validation (`40106383191`). Release-workflow validation (`40106383120`) succeeded with publication skipped. Per repository workflow policy, the full unit suite ran in CI, not manually.
- Squash-merged PR #593 as `8ef9eb6e1f6e7099ae0369f0bd2471872fab816b` from exact reviewed head `1004251872937e3d6eef8cbcd2db033fbe5c0da3`. The lens service is now outside `navidrome_server.py`; lens lists remain gated by the default-off setting and are not wired into the recommendation path. No live provider run, image publication, deployment, or runtime verification was performed.
- Next action: define the bounded Phase 4 slice 4 (UI) scope before implementation.


## 2026-10-24 — Re-review, full CI suite, and merge PR #597

- Re-reviewed final PR head `017b4a81b7c5e8ba21d490584e2d2044cd3ef6b7`. The prior blocker was fixed: Last.fm API error payloads (including HTTP 200 errors) and unexpected response shapes now raise, allowing the window walk to fall back to ListenBrainz. Added regression tests cover API errors, malformed shape, valid empty history, single-track object responses, and fallback to ListenBrainz. The rest of the history-fetch tests cover pagination, source alternation, deduplication, floor/threshold behavior, and the page-cap diagnostic.
- All four required workflows passed on the exact PR head: Python syntax (`40113690376`), Docker packaging/full unit suite/image build (`40113690375`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40113690363`), and validation-only multi-architecture image validation (`40113690367`, publishing paused). CI ran the full unit suite on the exact head; no separate manual full-suite run was performed.
- Squash-merged PR #597 as `c653aab4526c450b84a2071bf8d0e0ea701891ed`. The actual starting threshold is 2000 usable listens, not the stale 500 mentioned in the PR description; the owner decision remains open. Discover's separate `recent_listens` paging bug remains tracked in PR #598. No publication, deployment, or runtime verification.


## 2026-10-24 — Re-review, full CI suite, and merge PR #598

- Re-reviewed exact PR head `96582e1a87d9908ed4ad1e23a68eb6d8d8fe5e3c`. The Discover `recent_listens` path no longer sends `min_ts` on every page, which returned the oldest page within the bound; it pages newest-first using `max_ts` and filters each page to the requested window. Regression coverage verifies request parameters and dropping out-of-window records.
- All four required workflows passed on that exact head: Docker packaging/full unit suite/image build (`40113450803`; unit tests and image build succeeded), container runtime smoke (`40113450800`), validation-only multi-architecture image validation (`40113450804`, publishing paused), and Python syntax/acquisition-safety/modularization checks (`40113450816`). CI ran the full unit suite on the exact head; no separate manual full-suite run was performed.
- Squash-merged PR #598 as `80e1ea2164ab4c3329a80d8c8947b88336bf5e4d`. Main was verified at that SHA after merge. No post-merge workflow run was visible at closeout; no publication, deployment, or runtime verification was performed. The PR description includes a live API check by the author; it was not independently repeated.

## 2026-10-24 — Review, full CI suite, and merge PR #602

- Reviewed exact PR head `7276e04a6fe7f1dde31496de46e7f5779be3da3c` across all five changed files. Request metadata (including the lens for Get requests) is passed to all three import-watcher success/uncertain paths; watcher startup persists it at initial acquisition state. Later status writes that omit metadata preserve the stored value, while a write with `metadata: {}` explicitly clears it to prevent stale lens attribution on a later personal-list request. Existing quality-summary preservation, candidate/settings retention, locking, reservation and file-handling behavior remain intact.
- Regression coverage added for omitted-versus-empty metadata and watcher persistence/defaulting. All four required workflows passed on the exact PR head: Docker packaging/full unit suite/image build (`40123851108`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40123851049`), non-publishing multi-architecture validation (`40123851089`), and Python syntax/acquisition-safety/modularization checks (`40123851118`; acquisition safety regressions passed). The full unit suite ran in CI, not separately locally. PR description reports one macOS-only temp-path assertion failure in local focused tests, also failing on untouched code; Linux CI passed.
- Squash-merged PR #602 as `46d8cb20c50bb89858cb62d727651e18da15ad17`. Backend-only; no manual UI test applicable. No image publication, deployment, or runtime verification.
- Phase 5 Get-to-lens acquisition attribution is implemented. Next: define/implement play and download attribution only after inspecting the available Navidrome/slskd events and choosing a reliable identity/attribution contract; do not infer listening-quality gains from save/dismiss counts.

## 2026-10-24 — Review, full CI suite, and merge PR #603

- Reviewed exact PR head `dccc555e565d4431affa5396e32d129c57fd6785` across all four changed files. The pure acquisition summary counts only jobs whose `details.metadata.lens` matches a known lens, handles malformed/non-mapping job data conservatively, and reports current persisted status counts. The service adds this object without changing save/dismiss counts or rates, and retains the default-off setting gate before feedback or acquisition-store reads.
- Regression tests cover known/unknown/missing lens metadata, malformed jobs, per-status counts, service output, and the API route. All four required workflows passed on the exact head: Docker packaging/full unit suite/image build (`40124369022`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40124369071`), non-publishing multi-architecture validation (`40124369042`), and Python syntax/acquisition-safety checks (`40124369145`; acquisition safety regressions passed). Per repository policy, the full unit suite ran in CI, not manually by the agent. PR notes a combined focused-test ordering failure in `test_discovery_lens_storage`; the same failure was reported on unchanged code, and the full CI suite passed.
- Squash-merged PR #603 as `b1454b8697016bd2217ffbf15e50c03f074d3d08`. Counts are lower bounds because pre-PR #602 success rows lack lens metadata; counts represent current stored job state, not historical request events. Backend-only; no manual browser test applicable. No publication, deployment, or runtime verification.
- Phase 5 feedback API now includes acquisition status breakdowns. Next: decide UI consumption and inspect available Navidrome/slskd events before defining play/download attribution. Do not interpret these counts as complete request history or as evidence of recommendation quality.

## 2026-10-24 — Daily lens lists enabled by default (PR #605)

- **Merged:** PR #605, squash commit `b0d309a04cf84a5aa7f223998dd6b40c675d9dfd`, from reviewed head `f75fc061d6fc0ceba0aee35b892864699ff4bb36`; owner explicitly approved merge.
- **Change:** `engine2_lens_lists_enabled` now defaults to `True`; explicit `False` continues to exit before provider, library, and storage work.
- **Verification:** Required CI on exact PR head was green, including full unit suite and Docker build (run `40127475063`) and Python syntax/acquisition-safety checks (run `40127475121`). PR reports 135 focused tests passed. Three test-collection errors in `test_service_settings.py` were reported as pre-existing and also present on main; full CI suite passed.
- **UI gate:** Owner approved merge and deferred remaining browser checks (keyboard/focus, Get using a safe fixture, Save/dismiss, reduced motion, screen readers). Those checks were not performed against this exact PR head.
- **Release state:** Merged only. No image publication, deployment, or post-merge runtime verification.

## 2026-10-25 — Full CI suite and merge PR #613

- Re-reviewed exact PR head `da0745623cee1f5293b56d951ffa36e0b1ae41d0`. The prior shared-fetch deadline issue is resolved: providers use a fixed `REQUEST_TIMEOUT = 5.0`, so a later consumer can extend the shared runner deadline without being constrained by the first consumer's shorter HTTP timeout. The added regression test uses a timeout-aware fake HTTP layer.
- The four required workflows passed on the PR run associated with the exact head: Python syntax (`40240240280`), Docker packaging/full unit suite/image build (`40240240369`), container runtime smoke (`40240240300`), and validation-only multi-architecture image validation (`40240240269`, `push: false)). The Docker packaging job's `Run unit tests` step ran 1,801 tests in 4.611 seconds and reported `OK`; its PR checkout was merge ref `4a78fcb1304eccd681e5691976e5e34994e47f56`, combining the reviewed head with base `59a7aa646f89f71389c5044d77f23fcf73514c11`. Syntax, runtime smoke, image validation and release workflow validation completed successfully. No live provider calls or browser checks were performed; no browser test was applicable to this backend-only PR.
- Squash-merged PR #613 as `2790fbca79dde0eb7b9390d972c54c9f1b341251`. GitHub reports the PR closed and merged. No image publication, deployment, or runtime verification was performed.
- Global search P2 slice A now provides MusicBrainz and Last.fm artist/album text search for `scope=all`, with shared provider calls, a cache, owned-result suppression and deduplication. Next: assess P2 slice B dependencies and acceptance criteria before implementation.


## 2026-10-26 — Re-review, full CI suite, and merge PR #622

- Re-reviewed exact PR head `f26caf1cbad1ecb91889c47316e106ce769623a1` against `main` base `7f1b44f07186522a49e41f1f508521b9bf344725`. The prior blocker is fixed: `similar_items()` delays writing refreshed provider records until seed/candidate tag work finishes without a rate-limit deadline. Regression test `test_an_incomplete_tag_refresh_leaves_the_previous_cache_entry_unchanged` seeds a prior entry, triggers a rate-limited tag lookup during `refresh=True`, and verifies the old entry remains unchanged. The scheduler retry fix remains covered by `tests/test_similar_precompute_schedule.py`.
- The PR's focused test report records 165 tests OK across similar-artist fusion/precompute, artist sections, index, providers, routes, merge and runner; size and legacy-import guards were reported OK. All five associated workflows passed on the exact head: Docker packaging/full unit suite/image build (`40253009484`; `Run unit tests` succeeded), Python syntax/acquisition-safety (`40253009419`), container runtime smoke (`40253009437`), validation-only multi-architecture image validation (`40253009480`, publishing paused), and release workflow validation (`40253009412`; `publish-release` skipped). Full suite passed in CI, not locally; live provider checks were not performed.
- Squash-merged PR #622 as `05b259cfa06f479d62486a93e781a3b54130551d`. The backend adds shared MusicBrainz artist-tag scoring, an owner play-count boost, and daily similar-artist precompute. No UI changes; no browser test applicable. No image publication, deployment, or runtime verification.
- Next: continue only after inspecting the current P3/P4 acceptance criteria and the post-merge GitHub state. Keep the tag/boost weights and precompute budget as unvalidated starting values until checked against real data.


## 2026-10-26 — Re-review, reconcile, and merge global search P4 PRs #624 and #625

- **PR #624 merged:** squash commit `13cb7d374fa76b72f65ef8c323d691fb47d9b3b5`, reviewed final head `4ef86537bf1eddb2958af34cab4ef54e1cef210b`. The final slice adds Discogs provider/style integration, genre pages, and global `genre` search to fulfill the approved `docs/SEARCH_CONTRACT.md` type contract. Earlier review findings for deadline reporting, Discogs global search integration, and per-candidate attribution were fixed in the updated PR head.
- **PR #624 verification:** first CI run failed because `tests/test_discovery_store_prefix_delete.py` still expected generation purge to touch only `search:` keys. Updated the regression assertion to also expect the new `genre:` namespace. On the final exact head, Docker packaging/full unit suite/image build passed (`40256663265`; 1,970 tests), Python syntax/acquisition safety passed (`40256663314`), container smoke passed (`40256663221`), and non-publishing multi-architecture validation passed (`40256663240`). Release-workflow validation completed (`40256663285`); publishing was skipped. No live provider check was performed.
- **PR #625 merged:** squash commit `afade38e3cf03bb38377335bd19fe64e426774a9`, reviewed final head `775171299466ea7f8ab184f9537c3fca52f70275`. Reconciled the stacked `search-p4c` branch with the post-#624 `main` tree and retargeted it to `main`; final PR diff contains only the seven intended UI/test files. Fixed an additional navigation defect found during re-review: closing a genre opened from global search now returns to the library list; closing a genre opened from an artist returns to that artist and restores focus. Added regression assertions for both paths.
- **PR #625 verification:** an initial full CI run exposed a stale source-contract assertion for the artist genre button's click handler after return-origin tracking was added. Updated the test to assert the new handler and state. On the final exact head, Docker packaging/full unit suite/image build passed (`40256978376`; 1,989 tests), Python syntax/acquisition safety passed (`40256978441`), container smoke passed (`40256978398`), non-publishing multi-architecture validation passed (`40256978474`), and release-workflow validation passed (`40256978406`; publication skipped). The owner waived manual browser verification for this batch; it was not performed. No live Discogs token check was performed.
- **Release/deployment state:** both PRs are merged. No image publication, deployment, or runtime verification occurred. The live Discogs authentication/provider path remains unverified.
- **Next action:** continue with the next approved P4 slice only after checking current `main`, open PRs, and the active work queue; keep publishing and deployment paused.


## 2026-10-26 — Re-review, full CI suite, and merge P5 latency harness PR #626

- **Merged:** PR #626, squash commit `1a8c06287c021668bb3be2a04b41e08393f019a2`, from exact reviewed final head `613306831610a392ab93a25095fc4e0a8d6e7041`. The final PR diff contains only `scripts/search_latency.py` and `tests/test_search_latency_script.py`.
- **Review fixes:** The first version could default to the app's data directory without proving isolation, and the normal owned-index factory started the identity resolver after a build. That resolver can call MusicBrainz and write identity/cache state even with `--network` disabled. The harness now requires an existing data-directory copy outside the repository, a copied `navidrome_discovery.sqlite3`, and the explicit `.navi-librarian-search-latency-isolated` marker; it constructs a measurement-only index without the identity callback. Only `--network` triggers `scope=all` searches. Terminal completion latency is recorded at the SSE `done` event, missing terminal events are counted, and index-build timing is reported in milliseconds.
- **Regression tests:** Added isolated-data-directory validation coverage, including missing path, repository path, missing database, missing marker, and valid marked copy.
- **Verification on exact PR head:** Docker packaging/full unit suite/image build passed (`40258822353`; 1,995 tests in 6.809 s, `OK)); Python syntax/acquisition safety passed (`40258822447`); container runtime smoke passed (`40258822423`); validation-only multi-architecture image validation passed (`40258822577`, publishing paused). Full suite ran in CI, not locally. No live-provider latency run was performed against the corrected harness in this review.
- **Performance evidence status:** Prior exploratory results are retained as historical evidence, but should be repeated using the corrected harness because the earlier version could run the identity resolver concurrently with measured requests. No performance target is newly claimed as accepted here. No image publication, deployment, or runtime verification.
- **Next action:** Repeat owned-only measurements using a marked isolated data copy; then, with explicit owner approval, run live-provider measurements and decide how to handle MusicBrainz 503 retries that consume the 3-second search deadline.


## 2026-10-26 — Review and merge PR #627

- **Merged:** PR [#627](https://github.com/abucalip/navi-librarian/pull/627), squash commit `99771e646663f795207b0f6593cecafe0c793d82`, from exact reviewed head `402a1a17612f713b3eea025a0431cc769c5eabe2`. The two-file diff is limited to `discovery/search/providers.py` and `tests/test_discovery_search_providers.py`.
- **Review:** When MusicBrainz returns HTTP 503, the client now checks whether the retry backoff fits the remaining search deadline. If not, it raises `ProviderError("rate_limited")` immediately rather than sleeping through a deadline that cannot accommodate the backoff. A regression test asserts no pause or second request occurs when only 0.8 seconds remain. This allows the runner to finish with other sources' results and mark the stream partial. No unrelated changes found.
- **Verification on exact PR head:** all four required workflows succeeded: Python syntax/acquisition safety (run `40259433709`), Docker packaging including the full unit suite and image build (`40259433731`), container runtime smoke (`40259433708`), and validation-only multi-architecture image validation (`40259433714`; publishing paused). The full suite was run by CI, not manually by the agent, per workflow policy. The PR author reports 136 focused tests passing; these were not independently rerun. The PR description reports a live six-search measurement; it was not independently repeated in this review.
- **State:** merged only. No publication, deployment, or post-merge runtime verification. The broader P5 latency targets and live-provider checks remain open; no claim that the 3-second target is met.
- **Next action:** continue the P5 measurement and provider-validation plan from current GitHub state; keep image publication and deployment paused unless explicitly authorized.
