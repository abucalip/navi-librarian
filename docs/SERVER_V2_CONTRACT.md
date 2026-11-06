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
| `features` | Map of feature name to `{available, resource, data_version}`; when `available` is `false` it also has `reason` (`not_populated`). Phase 1 features: `library_health`, `unresolved_queue`. |
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

Knowledge pages (Phase 4): fixtures `knowledge_album.json`, `knowledge_person.json`, `knowledge_person_slice_pending.json`, `knowledge_label.json`, `knowledge_work.json`, `knowledge_recording_works.json`, built from a small store of their own with fixed ids and clock. Routes `GET /api/knowledge/album|person|label|work|recording-works` (`app/api/knowledge.py`); bodies carry `mbid` only and every `owned` flag is a boolean. The pending fixture shows a store with no MusicBrainz slice loaded (`sources.musicbrainz_dump.coverage` is `pending`).

- Body: `lenses` (map of lens kind to `{enabled, cards[]}`), `data_version`, `generation`. Lens kinds: `forgotten_gem`, `blind_spot`, `series_completion`, `hidden_canon`, `anniversary`.
- A lens contributes cards only when it is enabled. A lens is enabled by default only when its scorecard verdict is `pass`; today none is (all four provider lenses are `insufficient_evidence`, Forgotten Gems has too little play history). A client shows "off" for `enabled: false` and an empty state for `enabled: true` with no cards; it never invents cards.
- Card (all kinds): `kind`, `title`, `body`, `subject{key, type, title, ...}`, `reasons[]` (each `{kind, evidence{}}`), `actions[]` (`{kind: "dismiss"}`), `dismissible`, `score`, plus kind-specific counters (`owned`, `total`, `missing_runs`, and so on). Wording states a fact (a count, a date, a listen total), never "you should own".
- `subject.key` is the dismissal and accept key. Actions: `POST /api/insights/{kind}/dismiss|restore|accept|unaccept` with JSON `{"key": "<subject.key>"}`, answering `{"changed": bool}` (`false` when nothing changed, for example a repeat dismiss or accepting a dismissed key); unknown kind `404`, missing key `422`. Restore lifts the suppression; the card returns at the next refresh.
- `capabilities` gains the `insights` feature (`available` once any card row has been saved).
- Filling the store: `app/services/insights_refresh.py` runs `intelligence.insights.refresh_forgotten_gems` at startup and every 6 hours, only when `forgotten_gem` is listed in `NAVI_INSIGHT_LENSES`. It reads the Navidrome album list (play count, last played, star, rating) and nothing else; an empty album list is a failed run that keeps the saved cards, and a library with sparse history saves no cards. With `blind_spot`, `hidden_canon` or `anniversary` listed, the same loop also runs `intelligence.insights.refresh_provider_lenses` (owner-approved provider traffic, 2026-11-05): per 6-hour tick it records up to 40 Navidrome artists (those with an MBID), then spends at most 120 MusicBrainz and ListenBrainz requests (paced 1.1 s and 0.5 s) on release browses (linking owned releases to release groups), studio discographies, ListenBrainz top release groups and artist life-spans, cached in the store (30-day freshness, never-fetched first). The three lenses are recomputed and saved only once every owned artist has been browsed and has all three documents, so a half-linked library never shows false gaps; until then saved cards stay as they were. A provider failure fails the run and keeps the cache. Series are refreshed too (PR #801): series ids are discovered from the owned release groups' own MusicBrainz series relations, within the same tick budget, only when `series_completion` is listed.

## GET /api/knowledge/{album,person,label,work,recording-works} (Phase 4)

Served by `app/api/knowledge.py` (D-016: nothing added to `navidrome_server.py`). Every body is built by `KnowledgeReader` (`album_dossier`, `person_page`, `label_page`, `work_page`, `works_of_recording`) from `intelligence.sqlite3`; no provider traffic, no writes, no ownership flags. The page shapes are those the reader returns, with provenance on every credit and a `coverage` field (`pending`, `loaded`, `no_relationships_in_slice`) instead of a silent empty list.

- `album`: `mbid` or `navidrome_id`, `type` = `release` (default) or `release_group`, `limit` 1 to 500 (default 100).
- `person`: `mbid` or `navidrome_id`, `type` = `artist` (default), `person` or `group`, `limit` 1 to 500 (default 200).
- `label` and `work`: `mbid` (required, else `422`), `limit` 1 to 500 (default 200).
- `recording-works`: `mbid` or `navidrome_id`, `limit` 1 to 500 (default 50).
- `connections` (`GET /api/knowledge/connections`, bounded graph walk, Phase 4 item 6): `mbid` or `navidrome_id` plus `type` (all required, else `400`), optional `credits_only`, repeatable `relation`, `direction` = `out`, `in` or `both` (default), `depth` 1 to 3 (default 1, else `422`), `limit` 1 to 500 (page size, default 50), `cursor` (opaque, from `next_cursor`; a bad one is `400`). Body: `start`, `hops` (each with `entity`, `depth`, `via_mbid`, `credit` and `evidence` with source, evidence class and match quality), `next_cursor`, `truncated` (`rows`, `time` or null) and `sources.musicbrainz_dump.coverage`. Each entity appears once at its shortest depth; inferred or unconfirmed edges are never `credit`. The walk stops at 200 rows or 2 seconds. Not fixtured yet.
- Errors: neither identifier `400`; bad `type` `400`; `limit` out of range `422`; entity not in the store `404`; store unreadable `502`.
- Shape (owner decisions, 2026-11-06): the page shapes are approved. Bodies carry `mbid` and never a store `id`, `created_generation`, `navidrome_id`, `discogs_id` or `wikidata_id` (`intelligence/knowledge/public.py`). Every `owned` flag is a boolean, and a release group is owned when any of its editions is. Clients show at most ten credits per list and a "more" control for the rest (the body still carries up to `limit`).
- Not yet fixtured and no client uses these routes; fixtures come next.

## Not in this contract

Entity pages and path `reasons[]` (later phases); any scheduling or trigger route for the health job; macOS Swift fixtures (the macOS Health view is the Phase 1 client gate and will consume these JSON files directly).
