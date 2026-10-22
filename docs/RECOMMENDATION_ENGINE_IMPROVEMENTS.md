# Recommendation engine — active decisions

This file contains only the remaining gates. Detailed experiments, completed work, historical proposals, and measurements are archived in [RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md](archive/recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md).

## Current gates

1. Repeat the ListenBrainz collaborative-filtering freshness capture after the imported listening history has been recomputed. This requires explicit owner approval before any live capture; the previous capture was inconclusive.
2. Only after freshness is understood, decide whether to seek approval for deeper CF pages. Current approved depth is four pages; do not increase it without a new decision.
3. Keep recommendation diversity UI/mapping paused until candidate supply supports meaningful cross-pool evaluation. See [the archived diversity roadmap](archive/parked/DIVERSITY_SETTING_ROADMAP.md).
4. Do not reopen ranking phases or alter provider request budgets without a deterministic baseline, relevant quality/supply metrics, regression tests, and explicit approval where required.

## Permanent guardrails

Preserve owned-album exclusion, artist identity, release eligibility, duplicate suppression, safe acquisition behavior, persisted settings, and web/API contracts. Keep provider calls bounded, retain graceful failure paths, and keep private listening captures, identities, credentials, and provider URLs out of GitHub.

See [ACTIVE_WORK.md](ACTIVE_WORK.md), [TEST_PLAN.md](TEST_PLAN.md), and [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) for current work and required process.
