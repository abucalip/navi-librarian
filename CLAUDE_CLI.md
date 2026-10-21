# Handoff for Claude CLI: recommendation-engine follow-up

Read this first. GitHub is the single source of truth; this file never overrides the docs it points to, except where it states an owner instruction explicitly (see "Permanent rules").

## Current handoff: Python module package layout (active priority)

The owner wants root-level Python modules organized into logical packages. Follow `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. This is a repository-layout effort, not permission to rewrite behavior or reopen the completed modularization roadmap.

**Owner decisions (2026-10-21):** `acquisition/` first, in three PRs; fix the `music_key` inversion (separate code PR, before the discovery core moves); `recommendation_cooldown` moves with the store modules. **Done:** acquisition PR 1 (request and queue, 8 modules) = PR #517, squash-merged to `main` as `2411740dc74d57b1a4fddbd33eeef80a461b40dd` from exact final head `cd39e83ee7abe50378c015d4486b6306d4690270` (owner named PR 517; compile, test-and-build, container-smoke, validate-container all passed on it). Root Python modules 40. `navidrome_server.py` keeps the alias `acquisition_orchestration` because `tests/test_slskd_transfers.py` patches `navidrome_server.acquisition_orchestration.*`. Publishing/deployment stay paused (the main-push runs were validation only). **Acquisition PR 2 (monitor, 5 modules) = PR #518, squash-merged as `32b23176e1c22317ad1ce662b8ca22cb8970409d` from head `29e7879beb162098cc612e27e4781e1ba40bf6e4`; four checks passed. Root Python modules 35.**

**Next tasks, in order, one PR each (no move is pre-approved beyond the owner's order above; branch from refreshed `main`, re-run the caller/path/test audit on current main first):**
1. ~~Acquisition PR 2, monitor~~ **(DONE, PR #518):** `watcher`, `watcher_startup`, `progress_accounting`, `progress_snapshots`, `monitor_payload` -> `acquisition/` (`watcher -> progress_accounting` is the only internal edge). Update `navidrome_server.py`, tests, Dockerfile root COPY line, add a packaging test like `test_acquisition_request_modules_live_in_acquisition_package`.
2. ~~Acquisition PR 3, import and cleanup~~ **(DONE, PR #519 merged as `6e12466`):** `completion`, `import_files` (renamed from `import`, a Python keyword), `import_service`, `cleanup`, `recovery` -> `acquisition/`. Root Python modules 30. Record the merge SHA once the owner names the PR.
3. ~~`music_key` inversion~~ **(OPEN PR, awaiting four checks and owner merge):** now `recommendation/music_key.py`, re-exported by `discovery_recommendations`; identity test in `tests/test_music_key.py`.
4. **`discovery/` leaf cluster (6):** `classics_candidates`, `classics_genres`, `classics_ratings`, `deep_dive_candidates`, `new_releases`, `recommendation_payload` (server-only callers).
5. **Allocator (3):** `allocation_contract`, `personal_allocator`, `mmr`; update `recommendation_feedback` and `recommendation/mmr_evaluate` imports.
6. **Store/refresh with cooldown:** `store`, `snapshot`, `refresh`, `list_payload`, `candidate_supply`, plus `recommendation_cooldown` (owner decision); update `recommendation/profile_comparison` and `replay` imports.
7. **Gathering core (6):** `candidate_gathering`, `batch_metadata`, `lb_tag_lane`, `tag_queries`, `library_snapshot`, `recommendations`; rewrite the `mock.patch("discovery_*...")` string targets (6 on `candidate_gathering`, one each on `library_snapshot` and `lb_tag_lane`).
`recommendation_run_metrics`, `navidrome_server` and the three single-purpose modules stay in root. Housekeeping candidate (ask first): the tracked stray `Dockerfile-E` looks like an accidental sed backup. Local note: the owner installed `httpx`, but the default `python3` here (Homebrew 3.12) still cannot import it, so `test_slskd_transfers` adapter tests error locally; CI covers them, or point at the interpreter that has httpx.

After the layout work, or if the owner redirects: P1a (deeper CF pool, brief and plan only, no live run) below.

**Acceptance:** current-main dependency evidence and a caller map support the chosen boundary; behavior and safety remain unchanged; Docker/CI paths are correct; required CI passes on the exact PR head; and documentation distinguishes merged, tested, published, deployed, and runtime-verified states.

---
## Getting started

1. Clone `abucalip/navi-librarian`, fetch `main`, branch from current `main`.
2. Read, in order: `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (the findings "cold-start supply gain", "steady-state (warm) final list" and "Verification of caching + warm batch path", then Phases 1.2, 3.1, 3.2) and the top of `PROJECT_LOG.md`, then the "`CF_MAX_PAGES = 4` re-measured" and "tag-lane rotation" findings.
3. Check open PRs and the four required workflows on the exact head you push.

## Current state

- P0f merged: genre circuit breaker on by default (PR #495, `0825f0e0`; simulated-throttle sample 498.1 s to 47.4 s, MusicBrainz artist requests 207 to 18, final list 10 in both); redundant batch flags removed (reconciled PR #497, `b25d2cbd`). Early stop measured healthy-only: no effect, left off.
- P0g merged: tag-lane early stop on by default (PR #498, `ad88bbbb`). With one tag query exhausted by simulated 503s the lane now runs 8 of 8 queries: 23 and 25 tag candidates against 5, 11 to 12 MusicBrainz requests (8 plus retries), +5 to 10 s, final list 10; with two consecutive exhausted queries it still stops (no gain). MusicBrainz OAuth client credentials in `config.env` are **not useful** here: `client_credentials` is rejected and a user bearer token did not avoid real 503s (5 in 12 requests). The app does not use them; do not wire them in.
- P0c merged: ListenBrainz release-group popularity replaces Last.fm in the ranking pass (PR #490, `58182ae0`); the opt-in ListenBrainz tag-radio lane is merged but off (reconciled PR #492, `37014f6f`; original PR #491 closed as superseded). Last.fm stays in classics and deep dives only; as a ranking source it is still parked.
- Repeat rate at simulated intervals measured (PRs #477, #478): decision not to reopen 3.2. Cold-start supply gain (PR #474) and warm final list (PR #475) measured: do not reopen 1.2, 3.1 or 3.2.
- PR #476: steady-state builds use the batch path (`WARM_BATCH_ENABLED`, default on) and cache batch results under `mb:recording_batch:<mbid>`. PR #479: a failed release-group chunk falls back only for its own recordings.
- Release-group 502s solved (PR #486, merge `f8a248d555bf557e4bb965757d279afbed77cc1d`). Cause: the ListenBrainz release-group endpoint passes 80 comma-joined MBIDs per GET and fails from 81 (dropped connection, then HTML 502 at 83), whichever MBIDs; the old chunk of 100 failed whenever a run had more than 80 distinct groups (the 4-page run had 83). Fix: `RELEASE_GROUP_CHUNK = 50`. Also: retried MusicBrainz attempts count as `recording_lookup_retry`, so `recording_lookup` matches the 100 budget. `lastfm.api` 13 to 40 is the top-40 `album.getInfo` popularity pass (30-day cache).
- 4 pages is now bound by per-artist genre lookups, not the 502s. Cold 4-page profile after the fix: 207 to 319 s, of which `genre_lookup` about 111 to 121 s (up to 75 artists, one uncached MusicBrainz request each at 1.1 s spacing plus about 1.2 s response) and `genre_prefetch` about 38 s. With the merged batch implementation, the owner-approved PR #489 harness sample measured 3 pages at 41.5 s cold (55 albums / 24 artists) and 4 pages at 40.9 s cold (79 albums / 42 artists). `CF_MAX_PAGES` is now **4**; these are single samples.
- ListenBrainz `metadata/artist/` (`inc=tag`): one GET returns tags for many artists. Tags carrying a `genre_mbid` matched the MusicBrainz genre set for 5 of 5 sampled artists. Sizes 25 to 96 artists all returned 200 (47 KB to 173 KB, 0.5 to 1.1 s); **no failing size found**, the limit is above 96 and unlocated. The app needs at most about 75 artists.
- Tag-lane rotation (PR #483, merge `28fb84026201b0779cd604efc5c50aa11203cff5`): **measured and not adopted**; the code was removed after review, only the findings remain. Warm overlap 5/5/4 off vs 4/5/3 on (noise), tag supply unchanged, warm MusicBrainz calls 0 vs 12/6/5, warm time 2.8-4.3 s vs 8.6-20.9 s. Do not reopen without a new idea that adds no lookups.
- Side effect to watch: overlap with the previous list is 5 of 10 because supply is stable run to run, so the soft cooldown (max 25%, 7-day half-life, 30-day expiry) is the only repeat damper.
- `LISTENBRAINZ_TOKEN` is in Compose/docs (PR #472, not deployed). The token is in `config.env` in the harness project folder; never print or commit it. Diversity setting: paused by the owner. `navidrome_server.py` is 2,448 of 2,650 lines.

## Next task: P1a — deeper CF pool: measure first, change nothing without approval (read-only design, then one gated measurement)

P0i is merged (PR #499, docs only: stale default-flag statements fixed). The artist deep-dive Save check (PR #500) and the Saved page (PR #501) are merged; their remaining Saved-area items (undo after reload, MBID in save metadata) are separate and not this task.

**Question.** `CF_MAX_PAGES = 4` x `CF_PAGE_SIZE = 100` reads the first 400 of a roughly 1,000-recording ListenBrainz CF pool (`discovery_candidate_gathering.py`, `fetch` loop near line 185). Would reading deeper (pages 5 to 10) add enough distinct, eligible, unowned albums to change the final list, at an acceptable time cost?

**Gate (owner rule, 2026-10-21).** Added ListenBrainz requests are allowed only when they save time. Deeper paging adds requests whose effect is more data to resolve, so it **needs owner approval before any live run**, and the owner wants P0h (CF freshness, parked) settled first because deeper pages of a stale pool are not worth reading. Do the read-only part, then stop and ask.

Do, in order:
1. Read-only, no network: in the code and the findings ("CF supply is limited by pages read", "`CF_MAX_PAGES = 4` re-measured", P0b/P0f/P0g, P0h baseline), write a short brief in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` under P1: what grows with pages (batch recording lookups at 50 per chunk? release-group chunks of 50, genre batch size 75 per `ARTIST_GENRE_CHUNK`), what stays bounded (uncached MusicBrainz budget 100; batch hits do not spend it), the endpoint limits already found (release-group GET fails from 81 MBIDs; artist genre batch has no failing size up to 96), and an estimate of added requests and time per extra page from the existing measurements (3 pages 41.5 s, 4 pages 40.9 s cold, so marginal time per page is small and unmeasured beyond 4).
2. Propose one measurement plan: pages 4 vs 6 (or 8), fresh data dir, slskd off, aggregate only, single cold plus one warm sample per arm, test-only harness not committed, counts of `listenbrainz.*` and `musicbrainz.bounded_get` before and after, final-list overlap, distinct artists, eligible unowned albums, cold time. State the added ListenBrainz GETs (about 1 CF page + 1 recording batch + up to 1 release-group GET per extra 100 recordings) and the pass/fail thresholds before running (for example: cold time within +10 s of the 4-page sample, eligible unowned albums up by at least 20%, no new 502s or 429s).
3. Push the brief and plan directly to `main` (documentation-only rule), and **wait for the owner** to approve the live measurement before any run. Do not change `CF_MAX_PAGES`.

If the owner approves the run: run only what the plan names, record aggregates and request counts in the doc and `PROJECT_LOG.md`, and open a separate PR for any default change (keep the flag/constant change one line, with a rollback note).

Acceptance: the brief and plan are in the doc with numbers sourced from existing findings (cite them); no live run, no network, no code change until approval.

Other options if the owner prefers something else: repeat the P0h capture after CF recompute (go-ahead naming the 1 statistics request); one healthy cold run and one warm run to confirm defaults live; undo after reload, MBID in save metadata (backend, needs approval).

## Completed task record: batched genre lookup (roadmap P0b) and four-page CF paging

- `prefetch_artist_genres` in `discovery_batch_metadata.py` calls `GET /1/metadata/artist/` (`inc=tag`, `ARTIST_GENRE_CHUNK = 75`) before the genre prefetch and genre stage loops, keeps tags with a `genre_mbid`, and writes `mb:artist-genres:<mbid>` unchanged. The per-artist MusicBrainz loops stay as the fallback. **The live response is a list of entries carrying `artist_mbid`, not a dict keyed by MBID**; a dict-assuming first version silently fell back everywhere, so check `listenbrainz.artist_batch` and `musicbrainz.bounded_get` counts in any live run.
- Measured (single samples): cold 4-page 207.6 s to 51.9 s and 40.9 s, MusicBrainz requests 78 to 10, 3 pages 41.5 s (55 albums / 24 artists), 4 pages 79 albums / 42 artists, warm 3.7 to 8.2 s. Details in `PROJECT_LOG.md`.

### Deferred

- Roadmap P0h is parked (see Open items); P1a (deeper CF pool, brief and plan only) is the next task; P0i is merged (PR #499). P0c, P0d, P0e, P0f and P0g are complete (PR #490, reconciled PR #492, client identity PR #493, breaker PR #495, flag cleanup PR #497, early stop on PR #498; P0d, P0e and the P0f and P0g findings pushed directly).
- Confirm the client fix over more runs; reopen the failure-class thread only if CF failures return.
- P0b and the approved four-page re-measurement are complete (PR #487 and reconciled PR #489; original PR #488 was superseded).
- Reading deeper into the 1,000-recording CF pool: now the next task (P1a above); live measurement still needs owner approval.
- CF freshness capture: repeat after ListenBrainz recomputes CF for the imported history (needs a go-ahead); Last.fm (parked); diversity setting UI (paused).
- Saved-area leftovers: undo after reload, MBID in save metadata. (The Saved page is PR #501 and the deep-dive Save rendered check is PR #500, both merged.)

## Permanent rules (owner, do not remove)

1. **Never run the full test suite.** Agents must never run `python -m unittest discover -s tests` or any equivalent full-suite command, in any session, for any reason. Run only focused modules for the files you change plus `python -m py_compile`. The owner and the `test-and-build` CI workflow run the full suite.
2. **Documentation-only updates are pushed directly to `main`.** No PR for changes that touch only documentation (`*.md` files such as `CLAUDE_CLI.md`, `PROJECT_LOG.md`, `docs/`). Refresh `main` first, commit with the attribution line, and push. Anything that also changes code, tests, Dockerfile/Compose or workflows still goes through a PR with the four required workflows on its exact final head.

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
- Documentation-only changes go directly to `main` (see "Permanent rules"); any change touching code, tests, Dockerfile or workflows still needs a PR with the four checks.
- The full suite has one known macOS-only failure: `test_acquisition_import.py::test_success_persists_importing_before_import_and_then_imported` (`/var` → `/private/var`). It fails on clean `main` too. CI on Linux passes it. The owner's independent full-suite run covers it; do not run the suite to check it.

## Open items and owner decisions

- Default-on flags. The genre circuit breaker is on (PR #495). The two batch flags are removed (PR #497). `TAG_LANE_EARLY_STOP_ENABLED` is on (PR #498). Steady-state batch (`WARM_BATCH_ENABLED`) and cold-start batch are on.
- Feedback signal (3.3). Merged as PR #456; default on, owner-approved 2026-10-20.
- Refill toggle and read path (3.4). Merged as PR #458 (default on) and PR #459 (stale-while-revalidate). Roadmap 3.4 is complete.
- Candidate freshness (P2). Baseline captured but inconclusive: ListenBrainz had not yet recomputed CF for the imported history. Repeat the P0h capture later, only with the owner's go-ahead.
- ListenBrainz client. Done in PR #493 (honest `User-Agent` plus token on every ListenBrainz request, never sent to MusicBrainz). Whether it prevents the verification page over repeated runs is unproven. Do not change the user agent or fingerprint to get around the check.
- Last.fm as a source is parked by the owner. Do not start a quality test or a combined path without a new decision.
- Exploration slider. The 0-100 `recommendation_diversity` setting, its API and the MMR penalty mapping already exist; the audit above decides whether anything backend is missing. No UI in backend PRs.
- Feedback positive seed. Merged (PRs #461, #463, #464, #465). One live sample is recorded in the roadmap; any further live run needs the owner's go-ahead.
