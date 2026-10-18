# UI backlog execution — Session 0 baseline

Last updated: 2026-10-15
Ownership: any agent may handle front-end work, strictly within the permitted paths in root `AGENTS.md`.
Scope of this file: session-bootstrap reference. It records the verified state of the
front-end at a known `main` SHA so later sessions do not re-read the full project
documentation set.

**Redesign pointer (2026-10-18).** The current front-end queue is `docs/REDESIGN_ROADMAP.md`, applying
`docs/DESIGN_SYSTEM.md`. The backlog state below is history and evidence: it records what shipped and
how it was measured, and the redesign must preserve the behavior and accessibility it established.
Update this file in the same PR as each redesign slice.

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
- **Navigation rail redesign** (not a numbered backlog item; requested directly) — merged as
  PR #132. The sidebar active state is a sliding indicator driven by `translateY`, adapted from
  the Forever Components `navigation/gooey-tab-bar`. The blob covers the seven content items;
  Acquisitions and Settings are intended to move elsewhere later, as is Log out. See section 5b.
- **State craft** (item 1) — merged as PR #121. A shared
  `.status-line` treatment now covers every status element, with `aria-live` on all of
  them and a per-state leading glyph so state is never carried by colour alone. See section
  5 for the before/after measurements.
- **Per-section layouts** (item 2) — acquisition merged as PR #128; artist deep dive merged as
  PR #184; recommendations (Discover music) opened as PR #215. Scoped to one section per PR, as
  `AGENTS.md` requires. Three discovery sections and Settings remain; see the Remaining list
  below.
- **Get/request button consolidation** (item 3) — merged as PR #131. The modal, artwork-overlay and card-action variants now
  share one `.get-album` base, three duplicated creation sites collapsed into one
  `createGetButton()` helper, and the control gained an explicit state machine. Three real
  defects were fixed as part of the work; see section 5a.

**Remaining, in the guide's priority order:**

1. ~~**State craft**~~ — done in PR #121.
2. **Per-section layouts** — **partially done.** Acquisition (PR #128), artist deep dive
   (PR #184), recommendations (PR #215) and Classics (this PR, section 5n) are differentiated.
   Still on the plain `.cards`
   grid: New Releases and Personal Discoveries, plus Settings, which has its own
   layout but no composition work. The guide's instruction is "do not force every page into the
   same dashboard grid", so each remaining section needs its own justification rather than a
   sweep. Recommendations was picked because its defect was the control stack rather than the
   grid, and a ranked album list is genuinely served by an album grid; see section 5l.
3. ~~**Get/request button consolidation**~~ — done, merged (PR #131).
4. ~~**Type/token cleanup**~~ — **done, merged as PR #194.** See section 5k. The item title
   overstated the work: of 33 distinct hex literals outside the token block only 3 exactly
   duplicated an existing token, so this was naming colours that already existed rather than
   deduplicating.
5. ~~**Responsive controls**~~ — **done, merged as PR #194.** See section 5k.
6. **Continue visual audit** — the external critique's list is exhausted; this now means
   finding the next issue by evidence. Candidate starting points: the 30x30 platform-link icons
   and the `#686044` hover-border value that appears three times — both closed by PR #194, so
   this item now needs a fresh starting point.

**Correction (2026-10-16, PR #215).** Items 4 and 5 were still listed here as "not started"
after PR #194 (`10b14c1`, "a11y: token cleanup and 44x44 touch targets") had merged them, and
section 5k already recorded the work. They are marked done above so the next session does not
redo them. The stale bullets are the reason this file must be updated in the same PR as the
work it indexes.

**Contrast fix (C1 of the external critique).** The `--subtle` token was raised
from `#77796f` to `#94958b`, merged as PR #142. The critique recommended
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
| C6 | **Differentiate Artist Deep Dive.** The critique's single highest-leverage move. | Item 2 | **Done** — PR #184. See 5h. |
| C7 | **Write per-section empty-state copy.** Three cases per section: loading, empty-success, error. | Copy work | **Done** — PR #186. See 5i. |

**C1–C7 are all closed.** Two further gaps found while working the list are also closed:

| Gap | Found during | Status |
|---|---|---|
| Settings-tab ARIA pattern (`aria-labelledby`, roving `tabindex`, arrow keys) | C2 audit | **Done** — PR #188. See 5j. |
| Missing skip link | C5 audit | **Done** — PR #188. See 5j. |

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

## 5l. Discover music control composition (item 2)

Backlog item 2, scoped to one section: `#recommendations` ("Discover music"). Branch
`ui/recommendations-control-hierarchy`, PR #215.

### The defect was the control stack, not the grid

The section stacked two adjacent control rows of equal visual weight — `.controls` (an `Albums`
count plus the primary Generate action) and `.discovery-controls` (search, discovery category,
sort) — with nothing distinguishing the inputs that produce a request from the controls that
only act on an already-generated set. Measured from source at `d54b25a`: `.controls` used
`margin: 18px 0 14px` and `.discovery-controls` `margin: 17px 0 8px`, so every vertical interval
in the panel sat within a few pixels of every other one, and the refinement controls are inert
until a set exists.

It was also the only discovery section with no descriptive line. `newReleases`,
`personalDiscoveries`, `classics` and `artistDeepDive` each explain themselves immediately below
their heading.

The four-column album grid was deliberately left alone. A ranked album list is genuinely served
by an album grid, and `FRONTEND_DESIGN_GUIDE.md` §3 allows a treatment only when it improves
hierarchy, comprehension, feedback or interaction. This is why the section was picked over the
other three still on `.cards`: the evidence pointed at the controls, not the layout.

### What changed

| Before | After |
|---|---|
| `h2` then straight into controls | `h2`, then a description paragraph |
| `.controls` (count + Generate) | `.controls.request-controls` — phase 1, primary action leads |
| `.discovery-controls` placed before the count | `.results-toolbar` after the count: count, name, then `.discovery-controls` |
| refinement row unnamed | `role="group"` + `aria-labelledby` = "Refine results" |
| every interval within a few px | `20px 0 30px` between the phases, `8-9px` within each |
| no client behaviour change | ids and listeners unchanged; `static/app.js` untouched |

The rhythm rules are scoped (`.controls.request-controls`, `.results-toolbar`, and
`.results-toolbar .discovery-controls`) so the shared `.controls` rule keeps its existing spacing
in `newReleases`. `.discovery-controls` appears exactly once in the document, which is what
keeps that override safe.

### Verification

`tests/test_recommendations_ui_contract.py` adds 8 source-contract regressions: the description
precedes any control; the request group's contents and its position ahead of the toolbar; toolbar
order (count → label → controls); the group's `aria-labelledby` resolving to a unique `<p>` in the
same block; `.discovery-controls` appearing exactly once; document id uniqueness; every `$('id')`
in `app.js` still resolving to a template id; and the section-scoped CSS rules, including that the
shared `.controls` rule is unchanged.

| Check | Result |
|---|---|
| `node --check static/app.js` | passed |
| `python -m compileall app static` | passed |
| new contract tests on the branch | **8 passed** |
| the same tests against the pre-change files | **6 failed** — the tests are a real guard |
| full unit suite | **413 ran, 0 failures, 0 errors, 1 skipped** |
| `detect --json static/app.css app/templates/index.html` | 6 findings, identical set before and after |
| `detect --json --scope layout ...` | `[]` |

`pytest` is not installed in this environment, so the suite was run through a `unittest` loader
rather than `python -m pytest tests/ -q`; same tests, different runner.

**Rendered verification is the operator's step against the PR head SHA**, per the PR body. The
measurements above are source-measured, not browser-measured.

### Carried forward, not fixed here

A failed generation is still invisible. `initializePage` auto-clicks Generate, and on failure the
handler writes the error into `#recommendationDebug`, which lives inside the collapsed
`<details>` "Recommendation diagnostics", so the user sees neither the failure nor a recovery
path. That is a state-craft (item 1) defect in this section, not a layout one, and fixing it here
would straddle two backlog items in one PR. It is the recommended next PR.

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

## 5m. Header settings menu (merged PR #327; plan in `docs/STATUS_ICON_DEV.md`)

Settings and Log out moved out of the sidebar into a gear button at the top right of the
header. Activating the gear opens a small disclosure with those two items. Acquisitions stays
in the rail. It completes the follow-up that §5b anticipated ("Acquisitions and Settings are
intended to move elsewhere later, as is Log out").

Decisions recorded from the plan: a disclosure (`aria-expanded`, `aria-controls`) rather than
`role="menu"`; Log out uses neutral text, because `--red-text` fails 4.5:1 on the panel surface
and logging out is not destructive; the skip link moved ahead of `<header>` so it stays the
first tab stop; one non-colour token (`--shadow-menu`) was added and no colour literal was.

Verification on the branch (head SHA recorded in the PR, not here):

- `python -m unittest tests.test_header_menu_ui_contract`: 20 tests pass on the change and 16
  of them fail when run against the pre-change `index.html`, `app.css` and `app.js`.
- `python -m unittest discover -s tests`: 660 tests, OK.
- `node --check static/app.js` and `python -m compileall app static`: clean.
- Impeccable detector: the same five findings as `main` (nav-blob and modal easing, card stripe,
  album-modal `<img>` without `src`, an 11px label). None are introduced by this change; they
  are left for their own items.
- Headless Chromium against the local app, sandbox paths, slskd disabled: rail has no Settings or
  Log out; skip link is the first tab stop; gear opens and closes by click, outside click,
  Escape (focus returns to the gear) and ArrowDown; Settings from the menu loads its panels;
  the gear and the item carry the current-page cue; no rail item is active on Settings and the
  blob is hidden; zero horizontal overflow at 1440, 1200, 900, 620, 390 and 360px with the panel
  inside the viewport and the toggle at 44×44; Log out sends `POST /api/auth/logout` and lands on
  `/login`.

Not verified: Safari (focus rule written for it, not exercised), a real screen reader, reduced
motion in a browser, and the CI workflows and manual gate on the exact PR head.

## 5n. Classics card titles (item 2, per-section layouts)

- **Problem.** Classics ("Add to your collection") sits on the four-column `.cards` grid of square
  artwork, which is 278px wide on a 1440px viewport. Long album names wrapped to four lines, so
  card heights and action rows were uneven across the section.
- **Tested and rejected:** the acquisition-grid layout (`cards acquisition-grid`). It fixes the
  wrapping but drops desktop to three columns with 603px cards, and collapses phone to one column,
  roughly doubling the scroll length. Density was the trade-off the guide asks to be deliberate.
- **Change.** Classics titles are clamped to two lines, scoped to `#classicsCards`. The full album
  name and year are the title's tooltip, so no text is lost. Other sections are unchanged.
- **Measured** (1440px and 390px, mocked discovery data with long names; screenshots in the PR):
  no title exceeds two lines; three of eighteen clamped titles lose their visible year, which
  remains in the tooltip; no horizontal overflow; console errors are only the pre-existing
  missing-asset 404s and the blocked external font request.
- **Not verified:** the full manual browser gate in `docs/LOCAL_UI_TESTING.md` on the PR head,
  keyboard tooltip access (tooltips are pointer-only; the full name stays in the DOM for
  assistive tech), Safari, and real Navidrome data.

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
available in the working environment", and that latitude is what caused two sessions (C1, C2) to proceed
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


## 9. Redesign Phase 0 baseline (2026-10-18)

Status: **measured and recorded; docs-only PR** (roadmap Phase 0). Nothing in `static/`, `app/templates/`, `tests/` or backend code was changed. Implemented: docs only. Automated tests: run (below). Browser-tested: baseline capture only (not a UI change). Merged / published / deployed / runtime-verified: **no**.

### 9.1 Pinned baseline and environment

| Item | Value |
|---|---|
| Application source measured | `main` at `dc3e5a3a8ea704bbc66aa1d1b43dc4e9594fd2be` ("Fix deterministic recommendation replay inputs", #350) |
| Branch base | `main` at `359737959e6cedca9200e7f88049235e49c819b5` (#351). `git diff --name-only dc3e5a3..3597379` lists only `PROJECT_LOG.md` and `docs/PROJECT_STATUS.md`, so the front end and application code are byte-identical to what was measured |
| Browser | Chromium 141.0.7390.37, headless, driven by Playwright 1.56.0 (Chromium only; no Firefox or WebKit) |
| OS / runtime | Ubuntu 24.04.5 LTS, Linux 6.18.44 x86_64 (cloud sandbox, not the owner's macOS machine); Python 3.13.16; Node v22.22.0 |
| Dependencies | `pip install --break-system-packages -r requirements.txt` (fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1, python-dotenv 1.2.4, mutagen 1.48.1) |
| `python -m unittest discover -s tests` | **709 tests, OK** on `dc3e5a3` (2.256 s) and again on `3597379` (2.287 s) |
| `node --check static/app.js`, `python -m compileall app static` | both clean on `3597379` |

### 9.2 How the baseline was captured, and deviations from the documented procedure

- **The documented helper was not used.** `~/navi-librarian-test/test-pr.sh` is installed on the owner's macOS machine and does not exist in this sandbox; it is also PR-oriented (downloads an open PR head), and this baseline is of `main`. The isolation it prescribes was reproduced by hand: `uvicorn app.main:app` on `127.0.0.1:8189` from the checkout, with `NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` pointing at a sandbox directory outside the repository, `SLSKD_URL=http://127.0.0.1:9` with an empty API key (slskd disabled), and Navidrome, Last.fm and ListenBrainz unconfigured. `git status` stayed clean throughout; no real data was touched.
- **Test auth:** the owner account was created through the real first-run form (`POST /api/auth/setup`); the password is random, kept only in the sandbox, and not recorded here. The helper's per-PR app-data persistence behavior was not exercised.
- **Two states per page.** *live* is the real app with an empty sandbox (no library, no listening history). *reconstructed* serves fictional API responses for the read endpoints only (`/api/dashboard-picks`, `/api/recommendations`, `/api/discovery/*`, `/api/artwork`, `/api/artist-bio`, `/api/album-details`, `/api/acquisitions` and its stream) through browser request interception; the real `app.js` then builds the DOM. Fixture fields are limited to fields `app.js` reads and statuses it handles. Names are fictional; one item has no artwork, one has very long names. The acquisition vocabulary shown is `downloading`, `download_complete_waiting_for_folder`, `imported`, `no_matches`, `queue_failed`, `slskd_error`, `settings_required`. **Reconstructed screenshots show how the current UI renders such data, not real library content.** Settings reads only real endpoints, so it has a live state only.
- **Outbound access is allowlisted in the sandbox, so Google Fonts could not load.** Every capture ran with fallback fonts instead of Barlow Condensed, IBM Plex Sans and IBM Plex Mono. **Typography in the baseline screenshots is therefore not what the owner sees.** Layout and overflow measurements may differ slightly from a machine with the web fonts.
- Pages were reached by clicking the rail (Settings through the header menu). Full-page screenshots; for reconstructed pages the capture scrolls the page first so lazily loaded artwork can load, then returns to the top. The album modal is a fixed overlay, so its screenshots are viewport captures (1440x900 down to 390x900) of the first Discover music card. The dashboard ring animates continuously, so each frame is one arbitrary moment.
- Not captured (skips): the Settings tabs other than the default Navidrome tab (slskd, Last.fm, ListenBrainz); live-state album modal (no cards without a library); keyboard walk-through, failed-Get and pending-Get states, dismiss confirmation, login failure message, 360px width, and any real-library content.

### 9.3 Visual baseline: 8 pages, modal and login at 5 widths

Each cell is `scrollWidth/clientWidth of the document · console errors · failed network requests`. Console errors and failed requests exclude the blocked Google Fonts request, which occurred exactly once in every one of the 90 captures and is reported separately in 9.4. **No capture had horizontal overflow (document or body) and none raised a page error.** All 90 captures succeeded; none was skipped.

| Page | State | 1440 | 1200 | 900 | 620 | 390 |
|---|---|---|---|---|---|---|
| Login (first-run setup) | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Login (sign-in) | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Dashboard | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Dashboard | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Discover music | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Discover music | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| New releases | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| New releases | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Personal Discoveries | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Personal Discoveries | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Add to your collection | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Add to your collection | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Artist Deep Dives | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Artist Deep Dives | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Acquisition status | live | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Acquisition status | reconstructed | 1440/1440 · 0 · 0 | 1200/1200 · 0 · 0 | 900/900 · 0 · 0 | 620/620 · 0 · 0 | 390/390 · 0 · 0 |
| Settings | live | 1440/1440 · 1 · 1 | 1200/1200 · 1 · 1 | 900/900 · 1 · 1 | 620/620 · 1 · 1 | 390/390 · 1 · 1 |
| Album modal (viewport capture) | reconstructed | 1440/1440 · 4 · 4 | 1200/1200 · 4 · 4 | 900/900 · 4 · 4 | 620/620 · 4 · 4 | 390/390 · 4 · 4 |

Artwork loaded / cards in the reconstructed state (one item has no artwork by design, so 11/12 and 9/10 are the full set): Dashboard 9/10, 9/10, 9/10, 3/10, 2/10 at the five widths (the 3D ring only loads covers that face the viewer at narrow widths); Discover music, New releases, Personal Discoveries and Add to your collection 11/12 at every width; Artist Deep Dives 11/12 at 1440 to 620 and 9/12 at 390 (covers in off-screen horizontal tracks load on scroll).

Observations, cause not investigated: the page footer text starts beneath the left rail and is clipped on its left edge at 1440 (live and reconstructed Dashboard); in full-page screenshots the rail ends at viewport height rather than page height, which may be an artifact of full-page capture.

### 9.4 Known errors present on the baseline

| ID | Finding | Evidence | Owner of fix |
|---|---|---|---|
| B1 | `GET /api/settings/listenbrainz` returns **502** whenever no ListenBrainz username is saved, so every Settings load on a fresh install logs one failed request and one console error (Settings, live, all five widths). | The route converts any exception to 502. Calling `discovery_get_listenbrainz_settings()` under the sandbox environment raises `ValueError("Configure a valid ListenBrainz username in Settings.")` from `service_settings.py:72`; identical with `LISTENBRAINZ_USERNAME` unset or empty. The other three settings endpoints return 200. Server log: 6 x 502, all this route. | Backend (protected paths). Not changed here. Until fixed, "no console or network errors" on a fresh-data run cannot be met on Settings, and later PRs should cite B1 rather than treat it as a regression. |
| B2 | The album modal requests **four third-party images at runtime**: `https://cdn.simpleicons.org/applemusic/FA243C`, `.../spotify/1DB954`, `.../bandcamp/1DA0C3` and `https://community.qobuz.com/s/Qobuz_logo_black-l2kk.jpg`. They failed in this sandbox (egress allowlist), so the platform-link icons are missing in the modal screenshots. | Source: `static/app.js` lines 560-563. 4 failed requests and 4 console errors per modal capture. | Front end. Conflicts with the redesign rule of no runtime third-party assets; belongs in the icon work (Phase 1 sprite) and the modal slice (Phase 6). |
| B3 | Google Fonts `@import` in `static/app.css` and `static/login.css` (already known; removed by Phase 1). | 1 request to `fonts.googleapis.com` per page load, blocked in the sandbox. | Front end, Phase 1. |

### 9.5 Performance baseline

Method: Chromium via Playwright, a new browser context for every run (cache disabled, authenticated session), network and CPU throttled through the DevTools protocol. **Throttle profile:** 150 ms added latency, 1.6 Mbit/s down (about 200 KiB/s), 750 Kbit/s up, CPU 4x slowdown, 1440x900 viewport. After load there is an 8 s observation window for layout shift, long tasks and late requests. Each scenario was run three times; all three values are shown as run 1 / run 2 / run 3.

- *Dashboard*: cold load of `/` (live state, empty sandbox).
- *Discover music*: cold load of `/`, then immediate navigation to Discover music by clicking the rail (the app is a single-page shell, so there is no separate cold load of Discover). Live state, so the list is empty.

| Metric | Dashboard | Discover music |
|---|---|---|
| Transfer, app requests (bytes) | 206610 / 206610 / 206610 | 206845 / 206845 / 206845 |
| Request count, app (same origin) | 8 / 8 / 8 | 9 / 9 / 9 |
| Request count, Google Fonts (blocked) | 1 / 1 / 1 | 1 / 1 / 1 |
| First contentful paint (ms) | 1108 / 1172 / 1160 | 1192 / 1204 / 1160 |
| Largest contentful paint (ms) | 1108 / 1172 / 1160 | 1192 / 1204 / 1160 |
| Cumulative layout shift | 0 / 0 / 0 | 0 / 0 / 0 |
| Load event end (ms) | 1344 / 1417 / 1393 | 1417 / 1425 / 1401 |
| Time to interactive, estimate (ms) | 1108 / 1172 / 1160 | 1192 / 1204 / 1160 |

Transfer by type, identical in all runs: document 17,872 B; stylesheets 46,103 B; scripts 110,661 B; images 31,659 B (the cassette); fetches 315 B (Dashboard) and 550 B (Discover music). Transfer sizes track the file sizes on disk, so no compression was observed. LCP element in all six runs is `#dashboardHeading`.

Limits of these numbers, stated plainly:
- **Google Fonts are not in the transfer total or the timings.** The request was blocked at the sandbox proxy, so it failed in a few milliseconds. On a real network the `@import` adds at least one stylesheet round trip plus the font files and delays first paint, so FCP and LCP here are **optimistic**, and font-swap layout shift is **not measured** (CLS 0 is for fallback fonts). The number and size of the Google Fonts font files were not observed (only the single stylesheet request), so the `<= 150 KB` font budget in the design system has no current-state baseline from this run.
- Time to interactive is **not** Lighthouse's metric. It is my own heuristic (FCP, pushed past any long task that ends within the following 5 s). Each run had one long task of 54 to 76 ms, ending before FCP, so the estimate equals FCP and carries little information.
- Populated-state weight (artwork images) was not measured; reconstructed responses are served locally and have no real transfer cost.
- Local server on loopback; only the emulated latency and bandwidth apply.

### 9.6 Contrast re-measurement (`docs/DESIGN_SYSTEM.md` section 4.1)

Measured with my own WCAG 2.1 relative-luminance script on the token values in the document (34 pairs: the 28 text pairs in the table plus the stated `--edge-strong`, `--on-accent`, `--chart-red-text` and `--edge` figures). **31 of 34 agree with the document to within 0.01** (30 numeric values plus the "at least 5.4" bound for `--text-subtle` on surface). Two more differ only because the document rounds prose figures: `--chart-red-text` on raised is 6.22 (document "6.2") and `--edge` on ink is 1.43 (document "1.4"). Every text pair clears 4.5:1; the lowest is `--chart-red` on `--surface-hover` at **4.65** (margin 0.15). `--edge-strong` is 3.28 on raised and 3.60 on surface (both above 3.0). `--text-subtle` on `--surface` is 5.85 (document: at least 5.4).

One real difference: `--edge` on `--surface` is **1.33**, not 1.4. `--edge` is decorative only, so no accessibility requirement is affected; the document's figure could be corrected to "1.3 to 1.4". This PR does not edit section 4.1.

This is a computation on token values. It is not the rendered-build re-measurement that Phase 1 owes.

### 9.7 Color-vision check (decision D2)

Swatches of `--chart-red #ff5a3c`, `--accent #f5d33f`, `--ok #86d39b` and `--caution #f0a640` on `--surface #1c1a18`, simulated with the Machado, Oliveira and Fernandes (2009) matrices at full severity in linear RGB. Difference is CIEDE2000 (dE): under 10 is hard to tell apart, 10 to 20 marginal, over 20 clear. Render: `cvd-swatches.png` (see 9.9). This is a simulation by one published model, not a test with people.

| Pair | Normal | Protanopia | Deuteranopia | Tritanopia |
|---|---|---|---|---|
| chart-red vs accent | 44.2 | 27.4 | 15.6 marginal | 28.3 |
| chart-red vs ok | 61.3 | 23.9 | 16.7 marginal | 64.1 |
| chart-red vs caution | 27.0 | 17.4 marginal | 8.1 **hard** | 17.4 marginal |
| accent vs ok | 28.9 | 16.1 marginal | 18.9 marginal | 41.4 |
| accent vs caution | 16.4 marginal | 10.4 marginal | 7.5 **hard** | 11.7 marginal |
| ok vs caution | 37.8 | 14.4 marginal | 15.7 marginal | 50.4 |

Findings:
- Under protanopia and deuteranopia the red, yellow and amber swatches collapse into one olive-yellow family. **Red vs amber is hard to tell apart under deuteranopia (dE 8.1) and yellow vs amber under deuteranopia (7.5)**; yellow vs amber is already marginal with normal vision (16.4) and also marginal under protanopia (10.4) and tritanopia (11.7).
- Lightness does not rescue any pair: luminance contrast between any two state colors is at most 2.71:1 (`--chart-red` vs `--accent` under protanopia). Color alone cannot carry state; this supports the existing rule that every state has a glyph and a text label. In the swatch render the glyphs and labels stay legible in all four views.
- Every state color keeps at least 4.09:1 on `--surface` under simulation. The lowest is `--chart-red` under protanopia (4.09); numerals are large text, and `--chart-red-text` exists for small text.
- **Red as brand vs red as error (D2):** both use one token, so they are identical to each other for every viewer; color never separates them. What separates them is glyph ("!"), message, `role`, and position (numerals only in the rank column). Red stays clearly distinct from body text under all simulations (dE 29.2 to 39.2 vs `--text`; 19.8 to 29.1 vs `--text-muted`).
- **Recommendation: keep** red as both, under the red rule, with one addition the evidence supports: error and caution always use different glyphs and labels, never color alone, because red and amber converge for deuteranopes. Changing the brand mark to the yellow family would not fix the weakest pair (yellow vs amber) and would put "selected" and "brand" on the same color. This is a judgment from a simulation; the dual meaning is semantic, and the check cannot settle it.

### 9.8 Manual checklist (`docs/LOCAL_UI_TESTING.md`), baseline run

Against `main` `dc3e5a3` with the reproduced isolation (9.2), not the helper. This is a baseline capture, not a UI-change gate.

| # | Item | Result |
|---|---|---|
| 1 | App starts; first-run setup and sign-in | **Pass**: account created through the setup form, redirected to `/`; sign-in page renders. Per-PR data persistence across SHAs not exercised |
| 2 | Dashboard layout, artwork, navigation | **Pass** for rendering in live and reconstructed states; the reconstructed ring shows artwork |
| 3 | Discovery lists load and refresh | **Partial**: lists load empty in the live state; first visits trigger `POST /api/discovery/<name>/refresh` (200); no real data to refresh. Reconstructed lists render |
| 4 | Artist/album navigation and details | **Partial**: modal opens, shows 7 reconstructed tracks, at all five widths; no real album data |
| 5 | Settings load, save, reload | **Skip** for save and reload (nothing saved). Load: **Fail** on B1 (502 on the ListenBrainz read) |
| 6 | Get/request state | **Skip**: no Get was triggered |
| 7 | Acquisition status | **Pass** for rendering the empty state (live) and 7 reconstructed statuses; live updates and reconnect not tested |
| 8 | Error/recovery states | **Skip** (not exercised beyond B1 and B2 observed as-is) |
| 9 | Performance | Recorded in 9.5 |
| 10 | No unexpected console or server errors | **Fail** on B1 and B2; otherwise none. Server log: 1,060 x 200, 6 x 502 (B1), 1 x 405 (a `HEAD /login` from my own reachability probe) |

### 9.9 Screenshot inventory and location

Per the owner's decision, **the screenshots are not in the repository**; this report is the only committed artifact. 91 PNGs were produced in the session workspace (`/tmp/claude-0/-home-claude/caca3a47-2bb4-5be5-9b93-5c19ed9df9ce/scratchpad/shots/`), which does not persist beyond the session. File names:

- `login-setup-<w>.png` and `login-signin-<w>.png` (10): login page, first-run and sign-in variants.
- `live-<page>-<w>.png` (40): Dashboard, Discover music, New releases, Personal Discoveries, Add to your collection, Artist Deep Dives, Acquisition status, Settings; `<page>` is `dashboard`, `discover`, `new-releases`, `personal`, `collection`, `deep-dives`, `acquisitions`, `settings`.
- `reconstructed-<page>-<w>.png` (35): the same pages except Settings.
- `reconstructed-album-modal-<w>.png` (5): modal, viewport capture.
- `cvd-swatches.png` (1): color-vision simulation render.

`<w>` is 1440, 1200, 900, 620 or 390. If the owner wants them kept, they must be copied out of the session workspace before it is discarded.

### 9.10 Decisions recorded (owner, 2026-10-18)

| ID | Decision | Outcome |
|---|---|---|
| D1 | Retire the 3D dashboard ring for a static tile strip | **Retire** (default) |
| D2 | Red as brand mark and error glyph | **Keep, with the red rule** (recommended); error and caution always use distinct glyphs |
| D3 | Vendored fonts and icon sprite | **Approve** (default) |
| D4 | Right rail for live acquisitions at 1440px and wider | **Not included** (default); revisit after Phase 5 |
| D5 | Global search scope | **Library-wide** (changes the page-scoped default). This needs a backend search endpoint, which is a contract proposal under roadmap section 6; none is written in this PR |
| D6 | Replace the cassette mark | **Keep until a replacement is supplied** (default) |
| Storage | Baseline screenshots | **Outside the repository** (default); report only is committed |

### 9.11 Limitations

Single browser (Chromium 141, headless) on Linux, not the owner's macOS setup; documented helper not used (9.2); Google Fonts blocked, so typography, FCP/LCP and font-swap shift are not representative (9.5); third-party modal icons blocked (B2); populated states are reconstructed from fictional fixtures; no real library, listening history or Get action; TTI is a heuristic; the CVD result is a model simulation; no screen reader, keyboard walk-through, or 360px capture; Settings tabs other than Navidrome not captured; screenshots are not persisted in the repository.

## 10. Redesign Phase 1 — foundations (tokens, self-hosted fonts, icon sprite)

Status: **implemented on `ui/phase-1-foundations`** (roadmap Phase 1, item list in `docs/REDESIGN_ROADMAP.md` section 4). Implemented: yes. Automated tests: run (10.5). Browser-tested: partial, see 10.6 and 10.9. Merged / published / deployed / runtime-verified: **no**. Roadmap items applied: `docs/DESIGN_SYSTEM.md` sections 4.1, 5, 10, 14 and 15 (D3). No layout change; no backend, API, auth or acquisition change.

### 10.1 What changed

- **Fonts.** Latin WOFF2 subsets from `@fontsource/*@5.3.0` (SIL OFL 1.1, licence files in `static/fonts/`) for Big Shoulders Display 700 and 800, Schibsted Grotesk 400, 500 and 600, and JetBrains Mono 400 and 500. Declared in `static/fonts/fonts.css` with `font-display: swap`. The display face (700) is preloaded by both HTML pages. The Google Fonts `@import` is removed from `static/app.css` and `static/login.css`. Total first-load font bytes across the seven files: **146,724 bytes** (budget 150 KB).
- **Icons.** `static/icons.svg`: 14 Lucide symbols from `lucide-static@1.59.0` (ISC, `static/vendor/lucide/LICENSE`). Generated by a script kept outside the repository. No template uses the sprite yet; that starts in Phase 2.
- **Tokens.** `:root` in `static/app.css` and `static/login.css` rewritten to the section 14 names and section 4.1 values. Scale, spacing, radius and motion tokens added (`--space-1`…`--space-8`, `--radius-chip`/`-control`/`-panel`, `--dur-fast`/`--dur`/`--dur-slow`, `--ease-out`, `--text-xs`…`--text-2xl`). `--caution` added as defined in section 4.1; no page uses it yet.
- **Login.** Hard-coded `#77796f`, `#191a1a` and `#f6e8a8` replaced with tokens. Input borders are `--edge-strong` (control boundary).
- **Tests.** Four assertions in `tests/test_acquisition_ui_contract.py` and `tests/test_ui_keyboard_and_feedback_contract.py` changed from `var(--yellow)` / `var(--on-yellow)` to `var(--accent)` / `var(--on-accent)`. Nothing else in those assertions changed. New `tests/test_fonts_and_icons_ui_contract.py` (6 tests): no third-party font host in CSS or templates, both pages link the self-hosted stylesheet and preload only the display face, all seven faces ship with `swap` and stay within the budget, OFL licences present, sprite has exactly the 14 expected symbols, Lucide licence present.

### 10.2 Old-to-new token map (as applied)

| Old (`main`) | New | Count in `app.css` + `login.css` | Note |
|---|---|---|---|
| `--bg` | `--ink` | 3 | section 14 |
| `--chrome` | `--ink-rail` | 2 | section 14 |
| `--surface`, `--surface-raised`, `--surface-hover` | same names | — | new values (section 4.1) |
| `--border` | `--edge` (13) or `--edge-strong` (4 control rules + login input) | 18 | controls need 3:1 (section 4.1); dividers and containers are decorative |
| `--edge`, `--edge-strong` | same names | — | new values |
| `--text` | `--text` | — | same name, new value `#f4efe6` |
| `--muted`, `--subtle` | `--text-muted`, `--text-subtle` | 22, 7 | `--subtle` raised from `#94958b` to `#9c958a` (section 4.1) |
| `--yellow` | `--accent` | 47 | |
| `--on-yellow` | `--on-accent` | 7 | |
| `--red` | `--chart-red` | 8 | |
| `--green` | `--ok` | 4 | |
| `--radius` | `--radius-panel` | 3 | `6px`, unchanged value |
| `--display`, `--body`, `--mono` | same names | — | families changed (section 5) |

### 10.3 Audit of the 22 single-purpose tokens from PR #194

| Token | Uses | Decision | Reason |
|---|---|---|---|
| `--chrome` | 2 | merged into `--ink-rail` | same role (header and sidebar ground) |
| `--surface-inset` | 4 | merged into `--surface` | section 9.7 puts inputs on `--surface` |
| `--surface-deep` | 2 | merged into `--ink` | recessed download well is the page ground |
| `--surface-well` | 3 | merged into `--surface-raised` | artwork placeholder and tag fill sit on a card (`--surface`), so the next step up is `--surface-raised` |
| `--edge-warm` | 1 | merged into `--accent-dim` | tinted card edge; same yellow family |
| `--yellow-bright` | 4 | renamed `--accent-hover` | hover state |
| `--yellow-pale` | 4 | merged into `--accent-hover` | the control border and hover fill were the same role |
| `--yellow-dim` | 3 | renamed `--accent-dim` | pending state border |
| `--on-yellow` | 7 | renamed `--on-accent` | text on accent fill |
| `--red-deep`, `--red-bright` | 0 | deleted | defined, never used |
| `--red-text` | 1 | renamed `--chart-red-text` | destructive glyph colour (section 4.1 text red) |
| `--red-text-hover` | 1 | merged into `--chart-red-text` | hover lift on a single glyph is decoration; the state is shown by its surface change |
| `--text-artist`, `--text-tag`, `--text-code`, `--text-chip`, `--text-placeholder` | 1, 1, 1, 2, 1 | merged into `--text-muted` | all were muted text between `--text` and `--text-subtle`; one muted step is enough |
| `--edge-tag` | 1 | merged into `--edge` | decorative divider |
| `--scroll-track` | 2 | merged into `--surface` | scrollbar track on the page surface |
| `--scroll-thumb` | 3 | merged into `--edge-strong` | scrollbar thumb is a control boundary, needs 3:1 |
| `--shadow-menu` | 1 | **kept** | section 7: the only shadow in the system; the test asserts its value |

Result: 22 tokens audited. 1 kept, 4 renamed, 15 merged, 2 deleted. The merges change some values slightly (for example `--text-chip` `#b7b8ae` becomes `--text-muted` `#b4ac9f`). Those changes are intended, and they appear in the computed-style comparison in 10.6.

### 10.4 Rendered-build comparison (purity of the remap)

Method: the same Playwright script was run against `main` (`origin/main` at `7b356a8`, extracted to a scratch directory with `git archive`) and against this branch, both served from isolated sandbox data directories on separate ports. At 1440px on the dashboard, every element's computed style was captured for nine properties (colour, background, border, font family and weight, size, radius, shadow, outline).

- Element count and tag/class sequence: **identical** (196 elements, same order). No markup or class change.
- Differences are only value differences, all traceable to the map above: colour and border-colour values from section 4.1 (for example `rgb(240,238,229)` becomes `rgb(244,239,230)`); background `#222424` becomes `#1c1a18` (`--surface`); control borders become `rgb(120,113,104)` (`--edge-strong`); accent `#e9c64a` becomes `#f5d33f`; font families change (section 5).
- No layout property (position, width, margin, padding, display) was captured because none changed in the diff. Layout was checked by overflow and screenshot instead (10.5).

### 10.5 Checks actually run (branch head: see the PR)

| Check | Result |
|---|---|
| `node --check static/app.js` | ok |
| `python -m compileall -q app static` | ok |
| `python -m unittest discover -s tests` before the new test file | 709 run, 4 failed on old token names; the 4 assertions were updated (10.1); re-run: 709 OK |
| `python -m unittest tests.test_fonts_and_icons_ui_contract -v` | 6 tests OK |
| `python -m unittest discover -s tests` with the new test file | see the final run recorded in the PR description |

### 10.6 Browser checks (isolated sandbox; not the owner's helper)

Servers: `uvicorn app.main:app` on `127.0.0.1:8101` (`main`) and `127.0.0.1:8102` (this branch), each with its own `NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` under a sandbox directory outside the repository, `SLSKD_URL=http://127.0.0.1:9`, empty key, Navidrome unconfigured. Browser: Chromium 141 through Playwright 1.56. Account created through the first-run form on the first width, then signed in through the same form at the other widths. Fresh data (no library), so populated states are **not** exercised.

| Width | Login | Dashboard: overflow / console / failed / http | Settings: overflow / console / http | External hosts (page requests) |
|---|---|---|---|---|
| 1440 | first-run; no overflow | none / 0 / 0 / none | none / 1 / `502 /api/settings/listenbrainz` (B1) | none (`main`: `fonts.googleapis.com`, `fonts.gstatic.com`) |
| 1200 | sign-in; no overflow | none / 0 / 0 / none | none / 1 / B1 | none |
| 900 | sign-in; no overflow | none / 0 / 0 / none | none / 1 / B1 | none |
| 620 | sign-in; no overflow | none / 0 / 0 / none | none / 1 / B1 | none |
| 390 | sign-in; no overflow | none / 0 / 0 / none | none / 1 / B1 | none |

- **Overflow:** no horizontal overflow at any of the five widths, on login, dashboard or Settings.
- **Errors:** the only console error on any width is the B1 `502` on Settings, which `main` also has. No failed requests. No `4xx` or `5xx` other than B1.
- **B2 (album modal third-party images):** not exercised. The modal needs library data, which the fresh sandbox does not have. Still present in code (`static/app.js`), unchanged in this PR.
- **Fonts:** all seven files are served from `/static/fonts/` with status 200. Big Shoulders 700 (preloaded), Schibsted 400 and 600, JetBrains 400 and 500 were fetched on the dashboard. Schibsted 500 was not fetched because no page element uses that weight on the dashboard, so the face stays unloaded; this is correct browser behaviour, not a missing file.
- **Weight mapping (rendering change):** 9 display elements that asked for 600 now render with the 700 face, and 5 body elements that asked for 700 render with the 600 face, and mono 700 renders with 500. The budget excludes faces not shipped (Big Shoulders 600, Schibsted 700, JetBrains 700). This is a visible weight change on those elements; it is intended for the budget and is listed as a limitation.
- **Contrast (rendered):** 19 distinct foreground/background text pairs measured with the page's computed colours and effective backgrounds, on login, dashboard and Settings at 1440px. Lowest 6.30:1 (`--text-subtle` on `--ink`). All pass AA (4.5:1 normal text, 3:1 large). **Not** measured on the rendered build: red (`--chart-red-text`), caution and ok states, the Get states, acquisition rows and the album modal, because those states did not render with empty data. Their values were measured by token arithmetic in Phase 0 and have not been re-measured.
- **Footer clipped under the rail at 1440px:** still present, as recorded in the handoff. Not investigated in this PR.
- **Browser background traffic:** Chromium itself tried to reach Google update and safety hosts during launch (shown in the egress proxy log). These are not page requests and are not counted above.

### 10.7 Screenshots

Before and after captures (login, dashboard, Settings at five widths, each build) are in the session scratch directory, not the repository, following the owner's decision in section 9.10. They are reconstructed-state captures on empty data. Typography differs from the Phase 0 captures on purpose: the self-hosted fonts render here, where Google Fonts did not.

### 10.8 Impeccable

Status: see the PR description. Applied and rejected guidance is recorded there, because `DESIGN.md` is generated from the built system at the end of Phase 1.

### 10.9 Limitations

- Fresh data only: no populated Discover, Dashboard tiles, acquisition rows, album modal or Get states were rendered. Reconstructed fixtures were not built in this PR.
- Keyboard walk-through, screen reader and a five-width keyboard pass were not run.
- Chromium 141 on Linux only.
- Literal colours that predate the token system still exist in component rules (for example `#353124`, `#292b28`, `#333531`, `#2a2c29`, `#c8c8bd`, `#ffe477`, `#9a8127`, `#000`). They are component work for Phases 2–6 and were not remapped here, so no token was invented for them.
- Radius literals (`2px`, `4px`) and spacing literals across the stylesheet still use values rather than `--space-*`/`--radius-*`. New tokens are defined and used where a value was already a token; full adoption happens per component.
- Type-scale tokens (`--text-*`) are defined but not yet applied to elements.
- Display 600 and body/mono 700 weights render with the nearest shipped face (see 10.6).
- Owner blockers unchanged: B1 (backend-owned 502), B2 (third-party images in the album modal, owner decision still needed: vendor brand marks with licences, or use text links; not decided here, left for Phase 6 unless the owner asks earlier).

## 11. Redesign Phase 2 — shell, slice A (left rail)

Status: **implemented on `ui/phase-2-shell-rail`; merged in PR #355** (roadmap Phase 2, item "left rail with icons and three groups, 232px; Acquisitions count as a numeral"). Implemented: yes. Automated tests: run (11.4). Browser-tested: partial, sandbox only (11.5). Merged: **yes** (PR #355, merge `981c244`, head `8817691`). Published / deployed / runtime-verified: **no**. Design-system sections applied: 9.3 (rail item, count as numeral), 10 (sprite icons), 13 (no eyebrow or mono label). No backend, API, auth or acquisition change.

### 11.1 What changed

- **Rail markup** (`app/templates/index.html`): seven items keep their accessible names, routes and `data-page` values. Each gets a decorative sprite icon from `static/icons.svg` (`layout-dashboard`, `download`, `compass`, `calendar-plus`, `user-round`, `library`, `mic-vocal`). Items sit in two `role="group"` containers with visible labels: **Collection** (Dashboard, Acquisitions) and **Discover** (Recommendations, New releases, Personal Discoveries, Add to your collection, Artist Deep Dives).
- **Width:** one token, `--rail-w: 232px`. Main and footer offsets are derived from it (`calc(var(--rail-w) + 34px)` at desktop, `+ 18px` at 1200px). At 900px the rail is 200px, not 232px, to fit an icon plus label (see 11.3).
- **Footer:** the footer sits outside `<main>`, so it had no rail offset and its text ran under the fixed rail at 1440px (the Phase 1 limitation recorded in 10.6). It now takes the same offset as main.
- **Count:** the Acquisitions count is plain tabular text (`.nav-count`), not a pill. It stays hidden at zero, as before.
- **Removed:** the mono `YOUR COLLECTION` heading (10px mono, the eyebrow pattern the craft floor refuses). Replaced by the two group labels at 12px body text.
- **Indicator:** the goo blob is still present in this slice. It is replaced in slice B with the responsive rail. Its height is 44px to match the new row height, and `moveNavBlob` now finds the active item inside the groups (`static/app.js`).
- **Touch targets:** rail rows are 44px tall (`min-height`), up from about 40px.

### 11.2 Decisions taken without the owner (state these in review)

1. **No System group.** The surface brief names three groups. Settings and Log out already live in the header menu (section 5m, PR #327), and `tests/test_header_menu_ui_contract.py` asserts they are not in the rail. Adding Settings back to a System group would reverse that merged decision, so the rail has two groups. Whether a third group returns is an owner call; it is recorded as open in `docs/REDESIGN_ROADMAP.md` Phase 2.
2. **Collection before Discover.** The brief lists Discover first. Dashboard is the landing page, so its group leads. Order change only; no item moved.
3. **Terminology kept.** The discover page is "Recommendations" in the rail, as users know it. The design system's shorter "Discover music" name is not adopted here, to avoid a silent rename.
4. **Interim 900px width.** A 184px rail clips "Recommendations" once an icon is added. The 900px rule is widened to 200px in this slice. Slice B replaces that band with an icon-only rail, so the 200px value is transitional.

### 11.3 Problems found by rendering, not by reading

- At 900px, with icons added at 184px, "Recommendations" ran past the active highlight. Fixed by the 200px interim width above.
- The footer clip at 1440px (Phase 1 limitation). Fixed by the offset above; verified in the 1440 render.

### 11.4 Checks actually run (on the branch, before the PR head was pushed)

| Check | Result |
|---|---|
| `node --check static/app.js` | ok |
| `python -m compileall -q app static` | ok |
| `python -m unittest tests.test_shell_rail_ui_contract tests.test_header_menu_ui_contract tests.test_fonts_and_icons_ui_contract` | 37 tests, OK |
| `python -m unittest discover -s tests` | 726 tests, OK |

The new `tests/test_shell_rail_ui_contract.py` (11 tests) is additive: no existing assertion was changed or deleted. It pins the accessible names and routes of the seven items, the two named groups, that each icon names an existing sprite symbol, the decorative icon attributes, the `--rail-w` token and the footer offset, the absence of the old eyebrow, the numeral count, the blob selector, and the 44px row height.

### 11.5 Browser checks (sandbox, not the owner's helper)

`~/navi-librarian-test/test-pr.sh` is **not present** in this container, so the documented helper was not run. Instead: `uvicorn app.main:app` on `127.0.0.1:8101` with `NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` under a sandbox directory outside the repository, `SLSKD_URL=http://127.0.0.1:9`, empty key. Chromium 141 via Playwright. Fresh data (no library); the account was created through the setup route.

| Width | Dashboard, Recommendations, Acquisitions: overflow / console / failed / external |
|---|---|
| 1440 | 0 px / none / none / none |
| 1200 | 0 px / none / none / none |
| 900 | 0 px / none / none / none |
| 620 | 0 px / none / none / none |
| 390 | 0 px / none / none / none |

- **Settings** (opened through the header menu) at all five widths: no overflow; one console error, `502` on `GET /api/settings/listenbrainz`. That is **B1**, pre-existing on `main` and recorded in 10.6. A second, unrelated `failed` entry (`/api/acquisitions/stream`) came from the capture script navigating away from Acquisitions while its stream was open. It is not an app error.
- **Keyboard:** from the skip link, Tab reaches the gear, then each of the seven rail items in order. Every stop shows a 2px solid outline. Every rail row measured 44px tall.
- **Active-download count:** the sandbox has no jobs, so the count was **reconstructed in the DOM** (set to `3` and un-hidden in the page) for a screenshot only. The numeral renders as plain text. This is labelled reconstructed, not a real acquisition state.
- **Screenshots:** before captures (dashboard, five widths) and after captures (dashboard, recommendations, acquisitions, five widths) are under `/tmp/claude-0/shots/` in the working container, not in the repository. They are not attached to the repository.
- **Contrast:** the rail labels use `--text-muted` and `--text-subtle` tokens already measured in Phase 1 (10.6). The active row is `--accent-dim` fill with `--text`. The active row was not separately re-measured.

### 11.6 Impeccable

- **Read before editing:** the surface brief (`.impeccable/surfaces/app-templates-index-html.md`), the product brief and design system (`docs/DESIGN_SYSTEM.md` 9.3, 10, 11, 13), and the craft-floor reference. The `docs/UI_BACKLOG_EXECUTION.md` protocol points at `.pi/skills/impeccable/reference/`, which is **not in this repository**; the same guidance was read from the plugin skill.
- **Applied:** icons from one drawn library in one stroke weight (sprite symbols, not Unicode glyphs); group labels as text, not an eyebrow or a numbered section; a single width token; the footer given the same offset as main; the count as a numeral rather than a pill.
- **Rejected:** a third System group (see 11.2); changing the discover label to the brief's "Discover music"; any new motion in this slice (the blob and its spring are slice B's job, and are not extended here).
- **Detector:** the design hook ran on the template and stylesheet edits. On `index.html` it reported two findings, both **pre-existing on `main`** and outside this slice: `broken-image` (the album modal `<img id="albumModalArtwork">` has no `src` until JS sets it) and `tiny-text` (sub-12px text). Both are left standing for their own items. The stylesheet scan reported no issues.

### 11.7 Limitations

- Fresh data only. The rail count is reconstructed, not observed from a real job.
- Two groups, not three (11.2).
- Top-bar search and breadcrumb are not in this slice. The breadcrumb is not started. The search is blocked by D5 (library-wide scope needs a backend contract; see `docs/DESIGN_SYSTEM.md` section 15 and `docs/REDESIGN_ROADMAP.md` section 9).
- The 620px and below bar is still the horizontal scroller with labels (it now shows icons too). The bottom tab bar and icon-only 620–900 rail are slice B.
- Chromium only. No screen-reader pass. No reduced-motion check of the blob, which is unchanged in this slice.
- The documented helper was not run (11.5).

### 11.8 Next action

Slice B: icon-only rail between 620 and 900px, bottom tab bar under 620px, goo filter and spring easing removed, indicator as a `translateY` bar. Owner input still needed on D5 before the top-bar search.

## 12. Redesign Phase 2 — shell, slice B (responsive rail)

Status: **implemented on `ui/phase-2-shell-slice-b`; merged in PR #360 (merge `d789f45`, head `7f2283c`).** Owner ran the manual test and approved the merge. Roadmap Phase 2, responsive rail: icon-only rail 621–900px, bottom tab bar under 620px, goo filter and spring easing removed, blob replaced by a `translateY` indicator. Design-system sections applied: 9.3 (rail item, active = 3px bar plus `--surface-raised`), 11 (motion: indicator `transform` on `--dur` / `--ease-out`, reduced motion ends at once), 12 (landmarks, skip link, 44px targets, focus).

Settings and Log out: already in the header menu (PR #327). No placement change in this slice; `tests/test_header_menu_ui_contract.py` still asserts the rail excludes them.

### 12.1 What changed

- `app/templates/index.html`: the SVG goo filter and the blob layer are removed. A single `.nav-indicator` bar sits in `.nav-list`. Each rail button gets a `title` (tooltip for icon-only use). Names, groups, routes and `aria-label`s are unchanged.
- `static/app.css`: `.nav-indicator` slides with `transform` only. `nav button.active` uses `--surface-raised`. At 621–900px the rail is 72px (`--rail-w`), labels and group names are visually hidden but stay in the accessibility tree, and the count is absolutely positioned on the icon. Under 620px the rail becomes a bottom tab bar (icon above label, `min-height` 56px, `env(safe-area-inset-bottom)`, horizontal scroll when tabs overflow), and the main content offset is recomputed.
- `static/app.js`: `moveNavBlob` renamed to `moveNavIndicator`, same translateY logic on `.nav-indicator`.
- `tests/test_shell_rail_ui_contract.py`: the blob-locating assertion now checks the indicator (reason: blob removed). The dashboard active-markup regex allows the new `title` attribute. New tests cover goo/spring removal, transform-only motion with reduced-motion handling, the 621–900px icon-only rule, the under-620px tab bar, and tooltips. No assertion was removed.

### 12.2 Verification (head `7f2283c`, PR #360)

- `node --check static/app.js`: pass. `python -m compileall -q app static`: pass.
- `python -m unittest discover -s tests`: 732 tests, OK (after `pip install -r requirements.txt --break-system-packages`).
- Rendering: Playwright (Chromium at `/opt/pw-browsers/chromium`) against the local app on sandbox data paths (`NAVIDROME_LIBRARIAN_DATA_DIR` outside the repo, `SLSKD_URL=http://127.0.0.1:9`). Widths 1440, 1200, 900, 620, 390. Measured: no horizontal page overflow at any width; rail 232px at 1440/1200, 72px at 900, bottom bar 64px tall at 620/390; indicator top matches the active button's top at 1440, 1200 and 900; rail and tab targets ≥44px (tab buttons 63px); zero console or page errors on the dashboard. Keyboard: Tab order is skip link, header settings toggle, Dashboard, Acquisitions, Recommendations, New releases, Personal Discoveries, Add to your collection, Artist Deep Dives, then Shuffle picks.
- Not run by the author: the documented `~/navi-librarian-test/test-pr.sh` helper (not present in the author environment), so the TEST_PLAN manual checklist items 3–10 (discovery loads, album detail, settings save, Get, acquisitions, error states) were **not** run and are recorded as skips. Populated states are not verified: there is no library, so the dashboard shows its empty state.
- Impeccable: `impeccable detect` and `/impeccable critique` were not run in this session; the guidance applied is limited to the design-system rules listed above. The web-design-guidelines review was not run either. CI on `7f2283c`: compile, test-and-build, container-smoke and validate-container all succeeded.
- Manual test: the owner reported the manual test done and approved the merge (PR thread, 2026-10-18). Which checklist items the owner covered was not recorded in this document.

### 12.3 Known limits

- Under 620px the seven tabs (with two-line labels) exceed the screen width, so the bar scrolls sideways. A shorter label set or a "More" tab is an owner decision, not made here.
- B1 (`GET /api/settings/listenbrainz` returns 502 with no username) is backend-owned and unchanged. B2 (third-party images in the album modal) is still open.
- Top-bar search (D5) and a third System group remain out of scope.

## 13. Redesign Phase 3 — Discover music as ranked rows (`ui/phase-3-discover-music`)

Roadmap item: Phase 3, first item (Discover music). Design system sections applied: 9.4 (ranked row), 8 (rank numerals and truthfulness), 9.6 (skeleton, empty, error), 12 (accessibility floor). Base: `origin/main` at `b4bc707` (the brief named `45f2f4e`; main had advanced).

**Implemented** (PR #365). `#recommendationCards` is an ordered list of `article.ranked-row` rows instead of the card grid. Each row: numeral (display face, red text), 64px artwork, title and artist, plain-text metadata, Get and dismiss as separate controls. The whole row opens the album modal, as before. Numerals appear only when the sort basis is a real order: server order ("Recommended order"), complete `discovery_score`, or complete `lastfm_listeners`. Any sort with missing values, and the A–Z sort, shows no numerals, and the count line names the basis. Loading shows opacity-pulse skeleton rows; a failed generation is shown in the count line as well as the diagnostics panel.

**Unchanged.** Get state machine and `searchAlbum`, dismiss storage key and filtering, search/category/sort controls and their order, modal, refresh behaviour, endpoints, schemas and server code. No backend, API or dependency change.

**Contract tests.** `tests/test_recommendations_ui_contract.py`: new `RankedRowContractTests` class (additive). `tests/test_classics_card_ui_contract.py`: `test_no_other_section_gets_the_title_clamp` changed from exactly one `-webkit-line-clamp` to exactly two, because the ranked-row title also clamps to two lines; the test still rejects any third clamp. The classics tooltip guard is untouched (the row title uses `setAttribute`, so the single `title.title =` guard still holds).

**Impeccable.** Loaded `impeccable:impeccable`; ran `context` and `critique` on the page (findings in the PR). Applied: row composition from 9.4, token-based type sizes for metadata (`--text-xs`, `--text-sm`), transform-only hover bar, reduced-motion rules, 44px get and dismiss targets. Rejected: a sparkline or score ring (not in the system), a pill per metadata value (section 13 anti-pattern; genres are plain text), a stronger category chip (kept as plain text). The `999px` pill radius on Get is the 9.2 "pill with label in rows" rule, not a new radius. `impeccable detect` ran on the three changed files; its remaining font-size and radius notes are the existing values across `static/app.css`, and its `tiny-text` and `broken-image` notes on `index.html` are on the pre-existing modal artwork image and existing 11px text, not on this change. Not changed.

**web-design-guidelines.** The skill's source URL returned a summary, not the full rule list, so the review was against the summarized categories (focus, reduced motion, truncation, tabular numerals, labelled icon buttons, live region). Nothing from it was applied beyond what the design system already requires.

**Checks run on the working tree before the PR head was pushed:**
- `node --check static/app.js`: OK.
- `python3 -m compileall -q app static`: OK.
- `python3 -m unittest discover -s tests -v`: OK, 745 tests, 0 failures.
- `pip install -r requirements.txt --break-system-packages`: OK.

**Browser checks** (sandbox, not the documented helper): `~/navi-librarian-test/test-pr.sh` is not present in this container, so `uvicorn app.main:app` was run on `127.0.0.1:8189` with `NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR`, `SLSKD_DOWNLOADS_DIR` under a directory outside the repo, `SLSKD_URL=http://127.0.0.1:9`, empty key, Navidrome unconfigured. Chromium from `/opt/pw-browsers/chromium`, driven by Playwright. Data was fresh (no library); the six albums were injected through `renderRecommendations` as **reconstructed DOM**, labelled as such.

| Check | Result |
|---|---|
| Horizontal overflow at 1440, 1200, 900, 620, 390px | Pass (0px at all five) |
| Rendered rows, long album and artist names, missing artwork, missing score | Pass (screenshots only, reconstructed DOM) |
| Sort basis labels for original, score, popularity, artist | Pass |
| Keyboard: row focus, Get is a separate stop, dismiss is a separate stop, Enter opens modal, Escape returns focus to row | Pass |
| Failed generation shows the error in the count line | Pass (502 from a route stub) |
| Console | One expected error: the stubbed 502 |
| Loading skeleton rows rendered | Not checked visually (the loading state was only reached between click and the stubbed 502) |
| Get request state machine against a live server | Skip (no Navidrome configured; Get was not clicked) |
| Live library, populated states, real artwork | Skip (fresh data, no library) |
| Screen reader | Skip (not run) |
| Before/after screenshots | Captured in `~/rt/shots/` in the sandbox (`before-*.png`, `after-*.png`); not uploaded to the PR |

**Limitations.** Artwork in the reconstructed DOM is absent, so the artwork tile is the placeholder colour only. `--text-sm` and `--text-xs` resolve to rem values; a browser with a non-default root size changes them proportionally. The modal artwork `<img>` without a `src` (pre-existing) is still flagged by the detector.


## 14. Redesign Phase 3 — New releases with a release-date column (`ui/phase-3-new-releases`)

Roadmap item: Phase 3, second item (New releases). Design system sections applied: 8 (row "New releases": rows ordered by release date, date column in place of numerals; truthfulness rules), 9.4 (ranked row), 9.6 (skeleton, status line, empty and error states), 9.2 (Get kept), 12 (accessibility floor). PR #369 (head `dc7f877`). Base: `origin/main` at `de340b7` (PR #365 merge). Confirmed with `gh api repos/abucalip/navi-librarian/commits/main`.

**Implemented.** `#newReleasesCards` is an ordered list (`ranked-list`) of the shared `article.ranked-row` rows. `buildRecommendationRow` takes an optional `options` argument instead of being forked: `releaseDate` puts a date column in the leading position, `meta` replaces the Discover metadata lines, and `onDismiss` / `onDismissArtist` route to the existing `sendFeedback` endpoint. Discover music calls the function with no options and produces the same DOM as before. The date comes from the API's `first_release_date` (returned by `discovery_new_releases.build_new_release_response`, which already sorts newest first). `releaseDateParts` accepts only `YYYY-MM-DD`, `YYYY-MM` or `YYYY`; anything else leaves the column empty. No date or order is invented. The status line names the sort basis: "Sorted by release date, newest first". No numerals on this list. The year badge is omitted on release rows because the date column shows the year. The date is also added to the row's accessible name, because the row is a button. Skeleton rows show while loading and are removed before rows render, and on failure. The empty-state copy is unchanged.

**Unchanged.** Load and Refresh buttons and `loadDiscovery` request flow, the endpoint and its parameters, the empty-state copy, the Get state machine (`searchAlbum`, `POST /api/acquire`, `ok:false` handling), the dismiss and dismiss-artist feedback calls, the row-open modal and keyboard handling, and all server code. No backend, API or dependency change. No new clamp, so the classics clamp test is untouched.

**Contract tests.** New file `tests/test_new_releases_ui_contract.py` (`NewReleasesRowContractTests`, 14 source checks). `tests/test_recommendations_ui_contract.py` and `tests/test_classics_card_ui_contract.py` are unchanged. Their assertions still hold against the shared builder.

**Impeccable.** Ran `impeccable detect` on `static/app.css`, `static/app.js` and `app/templates/index.html`. None of the findings fall on lines this PR added. Pre-existing findings: the album-modal `<img>` with no `src` (populated by JS on open), 11px text in `index.html`, the `.card-art::after` stripe, the 999px pill radius on Get, and the 28px and 18px sizes on `.rank-numeral` and `.ranked-row h3` from PR #365. The `.ranked-row::before` 3px stripe is the hover bar DESIGN_SYSTEM 9.4 specifies, so it is kept on purpose. The `/impeccable critique` skill was not run as an interactive pass in this session. Instead I reviewed the 1440, 620 and 390px renders by eye against 8 and 9.4.

**web-design-guidelines.** The skill's source URL returned a condensed summary, not the full rule text, so this review checked against the categories it lists: focus visibility, reduced motion for the skeleton, truncation and `min-w-0`, tabular numerals on the date, labelled controls, live status region, and anchors versus buttons. Nothing in the summary flagged the changed lines. The full rule list was not checked.

**Checks run on the working tree (before the PR head was pushed):**
- `node --check static/app.js`: OK.
- `python3 -m compileall -q app static`: OK.
- `pip install -r requirements.txt --break-system-packages`: OK.
- `python3 -m unittest discover -s tests -v`: OK, 760 tests, 0 failures (one new test failed on a wrong literal during writing; fixed before this run).

**Browser checks (reconstructed DOM, sandbox servers).** The documented helper `~/navi-librarian-test/test-pr.sh` is not present in this container, so uvicorn was run by hand on `127.0.0.1:8091` (`origin/main`) and `127.0.0.1:8092` (this branch). Both used sandbox paths outside the repo (`NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR`, `SLSKD_DOWNLOADS_DIR`), `SLSKD_URL=http://127.0.0.1:9`, and no slskd key. The owner account was created through `POST /api/auth/setup`. Playwright ran against Chromium 1194. The list response, `POST /api/discovery/feedback` and `POST /api/acquire` were intercepted with a fixture. The fixture is **reconstructed**: four albums with dates `2026-03-14`, `2025-11`, `2025` and missing. No real library, no MusicBrainz data, no artwork.

| Check | Result |
|---|---|
| Horizontal overflow at 1440, 1200, 900, 620, 390px | Pass (scrollWidth = innerWidth at all five) |
| Date column shows API dates in three shapes; missing date leaves the column empty | Pass |
| Numerals on the list | Pass (0 at all widths) |
| Touch targets for Get, × and Dismiss artist at 390px | Pass (none under 44px) |
| Title truncation (two lines) at 620 and 390 | Pass (screenshots) |
| Loading: "Loading…" with six skeleton rows, cleared on response | Pass (screenshot taken while the response was held) |
| Error (HTTP 500): rows cleared, server message in the status line | Pass |
| Sort basis in the status line | Pass ("4 items · Sorted by release date, newest first") |
| Keyboard: focus row, Tab order Get → × → Dismiss artist → next row | Pass |
| Dismiss (×) sends `action: "dismiss"` to the existing feedback endpoint; before build sends the same body | Pass (parity) |
| Get: `ok:false` → failed state; `ok:true` → requested state | Pass (both builds the same) |
| Console and network | One expected error (the intentional 500 from the error check). No other errors or failed requests |
| Row-open modal and Escape | Skip (not run in this harness; the modal path is untouched code) |
| Screen reader | Skip (not run) |
| Live Get against the server | Skip (`/api/acquire` was mocked; slskd disabled; no download started) |
| Real library, real artwork, populated MusicBrainz data | Skip (not available in the sandbox) |

Screenshots: before (`origin/main`) and after (this branch), each at 1440, 1200, 900, 620 and 390px, plus loading and error at 1440. Copied to `/mnt/project-files/phase-3-new-releases/screenshots/`.

**Limitations.** Renders use the reconstructed fixture. The fixture's artwork tiles are blank. The bottom tab bar still scrolls sideways under 620px (existing follow-up, not this PR). The `Dismiss artist` button is text, so its width depends on the label. On a narrow phone it fits beside Get and × in the sandbox renders. Long localized labels were not tested.

**Next action.** Owner review of this PR's before and after screenshots, then a manual pass on the exact head SHA using the helper once it is restored.
