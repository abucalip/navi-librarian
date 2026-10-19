# Redesign roadmap — "Chart Rundown"

Status: **governance edits merged (PR #349); Phase 0 merged (PR #352); Phase 1 merged (PR #353); Phase 2 in progress: slice A (rail) merged in PR #355 (merge `981c244`); slice B (icon-only rail 621–900px, bottom tab bar under 620px, goo filter removed) merged in PR #360 (merge `d789f45`)** · Last updated: 2026-10-18 · Baseline: GitHub `main` at `995094a` for Phase 2

This is the proposed authoritative roadmap for redesigning the Librarian web UI against `docs/DESIGN_SYSTEM.md`. It replaces the backlog in `docs/FRONTEND_DESIGN_GUIDE.md` section 8 once approved. It does not change code. Product truth is in `PRODUCT.md`; the direction contract is in `.impeccable/surfaces/app-templates-index-html.md`.

## 1. Principles

1. **One cohesive system, shipped in thin vertical slices.** Tokens first, then shell, then pages, one reviewable PR each.
2. **Behavior is frozen, appearance is not.** API paths, schemas, auth, acquisition and Dismiss semantics, and the Get state machine are preserved exactly. No endpoint or field is invented.
3. **Evidence over opinion.** Every PR records the rendered check at the exact head SHA. Token-only changes are proven pure with the computed-style comparison used in PR #194.
4. **Existing contract tests are protected.** The `tests/*_ui_contract.py` files assert current class names and structure. Each phase updates them narrowly with a stated reason; none is deleted or weakened to pass.
5. **Every flourish earns its place** (design system sections 11 and 13).

## 2. Where the repo stands (verified 2026-10-18)

- `main` is `af412e3`; the repo's own docs record PRs up to at least #215. The older project files (`ONBOARDING_ANALYSIS.md`, `REDESIGN_ROADMAP.md`, `PHASE_1_CHECKLIST.md`) describe `4c6764c` and a repo state before PRs #44–#215. Their facts about HEAD, "no UI changes yet", and missing design tokens are out of date. Treat this document and `docs/UI_BACKLOG_EXECUTION.md` as current.
- Already done and not to be redone: state craft, Get button consolidation, accessibility fixes C1–C7, skip link, tabs ARIA, token naming, 44px touch targets, per-section layouts for acquisition, deep dive, recommendations and classics, nav rail redesign (`UI_BACKLOG_EXECUTION.md` sections 4–5l).
- Front end: `static/app.css` 462 lines, `static/app.js` 2,270, `app/templates/index.html` 282, `static/login.css` 47. Vendored Notyf already exists under `static/vendor/`, which is the precedent for vendoring fonts and icons.
- Real constraints the redesign must respect: eight pages in one shell; `discovery_score` is returned for recommendations; `/api/acquisitions/stream` exists; job statuses are the server's vocabulary.

## 3. Governance changes needed first (Phase 0)

The owner asked for these edits on 2026-10-18; they are applied in the same PR as this roadmap (PR #349) and take effect when it merges. The table records what changed. Design-system decisions D1–D6 were recorded by the owner on 2026-10-18 (`docs/DESIGN_SYSTEM.md` section 15).

| File | Proposed change |
|---|---|
| `AGENTS.md` | Applied: allow `static/fonts/**`, `static/icons.svg`, `static/vendor/**` and `docs/DESIGN_SYSTEM.md`, `docs/REDESIGN_ROADMAP.md` in normal scope. Replace "preserve the established type, color, spacing" with "follow `docs/DESIGN_SYSTEM.md`". Keep every protected backend, API, security and deployment boundary unchanged. |
| `docs/FRONTEND_DESIGN_GUIDE.md` | Applied: point sections 2, 3 and 8 at the design system and this roadmap. Move yellow/red and the Barlow/Plex trio from "established" to "superseded by DESIGN_SYSTEM.md". Keep section 4 (interaction, accessibility) and section 6 (boundaries) as is. |
| `docs/UI_BACKLOG_EXECUTION.md` | Applied: add a pointer to this roadmap; keep the evidence history. |
| `docs/TEST_PLAN.md` | Applied: add a visual-baseline step (Phase 0) and the viewport matrix below. |

"No external asset dependencies" stays true: fonts and icons are vendored and served from `/static`, not loaded from a CDN. Because `app/main.py` treats `/static/` as public, vendored files need no backend change.

## 4. Phases

Sizing is relative (S ≈ one PR, one session; M ≈ two or three; L ≈ four or more), not calendar estimates.

### Phase 0 — Authority and baseline (S, docs and harness only)

Status: **done in PR #352 (2026-10-18), pending owner merge.** Baseline measured on `main` `dc3e5a3`; results, environment, known errors B1–B3 and limitations are in `docs/UI_BACKLOG_EXECUTION.md` section 9. Decisions D1–D6 recorded. Screenshots are stored outside the repository by the owner's choice. Not exercised: the documented helper (not available in the capture environment), Google Fonts (blocked there, so typography and font timings are not representative), and any real library.

- Owner approves `DESIGN_SYSTEM.md`, resolves D1–D6, applies the governance edits above.
- Capture a visual baseline of the current UI: every page plus the modal at 1440, 1200, 900, 620 and 390px, using the documented isolated helper with sandbox paths and slskd disabled. Record exact `main` SHA, browser, and what could not be populated (the helper has no real library, so populated states use reconstructed DOM and are labeled as such).
- Record a performance baseline: first-load transfer size, number of requests (including the Google Fonts requests), layout shift, time to interactive on throttled network.
- Capture a color-vision-deficiency simulation of the proposed red/yellow/green/amber states (resolves D2).
- Exit: approved docs, baseline artifacts stored where the owner chooses, decisions recorded.

### Phase 1 — Foundations: tokens, fonts, icons (M)

Status: **implemented on `ui/phase-1-foundations`, PR open, not merged.** PR: #353 (`ui/phase-1-foundations`). Evidence, token audit, browser results and limitations: `docs/UI_BACKLOG_EXECUTION.md` section 10. Not yet verified: fonts and contrast on populated states, and the manual checklist against the exact head SHA.

Goal: new look at the token level, no layout change.
- Vendor WOFF2 subsets for Big Shoulders Display, Schibsted Grotesk and JetBrains Mono under `static/fonts/` with OFL license files; remove the Google Fonts `@import`; preload the display face; `font-display: swap`.
- Add `static/icons.svg` (Lucide, ISC license file included) with the initial set.
- Remap tokens per design system section 14; audit the 22 single-purpose tokens from PR #194 (keep, merge or delete with reasons); introduce the scale, spacing, radius and motion tokens.
- Verify purity of the remap by comparing computed styles old vs new for the selectors already used in PR #194, expecting only the intended value differences. Re-measure every contrast pair on the rendered build.
- Update affected contract tests narrowly.
- Impeccable: `/impeccable document` produces `DESIGN.md` from the built tokens; run `impeccable detect` once on the changed files and record findings applied and rejected.
- Exit: all pages render with new tokens; no horizontal overflow at the five widths; no console or network errors; no external font request; contrast table passes AA; all automated checks pass on the exact head.

### Phase 2 — Shell (M)

Status: **in progress.** Slice A (rail: icons, two named groups, 232px, numeral count, footer offset) merged in PR #355 (merge `981c244`, head `8817691`); evidence in `docs/UI_BACKLOG_EXECUTION.md` section 11. Slice B (icon-only rail 621–900px, bottom tab bar under 620px, goo and spring removed, translateY indicator) merged in PR #360 (merge `d789f45`, head `7f2283c`); evidence in `docs/UI_BACKLOG_EXECUTION.md` section 12. Phase 2 open items: the owner decisions on top-bar search (D5) and a third System group. Open for the owner: the top-bar search (D5, library-wide, needs a contract, see section 9) and whether a third System group returns (Settings is in the header menu per PR #327).

- Left rail with icons and three groups, 232px; top bar with breadcrumb, page-scoped search and the settings/user menu; Acquisitions count as a numeral.
- Responsive rail: icon rail under 900px, bottom tab bar under 620px. Remove the goo filter and spring easing; replace the blob with a `translateY` bar. Resolve the Settings/Log out placement already flagged in `UI_BACKLOG_EXECUTION.md` 5b.
- Preserve landmark names, `aria-current`, skip link, roving focus, 44px targets.
- Page-scoped search filters already-loaded items client-side. If the owner wants cross-page search, that is a backend contract proposal (see section 6), not part of this phase.
- Exit: keyboard-only walk of the shell passes; focus visible everywhere; screenshots at five widths; shell contract tests updated.

### Phase 3 — Ranked list component and Discover pages (L)

- Build the ranked row (design system 9.4) as one reusable component, including skeleton, empty, error and loading variants.
- Status: item 1 (Discover music) implemented in PR #365 on `ui/phase-3-discover-music` (not merged, not deployed). Item 2 (New releases) merged in PR #369 (squash `68fa6fb`, 2026-10-18), not deployed: the shared ranked row with a release-date column in place of numerals, skeleton loading, and the sort basis in the status line; evidence in `docs/UI_BACKLOG_EXECUTION.md` section 14. Item 3 (Personal Discoveries) merged in PR #372 (squash `f108bce`, 2026-10-18), with a muted position in place of the red numeral because the server returns these items in engine order, not score order. Its artist-bio follow-up merged in PR #373 (squash `fc656b9`, 2026-10-18). Evidence in `docs/UI_BACKLOG_EXECUTION.md` section 15. Not deployed. Item 4 (Add to your collection) merged in PR #375 (squash `5c9e3e9`, head `2a70386`, 2026-10-18) as shared ranked rows with a muted position and no red numeral (the server's exploration order is not a score ranking); not deployed. Its live-library browser check is still for Hamdi to run locally; the sandbox check used reconstructed fixtures. Evidence in `docs/UI_BACKLOG_EXECUTION.md` section 16.
- Convert, one PR each: Discover music, then New releases (date column), Personal Discoveries, Add to your collection.
- Rank numerals follow the truthfulness rules in design system section 8. Add a visible sort-basis label.
- Long names, missing artwork and failed requests are exercised in each PR.
- Exit per page: acceptance criteria met on the rendered page, existing behavior unchanged (Get, modal, filters, refresh), page contract tests updated.

### Phase 4 — Dashboard and Artist Deep Dives (M)

- Dashboard: static artwork tile strip replaces the ring (if D1 approved), keeping the "Ten from the collection" picks, Get on each tile, and keyboard operation. Status: merged in PR #381 (head `8714d95`, branch `ui/phase-4-dashboard-tiles`), after the owner's live-library check. Not deployed. Details in `docs/UI_BACKLOG_EXECUTION.md` section 18.
- Artist Deep Dives: genre sections with artist-led rows, strips that scroll only when they overflow, dismiss kept with its confirm step and server-side safety.
- Exit: dismiss path tested only on the sandbox folder; behavior parity with `main`.
- Status: Artist Deep Dives merged in PR #378 (squash `fb596c7`, head `2ff746e`, 2026-10-18), not deployed. The genre sections, artist-led tiles and overflow-only strips were already on `main` (`da908b5`); this PR brings the arrows, the Not for me control and the genre count onto the design system (sprite chevrons and × icons, 44px hit areas, no text-shadow, body-face count, singular "1 album"). Finding: `main` has **no confirm step** for Not for me (it posts at once, as it did before; no `confirm()` exists in the history of `static/app.js`), so the roadmap's "kept with its confirm step" describes behavior that is not there. This PR keeps the existing behavior and does not add a confirm step; the owner decides. Evidence in `docs/UI_BACKLOG_EXECUTION.md` section 17. Dashboard (item 1 of this phase) is the remaining Phase 4 item; decision D1 (retire the ring for a static tile strip) is recorded in `docs/DESIGN_SYSTEM.md` section 15.

### Phase 5 — Acquisitions (M)

Status: **merged in PR #383 (merge `a65fabf`), not deployed.** Acquisition cards and the conic ring are replaced by status rows, a linear progress bar scaled with `transform`, and one client-side status table (glyph and label for every status). Get, retry, skip, dismiss and the `/api/acquisitions/stream` path are unchanged. Evidence, checks and limitations: `docs/UI_BACKLOG_EXECUTION.md` section 19.

- Replace acquisition cards and the conic ring with status rows and a linear progress bar (design system 9.5); one table maps server statuses to glyph and label.
- Keep Get, retry, skip and dismiss semantics and the `/api/acquisitions/stream` updates. Verify live updates and the reconnect path.
- Exit: every status in the vocabulary renders with glyph and label; progress bar uses `transform`; contract tests updated; manual check of pending, failed and confirmed Get.

### Phase 6 — Settings, Login, Modal (M)

- Settings: two-column forms, new tab styling, quality-tier reorder with keyboard and drag, secret fields still preserving existing values on blank.
- Login and first-run setup restyled to the new tokens (the first-run variant was a recorded skip in PR #66; test it this time).
- Album modal: new layout and motion, focus return, Escape, tracklist rhythm.
- Exit: login, setup and failed sign-in verified; credentials never in markup.

Status: item 1 (Settings) merged as PR #386 (`ef93112`), not deployed. Evidence: `docs/UI_BACKLOG_EXECUTION.md` section 20. Item 2 (Login and first-run setup) merged as PR #388 (`a005b1c`), not deployed. Tokens, 44px targets, glyph-plus-text errors, first-run variant tested on a fresh data directory. Evidence and limits: `docs/UI_BACKLOG_EXECUTION.md` section 21. Item 3 (album modal) merged as PR #391 (squash `759510e`), not deployed. Evidence: `docs/UI_BACKLOG_EXECUTION.md` section 22.

### Phase 7 — Motion, polish, hardening (S–M)

- Apply the motion table once, in one pass: indicator, hover bars, list reorder on sort, modal, skeleton. Verify reduced-motion end states.
- `/impeccable audit` and `/impeccable critique` on every page; `/impeccable polish` and `/impeccable harden` on what they find, applying only fixes that fit this system.
- Performance comparison against the Phase 0 baseline; accessibility checks including a real screen-reader pass (not done before).
- Regenerate `DESIGN.md` from the finished build; update `docs/DESIGN_SYSTEM.md` where decisions changed.
- Exit: redesign acceptance (section 7) met.

Status: item 1 (motion table, one pass) merged as PR #392 (squash `46aa68e`), not deployed. Evidence: `docs/UI_BACKLOG_EXECUTION.md` section 23. Item 2 (audit, polish and harden) merged as PR #394 (merge `7b26d10`), not deployed; evidence in `docs/UI_BACKLOG_EXECUTION.md` section 24. Item 3 (`DESIGN.md` regenerated from the built system, drift record, performance against the Phase 0 baseline) implemented on `ui/phase-7-document-ryetdc`, PR open, not merged or deployed; evidence in `docs/UI_BACKLOG_EXECUTION.md` section 25 and `docs/DESIGN_SYSTEM.md` section 16. Still open: the real screen-reader pass, the third-party logos in the album modal, and the owner decisions in `docs/DESIGN_SYSTEM.md` section 16.5.

## 5. Per-PR checklist

1. State the problem, the design-system sections applied, and acceptance criteria.
2. Branch `ui/<short-name>` from current `main`; front-end files only, plus the approved asset paths.
3. Update or add tests for changed behavior and contract assertions; show before/after for any contract test edited.
4. Run `node --check static/app.js`, `python -m compileall app static`, focused tests, and `python -m unittest discover -s tests -v`; report real results.
5. Render at 1440, 1200, 900, 620, 390px; check keyboard, console and network; attach screenshots; mark any skip as a skip.
6. Run the manual smoke checklist from `docs/TEST_PLAN.md` against the exact head SHA; state the SHA.
7. Open the PR; do not merge, publish or deploy. CI is not deployment evidence.

## 6. Backend and API contract proposals

None are required for Phases 0–7 as scoped. Candidates the owner may add later, each needing a separate contract and owner decision before any backend work:

| Candidate | Why it might be wanted | Notes |
|---|---|---|
| Cross-page or library-wide search | A global search box beyond the loaded page | Needs a search endpoint and result schema; out of scope here |
| Queue position or ETA in acquisition payloads | A truthful "next up" numeral in Acquisitions | Only if the server can compute it; otherwise do not show it |
| Playback or now-playing bar | The references show a player | Owner chose visual language only; would need Navidrome stream contract, auth and security review |

If any is approved, write the contract (request, response, failures, why current API is insufficient) and stop at the backend boundary.

## 7. Definition of done for the redesign

- Every page uses the design system tokens, components and icons; no leftover one-off colors, no Google Fonts request.
- WCAG 2.1 AA text contrast measured on the rendered build; 44px targets; visible focus; reduced motion honored; status never by color alone.
- No horizontal overflow at the five widths; realistic long names, missing artwork, empty and failed states verified.
- API, auth, acquisition and Dismiss behavior unchanged; all existing and updated tests pass on the exact head SHA; all four required workflows pass.
- Performance no worse than the Phase 0 baseline on transfer size and layout shift.
- `DESIGN.md` generated from the built system; this roadmap updated with PR links and completion evidence.
- Manual browser report complete, with Chromium-only and no-screen-reader limits stated if still true.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Existing `*_ui_contract.py` tests encode old class names | Update narrowly per PR with a written reason; keep behavioral assertions |
| Red doing two jobs (brand and error) | Red rule and CVD check in Phase 0; fall back to yellow brand mark (D2) |
| Rank numerals imply ranking that does not exist | Truthfulness rules; hidden or muted when order is not meaningful |
| Fonts add weight | Latin subsets, preload display face only, budget in the design system |
| Large visual churn across about 3,100 lines of front end | Token remap first; one page per PR; baseline screenshots for comparison |
| No real library in the test helper | Label reconstructed DOM clearly; owner runs the manual checklist against the exact SHA |
| Impeccable detector output treated as a mandate | Apply only fixes that fit this system; record rejections in the PR |

## 9. Open items awaiting the owner

Merge of PR #352. D1–D6 and screenshot storage are decided. Still open: a contract proposal for library-wide search (D5, section 6) before Phase 2 can include it; owner/backend decision on B1 (`GET /api/settings/listenbrainz` returns 502 with no username saved), which affects the "no console or network errors" exit criterion on fresh-data runs; copying baseline screenshots out of the session workspace if the owner wants them kept; optionally re-measuring Google Fonts transfer and font-swap layout shift once on a machine with normal network access.
