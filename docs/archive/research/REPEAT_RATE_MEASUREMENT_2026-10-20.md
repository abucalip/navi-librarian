# Repeat rate at simulated intervals — measurement report (2026-10-20)

One owner-approved live run (cold build, then five warm refreshes). Aggregate numbers only: no titles, artists, identity hashes, URLs or credentials. Disposable data directory, slskd off, deleted afterwards. The driver is a test-only script kept outside the repo.

## Method and limits

- Between warm refreshes, `recommendation_history.generated_at` (and the stored list's timestamp) were shifted back by 0, 1, 3, 7 and 14 days in the disposable database. Cumulative shift before the last run: 25 days, inside the 30-day expiry.
- Simulated time does not change ListenBrainz CF or the listening profile. This isolates the cooldown, not supply drift.
- One sample, one library, count 10. Wall times of warm+0d reflect an empty metadata cache and are not comparable with later warm runs.
- "Top 10 swapped" compares the top 10 by score of ownership-clear candidates before and after the cooldown. The final list also passes the category allocator, so this is an upper bound on what the cooldown can change.

## Cooldown policy (from `recommendation_cooldown.py`)

Score is multiplied by `1 − penalty`. Each prior exposure adds `0.10 × (21 − rank)/20 × 2^(−age/7d)`; the total is capped at 0.25; entries older than 30 days are ignored.

Penalty from one exposure:

| Rank | now | 1 day | 3 days | 7 days | 14 days | 30 days |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.100 | 0.091 | 0.074 | 0.050 | 0.025 | 0.005 |
| 5 | 0.080 | 0.073 | 0.059 | 0.040 | 0.020 | 0.004 |
| 10 | 0.055 | 0.050 | 0.041 | 0.028 | 0.014 | 0.003 |

Several exposures: an album at rank 5 in 3 back-to-back lists reaches 0.24, in 4 lists the 0.25 cap. A penalty p can reorder two candidates only if their scores are within about p (relative).

## Measured results

| Run | Time | Overlap with previous list | Overlap with union of all earlier | Distinct artists / top-2 share | History rows read | Candidates penalised (of clear) | Max penalty | Median penalty (penalised) | Top 10 swapped by cooldown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cold | 106.5 s | n/a | n/a | 10 / 20% | 0 | 0 of 32 | 0 | n/a | 0 |
| warm +0d | 60.9 s | 4 of 10 | 4 | 10 / 20% | 10 | 10 of 55 | 0.100 | 0.077 | 0 |
| warm +1d | 2.9 s | 5 of 10 | 5 | 10 / 20% | 20 | 16 of 55 | 0.163 | 0.082 | 1 |
| warm +3d | 2.6 s | 5 of 10 | 8 | 10 / 20% | 30 | 21 of 55 | 0.188 | 0.064 | 1 |
| warm +7d | 2.6 s | 6 of 10 | 9 | 10 / 20% | 40 | 23 of 55 | 0.139 | 0.035 | 0 |
| warm +14d | 3.3 s | 6 of 10 | 9 | 10 / 20% | 50 | 24 of 55 | 0.057 | 0.012 | 0 |

Provider calls: cold = Last.fm 40, ListenBrainz CF 2, MusicBrainz 48; warm +0d = ListenBrainz CF 2, MusicBrainz 30; every later warm run = ListenBrainz CF 2, nothing else. No added requests per run.

## Score-gap statistics (ownership-clear pool, scores before cooldown)

| Pool | Relative gap rank 10 → 11 | Relative span rank 1 → 10 | Median adjacent relative gap, top 20 |
| --- | --- | --- | --- |
| cold: 32 candidates | 2.76% | 25.29% | 2.57% |
| every warm run: 55 candidates | 2.76% | 25.29% | 2.57% |

The pre-cooldown scores were identical in all five warm runs (same top-of-pool figures), confirming that supply is stable run to run and that only the cooldown differs between them.

## Reading

- The cap can change the top 10, but barely. The gap at the cut-off is 2.76%, so any penalty above that can swap rank 10 and 11, and the observed swaps were 0 or 1 of 10. The top ten spans a 25% score range, so a 25% penalty could in principle move an album most of the way out; no album reached that here (max 0.188).
- Overlap with the previous list rose from 4 to 6 of 10 as the penalty decayed (max penalty 0.188 at +3d, 0.057 at +14d). Overlap with all earlier lists reached 9 of 10 by +7d: the pool is small and stable, so albums return once their penalty fades.
- Spread stayed constant: 10 distinct artists, top-2 share 20% in every run.
- Steady-state cost is low: 2.6 to 3.3 s and 2 ListenBrainz requests per warm refresh once cached.

## Decision

Do not reopen 3.2 (cooldown calibration) on this evidence. Named risk if it were reopened: a stronger or longer cooldown would trade relevance for freshness (score span of the top 10 is 25%, so a larger penalty starts to displace the best-scoring albums) while the underlying cause, a stable 55-candidate pool, is untouched. Supply breadth (the larger lever) needs owner approval for any added lookups or ListenBrainz requests. Limits above apply: one sample, and simulated time does not move CF or the profile.
