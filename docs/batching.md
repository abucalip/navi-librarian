# External-provider batching audit

Last reviewed: 2026-11-06  
Repository baseline: `main` at `ece37e085f1c77f0e26ab507cf25cad6e2326a21`.

## Purpose and scope

This document records where application services make one-entity-at-a-time requests to external providers, where the application already uses batch or paginated browse operations, and which opportunities are worth investigating. It is an audit, not an implementation plan approved for provider traffic.

The governing project rule is in [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md): every external-provider request must use a batch lookup whenever that provider offers one. A single lookup is acceptable only when no suitable batch form exists; the reason should be stated in the implementation review. Existing request budgets, pacing, cache behavior, failure handling, and owner approvals remain in force.

The audit reviewed the current GitHub source, including the discovery metadata pipeline, MusicBrainz and ListenBrainz integrations, metadata service modules, and Server V2 insight-provider runtime. Provider API claims below are checked against the providers' published documentation where available. A possible batch form is not considered production-ready until its response shape, completeness, limits, and semantic equivalence have been tested.

## Executive summary

There are two particularly useful MusicBrainz opportunities:

1. **Critical ratings:** the classics enrichment path can call the MusicBrainz release-group lookup separately for as many as 80 candidates. MusicBrainz supports browsing release groups by artist and supports `inc=ratings` on release groups. Grouping candidates by artist MBID should allow one paginated browse per artist to supply ratings for many candidate albums.
2. **Tracklists:** `MusicBrainzSearch.release_group_tracks()` currently performs two sequential requests for one release group: a release-group lookup to list releases, then a release lookup to retrieve recordings. The MusicBrainz release browse endpoint supports browsing releases by release-group MBID and including recordings. This may collapse the two requests into one browse page for many albums, subject to pagination and track-count limits.

Other notable conclusions:

- ListenBrainz batch metadata is already used for CF recording resolution and artist genre enrichment, with bounded chunks and individual MusicBrainz fallback where batch results are missing or the batch fails.
- Album-year lookup already has a batch implementation; list views should continue using it rather than issuing the single-album endpoint repeatedly.
- Server V2 has already moved series-relationship discovery from one release-group lookup per owned group to a paginated release-group browse per artist (PR #802).
- Several Apple Music, Deezer, Wikipedia, and review lookups are query-specific. This audit did not establish a provider-supported multi-album request that preserves the current exact-match behavior for those operations. Do not invent a batch endpoint or combine unrelated search queries without evidence.
- Navidrome ingestion performs an individual `getAlbum` call for each album stub. This is a separate first-party server API concern, not an external-provider lookup; investigate whether a list response contains enough fields before changing it.

## Findings

### 1. MusicBrainz critical ratings — strongest remaining opportunity

**Current implementation**

- [`discovery/classics_ratings.py`](../discovery/classics_ratings.py) sorts candidates by Last.fm listeners, selects up to 80, and calls the injected rating lookup once per candidate. The first 30 calls request year enrichment as well.
- [`integrations/musicbrainz/rating_client.py`](../integrations/musicbrainz/rating_client.py) calls `/ws/2/release-group/{mbid}?inc=ratings`, after checking a 180-day cache. Each uncached call pauses for 1.1 seconds.
- Therefore, the upper bound is 80 individual rating lookups per enrichment pass, but the actual number of external requests is lower when cache entries are fresh or candidates lack MBIDs.

**Batch form to investigate**

MusicBrainz documents browse requests of the form:

```text
GET /ws/2/release-group?artist={artist_mbid}&inc=ratings&limit=100&offset=0&fmt=json
```

Release groups can be browsed by artist MBID; browse requests support pagination up to 100 results; and `ratings` is a supported include for release-group entities. This allows the application to retrieve ratings for many release groups belonging to one artist in a request (or a small number of pages), then select only the release-group MBIDs in the classics shortlist.

**Recommended design**

1. Partition eligible shortlist candidates by valid artist MBID.
2. Read the existing per-release-group rating cache first.
3. Browse each artist's release groups with `inc=ratings`, paging until the response is complete or the configured page bound is reached.
4. Match returned release-group MBIDs to candidates; preserve the existing rating, vote-count, and first-release-year fields.
5. Populate the existing cache using the same key, TTL, and result shape as the individual lookup.
6. Retain the individual lookup only as a bounded fallback for candidates whose artist MBID is absent, whose group is not returned, or whose browse is incomplete/failed. Record the fallback reason and keep MusicBrainz pacing.
7. Avoid repeatedly browsing the same artist within one run; deduplicate artist IDs and share the result across candidates.

**Important constraints**

- A browse is per artist, not one universal request for all artists. The expected request count becomes approximately the number of distinct candidate artists (plus pages), rather than the number of candidate albums.
- An artist with a large discography may require multiple pages. A partial browse must not be treated as proof that a missing candidate has no rating.
- The response must be checked for the same rating value and vote count currently read from the release-group lookup.
- Keep the current 80-candidate shortlist, ordering, 30-year-enrichment limit, scoring semantics, cache semantics, and non-fatal provider behavior unchanged.
- Candidates without a usable artist MBID may still need the existing single lookup unless another reliable batch key is available.

**Priority: High.** This is the clearest remaining many-lookups-to-fewer-requests opportunity.

### 2. MusicBrainz tracklists — likely two-to-one request reduction

**Current implementation**

[`discovery/search/providers.py`](../discovery/search/providers.py), method `MusicBrainzSearch.release_group_tracks()`, currently:

1. Looks up `/release-group/{mbid}?inc=releases`.
2. Sorts the returned releases, preferring Official status and then the earliest date.
3. Looks up `/release/{release_mbid}?inc=recordings` for the selected release.
4. Extracts track titles and durations.

The method's docstring explicitly describes this as two requests.

**Batch/browse form to investigate**

MusicBrainz supports browsing releases by release-group MBID, and the release browse endpoint supports including recordings:

```text
GET /ws/2/release?release-group={release_group_mbid}&inc=recordings&limit=100&offset=0&fmt=json
```

This can return multiple releases with their media and recording data in a browse response. The application could select the preferred Official release from the returned release objects without first making a separate release-group lookup.

**Recommended design**

- Prototype the browse response against representative release groups (single release, multiple editions, multiple media, unofficial-only, and unusually large tracklists).
- Preserve the existing Official-first, earliest-date selection exactly.
- Parse the selected release's `media[].tracks[]` and durations from the browse result.
- Handle paging correctly. MusicBrainz notes that release browse pages are constrained by a 500-track response cap and may return fewer than the requested number of releases; offsets must advance by the number of releases actually returned, not blindly by the requested page size.
- If the preferred release is not present in the fetched page, continue paging within a strict bound. If completeness cannot be established, use the existing two-request path as a safe fallback.
- Compare the resulting ordered tracklist and durations with the current implementation before switching callers.

**Priority: Medium–high.** This is a strong per-album request reduction, but it is not a single bulk request covering many unrelated release groups.

### 3. ListenBrainz metadata batches — already implemented

[`discovery/batch_metadata.py`](../discovery/batch_metadata.py) implements three batch operations:

| Operation | Endpoint | Current chunk size |
|---|---|---:|
| Recording metadata | `/1/metadata/recording/` | 100 recording MBIDs |
| Release-group metadata | `/1/metadata/release_group/` | 50 release-group MBIDs |
| Artist genre tags | `/1/metadata/artist/` | 75 artist MBIDs |

[`discovery/candidate_gathering.py`](../discovery/candidate_gathering.py) uses the recording and release-group batches for CF candidate resolution. Batch misses or failed chunks fall back to bounded per-recording MusicBrainz resolution. Artist genre prefetch fills the cache in batches; any artists still missing from cache may be resolved individually through MusicBrainz.

The batch response does not contain every field available from a full MusicBrainz recording lookup (notably secondary release types). The implementation therefore has a title-marker safeguard and keeps the batch cache separate from the full recording cache. Do not remove those safeguards merely to increase batch hit rate.

**Assessment: Already batched, with intentional fallbacks.** Preserve chunk limits, cache separation, response-shape assumptions, failure handling, and fallback budgets. Re-test the live response contract before changing chunk sizes.

### 4. MusicBrainz album years — already batched for list workloads

[`integrations/musicbrainz/album_year.py`](../integrations/musicbrainz/album_year.py) provides both:

- `lookup_album_year()`: a single artist/album search.
- `lookup_album_years()`: a multi-pair lookup that ORs up to 15 artist/album pairs per query, uses a 100-result cap, and recursively splits result-capped chunks to avoid treating incomplete results as complete.

The batch helper preserves exact title and artist-credit matching and uses the shared cache and MusicBrainz pacing lock. The API also exposes a list-oriented `/api/album-years` path; list callers should use that route rather than calling the single-album route in a loop.

**Assessment: Existing batch path is the preferred implementation.** Keep the single-item path for genuine one-album requests, not as the implementation behind a list loop.

### 5. Server V2 insight providers — mixed, mostly entity-scoped

Current implementation is in [`intelligence/insights/provider_runtime.py`](../intelligence/insights/provider_runtime.py) and [`intelligence/insights/set_fetchers.py`](../intelligence/insights/set_fetchers.py).

| Operation | Current request shape | Assessment |
|---|---|---|
| MusicBrainz release-to-release-group linking | Paged `/release?artist=…&inc=release-groups` browse per artist | Batched/paginated by artist |
| MusicBrainz studio discography | Paged `/release-group?artist=…` browse per artist | Batched/paginated by artist |
| MusicBrainz series relationships | Paged `/release-group?artist=…&inc=series-rels` browse per artist | Batched/paginated by artist; PR #802 replaced per-owned-group lookups |
| MusicBrainz artist life-span | `/artist/{mbid}` lookup per artist | Artist-specific lookup; no multi-MBID lookup established |
| ListenBrainz top release groups | `/1/popularity/top-release-groups-for-artist/{mbid}` per artist | Artist-specific endpoint; no multi-artist form established |
| MusicBrainz series details | `/series/{mbid}` lookup per discovered series | Series-specific lookup; no multi-series form established |

The series relationship change is already on `main`: PR [#802](https://github.com/abucalip/navi-librarian/pull/802), commit `0561eb5e7f3612df12c9ec97e557f6c58764fdda`. It replaced one lookup per owned release group with a paginated release-group browse per owned artist. The current runtime's `_artist_series()` follows that design.

Do not label every entity-specific request a batching defect. A provider may expose a browse endpoint only when the relationship MBID is known, or the operation may genuinely be scoped to one artist/series. Revisit only when the provider documents a suitable multi-entity form or when a different existing response already contains the needed data.

### 6. Album links, descriptions, reviews, and artwork — no general bulk endpoint established

The metadata service layer contains per-album or per-query enrichment for Apple Music, Deezer, Wikipedia, and review sources. Relevant modules include:

- [`app/services/album_links.py`](../app/services/album_links.py)
- [`app/services/album_reviews.py`](../app/services/album_reviews.py)
- [`app/services/album_wikipedia.py`](../app/services/album_wikipedia.py)
- [`app/services/apple_description.py`](../app/services/apple_description.py)
- [`app/services/deezer_album_details.py`](../app/services/deezer_album_details.py)
- [`app/services/deezer_album_matching.py`](../app/services/deezer_album_matching.py)
- [`app/services/deezer_artwork.py`](../app/services/deezer_artwork.py)
- [`app/services/fallback_artwork.py`](../app/services/fallback_artwork.py)
- [`app/services/artist_bio.py`](../app/services/artist_bio.py)
- [`app/services/persistent_metadata.py`](../app/services/persistent_metadata.py)

These services perform text searches or retrieve a selected entity/page, often with exact-match filtering. This audit did not verify a provider-supported multi-album operation that can replace those searches while preserving the current matching and editorial semantics.

Apple's iTunes Search API has lookup forms that accept multiple known catalog IDs, but that is not equivalent to searching arbitrary album/artist text in bulk. It may be useful after a stable Apple catalog ID has already been resolved and stored; it does not remove the initial text-search requirement for albums without IDs.

**Assessment: Investigate selectively, not a blanket refactor.** Check provider documentation for the exact endpoint used, distinguish search from lookup, and do not assume that a multi-ID lookup can replace multiple text searches. Persistent caching, request coalescing, and avoiding duplicate concurrent searches may offer more reliable wins than speculative batching.

### 7. Navidrome insight ingestion — separate first-party API opportunity

[`app/services/insights_refresh.py`](../app/services/insights_refresh.py), function `_ingest_step()`, currently:

1. Calls `getArtists` to obtain artists.
2. Calls `getArtist` for each due artist to obtain album stubs.
3. Calls `getAlbum` once per album stub to retrieve the full album data used by ingestion.

This is not an external metadata-provider request, so it is outside the strict provider batching rule. It may nevertheless be a significant request-count and refresh-time opportunity.

Investigate whether Navidrome's `getAlbumList2` (or another supported list endpoint) can provide all fields required by `ingest_album()` for a given artist or library slice. Do not replace `getAlbum` unless the list response is demonstrably equivalent for MBIDs, artist credits, dates, genres, track counts, and other consumed fields. If full album detail remains unique to `getAlbum`, retain the individual calls and rely on the existing per-artist refresh cadence/cache.

**Priority: Medium, separate investigation.**

## Prioritized follow-up

| Priority | Work | Expected benefit | Main risk / proof required |
|---|---|---|---|
| 1 | Batch classics ratings by artist browse | Replace up to 80 uncached release-group lookups with one or more pages per distinct artist | Confirm `inc=ratings` response shape, full pagination, exact cache parity and missing-MBID fallback |
| 2 | Browse releases with recordings for tracklists | Potentially reduce two sequential MusicBrainz calls to one or more browse pages per release group | Preserve Official-first selection, multi-disc tracks, ordering, duration and page completeness |
| 3 | Navidrome ingestion inventory | Potentially avoid one `getAlbum` call per album | Prove list endpoint supplies every consumed field; first-party API, not external provider |
| 4 | Metadata search coalescing/caching audit | Avoid duplicate concurrent Apple/Deezer/Wikipedia/review queries | Measure duplicate requests and confirm provider terms; no bulk API assumed |
| 5 | Recheck artist/series provider calls | Keep only genuine entity-scoped lookups | Require authoritative documentation of a multi-entity alternative before changing |

## Acceptance criteria for future batching changes

A batching implementation should not be considered complete until it:

1. Uses a documented provider batch or browse operation, with a link to the provider documentation in the PR.
2. Deduplicates input identifiers and respects provider chunk, URL-length, result-count, pagination, and rate-limit constraints.
3. Handles missing IDs, partial pages, capped responses, missing entities, and per-chunk failures without treating incomplete results as authoritative absence.
4. Preserves existing matching semantics, field meanings, output ordering, cache keys/TTLs where appropriate, and public API response shapes.
5. Retains a bounded single-lookup fallback only where needed and explains why the fallback cannot use the batch form.
6. Adds regression tests for both successful batch responses and unsafe/incomplete/failure cases, including proof that N inputs produce the expected bounded number of provider calls.
7. Records request counts before and after using the same fixture or provider tape. Do not claim a speedup from code structure alone.
8. Preserves provider budgets, pacing, circuit breakers, retries, credentials handling, and explicit owner approval for live traffic.
9. Updates this document when a new provider batch path is implemented or when a documented provider capability changes.

## Provider documentation

- [MusicBrainz Web Service API](https://musicbrainz.org/doc/MusicBrainz_API) — lookup, browse, supported relationships, `inc=` values, ratings, and paging. In particular, it documents browsing release groups by artist, browsing releases by release group, ratings as an include for release-group entities, and the 100-result browse limit.
- [MusicBrainz API examples](https://musicbrainz.org/doc/MusicBrainz_API/Examples) — examples of release-group lookups and included releases.
- [MusicBrainz Search API](https://musicbrainz.org/doc/MusicBrainz_API/Search) — query search and result limits; search is distinct from browse.
- [Apple iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — search and multi-ID lookup behavior. Multi-ID lookup requires known catalog IDs; it is not a general multi-query text-search endpoint.
- [ListenBrainz API documentation](https://listenbrainz.readthedocs.io/) — provider API reference; the repository's live batch endpoint contracts and chunk limits are additionally captured in `discovery/batch_metadata.py`.

---

This document records opportunities, not permission to increase live provider traffic. Implementations must continue to follow the provider request budgets and approval rules in [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).
