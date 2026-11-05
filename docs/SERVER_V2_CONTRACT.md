# Server V2 contract (Phase 1)

Status: draft for the owner's Phase 1 contract review. Route names are **provisional** (`ServerV2.md` section 8) and **no route is served yet**: `navidrome_server.py` takes no additions (D-016). This document fixes the response bodies the builders in `intelligence/api/` already produce; examples are the files in `intelligence/contract-fixtures/`, which `tests/test_intelligence_contract_fixtures.py` rebuilds and compares, so a body change fails CI until the fixtures are regenerated (`python scripts/write_intelligence_fixtures.py`).

## Rules for every endpoint

- Read-only `GET`. Nothing here edits music files or calls a provider.
- No file paths, credentials, tokens or provider URLs in any body.
- Clients hide a section when its feature is unavailable. Unknown keys are ignored; known keys are never removed within a `contract_version`.
- Every body carries `generation` (matching-logic version) and, where it has one, the resource `data_version`.
- Responses for `library-health` and `unresolved` send a weak `ETag` (`W/"<resource>-<generation>-<data_version>"`). A request whose `If-None-Match` matches (weak comparison, comma list, or `*`) gets `304` with no body. `capabilities` and `changes` are never cached (`Cache-Control: no-store`).

## GET /api/capabilities

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

## Not in this contract

Entity pages, insight cards and `reasons[]` (later phases); any scheduling or trigger route for the health job; macOS Swift fixtures (the macOS Health view is the Phase 1 client gate and will consume these JSON files directly).
