# Handoff for Claude CLI: read-only look at release-group 502s

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`, then the "`CF_MAX_PAGES = 4` re-measured" and "tag-lane rotation" findings.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Repeat rate at simulated intervals measured (PRs #477, #478): decision not to reopen 3.2. Cold-start supply gain (PR #474) and warm final list (PR #475) measured: do not reopen 1.2, 3.1 or 3.2.
- PR #476: steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. PR #479: a failed release-group chunk falls back only for its own recordings.
- `CF_MAX_PAGES = 4` re-measured (PR #482, merge `c02e4966c3835f893f27a09bef0b1172b8578d66`): **kept at 2**. Cold 4-page runs took 255 s and 316 s against 141 s at 2 pages, because release-group requests still returned 502 after the retry, so recordings fell back to per-recording lookups and spent the 100 budget. Warm 2 at 4 pages reached 77 CF albums from 42 artists (top-2 26.4%) once cached. Unexplained: 111 to 113 `recording_lookup` calls (budget is 100) and `lastfm.api` calls (13 to 40) in some runs.
- Tag-lane rotation (PR #483, merge `28fb84026201b0779cd604efc5c50aa11203cff5`): **measured and not adopted**; the code was removed after review, only the findings remain. Warm overlap 5/5/4 off vs 4/5/3 on (noise), tag supply unchanged, warm MusicBrainz calls 0 vs 12/6/5, warm time 2.8-4.3 s vs 8.6-20.9 s. Do not reopen without a new idea that adds no lookups.
- Side effect to watch: overlap with the previous list is 5 of 10 because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: read-only look at why release-group requests return 502 at larger sizes

Why: it is the open P0 question in the roadmap and the gate for revisiting `CF_MAX_PAGES = 4`. At 4 pages, release-group requests still returned 502 (HTML body) after #479's single retry, so recordings fell back to per-recording lookups and spent the 100 budget (cold 255 s and 316 s against 141 s at 2 pages). The cause is not established.

Steps (all read-only; no request-pattern change without owner approval):
1. Read `_prefetch_batch_recordings` and the release-group chunking and retry in `discovery_candidate_gathering.py`, and the batch client code it calls. Record chunk size, request count, spacing and which endpoint and method are used at 2 vs 4 pages.
2. Offline: from existing aggregate reports (PRs #479 and #482, `reports/`), tabulate request size against outcome. Check whether the 502 appears only above a size, only on the first release-group request, or is intermittent. Keep identity-bearing data, URLs and credentials out of anything written.
3. Also look at the two unexplained counts: 111 to 113 `recording_lookup` calls against the 100 budget, and 13 to 40 `lastfm.api` calls in some runs. Find where each is counted and whether the budget check is per call or per batch. Note that cold runs of the tag-rotation experiment also made 40 `lastfm.api` calls at 2 pages.
4. Write findings, hypotheses and the smallest candidate fixes with their request-pattern impact in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`. A diagnostic live run, smaller chunks, different spacing or more requests all need the owner's go-ahead first; ask before running anything live.

Acceptance: a docs-only PR (four workflows green on its head) that states what is known, what is not, and a recommended next step. No code change unless the owner approves one. Do not run the full suite.

### Deferred

- Read-only look at why release-group requests 502 at larger sizes, and the unexplained lookup and Last.fm call counts. Any request-pattern change needs owner approval.
- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- Reading deeper into the 1,000-recording CF pool (more ListenBrainz requests; owner approval); revisit 4 pages only after the 502s are understood.
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
- ListenBrainz requests (owner, 2026-10-20, revised 2026-10-21): the limit exists to protect per-run time. Added ListenBrainz requests that **save time** are allowed, for example batch lookups that replace many slower per-item requests (measured: +3 ListenBrainz GETs replace about 79 MusicBrainz requests and cut a cold 4-page run from about 212 s to about 40 s). Requests that add time, or whose only effect is more data to resolve, still need owner approval. Recent listens stay at 3 pages of 100 within 30 days. Always measure the time effect and report the request counts before and after.
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
