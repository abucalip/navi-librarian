# Index theme for Android: design system and build plan

Status: **design approved by the owner** (2026-11-17); every decision in section 13 is decided as proposed. **I0 is done** (section 11a; every missing server row is built) and **I1 (palettes, pair, shell) is built in a PR** (`ui/common/IndexKit.kt`, `IndexIcons.kt`, `IndexShell.kt`, `ui/theme/IndexMotion.kt`); I2 to I6 are not built. This document is the spec that implementing agents build from. The mockups beside it are the spec for every screen ("the mockups are the spec", Round 3 owner rule).

Package: [`docs/design/index/`](design/index/). Start with its [`README.md`](design/index/README.md). The shared mockup kit is [`docs/design/_kit/`](design/_kit/).

## 1. What the owner asked for

1. Index was option C of the 16 November proposal (Gallery, Aura, Index). On 2026-11-17 the owner brought it back alongside Bento ([`BENTO_THEME.md`](BENTO_THEME.md)).
2. The owner kept **all four palettes**:
   - **Signal Blue**, the original (day, the default);
   - **Newsprint Red** (day);
   - **Graphite Orange** (night);
   - **Field Green** (day).
3. The owner asked for:
   - mockups of every page in one palette, including the album and artist **Paths** pages;
   - the other palettes as codes and scripts;
   - detailed instructions for the animations (section 8).
4. Every mockup is drawn in **Signal Blue**. The other three palettes are **colour variations only**. [`pages/palettes`](design/index/pages/palettes.html) shows Home in all four, generated from `tokens.json`.

## 2. Rules

1. **Ownership.** Index is one new `Layout.Index` shared by its four palettes. Every composable it changes is reached through an `isIndex()` branch and lives in Index's own files (section 11). No shared composable changes what it draws for any other layout. `ExistingLayoutsTest` must still pass.
2. **Behaviour is unchanged** (D-023). These stay reachable, with text labels:
   - Get album, Save, Not this album, Never suggest this artist;
   - Play, and Dismiss with its confirmation;
   - the downloads badge and Settings;
   - the mini player and the four destinations.
3. **The mockups are the spec.** Build each screen element by element from its mockup. List anything dropped in the PR.
4. **Artwork first.** Square covers and photos are the only pictures; colour on controls carries meaning.
5. **Contrast.**
   - Every palette passes `PaletteTest`.
   - The Index roles pass [`_src/check_contrast.py`](design/index/_src/check_contrast.py). All four pass today.
   - The existing rules still apply: 48dp touch targets, state never shown by colour alone, Remove animations respected, missing data said in words.

## 3. Identity in six rules

1. **A Swiss index of your music.** A strict grid with 16dp margins, a four-column strip with an 8dp gap, and left alignment everywhere. Nothing is centred except transport glyphs.
2. **Numbers do the organising.** Every list is numbered in mono (01, 02…): pick numbers, steps, stations, downloads, settings rows. Counts sit as superscripts in `accent` beside headings ("Picks¹²"). The lead pick carries a large "01" in `accent`. Track numbers are large and pale (`edge`).
3. **Rules, not boxes.**
   - A heavy 2dp `text` rule opens each section and sits under each page head.
   - Rows are divided by 1dp `edge` rules.
   - Nothing has a shadow. The radius is at most 3dp (buttons); art, tags, badges, switches and sheets are square (sheets 6dp at the top).
4. **Big tight type plus mono data.** Inter Tight 800 for heads and numerals, Inter for reading, IBM Plex Mono caps for every data key, meta line, tab and link.
5. **One signal colour.** `accent` marks:
   - the selected tab and the source switch;
   - the bar's signal block and the progress line;
   - counts, numbers and links;
   - "Owned: No".

   `control` fills primary buttons. In Signal Blue that is ink; in the three new palettes it equals the signal colour.
6. **The ink strip.** The mini player is a solid `strip` band with the progress along its top edge, sitting on a white four-cell bar with mono labels.

## 4. Colour

### 4.1 Roles

The CSS variables in [`palettes.css`](design/index/palettes.css) use the `Palette` field names. Index needs no new `Palette` field. Its own colours, the **tones** (the player strip and the insight block), live in `IndexTones` in `ui/common/IndexKit.kt`, keyed by palette id (decision I1).

| Role | Used for |
|---|---|
| `ink` | Page background |
| `rail`, `surface`, `mat` | The bar under the strip, Now Playing and live radio pages, sheets, the search field. `mat` = `surface` (no mats) |
| `raised` | Skeletons, station plates without a logo |
| `edge` | Row rules, tab baseline, seek track, track numbers, switch off |
| `edgeStrong` | Chart baseline |
| `text` | Text, heavy rules, the sheet handle, the quality tag fill |
| `textMuted` | Meta lines, inactive tabs and bar labels |
| `control` / `onControl` | Primary buttons, Play, switch on |
| `accent` / `onAccent` | Selected tab bar, signal block, counts, numbers, links, the playing row, the badge, first chart series, On air tag |
| `ok`, `caution`, `chartRedText`, `info` | State words: In library, needs attention, failed or Dismiss, information |
| tone `strip` / `onStrip` / `stripMuted` / `stripProgress` | The mini-player strip, the Queue's now-playing band and the snackbar |
| tone `insight` / `onInsight` / `insightLabel` | The This week block |

### 4.2 The four palettes

Single source: [`tokens.json`](design/index/tokens.json). On all four: `family = Classic`, `shape = null`, `layout = Layout.Index`, `suggestedFontId = "index"`, `minAccentContrast = 4.5`.

| Role | Signal Blue (day) | Newsprint Red (day) | Graphite Orange (night) | Field Green (day) |
|---|---|---|---|---|
| `ink` | `#F6F7F8` | `#F1EDE4` | `#141516` | `#EDF1EB` |
| `rail` | `#FFFFFF` | `#FBF9F4` | `#1D1F21` | `#FFFFFF` |
| `surface` | `#FFFFFF` | `#FBF9F4` | `#1D1F21` | `#FFFFFF` |
| `mat` | `#FFFFFF` | `#FBF9F4` | `#1D1F21` | `#FFFFFF` |
| `raised` | `#ECEEF0` | `#E7E1D5` | `#26292B` | `#E0E7E1` |
| `edge` | `#D9DCE0` | `#D8D1C4` | `#2E3134` | `#CFD8D0` |
| `edgeStrong` | `#80868F` | `#857E71` | `#767A78` | `#76837B` |
| `text` | `#0B0C0E` | `#141210` | `#EDEEEA` | `#0E1A14` |
| `textMuted` | `#5B6068` | `#5C564E` | `#A0A39E` | `#4F5C55` |
| `control` | `#0B0C0E` | `#B81F18` | `#FF6A1A` | `#086F43` |
| `onControl` | `#FFFFFF` | `#FFFFFF` | `#141516` | `#FFFFFF` |
| `accent` | `#2B4BFF` | `#B81F18` | `#FF6A1A` | `#086F43` |
| `onAccent` | `#FFFFFF` | `#FFFFFF` | `#141516` | `#FFFFFF` |
| `ok` | `#1B6B3A` | `#1B6B3A` | `#8FD6A0` | `#1B6B3A` |
| `caution` | `#8A5300` | `#7F4A00` | `#F2C45A` | `#7F4A00` |
| `chartRed`, `chartRedText` | `#B3261E` | `#9E1B14` | `#FF8A73` | `#B3261E` |
| `info` | `#1F5A8A` | `#1F5A8A` | `#8FB8E8` | `#1F5A8A` |
| `chart2` | `#80868F` | `#857E71` | `#767A78` | `#76837B` |
| `chart3` | `#D9DCE0` | `#D8D1C4` | `#3A3E41` | `#CFD8D0` |
| tone `strip` | `#0B0C0E` | `#141210` | `#EDEEEA` | `#0E1A14` |
| tone `onStrip` | `#FFFFFF` | `#FBF9F4` | `#141516` | `#FFFFFF` |
| tone `stripMuted` | `#A7ACB4` | `#B4ADA2` | `#55585C` | `#A9B8AF` |
| tone `stripProgress` | `#2B4BFF` | `#FF6A5C` | `#C2410C` | `#4CC98D` |
| tone `insight` | `#0B0C0E` | `#B81F18` | `#FF6A1A` | `#0E1A14` |
| tone `onInsight` | `#FFFFFF` | `#FFFFFF` | `#141516` | `#FFFFFF` |
| tone `insightLabel` | `#AEB4FF` | `#FFE1DD` | `#3A1A08` | `#8FE0B5` |
| `id` | `index` | `index_newsprint` | `index_graphite` | `index_field` |
| Label | Index · Signal Blue | Index · Newsprint Red | Index · Graphite Orange | Index · Field Green |

Add the three day palettes to `Palettes.Light` and Graphite Orange to `Palettes.Dark`. When "Follow the phone" is on and Index is chosen, the defaults are Signal Blue for light and Graphite Orange for dark.

**Changed from the proposal for contrast:**

- Newsprint Red's signal `#C8231B` → `#B81F18`, and Field Green's `#0B7A4B` → `#086F43`: both measured under 4.5:1 on `raised`.
- The progress line on the strip got its own tone (`stripProgress`), because the signal colour is too dark on a near-black strip (Newsprint, Field) and too light on Graphite's light strip:
  - Newsprint `#FF6A5C`;
  - Field `#4CC98D`;
  - Graphite `#C2410C`.

### 4.3 Contrast (checked)

`python3 docs/design/index/_src/check_contrast.py` runs 38 to 39 checks per palette:

- the `PaletteTest` rules;
- `control` and `accent` on every background;
- `onStrip` and `stripMuted` on `strip`, and `stripProgress` on `strip` at 3:1;
- `onInsight` and `insightLabel` on `insight`.

**All four pass.** The lowest result is Signal Blue's muted text over pastel washes, at 4.67:1.

## 5. Type

### 5.1 Fonts

**Index adds no font file.** All three faces are already in `android/app/src/main/res/font/`:

- `inter_tight_800.ttf`;
- `inter_variable.ttf`;
- `ibm_plex_mono_400.ttf`, `_500` and `_600`.

The mockups load those exact files.

### 5.2 Font pair

- Add `FontPairs.Index`: id `index`, label "Index", title "Inter Tight", body "Inter", `mono` IBM Plex Mono, `monoName` "IBM Plex Mono", `numeral` = the title face, `numeralWeight = FontWeight.ExtraBold`.
- It differs from `brut_swiss` (Inter Tight and Inter) only by naming IBM Plex Mono as its mono.
- Index's text styles live in `IndexKit.kt` and read faces through `LocalFontPair`, so another pair chosen in Appearance keeps Index's layout (D4).
- Two counts change: `twelvePairsWithUniqueIdsAndDiscairFirst` moves up by one, and the `monoName` set check gains `index`.

### 5.3 Type scale

From `tokens.json` → `type`. Sizes and line heights are in sp.

| Style | Face | Weight | Size / line | Tracking | Used for |
|---|---|---|---|---|---|
| Wordmark | Inter Tight | 800 | 22 / 24 | −0.035em | "discair" |
| Display | Inter Tight | 800 | 52 / 44 | −0.035em | Page heads (Picks, Discover, Library…) |
| Page title | Inter Tight | 800 | 46 / 42 | −0.035em | Album title |
| Lead title | Inter Tight | 800 | 34 / 31 | −0.035em | The lead pick, artist name, sheet titles (30) |
| Index numeral | Inter Tight | 800 | 36 / 36 | −0.02em | "01" beside the lead pick, in `accent` |
| Section | Inter Tight | 800 | 24 / 24 | −0.035em | Section heads |
| Numeral | Inter Tight | 800 | 92 / 72 | −0.04em | The anniversary number, Crossfade; Stats at 44 |
| Track number | Inter Tight | 800 | 20 / 24 | −0.02em | Track list, in `edge` |
| Time | Inter Tight, `tnum` | 800 | 20 / 24 | −0.02em | Seek times on Now Playing |
| Row title | Inter | 600 | 15 / 20 | 0 | Rows |
| Body | Inter | 400 | 14 / 21 | 0 | Reasons, sentences |
| Data value | Inter | 500 | 12.5 / 18 | 0 | Values in a data list |
| Button | Inter | 600 | 14 / 14 | 0 | Buttons; small 13 |
| Label | IBM Plex Mono caps | 500 | 10.5 / 14 | +0.06em | Eyebrows, data keys, meta lines, tabs, links ("ALL →") |
| Nav label | IBM Plex Mono caps | 500 | 9.5 / 12 | +0.07em | Bar labels |
| Count | IBM Plex Mono | 600 | 13 / 13 | 0 | Superscript count, `accent` |

## 6. Icons

[`icons/`](design/index/icons/) holds the same 48 glyphs as Bento, drawn with a **2dp stroke, square caps and mitred joins**, plus [`icons/IndexIcons.kt.txt`](design/index/icons/IndexIcons.kt.txt), a ready `IndexIcons` object.

- **Builder.** Use the `ArtIcons` builder with `strokeLineWidth = 2f`, `StrokeCap.Square` and `StrokeJoin.Miter`.
- **Sizes:**
  - 22dp default;
  - 18dp in buttons and chevrons;
  - 26dp transport.
- **Colour:**
  - `text` in the top bar and rows;
  - `onStrip` in the strip;
  - `textMuted` on idle bar cells and `text` on the selected one;
  - `onControl` on fills.
- **No backgrounds.** Icons never sit on circles or tiles.

## 7. Components

Every measurement is in [`index.css`](design/index/index.css) (1 CSS px = 1dp). The board is [`pages/components`](design/index/pages/components.html).

| Component | Spec |
|---|---|
| Top bar (Home and tabs) | 54dp. Wordmark at 16dp, the mono date beside it, then downloads (square `accent` badge, 15dp) and settings icon buttons |
| Page top bar | 52dp. Back left, a mono catalogue line in the middle ("ALBUM 0418 / 1284", "ARTIST 0031 / 312", "NOT IN YOUR LIBRARY"), an action right |
| Page head | Display title with an `accent` count superscript. Right-aligned mono source switch (PICKS · NEW · PLAYED) with a 3dp `accent` bar under the selected word. Then the 2dp `text` rule, 12dp below |
| Lead pick | Grid 168 + 1fr, 12dp gap: square cover; right column "01" (Index numeral), Lead title, and a data list (mono keys ARTIST / YEAR / GENRE / OWNED; Owned "No" in `accent`) |
| Strip of picks | Four columns, 8dp gap, square covers with mono "02"–"05" under them |
| Section head | 28dp above; 2dp `text` rule; Section title, a mono meta word, a mono `accent` link pushed right |
| Row | Grid: number (26, mono `accent`) · art 48 square · title over mono meta · trail. Min 64dp, 1dp `edge` rule. Variants: no number, no art |
| Data row (album) | Four-column key/value grid between 1dp rules (ARTIST, YEAR, LENGTH, FORMAT) |
| Track row | 40 / 1fr / time / 36: big pale number (playing: the bars in `accent` and the title in `accent` 700), mono time, three dots. Min 54dp |
| Primary button | 44dp, radius 3, padding 16, `control` fill, Inter 600 14. Small 36dp |
| Ghost button | 1.5dp inset `edge`, `text` label |
| Get states | Idle "Get" (primary) · pending "Getting" (ghost, turning icon) · requested REQUESTED (mono, muted) · owned IN LIBRARY (mono, `ok`) · failed "Try again" (ghost, `chartRedText`) · none NO ARTIST (mono, muted) |
| Tabs | Mono caps, 16dp apart, 40dp high, 1dp `edge` baseline, 3dp `accent` bar under the selected tab. Lenses, library views, path kinds, presets |
| Tag | Mono 10 caps on a square `text` fill with `ink` letters (FLAC 16/44.1); On air in `accent` |
| Search field | 52dp, square, 2dp `text` inset outline on `surface`; Inter 600 17 |
| Switch | 44×24 square; off `edge` with a `surface` knob; on `control` with an `onControl` knob |
| Seek | 6dp square track `edge`, `accent` played part, no thumb; times in Inter Tight 20 below |
| Tracker | Four 4dp segments, 4dp apart (`text` reached, `edge` ahead, `chartRedText` failed), mono step names |
| Insight block | `insight` fill, 16dp padding; a 92sp numeral spanning two rows, the mono label in `insightLabel`, a 16sp 600 sentence |
| Charts | Square columns, `chart3`, the current one `accent`; 1dp `edgeStrong` baseline; ranked bars 6dp |
| Dock | The strip: 56dp, `strip` fill, 38dp cover, title over a mono meta line in `stripMuted`, pause; a 3dp `stripProgress` line along the top. Under it the bar: 60dp on `rail`, a 1dp `edge` top rule, four cells (icon 22 over a mono label), and a 3dp `accent` signal block, 14% of the width, on the top edge over the selected cell |
| Sheet | `surface`, top radius 6, a 32×3 `text` handle. Header grid 72 + 1fr: art, mono eyebrow, Lead title (30), then a 2dp `text` rule. Options: 62dp rows lettered A, B, C in mono `accent`, with a trailing glyph. Scrim rgba(10,10,12,.5) |
| Snackbar | 52dp, radius 3, `strip` fill, `onStrip` text, UNDO in mono `stripProgress` |
| Skeleton | `raised` squares; no shimmer |

## 8. Motion: what moves and how to build it

Values are in `tokens.json` → `motion`. Try them on the live page [`pages/motion`](design/index/pages/motion.html), which covers the directional tab slide, the signal block, the row cascade and the numeral roll.

Index's character is **firm and directional**:
- things slide along the axis they belong to and stop without overshoot;
- the one curve is `firm` = cubic-bezier(0.77, 0, 0.18, 1);
- there are no springs, no scale and no fades on navigation.

### 8.1 Ground rules for every animation

1. **Route all durations through the existing helpers.**
   - Add `Layout.Index` to `MotionRules.familyFor` → `MotionFamily.Standard`.
   - Read `rememberReducedMotion()` once per screen.
   - Pass every duration through `MotionRules.duration(ms, MotionFamily.Standard, reduced)`.
2. **`ui/theme/IndexMotion.kt`** (pure, like `GalleryMotion.kt`):
   ```kotlin
   object IndexMotion {
       val Firm = CubicBezierEasing(0.77f, 0f, 0.18f, 1f)
       val Settle = CubicBezierEasing(0.2f, 0f, 0f, 1f)   // rowCascade, sheetIn
       val Exit = CubicBezierEasing(0.4f, 0f, 1f, 1f)     // sheetOut
       const val TAB_SLIDE_MS = 380; const val PUSH_MS = 340; const val ROW_MS = 300; const val ROW_STAGGER_MS = 20
       const val ROW_MAX = 12; const val ROW_FROM_DP = -12; const val SIGNAL_MS = 380; const val SOURCE_BAR_MS = 260
       const val PLAYER_RISE_MS = 420; const val PLAYER_FALL_MS = 320; const val SHEET_IN_MS = 260; const val SHEET_OUT_MS = 200
       const val NUMERAL_MS = 420; const val NUMERAL_DIGIT_DELAY_MS = 40; const val RULE_MS = 360; const val SNACK_MS = 220
       /** Generic, so the same call serves Float, Dp and IntOffset (slides) animations. */
       fun <T> firm(ms: Int, reduced: Boolean, delayMs: Int = 0): TweenSpec<T> =
           tween(MotionRules.duration(ms, MotionFamily.Standard, reduced), if (reduced) 0 else delayMs, Firm)
       fun tabDirection(from: Int, to: Int): Int = if (to > from) 1 else -1   // bar order: Home, Discover, Library, Search
   }
   ```
   `IndexMotionTest` pins every constant to `tokens.json`.
3. **Shorthand in the table below.** A plain `tween(ms, …)` in section 8.2 stands for `IndexMotion.firm<T>(ms, reduced)` (or the same tween with the `Settle` or `Exit` curve, through `MotionRules.duration`). Never call Compose's own `tween` directly in Index code.
4. **No continuous motion**, except the playing bars and the pending Get icon. Both run only while their state holds and the screen is resumed.

### 8.2 The animations

| # | Moment | Values | How to build it in Compose |
|---|---|---|---|
| 1 | **Tab change** (bar) | `tabSlide` 380ms Firm; full width; no fade | In the NavHost, for routes that are bar destinations: `enterTransition = { slideIntoContainer(if (dir > 0) SlideDirection.Left else SlideDirection.Right, IndexMotion.firm<IntOffset>(380, reduced)) }` and `exitTransition = { slideOutOfContainer(…same direction…, IndexMotion.firm<IntOffset>(380, reduced)) }`. Here `dir = IndexMotion.tabDirection(indexOf(initialState), indexOf(targetState))`. Add no `fadeIn`/`fadeOut`. When reduced, use `EnterTransition.None` / `ExitTransition.None` |
| 2 | **Push** (open album, artist, genre, settings page) | `pushSlide` 340ms Firm; enter from +30% width with a fade; exit to −12% and dim to 85% | `enterTransition = slideInHorizontally(tween(340, easing = Firm)) { (it * 0.3f).toInt() } + fadeIn(tween(200))`; `exitTransition = slideOutHorizontally(tween(340, easing = Firm)) { -(it * 0.12f).toInt() }`. For the dim, draw a scrim on the leaving page with `graphicsLayer { alpha }`, or use `fadeOut(targetAlpha = 0.85f)`. `popEnter`/`popExit` mirror them. Covers keep `Modifier.sharedCover(routeKey)`, so a tapped cover travels to the album's 200dp cover |
| 3 | **Signal block** (bar) | `signalBlock` 380ms Firm | One `Box` 3dp × 14% of the bar width at the top edge. `val x by animateDpAsState(cellCenter(selected) - blockWidth / 2, tween(380, easing = Firm))` → `Modifier.offset { IntOffset(x.roundToPx(), 0) }`. Selected label and icon colours change at once (no tween), as the mockup does |
| 4 | **Source switch / tabs bar** | `sourceBar` 260ms Firm | The 3dp bar under the selected word moves and resizes to it. Measure each word with `onGloballyPositioned`, then `animateDpAsState` for x and width. Tabs (lenses, path kinds) use the same code |
| 5 | **Row cascade** (a list arrives) | `rowCascade` 300ms Settle; from −12dp x and alpha 0; stagger 20ms; at most 12 | Per visible row `i < 12`: `Animatable(0f)`, then `delay(i * 20L)`, then `animateTo(1f, tween(300, easing = Settle))`, read in `graphicsLayer { translationX = (1 - p) * -12.dp.toPx(); alpha = p }`. Run it on the first arrival of a list and when a tab or lens changes the list, not on scroll and not when Back returns. In `LazyColumn` use stable keys and `Modifier.animateItem(fadeInSpec = null, placementSpec = tween(260, easing = Firm))` for later inserts and removals (Dismiss, Undo) |
| 6 | **Rules draw** | `ruleDraw` 360ms Firm | The page-head rule and each section rule draw left to right on arrival: `Animatable(0f)` → `graphicsLayer { scaleX = p; transformOrigin = TransformOrigin(0f, 0.5f) }`. They start with the row cascade |
| 7 | **Numeral roll** | `numeralRoll` 420ms Firm, 40ms per digit | For the anniversary number, Stats numerals, the crossfade seconds and download percentages. Split the formatted number into characters. Each digit is `AnimatedContent(targetState = digit, transitionSpec = { (slideInVertically(IndexMotion.firm<IntOffset>(420, reduced, delayMs = index * 40)) { it } togetherWith slideOutVertically(IndexMotion.firm<IntOffset>(420, reduced)) { -it }) using SizeTransform(clip = true) })`. On first arrival the old value is blank, so digits rise in. The spoken label is the final value |
| 8 | **Now Playing opens / closes** | `playerRise` 420ms Firm; `playerFall` 320ms Firm | A full white page slides up from the strip: `slideInVertically(tween(420, easing = Firm)) { it }`, no fade. The strip's 38dp cover flies to the 328dp cover. The player is a dialog window, so draw the flight by hand from the strip cover's bounds, as `GalleryFlight` does: interpolate the rect only, square corners throughout. The bar stays; the strip slides away under the page |
| 9 | **Sheets** | `sheetIn` 260ms Settle; `sheetOut` 200ms Exit; scrim 200ms | Firm stop, no bounce. Material's `ModalBottomSheet` timing cannot be set (as Gallery found); decision I4. The lettered options cascade (#5) once the sheet is up |
| 10 | **Snackbar** | `snackIn` 220ms Firm from 56dp below; hold 4s | `val off = with(LocalDensity.current) { 56.dp.roundToPx() }`, then `slideInVertically(IndexMotion.firm<IntOffset>(220, reduced)) { off }` with no fade; exit `slideOutVertically(IndexMotion.firm<IntOffset>(180, reduced)) { off }` |
| 11 | **Get morph** | 220ms Firm | `AnimatedContent(state)` with `fadeIn(tween(120)) togetherWith fadeOut(tween(80)) using SizeTransform { _, _ -> tween(220, easing = Firm) }`. Pending: the refresh icon turns with an infinite rotation, only in that branch |
| 12 | **Seek and progress** | linear | The strip's top line and the seek fill track position directly (no tween), as today's `SeekBar` does |
| 13 | **Playing bars** | `playingBars` 800ms, 3 → 12dp, phases 0 / −300 / −600 | As Bento #13, in `accent`, 3dp wide; static at 7dp when reduced |

### 8.3 Order of work

| Step | Animations |
|---|---|
| I1 | #3 signal block, #4 tabs bar, #9 sheets, #10 snackbar, #1 tab slide, #2 push |
| I2 | #5 row cascade, #6 rules, #7 numerals, #11 Get morph |
| I5 | #8 player, #13 playing bars |

Each step has an `IndexMotionTest` that pins its values to `tokens.json`, and a test that every duration is 0 when reduced.

## 9. Home

Mockup: [`pages/home`](design/index/pages/home.html) (four frames). From top to bottom:

| # | Section | Content | Data |
|---|---|---|---|
| 1 | Top bar | Wordmark, mono date, downloads with badge, settings | as today |
| 2 | Head | "Picks¹²" (count of the source), source switch PICKS · NEW · PLAYED (remembered, as Flow) | `picks`, recently added, recently played |
| 3 | Lead | The first item: square cover, "01", title, data list (Artist, Year, Genre, Owned). Actions: Picks → Get album, Save, three dots; New and Played → Play, Shuffle, three dots | as above |
| 4 | Strip | Items 02–05 in four columns; tap opens, long press makes it the lead | as above |
| 5 | Played | This week; three numbered rows with play counts; ALL → | recently played |
| 6 | Artists | You return to; four portrait photos (74 × 92) with album counts | `HomeArtists` |
| 7 | Radio | Four station plates (initials when no logo) with last heard ("TODAY" in `accent`); "Heard on FIP this morning" with two rows (In library / Requested / Get) | as Gallery section 9, row 6 |
| 8 | This week | The insight block: numeral, label, sentence; Play and "Why this?" | insight source |
| 9 | Arrivals | In progress with percent and tracker; arrived today; DOWNLOADS → | `AcquisitionHub` |
| 10 | Genres | Mono caps names with `accent` counts | as today |
| 11 | Library line | Mono: albums · artists · hours this month →; opens Library stats. **The only stats on Home** | as today |

States (frame 4):
- a caution banner (2dp `caution` rule, warning icon, saved-copy time, Retry);
- skeleton squares while loading;
- "Play a few albums. What you play most is indexed here." when nothing has been played;
- the count shows "—" while unknown.

## 10. Every page and its file

Each page is an `.html` and a `.png` in [`docs/design/index/pages/`](design/index/pages/). Frames are 360 × 780dp. Rebuild them with `python3 docs/design/index/_src/build.py`.

| File | Frames |
|---|---|
| `home` | First screen; scrolled (Artists, Radio, Heard); end (This week, Arrivals, Genres, library line); states |
| `album-artist-genre` | Album owned with the fifth song playing (cover beside "05 / 10 PLAYING" and the data list, title, Play/Shuffle/Paths, tabs, numbered tracks); album not in the library (pick number, data grid, Get album/Save/Paths, Why, Similar); Artist (photo with data list, Top songs/Paths/Shuffle, numbered top songs, albums with GET under missing ones); Genre (head with count, artists, albums) |
| `paths` | **Album Paths** sheet: header (cover, PATHS · FROM, title, kinds and steps counts), kinds as tabs, numbered steps with the server's sentence and library state. **Album Paths step opened**: STUDIO CREW · STEP 01 / 04, the album, lettered reasons (A · MUSICIAN, B · ERA) under heavy rules, Open album / the person. **Artist Paths** sheet: kinds (Follow the musician, Sideman, Label, Composition, Scene), numbered musicians with photo, sentence and state. **Artist Paths step opened**: the musician with a data list (Plays, With, Owned), the link, Albums together with states, Open artist / Next step |
| `player` | Now Playing (white page, square cover, quality tag, seek, transport, LYRICS / QUEUE / EQ / FADE cells); Queue (now band in the strip colour, numbered up next); Lyrics with time stamps (stand-in text) |
| `discover` | Lists (lens tabs, numbered entries: genre, title, maker, reason, Get / Requested / Try again; Undo snackbar); Insights (taste bars, This week block, Never played); taste sheet (lettered options) |
| `library-search` | Albums (count tabs, sort line, two-column grid); Artists (rows with the A–Z index); Search (Artist, In your library, Not in your library, each with counts) |
| `radio` | Stations (numbered rows, the playing one with bars); Live radio; Heard |
| `downloads-stats-server` | Downloads (numbered, tracker, percent numerals, actions); Stats (four numerals under heavy rules, column chart); Server |
| `settings` | Settings (numbered rows in ruled groups); Appearance (the four palettes); Equalizer; Crossfade |
| `sheets` | Pick menu; song menu (with "Paths from this album"); Dismiss confirmation; snackbar with Undo |
| `extras-a` | Setup (numbered fields for both servers, Connect); Unavailable (Try again, Open Tailscale, Edit servers); the Newly added sheet; Discover's Saved list |
| `extras-b` | Album Booklet tab (page pager with a segment bar); cover picker sheet (numbered editions); Album Paths, Neighbours by ear (only with sonic data); Sonic path sheet from a Queue row |
| `palettes` | Home in all four palettes (colour only) |
| `components` | Token swatches for all four palettes, the type scale, controls, the dock and the 48 icons |
| `motion` | Live prototype: tab slide, signal block, row cascade, numeral roll |

Every route in `ui/Routes.kt` and every sheet the screens open has a frame. Not drawn: tablet widths, and empty or error states beyond Home's frame 4 (each uses the same banner, skeleton and one-line message).

**Paths behaviour stays as built.** The server is asked only when the sheet is open and a kind is chosen, and Back from an opened album returns to the sheet at the same step. Index changes only the drawing: numbered steps, lettered reasons, rules.

## 11. Where the code goes

| New file | Holds |
|---|---|
| `ui/theme/IndexMotion.kt` | Section 8 (pure) |
| `ui/common/IndexKit.kt` | `IndexTones`, text styles (5.3), page head, section head, rows, data list, key/value grid, buttons, `IndexGetButton`, tabs with the moving bar, tag, switch, tracker, insight block, numeral roll |
| `ui/common/IndexIcons.kt` | From `icons/IndexIcons.kt.txt` |
| `ui/common/IndexShell.kt` | Top bars, the strip and the bar with the signal block, sheet look, snackbar, the directional NavHost transitions |
| `ui/home/IndexHome.kt`, `IndexHomeRules.kt` | Section 9; the rules are pure (counts, number labels "01", the source head, last-heard words) |
| `ui/album/IndexAlbum.kt`, `ui/artist/IndexArtist.kt`, `ui/IndexGenre.kt` | Album, Artist, Genre |
| `ui/album/IndexAlbumPaths.kt`, `ui/artist/IndexArtistPaths.kt` | Paths steps and lettered reasons |
| `ui/discover/IndexDiscover.kt`, `ui/library/IndexLibrary.kt`, `ui/search/IndexSearch.kt` | Discover, Library, Search |
| `ui/player/IndexNowPlaying.kt`, `ui/player/IndexEqCrossfade.kt` | Now Playing, Queue, Lyrics, Equalizer, Crossfade |
| `ui/radio/IndexRadio.kt`, `ui/downloads/IndexDownloads.kt`, `ui/stats/IndexStats.kt`, `ui/settings/IndexSettings.kt` | Radio, Downloads, Stats, Server, Settings, Appearance |

These existing files each gain one `isIndex()` branch, the same list as Bento (`BENTO_THEME.md` section 11):

- `Palette.kt` (four palettes, `Layout.Index`), `Theme.kt` (font pair), `Motion.kt`;
- `MainShell.kt`;
- the screens, including `AlbumPathsSheet.kt`, `ArtistPaths.kt` and `PathPanes.kt`;
- the shared controls.

Add the `Index*` files to `ARCHITECTURE.md` in I1.

## 11a. Server data the theme needs: build what is missing

**Rule (owner decision, 2026-11-17).** If a theme element needs data or a route the server does not provide, the server part is **built**, not dropped and not faked on the phone. This applies to both Bento and Index.

1. **Audit first (step I0).** Before the first client step, the implementing agent checks every row of the table below against the current server code and the Android decoders, and marks each one *served* or *missing*. Rows marked *check* are the ones this spec could not confirm.
2. **Build the missing parts on the server.**
   - Each missing item becomes a server PR **before** the client step that draws it.
   - Domain logic stays server-side and the app only presents it.
   - New code goes in a new module in the owning package from `ARCHITECTURE.md` (`discovery/`, `intelligence/`, `integrations/`, `app/api/` for the route), never in `navidrome_server.py` (D-016). The module is tested by direct import, and gets an `ARCHITECTURE.md` row.
   - The route or field is added to the contract the client reads (`docs/ANDROID_CLIENT_CONTRACT.md`, `docs/SEARCH_CONTRACT.md` or `docs/SERVER_V2_CONTRACT.md`), with a recorded fixture under the existing fixture folders.
   - Prefer a new **optional field** on an existing response over a new route when the data belongs to that response. Clients ignore unknown keys (Android `ignoreUnknownKeys`, Swift `JSONDecoder`, the web), so nothing else changes.
   - Provider data uses batch lookups where the provider offers them, with the existing pacing, budgets and owner approvals (provider rule). Safety-critical code (acquisition, import, deletion, paths) keeps its own review rules.
   - Each server PR carries focused tests for the new code (never the full suite), and CI must pass on its final head.
3. **The client step that follows** decodes the new field with a fixture test, and draws the element only when the field is present. An older server that lacks the field hides the element and closes up the layout, with no placeholder number. Merge is not deployment: until the owner deploys the server, the element stays hidden on the phone, and the PR says so.
4. If building a route needs a new provider, more provider traffic than today's budgets, or a change to a parked decision, the agent stops and asks the owner before writing it.

| Element (page) | Data needed | Status | If missing, build |
|---|---|---|---|
| Lead pick data list (Artist, Year, Genre, Owned) (Home) | Genre and owned state per pick | check (picks carry artist and year) | Optional `genre` and `owned` on `/api/dashboard-picks` items |
| Played rows "14 plays" (Home), artist rows "212 plays" (Library) | Play count per album this week; per artist overall | check | Optional `play_count` (with a `window`) on recently played albums and on `/api/library/artists` items |
| Artist data list: Owned "5 of 9", Plays, Active "1967 – 2007" | Owned and total studio albums, plays, active years | check (the parked `missing_count` proposal; life span is in the knowledge store) | `owned_count`, `album_count`, `play_count` and `active_years` on `/api/artists/{key}`, the years from the stored MusicBrainz artist life span |
| Album head "0418 / 1284" | The album's position in the library by name | missing | An optional `library_position` and `library_total` on `/api/albums/{artist_key}/{album_key}`, from the owned index (decision I7: build it) |
| Album "05 / 10 PLAYING" | Track number and count | served (album tracks) | none; client only |
| Genres with counts (Home) | Albums per genre | check (`/api/dashboard/genres`) | An optional `album_count` per genre |
| Library tabs with counts "Artists 312 · Albums 1284 · Genres 48" | Totals | check (library pages return totals) | `total` on the first page of each library list; a genre total on `/api/dashboard/genres` |
| Downloads tabs "Active 3 · Done 14 · Failed 1" | Counts per state | served (`/api/acquisitions` lists every record) | none; client counts |
| Lyrics time stamps | Synced lyrics | check (the existing lyrics source) | When the source has synced lyrics, pass the times through; when not, the stamps are hidden and plain lyrics show |
| Artist Paths step data list "With 1968 – 1971", "Owned 2 of 4", Albums together | Years together, shared albums with states | check (`begin_year` is served) | Optional `years` and `shared_albums` on each `/api/knowledge/paths` stop (same as Bento) |
| Neighbours by ear segment meter | Closeness per neighbour | served (`matchCount`) | none |
| Server page "v0.3.9 · 84 ms" | Version and latency per service | check (`/api/health`) | Optional `version` and `latency_ms` per service (same as Bento) |
| Library "Unplayed", "Lossless" | Album filters (Bento needs them; Index can offer the same sort-line options once built) | missing | Same `filter` query as Bento; shared work, built once |

### I0 audit (2026-11-18, against `main` at `9e810191`)

Checked in the server code (routes, read models, stores) only. The Android decoders were **not** opened: "served" below means the server sends it. The missing rows are the follow-up server PRs, each before the client step that draws it. "Dropped" needs an owner answer.

| Element | Result | What the code shows | Build (own server PR) |
|---|---|---|---|
| Lead pick data list | **Served** | `/api/dashboard-picks` items carry `artist`, `album`, `genres` (up to 4), `release_group_mbid`. Picks exclude owned albums (`lens_week.week_pool`), so `owned` is always false and needs no field | none; the client reads `genres[0]` and shows "No" |
| Played "14 plays" (Home) | **Missing** | `/api/dashboard/albums/recent` items have no count; no per-week album play data on any route | Optional `play_count` (plays in the last 7 days) and `window` on `recent` shelf items, from ListenBrainz listens (owner decision I0-1, 2026-11-18: build the windowed count). **Built and merged**: PR #1192, `discovery/week_plays.py` |
| Artist rows "212 plays" (Library) | **Missing** | The owned index already sums plays per artist (`artist["plays"]`), but `library_page` items do not return it | Optional `plays` on `/api/library/artists` items (one line, no new provider traffic). **Built** (I0 server PR 2) |
| Artist data list: Owned, Plays, Active | **Missing** | `/api/artists/{key}` `artist` section has `album_count` (owned) only; no plays, no total, no years. `artist_life_span` (begin and end dates) is in the knowledge store | Optional `play_count`, `active_years` on the `artist` section; owned and total studio albums from the studio-albums catalog already on the page (`artist_sections`), shown only when it has loaded. New module under `discovery/search/`. **Built** (I0 server PR 3; `artist_facts.py`; `owned_count` and `album_count` sit on the `albums` section) |
| Album head "0418 / 1284" | **Missing** | Album `album` section has no position or total (decision I7: build) | Optional `library_position`, `library_total` on the `album` section, from the owned index. **Built** (I0 server PR 2; `discovery/search/album_position.py`) |
| Album "05 / 10 PLAYING" | **Served** | Tracks carry `track_number`; `song_count` on the header | none |
| Genres with counts (Home) | **Served** | `genre_tiles` returns `album_count` | none |
| Library tabs with counts | **Served** | Artists and albums pages return `total`; the genre count is the length of `/api/dashboard/genres` (limit up to 200) | none |
| Downloads tabs with counts | **Served** | `/api/acquisitions` lists every record | none (client counts) |
| Lyrics time stamps | **Served** | Read from Navidrome directly (`ANDROID_LYRICS_CONTRACT.md`): `synced` and per-line `start` | none; hide stamps for plain lyrics, as the contract says |
| Artist Paths step: With, Owned, Albums together | **Missing** | Stops carry `begin_year` and `anchor_begin_year` for `scene_path` only; no years together, no shared albums with states | Optional `years` and `shared_albums` on stops, in `intelligence/graph/` (same as Bento). **Built** (I0 server PR 4, #1195; `sideman_to_leader` stops, under `presentation`) |
| Neighbours by ear meter | **Served** (per spec; not re-read) | `matchCount` per spec | none |
| Server page "v0.3.9 · 84 ms" | **Missing** | `/api/health` answers `status`, `service`, `message` only; no version or latency | Optional `version` and `latency_ms` on `/api/health`, timed around the existing Navidrome `ping`. **Built** (I0 server PR 2) |
| Library "Unplayed", "Lossless" | **Missing** | `/api/library/albums` has `q`, `sort`, `order`, `cursor`, `limit`; no filter | Shared `filter` query with Bento, built once. Needs per-album play and quality data on the index entry. **Built** (I0 server PR 5, #1196; `discovery/search/album_filters.py`) |

**Stops and questions for the owner.** None of the builds above needs a new provider or more provider traffic. I0-1 is decided and built. Suggested server PR order, smallest first: `/api/health` fields; `plays` on library artists; `library_position` and `library_total`; artist page fields; path stop `years` and `shared_albums`; the library `filter`.

The table lists every element in the mockups whose data is not plainly on today's screens. When an audit finds another gap, add a row and follow the same rule.

## 12. Build steps

Each step is one PR with focused tests (JDK 17 for Android; never the full suite), in this order. I0 may be several server PRs; a server item can also be built just before the client step that needs it, as long as it merges first.

| Step | Objective | Acceptance |
|---|---|---|
| **I0** Server data audit and missing routes | Section 11a: check every row against the code; build each missing route or field as its own server PR (new module, contract entry, fixture, focused tests, `ARCHITECTURE.md`) | The audit table filled in I0's PR; every *missing* row either merged on the server or explicitly dropped by the owner; CI green on each server PR's final head |
| **I1** Palettes, pair, shell | `Layout.Index`; four palettes; `IndexTones`; `FontPairs.Index`; `IndexIcons`; `IndexKit`; strip and bar; top bars; sheet; snackbar; motion #1–#4, #9, #10 | `pages/components` matched; Index choosable in Appearance; `PaletteTest`, `ExistingLayoutsTest`, `IndexTest` (palettes and tones pinned to `tokens.json`) and `IndexMotionTest` pass |
| **I2** Home | Section 9; motion #5–#7, #11 | `pages/home` matched; `IndexHomeRulesTest` |
| **I3** Album, Artist, Genre, Paths | | `pages/album-artist-genre`, `pages/paths` matched |
| **I4** Discover, Library, Search | | `pages/discover`, `pages/library-search` matched |
| **I5** Now Playing, Queue, Lyrics, Radio | Motion #8, #13 | `pages/player`, `pages/radio` matched |
| **I6** Downloads, Stats, Server, Settings, sheets; closeout | | `pages/downloads-stats-server`, `pages/settings`, `pages/sheets` matched; `ACTIVE_WORK.md` updated |

Bento and Index are independent. Either can be built first, or both in parallel by different agents. Only `Palette.kt`, `Theme.kt`, `Motion.kt` and the shared screen files receive a branch from each, so the two B1 and I1 PRs should not run at the same time.

## 13. Decisions

The owner decided every point as proposed on 2026-11-17.

| # | Point | Decision |
|---|---|---|
| I1 | Where the strip and insight colours live | In `IndexTones` in `IndexKit.kt`, keyed by palette id; `Palette` gains no field |
| I2 | Signal Blue's primary button is ink, the others use the signal colour | Keep as the owner approved the palettes: the original stays as proposed on 16 November |
| I3 | Directional tab slides use the bar order Home, Discover, Library, Search | The Index bar keeps that order (as in the mockups); other themes keep theirs |
| I4 | Sheet timing | Keep Material's `ModalBottomSheet` timing (as Gallery G7); no custom sheet |
| I5 | "Follow the phone" defaults | Signal Blue (light) and Graphite Orange (dark) |
| I6 | The colour changes in 4.2 made for contrast | Accept them; the owner can compare in `pages/palettes` |
| I7 | The album's library position "0418 / 1284" needs a new field (11a) | Build it on the server as an optional field (`library_position`, `library_total`) in I0; the number stays |

## 14. Verification for each step

- Unit tests for every pure rule. The palette contrast test is extended to the four palettes. Focused tests only.
- `ExistingLayoutsTest` stays green.
- The PR shows a screenshot of each built screen next to its mockup PNG and lists anything dropped.
- `python3 docs/design/index/_src/check_contrast.py` stays green whenever `tokens.json` changes. Rebuild the mockups with `build.py`.
- CPU check: nothing animates at rest except the playing bars.
- The owner checks each step on the phone before the next one starts.
