# Handoff for Claude CLI: Phase 4.3 wider ListenBrainz CF pool

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (Phase 4 item 3, and "Candidate supply diagnosis" at the end) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Diversity setting: **paused by the owner (2026-10-20).** Do not build the Settings UI or tune the mapping.
- Save loop and feedback signal are complete (PRs #456, #461, #463-#465). Roadmap 3.4 refill is complete. `navidrome_server.py` is 2,448 of 2,650 lines.
- Candidate supply diagnosis: the offline trace is done. The "103 failures are budget skips" hypothesis is **refuted** (skips never reach `cf_failure_classes`). PR #467 merged and names the real exception classes on the next run. The live cold/warm pair is **deferred**: the app's ListenBrainz client times out on recent listens (curl to the same endpoint works). PR #468 (listens page cap 3 to 5) was **closed unmerged**: the owner cannot afford more ListenBrainz requests per run.

## Next task: Phase 4.3, wider ListenBrainz CF pool

Why: the live sample's CF recordings came from only 4 artists (top two 55.7%), giving 14 CF albums. Supply limits quality more than ranking does, and the CF pool is the narrow part. Roadmap Phase 4 item 3 says to check current official documentation before assuming any parameter exists.

Steps:
1. Offline, docs only: read the current official ListenBrainz documentation for the recording-recommendation endpoint the app calls (`_fetch_cf_recommendations` in `discovery_candidate_gathering.py`: count, offset, `CF_PAGE_SIZE`, `CF_MAX_PAGES`, `CF_ARTIST_RESOLUTION_CAP`). Record, with the doc URL and date, which parameters exist (artist type, offset, filters, other recommendation endpoints) and which do not. Do not assume any.
2. Offline, from code and tests: report how the 4-artist concentration arises (does the response itself cluster by artist, or does the 200-recording window?). Check `CF_ARTIST_RESOLUTION_CAP` behaviour with a deterministic synthetic test if the answer needs one.
3. Decide and name the risk before editing: widen paging, change the artist cap, or leave CF alone and widen another lane. Any option that adds ListenBrainz requests per run is **not allowed without the owner's approval** (see Standing rules).
4. If a live run is needed to measure it, ask first. The deferred cold/warm pair can ride along once the client reaches ListenBrainz. Keep the client's identity unchanged; a fix with an honest identifier and token needs the owner's go-ahead.

Not allowed without owner approval: edits to `app/api/**`, `app/security/**`, `navidrome_server.py` or domain modules, changing defaults or flags, new lookups, **more ListenBrainz requests per run (including the recent-listens page cap)**, raising the 100-per-run MusicBrainz budget, or weakening ownership, duplicate-identity or release-eligibility filtering.

Acceptance: a recorded finding in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with doc URLs and the decision; if code changes, a deterministic synthetic test, `python -m py_compile` on changed files and focused modules only.

### Deferred

- Live cold/warm candidate-supply pair (funnel for both runs; aggregate only; captures outside the repo, deleted afterwards). Blocked by the ListenBrainz client timeout.
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
