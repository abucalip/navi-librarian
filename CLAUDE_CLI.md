# Handoff for Claude CLI: recommendation-engine follow-up

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Testing scope").

## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`, then the "`CF_MAX_PAGES = 4` re-measured" and "tag-lane rotation" findings.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- P0c merged: ListenBrainz release-group popularity replaces Last.fm in the ranking pass (PR #490, `58182ae0`); the opt-in ListenBrainz tag-radio lane is merged but off (reconciled PR #492, `37014f6f`; original PR #491 closed as superseded). Last.fm stays in classics and deep dives only; as a ranking source it is still parked.
- Repeat rate at simulated intervals measured (PRs #477, #478): decision not to reopen 3.2. Cold-start supply gain (PR #474) and warm final list (PR #475) measured: do not reopen 1.2, 3.1 or 3.2.
- PR #476: steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. PR #479: a failed release-group chunk falls back only for its own recordings.
- Release-group 502s solved (PR #486, merge `f8a248d555bf557e4bb965757d279afbed77cc1d`). Cause: the ListenBrainz release-group endpoint passes 80 comma-joined MBIDs per GET and fails from 81 (dropped connection, then HTML 502 at 83), whichever MBIDs; the old chunk of 100 failed whenever a run had more than 80 distinct groups (the 4-page run had 83). Fix: `RELEASE_GROUP_CHUNK = 50`. Also: retried MusicBrainz attempts count as `recording_lookup_retry`, so `recording_lookup` matches the 100 budget. `lastfm.api` 13 to 40 is the top-40 `album.getInfo` popularity pass (30-day cache).
- 4 pages is now bound by per-artist genre lookups, not the 502s. Cold 4-page profile after the fix: 207 to 319 s, of which `genre_lookup` about 111 to 121 s (up to 75 artists, one uncached MusicBrainz request each at 1.1 s spacing plus about 1.2 s response) and `genre_prefetch` about 38 s. With the merged batch implementation, the owner-approved PR #489 harness sample measured 3 pages at 41.5 s cold (55 albums / 24 artists) and 4 pages at 40.9 s cold (79 albums / 42 artists). `CF_MAX_PAGES` is now **4**; these are single samples.
- ListenBrainz `metadata/artist/` (`inc=tag`): one GET returns tags for many artists. Tags carrying a `genre_mbid` matched the MusicBrainz genre set for 5 of 5 sampled artists. Sizes 25 to 96 artists all returned 200 (47 KB to 173 KB, 0.5 to 1.1 s); **no failing size found**, the limit is above 96 and unlocated. The app needs at most about 75 artists.
- Tag-lane rotation (PR #483, merge `28fb84026201b0779cd604efc5c50aa11203cff5`): **measured and not adopted**; the code was removed after review, only the findings remain. Warm overlap 5/5/4 off vs 4/5/3 on (noise), tag supply unchanged, warm MusicBrainz calls 0 vs 12/6/5, warm time 2.8-4.3 s vs 8.6-20.9 s. Do not reopen without a new idea that adds no lookups.
- Side effect to watch: overlap with the previous list is 5 of 10 because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: P0f — read-only evidence brief for the four default-off flags (no code first)

P0e is done (findings on `main`, `0a9d429`, pushed directly at the owner's instruction, no PR). Owner-approved aggregate cold runs, single samples: MusicBrainz tag lane 20.0 s, tag radio only 15.6 s, split (4 MusicBrainz / 4 tag radio) 17.8 s and 25.9 s. The sources return disjoint tag pools (candidate overlap 0/58 MusicBrainz vs radio); final-pick overlap MusicBrainz vs split 9/10, vs radio 5/10. The time differences are within noise, so **MusicBrainz stays the default; split and tag-radio-default were measured and not adopted**. No browser-verification page appeared in 5 live runs (one extra run came from a harness launch mistake). Reopen only with a new idea that adds no lookups and shows a time gain beyond noise. The test-only harness `run_tag_split.py` was not committed (it lives in the harness project folder).

Every remaining item in the roadmap is owner-gated, so the next useful step is a decision brief, not a build: the four flags that are off by default (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, the genre circuit breaker, `TAG_LANE_EARLY_STOP_ENABLED`) each change output or call pattern, and the owner cannot decide on them without one place that shows the evidence.

Do:
1. Read `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (P2 "Default-on flags", the warm and cold findings, the 502 finding) and the code that reads each flag in `discovery_candidate_gathering.py` and `discovery_batch_metadata.py`.
2. Read-only, from code and existing reports, write one table: for each flag, what it changes (output, call pattern, or both), the existing evidence with its source finding, whether that evidence is measured or only unit-tested, the request counts and cold/warm seconds before and after where measured, the failure it guards against, and the risk of turning it on.
3. For each flag, say what single measurement would settle it and what it would cost in live requests. Do not run it. A flag with enough evidence gets a recommendation (on, off, or measure first); a flag without gets "measure first".
4. Report to the owner **before any code change or live run**. Changing a default is the owner's decision.

Acceptance: findings in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `PROJECT_LOG.md`, pushed to `main` only if the owner says so (as for P0d and P0e); any code or default change needs a PR with four green workflows and the owner naming the PR in words.

## Completed task record: batched genre lookup (roadmap P0b) and four-page CF paging

- `prefetch_artist_genres` in `discovery_batch_metadata.py` calls `GET /1/metadata/artist/` (`inc=tag`, `ARTIST_GENRE_CHUNK = 75`) before the genre prefetch and genre stage loops, keeps tags with a `genre_mbid`, and writes `mb:artist-genres:<mbid>` unchanged. The per-artist MusicBrainz loops stay as the fallback. **The live response is a list of entries carrying `artist_mbid`, not a dict keyed by MBID**; a dict-assuming first version silently fell back everywhere, so check `listenbrainz.artist_batch` and `musicbrainz.bounded_get` counts in any live run.
- Measured (single samples): cold 4-page 207.6 s to 51.9 s and 40.9 s, MusicBrainz requests 78 to 10, 3 pages 41.5 s (55 albums / 24 artists), 4 pages 79 albums / 42 artists, warm 3.7 to 8.2 s. Details in `PROJECT_LOG.md`.

### Deferred

- Roadmap P0f is the current task (above). P0c, P0d and P0e are complete (PR #490, reconciled PR #492, client identity PR #493; P0d and P0e findings pushed directly).
- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- P0b and the approved four-page re-measurement are complete (PR #487 and reconciled PR #489; original PR #488 was superseded).
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
- ListenBrainz client. Done in PR #493 (honest `User-Agent` plus token on every ListenBrainz request, never sent to MusicBrainz). Whether it prevents the verification page over repeated runs is unproven. Do not change the user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider. The 0-100 `recommendation_diversity` setting, its API and the MMR penalty mapping already exist; the audit above decides whether anything backend is missing. No UI in backend PRs.
- Feedback positive seed. Merged (PRs #461, #463, #464, #465). One live sample is recorded in the roadmap; any further live run needs the owner's go-ahead.
