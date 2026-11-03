# Prompt to start macOS phase M1

Paste everything below the line into a new Claude Code session, in the folder that holds the `navi-librarian` repo. Start it only when ready: M1 is gated on the owner's word (`ACTIVE_WORK.md` 2j).

---

Read `handoff.md`, then `docs/ACTIVE_WORK.md` (section 2j), `docs/DEVELOPMENT_WORKFLOW.md`, `docs/MACOS_CLIENT_CONTRACT.md` (all of it) and decision D-025. GitHub `main` is the source of truth. Check current code, open PRs and CI first. Refer to the person directing the project only as "the owner".

**Task: phase M1 of the macOS client, as defined in the contract (section 9).** Build the Swift package skeleton in `macos/`, with unit tests, and nothing else. No UI beyond a minimal command-line or test harness, no audio, no themes (those are M2 and M4).

Scope:
1. `macos/` folder: a Swift Package (`Package.swift`, Swift 6, macOS 26, Apple Silicon) holding the logic modules, plus `macos/DESIGN.md` (skeleton: themes, window, accessibility rules from the contract) and a short `macos/README.md` (how to build and test).
2. **Profiles and reachability** (contract section 3): a profile has a name, a Librarian URL and a Navidrome URL; probe the LAN profile first, then Tailscale, with a manual override. Allow plain `http://` only for RFC 1918 addresses, `.local` names and `100.64.0.0/10`; block public HTTP. Distinct error kinds: no network, server unreachable, Tailscale not connected (detected from network interfaces, no Tailscale SDK), unauthorised, server error.
3. **Keychain storage** for the Navidrome login and the Librarian login (separate, never shared with other apps, never logged or printed).
4. **Navidrome client**: Subsonic token and salt authentication (fresh salt per request, password never sent), ping, and a read of the library (artists, albums, songs, cover art URLs) using the same endpoints and rules as `android/` (`docs/ANDROID_CLIENT_CONTRACT.md` section 4.2 and 5.1). One function builds stream URLs (`docs/ANDROID_PLAYER_CONTRACT.md` 3.1: id, optional `maxBitRate` and `format` from the allowlist only).
5. **Librarian client**: login and one read call (for example the daily picks), following `ANDROID_CLIENT_CONTRACT.md` 4.1 and 5.2. Use the existing API only; invent no endpoint or field.
6. **Two checks, recorded in the contract**: (a) whether Navidrome's playlist API can read and write playlists (needed for smart playlists), (b) whether the Librarian login rate limit is shared when requests arrive through `tailscale serve` (contract section 3, `ANDROID_CLIENT_CONTRACT.md` section 9). Run each against the owner's servers only if the owner supplies the addresses; otherwise describe exactly what to run and mark the result open.
7. **Tests**: unit tests for URL and profile rules, the http allowlist, token/salt generation, stream URL allowlist, error mapping, and payload decoding from fixtures (reuse `android/` fixtures where they exist). `swift test` must pass.
8. **CI**: a GitHub Actions job on a macOS runner, running only when `macos/**` changes, that runs `swift build` and `swift test`. Do not touch the existing workflows' behaviour.

Constraints:
- Xcode is not installed on the owner's Mac (contract O7); only the Command Line Tools with Swift 6.2. Everything in this scope must build and test with `swift build` and `swift test`. Do not create an Xcode project, SwiftUI views, Sparkle or screenshot tests.
- No new third-party dependency without asking the owner. No analytics. Credentials, tokens and salts never appear in logs, errors or test output.
- Follow the repo workflow: a branch, one PR, required CI green, no merge without the owner's approval. End commits with the attribution lines given by the session.
- Work independently and finish the whole scope in this turn. Where a decision is the owner's, pick the recommended option, say so, and list it in the PR.

Report at the end: what was built, the test results, the two checks (done or exactly what is left), anything you changed in the contract, and what M2 (the audio spike) needs from the owner.
