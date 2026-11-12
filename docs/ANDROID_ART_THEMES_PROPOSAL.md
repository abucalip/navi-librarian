# Android art-led themes: Soft Brut and Flow (proposal)

Status: **proposal; step 0 (PR #1005), S1 (PR #1006) and S2 (PR #1007) built; Home and the shell are themed, the other pages are not yet.** Written 2026-11-12. This document and the mockups beside it are the whole change; no application code is touched. Building starts only after the owner approves it and the steps in section 10 are scheduled in `ACTIVE_WORK.md`.

## 1. What the owner asked for

Two new Android themes whose Home is built around album artwork and artist photos instead of numbers: one in a subtle neobrutalist style, one in an ordinary style inspired by iOS. Each theme owns its elements: the way it arranges its pages and components must not change any other theme. Some statistics are fine, but few.

Eight dashboards were drawn (four per theme) and the owner chose:

| Theme | Chosen proposal | Change asked for |
|---|---|---|
| Soft Brut (subtle neobrutalism) | **N1, Cover Stack** | Add the Radio tile from N3 |
| Flow (iOS-inspired) | **I4, Flow** | None |

The two sheets the owner chose from are kept as the record of the choice: [`picks/soft-brut-proposals.html`](design/android-art-themes/picks/soft-brut-proposals.html) and [`picks/ios-style-proposals.html`](design/android-art-themes/picks/ios-style-proposals.html).

## 2. Rules both themes follow

1. **Ownership.** Each theme is one new `Layout` value with one palette. Every composable it changes is reached through a branch on that layout (as `SheetStack` and `StickerWall` are today) and lives in the theme's own files (section 9). No shared composable changes its output for any other layout. A unit test asserts that every existing palette still resolves to its current layout.
2. **Behaviour is unchanged.** A theme changes how a screen is arranged, never what it does (D-023). Get album, Save, Not this album, Never suggest this artist, Play, Dismiss with its confirmation, the downloads badge, Settings, the mini player and the four destinations (Home, Discover, Library, Search) stay reachable, with text labels where they have them today.
3. **The mockups are the spec** (the Round 3 owner rule). Each screen is built element by element from its mockup; anything dropped is listed in the PR.
4. **Artwork first, numbers last.** Home opens on artwork. Each Home shows at most one line of statistics, and it opens Library stats.
5. **No new endpoints, fonts or icon assets.** Everything drawn uses data, font files and icons the app already has (sections 5, 7 and 8).
6. Existing rules still apply: 48dp touch targets, text contrast of at least 4.5:1, a state never shown by colour alone, reduced motion respected, missing data said in words and never shown as zero.

## 3. Soft Brut · Lavender

Subtle neobrutalism, taken from the kit in the owner's reference folder (ink outline, hard offset shadow, pastel fill, mono labels) and turned down: a **1.5dp** outline, a **3dp** shadow, one accent, and the outline goes on the artwork before anything else.

**Identity**

| | Value |
|---|---|
| Palette id, label | `softbrut`, "Soft Brut · Lavender" (light) |
| Family, layout | `Family.Brutal`, new `Layout.CoverStack` ("Cover Stack") |
| Shape | radius 10, outline 1.5, shadow 3. `BrutalShape` holds whole numbers today, so its outline must accept 1.5 (section 8, D1) |
| Font pair | the existing `brut_modern` (Space Grotesk 700 titles, Inter body, JetBrains Mono labels and numbers) |
| Accent as text | **Never** (lavender on the page is 1.7:1). Links are ink, underlined. The fill carries the accent |
| Pressed state | The element moves 3dp onto its shadow |

**Colour roles** (token names are those in [`soft-brut.css`](design/android-art-themes/soft-brut.css); the right column is the `Palette` field)

| Token | Value | `Palette` field |
|---|---|---|
| `--page`, `--rail` | `#FBF7EE` | `ink`, `rail` |
| `--surface` | `#FFFFFF` | `surface` |
| `--raised` | `#F1EBDD` | `raised`, `chartGhost` |
| `--edge` | `#1C1B22` | `edge`, `edgeStrong`, `shadowColor`, `chartBase` |
| `--edge-soft` | `#D8D2C4` | row dividers (dashed) and `chartGrid` |
| `--text` | `#1C1B22` | `text` |
| `--muted` | `#5E5A6B` | `textMuted` (6.2:1 on the page, 6.7:1 on the surface) |
| `--accent` | `#C4B5FD` | `accent`, `chart1` (always with the outline) |
| `--accent-dim` | `#ECE6FF` | `accentDim` |
| `--on-accent` | `#1C1B22` | `onAccent` (9.3:1) |
| `--accent2` | `#BFD9FF` | `accent2`: the Radio tile |
| `--accent3` | `#A6E9CB` | `accent3`: tags |
| `--accent4` | `#FFD84D` | `accent4`: the insight tag |
| `--ok` / dim | `#1B6B33` / `#D9EEDD` | `ok`, `okDim` |
| `--caution` / dim | `#7F4A00` / `#FBE9C4` | `caution`, `cautionDim` |
| `--danger` / dim | `#B3261E` / `#F8D9D5` | `chartRed`, `chartRedText`, `dangerDim` |
| `--info` / dim | `#1D4FB8` / `#DCE5FB` | `info`, `infoDim` |
| `--chart2`, `--chart3` | `#8B879A`, `#FFFFFF` with outline | `chart2`, `chart3` |

`minTextContrast = 4.5`, `minAccentContrast = 1.7` (the accent relies on its outline, as the other Brutal themes do).

**Components** (drawn on [`soft-brut/components`](design/android-art-themes/soft-brut/components.html))

| Component | Rule |
|---|---|
| Outline and shadow | One recipe for cards, buttons, the mini player, the navigation, fields, tabs and player buttons: 1.5dp ink outline, 3dp ink shadow to the lower right, surface fill, radius 10 |
| Covers and artist photos | 1.5dp outline, radius 6 (12 on the large cover); the large cover has a 4dp shadow. Artist photos are circles |
| Buttons | 44dp high (48dp touch), radius 10, label Inter 700 14. Primary is filled lavender. Square icon button 44 by 44 |
| Chips | 36dp, pill, outline, no shadow; selected is filled lavender |
| Tabs | A joined, outlined group; the selected segment is filled lavender |
| Tags | JetBrains Mono 10, caps, +0.07em, outline, radius 6, mint, yellow or lavender fill |
| Lists | Plain rows of at least 64dp with a dashed `--edge-soft` divider. Settings groups sit in one outlined card |
| Section heading | Space Grotesk 700 18; its link is underlined ink |
| Eyebrow | JetBrains Mono 500 11, caps, +0.08em, muted |
| Progress and tracker | A 10dp outlined bar with a lavender fill; the tracker is four outlined segments with the step names beneath |
| Switch | 52 by 32, outlined; on is filled lavender with the knob to the right |
| Navigation | One outlined bar, radius 14, four cells of 50dp with icon and label; the current cell is filled lavender and outlined |
| Mini player | 56dp outlined card: cover 40, title, artist, play or pause |
| Sheets, snackbar | The sheet is an outlined surface with a 14dp top radius. The snackbar is ink with page-coloured text and an underlined Undo |

## 4. Flow · Warm white

An iOS-inspired theme: no outlines and no hard shadows. Large titles, continuous corners, soft depth, translucent bars, capsule buttons and grouped lists. The artwork supplies the colour.

**Identity**

| | Value |
|---|---|
| Palette id, label | `flow`, "Flow · Warm white" (light) |
| Family, layout | `Family.Classic`, new `Layout.Flow` ("Flow") |
| Font pair | new `flow`: Inter for titles (800, −0.03em), body and labels; numbers in Inter with tabular figures. Uses the bundled `inter_variable.ttf`; Apple's own typeface cannot be shipped on Android |
| Accent as text | Yes on the page and the surface (5.0:1 and 5.2:1). Not on `raised` (4.4:1): text on a raised chip is the text colour |
| Pressed state | Tone shift, as the Classic themes do |

The accent in the chosen mockup was `#E8590C`. White on it is 3.6:1, which fails for a button label, so the spec uses **`#C2410C`** (white on it 5.2:1). The hue is the same and the mockups in this folder already use it.

**Colour roles** (tokens in [`flow.css`](design/android-art-themes/flow.css))

| Token | Value | `Palette` field |
|---|---|---|
| `--page`, `--rail` | `#FBFAF7` | `ink`, `rail` |
| `--surface` | `#FFFFFF` | `surface` |
| `--raised` | `#EFECE5` | `raised`, `chartGhost` |
| `--edge` | `#E2DFD6` | `edge`, `chartGrid` (hairlines, 0.5dp) |
| `--edge-strong` | `#8E887B` | `edgeStrong`, `chartBase` (3.4:1 on the page) |
| `--text` | `#15130F` | `text` |
| `--muted` | `#6F6A60` | `textMuted` (5.2:1 on the page, 5.4:1 on the surface, 4.6:1 on raised) |
| `--accent` | `#C2410C` | `accent`, `chart1` |
| `--accent-dim` | `#FBE4D5` | `accentDim` |
| `--on-accent` | `#FFFFFF` | `onAccent` |
| `--ok` / dim | `#1E7A3C` / `#DCEEDF` | `ok`, `okDim`; also the switch when on |
| `--caution` / dim | `#8A5300` / `#F8E8CC` | `caution`, `cautionDim` |
| `--danger` / dim | `#C0271A` / `#F9DCD8` | `chartRed`, `chartRedText`, `dangerDim` |
| `--info` / dim | `#1F5FBF` / `#DCE7F8` | `info`, `infoDim` |
| `--chart2`, `--chart3` | `#A8A296`, `#D9D4C8` | `chart2`, `chart3` |
| `--bar` | white at 86% | the mini player and navigation fill |

**Depth** (three levels, all soft; the values are in `flow.css` as `--e1` to `--e3`)

| Level | Used by | Shadow |
|---|---|---|
| 1 | Cards, grouped lists | y 4, blur 14, 30% of `#15130F`, pulled in 10 |
| 2 | Mini player, navigation, snackbar | y 6, blur 22, 30%, pulled in 8 |
| 3 | The cover in front (Home, Album, Now Playing) | y 22, blur 34, 60%, pulled in 18 |

**Components** (drawn on [`flow/components`](design/android-art-themes/flow/components.html))

| Component | Rule |
|---|---|
| Large title | Inter 800 30/36, −0.03em, at the top of every root and stack page; the stack page's top bar repeats the title small |
| Covers and artist photos | Radius 8 small, 14 large, no outline. Artist photos are circles in rows and 3:4 cards with the name over a dark fade on Home |
| Buttons | 44dp capsules. Primary is filled accent with a white label; secondary is `raised` with an accent label; round icon button 44 |
| Top-bar actions | 36dp circles in `raised` (48dp touch) |
| Chips | 34dp capsules in `raised`; selected is filled with the text colour |
| Tabs | A segmented control: `raised` track of radius 11, the selected segment a white pill with a small shadow |
| Tags | Inter 600 11, caps, radius 6, tinted fill |
| Lists | Rows of at least 64dp with a 0.5dp hairline. Grouped lists are one white card of radius 16 with icon tiles of 32dp and a grey chevron |
| Section heading | Inter 700 20; its link is accent-coloured |
| Progress and tracker | 4dp rounded bars |
| Switch | 52 by 32, grey track, white knob with a shadow; on is green |
| Navigation and mini player | Two floating capsules (radius 30 and 18) in `--bar` with a hairline. The current destination is accent-coloured on a `raised` pill |
| Wash | Album and Now Playing tint the top of the page with a colour taken from the cover, fading to the page by 420dp |

The mockups blur what is behind the two bars. Compose cannot blur content behind a surface without extra work (a captured layer with `RenderEffect` on Android 12 and later, nothing below), so the first build uses the 86% fill with no blur; blur is a later refinement (section 8, D3).

## 5. Fonts and icons

**Fonts.** No new font files.

| Role | Soft Brut (`brut_modern`) | Flow (new pair `flow`) |
|---|---|---|
| Large title | Space Grotesk 700, 26/32, −0.02em | Inter 800, 30/36, −0.03em |
| Title (album, artist, pick) | Space Grotesk 700, 26/30 | Inter 700, 24/28, −0.02em |
| Section heading | Space Grotesk 700, 18/24 | Inter 700, 20/24, −0.02em |
| Row title | Inter 600, 14/20 | Inter 600, 15/20 |
| Body | Inter 400, 14/20 | Inter 400, 14/20, −0.01em |
| Small | Inter 400, 12/18 | Inter 400, 12/18 |
| Eyebrow, tag | JetBrains Mono 500, 11/16, caps, +0.08em | Inter 600, 12/16, caps, +0.04em |
| Numeral | Space Grotesk 700, 28/32 | Inter 700, 28/32, tabular |
| Button label | Inter 700, 14 | Inter 600, 15 |

Space Grotesk ships at 700 only (`space_grotesk_700.ttf`); that is the only weight used. The font pair stays the owner's choice in Appearance: choosing either theme does not force its pair, but the pair above is the one each theme is drawn with and is suggested when the theme is first chosen.

**Icons.** No new icon assets. The mockups draw stand-ins; the app keeps its own.

| Mockup | App icon |
|---|---|
| Play, pause, next, previous, shuffle, repeat | `PlayerIcons.Play`, `Pause`, `Next`, `Previous`, `Shuffle`, `Repeat` |
| Queue, add to queue, lyrics, equalizer, crossfade | `PlayerIcons.Queue`, `QueueAdd`, `Quote`, `Tune`, `Swap` |
| Back, close sheet, chevron | `PlayerIcons.Left`, `Down`, `Right` |
| Radio, server, appearance, ListenBrainz | `PlayerIcons.Radio`, `Server`, `Sun`, `Wave` |
| Download to device, remove | `PlayerIcons.DownloadToDevice`, `Close` |
| Favourite, check, search, clear | `Icons.Default.Favorite` and `FavoriteBorder`, `Check`, `Search`, `Clear` |
| Home, Discover, Library, Search; downloads; Settings; the three dots; Get; Sort; Sonic path | Whatever the current navigation, top bar and buttons already use |

Icon size is 24dp (20dp inside a 36dp circle or icon tile, 18dp inline). Soft Brut draws icons at the text colour; Flow tints the back arrow and trailing actions with the accent.

## 6. Home

### 6.1 Soft Brut Home (mockup [`soft-brut/home`](design/android-art-themes/soft-brut/home.html))

One column, in this order.

| # | Module | Content | Data |
|---|---|---|---|
| 1 | Today's picks | Eyebrow with "1 / 7". A pile of three sleeves: the current pick in front (248dp, outlined, 4dp shadow), the next two behind it at 2.5° and 5°. Swipe left or right, or tap a back sleeve, to change pick. Title, then artist, year and genre. Get album (filled, wide), Save, the three-dot menu | `picks(10)` |
| 2 | In rotation | Round artist photos, 68dp, name beneath, side-scrolling; "All artists" opens Library | section 7 |
| 3 | Arrival | Up to two cards: cover 52, title, state in words, outlined progress bar. Hidden when empty | `AcquisitionHub` |
| 4 | Radio | The tile from N3: sky fill (`accent2`), radio icon, "Radio", "Last heard: FIP, 08:42", chevron. Opens Radio | `radioPlays()` |
| 5 | Recently added | Two-column cover grid, four albums | `shelf(Newest)` |
| 6 | Recently played | Cover shelf, 112dp | `shelf(Recent)` |
| 7 | Insight | One card: cover 88, tag, sentence, Play or Get, Why? | `insights` |
| 8 | Genres | Outlined chips, wrapping | `genres()` |
| 9 | Stat strip | One mono line between dashed rules: album count, added this month, "Stats →". Opens Library stats | `DashboardRules.hero` |

Frame 5 draws the states: a caution banner under the top bar when a service fails, the pile as three blank sleeves while picks load, and a sentence in place of In rotation when there is no listening yet. With no picks the pile is replaced by "Nothing recommended right now."

### 6.2 Flow Home (mockup [`flow/home`](design/android-art-themes/flow/home.html))

| # | Module | Content | Data |
|---|---|---|---|
| 1 | Segmented control | Picks, New, Played. It chooses what the carousel shows and remembers the choice | — |
| 2 | Cover carousel | The centred cover at 220dp with depth level 3; its neighbours at 160dp and 75% opacity, cut by the screen edge. Swipe to move; the title and actions under it follow the centred cover | Picks: `picks(10)`. New: `shelf(Newest)`. Played: `shelf(Recent)` |
| 3 | Title and actions | Centred title, then artist, year and genre. Picks: Get album (filled), Save, three dots. New and Played: Play (filled), Shuffle, three dots | as above |
| 4 | Artists | Portrait cards, 150dp wide, 3:4, radius 18, name over a dark fade; side-scrolling. "All" opens Library | section 7 |
| 5 | Insight | One white card: cover 88, tag, sentence, Play or Get, Why? | `insights` |
| 6 | Genres | Capsule chips in one side-scrolling row | `genres()` |
| 7 | Grouped list | One white card of rows with chevrons: each arrival (cover, state in words), Radio (last heard), Library (album count and added this month, opens Library stats) | `AcquisitionHub`, `radioPlays()`, `DashboardRules.hero` |

Frame 3 draws Played selected; frame 4 draws the loading, failing-service and no-listening states.

### 6.3 Dropped from Home in both themes

These stay available elsewhere and are unchanged for every other theme.

| Dropped | Where it lives |
|---|---|
| The large album count hero | One line: the stat strip (Soft Brut) or the Library row (Flow) |
| Stat cards (Listens 7 days, Never played, Waiting) | Library stats; the downloads badge carries Waiting |
| Your taste | Discover, Insights |
| Library in numbers (12-month chart) | Library stats |
| Server row | The banner when a service fails; Settings otherwise |

At 840dp and wider, both themes keep the existing two-pane rule: picks (pile or carousel) and artists in the primary pane, everything else in the secondary. This is not drawn.

## 7. Artist data on Home

"In rotation" and "Artists" show the artists the owner has been playing. No endpoint returns that list, and none is needed:

- Take `shelf(Shelves.Recent, 20)` and `shelf(Shelves.Frequent, 20)`, already loaded for Home shelves; keep the distinct artists in order of first appearance, recent first, up to eight.
- The photo is the existing `GET /api/artist-image` route, the one Library artist rows and the artist page use.
- An artist with no photo gets the theme's placeholder (initials on `raised`), never another artist's or an album's picture.
- With fewer than three artists the module shows its sentence instead ("Play a few albums and the artists you return to appear here.").

The rule is a pure function (`HomeArtists.from(recent, frequent)`) with a unit test. A server-ranked "most played artists" list would be better and is noted as a possible later proposal; it is not part of this work.

## 8. Dependencies and open points

| # | Point | Proposed answer |
|---|---|---|
| D1 | `BrutalShape(radius, outline, shadow)` takes whole numbers; Soft Brut needs a 1.5dp outline | Change the three fields to `Float` (existing values are unchanged). If the owner prefers no change to the class, Soft Brut uses 2dp |
| D2 | Colours from the cover (the Flow wash) | Use the Palette library the player already uses for artwork tint if present; otherwise the wash is `raised` and the colour is a later refinement. Confirm at step F1 |
| D3 | Blur behind the Flow bars | Not in the first build (section 4) |
| D4 | The font pair when a theme is chosen | Suggested, not forced (section 5). The owner may prefer each theme to lock its pair |
| D5 | Dark variants | Not designed. Each theme is one light palette, as Round 3 did; a night palette for each is a later proposal |
| D6 | The Flow accent was darkened from `#E8590C` to `#C2410C` for contrast | Needs the owner's agreement, since it differs from the chosen mockup |

## 9. Every page, and the files to build from

**Mockups.** Each name has an `.html` and a `.png` in [`docs/design/android-art-themes/soft-brut/`](design/android-art-themes/soft-brut/) and [`docs/design/android-art-themes/flow/`](design/android-art-themes/flow/). Frames are 360 by 780dp, and 1 CSS px is 1dp, so sizes can be read from the stylesheet or measured in the browser.

| File | Frames | What each theme does there |
|---|---|---|
| `home` | Home at each scroll position, and its states | Section 6 |
| `discover` | Lists, Insights, the taste sheet | Soft Brut: two-column cards, cover on top, Get, Save and three dots under it. Flow: one-column white cards, cover 112 at the left. Both: list names as chips, taste card with ranked bars, lens cards |
| `library-search` | Library artists, Library albums, Search results | Artists as rows with round photos; albums as a two-column cover grid; Search groups (Artists, Albums, Songs) with the owned state in words and Get on missing albums |
| `album-artist-genre` | Album (owned), Artist, Genre | Soft Brut album: cover at the left on a tilted lavender second sleeve; the playing song is a filled row. Flow album: centred cover over the wash, centred title, capsules. Soft Brut artist: round photo beside the name. Flow artist: full-width photo with the name and Play over a dark fade |
| `player` | Now Playing, Queue, Lyrics | Soft Brut: outlined cover, outlined seek bar with a block thumb, outlined square buttons, lavender Play. Flow: cover with depth over the wash, 4dp seek line, plain glyphs, round ink Play |
| `radio` | Stations, live radio, Heard on radio | Station rows with logo tiles; the live screen with the station tile, the song heard and Get this song; Heard rows with Get, Requested or In your library |
| `downloads-stats-server` | Downloads, Library stats, Server | One card per download with the four-step tracker and its action row; charts drawn with the theme's chart roles; services with their state in words |
| `settings` | Settings, Appearance, Equalizer, Crossfade | Grouped rows; theme tiles with the selected one marked by the theme's own selection (shadow in Soft Brut, accent ring in Flow) |
| `sheets` | Pick menu, Dismiss confirmation, snackbar with Undo | The theme's sheet and snackbar shapes |
| `components` | Token swatches, the type scale and every control | The reference board for sections 3 and 4 |

Not drawn: tablet widths; the album page for an album that is not owned (Play becomes Get album; nothing else moves); the album Booklet, cover picker and paths sheets, the artist paths panes and the Sonic path sheet (each takes the theme's sheet, list and button looks, with no new arrangement); empty and error states other than those on `home` frame 5 and 4; motion (both themes use the tokens in `theme/Motion.kt` unchanged, plus the two gestures in section 6).

**Files an implementer can use directly**

| File | Use |
|---|---|
| [`soft-brut.css`](design/android-art-themes/soft-brut.css) | The Soft Brut tokens (first block) and the exact look of every component: sizes, radii, outline, shadow, fills. Read it as the measurement sheet |
| [`flow.css`](design/android-art-themes/flow.css) | The same for Flow, including the three depth levels and the bar fill |
| [`shared.css`](design/android-art-themes/shared.css) | Structure shared by both: the phone frame, row heights, grids. Also the stand-in artwork, which is not for the app |
| [`_src/build.py`](design/android-art-themes/_src/build.py) | Writes every mockup page. The page content is written once and drawn by both stylesheets, which shows which differences are look and which are arrangement. Home is the one page composed per theme (`sb_home`, `fl_home`). Run `python3 build.py` to rebuild, or `python3 build.py sb home` for one page; it needs Google Chrome only for the PNGs |

The CSS is not shipped in the app. It is the spec in a form that can be measured, and the web client is not part of this proposal.

**Where the code would go** (new files only, so no other theme's file changes shape)

| Theme | New files | Existing files that gain a branch |
|---|---|---|
| Soft Brut | `ui/common/CoverStack.kt` (outline recipe, sleeve pile, tiles), `ui/home/CoverStackHome.kt`, `ui/player/CoverStackPlayer.kt` | `theme/Palette.kt` (palette, `Layout.CoverStack`), `home/HomeScreen.kt`, `NavIsland.kt`, `NavRules.kt`, `player/NowPlayingSheet.kt`, `player/SeekBar.kt`, `player/MiniPlayer.kt` |
| Flow | `ui/common/FlowKit.kt` (capsules, grouped list, segmented control, depth), `ui/home/FlowHome.kt`, `ui/player/FlowPlayer.kt` | The same list, plus `theme/Theme.kt` for the `flow` font pair |
| Both | `ui/home/HomeArtists.kt` (section 7) with its test | — |

## 10. Build steps

Each step is one PR with its own tests, in this order. Soft Brut and Flow are independent after step 0.

| Step | Objective | Acceptance |
|---|---|---|
| **0** Shared groundwork (merged, PR #1005) | `HomeArtists` and its test; `BrutalShape` accepts 1.5 (D1); the "existing layouts unchanged" test | Tests pass; no screen looks different |
| **S1** Soft Brut palette and shell (merged, PR #1006) | Palette `softbrut`, `Layout.CoverStack`, the outline recipe, navigation bar, mini player, buttons, chips, tabs, lists, sheets, snackbar | `soft-brut/components` matched; the theme can be chosen in Appearance; contrast test passes |
| **S2** Soft Brut Home (merged, PR #1007) | Section 6.1 | `soft-brut/home` matched in all five frames; Get, Save and the menu work on the front sleeve |
| **S3** Soft Brut pages | Album, Artist, Genre, Discover, Library, Search | Their mockups matched |
| **S4** Soft Brut player and the rest | Now Playing, Queue, Lyrics, Radio, Downloads, Stats, Server, Settings, Equalizer, Crossfade | Their mockups matched; closeout |
| **F1** Flow palette and shell | Palette `flow`, `Layout.Flow`, font pair `flow`, depth levels, capsules, grouped list, segmented control, floating bars; settle D2 | `flow/components` matched |
| **F2** Flow Home | Section 6.2 | `flow/home` matched in all four frames |
| **F3** Flow pages | Album (with the wash), Artist, Genre, Discover, Library, Search | Their mockups matched |
| **F4** Flow player and the rest | As S4 | Their mockups matched; closeout |

## 11. Verification for each build step

- Unit tests for every pure rule added (artist list, carousel index, pile order), and the palette contrast test extended to the two new palettes. Focused tests only, with JDK 17 (`docs/DEVELOPMENT_WORKFLOW.md`).
- The unchanged-layout test from step 0 stays green in every step.
- A screenshot of each built screen beside its mockup PNG in the PR, and a list of anything dropped.
- The owner checks each step on the phone before the next one starts.
