# Brut layouts plan (web and Android)

Last updated: 2026-11-03 (P3 merged; behaviour rule added). Governing decision: D-023 in [DECISIONS.md](DECISIONS.md). Status tracking: the table in section 9 (update it in the PR that completes each phase). GitHub `main` is authoritative.

## 1. What this is

Round 2 of the Neobrut work (round 1 is D-022: nine web themes, 20 app themes, six Brut font pairs). Round 1 only changed tokens and component skins. Round 2 changes **composition**: the same pages and functions, arranged differently, each arrangement in three or fewer palettes.

The owner chose six layouts and the palettes to keep:

| Id | Layout | Platform | Palettes kept |
|---|---|---|---|
| W1 | Tape Deck | Web | Lime (current), Cobalt Reel, Tangerine Reel |
| W3 | Ledger Room | Web | Ink Slate, Plum Archive, Paper Mono |
| W4 | Crate Wall | Web | Kraft (current), Mint Sleeve, Night Press |
| A1 | Cassette Deck | Android | Lime (current), Cobalt Reel, Tangerine Reel |
| A3 | Sheet Stack | Android | Violet-orange (current), Acid Night, Daylight Sheet |
| A4 | Sticker Wall | Android | Peach-teal (current) |

That is 9 web themes and 7 app themes. Rejected and not to be rebuilt: W2 Comic Issue, A2 Comic Burst, Night Reel, Magenta Midnight, Lilac Pop, Lemon Lime, Cherry Cola, Blueprint Stock, and the sage "Ledger Room Current".

Reference mockups (static HTML, open in a browser, animated meters): [`design/brut-layouts/concepts.html`](design/brut-layouts/concepts.html) (all eight original concepts) and [`design/brut-layouts/variants.html`](design/brut-layouts/variants.html) (the six chosen layouts with every palette switchable). They are design references, not shipped code; they use third-party font links that the app itself must not use (fonts and icons are self-hosted).

## 2. Hard constraints (all phases)

- The API is authoritative; no endpoint or field is invented. Domain, discovery, acquisition and import logic stay server-side (D-016: `navidrome_server.py` takes no additions).
- **The web UI has no playback** (PRODUCT.md). Player-style pieces on the web (Tape Deck's "deck", equalizer meters) show **acquisition progress only**. Nothing may imply audio plays in the browser.
- **A layout may change how a screen is operated, not only how it looks (owner rule, 2026-11-03).** Whenever it serves the layout, a theme's composition may rearrange or replace UI behaviour: which controls appear where, how views are switched (a lyrics button in place of a flip card, a queue shown under the player instead of on a card face), whether a mini player or a floating island is used, what a tap opens. Each such change applies to that layout's themes only; every other theme keeps today's behaviour.
- What a layout may not change is the contract underneath: the API and data, the Android player contract (D-018: gapless playback, scrobbling, the equalizer D-020 and crossfade D-021 behave as today), no playback on the web, and the accessibility floor below. A rearranged control still does exactly what the original did.
- Accessibility is a floor: WCAG 2.1 AA text contrast, 44x44 touch targets, visible focus, keyboard-operable, `prefers-reduced-motion` honoured (meters and tilts stop), status never by colour alone.
- Existing themes (Ink, Vinyl, Nocturne, Parchment, Gallery, Sleeve, Cassette, Mint Desk, Night Shift on web; the 20 app themes) stay unchanged and selectable. The default stays Ink.
- Neobrut shadows and outlines remain the opt-in exception to the flat-depth rule (D-022); the new layouts extend that exception and nothing else.
- Fonts stay independent of the theme: the owner's Brut font pairs apply on top of any layout. A layout may suggest a pair but must not force one.
- Settings, login and account screens keep their structure on every layout (they get the layout's tokens and components only).

## 3. Palettes (from the approved mockups)

Mockup token names: `bg` page ground, `sf` surface, `sf2` raised surface, `ink` text and outlines, `mu` muted text, `ac` primary accent, `on` text on the accent. These are **starting values**. Each PR derives the app's real tokens from them and must check contrast (below); any value that fails AA is adjusted and the adjustment is recorded in the PR description. Not yet checked for contrast: Cobalt Reel (white on `#4f7cff`), Paper Mono (white on `#2f5bff`), and any muted text on a coloured ground.

### Tape Deck (web W1 and Android A1; the same three palettes on both platforms)

| Palette | bg | sf | ink | mu | ac | soft | on | extra tones |
|---|---|---|---|---|---|---|---|---|
| Lime (current) | `#f1eee3` | `#fffdf6` | `#111111` | `#5b594f` | `#c6f432` | `#e9f8b4` | `#111111` | pink `#ff5d8f`, blue `#3d7bff`, amber `#ffc93c` |
| Cobalt Reel | `#e6edfb` | `#fbfcff` | `#0e1b3d` | `#4a5a82` | `#4f7cff` | `#d3dfff` | `#ffffff` | coral `#ff6b4a`, yellow `#ffd23f`, navy `#0e1b3d` |
| Tangerine Reel | `#fff0dc` | `#fffaf2` | `#1b120a` | `#6b563f` | `#ff8a1f` | `#ffe0b8` | `#1b120a` | green `#1f8a70`, yellow `#ffd23f` |

### Ledger Room (web W3)

| Palette | bg | sf | ink | mu | ac | on | ok | wait | miss | sidebar text / muted / hover row |
|---|---|---|---|---|---|---|---|---|---|---|
| Ink Slate | `#e4e9f2` | `#fbfcff` | `#14213d` | `#50607f` | `#fca311` | `#000000` | `#7bd88f` | `#ffd166` | `#ff8fa3` | `#e4e9f2` / `#8fa0c4` / `#eef3ff` |
| Plum Archive | `#efe3f0` | `#fffaff` | `#2d1233` | `#6b4a73` | `#ff5ca8` | `#000000` | `#9be3b0` | `#ffd75e` | `#ff9aa8` | `#f0e0f2` / `#b28bb9` / `#f8ecf9` |
| Paper Mono | `#f4f4f0` | `#ffffff` | `#0a0a0a` | `#555555` | `#2f5bff` | `#ffffff` | `#b7f0c0` | `#ffe58a` | `#ffb3a6` | `#f4f4f0` / `#9a9a9a` / `#f0f3ff` |

The sidebar is the ink colour; `ok`, `wait`, `miss` are the Owned, Queued and Missing badge fills (labels stay words, never colour alone).

### Crate Wall (web W4)

| Palette | bg | sf | ink | mu | stamp red | gold (Queued) | on |
|---|---|---|---|---|---|---|---|
| Kraft (current) | `#d9b98a` | `#fff6e2` | `#17110a` | `#5c4630` | `#d7263d` | `#f2c14e` | `#ffffff` |
| Mint Sleeve | `#a9d9b4` | `#f4fff6` | `#0d2a16` | `#3c6a49` | `#ff5a5f` | `#ffd166` | `#0d2a16` |
| Night Press | `#1b1713` | `#2a241d` | `#f5ead8` | `#b8a68c` | `#ff4d4d` | `#ffbf3c` | `#1b1713` |

### Sheet Stack (Android A3)

| Palette | bg | sf | sf2 | ink (also edge) | mu | ac | cy (second tone) | on |
|---|---|---|---|---|---|---|---|---|
| Violet-orange (current) | `#15131f` | `#221f31` | `#2e2a43` | `#f4f1ff` | `#a8a2c4` | `#ff6a3d` | `#35e0d0` | `#15131f` |
| Acid Night | `#0d1210` | `#17201b` | `#22302a` | `#eefaf0` | `#93ad9b` | `#c6f432` | `#ff5dc8` | `#0d1210` |
| Daylight Sheet | `#f4efe6` | `#fffdf7` | `#ece4d4` | `#14121c` | `#6a647a` | `#ff6a3d` | `#2bb3a6` | `#14121c` |

### Sticker Wall (Android A4)

| Palette | bg | sf | ink | mu | primary (teal) | orange | pink | yellow |
|---|---|---|---|---|---|---|---|---|
| Peach-teal (current) | `#ffe8d6` | `#fffaf5` | `#3b1f14` | `#7a4a36` | `#2ec4b6` | `#ff9f68` | `#ff6b8b` | `#ffd23f` |

Dark/light flags for the Day and Night slots: Night Reel was rejected, so the dark themes are Night Press (web), Acid Night and Violet-orange (app); Daylight Sheet is light; every other palette is light.

## 4. Web architecture (shared by W1, W3, W4)

- **A layout is a CSS mode, a palette is a token set.** `static/appearance.js` gains a `layout` field on theme entries (`tape`, `ledger`, `crate`; none for the existing themes) and `apply()` sets `data-layout` on `<html>` next to `data-theme` and `data-brut`. The new themes set `data-brut` too, so they inherit the Neobrut component layer in `static/themes.css`.
- **Selection stays one list.** Settings > Appearance keeps one Theme select (plus Day, Night and Font). The new themes appear as a new optgroup per layout, named `Tape · Lime`, `Tape · Cobalt`, `Tape · Tangerine`, `Ledger · Slate`, `Ledger · Plum`, `Ledger · Mono`, `Crate · Kraft`, `Crate · Mint`, `Crate · Night`. Day and Night slots work unchanged (each theme declares `dark`).
- **Files.** Palettes: new `:root[data-theme="…"]` blocks in `static/themes.css` (token names as in the existing Brut themes: `--ink-rail`, `--ink`, `--surface`, `--surface-raised`, `--surface-hover`, `--edge`, `--text*`, `--accent*`, `--on-accent`, `--focus`, `--bw`, radii, `--brut-*`). Layout rules: a new `static/layouts.css`, every selector scoped `:root[data-layout="tape"]` (and so on), loaded after `themes.css` and registered in the template and in the packaging/static tests. No layout rule may appear outside that scope, so removing a layout is deleting its block.
- **Markup changes are small and shared.** Prefer CSS over new markup. Where a layout needs a hook (an equalizer span in an acquisition row, a column wrapper), add it to `app.js` / `index.html` once, hidden by default and shown only by the layout that wants it, so other themes render exactly as today.
- **Responsive rule.** A layout applies from 900 px up. Below 900 px the existing mobile shell (bottom nav, single column) is kept and receives only the layout's tokens and component skins. This avoids rebuilding the phone UI three times.
- **Persistence and first paint.** `appearance.js` already runs before first paint and stores the choice in `localStorage`; the layout rides on the theme id, so no new key. A saved id that no longer exists falls back to Ink.
- **Tests.** Each layout PR adds a `test_<layout>_layout_ui_contract.py` (pattern of the existing `*_ui_contract` modules): the catalogue entries exist with the right ids, `dark`, `brut` and `layout` fields; every selector in `layouts.css` is scoped; every palette defines the full token set; contrast of text-on-ground, text-on-accent and focus tokens meets AA (computed in the test from the hex values); new markup hooks are hidden without the layout; reduced-motion disables the meters. Agents run only the `*ui_contract*` modules plus the fonts test (never the full suite).
- **Decision record.** D-023 (section 8) is added with this plan. Each layout PR appends a short dated paragraph to D-023, as D-022 did.

## 5. Web layouts

For every layout, "unchanged" means the existing page keeps its content and behaviour and only gets the layout's tokens and component skins.

### W1 Tape Deck (phase P1)

Idea: lists read as a ruled playlist; the top of the window is one ruled tab strip; progress is shown by live meters.
- **Shell:** the left rail becomes a horizontal ruled tab strip under the header (current page filled with the accent); the header holds the wordmark and the search field with a `Ctrl K` hint (the shortcut only if it does not already exist; if it does not, show no hint). `main` loses the rail margin.
- **Dashboard:** the shelves (New releases, Newly added, Recently played, Most played) become ruled rows (number, small cover, title, artist, quality text, Get or state) in a two-column arrangement: lists on the left, a deck column on the right (Acquisitions summary: the active request with cover, title, artist, a 5-bar meter and a seek-style progress bar; below it three counts). The Recommended carousel stays above as a full-width ruled panel. Genres stay tiles in a ruled grid.
- **Recommendations / New releases / Personal Discoveries / Daily picks / Classics / Deep Dives:** the existing ranked rows get the playlist look: ruled dividers, number cell, mono quality and duration-style fields, accent-soft hover; a row whose album is being fetched shows the 3-bar meter in the number cell.
- **Acquisitions page:** each request row shows a meter while active, and the page header is the "deck" (selected request large, others as rows). Failed and queued states keep their words and icons.
- **Album modal:** the track list uses the ruled playlist rows (number, title, mono duration); no play control.
- **Components:** square 2 px outlines, hard 5 px shadow, pill-less rectangles (radius 0 to 2 px), mono numerals. Equalizer meters are decorative (`aria-hidden`), animation off under reduced motion.
- **Palettes:** Lime, Cobalt Reel, Tangerine Reel (section 3).
- **As built in P1 (differs from the text above):** the tab strip is text only (rail icons hidden) and scrolls sideways below about 1,250 px; there is no `Ctrl K` hint (no such shortcut exists); the dashboard has no deck column (it has no acquisition data), so the three-bar meter sits on the Acquisitions page (rows that are downloading, monitoring or importing); search fields are rectangles; ranked rows are 72 px with a one-line bio and a text column that grows, never clips; the shelf covers are 52 px with a corner badge and no placeholder text or hover bio. Cobalt's accent is `#3d68f0` (the mockup's `#4f7cff` failed AA with white text).
- **Acceptance:** the nine existing themes render byte-identical CSS output outside `layouts.css`; Tape pages work at 1280, 1024 and 900 px, fall back correctly at 899 px and 390 px; keyboard order matches reading order after the nav moved; no horizontal overflow; long names truncate; missing artwork shows the existing fallback.

### W3 Ledger Room (phase P2)

Idea: table-first, for scanning many albums at once.
- **Shell:** a dark ink sidebar (counts on Discover, New releases, Requests), breadcrumb line above each page, a command-style search with a `Ctrl K` hint, a stat strip (Owned, Missing, Queued, Imported in 7 days) from data the dashboard already loads.
- **Discovery pages and Library:** a data table: cover and title/artist, year, quality, status badge (Owned, Missing, Queued, with the word), inline Get; a toggle group above (All, Missing, Queued) and pagination below. Sorting uses the sort options the page already has; no new endpoint, and no client-side re-ranking of server results.
- **Artist Deep Dives:** an accordion per genre (the current grouping), one album per artist rows inside.
- **Dashboard:** stat strip, then the Recommended slider and shelves as compact tables.
- **Acquisitions:** table with a progress column.
- **Palettes:** Ink Slate, Plum Archive, Paper Mono. Paper Mono has a white-on-blue accent (check AA); badge fills never carry meaning alone.
- **As built in P2 (differs from the text above):** the layout is CSS plus small hidden-by-default hooks (a breadcrumb, a summary strip, a status cell per ranked row, a filter switch per discovery list, a fold button per Deep Dives genre; all shown only by the layout). The summary strip counts the acquisition list the page already loads (Active, Imported in 7 days, Failed, All records), because the dashboard does not load Owned or Missing library totals. The status cell reads Owned, Missing or Queued as a word and follows the row's Get button. The All/Missing/Queued switch hides rows by that cell and never reorders. **Ctrl+K (Cmd+K on a Mac)** jumps to the header search in the ledger layout only, with a hint in the field (added at the owner's request; no other theme has the shortcut). **Not built:** pagination and sort changes (no new endpoints, no client-side re-ranking), real `th` header cells (rows stay interactive articles), the Library page as a table (it is an artist/album grid with its own sort). The sidebar and the Owned/Queued/Missing fills of the plan's palette table (`ok`, `wait`, `miss`) are not used: status keeps its word and the sidebar tokens are `--ledger-side*`. All three palettes passed AA with the mockup values.
- **Acceptance:** tables become stacked rows below 900 px (the mobile shell), scroll horizontally inside their own container only if they must; header cells are real `th` with `scope`; sort state is announced; the table keeps working with the existing keyboard activation of rows.

### W4 Crate Wall (phase P3)

Idea: artwork leads; the wall is the home.
- **Shell:** a single header band (wordmark, nav as stamped labels), no rail; the current page's label is rotated and filled.
- **Dashboard and discovery pages:** a mosaic wall (5 columns, one 2×2 hero tile per page for the first or featured album); status as rubber-stamp labels on the tile (Owned, Missing, Queued; text, not colour); the name strip along the tile's bottom edge; New releases as a carousel strip with arrow buttons (reuse the existing carousel behaviour).
- **Album detail:** the modal becomes a right-hand drawer (the existing `.album-modal` dialog, restyled and anchored right, same focus trap, Escape and backdrop behaviour); tracklist as dashed-rule rows; Get and Skip at the foot.
- **Hover card** on tiles for hover-capable devices only, showing artist, year and owned count from data already on the card; never the only way to reach information.
- **Palettes:** Kraft, Mint Sleeve, Night Press.
- **As built in P3 (differs from the text above):** the header and a stamped label strip under it read as one band (the nav stays a separate element; labels are bordered mono capitals, the current one tilted -2 degrees and filled with the stamp red; the tilt is static, so reduced motion has nothing to stop). Every ranked list is the wall: 5 columns from 1280 px, 4 from 1060 px, 3 below; there is no 2-column step because the layout stops at 900 px (the phone shell keeps its own grid). The first tile is the 2x2 hero. Status stamps reuse the P2 status cell (Owned, Missing, Queued as words; Queued uses `--crate-gold`). The hover card (hover-capable devices only) shows the row's own metadata lines; the owned count is not on the card, so it is not shown. The dashboard shelves stay horizontal strips of cards with arrows added by a hidden-by-default hook (hidden again while the strip fits). The album dialog is the drawer: Get moves from the cover to a sticky foot (the same element) and **Not for me** (added at the owner's request) runs the originating row's own dismiss control, so it appears only for rows that have one. Kraft's accent text is `#b01c31` (the stamp red failed AA on the raised surface); Mint and Night passed with the plan's values; Night is dark with a gold focus ring and red shadows.
- **Acceptance:** wall reflows 5 → 4 → 3 → 2 columns; the drawer meets the dialog accessibility rules already in the album modal tests; tile order matches the DOM order of the lists it restyles; reduced motion removes the stamp tilt animation.

## 6. Android architecture (shared by A1, A3, A4)

- Themes live in `android/app/src/main/kotlin/app/discair/ui/theme/` (`Palette.kt`, `Appearance.kt`, `Theme.kt`, `BrutalShapes.kt`); components in `ui/common/BrutalComponents.kt`; the Appearance screen in `ui/settings/AppearanceSettings.kt`.
- **A layout is a new field on a theme** (for example `layout: Layout = Layout.Standard | TapeDeck | SheetStack | StickerWall`) provided through the theme's CompositionLocal, plus a palette. Screens read the layout and choose a composition (Home, Now Playing, mini player, nav, Downloads), falling back to today's composition for `Standard`. The 20 existing themes keep `Standard`.
- Reuse the Round 1 `BrutalComponents` wrappers and add the missing pieces there (ruled list row, joined toggle nav, tile with tilt and sticker, pill nav, stacked pill bars); do not fork Material usage at call sites.
- Unit tests in `AppearanceRulesTest` and `PaletteTest` style: theme ids, layout ids, full palette fields, AA contrast of the text pairs, Day/Night slot eligibility; composition choices that are pure functions are unit-tested.
- Verification: `assembleDebug`, lint, R8 release build, the Android unit tests; the owner's phone for look and feel (not claimed otherwise). Build and install commands are in the owner's notes: release-signed APK only.
- Compose limits to design around: no uppercase transform on text (only Bebas Neue reads as capitals); a hard shadow on a dialog or dropdown is drawn inside it.

## 7. Android layouts

### A1 Cassette Deck (phase P4)
Palettes Lime, Cobalt Reel, Tangerine Reel. Home: ruled recently added list, the playing row shows a 3-bar meter, the mini player has a seek strip along its bottom edge. Now Playing: the full player card (cover 68 dp with hard shadow, "Track n of m" mono label, title, 5-bar meter, ruled seek bar, square transport, queue as a playlist under the card). Nav: the existing island becomes a ruled four-cell bar. The meter reflects real playback state (playing, paused, buffering) and stops when paused or under reduced motion.

### A3 Sheet Stack (phase P5)
Palettes Violet-orange (current), Acid Night, Daylight Sheet. Home: a carousel row ("Today") over item rows with status badges for requests (Fetching, Queued, Done, always with words). Nav: a joined four-segment toggle group replaces the island. Now Playing: a bottom sheet with a grab handle, large cover with a vertical volume slider beside it, a joined transport (previous, play, next, queue), a lyrics strip that uses the existing lyrics feature (D-019) and shows "no lyrics" states as today.

### A4 Sticker Wall (phase P6)
Palette Peach-teal only. Home: floating pill nav over a two-column tilted tile wall with sticker badges (New, Missing; text). Now Playing: poster style, large stacked title, the equalizer shown as three stacked pill bars that are the real controls of the existing Equalizer screen (bass, mid, treble summary; tapping opens the Equalizer, no new audio behaviour), a crossfade switch that is the real setting, round transport buttons. Tilts are static (no animation), removed from the accessibility tree and never reduce touch targets below 44 dp.

## 8. Decision D-023 (text for DECISIONS.md)

Recorded in [DECISIONS.md](DECISIONS.md) in the same commit as this plan.

## 9. Phases and status

One PR per phase except P0 and P7 (documents, direct to `main`). Each code PR: branch from current `main`, focused tests only, CI green on the exact final head, owner's manual check on that head, squash merge, then update this table, `PROJECT_STATUS.md` and `PROJECT_LOG.md` in a documentation commit.

| Phase | Scope | Status |
|---|---|---|
| P0 | This plan, D-023, mockups in `docs/design/brut-layouts/` | done 2026-11-03 (documentation, direct to `main`) |
| P1 | Web infrastructure (`data-layout`, `layouts.css`, catalogue fields, test scaffold) and the Tape Deck layout with Lime, Cobalt Reel, Tangerine Reel | **done 2026-11-03**: PR [#701](https://github.com/abucalip/navi-librarian/pull/701), squash `a4961c9`; owner checked it in the browser; not published |
| P2 | Web Ledger Room with Ink Slate, Plum Archive, Paper Mono | **done 2026-11-03**: PR [#702](https://github.com/abucalip/navi-librarian/pull/702), squash `d94667d8fe645197acd9a2cb98e68836306132f3`; owner checked it in the browser; not published |
| P3 | Web Crate Wall with Kraft, Mint Sleeve, Night Press | **done 2026-11-03**: PR [#703](https://github.com/abucalip/navi-librarian/pull/703), squash `c6dbc43bd113bd3033ad430e787d3c1da05377ce`; owner checked it in the browser; not published |
| P4 | Android layout plumbing and Cassette Deck with Lime, Cobalt Reel, Tangerine Reel | not started |
| P5 | Android Sheet Stack with Violet-orange, Acid Night, Daylight Sheet | not started |
| P6 | Android Sticker Wall with Peach-teal | not started |
| P7 | Closeout: documents, a published release when the owner authorises it | not started |

**Starting a later phase in a new session:** read `handoff.md`, `ACTIVE_WORK.md`, this plan and the previous phase's PR; reuse the infrastructure P1 (web) or P4 (Android) left; start from the layout's section above, build the three palettes from section 3, and follow `LOCAL_UI_TESTING.md` for the web check. Do not widen the scope (no new pages, endpoints or playback on the web).

## 10. Risks and open points

- **Lessons from P1 for P2 and P3:** a fixed-height text column clips late-loading bios (let rows grow); a placeholder mark (`NL / 01`) is drawn inside any small cover (hide it, as `.ranked-row` and `.acq-row` do); the last item of a group must drop its right rule or the group divider doubles; a hidden `.page` uses `display: none !important`, so a layout may set `display` on `#dashboard` safely; the focused test pattern is `tests/test_tape_layout_ui_contract.py`; to check a layout without a login, render `app/templates/index.html` with sample rows in headless Chrome.

- `app.css` is long and cascade-heavy (1,267 lines plus `themes.css`). Layout rules therefore live in their own file with a scoped prefix and are verified at the listed widths; do not edit `app.css` selectors to make a layout work unless the change is behaviour-neutral for every other theme and tested.
- stream/ui's colour tokens and comic helpers were never read from source (the doc pages do not show them); the mockups use approximated values. If the owner wants exact matches, they must supply the component source.
- The contrast of the Cobalt Reel and Paper Mono accents and of muted text on coloured grounds is unchecked; a failure changes the palette value, not the layout.
- Layout changes to the Android Home and Now Playing screens carry real regression risk for playback UI (seek, queue, lyrics, equalizer and crossfade entry points). Each Android PR keeps `Standard` as the default and unit-tests the layout selection logic.
- Phone-width web layouts are deliberately not redesigned in this plan (section 4). If the owner wants them, that is a new decision.
