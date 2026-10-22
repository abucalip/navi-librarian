# Header gear menu — Settings and Log out (plan, now merged)

Last updated: 2026-10-18
Status: **merged as PR #327 (commit `4951374` on `main`).** The implementation follows §9 of
this plan. The text below is kept as the record of the plan. Where the plan and the merged code
differ, the merged code is authoritative.
Base: GitHub `main` at `9a8a8f1` ("docs: generalize frontend contribution ownership").
Line numbers below are against that SHA and will drift; re-inspect before implementing.

This file is a proposal under root `AGENTS.md`: documentation outside
`docs/UI_BACKLOG_EXECUTION.md` is normally proposed rather than edited, and this file was
created because the operator asked for it explicitly. The implementation PR that follows must
also update `docs/UI_BACKLOG_EXECUTION.md` in the same PR, as `AGENTS.md` requires.

## 1. Objective

Move **Settings** and **Log out** out of the sidebar and into a gear icon button at the top
right of the header. Activating the gear drops down a small menu containing those two items.

Why it matters: both items are account/system controls, not content destinations, yet they sit
in the rail directly under the seven discovery items and read as equals of them. The rail's own
history already anticipates this: `docs/UI_BACKLOG_EXECUTION.md` §5b records that "Acquisitions
and Settings are intended to move elsewhere later, as is Log out." This change does Settings and
Log out. **Acquisitions stays in the rail**; it is a content destination with a live count badge.

Visitor mode (Impeccable): **Operate**. The user is in a task and the control must be familiar
on sight. Brand lives in precise details, not in a novel pattern.

## 2. Constraints that bound the design

- Front-end-only. Allowed files: `static/app.css`, `static/app.js`, `app/templates/index.html`,
  and a narrowly scoped test under `tests/`. No backend, API, auth, or cookie change.
- **No contract change.** Logout keeps calling `POST /api/auth/logout` and then
  `window.location.replace('/login')`. Settings keeps loading through the existing
  `initializePage('settings')` path. No endpoint or field is invented.
- No new dependency, icon font, CDN asset, or build step. The icon is authored inline SVG.
- Preserve identity: dark grey foundation, yellow accent, red for destructive/error only, and
  the three established families.
- No wholesale redesign. One cohesive, reviewable change.

## 3. Current state (verified in source at `9a8a8f1`)

| Fact | Where |
|---|---|
| Header is `position: fixed`, `z-index: 20`, flex with `justify-content: space-between`; holds `<h1>` (cassette mark plus title) and a tagline `<p>` that is right-aligned and hidden at ≤620px | `index.html:13-16`, `app.css:50-60`, `app.css:398` |
| Settings is `<button data-page="settings">` and Log out is `<button id="logoutButton">`, both direct children of `<nav>` after `.nav-list` | `index.html:50-51` |
| Neither is pushed to the bottom of the rail: there is no `margin-top: auto`, so removing them simply shortens the rail | `app.css:62-66` |
| Page switching is `showPage(name)`; it toggles `.active` on `nav button[data-page]`, then runs `moveNavBlob()` and `syncNavAria()` | `app.js:18-25` |
| `moveNavBlob()` already hides the blob when no `.nav-list > button.active` exists, so being on Settings with no rail item active is handled | `app.js:30-37` |
| Rail click listener does three things: `showPage(name)`, `initializePage(name)`, and `stopAcquisitionStream()` unless the page is acquisitions | `app.js:62-68` |
| `initializePage('settings')` is what loads the four settings panels; a menu item that only calls `showPage` would open an empty Settings page | `app.js:58` |
| Logout handler is bound by id and is independent of where the button lives | `app.js:2201-2204` |
| Global `button` styling: 4px radius, `--surface` fill, `--border` edge; hover gives a yellow border and `--surface-hover` fill; focus-visible is a 2px yellow outline with 2px offset | `app.css:45-49` |
| Stacking: header 20, rail 15, skip link 100, album modal backdrop 100, toasts 200 | `app.css` z-index grep |
| At ≤620px the rail becomes a horizontal scroller under a 70px header; the active item gets `inset 0 -3px var(--yellow)` | `app.css:397-409` |
| There are no `data-go` buttons in the template and no UI test references the Settings or Log out buttons | grep of `index.html`, `tests/` |

## 4. Design brief

**Job and audience.** A returning librarian-owner who needs to reach configuration or end the
session, occasionally, from any page. Neither action is frequent; both must be findable without
instruction.

**Selected direction.** The standard pattern: a gear at the far right of the header opens a
dropdown anchored beneath it. Familiarity is the feature. No avatar or user chip: the API exposes
no user identity, and inventing one would require a backend field.

**Structural thesis.** The header gains a right-hand tool group (tagline, then gear). The menu is
a child of the fixed header, so it is not clipped by any `overflow` ancestor and needs no portal.

**Anti-goals.** No scrim or modal treatment. No icons beside the menu items. No red Log out
(see §6.2). No display font in the menu. No entrance choreography. No badge on the gear.

**Assumptions** (Impeccable's `shape` flow normally interviews first; the request was specific, so
these are stated instead of asked, and any of them can be reversed cheaply):

1. Menu items are exactly **Settings** and **Log out**, in that order, with existing wording.
2. Log out needs no confirmation step, matching current behavior.
3. Acquisitions is not part of this change.
4. The tagline stays in the header, to the left of the gear.

## 5. Layout and component spec

### 5.1 Header (≥621px)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ [cassette] NAVIDROME LIBRARIAN      LISTENING INTELLIGENCE · DISCOVERY INDEX  [⚙] │
└────────────────────────────────────────────────────────────────────────────┘
                                                                    ┌──────────────┐
                                                                    │ Settings     │
                                                                    ├──────────────┤
                                                                    │ Log out      │
                                                                    └──────────────┘
```

- Wrap the tagline and the gear in `.header-tools`: `display: flex; align-items: center;
  gap: 20px`. The existing `header` rule keeps `space-between`, so the h1 stays left and the
  tool group stays right. Header height (`min-height: 82px`) is unchanged; a 44px control fits.
- The tagline keeps its current style and remains hidden at ≤620px.

### 5.2 Gear toggle

- 44×44px hit area (the project's touch-target floor, from PR #194), 4px radius to match every
  other control, 1px `--border` edge, transparent fill at rest.
- Inline SVG, `viewBox="0 0 24 24"`, rendered at 20×20, `fill="none"`, `stroke="currentColor"`,
  stroke width 1.75, round caps and joins, `aria-hidden="true"`, `focusable="false"`. Authored
  here; no third-party set. If an existing permissively licensed shape is adapted, record its
  license in the PR.
- Accessible name: `aria-label="Settings and account"`, plus matching `title` for pointer
  users. `aria-haspopup` is **not** used (see §6.1). `aria-expanded` and `aria-controls` are.

### 5.3 Panel

- Absolutely positioned inside `.header-menu` (`position: relative`), right edge aligned to the
  toggle, 8px below it. `min-width: 176px; max-width: calc(100vw - 30px)`.
- `--surface-raised` fill, 1px `--edge-strong` border, `--radius` corner, 4px inner padding,
  one shadow via a new token (§7.2). The shadow is justified: this is the only element that
  floats over arbitrary content, and a 1.22:1 fill difference alone does not separate it.
- Items are `<button type="button">`, full width, left-aligned, `min-height: 44px`,
  `padding: 10px 14px`, 3px radius, no border, transparent fill. A 1px `--border` separator
  sits between Settings and Log out, `margin: 4px 0`, so the session action is set apart from
  navigation.
- Opens with a 150ms opacity and 4px `translateY` fade. Closes instantly.

### 5.4 States

| Element | State | Treatment | Non-colour cue |
|---|---|---|---|
| Toggle | rest | glyph `--text-chip`, 1px `--border` edge | the glyph itself |
| Toggle | hover | glyph `--text`, fill `--surface-hover`, edge `--yellow` (inherited global rule) | edge weight and fill change |
| Toggle | focus-visible | 2px `--yellow` outline, 2px offset (inherited global rule) | outline shape |
| Toggle | active (pressed) | same as hover; no extra effect | — |
| Toggle | expanded | fill `--surface-raised`, edge `--yellow`, glyph `--yellow` | `aria-expanded="true"`; panel visible |
| Toggle | current page is Settings | glyph `--yellow`, `inset 0 -3px var(--yellow)` | the 3px bar is a shape, reused from the rail's narrow-width active state |
| Toggle | disabled | not applicable; the toggle is never disabled | — |
| Item | rest | `--text` on `--surface-raised` | — |
| Item | hover | fill `--surface-hover` | fill change |
| Item | focus-visible | 2px `--yellow` outline, **inset** (`outline-offset: -2px`) so the panel edge cannot clip it | outline shape |
| Item | current (Settings while on Settings) | fill `--yellow-dim`, 3px `--yellow` left bar, `aria-current="page"` | the bar |
| Item | loading (Log out in flight) | `disabled`, `aria-busy="true"`, global `opacity: .55` | dimming plus not-allowed behavior |
| Item | error | none: logout redirects in `finally`, as today | — |

## 6. Decisions and reasoning

### 6.1 Disclosure pattern, not `role="menu"`

The WAI-ARIA Authoring Practices reserve `role="menu"` for application-style command menus and
treat site navigation as a **disclosure**. This is a two-item navigation-and-session menu, so a
button with `aria-expanded` and `aria-controls`, controlling a plain group of buttons, is the
correct semantic and carries far less keyboard-management risk. `role="menu"` would oblige full
roving arrow-key behavior and would announce as an application widget. Up/Down/Home/End between
items are added as a progressive enhancement, not as a requirement of the pattern.

### 6.2 Log out is neutral, not red

`AGENTS.md` and the design guide reserve red for destructive actions and errors. Logging out
destroys nothing. It also fails contrast: the existing `--red-text` (`#ff5148`) measures
**4.43:1 on `--surface-raised`** and **4.02:1 on `--surface-hover`**, both below the 4.5:1 AA
floor for 13px text, and `--red` (`#e05b4f`) is lower still at 3.92:1. Log out therefore uses
`--text`. The separator carries the distinction.

### 6.3 Current-page cue lives on the toggle as well as the item

With Settings out of the rail, no rail item is active on the Settings page and the user loses
their "you are here". The toggle takes `inset 0 -3px var(--yellow)` plus a yellow glyph, and the
Settings item takes `aria-current="page"` while the menu is open. The bar is the same shape
vocabulary the rail already uses below 620px.

### 6.4 No icons beside the items, no display font

Two short text labels do not need glyphs (the design guide lists unnecessary icons as an
anti-pattern), and `operate.md` flags display fonts in UI labels. Barlow Condensed stays on the
header title only.

## 7. Colors and typography

### 7.1 Color tokens used

Every value below already exists in `:root` at `app.css:4-39`. **No new color is introduced.**
Ratios were computed with the WCAG relative-luminance formula.

| Token | Hex | Role in this feature |
|---|---|---|
| `--chrome` | `#1d1f1e` | header background (unchanged); gear rests on it |
| `--bg` | `#191a1a` | page background behind the panel |
| `--border` | `#3b3d39` | toggle edge at rest; separator; header bottom edge |
| `--text` | `#f0eee5` | item labels; toggle glyph on hover |
| `--text-chip` | `#b7b8ae` | toggle glyph at rest (same role as rail items at rest) |
| `--muted` | `#a5a69c` | tagline (unchanged) |
| `--surface-raised` | `#292b2a` | panel fill; toggle fill while expanded |
| `--surface-hover` | `#30322f` | toggle and item hover fill |
| `--edge-strong` | `#55574e` | panel border (same token the modal border uses) |
| `--yellow` | `#e9c64a` | hover/expanded edge, expanded and current glyph, focus ring, current bars |
| `--yellow-dim` | `#554b26` | fill of the current menu item (same as the rail's active blob) |

Not used, on purpose: `--red` `#e05b4f`, `--red-text` `#ff5148`, `--on-yellow` `#191a1a`,
`--subtle` `#94958b`.

### 7.2 One new token (non-color)

`--shadow-menu: 0 8px 24px rgba(0,0,0,.45);` added to `:root`, so the shadow is named rather
than written inline, following the token cleanup in PR #194. Pure black at 45% is a shadow, not a
palette color.

### 7.3 Contrast, measured

| Pair | Ratio | Needs | Result |
|---|---|---|---|
| `--text-chip` glyph on `--chrome` (gear at rest) | 8.27:1 | 3:1 (graphic) | pass |
| `--text` glyph on `--surface-hover` (gear hover) | 11.13:1 | 3:1 | pass |
| `--yellow` glyph on `--surface-raised` (gear expanded) | 8.58:1 | 3:1 | pass |
| `--yellow` glyph on `--chrome` (gear current) | 9.98:1 | 3:1 | pass |
| `--text` on `--surface-raised` (item at rest) | 12.26:1 | 4.5:1 | pass |
| `--text` on `--surface-hover` (item hover) | 11.13:1 | 4.5:1 | pass |
| `--text` on `--yellow-dim` (current item) | 7.46:1 | 4.5:1 | pass |
| `--yellow` bar on `--yellow-dim` (current item) | 5.22:1 | 3:1 | pass |
| `--yellow` focus ring on `--surface-raised` | 8.58:1 | 3:1 | pass |
| `--yellow` focus ring on `--chrome` | 9.98:1 | 3:1 | pass |
| `--red-text` `#ff5148` on `--surface-raised` | 4.43:1 | 4.5:1 | **fail, rejected** |
| `--red-text` `#ff5148` on `--surface-hover` | 4.02:1 | 4.5:1 | **fail, rejected** |

Two honest limits. The toggle's 1px `--border` edge is only 1.51:1 against `--chrome`, and the
panel border is 1.94:1 against its fill. Neither boundary is what identifies the control: the
gear glyph (8.27:1) and the item text (12.26:1) do, so WCAG 1.4.11 is met by the content, not by
the edges. These are recorded rather than hidden.

### 7.4 Typography

| Element | Family | Size / line-height | Weight | Case and tracking | Notes |
|---|---|---|---|---|---|
| Menu item label | IBM Plex Sans (`--body`) | 13px / 1.4 | 400 | sentence case, no tracking | Matches rail items (`nav button`, 13px). Weight stays 400 in every state so the current item does not shift layout. |
| Toggle | none; SVG glyph | 20×20 glyph in a 44×44 control | stroke 1.75 | — | No text node. |
| Tagline (unchanged) | IBM Plex Sans | 12px | 400 | uppercase as authored, `.025em` | `--muted`. |
| Header title (unchanged) | Barlow Condensed (`--display`) | 29px / .95 (24px at ≤620px) | 700 | uppercase, `.025em` | The only display type near this feature. |
| IBM Plex Mono | not used | — | — | — | Nothing in this menu is technical metadata. |

Labels: **Settings**, **Log out**. Toggle name: **Settings and account**.

### 7.5 Dimensions and layering

| Property | Value |
|---|---|
| Toggle | 44×44px, 4px radius, 20×20 glyph |
| Panel | min-width 176px, max-width `calc(100vw - 30px)`, 4px padding, `--radius` (6px) corner |
| Panel offset | 8px below the toggle, right-aligned |
| Item | min-height 44px, `padding: 10px 14px`, 3px radius |
| Separator | 1px, `margin: 4px 0` |
| Tool-group gap | 20px between tagline and toggle |
| Stacking | panel lives inside the header (z 20): above the rail (15), below the skip link and modal (100) and toasts (200) |
| Motion | 150ms opacity and `translateY(-4px → 0)` on open; instant close; none under `prefers-reduced-motion` |

## 8. Behavior and accessibility

**Markup.**

```html
<div class="header-tools">
  <p>LISTENING INTELLIGENCE · DISCOVERY INDEX</p>
  <div class="header-menu">
    <button id="appMenuButton" class="header-menu-toggle" type="button"
            aria-label="Settings and account" title="Settings and account"
            aria-expanded="false" aria-controls="appMenu">
      <svg …gear… aria-hidden="true" focusable="false"></svg>
    </button>
    <div id="appMenu" class="header-menu-panel" hidden>
      <button type="button" data-page="settings">Settings</button>
      <div class="header-menu-separator" role="separator"></div>
      <button type="button" id="logoutButton">Log out</button>
    </div>
  </div>
</div>
```

`id="logoutButton"` is kept so the existing logout handler binds unchanged, and
`data-page="settings"` is kept so page switching keeps its single source of truth.

**Pointer.** Click the toggle to open or close. Click or tap anywhere outside `.header-menu`
closes it. Choosing Settings closes the menu and shows the page.

**Keyboard.**

| Key | Behavior |
|---|---|
| Enter / Space on toggle | open or close (native button) |
| ArrowDown on toggle | open and focus the first item (enhancement) |
| ArrowDown / ArrowUp in panel | move between items, wrapping (enhancement) |
| Home / End in panel | first / last item (enhancement) |
| Escape | close and **return focus to the toggle** |
| Tab / Shift+Tab | moves through items naturally; leaving the container closes it |

**Focus after choosing Settings.** Focus returns to the toggle, because the focused item is
hidden by closing. This matches the rail, which does not move focus to the new page. Moving focus
to the Settings heading would be better for screen readers but would diverge from every other
navigation in the app; it is listed as an open decision (§12).

**Safari caveat, designed in.** Safari does not focus a `<button>` on click, so a `focusout`
handler that closes the menu whenever `relatedTarget` is `null` would close the panel on
mousedown and swallow the click on the item. The rule is therefore: close on `focusout` only when
`relatedTarget` is a **non-null element outside** the container; pointer dismissal is handled by
the document click listener instead.

**Semantics.** The Settings item gets `aria-current="page"` when Settings is the active page;
`syncNavAria()` is extended to cover it. The toggle's name does not change.

**Logout hardening (small, in scope).** While the request is in flight the item is disabled and
`aria-busy="true"`, preventing duplicate submission (`AGENTS.md` asks for this where
appropriate). The request, the `finally`, and the redirect are unchanged.

## 9. Implementation plan

Branch `ui/header-settings-menu` from current `main`. Three allowed files plus one test.

### 9.1 `app/templates/index.html`

1. Wrap the header tagline and the new toggle in `.header-tools` (markup in §8).
2. Delete lines 50-51 (the rail's Settings and Log out buttons). The panel owns both now.
3. **Move the skip link above `<header>`.** In the DOM the header (line 13) precedes the skip
   link (line 18). Today the header has nothing focusable, so the skip link is the first tab
   stop (PR #192). The gear would take that place and break it. The skip link is
   `position: fixed`, so moving it in the source changes tab order, not appearance. Update the
   comment on it ("First stop in the tab order") only if the wording stops being true.
4. Update the comment above `<nav>` only if it mentions the removed buttons (it does not).

### 9.2 `static/app.css`

1. Add `--shadow-menu` to `:root`.
2. `.header-tools` flex group; keep the existing `header p` rules.
3. `.header-menu` (`position: relative`), `.header-menu-toggle` (44×44, `padding: 0`, grid-centered
   glyph, `color: var(--text-chip)`), its hover/expanded/current rules, and `.header-menu-panel`
   plus its item, current-item, separator and open-animation rules.
4. Item focus uses `outline-offset: -2px`.
5. At ≤620px: the toggle stays 44×44; the header's `padding: 12px 15px` already leaves room; the
   panel keeps `max-width: calc(100vw - 30px)`. No extra override is expected.
6. Add `.header-menu-panel { animation: none; }` to a `prefers-reduced-motion` block. Nothing
   waits on `animationend`, so switching it off is safe (same reasoning as the Get button block).
7. Remove no existing rule. The rail's `nav button` rules still apply to Acquisitions and the
   six discovery items. Check that nothing styled `nav button[data-page="settings"]` specially
   (none was found).

### 9.3 `static/app.js`

1. Extend the three `nav button[data-page]` selectors (in `showPage`, `syncNavAria`, and the click
   binding) to also match `.header-menu button[data-page]`.
2. Factor the click body into one function so the rail and the menu cannot drift:
   `showPage(name); initializePage(name); if (name !== 'acquisitions') stopAcquisitionStream();`
   **Settings must still run `initializePage('settings')`**, or the panels load empty.
3. In `showPage`, toggle `.is-current` on the toggle when `name === 'settings'`.
4. Add open/close helpers, the toggle click, the outside-click listener, the container-scoped
   `focusout` rule (§8), and the arrow/Home/End handling. Extend the existing document `keydown`
   at `app.js:671` for Escape, checking the album modal first so Escape still closes the modal.
5. Logout: add the disabled and `aria-busy` guard around the existing handler. Leave the fetch
   and `window.location.replace('/login')` untouched.

### 9.4 Not touched

`app/main.py`, `app/api/**`, `app/security/**`, every backend module, `static/login.*`,
`docs/**` other than `docs/UI_BACKLOG_EXECUTION.md`.

## 10. Tests and verification

### 10.1 New source-contract test

`tests/test_header_menu_ui_contract.py`, in the style of the existing `*_ui_contract` modules
(read the shipped assets, assert on source, no browser). It should assert:

1. The rail no longer contains Settings or Log out buttons; the header menu contains both.
2. `id="logoutButton"` exists exactly once and is inside `.header-menu-panel`.
3. The toggle has `aria-expanded="false"`, `aria-controls` resolving to the panel id, an
   `aria-label`, and an `<svg>` marked `aria-hidden="true"`.
4. The panel is `hidden` in the shipped markup.
5. Document ids stay unique, and every `$('id')` in `app.js` still resolves to a template id.
6. The page-switch binding covers `.header-menu button[data-page]` **and** the shared handler
   still calls `initializePage` and `stopAcquisitionStream` (guards the empty-Settings regression).
7. `showPage` and `syncNavAria` both include the menu selector.
8. The logout handler still contains `/api/auth/logout` and `window.location.replace('/login')`.
9. `app.js` contains an Escape branch for the menu and the album-modal Escape branch remains.
10. The `focusout` rule requires a non-null `relatedTarget` (Safari guard).
11. `app.css` defines the panel, the current state, the inset item focus offset, a
    `prefers-reduced-motion` rule for the panel, and `--shadow-menu`; no new hex literal is added.
12. The skip link appears in the source before `<header>`, so it stays the first tab stop.

Run the new tests against the pre-change files and confirm they fail, as PR #215 did, so they are
shown to be a real guard.

### 10.2 Commands

```sh
node --check static/app.js
python -m compileall app static
python -m unittest tests.test_header_menu_ui_contract -v
python -m unittest discover -s tests -v
```

`<impeccable-skill-dir>/scripts/impeccable detect --json static/app.css app/templates/index.html static/app.js`
runs the mechanical detector once the UI is finished. Compare the finding set with `main`; do not
treat detector output as a mandate.

### 10.3 Manual browser gate (required, per `AGENTS.md`)

After CI passes on the exact PR head, run `docs/LOCAL_UI_TESTING.md` with sandbox paths and slskd
disabled. Specific to this change:

- Open and close by click, by keyboard, by outside click, and by Escape; focus returns to the toggle.
- Settings from the menu loads all four panels (not empty); Log out ends the session and lands on `/login`.
- On Settings: gear shows the current cue, the rail has no active item and the blob is hidden, and
  navigating away restores the blob without a stray slide.
- Widths 1440, 1200, 900, 620, 390, 360px: no horizontal overflow, panel fully on screen, toggle ≥44×44.
- With the album modal open, the menu is not above it.
- Tab order: the **skip link is still the first stop**, then the gear, then the rail, then page
  content. Record the order actually observed and confirm it is logical.
- `prefers-reduced-motion`: no open animation.
- Safari: click an item with the menu open. Record as a **skip** if Safari is not available.
- Console and network clean; only `POST /api/auth/logout` fires on Log out.

State, as `AGENTS.md` requires: implemented, automated-tested, browser-tested, merged, published,
deployed and runtime-verified are separate. Chromium-only and no real screen reader means those are
skips, not passes.

## 11. Impeccable guidance

Context: `impeccable context` found no `PRODUCT.md` and no `DESIGN.md`; the incumbent CSS and
templates were treated as design authority, which the tool permits for a scoped refinement.
`/impeccable init` was **not** run, because it writes a root `PRODUCT.md` outside the allowed
paths. Recommended as a follow-up for the operator to approve.

**Applied** (`shape.md`, `operate.md`):

- Operate mode: earned familiarity over invention; a top-right gear and a dropdown is the pattern
  a category-fluent user already trusts.
- Accent for hover, expanded, current and focus only; never decoration.
- A state-complete component: rest, hover, focus, active, expanded, current, loading.
- Overlays must escape their container: the panel is a child of the fixed, non-clipping header.
- Motion conveys state only, 150-250ms range, no choreography.
- No display font in labels; one family carries the control.
- Brief structure from `shape.md` (job, direction, scope, states, constraints, open decisions),
  with assumptions marked because no interview round was run.

**Rejected, with reasons:**

- Modal or scrim treatment: `operate.md` calls modal-as-first-thought a smell, and two items do
  not warrant it.
- Red Log out: not destructive, and `--red-text` fails 4.5:1 on the panel (§6.2).
- Icons beside items, avatar or user chip, badge on the gear: unneeded, and an avatar would need a
  backend field that does not exist.
- Full `role="menu"`: wrong semantic for navigation (§6.1).
- A bounce or spring on open: the rail's spring was flagged advisory-only by the external critique;
  not repeated here.

## 12. Open decisions and risks

Decisions for the operator (defaults in bold):

1. Toggle name: **"Settings and account"**, or shorter "Settings".
2. After choosing Settings, focus goes to **the toggle**, or to the Settings heading.
3. Should Log out ever ask for confirmation: **no**, matching current behavior.
4. Later: should Acquisitions join the menu? Not in this change.

Risks, each with its guard:

| Risk | Guard |
|---|---|
| Settings opens empty because the menu bypassed `initializePage` | shared handler plus contract test 6 |
| Safari swallows the item click | `focusout` rule in §8 plus contract test 10 and the manual Safari check |
| No "you are here" on the Settings page | toggle current state (§6.3) |
| Blob animates oddly when returning from Settings | verify manually; `moveNavBlob()` already hides it without an active item |
| Menu hidden or clipped at 360px | right-aligned, `max-width: calc(100vw - 30px)`, checked at all widths |
| Escape closes the wrong layer | modal checked first in the shared `keydown` |
| The gear becomes the first tab stop and displaces the skip link, because the header precedes it in the DOM | move the skip link above `<header>` (§9.1) plus contract test 12 and the manual tab-order check |
| Pre-existing: rail label "YOUR COLLECTION" sits above Recommendations and Classics, which are outside the collection | recorded in `UI_BACKLOG_EXECUTION.md` §4a; **not** fixed here |

## 13. Acceptance criteria for the implementation PR

- Settings and Log out are absent from the rail and reachable from a gear at the top right.
- The gear is a 44×44 named, keyboard-operable disclosure; the panel opens, closes, and returns focus as specified.
- Settings still loads its panels; Log out still posts to `/api/auth/logout` and redirects to `/login`.
- Only existing color tokens are used; one non-color token is added; no new hex literal.
- No API, auth, cookie, backend, or acquisition behavior changes; the diff touches only the allowed files and one new test.
- Contract tests pass on the branch and fail on the pre-change files; the full unit suite and the four required CI workflows pass on the exact head.
- The manual gate in §10.3 is recorded against the exact head SHA, with skips marked as skips.
- `docs/UI_BACKLOG_EXECUTION.md` is updated in the same PR.
- The PR body lists Impeccable guidance applied and rejected, with before and after screenshots.
