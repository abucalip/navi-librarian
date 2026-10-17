# Recommendation engine improvement roadmap

Status: active implementation. Phase 0 is closed for prioritization based on the owner's sustained real-world evidence; this is not a claim that the exact technical root cause has been proven. This roadmap consolidates the 2026-10-17 hardcoding audit, implementation evidence from `main` at `a977016a6f260d87518a595e22fb641963893b9c`, the DroppedNeedle review, and recommendation-system research. It prioritizes diagnosis and offline measurement before ranking changes. This document does not authorize publishing or deployment.

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

### Phase 2 — Make candidate generation reflect the current profile

Proceed after Phase 0, and coordinate with Phase 1 so query changes can be evaluated independently from score changes.

#### 2.1 Replace fixed supplementary tag searches

Derive a bounded set of MusicBrainz tag queries from the highest-weighted tags in recent artists' cached genres and tags that co-occur among strong CF candidates. Keep a small exploration quota whose tags are drawn from the broader candidate pool, rather than from fixed regional constants.

Remove fixed regional one-slot targets and replace them with measured diversity selection (Phase 3) or profile-derived allocation. If the owner wants specific regional styles favored, expose them as explicit, empty-by-default pinned interests rather than code constants.

Keep candidate caps, rate limits, diagnostics, and graceful provider-failure behavior. Query selection must respond to changed profile fixtures even when the genre cache is unchanged.

#### 2.2 Review classification overrides and source provenance

Replace artist-name classification sets with normalized provider tags where possible. Any remaining exception must document why metadata is insufficient and include direct regression coverage.

Track all source provenance for each candidate (CF, profile-derived tags, similar-artist lookup, library gap, new release, or optional popularity fallback). Merge and deduplicate sources before eligibility/ranking; a source's presence must not guarantee a fixed number of slots.

**Acceptance gate:** contrasting profiles generate different supplementary queries where metadata supports it; exploration remains available but is not a hidden personal preference; provider calls remain bounded.

### Phase 3 — Improve list diversity and recommendation freshness

#### 3.1 Greedy MMR-style re-ranking

After relevance scoring and hard eligibility/artist caps, apply a deterministic greedy marginal relevance/diversity re-ranker. Start with the concrete similarity:
- 1.0 for the same artist.
- Otherwise Jaccard overlap between MusicBrainz tag sets.

Use `selection_score = relevance_score - lambda × max_similarity(candidate, selected)` as the initial form. Evaluate `lambda` with the Phase 0 replay harness. Do not let soft diversity penalties replace hard product constraints, including one-album-per-artist requirements where applicable. Preserve high-relevance candidates unless measured results justify a trade-off.

This replaces the four fixed regional slots as the diversity mechanism; it does not prohibit regional styles from being recommended.

#### 3.2 Recommendation history and cooldown

First inspect `discovery_store.py` and existing persistence to see whether recommendation batches are already retained. If not, persist a minimal batch history (album identity, timestamp, rank) sufficient for repeat-rate metrics and comparisons.

Use history for a soft, time-limited cooldown when candidates are otherwise comparable. Define expiry explicitly; never permanently exclude a candidate merely because it was previously shown. Account for missing/deleted albums and storage growth.

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

PR #298 implements Phase 0.1/0.2 infrastructure: bounded diagnostics, deterministic synthetic metrics, and an opt-in private capture/offline replay harness. The private baseline captured at `d8c1f3de5180b35919f55c304d55e5c939dad373` replays successfully offline (10/10 recommendations; 197 provider events; 40 Last.fm events; zero network providers). The comparator covers all stable top-level fields except volatile pool diagnostics and Last.fm error state. These results establish replay fidelity, not recommendation quality: the current session has not inspected the private capture's full metric output, and the synthetic fixture is not a substitute for the user's historical replay.

PR #303 adds bounded origin/outcome telemetry for personal-list refreshes, separating manual refresh requests from the hourly scheduler and keeping the latest outcome for each origin. No ranking, candidate selection, allocation, or public response fields are intentionally changed. Verify all required gates on the exact final PR head before treating this step as complete.

Next, add aggregate candidate provenance, score-component, profile-evidence, cache, and rejection diagnostics as a separate baseline-independent observability task. Do not change scoring, source selection, candidate generation, or allocation until the real baseline metrics and limitations have been reviewed.

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
