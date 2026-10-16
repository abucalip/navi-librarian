# UI backlog execution — Session 0 baseline

Last updated: 2026-10-15
Owner: ZCode (front-end implementation, per root `AGENTS.md`)
Scope of this file: session-bootstrap reference. It records the verified state of the
front-end at a known `main` SHA so later sessions do not re-read the full project
documentation set.

This file does not replace root `AGENTS.md` or `docs/FRONTEND_DESIGN_GUIDE.md`; those
remain authoritative. It only compresses the parts a front-end session needs.

## 1. Baseline this file was written against

- GitHub `main` at `4098361` — "docs: close out direct-import test migration (#119)".
- Highest PR number in the repository at time of writing: **#119**. New branches/PRs
  should be assumed to land at **#120 or later**; confirm with `gh pr list` before opening.
- No front-end file has been changed by this session. No implementation work has been
  performed or verified. This is a documentation-only baseline.

## 2. Authorized front-end surface (verbatim scope from `AGENTS.md`)

| File | Lines at baseline | Notes |
|---|---|---|
| `static/app.css` | 189 | single stylesheet, token block at top |
| `static/app.js` | 1471 | single script, all client behavior |
| `static/login.css` | 47 | login page only |
| `static/login.js` | 5 | login page only |
| `app/templates/index.html` | 213 | all app pages, one file |
| `app/templates/login.html` | (not measured) | login page |

Narrowly scoped front-end tests/fixtures under `tests/` are also permitted.

**There are currently no front-end/UI test files in `tests/`.** All 34 files there are
backend or domain tests (acquisition, discovery, routes, auth). Any UI test added becomes
a new file in that directory; follow the existing pytest conventions there.

Protected paths (never edit without explicit approval): `app/main.py`, `app/api/**`,
`app/security/**`, `navidrome_server.py`, domain/acquisition/persistence modules,
`Dockerfile*`, Compose files, `.github/workflows/**`, dependency and lockfiles, and any
requirements/architecture/test-gate/deployment policy.

## 3. Verified front-end architecture facts

These were read from source at the baseline SHA. Later sessions can trust them instead
of re-deriving them.

- **Serving:** `app/main.py:47` mounts `static/` at `/static`; `app/main.py:120` treats
  `/static/` and `/assets/cassette.png` as public assets. Templates are rendered from
  `app/templates/` (`app/main.py:46`).
- **Single-page shell:** `index.html` holds every page as a `<section class="page">`,
  toggled by a `hidden` class. Pages: `dashboard`, `recommendations`, `newReleases`,
  `personalDiscoveries`, `classics`, `artistDeepDive`, `settings`, `acquisitions`.
  There is no router and no framework; all behavior is in `static/app.js`.
- **Design tokens** are defined once in `static/app.css:2-8` as CSS custom properties:
  `--bg`, `--surface`, `--surface-raised`, `--surface-hover`, `--border`, `--text`,
  `--muted`, `--subtle`, `--yellow`, `--yellow-dim`, `--red`, `--green`, `--radius`,
  plus font stacks `--display` (Barlow Condensed), `--body` (IBM Plex Sans),
  `--mono` (IBM Plex Mono).
- **Fonts are loaded from Google Fonts** via `@import` at `static/app.css:1`. This is an
  existing external asset dependency; do not add further ones.
- **Layout:** fixed `header` (min-height 82px) and fixed left `nav` (220px) with
  `main` offset by `margin: 112px 34px 0 254px`. Breakpoints exist at 1200, 1100, 900,
  760, 650, 620, and 360 px, plus a `prefers-reduced-motion` block.
- **Card grid:** `.cards` is `repeat(4, minmax(0,1fr))`, degrading to 3/2/1 columns at
  narrower widths. `.cards.deep-dive-rows` switches to a flex column for genre rows.
- **Existing status/empty-state mechanism:** each discovery section has a paired
  `[cardsContainer, statusElement]` entry in the `discoveryViews` map at
  `static/app.js:860-863`, and `discoveryStatus(name, message)` at `static/app.js:877`
  writes plain text into the status element.
- **Existing empty-state pattern to mirror:** `static/app.js:1104-1105` appends a plain
  `<p>` with text "No results. Try refreshing this list." into the cards container.
  `static/app.js:822-828` does the same for filtered recommendations.

## 4. Backlog state

From `docs/FRONTEND_DESIGN_GUIDE.md` section 8.

**Completed:**

- Login-page alignment (PR #66). The guide marks this closed and says not to reopen it
  without new evidence. Its verification recorded keyboard focus modality and the
  first-run setup variant as **skips, not passes**.
- **Navigation rail redesign** (not a numbered backlog item; requested directly) — on
  branch `ui/nav-blob`. The sidebar active state is now a sliding indicator driven by
  `translateY`, adapted from the Forever Components `navigation/gooey-tab-bar`. The blob
  covers the seven content items; Acquisitions and Settings are intended to move elsewhere
  later, as is Log out. See section 5b for the technique and the two failures encountered.
- **State craft** (item 1) — implemented in PR #121 on branch `ui/state-craft`. A shared
  `.status-line` treatment now covers every status element, with `aria-live` on all of
  them and a per-state leading glyph so state is never carried by colour alone. See
  section 5 for the before/after measurements.
- **Per-section layouts** (item 2) — started in PR #128 on branch `ui/acquisition-layout`.
  Scoped to one section per PR, as `AGENTS.md` requires. The acquisition section moved off
  the shared four-column artwork grid onto a wider status-board layout. Other sections are
  deliberately unchanged; the remaining sections in this item are still open.
- **Get/request button consolidation** (item 3) — implemented on branch
  `ui/get-request-consolidation`. The modal, artwork-overlay and card-action variants now
  share one `.get-album` base, three duplicated creation sites collapsed into one
  `createGetButton()` helper, and the control gained an explicit state machine. Three real
  defects were fixed as part of the work; see section 5a.

**Remaining, in the guide's priority order:**

1. ~~**State craft**~~ — done in PR #121.
2. **Per-section layouts** — in progress. Acquisition done in PR #128. Still to consider:
   artist exploration, library, and settings. The guide's instruction is "do not force
   every page into the same dashboard grid"; six sections still share one grid, so the
   candidates are the discovery sections and settings rather than acquisition again.
3. ~~**Get/request button consolidation**~~ — done, merged (PR #131).
4. **Type/token cleanup** — consolidate duplicated values into shared tokens and tighten
   the type scale without broad visual churn.
5. **Responsive controls** — improve navigation, filters, and acquisition cards at narrow
   viewport widths.
6. **Continue visual audit** — re-prioritize based on evidence after the above.

**Contrast fix (C1 of the external critique, see PR #141).** The `--subtle` token was raised
from `#77796f` to `#94958b` on branch `fix/subtle-contrast`. The critique recommended
approximately `#8a8b81`; that clears AA on three of the four backgrounds `--subtle` renders
on but leaves only 4.53:1 on `--surface`, so a value with real margin was chosen instead.
See section 5c.


### Priorities from the Claude critique (see section 4a)

An external design critique scored the UI 17/36 and ranked its findings. The following
supersedes the order above where they disagree, because these are evidence-backed and
their claims were re-verified against `main` at `30e7c04`.

| # | Action | Effort | Status |
|---|---|---|---|
| C1 | **Fix `--subtle` contrast.** It fails WCAG AA at 3.94:1 and is used on functional metadata. | One token | Verified, not fixed |
| C2 | **Add `aria-label` to `<nav>`; give page sections accessible names.** | Small | Verified, not fixed |
| C3 | **Set the modal artwork `alt` dynamically.** It is hardcoded and never updated. | Small | Verified, not fixed |
| C4 | **Fix `#recommendationCount`.** 11px mono on an `aria-live` region users must read. | One rule | Implemented in refreshed PR #149; four workflows passed on head `084aebb`; refreshed-head browser verification pending |
| C5 | **Move `<footer>` out of `<main>`.** It sits mid-document before five sections. | One line | Verified, not fixed |
| C6 | **Differentiate Artist Deep Dive.** The critique's single highest-leverage move. | Item 2 | Not started |
| C7 | **Write per-section empty-state copy.** Three cases per section: loading, empty-success, error. | Copy work | Item 1, partial |

C1–C5 are all small and independently verifiable. C6 is the rest of backlog item 2.

## 4a. External critique findings

Source: `Claude critique.docx` in the operator's project folder (not a repository file).
Method: dual-agent review — a design assessment plus a deterministic detector scan — then
synthesis. Scored **17/36** across ten usability heuristics. Its verdict: "competent first
pass rather than a finished specialist tool."

### Verification of its claims

The critique was written against an earlier `main`. Every claim below was re-checked against
`main` at `30e7c04` before being recorded as a priority. Measured, not assumed:

| Claim | Result |
|---|---|
| `--subtle` (#77796f) fails WCAG AA | **Confirmed.** 3.94:1 on `--bg`, 3.53:1 on `--surface`. AA needs 4.5:1. |
| `--subtle` is used on functional metadata | **Confirmed.** 7 uses, including the `.status-line` state glyph, track numbers and durations, and `genre-row-count`. |
| `<nav>` has no `aria-label` | **Confirmed.** `index.html:16` is a bare `<nav>`. |
| Modal `alt` is static, never updated | **Confirmed.** `alt="Album artwork"` in markup; `static/app.js` never assigns `.alt` on it. |
| `#recommendationCount` is 11px mono | **Confirmed.** `app.css:118`. |
| `<footer>` sits mid-`<main>` | **Confirmed.** `<main>` opens at line 15, `<footer>` at 114, `</main>` at 215. |
| Six sections share one grid | **Confirmed.** Five use bare `.cards`; only `#acquisitionCards` was differentiated (PR #128). |

One critique claim was already resolved by the time it would have been acted on: the
"bounce-easing advisory on the nav blob" refers to my `ui/nav-blob` work, which was merged as
PR #132 with a spring easing the critique flagged as advisory only.

Its contrast remedy was directionally right but understated: it suggested ~4.6:1. Measured,
`#8a8b81` gives **5.06:1** on `--bg`. Use the measured value.

It also flagged `#saveNavidrome` / `#saveSlskd` (dark on yellow) as needing verification.
Measured: **10.5:1**, comfortably passing. No change needed.

### Endorsed, and the reasoning worth keeping

- **"Layout that serves the task rather than defaulting to a universal grid."** This is the
  same principle as the design guide's "do not force every page into the same dashboard
  grid", stated from the other direction. It is why item 2 exists.
- **The status glyph system only works if the glyphs are visible.** The critique noticed
  that the `.status-line` prefix, added in PR #121 specifically for accessibility, is painted
  in the one token that fails contrast. That is a real self-inflicted contradiction and makes
  C1 more than a token tidy-up.
- **"Copy is the deliverable, not a component"** (on empty states). Worth carrying into C7.
- **Its highest-leverage recommendation is Artist Deep Dive first**, because that section's
  content type (one album per artist, grouped by genre) is the most obviously ill-served by a
  flat album grid. This matches the design guide's backlog order and my own reading, arrived
  at independently.

### Treated with caution

Recorded so later sessions apply judgement rather than treating the critique as a mandate.

- **The 17/36 score is not a metric.** It is one model's subjective scoring of ten
  heuristics with no calibration, and the critique says so itself in places. Do not report it
  as a tracked number or try to raise it.
- **Two of its seven detector findings are self-declared false positives or debatable**, and
  it says so: the missing modal `src` (populated at runtime) and the `.card-art` bottom
  stripe (a hover animation, not a border badge).
- **"Visual overlays: browser automation was not available"** — it did its review from
  source and a CLI scan, without rendering the UI. Findings that depend on rendered
  appearance are therefore weaker than its measured contrast and structural claims. This is
  exactly the gap the local headless verifier now covers; findings that matter should be
  confirmed by rendering.
- **It praises things I know to be recent or fragile.** It credits the "sliding nav blob" as
  evidence of authored craft, and that landed days earlier in PR #132. Praise for
  freshly-merged work is not independent corroboration of it.
- **Its heuristics 9 and 10 scored 1 and n/a.** "Help users recover from errors: 1" is
  doing a lot of work in the total. Treat the low scores as directional, not precise.

### What it got right that is easy to miss

- The **`.card-category` 2px yellow left border** technically brushes the guide's anti-pattern
  about card borders. Its judgement that this is a *tag*, not a card, and that the 2px is what
  makes it legible, is sound. Leave it, but acknowledge it consciously.
- The **`nav::before` "YOUR COLLECTION"** label is misleading above Recommendations and
  Classics, which are outside the collection. A real copy problem, not a nitpick.

## 5a. Item 3 findings

Three defects found while consolidating the get/request control. All three were live on
`main`.

1. **Acquisition outcomes were silently discarded.** `searchAlbum()` wrote success and error
   messages to `document.querySelector('.page:not(.hidden) .status')`. After the state-craft
   work no status element carries the bare `status` class except `#connection`, which lives
   inside the Settings section, so on every discovery page that selector matched **nothing**.
   A user who requested an album saw no confirmation and no error. Measured: `matches=0` on
   dashboard, recommendations, classics, artistDeepDive and acquisitions; `matches=1` only
   on settings.
2. **Success was claimed before the server confirmed.** The control was set to `'requested'`
   *before* awaiting `/api/acquire`. `AGENTS.md` requires not reporting success until the
   server confirms, especially for acquisition actions. There was also no pending state, so
   the button asserted an outcome it could not yet know.
3. **A 200 response with `ok: false` was treated as success.** `/api/acquire` can answer
   HTTP 200 with `{"ok": false, "message": "..."}` — for example when no slskd API key is
   configured. Any 2xx was treated as a completed request.

Measured while driving the real helper against a live instance with no slskd key configured,
which exercises the `ok: false` path:

| Observation | `main` | branch |
|---|---|---|
| Message reaches a visible status region | **no** (selector matched nothing) | **yes** — the section's own status region, given an error state |
| Button claims `requested` for a request never placed | **yes** | **no** — shows `retry` with a failed state |
| Pending state while in flight | absent | `…` label, `disabled`, `aria-busy="true"` |
| Aria label reflects the real state | only on success/error | on every state, including pending |
| Distinct `.get-album` CSS declarations | 3 near-duplicate blocks | 1 shared base plus per-variant geometry |
| JS creation sites repeating label/title/aria | 3 manual copies | 1 `createGetButton()` helper |

Verified on the branch: all three variants resolve to identical computed style
(`borderRadius`, `backgroundColor`, `borderColor`, `fontFamily`, `textTransform`); the
control is reachable by Tab with a visible 2px focus outline; 8/8 pages render their
expected heading; zero horizontal overflow at 1440/1200/1100/900/760/620/390/360px; and no
console or page errors.

**Correction — a withdrawn finding.** An earlier revision of this file, and the
`PROJECT_STATUS.md` / `PROJECT_LOG.md` entries derived from it, claimed a keyboard-focus
reach defect: "25 Tab presses reached only three dashboard controls." **That claim was
wrong and is withdrawn.** It was a measurement artifact, not a defect. See section 5.

The real, smaller gap found on re-inspection is that the settings tab widget implements
`role="tab"` and `role="tabpanel"` without `aria-controls`, `aria-labelledby`, or roving
`tabindex`, which is the ARIA tabs pattern only half-applied. That is genuine but minor
and is not a focus-reach defect.

## 5b. Navigation rail findings

Adapted from Forever Components `navigation/gooey-tab-bar`
(`https://forevercomponents.com/infinite/navigation/03-gooey-tab-bar.html`).

### What was taken

Only the technique: a pill that slides between items with a spring easing, combined with an
SVG `feGaussianBlur` + `feColorMatrix` goo filter for a liquid merge. **No component code or
styling was copied.** The reference ships its own palette (`#E04729` vermillion) and tokens;
the project's own tokens are used throughout.

Adapted for a vertical rail: the reference is horizontal, so the blob animates `translateY`,
and it is height-locked to a nav row so no width term is needed.

### Two failures, and what they teach

Both were found by rendering the result, not by reading the code.

1. **The goo filter erased every navigation label.** Applying `filter: url(#nav-goo)` to the
   list containing the buttons blurred all seven labels into illegibility. The filter's final
   `feComposite operator="atop"` keeps source pixels only where the goo is opaque, so text
   outside the blob's area is discarded outright.

   The reference escapes this only because all of its tabs sit *inside* one pill, so the goo
   is opaque across the whole control. With one blob behind one row out of seven, six labels
   vanished.

   **Fix:** apply the filter to `.nav-blob-layer`, an absolutely positioned overlay holding
   the blob and nothing else. Labels live outside it.

2. **A missing filter primitive produced an unreadable smear.** The first attempt omitted
   `feComposite in="SourceGraphic" in2="nav-goo" operator="atop"`, leaving the blur applied
   to the whole nav. This primitive is not optional decoration; it is what restores the sharp
   original over the goo.

### Deviations from the reference, and why

| Reference behaviour | What this branch does | Reason |
|---|---|---|
| Auto-cycles tabs every 1700ms as a demo | No auto-cycle | Its own `knownLimitations` says to remove the `loop()` call before production. Unsolicited motion in a library tool is the decorative noise the design guide prohibits. |
| No `aria-selected` or `role=tablist` | `aria-current="page"` on the active item | Its own `knownLimitations` flags the missing ARIA. This is a navigation landmark, not a tab widget, so `aria-current` is the correct semantic. |
| `translateX`, width-matched blob | `translateY`, height-locked blob | The rail is vertical. Height is fixed at 40px, so neither width nor height is animated. |
| Any number of tabs | Blob on the 7 content items only | Its own `avoidWhen` warns that blob sizing breaks past 4-5 tabs. Acquisitions and Settings sit outside `.nav-list` and keep the flat treatment. |
| Horizontal at every width | Vertical rail to 620px, then the blob is removed and a flat underline returns | Below 620px the nav becomes a horizontal scroller, so a vertical blob would point the wrong way. |

### Verification

Measured on the branch: the blob aligns to the active row within 1px on all seven content
items; the transition animates `transform` only, never `top` or `height`; exactly one element
carries `aria-current="page"`; the goo filter applies to `.nav-blob-layer` and not to `nav`;
the blob is `display: none` below 620px; `prefers-reduced-motion` reduces the transition to
`1e-05s`; all eight navigation items are reachable by Tab with a visible focus ring; 8/8
pages render their expected heading; zero horizontal overflow at
1440/1200/1100/900/760/620/390/360px; and no console or page errors.

## 5c. Contrast findings (`--subtle`)

Measured on the running app, reading the real composited background behind each use rather
than assuming `--bg`.

### Three live failures, all on `--subtle`

| Use | Background | Before | After |
|---|---|---|---|
| `nav::before` "YOUR COLLECTION" label | `#1d1f1e` | **3.75:1 FAIL** | 5.47:1 |
| `footer` notice | `#191a1a` | **3.94:1 FAIL** | 5.76:1 |
| `.status-line.is-loading` glyph `…` | `#191a1a` | **3.94:1 FAIL** | 5.76:1 |
| `.status-line.is-empty` glyph `—` | `#191a1a` | **3.94:1 FAIL** | 5.76:1 |
| `.genre-row-count`, track numbers | page / modal | fail | pass |

WCAG AA requires 4.5:1 for normal text.

**Two of the failures were glyphs added in PR #121 specifically for accessibility.** That
work introduced a state vocabulary carried by a leading glyph; two of the five glyphs were
painted in the one token that failed contrast. An accessibility affordance that cannot be
seen does not do its job. All five glyphs now pass: loading 5.76:1, empty 5.76:1, error
4.8:1 (uses `--red`, unchanged, pre-existing), success 9.23:1, progress 10.5:1.

### Why `#94958b` rather than the suggested `#8a8b81`

Only four backgrounds actually matter, because `--subtle` is never used on `--surface-raised`
or `--surface-hover`:

| Candidate | nav `#1d1f1e` | page `#191a1a` | modal `#202221` | card `#222424` | worst |
|---|---|---|---|---|---|
| `#77796f` (before) | 3.75 | 3.94 | 3.62 | 3.53 | **3.53** |
| `#8a8b81` (suggested) | 4.81 | 5.06 | 4.64 | 4.53 | 4.53 (no margin) |
| **`#94958b` (chosen)** | 5.47 | 5.76 | 5.28 | 5.15 | **5.15** |

The lighter value keeps `--subtle` measurably quieter than `--muted` (`#a5a69c`, 7.09:1 on
`--bg`), so the three-tier text hierarchy survives: subtle 5.76, muted 7.09, text 15.01.

Also verified: the two save buttons flagged as unverified by the critique measure 10.5:1
(dark on `--yellow`) and need no change.

## 5d. Landmark naming findings

C2 of the external critique: add `aria-label` to `<nav>` and give page sections accessible
names. Audited with Playwright's ARIA snapshot, which reports what assistive technology
actually receives rather than what the markup implies.

### Before

The landmark tree rendered as three bare, unnamed entries:

```
- banner:
- main:
  - navigation:
```

| Element | Unnamed, before |
|---|---|
| `<nav>` | 1 of 2 — the sidebar had no name; the modal's links did |
| `<section class="page">` | **8 of 8** |
| `<section>` overall | 8 of 9 — only the album modal was named |

A `<section>` only becomes a `region` landmark when it has an accessible name. So the eight
page sections were **not landmarks at all**: a screen-reader user could not jump between pages
by region, and each announced as an anonymous group.

### After

```
- banner:
- main:
  - navigation "Main":
  - region "Ten from the collection":
```

- `<nav>` sidebar: `aria-label="Main"`, so the two nav landmarks are distinguishable.
- All 8 page sections: `aria-labelledby` pointing at their own `<h2>`, so all 8 are now
  `region` landmarks. Measured **9 of 9** named, up from 1 of 9.
- Each section has a unique name; checked for duplicates.

### Why `aria-labelledby` rather than `aria-label`

The critique suggested accessible names; `aria-labelledby` pointing at the existing visible
heading is the better mechanism because the name **cannot drift from the visible text**. A
hardcoded `aria-label="Settings"` would silently disagree with the `<h2>` the moment anyone
rewords the heading. This required adding ids to the eight `<h2>` elements; all nine
`aria-labelledby` references were verified to resolve to an existing id.

### Deliberately NOT labelled

The critique named only `<nav>` and the sections. `banner`, `main` and `contentinfo` are left
unlabelled on purpose: **a landmark type that appears once is unambiguous by role alone**, so
a label there is noise. Labels are needed only where a type repeats, which is why both `<nav>`
elements have one.

This means the audit's `UNNAMED` result for `<header>`, `<main>` and `<footer>` is **not a
defect**, and should not be "fixed" by a later session.

### Verification

Measured on the branch: the landmark tree shows `navigation "Main"` and named regions; all 9
sections named; the visible region on each of the 8 pages resolves to its expected heading
name; no two sections share a name; 79 ids with zero duplicates; zero horizontal overflow at
1440/1200/1100/900/760/620/390/360px; no console or page errors.

## 5e. Modal artwork and nav label findings

C3 of the external critique: set the modal artwork `alt` dynamically. Auditing it surfaced a
second, unrelated defect in the same dialog.

### Defect 1 — the modal image never described its own album

The `<img>` carried a hardcoded `alt="Album artwork"` that was never updated. The ARIA tree
for an open modal read:

```
- dialog "Bitches Brew":
  - img "Album artwork"
```

The name is identical for every album, so it conveys nothing. `audit.md` lists "Alt text:
Missing or poor image descriptions", and `clarify.md:74` gives the rule: "Make alt text convey
the image's information; use empty alt for decoration."

**Fixed:** the description is set on open — `Album artwork for <album> by <artist>` — and
cleared to an empty `alt` when no artwork resolves, since an `<img>` with an alt but no source
is announced as a broken image.

The card artwork deliberately keeps `alt=""`. Each card already carries its own heading, so a
per-image description there would duplicate the announcement. The modal image is different: it
is a distinct larger depiction and the first content a user meets when the dialog opens. This
distinction is recorded as a comment in `static/app.js` so the two are not "made consistent"
later.

### Defect 2 — the sidebar's label leaked into the modal's navigation

`nav::before { content: "YOUR COLLECTION" }` was **unscoped**, so it matched both `<nav>`
elements. The album modal's platform-links navigation rendered the sidebar's heading above its
icon links, and the accessible name of that region was polluted:

```
- navigation "Find this album on music services": YOUR COLLECTION
```

Measured before: the modal nav's `::before` computed to `"YOUR COLLECTION"`. After scoping the
rule to `main > nav`, it computes to `none` and the region exposes its platform links directly.

A comment in `static/app.css` records why the selector is scoped, because the unscoped form
looks more natural and would be an easy regression.

### Verification

Measured on the branch: with artwork present the image is announced as "Album artwork for
Bitches Brew by Miles Davis"; with no artwork the alt is empty and no broken image is exposed;
the modal nav's pseudo-element is `none` while the sidebar's is `"YOUR COLLECTION"`; the modal
region now lists its link children instead of the leaked heading; 8/8 pages render their
expected heading; zero horizontal overflow at 1440/1200/1100/900/760/620/390/360px; no console
or page errors.

## 5f. recommendationCount findings

C4 of the external critique. Measured before changing anything.

### What the element is

It holds two different kinds of text, which matters for the fix:

- Initial: an instructional sentence, "Generate recommendations to get started."
- After generating: `"Showing 12 of 30 recommendations"` — a sentence with embedded counts.

### Defect: 11px is below the readable floor

Measured: `font: 11px/1.5 var(--mono)`, weight 400. `typeset.md` says to "use 1rem / 16px as
the ordinary web body floor unless a dense role, platform convention, or user setting
justifies otherwise". This is neither dense nor a convention: it is a live region the user is
meant to read. 11px was the smallest text in the app.

**Fixed:** 13px in `var(--body)`, matching the existing `.status-line` convention, plus
`font-variant-numeric: tabular-nums`.

### Correction: the contrast claim was wrong

The critique said "the contrast is also uncertain at 11px depending on the color in use".
Measured: the element uses `--muted` (`#a5a69c`) on `--bg`, which is **7.09:1** — comfortably
passing AA, and never in doubt. Only `--subtle` ever failed, and that was C1.

This is recorded because "uncertain" invited a change that was not needed. The element's
colour is unchanged.

### Why mono was replaced rather than enlarged

The critique suggested switching "from mono to body". `typeset.md` line 51 says to "use
numeric, tabular, code, and label features when their content benefits" — so mono is not
wrong a priori for numeric content. But this is a **sentence with numbers in it**, not a code
readout or a column of figures: it is read as prose and announced as a live region.
Proportional body type at a readable size, with tabular figures to keep the two counts
column-stable, satisfies both lines rather than trading one for the other.

`typeset.md` line 42 also says to "combine size, weight, space, and tone deliberately instead
of asking size alone to do all the work". That is why the weight stays 400 and the colour
stays `--muted`: the count is quiet metadata and must not compete with the section heading.

### Also fixed: the live region had no role

The element was `aria-live="polite"` with no `role`. It now carries `role="status"`, which
gives it an implicit polite live region and a reliable announcement across assistive tech.
The explicit `aria-live` is retained for readers that do not infer it from the role.
Verification shows it now appears as `status:` in the accessibility tree; before it was an
unroled paragraph.

### Verification

Measured on the branch: computed style is 13px, weight 400, `IBM Plex Sans`, `tabular-nums`,
`role="status"`, contrast unchanged at 7.09:1; the region renders as `status:` in the ARIA
tree; 8/8 pages render their expected heading; zero horizontal overflow at
1440/1200/1100/900/760/620/390/360px; no console or page errors; `--mono` still has 18 other
uses so the token is not orphaned.

The manual browser report is published in PR #149's comments and records tested head
`600c75475cfbe1d28230345835aee2316519365f`. Because the branch has now been refreshed onto
current `main`, repeat the required browser checklist on the new exact head after CI passes.
The prior report remains evidence for the prior SHA only.

## 5g. Footer placement findings

C5 of the external critique. It reported the `<footer>` as sitting "mid-`<main>`, before five
page sections". Measured, it was worse than that: **the footer's position changed per route.**

### Measured before

The footer sat inside `<main>` between the `newReleases` section and the five that follow it.
Because sections are toggled with a `hidden` class, its place in the reading order depended on
which section was visible:

| Route | `<main>` children in order | footer renders |
|---|---|---|
| dashboard, recommendations, newReleases | `nav, section, footer` | below content (top 291) |
| personalDiscoveries, classics, artistDeepDive, acquisitions, settings | `nav, footer, section` | **above content (top 112)** |

On five of eight routes the footer rendered at `top=112` while the page heading started at
`143`, so a page footer appeared **above the page heading**. A screenshot of the Settings page
shows the notice line sitting over the word "Settings".

It was also never a `contentinfo` landmark: nested inside `<main>`, the ARIA tree showed no
`contentinfo` at all.

### After

Moved after `</main>`. Measured: `footerInsideMain: false`, ancestor chain `[body, html]`;
`main`'s children are `[nav, section]` on all eight routes so the reading order is now
identical everywhere; the footer renders **below** the content on all eight; and the ARIA tree
now reports `contentinfo:` as its own landmark.

### Not done: the skip link

`harden.md` lists "skip links for long content" under keyboard navigation, and an audit of this
change found **zero skip links**: the first tab stop is the Dashboard nav button, so a keyboard
user must traverse all nine navigation controls before reaching page content on every route.

Not fixed here. It is a real gap but a separate change with its own design question (where the
link should become visible, and which target it should point at), and this PR is scoped to
relocating the footer. Recorded so it is not lost.

### Verification

Measured on the branch: footer outside `<main>`; reading order identical across all 8 routes;
footer below content on all 8 (verified by comparing `footerTop` against `sectionBottom` per
route); `contentinfo` present in the ARIA tree; 8/8 pages render their expected heading; zero
horizontal overflow at 1440/1200/1100/900/760/620/390/360px; keyboard order is nav then content
with no footer interruption; no console or page errors.

### Manual browser report and merge (PR #156)

The user-published manual report is attached to PR #156's conversation and pins the run to exact head `47d33cbecadf64ed4b434764883cec6ae99d30bc`. All eight checklist items passed with zero failures. The report covers first-run login/setup, dashboard/artwork, discovery, navigation/album details, settings secrecy/persistence, Get/request behavior without triggering a real download, acquisition cards/status, and absence of unexpected browser/server errors. Exact-head CI passed: syntax `38815023255`, Docker packaging `38815023085`, runtime smoke `38815023444`, validation-only image/multi-architecture validation `38815023661`. PR #156 merged at `c560c28063f26a1a72d7016c951bf265d2ddd158`.

Limitations remain explicit: Chromium only, no real screen reader test. The skip-link gap above remains open and is not part of C5. Image publishing/deployment and production runtime verification were not performed.

## 5h. Artist Deep Dive findings

C6 of the external critique, which called this its single highest-leverage move. Three
defects measured, none of which was the one the critique described.

### The critique's premise was outdated

It said the section's content "groups by artist with genre context; a flat album grid erases
that structure entirely". That was true when it was written, but the code already groups:
`loadDiscovery` builds one `.genre-row` per genre family with an `<h3>` heading, an album
count, and per-row scroll arrows, and it deduplicates to one album per artist before grouping.

So the fix is not "add grouping". The three real defects are below. This is recorded because
the critique's stated diagnosis would have led to rebuilding something that already exists.

### Defect 1 — the hierarchy inverted the task

Measured on a rendered deep-dive card:

| Element | Size | Family |
|---|---|---|
| Album (the `<h3>`) | 20px | Barlow Condensed |
| Artist (`.card-artist`) | 12px | IBM Plex Sans, muted |

The section's own copy, in `index.html`, reads "**Explore missing albums by artists in your
library**". The task is artist-led. `layout.md` requires hierarchy to "follow product priority,
not framework defaults" — the album-led order was inherited from the album-grid sections, where
it is correct, and carried into a section whose task is the opposite.

**Fixed:** the artist takes the card heading and the album becomes the supporting line. Gated
on `isDeepDive`, so every other section keeps album-led hierarchy.

### Defect 2 — a category tag repeated on every card

The card rendered a `card-category` tag reading "artist deep dive" on every item. In a section
where every card is a deep dive, and where the row heading already names the genre, the tag
conveyed nothing while adding a bordered element to each card. `layout.md`: "Group by meaning.
Use proximity before adding containers or decoration."

**Fixed:** the tag is omitted for this section only. Other sections keep theirs, where the
category genuinely varies per card.

### Defect 3 — dead controls in the tab order

Each genre row rendered two scroll arrows unconditionally. Measured on a row of two albums:
`scrollWidth === clientWidth`, so the row does not overflow and the arrows do nothing. Clicking
measured `scrollLeft` staying at `0`.

The arrows were nonetheless **visible and keyboard-focusable**, so a short row put two inert
buttons in the tab order that a keyboard user would land on and activate for no effect.

**Fixed:** the arrows are hidden and given `tabindex="-1"` unless the track actually overflows,
re-evaluated through a `ResizeObserver` and on content change because neither the final width
nor the content is known at construction time. Observers are disconnected on every re-render so
repeated loads do not accumulate them.

### Verification

Measured on the branch with a fitting row (2 albums) and an overflowing row (14 albums):

| Row | `overflow` | arrows hidden | arrow `tabindex` |
|---|---|---|---|
| 2 albums | false | **true** | `-1`, `-1` |
| 14 albums | true | false | removed (focusable) |

Tab from a fitting row's arrow moves to the card, not to another inert arrow. The deep-dive card
heading now reads "Keith Jarrett" with "The Köln Concert" beneath it, and renders zero category
tags. 8/8 pages render their expected heading; zero horizontal overflow at
1440/1200/1100/900/760/620/390/360px; no console or page errors.

### Note on the payload used

The isolated environment has no Navidrome library, so deep-dive data was injected by
reconstructing the exact DOM the app's own renderer produces. The structure and the style
results are real; the content is not. The real `loadDiscovery` path was exercised only for the
empty case.

### Manual browser checklist status

**Pending on the refreshed exact PR-head SHA.** Prior browser-agent measurements used reconstructed/injected deep-dive DOM rather than a real Navidrome library. They are not a substitute for the documented human checklist. After exact-head CI passes, run the full checklist in the isolated local helper, with sandbox paths and slskd disabled; record the exact SHA, viewport checks, keyboard behavior, console/network/server errors, and any skips. Do not merge before this gate is complete.

## 5i. Empty-state copy findings

C7 of the external critique. Four defects, measured in the running app rather than read from
source.

### Defect 1 — four sections shared one generic sentence

`loadDiscovery` renders one empty-state string for `new_releases`, `personal`, `classics` and
`artist_deep_dive`:

```
No results. Try refreshing this list.
```

Those four sections have genuinely different preconditions, stated in their own descriptions:
new releases needs a full album already in the library, personal discoveries needs listening
history, and the library and artist views need a connected Navidrome. One sentence could only
name the symptom.

`clarify.md` requires an empty state to "explain the state and provide the next useful action",
and to "distinguish first use, no results, filters, permissions, and failure". A single string
cannot do that across four different causes.

**Fixed:** each section now states its own precondition and what resolves it, e.g. "No personal
discoveries yet. These recommendations are based on your listening history, so they need
Last.fm or ListenBrainz configured in Settings before there is anything to work from."

### Defect 2 — parenthesised pseudo-plurals

Three messages used fake plurals:

```
3 item(s)
1 acquisition record(s).
```

`clarify.md` asks for "complete translatable messages rather than concatenated fragments" and
for pluralization to be handled. "item(s)" is neither: it reads as a fragment to a person and
it is untranslatable in languages with more than two plural forms.

**Fixed:** a small `pluralize(count, singular, plural)` helper. Measured: `1 acquisition
record`, `3 acquisition records`, `1 item`, `0 items`.

### Defect 3 — the empty message carried the loading glyph

`renderAcquisitions` set the status text without calling `setStatusState`, so the element kept
the `is-loading` class applied by `loadAcquisitions`. Measured, with no acquisition records:

| | Before | After |
|---|---|---|
| text | `No acquisition records yet.` | same, plus what the section is for |
| classes | `status-line is-loading` | `status-line is-empty` |
| glyph | `…` (loading) | `—` (empty) |

The message said "no records" while the glyph said "still working" — the two halves of the same
state contradicted each other, and the glyph is the part a scanning user reads first.

**Fixed:** the kind now travels with the message. The detached-override case is excluded,
because a caller rendering a single identity owns its own node.

### Defect 4 — the empty state named no action

"Try refreshing this list" told the user to retry an operation that had already produced
nothing, without saying why it might work the second time. The rewritten copy names the actual
precondition instead, which is what the user has to change.

### Note on where the generic string appears

With no data, the sections take the auto-refresh path first and show "Building the first list
in the background…", so the empty branch only renders once a refresh has already been attempted
for that section. Verified by exercising the branch directly rather than by waiting for it.

### Verification

Measured on the branch: four distinct empty strings, one per section, all four carrying
`is-empty` and the em-dash glyph; the acquisitions empty message now renders `is-empty` with
`—` instead of `is-loading` with `…`; `pluralize` returns `1 acquisition record`, `3 acquisition
records`, `1 item`, `0 items`; 8/8 pages render their expected heading; zero horizontal overflow
at 1440/900/620/390/360px despite the longer strings; no console or page errors.

## 5j. Tabs pattern and skip link

Two gaps carried forward from earlier sessions: the settings-tab ARIA pattern, and the skip link
discovered while auditing C5.

### Gap 1 — the tabs pattern was half-applied

The markup already had `role="tablist"`, `role="tab"`, `role="tabpanel"` and `aria-controls`.
Measured, two halves were missing:

| | Before | After |
|---|---|---|
| Panel accessible name | **none** | `aria-labelledby` on all 4 panels |
| Roving `tabindex` | **absent** | selected tab `0`, others `-1` |
| Tab stops consumed by the 4 tabs | **4** | **1** |
| `ArrowLeft`/`ArrowRight` | did nothing | moves focus **and** switches panel |
| `Home`/`End` | nothing | first / last tab |
| Wrap-around | n/a | last → first |

`audit.md` lists "Keyboard navigation: Missing focus indicators, illogical tab order" and
`critique.md` asks "Are all interactive elements focusable with visible focus indicators?". A
tabs widget that is announced but not operable is the failure both are pointing at: a keyboard
user had to Tab through all four tabs to leave the group, which is exactly what the pattern
exists to prevent.

**Fixed** per the tabs pattern: activation follows focus, so an arrow key both moves focus and
switches the panel. Click still works, verified separately, so the pointer path is unchanged.

### Gap 2 — no skip link at all

`harden.md` lists "Skip links for long content" under keyboard navigation. Measured: the document
contained **zero anchors**, so there was no skip mechanism, and the nine navigation controls plus
the page's own controls occupied the first 15 tab stops on every route.

**Fixed:** a `.skip-link` as the first element in the tab order, targeting `main` (given
`id="content"` and `tabindex="-1"` so it can receive focus without becoming a tab stop itself).

It is hidden with `transform: translateY(-200%)` rather than `display: none`, because a
`display: none` link cannot receive focus and would therefore be unreachable by the very
keyboard users it serves.

### Note on the Forever Components reference

`inputs-switches/segmented-pill` was a candidate for this pattern. Its own metadata rules it out:
"**No aria-selected or role=tablist — add for full accessibility**", plus "Production use without
removing the auto-cycle loop". It is announced as no better than the code it would replace, so
the pattern was built directly rather than borrowed.

### Verification

**Skip link:** first tab stop measured as `A.skip-link`; activating it moves focus to
`MAIN#content` and sets `#content` in the URL; when unfocused its transform is
`translateY(-74px)` so it is off-screen; it does not affect `scrollWidth`.

**Tabs:** `tabindex` reads `navidrome:0, slskd:-1, lastfm:-1, listenbrainz:-1`; all four panels
resolve `aria-labelledby` to an existing tab id; Tab from the selected tab goes straight to the
first form input, so the group costs **one** stop instead of four; `ArrowRight` moves focus to
`slskd` and switches the visible panel to `settingsSlskd`; `End` selects `listenbrainz`;
`ArrowRight` from the last wraps to `navidrome`; clicking each tab still switches its panel.

Both: 8/8 pages render their expected heading; zero horizontal overflow at
1440/1200/1100/900/760/620/390/360px; no console or page errors.



### Refreshed-main merge verification (PR #192, 2026-10-16)

PR #188 conflicted after main advanced, so its accessibility changes were reapplied to the current
main versions in replacement PR #192. Exact tested head: `75c13b0099285747c9da75c5c3879e6594e5fe36`;
squash merge: `4fc72001807e0afc40ebc99bf1be9a502f87e0f8`.

All four required GitHub Actions workflows passed on that exact head: Python syntax (run 1069),
Docker packaging/full unit suite/build (run 976), container runtime smoke (run 785), and
validation-only Docker image validation with publishing paused (run 829). The user-published
manual browser report in PR #192 tested the same SHA and records all checklist items passing,
with zero failures. No publication, deployment, or production runtime verification is claimed.


## 5k. Token and touch-target findings

Backlog items 4 and 5.

### Item 4 — 33 colour literals, only 3 of which were duplicates

Measured before changing anything. Of 33 distinct hex values after the token block, only three
exactly duplicated an existing token (`#191a1a` = `--bg`, `#222424` = `--surface`, `#3b3d39` =
`--border`). The other thirty were real values with no name.

So this was not mostly deduplication, which is what the item title implies. It was naming colours
that already existed. Adding 22 tokens named by purpose, per the type guidance that "role names
and tokens should describe purpose rather than values":

| Token | Replaced | Written |
|---|---|---|
| `--chrome` | `#1d1f1e` | 2x (header, sidebar) |
| `--surface-inset` | `#202221` | 4x (inputs, panels) |
| `--yellow-bright` | `#f3d66b` | 4x (accent hover) |
| `--edge` | `#353834` | 3x (card edges) |
| `--surface-well` | `#30322e` | 3x (artwork placeholder, tag fill) |
| `--scroll-thumb` | `#686044` | 3x |

`--on-yellow` is worth noting specifically: `#191a1a` appears as **text on an accent fill**, not
as a background. Reusing `--bg` would have been a token that lies about its role.

**Hardcoded hex after the token block: 55 → 8.** The remaining eight are single-use tints and
shades plus pure black and white. Adding a token for each would be the "system abstraction for one
local exception" the polish guidance warns against, so they are left deliberately.

**Verified as a pure refactor rather than assumed.** The pre-change CSS was checked out into a
separate git worktree at `origin/main`, both versions were served side by side, and computed styles
were compared for 33 selectors across 7 colour properties each:

- **0 differences** across all 231 property comparisons.
- Screenshots of the settings page from both builds hashed **identically**.

### Item 5 — four controls under the 44x44 minimum

Measured against the 44x44 touch-target criterion:

| Control | Before | After | Method |
|---|---|---|---|
| `.genre-row-arrow` | 38x34 | **44x44** | enlarged; glyph unchanged |
| `.album-modal-close` | 38x38 | **44x44** | enlarged |
| `.card-actions .get-album` | 42x42 | **44x44** | enlarged |
| modal platform-link chips | 30x30 | visual 30x30, **hit 44x44** | transparent `::after` inset |

The platform chips keep their 30px visual size so the strip keeps its rhythm, while a transparent
pseudo-element expands the pressable area. This follows the layout guidance to "keep touch targets
usable even when their visible marks are small".

`.card-art .get-album` (46px) and `.album-modal-art .get-album` (58px) were already above the
minimum and are unchanged.

### Verification — the gesture, not just the box

The audit guidance is explicit that "a rendered viewport proves layout, not the gesture", so the
sizes were not trusted on their own. Exercised in a `has_touch` context with synthesized taps:

- The genre-row arrows **scroll the track under touch**: `scrollLeft` went `2 → 926`.
- A tap **4px outside the visible edge** of a 30px platform chip still resolved to that link
  (`closest('a')` matched), proving the expanded hit area is real and not just a wider box.
- No horizontal page scroll was introduced: `scrollWidth == clientWidth` at every width.

### A measurement error worth recording

An intermediate run reported three controls as `FAIL` with `box=[0,0]`. That was a fault in my
check, not the CSS: the controls live in sections toggled with a `hidden` class, so they measured
zero until their section was navigated to. Recording it because a zero-size box in this codebase
means "not in the visible section", not "broken target" — and the same trap produced a false
negative during C1.

### Verification summary

Item 4: 0 computed-style differences across 33 selectors x 7 properties; identical screenshot
hashes. Item 5: all six interactive controls at or above 44x44 in both axes; arrows scroll under
synthesized touch; an out-of-mark tap lands on the intended link; no horizontal scroll. Both: 8/8
pages render their expected heading; zero horizontal overflow at 1440/1200/1100/900/760/620/390/
360px; no console or page errors.

## 5. Observed evidence for item 1 (State craft)

### Before the change (main at `4098361`)

Observed by the local headless verifier driving an authenticated session, and confirmed
by reading source.

- **Status elements are styled inconsistently.** Eleven status paragraphs existed. Only
  three carried a class: `dashboard-picks-status`, `album-modal-status`, and `.status` on
  `#connection`. The rest carried **no class at all**, so they inherited plain `<p>`
  styling and rendered at body size and weight (15px/400), visually indistinguishable
  from descriptive prose. Measured: **9 of 10 status elements unclassed at body
  size/weight**.
- **`aria-live` was applied inconsistently.** Six had it; four that the JS writes dynamic
  progress text into did not (`personalStatus`, `classicsStatus`, `artistDeepDiveStatus`,
  `acquisitionsStatus`). Measured: **5 of 10 without `aria-live`**.
- **Status text was unstructured prose** with no shared vocabulary or visual distinction
  between loading, empty, error, and success, so a transient state was indistinguishable
  from a failure without reading the sentence.
- **Contrast was fine** (7.09:1 worst case), so this was a hierarchy defect, not a
  legibility one.

### After the change (branch `ui/state-craft`)

- One shared `.status-line` treatment in `static/app.css` derived from existing tokens.
- Every status element carries the class: **10 of 10**.
- Every status element announces updates: **10 of 10** with `aria-live`.
- Each state has a distinct leading glyph, so state is never carried by colour alone:
  `…` loading, `—` empty, `!` error, `✓` success, `›` progress, `•` neutral.
- `static/app.js` derives the state kind via `classifyStatus()` and applies it via
  `setStatusState()`, so existing call sites needed no second argument threaded through.
- Verified: zero browser console or page errors, no horizontal overflow at 1440, 390, or
  360 px.
- Deliberately **not** a pill or a badge, because `docs/FRONTEND_DESIGN_GUIDE.md` section 3
  lists colourful status pills among the anti-patterns to avoid.

## 6. Session protocol

Each session handles exactly one backlog item and produces exactly one PR.

**Session start — read only these three:**
1. `AGENTS.md`
2. `docs/FRONTEND_DESIGN_GUIDE.md` (sections 2, 3, and 8 matter most)
3. this file

Do not re-read `PROJECT_STATUS.md`, `PROJECT_LOG.md`, `TEST_PLAN.md`, or the other project
docs unless the item genuinely requires it. GitHub is the record of what happened; this
file is the compressed index into it.

**Impeccable is mandatory every session, not optional.** `AGENTS.md` frames it as "when
available in ZCode", and that latitude is what caused two sessions (C1, C2) to proceed
without opening it. Treat it as required:

1. Read the relevant reference file(s) below **before** choosing an approach — not after, to
   justify a decision already made.
2. Record in the PR body which guidance was **applied** and which was **rejected**, with the
   reason. A PR that cites no Impeccable guidance is incomplete.

The reference files live at `.pi/skills/impeccable/reference/`. Select by kind of work:

| Kind of work | Read |
|---|---|
| Contrast, WCAG, ARIA, landmarks, semantic HTML, keyboard access | `audit.md` |
| Error, empty, loading, edge-case and boundary states | `harden.md` |
| Hierarchy, spacing, type scale, motion, general refinement | `polish.md` |
| Adding or changing motion | `animate.md` |
| Fonts, type scale, sizing | `typeset.md` |
| Section composition, grids, layout rhythm | `layout.md` |
| Interface copy, empty-state wording, error text | `clarify.md` |
| Removing clutter, simplifying a busy screen | `distill.md` |
| Evaluating an existing component in isolation | `component-review.md` |

If two apply, read both. `audit.md` carries a severity model (P0-P3) and a health-score
template that are useful even when the task is not a full audit.

**Do not treat Impeccable as a mandate.** `AGENTS.md` is explicit that only recommendations
fitting this product and its existing components should be applied, and that broad redesign
commands are out of scope. Where it conflicts with `docs/FRONTEND_DESIGN_GUIDE.md` or with
`AGENTS.md`, the project documents win and the conflict is recorded in the PR.

**Work:**
1. Confirm current `main` and the highest PR number (`gh pr list --state all --limit 1`).
2. Branch `ui/<short-task-name>` from current `main`. Never commit to `main`.
3. Change only files in the authorized surface.
4. Add or update front-end tests for changed client behavior.
5. Run the checks in section 7 and report exact commands and observed results.
6. Open a PR against `main` with purpose, acceptance criteria, changed files, Impeccable
   guidance applied and rejected, before/after screenshots, exact head SHA, tests actually
   run, manual UI report, limitations, and next action.
7. Do not merge, tag, publish, deploy, or alter branch protection.

**Session end:** update section 4 of this file (mark the item done, record the PR number)
in the same PR as the work, so the next session's read is accurate.

## 7. Verification commands

Automated, run on the exact PR head:

- Syntax: `python -m compileall app static` is not meaningful for JS; use
  `node --check static/app.js` for the client script.
- Unit suite: `python -m pytest tests/ -q` (or the subset relevant to changed behavior).
- Existing CI workflows are `container-smoke.yml`, `docker-publish.yml`, `docker-test.yml`,
  and `python-syntax.yml`.

Manual browser gate: required for UI-facing changes after automated checks pass on the
exact head SHA. The helper is `~/navi-librarian-test/test-pr.sh <PR-number>`; it reads the
open PR head from GitHub and writes a report to `~/navi-librarian-test/reports/`. It uses
`~/navi-librarian-test/sandbox/` for music paths and requires slskd disabled at
`http://127.0.0.1:9`. See `docs/LOCAL_UI_TESTING.md` for the full checklist.

**The manual gate requires a real browser.** If it has not been run against the exact head
SHA, the PR must say so and record those checks as skips. Skipped is not passed.

## 8. Automation status

A headless-browser verifier exists and works, but it is deliberately **not** in this
repository. It lives on the operator's machine at `~/.ui-verify/` (`ui-verify.sh`,
`drive.py`) and is a verification utility, not an application dependency. Nothing in
`app/` imports it and it is absent from `requirements*.txt`. Keep it that way.

It resolves a PR head SHA from GitHub, downloads that exact archive, installs the app's
requirements into an isolated venv outside the repo, boots the app on a private port with
its own data directory, then drives headless Chromium and writes a Markdown report pinned
in filename and content to the tested SHA.

It measures things that are mechanically checkable: page rendering, per-page headings,
class and `aria-live` coverage on status elements, computed contrast, keyboard focus
reach, horizontal overflow at several widths, reduced-motion enforcement, and console
errors. It cannot judge whether a design is good, so it does not replace the human
checklist in `docs/LOCAL_UI_TESTING.md`. It never runs destructive acquisition actions.

### Findings from the initial verifier run (main at `4098361`)

Recorded here because the verifier itself is not published.

> **A caution about focus measurements.** Any keyboard-focus check must first report how
> many focusable elements the page actually contains, and must only claim a reach problem
> when that count exceeds the number of stops observed. The runs recorded here have no
> Navidrome connection, so no discovery cards render; the app shell is deliberately sparse.
> A low focus-target count in this environment is expected and is **not** evidence of a
> defect. See the withdrawn finding in section 5.

- **Reduced motion is implemented correctly.** `static/app.css` has exactly one
  `prefers-reduced-motion: reduce` block, and under that preference the computed
  `transitionDuration` on interactive elements becomes `1e-05s`. `static/login.css` has
  no such block, which is acceptable because the login page is nearly static.
- **Contrast is not a problem.** The lowest-contrast status text measured 7.09:1, well
  above the 4.5:1 WCAG AA threshold for body text. The state-craft defect was hierarchy,
  not legibility.
- **Keyboard focus reach: WITHDRAWN — not a defect.** An earlier revision of this file
  claimed that 25 Tab presses reached only three dashboard controls, and that focus could
  not reach the remaining navigation, the discovery cards, or the card action buttons.
  **This was wrong.** Re-measured against an authenticated session with the app shell
  rendered: Tab reaches all nine navigation buttons in order, then the dashboard shuffle
  button, then cycles back to the start. Every stop shows a visible focus ring
  (`outline: solid 2px` in the accent colour).

  The original number came from a checking loop that collected *distinct* focus targets
  over 25 presses on a page with about ten focusables, while **no discovery data was
  present** (the isolated runs have no Navidrome connection, so no cards render). The
  loop therefore reported a data-starvation artifact as an accessibility defect. The
  mistake was reporting a count without first confirming that the page had more than that
  many focusable elements to reach.

  Cards were also checked in source and are keyboard-operable already:
  `makeAlbumCardInteractive()` sets `tabindex="0"` and `role="button"`, and a document-level
  `keydown` handler opens the modal on Enter or Space. The album modal declares
  `role="dialog"`, `aria-modal="true"`, and `aria-labelledby`.
- **No horizontal overflow** at 1440, 390, or 360 px in the measured states.
- **No browser console or page errors** during an authenticated pass over all eight pages.
