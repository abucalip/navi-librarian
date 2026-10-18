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

## Overview

**Creative North Star: "The Chart Rundown"**

The interface reads like a weekly music-press chart for the owner's own collection. It is ordered and scannable: artwork and titles lead, metadata stays quiet, and one action closes each row. Depth comes from a ground ladder (ink, surface, raised), not from shadows or borders. Chart red is the signature mark; yellow means "do this" or "selected".

This system was chosen in `docs/DESIGN_SYSTEM.md` (owner decisions D1–D6). It is a Phase 1 foundation: the tokens below are what the shipped CSS renders. Component rules in later phases will extend it.

**Key Characteristics:**
- Warm ink ground with a darker rail; no gradients, glass or glow.
- One working accent (yellow) and one signature accent (chart red) that is never the sole carrier of an error.
- Condensed display numerals and headings; grotesque UI text; mono for technical metadata only.
- Self-hosted fonts and icons; no third-party runtime requests.

## Colors

Warm neutrals with two accents. Yellow is the working accent; chart red is the signature and the error hue.

- **Ground ladder:** `ink-rail` (sidebar, header), `ink` (page), `surface` (panels, inputs), `surface-raised` (menus, selected rows), `surface-hover`.
- **Edges:** `edge` is decorative (dividers, card edges, 1.33:1 on surface). `edge-strong` is the boundary of any control and meets 3:1 on its surface.
- **Text:** `text` (primary), `text-muted` (secondary), `text-subtle` (metadata; the floor for functional labels).
- **Accent:** `accent` fills primary actions and marks selection and focus; `on-accent` is the text on it. `accent-hover` and `accent-dim` are its hover and pending states.
- **States:** `ok` and `caution` exist as tokens. Every state also carries a glyph and a text label; colour is never the only signal.

Measured on the rendered build (Phase 1, empty states at 1440px): 19 text pairs on login, dashboard and Settings, lowest 6.30:1, all passing AA. Red text, caution, and acquisition states were not rendered in that run.

## Typography

- **Display** (Big Shoulders Display 700, preloaded): page heads and rank numerals only. Never in buttons, inputs, labels or data cells.
- **Body** (Schibsted Grotesk 400/500/600): all UI text. Use tabular figures for numbers.
- **Mono** (JetBrains Mono 400/500): technical metadata only (bitrate, format, paths, IDs).

Shipped weights are 700 and 800 for display, 400, 500 and 600 for body, 400 and 500 for mono. Requests for other weights resolve to the nearest shipped face.

Type scale tokens (`--text-xs` 12px to `--text-2xl` 30px) are defined; most components still use literal sizes until their phase.

## Layout

Single column content inside a fixed header and a left rail. The rail carries the navigation; the header carries the page identity and tools. Spacing follows the 4px base in the spacing tokens. The layout has no hero banner and no right rail.

Responsive behaviour is verified at 1440, 1200, 900, 620 and 390px. No horizontal overflow at any of them on the Phase 1 pages.

## Elevation & Depth

Flat by default. Depth comes from the ground ladder. The only shadow is `--shadow-menu` (`0 8px 24px rgba(0,0,0,.45)`) on the floating header menu.

## Shapes

- `radius-chip` 2px: artwork, chips.
- `radius-control` 4px: buttons, inputs.
- `radius-panel` 6px: panels, menus, modal.

No nested cards. Dividers are 1px `edge`.

## Components

- **Buttons:** `surface` fill with `edge-strong` border and `text` label. Hover uses `surface-hover` with an accent border. Disabled dims to 55% opacity.
- **Get / request:** the existing state machine (idle, pending, requested, failed). Requested is an `accent` fill with `on-accent` text and a drawn tick; the server confirmation rule is unchanged.
- **Focus:** 2px `accent` outline, 2px offset, on every focusable element.
- **Navigation:** rail items in `text-muted`; the active item is marked by `aria-current` and the accent treatment.
- **Header menu:** `surface-raised` panel with `edge-strong` border and `--shadow-menu`.

## Do's and Don'ts

- Do use `accent` only for do-this and selected states.
- Do pair every state colour with a glyph and a label.
- Do use `text-subtle` or brighter for any functional text.
- Don't use the display face in controls or data.
- Don't add gradients, glass, glow, emoji or decorative icons.
- Don't add a third-party font, icon or script request.
- Don't rank rows with numerals unless the API returns a real order.
