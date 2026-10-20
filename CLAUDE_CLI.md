# Handoff for Claude CLI: longer-interval repeat-rate measurement

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Repeat rate measured at simulated intervals (PRs #477, #478 open as docs at time of writing): decision not to reopen 3.2. Supply is limited by `CF_MAX_PAGES` (2), not by the lookup budget. PR #479 made batch resolution resilient to a failed release-group chunk.
- Cold-start supply gain measured and closed (PR #474). Warm final list measured (PR #475): spread unchanged (10 distinct artists, top-2 20%), family cap never blocked a full list. Decision on both: do not reopen 1.2, 3.1 or 3.2.
- PR #476 (merge `61520d6a4cd8c64e5714a23f3fb7dacb4c5a7855`): steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. Live, one sample: warm CF unowned 17 (was 4 and 14), warm time 32 s then 3 s (was 202 to 230 s), MusicBrainz calls 78 / 10 / 0.
- Side effect to watch: overlap with the previous list is now 5 of 10 (was 3 to 4) because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper. Back-to-back runs say nothing about decay.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: re-measure CF_MAX_PAGES = 4 after the batch fix

Why: the owner approved reading 4 CF pages (2026-10-20: 400 of the ~1,000 pool, +2 ListenBrainz requests per run). The first trial was slow because one 502 from the release-group endpoint discarded the whole batch; PR #479 (merge `4cf66322866c5377fec612a297db05922d7a8e11`) fixed that. Not yet confirmed live. Evidence so far (docs: `CF_PAGES_PROPOSAL_2026-10-20.md`, `REPEAT_RATE_MEASUREMENT_2026-10-20.md`): at 2 pages 36 CF albums from 15 artists, top-2 artist share 47.5%, identical every run; at 4 pages (old code, after the cache filled) 78 albums from 42 artists, top-2 share 26.4%.

Steps:
1. Branch `feat/cf-max-pages-4` off current `main`. Change `CF_MAX_PAGES` from 2 to 4 in `discovery_candidate_gathering.py` (a local stash `stash@{0}` on the old branch holds an identical edit and the matching test rewrite of `test_second_page_is_requested_with_offset_and_budget_stops_at_two_pages` to four pages; recreate it rather than trusting the stash).
2. Focused tests only: `test_discovery_candidate_gathering` plus the batch modules; `py_compile` on changed files.
3. Ask the owner for a live run (fresh data dir, slskd off, aggregate only, deleted afterwards). Harness: `reports/repeat-rate/run_cf_budget.py` (cold plus two warm; prints CF recordings, albums, artists, top-2 share, paging, provider calls, final source mix) and `run_batch_diag.py` (adds per-request status of the batch calls, no identifiers). Allow about 5 minutes per cold run; run it in the background.
4. Record per run: CF recordings returned/resolved/failed, uncached MusicBrainz lookups and skips, CF albums and artists, top-2 share, final-list mix, overlap with the previous list, wall time, requests per run. Success means a cold run near the 2-page time (about 106 to 123 s) with the batch path intact, not 260+ s.
5. If a 502 or other batch failure recurs, report the chunk status log before changing code; the fallback should now cost only the failed chunk.
6. Decide keep or revert (a one-constant change) and say so in the PR; record the numbers in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.

Acceptance: PR with the constant change, updated test, measured numbers, and the four workflows green on the final head. Do not run the full suite.

Alternative if the owner prefers no extra requests: measure rotating the tag lane's sampled tags per run (no added lookups; the lane was the noisiest input, 38 vs 10 candidates).

### Deferred

- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- Reading deeper into the 1,000-recording CF pool (more ListenBrainz requests; owner approval).
- CF freshness capture (needs an authorized two-sided capture); default-on decisions for the remaining flags (`BATCH_TITLE_FILTER_ENABLED` and steady-state `CF_BATCH_RESOLUTION_ENABLED`, genre breaker, tag-lane early stop); Last.fm (parked); diversity setting UI (paused).
- A "Saved" page, undo after reload, MBID in save metadata, rendered check of the artist deep-dive Save control.

## Testing scope (standing owner rule, 2026-10-20)

- **Agents working on PRs must never run the full test suite** (`python -m unittest discover -s tests`). This is permanent, not per-session. The owner runs the full suite independently and CI runs it on the PR head. Run only the focused test modules for the files you change, plus `python -m py_compile` on each changed Python file. A few modules (for example `test_discovery_cold_start_batch`) import siblings and need `python -m unittest discover -s tests -p <file>`.
- This overrides any full-suite step in `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`; those now carry the same rule. The four required CI workflows still run on the PR head.
- In the PR description, say which focused modules you ran. Do not report a full-suite result you did not observe.

## Standing rules

- GitHub is the source of truth. Never merge local-only commits.
- Ownership checks, duplicate-identity suppression and release-eligibility filtering are never weakened to raise coverage.
- No added lookups per run. The uncached MusicBrainz budget stays at 100 per run.
- No added ListenBrainz requests per run (owner, 2026-10-20). Recent listens stay at 3 pages of 100 within 30 days.
- Per-run time is a constraint on new work.
- Diagnostics are aggregate-only. Keep identity-bearing data, raw listens, credentials and provider URLs out of GitHub.
- Publishing and deployment are paused.
- Merges happen only after the owner names the PR in words. A bare "merge" or "yes" does not name one.
- Every PR runs the four required workflows on its exact final head: `compile` (Python syntax and acquisition safety), `test-and-build` (Docker packaging, full unit suite, build), `container-smoke` (runtime smoke), and `validate-container` (validation-only multi-architecture image; no publishing).
- Record merge SHAs in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`.

## Repository traps

- `navidrome_server.py` is capped at 2650 lines by the CI compile job (currently 2,448). Prefer new modules over server growth. Run `scripts/check_server_size.py` after editing it.
- A new Python module must be added to the `COPY` list in the Dockerfile, or `container-smoke` fails.
- The docs-only change rule still applies: a docs PR needs the same four checks on its head.
- The full suite has one known macOS-only failure: `test_acquisition_import.py::test_success_persists_importing_before_import_and_then_imported` (`/var` → `/private/var`). It fails on clean `main` too. CI on Linux passes it. The owner's independent full-suite run covers it; do not run the suite to check it.

## Open items and owner decisions

- Default-on flags. `CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, the genre circuit breaker and the tag-lane early stop are all off by default. Each changes output or call pattern, so each needs an owner decision.
- Feedback signal (3.3). Merged as PR #456; default on, owner-approved 2026-10-20.
- Refill toggle and read path (3.4). Merged as PR #458 (default on) and PR #459 (stale-while-revalidate). Roadmap 3.4 is complete.
- Candidate freshness (P2). Unmeasured: whether collaborative filtering reflects all-time history. This needs an authorized two-sided capture; do not start it without approval.
- ListenBrainz client. The app's HTTP client intermittently receives a browser-verification page instead of JSON. A fix that sends an honest client identifier and token would need the owner's go-ahead first. Do not change the client's user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider. The 0-100 `recommendation_diversity` setting, its API and the MMR penalty mapping already exist; the audit above decides whether anything backend is missing. No UI in backend PRs.
- Feedback positive seed. Merged (PRs #461, #463, #464, #465). One live sample is recorded in the roadmap; any further live run needs the owner's go-ahead.
