# Colour palettes for Soft Brut and Flow (plan)

Status: **P1 built (Soft Brut day, PR #1043); P2 to P5 not built.** The owner picked the palettes on 2026-11-13. This document is the spec for the implementer: the palette ids, every colour code, the mockups, and the code that has to change so the existing Soft Brut and Flow themes can be drawn in each palette.

## 1. What the owner asked for

- A night mode for Soft Brut and for Flow, and more than one palette for each mode.
- Nothing else changes. Layout, shapes, outline, shadow offsets, type, icons and behaviour of both themes stay as built (`ANDROID_ART_THEMES_PROPOSAL.md`). The app only applies a different set of colours.
- The owner chose from ten proposals per theme (the pick sheet is kept in [`design/android-art-themes/picks/palette-proposals.html`](design/android-art-themes/picks/palette-proposals.html)). The proposals that were not picked are not to be built.

### The picks

| Theme | Mode | Palettes |
|---|---|---|
| Soft Brut | Day | Lavender (the current `softbrut`, unchanged), Mint, Peach, Sky, Lemon |
| Soft Brut | Night | Midnight Mint, Plum Peach, Navy Sky |
| Flow | Day | Warm white (the current `flow`, unchanged), Forest, Raspberry, Violet |
| Flow | Night | Ember, Moss, Plum |

That is 13 new palettes: 4 day and 3 night for Soft Brut, 3 day and 3 night for Flow. The two existing palettes keep their ids, labels and values.

## 2. Files to build from

| File | What it is |
|---|---|
| [`design/android-art-themes/palettes/palettes.css`](design/android-art-themes/palettes/palettes.css) | The colour tokens of the 13 palettes, one class each (`.sb.p-<id>`, `.fl.p-<id>`). Loaded after `soft-brut.css` or `flow.css`. Token names are the ones sections 3 and 4 of the art themes proposal map to `Palette` roles. |
| [`design/android-art-themes/palettes/soft-brut.html`](design/android-art-themes/palettes/soft-brut.html) and [`.png`](design/android-art-themes/palettes/soft-brut.png) | Home, Album and Now Playing in each new Soft Brut palette. |
| [`design/android-art-themes/palettes/flow.html`](design/android-art-themes/palettes/flow.html) and [`.png`](design/android-art-themes/palettes/flow.png) | The same three screens in each new Flow palette. |
| [`design/android-art-themes/palettes/roles.md`](design/android-art-themes/palettes/roles.md) | The tables of section 4 and a ready `Palette(...)` entry for each palette. |
| [`design/android-art-themes/_src/build_palettes.py`](design/android-art-themes/_src/build_palettes.py) | Builds the four files above from the existing mockup pages and checks the contrast floors. `soft-brut.css`, `flow.css` and `shared.css` are not edited. |

The mockups show three screens per palette. Every other screen follows from the same tokens: the existing mockup pages in `design/android-art-themes/soft-brut/` and `flow/` remain the spec for layout, and adding a palette class to their `.phone` elements shows any of them in a new palette.

## 3. Rules

1. **A palette is a `Palette` entry and nothing more.** Each new palette is a new value in `Palettes` with `layout = Layout.CoverStack` (Soft Brut) or `Layout.Flow` (Flow). No new layout, no new screen file, no new setting.
2. **Shape and type are copied from the current theme.** Soft Brut palettes keep `Family.Brutal`, `BrutalShape(10f, 1.5f, 3f)` and `suggestedFontId = "brut_modern"`. Flow palettes keep `Family.Classic`, no shape, and `suggestedFontId = "flow"`.
3. **Day palettes go in `Palettes.Light`, night palettes in `Palettes.Dark`.** That is what makes the night mode work: the owner sets a Soft Brut or Flow palette as the Day theme and another as the Night theme in Appearance, and the existing "follow the system" choice switches between them. No pairing logic is added (see open point O1).
4. **Soft Brut at night:** the outline and the hard shadow are the light outline colour (`edge` = `edgeStrong` = `shadowColor`), the fills stay pastel, and whatever is drawn on a pastel fill uses `onAccent` (dark). By day `onAccent` equals `text`, which is why the current code can get away with either.
5. **Flow at night:** the accent is bright enough to be text on the page and on cards, the label on an accent button is dark (`onAccent`), and the wash behind the album and the player is the dark tone of the cover that the code already computes for dark palettes.
6. **Status colours** are shared per mode, not per palette: day palettes reuse the current theme's values, night palettes use the values the existing dark themes use (section 4.3).

## 4. The colours

Every value below is also in `palettes.css` and in the Kotlin entries of `roles.md`. Where the two disagree, `palettes.css` wins and the build script should be re-run.

### 4.1 Soft Brut

| Palette | id | Mode | page (`rail`, `ink`) | `surface` | `raised` | outline (`edge`, `edgeStrong`, `shadowColor`, `chartBase`) | `text` | `textMuted` | `accent` (`chart1`) | `accentDim` | `onAccent` | `accent2` | `accent3` | `accent4` | soft edge (`chartGrid`) | `chart2` | `minAccentContrast` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SD1 Soft Brut · Mint | `softbrut_mint` | day | `#F5F8F0` | `#FFFFFF` | `#E6EDDD` | `#17211C` | `#17211C` | `#55625A` | `#9BE3C0` | `#DDF5EA` | `#17211C` | `#FFD9A8` | `#C9BBFF` | `#FFD84D` | `#CFD8C6` | `#7F8C84` | 1.3 |
| SD2 Soft Brut · Peach | `softbrut_peach` | day | `#FFF6EE` | `#FFFFFF` | `#F7E6D6` | `#261A15` | `#261A15` | `#6B564C` | `#FFB59A` | `#FFE6DB` | `#261A15` | `#BFE3FF` | `#B9E8C2` | `#FFD84D` | `#E2CFBF` | `#94827A` | 1.5 |
| SD3 Soft Brut · Sky | `softbrut_sky` | day | `#F3F7FB` | `#FFFFFF` | `#E1EAF3` | `#141C2B` | `#141C2B` | `#556073` | `#A9CCFF` | `#E0ECFF` | `#141C2B` | `#FFC9DE` | `#A6E9CB` | `#FFE066` | `#C9D4E0` | `#808B9C` | 1.5 |
| SD4 Soft Brut · Lemon | `softbrut_lemon` | day | `#FBF8E9` | `#FFFFFF` | `#F0EBCF` | `#1F1D12` | `#1F1D12` | `#615C45` | `#FFDF5C` | `#FFF4BF` | `#1F1D12` | `#C9BBFF` | `#A6E9CB` | `#FFB59A` | `#D9D3B3` | `#8C876E` | 1.2 |
| SN2 Soft Brut · Midnight Mint | `softbrut_midnight_mint` | night | `#101714` | `#18221D` | `#223029` | `#DDEFE3` | `#EFF8F1` | `#A9C0B2` | `#9BE3C0` | `#1F4636` | `#101714` | `#FFD9A8` | `#C9BBFF` | `#FFD84D` | `#31443A` | `#7E9487` | 3.0 |
| SN3 Soft Brut · Plum Peach | `softbrut_plum_peach` | night | `#1B1416` | `#261C1F` | `#35272B` | `#F6E4DC` | `#FFF3EE` | `#CDB3AD` | `#FFB59A` | `#55302A` | `#1B1416` | `#BFE3FF` | `#B9E8C2` | `#FFD84D` | `#4A383C` | `#9A827D` | 3.0 |
| SN4 Soft Brut · Navy Sky | `softbrut_navy_sky` | night | `#0F1520` | `#17202F` | `#212D42` | `#DCE7F7` | `#F0F5FF` | `#A7B5CC` | `#A9CCFF` | `#24406B` | `#0F1520` | `#FFC9DE` | `#A6E9CB` | `#FFE066` | `#2F3D57` | `#7D8BA3` | 3.0 |

### 4.2 Flow

| Palette | id | Mode | page (`rail`, `ink`) | `surface` | `raised` (`chartGhost`) | `edge` (`chartGrid`) | `edgeStrong` (`chartBase`) | `text` | `textMuted` | `accent` (`chart1`) | `accentDim` | `onAccent` | `chart2` | `chart3` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD2 Flow · Forest | `flow_forest` | day | `#F8F9F4` | `#FFFFFF` | `#E9EDE2` | `#DBE0D2` | `#7D8672` | `#12150F` | `#596051` | `#1B7340` | `#D9EEDF` | `#FFFFFF` | `#87907C` | `#D0D6C6` |
| FD3 Flow · Raspberry | `flow_raspberry` | day | `#FCF8F8` | `#FFFFFF` | `#F1E8E9` | `#E5DADB` | `#8E7F82` | `#171113` | `#6A5C5F` | `#BE2260` | `#FADCE6` | `#FFFFFF` | `#96878A` | `#DCCFD1` |
| FD4 Flow · Violet | `flow_violet` | day | `#F9F8FC` | `#FFFFFF` | `#ECEAF3` | `#DEDBE8` | `#827D93` | `#13111A` | `#5F5A6E` | `#6A3BD2` | `#E7DEFA` | `#FFFFFF` | `#8A859B` | `#D3CFE0` |
| FN1 Flow · Ember | `flow_ember` | night | `#12110F` | `#1C1A17` | `#2A2723` | `#35312C` | `#8A8377` | `#F5F1EA` | `#A9A296` | `#FF8A4C` | `#4A2A17` | `#1A0F08` | `#8A8377` | `#4A453E` |
| FN3 Flow · Moss | `flow_moss` | night | `#0E1311` | `#171E1A` | `#232C27` | `#2D3832` | `#7A887F` | `#EEF5F0` | `#9FAFA5` | `#5FD28C` | `#173D27` | `#06170D` | `#7A887F` | `#3D4A43` |
| FN4 Flow · Plum | `flow_plum` | night | `#151015` | `#1F181F` | `#2D232D` | `#3A2E3A` | `#8C7C8C` | `#F7EEF5` | `#B3A2B0` | `#FF7FAE` | `#4D1F33` | `#2A0A17` | `#8C7C8C` | `#4C3D4C` |

### 4.3 Status colours (shared per mode)

| Role | Soft Brut day | Soft Brut night | Flow day | Flow night |
|---|---|---|---|---|
| `ok` / `okDim` | `#1B6B33` / `#D9EEDD` | `#86D39B` / `#1F3326` | `#1B7339` / `#DCEEDF` | `#86D39B` / `#1F3326` |
| `caution` / `cautionDim` | `#7F4A00` / `#FBE9C4` | `#F0A640` / `#3D2E14` | `#8A5300` / `#F8E8CC` | `#F0A640` / `#3D2E14` |
| `chartRed`, `chartRedText` / `dangerDim` | `#B3261E` / `#F8D9D5` | `#FF8A80` / `#40211A` | `#C0271A` / `#F9DCD8` | `#FF7B62` / `#40211A` |
| `info` / `infoDim` | `#1D4FB8` / `#DCE5FB` | `#8FB8E8` / `#1D2C3D` | `#1F5FBF` / `#DCE7F8` | `#8FB8E8` / `#1D2C3D` |

Soft Brut also sets `chart3` to the surface and `chartGhost` to `raised`, as the current palette does.

### 4.4 Flow colours that are not `Palette` roles today

| Palette | chevron | switch, off | hairline on bars | seek track |
|---|---|---|---|---|
| Flow · Forest | `#AEB5A3` | `#D0D6C6` | `rgba(0,0,0,.08)` | `rgba(18,21,15,.14)` |
| Flow · Raspberry | `#BBADB0` | `#DCCFD1` | `rgba(0,0,0,.08)` | `rgba(23,17,19,.14)` |
| Flow · Violet | `#B2AEC2` | `#D3CFE0` | `rgba(0,0,0,.08)` | `rgba(19,17,26,.14)` |
| Flow · Ember | `#6B655B` | `#4A453E` | `rgba(255,255,255,.10)` | `rgba(245,241,234,.18)` |
| Flow · Moss | `#5E6B63` | `#3D4A43` | `rgba(255,255,255,.10)` | `rgba(238,245,240,.18)` |
| Flow · Plum | `#6E5F6E` | `#4C3D4C` | `rgba(255,255,255,.10)` | `rgba(247,238,245,.18)` |

The current Flow code holds the first two as literals and the hairline as black at 8%; section 5.3 makes them follow the palette. The bar fill is already `surface` at 86% (`FlowRules.barFill`), so it needs no change. The depth shadows stay black; the mockups only make them denser at night, which is not a requirement.

### 4.5 Kotlin entries

A ready `Palette(...)` entry for each of the 13 palettes is in [`design/android-art-themes/palettes/roles.md`](design/android-art-themes/palettes/roles.md), written in the form `Palette.kt` uses.

## 5. Code changes

File and line references are to `main` at `adb9892e`. All paths are under `android/app/src/main/kotlin/app/discair/ui/` unless they start with `test/`.

### 5.1 Palettes (`theme/Palette.kt`)

- Add the 13 entries after `Flow`.
- `Palettes.Light`: append `SoftBrutMint, SoftBrutPeach, SoftBrutSky, SoftBrutLemon` after `SoftBrut`, and `FlowForest, FlowRaspberry, FlowViolet` after `Flow`. The list grows from 18 to 25.
- `Palettes.Dark`: append `SoftBrutMidnightMint, SoftBrutPlumPeach, SoftBrutNavySky, FlowEmber, FlowMoss, FlowPlum`. The list grows from 11 to 17. `Night` stays first (the default night theme).
- Ids and labels must stay unique (`PaletteTest`).

### 5.2 Soft Brut: draw on fills with `onAccent`

By day `onAccent` and `text` are the same colour, so content on a pastel fill may be tinted with either today. At night `text` is light and must not be used on a fill. Audit every place a Cover Stack screen draws on `accent`, `accent2`, `accent3` or `accent4` and make the content colour `onAccent`:

- the selected navigation cell and the main play button;
- the primary button (already `onAccent` in the mockup CSS);
- the selected chip and the selected tab;
- tags on `accent3` and `accent4` (`home/CoverStackHome.kt:552`, `discover/CoverStackDiscover.kt:224`);
- the Radio tile on `accent2` (`home/CoverStackHome.kt:464`), including its icon, title, caption and chevron;
- the download badge and the highlighted lyric line.

The seek knob sits on `surface` and is not affected.

`rg "accent[234]?\b" --glob '*CoverStack*' --glob 'BrutalComponents.kt' --glob 'NavIsland.kt'` lists the candidates. `BrutalComponents.kt:105` already uses black on `accent2`.

Other Soft Brut points to check at night, each against the mockup:

- rows marked as playing use `accentDim` as a background with `text` on top; the night tints are dark for that reason;
- the dashed dividers use the soft edge (`chartGrid`), not `edge`;
- screens drawn over artwork (`theme/Theme.kt:91`) swap in a dark copy only for light palettes; a night palette is used as it is, which is the intended result.

### 5.3 Flow: three literals become palette-driven

| Where | Today | Change |
|---|---|---|
| `common/FlowKit.kt:244` `FLOW_SWITCH_OFF` | `#D9D5CB` | the palette's `chart3` (same value as "switch, off" in 4.4; for the current `flow` palette keep `#D9D5CB`) |
| `common/FlowKit.kt:325` `FLOW_CHEVRON` and `common/FlowPages.kt:261` | `#B5B0A5` | the chevron colour of 4.4; for the current `flow` palette keep `#B5B0A5` |
| `common/FlowKit.kt:109` bar hairline | black at 8% | black at 8% on light palettes, white at 10% on dark ones |

The chevron is the one colour with no `Palette` role. Either add an optional role with a default (so no other theme changes), or keep a small id-to-colour table next to `FlowRules`; the implementer chooses, and the current `flow` palette must render exactly as it does now.

Other Flow points to check at night, each against the mockup:

- the wash (`common/FlowPages.kt:119`, `player/NowPlayingSheet.kt:206`) already takes the unsoftened cover colour on a dark palette; confirm text and muted text stay readable over it and darken the wash if they do not;
- the lyric lines use `text` at 50% (`player/CoverStackLyrics.kt:57`), which works in both modes;
- the switch thumb stays white, the round play button stays `text` on `page` (a light disc at night);
- the selected segment of the Picks / New / Played control is `surface` on `raised`.

### 5.4 Appearance

No new control. The three Appearance screens (`settings/AppearanceSettings.kt`, `settings/CoverStackAppearance.kt`, `settings/FlowAppearance.kt`) read the palette lists (two of them filter on `light` and `family`), so the new palettes should appear in the pickers and in the Day and Night theme choices once they are in the lists. Check that the Day picker offers only light palettes and the Night picker only dark ones (`AppearanceRules.sanitizeDay` / `sanitizeNight` already enforce it).

### 5.5 Tests to change or add

- `test/.../theme/PaletteTest.kt:23-25`: counts become 42, 25 and 17.
- `test/.../theme/SoftBrutTest.kt`: "the only Cover Stack" becomes "every Cover Stack palette is one of these eight"; `sanitizeNight("softbrut")` still falls back to Night. "text on the sky tile / mint tag / yellow tag" becomes `onAccent` on `accent2` / `accent3` / `accent4`.
- `test/.../theme/FlowTest.kt`: "the only Flow layout" becomes "every Flow palette is one of these seven".
- New, per family: the tokens of each new palette match section 4; each keeps the current theme's shape, family, layout and suggested font; the contrast floors of `everyTextPairMeetsTheirFloor` / `everyTextPairMeetsItsFloor` hold for every palette of the family (the build script already checks them: text, muted and error text on page, surface and raised; `onAccent` on every fill; each status on its tint; for Flow the accent as text on page and surface, and the strong edge at 3:1).
- `ExistingLayoutsTest` lists palettes by id and needs no change; it must still pass, which proves no existing theme moved.
- The Soft Brut day accents are pastel, so each palette carries its own `minAccentContrast` (table 4.1), as `softbrut` does with 1.7.

## 6. Build steps

Each step is one PR, branched from current `main`, with focused tests only (owner rule: agents never run the full unit suite; CI runs it on the PR head).

| Step | Content |
|---|---|
| P1 | Soft Brut day: Mint, Peach, Sky, Lemon. Palette entries, list order, tests. No screen code should need to change. |
| P2 | Soft Brut night: Midnight Mint, Plum Peach, Navy Sky. Palette entries, the `onAccent` audit of 5.2, tests. |
| P3 | Flow day: Forest, Raspberry, Violet. Palette entries, the chevron and switch colours of 5.3, tests. |
| P4 | Flow night: Ember, Moss, Plum. Palette entries, the hairline of 5.3, the night checks of 5.3, tests. |
| P5 | Closeout: `ACTIVE_WORK.md`, `PROJECT_STATUS.md`, `PROJECT_LOG.md`, `android/DESIGN.md` theme list. |

P1 and P3 may be merged into one PR, and P2 and P4 into another, if the diffs stay small.

## 7. Verification for each step

- The focused theme tests named in 5.5, run and reported by name.
- A screenshot of Home, Album and Now Playing in each new palette on a device or emulator, compared with the PNG in `design/android-art-themes/palettes/`. For night palettes add one screen with tags and the Radio tile (Soft Brut) and Settings with a switch and chevrons (Flow), since those carry the colours of 5.2 and 5.3.
- The two current palettes (`softbrut`, `flow`) look exactly as before.
- Required CI green on the final PR head.

## 8. Limits and open points

- The mockups are drawn pages, not the app. Nothing in this plan has been seen on a device.
- Only three screens per palette were drawn. The contrast floors were checked by script for every palette; the look of the remaining screens was not reviewed palette by palette.
- **O1, pairing.** Day and night palettes are independent choices in Appearance. The app could instead offer a night twin automatically when a Soft Brut or Flow day palette is chosen. Not planned; it needs an owner decision.
- **O2, counts.** The owner asked for three palettes per mode and picked five day palettes for Soft Brut and four for Flow, both including the current one. The plan builds what was picked.
