# Engine 2 — roadmap: diverse, multi-list recommendations

Status: **draft roadmap, 2026-10-23.** GitHub `main` is authoritative; the family-coverage policy is merged in PR #573 and remains opt-in. Phase 1 and Phase 2 (lens framework and evaluation metrics) are complete. Phase 3 is partly complete: the unwired Deep cuts tiered supply (PR #581) and the per-lens, per-day radio cache scope (PR #582) are merged; the window gate is met only at the seed level (see Phase 3). Evidence is aggregate-only from one profile; see [Limits](#limits-of-the-evidence).

## Goal

Replace "one list of 10 shaped by fixed 4/3/3 quotas" with several complementary lists of 10, each produced by a named **lens**, all generated from one shared candidate pool. The owner's stated aims:

1. Diversity: more than one list, so variety is available over the day and not only inside a single list.
2. Obscure albums: some lists should deliberately surface them.
3. Time ranges: lenses may use different windows of listening history (for example last 30 days versus all time).
4. Bounded provider cost: pre-compute and cache; do not multiply fetching by the number of lists.

## What was measured

All captures are read-only, slskd off, fresh data directory per run, private, outside the repository (mode 600). Single profile, one capture per arm, `count = 10`. The harnesses were one-off scripts and are not committed.

### 1. The tag-lookup budget limits what a wider CF pool can do

Genre-tag lookups were hard-capped at 60 candidate artists (plus 15 recent) regardless of pool size, so extra candidates arrived untagged, scored low, and never ranked. Untagged unowned candidates:

| CF pages | Unowned pool | Untagged at 60 lookups | at 120 | at 220 |
| --- | --- | --- | --- | --- |
| 4 | 107 | 40 | 15 | 15 |
| 8 | 200 | 97 | 39 | 13 |
| 12 | 243 to 248 | 128 | 61 | 15 |

120 lookups removes most of the problem; 220 adds almost nothing. With the ListenBrainz batch prefetch, runs at 120 and 220 lookups took 20 to 33 s cold with no provider failures. The per-artist MusicBrainz fallback path (about 1.1 s per artist) was not exercised, so the cost of 120 lookups when the batch path fails is unmeasured.

### 2. Labelling mistake and its correction

The first experiments labelled a candidate's family by the alphabetically first tag through the rules table, which put "alternative rock" under "alternative" and inflated family counts. MusicBrainz tags arrive sorted by name, so the first tag carries no relevance. The label now used is `primary_genre_family`: the plurality of `fallback_family` (trailing root word, then the Wikidata ancestry table) across all tags. Earlier claims that "cap 2 clearly beats 4/3/3" were overstated; with the corrected label a cap of 2 per family alone is roughly level with 4/3/3 on spread (6 against 6 to 7 families) and higher on engine score.

### 3. Family coverage uses the wider pool; quotas and MMR do not

Policy compared (real allocator, all arms returned 10 albums by 10 artists):

- **4/3/3 quota** (production).
- **Family coverage:** genre-family cap 2 (unknown tags capped at 1), adventurous floor `count // 5`, a coverage phase taking the best candidate of each unseen family at or above 0.4 x the top score, then score fill.

| CF pages / tags | 4/3/3: families, entropy, mean score, largest family | Coverage: families, entropy, mean score, largest family |
| --- | --- | --- |
| 4 / 60 | 5, 2.05, 0.137, 4 (3 untagged) | 7, 2.72, 0.156, 2 |
| 4 / 120 | 7, 2.52, 0.140, 4 | 7, 2.72, 0.156, 2 |
| 8 / 60 | 6, 2.32, 0.142, 4 | 8, 2.92, 0.152, 2 |
| 8 / 120 | 6, 2.45, 0.145, 3 | **9, 3.12, 0.147**, 2 |
| 12 / 60 | 7, 2.52, 0.136, 4 | 8, 2.92, 0.152, 2 |
| 12 / 120 | 6, 2.45, 0.145, 3 | 9, 3.12, 0.147, 2 |

Other findings from the harness (prototype, not the production allocator):

- Score order only: 4 families, 6 to 7 albums in the largest.
- MMR alone (penalties 0.25 to 1.0) changed almost nothing; with a family cap it added little. Tag overlap is low everywhere because most tags are fine-grained and distinct.
- A relevance floor on top of the cap changed nothing at 0.3 to 0.5; coverage needs a floor of 0.4 or lower to reach the extra families, and the benefit appears only from 8 CF pages with 120 tags. At 4 pages the pool cannot exceed 7 families. 12 pages added nothing over 8.
- Category mix under coverage tilts toward cross-genre (adjacent 3, cross-genre 5, adventurous 2 at 4 pages); the floor keeps adventurous at 2.
- With cap 3, the legacy 60-check budget (consumed by already-owned albums) left lists at 8 to 9 albums. Under the coverage policy owned candidates do not use the budget.
- Mean pairwise tag Jaccard (lower is more varied): coverage 0.037 to 0.060 against 4/3/3 at 0.049 to 0.131, lower in every arm. A cap of 2 alone was higher than 4/3/3 in the 8-page arms (0.083 against 0.049).

### 4. Live end-to-end (new code, 120-artist tag budget)

| CF pages | Policy | Distinct families | Largest family | Notes |
| --- | --- | --- | --- | --- |
| 4 | quota | 7 | 4 (rock) | 4/3/3 split |
| 4 | family_coverage | 7 | 2 | adventurous 2 |
| 8 | family_coverage | 9 | 2 | adventurous 2 |

10 recommendations by 10 artists each, no provider failures. In this one comparison the coverage lists were made of better-known albums than the quota list (which had a jazz album and two lesser-known picks the coverage lists lacked). Whether that is better or worse is unmeasured.

### 5. Obscurity: where obscure candidates come from

Last.fm `album.getInfo` for all 203 unowned candidates of the 8-page/120-tag capture, then `artist.getInfo` for the 144 distinct artists. Read-only, about 350 calls at 4 per second.

- **Existing data is almost empty.** The engine looks up Last.fm popularity for about 40 candidates per run; only 12 unowned candidates carried listener counts, and the smallest was 9,382. The captures cannot answer obscurity questions on their own.
- **Album-level counts are unreliable.** Titles with brackets, curly quotes or edition suffixes failed to match, so very well-known albums appeared to have a few thousand listeners. Artist-level counts are better but still mismatch on "feat." credits and non-ASCII hyphens. Lookups by MBID (Last.fm accepts `mbid`) would avoid name matching.
- **The pool is overwhelmingly popular.** Artist listeners, 203 candidates: median 4.2M; 33 candidates (16%) by artists under 200k; 22 under 50k; 17 under 10k.
- **Obscure candidates come from the MusicBrainz tag lane, not CF.** By source: tag lane 29 of 40 obscure (73%); ListenBrainz CF 4 of 163 (2%). CF is built from listening data and is popular by construction.
- **The tag lane has no ranking signal.** Its candidates all carry the same base score (0.035, no taste bonus), so they sit at the bottom and never surface; order among them is arbitrary.
- **The engine score tracks popularity.** Median album listeners by score rank: top 20, 2.7M; ranks 20 to 60, 2.0M; ranks 60 to 120, 1.6M; ranks 120 and below, 75k.
- **Deezer probe (15 matched of 20; free, no key).** Albums with 1 to 554 Last.fm listeners had 0 to 132 Deezer fans; albums with 4.0M to 5.3M had 54 to 348,362. Separates the extremes; noisy in the middle (4.17M listeners with 1,625 fans; 4.97M with 54).

### 6. Time ranges (from earlier work, 2026-10-23 log)

Recent 30 days against all time (flat weights): 9/10 final overlap, 143 of 152 shared candidates changed rank, category split unchanged. With the production 14-day half-life the two are identical, because decay is anchored to the newest listen. The CF pool is built by ListenBrainz from the whole history, so a time window can change only the ranking and the profile-driven seeds, not the CF candidates. Whether the tag-lane seeds come from the profile (so that a window could change which obscure candidates exist) has **not** been verified; the seeding code (`discovery/tag_queries.py`, `discovery/lb_tag_lane.py`) has not been read for this purpose.

## Findings

1. Fetch cost is per pool, not per policy. Selection policies are pure and take milliseconds, so many lists can come from one gather. Rotating the approach does not save provider budget.
2. A wider CF pool helps only if tagging keeps up (about 120 artists) and only through a selection step that reserves slots for new families.
3. The best available engine score is a popularity-flavoured relevance score; it cannot by itself produce an obscure list.
4. Obscure supply exists but lives in a lane with no ranking signal, and the popularity data needed to identify it is missing and name-fragile.
5. There is no ground truth for "better list". Multiple lenses with per-recommendation attribution would create it.
6. Lists from one pool overlap (4 to 6 of 10 between policies), and the cooldown removes shown albums, so lists must be partitioned or later lists degrade.

## Design principles

- One gather per refresh, many lenses. Lenses are pure functions of an immutable pool snapshot.
- Each album appears in at most one list per day (partition), and every recommendation records its lens.
- Lists are generated ahead of time and fixed for the day (owner decision, 2026-10-24); they change between days, not on every refresh. Rotation is a presentation choice, not a fetch strategy.
- Popularity and taste signals are keyed by MBID wherever a provider supports it.
- Preserve the guardrails in `RECOMMENDATION_ENGINE_IMPROVEMENTS.md`: owned-album exclusion, artist identity, duplicate suppression, bounded provider calls, private captures never in GitHub.

## Lens catalog (proposed)

| Lens | Window | What it does | Needs |
| --- | --- | --- | --- |
| Now | last 30 days | Today's behaviour: close to the current profile | existing |
| Genre spread | any | Family coverage policy | merged branch, tag budget |
| Long-term taste | all time, flat weights | Profile without recency decay. Measured 2026-10-24: its seed tags overlap Rediscovery's by 5 of 6, so it adds little next to it. | profile windows, seeds |
| Rediscovery | years ago, dormant for 12+ months | Unowned albums by or near artists once played heavily | history import, similar artists |
| Deep cuts | dense month or recent window | **Owner-approved definition (2026-10-23):** window: a dense listening month (or the recent-activity window when the history is too short); source: ListenBrainz tag radio at popularity band 50 to 75% (low percent = most popular), with the 75 to 100% band and the MusicBrainz tag search as the tail; seeds from the window profile via `select_supplementary_tag_queries`; gates: batch title-marker filter on, tag count at least 2, album listeners by release MBID between about 300 and 50,000, one album per artist, at most 2 per seed, artists already known to the listener excluded. Ranked by radio tag strength; plays per listener is an optional tie-break. Thresholds are starting values. | merged popularity module, window profiles |
| Stretch | all time minus recent | Families in all-time listening absent recently, plus genre-table neighbours. Not built: on the measured history it gives the same artists as Rediscovery. | profile windows |
| Repeated tracks | all time | **Owner-approved definition (2026-10-24):** seeds from tracks played at least 5 times by artists outside the all-time dominant tags (`discovery/profile_seeds.py`, `repeated_track_seed_queries`; the dominant tags are the 5 most common tags among the 40 most played artists; artists without tags are skipped); supply, tiers and day-keyed radio answers as for Deep cuts (`run_deep_cuts_tag_supply` with lens `repeated_tracks`); selection with the Deep cuts gates: tag count at least 2 (a minimum of 1 was tried in PR #585 and dropped: it rescued 2 of the 8 candidates the minimum of 2 rejected, and 5 had no genre tags at all), album listeners 300 to 50,000, one album per artist, at most 2 per seed, owned albums excluded, and artists the listener already knows excluded (a library artist with the same normalized name, decided by artist MBIDs when both sides have one; a listening-history artist by MBID), reported under its own lens name. Registered in `lenses.py` but not in the default lens order. On the one measured history the seeds are raï, folk, traditional pop, desert blues, jazz fusion and folk rock, which share no tag with Now, Long-term or Rediscovery. Open: candidates by artists with no genre tags are always rejected (5 of 23 in the live run, including the niche genres this lens seeds); the owner asked to explore another tag source or an exception. The radio path has not been exercised for this lens. Thresholds are starting values. | merged helpers, popularity module |
| Obsessions | all time | **Owner decision (2026-10-24): becomes a lens; definition not yet written.** Artists with most listens inside one short span (`burst_artist_weights`). Seed tags are broad (rock, rock and roll, blues rock), so obscurity rests on the Deep cuts gates, which the lens is expected to reuse. | merged helpers, definition |
| New artists (candidate) | since a cutoff | Artists first heard since a date (`new_artist_weights`). Four of six seed tags overlap Now, so it is redundant with Now on the measured history. Lens not defined. | merged helpers, owner decision |
| Era and region | any | Spread across decade and country | MusicBrainz area and dates |
| Comeback | past window | New releases by artists played heavily in a past window | `new_releases.py` |

## Other data sources (candidates)

Verified in this work: Deezer album search works without a key (see above); the repo already has MusicBrainz and Last.fm clients and a MusicBrainz rating client. Everything else is from general knowledge and needs verification, rate-limit review and, where credentials are involved, the owner's approval.

| Source | Possible use | Notes |
| --- | --- | --- |
| Deezer | Fan count as a cross-check on obscurity | Free; noisy mid-range; some albums unmatched |
| Discogs | Have/want counts; finer genre styles | Needs a token |
| MusicBrainz | Rating votes, release counts, area, dates | Already integrated; area and dates give era/region axes |
| Wikidata/Wikipedia | Notability (page existence, pageviews) | Wikidata already used for the genre table |
| Cover Art Archive | Weak existence signal | Free |
| Bandcamp, Spotify, RYM | None planned | No usable open API, or restricted access |

## Roadmap

Each phase ends with a written result in `PROJECT_LOG.md`. Any live capture or higher provider budget needs the owner's approval; merges, publication and deployment are separate decisions.

### Phase 0 — decisions and housekeeping

- Owner decides: merge the family-coverage branch (opt-in, default unchanged), whether to raise `CF_MAX_PAGES` to 8 when coverage is enabled, and whether a settings control is wanted.
- Commit the evaluation harness (selection-policy comparison, metrics below) as a tested script, since the one-off scripts are not in the repository.
- Let replay captures freeze the selection policy so family-coverage captures reproduce.

### Phase 1 — first steps (next priority)

1. **MBID-keyed popularity** for the whole pool, with a bounded budget and caching; compare Last.fm artist-level, Last.fm album-level by MBID and the Deezer cross-check on the existing 203-candidate capture. Output: an obscurity signal and its coverage. **Measured 2026-10-23:** album listeners by release MBID (via batched MusicBrainz release search) 166 of 203, artist listeners by artist MBID 203 of 203; Deezer and Discogs agree less (Spearman 0.38 / 0.50 against album listeners). Implementation merged in PR #574 (not wired into runtime); details in `PROJECT_LOG.md`.
2. **Tag-lane taste-fit score**, evaluated offline on existing captures: tag/family overlap with the profile, similar-artist links. Output: a ranking among tag-lane candidates that is not arbitrary.
3. **Read how the tag lane is seeded** and whether a history window can drive the seeds.
4. **Offline "deep cuts" prototype** on the existing captures: how many obscure, well-fitting candidates exist, and what a list of 10 looks like.

Exit criteria: a measured obscure supply (count and fit) and a recommendation on whether the tag lane alone is enough or another source is needed.

**Phase 1 result (complete 2026-10-23, details in `PROJECT_LOG.md`):** album listeners by release MBID are the obscurity signal (artist listeners are a diagnostic fallback only and do not pass the Deep cuts album gate); a window changes the tag-lane seeds completely and the resulting lists share no artists across four different months; tag/family fit is not a validated ranking signal, so it is not used; the tag lane alone is enough to supply obscure candidates when it uses the ListenBrainz tag radio (50 to 75% band, whose `percent` is inverted: low is popular) with the MusicBrainz tag search as a tail; a five-window end-to-end run takes about 35 s per window. The Deep cuts lens definition is in the lens catalog above.

### Phase 2 — lens framework

Status 2026-10-23: lens field, Now/Genre spread/Deep cuts lenses, partitioning, Deep cuts pool adapter, and evaluation metrics merged (PRs #575, #577, #578; unwired).

- Lens as an explicit concept in the allocator request and result; partitioning across lists (each album in one list per day).
- Implement Now, Genre spread, Deep cuts. Tests per lens plus a partition test.
- Evaluation metrics (below) computed per lens and across the set.

### Phase 3 — time-range profiles

- Profile windows (30 days, 1 year, all time) built from the imported history, with flat or windowed weights.
- Window-driven seeds for the tag lane and similar-artist queries; Long-term taste, Rediscovery and Stretch lenses. Time-window lists were skipped on 2026-10-24 and reopened by the owner the same day, at the seed level: they set the genre mix, not the albums. The history profiles are merged in PR #583 (unwired); which of them become lenses is an owner decision.
- Deferred from Phase 2 (owner decision, 2026-10-23): make the tag-radio popularity band a parameter keyed in the radio cache (approved Deep cuts band 50 to 75%, tail 75 to 100%), verify the title-marker filter on both radio and MusicBrainz sources, and add the MusicBrainz tag-search tail. Defaults stay at the current 0 to 100% until the owner approves a live run.
- Gate: show that a window changes the candidate pool, not only ranks. Result (2026-10-24, six repeated radio samples per tag, five windows, replayed through the production lane): a window changes the pool only through its seed tags. Each tag contributes exactly five albums, and the albums are redrawn on every radio call (about one album shared across repetitions of the same window). Different windows share albums only where they share seed tags. The gate is therefore met at the seed level and not at the album level. Radio answers are now fixed per lens per day (PR #582), so a daily list is stable without making it fixed forever.

### Phase 4 — precompute and serve

- Background gather writes a pool snapshot; all lenses run on it; finished lists are stored with timestamp and lens (the repo has `discovery/refresh.py` and a snapshot store to build on).
- Daily generation with lists fixed for the day (radio answers keyed by lens and day, PR #582), a fresh set the next day; rotation or "next list" in the UI. Cooldown interaction handled by partitioning.
- Cache popularity and tags (genre tags already use a 90-day cache); respect MusicBrainz and Last.fm rate limits.

### Phase 5 — feedback loop

- Store the lens on every recommendation; use existing recommendation feedback (saves, downloads, plays) to compare lenses.
- Only then consider reweighting or retiring lenses. No quality claim before this data exists.

## Evaluation metrics

Distinct families and largest-family count; entropy of the family distribution; mean pairwise tag Jaccard; mean engine score and minimum score; overlap with the production list; untagged picks; adventurous count; for obscure lenses, the share under a stated artist-listener ceiling and the fit score. For the set of lists: union size and pairwise overlap.

## Risks

- Popularity lookups by name mislabel artists; MBIDs are required.
- "Unknown" is not "obscure": data-poor candidates can be junk. Obscure lenses need a taste-fit gate.
- More lists mean more acquisitions; a daily cap is worth discussing.
- Engine score is not a listening-quality measure.
- One profile (rock-leaning in the 10-23 captures, jazz-leaning earlier): results may not transfer.

## Limits of the evidence

One profile; one capture per arm; single live run per configuration; harnesses are my own re-implementation except where stated; Last.fm and Deezer matching is imperfect; the genre label is derived and coarse; no browser check; no listener-quality measurement; nothing here is published or deployed.

## Open decisions for the owner

1. Merge the family-coverage branch (opt-in)? Make it the default later?
2. `CF_MAX_PAGES` 8 when coverage is on?
3. Settings or UI control for the policy, now or later?
4. Which additional data sources to adopt (Deezer, Discogs), and credentials for Discogs if so.
5. How many lists per day, and rotation versus tabs.

   Resolved 2026-10-24 (owner): lists are fixed for the day and refreshed daily, not on every refresh.
6. A daily acquisition cap if several lists are served.
