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

## Finding — batched genre lookup, endpoint limit and 4-page re-measurement (2026-10-21; owner-approved live runs, test-only patches not committed, aggregate only, disposable data dirs deleted)

**ListenBrainz request rule (owner, revised 2026-10-21).** "No added ListenBrainz requests per run" stands only where the requests add run time. Batch lookups that work quickly may add requests when they reduce total time. Each such change still reports request counts and wall time before and after.

**Context.** After the release-group chunk cap (PRs #484 and #485: the release-group endpoint passes 80 MBIDs per GET and fails from 81; chunk set to 50), a cold 4-page run still took 207 to 319 s. The profile put about 111 to 121 s of it in `genre_lookup` (up to 75 artists, one uncached MusicBrainz request each at 1.1 s spacing plus about 1.2 s response time) and about 37 to 39 s in `genre_prefetch`.

**Batch genre lookup.** The ListenBrainz `metadata/artist/` endpoint (`inc=tag`) returns tags for many artists per GET. Keeping tags that carry a `genre_mbid` gave exactly the MusicBrainz genre set for 5 of 5 sampled artists. Patch (test-only): before the prefetch and before the genre stage, fetch uncached artists in one chunk and write `mb:artist-genres:<id>`; the existing per-artist MusicBrainz loop remains as the fallback for artists the batch misses.

**Endpoint size limit measured.** Requests of 25, 40, 50, 60, 70, 80 and 96 artist MBIDs all returned 200 `application/json` with every artist present (response 47 KB at 25, 173 KB at 96; 0.5 to 1.1 s). **No failing size was found up to 96, the most distinct artists the 400-recording CF set offered.** The limit is therefore above 96 and not located; the app needs at most about 75 artists per call (60 candidate artists plus recents, deduplicated), so one chunk of 75 is used, 22% under the largest size verified. This is a different endpoint from the release-group one, which fails at 81.

**Options compared (cold 4-page runs, one run per arm unless noted; same CF supply in every arm: 79 albums from 42 artists).**

| Arm | Cold time | MusicBrainz requests | `genre_lookup` |
| --- | --- | --- | --- |
| Baseline | 212.2 s (a second baseline: 93.5 s) | 81 (73) | 111.3 s (43.1 s) |
| Batch (25 per request) | 36.5 s | 2 | 1.0 s |
| Top-20 candidate artists only | 75.3 s, 78.5 s | 52 | 15.7 s |
| Cap of 30 artists | 112.7 s | 53 | 37.4 s |

Top-20 and cap-30 save time by giving fewer artists a genre (less scoring data). Batch removes the time without removing data. Final-list overlap cannot compare arms: two identical baseline runs overlapped 2 of 10, arms overlapped 3 to 7 of 10, so run-to-run noise exceeds any arm effect. The baseline time itself varies 93 to 319 s between runs (MusicBrainz response time).

**4 pages end to end with the batch patch (chunk 75, release-group chunk 50, cold then two warm runs, one session).**

| Run | Wall time | CF albums / artists | MusicBrainz requests | Last.fm calls | `genre_lookup` | `lastfm_album_popularity` |
| --- | --- | --- | --- | --- | --- | --- |
| Cold | 39.6 s | 79 / 42 | 3 | 40 | 0.7 s | 27.5 s |
| Warm 1 | 16.5 s | 79 / 42 | 8 | 0 | 0.5 s | 0.02 s |
| Warm 2 | 4.2 s | 79 / 42 | 1 | 0 | 0.04 s | 0.03 s |

For comparison, the 2-page baseline cold run was 141.0 s and the unpatched 4-page cold runs were 207 to 363 s. ListenBrainz requests in the cold run: 4 CF pages, 4 recording batches, 2 release-group GETs and 1 genre-batch GET for the prefetch plus 1 for the genre stage, plus the recent-listens calls (about 15 in all against 12 before). The remaining cold time is mostly the 40 Last.fm popularity calls (27.5 s, 30-day cache) and the tag lane. Single sample per row; no recommendation-quality claim. With the rule revised above, the added ListenBrainz GETs are allowed because they cut cold time by about 80%. **Not implemented in code**; the roadmap item below tracks it. `CF_MAX_PAGES` stays 2 until the owner decides after a code-level measurement.
## Finding — read-only look at release-group 502s and the unexplained counts (2026-10-21, code reading and existing reports only; no live run)

**Request pattern (from `discovery_batch_metadata.py` and `_prefetch_batch_recordings`).** Recordings: one POST per 100 MBIDs to the ListenBrainz `metadata/recording/` endpoint (`BATCH_RECORDING_CHUNK = 100`), sent back to back with no spacing. Release groups: one GET per 100 release-group MBIDs to `metadata/release_group/`, with the MBIDs comma-joined in the query string (about 3.7 KB of MBIDs, about 3.9 KB once commas are percent-encoded), also with no spacing. Failed chunk: one retry after a 2 s sleep (#479), then its recordings fall back. Only the number of chunks changes with pages: at most 2 recording and 2 release-group requests at 2 pages, at most 4 and 4 at 4 pages. **Each request is the same size at both settings**, so request size per call does not explain a failure that appears only at 4 pages. The 4-page diag run logged two `release_group` calls, both 502 with an HTML body (an HTML 502 is typical of a gateway or proxy in front of the API, not the application's JSON error).

**What is known:** the endpoint and method are the same at 2 and 4 pages; per-request URL size is the same; the 2-page path resolved all 200 recordings with no lookups (single sample); both release-group calls in the 4-page diag run returned 502; the retry gap is only 2 s.

**What is not known:** whether the logged calls include the retry (if they do, the 502 hit the first request and its retry); whether the 502 depends on the number of release-group requests in a burst, on server load at the time, or on response time (a heavier cold lookup of up to 100 uncached groups); and whether it recurs at all, since the report holds one failing run, with the first 4-page cold run not logging individual calls. The aggregate reports contain no per-request size, status or latency table beyond that, so none could be tabulated offline.

**Cause (established by bisection and threshold search):** request size. A GET with 83 MBIDs is rejected with a fast HTML 502 every time; 81 drops the connection; 80 and fewer pass. A single poison MBID and a transient outage are ruled out. The limit sits at 80/81 MBIDs; whether it is on the URL or the response is not separated.

**Live diagnostic (owner-approved, one cold 4-page run, test-only harness not committed, aggregate only, disposable data dir deleted).** Per-attempt log: four `recording_batch` POSTs of 100 MBIDs each returned 200 `application/json` in 0.5 to 1.1 s. Then exactly **one** `release_group` chunk was built, with **83** unique release-group MBIDs (400 recordings collapse to 83 groups), not 100. Its first attempt returned 502 `text/html` in 0.5 s, and the retry (after the 2 s sleep) returned 502 `text/html` in 0.7 s. So the earlier "both release_group calls" were the attempt and its retry, not two chunks. Run: 363.6 s, 98 of 100 budgeted recordings resolved, 300 skipped, 14 CF albums from 4 artists; `recording_lookup` 105 for 100 resolutions (5 retried attempts), `lastfm.api` 40, `musicbrainz.bounded_get` 62.

What this showed (superseded in part by the bisection below, which found a size dependence): the 502 is **not** a burst or second-request effect (it was the first and only release-group request), and **not** a slow timeout (it failed in about 0.5 s, twice, with an HTML body, i.e. an intermediary answering before the application). It is consistent with a deterministic, content-dependent failure of this particular request (for example one release-group MBID the endpoint or its proxy chokes on) or with a short outage window longer than 2 s. One sample cannot separate the two.

**Bisection (owner-approved, test-only harness, aggregate only; it also re-sent 4 CF page requests and 4 recording batches to rebuild the same 83-group set).** The identical 83-MBID request returned 502 `text/html` (0.5 s) again, and again after a 3 s pause: **3 of 3 failures, so it is reproducible, not transient.** Splitting it into 41 and 42 MBIDs returned 200 `application/json` for both (0.4 s each). No single-ID culprit exists (each half passes whole). **Conclusion: the failure depends on request size.** The release-group endpoint (or an intermediary) rejects a GET with 83 comma-joined MBIDs (about 3.1 KB of MBIDs, about 3.3 KB URL-encoded) and accepts 41 to 42. The threshold was then narrowed to 80 passing / 81 failing (next paragraph). This corrects the earlier statement that a size limit was ruled out: the "100-MBID requests succeeded at 2 pages" premise was never observed (a 2-page run has at most 200 recordings and probably well under 83 distinct release groups; its count was not logged). The retry cannot help a deterministic size rejection.

**Threshold search (owner-approved, test-only harness, aggregate only; each of the two runs re-sent 4 CF pages and 4 recording batches to rebuild the 83-group set).** Prefixes of the same list: 62, 72, 77 and 80 MBIDs returned 200 `application/json` (0.4 to 0.6 s). **81 MBIDs failed** with a dropped connection before the body finished (`RemoteProtocolError`, "incomplete chunked read", 0.4 s), and 83 MBIDs failed with an HTML 502. A tail slice of 80 passed and a slice of 81 failed again, so the limit is the **count (equivalently length) of the request, not which IDs it carries: 80 passes, 81 fails.** 80 MBIDs is about 3.0 KB of MBIDs joined by commas; whether the limit is on the request URL or on the response size was not separated (both scale with count), and the endpoint or intermediary behind it is not identified. The two failure modes (dropped connection at 81, HTML 502 at 83) share the same cliff. Conclusion: the current chunk of 100 is above the limit, so any run with more than 80 distinct release groups hits it; this happens at 4 pages (83 groups) and is likely rare at 2 pages (not logged).

**Unexplained counts, now explained from code (no run needed).**
- `musicbrainz.recording_lookup` 111 to 113 against the 100 budget: `record_provider_call("musicbrainz", "recording_lookup")` sits inside the per-attempt retry loop (up to 3 attempts on 429/500/502/503/504), while the budget (`resolution_calls >= CF_MAX_UNCACHED_RESOLUTIONS`) is incremented once per recording. So the budget caps recordings resolved (100), not HTTP requests; the counter counts requests. The 11 to 13 extra are retried attempts. Real MusicBrainz traffic can therefore reach up to 300 requests per run in the worst case, and the 1.1 s spacing is applied per recording, not per retry (retries sleep 2 s and 4 s).
- `lastfm.api` 13 to 40: `apply_lastfm_popularity_bonus` queries `album.getInfo` for the top 40 candidates by score (30-day cache). A cold run with an API key therefore makes up to 40 calls (13 means 27 were cached); warm runs make none, matching the 0 in the rotation experiment. The tag-rotation cold runs' 40 calls fit the same cap. This path is independent of CF paging.

**Smallest candidate fixes, with request-pattern impact (none implemented; each needs owner approval).**
1. Instrumentation only: record per-request status, latency and attempt number for release-group calls in the aggregate diagnostics. No added requests.
2. Count retries separately (`recording_lookup_retry`) so the counter matches the budget. No request change.
3. Space release-group chunks (for example 1 s) and/or lengthen the retry gap. No added requests, slightly longer runs.
4. Smaller release-group chunks (50, under the measured 80/81 cliff). More requests (2 instead of 1 at 4 pages; no change when a run has 50 or fewer groups): breaks the no-added-requests rule unless the owner approves; it likely removes the cold-run fallbacks that cost 100+ s.

**Recommended next step:** make the release-group chunk size smaller than the failing size (candidate: 50, a 37% margin under the 80 that passed; 40 is the more conservative option). Impact: release-group requests rise from ceil(groups/100) to ceil(groups/50), that is 2 requests for 83 groups (3 with 40), and fewer 502-driven per-recording fallbacks (each fallback costs 1.1 s plus a lookup). That is an added-request change, so it needs owner approval; it should be paired with the two no-impact instrumentation fixes. Then re-measure `CF_MAX_PAGES = 4` cold time. Do not reopen `CF_MAX_PAGES = 4` until the 502 cause is shown.

## Remaining work, in dependency order

### P0 — Candidate supply → final-list verification
- Done: cold and warm candidate supply, final-list effects, longer-interval repeat rate (no reopening of 3.2) and the `CF_MAX_PAGES = 4` re-measurement (kept at 2; PR #482, merge `c02e4966c3835f893f27a09bef0b1172b8578d66`) are measured. Tag-lane rotation was measured and not adopted (see its finding). Keep the 100-per-run MusicBrainz budget unchanged unless the owner explicitly approves otherwise. The ListenBrainz request count may rise only when the added requests save run time (owner rule, revised 2026-10-21; see "ListenBrainz request rule" below).
- Release-group 502s: cause found (request size: 80 MBIDs pass, 81 fail); fixed by `RELEASE_GROUP_CHUNK = 50` (see the findings above and the PROJECT_LOG entry). Remaining 4-page cold time is dominated by per-artist genre lookups (P0b below).
- Do not tune ranking weights to compensate for an unmeasured supply bottleneck.

### P0b — Batched genre lookup (PR #487 merged)
- **Result:** batched `metadata/artist/` genre lookup is implemented in `discovery_batch_metadata.py`, chunks of 75, populating the existing 90-day cache and retaining the per-artist MusicBrainz fallback. The single harness sample improved cold 4-page time from 207.6 s to 51.9 s with the same 79 albums / 42 artists; details and limitations are recorded in `PROJECT_LOG.md`.
- **Follow-up complete in reconciled PR #489 (original PR #488):** the owner-approved `CF_MAX_PAGES` increase to 4 was measured on the batched code and merged. Three pages yielded 55 albums / 24 artists (41.5 s cold); four pages yielded 79 albums / 42 artists (40.9 s cold). Single samples only; not a recommendation-quality claim.

### P0c — Test batch lookups for Last.fm (added 2026-10-21)
- After genre lookups are batched, the largest remaining cold-run cost at 4 pages is the Last.fm popularity pass: `apply_lastfm_popularity_bonus` makes up to 40 sequential `album.getInfo` calls (30-day cache; 27.5 s of a 39.6 s cold run, 0.5 to 0.7 s each, 0.2 s pacing between calls). Warm runs make none.
- Test, read-only first, whether this cost can fall: (a) whether any Last.fm API method returns album statistics for several albums in one request (none is known; `album.getInfo` takes one artist and album, so check the documentation before assuming a batch exists); (b) if there is no batch path, whether the same 40 calls issued with bounded concurrency (for example 4 at a time) cut wall time without breaching Last.fm's rate guidance, which changes the request pattern; (c) whether the ListenBrainz popularity or listen-count endpoints can replace some of the Last.fm calls (the batch recording and artist endpoints are already in use).
- Measure cold time and request counts before and after, the same way as P0b, and report them. Any change to the number or pacing of Last.fm calls needs owner approval, and Last.fm as a ranking source is otherwise parked by the owner.

#### P0c implementation (2026-10-21, owner-approved; merged in PR #490)
- The ranking pass no longer calls Last.fm `album.getInfo`. Candidates carry `release_group_mbid` (CF path and tag lane). `listenbrainz_popularity.py` sends the top 40 candidates' release groups in one `POST /1/popularity/release-group` (chunks of 50, cached 30 days under `lb:popularity:release-group:<mbid>`, nulls skipped, best-effort). Counts feed the existing fields: `total_user_count` as `lastfm_listeners`, `total_listen_count` as `lastfm_playcount`, so the bounded bonus formula and payload keys are unchanged (renaming the keys is a separate change). Last.fm tags are no longer attached to candidates, so the recent-profile family adjustment from those tags is skipped (the genre-based one remains).
- **Measured** (owner-approved, one cold 4-page run plus two warm, aggregate only, disposable data dir deleted, single sample): cold 23.6 s, warm 5.3 s and 7.8 s; 79 CF albums / 42 artists, 4 CF GETs, 2 artist-batch GETs, 9 MusicBrainz requests cold. **1 popularity POST** (40 release groups, 200 in 0.2 s) returned counts for **40 of 40**; warm runs made 0 popularity requests. Before (P0b/#489 samples, same harness): cold 40.9 s and 51.9 s with 40 Last.fm GETs (`lastfm_album_popularity` 19 to 25 s). The disposable data dir has no Last.fm key, so the before figures are the earlier recorded samples, not a same-day control. The 40-group POST and the absent `inc` field worked, so the open question is only the maximum batch size (40 is under any plausible cap; 50 is the chunk). Remaining cold time is the tag lane (16.1 s) and CF fetch. ListenBrainz counts are smaller than Last.fm's (the bonus will be weaker; it is capped at 12% either way). Last.fm stays in use for classics and deep-dive pipelines.

#### Tag lane via ListenBrainz tag radio (2026-10-21; flagged, off by default; measured, not recommended as default)
- `LB_TAG_LANE_ENABLED = False` in `discovery_candidate_gathering.py`; `discovery_lb_tag_lane.py`. Per tag: `GET /1/lb-radio/tags` (undocumented in the public API docs; 20 recordings per tag), then one shared pass through the existing batch recording and release-group endpoints (batch title-marker filter always on), same candidate shape, score, caps and source labels as the MusicBrainz lane; candidates are marked `listenbrainz_tag_radio`. No MusicBrainz request in the lane.
- Probe: 5 of 5 sampled tags returned 200 with 50 recordings; 100 recordings per tag resolved to 44 to 97 release groups, 79 to 94 percent Album type (18 to 88 artists).
- Live A/B (owner-approved, aggregate only, single samples, same harness, Last.fm key present in all arms): MusicBrainz lane cold 47.8 s, lane 18.6 s, 10 MusicBrainz requests; tag-radio lane cold 68.3 s (best of three runs), lane 35.1 s, 0 MusicBrainz requests in the lane; warm 3.4 to 5.4 s in both. Cause: `lb-radio/tags` latency is heavy-tailed, 0.2 s for most tags but 10 to 13 s for some on a first request (pop, electronic), and 8 sequential GETs took 31.6 s in-app.
- Failure seen once: at 50 recordings per tag (about 25 sequential ListenBrainz requests in a burst) the release-group endpoint returned HTTP 200 `text/html` (the known browser-verification page), the lane added nothing, and the per-artist MusicBrainz fallbacks pushed the cold run to 139 s. The count was reduced to 20 per tag; the page did not recur in the two later runs, but one sample cannot rule it out.
- **Parallel tag calls, first answer wins (owner-requested, 2026-10-21):** all uncached tag GETs run at once (up to 8 threads); stragglers are dropped 4 s after the first answer, and a late answer still writes its cache entry from the worker thread. Live (single samples): cold lane **6.7, 6.2 and 6.0 s** (was 35.1 s sequential and 18.6 s for the MusicBrainz lane), cold run 37.3 to 41.8 s with Last.fm still in the run (about 22 s of it). Dropped tags make the candidate set vary run to run (2 to 4 radio picks of 10 cold). Before the cache fix, dropped tags were re-requested on every warm run and warm runs took 14 to 18 s; the cache fix is unit-tested but its live warm effect is **not measured**.
- **Block:** after roughly ten full live runs in a short time, ListenBrainz began answering every request from this machine, including a plain tag GET, with HTTP 200 `text/html` "Verifying your browser" (the known browser-verification page). Live testing stopped; no workaround was attempted. Heavy repeated measurement can trigger it, so the parallel lane's burst (8 simultaneous GETs) should be treated as a risk until measured over time.
- Conclusion: the lane removes MusicBrainz requests but is slower cold on this profile, and it changes the pool (final picks differ). Not a default-on candidate. Options if pursued: per-tag timeout with skip, or parallel tag GETs (a request-pattern change that needs owner approval). Final-pick overlap and quality were not measured reliably.

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
- **More ListenBrainz pages, extra provider lookups, or a higher MusicBrainz budget:** require explicit owner approval. The approved CF page limit is now 4 (PR #489, reconciled from original PR #488); do not raise it further without a new decision.

## Current implementation facts

- ListenBrainz CF is the primary candidate source; MusicBrainz resolves recording metadata. A cold-start batch path is enabled for first builds and covers all uncached CF recordings in batches. Batch hits do not spend the 100-call MusicBrainz budget; batch misses remain bounded by it. Since 2026-10-21 (owner-approved) steady-state builds also use the batch path (`WARM_BATCH_ENABLED`), and batch results are cached under `mb:recording_batch:<mbid>` (never the full-lookup key, because batch data lacks secondary release types). Live effect: see the verification note under the warm finding.
- Fixed MusicBrainz tag searches are supplementary candidates. The batch metadata response lacks secondary release types, so its title-marker filter is only a partial safeguard and stays behind its default-off flag.
- Recommendation output is persisted. Candidate generation, scoring/allocation, eligibility, and snapshot freshness are separate layers; diagnose them separately.
- Batch release-group lookups are resilient (PR #479, merge `4cf66322866c5377fec612a297db05922d7a8e11`): a failed chunk is retried once; if it still fails only its recordings fall back to per-recording lookups and the other chunks stay batch-resolved and cached. Found live at 400 CF recordings (a 502 HTML response discarded all four successful recording batches). The four-page path was measured in the owner-approved reconciled PR #489 harness sample; timing and recommendation-quality conclusions remain limited by the single sample.
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
