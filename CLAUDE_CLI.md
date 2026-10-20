# Handoff for Claude CLI: recommendation engine

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to.

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state" and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` head: `76030c0f70e59ebe05b2e10ca5fcfc6a4fc75bd9` (PR #452: per-stage gathering timers, offline, no behavior change). Verify before you rely on it; it may have moved.
- Merged and recorded: PR #451 (`42b6d81`), PR #450 (`27bdcc2`), PR #449 (`c90e43b`), and earlier PRs listed in the roadmap.
- No draft recommendation PR is open at the time of writing. Check `list_project_prs` or GitHub.

## Next task

**Repeat the timing runs with the stage keys, and report aggregate stage seconds.**

- Why next: the owner's priority is to reduce the time it takes to build a recommendations batch, without adding lookups per run. Earlier single samples showed the batch flags cut the metadata stage from about 180 s to under 1 s, and all-flags runs were much faster than single-flag runs. Nobody has yet explained that difference. PR #452 added per-stage keys (`metadata_resolution`, `genre_prefetch`, `supplementary_tag_lane`, `replenishment`, `genre_lookup`) so a repeated run can answer it.
- Acceptance criteria:
  - Cold and warm runs for the all-flags and single-flag configurations, each reporting the stage keys in aggregate.
  - No candidate identities, raw listens, raw tags, provider URLs or credentials in the output or in GitHub.
  - No change to any flag default, weight, window, eligibility, ownership, duplicate or budget rule.
  - Any code change needed to get the numbers is separate, tested offline, and reviewed on its own PR.
- **Gate:** a live run needs the owner's explicit go-ahead in words. Do not start one without it. The Mac measurement is paused, so the run may need a different route. Offline checks may proceed without approval.

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

- `navidrome_server.py` is capped at 2650 lines by the CI compile job. Move logic into a module rather than growing it.
- A new Python module must be added to the `COPY` list in the Dockerfile, or `container-smoke` fails.
- The docs-only change rule still applies: a docs PR needs the same four checks on its head.

## Open items and owner decisions

- Default-on flags. `CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, the genre circuit breaker and the tag-lane early stop are all off by default. Each changes output or call pattern, so each needs an owner decision.
- Refill toggle. Background refill runs by default, but no setting exists to turn it off. The owner needs to decide.
- Candidate freshness (P2). Unmeasured: whether collaborative filtering reflects all-time history. This needs an authorized two-sided capture; do not start it without approval.
- ListenBrainz client. The app's HTTP client intermittently receives a browser-verification page instead of JSON. A fix that sends an honest client identifier and token would need the owner's go-ahead first. Do not change the client's user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider (later). Map one user-facing value onto the existing `recommendation_diversity` setting (0–100). Backend first; no UI in backend PRs.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
