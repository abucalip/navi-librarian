# Owned-first Artist Radio (LB-17)

`GET /api/artist-radio` uses the existing API authentication. It returns `Cache-Control: no-store` and performs no playback, acquisition, playlist or library mutations.

- `artist_mbid`: required artist UUID. Must identify exactly one artist in the current owned index; unknown or ambiguous seeds return `empty`.
- `familiarity`: `familiar` (default), `explore`, or `deep_cuts`.
- `count`: integer 25–50, default 40. Invalid parameters return `422`; unauthenticated requests return `401`.

Response fields:

| Field | Meaning |
| --- | --- |
| `state` | `ready`, `empty`, `unconfigured`, or `index_unavailable` |
| `artist_mbid`, `familiarity`, `requested_count` | Normalized request values |
| `index_state` | Owned-index state; null when ListenBrainz is unconfigured |
| `similar_state` | `ready` if a fresh precomputed result exists, otherwise `unavailable` |
| `popularity_state` | `ready` when all eligible artist popularity reads succeeded, `partial` when any failed or lacked an MBID, otherwise `unavailable` |
| `tracks` | Ordered playable queue, empty unless `ready`; never padded or repeated to meet the requested count |

Each track contains `song_id`, `title`, `artist`, `artist_id`, `album`, `album_id`, `duration` (seconds), `recording_mbid`, and `owned: true`. Album, duration and recording metadata may be null. Clients use `song_id` for native playback and must preserve existing queues on empty or unsuccessful responses. Web playback and client controls belong to LB-19–21.

## Selection defaults

Candidates come exclusively from `OwnedData.songs` for the seed plus at most five uniquely resolved owned similar artists. Similar artists use the existing seven-day precompute cache in stored relevance order; generation never triggers similar-artist provider lookups. Known conflicting artist IDs and ambiguous name matches are refused.

| Mode | Target seed share | Local play weight | Popularity weight |
| --- | --- | --- | --- |
| Familiar | 60% | +0.65 | +0.35 |
| Explore | 35% | −0.35 | +0.65 |
| Deep cuts | 20% | −0.70 | −0.30 |

Local plays use `log(1 + plays) / log(1 + maximum candidate plays)`, or zero with no history. Popularity uses descending source position, `1 - position / row_count` (position starts at zero); unmatched songs receive zero. The weighted sum ranks each artist's songs; song ID breaks ties. Similar artists receive slots in round-robin order. Missing supply is filled from remaining eligible artists, then tracks are interleaved in proportion to final artist allocations. With sufficient supply this yields 25–50 songs; otherwise it returns every eligible unique recording up to the requested count. Recording MBID copies use the lowest song ID; separate untagged files and distinct versions remain distinct.

Popularity metadata uses the shared LB-03 matcher: exact recording MBID first, then uniquely corroborated full artist/title with release or duration evidence. A popularity row can rank an owned candidate but cannot introduce a song. Stale last-known-good library indexes are usable and explicitly reported.

## Availability and provider budget

Both a valid configured ListenBrainz username and token are required; missing configuration returns `unconfigured` without indexing or provider requests. Missing owned data returns `index_unavailable`, distinct from zero eligible songs. Missing similar data yields seed-only selection. Missing popularity data uses local ranking and reports `partial`.

[ListenBrainz top recordings](https://listenbrainz.readthedocs.io/en/latest/users/api/popularity.html) are cached by artist MBID for 30 days (one hour for definitive empty results), independently of library ownership. Concurrent successful reads share a fetch within the web process. At most six artist reads occur, using the existing shared ListenBrainz limiter, a 12-second request budget and at most four seconds per HTTP call; rate refusal, timeout, HTTP failure and malformed bodies are not cached. No new dependencies, MusicBrainz calls, scheduled jobs or Navidrome writes.
