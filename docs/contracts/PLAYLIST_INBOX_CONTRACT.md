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
- Job settings, candidates, and message details are omitted. For a row saved without an album, the download response supplies the acquisition polling key.

Both routes return `401` without an owner session. A missing edition returns `404`. An invalid edition ID returns `422`. An unavailable snapshot store or unreadable acquisition store returns `503`.

## POST /api/playlists/inbox/{edition_id}/tracks/{position}/download

The owner session is required. The request needs no body. The server selects the immutable stored occurrence by edition ID and zero-based position, including historical editions. It checks a complete current Navidrome inventory and verifies that the connection and idle scan marker stayed stable before starting acquisition.

- A track already owned returns `200` with `edition_id`, `position`, `ok: true`, `status: "owned"`, and `song_id`.
- Otherwise the action returns `200` with `edition_id`, `position`, the single-track acquisition outcome (`ok`, `status`, `message`), `artist`, the display `album`, and the synthetic `job_album` used for acquisition polling. `already_in_progress`, `importing`, and `imported` refer to the existing acquisition. `identity_conflict` means the normalized job key belongs to a different acquisition. Successful HTTP responses use `Cache-Control: no-store`.
- An invalid ID or negative position returns `422`. An unknown edition or position returns `404`.
- `409` means the track is ambiguous (`ambiguous_track`), lacks artist or title (`unresolved_track`), or has no confirmed album (`unresolved_album`). For an albumless track, ListenBrainz can confirm the album of a known recording ID. Otherwise, paced MusicBrainz search must identify one recording and one release title or confirm the stored or mapped release ID.
- `503` means ownership cannot be checked against a stable inventory (`ownership_unavailable`) or a required store cannot be read. A failed metadata fallback or acquisition request returns `502` with `metadata_unavailable` or `acquisition_unavailable`. The named error codes appear in `detail.code` with readable text in `detail.message`.

Concurrent requests for the same stored track metadata share one action in the web process. The acquisition service also guards the normalized artist and job album key, including when the request arrives through a different route.
