# Design system — "Chart Rundown"

Status: **proposed; AGENTS.md points here (PR #349); decisions D1–D6 recorded in section 15 (Phase 0); tokens, fonts and icon sprite implemented in Phase 1 (`ui/phase-1-foundations`, see `docs/UI_BACKLOG_EXECUTION.md` section 10)** · Last updated: 2026-10-18 · Mode: Operate

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
| `--edge` | `#34302c` | Dividers, decorative only (1.33:1 on `--surface`; corrected from 1.4 by the Phase 0 token check, not yet re-measured on the rendered build) |
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

## 16. Drift record at the end of Phase 7 (2026-10-19)

Recorded by Redesign Phase 7 item 3 (`ui/phase-7-document-ryetdc`) after the Phase 7 audit (PR #394, merge `7b26d10`). Method: read the built `static/app.css`, `app/templates/index.html` and `static/icons.svg` against sections 4 to 12; ran the Impeccable detector once on `static/app.css`; measured transfer and layout shift in Chromium. The code was not changed. Each row gets one status: **match** (built as specified), **accepted** (built differs and the difference is kept, with the reason), **open** (needs a code or doc change in a later PR, or an owner decision).

### 16.1 What matches

- Every token value in section 4.1 matches `:root` in `static/app.css` (all 18 colour tokens, the shadow, space, radius, motion and type-scale tokens).
- Google Fonts is removed. The three families are self-hosted under `static/fonts/` with OFL licence files and `font-display: swap`. No request left the origin during the dashboard or Discover loads (section 16.4).
- The icon sprite holds the 14 names in section 10 (`layout-dashboard`, `compass`, `calendar-plus`, `user-round`, `library`, `mic-vocal`, `download`, `settings`, `log-out`, `search`, `chevron-left`, `chevron-right`, `x`, `trash-2`).
- Focus rings are 2px `accent` at 2px offset on buttons, inputs, selects and rail items (section 9.1).
- Reduced motion ends the modal, header menu, Get arc and tick, skeletons and indicator at their end state (section 11). The Notyf toast animation is shortened, not removed, as section 11 allows.

### 16.2 Drift and decisions

| # | Area | Section says | Built | Status | Next step |
|---|---|---|---|---|---|
| 1 | Icon rail width, 621–900px | 64px (section 6) | 72px (`--rail-w` in the 621–900px media query) | **open**, owner decision | 72px fits a 44px target with padding; recommend updating section 6 to 72px. Code unchanged. |
| 2 | Bottom tab bar under 620px | Five most used destinations, the rest in a sheet (section 6) | Seven destinations in a horizontal scroll; four visible at 390px (PR #394, section 24.5) | **open**, Hamdi's call | A "More" sheet or shorter labels would change the shell. Not redesigned in Phase 7. |
| 3 | Rail label for the Discover page | "Discover music" (sections 6 and 8) | "Recommendations" in the rail; the page heading is "Discover music" | **open**, terminology | AGENTS.md says keep terms users rely on. Recommend keeping "Recommendations" and changing section 6 and 8. |
| 4 | Type ramp | Ramp steps 12px to 30px; no text below 12px; display 30px as the maximum page head (sections 5 and 13) | About 24 literal sizes off the ramp (9px to 16px). The header title is 29px; the desktop `.panel h2` is 34px (30px under 620px). Two labels at 9px and 11px sit below the floor: the category label on cards and the 11px Get labels and rail counts | **fixed** (Phase 7 item 4, `ui/phase-7-typography-zfk4p0`, this PR; `docs/UI_BACKLOG_EXECUTION.md` section 26) | Every font size in `static/app.css` is now a ramp token. The 25 off-ramp declarations map to 12, 15, 17, 24 or 30px, and no text is below 12px. The rank numeral is 30px (text ramp), not the 56px `--num-row` token of section 5; that is a separate decision, not made here. |
| 5 | Gradients | No gradients (sections 4.2 and 13) | Two `linear-gradient(135deg …)` diagonal stripes on the placeholder artwork surfaces (`.card-art` and the ranked-row artwork) | **open** | Replace with a flat `surface-raised` fill in a follow-up PR. |
| 6 | Shadows | One shadow, `--shadow-menu` (sections 4.2 and 7) | Also a Get control shadow over artwork (`0 3px 12px rgba(0,0,0,.55)`) and the Notyf toast (`0 10px 30px rgba(0,0,0,.5)`). The inset bars on active navigation items are indicators, not shadows | **accepted** for the toast (vendored component); **open** for the Get shadow | Remove the Get shadow, or record it as an overlay rule, in a follow-up. |
| 7 | One-off colours | Add no value that is not a token (AGENTS.md design rules) | `#353124` (category label fill), `#2a2c29` (card action button fill), `rgba(233,198,74,.12)` (stripe in row 5), `rgba(0,0,0,.5)` and `rgba(0,0,0,.55)` (shadows in row 6). The modal scrim `rgb(20 18 17 / .8)` is `ink` at 80%, as specified | **open** | Map to `surface-raised`, `surface-hover` and `accent-dim` in the typography and gradient PRs. |
| 8 | Radii | 2px, 4px, 6px scale; pill and circle for Get (sections 7 and 9.2) | A 3px literal on rail items and two labels (off-scale). The 999px pill on ranked-row Get and the 50% circles on artwork Get match section 9.2 | 999px and 50%: **match**. 3px: **open** | Move the 3px literals to `--radius-chip` (2px). |
| 9 | Side stripes | 3px yellow left bar on ranked rows, hover only (section 9.4) | Matches on ranked rows. A 3px bottom stripe on artwork hover (`.card-art::after`) is not in section 9 | Ranked-row bar: **match**. Artwork hover stripe: **accepted** as a hover cue, reviewed at the owner's pass. | Review with the owner. |
| 10 | Primary button | Yellow fill, `on-accent` text, 40px (section 9.1) | No primary class. The base button is a `surface` control with an `edge-strong` border. The accent fill appears only on the Get requested state and on selection | **open**, decision | Either add a primary variant for one action per region, or record that the system has no primary button. |
| 11 | Motion literals | Motion tokens for all durations (section 11) | Get arc 1.15s and skeleton pulse 1.4s are literal (decided in PR #392; section 23.5) | **accepted** | Add two tokens in a later pass if the owner wants them named. |
| 12 | Modal | `dialog`, focus trap, Escape, focus return, 6px radius, 80% solid scrim (section 9.8) | Matches on the reconstructed pages (section 22 and 24). Platform logos load from third-party hosts (section 24.5, B2) | Structure and scrim: **match**. Logos: **open** (third-party runtime requests). | Vendor the logos or replace them with text labels; a brand and licence decision. |
| 13 | Contrast on the rendered build | Measured on the rendered build (section 4.1, roadmap section 7) | Re-measured on Phase 1 empty states only. Red text, caution and acquisition states not re-measured | **open** | Re-measure the status pairs with the next visual PR. |
| 14 | Content gutters | 32px gutters, 16px under 620px (section 6) | 34px sides above 620px (`main` margin); 14px under 620px | **open** | Set section 6 to the built values or move the CSS to 32px; the value is small, so the doc change is the cheaper fix. |

### 16.3 Detector result (advisory)

`impeccable detect --json static/app.css` returned 34 findings: 24 `design-system-font-size`, 4 `design-system-radius`, 4 `design-system-color` and 2 `side-tab`. The two `side-tab` findings are the stripes in rows 9 and 5 above. The detector output is advisory, as the Impeccable direction says; each item is classed in table 16.2 and the remaining findings are the font sizes in row 4.

### 16.4 Performance against the Phase 0 baseline

Same method as `docs/UI_BACKLOG_EXECUTION.md` section 9.5 (Chromium through Playwright, a new context per run, cache disabled, 150 ms latency, 1.6 Mbit/s down, 750 Kbit/s up, 4x CPU, 1440x900, three runs). Built at `origin/main` `8849e7e`, live empty sandbox with no reconstructed data. Figures are byte totals from the network log with the cassette counted once.

| Metric | Phase 0 dashboard | Phase 7 dashboard | Phase 0 Discover | Phase 7 Discover |
|---|---|---|---|---|
| Transfer, same origin (bytes) | 206,610 | 339,582 | 206,845 | 365,229 |
| Requests to same origin | 8 | 16 | 9 | 18 |
| Requests to third-party hosts | 1 (Google Fonts, blocked) | 0 | 1 (blocked) | 0 |
| Font bytes | not loaded (blocked) | 108,148 (5 WOFF2) | not loaded | 133,560 (6 WOFF2) |
| Stylesheet bytes | 46,103 | 57,534 (app.css 50,390 and fonts.css 1,741) | | |
| Script bytes | 110,661 | 118,004 (app.js 110,107) | | |
| First contentful paint (ms, run 1 / 2 / 3) | 1108 / 1172 / 1160 | 1352 / 1056 / 1060 | 1192 / 1204 / 1160 | 1044 / 1080 / 1060 |
| Cumulative layout shift | 0 / 0 / 0 | 0.000086 in all runs | 0 / 0 / 0 | 0.000086 in all runs |
| Load event end (ms, run 1 / 2 / 3) | 1344 / 1417 / 1393 | 2219 / 1957 / 1959 | 1417 / 1425 / 1401 | 1939 / 1998 / 1952 |

Reading the table:
- **Transfer went up by about 133 KB on the dashboard and about 158 KB on Discover.** Nearly all of it is the self-hosted font files (108 to 134 KB), which the Phase 0 baseline could not include: its Google Fonts request was blocked, so no font file was ever downloaded. The section 5 budget is 150 KB of first-load font weight. Discover's 133,560 bytes are under it.
- The icon sprite adds 4,611 bytes, and `fonts.css` adds 1,741.
- **Layout shift is unchanged in effect.** CLS is about 0.00009, down from zero, which is below any perceptible threshold. The shift is measured with fallback-to-web-font swap in place.
- **FCP and load time are not regressed in this run, but this does not show the real-network cost.** The fonts come from the same local server and the throttle applies only to that link, so the font bytes are slower on a real network than they look here. Phase 0 notes that the blocked Google request made its own timings optimistic, so the two sets of numbers are not like for like.
- The Phase 7 run shows one `/assets/cassette.png` network entry as an image and a second as an "Other" entry. The duplicate was not investigated; the totals here count it once.
- Not measured: the LCP element (Phase 0 recorded `#dashboardHeading`; the observer here did not record the element), and the populated states (artwork weight).

### 16.5 Open decisions from this record

Owner decisions needed, in the order they block later work: rows 1, 3 and 14 (small value changes to section 6, and the rail name), row 2 (the bottom bar on phones), and row 10 (whether the system has a primary button). All other open rows are code or typography work for a follow-up PR, not new decisions.
