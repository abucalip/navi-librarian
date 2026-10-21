## 2026-10-21 — P1a deeper CF pool measured (PR #502, docs only)

- Owner waived P0h and approved one cold plus one warm run for `CF_MAX_PAGES` 4 vs 6 (test-only harness, not committed, fresh data dirs, slskd off, aggregate only).
- 4 pages: cold 25.2 s, warm 5.1 s, 117 candidate albums / 85 artists, 0 uncached recording lookups. 6 pages: cold 183.6 s (2 ListenBrainz 429s, batch fallback, 100 lookups, 47 albums), warm 10.0 s (162 albums / 109 artists). Final list 10 in all runs; overlap 4 of 10.
- Decision: keep `CF_MAX_PAGES = 4`. Single samples, order effect not excluded. No code change. Merge awaits the owner naming the PR.

## 2026-10-21 — PRs #500 and #501 merged

- **PR #500** (`ui/deepdive-save-render-check`) merged by squash as `e911a26b87cf8d9c11bb2502d8f1c074190b7a4c`, from exact final head `97e0bbbffbf3efb7c47860d980e49b023323bd0c`. Docs-only rendered verification record: Playwright/Chromium observed four 44 px Save controls, unobstructed hit targets, `save`/`remove_for_me` behavior without acquire or list reload, retry state on HTTP 500, and no overflow at 375 px. Screen-reader/live-data checks not done. All four required workflows passed on exact head: Python syntax/acquisition safety `39622877712`, Docker packaging `39622877775`, runtime smoke `39622877823`, validation-only multi-architecture image `39622877814` (publishing paused).
- **PR #501** (`ui/saved-page`) merged by squash as `990c83d3c0fdee816d7b511a7c6bd347bc715532`, from exact final head `10d0defec37479606ebb9bca143a21eb9d5cfd7c`. Adds the Saved page to the header menu, reading existing `/api/discovery/for_me`; supports refresh/revisit, saved dates, owned-album indication, remove/undo, loading/empty/error states, and hides Get for owned albums. Also removes the footer copy per owner request. PR report says 5 focused UI-contract tests and all UI-contract modules passed, `node --check static/app.js` passed, and Playwright/Chromium checks covered menu/navigation, rows, save/remove without acquisition/reload, refresh/revisit, empty/failure states, and 375 px layout. Live Navidrome data and screen-reader checks not done. All four required workflows passed on exact head: Python syntax `39626079394`, Docker packaging/full unit suite/build `39626079244`, runtime smoke `39626079346`, validation-only multi-architecture image `39626079497` (publishing paused).
- Publishing, deployment, and production-runtime verification remain unperformed. Exact PR heads were CI-verified before merge; no separate local full-suite run was performed.

## 2026-10-21 — PR #499 merged: P0i stale-flag audit (documentation only)

- PR #499 (`docs/p0i-stale-flag-audit`) merged by squash from exact final head `b5404cfcb80f65d36d61f309bb8c90b54d40b091`; merge commit `90d127eb46b0528a12ea0255ba81f25e1617ac4a`.
- Updated active status wording to reflect the current genre circuit-breaker and batch/title-filter defaults after PRs #495–#498. Corrected the tag-lane early-stop test docstring. No application code or defaults changed; dated historical experiment records were retained.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `39621883615`; Docker packaging/full unit suite/build `39621883770` (`test-and-build`, unit tests and image build succeeded); container runtime smoke `39621883534`; validation-only multi-architecture image validation `39621883758` (non-publishing).
- No separate local full-suite run (owner rule); CI ran the full suite. Publishing, deployment, and production-runtime verification remain unperformed.
- Next action: continue the active recommendation-engine roadmap from its top item; do not infer recommendation-quality or stable performance improvements from single samples.

## 2026-10-21 — Handoff: next task P0i (stale-flag audit, read-only then docs PR) (docs only)

- Pushed straight to `main` at the owner's instruction. `CLAUDE_CLI.md` hands off P0i: audit docs and comments against the post-#495 to #498 code defaults (known suspect: `docs/PROJECT_STATUS.md` still says the batch/breaker PRs are off by default), fix contradictions in a docs PR, no code or default changes, no network. P0h stays parked until ListenBrainz recomputes CF. No tests run (docs only).

