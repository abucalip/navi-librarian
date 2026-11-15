# Flow Discover page: one switch (option B)

Status: plan, approved direction. The owner chose option B ("One switch") on 2026-11-15 from three mockups (A one feed, B one switch, C hub). No code has been written yet. Build it in the steps of section 8, one PR per step, in order.

Scope: the **Flow** layout of the Android client (`Layout.Flow`, every Flow palette). No other theme, the server, the web client or macOS changes. Every change sits behind `isFlow()`.

## 1. Files

| What | Where |
|---|---|
| This plan | `docs/Discover_page.md` |
| Mockups (spec), four frames B1 to B4 | [`design/android-art-themes/flow/discover-b/discover-b.html`](design/android-art-themes/flow/discover-b/discover-b.html) and `discover-b.png` beside it |
| The earlier Flow Discover mockup (superseded for Discover only) | `design/android-art-themes/flow/discover.html` / `.png` |
| Flow tokens and components (unchanged) | `design/android-art-themes/flow.css`, `ui/common/FlowKit.kt`, `ui/common/FlowPages.kt` |

The mockup HTML is self-contained: colours are the `Palettes.Flow` values, icon paths are copied from `ui/common/ArtIcons.kt`, 1 CSS px = 1 dp, covers are drawn stand-ins. Re-render the PNG with headless Chrome (`--window-size=1680,940 --screenshot`) after editing the HTML. **The mockups are the spec**; where this text and a frame disagree, ask the owner.

All Kotlin paths below are under `android/app/src/main/kotlin/app/discair/`.

## 2. The problem today

Flow's Discover (`ui/discover/FlowDiscover.kt`, `ui/discover/DiscoverScreen.kt`) stacks three selector rows before the first album:

1. `FlowTabs` Lists | Insights (`FlowDiscoverHeader`).
2. Six capsule chips: Daily picks, Deep dives, New releases, Add to your collection, Personal discoveries, Saved.
3. `EditorTabs` over a `HorizontalPager` (`ListBody`): four lens tabs on Daily picks (`LensLists`), one tab per `genreRowLabel` on Deep dives.

Insights then shows five lens headings (`InsightsPage`), including lenses that are off or empty, each with a paragraph.

## 3. The design in one paragraph

The shell's bar stays as it is ("Discover" large, Downloads, Settings). Under it, **one switch row** names the list on screen ("Daily picks ⌄") and shows where it sits among the seven (page dots). Tapping the switch opens a **sheet** with the five lists, then Saved and Insights under "Yours". Inside a list, the old third row becomes **section headings** with counts: lens names on Daily picks, genre names on Deep dives. Albums show as a **two-column grid**, cover first, Get on the cover. Insights loses its five lens headings: the cards already carry their lens as a tag, and the off or empty lenses fold into one muted line.

## 4. Components

### 4.1 Switch row (new, frames B1, B3, B4)

- Sits directly under the shell bar, inside `DiscoverScreen`'s column, in place of `FlowDiscoverHeader`. Height 48 dp, padding 0 16 dp.
- Left: one button, the current list's `DiscoveryList.label` in Inter 700 22/28 sp, letter-spacing −0.02 em, `p.text`, `maxLines = 1`, ellipsis; then `ArtIcons.Down` 20 dp in `p.accent` with 4 dp gap. The whole label plus chevron is the touch target (min height 48 dp). Semantics: role Button, content description "`<label>`, list `<n>` of 7. Change list".
- Right: page dots, one per `DiscoveryList.entries` (7), 5 dp apart. Others 6×6 dp, radius 3, `p.chart3`. Current 18×6 dp, radius 3, `p.text`. Decorative (`clearAndSetSemantics {}`); the button's description carries the position.
- Not in the shell. The shell keeps `flowTitle = "Discover"`. No new bar buttons (Saved lives in the sheet).

### 4.2 List sheet (new, frame B2)

- The themed `ModalBottomSheet` from `ui/common/BrutalComponents.kt` (Flow branch: radius 24 dp top, handle 36×4 dp in `p.chartGrid`). Pass `containerColor = p.rail` (#FBFAF7) so the white `FlowGroup`s stand out on it, as in frame B2; the default `p.surface` would put white on white.
- Title "Lists": Inter 700 20/24 sp, padding 0 16 dp 12 dp.
- Two `FlowGroup`s of `FlowListRow`s (`ui/common/FlowKit.kt`), divider between rows, `FlowEyebrow("Yours")` between the groups (Inter 600 12/16 sp, uppercase, +0.04 em, `p.textMuted`, padding 18 28 6 dp).
- Each row: `leading = FlowIconTile(icon)`, `title` = the list label, `state` = the subtitle below. The current list's title is `p.accent`, and its `trailing` is `ArtIcons.Check` 20 dp in `p.accent`. Other rows have **no trailing** (pass an empty `trailing = {}`; the default chevron would read as "opens a page").
- Tapping a row selects the list (`selected = it.name; statusLine = null`, as the chips do now) and closes the sheet. Back and the scrim close it unchanged.
- **No counts and no covers in the sheet.** Only the list on screen is loaded (section 6); showing numbers would mean reading every list.

| Group | Row | Icon (`ArtIcons`) | Subtitle |
|---|---|---|---|
| Lists | Daily picks | `Sun` | Four lists, new each day |
| Lists | Deep dives | `Album` | More from artists you play, by genre |
| Lists | New releases | `MusicNote` | Recent albums near your taste |
| Lists | Add to your collection | `Lib` | Well-known albums you do not own |
| Lists | Personal discoveries | `Paths` | Further from what you play |
| Yours | Saved | `Bookmark` | Albums you kept for later |
| Yours | Insights | `Wave` | Your taste and what it notices |

Keep the order of `DiscoveryList.entries`; the sheet, the dots and the swipe all use it. Put the subtitles and icons in one table in code (for example `FlowDiscoverRules.sheetRows`) so a test can check that every `DiscoveryList` entry has exactly one row.

### 4.3 Section heading (frames B1, B3)

- Reuse `FlowLensHeading(name, count)` (`FlowDiscover.kt`): Inter 700 20/24 sp heading, count in `p.textMuted` 14 sp at the right. Padding 14 16 10 dp. Semantics heading (already there).
- Daily picks: one heading per lens section, in `LensLists` order, count = visible cards (after `hidden`).
- Deep dives: one heading per `genreRowLabel` group in server order; a blank label is "More" (as `pagesFor` does now). When no row has a label, no headings: one plain grid.
- Other lists: no headings.

### 4.4 Section note (frame B1 text, B4)

A muted line in a `p.raised` box: radius 12 dp, padding 10 12 dp, 13/18 sp `p.textMuted`, 16 dp side margin. Used for:

- a lens section that failed: "`<lens>` could not be loaded: `<error>`" (today's wording);
- a lens section that is empty: the server's `message`, else "No albums today." (today's wording);
- an empty Deep dives genre never happens (groups come from rows).

The whole-list states keep today's `emptyNote` (disabled "Daily picks are turned off in Settings.", server message, Build this list button) unchanged.

### 4.5 Grid card (new, frames B1, B3)

Replaces `FlowDiscoverCard` in `CardGrid`'s Flow branch. Two columns, `GridCells.Fixed(2)`, gaps 14 dp across and 16 dp down, padding 16 dp sides, bottom `16.dp + LocalBottomClearance.current`.

- **Cover:** `FlowCover`, full column width, square, radius 12 dp, a soft drop shadow (`flowDepth` level 1 or the `--e1` look); tap opens the album (as now).
- **Get** on the cover, 8 dp from the bottom-right corner: a 34 dp circle, `p.accent` fill, `ArtIcons.Get` 18 dp in `p.onAccent`, light shadow. It is `FlowGetButton(..., iconOnly = true)` with its current states (Pending, Requested shows `Check`, Failed retries). When `item.acquired`: a 34 dp `p.surface` circle with `ArtIcons.Check` in `p.text`, disabled, description "`<album>` is in your library" (as now).
- **Text** under the cover (8 dp gap): title Inter 600 14/19 sp, 1 line; "artist · year" 12.5/17 sp `p.textMuted`, 1 line, opens the artist (as now); reason line (`pickReason`) 12.5/17 sp `p.textMuted`, 1 line. When there is no reason and the album is owned, the third line reads "In your library"; otherwise it is left out.
- **Save and ⋯** to the right of the title and artist lines: `ArtIcons.Bookmark` (saved: `BookmarkFilled` in `p.accent`) and `ArtIcons.More`, glyphs 18 dp in `p.textMuted`. Same actions, states and descriptions as today's card (Save toggles; Pending disables; the menu holds Not this album, Not this artist and `PickFeedbackItems`). See open point O1 for the touch size.
- Keys: `"<section>:<entry.key>"`, because one album can appear in two lens sections. Keep `animateItem()` so dismissals slide out.

### 4.6 Insights (frame B4)

- The switch row reads "Insights"; no Lists | Insights control.
- Order: the taste card (`TasteCardView`, unchanged, with its Details sheet), then every visible insight card in `lensKinds(response)` order, each the existing `FlowInsightCard` (it already shows the lens as a `FlowTag`; Anniversaries keep the `cautionDim`/`caution` tag).
- **No lens headings on Flow.** After the cards, one section note (4.4) listing the lenses with nothing to show: "Off: `<names>`. Nothing today: `<names>`." Leave out either half when it is empty, and the whole note when both are. Names come from `lensName`.
- Other themes keep `InsightsPage` exactly as it is.

### 4.7 What does not change

Shell bar and its buttons, the nav capsule, the mini player, the blur, the snackbar with Undo, `statusLine`, Build this list, `rememberLoad` and the request counts (`countFor`), dismiss and save logic, `PickFeedbackItems`, the taste refresh once per launch, Soft Brut's and the classic Discover.

## 5. Tokens (Flow · Warm white; every Flow palette maps the same roles)

| Role (`Palette`) | Warm white | Used for |
|---|---|---|
| `rail` / page | `#FBFAF7` | page, sheet (`containerColor`) |
| `surface` | `#FFFFFF` | grouped rows, insight cards, owned Get circle |
| `raised` | `#EFECE5` | icon tiles, section note, round buttons |
| `edge` | `#E2DFD6` | row dividers |
| `text` | `#15130F` | titles, current dot |
| `textMuted` | `#645F55` | meta, reason, counts, notes, Save and ⋯ glyphs |
| `accent` | `#C2410C` | switch chevron, Get, current sheet row and check, saved bookmark |
| `onAccent` | `#FFFFFF` | Get glyph |
| `chart3` | `#D9D4C8` | other dots |
| `chartGrid` | `#E2DFD6` | sheet handle (the sheet's own) |
| `caution` / `cautionDim` | `#8A5300` / `#F8E8CC` | Anniversaries tag (unchanged) |
| scrim | `rgba(21,19,15,.38)` | behind the sheet (the sheet's own) |

Use the palette roles, never the hex codes, so the night palettes (Ember, Moss, Plum) and the other day palettes follow. The mockup's chevron grey `#B5B0A5` is `FlowRules.chevron(p)`.

Type: Inter (font pair `flow`). Sizes in dp: switch row 48, sheet row min 64 (`FlowRules.ROW_MIN`; the mockup draws 56, follow the code), icon tile 32 with 18 glyph, Get circle 34, cover radius 12, card gaps 14/16, dots 6 and 18×6.

Add the new numbers to `FlowPagesRules` (or a new `FlowDiscoverRules` object next to it): `SWITCH_HEIGHT = 48`, `GRID_GAP_X = 14`, `GRID_GAP_Y = 16`, `GRID_COVER_RADIUS = 12`, `GET_ON_COVER = 34`, `DOT = 6`, `DOT_CURRENT = 18`. `DISCOVER_COVER` and `DISCOVER_GAP` stay as long as anything uses them; delete them in step D4 if nothing does.

## 6. Behaviour

- **Loading:** unchanged. Only the list on screen is read; Daily picks still reads its four lens lists together. The sheet reads nothing.
- **Swipe:** on Flow there is no pager any more, so every sideways swipe over the page goes to `switchBy` and moves to the previous or next list in `DiscoveryList.entries` order, Insights included; the dots follow. The edge-overflow `NestedScrollConnection` is only needed by the pager and stays for the other themes.
- **Saved:** a list like the others (sheet row, sixth dot). Cards there start as saved (as now).
- **Remembered choice:** `selected` stays `rememberSaveable`, as now.
- **Accessibility:** the switch is one button with the list name and position; the sheet rows are buttons whose current one says "selected" (`Modifier.semantics { selected = true }`); headings keep `heading()`; Get, Save and ⋯ keep their descriptions; nothing new animates every frame.

## 7. Removed on Flow

`FlowDiscoverHeader` (Lists | Insights and the chips), `EditorTabs` and `HorizontalPager` for Daily picks and Deep dives, the one-column `FlowDiscoverCard`, and the Flow lens headings inside Insights. Delete the Flow-only code that nothing calls after D3; keep anything another theme uses.

## 8. Build steps (one PR each, in order)

Each step: branch from current `main`, Flow-only, other themes unchanged. Run **filtered tests only** (JDK 17): `FlowTest`, `ExistingLayoutsTest`, `DiscoveryTest`, `InsightsTest`, `FlowPagesRulesTest`, `SoftBrutTest`, `NavRulesTest`, plus the new test of the step. Record the PR, squash and tests in `ACTIVE_WORK.md` and `PROJECT_LOG.md`. Compare the screen with the frame named in the step; say plainly when it was not seen on a device.

### D1. Switch row and list sheet (frames B1 top, B2)

- New `FlowDiscoverSwitch(list, onOpen)` and `FlowListSheet(list, onSelect, onDismiss)` in `ui/discover/FlowDiscover.kt`; the row/icon/subtitle table in `FlowDiscoverRules`.
- `DiscoverScreen`: the Flow branch draws the switch instead of `FlowDiscoverHeader`, and holds `var sheetOpen by remember`.
- Test `FlowDiscoverRulesTest`: one sheet row per `DiscoveryList` entry, in entry order, labels equal to `DiscoveryList.label`; dot index equals the entry's ordinal; the switch description text.
- Acceptance: one selector row; every list, Saved and Insights reachable from the sheet; the third row (lens/genre tabs) may still show until D2.

### D2. Sections and grid card (frames B1, B3)

- On Flow, `ListBody` draws one `LazyVerticalGrid` with full-span heading and note items (`GridItemSpan(maxLineSpan)`) instead of `EditorTabs` + `HorizontalPager`; `pagesFor` stays as the source of sections and titles.
- New `FlowDiscoverGridCard` (4.5) replaces `FlowDiscoverCard` in `CardGrid`'s Flow branch.
- Swipes go straight to `switchBy` on Flow.
- Tests: section building for Daily picks (four lenses, failed lens, empty lens, duplicate album across lenses gets two keys) and Deep dives (labels, blank → "More", no labels → no headings), as pure functions in `FlowDiscoverRules`; the third-line rule (reason, else "In your library" when owned, else nothing).
- Acceptance: frames B1 and B3; no tabs anywhere on Discover; Get, Save, menu, Undo and Build this list work as before.

### D3. Insights without lens headings (frame B4)

- Flow branch in `InsightsPage`: taste card, cards in `lensKinds` order, then the one-line note (4.6).
- Test: the note text for (off only), (empty only), (both), (neither → no note).
- Acceptance: frame B4; other themes' Insights unchanged.

### D4. Cleanup and closeout

- Delete Flow code nothing calls (`FlowDiscoverHeader`, `FlowDiscoverCard`, unused `FlowPagesRules` constants). Update `ARCHITECTURE.md` only if a new file was added. Mark this plan done in `ACTIVE_WORK.md` and point to the merged PRs.
- Owner check on the phone: each of the seven lists, the sheet, swipes across all seven, a night palette.

## 9. Open points for the owner

- **O1. Save and ⋯ touch size.** In a 157 dp column, two full 48×48 dp targets leave about 60 dp for the title. The plan uses 36 dp wide × 48 dp tall boxes (18 dp glyphs), which gives about 85 dp. If 48×48 is required, Save moves into the ⋯ menu and only ⋯ stays beside the title. Default until the owner says otherwise: 36×48.
- **O2. Long list names in the switch.** "Add to your collection" and "Personal discoveries" fit at 22 sp beside the dots on a 360 dp screen; on narrower screens the label ellipsizes. Shorter switch labels are possible if the owner prefers.
