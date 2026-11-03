# Discair for Mac: logic package

Phase M1 of [`docs/MACOS_CLIENT_CONTRACT.md`](../docs/MACOS_CLIENT_CONTRACT.md) (decision D-025). A Swift package with the logic only: no UI, no audio, no themes. The app shell (Xcode project) starts in M4 and depends on these products.

Swift 6, macOS 26, Apple Silicon. No third-party dependencies.

| Product | Holds |
|---|---|
| `DiscairCore` | Address rules (https, or http only for RFC 1918, `.local`, 100.64.0.0/10), profiles and their JSON store, reachability and profile selection (LAN, then Tailscale, manual override), Tailscale detection from network interfaces, error kinds, Keychain store, HTTP transport |
| `DiscairNavidrome` | Subsonic token and salt auth, `ping`, library read (artists, albums, songs, cover art URLs), playlist calls, the one stream-URL builder |
| `DiscairLibrarian` | Login and the dashboard picks read |
| `discair-checks` | Command-line harness for the two server checks (contract section 11) |
| `discair-audio-spike` | M2 measurement tool, not shipped: `AVAudioEngine` decode, EQ, crossfade, gapless, device rates, SMB timings (contract section 12) |

## Build and test

Needs full Xcode 26 selected (`xcode-select -p` shows `/Applications/Xcode.app/...`).

```sh
cd macos
swift build
swift test
xcodebuild -scheme Discair-Package -destination 'platform=macOS' test   # same tests, through Xcode
```

Tests use no network. Client tests read the Android contract fixtures (`android/contract-fixtures/`), linked into the test targets as `Fixtures`. One test writes to the real macOS Keychain under a throw-away service name and removes it afterwards; set `DISCAIR_SKIP_KEYCHAIN_TESTS=1` on a machine without an unlocked login keychain.

## Server checks (the owner runs these)

Logins are read from environment variables and never printed.

```sh
export DISCAIR_NAVIDROME_URL=...  DISCAIR_NAVIDROME_USER=...  DISCAIR_NAVIDROME_PASSWORD=...
swift run discair-checks playlists            # read only
swift run discair-checks playlists --write    # also create, update and delete a playlist "discair-m1-check"

export DISCAIR_LIBRARIAN_URL=...
swift run discair-checks ratelimit --yes      # sends wrong logins until 429; locks that address out for 15 minutes
```

What the results mean and how to record them: contract section 11.

## Audio spike (M2)

```sh
swift build -c release --product discair-audio-spike
.build/release/discair-audio-spike offline        # EQ, crossfade, gapless, device rates: silent, needs nothing
.build/release/discair-audio-spike device --switch  # tries a rate change on the default output and restores it
# with DISCAIR_NAVIDROME_* set: samples | formats <id>... | gap <id> <id> | partial <id>... | find <text> [--songs]
# listen <id> <id> [--crossfade S] PLAYS SOUND: end of one song into the next, to listen for gaps
# scripts/spike.sh <command...> runs any of these with the login read from ~/Desktop/disqair/config.env
.build/release/discair-audio-spike smb "<path under /Volumes/media/library/music>"
```

Results and what they mean: contract section 12. The offline tests make no sound.

## Rules for contributors

- Credentials, tokens and salts never appear in logs, errors, test output or URLs that are printed. `Credential` prints as redacted; Subsonic URLs are secrets (use `redactSecrets` if one must appear in text).
- No endpoint or field is invented; DTOs follow the fixtures.
- No analytics, no new dependency without the owner's approval.
