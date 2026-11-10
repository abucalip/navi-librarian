# Internet radio playback contract (Discair)

Status: **approved by the owner on 2026-11-10. Stage 1 slice 0 (contract), slice 1 (server stations list, favourites, tags, logos; PR #965) and slice 2 (server live "now" holder, `/now`, `/api/radio/now`; PR #966) are merged (2026-11-10). Slice 3 is next. Stage 2 (macOS) starts only after deployment is authorized and verified.**

This contract turns [`RADIO_PLAYBACK_PROPOSAL.md`](RADIO_PLAYBACK_PROPOSAL.md) into the rules the server and clients build against. Where the proposal and this contract disagree, this contract governs. Builds on RADIO-01 ("Grab the radio", PR [#637](https://github.com/abucalip/navi-librarian/pull/637)): the relay at `GET /radio/stream/{token}`, ICY title reading, the 30-second play log in `radio.sqlite3`, and `POST /api/radio/plays/{play_id}/get` as the Download action. Related: [`ANDROID_PLAYER_CONTRACT.md`](ANDROID_PLAYER_CONTRACT.md), [`MACOS_CLIENT_CONTRACT.md`](MACOS_CLIENT_CONTRACT.md).

## 1. Scope

- **In scope:** playback of the owner's Navidrome internet radio stations in the Android client (stage 1) and the macOS client (stage 2), with station logos, the live song, and a Download button when the live song has usable metadata.
- **Lifted scope:** the "radio is out of scope" lines in `PRODUCT.md`, `ANDROID_PLAYER_CONTRACT.md` and `MACOS_CLIENT_CONTRACT.md` point here. The macOS line stays in force until stage 2 starts.
- **Not in scope:** recording a stream (owner excluded it on 2026-11-10); changes to the web UI, which stays without playback; browsing Radio Browser or adding stations to Navidrome (idea 9, needs its own approval).

## 2. Principles

1. **The server is the single source of truth for "what is playing".** Clients do not download anything themselves. Acquisition (MusicBrainz, slskd, import) stays server-side.
2. The artist/title split and the MusicBrainz lookup stay in Python (`integrations/radio/icy.py`). They are not duplicated in Kotlin or Swift.
3. A client may read ICY titles from its own stream for an instant display only. The title that enables Download comes from the server's `/now` endpoint.
4. The play log stays. A Download button needs a `play_id`, and the 30-second rule keeps skipped songs out of the log. The Heard list (RADIO-01) keeps working unchanged.
5. Provider rules apply: no provider call per client request, batch lookups where the provider offers one, and the existing MusicBrainz match rule (exact artist and title, plain official studio album first) is not loosened.
6. Clients never log or display a stream URL, token or salt, and never display the Librarian or Navidrome password.

## 3. Server API

All endpoints follow the existing authentication and error conventions of `app/api/radio.py`.

### 3.1 Stations list: `GET /api/radio/stations`

Each station gains:

| Field | Meaning |
|---|---|
| `logo_url` | Server path under `/api/radio/stations/{id}/logo`, never a third-party URL. Always present; the generated tile is served when nothing else is found. |
| `homepage_url` | Station homepage from Navidrome, or null. |
| `favourite` | Boolean, owner-set. |
| `last_played_at` | Last time a play of this station was logged, or null. Used for sort order. |
| `tags` | Free-text list, owner-set, for grouping. May be empty. |
| `playable_url` | The relay URL `/radio/stream/{token}` when the station is proxied, else the original stream URL. |
| `proxied` | Boolean. Stations that are not proxied are still listed and playable, but have no live title and no Download. |

Order: favourites first, then by `last_played_at` descending, then by name.

### 3.2 Live song: `GET /api/radio/stations/{id}/now`

Returns `{state, raw_title, artist, title, play_id, in_library, cover_url}`.

- `state` is one of:
  - `ok`: an artist and title were parsed;
  - `no_metadata`: the station sends no ICY titles;
  - `unparsed`: a title was read but has no "Artist - Title" form;
  - `not_proxied`: the station is not relayed, so no title is known;
  - `unavailable`: the relay is down or the station cannot be reached.
- `play_id` is null until the song has been heard for the 30-second threshold, then it is the `radio_plays` id.
- `in_library` is true when the artist and title match the Navidrome library.
- `cover_url` is a server artwork path for the live song from the existing artwork pipeline, or null.
- **Download is enabled only when `state` is `ok` and `play_id` is set.** Clients apply this rule.
- The server keeps the current title per station in memory, fed by the relay (`ListenTracker`). `/now` makes no provider call and no upstream connection.

Slice 2 note (PR #966, merged 2026-11-10): `/now` also returns `idle` when nobody is listening, and `unavailable` when the relay could not reach the station in the last 20 seconds (the five states above did not cover these two cases). A station that is not relayed, or is unknown, returns `not_proxied` without a Navidrome call. `cover_url` is set only for songs found in the library (the Navidrome cover of that song, served through the owned-artwork route); other songs get `null`. The library answer is looked up once per song and kept until the song changes.

### 3.3 Live titles for all stations: `GET /api/radio/now`

Returns the live title for each proxied station that has a current listener. Stations with no listener report `idle`. The relay does not open an upstream connection just to show a title. Idle stations do not show their last known title (open question 1).

### 3.4 Logos

Resolved once per station, cached on disk in the data directory, served at `GET /api/radio/stations/{id}/logo?size=` in one of two sizes: 128 and 512 px, PNG or WebP (proposal default, open question 2).

Slice 1 note: `size` accepts 128 or 512 and is validated, but the logo itself is served as the source image (PNG, JPEG, GIF, WebP or ICO, sniffed from its bytes) because no image library is installed. Only the generated tile is sized (a PNG drawn in pure Python). Resizing waits for an approved image dependency.

Resolution order:

1. **Owner override:** `PUT /api/radio/stations/{id}/logo` to upload, `DELETE` to clear.
2. **Radio Browser API** (radio-browser.info, approved 2026-11-10): one search by stream URL, falling back to name, using the returned `favicon`. Use the batch form where the API offers one.
3. **Homepage icon** parsed from `homepage_url`: `apple-touch-icon`, then `og:image`, then `/favicon.ico`.
4. **Generated tile:** station initials on a colour hashed from the station name. A station never shows a plain icon.

Fetch rules for every external fetch:

- http(s) only; no private, loopback or link-local addresses, checked again after every redirect (SSRF guard);
- content type must be an image; a size cap; a timeout;
- no credentials sent;
- negative results cached with an expiry, so a dead logo is not retried on every list call;
- failures fall through to the next source and never become an error for the client.

### 3.5 Favourites and tags

- `PUT /api/radio/stations/{id}/favourite` sets or clears the flag.
- Tags are owner-set free text, for grouping. `PUT /api/radio/stations/{id}/tags` with `{"tags": [...]}` replaces the list: at most 10 tags of 24 characters, blank and case-insensitive duplicates dropped.

### 3.6 Heard list

No new endpoint. `GET /api/radio/plays` exposes `grabbed` and `in_library` so a client can show the Download, Downloaded and Owned states.

### 3.7 Scrobbling and love

- `POST /api/radio/plays/{play_id}/scrobble` is called by the server itself once a song crosses the 30-second threshold, only when the owner has switched radio scrobbling on (Settings, default **off**). It reuses the existing Last.fm scrobbling code. A play is scrobbled at most once.
- A "love" action on a play is a separate request.
- Before slice 3 ships, the change must show that radio scrobbles do not double-count with Navidrome's own scrobbling, which does not see radio plays.

Slice 3 implementation note (PR, not merged): the repository had no Last.fm write code, so this slice adds `integrations/radio/scrobble.py` that calls Last.fm `track.scrobble` and `track.love` directly, signed with `LASTFM_SHARED_SECRET` and a `LASTFM_SESSION_KEY` (both from the configuration; no password is asked for). Without a session key, switching scrobbling on is refused. A play is claimed before the call (`scrobbled`), so it is sent at most once and a failed request is never retried. Routes: `GET`/`PUT /api/radio/scrobbling` (default off) and `POST /api/radio/plays/{id}/love`. The double-count check is by design only: radio songs never pass through Navidrome, so the server's Last.fm call is the only scrobble for them; a live check against the owner's account is still needed.

### 3.8 Relay and "now" holder

- The relay must not be a single point of silence: a relay outage stops the station, and the stations list must make it easy to switch the relay off (restoring the original address).
- Logs of songs keep the existing rule: a repeated title within 10 minutes is merged.

### 3.9 Data changes

Additive only. New columns or tables are created when missing, so a rollback to the previous image still opens `radio.sqlite3`. The logo cache is a new folder in the data directory.

## 4. Android client (stage 1)

- **Radio section:** station list with logos (generated tile when none), favourites first, and a live title strip from `GET /api/radio/now`.
- **Playback:** the existing Media3 `MediaSessionService`, as a live stream. No seek bar, no duration, no gapless, no crossfade. Notification and lock screen show the station logo and the live title, and the cover when `cover_url` exists. The stream plays from `playable_url`.
- **Now Playing for radio:** live title, cover or logo, favourite toggle, and a Download button enabled only by the rule in section 3.2. States shown with words, not colour alone: Download, Downloading, Downloaded, Owned. Results of `POST .../get` are shown as text.
- **Heard list:** same states as the Now Playing button, from `GET /api/radio/plays`.
- **Reconnect (idea 7):** automatic retry with backoff when the stream drops or stalls. After a bounded number of attempts, show "Station unreachable" with a retry action. No retry loop while the app is in the background without playback.
- **Sleep timer (idea 8):** reuses the existing Android timer for radio.
- **Settings:** radio scrobbling switch (default off), logo override picker, and the app address already stored in `radio_settings`. The address must be reachable from the phone (for example the Tailscale address).
- Everything in `ANDROID_CLIENT_CONTRACT.md` section 2 applies: 48dp targets, TalkBack labels, no third-party SDKs or analytics, bundled assets, honest states, and the `/mobile-design` pass recorded in `android/DESIGN.md`.

## 5. macOS client (stage 2, not started)

Written against the deployed and verified API. Under stage 2 the macOS client gets:

- one neutral Radio layout first (stations with logos, now-playing strip, Download, Heard list), then one view per theme as each theme is touched;
- integration with the existing player model, media keys, the Now Playing centre and the menu bar item, with live-stream behaviour as on Android;
- the "Heard on Radio" tape in the Mailroom (`MACOS_CLIENT_CONTRACT.md` section 6) gains the Owned and Downloaded states;
- the same reconnect and sleep timer rules as Android.

The macOS line in `MACOS_CLIENT_CONTRACT.md` is lifted only when stage 2 starts.

## 6. States and failure rules

| Situation | What the client shows |
|---|---|
| `no_metadata` | The station plays. No live title and no Download button; the strip says the station sends no song titles. |
| `unparsed` | The raw title is shown. No Download button; the text says the title could not be matched to an artist and song. |
| `not_proxied` | The station plays from its original address if the client can. No live title and no Download. |
| `unavailable` | "Station unreachable", with retry. Never silence without text. |
| `ok`, no `play_id` yet | Live title shown; Download shown as waiting for the song to be heard (about 30 seconds). |
| `ok` with `play_id` | Download enabled. |

Honest-state rule: every state has text, not colour alone.

## 7. Fixtures

Contract fixtures in the existing contract-fixtures layout, so Android and macOS decoders are tested against the same files:

- one fixture per `/now` state (`ok`, `no_metadata`, `unparsed`, `not_proxied`, `unavailable`), with and without `play_id`, with and without `cover_url`;
- the stations list with logos, without logos, and with an empty list;
- the `/api/radio/now` response with an `idle` station and a listening station;
- the unavailable case.

## 8. Tests

Each slice is its own PR with focused tests only (owner rule). The owner runs the full suite. Agents do not run the full unit suite. Each slice names the focused tests it ran and any it could not run.

## 9. Slices

0. ~~**Contract and doc edits** (this document; docs only, committed directly to `main`). Edits to `PRODUCT.md`, `ANDROID_PLAYER_CONTRACT.md` and `MACOS_CLIENT_CONTRACT.md` point their radio lines here.~~ — done 2026-11-10 (docs on `main`)
1. ~~**Server:** stations list fields, favourites, tags, logo resolver and cache, with tests and fixtures.~~ — done, PR #965 (merged 2026-11-10)
2. ~~**Server:** live "now" holder, `/now`, `/api/radio/now`, `in_library`, `cover_url`.~~ — done, PR #966 (merged 2026-11-10)
3. **Server:** scrobble on threshold (off by default) and love. — PR open (not merged).
4. **Android:** decoders, Radio section, logos, favourites.
5. **Android:** playback service, live Now Playing, Download and Heard states.
6. **Android:** reconnect, sleep timer, settings.

After slice 6, work stops. Publication and deployment are separate decisions and need the owner's explicit authorization (`DEVELOPMENT_WORKFLOW.md`).

## 10. Deployment gate

Before asking for authorization, record:

- the image tag;
- the new `radio.sqlite3` columns or tables;
- the new data-directory logo cache;
- the rollback reference.

Owner checks on a live deployment:

- a real station plays on a phone over Tailscale;
- the logo appears;
- the live title changes with the song;
- Download enables after about 30 seconds and the song reaches the library;
- a station with no ICY metadata plays without a button.

## 11. Stage 2 gate

Stage 2 (macOS) starts only after deployment is authorized and the checks in section 10 are recorded. The stage 2 layout and theme work follow the same rules as `macos/DESIGN.md`.

## 12. Risks

- **No metadata:** stations that serve playlists, send no ICY titles, or use the non-HTTP `ICY 200 OK` status line give no title and no Download. The client says so.
- **Unparsed titles:** shown, but not downloadable (RADIO-01 rule).
- **Wrong MusicBrainz match** can download another album's version of a song. The existing exact-match rule is kept.
- **Relay in the audio path:** every proxied listener goes through the app. A relay outage stops the station; the switch to turn relaying off must stay easy to reach.
- **Logo sources:** Radio Browser is a community service with no guarantee. The fallback chain means its failure never blocks a station. The size cap and SSRF guard limit a large or hostile image.
- **Scrobble duplicates** if a station's title repeats within 10 minutes, or if another source also scrobbles.

## 13. Decisions recorded (owner, 2026-11-10)

1. Lifting "radio is out of scope" through this contract: approved.
2. All proposed ideas are in except recording. Build in two stages: server and Android first, then deployment, then macOS.
3. The live title that enables Download comes from `/now`; clients read ICY only for an instant display.
4. Radio Browser is approved as an external logo source.

## 14. Open questions

1. Whether `/api/radio/now` should also list idle stations with their last known title. Current position: no, `idle` only.
2. Logo sizes. Current position: 128 and 512 px, PNG or WebP.
3. Whether the logo override upload is available from the web Radio settings panel too, or Android only. Current position: a small Radio settings panel on the web page, since RADIO-01 already has one.
