# Brut round 3 plan (web and Android)

Last updated: 2026-11-03 (P1 merged; theme-ownership and mockup-is-the-spec rules in section 2). Governing decision: D-024 in [DECISIONS.md](DECISIONS.md). Status tracking: the table in section 9 (update it in the PR that completes each phase). GitHub `main` is authoritative.

## 1. What this is

Round 3 of the Neobrut work (round 1 is D-022, round 2 is D-023 and [BRUT_LAYOUTS_PLAN.md](BRUT_LAYOUTS_PLAN.md)). Round 2 rearranged the same screens. Round 3 also changes **what a screen is made of and how it is operated**: the dashboard becomes a board, pages become windows, an album becomes a receipt or a binder slot. Round 3 covers **every screen**, album and artist pages included, which round 2 only touched lightly.

The owner approved five themes, one palette each:

| Id | Theme | Platform | Idea in one line |
|---|---|---|---|
| Z | **Zine Spread** (`zine`) | Web | A newspaper front page; the album is an article, the artist a magazine cover |
| B | **Pipeline Board** (`pipeline`) | Web | A kanban board; dragging a card into Queued is Get |
| W | **Window Manager** (`windows`) | Web | A desktop: pages and albums are windows, two albums can sit side by side |
| R | **Receipt Roll** (`receipt`) | Android | Thermal receipt paper: itemised albums, barcode seek bar, tear-off slips |
| K | **Binder** (`binder`) | Android | A collector's binder: every album a slot, missing ones dashed with a Get |

Reference mockups (static HTML, open in a browser; tabs 1–5 are the approved themes): [`design/brut-round3/mockups.html`](design/brut-round3/mockups.html). Tabs 6–10 in that file (Workspace, Expressive, Seeded, Thumb Zone, Triage) are Material 3 based ordinary-theme ideas the owner has **not** approved; they are parked (ACTIVE_WORK.md, section 4) and must not be built from this plan. The mockups use third-party font links; the app itself must not (fonts and icons are self-hosted).

Mockup artifact (private to the owner, may expire): claude.ai/artifact/1AiN1zTmCphn4MeUUW5xKo.

### Owner decisions already taken

- All five Neobrut themes are kept.
- Each theme is built on **its own platform only** (web or Android). Companion palettes on the other platform are not part of this plan.
- **One palette per theme** to start. Variants (three per theme, as in round 2) are a separate optional phase, proposed through mockups first.
- The behaviour rule of D-023 (a layout may change how a screen is operated, for its own themes only) applies in full. Where a theme adds a gesture, a button alternative must exist.

## 2. Hard constraints (all phases)

Everything in BRUT_LAYOUTS_PLAN.md section 2 still applies. Restated, with the round 3 additions:

- The API is authoritative; no endpoint or field is invented. Domain, discovery, acquisition and import logic stay server-side (D-016: `navidrome_server.py` takes no additions). A need the existing data cannot meet is written up as a contract proposal and waits for approval (see section 7, "Data the mockups assume").
- **The approved mockups are the spec (owner rule, 2026-11-03).** `design/brut-round3/mockups.html` is what the owner approved. Each theme's screens must follow its mockup closely, element by element: every band, strip, column, box, label, headline pattern, behaviour hint (for example J / K, the letter margin, the index footer) and piece of dynamic copy the mockup shows is built, not approximated, and a light re-skin of the default page does not count. Before calling a screen done, compare it to the mockup tab for that screen and list every element; an element that cannot be built (a data gap, an accessibility conflict) is named in the PR with its fallback, never silently dropped. The sample numbers and names in a mockup are placeholders; the wording patterns (for example "You own two X records. Not this one.") are the design.
- **A theme owns its screens (owner rule, 2026-11-03).** A round 3 theme may change how any screen is laid out and operated, and may move, merge, replace or drop any element of the default layout, including shelves, carousels and the New releases list. Nothing in the default layout is sacred: the default theme keeps all of it, and the owner can switch back to it. Do not trade a theme's essential structure (for Zine Spread: the lead story, the New this week column and the Classifieds box) for fidelity to the default arrangement. What a theme may not do is change what the app is allowed to do: the data and actions stay the API's, every action keeps its real control and its confirmation, and Get, Save and Not for me always stay reachable (with a visible text label wherever the theme makes that action prominent). Where the theme replaces an element, it builds the replacement from the same builders and data (one render path per card), not a second implementation.
- **The web UI has no playback.** Nothing on the web may imply audio plays in the browser. Window Manager has no player window.
- **A gesture is never the only way.** Drag (Pipeline), swipe (Receipt), tap-on-slot (Binder) each have a visible button or keyboard equivalent that does exactly the same thing.
- **A gesture never skips a confirmation the button has.** Dismissing an acquisition deletes the album's folder (ACQ-04); a swipe or a drop may open the existing confirm, never replace it. Get and Save are non-destructive and may run on a drop.
- **The client never reports success before the server confirms** (existing rule). A card dropped into Queued shows the pending state, moves when the request is confirmed, and returns with a worded failure otherwise. The existing `searchAlbum(...)` flow and its `setGetButtonState` states are the single code path; a drop calls it (or clicks the card's real Get button), it does not re-implement it.
- Accessibility floor: WCAG 2.1 AA text contrast (computed in tests from the hex values), 44x44 px (web) / 48 dp (Android) touch targets, visible focus, full keyboard operation, `prefers-reduced-motion` honoured, status never by colour alone (words or icons).
- Existing themes (Ink and the eight others, the sixteen round 2 themes, the 20 app themes plus the seven app layouts) stay unchanged and selectable. The default stays Ink. Settings, login and account screens keep their structure on every layout.
- Fonts stay independent of the theme: the Brut font pairs apply on top of any layout. A theme may suggest a pair but must not force one.
- Web layouts apply from 900 px up. Below 900 px the existing phone shell is kept and receives only the theme's tokens and component skins.

## 3. Shared infrastructure

### Web (Z, B, W)

Already on `main` from round 2: `data-layout` set by `static/appearance.js` from a `layout` field on a theme entry; `static/layouts.css` with one block per layout, every selector scoped `:root[data-layout="…"]`; palettes as `:root[data-theme="…"]` blocks in `static/themes.css`; layouts loaded on the main page only.

Round 3 adds, per layout:
- Catalogue entries in `appearance.js` (`layout: 'zine'`, `'pipeline'`, `'windows'`; `brut: true`; `dark`; `bar` colour) in a new group each, shown as new optgroups in Settings > Appearance.
- A block in `layouts.css` headed `==== Zine Spread ("zine")` (same header style as the others, the tests split on it).
- A palette block in `themes.css` with the full token set (see the existing Brut themes for names: `--ink-rail`, `--ink`, `--surface`, `--surface-raised`, `--surface-hover`, `--edge`, `--text*`, `--accent*`, `--on-accent`, `--focus`, `--bw`, radii, `--brut-*`).
- Hooks in `app.js` / `index.html` that are **hidden by default** and shown only by the layout, so every other theme renders exactly as today. New JS lives in new functions guarded by `document.documentElement.dataset.layout === '…'`; prefer a new file (for example `static/layout-pipeline.js`) over growing `app.js` (6,205 lines), registered in the template, the static packaging and the packaging tests.
- A test module `tests/test_<layout>_layout_ui_contract.py` in the pattern of `test_crate_layout_ui_contract.py`: catalogue ids and fields, every selector scoped, full token set, AA contrast of text on ground, text on accent and focus, hooks hidden without the layout, reduced motion disables animation.

Phone-width web is not redesigned (decision in BRUT_LAYOUTS_PLAN.md section 4 stands).

### Android (R, K)

Already on `main`: the `Layout` enum in `ui/theme/Palette.kt` (`Standard`, `TapeDeck`, `SheetStack`, `StickerWall`), `layout` on `Palette`, `currentLayout()` in Compose, `BrutalComponents.kt` wrappers.

Round 3 adds `ReceiptRoll` and `Binder` to the enum (first PR that needs each), one palette each, pure rule objects with unit tests (`ReceiptRollRules` in `ui/common/ReceiptRoll.kt`, `BinderRules` in `ui/common/Binder.kt`; test style of `StickerWallTest`), and screens that read `currentLayout()` and fall back to today's composition for `Standard`. Reuse `BrutalComponents`; add missing pieces there or in the layout's own file, do not fork Material usage at call sites. Player behaviour (D-018 gapless, scrobbling, D-020 equalizer, D-021 crossfade) is unchanged.

Build and install commands (from the owner's notes): `ANDROID_HOME=/opt/homebrew/share/android-commandlinetools JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home ./gradlew testDebugUnitTest assembleDebug lintDebug assembleRelease --offline`; the phone accepts only the release-signed APK, copied to `Desktop/disqair/discair-<name>-release.apk`; install with `adb install -r` **only when the owner asks**. Compose cannot uppercase through a style; uppercase display strings in code with `String.uppercase()` and keep the real name in the accessibility label.

## 4. Palettes (starting values from the mockups)

Token names as in round 2: `bg` ground, `sf` surface, `ink` text and outlines, `mu` muted text, `ac` accent. Every value is a **starting value**; each PR derives the app's real tokens, checks contrast, and records any adjustment in its PR description. Not yet checked for contrast: every muted text on a coloured ground, white on violet and red, ink on pink.

| Theme (proposed label) | bg | sf | ink | mu (to set) | accents |
|---|---|---|---|---|---|
| Zine · Yellow (`zine`) | `#f1ede4` | `#ffffff` | `#111111` | `#4a463d` | yellow `#ffde59` (masthead, current), pink `#ff4d6d` (kicker), teal `#2ec4b6` (buttons) |
| Pipeline · Orange (`pipeline`) | `#e7f0ff` | `#ffffff` | `#0a0a0a` | `#3d4663` | orange `#ff7a1a` (progress), lime `#c6f432` (toast, Get), yellow `#ffde59`, violet `#7b4dff`, red `#d7263d`, teal `#2ec4b6` (genre tags; white on violet and red must pass or the text stays ink) |
| Windows · Pink (`windows`) | `#ffb4c8` + dot grid `#0a0a0a` | `#fffdf6` | `#0a0a0a` | `#4a4440` | yellow `#ffde59` (title tab, current), orange `#ff7a1a`, green `#9be3b0` (Owned), rose `#ff9aa8` (Missing) |
| Receipt · Paper (`receipt`, Android, light) | `#d8d4cc` | `#fffef8` | `#1a1a1a` | `#4a4640` | stamp red `#d7263d`, yellow `#ffde59` (ADD, nav) |
| Binder · Teal (`binder`, Android, light) | `#fbf1e3` | `#ffffff` | `#17110a` | `#5c4630` | teal `#2ec4b6`, pink `#ff7a8a`, yellow `#ffde59`, violet `#7c5aa6`, blue `#a8d8ff`, lilac `#d9c6f2` |

Labels are proposals; the owner may rename them in the first PR of each theme. All five are light themes (Day list). A dark variant of any of them is a variants-phase decision.

## 5. Web themes

For every screen, "unchanged" means content and behaviour stay as today and only tokens and component skins apply. Screen names below are the app's own pages. The artist page and the album window are the existing Library artist detail (`#artistDetail*`, ids in `index.html` around line 370) and `.album-modal`.

### Z. Zine Spread (phase P1)

Idea: print. Dense, columnar, headline-led. Reading order matters; J / K moves through stories.
- **Shell:** masthead band (wordmark as "THE DISCAIR DAILY" is a **visual** treatment of the existing wordmark and date, no new text in the data), the existing nav as a stamped label strip under it (like Crate Wall's strip but a different skin: thick ruled boxes, no tilt), a ticker strip built from the acquisition list already loaded (Downloading, Imported, Failed, with words).
- **Dashboard:** "lead story" = the first item of the existing Recommended carousel (cover with hard shadow, a large condensed headline from the album title, a two-column blurb using the existing bio/why text, Get and Not for me as the existing controls). A right column "New this week" from the existing New releases shelf; "Classifieds" box = the existing Missing/Newly-added data as a short list with the existing Get. Shelves below become ruled narrow columns. The `Ctrl K` hint and shortcut follow the other layouts.
- **Library:** an A–Z index: a letter margin and the artist list as three columns with dotted leaders. The letter margin scrolls to the first loaded row for that letter. **Open point:** if the library list is paged by the API, letters beyond the loaded rows need the existing search/filter, not a client-side re-sort; decide while building (the safe default is to disable letters with no loaded row, with a tooltip).
- **Album:** the existing album window restyled as an article: giant headline, byline row (artist, year, genre, quality from existing fields), pull quote from existing description text if present, a two-column contents box for the tracklist where a missing track's Get is styled as a dashed coupon (it is the real per-track Get, ACQ-08). Album-level Get and Save stay in the byline row.
- **Artist:** a magazine cover: the artist name set very large and cropped by the right edge (real text in the DOM, `overflow: hidden`, the accessible name unchanged), a rotated-free "cover lines" box from Top songs, the owned albums and missing albums as "back issues" (owned solid, missing dimmed with a dashed border and the word Missing plus Get), similar artists as "also in this issue" chips, bio below.
- **Acquisitions:** each request is a "dispatch": headline from the album title, a one-line state in words, a press-run bar for progress, Retry and Dismiss unchanged.
- **Behaviour:** J / K steps between stories on the dashboard and lines on the library list (only when focus is not in a field); Ctrl/Cmd+K as the other layouts.
- **Palette and type:** Zine · Yellow. Suggested font pair: Poster shout (Anton) for headlines; the layout works with any pair.
- **Acceptance:** works at 1280, 1024 and 900 px, falls back correctly at 899 and 390; long names wrap inside the headline, never clip; the cropped artist name has the full name available to assistive tech; no horizontal overflow; keyboard order matches reading order; the nine round 1 and sixteen round 2 themes render byte-identical CSS outside the new blocks.

### B. Pipeline Board (phase P2)

Idea: the app's job is "from what should I add next to a confirmed request"; the screen is that pipeline.
- **Dashboard:** a five-column board: Recommended (the existing dashboard picks), Saved (the Saved page's existing loader), Queued and Downloading (the acquisition list already loaded), In library (the existing Newly added shelf data). Cards carry a genre colour bar like the genre tiles. Each card is the existing card with its real Get / Save / Not for me controls inside; the board only arranges them.
- **Drag:** HTML5 drag and drop, desktop only (the layout is 900 px and up). **Drop on Queued** = click the card's real Get button (the `searchAlbum` path): the card shows the pending state in place and moves to Queued only when the server confirms and the acquisition list reports it; on failure it stays where it was with the worded failure (existing toast and `is-failed` state). **Drop on Saved** = the real Save. No drop target for Not for me (destructive paths stay buttons). A toast region (`role="status"`) announces results.
- **Keyboard:** Space picks a card up, arrows move between columns, Enter drops; the same two actions (Get, Save). A visible "Move to…" menu button on each card is the non-drag, non-chord alternative.
- **Library:** swimlanes by genre (a lane per genre with the albums as cards), reusing the genre loader from the dashboard accordion (PR #708) and `/api/library/*` data; a lane loads on first open, like the accordion.
- **Album:** the album window gains a stage tracker (Recommended, Saved, Queued, Downloaded, In library) derived from state the card already knows; the stage shown is a **word and a position**, never colour alone; per-track Get unchanged.
- **Artist:** three lanes: In library (owned albums), Missing (missing albums, each draggable to Queued with the same rules), Similar artists (cards that open the artist).
- **Acquisitions:** the right four columns of the board: Queued, Downloading, Done (Imported), Failed, live progress bars from the existing stream; Retry and Dismiss unchanged, Dismiss keeps its confirm.
- **Palette and type:** Pipeline · Orange. Suggested pair: Swiss brut or Baseline.
- **Acceptance:** drag works with a real request on the local test server with slskd disabled (the failure path is the testable one) and the pending/failed states are visible; keyboard path reaches the same result; reduced motion removes card tilt and transitions; board scrolls sideways inside its own container only when it must; at 900 px five columns still fit or scroll cleanly; tests assert the drop code calls the existing request function and contains no second `fetch('/api/acquire')`.
- **Risk:** the board duplicates cards that other pages also render. Cards must be cloned from, or re-rendered by, the existing render functions, not rebuilt by hand, so state (pending, requested, failed) stays one source of truth. Decide in the first hour of P2 and write the choice in the PR.

### W. Window Manager (phase P3, two steps)

Idea: a desktop. The riskiest web theme (focus order, dialog rules), so it is split.
- **P3a, shell and single windows:**
  - Desktop ground (colour plus dot grid), a taskbar at the bottom listing open windows (the nav moves here as the launcher; the existing nav keeps its buttons, restyled and repositioned, the order in the DOM matches the visual order).
  - The current page is shown as one large window with a title bar (page name, a close button that returns to the Dashboard). Only the current page is open, as today (`.page.hidden` is `display: none !important`; the layout does not change that).
  - Dashboard: shelves as separate smaller windows arranged in a fixed grid (not freely draggable in P3a), plus desktop icons for the pages.
  - Library: a file-explorer window (genre tree on the left from the existing genre list, icon view on the right).
  - Album: the existing album window as a floating window with a title bar (non-modal look, still the existing `dialog` element and focus trap in P3a).
  - Artist: a profile window with tabs Albums, Similar and Bio (tabs are the existing sections, shown one at a time through the existing neobrut tabs component).
  - Acquisitions: a task-manager table (Name, State, Progress, Action).
- **P3b, compare two albums:** a second album window. **Spike first:** can `openAlbumModal` render into a given container? If yes, open a second instance. If not, the compare window is a snapshot of the tracklist (owned/missing status per track and its real Get via `searchAlbum`), labelled as a snapshot. Either way: at most two album windows; Esc closes the top one; windows are draggable by the title bar and have a keyboard move mode; positions are remembered for the session only (`sessionStorage`).
- **Accessibility:** a window with a title bar is a `role="dialog"` only if it is modal; floating windows are regions with a heading, and focus moves to the opened window and back on close. Draggable never means drag-only: windows also open at fixed, non-overlapping default positions.
- **Palette and type:** Windows · Pink. Suggested pair: Technical (Rubik Mono One / IBM Plex Mono).
- **Acceptance:** P3a ships without P3b; the spike result and decision are recorded in the PR; 900/1024/1280 px, no horizontal overflow; tab order equals reading order after the nav moves; Esc and backdrop behaviour of the album window match the existing album-modal tests.

## 6. Android themes

Both are light, Brutal family. Screen set: Home, Library, Album, Artist, Downloads, Now Playing (plus Search, Discover and Settings, which get tokens and components only unless noted).

### R. Receipt Roll (phase P4: plumbing and Receipt Roll)

Idea: everything printed on thermal paper: monospace, dashed rules, itemised lines, stamps.
- **Components** (`ui/common/ReceiptRoll.kt`): `ReceiptPaper` (white sheet, 3 dp ink outline, hard shadow, zig-zag bottom edge drawn as a custom shape), `ReceiptRule` (dashed), `ReceiptLine(label, value)` with a leader, `ReceiptStamp(word)` (static rotation, word always visible), `ReceiptAdd` (yellow ADD button, 48 dp touch height), `BarcodeSeek`.
- **Navigation:** one stamped four-cell bar: Home, Search, Library, Player; the current cell inverted. Downloads, Discover and Settings are buttons on Home (as Sheet Stack did for Library). A one-line mini player ("NOW: TEARDROP 2:08") sits above the bar while a song is queued and opens Now Playing (same behaviour as the Cassette Deck mini player).
- **Home:** "daily receipt": picks as lines with ADD (the real Get), then OPEN ORDERS from the same acquisition hub as Downloads (state in words), then a footer barcode that is decoration only (`contentDescription = null`).
- **Library:** inventory ledger: artist and album-count lines. **Fractions like `2/5` need the missing count, which the library list does not carry**; show the owned album count only (see section 7).
- **Album:** an itemised receipt: header, one line per track (number, title, duration); a missing track's line has ADD (the real per-track Get); total line "OWNED 10/11" computed from the per-track `owned` flags the page already has; album-level Get and Save as ADD and SAVE lines.
- **Artist:** the artist file: top songs (existing), discography lines (✓ or ADD), similar artists as "ALSO BOUGHT" lines.
- **Downloads:** order slips, one per request, state as a word stamp (FETCHING, QUEUED, DONE, FAILED), progress as a text bar. **Swipe left on a slip opens the existing Dismiss confirm; it never dismisses by itself**; a visible Dismiss button does the same; Retry unchanged.
- **Now Playing:** queue as receipt lines under the cover line, `BarcodeSeek` replaces the seek bar (a real slider semantics: value, range, step, drag and tap, 48 dp touch height; the stripes are drawn, the red marker is the thumb), "REMAINING" total line, lyrics printed line by line (a reveal animation, off under reduced motion; the existing lyrics feature D-019 and its no-lyrics states are unchanged), the existing equalizer and crossfade entry points kept as stamped buttons. Playback logic untouched.
- **Palette and type:** Receipt · Paper. The chosen font pair still applies; the receipt's numerals, line values, rules and labels use that pair's mono face.
- **Acceptance:** `ReceiptRollRules` unit-tested (nav cells, mini-player visibility, total-line rule, swipe-opens-confirm rule); palette in `PaletteTest` and `AppearanceRulesTest` (id, layout, Day list, AA contrast of ink on paper, ink on yellow, red on paper); `assembleDebug`, `lintDebug`, R8 `assembleRelease`; the owner checks on the phone (TalkBack on the seek bar and the slips, 200% text).

### K. Binder (phase P5)

Idea: collecting. Every album is a slot in a binder page; a missing slot is dashed with a Get. Built from the owner's neobrutalism screenshots: stat cards, stacked progress bars, overlapping avatars, colour-block panels with one oversized corner, joined tabs, a round play button with a crescent shadow. Tilt and sticker badges are deliberately not used, so it stays different from Sticker Wall.
- **Components** (`ui/common/Binder.kt`): `BinderSlot` (owned: cover with a name strip; missing: dashed hatched silhouette with a round Get button and the album name; the whole slot is one button, named "album, by artist, owned or missing"), `StatCard`, `StackedBar` (two to three labelled bars), `AvatarStack` (overlapping circles, "+N"), `ColourBlock` (panel with one oversized rounded corner), `CrescentPlay`.
- **Navigation:** four round buttons (Home, Library, Downloads, Player) with a hard shadow; the current one filled.
- **Home:** "Your collection": stat cards from data already on the device or in the hub (owned album count from the library list, requests Fetching and Queued from the acquisition hub, picks waiting), a stacked bar of requests by state, then "Fill the next slot": a binder page of the day's picks with missing slots.
- **Library:** one binder per artist (cover, name, album count). **Completion percent needs the missing count per artist; not available in the list** (section 7); show the album count only.
- **Album:** a card header (cover, title, artist, year, genre), two stat cards (tracks owned of total from the per-track flags; quality), the tracklist as rows with the per-track Get.
- **Artist:** a binder page of the discography: owned albums filled, missing ones dashed with Get; a completion bar and the line "2 of 5 known albums" computed from `owned_albums` and `missing_albums` (the label says "known albums" because the missing list is capped and ranked); similar artists as an avatar stack that opens the artist.
- **Downloads:** each request shows three labelled stacked bars: SEARCH (full once past searching), TRANSFER (the real percentage), IMPORT (full once imported); failed requests are a coloured block with the word FAILED and Retry; Dismiss keeps its confirm.
- **Now Playing:** a colour-block cover panel, the existing seek bar skinned (thick outlined track), `CrescentPlay` and round previous / next / repeat / shuffle, a joined tab row Queue, Lyrics, EQ that switches among the existing queue panel, lyrics strip and the equalizer entry. Playback logic untouched.
- **Palette and type:** Binder · Teal; font pair applies.
- **Acceptance:** `BinderRules` unit-tested (slot state from owned flag, completion line, the three-bar mapping from request state); palette tests as for Receipt; the three bars never show a state by colour alone (each has its word label); same builds and owner phone check.

## 7. Data the mockups assume (check before building; do not invent)

| Mockup shows | Available today? | Plan |
|---|---|---|
| Owned / total per artist in the library list (Zine, Receipt, Binder) | No: the list has the owned count only | Show the owned count. A `missing_count` field on library artist rows is a **contract proposal** that needs the owner's approval; do not start it in a layout PR |
| Library-wide "missing" total (Binder Home) | No | Not shown; Home uses owned count, requests and picks |
| Discography completion on the artist page | Yes, from `owned_albums` and `missing_albums` (missing is capped at 50 and ranked) | Label it "known albums" |
| Per-track owned flags on the album page | Yes (PR #635) | Used for totals and coupons |
| Search / transfer / import phases of a request | Partly: states plus transfer percentage | Map as described in section 6 K; no new fields |
| Saved list on the dashboard (Pipeline) | The Saved page loads it; the dashboard does not | Pipeline loads it with the Saved page's existing loader, in this layout only |
| Genre loader for swimlanes | Yes (`/api/genres/{tag}`, PR #708) | Reuse |

## 8. Decision D-024 (text for DECISIONS.md)

Recorded in [DECISIONS.md](DECISIONS.md) in the same commit as this plan.

## 9. Phases and status

One PR per phase except P0 and the closeout (documents, direct to `main`). Each code PR: branch from current `main`, focused tests only (never the full unit suite), CI green on the exact final head, the owner's manual check on that head, squash merge, then a documentation commit updating this table, `PROJECT_STATUS.md`, `ACTIVE_WORK.md` and `PROJECT_LOG.md`. After each merge the final response includes the `Did you know?` Python lesson required by `DEVELOPMENT_WORKFLOW.md`.

| Phase | Scope | Status |
|---|---|---|
| P0 | This plan, D-024, mockups in `docs/design/brut-round3/` | **done 2026-11-03** (documentation, direct to `main`) |
| P1 | Web Zine Spread: catalogue entry, palette, `layouts.css` block, hooks, all five web screens, tests | **done 2026-11-03**, PR [#709](https://github.com/abucalip/navi-librarian/pull/709), squash `3f546f9ec409a127ca8d5ce8f9e677ba1865479e` (see "As built, P1" below) |
| P2 | Web Pipeline Board: board, drag with real Get and Save, keyboard path, swimlanes, stage tracker, tests | not started |
| P3a | Web Window Manager: shell, taskbar, single windows on every screen, tests | not started |
| P3b | Web Window Manager: second album window (spike first) | not started |
| P4 | Android Receipt Roll: `Layout.ReceiptRoll`, palette, components, nav and mini player, Home, Library, Album, Artist, Downloads, Now Playing, tests | not started |
| P5 | Android Binder: `Layout.Binder`, palette, components, all screens, tests | not started |
| V | Optional: palette variants for any of the five (mockups first) | not started, owner's call |
| P6 | Closeout: documents; a published release only when the owner authorises it | not started |

Order rationale: web first, from the most CSS-only (Zine) to the riskiest (Window Manager); Android after, Receipt before Binder because Receipt reuses the plumbing pattern of the Cassette Deck. The order may be changed by the owner; phases are independent apart from the shared plumbing (the Android `Layout` enum additions go in whichever Android phase comes first).

## 10. Starting a phase in a new session

1. Read `handoff.md`, `ACTIVE_WORK.md` (section 2i), this plan, `DEVELOPMENT_WORKFLOW.md`, and the previous layout PRs for the pattern: the round 2 plan's "As built" notes (BRUT_LAYOUTS_PLAN.md sections 5 to 7 and 10) list the lessons: rows must grow, never clip; hide placeholder marks in small covers; drop the last item's right rule in groups; a hidden `.page` is `display: none !important`.
2. Check current `main`, open PRs and CI. Branch from `main`.
3. Open the mockup tab for the theme and the screen. The mockup is a design reference, not code to ship.
4. For web: follow `LOCAL_UI_TESTING.md` (isolated data, slskd disabled) and check the layout without a login by rendering `app/templates/index.html` with sample rows in headless Chrome. Server for testing: system `python3` with `.venv` site-packages, uvicorn on 127.0.0.1:8089.
5. Run only the focused tests: the new `test_<layout>_layout_ui_contract.py`, the other `*ui_contract*` modules touched, and the fonts test, with `PYTHONPATH=.venv/lib/python3.12/site-packages python3 -m unittest …`. `node --check static/app.js` (and any new script). Never the full suite.
6. Do not widen the scope: no new pages, endpoints or playback on the web. A data gap goes in the PR description as a contract proposal.

### First task: P1, Zine Spread

1. Add the catalogue entry `zine` (`label: 'Zine · Yellow'`, `group: 'Zine Spread'`, `dark: false`, `brut: true`, `layout: 'zine'`, `bar: '#ffde59'`), the `:root[data-theme="zine"]` palette block in `themes.css` (section 4), and the `==== Zine Spread ("zine")` block in `layouts.css`.
2. Build the shell first (masthead, label strip, ticker from the acquisition list), check it at 1280, 1024 and 900 px, then the dashboard lead story, then Library index, Album article, Artist cover, Acquisitions dispatches, one screen at a time, in that order, committing after each.
3. Add hidden-by-default hooks in `index.html` and `app.js` only where CSS cannot reach (ticker, lead-story wrapper, letter margin, J/K handler, Ctrl/Cmd+K reuse).
4. Write `tests/test_zine_layout_ui_contract.py`; register any new file in the packaging tests.
5. Open the PR; CI green on the final head; the owner checks in the browser; merge; documentation commit.

## 11. Risks and open points

- **Pipeline duplicates cards** that other pages render (section 5 B): keep one render path.
- **Window Manager** touches focus order and dialog semantics; split in two and spike the second window.
- **Two data gaps** (completion fractions, library-wide missing total) change the mockups: the plan shows the fallbacks; a `missing_count` contract is parked until the owner decides.
- **Contrast** of muted text on coloured grounds and of white on violet, red and teal is unchecked; a failure changes the palette value, not the layout.
- **Android regression risk** on Home and Now Playing (seek, queue, lyrics, equalizer, crossfade entry points): each Android PR keeps `Standard` as the default and unit-tests the layout selection logic.
- **Receipt's barcode seek bar** must keep real slider semantics and a 48 dp touch height; the stripes are decoration.
- **Typography:** Compose cannot uppercase through styles; uppercase in code and keep the real name for TalkBack.
- Fonts and icons are self-hosted; the mockups' Google Fonts links never ship.

## 12. As built, P1 (Zine Spread, PR #709)

Lessons for the other web themes:
- **Build to the mockup element by element.** A first pass that only re-skinned the default pages was rejected; the accepted one rebuilt each screen from the mockup (see the rules in section 2). Keep a checklist per mockup screen.
- **Own file, one hook function.** All behaviour is in `static/layout-zine.js`; `app.js` reaches it only through `zineHook(name, ...)` (a no-op when the file or layout is absent). New hidden-by-default elements in `index.html`, shown only by the layout.
- **Replace, do not restyle, where the default structure fights the design.** The default Recommended panel and New releases shelf are hidden by the layout and the front page is built from the same data with the same builders (`buildDashboardTile`, `buildShelfCard`), so Get, Save and Not for me are the real controls; the dismiss path in `app.js` was made to work for tiles outside the slider.
- **Words for state.** Text labels on Get, Save and Not for me where prominent; verbs for acquisition state in CSS (`content: "..." / ""`).
- **Reads used (existing endpoints only):** `/api/library/albums` (owned albums by the lead's artist), `/api/album-description`, `/api/settings/slskd` (first quality). The lead copy is built from these plus the picks' `reason`/`anchor_artist` and the Most played shelf; the album description leads and the artist bio is the fallback.
- **Departures recorded in the PR:** library rows show "n albums" (no per-artist total in the API); cover lines are text, with the real Top songs list kept below; fine-pointer letter buttons 24 px (44 px on touch); Classifieds built from the remaining picks (no library-wide missing list).
- **Not covered:** the album page's contents box falls under the cover column at 1280 px (floats); phone width is unchanged by design; Get all, Get missing, Not for me and Undo were not exercised by the agent against real data (the owner reviewed the screens in the browser).
