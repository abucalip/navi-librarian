# Handoff for Claude CLI: recommendation-engine follow-up

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`, then the "`CF_MAX_PAGES = 4` re-measured" and "tag-lane rotation" findings.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- Repeat rate at simulated intervals measured (PRs #477, #478): decision not to reopen 3.2. Cold-start supply gain (PR #474) and warm final list (PR #475) measured: do not reopen 1.2, 3.1 or 3.2.
- PR #476: steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. PR #479: a failed release-group chunk falls back only for its own recordings.
- Release-group 502s solved (PR #486, merge `f8a248d555bf557e4bb965757d279afbed77cc1d`). Cause: the ListenBrainz release-group endpoint passes 80 comma-joined MBIDs per GET and fails from 81 (dropped connection, then HTML 502 at 83), whichever MBIDs; the old chunk of 100 failed whenever a run had more than 80 distinct groups (the 4-page run had 83). Fix: `RELEASE_GROUP_CHUNK = 50`. Also: retried MusicBrainz attempts count as `recording_lookup_retry`, so `recording_lookup` matches the 100 budget. `lastfm.api` 13 to 40 is the top-40 `album.getInfo` popularity pass (30-day cache).
- 4 pages is now bound by per-artist genre lookups, not the 502s. Cold 4-page profile after the fix: 207 to 319 s, of which `genre_lookup` about 111 to 121 s (up to 75 artists, one uncached MusicBrainz request each at 1.1 s spacing plus about 1.2 s response) and `genre_prefetch` about 38 s. With the merged batch implementation, the owner-approved PR #489 harness sample measured 3 pages at 41.5 s cold (55 albums / 24 artists) and 4 pages at 40.9 s cold (79 albums / 42 artists). `CF_MAX_PAGES` is now **4**; these are single samples.
- ListenBrainz `metadata/artist/` (`inc=tag`): one GET returns tags for many artists. Tags carrying a `genre_mbid` matched the MusicBrainz genre set for 5 of 5 sampled artists. Sizes 25 to 96 artists all returned 200 (47 KB to 173 KB, 0.5 to 1.1 s); **no failing size found**, the limit is above 96 and unlocated. The app needs at most about 75 artists.
- Tag-lane rotation (PR #483, merge `28fb84026201b0779cd604efc5c50aa11203cff5`): **measured and not adopted**; the code was removed after review, only the findings remain. Warm overlap 5/5/4 off vs 4/5/3 on (noise), tag supply unchanged, warm MusicBrainz calls 0 vs 12/6/5, warm time 2.8-4.3 s vs 8.6-20.9 s. Do not reopen without a new idea that adds no lookups.
- Side effect to watch: overlap with the previous list is 5 of 10 because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Current focus: P0c — investigate Last.fm popularity-pass latency read-only first. PR #487 batched genre lookup and PR #489 four-page CF paging (reconciled from original PR #488) are merged; do not reopen them without new evidence.

## Completed task record: batched genre lookup (roadmap P0b)

Why: it removes about 150 s of cold time at 4 pages, with identical supply, and it is the gate for revisiting `CF_MAX_PAGES = 4`. The owner approved the approach and revised the ListenBrainz rule (see Standing rules): added ListenBrainz requests are allowed because they save time.

Do:
1. Read `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the finding "batched genre lookup, endpoint limit and 4-page re-measurement" and roadmap P0b), the genre prefetch (`genre_prefetch_started`) and the genre stage (`genre_lookup_started`) in `discovery_candidate_gathering.py`, and `discovery_batch_metadata.py`.
2. Add a batch client function to `discovery_batch_metadata.py` (no new module, so no Dockerfile change): `GET https://api.listenbrainz.org/1/metadata/artist/` with `artist_mbids` (comma-joined) and `inc=tag`, chunks of up to 75 (`ARTIST_GENRE_CHUNK`; named constant with a comment citing the measured 96-artist pass). For each returned artist keep tags that have a `genre_mbid`, lower-cased and stripped, sorted and de-duplicated, exactly the shape the per-artist loop writes. Write them to `providers.metadata_cache_set(f"mb:artist-genres:{artist_id}", ...)` so everything downstream (cache keys, 90-day TTL, `genre_cache`) is unchanged.
3. Call it before the prefetch loop (profile artists plus the top `CANDIDATE_PREFETCH_LIMIT` candidate artists) and before the genre stage loop (the `artist_ids` list), only for artists not already cached. Keep the existing per-artist MusicBrainz loops as the fallback: an artist missing from the response, a non-200, a non-JSON body or any exception must leave it uncached so the loop looks it up as before. Never raise out of the batch. Do not change the 1.1 s spacing, the circuit breaker or the budget logic.
4. Record the new call with `record_provider_call("listenbrainz", "artist_batch")`.
5. Tests (stubbed HTTP, `tests/test_discovery_batch_lookup.py` or a narrow new test file): chunking at the constant, genre filtering by `genre_mbid`, cache-write shape, fallback on missing artist and on failure, cached artists not re-requested, spacing sleeps skipped for batch hits. Run only the focused modules for the files you change plus `python -m py_compile` on each changed file. Do not run the full suite.
6. Live measurement (owner pre-approved the batch work and the live runs; re-confirm only if the plan changes): on the PR branch, one cold 4-page run (the harness-only `CF_MAX_PAGES = 4` override, not a code change) then two warm runs; report wall time, per-stage seconds, MusicBrainz and ListenBrainz request counts before and after, and CF albums/artists. Aggregate only, disposable data dir deleted. Harnesses from the previous session are in the harness project folder under `reports/repeat-rate/` (`run_genre_arm.py` has the batch patch used for the measurement).
7. Update `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`, and this file's handoff when done.

Acceptance: a PR with the four workflows green on its head, the focused tests listed in the description, and the before/after numbers. The owner separately approved raising `CF_MAX_PAGES`; this landed in PR #489 (reconciled from original PR #488). Do not raise it further without another decision.

### Deferred

- Roadmap P0c: test batch lookups for Last.fm (27.5 s of a 39.6 s cold run at 4 pages is up to 40 sequential `album.getInfo` calls). No batch method is known; check the docs, then concurrency, then ListenBrainz substitutes. Any change to Last.fm call count or pacing needs owner approval; Last.fm as a ranking source is otherwise parked.
- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- P0b and the approved four-page re-measurement are complete (PRs #487 and #488).
- Reading deeper into the 1,000-recording CF pool (more ListenBrainz requests; owner approval).
- CF freshness capture (needs an authorized two-sided capture); default-on decisions for the remaining flags (`BATCH_TITLE_FILTER_ENABLED` and steady-state `CF_BATCH_RESOLUTION_ENABLED`, genre breaker, tag-lane early stop); Last.fm (parked); diversity setting UI (paused).
- A "Saved" page, undo after reload, MBID in save metadata, rendered check of the artist deep-dive Save control.

## Testing scope (standing owner rule, 2026-10-20)

- **Agents working on PRs must never run the full test suite** (`python -m unittest discover -s tests`). This is permanent, not per-session. The owner runs the full suite independently and CI runs it on the PR head. Run only the focused test modules for the files you change, plus `python -m py_compile` on each changed Python file. A few modules (for example `test_discovery_cold_start_batch`) import siblings and need `python -m unittest discover -s tests -p <file>`.
- This overrides any full-suite step in `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`; those now carry the same rule. The four required CI workflows still run on the PR head.
- In the PR description, say which focused modules you ran. Do not report a full-suite result you did not observe.

## Standing rules

- GitHub is the source of truth. Never merge local-only commits.
- Ownership checks, duplicate-identity suppression and release-eligibility filtering are never weakened to raise coverage.
- No added lookups per run. The uncached MusicBrainz budget stays at 100 per run.
- ListenBrainz requests (owner, 2026-10-20, revised 2026-10-21): the limit exists to protect per-run time. Added ListenBrainz requests that **save time** are allowed, for example batch lookups that replace many slower per-item requests (measured: +3 ListenBrainz GETs replace about 79 MusicBrainz requests and cut a cold 4-page run from about 212 s to about 40 s). Requests that add time, or whose only effect is more data to resolve, still need owner approval. Recent listens stay at 3 pages of 100 within 30 days. Always measure the time effect and report the request counts before and after.
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
