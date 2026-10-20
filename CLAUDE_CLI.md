# Handoff for Claude CLI: recommendation engine

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to.

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state" and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #456 (merge `4680a187734dc05516ebdca639b8a003366aaeb2`, roadmap 3.3, feedback as a bounded signal, on by default, owner-approved 2026-10-20). Verify the `main` head before you rely on it; it may have moved.
- Merged and recorded: PR #454 (`a5bba87`), PR #452 (`76030c0`), PR #451 (`42b6d81`), PR #450 (`27bdcc2`), PR #449 (`c90e43b`), and earlier PRs listed in the roadmap.
- Live timing is done (single samples, see the roadmap section "Live stage-timing runs"). Batch resolution explains the all-flags speed-up. The breaker-only warm run's 100 recording lookups fit the 100-per-run uncached budget (hypothesis; the `cache_known` counter is not in run metrics).
- Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Next task

**Roadmap 3.4: refill on/off setting.** One PR, offline first.

- Current state: background refill runs by default on the hourly discovery-refresh cycle. No setting turns it off. The owner decision of 2026-10-19 (roadmap 3.4) already says: on by default, and "the setting defaults to on and can be turned off". The decision to make it switchable is therefore already made; only the setting is missing.
- Required behavior: a persisted boolean setting, default `true`, that gates the automatic refill. When off, no background refill work runs. Foreground builds and stored-list reads are unchanged.
- Confirm the file scope with the owner before editing `app/api/**` or `app/main.py`. The setting needs an API route and a settings entry, and those paths were not yet approved for this change.
- Acceptance (deterministic tests, from roadmap 3.4): with the setting off, no background work runs; with it on, the refill keeps the 100-request uncached budget and the one-lock rule shared with foreground builds. Add a test that the default is on, and one that a corrupt stored value falls back to on.
- No live run is needed. Do not change the refill schedule or its staleness threshold in this PR.
- Check the status notes for 3.4 and 3.3 in the roadmap before assuming they are done. 3.3 is merged as PR #456.

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

- `navidrome_server.py` is capped at 2650 lines by the CI compile job. It is at the cap now, so any added line must be offset by a removal or moved into a module.
- A new Python module must be added to the `COPY` list in the Dockerfile, or `container-smoke` fails.
- The docs-only change rule still applies: a docs PR needs the same four checks on its head.
- The full suite has one known macOS-only failure: `test_acquisition_import.py::test_success_persists_importing_before_import_and_then_imported` (`/var` → `/private/var`). It fails on clean `main` too. CI on Linux passes it.

## Open items and owner decisions

- Default-on flags. `CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, the genre circuit breaker and the tag-lane early stop are all off by default. Each changes output or call pattern, so each needs an owner decision.
- Feedback signal (3.3). Merged as PR #456; default on, owner-approved 2026-10-20.
- Refill toggle (3.4). Default-on is decided; the on/off setting is the next task above.
- Candidate freshness (P2). Unmeasured: whether collaborative filtering reflects all-time history. This needs an authorized two-sided capture; do not start it without approval.
- ListenBrainz client. The app's HTTP client intermittently receives a browser-verification page instead of JSON. A fix that sends an honest client identifier and token would need the owner's go-ahead first. Do not change the client's user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider (later). Map one user-facing value onto the existing `recommendation_diversity` setting (0–100). Backend first; no UI in backend PRs.
- Feedback positive seed. Roadmap 3.3 asks for `save` as a seed for supplementary tag-query selection. PR #456 implements it as a score boost only. The tag-query version is a follow-up, and it touches the 100-lookup budget path, so it needs its own PR and a check of the budget.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
