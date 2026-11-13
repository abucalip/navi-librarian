# Internet radio playback proposal

**Status:** owner decisions recorded 2026-11-10 (see "Decisions recorded"). Approved for build in two stages. Stage 1 slices 0 to 6 are done (slice 1 merged as PR #965, slice 2 as PR #966, slice 3 as PR #967, slice 4 as PR #968, slice 5 as PR #969, slice 6 as PR #970, all 2026-11-10); struck-through items below are built. Stage 1 is complete; the deployment gate is next.
**Date:** 2026-11-10
**Stage 2 update (2026-11-13):** the owner reports the server and Android parts deployed and working, and chose the macOS design (A2 · B2 · C1 · D2 · E1 E5 E7). The detailed macOS plan is in "Stage 2 detailed plan"; the mockups are in [`design/macos-radio/`](design/macos-radio/mockups.html). No macOS code is written yet.
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
No new endpoint beyond the existing `/api/radio/plays`, with `grabbed` and `in_library` exposed so a client can show Download, Downloaded and Owned states. ~~**Gap found in slice 5:** the route returned the raw `radio_plays` rows, so `in_library` was missing.~~ — fixed, PR #971 (merged 2026-11-10, `5aee5fbd`): each play now carries `in_library`, looked up once per song (found songs kept, misses re-checked after 5 minutes, a failed search not kept); the Android Heard list reads it already and shows Owned.

### ~~Scrobbling and love (idea 5)~~ — done, PR #967 (merged 2026-11-10); deviations are in the contract, section 3.7
~~The server scrobbles a song to Last.fm once it crosses the 30-second threshold, when the owner has switched radio scrobbling on (`GET`/`PUT /api/radio/scrobbling`, default off). A play is scrobbled at most once. `POST /api/radio/plays/{id}/love` loves a play on Last.fm.~~ Deviation: the repository had no Last.fm write code, so the slice added it (`integrations/radio/scrobble.py`) rather than reusing it. The scrobble is sent by the server directly, not by a `POST .../scrobble` endpoint. The double-count check is by design only (radio songs never pass through Navidrome); a live check against the owner's account is still open.

### Contract fixtures
Fixtures for each `/now` state, the stations list with and without logos, and the empty and unavailable cases, in the existing contract-fixtures layout so Android and macOS decoders are tested against the same files.

## Android work (stage 1)

- ~~A Radio section: station list with logos, favourites first, the live title strip (from `/api/radio/now`).~~ — done, PR #968 (a Radio row on Home opens the page; the favourite toggle is there; tapping a station plays nothing until slice 5)
~~- Playback through the existing Media3 service as a live stream: no seek bar, no duration, no gapless or crossfade, notification and lock-screen showing the station logo and the live title (cover when `cover_url` exists).~~ — done, PR #969 (live item with no seek, scrobble or saved queue; notification and lock screen carry the live title and picture, updated in place, not yet seen on a device)
~~- Now Playing for radio: live title, cover or logo, favourite toggle, Download button (enabled by the rule above, with Downloaded and Owned states), Get result messages from the existing endpoint.~~ — done, PR #969 (built like the song sheet; one neutral layout for all themes; Owned shows from `/now`)
~~- Heard list screen with the same states.~~ — done, PR #969 (Owned shows in the Heard list once the server sends `in_library`; it does since PR #971)
- ~~Reconnect policy (idea 7): automatic retry with backoff when the stream drops or stalls, a clear "station unreachable" state after a bounded number of attempts, and no retry loop while the app is in the background without playback.~~ — done, PR #970 (2, 5, 10, 20, 30 s backoff, then Station unreachable with Retry; none in background or after a pause)
- ~~Sleep timer (idea 8) for radio, reusing the existing Android timer if there is one.~~ — done, PR #970 (the app had no timer, so a new generic one: 15 to 90 min)
- ~~Settings: radio scrobbling switch, logo override picker.~~ — done, PR #970 (scrobbling switch, per-station logo Change/Reset)
- ~~Android also needs the app address set (already stored in `radio_settings`), because the relay URL must be reachable from the phone (Tailscale address).~~ — done, PR #970 (shown read only in Settings; edited on the web Radio page)

## Stage 1 slices

0. ~~Contract and doc edits (docs only, directly on `main`).~~ — done 2026-11-10 (docs on `main`)
1. ~~Server: stations list fields, favourites, logo resolver and cache, with tests and fixtures.~~ — done, PR #965 (merged 2026-11-10)
2. ~~Server: live "now" holder, `/now`, `/api/radio/now`, `in_library`, `cover_url`.~~ — done, PR #966 (merged 2026-11-10)
3. ~~Server: scrobble on threshold (off by default) and love.~~ — done, PR #967 (merged 2026-11-10)
4. ~~**Android:** decoders, Radio section, logos, favourites.~~ — done, PR #968 (merged 2026-11-10)
5. ~~Android: playback service, live Now Playing, Download and Heard states.~~ — done, PR #969 (merged 2026-11-10)
6. ~~Android: reconnect, sleep timer, settings.~~ — done, PR #970 (merged 2026-11-10)

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

## Stage 2 detailed plan (macOS; owner choices 2026-11-13)

This section details the five bullets above. Where it differs from them, this section is the newer text; the bullets are kept for the record. Nothing here is built. The server and Android parts are deployed and working (owner, 2026-11-13) and need no additions: every endpoint below already exists.

**Mockups (the spec):** [`design/macos-radio/mockups.html`](design/macos-radio/mockups.html), with `mockups.css` (the page around the mockups), `cupertino-radio.css` (the app as drawn: colour roles for Day and Night and every radio component) and `mockups.js` (sample data and drawing code). Open the HTML file in a browser; it needs no network. All options that were offered are kept in the file; the chosen ones are marked "chosen" and are what the page opens on.

### S2.1 Owner choices

| Decision | Chosen | Not chosen (kept in the mockups, not built) |
|---|---|---|
| A · Radio page | **A2 Tuner:** station list on the left, fixed On Air panel on the right | A1 Station wall, A3 Presets and On Air |
| B · Player bar while a station plays | **B2 Level meter:** live level bars where the sound graph is | B1 Plain live (also the fallback, see S2.6), B3 Session tape |
| C · Now Playing | **C1 Song first:** cover, title, artist; Heard on this station where lyrics are | C2 Station first |
| D · Menu bar item | **D2:** menu bar item with a popover, for radio and library songs | D1 none |
| E · Extras | **E1** ⌘1 to ⌘9 for favourite stations · **E5** edit tags on the Mac · **E7** radio card on Home | E2 "Tune to" in ⌘K, E3 Love, E4 drop an image as logo, E6 Download all heard, E8 notification, E9 resume at launch |

Consequences of what was not chosen: no Love button anywhere (the mockups draw one in A2 and C1 only when E3 is ticked on the page); no radio entries in the command palette; no drag and drop of logos (Change and Reset in Settings stay, as on Android).

### S2.2 Corrections to the earlier stage 2 text

1. **"One view per theme" no longer applies.** Zine was removed (`macos/DESIGN.md`, "Night mode and Zine removal"). There is one theme, Cupertino, in Day and Night. Radio is drawn once and must read in both modes at every accent hue, through the `CU` colour roles only.
2. **There is no menu bar item today.** The app has the main window, the floating mini player, the widget and the media keys. D2 adds the menu bar item as its own slice (S2-5).
3. **The sleep timer is out of scope in `MACOS_CLIENT_CONTRACT.md`** (line 9, "sleep timer"). Slice S2-0 lifts it together with the radio line.
4. **A live stream needs its own playback path.** `AVAudioEngineOutput` (`DiscairAudio/AudioOutput.swift`) plays files through two player nodes for gapless, crossfade, the waveform and sample-rate matching. None of that fits an endless stream. Radio gets a separate live player behind `PlayerModel` (see S2.6).
5. **The "Mailroom tape" is not a screen.** Home already lists heard songs with Get (`HomeDashboard`, the `.radio` row, fed by `GET /api/radio/plays`). The bullet becomes: Home's heard rows and the new Heard list show Downloaded and Owned.
6. **Media keys.** Play/pause stops and restarts the stream (a live stream cannot pause and keep its place). Next and Previous move through the favourite stations. Seeking is switched off while a station plays.
7. **Name clash.** `RadioModel` already exists in `DiscairUI/Model/QueueWorkspace.swift` and means "Radio from this" (similar songs from the library). The internet radio types must not reuse it. Use the `Station` and `Live` prefixes below. In the UI, the sidebar row is "Radio"; the existing artist-page button "Radio" keeps its meaning.

### S2.3 What exists and is reused

| Need | Existing code | Note |
|---|---|---|
| Heard list rows | `RadioPlay`, `LibrarianClient.radioPlays(limit:)`, `getRadioPlay(id:)` in `macos/Sources/DiscairLibrarian/HomeFeeds.swift` | Already decode `grabbed` and `in_library`. `AppState.radioPlays` holds them for Home. |
| Authenticated calls | `LibrarianClient.authedSendPublic`, `decodePublic` | Same pattern for every new call. |
| Player state | `PlayerModel` (`@Observable`, `Phase`, `onNowPlayingChange`) in `DiscairUI/Model/PlayerModel.swift` | Gains a live session (S2.6). |
| Player bar | `CupertinoPlayerBar` (`Themes/Cupertino/CupertinoPlayerBar.swift`), height 92 pt, corner radius 16, blurred artwork with a dim layer | Gains a live branch. |
| Now Playing | `CupertinoNowPlaying.swift`, `BlurredArtwork` | Gains a live branch. |
| System | `SystemMedia.swift` (media keys, Control Centre), `WidgetPublisher.swift` and `NowPlayingSnapshot`, `Chrome/MiniPlayer.swift` | Each gains a live case. |
| Navigation | `Screen` in `Model/AppState.swift`, `CupertinoSidebar` in `CupertinoTheme.swift` | New case and row. |
| Home | `HomeDashboard.swift`, `CupertinoHome.swift` (the `.radio` row) | States and the E7 card. |
| Settings | `CupertinoSettings.swift` (tabs) | New Radio tab. |
| Covers | `ArtworkStore` (owned-artwork route for `cover_url`) | Logos use their own small cache (S2.5). |
| Decoder tests | `android/contract-fixtures/librarian/radio_*.json`, linked into `DiscairLibrarianTests` as `Fixtures` (`macos/README.md`) | 13 radio fixtures exist: `radio_stations`, `radio_stations_empty`, `radio_station_favourite`, `radio_station_tags`, `radio_station_logo`, `radio_now_ok`, `radio_now_ok_waiting`, `radio_now_no_metadata`, `radio_now_unparsed`, `radio_now_not_proxied`, `radio_now_unavailable`, `radio_now_idle`, `radio_now_all`. |
| Android reference | `android/app/src/main/kotlin/app/discair/model/Radio.kt` (decoders, `RadioDownload` words and rule), `player/RadioPlayback.kt` (live item, reconnect), `player/SleepTimer.kt`, `ui/radio/RadioScreen.kt`, `RadioNowPlaying.kt`, `HeardScreen.kt`, `ui/settings/RadioSettings.kt` | Read these first: the Mac follows the same rules and the same words. |

### S2.4 Endpoints used (all deployed; none added)

| Call | Used for |
|---|---|
| `GET /api/radio/stations` | The list. Server order is kept (favourites, then last played, then name); the Mac never re-sorts. `id` is a string. `last_played_at` is Unix seconds or null. |
| `GET /api/radio/stations/{id}/now` | The playing station's live song, `play_id`, `in_library`, `cover_url`. |
| `GET /api/radio/now` | Live titles of all stations, only while the Radio page is on screen. |
| `GET /api/radio/stations/{id}/logo?size=128` or `512` | Logos. 128 in rows and menus, 512 for the bar, Now Playing and the system cover. Always answers with an image (generated tile when none), so the Mac never draws its own placeholder logo. |
| `PUT /api/radio/stations/{id}/favourite` `{"favourite": bool}` | The star. |
| `PUT /api/radio/stations/{id}/tags` `{"tags": [...]}` | Edit Tags (E5): at most 10 tags of 24 characters. |
| `PUT` and `DELETE /api/radio/stations/{id}/logo` | Settings: Change (up to 2 MB) and Reset. |
| `GET /api/radio/plays` | Heard list (exists in the Mac client). |
| `POST /api/radio/plays/{id}/get` | Download (exists in the Mac client). |
| `GET` and `PUT /api/radio/scrobbling` | Settings switch. The answer has `enabled` and `configured`; when `configured` is false the switch is disabled with an explanation. |
| `GET /api/radio/settings` | The app address, shown read only. |
| `playable_url` from the stations list | The stream. Never logged, never displayed, never put in an error text (contract principle 6). |

Not used on the Mac: `POST /api/radio/plays/{id}/love` (E3 not chosen), enable and disable of the relay, deleting plays.

### S2.5 Request budget

- The stations list: on opening the Radio page, after a favourite, tag or logo change, and at most once a minute while the page stays open.
- `/api/radio/now`: every 15 s, only while the Radio page is visible and the window is not hidden or minimised.
- The playing station's `/now`: every 5 s while it plays, from any screen. It stops with the stream.
- `/api/radio/plays`: on opening the Radio page or Now Playing for radio, and when the playing station's `play_id` changes (a new song crossed 30 s). No timer.
- Logos: fetched once per station and size, kept in memory and on disk under the app's caches folder, keyed by station id and size. Refetched after Change or Reset, and when the app's "Reset saved data" button is used.
- Nothing is asked for while the window is hidden and no station plays. One request of a kind at a time; a slow answer is not stacked with a second request.

### S2.6 Live playback: decision and proof

- **Engine:** an `AVPlayer` on `playable_url`, wrapped as `LiveStreamPlayer` behind a small protocol (`LiveOutput`: `start(url:)`, `stop()`, `volume`, a state callback, a level callback) so the model is tested with a fake. It lives in `DiscairAudio`.
- **Level meter (B2):** an `MTAudioProcessingTap` on the player item's audio track gives the samples. The meter shows the level history: one RMS value about 15 times a second, the last 64 values as bars, newest on the right. No spectrum analysis. Bars are white at 17% opacity and at most half the bar's height, the same limits as the song sound graph (`macos/DESIGN.md`, "Player bar refinements").
- **Fallback, stated in the UI by design, not by error:** when the tap gives no samples within 3 s of sound (HLS addresses do not expose a tappable track), or under Reduce Motion or Low Power Mode, the meter is not drawn and the bar is B1: a 3 pt hairline at 22% white on the bottom edge.
- **Proof first:** S2-2 starts with a spike in the `AudioSpike` target that plays one relayed MP3 station and one relayed AAC station and confirms sound and tap samples. Record the result in `macos/DESIGN.md`. If the tap does not work on relayed stations, stop and ask the owner: the alternatives are B1 for everything, or decoding the stream into the existing engine, which is a larger piece of work.
- **What live mode switches off:** seek, the waveform, gapless and crossfade, output sample-rate matching (call `restoreOutputRate()` before a station starts), client scrobbling (the server scrobbles radio), feedback events, the saved queue (`persist()` never writes a station), lyrics, facts, the flip cover, booklet, disc and slideshow. The equalizer does not apply to radio in this version; the Equalizer screen says so in one line while a station plays.
- **Addresses the Mac cannot play:** a station that is not relayed and whose address is a `.pls` or `.m3u` playlist shows "This station's address is a playlist the Mac cannot play. Switch its relay on from the web Radio page." No silent failure.
- **Queue:** starting a station pauses the library song and leaves the queue as it is. Stopping the station leaves the queue paused on the same song. Playing a library song stops the station.
- **ICY titles read by the Mac itself** (contract principle 3 allows it for display only) are not built in this version; the 5 s `/now` poll is the only title source, so the title and the Download rule never disagree.

### S2.7 Colour, type and size reference

Use the `CU` roles in Swift. The hex values are the Day and Night defaults in `CUPalette` (`CupertinoPalette.swift`), given so the mockups can be checked by eye. The accent changes with the owner's hue slider, so never write an accent hex in a view.

| Role (`CU`) | Day | Night | Used in radio for |
|---|---|---|---|
| `content` | `#FFFFFF` | `#0B0B0D` | Page ground, text field ground |
| `panel` | `#F5F5F7` | `#151518` | On Air panel's Heard box, Home card, sheets, menus |
| `fill` | `#ECECF0` | `#202025` | Tag chips, neutral buttons, "Listening" button, selected sidebar row |
| `text` | `#1D1D1F` | `#F2F2F4` | Names, titles |
| `textSecondary` | `#636368` | `#9E9EA7` | Status sentences, artist, time |
| `textTertiary` | `#8E8E93` | `#6E6E78` | Empty star, placeholders, shortcut hints |
| `separator` | `#E5E5EA` | `#27272C` | Row rules, "Owned" outline |
| `accent` | `#D61F4A` | `#FF7A8F` | Download and Retry fill, live title in the list, filled star, LIVE badge on light ground |
| `accentStrong` | `#C8163F` | from the palette | Text on white buttons over artwork |
| `accentTint` | `#FCE8EC` | panel mixed with the accent (mockup `#33202A`) | Selected station row |
| `onAccent` | `#FFFFFF` | `#0B0B0D` | Label on the accent |
| `success` / `successTint` | `#187A48` / `#E6F4EC` | `#47C285` / panel + 16% | "Downloaded"; the connection indicator |
| `warning` / `warningTint` | `#8A5200` / `#FFF4DC` | `#F2B04A` / panel + 16% | "Downloading…", "Reconnecting" |
| `danger` / `dangerTint` | `#B3261E` / `#FBEAE8` | `#FF7B72` / panel + 16% | "Station unreachable" |
| `onMedia` | `#FFFFFF` | `#FFFFFF` | All text and marks on the bar, the On Air panel and Now Playing |

Download button states (the words are Android's, `RadioDownload` in `model/Radio.kt`):

| State | Rule | Words | On a page (fill / label) | Over artwork (bar, On Air, Now Playing) |
|---|---|---|---|---|
| Waiting | `state` is `ok`, `play_id` null | "Listening · 18 s" with a small ring; disabled | `fill` / `textSecondary` | white 18% / white |
| Ready | `ok` with `play_id`, not grabbed, not in library | "Download" | `accent` / `onAccent` | white / `accentStrong` |
| Working | the Get request is in flight | "Downloading…"; disabled | `warningTint` / `warning` | white 18% / white |
| Done | `grabbed` | "✓ Downloaded"; disabled | `successTint` / `success` | green 25% / white |
| Owned | `in_library` (wins over everything) | "✓ Owned"; disabled | outline `separator` / `textSecondary` | outline white 35% / white |
| Failed | the server refused | "Try again", with the server's sentence beside it | `accent` / `onAccent` | white / `accentStrong` |
| No button | `no_metadata`, `unparsed`, `not_proxied`, `idle` | the sentence from contract section 6 | | |

Every state is words plus a mark, never colour alone. The seconds in "Listening" count from the moment the Mac first saw this title, capped at 30; they are a display aid, the server's `play_id` is the only thing that enables Download.

Other fixed values from the mockups and the app:

| Thing | Value |
|---|---|
| Sidebar | `CU.Shell.sidebarWidth` 216 pt, radius `CU.sidebarRadius` 20; the Radio row uses the SF Symbol `radio`, placed under Library |
| Page title | `CU.Font.largeTitle` (34/40 bold). Section labels: `CU.Font.eyebrow` (11 bold, capitals). Rows: `headline` 13 semibold over `callout` 12 |
| Spacing | `CU.Space`: 4, 8, 16, 24, 32 |
| Station row | Logo 34 pt with 22% corner radius, name, status sentence, tag chip, star. Row radius `CU.Shell.rowRadius` 12. The selected (playing) row has the `accentTint` ground |
| On Air panel | 330 pt wide, radius 14, cover or logo 120 pt, blurred artwork behind with a 30% black layer; below 880 pt of content width the panel moves under the list |
| Player bar | Unchanged: 92 pt high, radius 16, cover or logo 50 pt. Blur 24, saturation 1.3, dim 28% (35% on bright artwork), as today |
| LIVE badge | 10.5 pt bold, tracking 0.08 em, radius 4. Over artwork: white ground, `accentStrong` text. On a page: `accent` ground, `onAccent` text. Always the word, never a dot alone |
| Level meter | 64 bars, 3 pt gap, white 17%, at most 50% of the bar's height, top corners 2 pt |
| Now Playing (C1) | Cover 230 pt, radius 12; title `title1`; right column "Heard on (station) tonight" |
| Menu bar popover | 300 pt wide, radius 14, cover 54 pt; menu bar title cut at 30 characters |
| Mockup-only colours | The purple, pink and blue washes behind the bar and On Air panel stand in for blurred artwork. The coloured logo tiles stand in for the server's logos. Do not copy either. |

### S2.8 Slices

Each slice is one PR from a worktree off `origin/main`, with filtered tests only (`DEVELOPMENT_WORKFLOW.md`); the owner runs the full suite. Each PR adds its section to `macos/DESIGN.md`, lists what the mockup shows that was dropped or changed, and names what was not verified (not heard, not seen in a window). Check CI before reporting success.

#### S2-0 · Documents (directly on `main`)

1. `RADIO_PLAYBACK_CONTRACT.md` section 5: replace the four bullets with the rules of this section (choices, corrections, request budget, live-mode rules, states). Section 11: record that the deployment checks are done (owner, 2026-11-13).
2. `MACOS_CLIENT_CONTRACT.md` line 9: remove internet radio and the sleep timer from "Out of scope" and point to the radio contract. Add the menu bar item to the window list (section with the mini player).
3. `macos/DESIGN.md`: a "Radio (stage 2)" section naming the mockups folder and the choices.
4. `ACTIVE_WORK.md`: stage 2 as the current macOS task, one line per slice.

#### S2-1 · Stations: decoders, model, the Radio page (A2), favourites, tags (E5)

1. **Decoders** in a new `macos/Sources/DiscairLibrarian/Radio.swift`:
   - `RadioStation`: `id` (String), `name`, `proxied`, `playableURL`, `homepageURL`, `logoPath`, `favourite`, `tags`, `lastPlayedAt` (Unix seconds, optional). Do not decode `stream_url`. Lossy list decoding (one unreadable row must not hide the rest; reuse `FeedLossy`). Give the type a `description` that leaves the address out, so it cannot reach a log.
   - `RadioNow`: `state` as an enum (`ok`, `noMetadata`, `unparsed`, `notProxied`, `unavailable`, `idle`, and `unknown` for anything else, shown like `noMetadata`), `rawTitle`, `artist`, `title`, `playID`, `inLibrary`, `coverPath`. `RadioNowAll` is the same per station id.
   - `RadioScrobbling` (`enabled`, `configured`).
2. **Client calls** as an extension of `LibrarianClient`: `radioStations()`, `radioNow(station:)`, `radioNowAll()`, `setRadioFavourite(station:on:)`, `setRadioTags(station:tags:)`, `radioLogo(station:size:)` (bytes), and for S2-4 `radioScrobbling()`, `setRadioScrobbling(_:)`, `uploadRadioLogo(station:data:)`, `resetRadioLogo(station:)`, `radioSettings()`.
3. **Tests:** `RadioClientTests` in `DiscairLibrarianTests`, one test per fixture listed in S2.3, plus: an unknown state decodes as `unknown`; a station description never contains its address.
4. **Rules, pure and tested** (`DiscairUI/Model/Stations.swift`, `StationRules`):
   - the status sentence of a row: live title in the accent for a listening station; "Not relayed · no song titles"; "Sends no song titles"; "Station unreachable"; else "Played today, 18:40", "Played yesterday", "Played 3 days ago", "Never played";
   - the tag chips: All, then each tag once (case-insensitive), most used first;
   - `DownloadState` from a `RadioNow` or a `RadioPlay` (table in S2.7), Owned first;
   - tag validation for the sheet: trimmed, no blanks, no case-insensitive duplicates, at most 10 of 24 characters.
5. **`StationsModel`** (`@MainActor @Observable`, owned by `AppState` as `stations`): the list, `nowByID`, the tag filter, loading, empty and error states, and the polling of S2.5 driven by a `pageVisible` flag. After a favourite or tag change it shows the change at once, sends it, then reloads the list; a refusal puts the old value back and shows the server's sentence.
6. **Navigation:** `Screen.stations`; sidebar row "Radio" under Library; `selected` maps the screen to it. A Go menu or View menu entry as the other pages have.
7. **The page** `Themes/Cupertino/CupertinoStations.swift`, built from mockup A2: title, tag chips, the station list (logo, name, sentence, first tag, star button with a spoken label "Favourite, on"), and the On Air panel. In this slice the panel shows "Nothing playing. Choose a station." and a row click does nothing yet beyond selecting it.
8. **Edit Tags (E5):** right-click a station, "Edit Tags…", the sheet from the "Small pieces" mockup; Return adds a tag, Save sends the list, Cancel closes.
9. **States with words:** no stations ("No stations yet. Add one in Navidrome and it appears here."), Librarian not reachable (the app's usual error kinds with Try Again), loading.
10. **Tests to run:** `swift test --skip-update --filter "RadioClientTests|StationRulesTests|StationsModelTests"` and one render test of the page in Day (`CupertinoPagesRenderTests` pattern).

#### S2-2 · Live playback, the bar (B2), media keys, mini player, widget

1. **Spike** (S2.6 "Proof first"). Stop if it fails.
2. **`DiscairAudio`:** `LiveOutput` protocol; `LiveStreamPlayer` (AVPlayer, the tap, RMS at about 15 Hz, state: connecting, playing, stalled, failed); a `FakeLiveOutput` in the tests.
3. **`PlayerModel`:** a `live` value (station id, name, logo path, started at, phase: connecting, playing, reconnecting, unreachable) and `levels` (the last 64 values). `playStation(_:)`, `stopStation()`. `togglePlayPause()` stops or restarts the station; `next()` and `previous()` go to the following or preceding favourite in server order and do nothing when there are fewer than two favourites; `seek` is ignored. The rules in S2.6 "What live mode switches off" and "Queue" are applied here. The last station id is kept in `UserDefaults` (`discair.radio.lastStation`) for the Home card.
4. **Row click** on the Radio page plays the station; the playing row gets the `accentTint` ground. The On Air panel shows the logo, LIVE, the station and the time since tuning in, with Stop. The song appears in S2-3.
5. **Bar:** a live branch in `CupertinoPlayerBar`, from mockup B2: logo, station name, LIVE badge, elapsed time since tuning in, previous station, stop, next station, the star, the level meter behind. Hidden in live mode: shuffle, repeat, the lyric and fact line and their switches, the quality tag, the waveform, the progress line. Fallback hairline per S2.6.
6. **`SystemMedia`:** while live, title is the station name, `MPNowPlayingInfoPropertyIsLiveStream` is true, no duration and no position, the picture is the logo at 512; the seek command is disabled and enabled again when a library song plays.
7. **Mini player:** LIVE badge, station name, a stop button, no "next" line. **Widget:** `NowPlayingSnapshot` gains an optional `isLive` (old snapshots still decode); the widget draws LIVE where the progress bar is.
8. **Tests to run:** `--filter "LiveSessionTests|PlayerModelTests|SystemMediaTests|MiniPlayerTests"` with the fake output: start, stop, toggle, next and previous over favourites, the queue untouched, nothing persisted, seek disabled. Build the bundle (widget changed).
9. **Not verifiable by tests:** that sound plays and the meter moves. Say so; the owner listens.

#### S2-3 · The live song: Now Playing (C1), Download, Heard, Home (E7)

1. **Live song:** the 5 s `/now` poll fills the bar, the On Air panel, the mini player, the widget and `SystemMedia` (title, artist; album is the station name; the cover from `cover_url` through the owned-artwork route when set, else the logo). The state sentences of contract section 6 replace the artist line when there is no song (mockup "The Download button and the honest states").
2. **Download:** one `DownloadButton` view for the bar, the On Air panel, Now Playing and Heard rows, driven by `DownloadState` (S2.7). A click sends `POST /api/radio/plays/{id}/get`; the result sentence from the server is shown beside the button and kept on the row; a refusal gives "Try again". After success the Heard list is reloaded.
3. **Now Playing:** a live branch in `CupertinoNowPlaying` from mockup C1: cover or logo 230 pt, LIVE and elapsed, title, artist, Download, Favourite, Sleep (the Sleep button appears with S2-4); right column "Heard on (station) tonight": this station's plays of the last 12 hours, newest first, at most 8, each with its button, and the line "Download appears once a song has been heard for about 30 seconds."
4. **Heard:** the On Air panel lists the last three plays of the playing station and "All heard songs ›", which switches the Radio page to a Heard tab (a segmented control Stations | Heard in the page header): every play, grouped by day, with station, time and the button. Empty text: "Songs you hear for 30 seconds on a relayed station are listed here."
5. **Home rows:** the existing heard rows keep their filter, and after a click the row shows Downloading, then Downloaded, instead of vanishing before the next reload.
6. **Home card (E7):** from the "Small pieces" mockup, in Home's first row: while a station plays, cover or logo, LIVE, song or state sentence, station, Stop and Open Radio; when none plays and a last station is known and still in the list, its logo, name, "Last played …" and Resume; otherwise no card.
7. **Tests to run:** `--filter "DownloadStateTests|StationsModelTests|HomeDashboardTests|HomeRenderTests"`: every row of the state table, the 12-hour and 8-row limits, the card's three cases, the Home row after a click.

#### S2-4 · Reconnect, sleep timer, Settings, station shortcuts (E1)

1. **Reconnect** (`ReconnectPolicy` in `DiscairAudio`, pure): after a drop, an error status, or 20 s without sound, try again after 2, 5, 10, 20 and 30 s; sound resets the count; after the fifth failure the state is unreachable: "Station unreachable" with Retry in the bar, the On Air panel, the mini player and the menu bar popover. Nothing is tried after the owner pressed stop. While the Mac sleeps nothing is tried; on wake, one fresh round if a station was playing. While reconnecting the bar says "Connection lost · trying again in 5 s (attempt 2 of 5)".
2. **Sleep timer** (`SleepTimer` in `DiscairUI/Model`, generic as on Android): Off, 15, 30, 45, 60, 90 minutes; on expiry a station stops and a library song pauses; cancelled when playback stops. Reached from the moon in the bar (menu from the "Small pieces" mockup), the Sleep button on Now Playing and a Controls menu submenu. While it runs the moon shows the minutes left and is read as "Sleep timer, 45 minutes left".
3. **Settings, new Radio tab:** the scrobbling switch (disabled with "Last.fm is not set up on the server" when `configured` is false); a station list with Change (an open panel for images up to 2 MB) and Reset for each logo; the app address read only with the line "Changed on the web Radio page"; and, from S2-5, the menu bar switches.
4. **Station shortcuts (E1):** Controls › Stations lists the first nine favourites with ⌘1 to ⌘9 (no other command uses these keys today) and "Stop Radio". They work from any screen.
5. **Tests to run:** `--filter "ReconnectPolicyTests|SleepTimerTests|StationRulesTests"`: the delay sequence, reset on sound, none after stop, expiry for both kinds of playback, the first-nine rule.

#### S2-5 · Menu bar item (D2)

1. A `MenuBarExtra` scene with the window style in `DiscairApp.swift`. Label: the `radio` symbol while a station plays, a note symbol for a library song, plus the title cut at 30 characters when "Show title" is on.
2. Popover from mockup D: cover or logo, LIVE and station (or artist and album), title; Stop or Play/Pause, Next for library songs, Download with the same `DownloadButton`, the sleep timer; the first four favourites with their shortcuts; "Open Discair".
3. Settings › Radio: "Show in menu bar" (on by default) and "Show title in menu bar" (on by default), kept in `UserDefaults`.
4. It reads `AppState` only; no new requests of its own.
5. **Tests to run:** a pure `MenuBarContent` rule test (label text and cut, which buttons show for radio and for a library song). Build the bundle. Not verifiable by tests: the item in the real menu bar.

### S2.9 Accessibility and honesty rules for every slice

- Every control has a spoken label and a keyboard path; the station list moves with the arrow keys, Return plays, Space toggles play, ⌘-click is never the only way to anything.
- States are sentences. LIVE is a word. The star says on or off.
- Reduce Motion: no meter, no animated transitions. Increase Contrast and Reduce Transparency: check the On Air panel and the bar.
- No address, token or password in any text, log or error.
- Text never shrinks below `CU.Font.caption`; long titles end in an ellipsis in rows and scroll in the bar as song titles do today.

### S2.10 Owner checks after stage 2 (live)

- A relayed station plays on the Mac over Tailscale and on the home network; the logo appears; the meter moves.
- The live title changes with the song in the bar, the On Air panel, Control Centre and the menu bar.
- Download enables after about 30 seconds; the song reaches the library; the row turns to Downloaded, later Owned.
- A station without titles plays with its sentence and no button; an unreachable station says so and Retry works.
- Media keys: play/pause stops and restarts; next and previous change the favourite station.
- The sleep timer stops the station; ⌘1 to ⌘9 tune; tags edited on the Mac appear on the phone.
- Pulling the network cable shows the reconnect line, and the station comes back by itself.

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
