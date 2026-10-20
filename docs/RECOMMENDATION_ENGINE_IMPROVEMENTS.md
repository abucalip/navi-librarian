# Recommendation engine improvement roadmap

Last reviewed: 2026-10-20. This is the active plan only; historical measurements, completed changes, and superseded task orderings are in [the archive](RECOMMENDATION_ENGINE_IMPROVEMENTS_ARCHIVE.md). GitHub `main` is authoritative. Publishing and deployment remain paused.

## Finding — cold-start supply gain in the final list (2026-10-20, measured)

Owner-approved live pair, `_cold_start=True`, count 10, fresh data dir, slskd off, aggregate only, data dirs deleted. "Before" is the parent of PR #471 (`961266d`), "after" is `main` at `7deaf46` (includes #471). One sample each; the tag lane and genre lookup vary run to run (MusicBrainz throttling), so treat differences as indicative.

| | before (#471 parent) | after (#471) |
| --- | --- | --- |
| Final list: albums / distinct artists / top-2 share | 10 / 10 / 20% | 10 / 10 / 20% |
| Final items by source | CF 3, profile tags 6, exploration tags 1 | CF 7, profile tags 3 |
| Pool: albums resolved (CF / tag lane) | 52 (14 / 38) | 46 (36 / 10) |
| Unowned unique candidates by source | CF 4, profile 30, exploration 8 | CF 17, profile 10 |
| Category counts (adj / cross / adv) | 4 / 3 / 3 | 4 / 3 / 3 |
| Allocator rejections | owned 7, family cap 24, quota 11 | owned 11, family cap 17, same-artist 6, quota 2 |
| Wall time | 170 s | 95 s |
| `run_metrics` provider calls | LB CF 2, MB 68, Last.fm 40 | LB CF 2, MB 57, Last.fm 40 |

Offline trace: the personal allocator takes at most one album per artist, so the final list is 10 distinct artists and a 20% top-2 share whenever at least 10 eligible artists exist. The CF-stage 47.5% top-2 share never carries into the final list. The category quotas (4/3/3) were met in both runs, so nothing unclassified was needed. Cooldown has no history on a first build and MMR is off at the default setting 0, so Phases 3.1 and 3.2 cannot respond to supply on this path.

Result: the gain is real in provenance, not in spread. CF now supplies 7 of 10 final albums (before 3) and the CF unowned pool grew 4 to 17, with distinct artists and category balance unchanged. The tag lane filled the gap before. Limits: the earlier pre-change tag-lane yield (38) versus after (10) differs by more than the CF change would explain, so the lane is the noisiest input; no pre-#471 final-list history existed before this run.

Decision: **do not reopen 1.2, 3.1 or 3.2.** The final spread is already at the allocator's ceiling, 3.1 and 3.2 are inert on a first build, and there is no measured defect to tune against. Risk named: the recent-genre family cap rejected 17 to 24 candidates per run; it is soft and relaxed in a later pass, and it filled the list both times, but it is the stage to look at first if warm-run spread ever drops. No code changed.

## Remaining work, in dependency order

### P0 — Candidate supply → final-list verification
- Done (see the finding above). Keep the 100-per-run MusicBrainz budget and current ListenBrainz request count unchanged unless the owner explicitly approves otherwise.
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
