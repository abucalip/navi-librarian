# Internet radio playback contract (Discair)

Status: **approved by the owner on 2026-11-10. Stage 2 (macOS) started 2026-11-13, section 5. Stage 1 slice 0 (contract), slice 1 (server stations list, favourites, tags, logos; PR #965) slice 2 (server live "now" holder, `/now`, `/api/radio/now`; PR #966) slice 3 (server scrobble and love; PR #967) slice 4 (Android decoders, Radio page, logos, favourites; PR #968) and slice 5 (Android playback, live Now Playing, Download and Heard states; PR #969) are merged (2026-11-10). Slice 6 (reconnect, sleep timer, settings) is merged (PR #970, 2026-11-10); stage 1 is complete and the deployment gate is next. Stage 2 (macOS) starts only after deployment is authorized and verified.**

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

Slice 5 note (PR #969): the route returned the raw table rows, so `in_library` was not sent and the Heard list could not show Owned. Fixed in PR #971 (merged 2026-11-10, `5aee5fbd`): every play carries `in_library`, an exact artist and title match against the library, cached per song (found songs kept, misses re-checked after 5 minutes, failed searches retried). A play without an artist is always false. The Android decoder already reads the field.

### 3.7 Scrobbling and love

- `POST /api/radio/plays/{play_id}/scrobble` is called by the server itself once a song crosses the 30-second threshold, only when the owner has switched radio scrobbling on (Settings, default **off**). It reuses the existing Last.fm scrobbling code. A play is scrobbled at most once.
- A "love" action on a play is a separate request.
- Before slice 3 ships, the change must show that radio scrobbles do not double-count with Navidrome's own scrobbling, which does not see radio plays.

Slice 3 note (PR #967, merged 2026-11-10 as `ae69fcf0`): the repository had no Last.fm write code, so this slice adds `integrations/radio/scrobble.py` that calls Last.fm `track.scrobble` and `track.love` directly, signed with `LASTFM_SHARED_SECRET` and a `LASTFM_SESSION_KEY` (both from the configuration; no password is asked for). Without a session key, switching scrobbling on is refused. A play is claimed before the call (`scrobbled`), so it is sent at most once and a failed request is never retried. Routes: `GET`/`PUT /api/radio/scrobbling` (default off) and `POST /api/radio/plays/{id}/love`. The scrobble has no `POST .../scrobble` route: the server sends it itself from the threshold, so the route named in the first bullet above was not built. The double-count check is by design only: radio songs never pass through Navidrome, so the server's Last.fm call is the only scrobble for them; a live check against the owner's account is still needed.

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
- **Slice 6 note:** (a) Reconnect: after a drop or a stall of 20 seconds the client tries again after 2, 5, 10, 20 and 30 seconds, then shows "Station unreachable" with Retry; sound resets the count; nothing is tried while the app is in the background or after a pause. A relay or station that answers with an error status counts as a drop for a station (a song would be skipped). (b) The app had no sleep timer, so "reuses the existing timer" became a new generic `SleepTimer` (15, 30, 45, 60 or 90 minutes, pause on expiry), offered on the radio Now Playing sheet and cancelled when a station is no longer playing. (c) Settings: the scrobbling switch (disabled with an explanation when the server says Last.fm is not set up), a per-station logo picker (Change uploads up to 2 MB, Reset clears the override), and the app address shown read only: changing it rewrites the stations in Navidrome, so it stays on the web Radio page. Not seen on a device.
- Everything in `ANDROID_CLIENT_CONTRACT.md` section 2 applies: 48dp targets, TalkBack labels, no third-party SDKs or analytics, bundled assets, honest states, and the `/mobile-design` pass recorded in `android/DESIGN.md`.

## 5. macOS client (stage 2, started 2026-11-13)

The owner reports the server and Android parts deployed and working (2026-11-13), so stage 2 starts. The owner chose the macOS design. The detailed slices are S2-0 to S2-5 in [`RADIO_PLAYBACK_PROPOSAL.md`](RADIO_PLAYBACK_PROPOSAL.md), "Stage 2 detailed plan". The mockups in [`design/macos-radio/mockups.html`](design/macos-radio/mockups.html) are the spec; the options the owner chose are the ones the page opens on. The rules below are what the macOS slices build against. Where the earlier stage 2 bullets differ, these rules govern.

### 5.1 Choices (owner, 2026-11-13)

| Area | Chosen | Not built |
|---|---|---|
| A · Radio page | A2 Tuner: station list left, fixed On Air panel right | A1, A3 |
| B · Player bar while a station plays | B2 level meter (fallback B1, see 5.4) | B3 |
| C · Now Playing | C1 song first, "Heard on (station) tonight" in the right column | C2 |
| D · Menu bar item | D2 item with a popover | D1 |
| E · Extras | E1 ⌘1 to ⌘9 for the first nine favourites; E5 Edit Tags on the Mac; E7 radio card on Home | E2, E3 (no Love button), E4, E6, E8, E9 |

### 5.2 Corrections to the earlier stage 2 bullets

1. **One theme.** Zine is removed (`macos/DESIGN.md`, "Night mode and Zine removal"). Radio is drawn once, in Cupertino Day and Night, through the `CU` colour roles only; no accent hex in a view.
2. **Menu bar item.** The app has none today; D2 adds it as its own slice.
3. **Sleep timer is in scope on the Mac.** `MACOS_CLIENT_CONTRACT.md` lifts it with the radio line.
4. **Live playback has its own path.** A live stream does not fit the `AVAudioEngine` pipeline that plays files, so radio gets a separate live player behind `PlayerModel` (5.4).
5. **The "Heard on Radio" tape is not a screen.** Home's heard rows and the new Heard list show Downloaded and Owned.
6. **Media keys.** Play/pause stops and restarts a station (a live stream cannot keep its place). Next and Previous move through the favourite stations. Seek is off while a station plays.
7. **Names.** `RadioModel` already means "Radio from this" (`DiscairUI/Model/QueueWorkspace.swift`). The internet radio types use the `Station` and `Live` prefixes. The sidebar row is "Radio".

### 5.3 Request budget

- Stations list (`GET /api/radio/stations`): on opening the Radio page, after a favourite, tag or logo change, and at most once a minute while the page stays open.
- Live titles of all stations (`GET /api/radio/now`): every 15 s, only while the Radio page is visible and the window is not hidden or minimised.
- The playing station's `GET /api/radio/stations/{id}/now`: every 5 s while it plays, from any screen. It stops with the stream. This is the only title source; the Mac does not read ICY titles itself in this version, so the title and the Download rule never disagree.
- Heard list (`GET /api/radio/plays`): on opening the Radio page or radio Now Playing, and when the playing station's `play_id` changes. No timer.
- Logos: one fetch per station and size (128 in rows and menus; 512 for the bar, Now Playing and the system cover), kept in memory and on disk under the app's caches folder. Refetched after Change or Reset, and after "Reset saved data".
- Nothing is requested while the window is hidden and no station plays. One request of each kind at a time; a slow answer is not stacked with another.
- The `playable_url` is never logged, displayed or put in an error text.

### 5.4 Live playback

- **Engine:** `AVPlayer` on `playable_url`, behind a `LiveOutput` protocol (`start(url:)`, `stop()`, `volume`, state and level callbacks) so the model is tested with a fake. It lives in `DiscairAudio`.
- **Level meter (B2):** an audio tap on the player item gives one RMS value about 15 times a second; the last 64 values are drawn as bars, newest on the right, white at 17% opacity, at most half the bar's height.
- **Proof first:** the spike S2-2 plays one relayed MP3 and one relayed AAC station and records the result in `macos/DESIGN.md`. If the tap gives no samples on relayed stations, the work stops and the owner decides between B1 everywhere and decoding the stream into the existing engine.
- **Fallback (stated by design, not as an error):** when no samples arrive within 3 s of sound, or under Reduce Motion or Low Power Mode, the meter is not drawn and the bar shows B1: a 3 pt hairline at 22% white on its bottom edge.
- **Switched off in live mode:** seek, the waveform, gapless and crossfade, output sample-rate matching (`restoreOutputRate()` runs before a station starts), client scrobbling (the server scrobbles radio), feedback events, the saved queue (a station is never written to it), lyrics, facts, the flip cover, booklet, disc and slideshow. The equalizer does not apply to radio; the Equalizer screen says so in one line while a station plays.
- **Addresses the Mac cannot play:** a station that is not relayed and whose address is a `.pls` or `.m3u` playlist shows "This station's address is a playlist the Mac cannot play. Switch its relay on from the web Radio page." It never fails silently.
- **Queue:** starting a station pauses the library song and leaves the queue as it is. Stopping the station leaves the queue paused on the same song. Playing a library song stops the station.
- **Reconnect (same rule as Android, section 4):** after a drop, an error status, or 20 s without sound, retry after 2, 5, 10, 20 and 30 s; sound resets the count; after the fifth failure the state is "Station unreachable" with Retry. Nothing is tried after the owner pressed stop. While the Mac sleeps nothing is tried; on wake, one fresh round if a station was playing.
- **Sleep timer (same rule as Android):** Off, 15, 30, 45, 60 or 90 minutes. On expiry a station stops and a library song pauses. Cancelled when playback stops.

### 5.5 States and words

The Download button follows the Android rules in `model/Radio.kt` (`RadioDownload`). Owned wins over everything.

| State | Rule | Words |
|---|---|---|
| Waiting | `ok`, `play_id` null | "Listening · 18 s" with a small ring; disabled. The seconds count from when the Mac first saw the title, capped at 30; the server's `play_id` alone enables Download |
| Ready | `ok` with `play_id`, not grabbed, not in library | "Download" |
| Working | the Get request is in flight | "Downloading…"; disabled |
| Done | `grabbed` | "✓ Downloaded"; disabled |
| Owned | `in_library` | "✓ Owned"; disabled |
| Failed | the server refused | "Try again", with the server's sentence beside it |
| No button | `no_metadata`, `unparsed`, `not_proxied`, `idle` | the sentence from section 6 |

Every state is words plus a mark, never colour alone. Other rules: every control has a spoken label and a keyboard path; the star says "on" or "off"; LIVE is a word; text never goes below the caption size; no address, token or password appears in any text, log or error.

### 5.6 Slices

S2-0 documents (this change). S2-1 stations, the Radio page, favourites and tags. S2-2 live playback, the bar, media keys, mini player and widget (after the spike). S2-3 the live song, Now Playing, Download, Heard and the Home card. S2-4 reconnect, sleep timer, Settings and ⌘1 to ⌘9. S2-5 the menu bar item. Each slice is one PR with focused tests; the owner runs the full suite and checks the live behaviour listed in the proposal, S2.10.

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
3. ~~**Server:** scrobble on threshold (off by default) and love.~~ — done, PR #967 (merged 2026-11-10)
4. ~~**Android:** decoders, Radio section, logos, favourites.~~ — done, PR #968 (merged 2026-11-10)
5. ~~**Android:** playback service, live Now Playing, Download and Heard states.~~ — done, PR #969 (merged 2026-11-10)
6. ~~**Android:** reconnect, sleep timer, settings.~~ — done, PR #970 (merged 2026-11-10; see the slice 6 note in section 4)

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

Stage 2 (macOS) starts only after deployment is authorized and the checks in section 10 are recorded. **Recorded 2026-11-13:** the owner reports the server and Android parts deployed and working, and stage 2 started; the section 10 checks are as the owner reported them, not re-run by the agent. The stage 2 layout and theme work follow the same rules as `macos/DESIGN.md`.

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
