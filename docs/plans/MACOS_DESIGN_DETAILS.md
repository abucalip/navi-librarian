# macOS design details: fine fixes plan

Status: D1 (`dd95d6f9`), D2 (PR #1208, squash `5071453c8ba8a2b1dbd7b510349121726b253375`, PR head `0c306579c3fabfabd6e6076f782473814f99b30e`), D3 (PR #1209, squash `7808ab8c1bbee93def332ea4efd2d68ab1ffb8a5`, PR head `2495876f52b35bd055533d68dfa43a4c158ff78a`), D4.1 (PR #1210, squash `fe90cc43151bb2b10156200d8384829f5bca0036`, PR head `4abdb36be351b05d322cb2d7a10e08494df7b62a`), D4.2 (PR #1211, squash `bb96dbbaaa1e14921b046c8690423761e3704b98`, PR head `92e36ccd442833aa879083200cec934ef75054d2`), D4.3 (PR #1212, squash `2f62f933ac1c546754eefbced5ba0040dde398b5`, PR head `d972ac1abccf607a0443215fc4725275b271b166`), D4.4–D4.6 (PR #1213, squash `2ecb2921de46fb7ac18212e734c7fd78eceb19fc`, PR head `c938fe73f2dc7c9ee3d65b875fe4e6e9177d7566`), D4.7–D4.8 (PR #1214, squash `bb701cfaca4b2b6e6ab0d96fc618d35e791aad45`, PR head `36dc8ae4646e4b4e09a44dd88cb7c9af8aa666e3`) and D5.1–D5.9 (PR #1215, squash `10e9e228cd5f22c36591d8d7927cc453b3df1f11`, PR head `9a807380df6ad655fcc48f5aa9aff15f55685227`) are merged to main; D3 and D5 visual acceptance are still open; D6 to D8 are not started. Source: the owner's 12 screenshots of the Cupertino macOS client (`macos screenshots/`, local, not in the repo), taken 2026-11-18 between 02.20 and 02.37. This is a polish pass: alignments, overlaps, spacings, text sizes, small navigation details. It does not redesign any page.

## How to read this plan

- **Screenshots** are named by time: `02.20.02` is `Screenshot 2026-11-18 at 02.20.02.png`. Short list:
  - Album: 02.20.02 (Blue Train, top), 02.20.21 (Blue Train, scrolled)
  - Artist: 02.20.44 (John Coltrane, top), 02.21.06 (scrolled)
  - Home: 02.21.45, and 02.37.08 (queue open)
  - Now Playing: 02.23.44
  - Radio: 02.24.02
  - Connections: 02.24.56
  - Timeline: 02.26.06
  - Downloads: 02.26.49
  - Atlas: 02.27.57
- **Sizes are in points (pt).** The screenshots are 3046 px wide at 2x, so 1 pt = 2 px of the original file. Measurements are estimates from the images (about ±2 pt).
- **Each item lists:**
  - where it is and what is wrong;
  - the proposed fix;
  - a file pointer (a starting point only; the implementer confirms it);
  - the acceptance check;
  - "Owner" when the owner must decide first.
- **Out of scope:** missing covers, placeholder art and dates. These are data issues, listed at the end.

## Rules for implementers

- Follow `docs/LOCAL_UI_TESTING.md`, `docs/UI_DESIGN_RULES.md` and `macos/DESIGN.md`.
- Do not add continuous or looping SwiftUI motion (CLAUDE.md, `docs/DEVELOPMENT_WORKFLOW.md` "macOS client motion and CPU rules").
- Tests: filtered only. Choose targets with `macos/scripts/select-tests.sh`, then run `swift test --filter <target>`. Report what ran and what did not.
- Acceptance is visual. For each slice, take before and after screenshots of the same pages at the same window size, Night and Day, and crop the area named in the item. Add any render test the existing screenshot tests can carry.
- One slice per PR. Each slice is small and touches only presentation. No domain logic moves into the UI.

## Slice D1: window shell, corners and hero edges

**D1.1 Hero does not meet the window's rounded corners** (02.20.02, 02.20.44, 02.23.44: top-right and top-left corners)
- **What is wrong:**
  - A thin dark rim runs along the top and right edges between the hero (blurred cover or collage) and the window edge, and it gets thicker in the corner.
  - The window content is clipped to a hard-coded `CU.windowRadius = 26` (`CupertinoTheme.swift:151`, applied at `:246`, `CupertinoNowPlaying.swift:80`, `CupertinoNowPlayingLive.swift:31`).
  - The system window corner is likely a different radius, and the content may also be inset by a point or two from the frame.
- **Fix:**
  1. Measure the real system corner radius on this macOS version from a zoomed corner crop (or read it at runtime), and derive the clip from it rather than a constant.
  2. Make the hero draw to the very edge, with no inset under the window border.
  3. If the system radius cannot be read, the clip shape must at least be concentric with the frame (`docs/UI_DESIGN_RULES.md`, "Nested corners").
  4. Do not guess a number in code without the crop check.
- **Acceptance:** crops of all four corners on Album, Artist and Now Playing, before and after, show no dark crescent and no light seam at 400% zoom.

**D1.2 Hero shows through the strip around the floating sidebar** (02.20.44, 02.21.06: left edge of the window, beside and above the sidebar)
- **What is wrong:**
  - The banner is drawn under the sidebar (`CupertinoTheme.swift:227-228`), so a sliver of the collage shows in the gutter left of and above the sidebar.
  - The sliver stops with a hard horizontal edge at the banner's bottom (about 356 pt from the top), while the sidebar continues below it.
  - On the busy collage this reads as a glitch. On the dark album blur it is barely visible.
- **Fix (owner decision, 2026-11-18: (a)):** keep the hero under the sidebar but fade it out to `CU.content` over its last 40 pt, so the gutter has no hard edge. This keeps the edge-to-edge look the design asked for. (Not chosen: start the hero at the sidebar's trailing edge.)
- **Acceptance:** left-edge crop of Artist and Album at the banner's bottom shows no hard step in the gutter.

**D1.3 Hard cut where content scrolls under the fixed hero** (02.20.21, 02.21.06: the line about 356 pt from the top)
- **What is wrong:**
  - The hero is fixed and the content scrolls under it.
  - Rows and covers are sliced by a straight edge (track 7 in 02.20.21; album covers in 02.21.06), with no shadow or fade.
- **Fix:** add the system hard scroll-edge effect, or a 12 to 16 pt fade from the hero's bottom colour, on the album and artist scroll views.
  - `macos/DESIGN.md` prefers a hard-edged scroll effect under floating bars.
  - Radio already uses `.scrollEdgeEffectStyle(.hard, for: .top)` (`CupertinoStations.swift:93`); use the same here.
- **Acceptance:** scroll the Blue Train tracks halfway under the hero. The cut reads as a deliberate edge, not as clipped content.

**D1.4 Fixed 356 pt hero takes a third of the window on every scroll** (02.20.21, 02.21.06)
- **What is wrong:** after scrolling, the hero keeps 356 pt. In a 940 pt high window only about 400 pt of list stays visible.
- **Fix (owner decision, 2026-11-18: collapse):** the hero shrinks to a compact 96 pt bar as the content scrolls: small cover (or portrait on Artist), title, Play. Scrolling back to the top restores the full hero.
  - The height follows the scroll offset directly (one resize, no looping animation, no timer). Under Reduce Motion it switches between the two heights with no tween.
  - The compact bar keeps the back button, on the same line as in D2.1.
  - This changes the documented banner (`macos/DESIGN.md`, "Album banner" and the Artist section, "the banner is fixed"); update those lines in the same PR.
  - Acceptance: scroll Album and Artist down and back up. The hero shrinks and grows with no jump. In a 940 pt high window, at least 700 pt of list shows when it is compact. Measure CPU while scrolling, following the macOS motion and CPU rules.

## Slice D2: album and artist hero alignment

**D2.1 Back button sits at a different height on Album and Artist** (02.20.02 vs 02.20.44)
- **What is wrong:**
  - Album: the back button's top is about 100 pt from the window top. Artist: about 74 pt.
  - Going Artist → Album → back, the button jumps by about 26 pt.
  - Cause: `CupertinoAlbum.swift:78` `.padding(.top, 76)` vs `CupertinoArtist.swift:97` `.padding(.top, 50)`.
- **Fix:** one shared top inset for the back button on both banners, aligned to the toolbar's centre line or a fixed distance under it.
- **Acceptance:** switching between the two pages leaves the back button in the same place.

**D2.2 Album cover is out of line with the back button and the title block** (02.20.02)
- **What is wrong:**
  - The cover's left edge, including the white spine strip, sits about 12 pt left of the back button's left edge.
  - The spine (`FlipCover(... spineStrip: true)`, `CupertinoAlbum.swift:30`) is drawn outside the cover box.
- **Fix:** put the spine inside the cover's frame, or offset the cover so its left edge (spine included) lines up with the back button's left edge.
- **Acceptance:** one vertical line touches the back button's left edge and the cover's left edge.

**D2.3 Hero column and body column never line up** (02.20.02, 02.20.44)
- **What is wrong:**
  - On Album, the hero content starts at sidebar + 32 pt (about 264 pt from the window edge). The tab bar and track table below are centred in the content (table starts about 566 pt).
  - On Artist, the bio and Albums start about 386 pt and Top songs about 1167 pt. None of these share an edge with the hero (about 276 pt).
  - The page reads as two unrelated layouts.
- **Fix:**
  - Pick one content column per page and make the hero's leading edge equal to the body's leading edge.
  - Album: either left-align tabs and table to the hero, or move the hero content into the same centred column as the table. Recommendation: left-align the body to the hero edge, with the table at its current max width.
  - Artist: align the bio and Albums leading edge with the portrait's leading edge.
- **Acceptance:** one vertical guide touches the hero's leading edge and the first column of the body on both pages.

**D2.4 Artist name and actions sit on a busy collage with no scrim** (02.20.44, 02.21.06)
- **What is wrong:**
  - "John Coltrane" (60 pt), "12 of 23 albums owned" and the capsules sit straight on dense print and photos.
  - The ⋮ button is tight against the name, and its centre is about 6 pt below the name's cap-height centre.
  - The Radio and Paths capsules are 8 pt apart, against about 14 pt between the others; Paths straddles a collage seam.
- **Fix:**
  - Add a left-to-right dark scrim (about 55% → 0% over the text block's width) behind the name, count and buttons.
  - Space the ⋮ button 12 pt from the name and centre it on the name's cap height.
  - Use one spacing token for all capsules in the row.
- **Acceptance:** text contrast of at least 4.5:1 over the worst collage tile (`docs/UI_DESIGN_RULES.md`); equal gaps between the capsules.

**D2.5 Collage tiles show seams** (02.20.44, 02.21.06: vertical lines about 460 pt and 880 pt in, horizontal about 147 pt down)
- **What is wrong:** thin light or teal lines and a 1 to 2 pt gap show between tiles (`ArtistCollage.swift`, `CollageHeroBackdrop`).
- **Fix:** let tiles overlap by 1 pt, or draw them on a black ground with no gaps. Pixel-round each tile's frame.
- **Acceptance:** a 400% crop shows no light line between tiles.

**D2.6 Translucent capsules lose their edge on light covers** (02.20.44: Shuffle, Radio, Paths)
- **What is wrong:** over the white liner-note scans, the translucent capsules almost vanish.
- **Fix:** with the scrim from D2.4 this mostly goes away. Otherwise give `CapsuleButtonStyle(translucent:)` a hairline border or a slightly darker fill on media.

**D2.7 Section heading styles differ between Album and Artist** (02.20.21 vs 02.21.06)
- **What is wrong:**
  - Album: "Not in your library" (title) then "SIMILAR ARTISTS" and "ALBUMS" (small caps, grey).
  - Artist: "Similar artists" and "Albums" as 20 pt titles.
- **Fix:** one heading style for the same kind of section on both pages. Recommendation: the 20 pt title, with small caps used only for sub-groups inside a titled section.
- **Pointers:** `RelatedSections.swift`, `CupertinoArtist.swift:119,130`.

**D2.8 Playing row in the track table hides its quality badge** (02.20.02: "I'm Old Fashioned")
- **What is wrong:** on the pink playing row, the "MP3 320" badge is pink on pink and can barely be read.
- **Fix:** on the selected or playing row, draw badges in the row's foreground colour (white outline or white fill with accent text).
- **Acceptance:** the badge on the playing row has a contrast of at least 4.5:1.

**D2.9 Track table: the "⋯" menu floats far from the row's data** (02.20.02)
- **What is wrong:** about 120 pt of empty space sits between the Quality column and "⋯".
- **Fix:** either let the Track column take the spare width (Duration and Quality move right next to "⋯"), or cap the table width. Recommendation: the first.


**D2 implementation record (2026-11-19; merged PR #1208).**

- **Merge:** PR [#1208](https://github.com/abucalip/navi-librarian/pull/1208), squash commit `5071453c8ba8a2b1dbd7b510349121726b253375`; exact PR head `0c306579c3fabfabd6e6076f782473814f99b30e`.
- D2.1: Album and Artist use one shared 76 pt hero top inset.
- D2.2: the Spine strip is drawn inside the Album cover frame, so the cover's full left edge meets the back button.
- D2.3: the Album tabs, track table and related grids are left-aligned to the hero column; the Artist body column and biography text are left-aligned to the portrait edge.
- D2.4: the Artist text group is constrained to a local 620 pt width and backed by a 55%-centre elliptical scrim that feathers to transparent on all edges; no rectangular panel or hero-wide fill. The menu is separated by 12 pt and raised 6 pt; action capsules use a 14 pt gap. The final scrim correction was made in commit `0c306579c3fabfabd6e6076f782473814f99b30e` after owner visual feedback; the owner approved the final appearance.
- D2.5: collage tile frames are pixel-rounded and overlap by 1 pt. D2.6: translucent media capsules use a dark fill and light hairline; the scrim also improves their ground.
- D2.7: source review found the recommended hierarchy already present: 20 pt top-level headings and small-caps subgroup labels under "Not in your library". No duplicate style change was made.
- D2.8: the playing-row quality badge uses accent text on the on-accent surface (white in Day, dark in Night). D2.9: the overflow action is leading-aligned within its trailing cell, beside Quality.
- Added `HeroAlignmentTests` for shared inset/action metrics, pixel alignment and overlap across the 2–5 tile layouts.
- **Tests:** the owner reports the complete macOS Swift test suite passed on the PR revision. An earlier full-suite invocation reported the timestamp-freshness assertion in `dismissQueuesOneCardEventKeyedBySubject()`; the test passed when run alone, and the owner subsequently confirmed the complete suite successful. The assertion was not weakened.
- **CI:** all five GitHub Actions workflows on exact PR head `0c306579` passed: Validate Docker image (publishing paused), Validate Docker packaging, Lint changed files, Python syntax check, and Container runtime smoke test.
- **Visual acceptance:** approved by the owner. The final soft scrim was checked after the hard-edged rectangular version was rejected.
- **Release/deployment:** no publication, deployment or runtime verification is claimed.

## Slice D3: bottom insets and the Pipeline dock

**D3.1 Pipeline dock covers content** (02.20.02, 02.20.21, 02.21.45, 02.24.02, 02.27.57, 02.37.08)
- **What is wrong:** "Pipeline 1 failed" (bottom right, about 200 × 32 pt) sits over:
  - similar-artist and album rows (Album);
  - the last shelf cover (Home);
  - the third shelf cover (Home with the queue open; the dock moves to the main column's right edge and straddles the column and the queue edge);
  - inspector rows (Atlas);
  - the On Air column ground (Radio).
- **Fix:**
  - Give every scroll view a bottom content inset equal to the dock height + 16 pt while the dock shows, so the last row can scroll clear of it.
  - With the queue open, anchor the dock inside the main column with the same 16 pt margin.
  - Pointers: `PipelineDock.swift`, `CupertinoTheme.swift:238`. `macos/DESIGN.md` says the dock was moved to the bottom left at one point; check which side is current and the reason.
- **Acceptance:** on each listed page, scroll to the end. Nothing is hidden under the dock.

**D3.2 Lists end under the player bar** (02.24.02 Radio: "Pool FM" cut; 02.26.49 Downloads: "Solar Wind" stepper cut; 02.20.02 similar-artist circles cut)
- **What is wrong:** the last row cannot be scrolled fully into view, or is clipped by a hard line above the bar.
- **Fix:** one shared bottom inset for all content scroll views (player bar gap + `CU.Space.xl`), applied in the shell rather than per page.
- **Acceptance:** scroll each page to the end. The last row sits fully above the bar with the standard gap.

**D3 implementation record (2026-11-19; PR #1209, squash `7808ab8c1bbee93def332ea4efd2d68ab1ffb8a5`, branch `macos/d3-bottom-insets-pipeline-dock`).**

- D3.1: `PipelineDockPlacement` holds the rules. The card shows on every screen except Downloads and Now Playing, sits 14 pt above the player bar and 16 pt from the trailing edge, or the queue's width plus 16 while the queue is open. The card reports its laid-out height (`onGeometryChange`); the window publishes `height + 14 + 16` through the environment, and the shell takes the shared inset or that clearance, whichever is larger. Every page ScrollView therefore gets a bottom content inset high enough for the last row to scroll above the card. The queue-open anchoring was already correct in source; the rule is now explicit and tested. Side check: the active card is bottom right (added in #972), the finished-Get notes are bottom left; `macos/DESIGN.md` records both.
- D3.2: one shared 32 pt bottom inset (`CU.Shell.contentBottomInset`) lives in the shell and applies to every content scroll view. The page-level bottom paddings were removed: pages that had 32 use the shared value, Timeline, Atlas and Connections go from 20 to 32, and Insights keeps 28 pt of its own for its dismiss/undo bar (60 pt total, as before). The player bar is a VStack sibling, so content never runs behind it; a measured end-of-page state on Downloads already showed the standard gap, so the cuts in the screenshots were mid-scroll positions. The consolidation puts that gap in one place.
- Added to `PipelineDockTests`: the placement rules, the measured scroll inset (no card, one failed job, three rows) and a Home render scrolled to the end with the card showing.
- **Verification:** 50 focused UI tests in six suites passed (`PipelineDockTests`, `ScreenshotTests`, `LiveScreenshotTests`, `CupertinoPagesRenderTests`, `HomeRenderTests`, `ConnectionsServicesRenderTests`). The selected `DiscairUITests` target ran 885 tests with 884 passing; the known wall-clock freshness test `dismissQueuesOneCardEventKeyedBySubject` failed inside the full run and passes alone. **Not done:** owner visual acceptance in Day and Night on the exact PR head, before/after crops of each listed page, and CPU measurement (no motion added; one one-shot geometry read per card layout).

## Slice D4: controls and type consistency

**D4.1 Four styles of segmented control**
- **What is wrong:**
  - Timeline "By year / By decade" and Atlas "Map / List": system blue fill.
  - Radio "Stations / Heard": pink accent fill.
  - Connections "Graph / List" and "1 / 2 / 3 steps", Downloads "All / Active / Needs you / Arrived": dark fill with white text.
  - Radio tag chips "All / Jazz": a white pill.
- **Fix (owner decision, 2026-11-18): the neutral style everywhere.** Pink (accent) stays for the single main action on a page (Play, Get album, Try again), never for a selected tab. The neutral style is the default `CUSegmented` (`CupertinoKit.swift:99`) without `accented`. Its roles already come from `CUPalette`:

  | Part | Night (dark neutral) | Day (light neutral) |
  |---|---|---|
  | Track (the control's ground) | `CU.bgFill` #202025; on a panel `CU.bgFillOnPanel` #26262B | `CU.bgFill` #ECECF0; on a panel `CU.bgFillOnPanel` #E6E6EB |
  | Selected segment | `CU.content` #0B0B0D, a chip darker than the track, inset 2 pt, radius 4 | `CU.content` #FFFFFF, a white chip lifted off the grey track, inset 2 pt, radius 4 |
  | Selected text | `CU.text` #F2F2F4, semibold | `CU.text` #1D1D1F, semibold |
  | Other segments | `CU.textSecondary` #9E9EA7, medium, no fill | `CU.textSecondary` #636368, medium, no fill |
  | Edge of the selected chip | 1 pt hairline in `CU.separator` (the drop shadow does not show on near black) | hairline drop shadow as today (`shadowInk` 14% at 1.5 pt, y 1, plus 6% at 0.5 pt); no border |
  | Hover on an unselected segment | text goes to `CU.text`; no fill | text goes to `CU.text`; no fill |
  | Size | track radius 8, padding 2; segment 24 pt high, 28 pt in a control bar | same |

  - The Day style is the Night style inverted: in Night the selected chip is darker than its track; in Day it is lighter (white on light grey, like the standard macOS segmented control). In both, the selection is shown by the chip and the semibold weight, never by colour alone.
  - Only code change in `CUSegmented`: the Night hairline on the selected chip, added when the palette mode is Night. The fills, text and sizes are already as above.
  - Then use `CUSegmented` everywhere instead of the system `Picker(.segmented)`, which draws the system blue. Files using `Picker` today: `AtlasView.swift`, `TimelineView.swift`, `GraphExplorerView.swift`, `CupertinoDownloads.swift`, `CupertinoStations.swift`, `CupertinoConnections.swift`, and others listed by `grep -n "pickerStyle(.segmented)"`. Radio "Stations / Heard" drops `accented: true`.
  - Filter chips (Radio "All / Jazz") stay a separate, documented style. They use the same roles: selected chip `CU.text` ground with `CU.content` text, unselected `CU.bgFill` with `CU.textSecondary`.
  - Contrast check (`docs/UI_DESIGN_RULES.md`, 4.5:1): selected and unselected text on their grounds in both modes. Add the pairs to `CUPalette.contrastPairs` if they are not there.
- **Acceptance:** screenshots of Timeline, Atlas, Radio, Connections and Downloads, in Night and in Day, show the same selected look, with no system blue.

**D4.1 implementation record (2026-11-19; merged PR #1210, squash `fe90cc43151bb2b10156200d8384829f5bca0036`, branch `macos/d4-1-segmented-control`).**

- `CUSegmentedSpec` holds the four style decisions: track radius 8, chip radius 4, 2 pt track padding, 24 pt segments (28 in a control bar). The selected chip is `CU.content` — white on the grey track by Day, near black on the dark track by Night — with a `CU.text` semibold label; unselected labels are `CU.textSecondary` medium. Day keeps the hairline drop shadow; Night adds a 1 pt `CU.separator` hairline around the selected chip, because the shadow cannot read on near black. Selection is the chip and the weight, never colour.
- The unused `accented` variant of `CUSegmented` was removed. Radio "Stations / Heard" stopped passing it; Connections "Graph / List" and "1 / 2 / 3 steps", Downloads "All / Active / Needs you / Arrived", Library, Settings, Taste and the other call sites already used the neutral control and now get the Night hairline.
- The system `Picker(.segmented)` controls were replaced with `CUSegmented`: Timeline "By year / By decade" (`TimelineView.swift`), Atlas "Map / List" (`AtlasView.swift`) and the classic Connections "Depth 1 / 2 / 3" control (`GraphExplorerView.swift`, unreachable under the single Cupertino theme but converted so no system segmented picker remains).
- The Radio tag chips stay a separate, documented inverted-pill style (selected `CU.text` ground with a `CU.content` label, unselected `CU.bgFill` with `CU.textSecondary`); the code comment points at `macos/DESIGN.md`.
- Contrast: added the pairs missing from `CUPalette.contrastPairs` — unselected segment text on a panel track (`textSecondary` on `fillOnPanel`) and the filter-chip label on its inverted ground (`content` on `text`). Selected segment text on the chip and unselected on a content-ground track were already `text on content` and `text secondary on fill`. All pass 4.5:1 in Day and Night.
- Added `SegmentedControlTests` (spec sizes, the Night/Day edge rule, the Day/Night inversion, the four AA pairs) and `D4SegmentedRenderTests` (Timeline, Atlas, Radio, Connections and Downloads in Day and Night, written as `d4-<page>-<mode>.png`).
- **Tests:** the agent's focused run passed 9 tests in 2 suites (`SegmentedControlTests`, `D4SegmentedRenderTests`). The owner reports a further 50 tests in 7 suites passed after 133.897 seconds. The selected `DiscairUITests` target was started but stalled and was stopped; no result is claimed for it.
- **CI:** all five GitHub Actions workflows on exact PR head `4abdb36b` passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Visual:** before/after renders of the five pages in Day and Night were taken and inspected: no system blue, one neutral selected look, and the Night hairline is visible. Owner visual acceptance in a live window is not recorded.
- **Release/deployment:** not published, deployed or runtime-verified.

**D4.2 Capsule buttons in one row differ in height** (02.21.45, 02.37.08: Home "More" against "Get album / Save / Not for me"; Home "Resume")
- **What is wrong:** "More" is about 19 pt tall against about 25 pt for its neighbours. "Resume" is also shorter than other primary capsules.
- **Fix:** every capsule in a row uses the same size variant. Check `CapsuleButtonStyle(small:)` use in `CupertinoHomeMarquee.swift` and `CupertinoHomeRadio.swift`.

**D4.2 implementation record (2026-11-19; merged PR #1211, squash `bb96dbbaaa1e14921b046c8690423761e3704b98`, branch `macos/d4-2-capsule-heights`).**

- The Home marquee's "More" menu now uses the regular variant beside Get album / Save / Not for me, and keeps the small variant on a Discover row, whose Get / Save / Not for me are all small. The size decision lives in `CupertinoPickFeedbackMenu.capsuleStyle(marquee:)`. The Home radio card's Resume, Stop and Open Radio move off their hand-rolled ~22 pt buttons onto the shared `CapsuleButtonStyle` at the regular height via `HomeRadioCardView.capsuleStyle(primary:)` (accent for Resume, neutral for Stop / Open Radio), so "Resume" matches the Home primary capsules and Stop / Open Radio match it.
- **Tests:** `swift test --disable-sandbox --filter 'D4CapsuleTests|CupertinoControlsTests|HomeRadioCardTests|HomeRenderTests'` passed 25 tests in 4 suites. `D4CapsuleTests` (new) covers marquee More regular, Discover More small and the radio card regular; `HomeRenderTests` gained two Night radio-card renders. The rendered "Resume" capsule measured 22.5 pt before and 31.5 pt after (2 px = 1 pt).
- **CI on head `92e36ccd`:** all five GitHub Actions checks passed (compile, container-smoke, lint-changed, test-and-build, validate-container).
- **Visual:** before/after Home renders of the marquee and the radio card in Day and Night were taken and inspected; the "More" and "Resume"/"Stop"/"Open Radio" capsules now share one height per row. Owner visual acceptance in a live window is not recorded. No motion added, so no CPU measurement.
- **Not verified:** owner visual acceptance in a live window. Not published, deployed or runtime-verified.

**D4.3 Phone banner text is off-centre** (02.21.45, 02.37.08: "Playing on your phone …")
- **What is wrong:** the text line sits about 3 pt above the banner's centre, while the info icon and "Continue on this Mac" are centred.
- **Fix:** centre-align the text, the icon and the button on one line (`.firstTextBaseline` or centre alignment in the `HStack`).
- **Pointer:** the Home banner in `CupertinoHome.swift` or `CupertinoHomeParts.swift`.

**D4.3 implementation record (2026-11-22; merged PR #1212, squash `2f62f933ac1c546754eefbced5ba0040dde398b5`, branch `macos/d4-3-phone-banner`).**

- `CUNotice` (`CupertinoKit.swift`) now centre-aligns its leading icon, notice sentence and trailing capsule button (`HStack(alignment: CUNotice.rowAlignment, spacing: CU.Space.s)` with `CUNotice.rowAlignment = .center`) and drops the 4 pt top padding on the icon that had previously aligned only the icon and the 24 pt trailing capsule button while leaving a one-line sentence ("Playing on your phone: …") 3.0 pt above the banner's vertical centre.
- **Tests:** `swift test --disable-sandbox --filter 'D4NoticeTests|CupertinoControlsTests|HomeRenderTests'` passed 20 tests in 3 suites. `D4NoticeTests` (new) checks `CUNotice.rowAlignment == .center` and renders the phone handoff banner in Day and Night, verifying that the vertical centres of the icon, text line and trailing button all sit within 1.0 pt of the banner's vertical centre; `HomeRenderTests` gained Day and Night phone handoff renders. In the 40.0 pt rendered phone banner (`68.0..107.5 pt`, centre `87.75 pt`, 2 px = 1 pt), the text centre moved from `84.75 pt` (`-3.00 pt`) before to `88.75 pt` (`+1.00 pt` with descenders; cap-height-to-baseline centre `87.50 pt`, `-0.25 pt`) after, matching the icon (`87.75 pt`) and button (`87.75 pt`).
- **CI on head `d972ac1a`:** all five GitHub Actions checks passed (compile, container-smoke, lint-changed, test-and-build, validate-container).
- **Visual:** before/after Home renders and banner crops in Day and Night were taken and inspected; the info icon, "Playing on your phone: …" sentence and "Continue on this Mac" capsule now sit on one centre line. Owner visual acceptance in a live window is not recorded. No motion added, so no CPU measurement.
- **Not verified:** owner visual acceptance in a live window. Not published, deployed or runtime-verified.

**D4.4 Page title leading edge differs** (02.26.06 Timeline, 02.27.57 Atlas vs Home, Radio, Connections, Downloads)
- **What is wrong:** "Timeline" and "Atlas" start about 3 pt further left than the other titles. Their search field and map share that offset.
- **Fix:** use the shared page header padding (`TimelineView`, `AtlasView` in Cupertino style).

**D4.5 Quality badge has two looks** (player bar outlined "MP3 320"; track table filled grey)
- **Fix:** one badge style across the player bar, track table and album header.

**D4.6 Sidebar group headers differ**
- **What is wrong:**
  - "Discover" is a large grey label with a disclosure chevron. "Playlists" is a small bold grey label.
  - The gap above "Smart Playlists" (about 45 pt) is larger than the gap above "Playlists" (about 25 pt).
- **Fix:** one header style (the small "Playlists" style, with the chevron where the group folds) and equal group spacing.
- **Pointer:** `CupertinoSidebar`, in `CupertinoTheme.swift`.

**D4.4–D4.6 implementation record (2026-11-22; merged PR #1213, squash `2ecb2921de46fb7ac18212e734c7fd78eceb19fc`, branch `macos/d4-4-page-title-edge`).**

- D4.4: `TimelineView` and `AtlasView` now use `Self.horizontalPadding = CU.Space.xl` (32 pt) instead of 28 pt, aligning their titles, search field and map/rail with Home, Radio, Connections and Downloads.
- D4.5: added `CUQualityBadge` (`CupertinoKit.swift`, filled 4 pt rounded rectangle, bold caption, 8×2 pt padding; `.standard`, `.playing`, `.onMedia`) and adopted it across `CupertinoPlayerBar` (replacing the outlined badge), `CupertinoAlbum` (header and track table) and `CupertinoLibrary` (song table).
- D4.6: `CupertinoSidebar` (`CupertinoTheme.swift`) now uses `groupHeaderFont = CU.Font.eyebrow.font` for both Discover and Playlists and `groupGap = CU.Space.m` above Discover, Smart Playlists and Playlists.
- **Tests:** `swift test --disable-sandbox --filter 'D4PageTitleEdgeTests|TimelineTests|AtlasTests|D4SegmentedRenderTests'` passed 21 tests in 7 suites; `swift test --disable-sandbox --filter 'D4PageTitleEdgeTests|D4QualityBadgeTests|D4SidebarHeaderTests|CupertinoControlsTests|PlayerBarRefinementTests|HeroAlignmentTests'` passed 20 tests in 6 suites.
- **Visual:** before (`fab17724`) and after (`c938fe73`) offscreen renders in Day and Night were captured and inspected for Timeline, Atlas, Connections, Album and Sidebar; the player bar rendered `"Nothing playing"` in preview mode so its badge was not shown in that render. Owner visual acceptance in a live window is not recorded. No motion added, so no CPU measurement.
- **Not verified:** owner visual acceptance in a live window. Not published, deployed or runtime-verified.

**D4.7 Selected sidebar sub-item highlight starts at the indent** (02.24.56 "Connections", 02.26.06 "Timeline", 02.27.57 "Atlas")
- **What is wrong:** the highlight for Discover sub-items starts about 16 pt right of the top-level highlights ("Home", "Radio", "Downloads"), so the pills have two left edges.
- **Fix:** keep the highlight's leading edge the same for every row and indent only the icon and label.

**D4.8 Search field shortcut hint** (all pages: "Search ⌘K")
- **What is wrong:** "⌘K" follows the placeholder one space later in the same colour, so it reads as part of the text.
- **Fix:** move "⌘K" to the field's trailing edge in the tertiary text colour (a key-cap look is optional).

**D4.7–D4.8 implementation record (2026-11-22; merged PR #1214, squash `bb701cfaca4b2b6e6ab0d96fc618d35e791aad45`, branch `macos/d4-7-sidebar-highlight-search-hint`).**

- D4.7: `CupertinoSidebar` (`CupertinoTheme.swift`) now passes `subItemIndent` (`CU.Space.m`, 16 pt) into `row(_:_:_:indent:)` as inner leading padding on the icon and label instead of `.padding(.leading, 16)` outside the button, so the `CU.accentTint` highlight pill shares the same leading edge across top-level rows and Discover sub-items.
- D4.8: `CupertinoToolbar` (`CupertinoTheme.swift`) splits `"Search  ⌘K"` into leading `Text("Search")` (`CU.textSecondary`) and trailing `Text("⌘K")` (`CU.textTertiary`) across `Spacer(minLength: 0)`.
- **Tests:** `swift test --disable-sandbox --filter 'D4SidebarHighlightSearchHintTests|D4SidebarHeaderTests|CupertinoControlsTests'` passed 9 tests in 3 suites (`D4SidebarHighlightSearchHintTests` new, verifying `subItemIndent == CU.Space.m`, matching Day/Night highlight leading edges and icon indent, and Day/Night Search/⌘K separation and `CU.textTertiary` colour).
- **CI on head `36dc8ae4`:** all five GitHub Actions checks passed (compile, container-smoke, lint-changed, test-and-build, validate-container).
- **Not verified:** owner visual acceptance in a live window; no CPU measurement (no motion added). Not published, deployed or runtime-verified.

## Slice D5: columns in lists

**D5.1 Downloads stepper columns move from row to row** (02.26.49)
- **What is wrong:**
  - The four dots (Found, Downloading, Importing, In library) drift by up to about 6 pt between rows. In library is at about 597 pt in row 1 and about 603 pt in row 2.
  - The trailing button stack is wider in row 1 (Try again + Dismiss) and the stepper fills what is left.
- **Fix:** give the stepper a fixed width and fixed column widths, and give the trailing action stack a fixed width.
- **Pointer:** `CupertinoDownloads.swift`.
- **Acceptance:** one vertical guide passes through each step's dot in every row.

**D5.2 Downloads stepper has no connectors; done rows look identical** (02.26.49)
- **What is wrong:** the four dots are not joined. A finished row (all white) carries the same visual weight as an active row.
- **Fix:**
  - Draw a 2 pt line between dots, filled up to the current step.
  - For rows already in the library, show the stepper at reduced emphasis (or hide it and keep "✓ In your library").
- Static drawing only; no looping motion.

**D5.3 Downloads list is half the page wide** (02.26.49)
- **What is wrong:** the card stops at about 730 pt, while "Clear 42 imported" floats at the page's right edge over empty space.
- **Fix:** let the card fill the content width (with a sensible max width), or align "Clear 42 imported" to the card's right edge. Recommendation: fill the width and keep the button aligned with it.

**D5.4 Queue: durations do not share a column** (02.37.08)
- **What is wrong:**
  - Rows without the "⋯" button put the time at the right edge; rows with it move the time about 29 pt left.
  - On the playing row, the "playing bars" icon also pushes the time left.
  - "6 to come · 16 min" in the header lines up with neither.
- **Fix:** reserve the "⋯" slot on every row (shown on hover or for upcoming rows only) and the playing icon slot before the title, so the time column is fixed. Align the header count's trailing edge with that column.
- **Pointer:** `CupertinoQueue.swift`.

**D5.5 Queue panel has empty space above its tabs** (02.37.08)
- **What is wrong:** the queue inspector runs from the window top, but its first control (Queue / Saved) starts about 70 pt down. The band above is empty while the toolbar stops at the panel's edge.
- **Fix:** put Queue / Saved and the count on the toolbar's centre line (about 43 pt from the top), and let the list start higher.

**D5.6 Timeline year labels are not on the card title's baseline** (02.26.06)
- **What is wrong:** "1961" sits about 9 pt above "My Favorite Things".
- **Fix:** align the year with the card title's first baseline (`.firstTextBaseline`).
- **Pointer:** `TimelineView.swift`.

**D5.7 Trailing inspectors start in different places** (02.26.06 Timeline, 02.27.57 Atlas vs 02.37.08 Queue)
- **What is wrong:** the Timeline and Atlas inspectors start under the toolbar (about 85 pt down) on a lighter ground. The queue inspector runs the full window height.
- **Fix (owner decision, 2026-11-18):** all trailing panels run full height like the queue, with the toolbar stopping at the panel edge, as it already does for the queue. The panel's title sits on the toolbar's centre line (same as D5.5).

**D5.8 Radio station logos are cropped** (02.24.02: "3j Radio" shows "Ra")
- **What is wrong:** logos use fill, so wide logos are cut.
- **Fix:** aspect-fit inside the rounded square, with 3 pt padding on a white or neutral ground when the logo is not square.
- **Pointer:** `CupertinoStations.swift`.

**D5.9 Radio "On Air" panel and "Add station"** (02.24.02)
- **What is wrong:** the empty On Air panel is about 120 pt tall with about 60 pt of empty bottom space. "Add station" sits outside it with no clear tie to it.
- **Fix:** shrink the empty state to its content, and place "Add station" under the list's header (or in the toolbar row with Stations / Heard).

**D5.1–D5.9 implementation record (2026-11-22; merged PR #1215, squash `10e9e228cd5f22c36591d8d7927cc453b3df1f11`, branch `macos/d5-columns-in-lists`).**

- D5.1: `CUStageTracker` (`CupertinoCharts.swift`) gained `columnWidth: CGFloat?` and leading outer-frame alignment; `CupertinoDownloads` (`CupertinoDownloads.swift`) sets fixed `stepperColumnWidth = 70`, `stepperWidth = 280` and `actionWidth = 128` so all four stage dots align vertically across rows.
- D5.2: `CUChartMath.stageConnectors(step:)` and static 2 pt connectors (`CUStageTracker.connectorThickness = 2`, filled up to `step`) join the four dots; `CupertinoDownloads` hides `CUStageTracker` on `.imported` rows so completed items keep only `"✓ In your library"`.
- D5.3: replaced `.containerRelativeFrame` with `CupertinoDownloads.maxListWidth = 1040` on both the `CUPanel` card and the `"Clear … imported"` action bar so the card fills the content width up to 1040 pt and the Clear button aligns with its trailing edge.
- D5.4: `CupertinoQueueInspector` (`CupertinoQueue.swift`) reserves `playingSlotWidth = 18` before the title/artist stack and `actionSlotWidth = 24` at the trailing edge of every row, and aligns the Queue header count trailing edge with `headerCountTrailingInset = 40`.
- D5.5: exposed `CupertinoToolbar.height = 44` (`CupertinoTheme.swift`) and aligned `CupertinoQueueInspector`'s top band (`headerTop = CU.Shell.toolbarTop`, `.frame(height: CupertinoToolbar.height)`) to the toolbar's centre line.
- D5.6: `TimelineView` (`TimelineView.swift`) aligns year and undated rail labels to `.firstTextBaseline` (`TimelineView.rowAlignment`).
- D5.7: extracted `TimelineInspector` (`TimelineView.swift`) and `AtlasInspector` (`AtlasView.swift`) with full-height glass chrome matching `CupertinoQueueInspector`, hosted in `CupertinoWindow`'s trailing slot (`trailingPanelWidth(for:)` in `CupertinoTheme.swift`) so the toolbar stops at the panel edge, with titles aligned to `CupertinoToolbar.centreY`.
- D5.8: `StationLogo` (`StationLogoStore.swift`) uses `.scaledToFit()` with 3 pt padding on `CU.bgFill` for non-square logos (0 pt for square logos), plus synchronous `StationLogoStore.cached(station:size:)`.
- D5.9: `OnAirPanel` (`CupertinoStations.swift`) drops `minHeight: 120` so the empty state hugs its content, and `"Add station"` moves into the Radio header toolbar row beside `Stations | Heard` on the Stations pane.
- **Tests:** `select-tests.sh` selected `DiscairUITests` (`bundle=false`); `swift test --disable-sandbox --filter 'D51DownloadsStepperColumnsTests|D52DownloadsStepperConnectorsTests|D53DownloadsCardWidthTests|D54QueueDurationColumnTests|D55QueueHeaderAlignmentTests|D56TimelineYearBaselineTests|D57TrailingInspectorHeightTests|D58RadioStationLogoTests|D59RadioOnAirAddStationTests|CupertinoChartsTests|TimelineTests|AtlasTests|StationLogoStoreTests|QueueWorkspaceTests|D4PageTitleEdgeTests|D4SidebarHighlightSearchHintTests'` passed 89 tests in 22 suites (22.239 s) on exact head `9a807380`. No full suite.
- **CI on head `9a807380`:** all five GitHub Actions checks passed (compile, container-smoke, lint-changed, test-and-build, validate-container).
- **Not verified:** owner visual acceptance in a live window; no CPU measurement (no continuous or looping SwiftUI motion added). Not published, deployed or runtime-verified.

## Slice D6: Now Playing

**D6.1 Window buttons jump when Now Playing opens** (02.23.44 vs any library page)
- **What is wrong:**
  - Library pages: the traffic lights are inside the sidebar card, about 33 pt from the left and 27 pt from the window top.
  - Now Playing: about 18 pt and 18 pt.
  - The collapse chevron sits about 30 pt from the traffic lights. "Photos on" and "Up Next" are about 8 pt lower than the traffic lights' centre line.
- **Fix:** keep the traffic lights in one place in both screens (or accept the move and document it), and put the chevron and the top-right chips on the traffic lights' centre line.

**D6.2 Album name wraps as a hanging block** (02.23.44)
- **What is wrong:** "Aretha Franklin — The Electrifying / Aretha Franklin" is laid out as artist + "—" + a two-line album name in a column of its own.
- **Fix:** one `Text` (artist, "—", album) that wraps as a paragraph, or the album on its own line under the artist, at most 2 lines with tail truncation. Both names stay clickable (they open their pages).
- **Pointer:** `CupertinoNowPlaying.swift` / `CupertinoNowPlayingLive.swift`.

**D6.3 Vinyl disc touches the lyrics** (02.23.44)
- **What is wrong:** the slid-out disc's right edge meets the lyrics column's left edge (0 to 2 pt gap). "I didn't want to do it" touches the label.
- **Fix:** move the lyrics column right by the disc's overhang plus 32 pt, or limit the slide-out so the disc stays 32 pt clear.

**D6.4 Lyrics and chips are out of line with the left column** (02.23.44)
- **What is wrong:**
  - "These lyrics are not timed." sits about 7 pt above the cover's top. The first lyric line starts about 155 pt below it, so the note looks orphaned.
  - The EQ / Crossfade / Quality / MP3 chips sit about 177 pt below the transport, with no alignment to the left column's bottom (volume slider).
  - The "MP3" chip has a filled look the others lack.
- **Fix:**
  - Put the "not timed" note directly above the first lyric line.
  - Align the chips' baseline with the volume slider row.
  - Give the MP3 chip the same style as the others, unless it is a toggle in its on state; if so, label it so.

## Slice D7: graph and map labels

**D7.1 Connections: graph edges run through labels** (02.24.56)
- **What is wrong:** the edges to Giant Steps and Crescent cross the centre label "John Coltrane". "PEOPLE" and "ALBUMS" sit on top of edges.
- **Fix:** draw labels on a small halo or backing (`CU.content` at 80%, 4 pt padding, rounded), and draw the edges under the node and its label. Place the cluster labels in the gap between edges, or drop them when a cluster has fewer than 2 nodes.
- **Pointer:** `GraphExplorerView.swift`.

**D7.2 Atlas: pin labels collide and clip** (02.27.57)
- **What is wrong:**
  - The top label "Studios, Studios, Studio 2" is overlapped and clipped by the map's top edge.
  - Around London and the Benelux, dozens of pins pile up on top of one another.
- **Fix:** turn on MapKit clustering for close pins (a numbered cluster), set label collision priority so lower-count labels hide first, and keep labels inside the map bounds.
- **Pointer:** `AtlasView.swift`.

**D7.3 Atlas inspector rows reserve an empty line** (02.27.57: "! (foreword)", "Ashes (major)")
- **What is wrong:** rows without an album still keep the album line, so they have a blank gap.
- **Fix:** collapse the line when it is empty.

**D7.4 Footer legends wrap** (02.27.57 Atlas, 02.26.06 Timeline)
- **What is wrong:** the legend wraps to two lines in the middle of a sentence, beside a right-aligned "Showing the first … only."
- **Fix:** let the legend wrap as one block with the "showing" note on its own line, or shorten the text (see D8).

## Slice D8: user-facing copy

**D8.1 Internal source codes shown** (02.27.57 Atlas inspector)
- **What is wrong:** each row shows "musicbrainz_dump · source_explicit · exact_mbid".
- **Fix:** map these to plain words on the server or in a client display map ("MusicBrainz · stated place · exact match"), or move them into a tooltip.
- Keep the mapping in one place, and server-side if the labels are shared with other clients.

**D8.2 Raw status text** (02.26.49 Downloads, row 2: "Destination Exists")
- **What is wrong:** a raw title-case status code is shown to the user.
- **Fix:** a sentence ("Already in your library folder; nothing was copied") and the right action (Dismiss, or Try again if the server allows). Check where the text comes from: the client display map or the server message.

**D8.3 Developer wording in the Connections notice** (02.24.56)
- **What is wrong:** "The server stops a walk at 200 rows or 2 seconds."
- **Fix:** "Showing the first 8 connections. Turn on Credits only, lower the reach, or use List to see them all." Keep the Switch to List button.

**D8.4 Truncated names where space exists** (player bar: "Aretha Franklin — The Electrifying…" while the centre fact has about 300 pt free on each side)
- **Fix:** let the title block take up to 40% of the bar before truncating. Centre the fact text in the space left between the title block and the controls, not on the whole bar.

## Smaller details (fold into the nearest slice)

- **Player bar waveform under text** (all pages): the waveform runs behind the second line ("John Coltrane — Blue Train"). Lower the waveform's opacity under the text block or start it after the text block. Static only. (D4)
- **Home hero with the queue open** (02.37.08): the hero backdrop shows two vertical bands (about 460 pt and 920 pt in). Same fix as D2.5 if it is a tiled backdrop. "Next picks" moves under the cover and leaves the right half of the card empty; check the narrow layout. (D2)
- **Home shelf play buttons** (02.21.45): the round play buttons on covers are cut by the player bar edge. Covered by D3.2.
- **Album hero badges** (02.20.02): "MP3 320" and "7 of 7 owned" are about 11 pt bold on a translucent ground; low contrast over a light blur. Check at least 4.5:1, or add a darker badge ground on media. (D2)
- **Artist bio** (02.20.44): justified text leaves visible rivers ("he scored an / unexpected hit"). Owner decision (2026-11-18): the bio becomes left-aligned (ragged right), keeping the centred column and its width. This replaces the documented justified bio (`ArtistPageParts.swift:14`, the `.justified` paragraph style at `:52`); update that comment. (D2)

## Owner decisions (2026-11-18)

The owner took every recommendation and added one detail for D4.1.

1. D1.2: the hero fades out in the sidebar gutter.
2. D1.4: the hero collapses to a compact bar on scroll.
3. D4.1: the dark neutral selected style in Night, and its Day equivalent (white chip on a light grey track). The full spec is in D4.1.
4. D5.7: trailing inspectors run full height, like the queue.
5. Artist bio: left-aligned.

6. Player bar: the cover keeps showing twice, large in the sidebar slot and small with the disc in the bar. No change.

## Out of scope: data, not design

- Missing covers: Home Today's Pick "Nigeria 70" shows a plain gradient; Downloads rows; Connections "A Love Supreme" blank, "Live at the Village Vanguard" purple.
- Timeline dates are reissue years (Blue Train 1997, Kind of Blue 1987). This is a data or source question for `TimelineModel` and the server, not a design fix.
- Radio tags: only FIP Jazz shows a tag, because the others have none.

## Order

D1 → D2 → D3 first (they cover the owner's main complaint and the overlaps), then D4, D5, D6, D7 and D8 in any order. All owner decisions are taken; every item can start now.
