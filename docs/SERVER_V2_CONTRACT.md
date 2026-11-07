# Server V2 contract (Phases 1 and 3)

Status: draft for the owner's Phase 1 contract review. Route names are **provisional** (`ServerV2.md` section 8) and **no route is served yet**: `navidrome_server.py` takes no additions (D-016). This document fixes the response bodies the builders in `intelligence/api/` already produce; examples are the files in `intelligence/contract-fixtures/`, which `tests/test_intelligence_contract_fixtures.py` rebuilds and compares, so a body change fails CI until the fixtures are regenerated (`python scripts/write_intelligence_fixtures.py`).

## Rules for every endpoint

- Read-only `GET`. Nothing here edits music files or calls a provider.
- No file paths, credentials, tokens or provider URLs in any body.
- Clients hide a section when its feature is unavailable. Unknown keys are ignored; known keys are never removed within a `contract_version`.
- Every body carries `generation` (matching-logic version) and, where it has one, the resource `data_version`.
- Responses for `library-health` and `unresolved` send a weak `ETag` (`W/"<resource>-<generation>-<data_version>"`). A request whose `If-None-Match` matches (weak comparison, comma list, or `*`) gets `304` with no body. `capabilities` and `changes` are never cached (`Cache-Control: no-store`).

## GET /api/capabilities

Served by `app/api/capabilities.py` (`Cache-Control: no-store`). `listenbrainz_connected` is true when a ListenBrainz username is saved; `sonic_available` and `graph_coverage` stay `false` and `none` until a later phase measures them. Reads only the Server V2 store (`intelligence.sqlite3`).

Fixtures: `capabilities_empty.json`, `capabilities_populated.json`.

| Field | Meaning |
|---|---|
| `contract_version` | Integer, `1`. Bumped only for a breaking change. |
| `schema_version` | Store schema version, informational. |
| `generation` | Matching-logic generation. |
| `cursor` | Current change sequence; store it and send it as `since` to `/changes`. |
| `graph_coverage` | `none`, `partial` or `broad`. |
| `sonic_available`, `listenbrainz_connected` | Booleans; unknown means `false`. |
| `features` | Map of feature name to `{available, resource, data_version}`; when `available` is `false` it also has `reason` (`not_populated`). Phase 1 features: `library_health`, `unresolved_queue`. Phase 7 adds `paths`: `resource` `musicbrainz_slice`, available once the MusicBrainz slice is loaded (an available feature can still return an `empty` path for a given artist). |
| `data_versions` | Map of resource to counter. |

## GET /api/changes?since=\<cursor\>

Fixtures: `changes_from_start.json`, `changes_caught_up.json`, `changes_reset.json`, `changes_empty_store.json`.

- `since` is optional (missing or blank means `0`); it must be a whole number of at least 0, otherwise `400` with `{"error": "..."}`.
- Body: `cursor` (new value to store), `reset`, `generation`, `changes[]` of `{resource, data_version, changed_at}`, oldest change first.
- `reset: true` means the client's cursor is ahead of the server (store rebuilt): `changes` lists every resource and the client must refresh everything.
- A client that is caught up gets an empty `changes` list.

## GET /api/library-health

Fixture: `health.json` (includes the `ETag` header).

Body: `albums_checked`, `counts` (every check name, zero when clean), `findings[]`, `not_checked[]`, `data_version`, `generation`. A finding is `{check, severity (info|warn), album_ids[], message, detail{}}`, sorted by check then album. `not_checked` lists checks that need the audio (`suspected_upsampled_or_transcoded`, `clipping`, `measured_loudness`) and are **not** run: a client must not show them as passed. Checks: `missing_album_mbid`, `missing_artist_mbid`, `missing_track_mbid`, `missing_genre`, `track_count_mismatch`, `track_number_problem`, `disc_gap`, `mixed_years`, `replaygain_missing`, `inconsistent_album_artist`. The report is a worklist for external tagging tools. `mixed_years` is a heuristic, not edition detection.

## GET /api/unresolved?status=\&kind=\&limit=\&after_id=

Fixture: `unresolved.json`.

- `status` defaults to `open`; `all` lists every status. `limit` defaults to 50 and is clamped to 1 to 200. `after_id` pages by item id.
- Body: `items[]`, `open_count`, `next_after_id` (`null` on the last page), `data_version`, `generation`.
- Item: `id`, `kind`, `navidrome_ref`, `status` (`open`, `user_confirmed`, `user_rejected`), `reason`, `first_seen`, `candidates[]` (the chosen one has `confirmed: true`).
- Confirm, reject and reopen exist as service functions only. Their `POST` routes are a later slice and need owner approval of the wording before any client shows a confirm button.

## GET /api/insights

Fixtures: `insights_all_off.json`, `insights_three_on.json` (Phase 3). Served by `app/api/insights.py` (D-016: nothing added to `navidrome_server.py`); the body builder is `intelligence/api/insights.py`. The store is `intelligence.sqlite3` in the data directory (D-026). Query: `limit` (1 to 100, default 20, else `400`). Lenses are enabled only by the `NAVI_INSIGHT_LENSES` environment variable (comma separated lens kinds); none by default.

Knowledge pages (Phase 4): fixtures `knowledge_album.json`, `knowledge_person.json`, `knowledge_person_slice_pending.json`, `knowledge_label.json`, `knowledge_work.json`, `knowledge_recording_works.json`, `knowledge_place.json`, `knowledge_event.json` (Phase 5; connections fixtures are listed with that route below), built from a small store of their own with fixed ids and clock. Routes `GET /api/knowledge/album|person|label|work|recording-works` (`app/api/knowledge.py`); bodies carry `mbid` only and every `owned` flag is a boolean. The pending fixture shows a store with no MusicBrainz slice loaded (`sources.musicbrainz_dump.coverage` is `pending`).

- Body: `lenses` (map of lens kind to `{enabled, cards[]}`), `data_version`, `generation`. Lens kinds: `forgotten_gem`, `blind_spot`, `series_completion`, `hidden_canon`, `anniversary`.
- A lens contributes cards only when it is enabled. A lens is enabled by default only when its scorecard verdict is `pass`; today none is (all four provider lenses are `insufficient_evidence`, Forgotten Gems has too little play history). A client shows "off" for `enabled: false` and an empty state for `enabled: true` with no cards; it never invents cards.
- Card (all kinds): `kind`, `title`, `body`, `subject{key, type, title, ...}`, `reasons[]` (each `{kind, evidence{}}`), `actions[]` (`{kind: "dismiss"}`), `dismissible`, `score`, plus kind-specific counters (`owned`, `total`, `missing_runs`, and so on). Wording states a fact (a count, a date, a listen total), never "you should own".
- `subject.key` is the dismissal and accept key. Actions: `POST /api/insights/{kind}/dismiss|restore|accept|unaccept` with JSON `{"key": "<subject.key>"}`, answering `{"changed": bool}` (`false` when nothing changed, for example a repeat dismiss or accepting a dismissed key); unknown kind `404`, missing key `422`. Restore lifts the suppression; the card returns at the next refresh.
- `capabilities` gains the `insights` feature (`available` once any card row has been saved).
- Filling the store: `app/services/insights_refresh.py` runs `intelligence.insights.refresh_forgotten_gems` at startup and every 6 hours, only when `forgotten_gem` is listed in `NAVI_INSIGHT_LENSES`. It reads the Navidrome album list (play count, last played, star, rating) and nothing else; an empty album list is a failed run that keeps the saved cards, and a library with sparse history saves no cards. With `blind_spot`, `hidden_canon` or `anniversary` listed, the same loop also runs `intelligence.insights.refresh_provider_lenses` (owner-approved provider traffic, 2026-11-05): per 6-hour tick it records up to 40 Navidrome artists (those with an MBID), then spends at most 120 MusicBrainz and ListenBrainz requests (paced 1.1 s and 0.5 s) on release browses (linking owned releases to release groups), studio discographies, ListenBrainz top release groups and artist life-spans, cached in the store (30-day freshness, never-fetched first). The three lenses are recomputed and saved only once every owned artist has been browsed and has all three documents, so a half-linked library never shows false gaps; until then saved cards stay as they were. A provider failure fails the run and keeps the cache. Series are refreshed too (PR #801): series ids are discovered from the owned release groups' own MusicBrainz series relations, within the same tick budget, only when `series_completion` is listed.

## POST /api/feedback/events (Phase 6 item 5, D-027)

Served by `app/api/feedback.py`; body builder `intelligence/api/feedback.py`. Fixtures: `feedback_events_first.json` and `feedback_events_replay.json` (same request body, so the replay shows nothing new is stored), built with a fixed clock; both clients decode them. Authenticated like every `/api` route. Record-only: nothing reads the stored events for ranking, lenses, radio, cards or playlists. Events stay on the server, are never sent to a provider, and are not logged beyond counts.

- Request: `{"events": [...]}`, at most 100 events. Over 100 is refused whole with `400` and nothing is stored; a missing or non-list `events` is `422`.
- Event: `event_id` (client-generated UUID; the server lowercases it, so retries are idempotent), `client` (`macos` or `android`), `kind` (`skip` or `dismiss`), `subject_kind` (`track`, `album`, `artist` or `card`), `subject_id` (non-empty, at most 200 characters; the Navidrome id, or the card key for `card`), optional `mbid` (UUID), `occurred_at` (epoch seconds, more than 0 and at most 300 s in the future), and for tracks only optional `played_seconds` and `duration_seconds` (0 or more). A `skip` must be a `track`. No file paths, tokens, device names or free text.
- What counts as a skip is decided by the client: a track abandoned before 30 s or before 50 percent of its length, whichever comes first, and not at the end of a queue. These are starting values, not measured; the server stores what the client reports and never re-derives it.
- Response `200`: `received`, `inserted` (new rows), `accepted`, `rejected`, and `results[]`, one per input item in order: `{index, status: "accepted", duplicate}` or `{index, status: "rejected", reason}`. A replay of a stored event, or a repeated id inside the batch, is `accepted` with `duplicate: true` and changes nothing. A malformed item is rejected without losing the rest.
- Rejection reasons: `not_a_mapping`, `bad_event_id`, `bad_client`, `bad_kind`, `bad_subject_kind`, `bad_subject_id`, `skip_needs_track`, `bad_mbid`, `bad_occurred_at`, `future`, `bad_played_seconds`, `bad_duration_seconds`, and `event_id_conflict` (the id is already stored with a different payload; the stored row is kept). A client must not retry a rejected item unchanged.
- A storage failure is `502` with a fixed message that never echoes event content.

## GET /api/insights/suppression (Phase 6 item 5, D-027)

Fixture: `suppression.json`. Query: `limit` (1 to 200, default 50) and `offset` (0 or more), else `400`.

- Body: `entries[]`, `total`, `next_offset` (`null` on the last page), `as_of` (server clock used), `record_only` (always `true`), `config`.
- Entry: `subject_kind`, `subject_id`, `weight` (0 to 1: the sum of active event weights, each `2 ** (-age / 14 days)`, zero after 60 days, capped at 1.0), `events` and `skips` (active counts), `last_event_at`. Newest `last_event_at` first.
- A subject is judged only by its own events: a skipped track never creates an album or artist entry. Sparse or empty memory is an empty list, never an error. Weights are derived on each read; the 14-day, 60-day and 100-event values are starting values reused from the negative-feedback policy, not measured. Events older than 180 days are removed by a retention sweep that nothing runs yet.
- A client may show these entries but must not treat them as an instruction to hide anything: no ranking uses them.

## Smart playlists: `/api/playlists/smart` (Phase 6 item 6, slice 14)

Served by `app/api/smart_playlists.py`; body builders `intelligence/api/smart_playlists.py`; rules in `intelligence/taste/smart_playlist.py`, storage in the owner-state file (`state.smart_playlists`). Fixtures: `smart_playlists_empty.json`, `smart_playlist_put_first.json`, `smart_playlist_put_replay.json`, `smart_playlist_put_rejected.json`, `smart_playlists_list.json`, `smart_playlist_result.json` (fixed clock). Authenticated like every `/api` route. Rule sets are owner configuration. The server never writes a playlist to Navidrome and makes no provider call; there is no scheduled refresh.

- `GET /api/playlists/smart`: `{playlists[], total, config}`, oldest first. `config` lists the accepted fields, operators, orders, matches and limits so a client need not hard-code them. No rule sets is an empty list.
- `PUT /api/playlists/smart/{rule_id}`: create or replace. `rule_id` is a client-chosen lowercase UUID, so a retry is idempotent. Body: `name` (1 to 100 characters), `match` (`all` or `any`, default `all`), `rules[]` of `{field, op, value}` (at most 20), `order` (default `random`), `limit` (25 to 250 or `null`). Answers `200 {status: created|replaced|unchanged, playlist}`; `unchanged` leaves `updated_at` alone. Invalid content is `400 {status: "rejected", errors: [{path, reason}]}` and nothing is stored; a bad id is `400`; a body that is not an object is `422`.
- `GET /api/playlists/smart/{rule_id}`: one rule set, `404` if absent. `DELETE` answers `{deleted: true}`, `404` if absent.
- `GET /api/playlists/smart/{rule_id}/result?seed=<int>`: evaluates now over the whole Navidrome song list (paged `search3`, up to 50,000 songs) and returns `{rule_id, song_ids[], matched, returned, unfinished[], missing_data[], evaluated_at, songs_considered, stored: false}`. `unfinished` holds rule indexes that match every song (empty or non-numeric value, or missing insight data); `missing_data` names the missing lookups. Neither is an error. `seed` fixes the `random` order. A Navidrome failure is `502` with a fixed message.
- Insight fields: no obscurity bands or lens members are wired yet, so `obscurity_band` and `in_lens` rules are unfinished and reported in `missing_data`. `suppressed` is not offered.
- Semantics match the macOS engine (unfinished rules match everything, unknown numbers never match, never-played matches "last played at least N days ago"); ties break on the Navidrome id.

## GET /api/insights/taste (Phase 6)

Served by `app/api/insights.py`; body builder `intelligence/api/taste.py`; no fixture yet. Read-only: it returns the last saved taste profiles and never computes, fetches or changes anything.

- Body: `profiles`, `data_version`, `generation`. `profiles` is `null` until a run has saved some (nothing fills the store yet: the scheduled job and listens fetching are later slices), so "not computed" is distinct from "computed but sparse".
- `profiles`: `windows` (`recent`, `mid`, `all_time`, each with `listens`, `low_sample`, `attributed` and `dimension_low_sample` per dimension, and `dimensions` mapping genre, era, area, label and collaborator to ranked `{value, count, share}`), `shifts[]` (`{window, dimension, value, direction, from_share, to_share}`, stated only when both sides are sound), `config` (the thresholds used), `load` (`total`, `unusable`, `unmatched`, `attributed`, when the loader ran), `computed_at`, `generation`. A client must show `low_sample` windows and dimensions as such and must not state a shift that is not listed.
- Stored as one `taste_profile` row in `insights`; an unchanged recompute writes nothing and keeps `data_version`. The profiles do not change recommendation weights.

## POST /api/insights/popularity/fill and GET /api/insights/popularity/status (Phase 6 item 2, slice 18)

Served by `app/api/popularity.py` (D-016: nothing added to `navidrome_server.py`); job logic in `intelligence/taste/popularity_job.py`. The owner triggers the fill by hand only: there is no scheduler and no startup hook. No fixture yet.

- Fill body: optional JSON `{"max_requests": n}`, a positive integer, default 5, capped at 20 (a larger value is applied as 20 and the body reports `max_requests`). Anything else is `422`. Each run makes at most that many ListenBrainz batch requests (100 MBIDs each) and then stops; a run with artists still pending answers `queued` and the next run resumes it.
- Fill answer: `run_id`, `state` (`succeeded`, `queued`, `failed`), `progress` (`requests`, `filled`, `absent`, `pending`), `error` (null unless failed) and `max_requests` (the applied value). A failed run keeps every figure saved before it and the last good figures of other artists. A run refused because another is in progress is `409`.
- Status answer: `status` (the newest run of job `taste_popularity`), `last_good` (the newest succeeded run) and `running` (true while a fill holds the process lock). The status route makes no provider call.
- Requests carry a `User-Agent` of `Discair/1.0 (...)` and `Authorization: Token <LISTENBRAINZ_TOKEN>`, the token read only from `config.env` in the working folder (key `LISTENBRAINZ_TOKEN`). The token is never logged, returned or stored.
- Figures are saved in `state.artist_popularity` and are the only write. Obscurity-band smart-playlist rules stay `missing_data` until figures are saved.

## GET /api/knowledge/{album,person,label,work,recording-works} (Phase 4)

Served by `app/api/knowledge.py` (D-016: nothing added to `navidrome_server.py`). Every body is built by `KnowledgeReader` (`album_dossier`, `person_page`, `label_page`, `work_page`, `works_of_recording`) from `intelligence.sqlite3`; no provider traffic, no writes, no ownership flags. The page shapes are those the reader returns, with provenance on every credit and a `coverage` field (`pending`, `loaded`, `no_relationships_in_slice`) instead of a silent empty list.

- `album`: `mbid` or `navidrome_id`, `type` = `release` (default) or `release_group`, `limit` 1 to 500 (default 100).
- `person`: `mbid` or `navidrome_id`, `type` = `artist` (default), `person` or `group`, `limit` 1 to 500 (default 200).
- `atlas` (Phase 7, `KnowledgeReader.atlas_page`, `intelligence/knowledge/atlas.py`): `limit` 1 to 2000 (default 500). `places[]` of every place with both coordinates stated and at least one firmly matched, non-inferred place-to-recording link: `entity` (`mbid`, `canonical_name`), `kind`, `latitude`, `longitude`, `recordings`, `owned_recordings` (owned itself, or on an owned release or group), most owned first; `truncated`; `sources.musicbrainz_dump.coverage`. Nothing is geocoded.
- `label`, `work`, `place` and `event`: `mbid` (required, else `422`), `limit` 1 to 500 (default 200). `place` (Phase 5, `KnowledgeReader.place_page`) answers facts (kind, coordinates, dates), `area` (the area MusicBrainz states, each with `contained_in`, its stated containment chain nearest first, with `kind` and `iso_code`), `recordings` (with albums and `owned`), `people` and `events`. `event` (`event_page`) answers facts (kind, dates, `cancelled`), `places`, `area`, `people` and `recordings`. A country appears only in a stated chain; nothing is derived from names, labels or one recording location. An mbid of another entity type is `404`.
- `timeline` (`GET /api/knowledge/timeline`, Phase 7 client gate, `KnowledgeReader.timeline_page`): `mbid` or `navidrome_id` (else `400`), `type` (`artist`, `person` or `group`, else `400`), `limit` 1 to 500 (default 200). Body: `person`, `life_span`, `items` (albums from the person page plus events; each with `kind`, `entity`, `owned`, `date`, `why`, `relations`, `evidence`, and for events `event_kind` and `cancelled`), `undated` (count), `truncated`, `sources` and `not_loaded`. Dated items come first, oldest first; an album's date is the earliest `release_facts` date of any edition in its release group, an event's is its stated begin date. Nothing is dated from a file tag, and an undated item is listed last, never placed. Read-only, no provider call. Fixture not yet recorded.
- `recording-works`: `mbid` or `navidrome_id`, `limit` 1 to 500 (default 50).
- `connections` (`GET /api/knowledge/connections`, bounded graph walk, Phase 4 item 6): `mbid` or `navidrome_id` plus `type` (all required, else `400`), optional `credits_only`, repeatable `relation`, `direction` = `out`, `in` or `both` (default), `depth` 1 to 3 (default 1, else `422`), `limit` 1 to 500 (page size, default 50), `cursor` (opaque, from `next_cursor`; a bad one is `400`). Body: `start`, `hops` (each with `entity`, `depth`, `via_mbid`, `credit` and `evidence` with source, evidence class and match quality), `next_cursor`, `truncated` (`rows`, `time` or null) and `sources.musicbrainz_dump.coverage`. Each entity appears once at its shortest depth; inferred or unconfirmed edges are never `credit`. The walk stops at 200 rows or 2 seconds. Fixtures: `knowledge_connections.json` (depth 2, one page), `knowledge_connections_page1.json` and `knowledge_connections_page2.json` (page size 2; the second request carries the first body's `next_cursor`).
- `paths` (`GET /api/knowledge/paths`, Phase 5 discovery paths): `kind` (required, else `422`; one of `follow_the_musician`, `sideman_to_leader`, `label_path`, `composition_path`, `scene_path`; the dropped `same_studio_different_decade` answers `400` with the reason), `mbid` or `navidrome_id` (else `400`) and `type` (`artist`, `person` or `group`, else `400`). Body: `kind`, `start`, `status` (`ok` or `empty`; no stop is ever padded in), `stops` (each with `entity`, `reason_count` and up to three `reasons`, each with `code`, `text`, `via`, `anchor` and `evidence` with source, evidence class and match quality), `truncated` (`rows`, `time`, `stops` or null) and `sources.musicbrainz_dump.data_version`. Edges that are inferred or unconfirmed are never used. Built on demand within 3,000 rows, 30 stops and 2 seconds, cached by (start, kind, generation) in the Server V2 file (the only write; a path cut short by time is not cached). Unknown start `404`. Recorded responses: `android/contract-fixtures/librarian/paths_*.json` (one `ok` and one `empty` per kind, the `400` same-studio refusal, `400` unknown kind, `422` missing kind, `400` missing identifier and type, `404` unknown entity; captured 2026-11-07 from a copy of the owner's local store). `sideman_to_leader` (stops are artists; reason code `sideman_on`, `via` the release, `anchor` the recording): `paths_sideman_to_leader.json` (`ok`), `paths_sideman_to_leader_empty.json` (`empty`) and `paths_sideman_to_leader_truncated.json` (`truncated: stops`, 30 stops). The `ok` and `truncated` responses are the first match among the first 80 owned artists, captured 2026-11-07 from a copy of the owner's store after the MusicBrainz slice re-import (`track_on` and `release_artist` links present). No `502` was recorded.
- Context readers (Phase 5, additive keys): each album edition carries `formats` (text such as `2×Vinyl`, or null) and `catalogue[]` of `{label{mbid,name} or null, catalogue_number or null, source}`; a label page carries `parents[]` and `sub_labels[]` (the `label ownership` relation by direction; `related_labels` is unchanged) and `catalogue_numbers[]` on every catalogue row. `catalogue_numbers` and `formats` stay in `not_loaded` while the store holds none (a slice imported before schema 4), so a client says "not loaded", never "none".
- Errors: neither identifier `400`; bad `type` `400`; `limit` out of range `422`; entity not in the store `404`; store unreadable `502`.
- Shape (owner decisions, 2026-11-06): the page shapes are approved. Bodies carry `mbid` and never a store `id`, `created_generation`, `navidrome_id`, `discogs_id` or `wikidata_id` (`intelligence/knowledge/public.py`). Every `owned` flag is a boolean, and a release group is owned when any of its editions is. Clients show at most ten credits per list and a "more" control for the rest (the body still carries up to `limit`).
- Not yet fixtured and no client uses these routes; fixtures come next.

## Not in this contract

Entity pages and path `reasons[]` (later phases); any scheduling or trigger route for the health job; macOS Swift fixtures (the macOS Health view is the Phase 1 client gate and will consume these JSON files directly).
