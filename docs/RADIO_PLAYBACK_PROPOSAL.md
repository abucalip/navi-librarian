# Internet radio playback proposal

**Status:** owner decisions recorded 2026-11-10 (see "Decisions recorded"). Approved for build in two stages. Stage 1 slices 0, 1 and 2 are done (slice 1 merged as PR #965, slice 2 as PR #966, both 2026-11-10); struck-through items below are built. Slice 3 is next.
**Date:** 2026-11-10
**Context:** RADIO-01 ("Grab the radio", PR #637) already relays Navidrome radio stations through `/radio/stream/<token>`, reads ICY titles and logs songs heard for 30 seconds or more in `radio.sqlite3` (`integrations/radio/`, `app/api/radio.py`). This proposal adds playback in the clients on top of it. Related: [Android player contract](ANDROID_PLAYER_CONTRACT.md), [macOS client contract](MACOS_CLIENT_CONTRACT.md).

## Goal

Play the owner's Navidrome internet radio stations in the Android and macOS clients, with station logos instead of plain icons, the live song shown, and a Download button when the live song has usable metadata.

## Scope change

Three documents list radio as out of scope: `PRODUCT.md` (line 27), `ANDROID_PLAYER_CONTRACT.md` (line 18) and `MACOS_CLIENT_CONTRACT.md` (line 9). The owner approved lifting this on 2026-11-10 through this proposal. Slice 0 turns it into a contract (`RADIO_PLAYBACK_CONTRACT.md`) and edits those three lines to point at it. macOS stays out of scope until stage 2.

## Principle: the server stays the single source of truth for "what is playing"

- Clients do not download anything themselves. Acquisition (MusicBrainz, slskd, import) stays server-side; the existing `POST /api/radio/plays/{id}/get` is the Download action.
- The artist/title split and the MusicBrainz lookup stay in Python (`integrations/radio/icy.py`); they are not duplicated in Kotlin or Swift.
- A client may read ICY titles from its own stream for an instant display, but the title that enables Download comes from the server's `/now` endpoint.
- The play log stays. A Download button needs a `play_id`, and the 30-second rule keeps skipped songs out of the log. The Heard list (RADIO-01) keeps working unchanged.

## Server work (stage 1)

### ~~Stations list~~ — done, PR #965 (merged 2026-11-10)
~~`GET /api/radio/stations` gains per station: `logo_url` (a server path, never a third-party URL), `homepage_url`, `favourite`, `sort_key` data (last played), and a `playable_url` (the relay URL when proxied, else the original). Stations that are not proxied are still returned and playable, but have no live title and no Download.~~ — done, PR #965 (merged 2026-11-10)

### ~~Live song: `GET /api/radio/stations/{id}/now`~~ — done, PR #966 (merged 2026-11-10); deviations are in the contract, section 3.2
Returns `{state, raw_title, artist, title, play_id, in_library, cover_url}`.
- `state`: `ok`, `no_metadata` (station sends no ICY titles), `unparsed` (title without "Artist - Title"), `not_proxied`, `unavailable`.
- `play_id` is null until the song has been heard for the 30-second threshold, then it is the `radio_plays` id. The client enables Download only when `play_id` is set and `state` is `ok`.
- `in_library` is true when the artist and title match the Navidrome library (idea 4).
- `cover_url` is a server artwork path for the live song, from the existing artwork pipeline (idea 6); null when none is found.
- Requires the relay to keep the current title per station in memory (a small per-station "now" holder fed by `ListenTracker`/`relay`), so `/now` is cheap and makes no provider call per request.

### ~~Logos~~ — done, PR #965 (merged 2026-11-10)
~~Resolved once per station, cached on disk in the data directory, served at `GET /api/radio/stations/{id}/logo?size=` in one or two resized sizes. Order:~~
1. ~~**Owner override** (idea: upload or pick in settings; `PUT /api/radio/stations/{id}/logo`, `DELETE` to clear).~~
2. ~~**Radio Browser API** (radio-browser.info, approved by the owner 2026-11-10): one search by stream URL, falling back to name; use the returned `favicon`. Use the batch form where the API offers one (provider rule).~~
3. ~~**Homepage icon:** `apple-touch-icon`, then `og:image`, then `/favicon.ico`, parsed from `homepage_url`.~~
4. ~~**Generated tile:** station initials on a colour hashed from the name, so a station never shows a plain icon.~~

~~Fetch rules: http(s) only, no private or loopback addresses (SSRF guard, also after redirects), content type must be an image, size cap, timeout, no credentials sent, negative results cached with an expiry so a dead logo is not retried on every list call. Failures fall through to the next source, never to an error.~~

### ~~Favourites, order and "now" strip (idea 1 and 2)~~ — favourites, tags (PR #965) and the `/now` strip (`/api/radio/now`, PR #966) done
- ~~`PUT /api/radio/stations/{id}/favourite`; the list sorts favourites first, then by last played.~~ — done, PR #965 (merged 2026-11-10)
- ~~Optional per-station tags (free text, owner-set) for grouping.~~ — done, PR #965 (merged 2026-11-10)
- ~~`GET /api/radio/now` returns the live title for every proxied station that currently has a listener, so a client can show what is on without tuning in. Stations nobody is connected to report `idle`, because the relay does not hold a connection with no listener (it must not open upstream connections just to show titles).~~ — done, PR #966

### Heard list in clients (idea 3)
No new endpoint beyond the existing `/api/radio/plays`, with `grabbed` and `in_library` exposed so a client can show Download, Downloaded and Owned states.

### Scrobbling and love (idea 5)
`POST /api/radio/plays/{id}/scrobble`, called by the server itself once a song crosses the 30-second threshold when the owner has switched radio scrobbling on (Settings, default off). It reuses the existing Last.fm scrobbling code; a song is scrobbled once per play entry. A "love" action on a play is a separate request. Needs a check that scrobbling does not double-count with Navidrome's own scrobbling, which does not see radio plays.

### Contract fixtures
Fixtures for each `/now` state, the stations list with and without logos, and the empty and unavailable cases, in the existing contract-fixtures layout so Android and macOS decoders are tested against the same files.

## Android work (stage 1)

- A Radio section: station list with logos, favourites first, the live title strip (from `/api/radio/now`).
- Playback through the existing Media3 service as a live stream: no seek bar, no duration, no gapless or crossfade, notification and lock-screen showing the station logo and the live title (cover when `cover_url` exists).
- Now Playing for radio: live title, cover or logo, favourite toggle, Download button (enabled by the rule above, with Downloaded and Owned states), Get result messages from the existing endpoint.
- Heard list screen with the same states.
- Reconnect policy (idea 7): automatic retry with backoff when the stream drops or stalls, a clear "station unreachable" state after a bounded number of attempts, and no retry loop while the app is in the background without playback.
- Sleep timer (idea 8) for radio, reusing the existing Android timer if there is one.
- Settings: radio scrobbling switch, logo override picker.
- Android also needs the app address set (already stored in `radio_settings`), because the relay URL must be reachable from the phone (Tailscale address).

## Stage 1 slices

0. ~~Contract and doc edits (docs only, directly on `main`).~~ — done 2026-11-10 (docs on `main`)
1. ~~Server: stations list fields, favourites, logo resolver and cache, with tests and fixtures.~~ — done, PR #965 (merged 2026-11-10)
2. ~~Server: live "now" holder, `/now`, `/api/radio/now`, `in_library`, `cover_url`.~~ — done, PR #966 (merged 2026-11-10)
3. Server: scrobble on threshold (off by default) and love.
4. Android: decoders, Radio section, logos, favourites.
5. Android: playback service, live Now Playing, Download and Heard states.
6. Android: reconnect, sleep timer, settings.

Each slice is its own PR with focused tests only (owner rule); the owner runs the full suite.

## Deployment gate

After slice 6, stop. Publication and deployment are separate decisions and need the owner's explicit authorization (`DEVELOPMENT_WORKFLOW.md`). Before asking, record: the image tag, the new `radio.sqlite3` columns or tables (migration is additive and creates what is missing, so a rollback to the previous image still opens the file), the new data-directory logo cache, and the rollback reference. Owner checks on a live deployment: a real station plays on a phone over Tailscale, the logo appears, the live title changes with the song, Download enables after about 30 seconds and the song reaches the library, and a station with no ICY metadata plays without a button.

## Stage 2 (after deployment)

macOS, written against the deployed and verified API:
- One neutral Radio layout first (stations with logos, now-playing strip, Download, Heard list), then one view per theme as each theme is touched, so theme work does not block the feature.
- Integration with the existing player model, media keys, the Now Playing center and the menu bar item; live-stream behaviour as on Android.
- The Mailroom "Heard on Radio" tape (already in the macOS contract) gets the Owned and Downloaded states.
- Same reconnect and sleep timer rules.
- Lift the macOS line in `MACOS_CLIENT_CONTRACT.md` only when stage 2 starts.

Possible later, not committed: browsing Radio Browser by genre or country and adding a station to Navidrome (idea 9). It widens scope to station management and needs its own approval.

## Not included

- **Recording** a stream (idea 10). The logged-song plus Get path covers the need; the owner excluded recording on 2026-11-10.
- Changes to the web UI, which stays without playback (`PRODUCT.md`).

## Risks

- **No metadata.** Stations that serve playlists, send no ICY titles or use the non-HTTP `ICY 200 OK` status line give no title and no Download. The client says so instead of showing a dead button.
- **Unparsed titles.** A title without "Artist - Title" is shown but cannot be downloaded (RADIO-01 rule).
- **Wrong MusicBrainz match** can download the wrong album's version of a song. The existing rule (exact artist and title, plain official studio album first) is kept; no loosening.
- **Relay in the audio path.** Every proxied listener now goes through the app. A relay outage stops the station; the stations list must make it easy to turn the switch off, and the client should show "station unreachable" rather than silence.
- **Logo sources.** Radio Browser is a community service with no guarantee; the fallback chain means its failure never blocks a station. A large or hostile image is the reason for the size cap and the SSRF guard.
- **Scrobble duplicates** if a station's title repeats within 10 minutes (the log already merges those) or if another source also scrobbles.

## Decisions recorded

Owner, 2026-11-10:
1. Lifting "radio is out of scope" through a contract: approved.
2. All proposed ideas are in except recording; build in two stages: server and Android first, then deployment, then the rest (macOS) later.
3. The live title that enables Download comes from the server's `/now` endpoint; clients read ICY only for an instant display.
4. Radio Browser is approved as an external logo source.

## Open questions for the contract

- Whether `/api/radio/now` should also list idle stations with their last known title (current proposal: no, `idle` only).
- Logo sizes (proposal: 128 and 512 px, PNG or WebP).
- Whether the override upload is owner-only from the web UI too or Android only (proposal: a small Radio settings panel on the web page, since RADIO-01 already has one).
