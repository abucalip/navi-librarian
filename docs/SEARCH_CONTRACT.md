# Global search and library browsing: API contract

Status: **revised after the second PR #608 review; pending re-review.** Not implemented. P1 does not start until this revision is approved. Per `PRODUCT.md`, no endpoint or field may be added without an approved contract; sections 3 to 6 are that contract.

## 1. Owner decisions (recorded)

| Topic | Decision |
|---|---|
| Discogs | Integrate, with a configuration page in Settings (section 3.5). Authentication is a **personal access token**. |
| Discogs caching | Private single-owner app, so the six-hour cap that applies to public apps does not apply. Standard cache TTLs (section 6). The owner confirmed the attribution wording "Data provided by Discogs" is still shown next to Discogs data. |
| Batch lookups | Use a batch request wherever a provider offers one, for every provider. Where none exists, coalesce concurrent identical requests and cache the results. |
| Latency | Per search, complete (or partial with status) within **4 seconds**. Measured as defined in section 2.1. |
| Provider budgets | No per-day ceiling. Providers limit per minute; the limiter queues and skips, it does not cap daily totals. |
| Cache | Required. The library is large. |
| Similar artists | Include ListenBrainz from the start. |
| Transport | SSE streaming. |
| Library page | Both a standalone library page and top-bar search. |
| Library size | **12,097 songs, 1,744 albums, 733 artists** (Navidrome counts; artists are whatever Navidrome returns). |
| Local MusicBrainz replication | Not now. Reopen only if measured search timings show the public API is the bottleneck. |

## 2. Constraints that shape the design

- **Rate limits decide the spine.** MusicBrainz allows an average of 1 request/second per source IP, with HTTP 503 when exceeded. Discogs is reported at 60 requests/minute authenticated (secondary sources; section 9). Inside the 3-second server deadline, MusicBrainz can answer only a few uncached requests. So MusicBrainz is used for identity resolution of the top candidates only, with long caching.
- **Owned results never wait on the network.** They come from the in-process owned index (section 4.1). Provider calls never run before owned results are emitted, and a slow provider never delays them.
- **Batch first.** Every provider call uses the batch path when the provider has one. Single-item calls are the fallback.
- **Index refresh never runs in a request.** Full index builds run in a background job. Requests read the last known-good index.
- **Deadline, not per-source timeouts alone.** Each search has one server-side deadline of **3.0 s**. Sources still running at the deadline are cancelled and reported as `timeout`.

### 2.1 Measurable targets

These are proposed acceptance targets. P1 and P5 measure them; none is claimed as met yet.

| Measure | Target | Notes |
|---|---|---|
| Time to first owned result, warm index, server | p95 ≤ 100 ms | Measured from request receipt to the first `result` event. |
| Time to first owned result, browser | p95 ≤ 250 ms | Includes rendering. Owned results are shown without waiting for any `source` event. |
| Time to first external result, cache miss | p95 ≤ 1.5 s | Measured from request receipt to the first external `result` event. |
| Terminal `done` event | ≤ 3.0 s server, always | Enforced by the deadline. |
| Browser-rendered complete results | ≤ 4.0 s | End-to-end, including network and rendering. |
| Cache hit, all sources | terminal `done` ≤ 300 ms | Every `source` event reports `cached`. |
| Index refresh | Background; target ≤ 10 s, measured in P1 | Never on the request path. The 1.8 s probe for song paging is a lower bound, not a build time. |
| Slow or unavailable provider | Reported `timeout` or `failed` at the deadline; other sources and owned results unaffected | Verified by a test with a stubbed slow provider. |
| Deadline expiry | `done` with `deadline_hit: true` within 3.0 s + 100 ms | Verified by a test. |

## 3. Endpoints

### 3.1 `GET /api/search`

Streams search results as Server-Sent Events. Owned results are emitted first.

Query parameters:

| Name | Type | Notes |
|---|---|---|
| `q` | string, 1–200 chars | Required. Normalized server-side (case, diacritics, leading "The"). |
| `types` | comma list of `artist`, `album`, `song`, `genre` | Default: all four. A type that is not available in this build is reported in `capabilities` (section 3.6). |
| `scope` | `owned` \| `all` | Default: `all`. `owned` skips all network sources. |
| `limit` | int, 1–50 | Per type, default 10. |

Events (each `data:` line is JSON):

- `event: capabilities` — always the first event. Lists the types and sources available in this build and their state (section 3.6).
- `event: result` — one entity.
  ```json
  {"type": "artist", "owned": true, "id": "...", "key": "beyonce",
   "name": "Beyoncé", "mbid": "…|null", "album_count": 12,
   "sources": ["navidrome", "musicbrainz"], "artwork_url": "…|null"}
  ```
  Album results add `"artist"`, `"artist_key"`, `"year"`, `"release_group_mbid"`. Song results add `"album"`, `"duration"`, `"track_number"`. Genre results add `"tag"` and `"tag_source"` (`musicbrainz`, `discogs`, `listenbrainz`).
  `owned` is `true` only when the match is confirmed by MBID or, failing that, by normalized name plus year. Otherwise it is `false`, and `"owned_candidates"` may list library keys that are close but not confirmed.
- `event: source` — status of one provider.
  ```json
  {"source": "lastfm", "state": "pending|done|failed|timeout|rate_limited|disabled|cached",
   "count": 7, "ms": 412}
  ```
- `event: done` — terminal event for a normally completed stream.
  ```json
  {"elapsed_ms": 2930, "deadline_hit": false, "partial": false}
  ```
- `event: error` — terminal event for a fatal failure after streaming started (section 3.7).

Caching: a fully cached query is emitted as normal events, with every `source` event set to `cached`.

Errors before streaming starts: `400` for a bad `q`, `types` or `scope`; `401` from the existing login middleware. An owned index that is not available is **not** an HTTP error. The stream starts, and the owned types are reported unavailable in `capabilities` (section 3.6), so provider results can still arrive (section 4.1).

### 3.2 `GET /api/library/artists`

Paged list of Navidrome artists, for the library page. Available in P1.

| Name | Type | Notes |
|---|---|---|
| `q` | string, optional | Same normalization as search. |
| `sort` | `name` \| `album_count` | Default `name`. |
| `cursor` | string, optional | Opaque; from the previous response. |
| `limit` | int, 1–200 | Default 60. |

Response:
```json
{"items": [{"id": "...", "key": "...", "name": "...", "album_count": 12,
            "artwork_url": "…|null"}],
 "next_cursor": "…|null", "total": 733, "index_state": "fresh|stale|building|unavailable",
 "snapshot_at": "2026-10-25T16:00:00Z"}
```

`index_state` values:

- `fresh`: the list comes from a completed build. A valid empty result is `fresh` with `total: 0`.
- `stale`: the last refresh failed; the list shows the last known-good data.
- `building`: the first build is running and no index exists yet. `items: []`, `total: null`.
- `unavailable`: the first build failed and no last-known-good index exists. `items: []`, `total: null`. The response is still HTTP 200, so the page can show a clear message and retry on the next refresh trigger.

`building` and `unavailable` are never reported as an empty library.

### 3.3 `GET /api/artists/{key}`

Artist page. `key` is the normalized artist key, with `?mbid=` optional to disambiguate.

Each section carries its own availability. Owned albums are available in P1. Missing albums are available from P2. Similar artists are available from P3. Bio is available where the existing bio service has one.

Response:
```json
{"artist": {"name": "...", "mbid": "…|null", "owned": true, "bio": "…|null"},
 "owned_albums": {"available": true, "items": [{"name": "...", "year": 2019, "song_count": 12, "album_key": "…"}]},
 "missing_albums": {"available": false, "reason": "not_in_this_build", "items": []},
 "similar": {"available": false, "reason": "not_in_this_build", "items": []},
 "sources": [{"source": "lastfm", "state": "done"}]}
```

When a section is `available: true` with `items: []`, that is a valid empty result. When `available: false`, the `reason` says why (`not_in_this_build`, `source_disabled`, `source_failed`). The frontend renders the two cases differently.

Missing-album items, from P2, include `release_group_mbid`, `popularity` and `sources`. Similar items, from P3, include `score` and `reasons`.

The artist page may stream. If `Accept: text/event-stream` is sent, the stream follows the same contract as search (section 3.7): it begins with exactly one `capabilities` event that uses the vocabulary in section 3.6, then emits one `section` event per section, then exactly one terminal `done` or `error`. Otherwise it returns one JSON document, from cache where possible, with the same `available`/`reason` fields in each section.

### 3.4 `GET /api/genres/{tag}`

Available from P4. Genre page: top owned and unowned artists and albums for a tag, with the tag's sources. Same section structure as 3.3, with `artists` and `albums` sections in place of `artist`.

### 3.5 Discogs settings

Available from P4. Mirrors the existing Last.fm settings contract (`app/api/settings.py`, `settings/service.py`), so the token is never returned to the browser. Authentication is a Discogs **personal access token** (decided by the owner). The OAuth consumer key and secret in `config.env` are not used by this integration.

- `GET /api/settings/discogs` → `{"token_configured": true|false, "source": "settings|environment|none"}`. The token value is never included.
- `PUT /api/settings/discogs` with `{"token": "..."}` → saves the token; an empty string clears it. Returns the same shape as GET. Saving a new token, replacing an existing one, or clearing it invalidates every Discogs cache entry (section 5.2).
- `POST /api/settings/discogs/test` → one lightweight authenticated request; returns `{"ok": true|false, "error": "..."}`.

The Settings page gets a Discogs section beside Last.fm and ListenBrainz: a password-type input, a configured/not-configured status line, Save, and Test. The token can also come from an environment variable, `DISCOGS_TOKEN`, following the existing `LASTFM_*` pattern. Discogs is disabled, and the search source reports `disabled`, until a token is configured.

### 3.6 Capabilities

The `capabilities` event (search) and the `reason` fields (artist page) use one vocabulary:

| Field | Values |
|---|---|
| `available` | `true` or `false` |
| `reason` | `not_in_this_build`, `source_disabled` (no token or key), `source_failed` (last attempt failed), `index_building` (first build running; no index yet), `index_unavailable` (first build failed; no last-known-good index) |

A capability that is not available is never reported as an empty list. The frontend shows a "not available yet" or "not configured" message for these, and "No matches" only for `available: true` with no items.

### 3.7 SSE stream semantics

Invariants, each covered by an automated test in the phase that introduces the stream (P1 for the owned-only stream, P2 for provider streams):

1. Every stream begins with exactly one `capabilities` event.
2. Owned `result` events are emitted before any provider `result` event.
3. A normally completed stream emits exactly one `done` event, as the last event.
4. A fatal error after the stream started emits one `error` event and closes. No `done` follows it.
5. A provider failure or timeout emits a `source` event with `failed` or `timeout`. It does not end the stream, and it does not discard results already emitted.
6. A provider that is timed out or cancelled emits no further `result` events. Results that arrive after cancellation are dropped on the server.
7. Shared provider work is reference-counted by its active consumers (streams). A client disconnect removes that client's reference. Provider work is cancelled only when its last consumer disconnects. A disconnect is detected on write, and no further events are written to that client.
8. Identical concurrent queries share one set of provider calls (request coalescing). Every consumer receives the same events from the shared work, and a consumer that joins later receives the events already emitted, followed by the rest.
9. Work that is cancelled, or that hits the deadline, is never written to the cache as a complete result. Only complete results from a finished call are cached.
10. The first event on any stream, whether search or artist page, is `capabilities`.

## 4. Search and matching

### 4.1 Owned index lifecycle

The owned index is a new package, `discovery/search/index.py`, that holds:

- **Artists and albums**: taken from the existing library snapshot (`discovery/library_snapshot.py`, which builds artist and album inventories and caches them for 10 minutes).
- **Songs**: loaded with paged Navidrome `search3`, using an empty `query`, `songCount=500` and increasing `songOffset`, until a short page is returned. A live probe on 2026-10-25 returned all 12,097 songs in 25 pages, about 1.8 s. Per-album `getAlbum` calls are not needed.

Lifecycle rules:

- **Build**: a background job assembles a new index object from the snapshot and the full song pages. It is never built inside a request.
- **Single flight**: one build runs at a time, guarded by one lock. A refresh requested while a build is running joins that build; it does not start a second full scan.
- **Atomic swap**: the new index replaces the current one only after a build completes. The build is complete only when every song page succeeded and the final page was short. A failed or incomplete build leaves the last known-good index in place and sets `index_state: "stale"`.
- **Sanity check**: a build whose song count falls by more than 10% from the last good index is rejected as suspicious and reported as stale. The threshold is a proposal to confirm in P1.
- **First build**: before the first successful build, a search stream starts normally. Owned types are reported in `capabilities` with `available: false, reason: "index_building"`, and provider results may still arrive. If the first build fails and no last-known-good index exists, owned types are reported with `reason: "index_unavailable"`, the error is logged, and the next refresh trigger retries the build. A search never returns `503` for this case. This contract defines no `503` for index failures.
- **Scope-owned search with no index**: the stream starts, owned types are unavailable as above, no provider calls are made, and the terminal `done` has `partial: true`.
- **Refresh trigger**: the index is rebuilt when the library snapshot is rebuilt (its 10-minute TTL), and by the existing manual refresh path. Navidrome settings changes trigger a rebuild.
- **Memory**: the index holds only normalized keys and display fields, which is small at 12,097 songs.

### 4.2 Matching and ranking

- **Identity**: MBID first, then normalized name plus year. Reuse `_discovery_is_various_artists` and exact artist-credit matching (DISC-05). "Various Artists" never becomes an artist result.
- **Dedupe**: entities are merged across sources by MBID, then by key plus year. Each result lists every source that contributed.
- **Ranking**: exact and prefix matches first, then owned before unowned for equal match quality, then the source count. The ranking is simple and documented, and it changes only with evidence.

## 5. Sources, roles and cache ownership

### 5.1 Sources

| Source | Used for | Limit | Notes |
|---|---|---|---|
| Navidrome | Owned artists, albums, songs | Local | Via existing `api_call`. |
| Last.fm | Fast text search, `getSimilar`, top albums, popularity | Documented per-second cap | Primary for bulk candidates. No batch method found. |
| ListenBrainz | Release-group popularity, artist metadata and popularity (batch), tag radio, similar artists | Per-minute header-driven (30 per window on `lb-radio`) | Batch forms in section 9. |
| MusicBrainz | MBIDs, release-groups, tags | Average 1 req/s per IP; HTTP 503 when exceeded | Identity for the top candidates only. Search batches of 100 terms. |
| Discogs | Styles and genres, release variants | 60 req/min authenticated (secondary sources) | New integration. Personal access token. No batch method found. |
| Deezer | Artwork, tracklists | Existing | Already integrated. |
| Wikidata | Bios, genre hierarchy | Existing | Already integrated. |

Each source has its own token bucket and concurrency cap in one limiter module. A request that cannot be served within the remaining deadline is not queued: the source is reported `rate_limited` and skipped.

### 5.2 Cache layers and ownership

Each layer has one owner and one invalidation rule. The existing persistence (`_discovery_read_list` / `_discovery_write_list`) is reused for every persistent layer. No new cache framework is introduced.

| Layer | Owner module | Storage | Key | Invalidation | Failure behavior |
|---|---|---|---|---|---|
| Library snapshot | `discovery/library_snapshot.py` | Persistent list store | `library_snapshot` | 10-minute TTL; Navidrome settings change | Keep the previous snapshot; do not write a partial one. |
| Owned index (artists, albums, songs) | `discovery/search/index.py` | Memory | Single index | Rebuilt with the snapshot; manual refresh | Keep last known-good index; set `stale`. Never swap in a partial build. |
| Provider query results | `discovery/search/cache.py` | Persistent list store | `search:{source}:{config_generation}:{normalized query}:{types}:depth{50}` | 24 h TTL; any credential or setting change bumps the source's `config_generation` (below) | Stores a complete result set at fixed depth 50 per type, independent of request `scope` and `limit`. `scope` and `limit` are applied per request after the cache read. Failures, timeouts and cancelled work are not cached. A 1 h negative entry is cached only for definitive empty answers. |
| Provider entity lookups (MBID) | the source's integration module | Persistent list store | `mbid:{source}:{mbid}` | 30-day TTL | Same as above. |
| Provider credentials and settings | `settings/service.py` | Existing settings store | Per-source `config_generation` counter | Every save that changes a credential (new token, replacement, clear) or a non-secret setting increments the counter. Old-generation entries become unreachable and are deleted in the background. | Tokens are never stored in cache keys, logs or responses. The counter is the only credential-derived value in a key. |
| Similar artists | `discovery/similar_artists.py` (precompute job) | Persistent list store | `similar:{artist_mbid}` | Daily precompute, same cadence as lens lists; 7-day TTL for on-demand entries | Keep the previous entry on a failed recompute. |
| Genre tag results | the genre module (P4) | Persistent list store | `genre:{source}:{tag}` | 7-day TTL | Same as provider results. |

`config_generation` is a per-source integer stored with that source's settings. It is incremented on every save that changes a credential or non-secret setting: setting a first token, replacing one non-empty token with another, or clearing a token. The increment, not a hash of the token, is what separates one credential's cache from another's, so no token-derived value is stored or logged. Entries under an old generation are never read again.

## 6. Caching TTLs (summary)

| Data | TTL |
|---|---|
| Library snapshot | 10 min |
| Text search results per source | 24 h |
| Negative search results (definitive empty only) | 1 h |
| MBID entity lookups | 30 days |
| Similar artists | 7 days; precomputed daily for library artists |
| Genre tag results | 7 days |
| Songs search (Navidrome, on-demand fallback only) | 10 min |

Cache misses and failures are never stored as hits. TTLs are fixed; a hit does not extend them.

## 7. Similar artists

Rank fusion across:
1. Last.fm `artist.getSimilar`.
2. ListenBrainz `/1/lb-radio/artist/{seed_artist_mbid}`. The Labs `similar-artists` route is undocumented and is not used. The seed artist appears in the response and is removed. One request per seed; no batch form.
3. Shared tags (MusicBrainz, plus Discogs styles), via `discovery/similar_artists.py`.
4. Owner listening: candidates the owner plays get a boost; owned candidates are moved to the owned list.

Each suggestion lists its `reasons`. ListenBrainz gives no similarity score, so its contribution uses result order. The library's artists are precomputed daily. Non-library artists are computed on demand and cached.

## 8. Module layout, rules and phase tests

- Routes: `app/api/search.py` (search, artists, genres) and `app/api/library.py` (library artists). Thin adapters only; they are registered in `app/main.py`.
- Logic: `discovery/search/` (index, cache, query normalization, merge and ranking, deadline runner, SSE event assembly) and `integrations/<source>/` clients for Discogs and any new calls. Direct-import tests for each.
- `navidrome_server.py`: no additions (D-016).
- Browser: top-bar search box with an accessible label; results grouped by type under "In your library" and "Not in your library"; streaming updates announced politely (`aria-live`); source status shown per provider. Logic stays server-side. Frontend work in a phase depends only on capabilities that phase delivers (section 3.6).

### 8.1 Tests required in each phase

Correctness tests land in the same PR as the code they cover.

| Phase | Required automated tests |
|---|---|
| P1 | Complete song retrieval and paging (including a short final page and an empty library); index build single flight; failed or incomplete build keeps the last good index; `stale`, `building` and `unavailable` states; first build failure with no last-known-good index reports `index_unavailable` in an HTTP 200 stream or response, never a `503` and never an empty library; `scope=owned` with no index emits a `done` with `partial: true` and makes no provider calls; owned identity and ownership matching, including false matches (same name, different MBID; Various Artists); `capabilities` event first; owned results before any provider event; library artist list paging and `index_state`. |
| P2 | Provider isolation (one failing provider does not affect others); cross-provider deduplication by MBID and by key plus year; MusicBrainz 503 backoff and retry; 100-term batching and paging; rate-limit skip (`rate_limited`); deadline expiry (`deadline_hit`); SSE invariants 3 to 10 (section 3.7); shared-work cancellation: one consumer disconnects while another continues, and the shared call is cancelled only when the last consumer disconnects; cancelled or deadline-expired work is not cached; provider cache stores depth 50 and serves smaller `limit` values by slicing; `scope=owned` never reads or writes the provider cache. |
| P3 | Seed artist exclusion from `lb-radio`; owned candidates moved to the owned list; ranking with no ListenBrainz score; precompute failure keeps the previous entry; `similar` section availability; artist-page stream begins with `capabilities`. |
| P4 | Discogs token handling (never in responses, logs or cache keys); first token set, token replacement (non-empty to different non-empty), and clear each bump `config_generation`, and old-generation entries are never read; attribution text present on every Discogs-sourced item; genre matching; `disabled` state without a token. |
| P5 | Latency measurements against section 2.1 targets, with results recorded in `PROJECT_LOG.md`; `TEST_PLAN.md` entries for each phase. |

## 9. Verification results and open items

Checked on 2026-10-25. Live results are authoritative; secondary sources are marked as such.

### Verified

- **Navidrome `search3` with an empty query and paging works.** A read-only probe of the owner's server returned 12,097 unique songs in 25 pages (`songCount=500`), about 1.8 s total.
- **Library counts.** Navidrome is the source of truth: `getArtists` returns **733** artists, and the owner confirmed the count is whatever Navidrome returns. Songs: 12,097. Albums: 1,744 (owner-supplied; not probed).
- **MusicBrainz rate limit and identification** ([MusicBrainz rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)). The official page sets an average of 1 request per second per source IP (300 requests/second global, anonymous agents about 50/second). Exceeding the limit returns HTTP 503 and every request is declined until the rate drops. Each request needs a User-Agent that identifies the app and a contact. The page does not address caching. It says high-volume commercial use should replicate the database locally, and it asks clients not to poll for metadata changes.
- **MusicBrainz OR-search size** (live, 2026-10-25). The limit is the request URL length, not the term count. 150 terms returned complete results (paged with `offset`); 160 terms returned HTTP 414 "URI Too Long"; 250 and 300 terms returned 414 and 431. **Decision: 100 terms per call**, about 1,800 characters under the first failure.
- **MusicBrainz 503s.** The public service returned HTTP 503 "web server is currently busy" several times during probes and cleared after backing off. Backoff and retry are required.
- **ListenBrainz `lb-radio/artist`** (live, 2026-10-25). `GET https://api.listenbrainz.org/1/lb-radio/artist/{seed_artist_mbid}` with `mode=easy&max_similar_artists=5&max_recordings_per_artist=1&pop_begin=0&pop_end=100` returned HTTP 200 with a JSON object keyed by artist MBID. Each value is a list of `{recording_mbid, similar_artist_mbid, similar_artist_name, total_listen_count}`. The seed is included. There is no similarity score. `max_similar_artists=5` returned six entries, so it is not an exact cap. Rate-limit headers: `X-RateLimit-Limit: 30`.

### Batch endpoints (checked 2026-10-25)

| Provider | Batch form | Status | Used for |
|---|---|---|---|
| ListenBrainz metadata | `GET /1/metadata/artist/?artist_mbids=a,b,c&inc=tag` | **Live 200**, 6 artists | Artist tags and identity for many artists per call. |
| ListenBrainz popularity | `POST /1/popularity/artist` with `{"artist_mbids": [...]}` | **Live 200**, 6 artists | Artist popularity for many artists per call. |
| ListenBrainz popularity (release-group) | `POST /1/popularity/release-group` | Already in use (`integrations/listenbrainz/popularity.py`) | Album popularity, chunked. |
| ListenBrainz recording and release-group metadata | `POST /1/metadata/recording/` (up to 100 MBIDs), `GET /1/metadata/release_group/` (up to 50 used; measured limit 80, fails at 81) | Already in use (`discovery/batch_metadata.py`) | Track and album metadata. |
| ListenBrainz metadata (artist, POST) | `POST /1/metadata/artist/` | **Live 405**: use GET | Not usable. |
| MusicBrainz search | `GET /ws/2/artist?query=arid:X OR arid:Y ...` | **Live 200** up to 150 terms | Batch identity resolution, 100 terms per call. |
| MusicBrainz lookup by ID | `GET /ws/2/artist/{mbid}` | Single ID only | Fallback. |
| Last.fm | None found | Single-artist `artist.getInfo` and similar methods | Coalesced and cached. Secondary sources only; official docs not readable. |
| Discogs | None found | One release or artist per call | Coalesced and cached. Secondary sources only; official docs not readable. |

### Partly verified

- **Discogs rate limits.** Secondary sources report 60 requests/minute authenticated and 25/minute unauthenticated ([Discogs-MCP PR #69](https://github.com/WOIII-me/Discogs-MCP/pull/69), [Sonovault](https://sonovault.now/resources/discogs-api-rate-limits)). Responses over the limit return 429.
- **Discogs caching and attribution (owner-confirmed).** The owner confirmed the attribution wording "Data provided by Discogs" is correct. The six-hour cap applies to public apps only. The official terms page was not readable by the agent.

### Decided

- **Discogs authentication:** personal access token, stored in settings or `DISCOGS_TOKEN` (section 3.5).
- **No local MusicBrainz replication** for now (section 1).

### Open

No open items in this section. The second re-review items are addressed in sections 3.1 (no `503` for owned-index failure), 3.2 (`index_state` values), 3.3 and 3.7 (artist-page stream and shared-work cancellation), 5.2 (cache keys and `config_generation`) and 8.1 (tests). Re-review is requested before P1 starts.

## 10. Phasing

- **P1**: owned search and library page, with the owned index lifecycle (section 4.1), the `capabilities` event, and no network sources. Ships first; no new provider risk. Owned types only; genre and external types report `not_in_this_build`.
- **P2**: MusicBrainz, Last.fm and ListenBrainz for not-owned artists and albums; deduplication; provider streaming; the deadline runner; missing-album sections on the artist page.
- **P3**: similar artists with fusion and daily precompute; the `similar` section.
- **P4**: Discogs integration, including the Settings page (section 3.5); genre pages.
- **P5**: consolidated integration and performance: latency measurement against section 2.1, and `TEST_PLAN.md` entries.

Each phase is a separate branch and PR from current `main`, with CI verified on the exact head before merging, and with the tests in section 8.1. Nothing in this plan is published or deployed.
