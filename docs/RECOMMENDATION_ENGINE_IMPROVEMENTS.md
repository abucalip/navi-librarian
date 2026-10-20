# Recommendation engine improvement roadmap

Status (2026-10-20): active. This file keeps only what is still needed for the next work: current state, open decisions, guardrails, the phase plan, and evaluation rules. Dated evidence, merge logs and superseded orderings are archived in `PROJECT_LOG.md` under "Recommendation roadmap archive". The owner's sustained real-world evidence prioritized ranking responsiveness; no technical root cause is claimed as proven. Publishing and deployment remain paused.

## Current state (2026-10-20)

Merged on `main`: candidate-supply diagnostics (PR #382); bounded CF paging with a 100-call uncached budget (PR #384, budget counter #395); retries for artist-genre and tag lookups (PR #385, PR #387); gated supplementary tag searches (PR #411); batch resolution behind flags, both off by default (PR #430); title-marker batch filter, off by default (PR #429); genre circuit breaker, default off (PR #431); tag-lane early stop, default off (PR #442); genre-breaker gate on profile prefetch (PR #444); snapshot guard (PR #445); read-time ownership filter on the personal list (PR #446, merge `80d796b`); provider-failure threshold in the snapshot guard (PR #447, merge `e932c51`); cold-start batch path for first builds only (PR #450, merge `27bdcc2`, cold-start-only, tests `tests/test_discovery_cold_start_batch.py`); run timing and provider-call counters (PR #451, merge `42b6d81`, exact head `a1d061b`); cache and cross-run candidate-resolution tests with roadmap 2.3 marked implemented (PR #449, merge `c90e43b`).

Per-stage run timers: the counters from PR #451 now include aggregate seconds for metadata resolution, genre prefetch, the supplementary tag lane, replenishment, and the genre lookup stage. Merged as PR #452 at `76030c0f70e59ebe05b2e10ca5fcfc6a4fc75bd9` from exact head `856df1f6ed50353ee671c6b129d51e86a49b4ad7`; all four required workflows succeeded on that head. See "Per-stage run timers" at the end of this file.

Merged 2026-10-20: PR #456, roadmap 3.3 feedback as a bounded signal, on by default (merge `4680a187734dc05516ebdca639b8a003366aaeb2`; all four required workflows passed on head `7b0a3a0`).

Merged 2026-10-20: PR #458, roadmap 3.4 automatic refill on/off setting, default on (squash merge `7fb140e6d915ada98974d1b56002c03d4e5cfef0`; all four required workflows passed on head `d72d650`; owner approved the `app/api/**` and `navidrome_server.py` changes). 

Merged 2026-10-20: PR #459, roadmap 3.4 stale-while-revalidate read path (squash merge `b09c9544cd96828a732fea04818729fc381cee0e`; all four required workflows passed on exact head `44148af78a93a0a3be27a1f17ec6cc196e678bf6`; owner approved the `navidrome_server.py` and `app/api/**` scope). Roadmap 3.4 is now fully implemented. The 3.3 positive tag-query seed followed (PR #461).

Merged 2026-10-20: PR #465 (`6e1054b`, exact head `d962dd1`; all four required workflows passed), aggregate `save_seed.*` counters in `run_metrics.counts` plus one owner-approved live sample (4 saves: 1 initial query changed, 0 in replenishment). See roadmap 3.3 status.

Merged 2026-10-20: PR #463 (`a12fb2f`, exact head `dcbe2df`; all four required workflows passed), `save` is a side-effect-free bookmark: it writes the `for_me` row and starts no slskd search, the `auto_acquisition`/`note` response fields are gone, and the unused `auto_acquire_for_me` setting was retired. PR #464 (`de52808`, exact head `6e3a815`; all four required workflows passed) added the UI Save control (front end only; updates in place because the list endpoints hide saved albums).

Server headroom: PR #460 (`4201ed9`) extracted the deep-dive candidate collection and PR #463 removed the auto-acquire thread, so `navidrome_server.py` is 2,448 of 2,650 lines. Agents never run the full unit suite on PRs (owner rule, 2026-10-20); see `CLAUDE_CLI.md`.

Open items:
- **CF freshness (P2):** undecided. No measurement has shown whether CF reflects all-time history. Needs an authorized two-sided capture; do not start without owner approval.
- **Refill toggle (3.4):** background refill runs by default on an hourly cycle, with a 24-hour staleness threshold. The owner decided on 2026-10-19 that it defaults to on and can be turned off. Built in PR #458 (`7fb140e`): persisted `automatic_refill_enabled`, default on, gates the hourly scheduler; `GET/PUT /api/settings/automatic-refill`.
- **Default-on decisions (owner):** batch resolution (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`), the genre circuit breaker, and the tag-lane early stop are all off by default. Each changes output or call pattern, so each needs an owner decision.
- **Early-stop live measurement:** not yet run live. Needs owner "yes" for any live run.
- **Exploration slider (product):** audited 2026-10-20 (see "Exploration setting audit"): no new backend mapping is needed, but the Settings UI stays **blocked** by `docs/DIVERSITY_SETTING_ROADMAP.md` gates until cross-pool and real-library evidence exists. No UI in backend PRs.
- **Candidate supply diagnosis (2026-10-20):** offline trace done (see "Candidate supply diagnosis" at the end); the budget-skip hypothesis is **refuted**. PR #467 (`2794237`) names the failing exception classes. The live cold/warm pair is **not run**: the app's ListenBrainz client times out. Retry later. Next roadmap item: Phase 4.3, wider CF pool (see `CLAUDE_CLI.md`).
- **Diversity setting:** paused by the owner (2026-10-20). Do not build the UI or tune the mapping; revisit only when supply gives pools large enough to reorder.
- **Last.fm source:** parked by the owner (2026-10-19). Recorded only as a possible future recommendations-source option. Do not start a quality test or a combined path without a new decision.

Deferred until candidate supply shows a gain: weight retuning (Phase 1.2), MMR re-ranking evaluation (Phase 3.1), cooldown calibration (Phase 3.2).

Known limits: candidate supply is still narrow in the owner's capture; the batch path has no secondary release-type filter (only the title-marker filter); the ListenBrainz history available is about two weeks. Each new change is measured offline first.

## Goal and guardrails

Recommendations should respond meaningfully to changes in recent listening and the library, avoid repetitive lists, and balance relevance with novelty and useful exploration.

Preserve:
- Owned-album exclusion, reliable artist identity, and compilation/remix/non-album release filtering.
- Existing discovery-list/API response contracts, acquisition behavior, and persistence. MCP transport/registration is retired.
- Bounded provider calls, cache/rate-limit behavior, and graceful failure paths.
- Deterministic, fixture-driven verification; no live provider dependency for correctness tests.
- Publishing remains paused. No UI redesign or new discovery mode is part of the first implementation.

Do not assume a diagnosis before measuring it. In particular, repeated recommendations may arise from candidate supply, scoring/allocation, cache/persisted-list freshness, or some combination.

## Current implementation baseline (verified by read-only audit)

The audit inspected `navidrome_server.py::recommend_new_music`, `discovery_candidate_gathering.py`, `discovery_recommendations.py`, `discovery_list_payload.py`, and `app/api/discovery.py`. The audit ran no tests and changed no behavior.

### Candidate sources and refresh

- Discovery refresh freshness is a separate layer from recommendation candidate/scoring behavior. PR #299 adds direct tests for missing/expired/malformed/non-finite timestamps and isolates cache-read and refresh failures per list, so one failing list does not prevent later lists from being checked in that hourly cycle. The scheduler keeps its existing hourly cadence, 24-hour stale threshold, list order, and callbacks. Warning logs are intentionally bounded to list, stage, and exception type; do not log provider exception messages or URLs.

- **ListenBrainz collaborative filtering (CF) is already the primary candidate source.** Candidate gathering requests `cf/recommendation/user/<user>/recording` with `count=100`, resolves recording MBIDs through MusicBrainz with approximately 1.1-second spacing and a 180-day cache, and groups recordings into albums using the maximum recording score per album. This avoids automatically favoring albums with more tracks.
- Fixed MusicBrainz tag searches are the **supplementary** candidate source, not the primary recommender. The supplementary path has a fixed set of 20 style/regional tag queries, can add up to 60 candidates, and caches search results for 30 days.
- CF output is externally generated on ListenBrainz's schedule, and at most 100 recordings are requested. Repeated refreshes may therefore receive a similar candidate pool even after listening changes. This is a hypothesis to measure, not yet a proven root cause.
- Discovery output is persisted through `discovery_refresh.py`. Refresh triggers, scheduler behavior, and list freshness must be traced separately from candidate/scoring behavior.
- Artist genre metadata is cached for 90 days; Last.fm album popularity is cached for 30 days. Stable metadata caching can remain long-lived if profile-dependent ranking is recalculated.

### Existing score composition

The current score is multiplicative:

```
discovery_score = CF score
                × familiarity
                × exploration-family bonus
                × recent-profile bonus
                × Last.fm popularity bonus
```

| Term | Current behavior | Audit implication |
|---|---|---|
| Familiarity | 0.75–1.35 based on recent plays of the candidate artist; 0 plays gets 1.35, 11+ plays gets 0.75 | Step function, 1.8× spread; strongly rewards unheard artists |
| Exploration-family | 1.00 or 1.10 | Flat bonus when a candidate's family is in the exploration set |
| Recent profile | 1.00–1.10, calculated as 1 + 0.10 × average family share | Recent listening changes score by at most 10% |
| Last.fm popularity | Up to approximately 1.12, using log-scaled listeners/playcount | Applied only to the top 40 candidates after earlier terms; can further bias the head of the pool |

Listening counts currently use a flat 30-day window without recency weighting. Taken together, the current score appears novelty-biased rather than strongly taste-responsive: recent-profile influence is comparatively weak while familiarity has the largest spread. Confirm with the evaluation harness before selecting new weights.

The Last.fm path divides out and re-applies the profile bonus when tags change the family match. This may be correct but is fragile; a single score-component record would be easier to reason about and test.

### Allocation, feedback, and hidden preferences

- Allocation targets are 40% adjacent, 30% cross-genre, and the remainder adventurous, plus four fixed one-slot regional targets. `family_cap=1` and `max_checks=60` are also configured. Inspect `discovery_personal_allocator.py` to establish precisely what `family_cap` constrains before changing it.
- The four fixed regional slots and fixed supplementary tag searches can reserve capacity without current profile evidence. Replace these with profile-derived selection; do not ban those styles.
- `discovery_recommendations.py` contains artist-name sets used as regional/style classification overrides. Prefer normalized provider metadata and tags. Retain any exception only with a documented reason and regression test.
- Feedback actions (`save`, `dismiss`, `dismiss_artist`, `remove_for_me`) currently filter stored lists in `discovery_list_payload.py`; they do not affect scoring or query selection.
- Candidates already expose `recent_profile_bonus`, `lastfm_popularity_bonus`, `genres`, `discovery_category`, and `diversity_style`. Add backend/debug-only diagnostics before building UI explanations.

## Roadmap and decision gates

Phases are ordered by dependency and evidence. Do not skip measurement to tune weights by intuition. Each phase should be a focused, reviewable PR (split independent work only when it does not obscure the decision gate).

### Phase 0 — Diagnose candidate supply and establish a measurable baseline

**Priority: first implementation unit. No ranking behavior changes in this phase.**

#### 0.1 Pool-fingerprint diagnostic

**Private baseline review (2026-10-17):** the frozen capture reported 100 CF recordings returned, all 100 with metadata, and 83 resolved albums. Both CF-recording and final-list Jaccard overlap against the previous stored snapshot were 1.0; supplementary cache counters were 14 hits and zero misses. The same capture had zero metadata lookup errors, zero unclassified recommendations, and met all category targets. This is consistent with an unchanged candidate pool and final list across that adjacent comparison. It is only one comparison: it does not establish a longer-term trend, show whether the listening profile changed between snapshots, or prove whether stable input, persisted-list freshness, ranking, or allocation caused the repeated output. Do not change policy on this evidence alone. The capture's limitations include the 100-recording CF cap, incomplete community-supplied genre tags, bounded genre lookup, a rolling 30-day profile, cached Last.fm popularity, and imperfect ownership matching. Keep the capture private; record only bounded aggregates in repository documentation.


On each recommendation refresh, record privacy-conscious, bounded diagnostic data:
- Fingerprint/set of CF recording MBIDs (do not log credentials or raw personal data beyond the identifiers needed for this diagnostic).
- Number of recordings returned, number resolved, and resolved album count.
- Jaccard overlap of the current CF recording set with the previous refresh's set.
- Supplementary-query cache hit rate and candidate counts by source.
- Profile/list refresh timestamp and final list identity/overlap where available.

Determine where to store this safely and whether existing diagnostics or cache records already cover part of it. Keep this diagnostic bounded and avoid turning normal logs into a high-volume per-recording trace.

**Decision gate:** high CF overlap suggests a candidate-supply/freshness limitation; low CF overlap with repeated final lists points toward scoring, allocation, eligibility, or persisted-output behavior. Do not infer causation from one refresh pair.

#### 0.2 Fixture-based offline replay harness

Build a deterministic harness from frozen fixtures for listening history, CF payload, genre cache, and relevant feedback/library state. No live provider calls should be required. Replay chronologically: use listens through day T to generate recommendations, then inspect whether recommended **unowned artists** appear in listens during T to T+14 days.

Report:
- Artist-level hit-rate@k and nDCG@k (album-level outcomes are too sparse for the primary replay measure).
- Responsiveness: candidate-pool overlap and ranking changes between contrasting profiles.
- Novelty, intra-list diversity, artist/style spread, repeat rate, and relevance retention.
- Eligibility/rejection counts for owned albums and ineligible/ambiguous releases.

Library owners may already own and play music, so evaluate on unowned artists and treat replay hit rate as a relative comparison, not an absolute prediction of user satisfaction. Avoid leakage: future-window listens must not enter the profile or candidate-generation fixtures for day T. Document fixture construction and the limits of historical replay.


**Full-engine profile responsiveness evaluated by the owner (2026-10-18; harness PR #361).** Against the same frozen schema-v2 candidate/library snapshot, the first five-day profile (138 listens, 35 normalized artists, 60 genre-classified listens, 6 families) and last five-day profile (132 listens, 63 normalized artists, 26 genre-classified listens, 4 families) each ranked 19 candidates and returned five recommendations. The top-five membership was unchanged (5/5 overlap, Jaccard 1.0), but two positions changed. Seventeen of the 19 shared candidates changed rank; maximum rank displacement was 14. Both profile runs were repeatable, 19 captured Last.fm entries were used in each run, and zero network providers were called. Controls held the candidate/library snapshot, ownership, ranking timestamp, recommendation history, diversity setting, and Last.fm responses fixed. This establishes ranking responsiveness below/within the top-five ordering, but not shortlist membership responsiveness, recommendation quality, or profile-driven candidate-generation responsiveness. The capture postdates both listening windows, so future-listen hit-rate/nDCG and causal claims are out of scope. Harness merge commit `054b7aa71d632821f3d7a3811ab5f24f63003366`, exact tested head `257a2fa37ab0831e42769463107a2f05c1e7b220` (733 tests; all four required workflows passed).

**Decision / next task:** do not tune profile weights based on this single frozen pool. Inspect score-component attribution and shortlist/allocation behavior to explain why 17/19 candidates move in rank while the top-five set stays identical. Add identity-free aggregate diagnostics and deterministic regression coverage, then repeat the same comparison before choosing weight changes. This is a responsiveness diagnostic, not a future-listen quality evaluation.


#### 0.3 Trace refresh and expose score diagnostics

**Refresh/freshness audit started in PR #299.** Manual reads return persisted discovery lists rather than regenerating them. The scheduler checks five cached records hourly and refreshes records at least 24 hours old. Personal refresh is synchronous at the explicit refresh entry point; other discovery refreshes are launched in background threads. The scheduler previously wrapped the entire list loop in one silent exception handler, so a read/refresh failure could stop processing later lists for that hour without leaving a useful diagnostic.

PR #299 adds a directly tested stale-reason classifier (missing, expired, invalid timestamp), isolates read/refresh failures per list, and logs bounded list/stage/exception-type diagnostics without provider exception messages. This is operational visibility only; it does not change score, candidate, or allocation policy. CI must confirm the scheduler wiring and existing behavior.

Refresh-origin tracing is now implemented on the working branch: the personal-list refresh adapter distinguishes manual refresh requests from the hourly scheduler, passes the origin into the recommendation pool snapshot, and persists only the latest bounded outcome per origin (success, error, or already-running). Persisted outcome data excludes exception messages, URLs, credentials, and candidate identities. CI and final-head review remain required before this is considered complete.

Aggregate recommendation diagnostics are implemented and merged in PR #304. Bounded source counts, base/final score and bonus distributions, profile-evidence counts, cache counts, and eligibility/selection outcomes are persisted with the existing pool snapshot. The aggregate omits candidate identities and raw tags and does not expand the public API response. All four required workflows passed on exact final head `808ed2621ec5a3e9db3a05083e5fb1dcc828e4cb`; merge commit `19435d5deea69b188d920cf375ef924ec3b14a97`. Review the real replay baseline's metrics and limitations before any score, source, or allocation changes.


**Phase 0 decision (2026-10-17): closed for prioritization at the owner's direction.** The private exact replay was reproducible (10/10 recommendations, 197 provider events, 40 Last.fm events, zero network providers) and the compared CF/final-list snapshots were identical (Jaccard 1.0 each). More importantly, the owner reports sustained use since v0.1 publication and overwhelmingly unchanged recommendations despite daily listening-history changes. Treat this longitudinal product experience as sufficient evidence to begin improving responsiveness. Do not require more snapshot collection before proceeding. The capture and synthetic fixture remain useful regression/evaluation tools, but neither proves a specific technical root cause or future-listen relevance.

The initial implementation target is the ranking/profile path: weight recent listens more strongly, reduce the coarse familiarity step function, and strengthen profile-derived influence while keeping cached metadata separate from profile calculations. Candidate-source and persisted-list freshness can be revisited only if behavior-focused tests and subsequent user evaluation show that ranking responsiveness is insufficient.

**Acceptance gate for Phase 0 — accepted for prioritization**
- Existing capture/replay and aggregate diagnostics are available for reproducibility and regression investigation.
- The owner has supplied sustained real-world evidence that current recommendations do not respond adequately to changing listening history.
- Further diagnostic collection is not a prerequisite for behavior changes.
- Existing ownership, release eligibility, API contracts, and safe provider-call limits remain invariants.

### Phase 1 — Make listening signals time-sensitive and proportionate

Proceed based on the owner's sustained real-world evidence that recommendations remain overwhelmingly unchanged while listening history changes daily. Use deterministic fixtures and the existing replay harness for each candidate formula; do not wait for further live diagnostic snapshots.

#### 1.1 Time-decayed profile

Replace flat scrobble counts with a 14-day half-life decay anchored to ListenBrainz listen timestamps, deriving artist and family/tag weights from the same per-listen weights. The initial implementation keeps the existing 30-day retrieval window to avoid changing provider/capture contracts; consider a longer stable-taste window separately if the responsiveness checks show it is needed.

Use those weights both in scoring and supplementary query selection. Keep profile computation separate from cached provider metadata so cached genres do not freeze the profile.

#### 1.2 Rebalance familiarity and profile relevance

Replace the step-function familiarity term with a smooth curve peaking at low-but-nonzero weighted familiarity, rather than awarding the maximum only to never-played artists. The current implementation begins with a bounded smooth curve and decayed inputs, and increases the profile multiplier cap from 10% to 25% so current taste can compete more strongly with familiarity and popularity.

Choose curve/weights using deterministic contrasting profiles and the existing replay harness, supplemented by the owner's qualitative evaluation. Inspect the current multiplicative score for interactions; consider representing components explicitly and calculating the final score once to avoid fragile divide/re-apply behavior in the Last.fm tag path.

Keep Last.fm popularity capped and normalized as a weak tie-breaker or cold-start fallback. It must not routinely overpower personal relevance.

**Acceptance gate:** replay results show more responsiveness without an unacceptable regression in relevance, novelty, diversity, or deterministic repeatability. Numeric targets should be chosen after baseline collection rather than invented in advance.

**Contrasting-profile regression (PR #310):** the adapter test runs the same two candidates and provider scores against two different recent-listening histories, with cached genre metadata held fixed. It asserts both score ordering and the leading recommendation reverse when the listened-to artist changes. This verifies profile sensitivity through the real recommendation adapter without live providers or private captures. It does not by itself establish production-list freshness or future-listen relevance; evaluate those qualitatively after the change is merged.

### Phase 2 — Make candidate generation reflect the current profile

Proceed after the Phase 1 responsiveness changes have been evaluated, and coordinate query changes so they can be evaluated independently from score changes.

#### 2.1 Replace fixed supplementary tag searches

PR #312 merged at `5b23b08556c467a67b0b6cdbe7148dc069eda6f1` from exact final head `dc957f9eb1d817fcc2117f819c0d12be6663b142`. The implementation derives up to six MusicBrainz tag queries from cached genres weighted by the 14-day-decayed listening profile, plus up to two exploration queries from tags in the CF candidate pool. Query selection is a pure, directly tested helper; it performs no I/O and does not change cache TTL or the provider-call path. Fixed regional query constants and four fixed regional one-slot allocation targets were removed. All four required workflows passed on the exact final head; the Docker unit suite reported 631 passing tests on the preceding code/documentation head. Phase 3 will evaluate a measured diversity re-ranker. Keep the exploration quota bounded and ensure cache-read/provider failures do not discard primary CF candidates.

Remove fixed regional one-slot targets and replace them with measured diversity selection (Phase 3) or profile-derived allocation. If the owner wants specific regional styles favored, expose them as explicit, empty-by-default pinned interests rather than code constants.

Keep candidate caps, rate limits, diagnostics, and graceful provider-failure behavior. Query selection must respond to changed profile fixtures even when the genre cache is unchanged.

#### 2.2 Review classification overrides and source provenance

**Implemented and merged in PR #314** at `295da73b9d279e944501c5c3d28866e8b1b7123f`, from exact final PR head `21e5f8da161613427748e995f5b542c9f24c0859`. Provider genre tags now take precedence over hardcoded artist-name exceptions in recommendation-category and diversity-style classification. Name-based regional classification remains only as a fallback when provider genre metadata is absent; direct regressions cover fallback behavior and conflicting available tags.

Recommendation candidates now carry a bounded `discovery_sources` list. The active personal-recommendation pipeline distinguishes ListenBrainz CF, profile-derived tag searches, and candidate-pool exploration tag searches; duplicate candidates merge/deduplicate source labels before eligibility and ranking through a directly tested helper. The legacy singular `discovery_source` field is retained for compatibility. Aggregate diagnostics count each recognized source independently while keeping old records readable and rejecting arbitrary source labels, so tag names and candidate identities are not persisted in source counts. Provenance is passed only to the private aggregate summarizer; the existing public debug payload shape is unchanged. Other source types (similar-artist lookup, library gap, new release, optional popularity fallback) are reserved in the aggregate allowlist but are not claimed as active sources in this pipeline.

**Acceptance gate:** contrasting profiles generate different supplementary queries where metadata supports it; provider tags override name heuristics when present; missing metadata still has a tested fallback; duplicate candidates retain every actual source without duplicate labels; aggregate source counts stay bounded and identity-free; exploration remains available without fixed slots; provider calls remain bounded.
#### 2.3 Persisted candidate resolution for per-run time (already implemented by the `mb:recording` cache; cross-run test added, 2026-10-19)

Status: the default path already persists resolutions. Every successful MusicBrainz recording lookup is stored under `mb:recording:{mbid}` with a 180-day read TTL, so a repeat MBID costs no call. Ownership and eligibility are checked after the cache, and ineligible outcomes are cached too, because the raw record is stored before eligibility runs. Existing tests cover cache-known skips and the 100-call uncached budget within one run. This branch adds offline tests that cover two consecutive runs: overlapping CF output resolves only the new recordings, and an identical second run makes zero MusicBrainz calls. No new store was built.

Cold-start batch (owner decision 2026-10-19, "cold-start only on"): when no stored personal list exists, `refresh_personal` passes `_cold_start` through to gathering, which then uses the batch path (`COLD_START_BATCH_ENABLED = True`, title filter always on for that path). Steady-state builds keep `CF_BATCH_RESOLUTION_ENABLED` and `BATCH_TITLE_FILTER_ENABLED` off. Cold-start output has no secondary release-type filter beyond the title markers, so it is a first-run list only. Tests: `tests/test_discovery_cold_start_batch.py`. No live timing has been measured yet.

Deferred gap: the flagged batch path (`CF_BATCH_RESOLUTION_ENABLED`) writes nothing back. Its results are synthesized and lack secondary release types, so they must not be written under the default key. Any persistence needs its own namespace and an owner decision, and batch lookups are already cheap (about 0.7 s in the flags-on run), so the gain is small. Open measurement: how often CF recordings repeat across consecutive live runs has not been measured. That rate decides whether more persistence helps.

Original proposal (2026-10-19), kept for reference:

Evidence: owner priority (2026-10-19) is to reduce the time to build a batch without adding lookup time. The Mac timing runs on main `76ec40e` show that uncached MusicBrainz resolution dominates: one flags-off run made 277 uncached requests with 76 throttled, taking 359 s; a flags-on run made 63 uncached requests and took 46 s. Timings are single-sample and noisy (flags-off runs ranged 237-359 s), so treat the gain as directional until repeated.

Proposal: store resolved candidate metadata (recording to release group, artist identity, and source) in a TTL store keyed by MBID, reusing the existing 180-day recording cache horizon as the upper bound. Every read re-checks ownership against the current library; the store never supplies ownership. Hard release eligibility and the per-run uncached budget (100) are unchanged.

Cold-start mode: the batch-resolution flags stay off for steady-state output. They may serve as a clearly labelled cold-start path, used only when no stored resolution exists for the profile. Flag-on output must not silently replace flag-off output, because the batch path has no secondary release types and the title filter is heuristic.

Alternatives considered: caching whole ranked lists (section 3.4) fixes freshness and serving latency but not lookup time, so it does not replace this item.

Acceptance: with identical inputs, a warm store and a cold store produce the same final list; zero owned or duplicate items are served from the store; uncached request count falls on a warm run; the store holds no listening rows, only MBIDs, dates, and eligibility outcomes. Metrics are aggregate: uncached request count, throttled count, and wall-clock time, measured over at least three runs per mode.

### Phase 3 — Improve list diversity and recommendation freshness

#### 3.1 Greedy MMR-style re-ranking

**Identity-free evaluator CLI verified; backend preference-contract/integration is next (2026-10-18).** The owner ran `recommendation_mmr_evaluate.py --identity-free` against the existing private fixture in the isolated PR-320 source environment (`acb437f85d8d5c8ae2e6cdb5240457423e9b6e64`). The fixture's capture source SHA is `d8c1f3de5180b35919f55c304d55e5c939dad373`. The command exited 0; no network providers were used and the provider tape was not replayed. Aggregates: 83 gathered albums, 1,733 library albums, 66 scored candidates, 17 rows rejected for hard eligibility or missing score, and 10 baseline recommendations with captured scores.

The CLI evaluated lambda values 0, 0.1, 0.25, 0.5, 0.75, and 1.0. Each result selected 10 items from the evaluator's eligible pool, with 10 unique artists, zero duplicate non-empty artist keys, and deterministic repeated results. Lambda 0 had mean pairwise similarity 0.1044, retained 7/10 baseline items, and retained 85.6% of baseline relevance score. Lambda 0.25/0.5 had similarity 0.1007 and retained 7/10 items. Lambda 0.75/1.0 had similarity 0.0591, retained 7/10 items, and retained 85.5% of baseline relevance score. Lambda 0.75 reduced similarity about 43% versus lambda 0 and about 41% versus lambda 0.25; lambda 1.0 added no observed benefit. This is a frozen-pool comparison, not future-listen hit-rate/nDCG or evidence of broad satisfaction.

The earlier 35-combination/floor-sweep reproduction is dismissed as a decision input. The actual CLI output contained six lambda results and no floor dimension; do not claim that it verified a relevance-floor sweep, and do not run another fixture test for that discrepancy. Keep the relevance floor at its default of 0 and production ranking unchanged while implementing the preference contract and safe integration. Keep the fixture and identity-bearing report private.

**Backend preference contract and allocator integration merged in PR #326** at merge commit `ef8173a4ce47b0b4b1ec72fc567377dbd0cf1dd0`, from exact final PR head `f502e6c3e2877ec88b8e8f1a744e4d0fdf6b9c1f`. All four required workflows passed on that exact head, including 655 passing unit tests. The persistent `recommendation_diversity` setting accepts strict integer values 0–100 through `GET/PUT /api/settings/recommendation-diversity`. Missing or corrupt stored values safely default to 0, and value 0 bypasses MMR ordering to preserve legacy selection order. Nonzero values map linearly to the MMR penalty and re-rank ownership-clear candidates dynamically inside existing allocation passes; owned/ambiguous candidates retain their legacy positions. Regression tests cover service/API validation, persistence/defaults, setting-to-allocator wiring, MMR selection, ownership, artist cap, and allocation contract validation. Keep the settings UI in a separate coordinated PR.

#### 3.2 Recommendation history and cooldown

**History persistence merged in PR #329** at merge commit `85a94f2d66aefc0c1f130d4440546e7135d4e8d7`, from exact tested PR head `613fd85715eaedc69f2375daf3cb6da6833c63bb`. All four required workflows passed on that head: Python syntax run `1650`, Docker packaging/full unit suite/build run `1558` (659 tests), container runtime smoke run `1367`, and validation-only multi-architecture image validation run `1411` (publishing paused). Inspection confirmed `discovery_store.py` retained only the latest payload per list plus a single pool-diagnostic snapshot; it did not retain recommendation batches. Personal-list persistence now records up to 20 ranked items per batch, storing only a SHA-256 hash of normalized artist/album identity, timestamp, and rank—not raw labels. Retention is bounded to 30 days and 2,000 rows; history writes share the personal-list SQLite transaction. Ranking is unchanged by this persistence-only step.

**Soft cooldown merged in PR #332** at merge commit `1fdd01b1878be10544358450cb9f2a4a1d03d5d2`, from exact tested PR head `692722e019e671a3cd4cef67698743d359f205e9`. All four required workflows passed on that exact head: Python syntax/acquisition safety run `1663`, Docker packaging/full suite/build run `1571` (691 tests passed), container runtime smoke run `1380`, and validation-only multi-architecture image validation run `1424` (publishing paused). The policy applies only after existing ownership classification and adjusts allocation scores rather than filtering candidates. Each matching prior exposure contributes a rank-weighted penalty (rank 1: 10%; rank 20: 0.5%), decayed with a seven-day half-life, summed to a 25% cap, and ignored after 30 days. These are explicit conservative starting constants, not fixture-calibrated quality claims. History remains SHA-256 identity-only, bounded to 30 days/2,000 rows; missing/deleted albums have no effect unless they reappear as candidates. Storage read failures fail open; sparse pools retain all candidates and hard eligibility is unchanged. Deterministic tests cover decay, expiry, rank weighting, the cap, malformed/future rows, sparse-pool retention, deterministic output, a relevance-gap guard, ownership-gate preservation, and storage failure. Calibration remains open: do not collect another live capture or publish private fixture data; use only the existing offline fixture if an appropriate identity-free comparison is available.

**Calibration feasibility check (2026-10-18):** the existing private capture is not sufficient to compare the merged cooldown against baseline. Its captured `expected_output` contains the baseline debug pool and scores, but the capture format does not include the contemporaneous SQLite recommendation-history rows consumed by `apply_history_cooldown()`. The existing `recommendation_mmr_evaluate.py` is an MMR-only evaluator: it does not invoke the allocator/cooldown or replay the provider tape. Applying synthetic history would measure an invented exposure scenario, not the observed baseline-vs-cooldown effect. Therefore, do not claim cooldown calibration and do not collect another live capture; retain the merged constants as explicitly uncalibrated policy defaults.

#### 3.3 Feedback as a bounded signal

Use feedback in ranking/query selection, not only stored-list filtering:
- `dismiss_artist`: apply a decaying soft penalty to that artist and a weaker penalty to its dominant tags.
- `save`: use the saved album/artist as a positive similarity seed for ranking and supplementary query selection.
- `dismiss`: penalize that album only; do not generalize to its artist or genre.
- `remove_for_me`: preserve its existing semantics; do not silently reinterpret it as a global dislike.

Define separate time windows/decay rules and expiry for positive/negative signals. Do not create permanent exclusion. Add regression tests using injected feedback rows, including expiry and ensuring album-level dismissal does not penalize sibling albums.

**Status (2026-10-20, merged as PR #456 at `4680a18`):** implemented offline in `recommendation_feedback.py`, on by default (`FEEDBACK_SIGNAL_ENABLED = True`, owner-approved 2026-10-20). Dismissals apply a decaying penalty (album 0.50, artist 0.30, shared-tag 0.10, cap 0.60; 14-day half-life, 60-day expiry, from `updated_at`). Saves apply a boost to the same artist (0.10 max; 30-day half-life, 90-day expiry, from `created_at`). `dismiss_artist` takes the larger penalty, not the sum. Ownership-clear candidates only. The read-time hard filter is unchanged. Controlled synthetic fixture (`tests/test_recommendation_feedback_fixture.py`) runs the real ranking and allocator: a dismissed artist drops from one slot to zero and a non-dominant artist takes it; a save leaves the slate size and eligibility unchanged. Not done: the positive seed is a score boost, not a tag-query seed; no live or private-capture evaluation.

**Status (2026-10-20, save tag-query seed, merged as PR #461 at `ace28d3`; roadmap 3.3 is complete):** saved albums now seed supplementary tag-query selection. `recommendation_feedback.saved_artist_seed_weights` returns a decayed weight per saved artist (`SAVE_SEED_WEIGHT = 1.0`, same `created_at` 30-day half-life and 90-day expiry as the boost) and the gatherer adds it to that artist's tag weight. Artists whose MBID this run knows (listens, CF candidates) are seeded from cached genres; other saved artists are seeded from the `genres` stored in the save's metadata, so no MBID is needed. No lookup is added, and the seeded plan is capped at the unseeded plan's length (initial and replenishment), so a seed replaces a query and never adds one. Gated by `FEEDBACK_SIGNAL_ENABLED`; `RecommendationProviders.feedback_rows` defaults to `None` (unseeded). Synthetic fixture: 8 queries and 0 uncached lookups with and without a fresh save; the save moves a saved-artist tag into the profile quota. Limits: a save whose metadata has no `genres` and whose MBID is unknown is not seeded; saves now come from the UI Save control (PR #464) or API callers, both sending the item as metadata; no live run. All four required workflows passed on exact head `8c2c418`. A review finding (P2) was fixed before merge: the budget cap now compares against a pre-seed snapshot of the profile-tag map. **Follow-up (2026-10-20):** `save` is now side-effect-free (PR #463) and the UI can create a save (PR #464). **Seed diagnostics (2026-10-20, merged as PR #465, squash `6e1054b56c531eb4fbad912f8ffe1d300c358339`, exact head `d962dd1fc8a022b2d75f3565134d6ab5357ff97b`; all four required workflows passed on that head):** `run_metrics.counts` now holds seven integer `save_seed.*` counters (saved artists in the window; seeded from cached genres (counted only when cached genres were found); MBID known but no cached genres; seeded from metadata genres; skipped for no genres and unknown MBID; initial and replenishment queries that differ from the unseeded plan). Recorded only after the seed block succeeds; a feedback failure or no provider leaves them absent. No lookup, selection, quota or flag change. **Live run (owner-approved, one sample, count 10, fresh data dir, slskd disabled):** after an unseeded baseline, 4 saved albums (3 with stored genres, 1 without) gave `saved_artists` 4, `from_cached_genres` 1, `from_metadata_genres` 2, `skipped_no_genres` 1, `initial_queries_changed` 1, `replenish_queries_changed` 0. The live figure `from_cached_genres` 1 was taken before review fixed the counter: it then counted every MBID-known save, whether or not cached genres existed, so it means 'MBID known', not 'seeded from cache'. The counter now splits that outcome and the live run was not repeated. So at most 3 of 4 saves reached the planner and changed one initial query; replenishment changed none. Limits: single sample; saves were chosen from the baseline's own recommendations, which biases the MBID-known split; candidate quality of the changed query not measured; wall time (217 s baseline, 249 s seeded) is not evidence about the seed. Storing the artist MBID in save metadata would recover at most the one skipped save here. **Review notes:** two reviews were addressed before merge: `from_cached_genres` now counts only when cached genres were found (with `mbid_known_no_cached_genres` split out), and a counters-disabled equivalence test was added; a claimed double-count of metadata-seeded artists was disproved by a test (the branch ends in `continue`). **Next action:** none for the seed unless real saves over time suggest it; the engine's next item is the exploration setting (see `CLAUDE_CLI.md`).

**Acceptance gate:** controlled fixtures show reduced repeated artists/styles and improved handling of feedback without collapsing relevance, creating permanent exclusions, or violating eligibility rules.

#### 3.4 Persisted last-known-good snapshots and automatic background refill (implemented 2026-10-20; read path PR #459 `b09c954`; snapshot guard PR #445 `c5e9b17`; read-time ownership filter PR #446 `80d796b`; provider-failure threshold PR #447 `e932c51`)

Owner decision (2026-10-19): background refill is on by default and runs automatically, because the app will run as a self-hosted service.

Evidence and reason: a failed or degraded refresh can replace a good persisted list, which is the refresh-failure and persisted-versus-ranked-output risk already in Phase 0 and the priority list. DroppedNeedle (commit `cf7278a`, checked 2026-10-19) keeps a last-known-good snapshot in SQLite (`backend/infrastructure/persistence/discovery_snapshot_store.py`), serves it stale-while-revalidate with a 5-minute rebuild threshold (`backend/services/discover/homepage_service.py`, lines 97-103 and 289-356), and does not overwrite it with an empty or degraded build. We adopt the pattern only. No code is copied until its license is checked.

Design:
- Persist the final ranked list per user as a snapshot (rank, provenance, build time, listening-window identifier, configuration hash). Store hashed identities and ranks, as in 3.2, not raw labels.
- Serve the latest good snapshot on request. When it is older than the existing 24-hour stale threshold, start a background rebuild and never block the request on it.
- Automatic refill: the existing hourly discovery-refresh cycle triggers the default (flags-off, full-quality) build for each stale profile. It runs under the 100-request uncached budget and the 1 request/second MusicBrainz limit, under one lock shared with foreground builds so they never overlap. The setting defaults to on and can be turned off.
- Degraded-build guard: a build with provider failures, or with fewer eligible items than the stored snapshot, does not replace it. The previous snapshot stays, and the failure is logged in aggregate only.
- Read-time safety: owned and duplicate identities are re-filtered against the current library on every read, so a snapshot cannot re-surface an album the user has since acquired.
- Refill uses the default path only. The batch flags are not used for refill, so the stored list stays consistent with steady-state output.

Acceptance (deterministic tests): a failed build keeps the previous snapshot; a stale snapshot is served while a rebuild is triggered; a snapshot served after a library change excludes newly owned albums; a refill run makes no more than 100 uncached requests; with the setting off, no background work runs. Metrics: foreground latency, age of served snapshot, and refill outcome counts, all aggregate.

Out of scope here: a per-item scored history store (deferred to Phase 4 item 5).

**Current status (2026-10-20).** Items (1) provider-failure count (threshold, PR #447, merge `e932c51`), (2) read-time ownership filter (PR #446, merge `80d796b`), and the snapshot guard (PR #445, merge `c5e9b17`) are merged. The refill on/off setting is merged as PR #458 (`7fb140e`, default on). Roadmap 3.4 is complete. The stale-while-revalidate read path merged as PR #459 (`b09c954`, exact head `44148af`): reading the personal list serves the stored snapshot, still re-filtered against the current library, and when it is 24 hours or older starts one background rebuild through `_discovery_refresh_personal(20, origin="read")`, which keeps the shared build lock and the snapshot guard. No rebuild starts when automatic refill is off, one is already in flight, one started within the last hour (`REVALIDATE_COOLDOWN_SECONDS`, so a failed or rejected rebuild retries at the scheduler's cadence, not per request; a failed thread start releases the cooldown), or no snapshot exists (the scheduler handles cold start). Personal list only. The 24-hour threshold is one shared constant, `STALE_MAX_AGE_SECONDS`; the refill schedule is unchanged. Refresh diagnostics gained the `read` origin and the `rejected` status (the latter was previously refused by the store and silently dropped). No lookups were added; the 100-request refill budget is covered by the existing budget tests, not a new one. Tests: `tests/test_discovery_revalidate.py`, plus a `read`-origin and a `rejected`-status case in `tests/test_recommendation_diagnostics.py`. Known limits: the rebuild trigger and cooldown are per process and in memory; the metrics named in the design (served-snapshot age, foreground latency, refill outcome counts) are not exposed beyond the stored refresh outcomes; no live or browser run.

### Phase 4 — Evaluate additional candidate lanes (only when earlier phases justify them)

These are candidates for experiments, not committed additions. Check existing modules and source overlap before implementation.

1. **Library gaps / deep dives:** for artists with several owned albums, find missing studio albums via MusicBrainz release groups. Inspect `discovery_new_releases.py`, classics modules, and existing library snapshot logic first to avoid duplicate inventory/catalog work.
2. **Similar artists seeded by recent listening:** evaluate Last.fm `artist.getSimilar` or a ListenBrainz similarity endpoint only if current official documentation confirms the endpoint and its behavior. Seed from a small weighted set of recent artists, prefer MBIDs, aggregate evidence from multiple seeds, and downweight weak/stale matches. Cache provider results while recalculating profile-dependent weights on each refresh.
3. **Wider ListenBrainz CF pool:** check current official documentation for pagination or artist-type/filter parameters. The current code requests `count=100`; do not assume additional parameters exist until confirmed.
4. **Popularity/trending fallback:** only consider it as a capped cold-start or optional lane, never as a dominant personal signal.
5. **Scored recommendation store (deferred):** keep every recommendation with its score against the current profile and build pages from the store plus fresh fetches. This adds long memory, so it needs read-time ownership and duplicate checks and window-tagged scores to avoid temporal leakage. Defer until 2.3 and 3.4 show value.

For each lane, compare against the Phase 0 baseline and simpler profile-driven sources. Retain only sources that improve measured outcomes enough to justify operational complexity, cache/rate-limit cost, and failure modes. ListenBrainz's recording-level CF endpoint is already in use; do not describe it as a new prototype or replacement.

## Lessons and design patterns retained from prior research

### DroppedNeedle: distinct sources and discovery intents

The public [DroppedNeedle repository](https://github.com/DroppedNeedle/DroppedNeedle) and [feature documentation](https://www.droppedneedle.com/docs/features) describe discovery entry points including similar artists, library gaps, fresh releases, charts, ListenBrainz/Last.fm patterns, and “Because You Listened To” rows. This supports using independent candidate generators with provenance and keeping existing lists focused on distinct intents:
- **Personal discoveries:** recent-listening responsiveness with controlled adjacent novelty.
- **Classics / collection-building:** meaningful library gaps and relevance, not popularity alone.
- **Artist Deep Dives:** explore owned artists without letting one artist dominate a row.
- **New Releases:** recency plus reliable artist identity and release eligibility.

Do not add new UI modes in the initial backend work. The public docs establish product features, not DroppedNeedle's exact internal algorithm or measured quality; do not attribute unverified ranking internals to it.

**Caching and freshness (checked at commit `cf7278a`, 2026-10-19; cite paths, not inferred behavior):**
- Stale-while-revalidate with a last-known-good SQLite snapshot (`backend/infrastructure/persistence/discovery_snapshot_store.py`); adopted as section 3.4.
- Degraded or empty builds do not replace good cached content (`backend/services/discover/homepage_service.py`, around lines 664-690); adopted as the degraded-build guard in 3.4.
- Per-stage budgets kept below the overall task timeout (`homepage_service.py`, lines 97-125); consistent with our bounded uncached budget.
- Background retry schedule: short on failure, long on success (`backend/services/discover/demand_service.py`); informs the refill backoff in 3.4.
- Not adopted: a multi-user warmer with per-user leases. This is a single-user deployment, so a single lock is enough. Inference, not verified against our load.
- DroppedNeedle has no item-level scoring store and no ownership-aware allocator we could compare against, so it informs freshness and persistence only, not ranking.

### Recommendation-system research

- **Diversity after relevance:** research on serendipity/diversity indicates that diversity can improve discovery but excessive diversification can reduce accuracy. Use measured, controlled re-ranking rather than arbitrary quotas. See Kotkov et al., [“How does serendipity affect diversity in recommender systems?”](https://link.springer.com/article/10.1007/s00607-018-0687-5) and [“Current challenges and visions in music recommender systems research”](https://link.springer.com/article/10.1007/s13735-018-0154-2).
- **Listener outcomes:** work on diversified music recommendations supports measuring discovery outcomes beyond similarity, but does not prescribe a universal diversity level. See Porcaro, Gómez, and Castillo, [“Assessing the Impact of Music Recommendation Diversity on Listeners”](https://dl.acm.org/doi/10.1145/3608487).
- **ListenBrainz freshness:** CF recording recommendations are experimental and provider-generated output has its own update schedule. Keep provider-output freshness distinct from profile freshness, metadata cache TTL, and persisted-list freshness. See the [ListenBrainz recommendation API](https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html), [ListenBrainz documentation](https://listenbrainz.readthedocs.io/en/latest/), and [data update intervals](https://github.com/metabrainz/listenbrainz-server/blob/master/docs/general/data-update-intervals.rst).
- **Similar artists:** Last.fm's official API exposes `artist.getSimilar` with a match value and optional MBID. Treat this as evidence, not truth, and verify provider behavior before implementation. See [Last.fm artist.getSimilar](https://www.last.fm/api/show/artist.getSimilar) and the [Last.fm API overview](https://www.last.fm/api).

## Evaluation checklist for every behavior-changing phase

Use frozen, provider-injected fixtures. For each change, compare with the Phase 0 baseline and report:
- Artist-level hit-rate@k and nDCG@k on unowned artists in the T+14-day replay window.
- Responsiveness: candidate-set overlap and ranking changes across contrasting histories.
- Novelty, intra-list diversity, unique artists/styles, average pairwise tag similarity where available, and batch repeat rate.
- Relevance guardrails, including retention of high-relevance candidates before/after re-ranking.
- Ownership and release eligibility/rejection counts.
- Determinism, bounded candidate/provider work, and safe handling of empty, malformed, stale, or unmappable provider data.
- Cache hits/misses and freshness at the correct layer (CF output, metadata, supplementary query results, persisted recommendation list).

Do not set arbitrary numeric targets until the baseline exists. Keep hit rate relative rather than absolute, avoid future-data leakage, and state the fixture/replay limitations.

## Cross-phase acceptance criteria

- No hidden fixed regional slots or hard-coded personal taste preferences remain in personal recommendations unless explicitly documented as a product setting.
- Candidate generation and ranking respond to recent listening and library context while retaining bounded exploration.
- Identical fixtures/settings produce identical results.
- Diversity and cooldown reduce repetition without collapsing relevance or violating hard artist/eligibility constraints.
- Feedback influences only the intended scope, decays/expires, and is covered by regression tests.
- Missing metadata and provider failures degrade safely; popularity does not accidentally dominate personal signals.
- Refresh semantics are verified; fix stale output only when the root cause is established.
- Existing ownership, artist identity, release eligibility, response schema, acquisition, and MCP compatibility tests remain passing.
- Cache TTL changes are justified by evidence/provider limits rather than shortened indiscriminately.

## Private real-run capture and offline replay

PR #298 extends Phase 0.2 with a private capture/replay path. A successful recommendation call can write one immutable capture when `LIBRARIAN_RECOMMENDATION_CAPTURE_PATH` is set. The capture contains:

- The exact ordered provider/cache call tape consumed during candidate gathering: ListenBrainz listening history and CF response, MusicBrainz HTTP responses, cache reads/writes, Navidrome inventory API responses, and request identities/arguments.
- The gathered input snapshot that entered ranking, plus Last.fm popularity results consumed by scoring.
- The exact output from the captured run, the capture timestamp, schema version, source Git SHA, and SHA-256 integrity hash.

Capture files contain personal listening, library, and provider metadata. They are rejected if placed inside the repository, if the target already exists, or if the containing directory/file permissions are not private. Use an owner-only directory (mode 700); the capture file is created mode 600. Do not commit or attach real captures to a public PR.

### Set up a capture

Run the app from an isolated, identified GitHub PR revision with its test settings configured. Set these variables **before starting that test app**, not on the production service:

```sh
mkdir -p "$HOME/navi-librarian-test/private-recommendation-fixtures"
chmod 700 "$HOME/navi-librarian-test/private-recommendation-fixtures"
export LIBRARIAN_RECOMMENDATION_CAPTURE_PATH="$HOME/navi-librarian-test/private-recommendation-fixtures/baseline-unique.json"
export LIBRARIAN_RECOMMENDATION_CAPTURE_GIT_SHA="<exact GitHub revision under test>"
```

Then trigger one successful recommendation refresh in that isolated app. The configured path must be new for each capture; the implementation refuses to overwrite it. The capture attempt is one-shot and clears the environment variable afterward, preventing repeated capture attempts on every refresh. If capture fails, recommendation generation continues and the app logs a warning. The source SHA should be the exact GitHub revision tested, not an unrelated local commit.

### Replay without network access

Use the same isolated source environment (Python dependencies installed) to run:

```sh
NAVIDROME_LIBRARIAN_DATA_DIR="$(mktemp -d)" python recommendation_replay.py "$HOME/navi-librarian-test/private-recommendation-fixtures/baseline-unique.json"
```

The temporary data directory prevents module initialization from touching the app's normal persisted database. The replay validates the schema and checksum first, then replays provider/cache responses in strict call order and substitutes captured Last.fm results. It does not call the live provider functions, open real HTTP clients, sleep for provider rate limits, or write pool diagnostics to the application database. A changed call order, missing response, extra/unused tape event, or output mismatch fails the replay. The report compares stable output fields and omits only volatile pool-overlap diagnostics and Last.fm error-state text.

The capture preserves the provider/cache values actually consumed; the saved gathered-input snapshot is included for inspection. This is a reproducibility harness, not an assertion that recommendations are good. The separate T-to-T+14-day outcome evaluation remains a later step and must not feed future listens into generation inputs. The public CI fixture remains synthetic.

## Out of scope unless separately approved

- Rewriting the recommender or adding a machine-learning stack.
- Further broad modularization; its roadmap is complete.
- New UI modes or UI redesign as part of initial backend changes.
- Removing ownership/release eligibility or safety checks.
- Shortening all cache TTLs without evidence.
- Publishing or deploying an image.


## Score attribution and shortlist diagnostics (PR #366, 2026-10-18)

The profile-comparison evaluator now reports aggregate distributions for the final discovery score, recent-profile multiplier, Last.fm popularity multiplier, recent artist play counts, and exploration-family match share. It also reports allocation decision counts, candidate/selected category counts, the selected candidates' score-rank distribution, and overlap/Jaccard between the score-ranked top-k and the final allocated shortlist. These diagnostics are aggregate-only: no candidate identities or per-candidate score rows are serialized. The metrics help separate scoring/rank movement from allocation effects; they do not establish relevance or future-listen quality. Deterministic synthetic regression coverage is included. PR #366 merged as `0588ec0cc8b0ed5ad32c596c5d2c5e314f107639` from exact tested head `deabda7d04f66909a6da5b2fec7dc889ed27a200`; all four required workflows passed on that exact head (syntax/full suite `39160186431`, packaging/full suite/build `39160186619`, container smoke `39160186497`, validation-only multi-architecture `39160186550`; 739 tests passed). No local tests or private capture replay were run by the assistant. Publishing remains paused.

**Next action:** PR #370 has since merged after the corrected owner replay and exact-head CI. The result is documented in the merged shortlist-underfill section below. Investigate candidate supply separately using aggregate eligibility/source counts and deterministic bounded-replenishment tests; preserve ownership, duplicate identity, release-type filtering, provider limits, and replay determinism. Keep private captures and identities outside GitHub, and do not tune weights to mask scarcity.

## Recommendation shortlist underfill diagnostics — PR #370 merged (2026-10-18)

PR #370 squash-merged as `6256fd375db0d9c93870f78b632b60390c9ee31f` from exact tested head `e8fac4e737ce75e11210c964af5a50e4ca9bdede`. All four required workflows passed on that exact head: Python syntax/acquisition safety `39173185205`; Docker packaging/full suite/build `39173185161` (790 tests); container runtime smoke `39173185160`; validation-only multi-architecture image validation `39173185157` (publishing paused).

The merged aggregate diagnostics report actual allocator categories separately from the genre classifier, category targets/counts/shortfalls, checked/max-check values, phase attempts, and authoritative decision counts. The owner-side private schema-v2 replay resolved 19 rows per profile: 12 `already_owned`, 2 `duplicate_candidate`, and 5 `selected`. Final fallback was entered and checked count was 14/60. This explains the five-item shortlist on the frozen snapshot: ownership and duplicate protections leave only five eligible unique unowned candidates. The earlier family-cap outcomes were stale diagnostic attribution. No ranking, selection, or ownership policy changed.

The first/last profiles still return the same five recommendations (Jaccard 1.0) despite rank movement. This indicates rank sensitivity but does not establish shortlist membership responsiveness, recommendation quality, or future-listen outcomes. The private capture, listening history, and candidate identities remain outside GitHub.

**Next action:** investigate candidate supply as a separate focused task. Add aggregate eligible/unique/unowned counts at candidate-gathering and eligibility boundaries; trace which sources contribute eligible candidates; and test deterministic bounded replenishment. Preserve ownership, duplicate identity, release-type filtering, provider-rate limits, and replay determinism. Do not relax safety checks or tune weights to hide candidate scarcity. Publishing/deployment remain paused.

**Candidate supply eligibility counts (2026-10-19, merged as PR #408 at merge commit `e29487d`).** Adds aggregate, identity-free counts at the release-type boundary and per-source counts for unowned unique candidates. The CF release-group rules now live in one predicate, `cf_release_group_rejection`, which gathering and the offline counts both call; gathering behavior is unchanged. The replay report emits `release_eligibility` (release groups seen, eligible, and rejected by reason, over CF recording payloads on the tape) and `stages.unowned_unique_by_source`. On the frozen capture, the replay made zero provider calls and showed 19 candidates, 12 owned, 7 unowned unique, 2 artist-cap rejections, and 5 selected, identical to `main`. The release counts were 1982 release groups seen and 1598 eligible across 100 tape payloads. Those totals are an upper bound: they include recordings that the live artist cap or budget would skip, and they count each release entry, not each album. Every unowned unique candidate in the capture came from `listenbrainz_cf`, so the capture shows no supplementary-source contribution. The capture's replay still reports `reproduced: false`, the same as untouched `main`, so that check is unresolved. Supply itself is not changed: no bounded replenishment has been implemented or measured yet. The next action is to decide whether the page-2 and supplementary gap needs a replenishment change, using these counts.

**PR #411 replenishment live measurement (2026-10-19, aggregate only, no code change).** One live pass at `76e3ac2` (PR #411 merged) on the owner's isolated test copy, with a fresh empty data directory. Shortlist target 10; eligible unowned albums 7 before and 7 after; the replenishment gate triggered (7 < 10), but it planned 0 extra queries, attempted 0, and added 0 candidates. The base supplementary lane also issued 0 queries. CF supplied 21 albums from 10 artists. So #411 added no supply in this run. The gate fires, but the tag-query selection had no inputs. Code trace: `select_supplementary_tag_queries` reads only cached `mb:artist-genres:*` entries, which the genre-lookup stage writes later in the same run. A fresh empty data directory has no cache, so the base lane and the replenishment pass both select nothing. This run therefore does not measure replenishment on a warm cache. Single run, single profile; no identities, listening data, tags, or provider URLs were recorded. No weights, windows, eligibility, ownership, or budget changed. **Next action:** rerun on a warm metadata cache (needs owner approval of the data directory), and decide whether tag selection should read the genre cache after the genre-lookup stage, which would be a code change.

**PR #411 warm-cache measurement (2026-10-19, aggregate only, no code change).** One pass at `963f8f5` (main with #411 and the #414 tag-lane counters), in a fresh directory holding only a copy of the metadata cache. Eligible unowned albums were 62 before and after the target of 10, so the gate stayed closed and no extra queries ran. The tag lane had inputs: 15 of 15 top profile artists and 7 of 23 candidate artists were cache hits, yielding 92 and 106 tags. This confirms the cold-cache zero was an empty-cache artifact, not a selection bug. Replenishment's effect on shortlist fill is still unmeasured, since this profile had no shortfall. **Next action:** measure replenishment under a real shortfall, preferably with an offline replay fixture that leaves fewer than 10 eligible unowned albums.

**PR #411 replenishment offline shortfall measurement (2026-10-19, synthetic fixture, no code behavior change).** The live runs left replenishment unmeasured: the warm-cache run had 62 eligible unowned albums against a target of 10, so the gate stayed closed. This check uses the existing replenishment test harness with a synthetic fixture where eligible supply is short. Base CF albums: three, one owned, so eligible unowned before is 2 against a target of 10. The gate fires, and the planned and attempted extra queries are both 2, the fixed cap. Those two queries add 2 new eligible albums (one duplicate across queries and one same-album duplicate of an existing candidate are not counted; a release-type-filtered single is not counted). Eligible unowned after is 4. The third scripted extra query is never issued. Rerunning the same inputs gives identical replenishment accounting. Test: `test_shortfall_replenishment_adds_eligible_supply_within_caps`. The harness also had a defect: `test_tag_lane_counters_separate_empty_cache_from_no_listens` sat after the `__main__` guard and never ran; it is now inside the test class and passes. **Limits:** the tag-query selector is stubbed in this harness, so the fixture does not measure real tag yield, MusicBrainz response shape at scale, or the cold-cache ordering issue (genres are read before the genre-lookup stage writes them). It shows the mechanics of the gate, the caps, and the accounting, not how much real supply replenishment adds. **Next action:** decide whether tag selection should read the genre cache after the genre-lookup stage (a behavior change needing its own measurement). A live rerun with a real shortfall needs the owner's explicit go-ahead.

**Supplementary tag lane genre-read timing (2026-10-19, draft PR; code change, measured offline first).** Question: should tag selection read `mb:artist-genres` after the genre-lookup stage, since the lane runs before that stage writes the cache? Measurement: the real gathering path ran on a synthetic fixture (one profile artist, one CF candidate, no owned albums, eligible unowned 4 cold / 28 warm against a target of 10), with providers stubbed and no live calls. Cold cache, current order: 0 profile queries, 0 candidate-pool tags, 0 planned replenishment queries. Warm cache: 8 queries (7 profile tags, 3 candidate-pool tags), 28 eligible unowned. A full reorder (prefetch every CF and profile artist before the lane) matched the warm run exactly, but it adds up to about 60 uncached MusicBrainz lookups to a first run, because the lane's own album artists would no longer be in the earlier set; that is more than the budget discussed for this stage, so it was not chosen. The change: prefetch the top 15 listening-profile artists' genres before the lane. These artists are already in the genre stage's lookup set, so total calls per run are unchanged, and the genre-stage writes and values are the same. Result on the same fixture, cold cache: 6 queries (all 6 profile queries; the 2 exploration queries still need candidate-pool genres), 22 eligible unowned, 25 genre lookups in the run. Remaining gap versus warm: exploration queries and about six eligible albums. Tests: `tests/test_discovery_genre_prefetch.py` (cold plans profile queries from prefetched genres; cold and warm plan the same profile queries; a failed prefetch does not fail gathering). The first two fail without the change. Weights, windows, eligibility, ownership, duplicate identity, and provider budgets are unchanged. Merged as PR #419, `51f6e9877575a11dd5e0314cd23b2b197baca491` (exact head `9f045e33e85334247b55fc230e4152a3d3b3b620`). Limits: synthetic fixture; the tag selector's real yield is not measured; no live run was made. **Next action:** a live cold-cache run needs the owner's go-ahead. If exploration parity matters, measure the candidate-artist prefetch cost (uncached lookups per run) before deciding.

**Candidate-pool genre prefetch (2026-10-19, merged as PR #421 at `d840150`; code change, measured offline first).** Question: should the supplementary tag lane also prefetch genres for the top candidate-pool artists, so a cold cache plans the same exploration queries as a warm one? After #419, the profile artists were prefetched but candidate artists were not, so a cold run still planned 0 of 2 exploration queries. Change: `CANDIDATE_PREFETCH_LIMIT = 5` adds the top five CF candidate-pool artists by score to the same pre-lane prefetch, after the top 15 profile artists. An exhausted retry on a candidate stops only the candidate prefetch; the genre stage still retries and records every artist as before. Measurement: synthetic fixtures, no live calls, three sizes (20, 40, 60 CF albums, shortlist target 10). Cold without the change (#419): 6 queries, eligible unowned 28, 44, 48. Cold with the change: 8 queries, eligible unowned 34, 50, 54, identical to the warm cache. Warm: 8 queries and the same eligible counts. Uncached MusicBrainz genre lookups: the prefetch itself adds none in any configuration tested (limits 1 to 60). The extra cold lookups at limit 5 (0 to 6 per run) come from the two exploration queries that are now planned, and the warm run makes the same lookups for them. Added time at the existing 1.1 s spacing: a successful prefetch replaces genre-stage calls, so it adds no spacing. The two extra queries add about 3.3 to 9.9 s in these fixtures, including their search spacing. Worst-case bound from the prefetch alone: each candidate that fails with a non-retryable status is requested twice (at most 5 extra requests, 5.5 s), and one exhausted retry adds at most three requests, 6 s of backoff, and one spacing (about 7.1 s), so at most about 13 s. Tests: `tests/test_discovery_candidate_genre_prefetch.py` (cold plans the exploration queries; cold and warm plan the same queries; each artist is looked up once; limit 0 keeps the previous plan; an exhausted retry stops the candidate prefetch). Weights, windows, eligibility, ownership, duplicate identity, and provider budgets are unchanged. Limits: synthetic fixtures; exploration needs unseen tags from the top candidates, so a pool whose top five artists share tags with the profile may still show a gap; real tag yield is not measured; no live run. **Next action:** a live cold-cache run needs the owner's go-ahead. Record its aggregate counts (queries planned, eligible unowned before and after, uncached lookups, seconds added) against these fixture numbers.

**Live cold-cache pass for PR #421 (2026-10-19, aggregate only, owner's test copy at `d840150`).** One gathering pass, shortlist target 10, fresh empty data directory with no metadata cache and no prior listening or recommendation state. Eligible unowned albums were 45 before and after, above the target, so replenishment did not trigger (0 extra queries planned, attempted, or added). The tag lane planned and issued 8 queries: 7 returned yield and 1 failed with an HTTP error. The profile prefetch left 14 of 15 top profile artists cached; 6 of 13 candidate artists were cache hits. CF paging fetched 2 pages (200 recordings); the 100-resolution uncached budget was fully used and 87 resolutions were skipped on budget. There were 65 uncached MusicBrainz artist-genre lookups, which may slightly undercount because failed lookups are not cached. The live estimate of about 190 s at 1.1 s spacing covers all 173 uncached requests in the run, including the 100 recording resolutions that this change did not add, so it is not the added cost of PR #421. The offline fixture comparison (cold 8 queries, 34/50/54 eligible, same as warm) is unchanged by this pass, but this run has no pre-change comparison, so it does not show the gain directly. Limits: one pass, one profile, one cold state. **Next action:** decide whether a live pre-change comparison is worth one more authorized pass; otherwise move to the next roadmap priority.

**Uncached-budget sweep (2026-10-19, offline synthetic, no live calls, no code change).** Question: does the 100 uncached-resolution budget (`CF_MAX_UNCACHED_RESOLUTIONS`) limit candidate supply? Method: the real `gather_recommendation_candidates` path with stubbed providers, 200 CF recordings over two pages in a seeded shuffled order, budget set from 25 to 300. Two synthetic pools: *concentrated* (184 of 200 recordings from two artists with 25 albums each, the rest from 16 single-album artists, approximating the owner's 92-of-100 concentration) and *spread* (200 distinct artists). No albums owned. Aggregates only:

| Pool and cache | Budget | Uncached calls | Budget skips | Unique albums | Distinct artists | Shortlist ceiling | Spacing added (s) |
|---|---|---|---|---|---|---|---|
| concentrated, cold | 25 | 25 | 175 | 22 | 3 | 30% | 27.5 |
| concentrated, cold | 50 | 50 | 150 | 39 | 6 | 60% | 55.0 |
| concentrated, cold | 100 | 100 | 100 | 53 | 10 | 100%, no margin | 110.0 |
| concentrated, cold | 150 | 150 | 50 | 62 | 15 | 100% | 165.0 |
| concentrated, cold | 200 | 200 | 0 | 66 | 18 | 100% | 220.0 |
| concentrated, warm | any | 0 | 0 | 35 | 18 | 100% | 0 |
| spread, cold | 25 to 200 | 25 to 200 | 175 to 0 | equals budget | equals budget | 100% from 25 | 27.5 to 220 |

The shortlist ceiling is `min(distinct artists, 10) / 10`. Warm concentrated: the 10-per-artist cap skipped 164 of 200 recordings, and 36 were resolved.

Findings:
1. **The budget binds artist supply on a cold run with a concentrated pool.** Below 100 the ceiling falls under the 10-slot target (3 artists at 25, 6 at 50). At 100 it reaches the target exactly, with no margin for any artist to drop out.
2. **Album counts overstate shortlist supply.** Concentrated, cold, budget 100: 53 eligible albums but only 10 artists. The personal allocator selects at most one album per artist (`artist_already_selected` in `discovery_personal_allocator.py`), so distinct artists, not albums, set the fill ceiling.
3. **The replenishment gate is blind to artist shortage.** The gate compares eligible unowned albums with the shortlist target. At budget 50 the fixture has 39 eligible albums, so the gate stays closed, yet only 6 artists are available, 4 slots short. Replenishment would not fire in that case.
4. **The artist cap depends on cache state.** It applies only to cache-known recordings, because the CF response carries no artist. A cold run therefore spends about 92 of its first 100 uncached calls on the two dominant artists, while a warm run skips them. This matches the direction of the owner's live runs (cold 45 eligible albums, warm 62), but the fixture was not calibrated to those runs.
5. **Cost.** Each extra 50 of budget adds about 55 s of recording spacing at 1.1 s per call, plus genre lookups for new artists. Going from 100 to 150 adds about 55 s for 5 more artists in this fixture. The owner's rule is that a few seconds is acceptable and about 100 s is too long, so 150 is a trade-off for the owner to decide.

Decision: no change to the budget, weights, windows, eligibility, ownership, or duplicate rules. The budget is not shown to cause underfill on the owner's live cold run (45 eligible albums), but the number of distinct unowned artists there is unmeasured, so the margin at 100 is unknown. Next steps: (a) add a distinct unowned eligible artist count to the aggregate diagnostics and test it offline; (b) evaluate an artist-based replenishment gate offline, since the album-based gate cannot see finding 3; (c) a live aggregate run for distinct unowned artists per budget needs Hamdi's go-ahead in words first.

Limits: synthetic pools with an assumed album structure; no ownership applied; no non-CF sources (the tag lane returned empty release groups); genre lookups stubbed empty; spacing computed as 1.1 s per recording call, not measured; the ceiling ignores categories, quotas, MMR, and ownership, and is not a prediction of live supply. The sweep script stays in the agent's scratch directory and is not committed.

**Last.fm similar-artist source and combination study (2026-10-19, aggregates only).** Question (owner): can a Last.fm candidate source cut batch time without a recommendation-quality drop, and does combining it with CF help? Requests scale with artists, not recordings, so a Last.fm path could avoid the per-recording MusicBrainz spacing.

Measured on the owner's device (key never left the device): 15 `artist.getSimilar` calls, one per seed from the first 75% of the 407-listen history, limit 30. Results: 0 failures; 23.8 s total (about 1.6 s per call including device-session spacing). 30 similar artists per seed, 394 distinct in total, 298 with a MusicBrainz ID; 5 of the similar artists are also seeds. Then one MusicBrainz release-group browse per artist for the top 20 similar artists by match score, at 1.1 s spacing: 20 calls, 2 failed with HTTP 503, 31.5 s. These returned 672 albums; 236 pass the release-type eligibility rules; 17 distinct artists among them. These counts are before ownership and duplicate-identity filtering.

Frozen CF capture for comparison (aggregates, no identities): 100 recordings returned and resolved at budget 100, about 110 s of recording spacing; 19 albums from 8 artists; 7 eligible unowned albums from 5 artists, after ownership.

| Path | Time (approx.) | Supply (before ownership unless noted) |
|---|---|---|
| CF, budget 100 (capture) | about 110 s | 7 eligible unowned albums, 5 artists (after ownership) |
| Last.fm top-20 plus browses | about 55 s (23.8 s + 31.5 s) | 236 eligible albums, 17 artists (before ownership) |
| Last.fm, all 298 browses (not run) | about 330 s, estimated | worse than CF on time |

The two supply rows are not directly comparable: the ownership filter has not been applied to the Last.fm side.

Combinations (time sketches, not measured):
- Running both at today's settings costs about 165 s, which is slower, so it is excluded.
- CF at budget 50 (about 55 s) plus a Last.fm top-20 pass (about 55 s) is about 110 s, equal to today's total.
- Gated: run the Last.fm pass only when CF's distinct eligible artists fall below the 10-slot target; CF at budget 50 plus Last.fm top-10 is about 80 s when triggered, and about 55 s otherwise.

Quality: not measured. The frozen CF capture was taken after the listens that would serve as holdout, so a CF hit rate against them would be inflated, and no historical CF tape exists. Fair options: (a) an offline Last.fm holdout on the device, seeds from the first 75% of listens only, holdout = last 25%; (b) a prospective test, snapshot CF and Last.fm candidates now and score both against the listens of the following two weeks. Only (b) compares CF fairly.

Decision: no change to the budget, weights, windows, eligibility, ownership, or duplicate rules. The Last.fm source is not implemented. Next action: a prospective quality protocol plus an offline harness for the gated combination, with the ownership and duplicate filters applied to both paths before any time or supply comparison.

Limits: one seed set, one profile, one day of measurement; 2 of 20 browses failed; the ownership filter is not applied to the Last.fm side; spacing is partly device-session added; combination times are sketches. Not a satisfaction or quality result.

## Last.fm as a future source option (2026-10-19)

Owner direction: keep Last.fm as an optional recommendation-source setting for later, and move the roadmap forward. It is not a default change and not implemented as a default source.

Measured so far (aggregates only; no identities recorded):
- Capped path (top 10 seeds from the 407-listen profile, top 20 similar artists, one release-group browse each): about 40 s, 95 candidates across 15 artists, none owned (positive control passed: all 31 albums of the 10 seed artists flagged owned). 4 of 20 browses returned 503 with Retry-After; their effect on supply is unquantified.
- Holdout (70 listens after 2026-10-18 15:41 UTC, 27 artists): 0 of 15 candidate artists matched, so 0 hits. The frozen CF side matched 3 of 27 artists from 7 eligible albums. Samples are too small to judge quality.
- Uncapped path (169 browses): 273 to 313 s, not faster than CF.

Next action for the roadmap: prospective quality test once more listens accrue; a source-setting design only if the owner asks for it.

**Batch metadata lookup study (2026-10-19, aggregate only, no code path changed).** Question: can per-recording MusicBrainz lookups (about 110 s per run at budget 100) be replaced by ListenBrainz batch endpoints without weakening eligibility? Live checks on the owner's test Mac, one sample of 100 recordings:
- `POST /1/metadata/recording/` returned HTTP 200 in about 1 s for 100 IDs. Each key had an artist name and artist MBIDs (under `artist.artists[]`), a release-group MBID, and a release name. It has no secondary release types.
- `GET /1/metadata/release_group/` returned HTTP 200 in about 0.4 s for the 35 distinct release groups. Each has a primary `type`. None has a secondary-types field, so live, compilation and similar exclusions cannot be applied from it. (A POST to this endpoint returned HTTP 405.)
- Those 100 recordings map to 35 release groups by 26 artists.

Decision: the batch path cannot preserve secondary-type exclusions. It is acceptable only with a backend title-marker filter (`batch_title_marker_rejection`, behind `BATCH_TITLE_FILTER_ENABLED`, off by default). The filter is a partial safeguard: unmarked live albums and compilations still pass. On this sample it flags 1 of 35 release groups.

Discogs was checked as an alternative: no release-type field or batch endpoint is documented. Not pursued.

Limits: one 100-recording sample; timings from one device session; the batch path was not wired into gathering when this study was written.

**Flagged batch resolution (2026-10-19, offline, default off).** `CF_BATCH_RESOLUTION_ENABLED` in `discovery_candidate_gathering.py` routes uncached CF recordings through `discovery_batch_metadata.py`: one `POST /1/metadata/recording/` per 100 recordings, then one `GET /1/metadata/release_group/` per 100 release groups, with no MusicBrainz recording calls, no 1.1 s spacing and no recording cache writes. Results are shaped like the MusicBrainz resolver output, so eligibility, ownership, duplicate and budget rules run unchanged. The path runs only when `BATCH_TITLE_FILTER_ENABLED` is also on, and any batch failure falls back to per-recording lookups. Both flags stay off; the path is inert in production until they are changed deliberately.
- Measured saving on one pair of runs: 332.5 s without the flags and 105.7 s with them (see the timing entry below). Single samples.
- Remaining gaps: secondary release types are still unavailable (the title filter is partial); the wire format was checked against a live response on one 100-recording sample (the recording POST needs `inc` set to `artist release`); the release-group step still needs a call per 100 IDs; the batch size of 100 is the only size tested.
- Verified offline by 15 stubbed tests (`tests/test_discovery_batch_lookup.py`): flag gating, budget, chunking, fallbacks, title-marker rejection, and MusicBrainz-shaped output. Merged as PR #430 at `ea383cc`; the title-marker filter is PR #429 at `f33a118`. Discogs was ruled out for this use (no release-type field, token and rate limit, no batch endpoint).

**Batch title filter check (2026-10-19, aggregate only).** On 35 sample release groups the title-marker filter flagged 1. Unmarked live albums and compilations still pass, so the filter is a partial safeguard. It stays off by default.

**Batch path end-to-end timing (2026-10-19, aggregate only, one run per mode).** Owner's test Mac, `origin/main` at `ea383cc`, fresh data directory, count 10, budget 100.
- Flags off: 332.5 s, 214 uncached requests (135 recording, 3 release-group, 42 artist-genre, 34 other); eligible unowned albums 12.
- Flags on (`CF_BATCH_RESOLUTION_ENABLED` and `BATCH_TITLE_FILTER_ENABLED`): 105.7 s, 85 uncached requests (1 batch recording, 1 batch release-group, 3 release-group, 46 artist-genre, 34 other); eligible unowned albums 12.
- No fallback ran, and the title filter dropped nothing in this run.
- Limits: one sample per mode, one profile.

**Artist-genre stage under throttling (2026-10-19, aggregate only).** A repeat run with the flags on took 254 s, against 105.7 s in the timing run above. It made 83 artist-genre HTTP attempts for 55 unique artists: 28 repeats, with one artist requested 6 times. 33 of the 83 responses were HTTP 429 or 5xx.
- The retry helper makes up to 3 attempts per lookup with 2 s and 4 s backoff. It ignores `Retry-After`.
- Retryable failures are never cached, so a throttled artist is retried in profile prefetch and again in the genre stage.
- The genre stage had no early stop. The tag lane stops after one exhausted query; the genre stage did not.
- Draft PR #431 added a circuit breaker behind a default-off flag. It stops the genre stage after 3 consecutive exhausted artists and logs the skipped count. It merged at `b933d52`. Turning it on changes output, so it needs the owner's decision.

**Open decisions for the owner.** Whether to turn on the genre-stage breaker and the batch flags (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`) by default. Both change output and both remain off.

**Flag timing and variance check (2026-10-19, main `76ec40e`, test-only).** Aggregates from the owner's test copy, one fresh data directory per run, count=10 unless noted. No code or defaults changed.

| Run | Flags | Seconds | Uncached requests | Throttled 429/5xx | Recommendations | Eligible unowned |
|---|---|---|---|---|---|---|
| 1 | off | 359.1 | 277 | 76 | 10 | not captured |
| 3 | off (repeat) | 237.0 | 207 | 38 | 10 | 17 |
| a | batch only | 211.5 | 180 | 34 | 5 | 6 |
| b | title filter only | 197.0 | 179 | 28 | 6 | 7 |
| c | breaker only | 206.1 | 180 | 30 | 6 | 7 |
| 2 | all three | 46.3 | 63 | 9 | 6 | not captured |
| 4 | all three | 55.1 | 71 | 6 | 10 | 12 |
| d | all three (repeat) | 51.4 | 69 | 15 | 6 | 7 |
| 5 | all three, count=20 | 148.7 | 121 | 16 | 20 | 35 |

- Title filter: 100 calls and 0 drops in the all-flags runs, so no release title in those samples carried a marker. In the title-only run it made 0 calls because it runs only inside the batch path.
- Breaker: 0 trips and 0 skipped artists in every run, so its effect is not measured. A trip needs three consecutive exhausted artist lookups, and no run produced that streak.
- Batch resolution alone cut the MusicBrainz genre traffic only slightly (152 requests in run a, against 150 in run b with no batch) and did not cut time to the flags-on range.
- The all-flags runs (46 to 55 s) are much faster than any single-flag run (197 to 211 s), and the data does not explain why. Treat the combined speed-up as unexplained until a repeated run and a per-stage breakdown exist.
- Underfill: all-flags runs at count=10 returned 6 or 10 recommendations, with 7 to 12 eligible albums. The count=20 run had 35 eligible and filled to 20. The pool size, not the flags alone, appears to set the fill.
- Variance: the two flags-off runs differed by 122 s, and the two all-flags runs at count=10 had different eligible pools (7 and 12) under the same commit and flags. One run per mode is not enough for a timing decision.
- Limits: single samples per variant, one profile, one copy, and Mac-side wrappers that were runtime-confirmed only for the title filter. Eligible counts are missing for runs 1 and 2.
- ListenBrainz artist tags: the public docs list `GET /1/metadata/artist/` with a comma-separated `artist_mbids` and `inc=tag`, which may allow a batch artist-genre lookup. The docs do not say it returns genre names, and our code matches MusicBrainz genre names. Not verified. MusicBrainz has no batch artist-genre endpoint, so the current stage makes one request per artist.

**Decision still open.** These runs do not justify turning any flag on by default. Next useful steps: a repeated all-flags run with a per-stage breakdown, a run that trips the breaker, and a test-only shape check of the ListenBrainz artist-tag endpoint against a few artists.

**Candidate next steps (listed, not started).** Repeat the timing pair for a second sample. Honor `Retry-After` in the retry helper. Negative-cache exhausted artist lookups.

## Supplementary tag lane early stop and genre-check findings (2026-10-19)

Owner's test copy, aggregate results only. Single samples and one profile unless stated. Test runs were test-only; no Mac-side commits, branches or PRs.

**Code change (this PR, default off).** The supplementary MusicBrainz tag lane (`_run_tag_queries` in `discovery_candidate_gathering.py`) stopped every remaining query at the first query that exhausted its bounded retries. That was intentional rate-limit behavior, but it cut supply: 4 to 7 of 8 queries attempted and 15 to 29 supplementary candidates, against 38 to 39 when all 8 ran. `TAG_LANE_EARLY_STOP_ENABLED` (default `False`) changes this: with the flag on, the lane continues past an exhausted query and stops only after `TAG_LANE_EXHAUSTION_THRESHOLD` (2) consecutive exhausted queries. A successful response resets the run. Flag off is unchanged. Regression tests: `tests/test_discovery_tag_lane_early_stop.py` (7 synthetic tests).

**Artist-tag endpoint check (Test 1, read-only).** `GET /1/metadata/artist/` with `inc=tag` for 8 cached artists: 8 of 8 returned at least one tag (7 to 38 tags each, median about 18). Of 151 distinct tag names, 109 exactly match our MusicBrainz genre names for the same artists (about 0.72, exact match after case folding, so near-synonyms are not counted). Response shape: a top-level list; each item has area, artist_mbid, begin_year, end_year (missing on some), mbid, name, rels, tag, type; the tag field is a dict with one `artist` bucket holding the tag list. Not tested: the batch form of the endpoint. The sample was the first qualifying cache rows, not random.

**Breaker trip test (Test 2).** Flags on (`CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, `GENRE_CIRCUIT_BREAKER_ENABLED`), artist-genre requests forced to 429. The breaker opened after 9 genre attempts (3 artists, 3 tries each), made 0 genre requests after opening, and skipped 20 artists. The run completed with 6 of 10 recommendations; a rerun matched. About 181 s. **Gap:** the profile prefetch stage made 48 artist-genre requests, all 429. The breaker does not gate that stage, so its retries and sleeps are a large share of the runtime. This is an open follow-up and is not changed here.

**All-flags repeats (Test 3).** Three runs with flags on took about 62 to 133 s; one flags-off run took 299 s. The batch metadata stage was 0.7 s in one comparison against 179.6 s, as summarized by the test thread. A/B pair, 10 recommendations each: flags off 299 s, flags on 80 s.

**Limits.** Single samples per variant; one profile; the 6-of-10 underfill seen in an earlier flags-on run is still unexplained, and the early stop does not by itself explain it. Eligible-supply effect of the early stop is not yet measured on a live run. Not a quality result.

**Open decisions and follow-ups.** (1) Whether to enable `TAG_LANE_EARLY_STOP_ENABLED`, the breaker, and the batch flags by default; each changes output and stays the owner's call. (2) Gate the profile genre prefetch with the breaker: implemented behind `GENRE_CIRCUIT_BREAKER_ENABLED` (default off); once the streak opens, remaining prefetch lookups are skipped and counted as `profile_genre_circuit_breaker` in failures. The genre stage keeps its own streak and is not seeded by the prefetch, so a throttled run can still make up to one more streak of genre requests. Live timing not measured. (3) A live run with the early-stop flag on, to measure eligible supply and time.

## Per-stage run timers (2026-10-20, offline, no behavior change)

PR #451 timed candidate gathering as a whole, so the timing runs could not say which stage dominated. The gathering path now records aggregate wall-clock seconds in the existing `run_metrics.stage_seconds` map for: `metadata_resolution` (CF recording resolution, including any batch prefetch), `genre_prefetch` (the pre-lane artist-genre warm-up), `supplementary_tag_lane`, `replenishment`, and `genre_lookup` (the genre stage). `candidate_gathering` still reports the whole function, so the stage values overlap it and are not additive. Stages that fail or return early before their end point record nothing for that run.

The timers only read the clock. No lookup, budget, cache, eligibility, or ownership rule changed. Tests: `tests/test_discovery_candidate_genre_prefetch.py` (each stage key is reported for one run) and `tests/test_recommendation_run_metrics.py` (accumulation). Full unit suite on the working head: 1039 tests, all passing, with the sandbox dependencies installed.

Limits: this is a stage breakdown for the owner's next timing run, not a timing result. No live or Mac run was made. The owner's open question (why the all-flags runs were much faster than single-flag runs) can be answered only by a repeated run that reports these keys. Live runs need the owner's go-ahead, and the Mac measurement is paused. Merged as PR #452 at `76030c0f70e59ebe05b2e10ca5fcfc6a4fc75bd9` from exact head `856df1f6ed50353ee671c6b129d51e86a49b4ad7`; the four required workflows (compile, test-and-build, container-smoke, validate-container) succeeded on that head.

## Live stage-timing runs (2026-10-20, owner-approved, aggregate only)

Live runs on the owner's machine, count 10, one fresh data directory per configuration (warm runs reuse it). Single samples. Raw stage seconds come from `run_metrics.stage_seconds`; `candidate_gathering` overlaps the other stages and is not additive. Flags: "all" = batch resolution, title filter, genre breaker, tag-lane early stop; "batch" = batch resolution and title filter only; "single" = genre breaker only, because the handoff named no single flag.

| Run | Wall s | Recs | metadata_resolution s | genre_lookup s | MusicBrainz recording lookups | Outcome |
|---|---|---|---|---|---|---|
| all, cold | 111.6 | 10 | 1.1 | 51.9 | 0 | ok |
| all, warm | 3.1 | 10 | 0.7 | 0.0 | 0 | ok |
| batch, cold (run 1) | 107.8 | 10 | 0.7 | 48.6 | 0 | ok |
| batch, warm (run 1) | 0.2 | 0 | - | - | - | listening-history call returned a non-JSON response |
| batch, warm (retry) | 8.6 | 10 | 0.8 | 0.0 | 0 | ok |
| batch, cold (run 2) | 0.3 | 0 | - | - | - | same non-JSON failure |
| single, cold | 228.9 | 10 | 131.8 | 48.1 | 101 | ok |
| single, warm | 162.9 | 10 | 132.1 | 17.9 | 100 | ok |

**Reading.** The speed-up the owner asked about is the batch path. Batch-only and all-flags both resolve recordings without per-recording MusicBrainz calls, and their metadata stage takes about 1 s. The breaker-only configuration spends about 130 s in that stage. The two batch-only failures are upstream (the listening-history response), not timing data, and are excluded.

**Warm breaker-only run, cache miss (hypothesis, consistent with the evidence).** The warm run made 100 recording lookups. The recording cache held 200 entries afterwards: 100 written in the cold window and 100 in the warm window, with no overwrites. So the warm run resolved 100 recordings the cold run never cached. Code path: `discovery_candidate_gathering.py` allows 100 uncached resolutions per run (`CF_MAX_UNCACHED_RESOLUTIONS`), cache hits are free, and the cold run used its full budget. Each run therefore resolves its own next 100. The skip counter (`cache_known`) is not in `run_metrics`, so this is not directly measured.

**Limits.** Single samples; the batch cold figure is one successful sample; no variance bound. Provider failure on one batch run was not reproduced on the retry. No code, flag, weight, window, eligibility, ownership, duplicate or budget rule changed.

Merged as PR #454 at `a5bba875dbec57fc5c98aba119b374f268bf1ef6` (squash; all four required workflows passed on the exact head before merge).

## Exploration setting audit (2026-10-20, offline, docs only)

**Decision: the backend contract is sufficient (no new mapping needed), but this does not authorize the UI.** `docs/DIVERSITY_SETTING_ROADMAP.md` still blocks the Settings UI pending cross-pool results, a reviewed setting-to-penalty mapping and broader quality evidence; none of those gates is waived or closed here. The next step is gathering that evidence (an owner-scoped real-library measurement), not building the control. No code changed.

**Call path (line numbers on `main` at `9eb43d6`):**
- Stored value: `service_settings.py` `recommendation_diversity` (validated integer 0-100); default `0` in `navidrome_server.py:1197`; API `GET/PUT /api/settings/recommendation-diversity` in `app/api/settings.py`.
- `navidrome_server.py:455` passes `diversity_setting_fn` to `recommendation_cooldown.prepare_ranking_inputs` (`recommendation_cooldown.py:148`), which freezes the value into `ranking_context["diversity_setting"]`.
- `navidrome_server.py:463` maps it with `discovery_mmr.diversity_setting_to_penalty` (`min(v, 75) / 100`) into `AllocationRequest.diversity_penalty`.
- `discovery_personal_allocator.ranked_candidates` (`discovery_personal_allocator.py:62`) applies the penalty at every selection step: `relevance - penalty * max similarity to already-selected`, among ownership-clear candidates only. Owned and title-conflict candidates keep their legacy position and decisions. Hard filters, duplicate identity and release eligibility run after it, unchanged.
- `discovery_mmr.mmr_rerank` is **not** on the production path; only `recommendation_mmr_evaluate.py` calls it.
- **Setting 0 is a true no-op:** `ranked_candidates` returns the input order when `diversity_penalty == 0` (`discovery_personal_allocator.py:65`). Confirmed on a synthetic pool: setting 0 and no penalty select identical ids.

**Offline measurement** (synthetic pool, 60 candidates with two-tag sets over 10 clusters, relevance skewed toward 4 clusters, 30 seeds, count 10, production allocator; identity-free aggregates; the private capture was not used):

| setting | penalty | mean pairwise similarity | mean relevance score | overlap with setting 0 | distinct tags |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.00 | 0.330 | 1.357 | 1.00 | 5.8 |
| 25 | 0.25 | 0.277 | 1.340 | 0.88 | 7.1 |
| 50 | 0.50 | 0.153 | 1.233 | 0.68 | 11.1 |
| 75 | 0.75 | 0.091 | 1.114 | 0.55 | 13.6 |
| 100 | 0.75 | 0.091 | 1.114 | 0.55 | 13.6 |

Each step trades some relevance for diversity; **75 and 100 give identical output because the penalty saturates at 0.75** (the single-pool gate failed from 80 upward). Repeat rate was not measured (needs history; the synthetic pool has none). Limits: synthetic pool, so absolute numbers say nothing about real taste; future-listen quality is unmeasured; the allocator's category quotas and style reservations also shape the result.

**Draft acceptance criteria for the later UI task, valid only after the roadmap gates close** (see `CLAUDE_CLI.md`): a control over the existing endpoint, no backend edit; range 0-75 (or 0-100 labelled so 75-100 is not presented as stronger); default 0 shown as "Relevance"; reads with GET, saves with PUT, shows the API error text on a 4xx; a rendered browser check against the exact tested SHA.

### Live sample: diversity setting had no effect (2026-10-20, owner-approved, one sample, aggregate only)

Fresh data dir, slskd off, count 10, real library (1,733 albums). One live gather was captured, then the production path was re-run offline from that capture at settings 0, 25, 50, 75, 100. **All five returned the same 10 albums** (10 distinct artists, category mix 4/3/3, mean score 0.084). `recommendation_mmr_evaluate.py --identity-free` on the same capture agreed: mean pairwise similarity 0.285 and 7/10 baseline retained at every lambda from 0 to 1. The pool was 24 gathered albums, 10 owned, leaving 14 unowned (4 from CF, 10 from profile tag search) for 10 slots, so the penalty had almost nothing to reorder. This says nothing about future-listen quality and does not close any `DIVERSITY_SETTING_ROADMAP.md` gate; the diversity setting is paused.

Supply funnel from the same capture (`recommendation_replay.py`, aggregate): 200 CF recordings returned, 4 distinct artists (top two = 55.7% of recordings), 97 resolved and 103 failed (class "other"); 14 CF albums from 4 artists; 1,998 release groups seen, 1,591 eligible; 3 supplementary queries attempted, 1 failed; decisions: 10 selected, 7 already owned, 7 recent-genre-cap. The 103 failures were first suspected to be budget skips counted as "other"; the offline trace below refutes that. Limits: single sample, v2 capture lacks per-query supplementary yield.



## Candidate supply diagnosis (2026-10-20, offline trace plus one failed live attempt)

**Trace.** `cf_failure_classes` is built by `summarize_cf_recordings` (`discovery_candidate_supply.py`): every record that is not `resolved and no error_class` counts as failed, labelled by `classify_error`, which returns the exception class name only if it is on a bounded allowlist and otherwise `"other"`. In `discovery_candidate_gathering.py` the budget skip (`resolution_budget`) and the artist-cap skip `continue` **before** the record is appended, so neither can appear in `cf_failure_classes`; they are counted in `cf_paging.resolution_budget_skipped` and `artist_cap_skipped`. Since 97 resolved + 103 failed = 200 recordings considered = 200 returned, nothing was skipped before the sample's record list. The 103 "other" failures are therefore real exceptions outside the old allowlist (for example httpx `ConnectTimeout`, `ReadError`, `RemoteProtocolError`, which were not listed); replayed recorded errors raise `RuntimeError`, which was listed, so replay does not explain them. The exact class is still unknown.

**Change.** PR #467 (merge `27942379095cf41654fcb6298b3e9b0d9f56d730`, exact head `857a180ed6e93414122e0d23e9e413222a8606c0`, all four required workflows passed) widened the allowlist so the next run names the class. Diagnostics only; no lookup, selection, quota, budget or filter change.

**Live pair: not recorded.** Two cold-then-warm attempts (count 10, fresh data dir, slskd off) failed at the first step with `Could not retrieve recent listening history: The read operation timed out` after 30 s each, before any MusicBrainz lookup. A plain HTTP request to the same ListenBrainz endpoint returned 200 in about 2 s. The app's client was not changed (see the ListenBrainz client open item). No funnel numbers exist.

**Decisions.** (1) Page cap for recent listens (3 to 5 pages) was drafted as PR #468 and **closed unmerged**: the owner cannot afford more ListenBrainz requests per run. Branch `feat/listens-page-cap` is kept. The owner's history is under 30 days, so the cap, not the window, limits recent listens (300 listens max today). (2) The live pair is deferred; retry when the client reaches ListenBrainz. (3) Step 4 of the handoff (budget per run, batch default, or CF concentration) stays open until the funnel exists; the unmeasured 4-artist concentration (top two = 55.7%) points at Phase 4.3.

## Phase 4.3 wider ListenBrainz CF pool: finding (2026-10-20, offline, docs and code only)

**Official documentation** (checked 2026-10-20): <https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html>. Endpoint `GET /1/cf/recommendation/user/(mb_username)/recording`, marked experimental ("probably will change"). Parameters that exist: `count` (optional, default `DEFAULT_ITEMS_PER_GET`, max `MAX_ITEMS_PER_GET`) and `offset` (optional, pagination). Response `payload`: `mbids` (list of `recording_mbid` + `score`), `last_updated`, `type`, `entity`, `user_name`, `count`, `offset`, `total_mbid_count`; "sorted on rating and ratings". Parameters that do **not** exist: any artist type, artist filter, genre, date or score-threshold filter (the sample response shows a `type` field, but the page documents no matching request parameter). No other recording-recommendation endpoint exists; the other `/1/recommendation/*` endpoints only submit, delete or read user feedback. The numeric values of the default and maximum page size are not stated on the page, so the app's `CF_PAGE_SIZE = 100` is unconfirmed against the documentation.

**How the 4-artist concentration arises (code trace).** The response carries only recording MBIDs and scores, no artist, so the app cannot see or filter by artist before resolving each recording. `cf_distinct_recording_artists` and `cf_top2_artist_recording_share` are computed by `summarize_cf_recordings` over **resolved** records only (97 of 200 in the live sample); the 103 failed recordings have no artist and are excluded, so the 4 artists and the 55.7% share describe the 97 survivors, not the 200-recording window. Whether the response itself clusters by artist is therefore **not established**: the 103 unresolved recordings may belong to other artists. `CF_ARTIST_RESOLUTION_CAP` (10) cannot explain the figure either: it skips only recordings already in the metadata cache whose artist reached 10 (`artist_cap_skipped`, covered by `RecommendationCfPagingTests`), and a fresh data dir has no cache, so on a cold run it is inert. Four artists at the cap would account for at most 40 recordings, not 97.

**Decision: leave CF paging and the cap alone; no code change.** Options considered:
- *Widen paging* (`CF_MAX_PAGES` above 2): adds ListenBrainz requests per run. Not allowed without owner approval (standing rule 2026-10-20), and it would also feed more recordings into the 100-per-run MusicBrainz budget, which the 103 failures suggest is not the binding constraint yet.
- *Change the artist cap*: inert on cold runs and only skips cache-known recordings, so it cannot widen a cold pool; lowering it risks dropping valid warm-run recordings with no measurement behind the change.
- *Widen another lane*: out of scope for this item and needs its own measurement.

**Risk named.** Acting on the "4 artists" figure now would tune against a number that is partly an artifact of the 103 unresolved recordings. The failure class is unknown until PR #467's allowlist names it on a live run.

**Open, needs the owner:** (1) the live cold/warm pair (blocked by the client timeout), which would show the artists of the failed recordings only once they resolve; (2) approval for any extra ListenBrainz page; (3) optionally, a one-request check of `total_mbid_count` from an already-made page (no extra request: the field is in the existing response) to learn the real CF pool size before deciding whether paging could help at all. Item 3 was approved by the owner and built: `cf_paging.total_mbid_count` (integer from the first page's response, else `None`); no extra request, no selection change.

**Client identity (owner-approved 2026-10-20):** `listenbrainz_client.request_headers()` sends `User-Agent: NavidromeLibrarian/1.0 (+https://github.com/abucalip/navi-librarian)` and, only if the env var `LISTENBRAINZ_TOKEN` is set, `Authorization: Token <token>`. Applies to the recent-listens call; the token is never logged or stored. Effect on the browser-verification timeout is unmeasured until a live run.

Tests (focused): `test_discovery_candidate_gathering`, `test_discovery_candidate_supply` (53, OK), `test_listenbrainz_client` plus `py_compile` on the changed files. CI: see the PR.
