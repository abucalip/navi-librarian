# Handoff for Claude CLI: effect of the cold-start supply gain on the final list

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` ("Current state", then the sections "Live cold/warm pair" and "Cold-start batch path, measured", and Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Cold-run budget **closed**: PR #471 (merge `93225291c03214f377689875df12454f6eb97375`, head `230cf97b44807fb07c60fd5a76de8f5dce483b97`, all four workflows passed). The cold-start batch path prefetches all uncached CF recordings (+1 ListenBrainz POST and +1 GET per cold run, owner-approved); batch hits do not spend the 100 MusicBrainz budget; batch misses still do. PR #470 closed as superseded.
- Live, one sample, `_cold_start=True`, count 10: 117 s; 200/200 CF recordings resolved; 15 distinct CF artists; top-2 share 47.5%; 0 budget-skipped (before: 100/200, 4 artists, 55%). Time did not fall; it is spent in other stages. Provider-call counts were not captured (`run_metrics` was null in the wrapper's capture).
- Earlier: Phase 4.3 closed, no change (PR #469): only `count`/`offset` on the CF endpoint; pool 1,000, app reads 200. Honest ListenBrainz identifier plus optional `LISTENBRAINZ_TOKEN` (in `config.env` in the harness project folder; never print or commit it).
- Diversity setting: **paused by the owner**. No Settings UI, no mapping tuning. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: does the wider cold-start supply change the final list? (measure first)

Why: the roadmap defers weight retuning (1.2), MMR evaluation (3.1) and cooldown calibration (3.2) "until candidate supply shows a gain". The gain is now measured at the CF stage only (4 to 15 artists among resolved recordings). Whether the final top 10 changed is unmeasured, and that decides whether those phases reopen.

Steps:
1. Offline: from code and `docs/`, list what turns CF albums into the final list on a first build (filters, allocation, per-artist limits, dedup) and where the extra 100 resolved recordings can be dropped. Name the stage most likely to cap the final artist spread.
2. Ask the owner for a live run (fresh data dir, slskd off, aggregate only, outside the repo, delete afterwards): cold-start `count=10`, capturing final-list distinct artists, top-2 share, candidate counts per stage (`candidate_supply.stages`), and provider-call counts from `run_metrics` (capture them this time; wrap `record_recommendation_diagnostics`, which returns them). Compare to the pre-#471 cold numbers in the roadmap; the pre-change final-list figures were not captured, so say so rather than inventing a baseline. If a baseline is needed, ask the owner before checking out the pre-#471 commit for a second run.
3. Decide and name the risk before editing: reopen 1.2/3.1/3.2 or not, or leave as is. Any option that adds lookups or ListenBrainz requests per run needs the owner's approval.

Not allowed without owner approval: edits to `app/api/**`, `app/security/**`, `navidrome_server.py` or domain modules (name the module in the request), changing defaults or flags, new lookups, more ListenBrainz requests per run, raising the 100-per-run MusicBrainz budget, or weakening ownership, duplicate-identity or release-eligibility filtering.

Acceptance: a recorded finding in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with measured numbers and the decision; if code changes, a deterministic synthetic test, `python -m py_compile` on changed files and focused modules only.

### Deferred

- Add `LISTENBRAINZ_TOKEN` to `compose.yaml` and `docs/DEPLOYMENT.md` (touches deployment config; ask first). Small and self-contained; a reasonable alternative if the owner prefers it first.
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
