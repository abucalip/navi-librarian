## 2026-11-27 — Android Index Graphite night palettes

- Branch `feat/index-graphite-palettes`, based on GitHub `main` at `780f20d5`, implements the owner's eight approved Graphite variants: Blue, Cyan, Mint, Lime, Yellow, Violet, Pink and Coral. Shared neutral/status roles, the light mini-player strip, existing light palettes and Graphite Orange's default position are preserved. Canonical tokens and generated CSS include every variant; the design generator derives its palette frame count from the tokens.
- Focused `IndexTest` coverage now includes all 12 palettes, tone lookups, picker order, Appearance ID sanitization/resolution, inherited neutrals/status colours and derived accents. `PaletteTest` expects 62 registered palettes with unique IDs. Appearance uses the existing SharedPreferences path; no persistence format changes.
- `python3 docs/design/index/_src/check_contrast.py` passed all 459 colour-pair checks across 12 palettes. Generated CSS and palette-frame counts were checked against the tokens; `git diff --check` passed.
- Attempted JDK 17 `./gradlew --offline testDebugUnitTest --tests 'app.discair.ui.theme.IndexTest' --tests 'app.discair.ui.theme.PaletteTest' assembleDebug`: blocked before tests by sandbox denial writing the default Gradle wrapper lock. Retrying the installed Gradle with a writable temporary cache reached daemon startup but was blocked by `java.net.SocketException: Operation not permitted`. Neither Android tests nor the debug build completed. ADB also cannot bind its listener in this sandbox. Appearance/restart, Home, Now Playing, Queue and insight-block device checks, full suites and post-push CI were not run. GitHub CLI could not read initial PR/CI state because api.github.com was unreachable.
- Next action: review the PR, run the focused Android checks and inspect the eight palettes on a device. Nothing merged, published or deployed; the owner handles post-push CI.

## 2026-11-27 — macOS Playlist Inbox downloads (LB-16)

- Branch `feat/lb-16-macos-inbox-downloads` starts from GitHub `main` at `a1c94f30` (LB-15, PR #1284).
- Inbox rows request and retry by immutable edition and position, retain structured refusal messages, and use server-provided synthetic job keys for shared acquisition progress. Active/imported responses with `ok: false` do not offer Retry. Imported tracks enter playback only after refreshed ownership confirms them, preserving source order and repeats.
- `swift test --disable-sandbox --cache-path /private/tmp/discair-lb16-cache --manifest-cache none --jobs 6 --filter 'PlaylistInboxTests|PlaylistInboxDownloadTests|AcquisitionClientTests'` passed all 21 focused tests. The Clang and SwiftPM module caches were redirected to the same writable temporary directory. Initial attempts hit sandbox cache permissions and a corrected caption-font compile error.
- Reviewed Cupertino shelf, mixed, zero-owned, and download/refusal fixture renders (540-point edition width). `git diff --check` passed. Full suites, live Navidrome/Soulseek transfer, and installed-app keyboard/VoiceOver checks were not run. No provider calls, deployment, or publication. Next action: PR review and the live macOS download/import/scan check. Post-push CI belongs to the owner.

## 2026-11-25 — macOS Playlist Inbox playback (LB-15)

- Branch `feat/lb-15-macos-inbox-playback` starts from GitHub `main` at `525f08ff` (LB-14, PR #1283).
- Discover shows saved editions and their tracks. Play owned tracks starts the native queue in source order with shuffle off, preserves repeats, and leaves playback alone when ownership is zero or unknown.
- Nine focused Swift tests passed. The Cupertino shelf and the mixed and zero-owned edition renders were reviewed. A live Navidrome run remains unverified because the local sandbox denied the loopback bind.

## 2026-11-25 — Android Playlist Inbox downloads (LB-14)

- Branch `feat/lb-14-android-inbox-downloads` starts from GitHub `main` at `5de03f15` (LB-13, PR #1282).
- Edition rows request and retry by position, show structured refusals and shared acquisition progress, and refresh ownership before newly imported tracks can join playback.
- All 13 focused Android tests and the debug build passed. An Android 36 emulator with a disposable HTTPS fixture verified two rapid taps produced one request, a retry after no matches, 42% transfer progress, an unresolved-album refusal, and the ownership transition from two repeated owned occurrences to the ordered three-position queue. A live Navidrome and Soulseek transfer through Android remains unverified.

## 2026-11-25 — Android Playlist Inbox playback (LB-13)

- Branch `feat/lb-13-android-inbox` starts from GitHub `main` at `40a0ed51` (LB-12, PR #1281).
- Discover shows current Inbox editions and opens their ordered detail. Play owned tracks sends each owned occurrence to the native player. The Play control is disabled when there are no playable tracks.
- All three focused Android tests and the debug build passed. The Android 36 emulator used the shared Inbox responses over authenticated loopback HTTPS and streamed generated audio through a Subsonic fixture. The check covered the shelf, mixed detail, repeated queue entries, and preserving playback on a zero-owned edition. Physical-device and live-service checks remain open.

## 2026-11-25 — Listening Room Playlist Inbox downloads (LB-12)

- Branch `feat/lb-12-web-inbox-downloads` starts from GitHub `main` at `5d8d6953` (LB-11, PR #1280).
- The Inbox requests downloads by edition and track position, shows transfer progress and retry, and preserves saved job linkage for tracks whose album was resolved by the server. An imported track becomes owned when the library index confirms it.
- All 19 focused Inbox API and Listening Room shell tests passed. Isolated Chrome fixtures at 1440 px and 390 px covered keyboard activation, duplicate clicks, retry, progress after reload, unresolved metadata, the indexed ownership transition, and polling cleanup on navigation. The follow-up browser checklist on the CI-tested SHA remains open.

## 2026-11-25 — Listening Room Playlist Inbox browse (LB-11)

- Branch `feat/lb-11-web-inbox` starts from GitHub `main` at `fbd758a2` (LB-10, PR #1279).
- The Discover shelf and edition detail use the authenticated read API and display recorded Navidrome copy linkage for the selected edition and connection. Edition links preserve source track order and repeats.
- All 28 focused API, edition store, and Listening Room shell tests passed. Chrome fixtures covered the shelf and mixed and zero-owned editions at desktop and phone widths, with keyboard return to the shelf. The post-CI browser acceptance checklist remains open.

## 2026-11-25 — Schedule ListenBrainz Playlist Inbox import (LB-10)

- Branch `feat/lb-10-schedule-inbox` starts from GitHub `main` at `0f127acb` (LB-09, PR #1278).
- The discovery worker refreshes Created for Me and collaborative-filtering editions hourly, enriches each new CF page in one batch, and syncs private rolling copies. It checks Navidrome scans every five minutes and rechecks all linked copies after an hour even if the scan marker is unchanged.
- The owner verified the live disposable check with one Soulseek download for two requests, import and indexing, and an in-place update preserving the playlist ID, privacy, and order. All 42 focused scheduler, refresh, sync and ListenBrainz adapter tests passed. The full suite was not run.

## 2026-11-24 — ListenBrainz Inbox downloads (LB-09)

- Branch `feat/lb-09-inbox-download` starts from GitHub `main` at `42bbd175` (LB-08, PR #1277).
- Added the authenticated edition-position action. It verifies current ownership, resolves missing album metadata conservatively, and passes valid requests to the single-track acquisition service.
- Focused Inbox API, acquisition track, ListenBrainz client and MusicBrainz recording-album tests passed. The disposable fixture exercised one download, import, index update and private playlist reconciliation. The live Navidrome/slskd check remains in LB-10.

## 2026-11-24 — ListenBrainz managed-copy reconciliation (LB-08)

- Branch `feat/lb-08-reconcile-playlists` starts from GitHub `main` at `9f9606a8`.
- Reconciliation checks the scan marker before and after reading the song inventory, updates the existing private copy in source order, and records confirmed missing copies as unlinked while retaining their Inbox editions.
- All 24 focused playlist sync and edition repository tests passed. LB-10 registers the recurring job and verifies the import, scan, and reconcile flow on a disposable live playlist.

## 2026-11-24 — ListenBrainz rolling private copies (LB-07)

- Branch `feat/lb-07-rolling-playlists` starts from GitHub `main` at `076d1e72` (LB-06, PR #1275).
- Added one private rolling Navidrome copy per feed. Schema v8 records creation intent before the request, so a lost reply can recover the same copy. Uncertain creates remain pending until the matching copy appears.
- Fifty focused tests passed for sync, migration, store, and Navidrome transport. The sandbox denied loopback binding, leaving the TCP connection-reuse test and live Navidrome fault-injection check open.

## 2026-11-24 — ListenBrainz Playlist Inbox reads (LB-06)

- Branch `feat/lb-06-inbox-read` starts from GitHub `main` at `838eceb6` (LB-05, PR #1274).
- Added session-protected list and detail routes, a shared client contract, and response fixtures for guarded ownership and acquisition status, snapshot age, and empty and unconfigured states.
- Six focused HTTP tests passed. The migrated v4-to-v7 copy of the supplied test store passed the authenticated route smoke check with seeded editions, acquisition rows, and an owned-song index fixture. SQLite tracing recorded ten read-only statements. The original store stayed at v4. Live provider and installed-client verification were outside this check.

## 2026-11-24 — ListenBrainz playlist edition storage (LB-05)

- Branch `feat/lb-05-playlist-editions` starts from GitHub `main` at `23cbb776` (LB-04, PR #1273).
- Schema v7 stores ordered snapshots, a current edition per source, and a separate Navidrome link per recurring feed. Publication checks the edition observed before fetching, so a competing refresh cannot overwrite the winner.
- The playlist repository, migration, store, and capabilities fixture checks passed (44 tests and 85 subtests). The partial-refresh fixture kept the failed playlist's prior edition while publishing the successful detail. The tests used local fixtures.

---
Older entries rotated to [`docs/archive/PROJECT_LOG_2026-11.md`](docs/archive/PROJECT_LOG_2026-11.md) on 2026-11-27.
