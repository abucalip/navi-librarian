# Album paths proposal

**Status:** proposal, not approved for build. Nothing here is implemented, tested, merged or published.
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
- **Same Room:** recording place and date links (listed in `not_loaded`).
- **Studio Crew:** production-credit relations at recording scope, if the current slice keeps only album-scope ones.
- **Covers and Sources:** work-to-work relations, if not currently imported.

A new slice follows the Phase 7 release-links precedent: a bounded, resumable import step, a schema bump, and the path cache invalidated through the slice's data version. `not_loaded` stays accurate until it lands.

## API and client shape (proposed, for review)

- Extend `GET /api/knowledge/paths` to accept `type=release` or `release_group` with the new `kind` values, or add `GET /api/knowledge/album-paths`. Prefer extending, so clients reuse the existing decoder; owner to decide.
- `GET /api/knowledge/paths/warm` is per owned artist today; album paths are cheaper to build on demand and probably need no warm-up. Confirm after the probe's timings.
- Clients hide the Paths button when the album has no kind with stops, and show Neighbours by Ear only when `sonic_available`.
- Album paths must not list the artist's own paths again; the button lists only the album kinds.

## Open decisions for the owner

1. Extend the existing paths route or add a separate album route.
2. ~~The "enough data" thresholds for the probe.~~ Decided 2026-11-09 (Balanced; see Probe plan).
3. Whether play-history filtering (path 9) is acceptable under the taste rule, with the constraint above.
4. Whether a stop that is also an artist-path stop is dropped or kept when its reason differs.
5. Whether Neighbours by Ear sits in the same list as the credit-based paths or in a separate sonic section.

## Next steps

1. Owner reviews this proposal and answers the open decisions.
2. Write the probe (`scripts/album_path_coverage.py`, filtered tests) and run it on a copy of the real store.
3. Record results in this document; keep, cut or add a slice per path.
4. Contract, builders, fixtures, then clients, each as its own slice with filtered tests and required CI.

## Work split by model and effort

For usage efficiency, give Haiku the mechanical, self-checking steps: a spelled-out spec, an existing pattern to copy, and a test or diff that proves the result. Keep design, evidence rules and judgment on a stronger model. Effort is relative to the model's default. These are planning estimates, not measurements.

| Step | Model | Effort | Why |
|---|---|---|---|
| Copy the real store and run the probe script | Haiku | low | Mechanical; output is numbers. |
| Write the probe measurements for paths 1, 2, 4 (counts, coverage, stop distribution, timing) | Haiku | low | Queries are fully specified above and copy `path_coverage.py`. |
| Probe overlap with the artist's five kinds, and the label-only share for path 6 | Sonnet | medium | Needs care to compare stops correctly; a wrong join gives plausible but wrong numbers. |
| Probe for Same Room and Covers and Sources (place and work link coverage) | Haiku | low | Counting queries against known tables. |
| Probe for Neighbours by Ear (analysed tracks, call cost) | Haiku | low | Calls the live sonic routes and counts. |
| Fill the results table in this document and apply the thresholds | Haiku | low | Compare numbers to the fixed table; no judgment, and a non-passing path is flagged, not argued. |
| Decide keep, cut or add a slice per path | Owner / main model | high | Judgment against thresholds, with a decision recorded. |
| Set the Neighbours by Ear call cap | Owner | — | Decided: 8 seeds per album (2026-11-09). |
| New import slice (recording places, production credits, work relations) | Sonnet | high | Schema bump, resumable import, cache invalidation; follows the release-links precedent. |
| Path builders for Studio Crew, Guest List, Covers and Sources | Sonnet | high | Evidence rules, hub caps, de-duplication of people across paths; a mistake breaks the credit-grade guarantee. |
| Same Year Same Scene builder | Sonnet | medium | Strict-rule logic on top of existing readers. |
| Neighbours by Ear composition | Sonnet | medium | Groups similar-track results; must never sort or threshold on `similarity`. |
| Listen-through Gaps filter | Sonnet | high | Must stay within the taste rule; a leak into ranking is a contract violation. |
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
