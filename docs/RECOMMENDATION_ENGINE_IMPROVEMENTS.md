# Recommendation engine: audit findings, research, and proposed improvements

Status: planning and research only. This document records the 2026-10-17 hardcoding audit and follow-up research into DroppedNeedle and public recommendation-system approaches. It does not authorize changing recommendation behavior by itself. Implement a focused behavior change in a later PR after inspecting the current implementation and writing characterization/regression tests.

## Goal

Recommendations should respond meaningfully to changes in recent listening and the library, avoid repetitive lists, and balance relevance with discovery. Keep eligibility and ownership correctness, provider safety, response contracts, and existing acquisition behavior intact. Avoid hidden personal taste assumptions and fixed artist/genre preferences unless they are explicit, configurable product choices.

## Current diagnosis

### Fixed supplementary discovery queries

discovery_candidate_gathering.py contains a fixed set of 20 MusicBrainz tag searches covering regional/style families, including North African music, African styles, Brazilian music, jazz, soul, and rock. The supplementary path can add up to 60 candidates, with up to five new candidates per query, and its search results are cached for 30 days. This makes the same discovery directions recur even when listening changes.

### Fixed regional-style selection targets

navidrome_server.py::recommend_new_music() supplies one-slot targets for north_african, afrobeats, afro_jazz, and malian_desert_blues. These targets are not calculated from recent listening and can reserve recommendation capacity for those styles regardless of the current profile.

### Artist-specific classification overrides

discovery_recommendations.py contains explicit artist-name sets used for regional/style classification. These exceptions can override metadata-driven classification and overlap with the fixed regional discovery preferences. Prefer metadata-based classification; retain only individually justified, documented exceptions if provider metadata demonstrably fails.

### Personalization signals and caches

The engine reads recent ListenBrainz listens over a rolling 30-day window and uses MusicBrainz genre tags for a bounded candidate pool (up to 60 candidate artists plus up to 15 recently scrobbled artists when slots are available). Artist genre metadata is cached for 90 days and Last.fm album popularity for 30 days. Caching is not inherently wrong, but the scoring and query-selection layers must allow current listening to influence ranking even when metadata is cached.

### Refresh behavior is a separate question

Discovery lists are persisted by discovery_refresh.py. The audit did not establish every UI action's refresh behavior or measure whether stale list state contributes to the observed repetition. Verify refresh triggers and scheduler behavior separately from algorithm changes.

## Lessons from DroppedNeedle

Reviewed the public [DroppedNeedle repository](https://github.com/DroppedNeedle/DroppedNeedle), its README, and its [feature documentation](https://www.droppedneedle.com/docs/features). Its documented discovery design combines several distinct entry points rather than relying on one undifferentiated recommendation list.

### 1. Blend independent candidate sources

DroppedNeedle describes a discovery queue drawing from similar artists, library gaps, fresh releases, global charts, and ListenBrainz/Last.fm listening patterns. Its home page also separates trending artists, popular albums, recently added music, genre links, and personalised “Because You Listened To” rows.

**Application to Librarian:** treat sources as candidate generators with explicit provenance, not as hard-coded category quotas. Candidate sources worth evaluating:

- Recent listening and artist similarity.
- MusicBrainz genre/tag exploration seeded from the current profile.
- Library gaps / collection-building opportunities.
- New releases by artists already represented in the library.
- ListenBrainz collaborative recommendations, if the recording-to-album mapping and provider availability are useful enough.
- A bounded popularity/trending source as a weak fallback or optional lane, never the dominant personal signal.

Merge, deduplicate, validate eligibility, and rank the combined candidate pool. Track which source(s) proposed each candidate so tests and explanations can show why it appeared. A source's existence must not guarantee a slot in the final list.

### 2. Separate discovery modes by intent

DroppedNeedle's documented weekly ListenBrainz exploration playlist is distinct from its more familiar personalised recommendations and charts. This suggests that one ranking cannot simultaneously optimize familiarity, novelty, and broad exploration without making trade-offs invisible.

**Application to Librarian:** preserve the product's existing lists, but give each an explicit intent:
- **Personal discoveries:** strongest response to recent listening, with a controlled amount of adjacent novelty.
- **Classics / collection-building:** quality/relevance and meaningful library gaps, not simply global popularity.
- **Artist Deep Dives:** explore artists already in the library, without letting one artist dominate a row.
- **New Releases:** recency and reliable artist identity/album eligibility.

Do not add new UI modes as part of the first algorithm fix. First make candidate generation and ranking responsive within the existing contracts.

### 3. Use listening history as a signal, not a fixed identity

The app documentation says personalised discovery depends on connecting ListenBrainz or Last.fm, and offers “Because You Listened To” recommendations. This is a useful product pattern: show a clear connection to actual listening and do not imply personalisation when no usable history exists.

**Application to Librarian:** keep recent listens as a first-class, time-sensitive ranking signal. For each candidate, record which recent artists/listens or profile features contributed to its score. A changed listening history should be able to change both query selection and the candidate order; cached genres should enrich that calculation but must not freeze it.

### 4. Keep source evidence and explanations

DroppedNeedle's discover cards expose album details and previews before a user requests or skips them. Librarian is album-first and has acquisition actions, so confidence and explanation are particularly useful.

**Application to Librarian:** add internal candidate diagnostics first: source(s), relevant seed artist(s), recent-listening contribution, genre/tag overlap, popularity contribution, novelty/familiarity, ownership/eligibility rejection reason, and final score components. User-facing explanations can be a later UI task; do not make this backend research depend on a UI redesign.

### Limits of the comparison

DroppedNeedle's public docs establish the product's discovery features, not the exact implementation or measured recommendation quality. Do not assume its source code uses a particular ranking formula, collaborative-filtering model, or diversity algorithm unless code-level evidence confirms it. Reuse ideas and testable patterns, not unverified internals.

## Findings from recommendation-system research and music services

### 1. Re-rank for diversity and serendipity after relevance scoring

Music recommender research notes that systems optimized only for similarity/popularity can over-specialize and repeatedly suggest familiar material. Serendipity-oriented greedy re-ranking research finds that diversity can improve serendipity, but that increasing diversity too far can reduce accuracy. Diversity should therefore be controlled rather than maximized blindly. See Kotkov et al., [“How does serendipity affect diversity in recommender systems?”](https://link.springer.com/article/10.1007/s00607-018-0687-5) and the review [“Current challenges and visions in music recommender systems research”](https://link.springer.com/article/10.1007/s13735-018-0154-2).

**Recommended technique: greedy marginal relevance/diversity re-ranking.** First compute relevance scores. Then select the next album by balancing its relevance against similarity to already selected albums, for example:

    selection_score(candidate) = relevance(candidate) - lambda * max_similarity(candidate, selected)

The similarity can combine artist identity, shared MusicBrainz tags/genres, and other available metadata. Start with a simple, deterministic implementation and a small configurable penalty. Avoid adding a machine-learning dependency before the simpler method is measured. A related standard technique is Maximal Marginal Relevance (MMR); treat it as a candidate design, not an assumed requirement.

For an album-oriented result set, diversity should be evaluated across both artists and styles. Enforce one album per artist where product requirements already demand it; do not rely on the softer diversity penalty to replace a hard eligibility rule.

### 2. Consider collaborative recommendations as a separate candidate source

ListenBrainz documents a collaborative-filtering recording recommendation endpoint that returns MusicBrainz recording IDs and scores. It also provides a Weekly Exploration playlist based on collaborative filtering, intended to surface music the user has not heard. The recommendation endpoint is explicitly documented as experimental, and data/playlist generation has its own update schedule.

Sources: [ListenBrainz recommendation API](https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html), [ListenBrainz documentation](https://listenbrainz.readthedocs.io/en/latest/), and [ListenBrainz data update intervals](https://github.com/metabrainz/listenbrainz-server/blob/master/docs/general/data-update-intervals.rst).

**Application to Librarian:** investigate this as an optional candidate generator, not as a wholesale replacement for the current album-ranking engine. Assess:
- Whether the user's ListenBrainz identity and endpoint are available and reliably configured.
- How many returned recording MBIDs map to usable MusicBrainz release groups/albums.
- How to aggregate recording scores to album candidates without letting albums with many tracks gain an unfair advantage.
- How to filter owned albums, compilations/remixes/non-album releases, and ambiguous artist identities.
- Endpoint freshness, empty/204 responses, rate limits, and fallback behavior.

Because the API is experimental and recording-level, this should follow the baseline responsiveness and diversity work rather than block it.

### 3. Use similar-artist data as a bridge, not as truth

Last.fm's official API exposes artist.getSimilar, with a similarity match value and optional MusicBrainz ID. See [Last.fm API documentation](https://www.last.fm/api/show/artist.getSimilar) and the [Last.fm API overview](https://www.last.fm/api).

**Application to Librarian:** similar artists can bridge from recent listens to candidates not represented by the current fixed genre queries. Seed the lookup from a small, weighted set of recent artists, prefer MBIDs over names, and aggregate scores from multiple seeds. Reduce the influence of an artist that is only weakly related or appears as a single stale seed. Cache provider results according to provider limits, but recalculate the profile-dependent weights on each refresh.

Do not let Last.fm album popularity stand in for taste. Popularity is a weak tie-breaker or cold-start fallback and should be capped/normalized so it cannot swamp the personal score.

### 4. Evaluate diversity as a product outcome, not a genre quota

A longitudinal study of diversified music recommendations found that exposure to varied recommendations can affect curiosity and openness to less familiar music. It supports measuring discovery quality beyond immediate similarity, but does not prescribe a universal diversity level for every listener. See Porcaro, Gómez, and Castillo, [“Assessing the Impact of Music Recommendation Diversity on Listeners”](https://dl.acm.org/doi/10.1145/3608487).

**Application to Librarian:** measure both whether recommendations track recent listening and whether the result set contains useful variety. Do not substitute fixed regional quotas for measured diversity. Keep a configurable exploration component that is derived from the current profile and broad candidate pool, with safeguards against a single tag or source monopolizing the result.

### 5. Keep a clean distinction between freshness and metadata caching

ListenBrainz documents different refresh schedules for raw listens, statistics, similarity data, and generated playlists. This reinforces that “recent listening”, “provider metadata”, and “precomputed recommendation output” are different freshness domains.

**Application to Librarian:** inspect each cache and persisted list independently. Record cache key, TTL, purpose, and whether it contains user-dependent output or relatively stable catalog metadata. Do not shorten all TTLs indiscriminately. User-dependent ranking should be recomputed when a discovery refresh is requested, even if catalog metadata remains cached.

## Proposed design for Librarian

### Phase 0 — Characterize the current engine and refresh path

1. Inspect current main implementations and callers for recent_listening_profile(), recommend_new_music(), candidate gathering, scoring/allocation, discovery_recommendations.py, discovery_refresh.py, and relevant tests.
2. Trace every refresh trigger and persisted discovery-list read/write. Establish whether the observed repetition is from candidate generation, ranking, caching, or stale displayed output.
3. Add/confirm deterministic diagnostics for candidate counts by source, profile timestamp/window, cache hit/miss, rejection reason, final score components, and selected output.
4. Capture baseline behavior on fixtures before altering algorithms.

### Phase 1 — Remove hidden preference and improve responsiveness

1. **Remove forced regional quotas.** Remove the four fixed regional-style targets or replace them with profile-derived allocation and a general exploration floor. Do not remove those genres from consideration; make their representation responsive rather than guaranteed.
2. **Make supplementary discovery profile-driven.** Derive a bounded set of MusicBrainz tag queries from recent listens, available artist genres, and library context. Preserve rate limits, bounded candidate counts, failure diagnostics, and an exploration path for unfamiliar styles.
3. **Simplify artist-specific overrides.** Prefer provider metadata and normalized tags. Keep exceptions only with a documented reason and direct regression coverage.
4. **Review scoring influence.** Characterize how recent artist familiarity, recent-family bonuses, Last.fm popularity, initial candidate scores, and allocation interact. Prevent popularity or fixed seed scores from routinely overpowering current listening.
5. **Fix refresh semantics if proven stale.** If the refresh trace shows persisted output is not regenerated when expected, correct that as a separate, testable root-cause fix.

### Phase 2 — Reduce list repetition

1. Apply a small, deterministic diversity-aware re-ranker after eligibility and relevance scoring.
2. Penalize duplicate artists and near-identical style profiles in the same result set; keep any product-required hard artist limits as hard constraints.
3. Prefer less recently recommended candidates when relevance is otherwise comparable, if recommendation history is available. Define the time window explicitly and avoid permanent exclusion.
4. Track the provenance of each candidate so source diversity can be inspected. Do not force each source to contribute a fixed number of albums.
5. Only introduce randomized tie-breaking if a deterministic seed is injected and tests prove repeatability; stable deterministic diversity is preferable initially.

### Phase 3 — Add external candidate sources only when justified

1. Prototype ListenBrainz collaborative recommendations with recording-to-album mapping and clear diagnostics.
2. Prototype Last.fm similar-artist candidates seeded by current listening, with popularity treated separately.
3. Compare the extra sources against the simpler profile-driven MusicBrainz approach before keeping them. Avoid broadening the architecture or adding dependencies without measurable improvement.

## Test and evaluation plan

Use provider-injected fixtures; do not rely on live provider APIs for correctness tests.

### Core behavioral tests

- Two materially different recent-listening histories lead to changed profile-derived queries and/or candidate ranking when candidate metadata supports the difference.
- Identical inputs and deterministic settings produce identical results.
- A candidate supported by multiple recent seed artists scores appropriately relative to one supported only by a weak/stale seed.
- Fixed regional preferences and artist-name overrides no longer dominate results in the absence of profile evidence.
- Popularity cannot routinely overpower relevant personal signals.
- Candidate results remain bounded and provider failures degrade safely.
- Cached genre/similarity metadata can be reused without freezing profile-dependent ranking.
- Refresh actions regenerate user-dependent output when intended; persisted results have observable freshness metadata or equivalent diagnostics.
- Diversity re-ranking reduces repeated artists/styles in a controlled fixture without displacing all high-relevance candidates.
- The same artist is never duplicated where a product rule forbids it.
- Optional collaborative recommendations handle empty, stale, malformed, and unmappable recording IDs safely.

### Metrics to report in tests/diagnostics

- **Responsiveness:** overlap and ranking changes between contrasting listening profiles.
- **Novelty:** fraction of recommendations whose artist/album is not in recent listening history (separate from library ownership).
- **Intra-list diversity:** unique artists and genre/tag spread, plus average pairwise candidate similarity if metadata supports it.
- **Repeat rate:** overlap with previous recommendation batches over a defined period.
- **Relevance guardrails:** score distribution and retention of high-relevance candidates before/after re-ranking.
- **Eligibility correctness:** owned-album, compilation/remix/non-album, and artist-identity rejection counts.

Do not set arbitrary numeric targets before collecting a baseline. First make the metrics reproducible, then agree on target thresholds.

## Acceptance criteria

- No hidden, fixed genre quotas remain in personal recommendations unless documented as an explicit product policy.
- Candidate query selection and ranking are influenced by recent listening and library context, while preserving bounded exploration.
- Controlled different-profile tests demonstrate meaningful query/ranking changes without relying on live provider APIs.
- Identical fixtures and deterministic inputs produce repeatable results.
- Diversity re-ranking measurably reduces repetitive artists/styles on controlled fixtures without collapsing relevance.
- Missing genre metadata or provider failures degrade safely and do not cause popular/fixed-seed candidates to dominate by accident.
- Refresh behavior is verified; any stale persisted output is fixed only when the root cause is established.
- Ownership, artist identity, release eligibility, response schema, and acquisition regression tests remain passing.
- Any cache TTL change is justified by measured impact and provider limits, not shortened indiscriminately.

## Invariants and constraints

- Keep owned-album exclusion, compilation/remix/non-album filtering, artist identity checks, and existing album/release eligibility rules.
- Preserve response schemas, acquisition behavior, and the remaining MCP compatibility surface unless separately approved.
- Keep provider calls bounded and failures non-fatal where existing behavior requires graceful degradation.
- No publishing or deployment is authorized by this document; image publishing remains paused.
- The first implementation should be a small behavior change with focused tests, not a full recommender rewrite or new machine-learning stack.

## Research references

- DroppedNeedle repository and documented features: https://github.com/DroppedNeedle/DroppedNeedle and https://www.droppedneedle.com/docs/features
- ListenBrainz collaborative recording recommendations: https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html
- ListenBrainz data update intervals: https://github.com/metabrainz/listenbrainz-server/blob/master/docs/general/data-update-intervals.rst
- Last.fm similar artists API: https://www.last.fm/api/show/artist.getSimilar
- Kotkov, Veijalainen, Wang, “How does serendipity affect diversity in recommender systems?”: https://link.springer.com/article/10.1007/s00607-018-0687-5
- “Current challenges and visions in music recommender systems research”: https://link.springer.com/article/10.1007/s13735-018-0154-2
- Porcaro, Gómez, Castillo, “Assessing the Impact of Music Recommendation Diversity on Listeners”: https://dl.acm.org/doi/10.1145/3608487

## Out of scope unless separately approved

- Rewriting the whole recommendation engine.
- Broad modularization; the modularization roadmap is complete.
- Shortening every cache duration without measuring its effect.
- Removing legitimate eligibility and ownership safety rules.
- UI redesign or adding new discovery modes as part of the first backend fix.
- Publishing or deploying an image.
