# Recommendation engine: audit findings and proposed improvements

Status: planning only. This document records findings from the 2026-10-17 hardcoding audit. It does not authorize changing recommendation behavior in the configuration-cleanup PR. The recommendation-engine work should be scoped and implemented in a later session.

## Goal

Recommendations should respond meaningfully to changes in the user's recent listening and library while preserving useful exploration, album eligibility, ownership checks, provider safety, and stable response contracts. Avoid hidden personal taste assumptions and fixed artist/genre preferences unless they are explicit user-configurable choices.

## Audit findings

### Fixed supplementary discovery queries

`discovery_candidate_gathering.py` contains a fixed set of 20 MusicBrainz tag searches covering regional/style families, including North African music, African styles, Brazilian music, jazz, soul, and rock. The supplementary path can add up to 60 candidates, with up to five new candidates per query, and its search results are cached for 30 days. This makes the same discovery directions recur even when listening changes.

### Fixed regional-style selection targets

`navidrome_server.py::recommend_new_music()` supplies one-slot targets for `north_african`, `afrobeats`, `afro_jazz`, and `malian_desert_blues`. These targets are not calculated from recent listening and can reserve recommendation capacity for those styles regardless of the current profile.

### Artist-specific classification overrides

`discovery_recommendations.py` contains explicit artist-name sets used for regional/style classification. These exceptions can override metadata-driven classification and overlap with the fixed regional discovery preferences. Prefer metadata-based classification; retain only individually justified, documented exceptions if provider metadata demonstrably fails.

### Personalization signals and caches

The engine reads recent ListenBrainz listens over a rolling 30-day window and uses MusicBrainz genre tags for a bounded candidate pool (up to 60 candidate artists plus up to 15 recently scrobbled artists when slots are available). Artist genre metadata is cached for 90 days and Last.fm album popularity for 30 days. Caching is not inherently wrong, but the scoring and query-selection layers must allow current listening to influence ranking even when metadata is cached.

### Refresh behavior is a separate question

Discovery lists are persisted by `discovery_refresh.py`. The audit did not establish every UI action's refresh behavior or measure whether stale list state contributes to the observed repetition. Verify refresh triggers and scheduler behavior separately from algorithm changes.

## Proposed work for the next session

1. **Remove forced regional quotas.** Remove the four fixed regional-style targets or replace them with profile-derived targets that are based on current listening and have a general exploration floor. Do not remove those genres from consideration; make their representation responsive rather than guaranteed.
2. **Make supplementary discovery profile-driven.** Derive a bounded set of MusicBrainz tag queries from recent listens, available artist genres, and library context. Preserve rate limits, bounded candidate counts, failure diagnostics, and an exploration mechanism so the engine can still introduce unfamiliar styles.
3. **Simplify artist-specific overrides.** Replace artist-name lists with provider genre metadata and normalized tags wherever possible. Keep exceptions only with a documented reason and direct regression coverage.
4. **Review scoring influence.** Characterize how recent artist familiarity, recent-family bonuses, Last.fm popularity, initial candidate scores, and allocation interact. Ensure popularity and fixed seed scores cannot routinely overpower the current listening profile.
5. **Measure repetition and responsiveness.** Add deterministic tests with controlled candidate/provider fixtures and two materially different listening histories. Assert that changed profiles can change query selection and candidate ranking, while identical inputs remain stable when randomness is injected deterministically.
6. **Verify cache/refresh boundaries.** Confirm that recent ListenBrainz data is fetched at refresh time, identify which metadata caches are relevant to ranking, and test that cached metadata does not freeze the user's listening profile. Establish which UI actions trigger refresh and whether saved lists can appear stale.
7. **Preserve invariants.** Keep owned-album exclusion, compilation/remix/non-album filtering, artist identity checks, response schemas, acquisition behavior, and MCP compatibility unchanged unless separately approved.

## Suggested acceptance criteria

- No hidden, fixed genre quotas remain in personal recommendations unless documented as an explicit product policy.
- Candidate query selection is influenced by recent listening and library context, but retains bounded exploration.
- Controlled different-listening-profile tests demonstrate ranking/query changes without relying on live provider APIs.
- Identical fixtures and deterministic random inputs produce repeatable results.
- Missing genre metadata or provider failures degrade safely and do not cause popular/fixed-seed candidates to dominate by accident.
- Ownership and release eligibility regression tests remain passing.
- Any cache TTL changes are justified by measured impact and provider limits, not shortened indiscriminately.

## Out of scope for that session unless evidence warrants it

- Rewriting the whole recommendation engine.
- Broad modularization after the modularization roadmap has been closed.
- Shortening every cache duration without measuring its effect.
- Removing legitimate eligibility and ownership safety rules.
- Publishing or deploying an image; publishing remains paused unless separately authorized.
