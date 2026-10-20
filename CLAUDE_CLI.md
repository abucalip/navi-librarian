# Handoff for Claude CLI: bookmark Save (backend, then UI)

Read this first. It is written so you can pick up the next recommendation task from GitHub alone. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope" below).

## Getting started

1. Clone `abucalip/navi-librarian`, then fetch `main`. Work on a branch from current `main`, never on `main` directly.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the trimmed roadmap; its "Current state" and "Per-stage run timers" sections are the latest), and the top of `PROJECT_LOG.md`.
3. Check the open PRs and the four required workflows on the exact head you will push.

## Current state

- `main` includes PR #461 (`ace28d3`, roadmap 3.3 complete: saved albums seed supplementary tag-query selection; no added lookups; seeded plans capped at the unseeded plans) and PR #460 (`4201ed9`, deep-dive candidate collection extracted; `navidrome_server.py` is 2,536 of 2,650 lines). Verify the `main` head before you rely on it; it may have moved.
- Roadmap 3.3 and 3.4 are both done. Feedback is a bounded signal (PR #456), refill toggle and stale-while-revalidate read path (PR #458, #459), save seed (PR #461).
- Live timing is done (single samples, roadmap section "Live stage-timing runs"). Two batch live runs failed on a non-JSON listening-history response (one retry succeeded). Cause not established; the ListenBrainz client must not be changed to get around it.

## Next tasks (two PRs, in this order)

Product decision (owner, 2026-10-20): **Save is a bookmark.** It stores the album and its metadata for the recommendation engine and for a future "Saved" page. It never starts an slskd search; acquisition is the Get button's job. A "Saved" page will be added later and is not part of either task below.

### Task 1: make `save` side-effect-free (backend, one small PR)

- Why first: today `discovery_set_feedback(action="save")` in `navidrome_server.py` writes the `for_me` row and then starts a daemon thread, `_discovery_auto_acquire_for_me`, which runs `discovery_acquire_album(..., auto_queue=True)` unless the `auto_acquire_for_me` setting is off (default on). That predates the redesign, when "For Me" meant "get this". A UI Save button wired to the endpoint would start slskd searches, which contradicts the decision above.
- Required: `save` writes the row and returns; no thread, no search. Remove the `auto_acquisition` and `note` fields from the save response (or return them as `None`; keep the response shape otherwise). `dismiss`, `dismiss_artist` and `remove_for_me` do not change. The seed (PR #461) reads only `created_at` and `metadata.genres`, so it is unaffected.
- Dead code: `_discovery_auto_acquire_for_me` and its lock/set become unused; delete them (this also frees server lines). Check the other writer of `metadata["auto_acquisition"]` near `navidrome_server.py:1572` before deleting anything it relies on, and leave existing rows' `auto_acquisition` metadata alone.
- The `auto_acquire_for_me` setting: it is plumbed through `service_settings.py`, `app/api/settings.py`, `navidrome_server.py` and two test modules, and no UI references it. Do **not** retire it in this PR; leave the key and validation as they are, note it as unused, and ask the owner whether to remove it in a follow-up.
- Approval: editing `navidrome_server.py` needs explicit owner approval for this task (earlier approvals do not carry over). Touching `app/api/**` is not needed; if it seems needed, stop and ask.
- Acceptance (deterministic tests): saving does not start a thread or call `discovery_acquire_album` (patch both and assert not called); the `for_me` row is written with the supplied metadata; the response shape is unchanged apart from the removed fields; dismissal and `remove_for_me` behave as before; existing `tests/test_settings_routes.py` and `tests/test_quality_priority.py` still pass. Run `scripts/check_server_size.py`.
- Record the merge SHA in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`.

### Task 2: UI Save action (front end, one PR, after Task 1 is merged)

- Gap: nothing in the UI creates a save. In `static/app.js` the cards offer the Get button (`createGetButton`), "Not for me" (`dismiss`) and "Dismiss artist" (`dismiss_artist`); `sendFeedback()` is the only caller of `POST /api/discovery/feedback` and no code path sends `save`.
- Required: a Save control on recommendation cards that calls `sendFeedback('save', artist, album, item, listName)`. Send the whole `item` as metadata, as dismiss does: the seed reads `metadata.genres` for artists whose MBID is unknown, so do not strip it. Label it as a bookmark, not an acquisition. Provide a saved (pressed) state, an undo (`remove_for_me`, whose semantics do not change) and an error state. `sendFeedback()` reloads the list, so check the saved card is neither lost nor duplicated.
- Do not change the backend, the API route or feedback semantics. If `app/api/**` or `app/main.py` seems necessary, stop and ask.
- Scope: front end only. Read root `AGENTS.md`, `docs/DESIGN_SYSTEM.md`, `docs/REDESIGN_ROADMAP.md` and `docs/FRONTEND_DESIGN_GUIDE.md` first; edit only the permitted UI files (`static/app.{css,js}`, `app/templates/*.html`, narrow UI tests, `docs/UI_BACKLOG_EXECUTION.md`). The manual browser checklist runs against the exact tested SHA after CI passes; record the result.
- Acceptance: Save is reachable by keyboard with an accessible name that includes the album; saving posts one feedback request with the item as metadata and starts no download (verify in the browser harness that no acquisition request follows); the card shows a saved state without a full-page flicker; undo posts `remove_for_me`; a failed request shows an error and leaves the card unchanged. Add narrow tests in the style of `tests/test_ui_keyboard_and_feedback_contract.py` and `tests/test_personal_discoveries_ui_contract.py`.

### Deferred (neither task)

- A "Saved" page that lists `for_me` rows.
- Storing the artist MBID in save metadata (only worth it if saves of unknown-MBID artists without `genres` turn out to matter).
- Measuring the seed's real tag yield on a live run (needs owner go-ahead).

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
- Feedback positive seed. Merged as PR #461. The remaining gap is the missing UI save action; Task 1 (side-effect-free save) comes first, then Task 2.

## Working style

- Measure offline first, using the existing replay and profile-comparison harnesses. Use synthetic fixtures where the private captures would be needed.
- Report results as separate states: implemented, automated-tested, merged, published, deployed, runtime-verified. A merge is not deployment evidence.
- Keep changes small and reviewable, one roadmap item per PR.
