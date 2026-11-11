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
- Filling the store: `app/services/insights_refresh.py` (started by the worker process, `python -m app.worker`) runs `intelligence.insights.refresh_forgotten_gems` at startup and every 6 hours, only when `forgotten_gem` is listed in `NAVI_INSIGHT_LENSES`. It reads the Navidrome album list (play count, last played, star, rating) and nothing else; an empty album list is a failed run that keeps the saved cards, and a library with sparse history saves no cards. With `blind_spot`, `hidden_canon` or `anniversary` listed, the same loop also runs `intelligence.insights.refresh_provider_lenses` (owner-approved provider traffic, 2026-11-05): per 6-hour tick it records up to 40 Navidrome artists (those with an MBID), then spends at most 120 MusicBrainz and ListenBrainz requests (paced 1.1 s and 0.5 s) on release browses (linking owned releases to release groups), studio discographies, ListenBrainz top release groups and artist life-spans, cached in the store (30-day freshness, never-fetched first). The three lenses are recomputed and saved only once every owned artist has been browsed and has all three documents, so a half-linked library never shows false gaps; until then saved cards stay as they were. A provider failure fails the run and keeps the cache. Series are refreshed too (PR #801): series ids are discovered from the owned release groups' own MusicBrainz series relations, within the same tick budget, only when `series_completion` is listed.

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

Served by `app/api/insights.py`; body builder `intelligence/api/taste.py`; headline builder `intelligence/taste/headline.py`. Read-only: it returns the last saved taste profiles and never computes, fetches or changes anything. Fixtures: `intelligence/contract-fixtures/taste_rich.json`, `taste_thin_window.json`, `taste_sparse_dimension.json` and `taste_empty.json`.

- Body: `profiles`, `context`, `data_version`, `generation`. Both `profiles` and `context` are `null` until the on-demand refresh has saved them; the refresh route is the only writer and there is no scheduler or startup hook. `context`, when present, is `{kind, timezone (UTC), listens, lenses{time_of_day{night,morning,afternoon,evening}, day_type{weekday,weekend}} (each context shaped like a window: listens, low_sample, attributed, dimension_low_sample, dimensions), contrast{between [morning, night], min_listens (100), listens, state (stated, no_difference, low_sample), entries[{dimension, value, morning, night}]}, computed_at, generation}`. A client states a contrast only when `state` is `stated` and shows low-sample contexts as such. `profiles` distinguishes not-computed (`null`) from computed-but-sparse (per-window and per-dimension low-sample flags).
- `profiles`: `kind`, `headline`, `windows` (`recent`, `mid`, `all_time`, each with `listens`, `low_sample`, `attributed` and `dimension_low_sample` per dimension, and `dimensions` mapping genre, era, area, label and collaborator to ranked `{value, count, share}`), `shifts[]` (`{window, dimension, value, direction, from_share, to_share}`, stated only when both sides are sound), `config` (the thresholds used), `load` (`total`, `unusable`, `unmatched`, `attributed`, when the loader ran), `computed_at`, `generation`. A client must show `low_sample` windows and dimensions as such and must not state a shift that is not listed.
- `headline`: `null` when no window is sound enough to say anything (the client shows its progress state), else `{text, kind, window, subjects: [{dimension, value, direction}]}`. `kind` is `pair` ("More X, less Y lately."), `up` ("Leaning into X lately."), `down` ("Drifting from X lately.") or `steady` ("Your taste has held steady.", no subjects). `window` is `recent`, or `mid` ("this past year") when recent is low-sample. The client draws `text` as given and never composes prose. Wording is a starting value, not measured.
- Stored as one `taste_profile` row in `insights`; an unchanged recompute writes nothing and keeps `data_version`. Rows saved before `headline` existed are rewritten once by the first save after the change. The profiles do not change recommendation weights.

## POST /api/insights/taste/refresh and GET /api/insights/taste/refresh/status (Phase 6 presentation slice 3)

Served by `app/api/taste_refresh.py`; logic in `intelligence/taste/refresh.py` (D-016). Clients call the refresh on launch; there is no scheduler or startup hook. Raw listens are read from the owner's ListenBrainz history (read-only; token from the saved Settings or `LISTENBRAINZ_TOKEN`) only after the interval has passed. The reader walks year-sized windows to the 13-year floor; any unanswered window or window that reaches the 50-page/5,000-listen cap fails the run and keeps saved profiles rather than accepting partial history. No ListenBrainz username: `no_listens_source`.

- Refresh answer: `state` (`refreshed`, `unchanged`, `too_soon`, `failed`, `no_listens_source`), `run_id`, `changed`, `retry_after` (seconds, `too_soon` only), `progress` (`changed`, `listens`, `unusable`, `unmatched`) and `error`. Minimum interval one hour after the last success; failed attempts do not start it. An overlapping call is `409`.
- Status answer: `status` (newest run of job `taste_refresh`), `last_good`, `running`, `min_interval`, `retry_after`.
- Windows end at the start of the current UTC day, so an unchanged replay writes nothing and keeps `data_version`. Profiles change no recommendation weight.

## POST /api/insights/popularity/fill and GET /api/insights/popularity/status (Phase 6 item 2, slice 18)

Served by `app/api/popularity.py` (D-016: nothing added to `navidrome_server.py`); job logic in `intelligence/taste/popularity_job.py`. The owner triggers the fill by hand only: there is no scheduler and no startup hook. No fixture yet.

- Fill body: optional JSON `{"max_requests": n}`, a positive integer, default 5, capped at 20 (a larger value is applied as 20 and the body reports `max_requests`). Anything else is `422`. Each run makes at most that many ListenBrainz batch requests (100 MBIDs each) and then stops; a run with artists still pending answers `queued` and the next run resumes it.
- Fill answer: `run_id`, `state` (`succeeded`, `queued`, `failed`), `progress` (`requests`, `filled`, `absent`, `pending`), `error` (null unless failed) and `max_requests` (the applied value). A failed run keeps every figure saved before it and the last good figures of other artists. A run refused because another is in progress is `409`.
- Status answer: `status` (the newest run of job `taste_popularity`), `last_good` (the newest succeeded run) and `running` (true while a fill holds the process lock). The status route makes no provider call.
- Requests carry a `User-Agent` of `Discair/1.0 (...)` and `Authorization: Token <LISTENBRAINZ_TOKEN>`, the token read only from `config.env` in the working folder (key `LISTENBRAINZ_TOKEN`). The token is never logged, returned or stored.
- Figures are saved in `state.artist_popularity` and are the only write. Obscurity-band smart-playlist rules stay `missing_data` until figures are saved.

## `listens_by_day` on GET /api/insights/taste (redesign D2, redesign S1)

Built in `intelligence/taste/listens_by_day.py` (D-016: nothing added to `navidrome_server.py`); the field is added by `intelligence/api/taste.py` and saved by the taste refresh. The macOS Home (redesign M8) already reads it. Fixture: `taste_listens_by_day.json`. Not yet checked against the owner's live ListenBrainz history.

- Body field `listens_by_day`: an array of `{date, count}`, one entry per UTC calendar day for the 84 complete days before the refresh's day, oldest first, **zero days included** (the client needs at least 14 entries and treats the last 7 against the 7 before). `date` is `YYYY-MM-DD`; `count` is a non-negative integer. The field is absent, not empty, until a refresh has saved it (so also when no listens source is set); the other taste fields are unchanged.
- Built from the listens the taste refresh already read, with no extra provider call, and saved as one `taste_listens_by_day` row in `insights` (no migration; an unchanged series writes nothing). The route stays read-only. The series ends at the day before the day the last refresh ran, so a stale series is visible from its last date ("as of 9 November"). A listen without a usable timestamp is not counted.

## Proposed: GET /api/insights/refresh/status (redesign D3)

Not built on the server. Home's Server activity row for the insight lenses reads it; without it the row falls back to when the app last read the cards.

- Same shape as `GET /api/insights/taste/refresh/status`: `status` (newest run of the lens refresh job), `last_good`, `running`, `min_interval` (seconds) and `retry_after` (seconds until the next run is due, 0 = now). The client writes "Refreshed 2 hours ago · next in 4 hours" from `last_good.finished_at` and `retry_after`. Read-only; makes no provider call.

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
- Album dossier `recording_places[]` (additive): place, event and area links to the album's recordings, each `{entity, relation, role, track, valid_from, valid_to, source, source_url, evidence_class, match_quality}`; `recording_places_and_dates` leaves `not_loaded` once the store holds any such link. Fixture `knowledge_album.json` re-recorded.
- Context readers (Phase 5, additive keys): each album edition carries `formats` (text such as `2×Vinyl`, or null) and `catalogue[]` of `{label{mbid,name} or null, catalogue_number or null, source}`; a label page carries `parents[]` and `sub_labels[]` (the `label ownership` relation by direction; `related_labels` is unchanged) and `catalogue_numbers[]` on every catalogue row. `catalogue_numbers` and `formats` stay in `not_loaded` while the store holds none (a slice imported before schema 4), so a client says "not loaded", never "none".
- Errors: neither identifier `400`; bad `type` `400`; `limit` out of range `422`; entity not in the store `404`; store unreadable `502`.
- Shape (owner decisions, 2026-11-06): the page shapes are approved. Bodies carry `mbid` and never a store `id`, `created_generation`, `navidrome_id`, `discogs_id` or `wikidata_id` (`intelligence/knowledge/public.py`). Every `owned` flag is a boolean, and a release group is owned when any of its editions is. Clients show at most ten credits per list and a "more" control for the rest (the body still carries up to `limit`).
- Not yet fixtured and no client uses these routes; fixtures come next.

## GET /api/sonic/similar and GET /api/sonic/path (Phase 7)

Served by `app/api/sonic.py` over `intelligence/sonic/proxy.py`: Navidrome's `getSonicSimilarTracks` and `findSonicPath` with Librarian's rules. Read-only, no store access, no provider traffic; answers are kept for an hour. Clients show the feature only when `GET /api/capabilities` says `sonic_available: true`.

- `similar`: `id` (required, a Navidrome song id), `count` (1 to 50, default 10). Up to `count` owned tracks in Navidrome's order. Near-duplicates of the seed (same recording or same title by the same artist) are dropped, and at most 2 matches may be by the seed's own artist (`dropped.artist_cap` counts the rest).
- `path`: `start` and `end` (required, different songs, else `400`), `count` (2 to 50, default 10). Ordered steps from the start song to the end song; the first step is the start song.
- Body: `status` (`ok` or `empty`; `empty` means the song has no analysis data, 2 of 250 sampled), `seed` (the seed song, `null` on a path), `tracks[]`, `dropped` (`same_recording`, `repeat`, `artist_cap`). A track has `navidrome_id`, `title`, `artist`, `artist_id`, `album`, `album_id`, `duration`, `year`, `mbid`, `cover_art`, `owned` (always `true`) and `similarity`. **Do not threshold or sort on `similarity`**: it sits in a narrow band (median 0.92), is informational, and is `null` on every path step.
- Errors: `404` unknown song; `502` sonic similarity unavailable or Navidrome did not answer (fixed text, never Navidrome's); `422` for a missing parameter or a count out of range.

Fixtures (recorded from the owner's Navidrome, read-only, 2026-11-07): `sonic_similar.json`, `sonic_similar_empty.json`, `sonic_path.json`, `sonic_error_not_found.json`, `sonic_error_unavailable.json`.

## POST /api/knowledge/paths/warm and GET /api/knowledge/paths/warm/status (Phase 7)

Served by `app/api/paths_warm.py`. A manual trigger that builds the missing or stale cached paths for every owned artist, so the first `GET /api/knowledge/paths` from a client is a cache read. No scheduler, no startup hook, no provider traffic. Clients do not call it.

- Optional JSON body: `max_seconds` (positive number, default 300, capped at 1800) and `kinds` (non-empty list of path kinds, default all five). Anything else is `422`.
- Answer: `run_id`, `state` (`succeeded`, or `queued` when the time budget ended first: call again to resume), `progress` (`built`, `skipped` for current caches, `empty`, `timed_out`, `pending`), `error`, `max_seconds`, `kinds`. `409` while another warm-up is running; `502` when it could not run.
- Status: `status` (the latest run), `last_good`, `running`.

## Album paths: `GET /api/knowledge/paths` with `type=release` or `release_group`, and `GET /api/sonic/album-neighbours` (Phase 7, album Paths button)

Decided in [ALBUM_PATHS_PROPOSAL.md](ALBUM_PATHS_PROPOSAL.md) (owner, 2026-11-09). **Status: `GET /api/knowledge/paths` serves `album_crew`, `album_guests`, `album_works`, `album_room` and `album_moment` for `type=release`; `album_gaps` answers `501` (Gaps needs play history the route does not read yet); `type=release_group` answers `404` or `400` until a release-group builder exists; `GET /api/sonic/album-neighbours` is served (PR #926).** Bodies are the builders' (`intelligence/graph/album_paths.py`, `album_gaps.py`, `intelligence/sonic/neighbours.py`) in the public shape (mbid only, boolean `owned`; `presentation_version` is not returned). Path and Sonic fixtures are recorded; Gaps is not, so a client must not treat that part as final. Everything in "Rules for every endpoint" applies, and so do the artist-path rules: credit-grade evidence only (an inferred edge, or one whose other end is unconfirmed or unresolved, is never used, not even as a bridge), no stop without a `reasons[]` entry, nothing padded in, no provider traffic.

### Request

Same route and decoder as artist paths. Differences:

- `type`: `release` or `release_group` selects an album start. `mbid` or `navidrome_id` identifies it (else `400`). A start that is not a release or release group is `400`; an unknown start is `404`.
- `kind` (required, else `422`): one of `album_crew`, `album_guests`, `album_works`, `album_moment`, `album_room`, `album_gaps`. An artist kind with an album `type`, or an album kind with an artist `type`, is `400`. `album_sonic_neighbours` is not a `kind` here; it has its own route (below).
- The button lists only album kinds. Album paths never repeat the artist's own five kinds (see `overlap_dropped`).

### Body

As artist paths: `kind`, `start`, `generation`, `status` (`ok` or `empty`), `stops`, `truncated` (`rows`, `time`, `stops` or null), `built_from.musicbrainz_dump` (data version) and `presentation_version`. Each stop is `{entity, presentation, reason_count, reasons[]}` with at most three reasons, each `{code, text, via, anchor, evidence}`. A stop is always an owned album. Additions:

- `overlap_dropped`: count of stops removed because the credited artists' five artist paths already reach that album (owner decision 4: dropped even when the reason differs). A build that runs out of time during that check is `truncated: "time"`.
- `capped[]`: `{via, more}` for each person or work whose albums were cut at the per-person cap (50) or per-work cap (20); `more` is the count left out. A client shows "and N more", never hides it.
- Ranking: most distinct people (or works) first, then the nearer link, then the earlier release date. Similarity and play data are never a sort key.
- Built on demand within the artist-path bounds (3,000 rows, 30 stops, 2 seconds), cached by (start, kind, generation) with the paths cache; a path cut short by time is returned but not cached. No warm-up: `POST /api/knowledge/paths/warm` stays per owned artist.

### Kinds and reason codes

| Kind | Stops follow | Reason codes (`via`, `anchor`) |
|---|---|---|
| `album_crew` (Studio Crew) | producer, engineer, mix and mastering credits on this album to other owned albums with the same person | `crew_on` (the person, the credited album) |
| `album_guests` (Guest List) | instrument, vocal and performer credits on this album, minus its own credited artists | `guest_on` (the person, the credited track) |
| `album_works` (Covers and Sources) | the work behind each track to other owned recordings of it, and to works linked by `parts`, `other version`, `arrangement` or `based on` | `same_work`, `derived_work` (the work, the track) |
| `album_moment` (Same Year, Same Scene) | owned albums whose earliest `release_facts` date is within 2 calendar years of this album's, **and** a stated link | `same_period_label` (label), `same_period_credit` (shared credited artist), `same_period_area` (stated non-country area of two different credited artists); `via` is the label, artist or area, `anchor` the start album |
| `album_room` (Same Room) | recordings with a stated place or event to other owned recordings made there | `recorded_at` (the place or event, the track). Place and event links `recorded at`, `mixed at` and `engineered at` on recordings only, never an area; a hub place keeps 50 albums, listed in `capped[]`. |
| `album_gaps` (Listen-through Gaps) | the `album_crew` and `album_guests` stops with fewer than 2 plays | the base stop's own `crew_on` and `guest_on` reasons; nothing added |

- A date match alone never produces a `album_moment` stop; an undated start or candidate gives none. File-tag years are never used.
- A person with both crew and guest credits is one stop with both reasons, not two stops.
- `reasons[]` text templates follow the artist-path pattern: name the person, work or place, name the credit, name both albums.

### `album_gaps` additions

Play history only selects and labels; it never adds a stop and never reorders by affinity (taste rule). Order is the base order: crew stops first, then guest-only stops. Each stop has `play`: `{state, play_count, text}` with `state` `never` or `little`, or `null` when the history is not usable. The body adds:

- `history`: `{state, played_albums, filtered_out, unknown, little_plays_below, filtered}`. `state` is `ok`, `thin` (fewer than 20 albums with any play) or `unavailable` (play records could not be read).
- On `thin` or `unavailable` every base stop is returned unfiltered with `play: null` and `filtered: false`. A client says the history is not enough; it never shows an empty "not played" claim.
- An album with no record in a usable history is counted in `history.unknown` and left out; absence of a record is not "never played".
- The cutoff of 2 and the minimum of 20 are provisional. This kind is not cached (it depends on play data that changes).

### `GET /api/sonic/album-neighbours?album_id=` (Neighbours by Ear)

Served by `app/api/sonic.py` (PR #926). `album_id` is a Navidrome album id (required, else `422`). Clients show it, in its own tab, only when `GET /api/capabilities` says `sonic_available: true`.

- Method: up to 8 seeds, evenly spaced over the tracklist, first and last always included, deterministic. One similar-track call per seed. Matches on the start album are dropped; the per-artist cap of 2 per seed applies. An unanalysed seed is skipped, reported in `skipped` and replaced by the next unused track (at most 16 calls). `similarity` is never read, sorted or thresholded.
- Body: `status` (`ok` or `empty`), `start` (`album_id`, `album`, `artist`, `year`, `tracks`), `stops[]`, `seeds[]` (`navidrome_id`, `title`), `skipped[]` (`navidrome_id`, `title`, `reason` `no_analysis`), `truncated` (`time` or null).
- Stop: `album_id`, `album`, `artist`, `artist_id`, `cover_art`, `year` (from the matched tracks, not release facts), `match_count`, `matches[]` (`seed` and the matched `tracks`), `owned` (always `true`) and `reasons[]` with one `{code: "sonic_neighbour", count, text}`. Ranked by `match_count`, ties by earliest year then album id. This is not a graph path, so there is no `evidence`; it is composed from Navidrome's analysis.
- Bounded at 5 seconds; an answer cut short by time has `truncated: "time"` and is not cached. Otherwise cached for an hour with the other sonic routes.
- Errors: `404` unknown album; `502` sonic similarity unavailable or Navidrome did not answer (fixed text); `422` missing `album_id`.
- Provisional: counts are lower bounds because some returned tracks have no matching owned recording. The wider-sample coverage re-measure (60% gate) is a build-time requirement and is still open.

### Client rules

- Hide the Paths button when the album has no album kind with stops. Hide Neighbours by Ear unless `sonic_available`.
- Say `empty` as "nothing found", and a missing slice as "not loaded"; never turn either into a fact about the album.
- Show at most the three reasons the body carries; show `capped[]` and `overlap_dropped` only as plain counts.
- Fixtures: `paths_album_crew.json`, `paths_album_guests.json`, `paths_album_works.json`, `paths_album_room.json`, `paths_album_moment.json` (`ok`) and the matching `_empty` files, plus `paths_error_album_kind_artist_type.json`, `paths_error_artist_kind_album_type.json` (`400`), `paths_error_album_unknown_entity.json` (`404`). Recorded through the route on a copy of the owner's store (first `ok` and first `empty` album among the owned releases, ordered by id). Sonic: `sonic_album_neighbours.json` (`ok`, 14 stops), `sonic_album_neighbours_empty.json` (`empty`, one unanalysed seed reported in `skipped`) and `sonic_album_neighbours_error_not_found.json` (`404`), recorded through the route against the owner's Navidrome (read-only, 2026-11-09). No `502` was recorded. Not recorded yet: the `album_gaps` body.

## Album artwork: `GET /api/artwork/index` and `GET /api/artwork/image/{image_id}` (artwork slice 1)

Decided in [artwork.md](artwork.md) (owner, 2026-11-10). **Status: both routes are served (PRs #945, #946).** Everything in "Rules for every endpoint" applies. Session auth is required on both; clients never contact MusicBrainz or the Cover Art Archive (CAA). Nothing here reads taste or play data: images are chosen by approval, type, size and date only.

### `GET /api/artwork/index?rgid=&release=`
- `rgid` (required): MusicBrainz release group MBID. `release` (optional): the owned release MBID; it makes the owned edition win the slots and protects that album's best front in the cache. A malformed id is `400`; a missing `rgid` is `422`. Always `Cache-Control: no-store`.
- `status`: `ok`, `empty` (every release answered "no images"), `unavailable` (the lookup or every read failed; the body is only `status` and `rgid`, and says nothing about the album) or `not_loaded` (a background build has started; the body is `status`, `rgid` and `retry_after` in seconds, so ask again). `empty` and `unavailable` are never the same: a failed read is never counted as "no images".
- Body (`ok` and `empty`): `rgid`; `truncated` and `truncated_reason` (`null`, `release_cap`, `served_cap` or `partial`); `releases` (`total`, `fetched`, `empty`, `failed` counts); `best_front` (an `image_id`, or `null` when nothing is typed Front: never an artist photo, never an untyped image); `slots` (type to `{image_id, release, edition, from_owned}` for Front, Back, Spine, Obi, Medium, Tray, Sticker, Poster; the owned edition's image wins, `from_owned` says so); `booklet` (`{release, edition, image_ids[]}` from the single release with the most pages, in CAA order, or `null`); `images[]`.
- Each image: `image_id`, `release` (preferred release), `releases` (every fetched release it is on; the same image appears once), `edition` ("1999 JP CD", parts MusicBrainz lacked are left out), `types[]`, `comment`, `approved`, `width`, `height` (integers or `null`), `format` (`jpg`, `png`, `gif`, `webp` or `pdf`: the original's file type; a PDF booklet is `pdf`). Images are in quality order: approved, larger side, earlier release date, lower id. `best_front` is by the same rule among Front images and can differ from the owned edition's Front in `slots`.
- `truncated_reason`: `release_cap` (more than 60 releases; the owned release first, then newest), `served_cap` (more than 250 images; slot winners, booklet pages, then quality order are kept), `partial` (a release read failed, or the build stopped on its time bound before reading every release; the rest is served).
- `comment` is third-party text: show as plain text, never as markup. Unknown keys are ignored.
- Clients: with no images, show nothing extra (no placeholder, no empty tab). `not_loaded` and `unavailable` are never a statement about the album.

### `GET /api/artwork/image/{image_id}?size=thumb|display|full`
- `image_id` is a positive integer from an index the server has built (else `404`); `size` default `display`, anything else `400`. `thumb` is the CAA 250 px file and `display` the 500 px file (no resizing yet); `full` is fetched on first use and stored.
- `200`: the image bytes with their real `Content-Type` (JPEG, PNG, GIF or WebP; a PDF original only as `size=full`, `application/pdf`, with `Content-Security-Policy: sandbox`). `X-Content-Type-Options: nosniff`, `Cache-Control: private, max-age=86400`. `503` when the provider is temporarily unavailable (retry later); `404` when the id is unknown or the file does not exist.
- Use `format` on the index entry to tell a PDF before asking for `full`. `thumb` and `display` of a PDF are the first-page preview image.

### Cover choice (edition picker, artwork slice 4)
- `PUT /api/artwork/choice/{album_id}` with `{"rgid": "<release group MBID>", "image_id": <int>}`: stores the owner's pick for an owned album (the Navidrome album id). The image must be a Front image (not a PDF) in the served index of that release group, else `404`; `409` while the index is not built yet (the build is queued, ask again); `400` for a malformed id. `200` body `{"album_id", "image_id"}`. The picked image is protected from cache eviction.
- `DELETE /api/artwork/choice/{album_id}`: removes the pick (`200`, `image_id: null`; removing a missing pick is not an error).
- `GET /api/artwork/choices`: `{"choices": {"<album_id>": <image_id>}}`, every pick, for clients that load library covers themselves (macOS). `no-store`.
- The album page's `album` section carries `artwork_choice` (an `image_id` or `null`; `null` for an album not in the library).
- `GET /api/owned/artwork/{cover_id}?size=` (the library cover route): when `cover_id` is an album with a pick, the picked image is served (`thumb` up to 250 px, else `display`; `Cache-Control: private, max-age=300`) and Navidrome is not asked. Without a pick it is the Navidrome cover, **replaced by the release group's best front only when Navidrome has no cover, or the cover's longer side (read from the JPEG or PNG header) is under 300 px and the best front's recorded size is larger**. A group whose index is not built is queued, and this request keeps its old answer (`404` for no cover). Never an artist photo; taste and play data are never read.
- Clients: a new pick is a new address (`?c=<image_id>` is ignored by the server), so image loaders do not keep the old cover.

Fixtures (`android/contract-fixtures/librarian/`): `artwork_index.json` (`ok`), `artwork_index_empty.json`, `artwork_index_unavailable.json`, `artwork_index_not_loaded.json`, `artwork_index_truncated.json` (`partial`: one release failed), `artwork_index_truncated_release_cap.json`, `artwork_index_truncated_served_cap.json` and `artwork_index_error_bad_rgid.json` (`400`). Written by `scripts/write_artwork_fixtures.py` through the real route with canned provider answers: invented ids and comments, no provider traffic, shapes exact and values not real. The two cap fixtures use lowered caps (2 releases, 3 images) to stay small. `tests/test_artwork_fixtures.py` fails if a file drifts from the route.

## Not in this contract

Entity pages and path `reasons[]` (later phases); any scheduling or trigger route for the health job; macOS Swift fixtures (the macOS Health view is the Phase 1 client gate and will consume these JSON files directly).
