---
name: Navidrome Librarian
description: An ordered, scannable chart rundown for a self-hosted music library, with requests that close the loop.
colors:
  ink-rail: "#0f0e0d"
  ink: "#141211"
  surface: "#1c1a18"
  surface-raised: "#252220"
  surface-hover: "#2d2926"
  edge: "#34302c"
  edge-strong: "#787168"
  text: "#f4efe6"
  text-muted: "#b4ac9f"
  text-subtle: "#9c958a"
  accent: "#f5d33f"
  accent-hover: "#f8e08a"
  accent-dim: "#554b26"
  on-accent: "#141211"
  chart-red: "#ff5a3c"
  chart-red-text: "#ff7b62"
  ok: "#86d39b"
  caution: "#f0a640"
typography:
  display:
    fontFamily: "Big Shoulders Display, Arial Narrow, sans-serif"
    fontWeight: 700
    letterSpacing: "0.025em"
  body:
    fontFamily: "Schibsted Grotesk, sans-serif"
    fontWeight: 400
    fontSize: "15px"
    lineHeight: 1.55
  mono:
    fontFamily: "JetBrains Mono, monospace"
    fontWeight: 400
rounded:
  chip: "2px"
  control: "4px"
  panel: "6px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "24px"
  "6": "32px"
  "7": "48px"
  "8": "64px"
---

# Design System: Navidrome Librarian

<!-- Regenerated 2026-10-19 from the built front end at the end of Phase 7 (origin/main 8849e7e, after PR #394). Drift between this file and the built CSS is recorded in docs/DESIGN_SYSTEM.md section 16. -->

## Overview

**Creative North Star: "The Chart Rundown"**

The interface reads like a weekly music-press chart for the owner's own collection. It is ordered and scannable: artwork and titles lead, metadata stays quiet, and one action closes each row. Depth comes from a ground ladder (ink, surface, raised), not from shadows or borders. Chart red is the signature mark; yellow means "do this" or "selected".

The system was chosen in `docs/DESIGN_SYSTEM.md` (owner decisions D1–D6) and is now built across the redesign phases. The tokens in the frontmatter are the ones `static/app.css` declares. Some shipped rules fall outside the system (a few one-off sizes, colours and a diagonal stripe); they are listed under Do's and Don'ts and in `docs/DESIGN_SYSTEM.md` section 16, not treated as part of the system.

**Key Characteristics:**
- Warm ink ground with a darker rail; flat surfaces, no glass or glow.
- One working accent (yellow) and one signature accent (chart red) that is never the sole carrier of an error.
- Condensed display numerals and headings; grotesque UI text; mono for technical metadata only.
- Self-hosted fonts and icons (`static/fonts/`, `static/icons.svg`); no third-party runtime requests.

## Colors

Warm neutrals with two accents. Yellow is the working accent; chart red is the signature and the error hue.

- **Ground ladder:** `ink-rail` (rail and header), `ink` (page), `surface` (panels, inputs, base buttons), `surface-raised` (menus, modal, selected rows), `surface-hover` (row and control hover).
- **Edges:** `edge` is decorative (dividers, row separators; 1.33:1 on `surface`). `edge-strong` is the boundary of every control and meets 3:1 on its surface.
- **Text:** `text` (primary), `text-muted` (secondary), `text-subtle` (metadata; the floor for functional labels).
- **Accent:** `accent` marks selection, focus rings and the active rail item; `on-accent` is the text on an accent fill. `accent-hover` and `accent-dim` are its hover and selected-background states.
- **Chart red:** `chart-red` for rank numerals, the header rule and error glyphs; `chart-red-text` when red is used as small text.
- **States:** `ok` and `caution` are tokens for confirmed and stalled states. Every state also carries a glyph and a text label; colour is never the only signal.

Contrast was measured on the Phase 1 build (empty states, 1440px): 19 text pairs on login, dashboard and Settings, lowest 6.30:1, all passing AA. The Phase 7 audit (`docs/UI_BACKLOG_EXECUTION.md` section 24) re-checked text on the reconstructed pages. Red text, caution and acquisition states were not re-measured on the rendered build.

## Typography

- **Display** (Big Shoulders Display 700 and 800, self-hosted WOFF2, preloaded): page heads and rank numerals only. Never in buttons, inputs, labels or data cells.
- **Body** (Schibsted Grotesk 400, 500 and 600, self-hosted): all UI text. Use tabular figures for numbers.
- **Mono** (JetBrains Mono 400 and 500, self-hosted): technical metadata only (bitrate, format, paths, IDs).

Fonts load through `static/fonts/fonts.css` with `font-display: swap`. The Google Fonts import is gone. Requests for other weights resolve to the nearest shipped face.

The type scale tokens (`--text-xs` 12px to `--text-2xl` 30px, `--num-row`, `--num-lead`) are defined. Most components still use literal sizes, and some fall below the 12px floor (9px and 11px labels). The inventory is in `docs/DESIGN_SYSTEM.md` section 16.

## Layout

Single column content inside a fixed header and a left rail. The rail carries the navigation in two groups (Discover, Collection) with a System group in the header menu; the header carries the page identity and tools. Spacing follows the 4px base in the spacing tokens. There is no hero banner and no right rail.

Breakpoints as built: a 232px labelled rail above 900px; a 72px icon rail from 621px to 900px; a bottom tab bar under 620px that scrolls sideways at 390px. Content gutters are 34px at each side above 620px (section 6 says 32px; see `docs/DESIGN_SYSTEM.md` section 16) and 14px below 620px. Responsive behaviour was verified at 1440, 1200, 900, 620 and 390px on the Phase 1 pages and the Phase 7 audit reconstructions. No capture showed horizontal page overflow.

## Elevation & Depth

Flat by default. Depth comes from the ground ladder, with 1px `edge` dividers. The system's shadow is `--shadow-menu` (`0 8px 24px rgba(0,0,0,.45)`) on the floating header menu. The built CSS also carries three literal shadows (the Get control over artwork and the toast surface); they are outside the system and listed in `docs/DESIGN_SYSTEM.md` section 16.

## Shapes

- `radius-chip` 2px: artwork, chips and the category label.
- `radius-control` 4px: buttons, inputs, selects.
- `radius-panel` 6px: panels, menus, the modal and toasts.
- Pill (999px) on the Get control in ranked rows, and circles (50%) on the Get control over artwork and the Get arc. Both are sanctioned by the Get section of the system.

No nested cards. Dividers are 1px `edge`. A 3px-radius literal remains on the rail items and two artwork-adjacent labels; it is off the scale.

## Components

**Buttons.** The base button is a `surface` fill with an `edge-strong` border, `text` label, 4px radius and a 44px minimum height on controls. Hover changes the fill to `surface-hover` and the border to `accent`. Disabled is 55% opacity with a wait cursor. There is no separate yellow primary button in the built CSS: the accent fill appears on the Get control's requested state and on selection.

**Focus.** Every focusable element shows a 2px `accent` outline, offset 2px. Inside clipped or dense containers (the header menu panel and acquisition rows) the offset is negative.

**Get / request control.** The `.get-album` state machine is kept: idle, pending (an arc with `aria-busy` and disabled), requested (only after the server confirms, with a drawn tick and an `accent` fill) and failed (retry). Over artwork it is a 46px circle, 58px in the modal; in ranked rows it is a 44px-tall pill with a label. The server confirmation rule is unchanged.

**Ranked row.** Numeral, artwork, title and artist, metadata as plain text, one action. Hover raises to `surface-hover` with a 3px `accent` bar. The whole row opens the album modal; the Get control is a separate button with its own focus stop.

**Acquisition status row.** Artwork, title, artist and quality profile on the left; state glyph and label, a `transform`-scaled progress bar and the actions on the right. Status vocabulary is the server's.

**Navigation.** Rail items use `text-muted`; the active item uses `surface-raised`, `aria-current="page"` and an `accent` indicator that slides with `translateY`. The rail count for active downloads is a numeral, not a pill.

**Modal.** `dialog` semantics with a focus trap and Escape to close. `surface-raised` panel with a 6px radius over a solid `ink` scrim at 80%, no blur. It fades in with a short upward move, which reduced motion turns off.

**Motion.** The `--dur-fast`, `--dur`, `--dur-slow` and `--ease-out` tokens cover hover, menus, the indicator and the modal. Two loops are literal values kept from the Phase 7 motion pass: the Get arc (1.15s, linear) and the skeleton opacity pulse (1.4s). Under `prefers-reduced-motion: reduce` each animation resolves to its end state.

**Icons.** Lucide line icons from `static/icons.svg`, 20px, 1.75 stroke, `currentColor`. Each icon has a visible label or an `aria-label`.

## Do's and Don'ts

- **Do** use `accent` only for do-this and selected states, focus rings and the active rail item.
- **Do** pair every state colour with a glyph and a text label.
- **Do** use `text-subtle` or brighter for any functional text.
- **Do** keep the Get control's state machine and server confirmation rule exactly as they are.
- **Do** rank numerals only where the API returns a real order, and name the sort basis.
- **Don't** use the display face in controls, labels or data.
- **Don't** add gradients, glass, glow, emoji or decorative icons. (Known exception: a diagonal stripe on two placeholder artwork surfaces is still in the built CSS; it is recorded in `docs/DESIGN_SYSTEM.md` section 16 and is not a pattern to copy.)
- **Don't** add a third-party font, icon, image or script request. Platform logos in the album modal are a known exception (`docs/UI_BACKLOG_EXECUTION.md` section 24.5).
- **Don't** add a new shadow, radius or font size outside the tokens without recording it in `docs/DESIGN_SYSTEM.md`.
