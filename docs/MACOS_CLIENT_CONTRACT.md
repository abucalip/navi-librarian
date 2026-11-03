# macOS client contract (Discair)

Status: **approved by the owner and merged (PR [#713](https://github.com/abucalip/navi-librarian/pull/713), squash `8a3bab9706e49dcd485cb6c92073ee0285b1a4e7`, 2026-11-03). Phase M0 is done. M1 (Swift package skeleton, section 11) is merged (PR [#716](https://github.com/abucalip/navi-librarian/pull/716), squash `77e87484042a9db5c6987cb6b15f0f5b38e94d60`, 2026-11-03); M2 (audio spike) is approved by the owner and in progress.** Written from the owner's answers of 2026-11-03. Mockup rounds 1 and 2 are done (section 9); the launch themes are Cupertino and Zine Spread.

## 1. Purpose and scope

A native macOS app named **Discair** for the owner: a full Navidrome player and a Librarian discovery and acquisition client, reimagined for the desktop rather than ported from the web UI. It has **everything the Android app has** (Home, Library, Artist, Album, Search, Discover lists, Downloads, Settings, Now Playing, queue, gapless, crossfade, EQ, lyrics, scrobbling, quality cap, resume paused) plus the desktop features in section 6. Nothing on Android is left out.

Out of scope: App Store distribution, Intel Macs, macOS before 26, multi-user, internet radio, a terminal/TUI theme, a Mac Catalyst or web wrapper, technical audio analysis beyond a bitrate and format badge, tag-audit view, sleep timer, AirPlay picker, per-device EQ.

## 2. Decisions taken

| Topic | Decision |
|---|---|
| Repo and folder | `abucalip/navi-librarian`, folder `macos/`, own CI jobs filtered to `macos/**`. |
| Language, UI | Swift, SwiftUI (AppKit only where SwiftUI cannot do it, e.g. borderless window chrome, floating panel). |
| Structure | Swift Package for logic (network, auth, models, queue, audio, cache), thin Xcode project for the app shell. |
| Target | macOS 26, Apple Silicon only. |
| Distribution | Personal app, no App Store. Auto-update with Sparkle. Ad-hoc signed, no Developer account (section 10). |
| Audio | `AVAudioEngine` pipeline for maximum fidelity: native decode (FLAC, ALAC, MP3, AAC, Opus), 10-band EQ, true crossfade, gapless, output at the file's sample rate where the device supports it. Original file by default; optional bitrate cap. |
| Server access | Direct to Navidrome for library and `stream.view`; Librarian for recommendations, detail, acquisition. Same split as `ANDROID_CLIENT_CONTRACT.md` 5. |
| New endpoints | None invented. Gaps are written up as contract proposals; the owner has said missing data may be created as needed, each through a proposal. |
| Users | Single owner. |
| Credentials | macOS Keychain. Separate Navidrome and Librarian logins. Not shared with any other app. Never logged or shown (same as Android player contract 2). |
| Themes | Each theme owns its screens and window composition (D-022 spirit, round 2 and 3 rules). No round 1 inheritance. Each theme fixes its own light or dark. |
| Window | One window with panes, fully custom borderless chrome (own traffic lights, drag region, resize), plus one floating always-on-top mini player window. |

## 3. Network

- Profiles: a list, each with a Librarian URL and a Navidrome URL (for example Home `http://192.168.x.x:port`, Tailscale `https://<name>.ts.net`).
- Auto-select by reachability (LAN first, then Tailscale) with a manual override and a visible active-profile indicator.
- Plain `http://` is allowed only for RFC 1918 addresses, `.local` names and `100.64.0.0/10`. A visible "unencrypted" badge is shown. Public HTTP is blocked (App Transport Security local-networking exception only).
- Errors distinguish: no network, server unreachable, **Tailscale not connected** (detected from network interfaces; no Tailscale SDK), unauthorised, server error. Each has a retry action.
- Both servers are on the same host. The login rate limit under `tailscale serve` is verified in phase M1 and recorded.

## 4. Themes

Decided at mockup rounds 1 and 2 (2026-11-03). Mockups are the spec: `docs/design/macos-m3/mockups.html` (round 1) and `docs/design/macos-m4/mockups.html` (round 2, published as an artifact).

**Build order**
1. **Launch themes: Cupertino (macOS) and Zine Spread (Neobrut).**
2. **Later, documented here and not yet scheduled: Bento Block (Neobrut) and Native Glass v2 (macOS).**

| Theme | Kind | Decision | Build rule |
|---|---|---|---|
| **Cupertino** | macOS, light | Approved for launch. Change from the mockup: titles use a **bold sans-serif** (SF Pro Display), not a serif; the round 2 mockup is updated to match. | Follow the mockup; glass only on controls (sidebar, toolbar pieces, centre Now Playing display), opaque white content, red-pink accent, zebra tables, Up Next as a trailing inspector. |
| **Zine Spread** | Neobrut | Approved for launch ("very good"). | Follow the mockup closely and keep every detail: masthead, ticker, lead story, New this week, Classifieds, running order, A-Z index, magazine-cover artist page, centre-spread Now Playing, black player strip. |
| **Bento Block** | Neobrut | Approved, later ("very good"). | Follow the mockup details very closely: colour-block panels with one oversized corner on dotted paper, ink outlines and hard offset shadows, joined tabs, the permanent stream/ui player card in the right column, big circle play button with crescent shadow and coloured Prev / Next circles, square-thumb sliders, one-line timed lyric field, EQ as stacked bars, Pipeline strip on Home, ruled Ledger table in Library, overlapping avatars for similar artists. |
| **Native Glass v2** | macOS, dark | Approved, later ("very good"). Supersedes the round 1 Native Glass. | Follow the round 2 mockup: floating inset glass sidebar, glass toolbar pieces, one glass player capsule, opaque content layer, artwork flowing under the sidebar, trailing inspector (Pipeline, notes), tint only on the primary action. |

Not built for the Mac: Cassette Deck, Sheet Stack, Sticker Wall (rejected in round 1) and the round 1 Native Glass (replaced by v2). One idea from them is kept for every Neobrut theme: the **single timed lyric line field** on Now Playing (Bento Block has it; Zine's mockup is approved as is).

Remaining themes (Hi-Fi Deck, Liner Notes, Mini-Player Widget and others) are built later, one at a time.

Rules: mockups are the spec and built element by element (no light re-skins); gestures are never the only path; Get, Save, Not for me stay reachable with text labels; list dropped elements in the PR; fonts are bundled from the repo plus system fonts (SF Pro, SF Mono, New York) where they look good; no third-party runtime asset requests. App and Dock icon get one variant per theme (logo variation designed later). The theme system must be built so a later theme is added without changing screens (themes own their layouts behind a shared set of data and actions).

### 4.1 Apple design guidance applied to the macOS themes

Sources actually read: WWDC25 "Build an AppKit app with the new design" (session 310) and "Get to know the new design system" (session 356). Apple's Human Interface Guidelines pages are rendered by script and could not be read in full; the HIG pages for Toolbars, Sidebars, Materials and Layout still need a direct read before M4.

- Liquid Glass is for the functional layer that floats above content (sidebar, toolbar, player, sheets), never for content itself. No glass behind content as a sibling, no glass on glass.
- Sidebars are inset, floating glass; content extends edge to edge and flows under them (background extension), with text and controls layered above.
- Toolbars: group actions by function; search, segmented controls and pop-ups sit on their own glass; titles and status are not bordered like buttons; tint only for state or the primary action; symbols over text.
- Windows with toolbars use larger corner radii; nested shapes are concentric (inner radius = outer radius minus padding); large controls are capsules, small ones rounded rectangles.
- A scroll edge effect (hard variant on macOS) replaces hard dividers under floating bars; one effect per view.
- Hierarchy comes from layout and grouping, not extra backgrounds or borders; type is bold and left-aligned for key moments; do not hard-code control heights.
- Check legibility with Increase Contrast and Reduce Transparency.

## 5. Parity with Android

Queue (play next, add to queue, reorder), shuffle, repeat, gapless with next-track preload, crossfade (continuous albums stay gapless), 10-band EQ with presets and pre-gain, timed and plain lyrics, scrobbling toggle, streaming quality cap and transcoding, resume paused after restart, offline banner and cached pages, acquisition Get, progress, retry, dismiss, Undo and Never suggest, song-level Get, Settings for all services. Each Android contract (`ANDROID_PLAYER`, `CROSSFADE`, `EQ`, `LYRICS`) is the baseline; the macOS contract changes only what the engine requires.

## 6. Desktop features (approved by the owner)

1. **Library table:** sortable columns (year, rating, bitrate, format, added, plays, last played, missing MBID).
2. **Command palette (⌘K):** play, Get, jump to any screen or setting.
3. **Miller columns** (genre, artist, album, track inspector): opt-in view.
4. **Gap radar:** per-artist discography map with owned and missing albums and an inline Get.
5. **Pipeline dock:** acquisition progress in a persistent tray while listening.
6. **Listening history:** timeline and scrobble heatmap (Navidrome, Last.fm, ListenBrainz).
7. **Smart playlists:** rule builder, plus Navidrome playlist read and write (needs API check, M1).
8. **Queue workspace and Radio from this:** saved queues, drag reorder, similarity radio built on Librarian similarity (not internet radio).
9. **Album spread:** liner notes, credits, MusicBrainz data, reviews, similar artists.
10. **Bitrate and format badge** on tracks and Now Playing (nothing else technical).
11. **Finder integration:** reveal in Finder when the library is mounted.
12. **Waveform and quick tag reads over SMB** (section 7).
13. **Floating mini window** (always on top), **Notification Center widget**, **system notification when a Get finishes**, media keys, Now Playing in Control Center, Bluetooth, keyboard navigation and common hotkeys, drag and drop (drag a card to Queue or to Get, with a non-gesture path for each), local cache as an option.

## 7. Local library over SMB

- The app may read the music folder over SMB for fast tag reads and waveforms only. Never download whole files over HTTP for a waveform.
- Waveforms are produced only when the SMB file is reachable and the read is quick (time budget set in M2); otherwise the seek bar is plain. No waveform is invented.
- SMB use is optional, off when the share is unmounted, and never required for playback. Playback stays on `stream.view`.
- Mount point `/Volumes/media/library/music`; the app auto-mounts the share (section 10). Path mapping from Navidrome paths to the mount is a setting, confirmed in the M2 spike.

## 8. Testing and release

- Unit tests for logic (stream URL builder, profiles, queue persistence, crossfade rules, SMB path mapping).
- **Screenshot tests** per theme and key screen, run in GitHub Actions on macOS runners (the repo is public). Physical-device approval by the owner applies **only to UI design**; behaviour is verified by tests and the audio spike.
- Auto-update via Sparkle with an appcast published from GitHub Releases.
- Owner-only decisions stay gated: contract approval, then each phase.

## 9. Phases

| Phase | Content | Gate |
|---|---|---|
| M0 | This contract, `macos/DESIGN.md` skeleton, project layout | **Done**: owner approved, merged in PR #713 (the `macos/` folder and `DESIGN.md` are created in M1) |
| M1 | Package skeleton, profiles and reachability, Keychain, Navidrome auth, library read, Navidrome playlist API check, rate-limit check | Tests pass. **Done**: merged in PR #716, see section 11 (the two server checks are run in M2 with the owner's servers) |
| M2 | Audio spike: `AVAudioEngine` decode of FLAC/MP3/Opus, EQ, crossfade, gapless, SMB waveform speed | Measured result recorded |
| M3 | **Mockups:** done in two rounds (9 theme drawings, 6 screens each) | Owner picked: Cupertino and Zine first, Bento Block and Native Glass v2 later |
| M4 | Window shell, theme layer, Cupertino and Zine Spread, all screens | Screenshot tests; owner approves the UI on the Mac |
| M5 | Parity: Discover, Downloads, Settings, EQ, lyrics, scrobbling, cache, Sparkle | Tests |
| M6 | Desktop features (section 6), mini window, widget, notifications, command palette | Per-feature acceptance |
| M7 | Bento Block, Native Glass v2, then remaining themes, one at a time | Owner approves each |

Priorities when trade-offs appear (owner, 2026-11-03): the look, smooth browsing, getting new music.

## 10. Owner answers (2026-11-03) and remaining open items

- **Signing:** no Apple Developer account. Ad-hoc signed; Gatekeeper warnings on install and update are accepted. Sparkle updates are verified with Sparkle's own EdDSA key (a separate key, kept out of the repo), so updates stay authentic without notarization. Each first launch needs right-click > Open.
- **Widget:** Notification Center widget shows now playing only.
- **Mini window:** floating always-on-top; cover, transport, seek bar, peek at the next track.
- **Cache (optional, off by default):** audio, covers and metadata, capped at **2 GB** with least-recently-used eviction, a clear button and a size readout in Settings.
- **SMB:** music folder is `/Volumes/media/library/music`, mounted by hand today. The app mounts it itself: the share address is a setting, the SMB login is stored in the Keychain, and the app calls Apple's NetFS mount API at launch and when the profile changes (the same as Finder "Connect to Server", no extra tools). If the mount fails or the volume is absent, SMB features switch off silently and playback is unaffected. Remaining detail for M2: the Navidrome-path to `/Volumes/media/library/music` prefix mapping, which the spike confirms against real paths. Share address: `smb://192.168.1.87/media` (username and password login; the credentials go in the Keychain, never in the repo).
- **O7 Xcode (resolved 2026-11-03):** Xcode 26.6 (macOS SDK 26.5) is installed and active at `/Applications/Xcode.app` on the owner's Mac (the earlier note that only the Command Line Tools were present is out of date). The package builds and tests with `swift build`, `swift test` and `xcodebuild -scheme Discair-Package -destination 'platform=macOS' test`. The SwiftUI app shell, screenshot tests and Sparkle start in M4. CI uses GitHub's `macos-26` runner (Xcode 26.6 is its default).

## 11. M1 package and checks (2026-11-03)

Code: `macos/` (`README.md` there says how to build and test). Rules as decided by the owner in sections 3 and 10; where the contract left a detail open, M1 picked the recommended option, listed here:

- **Profiles** carry a `network` (LAN, Tailscale, other) that is inferred from the addresses and can be changed. Probe order is LAN, then Tailscale, then other; ties keep the owner's order. A profile counts as reachable only when both its Librarian and Navidrome addresses answer (any HTTP answer below 500, 3 s timeout, no redirects). A manual override skips probing. A Tailscale profile is not probed when no Tailscale interface is up.
- **Tailscale detection:** an up `utun` interface holding an address in 100.64.0.0/10 or `fd7a:115c:a1e0::/48`.
- **HTTP allowlist:** strict dotted-decimal IPv4 only (so `192.168.1.1.example.com`, octal and hex forms are names and are blocked over http); `localhost`, `127.0.0.1` and IPv6 over http are blocked because section 3 does not list them. Credentials inside a URL are refused.
- **Error kinds:** the five of section 3 plus `tooManyAttempts` for the Librarian's 429 (ANDROID_CLIENT_CONTRACT 4.1: shown, never retried automatically), and an address-rejected kind that has no retry.
- **Keychain:** one generic-password item per login (`app.discair.navidrome`, `app.discair.librarian`), this device only, no sync, no access group. `Credential` prints as redacted.
- **Subsonic auth:** token = md5(password + salt), fresh 16-hex-character salt per request URL; `u t s v=1.16.1 c=discair f=json`. Redirects are refused. One request timeout of 30 s (the separate 10 s connect timeout of the Android contract is not available in `URLSession`; the 3 s probe timeout covers reachability).
- **Stream URLs:** one builder; `id`, optional `maxBitRate` from 64, 96, 128, 192, 256, 320 and optional `format` of `mp3` or `opus`, written from the allowlist; song ids `[A-Za-z0-9_-]{1,128}`. The Android rule "https only" is widened to the section 3 transport rules for the Mac.
- **Librarian:** `GET /api/auth/status`, `POST /api/auth/login`, `GET /api/dashboard-picks?count=` (clamped 1 to 30). One re-login on a 401, then the error is reported. The session cookie is kept in memory only; persisting it is left to M5.
- **Not done in M1 (by scope):** the library cache, `getGenres` and `search3` reads, the other Librarian reads, SSE, and cookie persistence.

### 11.1 Check (a): Navidrome playlist API (needed for smart playlists)

**Status: open, needs the owner's Navidrome address.** The package implements `getPlaylists`, `getPlaylist`, `createPlaylist`, `updatePlaylist` (add songs) and `deletePlaylist` against the Subsonic 1.16.1 specification, and unit tests cover them with spec-shaped payloads. No playlist call was captured from the owner's Navidrome (`android/contract-fixtures/navidrome/` has none), so whether this server accepts them is not yet known. To run it:

```sh
cd macos
export DISCAIR_NAVIDROME_URL=<address>  DISCAIR_NAVIDROME_USER=<user>  DISCAIR_NAVIDROME_PASSWORD=<password>
swift run discair-checks playlists --write
```

It reads the playlist list, creates `discair-m1-check` with one song, reads it back, adds the song again, deletes the playlist and confirms it is gone. Pass means smart playlists can be saved to Navidrome; any FAIL line names the failing call. Record the result here with the Navidrome version. Not yet checked: removing or reordering songs (`songIndexToRemove`), which smart playlists may need.

### 11.2 Check (b): is the Librarian login rate limit shared behind `tailscale serve`?

**Status: open, needs the owner's addresses and a second tailnet device.** What the code says: the limit is 8 attempts per 15 minutes per `request.client.host` (`app/api/auth.py`), held in memory. The container starts uvicorn without `--forwarded-allow-ips`, so it trusts `X-Forwarded-For` only from 127.0.0.1. If the proxy reaches the container through Docker's port mapping, every tailnet client probably shares one key (the bridge address). This is a hypothesis, not a result. To settle it:

1. From the Mac, through the `tailscale serve` address: `export DISCAIR_LIBRARIAN_URL=<tailscale address>; swift run discair-checks ratelimit --yes`. It sends wrong logins for the user `discair-m1-ratelimit-probe` and prints the attempt that gets a 429 (expected 9, after 8).
2. Straight away, from a second device on the tailnet (the phone's browser or the Android app), try one wrong login through the same address. **429 means the limit is shared**; a 401 means each client has its own.
3. Also try one wrong login from the LAN address on the home network: expected 401 in both cases, since that is a different client address.
4. Wait 15 minutes, or restart the Librarian container, to clear the lockout (the limit is in memory).

If shared: the owner's own web UI and the app lock each other out after 8 failures in 15 minutes. Any fix (trusting the proxy's forwarded address) is a backend contract proposal and needs the owner's approval; the app already shows the 429 message and does not retry.

### 11.3 What M2 (audio spike) needs from the owner

- Approval to start M2, and the two server checks of 11.1 and 11.2 run or deferred.
- The Navidrome address and login (in the Keychain through the app or the harness, never in the repo), so the spike streams real files.
- A few real song ids from the library: one FLAC (ideally high sample rate), one MP3, one Opus if any, and two consecutive tracks of a continuous album (for the gapless test).
- The SMB share (`smb://192.168.1.87/media`) reachable from the Mac with its login, and one Navidrome `path` value next to the matching file under `/Volumes/media/library/music`, to confirm the prefix mapping.
- The output device to judge by ear (built-in, headphones, DAC) and the owner's verdict on gapless and crossfade quality; automated tests cannot judge that.
- A decision on the waveform time budget (contract section 7): the spike proposes a value from measurements.
