# Handoff for Claude CLI: longer-interval repeat-rate measurement

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Cold-start supply gain measured and closed (PR #474). Warm final list measured (PR #475): spread unchanged (10 distinct artists, top-2 20%), family cap never blocked a full list. Decision on both: do not reopen 1.2, 3.1 or 3.2.
- PR #476 (merge `61520d6a4cd8c64e5714a23f3fb7dacb4c5a7855`): steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. Live, one sample: warm CF unowned 17 (was 4 and 14), warm time 32 s then 3 s (was 202 to 230 s), MusicBrainz calls 78 / 10 / 0.
- Side effect to watch: overlap with the previous list is now 5 of 10 (was 3 to 4) because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper. Back-to-back runs say nothing about decay.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: repeat rate at realistic intervals (measure first)

Why: the owner-visible question is whether consecutive lists feel stale. Back-to-back refreshes (cooldown barely decayed, history of at most two lists) gave 5 of 10 repeats. The real scheduler refreshes hourly and the read path rebuilds after 24 hours, so the relevant cases are hours to days apart with several lists in history. Nothing is measured there, and 3.2 (cooldown calibration) is deferred until it is.

Steps:
1. Offline: read `recommendation_cooldown.py` and `discovery_store.recent_recommendation_history`. Compute, with synthetic scores, how much a 25% cap moves a candidate relative to the score gaps seen in a real pool (take gap statistics from aggregate diagnostics only). State whether the cap can change the top 10 at all.
2. Ask the owner for a live run (fresh data dir, slskd off, aggregate only, outside the repo, delete afterwards). Same harness pattern as before (wrap `recommendation_run_metrics.snapshot_and_reset` and `discovery_candidate_supply.summarize_candidate_stages`; source mix comes from the `discovery_source` field of `debug_all_candidates`). Build cold, then simulate elapsed time by shifting `recommendation_history.generated_at` backwards in the disposable database by 1, 3, 7 and 14 days before each warm refresh. Record per run: overlap with the previous list, overlap with the union of all earlier lists, distinct artists, top-2 share, MusicBrainz/Last.fm/ListenBrainz call counts. Limit to state: simulated time does not change ListenBrainz CF or the listening profile, so this isolates the cooldown, not supply drift.
3. Decide and name the risk before editing: reopen 3.2 (cooldown calibration) or not. Any option adding lookups or ListenBrainz requests per run needs owner approval.

Acceptance: a recorded finding in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with measured numbers and the decision; if code changes, a deterministic synthetic test, `python -m py_compile` on changed files and focused modules only.

Alternative if the owner prefers a decision over a measurement: a one-page brief for the default-on flags (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, genre breaker, tag-lane early stop). Evidence for it: the tag lane is the noisiest input (38 vs 10 candidates across the cold pair). Note the cold and warm paths already batch by default via their own switches.

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
