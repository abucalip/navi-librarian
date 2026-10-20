# Recommendation engine improvement roadmap

Last reviewed: 2026-10-20. This is the active plan only; historical measurements, completed changes, and superseded task orderings are in [the archive](RECOMMENDATION_ENGINE_IMPROVEMENTS_ARCHIVE.md). GitHub `main` is authoritative. Publishing and deployment remain paused.

## Next task — measure the cold-start supply gain in the final list

**Priority: do this before reopening ranking/diversity work. No code or policy change until the measurement identifies a need.**

PR #471 removed the MusicBrainz-resolution budget charge for cold-start ListenBrainz batch hits. One owner-approved sample resolved 200/200 CF recordings across 15 artists (previous sample: 100/200 across 4 artists); runtime stayed at 117 seconds. The effect on the final recommendation list is **not measured**. There is no captured pre-change final-list baseline, so do not invent one.

1. **Offline trace first:** follow the first-build path from CF recordings through metadata resolution, release eligibility, ownership/deduplication, candidate gathering, artist limits, allocation, and final top 10. Use existing aggregate diagnostics and identify where the wider resolved pool may be reduced.
2. **Then request owner approval before any live run.** If approved: use a fresh disposable data directory, slskd off, aggregate-only output, and delete the directory afterwards. Capture final-list distinct artists and top-two share, `candidate_supply.stages`, final recommendation count, and `run_metrics` provider-call counts (wrap `record_recommendation_diagnostics` so the counters are actually captured). Do not include identities, listens, credentials, or provider URLs in repository evidence.
3. **Decide from evidence:** state whether the final-list spread improved and whether Phases 1.2, 3.1, or 3.2 should reopen. If no valid baseline exists, report the limitation; ask before running the pre-#471 revision.
4. Record only aggregate results, limits, and the resulting decision here and in `PROJECT_LOG.md`.

Handoff details and owner constraints: `CLAUDE_CLI.md`.

## Remaining work, in dependency order

### P0 — Candidate supply → final-list verification
- Complete the task above.
- Keep the 100-per-run MusicBrainz budget and current ListenBrainz request count unchanged unless the owner explicitly approves otherwise.
- Do not tune ranking weights to compensate for an unmeasured supply bottleneck.

### P1 — Reopen ranking work only if measurements justify it
- **Phase 1.2 — Familiarity/profile balance:** evaluate the current multiplicative score and the strong familiarity spread against deterministic fixtures; change weights only with comparative evidence.
- **Phase 3.1 — MMR-style re-ranking:** evaluate only if eligible candidate pools are large enough to reorder meaningfully; preserve relevance and eligibility.
- **Phase 3.2 — Cooldown calibration:** evaluate only after supply and shortlist behavior are understood.
- For any reopened phase, define a baseline, metrics, acceptance thresholds, and rollback/flag strategy before implementation.

### P2 — Explicit owner decisions / parked work
- **Default-on flags:** `CF_BATCH_RESOLUTION_ENABLED`, `BATCH_TITLE_FILTER_ENABLED`, genre circuit breaker, and tag-lane early stop remain off by default. Each affects output or call patterns; do not change defaults without an explicit decision and evidence.
- **CF freshness:** unknown whether ListenBrainz CF reflects all-time history. Any two-sided capture requires owner approval.
- **Diversity setting/UI:** paused. Do not build the Settings UI or tune the mapping until candidate supply supports meaningful cross-pool evaluation and the separate diversity roadmap gates are met.
- **Last.fm as a source:** parked. Do not start a quality test or combined path without a new decision.
- **More ListenBrainz pages, extra provider lookups, or a higher MusicBrainz budget:** require explicit owner approval.

## Current implementation facts

- ListenBrainz CF is the primary candidate source; MusicBrainz resolves recording metadata. A cold-start batch path is enabled for first builds and covers all uncached CF recordings in batches. Batch hits do not spend the 100-call MusicBrainz budget; batch misses remain bounded by it.
- Fixed MusicBrainz tag searches are supplementary candidates. The batch metadata response lacks secondary release types, so its title-marker filter is only a partial safeguard and stays behind its default-off flag.
- Recommendation output is persisted. Candidate generation, scoring/allocation, eligibility, and snapshot freshness are separate layers; diagnose them separately.
- Feedback-seed work and automatic refill/stale-while-revalidate are implemented. Roadmap 3.3 and 3.4 are complete.
- `LISTENBRAINZ_TOKEN` is supported through `compose.yaml`, `.env.example`, and deployment documentation, but the change is **not deployed**.
- Historical evidence is limited: live measurements are small samples; the final-list effect of the cold-start gain is unknown; available ListenBrainz history covers roughly two weeks.

## Goal and non-negotiable guardrails

Improve responsiveness to recent listening and library context while balancing relevance, novelty, and diversity. Do not assume the root cause before measuring it.

Preserve:
- Owned-album exclusion; reliable artist identity; compilation, remix, live, and other non-album eligibility safeguards.
- Duplicate suppression, safe acquisition behavior, persisted settings/lists, and existing web/API response contracts.
- Bounded provider calls, cache/rate-limit behavior, and graceful provider-failure paths.
- Deterministic fixture-based tests with no live-provider dependency for correctness.
- Aggregate-only repository diagnostics. Keep private captures, identities, raw listening history, credentials, and provider URLs out of GitHub.
- MCP remains retired as a supported interface. No UI work in backend PRs.
- Publishing and deployment remain paused until separately authorized.

No change may weaken ownership, duplicate-identity, or release-eligibility filtering to increase shortlist fill. Any live provider run needs owner approval. Follow `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, and the standing testing rule in `CLAUDE_CLI.md`: agents run focused tests and syntax checks only; the owner runs the full suite independently, and all four required workflows must pass on the exact final PR head.

## Evaluation and acceptance for behavior changes

Before changing ranking, candidate generation, or allocation:

1. Establish a deterministic baseline with fixed profile, library/ownership state, provider fixtures, ranking timestamp, and feedback/history.
2. Measure candidate counts by source and stage, eligible unique unowned albums and artists, final list size, repeat rate, artist/style spread, ranking/shortlist overlap, and score-component attribution as applicable.
3. For quality claims, use leakage-free chronological evaluation: build from listens through time T and evaluate unowned-artist hits during T to T+14 days. Report artist-level hit-rate@k and nDCG@k alongside novelty/diversity and eligibility counts. Treat small historical samples as relative evidence, not proof of satisfaction.
4. Add deterministic regression tests; keep identity-bearing fixtures private.
5. State limitations and a clear decision gate. Do not use one live sample to claim quality or causality.

## Reference map

- Current project state and single next action: `docs/PROJECT_STATUS.md`
- Immediate task handoff and owner constraints: `CLAUDE_CLI.md`
- Chronological PR and verification evidence: root `PROJECT_LOG.md`
- Product invariants: `docs/REQUIREMENTS.md`
- Verification gates: `docs/TEST_PLAN.md`
- Diversity calibration and rollout gates: `docs/DIVERSITY_SETTING_ROADMAP.md`
- Workflow and merge rules: `docs/DEVELOPMENT_WORKFLOW.md`
