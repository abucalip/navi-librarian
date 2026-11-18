# Gallery theme for Android: design system and build plan

Status: **design approved by the owner** (2026-11-16); **G1 built** (#1117); **G2 Home built** (#1118); **G3 Album, Artist, Genre built** (#1119); **G4 Discover, Library, Search built** (#1120); **G5 Now Playing, Queue, Lyrics, Radio built**; **G6 Downloads, Stats, Server, Settings, sheets built**. This document is the spec implementing agents build from. The mockups beside it are the spec for every screen ("the mockups are the spec", Round 3 owner rule).

Package: [`docs/design/gallery/`](../../design/gallery/). Start with its [`README.md`](../../design/gallery/README.md).

## 1. What the owner asked for

1. Three new Android theme directions were proposed on 2026-11-16 (A Gallery, B Aura, C Index). The owner chose **A, Gallery**: an editorial theme where every cover is treated as a framed print on a gallery wall, with italic serif titles, a small mono font for catalogue lines, and thin lines (hairlines) instead of cards.
2. The owner asked for a **Radio section on Home, directly below "Artists you return to"**.
3. Palettes were reviewed in three rounds. The owner kept **Day 1 to Day 5 and Night 1 to Night 3** (section 4). Day 1 is the proposal as drawn and is the default.
4. Every mockup is drawn in **Day 1**. The other seven palettes are **colour variations only**: same layout, components, type and icons; only the colour values change. [`pages/palettes`](../../design/gallery/pages/palettes.html) shows Home and the Radio section in all eight.
5. The package holds everything an implementing agent needs: tokens, colour codes, fonts, icons, component measurements, motion values, the Home data sources and the build steps.

## 2. Rules

1. **Ownership.** Gallery is one new `Layout.Gallery` shared by its eight palettes. Every composable it changes is reached through an `isGallery()` branch (as `isFlow()` and `isCoverStack()` do today) and lives in Gallery's own files (section 11). No shared composable changes what it draws for any other layout. `ExistingLayoutsTest` must still pass.
2. **Behaviour is unchanged.** A theme changes how a screen is arranged, never what it does (D-023). Get album, Save, Not this album, Never suggest this artist, Play, Dismiss with its confirmation, the downloads badge, Settings, the mini player and the four destinations stay reachable, with text labels where they have them today.
3. **The mockups are the spec.** Build each screen element by element from its mockup. List anything dropped in the PR.
4. **Artwork first.** Covers are the only large colour on most screens. Colour on controls carries meaning (section 4.1), never decoration.
5. **Contrast.** Every palette passes `PaletteTest` as written, and the Gallery roles pass the extra checks in [`_src/check_contrast.py`](../../design/gallery/_src/check_contrast.py) (all pass today). The rest of the existing rules still apply: 48dp touch targets, state never shown by colour alone, Remove animations respected, missing data said in words.

## 3. Identity in six rules

1. **Prints.** A cover always sits in a mat: `mat` colour, 11dp padding on large covers (Home pick, album page), 14dp on Now Playing, 5dp on anything under 72dp. The print casts a soft wall shadow (section 7.1). Covers have no corner radius.
2. **Placards.** The text under a print is set like a museum label: a catalogue line in DM Mono caps, then the work title in Fraunces italic, then the maker in Manrope.
3. **Hairlines, not cards.** Sections open with a 1dp `edge` rule. Rows are divided by 1dp rules. Nothing else gets a box, fill or shadow, except prints, sheets, the snackbar and the dock.
4. **Type does the switching.** Picks/New/Played, list names, presets and fades are words in Fraunces with a 1.5dp underline on the selected one, never chips or pills. Tabs inside a page are Manrope 600 13 with the same underline.
5. **Two colours with jobs.** `control` (Day 1: ink) fills primary buttons and colours every icon and link. `accent` (Day 1: plum) means state only: playing, live, today, the downloads badge, the progress line, the selected chart series.
6. **Old-style figures.** Track numbers use Fraunces old-style figures (`onum`). Times and counts use DM Mono with tabular figures.

## 4. Colour

### 4.1 Roles

The CSS variables in [`palettes.css`](../../design/gallery/palettes.css) use the `Palette` field names, so the mapping is one to one.

| Role | Used for |
|---|---|
| `ink` | The wall: page background behind everything |
| `rail` | Background of the dock (mini player and bar) |
| `surface` | Sheets, menus, dialogs |
| `mat` | The frame around every cover and artist photo, and the station plates. **New field** (G1) |
| `raised` | Loading skeletons, pressed rows |
| `edge` | Hairlines, section rules, inactive tracker segments, the seek track |
| `edgeStrong` | Switch outline (off), chart baseline |
| `text` | All text that is not muted; the seek line and thumb; the snackbar background |
| `textMuted` | Secondary text, catalogue lines, inactive tabs and bar labels |
| `control` | Primary button fill; every icon; links; the selected tab underline; the selected bar label and its marker; switch on. **New field** (G1) |
| `onControl` | Text and icons on a `control` fill. **New field** (G1) |
| `accent` | State only: playing row, playing bars, live/today labels, downloads badge, mini-player progress, selected chart series |
| `onAccent` | Text on `accent` (the badge number) |
| `ok`, `caution`, `chartRedText`, `info` | Status words: In library, needs attention, failed or Dismiss, information |
| `chart2`, `chart3` | Second and pale chart series |

Dims (`accentDim`, `okDim`, `cautionDim`, `dangerDim`, `infoDim`) are not drawn by Gallery. Give them the derived default (colour at 10% over `surface`); [`check_contrast.py`](../../design/gallery/_src/check_contrast.py) prints the exact values. `chart1` = `accent`, `chartGhost` = `raised`, `chartGrid` = `edge`, `chartBase` = `edgeStrong`, `chartRed` = `chartRedText`.

### 4.2 The eight palettes

Single source: [`tokens.json`](../../design/gallery/tokens.json). `family = Classic`, `shape = null`, `layout = Layout.Gallery`, `suggestedFontId = "gallery"` on all eight.

| Role | Day 1 · Gallery White | Day 2 · Celadon | Day 3 · Mist Teal | Day 4 · Blush Paper | Day 5 · Butter and Cobalt | Night 1 · Graphite Amber | Night 2 · Oxblood Dark | Night 3 · Moss Black |
|---|---|---|---|---|---|---|---|---|
| `ink` | `#F2F2EF` | `#E4ECE5` | `#E2EDEF` | `#F4E9E7` | `#F3EED6` | `#141414` | `#181113` | `#111512` |
| `rail` | `#FFFFFF` | `#F3F8F3` | `#F2F8F9` | `#FCF6F5` | `#FBF8EA` | `#1B1B1B` | `#20171A` | `#171C18` |
| `surface` | `#FFFFFF` | `#F3F8F3` | `#F2F8F9` | `#FCF6F5` | `#FBF8EA` | `#1B1B1B` | `#20171A` | `#171C18` |
| `mat` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#262626` | `#2D2125` | `#222A24` |
| `raised` | `#E8E8E3` | `#D8E2DA` | `#D5E3E6` | `#EADCD9` | `#E9E3C6` | `#242424` | `#2B2024` | `#202721` |
| `edge` | `#DCDCD6` | `#C8D7CC` | `#C5D8DC` | `#E5D2CF` | `#E0D9B8` | `#2E2E2E` | `#33262A` | `#29322B` |
| `edgeStrong` | `#85888F` | `#6F8277` | `#6A8188` | `#8E7579` | `#837D63` | `#76726A` | `#806A6E` | `#6E7B6E` |
| `text` | `#15171C` | `#14342A` | `#0F2E37` | `#3A1820` | `#181E3C` | `#EDE8DE` | `#F3E5E3` | `#E3ECE2` |
| `textMuted` | `#5D6169` | `#4A6056` | `#4A626A` | `#6E5458` | `#5A5C66` | `#A6A29A` | `#B49FA2` | `#9CAA9E` |
| `control` | `#15171C` | `#1E5C46` | `#14596A` | `#86243A` | `#2A3D9E` | `#E9B35A` | `#E6A397` | `#B5D69A` |
| `onControl` | `#FFFFFF` | `#F3F8F3` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#141414` | `#181113` | `#111512` |
| `accent` | `#7A2E55` | `#9A3D22` | `#A3246B` | `#1F5A86` | `#B02E2A` | `#F0C27A` | `#F28B78` | `#C9E3A6` |
| `onAccent` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#141414` | `#181113` | `#111512` |
| `ok` | `#1B6B3A` | `#1B6B3A` | `#1B6B3A` | `#1B6B3A` | `#1B6B3A` | `#8FD6A0` | `#8FD6A0` | `#8FD6A0` |
| `caution` | `#8A5300` | `#7F4A00` | `#7F4A00` | `#7F4A00` | `#784500` | `#F2A65A` | `#F0B35A` | `#F0B35A` |
| `chartRedText` | `#B3261E` | `#AE2219` | `#AE2219` | `#AE2219` | `#A3221C` | `#FF8A73` | `#FF7B6B` | `#FF8A73` |
| `info` | `#1F5A8A` | `#1F5A8A` | `#1F5A8A` | `#1F5A86` | `#2A3D9E` | `#8FB8E8` | `#9DBDF0` | `#9DBDF0` |
| `chart2` | `#85888F` | `#6F8277` | `#6A8188` | `#8E7579` | `#837D63` | `#76726A` | `#806A6E` | `#6E7B6E` |
| `chart3` | `#D3D3CC` | `#C3D2C7` | `#C0D3D7` | `#E0CDCA` | `#DDD5B0` | `#3A3A3A` | `#43333A` | `#36413A` |
| `id` | `gallery` | `gallery_celadon` | `gallery_mist` | `gallery_blush` | `gallery_butter` | `gallery_graphite` | `gallery_oxblood` | `gallery_moss` |
| Label | Gallery · White | Gallery · Celadon | Gallery · Mist Teal | Gallery · Blush Paper | Gallery · Butter and Cobalt | Gallery · Graphite Amber | Gallery · Oxblood | Gallery · Moss Black |

Add the five day palettes to `Palettes.Light` and the three night palettes to `Palettes.Dark`, after the Flow ones. When "Follow the phone" is on and Gallery is chosen, the defaults are Day 1 for light and Night 1 for dark (G4).

### 4.3 Contrast (checked)

`python3 docs/design/gallery/_src/check_contrast.py` runs 32 to 33 checks per palette. These are the `PaletteTest` rules (text, muted, error, caution and ok text on page, surface and raised; label on accent; text on the selected background; accent and strong edge 3:1; muted text over every pastel wash on light palettes), plus `control` on every background at 4.5:1, `onControl` on `control`, text on `mat`, and accent held to 4.5:1 because Gallery uses it as text. **All eight pass.** The lowest results are Day 1 muted text over pastel washes (4.52:1) and Night 2 strong edge on surface (3.51:1).

## 5. Type

### 5.1 Font files

The app's existing `fraunces_variable.ttf` is cut down to weights 600 to 800, upright only, with no optical-size axis. Gallery needs the italic and the lighter weights. The existing `manrope_variable.ttf` stops at 600. So Gallery ships three new files, subset to Latin (Basic Latin, Latin-1, Latin Extended-A, punctuation) and limited to the axes it uses. DM Mono is already in the app.

| File (copy into `android/app/src/main/res/font/`) | Source | Axes kept | Size |
|---|---|---|---|
| [`fraunces_gallery.ttf`](../../design/gallery/fonts/fraunces_gallery.ttf) | Google Fonts `ofl/fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf`, SOFT=0, WONK=0 | `opsz` 9–144, `wght` 300–600 | 133 KB |
| [`fraunces_gallery_italic.ttf`](../../design/gallery/fonts/fraunces_gallery_italic.ttf) | `Fraunces-Italic[SOFT,WONK,opsz,wght].ttf`, SOFT=0, WONK=0 | `opsz` 9–144, `wght` 300–600 | 156 KB |
| [`manrope_gallery.ttf`](../../design/gallery/fonts/manrope_gallery.ttf) | `ofl/manrope/Manrope[wght].ttf` | `wght` 400–800 | 81 KB |
| `dm_mono_400.ttf`, `dm_mono_500.ttf` | already in `res/font` | — | — |

All three are under the SIL Open Font License; the licence texts are in [`fonts/`](../../design/gallery/fonts/). Together they add about 370 KB to the APK (G2). The subsets were made with fontTools `instancer` and `subset`; the commands are in the fonts README.

### 5.2 Font pair

Add `FontPairs.Gallery` (id `gallery`, label "Gallery", title "Fraunces", body "Manrope", `mono` DM Mono, `monoName` "DM Mono"). Register `title` as a family with the upright and italic files, built with `FontVariation.Settings(weight, opticalSizing)` per style. Gallery's own text styles (section 5.3) are defined in `ui/common/GalleryKit.kt` and read the pair through `LocalFontPair` only for the body face, so a user who picks another pair in Appearance still gets Gallery's layout with that pair's faces (D4: suggested, not forced). `PaletteTest.twelvePairsWithUniqueIdsAndDiscairFirst` must move to 13, and the `monoName` set check must include `gallery`.

### 5.3 Type scale

From `tokens.json` → `type`. Sizes are sp. For Fraunces, set `opsz` together with `wght`.

| Style | Face | Weight | Size / line | Tracking | Used for |
|---|---|---|---|---|---|
| Wordmark | Fraunces Italic, opsz 96 | 600 | 25 / 25 | −0.02em | "discair" in the Home top bar |
| Large title | Fraunces, opsz 96 | 400 | 34 / 38 | −0.02em | Page titles (Discover, Library, Radio, Downloads…) |
| Work title XL | Fraunces Italic, opsz 72 | 420 | 36 / 38 | −0.01em | Album and artist page title |
| Work title | Fraunces Italic, opsz 72 | 420 | 30 / 32 | −0.01em | Home pick, Now Playing, live radio, sheet titles |
| Work title M | Fraunces Italic, opsz 72 | 420 | 22 / 26 | −0.01em | Discover entries, This week, sheet headers |
| Section heading | Fraunces, opsz 48 | 400 | 21 / 24 | 0 | "Played lately", "Radio"… |
| Source switch | Fraunces, opsz 24 | 400 | 17 / 20 | 0 | Picks / New / Played, list names, presets |
| Row work | Fraunces Italic, opsz 24 | 420 | 16 / 20 | 0 | Album or song name in rows, grid captions, the mini player |
| Genre list | Fraunces, opsz 48 | 300 | 22 / 32 | 0 | The Genres line on Home |
| Lyric | Fraunces, opsz 36 | 400 | 24 / 32 | −0.01em | Lyrics; the current line is italic in `text`, the others `textMuted` at 55% |
| Track number | Fraunces, opsz 24, `onum` | 400 | 19 / 24 | 0 | Album track list |
| Numeral | Fraunces, opsz 72, `lnum` | 400 | 40 / 40 | −0.02em | Library stats, crossfade length |
| Row title | Manrope | 600 | 15 / 20 | 0 | Rows that are not works (artists, stations, settings) |
| Body | Manrope | 400 | 14 / 21 | 0 | Body text, maker line under a title |
| Small | Manrope | 400 | 12.5 / 18 | 0 | Secondary lines |
| Button | Manrope | 700 | 14 / 14 | 0 | Button labels |
| Tab | Manrope | 600 | 13 / 16 | 0 | In-page tabs |
| Bar label | Manrope | 600 | 11 / 14 | 0 | Navigation labels |
| Catalogue | DM Mono, caps | 500 | 10.5 / 14 | +0.07em | Eyebrows, catalogue lines, state words, section links |
| Time | DM Mono, `tnum` | 400 | 12 / 16 | 0 | Durations, seek times, axis labels |

Rule: **a work's name (album, song, station show) is italic; a person's or place's name (artist, station, genre, setting) is upright.**

## 6. Icons

[`icons/`](../../design/gallery/icons/) holds 46 SVGs (24 by 24) and [`icons/GalleryIcons.kt.txt`](../../design/gallery/icons/GalleryIcons.kt.txt), a ready `GalleryIcons` object written by the build script. It has the same `stroked`/`filled` builder as `ArtIcons` with `strokeLineWidth = 1.4f`, round caps and joins, and property names that match `ArtIcons` one for one, plus `Ban` (Never suggest), `RepeatOne` and `MusicNote`. Circles are written as arcs so `PathParser` reads them.

- Stroke 1.4dp, round caps and joins, outline only. Play, pause, next, previous and the three dots are the only filled glyphs.
- Sizes: 22dp default (bar, top bar, rows); 18dp inline (pager arrows, chevrons, Sort); 26dp transport; 28dp inside the 68dp Play circle; 19dp in buttons, 16dp in small buttons.
- Colour: always `control` (on fills, `onControl`). Never `accent`, except the playing bars.
- No circles, tiles or pills behind icons. Touch targets stay 44 to 48dp with the glyph centred.
- Discover is a compass, Settings is sliders, Downloads is an arrow onto a line, Get is a cloud with an arrow, Save is a bookmark.

In Gallery, read icons through a small switch (`GalleryIcons` when `isGallery()`, else today's `ArtIcons`/`PlayerIcons`) so other themes keep their glyphs.

## 7. Components

Every measurement is in [`gallery.css`](../../design/gallery/gallery.css) (1 CSS px = 1dp). The board is [`pages/components`](../../design/gallery/pages/components.html).

### 7.1 Prints

| Size | Mat | Shadow (day) | Shadow (night) |
|---|---|---|---|
| Large (Home pick 246, album 228, artist photo 200) | 11dp | `0 1 2 rgba(shadow,.08)` + `0 26 36 −24 rgba(shadow,.50)` | `0 30 40 −22 rgba(0,0,0,.90)` |
| Now Playing (300) | 14dp | as large | as large |
| Small (grid 151, rows 48–64, plates 76) | 5dp | `0 1 2 rgba(shadow,.08)` + `0 12 18 −12 rgba(shadow,.45)` | `0 14 20 −12 rgba(0,0,0,.85)` |
| Mini player cover (38) | none | none | none |

`shadow` is each palette's text colour as RGB (`shadowRgb` in tokens). Draw it in Compose with `Modifier.drawBehind` and a blurred `Paint` (`BlurMaskFilter`), or with two `shadow()` layers. The negative spread is what keeps it under the print like a wall shadow; a plain elevation shadow is not a match. Night palettes add a **spot**: a radial glow (60% × 55% at the centre of the hero, palette colour at 7–9% opacity, transparent at 70%) behind the Home pick and the Now Playing cover only.

### 7.2 Controls

| Component | Spec |
|---|---|
| Primary button | 44dp high, radius 2, 18dp side padding, `control` fill, `onControl` label (Manrope 700 14), icon 19 with an 8dp gap. Small: 36dp, 12dp padding, 12.5 label, icon 16 |
| Text button | No fill; `control` icon and label, label underlined with a 1dp rule 1dp below |
| Outlined button | 1dp inset `control` outline, `control` label. Danger: `chartRedText` outline and label |
| Icon button | 44dp square, glyph 22, `control`, no background |
| Source switch | Fraunces 17 words, 22dp apart; selected `text` with a 1.5dp `control` underline, others `textMuted`. Scrolls sideways when the words do not fit |
| Tabs | Manrope 600 13, 22dp apart, 1dp `edge` rule under the row, 1.5dp `control` underline on the selected tab |
| Section head | 34dp above; 1dp `edge` rule; 12dp below the rule, Fraunces 21 heading left, DM Mono link right (`control`, underlined); 14dp to content |
| Row | Min 64dp (56 in the track list), 14dp gap, 1dp `edge` divider, lead (48dp print, 52dp photo print or 36dp icon) · title and sub · trail (state word, small button, icon button) |
| State words | DM Mono 10.5 caps: "In library" in `ok`, "Requested" and "New" in `textMuted`/`ok`. Never a coloured dot alone |
| Tag | DM Mono 10 caps in a 1dp `edge` box, 5×7 padding (the quality tag `FLAC 16/44.1`). Accent variant for "On air" |
| Badge | 15dp pill, `accent` fill, `onAccent` Manrope 700 9 |
| Switch | 44×26 pill. Off: 1dp `edgeStrong` outline, 18dp `edgeStrong` knob. On: `control` fill, `onControl` knob |
| Search field | No box: Fraunces 22 text over a 1.5dp `text` rule; search icon left, clear right |
| Download tracker | Four 2dp segments 4dp apart (`text` when reached, `edge` ahead, `chartRedText` on the failed step) with DM Mono step names under them |
| Seek | 1.5dp `edge` track, `text` played part, 10dp `text` thumb; DM Mono times below; remaining time with a minus sign |
| Transport | 26dp glyphs in `control`; Play is a 68dp `control` circle with a 28dp `onControl` glyph |
| Ranked bars | 6dp bars, `chart3`, the first in `accent`; label 96dp wide, value in DM Mono |
| Charts | 1dp `edge` grid, 1dp `edgeStrong` baseline, 1.5dp `text` line, `accent` point; column pairs `chart3` (owned) and `accent` (played) |
| Banner | 1dp `caution` rule above and `edge` below, `caution` icon, text in `text`, a `control` link right |
| Skeleton | `raised` blocks inside the same mats; no shimmer |

### 7.3 Bars and surfaces

| Component | Spec |
|---|---|
| Home top bar | 54dp. Wordmark left (20dp inset); downloads (with badge) and settings icon buttons right |
| Page top bar | 52dp. Back icon button left, DM Mono catalogue title centred ("ALBUM", "RADIO"), three dots or a text link right. Then the page head: catalogue line, large title |
| Dock | `rail` fill with a 1dp `edge` rule on top. The mini player (58dp) sits above the bar (62dp), divided by a 1dp `edge` rule. The mini player's progress is a 1.5dp `accent` line on its top edge |
| Mini player | 16dp inset, 38dp cover (no mat), row work title over Manrope 12 artist, pause icon button |
| Bar | Four cells, icon 22 over Manrope 600 11; selected cell in `control` with a 22×2dp `control` marker at its top edge; the marker slides between cells (section 8) |
| Sheet | `surface`, top radius 14, 10dp top padding with a 36×4 `edge` handle, 20dp sides. Header: small print 58, work title M, catalogue line, then a 1dp rule. Option rows 62dp with icon 22, Manrope 600 15 title and optional Small explanation. Scrim: rgba(10,10,14,.42) |
| Snackbar | 12dp from the sides, 14×16 padding, radius 2, `text` fill with `ink` text; Undo in Manrope 700 underlined. Sits 8dp above the dock |

## 8. Motion

Values are in `tokens.json` → `motion`. Try them on the live page [`pages/motion`](../../design/gallery/pages/motion.html) (tap the Laughing Stock print, the back arrow, the mini player, the down arrow and the three dots beside Save). Every duration goes through `MotionRules.duration`, so it becomes 0 when the phone removes animations. Add `Layout.Gallery` to `MotionRules.familyFor` → `MotionFamily.Standard`.

| Moment | What moves | Duration | Curve |
|---|---|---|---|
| Open an album from any cover | The tapped print travels and scales into the album page's print (shared element: the app already wraps the NavHost in `SharedTransitionLayout`, provides `LocalSharedTransitionScope`, and has `Modifier.sharedCover(routeKey)` in `ui/common/SharedCover.kt`; put it on the print, mat included) | 420ms | cubic-bezier(0.3, 0, 0.1, 1) |
| Back from the album | The print returns to its place on the page below | 420ms | same |
| Page content arriving | The leaving page fades out (180ms). The new page fades in (260ms after 80ms), and its first six blocks (print, placard, actions, tabs, sections) rise 10dp, 40ms apart | 420ms each | cubic-bezier(0.2, 0.8, 0.2, 1) |
| Bar marker | The 22×2 marker slides to the chosen cell | 450ms | cubic-bezier(0.2, 0.8, 0.2, 1) |
| Open Now Playing | The page rises from the bottom while the mini cover grows into the 300dp print (shared key `np`); the dock slides away | 440ms | cubic-bezier(0.3, 0, 0.1, 1) |
| Close Now Playing | The page falls; the dock slides back up | 360ms | same |
| Sheet | Scrim fades in (260ms); the sheet glides up with no overshoot (380ms). Closing: 260ms, cubic-bezier(0.5, 0, 0.8, 0.4) | 380 / 260ms | cubic-bezier(0.2, 0.8, 0.2, 1) |
| Snackbar | Fades in and rises 14dp, holds 4s | 280ms | cubic-bezier(0.2, 0.8, 0.2, 1) |
| Playing bars | Three 2.5dp bars in `accent` move only while a song plays, and stop when animations are off (CPU rule: one small animated view, not a whole-screen redraw) | — | — |

There are no springs with overshoot, no parallax and no looping background motion. The calm is part of the identity.

As built (G7): every row above except the Sheet. Material 1.3.2's `ModalBottomSheet` has no setting for its animation, so Gallery's sheets keep Material's slide and scrim timing (about 300ms). The player is a dialog window, so its cover flight is drawn by hand from the dock's mini cover to the print (`GalleryFlight` in `GalleryShell.kt`) rather than through the shared-element layout.

## 9. Home

Mockup: [`pages/home`](../../design/gallery/pages/home.html) (six frames). From top to bottom:

| # | Section | Content | Data |
|---|---|---|---|
| 1 | Top bar | Wordmark, downloads with badge, settings | as today |
| 2 | Source switch | Picks · New · Played (choice remembered, as Flow) | as `FlowHomeRules` |
| 3 | Hero | Large print (246dp) on the wall; placard: catalogue line ("Pick for tonight", "New in your library", "Played an hour ago") with a pager (‹ 01 / 12 ›, swipe the print too), work title, "Artist, year", muted genre and owned state. Actions: Picks → Get album, Save, three dots; New and Played → Play, Shuffle, three dots | `picks`, recently added, recently played |
| 4 | Played lately | Two small prints with captions; All | recently played albums |
| 5 | Artists you return to | Three portrait photos (4:5) with name and album count; All | `HomeArtists` |
| 6 | **Radio** (new) | Four station plates (76dp prints: logo, else initials on a neutral tile), name, and when last heard ("Today" in `accent`, "Yesterday", weekday, date). Under them, "Heard on FIP this morning": the latest two plays as rows with In library / Requested / Get. Link: All stations. Opens Radio; a plate opens that station live | `radioStations()`; last heard per station = newest `radioPlays().heardAt` for its `stationName`; rows = the newest two `radioPlays()` (`inLibrary` → "In library", `grabbed` → "Requested", else Get when the play has an artist). Hidden when there are no stations |
| 7 | This week | One insight placard (anniversary, never played…) with Play and "Why this?" | the existing insight source |
| 8 | Arrivals | Up to two rows: in progress (percent) and arrived today; link Downloads | `AcquisitionHub` |
| 9 | Genres | One Fraunces line of genre names divided by thin slashes, the favourite in italic; each name opens its genre | as today |
| 10 | Library line | One DM Mono line: albums · artists · hours this month, with a chevron; opens Library stats. The only statistics on Home | as today |

States (frame 6): a service banner above the switch; skeleton print and placard while picks load; "Play a few albums and the artists you come back to are hung here." when there is no listening yet. Stations and plays carry no artwork today. A play with no cover shows an empty mat with the `note` icon, and a station with no logo shows its initials.

## 10. Every page and its file

Each page is an `.html` (open it in a browser and measure) and a `.png` in [`docs/design/gallery/pages/`](../../design/gallery/pages/). Frames are 360 × 780dp.

| File | Frames |
|---|---|
| `home` | First screen; scrolled to Played lately, Artists and Radio; Radio and This week; Arrivals, Genres and the library line; Played selected; loading, failing service and no listening |
| `album-artist-genre` | Album owned with the third song playing (tabs Songs, Info, Reviews, Booklet; Similar albums); album not in the library (Get album, the note, Info, Why this pick); Artist (photo print, Top songs, In your library); Genre |
| `player` | Now Playing (300dp print, quality tag, seek, transport, Lyrics/Queue/Equalizer/Crossfade); Queue; Lyrics (stand-in text; real lyrics come from the existing lyrics source) |
| `discover` | Lists (catalogue entries: print 104, "No. 01 · genre", title, maker, the reason in Fraunces italic, Get/Save/three dots); Insights (taste ranked bars, This week, Never played); taste sheet |
| `library-search` | Artists (photo prints in rows), Albums (two-column prints), Search (underline field; groups Artists, Albums, Songs with counts; owned state in words; Get) |
| `radio` | Stations (plates, the playing one with bars); Live radio (300dp plate, On air, Get this song); Heard on radio (Get, In library, Requested, an unnamed play) |
| `downloads-stats-server` | Downloads (tracker, actions); Library stats (numerals, line and column charts); Server (banner, services in words, activity) |
| `settings` | Settings; Appearance (Day and Night palette swatches as small prints; Follow the phone / One theme; Type); Equalizer; Crossfade |
| `sheets` | Pick menu; song menu; Dismiss confirmation; snackbar with Undo |
| `palettes` | Home and the Radio section in all eight palettes (colour variations only) |
| `components` | Token swatches, the type scale, every control, prints, dock, sheet and the 46 icons |
| `motion` | Live prototype with the motion values (section 8) |

Not drawn, and built with the components above and no new arrangement: tablet widths; the album Booklet and cover picker sheets; Paths sheets and panes; Sonic path; the Saved list; empty states not on `home` frame 6. Each of these uses Gallery's sheet, row, tab and button looks.

## 11. Where the code goes

New files only, so no other theme's file changes shape:

| New file | Holds |
|---|---|
| `ui/common/GalleryKit.kt` | Text styles (5.3), `GalleryPrint` (mat, shadow, spot), buttons, source switch, tabs, section head, rows, state words, tag, switch, tracker, banner, `GalleryRules` (pure: pager label, last-heard words, Radio rows) |
| `ui/common/GalleryIcons.kt` | From `icons/GalleryIcons.kt.txt` |
| `ui/common/GalleryShell.kt` | Dock (mini player and bar with the sliding marker), top bars, sheet and snackbar shapes |
| `ui/home/GalleryHome.kt`, `GalleryHomeRules.kt` | Section 9 |
| `ui/album/GalleryAlbum.kt`, `ui/artist/GalleryArtist.kt`, `ui/GalleryGenre.kt` | Album, Artist, Genre |
| `ui/discover/GalleryDiscover.kt`, `ui/library/GalleryLibrary.kt`, `ui/search/GallerySearch.kt` | Discover, Library, Search |
| `ui/player/GalleryNowPlaying.kt` | Now Playing, Queue, Lyrics |
| `ui/radio/GalleryRadio.kt`, `ui/downloads/GalleryDownloads.kt`, `ui/stats/GalleryStats.kt` | Radio, Downloads, Stats |
| `settings/GallerySettings.kt` | Settings, Appearance, Server, Equalizer, Crossfade |
| `res/font/fraunces_gallery.ttf`, `fraunces_gallery_italic.ttf`, `manrope_gallery.ttf` | Section 5.1 |

Existing files that gain a Gallery branch (one `isGallery()` branch each, as Flow did): `theme/Palette.kt` (eight palettes, `Layout.Gallery`, the three new fields with defaults), `theme/Theme.kt` (font pair), `theme/Motion.kt` (`familyFor`), `MainShell.kt`, `HomeScreen.kt`, `AlbumScreen.kt`, `ArtistScreen.kt`, `GenreScreen.kt`, `DiscoverScreen.kt`, `LibraryScreen.kt`, `SearchScreen.kt`, `NowPlayingSheet.kt`, `SeekBar.kt`, `RadioScreen.kt`, `HeardScreen.kt`, `RadioNowPlayingSheet.kt`, `DownloadsScreen.kt`, `StatsScreen.kt`, the settings screens, and the shared buttons, tabs, switch, progress, divider, text field, snackbar and sheet (as F1 did for Flow). Update `ARCHITECTURE.md` in G1 for the new `Gallery*` files.

## 12. Build steps

Each step is one PR with focused tests (JDK 17; never the full suite), in this order.

| Step | Objective | Acceptance |
|---|---|---|
| **G1** Palettes, fonts, shell | `Layout.Gallery`; the eight palettes and the `control`/`onControl`/`mat` fields (defaults: `text`, `ink`, `surface`, so no other palette changes); the font files and `FontPairs.Gallery`; `GalleryIcons`; `GalleryKit` components; dock, bars, sheet, snackbar; Gallery branches in the shared controls; `MotionRules.familyFor` | `pages/components` matched; theme choosable in Appearance (Day and Night groups); `PaletteTest` and `ExistingLayoutsTest` pass with the new palettes; a `GalleryTest` pins the eight palettes' tokens to `tokens.json` |
| **G2** Home | Section 9 with the Radio section; the shared print transition into the album page | `pages/home` matched in all six frames; `GalleryHomeRulesTest` (pager label, last-heard words, Radio rows from plays: In library / Requested / Get / none) |
| **G3** Album, Artist, Genre | Album owned and missing, Artist, Genre | `pages/album-artist-genre` matched |
| **G4** Discover, Library, Search | | `pages/discover`, `pages/library-search` matched |
| **G5** Now Playing, Queue, Lyrics, Radio | Player rise and fall with the shared cover | `pages/player`, `pages/radio` matched |
| **G6** Downloads, Stats, Server, Settings, sheets; closeout | | `pages/downloads-stats-server`, `pages/settings`, `pages/sheets` matched; `ACTIVE_WORK.md` updated |

## 13. Open decisions

| # | Point | Proposed answer |
|---|---|---|
| G1 | `Palette` has no fields for the button/icon colour or the mat | Add `control`, `onControl` and `mat` as optional fields with defaults (`text`, `ink`, `surface`), so every existing palette is unchanged and only Gallery names them. `overArtwork` copies them through |
| G2 | Three new font files (about 370 KB) | Needed for the italic and the light weights (5.1). If APK size matters more, drop `manrope_gallery.ttf` and use Manrope 600 for buttons (saves 81 KB) |
| G3 | Shared element transitions | Use the existing `SharedTransitionLayout`, `LocalSharedTransitionScope` and `Modifier.sharedCover` (Compose BOM 2025.04.01). Where a screen is not under it (sheets), fall back to the fade and rise |
| G4 | Defaults for "Follow the phone" | Day 1 Gallery White and Night 1 Graphite Amber |
| G5 | Lyrics in the mockup | Stand-in text; the screen shows the real lyrics from the existing source |

## 14. Verification for each step

- Unit tests for every pure rule added, and the palette contrast test extended to the eight palettes. Focused tests only.
- `ExistingLayoutsTest` stays green in every step.
- A screenshot of each built screen next to its mockup PNG in the PR, with a list of anything dropped.
- `python3 docs/design/gallery/_src/check_contrast.py` stays green whenever `tokens.json` changes. Rebuild the mockups with `python3 docs/design/gallery/_src/build.py`.
- The owner checks each step on the phone before the next one starts.
