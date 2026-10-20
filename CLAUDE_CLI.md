# Handoff for Claude CLI: recommendation engine

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope" below).

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state" and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #460 (`4201ed9`, deep-dive candidate collection extracted to `discovery_deep_dive_candidates.py`; `navidrome_server.py` is now 2,535 of 2,650 lines) and PR #459 (squash merge `b09c9544cd96828a732fea04818729fc381cee0e`, roadmap 3.4 stale-while-revalidate read path). It was merged after all four required workflows passed on head `44148af`. Roadmap 3.4 is complete. Verify the `main` head before you rely on it; it may have moved.
- Reading the personal list serves the stored snapshot and starts at most one background rebuild when it is 24 hours or older (`discovery_refresh.revalidate_on_read`, `STALE_MAX_AGE_SECONDS`). It honors `automatic_refill_enabled`, skips while a rebuild is in flight or within the one-hour cooldown, and does nothing without a snapshot. Refresh outcomes use origin `read`; the store now accepts status `rejected`.
- `main` also includes PR #458 (`7fb140e`, refill on/off setting, default on) and PR #456 (`4680a18`, roadmap 3.3, feedback as a bounded signal, on by default).
- Merged and recorded: PR #454 (`a5bba87`), PR #452 (`76030c0`), PR #451 (`42b6d81`), PR #450 (`27bdcc2`), PR #449 (`c90e43b`), and earlier PRs listed in the roadmap.
- Live timing is done (single samples, roadmap section "Live stage-timing runs"). Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Next task

**Roadmap 3.3, remaining part: `save` as a positive seed for supplementary tag-query selection.** One PR, offline first.

- Current state: PR #456 applies a saved album's artist as a score boost only (0.10 max; 30-day half-life, 90-day expiry from `created_at`). The supplementary tag lane (`discovery_tag_queries.py`, `discovery_candidate_gathering.py`) does not use saves when it picks tag queries.
- Required behavior (roadmap 3.3): use saved albums/artists as a positive similarity seed when selecting supplementary tag queries, with the same expiry rules as the boost. Never create a permanent effect. `dismiss`, `dismiss_artist` and `remove_for_me` semantics do not change.
- Budget: this touches the 100-uncached-lookup path. Measure first: show on a synthetic fixture how many queries and uncached lookups a run plans with and without the seed, and keep it within the existing budget. A seed that replaces a planned query is fine; one that adds lookups is not. Weights, windows, eligibility, ownership and duplicate identity are unchanged.
- Acceptance (deterministic tests): with a fresh save, the planned tag queries include a tag from the saved artist's genres; with an expired save, the plan is identical to no save; the uncached lookup count is no higher than without the seed; ownership and duplicate filtering still apply to candidates the seed surfaces; flag off or no feedback leaves output unchanged.
- Scope: most likely `discovery_tag_queries.py`, `recommendation_feedback.py` and the call site in `navidrome_server.py`. `navidrome_server.py` has about 115 lines of headroom (2,535 of 2,650) after PR #460; still keep additions small and run `scripts/check_server_size.py`. Editing `navidrome_server.py` or `app/api/**` needs explicit owner approval for this task; the approvals for PRs #459 and #460 do not carry over. Prefer not to touch them.
- Check the 3.3 status note in the roadmap before assuming anything is done.

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

- `navidrome_server.py` is capped at 2650 lines by the CI compile job (currently 2,535). Prefer new modules over server growth. Run `scripts/check_server_size.py` after editing it.
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
- Feedback positive seed. This is the next task above.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
