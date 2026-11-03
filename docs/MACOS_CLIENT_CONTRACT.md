# macOS client contract (Discair)

Status: **draft, pending owner approval. Nothing is built.** Written from the owner's answers of 2026-11-03 (sections 1 to 40 of the grilling). Mockups come after this contract is approved (section 9).

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

Launch set: **one Neobrut and one macOS theme** (owner's choice per theme when mockups are reviewed).

Neobrut candidates (all radically different layouts; absolute variety is the goal): **Sheet Stack**, **Cassette Deck**, **Sticker Wall** (from Android) and **Zine Spread** (from the web UI), redesigned for a desktop window, not copied.

macOS candidates: **Native Glass** (vibrancy, sidebar blur, system accent; the launch macOS theme), **Cupertino** (Music.app-style), **Hi-Fi Deck** (amp faceplate), **Liner Notes** (editorial serif), **Mini-Player Widget** (compact). Built after launch.

Rules: mockups are the spec and built element by element (no light re-skins); gestures are never the only path; Get, Save, Not for me stay reachable with text labels; list dropped elements in the PR; fonts are bundled from the repo plus system fonts (SF Pro, SF Mono, New York) where they look good; no third-party runtime asset requests. App and Dock icon get one variant per theme (logo variation designed later).

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
| M0 | This contract, `macos/DESIGN.md` skeleton, project layout | Owner approves PR |
| M1 | Package skeleton, profiles and reachability, Keychain, Navidrome auth, library read, Navidrome playlist API check, rate-limit check | Tests pass |
| M2 | Audio spike: `AVAudioEngine` decode of FLAC/MP3/Opus, EQ, crossfade, gapless, SMB waveform speed | Measured result recorded |
| M3 | **Mockups:** 5 themes, 6 screens each (Home, Album, Now Playing, Queue, Library, Artist) as an HTML artifact | **Owner picks themes** |
| M4 | Window shell, launch Neobrut theme and Native Glass, all screens | Screenshot tests; owner approves the UI on the Mac |
| M5 | Parity: Discover, Downloads, Settings, EQ, lyrics, scrobbling, cache, Sparkle | Tests |
| M6 | Desktop features (section 6), mini window, widget, notifications, command palette | Per-feature acceptance |
| M7 | Remaining themes, one at a time | Owner approves each |

Priorities when trade-offs appear (owner, 2026-11-03): the look, smooth browsing, getting new music.

## 10. Owner answers (2026-11-03) and remaining open items

- **Signing:** no Apple Developer account. Ad-hoc signed; Gatekeeper warnings on install and update are accepted. Sparkle updates are verified with Sparkle's own EdDSA key (a separate key, kept out of the repo), so updates stay authentic without notarization. Each first launch needs right-click > Open.
- **Widget:** Notification Center widget shows now playing only.
- **Mini window:** floating always-on-top; cover, transport, seek bar, peek at the next track.
- **Cache (optional, off by default):** audio, covers and metadata, capped at **2 GB** with least-recently-used eviction, a clear button and a size readout in Settings.
- **SMB:** music folder is `/Volumes/media/library/music`, mounted by hand today. The app mounts it itself: the share address is a setting, the SMB login is stored in the Keychain, and the app calls Apple's NetFS mount API at launch and when the profile changes (the same as Finder "Connect to Server", no extra tools). If the mount fails or the volume is absent, SMB features switch off silently and playback is unaffected. Remaining detail for M2: the Navidrome-path to `/Volumes/media/library/music` prefix mapping, which the spike confirms against real paths. Share address: `smb://192.168.1.87/media` (username and password login; the credentials go in the Keychain, never in the repo).
