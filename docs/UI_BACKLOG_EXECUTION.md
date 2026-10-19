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

Roadmap item: Phase 3, second item (New releases). Design system sections applied: 8 (row "New releases": rows ordered by release date, date column in place of numerals; truthfulness rules), 9.4 (ranked row), 9.6 (skeleton, status line, empty and error states), 9.2 (Get kept), 12 (accessibility floor). PR #369, merged as `68fa6fb` on 2026-10-18 (head `bc3eefe`; not deployed). Base: `origin/main` at `de340b7` (PR #365 merge). Confirmed with `gh api repos/abucalip/navi-librarian/commits/main`.

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

**Next action.** Manual pass on the merged head against the documented helper once it is restored, then Phase 3 item 3 (Personal Discoveries).

## 15. Redesign Phase 3 — Personal Discoveries as ranked rows (`ui/phase-3-personal-discoveries`)

Roadmap item: Phase 3, third item (Personal Discoveries). Merged: PR #372 as `f108bce`, follow-up PR #373 as `fc656b9`, both 2026-10-18; not deployed. Design system sections applied: 8 (truthfulness rules, rule 2 for an unordered-by-score list: muted position, no red numeral), 9.4 (ranked row), 9.6 (skeleton, status line, empty and error states), 9.2 (Get kept), 12 (accessibility floor). Base: `origin/main` at `7d4f7a8` (PR #369 merged as `68fa6fb`, docs PR #371 merged). PR #372 (head `d476990` at open; this docs commit adds the link only). Not merged, not deployed.

**Order is the real question.** The personal list is built in `navidrome_server.py` from `allocation.selected_candidate_ids`, which is the allocator's selection order (category quotas and diversity slots), not a `discovery_score` sort. Every personal item does carry a `discovery_score` (`discovery_recommendation_payload.py` always sets it), but that is not the served order, so a numeral would imply a ranking the API did not return. Rows therefore show a muted position (`rank-numeral is-index`, `--text-muted`) and no red numeral, and the status line says "Engine order, not ranked by discovery score". If the server later returns a score-ordered list, the numeral can be enabled with a labelled sort basis, as Discover music does.

**Implemented.** `#personalCards` is now `ranked-list`. `buildPersonalRow` calls the shared `buildRecommendationRow(item, index + 1, {indexed, meta, onDismiss, onDismissArtist})`, so there is no fork. Metadata lines are the category, the API's `reason`, and the Last.fm playcount, each shown only when returned. Dismiss and dismiss-artist call `sendFeedback` with the `personal` list name, which keeps the server's dismiss rules. Loading shows six skeleton rows and removes them before rows render, and on failure. A shared `rankedRowList` flag replaces the New releases-only checks, so both lists use one path.

**Changed behaviour (disclosed).** The old personal editorial card lazily loaded an artist bio for cards whose reason was the "Genre tags connect this artist…" line. The shared row does not do that, the same as Discover music and New releases rows already. The bio fetch (`/api/artist-bio`) is no longer triggered from this list. The album modal is unchanged. Restoring the bio on ranked rows would need a new option on the shared builder, so it is left for a follow-up decision. The old card's category tag is now plain text in the metadata column.

**Unchanged.** Load and Refresh buttons, the status line element, `loadDiscovery`'s request (`/api/discovery/personal?count=30&nonce=…`), the feedback endpoint, the Get state machine (`createGetButton`), the row-open modal (`makeAlbumCardInteractive`), the empty-state copy, and all server code. No backend, API or dependency change. No new endpoint or field was needed, so no contract proposal is required.

**Tests.** New `tests/test_personal_discoveries_ui_contract.py` (`PersonalDiscoveriesRowContractTests`, 10 source checks). `tests/test_new_releases_ui_contract.py` had three assertions on the exact `new_releases`-only skeleton and clear lines. They now check the shared `rankedRowList` flag, with the same behaviour. No behavioural assertion was removed.

**Checks run on the branch head.**
- `node --check static/app.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `python3 -m pip install -r requirements.txt --break-system-packages`: installed.
- `python3 -m unittest discover -s tests -v`: 771 tests, OK.
- `python3 -m unittest tests.test_personal_discoveries_ui_contract tests.test_new_releases_ui_contract tests.test_recommendations_ui_contract -v`: 40 tests, OK.

**Browser checks.** Not run through the `~/navi-librarian-test/test-pr.sh` helper, which is not present in this session. Instead I ran two isolated servers from one sandbox (`NAVIDROME_LIBRARIAN_DATA_DIR` per tree, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` in `sandbox/`, `SLSKD_URL=http://127.0.0.1:9`, no Navidrome configured). One tree is `origin/main`, one is this branch. The personal endpoint was answered by Playwright with reconstructed fixture data, so the DOM and layout are real but the recommendations and artwork are not. This section states it; the PNGs themselves carry no label. Results are in `/mnt/project-files/phase-3-personal-discoveries/screenshots/render-results.json`.
- Widths 1440, 1200, 900, 620 and 390: rows render as `ranked-row`, `overflowX` is 0 at every width, every button in the list is at least 44px on the branch (on main, 10 buttons were under 44px in the old card grid), and the console shows no errors on the branch. On main the console was also clean.
- Numerals: five muted `01`–`05` on the branch, computed colour `rgb(180, 172, 159)` (the `--text-muted` value), no red.
- Loading: six skeleton rows and "Loading…" while the response is delayed; both cleared when rows arrive (`branch-loading-1440.png`).
- Error: a 502 clears all skeletons and rows and shows the server message (`branch-error-1440.png`). The browser logs the 502 as a console error, which is the intended failure.
- Dismiss: clicking × posts `action: dismiss` with the artist, album and item metadata to `/api/discovery/feedback`, then reloads the list.
- Keyboard: Tab order on each row is row link, Get, Not for me, Dismiss artist. Enter on the row opens the album modal and Escape returns focus to the row.
- Not run: a real Get request (the sandbox has no acquisition path and the brief forbids destructive acquisition), real artwork, a real personal list, and the full manual checklist against a PR head SHA.

**Impeccable.** `impeccable detect` ran through the edit hook on `app/templates/index.html` and `static/app.css`. Its findings on `index.html` are on lines this PR did not touch: the album-modal `<img>` with no `src` (`origin/main` line 269) and the existing `11px` text. `app.css` had no findings. A separate `/impeccable critique` pass was not run in this session. The brief's direction was applied by reusing the shared row, not re-rolling it. `/impeccable document` is not due until Phase 7.

**web-design-guidelines.** The skill fetched the full rule list. It was checked against the changed lines: `aria-live="polite"` on the status line, `aria-hidden` on the decorative index, reduced-motion disables the skeleton pulse (`app.css` line 556), no `transition: all` or `outline: none`, no `...` in new strings, and text truncation and `min-w-0` from the shared row. No new findings on the changed lines.

**Known limitations.** Artist bio lazy load not carried over (see above). Engine order is not a score order, so the list has no ranking numeral. The fixed mobile tab bar overlays the 390px element screenshot (existing; the open follow-up for seven bottom tabs under 620px still applies). The sandbox has no real library, so artwork and recommendations are reconstructed fixture data.

**Follow-up: artist bio on Personal Discoveries rows (`ui/personal-artist-bio`).** The bio that the old editorial card showed for "Genre tags connect this artist…" rows is restored on the ranked rows. `buildRecommendationRow` takes an `artistBio` option, and only Personal Discoveries sets it, when the reason matches that line. `attachArtistBio` reuses the existing `/api/artist-bio` request and cache, the shared intersection observer, and text-only rendering. Discover music and New releases rows are unchanged. Sandbox check on a branch server: only the matching row requested a bio, the paragraph showed in muted text, and the console had no errors. Unit suite: 774 tests, OK. The earlier "changed behaviour" note above is superseded by this follow-up.

## 16. Redesign Phase 3 — Add to your collection as ranked rows (`ui/phase-3-add-to-collection`)

Roadmap item: Phase 3, fourth item (Add to your collection, the Classics list). Design system sections applied: 8 (rows with acquisition focus, Get prominent; rule 2 for an order that is not a score ranking: muted position, no red numeral, basis named in the status line; rule 4, no numeral derived from data the API does not return), 9.2 (Get state machine kept), 9.4 (ranked row), 9.6 (skeleton, status line, empty and error states), 12 (accessibility floor). Base: `origin/main` at `31ef78a` (PR #374 merged). PR #375, merged as squash `5c9e3e9` (head `2a70386`) on 2026-10-18. Not deployed.

**Endpoint and fields.** The page uses `GET /api/discovery/classics?count=100&nonce=…` (unchanged) and the feedback endpoint `POST /api/discovery/feedback` with `dismiss` and `dismiss_artist`. Fields read: `artist`, `album`, `discovery_type` / `discovery_category`, `reason`, `anchor_artist`, `lastfm_playcount`, `year`. No endpoint or field was added or invented. No contract proposal is needed.

**Why no numerals ranking.** The server sorts candidates by `exploration_score`, which includes random jitter, and the Load albums control rotates the list on the client. The order is therefore not a stable ranking, so rows show a muted position (`rank-numeral is-index`, `--text-muted`), not a red numeral. The status line says "Picked for exploration, not ranked by score".

**Implemented.** `#classicsCards` is now `ranked-list`. `buildClassicsRow` calls the shared `buildRecommendationRow(item, index + 1, {indexed, artistBio, meta, onDismiss, onDismissArtist})`, so there is no fork. Metadata lines are the category, "Similar to" the anchor artist, the reason (hidden when the artist bio shows, as the card did), and the Last.fm playcount. Dismiss and dismiss-artist still go to the server feedback endpoint with the `classics` list name; the shared row's local dismiss is not used here. The artist bio follows the card's connection-reason rule and the existing `/api/artist-bio` cache. Loading shows six skeleton rows (the `rankedRowList` flag now includes `classics`) and clears on response and on failure. The classics-only title tooltip line and the `#classicsCards .card h3` clamp were removed; the shared row's `.ranked-row h3` provides the two-line clamp.

**Unchanged.** Load albums and Refresh buttons, the status element, `loadDiscovery`'s request, pool size (100), the 30-item cap and three-per-artist cap, the rotate shuffle, the auto-refresh path, the empty-state copy, the Get state machine (`createGetButton`, pending until the server answers), the row-open modal, and all server code. No backend, API or dependency change.

**Behaviour changes (disclosed).**
- The title tooltip is now the album name alone, not "album (year)". The year stays visible in the row next to the title.
- Rows show a muted position number (01–05) that the card did not show.
- Dismiss artist and the × control are now 44px targets (the card's were under 44px).

**Tests.** New `tests/test_add_to_collection_ui_contract.py` (`AddToCollectionRowContractTests`, 16 source checks). Narrow updates with reasons in `tests/test_classics_card_ui_contract.py` (the classics clamp moved to `.ranked-row h3`, so the clamp count is 1; the tooltip guard now checks the shared row; the container assertion now expects `ranked-list`), and the shared `rankedRowList` declaration assertion in `tests/test_personal_discoveries_ui_contract.py` and `tests/test_new_releases_ui_contract.py` now includes `classics`. No behavioural assertion was removed.

**Checks run on the branch head.**
- `node --check static/app.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install -r requirements.txt --break-system-packages`: installed.
- Focused: `python3 -m unittest tests.test_add_to_collection_ui_contract tests.test_classics_card_ui_contract tests.test_personal_discoveries_ui_contract tests.test_new_releases_ui_contract tests.test_recommendations_ui_contract -v`: 62 tests, OK.
- Full: `python3 -m unittest discover -s tests -v`: 787 tests, OK.

**Browser checks (sandbox, not the helper).** `~/navi-librarian-test/test-pr.sh` is not present in this session. Two isolated servers ran from the same sandbox: `origin/main` at `31ef78a` on 8101 and this branch on 8102, with `NAVIDROME_LIBRARIAN_DATA_DIR` per tree, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` under a sandbox directory, and `SLSKD_URL=http://127.0.0.1:9`. No Navidrome library is configured. The classics endpoint was answered by Playwright with a labelled **RECONSTRUCTED FIXTURE** (five albums, no artwork). Script and results: `/mnt/project-files/phase-3-add-to-collection/screenshots/render-classics.mjs` and `classics-render-results.json`.
- Widths 1440, 1200, 900, 620, 390: `overflowX` 0 on both trees at every width. Branch: five `ranked-row` rows, numerals 01–05 in `rgb(180, 172, 159)` (`--text-muted`), no small targets, zero console errors, zero failed requests. Main: five editorial cards, and × and Dismiss artist under 44px.
- Loading (branch): six `is-skeleton` rows while the response is delayed (2.5 s); main shows no skeleton. Both show "Rotating suggestions…" because the sandbox check used the rotate path.
- Error (502): both trees clear rows and show the server message.
- Not for me: clicking × posts `action: dismiss` with the album metadata to `/api/discovery/feedback` and reloads the list.
- Keyboard after Load albums: Refresh, row link, Get, Not for me, Dismiss artist, next row link.
- Not run: a real Get request (the brief forbids acquisition on a sandbox without authorisation, and the sandbox has no acquisition path), a live library and real artwork, Dismiss artist clicked (it would post to the server), reduced-motion emulation, and the full manual checklist against the PR head SHA.
- Live-library check (other albums by artists who have a full album in the library): **skipped**, for Hamdi to run locally.

**Impeccable.** `/impeccable context` ran. Its `CONTEXT_STALE` note is about `buildPath` in `.impeccable/config.json` and was not acted on. `impeccable detect` ran on `static/app.js` (no findings, regex-only), `app/templates/index.html` (`<img>` with no `src` and 11px text, both in code this PR did not touch) and `static/app.css` (advisory design-system radius, colour and type-ramp literals, all pre-existing; this PR removed one rule and added none). Applied: shared ranked row, muted index instead of a numeral, sort-basis label. Rejected: a red numeral (the order is not a stable score ranking), and a new clamp or tooltip on the shared row (kept to the existing `.ranked-row h3`).

**web-design-guidelines.** The skill's WebFetch of the rules URL returned a summary, not the rule list, so the rules were **not** checked line by line. The summary's categories (focus, touch targets, motion, text overflow, labels) were checked against the changed lines by reading: visible focus is inherited from `.ranked-row:focus-visible` and the button styles; the reduced-motion rule for the skeleton remains in `app.css`; text truncates with the full name in `title`. This is a limitation, not a pass.

**Known limitations.** The title tooltip no longer carries the year. The 390px bottom tab bar overlaps the list (the open follow-up for seven bottom tabs under 620px). Artwork is absent in the fixture. The live-library check is for Hamdi to run.

**Next action.** Hamdi runs this page on a live library locally against the PR head SHA, and decides whether to merge.

## 17. Redesign Phase 4 — Artist Deep Dives (`ui/phase-4-artist-deep-dives`, PR #378, merged)

Merged as squash `fb596c7` on 2026-10-18 after CI on head `2ff746e` (compile, test-and-build, validate-container, container-smoke: all success), no open review threads, and owner instruction to merge. Not deployed. The live-library check and the confirm-step decision remain with the owner.

Roadmap item: Phase 4, Artist Deep Dives (the Dashboard item waits on decision D1 and is not in this PR). Design system sections applied: 8 (the composition for Artist Deep Dives: genre sections, artist-led tiles, a horizontal strip per genre that shows arrows only when it overflows), 9.1 (icon button: 44×44 hit area, 20px sprite icon, `aria-label`, focus ring), 9.2 (Get control, unchanged), 10 (icons from `static/icons.svg`), 12 (accessibility and touch-target floor). Base: `origin/main` at `da908b5` (PR #376, which records PR #375 as merged). PR 375 (`5c9e3e9`) was already recorded in the roadmap on `main`.

**What was already on `main`.** Genre sections (`.genre-row`) with a horizontal `.genre-row-track`, one artist-led card per album, a genre heading with the album count, arrows that are hidden and removed from the tab order unless the track overflows (`syncArrows`, re-checked on resize and on content change), and the existing `/api/discovery/artist_deep_dive` request, pool size (150), 15-per-genre cap and one-album-per-artist rule. This PR does not change any of that.

**What changed.**
- Arrows: the text glyphs `<` and `>` (display face, 36px, with a text shadow) are now the sprite's `chevron-left` and `chevron-right` at 20px in the 44×44 hit area. The `::after` expansion is gone because the box is already 44px. The hover scale is gone; hover is a colour change to `--accent-hover`.
- Not for me: the text `×` is now the sprite's `x` icon at 20px in a 44×44 hit area (it was about 16×16 with a 3px padding). The text shadow is removed. Hover goes to `--text` (the same hover as the ranked-row dismiss). The focus ring sits inside the artwork corner (`outline-offset: -4px`), because the artwork is clipped. Its `title`, `aria-label` and action are unchanged.
- Genre count: "15 albums" was 10px mono; it is now 13px (`--text-sm`) in the body face, `--text-muted`, tabular numerals. Mono is kept for technical metadata only (DESIGN_SYSTEM.md 5).
- Copy: a one-album genre now reads "1 album", not "1 albums".
- A small `spriteIcon(name)` helper in `static/app.js` builds the `<svg><use>` with DOM APIs. The name is always a literal; nothing from the API is put into markup.

**Not changed.** Get and its state machine, the row-open modal, Not for me and its request (`POST /api/discovery/feedback`, `action: dismiss`), the endpoint and its parameters, the grouping and ordering rules, the status line, the empty-state copy, and all server code. No endpoint, field or dependency was added. No contract proposal is needed.

**Dismiss and the confirm step (finding, not changed).** The roadmap's Phase 4 item says Dismiss is "kept with its confirm step". `main` has no confirm step for this control: the click posts `dismiss` at once and the list reloads. There is no `confirm(` in the history of `static/app.js`. DESIGN_SYSTEM.md 9.1 asks for a confirm before any Dismiss. This PR keeps the current behavior, as AGENTS.md requires, and does not add a confirm. The owner should decide whether to add one in a separate PR, or to correct the roadmap wording.

**Tests.** `tests/test_artist_deep_dive_ui_contract.py` gains five source contracts: sprite icons for the arrows and Not for me with names kept; the helper builds nodes without `innerHTML`; no `text-shadow` and 44px boxes on both controls; the count uses the body face; the singular/plural label. The existing three assertions are unchanged; none of them was weakened.

**Checks run on the branch (before the PR head was pushed).**
- `node --check static/app.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install -r requirements.txt --break-system-packages`: installed.
- Focused: `python3 -m unittest tests.test_artist_deep_dive_ui_contract tests.test_add_to_collection_ui_contract tests.test_classics_card_ui_contract -v`: 26 tests, OK (before the pluralize test was added; that test is in the full run).
- Full: `python3 -m unittest discover -s tests -v`: 792 tests, OK.

**Browser checks (sandbox, not the owner's helper).** `~/navi-librarian-test/test-pr.sh` is not present in this session, so the helper was not run. Two isolated uvicorn servers ran from the same sandbox layout: `origin/main` `da908b5` on 8201 and this branch on 8202, each with its own `NAVIDROME_LIBRARIAN_DATA_DIR`, sandbox `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR`, and `SLSKD_URL=http://127.0.0.1:9`. A sandbox owner account was created with `POST /api/auth/setup` on each server. `/api/discovery/artist_deep_dive` was answered by Playwright with a **RECONSTRUCTED FIXTURE** (22 albums in four genres: 15 jazz, 4 rock, 2 African, 1 electronic; no artwork; "COVER NOT FOUND" placeholders). Scripts: `render.mjs` and `keys.mjs`, copied with the screenshots to `/mnt/project-files/phase-4-artist-deep-dives/screenshots/`.

| Width | Before: small targets (×) | After: small targets | Arrows visible (sections 1–4) | Overflow-x, after | Console errors, after | Failed requests, after |
|---|---|---|---|---|---|---|
| 1440 | 22 | 0 | jazz only | 0 | 0 | 0 |
| 1200 | 22 | 0 | jazz only | 0 | 0 | 0 |
| 900 | 22 | 0 | jazz, rock | 0 | 0 | 0 |
| 620 | 22 | 0 | jazz, rock | 0 | 0 | 0 |
| 390 | 22 | 0 | jazz, rock, African | 0 | 0 | 0 |

Before and after screenshots: `before-{1440,1200,900,620,390}.png` and `after-{...}.png` in the screenshot folder. Keyboard: Tab reaches a 44px Not for me control with a visible 2px accent ring inside the artwork corner; Enter on the right chevron scrolls the Jazz track from 2px to 926px; Enter on Not for me posts `{action: "dismiss", artist, album, metadata}` to `/api/discovery/feedback` (intercepted in the sandbox, not sent to a real server) and the list reloads.

Not run: the live-library check (skipped; for the owner to run locally against the PR head); a real Dismiss against a server (not run; the endpoint was intercepted); a real Get request (not run; the sandbox has no acquisition path, and the brief forbids it without authorization); reduced-motion emulation (not run; the global `prefers-reduced-motion` rule that sets `scroll-behavior: auto` is unchanged); a screen-reader pass (not run, as before); the full manual checklist from `docs/TEST_PLAN.md` against the exact PR head SHA (not run through the helper).

**Impeccable.** `impeccable context` ran at the start of the session. `critique` was applied to the rendered page at five widths (the findings above are from the renders, not from reading the CSS alone). Applied: sprite icons in place of glyphs and text shadows; 44px targets; the count in the body face; the focus ring kept inside the clipped artwork. Rejected: adding a confirm step (behavior, not design; it needs the owner's decision); adding a new genre tile style or a different strip layout (the current structure already matches DESIGN_SYSTEM.md section 8); hover scale (not in the motion table). `impeccable detect` on `static/app.css`, `static/app.js` and `app/templates/index.html` reports 48 advisory notes, down from 51 on `main`. None of the 48 is on a line this PR wrote; the remaining ones are pre-existing (the album modal backdrop, the Get button font size, the type ramp and literal colours that Phase 1 and Phase 7 are to clear).

**web-design-guidelines.** The skill's WebFetch of the rules URL returned a summary, not the rule list, so the rules were **not** checked line by line. The changed controls were checked by reading against the categories it names (focus visibility, accessible names on icon-only controls, touch targets, reduced motion, no `transition: all`, no overflow): the new controls have `aria-label`, a visible focus ring and 44px boxes; the new CSS adds no transition. This is a limitation, not a pass.

**Known limitations.** The fixture has no artwork, so the artwork corner shows placeholders only. The Dashboard item of Phase 4 is not in this PR (waits on D1). The confirm-step finding is open. The 390px bottom tab bar issue from Phase 2 is unchanged.

**Next action.** The owner runs Artist Deep Dives on a live library locally against the PR head SHA (including Not for me on a sandbox folder), and decides on the confirm step before the Dashboard item starts.

## 18. Redesign Phase 4 — Dashboard as a static tile strip (`ui/phase-4-dashboard-tiles`)

Roadmap item: Phase 4, Dashboard (first bullet). Decision D1 (retire the 3D ring for a static tile strip) is applied; the owner's D1 outcome is recorded in `docs/DESIGN_SYSTEM.md` section 15 as "Retire". PR #381 (head `8714d95`, branch `ui/phase-4-dashboard-tiles`). CI on `8714d95` passed (compile, validate-container, test-and-build, container-smoke: all success), with no review threads. The owner ran the dashboard on the live library and reported it looks good. Merged by squash after the owner's instruction. Not deployed.

Design system sections applied: 8 (Dashboard row: artwork tile strip, unranked, no numerals), 9.1 (focus ring, 44px Get), 9.2 (Get state machine kept: pending, then requested only after the server answers), 9.6 (loading, empty and error copy), 10 (icon sprite unchanged), 11 (reduced motion: the ring's ambient loop and drag inertia are removed, and native smooth scrolling is turned off by the global reduced-motion rule), 12 (accessibility floor), 15 (D1).

**What changed.**
- The 3D coverflow ring (`buildDashboardRing`, `ringFlatten`, the `RING_*` constants, the ambient drift, the drag and key steering) is removed from `static/app.js`. The strip is the flat scroller that was already the fallback. Its CSS (`.is-ring`, `.ring-scene`, `.ring-stage`, `.ring-card`, `rotateY`, `translateZ`, `perspective`) is removed.
- Each tile is now an `article` with no focus stop of its own. One named `button` (`.dashboard-tile-open`, "View details for ALBUM by ARTIST") covers the tile and opens the album dialog. It comes first in the DOM, so it is the first focus stop. The Get control sits in the artwork corner as its own focus stop, not nested inside the open button. This follows the ranked-row pattern (9.4) that Phase 3 shipped.
- The album dialog returns focus to the open button that opened it, not to the non-focusable article (`openAlbumModal(card, returnFocus = card)`).
- The strip takes the genre-row scroller treatment: a tab stop, a name, arrow, Home and End keys, and a visible focus ring. It is attached once at startup, so shuffles do not stack listeners.
- Tiles are unranked. No numeral is shown, and the random order is not presented as a ranking.
- Shuffle is disabled while a request is pending, so two responses cannot race into the strip.
- Copy: "Drag the ring, or focus it and use ← →" is now "Scroll the row, or focus it and use ← →."

**Not changed.** `GET /api/dashboard-picks` and its parameters, the response handling and the `isAlbumRecommendation` filter, the Get request (`POST /api/acquire`) and its state machine, the album dialog contents, all backend code, and the artwork loader.

**Tests.** `tests/test_ui_keyboard_and_feedback_contract.py`: the `DashboardRingTests` class was removed because it asserted ring code that no longer exists. It is replaced by `DashboardTileStripTests` (10 contracts: no ring or 3D transforms; unranked; one named open control and a separate Get; the tile article is not a focus stop; focus returns to the open button; metadata hidden from assistive tech; the Get state machine; shuffle guard; the strip as a named, focusable scroller with a focus ring; the open control's focus ring and coverage). Two existing assertions were updated narrowly, with a reason written in the test: the scroll-helper wiring (now the strip and the genre rows), and the focus-return expression (`albumModalReturnFocus = returnFocus`). The behavior each one protects is the same, and nothing was deleted to make a test pass.

**Checks run (head: see PR).**
- `node --check static/app.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install -r requirements.txt --break-system-packages`: installed.
- `python3 -m unittest discover -s tests -v`: 788 tests, OK.
- `python3 -m unittest tests.test_ui_keyboard_and_feedback_contract -v`: 29 tests, OK.

**Browser checks (sandbox, RECONSTRUCTED fixture, not the owner's helper).** Two isolated uvicorn servers: `origin/main` (`4b76226`) on 8301 and this branch on 8302, each with sandbox data, music and downloads paths outside the repo, `SLSKD_URL=http://127.0.0.1:9` with an empty key, Navidrome unconfigured. The sandbox owner account was created with `POST /api/auth/setup`. `/api/dashboard-picks` was answered by Playwright with a fixture of ten albums (labelled RECONSTRUCTED), `/api/artwork` returned no artwork, and `/api/acquire` was answered with a fixture reply, so no request reached slskd. Chromium 1194 through Playwright.
- Widths 1440, 1200, 900, 620, 390 on both servers. Branch: 10 tiles, 0 numerals, no ring, document overflow 0 at every width, open control 216px (covers the tile), Get 46×46 at every width. The strip scrolls inside its container.
- Keyboard (branch, 1440): ArrowRight and End scroll the strip; Tab from the strip lands on the first tile's open control; Enter opens the dialog; Escape returns focus to that open control.
- Get (branch): click gives `is-pending`, `aria-busy="true"` and disabled; after the server reply, `requested` with the "Acquisition requested" label. The request payload carried the correct artist.
- Shuffle (branch): rebuilds the strip to 10 tiles.
- Empty state: "No suggestions yet. Open a discovery page and refresh its list first." Error state: the server's message is shown and the strip is empty.
- Reduced motion (`prefers-reduced-motion: reduce`): the strip's computed `scroll-behavior` is `auto`.
- Console: the branch shows no errors on the dashboard. When the album dialog opens, four `ERR_TUNNEL_CONNECTION_FAILED` errors appear. `main` shows the same four with the same flow, so they predate this change. They come from the dialog's third-party logo requests (B2 in the known limits), which the sandbox cannot reach.
- Screenshots: `/mnt/project-files/phase-4-dashboard-tiles/screenshots/` (before = `main`, after = branch).

**Impeccable and web-design-guidelines.** The web-interface guidelines rules were fetched this time and checked against the changed files. Applied: `aria-hidden` on decorative tile text; `:focus-visible` on the overlay and the strip; no `transition: all`; the loading copy ends with `…`; the Get control has an accessible name; the open control covers the whole tile so the dead zone is gone. Rejected or out of scope: `<img>` width and height and the `loading="lazy"` attribute live in the shared `attachArtwork` helper, which predates this change and is used by other lists, so it is left for a separate slice. Impeccable: `impeccable context` was run and the product and design context was read. The full critique workflow was **not** run, so no Impeccable finding is claimed. The `impeccable detect` run was not done.

**Known limitations.**
- No live library: tiles show placeholders. The live-library check is the owner's, against the PR head SHA.
- Only the Chromium check was run. No screen reader was tested.
- The shared `attachArtwork` image attributes are unchanged (see above).
- The strip has no arrow buttons; the native scroller and keys are the only controls. That matches the genre rows at widths where they overflow.

**Next action.** Phase 5 (Acquisitions) is the next roadmap phase. Phase 4 is complete with this PR merged; deployment is the owner's call.


## 19. Redesign Phase 5 — Acquisitions as status rows (`ui/phase-5-acquisition-rows`)

Roadmap item: Phase 5, first bullet (status rows and a linear progress bar; one status table). Design-system sections applied: 9.5 (acquisition status row), 9.6 (skeleton loading, status line), 11 (motion, `transform` only), 12. Acceptance criteria were those in the Phase 5 brief: every status renders with a glyph and a label; the bar animates only `transform`; no horizontal overflow at 1440, 1200, 900, 620 and 390px; 44px targets; reduced motion respected; pending, failed and confirmed Get checked; contract tests changed only where a structure changed intentionally.

### 19.1 What changed
- `renderAcquisitions` builds one `article.acq-row` per job: artwork thumb (the existing `attachArtwork` loader, so the image comes from the existing `/api/artwork` endpoint), title with year, artist, quality profile (mono), transport lines, and a state block. The state block holds the glyph and label, and for downloads a `role="progressbar"` with the percentage as text, plus speed, size and track figures.
- `ACQUISITION_STATUS_TABLE` maps each server job status to a glyph, a label and a tone. Unknown statuses render with `•` and their own name, never blank.
- The conic `progress-ring` and the `.download-progress` card block are removed. The bar fills with `transform: scaleX(var(--progress))`.
- Loading shows three skeleton rows only while the list is empty, and clears them on failure. Known rows stay visible during a refresh.
- Rows keep the album-dialog click and Enter behaviour (`.acq-row[data-album-title]` is added to the shared delegation).
- `index.html`: `#acquisitionCards` changes class from `cards acquisition-grid` to `acq-list`.
- Unchanged: `/api/acquire` (Try again), `/api/acquisitions/skip`, `/api/acquisitions/dismiss` (success-only removal), `/api/acquisitions/stream` and its reconnect message, the Get state machine.

### 19.2 Decisions taken without the owner (state these in review)
- The title is not clamped. The ranked rows clamp to two lines; a status record shows the whole album name, so no state is hidden. The stylesheet keeps its single `-webkit-line-clamp`, which the classics contract test pins.
- Status copy is new wording for the glyph labels (for example "Download complete, waiting for folder"). The raw status names are not shown any more, except as the fallback for an unknown status. The server vocabulary itself is not renamed.
- The table covers the statuses found in the backend and in the design system. A status that is not listed falls back as described above. Nothing was invented in the API.
- Artwork is now requested for acquisition rows. Each row adds one cached `/api/artwork` request, as ranked rows already do.
- Rows keep `role="button"` from the shared album-dialog pattern, with Try again and Dismiss inside it. That nesting is pre-existing, and is recorded as a limitation (19.6), not changed here.

### 19.3 Contract tests
`tests/test_acquisition_ui_contract.py`: one narrow update, `card.remove();` becomes `row.remove();` (the dismiss handler now removes a row). The success-only removal and its ordering are asserted exactly as before. Ten tests were added in `AcquisitionStatusRowTests` for the status table, the unknown-status fallback, glyph plus label, progressbar with `transform`, the unavailable-progress text, the skeleton, reduced motion, the shared click path and the stream path. No existing assertion was deleted or weakened. One intermediate failure, the `-webkit-line-clamp` count, and one, the first `620px` media block the shell test matches, were caused by my CSS placement and fixed by moving the rules, not by changing the tests.

### 19.4 Checks actually run
Run on the branch before the PR head was pushed (the head SHA is in the PR):
- `node --check static/app.js`: pass.
- `python3 -m compileall -q app static`: pass.
- `pip install -r requirements.txt --break-system-packages`: pass.
- `python3 -m unittest discover -s tests -v`: 798 tests, OK. Baseline on `main` `b6acd7a` before the change: 788 tests, OK.
- Focused: `tests.test_acquisition_ui_contract` 23 tests, OK.

### 19.5 Browser checks (sandbox, not the owner's helper)
The helper `~/navi-librarian-test/test-pr.sh` is not available in this environment. The check used two local servers: `main` `b6acd7a` on 8401 and the branch on 8402, each with `NAVIDROME_LIBRARIAN_DATA_DIR` set to a per-run directory and `SLSKD_URL=http://127.0.0.1:9`. No Navidrome library and no slskd were connected. Acquisition jobs, dashboard picks, artwork and album details were answered by Playwright with **RECONSTRUCTED** fixtures (11 jobs covering every status in the table, a long album title, an unknown status, a failing dismiss and a stall). Live-library checks are **skipped**. Screenshots are in `/mnt/project-files/phase-5-acquisitions/screenshots/` (`main-*` before, `branch-*` after, at 1440, 1200, 900, 620 and 390, element and viewport; plus skeleton, error, empty and after-dismiss at 1440). Raw results: `render-results.json` in the same folder.
- Width matrix (both targets, five widths): horizontal overflow 0 everywhere; no row overflowing its box; no skeleton left after load.
- Every status row shows a glyph and label (branch). Progress at 42% renders `matrix(0.42, 0, 0, 1, 0, 0)` with `transition-property: transform`; the progress-less download shows "Progress unavailable".
- Keyboard: a row takes focus; Enter opens the album dialog; Escape closes it.
- Try again posts once to `/api/acquire` with the row's artist and reloads the list.
- Dismiss success removes only that row (10 remain). Dismiss failure keeps the row, re-enables the button and shows the server message in an error status line.
- Skeleton: three placeholder rows with `aria-hidden` during a delayed load, status "Connecting…"; cleared on load. Error state: the list error is shown and no placeholder remains. Empty state: the empty copy.
- Reduced motion: fill transition effectively 0s; row animation none.
- Live stream: the sandbox stream closes after one event, so the reconnect message appears after the first event and the rows are kept (10). This exercises the reconnect path; a long-lived stream was not tested.
- Get (dashboard, branch): pending (`is-pending`, `aria-busy`, disabled) → confirmed (`requested`, label "Acquisition requested") only after the server answered; failure → `is-failed` and enabled. Get code was not changed.
- Console: no errors on the acquisitions width matrix. In the dialog check, the album dialog loads third-party platform icons and a cover from external hosts, which the sandbox cannot reach. That is the known limit B2 and is not from this change. The one 500 is the deliberate failing dismiss.
- Network: no failed requests at any width except the deliberate dismiss 500 and the B2 external loads.

### 19.6 Impeccable and web-design-guidelines
- `/impeccable` context loaded (PRODUCT.md, DESIGN.md, the surface brief). `impeccable detect` run on `static/app.css` and `app/templates/index.html`. Applied: the two new 12px mono rules use the existing `--text-xs` step. Rejected: the other detector findings are in rules outside this change (ranked-row `999px` radius, the `11px`/`13px` legacy sizes, the 20px row title that matches the ranked row, the `rgba` overlays, the empty `<img>` and the `11px` text, which predate this PR).
- web-design-guidelines: the guidelines source was fetched as a summary, not verbatim, so this is a review against that summary only. Reviewed for labels, focus, reduced motion, transform-only animation, tabular numerals, ellipsis, truncation and empty states. Applied: `transform`-only animation, `aria-hidden` on glyphs and skeletons, the existing `aria-live` status line, `tabular-nums` on percentages and figures. Rejected: none of the rules found a violation beyond the nested-button pattern below.

### 19.7 Limitations
- Chromium only, no screen-reader pass. The shared album-dialog pattern nests Try again and Dismiss inside a `role="button"` row. That is pre-existing; a fix (a row that is not a button, with a separate open control) is a separate PR because it changes the click behaviour.
- The "Refresh status" button sits flush at the left edge of the section, as on `main`. Not changed here.
- Artwork is from the sandbox mock (blank thumbs). Real artwork and real progress are for the owner's live-library check.
- Stall and skip were tested only as the button's presence and label, not against a live source switch.

### 19.8 Next action
Owner: run the Phase 5 manual checklist on the exact PR head against a live library (pending, failed and confirmed Get; a real progress row; skip on a stalled job). Merge is the owner's call.

## 20. Redesign Phase 6 — Settings (`ui/phase-6-settings`)

Roadmap item: Phase 6, first bullet (Settings). Design system sections applied: 9.7 (forms and tabs), 9.1 (buttons), 6 (layout, compact rows), 7 (borders), 10 (icons unchanged), 11 (motion: none added), 12 (accessibility floor), 13 (anti-patterns). Branched from `origin/main` at `a65fabf` (PR #383).

### 20.1 Acceptance criteria (stated before implementation)
- Two-column field layout from 900px; one column below.
- ARIA tabs pattern kept: roving tabindex, arrow keys, Home and End.
- Quality-tier order works by keyboard alone, announces the new position, and keeps focus on the moved row.
- Secret fields are never rendered into markup; a blank secret field still preserves the saved value.
- Contrast and 44px targets hold; no horizontal overflow at 1440, 1200, 900, 620 and 390px; reduced motion honored; console and network clean apart from known limits.

### 20.2 What changed
- `static/app.css`: the settings tabs restyled as a bottom-rule tab row (selected tab takes the accent text and 3px accent underline; no pill fills). Two-column grid from 900px for fields, with headings, notes, status lines and the tier list spanning both columns. Inputs 40px tall. Settings buttons 44px. Quality rows 48px (compact). Move buttons 44×44. Hardcoded `#c8c8bd` label grey replaced with `--text-muted`.
- `static/app.js`: after a keyboard or button move, focus returns to the moved row's same-direction button, or to the other button when the pressed one becomes disabled at the list edge. Before this change, focus fell to `BODY` after the first move (confirmed in the browser check below).
- `tests/test_settings_ui_contract.py` (new): 13 source-contract tests for the focus return, the announcement live region, roving tabindex, the two-column breakpoint, the 44px floor, token use, no new motion, and secret inputs rendered without a value.
- No template change, no endpoint, field, request body, or save or load path change. Secret fields keep the existing blank-means-keep behavior in `saveNavidrome`, `saveSlskd` and `saveLastfm`, enforced server-side in `service_settings.py`. ListenBrainz has no secret field.

### 20.3 Decisions taken without the owner (state these in review)
- The tier reorder already had Move up and Move down buttons, an `aria-live` announcement and drag. Kept all three; the change is focus retention and touch targets, not a new control.
- Drag reorder is not given a keyboard-only drag. The keyboard path is the buttons, as in `main`.
- No FLIP list animation was added. Design section 11 allows it on sort change; a reorder animation would add motion for a settings list with six rows and was left out to keep this slice small.
- The tab row wraps to two lines at 390px rather than scrolling sideways, so no tab is hidden.
- Field grid uses the existing `.settings-tab-panel` container. The old `#settings input` max-width of 520px is removed so fields fill their column.

### 20.4 Checks actually run
- `node --check static/app.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install -r requirements.txt --break-system-packages`: installed.
- `python3 -m unittest tests.test_settings_ui_contract -v`: 13 tests, OK.
- `python3 -m unittest discover -s tests`: 825 tests, OK. The Phase 5 handoff quoted a baseline of 798 on `main`; this run reports 825 on the branch with 13 new tests added. The 14-test difference from the handoff baseline is not reconciled here.
- Sandbox servers, outside the checkout, with `NAVIDROME_LIBRARIAN_DATA_DIR` set to a per-run directory, `SLSKD_URL=http://127.0.0.1:9`, and music set to the sandbox path. Branch at `5dfa646` on port 8090; `origin/main` at `a65fabf` (extracted, not checked out) on port 8091. Owner account created on each. No live library and no slskd were connected.

### 20.5 Browser checks (sandbox, not the owner's helper)
The helper `~/navi-librarian-test/test-pr.sh` is on the owner's machine, not in this environment, so it was not used. Fixture data is reconstructed: the quality tiers are the app's six default options and no real Navidrome library is connected. Labelled RECONSTRUCTED.
- Width matrix (both builds, 1440, 1200, 900, 620, 390): horizontal overflow 0 everywhere. Screenshots: `phase-6-settings/screenshots/` in the project folder (before-*, after-*).
- Layout: at 1440 the slskd fields sit in two columns; at 390 they stack and the tier rows keep their 44px move buttons inside the row.
- Keyboard reorder, Enter on Move down of row 1, repeated (RECONSTRUCTED fixture):
  - `main`: after the first move, focus is on `BODY`; the announcement is set but the user has to tab back to the list.
  - branch: focus stays on the moved row's Move down button; position reads 02, then 03. Pressing Enter at the bottom edge moves focus to the Move up button; further Enter moves the row back up with focus kept.
- Console and network: the only error on both builds is `502` from `GET /api/settings/listenbrainz`. This is the known backend limit B1 from the Phase 0 baseline, present on `main` as well, not from this change.
- Not run: saving a secret on the sandbox to confirm preserve-on-blank end to end. The skip is recorded as a skip; the behavior is covered by the unchanged save paths and the contract tests in 20.4, not by a browser save.
- Not run: drag reorder in the browser. Mouse drag is unchanged code.
- Not run: reduced-motion emulation. No motion was added, so there is nothing for it to disable.
- Not run: contrast measured on the rendered build. Colors used are existing tokens (`--text-muted`, `--accent`, `--edge-strong`).

### 20.6 Impeccable and web-design-guidelines
- The Impeccable post-edit hook reported no deterministic design-quality issues in `static/app.css`. The full `/impeccable critique` and `/impeccable audit` passes were not run in this session, so none are claimed.
- Applied from the design system: tokens only in the settings rules, the selected tab marked by an underline as well as color, 44px targets, two-column grid with full-width headings and notes.
- Rejected: an animated list reorder (section 20.3); a horizontally scrolling tab strip; a numeral on the tier rows beyond the existing position numbers, which are a real saved order.
- `anthropic-skills:web-design-guidelines` was not run in this session. Not claimed.

### 20.7 Limitations
- Chromium only. No screen-reader pass.
- The live Navidrome library and real saved secrets were not tested. The owner runs the live check.
- The 502 from the ListenBrainz settings endpoint remains (B1, backend, out of scope for the front end).
- The tab row wraps to two lines at narrow widths; labels were not shortened.

### 20.8 Next action
Owner: review the diff and the keyboard evidence in 20.5, run the Settings checklist on the exact PR head against the live library (including one real secret save with a blank field preserving the saved value), and merge if satisfied. Next roadmap item in this phase: Login and first-run setup, as a separate PR.

## 21. Redesign Phase 6 — Login and first-run setup (`ui/phase-6-login`)

Roadmap item: Phase 6, second bullet (login and first-run setup restyled to the new tokens; the first-run variant was a recorded skip in PR #66 and is tested here). Design system sections applied: 9.7 (forms), 9.1 (buttons), 6 (page head with the 3px chart-red rule), 7 (borders, no shadow), 4.2 (state never by colour alone), 5 (type faces), 11 (reduced motion), 12 (accessibility floor), 13 (anti-patterns). Branched from `origin/main` at `c0856d8`, which includes Settings (PR #386, `ef93112`).

### 21.1 Acceptance criteria (stated before implementation)
- Sign-in and first-run setup both render in the Chart Rundown tokens.
- First-run keeps its password-confirmation check and its server-side rules: username 3–64 characters, password at least 12, passwords must match. The server message copy is shown unchanged.
- A failed sign-in shows an accurate error with a glyph and text in a `role="alert"` region, not colour alone.
- Labelled fields, visible focus, 44px inputs and primary button, no horizontal overflow at 1440, 1200, 900, 620 and 390px, reduced motion honoured, no console or network errors except known limits.
- No endpoint, request body, auth, session or cookie change. No credential or configuration value in markup. No third-party asset and no Google Fonts import.

### 21.2 What changed
- `app/templates/login.html`: a field wrapper per input; the confirmation hint is linked to its field with `aria-describedby`; the brand image has intrinsic 64×64 dimensions; the username input has `autocapitalize="none"` and `spellcheck="false"`. Ids, names, `minlength`/`maxlength`, the `role="alert"` message region and the script and stylesheet references are unchanged.
- `static/login.css`: the page is restyled to the tokens (copied from `static/app.css` because this page does not load `app.css`). Heading uses the display face with a 3px chart-red rule. Labels and hints use the UI face (JetBrains Mono removed from labels). Inputs and the button are 44px minimum. The panel has no shadow. Error text uses `--chart-red-text` with a glyph. Reduced motion removes the button transition.
- `static/login.js`: errors are built with `textContent` and a decorative `aria-hidden` glyph. The pending state sets `aria-busy` and a progress label ("Signing in…" or "Creating account…"). Non-string `detail` values fall back to "Authentication failed." (previously an array would have rendered as `[object Object]`). A network failure reads "Could not reach the server. Try again." The redirect still happens only after the server accepts the request.
- `tests/test_login_ui_contract.py` (new): 21 source-contract tests covering the landmark and labels, the alert region, no inline style or script or third-party asset, tokens and no literal colours, no panel shadow, 44px floor, focus, glyph-plus-text errors, reduced motion, display-face scope, no mono labels, the unchanged endpoints and password-confirmation field, redirect ordering, and no `innerHTML`.

### 21.3 Decisions taken without the owner (state these in review)
- The design system says inputs are 40px and the button is 40px with a 44px touch area. The 44px floor in AGENTS.md and the Settings precedent (section 20) were applied, so inputs and the button are 44px tall.
- The password-match check stays on the server, as before. The client does not add a second check, so the server copy "Passwords do not match." is the only message.
- Button label changes while pending ("Signing in…"). This is copy the user did not previously see; it is noted for review.
- Login password `minlength="12"` on the sign-in form is kept, as before.
- No new icon was added. The sprite holds the 14 approved icons, and its test requires that exact set. The error glyph is a CSS-drawn "!" in a circle.
- The `.intro` error on a failed status load gets the same glyph. The intro is not a live region, as before.

### 21.4 Checks actually run
- `node --check static/login.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install -r requirements.txt --break-system-packages`: installed.
- `python3 -m unittest tests.test_login_ui_contract -v`: 21 tests, OK.
- `python3 -m unittest discover -s tests -v` (before the two template attribute edits) and `python3 -m unittest discover -s tests` (final tree): 853 tests, OK each time.

### 21.5 Browser checks (sandbox, not the owner's helper)
The helper `~/navi-librarian-test/test-pr.sh` is on the owner's machine, not in this environment, so it was not used. Servers ran from `git archive` extracts of the committed tree, outside the checkout, with `NAVIDROME_LIBRARIAN_DATA_DIR` set to scratch directories, `SLSKD_URL=http://127.0.0.1:9`, and no live library. Sign-in servers were given a sandbox owner account. Fixture credentials are RECONSTRUCTED sandbox values, not real ones. Playwright (Chromium 1194) drove the renders. Screenshots are in `phase-6-login/screenshots/` in the project folder: `main-*` is the before state (`origin/main`, `c0856d8`), `branch-*` is the after state (the application commit `b639cd1`).

- Width matrix, sign-in and first-run states, both builds, at 1440, 1200, 900, 620 and 390: horizontal overflow 0 everywhere. Inputs and the primary button measure 44px on the branch and 49px and 41px on `main`.
- Label font: the branch uses Schibsted Grotesk; `main` uses JetBrains Mono.
- Reduced motion (emulated at 1440): the branch button transition is 0s; `main` keeps 0.15s.
- Failed sign-in with a wrong password (sandbox account): the branch shows a glyph, the text "Invalid username or password.", `role="alert"`, and restores the button label "Sign in" with no `aria-busy` left behind. The `main` build shows the same copy without a glyph.
- First-run mismatch (fresh data directory, no account created): the branch shows "Passwords do not match." with a glyph and no console error. The server returned 400 and no account was created.
- First-run success on a fresh data directory (branch, 390px): the owner account is created, the page redirects to `/`, `/api/auth/status` reports `setup_required: false`, and there are no console errors. That fresh directory is now used by the owner account; the render was re-run on a second fresh directory.
- Console and network: the only console error on either build in a failed sign-in is the expected `401` from the deliberately wrong password. No third-party host was requested on either build.
- Impeccable: `npx -y impeccable@4.6.0 detect` on the changed CSS, JS and HTML files printed the notice that the page-level rules did not run on static files, with no findings reported. The same CLI on the live pages (`IMPECCABLE_BROWSER` pointed at a no-sandbox Chromium wrapper) exited 0 with no output. This does not show that the page-level rules ran, so it is recorded as "no findings printed", not as a clean pass.
- Not run: keyboard-only traversal recorded as a video or sequence; the focus ring was checked in the rendered screenshots only on the username field. Not run: screen-reader pass. Not run: the live library sign-in, real credentials, or the owner's helper checklist.

### 21.6 Impeccable and web-design-guidelines
- Impeccable `critique` and `audit` passes were not run as full sessions in this environment. The detector results are in 21.5. No critique or audit is claimed.
- `anthropic-skills:web-design-guidelines`: the fetched guideline source returned a category summary, not the verbatim rule list. The review applied these categories to the three files: labels, focus, autocomplete, inline errors, reduced motion, ellipsis in loading copy, intrinsic image size (applied: `width` and `height` on the brand image), input hints (applied: `autocapitalize` and `spellcheck` on username), and no layout reads in the script. Not claimed as a full verbatim rule review.
- Applied from the design system: tokens only, display face on the page heading only, 3px chart-red rule, no shadow, 44px targets, glyph plus text for errors.
- Rejected: a second client-side password-match check (server remains the authority); a new icon for the error (the sprite test pins the 14-icon set); a larger brand mark or new imagery (D6, keep the cassette).

### 21.7 Limitations
- Chromium only; no screen-reader pass; no physical-device check.
- The live Navidrome library and real credentials were not tested. The owner runs the live check.
- Sign-in is still limited to the existing server rules and rate limit (429 copy shown as the server sends it).
- The error glyph is CSS-drawn; it is decorative and `aria-hidden` on the script-built span.

### 21.8 Next action
Owner: review the diff and the screenshots in `phase-6-login/screenshots/`, run the sign-in and first-run checklist against the exact PR head on the owner's helper (first-run on a deliberately fresh per-run data directory, never by deleting an existing one), and merge if satisfied. Next roadmap item in this phase: album modal, as a separate PR.

### 21.9 Merge record
Owner-approved merge of PR #388 on 2026-10-19 at head `9d5eb72` (squash commit `a005b1c`). CI green on that head. Deployment not verified.

## 22. Redesign Phase 6 — Album modal (PR #391, merged, squash `759510e`)

Roadmap item: Phase 6, third bullet (new layout and motion, focus return, Escape, tracklist rhythm). Design system sections applied: 8 (album modal composition: artwork left, tracklist right, platform links beneath the artwork), 9.8 (modal: dialog semantics, focus trap, Escape, focus return, solid scrim, 6px radius), 9.4 (row behaviour is unchanged), 6 (tracklist rows at 48px, page-head maximum of 30px), 7 (no shadow on the dialog, depth from the ground ladder), 10 (sprite close icon), 11 (modal motion is opacity and an 8px translate; reduced motion removes it), 12 (44px targets, reduced motion, landmarks and names). Branched from `origin/main` at `a005b1c` (PR #388). The branch name follows the designated development branch for this session, not the `ui/phase-6-album-modal` name in the project brief.

### 22.1 Acceptance criteria (stated before implementation)
- Artwork left and tracklist right at 900px and wider; stacked below 650px. No horizontal overflow at 1440, 1200, 900, 620 and 390px.
- Modal motion is opacity and an 8px translate only, and `prefers-reduced-motion: reduce` removes it.
- Focus returns to the opener on close; Escape closes; Tab stays inside the dialog.
- Every control in the dialog is at least 44×44px.
- Existing album-detail and artwork calls, the Get state machine and the dialog's ARIA semantics are unchanged.
- No console or network errors except known limit B2 (third-party platform images in the album modal).

### 22.2 What changed
- `static/app.css`: the album modal block is rewritten with tokens only. The scrim is `--ink` at 80% and solid (blur removed). The panel is `--surface-raised`, `--edge` border, `--radius-panel`, and no box shadow. The title uses the 30px `--text-2xl` display step. The year is metadata colour, not the accent. Tracklist rows are 48px minimum with tabular numbers. Platform links are 44px visible chips (previously 30px visible with a 44px pseudo-element hit area). The open animation is `album-modal-fade` and `album-modal-rise`, which use only opacity and an 8px translate at `--dur-slow` and `--ease-out`. Reduced motion sets `animation: none`. `overscroll-behavior: contain` is set on the dialog, and `text-wrap: balance` on the title.
- `app/templates/index.html`: the close control's `×` text is replaced by the sprite `x` icon, `aria-hidden`. The button keeps its accessible name, `aria-label="Close album details"`. Ids, dialog semantics, and the platform link and Get markup are unchanged.
- `static/app.js`: not changed. The focus trap, Escape, focus return and data calls already met the acceptance criteria and are protected by existing tests.
- `tests/test_album_modal_ui_contract.py` (new): 14 source-contract tests covering the dialog name and semantics, the sprite close icon, artwork-before-copy order, no blur or shadow, no literal colours, year not in the accent, motion keyframes, the reduced-motion removal, 44px targets, tracklist rhythm, title size, `overscroll-behavior`, `text-wrap`, and the unchanged data calls and close-to-opener logic. The existing focus, trap and Escape tests in `tests/test_ui_keyboard_and_feedback_contract.py` are not edited.

### 22.3 Decisions taken without the owner (state these in review)
- The 30px visible platform chips became 44px visible chips, not 30px chips with a larger hit area. The 44px floor in AGENTS.md applies to the visible control, and five chips plus gaps fit the 340px column.
- The dialog no longer has a drop shadow or a backdrop blur, following DESIGN_SYSTEM.md 7 and 9.8. The scrim is now opaque, so the dialog reads through its raised surface rather than a shadow.
- The title is 30px (`--text-2xl`), the maximum for headings in section 13, down from 34px. The 28px mobile override was removed.
- Motion runs on open only. Close is still instant (`hidden`), because animating the close would need a delayed hide and the design system lists only the open motion for the modal.
- The artwork `<img>` has no `width` and `height` attributes. Its box is fixed by `aspect-ratio: 1` and the artwork's intrinsic size varies, so the box does not shift.

### 22.4 Checks actually run
- `node --check static/app.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install -r requirements.txt --break-system-packages`: installed.
- `python3 -m unittest tests.test_album_modal_ui_contract -v`: 14 tests, OK.
- `python3 -m unittest discover -s tests -v`: 875 tests, OK.
- Impeccable: `npx -y impeccable@4.6.0 detect` on `static/app.css`, `app/templates/index.html` and `static/app.js`. The advisory count went from 44 on `origin/main` to 34 on this branch. The remaining findings are outside the album modal block (for example, card and Dashboard values). None lie inside the modal block lines.
- `anthropic-skills:web-design-guidelines`: fetched the live rule list. Applied: `overscroll-behavior: contain` on the dialog; `text-wrap: balance` on the dialog title. Checked and already satisfied: icon-only buttons have `aria-label`, decorative icons and the platform icons have `aria-hidden` or empty `alt`, `Loading…` style copy, no `outline: none`, `:focus-visible` rings, no `transition: all`, reduced motion. Rejected: explicit `width` and `height` on the artwork image (the box is fixed by `aspect-ratio`; the artwork's intrinsic size varies). The Impeccable critique and audit skills were not run as full sessions; the detector result is recorded above, not a critique.

### 22.5 Browser checks (sandbox, RECONSTRUCTED data)
- The owner's helper `~/navi-librarian-test/test-pr.sh` is not in this environment, so it was not used. Two servers ran from copies of the trees, `origin/main` at `a005b1c` ("main") and the branch working tree ("branch"), each with its own scratch data directory (`NAVIDROME_LIBRARIAN_DATA_DIR`), `SLSKD_URL=http://127.0.0.1:9`, and a sandbox owner account created through the first-run endpoint. There is no live library. Album details and artwork responses were mocked in the browser with RECONSTRUCTED values (12 tracks, one long title, a generated SVG). The opener card was a RECONSTRUCTED fixture built with the app's own `makeAlbumCardInteractive`.
- Script: `phase-6-album-modal/screenshots/render-modal.js` (Playwright, Chromium 1194). Results: `render-modal-main.json` and `render-modal-branch.json`.
- Width matrix, branch vs main: document scroll width equals the viewport at 1440, 1200, 900, 620 and 390 on both builds. Layout: side by side at 900 and wider, stacked at 620 and 390 on both builds. Smallest interactive target: 44px on the branch, 30px on main.
- Keyboard: opened with Enter on the card. Tab presses stayed inside the dialog (25 presses at each width). Escape closed the dialog and focus returned to the card at each width.
- Mouse: a click on the card opened the dialog at 1440.
- Motion: the branch modal animation is `album-modal-rise` with motion allowed and `none` with `prefers-reduced-motion: reduce`. Main has no modal animation.
- Error state (tracklist request returns 500): the status reads "Could not load tracklist: RECONSTRUCTED failure" with the error state. Screenshot `branch-modal-error-1440-RECONSTRUCTED.png`.
- Console and network: four console errors on both builds, each `net::ERR_TUNNEL_CONNECTION_FAILED` for the third-party platform icons (`raw.githubusercontent.com`, `cdn.simpleicons.org`, `community.qobuz.com`). These are known limit B2. No other console error and no HTTP error response on either build.
- Screenshots: `phase-6-album-modal/screenshots/main-modal-<width>-RECONSTRUCTED.png` and `branch-modal-<width>-RECONSTRUCTED.png`, for 1440, 1200, 900, 620 and 390. Every image is labelled RECONSTRUCTED.
- Not run: the live Navidrome library and real artwork; the owner's helper checklist; the Get request path (the search endpoint was not exercised, so Get behaviour is unchanged by code but not browser-tested here); keyboard traversal of the platform links; a screen-reader pass; Chromium only.

### 22.6 Limitations
- Chromium only; no screen-reader pass; no physical-device check.
- The platform icons are third-party images (B2). In the sandbox they fail to load and show text fallbacks; the fallback path is what the screenshots show.
- Close has no motion. Reduced motion and the open animation are verified only in the rendered browser runs above.

### 22.7 Next action
Owner: review the diff and the screenshots in `phase-6-album-modal/screenshots/`, run the album-modal checklist from `docs/TEST_PLAN.md` against the exact PR head on the owner's helper with a live library, and merge if satisfied. Next roadmap item: Phase 7 (motion, polish, hardening).

## 23. Redesign Phase 7 — Motion pass, item 1 (`ui/phase-7-motion-e3ntxn`, PR #392, merged, squash `46aa68e`)

Roadmap item: Phase 7, first bullet (apply the motion table once across the app; verify reduced-motion end states). Design system sections applied: 4.2 (yellow only for state), 9.2 (Get state machine kept), 9.3 (rail indicator), 9.5 and 9.6 (progress bar and skeleton), 9.8 (modal), 11 (motion table and tokens), 12 (reduced motion, accessibility floor). Base: `origin/main` at `759510e`.

Branch note: the session's designated branch is `ui/phase-7-motion-e3ntxn`, not the `ui/phase-7-motion` stem in the brief. The PR uses the designated name.

### 23.1 Acceptance criteria

- Every listed motion animates only `transform` or `opacity`; no `transition: all`; no `stroke-dashoffset`, `width`, `height`, or colour transitions.
- Durations use the section 11 tokens, except the two looping periods that section 11 does not name (see 23.5).
- `prefers-reduced-motion: reduce` leaves each animated element at its end state: no stranded toasts, the Get arc holds still, the tick is drawn, the modal and menu are visible at rest.
- Sort changes on Discover music reorder with a FLIP slide (transform only). Reduced motion shows the new order at once.
- No layout shift and no horizontal overflow at 1440, 1200, 900, 620 and 390px. 44px targets unchanged.

### 23.2 What changed

- `static/app.css`: removed `transition: all`-style colour transitions on buttons, Get control, album platform links, cards and card artwork; removed the card hover lift (`translateY(-2px)`, not in the table) and the artwork opacity fade; header menu fade is opacity-only on `--dur`; Get arc is a rotation (`transform`) about the glyph centre instead of a dash-offset animation; Get tick enters with opacity and `scale(.6)` on `--dur` instead of drawing its dash; card hover bar and the rail, row and progress motions use the tokens; reduced-motion rule for the tick now ends at `opacity: 1; transform: none`.
- `static/login.css`: removed the colour transition on the sign-in button (the reduced-motion rule stays).
- `static/app.js`: `recommendationKey(item)` extracted from the dismiss key (same value); rows carry `data-key`; `reorderRecommendations(render)` runs FLIP only from the sort control's `change` listener. Search and filter re-renders do not animate. The Get-button comment no longer describes a dash-offset draw.
- Tests: `tests/test_acquisition_ui_contract.py` assertions on the Get arc and tick were updated narrowly because the mechanism changed (dash-draw keyframes replaced by rotate and scale). No behavioural assertion was removed. New `tests/test_motion_ui_contract.py` (9 tests) enforces the table: no `transition: all`, transitions and keyframes limited to transform and opacity, no dash-offset or size animation, literal durations limited to the two loops, menu fade opacity-only, no card lift, reduced-motion end states, and FLIP limited to the sort control.

### 23.3 Measured results (Chromium, reconstructed fixtures)

Harness: `phase-7-motion/screenshots/motion_audit.py` serves `app/templates/index.html` and `static/` from each checkout and answers `/api` with synthetic recommendations (labelled RECONSTRUCTED). No backend, Navidrome or credentials were involved.

| Check | Before (`759510e`) | After (this branch) |
|---|---|---|
| Computed transition properties, normal motion | background, border-color, color, opacity, transform | transform only |
| Elements animating a non-transform/opacity property | 23 (colour and border transitions) | 0 |
| Get arc during pending | `get-arc-travel` (stroke-dashoffset) | `get-arc-travel` (rotate) |
| Get tick when requested | `get-tick-draw` (dashoffset 1 to 0) | `get-tick-in` (opacity and scale) |
| Running animations after a sort change, normal motion | 0 (no reorder motion) | 7 row FLIP animations |
| Running animations after a sort change, reduced motion | 0 | 0 |
| Animations at rest, reduced motion | none listed | none listed; tick opacity 1, transform none; arc static |
| Horizontal overflow at 1440/1200/900/620/390 | 0 at each | 0 at each |
| Pixels changed in recommendation renders | n/a | 3 pixels at 1440 (hover residue), 0 at 1200, 900 (≤1 level), 620, 390 |

Rendered screenshots: `phase-7-motion/screenshots/before-recommendations-{1440,1200,900,620,390}-RECONSTRUCTED.png` and the matching `after-` files; Get states at `get-is-pending-*` and `get-requested-*`. The before and after renders are pixel-identical in layout; the only visible change is the Get arc rotating and the tick entering, both of which are motion.

### 23.4 Checks actually run

- `node --check static/app.js`: pass.
- `python3 -m compileall -q app static`: pass.
- `pip install -r requirements.txt --break-system-packages`: pass (also installed `playwright` for the harness).
- `python3 -m unittest discover -s tests -v`: 884 tests, OK (baseline on `759510e`: 875, OK; +9 from the new motion contract file). Log: `phase-7-motion/screenshots/unittest-after.log`.
- Reduced-motion emulation in Chromium through Playwright (`reduced_motion="reduce"`): run and recorded above.
- Console: two `net::ERR_FAILED` errors appear on both before and after runs; they come from the harness aborting unmocked requests, not from app code.

### 23.5 Deviations and limits

- **Looping periods have no token.** The Get arc rotates over 1.15s and the skeleton pulses over 1.4s. Section 11 names no duration for loops, and `--dur-slow` (260ms) would spin the arc too fast. Both keep their periods and linear or ease-in-out timing. Hamdi to decide: add a loop token, or accept these two.
- **Hover colour is instant.** Section 11 lists `--dur-fast` for hover, but also says to animate only transform and opacity. I took the second rule, so hover fills and borders change without a transition.
- **Removed, not in the table:** the card hover lift, the artwork fade-in, and the colour transitions. If Hamdi wants the card lift kept, it is a one-line change, but it would be outside the table.
- **Not changed:** vendored Notyf toast animations (restyle-only, per section 9.6; reduced motion still shortens them and never removes them). The global `html { scroll-behavior: smooth }` and the JS scroll behaviour are existing tested behaviour, so I left them.
- **Reduced motion verified by emulation only in Chromium.** No real OS setting or screen reader was used. Toast reduced-motion timing was not exercised with a live toast.
- **Live library checks: skipped.** The sandbox has no Navidrome library, and the helper described in `docs/LOCAL_UI_TESTING.md` is not available here. Discover music was rendered from synthetic fixtures only.

### 23.6 Impeccable and skill guidance

- `impeccable` CLI: not installed in this sandbox, so `impeccable detect` did not run. No detector output is claimed.
- `anthropic-skills:web-design-guidelines`: run on the changed files (`static/app.css`, `static/login.css`, and `reorderRecommendations` and `recommendationKey` in `static/app.js`). Limit: the skill fetched its rules with WebFetch, which returned a paraphrase rather than the verbatim source, so this is a check against that paraphrase, not the exact published list.
  - Applied: the sort reorder now reads every row's new position before writing any animation (`static/app.js`, the `moves` pass), following the rule to batch DOM reads and writes.
  - Checked, no finding: no `transition: all`; only transform and opacity animate; reduced motion ends each animation at rest; transform origins are set on the Get arc and tick; hover feedback remains on buttons and cards.
  - Not in this diff and not changed: focus-visible styles, image dimensions on card artwork, and touch behaviour. Pre-existing items the rules would flag, left for later Phase 7 items.
- Applied from the motion table and section 12 rather than from a skill: transform and opacity only, reduced-motion end states, tokens for durations, no bounce or spring, FLIP limited to the one real reorder.
- Rejected: loop tokens invented outside section 11; a card hover lift; artwork fade-in; hover colour timing that would require a colour transition.

### 23.7 Next action

Owner: review the diff, the before and after screenshots and the motion audit JSON, and decide the two loop-duration questions in 23.5. Then run the live browser checklist from `docs/TEST_PLAN.md` against the exact PR head SHA on the owner's helper, including sort on Discover music and a Get request, before the remaining Phase 7 items (critique, audit, polish, harden, `DESIGN.md`, and the screen-reader pass).

## 24. Redesign Phase 7 — Audit, polish and harden, item 2 (`ui/phase-7-audit-harden-xnw111`, PR #394, merged, merge `7b26d10`)

Roadmap item: Phase 7, second bullet (audit and critique on every page, polish and harden what they find, fixes that fit the system). Design system sections applied: 4 (colour and contrast), 9.1 and 9.7 (button and form sizing), 9.4 and 9.5 (ranked row and acquisition row roles), 9.8 (modal artwork), 12 (44×44 floor, visible focus, status by text). Base: `origin/main` at `46aa68e`. Section 23 (PR #392) is marked merged here.

Branch note: the session's designated branch is `ui/phase-7-audit-harden-xnw111`, not the `ui/phase-7-audit-harden` stem in the brief. The PR uses the designated name.

### 24.1 Acceptance criteria

- Every audited page (dashboard, Discover music, New releases, Personal Discoveries, Add to your collection, Artist Deep Dives, Acquisitions, the four Settings tabs, login) has no control under 44×44 at 1440, 1200, 900, 620 or 390px, except where stated in 24.5.
- No horizontal overflow at the five widths. Text contrast meets 4.5:1 (3:1 large) on every rendered text element.
- Every focusable control shows a visible focus ring when reached by Tab.
- No album article is a button around its own Get, Dismiss or Try again controls.
- The album modal shows no broken-image glyph when artwork is absent or fails to load.
- No behaviour, endpoint, auth, acquisition or Get change. The Get state machine, Dismiss and settings-secret handling are untouched.

### 24.2 What changed

- `static/app.css`: settings text inputs 40px → 44px (`.settings-tab-panel input`); `.controls button`, `.controls select`, `.discovery-controls input` and `select` at `min-height: 44px`; `summary` (the diagnostics disclosure) at 44px; `.skip-link` at 44px; `.dashboard-picks-status` from 11px to `--text-xs` (12px).
- `static/app.js`: album articles (ranked rows, cards, acquisition rows) no longer carry `role="button"`. They keep `tabindex="0"`, their `aria-label`, and the existing Enter and Space handler that opens the modal. The modal artwork `<img>` is `hidden` until an artwork URL resolves, and hidden again if the URL fails to load (`error` listener).
- `tests/test_phase7_audit_ui_contract.py` (new, 7 tests): pins each fix above. No existing assertion was edited or removed.
- `docs/REDESIGN_ROADMAP.md`: PR #392 marked merged in item 1; item 2 status updated.

### 24.3 Measured results (Chromium, reconstructed fixtures)

Harness: `phase-7-audit-harden/screenshots/audit.py` (copied to the shared folder) serves `app/templates/index.html`, `login.html` and `static/` from a checkout and answers `/api` with synthetic data labelled RECONSTRUCTED. The before run used a detached worktree at `46aa68e`, with the same harness.

| Check | Before (`46aa68e`) | After (this branch) |
|---|---|---|
| Control or link under 44×44 (instances, 12 page states × 5 widths) | 131 | 0 |
| Horizontal overflow, max px across renders | 0 | 0 |
| Text under its contrast threshold | 0 | 0 |
| Lowest sampled text contrast (1440, dark ground) | 6.3:1 | 6.3:1 |
| Tab stops without a visible focus ring (dashboard 14, Discover 22) | 0 | 0 |
| Album articles with `role="button"` containing buttons | every card, ranked row and acquisition row | 0 |
| Modal opens from a focused article (Enter), closes on Escape | yes | yes |
| Broken-image glyph in album modal with no artwork | yes (screenshot) | none (screenshot) |

Rendered screenshots: `phase-7-audit-harden/screenshots/{before,after}-{dashboard,recommendations,acquisitions,settings-navidrome,login}-{1440,390}-RECONSTRUCTED.png` and the modal pair. Full JSON: `before-audit.json` and `after-audit.json`.

Console: the only errors are `net::ERR_FAILED` from the harness aborting third-party logo requests (24.5). The before run also showed a 404 for `/assets/cassette.png`, which was a harness path mapping error and is fixed in the harness, not the app.

### 24.4 Checks actually run

- `node --check static/app.js`, `node --check static/login.js`: pass.
- `python3 -m compileall -q app static`: pass.
- `pip install -r requirements.txt --break-system-packages`: pass.
- `python3 -m unittest discover -s tests -v`: 891 tests, OK (baseline on `46aa68e`: 884, OK; +7 from the new audit contract file). Log is in the session workspace.
- `impeccable detect` (CLI via the Impeccable skill launcher, now available; it was missing in the last session): ran on `static/app.css`, `static/app.js`, `app/templates/index.html`. See 24.6.
- Automated audit at five widths: run on `46aa68e` and on this branch as in the table above.

### 24.5 Limits, deviations and open items

- **Third-party logo requests in the album modal (B2, not fixed).** Platform links load logos at runtime from `cdn.simpleicons.org`, `raw.githubusercontent.com` and `community.qobuz.com`. AGENTS.md forbids runtime third-party assets. Fixing this means vendoring brand logos under `static/vendor/` with their licences, or dropping the images for text labels, which is a brand and licensing decision. Left for Hamdi. Without the images the links show abbreviations ("Li", "Ap", "Sp") as fallback text in the harness.
- **Bottom tab bar under 620px (Hamdi's call, not redesigned).** The seven destinations still scroll sideways at 390px; four are visible in the 390px render. Shorter labels or a More tab would change the shell, so this is reported, not changed.
- **Screen reader pass: not done.** No screen reader was available. The role change in 24.2 is based on the ARIA rule about interactive descendants, not on a spoken test.
- **Album articles keep an `aria-label`.** The label ("View details for …") now names the article, so a screen reader may announce the Get or Dismiss buttons inside it as part of the article. Verifying that needs the screen-reader pass above.
- **Live library and the isolated helper: skipped.** `~/navi-librarian-test/test-pr.sh` is not present in this sandbox, and the cloud sandbox has no Navidrome library. Every check above used reconstructed fixtures. The manual checklist from `docs/TEST_PLAN.md` against the exact head SHA is not run here and is for Hamdi.
- **Reduced motion.** This PR changes no animation. The motion checks from section 23 still hold (`tests/test_motion_ui_contract.py` passes).
- **Remaining font and radius drift.** The detector's advisory notes (about 33) flag literal sizes such as 11px, 13px and 18px, radii of 3px and 999px, and undocumented colours against `DESIGN.md`. They are advisory and not fixed in this PR; they belong to the `DESIGN.md` regeneration and a typography decision at the end of Phase 7.

### 24.6 Impeccable and skill guidance

- **Impeccable CLI and skill:** the `impeccable` CLI ran (`detect`, `context`). The Impeccable skill was loaded for `audit`. Its launcher supplied PRODUCT.md and DESIGN.md, and its craft-floor reference was read before editing.
- **`impeccable detect` on the changed files (4 findings, all rejected with reason):**
  - `static/app.css:390` `.card-art::after` and `static/app.css:518` `.ranked-row::before`, flagged as `side-tab` (3px coloured stripe). Rejected: DESIGN_SYSTEM 9.4 specifies the 3px yellow row bar as the ranked-row hover state, and the card-art stripe is the existing accent. Both are kept.
  - `app/templates/index.html`, `<img id="albumModalArtwork">` with no `src`, flagged `broken-image`. Rejected as a false positive for this slice: the image is hidden until an artwork URL resolves (24.2), so no broken box renders. Keeping the element avoids a placeholder data URI.
  - `app/templates/index.html`, `.settings-tabs` flagged `cramped-padding`. Rejected: the tab bar's `margin-bottom: -1px` is the design's active-underline seam on the tablist border, and it is intentional.
- **Impeccable guidance applied:** craft-floor refusal list checked (no gradient text, no added coloured `border-left`, no glass, no hard shadows, no eyebrow labels). Focus rings, tabular data and the Get states kept as they are. The detector's advisory font and radius notes were reviewed and deferred (24.5).
- **Impeccable guidance rejected:** the card hover lift, a new loop token, and any re-roll of the Chart Rundown direction, which the project's rules forbid.
- **`anthropic-skills:web-design-guidelines`:** the fetched guidelines came back as a summary, not verbatim, so this check is against that summary only. Applied to the changed files: accessible names on icon and link controls, visible focus and no outline removal, no interactive descendants in a button, no broken image shown, live status left as it was. Not applied, out of scope: text-wrap balance, tabular numerals in new places, and touch-action on the carousel.
- **`/impeccable document`:** not run. The roadmap runs it at the end of Phase 7.

### 24.7 Next action

Owner: review this PR's diff and the before and after screenshots, then decide the open items in 24.5, mainly the album-modal logos (B2) and the bottom-tab overflow under 620px. Then run the `docs/TEST_PLAN.md` checklist against the exact head SHA on the isolated helper, with a screen-reader pass on the album article and the Get control, before Phase 7's `DESIGN.md` regeneration.

## 25. Redesign Phase 7 — DESIGN.md and performance record, item 3 (`ui/phase-7-document-ryetdc`, PR #396, merged, squash `173a8fa`)

Roadmap item: Phase 7, the `DESIGN.md` regeneration and the Phase 0 performance comparison (roadmap section 4, Phase 7 bullets 3 and 4). Design system sections applied: 4 to 12 (read against the built CSS), and 15 (decisions, unchanged). Base: `origin/main` at `8849e7e`, which includes PR #394 (merge `7b26d10`). Designated branch: the session brief named the stem `ui/phase-7-document`; the session's designated branch was `ui/phase-7-document-ryetdc`, and the PR uses that name.

Status, kept separate: **implemented**: docs only (`DESIGN.md`, `docs/DESIGN_SYSTEM.md` section 16, roadmap and this section). **Automated-tested**: yes, listed in 25.4. **Browser-tested**: performance capture only, in headless Chromium against a live empty sandbox; no manual checklist and no screenshots (25.5). **Merged**: yes, PR #396, squash `173a8fa`, on Hamdi's instruction after a clean check on head `e5974ef`. **Published**: no. **Deployed**: no. **Runtime-verified**: no.

### 25.1 Acceptance criteria (stated before the work)

- `DESIGN.md` is regenerated from the built CSS, keeps the eight canonical sections in order, and its frontmatter tokens match `static/app.css`. No code, API or test change.
- `docs/DESIGN_SYSTEM.md` section 16 records each drift between section 4 to 12 and the built front end, with a status (match, accepted, open) and a next step. No value in sections 4 to 12 is silently changed.
- Transfer size, request count, third-party requests, FCP, LCP where recorded, and CLS are measured against the Phase 0 baseline (section 9.5), using the same profile, and the result is stated including its limits.
- Roadmap item 2 shows PR #394 merged; this section and section 24 agree.
- Checks run and recorded: `node --check static/app.js`, `node --check static/login.js`, `python3 -m compileall -q app static`, `python3 -m unittest discover -s tests -v`.

### 25.2 What changed

- `DESIGN.md`: regenerated. The frontmatter is unchanged (the tokens already matched the built `:root`). The body was rewritten to describe the built system: the Phase 7 state of the layout breakpoints, the self-hosted fonts, the Get control's shapes, the modal, motion, and the known exceptions, which are listed as exceptions and not as system rules. The Impeccable "Overview" voice and the North Star were kept from the owner-approved Phase 1 text.
- `docs/DESIGN_SYSTEM.md`: new section 16 (drift record, 14 rows, detector result, performance table, owner decisions). No other section edited.
- `docs/REDESIGN_ROADMAP.md`: Phase 7 status paragraph only. PR #394 marked merged; item 3 added.
- `docs/UI_BACKLOG_EXECUTION.md`: section 24 heading marked merged; this section 25 added.
- No front-end, template, test, API, auth or backend file changed.

### 25.3 Impeccable guidance applied and rejected

- **Applied:** `/impeccable document` (the Impeccable skill, loaded this session). Its context loader ran and read `PRODUCT.md` and the existing `DESIGN.md`. The document reference's scan mode was followed: tokens taken from `static/app.css`, components and states from its rules, and the drift check. The canonical section order and the Named-Rule style were kept where the built system supports them.
- **Applied:** `impeccable detect --json static/app.css` run once (34 advisory findings, classed in `docs/DESIGN_SYSTEM.md` section 16.2).
- **Rejected:** the sidecar `.impeccable/design.json`. The reference calls for it in scan mode, but `.impeccable/design.json` is not in the `AGENTS.md` file list (only `.impeccable/surfaces/**` is), so it is proposed here rather than written. The same goes for the components in the sidecar.
- **Rejected:** the scan mode's qualitative questions (North Star options, colour names, elevation philosophy). This run is autonomous and could not ask. The existing owner-approved text was kept, and the sections it does not cover are the open items.
- **Rejected:** the "refresh, overwrite or merge" prompt. The roadmap requires regeneration at this point, and the old file is in the PR diff.
- **Rejected:** fixing the drift in code. The roadmap asks for drift to be recorded, not fixed, in this item, and the drift rows are follow-up work.

### 25.4 Checks actually run

| Command | Result |
|---|---|
| `pip install --break-system-packages -r requirements.txt` | exit 0 |
| `node --check static/app.js` | clean |
| `node --check static/login.js` | clean |
| `python3 -m compileall -q app static` | clean |
| `python3 -m unittest discover -s tests` | **891 tests, OK** (`Ran 891 tests in 3.252s`). Phase 0 recorded 709 tests on `main` `dc3e5a3`; the count rose with the Phase 1 to 7 tests. |
| `impeccable detect --json static/app.css` | 34 advisory findings (exit 2 means findings present). Not a gate. |

### 25.5 Browser capture (performance only)

- Chromium `/opt/pw-browsers/chromium` through Playwright (Node), headless, 1440x900, cache disabled, a new context per run, three runs, 150 ms latency, 1.6 Mbit/s down, 750 Kbit/s up, 4x CPU. Same profile as section 9.5.
- Server: `uvicorn app.main:app` on `127.0.0.1:8189` from the checkout at `8849e7e`, with `NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` pointing at a scratch directory outside the repository, `SLSKD_URL=http://127.0.0.1:9` and an empty API key. The helper `~/navi-librarian-test/test-pr.sh` is not in this sandbox, so the isolation was reproduced by hand, as in section 9.2. An owner account was created through `POST /api/auth/setup` with a sandbox password. `git status` stayed clean.
- Live state only (empty sandbox, no library, no reconstructed responses). Discover was reached by clicking the rail item with `data-page="recommendations"`; its label reads "Recommendations" (drift row 3).
- **Not run:** keyboard walk, five-width screenshots, console and network review beyond the request list, the manual checklist in `docs/TEST_PLAN.md`, and anything on the exact head SHA of a PR (none existed when the capture ran).

### 25.6 Results

The numbers are in `docs/DESIGN_SYSTEM.md` section 16.4. In short: the dashboard transfer rose from 206,610 to 339,582 bytes and Discover from 206,845 to 365,229 bytes, almost all of it the self-hosted fonts that the Phase 0 baseline could not download (Google Fonts was blocked there). Font bytes are 108 to 134 KB, inside the 150 KB budget. Requests to third-party hosts fell from one (blocked) to zero. FCP stayed between 1.04 and 1.35 s. CLS is about 0.00009, against 0 in the baseline, which is not perceptible.

### 25.7 Limitations

- The sandbox is Chromium only, has no screen reader, and has no real library. Populated states were not captured.
- The performance run is loopback with emulated throttling. The font bytes cost more on a real link than this run shows; the Phase 0 numbers were optimistic for the same reason. The two sets are not comparable beyond bytes.
- LCP element was not recorded in this run (Phase 0 recorded `#dashboardHeading`).
- The drift rows are reported, not fixed. Rows 1 to 3 and row 10 need owner decisions (`docs/DESIGN_SYSTEM.md` section 16.5).
- The duplicate `/assets/cassette.png` network entry (one as Image, one as Other) was not investigated.

### 25.8 Next action

Hamdi reviews this PR's diff (docs only) and decides the owner items in `docs/DESIGN_SYSTEM.md` section 16.5, starting with the rail width and the "Recommendations" label. After that, a follow-up typography PR (drift row 4) and a gradient and colour removal PR (rows 5 to 7), each with before and after screenshots at the five widths. The manual checklist from `docs/TEST_PLAN.md` against the exact head SHA of this PR is still to be run by the owner.

## 26. Redesign Phase 7 — Typography to the type ramp, item 4 (`ui/phase-7-typography-zfk4p0`, PR #398, merged, squash `bce6017`)

Roadmap item: Phase 7, item 4, added by this PR (`docs/REDESIGN_ROADMAP.md`, Phase 7 status). It closes `docs/DESIGN_SYSTEM.md` section 16.2 row 4. Design system sections applied: 5 (type ramp and rules), 9.7 (forms and tabs, unchanged), 12 (floor and performance), 13 (page-head cap). Base: `origin/main` at `173a8fa`, which includes PR #396. PR: #398, merged as squash `bce6017`. Head reviewed: `ed34127`; CI on that head was green (compile, test-and-build, container-smoke, validate-container).

Status, kept separate: **implemented**: yes, in `static/app.css` and one narrow test assertion. **Automated-tested**: yes, 26.4. **Browser-tested**: sandbox render at five widths on four pages plus a clipping check on the populated dashboard, 26.5. A keyboard walk, the screen-reader pass and the manual checklist were not run on this change (26.7). **Merged**: yes, PR #398, squash `bce6017`, after Hamdi's review and test. **Published**: no. **Deployed**: no. **Runtime-verified**: no.

### 26.1 Acceptance criteria (stated before the work)

- No text below 12px (`--text-xs`) anywhere in `static/app.css`.
- Every literal `font-size` or `font` size that is off the section 5 ramp (9, 10, 11, 14, 16, 18, 23, 28, 29, 34, 36px) moves to the nearest step, and the mapping is written down (26.2).
- The 29px header title and the 34px desktop `.panel h2` go to 30px (`--text-2xl`), as decided by Hamdi in the Design doc thread. Section 13 caps the page head at 30px.
- The on-ramp literals (12, 13, 15, 20, 24, 30px) are written as ramp tokens. Their values do not change.
- No horizontal overflow at 1440, 1200, 900, 620 and 390px. No truncated or clipped labels on the pages whose text changed.
- Out of scope and unchanged: the display face in controls and data, the "Recommendations" rail label, radius (row 8), gradients and colours (rows 5 to 7), the primary button (row 10), the rail width and gutter (rows 1 and 14), and every behaviour, API, auth and Get/Dismiss path.

### 26.2 What changed

The mapping, per declaration. "Display" means the display face is kept; only the size moved.

| Was | Count | Where | Now |
|---|---|---|---|
| 9px | 1 | `.card-category` (card category label) | 12px `--text-xs` |
| 10px | 3 | `.card-art-placeholder` (mono), `.genre-tag`, footer | 12px `--text-xs` |
| 11px | 8 | `.get-album` base, `.card .card-art .get-album`, `.card .card-actions .get-album`, `.card-meta, .card-source`, `pre, #result`, `.quality-priority-position`, `nav .nav-count` (≤900px), `nav button` (≤620px) | 12px `--text-xs` |
| 14px | 1 | `.acq-glyph` (status mark, mono) | 15px `--text-base` (a tie with 13px; the larger step keeps the glyph legible) |
| 16px | 2 | `h3` (base), `.row-date-day` (display) | 17px `--text-md` |
| 18px | 4 | `.quality-priority-grip` (glyph), `.card h3`, `.acq-row h3`, `.ranked-row h3` (≤620px) | 17px `--text-md` |
| 23px | 1 | `.genre-row-heading h3` (display) | 24px `--text-xl` |
| 28px | 2 | `.card-art-placeholder::before` "NL / 01" (display), `.rank-numeral` (≤620px) | 30px `--text-2xl` |
| 29px | 1 | `header h1` (display) | 30px `--text-2xl` (Hamdi) |
| 34px | 1 | `.panel h2` (desktop) | 30px `--text-2xl` (Hamdi; section 13 cap) |
| 36px | 1 | `.rank-numeral` (desktop) | 30px `--text-2xl` (nearest text step, see 26.7) |

Total: 25 off-ramp declarations on `origin/main`, 0 on this branch. The regex count on `origin/main` found 57 literal sizes in all, of which 25 were off the ramp; the other 32 were on the ramp and are now tokens with unchanged values.

Other changes in this PR:

- **Bottom tab bar under 620px:** the horizontal padding of each tab went from 4px to 8px. At 12px the labels "Recommendations" and "New releases" sat against each other with 4px padding. The bar still scrolls sideways, the owner item in `docs/DESIGN_SYSTEM.md` section 16.5 (row 2).
- **`tests/test_new_releases_ui_contract.py`:** one assertion pinned the literal `.row-date-day { font: 600 16px/1.2 …`. It now expects `var(--text-md)`. The assertion's purpose, that the release date is plain text and not the red numeral, is unchanged. This is the only test change.
- **`docs/DESIGN_SYSTEM.md` section 16.2 row 4:** marked fixed, with the remaining note on the rank numeral.
- **`docs/REDESIGN_ROADMAP.md`:** Phase 7 status gains item 4. Item 3's status is not edited in this PR.

`font-size: 0` on the two hidden placeholder labels (`.acq-row .card-art-placeholder`, `.ranked-row .card-art-placeholder`) is kept. It hides text that the layout does not show, and no size is applied to visible text.

### 26.3 Impeccable guidance applied and rejected

- **Impeccable CLI:** not available in this sandbox (`npx --no-install impeccable` fails). `impeccable detect` was **not run** on `static/app.css`, before or after. The advisory font-size count from section 16.3 (24 findings) is the last recorded detector result, and this PR removes all of the literal font sizes it counted.
- **Impeccable skill:** not loaded in this run. The typography rules were applied from `docs/DESIGN_SYSTEM.md` section 5 and `DESIGN.md`, not from the skill's guidance.
- **Applied:** the ramp rules in section 5 (floor 12px, no off-ramp sizes, display face kept to the page head and data-free labels).
- **Rejected:** moving the rank numeral to the 56px `--num-row` token. Section 5 names that token, but it is a layout change to the ranked row, not a typography step, so it is left for a separate decision.
- **Rejected:** changing the display face on controls or data cells. Hamdi named that as out of scope.

### 26.4 Checks actually run

| Command | Result |
|---|---|
| `pip install --break-system-packages -r requirements.txt` | exit 0 |
| `node --check static/app.js` | clean |
| `node --check static/login.js` | clean |
| `python3 -m compileall -q app static` | clean |
| `python3 -m unittest discover -s tests -v` (this branch) | **894 tests, OK**. The first run had one failure, `test_release_date_column_is_plain_text_not_the_red_numeral`, which pinned the 16px literal. After the narrow update it passes. |
| `python3 -m unittest discover -s tests` (`origin/main`, same sandbox, before the edits) | **894 tests, OK** |

### 26.5 Browser (sandbox, RECONSTRUCTED fixture, not the owner's helper)

- `~/navi-librarian-test/test-pr.sh` is not in this sandbox. Two isolated uvicorn servers were run by hand: `origin/main` `173a8fa` (extracted with `git archive`) on `127.0.0.1:8301`, and this branch on `127.0.0.1:8302`. Each had its own `NAVIDROME_LIBRARIAN_DATA_DIR`, `NAVIDROME_MUSIC_DIR` and `SLSKD_DOWNLOADS_DIR` under a scratch directory outside the repository, `SLSKD_URL=http://127.0.0.1:9`, an empty key, and Navidrome unconfigured.
- Owner account created with `POST /api/auth/setup` and signed in with `POST /api/auth/login`. Chromium 1194 through Playwright, reduced motion, 1440, 1200, 900, 620 and 390px.
- Pages captured: sign-in entry (`/`, with the login stylesheet), Dashboard, Acquisitions and Settings. The Dashboard shows a **RECONSTRUCTED** fixture of six albums on `/api/dashboard-picks` (labelled in the file names). There is no artwork (`/api/artwork` answered 404), so the placeholders read "COVER NOT FOUND".
- **Not captured:** Recommendations, New releases, Personal Discoveries, Add to your collection, Artist Deep Dives, and the album modal. These have text that changed (ranked rows, the date column, the artist-deep-dive heading) but their populated states need fixtures I did not build here. They are skipped, not passed.
- **Overflow:** `scrollWidth − clientWidth` was 0 at every width on the four pages, before and after.
- **Sizes:** before, the four pages carried 9px, 10px and 11px text (up to 13 elements at 11px on the narrow widths). After, no text is below 12px on any of them.
- **Clipping:** a script checked every text element in `#dashboard`, the rail and the header on the populated dashboard for `scrollWidth > clientWidth` under a hidden overflow. It found none, before or after, at the five widths.
- **Visual check:** the after screenshots were read at 1440 and 390px. The category labels, the Get circles and the placeholder "NL / 01" fit. The 390px tab labels were tight before the padding change and have about 8px between them after it.
- **Console and network:** the only console messages were two 404s on `/api/artwork` in both the before and after runs, from the fixture's no-artwork answer. No `pageerror` was logged.
- **Keyboard walk and screen-reader pass:** not run for this change. It changes no focus order, role or name. Skipped, not passed.
- Screenshots and results are in `/mnt/project-files/phase-7-typography/screenshots/` (names `before-*` and `after-*`, with `-dashboard-RECONSTRUCTED` on the fixture pages). Results JSON: `before-results.json` and `after-results.json`.

### 26.6 Limitations

- No real library and no artwork. Populated Recommendations, New releases, Personal Discoveries, Add to your collection, Artist Deep Dives and the album modal were not captured (26.5).
- The Impeccable detector and skill did not run (26.3). The detector's font-size count is therefore not re-measured; the literal count was re-measured by regex.
- The rank numeral is now 30px on desktop (was 36px), a visible shrink on the ranked rows. The 56px `--num-row` token is the section 5 target and remains undecided.
- The 390px bottom bar is still a horizontal scroller with seven destinations (owner item, section 16.5 row 2).
- No keyboard, screen-reader or manual checklist run on the exact PR head.

### 26.7 Next action

Hamdi reviews the before and after screenshots and this table. If the 30px rank numeral is too small on the ranked rows, decide between 30px and the `--num-row` token before the rank numeral is touched again. Next roadmap item after this one: the gradient and colour removal (section 16.2 rows 5 to 7), with before and after screenshots at the five widths.

## 27. Redesign Phase 7 — Rank numerals to the 56px row token and rank 1 lead, item 6 (`ui/phase-7-rank-numeral-nk9ue4`, PR #400, merged)

Roadmap item: Phase 7, follow-up item 6 (`docs/REDESIGN_ROADMAP.md`, Phase 7 status). It closes the rank numeral row of `docs/DESIGN_SYSTEM.md` section 16.2 row 4, applies the rank 1 lead size (row 15), and records the Get shadow decision (row 6). Design system sections applied: 5 (`--num-row`, `--num-lead`), 8 (rank numeral truthfulness rules), 9.4 (ranked row). Base: `origin/main` at `daf424d` (includes PR #398 squash `bce6017` and PR #399 `daf424d`), then merged with `origin/main` at `870992c` (PR #389, a three-line backlog doc change) by merge commit, no rebase. The branch name the brief gave was `ui/phase-7-rank-numeral`; the branch assigned for this session is `ui/phase-7-rank-numeral-nk9ue4`, and that is the one used.

Status, kept separate: **implemented**: yes, in `static/app.css` only (no JavaScript, template or test change). **Automated-tested**: yes, 27.4. **Browser-tested**: sandbox render at five widths on the three lists that show numerals, plus the Discover sort check, 27.5. Keyboard walk, screen-reader pass and the helper checklist were not run (27.5). **Merged**: PR #400, after Hamdi's decision on 2026-10-19 that rank 1 uses 80px and the muted index numerals are smaller than the red rank. **Published**: no. **Deployed**: no. **Runtime-verified**: no.

### 27.1 Acceptance criteria (stated before the work)

- `.rank-numeral` uses `--num-row` (3.5rem, 56px) at every width, replacing 30px on desktop and the 30px phone override.
- Rank 1 uses `--num-lead` (5rem, 80px) on wide screens (above 1200px, where the 72px numeral column has room). Rank 1 is the first row of a numbered list only.
- Muted index numerals (`.is-index`) are smaller than the red rank: `--text-2xl` (30px), at every width. Decided by Hamdi.
- Both tokens are defined on `:root`. Section 5 and `DESIGN.md` already named them, but `static/app.css` did not define them before this PR.
- Numerals appear only where the list has a sort basis the API returns, and the basis is named in the status line. Lists sorted by name, or with missing values, show no visible numeral.
- No horizontal overflow at 1440, 1200, 900, 620 and 390px; no numeral overlaps artwork; no title or Get control is pushed out of its row; the row height of a non-rank-1 row does not change.
- Focus, reduced motion, landmarks and the skip link are unchanged (no rule in those areas was touched).

### 27.2 What changed

- `static/app.css`, `:root`: `--num-row: 3.5rem; --num-lead: 5rem;` added, with a comment.
- `static/app.css`, `.rank-numeral`: font size `var(--text-2xl)` becomes `var(--num-row)`. The display face, weight 600, tabular figures and the `--chart-red-text` colour are kept.
- `static/app.css`, `.rank-numeral.is-index`: `font-size: var(--text-2xl)` added, so muted index numerals are 30px.
- `static/app.css`, new `@media (min-width: 1201px)` rule: `.ranked-list > .ranked-row:first-child > .rank-numeral:not(.is-index)` takes `--num-lead`. The selector matches only the first numbered row, so the release-date list (which has no numeral) and index lists are not affected.
- `static/app.css`, `@media (max-width: 620px)`: the 30px phone override is removed, so the phone numeral is the `--num-row` token. Phone numeral column goes from 36px to 44px. At 56px a two-digit numeral measured 37px wide, so 36px overflowed its track by 1px. Rank 1 is not enlarged on phones (the lead rule only applies above 1200px).
- Not changed: the skeleton numeral (`.is-skeleton .rank-numeral`, which keeps its own placeholder blocks), the date column on New releases, the `is-index` colour, the Get control shadow, and every JavaScript path.

### 27.3 Which lists show numerals and on what basis

Read from `static/app.js` (`rankingBasis`, `buildRecommendationRow` and the three builders). No numbering was added.

| List | Numerals | Size | Basis (status line) |
|---|---|---|---|
| Discover music (`#recommendationCards`) | Red numeral when the sort has a complete API value; rank 1 is the lead size above 1200px | 56px, rank 1 80px above 1200px | "Ranked by discovery score" (`score`), "Ranked by Last.fm artist listeners" (`popularity`), "Recommended order" (`original`, the server order). When a value is missing for any album, the numeral is hidden and the line says so. |
| Discover music, "Artist A–Z" | None (the numeral element stays as an empty grid slot so artwork keeps its column) | n/a | "Sorted A–Z by artist" |
| Personal Discoveries (`#personalCards`) | Muted index (`is-index`), not red | 30px | "Engine order, not ranked by discovery score" |
| Add to your collection (`#classicsCards`) | Muted index (`is-index`), not red | 30px | "Picked for exploration, not ranked by score" |
| New releases | None; the release date replaces the numeral | n/a | Release-date order |

Decision: Hamdi chose on 2026-10-19 that rank 1 uses `--num-lead` (80px) on wide screens, and that the muted index numerals are smaller than the red rank (30px here). The index size is the text ramp's `--text-2xl`, chosen so the index stays readable but does not compete with the red rank.

### 27.4 Checks actually run

- `node --check static/app.js`: passed.
- `node --check static/login.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `pip install --break-system-packages -r requirements.txt`: installed on the Python 3.13 sandbox.
- `python3 -m unittest discover -s tests -v`: **Ran 894 tests, OK**, run after the final CSS change and after the merge with `origin/main`. The count matches the 894 recorded for `main` at `bce6017`. No `tests/*_ui_contract.py` file was edited, because no contract assertion names the numeral size.
- Impeccable detector (`npx --yes impeccable@latest detect --json`) on the same file before and after the first CSS change: **10 findings before and 10 after**, same types (2 `side-tab`, 4 `design-system-radius`, 4 `design-system-color`). None is a numeral finding. The count differs from the 34 findings in section 16.3, which came from an earlier CLI version; the same CLI was run on both files here, so the comparison is fair. The lead and index change was not re-run through the detector.
- The Impeccable skill guidance was not loaded in this session, so the design pass was made against section 8 and 9.4 directly. `web-design-guidelines` was not run as a separate skill pass.

### 27.5 Browser (sandbox, RECONSTRUCTED fixture, not the owner's helper)

Setup: local uvicorn servers, each with its own data directory under the session scratch folder, `SLSKD_URL=http://127.0.0.1:9` (slskd disabled), a sandbox account `sandbox.tester`. "Before" was a worktree at `bce6017`; "after" was the working tree at `daf424d` plus this change. Playwright (Chromium) at 1440, 1200, 900, 620 and 390px, one fresh context per run. The Discover, Personal Discoveries and Add to your collection responses were replaced with **RECONSTRUCTED** fixture rows (five albums, mixed scores and listener counts, one long title, one row with no score). The sandbox has no library, so this shows the DOM and layout, not real recommendations.

Two passes: the first "after" pass (56px for all numerals) and the final "after" pass with the lead and index rules. The final pass is the one reported here; its results are in `render-results-after-lead.json`. The "before" numbers are from the first pass, which ran against the unchanged `bce6017` worktree.

- **Numeral size, final after:** rank 1 is 80px above 1200px and 56px at 1200px and below; rows 2 to 5 are 56px; index numerals are 30px on Personal Discoveries and Add to your collection at every width. Before: 30px for everything.
- **Rank 1 row height at 1440:** 105px before and after. The 80px numeral is taller than the 64px artwork, but the text column sets the row height, so the row did not grow.
- **Overflow:** `scrollWidth − clientWidth` was 0 at every width, before and after, on all three lists.
- **Numeral box versus artwork:** rank 1 at 1440 is a 52px-wide, 80px-tall box; the artwork begins after it on every row at every width (no overlap, measured as `numOverflowsCol` false on the first five rows of each list).
- **Get inside its row:** true for all five rows of every list at every width, before and after.
- **Row height, deterministic lists:** Discover music rank 1 is 105px at 1440, 1200 and 900px, 170px at 620px, 211px at 390px, identical before and after. Personal Discoveries rank 1 is 103, 122, 122, 192 and 231px, identical before and after. Add to your collection changes with rotation between runs, so its heights are not compared.
- **Discover sort check (1440, final after):** "Highest discovery score" 5 numerals, "Most popular artists" 5, "Recommended order" 5, "Artist A–Z" 0 visible numerals (the basis line says "Sorted A–Z by artist"). The widest numeral box in the numbered sorts was 52px, from the rank 1 lead.
- **Console and network:** no console error or warning and no HTTP status 400 or above on any run. No `pageerror`.
- **Screenshots:** `/mnt/project-files/phase-7-rank-numeral/screenshots/`. `before-*-RECONSTRUCTED.png` (first before pass) and `after-*-RECONSTRUCTED.png` (final after pass, which replaced the earlier after images of the same names) for the three lists at five widths. Results: `render-results.json` (first pass, before and after) and `render-results-after-lead.json` (final after). Scripts: `render-numerals.mjs` and `render-after-lead.mjs`.
- **Keyboard walk and screen-reader pass:** not run. The numerals are `aria-hidden` and the change touches no focus, role or name. Skipped, not passed.
- **Manual checklist against the exact PR head SHA:** skipped. The owner's helper (`~/navi-librarian-test/test-pr.sh`) is not installed in this sandbox, so the sandbox servers above were used instead. This is not the exact-head helper run that `docs/LOCAL_UI_TESTING.md` requires.

### 27.6 Limitations

- Reconstructed fixture data, no real library and no artwork. Populated numeral appearance on a real list may differ in text length; the fixture shows two-digit numerals only.
- The Discover sort check changed the sort in the sandbox page only; the stored preference is not changed.
- The lead rule depends on the first numbered row being rank 1. That holds for the numbered sorts, where the list is sorted before rendering. If a future list shows a numeral on a non-rank first row, it needs its own rule.
- The 80px rank 1 is taller than its artwork. Row height is not changed at 1440, but a slow layout pass on a real device was not measured.
- The skeleton placeholders keep their own sizes. They do not match the 56px numeral's line box; no shift was seen, and it was not measured on a slow connection.

### 27.7 Next action

Next Phase 7 item: the gradient and one-off colour pass (`docs/DESIGN_SYSTEM.md` section 16.2 rows 5 and 7), with before and after screenshots at the five widths.

## 28. Redesign Phase 7 — Gradients and one-off colours, follow-up item 7 (`ui/phase-7-gradients-9djfjj`, PR #401, merged as squash `96fdc53`)

Roadmap item: Phase 7, follow-up item 7 (`docs/REDESIGN_ROADMAP.md`, Phase 7 status). It closes rows 5 and 7 of `docs/DESIGN_SYSTEM.md` section 16.2. Row 6 (shadows) and row 9 (artwork hover stripe) are not changed. Design system sections applied: 4 (tokens, usage rules), 13 (no gradients), 9.4 (artwork placeholder on ranked rows). Base: `origin/main` at `5cff896` (PR #400). The branch the brief named was `ui/phase-7-gradients`; the server suffixed it to `ui/phase-7-gradients-9djfjj`.

Status, kept separate: **implemented**: yes, in `static/app.css` and one new contract test file. **Automated-tested**: yes, 28.4. **Browser-tested**: sandbox render at five widths on the pages that show artwork placeholders, 28.5. **Merged**: yes, PR #401, squash `96fdc53`, after Hamdi's instruction on 2026-10-19. CI on the head `ec58f37` was green (`test-and-build`, `container-smoke`, `validate-container`, `compile`). **Published**: no. **Deployed**: no. **Runtime-verified**: no.

### 28.1 Acceptance criteria (stated before the work)

- No `gradient` in `static/app.css`. The artwork placeholder (`.card-art`, and the ranked-row artwork that inherits it) is a flat `var(--surface-raised)` fill.
- Every colour on the changed selectors is a token. No new colour value is added.
- Artwork placeholders still read as placeholders, with a visible edge (the existing 1px `--edge` border on the artwork).
- No horizontal overflow at 1440, 1200, 900, 620 and 390px.
- Focus rings, reduced motion, landmarks and the skip link are unchanged (no rule in those areas is touched).
- Out of scope, unchanged: radius (row 8), primary button (row 10), rail width and gutter (rows 1 and 14), the "Recommendations" label (row 3), the tab bar (row 2), numeral sizes (section 27), and every behaviour, API, auth and Get/Dismiss path. The Get shadow (row 6, overlay rule), the Notyf toast shadow (row 6, accepted) and the artwork hover stripe (row 9, accepted) are not touched. The stripe is still a yellow bar on hover; removing the gradient does not make it inconsistent with a flat fill, so it stays as recorded.

### 28.2 What changed

| Old value | Where | Now | Why |
|---|---|---|---|
| `linear-gradient(135deg, transparent 49.5%, rgba(233,198,74,.12) 50%, transparent 50.5%), var(--surface-raised)` | `.card-art` (dashboard tiles, deep dives, and the ranked-row artwork that inherits it) | `var(--surface-raised)` | Row 5. Section 13 bans gradients. The stripe colour `rgba(233,198,74,.12)` goes with it. |
| `#353124` | `.card-category` fill (the genre or discovery label on tiles and cards) | `var(--surface-hover)` (`#2d2926`) | Row 7. Nearest token in luminance to the old fill. Measured: the old fill is 1.34:1 against `--surface`, `--surface-hover` is 1.20:1, `--surface-raised` 1.10:1. Accent text on the fill is 8.83:1 before and 9.80:1 after. |
| `#2a2c29` | `.card-actions button` fill | `var(--surface-raised)` (`#252220`) | Row 7. Measured: the old fill is 1.23:1 against `--surface`, `--surface-raised` is 1.10:1. Chosen over `--surface-hover` so the resting control is darker than its hover state (`--surface-hover`), which keeps the hover change visible. |
| `rgba(0,0,0,.5)` | `.notyf__toast` shadow | unchanged | Row 6. The toast is a vendored component; its shadow was accepted. No token added. |
| `rgba(0,0,0,.55)` | `.get-album` shadow over artwork | unchanged | Row 6. Decided as an overlay rule (Hamdi, 2026-10-19). No token added. |
| `rgb(20 18 17 / .8)` | `.album-modal-backdrop` scrim | unchanged | `--ink` at 80%, as specified in section 9.8. Not a one-off. |

The `.card-actions` fill change lands on a path the current UI does not reach from the sandbox (see 28.6). It is made for token consistency, not because a visible state changed.

Files changed: `static/app.css` (three declarations, plus the removed gradient); `tests/test_flat_surfaces_ui_contract.py` (new, four assertions on the stylesheet); `docs/REDESIGN_ROADMAP.md`, `docs/DESIGN_SYSTEM.md` section 16.2 rows 5 and 7, and this section. No JavaScript, template, API or test assertion was changed.

### 28.3 Impeccable and design guidance

- `impeccable detect --json static/app.css` (`npx --yes impeccable@latest`): **10 findings before, 8 after**. The two removed findings were `design-system-color` for `#353124` and `rgba(233,198,74,.12)`. `#2a2c29` was not a finding. Remaining colour findings: `rgba(0,0,0,.55)` and `rgba(0,0,0,.5)`, both shadows accepted in row 6. Remaining radius findings (three 3px, one 999px) and the two `side-tab` stripes (`.card-art::after`, `.ranked-row::before`) are not in scope and are unchanged. The detector output is advisory; the side-tab stripes are row 9 and the ranked-row bar, which section 9.4 specifies.
- `/impeccable critique` and `/impeccable audit`: not run as the Impeccable skill in this session. The critique was made against sections 4, 9.4 and 13 and against the screenshots in 28.5. This is stated here so the review does not read as an Impeccable pass.
- `web-design-guidelines` compliance pass: not run as a separate skill pass in this session. The change is three declarations and a removed gradient; the contract test covers the points it would check here.
- Guidance applied: flat surfaces with a border for placeholders (section 13); token-only colour (section 4.2). Rejected: adding a new surface token for the artwork placeholder (section 4 says add no value that is not a token), and changing the artwork hover stripe (row 9, accepted).

### 28.4 Checks actually run

- `node --check static/app.js`: passed.
- `node --check static/login.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `python3 -m unittest tests.test_flat_surfaces_ui_contract -v`: 4 tests, OK.
- `python3 -m unittest discover -s tests -v`: **Ran 898 tests, OK** (894 on `main` plus the 4 new tests). A baseline run on `5cff896` before the change gave 894 tests, OK.
- Not run: `pip install` was run on the Python 3.13 sandbox before the suite, as the project instructions require.

### 28.5 Browser (sandbox, RECONSTRUCTED fixture, not the owner's helper)

Setup: two local uvicorn servers with their own data directories under the session scratch folder, music path under the sandbox, `SLSKD_URL=http://127.0.0.1:9` (slskd disabled), a sandbox account. "Before" is `origin/main` at `5cff896` (port 8101). "After" is the working tree of this branch (port 8102). Playwright (Chromium) at 1440, 1200, 900, 620 and 390px, one fresh context per run. `/api/dashboard-picks`, `/api/discovery/classics`, `/api/discovery/artist_deep_dive`, `/api/discovery/personal`, `/api/discovery/new_releases` and `/api/recommendations` were answered with **RECONSTRUCTED** fixture rows (six albums, one long title, no artwork), so every card shows the artwork placeholder. Artwork and bio routes were answered with `artwork_url: null`.

- Pages rendered: Dashboard tiles, Add to your collection (ranked rows), Artist Deep Dives, Discover music. Screenshots in `/mnt/project-files/phase-7-gradients/screenshots/` as `before-<page>-<width>-RECONSTRUCTED.png` and `after-<page>-<width>-RECONSTRUCTED.png`, with the script `render-gradients.mjs` and the numbers in `render-results.json`.
- Gradient: computed `background-image` on the artwork placeholder is a `linear-gradient` before and `none` after, at every width.
- Overflow: `scrollWidth − innerWidth` was 0 on every page at every width, before and after.
- Placeholder read: the dashboard tiles keep the "NL / 01" and "Cover not found" text, which carries the placeholder reading. On ranked rows the placeholder is a flat square with the 1px edge, which reads as an empty artwork slot. The edge is `--edge` (1.33:1 against `--surface`, decorative per section 4.1), so it is faint; this is recorded as a limitation, not a change.
- Category label: computed fill is `rgb(45, 41, 38)` (`--surface-hover`) after, `rgb(53, 49, 36)` (`#353124`) before.
- Console and network: no console error, warning or page error, and no request outside the local origin, on every run.
- Keyboard walk: not run. No focus, role or name rule was changed; the focus ring rule (`button:focus-visible`) is untouched. Skipped, not passed.
- Screen-reader pass: not run. Skipped.
- Album modal and Acquisitions: not rendered in this pass. The modal fixture and the acquisition state were not set up here. Skipped, not passed. The modal artwork uses `.album-modal-art` (a surface fill, not `.card-art`), so this change does not reach it.
- Manual checklist against the exact PR-head SHA with the owner's helper: skipped. The helper is not installed in this sandbox, so the sandbox servers above were used.

### 28.6 Limitations

- Reconstructed fixture data, no real library and no artwork. Real artwork covers the placeholder and the fills are not visible on populated cards.
- `.card-actions button` (the "Dismiss artist" fill): in the current UI, that row builder is reached only by a non-ranked, non-deep-dive list, and the sandbox renders none. Its computed fill was not measured on screen. The token change is made for consistency; no visible state was observed.
- The ranked-row placeholder edge is faint (`--edge` against `--surface`). It reads as a slot in the screenshot, but a stronger boundary would be a token decision (`--edge-strong` is the control-boundary token), not made here.
- The artwork hover stripe (row 9) remains a yellow bar on hover. Not changed.

### 28.7 Next action

Hamdi's decision on the remaining Phase 7 rows: radius (row 8), primary button (row 10), and the section 16.5 owner decisions (rail width, "Recommendations" label, phone tab bar, gutters). Not merged, published or deployed by the author.

## 29. Redesign Phase 7 — Radius to the chip token, follow-up item 8 (`ui/phase-7-radius-cux3ev`, PR #406, merged as squash `94824aa`)

Roadmap item: Phase 7, follow-up item 8 (`docs/REDESIGN_ROADMAP.md`, Phase 7 status). It closes row 8 of `docs/DESIGN_SYSTEM.md` section 16.2 and the radius decision in section 16.5. Base: `origin/main` at `96fdc53` (PR #401). Design system sections applied: 7 (shape: 2px chips and artwork, 4px controls, 6px panels and modal) and 9.2 (pill and circle for Get, kept). Hamdi approved radius as the next item on 2026-10-19.

The branch name is the one the server designated (`ui/phase-7-radius-cux3ev`). The requested name `ui/phase-7-radius` was not used.

Status, kept separate: **implemented**: yes, in `static/app.css` and one new contract test file. **Automated-tested**: yes, 29.4. **Browser-tested**: sandbox render at five widths, dashboard and header menu, computed radius before and after, 29.5. **Merged**: yes, PR #406, squash `94824aa`. **Published**: no. **Deployed**: no. **Runtime-verified**: no.

### 29.1 Acceptance criteria (stated before the work)

- No `border-radius` in `static/app.css` is 3px. Every radius on the changed selectors is a token (`--radius-chip`, 2px).
- The 999px pill (ranked-row Get) and the 50% circles (artwork Get) are unchanged, as section 9.2 requires.
- No change to layout beyond a 1px corner. No horizontal overflow at 1440, 1200, 900, 620 and 390px.
- Focus rings, landmarks, skip link, reduced motion, the rail indicator's motion and every behaviour, API, auth and Get/Dismiss path are unchanged.
- Out of scope, unchanged: primary button (row 10), rail width and gutter (rows 1 and 14), the "Recommendations" label (row 3), the tab bar (row 2), shadows (row 6) and the artwork hover stripe (row 9).

### 29.2 What changed

Row 8 said "a 3px literal on rail items and two labels". The stylesheet has three 3px declarations, not two labels. They are recorded here as found:

| Selector | Old | Now | Why |
|---|---|---|---|
| `nav button` (rail items, 621px and wider) | `border-radius: 3px` | `var(--radius-chip)` | Rail item, row 8. |
| `.nav-indicator` (the 3px yellow bar on the active item) | `border-radius: 0 3px 3px 0` | `0 var(--radius-chip) var(--radius-chip) 0` | Rail item indicator, row 8. The bar stays 3px wide; only the rounded end moves to the 2px chip. |
| `.header-menu-panel button` (Settings and user menu items) | `border-radius: 3px` | `var(--radius-chip)` | The menu items are the "labels" in row 8. The menu panel itself stays `--radius-panel` (6px). |

Files changed: `static/app.css` (three declarations); `tests/test_radius_scale_ui_contract.py` (new, four assertions on the stylesheet); `docs/REDESIGN_ROADMAP.md` (Phase 7 status); `docs/DESIGN_SYSTEM.md` section 16.2 row 8 and section 16.5; this section. No JavaScript, template, API or existing test was changed.

Not changed: the `.genre-tag` declaration `border-radius: 2px` (line 404) already equals the token and was left as a literal; the `999px` and `50%` shapes; and the `4px` literals on controls (section 7 keeps 4px for controls, and they are outside row 8's 3px scope).

### 29.3 Impeccable and design guidance

- `impeccable detect --json static/app.css` (`npx --yes impeccable@latest`, run in this session): **8 findings before, 5 after**. Radius findings: **4 before, 1 after**. The one that remains is `border-radius: 999px` at line 568, the ranked-row Get pill, which section 9.2 keeps. The `side-tab` findings (rows 9 and 5) and the colour findings (rows 6 and the shadows) are unchanged and are not part of this slice.
- `/impeccable critique`, `/impeccable audit`, `/impeccable polish`: **not run** as the Impeccable skill in this session. The skill was not invoked. The visual judgement was made against section 7 and the before and after screenshots, and is recorded as such.
- `web-design-guidelines` compliance pass: **not run** as a separate skill pass. The change is three declarations; the contract test covers the points it would check here.
- Guidance applied: section 7's 2px chip radius for small rail and menu items; the indicator keeps its 3px width and only its rounded end is changed (section 9.3 indicator is unchanged in geometry).
- Rejected: changing the 999px and 50% Get shapes (section 9.2 matches); adding a new radius token; moving the menu panel off 6px; changing the 4px control radius.

### 29.4 Checks actually run

- `node --check static/app.js`: passed.
- `node --check static/login.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `python3 -m unittest tests.test_radius_scale_ui_contract -v`: 4 tests, OK on this branch. The same file run against the `96fdc53` stylesheet: 3 failures (the three old-value checks), as intended.
- `python3 -m unittest discover -s tests -v`: **Ran 902 tests, OK** (898 on `main` plus the 4 new tests).
- `pip install --break-system-packages -r requirements.txt` was run before the suite.

### 29.5 Browser (sandbox, RECONSTRUCTED fixture, not the owner's helper)

Setup: two local uvicorn servers (`app.main:app`), each with its own data directory under the session scratch folder, `SLSKD_URL=http://127.0.0.1:9` (slskd disabled), sandbox music and download paths, and one sandbox account. "Before" is a `git archive` of `96fdc53` (port 8101). "After" is the working tree of this branch (port 8102). Chromium through Playwright at 1440, 1200, 900, 620 and 390px. Screenshots are in `/mnt/project-files/phase-7-radius/screenshots/` as `before-dashboard-<width>-RECONSTRUCTED.png`, `after-dashboard-<width>-RECONSTRUCTED.png`, and the same two names with `header-menu`. The render script and results are in the session scratch folder.

- Computed radius, nav item: `3px` before, `2px` after, at every width where the rail shows (621px and wider). Under 620px the bottom bar uses the same `nav button` rule and also moved to `2px`.
- Computed radius, nav indicator: `0 3px 3px 0` before, `0 2px 2px 0` after, at 1440, 1200 and 900px where the bar shows. It is hidden under 620px (bottom bar), as before.
- Computed radius, header menu item: `3px` before, `2px` after, at all five widths. The panel stays `6px` before and after.
- Overflow: `scrollWidth − innerWidth` was 0 at every width, before and after.
- Console and network: no console error, warning or page error, and no request outside the local origin, on every run, before and after.
- Dashboard: the fixture has no library, so the page shows the empty state ("No suggestions yet"). The rail and header are real rendered output. No album or Get state was rendered, so the 999px Get pill and the 50% artwork circles were not visually re-checked in this pass. Their values are unchanged in the stylesheet.
- Keyboard walk: **skipped**. No focus, role or name rule was changed, and the `:focus-visible` rules are untouched. Not run as a walk.
- Screen-reader pass: **skipped**.
- Album modal, Acquisitions, Get states: **skipped**, not rendered (no fixture for those states in this sandbox).
- The owner's `test-pr.sh` helper: **not run** (not installed in this sandbox). The manual checklist against the exact PR-head SHA is **skipped** and is the next action before merge.

### 29.6 Limitations

- Reconstructed empty fixture, no library and no artwork. The change is small (1px corners on small items), so screenshots show it only as a close match; the computed-style comparison in 29.5 is the evidence.
- Under 620px the nav indicator is hidden and the bottom bar items are not separately measured beyond their computed radius.
- The 999px Get pill and the 50% artwork circles were not rendered in this pass (see 29.5).

### 29.7 Next action

Hamdi's review of the PR, then the manual checklist against the exact PR-head SHA with the owner's helper (sandbox paths, slskd disabled). Not merged, published or deployed by the author.


## 30. Redesign Phase 7 — Contrast re-measure of status pairs, follow-up item 9 (`ui/phase-7-contrast-cc6445`)

Roadmap item: Phase 7, follow-up item 9 (`docs/REDESIGN_ROADMAP.md`, Phase 7 status). It closes row 13 of `docs/DESIGN_SYSTEM.md` section 16.2 (contrast on the rendered build, which had been re-measured on Phase 1 empty states only). Base: `origin/main` at `bb25be0` (merge of PR #405, after radius PR #406 merged as `94824aa`). The designated branch name `ui/phase-7-contrast-cc6445` was used (the requested `ui/phase-7-contrast` was not; the server's suffix is the designated name). Design system sections applied: 4.1 (contrast rules), 4.2 (state colours never carry meaning alone), 9.5 and 9.6 (acquisition status row and status line), and 9.2 (Get states). Owner decisions in 16.5, the primary button (row 10), gutters (row 14) and the album modal logos (row 12) are out of scope.

### 30.1 Acceptance criteria (stated before the work)

- Every text-on-background pair for status (status line states, legacy `.error` and `.ok`, acquisition status and glyphs, Get states, the Notyf toasts) is measured with computed colours on the rendered build, before and after.
- WCAG 2.1 AA: 4.5:1 for text under 24px (or under 18.66px bold), 3:1 for large text and for non-text boundaries and glyphs that carry state.
- Only failing pairs change, and only to existing tokens. No new colour value.
- No change to behaviour, API, auth, Get/Dismiss paths, markup or the Get state machine. No horizontal overflow at 1440, 1200, 900, 620 and 390px.

### 30.2 What the measurement found

Method: `measure.mjs` (Playwright, the shipped `static/app.css`) renders each status selector once on five token grounds (`--ink`, `--surface`, `--surface-raised`, `--surface-hover`, `--accent-dim`), reads the computed colour and the effective opaque background (translucent layers composited), and computes WCAG 2.1 relative luminance. Each probe is the real class on a real element, so the stylesheet applies; the probe elements are reconstructed because the sandbox has no acquisitions and no albums. The `--accent-dim` ground was measured to show the failure, but it is not a ground any status text renders on (it is only the active header-menu item, which carries `--text`), so it is excluded from the verdict.

Result, on the four grounds that status text actually renders on (104 pairs):

- **Before: 4 failing pairs, all one control.** `.get-album.is-pending` border (`--accent-dim`) measured 2.15, 2.00, 1.82 and 1.66:1 on ink, surface, raised and hover. The text was 7.03:1 and passed. The pending state is announced by the arc and the muted label, but the control's boundary is the only thing that identifies it as a control on the card, so it fails 1.4.11.
- **Every status text and glyph pair passed before the change.** The tightest are `status-line is-error` and the legacy `.error` on `--surface-hover` (4.65:1) and `acq-profile` on hover (4.86:1). These pass, with small margins, and are recorded rather than changed.
- **Toasts pass.** Notyf success and error toasts (`--surface-raised` ground): message text 13.8:1; the icon discs measure 8.89:1 (`--ok`) and 5.10:1 (`--chart-red`) against their glyph.

### 30.3 What changed

| Selector | Old | Now | Why |
|---|---|---|---|
| `.get-album.is-pending` (`border-color`) | `var(--accent-dim)` (1.66 to 2.15:1) | `var(--accent)` (9.80 to 12.69:1) | Control boundary, row 13. It keeps the idle control's yellow ring; the pending state still differs from idle by the raised dark fill, the muted label and the travelling arc. |

`--edge-strong` was tried first (the documented control-boundary token). It measured 3.28:1 on raised and 3.60:1 on surface, but 2.99:1 on `--surface-hover`, which is the ranked-row hover ground where the Get pill sits, so it fails. `--accent` clears 3:1 on every ground.

Files changed: `static/app.css` (one declaration, plus its comment); `tests/test_status_contrast_ui_contract.py` (new, two assertions on the stylesheet); `docs/REDESIGN_ROADMAP.md`; `docs/DESIGN_SYSTEM.md` section 16.2 row 13; this section.

Not changed, and found outside scope: `.card-actions button:first-child` (`border-color: var(--accent-dim)`, `app/static/app.css` line 409 area). Its boundary is about 1.8 to 2.0:1 on surface and raised by the token values (computed from the tokens, not probed), but it is a card action, not a status pair. It is recorded for the owner, not fixed here.

### 30.4 Full measurements

Ratios are text (or the glyph, or the boundary where marked) on each ground. "→" shows the value after the change where it changed. Source: `measure.mjs` output, saved as `/mnt/project-files/phase-7-contrast/measure-before.json` and `measure-after.json`, with the script at `/mnt/project-files/phase-7-contrast/measure.mjs`. The table is generated from those files.

| Probe | ink | surface | raised | hover | Min before | Min after |
|---|---|---|---|---|---|---|
| status-line is-error | 6.03 | 5.60 | 5.10 | 4.65 | 4.65 | 4.65 |
| status-line is-success | 10.50 | 9.75 | 8.89 | 8.10 | 8.10 | 8.10 |
| status-line is-progress | 12.69 | 11.79 | 10.74 | 9.80 | 9.80 | 9.80 |
| status-line is-loading | 6.30 | 5.85 | 5.33 | 4.86 | 4.86 | 4.86 |
| status-line is-empty | 6.30 | 5.85 | 5.33 | 4.86 | 4.86 | 4.86 |
| status-line (default) | 6.30 | 5.85 | 5.33 | 4.86 | 4.86 | 4.86 |
| error | 6.03 | 5.60 | 5.10 | 4.65 | 4.65 | 4.65 |
| ok | 10.50 | 9.75 | 8.89 | 8.10 | 8.10 | 8.10 |
| acq-status is-error | 7.35 | 6.83 | 6.22 | 5.67 | 5.67 | 5.67 |
| acq-status is-caution | 9.10 | 8.46 | 7.70 | 7.02 | 7.02 | 7.02 |
| acq-status is-ok | 10.50 | 9.75 | 8.89 | 8.10 | 8.10 | 8.10 |
| acq-status is-muted | 8.31 | 7.72 | 7.03 | 6.41 | 6.41 | 6.41 |
| acq-status (active) | 12.69 | 11.79 | 10.74 | 9.80 | 9.80 | 9.80 |
| acq-stat | 8.31 | 7.72 | 7.03 | 6.41 | 6.41 | 6.41 |
| acq-profile | 6.30 | 5.85 | 5.33 | 4.86 | 4.86 | 4.86 |
| acq-percent | 16.31 | 15.15 | 13.80 | 12.59 | 12.59 | 12.59 |
| acq-transport | 8.31 | 7.72 | 7.03 | 6.41 | 6.41 | 6.41 |
| get-album (idle) | 12.69 (border 14.25) | 12.69 (border 13.24) | 12.69 (border 12.06) | 12.69 (border 11.00) | 11.00 | 11.00 |
| get-album is-pending | 7.03 (border 2.15 → 12.69) | 7.03 (border 2.00 → 11.79) | 7.03 (border 1.82 → 10.74) | 7.03 (border 1.66 → 9.80) | 1.66 | 7.03 |
| get-album requested | 12.69 (border 14.25) | 12.69 (border 13.24) | 12.69 (border 12.06) | 12.69 (border 11.00) | 11.00 | 11.00 |
| get-album is-failed | 5.10 (border 6.03) | 5.10 (border 5.60) | 5.10 (border 5.10) | 5.10 (border 4.65) | 4.65 | 4.65 |
| album-modal-status | 8.31 | 7.72 | 7.03 | 6.41 | 6.41 | 6.41 |
| track-number | 16.31 | 15.15 | 13.80 | 12.59 | 12.59 | 12.59 |
| row-source | 6.30 | 5.85 | 5.33 | 4.86 | 4.86 | 4.86 |
| dashboard-picks-status | 8.31 | 7.72 | 7.03 | 6.41 | 6.41 | 6.41 |
| genre-row-count | 8.31 | 7.72 | 7.03 | 6.41 | 6.41 | 6.41 |

### 30.5 Impeccable and design guidance

- `npx --yes impeccable@latest detect --json static/app.css` (run in this session): **5 findings before, 5 after**, the same five: the two 3px stripes (`.card-art::after`, `.ranked-row::before`, rows 9), two undocumented shadow colours (row 6, accepted), and the 999px pill (section 9.2). The change adds no finding. The PostToolUse design hook also reported no deterministic issue on the edited `static/app.css`.
- `/impeccable critique`, `/impeccable audit`: **not run** as the Impeccable skill in this session. The judgement is made against section 4.2 (yellow means do this or selected; the pending control keeps the working accent, and the arc is the state) and against the before and after screenshots.
- `web-design-guidelines` compliance pass: **not run** as a separate skill pass. The change is one declaration; the contract test covers it.
- Guidance applied: section 4.1's contrast rules, and the control-boundary rule (a boundary needs 3:1, and a boundary that identifies a control is not an ornament).
- Rejected: `--edge-strong` (fails 2.99:1 on the hover ground; see 30.3); `--text-subtle` as a border (a text token, not a boundary); changing the pending label colour (7.03:1, passes); adding a dedicated pending token (no new token needed).

### 30.6 Checks actually run

- `node --check static/app.js`: passed.
- `node --check static/login.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `python3 -m unittest tests.test_status_contrast_ui_contract -v`: 2 tests, OK.
- `python3 -m unittest discover -s tests -v`: **Ran 905 tests, OK** on this branch. The same command on `origin/main` (`bb25be0`, in a temporary worktree) ran 903 tests, OK. The difference is the two new tests.
- `pip install --break-system-packages -r requirements.txt` was run before the suite.

### 30.7 Browser (sandbox, RECONSTRUCTED states, not the owner's helper)

Setup: two local uvicorn servers (`app.main:app`), each with its own data directory under the session scratch folder, `SLSKD_URL=http://127.0.0.1:9` (slskd disabled), sandbox music path, one sandbox account per server. "Before" is a worktree of `origin/main` (`bb25be0`, port 8101). "After" is the working tree of this branch (port 8102). Chromium through Playwright, `prefers-reduced-motion: reduce`.

- Computed-colour measurement (`measure.mjs`): 104 pairs per run, before and after (30.4). **After: 0 failing pairs** on the four grounds. The console had no error or warning, and no request left the local origin, in either run.
- Screenshots at 1440, 1200, 900, 620 and 390px, before and after, in `/mnt/project-files/phase-7-contrast/screenshots/` as `before-states-<width>-RECONSTRUCTED.png` and `after-states-<width>-RECONSTRUCTED.png`. The state panel is injected into the dashboard with the real stylesheet: four status lines, three acquisition status rows and four Get cards (idle, pending, requested, failed). It is labelled RECONSTRUCTED; the sandbox has no library, acquisitions or albums, so no real state is shown.
- Overflow: `scrollWidth − innerWidth` was 0 at every width, before and after.
- Keyboard walk: **skipped**. No focus, role, name or key rule changed; the `:focus-visible` rules are untouched.
- Screen-reader pass: **skipped**.
- Real acquisition rows and real album Get states: **skipped** (no fixture in the sandbox). The probes in 30.2 cover the same classes on the shipped stylesheet; they are not a substitute for a live library.
- The owner's `test-pr.sh` helper: **not run** (not installed in this sandbox). The manual checklist against the exact PR-head SHA is **skipped** and is the next action before merge.

### 30.8 Limitations

- The probes are reconstructed DOM on the real stylesheet. The ratios are computed from the rendered colours, but a live library may place a state on a ground not covered here (the four grounds above are the ones the sandbox pages and the stylesheet use).
- The `--accent-dim` card action border (30.3) is recorded and not fixed.
- Margins: `status-line is-error` and the legacy `.error` on `--surface-hover` pass at 4.65:1 and `acq-profile` at 4.86:1. They pass, but any token change to the hover ground would need re-measuring.
- Measured with the WCAG 2.1 relative-luminance formula on sRGB values, as section 4.1 does. No colour-vision simulation was run.

### 30.9 Next action

Hamdi's review of the PR, then the manual checklist against the exact PR-head SHA with the owner's helper (sandbox paths, slskd disabled). Not merged, published or deployed by the author.


## 31. Card action boundary (Phase 7 follow-up item 10)

Scope: the `.card-actions` border that section 30.3 recorded and did not change. Roadmap follow-up item 10 and `docs/DESIGN_SYSTEM.md` section 16.2 row 13. Branch `ui/phase-7-card-actions-ldo6fm` (the server suffix; the requested name was `ui/phase-7-card-actions`). Base: `origin/main` at `ddfd30a` (PR #409 merged).

### 31.1 The failure

`static/app.css` set `.card-actions button:first-child { border-color: var(--accent-dim); }`. On a deep-dive card the first action is "Dismiss artist". Its edge identifies a control, so it falls under the 3:1 non-text boundary rule. Ratios computed from the token values (WCAG 2.1 relative luminance, the section 4.1 formula):

| Border | on `--surface` (card ground) | on `--surface-raised` (button fill) | on `--surface-hover` |
|---|---|---|---|
| `--accent-dim` (before) | 2.00:1 | 1.82:1 | 1.66:1 |
| `--edge-strong` (after) | 3.60:1 | 3.28:1 | 2.99:1 |
| `--accent` (rejected) | 11.79:1 | 10.74:1 | 9.80:1 |

On the rendered build the first action's computed border was `rgb(85, 75, 38)` (`#554b26`) at all five widths, the same token value.

### 31.2 What changed

| Selector | Old | Now | Why |
|---|---|---|---|
| `.card-actions button:first-child` | `border-color: var(--accent-dim)` | rule removed | The base `button` rule already sets `1px solid var(--edge-strong)`, the control boundary in section 7 and the secondary shape in section 9.1. The first action now matches its sibling. |

Why not `--accent`: it clears 3:1 everywhere, but it would give each card a second yellow control, against section 4.2 (yellow marks the one action or a selection). A card action is a secondary control.

Hover is unchanged: `button:hover` still sets the accent border and `--surface-hover` fill. `.card:hover` changes only the card's own border, not the buttons' ground.

Files changed: `static/app.css` (one rule removed); `tests/test_status_contrast_ui_contract.py` (one new test, `test_card_action_boundary_does_not_use_the_dim_accent`); `docs/REDESIGN_ROADMAP.md` (item 9 corrected to merged, item 10 added); `docs/DESIGN_SYSTEM.md` section 16.2 row 13; this section.

### 31.3 Impeccable and design guidance

- `impeccable detect`: the PostToolUse design hook scanned `static/app.css` after the edit and reported no deterministic design-quality issues. No separate `npx impeccable@latest detect --json` run was made, so the hook is the only detector record.
- `/impeccable critique` and `/impeccable audit`: **not run** as the Impeccable skill in this session. The judgement is made against sections 4.2 and 7, and against the screenshots in 31.5.
- `web-design-guidelines` compliance pass: **not run** as a separate skill pass. The change removes one declaration, and the contract test covers it.
- Applied: the control-boundary rule (a boundary that identifies a control meets 3:1), the base control token (`--edge-strong`), and the one-yellow-action rule (section 4.2).
- Rejected: `--accent` (a second yellow control per card); keeping the rule with `--edge-strong` (a no-op, since the base rule already sets it); any new colour value.

### 31.4 Checks actually run

- `pip install --break-system-packages -r requirements.txt`: run first.
- `node --check static/app.js` and `node --check static/login.js`: passed.
- `python3 -m compileall -q app static`: passed.
- `python3 -m unittest discover -s tests -v`: **Ran 909 tests, OK** with the CSS change (before the new test, which is the same count as `origin/main` after #409). **Ran 910 tests, OK** with the new test. The second run is the one recorded for the PR head.
- The new test fails on the old stylesheet (`FAIL: test_card_action_boundary_does_not_use_the_dim_accent`, confirmed by stashing only `static/app.css`) and passes on the change.

### 31.5 Browser (sandbox, RECONSTRUCTED fixture cards)

Setup: two local uvicorn servers (`app.main:app`), each with its own data directory under the session scratch folder, `SLSKD_URL=http://127.0.0.1:9` (slskd disabled), sandbox music and download paths, Navidrome unconfigured. "Before" is a worktree of `origin/main` (`ddfd30a`, port 8101); "after" is this branch (port 8102). Chromium through Playwright, `reducedMotion: 'reduce'`, one owner account per server created through the first-run route. No library exists in the sandbox, so each width shows two injected cards: a `.card-art` Get control and the actions "Dismiss artist" and "Not this album", using the app's classes so the shipped stylesheet renders them. Labelled RECONSTRUCTED in file names and in the DOM (`data-reconstructed`).

Screenshots in `/mnt/project-files/phase-7-card-actions/screenshots/`: `before-RECONSTRUCTED-{1440,1200,900,620,390}.png` and `after-RECONSTRUCTED-{1440,1200,900,620,390}.png`. Raw results: `before-results.json` and `after-results.json` in the same folder.

- First action border, computed: before `rgb(85, 75, 38)` at every width; after `rgb(120, 113, 104)` (`#787168`, `--edge-strong`) at every width. The second action was `--edge-strong` in both builds.
- Card ground `rgb(28, 26, 24)` and action fill `rgb(37, 34, 32)` in both builds, so the ratios in 31.1 apply.
- Horizontal overflow (`scrollWidth - clientWidth`): 0 at every width, both builds.
- Keyboard: the first card action took keyboard focus (Shift+Tab then Tab, so `:focus-visible` applies) at every width, both builds. Focus rules are unchanged.
- Console: no error or warning from the card UI at any width. One `409 (Conflict)` console message appears at 1440 in both builds. It comes from the fixture's own account bootstrap request, not the card, and was not investigated further.
- Network: no request left the local origin in either build.
- Real albums, real Get state, and real acquisition: **skipped** (no library in the sandbox).
- Screen-reader pass: **skipped**.
- The documented `test-pr.sh` helper: **not run** (not installed in this sandbox; it downloads an open PR head).
- Manual checklist against the exact PR-head SHA: **skipped** here, and it is the next action before merge.

### 31.6 Limitations

- The fixture is reconstructed DOM on the real stylesheet. A live album card may sit on a ground not measured here.
- The artwork "Not for me" button (`.card .card-art .deep-dive-dismiss`) is not a `.card-actions` control and is not measured. Its rules are unchanged.
- `--edge-strong` passes at 3.28:1 on the button's own raised fill, a small margin. Any token change to `--surface-raised` or `--surface` needs re-measuring.
- The Impeccable skill passes were not run as skills (see 31.3).

### 31.7 Next action

Hamdi's review of the PR, then the manual checklist against the exact PR-head SHA with the owner's helper (sandbox paths, slskd disabled). Not merged, published or deployed by the author.
