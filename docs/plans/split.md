# Repository Split Plan: macOS & Android Clients

Move `macos/` and `android/` out of `abucalip/navi-librarian` into dedicated GitHub repositories using **Option 1 (`git filter-repo`)** to preserve full commit history for both clients.

## Assumptions & Guardrails

- **Clean runway:** All client PRs are merged into `navi-librarian` `main`; no branches need cross-repo rebasing.
- **Target repo names (confirmed):**
  - macOS: `abucalip/discair-macos`
  - Android: `abucalip/discair-android`
  - Server + web client remains in `abucalip/navi-librarian`.
- **History preservation:** Run `git filter-repo --subdirectory-filter` only on disposable clones in `/tmp/`, never on `/Users/hamdibaala/Desktop/disqair/navi-librarian`.
- **Secrets safety:** `android/` has local untracked signing/config files (`discair-release.jks`, `keystore.properties`, `local.properties`). Cloning from `origin` (or `--no-local` from tracked refs only) ensures they are never committed. Keep them backed up locally and copy them manually into the new Android checkout after cloning.
- **Shared server contracts:** `SERVER_V2_CONTRACT.md`, `PLAYLIST_INBOX_CONTRACT.md`, `RADIO_PLAYBACK_CONTRACT.md`, and `SEARCH_CONTRACT.md` stay authoritative in `navi-librarian`. Client-only contracts move to their respective repos.

---

## Coupling Inventory

### macOS (7 test files)
- `Tests/DiscairUITests/GraphExplorerTests.swift` → `../../../intelligence/contract-fixtures/*.json`
- `Tests/DiscairUITests/CupertinoPagesRenderTests.swift` → `../../../intelligence/contract-fixtures/taste_context_contrast.json`
- `Tests/DiscairLibrarianTests/TasteClientTests.swift` → `../../../intelligence/contract-fixtures/*.json`
- `Tests/DiscairLibrarianTests/InsightCardsTests.swift` → `../../../intelligence/contract-fixtures/*.json`
- `Tests/DiscairLibrarianTests/SmartPlaylistsClientTests.swift` → `../../../intelligence/contract-fixtures/*.json`
- `Tests/DiscairLibrarianTests/FeedbackEventsTests.swift` → `../../../intelligence/contract-fixtures/*.json`
- `Tests/DiscairUITests/PlaylistInboxTests.swift` → `../../../tests/fixtures/listenbrainz_inbox_responses.json`

### Android (1 Gradle config + 5 test files)
- `app/build.gradle.kts` (line 61) → `resources.srcDir("../../intelligence/contract-fixtures")`
- `app/src/test/kotlin/app/discair/model/PlaylistInboxTest.kt` → `../../tests/fixtures/listenbrainz_inbox_responses.json`
- `app/src/test/kotlin/app/discair/ui/theme/GalleryTest.kt` → `../../docs/design/gallery/tokens.json`
- `app/src/test/kotlin/app/discair/ui/theme/GalleryMotionTest.kt` → `../../docs/design/gallery/tokens.json`
- `app/src/test/kotlin/app/discair/ui/theme/IndexTest.kt` → `../../docs/design/index/tokens.json`
- `app/src/test/kotlin/app/discair/ui/theme/IndexMotionTest.kt` → `../../docs/design/index/tokens.json`

### Docs, Contracts & Scripts
- **macOS-only:** `docs/contracts/MACOS_CLIENT_CONTRACT.md`, `scripts/perf/macos_cheap.sh`, macOS design specs under `docs/design/macos-*`.
- **Android-only:** `docs/contracts/ANDROID_CLIENT_CONTRACT.md`, `ANDROID_CROSSFADE_CONTRACT.md`, `ANDROID_EQ_CONTRACT.md`, `ANDROID_LYRICS_CONTRACT.md`, `ANDROID_PLAYER_CONTRACT.md`, `scripts/perf/android_cheap.sh`, Android design specs under `docs/design/` (`gallery/`, `index/`, `android-art-themes/`).
- **Monorepo docs to update:** `docs/ARCHITECTURE.md`, `docs/ACTIVE_WORK.md`, `docs/PROJECT_STATUS.md`, workspace `AGENTS.md` / `GEMINI.md` / `CLAUDE.md`.

---

## Implementation Slices

### Slice S0 — Pre-flight & Empty Repos
**Goal:** Lock the source SHA, verify `git-filter-repo` is installed, and create the two empty GitHub repositories.
- Sync `navi-librarian` `main` with `origin/main` and record the split anchor SHA (`SPLIT_SHA`).
- Install/verify `git-filter-repo` (`brew install git-filter-repo` if missing).
- Create empty GitHub repos (`abucalip/discair-macos` and `abucalip/discair-android`) with no initial commit, README, or license.
- **Done when:** Both empty remotes exist and `SPLIT_SHA` is recorded.

### Slice S1 — Extract & Decouple `discair-macos`
**Goal:** Push full macOS git history to `discair-macos` and make its build and tests 100% self-contained.
- Clone `navi-librarian` into `/tmp/discair-macos` and run:
  ```bash
  git filter-repo --subdirectory-filter macos
  ```
- Push `main` to `abucalip/discair-macos`.
- On a branch in `discair-macos`:
  1. Vendor the referenced JSON fixtures from `navi-librarian` at `SPLIT_SHA` into `Tests/Fixtures/contract-fixtures/` and `Tests/Fixtures/listenbrainz_inbox_responses.json`.
  2. Update the 7 Swift test files to resolve fixtures relative to the repo root (`Tests/Fixtures/...`) instead of `../../../`.
  3. Add a minimal `scripts/sync-fixtures.sh` (optional) noting the source paths in `navi-librarian`.
- **Verification:** Run focused `swift test --filter` across the 7 updated test suites; confirm `swift build` succeeds cleanly.

### Slice S2 — Extract & Decouple `discair-android`
**Goal:** Push full Android git history to `discair-android` and make its build and tests 100% self-contained.
- Clone `navi-librarian` into `/tmp/discair-android` and run:
  ```bash
  git filter-repo --subdirectory-filter android
  ```
- Verify `discair-release.jks`, `keystore.properties`, and `local.properties` are absent from git history and working tree.
- Push `main` to `abucalip/discair-android`.
- On a branch in `discair-android`:
  1. Vendor the referenced fixtures from `navi-librarian` at `SPLIT_SHA` into `contract-fixtures/intelligence/` (or `contract-fixtures/`), `contract-fixtures/listenbrainz_inbox_responses.json`, and `design-tokens/{gallery,index}/tokens.json`.
  2. Update `app/build.gradle.kts` (line 61) and the 5 Kotlin test files to point to the local vendored paths.
- **Verification:** Run focused Gradle unit tests (`JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew testDebugUnitTest --tests '...'`) for `PlaylistInboxTest`, `GalleryTest`, `GalleryMotionTest`, `IndexTest`, `IndexMotionTest`, and one intelligence-fixture consumer test.

### Slice S3 — Re-home Client Docs, Contracts & Agent Instructions
**Goal:** Give each new repo its own contracts, perf script, and lightweight agent rules.
- In `discair-macos`:
  - Copy `docs/contracts/MACOS_CLIENT_CONTRACT.md` → `docs/CONTRACT.md` (or `docs/contracts/`), `scripts/perf/macos_cheap.sh` → `scripts/perf/macos_cheap.sh`, and update relative links in `README.md` and `DESIGN.md`.
  - Add a concise `AGENTS.md` / `CLAUDE.md` (SwiftPM test rules, macOS motion/CPU rules, link to `navi-librarian` for shared API contracts).
- In `discair-android`:
  - Copy `docs/contracts/ANDROID_*_CONTRACT.md` → `docs/contracts/`, `scripts/perf/android_cheap.sh` → `scripts/perf/android_cheap.sh`, and update relative links in `README.md` and `contract-fixtures/README.md`.
  - Add a concise `AGENTS.md` / `CLAUDE.md` (JDK 17 + Gradle filtered test rules, link to `navi-librarian` for shared API contracts).
- **Verification:** Confirm no broken relative links to `../docs/` remain in either client `README.md` or `DESIGN.md`.

### Slice S4 — Trim `navi-librarian` Monorepo & Document New Client Locations
**Goal:** Remove `macos/` and `android/` from `navi-librarian` in a single clean PR once S1–S3 are merged and verified, and make it unmistakable where the clients now live for future feature work.
- Remove `macos/`, `android/`, `scripts/perf/macos_cheap.sh`, `scripts/perf/android_cheap.sh`, and the moved client-only contracts from `docs/contracts/`.
- Explicitly document in `navi-librarian` that the native clients moved to `abucalip/discair-macos` and `abucalip/discair-android` (so future feature development knows where to find them):
  - `docs/ARCHITECTURE.md` — replace client directory rows with explicit links to `abucalip/discair-macos` and `abucalip/discair-android`.
  - `AGENTS.md` and `PRODUCT.md` — note that native client work happens in `abucalip/discair-macos` and `abucalip/discair-android` while server/web and shared API contracts remain in `abucalip/navi-librarian`.
  - `docs/ACTIVE_WORK.md` and `docs/PROJECT_STATUS.md` — record the split and point open client items to their new repos.
- **Verification:** Run `python scripts/check_lint_changed.py --base origin/main` and confirm server/web tests are unaffected.

### Slice S5 — Local Workspace Setup & Closeout
**Goal:** Set up local checkouts and update workspace-level agent rules.
- Clone `discair-macos` and `discair-android` into `/Users/hamdibaala/Desktop/disqair/` alongside `navi-librarian`.
- Copy local untracked Android signing/config files (`discair-release.jks`, `keystore.properties`, `local.properties`) from the old backup into `/Users/hamdibaala/Desktop/disqair/discair-android/` and verify `git status` shows them ignored.
- Update `/Users/hamdibaala/Desktop/disqair/AGENTS.md` and `GEMINI.md` to reference all three repos.
- Delete temporary `/tmp/discair-macos` and `/tmp/discair-android` directories.
