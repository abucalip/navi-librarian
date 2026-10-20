# Handoff for Claude CLI: cold-run CF resolution budget

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (open item "Cold-run resolution budget", then "Live cold/warm pair" and the batch-resolution sections near lines 200 and 488) and the top of `PROJECT_LOG.md`.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Phase 4.3 is **closed, no change** (PR #469, merge `eca44e52dedfb5aec188faf287a8c0696d7566c7`, head `439c54be6c9c687aee9f7857cf2015850753a237`, all four workflows passed). Only `count` and `offset` exist on the CF endpoint; the pool is 1,000 recordings and the app reads 200.
- PR #469 also added `cf_paging.total_mbid_count` and an honest ListenBrainz identifier plus optional `LISTENBRAINZ_TOKEN`. The recent-listens timeout did not recur in the live pair; which change fixed it was not isolated. The token sits in `config.env` in the harness project folder; never print it or commit it.
- Live cold/warm pair (2026-10-20): cold 323 s, budget-bound (100 uncached MusicBrainz calls, 86 recordings skipped unread, 6 artists, top-2 54%); warm 63 s, 15 artists, top-2 31%; 0 CF failures in both. One sample.
- Diversity setting: **paused by the owner**. Do not build the Settings UI or tune the mapping. Save loop, feedback signal and roadmap 3.4 are complete. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: cold-run resolution budget (measure first)

Why: on a cold run the 100-call MusicBrainz budget, not paging, limits the resolved CF set, and the artist cap cannot act on uncached recordings. Candidate fixes are batch resolution (`CF_BATCH_RESOLUTION_ENABLED`, off, changes the call pattern, needs an owner decision) or ordering unresolved recordings so one artist cannot take the budget (the CF response carries no artist).

Steps:
1. Offline, from code: confirm how `cold_start` reaches `gather_recommendation_candidates` (`refresh_personal` passes `_cold_start`; `recommend_new_music` defaults it to `False`). The live pair called `recommend_new_music(10)` directly, so the **cold-start batch path (`COLD_START_BATCH_ENABLED`, on) was not exercised**. State what a real first build does.
2. Measure that path: ask the owner for a live run with `_cold_start=True` (fresh data dir, slskd off, aggregate only, capture outside the repo and delete it). Compare to the recorded cold run: seconds, uncached MusicBrainz calls, resolved recordings, distinct CF artists, top-2 share, `resolution_budget_skipped`. Keep the client identity as merged.
3. Decide and name the risk before editing: leave as is, recommend the batch flag default (owner decision, with the measured numbers), or an artist-aware ordering. Any option that adds lookups or ListenBrainz requests per run is **not allowed without the owner's approval**.
4. Optional, diagnostics only: record whether the skipped tail differs in artist mix only if it can be known without resolving more; do not resolve more.

Not allowed without owner approval: edits to `app/api/**`, `app/security/**`, `navidrome_server.py` or domain modules (name the module in the request), changing defaults or flags, new lookups, more ListenBrainz requests per run, raising the 100-per-run MusicBrainz budget, or weakening ownership, duplicate-identity or release-eligibility filtering.

Acceptance: a recorded finding in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with measured numbers and the decision; if code changes, a deterministic synthetic test, `python -m py_compile` on changed files and focused modules only.

### Deferred

- Add `LISTENBRAINZ_TOKEN` to `compose.yaml` and `docs/DEPLOYMENT.md` (touches deployment config; ask first).
- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- Reading deeper into the 1,000-recording CF pool (more ListenBrainz requests; owner approval).
- CF freshness capture (needs an authorized two-sided capture); default-on decisions for the four flags; Last.fm (parked); diversity setting UI (paused).
- A "Saved" page, undo after reload, MBID in save metadata, rendered check of the artist deep-dive Save control.

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
