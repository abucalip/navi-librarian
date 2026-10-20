# Handoff for Claude CLI: steady-state (warm) final-list measurement

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` ("Current state", then the sections "Live cold/warm pair" and "Cold-start batch path, measured", and Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Cold-start supply gain **measured and closed**: PR #474 (merge `aedc34e44034a04bb20c177458f9c8b73b12900f`, head `b46f13df69be63d1eb1d25047bac04b4eb2f388e`, all four workflows passed). Cold, count 10, one sample each: final list 10 distinct artists and 20% top-2 share before and after #471 (the allocator takes one album per artist); CF share of the final 10 rose 3 to 7; unowned CF candidates 4 to 17. Decision: do not reopen 1.2, 3.1 or 3.2 on cold-start evidence. Details in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` ("Finding").
- Cold-run budget closed (PR #471); `LISTENBRAINZ_TOKEN` in Compose/docs (PR #472, not deployed); Phase 4.3 closed (PR #469). Token is in `config.env` in the harness project folder; never print or commit it.
- Diversity setting: **paused by the owner**. No Settings UI, no mapping tuning. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: steady-state (warm) final-list behaviour (measure first)

Why: on a first build cooldown has no history and MMR is off at the default, so Phases 3.1 and 3.2 were inert in the cold measurement. They can only matter on a warm refresh, which is also where the soft recent-genre family cap (17 to 24 rejections per cold run) could limit spread. Nothing is measured there yet; the roadmap defers 1.2/3.1/3.2 until a warm measurement shows a need.

Steps:
1. Offline: trace a warm refresh (`refresh_personal` with a stored previous list, cooldown history present, stale-while-revalidate path). List what differs from cold: cooldown penalties (max 25%), feedback signal, cached CF/genre metadata, batch path off. Name the stage most likely to cap spread or cause repeats between consecutive lists.
2. Ask the owner for a live run (fresh data dir, slskd off, aggregate only, outside the repo, delete afterwards): cold build then one or two warm refreshes, count 10, using the capture wrapper pattern from the #474 finding (wrap `recommendation_run_metrics.snapshot_and_reset` and `discovery_candidate_supply.summarize_candidate_stages`; the return value of `record_recommendation_diagnostics` does not carry them). Record per run: distinct artists, top-2 share, overlap with the previous list, source mix, family-cap rejections, provider-call counts.
3. Decide and name the risk before editing: reopen 1.2/3.1/3.2 or not. Any option adding lookups or ListenBrainz requests per run needs owner approval.

Acceptance: a recorded finding in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with measured numbers and the decision; if code changes, a deterministic synthetic test, `python -m py_compile` on changed files and focused modules only.

Alternative if the owner prefers a decision over a measurement: a one-page brief for the default-on flags (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, genre breaker, tag-lane early stop). Evidence for it: the cold pair shows the tag lane is the noisiest input (38 vs 10 candidates).

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
