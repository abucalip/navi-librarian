# Proposal: read more ListenBrainz CF pages (needs owner approval)

Status: **proposal only. No code change. No extra request is made until the owner approves.**

## Finding that motivates it

Measured with one owner-approved live run (cold build plus two warm refreshes, aggregate only, disposable data directory deleted):

| | cold | warm 1 | warm 2 |
| --- | --- | --- | --- |
| CF recordings returned / resolved / failed | 200 / 200 / 0 | 200 / 200 / 0 | 200 / 200 / 0 |
| Uncached per-recording MusicBrainz lookups | 0 | 0 | 0 |
| Per-run budget (100) reached or skipped | no / 0 | no / 0 | no / 0 |
| CF albums / distinct CF artists | 36 / 15 | 36 / 15 | 36 / 15 |
| Top-2 artists' share of CF recordings | 47.5% | 47.5% | 47.5% |
| Final list (CF / tag search) | 4 / 6 | 4 / 6 | 4 / 6 |
| ListenBrainz CF requests | 2 | 2 | 2 |

- The 100-per-run MusicBrainz budget is not a limit: the batch path resolves every fetched recording.
- The limit is `CF_MAX_PAGES = 2` × `CF_PAGE_SIZE = 100`: each run reads 200 of the 1,000 recordings ListenBrainz reports (`total_mbid_count`), and the same 200 each time.
- That is why the candidate pool (55 clear candidates) and the repeat rate (see `REPEAT_RATE_MEASUREMENT_2026-10-20.md`) do not move between runs.

## Proposal

Raise `CF_MAX_PAGES` from 2 to 3 (or 4). No other code path changes.

| `CF_MAX_PAGES` | CF recordings read | ListenBrainz CF requests per run (now 2) |
| --- | --- | --- |
| 2 (today) | 200 | 2 |
| 3 | 300 | 3 |
| 4 | 400 | 4 |

Per-recording MusicBrainz lookups are unaffected for batch hits. Recordings resolved by the batch path are cached for 180 days, so the added work is mostly the first run after the change.

## Risks and unknowns (not measured)

- **Added requests per run:** +1 or +2 ListenBrainz requests. The standing rule is no added ListenBrainz requests without owner approval; this is that request.
- **Batch and release-group calls for the new recordings** are not counted above. The cold run showed 48 to 58 MusicBrainz-side calls; the added cost for 100 or 200 more recordings is unmeasured.
- **Pool depth quality:** ranking inside the CF list is by score, so later pages are lower-scored. Whether they add useful, non-owned, differently-sourced albums is unmeasured. Concentration today is high (two artists supply 47.5% of recordings).
- **Cold-start time** is likely to rise slightly (the cold build took about 106 to 123 s).
- A later page failure is already tolerated: earlier pages are kept (`page_failure_class`).

## Suggested acceptance if approved

One owner-approved live run at the chosen value with the same harness: report CF recordings resolved, CF albums and artists, top-2 share, final-list mix, overlap with the previous list, requests per run and wall time, then decide whether to keep it. Revert is a one-constant change.

## Alternative that needs no approval

Rotate which profile and exploration tags the tag lane samples per run, with unchanged candidate counts and no added lookups. The lane was the noisiest input (38 vs 10 candidates across the cold pair), so it needs its own measurement first.
