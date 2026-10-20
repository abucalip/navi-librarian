# Handoff for Claude CLI: exploration setting audit (backend, offline first)

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope" below).

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state", roadmap 3.3 status and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #465 (`6e1054b`, save-seed diagnostics counters), PR #464 (`de52808`, Save bookmark UI), PR #463 (`a12fb2f`, side-effect-free `save`) and PR #461 (`ace28d3`, saved albums seed tag-query selection). Verify the `main` head before you rely on it; it may have moved. `navidrome_server.py` is 2,448 of 2,650 lines.
- Save is a bookmark (owner, 2026-10-20): it stores the album and metadata for the engine and a future "Saved" page, and never starts an slskd search.
- The save loop is complete and measured once: `run_metrics.counts` carries seven `save_seed.*` counters. One owner-approved live sample (4 saves) changed 1 initial query and 0 replenishment queries; at most 3 of 4 saves reached the planner. Single sample; candidate quality of the changed query is unmeasured. No further seed work is planned unless real saves over time suggest it.
- Live timing is done (roadmap "Live stage-timing runs"). Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Exploration setting audit: DONE (2026-10-20, docs-only PR; decision (a))

Result in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` "Exploration setting audit". Next task: a UI-only exploration control over the existing endpoint (acceptance criteria are in that section). Original brief kept below.

Roadmap open item: "Exploration slider (later, product): map one user-facing value onto the existing `recommendation_diversity` contract (0-100). Backend first; no UI in backend PRs." Before building anything, establish what is actually missing. Facts verified at hand-off (re-check them on current `main`):

- The setting already exists: `service_settings.py` (`recommendation_diversity`, validated integer 0-100, default 0 in `navidrome_server.py`), `GET/PUT /api/settings/recommendation-diversity` in `app/api/settings.py`, and `discovery_mmr.diversity_setting_to_penalty` (linear 0-75 to a 0.00-0.75 penalty, saturating above 75, a provisional guardrail). `navidrome_server.py` passes `diversity_setting_fn` into the recommendation path. There is no UI control.
- So the open question is whether a new backend mapping is needed at all, or only a UI control over the existing contract.

Steps:

1. Trace the setting end to end: stored value, `diversity_setting_fn`, where `mmr_rerank` runs, and whether `0` is a true no-op (identical output to MMR off). Report the exact call path with line numbers.
2. Measure offline with the existing harnesses (`recommendation_mmr_evaluate.py`, `recommendation_replay.py`, synthetic fixtures where the private capture would be needed): output at settings 0, 25, 50, 75, 100 for diversity, relevance retention and repeat rate. Identity-free aggregates only. Known: the single-pool gate failed from setting 80 upward, which is why the penalty saturates at 75; confirm the user-facing 75-100 range is therefore flat and say so.
3. Decide and write down one of: (a) the contract is sufficient and the next step is a UI-only task (draft its acceptance criteria in this file); (b) a small backend change is needed (for example a distinct "exploration" label or a non-flat 75-100 range); name it and its risk before editing.

- Not allowed without the owner's approval: any edit to `app/api/**`, `app/security/**`, `navidrome_server.py` or a domain module (earlier approvals do not carry over), a change to the default value, new lookups, or any weakening of ownership, duplicate-identity or release-eligibility filtering.
- Acceptance: a recorded trace and offline measurements in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`, with the decision above. If you change code, add a deterministic synthetic test and run `python -m py_compile` on each changed file and the focused modules only.
- Record the PR/merge SHA in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`. A docs-only finding still goes through a PR with the four checks unless the owner says otherwise.

### Deferred (not this task)

- A "Saved" page that lists `for_me` rows, and a way to undo a save after the list has reloaded.
- Storing the artist MBID in save metadata: the live sample suggests it would recover at most one of four saves.
- Rendered check of the artist deep-dive Save control (not covered by PR #464's harness).
- Whether to enable the default-off flags (see "Open items").

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
