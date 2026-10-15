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
- **State craft** (item 1) — implemented in PR #121 on branch `ui/state-craft`. A shared
  `.status-line` treatment now covers every status element, with `aria-live` on all of
  them and a per-state leading glyph so state is never carried by colour alone. See
  section 5 for the before/after measurements.

**Remaining, in the guide's priority order:**

1. ~~**State craft**~~ — done in PR #121.
2. **Per-section layouts** — refine artist exploration, library, acquisition, and settings
   into distinct task-appropriate compositions sharing the established design language.
3. **Get/request button consolidation** — align modal, artwork-overlay, and card-action
   variants into one consistent interaction pattern without changing API or acquisition
   semantics.
4. **Type/token cleanup** — consolidate duplicated values into shared tokens and tighten
   the type scale without broad visual churn.
5. **Responsive controls** — improve navigation, filters, and acquisition cards at narrow
   viewport widths.
6. **Continue visual audit** — re-prioritize based on evidence after the above.

**Newly found, not yet in the guide's numbered list:** keyboard focus reaches only three
interactive controls on the dashboard (see section 5), which is an accessibility defect
rather than a styling one. It belongs with item 5 or as its own item; decide when that
work is scheduled.

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

- **Reduced motion is implemented correctly.** `static/app.css` has exactly one
  `prefers-reduced-motion: reduce` block, and under that preference the computed
  `transitionDuration` on interactive elements becomes `1e-05s`. `static/login.css` has
  no such block, which is acceptable because the login page is nearly static.
- **Contrast is not a problem.** The lowest-contrast status text measured 7.09:1, well
  above the 4.5:1 WCAG AA threshold for body text. The state-craft defect was hierarchy,
  not legibility.
- **Keyboard focus reach is a real defect.** On the dashboard, 25 Tab presses reached
  only three distinct elements: the first navigation button, the logout button, and the
  shuffle button. Focus does not reach the remaining navigation, the discovery cards, or
  the card action buttons. Not addressed by the state-craft change.
- **No horizontal overflow** at 1440, 390, or 360 px in the measured states.
- **No browser console or page errors** during an authenticated pass over all eight pages.
