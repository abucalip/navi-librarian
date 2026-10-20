# Handoff for Claude CLI: seed diagnostics (backend, one small PR)

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope" below).

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state", roadmap 3.3 status and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #464 (`de52808`, Save bookmark UI), PR #463 (`a12fb2f`, side-effect-free `save`; it also retired the unused `auto_acquire_for_me` setting), PR #461 (`ace28d3`, saved albums seed supplementary tag-query selection) and PR #460 (`4201ed9`; `navidrome_server.py` is 2,448 of 2,650 lines). Verify the `main` head before you rely on it; it may have moved.
- Save is a bookmark (owner, 2026-10-20): it stores the album and metadata for the engine and a future "Saved" page, and never starts an slskd search. The UI Save control updates in place; the list endpoints hide saved albums, so a saved album leaves its list on the next load.
- Roadmap 3.3 and 3.4 are done, and the save loop is now complete end to end (UI save, stored row, tag-query seed). Nothing yet reports whether the seed changes any query.
- Live timing is done (single samples, roadmap section "Live stage-timing runs"). Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Next task: aggregate seed diagnostics (backend, one small PR, no behavior change)

Why: the seed (PR #461) was verified only on a synthetic fixture. Before asking the owner for a live run to measure its real yield, the run must report what the seed did. This follows the PR #451/#452 pattern: counters only, so the next live run answers the question.

- Required: add aggregate-only counters to the existing `run_metrics` for the seed path in `discovery_candidate_gathering.py` (around the `saved_artist_seed_weights` block). Candidates: saved artists in the seed window; seeded from cached genres (MBID known); seeded from metadata `genres` (MBID unknown); skipped because the save had no `genres` and the MBID is unknown; planned supplementary queries that differ from the unseeded plan (initial and replenishment). Choose the final names yourself, keep them integers, and add them to the existing metrics map and its summarizer. Inspect `recommendation_run_metrics.py` first.
- Not allowed: any identity-bearing value (artist, album, tag names, MBIDs) in the counters, a new lookup, a change to query selection, quotas, caps, scoring or the flag defaults, and any change to `navidrome_server.py` or `app/api/**` (stop and ask if either seems needed).
- Acceptance (deterministic, synthetic): with no feedback provider, with feedback rows that seed no one, and with one MBID-known and one MBID-unknown save, the counters have the expected values; the planned queries and lookup count are identical to the run without the counters (assert it); a feedback-provider failure leaves the counters at zero and the run unseeded. Existing `tests/test_discovery_candidate_gathering*.py` modules for the changed file still pass.
- Run `python -m py_compile` on each changed file and the focused modules only. If you add a Python module, add it to the Dockerfile `COPY` list.
- Approval: `discovery_candidate_gathering.py` is a domain module. The owner's approval for this task is needed before you edit it (earlier approvals do not carry over).
- Record the merge SHA in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (roadmap 3.3 status) and `PROJECT_LOG.md`.
- After the merge, the live measurement itself (run the engine with a few real saves, read the counters) needs the owner's explicit go-ahead. Do not start it, and do not describe it as done.

### Deferred (not this task)

- A "Saved" page that lists `for_me` rows, and a way to undo a save after the list has reloaded.
- Storing the artist MBID in save metadata (only worth it if the new counters show many skipped saves).
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
- Exploration slider (later). Map one user-facing value onto the existing `recommendation_diversity` setting (0–100). Backend first; no UI in backend PRs.
- Feedback positive seed. Merged as PR #461; its UI (PR #464) and side-effect-free save (PR #463) are merged. Its real tag yield is unmeasured: seed diagnostics first (the task above), then a live run only with the owner's go-ahead.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
