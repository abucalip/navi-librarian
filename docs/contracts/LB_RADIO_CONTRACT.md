# LB Radio Discovery Mix (LB-18)

`GET /api/discovery/lb-radio` uses existing API authentication (`401` without a session) and returns `Cache-Control: no-store`. It calls ListenBrainz's `/1/explore/lb-radio`; it performs no acquisition, playback or Navidrome playlist writes.

- Exactly one seed: `artist_mbid` (UUID) or `tag` (1–80 characters). Tags normalize Unicode, case and spacing; letters, numbers, spaces and `-_&'/+.` are accepted. Prompt operators and control characters are rejected. Artist IDs need not exist in the owned library.
- `mode`: `easy` (default), `medium`, or `hard`. Invalid seeds/modes return `422` before provider work. Weighted/multiple seeds remain deferred.
- Both configured ListenBrainz username and token are required (saved token, then environment fallback). Missing configuration returns `200`, `state: unconfigured`, without index or provider reads.

| Field | Meaning |
| --- | --- |
| `state` | `ready`, `empty`, `unconfigured`; failures listed below |
| `seed` | `{kind: artist\|tag, value: normalized seed}` |
| `mode` | Requested mode |
| `index_state` | Owned-index state, null before matching |
| `total_count` | Full source track count, including repeats |
| `owned_count` | Owned occurrences; null when ownership is unknown |
| `tracks` | Full source order, including owned, missing and ambiguous occurrences |

Each track uses the shared JSPF fields: zero-based `position`, `recording_mbid`, `title`, `artist`, `album`, `duration_ms`, `conflicting_recording_mbids`, `artist_mbids`, `release_mbid`, `caa_id`, `caa_release_mbid`; plus `match_state` (`owned`, `missing`, `ambiguous`, or null) and `song_id` (owned only). Optional source metadata may be null.

Matching uses LB-03 against the current owned index on every read, including cache hits. Missing index data leaves every match unknown while retaining the discovery list; a stale last-known-good index remains usable. No unowned occurrence is removed or made playable. Clients must preserve native queues on errors/empty results and play/save only confirmed `song_id` values. Download controls and album/identity resolution belong to LB-19–21 using existing acquisition services; ambiguous/unknown rows must not be submitted as confirmed missing recordings.

## Caching and failures

- Complete source JSPF responses, including empty results, cache for five minutes. Cache identity includes normalized seed, mode, username and a token-derived SHA-256 digest; keys contain no plaintext credentials. Ownership is never cached with the source mix.
- Concurrent identical requests share a success or failure within the web process. At most 16 distinct upstream requests are in flight. Requests use the existing shared ListenBrainz two-second limiter, a 12-second request budget and HTTP timeouts capped at ten seconds; no retries or MusicBrainz calls.
- Upstream responses over 1 MiB, malformed JSPF or over 200 tracks fail completely rather than silently truncating. Upstream bodies, feedback and internal errors are not returned.
- Failure bodies retain the response shape with empty `tracks` and unknown ownership: `rate_limited` (`429`), `timeout` (`504`), `upstream_error` (`502`), `busy` or `unavailable` (`503`). `429` and capacity refusals include `Retry-After: 2`. Failed fetches are not cached.

Focused tests: `tests/test_api_lb_radio.py`, `tests/test_listenbrainz_discovery_mix.py` (sanitized fixtures and simulated transports; no live provider calls).
