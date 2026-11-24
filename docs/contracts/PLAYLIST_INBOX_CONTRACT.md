# Playlist Inbox API

Both GET routes require the app's owner session and send `Cache-Control: no-store` on success. The endpoints read SQLite snapshots and use the shared owned-song index. Their contract examples are in [the shared Inbox response fixture](../../tests/fixtures/listenbrainz_inbox_responses.json).

## GET /api/playlists/inbox

The response contains `state`, `listenbrainz_configured`, `index_state`, and `items`.

- `listenbrainz_configured` means a valid username and a configured token are present. Previously saved editions and local mixes remain browsable when configuration is absent.
- `state` is `ready` when any current edition is stored, `empty` when configured with no stored edition, or `unconfigured` when neither condition is met. An empty edition is still an edition and appears in `items`. An empty list says only that no edition is stored.
- `items` contains the current edition for each source, newest `fetched_at` first with descending `edition_id` breaking ties. Summaries carry no track rows.
- `index_state` is `fresh`, `stale`, `building`, or `unavailable`. It is `null` for an empty list. A stale index can serve its last good matches. When no owned index is available, `owned_count` and per-track matching are unknown.

Each summary includes `edition_id`, `source_kind`, `source_key`, `identifier`, `title`, `creator`, `source_patch`, `generated_at`, `last_modified_at`, `fetched_at`, `stale`, `total_count`, and `owned_count`. Source metadata may be `null`. Dates are ISO 8601 in UTC when present. Counts include repeated occurrences. `owned_count` is `null` when ownership is unknown.

`stale` means at least seven days have elapsed since the edition's saved `fetched_at`. That timestamp belongs to the immutable edition. A refresh that sees identical content keeps the timestamp. The age flag reports the age of this snapshot. Provider refresh outcomes are tracked separately from edition age and are outside this contract.

## GET /api/playlists/inbox/{edition_id}

The response contains the edition summary, `listenbrainz_configured`, `index_state`, and `tracks`. A stored historical edition can still be read by ID. Each track carries its original zero-based `position`, display metadata and identifiers. Repeated tracks retain each occurrence and its position.

- `match_state` is `owned`, `missing`, `ambiguous`, or `null` when the index has no usable data. `song_id` is set only for `owned`.
- `acquisition_status` is the saved status of an existing single-track job, or `null`. A job can be attached only for a known, unambiguous match state and when the recording has artist, album, and full title. Both the existing normalized job key and the saved artist, album, and title must agree. Label comparison ignores case, whitespace, and Unicode composition while preserving punctuation and title qualifiers. Repeated occurrences can refer to the same job. Ownership and job status are independent.
- Job settings, candidates, and message details are omitted. Download actions and Navidrome sync are covered by later slices.

Both routes return `401` without an owner session. A missing edition returns `404`. An invalid edition ID returns `422`. An unavailable snapshot store or unreadable acquisition store returns `503`.
