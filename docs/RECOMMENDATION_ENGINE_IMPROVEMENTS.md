# Recommendation engine improvement roadmap

Status: active implementation. Phase 0 is closed for prioritization based on the owner's sustained real-world evidence; this is not a claim that the exact technical root cause has been proven. This roadmap consolidates the 2026-10-17 hardcoding audit, implementation evidence from `main` at `a977016a6f260d87518a595e22fb641963893b9c`, the DroppedNeedle review, and recommendation-system research. It uses deterministic diagnostics and offline measurement to guide changes, while owner-reported sustained real-world failure can prioritize ranking responsiveness without claiming a proven technical root cause. This document does not authorize publishing or deployment.

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

**Acceptance gate:** controlled fixtures show reduced repeated artists/styles and improved handling of feedback without collapsing relevance, creating permanent exclusions, or violating eligibility rules.

### Phase 4 — Evaluate additional candidate lanes (only when earlier phases justify them)

These are candidates for experiments, not committed additions. Check existing modules and source overlap before implementation.

1. **Library gaps / deep dives:** for artists with several owned albums, find missing studio albums via MusicBrainz release groups. Inspect `discovery_new_releases.py`, classics modules, and existing library snapshot logic first to avoid duplicate inventory/catalog work.
2. **Similar artists seeded by recent listening:** evaluate Last.fm `artist.getSimilar` or a ListenBrainz similarity endpoint only if current official documentation confirms the endpoint and its behavior. Seed from a small weighted set of recent artists, prefer MBIDs, aggregate evidence from multiple seeds, and downweight weak/stale matches. Cache provider results while recalculating profile-dependent weights on each refresh.
3. **Wider ListenBrainz CF pool:** check current official documentation for pagination or artist-type/filter parameters. The current code requests `count=100`; do not assume additional parameters exist until confirmed.
4. **Popularity/trending fallback:** only consider it as a capped cold-start or optional lane, never as a dominant personal signal.

For each lane, compare against the Phase 0 baseline and simpler profile-driven sources. Retain only sources that improve measured outcomes enough to justify operational complexity, cache/rate-limit cost, and failure modes. ListenBrainz's recording-level CF endpoint is already in use; do not describe it as a new prototype or replacement.

## Lessons and design patterns retained from prior research

### DroppedNeedle: distinct sources and discovery intents

The public [DroppedNeedle repository](https://github.com/DroppedNeedle/DroppedNeedle) and [feature documentation](https://www.droppedneedle.com/docs/features) describe discovery entry points including similar artists, library gaps, fresh releases, charts, ListenBrainz/Last.fm patterns, and “Because You Listened To” rows. This supports using independent candidate generators with provenance and keeping existing lists focused on distinct intents:
- **Personal discoveries:** recent-listening responsiveness with controlled adjacent novelty.
- **Classics / collection-building:** meaningful library gaps and relevance, not popularity alone.
- **Artist Deep Dives:** explore owned artists without letting one artist dominate a row.
- **New Releases:** recency plus reliable artist identity and release eligibility.

Do not add new UI modes in the initial backend work. The public docs establish product features, not DroppedNeedle's exact internal algorithm or measured quality; do not attribute unverified ranking internals to it.

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

## Immediate next step

PR #309 implemented 14-day half-life recency weighting, a smooth familiarity curve, and a recent-profile multiplier cap of 25%. PR #310 added a deterministic contrasting-profile regression, and PR #312 replaced fixed supplementary MusicBrainz tag searches with profile-derived queries plus a bounded exploration quota. PR #320 added the offline MMR evaluator; PR #326 added the preference contract and allocator integration. PR #329 now provides bounded ranked recommendation history (hashed identities only; 30-day retention, 2,000-row cap), with all four required workflows passing on exact PR head `613fd85715eaedc69f2375daf3cb6da6833c63bb`.

**Next recommendation-engine step (2026-10-18):** PR #341's final-shortlist evaluator metrics are merged. Define and review a rollout gate for relevance retention and category mix before any diversity UI work. A provisional gate is now documented in `docs/DIVERSITY_SETTING_ROADMAP.md`; it is not approved or passed because the existing private fixture has not been rerun with the new category metrics. Do not rerun the dismissed 35-combination/floor reproduction, collect a new live capture, or fabricate history for cooldown calibration. Keep cooldown constants uncalibrated, keep the diversity UI blocked, and leave publishing/deployment unauthorized.

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

## Out of scope unless separately approved

- Rewriting the recommender or adding a machine-learning stack.
- Further broad modularization; its roadmap is complete.
- New UI modes or UI redesign as part of initial backend changes.
- Removing ownership/release eligibility or safety checks.
- Shortening all cache TTLs without evidence.
- Publishing or deploying an image.


## Score attribution and shortlist diagnostics (PR #366, 2026-10-18)

The profile-comparison evaluator now reports aggregate distributions for the final discovery score, recent-profile multiplier, Last.fm popularity multiplier, recent artist play counts, and exploration-family match share. It also reports allocation decision counts, candidate/selected category counts, the selected candidates' score-rank distribution, and overlap/Jaccard between the score-ranked top-k and the final allocated shortlist. These diagnostics are aggregate-only: no candidate identities or per-candidate score rows are serialized. The metrics help separate scoring/rank movement from allocation effects; they do not establish relevance or future-listen quality. Deterministic synthetic regression coverage is included. PR #366 merged as `0588ec0cc8b0ed5ad32c596c5d2c5e314f107639` from exact tested head `deabda7d04f66909a6da5b2fec7dc889ed27a200`; all four required workflows passed on that exact head (syntax/full suite `39160186431`, packaging/full suite/build `39160186619`, container smoke `39160186497`, validation-only multi-architecture `39160186550`; 739 tests passed). No local tests or private capture replay were run by the assistant. Publishing remains paused.

**Next action:** owner reruns the offline evaluator using PR #370's exact source in the isolated test environment, then shares only aggregate JSON. PR #370 distinguishes classifier `assigned_category` from allocator `discovery_category`, adds actual allocator category counts and target/shortfall diagnostics, and adds a deterministic test with the observed 19-candidate category shape. The new synthetic test passes and proves fallback fills ten when enough eligible unique-artist candidates exist; it does not yet reproduce the owner's exact underfill. Code head `0dfe32d098b4acb4c1ce78dfef7422b64189297b` passed all four required workflows (syntax/safety and Docker full-suite workflows each ran 747 tests; container smoke and validation-only multi-architecture checks succeeded). An earlier head failed one fixture assertion, which was corrected before these successful runs. Keep private captures and identity-bearing artifacts outside GitHub; do not change allocation policy until the new report establishes the cause.

## Underfilled shortlist — next diagnostic pass (2026-10-18)

Owner replay shows 5/10 returned from 19 resolved candidates; category targets are adjacent 4, adventurous 3, cross-genre 3, but the pool has no adventurous candidates. Four candidates are owned and ten final candidate statuses report recent-family-cap rejection. The earlier synthetic test proves the broad category shape alone does not prevent filling ten, but does not reproduce the exact pool.

PR #370 now adds allocator pass counters (entry and attempt counts for each fallback stage), checked-count/max-check values, and authoritative allocator decision counts to the aggregate-only evaluator. This is diagnostic instrumentation only; no selection behavior or ownership protection changes. The owner should replay the private capture using the updated PR source and provide only aggregate output. Use phase-attempt counts and decision counts to determine whether fallback was skipped, candidates were reconsidered but blocked by artist/identity/ownership constraints, or a different issue exists. Do not tune ranking weights or merge before the evidence and exact-head CI are reviewed.


## Shortlist underfill diagnostics update (PR #370, 2026-10-18)

The owner-side replay against the diagnostic branch reports that final fallback entered and attempted all 19 candidate rows, while the shortlist remained 5/10 and the check count was 14/60. The 10 final `recent_genre_cap_reached` decisions are inconsistent with the final fallback, which explicitly relaxes that cap. The allocator checked family caps before normalized identity; when a duplicate identity had already been processed through another row, `decisions.setdefault` could preserve the earlier family-cap status instead of reporting `duplicate_candidate`. PR #370 now prioritizes hard duplicate-identity rejection ahead of soft diversity caps and tests that attribution. This is a diagnostics correction, not a selection-policy change. The underfill's actual eligible unique-artist/identity supply remains unproven until the owner reruns the evaluator on the corrected branch and shares aggregate-only output. Do not tune weights or relax ownership checks based on this report alone.


Verification update: the first attempted diagnostic-precedence change failed two tests on head `43411aa29c63cece935475d0328a1d1d0bad4f49`; the selection-order expectation and exact-owned diagnostic precedence were corrected. Exact code head `277560ab0185d8b1beb6beafdb4a055b316e3a3b` passed all four required workflows: Python syntax `39172112667`, Docker packaging/full suite/build `39172112675` (777 tests), container runtime smoke `39172112640`, and validation-only multi-architecture image validation `39172112650`. The owner-side evaluator has not yet been rerun against this corrected source; selection behavior remains unchanged and publishing remains paused.
