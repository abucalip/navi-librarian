# Handoff for Claude CLI: recommendation engine and UI save action

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope" below).

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state" and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #461 (`ace28d3`, roadmap 3.3 complete: saved albums seed supplementary tag-query selection; no added lookups; seeded plans capped at the unseeded plans) and PR #460 (`4201ed9`, deep-dive candidate collection extracted; `navidrome_server.py` is 2,536 of 2,650 lines). Verify the `main` head before you rely on it; it may have moved.
- Roadmap 3.3 and 3.4 are both done. Feedback is a bounded signal (PR #456), refill toggle and stale-while-revalidate read path (PR #458, #459), save seed (PR #461).
- Live timing is done (single samples, roadmap section "Live stage-timing runs"). Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Next task

**A UI save action for personal recommendations.** One PR, UI files only.

- Gap: the backend accepts `POST /api/discovery/feedback` with `action: "save"` (writes a `for_me` row, starts the background auto-acquire), and PR #461 uses saves to seed tag queries. The shipped UI cannot create one. In `static/app.js` the personal and other list cards offer only the Get button (`createGetButton`), "Not for me" (`dismiss`) and "Dismiss artist" (`dismiss_artist`); `sendFeedback()` is the only caller of the endpoint and no code path sends `save`. The `for_me` list exists but only API callers fill it.
- Required: a Save control on recommendation cards that calls `sendFeedback('save', artist, album, item, listName)`. Send the whole `item` as metadata, as dismiss does: the seed reads `metadata.genres` for artists whose MBID is unknown, so do not strip it. Decide, and state in the PR, how Save relates to Get: a save also starts a background slskd search (`auto_acquire_for_me` setting), so the label and confirmation must not promise only "bookmark". Provide a pressed/saved state, a way to undo (`remove_for_me` exists and keeps its semantics), and an error state. Reload semantics: `sendFeedback()` reloads the list, so check the saved card is not lost or duplicated.
- Do not change the backend, the API route, or feedback semantics (`dismiss`, `dismiss_artist`, `remove_for_me`). If something in `app/api/**` or `app/main.py` seems necessary, stop and ask.
- Scope: front-end only. Read root `AGENTS.md`, `docs/DESIGN_SYSTEM.md`, `docs/REDESIGN_ROADMAP.md` and `docs/FRONTEND_DESIGN_GUIDE.md` first; edit only the permitted UI files (`static/app.{css,js}`, `app/templates/*.html`, narrow UI tests, `docs/UI_BACKLOG_EXECUTION.md`). UI changes need the manual browser checklist against the exact tested SHA after CI passes, and the result recorded.
- Acceptance: Save is reachable by keyboard with an accessible name that includes the album; saving posts one feedback request with the item as metadata; the card shows a saved state without a full-page flicker; undo posts `remove_for_me`; a failed request shows an error and leaves the card unchanged. Add narrow tests (see `tests/test_ui_keyboard_and_feedback_contract.py` and `tests/test_personal_discoveries_ui_contract.py` for the existing contract style).
- Deferred, not part of this task: storing the artist MBID in save metadata (only worth it if saves of unknown-MBID artists without `genres` turn out to matter); measuring the seed's real tag yield on a live run (needs owner go-ahead).

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
- Feedback positive seed. Merged as PR #461. The remaining gap is the missing UI save action, the next task above.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
