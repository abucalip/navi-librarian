# macOS client contract (Discair)

Status: **approved by the owner and merged (PR [#713](https://github.com/abucalip/navi-librarian/pull/713), squash `8a3bab9706e49dcd485cb6c92073ee0285b1a4e7`, 2026-11-03). Phase M0 is done. M1 (Swift package skeleton, section 11) is merged (PR [#716](https://github.com/abucalip/navi-librarian/pull/716), squash `77e87484042a9db5c6987cb6b15f0f5b38e94d60`, 2026-11-03); M2 (audio spike, section 12) is merged (PR [#717](https://github.com/abucalip/navi-librarian/pull/717), squash `f4d01daafda2b581aa881ffe3d8400186074fe77`, 2026-11-03); M4 slice 1 (theme layer, window chrome and the six Cupertino screens) is merged (PR [#718](https://github.com/abucalip/navi-librarian/pull/718), squash `626494c7fdf48c7d1ae0b8cd5a5b15de3621d129`, 2026-11-03); M4 slice 2 (Zine Spread, six screens) is merged (PR [#719](https://github.com/abucalip/navi-librarian/pull/719), squash `7ea0bf87f59422d27488bf98cd906c4bac3f3fe2`, 2026-11-03); the owner approved the Zine look live and the review fixes are merged (PR [#720](https://github.com/abucalip/navi-librarian/pull/720), squash `561a6a83109532a10928a41428f507a296b795b9`); M5 slice 1a (session model and Settings) is merged (PR [#721](https://github.com/abucalip/navi-librarian/pull/721), squash `d47874d780f3df8bc1a36849fab2c4d5f81672f8`); slice 1b (live library data and artwork) is merged (PR [#722](https://github.com/abucalip/navi-librarian/pull/722), squash `2b8a1419637e042a0bce1d7e5de02dcaf6a24f63`); slice 2 (acquisition: Get, Save, Not for me) is next.** Written from the owner's answers of 2026-11-03. Mockup rounds 1 and 2 are done (section 9); the launch themes are Cupertino and Zine Spread.

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
- Both servers are on the same host. The login rate limit under `tailscale serve` was verified (2026-11-03, section 11.2): it is counted per tailnet device, not shared.

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

Sources actually read: WWDC25 "Build an AppKit app with the new design" (session 310) and "Get to know the new design system" (session 356). The HIG pages for Toolbars, Sidebars, Materials and Layout were read in full on 2026-11-03 (saved as PDFs by the owner); findings and the open differences from the mockups are in `macos/DESIGN.md`.

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
| M1 | Package skeleton, profiles and reachability, Keychain, Navidrome auth, library read, Navidrome playlist API check, rate-limit check | Tests pass. **Done**: merged in PR #716, see section 11 (both server checks are done: 11.1 passed, 11.2 not shared) |
| M2 | Audio spike: `AVAudioEngine` decode of FLAC/MP3/Opus, EQ, crossfade, gapless, SMB waveform speed | Measured result recorded: **done**, section 12 (gapless and crossfade confirmed by ear on headphones; DAC and Bluetooth not heard) |
| M3 | **Mockups:** done in two rounds (9 theme drawings, 6 screens each) | Owner picked: Cupertino and Zine first, Bento Block and Native Glass v2 later |
| M4 | Window shell, theme layer, Cupertino and Zine Spread, all screens | Screenshot tests; owner approves the UI on the Mac. **Slice 1 done** (theme layer, Cupertino, all six screens, owner-approved live, PR #718); **slice 2 done** (Zine Spread, six screens, PR #719 and review fixes #720, owner-approved live); baselines open |
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

**Done 2026-11-03: PASS.** Run by the agent with the owner's Navidrome login (read from the local `config.env`, never printed) through `discair-checks playlists --write`, over the owner's LAN address (plain http, allowed by the section 3 rules). `ping`, `getPlaylists` (37 playlists), `createPlaylist` with one song, `getPlaylist` read back (1 song), `updatePlaylist` adding a song (2 songs), `deletePlaylist`, and a final listing that no longer contained it all succeeded. The temporary playlist `discair-m1-check` was deleted by the check itself. So the login can read and write playlists, and smart playlists can be saved to Navidrome. Not checked: removing or reordering songs (`songIndexToRemove`), which smart playlists may need; to be tested when that feature is built (M6).

### 11.2 Check (b): is the Librarian login rate limit shared behind `tailscale serve`?

**Done 2026-11-03: NOT shared.** Run by the owner. From the Mac, through the `tailscale serve` address, `discair-checks ratelimit --yes` got 401 for 8 wrong logins and `429` on the 9th ("The server limit is reached after 8 attempts from this address"), matching the code (8 attempts per 15 minutes per client address, `app/api/auth.py`). Straight afterwards the owner's phone, through the same `tailscale serve` address, got "Invalid username or password" (401, not 429), and a wrong login from the Mac through the home-network address also got 401. So the Librarian sees a different client address per tailnet device, the lockout of one device does not reach another, and the app and the web UI cannot lock each other out. No backend change or proposal is needed. The hypothesis in the earlier draft (all tailnet clients share the proxy's address) was wrong. Not tested: two sessions from the same device (for example the app and a browser on the Mac share one address, so eight wrong logins in 15 minutes from either would lock both out; the app shows the 429 message and does not retry).

### 11.3 What M2 (audio spike) needed from the owner (all supplied; M2 is done, see section 12)

- Approval to start M2, and the two server checks of 11.1 and 11.2 run or deferred.
- The Navidrome address and login (in the Keychain through the app or the harness, never in the repo), so the spike streams real files.
- A few real song ids from the library: one FLAC (ideally high sample rate), one MP3, one Opus if any, and two consecutive tracks of a continuous album (for the gapless test).
- The SMB share (`smb://192.168.1.87/media`) reachable from the Mac with its login, and one Navidrome `path` value next to the matching file under `/Volumes/media/library/music`, to confirm the prefix mapping.
- The output device to judge by ear (built-in, headphones, DAC) and the owner's verdict on gapless and crossfade quality; automated tests cannot judge that.
- A decision on the waveform time budget (contract section 7): the spike proposes a value from measurements.

## 12. M2 audio spike: measured results (2026-11-03)

Tool: `discair-audio-spike` (`macos/Sources/AudioSpike`, build `swift build -c release --product discair-audio-spike`). Offline tests use `AVAudioEngine` manual rendering, so they are deterministic and play no sound. Library tests ran against the owner's Navidrome (LAN, plain http) and the mounted SMB share. Machine: MacBook Air, macOS 26.5 SDK, Xcode 26.6. **Not measured, because it needs the owner's ears or hardware:** any DAC or Bluetooth output. Gapless and crossfade were checked by ear by the owner on headphones (12.9).

### 12.1 Decoding (`AVAudioFile`, no third-party decoder)

| Source in the library | Result | Speed |
|---|---|---|
| FLAC (44.1 kHz, 1546 kbps) | decodes | 333x real time |
| M4A (256 kbps) | decodes | 773x |
| MP3 (320 kbps) | decodes | 392x |
| Ogg Opus (a Navidrome `format=opus` transcode) | decodes, always 48 kHz | 171 to 223x |
| Navidrome `format=mp3` transcode | decodes | 411 to 440x |
| **Ogg Vorbis** (found in the library) | **does not open** | |
| **WMA** (found in the library) | **does not open** | |

So Opus works natively on macOS 26 without a bundled decoder. Vorbis and WMA files must be played through the server's transcode (`format=opus` or `format=mp3`, both on the stream allowlist; `maxBitRate` up to 320). The library had 240 albums scanned: flac, m4a, mp3, ogg and wma occurred; no native `.opus` file was found. The app needs to know which suffixes it can play directly (flac, m4a, mp3, and others if found later: alac, wav, aiff) and use a transcode for the rest. The decision on the transcode quality for those two formats is the owner's (recommended: opus at 192 for ogg and wma sources, since transcoding is lossy either way).

### 12.2 Starting playback before the download ends

Whole-file download over the LAN: 52 MB FLAC took about 4 s (105 Mbit/s), a 9 MB MP3 or M4A under 1 s; first byte arrives in 10 to 120 ms. `AVAudioFile` reads a file only from disk, so playback needs either the whole file or a growing file. Tested on truncated copies:

| Format | Opens when truncated? |
|---|---|
| MP3 | yes, at 256 KiB; decodes exactly what has arrived |
| Ogg Opus | yes, at 256 KiB; decodes what has arrived |
| FLAC | no at 256 KiB (large header, embedded art); yes at 2 MiB (5 s decodable) |
| M4A | no, even at 2 MiB (the index is at the end of the file) |

Recommendation for M5: download to a temporary file; start playing a progressive format (MP3, Opus, FLAC) once about 3 s are decodable, by reading what exists and re-opening as the file grows; for M4A, wait for the whole file (about 1 s on the LAN). Preload the next track in full in the background. The growing-file reader itself is not built or proven end to end; only the truncated-file behaviour is measured.

### 12.3 10-band EQ (`AVAudioUnitEQ`, parametric, one-octave bands at 31, 62, 125, 250, 500, 1k, 2k, 4k, 8k, 16k Hz)

Measured on pure tones: +12 dB at 1 kHz gives +12.00 dB at 1 kHz and +0.08 and +0.10 dB at 100 Hz and 8 kHz; -12 dB at 62 Hz gives -12.00 dB; +12 dB at 16 kHz gives +12.00 dB; flat is 0.00 dB; `globalGain` of -6 gives -6.00 dB (pre-gain works); bypassed bands give 0.00 dB. Measured at 44.1 kHz only. The EQ behaves as specified, so the Android presets can be ported as they are (`ANDROID_EQ_CONTRACT.md`).

### 12.4 Crossfade

Two `AVAudioPlayerNode`s into the mixer, the second started sample-accurately with `play(at: AVAudioTime(sampleTime:...))`, gain changed every 10 ms. Equal-power curve (cos, sin): level through a 4 s fade stays within 0.00 dB of steady state. A linear curve dips 3.01 dB, as expected, so equal-power is the default. Difference from the ideal per-sample curve: -56 dB (the stepping), far below audibility; a render-thread gain ramp is not needed for the launch. Continuous albums stay gapless (section 5): no fade is applied between consecutive tracks of one album.

### 12.5 Gapless

One player node with the next file scheduled before the current one ends: a sine split at an arbitrary frame into two files joins with zero error for PCM and 6e-8 (24-bit rounding) for FLAC, with no inserted or dropped frames. Two real MP3 tracks of the library joined with zero sample error and the exact frame total; the engine adds no gap, so any gap heard is silence stored in the files (those two tracks had 1.9 s of it, which is normal for non-continuous tracks). Whether the decoder trims MP3 encoder delay was not measured separately. Continuous album, measured: *The Dark Side of the Moon* (MP3, 10 tracks). *Breathe In The Air* into *On The Run*, and *Brain Damage* into *Eclipse*, have 0.0 ms of stored silence at both ends of the join and joined with zero sample error and the exact frame total. The decoded lengths are not multiples of the MP3 frame size (1152), and there is no leading digital silence, which is consistent with the decoder trimming encoder padding (not proven by a separate test). The by-ear check is still the owner's (12.9).

### 12.6 Output sample rate

The default output (MacBook Air speakers) offers 44100, 48000, 88200 and 96000 Hz. Setting the device's nominal rate to 96 kHz was accepted and read back, and was restored to 44.1 kHz. So matching the device to the file rate is possible where the device offers it (Opus is always 48 kHz); `AVAudioEngine` resamples otherwise. The app must restore the rate on quit and tell the owner it changes the system output rate. Not tested with a DAC or Bluetooth.

### 12.7 SMB (`/Volumes/media/library/music`, already mounted by hand)

| File | Size | Tag-sized read (64 KiB) | Whole-file read | Decode + 1000 peaks |
|---|---|---|---|---|
| FLAC | 52 MB | 50 ms | 2.6 s (166 Mbit/s) | 0.8 s |
| MP3 | 9 MB | 46 ms | 0.3 s | 0.6 s |
| M4A | 10 MB | 50 ms | 0.3 s | 0.4 s |

Proposed budget (section 7): a tag read must finish within 150 ms (measured 50 ms); a waveform is computed in the background and shown only if ready within 5 s of the song starting (measured worst case 3.4 s for a 52 MB FLAC, under 1 s for the others), otherwise the seek bar stays plain, the work continues, and the result is cached per song (1000 peaks, about 2 KB). Never over HTTP.

**Path mapping: cause found, one setting left for the owner.** For 5 of 5 sampled songs, `/Volumes/media/library/music/<Subsonic path>` did not exist, although the folders are the same ones: Navidrome's Subsonic `path` was `AM (Jewel Case)/01-01 - Do I Wanna Know?.flac`, the file on the share is `AM (2013)/0101 Do I Wanna Know_.flac`. Navidrome's own API (`/api/song/<id>`, read-only, used once for this diagnosis only; the app does not use it) returns the real path, and all 5 real paths exist under the mount. So Navidrome stores the right path and the mount is right. By default Navidrome does not report real paths over the Subsonic API: its configuration option `Subsonic.DefaultReportRealPath` (`ND_SUBSONIC_DEFAULTREPORTREALPATH`) is `false` ("can be customized individually for each client/player", "this can be a security risk, so it is disabled by default", [navidrome.org configuration options](https://www.navidrome.org/docs/usage/configuration/options/)) and a rebuilt `Artist/Album/disc-track - Title.ext` name is returned instead. Every player registered in the owner's Navidrome currently has it off, including `discair [CFNetwork]` (created by the M1 and M2 tools).

**Resolved 2026-11-03.** The owner switched on "Report Real Path" for the player `discair [CFNetwork]` (the Mac tools' player; the real app will be a new player and needs the same switch once, or the server-wide default `ND_SUBSONIC_DEFAULTREPORTREALPATH=true`, which a community report says applies to newly registered players only). Navidrome then reports the path **as the Navidrome container sees it**, `/music/<Artist>/<Album>/<file>`, not the host path `/media/library/music` (the owner's first answer named the host path; the container mounts the same folder at `/music`). The app's path-mapping setting is therefore the pair **server root `/music` to local root `/Volumes/media/library/music`**, and the owner must be able to edit the server root. Verified with `scripts/spike.sh mapcheck 80`: 540 of 540 songs from 80 random albums resolved to an existing file on the mounted share (100 %). Until the switch is on for the app's player, Navidrome returns the rebuilt name that matches no file: the app must detect that (a path that does not start with the server root) and keep SMB features off with a one-line hint, not guess.

### 12.8 Owner decisions

1. **Path mapping: done.** Navidrome's music folder is the same folder as the share (`/media/library/music` on the host, `/music` inside the container). Cause, switch and verification: 12.7.
2. **Transcode for Ogg Vorbis and WMA sources: opus at 192** (the recommendation, accepted by the owner).
3. **Check 11.2 (rate limit): done by the owner, not shared** (11.2).
4. **By-ear gapless check:** see 12.9.

### 12.9 Listening session (the owner, about 10 minutes)

`discair-audio-spike listen` plays sound on the Mac's current output (default volume 0.5; lower it first). From `macos/`, with `scripts/spike.sh` (it reads the Navidrome login from `~/Desktop/disqair/config.env`, or the file named in `DISCAIR_ENV_FILE`):

```sh
# 1. gapless: the last 20 s of Breathe, then On The Run (a seamless segue on the record)
./scripts/spike.sh listen 5NvmJiy1uTG8HkoUAMaEEB 0moCUUrucnJAPO74LkcFL8
# 2. gapless: Brain Damage into Eclipse
./scripts/spike.sh listen 2KKthn7KKdaFJEiaOT78dn 4CYrvCn4U3Wy98uP1gxih7
# 3. crossfade 4 s, equal-power, between two songs: Money into Us And Them
./scripts/spike.sh listen 40DXYbfXU5PJQda4si36jN 4oyxwB1jkJBihafgXlTETd --crossfade 4
```

Listen for: any click, pop or dropout at the join in 1 and 2 (there should be none; the join was measured as exact); in 3, whether the fade is smooth and whether the level dips or bumps in the middle. Also repeat 1 with another output (headphones, a DAC, Bluetooth) if available, and say which one was used. Add `--volume 0.3` for quieter, `--tail 40` to hear more of the first song. Report: "1 clean / click", "2 clean / click", "3 smooth / bumpy", and the output used.

**Result (owner, 2026-11-03), on good headphones:** 1 clean, 2 clean (no click or gap at either gapless join), 3 smooth (the 4 s equal-power crossfade had no audible bump). This confirms the measurements of 12.4 and 12.5 by ear for the built-in decoder, `AVAudioPlayerNode` queueing and the timer-driven gain ramp. Not yet heard: a DAC or Bluetooth output, and the Opus or MP3 transcode path.
