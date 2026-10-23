# Recommendation engine — active decisions

This file contains only the remaining gates. Detailed experiments, completed work, historical proposals, and measurements are archived in [RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md](archive/recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md).

## Current gates

1. Repeat the ListenBrainz collaborative-filtering freshness capture after the imported listening history has been recomputed. This requires explicit owner approval before any live capture; the previous capture was inconclusive.
2. Deeper CF pages: freshness is understood (mixed; see `PROJECT_LOG.md`). Current approved depth is four pages; do not increase it without a new decision. New evidence: 8 pages helps only together with 120 genre-tag lookups and the opt-in family-coverage policy (unmerged), and 12 pages adds nothing over 8. See [engine2.md](engine2.md).
3. Keep recommendation diversity UI/mapping paused until candidate supply supports meaningful cross-pool evaluation. See [the archived diversity roadmap](archive/parked/DIVERSITY_SETTING_ROADMAP.md).
4. Engine 2 (multi-list lenses, obscurity, history windows) is the active direction: [engine2.md](engine2.md). Its Phase 1 is offline analysis and needs no ranking change.
5. Do not reopen ranking phases or alter provider request budgets without a deterministic baseline, relevant quality/supply metrics, regression tests, and explicit approval where required.

## Permanent guardrails

Preserve owned-album exclusion, artist identity, release eligibility, duplicate suppression, safe acquisition behavior, persisted settings, and web/API contracts. Keep provider calls bounded, retain graceful failure paths, and keep private listening captures, identities, credentials, and provider URLs out of GitHub.

See [ACTIVE_WORK.md](ACTIVE_WORK.md), [TEST_PLAN.md](TEST_PLAN.md), and [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) for current work and required process.
