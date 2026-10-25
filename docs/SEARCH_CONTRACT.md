# Global search and library browsing: API contract proposal

Status: **approved by the owner; finalized; pending review before implementation.** Not implemented. P1 does not start until this document is reviewed. Per `PRODUCT.md`, no endpoint or field may be added without an approved contract; sections 3–5 are that contract.

## 1. Owner decisions (recorded)

| Topic | Decision |
|---|---|
| Discogs | Integrate, with a configuration page in Settings (section 3.5). Authentication is a **personal access token**. |
| Discogs caching | Private single-owner app, so the six-hour cap that applies to public apps does not apply. Standard cache TTLs (section 6). The owner confirmed the attribution wording "Data provided by Discogs" is still shown next to Discogs data. |
| Batch lookups | Use a batch request wherever a provider offers one, for every provider. Where none exists, coalesce concurrent identical requests and cache the results (section 2). |
| Latency | Per search, complete (or partial with status) within **4 seconds**. |
| Provider budgets | No per-day ceiling. Providers limit per minute; the limiter queues and skips, it does not cap daily totals. |
| Cache | Required. The library is large. |
| Similar artists | Include ListenBrainz from the start. |
| Transport | SSE streaming. |
| Library page | Both a standalone library page and top-bar search. |
| Library size | **12,000 songs in 1,744 albums.** Artist count not yet supplied (see section 9). |

## 2. Constraints that shape the design

- **Rate limits decide the spine.** MusicBrainz allows an average of 1 request/second per source IP, with a 503 when exceeded. Discogs is reported at 60 requests/minute authenticated and 25/minute unauthenticated (secondary sources only; see section 9). Inside a 4-second window MusicBrainz can answer only about 3 uncached requests. So MusicBrainz is used for identity resolution of the top few candidates only, and its answers are cached for a long time. Bulk discovery depends on Last.fm, ListenBrainz and Discogs, and on the cache.
- **Owned results never wait on the network.** They come from the in-process index built from `discovery/library_snapshot.py`.
- **Batch first.** Every provider call goes through the batch path when the provider has one: one request for many IDs, or one request for many queries. Single-item calls are the fallback. Batching reduces requests per minute, which is the constraint that matters most here.
- **The whole song library fits in memory.** At 12,000 songs and 1,744 albums, an in-memory song index is small. It is rebuilt with the library snapshot, not queried per keystroke.
- **Deadline, not per-source timeouts alone.** Each search has one server-side deadline of **3.0 s** (1 s headroom for network and rendering). Sources still running at the deadline are cancelled and reported as `timeout`.

## 3. Endpoints

### 3.1 `GET /api/search`

Streams search results as Server-Sent Events. Owned results are emitted first.

Query parameters:

| Name | Type | Notes |
|---|---|---|
| `q` | string, 1–200 chars | Required. Normalized server-side (case, diacritics, leading "The"). |
| `types` | comma list of `artist`, `album`, `song`, `genre` | Default: all four. |
| `scope` | `owned` \| `all` | Default: `all`. `owned` skips all network sources. |
| `limit` | int, 1–50 | Per type, default 10. |

Events (each `data:` line is JSON):

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
- `event: done` — terminal event, always sent.
  ```json
  {"elapsed_ms": 2930, "deadline_hit": false, "partial": false}
  ```
- `event: error` — the search itself failed (for example, Navidrome unreachable). The stream then closes.

Caching: a fully cached query is emitted as normal events, with every `source` event set to `cached`. The response is not buffered.

Errors before streaming starts: `400` for a bad `q`, `types` or `scope`; `401` from the existing login middleware.

### 3.2 `GET /api/library/artists`

Paged list of Navidrome artists, for the library page.

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
 "next_cursor": "…|null", "total": 1234, "snapshot_at": "2026-10-25T16:00:00Z"}
```

### 3.3 `GET /api/artists/{key}`

Artist page. `key` is the normalized artist key, with `?mbid=` optional to disambiguate.

Response:
```json
{"artist": {"name": "...", "mbid": "…|null", "owned": true, "bio": "…|null"},
 "owned_albums": [{"name": "...", "year": 2019, "song_count": 12, "album_key": "…"}],
 "missing_albums": [{"name": "...", "year": 2021, "release_group_mbid": "…",
                     "popularity": 0.7, "sources": ["musicbrainz", "lastfm"]}],
 "similar": [{"name": "...", "key": "…", "owned": false, "score": 0.82,
              "reasons": ["lastfm", "tags"]}],
 "sources": [{"source": "lastfm", "state": "done"}]}
```

The artist page may also stream. If `Accept: text/event-stream` is sent, the same data is emitted in parts: `artist`, `owned_albums`, `missing_albums`, `similar`, then `done`. Otherwise it returns one JSON document, from cache where possible.

### 3.4 `GET /api/genres/{tag}`

Genre page: top owned and unowned artists and albums for a tag, with the tag's sources. Same response shape as 3.3, with `artists` and `albums` lists in place of `artist`.

### 3.5 Discogs settings

Mirrors the existing Last.fm settings contract (`app/api/settings.py`, `settings/service.py`), so the token is never returned to the browser. Authentication is a Discogs **personal access token** (decided by the owner). The OAuth consumer key and secret in `config.env` are not used by this integration.

- `GET /api/settings/discogs` → `{"token_configured": true|false, "source": "settings|environment|none"}`. The token value is never included.
- `PUT /api/settings/discogs` with `{"token": "..."}` → saves the token; an empty string clears it. Returns the same shape as GET.
- `POST /api/settings/discogs/test` → one lightweight authenticated request; returns `{"ok": true|false, "error": "..."}`.

The Settings page gets a Discogs section beside Last.fm and ListenBrainz: a password-type input, a configured/not-configured status line, Save, and Test. The token can also come from an environment variable, `DISCOGS_TOKEN`, following the existing `LASTFM_*` pattern. Discogs is disabled, and the search source reports `disabled`, until a token is configured.

## 4. Search and matching

- **Owned index**: built from the library snapshot, refreshed on its 10-minute TTL. Keys use `_music_key`. Songs are indexed in memory. They are loaded with paged `search3` using an empty `query`, `songCount=500` and increasing `songOffset`. A live read-only probe on 2026-10-25 returned all 12,097 songs unique in 25 pages, about 1.8 s total, so per-album `getAlbum` calls are not needed. The index is built on refresh and kept in memory; no per-query Navidrome calls for songs.
- **Identity**: MBID first, then normalized name plus year. Reuse `_discovery_is_various_artists` and exact artist-credit matching (DISC-05). "Various Artists" never becomes an artist result.
- **Dedupe**: entities are merged across sources by MBID, then by key plus year. Each result lists every source that contributed.
- **Ranking**: exact and prefix matches first, then owned before unowned for equal match quality, then the source count. The ranking is simple and documented, and it is changed only with evidence.

## 5. Sources and roles

| Source | Used for | Limit (to verify) | Notes |
|---|---|---|---|
| Navidrome | Owned artists, albums, songs | Local | Via existing `api_call`. |
| Last.fm | Fast text search, `getSimilar`, top albums, popularity | Documented per-second cap | Primary for bulk candidates. |
| ListenBrainz | Release-group popularity, tag radio, similarity | Per-minute header-driven | Popularity already implemented in `integrations/listenbrainz/popularity.py`. |
| MusicBrainz | MBIDs, release-groups, tags | About 1 req/s | Identity for the top candidates only; long cache. |
| Discogs | Styles and genres, release variants | 60 req/min authenticated (secondary sources) | New integration. Personal access token in settings. No batch endpoint is known; requests are coalesced and cached. |
| Deezer | Artwork, tracklists | Existing | Already integrated. |
| Wikidata | Bios, genre hierarchy | Existing | Already integrated. |

Each source has its own token bucket and concurrency cap in one limiter module. A request that cannot be served within the remaining deadline is not queued: the source is reported `rate_limited` and skipped.

## 6. Caching

| Data | Key | TTL |
|---|---|---|
| Owned index | snapshot | 10 min (existing) |
| Text search results per source | source + normalized query + types | 24 h |
| Negative search results | same | 1 h |
| MBID entity lookups | source + MBID | 30 days |
| Similar artists | artist key or MBID | 7 days; precomputed daily for library artists |
| Genre tag results | source + tag | 7 days |
| Songs search (Navidrome) | normalized query | 10 min |

Storage uses the existing persistent list store (`_discovery_read_list` / `_discovery_write_list`). Cache misses and failures are not cached as hits. Repeated hits extend nothing; TTLs are fixed.

## 7. Similar artists

Rank fusion across:
1. Last.fm `artist.getSimilar`.
2. ListenBrainz similar artists: the documented route is `/1/lb-radio/artist/{seed_artist_mbid}` (section 9). The Labs `similar-artists` route is undocumented and is not used.
3. Shared tags (MusicBrainz, plus Discogs styles), via `discovery/similar_artists.py`.
4. Owner listening: candidates the owner plays get a boost; owned candidates are moved to the owned list.

Each suggestion lists its `reasons`. The library's artists are precomputed daily, on the same cadence as the lens lists. Non-library artists are computed on demand and cached.

## 8. Module layout and rules

- Routes: `app/api/search.py` (search, artists, genres) and `app/api/library.py` (library artists). Thin adapters only; they are registered in `app/main.py`.
- Logic: a new package `discovery/search/` (index, query normalization, merge and ranking, deadline runner) and `integrations/<source>/` clients for Discogs and any new calls. Direct-import tests for each.
- `navidrome_server.py`: no additions (D-016).
- Browser: top-bar search box with an accessible label; results grouped by type under "In your library" and "Not in your library"; streaming updates announced politely (`aria-live`); source status shown per provider. Logic stays server-side.

## 9. Verification results and open items

Checked on 2026-10-25. Live results are authoritative; secondary sources are marked as such.

### Verified

- **Navidrome `search3` with an empty query and paging works.** A read-only probe of the owner's server returned 12,097 unique songs in 25 pages (`songCount=500`), about 1.8 s total. Songs, and whole-library song checks, can use this path.
- **Library counts.** Navidrome is the source of truth: `getArtists` returns **733** artists, and the owner confirmed the count is whatever Navidrome returns. Songs: 12,097. Albums: 1,744 (owner-supplied; not probed).
- **MusicBrainz rate limit and identification** ([MusicBrainz rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)). The official page sets an average of 1 request per second per source IP (300 requests/second global, anonymous agents about 50/second). Exceeding the limit returns HTTP 503 and every request is declined until the rate drops. Each request needs a User-Agent that identifies the app and a contact. The page does not address caching. It says high-volume commercial use should replicate the database locally, and it asks clients not to poll for metadata changes.

### Partly verified

- **Discogs rate limits.** Secondary sources report 60 requests/minute authenticated and 25/minute unauthenticated ([Discogs-MCP PR #69](https://github.com/WOIII-me/Discogs-MCP/pull/69), [Sonovault](https://sonovault.now/resources/discogs-api-rate-limits)). Responses over the limit return 429.
- **Discogs caching and attribution (owner-confirmed).** The owner confirmed the attribution wording "Data provided by Discogs" is correct. The six-hour cache cap applies to public apps only; this app is private and single-owner, so the standard TTLs in section 6 apply. The official terms page was still not readable by the agent, so the owner's reading is the basis for this.
- **ListenBrainz similar artists (live check, 2026-10-25).** `GET https://api.listenbrainz.org/1/lb-radio/artist/{seed_artist_mbid}` with `mode=easy&max_similar_artists=5&max_recordings_per_artist=1&pop_begin=0&pop_end=100` returned HTTP 200 with a JSON object keyed by artist MBID. Each value is a list of `{recording_mbid, similar_artist_mbid, similar_artist_name, total_listen_count}`. The seed artist is included in the result, so it must be filtered out. The response has **no similarity score**; ranking must use the order of the results or a score computed from the other sources. `max_similar_artists=5` returned six entries, so the parameter is not an exact cap. The response carries rate-limit headers, `X-RateLimit-Limit: 30` and `X-RateLimit-Reset-In`. This is one request per seed artist; no batch form was seen. The Labs `similar-artists/json` route is undocumented and is not used.

### Decided

- **Discogs authentication:** personal access token, stored in settings or `DISCOGS_TOKEN` (section 3.5).

### Batch endpoints (checked 2026-10-25)

| Provider | Batch form | Status | Used for |
|---|---|---|---|
| ListenBrainz metadata | `GET /1/metadata/artist/?artist_mbids=a,b,c&inc=tag` | **Live 200**, 6 artists, list response with `artist_mbid`, `name`, `tag`, `area`, `rels`, `type` | Artist tags and identity for many artists per call. |
| ListenBrainz popularity | `POST /1/popularity/artist` with `{"artist_mbids": [...]}` | **Live 200**, 6 artists | Artist popularity for many artists per call. |
| ListenBrainz popularity (release-group) | `POST /1/popularity/release-group` | Already in use (`integrations/listenbrainz/popularity.py`) | Album popularity, chunked. |
| ListenBrainz recording and release-group metadata | `POST /1/metadata/recording/` (up to 100 MBIDs), `GET /1/metadata/release_group/` (up to 50 used; measured limit 80, fails at 81) | Already in use (`discovery/batch_metadata.py`), measured in the repo | Track and album metadata. |
| ListenBrainz metadata (artist, POST) | `POST /1/metadata/artist/` | **Live 405**: use GET | Not usable. |
| MusicBrainz search | `GET /ws/2/artist?query=arid:X OR arid:Y ...` | **Live 200** up to 150 terms; **HTTP 414** from 160 terms (see below) | Batch identity resolution. Use **100 terms per call**, paging results with `limit=100` and `offset`. |
| MusicBrainz lookup by ID | `GET /ws/2/artist/{mbid}` | Single ID only | Fallback. |
| Last.fm | None found | Single-artist `artist.getInfo` and similar methods only | Requests are coalesced and cached. Third-party sources only; the official docs were not readable. |
| Discogs | None found | One release or artist per call | Requests are coalesced and cached. Third-party sources only; the official docs were not readable. |

Notes from the live checks:
- MusicBrainz rate limits are returned as headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`). The search endpoint limit was 400 per window and the lookup endpoint 1,900, so the search batch is the cheaper path. The public site also returned HTTP 503 "web server is currently busy" under global load. The app must treat that as retryable with backoff, not as a missing result.
- ListenBrainz `lb-radio/artist` takes one seed per call (section 9, above). It has no batch form.

### MusicBrainz OR-search size (checked 2026-10-25)

The limit is the **URL length**, not the term count. Results were complete (every requested MBID returned) at every size tested:

| Terms | Request URL length | Result |
|---|---|---|
| 5 | about 300 chars | 200, complete |
| 10 | about 530 chars | 200, complete |
| 25 | about 1,230 chars | 200, complete |
| 50 | about 2,410 chars | 200, complete |
| 75 | about 3,580 chars | 200, complete |
| 100 | about 4,760 chars | 200, complete |
| 150 | about 6,850 chars | 200, complete (paged with `offset`) |
| 160 | about 7,580 chars | **HTTP 414 URI Too Long** |
| 175 to 225 | 8,280 to 10,630 chars | 414 |
| 250 and 300 | 11,800 to 14,170 chars | 414 and 431 Request Header Fields Too Large |

**Decision: 100 terms per call.** It stays about 1,800 characters under the first failure, and it is a round number that matches `limit=100`. Results over 100 are paged with `offset`. If the largest accepted URL length changes on the server, this margin absorbs it.

Also observed: MusicBrainz returned HTTP 503 ("web server is currently busy") several times across these probes, and it cleared after backing off. Backoff and retry are required for every MusicBrainz call.

### Open

1. **MusicBrainz local replication.** At the current scale rate limits are the constraint. If bulk MusicBrainz use grows, the public service will not be enough.

## 10. Phasing

- **P1**: owned search and library page, with the in-memory song index and no network sources. Ships first; no new provider risk.
- **P2**: MusicBrainz, Last.fm and ListenBrainz for not-owned artists and albums; dedupe; streaming; deadline runner.
- **P3**: similar artists with fusion and daily precompute.
- **P4**: Discogs integration, including the Settings page (section 3.5), then genre pages.
- **P5**: fixture tests for dedupe and false matches, latency measurements against the 4-second target, and `TEST_PLAN.md` entries.

Each phase is a separate branch and PR from current `main`, with CI verified on the exact head before merging. Nothing in this plan is published or deployed.
