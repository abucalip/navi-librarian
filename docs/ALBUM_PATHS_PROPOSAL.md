# Album paths proposal

**Status:** owner decisions recorded 2026-11-09 (see "Decisions recorded"). Approved for build in slices. Built and merged so far: the probe script (PR #921), the recording-places audit (PR #922), the builders for Studio Crew, Guest List and Covers and Sources (PR #924, squash `3901673d599079e80cfa41319d4e6d2fe55751fe`) the Same Year, Same Scene builder (PR #925, squash `adf7454da321543e78aff8d3526f0987b7e7c497`) and the Neighbours by Ear composition (PR #926, squash `934a1c0786f78f4daa2ce257888ee6b189278e3b`). Nothing is published or deployed.
**Date:** 2026-11-09
**Context:** The Paths button on an album page. Contract context: [Server V2 contract](SERVER_V2_CONTRACT.md) (`GET /api/knowledge/paths`), [Server V2 remaining work](ServerV2.md), builders in `intelligence/graph/paths.py`.

## Goal

An album page gets a Paths button. Its paths start from the album, not the artist, and must not repeat the five artist kinds (`follow_the_musician`, `sideman_to_leader`, `label_path`, `composition_path`, `scene_path`). Each stop needs a credit-grade reason, as artist paths do. A start with no evidence returns `empty`; nothing is padded in.

## Rules inherited from the artist paths

- Credit-grade evidence only. An `inferred` edge, or one whose other end is `fuzzy_unconfirmed` or `unresolved`, is never used, not even as a bridge.
- Every stop carries `reasons[]` (`code`, `text`, `via`, `anchor`, `evidence`); a stop with no reason is never produced.
- Built on demand within bounds (rows, time, stops) with a `truncated` flag; cached by (start, kind, generation); no provider traffic.
- Missing data is reported as `not_loaded` or `empty`, never as a fact about the album.
- Taste data must not affect recommendation ranking (see path 7).
- Design sheets and pages according to the artist paths ones, use the same layout, rules and dynamic text templates. Adapt the latter to contexts if need be.

## Kept paths

Reason codes below are proposed names, to be settled when the contract is written.

### 1. Studio Crew (`album_crew`)
Producer, engineer, mixer and similar production credits on this album lead to other owned albums those people worked on.
- **Data:** album-scope and recording-scope credits from the album dossier (`people[].credits`, relations such as `producer`, `engineer`, `mix`).
- **Stop:** an owned album. **Reason:** `crew_on` (via the person, anchor the credit on this album).
- **Not a repeat:** artist paths follow performers and leaders; this follows the people behind the console.
- **Risk:** a hub producer or engineer can fan out to hundreds of albums. Needs a per-person cap and a ranking rule that does not use similarity or play counts (for example, number of shared credits, then release date).

### 2. Guest List (`album_guests`)
Only the non-lead credits on this album (guest vocalist, string arranger, featured player) lead to other owned albums where that person appears.
- **Data:** recording-scope `instrument`, `vocal`, `performer` credits, minus the album's own credited artists.
- **Stop:** an owned album. **Reason:** `guest_on` (via the person, anchor the track they are credited on).
- **Not a repeat:** `sideman_to_leader` starts from an artist and lands on leaders. This starts from the specific people on this album and lands on any album they appear on.
- **Risk:** overlap with Studio Crew when one person has both production and performance credits. Merge such a person into one stop with two reasons, not two stops.

### 3. Same Room (`album_room`)
Recordings on this album with a stated recording place or event lead to other owned recordings made in the same place.
- **Data:** place and event links on recordings (`place_page`, `event_page`).
- **Stop:** an owned album. **Reason:** `recorded_at` (via the place, anchor the track).
- **Known gap:** `recording_places_and_dates` is listed in the album dossier's `not_loaded`. This is the album-scoped successor to the dropped `same_studio_different_decade`, so it may hit the same coverage problem. The probe decides whether it can be built.

### 4. Covers and Sources (`album_works`)
Each track's recording maps to a work. Stops are other owned recordings of the same work, plus related works linked by a stated work-to-work relation (for example, a cover or arrangement source).
- **Data:** `recording-works` and `work` pages; stated work relations only.
- **Stop:** an owned album. **Reason:** `same_work` or `derived_work` (via the work, anchor the track on this album).
- **Not a repeat:** `composition_path` starts from an artist's compositions. This starts from this album's tracklist and shows who else recorded each song.
- **Risk:** common standards have very many recordings; cap per work and show the count of the rest.

### 6. Same Year, Same Scene (`album_moment`)
Albums from roughly the same time, linked by something the data states.
- **Rule (strict, proposed):** a stop needs a release date within two years of this album's earliest edition date **and** at least one stated link: the same label, the same stated non-country area, or a shared credited person. A date match alone never produces a stop.
- **Stop:** an owned album. **Reason:** `same_period_label`, `same_period_area` or `same_period_credit`.
- **Date source:** earliest `release_facts` date in the release group. File-tag years are not used.
- **Risk:** closest to padding. If the probe shows the strict rule yields mostly label-only stops that `label_path` already gives, cut it.

### 8. Neighbours by Ear (`album_sonic_neighbours`)
Shown only when `GET /api/capabilities` says `sonic_available: true`.
- **Method:** call `/api/sonic/similar` for each track of this album, drop tracks already on the album, group the results by album and rank albums by how many of this album's tracks return a track from them.
- **Stop:** an owned album. **Reason:** `sonic_neighbour` with the count of matching tracks.
- **Constraints:** never sort or threshold on `similarity` (contract: it sits in a narrow band and is informational). The per-artist cap of 2 still applies per seed. A track with no analysis data is skipped and reported, not treated as no match.
- **Cost:** one similar-track call per track. Needs a bound on tracks per album and a cache; the Sonic responses are already kept for an hour. This is a composed path, not a graph path, so it likely lives beside the sonic routes and not in `paths.py`.

### 9. Listen-through Gaps (`album_gaps`)
Credits on this album that lead to owned albums the owner has played little or never.
- **Data:** path 1 and 2 stops, filtered by play history.
- **Decision needed:** the contract states that taste profiles and context do not affect recommendation ranking. A filter on play counts is a different thing from ranking, but it must be stated and approved. Proposed constraint: play history only selects and labels stops that already have a credit-grade reason; it never adds a stop and never reorders by affinity.
- **Reason:** the stop's own credit reason, plus a label such as "not played".
- **Risk:** depends on the play data source and its sample state. If history is thin or unavailable, the path returns the unfiltered stops marked as such, not an empty "unplayed" claim.

## Dropped from the first list

- **Other Pressings:** a library-health feature, not a path; belongs with the edition tools.
- **Album Drift** (route from first track to last through the library): not wanted.

## Probe plan

Mirror `intelligence/graph/path_coverage.py` and run against a copy of the owner's real store.

For each owned album, and for each kept kind, record:
- albums with at least one stop, `empty` count, and the distribution of stop counts (including how many hit the cap);
- the fraction of stops that are also reachable by the album's artist's five existing kinds (the overlap with artist paths);
- for Same Room: albums with at least one recording place or event link; for Covers and Sources: tracks with a work link and works with more than one recording;
- for Same Year, Same Scene: stops by link type, and how many are label-only;
- for Studio Crew and Guest List: credit counts per album, hub fan-out, and time per build against the 2-second bound;
- for Neighbours by Ear: albums with at least one analysed track, and call cost per album.

Outputs go in the scratchpad, not the repo, until a decision is recorded.

### Thresholds (owner decision, 2026-11-09, fixed before the probe runs)

The **Balanced** preset applies to Studio Crew, Guest List, Covers and Sources, and Same Year Same Scene:

| Measure | Pass |
|---|---|
| Coverage (owned albums with at least one stop) | at least 35% |
| Median stops, among albums that have any | at least 3 |
| Overlap with the artist's five existing kinds | at most 35% of stops |
| Builds finishing within bounds (no `truncated: time`) | at least 95% |

Additional and special rules:
- **Same Year Same Scene:** at most 50% of its stops may be label-only, since `label_path` already covers that ground.
- **Same Room:** judged on its probe result to decide whether a recording-place slice is needed; failing the preset does not cut it.
- **Neighbours by Ear:** coverage held to the stricter 60%, plus a cap of **8 seeds (similar-track calls) per album** (owner decision, 2026-11-09, option B). Rules that go with it:
  - Seeds are evenly spaced across the tracklist and always include the first and last track. Selection is deterministic, so the one-hour cache still applies; no random sampling.
  - A seed with no analysis data is skipped and reported; it does not count against the cap.
  - Ties in the album ranking break by earliest release date, never by `similarity`.
  - A total time bound applies, like the 2-second path limit; if hit, the response returns `truncated`.
  - The number is provisional: the probe records latency and result quality at 5, 8 and 12 seeds on a sample of albums. The cap is changed only by a new owner decision, not loosened after seeing results.
- **Listen-through Gaps:** no coverage threshold of its own, since it inherits stops from Studio Crew and Guest List. Rule: thin or unavailable play history returns the unfiltered stops marked as such, never an empty "unplayed" claim.

A path that fails its thresholds is cut or gets a new slice (see the contingency below); the numbers are not loosened after seeing the result.

## Contingency: new import slice

If a path lacks data, build a slice for it instead of loosening the evidence rules. Likely candidates:
- ~~**Same Room:** recording place and date links (listed in `not_loaded`). **Approved 2026-11-09**; this is the one new slice.~~ **Done as an audit (2026-11-09, PR #922): no new import step needed**, the store already holds the links; see "Slice audit" below.
- **Studio Crew:** production-credit relations at recording scope, if the current slice keeps only album-scope ones.
- **Covers and Sources:** work-to-work relations, if not currently imported.

A new slice follows the Phase 7 release-links precedent: a bounded, resumable import step, a schema bump, and the path cache invalidated through the slice's data version. `not_loaded` stays accurate until it lands.

## API and client shape (proposed, for review)

- Extend `GET /api/knowledge/paths` to accept `type=release` or `release_group` with the new `kind` values, so clients reuse the existing decoder. Decided 2026-11-09; no separate album route.
- `GET /api/knowledge/paths/warm` is per owned artist today; album paths are cheaper to build on demand and probably need no warm-up. Confirm after the probe's timings.
- Clients hide the Paths button when the album has no kind with stops, and show Neighbours by Ear, in its own tab, only when `sonic_available`.
- Album paths must not list the artist's own paths again; the button lists only the album kinds.

## Probe results (2026-11-09)

Run on a copy of the owner's store (`discair-mb-test/intelligence.sqlite3`, opened read-only). Raw outputs are in the scratchpad, not the repo. Scripts: `scripts/album_path_coverage.py` (offline kinds) and a sonic probe that calls `/api/sonic/similar`-equivalent logic through the app's Sonic path (read-only Navidrome calls).

### Offline kinds (884 owned albums)

| Path | Coverage (≥35%) | Median stops where any (≥3) | Overlap proxy (superseded) | Exact overlap, as shown / uncapped (≤35%) | Within 2 s | Result |
|---|---|---|---|---|---|---|
| Studio Crew (`album_crew`) | 56.7% | 9 | 63% | 8.8% / 10.7% | 100% | Passes |
| Guest List (`album_guests`) | 56.6% | 11 | 72% | 12.0% / 19.3% | 100% | Passes |
| Covers and Sources (`album_works`) | 44.1% | 3 | 78% | 9.2% / 15.7% | 100% | Passes |
| Same Year, Same Scene (`album_moment`) | 74.2% | 4 | 78% | 22.4% / 29.6% | 100% | Passes; label-only share 28.7% (≤50% passes) |
| Same Room (`album_room`) | 38.7% | 6 | 46% | 8.5% / 13.1% | 100% | No gate; judged on its own result |

- No album reached the 200-stop cap. Maximum stops per album: crew 54, guests 79, works 22, room 58, moment 22.
- **Overlap, exact (2026-11-09).** Measured against the real artist-path builder (`build_path`, all five kinds) for each album's credited artists, run read-only on the store copy. Each artist-path stop is mapped to owned releases (recording stops via the releases carrying them, label stops directly, artist stops via the releases credited to them); an album-path stop counts as overlap when the artist paths reach that release. "As shown" uses the default limits (30 stops); "uncapped" lifts the stop and row limits and is the worst case. It is still a slight undercount: 95 `follow_the_musician` and 90 `composition_path` artist builds hit the row bound even uncapped. The earlier proxy overstated overlap about 4 to 7 times, so the four proxy failures are void and all four paths pass the overlap gate.
- **After dropping overlapping stops** (decision 4, uncapped worst case): coverage and median stay above the thresholds. Studio Crew 55.5% / 8, Guest List 51.6% / 9.5, Covers and Sources 39.4% / 3, Same Year Same Scene 63.5% / 3, Same Room 37.4% / 5.
- **Label-only share** (Same Year, Same Scene): 28.7% of all stops; 17.9% (as shown) or 19.2% (uncapped) once stops the artist paths already reach are dropped. Passes the 50% limit.
- **Overlap by artist kind:** mostly `label_path` and `sideman_to_leader`; for Covers and Sources it is `composition_path` (129 of 173 overlapping stops).

### Neighbours by Ear (40 sampled albums)

Sample: 40 of 748 owned albums with at least three tracks that have Navidrome IDs, chosen at even intervals by album ID. Seeds are the sample's tracks spaced evenly by ID order, not by track number.

| Seeds per album | Similar-track calls | Coverage (≥60%) | Call latency median / p90 | Album time median / max |
|---|---|---|---|---|
| 5 | 193 | 100% | 0.135 s / 0.209 s | 0.74 s / 0.87 s |
| 8 | 297 | 100% | 0.122 s / 0.187 s | 0.98 s / 1.22 s |
| 12 | 394 | 100% | 0.084 s / 0.164 s | 1.02 s / 1.82 s |

- Ranking stability: median Jaccard overlap of the top-5 neighbour albums between 5 and 12 seeds is 0.43. The ranking moves a lot with the seed count.
- Unmapped tracks: 360 (5 seeds), 581 (8), 754 (12) returned tracks had no matching owned recording in the store copy. They are dropped from the counts, so the figures are a lower bound. The cause is unverified (possibly the copy is older than the live library).
- No seed came back without analysis data in this sample, so the skip-and-report rule was not exercised.
- Per-artist cap of 2 per seed is applied, matching the app's current setting.
- The cap stays at 8 seeds unless the owner makes a new decision. These results are recorded for that decision, not used to change the cap.

## Slice audit (2026-11-09)

`scripts/album_slice_audit.py` unpacks only the recording, link, link-type and recording-link tables from the export (on every core with `indexed_bzip2`; 6.8 GB in 85 s on 8 cores) and compares, for the owned recordings, the distinct (recording, other end, relation) triples in the dump with the store copy. Counts only; read-only on both.

- 9,611 of 9,614 owned recordings are in the dump.
- **Place and event links:** `recorded at` 5,230 of 5,230 place links present; `mixed at`, `engineered at`, `edited at`, `produced at`, `remixed at`, `recorded in` (area) all complete. Event `recorded at`: 185 of 207 present (22 events missing).
- **Production credits at recording scope:** `producer` 8,123, `engineer` 6,825, `mix` 4,652, `recording` 2,960, plus arranger, conductor, instrument, vocal and the rest: every one complete.
- **Work links:** `performance` 7,454 of 7,454 complete. Work-to-work relations (`based on`, `arrangement`, `other version`) are loaded by the main import at the second hop.
- **Only gaps:** recording-to-recording relations whose other end is not an owned recording (for example `mashes up` 29 of 1,097, `samples material` 107 of 788). No path uses them, and the 22 missing event links are 0.3% of Same Room's source.

Merged in PR #922 (script, filtered test, dossier `recording_places[]`, re-recorded `knowledge_album.json`). Decision: the main import already holds everything the three paths need, so no separate import step, schema bump or data-version change is added. The one real defect was the album dossier: it listed `recording_places_and_dates` in `not_loaded` and never showed the place links it held. It now returns `recording_places[]` (recording scope only: `entity`, `relation`, `role`, `track`, `valid_from`, `valid_to` and the evidence fields) and drops that `not_loaded` key once the store holds any place, event or area link to a recording. Builders read the same edges.

## Decisions recorded (owner, 2026-11-09)

Made after the probe results above; thresholds were fixed before the probe and are not changed.

**Per path**

| Path | Decision |
|---|---|
| 1. Studio Crew (`album_crew`) | Keep. |
| 2. Guest List (`album_guests`) | Keep. |
| 3. Same Room (`album_room`) | Keep, and add the recording-places import slice (see the contingency section). ~~Import slice~~ Not needed after the audit (PR #922); the builder is unblocked. |
| 4. Covers and Sources (`album_works`) | Keep. No work-relations slice for now; margins are narrow (median 3, coverage 39.4% after dropping overlap), so revisit only if the built path feels thin. |
| 6. Same Year, Same Scene (`album_moment`) | Keep. ~~Builder~~ Done (PR #925). |
| 8. Neighbours by Ear (`album_sonic_neighbours`) | Keep at 8 seeds per album. The wider-sample check noted below is a build-time requirement, not a change to the cap. |
| 9. Listen-through Gaps (`album_gaps`) | Keep, with the constraint below recorded. |

**Open decisions resolved**

1. **Route:** extend `GET /api/knowledge/paths` (`type=release` or `release_group` with the new `kind` values). No separate album route.
2. Thresholds: already decided (Balanced).
3. **Play-history filter (path 9):** acceptable under the taste rule with this constraint: play history only selects and labels stops that already have a credit-grade reason; it never adds a stop and never reorders by affinity. Thin or unavailable history returns the unfiltered stops marked as such, never an empty "unplayed" claim.
4. **Overlap with artist paths:** a stop that the artist's five kinds already reach is dropped, even when its reason differs. The "after dropping overlapping stops" figures above are the ones that apply.
5. **Neighbours by Ear placement:** its own tab, separate from the credit-based paths, in the same way Sideman and Composition have separate tabs on artist paths. It is shown only when `sonic_available` is true.

**Carried into the build**
- Neighbours by Ear: the probe sample was 40 of 748 albums and the counts are lower bounds (unmapped tracks), so the build slice re-measures coverage on a wider sample before release. The 60% gate and the 8-seed cap stay as decided.
- Same Year, Same Scene and Covers and Sources pass with thin margins; their builders get fixtures that pin the strict rules.

## Open decisions for the owner (historical)

All resolved above on 2026-11-09. Kept for the record.

1. Extend the existing paths route or add a separate album route.
2. ~~The "enough data" thresholds for the probe.~~ Decided 2026-11-09 (Balanced; see Probe plan).
3. Whether play-history filtering (path 9) is acceptable under the taste rule, with the constraint above.
4. Whether a stop that is also an artist-path stop is dropped or kept when its reason differs.
5. Whether Neighbours by Ear sits in the same list as the credit-based paths or in a separate sonic section.

## Next steps

Status as of 2026-11-09 (merged work is on `main`; PR #921 merged):

1. ~~Owner reviews this proposal and answers the open decisions.~~ Done 2026-11-09 (see "Decisions recorded").
2. ~~Write the probe (`scripts/album_path_coverage.py`, filtered tests) and run it on a copy of the real store.~~ Done: script and filtered tests merged in PR #921; run on a copy of the store. Neighbours by Ear was measured separately (40-album sample, live sonic routes).
3. ~~Record results in this document~~ Done (see "Probe results"). Keep, cut or add a slice per path: decided 2026-11-09 (see "Decisions recorded"). The exact overlap measurement is done (see "Probe results"): all four paths pass the overlap gate.
4. Contract, builders, fixtures, then clients, each as its own slice with filtered tests and required CI. ~~Recording-places import slice~~ Done as an audit and dossier fix, merged in PR #922 (no import step needed; see "Slice audit"). Builders for paths 1, 2 and 4 are done (PR #924, see "Builders built" below). ~~Builder for path 6~~ Done, merged in PR #925 (see "Same Year, Same Scene builder"). ~~Neighbours by Ear composition~~ Done, merged in PR #926 (see "Neighbours by Ear composition"). Remaining, not started. Suggested order: contract section; builder for path 3 (its data is already in the store); Listen-through Gaps; fixtures and decoders; client screens.

## Builders built (PR #924, 2026-11-09)

`intelligence/graph/album_paths.py`: `build_album_path` and `cached_album_path` for `album_crew`, `album_guests` and `album_works`; `paths.py` exposes `kind_rows()` for the overlap check. Relation sets are the ones the probe measured. Caps: 50 albums per person, 20 per work, ranked by shared credits then earliest release date; the count left out is reported in `capped[]`. Stops the credited artists' five artist paths reach are dropped (decision 4) and counted in `overlap_dropped`; a build that runs out of time during that check is `truncated: "time"`. Filtered tests: `tests/test_intelligence_album_paths.py` (18) and the existing paths tests passed; full suite left to CI.

Run on a read-only copy of the owner's store, all 884 owned albums, after overlap dropping:

| Path | Coverage (≥35%) | Median stops where any (≥3) | No `truncated: time` (≥95%) |
|---|---|---|---|
| Studio Crew | 54.5% | 7 | 100% |
| Guest List | 48.8% | 11 | 99.8% |
| Covers and Sources | 36.7% | 3 | 100% |

All pass the Balanced thresholds; Covers and Sources has the thinnest margin. Slowest build 2.0 s. Not done: contract section, route extension, fixtures, clients.

## Same Year, Same Scene builder (PR #925, 2026-11-09)

Merged to `main` as `adf7454da321543e78aff8d3526f0987b7e7c497`. Filtered tests only; full suite and required CI ran on the PR.

`album_moment` is built in `intelligence/graph/album_paths.py` (`_moment_rows`). Rules as proposed: the start's earliest stored `release_facts` date, owned albums whose earliest date is within 2 calendar years (inclusive, by year), and at least one stated link. A date match alone, an undated start and an undated candidate give no stop. Links and reason codes:
- `same_period_label`: a shared `release_labels` row (no edge, so no edge evidence, as in the label path).
- `same_period_credit`: a shared credited artist (`credited_to` or `release_artist`, credit-grade, placeholder artists excluded), with both edges as evidence.
- `same_period_area`: a stated non-country area (`area` or `begin area`, kind not `country`) of two different credited artists. A stricter reading than the probe, which also let the same artist count; the same artist is already the credit link.

Ranking: most distinct links first, then the nearer year, then the earlier release; no similarity or play data. Overlap with the artist paths is dropped as for the other kinds. Because the artist's label path reaches every other album on a shared label, label links from a credited start are always dropped; label-only stops survive only for an album with no credited artist.

Run on the store copy, all 884 owned albums, after overlap dropping:

| Measure | Result | Pass |
|---|---|---|
| Coverage | 58.4% | at least 35% |
| Median stops where any | 3 | at least 3 |
| No `truncated: time` | 100% (slowest 1.3 s) | at least 95% |
| Label-only share of stops | 0% | at most 50% |

Median 3 is at the threshold. Filtered tests in `tests/test_intelligence_album_paths.py` pin the strict rules (the 2-year edge, no date match alone, undated start, unowned, uncertain edges, non-country area, ordering, overlap drop). Not done: contract section, route extension, fixtures, clients.

## Neighbours by Ear composition (PR #926, 2026-11-09)

Merged to `main` as `934a1c0786f78f4daa2ce257888ee6b189278e3b`.

`intelligence/sonic/neighbours.py` (`album_neighbours`) and `GET /api/sonic/album-neighbours?album_id=` in `app/api/sonic.py`. Rules as decided: up to 8 seeds, evenly spaced with first and last always included, deterministic; an unanalysed seed is skipped, reported in `skipped` and replaced by the next unused track (max 16 calls); matches on the album itself dropped; albums ranked by distinct seeds matched, ties by earliest track year then album id; `similarity` is never read. 5 s time bound gives `truncated: "time"` (such answers are not cached). Answers are cached for an hour with the other sonic routes. Filtered tests: `tests/test_sonic_neighbours.py` (9) and `tests/test_api_sonic_routes.py` pass. Not done: route test for the new endpoint, wider-sample coverage re-measure (build-time requirement), contract section, fixtures, clients. Year comes from the matched tracks, not release facts.

## Work split by model and effort

For usage efficiency, give Haiku the mechanical, self-checking steps: a spelled-out spec, an existing pattern to copy, and a test or diff that proves the result. Keep design, evidence rules and judgment on a stronger model. Effort is relative to the model's default. These are planning estimates, not measurements.

| Step | Model | Effort | Why |
|---|---|---|---|
| ~~Copy the real store and run the probe script~~ **Done** | Haiku | low | Mechanical; output is numbers. |
| ~~Write the probe measurements for paths 1, 2, 4 (counts, coverage, stop distribution, timing)~~ **Done** (offline kinds) | Haiku | low | Queries are fully specified above and copy `path_coverage.py`. |
| ~~Probe overlap with the artist's five kinds, and the label-only share for path 6~~ **Done** (exact overlap 8.8% to 29.6%; label-only 28.7%) | Sonnet | medium | Needs care to compare stops correctly; a wrong join gives plausible but wrong numbers. |
| ~~Probe for Same Room and Covers and Sources (place and work link coverage)~~ **Done** | Haiku | low | Counting queries against known tables. |
| ~~Probe for Neighbours by Ear (analysed tracks, call cost)~~ **Done** (40-album sample) | Haiku | low | Calls the live sonic routes and counts. |
| ~~Fill the results table in this document and apply the thresholds~~ **Done** | Haiku | low | Compare numbers to the fixed table; no judgment, and a non-passing path is flagged, not argued. |
| ~~Decide keep, cut or add a slice per path~~ **Done** 2026-11-09 | Owner / main model | high | Judgment against thresholds, with a decision recorded. |
| Set the Neighbours by Ear call cap | Owner | — | Decided: 8 seeds per album (2026-11-09). |
| ~~New import slice (recording places, production credits, work relations)~~ **Done** as an audit plus dossier fix (PR #922); no import needed | Sonnet | high | Schema bump, resumable import, cache invalidation; follows the release-links precedent. |
| ~~Path builders for Studio Crew, Guest List, Covers and Sources~~ **Done** (PR #924) | Sonnet | high | Evidence rules, hub caps, de-duplication of people across paths; a mistake breaks the credit-grade guarantee. |
| ~~Same Year Same Scene builder~~ **Done** (PR #925, see "Same Year, Same Scene builder") | Sonnet | medium | Strict-rule logic on top of existing readers. |
| ~~Neighbours by Ear composition~~ **Done** (PR #926) | Sonnet | medium | Groups similar-track results; must never sort or threshold on `similarity`. |
| ~~Listen-through Gaps filter~~ **Built** (`intelligence/graph/album_gaps.py`, not yet merged) | Sonnet | high | Must stay within the taste rule; a leak into ranking is a contract violation. |
| Write the contract section | Sonnet | medium | Needs consistent wording with the existing paths contract. |
| Record fixtures from a store copy | Haiku | low | Same capture steps as the artist path fixtures; tests diff the result. |
| Fixture-based filtered server tests | Haiku | low | Copy the artist-path tests; the fixtures define the assertions. |
| Android and macOS decoders plus filtered tests | Haiku | low | Copy the existing paths decoder and tests; fixtures define the result. |
| Android and macOS Paths button and screens | Sonnet | medium | UI design choices, shared actions, honest empty states. |
| Update status docs (`ACTIVE_WORK.md`, `PROJECT_STATUS.md`) after merges | Haiku | low | Templated edits from merged PR facts. |

### Rules for delegating to Haiku
- Give it the spec, the file to copy and the exact filtered test command. Do not ask it to choose a design.
- Review its output against the fixtures or the threshold table before anything is merged.
- Haiku work that touches evidence rules, the taste rule or the contract is out of scope; escalate it to Sonnet.
- Required CI on the exact PR head applies to every slice, whichever model wrote it.
