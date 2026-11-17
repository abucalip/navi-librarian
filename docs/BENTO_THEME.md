# Bento theme for Android: design system and build plan

Status: **design approved by the owner** (2026-11-17); every decision in section 13 is decided as proposed, and both font files are kept. Nothing is built; B0 is next. This document is the spec that implementing agents build from. The mockups beside it are the spec for every screen ("the mockups are the spec", Round 3 owner rule).

Package: [`docs/design/bento/`](design/bento/). Start with its [`README.md`](design/bento/README.md). The shared mockup kit is [`docs/design/_kit/`](design/_kit/).

## 1. What the owner asked for

1. On 2026-11-17 the owner saw four new Android theme directions (Bento, Orbit, Darkroom, Spectrum) and **kept A, Bento**. They also brought back **Index** from the 16 November round, which has its own spec: [`INDEX_THEME.md`](INDEX_THEME.md).
2. The palettes kept for Bento are **Sorbet** (day, the default), **Licorice** (night) and **Riviera** (day).
3. The owner asked for:
   - a design system and an implementation plan for each theme;
   - mockups of **every page**, drawn in one palette, including the album and artist **Paths** pages;
   - the other palettes given as codes and scripts;
   - detailed instructions on how to build the animations (section 8).
4. Every mockup is drawn in **Sorbet**. Licorice and Riviera are **colour variations only**: the layout, components, type and icons are the same, and only the colour values change. [`pages/palettes`](design/bento/pages/palettes.html) shows Home in all three, generated from `tokens.json`.

## 2. Rules

1. **Ownership.** Bento is one new `Layout.Bento` shared by its three palettes. Every composable it changes is reached through an `isBento()` branch, as Gallery does with `isGallery()`, and lives in Bento's own files (section 11). No shared composable changes what it draws for any other layout. `ExistingLayoutsTest` must still pass.
2. **Behaviour is unchanged.** A theme changes how a screen is arranged, never what it does (D-023). These stay reachable, with text labels where they have them today:
   - Get album, Save, Not this album, Never suggest this artist;
   - Play, and Dismiss with its confirmation;
   - the downloads badge and Settings;
   - the mini player and the four destinations.
3. **The mockups are the spec.** Build each screen element by element from its mockup. List anything dropped in the PR.
4. **Artwork first, colour second.** Covers and artist photos are the largest things on every page. The tile tones are the only other large colour. Tones are decoration and say nothing; state is said in words (In library, Requested) and through `control`/`accent`.
5. **Contrast.**
   - Every palette passes `PaletteTest` as written.
   - The Bento roles pass the extra checks in [`_src/check_contrast.py`](design/bento/_src/check_contrast.py). All three palettes pass today.
   - The existing rules still apply: 48dp touch targets, state never shown by colour alone, Remove animations respected, missing data said in words.

## 3. Identity in six rules

1. **Tiles, not lists.** Home and most pages are made of rounded tiles in a two-column grid with a 10dp gap and 14dp side margins.
   - Large tiles have a 28dp radius and 14dp padding; small tiles have a 22dp radius and 12dp padding.
   - A tile can span both columns (`span2`) or two rows (`tall`).
   - Each tile is one thing and one door: tapping it opens its page.
2. **Five tones in rotation.** Tiles take `warm`, `sun`, `leaf`, `bloom` and `sky` in that order, white `surface` for lists, and one `deep` tile per screen for the strongest call (the Discover teaser, the opened Paths step). Never put two tiles of the same tone side by side.
3. **Round everything that is touched.** Buttons are 22dp pills, chips are 20dp pills and icon buttons are 44dp circles. Covers have an 18dp radius when large, 14dp on small tiles, 12dp in rows and 10dp under 44dp. Artist photos have a 20dp radius on tiles and are round (circle) in rows and on Paths.
4. **One colour for doing.** `control` (Sorbet: tomato `#B8321A`) fills:
   - primary buttons, the active nav pill, the Play circle and the mini player's Pause;
   - and colours links, rank numbers, the header icons and the seek bar.

   In Bento `accent` equals `control`. It also marks state: the playing row, the playing bars, the badge and the progress line.
5. **Bold rounded type.** Gabarito 800 for titles and numbers; Figtree for everything else. No serif and no mono.
6. **Floating dock.** The mini player is its own white tile, and below it a dark pill bar floats over the page with a 12dp margin. Only the active destination shows its label, inside a `control` pill.

## 4. Colour

### 4.1 Roles

The CSS variables in [`palettes.css`](design/bento/palettes.css) use the `Palette` field names, so the mapping is one to one. Bento needs no new `Palette` field: `control`, `onControl` and `mat` exist since Gallery G1. Bento's own colours, the **tones**, live in `BentoTones` in `ui/common/BentoKit.kt`, keyed by palette id (decision B1).

| Role | Used for |
|---|---|
| `ink` | Page background |
| `rail`, `surface` | White tiles, the mini-player tile, sheets |
| `mat` | Not drawn (no mats); set to the surface or the raised tone |
| `raised` | Skeletons, the seek and slider tracks, switch off |
| `edge` | Row dividers inside white tiles |
| `edgeStrong` | Chart baseline, the sheet handle (at 50%) |
| `text`, `textMuted` | Text on `ink` and `surface` |
| `control` / `onControl` | Primary buttons, the active nav pill, icons on `surface`, links, rank numbers, the seek bar, switch on |
| `accent` / `onAccent` | Equal to control: playing state, the badge, the progress line, the first chart series |
| `ok`, `caution`, `chartRedText`, `info` | State words: In library, needs attention, failed or Dismiss, information |
| tone `warm` `sun` `leaf` `bloom` `sky` | Tile backgrounds in rotation |
| tone `onTone` / `onToneMuted` | Text on a tone tile (title / label) |
| tone `bar` / `barIcon` | The floating nav bar and its idle icons |
| tone `deep` / `onDeep` / `deepEyebrow` | The one dark tile per screen, the snackbar, a selected chip |
| tone `chip` | Chip and icon-button fill inside a tone tile |
| tone `shadowRgb` | The colour of the float and lift shadows |

### 4.2 The three palettes

Single source: [`tokens.json`](design/bento/tokens.json). On all three: `family = Classic`, `shape = null`, `layout = Layout.Bento`, `suggestedFontId = "bento"`, `minAccentContrast = 4.5`.

| Role | Sorbet (day) | Licorice (night) | Riviera (day) |
|---|---|---|---|
| `ink` | `#F4F0E8` | `#121110` | `#EFF3F1` |
| `rail` | `#FFFFFF` | `#1C1A18` | `#FFFFFF` |
| `surface` | `#FFFFFF` | `#1C1A18` | `#FFFFFF` |
| `mat` | `#FFFFFF` | `#26231F` | `#FFFFFF` |
| `raised` | `#EAE4D8` | `#26231F` | `#DDE6E3` |
| `edge` | `#E3DCCF` | `#2E2A26` | `#D3DEDA` |
| `edgeStrong` | `#8A8276` | `#7A7268` | `#6E7F7B` |
| `text` | `#1D1B18` | `#F3EEE6` | `#13201E` |
| `textMuted` | `#5E5850` | `#ADA59A` | `#4E5D5A` |
| `control` | `#B8321A` | `#FF8E6A` | `#2440C8` |
| `onControl` | `#FFFFFF` | `#121110` | `#FFFFFF` |
| `accent` | `#B8321A` | `#FF8E6A` | `#2440C8` |
| `onAccent` | `#FFFFFF` | `#121110` | `#FFFFFF` |
| `ok` | `#1B6B3A` | `#8FD6A0` | `#1B6B3A` |
| `caution` | `#8A5300` | `#F2A65A` | `#7F4A00` |
| `chartRed`, `chartRedText` | `#B3261E` | `#FF8A73` | `#B3261E` |
| `info` | `#1F5A8A` | `#8FB8E8` | `#1F5A8A` |
| `chart2` | `#8A8276` | `#7A7268` | `#6E7F7B` |
| `chart3` | `#E3DCCF` | `#3A352F` | `#D3DEDA` |
| tone `warm` | `#F7D0BD` | `#3A241B` | `#FFD2CA` |
| tone `sun` | `#F3E3A1` | `#36301A` | `#F2EC9B` |
| tone `leaf` | `#CDE7D6` | `#1F3328` | `#BFE3DC` |
| tone `bloom` | `#DCD3F2` | `#2A2540` | `#D3DCFA` |
| tone `sky` | `#CBDDF2` | `#1F2E2E` | `#CFEAF2` |
| tone `onTone` | `#1D1B18` | `#F3EEE6` | `#13201E` |
| tone `onToneMuted` | `#4A453E` | `#D3C9BC` | `#36433F` |
| tone `bar` | `#1D1B18` | `#26231F` | `#13201E` |
| tone `barIcon` | `#E9E3D8` | `#D8D1C5` | `#DDE6E3` |
| tone `deep` | `#1D1B18` | `#26231F` | `#13201E` |
| tone `onDeep` | `#F4F0E8` | `#F3EEE6` | `#EFF3F1` |
| tone `deepEyebrow` | `#F3B8A3` | `#FFB59C` | `#F2EC9B` |
| tone `chip` | `#FFFFFF` | `#121110` | `#FFFFFF` |
| tone `shadowRgb` | `29,27,24` | `0,0,0` | `19,32,30` |
| `id` | `bento` | `bento_licorice` | `bento_riviera` |
| Label | Bento · Sorbet | Bento · Licorice | Bento · Riviera |

Add Sorbet and Riviera to `Palettes.Light` and Licorice to `Palettes.Dark`, after the Gallery ones. When "Follow the phone" is on and Bento is chosen, the defaults are Sorbet for light and Licorice for dark.

**Changed from the proposal for contrast.** Sorbet's tomato was `#C8381A` in the proposal; it is `#B8321A` here so that it reaches 4.5:1 on `raised` (it measured 4.35:1). Nothing else changed.

### 4.3 Contrast (checked)

`python3 docs/design/bento/_src/check_contrast.py` runs 48 to 49 checks per palette:

- the `PaletteTest` rules;
- `control` on every background at 4.5:1;
- `onTone` and `onToneMuted` on all five tones;
- `barIcon` on `bar` at 3:1;
- `onDeep` and `deepEyebrow` on `deep`;
- text and `control` on `chip`.

**All three pass.** The lowest results:

| Palette | Lowest check | Result |
|---|---|---|
| Sorbet | `control` on `raised` | 4.73:1 |
| Licorice | `edgeStrong` on `surface` | 3.66:1 (needs 3.0) |
| Riviera | `textMuted` on pastel washes | 5.10:1 |

## 5. Type

### 5.1 Font files

Bento ships two new files, subset to Latin (Basic Latin, Latin-1, Latin Extended-A and common punctuation) and kept variable on weight only.

| File (copy into `android/app/src/main/res/font/`) | Source | Axis kept | Size |
|---|---|---|---|
| [`gabarito_bento.ttf`](design/bento/fonts/gabarito_bento.ttf) | Google Fonts `ofl/gabarito/Gabarito[wght].ttf` | `wght` 500–900 | 88 KB |
| [`figtree_bento.ttf`](design/bento/fonts/figtree_bento.ttf) | `ofl/figtree/Figtree[wght].ttf` | `wght` 400–800 | 43 KB |

Both are under the SIL Open Font License 1.1; the licence texts are in [`fonts/`](design/bento/fonts/). The subset commands are in the package README. Together they add about 131 KB to the APK. Both ship (decision B2).

### 5.2 Font pair

- Add `FontPairs.Bento`: id `bento`, label "Bento", title "Gabarito", body "Figtree", `numeral` = the title face, `numeralWeight = FontWeight.ExtraBold`.
- Register each face as a `FontFamily` of `variable(R.font.…, weight)` entries for the weights used (Gabarito 800 and 900; Figtree 400, 500, 600 and 700).
- Bento's own text styles (section 5.3) live in `BentoKit.kt` and read the pair through `LocalFontPair`, so a person who picks another pair in Appearance keeps Bento's layout with that pair's faces (D4: suggested, not forced).
- The count in `PaletteTest.twelvePairsWithUniqueIdsAndDiscairFirst` moves up by one. Bento has no mono face, so `mono` is the body face.

### 5.3 Type scale

From `tokens.json` → `type`. Sizes and line heights are in sp.

| Style | Face | Weight | Size / line | Tracking | Used for |
|---|---|---|---|---|---|
| Greeting | Figtree | 600 | 13 / 16 | 0 | "Tuesday evening" over the Home title |
| Large title | Gabarito | 800 | 34 / 36 | −0.02em | Page titles |
| Page title | Gabarito | 800 | 36 / 37 | −0.02em | Album and artist name on their page |
| Hero title | Gabarito | 800 | 30 / 31 | −0.01em | The pick, the Discover hero, Now Playing |
| Tile title | Gabarito | 800 | 20 / 21 | 0 | Tile headings: Newly added, Most played… |
| Tile name | Gabarito | 800 | 18 / 20 | 0 | Names inside small tiles |
| Stat | Gabarito | 900 | 40 / 40 | −0.01em | The one Home stat, Stats numerals, the crossfade length |
| Rank | Gabarito | 800 | 18 / 20 | 0, `tnum` | 1 2 3 in Most played; track numbers (15, muted) |
| Row title | Figtree | 700 | 15 / 20 | 0 | Rows |
| Body | Figtree | 400 | 14 / 20 | 0 | Body text |
| Small | Figtree | 500 | 13 / 17 | 0 | Second lines |
| Eyebrow | Figtree caps | 700 | 12 / 15 | +0.06em | RECOMMENDED · 1/12 (in `control`; on `deep` in `deepEyebrow`) |
| Tile label | Figtree | 600 | 12 / 15 | 0 | "Radio", "This month" over a tile value (`onToneMuted`) |
| Button | Figtree | 700 | 15 / 18 | 0 | Buttons; small buttons 13 |
| Chip | Figtree | 700 | 14 / 18 | 0 | Chips and lens names |
| Nav label | Figtree | 700 | 15 / 18 | 0 | Only inside the active pill |
| Time | Figtree, `tnum` | 500 | 12.5 / 16 | 0 | Durations and seek times |

## 6. Icons

[`icons/`](design/bento/icons/) holds 48 SVGs (24 by 24), plus [`icons/BentoIcons.kt.txt`](design/bento/icons/BentoIcons.kt.txt), a ready `BentoIcons` object written by the build script.

- **Builder.** Use the same `stroked`/`filled` builder as `ArtIcons`, with `strokeLineWidth = 1.8f` and round caps and joins.
- **Names.** Property names match `ArtIcons` one for one, plus:
  - `Ban` (Never suggest), `RepeatOne` and `MusicNote`;
  - `Spark` (Discovery mode);
  - `Grid` (Layout).
- **Fills.** Play, pause, next, previous and the three dots are the only filled glyphs.
- **Sizes:**
  - 22dp default;
  - 18dp in buttons and small icon buttons;
  - 28dp in the transport row;
  - 30dp inside the 76dp Play circle.
- **Colour:**
  - `control` on `ink` and `surface`;
  - `onTone` inside tone tiles;
  - `barIcon` in the bar;
  - `onControl` on `control` fills.
- **Circles behind icons.** Icon buttons sit in a 44dp circle filled with `ink` (on `surface`), `chip` (inside a tone tile) or `surface` (in the header).

Read icons through a small switch: `BentoIcons` when `isBento()`, else today's icons.

## 7. Components

Every measurement is in [`bento.css`](design/bento/bento.css) (1 CSS px = 1dp). The board is [`pages/components`](design/bento/pages/components.html).

### 7.1 Tiles

| Component | Spec |
|---|---|
| Grid | Two columns, 10dp gap, 14dp side margins; `span2` spans both columns, `tall` spans two rows |
| Large tile | Radius 28, padding 14, fill `surface` or a tone. No outline, no shadow |
| Small tile | Radius 22, padding 12 |
| Deep tile | `deep` fill, `onDeep` text, eyebrow in `deepEyebrow`; at most one per screen |
| Pick tile (Home) | `span2`, white. 124dp cover (radius 18) left. Right: eyebrow, hero title, "Artist · year", owned tag, then Get, Save and the three dots pinned to the bottom |
| Artist tile | `tall`, `warm`, 10dp padding. Photo (radius 20) over the tile label, name and "5 albums · 31 plays" |
| Stat tile | `leaf`. Tile label, Stat numeral, five 20dp bars (the current week in `control`, the others `onTone` at 30%) |
| Cover stack | Three covers fanned at −10°, +6° and 0°, the front one with `0 10 20 −8 rgba(0,0,0,.5)` |
| Skeleton | `raised` blocks in the same tile shapes; no shimmer |

### 7.2 Controls

| Component | Spec |
|---|---|
| Primary button | 44dp high, radius 22, padding 18, `control` fill, `onControl` label, icon 18 with an 8dp gap. Small: 36dp, padding 14, label 13. Wide: fills the row |
| Outline button (`o`) | `ink` fill on `surface` (`chip` inside a tone), `control` label |
| Danger button | `chartRedText` fill, white label (the Dismiss confirmation) |
| Icon button | 44dp circle (40 small), `ink`/`chip` fill, `control` glyph. Solid: `control` fill |
| Get button states | Idle "Get" (primary) · pending "Getting" (outline, the refresh icon turning) · requested "✓ Requested" (word in `textMuted`) · owned "✓ In library" (`ok`) · failed "Try again" (outline, `chartRedText`). The width animates between states (section 8) |
| Chip | 40dp pill (32 small), `surface` fill, `text` label; selected: `deep` fill, `onDeep` label. Lenses, Library sort, presets and Paths kinds are chips |
| Tag | 12sp Figtree 600 on a `warm` pill ("Not in your library"); `leaf` for quality ("FLAC 16/44.1") |
| Row | Min 60dp, 12dp gap, 1dp `edge` divider (8% black inside tones); lead (rank, 46dp cover or 44dp icon button) · title and sub · trail |
| Search field | 48dp pill, `surface` fill; focused: 2dp inset `control` ring |
| Switch | 52×32 pill. Off: `raised` with a `surface` knob. On: `control` with an `onControl` knob |
| Slider and seek | 6dp rounded `raised` track, `control` fill, a 16dp knob (20dp on sliders) ringed in the page colour |
| Download tracker | Four 6dp rounded segments, 4dp apart: `control` when reached, `raised` ahead, `chartRedText` on the failed step; step names below in 11sp |
| Ranked bars | 12dp rounded bars on `chip`, the first in `control`, the others `onTone` at 35% |
| Column chart | Rounded columns `8 8 4 4`, `chart3`, the current month in `accent` |
| Banner | A `warm` small tile: warning icon, title and saved-copy time, Retry outline button |

### 7.3 Bars and surfaces

| Component | Spec |
|---|---|
| Home header | Greeting over Large title, 22dp top padding. Right: the downloads (badge) and settings icon buttons, 44dp `surface` circles with `control` glyphs |
| Page top bar | Back icon button left, the 13sp page name in the middle (optional), a right action. Then the page head |
| Dock | Bottom 0, padding 24/12/14. Fades the page out over its top 30% |
| Mini player | Tile radius 24, padding 8, `surface`, float shadow. 48dp cover (radius 14), title 15/700 over artist 13; solid 40dp Pause; a 3dp `accent` progress line along the bottom |
| Nav bar | 64dp pill, radius 32, `bar` fill, float shadow, 10dp under the mini player. Four cells: idle cells are 56×48 with a `barIcon` glyph; the active cell is a 48dp `control` pill with its glyph and label |
| Badge | 18dp pill, `accent` fill, `onAccent` 11/700 |
| Sheet | `surface`, top radius 28, 10dp top padding, a 40×5 handle, 14dp sides. Header: 52–56dp cover, eyebrow, tile name. Options are 60dp rows with a 44dp icon circle. Scrim: rgba(10,10,10,.45) |
| Snackbar | 52dp pill, `deep` fill, `onDeep` text, Undo in `deepEyebrow` 800. Sits 8dp above the dock |
| Shadows | Only three: float `0 10 24 −14 rgba(shadow,.45)` (mini player, nav), lift `0 18 30 −16 rgba(shadow,.55)` (a pressed or dragged tile), cover stack |

## 8. Motion: what moves and how to build it

Values are in `tokens.json` → `motion`. Try them on the live page [`pages/motion`](design/bento/pages/motion.html), which covers tile entry, tile to page, the pill bar, press, and Remove animations.

Bento's character is **springy and tactile**: tiles pop in, the pill stretches, a tile grows into its page. Nothing loops except the playing bars and the pending Get spinner, and both stop when nothing is happening.

### 8.1 Ground rules for every animation

1. **Route all durations through the existing helpers.**
   - Add `Layout.Bento` to `MotionRules.familyFor` → `MotionFamily.Standard`.
   - Read `val reduced = rememberReducedMotion()` once per screen.
   - Pass every duration through `MotionRules.duration(ms, MotionFamily.Standard, reduced)`. It returns 0 when the phone's Remove animations is on.
2. **Springs.** For springs use a helper in `ui/theme/BentoMotion.kt`, modelled on `GalleryMotion.kt`:
   ```kotlin
   object BentoMotion {
       // Fully qualified calls: inside this object, plain spring()/tween() would call these same functions.
       fun <T> spring(damping: Float, stiffness: Float, reduced: Boolean): FiniteAnimationSpec<T> =
           if (reduced) snap() else androidx.compose.animation.core.spring(dampingRatio = damping, stiffness = stiffness)
       fun <T> tween(ms: Int, curve: Easing, reduced: Boolean, delayMs: Int = 0): FiniteAnimationSpec<T> =
           androidx.compose.animation.core.tween(MotionRules.duration(ms, MotionFamily.Standard, reduced), if (reduced) 0 else delayMs, curve)
       val Emphasized = CubicBezierEasing(0.2f, 0f, 0f, 1f)        // tileToPage, playerRise, getMorph, statCount
       val EmphasizedExit = CubicBezierEasing(0.3f, 0f, 0.8f, 0.15f) // pageToTile, playerFall
       val Exit = CubicBezierEasing(0.4f, 0f, 1f, 1f)               // sheetOut
       // the tokens below, one const per value, pinned to tokens.json by BentoMotionTest
   }
   ```
3. **Animate with `graphicsLayer`.** Use `graphicsLayer { }` for scale, translation and alpha, never `Modifier.scale`/`offset` with recomposition, so a moving tile redraws only itself.
4. **Grid items.** In lazy grids, give every item a stable `key` and use `Modifier.animateItem()` so reordering and inserts move rather than jump.
5. **Shorthand in the table below.** A plain `tween(ms, delay)` in section 8.2 stands for `BentoMotion.tween(ms, curve, reduced, delay)`, and a plain `spring(d, s)` for `BentoMotion.spring(d, s, reduced)`. Never call Compose's own `tween`/`spring` directly in Bento code, so Remove animations always reaches every animation.
6. **No continuous motion.** Do not use `rememberInfiniteTransition`, except for:
   - the three playing bars, only while `isPlaying`;
   - the pending Get icon, only while pending.

   Both must stop when the screen is not visible: use `LifecycleResumeEffect`, or check `Lifecycle.State.RESUMED`.

### 8.2 The animations

| # | Moment | Values (tokens.json → motion) | How to build it in Compose |
|---|---|---|---|
| 1 | **Tile entry** (a page arrives) | `tileEnter`: spring 0.72 / 380; scale 0.94 → 1; translate 14dp → 0; fade 220ms; stagger 40ms; at most 10 staggered | Keep one `Animatable(0f)` per visible tile in a `remember(pageKey)` list. In `LaunchedEffect(pageKey)`, for each index `i < 10` launch `delay(i * 40L)` then `animateTo(1f, BentoMotion.spring(0.72f, 380f, reduced))`. Read `p = anim.value` in `graphicsLayer { scaleX = lerp(0.94f, 1f, p); scaleY = …; translationY = (1 - p) * 14.dp.toPx(); alpha = (p * 1.6f).coerceAtMost(1f) }`. Tiles after the tenth start with `snapTo(1f)`. Run only on the first arrival of a page, not when Back returns to it (keep a `rememberSaveable` flag) |
| 2 | **Tile → page** (container transform) | `tileToPage`: 450ms, Emphasized; corners 28 → 0; the new content fades in after 150ms over 200ms | Use the app's `SharedTransitionLayout` (`MainShell.kt`, `LocalSharedTransitionScope`). On the tile: `Modifier.sharedBounds(rememberSharedContentState("tile:$routeKey"), animatedVisibilityScope, enter = fadeIn(tween(200, 150)), exit = fadeOut(tween(120)), boundsTransform = { _, _ -> BentoMotion.tween(450, Emphasized, reduced) }, resizeMode = RemeasureToBounds, clipInOverlayDuringTransition = OverlayClip(shape))`. Use the same key on the destination page's root. Animate the clip shape's corner from 28dp to 0 with `transition.animateDp`, read from the shared transition's `isTransitionActive` progress. Covers inside keep `Modifier.sharedCover(routeKey)` so the cover travels on its own as well |
| 3 | **Page → tile** (Back) | `pageToTile`: 380ms, EmphasizedExit | Same shared bounds in reverse. No extra code |
| 4 | **Other page changes** (tabs) | `pageCrossfade`: 220ms linear | NavHost `enterTransition = fadeIn(tween(220))`, `exitTransition = fadeOut(tween(220))`, then the arriving page runs #1 |
| 5 | **Press** | `press`: scale 0.97, spring 0.6 / 800 | `val pressed by interaction.collectIsPressedAsState(); val s by animateFloatAsState(if (pressed) 0.97f else 1f, BentoMotion.spring(0.6f, 800f, reduced))` → `graphicsLayer { scaleX = s; scaleY = s }`. On tiles, rows and buttons. A long-pressed (dragged) tile also takes the lift shadow |
| 6 | **Nav pill** | `navPill`: spring 0.8 / 500; label fades 150ms after a 60ms delay | Each cell is a `Row` with `Modifier.animateContentSize(BentoMotion.spring(0.8f, 500f, reduced))`. The pill fill is `animateColorAsState(if (selected) control else Transparent, tween(200))`, and the icon colour animates the same way. The label is `AnimatedVisibility(selected, enter = fadeIn(tween(150, delayMillis = 60)) + expandHorizontally(BentoMotion.spring(0.8f, 500f, reduced)), exit = fadeOut(tween(90)) + shrinkHorizontally(BentoMotion.spring(0.8f, 500f, reduced)))`. Do not build one sliding pill: each cell grows and shrinks, which reads as the pill moving |
| 7 | **Now Playing opens / closes** | `playerRise` 420ms Emphasized; `playerFall` 320ms EmphasizedExit | The player is a dialog window today, so fly the cover by hand as Gallery does (`GalleryFlight`). Capture the mini cover's bounds with `onGloballyPositioned`, and draw a cover that interpolates its rect and corner (14 → 28dp) to the player cover. The page rises with `slideInVertically { it } + fadeIn` and the dock slides down by its own height. Reverse on close |
| 8 | **Sheets** | `sheetIn` spring 0.85 / 420 (no visible overshoot); `sheetOut` 240ms Exit; scrim 220ms | With Material 1.3.2, `ModalBottomSheet` cannot take a custom spec (Gallery found the same). Decided (B4): keep Material's sheet and accept its timing. Not built: a custom `BentoSheet` (`Box` + scrim + `Animatable` offset `animateTo(0f, spring(0.85f, 420f))`, drag-to-dismiss with `draggable` and a velocity threshold of 1,000dp/s) |
| 9 | **Snackbar** | `snackIn` spring 0.75 / 500 from 24dp below; hold 4s | `val d = LocalDensity.current; val off = with(d) { 24.dp.roundToPx() }` then `AnimatedVisibility(visible, enter = slideInVertically(BentoMotion.spring(0.75f, 500f, reduced)) { off } + fadeIn(tween(150)), exit = fadeOut(tween(150)) + slideOutVertically { off })` (the lambda returns pixels, so convert once with the density). Hold with `delay(4000)` in the host, after TalkBack's longer wait where the app already uses one |
| 10 | **Get button morph** | `getMorph` 260ms Emphasized; the pending icon turns once per 900ms | `AnimatedContent(state, transitionSpec = { fadeIn(tween(160, 60)) togetherWith fadeOut(tween(100)) using SizeTransform(clip = false) { _, _ -> tween(260, easing = Emphasized) } })`. The pending icon uses `rememberInfiniteTransition` only inside the pending branch, so it stops when the state leaves |
| 11 | **Cover stack fan** (Recently played) | `coverStackFan` spring 0.7 / 300; angles −10°, +6°, 0° | On first composition the three covers start at 0° stacked and spring to their angles (`Animatable` per cover, `rotationZ` in `graphicsLayer`), 60ms apart. On press the back two open 4° more |
| 12 | **Stat count-up** | `statCount` 700ms Emphasized | `val shown by animateIntAsState(target, tween(700, easing = Emphasized))` on the first arrival only. Show the final value at once when reduced or when TalkBack is on (the spoken label is always the final value) |
| 13 | **Playing bars** | `playingBars` 900ms, 4 → 14dp, phases 0 / −300 / −600ms | Three 3dp bars in `accent`. One `rememberInfiniteTransition` with three `animateFloat(4f, 14f, infiniteRepeatable(tween(900), RepeatMode.Reverse, StartOffset(phase)))`. Only while playing and resumed; static at 9dp when reduced |
| 14 | **Pager on the pick tile** | swipe | `HorizontalPager` with the default fling. The eyebrow "1/12" changes with `AnimatedContent` (slide 8dp + fade, 200ms) |

### 8.3 Order of work

Build #5 (press) and #6 (nav pill) in B1 with the shell. Build #1, #2, #3 and #4 in B2 with Home. Build #10 and #11 in B2, #7 and #13 in B5, #8 and #9 in B1. Each comes with a `BentoMotionTest` that pins its values to `tokens.json`, and with a check that every duration is 0 and every spring is `snap()` when reduced.

## 9. Home

Mockup: [`pages/home`](design/bento/pages/home.html) (four frames). From top to bottom:

| # | Tile | Content | Data |
|---|---|---|---|
| 1 | Header | Greeting ("Tuesday evening", from the time of day), "Your library", downloads with badge, settings | as today |
| 2 | Pick (`span2`, white) | Cover, RECOMMENDED · 1/12, title, "Artist · year", "Not in your library" tag when missing, Get / Save / three dots. Swipe for the next pick | `picks` |
| 3 | Artist (`tall`, warm) | Photo, "Artist you return to", name, albums and plays | `HomeArtists` |
| 4 | Radio (sun) | Radio icon, Play, "Radio · last station", "On air now". Opens Radio; Play starts that station | `radioStations()` |
| 5 | Stat (leaf) | "This month", hours, five weekly bars. **The only stat on Home** | as today |
| 6 | Newly added (`span2`, white) | Four covers with names; See all | recently added |
| 7 | Recently played (bloom) | Cover stack, the latest album's name | recently played |
| 8 | Genres (sky) | Four genre chips; each opens its genre | as today |
| 9 | Most played (`span2`, white) | Three ranked rows with Play | most played |
| 10 | Discover teaser (`span2`, deep) | Two overlapped covers, "Discover · Daily picks", "3 new albums picked for today"; opens Discover on that lens | lens list counts |
| 11 | New releases (`span2`, white) | Two rows with Get states | new releases |
| 12 | Radio (`span2`, white) | Four station tiles (initials; "Today" in `control`), "Heard on FIP this morning" with two rows (In library / Requested / Get) | as Gallery section 9, row 6 |
| 13 | This week (`span2`, sun) | Insight with Play and "Why this?" | insight source |
| 14 | Arrivals (`span2`, white) | In-progress row with its tracker; arrived today; link Downloads | `AcquisitionHub` |
| 15 | Library line (`span2`, leaf) | "1,284 albums · 312 artists" and a chevron to Library stats | as today |

States (frame 4):
- a service banner tile above the grid;
- skeleton tiles while loading;
- "No listening yet. Play a few albums and the artists you come back to show up here." when there is no listening;
- tiles whose data is empty are left out, and the grid closes up (never an empty tile).

## 10. Every page and its file

Each page is an `.html` (open it in a browser to measure) and a `.png` in [`docs/design/bento/pages/`](design/bento/pages/). Frames are 360 × 780dp. Rebuild them with `python3 docs/design/bento/_src/build.py`.

| File | Frames |
|---|---|
| `home` | First screen; scrolled (Recently played, Genres, Most played, Discover teaser, New releases); end (Radio, This week, Arrivals, library line); states |
| `album-artist-genre` | Album owned with the fifth song playing (cover tile, info tiles, Play/Shuffle/Paths/Save, chips Songs/Info/Reviews/Booklet, tracks); album not in the library (Get album, why this pick, similar); Artist (photo tile, Paths button, top songs, albums with "Get" tags); Genre |
| `paths` | **Album Paths** sheet: header, kind chips (Studio crew, Guest list, Covers and sources, Same year same scene, Same room, Listen-through gaps, Neighbours by ear when sonic data exists), steps as tone tiles with the server's sentence and library state. **Album Paths step opened**: the album in a deep tile, one tone tile per reason (kind, who, the sentence), tiles to open the person and the album. **Artist Paths** sheet: kinds (Follow the musician, Sideman, Label, Composition, Scene), steps with round photos. **Artist Paths step opened**: the musician tile, the link, Albums together, Open and Next step |
| `player` | Now Playing (cover tile, quality tag, seek, transport, four tool tiles); Queue; Lyrics (stand-in text) |
| `discover` | Lists (lens chips, hero with the reason, Get states, deep dive tile, Undo snackbar); Insights; taste sheet |
| `library-search` | Albums (search field, view tiles, sort chips, album tiles); Artists; Search (Artist, In your library, Not in your library with Get) |
| `radio` | Stations (tone tiles, the playing one with bars); Live radio; Heard on radio (In library, Get, Requested, an unnamed play) |
| `downloads-stats-server` | Downloads (tracker, Use next source, Try again, Dismiss); Library stats; Server |
| `settings` | Settings in grouped tiles; Appearance (the three palettes as swatch tiles); Equalizer; Crossfade |
| `sheets` | Pick menu; song menu (with "Paths from this album"); Dismiss confirmation; snackbar with Undo |
| `extras-a` | Setup (Librarian and Navidrome addresses, Connect); Unavailable (Try again, Open Tailscale, Edit servers); the Newly added sheet (See all from Home); Discover's Saved list |
| `extras-b` | Album Booklet tab (page pager); cover picker sheet (editions, "Use the automatic cover"); Album Paths, Neighbours by ear (only with sonic data); Sonic path sheet opened from a Queue row |
| `palettes` | Home in all three palettes (colour only) |
| `components` | Token swatches for all three palettes, the type scale, every control, tiles, the dock and the 48 icons |
| `motion` | Live prototype: tile entry, tile to page, pill bar, press, Remove animations |

Every route in `ui/Routes.kt` and every sheet the screens open has a frame. Not drawn: tablet widths, and empty or error states beyond Home's frame 4 (each uses the same banner tile, skeleton tiles and empty-state tile).

**Paths behaviour stays as built.** The server is asked only when the sheet is open and a kind is chosen, and Back from an opened album returns to the sheet at the same step (`ArtistPaths.kt`, `AlbumPathsSheet.kt`). Bento changes only how a step and its reasons are drawn.

## 11. Where the code goes

New files only, so no other theme's file changes shape:

| New file | Holds |
|---|---|
| `ui/theme/BentoMotion.kt` | Section 8 values and helpers (pure) |
| `ui/common/BentoKit.kt` | `BentoTones` (per palette id, from `tokens.json`), text styles (5.3), `BentoTile`, `BentoGrid`, buttons, `BentoGetButton`, chips, tag, rows, switch, slider, tracker, banner, skeleton |
| `ui/common/BentoIcons.kt` | From `icons/BentoIcons.kt.txt` |
| `ui/common/BentoShell.kt` | Dock (mini-player tile, floating pill bar), header, top bar, sheet look, snackbar, tile-to-page shared bounds |
| `ui/home/BentoHome.kt`, `BentoHomeRules.kt` | Section 9; the rules are pure (greeting, tile order, which tiles show, tone rotation) |
| `ui/album/BentoAlbum.kt`, `ui/artist/BentoArtist.kt`, `ui/BentoGenre.kt` | Album, Artist, Genre |
| `ui/album/BentoAlbumPaths.kt`, `ui/artist/BentoArtistPaths.kt` | Paths step and reason tiles, branched from `AlbumPathsSheet.kt` and `ArtistPaths.kt` |
| `ui/discover/BentoDiscover.kt`, `ui/library/BentoLibrary.kt`, `ui/search/BentoSearch.kt` | Discover, Library, Search |
| `ui/player/BentoNowPlaying.kt`, `ui/player/BentoEqCrossfade.kt` | Now Playing, Queue, Lyrics, Equalizer, Crossfade |
| `ui/radio/BentoRadio.kt`, `ui/downloads/BentoDownloads.kt`, `ui/stats/BentoStats.kt`, `ui/settings/BentoSettings.kt` | Radio, Downloads, Stats, Server, Settings, Appearance |
| `res/font/gabarito_bento.ttf`, `figtree_bento.ttf` | Section 5.1 |

These existing files each gain one `isBento()` branch, as Gallery did:

- `theme/Palette.kt` (three palettes, `Layout.Bento`), `theme/Theme.kt` (font pair), `theme/Motion.kt` (`familyFor`);
- `MainShell.kt`;
- `HomeScreen.kt`, `AlbumScreen.kt`, `ArtistScreen.kt`, `GenreScreen.kt`;
- `AlbumPathsSheet.kt`, `ArtistPaths.kt`, `PathPanes.kt`;
- `DiscoverScreen.kt`, `LibraryScreen.kt`, `SearchScreen.kt`;
- `NowPlayingSheet.kt`, `RadioScreen.kt`, `HeardScreen.kt`, `RadioNowPlayingSheet.kt`;
- `DownloadsScreen.kt`, `StatsScreen.kt`, the settings screens;
- the shared buttons, chips, switch, text field, snackbar and sheet.

Add the `Bento*` files to `ARCHITECTURE.md` in B1.

## 11a. Server data the theme needs: build what is missing

**Rule (owner decision, 2026-11-17).** If a theme element needs data or a route the server does not provide, the server part is **built**, not dropped and not faked on the phone. This applies to both Bento and Index.

1. **Audit first (step B0).** Before the first client step, the implementing agent checks every row of the table below against the current server code and the Android decoders, and marks each one *served* or *missing*. Rows marked *check* are the ones this spec could not confirm.
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
| Stat tile, five weekly bars (Home) | Listening hours for each of the last five weeks | check (hours this month is served today) | An optional `weeks` list on the existing listening-hours source |
| Artist tile "5 albums · 31 plays" (Home), artist rows (Library) | Play count per artist | check | An optional `play_count` on Home artists and `/api/library/artists` items, from Navidrome play counts |
| Library chips "Unplayed" and "Lossless" | Filter albums by never played / lossless format | missing (`/api/library/albums` sorts only: `discovery/search/query.py` `ALBUM_SORTS`) | An optional `filter=unplayed\|lossless` query on `/api/library/albums`, filtering the owned index by Navidrome play count and file suffix / bit depth; paging and counts stay correct |
| Artist page "5 of 9 albums · 4 to get", Get tags on missing albums | Studio albums owned and not owned per artist | check (the parked `missing_count` contract proposal) | `owned_count`, `album_count` and the missing albums on `/api/artists/{key}`, from the MusicBrainz studio-album list the page already reads (batch browse per artist) |
| Album Paths, Neighbours by ear closeness meter | A closeness value per neighbour | served (`matchCount` on `/api/sonic/album-neighbours`) | Map `match_count` to the five segments; no server work |
| Artist Paths step: "With 1968 – 1971", "Albums together" with library states | Years the two worked together; the shared albums | check (`begin_year` is served on path stops) | Optional `years` and `shared_albums` (title, year, owned) on each `/api/knowledge/paths` stop |
| Album Paths reason tiles: kind, who, sentence | The reason kind and its subject | served (reasons with credits) | none |
| Discover teaser "3 new albums picked for today" (Home) | New items in a lens list since the last visit | check | An optional `new_count` (since the client's `since` time) on `/api/discovery/{list_name}` |
| Radio tile "On air now" (Home), stations "Last heard" | Current play per station; newest play per station | served (`/api/radio/now`, `/api/radio/plays`) | none |
| Server page "answered in 84 ms", version | Response time and version per service | check (`/api/health`) | Optional `version` and `latency_ms` per service on `/api/health` |
| Cover picker editions "2020 JP CD" | Edition labels for cover choices | served (`/api/artwork/choices`) | none |
| Sonic path steps | Ordered steps between two songs | served (`/api/sonic/path`) | none |

The table lists every element in the mockups whose data is not plainly on today's screens. When an audit finds another gap, add a row and follow the same rule.

## 12. Build steps

Each step is one PR with focused tests (JDK 17 for Android; never the full suite), in this order. B0 may be several server PRs; a server item can also be built just before the client step that needs it, as long as it merges first.

| Step | Objective | Acceptance |
|---|---|---|
| **B0** Server data audit and missing routes | Section 11a: check every row against the code; build each missing route or field as its own server PR (new module, contract entry, fixture, focused tests, `ARCHITECTURE.md`) | The audit table filled in B0's PR; every *missing* row either merged on the server or explicitly dropped by the owner; CI green on each server PR's final head |
| **B1** Palettes, fonts, shell | `Layout.Bento`; the three palettes; `BentoTones`; font files and `FontPairs.Bento`; `BentoIcons`; `BentoKit` components; dock with the pill bar (#6), header, sheet, snackbar (#9); press (#5); `familyFor` | `pages/components` matched; Bento choosable in Appearance (Day: Sorbet, Riviera; Night: Licorice); `PaletteTest` and `ExistingLayoutsTest` pass; `BentoTest` pins the palettes and tones to `tokens.json`; `BentoMotionTest` |
| **B2** Home | Section 9; tile entry (#1), tile to page (#2, #3, #4), Get morph (#10), cover stack (#11), stat count (#12) | `pages/home` matched in all four frames; `BentoHomeRulesTest` (greeting by hour, tile order, empty tiles dropped, tone rotation never repeats a neighbour) |
| **B3** Album, Artist, Genre, Paths | Album owned and missing, Artist, Genre; Paths sheet steps and opened steps for album and artist | `pages/album-artist-genre`, `pages/paths` matched |
| **B4** Discover, Library, Search | | `pages/discover`, `pages/library-search` matched |
| **B5** Now Playing, Queue, Lyrics, Radio | Player rise and fall (#7), playing bars (#13) | `pages/player`, `pages/radio` matched |
| **B6** Downloads, Stats, Server, Settings, sheets; closeout | | `pages/downloads-stats-server`, `pages/settings`, `pages/sheets` matched; `ACTIVE_WORK.md` updated |

## 13. Decisions

The owner decided every point as proposed on 2026-11-17, and said not to drop a font.

| # | Point | Decision |
|---|---|---|
| B1 | Where the five tones and the bar/deep colours live | In `BentoTones` inside `BentoKit.kt`, keyed by palette id, so `Palette` gains no field. The alternative is three to five optional `Palette` fields, as Gallery added `mat` |
| B2 | Two new font files (about 131 KB) | **Ship both** `gabarito_bento.ttf` and `figtree_bento.ttf`. Figtree is not replaced by Inter (owner, 2026-11-17) |
| B3 | Tile to page | `sharedBounds` in the existing `SharedTransitionLayout` (Compose BOM 2025.04.01). Pages opened from somewhere other than a tile use #4 |
| B4 | Sheet springs | Keep Material's `ModalBottomSheet` timing (as Gallery G7 did); no custom sheet (8.2 #8, option A) |
| B5 | "Follow the phone" defaults | Sorbet (light) and Licorice (dark) |
| B6 | Lyrics in the mockup | Stand-in text; the screen shows the real lyrics from the existing source |
| B7 | Bar order | As drawn: Home, Library, Discover, Search (other themes use Home, Discover, Library, Search). Bento owns its bar, so only Bento changes |

## 14. Verification for each step

- Unit tests for every pure rule added. The palette contrast test is extended to the three palettes. Focused tests only.
- `ExistingLayoutsTest` stays green in every step.
- The PR shows a screenshot of each built screen next to its mockup PNG and lists anything dropped.
- `python3 docs/design/bento/_src/check_contrast.py` stays green whenever `tokens.json` changes. Rebuild the mockups with `python3 docs/design/bento/_src/build.py`.
- CPU check for the motion: the playing bars and the pending spinner are the only running animations; no frame work is left when nothing plays (Android Studio profiler, or `adb shell dumpsys gfxinfo app.discair` before and after).
- The owner checks each step on the phone before the next one starts.
