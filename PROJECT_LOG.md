## 2026-10-20 — Steady-state (warm) final list measured (docs only)

- Branch `docs/warm-final-list-measurement`. Offline warm-path trace plus one owner-approved live run (cold, then two warm refreshes, count 10, aggregate only, data dir deleted). Final list 10 distinct artists, top-2 20% in all three; overlap with the previous list 4 and 3 of 10; family cap rejected 24 to 39 per run and never blocked a full list; warm CF unowned supply 4 and 14 vs 17 cold (batch hits are not cached, so warm runs re-spend the 100 budget; inferred from code).
- Decision: no reopening of 1.2, 3.1, 3.2; no code change. Harness bug: final-list source mix not captured. Details in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.
- Tests: none run, no code changed. PR/merge SHA and CI: see the PR. Not done: publication, deployment.

## 2026-10-20 — Cache batch hits and warm batch path (code)

- Branch `feat/cache-batch-hits-warm-batch`. Owner-approved after the warm measurement: `WARM_BATCH_ENABLED` (default on) sends steady-state builds through the batch path; batch results are cached under `mb:recording_batch:<mbid>` (180 days), read before any batch request, and never written to `mb:recording:`. Cache write failures are swallowed. Fewer lookups per run, no new request types; budget unchanged. `discovery_candidate_gathering.py`, `tests/test_discovery_cold_start_batch.py`, `tests/test_discovery_batch_lookup.py`.
- Tests (focused only, no full suite): `test_discovery_cold_start_batch` (15), `test_discovery_batch_lookup` (18), `test_discovery_candidate_gathering` (34), `test_discovery_candidate_supply`, `test_discovery_candidate_replenishment`, `test_discovery_candidate_genre_prefetch`, `test_discovery_save_tag_seed`, `test_recommendation_replay_capture` and the genre/tag-lane breaker modules, all OK; `py_compile` on the changed module. CI: see the PR.
- Live check (owner-approved, aggregate only, data dir deleted): warm CF unowned 17 (was 4/14), warm time 32 s then 3 s (was 202-230 s), MusicBrainz calls 78 / 10 / 0, spread unchanged, overlap with previous list 5 of 10. Details in the roadmap. Not done: merge, publication, deployment.

## 2026-10-20 — Cold-start supply gain measured in the final list (docs only)

- Branch `docs/final-list-supply-measurement`. Offline trace of CF recording to final list, then an owner-approved live pair (before = `961266d`, the #471 parent; after = `7deaf46`), aggregate only, data dirs deleted. Final list 10 distinct artists, top-2 20% both times (allocator takes one album per artist); CF share of the final 10 rose 3 to 7; CF unowned candidates 4 to 17; 170 s vs 95 s (one sample each, noisy).
- Decision: no reopening of 1.2, 3.1, 3.2; no code change. Details in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.
- Tests: none run, no code changed. Merged to `main` as `aedc34e44034a04bb20c177458f9c8b73b12900f` (squash, PR #474) from exact head `b46f13df69be63d1eb1d25047bac04b4eb2f388e`; compile, test-and-build, container-smoke and validate-container all passed. Next task (steady-state warm measurement) handed off in `CLAUDE_CLI.md`. Not done: publication, deployment.


## 2026-10-20 — Recommendation roadmap uncluttered

- Replaced the 683-line `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with an 81-line active plan focused on the next task, remaining decision-gated phases, current implementation facts, guardrails, and evaluation acceptance.
- Preserved the former document verbatim in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS_ARCHIVE.md` so historical measurements, completed work, and prior task orderings remain available.
- Immediate next action is unchanged: offline-trace the cold-start supply path, then obtain owner approval before a disposable aggregate-only live run to measure the effect on the final list. No code changed; no tests were run. Publishing/deployment remain paused.

## 2026-10-20 — LISTENBRAINZ_TOKEN in deployment config

- Branch `deploy/listenbrainz-token`. Owner-approved deployment-config change: `LISTENBRAINZ_TOKEN: ${LISTENBRAINZ_TOKEN:-}` in `compose.yaml`, a blank entry in `.env.example`, and a note plus commented example in `docs/DEPLOYMENT.md`. Empty default keeps behavior unchanged; no secret value committed. Checks: Docker is not installed on this machine, so `docker compose config` was not run (CI `container-smoke` and `validate-container` cover packaging); no local validation was possible (the one-line addition copies the neighbouring variables' syntax). Merged to `main` as `d7e5746b82b597e82c5747f0fdcfdf21ee17800a` (squash, PR #472) from exact head `4c0904657db983195d84abb79db6269edc1aa423`; compile, test-and-build, container-smoke and validate-container all passed. Not done: publication, deployment (the running container gets the token only if the real `.env` or Compose file sets it).

## 2026-10-20 — Cold-start batch no longer spends the MusicBrainz budget

- Branch `fix/cold-start-batch-budget` (includes the docs of PR #470). Owner-approved: prefetch all uncached CF recordings in batches (+1 ListenBrainz POST, +1 GET per cold run); batch hits do not count against the 100 budget; misses still do. `discovery_candidate_gathering.py`, `tests/test_discovery_batch_lookup.py`.
- Live: 200/200 resolved, 15 artists, top-2 47.5%, 0 budget-skipped, 117 s. Focused modules run listed in the roadmap section; the full suite was not run (owner rule). Merged to `main` as `93225291c03214f377689875df12454f6eb97375` (squash, PR #471) from exact head `230cf97b44807fb07c60fd5a76de8f5dce483b97`; compile, test-and-build, container-smoke and validate-container all passed. PR #470 closed as superseded. Not done: publication, deployment.

## 2026-10-20 — Cold-start batch path measured (docs only)

- Branch `docs/cold-start-batch-measurement`. Offline: `refresh_personal` passes `_cold_start=True` on a first build, which enables the batch path (`COLD_START_BATCH_ENABLED`); the earlier live pair did not.
- Live run (owner-approved, aggregate only, data dir deleted): 117 s, 100 of 200 CF recordings resolved, 100 skipped, 4 artists, top-2 55%. Batch hits count against the 100 budget in `discovery_candidate_gathering.py`, so batch is faster but no wider.
- Decision: owner approved a corrected option (prefetch all, batch hits free); see the next entry. This branch's docs shipped inside PR #471.

## 2026-10-20 — Phase 4.3 wider CF pool: finding, counter, client identity, live pair (PR #469)

- Branch `docs/cf-pool-phase-4-3`. Read the official ListenBrainz recommendation docs: only `count` and `offset` exist; no artist-type or other filter. Phase 4.3 closed with no paging change (extra ListenBrainz requests need the owner).
- Code, owner-approved: `cf_paging.total_mbid_count` in `discovery_candidate_gathering.py` (no extra request); `listenbrainz_client.request_headers()` sends an honest User-Agent and an optional `LISTENBRAINZ_TOKEN`. Focused tests: `test_discovery_candidate_gathering`, `test_discovery_candidate_supply` (53, OK), `test_listenbrainz_client` (7, OK), `py_compile`. No full suite. CI: see the PR.
- Live cold/warm pair (owner-approved, aggregate only, data dir deleted): recent-listens timeout did not recur, 0 CF failures in both runs, pool 1,000 and 200 read; cold run budget-bound (86 skipped, 6 artists), warm run 15 artists. One sample; a first wrapper launch may have run a stray extra pass. Details in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.
- Earlier trace claim corrected: the 4-artist share is over resolved recordings only.
- Merged to `main` as `eca44e52dedfb5aec188faf287a8c0696d7566c7` (squash, PR #469) from exact head `439c54be6c9c687aee9f7857cf2015850753a237`; compile, test-and-build, container-smoke and validate-container all succeeded on that head.
- Remaining: the cold-run budget decision (batch resolution or ordering), `LISTENBRAINZ_TOKEN` in `compose.yaml` and `docs/DEPLOYMENT.md`, confirming the client fix. Not done: merge, publication, deployment.

## 2026-10-20 — Candidate supply diagnosis: trace, deferred live run, PR #468 closed (docs only)

- Offline trace: budget and artist-cap skips `continue` before the CF record is appended, so they never reach `cf_failure_classes`; the 103 "other" failures (97 + 103 = 200) are exceptions outside the old allowlist. PR #467 (`2794237`) widened it; see the roadmap section "Candidate supply diagnosis".
- Live pair (owner-approved) not recorded: two attempts failed after 30 s with a read timeout on recent listens, before any MusicBrainz call; a plain request to the same endpoint returned 200. Client left unchanged. Throwaway data dirs were kept outside the repo; no captures were written.
- PR #468 (recent-listens page cap 3 to 5) closed unmerged by owner decision (ListenBrainz request cost). Branch `feat/listens-page-cap` kept.
- Tests: none run for this docs entry. Code PR #467 CI: see its entry. Published directly to `main` on the owner's instruction (no PR).
- Next: roadmap Phase 4.3, wider CF pool (`CLAUDE_CLI.md`); retry the live pair later.

## 2026-10-20 — Exploration setting audit (docs only)

- Merged to `main` as `af801d6` (squash, PR #466) from exact head `0da5d6086ad9eb302b5633f7e8adfadbf2e147b9`; compile, test-and-build, container-smoke and validate-container all succeeded on that head. The squash title still says "UI-only next"; the content and this log supersede it (UI stays blocked, diversity setting paused). Recorded directly on `main` at the owner's instruction.
- Branch `docs/exploration-setting-audit`. Traced `recommendation_diversity` end to end, confirmed setting 0 is a no-op and measured settings 0/25/50/75/100 on a synthetic pool with the production allocator. Decision: no new backend mapping needed; the Settings UI stays blocked by `docs/DIVERSITY_SETTING_ROADMAP.md` until its gates close (review of PR #466 caught an earlier draft that implied otherwise); 75-100 is flat (penalty saturates at 0.75). Details in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.
- Live sample (owner-approved, one run): settings 0/25/50/75/100 gave identical output on a 24-album pool; diversity setting paused by the owner. Next priority handed off in `CLAUDE_CLI.md`: candidate supply diagnosis (103 of 200 CF recordings unresolved, 4 CF artists).
- Tests: none run, no code changed (measurement script only, kept outside the repo). PR/merge SHA and CI: see the PR.
- Not done: UI control, repeat-rate measurement, private-capture measurement, publication, deployment.

## 2026-10-20 — Save-seed diagnostics counters and live measurement (merged as PR #465)

- Branch `seed-diagnostics`: `recommendation_run_metrics.record_count` and `snapshot_and_reset()["counts"]`; seven integer `save_seed.*` counters (six at first, plus `mbid_known_no_cached_genres` added after review) recorded in `discovery_candidate_gathering.py` after the seed block succeeds. No lookup, query-selection, quota, scoring or flag change; `navidrome_server.py` and `app/api/**` untouched. Owner approved the domain-module edit for this task.
- Tests run (focused only, no full suite): `test_discovery_save_tag_seed` (14), `test_recommendation_run_metrics` (6), `test_discovery_candidate_gathering` (32), `test_discovery_candidate_genre_prefetch` (6), plus `py_compile` on changed files. CI on the PR head: see the PR.
- Live run (owner-approved, aggregate only): one sample, 4 saves. `saved_artists` 4, `from_cached_genres` 1 (pre-review semantics: MBID known; since split into `from_cached_genres` and `mbid_known_no_cached_genres`, run not repeated), `from_metadata_genres` 2, `skipped_no_genres` 1, `initial_queries_changed` 1, `replenish_queries_changed` 0. Baseline 217 s, seeded 249 s, 10 recommendations each; not a timing result. Limits in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (roadmap 3.3).
- Merged to `main` as `6e1054b56c531eb4fbad912f8ffe1d300c358339` (squash) from exact head `d962dd1fc8a022b2d75f3565134d6ab5357ff97b`; compile, test-and-build, container-smoke and validate-container all succeeded on that head. Reviews: counter semantics fixed (`from_cached_genres` by outcome, `mbid_known_no_cached_genres` added, counters-disabled equivalence test); a double-count claim was disproved by test. Counters are seven, not six.
- Not done: publication, deployment, runtime verification; candidate quality of the changed query is unmeasured.

## 2026-10-20 — Roadmap 3.3 saved-album tag-query seed (merged as PR #461)

- Merged to `main` as `ace28d3f2ad76ca33f6ff7b103586d50e355b066` from exact tested PR head `8c2c418f912fc8656717c5f4c851bdfb952554aa`.
- Review follow-up: fixed the query-budget comparison to use a snapshot of the original profile genre cache, not the cache after seed-specific entries were added. Added a regression fixture for a saved artist outside the original top-15 profile-cache reads; initial and replenishment query counts are capped against the unseeded plan.
- Behavior: active saved album feedback (`for_me`) contributes a decaying artist seed (30-day half-life, 90-day expiry from `created_at`) to supplementary tag-query selection. Existing 6-profile/2-exploration quotas remain unchanged; only cached/stored genres are used, no new provider lookups are added, and feedback-provider failures fall back to unseeded selection. No live recommendation run.
- Full unit suite ran in CI: **1,096 tests, OK**. All four required workflows passed on the exact PR head: Python syntax/acquisition-safety run `39440622871`, Docker packaging/full suite/build run `39440622839`, container runtime smoke run `39440622897`, validation-only multi-architecture image validation run `39440623011` (publishing paused).
- Not done: the shipped UI has no save action, so only API callers create saves; handed off in `CLAUDE_CLI.md` as two tasks: a side-effect-free backend `save` first, then the UI Save action.
- Publishing, deployment, and production-runtime verification remain unperformed; publishing remains paused.

## 2026-10-20 — Deep-dive candidate collection extraction (merged as PR #460)

- Merged to `main` as `4201ed91333ec823b2c00684ab71c82ccd0a7085` from exact head `74e5b35da5dd041cb2fa0143310c1d35c576843d`. Compile, test-and-build, container-smoke and validate-container all passed on that head (run ids 39437774460, 39437774269, 39437774401, 39437774629).
- Purpose: free headroom under the 2,650-line server ceiling for recommendation work. Seam: `_build_artist_deep_dive_list()` collection policy, which had no direct tests. New `discovery_deep_dive_candidates.py` (`collect_missing_album_candidates`, `merge_resolved_pool_candidates`, `collect_similar_artist_candidates`, `enrich_candidate_genres`); lookups and the 0.15 s pacing are injected. The adapter keeps the snapshot read, the personal-list cache read, provider callables, year resolution and the response dict. Dockerfile COPY list updated.
- Size: `navidrome_server.py` 2,649 → 2,535 lines; `_build_artist_deep_dive_list` 191 lines shrank accordingly. `recommend_new_music()` (432/450) and `_discovery_acquire_album_impl()` (278/280) unchanged. Ceilings unchanged.
- Verification observed: 9 new direct tests in `tests/test_discovery_deep_dive_candidates.py`; a one-off run of the old `main` builder vs the new one with identical stubbed providers gave identical output (28 items; script not committed). Before the owner's no-full-suite rule was stated, one full-suite run (1,087 tests) showed only the known macOS `/var` failure. `check_server_size.py` and `check_app_legacy_imports.py` OK.
- Not done: no browser or live run. Merged is not published or deployed.
- Owner rule recorded this session: agents never run the full suite on PRs (AGENTS.md, DEVELOPMENT_WORKFLOW.md, TEST_PLAN.md, CLAUDE_CLI.md).

## 2026-10-20 — Roadmap 3.4 stale-while-revalidate read path (merged as PR #459)

- Squash-merged to `main` as `b09c9544cd96828a732fea04818729fc381cee0e` after the owner named PR #459. All four required workflows passed on exact head `44148af78a93a0a3be27a1f17ec6cc196e678bf6` (compile, test-and-build, container-smoke, validate-container).
- Behavior: `build_cached_discovery_list_response` takes an `on_stale` hook (personal list only); `discovery_refresh.revalidate_on_read` starts one daemon-thread rebuild when the stored snapshot is stale (`STALE_MAX_AGE_SECONDS`, 24 h) or has an invalid timestamp. Skips: missing snapshot, refill setting off, rebuild in flight, one-hour cooldown. The stored snapshot is served regardless; hook errors never reach the read. The rebuild is `_discovery_refresh_personal(20, origin="read")`, so the build lock, snapshot guard and 100-request budget apply unchanged.
- Also changed: `discovery_store` accepts refresh origin `read` (outcome table and pool diagnostic) and status `rejected` (`refresh_personal` already recorded it; the store refused it and the error was swallowed). A review finding was fixed: a failed thread start no longer leaves the cooldown timestamp set.
- `navidrome_server.py` stayed at 2649/2650 lines (collapsed `_discovery_refresh_all` to offset the hook).
- Tests: `tests/test_discovery_revalidate.py` (new) and two cases in `tests/test_recommendation_diagnostics.py`. Run for this PR, focused only (owner instruction: no full suite this session): revalidate, refresh, list payload, snapshot, scheduler refill gate, server size guard, dashboard/discovery routes, API injection, cold-start batch (via `discover -s tests -p`), diagnostics. All passed. The owner runs the full suite.
- Not done: no browser or live run; "refill run makes no more than 100 uncached requests" has no new test (no lookups added; existing budget tests apply); served-snapshot age and foreground-latency metrics are not exposed. Publishing and deployment remain paused.
- Next: roadmap 3.3 positive tag-query seed, handed off in `CLAUDE_CLI.md`.

## 2026-10-20 — Roadmap 3.4 refill on/off setting (merged as PR #458)

- Squash-merged to `main` as `7fb140e6d915ada98974d1b56002c03d4e5cfef0` after the owner named PR #458. All four required workflows passed on exact head `d72d650`.
- Setting: `automatic_refill_enabled` (`service_settings.py`), default `true`; absent or non-boolean stored values fall back to `true`. `GET/PUT /api/settings/automatic-refill` accepts only JSON booleans (`app/api/settings.py`).
- Gate: the hourly `_discovery_scheduler` passes an empty list to `refresh_stale_lists` when the setting is off, so no background cache reads or refreshes run. Foreground builds are unchanged. The toggle takes effect on the next hourly cycle; an in-flight refresh is not cancelled.
- Tests: `tests/test_discovery_scheduler_refill_gate.py` (4 tests running one real scheduler cycle), plus policy and route tests in `tests/test_service_settings.py` and `tests/test_settings_routes.py`. Mutation check: removing the gate fails the disabled-case test.
- Local full-suite run before merge: 1062 tests, one failure, the known macOS-only `test_acquisition_import` `/var` symlink case.
- Still open: the stale-while-revalidate read path (roadmap 3.4), recorded as the next task in `CLAUDE_CLI.md`.

## 2026-10-20 — Handoff: roadmap 3.4 refill on/off setting (docs only)

- PR #456 merged as `4680a187734dc05516ebdca639b8a003366aaeb2`. Its checks passed on head `7b0a3a0` before merge.
- Handoff: roadmap "Current state", the 3.3 status, and the 3.4 status are updated. `CLAUDE_CLI.md` names roadmap 3.4 (refill on/off setting, default on) as the next task. Its `app/api/**` and `app/main.py` scope needs owner confirmation before editing.
- Docs PR #457 was merged after `main` was merged into it. The two docs conflicts were resolved in favor of main's trimmed roadmap, with this handoff applied on top.

## 2026-10-20 — Roadmap 3.3 feedback signal (merged as PR #456)

- Task: roadmap 3.3, feedback as a bounded signal. Implemented in `recommendation_feedback.py`, wired through `prepare_ranking_inputs` (`recommendation_cooldown.py`) and the replay context validator (`recommendation_replay.py`); one server call-site line, with one blank line removed to stay at the 2650-line cap.
- Gate: `FEEDBACK_SIGNAL_ENABLED = True`, default-on, owner-approved 2026-10-20.
- Tests: `tests/test_recommendation_feedback.py` (14 unit tests) and `tests/test_recommendation_feedback_fixture.py` (3 controlled end-to-end tests through the real ranking and allocator). The fixture caught a bug where an expired artist dismissal still applied the shared-tag penalty; fixed by gating the dismissed-artist set on the negative window. Full suite: 1053 run, 1 failure, the known macOS `test_acquisition_import` case, confirmed to fail on clean `main` via stash.
- Merged: PR #456 squash-merged to `main` as `4680a187734dc05516ebdca639b8a003366aaeb2` after the owner named it.
- Not done: no tag-query seed; no live or private-capture evaluation.

## 2026-10-20 — Live stage-timing runs with per-stage keys (docs only)

- Merged: PR #454 squash-merged to `main` as `a5bba875dbec57fc5c98aba119b374f268bf1ef6` after the owner named it. All four required workflows passed on the exact head before merge.
- Handoff: `CLAUDE_CLI.md` now points the next session at roadmap 3.3 (feedback as a bounded signal).

- Task: owner-approved repeated live runs that report the PR #452 stage keys, as stated in `CLAUDE_CLI.md`. Results are in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`, section "Live stage-timing runs".
- Runs: all-flags cold and warm, batch-only cold and warm (one retry), breaker-only cold and warm. Fresh data directory per configuration; slskd disabled; aggregate counters only; no identities or credentials recorded.
- Findings: the all-flags speed-up is the batch path. Batch-only metadata resolution took about 1 s, against about 132 s for breaker-only. The breaker-only warm run's 100 recording lookups are consistent with the 100-per-run uncached budget (hypothesis; not directly measured).
- Failures: two batch runs got a non-JSON response on the listening-history call (one retried successfully). Not reproduced on the retry; cause not established. The ListenBrainz client was not changed.
- Not done: no code, flag, weight or budget change; no variance bound beyond single samples; the batch cold figure is one successful sample.
- Next: decide whether to repeat the batch cold run once the listening-history call is reliable, then a counter for `cache_known` in run metrics (needs its own PR).

## 2026-10-20 — Record PR #452 merge and Claude CLI handoff (docs only)

- Merge recorded: PR #452 squash-merged to `main` as `76030c0f70e59ebe05b2e10ca5fcfc6a4fc75bd9`, from exact head `856df1f6ed50353ee671c6b129d51e86a49b4ad7` (base `42b6d81`). All four required workflows succeeded on that head: `compile`, `test-and-build`, `container-smoke`, `validate-container` (validation-only; publishing paused).
- Change: merge SHA written into `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` (current state and the per-stage timers section) and this log. New `CLAUDE_CLI.md` at the repository root: a short handoff so Claude CLI can start the next roadmap task from GitHub alone.
- Not changed: no code, no tests, no settings, no flags, no live or Mac run.
- Next: the owner's go-ahead for a repeated timing run that reads the stage keys (see `CLAUDE_CLI.md`).

## 2026-10-20 — Per-stage run timers for candidate gathering (offline, no behavior change)

- Why: PR #451 timed gathering as one stage, so the flag-timing questions could not be attributed. The owner's priority is per-run time without added lookups.
- Change: `recommendation_run_metrics.add_stage_seconds` plus timers for `metadata_resolution`, `genre_prefetch`, `supplementary_tag_lane`, `replenishment`, and `genre_lookup` in `discovery_candidate_gathering.py`. Clock reads only.
- Tests: 2 added (stage keys reported per run; seconds accumulate). Focused tests: 11 OK. Full unit suite: 1039 tests OK (sandbox deps httpx, fastapi, mutagen installed).
- Merges recorded: PR #449 `c90e43b`, PR #450 `27bdcc2`, PR #451 `42b6d81` (exact head `a1d061b`, four checks green per the thread).
- Not done: no live or Mac run; four CI workflows on the new head not yet observed at time of writing.
- Next: a repeated all-flags timing run that reads these stage keys, when the owner approves a live run.

## 2026-10-19 — Persisted candidate resolution: cross-run tests (2.3, test and docs only)

- Finding: roadmap 2.3's default-path store already exists (`mb:recording:{mbid}`, 180-day TTL, written on every successful lookup). Ownership and eligibility run after the cache. No new store was built.
- Change: two offline tests in `tests/test_discovery_candidate_gathering.py` covering consecutive runs with overlapping CF output and an identical warm run (zero MusicBrainz calls). Test helper gained a `persist` option, off by default, so existing tests are unchanged.
- Deferred: batch-path persistence (needs its own namespace and an owner decision); measurement of cross-run CF repeat rate (not measured).
- Checks: gathering module 32 tests OK; full suite (`PYTHONPATH=tests:. python3 -m unittest <tests/test_*.py>`) 1023 tests OK; py_compile OK. Docker and CI workflows: see PR.

## 2026-10-19 — Last-known-good snapshot guard and read-time filter (3.4, branch)

- Task: roadmap 3.4, the next unfinished item after PR #444 on main. Confirmed by roadmap section 3.4 (3.1–3.3 not marked complete and 3.4 is the Phase 3 item the owner ranked next).
- Evidence: `refresh_personal` wrote any non-error build over the stored list, so an empty or smaller build could replace a good list. The hourly scheduler already refills stale lists (24-hour threshold).
- Change: `discovery_snapshot.py` (pure policy: replacement decision, read-time owned/duplicate filter, aggregate counts); optional `read_previous` guard in `discovery_refresh.refresh_personal`, wired in `navidrome_server.py`; tests in `tests/test_discovery_snapshot.py` (16).
- Tests: targeted suite 36 passed; full unit suite 1010 passed (after installing `requirements.txt`; earlier import errors were missing dependencies, not code failures).
- Limits: provider-failure count not yet produced; read-time filter not yet wired to the library predicate; no live measurement; PR not yet opened or merged.
- Publishing and deployment remain paused.

## 2026-10-19 — Supplementary tag lane early stop (flagged) and genre-check findings

- Task: add a default-off early stop to the supplementary MusicBrainz tag lane, and record the test-copy genre-check findings in the roadmap, status and log.
- Change: `TAG_LANE_EARLY_STOP_ENABLED` (default `False`) and `TAG_LANE_EXHAUSTION_THRESHOLD` (2) in `discovery_candidate_gathering.py`. Flag off keeps stop-at-first-exhaustion. Tests: `tests/test_discovery_tag_lane_early_stop.py` (7).
- Evidence (aggregate only, owner test copy): artist-tag endpoint 8 of 8 tagged, 109 of 151 tag names exact-match (0.72); breaker trip after 9 attempts with 0 genre requests after opening, but profile prefetch not gated (48 requests, all 429); all-flags repeats 62 to 133 s on, 299 s off in one run; A/B pair 80 s on, 299 s off, 10 recommendations each.
- Limits: single samples; one profile; the earlier 6-of-10 underfill is unexplained; no live run with the early-stop flag on.
- Open: flag defaults (owner decision); gate the profile genre prefetch with the breaker (not implemented); live early-stop measurement.
- Publishing and deployment remain paused.

## 2026-10-19 — Flag timing and variance check (test-only, docs)

- Task: record the Mac test-and-report runs on main `76ec40e` in the roadmap; no code or defaults changed.
- Evidence (aggregate only, fresh data directory per run): flags off 359.1 s and 237.0 s; batch only 211.5 s; title filter only 197.0 s; breaker only 206.1 s; all three on 46.3 s, 55.1 s, 51.4 s (count=10) and 148.7 s (count=20). Full table in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.
- Findings: breaker never tripped, so its effect is unmeasured; title filter had 0 drops; combined speed-up is unexplained; count=10 all-flags runs underfilled (6 or 10) with 7 to 12 eligible albums, count=20 filled to 20.
- Limits: single samples per variant; some eligible counts missing; ListenBrainz artist-tag endpoint unverified.
- Open: no default changes; next steps are a repeated all-flags run with per-stage breakdown, a breaker-trip run, and an endpoint shape check.

## 2026-10-19 — Batch lookup: title filter, flagged resolution, timing, genre-stage breaker (docs only)

- Task: record the batch-lookup work (PRs #429, #430, #431) and the timing and throttling results in the status docs and roadmap, correcting anything they contradicted.
- Merged changes, all default off: PR #429 (`f33a118`) title-marker filter; PR #430 (`ea383cc`) flagged batch resolution (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`); PR #431 (`b933d52`) genre-stage circuit breaker. Discogs ruled out.
- Evidence (aggregate only): title filter flagged 1 of 35 sample release groups. Timing pair at `ea383cc`, one run per mode: 332.5 s with flags off (214 uncached requests) and 105.7 s with them on (85 requests); eligible unowned albums 12 in both. Repeat run with flags on: 254 s, 83 artist-genre attempts for 55 artists, 33 throttled (429 or 5xx).
- Corrections made: the roadmap said the batch wire format was unchecked and the saving was an estimate; both now reflect the live-response check and the measured pair.
- Limits: single samples; one profile; no live run on `b933d52`. Breaker and batch flags are unchanged by default.
- Open decision: whether to enable the breaker and batch flags by default (changes output).
- Parked: the Last.fm line stays parked; no quality test is started.
- Publishing and deployment remain paused.

## 2026-10-19 — Last.fm source: capped check and holdout result (docs only)

- Task: owner asked to record Last.fm as a future recommendation-source setting option and move on with the roadmap.
- Evidence (aggregates only): capped path about 40 s, 95 unowned candidates from 15 artists; positive control passed (31 of 31 known-owned albums flagged); holdout of 70 listens after 2026-10-18 15:41 UTC gave 0 artist hits for this path versus 3 of 27 for the frozen CF side. Uncapped path 273 to 313 s.
- Change: documentation only, in docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md. No code, weights, windows, eligibility, ownership, duplicate rules, or budgets changed.
- Limits: one holdout of 70 listens, one profile, 4 of 20 browses returned 503; quality unmeasured at useful sample sizes. Publishing and deployment remain paused.

## 2026-10-19 — Supplementary tag lane: profile genre prefetch (draft PR)

- Task: decide whether tag selection for the supplementary lane should read artist genres after the genre-lookup stage, since the lane ran before that stage wrote the cache (the cause of the cold-cache zero in the PR #411 live run).
- Measurement: offline, through the real gathering path on a synthetic fixture with providers stubbed. Cold cache with the existing order planned 0 queries; warm cache planned 8. A full reorder would match warm exactly but adds up to about 60 uncached MusicBrainz lookups per first run, so it was not chosen.
- Change: prefetch genres for the top 15 profile artists before the lane. These artists are already in the genre stage's lookup set, so total calls per run are unchanged. Cold cache on the fixture now plans 6 queries (all profile), eligible unowned 22 (warm: 8 queries, 28 eligible). Exploration parity is not restored.
- Tests: `tests/test_discovery_genre_prefetch.py`, three synthetic cases; the two cold-cache cases fail without the change. Full unit suite run locally: 923 tests OK. PR #419 merged (squash) as `51f6e9877575a11dd5e0314cd23b2b197baca491` from exact head `9f045e33e85334247b55fc230e4152a3d3b3b620`; compile, test-and-build, container-smoke, and validate-container passed on that head.
- Limits: synthetic fixture only; no live run; tag yield not measured. Weights, windows, eligibility, ownership, and budgets are unchanged. Publishing and deployment remain paused.
- Next action: owner go-ahead for a live cold-cache run; decide separately whether candidate-artist prefetch is worth its extra lookups.

## 2026-10-19 — PR #411 warm-cache aggregate run (no code change)

- Task: rerun the #411 live measurement with a warm metadata cache, after PR #414 added aggregate tag-lane counters.
- Run: one pass at `963f8f5` (main with #411 and #414), in a fresh directory holding only a copy of the metadata cache. No listening data or ownership state was copied; the directory was deleted afterward. The owner approved the single cache-file copy from the prior data directory.
- Replenishment: shortlist target 10; eligible unowned albums 62 before and after. The gate stayed closed (not triggered), so 0 extra queries were planned, attempted, or added. The replenishment step is therefore not exercised by this run.
- Tag lane: 100 listens, 89 with an artist MBID. Profile: 19 artist MBIDs; 15 of the top 15 were cache hits, yielding 92 tags. Candidate pool: 23 artists considered, 7 cache hits, 106 tags. Supplementary: 8 queries planned and attempted.
- Interpretation: the earlier cold-cache zero (PR #411 live run at `76e3ac2`) came from an empty metadata cache, because the genre cache is written after tag selection. It is not a selection bug. With a warm cache, the tag lane has inputs.
- Limits: one run and one profile. Replenishment's effect on shortlist fill remains unmeasured, because this profile had no shortfall to replenish.
- No code, weights, windows, eligibility, ownership checks, or provider budget changed. Publishing and deployment remain paused.
- Next action: measure replenishment on a warm cache under a real shortfall, with a profile or fixture that leaves fewer than 10 eligible unowned albums. Use an offline replay where possible.

---

## 2026-10-19 — PR #411 replenishment live aggregate measurement (no code change)

- Task: measure whether the gated supplementary replenishment in PR #411 (merged at `76e3ac2`) adds eligible unowned candidates on a live run, using aggregate output only.
- Run: one live pass at `76e3ac2`, on the owner's isolated test copy, with a fresh empty data directory that was deleted afterward. Config loaded through the app's own loader. Earlier attempts failed before candidate gathering because of a malformed line in the test copy's env file; the owner fixed it, and only the successful run's counts are recorded here.
- Aggregate results: shortlist target 10. Eligible unowned albums 7 before and 7 after. Replenishment gate triggered (7 < 10). Extra queries planned 0, attempted 0. Extra candidates added 0. Base supplementary lane also issued 0 queries. CF supplied 21 albums from 10 artists; top artist album shares 0.333, 0.190, 0.143, 0.048, 0.048. No failure classes reported.
- Interpretation: the gate fired, but there were no tag queries to extend, so #411 added no supply in this run. Code trace (read-only): `select_supplementary_tag_queries` takes its tags only from the cached `mb:artist-genres:*` entries. Those entries are written later in the same run, by the genre-lookup stage after tag selection. A fresh, empty data directory has no cache, so both the base lane and the replenishment pass select nothing by construction. This run therefore does not measure replenishment on a warm cache, which is the state the feature targets. The zero result is a consequence of the cold-start setup, and it also means a cold first run never fills the tag lane.
- Limits: one run, one profile, one fresh data directory. The fresh directory has no prior ownership state beyond what Navidrome reports at run time. No identities, listening data, raw tags, provider URLs, or exception messages were recorded.
- No weights, windows, eligibility, ownership checks, or per-run budget changed. Publishing and deployment remain paused.
- Next action: rerun on a warm metadata cache, which requires the owner to approve the data directory for that run. Separately, decide whether tag selection should read the genre cache after the genre-lookup stage, which would be a code change.

---

## 2026-10-19 — P2 capture "FileExistsError" warning fix (offline; no live capture)

- Task: the owner's snapshot A and B runs logged `capture failed (FileExistsError)` although both captures were written intact on the first attempt. Established from code before changing anything.
- Cause: `recommend_new_music` reads the process-wide `LIBRARIAN_RECOMMENDATION_CAPTURE_PATH`. `/api/recommendations` calls it directly, outside the personal-refresh lock, so two overlapping runs can carry the same one-shot path. The first run wrote the capture. The second hit the refuse-to-overwrite check (`_check_private_path`, `O_EXCL`) and `write_capture_safely` logged the warning. No retry or third writer exists.
- Fix: `write_capture_safely` claims each capture path once per process under a lock. Later overlapping runs skip the write without a warning. Capture permissions (dir 700, file 600), the outside-repository check, and `write_capture`'s immutability refusal are unchanged.
- Tests: `tests/test_recommendation_replay_capture.py::test_second_run_sharing_capture_path_does_not_warn_or_overwrite`, synthetic and deterministic. It failed before the fix (warning logged) and passes after. Capture-module tests: 11 OK. Full unit suite: 899 OK. Syntax compile, `scripts/check_server_size.py`, and `scripts/check_app_legacy_imports.py` pass.
- Environment note: running the capture tests needed `httpx` installed from `requirements.txt`; without it three tests in that module error at import time, unrelated to this change.
- Not verified: the owner's logs were not inspected, so the concurrency explanation is inferred from code, not confirmed against a run. The four required CI workflows are pending on the PR head. No merge and no publication.
- Next: owner confirms whether the warning coincided with an overlapping `/api/recommendations` request or a manual/scheduled refresh.

---

## 2026-10-19 — P5 supplementary tag-search bounded 503 retry (offline; no live capture)

- Task: roadmap P5 in docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md. Decision from code inspection: P1 already records per-query supplementary yield (attempted, zero-yield, failed, not attempted), so the gap was not measurement. The gap was that the MusicBrainz release-group tag search made a single request and called `raise_for_status()`, so one 503 dropped that query. The P4 retry covered artist-genre lookups only. The frozen capture's two tag searches returned 503 and produced no candidates.
- Behavior: each tag search now gets one retry (one 2 s backoff) on 429/500/502/503/504, reusing `_get_with_bounded_retry` with `attempts=2`. Failures are not cached. If a query still returns a retryable status after its retry, the lane stops and sends no further tag searches. MusicBrainz documents that over-limit requests get 503 until the rate drops, so continuing to send requests would prolong the decline. Worst-case added time is one 2 s backoff plus one request per run.
- Unchanged: ranking, weights, ownership, duplicate-identity handling, release eligibility, the 1.1 s request spacing, the per-query 5-candidate and 60-candidate caps, and the supplementary cache TTL.
- Tests: `tests/test_discovery_candidate_gathering.py` adds synthetic cases: one tag-search retry recovers from 503; retry budget returns the last status after two attempts; a persistent 503 stops the lane after the first query's two attempts; a transient 503 then 200 still adds candidates. No live captures or private identities were used.
- Limits: the lane-stop threshold is a judgment call from MusicBrainz's documented behavior, not measured yield. The frozen capture holds no per-query yield, so the effect on real supply is unmeasured. The lane still runs only when profile genres are cached.
- Full unit suite: 840 tests OK. `scripts/check_server_size.py` and `scripts/check_app_legacy_imports.py` pass.
- Next: measure supplementary yield with an owner-authorized, identity-free aggregate run on the next capture.

---

## 2026-10-19 — P3 bounded CF paging (offline; no live capture)

- Task: roadmap P3. The CF recording endpoint accepts `offset`; the gathering path requested only `count=100`.
- Behavior: up to `CF_MAX_PAGES = 2` ListenBrainz pages (offsets 0 and 100), deduplicated by MBID. Paging stops on a short page. A failed first page keeps the legacy error contract. A failed second page stops paging, keeps page 1, and reports only the bounded error class.
- Budget: uncached MusicBrainz resolutions are capped at `CF_MAX_UNCACHED_RESOLUTIONS = 100` per run, the same worst case as the old single page. Cache-known recordings cost no call. Owner lowered the cap from 200 because about 110 s extra per cold run was too long. With a cold cache, page 2 therefore gets no uncached resolutions; it adds recordings only when they are cache-known.
- Artist cap: `CF_ARTIST_RESOLUTION_CAP = 10` skips cache-known recordings of an artist already resolved 10 times, before any provider call. Limit: the CF endpoint returns no artist, so uncached recordings must still be resolved to learn their artist. The cap cannot skip them.
- Diagnostics: `candidate_supply.cf_paging` reports pages requested and fetched, page-failure class, artist-cap skips, uncached resolution calls and budget, and budget skips. All are counts or bounded labels.
- Tests: `tests/test_discovery_candidate_gathering.py`, 7 new synthetic cases: offset paging and two-page budget; short page stops; cross-page MBID dedupe; second-page failure; first-page failure keeps legacy contract; artist cap before any call; uncached budget bounds MB calls.
- Offline replay on the frozen capture still reproduces the P1 aggregates (19 albums, 12 owned, 5 selected, 2 artist-cap rejections, 0 identity duplicates). The capture holds only page 1 and its MusicBrainz tape, so the after-supply effect of page 2 cannot be measured offline. Do not claim a supply gain from this PR.
- Full unit suite: 809 tests OK. Syntax compile, `scripts/check_server_size.py`, and `scripts/check_app_legacy_imports.py` pass. CI and merge state: pending; draft PR, no merge.
- Next: owner decision on the cold-cache budget. A supply measurement needs a page-2 tape, which requires an owner-authorized capture.

---

## 2026-10-19 — P4 genre-lookup bounded 503 retry (branch fix/genre-lookup-retry)

- Task: roadmap P4 in docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md. The artist-genre lookup (`mb:artist-genres`) made one MusicBrainz request per artist and recorded any 429/5xx as a failure. It now uses the same bounded retry shape as recording lookups: up to 3 attempts, sleeps of 2 s and 4 s, retry only on 429/500/502/503/504.
- Caching is unchanged: failures are recorded and not written to the metadata cache, so a later run retries the artist.
- Tests: `tests/test_discovery_candidate_gathering.py` adds synthetic cases for first-attempt success, 503 then success, retry exhaustion (bounded attempts, last status returned), and non-retryable 404 without retry. Full unit suite: 816 tests OK locally. `py_compile` on all tracked Python files and the legacy server-size guard passed.
- Limits: the frozen replay does not emit genre or unclassified metrics, so the acceptance criterion "fewer unclassified candidates in offline replay" is not measured here. The change only affects live runs. Worst-case provider calls for one artist rise from 1 to 3, bounded by the existing 75-artist cap; retry sleeps add up to 6 s per persistently failing artist.
- Not run: CI on the PR head, live provider checks, and any publication or deployment. No merge.

---

---

## 2026-10-18 — P1 candidate-supply diagnostics (aggregate only, no behavior change)

- Task: roadmap P1 from the 2026-10-18 revision (PR #380, merged as `63e5e2a`). Added aggregate-only supply diagnostics at the CF gathering boundary: CF recording outcomes (returned, resolved, failed by bounded error class), distinct recording artists and top-two share, resolved albums per artist (top-N shares), supplementary query yield (attempted, zero-yield, failed, not attempted), and stage counts for owned, unowned unique before/after dedupe, and before/after artist cap.
- Implementation: new `discovery_candidate_supply.py` (pure summarizers; exception types outside an allowlist collapse to `other`). `discovery_candidate_gathering.py` records per-recording and per-query outcomes in memory and returns a `candidate_supply` aggregate. Persisted pool diagnostics gain a `candidate_supply` block; public API responses are unchanged. The offline replay and profile comparison report the same aggregates from the capture without provider calls.
- Behavior: no change to candidate selection, ranking, allocation, ownership, eligibility, provider calls, or cache behavior. Gathering makes the same calls in the same order.
- Reproduction from the owner's frozen schema-v2 capture (aggregate output only): 100 of 100 CF recordings resolved; 92 of 100 from the top two artists; 19 CF albums from 8 artists; all 19 candidates from ListenBrainz CF; 12 already owned; 5 selected. Current replay also shows 2 `duplicate_candidate` decisions.
- Correction to the handoff: the 2 `duplicate_candidate` rows are not duplicate supply identities (zero duplicate identities among the 19 candidates under the allocator's identity key). They are unowned albums by an artist already selected, which the allocator relabels as `duplicate_candidate` when a later phase re-visits them. The stage summary counts them as artist-cap rejections (2) and reports duplicate identity rows as 0.
- Replay caveat (pre-existing, also on `main` at `63e5e2a`): `recommendation_replay.py` reports `reproduced: false` for this capture. Recommendations match (5/5, same scores); the stored expected output predates the allocator fields (`allocator_*`) and its stored decisions differ from current code (10 `recent_genre_cap_reached` vs current 2 `duplicate_candidate`). Not changed here.
- Tests: `tests/test_discovery_candidate_supply.py` (13 synthetic cases: empty pool, single-artist pool, provider-failure pool with bounded classes, album shares, stage counts, artist cap relabelled as duplicate, supplementary yield, tape reconstruction, no identities in offline report, gathering integration). Full unit suite: 809 tests passed locally. CI and merge state: pending; no merge.
- Limits: v2 captures do not store per-query supplementary yield, so the offline report states that field is unavailable. The figures come from one frozen fixture and do not show whether a change would improve future-listen outcomes.
- Next: P3 bounded CF paging, using this aggregate to judge whether replenishment adds eligible unique unowned albums.

---

## 2026-10-18 — PR #370 merged: recommendation shortlist underfill diagnostics

- PR #370 squash-merged as `6256fd375db0d9c93870f78b632b60390c9ee31f` from exact tested head `e8fac4e737ce75e11210c964af5a50e4ca9bdede`.
- All four required workflows passed on that exact PR head: Python syntax/acquisition safety run `39173185205`; Docker packaging/full suite/build run `39173185161` (790 tests); container runtime smoke run `39173185160`; validation-only multi-architecture image validation run `39173185157` (publishing paused).
- The owner-side private schema-v2 replay resolved 19 rows per profile: 12 already-owned, 2 duplicate identities, 5 selected. Final fallback was entered; checked count was 14/60. The underfill on this frozen snapshot is candidate supply after ownership and duplicate protections, not check-budget exhaustion. The earlier family-cap outcomes were stale diagnostic attribution. No ranking/selection policy or ownership protection changed.
- The top-five set remained identical across profiles (Jaccard 1.0) despite rank movement; this is not recommendation-quality or future-listen evidence. Private capture/history and candidate identities remain outside GitHub. No image publication, deployment, or runtime verification occurred.
- Next action: separately investigate candidate supply using aggregate eligibility/source counts and deterministic bounded-replenishment tests while preserving ownership, duplicate identity, release-type filtering, provider limits, and deterministic replay. Publishing remains paused.

---

## 2026-10-18 — Owner replay explains five-item recommendation shortlist (PR #370)

- Owner reran the private schema-v2 comparison against the corrected diagnostic source. Both profile windows resolved 19 candidates and reported 12 `already_owned`, 2 `duplicate_candidate`, and 5 `selected`; the counts account for all 19 rows. Final fallback was entered; checked count was 14/60.
- This explains the underfill on this frozen snapshot: only five eligible unique unowned candidates remained after ownership and duplicate protections. The check budget was not exhausted. The previous 10 recent-family-cap rejections were stale diagnostic attribution; the corrected output now reports owned/duplicate/selected outcomes.
- Both profiles still return the same five recommendations (Jaccard 1.0), with two positions changing and broader candidate rank movement. This establishes ranking responsiveness, but not top-five membership responsiveness, quality, or future-listen outcomes.
- No private capture, history, candidate identity, or per-candidate score was added to GitHub. No weights, ownership rules, or selection policy were changed.
- Next: keep PR #370 scoped to aggregate diagnostics; after its final review, investigate candidate supply separately with aggregate eligibility/source counts and deterministic bounded-replenishment tests. Preserve all safety constraints and provider limits. Publishing/deployment remain paused.

---

## 2026-10-18 — PR #370 underfill diagnostics refined after owner replay

- Owner-side private schema-v2 comparison on PR #370 source reported 5 recommendations from 10 requested, 19 resolved candidates, final fallback entered with 19 attempts, 14 checked candidates against the 60-check budget, and decisions reported as 4 already-owned, 10 recent-family-cap-reached, and 5 selected. Both profiles showed the same aggregate outcome; capture/history and identity-bearing rows remain private.
- Code inspection found that the final fallback explicitly allows over the recent-family cap, so retaining 10 final family-cap statuses is inconsistent with the pass sequence. Duplicate identity was checked after the family cap; a duplicate could retain an earlier cap decision through `decisions.setdefault`. PR #370 now checks normalized identity before soft caps and adds a deterministic regression. This changes diagnostic attribution, not selection behavior.
- The check budget was not reached. The true reason the unique shortlist stops at five is not yet established; duplicate identities and artist-level eligibility may account for some remaining rows. No ranking weights, ownership checks, or selection policy were changed.
- The first diagnostic-precedence attempt at `43411aa29c63cece935475d0328a1d1d0bad4f49` failed two tests: an incorrect expected selection order and an exact-owned candidate diagnostic that was masked as duplicate. Both were fixed. Exact code head `277560ab0185d8b1beb6beafdb4a055b316e3a3b` passed all four required workflows: Python syntax `39172112667`, Docker packaging/full suite/build `39172112675` (777 tests), container runtime smoke `39172112640`, and validation-only multi-architecture validation `39172112650` (publishing paused).
- Next: rerun the private evaluator against the corrected PR source and share only aggregate diagnostics. Publishing/deployment remain paused.

---

## 2026-10-18 — PR #353 merged; recommendation chronology findings recorded

- PR #353 (“ui: Redesign Phase 1 foundations”) squash-merged at `255f1ed62e4ce3d3bc85dea478f214e10a7a8d22` from exact final PR head `ed6c18a9e4ca6abd43d41911dc4ce920c5ab1c84`.
- All four required workflows passed on that exact head: `compile` run `39148156315`; `test-and-build` run `39148156413`; `container-smoke` run `39148156254`; `validate-container` run `39148156294`. PR #353 reports 715 unit tests passing and partial rendered browser checks at five viewport widths. The full manual keyboard/screen-reader walkthrough and populated real-library states were not verified in this session; do not describe the UI verification as complete. No publication, deployment, or production-runtime verification.
- Recommendation-history audit used public `abucalip/reports/listenbrainz-history.json` (407 timestamped listens across about 13.36 days). First rolling five-day window: 138 listens, 36 artist names, 37 releases. Last rolling five-day window: 132 listens, 64 artist names, 77 releases. Artist-name overlap was 8 (Jaccard about 0.087). These are descriptive profile-change facts, not quality scores.
- The available `baseline-20261018-v2.json` was captured after both windows (2026-10-18 15:41:26Z), so it is not a valid pre-window recommendation snapshot and there are no later listens in the history. Do not compute future-listen hit-rate or nDCG from this pair or allow temporal leakage.
- A small familiarity-multiplier calculation held candidate base scores fixed and changed only windowed artist counts; it illustrated component sensitivity but was not a full engine replay or final-rank result. No engine replay, tests, live provider calls, or application changes occurred in this session.
- Durable recommendations are in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`: next, build a deterministic offline responsiveness replay with identical frozen non-profile inputs and separate first/last-window profiles; assess ordered-list/score changes, top-k overlap, novelty, diversity, categories and eligibility. Keep this separate from any later T-to-future-listens observational evaluation. Librarian recommends music to acquire and does not control future listening, so future listens are independent evidence, not a causal success target.
- Next action: resolve the private capture's deterministic replay mismatch, then create a trustworthy frozen snapshot/replay tape before running the actual engine on both history profiles. Keep private identity-bearing artifacts private; publishing remains paused.

## 2026-10-18 — PR #352 merged: redesign Phase 0 baseline and owner decisions

- PR #352 squash-merged at `40c551b831f782de2f3000b844b7491689bea9b8` from exact final PR head `47791ffe638d80f1ecaf97d2c48648354710cc18`.
- All four required workflows passed on that exact head: Python syntax run 1733 (`39142873499`); Docker packaging/full unit suite/build run 1641 (`39142873452`); container runtime smoke run 1450 (`39142873440`); validation-only multi-architecture image validation run 1494 (`39142873438`, publishing paused).
- Documentation-only merge: records the Phase 0 baseline, owner decisions D1–D6, contrast remeasurement, colour-vision findings, and roadmap status. No application code changed.
- Verification caveats remain: Chromium 141 on Linux only; Google Fonts and third-party modal assets were blocked, so typography and some performance results are incomplete; populated states were reconstructed; no real-library Get action, keyboard walkthrough, screen-reader pass, or manual browser verification of a UI change. Existing backend issue B1 (ListenBrainz settings endpoint returns 502 when username is unset) and B2 (album modal third-party images) remain documented, untouched.
- Publishing, deployment, and runtime verification were not performed. Publishing remains paused.
- Next UI action: start Phase 1 (tokens, self-hosted fonts, icon sprite) from current GitHub `main`. The recommendation-engine evaluation track remains separate: a valid time-separated recommendation snapshot and independent future listening history have not yet been established; do not infer quality from deterministic replay.

---

## 2026-10-18 — Private schema-v2 recommendation baseline replay verified

- PR #350 merged as `dc3e5a3a8ea704bbc66aa1d1b43dc4e9594fd2be`. The owner captured a fresh schema-v2 fixture in the isolated PR #350 test environment and ran the replay script against the fixture's declared source revision.
- Replay reported `reproduced: true`: 5 expected recommendations and 5 actual recommendations. The comparison covered all stable output fields except volatile pool diagnostics and Last.fm error state.
- Replay consumed 19 captured Last.fm responses, used zero network providers, replayed zero provider events, and retained 225 provider events as provenance only. The fixture remains outside GitHub; no recommendation identities, listening history, library contents, or provider payloads were committed.
- This validates deterministic replay for this one frozen capture only. It does not measure recommendation relevance, future-listen hit rate, or responsiveness to listening changes. The prior schema-v1 fixture remains unchanged.
- No application code changed and no new tests were run in this capture/replay session; this is owner-run isolated-environment verification. PR #350's four required CI workflows had passed on its exact final PR head `0b69d0e7c42fd621ee903a8becf7791293a35d46`. Publishing, deployment, and production-runtime verification remain unclaimed.
- Next action: establish a valid time-separated snapshot/listening-history pair, then design an offline chronological evaluation with explicit limitations. Do not infer quality from successful replay.

---

## 2026-10-18 — Deterministic recommendation replay contract

- PR #350 (`fix/deterministic-recommendation-replay`) implements snapshot-authoritative replay, frozen ranking context (timestamp/history/diversity), and preservation of raw plus weighted play-count maps. Provider events are provenance only; Last.fm calls remain strict and fully consumed. Capture schema is v2; schema-v1 captures fail explicitly and require recapture.
- The private `baseline-20261018.json` was not copied into GitHub and remains unchanged/unsupported for deterministic replay because it is schema v1. No private listening/library/provider data was committed.
- All four required workflows passed on exact PR head `0b69d0e7c42fd621ee903a8becf7791293a35d46`: Python syntax run 1723 (`39138710922`); Docker packaging/full unit suite/build run 1631 (`39138710645`, 709 tests); container runtime smoke run 1440 (`39138710718`); validation-only multi-architecture image validation run 1484 (`39138710654`, publishing paused). Initial size-ratchet failure on `b8389454726f37101a1e26d41f46410c0c4dd652` was fixed by moving ranking-input preparation into `recommendation_cooldown.py`; the server remains at the 2,650-line limit.
- This documentation-only follow-up will trigger the same four workflows on its resulting PR head. PR remains open/unmerged; no publication, deployment, or production runtime verification occurred.
- Next action: verify all four workflows on the final PR head, then create a fresh private schema-v2 capture and replay it against its declared source revision before resuming chronological recommendation evaluation.

---

## 2026-10-18 — Private recommendation capture replay audit

- Audited the new private capture `baseline-20261018.json` against its declared source revision `4c2a0f09ebbbe374cf93049d17d4c3265fc5d589` (PR #342 source). The capture remains outside GitHub; no personal listening/library/provider data or identity-bearing comparison output was added to the repository.
- The offline replay consumed all 207 provider events and 40 Last.fm responses with zero live provider calls, and generated 10 recommendations versus 10 expected. Replay did **not** reproduce the stable output.
- A privacy-safe comparison found only `recommendations` and `debug_all_candidates` differed among stable output fields. The expected and actual recommendation counts both equal 10, and both debug candidate lists contain 59 rows, but the recommendation identity sets and order differ.
- Interpretation is unresolved: equal candidate counts do not establish whether ranking, eligibility, allocation, or incomplete replay inputs caused the mismatch. Do not treat this capture as a validated deterministic replay fixture or use it for quality conclusions until the discrepancy is investigated.
- No code changes, tests, CI runs, merges, publishing, or deployment occurred in this audit session. Existing private capture was not changed.
- Next action: inspect the replay harness and recommendation implementation at the exact captured GitHub revision to locate the reproducibility gap before attempting chronological future-listen evaluation.

---

## 2026-10-18 — Cross-pool recommendation MMR merged

- PR #347 merged as `9ace84947c13f2549fe0669b6a0c1a30af4c2349`; final PR head was `5ae39d5cdc0fb7abad2036d30ac1aa0a6ae5780f`.
- All four required workflows passed on the exact final PR head: Python syntax run 1710, Docker packaging/full unit suite/build run 1618 (706 tests passed), container runtime smoke run 1427, and validation-only multi-architecture image validation run 1471. Publishing remains paused.
- Added cross-pool deterministic MMR tests and capped the diversity mapping at lambda 0.75 for settings 75–100. Synthetic correctness checks do not establish future-listen quality or broad calibration.
- Settings UI remains blocked; no private fixture rerun, image publication, deployment, or production runtime verification was performed.
- Next action: collect/review broader recommendation-quality evidence before deciding whether diversity-setting UI calibration can proceed.

---

## 2026-10-18 — Cross-pool recommendation MMR verification (PR pending)

- Added deterministic tests using two deliberately different pools: one with a large score outlier and a close-tag cluster; another with a larger pool, tied ranks, and sparse tags. Tests check repeatability, shortlist size, unique artists, and rank-order invariance under score rescaling.
- Changed the backend 0–100 diversity-setting mapping to ramp linearly from λ=0 at setting 0 to λ=0.75 at setting 75, then saturate at λ=0.75 through setting 100. This conservative piecewise mapping follows the existing single-pool provisional gate (settings 0–75 passed; 80–100 failed) without claiming cross-pool or future-listen quality calibration.
- Updated `docs/DIVERSITY_SETTING_ROADMAP.md` and `docs/PROJECT_STATUS.md`. Settings UI remains blocked. No private fixture was rerun or committed; no live capture, publishing, deployment, or production-runtime verification.
- Code head `2bcecb50e09fb6864f97100c2e093b5022226a94` passed all four required workflows: Python syntax run `1708` (`39128352041`), Docker packaging/full unit suite/build run `1616` (`39128352047`, 706 tests passed), container runtime smoke run `1425` (`39128352031`), and validation-only multi-architecture image validation run `1469` (`39128352038`, publishing paused). The documentation closeout commit changes the PR head, so rerun all four required workflows against that exact final head before merge. Merge and release/deployment state remain pending.

---

## 2026-10-18 — Identity-free diversity rollout-gate evaluation

- The owner approved applying the provisional relevance/category thresholds to the existing private frozen fixture. No new capture was collected; the dismissed 35-combination/floor reproduction was not rerun.
- Found and fixed an evaluator schema mismatch in PR #345: captured `debug_all_candidates` rows use `assigned_category`, but the evaluator previously ignored that field and silently reported `unknown` category metrics. Added a synthetic regression test. PR #345 merged at `490afbaca5ed48cfbe8c78a6c5622cf9e6a0de04` from exact final PR head `80f6fb881e0da32fa0088153eca374e3c21cf416`.
- All four required workflows passed on that exact head: Python syntax `39126978342`, Docker packaging/full unit suite/build `39126978446` (704 tests passed), container runtime smoke `39126978284`, and validation-only multi-architecture image validation `39126978293` (publishing paused).
- Offline identity-free evaluation used the existing schema-v1 capture (captured source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`; fixture SHA-256 `d74877fd8635cfbd390a66f338389a3c8d91aa27c10ad10cc11e78b10182eb21`; payload SHA-256 `5dc522d622ada3bbe3fc12a2bf674b05b1345c7a02b9d67bed20b62549368d8e`). It validated the checksum/schema, used 83 gathered albums, 1,733 library albums, 66 scored candidates, 17 rejected rows, and 10 baseline recommendations. The sweep evaluated all 21 settings from 0–100 in increments of 5 with relevance floor fixed at 0; zero network providers and no provider-tape replay.
- Baseline categories were adjacent 4, adventurous 3, cross-genre 3; baseline normalized tag coverage was 72 and no baseline recommendation was untagged. All 21 settings returned 10 eligible candidates, 10 unique artists, no duplicate non-empty artist keys, deterministic repeated selections, and zero untagged selections/promotions.
- Settings 0–10: similarity 0.10440, 7/10 retained, 100.00% mean raw-score retention, category mix 40/30/30%. Setting 15: similarity 0.06719, 8/10 retained, 91.80% retention, mix 50/20/30%. Settings 20–75: similarity 0.06275, 7/10 retained, 91.79% retention, mix 50/20/30%. Settings 80–85: 81.14% raw-score retention and mix 60/20/20% (+20pp adjacent concentration); settings 90–100 also retain only 6/10 baseline items, with setting 100 retaining 72.17% of baseline raw score.
- Under the provisional per-setting gate, settings 0–75 pass and settings 80–100 fail. The result supports retaining 75 as a provisional effective cap, not approving a production mapping: the result is one frozen candidate pool, not future-listen hit-rate/nDCG or cross-pool evidence. The raw fixture and identity-bearing report remain private and are not committed.
- Publishing, deployment, and production-runtime verification remain unperformed. Settings UI stays blocked.
- Next action: add deterministic cross-pool tests for rank-normalized MMR and review a slider mapping consistent with the measured cap before considering UI work.

---

## 2026-10-18 — Identity-free recommendation-diversity sweep

- Evaluated the existing private frozen fixture offline at all 21 penalty values from 0.00 to 1.00 in 0.05 increments, with relevance floor fixed at 0. The capture schema/checksum validated. No provider tape was replayed, zero network providers were used, and no fixture or identity-bearing report was committed.
- Fixture aggregates: 83 gathered albums, 1,733 library albums, 66 scored candidates, 17 rejected rows under the evaluator's explicit hard-rejection/missing-score rules, and 10 baseline recommendations. All settings returned 10 candidates from the evaluator's rankable pool, 10 unique artists, and deterministic repeated selections; no selected candidate lacked tags in this capture.
- Identity-free curve: setting 0 similarity 0.1044, 7/10 baseline items retained, baseline relevance-score retention 85.6%. Settings 5–15: similarity 0.1016, 6/10 retained, baseline score retention 80.6%. Settings 20–70: similarity 0.1007, 7/10 retained, baseline score retention 85.5%. Settings 75–100: similarity 0.0591, 7/10 retained, baseline score retention 85.5%. Mean selected raw discovery score at 0.75 is 91.72% of setting 0; settings above 0.75 showed no additional measured benefit.
- Provisional recommendation: cap the effective penalty at 0.75; do not present a linear 0–1 slider as evidence-calibrated. Candidate guardrail for explicit review: at least 90% mean selected raw score versus setting 0 and at least 7/10 baseline items retained. These single-fixture metrics are not future-listen hit-rate/nDCG or broad quality evidence.
- Updated `docs/DIVERSITY_SETTING_ROADMAP.md` with the measured curve, distinctions between relevance metrics, provisional mapping/cap and review gate. Updated `docs/PROJECT_STATUS.md`; settings UI remains blocked pending normalization/pool stability, missing-tag neutrality, and final-shortlist guardrails.
- Private fixture and identity-bearing report remain local/private. The dismissed 35-combination/floor sweep was not rerun; no new capture, provider call, code behavior change, publishing, or deployment.
- Next action: implement rank-based relevance normalization and cross-pool stability tests, then address missing-tag neutrality and final-shortlist quality/category guardrails before any UI work.

---
## 2026-10-18 — Recommendation batch history persistence merged (PR #329)

- Branch: `feat/recommendation-batch-history`, based on main commit `547ea225b47c97a8f762f1d8d17d70118b31a643`.
- PR #329 merged at `85a94f2d66aefc0c1f130d4440546e7135d4e8d7` from exact tested PR head `613fd85715eaedc69f2375daf3cb6da6833c63bb`.
- Inspection found `discovery_store.py` kept only the current payload for each list and one latest pool diagnostic; no ranked recommendation-batch history was retained.
- Added bounded history recording to the same SQLite transaction as a successfully written `personal` list. Each row contains only a SHA-256 hash of normalized artist/album identity, generation timestamp, and rank. Raw artist/album labels are not stored in the history table. Retention is capped at 30 days and 2,000 rows; only the top 20 ranked entries per stored batch are recorded.
- Added read access to recent hashed history and regression tests for hashed identity storage, rank ordering, retention-window filtering, future-row exclusion, isolation from non-personal lists, and the row cap.
- All four required workflows passed on exact PR head `613fd85715eaedc69f2375daf3cb6da6833c63bb`: Python syntax `1650` (run `39080590034`), Docker packaging/full unit suite/build `1558` (run `39080590036`, 659 tests passed), container runtime smoke `1367` (run `39080590039`), and validation-only multi-architecture image validation `1411` (run `39080590047`, publishing paused).
- Ranking/candidate ordering is unchanged; no cooldown is active. No local tests were run in this GitHub-only session. No publish, deployment, or runtime verification.
- Next action: implement a separately reviewed, measured soft cooldown using this history; keep the Recommendation diversity settings UI with the coordinated frontend owner.

---

## 2026-10-18 — Backend recommendation-diversity contract and MMR integration merged

- PR #326 merged at `ef8173a4ce47b0b4b1ec72fc567377dbd0cf1dd0` from exact final PR head `f502e6c3e2877ec88b8e8f1a744e4d0fdf6b9c1f`.
- Added persistent `recommendation_diversity` (strict integer 0–100, default 0), `GET/PUT /api/settings/recommendation-diversity`, safe fallback to 0 for absent/corrupt stored values, and rejection of invalid writes without persistence.
- Integrated dynamic MMR marginal ranking inside existing personal recommendation allocator passes. MMR applies only among ownership-clear candidates; non-clear candidates keep legacy positions. Value 0 bypasses MMR ordering and preserves previous selection order. Existing category/style/family policy, artist cap, deterministic ties, ownership behavior, and 60-check limit remain intact.
- Added regression coverage for preference service validation/fallback, persistence defaults/round-trip, API paths and invalid inputs, setting-to-allocator wiring, MMR candidate ordering, ownership gates, artist cap, and allocation contract validation.
- All four required workflows passed on the exact final PR head: Python syntax, Docker packaging/full unit suite (655 tests passed), container runtime smoke test, and validation-only multi-architecture image validation (publishing paused). Earlier CI iterations caught and fixed the server-size ratchet and a candidate-tag assignment regression; neither safety guard was weakened.
- The identity-free fixture CLI result remains documented. The earlier 35-combination/floor-sweep reproduction is dismissed as a decision input; no further fixture test was run. The fixture/report remains private and unchanged.
- No UI change, live provider call, publish, deployment, or production-runtime verification occurred.
- **Next action:** coordinate the separate settings UI PR, following frontend file ownership and the documented API contract. Keep publishing and deployment paused.

## 2026-10-17 — Owner-supplied offline MMR comparison

- Evaluated the private 66-candidate scored pool with lambda values 0, 0.1, 0.25, 0.5, 0.75, and 1.0. The owner supplied aggregate output; candidate identities remain private.
- All runs returned 10 results, 10 unique artists, no duplicate non-empty artist keys, eligible-pool checks true, and deterministic repeats. Lambda 0 retained 7/10 baseline recommendations, mean pairwise similarity 0.1044, mean raw score 0.1540. Lambda 0.25/0.5 retained 7/10, similarity 0.1007, mean score 0.1539. Lambda 0.75/1.0 retained 7/10, similarity 0.0591 (about 43% lower than lambda 0), mean score 0.1412 (about 8.3% lower), and baseline relevance-score retention 85.5%. Lambda 0.1 retained only 6/10.
- Preliminary decision: use lambda 0.75 as the candidate for a controlled adapter-integration PR; lambda 1.0 showed no additional reported benefit on this capture. At lambda 0, unique artist count is already 10 because the hard one-per-artist cap remains active, so the measured diversity gain is primarily lower genre/tag similarity. This single frozen comparison does not establish future-listen hit-rate/nDCG or sustained real-world benefit.
- PR #320 merged at `7fe6003e9317711f49e8757864ff4b0097ea7046` after the final diff review and all four required workflows passed on that exact head: Python syntax `39064208835`, Docker packaging/full unit suite/build `39064208799`, container runtime smoke `39064208857`, and validation-only multi-architecture image validation `39064208813` (publishing paused). No assistant-side local tests were run; the aggregate fixture metrics below were supplied by the owner.
- Next action: create a controlled adapter integration using lambda 0.75 with characterization tests for eligibility, stable artist identity, missing tags, deterministic output, and unchanged API/persistence/provider behavior. Do not publish or deploy.
- Publishing, deployment, and runtime verification remain unperformed.

---

## 2026-10-17 — Phase 3.1 offline MMR evaluator implementation

- Branch `feat/offline-mmr-capture-evaluator`, based on main `442f2dcdb1a7824a24eb6a1d80ae9b7b2fbc1996`.
- Added `recommendation_mmr_evaluate.py`, a provider-free evaluator that validates the existing owner-only capture and compares its captured scored debug candidate pool with the original top 10 across a configurable MMR lambda grid. It does not replay stale provider events, import the application, access network providers, or write application state.
- Added synthetic tests for lambda-grid metrics, deterministic repeatability, one-per-artist enforcement, explicit owned/ineligible-row rejection, missing score-pool refusal, and invalid limits. Added both files to the Python syntax workflow.
- The report includes baseline overlap/retention, relevance score retention, unique artists, mean pairwise similarity, hard artist cap, and repeatability. `--identity-free` omits candidate identities from printed output. The evaluator refuses to fabricate scores if `debug_all_candidates` is absent.
- Limitations: the evaluator's candidate rejection depends on explicit flags/decision labels in the captured debug rows; verify those semantics against the private fixture and gathered library snapshot before interpreting eligibility as fully audited. It does not measure future-listen hit-rate/nDCG. The owner-local capture was not accessible to this session, so no private evaluation or local test run is claimed.
- Production recommendation ranking is unchanged. Publishing, deployment, and runtime verification remain unperformed. Exact-head CI and full diff review remain pending.
- Next action: run exact-head required workflows, then execute the evaluator against the unchanged private capture in the isolated environment and review the local results before choosing any lambda or production integration.

---

## 2026-10-17 — Phase 3.1 MMR offline evaluation prioritized; replay compatibility blocker recorded

- The owner requested that MMR evaluation become the next recommendation-engine priority and that the session close with this recorded.
- PR #316 remains merged at `f2393fdfb9e793f8d8b7f32a13c2fc754cbd9409`; its pure `discovery_mmr.py` selector and diversity metrics are not integrated into production ranking.
- Owner ran strict replay of private fixture `baseline-20261017_new.json` against the merged source. Fixture capture SHA is `d8c1f3de5180b35919f55c304d55e5c939dad373`; it contains 83 resolved candidate albums, 10 expected recommendations, and 197 provider events. Replay returned `reproduced: false`, reporting provider call mismatch at event 125. A local diagnostic found the first observed divergence at event index 104: expected operation `http_client.open`, actual operation `metadata_cache_get`. This indicates call-order incompatibility between captured and newer code, not a failed MMR quality result. The fixture was not changed or uploaded.
- Next priority: create a deterministic offline evaluator that consumes the fixture’s captured `gathered_inputs` and `expected_output` directly, rather than replaying the stale provider-call tape. Compare original top 10 with MMR selections over a documented lambda grid, reporting relevance retention/order changes, unique artists, mean pairwise similarity, hard artist/eligibility invariants, and repeatability. No live providers, app-state writes, or private identities in committed output.
- Documentation PR #319: branch `recommendation/mmr-offline-evaluation-priority`; initial PR head `9396a64699a82d41caeac49468d56a4990d52828`. No code tests were run in this documentation-only closeout; required workflow results were not available at the time of this entry and must be verified against the final PR head.
- Production ranking remains unchanged; no publishing, deployment, or runtime verification is authorized or claimed.

---

## 2026-10-17 — PR #314 merged: metadata-led classification and source provenance

- PR #314, [Make recommendation classification metadata-led and track source provenance](https://github.com/abucalip/navi-librarian/pull/314), merged at `295da73b9d279e944501c5c3d28866e8b1b7123f` from exact final PR head `21e5f8da161613427748e995f5b542c9f24c0859`.
- Recommendation category and diversity-style classification now prefer provider genre tags when present. Hardcoded artist-name fallbacks are used only when provider genre metadata is absent. Regression tests cover missing-metadata fallbacks, conflicting provider metadata, and query-style hints yielding to actual tags.
- Added `discovery_sources` for ListenBrainz CF, profile-derived MusicBrainz tag queries, and candidate-pool exploration queries. Duplicate candidates merge and deduplicate recognized labels. The legacy singular `discovery_source` remains unchanged for compatibility.
- Source provenance is supplied to the private aggregate diagnostic summarizer, which counts recognized sources independently and preserves compatibility with older records. Raw tag names, candidate identities, and the new provenance list are not added to the public response payload. The Docker unit suite passed 633 tests on the exact final PR head.
- All four required workflows passed on exact final PR head `21e5f8da161613427748e995f5b542c9f24c0859`: Python syntax/size/import-boundary run 1595 (`39050221841`); Docker packaging/full unit suite/build run 1503 (`39050221969`, 633 tests passed); container runtime smoke run 1312 (`39050221788`); validation-only multi-architecture image validation run 1356 (`39050221624`, publishing paused). Initial CI found one stale test expectation after metadata precedence changed; it was corrected and all four workflows passed on the final head.
- No assistant-side local tests were run. Publishing remains paused; no deployment or production-runtime verification is claimed.
- **Next action:** Phase 3.1 — evaluate deterministic MMR-style re-ranking with the offline replay harness, keeping hard artist and eligibility constraints.

---

## 2026-10-17 — PR #312 merged: profile-derived supplementary queries

- PR #312 merged at `5b23b08556c467a67b0b6cdbe7148dc069eda6f1` from exact final PR head `dc957f9eb1d817fcc2117f819c0d12be6663b142`.
- Replaced the 20 fixed regional MusicBrainz supplementary searches with up to six queries selected by 14-day-decayed listening weights against cached artist genre tags, plus up to two exploration queries from the ranked CF candidate pool. The selector is pure and directly tested for contrasting profiles, weighted determinism, exploration quota, safe query formatting, and bounds. Cache reads are bounded to 15 recent artists and 60 candidate artists; provider rate limiting, 30-day search-result cache, candidate cap, and graceful failure behavior remain intact.
- Removed four fixed regional one-slot allocation targets so regional styles are not hidden preferences. Measured diversity re-ranking remains Phase 3 work.
- All four required workflows passed on exact final PR head `dc957f9eb1d817fcc2117f819c0d12be6663b142`: Python syntax/size/import-boundary `39049404041`, Docker packaging/full unit suite/build `39049404031`, container runtime smoke `39049404044`, and validation-only multi-architecture image validation `39049404139` (publishing paused). The Docker unit suite reported 631 passing tests on the preceding code/documentation head `f4eaa44642003ea233cd1f66274746286732d6d4`. No assistant-side local tests were run. Publishing remains paused; no deployment or production-runtime verification is claimed.

---

## 2026-10-17 — Phase 2.1 profile-derived supplementary queries (verification pending)

- Started branch `recommendation/profile-derived-tag-queries` from current GitHub main `c6cbd65e872944b08f15ae66df94d15935dccf6e`.
- Added pure `discovery_tag_queries.py`: up to six queries weighted by decayed recent-artist listening against cached genre tags, plus up to two exploration queries from cached tags associated with the CF candidate pool. Queries are bounded, deduplicated case-insensitively, quote multiword tags, and reject invalid/control-character tags.
- Replaced the 20 fixed regional supplementary queries with profile-derived selection and removed four fixed regional one-slot allocation targets. Cache reads are bounded to 15 recent artists and 60 candidate artists; no additional live provider is introduced. Existing MusicBrainz request throttling, 30-day result cache, per-query result cap, candidate cap, failure isolation, and primary CF candidates remain in place. Added direct tests for contrasting profiles with unchanged cache, deterministic weighted selection/exploration quota, escaping/invalid tags, and limit validation. Added the helper to Docker packaging.
- Verification on code/documentation head `f4eaa44642003ea233cd1f66274746286732d6d4`: Docker packaging/full unit suite/build passed with 631 tests (`39049316950`); Python syntax/size/import-boundary passed (`39049316942`); container runtime smoke passed (`39049316947`); validation-only multi-architecture image validation passed (`39049316962`, publishing paused). Earlier CI attempts exposed two assertion mistakes in the new test expectations; those were corrected before the successful run. No assistant-side local tests were run. A final documentation-only commit requires all four workflows to be checked again on its exact PR-head SHA. Publishing remains paused; no deployment/runtime verification.

---

## 2026-10-17 — Recommendation Phase 0 closed; Phase 1 profile responsiveness started

- The owner reports using the app since v0.1 publication and that recommendations have remained overwhelmingly the same despite daily changes in listening history. This is accepted as sufficient real-world evidence to prioritize profile-responsive ranking without further diagnostic collection. It establishes the product defect, not a definitive technical root cause.
- Closed PR #308, “Add bounded recommendation diagnostic history,” unmerged at the owner's direction; its diagnostic-history implementation was not incorporated into main.
- Started branch `recommendation/time-decayed-profile` from main `6f9dc1c0073690d78862fa95f510984397ee65e2`. Added deterministic per-listen weights using a 14-day half-life relative to the newest dated listen; undated legacy/test records retain equal weight so existing fixtures remain compatible. Used weighted artist/artist-MBID/family counts for ranking/profile calculations while preserving raw counts for public play-count fields.
- Replaced the familiarity step function with a smooth bounded curve peaking at low-but-nonzero weighted familiarity, and raised the profile relevance multiplier cap from 10% to 25% so current taste can compete more strongly with familiarity and popularity. Added focused tests for deterministic decay, invalid half-life rejection, curve shape, and profile-score response to contrasting family weights. Existing ownership and release eligibility paths were not intentionally changed.
- PR #309 merged at `d11dce4d981af4c34aa60a4d9caedb15eb8b6d58` from exact final PR head `e00d07363c72fcbe971cb9b08432cd1f5bddf46e`. All four required workflows passed on that exact head: Python syntax/size/import-boundary run 1560 (`39047871211`); Docker packaging/full unit suite/build run 1468 (`39047871243`, 626 tests passed); container runtime smoke run 1277 (`39047871304`); validation-only multi-architecture image validation run 1321 (`39047871378`). The full diff was reviewed; focused tests cover recency weights, invalid half-life, familiarity curve shape, and contrasting profile weights. No assistant-side local tests were run. Publishing remains paused; no deployment or production-runtime verification is claimed.

---

## 2026-10-17 — Private recommendation baseline reviewed; policy gate remains closed

- Reviewed the owner-provided aggregate report from the private PR #298 capture/replay. The replay reproduced 10/10 recommendations from capture/source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`, consumed 197 provider events and 40 Last.fm events, and made zero network provider calls.
- The captured run returned 100 CF recordings; all 100 had metadata and grouped into 83 resolved albums. It recorded zero metadata lookup errors, zero unclassified recommendations, and met all category targets. Supplementary cache counters were 14 hits and zero misses.
- CF-recording Jaccard overlap and final-list Jaccard overlap against the previous stored snapshot were both 1.0. This supports only the narrow conclusion that the compared adjacent snapshots were identical. It is not a longitudinal trend and does not prove causation; the snapshot does not establish whether the profile changed between refreshes. The capture limitations include the 100-recording CF cap, incomplete community genre tags, bounded genre metadata lookup, 30-day profile window, cached Last.fm popularity, and imperfect ownership matching.
- The checked-in offline replay fixture is synthetic and useful for exercising metric calculations; it is not evidence of real-user relevance. The private exact replay validates deterministic reproduction, not future-listen hit-rate/nDCG or profile responsiveness. **Decision: do not change scoring, candidate generation, or allocation yet.** Collect comparable aggregate snapshots across multiple refreshes, preferably including a deliberate listening-profile change, and use CF-vs-final overlap to choose the next diagnosis.
- Private capture contents remain local and are not committed. This documentation change contains only aggregate metrics and interpretation. No code or ranking behavior changed; CI and PR review are still required on the documentation PR. Publishing remains paused; no deployment/runtime verification is claimed.

---

## 2026-10-17 — PR #305 merged: omit raw profile tags from recommendation diagnostics

- Based on current GitHub `main` after PR #304, review found that `recommendation_diagnostics.summarize_candidate_diagnostics()` persisted `profile_evidence.recent_family_counts` with raw family/tag names, contradicting the explicit privacy claim in the roadmap and PR #304.
- Replaced the raw-tag-keyed map with two aggregates: number of valid recent families and summed family-listen counts. Added regression assertions that representative raw tag names are absent from both returned summaries and persisted diagnostic JSON while aggregate counts remain available. Public response shape and recommendation ranking/candidate/allocation behavior are unchanged.
- PR #305 final PR head: `4b9e0ad77b89aac144bbf5505666381a49a2af69`; squash merge commit: `909eac617368f18a0ec4ff196f7eb83bb9a9a9c6`.
- All four required workflows passed on that exact final PR head: Python syntax/acquisition safety run 1539 (`39044014509`), Docker packaging/full unit suite/build run 1447 (`39044014507`), container runtime smoke run 1256 (`39044014508`), and validation-only multi-architecture image validation run 1300 (`39044014541`). No assistant-side local tests were run.
- Publishing remains paused; no deployment or production-runtime verification is claimed. Next: review the private PR #298 replay baseline metrics and limitations before making recommendation-policy changes.
---

## 2026-10-17 — Recommendation Phase 0.3: aggregate diagnostics (PR #304 merged)

- Started the branch from current GitHub main at `b51ab24dee6cd760c31e6924816143a8658db815` after reviewing the workflow, project status, requirements, test plan, recommendation roadmap, relevant source, and existing diagnostic tests.
- Added bounded aggregate metrics for candidate source provenance, base/final score, familiarity/exploration/profile/popularity bonuses, listening/profile evidence, supplementary cache hit/miss counts, and eligibility/selection outcomes. Metrics contain no candidate names, album titles, or raw tags and are persisted in the existing private pool-diagnostic record; the public diagnostic response shape and ranking behavior are unchanged.
- Added deterministic tests for summary values, identity omission, private persistence, and no public-schema expansion. No assistant-side local tests were run. On exact final PR head `808ed2621ec5a3e9db3a05083e5fb1dcc828e4cb`, all four required workflows passed: Python syntax/size/import-boundary run 1531 (`39042482100`); Docker packaging/full unit suite/build run 1439 (`39042482020`); container runtime smoke run 1248 (`39042481923`); validation-only multi-architecture build run 1292 (`39042481930`). PR #304 squash-merged at `19435d5deea69b188d920cf375ef924ec3b14a97`.
- Publishing remains paused. No deployment or production-runtime verification is claimed. Next action: review the private PR #298 replay baseline metrics and limitations before making any recommendation-policy changes.

---

## 2026-10-17 — Recommendation Phase 0.3: refresh-origin diagnostics (PR #303 merged)

- Started from GitHub main merge commit `bb473e99855208606e3bcb76dbf7c1cb9eb09b43` after checking recent commits and the PR #302 merge state. The recommendation roadmap's next baseline-independent observability step was to trace personal-list refresh origin and outcome through persistence.
- Added origin-aware personal refresh instrumentation for `manual` and `scheduler` triggers. The recommendation adapter receives the origin, pool diagnostics retain it in persisted diagnostic metrics, and SQLite stores only the latest bounded outcome per trigger: success, error, or already-running, with timestamp, optional item count, and exception type only.
- Added regression coverage for origin propagation, success/error outcomes, per-origin latest-state replacement, rejection of arbitrary origins/statuses, and absence of provider exception messages from persisted outcome telemetry. No ranking, candidate-selection, allocation, or public response-schema changes were intended.
- PR #303: `https://github.com/abucalip/navi-librarian/pull/303`; final PR head `29c793d29c8209153f4a480903df32372bf52fec`; squash merge commit `a04d4f4c3b5beed3e29969c75cf812591222dc08`. All four required workflows passed on the exact final head: Python syntax run 1521; Docker packaging/full unit suite/build run 1429; container runtime smoke run 1238; validation-only multi-architecture build run 1282. No assistant-side local tests were run. Publishing remains paused; no deployment or production-runtime verification is claimed.
- Next action: add aggregate candidate-provenance, score-component, profile-evidence, cache, and rejection diagnostics. Keep recommendation-policy changes gated on review of the private replay baseline metrics and limitations.

---

## 2026-10-17 — PR #302: Agent session context search workflow

- PR #302 adds `scripts/session_search.py`, a standard-library lexical search tool returning ranked documentation/source snippets. It supports docs/code scopes, quoted phrases, all/any matching, bounded context and file sizes, JSON output, and excludes common generated/virtual-environment/data directories.
- Added `tests/test_session_search.py` covering query parsing, all/any matching, scope filtering, snippets, ignored directories, file-size bounds, and empty-query rejection.
- Added `docs/SESSION_CONTEXT_SEARCH.md`; updated `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, and this status to establish focused retrieval as the standard agent workflow. Search remains a navigation aid; GitHub state inspection, canonical-doc reading, caller/test tracing, and all existing verification gates remain mandatory.
- Initial CI on head `627c442780f26613e76541cbc46e91d6058997b3` exposed one test-fixture assumption: the documentation fixture also contained both query terms. The test was corrected to use a distinctive all-terms query. On corrected code head `157dfa3d18ff253d4de64e91907166d3aba442bb`, all 616 unit tests passed in Docker packaging workflow 1416; Python syntax/size/import-boundary checks passed in workflow 1508; container runtime smoke passed in workflow 1225; validation-only multi-architecture build passed in workflow 1269. Publishing remained paused.
- PR #302 merged at `bb473e99855208606e3bcb76dbf7c1cb9eb09b43` from final PR head `1baa1d43920974b8a03da60abd84256e3bcbdd35`. The available recorded CI evidence is on corrected code head `157dfa3d18ff253d4de64e91907166d3aba442bb` (616 unit tests and four workflows); this log does not establish that those workflows ran on the exact final PR head. Publishing remains paused; no deployment or production-runtime verification is claimed.
- The current follow-up is recommendation Phase 0.3 refresh-origin diagnostics in PR #303.

---

## 2026-10-17 — PR #298 merged: recommendation diagnostics and offline capture/replay

- PR #298, “Add recommendation diagnostics and offline capture/replay,” merged at `68a0ee365778dab790ec54e04b54c8c72bd4552c`. Exact final PR head: `a3bdfd7bff6785c1fd17e422a26a7fde36170fad`.
- Added bounded recommendation-pool diagnostics with hashed recording/album identities, deterministic synthetic metrics, private opt-in capture, strict offline replay, and HTTP error replay fidelity preserving request method and fully resolved URL/query parameters. Candidate classification was extracted into `discovery_recommendations.py` with regression coverage to satisfy the legacy-server size guard without weakening it.
- User's isolated Mac replay of private capture/source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373` reproduced 10/10 recommendations, consumed 197 provider events and 40 Last.fm events, and used zero network providers. Stable output comparison excludes only `pool_diagnostics` and `lastfm_last_error`; the private capture was not uploaded or exposed. Review baseline metrics and limitations before changing ranking/scoring/source/allocation.
- All four required workflows passed on exact final PR head `a3bdfd7bff6785c1fd17e422a26a7fde36170fad`: Python syntax/size guard `39037807384`; Docker packaging/full unit suite/build `39037807392`; container runtime smoke `39037807378`; validation-only multi-architecture image build `39037807401`. Publishing remains paused. No deployment or production-runtime verification is claimed.

---

## 2026-10-17 — PR #299 merged: discovery refresh freshness diagnostics

- PR #299, “Improve discovery refresh freshness diagnostics,” merged at `22820fb534ce243c78b1bb30d1f7cbbaaabd36cd`. Exact final PR head: `e830adc7b014a915d31756619e5fadc90106696c`.
- Added deterministic freshness classification for missing, expired, malformed, and non-finite cache timestamps; isolated cache-read and refresh failures per list; and bounded scheduler warnings that include list, stage, and exception type but omit exception messages/URLs. The scheduler's 24-hour threshold, hourly cadence, list ordering, callbacks, and API response contracts remain unchanged. Recommendation ranking, candidate selection, and allocation are unchanged.
- All four required workflows passed on the exact final PR head: Python syntax run 1497; Docker packaging/full unit suite/build run 1405; container runtime smoke run 1214; validation-only multi-architecture image validation run 1258. The multi-architecture workflow is validation-only; publishing remains paused.
- No assistant-side local tests were run. No image publication, deployment, or production-runtime verification is claimed.
- PR #298's private baseline replay succeeded on source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373` (10/10 recommendations; 197 provider events; 40 Last.fm events; zero network providers). Review baseline metrics and limitations before changing recommendation scoring, candidate selection, or allocation.

---

## 2026-10-17 — PR #298 HTTP error replay fidelity fix

- Investigated the private-baseline discrepancy without accessing or printing the private capture. The replay cassette recorded HTTP status/JSON only and rebuilt responses with a GET request using the unexpanded first URL argument. This discarded the original response request's method and fully resolved URL (including query parameters supplied separately), so HTTPX HTTPStatusError text could differ despite matching status counts and recommendation output.
- Updated HTTP response capture to retain the original request method and resolved URL, and replay to reconstruct the response with those values. Older cassette events retain a compatibility fallback. Added a synthetic HTTPX 503 regression that asserts identical request URL/method and exception text, including query parameters; no ranking/candidate-selection logic changes.
- The user replayed the private baseline offline against exact source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`: 10/10 recommendations reproduced, 197 provider events and 40 Last.fm events consumed, zero network providers used. The comparator includes all stable top-level fields except `pool_diagnostics` and `lastfm_last_error`. CI on the latest PR head and final review remain pending; publishing/deployment remain paused.

---

## 2026-10-17 — PR #298 extended with private recommendation capture and replay

- Extended the existing open recommendation baseline PR rather than stacking a second PR on its still-unmerged base.
- Added opt-in `LIBRARIAN_RECOMMENDATION_CAPTURE_PATH` capture. A successful run records ordered provider/cache calls and consumed results (ListenBrainz, MusicBrainz HTTP, cache get/set, Navidrome API responses), the ranking input snapshot, Last.fm callback results, expected output, timestamp, schema version, source SHA, and SHA-256 integrity hash.
- Added strict cassette replay for the actual candidate-gathering and ranking entry point. Replay validates request identity and event order, uses captured HTTP responses and cache values, disables provider sleeps, substitutes captured Last.fm results, and skips mutable pool-diagnostic persistence. It fails on missing/extra events or output mismatch.
- Capture files must be outside the repository, in a mode-700 directory; files are created mode 600 and existing files are never overwritten. Real listening/library/provider data must not be committed or attached to public PRs.
- Added regression tests for freeze/thaw ordering, private capture permissions, overwrite refusal, checksum tampering, provider cassette replay, and strict Last.fm call order. Added the replay module to Docker packaging and documented setup/replay commands and limitations.
- No ranking/scoring/allocation behavior was intentionally changed. Earlier code head `794013c3966c4d2dd9f736ccee4089c8621df943` passed all four required workflows: Python syntax `39022880718`, Docker packaging/full unit suite/build `39022880732` (602 tests), container runtime smoke `39022880724`, and validation-only multi-architecture image validation `39022880734`. The later private capture at `d8c1f3de5180b35919f55c304d55e5c939dad373` replayed successfully offline (10 recommendations; 197 provider events; 40 Last.fm events; zero network providers). CI for the latest head remains unverified; no merge, publication, deployment, or production-runtime verification is claimed. Publishing/deployment remain paused.

---

## 2026-10-17 — Recommendation Phase 0 diagnostics and offline replay harness

- Started from GitHub main `06c4407f7185db1abfecdad256d7bfd6821327e1`, after confirming no open PRs. Objective: implement recommendation roadmap Phase 0.1/0.2 without changing ranking.
- Added bounded pool fingerprints and one-snapshot SQLite diagnostics. Recording MBIDs and album identities are SHA-256 hashed before persistence; only the latest snapshot is retained. Diagnostics compare current and prior CF pools and final recommendation lists using Jaccard overlap and include provider/cache/source counts.
- Added deterministic offline replay metric helpers and a frozen synthetic fixture. The harness reports unowned-artist hit rate@k, nDCG@k, artist/style spread, ownership exclusions, eligibility counts, and pool/ranking overlap across contrasting cases. The fixture explicitly documents that it is synthetic, not evidence of live recommendation quality.
- Wired diagnostics into the existing recommendation response without changing selection/scoring logic. Initial CI exposed three incorrect test expectations; corrected them and added the new diagnostics module to Docker packaging.
- Exact code/test head `57011aa17b798b9173dfa9b1a3bc493a4a29f9a2` passed all four required workflows: Python syntax/acquisition safety `38992151740`, Docker packaging/full unit suite/build `38992151716` (596 tests passed), container runtime smoke `38992151848`, and validation-only multi-architecture image validation `38992151723`. Publishing remains paused.
- Tests were run by GitHub Actions; no local tests were run in this GitHub-only session. The fixture is synthetic and does not yet constitute a captured historical engine baseline or a full provider-input-to-engine replay. Phase 0 is therefore **partially implemented**, and no scoring/source/allocation changes are authorized by these results. No deployment or production-runtime verification is claimed.
- Branch: `feat/recommendation-baseline-diagnostics`, PR #298. Next: complete documentation closeout and verify CI on that final PR head; then capture a reproducible baseline fixture from frozen provider/listening/library inputs before changing ranking.

---

## 2026-10-17 — MCP retirement closeout

- Refreshed GitHub `main`: PR #296's retirement implementation is present at commit `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`; the earlier status/plan text incorrectly still described the PR as open and verification as pending.
- Confirmed the merged source/configuration state: `requirements.txt` no longer declares the MCP SDK; the Dockerfile no longer copies `mcp_registry.py`; Compose exposes only the web service; the web app is the supported interface. The implementation removes the MCP registry/transport and the separate un-packaged Proxmox MCP entry point while retaining shared Librarian functions and `read_only_command_policy.py` safety coverage.
- PR #296's four required workflows were reported passing on its final PR head: Python syntax/acquisition safety; Docker packaging/full unit suite/build; isolated container runtime smoke; validation-only multi-architecture. Publishing remains paused. A follow-up workflow/status query returned no records, so no new run IDs or fresh execution are claimed here.
- No local tests were run during this documentation closeout. No publication, deployment, or production-runtime verification is claimed.
- Updated `docs/MCP_RETIREMENT_PLAN.md` and `docs/PROJECT_STATUS.md` to mark repository-level retirement complete and distinguish it from external-client/configuration migration. Repository inspection cannot identify user-specific or external clients still pointing at the retired endpoint; persisted settings were not migrated.
- Documentation-only closeout branch: `docs/closeout-mcp-retirement`, based on `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. CI for this documentation follow-up remains to be checked on its final PR head. No merge/publication/deployment is claimed for this follow-up.
- Next action: verify required CI for the documentation closeout PR, merge if all required gates pass, then treat any external client migration as a separate user-environment check.

---

## 2026-10-17 — MCP retirement implementation prepared

- Audited current GitHub `main` against `docs/MCP_RETIREMENT_PLAN.md`. The 25-entry registry in `mcp_registry.py`, the `mcp==2.3.0` requirement, the Docker COPY reference, and the `navidrome_server.py` streamable-HTTP startup block were the Librarian runtime/package references. The broader audit also found `server.py`, a separate un-packaged Proxmox MCP entry point with a hardcoded SSH identity/host. `compose.yaml` defines only the web service and exposes its configured web port; no separate Librarian MCP service is configured.
- All 25 registry-referenced function definitions are retained in this focused change to avoid deleting behavior based solely on MCP registration. Web routes continue using shared service functions through the lazy adapter; any MCP-only helper definitions are no longer registered or exposed by a transport and may be reviewed separately for dead-code cleanup. Removed MCP registration/transport/package wiring, replaced the registry tests with MCP-free architecture checks, and left existing acquisition/import/cleanup safety tests intact.
- Audit uncovered that the standalone MCP block also started the discovery scheduler, while the supported Uvicorn web entry point did not. Added idempotent scheduler startup from the FastAPI startup hook so scheduled refresh remains available under the supported entry point.
- Removed the unrelated `server.py` Proxmox MCP entry point and its handler tests; retained `read_only_command_policy.py` and its rejection tests for shell composition, invalid IDs, and unsafe device paths. Updated the MCP retirement plan, requirements, test plan, workflow, status, and project log. External MCP clients or user-specific configuration cannot be determined from repository inspection; no such consumer is defined in the inspected Compose configuration.
- Branch: `retire/remove-mcp-runtime`. PR #296 is open; exact-head CI and verification evidence are pending. No local tests have been run from this GitHub-only workflow; do not infer passing tests or CI. Publishing remains paused. No deployment or production runtime verification is claimed.

---

## 2026-10-17 — Post-closeout hygiene: remove orphan patch scripts and tighten server ceiling

- Starting from `main` after PR #290 merge (`c20e931de22fe30cc3378867cbbebe56b28a91a4`), reviewed the closed modularization roadmap and size-guard/testing documentation.
- GitHub code search found no references to `patch_recommender.py` or `patch_recommender_v2.py`; neither script is part of the Docker COPY list or current server/app imports. Both are one-off source-rewriting experiments with backup/compile behavior rather than maintained runtime code, so removing them reduces ambiguity and audit surface.
- Tightened `scripts/check_server_size.py` from 3,031 to 2,650 lines, leaving 53 lines above the current 2,597-line server count measured from the fetched source with `splitlines()`. Updated the guard's docstring/comment to direct new domain logic into modules and added a regression assertion for the ceiling. Updated status, roadmap, test plan, and workflow references.
- This entry records intent only; PR/commit SHA, focused/full test results, exact-head CI, and merge state will be added after verification. Publishing remains paused; no deployment or runtime verification is claimed.

---

## 2026-10-16 — PR #288 merged: Docker recommendation import packaging fixed

- Follow-up audit after PR #286 found a second missing Docker dependency: `navidrome_server.py` imports `discovery_candidate_gathering.py`, but the explicit Docker COPY list omitted it.
- PR #288 added the module and generalized `tests/test_docker_packaging.py` to AST-inspect the legacy server and require every imported root-level Python module to appear in the Docker COPY sources. This also guards the earlier `acquisition_import_service.py` omission fixed by PR #286.
- Exact PR head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c`; merge commit `047822df81b134084383ed370205b1a3554c706a`.
- All four required workflows passed on that exact head: syntax `38978049684`, Docker packaging/full unit suite/build `38978049670`, runtime smoke `38978049793`, and validation-only multi-architecture `38978049589` (publishing paused). No local tests, deployment, or production-runtime verification are claimed.
- Post-merge review compared current `navidrome_server.py` root-level imports with the Docker COPY list: all 48 distinct imported root modules are included. This does not yet prove transitive or dynamic imports are fully packaged; the final modularization audit remains open.
- Next: inspect transitive imports of packaged root modules and the exact-main dependency-map artifact, then review dynamic/runtime imports and compatibility/safety coverage. Do not declare modularization complete or invent size-only extractions before that audit finishes.

---

## 2026-10-16 — Follow-up audit found another missing Docker module

- After PR #286 merged as `1cf9d66ad57364eec855b2425263e9a59b011d9a`, continued the modularization completion audit by comparing `navidrome_server.py` imports with the explicit root-level Docker COPY list.
- Found that `discovery_candidate_gathering.py` is imported by `navidrome_server.py` at line 305 but is absent from the Docker image source list. This affects the recommendation path and was not detected by the earlier audit because it focused on the import-completion module.
- The follow-up fix adds the missing module and generalizes `tests/test_docker_packaging.py` to AST-inspect `navidrome_server.py` and assert that every imported root-level Python module is copied into the image, including imports nested inside functions.
- PR and CI evidence are pending; no local tests were run. Continue the packaging/runtime audit after this fix and do not declare modularization complete until the exact-main dependency map, dynamic imports, Docker inclusion, and safety/compatibility tests have been reviewed. Publishing remains paused.

---

## 2026-10-16 — PR #286 merged: Docker acquisition import service packaging fixed

- Completion audit of GitHub `main` at `1f8f37ba7f9c289b694b1089492ba7a3cfdacf82` found that `navidrome_server.py` lazily imports `acquisition_import_service.import_completed_source_locked()` during import completion, but the explicit root-module COPY list in `Dockerfile` omitted `acquisition_import_service.py`. Startup alone did not exercise this delayed import.
- PR #286 added the missing module to the Docker image and added `tests/test_docker_packaging.py` to guard the COPY list. Merge commit: `1cf9d66ad57364eec855b2425263e9a59b011d9a`; exact PR head: `de68aa4cd5cbd657bcdd1c59cdde4e2b7e1df283`.
- All four required workflows passed on that exact head: Python syntax `38977669838`, Docker packaging/full unit suite/build `38977669928`, container runtime smoke `38977669818`, and validation-only multi-architecture image validation `38977669844`. Publishing remained paused. No local tests, deployment, or production-runtime verification are claimed.
- Confirmed the AST/source-layout migration is complete in PR #274 and the documented lazy `app/api/dependencies.py:get_librarian()` import remains the only permitted app-to-legacy edge.
- Next: finish the modularization completion audit against exact current `main`, including the generated dependency-map artifact, dynamic/runtime imports, Docker module inclusion, and compatibility/safety coverage. If no concrete gap remains, close modularization without inventing another extraction.

---

## 2026-10-16 — UI PRs #222, #279, and #282 merged

- Owner confirmed all three UI changes were manually tested and explicitly waived the older manual-report requirement for this merge set. The changes were reviewed as UI-only; #222 updates the dashboard coverflow ring and its keyboard contract, #279 adds the async Get-button visual/state treatment, and #282 removes the redundant colored toast side border.
- PR #222 exact head `5b55527ec3a13aaa137ed3d56341fb029913f09f`: all four required workflows passed (Python syntax, Docker packaging/full unit suite, container runtime smoke, and non-publishing multi-architecture validation). Squash-merged as `880fc34b43012f235fd0920bacd6ba644ecf3713`.
- PR #279 exact head `b3f44942724b6f9c6865f6c9160a69e58715b28a`: all four required workflows passed. Squash-merged as `48675a803ef6a74dbb5782a1c87fdacd2c278b76`.
- PR #282 exact head `cbe30a5bf26e503f1cb455861b32a5064b3604ab`: all four required workflows passed. Squash-merged as `71eb20bc734f1113f81b62eef35e17d53b8adf8e`.
- Merge order was #222, #279, then #282. GitHub reported successful merges and each PR is now closed/merged. The commits were reviewed as non-overlapping functional regions despite shared UI asset files; GitHub mergeability was refreshed before the final merge.
- No assistant-side local tests or browser tests were run in this session; manual testing is recorded as owner-reported. No publishing, deployment, or production runtime verification was performed. Publishing remains paused.
- Next: continue from the modularization roadmap only where a concrete, testable responsibility boundary justifies the work.

---

## 2026-10-16 — PR #270 merged: import-completion service extraction

- Based on GitHub main after PR #268 merge `d5f48cd5666ccbe2ab318516b7ed9fba0fa37fee`. Added `acquisition_import_service.import_completed_source_locked()` with injected path naming, authoritative status persistence, hardened import operation, and clock dependencies. The legacy `_discovery_import_completed_source_locked()` is now a narrow adapter; the outer transition-lock/dismissal guard is unchanged.
- Added direct-import tests for failure to persist `importing` (no filesystem mutation), successful status ordering and mount identity arguments, symlinked artist destination refusal, existing destination preservation, and unavailable library roots. The existing AST-based compatibility test remains in place and now executes the thin adapter, so this extraction does not remove lock/dismissal coverage.
- PR #270 was rebased onto current main (`d5f48cd5666ccbe2ab318516b7ed9fba0fa37fee`) on branch `refactor/acquisition-import-service-main`; final PR head is tracked by GitHub. All four required workflows passed on exact final PR head `6f2a32656f399b1bde64e4746d6f5626a60678d0`: Python syntax/acquisition safety, Docker packaging and full unit suite, container runtime smoke, and non-publishing multi-architecture validation. No separate local tests were run. Publishing remains paused; deployment/runtime on production is unverified.
- Status: merged as `d84d74c1cfa295e3c3fd2ff1594fa1758dc69949` after final diff review; all four required workflows passed on exact PR head `6f2a32656f399b1bde64e4746d6f5626a60678d0`. PR #269 was closed as superseded to avoid merging its stale base. Publishing remains paused; no deployment/runtime verification.


---

## 2026-10-16 — Acquisition coordinator policy/orchestration audit

- Audited GitHub `main` at `cd5d0240c1ac696417727de938736a1b15f7582b`. `_discovery_acquire_album_impl()` spans lines 2341–2618 and is 278 lines by the existing AST size measurement.
- Traced its responsibilities to extracted owners: `slskd_search_polling.collect_search_responses()` handles search polling; `_slskd_extract_candidates()` handles candidate policy; `acquisition_lifecycle.queue_failure_action()` classifies queue errors; existing adapters/services handle dismissal-serialized queueing, source-start checks, safe cleanup/source switching, and watcher startup.
- Remaining inline rules are interleaved with the orchestration: cap attempts at ten clear candidates; distinguish source rejection from fatal HTTP authorization/configuration errors; monitor uncertain queue outcomes rather than risk duplicate downloads; clean a definitively stopped source before fallback; and terminate when cleanup cannot be confirmed. These are safety-critical transitions, but no smaller cohesive policy API was identified that would reduce coupling rather than duplicate the orchestration.
- **Decision: retain `_discovery_acquire_album_impl()` as orchestration.** No application code changed and no tests were run for this audit. The size guard already tracks its 278-line size; do not extract it for size alone.
- Next: trace and migrate the remaining AST-coupled import-safety test in `tests/test_acquisition_safety.py` only after identifying a direct-import production owner and preserving destination path, filesystem mount identity, no-overwrite, and importing-status persistence-failure coverage. Operational MCP functions remain blocked on explicit owner decision.

---

## 2026-10-16 — Mutable MUSIC_DIR coupling audit

- Audited every MUSIC_DIR occurrence in the current navidrome_server.py source fetched from GitHub main (3,031 source lines; 3,032 split fields including the trailing empty element): initialization at line 88; persistence callback wiring at 218; raw library tag scan at 230; settings defaults and downloads fallback at 1517/1531; central and nested writers at 1545–1546, 1591–1592, and 1665–1666; settings-get adapters at 1580 and 1651; and acquisition recovery/watcher dependency injection at 2271/2286. Line references are audit-time references and should be refreshed before a later code change.
- Traced SettingsPersistence: its injected getter/setter separates SQLite persistence from runtime path ownership. read() applies a saved absolute path, while migration logic uses the current path to identify legacy downloads locations. service_settings.py similarly receives path getter/setter callbacks; tests/test_service_settings.py directly tests settings behavior and path updates.
- **Decision: no new settings object or wrapper extraction.** The remaining global reads are concentrated in the legacy compatibility/runtime owner, and the existing service and persistence modules already expose explicit callbacks. A new object would add indirection without removing the compatibility boundary; acquisition watcher/recovery adapters currently pass a path snapshot at invocation time, so changing ownership needs a broader lifecycle design and behavior tests, not a mechanical refactor.
- Documentation-only audit. No application tests or local commands were run. PR #267 was opened at head `e1df4f783c217fadecae57c002b8ad1a9d92766c`; the first workflow/status lookup returned no runs or status checks, so required CI is not yet verified. Recheck the final head before merge. No merge, publication, deployment, or production runtime verification is claimed.
- Next: audit _discovery_acquire_album_impl() for actual candidate-selection, source-switch, retry, and state-transition policy; keep it intact if it is only orchestration. Operational MCP functions remain blocked on explicit owner decision.

---

## 2026-10-16 — PR #265 merged: measurable legacy-server size ratchet

- Baseline measured against main after PR #264 merge commit `cb4f5aef3534e06128401ef3eed3e9ce2908b5f4`: `navidrome_server.py` has 3,031 source lines (`splitlines()`, matching the guard). On the first PR #265 CI run, AST measurements were `recommend_new_music`: 568 lines and `_discovery_acquire_album_impl`: 278 lines. The initial 3,032 count included the trailing empty element produced by splitting on a newline; the enforced ceiling is corrected to 3,031.
- Added `scripts/check_server_size.py` with a 3,031-line file ceiling, 280-line default top-level function ceiling, and a named temporary 575-line `recommend_new_music()` exception with reason and follow-up. Added pass/fail regression tests for file/function limits, exception diagnostics, and parse failures; wired compile and guard execution into the Python syntax workflow.
- Final PR head `0ac078656cf8af78cb507a9a7dfa337e1a173db7` passed all four required workflows: Python syntax/acquisition safety (`38965190861`), Docker packaging/full unit suite/build (`38965190744`), container runtime smoke (`38965190728`), and validation-only multi-architecture image validation (`38965190622`, publishing paused). The full unit suite ran 550 tests successfully; the size guard reported 3,031 source lines, `recommend_new_music()` at 568 AST lines, and `_discovery_acquire_album_impl()` at 278 AST lines.
- PR #265 squash-merged as `57ec3a594df22bba77895934535530c37d833087`. No assistant-side local tests were run. Publishing, deployment, and production runtime verification were not performed.
- Next: audit mutable `MUSIC_DIR` readers/writers before deciding whether settings-wrapper extraction is worthwhile.

---

## 2026-10-16 — PR #264 merged: recommendation provider diagnostics restored

- CI on merged PR #263 exact head `a0d0afcdc1c54b73c2227a24735f8a606bb38f6a` failed in both the Docker/unit and Python syntax/unit workflows. The unit suite ran 545 tests and reported six errors in `tests/test_recommend_new_music_characterization.py`: `recommend_new_music()` read `regional_candidates_added`, which the new provider-gathering result mapping did not return. Syntax compilation and the app-to-legacy import-boundary guard passed; Docker build was skipped after unit failure. Container smoke and validation-only multi-architecture workflows passed on that head.
- PR #264 returns `regional_candidates_added`, `regional_results_seen`, and `library_albums` from `gather_recommendation_candidates()`, unpacks them in `recommend_new_music()` before response shaping, and extends the stable response-shape characterization test to assert the regional counters. The first follow-up attempt restored the regional counter mapping but still failed because the adapter did not unpack those counters; the second CI run then exposed the same extraction-boundary issue for `library_albums`. The current follow-up fixes the provider result and adapter unpacking for all three values without changing candidate policy.
- PR #264 final head `c9635675005d995c368100688e0a8eaf5abb75ad` passed all four required workflows: Python syntax/acquisition safety (`38964596901`), Docker packaging/full unit suite/build (`38964597032`), container runtime smoke (`38964596886`), and validation-only multi-architecture image validation (`38964596916`, publishing paused). The full unit suite and syntax workflow passed on this exact head.
- PR #264 squash-merged as `cb4f5aef3534e06128401ef3eed3e9ce2908b5f4`. No assistant-side local tests were run. Publishing, deployment, and production runtime verification were not performed.

---

## 2026-10-16 — PR #263 merged: recommendation provider orchestration

- Merged PR #263 with merge commit `20728507774a210123ef91d72b7cd2370668659d`. Added `discovery_candidate_gathering.py` with an immutable `RecommendationProviders` dependency bundle for ListenBrainz, MusicBrainz, cache, Navidrome inventory, album eligibility, HTTP, and sleep dependencies. The public `recommend_new_music(count=10)` adapter remains; scoring, ownership allocation, and payload shaping remain downstream.
- CI verification is **unconfirmed**: the workflow-run lookup returned no runs for the merge commit. The initial PR run exposed six characterization failures from downstream imports; the adapter imports were restored in a follow-up commit, but no successful post-fix CI result was confirmed here. No local tests were run. Do not describe this revision as verified until characterization, full unit suite, and required workflows pass.
- Publishing, deployment, and runtime verification were not performed.

---

## 2026-10-16 — Shared raw Navidrome album inventory pagination

- Added `discovery_library_snapshot.fetch_album_inventory()`, a direct-import raw pagination helper with injected API/items callables, non-empty album-ID deduplication, and `AlbumInventoryLimitError.albums_retrieved`. Both `build_library_snapshot()` and `recommend_new_music()` now use it.
- Preserved the adapters' distinct contracts: snapshot cache, artist inventory, normalization, and persistence remain in `build_library_snapshot()`; the recommendation path still fetches fresh raw records and returns separate JSON error payloads for API failure and safety-limit exhaustion.
- Added `tests/test_discovery_album_inventory.py` for pagination, deduplication, raw record shape, safety-limit reporting, and API exception propagation. Extended recommendation characterization to pin the safety-limit response.
- PR #261 final head `4c8b621a26b9d8c4bceb8fa7e4be6d8956146fd1` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38962780709`), Docker packaging/full unit suite/build (`38962780687`), isolated container runtime smoke (`38962780674`), and validation-only multi-architecture image validation (`38962780692`, `push: false`). Full suite: 543 tests passed. No separate assistant-side local test command ran.
- PR #261 was squash-merged as `a9bc864df85a8fb643864cb128d6b70f10eb7dce`. No publishing, deployment, or production runtime verification was performed.
- Next: extract candidate gathering/provider orchestration from `recommend_new_music()` behind injected provider dependencies and verify output parity against the characterization fixtures.

---

## 2026-10-16 — Characterized Last.fm scoring and regional MusicBrainz failure

- PR #259 added deterministic tests for the current capped Last.fm popularity bonus and the behavior when regional MusicBrainz release-group searches return HTTP 503. The test asserts the personalized ListenBrainz candidate remains available and the regional failure is reported; the test HTTP client is fake.
- PR #259 final head `d39ee50b2ec0483da2a415ef81793d20d644a439` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38962391039`), Docker packaging/full unit suite/build (`38962391189`), isolated container runtime smoke (`38962391035`), and validation-only multi-architecture image validation (`38962391062`, `push: false`). Full suite: 539 tests passed. No separate assistant-side local test command ran.
- PR #259 was squash-merged as `4a82ce01cf37d0e9cff27a9f67f9a037cad23e2e`. Tests only; no production behavior changed. Publishing, deployment, and production runtime verification were not performed.
- Compared the inventory paths: both paginate `getAlbumList2` in batches of 500 up to 50,000 and deduplicate non-empty album IDs. However, `discovery_library_snapshot.build_library_snapshot()` uses a 10-minute cache, also reads artists, normalizes album records, and propagates API/safety exceptions; `recommend_new_music()` reads fresh raw records and maps inventory failures and safety-limit exhaustion to distinct JSON responses. Directly reusing the snapshot builder would change freshness, schema, and error semantics.
- Next: extract a small shared raw album-pagination helper with direct tests, preserving the two adapters' distinct cache, normalization, and error contracts. Only after that should the larger provider/candidate-gathering seam be extracted.

---

## 2026-10-16 — Expanded new-music ranking and provider characterization

- Extended `tests/test_recommend_new_music_characterization.py` with a fixed two-recording fixture proving recommendation output is ordered by discovery score rather than raw ListenBrainz order. Added assertions for the existing ListenBrainz recent-history error response and the empty-recommendation message.
- PR #257 final head `4de3a9e0488552e2f3452c00fe691fb8ce084e61` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38961968775`), Docker packaging/full unit suite/build (`38961968720`), isolated container runtime smoke (`38961968596`), and validation-only multi-architecture image validation (`38961968694`, `push: false)). Full suite: 537 tests passed. No separate assistant-side local test command ran.
- PR #257 was squash-merged as `2bbe5c28887e16c249c119634c7b33396351f540`. Tests only; no production behavior changed. Publishing, deployment, and production runtime verification were not performed.
- Remaining before extraction: characterize scoring/bonus effects and regional MusicBrainz failure behavior, and complete the comparison with `discovery_library_snapshot.py` so any inventory-schema/cache/safety-limit mismatch is explicit.

---

## 2026-10-16 — Initial new-music inventory characterization

- Added `tests/test_recommend_new_music_characterization.py` with deterministic mocked provider/cache responses. It pins the public response shape for a clear inventory, exclusion of an exact artist+album ownership match, duplicate album-ID deduplication before ownership indexing, and fail-closed behavior when Navidrome inventory retrieval raises.
- The first CI attempt on `4e52318afed32ccbfdcc61e43799a4bf72d76702` exposed one incorrect expected allocator decision (`exact_owned`); the assertion was corrected to the production contract (`already_owned`). The corrected code-only PR head `97798f8bb12bdfba9ad735ca4b5e900e634e1ca0` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38961591461`), Docker packaging/full unit suite/build (`38961591460`), isolated container runtime smoke (`38961591458`), and validation-only multi-architecture image validation (`38961591546`, publishing remains disabled / `push: false`). The full suite ran 534 tests. No separate assistant-side local test command ran.
- PR #255 was squash-merged as `4d21627f4d01c7129298fa2753c518006db5ba45`. This is test-only; no production behavior changed. No publishing, deployment, or production runtime verification was performed.
- Remaining before extracting the candidate-gathering pipeline: characterize stable candidate ordering/scoring and provider failure behavior, and finish comparing the inventory semantics with `discovery_library_snapshot.py`. This PR is the initial characterization slice, not the complete acceptance gate.

---

## 2026-10-16 — Migrated slskd transfer lookup tests to direct imports

- Replaced the AST harness in `tests/test_slskd_transfer_lookup.py` with direct imports of `slskd_transfers.download_transfer_files()`. Coverage retains the missing-peer 404 behavior, propagation of other HTTP errors, URL-escaped usernames and timeout, and successful parsing with remote-directory metadata.
- Kept the legacy `navidrome_server._slskd_download_transfer_files` compatibility contract in `tests/test_slskd_transfers.py`; no production behavior changed.
- Updated `docs/architecture/AST_TEST_INVENTORY.md`, `docs/MODULARIZATION_ROADMAP.md`, and `docs/PROJECT_STATUS.md`: two AST-coupled test files remain.
- Branch: `test/migrate-slskd-transfer-lookup`. Required CI passed on final PR head `66ef76b30e3c3b0a8a30169e3fa349f75b1c6d9e`: Python syntax/acquisition-safety and dependency map (`38954108967`), Docker packaging/full suite/build (`38954109155`), container runtime smoke (`38954109044`), and validation-only multi-architecture image validation (`38954108939`, `push: false`). No assistant-side local test command ran. PR #249 merged by squash as `60cf07ffa05416355053660c1823f6af5b18716b`. Publishing, deployment, and production runtime verification were not performed.

---

## 2026-10-16 — Dependency-map execution and AST-coupled test inventory

- Audit baseline: current GitHub `main` at `be01d3ebe41abc888de24b4e5bd01d54628bb0ff`. A local `git clone` could not run because this execution environment cannot resolve `github.com`; no local checkout was used as source of truth.
- Added a step to `.github/workflows/python-syntax.yml` that runs `scripts/dep_map.py`, prints key graph metrics and direct `app/** -> navidrome_server` imports, and uploads the full JSON as the `modularization-dependency-map` artifact (14-day retention). CI executed the script on initial PR head `1f9e6313310c691e9d9844d22136182e51ca6fee`: 159 local Python modules, 71 modules in the static `app.main` closure, `navidrome_server` included in that closure, and one direct app edge (`app/api/dependencies.py`). Artifact ID `12068042162` was downloaded and inspected. This is a static graph; the edge is a lazy import inside `get_librarian()`, and `tests/test_auth_routes_integration.py` verifies the app import does not eagerly initialize the legacy server. The final PR head `25324a25643e7f688eb1be057ba62cd6222a4c04` passed all four required workflows: Python syntax + unit suite (`38951397693`), Docker packaging/full suite/build (`38951397752`), container runtime smoke (`38951397876`), and non-publishing multi-architecture validation (`38951397770`). The final artifact is `12068282349`. PR #247 merged as `26009d1321c2169859f06c75c0a8abb409425325`. No local test command ran separately; CI did execute the full suite and dependency-map script.
- Added `docs/architecture/AST_TEST_INVENTORY.md`. A repository-wide review of the 77 Python test files found three tests that parse/compile function definitions from `navidrome_server.py`: `tests/test_acquisition_safety.py`, `tests/test_quality_priority.py`, and `tests/test_slskd_transfer_lookup.py`.
- Inventory conclusion: transfer-list behavior can move directly to `slskd_transfers.download_transfer_files()`; quality policy has an existing direct implementation in `slskd_quality.quality_tier()`; search helpers have direct implementations in `slskd_search.py`. The acquisition-safety AST harness combines pure helper checks with high-risk lifecycle/concurrency/persistence/recovery behavior and must be migrated in smaller slices without deleting or weakening those cases.
- Classified other `navidrome_server` references as compatibility tests rather than AST source coupling, including lazy API service injection, app-import isolation, Last.fm/ListenBrainz/metadata adapters, slskd adapter contracts, and MCP registry behavior. Those remain valid unless the corresponding compatibility contract changes.
- Updated the roadmap, status, test plan, and architecture doc to point at the inventory and distinguish the pending generated map from completed source-test inventory.
- No test or CI result is claimed yet for this PR. No application behavior was changed; publishing, deployment, and runtime verification are not part of this audit.

## 2026-10-16 — Adopt scripted modularization audit workflow

- Adopted the audit recommendations as a gated workflow rather than treating them as permission for immediate extraction. Added `scripts/dep_map.py`, which emits deterministic AST import edges for repository Python modules and calculates the transitive local import closure from `app.main`; added focused tests for import parsing and local import resolution in `tests/test_dep_map.py`.
- Updated `docs/MODULARIZATION_ROADMAP.md`, `docs/TEST_PLAN.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/PROJECT_STATUS.md`, and `docs/ARCHITECTURE.md`. The sequence is now: generate/review the map; inventory AST/source-reading tests and move behavior coverage to direct imports without weakening safety coverage; establish an allowlist-aware `navidrome_server` app-import guard; then assess settings wrappers and the acquisition coordinator.
- Tightened the coordinator decision to one question: does `_discovery_acquire_album_impl()` contain policy (candidate selection, retry/source-switch thresholds, state transitions) or only orchestration? Keep pure orchestration in place; extract only a demonstrated policy seam.
- The generated `docs/architecture/dependency-map.json` is intentionally not fabricated in this change: it must be produced and reviewed from the exact source revision by running `python scripts/dep_map.py --output docs/architecture/dependency-map.json`.
- No local test commands were run in this session. All four required GitHub Actions workflows passed on the exact final PR head `9fc7059341d13e40ef2a800299f8e6db84c61e59`: Python syntax/acquisition-safety (`38949122909`), Docker packaging/full suite/build (`38949122831`), container runtime smoke (`38949122830`), and non-publishing multi-architecture validation (`38949122845`). PR #245 was squash-merged as `cc2613e1a03e2084f9cbce4febb83a3a24d77600`. No local tests were run separately; no publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — Classics builder boundary audit: no further extraction justified

- Traced `_build_classics_list()` on main at `b9a97b5e37aff297c836d2039763de7b166441ba`. Its only direct production reference is the classics builder registration in the discovery-list dispatch table; that call is an orchestration entry point, not a reusable policy function.
- The builder now composes already-separated responsibilities: `discovery_classics_candidates.collect_classic_candidates()` (candidate collection, normalized duplicate resolution, ownership/eligibility filtering, metadata, pacing), `discovery_classics_ratings.enrich_critical_ratings()` (bounded shortlist enrichment), `discovery_recommendations.score_classic_candidates()` / `refresh_exploration_scores()` / `diversify_classic_candidates()` (ranking and diversity), and `discovery_classics_genres.enrich_classic_genres()` (bounded genre metadata). The provider/cache lookups, inventory snapshot, stage order, jitter, and response envelope are adapter/orchestration responsibilities.
- Direct-import regression suites already exist for the extracted candidate and rating helpers; the genre helper was likewise introduced with direct-import coverage in PR #231. I found no remaining self-contained policy stage in the builder that would improve ownership if moved. Extracting the response dictionary alone would be a mechanical relocation; extracting the whole pipeline would create a broad callback interface and obscure orchestration.
- **Decision:** no application-code PR for classics. Removed this stale candidate from the active roadmap and made the application-assembly / AST-coupled test audit the next action. Acquisition coordination remains conditional and safety-critical.
- This session's work is documentation-only. No application tests or local test commands were run. Required workflow status must be verified on the final documentation PR head before merge. No publication, deployment, or production runtime verification is claimed.

---

## 2026-10-16 — Documentation consolidation

- Re-established canonical document roles: `docs/MODULARIZATION_ROADMAP.md` is the short active plan; `docs/PROJECT_STATUS.md` is the current snapshot; `docs/TEST_PLAN.md` is the verification baseline; `docs/ARCHITECTURE.md` describes current responsibilities; this file remains the primary detailed project history.
- Older extraction/verification sections found in the former diary-style roadmap, test plan, and architecture document that were not represented by PR number here were preserved in `docs/archive/MODULARIZATION_HISTORY.md`. Archived records are historical evidence, not current status; verify current state against GitHub `main` and exact CI runs.
- Updated the workflow to use targeted historical search instead of reading the full log every session.
- The read-only boundary audit found the next candidate should be a trace of `_build_classics_list()` and its tests, followed by an application-assembly/AST-test dependency audit. Acquisition coordinator extraction remains conditional on a narrow safe seam; slskd work is not justified by file size alone. PR #228's audit findings are incorporated here and in the roadmap; the PR can be closed as superseded once this consolidation is reviewed.
- This was a documentation-only change; no application tests or CI have been run yet. No publication, deployment, or runtime verification is claimed.

---

## 2026-10-16 — PR #240 merged: lazy auth-secret provider

PR #240 squash-merged at `78547fd47c1b155255c1da6ef57120b76513a0fc` from exact final tested head `e3542c6a8fa3b2fc3ddf07a0268563ae5946064a`. Extracted lazy, lock-protected signing-secret loading to `app/security/auth_secret.py`, with injected data-directory lookup and existing secret loader; retained `app.main._AUTH_SECRET` for integration-test compatibility. Direct-import tests cover laziness, caching, retry after exceptions/None, and concurrent first use. Initial CI caught the removed compatibility attribute; it was restored and the corrected head passed all four workflows: syntax/acquisition safety `38941505550`, Docker/full suite/build `38941505440`, runtime smoke `38941505508`, and validation-only multi-architecture `38941505516`. Assistant-side local tests were not run. Publishing remains paused; no deployment or production runtime verification claimed.

## 2026-10-16 — PR #236 merged: New Releases lookup construction

- Squash merge: `aaa748f2dfdc307d79faf5397a51dbfbcd75ec6c`; exact tested head: `990e3ddfe08b6b1590860e8fd07d0ac13882be3e`.
- Extracted `discovery_new_releases.build_new_release_lookup()` and added direct-import tests for date-bounded query shape, quote/backslash escaping, and cache-key stability.
- All four required exact-head workflows passed: syntax/acquisition safety `38938238608`, Docker/full suite/build `38938238694`, runtime smoke `38938238678`, validation-only multi-architecture `38938238904` (publishing paused).
- No assistant-side local tests, image publication, deployment, or production runtime verification claimed.

## 2026-10-16 — PR #235 merged: New Releases response projection

- Squash merge commit: `0d77f7d99a89660ea1d9a38635e93343538e93b8`; exact tested PR head: `f3e7ec7c14deac8136b5066011623e00dffca134`.
- Extracted sorting, the 200-item visible cap, the 20-error cap, and response shaping into `discovery_new_releases.build_new_release_response()`. Provider/cache/rate-limit access, date-window policy, candidate selection, and error collection remain in the server adapter.
- Added direct-import tests for newest-first ordering/tie behavior, response metadata, error/item caps, and non-mutation. Docker packaging already included `discovery_new_releases.py`, so no packaging change was needed.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety run `38937239432`; Docker packaging/full unit suite/build run `38937239481`; container runtime smoke run `38937239444`; validation-only multi-architecture image validation run `38937239482` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — PR #234 merged: New Releases global candidate merge

- Squash merge commit `c44ea572354b4714e5e2577f5eb21b091be97cc8`; exact tested PR head `56bb5b6835d03860124f2dbdff4dbb13a813d5c8`.
- `discovery_new_releases.merge_release_candidates()` now owns cross-artist identity merge policy; newest release wins and the existing candidate remains on date ties. Added direct-import tests for precedence, tie behavior, non-mutation, empty inputs, and missing dates.
- All four required workflows passed on the exact final PR head: syntax 38935716487, Docker/full suite/build 38935717026, runtime smoke 38935716420, validation-only multi-architecture 38935716622. Local test commands were not run by the assistant. No image publication, deployment, or production runtime verification claimed.

## 2026-10-16 — PR #233 merged; PR #234 global merge extraction started

- PR #233 merged at `08e20f502e10f829bf9ae7920106b7e8427668eb` from tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`; all four required workflows passed on that exact head (syntax 38934044235, Docker/full suite/build 38934044270, runtime smoke 38934044253, validation-only multi-architecture 38934044237). No local test execution or production verification claimed.
- PR #234 (`extract/new-releases-global-merge`) isolates pure cross-artist identity merging. It preserves the newest candidate per identity and stable existing-winner tie behavior; tests cover newer wins, ties, non-mutation, empty inputs, and missing dates. Exact-head CI pending.

## 2026-10-16 — PR #232 merged: classics candidate collection

- Squash merge commit: `451944c9056eeb50ec7d8b1744bbf435d653b70b`. `discovery_classics_candidates.collect_classic_candidates()` owns candidate collection, normalized duplicate resolution, ownership/eligibility filtering, metadata, and fifth-artist pacing; the server retains library/provider access, scoring, enrichment, diversity, and response assembly.
- The latest four workflow runs inspected for the PR reported success (syntax/acquisition safety, Docker packaging/full suite/build, container smoke, and non-publishing multi-architecture validation). The connector evidence did not independently expose each run's head SHA, so this closeout does not label them exact-head verified. Assistant-side local tests were not run. Publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — New Releases library qualification extraction in progress

The next candidate moves normalized ownership identity construction and full-album artist qualification/sorting into `discovery_new_releases.prepare_new_release_library_scope()`. It preserves the six-track threshold, Various Artists exclusion, stable descending album-count order, all-owned-album identity set, and untruncated qualified count. The adapter retains the 120-artist request cap, date-window policy, MusicBrainz requests/cache/rate limit, error reporting, and global merge. Direct-import contract tests are added. PR #233 is open on tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`. All four required workflows passed on that head: Python syntax/acquisition safety run 38934044235, Docker packaging/full unit suite/build run 38934044270, container runtime smoke run 38934044253, and validation-only multi-architecture validation run 38934044237. Assistant-side local tests were not run. Merge remains pending; publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — PR #231 merged: classics genre enrichment

- Branch: `extract/classics-genre-enrichment`; exact tested head `0856f2a9a91e8b3aff88f933d845b182007997d4`; squash merge `b23d76712a04dcbfc461ceb7245a0676738fca7a`.
- Extracted bounded genre annotation to `discovery_classics_genres.enrich_classic_genres()`; injected Last.fm lookup and family classification remain adapter responsibilities. Added direct-import tests for the limit, order, normalized lookup deduplication, fallback metadata, and invalid limits; added Docker packaging.
- All four required exact-head workflows passed: Python syntax run 1208, Docker packaging/full unit suite/build run 1116, container runtime smoke run 925, and validation-only multi-architecture validation run 969 (publishing paused). Assistant-side local tests were not run.
- No publication, deployment, or production runtime verification. Next: resume the remaining acquisition-coordination boundary audit; do not start broader extractions before reviewing safety and independent testability.

## 2026-10-16 — PR #230 merged: watcher progress accounting

- Branch: `refactor/extract-watcher-progress-accounting`; exact tested head `47fb2a5bb18d4101dde910dd30e5bad2ed13e2e7`; squash merge `57f9776b1b517c7c86119b2a11d7f919b8cab631`.
- Extracted the deterministic byte-counter/progress-timer update into `acquisition_progress_accounting.observe_progress()`; the watcher retains slskd polling, transfer interpretation, stall policy/countdown, source switching, filesystem verification, and import decisions. Added direct-import regression tests and Docker packaging.
- All four required exact-head workflows passed: Python syntax run 1202; Docker packaging/full unit suite/build run 1110; container runtime smoke run 919; validation-only multi-architecture image validation run 963 (`push: false`). Assistant-side local tests were not run.
- No image publication, deployment, or production runtime verification is claimed. Publishing remains paused.

## 2026-10-16 — PR #229 merged: classics critical-rating extraction

- Branch: `refactor/extract-classics-rating-enrichment`; tested head `28c364dca41971ea90667c175663de17b41ca7ab`; squash merge `925eb16cba7d2387cd0a17c7690e36d35f17e8f1`.
- Extracted listener-ranked shortlist and critical-rating enrichment to `discovery_classics_ratings.py`; added five direct-import regression tests, Docker packaging, and documentation updates.
- All four required exact-head workflows passed: Python syntax/acquisition safety run 1194; Docker packaging/full suite/build run 1102; runtime smoke run 911; validation-only multi-architecture run 955. Local test execution was not performed.
- Publishing/deployment remain paused; no runtime deployment is claimed.

## 2026-10-16 — Classics-list rating enrichment extraction implementation notes

- Branch: `refactor/extract-classics-rating-enrichment`, based on GitHub main at `80935c5bc97cc56bc6fd54efc7416c3a2ed6978e`.
- Extracted the critical-rating shortlist/enrichment stage into `discovery_classics_ratings.py`; kept provider/cache access in `_musicbrainz_critical_rating` and retained the surrounding `_build_classics_list()` pipeline.
- Added direct-import regression tests and Docker packaging. Docs updated in status, roadmap, and test plan.
- Final verification and merge are recorded in the subsequent PR #229 closeout entry above. Local test execution was not performed; publishing/deployment remain paused.

## 2026-10-16 — Session closeout: PRs #225 and #226 merged

- **PR #225:** https://github.com/abucalip/navi-librarian/pull/225 — cached discovery-list projection extracted to `discovery_list_payload.build_cached_discovery_list_response()`. Exact tested head `573fe05d31dae422c25188688cd2fa949339e487`; squash merge `4d968b381d1f541b81a4a46d1753b5145347e33d`. Four required workflows passed: syntax/acquisition safety 1187, Docker/full suite (477 tests)/build 1095, runtime smoke 904, validation-only multi-architecture 948.
- **PR #226:** https://github.com/abucalip/navi-librarian/pull/226 — background listening-profile refresh extracted to `listening_profile.refresh_and_persist_background_profile()`. Exact tested head `740979f1b4da4f5c13632ab3598c13bc09ed413e`; squash merge `f5a95338e978a14d01fb6a1c3741e2e6c8bea11c`. Four required workflows passed: syntax/acquisition safety 1189, Docker/full suite (481 tests)/build 1097, runtime smoke 906, validation-only multi-architecture 950.
- Both changes preserve the server adapter/compatibility boundary and include direct-import regression coverage. PR #225's initial test-fixture assertion was corrected before final CI. No independent local tests, publication, deployment, or production runtime verification are claimed.

## 2026-10-16 — PR #224 merged: personal recommendation payload shaping

- PR #224 squash-merged at `f795239589e6dd78f0f5e6d98cf2eadc897d6f49` from exact tested head `6d2e0ccc8d24cd11b727255f171fd405384a8729`.
- Pure personal-recommendation payload projection moved to `discovery_recommendation_payload.py`; the server retains recent-listen count lookup and selection-specific ownership annotations.
- Exact-head CI passed syntax/acquisition safety run 1177, Docker packaging/full suite (473 tests)/build run 1085, runtime smoke run 894, and validation-only multi-architecture build run 938. Assistant-side local tests were not run.
- No image publication, deployment, or production runtime verification. Publishing remains paused.

## 2026-10-16 — Personal recommendation payload projection extraction (in progress)

- Branch `refactor/personal-recommendation-payload`, based on current GitHub main after PR #223. Extracted the base personal-recommendation payload mapping to `discovery_recommendation_payload.py`; selection-specific `ownership_check` / `ownership_note` annotations remain in the adapter.
- Added direct-import tests for legacy fields, defaults, score rounding, category reason text, ListenBrainz-vs-Last.fm score handling, and the three-track limit. Docker packaging includes the new module.
- Tests and exact-head CI have not yet been verified. Next: review the complete diff, open a focused PR, and run all four required workflows on its exact final head.

## 2026-10-16 — PR #223 merged: personal recommendation allocation

- PR #223 squash-merged as `1ccb11485bf1efce3ff201fb7337407c3e668c47` from exact final tested head `b604940e4b7a20160d4f3710b009c6ca718c57c5`.
- Moved shortlist allocation loops into the pure `discovery_personal_allocator.allocate_personal_recommendations()`; the immutable contract keeps candidate identity, ownership classification, quotas, style targets, family cap, and check budget explicit. Server-side payload/diagnostic shaping and Navidrome ownership lookup remain in the adapter.
- Exact-head CI passed all four required workflows: syntax/acquisition safety run 1171; Docker packaging/full suite (468 tests)/build run 1079; runtime smoke run 888; validation-only multi-architecture build run 932. No assistant-side local tests were run.
- The first CI attempt exposed two incorrect test fixture expectations; corrected them before final verification. Also reviewed and preserved the distinct selected/review payload shapes. No image publication, deployment, or production runtime verification.
- Next: refresh GitHub main/open PRs and identify one small, independently testable seam. Publishing remains paused.


## 2026-10-16 — Personal recommendation allocator boundary investigation (pre-integration history)

- PR #221 established the immutable contract, deliberately leaving allocation loops untouched. A follow-up investigation identified the stable tie-order distinction between regional-style reservations and final fallback; `source_order` was added to preserve the legacy behavior.
- This exploratory stage was superseded by PR #223, which integrated the pure allocator through the server adapter, added Docker packaging and policy tests, and passed all four required workflows on exact final head `b604940e4b7a20160d4f3710b009c6ca718c57c5`. See the PR #223 entry above for verification details.
- Publishing/deployment remain paused.



## 2026-10-16 — PR #194 merged: token cleanup and touch targets

- Refreshed PR #194 against current main and merged the reviewed CSS/documentation diff. Exact tested PR head: `0cf2e4329015fd9159213fbe25561decb16dbdb8`; squash merge commit: `10b14c1ed37bfc20930bf642f511065404dfb379`.
- Manual browser report was published by the operator in PR #194 comments for that exact head. All 8 checklist items passed with zero failures: first-run setup, dashboard/artwork, discovery lists, navigation/album details, settings load/save and secret handling, Get/request behavior without a real download, acquisition cards/status, and absence of unexpected browser/server errors.
- All four required workflows passed on the exact tested head: Python syntax run 38900816052; Docker packaging/full unit suite/build run 38900816045; container runtime smoke run 38900816210; validation-only multi-architecture image validation run 38900816039 (`push: false`).
- Scope remained `static/app.css` and `docs/UI_BACKLOG_EXECUTION.md`. Merge is verified; publishing remains paused. No image publication, deployment, or production runtime verification is claimed.
- **Next action:** refresh current main/open PRs/CI and review outstanding work against the requirements and priority order before choosing the next task.

## 2026-10-16 — Session closeout: PRs #208–#210 merged

- **PR #208 — page/asset routes:** merged as `8ed54b0cc3750dc0aae1bc20efda61bba7dd71cd` from exact tested head `75305491eb12ff1796569f51e364aace41796292`. All four required workflows passed (syntax 1121, Docker/full suite/build 1028, runtime smoke 837, validation-only multi-architecture 881).
- **PR #209 — login-gate middleware:** merged as `669379aaed12092b1f826d46e0c3f8675e6ea6eb` from exact tested head `1b248dcb20d7a0f8622f32de6ae0bcfc3e5795ed`. All four required workflows passed (syntax 1123, Docker/full suite/build 1030, runtime smoke 839, validation-only multi-architecture 883).
- **PR #210 — session-cookie policy:** merged as `21cd2bc19e9af66bb155b0d036f3b1f9ffb8d28f` from exact tested head `a394b6ea75fff91fcd4828f1946c14b98bbcf827`. All four required workflows passed (syntax 1125, Docker/full suite/build 1032, runtime smoke 841, validation-only multi-architecture 885).
- Regression tests added for page routes/assets, authentication-gate decisions, and session-cookie security attributes. These are code merges only; publishing, deployment, and production runtime verification are not claimed.
- **Session outcome:** no further extraction started. Next session should refresh GitHub state and read the current requirements/workflow/test-plan/roadmap before choosing another candidate. Keep PR #194 unchanged as previously requested; review other open PRs against current priorities rather than assuming they are ready to merge.

## 2026-10-16 — Independent extraction session: PRs #205 and #207

- **PR #205:** https://github.com/abucalip/navi-librarian/pull/205 — extracted per-artist MusicBrainz release-group candidate filtering to `discovery_new_releases.select_artist_release_candidates()`. Exact tested head `079d355e972ea39d792c1dfa6fca6eab902800e3`; all four workflows passed (syntax 1111, Docker/full suite/build 1018, runtime smoke 827, validation-only multi-architecture 871); squash merge `32b39be400ec046e8310a87260346b1959141609`.
- **PR #207:** https://github.com/abucalip/navi-librarian/pull/207 — extracted Artist Deep Dives score/rank/diversity policy to `discovery_recommendations.rank_and_diversify_deep_dive_candidates()`. Exact tested head `20e565582579f4097eed3803748c87bb3d932a98`; all four workflows passed (syntax 1114, Docker/full suite/build 1021, runtime smoke 830, validation-only multi-architecture 874); squash merge `a5b0d865060c3d069a865be7a1cb43c1a072ae91`.
- Both are backend-only and preserve provider access, cache/rate-limit behavior, legacy server entry points, and MCP response contracts. Direct-import tests added. Assistant-side local test commands were not run; no publication, deployment, live provider integration, or production runtime verification is claimed. PR #206 was superseded and closed before PR #207 was opened from updated main. Acquisition-dismissal HTTP 409 remains deferred; publishing remains paused.


## 2026-10-16 — Independent extraction session: PRs #202 and #203

- **PR #202:** https://github.com/abucalip/navi-librarian/pull/202 — extracted pure library-overview payload shaping to `navidrome_client.library_overview_payload()`; exact tested head `6903f40578f40fec08f1efde92d6577fcaeeced0`, squash merge `7a95364a31f360bb20dd8d2919a9bfea93ec893c`. All four required exact-head workflows passed: syntax 1104, Docker packaging/full unit suite/build 1011, runtime smoke 820, validation-only multi-architecture 864.
- **PR #203:** https://github.com/abucalip/navi-librarian/pull/203 — extracted pure source-preview redaction to `server_source_redaction.redact_assignment()`; exact tested head `14019b8beeca9b71fbb8167117dafea3f60c74ea`, squash merge `89e639394122aebe29bfb8602a1135722ea28bbe`. All four required exact-head workflows passed: syntax 1106, Docker packaging/full unit suite/build 1013, runtime smoke 822, validation-only multi-architecture 866.
- Assistant-side local tests were not run; full unit suites ran in CI. No publication, deployment, or production runtime verification. Acquisition-dismissal HTTP 409 remains deferred; publishing remains paused.


## 2026-10-16 — Navidrome response-shaping extractions (PRs #196 and #198)

- **PR #196:** https://github.com/abucalip/navi-librarian/pull/196 — branch refactor/extract-navidrome-search-shaping; exact tested head 4b501c64c82a69af1805a7f6195b4fc15ef0c836; squash merge 277499ec949353f5f24542a8033a481283814782.
- Extracted pure search-result payload shaping into navidrome_client.search_result_payload(). Kept search validation, API request, JSON formatting, and legacy tool interface in search_music(). Added direct-import tests for per-category output, field filtering, and all-category ordering.
- Exact-head workflows all passed: Python syntax run 1088; Docker packaging/full unit suite/build run 995; container runtime smoke run 804; validation-only multi-architecture build run 848.

- **PR #198:** https://github.com/abucalip/navi-librarian/pull/198 — branch refactor/extract-navidrome-album-details-main; exact tested head a718780edcb85eb8f4453e44a2d5a4925a512314; squash merge 92cdd6309244e78e78bd0f6f8d2e38ea929e434b.
- Extracted pure album/track payload shaping into navidrome_client.album_details_payload(). Kept API access, JSON serialization, and legacy tool interface in get_album_details(). Added direct-import tests for scalar track records and missing fields.
- Exact-head workflows all passed: Python syntax run 1090; Docker packaging/full unit suite/build run 997; container runtime smoke run 806; validation-only multi-architecture build run 850.

- Both changes are backend-only, require no manual UI checklist, and preserve the existing MCP-facing response shapes. The full unit suite was run in the packaging workflows; assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed. PR #197 was closed as superseded before its clean-main replacement PR #198.
- Acquisition-dismissal HTTP 409 remains deferred per explicit user direction. Keep publishing paused.
- Next action: refresh GitHub main/open PRs/exact-head CI and select the next independent low-coupling extraction.
## 2026-10-16 — PR #192 merged: settings tabs and skip-link accessibility

- PR: https://github.com/abucalip/navi-librarian/pull/192
- Supersedes conflicted PR #188, which was closed without merging. Branch: `a11y/refresh-188-from-main`; base main `470b232977b45ee1cf1bf1b399c2c43843062c1f`; exact tested head `75c13b0099285747c9da75c5c3879e6594e5fe36`; squash merge/current main `4fc72001807e0afc40ebc99bf1be9a502f87e0f8`.
- Reapplied four focused changes on current-main files: skip link and main target, accessible names for four settings tab panels, keyboard-operable roving tabindex tabs, and UI backlog evidence. Existing current-main content was retained.
- All four exact-head workflows passed: Python syntax run 1069; Docker packaging/full unit suite/build run 976; container runtime smoke run 785; validation-only Docker image validation run 829.
- User-published manual browser report comment in PR #192 tested the exact head and recorded all checklist items passing with zero failures. No assistant-side local test run, publication, deployment, or production runtime verification is claimed.
- PR #188 closed as superseded after #192 merged. Acquisition dismissal HTTP 409 remains deferred by explicit user direction.
- Next: refresh GitHub main, open PRs, and CI before selecting further work; do not claim deployment or production runtime verification.

## 2026-10-16 — PR #190 merged: artist-biography resolution

- PR: https://github.com/abucalip/navi-librarian/pull/190
- Branch: `refactor/extract-artist-bio-resolution`; exact tested head `6c04d8a67944568a3e2b280deafb4eb2c66c2391`; squash merge `b829fa953d979563a8ace6e5529eace8cb80ac43`.
- Extracted pure biography selection into `app/services/artist_bio.py`, preserving provider I/O, concurrent retrieval, cache ownership, validation, and response schema in `app/api/metadata.py`.
- Direct-import tests cover matching QIDs, mismatched page identity, disambiguation, ranking/filtering, empty payloads, and truncation. All four required workflows passed: syntax 1059, Docker/full suite/build 966, runtime smoke 775, validation-only multi-architecture 819.
- No assistant-side local test execution, publication, deployment, or production runtime verification is claimed.
- PR #190 code merge SHA: `b829fa953d979563a8ace6e5529eace8cb80ac43`; documentation closeout commits followed on main.
- Next: refresh GitHub main/open PRs/CI before selecting another independent extraction.

## 2026-10-16 — Artist-biography resolution extraction opened

- Branch `refactor/extract-artist-bio-resolution`, based on refreshed main `7bfcbebfa66e7d00d20f78e25d8b998b7a617bd0` after PR #189.
- Added `app/services/artist_bio.py` with pure artist-biography resolution from already-fetched Wikidata entities and Wikipedia page payloads. `app/api/metadata.py` still owns provider requests, parallel retrieval, caching, input validation, and the response contract.
- Added `tests/test_artist_bio_service.py`; retained `tests/test_metadata_routes.py` for HTTP routes and provider integration.
- Verification pending on the exact PR head; no assistant-side test execution, merge, publication, deployment, or production runtime verification is claimed.
- Next: inspect the complete diff and all four required exact-head workflows before merge.

## 2026-10-16 — PR #189 merged: dashboard-pick service

- PR: https://github.com/abucalip/navi-librarian/pull/189
- Branch: `refactor/extract-dashboard-pick-service`; exact tested head `d28aaa33f7096ba764232d6bd435cc68d5d85f98`; squash merge/main commit `f5f355f8bdc0599bb240933e248177c7b0517ff5`.
- `app/services/dashboard.py` now owns three-lane dashboard candidate assembly, album eligibility, case-insensitive artist/album deduplication, category balancing, and random fill. The API route retains count validation, the lazy librarian dependency, and the response contract.
- Direct-import service tests added; route tests retained. Exact-head workflows passed: syntax/acquisition safety 1052, Docker packaging/full unit suite/build 959, container runtime smoke 768, and non-publishing multi-architecture validation 812.
- No assistant-side local test run, image publication, deployment, or production runtime verification is claimed. Acquisition-dismissal HTTP 409 remains deferred.
- Process note: a test-file creation omitted the branch argument and briefly committed the new test on main; the file was immediately removed by `039b5ed14834aeb63627f141c1bafa1d96c8589b`, verified absent on main, and then created on the PR branch. The intended file is included in the merged PR.
- Next: refresh GitHub main/open PRs/CI before selecting another independent extraction.

## 2026-10-16 — Dashboard-pick assembly extraction opened

- Branch `refactor/extract-dashboard-pick-service`, based on refreshed GitHub main `2b9eb6a88c752aa1d2e65687641d05629aa89427`.
- `app/services/dashboard.py` now owns dashboard candidate aggregation, case-insensitive artist/album deduplication, album eligibility filtering, balanced category picks, and random fill. `app/api/dashboard.py` remains the HTTP adapter and preserves the endpoint path, count validation, service calls, and response schema.
- Added `tests/test_dashboard_service.py` for direct-import behavior. Existing `tests/test_dashboard_routes.py` remains in place to cover route inventory, injected service calls, sanitized health failures, category balance, filtering/deduplication, and invalid counts.
- Verification is pending until the final PR head. No assistant-side test execution, merge, image publication, deployment, or production runtime verification is claimed.
- Acquisition-dismissal HTTP 409 remains deferred and unchanged.
- Next: open PR, inspect full diff, and wait for all four required workflows on the exact final PR head.
## 2026-10-16 — PRs #186 and #187 merged

- **PR #186 — UI empty-state copy/state kinds:** published local manual report for tested head `0c12a43cd40211d522868dab7caa70c8a5fbf6e6`; all manual checklist items passed, zero failures. All four GitHub Actions workflows succeeded on that exact head (syntax 1041, Docker packaging 948, runtime smoke 757, validation-only image 801). Squash merge `d42618b63f141049d5b0e6558e81174ef5c1418f`.
- **PR #187 — slskd connection probe:** extracted the connection check to `slskd_client.py`, preserved the legacy adapter, added direct-import regressions and Docker packaging. Exact final PR head `920590871883aa8c75c29a1b16131bd88519072d` passed all four workflows (syntax 1041, Docker packaging/full suite/build 948, runtime smoke 757, validation-only image 801). Squash merge `b7ae6458adda3650f178fc64457914beb66ece9c`.
- Assistant-side local tests were not run independently. No image publication, deployment, or production runtime verification is claimed. Acquisition dismissal HTTP 409 remains deferred and unchanged.
- Main tip at closeout: `b7ae6458adda3650f178fc64457914beb66ece9c`.
- Next: refresh GitHub main/open PRs/CI and choose the next low-coupling roadmap extractions; keep publishing paused.

## 2026-10-16 — slskd connectivity probe extraction opened (PR #187)

- Branch: `refactor/extract-slskd-connection-check`; base main `d66257586b69c4cb03641f5ce67050c3f4defd76`.
- Current code head before this log update: `73be3bf8fa1211edff3689bfd1a9c820bf6770d6`.
- Added `slskd_client.py` with an injected config reader/HTTP getter; preserved the legacy MCP/web adapter and response JSON; added `tests/test_slskd_client.py`; updated Docker packaging.
- Exact-head local tests have not been run. CI results are pending/unverified; no publishing, deployment, or production runtime verification is claimed.
- PR: https://github.com/abucalip/navi-librarian/pull/187.
- Next: verify all four exact-head CI workflows and review before merge. Keep the dismissal HTTP 409 deferred and preserve all cleanup safety checks.

## 2026-10-16 — Open-PR refresh after extraction session

- PR #184, `ui: make Artist Deep Dive artist-led and drop its dead controls`, appeared during this session. Its branch `ui/artist-deep-dive` is based on `9f05bed`; comparison against the refreshed main showed it 7 commits behind and one commit ahead of its merge base.
- The PR description explicitly says the required human manual browser checklist is NOT RUN. Treat its automated/browser-agent measurements as separate evidence, not a substitute for the documented human checklist. Do not merge until the branch is refreshed, required exact-head CI is verified, and the human checklist is recorded on that exact head.
- This backend session did not modify PR #184. PR #23 remains the modularization roadmap; PRs #44/#45 remain closed per user direction.

## 2026-10-16 — slskd progress summary and speed estimator extracted (PRs #182–#183)

- **PR #182 — progress summary:** extracted matched-record aggregation into `slskd_transfers.summarize_transfer_progress()`; preserved the legacy HTTP and matching adapters, speed snapshot lock, and response schema. Tested head `045131f58365dd0e6538c1712f37f56f639c65ad`; all four required workflows passed (syntax 1016, Docker/full suite/build 923, runtime smoke 732, non-publishing multi-architecture validation 776). Squash merge `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`.
- **PR #183 — speed estimator:** extracted pure delta-based bytes/second calculation into `slskd_transfers.estimate_transfer_speed()`; snapshot state/identity/locking remain in `navidrome_server.py`. Final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`; all four required workflows passed (syntax 1019, Docker/full suite/build 926 with 342 tests, runtime smoke 735, non-publishing multi-architecture validation 779). Initial test assertion was corrected after CI showed the fixture elapsed 1 second; exact final head passed. Squash merge `e4e9bd1fad9536f00f3908d753b66147d30ca03f`.
- Assistant-side local test commands were not run. No image publication, deployment, or production runtime verification is claimed.
- Acquisition dismissal HTTP 409 remains deferred per explicit user direction. No cleanup behavior was changed and safety checks were not weakened.
- Next action: refresh main/open PRs/CI and choose the next focused, low-coupling extraction.

## 2026-10-16 — Two slskd transfer-boundary extractions merged

- **PR #180 — queue request extraction:** moved the slskd queue POST into `slskd_transfers.queue_download_files()`; retained the dismissal guard and orchestration in `acquisition_orchestration` and `navidrome_server.py`. Exact final tested head `ce0e635cc77c687958d6ad1c1a852e55476c14b2`; syntax run 1008, Docker packaging/full unit suite/build run 915, container runtime smoke run 724, and validation-only Docker image run 768 all succeeded. Squash merge `7c670f2eac838934bc9afa7f40f892ff595ca4ca`.
- **PR #181 — live progress transfer matching:** moved normalized expected/tracked basename matching and duplicate state precedence into `slskd_transfers.match_expected_transfer_records()`; byte/speed calculation and public progress shape remain unchanged. Exact final tested head `cf78b4188a549d6e1b2b98c76a63a6bc0826d129`; syntax run 1010, Docker packaging/full unit suite/build run 917, container runtime smoke run 726, and validation-only Docker image run 770 all succeeded. Squash merge `3df14d3c59bb7e5a689d797028e45468c6a87ee7`.
- Both PRs added direct-import regression tests and preserved compatibility paths. Assistant-side local test commands were not run; the full unit suite ran in CI on each exact final head. Publishing remained paused; no deployment or production runtime verification is claimed.
- Acquisition dismissal HTTP 409 remains deferred per user direction. No change was made to filesystem cleanup or dismissal behavior.
- Next action: refresh main/open PRs/CI and choose the next small seam from the modularization roadmap.

## 2026-10-16 — Last.fm similar-artist parsing extraction merged

- PR #178 merged as `f18574b74a564031c5268cf04c956475d64dc30c`; tested PR head `a97be052d3a1e74843feaacd6403d10ce5aad6af`.
- Moved cached Last.fm similar-artist parsing into `LastFmClient.similar_artists()` and retained the legacy adapter. Added regression tests for response shape/normalization, malformed values, request contract, cache TTL/hits/misses, and adapter delegation.
- Exact-head CI successes: Python syntax check run 1003, Docker packaging validation run 910, container runtime smoke run 719, and Docker image validation with publishing paused run 763. Local full unit suite not independently run; publishing/deployment not performed.
- Next action: refresh GitHub state before selecting another extraction. Acquisition-dismissal HTTP 409 remains deferred by user direction.

## 2026-10-16 — Last.fm similar-artist parsing extraction (in progress)

- Branch: `refactor/extract-lastfm-similar-artists-current`, based on main `86b2ac60416ed725755fc6c57200e1c3123b7606`.
- Extracted cached `artist.getSimilar` response parsing into `LastFmClient.similar_artists()`; `_lastfm_similar_artists()` remains a compatibility adapter. Existing Docker packaging already copies `lastfm_client.py`.
- Added direct-import regressions for scalar/list responses, blank and malformed records, invalid similarity values, request parameters, 60-day TTL/cache behavior, missing/provider-error responses, and adapter delegation.
- PR/CI/merge pending; do not claim tests passed until actually observed. Publishing/deployment remain paused. HTTP 409 investigation stays deferred per user direction.

## 2026-10-16 — Last.fm top albums extraction (PR #175)

- Branch `refactor/extract-lastfm-top-albums`, based on main `4dd8b926a7a6cf76e248420860d7c29c892da3c0`.
- Moved cached `artist.getTopAlbums` response normalization into `LastFmClient.artist_top_albums()` while retaining discovery-specific filtering in `_lastfm_top_albums()`.
- Added direct-import tests and updated architecture/roadmap/status documentation. PR #175 open; exact-head CI pending. No local test, publishing, deployment, or production runtime verification claimed.
- Acquisition dismissal HTTP 409 remains deferred by explicit direction.

---

## 2026-10-16 — Three-extraction session closeout (PRs #170–#172)

- Starting GitHub `main`: `098c5d9d8536070c1115ec2a7c25b99490efb312`. Final code `main`: `d5153a3fe0625bc52b5896e87846b55cabe58e81`.
- **PR #170 — MusicBrainz tag audit.** Branch `refactor/extract-music-tag-audit`; tested head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07`; squash merge `dbbdda35792fd569cfdeec2c4c7b42fc106f84e3`. Extracted a bounded read-only scan into `music_tag_audit.py`, retained the legacy MCP adapter/output contract, added direct-import regression tests, and updated Docker packaging. Exact-head workflows all passed: syntax `38827001217`; Docker/full suite/build `38827001215`; runtime smoke `38827001195`; validation-only multi-architecture `38827001227`.
- **PR #171 — Recommendation style rules.** Branch `refactor/extract-recommendation-style-rules`; final tested head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9`; squash merge `6d00562405320affcb1a04b4359397b332cd5bf5`. Extracted four pure classification helpers into the existing `discovery_recommendations.py`; no Docker file-list change was needed because that module was already packaged. The first CI run caught a mistaken test fixture (the classifier recognizes `Afrobeats`, not `Afrobeat`); the fixture was corrected and final exact-head workflows passed: syntax `38827709662`; Docker/full suite/build `38827709650` (319 tests); runtime smoke `38827709649`; validation-only multi-architecture `38827709610`.
- **PR #172 — Last.fm album popularity.** Branch `refactor/extract-lastfm-album-popularity`; final tested head `d2808d44825e949ff71ed8471d25cee6570b54f1`; squash merge `d5153a3fe0625bc52b5896e87846b55cabe58e81`. Extracted `album.getInfo` transport/response handling into `LastFmClient.album_popularity()`, preserving the old cache key, TTL, timeout, tags/stat normalization, diagnostic strings, and 404 behavior. The first CI run caught a test fixture that did not record the injected HTTP call; the test helper was corrected and final exact-head workflows passed: syntax `38827973048`; Docker/full suite/build `38827972941` (324 tests); runtime smoke `38827972940`; validation-only multi-architecture `38827972938`.
- All three PRs were merged only after the final exact PR-head workflows passed and the changed-file diffs were reviewed. Assistant-side local test execution was not performed. No manual UI tests were required. Publishing remained paused; no image publication, deployment, or production runtime verification is claimed.
- Current open PR inventory after the code merges: only PR #23, the modularization roadmap. PRs #44 and #45 remain closed. The acquisition-dismissal HTTP 409 remains unresolved and deferred until modularization is complete at the user's direction; do not claim a fix or relax filesystem safeguards.
- Next action: review current `main` and the roadmap, then select the next small independent seam. Keep publishing paused.

---

## 2026-10-16 — Two-extraction session closeout

- Starting main SHA `8dbb1e3125d2422e69bb30fa7ecb5bebdf652eed`; final main SHA `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`.
- **PR #167 — listening profile aggregation:** tested head `ca8f9e4b7decb3404c78f1ee8b8d3078815fd71f`; merge `6b656dc7218280aa0d37e738a881061ceefde55e`. All four required workflows passed: syntax `38825137244`, full suite/build `38825137296`, runtime smoke `38825137346`, validation-only multi-architecture `38825137280`.
- **PR #168 — discovery library snapshot:** tested head `fc69943301c5065a54a0128c8b82ae214cd69dd1`; merge `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`. All four required workflows passed: syntax `38825386951`, full suite/build `38825387005`, runtime smoke `38825386785`, validation-only multi-architecture `38825386797`.
- Both extractions retained legacy adapters, added direct-import regressions, and updated Docker packaging. The full unit suite passed in CI for each exact final head. Assistant-side local test commands were not run.
- Only PR #23 remains open as the modularization roadmap. PRs #44 and #45 are closed as requested; dismissal HTTP 409 investigation is deferred until it recurs. Publishing and deployment remain paused/unverified.

## 2026-10-16 — Multi-extraction session: PRs #163, #164, and #165 merged

Three independent integration-client extractions were completed sequentially, refreshing GitHub main after each merge.

- **PR #163 — ListenBrainz client.** Branch `refactor/extract-listenbrainz-client`; tested head `4c494a2679884579df5d6bc204287637e45e2ccd`; merge `7be68c74b8a97ed4d9c50e6a7e22e296b25e79e2`. Added bounded paging with injected clock/client/sleep, compatibility adapter tests, and Docker packaging. All required exact-head workflows passed: compile `38822823853`, unit suite/build `38822823922`, smoke `38822823751`, multi-architecture validation (publishing paused) `38822823989`.
- **PR #164 — Last.fm client.** Branch `refactor/extract-lastfm-client`; tested head `957f3a56afe15e4dd665b041f1fbf7803921d3b6`; merge `9f174c6086c0d2b9749e53e38cbe8e1eb337e22f`. Extracted cached/rate-limited HTTP calls with injected settings/cache/transport/time dependencies. All required exact-head workflows passed: compile `38823469617`, unit suite/build `38823470035`, smoke `38823469896`, multi-architecture validation `38823469762`.
- **PR #165 — MusicBrainz rating client.** Branch `refactor/extract-musicbrainz-rating-client`; tested head `4888bd08fdf05007cc74ad7005a196fd678305b5`; merge `a0cd3d8ff5dcdf6acb7d678c9fc8f1aa0d537629`. Extracted cached release-group rating/year lookup, preserving cache TTL/key, request pacing, 404 caching, and result shape. All required exact-head workflows passed: compile `38823643925`, unit suite/build `38823643703`, smoke `38823643931`, multi-architecture validation `38823643848`.
- The full unit suite and Docker build passed on all three final PR heads. Assistant-side local test execution was not performed. No manual UI testing was applicable. All multi-architecture validation workflows were non-publishing.
- These merges do not indicate image publication, deployment, or production runtime verification; those states remain paused/unverified.

Next: prioritize the outstanding acquisition-dismissal HTTP 409 investigation/diagnostic gate before more routine modularization.

---

## 2026-10-15 — PR #160 merged: discovery refresh orchestration extraction

- PR: https://github.com/abucalip/navi-librarian/pull/160. Exact tested head: `5aafc1a9c5835e2d9e2959a36e7419d09913403a`; squash merge commit: `dba172d5747607e65e8fadd32442b12d32054749`.
- Extracted ordered refresh-all orchestration into `discovery_refresh.refresh_all`; retained `navidrome_server._discovery_refresh_all()` as the compatibility adapter.
- Added regression coverage for callback order, personal count (20), and returned results. The existing module packaging was unchanged.
- All four required workflows passed on the exact PR head: Python syntax `38818349092`, Docker packaging/full unit suite/image build `38818349082`, container runtime smoke `38818349397`, and validation-only Docker/multi-architecture validation `38818349076`.
- MCP registrations, signatures, names, response shapes, provider calls, lock ownership, and persistence behavior remain unchanged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #156 merged: footer placement and accessibility verification

- PR #156: https://github.com/abucalip/navi-librarian/pull/156; exact tested head `47d33cbecadf64ed4b434764883cec6ae99d30bc`; squash merge `c560c28063f26a1a72d7016c951bf265d2ddd158`.
- Manual browser report published in the PR conversation for that exact SHA. All eight manual acceptance checklist items passed, with zero failures. Browser verification measured footer placement/reading order on all eight routes, the `contentinfo` landmark, expected headings, keyboard order, responsive overflow at eight widths, and absence of console/page errors.
- Exact-head CI passed: syntax `38815023255`, Docker packaging `38815023085`, runtime smoke `38815023444`, and validation-only Docker image/multi-architecture validation `38815023661`. Publishing remains paused.
- Limitations: Chromium only; no real screen reader test. The missing skip link remains a separate UI backlog item. No image publication, deployment, or production runtime verification is claimed.
- Session closeout: implementation, manual test, CI, and merge are complete. Next: re-check main/open PRs/CI and prioritize any remaining safety or verification gap before routine modularization.

## 2026-10-15 — Backend session closeout: PRs #155 and #157 merged

- PR #155: expected track-count metadata extracted to `slskd_search.py`; tested head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`; merge `d732241de9edfd3c643a8fa89fb25c42b2a93c67`. All four required workflows passed on that exact head.
- PR #157: slskd transfer listing/normalization extracted to `slskd_transfers.py`; `_slskd_download_transfer_files` retained as the adapter. Tested head `504b10392061dbc44d28d66e663b88cbefb8f1a4`; merge `17922f878f0ea391b47652012a38530e9eb044fc`.
- Exact-head PR #157 CI passed: syntax/acquisition safety `38816375215`; Docker packaging/full unit suite/image build `38816375266`; runtime smoke `38816375339`; validation-only multi-architecture validation `38816375410`.
- A packaging-only Dockerfile commit landed on `main` before the module; PR #157 added the missing module and tests. The current main tree now packages the module and the exact-head Docker build passed.
- Historical next action at the time: complete PR #156's manual browser checklist. This gate was later completed and the PR merged; see the newer closeout entry above. Publishing/deployment/runtime verification remain separate and unclaimed.

## 2026-10-15 — Multi-extraction workflow closeout; PR #149 blocked on UI gate

- PR #154 merged: https://github.com/abucalip/navi-librarian/pull/154; tested head `6de27ec137e9f859424eca0928fca25500852471`; merge commit `b547ff5c647d8bacd8bf17fd6cd760dc9c41980a`. All four required workflows passed on that exact tested head. Publishing/deployment/runtime verification remain separate and were not performed.
- PR #149 was not merged. All four workflows passed on head `600c75475cfbe1d28230345835aee2316519365f`, but the PR explicitly records its required manual browser checklist as NOT RUN, and the branch is 26 commits behind current `main`. Merge remains blocked pending safe branch refresh, exact-head CI, and the required manual UI checklist.

## 2026-10-15 — Standard multi-extraction session workflow (PR #154)

- PR: https://github.com/abucalip/navi-librarian/pull/154; branch: `docs/multi-extraction-session-workflow`.
- Documented the standard multi-extraction process in `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`: target two or three small extractions without quota pressure, default one independent extraction per PR, per-extraction regression and compatibility tests, full-diff review, four exact-final-head CI gates, UI-specific manual verification, sequential merge/refresh, and evidence-based closeout.
- Verification status at this entry: documentation-only; required CI is pending on the final PR head. No application tests, publishing, deployment, or production runtime verification are claimed.

## 2026-10-15 — Music path default policy extraction merged

- PR #151: https://github.com/abucalip/navi-librarian/pull/151; tested head `07cf1ab7dab46a1409236f7134881011dc31cac2`; merge commit `6a7678bd04ef539ae5f4c118b6707524fd569280`.
- Extracted pure music path selection, retained the legacy helper and initialization semantics, added four direct-import regression tests, and updated Docker packaging.
- All four required CI workflows passed on the exact tested head: `38805068326`, `38805068317`, `38805068315`, and `38805068337` (syntax/safety regressions, Docker packaging/full unit suite/build, runtime smoke, validation-only multi-architecture build).
- Publishing remains paused. Deployment and production runtime verification are not claimed.

## 2026-10-15 — PR #150 merged: Navidrome API client extraction

- PR: https://github.com/abucalip/navi-librarian/pull/150. Tested PR head: `be9a2558bd87eb8e7e2fbf25593936aa8c671a1a`; squash merge commit: `efc2acb93e3edb570e77419daa866f4a228c85d2`.
- Extracted Subsonic-compatible authentication, HTTP request execution, and API error interpretation into `navidrome_client.py`. The legacy `navidrome_server.api_call(method, **params)` remains as a compatibility adapter; Docker packaging and direct-import regression tests were updated.
- All four required workflows passed on the exact final PR head: Python syntax `38802307579`, Docker packaging/full unit suite/build `38802307812`, container runtime smoke `38802307700`, and validation-only multi-architecture image validation `38802307683`.
- State: implemented, tested, CI passed, merged. Image publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next: continue with the smallest remaining application-assembly/domain-service boundary after reviewing current main and open PRs; preserve the legacy MCP interface until retirement is separately justified and verified.

## 2026-10-15 — Navidrome API client extraction: pre-merge record

- Branch: `refactor/extract-navidrome-api-client`.
- Extracted the Subsonic-compatible request transport and authentication from `navidrome_server.py` into `navidrome_client.py`, leaving `api_call(method, **params)` as a compatibility adapter.
- Added direct-import regressions and included the new module in Docker packaging.
- Initial exact implementation head `555da7027ae0aa9f636ba66e18b33d549cd787d6` passed all four required workflows: syntax `38802076122`, Docker packaging/full suite `38802076327`, container runtime smoke `38802076229`, and validation-only multi-architecture validation `38802076245`. The subsequent documentation-only updates require a fresh exact-final-head CI check. PR #150 is open; merge, publication, deployment, and production runtime verification remain pending.

## 2026-10-15 — PR #148 merged

- Merged metadata-cache service extraction to `main` via squash merge commit `99e8da326fb0e2c4a8cf22acf9000e28647ec20f` (PR head `972376953444502fb1a372648adc8c58157403c9`).
- All four required PR-head workflows passed on the exact final head: Python syntax/acquisition safety, Docker packaging and full unit suite, isolated container runtime smoke, and validation-only multi-architecture Docker build.
- Publishing remains paused; no image publication, deployment, or production runtime verification is claimed. Next modularization step: inspect remaining application-assembly and domain-service dependencies in `navidrome_server.py` and choose the smallest seam consistent with the roadmap.

## 2026-10-15 — Metadata cache extraction CI follow-up

- Initial PR-head CI exposed a regression-test fixture issue: the malformed-JSON test inserted directly before creating the cache table. The fixture now initializes the table through the public cache service before inserting malformed JSON.
- Corrected test commit: d6e28b665a3b16cbd3aba68744e1943a73d1cda1. All required workflows must be rechecked on this exact updated head; the initial failed run is not evidence of a passing suite.

## 2026-10-15 — Metadata cache service extraction in progress

- The persistent MusicBrainz metadata cache is being moved behind metadata_cache.py with an injected database path and clock. navidrome_server.py retains _metadata_cache_get / _metadata_cache_set compatibility adapters and the existing SQLite filename and non-fatal cache-failure behavior.
- Direct-import regressions cover Unicode JSON round-trips, missing/expired entries, malformed cached JSON, and storage errors. Docker packaging includes the new module.
- Branch: refactor/extract-metadata-cache. CI, merge, publication, deployment, and runtime verification are pending; do not infer them from the code or documentation changes.

## 2026-10-15 — PR #147 merged: slskd settings boolean validation

- Audited the settings API and identified that `PUT /api/settings/slskd` silently dropped `auto_acquire_for_me`; unvalidated forwarding could cause string truthiness to enable a setting unintentionally.
- Added strict JSON-boolean validation, explicit boolean forwarding, omission preservation, and regression tests for accepted and rejected values.
- PR #147 merged by squash. Tested head: `22db7e7b4414f1ff3df7440bc47aece41bf0ae1d`; merge commit: `9ce0ae37ae207f79180d98b10f71147736fe2a75`.
- All four required PR-head workflows passed: syntax, container runtime smoke, Docker packaging, and Docker image validation. Image publication remains paused. No deployment or production runtime verification claimed.



## 2026-10-15 — Data-directory resolution extraction started

- Branch: `refactor/extract-data-directory-config`.
- Added `data_directory.py` as a pure resolver for `NAVIDROME_LIBRARIAN_DATA_DIR` and the legacy source-directory fallback. `navidrome_server.py` retains `DATA_DIR` and the existing directory-creation side effect; no persistence logic or MCP-facing API was moved.
- Added `tests/test_data_directory.py` for configured path expansion, empty setting fallback, and missing setting fallback. Updated Docker packaging to include the module.
- Implementation commits: `b46adec455eb2a889df523591a1c454f7200e805`, `7eaadcc7e3c88119f16101e4b6e2217948ab8edc`, `c4eecffc46fc312c5949c56043acfb0abdcb7e49`, `a5ff011456e05ce98a81c17074732ce81f7b4a39`.
- Verification, PR, merge, publishing, deployment, and production runtime status are pending; do not infer success from the changes being committed.


## 2026-10-15 — PR #152 merged: data-directory resolution extraction

- PR #152: https://github.com/abucalip/navi-librarian/pull/152; tested head `756ef13f6946299e2eacccbf5f9a55ebaf092aae`; squash merge commit `567409bb90f240667575a3730976e4c52676bc02`.
- Extracted configured/fallback data-directory resolution to `data_directory.py`; retained the legacy `DATA_DIR` symbol and directory-creation behavior. Added three direct-import regression tests and updated Docker packaging.
- All four required exact-head workflows passed: syntax `38807325467`; Docker packaging/full suite/build `38807325564`; runtime smoke `38807325555`; validation-only multi-architecture image validation `38807325557`.
- Merged and CI-verified. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next action: review current main, open PRs, and the modularization roadmap to select the next smallest safe dependency seam.


## 2026-10-15 — PR #149 merged: recommendation-count accessibility fix

- PR #149: https://github.com/abucalip/navi-librarian/pull/149; exact tested head `c71d28e74bbdfadbedef4ec3e30fdba5181feb5a`; squash merge commit `f3ac971e6c04b9c9caa8d4d20f50d0c25302556e`.
- Brought the original PR branch up to current GitHub main without force-pushing. Made the recommendation count readable at 13px in the body font, retained stable numeric figures with `tabular-nums`, and assigned `role="status"` to its polite live region.
- Reviewed the three-file diff: `app/templates/index.html`, `static/app.css`, and `docs/UI_BACKLOG_EXECUTION.md`.
- Manual browser report published by the operator for the exact final tested head; checklist reports zero failed items. All four required GitHub Actions workflows passed on that same SHA: syntax, runtime smoke, Docker packaging/full unit suite/build, and validation-only multi-architecture image validation.
- Merged after both the exact-head CI and manual verification gates passed. Image publishing remains paused; no deployment or production runtime verification claimed.
- Next session: inspect current main, open PRs, and the modularization roadmap before choosing the next smallest safe application-assembly/domain-service seam.


## 2026-10-15 — Focused verification audit before modularization

- Audited GitHub main, recent commits, open PRs, exact-head check-runs, requirements, workflow, test plan, modularization roadmap, and UI backlog. Main at audit was `678bfa001181d53190004d1c437b1344225082cf`; all four required workflows passed on that exact SHA (syntax `38818751753`, Docker packaging/full suite/build `38818751792`, runtime smoke `38818751871`, validation-only multi-architecture `38818751791`).
- Open PRs are stale relative to main: #23 is 341 commits behind, #44 is 259 behind and has no exact-head check runs, and #45 is 256 behind despite four older successful checks on its own head. No stale PR was merged or modified during this audit.
- Kept the acquisition dismissal HTTP 409 investigation deferred as directed. PR #44 remains draft diagnostics only; it is not a verified fix. Publishing/deployment/runtime verification remain separate and paused.
- Highest-priority next gap: automated regression coverage for ACQ-01/02/03 Get/request and Dismiss UI state transitions, while retaining backend ACQ-04/06 safe-cleanup tests. Acceptance criteria are specified in `docs/TEST_PLAN.md`. UI automation must mock acquisition API calls and never delete production files; complete manual browser verification against the exact final PR-head SHA after CI passes.
- Audit documentation only. No app code/tests were changed or run in this session. The next action is to implement this single focused regression-coverage task, not another routine backend extraction.


## 2026-10-16 — Acquisition Get/request and Dismiss regression coverage (in progress)

- Started branch test/acquisition-get-dismiss-regressions from current GitHub main following the verification audit.
- Added source-contract tests for Get's no-navigation/one-request behavior, pending/requested/retryable state transitions, and Dismiss visibility, successful card removal, and refusal/error handling. Added API adapter tests for successful Dismiss mapping and required artist/album validation.
- Existing destructive-cleanup regressions remain unchanged and required; no safety validation or production data was altered.
- Automated execution and exact-head CI have not yet been verified. UI tests are source-contract assertions, not browser execution; the manual checklist remains required after CI. No live slskd, production deletion, image publication, deployment, or runtime verification is claimed. The reported HTTP 409 remains deferred unless it recurs.


## 2026-10-16 — Last.fm artist tags extraction started

Started from GitHub main `ffa2b441e7543b2778d1835cfc42386e53c37225`. Moving cached `artist.getTopTags` response normalization into `LastFmClient.artist_genres()` while preserving `_lastfm_artist_genres()` as the compatibility adapter. Added direct-import and adapter regression cases. The initial CI run caught a test-fixture logging error because the custom fake HTTP function did not record its call; corrected the fixture in a follow-up commit. Final-head CI and merge are pending. No local tests, publication, deployment, or production runtime verification are claimed. The acquisition dismissal HTTP 409 remains deferred until modularization is complete.


## 2026-10-16 — Modularization session closeout: Last.fm extraction pair

- PR #174, `refactor: extract Last.fm artist tag parsing`, merged at `4dd8b926a7a6cf76e248420860d7c29c892da3c0` from exact tested head `08c260e2a166a744bbde4009196b53d238afb647`. Cached `artist.getTopTags` retrieval and normalization moved to `LastFmClient.artist_genres()`; legacy adapter remains.
- PR #175, `refactor: extract Last.fm top album parsing`, merged at `f922631e0393063bde02b1e0bd93d30b2d38bd2a` from exact tested head `6b5e32b1144e9f3517247110ea4383b287ce33f4`. Cached `artist.getTopAlbums` retrieval and response normalization moved to `LastFmClient.artist_top_albums()`; legacy adapter retains discovery eligibility filtering.
- Exact-head CI for PR #175 passed: Python syntax (run 38829855110), container runtime smoke (38829855100), validation-only multi-architecture image validation (38829855093), and Docker packaging/full suite/build (38829855077). PR #174's final-head checks also passed after correcting a fake-HTTP test fixture.
- Both extractions preserve legacy entry points and include direct regression coverage. No assistant-side local test run, image publication, deployment, or production runtime verification is claimed.
- Publishing remains paused. Acquisition dismissal HTTP 409 remains deferred by explicit instruction.
- Next action: on the next session, refresh GitHub main and open PRs, reread the required project workflow/testing/roadmap docs, and choose the next smallest safe extraction.


## 2026-10-16 — Two modularization extractions merged (PRs #193 and #195)

- PR #193: `musicbrainz_album_year.py` now owns exact MusicBrainz release-year lookup, artist-credit/title matching, request pacing, and positive/negative caching. The metadata route retains its compatibility adapter and response behavior. Tested head `2b426587e6cb4dc011c85099021041d9f9450744`; squash merge `bce1e32b4ca4c2df86f51dd6102931ed8299dcfe`.
- PR #195: `acquisition_candidate_queue.py` now owns pure normalization/validation for reviewed slskd file records and quality summaries. The legacy adapter retains network I/O, response mapping, and watcher startup. Tested head `f60d682b2ebcd94ecfbcfd0b4beb77c628643fc5`; squash merge `5629d259468a0f748fb5d3fdb78819a0fb00d73c`.
- All four required exact-head workflows passed on each tested SHA. PR #193: syntax/acquisition safety `38881961573`, Docker packaging/full suite/build `38881961574`, runtime smoke `38881961553`, validation-only multi-architecture `38881961580`. PR #195: syntax/acquisition safety `38882195745`, Docker packaging/full suite/build `38882195774`, runtime smoke `38882195700`, validation-only multi-architecture `38882195820`.
- No assistant-side local test execution, publication, deployment, or production runtime verification is claimed. Acquisition dismissal HTTP 409 remains deferred.
- Next: refresh main and open PRs/CI, then continue the remaining acquisition lifecycle/orchestration seams.


## 2026-10-16 — Acquisition progress snapshot extraction completed (PR #199)

- PR #199 squash-merged at a18889b7aa45dd8ef0a9e99a12236cedf5ed5a41 from exact tested head f7157cb28d5e753a97bb9c24eea209b767d74066.
- acquisition_progress_snapshots.py now owns the per-process, per-acquisition byte-snapshot map and lock. navidrome_server.py retains live slskd polling and compatibility behavior; the manager delegates speed math to slskd_transfers.estimate_transfer_speed.
- Direct-import regressions cover first/next samples, identity isolation, and retaining the current sample if the estimator raises. All four exact-head workflows passed: syntax/acquisition safety run 1096; Docker packaging/full suite/build run 1003; runtime smoke run 812; validation-only multi-architecture run 856.
- Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Acquisition search diagnostics extraction completed (PR #200)

- PR #200 squash-merged at 9b3cf481a46282d2f980709091d57aea36144029 from exact tested head b74f6a3f4f8290d6e8d7123399185e9692dd053c.
- acquisition_search_diagnostics.py now owns the bounded candidate diagnostic projection, recognized audio-file count, and no-match explanation. Search execution, path-match diagnostics, persistence, queueing, and JSON/API serialization remain in navidrome_server.py.
- The first CI attempt exposed a compatibility issue in the AST-based acquisition safety test harness: its extracted function namespace did not include a module-level helper alias. The import was moved into the function, preserving production behavior and allowing the legacy test harness to execute it. The exact final head passed all four workflows: syntax/acquisition safety run 1099; Docker packaging/full suite/build run 1006; runtime smoke run 815; validation-only multi-architecture run 859.
- Direct-import tests cover diagnostic field projection and 10-item cap, copied quality summaries, recognized audio extensions, and no-match message/query ordering. Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Independent extraction session closeout: PRs #199 and #200

- PR #199 extracted thread-safe acquisition progress snapshots; exact tested head f7157cb28d5e753a97bb9c24eea209b767d74066 passed all four required workflows and merged as a18889b7aa45dd8ef0a9e99a12236cedf5ed5a41.
- PR #200 extracted slskd search diagnostic shaping; after correcting the AST-test import seam, exact tested head b74f6a3f4f8290d6e8d7123399185e9692dd053c passed all four required workflows and merged as 9b3cf481a46282d2f980709091d57aea36144029.
- Both are backend-only. No local test run, live slskd operation, publication, deployment, or production runtime verification is claimed. Acquisition-dismissal HTTP 409 remains deferred.


## 2026-10-16 — PR #213 merged: Deezer album-matching policy

- Extracted catalog-name normalization, exact artist+album matching, release-year validation, and artwork relevance scoring from `app/api/metadata.py` into pure `app/services/deezer_album_matching.py`.
- The metadata router retains HTTP validation, provider requests, cache behavior, response shapes, tracklist retrieval, and transient-provider failure handling. Docker already packages the helper through `COPY app/ ./app/`.
- Added direct-import regressions for punctuation/case normalization, exact two-field identity, empty names, plausible release years, and unchanged artwork score weights. Existing metadata-route regressions remain.
- PR #213 final tested head: `8760f068b9ab0e28f8a578d1b39bf326010d6fbb`. All four required workflows passed on that exact head: Python syntax run 1131, Docker packaging/full unit suite/build run 1038, container runtime smoke run 847, and validation-only multi-architecture image validation run 891 (`push: false)).
- Squash merge: `c8d82c227ca7bac22feaf03e0f61b12bbe3ae88e`. Assistant-side local tests were not run independently. No image publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — PR #214 merged: Deezer tracklist shaping

- Extracted pure track-row-to-response shaping into `app/services/deezer_tracklist.py`; `app/api/metadata.py` retains provider I/O, matching, response assembly, and error handling.
- Direct-import tests cover track numbering/fallback, title trimming/filtering, missing durations, and invalid numeric conversion.
- Exact tested head `59c8d13ba57930400675e4f9ff90ccba919b63aa`; all four workflows passed: Python syntax run 1144, Docker packaging/full suite/build run 1051, container runtime smoke run 860, and validation-only multi-architecture validation run 904.
- Merged at `51c4e03ac3a65cd74a25c6aced897bfa4d74a989`. No publication or deployment.

## 2026-10-16 — PR #215 merged: Discover recommendations control hierarchy

- Front-end-only layout change separates recommendation request inputs from result-refinement controls without changing JavaScript behavior or API contracts.
- Exact tested head `e8d2e2d462092dcf8cc92beffaa33181aa6758bc`; all four required workflows passed: syntax run 1143, Docker packaging/full suite/build run 1050, container runtime smoke run 859, validation-only multi-architecture validation run 903.
- The operator completed the manual browser checklist and published the report before merge. Merge commit `7317a006e495099fbb733d8d73e425396ec1eaa4`. No publication or deployment.

## 2026-10-16 — PR #216 merged: Deezer artwork selection

- Extracted pure album-artwork relevance selection/payload shaping and exact-artist photo fallback shaping into `app/services/deezer_artwork.py`. `app/api/metadata.py` retains request sequencing, cache ownership, provider-failure/retry behavior, and HTTP validation.
- Added direct-import tests for relevance threshold, best candidate, resolution preference, HTTPS normalization, release-year handling, exact artist identity, missing photos, and empty results; route regressions cover album selection and artist-photo fallback.
- Exact final tested head `aa1099e8ed43b9afcce483a50be31226a66218f4`; all four workflows passed: Python syntax run 1148, Docker packaging/full suite/build run 1055, container runtime smoke run 864, and validation-only multi-architecture image validation run 908. Assistant-side local tests were not run.
- Squash merge commit `ad61b1b91a5c351a73c02e37d7639bc47c61a52f`. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — PR #217 merged: Deezer matched album payload shaping

- Extracted the pure projection of a matched Deezer album row into `app/services/deezer_album_details.py`. The metadata route retains provider requests, exact matching, tracklist retrieval, error handling, and endpoint response assembly.
- Direct-import tests cover cover-size preference, HTTP-to-HTTPS normalization, release-year parsing, and missing fields; the route regression asserts the existing artwork field.
- Exact final tested head `b631f4c6367c68357cbd91f75b986770edfeee0e`; all four workflows passed: Python syntax run 1151, Docker packaging/full suite/build run 1058, container runtime smoke run 867, and validation-only multi-architecture image validation run 911. Assistant-side local tests were not run.
- Squash merge commit `37f04d0a863f69f5596f6a46406cc8bd64bde039`. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — PR #218 merged: exact Deezer release-year selection

- Extracted the pure rule that returns the first plausible year among exact artist+album matches into `exact_album_release_year()` in `app/services/deezer_album_matching.py`. Provider requests and the `MusicBrainz`-first response contract remain in the metadata route.
- Direct-import regressions cover skipping non-exact/invalid-year results and preserving result order; a route-level regression covers the Deezer fallback source/year contract.
- Exact final tested head `0293e4fe4eab7dd66dc82280720183dab3b913ed`; all four workflows passed: Python syntax run 1153, Docker packaging/full suite/build run 1060, container runtime smoke run 869, and validation-only multi-architecture image validation run 913. Assistant-side local tests were not run.
- Squash merge commit `6dc6adae89169638da9a158c79ccee5d2e1ddfb7`. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — Modularization session closeout: PRs #216–#218

- **PR #216 — Deezer artwork selection:** exact final tested head `aa1099e8ed43b9afcce483a50be31226a66218f4`; syntax 1148, Docker/full suite/build 1055, runtime smoke 864, validation-only multi-architecture 908 all passed; merge `ad61b1b91a5c351a73c02e37d7639bc47c61a52f`.
- **PR #217 — matched Deezer album payload shaping:** exact final tested head `b631f4c6367c68357cbd91f75b986770edfeee0e`; syntax 1151, Docker/full suite/build 1058, runtime smoke 867, validation-only multi-architecture 911 all passed; merge `37f04d0a863f69f5596f6a46406cc8bd64bde039`.
- **PR #218 — exact Deezer release-year selection:** exact final tested head `0293e4fe4eab7dd66dc82280720183dab3b913ed`; syntax 1153, Docker/full suite/build 1060, runtime smoke 869, validation-only multi-architecture 913 all passed; merge `6dc6adae89169638da9a158c79ccee5d2e1ddfb7`.
- All three PRs added direct-import regression coverage and preserved route/provider/cache ownership. Assistant-side local test commands were not run; the Docker packaging workflows ran the full unit suite. No publication, deployment, or production runtime verification is claimed.
- Publishing remains paused. Acquisition-dismissal HTTP 409 remains deferred per user direction; no acquisition/import/deletion semantics were changed.
- **Next action:** refresh GitHub main/open PRs/CI and inspect remaining application-assembly/domain-service boundaries before selecting the next independent seam. Do not treat extraction count as a quota.

## 2026-10-16 — Personal recommendation allocation contract designed (pre-extraction)

- Based on GitHub main `9376d5f0d55815067aeb5cadf9015b4b775a9848`, traced `recommend_new_music()` and its policy loops. Added branch `refactor/personal-allocation-contract` with `discovery_allocation_contract.py`, `tests/test_discovery_allocation_contract.py`, and `docs/PERSONAL_RECOMMENDATION_ALLOCATION_CONTRACT.md`.
- Contract inputs are immutable prepared candidate records with stable IDs and precomputed ownership classification, plus explicit count/targets/caps. Contract output uses ordered candidate IDs and explicit decision diagnostics; adapter remains responsible for payload construction. No callbacks, provider/library access, or shared mutable counters.
- The selection loops are intentionally untouched. Contract tests are interface tests, not proof of allocation behavior. Focused execution and exact-head CI are pending. No publishing/deployment/runtime verification.
- Next: verify this contract PR; only if it passes and the seam stays independent, move the actual loops in a subsequent focused PR with policy parity regressions.

## 2026-10-16 — PR #221 merged: personal recommendation allocation contract

- Branch `refactor/personal-allocation-contract`; exact tested head `9d17a0ef32782db35b19b5226d3b8c052f8775d6`; squash merge/current main at merge `820556799fa9d3ec663e5117b36c68084281b20a`.
- Added immutable data-contract types, direct-import interface tests, and contract documentation. The four required exact-head workflows passed: syntax run `38916419736`, Docker packaging/full unit suite/build `38916419709`, runtime smoke `38916419958`, validation-only multi-architecture `38916419701` (`push: false`). Assistant-side local tests were not run independently; CI packaging ran the unit suite.
- This was a contract-design stage, not the allocation extraction. Selection loops, public signature, response construction, and provider/library operations remain unchanged. No publishing, deployment, or production runtime verification.
- Next: if the interface still fits once policy behavior is mapped to it, make the actual allocator a separate PR with comprehensive policy-parity tests. Do not add callbacks/shared mutable state to force the extraction; refine or stop if the boundary proves inadequate.



## 2026-10-16 — PR #233 merged: New Releases library qualification

- PR #233 merged to `main` from exact final PR head `2512a638001e922f5c507994b2f1e667bab9615a`; squash merge commit `08e20f502e10f829bf9ae7920106b7e8427668eb`.
- Extracted `prepare_new_release_library_scope()` to `discovery_new_releases.py`, with direct-import tests for the six-track full-album threshold, Various Artists/blank-name exclusions, stable descending album-count order, and normalized owned-album identities. Provider/cache/rate-limit operations, date policy, adapter cap, error reporting, and candidate merging remain in the adapter.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety run `38934216294`; Docker packaging/full unit suite/build run `38934216395`; container runtime smoke run `38934216347`; validation-only multi-architecture build (`push: false`) run `38934216280`.
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed; publishing remains paused.
- **Next action:** refresh GitHub main, open PRs, docs, and CI, then select the next independently testable remaining roadmap boundary. Do not treat extraction count as a quota.


## 2026-10-16 — PR #237 merged: New Releases date-window policy

- Merged PR #237; merge commit `2d11e52b78004ee51a6ce70a6a6ac6c2b451f397`, tested PR head `8d42c9f5f320fd7b4c0653fa09da8eda12f03f78`.
- Extracted deterministic 730-day cutoff/year-bound calculation into `discovery_new_releases.new_release_window(today)`; added direct-import cutoff and leap-day regressions.
- All four required workflows passed on the exact PR head: syntax `38938867862`, Docker packaging/full unit suite/build `38938867879`, container runtime smoke `38938867737`, validation-only multi-architecture image validation `38938867550` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — PR #238 merged: New Releases provider lookup

- Squash merge commit: `59430bba44bd32a9dfbbe51f19c3e2e8a1441c13`; exact tested PR head: `a26614489d1407792ba959461537f4e8d87fee06`.
- Extracted the cache/read-through MusicBrainz request into `discovery_new_releases.fetch_artist_release_groups()`. The server adapter retains artist iteration, the pacing decision, query construction, candidate selection/merging, and response assembly.
- Direct-import regressions cover cache hits, request parameters/timeout, pacing, cache writes, malformed payload normalization, and safe error-type reporting.
- All four required workflows passed on the exact PR head: Python syntax run `38939659986`; Docker packaging/full unit suite/build run `38939659632`; container runtime smoke run `38939659664`; validation-only multi-architecture image validation run `38939660017` (publishing paused).
- No assistant-side local test commands were run independently. No image publication, deployment, or production runtime verification is claimed.
- **Next action:** refresh main and inspect the remaining acquisition lifecycle/application-assembly boundaries before choosing another independently testable extraction.


## 2026-10-16 — Authentication configuration predicate extraction (PR #239 merged)

- Isolated the pure three-field owner-auth configuration check in `app/security/auth_configuration.py`; `app/main.py` retains the settings read and compatibility wrapper.
- Added direct-import regressions for complete credentials, each missing/empty required field, absent settings, and unrelated keys. Existing truthiness semantics are intentionally preserved.
- Scope is limited to application assembly policy; no routes, cookies, session behavior, persistence, or auth-secret handling changed.
- All four required workflows passed on the exact final PR head: Python syntax `38940305016`; Docker packaging/full unit suite/build `38940304930`; container runtime smoke `38940304907`; validation-only multi-architecture image validation `38940305045` (publishing paused). Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Auth settings reader extraction (PR verification pending)

The lazy persisted-settings read used by authentication now delegates through `AuthSettingsReader`, with `app.main._auth_settings()` retained as the compatibility adapter. Direct-import regressions cover fresh reads (no caching) and propagation of settings-store failures. Verification and merge remain pending until focused/full tests and all four required workflows pass on the exact final PR head. Publishing remains paused.


## 2026-10-16 — PR #250 merged: pure-helper test decoupling

- Starting from GitHub main after PR #249, migrated `tests/test_quality_priority.py` away from AST extraction: quality tier assertions call `slskd_quality.quality_tier()` directly, and legacy quality-order migration uses `SettingsPersistence` directly. The UI source-contract assertions remain unchanged.
- In `tests/test_acquisition_safety.py`, pure slskd search/path/candidate/quality helper bindings now point to `slskd_search.py` and `slskd_quality.py` implementations rather than compiling those wrappers from `navidrome_server.py`. The AST harness remains for acquisition lifecycle/orchestration behavior, preserving concurrency, persistence-before-import, incomplete recovery details, dismissed-job reactivation, and stale watcher recovery tests.
- Updated the AST inventory, roadmap, and status to distinguish completed-on-branch pure-helper decoupling from the still-pending lifecycle AST removal. No application production code changed.
- Branch: `test/migrate-acquisition-pure-helpers`; PR #250 squash-merged as `c71a330ee6b5d44595c0c70299e8a61a45b15ab4` from exact final tested PR head `b14b63194da7f06737d3bc3d8c70bc3e4bc64e53`. All four required workflows passed on that exact head: Python syntax/acquisition safety and dependency map (`38955482760`), Docker packaging/full unit suite/build (`38955482766`), container runtime smoke (`38955482782`), and validation-only multi-architecture image validation (`38955483052`, publishing paused). No assistant-side local test execution was performed. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Migrate acquisition request lifecycle tests to the production coordinator

- Traced the lifecycle test cases in `tests/test_acquisition_safety.py` to their actual owner, `acquisition_request_coordinator.acquire_album_request()`, which is the function used by the legacy `discovery_acquire_album()` adapter.
- Changed duplicate-request concurrency, incomplete saved-download recovery refusal, dismissed-job reactivation, failed reactivation refusal, and stale-download watcher recovery tests to invoke the extracted coordinator directly with injected state. The coordinator remains responsible for the real reservation, response, and recovery decisions; the tests no longer execute the AST-compiled legacy wrapper for these cases.
- Retained the broader-search orchestration test and the import-status persistence guard in the AST harness: these still exercise behavior owned by the legacy search implementation/import adapter, and no equivalent extracted owner currently represents the full tested behavior. Existing assertions were not removed or weakened.
- Updated `docs/architecture/AST_TEST_INVENTORY.md`, `docs/MODULARIZATION_ROADMAP.md`, and `docs/PROJECT_STATUS.md` to reflect the remaining boundary accurately.
- Branch: `test/direct-import-acquisition-lifecycle`, based on GitHub main `d5e3b77aded4f32cd2d188598747b9dac820a9e6`. Tests were not executed in this authoring environment; verify focused and full suite plus all four required workflows on the exact final PR-head SHA before merge. No merge, publication, deployment, or runtime verification is claimed.


## 2026-10-16 — Adopt recommendation and operational-surface audit

- Added `recommend_new_music()` to the active roadmap as a major live responsibility (audit estimate: about 1,058 lines, roughly lines 282–1340). The required order is deterministic fake-provider characterization first, inventory-overlap review against `discovery_library_snapshot.py`, then extraction of provider-injected candidate gathering while preserving route/MCP compatibility and existing allocator/payload modules.
- Added a measurable CI size-ratchet task for `navidrome_server.py` and recorded top-level-function limits. The audit estimate of 3,514 server lines must be verified against the exact current main SHA before it becomes a threshold; limits need explicit, temporary exceptions and pass/fail tests.
- Flagged MCP-exposed `restart_server` and `apply_server_patch` as an owner decision, not an automatic refactor. No authorization or exposure decision is assumed. If retained after owner approval, the roadmap calls for a dedicated ops module and tests for unique-match rejection, no-op on mismatch, and occupied-port/restart failure.
- Added an explicit audit of mutable `MUSIC_DIR` before settings-wrapper work, and a concise line-referenced policy-vs-orchestration decision for `_discovery_acquire_album_impl()`.
- Updated workflow guidance to allow independent audit gates to run as separate concurrent PRs only when dependencies and file overlap have been checked. Each still requires exact-head verification and documented evidence.
- This documentation change does not modify application behavior or make the product decision about the operational MCP tools. Test/CI, merge, publishing, deployment, and runtime status must be recorded after PR verification; none is claimed here.


## 2026-10-16 — Enforce app-to-legacy-server import boundary (PR #254)

- Initial implementation and branch notes are superseded by the final verified merge record below. PR #254 ultimately passed all four required workflows on final head `908783f0a46618c53e4f3e4c4dcf298ec33850fc` and merged as `8bfd6a57179aec46a672343745b494dff60fec02`.
- No assistant-side local tests ran. Publishing, deployment, and production runtime verification were not performed.


## 2026-10-16 — Enforced app-to-legacy-server import boundary (PR #254 merged)

- Added `scripts/check_app_legacy_imports.py` to reject direct `navidrome_server` imports from `app/` except the narrowly allowlisted lazy import inside `app/api/dependencies.py:get_librarian()`. Added regression tests for the allowed adapter, module-level imports, wrong paths/functions, `from` imports, submodule imports, and unparsable source. Wired the guard and compile checks into `.github/workflows/python-syntax.yml`.
- Final PR head `908783f0a46618c53e4f3e4c4dcf298ec33850fc` passed all four required workflows: Python syntax/acquisition safety (`38959799724`), Docker packaging/full unit suite/build (`38959799777`), container runtime smoke (`38959799720`), and validation-only multi-architecture image validation (`38959799806`, publishing paused). The import-boundary CI step passed. No assistant-side local test command ran.
- PR #254 merged by squash as `8bfd6a57179aec46a672343745b494dff60fec02`. Verified GitHub reports the PR closed and merged. No image publication, deployment, or production-runtime verification was performed.
- Next task: characterize `recommend_new_music()` deterministically with fake provider responses and a fixed listen/library fixture; trace `discovery_library_snapshot.py` and resolve inventory overlap before extracting candidate gathering.


---

## 2026-10-16 — PR #272 merged: broader-query fallback test decoupling

- Based on GitHub main commit `de94d9bbb9790129ed86dc9fefd28a1850a9c721`. Branch: `test/direct-search-fallback-regression`.
- Moved the broader-query fallback regression out of the AST harness in `tests/test_acquisition_safety.py` into direct-import coverage in `tests/test_slskd_search_polling.py`. The direct test uses the production query generator and polling implementation, asserts the exact Tinariwen query pair, request timeouts (15,000 ms then 6,000 ms), per-attempt collected response counts (0 then 1), aggregate counts, and ordered query diagnostics via `acquisition_search_diagnostics.no_match_message()`.
- The AST harness no longer compiles `_discovery_acquire_album_impl()`; it remains for the import/dismissal adapter and other acquisition lifecycle cases. No production acquisition code, candidate eligibility, queueing, concurrency, persistence, or filesystem-safety behavior was changed or removed.
- First CI attempts exposed two test-only defects: an empty class left after removing the AST test, and an assertion that overlooked the third generated query variant. Both were corrected; the fallback search stops after the second query returns a usable payload.
- Final code/test head `8a464edf8313594ddde69f0be90135fce4782f07` passed all four required workflows: Python syntax/acquisition safety (`38969125353`), Docker packaging/full unit suite/build (`38969125409`), isolated container runtime smoke (`38969125262`), and validation-only multi-architecture image validation (`38969125387`, publishing paused). The full suite passed 554 tests in both unit-test workflows. The latest code head has no production behavior changes. No live slskd search/download, filesystem mutation, deployment, or production runtime verification was performed.
- PR #272 was squash-merged as `9b97f447adc602a3be3b5ac496633430f3eb3cb4`. All four required workflows passed on the exact final PR head `7b1257e0ceb9368063de025a2758f48a344efbcb`: Python syntax/acquisition safety (`38969292510`), Docker packaging/full unit suite/build (`38969292338`), isolated container runtime smoke (`38969292382`), and validation-only multi-architecture image validation (`38969292490`, non-publishing). The full suite passed 554 tests. Publishing, deployment, and production runtime verification were not performed.


## 2026-10-16 — PR #274 merged: final acquisition safety AST coupling removed

- Based on current GitHub main `5a74b12d489ae30cfad923af7b68985ebede87dc`. Branch: `test/remove-acquisition-safety-ast`.
- Removed the `ast.parse()` of the legacy server source test harness from `tests/test_acquisition_safety.py`. The test fixture now creates isolated state directly; the import persistence-failure regression composes the production `acquisition_orchestration.import_source_unless_dismissed()` guard with `acquisition_import_service.import_completed_source_locked()`.
- Preserved assertions that failed persistence prevents the importer callback and destination creation. Existing direct tests continue to cover dismissal/lock behavior, request concurrency, recovery/retry refusal, source validation, rollback, symlink escapes, no-overwrite, and unrelated-file preservation. No production code changed.
- Exact final PR head `ad6864ea1f5f70b7f9d8b852bbc4bb02e7c2d395` passed all four required workflows: Python syntax/acquisition safety (`38970088355`), Docker packaging/full unit suite/build (`38970088327`), container runtime smoke (`38970088307`), and validation-only multi-architecture image validation (`38970088322`, publishing paused). The full suite passed 554 tests. PR #274 squash-merged as `cae95e74c9910c512392de80b337eb4b21de67a5`.
- No production code changed. Publishing, deployment, and production runtime verification were not performed.
- Next: obtain the owner decision on MCP-exposed `restart_server` and `apply_server_patch`; no changes to those capabilities before authorization.


## 2026-10-16 — PR #276 merged: retire legacy operational MCP tools

- Based on GitHub main `fc73958eac7b3e1b95ab29493fb023f63b76bd41`. Branch: `remove/legacy-operational-mcp-tools`.
- Safety audit found `restart_server` and `apply_server_patch` had no internal callers and were exposed only through `mcp_registry.TOOL_NAMES`. The former kills/relaunches the server on hardcoded port 8000; the latter rewrites `navidrome_server.py` on disk. Per the owner's earlier direction to remove these if safe, both definitions and registry entries are removed; the other 25 tools and MCP runtime remain.
- Updated `tests/test_mcp_registry.py` to assert 25 unique tools and that the two retired functions are neither registered nor exposed by the legacy service. Added a decision record and updated the active roadmap/workflow/status docs.
- Exact final PR head `67320d555d2ce5f26868b57f8d46a5b46b295f81` passed all four required workflows: Python syntax/acquisition safety (`38970741140`), Docker packaging/full unit suite/build (`38970741125`), container runtime smoke (`38970741243`), and validation-only multi-architecture image validation (`38970741035`, publishing paused). The full suite passed 554 tests. PR #276 squash-merged as `fb5085f7b62b4b9616372c4d044fd974320b2f76`.
- No live service restart, source rewrite, deployment, or publication was performed.
- Next: run the modularization completion audit against current main, including the dependency-map artifact, remaining legacy references, and size-ratchet measurements.


## 2026-10-16 — PR #277 merged and modularization completion audit

- PR #277 merged as `d6e32aadfbca6e1d746ced657bdc124b9d472251`. All four required workflows passed on its exact final PR head `246355b556bdb0d95830a5d504186fc1a14961f0`: syntax/acquisition safety `38970922948`, Docker packaging/full unit suite/build `38970922994`, runtime smoke `38970923035`, and validation-only multi-architecture image validation `38970923009`. Publishing remained paused.
- Current-main CI on `d6e32aadfbca6e1d746ced657bdc124b9d472251` passed all four workflows. The syntax workflow's dependency-map artifact `12077720422` (SHA-256 `4231dc3f9e23161c1d593c781758dd6ac834ebf0f10d14088880761211150879`) was reviewed: 168 repository modules, 73 modules in the app import closure, and one AST-visible app-to-`navidrome_server` edge at `app/api/dependencies.py:10`, the intended lazy service import. The map notes dynamic imports/dependency injection require manual review.
- The current size-guard log reports `navidrome_server.py` at 2,768 lines (limit 3,031), `recommend_new_music()` at 568 AST lines (temporary limit 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280); guard passed. The two retired operational tool names are absent from the service source and MCP registry; registry contains 25 tools. Their intentional mentions remain in tests and decision/history docs.
- PR #278 centralized the duplicated category classification in `discovery_recommendations.classify_recommendation_category()`. Exact PR head `d17f9b52823a7dbc7a5f291441bddef9061f4e7a` passed all four required workflows: syntax/acquisition safety (`38971546874`), Docker packaging/full unit suite/build (`38971547354`), runtime smoke (`38971547239`), and validation-only multi-architecture image validation (`38971546979`, publishing paused). The full suite passed 560 tests. Merge commit: `d619a83c064f3cc106356d96bf83747755c8072a`.


## 2026-10-16 — PR #278 merged and current-main audit refreshed

- PR #278 merged as `d619a83c064f3cc106356d96bf83747755c8072a`. The shared category policy reduced `recommend_new_music()` from 568 to 466 AST lines while preserving the existing characterization tests and adding six direct policy tests plus a selection/diagnostic category consistency assertion. Exact PR head `d17f9b52823a7dbc7a5f291441bddef9061f4e7a` passed all four required workflows; the full suite passed 560 tests.
- Current-main dependency-map artifact `12076627980` (SHA-256 `31105d5ff631b58093855dbfb7e6b62237fd44454c4327b3996be4f211976c94`) on `d619a83c064f3cc106356d96bf83747755c8072a` reports 169 Python modules and a 73-module app import closure. The only AST-visible app import of `navidrome_server` remains the intentional lazy import at `app/api/dependencies.py:10`. Dynamic imports/dependency injection remain outside the static graph and are covered by manual review and tests.
- Current size guard passes at 2,666 `navidrome_server.py` lines (limit 3,031), `recommend_new_music()` at 466 AST lines (temporary limit 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280). The retired operational functions are absent from service source and MCP registry; registry remains 25 tools.
- Next seam: extract the bounded Last.fm scoring/profile-adjustment loop from `recommend_new_music()` into a directly testable policy helper, preserving lookup cap/order, score multipliers, missing-stat behavior, tag-driven profile adjustment, and checked-count diagnostics.


## 2026-10-16 — PR #280 merged: Last.fm recommendation scoring extracted

- PR #280 merged as `3dc999b872bdf12db30c43ee73b5e726c4ea494b`. Exact PR head `ce2fc91612d6fbb8deb25e2222830db3ff0c8fd5` passed all four required workflows: syntax/acquisition safety (`38971979899`), Docker packaging/full suite/build (`38971979883`), runtime smoke (`38971979880`), and validation-only multi-architecture image validation (`38971979885`, publishing paused). The full suite passed 564 tests.
- The direct-import `apply_lastfm_popularity_bonus()` helper preserves top-40 score order, missing-stat skips, recent-family recomputation from Last.fm tags, capped popularity score multiplier, and the diagnostic checked count. A first CI attempt on an earlier head exposed the accidentally removed `lastfm_api_configured` assignment; it was restored before final verification. No provider calls or production data were used.
- Current-main dependency-map artifact `12076948070` (SHA-256 `5f56d6735f0416674aa853435f1ce1d126d015d930ad604c96226341ce185682`) on `3dc999b872bdf12db30c43ee73b5e726c4ea494b` reports 170 repository modules and a 73-module app import closure; the only AST-visible app-to-legacy-server edge remains the lazy import at `app/api/dependencies.py:10`.
- Current size guard passes at 2,616 server lines (limit 3,031), `recommend_new_music()` at 416 AST lines (temporary limit 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280).
- Next seam: extract the familiarity multiplier thresholds and exploration-family boost into `discovery_recommendations.apply_familiarity_exploration_bonus()`, with direct tests for every threshold and the family-overlap condition.


## 2026-10-16 — PR #281 merged: familiarity/exploration scoring extracted

- PR #281 merged as `93519c403ac2c301c46acddf6a64d59059d3f683`. Exact PR head `176914b3e4712d3090cb2fa80a4246fb12e89b2b` passed all four required workflows: syntax/acquisition safety (`38972398532`), Docker packaging/full suite/build (`38972398406`), runtime smoke (`38972398402`), and validation-only multi-architecture image validation (`38972398450`, publishing paused). The full suite passed 566 tests.
- `discovery_recommendations.apply_familiarity_exploration_bonus()` now owns the recent-artist multipliers and 1.10 exploration-family boost. Direct tests cover every threshold boundary and both overlap/no-overlap cases. No public response fields, provider calls, allocation policy, or production behavior changed beyond extracting the same scoring operations.
- Current-main dependency-map artifact `12078000327` (SHA-256 `cd9c931dd7e3ccb740f1ab24c01686a27c8f6b51ed7be58c87e301b6b6e0b58e`) on `93519c403ac2c301c46acddf6a64d59059d3f683` reports 171 Python modules and a 73-module app import closure. The sole AST-visible app import of `navidrome_server` remains the intentional lazy import at `app/api/dependencies.py:10`.
- Current size guard passes at 2,596 server lines (limit 3,031), `recommend_new_music()` at 396 AST lines (current temporary exception 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280).
- Next: tighten the recommendation adapter exception from 575 to 450 lines, then audit the remaining function for a clear independent seam rather than extracting solely for size.


## 2026-10-16 — PR #283 merged: recommendation size ratchet tightened

- PR #283 merged as `767ac3efd4e02eab15c04fd033fabeb619f4b1ff`. Exact PR head `992405682a8a942738ab354393e70a3fb8c89ab8` passed all four required workflows: syntax/acquisition safety (`38972838143`), Docker packaging/full suite/build (`38972838173`), runtime smoke (`38972838187`), and validation-only multi-architecture image validation (`38972838218`, publishing paused). The full suite passed 567 tests.
- The `recommend_new_music()` exception is now 450 AST lines; a regression accepts 450 and rejects 451 using the default exception configuration. The current function is 396 lines, leaving 54 lines of headroom. The 280-line general function ceiling and 3,031-line server ceiling are unchanged.
- Current-main CI on `767ac3efd4e02eab15c04fd033fabeb619f4b1ff` passed all four workflows. Size measurements: `navidrome_server.py` 2,596 lines, `recommend_new_music()` 396 AST lines, and `_discovery_acquire_album_impl()` 278 AST lines. Size guard passed.
- Current-main dependency-map artifact `12077488636` (SHA-256 `39b6b2854789f0273b117adb1b9357e4765e420f87f61b05b4932f4b45c5ad49`) reports 171 Python modules and a 73-module app import closure. The sole AST-visible app-to-legacy import remains the intentionally lazy import at `app/api/dependencies.py:10`.
- **Modularization completion decision:** after extracting provider gathering, category classification, Last.fm scoring, and familiarity/exploration scoring, the remaining `recommend_new_music()` code coordinates candidate ordering, allocation/ownership decisions, diagnostic projection, and public response shaping. Extracting the diagnostic loop now would require a broad shared-state context and would not simplify the boundary enough to justify it. Retain it under the 450-line ratchet; revisit only with a concrete bug or feature that reveals a smaller independently testable seam. No more size-only extraction work is planned.


## 2026-10-17 — Modularization completion audit closed

- Reviewed the current-main completion state after PR #288 and the subsequent documentation-only closeout: dependency-map generator and CI artifact step, app-to-legacy import guard and lazy compatibility edge, AST-test inventory, Docker COPY inclusion test, current Dockerfile root-module list, recommendation/acquisition retained orchestration, and the roadmap's definition of done.
- The dependency map is generated in CI rather than committed as a mutable snapshot. It traverses repository-local AST imports from `app.main`; its documented limitation is that dynamic imports and dependency injection require manual inspection. The only reviewed app-to-legacy import remains `app/api/dependencies.py:get_librarian()`.
- The packaging regression checks all AST-visible root-level imports in `navidrome_server.py` against Docker COPY sources. The post-PR #288 audit records all 48 imported modules present; PR #286 and PR #288 fixed the two delayed-import omissions found during this audit sequence.
- The AST-coupled test inventory records the migration to direct imports without weakening acquisition concurrency, recovery, persistence, or filesystem-safety coverage. The recommendation adapter and acquisition lifecycle coordinator remain justified orchestration; no narrower boundary emerged from this audit.
- **Decision: modularization roadmap complete.** No further concrete correctness, safety, or testability gap was identified. No size-only or speculative extraction is scheduled. Reopen only for a concrete defect or requirement.
- Verification evidence available in GitHub: PR #288 exact head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c` passed all four required workflows (syntax `38978049684`, Docker packaging/full unit suite/build `38978049670`, runtime smoke `38978049793`, validation-only multi-architecture `38978049589`, publishing paused). This audit did not run local tests or re-run those workflows on the documentation-only commit. No publishing, deployment, or production runtime verification is claimed.


## 2026-10-17 — Service configuration defaults audit

- Started focused branch `fix/remove-personal-network-defaults` from main `bf27b86069e5acb420f7e5663783a01fa4e36076`.
- Removed the personal ListenBrainz username fallback and the private `192.168.1.12` Navidrome/slskd URL fallbacks from Python settings defaults, the slskd settings tool signature, Compose defaults, and `.env.example`. Unconfigured service URLs/usernames now rely on existing validation to report configuration errors rather than silently targeting a personal account or private host.
- Added regression assertions that blank Navidrome/slskd URLs and a blank ListenBrainz username fail validation.
- Added `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with audit findings and next-session proposals: remove fixed regional targets, make supplementary discovery responsive to recent listening, reduce artist-specific overrides, and test ranking variability/refresh/cache behavior while preserving ownership and eligibility safeguards.
- **PR #292 merged:** final PR head `51f3a0e1ee55334020bc26793ca1d86a6c145a7c`; merge commit `0db291970fbeff2ed192d73b04fe1efc8ecb3cb6`.
- **CI:** all four required workflows passed on the exact final PR head: `compile`, `test-and-build`, `container-smoke`, and `validate-container`. Local test commands were not run. Publishing remains paused; no deployment or production runtime verification is claimed.
- **Configuration caveat:** existing persisted settings were not migrated, so values previously saved in an installation may remain until explicitly changed.

## 2026-10-17 — MCP retirement plan drafted

- Inspected current GitHub `main` documentation and implementation relevant to MCP retirement: project status, product requirements, development workflow, test plan, `mcp_registry.py`, `navidrome_server.py`, the lazy web-service adapter, MCP registry tests, `requirements.txt`, Dockerfile, and Compose configuration.
- Confirmed that MCP is not fully retired: `mcp_registry.py` still registers 25 tools, `navidrome_server.py` retains a standalone streamable-HTTP MCP startup path on `127.0.0.1:8000`, and `requirements.txt` still declares `mcp==2.3.0`.
- Recorded that the web app shares service logic through `app/api/dependencies.py:get_librarian`; retiring MCP must not remove recommendation, discovery, settings, acquisition, recovery, persistence, or filesystem-safety behavior. The consumer audit must establish whether any external clients rely on the MCP endpoint before removal.
- Added `docs/MCP_RETIREMENT_PLAN.md` with the audit sequence, focused removal approach, regression requirements, packaging checks, required four-workflow CI gate, and definition of done. The plan explicitly does not authorize publishing or deployment.
- No implementation code changed and no tests were run locally in this documentation-planning session. Existing historical CI results do not verify this new commit; record exact PR-head CI evidence before merge. Publishing remains paused; no deployment or production runtime verification is claimed.
- Next action: complete the consumer/reference audit and prepare a focused MCP retirement implementation PR.

## 2026-10-17 — PR #295 merged: MCP retirement plan

- Added `docs/MCP_RETIREMENT_PLAN.md` and updated `docs/PROJECT_STATUS.md` to record the focused migration plan and next action.
- PR #295 final head: `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`; merge commit: `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- All four required GitHub Actions workflows passed on the exact final PR head: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remained paused.
- Local tests were not run because this was a documentation-only planning change. No MCP implementation was removed. No publishing, deployment, or production runtime verification is claimed.
- Next action: complete the MCP consumer/reference audit, then prepare a focused implementation PR preserving shared web/service behavior and safety coverage.

## 2026-10-17 — PR #310: contrasting-profile recommendation adapter regression

- Based on GitHub main fd044b183884e13c20467975276fdea848e1d11e. Branch: test/contrasting-profile-adapter.
- Extended tests/test_recommend_new_music_characterization.py with injectable listening histories and per-artist cached genre fixtures. The new end-to-end test keeps the two candidates, their provider scores, and genre metadata fixed while changing the recent-listening profile between John Coltrane and Art Blakey. It asserts both candidate score ordering and the top recommendation reverse with the profile; the candidates share the same allocation category so category quota order does not mask ranking behavior.
- At code-only head 18d7fdd432729f68f3849935cf2848154759b7e1, the focused regression passed as part of the full unit suite: 627 tests passed. All four required workflows passed on that code-only head: Python syntax 39048378481, Docker packaging/full unit suite/build 39048378490, container runtime smoke 39048378488, and validation-only multi-architecture image validation 39048378513 (publishing paused).
- The PR then received documentation updates to docs/PROJECT_STATUS.md and docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md. Exact final PR head 2fb8ce7e45188f7f02104cd171ac0d08102279ca passed all four required workflows: Python syntax 39048493243, Docker packaging/full unit suite/build 39048493246 (627 tests passed), container runtime smoke 39048493238, and validation-only multi-architecture image validation 39048493239 (publishing paused). PR #310 squash-merged as 31315a54255762f821cdd9d9949ee11a3ce17fb1. No assistant-side local tests were run.
- No recommendation policy, API contract, provider behavior, or application code changed. No private capture or live provider data was used. Publishing, deployment, and production-runtime verification remain unperformed.
- Next: implement Phase 2.1 profile-derived supplementary MusicBrainz tag queries as a separate behavior change. Do not collect further live diagnostic snapshots.


## 2026-10-17 — Recommendation Phase 3.1 MMR evaluation seam

- PR #316 merged as `f2393fdfb9e793f8d8b7f32a13c2fc754cbd9409`; final PR head `f46b7fc23c2e0bdbaceff63cca532379fa2c456e`, based on main commit `8a6b4a9dd506c95026e12e5b9bd7569a5c380d61`.
- Added `discovery_mmr.py`, a deterministic offline greedy MMR selector using min-max-normalized relevance, exact artist identity, and Jaccard genre-tag similarity. It enforces one selected candidate per non-empty artist key and provides shortlist metrics for unique artists, pairwise similarity, and original-score retention.
- Added `tests/test_discovery_mmr.py` for similarity normalization, artist cap, MMR trade-off, deterministic ties, input immutability, metrics, and invalid inputs.
- Updated `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `docs/PROJECT_STATUS.md` to distinguish the helper from production rollout.
- Production ranking is unchanged. The private replay fixture was not available to this GitHub-only session; no replay result or assistant-side local test result is claimed. Initial CI exposed an incorrect expected ordering in the MMR trade-off fixture; the fixture scores/lambda were corrected. All four required workflows passed on exact final PR head `f46b7fc23c2e0bdbaceff63cca532379fa2c456e`: Python syntax run 1604 (`39051000774`), Docker packaging/full unit suite/build run 1512 (`39051000938`, 640 tests passed), container runtime smoke run 1321 (`39051000832`), and validation-only multi-architecture image validation run 1365 (`39051000940`, publishing paused).
- Publishing, deployment, and production-runtime verification remain unperformed.
- Next: run the existing offline fixture from `~/navi-librarian-test/private-recommendation-fixtures` against merged commit `f2393fdfb9e793f8d8b7f32a13c2fc754cbd9409`; compare baseline vs MMR relevance/diversity before any production integration.


## 2026-10-17 — Front-end contribution boundaries generalized

- Removed tool-specific front-end ownership from `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/FRONTEND_DESIGN_GUIDE.md`, and `docs/UI_BACKLOG_EXECUTION.md`.
- Any agent may work on front-end matters, but edits remain restricted to `static/app.css`, `static/app.js`, `static/login.css`, `static/login.js`, `app/templates/*.html`, narrowly scoped front-end tests/fixtures under `tests/`, and `docs/UI_BACKLOG_EXECUTION.md`.
- Protected backend/API/security, domain, architecture, workflow, dependencies, packaging, deployment, and release-policy files still require explicit approval and coordinated ownership. No application code or runtime behavior changed.
- Documentation-only change; automated tests and browser checks were not run in this editing step. CI verification on the final PR head remains required.


## 2026-10-17 — PR #321 merged: diversity setting roadmap

- PR #321 merged at `504035d36ad63605c7ba645f0e995745894f7434`; exact final head `8bf73dc4ac2927a08d3ac0e0d22466d60e542795`.
- Added `docs/DIVERSITY_SETTING_ROADMAP.md` describing the Recommendation diversity slider, endpoint copy, evidence limits, offline calibration, backend preference/persistence, safe MMR integration, frontend boundaries, acceptance criteria, and rollout restrictions. Updated `docs/PROJECT_STATUS.md` to point to the new roadmap and set offline mapping calibration as the next action.
- All four required workflows passed on exact final head: Python syntax run 1620 (`39066220743`), Docker packaging/full suite/build run 1528 (`39066220749`), container runtime smoke run 1337 (`39066220736`), and validation-only multi-architecture image validation run 1381 (`39066220768`, publishing paused).
- Documentation-only; no local tests or UI checks were run. Production ranking is unchanged. No publishing, deployment, or runtime verification is claimed.
- Next: calibrate the diversity-to-lambda mapping and relevance floor offline around lambda 0.75 before backend preference integration.


## 2026-10-17 — MMR relevance-floor calibration harness (PR pending)

- Started branch `recommendation/calibrate-mmr-relevance-floor` from current GitHub `main` at `bd1052ae8f963e0aacd90428b04687f4cea36cf4`.
- Added a pure, validated mapping from the proposed 0–100 diversity setting to this implementation's similarity-penalty weight. Code inspection found that this implementation subtracts `lambda × similarity`, so a higher lambda produces more diversity; the roadmap's prior statement that the slider should map inversely to conventional MMR lambda was inconsistent with the actual formula. The roadmap now records the implementation's real semantics and treats mapping calibration as pending.
- Extended the provider-free offline evaluator to sweep a bounded lambda grid around 0.75 together with normalized relevance floors (0, 0.05, 0.1, 0.15, 0.2 by default). Floors use the original candidate pool's min-max normalization and may produce shorter lists rather than forcing low-relevance replacements. Added regression coverage for mapping bounds, floor behavior, sparse-list trade-offs, and deterministic repeat checks.
- No private capture was accessed and no calibration outcome is claimed. The next required step is to run the updated evaluator against the existing private frozen fixture locally and share only identity-free aggregate metrics. No new live capture is needed. Production ranking remains unchanged.
- Initial PR-head CI on `47483bfeaa05d42f6770bf486e171f8586866358`: Python syntax run 1623 (`39068286640`) passed; Docker packaging/full unit suite/build run 1531 (`39068286574`) passed; container runtime smoke run 1340 (`39068286641`) passed; validation-only multi-architecture image validation run 1384 (`39068286688`) was still in progress at the time of this log update. The status/log update itself creates a newer PR head, so all four workflows must be rechecked against that exact final head before merge. No assistant-side local tests were run. Publishing, deployment, and production-runtime verification remain unperformed.


## 2026-10-17 — PR #322 merged: MMR relevance-floor calibration harness

- PR #322 merged at `76c872a43c48945d94125993f11e9ff5436b537e`; exact final PR head `8ed9934a8e78ddc8221ccbfae90c02b8d9e20dc9`.
- All four required workflows passed on that exact final head: Python syntax run 1624 (`39068353650`), Docker packaging/full unit suite/build run 1532 (`39068353631`), container runtime smoke run 1341 (`39068353654`), and validation-only multi-architecture image validation run 1385 (`39068353615`). Publishing remained paused.
- The pure MMR helper now supports an optional relevance floor defaulting to zero; the offline evaluator sweeps floor values and lambda values. Default production ranking remains unchanged because the production adapter does not invoke the helper.
- No assistant-side local tests were run and the private fixture was not accessed. Do not choose a nonzero floor or implement preference integration until the owner runs the evaluator against the existing private fixture and reviews identity-free aggregate metrics. No live capture, publication, deployment, or production-runtime verification is claimed.
- Next action: owner-fixture offline calibration; do not collect another live snapshot.


## 2026-10-17 — Owner-fixture MMR relevance-floor sweep reviewed

- Retrieved the existing owner-only capture from the private abucalip/reports repository; did not modify it or commit candidate identities/report output. Capture source SHA: d8c1f3de5180b35919f55c304d55e5c939dad373.
- Aggregate structure: 83 gathered albums, 1,733 library albums, 83 debug candidate rows, 66 scored/rankable candidates, 10 baseline recommendations, and captured scores for all 10 baseline recommendations. The 35 combinations covered lambda 0, 0.25, 0.5, 0.65, 0.75, 0.85, 1 and relevance floors 0, 0.05, 0.1, 0.15, 0.2.
- At floor 0 or 0.05, all lambdas returned 10 items and retained 7/10 baseline items. Lambda 0 had mean pairwise similarity 0.1044; lambda 0.75/0.85/1 had 0.0591 and about 85.5% baseline relevance-score retention at lambda ≥0.25. Lambda 1 showed no additional benefit. Floors ≥0.1 returned only seven items, retained 4/10 baseline items and 70.3% baseline relevance score, and raised mean pairwise similarity to about 0.216. Decision: keep floor 0; do not set a production lambda/default based on one frozen capture.
- **Verification limitation:** these aggregates came from a JavaScript reproduction of the inspected merged Python evaluator/MMR logic; the actual Python CLI was not executed in a Python runtime. Do not claim CLI verification. Next action is to run recommendation_mmr_evaluate.py --identity-free in the isolated Python environment and compare results. No live provider calls, production changes, publishing, deployment, or runtime verification occurred.


## 2026-10-18 — Diversity setting roadmap audit adopted

- Read the supplied audit against the current GitHub roadmap, development workflow, requirements, test plan, project status, and recent GitHub state. Current main at session start was `39353490d6f8f345e6feed64b8c6e892eef9b769`; PR #326 is recorded as merged and PR #327 remains an independent UI change.
- Restructured `docs/DIVERSITY_SETTING_ROADMAP.md` to block the diversity slider UI until calibration and correctness gates are met. The roadmap now prioritizes an identity-free 0–100 lambda sweep on the existing private fixture; evidence-based slider mapping/cap; rank-based or approved pool-stable relevance normalization and cross-pool tests; neutral treatment of missing genre tags; precomputed tag sets; relevance-retention, category-mix, genre-coverage, and untagged-promotion metrics; and a reviewed rollout gate.
- Added later-phase ideas for a “last generated with diversity X” indicator or safe refresh, bounded privacy-preserving Get/Skip/Dismiss feedback, and per-surface diversity only after the global setting is validated.
- Preserved the explicit decision to dismiss the prior 35-combination/floor-sweep reproduction. The proposed sweep is a separate scoped evaluation using the existing fixture only; no live capture or fixture/report publication is authorized.
- Recorded the audit's uncertainty about full ancestry verification for PR #326 rather than claiming it independently verified. The stale `navidrome_server.py` comment is listed for correction with the implementation follow-up.
- This is a documentation-only change. No tests, evaluator sweep, CI, UI checks, publication, or deployment were run as part of this session. The roadmap remains uncalibrated until the next action is actually performed.


## 2026-10-18 — PR #332 merged: soft recommendation-history cooldown

- Branch: `recommendation/soft-history-cooldown`, based on GitHub `main` at `2e8cdfcebd69565fe3a92742e43fccb8826c4377`.
- PR #332 merged at `1fdd01b1878be10544358450cb9f2a4a1d03d5d2`, from exact final tested PR head `692722e019e671a3cd4cef67698743d359f205e9`.
- Added `recommendation_cooldown.py`: repeat exposure contributes a rank-weighted soft score penalty (10% for rank 1 down to 0.5% for rank 20), decayed with a seven-day half-life, capped at 25%, and ignored after 30 days. The constants are explicit starting policy, not calibrated quality claims.
- Integrated the adjustment into personal recommendation allocation only for candidates already classified as ownership-clear. It changes scores, never filters candidates, and fails open when the optional history read errors. Persisted identity hashing is exposed through `discovery_store.recommendation_identity_hash()`; the previous private helper remains an alias, and the SHA-256 normalization/separator remains compatible with existing rows.
- Deterministic tests cover no-history behavior, rank weighting, half-life, expiry, future/malformed rows, cumulative cap, missing identity, sparse pools, deterministic repeat runs, relevance-gap retention, ownership-gate preservation, and storage failure.
- Exact-head CI passed: Python syntax/acquisition safety run `1663` (`39082723833`); Docker packaging/full unit suite/build run `1571` (`39082723818`, 691 tests passed); container runtime smoke run `1380` (`39082723841`); validation-only multi-architecture image validation run `1424` (`39082723824`, publishing paused).
- Initial CI on prior head `9514d74e7e88e6cb061b5a90652d200ed6a69097` found the missing Docker COPY entry and a too-strict floating-point assertion. Both were fixed; subsequent final-head workflows passed. No assistant-side local tests or private fixture replay were run.
- Publishing, deployment, and production-runtime verification were not performed. Cooldown calibration remains open; do not collect another live capture or publish private fixture data. The next useful action is an identity-free comparison on the existing private offline fixture if it can evaluate cooldown without reconstructing a new live capture.


## 2026-10-18 — Recommendation cooldown calibration feasibility

- **Repository baseline:** `main` at `ee87ef18ef41bed49a841e0996980487cac7dca5`; PR #332 cooldown implementation remains merged at `1fdd01b1878be10544358450cb9f2a4a1d03d5d2` from tested head `692722e019e671a3cd4cef67698743d359f205e9`.
- **Feasibility result:** the existing private capture/evaluator cannot establish a real baseline-vs-cooldown quality comparison. The capture stores gathered inputs and captured output/debug scores but not the SQLite recommendation-history rows consumed by `recommendation_cooldown.apply_history_cooldown`. `recommendation_mmr_evaluate.py` only reranks captured scores with MMR; it neither applies the cooldown nor replays the provider tape. Synthesizing history would only measure a hypothetical scenario, not the observed effect.
- **Changes:** documentation records the feasibility result and explicitly leaves cooldown constants uncalibrated. No application code, private fixture, identity-bearing report, or production data was changed. No tests or fixture evaluation were run.
- **Next action:** the separately scoped identity-free 0–100 diversity sweep against the existing private fixture, with relevance floor fixed at 0. The fixture is not available in the GitHub-only environment; no new capture and no rerun of the dismissed 35-combination/floor sweep.
- **Delivery state:** PR #336 merged at `91bc647c5300d42d10f6bd393645a481c6d25474` from exact head `1c4f958d662ead5b5a3f5ea4485b1e8f17efb20f`. All four required workflows passed on that exact head: Python syntax check `1670` (`39122256427`), Docker packaging `1578` (`39122256409`), container runtime smoke `1387` (`39122256392`), and validation-only Docker image check `1431` (`39122256401`, publishing paused). Documentation-only change; no tests or private fixture evaluation were run. Publishing, deployment, and runtime verification remain paused/unclaimed.


## 2026-10-18 — Rank-based recommendation relevance normalization (PR #338 pending)

- Branch: `recommendation/rank-normalization-pool-stability`, based on GitHub `main` at PR base `d42164e5930d4ee37e2a310a95871dbea3bd7bc8`.
- Replaced min-max relevance normalization in `discovery_mmr.py` with descending average-rank normalization into [0, 1]. Equal scores share relevance; a constant-score pool assigns all candidates relevance 1; selection tie-breaking remains deterministic by original input order.
- Added tests for score-scale/gap invariance, tied and constant-score pools, and updated relevance-floor expectations. Updated the diversity roadmap and project status. No private fixture replay, live providers, UI work, publishing, deployment, or runtime verification was performed.
- PR #338 exact head at this entry: `722972033c1470030f9ff986e5e474b7bd8283c4`. Required CI was in progress; no test or CI pass is claimed. No assistant-side local tests were run.
- Next action: confirm all four required workflows on the exact final PR head, fix any failures, and merge only after review and gates pass. Then address missing-tag neutrality; keep the diversity UI blocked.


## 2026-10-18 — PR #338 merged: rank-based relevance normalization

- PR #338 squash-merged at `8ce1fc0de31135653781edc231e5f77698cb8773`, from exact CI-verified head `5eda37a77a2c623b06843a87800e306a16e92412`.
- Replaced min-max normalization with descending average-rank relevance. Equal scores share relevance; constant-score pools assign relevance 1; selection ties remain deterministic. Added score-gap/scale, tie, constant-pool, and relevance-floor regressions.
- All four workflows passed on the exact head: syntax/safety `1682` (`39124360180`), packaging/unit tests/build `1590` (`39124360039`), container smoke `1399` (`39124359849`), non-publishing multi-architecture validation `1443` (`39124359917`). No assistant-side local tests or private fixture replay.
- Publishing remains paused; no UI, publication, deployment, or runtime verification. Next: missing-tag neutrality tests, then final-shortlist quality/category metrics.


## 2026-10-18 — PR #340: MMR missing-tag novelty bias

- Branch `recommendation/mmr-missing-tag-neutrality`, based on GitHub main `f61a01f3895ac59b7833c008771138d4499ef661`.
- Changed `discovery_mmr.py::candidate_similarity`: exact artist identity remains authoritative; when either candidate lacks usable genre tags, similarity is conservatively treated as 1.0 so absent metadata cannot earn an unearned diversity bonus. Fully tagged, disjoint candidates still have similarity 0.0. This is a conservative missing-data policy, not evidence that untagged albums are actually similar.
- Added direct regressions for either/both candidates untagged, genuinely disjoint tagged pairs, and shortlist ordering so an untagged candidate does not jump ahead of a genuinely dissimilar tagged candidate solely because its metadata is absent.
- Updated `docs/DIVERSITY_SETTING_ROADMAP.md` and `docs/PROJECT_STATUS.md`; final-shortlist relevance/category/genre-coverage/untagged-share guardrails remain the next task. Settings UI remains blocked.
- Exact PR head before documentation commits: `e8ad28c28a22d1b6a256ab02dfde65614dda208c`; docs commits follow, so all four required workflows must be checked against the final PR head before merge. At the time of the first check, Python syntax and Docker packaging/full unit suite/build had succeeded; container smoke had succeeded; non-publishing multi-architecture validation was still in progress. No local tests or private fixture replay were run by the assistant.
- No live providers, fixture identities, UI, publication, deployment, or production runtime were used or verified. Publishing remains paused.


## 2026-10-18 — PR #340 merged: MMR missing-tag novelty bias

- PR #340 merged by squash; merge commit `2e2958115adb27ca72f6a526211424bb8fb2bb65`, exact final PR head `fbf1276948cf85832da7df7c376482eb12100873`.
- All four required workflows passed on that exact head: Python syntax run 1689 (`39124983951`), Docker packaging/full unit suite/build run 1597 (`39124983946`), container runtime smoke run 1406 (`39124983965`), and validation-only multi-architecture image validation run 1450 (`39124983988`, publishing paused).
- Conservative missing-tag similarity handling and regressions are merged. No local tests or private fixture replay were run in this session; no live provider, UI, publishing, deployment, or production-runtime verification is claimed.
- Updated `docs/PROJECT_STATUS.md` on main at commit `7e504e303634bd0dd7fc3d103ad87348ab828c69`.
- Next action: implement final-shortlist relevance/category/genre-coverage/untagged-share guardrails. Keep the Recommendation diversity settings UI blocked until the remaining gates are reviewed. Publishing remains paused.


## 2026-10-18 — Final-shortlist evaluator guardrails (PR pending)

- Branch: `recommendation/final-shortlist-guardrails`, based on GitHub `main` at `043a432e5e1c095a07f3523405f3907bb7ab9a64`.
- Extended the provider-free MMR evaluator with category counts/shares, unique genre/tag coverage, untagged selected count/share, untagged promotions relative to score-ordered top-k, and mean raw-score retention against lambda 0 at the same relevance floor. Corrected evaluator interpretation notes to describe rank-based normalization and conservative missing-tag similarity.
- Added synthetic regression coverage for the new aggregate metrics and lambda-zero reference behavior. No private fixture was accessed or rerun; no live providers, UI, publishing, deployment, or runtime verification was performed. The identity-bearing private fixture/report remain untouched.
- Acceptance gate still open: inspect exact-head CI, review category/relevance trade-offs against existing identity-free fixture metrics only if the owner runs the existing fixture, and define a rollout gate before UI work. Publishing remains paused.


## 2026-10-18 — PR #341 merged: final-shortlist evaluator guardrails

- PR #341 merged at `f987fa596fce4f9d2c4c97c8293d8816759ad41f`, from exact final PR head `b53357d0672bb076b5b07f236694080033ca0946`; branch `recommendation/final-shortlist-guardrails` was based on GitHub main `043a432e5e1c095a07f3523405f3907bb7ab9a64`.
- The provider-free evaluator now includes per-shortlist category counts/mix, unique normalized tag coverage, untagged selected count/share, untagged promotions beyond score-ranked top-k, and mean raw-score retention versus lambda 0 at the same relevance floor. It also reports corresponding captured-baseline category mix, tag coverage, and untagged share. Synthetic regression coverage checks the metrics and lambda-zero reference.
- All four required workflows passed on exact PR head `b53357d0672bb076b5b07f236694080033ca0946`: Python syntax run 1693 (`39125576815`); Docker packaging/full unit suite/build run 1601 (`39125576720`); container runtime smoke run 1410 (`39125576669`); validation-only multi-architecture image validation run 1454 (`39125576695`, publishing paused).
- Assistant-side local tests and private fixture replay were not run. No live providers, UI, publication, deployment, or production-runtime verification. The metrics are diagnostic; rollout thresholds and diversity UI remain blocked pending reviewed relevance/category guardrails.


## 2026-10-18 — Provisional recommendation-diversity rollout gate documented

- Branch: `docs/recommendation-diversity-rollout-gate`, based on GitHub main commit `4c2a0f09ebbbe374cf93049d17d4c3265fc5d589`.
- Documented a proposed rollout gate in `docs/DIVERSITY_SETTING_ROADMAP.md`: mean selected raw-score retention at least 90% of lambda 0; baseline top-10 retention at least 7/10 (70% for other baseline sizes); no disappearance of a category represented by at least two baseline items; no category-share increase greater than 10 percentage points; and continued checks for untagged promotions, shortlist completion, eligibility, artist uniqueness, determinism, and bounded work.
- The thresholds are proposals, not approved policy. The 90%/7-of-10 criteria are informed by the existing single-fixture sweep; category thresholds are proposed guardrails. PR #341's newer category metrics have not been evaluated against the private fixture, so no category pass/fail or rollout approval is claimed.
- Aligned `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` and `docs/PROJECT_STATUS.md` with the next gate. No application code changed; no local tests or private fixture replay were run, and no live provider calls, UI work, publishing, deployment, or runtime verification were performed. The initial PR head `7ae8dcde567fbb01ac4427479952ff86737cb3e3` passed all four required workflows: Python syntax run 1697 (`39126126118`), Docker packaging/full unit suite/build run 1605 (`39126126071`), container runtime smoke run 1414 (`39126126139`), and validation-only multi-architecture image validation run 1458 (`39126126163`, publishing paused). This log edit creates a new PR head, so those workflows must be rechecked on the final SHA before merge.
- Explicitly preserved the prohibition on rerunning the dismissed 35-combination/floor reproduction, collecting a new live capture, or publishing private identities. The Recommendation diversity settings UI remains blocked.
- Next action: review the proposed thresholds; only if approved, arrange a separately authorized identity-free evaluation using the existing private fixture to inspect category/untagged metrics. Do not begin UI work before the gate is measured and passed.


## 2026-10-18 — PR #343 merged: provisional diversity rollout gate

- PR #343 merged at `18f5411ee9bdffd7cbc2bbdfdaaa4c90f099d3de` from exact final PR head `0145d35155a94137402b9958c3d07c5456b0229a`.
- All four required workflows passed on that exact head: Python syntax run 1698 (`39126236218`); Docker packaging/full unit suite/build run 1606 (`39126236242`); container runtime smoke run 1415 (`39126236230`); validation-only multi-architecture image validation run 1459 (`39126236221`, publishing paused).
- Updated the diversity roadmap with a provisional review gate: at least 90% mean raw-score retention versus lambda zero; at least 7/10 baseline top-10 items retained (70%, rounded up, for other baseline sizes); no disappearance of a category represented by at least two baseline items; no category share increase over 10 percentage points; plus untagged-promotion, shortlist completion, eligibility, artist uniqueness, determinism, and bounded-work checks.
- These criteria are proposals, not approved product policy. No private fixture evaluation was run with the new PR #341 metrics; category results remain unknown. No local tests, live provider calls, UI changes, publishing, deployment, or runtime verification.
- The settings UI remains blocked. Next action: review the proposed thresholds; only after explicit authorization, evaluate the existing private fixture using identity-free output and assess the category/untagged metrics. Do not rerun the dismissed 35-combination/floor reproduction or collect a new live capture.


## 2026-10-18 — Pristine candidate snapshots for counterfactual recommendation replay (PR #356 open)

- Base: GitHub `main` at `995094ab01b1cd5ff18c90048a7fe235928cd05f`; branch `recommendation/replay-pristine-ranking-snapshot`.
- Source inspection found that recommendation scoring mutates the gathered album dictionaries before the capture is serialized. The frozen candidate payload could therefore contain profile-derived `recent_profile_bonus`, Last.fm tags/stats, and other ranking fields from the original profile. A same-profile replay can conceal this; a counterfactual profile run can incorrectly divide out a bonus from the original profile.
- Updated `recommendation_replay.py` to strip known ranking-derived candidate fields both when freezing and thawing, while preserving candidate order and other gathering/provider fields. Added a regression test covering each derived field and preservation of an unrelated provider-specific field.
- Updated the recommendation roadmap, test plan, and project status. Clarified that PR #350 established a successful fresh schema-v2 same-profile replay; the older pre-fix mismatch is historical, while pristine snapshots are still required for profile substitution.
- Commits on branch: code `a267a8272d004fbb9526f36f5bf00ef60505714d`; test `28ef9f7dc14eaa20e1f81f043e534eab8ec9f646`; roadmap `000cff6027252450145e4fe898d40c89a4b26663`; test plan `87ff01034eea2fc29f04532638980ce776d93e3f`; status `c3f1fcef12af35fe3ffaec8756dcf9c050a6c008`.
- Assistant-side local tests were not run; PR #356 is open; the initial workflow/status query returned no runs or status checks for initial head `bd35eb0a13b01545a66a9e648648a765bf0e83e8`; final-head CI remains unverified. The private capture was not retrieved or modified, and no live providers were called. No publication, deployment, or runtime verification.
- Next action: review the complete branch diff, open a PR, and verify all four required workflows on its exact final head. After merge, run the owner-only first/last-profile responsiveness comparison using the sanitized frozen snapshot and public history; do not report future-listen quality from this post-window capture.


## 2026-10-18 — PR #356 merged: pristine recommendation replay inputs

- PR #356 merged at `7b17b3f05ce735edd232d1e2895ec9c868918934`, from exact final PR head `73261334020f6121582a6079414d282a38c1ada4`; branch `recommendation/replay-pristine-ranking-snapshot`, based on main `995094ab01b1cd5ff18c90048a7fe235928cd05f`.
- `recommendation_replay.py` strips known ranking-derived fields when freezing and thawing candidate dictionaries. The regression test verifies that prior profile/Last.fm bonuses and derived category/style fields are removed while candidate score, order, and unrelated provider metadata remain.
- All four required workflows passed on the exact final head: Python syntax run `39151554270`; Docker packaging/full unit suite/build run `39151554276`; container runtime smoke run `39151554212`; validation-only multi-architecture image validation run `39151554243` (publishing paused). The full unit-test step and Docker build succeeded. Assistant-side local tests were not run.
- Documentation now records the distinction between the older pre-PR #350 replay mismatch and this counterfactual snapshot-contamination defect. The private capture was not accessed or modified; no live provider calls, publishing, deployment, or production-runtime verification.
- **Next action:** run the full-engine first/last five-day profile responsiveness comparison using the existing owner-only capture and public ListenBrainz history, holding the candidate pool, library/ownership snapshot, Last.fm responses, ranking timestamp, recommendation history, and diversity setting fixed. The available capture postdates both windows, so do not report future-listen hit-rate/nDCG or causal quality claims.


## 2026-10-18 — PR #361 merged: offline profile chronology evaluator

- PR #361, `Add offline full-engine profile chronology evaluator`, merged at `054b7aa71d632821f3d7a3811ab5f24f63003366` from exact tested PR head `257a2fa37ab0831e42769463107a2f05c1e7b220`.
- Added `recommendation_profile_comparison.py` and six focused regression tests. The evaluator compares first-five-day and last-five-day ListenBrainz profiles against one frozen post-gathering candidate/library snapshot, recomputes only listen-derived artist/family counters with the production 14-day decay, holds ranking timestamp/history/diversity fixed, and replays captured Last.fm responses by identity. Missing Last.fm coverage fails closed; no live provider is invoked. Output is aggregate-only.
- Documented usage in `docs/TEST_PLAN.md`. All four required workflows passed on exact PR head: Python syntax run `39157709528`, Docker packaging/full unit suite/build run `39157709498` (733 tests passed and Docker build succeeded), container runtime smoke run `39157709523`, and validation-only multi-architecture image validation run `39157709496` (publishing paused).
- The owner independently replayed the private schema-v2 capture against PR #350 source SHA `dc3e5a3a8ea704bbc66aa1d1b43dc4e9594fd2be`: 5/5 recommendations reproduced, 19 Last.fm responses replayed, zero network providers used, and 225 provider events treated as provenance only. The private capture and history were not committed or exposed.
- The first/last-window comparison has **not** been run yet. The capture postdates both windows, so the comparison measures profile responsiveness on a frozen candidate/library snapshot only; it cannot establish future-listen hit-rate/nDCG or causal listening outcomes.
- **Next action:** run the merged evaluator locally against `baseline-20261018-v2.json` and `abucalip/reports/listenbrainz-history.json`; retain the capture/history and any identity-bearing artifacts outside GitHub.


## 2026-10-18 — Owner-side full-engine profile responsiveness comparison

- Evaluator: merged `recommendation_profile_comparison.py` from PR #361, source commit `054b7aa71d632821f3d7a3811ab5f24f63003366`. Private schema-v2 capture source SHA: `dc3e5a3a8ea704bbc66aa1d1b43dc4e9594fd2be`. History: 407 timestamped listens; private capture and history remained outside GitHub.
- Windows: first five days 2026-10-04 16:01:36Z through 2026-10-09 16:01:36Z; last five days 2026-10-13 00:47:28Z through 2026-10-18 00:47:28Z.
- First profile: 138 listens, 35 normalized artists, 120 artist-MBID listens, 60 genre-classified listens, 6 profile families. Last profile: 132 listens, 63 normalized artists, 111 artist-MBID listens, 26 genre-classified listens, 4 profile families.
- Controls: same 19-candidate pool, library/ownership snapshot, ranking timestamp, recommendation history, diversity setting 0, and captured Last.fm responses. Each run used 19 captured Last.fm entries; zero network providers used.
- Results: 5 recommendations from each profile; membership overlap 5/5 (Jaccard 1.0); two recommendation positions changed. Full ranked candidate order changed; 17 shared candidates changed rank, with maximum displacement 14 places. Both profile runs were deterministic on repeat.
- Interpretation: the ranker responds to the changed profile, but the final top-five membership is stable on this frozen pool. The result does not prove relevance/quality, production candidate freshness, profile-driven query generation, future-listen hit-rate/nDCG, or causal listening effects. The capture was taken after both windows and therefore cannot be used as a chronological future-outcome replay.
- **Next action:** inspect score-component attribution and shortlist/allocation effects using identity-free aggregate diagnostics and deterministic tests. Explain why ranked positions change without top-five membership change before tuning weights. No new live capture, provider request, publishing, deployment, or runtime verification.


## 2026-10-18 — PR #366 score attribution and shortlist diagnostics

- Branch `recommendation/score-attribution-shortlist-diagnostics`, based on GitHub main `b4bc707186e2b9202264e960018b59b4cb3a1cd6`.
- Extended `recommendation_profile_comparison.py` with aggregate distributions for discovery score, recent-profile bonus, Last.fm popularity bonus, recent artist play count, and exploration-family match share. Added allocation decision/category counts, selected rank distribution, and score-ranked top-k overlap/Jaccard with the final shortlist.
- Reports omit candidate identities and per-candidate scores. Added a synthetic regression asserting deterministic aggregate values and identity-free output.
- PR #366 merged at `0588ec0cc8b0ed5ad32c596c5d2c5e314f107639` from exact tested head `deabda7d04f66909a6da5b2fec7dc889ed27a200`.
- All four required workflows passed on that exact head: syntax/full suite `39160186431`, Docker packaging/full suite/build `39160186619` (739 tests), container runtime smoke `39160186497`, and validation-only multi-architecture image validation `39160186550` (publishing paused).
- An earlier test expectation failed and was corrected before the final successful run. No assistant-side local tests or private capture replay. No live providers, publication, deployment, or production-runtime verification.
- Next action: inspect aggregate diagnostics from the existing owner-only capture before choosing any ranking behavior change.

## Recommendation shortlist underfill investigation — 2026-10-18

The owner ran the merged PR #366 offline profile evaluator against the private schema-v2 capture and timestamped history. It returned five recommendations from a requested ten across 19 ranked candidates; aggregate decision counts were four already-owned, ten `recent_genre_cap_reached`, and five selected. The report's candidate-category counts used the separate genre classifier's `assigned_category`, while allocation uses `discovery_category`; it also omitted the allocator's category targets and shortfalls. Those aggregate counts therefore do not yet identify a root cause.

Branch `investigate/recommendation-shortlist-underfill` adds aggregate-only diagnostics for the actual allocation category, target counts, shortfalls, target satisfaction, and resolved candidate count. It adds a deterministic synthetic test using the same 19-candidate category shape (8 adjacent, 6 cross-genre, 5 unclassified; no adventurous candidates), four owned candidates, and a family-capped pool to verify fallback can fill ten without selecting owned items. The synthetic fallback test passed on code head `0dfe32d098b4acb4c1ce78dfef7422b64189297b`. All four required workflows passed on that code head: Python syntax/acquisition safety run `39168705693` (747 tests), Docker packaging/full suite/build run `39168705729` (747 tests), container runtime smoke run `39168705699`, and validation-only multi-architecture run `39168705788`. The first head, `044237463389a90c1ef7f86e8560550f986a380d`, failed one test because its synthetic output fields were inserted into the wrong test fixture; the fixture was corrected in `0dfe32d098b4acb4c1ce78dfef7422b64189297b`, where both full suites passed. No local tests or private capture replay were run by the assistant. The recorded runs apply to code head `0dfe32d098b4acb4c1ce78dfef7422b64189297b`; any later documentation-only commit requires its own exact-head CI verification. No private capture/history or candidate identities were committed. No ranking weights or allocation policy changed; publishing/deployment remain paused.

**Next action:** owner runs the evaluator from draft PR #370 in the isolated test environment and shares the aggregate-only output. The synthetic test shows that a pool with this category shape can fill ten under suitable ownership/family/artist conditions; it does not reproduce the exact private pool. Use the new actual-allocation-category and target/shortfall metrics to identify the missing constraint before proposing a behavior fix.

## Recommendation shortlist underfill — phase instrumentation continuation (2026-10-18)

Draft PR #370 was extended after the owner shared the aggregate-only schema-v2 profile comparison: 5 recommendations returned from 10 requested, 19 candidates resolved, 4 already owned, 10 recent-family-cap decisions, and category shortfalls against adjacent 4 / adventurous 3 / cross-genre 3 targets. The existing synthetic pool test can fill ten, so the private-pool stopping point remains unresolved.

The allocator contract and pure allocator now expose aggregate phase diagnostics: attempts in diversity reservation, category quota, family-cap relaxation, quota retry, unclassified fallback, plus final-fallback entry and attempts. The server response adds checked count, configured ceiling, and authoritative allocator decision counts; the profile comparison summarizes these fields without serializing identities. Regression tests cover phase reporting and aggregate comparison fields. No ranking/allocation behavior, ownership gates, or provider calls were changed.

CI on intermediate head 622ae19c0ecb67afa9f9a9ff2484690338359e88 exposed the server-size ratchet: navidrome_server.py reached 2656 lines versus the 2650 limit. The diagnostic output was compacted and a redundant blank line removed on the next head; this fix must be verified by CI on the exact final head. Keep captures, listening history, and candidate identities private. Publishing/deployment remain paused.

Next action: verify all four workflows on the final PR head, then have the owner rerun the evaluator from that exact source and share only aggregate diagnostics.

## P3 lookup-budget verification — 2026-10-19

- Branch `recommendation/p3-budget-verification` from GitHub main `8849e7e372381b508fb966a9069475a752b79310` (PR #393 merge).
- Verified that the uncached-resolution budget counter in `discovery_candidate_gathering.py` matches its code path: skips are counted only for refused uncached recordings. The owner's earlier 100-call, 0-skip result is consistent with the budget being reached exactly, so no counter defect was found.
- Added aggregate fields `uncached_resolution_budget_reached` and `cache_known_recordings` to `candidate_supply.cf_paging`. Page-level cache share is not reported.
- Added synthetic regression tests for exactly-at-budget, one-over-budget, and cache-known recordings after the budget is spent. No live provider calls.
- Local checks: `python3 -m unittest discover -s tests` passed, 894 tests. Candidate-gathering module: 20 tests passed.
- Updated `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` P3 status. P2 decision unchanged. No weights, windows, ownership, duplicate, or eligibility behavior changed.
- Not yet verified: exact-head CI on the four required workflows, merge, and any owner-authorized rerun of the page-2 measurement. No publishing or deployment.
- Next action: after CI passes on the PR head, the owner decides whether to authorize one aggregate rerun that reports the new fields.

## P2 freshness check and P3 merge record — 2026-10-19

- PR #395 (P3 budget counters and boundary tests) was squash-merged to `main` as `ba63de7fd39fa39ac1b7d2e9d2d645c91804f06c` from exact head `85ba55a508e93b2921777a8539e4ecb02871d087`. All four required checks passed on that head (compile, test-and-build, container-smoke, validate-container). Local unit suite before merge: 894 tests passed.
- P2 two-sided freshness check, owner-run on an isolated copy at `ba63de7`: snapshot A 200 returned, 103 resolved, 2 pages; snapshot B 200 returned, 101 resolved, 2 pages; same 30-day window. Overlap 144 shared, Jaccard 0.5625, 56 new, 56 dropped. Both captures passed integrity checks and remain private outside the repository. No identities or listening data were committed.
- Interpretation limits: one before-and-after pair. Shows CF output moves after a listening change; does not show quality improvement and does not settle whether CF reflects all-time history. P2 decision unchanged (unconfirmed).
- Publishing and deployment remain paused. No ranking, weight, window, or eligibility change.
- Next action: decide whether CF freshness needs a second bracketing pair before any supply change, or whether P1–P3 are sufficient to re-evaluate the supply gap.

## PR #405 merge record and candidate-supply eligibility counts — 2026-10-19

- PR #405 (false capture-failed warning for overlapping runs) merged to `main` as `bb25be0`. Recorded here as requested.
- Task: aggregate, identity-free eligible/unique/unowned counts at the release-type, ownership, and duplicate boundaries, with per-source counts, emitted by the offline replay. Rationale: the roadmap's candidate-supply next action asks for these counts before any replenishment change.
- Changes: `discovery_candidate_supply.py` adds `cf_release_group_rejection` (shared predicate), `summarize_cf_release_eligibility`, and `unowned_unique_by_source` plus `unowned_unique_by_source_count`. `discovery_candidate_gathering.py` calls the shared predicate in place of the inline checks, with the same ordering and outcomes. Tests in `tests/test_discovery_candidate_supply.py` (`EligibilityBoundaryTests`).
- Verification: 4 new tests failed before the change. Full unit suite: 907 passed. Compile check passed. Offline replay of the frozen capture, staged in a private directory, made zero provider calls. Its decision counts and stage values equal those from `main`. Only the two new keys differ. `reproduced: false` appears on untouched `main` too, so it is not caused by this change and is unresolved.
- Limits: release counts cover every CF payload on the tape, including recordings the artist cap or budget would skip, and count release entries rather than albums. The capture has no supplementary-source candidates. No replenishment was implemented.
- Publishing and deployment remain paused. No identities, listening data, or provider URLs were added to GitHub.
- Next action: decide, from these counts, whether the page-2 and supplementary supply gap needs a bounded replenishment change.

## PR #408 merge record — 2026-10-19

- PR #408 (aggregate eligibility and per-source counts in the candidate-supply replay) merged to `main` as `e29487d`. Recorded here as requested.
- Verification as recorded in the PR: frozen-capture replay made zero provider calls; decision counts and stage values matched `main`; only the two new keys differ. `reproduced: false` also appears on untouched `main` and remains unresolved.
- Limits: release counts are an upper bound over every CF payload on the tape, not over what the live artist cap or budget would process. The capture shows no supplementary-source candidates. No replenishment was implemented in #408.
- Publishing and deployment remain paused. No identities, listening data, or provider URLs were added to GitHub.
- Next action: bounded supplementary replenishment in candidate gathering, gated on eligible unowned shortfall (separate PR).

---

## 2026-10-19 — PR #411 replenishment offline shortfall measurement (synthetic fixture)

- Task: measure whether gated supplementary replenishment (PR #411) adds eligible unowned albums when the shortlist is short. The live runs never reached a shortfall with tag inputs, so this uses an offline fixture.
- Fixture: three synthetic CF albums, one owned; shortlist target 10. Eligible unowned before 2, after 4. Extra queries planned 2 and attempted 2, the fixed cap; extra candidates added 2. A release-type-filtered single, a duplicate, and a third un-issued query's album were not added. A rerun with the same inputs gave identical accounting.
- Test changes: added `test_shortfall_replenishment_adds_eligible_supply_within_caps`. Moved `test_tag_lane_counters_separate_empty_cache_from_no_listens` from after the `__main__` guard into the test class, where it now runs and passes. The module previously ran 8 tests; it now runs 10.
- Verification: `python3 -m unittest discover -s tests -p 'test_*.py'` ran 920 tests, all OK, on this branch. Compile check of the changed modules passed. CI on the exact PR head is still pending at the time of this entry.
- Limits: the tag selector is stubbed, so real tag yield, real MusicBrainz response variety, and the cold-cache ordering issue are not measured. No weights, windows, eligibility, ownership checks, or provider budgets changed. No live run, no owner data directory accessed. Publishing and deployment remain paused.
- Next action: decide whether tag selection should read the genre cache after the genre-lookup stage. That is a behavior change and needs its own measurement.

## 2026-10-19 — Candidate-pool genre prefetch for the supplementary tag lane

- Task: decide whether the tag lane should also prefetch genres for the top candidate-pool artists, so a cold cache matches warm exploration planning. #419 covered only the top 15 profile artists.
- Measurement: offline synthetic fixtures (20, 40, 60 CF albums; shortlist target 10), no live calls. Cold without the change planned 6 queries; cold with a prefetch limit of 5 planned 8, the same as warm. Eligible unowned matched warm (34, 50, 54). The prefetch itself added no uncached genre lookups at any limit from 1 to 60. The remaining cold-run cost comes from the two exploration queries now planned, and warm makes the same lookups.
- Change: `CANDIDATE_PREFETCH_LIMIT = 5` in `discovery_candidate_gathering.py`. An exhausted retry on a candidate stops only the candidate prefetch.
- Tests: `tests/test_discovery_candidate_genre_prefetch.py`, five tests. The full unit suite (`python3 -m unittest discover -s tests`) ran 928 tests, all OK, on this branch. Compile check passed.
- Added time: at most about 13 s per run in the worst case from the prefetch alone (non-retryable failures and one exhausted retry); a successful prefetch adds no spacing. The two exploration queries add about 3 to 10 s in the fixtures.
- Limits: synthetic fixtures; real tag yield not measured; no live run. No weights, windows, eligibility, ownership, duplicate identity, or provider budgets changed. Publishing and deployment remain paused.
- Next action: a live cold-cache run, with the owner's go-ahead, to compare against the fixture numbers.

## 2026-10-19 — PR #421 merged and live cold-cache pass recorded

- PR #421 (candidate-pool genre prefetch, `CANDIDATE_PREFETCH_LIMIT = 5`) merged as `d840150` after the four required checks passed on head `6da5994`. The merge needed the draft flipped to ready first.
- Live pass on the owner's test copy at `d840150`, fresh empty data directory, aggregates only: eligible unowned 45 before and after (replenishment not triggered); 8 tag queries planned and issued, 7 with yield and 1 HTTP error; 14 of 15 profile and 6 of 13 candidate genre-cache hits; 65 uncached artist-genre lookups; 2 CF pages, 200 recordings, 100-resolution budget fully used.
- The ~190 s estimate covers all 173 uncached requests in the run, including the 100 recording resolutions this change did not add.
- Limits: one pass, one profile, one cold state, no pre-change live comparison. The throwaway data directory and worktree were removed on the device.
- Publishing and deployment remain paused.

## 2026-10-19 — Uncached-budget sweep for CF candidate supply

- Task: check whether the 100 uncached-resolution budget limits candidate supply, using the real gathering path on synthetic fixtures with budgets from 25 to 300. No live call, no code change, no budget, weight, window, eligibility, ownership, or duplicate rule changed.
- Result (aggregates): on a concentrated cold pool, distinct artists are 3, 6, 10, 15, and 18 at budgets 25, 50, 100, 150, and 200. Shortlist ceiling reaches the 10-slot target only at 100, with no margin. Warm runs skip most dominant-artist recordings through the 10-per-artist cap, so their supply does not depend on the budget.
- Finding: the personal allocator takes at most one album per artist, and the replenishment gate counts albums. The gate can stay closed while artist supply is short (budget 50: 39 albums, 6 artists).
- Cost: about 55 s of extra recording spacing per 50 budget units at 1.1 s per call.
- Verification: offline sweep only; no unit tests run because no code changed. Documentation PR is a draft; CI on its exact head is pending at the time of this entry.
- Limits: synthetic album structure, no ownership, no non-CF sources, stubbed genres, computed spacing. Not calibrated to the owner's capture.
- Next action: add a distinct unowned eligible artist count to the aggregate diagnostics and test an artist-based replenishment gate offline. A live aggregate run needs Hamdi's go-ahead in words first.

## 2026-10-19 — Last.fm source and combination study

- Task: test whether a Last.fm similar-artist source can cut batch time without a quality drop, and whether combining it with CF helps. Aggregates only.
- Measurement: 15 seeds, `artist.getSimilar` on the owner's device, 0 failures, 23.8 s. Top-20 similar artists by match score, one MusicBrainz release-group browse each, 2 HTTP 503 failures, 31.5 s, 672 albums, 236 eligible by release type, 17 eligible artists before ownership and duplicate filtering. Frozen CF capture: about 110 s at budget 100, 7 eligible unowned albums from 5 artists after ownership.
- Result: the capped Last.fm path takes about 55 s, against about 110 s for CF. Supply is not directly comparable until the ownership filter is applied to the Last.fm side. Quality is not measured.
- Combinations: running both at today's settings is about 165 s. CF at budget 50 plus a Last.fm top-20 pass is about 110 s. Gated versions are about 55 to 80 s (sketches).
- Decision: no code change; the Last.fm source is not implemented and no budget, weight, window, eligibility, ownership, or duplicate rule changed.
- Next action: a prospective quality protocol and an offline gated-combination harness, with ownership and duplicate filters applied to both paths.

- PR #445, snapshot guard (roadmap 3.4), merged as `c5e9b17` from exact tested head `4eec946`. Full unit suite on the merge base: 1010 tests OK (local, `python3 -m unittest discover -s tests -p "test_*.py"` after `pip install -r requirements.txt`). Publication and deployment remain paused.
- Read-time ownership filter for the personal list (roadmap 3.4 item 2): reuses `discovery_snapshot.serve_snapshot` with the cached library snapshot. Four regression tests in `tests/test_discovery_list_payload.py`. Full local unit suite: 1014 tests OK. No live provider calls; no lookups added to the build path.

- PR #447 (roadmap 3.4 item 1, provider-failure count), squash-merged as `e932c51` from exact tested head `6b7e4bf`, based on main `80d796b` (PR #446). Four required checks green on that head (compile, test-and-build, container-smoke, validate-container). Merge after Hamdi's explicit go-ahead.
- Roadmap 3.4 item 1 (provider-failure count): personal builds report `provider_failure_count` (aggregate, from the bounded failure list), and `refresh_personal` passes it to the snapshot guard, so a run whose provider-failure share exceeds 0.2 keeps the stored list (owner chose threshold over strict). Branch from main `80d796b` (PR #446). No new lookups; per-run budget unchanged at 100 uncached. Added regression tests; full unit suite 1021 OK (`python3 -m unittest discover -s tests -p "test_*.py"` in a venv with `requirements.txt`). Background refill: the hourly scheduler runs by default; no on/off setting exists yet (gap). Publication and deployment remain paused.

## Recommendation roadmap archive (moved from docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md, 2026-10-19)

Preserved verbatim for history. Current state lives in the roadmap.

## Revised priorities after the 2026-10-18 roadmap review

This section supersedes the ordering in the phase list below where they conflict. Phase text is kept as history; the phase numbers are not a schedule. Evidence is bounded and aggregate-only; no artist identities or private listening rows are recorded here.

### What the evidence now shows

Source: the owner's private schema-v2 capture (`baseline-20261018-v2`, captured after both listening windows) and the 407-listen ListenBrainz export (2026-10-04 to 2026-10-18, about 13.4 days).

1. **Candidate supply is concentrated before ranking runs.** Of the 100 ListenBrainz CF recordings in the capture, 92 belonged to two artists. Those two artists were about 10% of the 407-listen export. The 100 recordings resolved to 19 albums from 8 artists. All 19 candidates came from CF; the supplementary MusicBrainz tag lane contributed zero candidates in this run.
2. **The pool is largely owned or duplicated.** Of the 19 candidates, 12 were already owned, 2 were duplicate identities, and 5 were selected. Only about 7 candidates were unowned before dedupe, so the shortfall to ten is a supply problem first, not a scoring or family-cap problem. This matches the corrected PR #370 replay.
3. **Ranking changes cannot fix membership when the pool is this narrow.** The profile comparison showed 17 of 19 candidates changing rank while the top-five set stayed identical. With most candidates from two artists, weight changes (Phase 1) have little room to alter which albums reach the list.
4. **The likely driver of the pool is a history-window mismatch, not yet proven.** Librarian's profile uses a 30-day window. ListenBrainz CF is generated from the account's listening history on the provider's own schedule, and the two dominant artists are a small share of the recent window. Hypothesis: CF reflects long-term history, so a 30-day profile cannot steer it. This explains the owner's observation that lists stay unchanged while daily listening changes. Not yet measured. The export here covers only about 13 days.
5. **Genre-lookup resilience is a secondary gap.** In the same capture, 12 of 14 recorded failures were artist-genre lookups that returned HTTP 503. The genre lookup path does not retry, unlike the recording lookup path, which retries 503 with backoff. Those artists then fall back to name-based classification and can land in `unclassified` (5 of 19 candidates). This affects category allocation more than supply.

### Revised ordering

**P1. Pool-level supply diagnostic (no behavior change).** Add bounded aggregates at the gathering boundary: distinct artists in the CF pool, top-2 artist share, resolved albums per artist, unowned unique albums before and after dedupe, and per-source yield. Report these in the existing aggregate diagnostics and the offline evaluator. Acceptance: the owner's frozen capture reproduces the figures above from aggregate output alone.

**P1 status (2026-10-18, feature branch, CI pending).** Implemented as aggregate-only diagnostics in `discovery_candidate_supply.py`, with no selection or provider-call change. From the frozen capture (aggregate output only): 92 of 100 CF recordings from two artists; 19 CF albums from 8 artists; all 19 candidates from CF; 12 owned and 5 selected. Correction: the two rows the allocator labels `duplicate_candidate` are unowned albums by an artist already selected (artist-cap rejections). Zero duplicate identities exist among the 19 candidates. The 2-duplicate figure in the handoff therefore reflects allocator attribution, not supply duplication.

**P2. Establish the history-window question before changing sources.** Confirm the owner's ListenBrainz all-time listen count and the CF input window (documented or measured against the provider). Acceptance: a written decision on whether CF reflects all-time history. If yes, the fix is in supply, not weights. If no, investigate provider output freshness and persisted-list freshness (Phase 0.3).

**P2 capture-warning fix (2026-10-19, code and tests; no live run).** The owner's snapshot A and B runs logged `capture failed (FileExistsError)` although both captures were intact. Cause from code: `recommend_new_music` reads the process-wide `LIBRARIAN_RECOMMENDATION_CAPTURE_PATH`, and `/api/recommendations` calls it directly, outside the personal-refresh lock. Two overlapping runs could both carry the same one-shot path; the first wrote the capture, and the second hit the refuse-to-overwrite check and logged a warning. No retry or third writer exists. Fix: `write_capture_safely` claims each capture path once per process, so later overlapping runs skip the write without a warning. Permissions (dir 700, file 600), the outside-repository check, and the immutability refusal in `write_capture` are unchanged. Regression test: `test_second_run_sharing_capture_path_does_not_warn_or_overwrite`, which failed before the fix. This changes no ranking, weights, windows, eligibility, or ownership. A different process writing the same path still logs a warning, which is correct.

**P2 decision (2026-10-19, docs-only): unconfirmed.** Neither the provider documentation nor the repository establishes whether CF output reflects all-time listening history, and no measurement has been made.

**P2 freshness result (2026-10-19, owner-run, aggregate only).** Measured on `main` at `ba63de7` (PR #395 merge, which contains the P3 budget counters) on an isolated copy, with two captures bracketing a known listening change. Snapshot A: 200 CF recordings returned, 103 resolved to albums, 2 pages, 30-day history window. Snapshot B: 200 returned, 101 resolved, 2 pages, same window. Overlap: 144 shared recordings, Jaccard 0.5625, 56 new in B, 56 dropped from A. Both captures passed their integrity checks and stayed outside the repository. This shows that CF output moves after a listening change within the 30-day window. It is one before-and-after pair: it does not show that recommendations improved, and it does not establish whether CF reflects all-time history, so the P2 decision above remains unconfirmed.
- ListenBrainz recommendation API ([recommendation.html](https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html)): documents `count` and `offset` (default 0). It does not say whether recommendations use all of a user's listens or a time window, gives no generation or update schedule, and describes the endpoint as experimental. A 204 response means recommendations "haven't been generated" for the user.
- ListenBrainz [data update intervals](https://github.com/metabrainz/listenbrainz-server/blob/master/docs/general/data-update-intervals.rst): no entry for CF recommendation generation.
- Code: `discovery_candidate_gathering.py` sends the CF request with only `count` and `offset`, so no time window is passed to the provider. The 30-day `listenbrainz_recent` call feeds the local profile only.
- Owner inputs (2026-10-19, aggregate only): the owner's all-time ListenBrainz listen count is 432, counted on the public profile the same day. The earlier 407-listen export was taken from the same profile earlier that day, so the difference is accrued listens, not a different source. A separate figure of 320 was a distinct-song count and is not a listen total. The export covers about 13.4 days and cannot separate all-time reflection from window reflection.
- Measured evidence: none. No CF freshness measurement has been run, so the decision that CF reflects all-time history is still open.
- Consequence: the gate is undecided. This decision changes no weights, the 30-day profile window, or the 14-day half-life. If a later measurement shows CF does not respond to known listening changes, the fix belongs in provider-output and persisted-list freshness (Phase 0.3), as stated above. The next action is a two-sided CF freshness check, which needs an authorized capture; the all-time count is now known. A two-sided CF freshness check (see "New ideas to evaluate") needs an authorized capture before it can run.

**P3. Bounded replenishment of the CF pool.** The ListenBrainz recording endpoint documents an `offset` parameter as well as `count`. Consider paging beyond the current `count=100` cap, with a fixed page budget. Each extra page adds MusicBrainz resolution calls at the ~1.1 s spacing, so the budget must be explicit. Options to evaluate offline:
- Page 2 or 3 of CF, with an artist cap applied before MusicBrainz resolution so that recordings from the two dominant artists do not consume the budget.
- Skip resolution for recordings whose artist is already known to be owned, using the library index, to save calls. Ownership must still be checked on the resolved album; this is an optimization, not a relaxation.

Acceptance: more eligible unique unowned albums and a higher fill rate on the frozen pool, with ownership, identity, eligibility, and provider-call counts unchanged or bounded. Report the offline result before any live change.

**P3 status (2026-10-19, merged).** Merged as PR #384 at merge commit `c0856d8`, from exact tested head `6e0de57`. Implemented bounded paging: at most two CF pages (offsets 0 and 100), a cap of 100 uncached MusicBrainz resolutions per run, which keeps the worst-case cold cost at the old single-page level, and a pre-resolution artist cap of 10 that applies only to cache-known recordings, because the CF response carries no artist. With a cold cache, page 2 adds no uncached resolutions; its recordings count only when cache-known. The frozen capture holds only page 1, so the effect of page 2 on supply is not yet measured. Acceptance is open until a page-2 tape is authorized and measured. Measured 2026-10-19 (owner-run, identity-free aggregates, from `main` at `46aa68e`, which includes #384, on a fresh copy of the same isolated data for each run). Two pages (stock): 2 pages fetched, 100 uncached MusicBrainz resolutions, 72 artist-cap skips, 0 budget skips, 124 resolved, 4 failed; 94 candidates, 23 owned; 71 unowned unique albums after dedupe, 65 after the artist cap. One page (temporary `CF_MAX_PAGES=1`, reverted): 1 page fetched, 0 uncached resolutions, 72 artist-cap skips, 28 resolved; 53 candidates, 9 owned; 44 unowned unique albums after dedupe, 43 after the artist cap. Page 2 therefore adds about 27 unowned unique albums before the artist cap and about 22 after it, on this snapshot. Open checks: (1) the stock run reached exactly the 100-lookup budget, yet the budget-skip counter reads 0, so the counter or the budget path needs verification before the figure is treated as clean; (2) no field reports page-2 recordings already cached, so cache hits are unmeasured; (3) the reported figure is unowned-unique-after-dedupe, not a strict eligible count, because release-eligibility filtering is not counted separately; (4) one earlier stock attempt returned an error whose class was not retained. Acceptance for P3 is therefore partly met: supply gain is measured, but the budget and eligibility checks above remain open.

**P3 follow-up (2026-10-19, code review and tests).** Open check (1) is resolved in the code, not by a live run. The budget check at the uncached-lookup path increments `resolution_budget_skipped` only when an uncached recording is refused after `CF_MAX_UNCACHED_RESOLUTIONS` calls have been made, so the counter agrees with the path. A stock run that makes exactly 100 uncached calls and reports 0 skips is consistent with the budget being reached exactly at its last uncached recording; the earlier run did not record whether a further uncached recording existed. The run now reports `uncached_resolution_budget_reached` (calls at or above the budget) separately from `resolution_budget_skipped` (calls refused), so the two cases can be distinguished in future aggregate output. Regression tests cover exactly-at-budget, one-over-budget, and cache-known recordings after the budget is spent (`tests/test_discovery_candidate_gathering.py`); no weight, window, or eligibility behavior changed. Check (2) is partly addressed: the run now reports `cache_known_recordings` (total cache-known recordings across both pages). It is not split by page, because page index is not carried past the paging helper, so the page-2 cache share remains unmeasured until an authorized run reports it. Check (3) and (4) are unchanged. The P2 decision is not changed by this follow-up. Acceptance for the budget counter is met on the code path; the owner's historical figure still needs a rerun to confirm the new fields.

**P4. Resilience of the genre-lookup path.** Give the artist-genre lookup the same bounded 503 retry used by recording lookups, and do not cache failures. Acceptance: fewer `unclassified` candidates in replay; provider calls stay within the existing budget; no change to ownership or eligibility.

**P4 status (2026-10-19, merged).** Merged as PR #385 at merge commit `3f0c57e`, from PR head `54b72fc`. The artist-genre lookup now uses the bounded 503 retry, and failures are still not cached.

**P5. Reactivate the supplementary lane only with a measured yield.** The profile-derived tag lane (PR #312) produced no candidates in the capture because its two searches returned 503. Add a yield metric per query before tuning it. If the lane still yields nothing under normal provider conditions, consider Phase 4 item 2 (similar-artist seeds) as a comparison, after checking the provider's current documentation.

**P5 status (2026-10-19, merged).** Merged as PR #387 at merge commit `d076e2d`, from exact head `fc21a3d`. Code inspection showed per-query yield is already recorded by P1, so the gap was retry, not measurement: the tag search made one request and dropped the query on a single 503. The change gives each tag search one bounded retry (2 s backoff, retryable statuses only, failures not cached) and stops the lane after a query that exhausts it, because MusicBrainz declines over-limit requests with 503 until the rate drops. Ranking, ownership, eligibility, and request spacing are unchanged. Acceptance remains open until an identity-free yield measurement on an authorized capture shows whether the lane produces candidates under normal provider conditions.

**Deferred until P1–P3 show a supply gain:** weight retuning (Phase 1.2), MMR re-ranking evaluation on a narrow pool (Phase 3.1), and cooldown calibration (Phase 3.2). MMR and cooldown cannot act on candidates that are not in the pool.

### New ideas to evaluate (not committed)

- **Two-sided check on CF freshness:** compare CF pool overlap across two replays spaced by a known listening change to test whether CF moves at all. Requires a new frozen capture, so it must be justified by P2 first.
- **Feedback as supply signal:** ListenBrainz documents recommendation feedback. Whether submitting feedback influences future CF output is unverified; check provider documentation before any design.
- **Owned-artist coverage lane:** for artists the owner already has, surface missing albums (Phase 4 item 1). This adds supply that is both owned-adjacent and unowned, and it does not depend on CF concentration.

### Open questions for the owner

Answered by the owner (2026-10-18):
1. Diversify supply. Later, expose a settings slider that lets users choose between maximum exploration and staying close to their taste. Supply work (P1–P3) comes first; the slider is a later product decision and must map onto the existing diversity-setting contract.
2. The ListenBrainz history available to the owner goes back only about two weeks, and the 30-day profile window was not a deliberate choice. Replace the 30-day window in the profile design (P2) with an explicit decision, and keep the CF-history hypothesis open because two weeks of history is shorter than the provider's full record.
3. Yes. An extra MusicBrainz budget of a few seconds per run is acceptable, bounded to one or two extra CF pages (P3).

Answered by the owner (2026-10-19):
4. Background refill is on by default and runs automatically, without any user action, because the app will run as a self-hosted service. It is specified in section 3.4. The batch flags' default (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`) remains an owner decision because it changes output.

### Recommendations after the owner's answers and the PR #377 merge

PR #377 is merged (merge commit `ee83330d7736b8b47d8e09883ce2b1ec24018212`). Its head was merged with `main` first (`ef87832`, a merge commit rather than a rebase, so no history was rewritten); all four required checks passed on `ef87832`.

The owner's answer that the ListenBrainz history covers only about two weeks changes the evidence:

- **Hypothesis 4 is weakened.** If the provider's history is only about two weeks, a long-history explanation for CF concentration is unlikely. The two dominant artists were about 10% of the two-week export, yet 92 of 100 CF recordings came from them. The next test is the provider's own behavior (how the CF pool shifts across replays with known listening changes), not the window length.
- **The 30-day profile window is not a product decision.** Do not lengthen it: the provider only has about two weeks of history. Keep the 14-day half-life and make the window an explicit, documented setting in a later change, after P1–P2 show whether it matters.
- **Exploration slider (later, backend first).** Map a single user-facing exploration value onto the existing `recommendation_diversity` contract (0–100, MMR penalty) rather than adding a second knob. Record the slider as a product item. Do not build UI in backend PRs.
- **Supply first.** Recommendations P1 (diagnostics) and P3 (bounded CF paging) remain the first implementation items; P4 (genre-lookup retry) is independent and can ship separately.

### First task (prompt for the next implementation thread)

```
Goal: add aggregate-only candidate-supply diagnostics at the candidate-gathering boundary (roadmap P1). No change to candidate selection, ranking, allocation, ownership, eligibility, or provider calls.

Read first: docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md (the revised section at the top and P1), docs/PROJECT_STATUS.md, docs/TEST_PLAN.md, discovery_candidate_gathering.py (the CF loop around the recording lookups and the artist-genre lookup), and the existing profile-comparison/offline evaluator and its tests.

Record, as bounded aggregates only (no artist names, album titles, MBIDs, tags, or URLs):
- CF recordings returned, resolved, and failed (by bounded error class).
- Distinct artists among resolved CF recordings; share of the top two artists.
- Resolved albums per artist (top-N shares only).
- Unowned unique albums before and after duplicate-identity removal, and before and after the artist cap.
- Yield per candidate source (CF vs supplementary), including zero-yield queries.

Acceptance criteria:
- Ranking, selection, ownership, eligibility, provider-call counts, and cache behavior are unchanged; prove this with the existing regression tests.
- New deterministic synthetic tests cover the aggregates, including an empty pool, a single-artist pool, and a provider-failure pool.
- The offline evaluator reports the new aggregates and needs no live provider.
- Reproduce, from the owner's frozen capture (aggregate output only, no identities), the figures: 92 of 100 CF recordings from two artists; 19 albums from 8 artists; all 19 candidates from CF; 12 owned, 2 duplicates, 5 selected.

Constraints: branch from current main; keep the diff focused; run the full unit suite and syntax checks; report exact commands and results; do not capture live data; do not commit private captures or identity-bearing output; do not merge or publish.
```

### Archived: immediate next step (2026-10-18)
## Immediate next step

PR #309 implemented 14-day half-life recency weighting, a smooth familiarity curve, and a recent-profile multiplier cap of 25%. PR #310 added a deterministic contrasting-profile regression, and PR #312 replaced fixed supplementary MusicBrainz tag searches with profile-derived queries plus a bounded exploration quota. PR #320 added the offline MMR evaluator; PR #326 added the preference contract and allocator integration. PR #329 now provides bounded ranked recommendation history (hashed identities only; 30-day retention, 2,000-row cap), with all four required workflows passing on exact PR head `613fd85715eaedc69f2375daf3cb6da6833c63bb`.

**Next recommendation-engine step (2026-10-18):** PR #341's final-shortlist evaluator metrics are merged. Define and review a rollout gate for relevance retention and category mix before any diversity UI work. A provisional gate is now documented in `docs/DIVERSITY_SETTING_ROADMAP.md`; it is not approved or passed because the existing private fixture has not been rerun with the new category metrics. Do not rerun the dismissed 35-combination/floor reproduction, collect a new live capture, or fabricate history for cooldown calibration. Keep cooldown constants uncalibrated, keep the diversity UI blocked, and leave publishing/deployment unauthorized.

### Archived: 3.4 implementation status (2026-10-19)
**Implementation status (2026-10-19; the snapshot guard is merged in PR #445, merge `c5e9b17`, head `4eec946`).** Implemented and tested without live calls: (a) `discovery_snapshot.py`, a pure policy module. `replacement_decision` rejects a build that is malformed or errored, has provider failures, is empty, or has fewer currently eligible items than the stored list (eligibility counted with an injected ownership predicate). `filter_snapshot` and `serve_snapshot` remove owned, duplicate, and unidentifiable items on read, keep stored ranks, and return aggregate counts only. (b) `refresh_personal` takes optional `read_previous`; when given, a rejected build leaves the stored list untouched, returns `status: rejected` with a bounded reason, and records a `rejected` outcome. A failed snapshot read fails closed. The server passes `_discovery_read_list`; without it, behavior is unchanged. Tests: `tests/test_discovery_snapshot.py` (16). Full suite: 1010 tests passed.

Not yet done, and why: (1) the provider-failure input is not yet produced: no bounded provider-failure count is carried in the personal payload today, so `provider_failures` defaults to 0 and the guard currently covers errored, empty, and smaller builds only; (2) the read path does not yet call `serve_snapshot` with a live library predicate, so the read-time ownership re-check is tested but not wired; (3) stale-while-revalidate serving is not changed: the existing hourly scheduler (24-hour threshold) already performs the default refill, and the single lock already serializes foreground and scheduler builds; (4) the default-path-only rule holds because refill calls `recommend_new_music` with its existing flags. Update (2026-10-19, this PR): item (2) is wired. The personal list read path (`discovery_list_payload.build_cached_discovery_list_response`) passes the existing cached library snapshot through `serve_snapshot`, so owned, duplicate, and unidentifiable stored items are removed on every read, with stored ranks kept. Aggregate counts appear in `diagnostics.read_filter`. If the library cannot be read, stored items are served unfiltered and `read_filter.ownership_checked` is `false`; this fail-open choice matches the For Me path and is a limitation. A read can page the Navidrome inventory when the library snapshot is older than 10 minutes, the same cost the For Me read already has. Update (2026-10-19, provider-failure PR, branch `claude/project-thread-ob6d8d`, after `80d796b`): item (1) is done. The personal build reports two aggregate integers: `provider_failure_count` (the length of its bounded failure list: metadata lookups, supplementary tag queries, and the profile genre circuit-breaker skip) and `provider_lookup_count` (the number of recording lookups the build made). Neither carries identities, URLs, or exception messages. `discovery_refresh.refresh_personal` passes both to `replacement_decision`, which rejects a build only when its failure share exceeds `PROVIDER_FAILURE_SHARE_THRESHOLD` (0.2, inclusive boundary). Owner choice (2026-10-19): threshold, not strict. Limitation: the numerator counts all failures while the denominator counts recording lookups only, so genre and tag failures can push the share up; the ratio is a conservative proxy, not an exact rate. Fail-safe: a missing or non-positive lookup count, or a missing failure count, is treated as no usable denominator, so any recorded failure rejects. Tests: `tests/test_discovery_snapshot.py`. Item (3), the hourly scheduler, already runs by default with no on/off setting; the roadmap's "the setting can be turned off" has no implementation yet and is a gap to decide, not a change made here.

### Archived: dated audits, shortlist diagnostics, Last.fm comparison, early-stop findings
## Private capture replay audit — 2026-10-18

A private capture from the pre-PR #350 replay implementation failed stable-output comparison despite equal recommendation/candidate counts. PR #350 subsequently froze ranking time, effective recommendation-history rows, and the diversity setting; the owner then replayed a fresh schema-v2 capture against its declared source revision successfully, with zero live provider calls. That newer result supersedes the old mismatch as the current reproducibility baseline; do not treat the pre-fix capture as evidence of a remaining current failure.

PR #356 fixed the counterfactual snapshot defect. `recommend_new_music()` mutates gathered album dictionaries while ranking, but capture serialization happens after ranking returns; the frozen snapshot could therefore preserve derived fields such as `recent_profile_bonus` and Last.fm tags/stats from the original profile. A same-profile replay can mask this because scoring recalculates the same bonus, while changing the profile can incorrectly divide out a bonus from the original profile. The replay serializer now strips ranking-derived fields when freezing and thawing candidate snapshots, while retaining gathering/provider fields and order. A regression test covers all known derived fields and confirms unrelated provider metadata remains intact.

PR #356 merged at `7b17b3f05ce735edd232d1e2895ec9c868918934` from exact final PR head `73261334020f6121582a6079414d282a38c1ada4`. All four required workflows passed on that exact head: Python syntax run `39151554270`, Docker packaging/full unit suite/build run `39151554276`, container runtime smoke run `39151554212`, and validation-only multi-architecture image validation run `39151554243` (publishing paused). The unit-test step and Docker build completed successfully; the container smoke and validation-only image workflows also succeeded. No assistant-side local tests were run.

Keep the real capture private; do not commit it, attach it to a PR, print its identities, or draw quality conclusions from it. Next, use the existing owner-only frozen snapshot and public timestamped listening history to compare actual engine outputs for the first/last five-day profiles. This is a responsiveness evaluation, not a future-listen outcome test; the available capture postdates both listening windows. The private capture was not accessed in this session, so the profile comparison remains open.

## Chronological listening-history audit — 2026-10-18

The public `abucalip/reports/listenbrainz-history.json` contains 407 timestamped listens spanning about 13.36 days (2026-10-04 to 2026-10-18). A descriptive comparison of the first and last rolling five-day windows found:

- First window: 2026-10-04 16:01:36Z to 2026-10-09 16:01:36Z; 138 listens, 36 distinct artist names, 37 distinct releases.
- Last window: 2026-10-13 00:47:28Z to 2026-10-18 00:47:28Z; 132 listens, 64 distinct artist names, 77 distinct releases.
- Eight artist names appeared in both windows; artist-name Jaccard overlap was approximately 0.087 (28 first-window-only and 56 last-window-only artist names). These are descriptive counts, not a recommendation-quality score. Artist-name normalization and window boundaries must be kept consistent in any repeatable evaluator.
- First-window leaders included The Dave Brubeck Quartet (13), Gorillaz (12), MF DOOM (11), and David Bowie (10). Last-window leaders included Arctic Monkeys (14), Mahmoud Ahmed (11), Antonio Carlos Jobim (10), and Gorillaz (8).

The available `baseline-20261018-v2.json` capture was taken at 2026-10-18 15:41:26Z, after both windows; it records five expected recommendations and a 1,733-album library. It is not an earlier recommendation snapshot and there are no listens in this history after its capture time. Consequently it cannot validly support a future-listen hit-rate, precision/recall, or nDCG evaluation for these recommendations. Using it as though it preceded the first window would introduce temporal leakage. Keep the capture and identity-bearing private evaluation artifacts out of public commits.

A preliminary diagnostic applied the existing familiarity multiplier to captured candidate base scores while holding those base scores fixed and changing only artist listen counts. For example, the multiplier for Arctic Monkeys changed from about 1.147 at zero listens to 0.820 at 14 listens; The Strokes changed from about 0.928 at five listens to 1.147 at three listens. This isolates one formula component only: it is **not** a full recommender replay and says nothing by itself about final rank order because profile families, Last.fm, allocation, eligibility, and diversity also affect output. Do not present its rankings or the raw-score-only overlap as full-engine results.

### Recommendations and next steps

1. Build a genuinely offline, deterministic profile-comparison harness using the real timestamps, but only after establishing a trustworthy frozen generation snapshot and replay tape. Freeze candidate pool, library/ownership eligibility, provider responses, and other non-profile inputs identically across runs; substitute only the defined first/last-window profile.
2. Execute the actual recommendation engine for both profiles. Compare ordered IDs and score deltas, top-k overlap, novelty/familiarity, artist/release diversity, category allocation, and ownership eligibility. Label this a *responsiveness* test, not a future-listen outcome test.
3. For outcome evaluation, capture a recommendation list at time T and evaluate against independent listens strictly after T over a predeclared horizon. Exclude all post-T events from generation inputs; report coverage and exposure limitations, and avoid causal claims because Librarian suggests music to acquire but does not influence what the user later chooses to listen to.
4. Keep the two evaluations separate: profile responsiveness can be tested without future listening; future listening is optional, independent observational evidence and is not Librarian's objective.
5. Do not tune ranking weights or claim quality gains from the current one-capture comparison. The replay mismatch documented above must be resolved before treating a capture as a deterministic evaluator fixture.

Status: history parsing and descriptive window comparison completed; familiarity-component arithmetic is diagnostic only. Counterfactual snapshot sanitation merged in PR #356 and all four required workflows passed on its exact head. Full-engine first/last-profile replay and a valid chronological outcome evaluation have not been run. The private capture was not accessed and no live provider calls were made.


## 2026-10-20 — PR #464 Save bookmark UI merged

- PR: https://github.com/abucalip/navi-librarian/pull/464
- Exact tested PR head: `6e3a815d9b98e73350e044c944187e62d716daca`.
- Merge commit: `de528089ecc2861c85a82c61a14abba87eb6bac6` (squash merge).
- Added Save/Undo bookmark controls to Personal, New releases, Classics, and artist deep-dive recommendation cards. Uses `save` and `remove_for_me` feedback with item metadata; no acquisition request is initiated. UI contract tests and Playwright stub harness results are described in the PR.
- All four required workflows passed on the exact PR head: Python syntax check, Docker packaging, container runtime smoke, and validation-only multi-architecture image validation. Publishing remains paused.
- Owner reports manual testing was performed, but the report was not submitted. The detailed manual checklist and deep-dive-card behavior therefore remain undocumented; no screen-reader pass is claimed.
- Not published or deployed; production runtime not verified.

## 2026-10-20 — PR #463 side-effect-free save merged; next task handed off

- PR: https://github.com/abucalip/navi-librarian/pull/463. Exact tested PR head `dcbe2dfc4a39842579713e69a29c03ead1aeb084`; merge commit `a12fb2f6eb6280dd4191fa520d9f420fe096f4cd` (squash).
- `discovery_set_feedback(action="save")` writes the `for_me` row and returns. No thread and no slskd search; `_discovery_auto_acquire_for_me` and its lock were removed, as were the `auto_acquisition` and `note` response fields. Existing rows' `auto_acquisition` metadata is left alone. The unused `auto_acquire_for_me` setting (key, default, API validation, tests) was retired; stale stored values are ignored. `dismiss`, `dismiss_artist` and `remove_for_me` are unchanged. `navidrome_server.py` is 2,448 of 2,650 lines.
- All four required workflows passed on the exact PR head. Publishing remains paused; not deployed; no live run.
- With PR #464 the save loop is complete end to end. The seed's real tag yield is still unmeasured. Next task (handed off in `CLAUDE_CLI.md`): aggregate-only seed counters in `run_metrics`, no behavior change; a live measurement afterwards needs the owner's go-ahead.


## 2026-10-20 — PR #467 bounded CF error-class diagnostics merged

- PR: https://github.com/abucalip/navi-librarian/pull/467
- Exact tested PR head: `857a180ed6e93414122e0d23e9e413222a8606c0`; squash merge commit: `27942379095cf41654fcb6298b3e9b0d9f56d730`.
- Expanded the bounded exception-class allowlist for common transport/protocol and decoding failures. Unknown names still collapse to `other`; exception messages, URLs, and credentials are not emitted. No candidate selection, provider calls, quota, budget, or filtering behavior changed.
- All four required workflows passed on the exact PR head. The Docker packaging workflow's `Run unit tests` step completed successfully; container runtime smoke and validation-only image validation also passed. Focused tests were reported by the PR author; no separate local suite run was performed in this session.
- PR merged after confirming the current head SHA. Publishing/deployment remain paused; no production runtime verification.
- Next action: continue the recommendation-engine candidate-supply investigation using aggregate-only diagnostics; keep identity-bearing captures private.
