# Design system — "Chart Rundown"

Status: **proposed; AGENTS.md points here (PR #349); decisions D1–D6 recorded in section 15 (Phase 0)** · Last updated: 2026-10-18 · Mode: Operate

This is the target design system for the Librarian redesign. It supersedes the visual-identity section of `docs/FRONTEND_DESIGN_GUIDE.md` once approved (see `docs/REDESIGN_ROADMAP.md`, Phase 0). Nothing here is implemented yet; the shipped tokens in `static/app.css` remain authoritative until Phase 1 lands. Impeccable's `DESIGN.md` is generated from the *built* system at the end of Phase 1 and again at the end of the redesign, not before.

Product truth lives in `PRODUCT.md`. Direction contract lives in `.impeccable/surfaces/app-templates-index-html.md`.

## 1. Decisions this system records

| Question | Owner decision (2026-10-18) |
|---|---|
| Visual world | **Chart Rundown**: a weekly music-press chart page, for the owner's own collection |
| Player bar in references | **Visual language only.** No playback UI; nothing in this system requires a new endpoint |
| Primary user | Single owner, self-hosted, desktop-first |
| Brand color / type | **Open.** Yellow/red and Barlow Condensed / IBM Plex are starting points, now replaced where noted below |
| Layout traits from references | **Icon + label sidebar: adopted.** Hero banner, right rail, soft rounded cards: **not selected** |

## 2. Thesis

An ordered, scannable rundown. The signature is the **rank numeral column**: large condensed numerals lead list rows, with artwork thumbnail, album and artist, quiet metadata and one action. It refuses the universal four-column card grid and the carousel-of-covers pattern all four references share.

The world supplies four things only: type, palette, density, one signature move. It never supplies navigation or controls, which stay standard web components.

## 3. What is kept, replaced, and rejected

| Area | Today | Target | Why |
|---|---|---|---|
| Ground | Neutral grey `#191a1a` | Warm ink `#141211`, darker rail `#0f0e0d` | Warm ink gives artwork more pop and separates the rail without a border |
| Primary accent | Yellow `#e9c64a` | Highlighter yellow `#f5d33f` | Slightly more saturated; 12.7:1 on ground. Keeps the product's recognisable accent |
| Shell/signature accent | Red used only for h2 rule and errors | Chart red `#ff5a3c` for numerals, rail marker, heading rule | Red becomes a brand mark; see the red rule in section 4.3 |
| Display type | Barlow Condensed | **Big Shoulders Display** | Taller, more signage-like; numerals read as chart ranks |
| UI type | IBM Plex Sans | **Schibsted Grotesk** | Humanist news grotesque with tabular figures; IBM Plex is on Impeccable's reflex list |
| Metadata type | IBM Plex Mono | **JetBrains Mono**, technical data only | Mono is reserved for bitrate, format, paths, IDs; dates and counts use tabular figures in the UI face |
| Icons | Almost none; text labels | **Lucide** line icons via inline SVG sprite | Rail and top bar need icons; ISC licensed |
| Radius | 4–6px | 2px artwork/chips, 4px controls, 6px panels/modal | Soft rounded cards were not selected |
| Dashboard ring | 3D coverflow | Proposed retire (decision D1) | Hides titles on rear cards, costs layout complexity, conflicts with a ranked world |
| Nav indicator | Spring blob with goo SVG filter | Plain `translateY` bar, no filter, no overshoot | Same cue, fewer failure modes (see `UI_BACKLOG_EXECUTION.md` 5b) |
| Reference features rejected | | Hero banner, right rail, neon green accent, player bar, soft cards, glass/gradient panels | Not selected by owner, or conflict with the anti-patterns in section 11 |

## 4. Color

Strategy: **Restrained shell with committed numerals.** A tinted ground, one working accent (yellow), one signature accent (red), semantic states. Not a grey screen with one accent.

### 4.1 Tokens

All values are proposals. Contrast was computed with WCAG 2.1 relative luminance on 2026-10-18.

| Token | Value | Role |
|---|---|---|
| `--ink-rail` | `#0f0e0d` | Sidebar and top bar ground |
| `--ink` | `#141211` | Page ground |
| `--surface` | `#1c1a18` | Panels, inputs |
| `--surface-raised` | `#252220` | Menus, modal, selected row |
| `--surface-hover` | `#2d2926` | Row and control hover |
| `--edge` | `#34302c` | Dividers, decorative only (1.4:1) |
| `--edge-strong` | `#787168` | Input and control boundaries (3.28:1 on raised, 3.60:1 on surface) |
| `--text` | `#f4efe6` | Primary text |
| `--text-muted` | `#b4ac9f` | Secondary text |
| `--text-subtle` | `#9c958a` | Metadata (4.86:1 on hover, 6.30:1 on ground) |
| `--accent` | `#f5d33f` | Primary action, selection, focus ring |
| `--on-accent` | `#141211` | Text on accent fill (12.7:1) |
| `--chart-red` | `#ff5a3c` | Rank numerals, rail marker, heading rule, error glyph |
| `--chart-red-text` | `#ff7b62` | Red used as text (6.2:1 on raised) |
| `--ok` | `#86d39b` | Confirmed/success |
| `--caution` | `#f0a640` | Stalled or needs attention |

Measured text contrast (foreground on ground / surface / raised / hover):

| Token | `--ink` | `--surface` | `--surface-raised` | `--surface-hover` |
|---|---|---|---|---|
| `--text` | 16.31 | 15.15 | 13.80 | 12.59 |
| `--text-muted` | 8.31 | 7.72 | 7.03 | 6.41 |
| `--text-subtle` | 6.30 | ≥5.4 | 5.33 | 4.86 |
| `--accent` | 12.69 | 11.79 | 10.74 | 9.80 |
| `--chart-red` | 6.03 | 5.60 | 5.10 | 4.65 |
| `--ok` | 10.50 | 9.75 | 8.89 | 8.10 |
| `--caution` | 9.10 | 8.46 | 7.70 | 7.02 |

Every text token clears 4.5:1 on every surface it is allowed on. These are computed values; they are re-measured on the rendered build in Phase 1.

### 4.2 Usage rules

- Yellow means *do this* or *this is selected*: Get, Save, active rail item, focus ring, selected tab. Never decoration.
- State colors never carry meaning alone. Every state has a glyph and a text label (the existing `.status-line` glyph vocabulary is kept and re-skinned).
- Artwork is the only place saturated imagery appears. Chrome stays tinted-neutral.
- No gradients, glows, glass, or translucent panels. One shadow exists: the floating menu.

### 4.3 The red rule (open risk)

Chart red serves two jobs: brand mark (numerals, rail marker, heading rule) and error glyph. They share a hue family, as today. Mitigation: red is **never the sole carrier of an error** (glyph "!" plus message plus `role`), and error surfaces never use the large numeral treatment. Phase 1 validates this with a color-vision-deficiency simulation; if red-as-brand and red-as-error read as confusable, the brand mark moves to the yellow family and red returns to errors only (decision D2).

## 5. Typography

| Role | Family | Weight | Notes |
|---|---|---|---|
| Page head, rank numerals | Big Shoulders Display | 700–800 | Uppercase for heads, tracking +0.02em |
| UI text, labels, buttons, body | Schibsted Grotesk | 400 / 500 / 600 | `font-variant-numeric: tabular-nums` on every number |
| Technical metadata | JetBrains Mono | 400 / 500 | Bitrate, format, file path, IDs only |

Fixed rem scale, ratio ≈1.2 (Operate mode: no fluid type):

| Step | Size | Use |
|---|---|---|
| `--text-xs` | 0.75rem (12px) | Floor; mono metadata only |
| `--text-sm` | 0.8125rem (13px) | Secondary metadata, status lines |
| `--text-base` | 0.9375rem (15px) | Body, rows, controls |
| `--text-md` | 1.0625rem (17px) | Row titles |
| `--text-lg` | 1.25rem (20px) | Section heads |
| `--text-xl` | 1.5rem (24px) | Modal title |
| `--text-2xl` | 1.875rem (30px) | Page head (display face, uppercase) |
| `--num-row` | 3.5rem (56px) | Rank numeral in a row (display face) |
| `--num-lead` | 5rem (80px) | Rank 1 only on wide screens |

Rules:
- Display face never appears in buttons, inputs, labels, or data cells.
- Line length for prose is 65–75ch; lists and tables run denser.
- No text below 12px; no all-caps UI face labels (caps are reserved for the display face).
- **Self-hosting required.** The current Google Fonts `@import` is replaced by vendored WOFF2 under `static/fonts/` (subset Latin, `font-display: swap`, preloaded display face). All three families are SIL OFL 1.1 (verified on npm: `@fontsource/big-shoulders-display`, `@fontsource/schibsted-grotesk`, `@fontsource/jetbrains-mono`, all 5.3.0). This removes a third-party request and a layout-shift source; it requires an approved scope change (Phase 0).

## 6. Layout and density

- Base unit 4px. Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64 (`--space-1`…`--space-8`).
- Shell: left rail 232px (icon + label, three groups), top bar 56px (breadcrumb, page-scoped search, user/settings), content max width 1280px, 32px gutters (16px under 620px).
- Rail groups: **Discover** (Dashboard, Discover music, New releases, Personal Discoveries), **Collection** (Add to your collection, Artist Deep Dives, Acquisitions), **System** (Settings, Log out). Group labels fix the existing "YOUR COLLECTION over Recommendations" copy error recorded in `UI_BACKLOG_EXECUTION.md` 4a.
- Under 900px the rail collapses to a 64px icon rail; under 620px it becomes a bottom tab bar of the five most used destinations with the rest in a sheet. Touch targets stay ≥44×44.
- Page anatomy: head (display face, 3px red rule), toolbar, content. No hero banner. Each page has its own composition (section 8).
- Row height 64px (compact 48px for Settings and tracklists). Artwork thumb 48–64px square, never cropped to circles, aspect preserved.

## 7. Elevation, borders, shape

- Depth comes from the ground/surface/raised ladder, not shadows or borders. Dividers are 1px `--edge`.
- Controls use `--edge-strong` so boundaries meet 3:1.
- Single shadow `--shadow-menu: 0 8px 24px rgb(0 0 0 / .45)` on floating menus only.
- Radii: 2px artwork and chips, 4px controls, 6px panels and modal. No nested cards; a panel never sits inside a panel.

## 8. Signature and compositions

**Rank numeral column.** Position in the order the user is *currently viewing*, set in the display face, red, tabular. Truthfulness rules:
1. A numeral appears only when the list has a meaningful order, and the sort basis is named in the toolbar ("Ranked by discovery score").
2. Sorted by name or artist, numerals show the row index in a muted tone, or are hidden. They never imply ranking that is not there.
3. Random or unordered sets (Dashboard "Ten from the collection") use artwork tiles with no numerals.
4. No numeral is ever derived from data the API does not return. `discovery_score` is returned today and drives the Discover sort.

| Page | Composition |
|---|---|
| Dashboard | Artwork tile strip (static, no ring if D1 approved), unranked |
| Discover music | Ranked rows, toolbar with request group then refine group (existing hierarchy kept) |
| New releases | Rows ordered by release date; date column in place of numerals |
| Personal Discoveries | Ranked rows when score order is returned, otherwise indexed |
| Add to your collection | Rows with acquisition focus, Get prominent |
| Artist Deep Dives | Genre sections, one row per artist (artist leads, as today), horizontal tile strip per genre with arrows only when it overflows |
| Acquisitions | Status rows, not cards: quality profile, progress bar, state glyph + label, actions (section 9.5) |
| Settings | Two-column form with tab list; no artwork |
| Album modal | Artwork left, tracklist right, platform links beneath artwork |

## 9. Components

Every interactive component defines default, hover, focus-visible, active, disabled, loading, error. Same vocabulary on every page.

### 9.1 Buttons
- **Primary:** yellow fill, `--on-accent` text, 4px radius, 40px tall (44px touch). One per view region.
- **Secondary:** transparent, `--edge-strong` border, `--text`.
- **Destructive:** secondary shape with red text and a trash icon; confirm step before any Dismiss.
- **Icon button:** 44×44 hit area, 20px icon, `aria-label` required.
- Focus ring: 2px `--accent`, 2px offset, on every focusable element; offset negative inside clipped containers.

### 9.2 Get / request control (kept behavior)
The consolidated `.get-album` state machine is preserved exactly: idle → pending (arc, `aria-busy`, disabled) → requested (only after the server confirms; tick draws) or failed (retry). Restyled to the new tokens, shape stays circular in artwork overlays and becomes a pill with label in rows. The server-confirmation rule and the `ok:false` handling are non-negotiable.

### 9.3 Rail and top bar
- Rail item: 20px icon, label, 44px tall; active = yellow bar (3px, `transform`) plus `--surface-raised` fill and `aria-current="page"`.
- Acquisitions item carries the active-download count as a numeral, not a pill.
- Top bar: breadcrumb (page group › page), page-scoped search that filters the loaded list client-side (no new endpoint), settings and user menu.
- Skip link, `aria-label="Main"` and named regions from earlier accessibility PRs are preserved.

### 9.4 Ranked row
Grid: numeral 72px · artwork 64px · title/artist (flex) · metadata (year, genre as plain text, not pills) · action. Hover raises to `--surface-hover` with a 3px yellow left bar; focus ring on the row link. Whole row opens the album modal (existing behavior); the Get control is a separate button with its own focus stop. Long names truncate to two lines with the full name in `title` and the modal.

### 9.5 Acquisition status row
Left: artwork thumb. Middle: title, artist, quality profile (mono), transport line. Right: state glyph + label, then a linear progress bar (`transform: scaleX`, not width) with a numeric percent, then actions. The server's job statuses are the vocabulary and are not renamed: `searching`, `requested`, `queued`, `downloading`, `download_complete_waiting_for_folder`, `importing`, `queue_uncertain`, `recovery_started`, `monitoring`, `imported`, `dismissed`, plus the retryable failure statuses already handled in `static/app.js`. One client-side table maps each to a glyph and a human label (the raw `replaceAll('_', ' ')` labels shown today are replaced); color is secondary. Live updates keep using the existing `/api/acquisitions/stream` source. The 72px conic progress ring is retired in favor of the bar.

### 9.6 Status line, toast, empty and loading states
- `.status-line` and its five glyph states are kept, re-skinned.
- Loading uses skeleton rows with the same grid as ranked rows (opacity pulse only), not centered spinners.
- Empty states keep the per-section copy from PR #186 and add one next action.
- Toasts (vendored Notyf) are restyled only; announcement behavior is untouched.

### 9.7 Forms and tabs
Inputs 40px tall, `--surface` fill, `--edge-strong` border, labels above in `--text-muted`. Tabs follow the existing ARIA pattern (roving tabindex, arrow keys). Secret fields keep preserve-on-blank behavior.

### 9.8 Modal
`dialog` semantics, focus trap, Escape closes, focus returns to the opener. 6px radius, `--surface-raised`, no blur or glass backdrop (solid scrim at 80%).

## 10. Icons

Lucide, inline SVG sprite at `static/icons.svg`, `<svg class="icon" aria-hidden="true"><use href="/static/icons.svg#name"></use></svg>`, 20px, stroke 1.75, `currentColor`. A label or `aria-label` always accompanies an icon. Initial set (≈14): `layout-dashboard`, `compass`, `calendar-plus`, `user-round`, `library`, `mic-vocal`, `download`, `settings`, `log-out`, `search`, `chevron-left`, `chevron-right`, `x`, `trash-2`. All 14 names were checked against the shipped `lucide-static` 1.59.0 package (ISC) on 2026-10-18; the set may still change in Phase 1. No emojis. No icon above a heading as decoration.

## 11. Motion

| Token | Value | Use |
|---|---|---|
| `--dur-fast` | 120ms | Hover, press |
| `--dur` | 180ms | Menus, row states, indicator slide |
| `--dur-slow` | 260ms | Modal, list reorder |
| `--ease-out` | `cubic-bezier(.2,.8,.2,1)` | Everything; no overshoot or bounce |

Allowed motion (state only): rail indicator `translateY`; row hover bar; Get arc and tick; progress `scaleX`; skeleton opacity pulse; modal opacity plus 8px translate; list reorder (FLIP) when the sort changes; menu fade. Animate only `transform` and `opacity`.

Not allowed: page-load choreography, parallax, bounce or spring easing, goo/blur filters, 3D scenes, scroll-jacking, looping decoration. `prefers-reduced-motion: reduce` replaces every animation with its end state; the existing safeguards (Notyf animation durations shortened, never removed) are retained.

## 12. Accessibility and performance floor

- WCAG 2.1 AA minimum; 44×44 targets; visible focus on every control; full keyboard operation.
- Status never by color alone; reduced motion honored; landmarks and names preserved.
- Performance budget (measured at Phase 0 baseline, not guessed): no regression in layout shift; fonts preloaded and swapped; total first-load font weight ≤ 150KB; no new JS dependency.
- Verification is on the rendered result at 1440, 1200, 900, 620 and 390px, not by reading CSS.

## 13. Anti-patterns for this world

No hero banner, right rail, neon or green accent, gradients, glass, glow, nested cards, pill per metadata value, decorative icons or emoji, oversized headings (the 30px page head and numerals are the maximum), stagger-in lists, or ranking implied by numerals without a real order behind it.

## 14. Token migration map

| Current token | Target |
|---|---|
| `--bg` `#191a1a` | `--ink` `#141211` |
| `--chrome` `#1d1f1e` | `--ink-rail` `#0f0e0d` |
| `--surface` `#222424` | `--surface` `#1c1a18` |
| `--surface-raised` / `--surface-hover` | same names, new values |
| `--border` / `--edge` / `--edge-strong` | `--edge` (decorative), `--edge-strong` (controls, 3:1) |
| `--text` / `--muted` / `--subtle` | `--text` / `--text-muted` / `--text-subtle` |
| `--yellow`, `--yellow-bright`, `--yellow-dim`, `--on-yellow` | `--accent`, `--accent-hover`, `--accent-dim`, `--on-accent` |
| `--red`, `--red-text`, `--red-deep`, `--red-bright` | `--chart-red`, `--chart-red-text`; deep/bright collapse into state classes |
| `--green` | `--ok` |
| `--display`, `--body`, `--mono` | same names, new families |
| 22 single-purpose tokens added in PR #194 | audited in Phase 1; each is kept, merged or deleted with a reason |

The migration is done as a token remap first (no layout change) and verified with the computed-style comparison method used in PR #194, then followed by component work.

## 15. Decisions

Recorded by the owner on 2026-10-18 during Redesign Phase 0 (PR #352). Evidence is in `docs/UI_BACKLOG_EXECUTION.md` section 9.

| ID | Decision | Outcome |
|---|---|---|
| D1 | Retire the 3D dashboard ring for a static tile strip | **Retire** (Phase 4) |
| D2 | Keep red as both brand mark and error glyph | **Keep, with the red rule.** Added by the colour-vision check: error and caution always carry different glyphs and labels, never colour alone (red and amber converge under deuteranopia, dE 8.1; yellow and amber are marginal even with normal vision, dE 16.4). Simulation by one published model, not a test with people |
| D3 | Approve vendored fonts and icon sprite (new files under `static/`) | **Approve** (unblocks Phase 1) |
| D4 | Right rail for live acquisitions on 1440px and wider | **Not included**; revisit after Phase 5 |
| D5 | Global search scope | **Library-wide.** This replaces the earlier page-scoped default. It needs a backend search endpoint and result schema, so it is a contract proposal under `docs/REDESIGN_ROADMAP.md` section 6; no proposal is written yet and no backend work is authorized. Consequence, not stated by the owner: the Phase 2 top-bar search can only be library-wide once a contract is approved; until then the page-scoped client filter is the only search that needs no backend change |
| D6 | Replace the cassette mark (`assets/cassette.png`) | **Keep until a replacement is supplied** |
