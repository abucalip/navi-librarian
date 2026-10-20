# Handoff for Claude CLI: candidate supply diagnosis (offline first, then one live run)

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (see "Live sample: diversity setting had no effect" at the end) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Diversity setting: **paused by the owner (2026-10-20).** PR #466 recorded the audit and a live sample (identical output at settings 0-100 on a 24-album pool). Do not build the Settings UI or tune the mapping.
- Save loop and feedback signal are complete (PRs #456, #461, #463-#465). Roadmap 3.4 refill is complete. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: candidate supply diagnosis

Why: the live sample's pool was 24 albums (14 unowned for 10 slots), so ranking changes cannot show up. Supply limits quality more than ranking does. Funnel from that capture (aggregate): 200 CF recordings from only 4 artists (top two 55.7%), 97 resolved, **103 failed as class "other"**, 14 CF albums, 3 supplementary queries attempted (1 failed), 10 of 24 candidates already owned, 7 rejected by the recent-genre cap.

Hypothesis to test first (offline, from code): the 103 failures are about the 100 uncached resolutions allowed per run (`CF_MAX_UNCACHED_RESOLUTIONS` in `discovery_candidate_gathering.py`), recorded as "other". If so, a run only resolves the next ~100 recordings, and a larger or warmer pool needs repeat runs or the batch path (`CF_BATCH_RESOLUTION_ENABLED`, default off).

Steps:
1. Trace where `cf_failure_classes` is built and which paths land in "other". Report line numbers.
2. If budget skips are indistinguishable from real failures, add a separate failure class (diagnostics only: no lookup, selection, quota or budget change), with a deterministic synthetic test. This is a small PR; it needs owner approval if it touches `navidrome_server.py` or a domain module (earlier approvals do not carry over).
3. Then one owner-approved live pair on a fresh data dir (cold, then warm, count 10, slskd off): record the funnel for both (CF recordings, failure classes, CF albums, supplementary yield, unowned unique, selected). Aggregate only; keep captures outside the repo and delete them afterwards.
4. Record whether warm runs grow the pool and decide the next step (budget per run, batch default, or CF concentration on few artists). Name its risk before editing.

Not allowed without owner approval: edits to `app/api/**`, `app/security/**`, `navidrome_server.py` or domain modules, changing defaults or flags, new lookups, raising the 100-per-run MusicBrainz budget, or weakening ownership, duplicate-identity or release-eligibility filtering.

Acceptance: a recorded trace and funnel numbers in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with the decision; if code changes, a deterministic synthetic test, `python -m py_compile` on changed files and focused modules only.

### Deferred

- Diversity setting UI and mapping (paused).
- A "Saved" page, undo after reload, MBID in save metadata, rendered check of the artist deep-dive Save control.
- Default-on decisions for the four flags; CF freshness capture; ListenBrainz client non-JSON responses (do not change the client's identity to get around it); Last.fm (parked).

## Testing scope (standing owner rule, 2026-10-20)

- **Agents working on PRs must never run the full test suite** (`python -m unittest discover -s tests`). This is permanent, not per-session. The owner runs the full suite independently and CI runs it on the PR head. Run only the focused test modules for the files you change, plus `python -m py_compile` on each changed Python file. A few modules (for example `test_discovery_cold_start_batch`) import siblings and need `python -m unittest discover -s tests -p <file>`.
- This overrides any full-suite step in `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`; those now carry the same rule. The four required CI workflows still run on the PR head.
- In the PR description, say which focused modules you ran. Do not report a full-suite result you did not observe.

## Standing rules

- GitHub is the source of truth. Never merge local-only commits.
- Ownership checks, duplicate-identity suppression and release-eligibility filtering are never weakened to raise coverage.
- No added lookups per run. The uncached MusicBrainz budget stays at 100 per run.
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
