# Handoff for Claude CLI: recommendation-engine follow-up

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`, then the "`CF_MAX_PAGES = 4` re-measured" and "tag-lane rotation" findings.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- P0f merged: genre circuit breaker on by default (PR #495, `0825f0e0`; simulated-throttle sample 498.1 s to 47.4 s, MusicBrainz artist requests 207 to 18, final list 10 in both); redundant batch flags removed (reconciled PR #497, `b25d2cbd`). Early stop measured healthy-only: no effect, left off.
- P0c merged: ListenBrainz release-group popularity replaces Last.fm in the ranking pass (PR #490, `58182ae0`); the opt-in ListenBrainz tag-radio lane is merged but off (reconciled PR #492, `37014f6f`; original PR #491 closed as superseded). Last.fm stays in classics and deep dives only; as a ranking source it is still parked.
- Repeat rate at simulated intervals measured (PRs #477, #478): decision not to reopen 3.2. Cold-start supply gain (PR #474) and warm final list (PR #475) measured: do not reopen 1.2, 3.1 or 3.2.
- PR #476: steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. PR #479: a failed release-group chunk falls back only for its own recordings.
- Release-group 502s solved (PR #486, merge `f8a248d555bf557e4bb965757d279afbed77cc1d`). Cause: the ListenBrainz release-group endpoint passes 80 comma-joined MBIDs per GET and fails from 81 (dropped connection, then HTML 502 at 83), whichever MBIDs; the old chunk of 100 failed whenever a run had more than 80 distinct groups (the 4-page run had 83). Fix: `RELEASE_GROUP_CHUNK = 50`. Also: retried MusicBrainz attempts count as `recording_lookup_retry`, so `recording_lookup` matches the 100 budget. `lastfm.api` 13 to 40 is the top-40 `album.getInfo` popularity pass (30-day cache).
- 4 pages is now bound by per-artist genre lookups, not the 502s. Cold 4-page profile after the fix: 207 to 319 s, of which `genre_lookup` about 111 to 121 s (up to 75 artists, one uncached MusicBrainz request each at 1.1 s spacing plus about 1.2 s response) and `genre_prefetch` about 38 s. With the merged batch implementation, the owner-approved PR #489 harness sample measured 3 pages at 41.5 s cold (55 albums / 24 artists) and 4 pages at 40.9 s cold (79 albums / 42 artists). `CF_MAX_PAGES` is now **4**; these are single samples.
- ListenBrainz `metadata/artist/` (`inc=tag`): one GET returns tags for many artists. Tags carrying a `genre_mbid` matched the MusicBrainz genre set for 5 of 5 sampled artists. Sizes 25 to 96 artists all returned 200 (47 KB to 173 KB, 0.5 to 1.1 s); **no failing size found**, the limit is above 96 and unlocated. The app needs at most about 75 artists.
- Tag-lane rotation (PR #483, merge `28fb84026201b0779cd604efc5c50aa11203cff5`): **measured and not adopted**; the code was removed after review, only the findings remain. Warm overlap 5/5/4 off vs 4/5/3 on (noise), tag supply unchanged, warm MusicBrainz calls 0 vs 12/6/5, warm time 2.8-4.3 s vs 8.6-20.9 s. Do not reopen without a new idea that adds no lookups.
- Side effect to watch: overlap with the previous list is 5 of 10 because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: P0g — measure the tag-lane early stop under simulated throttling (stubbed, then decide)

P0f is done. Breaker on by default (PR #495, `0825f0e0`); redundant batch flags removed (reconciled PR #497, `b25d2cbd`; original PR #496 closed as superseded). Findings are in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (P0f). `TAG_LANE_EARLY_STOP_ENABLED` is the only default-off flag left in that group: with MusicBrainz healthy, off and on made identical requests (17.3 s and 27.1 s, 8 searches, 38 tag candidates, 10 final, noise), so its value under throttling is the open question. Do not change its default on that evidence.

Do:
1. Read `_run_tag_queries` and `TAG_LANE_EXHAUSTION_THRESHOLD` in `discovery_candidate_gathering.py` and `tests/test_discovery_tag_lane_early_stop.py`.
2. Extend the test-only harness (the P0f `run_p0f.py` lives in the harness project folder, `reports/p0f/`; not committed). Stub MusicBrainz **release-group search** responses (`musicbrainz.org/ws/2/release-group`) so query 2 returns 503 once and every other query answers normally, then a second pattern where queries 2 and 3 both fail. Everything else stays live. Arms: flag off, flag on; one cold run each per pattern (4 runs).
3. Report per arm: tag queries attempted of 8, tag candidates, candidate albums, final list size and source mix, cold seconds, and MusicBrainz request count (must not exceed the healthy 8 plus retries). Aggregate only.
4. Report to the owner **before any default change**. Acceptance for recommending on: more tag candidates than off with no more than the healthy request count, and no added failure. If it only adds retry sleeps, recommend leaving it off.

Cost: 4 live cold runs (about 20 to 50 s each; no extra MusicBrainz requests beyond the stubbed ones). Needs the owner's go-ahead for the live runs; the read and the harness do not.

Acceptance: findings in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`, pushed to `main` only if the owner says so; any default change needs a PR with four green workflows and the owner naming the PR in words.

## Completed task record: batched genre lookup (roadmap P0b) and four-page CF paging

- `prefetch_artist_genres` in `discovery_batch_metadata.py` calls `GET /1/metadata/artist/` (`inc=tag`, `ARTIST_GENRE_CHUNK = 75`) before the genre prefetch and genre stage loops, keeps tags with a `genre_mbid`, and writes `mb:artist-genres:<mbid>` unchanged. The per-artist MusicBrainz loops stay as the fallback. **The live response is a list of entries carrying `artist_mbid`, not a dict keyed by MBID**; a dict-assuming first version silently fell back everywhere, so check `listenbrainz.artist_batch` and `musicbrainz.bounded_get` counts in any live run.
- Measured (single samples): cold 4-page 207.6 s to 51.9 s and 40.9 s, MusicBrainz requests 78 to 10, 3 pages 41.5 s (55 albums / 24 artists), 4 pages 79 albums / 42 artists, warm 3.7 to 8.2 s. Details in `PROJECT_LOG.md`.

### Deferred

- Roadmap P0g is the current task (above). P0c, P0d, P0e and P0f are complete (PR #490, reconciled PR #492, client identity PR #493, breaker PR #495, flag cleanup PR #497; P0d, P0e and the P0f findings pushed directly).
- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- P0b and the approved four-page re-measurement are complete (PR #487 and reconciled PR #489; original PR #488 was superseded).
- Reading deeper into the 1,000-recording CF pool (more ListenBrainz requests; owner approval).
- CF freshness capture (needs an authorized two-sided capture); the tag-lane early stop default (P0g); Last.fm (parked); diversity setting UI (paused).
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

- Default-on flags. The genre circuit breaker is on (PR #495). The two batch flags are removed (PR #497). `TAG_LANE_EARLY_STOP_ENABLED` is off by default and its decision waits on P0g. Steady-state batch (`WARM_BATCH_ENABLED`) and cold-start batch are on.
- Feedback signal (3.3). Merged as PR #456; default on, owner-approved 2026-10-20.
- Refill toggle and read path (3.4). Merged as PR #458 (default on) and PR #459 (stale-while-revalidate). Roadmap 3.4 is complete.
- Candidate freshness (P2). Unmeasured: whether collaborative filtering reflects all-time history. This needs an authorized two-sided capture; do not start it without approval.
- ListenBrainz client. Done in PR #493 (honest `User-Agent` plus token on every ListenBrainz request, never sent to MusicBrainz). Whether it prevents the verification page over repeated runs is unproven. Do not change the user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider. The 0-100 `recommendation_diversity` setting, its API and the MMR penalty mapping already exist; the audit above decides whether anything backend is missing. No UI in backend PRs.
- Feedback positive seed. Merged (PRs #461, #463, #464, #465). One live sample is recorded in the roadmap; any further live run needs the owner's go-ahead.
