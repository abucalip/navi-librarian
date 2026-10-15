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

**Completed:** item — login-page alignment (PR #66). The guide marks this closed and says
not to reopen it without new evidence. Its verification recorded keyboard focus modality
and the first-run setup variant as **skips, not passes**.

**Remaining, in the guide's priority order:**

1. **State craft** — consistent, purposeful loading / empty / error / success / recovery
   presentation across the app, preserving correct semantics and actionable feedback.
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

## 5. Observed evidence for item 1 (State craft)

Recorded here so the item-1 session starts from evidence rather than a fresh audit. These
are observations at the baseline SHA, not yet a chosen problem statement.

- **Status elements are styled inconsistently.** Eleven status paragraphs exist. Only
  three carry a class: `dashboard-picks-status` (`index.html:37`),
  `album-modal-status` (`index.html:208`), and the settings ones use ad-hoc rules.
  `newReleasesStatus` (`index.html:92`), `personalStatus` (`index.html:107`),
  `classicsStatus` (`index.html:118`), `artistDeepDiveStatus` (`index.html:129`), and
  `acquisitionsStatus` (`index.html:190`) carry **no class at all**, so they inherit plain
  `<p>` styling and are visually indistinguishable from body copy.
- **`aria-live` is applied inconsistently.** `newReleasesStatus`, `navidromeStatus`,
  `slskdStatus`, `lastfmStatus`, `listenbrainzStatus`, and `albumModalStatus` have
  `aria-live="polite"`. `personalStatus`, `classicsStatus`, `artistDeepDiveStatus`, and
  `acquisitionsStatus` do **not**, even though the JS writes dynamic progress text into
  them (for example `static/app.js:295` and `static/app.js:319`).
- **Status text is plain unstructured prose** — "3 item(s)", "Loading…",
  "Building the first list in the background…", error messages. There is no shared
  vocabulary or visual distinction between loading, empty, error, and success, so a user
  cannot tell a transient state from a failure without reading the sentence.

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

A headless-browser path for automated rendered verification is authorized and under
exploration. Until it exists and is proven, treat rendered verification as manual.

Any headless-browser tool introduced must not become an application dependency: no entry
in `requirements*.txt`, no build system, and nothing imported by `app/`. It belongs only
in the test/verification layer. If it cannot be added under those constraints, it must be
installed outside the repository checkout and the PR must record how it was invoked.
