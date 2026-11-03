# macOS client contract (Discair)

Status: **approved by the owner and merged (PR [#713](https://github.com/abucalip/navi-librarian/pull/713), squash `8a3bab9706e49dcd485cb6c92073ee0285b1a4e7`, 2026-11-03). Phase M0 is done. Nothing is built; M1 is next, to start only when the owner asks.** Written from the owner's answers of 2026-11-03. Mockup rounds 1 and 2 are done (section 9); the launch themes are Cupertino and Zine Spread.

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
| M1 | Package skeleton, profiles and reachability, Keychain, Navidrome auth, library read, Navidrome playlist API check, rate-limit check | Tests pass |
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
- **O7 Xcode is not installed on the owner's Mac (checked 2026-11-03).** Only the Command Line Tools with Swift 6.2 are present. M1's Swift package (logic and unit tests) builds and tests with `swift build` and `swift test` alone. The SwiftUI app shell, screenshot tests and Sparkle need full Xcode (free from the App Store, large download, macOS 26 SDK). Needed before M4, and for M1 only if the app shell is started there; the owner installs it, then runs `sudo xcode-select -s /Applications/Xcode.app`. CI uses GitHub's macOS runners, which include Xcode.
