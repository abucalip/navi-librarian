# Recommendation engine improvement roadmap

Last reviewed: 2026-10-20. This is the active plan only; historical measurements, completed changes, and superseded task orderings are in [the archive](RECOMMENDATION_ENGINE_IMPROVEMENTS_ARCHIVE.md). GitHub `main` is authoritative. Publishing and deployment remain paused.

## Finding — cold-start supply gain in the final list (2026-10-20, measured; merged as `aedc34e44034a04bb20c177458f9c8b73b12900f`, PR #474)

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

## Finding — steady-state (warm) final list (2026-10-20, measured; PR pending)

Offline trace: a warm `refresh_personal` finds a stored list, so `_cold_start` is off and the batch path is not used. Differences from cold: cooldown reads `recommendation_history` (written only when a list is stored; max 25% score penalty, 7-day half-life), the feedback signal applies, and cached metadata is reused. The 100-per-run uncached MusicBrainz budget applies again, and batch hits are not written to the metadata cache, so a cold build's 200 batch-resolved recordings are not cached for the next run.

Owner-approved live run (the owner said the agent may do it), one fresh data dir, slskd off, aggregate only, count 10, cold build then two warm refreshes back to back, data dir deleted. One sample; interpret as indicative.

| | cold | warm 1 | warm 2 |
| --- | --- | --- | --- |
| Albums / distinct artists / top-2 share | 10 / 10 / 20% | 10 / 10 / 20% | 10 / 10 / 20% |
| Overlap with previous list | n/a | 4 of 10 | 3 of 10 |
| Category counts (adj / cross / adv) | 4 / 3 / 3 | 4 / 3 / 3 | 4 / 3 / 3 |
| Pool (candidates / unowned unique) | 74 / 55 | 52 / 42 | 70 / not recorded |
| Unowned unique by source (CF / profile / exploration) | 17 / 30 / 8 | 4 / 30 / 8 | 14 / 30 / 8 |
| Recent-genre family cap rejections | 39 | 24 | 37 |
| Family cap relaxation attempts | 10 | 4 | 8 |
| Wall time | 126 s | 230 s | 202 s |
| Provider calls | LB CF 2, MB 86 (batch), Last.fm 40 | LB CF 2, MB recording lookups 117, Last.fm 22 | LB CF 2, MB recording lookups 113 |

MusicBrainz recording-lookup counts include retries (up to 3 attempts per recording); resolutions stayed within the 100 budget. Of 30 history rows across the three lists, 21 are distinct identities.

Result: spread is unchanged on warm refreshes (10 distinct artists, 20% top-2 share, quotas met every time). Repeats between consecutive lists were 3 to 4 of 10 even with cooldown history present. The stage that most plausibly causes repeats is the supply, not the penalty: the 30 profile-tag and 8 exploration-tag candidates were identical in count in all three runs, and the 25% cooldown cap is a soft multiplier that only reorders candidates with close scores. The recent-genre family cap rejected 24 to 39 candidates per run, was relaxed (4 to 10 attempts) and never prevented a full list. CF supply varied (4 to 17 unowned), consistent with the budget-bound warm resolution path, not with ranking.

Limits: one sample; runs were back to back, so cooldown decay was negligible and history held at most two prior lists; the harness did not capture the source mix of the final list (its source field was misread), so that row is missing; the budget/caching explanation for warm CF supply is from code reading, not a cache-hit counter.

Decision: **do not reopen 1.2, 3.1 or 3.2** on this evidence; no code change. Risk named: if repeat rate matters, the lever is CF supply on warm runs (batch hits are not cached, so warm runs re-spend the 100 budget). Caching batch hits or a warm batch path would change call patterns and needs owner approval. A follow-up measurement would need a cache-hit counter.

### Verification of caching + warm batch path (2026-10-20, PR #476 branch; one sample, owner-approved)

Same harness as the warm finding (count 10, fresh data dir, slskd off, aggregate only, cold then two warm refreshes, data dir deleted). Final-list source mix is captured this time.

| | cold | warm 1 | warm 2 |
| --- | --- | --- | --- |
| Albums / distinct artists / top-2 share | 10 / 10 / 20% | 10 / 10 / 20% | 10 / 10 / 20% |
| Overlap with previous list | n/a | 5 of 10 | 5 of 10 |
| Final items: CF / tag search | 4 / 6 | 4 / 6 | 4 / 6 |
| Unowned CF candidates | 17 | 17 | 17 |
| Wall time | 123 s | 32 s | 3 s |
| MusicBrainz calls | 78 | 10 | 0 |
| Family cap rejections | 38 | 38 | 37 |

Result: warm CF supply now matches cold (17, was 4 and 14), warm time fell from 202 to 230 s down to 32 s and then 3 s, and warm 2 made no MusicBrainz or Last.fm calls (ListenBrainz CF requests unchanged at 2). Spread is unchanged. Overlap with the previous list rose to 5 of 10 because supply is now stable run to run, so the cooldown (max 25%, soft) is the only repeat damper; this is the number to watch. Limits: one sample, back-to-back runs, so the near-zero warm 2 reflects a fully warm cache and the profile-tag lane also hit cache. Whether 5 of 10 repeats is acceptable is a product call; do not tune cooldown (3.2) without a longer-interval measurement.

## Remaining work, in dependency order

### P0 — Candidate supply → final-list verification
- Done: cold and warm candidate supply and final-list effects are measured (see findings above). Next: obtain longer-interval repeat-rate evidence before deciding whether cooldown needs calibration. Keep the 100-per-run MusicBrainz budget and current ListenBrainz request count unchanged unless the owner explicitly approves otherwise.
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

- ListenBrainz CF is the primary candidate source; MusicBrainz resolves recording metadata. A cold-start batch path is enabled for first builds and covers all uncached CF recordings in batches. Batch hits do not spend the 100-call MusicBrainz budget; batch misses remain bounded by it. Since 2026-10-21 (owner-approved) steady-state builds also use the batch path (`WARM_BATCH_ENABLED`), and batch results are cached under `mb:recording_batch:<mbid>` (never the full-lookup key, because batch data lacks secondary release types). Live effect: see the verification note under the warm finding.
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
