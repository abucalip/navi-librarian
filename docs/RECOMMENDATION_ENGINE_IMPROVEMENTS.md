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

## Finding — steady-state (warm) final list (2026-10-20, measured; PR #475 merged)

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

Decision at the time: **do not reopen 1.2, 3.1 or 3.2** on this evidence. The owner subsequently approved warm batch resolution and separate-key caching in PR #476; see the verification immediately below. Next: obtain longer-interval repeat-rate evidence before considering cooldown calibration.

### Verification of caching + warm batch path (2026-10-20, PR #476 merged; one sample, owner-approved)

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

## Finding — repeat rate at simulated intervals (2026-10-20, measured; one sample)

Cold build plus five warm refreshes with history shifted back 0, 1, 3, 7 and 14 days (disposable database, slskd off, aggregate only, deleted). Full tables and the score-gap statistics are in `docs/REPEAT_RATE_MEASUREMENT_2026-10-20.md`.

Result: overlap with the previous list was 4, 5, 5, 6, 6 of 10 and with all earlier lists 4, 5, 8, 9, 9; spread unchanged (10 distinct artists, 20% top-2 share). The cooldown penalised 10 to 24 of 55 candidates (max penalty 0.188) and swapped at most 1 of the top 10. Score gaps: 2.76% at the rank 10/11 cut-off, 25.29% across ranks 1 to 10, 2.57% median adjacent gap. Warm refreshes after the cache fills take 2.6 to 3.3 s with 2 ListenBrainz requests and no other provider calls.

Limits: one sample; simulated time does not change ListenBrainz CF or the listening profile, so this isolates the cooldown, not supply drift.

Decision: **do not reopen 3.2.** Repeats come from a small, stable pool; the cap moves at most one slot and a stronger cooldown would trade relevance for freshness. More supply breadth would need owner approval.

## Finding — CF supply is limited by pages read, not the lookup budget (2026-10-20, measured; one sample)

One live run (cold plus two warm). All 200 fetched CF recordings resolved every time; uncached per-recording MusicBrainz lookups were 0, so the 100-per-run budget never bound. The limit is `CF_MAX_PAGES = 2` × 100 of a 1,000-recording pool: 36 CF albums from 15 artists (top-2 share 47.5%), identical across runs. Details and an approval request for 3 or 4 pages: `docs/CF_PAGES_PROPOSAL_2026-10-20.md`. This corrects the earlier idea of spending spare budget on the already-fetched pool: there is no unresolved remainder. No code change; deeper reading needs owner approval.

## Finding — `CF_MAX_PAGES = 4` re-measured after the batch fix (2026-10-21, measured; one sample each; decision: keep 2)

Owner-approved live runs on a fresh data directory, slskd off, aggregate only, directory deleted. Same harness for both configurations; the 2-page baseline ran from `main` at `83b2583`.

| Config | Run | Seconds | CF recordings resolved / failed | Uncached MB lookups | CF albums / artists | Top-2 share |
| --- | --- | --- | --- | --- | --- | --- |
| 2 pages | cold | 141.0 | 200 / 0 | 0 | 36 / 15 | 47.5% |
| 2 pages | warm 1, warm 2 | 2.4, 2.6 | 200 / 0 | 0 | 36 / 15 | 47.5% |
| 4 pages | cold | 255.1 | 97 / 3 | 100 (budget reached, 300 skipped) | 14 / 4 | 54.6% |
| 4 pages | warm 1 | 285.9 | 138 / 1 | 100 (203 skipped) | 33 / 12 | 44.2% |
| 4 pages | warm 2 | 56.6 | 276 / 0 | 0 | 77 / 42 | 26.4% |

A second 4-page cold run with the batch diagnostic took 316.1 s (14 albums, 4 artists). Its request log: four `recording_batch` calls returned 200 (0.4 to 1.1 s each); both `release_group` calls returned 502 with an HTML body. With #479 the failure no longer discards the batch, but recordings in a failed release-group chunk fall back to per-recording lookups, which spend the 100-per-run budget. At 2 pages the same endpoint path resolved all 200 recordings with no lookups.

The cold run did not meet the success criterion (about 106 to 123 s with the batch path intact). The diversity gain (77 albums, 42 artists, top-2 26.4%) appears only after the cache fills. The cause of the 502s (request size, endpoint, or transient) is not established. Not measured: overlap with the previous list; `musicbrainz.recording_lookup` counts of 111 to 113 in the 4-page cold and warm 1 runs exceed the 100 budget, unexplained; `lastfm.api` calls (13 to 40) appeared in several runs, unexplained.

Decision: **keep `CF_MAX_PAGES = 2`; no code change.** Revisit when the release-group 502s are understood. Single samples; no recommendation-quality claim.

## Finding — tag-lane rotation measured (2026-10-21, one sample per arm; decision: keep off)

An experimental patch (not merged; reviewed on PR #483 and removed) rotated the non-anchor profile tags (top 3 stayed) and the exploration tags through the next-ranked window behind a default-off flag; query counts unchanged, deterministic per counter. Owner-approved live run, cold plus three warm, same harness for both arms, aggregate only, disposable data dirs deleted. Counter = run index.

| | Off | On |
| --- | --- | --- |
| Overlap with previous list, warm1/2/3 (of 10) | 5 / 5 / 4 | 4 / 5 / 3 |
| Tag-lane candidates / artists, cold | 38 / 37 | 38 / 37 |
| Tag-lane candidates / artists, warm | 38 / 37 each run | 39/38, 32/32, 35/33 |
| MusicBrainz calls, cold | 72 | 74 |
| MusicBrainz calls, warm1/2/3 | 0 / 0 / 0 | 12 / 6 / 5 |
| Last.fm calls, warm1/2/3 | 0 / 0 / 0 | 2 / 1 / 0 |
| Wall time, cold | 168 s | 147 s |
| Wall time, warm1/2/3 | 2.8 / 4.3 / 3.6 s | 20.9 / 10.7 / 8.6 s |

Final mix stayed 4 CF / 6 tag in every run. Mean overlap 4.7 (off) vs 4.0 (on): within noise at three runs. Rotation did not widen tag supply, and newly sampled tag queries are uncached, so warm runs make provider calls the baseline does not (breaks "calls must not rise") and are 2-7x slower. Calls may fall once the rotation cycle is cached; not measured. Decision: keep off, and the code was not merged: no benefit was shown and nothing in the app supplied the counter. Reintroduce only if a future experiment shows a measurable benefit. Harness `run_tag_rotation.py` was test-only and never committed (adapted from `run_cf_budget.py`).

## Finding — read-only look at release-group 502s and the unexplained counts (2026-10-21, code reading and existing reports only; no live run)

**Request pattern (from `discovery_batch_metadata.py` and `_prefetch_batch_recordings`).** Recordings: one POST per 100 MBIDs to the ListenBrainz `metadata/recording/` endpoint (`BATCH_RECORDING_CHUNK = 100`), sent back to back with no spacing. Release groups: one GET per 100 release-group MBIDs to `metadata/release_group/`, with the MBIDs comma-joined in the query string (about 3.7 KB of MBIDs, about 3.9 KB once commas are percent-encoded), also with no spacing. Failed chunk: one retry after a 2 s sleep (#479), then its recordings fall back. Only the number of chunks changes with pages: at most 2 recording and 2 release-group requests at 2 pages, at most 4 and 4 at 4 pages. **Each request is the same size at both settings**, so request size per call does not explain a failure that appears only at 4 pages. The 4-page diag run logged two `release_group` calls, both 502 with an HTML body (an HTML 502 is typical of a gateway or proxy in front of the API, not the application's JSON error).

**What is known:** the endpoint and method are the same at 2 and 4 pages; per-request URL size is the same; the 2-page path resolved all 200 recordings with no lookups (single sample); both release-group calls in the 4-page diag run returned 502; the retry gap is only 2 s.

**What is not known:** whether the logged calls include the retry (if they do, the 502 hit the first request and its retry); whether the 502 depends on the number of release-group requests in a burst, on server load at the time, or on response time (a heavier cold lookup of up to 100 uncached groups); and whether it recurs at all, since the report holds one failing run, with the first 4-page cold run not logging individual calls. The aggregate reports contain no per-request size, status or latency table beyond that, so none could be tabulated offline.

**Hypotheses after the live run:** (1) content-dependent failure: some MBID in the 83 makes the endpoint or proxy return a fast HTML 502 (explains why it fails identically twice and why a 400-recording set fails while a 200-recording subset does not); (2) a short outage or throttle window longer than the 2 s retry gap; (3) a size or burst limit (ruled out by the live run: 83 MBIDs, first request, 0.5 s).

**Live diagnostic (owner-approved, one cold 4-page run, test-only harness not committed, aggregate only, disposable data dir deleted).** Per-attempt log: four `recording_batch` POSTs of 100 MBIDs each returned 200 `application/json` in 0.5 to 1.1 s. Then exactly **one** `release_group` chunk was built, with **83** unique release-group MBIDs (400 recordings collapse to 83 groups), not 100. Its first attempt returned 502 `text/html` in 0.5 s, and the retry (after the 2 s sleep) returned 502 `text/html` in 0.7 s. So the earlier "both release_group calls" were the attempt and its retry, not two chunks. Run: 363.6 s, 98 of 100 budgeted recordings resolved, 300 skipped, 14 CF albums from 4 artists; `recording_lookup` 105 for 100 resolutions (5 retried attempts), `lastfm.api` 40, `musicbrainz.bounded_get` 62.

What this changes: the 502 is **not** a size limit (83 is smaller than the 100-MBID requests that worked at 2 pages), **not** a burst or second-request effect (it was the first and only release-group request), and **not** a slow timeout (it failed in about 0.5 s, twice, with an HTML body, i.e. an intermediary answering before the application). It is consistent with a deterministic, content-dependent failure of this particular request (for example one release-group MBID the endpoint or its proxy chokes on) or with a short outage window longer than 2 s. One sample cannot separate the two.

**Unexplained counts, now explained from code (no run needed).**
- `musicbrainz.recording_lookup` 111 to 113 against the 100 budget: `record_provider_call("musicbrainz", "recording_lookup")` sits inside the per-attempt retry loop (up to 3 attempts on 429/500/502/503/504), while the budget (`resolution_calls >= CF_MAX_UNCACHED_RESOLUTIONS`) is incremented once per recording. So the budget caps recordings resolved (100), not HTTP requests; the counter counts requests. The 11 to 13 extra are retried attempts. Real MusicBrainz traffic can therefore reach up to 300 requests per run in the worst case, and the 1.1 s spacing is applied per recording, not per retry (retries sleep 2 s and 4 s).
- `lastfm.api` 13 to 40: `apply_lastfm_popularity_bonus` queries `album.getInfo` for the top 40 candidates by score (30-day cache). A cold run with an API key therefore makes up to 40 calls (13 means 27 were cached); warm runs make none, matching the 0 in the rotation experiment. The tag-rotation cold runs' 40 calls fit the same cap. This path is independent of CF paging.

**Smallest candidate fixes, with request-pattern impact (none implemented; each needs owner approval).**
1. Instrumentation only: record per-request status, latency and attempt number for release-group calls in the aggregate diagnostics. No added requests.
2. Count retries separately (`recording_lookup_retry`) so the counter matches the budget. No request change.
3. Space release-group chunks (for example 1 s) and/or lengthen the retry gap. No added requests, slightly longer runs.
4. Smaller release-group chunks (for example 50). More requests: breaks the no-added-requests rule unless offset elsewhere.

**Recommended next step:** do 1 and 2 (no request-pattern impact). Then, with owner approval, test hypothesis (1) by splitting the same 83 MBIDs (bisection, about 7 requests) or re-sending the identical request after a pause; that tells content from outage. Do not touch chunk size or spacing before that. Do not reopen `CF_MAX_PAGES = 4` until the 502 cause is shown.

## Remaining work, in dependency order

### P0 — Candidate supply → final-list verification
- Done: cold and warm candidate supply, final-list effects, longer-interval repeat rate (no reopening of 3.2) and the `CF_MAX_PAGES = 4` re-measurement (kept at 2; PR #482, merge `c02e4966c3835f893f27a09bef0b1172b8578d66`) are measured. Tag-lane rotation was measured and not adopted (see its finding). Keep the 100-per-run MusicBrainz budget and current ListenBrainz request count unchanged unless the owner explicitly approves otherwise.
- Open question from the 4-page run: why release-group requests still return 502 after #479's retry. Read-only look done (see its finding): per-request size is the same at 2 and 4 pages, cause still unestablished; next step is per-request diagnostics, then an owner-approved live diag run. Any change to request pattern needs owner approval.
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
- Batch release-group lookups are resilient (PR #479, merge `4cf66322866c5377fec612a297db05922d7a8e11`): a failed chunk is retried once; if it still fails only its recordings fall back to per-recording lookups and the other chunks stay batch-resolved and cached. Found live at 400 CF recordings (a 502 HTML response discarded all four successful recording batches). Not yet confirmed live at 4 pages; `CF_MAX_PAGES` is still 2.
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
