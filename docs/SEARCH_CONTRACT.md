# Global search and library browsing: API contract

Status: **approved by the owner** (2026-10-25). **P1–P4 are implemented and merged (P4 record: section 13)**: P1 PRs #609–#612, P2 PRs #613–#620, P3/P3b PRs #621–#622, and P4 PRs #623–#625. **Section 14 (library pages and album page) is merged in PR #630.** **The P5 measurement harness is merged in PR #626**; exploratory results are in `PROJECT_LOG.md`, but repeat measurements with the corrected harness are required before final performance conclusions. P5 covers integration and performance verification against section 2.1 targets. Section 11 remains the P1 record and section 12 the P2 record. Historical per-phase notes below are preserved as written.

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
| Library size | **12,097 songs and 733 artists** (Navidrome counts; artists are whatever Navidrome returns), **1,744 albums** (owner-supplied, not probed). |
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
| Terminal `done` event | sent within 3.0 s of request receipt (the deadline), plus at most 100 ms of write latency | Enforced by the deadline. |
| Browser-rendered complete results | ≤ 4.0 s | End-to-end, including network and rendering. |
| Cache hit, all sources | terminal `done` ≤ 300 ms | Every `source` event reports `cached`. |
| Index refresh | Background; target ≤ 10 s, measured in P1 | Never on the request path. The 1.8 s probe for song paging is a lower bound, not a build time. |
| Slow or unavailable provider | Reported `timeout` or `failed` at the deadline; other sources and owned results unaffected | Verified by a test with a stubbed slow provider. |
| Deadline expiry | `done` with `deadline_hit: true`, sent within 3.0 s + 100 ms of request receipt | Verified by a test. |

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

- `event: capabilities` — always the first event. Lists the types, sources and owned-index state, each with availability and reason (schema in section 3.8).
- `event: result` — one entity.
  ```json
  {"type": "artist", "owned": true, "id": "...", "key": "beyonce",
   "name": "Beyoncé", "mbid": "…|null", "album_count": 12,
   "sources": ["navidrome", "musicbrainz"], "artwork_url": "…|null"}
  ```
  Album results add `"artist"`, `"artist_key"`, `"year"`, `"release_group_mbid"`. Song results add `"album"`, `"duration"`, `"track_number"`. Genre results add `"tag"` and `"tag_source"` (`musicbrainz`, `discogs`, `listenbrainz`).
  `owned` is `true` only when the match is confirmed by MBID or, failing that, by normalized name plus year. Otherwise it is `false`, and `"owned_candidates"` may list library keys that are close but not confirmed.
- `event: source` — status of one provider. Schema in section 3.8.
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

Errors before streaming starts: `400` for a bad `q`, `types`, `scope` or `limit` (1–50); `401` from the existing login middleware. An owned index that is not available is **not** an HTTP error. The stream starts, and the owned types are reported unavailable in `capabilities` (section 3.6), so provider results can still arrive (section 4.1).

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
- `building`: a build is running and no index exists for the current Navidrome generation. `items: []`, `total: null`.
- `unavailable`: a build failed and no last-known-good index exists for the current Navidrome generation. `items: []`, `total: null`. The response is still HTTP 200, so the page can show a clear message and retry on the next refresh trigger.

`building` and `unavailable` are never reported as an empty library.

`snapshot_at` is `null` while `index_state` is `building` or `unavailable`. Otherwise it is the time of the library snapshot the index was built from.

### 3.3 `GET /api/artists/{key}`

Artist page. `key` is the normalized artist key, with `?mbid=` optional to disambiguate.

**Identity and keys.** Two artists can share a normalized `key` (for example, two Navidrome artists both named "Ash"). The artist route therefore takes the Navidrome `id` as well:

- `GET /api/artists/{key}?id=…` selects one artist exactly. The `id` comes from the `items[].id` of `GET /api/library/artists`.
- `GET /api/artists/{key}` without `id` returns the artist only when exactly one owned artist has that key. When several do, it returns HTTP `409` with `code: "ambiguous_artist"` and a `candidates` array of `{id, name, album_count}`.
- `?mbid=` is used only to choose provider lookups. It never selects the owned artist.

**Index state and unknown keys.** While `owned_index.available` is `false` (no index for the current Navidrome generation), any key returns `200` with the owned sections `artist` and `owned_albums` set to `available: false` with reason `index_building` or `index_unavailable`, and `artist: null` or `items: []`. HTTP `404` is returned only against a ready index, when the key matches no artist.

**Response bodies.** The JSON form has exactly three top-level keys, all required: `capabilities`, `sections`, and `done` (the same fields as the `done` event, section 3.8). Errors use only the `error` shape of section 3.8, with `code` and `message` required and `candidates` allowed only on `409`:

| Status | Body |
|---|---|
| `200` | `{"capabilities", "sections", "done"}` |
| `404` | `{"code": "unknown_artist", "message": "No artist matches this key."}` |
| `409` | `{"code": "ambiguous_artist", "message": "...", "candidates": [{"id", "name", "album_count"}]}` |
| `502` | `{"code": "...", "message": "..."}` (a fatal error after the page began) |

Before streaming starts, the stream form returns the same `404` and `409` bodies. A fatal error after streaming starts follows section 3.7.

Sections and their phases:

| Section | Phase | Why |
|---|---|---|
| `artist` | P1 | Owned data from the owned index. |
| `owned_albums` | P1 | Owned data from the owned index. |
| `bio` | P2 | Uses the existing bio service, a network source. |
| `missing_albums` | P2 | Uses MusicBrainz, Last.fm and ListenBrainz. |
| `similar` | P3 | Uses similar-artist fusion (section 7). |

P1 builds only `artist` and `owned_albums`. Other sections report `not_in_this_build` until their phase.

**JSON form** (default, no `Accept: text/event-stream`). The document has the same shape as the stream, collected into one object:

```json
{"capabilities": {"sections": {"artist": {"available": true, "reason": null},
                               "bio": {"available": false, "reason": "not_in_this_build"},
                               "owned_albums": {"available": true, "reason": null},
                               "missing_albums": {"available": false, "reason": "not_in_this_build"},
                               "similar": {"available": false, "reason": "not_in_this_build"}},
                  "sources": {"navidrome": {"available": true, "reason": null},
                             "musicbrainz": {"available": false, "reason": "not_in_this_build"},
                             "lastfm": {"available": false, "reason": "not_in_this_build"},
                             "listenbrainz": {"available": false, "reason": "not_in_this_build"},
                             "discogs": {"available": false, "reason": "not_in_this_build"}},
                  "owned_index": {"available": true, "reason": null, "state": "fresh"}},
 "sections": {"artist": {"available": true, "complete": true, "reason": null,
                         "artist": {"id": "…", "name": "Radiohead", "mbid": "a74b1b7f-71a5-4011-9441-d0b5e4122711", "owned": true, "album_count": 9}},
              "owned_albums": {"available": true, "complete": true, "reason": null,
                               "items": [{"name": "...", "year": 2019, "song_count": 12, "key": "…"}]},
              "bio": {"available": false, "complete": false, "reason": "not_in_this_build", "bio": null},
              "missing_albums": {"available": false, "complete": false, "reason": "not_in_this_build", "items": []},
              "similar": {"available": false, "complete": false, "reason": "not_in_this_build", "items": []}},
 "done": {"elapsed_ms": 12, "deadline_hit": false, "partial": false}}
```

Each entry under `sections` is the same object as the stream's `section` event (section 3.8) with the `section` key removed. The JSON form and the stream therefore use one schema.

**`owned_albums` item schema** (owned albums only; P1):

| Field | Type | Rule |
|---|---|---|
| `name` | string | Display name. |
| `year` | int or null | Four-digit year. `null` when unknown. |
| `song_count` | int | Songs in the album. `0` only if Navidrome reports none. |
| `key` | string | Normalized album key (section 4.1), the same `key` used by album `result` events. |

Items are sorted by `year` ascending with `null` years last, then by `name`.

**Artist-page capabilities** (the first event of the stream, and the `capabilities` object of the JSON form) use the vocabulary in section 3.6 with three keys: `sections` (one availability object per section name above), `sources`, and `owned_index`. The artist page has no `types` key.

When a section is `available: true` with `items: []`, that is a valid empty result. When `available: false`, the `reason` says why. The frontend renders the two cases differently.

Missing-album items, from P2, include `release_group_mbid`, `popularity` and `sources`. Similar items, from P3, include `score` and `reasons`.

The artist page streams when `Accept: text/event-stream` is sent. The stream follows section 3.7: it begins with exactly one `capabilities` event, emits one `section` event per section (schema in section 3.8), then exactly one terminal `done` or `error`.

### 3.4 `GET /api/genres/{tag}`

Available from P4. Genre page: owned and unowned artists and albums for a tag. Same envelope as 3.3 (`capabilities`, `sections`, `done`; JSON or SSE), with `artists` and `albums` sections in place of `artist`. The tag is lower-cased with single spaces; a blank tag or one over 100 characters is `400`.

- **Owned items** come from the owned index with no network call. An album matches when its Navidrome genre equals the tag (ignoring case), and an artist matches through such an album. Owned items are listed first (approved by the owner, 2026-10-26).
- **Unowned items** come from MusicBrainz tag search (`tag:"…"` on artists and on studio release-groups) and, when a Discogs token is saved, Discogs style search on master releases. Discogs lists only albums, so its artists are the album artists, most frequent first. The sources are interleaved, owned entities and duplicates are dropped, and each section keeps at most 30 unowned items. Each item lists its `sources`.
- **Attribution.** A Discogs-sourced item carries `attribution: "Data provided by Discogs"`.
- **Cache.** Each source's records for one tag and kind are cached for 7 days under `genre:{source}:{config_generation}:{tag}:{kind}` (section 5.2). Only complete answers are written.
- **Sections and `done`.** A source that fails makes the sections it feeds incomplete with `source_failed`; a source that misses the 3.0 s deadline makes them incomplete with `deadline`, and `done.deadline_hit` is then `true`. Either makes the page `partial`. While the owned index builds, the page still serves network items and is `partial`.
- **Capabilities** use `sections` (`artists`, `albums`), `sources` (`navidrome`, `musicbrainz`, `discogs`) and `owned_index`. Discogs is `source_disabled` without a token.

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
| `reason` | `not_in_this_build`, `source_disabled` (no token or key), `source_failed` (last attempt failed), `index_building` (first build running; no index yet), `index_unavailable` (first build failed; no last-known-good index), `deadline` (section events only; see section 3.8) |

Availability is reported at three scopes, each with its own `available` and `reason`:

- **Types** (`artist`, `album`, `song`, `genre`): whether results of that type can be returned in this build.
- **Sources** (`navidrome`, `musicbrainz`, `lastfm`, `listenbrainz`, `discogs`): whether a provider participates.
- **Owned index**: whether owned results can be served, with `state` (`fresh`, `stale`, `building`, `unavailable`).

A capability that is not available is never reported as an empty list. The frontend shows a "not available yet" or "not configured" message for these, and "No matches" only for `available: true` with no items.

### 3.7 SSE stream semantics

Invariants, each covered by an automated test in the phase that introduces it. Invariants 1 to 4 and 10 apply to the owned-only stream in P1. Invariants 5 to 9 apply once providers stream, in P2:

1. Every stream begins with exactly one `capabilities` event.
2. Owned `result` events are emitted before any provider `result` event.
3. A normally completed stream emits exactly one `done` event, as the last event.
4. A fatal error after the stream started emits one `error` event and closes. No `done` follows it.
5. A provider failure or timeout emits a `source` event with `failed` or `timeout`. It does not end the stream, and it does not discard results already emitted.
6. A provider that is timed out or cancelled emits no further `result` events. Results that arrive after cancellation are dropped on the server.
7. Shared provider work is reference-counted by its active consumers (streams). A client disconnect removes that client's reference. Provider work is cancelled only when its last consumer disconnects. A disconnect is detected on write, and no further events are written to that client.
8. Identical concurrent queries share one set of provider calls (request coalescing). The coalescing key is source, config generation, normalized query, types and depth, the same as the provider cache key in section 5.2. Every consumer receives the same events from the shared work. A consumer that joins later receives the events already emitted, followed by the rest. The shared work runs until the latest deadline among its active consumers, so an earlier consumer's timeout does not cancel work that a later consumer can still use. Each consumer stops waiting at its own deadline, and its `done` reports its own `deadline_hit`.
9. Work that is cancelled, or that hits the deadline, is never written to the cache as a complete result. Only complete results from a finished call are cached.
10. The first event on any stream, whether search or artist page, is `capabilities`.

### 3.8 Event payload schemas

These are the contract targets for backend implementation and API contract tests. Every event's `data:` line is one JSON object. Unknown extra fields must be ignored by clients; required fields must always be present.

**Availability object** (used inside `capabilities`):

| Field | Required | Type | Rule |
|---|---|---|---|
| `available` | yes | bool | |
| `reason` | yes when `available` is false; `null` otherwise | string or null | One of the vocabulary in section 3.6. |

**`result` event** (one per entity; required fields by type):

| Field | Required | Type | Rule |
|---|---|---|---|
| `type` | yes | string | `artist`, `album`, `song` or `genre`. |
| `owned` | yes | bool | |
| `id` | yes | string | Navidrome ID for owned results; source-specific ID otherwise. |
| `key` | yes | string | Normalized key (section 4.1). |
| `name` | yes | string | Display name. For `song`, the title. |
| `mbid` | yes | string or null | `null` when no MBID is known. |
| `sources` | yes | array of strings | Non-empty for owned results (`["navidrome"]` at least). `[]` is not allowed. |
| `artwork_url` | yes | string or null | |
| `album_count` | artist only | int | |
| `genre` | artist only | string or null | Most common album genre (section 11.6). Null when no album has one. |
| `artist` | album only | string | Display name of the album's artist. |
| `artist_key` | album only | string | Normalized key (section 4.1). |
| `year` | album only | int or null | Four-digit year. `null` when unknown. |
| `release_group_mbid` | album only | string or null | `null` for owned albums without a known MBID. |
| `album` | song only | string | Display name of the song's album. |
| `duration` | song only | int or null | Seconds, rounded down. |
| `track_number` | song only | int or null | 1-based. `null` when unknown. |
| `tag` | genre only | string | Normalized tag. |
| `tag_source` | genre only | string | One of `musicbrainz`, `discogs`, `listenbrainz`, or `navidrome` for an owned genre. **The `navidrome` value was added in P4 and approved by the owner on 2026-10-26.** `listenbrainz` is not produced by this build. |
| `owned_candidates` | no | array of keys | Optional. Present only when `owned` is `false`. |

**P1 sends only owned `result` events.** Each owned result has `owned: true` and `sources: ["navidrome"]`.

**`source` event** (one per provider state change). Required fields:

| Field | Required | Type | Rule |
|---|---|---|---|
| `source` | yes | string | One of `navidrome`, `musicbrainz`, `lastfm`, `listenbrainz`, `discogs`. Deezer and Wikidata are not streamed sources; they serve artwork and bios through the artist page and are not in `source` events. `navidrome` never emits `source` events; it is reported only in `capabilities`. |
| `state` | yes | string | `pending`, `done`, `failed`, `timeout`, `rate_limited`, `disabled` or `cached`. |
| `count` | yes | int or null | `null` while `pending`. An int otherwise. |
| `ms` | yes | int or null | `null` while `pending`. An int otherwise. |

**P1 sends no `source` events**, because it has no providers. Its `done` reports `partial` as defined below.

**`capabilities` event** (always first, exactly once per stream).

Example in the P1 build, while the owned index is still building. Owned types are unavailable; Discogs is not in this build yet:

```json
{"types": {"artist": {"available": false, "reason": "index_building"},
           "album": {"available": false, "reason": "index_building"},
           "song": {"available": false, "reason": "index_building"},
           "genre": {"available": false, "reason": "not_in_this_build"}},
 "sources": {"navidrome": {"available": true, "reason": null},
             "musicbrainz": {"available": false, "reason": "not_in_this_build"},
             "lastfm": {"available": false, "reason": "not_in_this_build"},
             "listenbrainz": {"available": false, "reason": "not_in_this_build"},
             "discogs": {"available": false, "reason": "not_in_this_build"}},
 "owned_index": {"available": false, "reason": "index_building", "state": "building"}}
```

Example in the P2 build, once the owned index is fresh. MusicBrainz and Last.fm are available. ListenBrainz is not a search source and is `not_in_this_build` here (section 12.7). Discogs and genre are not yet in this build:

```json
{"types": {"artist": {"available": true, "reason": null},
           "album": {"available": true, "reason": null},
           "song": {"available": true, "reason": null},
           "genre": {"available": false, "reason": "not_in_this_build"}},
 "sources": {"navidrome": {"available": true, "reason": null},
             "musicbrainz": {"available": true, "reason": null},
             "lastfm": {"available": true, "reason": null},
             "listenbrainz": {"available": false, "reason": "not_in_this_build"},
             "discogs": {"available": false, "reason": "not_in_this_build"}},
 "owned_index": {"available": true, "reason": null, "state": "fresh"}}
```

Example in the P4 build, once the owned index is fresh. The Discogs token is set, so Discogs is available and genre results are available too:

```json
{"types": {"artist": {"available": true, "reason": null},
           "album": {"available": true, "reason": null},
           "song": {"available": true, "reason": null},
           "genre": {"available": true, "reason": null}},
 "sources": {"navidrome": {"available": true, "reason": null},
             "musicbrainz": {"available": true, "reason": null},
             "lastfm": {"available": true, "reason": null},
             "listenbrainz": {"available": true, "reason": null},
             "discogs": {"available": true, "reason": null}},
 "owned_index": {"available": true, "reason": null, "state": "fresh"}}
```

- For search, `types`, `sources` and `owned_index` are all required. The artist page's capabilities shape is defined in section 3.3 and has `sections`, `sources` and `owned_index`.
- `sources` always lists all five sources in section 5.1's streamed list, in the order `navidrome`, `musicbrainz`, `lastfm`, `listenbrainz`, `discogs`.
- `owned_index.state` is required and is one of `fresh`, `stale`, `building`, `unavailable`. When `state` is `fresh` or `stale`, `available` is `true` and `reason` is `null`. Otherwise `available` is `false` and `reason` is `index_building` or `index_unavailable`.
- An **owned type** (`artist`, `album`, `song`) can be `available: true` only when `owned_index.available` is `true`. Otherwise its `reason` is the owned index's reason (`index_building` or `index_unavailable`).
- An **external type** (`genre`) can be `available: true` only when at least one source that serves it is available. Otherwise its `reason` says why.

**`section` event** (artist page stream; one per section, each emitted once when that section is final).

Every `section` event has the common fields below. The section's payload is one of two shapes, selected by `section`:

| Field | Required | Type | Rule |
|---|---|---|---|
| `section` | yes | string | `artist`, `bio`, `owned_albums`, `missing_albums`, or `similar`. |
| `available` | yes | bool | |
| `complete` | yes | bool | `false` when the section ended early (deadline or source failure). |
| `reason` | yes | string or null | `null` when `available` is true and `complete` is true. Otherwise one of `not_in_this_build`, `source_disabled`, `source_failed`, `deadline`, `index_building`, `index_unavailable`. Owned sections (`artist`, `owned_albums`) report the two `index_*` reasons while the owned index is building or unavailable. When `available` is true and `complete` is false, `reason` is `deadline` or `source_failed`. |

`available: false` always implies `complete: false`. A section that is not available is never reported as complete.

**Payload shape by section:**

| Section | Payload field | Type | Notes |
|---|---|---|---|
| `artist` | `artist` | object or null | Required, object when available: `{"name": string, "mbid": string or null, "owned": bool, "album_count": int}`. `null` when `available` is false. Not an item list. |
| `bio` | `bio` | object or null | Required. `{"text": string, "source": string}` when a bio exists. `null` when available and complete with no bio (a valid empty result), or when unavailable. Not an item list. |
| `owned_albums`, `missing_albums`, `similar` | `items` | array | Required. Always an array, never `null`. `[]` when unavailable. An available section with `items: []` is a valid empty result. |

The `items` field is not present on `artist` or `bio` events, and the `artist` and `bio` fields are not present on list-section events.

Examples:

```json
{"section": "artist", "available": true, "complete": true, "reason": null,
 "artist": {"name": "Radiohead", "mbid": "a74b1b7f-71a5-4011-9441-d0b5e4122711", "owned": true, "album_count": 9}}
```

```json
{"section": "bio", "available": true, "complete": true, "reason": null,
 "bio": {"text": "English rock band formed in Abingdon in 1985.", "source": "wikidata"}}
```

A `bio` section is emitted once, when final, so an available `bio` is always `complete: true`. A `bio` with `available: true, complete: false` is not valid. A bio section that hits the deadline before its source answers is emitted as `{"section": "bio", "available": false, "complete": false, "reason": "deadline", "bio": null}`.

```json
{"section": "bio", "available": true, "complete": true, "reason": null, "bio": null}
```

```json
{"section": "missing_albums", "available": true, "complete": false, "reason": "deadline",
 "items": [{"name": "...", "year": 2021, "release_group_mbid": "…", "popularity": 0.7, "sources": ["musicbrainz", "lastfm"]}]}
```

```json
{"section": "similar", "available": false, "complete": false, "reason": "source_failed", "items": []}
```

**Failure representation.** A section whose source fails before any data arrives is emitted as unavailable: `available: false, complete: false, reason: "source_failed"`, with `artist: null` or `bio: null` or `items: []` as its payload shape requires. A list section that hits the deadline with some items keeps those items, with `available: true, complete: false, reason: "deadline"`. A section is never emitted twice; a later result for the same section is dropped.

**`done` event** (terminal, normal completion):

```json
{"elapsed_ms": 2930, "deadline_hit": false, "partial": false}
```

All three fields are required. `partial` is **true if and only if** at least one of these holds, ignoring types, sources and sections whose reason is `not_in_this_build` or `source_disabled`:

- the deadline was hit (`deadline_hit` is `true`);
- a requested type or owned section is unavailable with an `index_*` reason;
- a source ended `failed`, `timeout` or `rate_limited`;
- a section that is available has `complete: false`;
- a section is unavailable with reason `source_failed` or `deadline`.

A P1 stream with no index problem and no deadline is therefore `partial: false`, even though `genre` is not in this build.

**`error` event** (terminal, fatal):

```json
{"code": "stream_failed", "message": "Owned index read failed."}
```

`code` is required and is a short machine-readable string. `message` is required and contains no credentials, paths or stack traces.

## 4. Search and matching

### 4.1 Owned index lifecycle

The owned index is a new package, `discovery/search/index.py`, that holds:

- **Artists and albums**: taken from the existing library snapshot (`discovery/library_snapshot.py`, which builds artist and album inventories and caches them for 10 minutes).
- **Songs**: loaded with paged Navidrome `search3`, using an empty `query`, `songCount=500` and increasing `songOffset`, until a short page is returned. A live probe on 2026-10-25 returned all 12,097 songs in 25 pages, about 1.8 s. Per-album `getAlbum` calls are not needed.

Lifecycle rules:

- **Build**: a background job assembles a new index object from the snapshot and the full song pages. It is never built inside a request.
- **Single flight**: one build runs at a time, guarded by one lock. A refresh requested while a build is running joins that build; it does not start a second full scan.
- **Atomic swap**: the new index replaces the current one only after a build completes. The build is complete only when every song page succeeded and the final page was short. A failed or incomplete build leaves the last known-good index in place and sets `index_state: "stale"`.
- **Sanity check**: a build whose song count falls by more than 10% from the last good index is rejected as suspicious and reported as stale. The threshold is a proposal to confirm in P1. The check does not apply to the first build after a Navidrome generation change (below), because there is no comparable last good index.
- **Navidrome generation change**: when the Navidrome credential or URL changes (section 5.2), the old index is dropped at once. Owned state becomes `building` and owned types are reported `index_building`, so no data from the previous server is served. The index is then rebuilt from the new server.
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
| Last.fm | Fast text search, `getSimilar`, top albums, popularity | Reported per-second cap (secondary sources) | Primary for bulk candidates. No batch method found. |
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
| Library snapshot | `discovery/library_snapshot.py` | Persistent list store | `library_snapshot:navidrome{gen}` | 10-minute TTL; a Navidrome credential or URL change bumps its generation | Keep the previous snapshot; do not write a partial one. |
| Owned index (artists, albums, songs) | `discovery/search/index.py` | Memory | Single index | Rebuilt with the snapshot; manual refresh | Keep last known-good index; set `stale`. Never swap in a partial build. |
| Provider query results | `discovery/search/cache.py` | Persistent list store | `search:{source}:{config_generation}:{normalized query}:{types}:depth{50}` | 24 h TTL; any credential or setting change bumps the source's `config_generation` (below) | Stores a complete result set at fixed depth 50 per type, independent of request `scope` and `limit`. `scope` and `limit` are applied per request after the cache read. Failures, timeouts and cancelled work are not cached. A 1 h negative entry is cached only for definitive empty answers. |
| Provider entity lookups (MBID) | the source's integration module | Persistent list store | `mbid:{source}:{config_generation}:{mbid}` (MusicBrainz, which has no credential, uses generation `0`) | 30-day TTL; any generation change for the source makes all of its entries unreachable | Same as above. |
| Provider credentials and settings | `settings/service.py` | Existing settings store | Per-source `config_generation` counter | Every save that changes a credential (new token, replacement, clear) or a non-secret setting increments the counter. Old-generation entries become unreachable and are deleted in the background. | Tokens are never stored in cache keys, logs or responses. The counter is the only credential-derived value in a key. |
| Similar artists | `discovery/search/artist_sections.py`; daily precompute in `discovery/search/similar_precompute.py` | Persistent list store | `similar:{artist_mbid or none}:{artist key}:lastfm{gen}:listenbrainz0`. Tags use `search:musicbrainz:0:artist-tags:{mbid}:tags:depth50` at 30 days. The owner boost reads the owned index at request time, so the Navidrome generation is not in the key. The Discogs generation joins with P4. | 7-day TTL for similar entries; a Last.fm generation change makes them unreachable | Only complete fetches are cached. A failed or partial fetch writes nothing, so the previous entry stays. |
| Genre tag results | the genre module (P4; `genre` is not available before P4 because it needs the Discogs styles path, and in P2 it is `not_in_this_build`) | Persistent list store | `genre:{source}:{config_generation}:{tag}` | 7-day TTL; generation change makes entries unreachable | Same as provider results. |

`config_generation` is a per-source integer stored with that source's settings. It is incremented on every save that changes a credential or non-secret setting: setting a first token, replacing one non-empty token with another, or clearing a token. The increment, not a hash of the token, is what separates one credential's cache from another's, so no token-derived value is stored or logged. Entries under an old generation are never read again.

The generation rule applies to every credentialed source: Navidrome (user, password, URL), Last.fm (API key), ListenBrainz (token) and Discogs (token). MusicBrainz has no credential and uses generation `0`. Every source-scoped key in this table includes the generation, so no source-scoped entry can be read after its credential changes.

**Environment-sourced credentials.** A credential can come from the Settings store or from an environment variable (for example, `DISCOGS_TOKEN`). The effective credential is the stored setting when one exists, and the environment value otherwise. Two rules follow:

- Changes made through the Settings API bump the generation immediately, as above.
- Changes to an environment variable are read only at process start. When the process starts with an environment-sourced credential in use, it bumps that source's generation once at startup. This is conservative: a restart may refill that source's cache, but it can never serve an entry written under a different environment value. The environment value is not stored, logged or put in a key.
- Clearing a stored setting falls back to the environment value. That fallback is a credential change, so it bumps the generation.

**Transport and logging.** Secrets do not appear in cache keys, logs, responses or error messages:

- The Discogs token is sent in the `Authorization` header (`Discogs token=…`), not in the query string. A live request with a real token confirmed the format on 2026-10-26 (section 13.2).
- Last.fm's API key is a query parameter, because that is how Last.fm's API takes it. Request logging for these hosts must redact query parameters before writing, and no full URL that contains a credential is logged.
- `POST /api/settings/discogs/test` returns an `error` string that follows the `message` rule in section 3.8. It never echoes a provider response body or a request URL.

## 6. Caching TTLs (summary)

| Data | TTL |
|---|---|
| Library snapshot | 10 min |
| Text search results per source | 24 h |
| Negative search results (definitive empty only) | 1 h |
| MBID entity lookups | 30 days |
| Similar artists | 7 days (on demand, and precomputed daily for library artists in P3b) |
| Genre tag results | 7 days |

Cache misses and failures are never stored as hits. TTLs are fixed; a hit does not extend them.

## 7. Similar artists

Rank fusion across:
1. Last.fm `artist.getSimilar`.
2. ListenBrainz `/1/lb-radio/artist/{seed_artist_mbid}`. The Labs `similar-artists` route is undocumented and is not used. The seed artist appears in the response and is removed. One request per seed; no batch form.
3. Shared tags (MusicBrainz artist `inc=tags`, 30-day cache). The seed and the top 10 unowned candidates with an MBID are looked up. The contribution is `0.5 × |shared| / |union|`, and the reason reads `Shared tags: …`. Discogs styles join in P4 with the Discogs source. (P3b.)
4. Owner listening boost (P3b). The index stores each artist's Navidrome `playCount` total, and an owned artist the owner plays gets up to `0.5`, rising with `log(1 + plays) / log(1 + 100)`. Owned candidates are moved to the owned list: each item carries `owned` and, when matched, the library artist `id`, and owned items follow the unowned ones.

Each suggestion lists its `reasons`. ListenBrainz gives no similarity score, so its contribution uses result order. Non-library artists are computed on demand and cached for 7 days. **Library artists are precomputed daily (P3b):** a loop started at app startup runs once per local day when the owned index is usable. It calls the on-demand path with `refresh=true`, so a complete result overwrites the cached entry. A partial or failed result writes nothing. The run stops after 6 hours; artists it does not reach keep their entries. Each artist gets 120 s.

## 8. Module layout, rules and phase tests

- Routes: `app/api/search.py` (search, artists, genres) and `app/api/library.py` (library artists). Thin adapters only; they are registered in `app/main.py`.
- Logic: `discovery/search/` (index, cache, query normalization, merge and ranking, deadline runner, SSE event assembly) and `integrations/<source>/` clients for Discogs and any new calls. Direct-import tests for each.
- `navidrome_server.py`: no additions (D-016).
- Browser: top-bar search box with an accessible label; results in two sections only, "In your library" and "Not in your library"; streaming updates announced politely (`aria-live`). No provider names, provider status or popularity are shown in the search panel (owner direction, 2026-10-25). Logic stays server-side. Frontend work in a phase depends only on capabilities that phase delivers (section 3.6).

### 8.0 Test runs (rule)

Agents never run the full unit suite (`python -m unittest discover -s tests`), in any phase. The owner runs it independently, and CI runs it on the PR head. Agents run only the focused test modules for the code they changed, plus the guard scripts, and report exactly which modules ran and which checks were skipped.

### 8.1 Tests required in each phase

Correctness tests land in the same PR as the code they cover.

| Phase | Required automated tests |
|---|---|
| P1 | Complete song retrieval and paging (including a short final page and an empty library); index build single flight; failed or incomplete build keeps the last good index; `stale`, `building` and `unavailable` states; first build failure with no last-known-good index reports `index_unavailable` in an HTTP 200 stream or response, never a `503` and never an empty library; `scope=owned` with no index emits a `done` with `partial: true` and makes no provider calls; Navidrome generation change drops the index to `building` and skips the 10% sanity check on the first rebuild, with a test that the previous server's data is never served; owned-only identity: Various Artists excluded, and same-name artists with different Navidrome IDs kept as separate results (MBID-based ownership matching against provider results is tested in P2); SSE invariants 1 to 4 and 10 (section 3.7); schema tests for `capabilities` (the P1 example in section 3.8), `result` (owned results only, required fields), `done` (including `partial` false for a P1 stream with `genre` not in this build), and `error` (`code` and `message` present, no credential in `message`); no `source` events in P1; artist-page `artist` and `owned_albums` sections with the JSON form and the stream form matching the same schema; library artist list paging and `index_state`; index build time recorded against the section 2.1 target; artist-page JSON form with exactly `capabilities`, `sections` and `done`, checked against the example in section 3.3; `artist` section schema (available, and `artist: null` when unavailable); `owned_albums` item schema and sort order; `404` for an unknown key and `409 ambiguous_artist` with `candidates` when two artists share a key, selected by `?id=`; artist-page answers while the index is building (`200` with `index_building`, never `404`); `error` bodies on `404`, `409` and `502` containing only `code`, `message` and, on `409`, `candidates`. |
| P2 | Provider isolation (one failing provider does not affect others); entity-lookup entries are unreachable after a generation change (genre results and genre cache entries are P4 tests); schema tests for `capabilities` against the P2 build (MusicBrainz and Last.fm available; ListenBrainz and Discogs `not_in_this_build` for search) and for `source` events (`pending` with `count` and `ms` null; terminal states with ints); schema tests for `section` events covering each payload shape: `bio` object (with text), `bio: null` (valid empty), and list sections with `items` (available, empty, partial with `reason: "deadline"`, and source-failed with `items: []`); the `items` field absent on `artist` and `bio` events; the `done` payload matches section 3.8; cross-provider deduplication by MBID and by key plus year; MusicBrainz 503 backoff and retry; 100-term batching and paging; rate-limit skip (`rate_limited`); deadline expiry (`deadline_hit`); SSE invariants 5 to 9 (section 3.7); shared-work cancellation: one consumer disconnects while another continues, and the shared call is cancelled only when the last consumer disconnects; cancelled or deadline-expired work is not cached; provider cache stores depth 50 and serves smaller `limit` values by slicing; `scope=owned` never reads or writes the provider cache. |
| P3 | Seed artist exclusion from `lb-radio`; owned candidates moved to the owned list; ranking with no ListenBrainz score; `similar` section availability (source_failed partial, source_disabled, all-failed); on-demand 7-day cache, with failed or partial fetches never cached. |
| P3b | Shared-tag scoring and the tag deadline (`deadline` reason); owner boost from index play counts; precompute budget, `refresh` bypass, partial and failed results keeping the previous entry, and per-artist failure isolation (`tests/test_discovery_search_similar_precompute.py`). |
| P4 | Discogs token handling (never in responses, logs or cache keys); first token set, token replacement (non-empty to different non-empty), and clear each bump `config_generation`, and old-generation entries are never read from the query, entity-lookup, genre or similar-artist layers; environment-sourced `DISCOGS_TOKEN`: a process start with the variable set bumps the generation, a stored setting takes precedence over the variable, and clearing the stored setting falls back to the variable with a generation bump; a `capabilities` payload for each state (`not_in_this_build`, `source_disabled`, available); the `capabilities` payload never contains a credential value; attribution text present on every Discogs-sourced item; genre matching; `disabled` state without a token. |
| P5 | Latency measurements against section 2.1 targets, with results recorded in `PROJECT_LOG.md`; `TEST_PLAN.md` entries for each phase. |

## 9. Verification results and open items

Checked on 2026-10-25. Live results are authoritative; secondary sources are marked as such.

### Verified

- **Navidrome `search3` with an empty query and paging works.** A read-only probe of the owner's server returned 12,097 unique songs in 25 pages (`songCount=500`), about 1.8 s total.
- **Library counts.** Navidrome is the source of truth: `getArtists` returns **733** artists, and the owner confirmed the count is whatever Navidrome returns. Songs: 12,097. Albums: 1,744 (owner-supplied; not probed).
- **MusicBrainz rate limit and identification** ([MusicBrainz rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)). The official page sets an average of 1 request per second per source IP (300 requests/second global, anonymous agents about 50/second). Exceeding the limit returns HTTP 503 and every request is declined until the rate drops. Each request needs a User-Agent that identifies the app and a contact. The page does not address caching. It says high-volume commercial use should replicate the database locally, and it asks clients not to poll for metadata changes.
- **MusicBrainz OR-search size** (live, 2026-10-25). The limit is the request URL length, not the term count. 150 terms returned complete results (paged with `offset`); 160 terms returned HTTP 414 "URI Too Long"; 250 and 300 terms returned 414 and 431. **Decision: 100 terms per call**, about 1,800 characters under the first failure.
- **MusicBrainz 503s.** The public service returned HTTP 503 "web server is currently busy" several times during probes and cleared after backing off. Backoff and retry are required.
- **ListenBrainz `lb-radio/artist`** (live, 2026-10-25). `GET https://api.listenbrainz.org/1/lb-radio/artist/{seed_artist_mbid}` with `mode=easy&max_similar_artists=5&max_recordings_per_artist=1&pop_begin=0&pop_end=100` returned HTTP 200 with a JSON object keyed by artist MBID. Each value is a list of `{recording_mbid, similar_artist_mbid, similar_artist_name, total_listen_count}`. The seed is included. There is no similarity score. The result held five similar artists plus the seed, so the parameter limits similar artists, not total entries. Rate-limit headers: `X-RateLimit-Limit: 30`.

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

**Closed (2026-10-26):** the Discogs `Authorization: Discogs token=…` header format is accepted by the live API (section 13.2). The official documentation page was still not readable by the agent.

Fixes for the third review are in the sections listed below. They have not yet been re-reviewed. Earlier fixes: `result` and `source` schemas and the P1 `source` rule (3.8); the `partial` rule (3.8); invariants and tests moved to P1 (3.7, 8.1); phase-matched `capabilities` examples (3.8); the Navidrome generation drop and sanity-check exception (4.1); and the artist-page phases, JSON form, and capabilities (3.3). Non-blocking items are addressed in sections 2.1, 3.6, 3.7, 3.8, 5.2, 6 and 8.1. Re-review is requested before P1 starts.

## 10. Phasing

- **P1**: owned search and library page, with the owned index lifecycle (section 4.1), the `capabilities` event, the owned-only stream, the artist page's `artist` and `owned_albums` sections, and no network sources. Ships first; no new provider risk. Owned types only; genre and external types report `not_in_this_build`.
- **P2**: MusicBrainz, Last.fm and ListenBrainz for not-owned artists and albums; deduplication; provider streaming and `source` events; the deadline runner; the artist page's `bio` and `missing_albums` sections.
- **P3**: similar artists: Last.fm and ListenBrainz fusion, on demand with a 7-day cache, owned candidates in the owned list, and the `similar` section. Owner decision (2026-10-26) narrowed P3 to this slice.
- **P3b**: shared-tag scoring (MusicBrainz tags; Discogs styles join in P4), the owner-listening boost from Navidrome play counts, and daily precompute for library artists with the failed-recompute rule (keep the previous entry). Owner decision (2026-10-26) to proceed; weights and budgets are starting values, to be checked against the owner's data.
- **P4**: Discogs integration, including the Settings page (section 3.5); genre pages.
- **P5**: consolidated integration and performance: latency measurement against section 2.1, and `TEST_PLAN.md` entries.

Each phase is a separate branch and PR from current `main`, with CI verified on the exact head before merging, and with the tests in section 8.1. Nothing in this plan is published or deployed.

## 11. P1 implementation record

This section records what P1 built and every decision the contract left open. Sections 3 to 9 are unchanged except where noted here.

### 11.1 Built in P1 (backend only)

- Routes: `GET /api/search` (SSE only), `GET /api/artists/{key}` (JSON or SSE, chosen by `Accept`), `GET /api/library/artists`. Adapters in `app/api/search.py` and `app/api/library.py`, registered in `app/main.py`. All three sit behind the existing login middleware.
- Logic in `discovery/search/`: `normalize.py` (keys and query normalization), `index.py` (owned index lifecycle and song paging), `query.py` (matching, ranking, library pages, cursors, artist lookup), `events.py` (capabilities, SSE framing, search stream), `artist_page.py` (artist sections).
- Supporting changes: the Navidrome credential generation counter in `settings/service.py`; album `artist_id` in `discovery/library_snapshot.py`.
- `navidrome_server.py` is unchanged (D-016).

### 11.2 Decisions made in P1

| Topic | Decision |
|---|---|
| Key derivation (section 4.1) | Keys come from display names only: NFKD, diacritics removed, casefold, punctuation to single spaces, and a leading "The" dropped. An artist key is that name key. An album key is `artist_key/album_key`. A song key is `artist_key/title_key`. Results that share a key carry their Navidrome `id` to tell them apart. |
| Owned MBIDs | `mbid` and `release_group_mbid` are `null` in P1, because the snapshot carries no MBID. |
| Owned artwork | `artwork_url` is `/api/owned/artwork/{id}`. The app signs a Navidrome `getCoverArt` request on the server, so the Navidrome credential never reaches the browser (owner decision, 2026-10-25). Artists use their ID, albums their ID, and songs their album's ID. `size` is 64 to 1000, default 300. Only `image/jpeg`, `image/png`, `image/webp` and `image/gif` are passed through. SVG and every other type are refused, as are Subsonic error bodies and bodies over 5 MB, and each returns `404`. Responses carry `Cache-Control: private, max-age=3600` and `X-Content-Type-Options: nosniff`. |
| `snapshot_at` (section 3.2) | The UTC time the index build completed, not the snapshot's own `generated_at`. |
| Navidrome generation (section 5.2) | Settings store counter `navidrome_generation`. It increments whenever the Navidrome URL, user or password changes; a blank password that keeps the saved one does not increment it. The owned index is keyed by it. A changed generation drops the index at once. |
| Library snapshot key (section 5.2) | The owned index reads the library snapshot under `library_snapshot:navidrome{generation}`. The recommendation path still uses the unscoped `library_snapshot` key (see 11.4). |
| Album `artist_id` | The snapshot now keeps each album's `artistId`, so an artist page lists exactly that artist's albums. Snapshot cache entries without this field are refetched. |
| Sanity check (section 4.1) | 10% drop limit, approved by the owner on 2026-10-25. |
| Retry backoff | After a failed build, the index waits 30 s before the next automatic build. A generation change clears the wait. A forced refresh bypasses the TTL, but not the wait. |
| Index refresh | Each owned request triggers a non-blocking refresh once the index is older than 10 min. There is no manual refresh route in P1. |
| Song inventory | `search3` with an empty query, 500 per page. A walk that reaches the 200,000-song safety cap raises; it never returns a partial list. |
| `stale` and `partial` | `stale` is served normally. It does not set `partial`, because section 3.8 lists only `index_*` reasons. |
| `scope` | Accepted. In P1 `owned` and `all` give the same result, because no network source exists yet. |
| `deadline_hit` | Always `false` in P1. The deadline runner arrives with P2. |
| `mbid` on the artist route | Accepted and ignored. It only selects provider lookups, and none exist in P1. |
| Library cursor | Opaque base64url JSON holding the offset, the query and the sort. A cursor for another query or sort returns 400. |
| Search matching | Exact, then prefix, then contains, on the normalized key. Ties sort by name, then `id`. Genre matches nothing (`not_in_this_build`). |
| Errors | `400` for bad search or library parameters, and for a malformed or mismatched cursor. `404` and `409` follow section 3.3. A failure while reading the index in an artist request returns `502` with `code: "artist_failed"`. A search read failure after streaming starts emits `error` with `code: "stream_failed"`. |

### 11.3 Verification in P1

- Focused unit modules: `tests/test_discovery_search_*.py`, `tests/test_api_search_routes.py`, `tests/test_navidrome_generation.py`, and the updated `tests/test_discovery_library_snapshot.py`. The full unit suite was not run by the agent (owner rule); CI runs it on the PR head.
- Existing modules that touch the changed code, also run focused: `test_service_settings.py`, `test_settings_routes.py`, `test_app_legacy_import_boundary.py`, `test_auth_routes_integration.py`, `test_api_discovery_injection.py`, and `test_server_size_guard.py`.
- Guards: `scripts/check_server_size.py` and `scripts/check_app_legacy_imports.py` pass. `navidrome_server.py` is 2,457 lines, under the 2,650 ceiling and smaller than before the PR.
- End to end, against a throwaway Subsonic stub on localhost with a real app account: library paging reports `fresh`, search streams `capabilities`, owned `result` events and one `done`, and the ambiguous key returns `409` while `?id=` resolves it. This was a local check outside the repository, not a CI test.
- Not verified: browser behavior, latency against section 2.1 (measured in P5), and behavior against the owner's real Navidrome server.

### 11.4 Open items

1. **P1 UI manual gate.** The top-bar search and library page are built (section 11.5). Their browser checklist under `docs/LOCAL_UI_TESTING.md` is for the owner to run on the exact tested SHA.
2. **Recommendation snapshot generation (accepted, deferred).** The recommendation path still reads the unscoped `library_snapshot`. After a credential change it can serve the previous server's inventory for up to 10 min. The owner accepted this as a deferred follow-up on 2026-10-25. The fix is the same key scoping, and it touches existing recommendation code, so it needs its own change.
3. **Manual refresh route.** Section 4.1 mentions a manual refresh path. P1 has the internal `force` argument but no route.

### 11.5 P1 UI (branch `search-ui`)

- **Top bar:** a search form in the header (`role="search"`). Input is debounced at 250 ms and streams from `GET /api/search`. Results are grouped as Artists, Albums and Songs. Each result is placed as it arrives, and the status line shows a running count ("Searching… 3 matches so far"). The status is `aria-live="off"` while the stream runs and `polite` when it ends, so a screen reader hears the final count once. The previous results stay on screen until the new stream's first event, and a server error keeps the results already shown. The input is a plain searchbox with no combobox ARIA, because no listbox sits behind it. Escape closes the panel from the input or any result, and focus returns to the input. Focus moving to a real element outside the form closes it; a null target (Safari does not focus buttons on click) does not. An outside click also closes it. A new query closes the previous stream, and events from a superseded stream are ignored. A dropped connection and a server `error` event show different messages. Index states show the matching message, and "No matches" appears only when the index is available. Group headings are paragraphs, so the heading order has no gap.
- **Artists** open the artist view on the library page, by `id` and `key`. **Albums and songs** are listed for reference only in P1: they are plain rows with no hover state and no action. The placeholder and library copy do not promise albums or songs, so no text suggests they open.
- **Library page:** reached from the header menu, next to Saved. It has a filter (debounced, sent to the server as `q`), a sort control (`name` or `album_count`), and a Load more control that follows `next_cursor`. A failed first page offers Try again, which reloads from the start. A failed append offers Try again, which retries the same page and keeps the rows already loaded. `building` and `unavailable` show messages with a Try again control, never an empty library. `stale` is labeled.
- **Artist view:** leads with the artist's artwork and name (the artwork comes from the row or result that was clicked, so the artist API gains no field), then the owned albums with year and track count. The page intro steps aside while the artist view is open. It takes focus on open, returns focus on close, and shows a not-found message on 404.
- **Rendering:** every value is set with `textContent` or as an attribute. Artwork comes from `artwork_url` and is removed when it fails to load.
- **Verification:** `tests/test_library_search_ui_contract.py` checks structure and rendering rules in source. A DOM harness in jsdom drove the page script against stub API and stream responses, covering the flows above, and passed. Headless Chromium at 1280 px and 390 px rendered the header, search results, library, and artist view, with no console errors and no horizontal overflow. Those checks were run by the agent. The owner's manual browser checklist is still required.
- **Not verified:** keyboard-only pass on a real browser, reduced-motion behavior, screen-reader output, and behavior against a real Navidrome library.

### 11.6 Contract addition: artist genre (approved 2026-10-25)

Approved by the owner on 2026-10-25, with these decisions: the source is the Navidrome album genre tag, and an artist with no genre falls back to the album count. The title changed from the first proposal, which asked for a free-text detail line.

- **Field.** Artist `result` events gain `genre`: a string or null. It is the most common album genre of that artist, counting ignores case, the first spelling seen is kept, and ties go to the alphabetically first genre. Null when no album of the artist has a genre.
- **Display.** The search result shows "Name (genre)" when a genre exists. Without one, the name stands alone and the album count on the detail line tells same-name artists apart.
- **No new provider call.** The genre comes from the album records the library snapshot already fetches. The snapshot keeps each album's `genre`. Cache entries without the field are refetched.
- **Not in scope.** Album artwork on owned-album items is still a separate proposal, not approved.

### 11.7 P1 completion check (2026-10-25)

Checked against the P1 test rows in section 8.1 and the phase scope in section 10.

- **Closed in this change:** "Various Artists" never becomes an artist result (section 4.2). The rule is the existing `is_various_artists`, so search, the library list and the artist route all exclude it. The 502 body of the artist route is tested as `code` and `message` only.
- **Deviations, recorded:**
  - The artwork route lives in `app/api/owned_artwork.py`, not in the module layout in section 8.
  - Results show "N matches in your library". The "Not in your library" group waits for the network sources in P2.
- **Not done, deferred to P5:** recording the index build time against the section 2.1 target. It needs a run against the owner's Navidrome server, with the latency measurements (see 11.8).
- **Status:** P1 is complete except for the build-time record above.

### 11.8 Open follow-ups for P1 (2026-10-25)

1. **Index build time (P5).** Measure a full owned-index build against the owner's Navidrome server, and record the result against the section 2.1 target in `PROJECT_LOG.md`. Test the build on the real library size (12,097 songs, 733 artists, 1,744 albums). A stub run does not count. Owner: run the measurement or authorize it.
2. **Manual refresh route (proposal, not approved).** Section 4.1 describes a manual refresh, but P1 has only the internal `force` argument. Proposed endpoint: `POST /api/library/refresh`, behind the login middleware. It starts an owned-index build with `force` and returns `202` with `{"index_state": "building" | "fresh" | "stale" | "unavailable"}`. If a build is already running, it joins that build rather than starting another. It has no request body. Nothing here is built until the owner approves the endpoint.

## 12. P2 implementation record

P2 is delivered in slices. This section records slice A; slice B is listed at the end.

### 12.1 Slice A (branch `search-p2`)

- **Sources:** MusicBrainz (artist search, release-group search restricted to albums, depth 50, 503 retried after 1 s and 2 s) and Last.fm (`artist.search`, `album.search`). Last.fm is `source_disabled` until a key is saved. Both run only for `scope=all` and only for the `artist` and `album` types.
- **Pacing and deadline:** one limiter per process (MusicBrainz 1 call/s, Last.fm 5 calls/s). The deadline is 3.0 s from request receipt. Unfinished sources are reported `timeout` and set `deadline_hit`.
- **Sharing and cache:** calls are keyed by the cache key in section 5.2. Identical concurrent searches share one call, which runs until the latest deadline among its consumers (invariant 8). A call is cancelled only when its last consumer leaves. Only complete results that arrive before the call's deadline are cached.
- **Generation:** `lastfm_generation` in the settings store. MusicBrainz uses generation `0`.

### 12.2 Deviations (slice A)

1. **Null `album_count` and `genre` on provider artist results.** Section 3.8 types these as int and string. Search sources do not report them, so they are null rather than invented.
2. **Duplicates across sources are dropped, not merged.** Results are emitted as they arrive, so a second source's match for an entity already shown is dropped, and the first result lists only the sources known then. Merging `sources` after emission would need a change to the event model.
3. **Owned matching is by key, not MBID.** Owned MBIDs are null (section 11.2), so a provider match is owned when its normalized key matches, and for albums when the year also matches or one side has no year.
4. **Homonyms.** Two artists with different known MBIDs stay separate even with the same name. Without MBIDs, the same key collapses them, as section 3.8 requires for key plus year.
5. **Source `count`** is the number of provider records before dedupe.
6. **HTTP request budget is fixed at 5 s, not the search deadline.** A request in flight cannot have its timeout extended when a later consumer joins a shared call. Consumers stop waiting at their own deadlines; a request that returns after the call's final deadline is a timeout and is not cached. A request started near a deadline can therefore run up to 5 s after its consumers leave, then is discarded.

### 12.3 Slice B (branch `search-p2b`)

- **`missing_albums` on the artist page.** The owned artist's MBID is the first MusicBrainz artist whose normalized name matches exactly. Its studio albums come from one release-group browse (limit 100, no secondary types such as live or compilation). Albums the library owns are removed by key and year, and duplicates are merged. Items are sorted by ListenBrainz listen count (`popularity`), most first, then by year. The list is capped at 50. `sources` lists `musicbrainz`, plus `listenbrainz` when a count was found.
- **`bio`.** The existing bio service (`app/api/metadata.py`, `artist_bio`) is called from the route adapter and injected into the discovery layer, so discovery does not import the app. The section's `source` is `wikidata`, the service's primary identity source.
- **Deadline.** `bio` and `missing_albums` run on separate threads under the 3.0 s deadline. One that has not finished is `deadline`; one that failed is `source_failed`. Either makes the page `partial`. A late answer is not cached. The ListenBrainz popularity lookup receives a `can_cache` check and uses the 5 s request budget (section 12.2 item 6); its cache writes happen only while the check is true.
- **ListenBrainz** supplies release-group popularity (`POST /1/popularity/release-group`, the existing batch client). It is available on the artist page and not used by search, which has no text-search endpoint on ListenBrainz.

### 12.4 Slice B deviations

1. **`popularity` is the ListenBrainz listen count**, an integer, not the 0 to 1 score in the section 3.8 example.
2. **Identity is the first exact-name match**, not a confidence-checked match. Two artists with the same name can resolve to the wrong one.
3. **Provider caches use the 24 h TTL** from section 6, not the 30-day TTL for MBID lookups. The identity lookup shares the search cache entry for the same name.
4. **The artist page is computed before its stream starts** and then emitted section by section. Sections are not streamed as each one finishes.

### 12.5 Still open after slice B

- The "Not in your library" group in the search UI. The backend still returns provider results as `result` events with `owned: false`.
- Last.fm on the artist page (`lastfm` is reported `not_in_this_build` there).
- Cached entries for an old credential generation are not deleted in the background (section 5.2).

### 12.6 Slice C (branch `search-p2c`)

- **"Not in your library" group.** Results with `owned: false` go to their own section below the owned groups. Owned results keep their groups and their count. The summary reads "N matches in your library · M not in your library".
- **No source status in the panel.** The `source` events still reach the stream for clients, but the panel does not show them (owner direction, 2026-10-25).
- **Artists not in the library do not open the artist view**, because their IDs are MBIDs, not Navidrome IDs.
- **Partial album list.** When the artist page's deadline falls after the album list is known and before popularity arrives, `missing_albums` returns `available: true, complete: false, reason: deadline` with the albums it has (section 8.1, P2 row).
- **Last.fm generation.** A test shows that a new key bumps `lastfm_generation` and a repeated or blank key does not.

### 12.7 Open items after slice C (resolved by slices D and E)

Each item below is now resolved, as marked. Section 12.10 lists what remains in P2.

1. **ListenBrainz in search: not needed, and not built (resolved 2026-10-25).** ListenBrainz has no text search. Its uses in section 5.1 are popularity, metadata, radio and similar artists, none of which search needs. Search reports it `not_in_this_build`. Its only use is popularity on the artist page's `missing_albums`.
2. **Batched identity lookup (section 8.1, 100-term batching): called by the identity job** (section 12.9).
3. **Owned MBID matching: done** in slice E (section 12.9). Stored MBIDs are used when both sides have one, with name matching as the fallback.
4. **Background deletion of old-generation cache entries (section 5.2): done** in slice D (section 12.8). Identity records under old generations are not yet deleted (section 12.9).
5. **Last.fm on the artist page: done** in slice D (section 12.8).

### 12.8 Slice D (branch `search-p2d`)

**Navidrome MBIDs (probe, 2026-10-26).** A read-only probe of the owner's server, reporting counts only:

| Item | With MBID | Total | Share |
|---|---|---|---|
| Artists (`getArtist` `musicBrainzId`) | 314 | 733 | 43% |
| Albums (`getAlbumList2` `musicBrainzId`) | 858 | 1745 | 49% |

Most files are not tagged, so the premise of a majority does not hold. Two facts shape the design:
- Artist MBIDs are not in the artist index or in album artist references. Each one needs a `getArtist` call, so they are read per artist page, not library-wide.
- The album `musicBrainzId` is the **release** MBID. Provider albums are release groups, so the two cannot be matched by ID. Albums keep key-and-year matching.

**What slice D builds:**
- **Artist page identity.** The artist's Navidrome MBID is read with one `getArtist` call and used when present. Otherwise the exact-name MusicBrainz lookup is used.
- **Last.fm on the artist page.** `artist.getTopAlbums` adds albums to `missing_albums`. An album from both sources is one item with both sources listed. Last.fm works when MusicBrainz has no identity for the artist. A Last.fm failure is ignored: the MusicBrainz list still answers. Ordering is unchanged (ListenBrainz listen counts).
- **Batched MusicBrainz identity.** `artist_identities(names)` resolves many names with OR queries. Each batch is at most 100 names and about 1800 characters of query. It pages up to 5 pages per batch, and each page is one request. Only exact key matches count. The first match in MusicBrainz's ranking wins. **This is built and tested but not called yet.** A library-wide job would need about 420 unresolved artists, so about 5 batches. Whether to run it, and when, is an owner decision.
- **Old-generation cache cleanup.** `discovery/store.py` `delete_prefix_except` removes entries under a prefix except the current generation's. It compares prefixes as plain text, so `%` and `_` in names are safe. The search path schedules this once per source and generation per process, on a background thread. Failures are retried on a later request.

**Still open:** the library-wide identity job (see above); owned MBID matching for provider results (the owned index has no MBIDs).

### 12.9 Slice E (merged in PR #618, squash `a37f804`)

Owner approvals (2026-10-26): permanent storage of identities, a background pass after each owned-index build and for new items, and scope limited to artists and albums.

**What is stored.** One record per artist and per album, under the Navidrome generation:
- `identity:navidrome{gen}:artist:{id}` → `{"mbid", "source"}`.
- `identity:navidrome{gen}:album:{id}` → `{"release_group_mbid", "source"}`.

`source` is `navidrome`, `musicbrainz`, or `unresolved`. Records have no expiry. This is the approved deviation from the 30-day rule in section 6.

**How it is resolved.**
- Artists: Navidrome's tag first (`getArtist`). Untagged artists are matched by exact name in batches of 100. A name shared by two library artists is stored `unresolved`, because a name cannot tell them apart.
- Albums: the release MBID Navidrome tags is mapped to its release group in batches (`reid:` OR query). Albums without a tag are matched by exact artist and title, with the year as a tie-breaker. Compilations are stored `unresolved`.
- A lookup that answers with no match is stored `unresolved` and not asked again. A failed lookup stores nothing, and the next run retries it.

**When it runs.** Once after each owned-index build, on a background thread, one pass at a time. The pass resolves only items with no stored record. When a pass stores something, the index is rebuilt once so the MBIDs reach search results. A later pass with nothing new makes no calls.

**What changes for users.**
- Owned artists and albums carry their `mbid` and `release_group_mbid`, where known. Provider results matching an owned item by MBID are not shown again. Without an MBID they still match by name, as before.
- The artist page uses the stored MBID and skips the name lookup.

**Expected work for the owner's library** (from the probe in section 12.8): about 420 artist name lookups, about 5 batches; about 9 release batches plus a few dozen title batches for albums. The first pass takes a few minutes at MusicBrainz's rate limit. Later passes make almost no calls.

**Limits.**
- A name can match the wrong artist when the name is unique in the library but ambiguous in MusicBrainz. The first exact match is taken.
- An unresolved item stays unresolved until its record is removed. There is no correction tool yet.
- Identity records under old Navidrome generations are not deleted. Only `search:` cache entries are purged (section 12.8).

### 12.10 P2 status: complete (2026-10-26)

**Built and merged (PRs #613 to #620):**
- Provider search (MusicBrainz, Last.fm) behind the 3.0 s deadline runner, with `source` events, dedupe, shared calls, cancellation and complete-only caching (slice A).
- Artist page `bio` and `missing_albums`, with ListenBrainz listen-count ordering, under the deadline (slice B).
- The "Not in your library" group, with the search panel showing two sections only (slice C, direction of 2026-10-25).
- Navidrome MBID on the artist page, Last.fm top albums on the artist page, old-generation cache cleanup for search keys (slice D).
- Stored MusicBrainz identities for artists and albums, resolved in batches after each index build, with owned matches by MBID (slice E, PR #618).
- First identity pass on the owner's library, a cleanup of old identity records, and a correction path for stored identities (slice F, PR #620, section 12.11).

**Decided, not built:**
- ListenBrainz in search. The owner's direction (2026-10-25): search does not need it. Section 10's wording "MusicBrainz, Last.fm and ListenBrainz for not-owned artists and albums" is superseded for search. ListenBrainz is used only for popularity on the artist page.
- Provider artist results report `album_count: null` and `genre: null` (section 12.2).

**Remaining in P2:** nothing. Browser verification was waived by the owner.

**Known limits carried into P3 (not blockers):**
- 744 identities are stored as unresolved, and unresolved records are not retried. They change only through the correction endpoint.
- A name match can pick the wrong artist when MusicBrainz has several exact matches.
- Provider artist results have no album count or genre (section 12.2).

**Not P2:** `similar` (P3), Discogs and genre (P4), latency measurement and `TEST_PLAN.md` entries (P5).

### 12.11 Slice F (branch `search-p2f`)

**First identity pass on the owner's library (2026-10-26).** Run through the app's own functions against the owner's Navidrome server, with a read-only snapshot of the library. The run resumed from 323 identities stored by an earlier pass that timed out.

| Measure | Result |
|---|---|
| Library | 732 artists, 1745 albums (generation 0) |
| Records written this run | 409 artists, 1745 albums (including 744 unresolved) |
| Artists with a stored MBID | 609 of 732 (83%) |
| Albums with a stored release-group MBID | 1114 of 1745 (64%) |
| MusicBrainz requests | 103 (artist 30, release 22, release-group 51) |
| Navidrome requests | 409 `getArtist`, 25 `search3` pages |
| Time | 195 s |
| Second pass | no calls, no writes |

Sample check (names and MBIDs read by hand): artist matches were correct in every case shown. Unresolved examples: names in non-Latin scripts with a Latin variant in brackets, and names with parentheses. Album matches were correct where shown. Unresolved examples: titles that differ from MusicBrainz's, such as "Taha/Khaled/Faudel" and "1, 2, 3 Soleils: En Concert [1999] Disc 1".

**Bugs found by the first run and fixed in this slice:**
- A MusicBrainz request timeout escaped the identity job and aborted the whole pass. A failed request now skips only its batch.
- The background pass used the 5 s search timeout. It now uses 30 s.

**Cleanup.** Each pass deletes identity records of generations older than the current one. Generations are an increasing counter, so the comparison is numeric. The current generation is read at the moment of the delete, and the pass stops if the generation changes during the cleanup. Records of the current or a newer generation are never removed.

**Correction path.** `PUT /api/identities/{kind}/{id}` stores the owner's MBID as a manual record (`null` marks "no MBID"). `DELETE /api/identities/{kind}/{id}` removes the record, so the next pass resolves the item again. The MBID must be a lowercase UUID. The item must exist in the current index. The index is refreshed for the current generation only. These routes sit behind the login middleware.

**Limits.**
- Unresolved records are not retried. The 744 unresolved items stay unresolved until corrected or deleted through the endpoint above.
- A name match can still be wrong. The first exact match in MusicBrainz's ranking is taken.

## 13. P4 implementation record (Discogs and genre pages)

Merged in PRs [#623](https://github.com/abucalip/navi-librarian/pull/623) (token settings, squash `2f66598`), [#624](https://github.com/abucalip/navi-librarian/pull/624) (client, shared styles, genre pages, global genre search, squash `13cb7d3`) and [#625](https://github.com/abucalip/navi-librarian/pull/625) (Settings tab and genre view, squash `afade38`). Exact heads and CI runs are in `PROJECT_LOG.md`.

### 13.1 What was built

- **Token settings (3.5, 5.2).** `GET/PUT /api/settings/discogs` and `POST /api/settings/discogs/test`. The stored token wins over `DISCOGS_TOKEN`. The generation counter bumps on a first token, a replacement, a clear, and a clear that falls back to the environment value, and once at startup when the environment token is in use. No change to `navidrome_server.py`.
- **Client (`discovery/search/providers.py`, `DiscogsSearch`).** Master-release search by text (artists, albums) and by style, artist styles for shared-tag scoring, and genre names read off master results. Paced at 1 request/second. HTTP 429 is `rate_limited`; any other failure is `failed`, never an empty answer.
- **Capabilities.** `discogs` is `source_disabled` without a token and available with one, in search, the artist page and the genre page. It is queried for artist and album search and for genre search whenever it is reported available.
- **Similar artists (7).** Discogs styles join MusicBrainz tags as shared-tag input (styles cached 30 days under the Discogs generation). An item whose shared tag came from Discogs for the seed or for that candidate carries the attribution; another candidate's styles never count. The similar-artists cache key does not include the Discogs generation (see 13.3).
- **Global genre search (3.1, 3.8).** `genre` results come from the library's album genres, from MusicBrainz (the full `/genre/all?fmt=txt` list, one request, cached 30 days, filtered per query, because MusicBrainz has no genre search) and from Discogs (styles and genres on the master results a text search returns, because Discogs has no style search). A genre the library has is returned once, as owned. A genre two sources name is returned once, keeping the first.
- **UI.** A Discogs tab in Settings (password field never filled from the server; Save refuses an empty token; a separate Remove button; Test), a Genres group in the search panel, a genre button on the artist view, and a genre view. Back from a genre opened via search returns to the library list; Back from an artist opened in a genre returns to that genre.

### 13.2 Live check against Discogs (2026-10-26)

Run with the app's own client code and a real personal access token. Only statuses, counts and public names were printed.

| Check | Result |
|---|---|
| Settings Test call (`GET /oauth/identity`) | `ok` |
| Auth header `Authorization: Discogs token=…` | accepted |
| `artist_styles("Slowdive")` | 9 styles in 0.7 s (`shoegaze`, `dream pop`, `indie rock`, …) |
| `style_albums("Shoegaze")` | 50 masters in 1.2 s; `Artist - Album` titles parse |
| `artists("slowdive")` | 50 records in 0.4 s |
| `albums("souvlaki")` | 48 usable records of 50 in 2.0 s (two had no ` - ` separator) |
| Wrong token | `ProviderError("failed")`, not an empty list |
| MusicBrainz `/genre/all?fmt=txt` | 2,216 names, includes `shoegaze` |

**Exercised live at the end of P5 (2026-10-26, see `PROJECT_LOG.md`):** Discogs genre extraction, a real HTTP 429 (call 62 of an unpaced burst), the `Ash (2)` suffix, the Settings Test route, and the app against live providers through the API. Not done: the Settings button and the UI in a real browser.

### 13.3 Decisions and deviations

- **Approved by the owner (2026-10-26):** `tag_source: "navidrome"` for owned genre results (3.8), and owned items before unowned on genre pages (similar artists lists unowned first).
- **ListenBrainz is not a genre source** in this build, though 3.8 lists it as a possible `tag_source`. Last.fm tags are not used.
- **Discogs generation not in the similar-artists key.** The cached similar records come only from Last.fm and ListenBrainz; Discogs styles are read from their own generation-keyed cache on every request, so a token change cannot serve stale styles.
- **Manual browser checks were waived by the owner for this batch and not performed.**

### 13.4 Limits carried forward

- Discogs has no style search, so Discogs genre results depend on what the master-release search returns for the query text.
- Genre pages cap unowned items at 30 per section and rely on tag quality at MusicBrainz and Discogs.
- Tag lookups for shared styles add up to about 11 Discogs requests (1 per second) to an uncached artist page, inside the same 3 s page deadline.
- The first-page latency targets in section 2.1 have not been measured (P5).


## 14. Library pages and album page (follow-up to P1 to P4)

Requested by the owner; merged in PR [#630](https://github.com/abucalip/navi-librarian/pull/630) (squash `70b5330`). This section supersedes the P1 rule in 11.5 that albums and songs are reference-only rows. Status: implemented, required CI passed; not yet checked in a browser by the owner.

### 14.1 What changed

- **Navigation.** Every artist, album and genre name opens its library page: search results (a song opens its album), library rows, album rows, similar artists, genre items, and the names and tags on cards, rows and the album panel elsewhere in the app. Only song names are not links. One back stack serves the artist, album and genre pages. Library is also a sidebar tab between Dashboard and Acquisitions.
- **Artist page (`GET /api/artists/{key}`).**
  - `?name=` (with `?mbid=`) serves an artist the library does not have from the network sections alone. Without `name`, an unknown key is still 404.
  - New sections: `tags` (library genre first, then MusicBrainz tags and Discogs styles, at most 8) and `albums` (owned and unowned albums together, at most 20, most listened first). `missing_albums` is unchanged (the unowned subset, at most 50).
  - `albums` items carry `name`, `year`, `key`, `owned`, `id`, `artwork_url`, `release_group_mbid`, `popularity`, `popularity_source` (`listenbrainz` or `lastfm`), `rank` and `sources`. A listen count appears only when the source knows it; Last.fm counts are used only when ListenBrainz knows none of the albums, so the two scales never mix.
  - `owned_albums` items add `id` and `artwork_url`. `similar` items add `key` and `artwork_url`.
  - The stream sends `artist` and `owned_albums` first and every other section as it finishes, so section order after those two is completion order. The page deadline is 8 s (search stays 3 s).
  - `bio`: owned artists use Navidrome (`getArtistInfo2`, source `navidrome`), then Last.fm, then Wikidata; other artists use Last.fm, then Wikidata.
- **MusicBrainz album list.** Studio albums are fetched with a search (`arid:<mbid> AND primarytype:album AND NOT secondarytype:*`), not a browse. A browse returned the first 100 of hundreds of release groups, all live recordings for some artists, so those artists showed no albums, years or listen counts.
- **Album page (`GET /api/albums/{artist_key}/{album_key}`).** Query parameters `id`, `artist`, `name`, `year`, `mbid`; an album the library lacks needs `artist` and `name`, otherwise 404 `unknown_album`. Same envelope as 3.3 with sections `album`, `year`, `description`, `tracks`, `similar_artists` and `similar_albums`, streamed as they finish.
  - `tracks`: from the owned index for an owned album; otherwise the first non-empty answer from Deezer, Last.fm and MusicBrainz, raced. Cached 7 days.
  - `year`: sent at once when known, otherwise looked up through the existing catalogue lookup.
  - `description`: Apple Music's editorial notes, read from the public album page after an exact match. Many albums have none.
  - `similar_albums`: one top Last.fm album per similar artist, for albums the library does not own.
- **Other endpoints.** `GET /api/artist-image?name=` (Deezer photo), `GET /api/album-links?artist=&album=&mbid=` (exact album pages on Apple Music, Deezer, MusicBrainz and ListenBrainz; Spotify, Qobuz and Bandcamp keep search links), `GET /api/album-description?artist=&album=`.
- **Search results.** Song results add `album_id`, `artist` and `artist_key`.

### 14.2 Limits and decisions

- Qobuz and ListenBrainz have no licensed logo; their buttons use drawn monograms (`static/vendor/simple-icons/NOTICE.md`). Spotify, Qobuz and Bandcamp expose no keyless album lookup, so they open a search page.
- Apple Music notes come from the public page, not the catalogue API (which needs a developer token). If Apple changes the page, the description disappears and nothing else breaks.
- Several library artists with one name: a link made from a card (which has no Navidrome ID) opens the one with the most albums.
- Verification: focused tests for the new and changed modules and the UI contract files only; the full suite was not run (owner rule). Live checks against the owner's Navidrome and the public providers were made in an isolated instance. No browser check has been done.
