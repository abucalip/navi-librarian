# Handoff for Claude CLI: recommendation engine

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope" below).

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state" and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #458 (squash merge `7fb140e6d915ada98974d1b56002c03d4e5cfef0`, roadmap 3.4 automatic refill on/off setting, default on). It was merged after all four required workflows passed on head `d72d650`. Verify the `main` head before you rely on it; it may have moved.
- `main` also includes PR #456 (merge `4680a187734dc05516ebdca639b8a003366aaeb2`, roadmap 3.3, feedback as a bounded signal, on by default).
- Merged and recorded: PR #454 (`a5bba87`), PR #452 (`76030c0`), PR #451 (`42b6d81`), PR #450 (`27bdcc2`), PR #449 (`c90e43b`), and earlier PRs listed in the roadmap.
- The refill setting is `automatic_refill_enabled` in `service_settings.py`, exposed at `GET/PUT /api/settings/automatic-refill`. The hourly `_discovery_scheduler` in `navidrome_server.py` passes no lists to `refresh_stale_lists` when it is off.
- Live timing is done (single samples, see the roadmap section "Live stage-timing runs"). Batch resolution explains the all-flags speed-up. The breaker-only warm run's 100 recording lookups fit the 100-per-run uncached budget (hypothesis; the `cache_known` counter is not in run metrics).
- Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Next task

**Roadmap 3.4, remaining part: stale-while-revalidate read path for the stored snapshot.** One PR, offline first.

- Current state: the stored discovery list is persisted, and the hourly scheduler refreshes stale lists. The read path does not yet serve a stored snapshot while a rebuild runs. Nothing in the read path triggers a background rebuild when the snapshot is older than the 24-hour threshold.
- Required behavior (roadmap 3.4): serve the latest good stored snapshot on request. When it is older than the existing 24-hour stale threshold, start a background rebuild and never block the request on it. A rebuild that is already running is not started again. Foreground builds and the one-lock rule are unchanged.
- Owned and duplicate identities are re-filtered against the current library on every read (already merged in PR #446). Keep that filter on the new path.
- Acceptance (deterministic tests, from roadmap 3.4): a stale snapshot is served while a rebuild is triggered; a snapshot served after a library change excludes newly owned albums; a refill run makes no more than 100 uncached requests.
- Scope: this likely touches `app/api/**` and `navidrome_server.py`. Those paths need explicit owner approval for this task before you edit them. The approval for PR #458 does not carry over.
- Do not change the refill schedule or the 24-hour staleness threshold in this PR.
- Check the status notes for 3.4 in the roadmap before assuming it is done.

## Testing scope (owner instruction, 2026-10-20)

- **Do not run the full test suite** (`python -m unittest discover -s tests`) in this session. The owner runs the full suite independently. Run only the focused test modules for the files you change, plus `python -m py_compile` on each changed Python file.
- This overrides the full-suite step in `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md` for this session only. The four required CI workflows still run on the PR head; CI is not affected.
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

- `navidrome_server.py` is capped at 2650 lines by the CI compile job. It is at the cap now, so any added line must be offset by a removal or moved into a module. Run `scripts/check_server_size.py` after editing it.
- A new Python module must be added to the `COPY` list in the Dockerfile, or `container-smoke` fails.
- The docs-only change rule still applies: a docs PR needs the same four checks on its head.
- The full suite has one known macOS-only failure: `test_acquisition_import.py::test_success_persists_importing_before_import_and_then_imported` (`/var` → `/private/var`). It fails on clean `main` too. CI on Linux passes it. The owner's independent full-suite run covers it.

## Open items and owner decisions

- Default-on flags. `CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, the genre circuit breaker and the tag-lane early stop are all off by default. Each changes output or call pattern, so each needs an owner decision.
- Feedback signal (3.3). Merged as PR #456; default on, owner-approved 2026-10-20.
- Refill toggle (3.4). Merged as PR #458; default on. The stale-while-revalidate read path is the next task above.
- Candidate freshness (P2). Unmeasured: whether collaborative filtering reflects all-time history. This needs an authorized two-sided capture; do not start it without approval.
- ListenBrainz client. The app's HTTP client intermittently receives a browser-verification page instead of JSON. A fix that sends an honest client identifier and token would need the owner's go-ahead first. Do not change the client's user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider (later). Map one user-facing value onto the existing `recommendation_diversity` setting (0–100). Backend first; no UI in backend PRs.
- Feedback positive seed. Roadmap 3.3 asks for `save` as a seed for supplementary tag-query selection. PR #456 implements it as a score boost only. The tag-query version is a follow-up, and it touches the 100-lookup budget path, so it needs its own PR and a check of the budget.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
