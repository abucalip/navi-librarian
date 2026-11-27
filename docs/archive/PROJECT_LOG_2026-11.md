
## 2026-11-24 — ListenBrainz untagged track matching (LB-03)

- Branch `feat/lb-03-untagged-track-matching` starts from GitHub `main` at `1bdd7263` (LB-02, PR #1271).
- The matcher keeps exact recording ID priority and requires a unique artist/title candidate with agreeing release title or duration evidence for fallback. Conflicting IDs and competing versions are ambiguous.
- The focused matcher and JSPF parser tests passed (46 tests), and both changed modules compiled. The read-only Navidrome probe could not connect, so fallback accuracy on the owner's library remains unverified.

## 2026-11-24 — Web sidebar Docker updates

- Branch `web/docker-update-badge` starts from GitHub `main` at `a630e923`.
- The desktop sidebar badge shows when the published GHCR image is newer. An opt-in host process accepts a confirmed digest from the signed-in owner's web session, pins both Compose services to that digest and waits for health checks.
- Five focused pytest tests passed. The Unix socket integration test was skipped because the sandbox denied binding. JavaScript syntax and the isolated badge, confirmation and reload flow passed. The full suite, browser checklist and live Docker rollout were not run. No image was published or deployed.

## 2026-11-24 — macOS radio, sidebar and search

- Branch `macos/playback-navigation-search` starts from GitHub `main` at `383a4c01031182474d65b63cf81237b898113b6c`.
- The player bar, Now Playing and Radio's On Air panel link the current artist to their page. The album artist link now uses the same catalog fallback for artists outside the library.
- A chevron switches the sidebar between its regular and icon-only layouts. The follow-up shrinks the artwork to fit the icon column, so pages and the player bar use the recovered width. Expanding the sidebar restores the full artwork square.
- The Radio page uses the newer of the server timestamp and a local timestamp written after successful audio playback. An authenticated read returned timestamps for 4 of the 17 configured stations. The Mac can remember future playback when the server supplies no timestamp.
- Palette ranking and Library filtering run outside the main actor. Results from superseded queries are discarded.
- The focused macOS Swift run passed 160 tests. Native renders covered all three live artist links and compared the artwork area in both sidebar states. Live audio playback and installed-client typing latency remain unverified. The full suite was skipped.
- The artwork follow-up passed 21 focused Swift tests across six suites. The 1,100 × 700 pt radio render verified the compact artwork and the player bar's new position. A separate layout test verified album artwork dimensions in both states.

## 2026-11-24 — Listening Room Library (L10)

- Styled the Library browse controls, artist rows and thumbnail grid using the Listening Room tokens. The three shelves appear on Artists. Albums starts at Browse, matching its mockup.
- Reused owned-library search, sort preferences, cursor pagination and detail navigation. Added coverage for the shared toolbar and themed Load more label.
- `node --check static/app.js` and the focused Library, button-group and Listening Room shell contracts passed (62 tests, 48 subtests). Exact-head browser verification is pending CI.

## 2026-11-23 — Follow Apple Music artist-page redirects

- **Base and branch** — GitHub `main` at `a32dccd68defd7ac3e1cf58cfedd598edf7f32d9`, branch `fix/apple-artist-bio-redirect`.
- Apple Music returned a 301 for Portishead's ID-based URL. The metadata HTTP client left the redirect unfollowed, so the resolver went straight to Wikipedia. The redirect target contained the full artist biography.
- The Apple Music page request now follows redirects. The server cache key and web request URL use v4. The standalone endpoint gives fallback bios `Cache-Control: no-store`, and the web request cache releases them so later requests can see the server's refreshed result.
- **Verification** — 50 focused pytest tests passed across the Apple provider, HTTP cache, metadata cache semantics, persistent cache and web bio contract. A local FastAPI request backed by Apple's live public catalog returned Portishead's 1,106-character Apple Music bio with HTTP 200. Full suites, browser and native UI checks, deployment and production verification remain pending.

---

## 2026-11-23 — Listening Room Home lead and Daily picks (L3)

- **Base:** GitHub `main` at `be7a9d2ec53bd5313d39da24232919acf8b7267d`. Branch `web/listening-room-l3`.
- **Change:** render the lead, Up next and Daily picks in the opt-in Listening Room layout, with three reason sizes reading the server's `why` payload. Reuse album navigation, Get, bookmark, feedback and Undo actions. Sample lead covers in a 16×16 canvas, isolating the CORS probe for provider covers. Count unique sampled and fallback lead covers in each Home session for D4. The current server omits Genre spread, so the tab appears only when its endpoint is available.
- **Verification:** 132 focused pytest checks and 30 subtests passed, including all reason kinds, precedence and tint parity against the design reference. Isolated Chrome fixtures checked the responsive layout at 1440, 1080, 1079, 1024, 720, 719 and 390px, tab and action-menu keyboard navigation, safe Get, Skip/Undo, independent lens errors, and owned, CORS-enabled, CORS-blocked and missing covers. Two of four fixture covers used the fallback. The full application browser checklist and representative artwork measurement are pending.

---

## 2026-11-23 — Invalidate cached short artist biographies after Apple parser update

- **Base:** GitHub `main` at `90dbbaa259c93adfb85256c42f7b33428563b3d2` (PR #1249 merged); branch `fix/apple-artist-bio-cache-invalidation`.
- **Diagnosis:** PR #1247 improved the Apple Music parser, but `/api/artist-bio` continued reading persistent values from `artist-bio:v2`. Wikipedia answers cached by the previous parser therefore remained eligible for the full 24-hour cache lifetime and skipped the new Apple lookup.
- **Change:** use `artist-bio:v3`, leaving old stored rows intact but unreachable by the current resolver; add a test that seeds a short v2 Wikipedia result and verifies the new full Apple biography is fetched and stored under v3. The web client also uses `&v=3` to bypass its existing 24-hour HTTP cache entry. Update the test plan and status record.
- **Verification:** `tests/test_metadata_cache_semantics.py` passed (18 tests). All 45 test modules that read web assets passed (535 tests, 61 subtests) when run with a writable temporary `DISCAIR_DATA_DIR`; the initial run's auth integration test could not write to the managed worktree's default data directory. The first Docker packaging CI run failed because `tests/test_metadata_persistent_cache.py` still seeded `artist-bio:v2`; its fixture now uses v3, and the focused persistence module passed (10 tests). No post-push CI check, live provider request, UI check, deployment or runtime verification.

---

## 2026-11-23 — Extract the full Apple Music artist-page biography (merged, PR #1247)

- **Base:** GitHub `main` at `8bf6ca84c5b92e8ca49b8d1fdad884df8937f0a8` (PR #1246 merged); branch `fix/apple-music-full-artist-bio`.
- **Diagnosis:** the initial provider extracted only JSON-LD `description`, which is a short summary. Apple's public artist page also embeds its full About biography in the artist header's `bio` field inside `serialized-server-data`. Independent implementations corroborate the structure: the header item carries `contentDescriptor.kind = artist`, `contentDescriptor.identifiers.storeAdamID`, `title`, and `bio`.
- **Implementation:** parse the full page payload first; accept only the header item whose Apple artist ID matches the exact iTunes artist ID resolved by the provider. Keep JSON-LD as fallback, preserve line and paragraph breaks (including `<br>` markup), and request the canonical public `/artist/x/{id}` page. No developer token, new provider, or client change.
- **Regression coverage:** full bio beats JSON-LD summary; artist-ID match required; unrelated links and non-artist descriptors rejected; paragraph preservation and existing JSON-LD/fallback behavior retained.
- **PR:** [#1247](https://github.com/abucalip/navi-librarian/pull/1247) merged as `5442de6c56bd927a899f85736e6242aab6cf229e`.
- **Verification recorded in the PR:** focused tests were not run locally. No live Apple request from the implementation runtime, no manual UI check (no client changes), deployment or runtime verification.

---

## 2026-11-23 — Apple Music artist biographies become the primary source (PR #1246 merged)

- **Base and branch:** GitHub main at bba61f2f4bc9b09fbd747e813bdcde9fa2828743; fix/apple-music-artist-bios-default.
- **Verified code head:** f7941a2074aa4aac51a67cb91eb2c29d6444168f. PR [#1246](https://github.com/abucalip/navi-librarian/pull/1246) merged as `8bf6ca84c5b92e8ca49b8d1fdad884df8937f0a8`.
- **Diagnosis:** discovery/search/artist_sections.py::bio_job returned Navidrome's getArtistInfo2 biography immediately for owned artists. Independently, /api/artist-bio preloaded Navidrome text into memory before calling its Wikidata-validated Wikipedia resolver. The existing Apple Music integration covered album editorial notes, not artist biographies.
- **Provider:** Apple's public iTunes Search API resolves the artist ID; the corresponding Apple Music artist page exposes the full About biography in its `serialized-server-data` artist header; JSON-LD carries a shorter description. The Navidrome Apple Music Metadata Plugin uses the same public endpoints, but this implementation is standalone and needs neither that plugin, an Apple developer token nor Navidrome agent configuration. Exact normalized artist IDs and page names are required; ambiguous same-name IDs and generic Apple Music promotional descriptions are rejected.
- **Changes:** app/services/apple_artist_bio.py; shared resolver for /api/artist-bio and artist-page sections; priority Apple Music → identity-checked Wikipedia (Wikidata description fallback) → Navidrome; actual source provenance; cache versioning and separation of library/non-library contexts; short retries after external-provider failures; parser, identity, priority, cache and fallback regression tests; architecture, requirements, search contract and test-plan updates.
- **CI on f7941a2074aa4aac51a67cb91eb2c29d6444168f:** 4,439 passed, 2 skipped, 1 xfailed, 1,136 subtests passed. Python compile, changed-file lint, container runtime smoke, multi-architecture image validation, Docker packaging build and release-workflow validation passed. Release publishing was skipped by design. The first CI attempt exposed two test-only issues; both were corrected before the passing run.
- **Not performed:** no local focused test run, live Apple Music/Wikipedia request, manual UI test (no UI changed), merge, image publication, deployment or runtime verification.
- **Follow-up:** PR #1247 extracts the full artist-header biography from the public page; its verification status is recorded in the entry above.

## 2026-11-23 — Diagnose CritiqueBrainz album reviews; web MBID fix in progress

- **Base:** GitHub `main` at `ffb1528cbd4843292b621c85656aea899a11a9b7`; branch `fix/critiquebrainz-release-group-mbid`.
- **Diagnosis:** the album-page API emits `release_group_mbid` (from `discovery/search/album_page.py`). Web used nonexistent `album.mbid`, omitting the MBID so the server skipped CritiqueBrainz. macOS used Navidrome's `musicBrainzId`, which the repository documents as the release MBID rather than the release-group MBID. Android already reads `release_group_mbid` from the album-page DTO.
- **Album evidence:** Bitches Brew release group `a9e30282-5b37-3f92-b897-b9659a1a312b` has no CritiqueBrainz review; MusicBrainz says no one has reviewed it. Positive control: Tupelo Honey release group `c2c0e5e7-dc91-3e4e-b5bf-a26f06328926` has one CritiqueBrainz review by Chris Jones (4 positive, 0 negative votes).
- **Changes in PR #1245:** switch web to `album.release_group_mbid`; pass macOS `RelatedModel.releaseGroupMBID` into `AlbumSpreadModel` rather than deriving the review ID from Navidrome release metadata; add web source-contract and macOS request-level regression tests; correct the stale CB plan/project status.
- **PR:** [#1245](https://github.com/abucalip/navi-librarian/pull/1245), expanded cross-client head `4c1ab200ff22c711e79130623512b146e7e7b833` (open; not merged).
- **Verification on initial web-only head `2affb063ddeacc7d6be979604fff03d877997d3d`:** GitHub Actions passed `compile`, `lint-changed`, `container-smoke`, `test-and-build` (unit tests and Docker image build), `validate-container`, and `validate-release-workflow`; the tag-only `publish-release` job was skipped. The macOS changes were added after these runs; the Swift regression test and manual browser check have not been run. Full Python unit suite was run by CI, not by the agent.
- **Additional macOS correction:** `AlbumSpreadModel` now receives `RelatedModel.releaseGroupMBID` from `AppState.loadSelectedAlbum`; it no longer sends the Navidrome release MBID to CritiqueBrainz. A request-level Swift regression test was added, but not run locally.
- **Verification on expanded head:** GitHub Actions were triggered again for `4c1ab200ff22c711e79130623512b146e7e7b833`; results were pending at the time of this documentation update. No macOS Swift test or manual browser check has been run.
- **Not verified:** not merged, published, deployed or runtime-verified. **Next:** verify CI on the final PR head, run `swift test --filter DiscairUITests.AlbumSpreadTests` and the required manual browser check, then obtain owner review/merge.

---

## 2026-11-22 — FirstFM F5.2: drop temporary lastfm_* aliases and close out docs (PR pending)

- **Branch:** `feat/firstfm-f5-2-cleanup`, based on `main` at `0bfba05a` (FirstFM F5.1 merged, PR `#1237`).
- **Changes:**
  - `discovery/` & `recommendation/`: removed all temporary `lastfm_listeners`, `lastfm_playcount`, `lastfm_tags`, `lastfm_popularity_bonus`, and `apply_lastfm_popularity_bonus` aliases and fallback reads in `recommendation_payload.py`, `popularity.py`, `deep_dive_candidates.py`, `new_releases.py`, `lens_week.py`, `classics_candidates.py`, `classics_ratings.py`, `pick_why.py`, `recommendations.py`, `recommendation/replay.py`, `recommendation/diagnostics.py`, `recommendation/profile_comparison.py`, and `scripts/discovery_mode_sweep.py`.
  - **Clients:** removed transitional `lastfm_listeners` / `lastfm_playcount` fallback decoding in `static/app.js` and `android/app/src/main/kotlin/app/discair/model/{Discovery,Dto}.kt` (after confirming ListenBrainz `listeners` / `playcount` were already wired in F4.1/F4.2).
  - **Tests & Docs:** updated 16 Python test files and `android/app/src/test/kotlin/app/discair/FixtureParsingTest.kt`; updated `docs/ARCHITECTURE.md`, `PRODUCT.md`, `docs/ACTIVE_WORK.md`, `docs/PROJECT_STATUS.md`, and `PROJECT_LOG.md`. Verified zero remaining `ws.audioscrobbler.com` or `integrations.lastfm` references in production code.
- **Tests run:** focused `pytest` across all 18 affected test files (all passed) and `./gradlew testDebugUnitTest --tests 'app.discair.FixtureParsingTest'` (`BUILD SUCCESSFUL`). Full suites not run locally.
- **Not verified:** not published, deployed, or runtime-verified against a live server.

---

## 2026-11-22 — FirstFM F1.2: switch mbid_popularity and lens_pool_gatherer to ListenBrainz (PR #1225 merged)

- **Merged:** PR [#1225](https://github.com/abucalip/navi-librarian/pull/1225), squash commit `87fc2b40`, from exact PR head `7ab91bc4`; branch `feat/firstfm-f1-2-mbid-popularity-lb`, based on `main` at `ea63d22b`.
- **Changes:**
  - `discovery/mbid_popularity.py`: replaced Last.fm `artist.getInfo` / `album.getInfo` calls and the MusicBrainz release-search / ListenBrainz representative-release indirection with batched ListenBrainz `fetch_release_group_popularity` and `fetch_artist_popularity` (from F1.1). Kept `LASTFM_SPACING_SECONDS` temporarily while `discovery/artist_links.py` still imports it until F2.3.
  - `discovery/lens_pool_gatherer.py`: switched `resolve_popularity` to pass `providers.http_post` and removed `LENS_LASTFM_CALL_BUDGET`.
  - `tests/test_discovery_mbid_popularity.py` & `tests/test_discovery_lens_pool_gatherer.py`: updated offline unit tests to stub ListenBrainz batched popularity POSTs; removed obsolete `tests/test_discovery_release_years.py`.
- **Tests run:** focused run `.venv/bin/python -m pytest tests/test_discovery_mbid_popularity.py tests/test_discovery_lens_pool_gatherer.py` — 18 passed in 0.24 s on exact head `7ab91bc4`; `scripts/check_lint_changed.py --base origin/main` — 4 file(s) checked, 0 new finding group(s). Full unit suite not run locally.
- **Not verified:** not published, deployed or runtime-verified against a live server.
- **Next action:** start FirstFM F1.3 (switch Classics, Deep Dives, and New Releases popularity & top albums to ListenBrainz).

---

## 2026-11-22 — Listening Room web L1: foundations behind Appearance switch (PR #1222 merged)

- **Merged:** PR [#1222](https://github.com/abucalip/navi-librarian/pull/1222), squash commit `ab3e7663a35e76070039d54581275bbb32042289`, from exact PR head `585482d0dadfe718663b5e7395f657d134d85bf2`; branch `web/listening-room-l1`, based on `main` at `54e5e719`.
- **Changes:**
  - **Fonts:** copied `instrument-sans-600.woff2`, `instrument-sans-700.woff2`, and `LICENSE-instrument-sans.txt` (OFL 1.1) from `docs/design/listening-room/fonts/` into `static/fonts/`; declared both weights (`font-display: swap`) in `static/fonts/fonts.css`.
  - **Tokens:** copied `docs/design/listening-room/tokens.css` to `static/listening-room/tokens.css` with the four `@font-face` URLs updated to `../fonts/...`, keeping all `--lr-*` variables, reduced-motion overrides, and `.lr-type-*` classes identical to the package.
  - **Template and sprite:** linked `/static/listening-room/tokens.css` and inlined all 52 `#lr-*` `<symbol>` icons inside `<svg aria-hidden="true" style="display:none">` after the skip link in `app/templates/index.html`.
  - **Appearance switch:** added opt-in `listeningroom` (`label: 'Listening Room'`, `layout: 'listeningroom'`, `dark: true`, `bar: '#0c0d10'`; `DEFAULT` unchanged at `ink`) in `static/appearance.js`, added `:root[data-theme="listeningroom"]` in `static/themes.css`, and noted `static/listening-room/` in `docs/ARCHITECTURE.md`.
  - **Tests:** extended `tests/test_fonts_and_icons_ui_contract.py` (font count/budget/licence, `THEME_IDS`, `ListeningRoomFoundationTests`) and allowed `layout: 'listeningroom'` in `tests/test_tape_layout_ui_contract.py`.
- **Tests run:** focused run `.venv/bin/python -m pytest tests/test_tape_layout_ui_contract.py tests/test_fonts_and_icons_ui_contract.py` — 50 passed in 0.28 s on exact head `585482d0` (plus 81 passed across `test_fonts_and_icons_ui_contract.py`, `test_header_menu_ui_contract.py` and `test_zine_layout_ui_contract.py` on `e95ee227`, `node --check static/appearance.js`, and `scripts/check_lint_changed.py --base origin/main` with 0 new findings). Full unit suite not run locally.
- **CI on head `585482d0`:** `compile`, `container-smoke`, `lint-changed`, `test-and-build`, `validate-container`, and `validate-release-workflow` passed (`publish-release` skipped).
- **Not verified:** not checked in a live browser; not published, deployed or runtime-verified.
- **Next action:** start Listening Room slice L2 (shell: rail, icon rail, phone tab bar with More sheet, top bar with search and mode switch, skip link, focus ring).

---

## 2026-11-22 — Listening Room web L0: server audit, deep_dive_kind and pick_why builder (PR #1221 merged)

- **Merged:** PR [#1221](https://github.com/abucalip/navi-librarian/pull/1221), squash commit `c941c6a1f75a3a3de0f12563367976d75caff5e4`, from exact PR head `c6c7c74ccd64e277e8d67aac98b6b4f02dd7180a`; branch `web/listening-room-l0`, based on `main` at `b31b1165`.
- **Changes:**
  - **R7 vs R8:** added `deep_dive_kind` (`"missing_album"` / `"similar_artist"`) in `discovery/deep_dive_candidates.py` for missing-album, resolved-pool and similar-artist candidates.
  - **Pure `why` builder:** added `discovery/pick_why.py` (`build_pick_why`, `attach_why`) producing `why: {kind, sentence, chips: [{type, label, value, href_kind}]}` following `docs/plans/LISTENING_ROOM_WEB.md` section 6 precedence (`R1`–`R12`) and wording (assuming recommended D1 = server), never exposing internal R7 `reason` strings.
  - **Read-time attachment:** wired `why` into `discovery/list_payload.py` (`build_cached_discovery_list_response`, `build_lens_list_response`), `discovery/lens_week.py` (`to_pick`), and `app/api/discovery.py` (`/api/recommendations`), leaving `navidrome_server.py` untouched (D-016). Added the `discovery/pick_why.py` row in `docs/ARCHITECTURE.md`.
  - **Page-field audit (section 9.3):** confirmed `quality` on owned albums (`discovery/search/album_page.py`), `{source, quote, url}` on reviews (`app/services/album_reviews.py`), `owned`/`id` without `album_count` on similar artists (`discovery/search/similar.py`), and client-supplied `metadata` only on Saved (`for_me`).
- **Tests run:** focused run `.venv/bin/python -m pytest tests/test_discovery_pick_why.py tests/test_discovery_deep_dive_candidates.py tests/test_discovery_list_payload.py tests/test_lens_week.py tests/test_discovery_routes.py` — 50 passed in 0.78 s on exact head `c6c7c74c`. Full unit suite not run.
- **CI on head `c6c7c74c`:** `compile`, `container-smoke`, `lint-changed`, `test-and-build`, `validate-container` and `validate-release-workflow` passed (`publish-release` skipped).
- **Not verified:** not published, deployed or runtime-verified against a live server.
- **Next action:** start Listening Room slice L1 (foundations behind a switch: fonts, `tokens.css`, icon sprite in `index.html`, Appearance toggle).

---

## 2026-11-22 — macOS design details D8.1–D8.4, user-facing copy and player bar title width (PR #1218 merged)

- **Merged:** PR [#1218](https://github.com/abucalip/navi-librarian/pull/1218), squash commit `b2a434bb6abd8ece27d31a2277d07e6fa3f9d639`, from exact PR head `8bf8ede5cbb2e2afaa2aed490453021142894a85`; branch `macos/d8-user-facing-copy`, based on `main` at `409665c4` (D7.1–D7.4 docs closeout).
- **Changes:**
  - **D8.1:** added `GraphWording.sourceName(_:)`, `GraphWording.evidenceClass(_:explicitLabel:)` and `GraphWording.provenanceLine(source:evidenceClass:matchQuality:explicitLabel:)` (`GraphExplorer.swift`) as one shared display map and adopted it in `AtlasInspector` (`AtlasView.swift`, `"MusicBrainz · stated place · exact match"`), `TimelineInspector` (`TimelineView.swift`) and `GraphExplorerView` (`GraphExplorerView.swift`).
  - **D8.2:** mapped `destination_exists` in `AcquisitionModel.statusText(_:)` (`AcquisitionModel.swift`) to `"Already in your library folder; nothing was copied"` (along with plain-English strings for other known server statuses and a sentence-case fallback), kept `Dismiss` as the only action for `destination_exists`, and placed `destination_exists` / `download_complete_move_failed` on `.importing` in `HomeDashboard.stage(of:)` (`HomeDashboard.swift`).
  - **D8.3:** replaced developer wording in `GraphExplorerModel.truncatedNotice` (`GraphExplorer.swift`) with `"Showing the first N connections."` + `"Turn on Credits only, lower the reach, or use List to see them all."`, keeping the `Switch to List` button in `CupertinoConnections.swift`.
  - **D8.4:** replaced the fixed 290 pt title-block cap in `CupertinoPlayerBar` (`CupertinoPlayerBar.swift`) with `CappedWidthLayout` and `titleBlockMaxWidth(forBarWidth:)` (up to 40% of the bar width before truncating, hugging shorter titles), keeping the centre fact/lyric centred in the space left between the title block and the controls.
- **Tests run:** `select-tests.sh` selected `DiscairUITests` (`bundle=false`); `swift test --package-path navi-librarian/macos --disable-sandbox --filter 'D8UserFacingCopyTests|ConnectionsScreenModelTests|AcquisitionModelTests|PlayerBarRefinementTests|D7GraphMapLabelsTests'` — 60 tests in 5 suites passed (6.260 s) on exact head `8bf8ede5`. Day and Night offscreen renders of Atlas Inspector, Downloads (`destination_exists`), Connections (truncated notice) and Player Bar (`"Aretha Franklin — The Electrifying Aretha Franklin"`) were inspected. No full suite.
- **CI on head `8bf8ede5`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Not verified:** owner visual acceptance in a live window; no CPU measurement (no continuous or looping SwiftUI motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks D3, D5, D6, D7 and D8 in a live macOS window to close out the macOS design details polish pass.

---

## 2026-11-22 — macOS design details D7.1–D7.4, graph and map labels (PR #1217 merged)

- **Merged:** PR [#1217](https://github.com/abucalip/navi-librarian/pull/1217), squash commit `96ade9f3c9ecbd5f0f7f78898de7cadb9ff84c71`, from exact PR head `70a278c1deeaa7fc0a78486e31f0e72d185c73d2`; branch `macos/d7-graph-map-labels`, based on `main` at `19bb6a05` (D6.1–D6.4 merged in PR #1216).
- **Changes:**
  - **D7.1:** added `GraphLayout.sectorLabelAngles(_:)` (`GraphExplorer.swift`) to drop sector eyebrows with fewer than 2 step-1 nodes and place remaining sector labels in edge midpoint gaps; updated `CupertinoConnections.swift` and `GraphExplorerView.swift` so edges draw beneath nodes/labels and centre, node, and sector labels sit on a rounded `CU.content` 80% halo with 4 pt padding.
  - **D7.2:** replaced SwiftUI `Map` with `AtlasMapView` (`MKMapView` via `NSViewRepresentable` in `AtlasView.swift`) enabling native MapKit clustering (`clusteringIdentifier = "atlas-place"`, numbered `AtlasClusterView` badges that zoom to members on click) and `collisionMode = .circle`; added `AtlasGeometry.displayPriority(owned:recordings:selected:)`, `AtlasGeometry.clusterBadgeSize(count:)`, and pure `AtlasLabelLayout.place(_:in:)` (`AtlasModel.swift`) so lower-count labels hide first and visible labels stay inside the map's safe bounds.
  - **D7.3:** added `AtlasInspector.albumLine(for:)` (`AtlasView.swift`) and omitted the album `Text` when a recording has no linked albums (or only blank names).
  - **D7.4:** added optional `rowSpacing` and width clamping to `FlowLayout` (`CupertinoHome.swift`), and updated `AtlasView.footer` (`AtlasView.swift`) and `TimelineView.footer` (`TimelineView.swift`) to wrap legend clauses as one block with `"Showing the first … only."` on its own line.
- **Tests run:** `select-tests.sh` selected `DiscairUITests` (`bundle=false`); `swift test --package-path navi-librarian/macos --disable-sandbox --filter 'D7GraphMapLabelsTests|AtlasTests|GraphLayoutTests|GraphSectorTests|TimelineGroupingTests|TimelineModelTests|D4PageTitleEdgeTests|D57TrailingInspectorHeightTests'` — 38 tests in 10 suites passed (9.067 s) on exact head `70a278c1`. Day and Night offscreen renders of Connections, Atlas and Timeline were inspected. No full suite.
- **CI on head `70a278c1`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Not verified:** owner visual acceptance in a live window (including live MapKit clustering/tiles); no CPU measurement (no continuous or looping SwiftUI motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks D7.1–D7.4 in a live window; Slice D8 (user-facing copy) can start.

---

## 2026-11-22 — macOS design details D5.1–D5.9, columns in lists (PR #1215 merged)

- **Merged:** PR [#1215](https://github.com/abucalip/navi-librarian/pull/1215), squash commit `10e9e228cd5f22c36591d8d7927cc453b3df1f11`, from exact PR head `9a807380df6ad655fcc48f5aa9aff15f55685227`; branch `macos/d5-columns-in-lists`, based on `main` at `8fd63365` (D4.7–D4.8 docs closeout).
- **Changes:**
  - **D5.1:** fixed `CUStageTracker` column (`70` pt), stepper (`280` pt) and trailing action stack (`128` pt) widths in `CupertinoCharts.swift` and `CupertinoDownloads.swift`.
  - **D5.2:** added static 2 pt connectors (`CUChartMath.stageConnectors(step:)`, filled up to the current step) to `CUStageTracker` and hid the stepper on `.imported` rows so completed items keep only `"✓ In your library"`.
  - **D5.3:** replaced the `.containerRelativeFrame` half-width cap in `CupertinoDownloads.swift` with `maxListWidth = 1040` pt on both the `CUPanel` card and the `"Clear … imported"` action bar.
  - **D5.4:** reserved `playingSlotWidth` (`18` pt) and `actionSlotWidth` (`24` pt) slots on every queue row in `CupertinoQueue.swift` and aligned the Queue tab header count trailing edge with `headerCountTrailingInset` (`40` pt).
  - **D5.5:** exposed `CupertinoToolbar.height = 44` (`CupertinoTheme.swift`) and aligned `CupertinoQueueInspector`'s top band (`headerTop = CU.Shell.toolbarTop`) to the toolbar's centre line.
  - **D5.6:** aligned Timeline year and undated rail labels to `.firstTextBaseline` (`TimelineView.rowAlignment` in `TimelineView.swift`).
  - **D5.7:** extracted full-height glass `TimelineInspector` and `AtlasInspector` (`TimelineView.swift`, `AtlasView.swift`) into `CupertinoWindow`'s trailing slot (`trailingPanelWidth(for:)` in `CupertinoTheme.swift`) so the toolbar stops at the panel edge, with titles aligned to `CupertinoToolbar.centreY`.
  - **D5.8:** updated shared `StationLogo` (`StationLogoStore.swift`) to use `.scaledToFit()` with 3 pt padding on `CU.bgFill` for non-square logos (0 pt for square logos), and added synchronous `StationLogoStore.cached(station:size:)`.
  - **D5.9:** removed `minHeight: 120` from `OnAirPanel`'s empty state in `CupertinoStations.swift` and moved `"Add station"` into the Radio header toolbar row beside `Stations | Heard` on the Stations pane.
- **Tests run:** `select-tests.sh` selected `DiscairUITests` (`bundle=false`); `swift test --disable-sandbox --filter 'D51DownloadsStepperColumnsTests|D52DownloadsStepperConnectorsTests|D53DownloadsCardWidthTests|D54QueueDurationColumnTests|D55QueueHeaderAlignmentTests|D56TimelineYearBaselineTests|D57TrailingInspectorHeightTests|D58RadioStationLogoTests|D59RadioOnAirAddStationTests|CupertinoChartsTests|TimelineTests|AtlasTests|StationLogoStoreTests|QueueWorkspaceTests|D4PageTitleEdgeTests|D4SidebarHighlightSearchHintTests'` — 89 tests in 22 suites passed (22.239 s) on exact head `9a807380`. No full suite.
- **CI on head `9a807380`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Not verified:** owner visual acceptance in a live window; no CPU measurement (no continuous or looping SwiftUI motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks D5.1–D5.9 in a live window; Slice D6 (Now Playing) can start.

---

## 2026-11-22 — macOS design details D4.7–D4.8, sidebar sub-item highlight edge and search shortcut hint (PR #1214 merged)

- **Merged:** PR [#1214](https://github.com/abucalip/navi-librarian/pull/1214), squash commit `bb701cfaca4b2b6e6ab0d96fc618d35e791aad45`, from exact PR head `36dc8ae4646e4b4e09a44dd88cb7c9af8aa666e3`; branch `macos/d4-7-sidebar-highlight-search-hint`, based on `main` at `27eb07f6` (D4.4–D4.6 docs closeout).
- **Changes:**
  - **D4.7:** `CupertinoSidebar` (`CupertinoTheme.swift`) now passes `subItemIndent` (`CU.Space.m`, 16 pt) into `row(_:_:_:indent:)` as inner leading padding on the icon and label instead of `.padding(.leading, 16)` outside the button, so the `CU.accentTint` highlight pill shares the same leading edge across top-level rows and Discover sub-items.
  - **D4.8:** `CupertinoToolbar` (`CupertinoTheme.swift`) splits `"Search  ⌘K"` into leading `Text("Search")` (`CU.textSecondary`) and trailing `Text("⌘K")` (`CU.textTertiary`) across `Spacer(minLength: 0)`.
- **Tests run:** `swift test --disable-sandbox --filter 'D4SidebarHighlightSearchHintTests|D4SidebarHeaderTests|CupertinoControlsTests'` — 9 tests in 3 suites passed (2.111 s), including Day/Night offscreen render checks in `D4SidebarHighlightSearchHintTests`. No full suite.
- **CI on head `36dc8ae4`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Not verified:** owner visual acceptance in a live window; no CPU measurement (no motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks D4.7–D4.8 in a live window; Slice D5 (columns in lists) can start.

---

## 2026-11-22 — macOS design details D4.4–D4.6, page title edge, quality badge and sidebar group headers (PR #1213 merged)

- **Merged:** PR [#1213](https://github.com/abucalip/navi-librarian/pull/1213), squash commit `2ecb2921de46fb7ac18212e734c7fd78eceb19fc`, from exact PR head `c938fe73f2dc7c9ee3d65b875fe4e6e9177d7566`; branch `macos/d4-4-page-title-edge`, based on `main` at `fab17724` (D4.3 docs closeout).
- **Changes:**
  - **D4.4:** `TimelineView` and `AtlasView` now use `Self.horizontalPadding = CU.Space.xl` (32 pt) instead of 28 pt, aligning their titles, search field and map/rail with Home, Radio, Connections and Downloads.
  - **D4.5:** added `CUQualityBadge` in `CupertinoKit.swift` (filled 4 pt rounded rectangle, bold caption, 8×2 pt padding; `.standard`, `.playing`, `.onMedia`) and adopted it across `CupertinoPlayerBar` (replacing the outlined badge), `CupertinoAlbum` (header and track table) and `CupertinoLibrary` (song table).
  - **D4.6:** unified `CupertinoSidebar` (`CupertinoTheme.swift`) group headers onto `groupHeaderFont` (`CU.Font.eyebrow.font`) and `groupGap` (`CU.Space.m`) so Discover and Playlists share the same small bold grey label and equal inter-group spacing.
- **Tests run:** `swift test --disable-sandbox --filter 'D4PageTitleEdgeTests|TimelineTests|AtlasTests|D4SegmentedRenderTests'` — 21 tests in 7 suites passed (15.410 s); `swift test --disable-sandbox --filter 'D4PageTitleEdgeTests|D4QualityBadgeTests|D4SidebarHeaderTests|CupertinoControlsTests|PlayerBarRefinementTests|HeroAlignmentTests'` — 20 tests in 6 suites passed (4.606 s). No full suite.
- **Visual:** before (`fab17724`) and after (`c938fe73`) offscreen renders in Day and Night were captured and inspected for Timeline, Atlas, Connections, Album and Sidebar; the player bar rendered `"Nothing playing"` in preview mode so its badge was not shown in that render.
- **Not verified:** owner visual acceptance in a live window; CI checks on `c938fe73` were not waited on; no CPU measurement (no motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks D4.4–D4.6 in a live window; D4.7 (sidebar sub-item highlight) can start.

---

## 2026-11-22 — macOS design details D4.3, centre-align phone banner and notice rows (PR #1212 merged)

- **Merged:** PR [#1212](https://github.com/abucalip/navi-librarian/pull/1212), squash commit `2f62f933ac1c546754eefbced5ba0040dde398b5`, from exact PR head `d972ac1abccf607a0443215fc4725275b271b166`; merged 2026-11-21 23:45:44 UTC. Branch `macos/d4-3-phone-banner`, based on `main` at `9c46aede` (D4.2 merged).
- **Changes:** `CUNotice` (`CupertinoKit.swift`) now centre-aligns its leading icon, notice sentence and trailing capsule button (`HStack(alignment: CUNotice.rowAlignment, spacing: CU.Space.s)` with `CUNotice.rowAlignment = .center`) and drops the 4 pt top padding on the icon that had previously aligned only the icon and the 24 pt trailing button while leaving a one-line sentence (`Playing on your phone: …`) 3.0 pt above the banner's vertical centre.
- **Tests run:** `swift test --disable-sandbox --filter 'D4NoticeTests|CupertinoControlsTests|HomeRenderTests'` — 20 tests in 3 suites passed. `D4NoticeTests` (new) checks `CUNotice.rowAlignment == .center` and renders the phone handoff banner in Day and Night, verifying that the vertical centres of the icon, text line and trailing button all sit within 1.0 pt of the banner's vertical centre; `CupertinoControlsTests` re-ran unchanged; `HomeRenderTests` gained Day and Night phone handoff renders (`cupertino-home-handoff.png`, `cupertino-home-handoff-night.png`). In the 40.0 pt rendered phone banner (`68.0..107.5 pt`, centre `87.75 pt`, 2 px = 1 pt), the text centre moved from `84.75 pt` (`-3.00 pt`) before to `88.75 pt` (`+1.00 pt` with descenders; cap-height-to-baseline centre `87.50 pt`, `-0.25 pt`) after, matching the icon (`87.75 pt`) and button (`87.75 pt`). No full suite.
- **CI on head `d972ac1a`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Visual:** before/after Home renders and banner crops in Day and Night were taken and inspected; the info icon, "Playing on your phone: …" sentence and "Continue on this Mac" capsule now sit on one centre line. Owner visual acceptance in a live window is not recorded.
- **Not verified:** owner visual acceptance in a live window. No CPU measurement (no motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks the phone banner alignment; D4.4 (page title leading edge) can start.

---

## 2026-11-19 — macOS design details D4.2, capsule buttons share one height per row (PR #1211 merged)

- **Merged:** PR [#1211](https://github.com/abucalip/navi-librarian/pull/1211), squash commit `bb96dbbaaa1e14921b046c8690423761e3704b98`, from exact PR head `92e36ccd442833aa879083200cec934ef75054d2`; merged 2026-11-19 02:00:00 UTC. Branch `macos/d4-2-capsule-heights`, based on `main` at `f08dded1` (D4.1 merged).
- **Changes:** capsules that sit in one row now share one size variant. The Home marquee's "More" menu is the regular variant (32 pt) beside Get album / Save / Not for me, and keeps the small variant on a Discover row, whose Get / Save / Not for me are all small; the decision lives in `CupertinoPickFeedbackMenu.capsuleStyle(marquee:)`. The Home radio card's Resume, Stop and Open Radio move off their hand-rolled ~22 pt buttons onto the shared `CapsuleButtonStyle` at the regular height via `HomeRadioCardView.capsuleStyle(primary:)` (accent for Resume, neutral for Stop / Open Radio), so "Resume" matches the Home primary capsules.
- **Tests run:** `swift test --disable-sandbox --filter 'D4CapsuleTests|CupertinoControlsTests|HomeRadioCardTests|HomeRenderTests'` — 25 tests in 4 suites passed. `D4CapsuleTests` (new) covers marquee More regular, Discover More small and the radio card regular; `CupertinoControlsTests`, `HomeRadioCardTests` and `HomeRenderTests` re-ran unchanged, and `HomeRenderTests` gained two Night radio-card renders. The rendered "Resume" capsule measured 22.5 pt before and 31.5 pt after (2 px = 1 pt). No full suite.
- **CI on head `92e36ccd`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Visual:** before/after Home renders of the marquee and the radio card in Day and Night were taken and inspected; the "More" and "Resume"/"Stop"/"Open Radio" capsules now share one height per row. Owner visual acceptance in a live window is not recorded.
- **Not verified:** owner visual acceptance in a live window. No CPU measurement (no motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks the Home marquee and radio card capsule heights; D4.3 (phone banner) can start.

---

## 2026-11-19 — macOS design details D4.1, one neutral segmented control (PR #1210 merged)

- **Merged:** PR [#1210](https://github.com/abucalip/navi-librarian/pull/1210), squash commit `fe90cc43151bb2b10156200d8384829f5bca0036`, from exact PR head `4abdb36be351b05d322cb2d7a10e08494df7b62a`; merged 2026-11-19 01:30:22 UTC. Branch `macos/d4-1-segmented-control`, based on `main` at `4274bc61` (D3 merged).
- **Changes:** `CUSegmentedSpec` records the neutral control's sizes (track radius 8, chip radius 4, 2 pt track padding, 24 pt segments, 28 in a control bar). The selected chip is `CU.content` (white by Day, near black by Night), the selected label is `CU.text` semibold and the others `CU.textSecondary` medium; Day keeps the hairline drop shadow and Night adds a 1 pt `CU.separator` hairline because a shadow cannot read on near black. The unused `accented` variant was removed, Radio "Stations / Heard" stopped using it, and the last system `Picker(.segmented)` controls were replaced in Timeline ("By year / By decade"), Atlas ("Map / List") and the classic Connections header ("Depth 1 / 2 / 3", unreachable under the single Cupertino theme). Radio tag chips keep their separate inverted-pill style. The missing contrast pairs were added to `CUPalette.contrastPairs` (unselected segment text on a panel track; filter-chip label on its inverted ground); selected text on the chip and unselected on a content-ground track were already covered. All pass 4.5:1 in Day and Night.
- **Tests run:** the agent's focused run `swift test --disable-sandbox --filter 'SegmentedControlTests|D4SegmentedRenderTests'` passed 9 tests in 2 suites. The owner reports a further 50 tests in 7 suites passed after 133.897 seconds. The selected `DiscairUITests` target was started but stalled and was stopped; no result is claimed for it.
- **CI on head `4abdb36b`:** all five GitHub Actions checks passed: compile, container-smoke, lint-changed, test-and-build and validate-container.
- **Visual:** before/after renders of Timeline, Atlas, Radio, Connections and Downloads in Day and Night were taken and inspected; they show one neutral selected look and no system blue, and the Night hairline is visible. Owner visual acceptance in a live window is not recorded.
- **Not verified:** owner visual acceptance in a live window, the classic Connections depth control (no theme uses it), and CPU (no motion added). Not published, deployed or runtime-verified.
- **Next action:** the owner checks the D4.1 controls in Day and Night; D4.2 (capsule heights) can start.

---

## 2026-11-19 — macOS design details D3, bottom insets and the Pipeline dock (PR #1209 merged)

- **Merged:** PR [#1209](https://github.com/abucalip/navi-librarian/pull/1209), squash commit `7808ab8c1bbee93def332ea4efd2d68ab1ffb8a5`, from exact PR head `2495876f52b35bd055533d68dfa43a4c158ff78a`; merged 2026-11-19 00:35:47 UTC. Branch `macos/d3-bottom-insets-pipeline-dock`, based on `main` at `4bbdfc10` (D2 merged). Implementation commit `d4614fd0`; docs record in the PR `2495876f`.
- **Changes:** D3.1 — `PipelineDockPlacement` holds the visibility rules, the card's 14 pt gap above the player bar and its 16 pt trailing margin (the queue's width plus 16 when the queue is open). The card reports its laid-out height and the window publishes the clearance; the shell takes the shared inset or the card clearance, whichever is larger, so the last row scrolls above the card. D3.2 — one shared 32 pt bottom inset in the Cupertino shell (`safeAreaInset`) replaces the page-level bottom paddings; Timeline, Atlas and Connections move from 20 to 32 pt and Insights keeps 28 pt of its own for the undo bar (60 pt total, as before). Side check: the active card is bottom right (#972), the finished-Get notes are bottom left. The stale comment that said the card was hidden was corrected.
- **Tests run:** `swift test --disable-sandbox --filter 'PipelineDockTests|ScreenshotTests|LiveScreenshotTests|CupertinoPagesRenderTests|HomeRenderTests|ConnectionsServicesRenderTests'` — 50 tests in 6 suites passed. `swift test --disable-sandbox --filter DiscairUITests` — 885 tests, 884 passed; `dismissQueuesOneCardEventKeyedBySubject` hit its known wall-clock freshness assertion in the full run (the event measured 151 s old because the main actor was blocked by render tests) and passed alone (`swift test --filter InsightsModelTests`, 6 tests). No full suite.
- **CI on head `2495876f`:** compile, lint-changed, test-and-build, container-smoke and validate-container all passed.
- **Not verified:** owner visual acceptance in Day and Night, before/after crops of the listed pages, CPU measurement (no motion added; one one-shot geometry read). Not published, deployed or runtime-verified.
- **Next action:** the owner checks the listed pages at the end of their scroll with the card showing; D4 (controls and type consistency) starts next.

---

## 2026-11-19 — macOS design details D2 merged (PR #1208)

- **Merged:** PR [#1208](https://github.com/abucalip/navi-librarian/pull/1208), squash commit `5071453c8ba8a2b1dbd7b510349121726b253375`, from exact PR head `0c306579c3fabfabd6e6076f782473814f99b30e`; merged 2026-11-18 23:46:51 UTC. D2 aligns the Album and Artist hero top inset and leading edge, moves the Album spine inside its cover frame, aligns Album body content, aligns the Artist body and biography to the portrait, corrects Artist menu and capsule spacing, softens and contains the artist scrim, pixel-rounds and overlaps collage tiles, improves translucent capsule contrast, and fixes the playing-row quality badge and overflow action. D2.7 required no code change because the existing hierarchy already matched the plan. Added `HeroAlignmentTests`.
- **Tests:** the owner reports that the complete macOS Swift test suite passed on the PR revision. An earlier full-suite invocation reported the timestamp-freshness assertion in `dismissQueuesOneCardEventKeyedBySubject()` (`abs(event.occurredAt - Date().timeIntervalSince1970) < 60`); the test passed when run alone, and the owner subsequently confirmed the complete suite successful. The assertion was not weakened.
- **Visual review:** the owner approved the visual checks, including the final softened scrim. The earlier broad, hard-edged rectangular scrim was corrected; the final scrim is locally bounded and feathers to transparent on every edge.
- **GitHub CI on exact PR head `0c306579`:** all five associated workflows completed successfully: Validate Docker image (publishing paused), Validate Docker packaging, Lint changed files, Python syntax check, and Container runtime smoke test.
- **Not claimed:** no release publication, deployment, or runtime verification. The full test and visual results above are owner-reported; the CI results were independently checked on GitHub.
- **Next:** D3, bottom insets and the Pipeline dock.

---

## 2026-11-19 — D2.4 artist hero scrim correction (PR #1208 closeout)

- The owner reported that the original left-to-right scrim rendered as a broad dark rectangle with hard edges, extending across the hero. Root cause: the scrim background was attached to a text stack stretched to the available width.
- Corrected CupertinoArtistBanner: constrain the text group to 620 pt, add local breathing room, and use a 55%-centre elliptical gradient that fades smoothly to transparent on every edge. This keeps the contrast aid behind the name, count and actions without a visible panel boundary.
- The final correction is included in PR #1208 head `0c306579c3fabfabd6e6076f782473814f99b30e`, merged as `5071453c8ba8a2b1dbd7b510349121726b253375`. The owner approved the revised appearance and reports that the complete macOS Swift test suite passed. The earlier timestamp-freshness assertion passed when run alone; the owner subsequently confirmed the full suite successful.
- All five GitHub Actions workflows on the exact PR head passed. No publication, deployment or runtime verification is claimed.

---

## 2026-11-18 — macOS design details D2, Album and Artist hero alignment (draft PR #1208)

- **Branch/base:** `macos/d2-album-artist-hero-alignment-clean`, draft PR #1208, based on GitHub `main` at `dd95d6f9ceb54033d04dd341568bba131668b420` (D1 is present on main). Implementation commit: `079bed3efa8729644fef332bbeed92d961fcdb93`.
- **Changes:** shared 76 pt Album/Artist hero top inset and common leading inset; Album spine moved inside the cover frame; Album tabs, track table and related grids left-aligned; Artist body and biography text aligned to portrait; Artist name/menu spacing and capsule rhythm corrected; 55% to clear text scrim; collage tiles pixel-rounded with 1 pt overlap; translucent capsule dark fill and light hairline; playing quality badge changed to accent-on-white; overflow menu moved to the leading edge of its trailing cell. D2.7 needed no code change: current Album and Artist headings already follow the recommended top-level/subgroup hierarchy.
- **Regression tests added:** `macos/Tests/DiscairUITests/HeroAlignmentTests.swift` checks shared hero metrics and collage pixel alignment/overlap for 2–5 tile layouts.
- **Tests/CI:** not run here. macOS Swift tests must run on the owner's Mac; the selector maps the changed UI sources to `DiscairUITests`; run `swift test --filter DiscairUITests` on the exact PR head. No claim of test or CI success.
- **Visual acceptance:** not done. Same-size before/after Album and Artist screenshots in Day and Night, the 400% collage seam crop, and contrast over the lightest collage tile remain owner checks. No merge, publication, deployment or runtime verification claimed.
- **Next action:** run the focused Swift test on the exact PR head, then complete the Day/Night visual checks.

---

## 2026-11-18 — Index theme I6 and two follow-ups (PRs #1202, #1203, #1204)

- **Merged:** #1202 squash `0f069d4e38b5c1894f977c5de5d1f332ca86181c` (head `b61b14f6`): `IndexSheets.kt` (lettered menu sheet used by every Index menu, confirm body), `IndexDownloads.kt`, `IndexStats.kt`, `IndexSettings.kt` (Settings, Server, Appearance), `IndexEqCrossfade.kt`; `PickFeedback.kt` shares actions as pairs; `ServerRead.kt` decodes `/api/health` `version` and `latency_ms`. #1203 squash `6d49fb3399ca727a2d09191f9e47f407a2e24aa7` (head `71c9873e`): Index Paths use the shared layout; Index-only Paths files and branches removed. #1204 squash `735372a3d9b0802aa56b9796d5edd19123a8cf29` (head `9951463a`): Index Home lead is a swipe pager using `IndexMotion` tabSlide.
- **Tests run:** #1202: 99 tests (JDK 17: `IndexStatusRulesTest` new 15, `ServerModelTest`, `IndexTest`, `IndexMotionTest`, `ExistingLayoutsTest`, `GalleryStatusRulesTest`, `IndexPlayerRadioRulesTest`, `IndexHomeRulesTest`), 0 failures, plus `compileDebugKotlin` and `assembleDebug`. #1203: `compileDebugKotlin` only. #1204: `compileDebugKotlin` and `IndexHomeRulesTest`. Not run: full suite. CI on each head: compile, lint-changed, test-and-build, container-smoke, validate-container passed.
- **Emulator:** #1202 only, live server, Signal Blue: Appearance, Settings, Server, Downloads (Done), the Dismiss sheet (closed with Keep), Home pick sheet, Equalizer, Crossfade, Stats, player bar sheet. Appearance restored. Not checked: other palettes, Server version and ping (I0 server not deployed), a download in progress and the Failed tab, queue row sheets. #1203 and #1204 were not checked on a device.
- **Limitations:** I6 departures from the mockups (page bars, unnumbered Settings rows, Stats Albums and Artists only, no "Why this pick?", ten-band equalizer, no "Fade on skip") are listed in the PR. Three new `INDEX_THEME.md` 11a rows await the owner. Not published or deployed. Catch-up entry written after the docs tidy; the I6 closeout had not been recorded earlier.

## 2026-11-18 — Docs folder tidy (PR #1205)

- **Merged:** PR #1205, squash `a1fa8b73a7e62b691518be97b0d5998fddcfdfd6` (head `489b2d3e`). Moved the 10 contracts to `docs/contracts/`, 17 plans with open steps to `docs/plans/`, and finished work (`GALLERY_THEME`, `pathsredesign`, `Discover_page`, `MACOS_HOME_MARQUEE_PLAN`, `PLAYER_PROPOSAL`, `MACOS_M1_PROMPT`, the old recommendation archive, `SERVER_V2_PHASE0_AUDIT`) to `docs/archive/`. Removed the 8 pointer stubs at old paths. Rewrote `docs/...` paths and relative markdown links in docs, source comments and scripts (487 files, comment and path text only). Added `docs/README.md`; updated `docs/archive/README.md`. The parent `CLAUDE.md` (outside the repo) was updated to the new contract paths.
- **Tests run:** none (no behaviour change). `scripts/check_lint_changed.py --base origin/main`: 126 Python files, 0 new findings. CI on head `489b2d3e`: compile, lint-changed, test-and-build, container-smoke, validate-container, validate-release-workflow passed. Not run: full suite.
- **Limitations:** bare filename mentions without a `docs/` prefix were not rewritten (the names are unique). `PROJECT_LOG.md` path strings were updated too. 8 broken relative links remain in `docs/archive` history files, as before the change. Owner checks that remain on archived plans stay in `docs/ACTIVE_WORK.md`.

## 2026-11-18 — Index theme I5, Now Playing, Queue, Lyrics and Radio (PR #1201)

- **Merged:** PR #1201, squash `825f056d2d6d0922fe9a2227b79978e5111946a0` (head `1fc865b8`). `IndexNowPlaying.kt` (`IndexPlayerFrame` with motion #8: 420ms rise / 320ms fall on Firm, the strip cover flown by hand through `IndexFlight`, only the strip slides away; `IndexPlayer` with Now Playing, Queue and Lyrics; `IndexPlayerRules`), `IndexRadio.kt` (Radio page with Stations / Heard tabs, the Heard route, the live page in the same frame; `IndexRadioRules`); one Index branch each in `NowPlayingSheet`, `RadioScreen`, `HeardScreen`, `RadioNowPlayingSheet`; `OnArtwork(keepBrutal = true)` keeps the chosen palette for Index (its only caller is the player wrapper in `MainShell`). `ARCHITECTURE.md` Index line and `INDEX_THEME.md` status and 11a (two new rows) amended.
- **Tests run:** `IndexPlayerRadioRulesTest` (new, 13; rerun on the final head), `IndexMotionTest` (8), `IndexTest` (10), `ExistingLayoutsTest` (3), `RadioScreenTest` (3) (JDK 17), all pass. CI on head `1fc865b8`: compile, lint-changed, test-and-build, container-smoke, validate-container all passed. Not run: full suite.
- **Emulator:** live server, nothing played (scrobbling switched off for the check and back on after). Signal Blue: Now Playing, Queue, untimed Lyrics, Radio Stations and Heard tabs. Graphite Orange: Home strip, Now Playing, Queue. Appearance restored to Follow on with Day · Sand / Night.
- **Limitations:** live radio Save and previous/next station not built (new 11a rows, owner decision); station favourite by long press or screen-reader action (no heart); Radio has a page bar, not the Home bar; no lyrics photo backdrop; the waveform replaces the plain seek line when peaks exist. Not checked on screen: the live radio page, timed lyrics, the rise and cover flight frame by frame, Newsprint Red and Field Green. Not published or deployed.

## 2026-11-18 — Index theme I4, Discover, Library and Search (PR #1200)

- **Merged:** PR #1200, squash `c0b3a845dc19d377121a31d5523a8ee1122ad1ce` (head `b2897ca6`). `IndexDiscover`, `IndexLibrary`, `IndexSearch`, `IndexListsRules`; one `isIndex()` branch each in `DiscoverScreen` (head and list body), `InsightsPage`, `LibraryScreen`, `SearchScreen`; `IndexTabs` scrolls the chosen tab into view; `LibraryArtist.plays` (optional, null on an older server). `ARCHITECTURE.md` Index line and `INDEX_THEME.md` status amended.
- **Tests run:** `IndexListsRulesTest` (new, 12), `DtoFixtureTest` (8), `ExistingLayoutsTest` (3) (JDK 17), all pass. CI on the PR head: compile, lint-changed, container-smoke, validate-container passed; test-and-build was still pending when the merge was recorded. Not run: full suite, `IndexMotionTest`, `PaletteTest` (no motion or palette change).
- **Emulator:** Signal Blue only, live server: Discover lists and the X menu, Insights (Taste only; no lens had cards), Library Artists / Albums / Genres with the letter rail, Search groups with Get. Appearance restored to Follow on with Day · Sand.
- **Limitations:** discover frame 3 (lettered taste sheet: Discovery mode, Blocked genres, More like this, Refresh lists) not built, new behaviour awaiting the owner; one tab row for all seven lists; the X opens a menu; no A–Z INDEX link on Albums; artist rows show the play menu instead of the album count; the rail covers loaded pages only; the Genres count is hidden when the server returns its full default of 60; Search has no top bar and no source count. Insight lens rows, the anniversary block, artist plays and the other palettes unchecked on screen. Not published or deployed.

## 2026-11-18 — Index theme I3, Album, Artist, Genre and Paths (PR #1199)

- **Merged:** PR #1199, squash `39cc5d08ed3e5651643df5552e6beb825b4d6965` (head `dd22d8e2`). `IndexAlbum`, `IndexArtist`, `IndexGenre`, `IndexAlbumPaths`, `IndexArtistPaths`, `IndexPagesRules`; kit: key/value grid, sheet header, `IndexPlayingBars` (#13, with `IndexMotion.barHeightDp`), baseline-aligned `IndexDataList`, `IndexSectionHead(rule=)`; Index sheets get `statusBarsPadding`; DTOs decode `library_position`/`library_total`, artist `play_count`/`active_years`, `albums` counts, path stop `years`/`shared_albums`. `ARCHITECTURE.md` row and `INDEX_THEME.md` 11a (three new missing rows) amended.
- **Tests run:** `IndexPagesRulesTest` (new), `IndexMotionTest`, `ExistingLayoutsTest`, `IndexHomeRulesTest`, `PathsTest`, `DtoFixtureTest`, `IndexTest`, `PaletteTest` (JDK 17): 107 tests, 0 failures. CI on head `dd22d8e2`: compile, lint-changed, test-and-build, container-smoke, validate-container all passed. Not run: full suite.
- **Emulator:** Signal Blue only, live server: both album pages, artist, genre, album and artist Paths with opened steps; Open album then Back returns to the step. System Back with a Paths step open closes the whole sheet on Standard too (pre-existing, not fixed).
- **Limitations:** mockup departures listed in the PR (Play instead of Top songs, no Get on path steps, no Shuffle genre / Discover more, no artist position, pick number or genre artist counts until the owner decides). Other palettes, moving playing bars, reduced motion and a phone unchecked. Not published or deployed.

## 2026-11-18 — Index theme I2, Home (PR #1198)

- **Merged:** PR #1198, squash `05b3df3c3cf42c417f787b274ac531a35e96a39c` (head `f20fa89a`). `IndexHome`, `IndexHomeRules`, kit additions (`indexArrive`, `indexRuleDraw`, `IndexNumeral`, `IndexGetButton`, `IndexDataList`, `IndexInsightBlock`), `IndexMotion.rowDelayMs`/`digitDelayMs`, `ShelfAlbum.playCount`; `ARCHITECTURE.md` row amended.
- **Tests run:** `IndexHomeRulesTest`, `IndexMotionTest`, `IndexTest`, `ExistingLayoutsTest`, `PaletteTest`, `HomeArtistsTest` (JDK 17), all pass. CI on the merged head not re-checked here. Not run: full suite.
- **Limitations:** no emulator or phone screenshot against `pages/home`; differences listed in `ACTIVE_WORK.md`. Not published or deployed.

## 2026-11-18 — Index theme I1, palettes, font pair and shell (PR #1197)

- **Merged:** PR #1197, squash `cc1614b25ec4c3e23aa286bdd0c0388c72b95847`. `Layout.Index`, four palettes pinned to `tokens.json`, `IndexTones`, `FontPairs.Index`, `IndexIcons` (48), `IndexKit`, `IndexShell`, `IndexMotion`; Index branches in the shared controls, seek bar, chart style, `NavRules`, `ThemeGroups`, `NavIsland`, `MainShell`.
- **Tests run:** 16 focused classes, 146 tests, 0 failures (`IndexTest`, `IndexMotionTest`, `PaletteTest`, `GalleryTest`, `GalleryMotionTest`, `FlowTest`, `SoftBrutTest`, `ExistingLayoutsTest`, `AppearanceRulesTest`, `MotionTest`, `TypeRolesTest`, `TapeDeckTest`, `SheetStackTest`, `StickerWallTest`, `NavRulesTest`, `CoverStackSettingsRulesTest`). CI on head `60092ef9`: compile, lint-changed, test-and-build, container-smoke, validate-container all passed. Not run: full suite.
- **Differences and limits:** Danger label is the page ink on Graphite Orange; tab and source-switch cells are 48dp high; "ALL" link 24dp; chip and text field branches are the agent's reading; chart branch squares column tops only; `PUSH_FADE_MS` and `SNACK_OUT_MS` come from spec 8.2, not `tokens.json`. Left for later steps: insight block, data list, numeral roll (I2), player rise and bars (I5), lettered sheets (I6). Emulator-checked only in Signal Blue and Graphite Orange (board); the live theme switch after the final fix, Newsprint, Field, follow-the-phone night and CPU at rest are unchecked. About 10 s of playback on the AVD. Not published or deployed.

## 2026-11-18 — Index theme I0 server PR 5, library filter (PR #1196)

- **Merged:** PR #1196, squash `5b87060a4a042c492c63b692ddb4230f8cb96f35`. Optional `filter=unplayed|lossless` on `/api/library/albums` (400 on any other value); total counts the filtered albums; the cursor is bound to the filter. Index album entries gain `plays` and `quality` from existing song data (no provider traffic). New `discovery/search/album_filters.py`; contract (`SEARCH_CONTRACT.md` 14.1) and `ARCHITECTURE.md` updated. Shared with Bento. This was the last missing I0 row: **I0 is complete.**
- **Tests run:** `pytest tests/test_discovery_search_query.py tests/test_api_search_routes.py tests/test_quality_label.py` (103 passed). CI on the final head (`d9c7ad8a`) not re-checked here. Not run: full suite.
- **Limitations:** no recorded fixture (no response fields added); the route test for a cursor from another filter only runs when a second page exists; Android decoders not opened. Not published or deployed.

## 2026-11-18 — Index theme I0 server PR 4 (PR #1195)

- **Merged:** PR #1195, squash `3744190728a4bb072e415fd88999b8be231d0c51`. Optional `presentation.shared_albums` (`{album, year, owned}`, oldest first, at most 12) and `presentation.years` (`{from, to}`) on `sideman_to_leader` stops, from the releases behind the stop's reasons and `release_facts.date`. New `intelligence/graph/path_stop_facts.py`; `presentation_version` 8 rebuilds cached paths; contract (`SERVER_V2_CONTRACT.md`) and `ARCHITECTURE.md` updated. No provider traffic.
- **Tests run:** `test_intelligence_paths` and `test_intelligence_paths_warm` (35 passed, incl. 2 new). CI on the final head not checked here. Not run: full suite.
- **Limitations:** recorded `paths_sideman_to_leader*.json` fixtures not re-recorded; other kinds carry no shared albums; Android decoders not opened. Not built: library `filter`. Not published or deployed.

## 2026-11-18 — Index theme I0 server PR 3 (PR #1194)

- **Merged:** PR #1194, squash `9cc0f746e78658748abf8cc4721b18bcc72c15e3`. Artist page fields: `play_count` and `active_years` (`{begin, end, ended}` from the stored life span, read-only by MBID) on the `artist` section; `owned_count` and `album_count` (provider-listed albums only) on the `albums` section. New `discovery/search/artist_facts.py` and `intelligence/knowledge/artist_years.py`; contract (`SEARCH_CONTRACT.md` 14.5), `ARCHITECTURE.md` and `INDEX_THEME.md` updated. No new provider traffic.
- **Tests run:** `test_artist_facts` (new, 9), `test_discovery_search_artist_sections`, `test_api_search_routes`, `test_discovery_search_query` (all passed, 129 in total before a lint-only import fix; the new file re-run after it); `check_lint_changed.py` clean. CI result on the final head not re-checked here. Not run: full suite.
- **Limitations:** no recorded fixture for the new fields; Android decoders not opened. Not built: path stop `years` and `shared_albums`, library `filter`. Not published or deployed.

## 2026-11-18 — Index theme I0 server PR 2 (PR #1193)

- **Merged:** PR #1193, squash `2e169cf4034265fd6fd9f3def47e5fc5b773ad37`. Three of the missing I0 rows, all optional fields with no new provider traffic: `/api/health` `version` and `latency_ms`; `plays` on `/api/library/artists` items; `library_position` and `library_total` on the album page `album` section (new `discovery/search/album_position.py`). Contract (`SEARCH_CONTRACT.md` 14.5), `ARCHITECTURE.md` row and the audit table updated. The three share one PR at the owner's request (the spec says one each).
- **Tests run:** `test_health_route`, `test_album_position`, `test_discovery_search_album_page`, `test_discovery_search_query`, `test_dashboard_routes` (all passed); `check_lint_changed.py` clean. CI first failed on `test_dashboard_routes` (it pinned the exact health body); fixed in the PR. Not run: full suite.
- **Limitations:** no recorded fixture added for the new fields; Android decoders not opened. Not built: artist page fields, path stop `years` and `shared_albums`, library `filter`. Not published or deployed.

## 2026-11-18 — Index theme I0 server data audit (docs PR)

- **Done:** audited the 13 rows of `docs/plans/INDEX_THEME.md` section 11a against `main` (`9e810191`): 6 served, 7 missing (played counts, artist plays, artist page counts and years, album library position, path stop years and shared albums, `/api/health` version and latency, library filters). Table filled in the spec.
- **Tests:** none run; docs only. **Limits:** server code read only, Android decoders not opened, nothing built, no provider traffic needed. Owner decision I0-1 (played rows): a windowed count, built in PR #1192 (`ab19ed36`, 20 filtered tests pass, not run against a real ListenBrainz account). The Bento B0 audit shares the played, artist, paths, health and filter rows.

## 2026-11-18 — macOS Booklet B4 Your edition (PR #1190)

- **Merged:** PR #1190, squash `c284e1e483c85010872831d9f0a1c69284547e49`; CI on the PR passed (5 checks). Slice B4 of `docs/plans/MACOS_PATHS_BOOKLET.md`, built because the owner answered D3 (a). Server: `intelligence/artwork/index.py` adds `from_owned` to each `booklets` entry (and `booklet`): true when the booklet's release is the owned release, false when none is owned. Recorded in `docs/contracts/SERVER_V2_CONTRACT.md`; the artwork index fixtures were regenerated (two of them hold booklets). Mac: `ArtworkBooklet` and `BookletView` decode it (missing means false), `BookletLayout.editionTag`, and the editions row shows the "Your edition" tag (`ownedTag`/`ownedTagInk`). `navidrome_server.py` untouched.
- **Tests run:** `pytest tests/test_intelligence_artwork_index.py tests/test_artwork_fixtures.py` (43 passed); `swift test --filter BookletTests` (12), `BookletLayoutTests` (31), `BookletRenderTests` (6), all passed. Not run: full suites, Android tests (its decoder ignores the new key).
- **Limitations:** the render tests draw no owned edition, so the tag has no screenshot check; no CPU measurement (static tag), no real-window check. D4 (language tag) not built. Not published or deployed.

## 2026-11-18 — macOS Booklet finish B3 (PR #1189)

- **Merged:** PR #1189, squash `0f01a519b37666345dfdd3e04de615f18fa8a0e4`. Slice B3 of `docs/plans/MACOS_PATHS_BOOKLET.md`: filmstrip (every spread or page, extras after a separator, current item ringed and scrolled into view), zoom − / value / + / 1:1 in the bar with ⌘+ ⌘= ⌘− ⌘0 (the sheet owns the zoom; a turn, edition change or mode switch resets it), PDF zoom through `PDFZoomController` ("Fit" while auto-scaling, "PDF, n pages" in the bar), edition pop-up below 900 wide, loading and failed page states. New pure rules in `BookletLayout` (`filmstrip`, `isNarrow`, `showsEditionMenu`, `loadingText`, `stage`, `pdfBarDetail`, `pdfZoomLabel`, zoom limits); new `BookletRenderTests`.
- **Spec choices:** the sidebar stays hidden for one booklet with no extras (the `booklet-pdf` mockup draws it; plan text kept); "−" and "+" are dimmed at the zoom limits; the loading spinner and text are stacked together. D3 and D4 tags not built.
- **Tests run:** `swift test --filter BookletRenderTests` (6 passed), `BookletLayoutTests` (passed, new cases added), `BookletTests` (11 passed). Not run: the full UI target or suite. CI on the PR was not checked by this session.
- **Limitations:** no CPU measurement (B2's and B3's both open), no real-window check, PDF state not rendered (`PDFView` cannot be drawn offscreen). Not published or deployed.

## 2026-11-17 — macOS Booklet layout B2 (PR #1188)

- **Merged:** PR #1188, squash `e13bd1d64e89207e5f60a1782d1f25b08e39f866`. Slice B2 of `docs/plans/MACOS_PATHS_BOOKLET.md` with owner decision D1 (a): the Booklet stays a sheet, closed by Done or Escape. New bar (album title, "Booklet · edition · position", Page/Spread switch, Done), editions and extras sidebar (left out for one booklet with no extras), spread stage (pages fitted to the stage height, gutter shade, spread shadow, turn arrows, 0.15 s cross-fade, zoom per spread), three-line caption; "Another booklet" and its notice removed. `title:` added to `BookletSheet` and `BookletOpener`, passed by `CupertinoAlbum`, `AlbumBookletTab`, `PlayerBarCover` and `NowPlayingBookletBadge` (a fourth opener the plan did not list). Pure helpers `barDetail`, `showsSidebar`, `aspect`, `fit`, `index(of:)` in `BookletLayout`; views in new `Chrome/BookletParts.swift`.
- **Spec choices:** the bar title starts above the main column, as in the mockup; below 900 wide the sidebar is still drawn (the pop-up is B3). D4 unanswered: no language tag (recommended b).
- **Tests run:** `swift test --filter BookletLayoutTests` (23 passed, 5 new), `swift test --filter BookletTests` (11 passed); `swift build` clean. Not run: the full suite, other targets. A throwaway offscreen render matched the mockup's bar, sidebar and caption; page images were empty (no artwork store), so the spread was not seen.
- **Limitations:** no real-window check; the B2 CPU measurement (`top -l 4 -s 4`, five cases) was not taken; both belong to the owner check after B3. Filmstrip, zoom buttons, PDF zoom, narrow layout and loading/failed texts are B3. Not published or deployed.

## 2026-11-17 — macOS Booklet B1 base (PR #1187)

- **Merged:** PR #1187, squash `a16dc62054ffc5c887186a025344b34137c62305`. Slice B1 of `docs/plans/MACOS_PATHS_BOOKLET.md`: `CUPalette.stageAccent`, the `CU.Booklet` part of `CUPathsBooklet.swift`, `Model/BookletLayout.swift`. The generated geometry constant `bar` clashed with the `bar` colour, so it is `barHeight` in `build.py` and the package copy. `AppearanceTests` hue test also lets `stageAccent` change.
- **Spec gaps decided:** a one-page spread reads "Page 1 of 16"; "1 page" singular; an empty edition drops the ", edition" suffix in the caption.
- **Tests run:** `swift test --filter 'BookletLayoutTests|BookletStageAccentTests|CupertinoTokensTests|AppearanceTests|BookletTests'`, 48 tests in 5 suites, all passed; `check_contrast.py` 0 failing. Not run: the full suite.
- **CI:** all five checks reported success on the PR.
- **Limitations:** no visible change; no CPU measurement (no motion). Not published or deployed.

## 2026-11-17 — macOS Paths P2 details (PR #1186)

- **Merged:** PR #1186, squash `d20d2e93bd796d2e522c9e86528d89d83527c11b`. Slice P2 of `docs/plans/MACOS_PATHS_BOOKLET.md`: artist steps show the round `ArtistPhoto`; `PathRowThumb` asks `.display` above 64 pt; Room photos 96 × 64 under the album name; the "Your listening" card on the Gaps tab only; the summary is drawn while loading and after a failure, and an empty tab shows only its empty line. New `Tests/DiscairUITests/PathsRenderTests.swift`; `PathsSheetModel` gains `showForPreview(failed:)` and `clearForPreview`.
- **Tests run:** `swift build`; `swift test --filter PathsRenderTests` (10 passed), `PathTrailTests` (26), `PathsModelTests` (17). `select-tests.sh` answered "all", so the full suite was not run. Renders compared by eye with the PNGs for artist-sideman, gaps, room and min.
- **CI:** not checked by me; the owner merged.
- **Limitations:** the Room renders show no session photos (no artwork store in the test), so the 96 × 64 layout is unseen; generated covers and initials, not real art; no CPU measurement (no new motion); not checked in a real window. Not published or deployed.

## 2026-11-17 — macOS Paths P1 layout (PR #1185)

- **Merged:** PR #1185, squash `c5d9b6d864a867d3bdf16cfdb0d40711d9fe3738`. Slice P1 of `docs/plans/MACOS_PATHS_BOOKLET.md`: `Themes/Cupertino/CUPathsBooklet.swift` (Paths part), `Chrome/PathTrailViews.swift`, `Chrome/PathsSheet.swift` rewritten, `PathRowThumb` optional radius.
- **Owner decisions:** D2(a) resizable (ideal 1040 × 680, minimum 820 × 520), D5(a) filter back to All on each open, D6(a) all four arrows move in visual order.
- **Tests run:** `swift build`; `swift test --filter 'PathsModelTests|PathTrailTests'`, 43 tests, all pass. A throwaway offscreen render of the Crew tab (Day, sample data) matched `paths-crew.png`; not committed.
- **CI:** all five checks reported success on the PR.
- **Limitations:** the CPU measurement (five cases) was not taken; not checked in a real window; Night, the other tabs and keyboard behaviour were not exercised; no render test yet (P2). Not published or deployed.

## 2026-11-17 — macOS Paths P0 model (PR #1184)

- **Merged:** PR #1184, squash `5ec4ac568a9221ae4ff4545e64ee12dc0c0531af`. Slice P0 of `docs/plans/MACOS_PATHS_BOOKLET.md`: `Model/PathTrail.swift`; `PathStep` gains `firstVia`, `firstCode`, `creditRole`, `anchors` and `with(id:)` (the artist dedupe no longer rebuilds steps by hand); `PathAnswer.capped` kept structured; `PathsSheetModel` gains `year`, `filter`, `groups`, `order`, `looseNotes`, `count(for:)`, and `move(by:)` follows the visual order. The current sheet shows capped sentences through `looseNotes` (now after the other notes).
- **Owner decisions:** role-line anchors only from the reasons that share the first reason's link; `creditRole` reads `evidence.relation` (the fixtures send `role` null for crew).
- **Tests run:** `swift build`; `swift test --filter 'PathsModelTests|PathTrailTests'`, 43 tests, all pass. Not run: the rest of the UI suite, CPU measurement (no visible change).
- **CI:** not checked by me on the final head before the owner merged.
- **Limitations:** no visible change; P1 needs decisions D1, D2, D5, D6.

## 2026-11-17 — Web Listening Room: mockups for every page, reasons showcased, no Paths (docs, on main)

- **Request.** The owner asked for mockups of all web pages, without Paths (Paths stays on Android and macOS). They also asked for the texts that explain each pick to be "centred" in the sense of showcased: given a prominent place of their own, not centre-aligned. An earlier attempt was interrupted and thrown away at the owner's request; this round started fresh from `main` at `d3c4ed67`.
- **Reasons.** Every reason now sits in a reason panel:
  - new tokens: `reason-fill` `#1D2027` and `reason-rule` `#8A90A0`, plus hero variants;
  - a "Why this pick" label carrying the kind's icon;
  - the sentence in Instrument Sans 600 at 24/32 on heroes and 18/26 elsewhere, at full text strength;
  - a 3-line reason strip on grid cards.

  On ranked rows, the panel sits beside the title.
- **Pages.** `_src/pages.py` writes 25 pages from shared parts:
  - Discover with one list switch over the six lists;
  - Library (list and grid);
  - Artist;
  - Album (not owned and owned);
  - Album modal;
  - Genre;
  - Search;
  - Saved;
  - Blocklist;
  - Acquisitions (every tone);
  - Radio and Heard;
  - Settings (each of the six tabs);
  - Sign in.

  `build.py` renders each page at 1440 and 390 at a measured height. Home and states lost Paths; the rail gained Blocklist.
- **Package.**
  - 52 icons (18 added, `paths` removed); new components 5.14 to 5.30 in `components.css`.
  - The plan gained section 8 (a spec for each page), section 12 (the page list) and slices L7 to L14.
  - L0 item 3 is now the page-fields check.
- **Checks.**
  - `check_contrast.py`: all pairs pass, including the new reason pairs and the hero reason fill and rule over 1,301 tints (lowest hero text ratio 8.57).
  - `build.py` wrote 54 PNGs.
  - Checked by eye: home (1440 and 390), reasons, states, discover-daily, discover-phone, album, artist, album-modal, acquisitions (1440 and 390), library-phone, search and settings-slskd. That review led to fixes:
    - the reason-strip clamp;
    - the phone toolbar;
    - Get on phone rows;
    - Similar albums as cards;
    - a button inside a link in Search;
    - the phone genre chips and mini grids;
    - phone shelves cut to four covers;
    - one Save per settings tab (Last.fm, ListenBrainz and Discogs each get their own page);
    - Home's tablet badge;
    - the R5/R11 sheets and the Sizes note on the reasons page.
  - `scripts/check_lint_changed.py --base origin/main`: 0 new findings.
  - Not run: the unit suite (docs only).
  - Not opened: the other phone PNGs, which were generated but not viewed.
- **Limits.** Mockups only, no code. The acquisition and station helper sentences in the mockups are stand-in copy; the build shows the server's `details.message` (plan 8.10, 8.11). The owner decisions D1 to D4 are still open. Fields the pages print that L0 must confirm are listed in plan section 9.3.

## 2026-11-17 — CI optimization: unit suite under pytest, 40 min to 69 s (merged)

- Cause: CI ran `python -m unittest discover`, which does not load `tests/conftest.py`. Since R3 part 2 (#1137) put every MusicBrainz call behind the shared provider gate, each such call in a test slept 1.1 s on the real gate file. In run 44127218306 (`Ran 4426 tests in 2375s`), almost all of the time was in discovery files (candidate_gathering 907 s, save_tag_seed 321 s, replenishment 170 s, ...), with gaps in exact multiples of 1.1 s.
- PR [#1182](https://github.com/abucalip/navi-librarian/pull/1182) (squash `8eb8dfcc`, head `4d7b26a1`): `docker-test.yml` installs `pytest==9.1.1` (CI only) and runs `pytest tests -q -p no:cacheprovider --durations=25`; the job timeout went from 60 to 15 min. Three test modules aliased imported production `test_*` functions so pytest does not collect them. `docs/TEST_PLAN.md`: the full-suite command is pytest, with the reason.
- Same tests: unittest IDs from the CI log and `pytest --collect-only` match. pytest adds only `test_intelligence_taste_library_genres.py::test_newest_observation_wins_and_untagged_tracks_are_skipped`, which unittest never ran.
- Tests: locally, pytest on the ten slowest files plus the three edited files and the new test: 198 passed in 1.6 s. CI on the head: `4424 passed, 2 skipped, 1 xfailed, 1148 subtests passed in 69.00s`; all checks passed. The full suite was not run locally.
- Remaining: the slowest test is `test_provider_gate.py::MultiProcessTests::test_two_processes_never_get_slots_closer_than_the_interval` at 21 s, an intended real-time check. Docs-only pushes to `main` still run the suite; that now costs about 2 min.

## 2026-11-17 — Android Bento and Index design systems (docs PR, owner review pending)

- **Background.**
  - The owner picked Bento from four new proposals (Bento, Orbit, Darkroom, Spectrum, drawn as Design canvas artifacts and not in the repo).
  - They brought back Index from the 16 November proposal.
  - They kept these palettes:
    - Bento: Sorbet, Licorice and Riviera;
    - Index: Signal Blue, Newsprint Red, Graphite Orange and Field Green.
- **Added:**
  - `docs/plans/BENTO_THEME.md` and `docs/plans/INDEX_THEME.md` (spec, colour, type, icons, components, motion with Compose build steps, Home, page list, files, build steps, open decisions);
  - `docs/design/bento/` and `docs/design/index/`: tokens, generated `palettes.css`, component CSS, 48 icons each with a Kotlin object, mockups as HTML and PNG (14 pages each, 46 to 47 frames: Home, Album/Artist/Genre, album and artist Paths, Player, Discover, Library/Search, Radio, Downloads/Stats/Server, Settings, Sheets, Setup/Unavailable/Newly added/Saved, Booklet/Cover picker/Neighbours by ear/Sonic path, Palettes, Components), a live `motion.html`, `_src/build.py` and `_src/check_contrast.py`;
  - `docs/design/_kit/` (shared sample data, icon paths, contrast maths, page wrapper, stand-in art).
- **Fonts.**
  - Bento ships `gabarito_bento.ttf` (88 KB) and `figtree_bento.ttf` (43 KB): Latin subsets made with fontTools from Google Fonts' variable sources, OFL licences included.
  - Index uses fonts already in `res/font`.
- **Colours changed for contrast:**
  - Sorbet's control `#C8381A` → `#B8321A`;
  - Newsprint Red `#C8231B` → `#B81F18`;
  - Field Green `#0B7A4B` → `#086F43`;
  - a separate `stripProgress` tone for Index's player strip.
- **Owner rule added (2026-11-17):** if a theme element needs a route or field the server lacks, it is built server-side, not dropped. Section 11a of each spec holds the audit table (served, check or missing) and step B0/I0. Known missing:
  - album filters (Unplayed, Lossless);
  - Index's library position.
- **Decisions (2026-11-17):** the owner took every proposed answer, B1 to B7 and I1 to I7, and kept both Bento font files (Figtree is not swapped for Inter). I7: build the library position field.
- **Checks run:**
  - `check_contrast.py` for both themes: all seven palettes pass.
  - Both `build.py` scripts ran and rendered every PNG with Chrome.
  - pylint with the `check_lint_changed.py` checks on the five new Python files: 10.00/10.
  - No app code changed and no Android tests were run (none apply).

## 2026-11-17 — CI hang: unit suite never exited; CI runs the suite once, with timeouts (merged)

- Symptom: from about 02:30 UTC, CI runs stayed queued for hours or ended `cancelled` after 6 hours. Not a GitHub incident (status page: last Actions incident resolved 2026-11-16 16:26 UTC).
- Cause: after #1160 (`c817f703`), `test_intelligence_musicbrainz_auto_fill.WorkerTests.test_switching_auto_fill_off_keeps_the_worker_and_insights_running` failed (`start` called twice) before `stop.set()`, leaving `worker.main()` in a non-daemon thread. The suite finished (`Ran 4253 tests in 2360s, FAILED (failures=2)`), then the process logged `Could not save runtime metrics` every 5 minutes until GitHub's 6-hour default cancelled the job. `Validate Docker packaging` and `Python syntax check` both ran the suite with no `timeout-minutes`; 20 hung jobs held every concurrent slot and over 200 runs queued. The test was fixed in #1174 (`07f0dd96`, `addCleanup(stop.set)`).
- Cleanup: 65 unit-test runs cancelled by hand with owner approval (19 hung in progress, 46 queued and created before #1174).
- PR [#1179](https://github.com/abucalip/navi-librarian/pull/1179) (squash `4153075b`, head `9112d5b8`, merged 2026-11-17 14:57 UTC; CI queued at merge). The unit suite runs only in `Validate Docker packaging` (the copy in `Python syntax check` was removed, owner decision; that workflow's `feature/acquisition-integration-hardening` pushes no longer run the suite). Timeouts: 60 min on the suite job, 15 min on `Python syntax check`, 10 min on `Lint changed files`. A concurrency group per pull request cancels the older run; pushes keep one run per SHA. `docker-release.yml` unchanged. `main` has no branch protection or ruleset.
- Tests: all workflow files parsed as YAML; `tests/test_intelligence_musicbrainz_auto_fill.py` 24 passed locally on `main` in 2 s with no threads left. Full suite not run; CI on the PR head and merge commit was queued at merge.

## 2026-11-17 — K2: page sections served stale from the discovery cache state fetched_at (merged)

- PR [#1178](https://github.com/abucalip/navi-librarian/pull/1178) (squash `9a9f271f`, head `f6a62962`, merged 2026-11-17 14:02 UTC; CI pending at merge; not deployed). GitHub confirms `MERGED`. CI (compile, lint-changed, test-and-build, container-smoke, validate-container) was still pending on `f6a62962` at merge. It does the last K2 item from `docs/plans/efficiency.md` "Finishing Up" that had no gate.
- Artist and album page sections built from a discovery search cache row served stale (`read_or_revalidate`) state `fetched_at`, the oldest such row's store time (UTC ISO 8601, the format of `/api/album-reviews`). Each section job runs under `discovery/search/cache.py::run_noting_stale` (a per-job context variable, reset after the job); `with_fetched_at` stamps a copy of an available section only. The artist identity lookup does not set it (the MBID is not shown, and the job that looks it up first varies). Fresh, deadline, failed and library-only sections and the stored rows never carry it. `docs/contracts/SEARCH_CONTRACT.md` sections 3.8 and 14 document the optional key; Android (`ignoreUnknownKeys`), Swift `JSONDecoder` and the web ignore unknown keys.
- Not done: wider K2 scope (similar-artist records, candidates' tag lookups, the search and genre pages) stays gated on evidence. The `similar_albums` lambda's closure over `result` in `album_page.py` predates the PR and is unchanged.
- Tests: new `tests/test_discovery_stale_fetched_at.py` 14 passed; with the stale-rows, album page, artist sections, top songs, search routes, owned prefetch and similar precompute files, 195 passed; the genre, providers, store prefix delete and similar files, 101 passed. Lint on changed files: 0 new findings. Full suite not run. No live run, no provider traffic, not deployed.

## 2026-11-17 — K3 part 2 measured: "library tracklist first" (owner-approved provider traffic)

- Two backup copies of `local-test/data-live` on ports 8095 (cold) and 8096 (prefetched with the approved compose caps, limited to 24 cold owned albums), PR #1177 head. One first view of each album page per copy, each tracks section timed.
- Provider tracks section, median / p95 / max: cold 458 / 1,178 / 2,413 ms; prefetched 21 / 870 / 3,667 ms. Library tracks section: 17 ms in both. 4 of 24 albums have no provider tracklist and wait on every view.
- Provider requests: about 450 in all (pass A 215, prefetch 148, pass B 85, plus 45 in a 6-album re-check). Pass B still made 65 Last.fm requests (not attributed to a section).
- Owner decision the same day: keep "library tracklist first" permanently. The "temporary" label is dropped in PR #1177 (comment in `discovery/search/album_page.py`, test docstring, `docs/contracts/SEARCH_CONTRACT.md`); behaviour unchanged. Raw output: `local-test/k3m-*.json` (outside the repo).

## 2026-11-17 — Efficiency finishing up: K3 reviews prefetch (off), K2 fetched_at, M1 Navidrome label (merged)

- PR [#1177](https://github.com/abucalip/navi-librarian/pull/1177) (squash `a4804473`, head `1c0ace77`, merged 2026-11-17 13:31 UTC; CI queued at merge; not deployed). GitHub confirms `MERGED`. CI (compile, lint-changed, test-and-build, container-smoke, validate-container, validate-release-workflow) never started on any of the PR's heads: runners were queued, as for `main`'s own runs since 12:55. It covers the "Left out of merged steps" list in `docs/plans/efficiency.md`, at the owner's request.
- M1: no production Navidrome call outside the shared client was found. The `client_factory` branch now sends the `navidrome` label.
- K2: `LayeredCache(stale_fetched_at=True)` gives stale album reviews and links answers a `fetched_at` field (UTC ISO 8601). Fresh and stored values never carry it. `docs/contracts/SEARCH_CONTRACT.md` is updated.
- K3: the review outlets moved to `app/services/album_review_sources.py`, and the worker prefetches reviews under a new `reviews` cap. It stores outlet answers only, never the list, so a worker without `GUARDIAN_API_KEY` cannot hide a Guardian review on the route. The compose default does not name the cap, so this stays off (owner decision needed). The artist biography stays out (K1 measured 0 requests).
- Not done, each behind its gate: the "library tracklist first" removal (needs a measurement) and wider K2 scope (needs evidence).
- Tests: 14 focused files, 237 passed (`test_album_review_sources.py` is new, with 12 tests); `test_discovery_search_album_page.py` 29 passed after the label change. Full suite not run. Lint on changed files: 0 new findings. Full suite not run. No live run, no provider traffic, not deployed.

## 2026-11-17 — K3 part 2 caps and coverage target (merged)

- PR [#1176](https://github.com/abucalip/navi-librarian/pull/1176), squash `75c7728d`, head `bf5fd8b3`, merged 12:55 UTC. CI (compile, lint-changed, test-and-build, container-smoke, validate-container) pending at merge.

- Owner decision on the recommendation: `OWNED_PREFETCH_BUDGETS=musicbrainz=600,listenbrainz=300,lastfm=600,deezer=600,apple=400,wikipedia=300`; coverage target: every owned artist and album handled once within 21 days of switching on, at least 90 % `complete`.
- Inputs: Navidrome `getArtists`/`getAlbumList2` counts (705 artists, 1,739 albums, read-only); K1 pass-0 per-provider costs per owned entity (`local-test/k1-session.json`, outside the repo). ListenBrainz binds (about 2.7 per artist-album pair, about 110 pairs a day); the new caps are 1.5 to 2.3 times their need at that rate.
- At the owner's request `compose.yaml` defaults the worker to these caps (`OWNED_PREFETCH_BUDGETS=off` switches it off; an empty value falls back to the default).
- Test: `pytest tests/test_owned_prefetch.py` 22 passed (4 new in `RecommendedCapsTests`, one checks the compose default). Full suite not run. Not deployed; no live run.
- Limitations: costs from 25 entities of each kind on one store copy; part 2's extra MusicBrainz use was not in the part 1 sizing (600 still leaves room).

## 2026-11-17 — Server efficiency follow-ups with no owner decision: metrics labels, auto-fill shutdown, lock pruning (merged)

- PR [#1173](https://github.com/abucalip/navi-librarian/pull/1173), squash `c81bca22`, head `d9d020fd`: `runtime_metrics` maps `audioscrobbler.com` to `lastfm` and reads a request's `metrics_provider` extension (known names only) after the call; the shared Navidrome client sets it to `navidrome` with a request event hook; `prefetch_state.provider_of` drops its Last.fm special case. Tests: `test_runtime_metrics`, `test_owned_prefetch`, `test_navidrome_client`, `test_navidrome_cover_art`: 50 passed.
- PR [#1174](https://github.com/abucalip/navi-librarian/pull/1174), squash `07f0dd96`, head `60b53896`: `run_api_fill(should_stop=)`, `run_cycle(should_stop=)` and `library_enrich` check the worker's stop event before each fill request, `getAlbum`, search-sweep album, the fill itself, path rebuilds and each manual update request; a stopped fill is left `queued` (`stopped = "shutdown"`) and resumed. Also fixed two `WorkerTests` that had failed on `main` since W3 (two scheduler `start` calls), and made the thread test stop its worker on a failed assertion (it hung pytest). Tests: api_fill, auto_fill, library_enrich_find_artist, update_requests, worker_shutdown, worker_lock, slice import script: 68 passed.
- PR [#1175](https://github.com/abucalip/navi-librarian/pull/1175), squash `b6ff452d`, head `52c3a1e4`: `logos._lock_for` and `ArtworkService._key_lock` count holders and waiters and drop the entry when the last leaves (appendix A5.5). Tests: radio logos, artwork cache, artwork, owned artwork and radio routes, artwork choice: 96 passed.
- Lint on changed files clean for all three. CI queued at merge on all three heads. Full suite not run. Not deployed.
- Limitations: Navidrome calls outside the shared client still count as `other`; no real SIGTERM during a live fill was tried.

## 2026-11-17 — Server efficiency C2 rerun: unused code and owner-approved single-caller adapters removed from navidrome_server.py (merged)

- PR [#1172](https://github.com/abucalip/navi-librarian/pull/1172), squash `0391e5e0`, head `503929cb`, merged 2026-11-17 12:19 UTC (GitHub confirms `MERGED`).
- What changed (5 commits): `navidrome_server.py` went from 2,285 to 2,123 lines.
  - The C2 table was rebuilt on `52b202d1`: 170 symbols, imports included, with a reachability walk from real external references. No adapter was unreferenced; three unused imports (`hashlib`, `unicodedata`, `urlparse`) and two unused locals in `recommend_new_music` went.
  - Owner-approved: the 12 `discovery_{get,set,test}_*` settings wrappers moved into `app/api/settings.py`, which calls `settings/service.py` with the librarian's store, `MUSIC_DIR`, `_set_music_dir`, defaults and callbacks.
  - Owner-approved, acquisition, own commit: `_slskd_search_queries`, `_slskd_search_response_items`, `_discovery_expected_track_count` and `_discovery_filename_key` were replaced by the `integrations.slskd.search` and `acquisition.completion` functions.
  - Owner-approved, other: `_lastfm_similar_artists` and `_discovery_exact_artist_credit_matches` were replaced by their targets; `_default_music_dir`, `_discovery_refresh_all` and `_refresh_listening_profile_background` were folded into their only caller.
  - Two adapter-only tests were removed.
- Tests run:
  - `pytest` on 18 files (acquisition recovery, safety and track; discovery routes, refresh guard, schedule, refill gate, new releases, lens storage, list payload, API injection; settings routes; Last.fm client; slskd search; music paths; quality priority; song peaks; the `recommend_new_music` characterization): 289 passed.
  - New `tests/test_legacy_server_wiring.py`: 7 passed. A line trace showed the 8 changed call-site lines ran in no existing test; with the new file it shows 8 of 8.
  - `check_lint_changed.py --base origin/main`: 6 files, 0 new findings.
- CI: six checks on `503929cb` pending at merge.
- Not run: the full suite. Not deployed.
- Limitations: `discovery_refresh_list("all")` now looks up the two refresh functions when the thread is created instead of when it starts (same functions). The adapters left are listed in ACTIVE_WORK 2n.

## 2026-11-17 — Server efficiency K6: Deezer album page store and Wikipedia no-article mark (merged)

- PR [#1171](https://github.com/abucalip/navi-librarian/pull/1171), squash `f26b1e2f`, head `350e4ad3`, merged 2026-11-17 12:00 UTC (GitHub confirms `MERGED`).
- What changed: in `app/services/album_page_sources.py`, `load_album_links` reads and writes a found Deezer page under `album-deezer-url:v1:*` (7-day links TTL) before asking Deezer; the complete-sets-only rule for the links row is unchanged. `wikipedia_description_remembered` skips Wikipedia for an hour after a search that answered with no matching article (`album-no-match:v1:wikipedia:*`, through `negative_marks`); used by `app/api/metadata.py` and `prefetch_description`. A failed request writes neither. `docs/ARCHITECTURE.md` updated.
- Tests run: `pytest` on `test_album_page_sources` (new `K6Tests`: page stored and reused while the set stays incomplete, failure stores no page, no-article skipped within the hour and asked after, failure or found article writes no mark), `test_metadata_album_info_reviews`, `test_metadata_cache_semantics`, `test_stale_while_revalidate`: 106 passed. `check_lint_changed.py --base origin/main`: 3 files, 0 new findings.
- CI: six checks on `350e4ad3` pending at merge.
- Not run: the full suite; the restart side-by-side pass (K6 acceptance); any provider traffic. Not deployed.
- Limitations: a stored Deezer page that Deezer later removes stays up to 7 days; a Wikipedia article written later appears up to an hour late.

## 2026-11-17 — Server efficiency K4 + K5: short negative caches for review-outlet failures and Deezer/Apple no-match answers (merged)

- PR [#1170](https://github.com/abucalip/navi-librarian/pull/1170), squash `9cdc3ba3`, head `3c6e1600`, merged 2026-11-17 11:54 UTC (GitHub confirms `MERGED`).
- What changed: new `app/services/negative_marks.py` (dated `{"negative": true, "at"}` marks under their own keys). K4: `_ask_outlet` in `app/api/metadata.py` marks an outlet that raised (`album-review-source-failed:v1:*`, 1 h), in the pool thread so failures after the 6 s deadline count; a marked outlet raises `OutletResting`, so the list stays partial and unstored. K5: `album_page_sources.py` marks a definitive no-match for 1 h (`album-no-match:v1:{deezer|apple|deezer-year}:*`) from Deezer's album search (details and links share it), Apple's album search and the album year's Deezer fallback; route and worker share the marks. A failed or refused request, or a Deezer error body sent with status 200, writes nothing; an incomplete links set is still never stored. `/api/artwork` unchanged.
- Tests run: focused pytest, 185 passed over 13 files, plus 103 over the 5 files of the year commit; the changed files also under unittest; `check_lint_changed.py`: 7 files, 0 new findings. Three tests changed to pin the new rules (failed outlet re-asked after its hour; a definite Deezer miss leaves only the mark row, route and worker).
- Warm pass (owner-approved provider traffic): `main` and the branch side by side on two fresh copies of the aged live store, one shared MusicBrainz gate file, 35 album targets. After a restart: 80 provider requests in 38 s against 231 in 205 s on `main`; review outlets 0 against 81. The pass found the album year's Deezer fallback re-asked on every view; fixed in the PR (`deezer-year` mark), warm-pass album-page "not cached" misses 8 to 0. About 1,100 provider requests in all. Details: `docs/plans/efficiency.md`, "K4/K5 warm pass on the aged store".
- CI: six checks on `3c6e1600` pending at merge.
- Not run: the full suite. Not deployed.
- Limitations: two calls remain, recorded as K6 (a found Deezer page in an incomplete links set is re-asked; Wikipedia "no article" is re-asked after a restart). A details no-match read from a mark late in its hour is kept a fresh hour in that process's memory.

## 2026-11-17 — Server efficiency K3 part 2: prefetch of album tracklist, description, year, links and artist image (merged, off)

- PR [#1169](https://github.com/abucalip/navi-librarian/pull/1169), squash `36b582dd`, head `102bd6ba`, merged 2026-11-17 11:10 UTC (GitHub confirms `MERGED`).
- What changed: `app/services/album_page_sources.py` owns the loaders, store keys, TTLs and storing rule for Deezer album details, Apple notes and page address, the Wikipedia lead, the album year, album links and the artist image, with the HTTP `get` injected. `app/api/metadata.py` wraps them in `LayeredCache` as before. The worker (which does not attach `persistent_metadata`) reads and writes the metadata store directly under the same keys, so rows match by construction. `owned_prefetch.album_page_hooks` (tracklist, description, year) and `entity_extras` (links, image) give each work only when its providers have caps. `prefetch_state.PROVIDERS` gains `deezer`, `apple`, `wikipedia`.
- Behaviour: a refused or failed request is never stored. The worker stores a description only when found and nothing when Apple's answer was lost to a failure; a failed MusicBrainz year lookup stores nothing and skips the Deezer fallback; links are stored only when complete; the image only when found. `album_year.lookup_album_year_counted` takes a gate slot and reports failure instead of hiding it. The route keeps its older rule of storing a Wikipedia lead when Apple failed.
- Tests run: `tests/test_album_page_sources.py` (new, 25, includes a parity test that the routes answer from the prefetched rows with their HTTP client failing on any request), `test_owned_prefetch`, every test file naming the metadata or year/links/image routes, `test_app_legacy_import_boundary`, `test_musicbrainz_gate_boundary`, `test_worker_schedule`: 1,164 passed. Lint on changed files: 0 new findings. The gate-boundary test caught a MusicBrainz URL literal in `owned_prefetch` (now `album_year.RELEASE_GROUP_URL`); `test_metadata_cache_semantics` now patches the clock in the new module.
- CI: six checks on `102bd6ba` pending at merge and still pending afterwards.
- Not run: the full suite, a live worker, any provider traffic, a coverage measurement. Not deployed.
- Limitations: no caps for `deezer`, `apple`, `wikipedia` are approved and none are in `compose.yaml`; album reviews wait for K4; a cap counts the first request only (the Apple page fetch follows redirects uncounted); the temporary "library tracklist first" in `discovery/search/album_page.py` stays until a measurement.

## 2026-11-17 — Server efficiency K3 part 1: worker prefetch of owned artist and album page rows (merged, off by default)

- PR [#1168](https://github.com/abucalip/navi-librarian/pull/1168), squash `7f86842b`, head `e1dc9f29`, merged 2026-11-17 10:53 UTC (GitHub confirms `MERGED`).
- What changed: `app/services/owned_prefetch.py` is a worker scheduler entry (`owned_prefetch`, before `similar_precompute`). It walks owned artists and albums one of each in turn (50 newest additions first, then by listens) through the page routes' own `artist_page` and `album_sections` with a worker-built network, so it fills the same discovery search-cache and ListenBrainz popularity rows under the same keys. `app/services/prefetch_state.py` holds the caps, the counting `Spend` (a request past a cap or to an unnamed provider is refused before it is sent), per-date spent counts, cursors and coverage in the knowledge store's `meta`. `/api/diagnostics/runtime` gains `prefetch`. `compose.yaml` passes `OWNED_PREFETCH_BUDGETS` to the worker; empty means off. `navidrome_server.py` untouched.
- Behaviour: Last.fm and Discogs without a cap are switched off for the run; a reached cap ends the run and the cut-short entity is retried next day; a refusal for an unnamed provider only fails that source (a review caught a version that froze the walk on one entity). Run limit one hour, one pass per list.
- Owner decision (2026-11-17): caps `musicbrainz=600,listenbrainz=300,lastfm=600`, Discogs off, approved. Not yet set anywhere; deployment is paused.
- Tests run: `pytest` on `test_owned_prefetch` (18 new), `test_worker_schedule`, `test_runtime_metrics`, `test_musicbrainz_gate_boundary`, `test_app_legacy_import_boundary`, `test_worker_heartbeat`, `test_worker_shutdown`, `test_worker_lock`, `test_worker_metadata_prune`, `test_insights_refresh_schedule`, `test_similar_precompute_schedule`: 96 passed, 5 subtests. `check_lint_changed.py --base origin/main`: 0 new findings.
- CI: six checks on `e1dc9f29` pending at merge and still pending afterwards.
- Not run: the full suite, M2, a live worker, any provider traffic, a coverage measurement. Not deployed.
- Limitations: Deezer, Apple and Wikipedia namespaces (album links, details, year, description, artist image) are part 2 and need their loaders extracted from `app/api/metadata.py` and `persistent_metadata.attach` in the worker; album reviews wait for K4. `runtime_metrics` labels Last.fm's API host `other`; the prefetch counts it as `lastfm`.

## 2026-11-17 — Server efficiency K2 part 2: stale-while-revalidate for artist and album page provider rows (merged)

- PR [#1167](https://github.com/abucalip/navi-librarian/pull/1167), squash `1fbb61c4`, head `8c5f9585`, merged 2026-11-17 10:39 UTC (GitHub confirms `MERGED`).
- Evidence for the scope: a timestamp match of the K1 rerun's 17 expired artist and album page misses against both stores. The rewritten rows were discovery search-cache rows in `navidrome_discovery.sqlite3`: 12 ListenBrainz top recordings, 12 Last.fm album lists, 5 tracklists, 8 empty Discogs-style or MusicBrainz-tag answers. They were not metadata-cache rows behind `navidrome_server.py`'s `cache_get` callables, as the plan had assumed; ListenBrainz popularity did not expire. `navidrome_server.py` is unchanged.
- What changed: `discovery/search/cache.py` gains `read_cached_state` and `read_or_revalidate` (`read_cached` unchanged). A row past its TTL and under 10 times it is served, and one refresh runs the caller's own fetch-and-store with a fresh 20 s budget (`refresh_budget`), so the request's spent deadline cannot block the write; a failed refresh writes nothing. Applied to `_cached_records` (MusicBrainz artist lookup and studio albums, Last.fm album lists), the seed artist's tags and styles, top songs (both sources) and `race_tracks`. `ArtistNetwork.refresh_submit` is set only by `app/api/search.py::artist_network_for`, to `stale_refresh.DISCOVERY_REFRESHER` (a second pool, 2 threads, 32 pending). The owner confirmed the 10-times-TTL rule after the PR: 10 days for 24 h rows, 70 days for tracklists, 300 days for tags and styles, 10 h for empty answers.
- Tests run: `PYTHONPATH=tests .venv/bin/python -m unittest` on `test_discovery_stale_rows` (new, 21), `test_discovery_search_album_page`, `_artist_sections`, `_genre`, `_similar_precompute`, `_top_songs`, `_similar`, `_providers`, `test_similar_precompute_schedule`, `test_stale_while_revalidate`, `test_api_search_routes`, `test_discovery_store_prefix_delete`: 290 OK. Lint: 8 files, 0 new findings. Full suite, M2 warm-then-expired scenario and live check not run.
- CI on `8c5f9585` at merge: `container-smoke`, `lint-changed` and `validate-release-workflow` passed; `compile`, `test-and-build` and `validate-container` pending.
- Limitations: similar-artist records, candidates' tag lookups, the search and genre pages and the worker precompute keep today's expiry. Most expired Last.fm album lists in the rerun were 12 to 16 days old, past 10 times their 24 h TTL, so they still wait. No response field states age. Not deployed.

## 2026-11-17 — Server efficiency K2 part 1: stale-while-revalidate for album reviews and links (merged)

- PR [#1166](https://github.com/abucalip/navi-librarian/pull/1166), squash `624c9362`, head `a7191d0e`, merged 2026-11-17 09:59 UTC (GitHub confirms `MERGED`).
- What changed: the album review list (`album-reviews`), each outlet's own answer (`album-review-source`), album links (`album-links`) and the Apple album page address (`apple-album-url`) are served for up to 70 days past their TTL. One background refresh runs the same lookup on `app/services/stale_refresh.py`: 2 threads, one refresh per key, at most 32 pending, overflow dropped. A failed refresh keeps the stale value and writes nothing. An answer built from a stale input stays in memory for 10 minutes and is never stored. `MetadataCache.get_with_age` is new (`get` is unchanged); it is attached in `app/main.py` through `persistent_metadata.read_with_age`. Other namespaces keep today's expiry. `navidrome_server.py` is unchanged.
- Evidence for the scope: a timestamp match of the K1 rerun records against the rows they rewrote. The expired album-links misses were the `apple-album-url` row (7-day TTL), and the expired review misses were outlet "no review" rows (3-day TTL), not the list row.
- Tests run: `tests/test_stale_while_revalidate.py` 20 OK; 8 cache and metadata modules 98 OK; `test_fallback_artwork` and `test_api_search_routes` 60 OK. A wiring smoke check (`app.main` on a scratch data directory, write then `read_with_age`) returned the value and its age. Lint: 7 files, 0 new findings. Full suite, M2 warm-then-expired scenario and live check not run, so the acceptance criterion is not verified end to end.
- CI on `a7191d0e` at merge: `container-smoke`, `lint-changed`, `validate-container` and `validate-release-workflow` passed; `compile` and `test-and-build` pending.
- Limitations: K2 part 2 (artist and album page ListenBrainz, MusicBrainz, Discogs and Deezer rows, read through the `cache_get` callables that `navidrome_server.py` hands out) is not started. Album links still wait on Deezer no-match answers until K5. The Guardian tag row, album description and album details are not covered. No response field states age. Several albums with stale outlets can fill the 32-slot queue, so some refreshes are dropped and retried later. Background refreshes finish after their request, so a K1-style rerun needs a quiet window before reading totals. Not deployed.

## 2026-11-17 — Server efficiency K1 rerun on an aged cache (documentation)

- The owner approved copying the live stores and the provider traffic. The live stores were copied with the SQLite backup API inside the running `discair` container, read only; the temporary copy was removed. The copy went to `local-test/data-live`, outside the repo; it holds credentials. 69% of 48,245 metadata-cache rows were older than 7 days.
- `main` `f8f0c191` served it on port 8092 (web only, no reload, slskd unset, sandboxed folders); the server was stopped afterwards. `scripts/efficiency_inventory.py --warm-runs 1 --quiet-seconds 20 --max-provider-requests 1000 --data-dir local-test/data-live` was run over 70 new targets picked from aged rows (`local-test/k1r-targets.json`). The session made 537 provider requests; quiet windows showed 0 calls. Output: `local-test/k1r-session.json`.
- Result: on first view, 41 of 139 requests with a provider call (29%) were expired misses, accounting for 132 of 498 provider requests and 77 s of 319 s wall time. Owned album reviews were the largest cost (11 requests, about 4.2 s each); album links, the artist page and the album page followed. On the repeat pass, 19 of 230 requests had a provider call.
- Decision recorded in `docs/plans/efficiency.md`: K2's evidence gate is met and opening it is recommended; the owner decides, including the maximum staleness for reviews.
- No code changed and no tests run (documentation only). Not deployed.
- Owner decisions, same day:
  - K2 is opened, scoped to album reviews, album links, the album page's stored metadata and the artist page's provider rows.
  - Maximum staleness for album reviews is 70 days.
  - K4 (review-outlet failure negative cache) and K5 (Deezer/Apple no-match negative cache) are approved.
  - Recorded in `docs/plans/efficiency.md` and ACTIVE_WORK section 2p. Work is deferred to later sessions.

## 2026-11-17 — Server efficiency C3, C2, R3 live check and K1 (merged)

- All five merged by squash at the owner's instruction without waiting for CI; GitHub confirms `MERGED`. C3, C2, R3 and K1's script were written by subagents (Sonnet, medium effort), the #1163 follow-up and K1's analysis in the parent session; every diff reviewed before merge. Not deployed.
- C3, PR [#1161](https://github.com/abucalip/navi-librarian/pull/1161), squash `11798294`, head `58ad928b`: `compose.yaml` `init: true` and healthchecks (web: public `/api/auth/status`; worker: `python -m app.services.worker_heartbeat`, stamp max age 300 s); heartbeat thread writes only while `worker-schedule` and `worker-schedule-discovery` are alive. Tests: `pytest tests/test_worker_heartbeat.py tests/test_worker_shutdown.py tests/test_worker_lock.py tests/test_worker_schedule.py` 36 passed (re-run on the head in review); compose YAML parsed. Not run: `docker compose up`, `container-smoke`.
- C2, PR [#1162](https://github.com/abucalip/navi-librarian/pull/1162), squash `6ccb6bcd`, head `4571f28f`: removed `library_overview`, `search_music`, `get_album_details`, `find_missing_mbids`, `_lastfm_cached_call`, `_discovery_settings_init`, imports `scan_missing_mbids` and `mutagen.File`, two adapter-only tests (134 lines). Review re-searched every removed name on the head: only archived docs and comments. Tests: 108 passed, 34 subtests (music tag audit, Last.fm client, server size guard, discovery refresh guard, settings, discovery and acquisition routes); `import navidrome_server` ok; lint 0 new findings.
- C2 follow-up, PR [#1163](https://github.com/abucalip/navi-librarian/pull/1163), squash `652e72f7`: removed `library_overview_payload`, `search_result_payload`, `album_details_payload`, their re-exports and tests (139 lines). Tests: `pytest tests/test_navidrome_client.py tests/test_navidrome_cover_art.py` 21 passed, 13 subtests; lint 0 new findings.
- R3 live check, PR [#1164](https://github.com/abucalip/navi-librarian/pull/1164), squash `34687dc1`, head `7b0f8844`: `scripts/gate_spacing_check.py` (real web and worker, fake MusicBrainz and Navidrome via a scratch `sitecustomize.py`, non-loopback hosts refused). 120 s run: 129 MusicBrainz requests (web 80, worker 49); slot starts min 1.0999999 s, 0 under 1.1 s; arrivals min 1.086 s, 67 of 128 under 1.1 s by at most 13.7 ms. Owner kept 1.1 s; R3 acceptance wording corrected. Tests: `pytest tests/test_gate_spacing_check.py` 3 passed. The squash message carries the session's attribution (the branch commit named another model).
- K1, PR [#1165](https://github.com/abucalip/navi-librarian/pull/1165), squash `1d787c7c`, head `02b29252`: `scripts/efficiency_inventory.py`, `Accept` header option in `scripts/efficiency_baseline.py`, results and decision in `docs/plans/efficiency.md`. Session on port 8091 (copied store), 70 targets, 1 cold + 5 warm passes, 1,135 provider requests (cap 1,500). Warm misses: not cached 103, failure 58, never fetched 41, expired 1. K2 deferred, K3 confirmed and narrowed. Tests: `pytest tests/test_efficiency_inventory.py tests/test_efficiency_baseline.py` 19 passed; lint 0 new findings. The subagent was stopped by mistake mid-session; the session script finished on its own, and the 8091 server it started was stopped afterwards (the 8090 instance was left running).
- Full suite not run for any of the five. CI on the five merge heads still to be checked.

## 2026-11-17 — Server efficiency W3, C1, S2 and S1 report (merged)

- All four merged by squash at the owner's instruction without waiting for CI; GitHub confirms `MERGED`. Each was implemented by a subagent and the diff reviewed before merge. Not deployed.
- C1, PR [#1157](https://github.com/abucalip/navi-librarian/pull/1157), squash `38b2e24e`, head `c025b4b7`: removed `read_only_command_policy.py`, `get_server_source` with `server_source_redaction.py`, the `musicbrainz_rating_client.py` shim (importer repointed under the same name) and `Dockerfile-E`, plus their tests and `COPY` entries. Tests: `import navidrome_server`; `tests/test_musicbrainz_rating_client.py` 5 passed. Lint 0 new findings. CI at merge: `container-smoke`, `lint-changed`, `validate-container`, `validate-release-workflow` passed; `compile`, `test-and-build` pending.
- S2, PR [#1158](https://github.com/abucalip/navi-librarian/pull/1158), squash `340a73b1`, head `5aba3789`: `scripts/backup_stores.py` copies the eight stores with the SQLite backup API into a 0700 directory, copies 0600, integrity-checked; restore procedure in `docs/DEPLOYMENT.md`. Tests: `tests.test_backup_stores` 11 OK. Lint 0 new findings. Not run against the live host. Not covered: `app_auth.key`, artwork image files, music.
- S1 report, PR [#1159](https://github.com/abucalip/navi-librarian/pull/1159), squash `3d24c072`, head `2e03a8ec`: `scripts/store_size_report.py`, read-only (`immutable=1` when no `-wal`, else `mode=ro`; skips `-wal` without `-shm`). Tests: `tests.test_store_size_report` 11 OK. Lint 0 new findings. First run on `~/discair-mb-test` (copy) recorded in `docs/plans/efficiency.md` section 13 (`c093b1ab`).
- W3, PR [#1160](https://github.com/abucalip/navi-librarian/pull/1160), squash `c817f703`, head `a007e174`: `app/services/discovery_schedule.py` (`discovery_lists`, `lens_lists`, hourly, thread `worker-schedule-discovery`); `discovery/refresh_guard.py` wraps scheduled, manual and read-triggered list refreshes in `run_job` per list with a 60 s heartbeat and per-process recovery; `navidrome_server.py` scheduler loop and `lens_service` daily loop deleted (`navidrome_server.py` +23 −77, now 2,382 lines); `docs/DEPLOYMENT.md` gains "Background worker". Tests: 242 passed across 21 focused files (pytest), 53 OK under unittest for the new and changed files. Lint 0 new findings in 13 files. Not done: the 48-hour cadence run; live worker. Limitations: listening-profile refresh unguarded (worker-only); deploy web and worker from the same image.
- Full suite not run for any of the four. CI on the four merge heads still to be checked.

## 2026-11-17 — Server efficiency W2: similar-artist precompute moved to the worker (merged)

- PR [#1156](https://github.com/abucalip/navi-librarian/pull/1156), branch `efficiency-w2-similar-precompute` from `main` at `33a7f3ed`, squash `3e518379`, head `39d38d78`, merged 2026-11-17 01:50 UTC (GitHub confirms `MERGED`). Not deployed.
- New `app/services/similar_precompute.py`: `run_once(librarian, stop)` builds the owned data synchronously (snapshot lists, song inventory, stored identities; no shared index, no identity pass), runs `run_precompute` from `similar-precompute-cursor` with `stop`, and returns `worker_schedule.NOT_READY` when the library cannot be read. It owns `snapshot_lists`, `cache_reader` and `network_kwargs` (shared with `search.artist_network_for`), so the worker imports no route module for it. Logs artists, songs, build seconds and peak RSS per run.
- `app/worker_schedule.py`: `NOT_READY` return is not recorded; the entry waits `Entry.retry_seconds` (in memory, clamped against a clock step back). `app/worker.py` registers `similar_precompute` last (daily, retry 1800 s, no legacy key).
- `discovery/search/similar_precompute.run_precompute` takes `stop`: checked before each artist, passed as `cancelled`; an artist cut short by shutdown does not advance the cursor.
- `app/api/search.py`: `start_similar_precompute`, the loop, step and once functions removed. `app/main.py` warms the web owned index once instead. `compose.yaml` worker gains `LASTFM_API_KEY` (the Last.fm key default comes from the environment).
- Behaviour changes: the done day is persisted (a restart no longer repeats it; the first start after upgrade runs it); insights can wait behind a long run; Last.fm, ListenBrainz and Discogs pace per process, so browsing during a run can double their rate; the worker build has no 10% song-drop check; a mixed-version rollout would run the precompute twice that day.
- Tests run (unittest): 195 OK across `test_similar_precompute_schedule` (rewritten), `test_worker_schedule`, `test_discovery_search_similar_precompute`, `test_worker_shutdown`, `test_worker_lock`, `test_worker_metadata_prune`, `test_api_search_routes`, `test_mcp_retirement`, `test_musicbrainz_gate_boundary`, `test_android_contract_fixtures`, `test_auth_routes_integration`, `test_dep_map`, `test_intelligence_musicbrainz_auto_fill`, `test_runtime_metrics`, `test_insights_refresh_schedule`, `test_artwork_loading_ui_contract`, `test_api_identity_routes`; `test_api_genre_routes` 8 OK via `discover` (direct module run hits a pre-existing `gate_fakes` import error, same on `main`). Lint changed files: 0 new findings in 9 files. Not run: full suite, M2, live worker. Index build measured on synthetic data only (4.5 s, 69 MiB traced peak at 1,000 artists / 100,000 songs).
- CI at merge: `validate-container` passed; `compile`, `container-smoke`, `lint-changed`, `test-and-build`, `validate-release-workflow` on `39d38d78` still pending (runner backlog).

## 2026-11-17 — Server efficiency W1: table-driven worker scheduler (merged)

- PR [#1155](https://github.com/abucalip/navi-librarian/pull/1155), branch `efficiency-w1-scheduler` from `main` at `b3a0143e`, squash `87afd87e`, head `21b4805d`, merged 2026-11-17 01:33 UTC (GitHub confirms `MERGED`). Not deployed.
- New `app/worker_schedule.py` (efficiency section 6.2): `Entry(name, due, run)`, `interval()` and `daily()` (local date) due rules, and a `Scheduler` that runs due entries one at a time in a fixed order on one `worker-schedule` thread (60 s tick), persisting `schedule:<name>` in the store's `meta`. A run that returns or raises is recorded (a raise is logged by type only); a run that returns with `stop` set is not; `stop` is checked before each entry. The module imports no job module.
- `app/worker.py::schedule_entries` registers `daily_maintenance` (R1 job-history prune and P3 metadata-cache prune), then `insights_refresh` (`insights_refresh.is_due`: lens on and `CHECK_SECONDS` elapsed). The insights entry falls back to R5's `insights_refresh.last_run_at` until it writes its own key, so the first start after the upgrade does not re-run the refresh. `insights_refresh._loop`, `start`, `_seconds_until_due`, `_record_run` and `worker.PRUNE_SECONDS` removed. Auto fill and the metrics save keep their own threads.
- `GET /api/diagnostics/runtime` adds `schedule: {name: last_run}` (additive).
- Behaviour changes: daily maintenance runs at the first start and then once per local day (was only after 24 h of uptime); a failing insights refresh is recorded and waits its 6 h window across restarts (was an unrecorded in-memory wait).
- Tests run (unittest, 90 OK): `tests.test_worker_schedule` (new), `tests.test_insights_refresh_schedule` (R5 cases ported to `is_due` and the scheduler), `tests.test_insights_refresh`, `tests.test_insights_refresh_status`, `tests.test_worker_lock`, `tests.test_worker_shutdown`, `tests.test_worker_metadata_prune`, `tests.test_intelligence_musicbrainz_auto_fill`, `tests.test_runtime_metrics`. Lint changed files: 0 new findings in 10 files. Not run: full suite, M2, live worker.
- CI at merge: all six checks on `21b4805d` (`compile`, `container-smoke`, `lint-changed`, `test-and-build`, `validate-container`, `validate-release-workflow`) were still pending (runner backlog; `main` runs for `ae64633b`, `4e31c325` and `b3a0143e` also still queued).
- Limitations: only two entries so far; W2 and W3 move the similar-artist precompute, lens refresh and discovery scheduler in.

## 2026-11-17 — Server efficiency P5: inventory snapshot and ingest consolidation (merged)

- PR [#1154](https://github.com/abucalip/navi-librarian/pull/1154), branch `efficiency-p5-inventory-snapshot` from `main` at `ae64633b`, squash `4e31c325`, head `76d92a74`, merged 2026-11-17 01:22 UTC (GitHub confirms `MERGED`). Not deployed.
- (a) F9: `AlbumInventorySnapshot` in `discovery/library_snapshot.py`, keyed by the `getScanStatus` marker (`lastScan`, `count`): no call within 30 s of the last check, one `getScanStatus` after that, re-paged when the marker changes or the copy is 5 minutes old (the gaps path reads `playCount`, `played`, `starred`, `userRating`, which change without a scan). Failures, a running scan and an unreadable marker are not cached; callers get copies. Used only by `app/api/knowledge.py::_play_records`. The worker callers, lens refresh and candidate gathering read much less often than every 5 minutes and are unchanged; the owned search index is unchanged.
- (b) F10 decision: `insights_refresh._ingest_step` kept, reason in its docstring and in `docs/plans/efficiency.md` P5 (auto fill only baselines the existing library and re-ingests a seen album only when it gains a release MBID; `_ingest_step` records those albums and re-records MBID artists every 7 days; bounded to 40 artists per 6-hour refresh while a provider lens is on).
- (c) F10: `app/services/library_enrich.py::find_artist_id`: store lookup of the artist entity's Navidrome id, confirmed with one `getArtist`, falling back to the full `getArtists` index on a miss, a changed id or a Navidrome error.
- Tests run (unittest, 96 OK): `tests.test_album_inventory_snapshot` (new, 10), `tests.test_api_knowledge_paths_route` (new route test: two gaps requests make one `getScanStatus` and one inventory read), `tests.test_library_enrich_find_artist` (new, 5), `tests.test_discovery_album_inventory`, `tests.test_discovery_library_snapshot`, `tests.test_update_requests`, `tests.test_intelligence_musicbrainz_auto_fill`, `tests.test_insights_refresh`, `tests.test_insights_refresh_schedule`, `tests.test_insights_refresh_status`. Lint changed files: 0 new findings in 7 files. Not run: full suite, M2 live baseline.
- CI at merge: `compile`, `container-smoke`, `lint-changed`, `test-and-build`, `validate-container` and `validate-release-workflow` on `76d92a74` were all still pending. P4's checks on `a05e802e` were still pending at this entry too.
- Limitations: the snapshot is not keyed by Navidrome connection (a changed server URL shows within 5 minutes or at the next marker change); the gaps page can show play data up to 5 minutes old.

## 2026-11-17 — Server efficiency P4: bounded single-flight cache for the metadata routes (merged)

- PR [#1153](https://github.com/abucalip/navi-librarian/pull/1153), branch `efficiency-p4-layered-cache` from `main` at `77019429`, squash `a05e802e`, head `2ba8438f`, merged 2026-11-17 01:13 UTC (GitHub confirms `MERGED`). Not deployed.
- Fixes F8. New `app/services/layered_cache.py` (`LayeredCache`: bounded LRU, 2,000 entries per namespace; reads `persistent_metadata` when given a store key; single-flight per key, waiters share the leader's answer or exception; `Loaded(value, memory_ttl, persist)` decides caching per answer). The eight dicts in `app/api/metadata.py` moved onto it one commit each; keys, store keys, TTLs, negative and partial TTLs and the not-cached cases are unchanged.
- Tests, with `python -m unittest`: new `test_metadata_cache_semantics` (17; 16 passed against the old dicts first, then unchanged after the migration; one route test, two concurrent identical `artist_image` requests make one provider call), new `test_layered_cache` (11, run 5 times), plus `test_metadata_routes`, `test_artwork_retry`, `test_fallback_artwork`, `test_metadata_persistent_cache`, `test_album_links`, `test_metadata_album_info_reviews`, `test_discovery_search_album_page`, `test_discovery_search_artist_sections`, `test_artist_bio_service`: 167 OK on `b03913f0`. The full unit suite was not run locally; CI runs it on the head.
- Lint: `scripts/check_lint_changed.py --base origin/main`, 7 files checked, 0 new finding groups.
- CI: at the time of this entry all six PR checks were pending on `b03913f0` and again on the new head `ae239d45`; the `main` runs for `77019429` and `1cd9fb6e` were still queued.
- Year cache (the owner asked for it after the first push): `integrations/musicbrainz/album_year.py::year_cache` is now an LRU dict of at most 2,000 pairs (`YEAR_CACHE_MAX_ENTRIES`); lookups, TTLs, the gate and the refusal rule unchanged; not a `LayeredCache` because `integrations/` does not import `app/`. Tests on `2ba8438f`: `test_musicbrainz_album_year` 14 OK (3 new), then `test_metadata_routes`, `test_metadata_persistent_cache`, `test_metadata_cache_semantics`, `test_musicbrainz_gate_boundary` 49 OK; lint 9 files, 0 new. A first run of the new bound test forgot to stub the gate lane and was stopped after about 2 minutes: it made no network request (the fetch was a fake), but it took real slots in the local `provider_gate.sqlite3` of the checkout.
- Limitations: M2 not run (the step bounds memory and coalesces concurrent calls; warm timing is unchanged by design); expired entries are removed on read or eviction, not swept; the bound is per namespace (8 × 2,000).
- CI at merge: all six checks on `2ba8438f` were still pending; no result is recorded yet.
- Next action: check the six checks on `2ba8438f` (or `a05e802e`) and record the result; if one fails, open a fix PR.

## 2026-11-17 — Server efficiency P3: fix the legacy metadata cache

- PR [#1152](https://github.com/abucalip/navi-librarian/pull/1152), branch `efficiency-p3-metadata-cache` from `main` at `0866e3a1`, head `fa12f1ca`, squash `1cd9fb6e`, merged 2026-11-17 00:43 UTC (GitHub confirms `MERGED`). Not deployed.
- Fixes F7. `metadata_cache.py`: one connection per thread; the table and a `cached_at` index are created once per process per file (keyed by pid and inode); WAL with `synchronous = NORMAL`; SELECTs read fully; `prune(older_than_seconds, batch=500)` deletes in committed batches. `app/worker.py`: `_daily_maintenance` runs the job-history prune and the cache prune (400-day cutoff, `PRUNE_AFTER_SECONDS`), each isolated.
- Tests, with `python -m unittest discover -s tests -p ...`: `test_metadata_*.py` 66 OK (new `test_metadata_cache_lifecycle.py` 9, new `test_worker_metadata_prune.py` in the `test_worker_*` run); `test_worker_*.py` 14 OK; `test_musicbrainz_rating_client.py` 6 OK. The full unit suite was not run locally; CI runs it on the head.
- Lint: `scripts/check_lint_changed.py --base origin/main`, 4 files checked, 0 new finding groups.
- Local micro-timing (temp DB, 200 rows, median of 2,000 operations): `get` 130 µs before, 12 µs after; `set` 533 µs before, 40 µs after. M2 does not cover this file.
- CI at merge: all six checks on `fa12f1ca` were still pending (`compile`, `container-smoke`, `lint-changed`, `test-and-build`, `validate-container`, `validate-release-workflow`); the P2 runs on `main` had been queued since 00:33 UTC. The owner merged before they finished. Their results are not recorded here yet.
- Limitations: the file does not shrink after a prune (SQLite reuses free pages; no VACUUM); the index is built on the first operation after start, which is slow on a large existing file; WAL adds `-wal` and `-shm` files, so backups must use the SQLite backup API.
- Next action: check the six checks on `1cd9fb6e` and record the results; then the owner picks the next Phase P step (P4 or P5, both Sonnet, Medium).

## 2026-11-17 — Server efficiency P2: reuse the Navidrome HTTP client

- PR [#1151](https://github.com/abucalip/navi-librarian/pull/1151), branch `efficiency-p2-navidrome-client-reuse` from `main` at `8e782faa`, head `d1a8042a`, squash `594b5ae2`, merged 2026-11-17 00:32 UTC (GitHub confirms `MERGED`). Not deployed.
- Fixes F6. `integrations/navidrome/client.py`: `api_call` and `cover_art` share one process-wide `httpx.Client`, built lazily under a lock (timeout 30 s, `follow_redirects=False`, `max_keepalive_connections=10`, `keepalive_expiry=30`). A caller-supplied `client_factory` keeps the old per-call client. `navidrome_server.py` is untouched.
- Tests, with `python -m unittest`: `tests.test_navidrome_client` and `tests.test_navidrome_cover_art`, 26 OK. The new `SharedNavidromeClientTests` cover: one shared client across calls, cover art and calls sharing one client, the factory bypass, the limits, eight threads on first use, and a real loopback server showing one TCP connection for two calls. Not run: the full suite (agents do not run it).
- Lint: `scripts/check_lint_changed.py --base origin/main`, 2 files checked, 0 new finding groups.
- Loopback micro-timing (scratchpad, not committed), 300 calls per round, one threaded server: median 6.21 ms before, 0.46 ms after; 300 connections before, 1 after. Not measured: the LAN Navidrome server and M2.
- CI at merge: `validate-container` passed. `compile`, `lint-changed`, `container-smoke` and `test-and-build` were still queued or pending. The owner merged before those finished, at the owner's request not to wait for slow CI. Their results are not recorded here.
- Limitations: the shared client keeps a cookie jar (per-call clients never sent cookies back; Navidrome uses token parameters); a request racing a Navidrome restart can fail once; Navidrome calls are counted under `other` in runtime metrics.
- Next action: check the four pending checks on `d1a8042a`; then the owner picks the next Phase P step.

## 2026-11-17 — Server efficiency P1: cache settings reads

- PR [#1150](https://github.com/abucalip/navi-librarian/pull/1150), branch `efficiency-p1-settings-cache` from `main` at `ace556d9`, head `324001de`, squash `713c0949`, merged 2026-11-17 00:23 UTC (GitHub confirms `MERGED`).
- Fixes F5. `settings/persistence.py` keeps one long-lived read connection and re-reads only when `PRAGMA data_version` changes or after a local write. `initialize()` runs once per file and process; the connection reopens when the file's inode or the process id changes. `read()` returns a deep copy (the plan said shallow; the dict holds lists). Writes keep their own short connection. The migrations and `chmod` run on reload only.
- Tests run, with `python -m unittest`:
  - `test_settings_persistence` (10 new tests), `test_auth_settings`, `test_quality_priority`, `test_settings_routes`, `test_service_settings`, `test_discogs_settings`: 74 OK.
  - `test_app_auth`, `test_app_login_middleware`, `test_auth_configuration`, `test_auth_cookie`, `test_auth_routes_integration`, `test_auth_secret`, `test_auth_settings`, `test_login_ui_contract`, `test_api_identity_routes`, `test_discovery_save_bookmark`: 74 OK.
  - Lint changed files: 0 new findings.
  - Under pytest, `test_service_settings.py` and `test_discogs_settings.py` show 4 collection errors (production `test_*` functions imported from `settings/service.py`). The same errors appear on unchanged `main`.
- Timing on a temp DB with 40 saved keys, 2,000 reads: median 313 µs before, 43 µs after.
- CI at merge on `324001de`: `lint-changed`, `container-smoke` and `validate-container` passed; `compile` and `test-and-build` were pending, check them.
- Limitations:
  - M2's store counters do not cover the settings file, so M2 cannot show this change.
  - `DISCOVERY_DB` is shared with other tables, so any commit to that file invalidates the cache (correct, but it lowers the hit rate; not measured).
  - No live run; not deployed.

## 2026-11-17 — Server efficiency M3: process-local state inventory

- PR [#1149](https://github.com/abucalip/navi-librarian/pull/1149), squash `9cb57a1a`, head `7ad0677f`, merged 2026-11-17 00:06 UTC (GitHub confirms `MERGED`). CI at merge: `validate-container` passed; `compile`, `lint-changed`, `container-smoke` and `test-and-build` were pending. Closeout (this entry and the status update) committed directly to `main`, as the owner asked.
- Branch `docs/efficiency-m3-state-inventory` from `main` at `cc14fb51`. Changes: `docs/plans/efficiency.md` (new Appendix A: threads and pools, caches and registries, locks in `navidrome_server.py` and route modules, process-wide patches, findings A5.1 to A5.5, cross-references from W2, W3 and K1; M3 status; evidence log), `docs/PROJECT_STATUS.md`, this log.
- Method: grep for `threading.Thread(`, `ThreadPoolExecutor(`, `threading.Lock/RLock/Event/Semaphore(`, `lru_cache` (none in server code) and module-level mutable containers in the server packages and `navidrome_server.py`; each hit read. Constant tables excluded.
- Open item resolved (2026-11-17): `navidrome_server._DISCOVERY_ACQUIRE_ACTIVE` is written by `acquisition/request_coordinator.py` and `acquisition/track_service.py`, both under `_DISCOVERY_IMPORT_TRANSITION_LOCK`. Appendix A updated; code unchanged.
- Tests run: none. Documentation only; no code changed. Not run: any test, lint or full suite. Not deployed.
- Merged through a PR, as the owner asked.

## 2026-11-17 — Server efficiency M2: knowledge-route and full baseline

- Branch `efficiency-m2-knowledge-baseline` from `main` at `5437669c`. Changes: `scripts/efficiency_baseline.py` gains `--knowledge-type` (default `release_group`, unchanged) and `build_routes(..., knowledge_type)`; `tests/test_efficiency_baseline.py` gains `test_build_routes_knowledge_type_is_configurable`; `docs/plans/efficiency.md` (M2 status and evidence log) and `docs/PROJECT_STATUS.md`.
- Store: copy of the owner's ingested knowledge store, served on a second local instance (port 8091, no reload, copy in `local-test/data-mb`). The owner's store was not opened by a server. The 8090 instance was not changed.
- Tests run: `pytest tests/test_efficiency_baseline.py`, 10 passed; `python -m unittest tests.test_efficiency_baseline`, 10 passed (CI runner). `scripts/check_lint_changed.py --base origin/main` reported no changed Python files because the changes were uncommitted at the time; pylint on the two files still to run. Not run: full unit suite (not allowed by CLAUDE.md), any browser check (no UI change).
- Live measurement (knowledge routes only, `type=release`, 20 runs after an unmeasured warm-up): `knowledge_connections` 200, median 177.7 ms, p95 178.6 ms, no outbound calls; `knowledge_paths_album_gaps` 200, median 992.6 ms, p95 1336.2 ms, Navidrome 4.0 requests per run, no provider calls.
- Incident: a one-run probe of the full script made provider calls on the artist page (ListenBrainz 3, MusicBrainz 5) because the copied artist caches were cold; this was not owner-approved and was not checked before the run. No further provider traffic. The artist and album routes are not part of this baseline.
- Full seven-route baseline (owner approved provider traffic): 20 measured runs after a 2-run warm-up, all routes 200; album page 24 ms median and no outbound calls; artist page 421 ms with one ListenBrainz popularity call per request (F13); knowledge connections 178 ms; album gaps 1048 ms with 4 Navidrome calls per request. Full table in `docs/plans/efficiency.md` section 13.
- CI: not yet reported on the PR head at time of writing. Limitations: one machine, one artist, one album, one copied store.

## 2026-11-17 — Server efficiency P6: negative caching of ListenBrainz popularity (F13)

- PR [#1148](https://github.com/abucalip/navi-librarian/pull/1148), squash `4860a3e7`, head `cc8be999`, merged 2026-11-16 23:59 UTC (GitHub confirms `MERGED`). Branch `efficiency-p6-negative-popularity` from `main` at `6593023c`. Changes: `integrations/listenbrainz/popularity.py` (negative entry `{"negative": true, "at": <time>}` for release groups a 200 answer leaves without counts; fresh for 1 h, `NEGATIVE_TTL_SECONDS`; failed requests and malformed bodies write nothing; writes through the caller's `can_cache`-gated `cache_set`; `clock` kwarg for tests), `tests/test_listenbrainz_popularity.py`, `docs/contracts/SEARCH_CONTRACT.md` §12.3, `docs/plans/efficiency.md` P6.
- Tests run: `pytest tests/test_listenbrainz_popularity.py`, 7 passed; `pytest tests/test_recommend_new_music_characterization.py tests/test_api_search_routes.py`, 67 passed. Lint ratchet `scripts/check_lint_changed.py --base origin/main` (with the project venv on PATH): 2 files, 0 new findings. Not run: full unit suite (not allowed by CLAUDE.md).
- Live check (owner-approved provider traffic): local test instance on port 8090, which had the P6 code loaded (process started 00:33:21 CET, after the last edit at 00:33:10). `scripts/efficiency_baseline.py`, artist `beatles`: 2-run warm-up (not reported) then 20 runs. Warm-up made one ListenBrainz POST on the artist page and wrote the negatives (cache: 4 negative rows). Measured: 0 ListenBrainz calls per request; Navidrome 1 per run; artist page 53.2 ms median, 75.7 ms p95. Output `local-test/baseline-f13-after.json` (outside the repo). Recorded in `docs/plans/efficiency.md` P6 and PR comment.
- A copy of the store at `/Users/hamdibaala/discair-mb-test` was served on port 8091 (`local-test/data-f13`, copy via `sqlite3 -readonly .backup`; the source was not opened by a server). That instance had no library snapshot (index unavailable), so the artist page could not run there. Knowledge routes 404 on the 8090 instance (small store) and were not measured. The 8091 instance was stopped.
- CI on head `cc8be999` at merge: `lint-changed` and `validate-container` passed; `compile`, `test-and-build` and `container-smoke` were pending when merged. Check them on `cc8be999` (open item).
- Limitations: no before run on the same artist, so the before/after comparison uses the 2026-11-17 baseline on another artist; the measured artist had few uncached groups; one machine, one artist; not deployed.

## 2026-11-16 — Server efficiency M2: merge of per-route attribution

- PR [#1146](https://github.com/abucalip/navi-librarian/pull/1146), squash `a3b9eafe`, head `7cf3a403`, merged 2026-11-16 23:14 UTC (GitHub confirms `MERGED`). Changes: `scripts/efficiency_baseline.py` per-route runtime attribution, `numeric_delta` counts new keys from zero, nested `web` counter parsing; `tests/test_efficiency_baseline.py` 9 passed; lint changed files 0 new findings. Docs: `docs/plans/efficiency.md` section 4 (F13), section 7 (P6), section 13 (live runs); `docs/PROJECT_STATUS.md`.
- Live runs on the local test instance (port 8090), owner-approved provider traffic: a cold pass on a second artist (artist page ListenBrainz 3, MusicBrainz 1, Navidrome 2; album page Apple 2, Deezer 1, MusicBrainz 2, Wikipedia 2, Navidrome 7), then 20 warm runs (artist page ListenBrainz 1.0 and Navidrome 1.0 per request; album page no outbound calls).
- CI on head `7cf3a403` was still pending in the PR rollup at merge; check it on `a3b9eafe`.
- Limitations: one machine, one artist and one album per run; knowledge routes measured on the 404 path only.

## 2026-11-16 — Server efficiency M2: per-route Navidrome attribution

- Branch `efficiency-m2-route-attribution` from `main` at `0b9d3722`; PR opened (not merged). Changes `scripts/efficiency_baseline.py` (per-route runtime snapshots, `per_route_runtime` in the JSON, "Outbound per run" table column; `numeric_delta` counts new keys from zero) and `tests/test_efficiency_baseline.py`. Evidence log entry in `docs/plans/efficiency.md` section 13.
- Tests run: `.venv/bin/python -m pytest -q tests/test_efficiency_baseline.py`, 9 passed (stub server). Not run: full unit suite (not allowed by CLAUDE.md), any live instance run.
- Live run (test instance, port 8090): 20 warm runs, table and per-route attribution in `docs/plans/efficiency.md` section 13. The 2-run warm-up before it made provider calls (ListenBrainz, MusicBrainz, Apple, Deezer), which needed owner approval; the owner gave the test login.
- Fixed during the live run: the diagnostics snapshot nests counters under `web`; the first version read the top level and showed no outbound calls. The unit test now uses the nested shape.
- Limitations: one machine, one artist and one album; the knowledge routes return 404 on this instance, so they are not the real route. Background web threads are counted in the same window.

## 2026-11-16 — Server efficiency M2 follow-up: CI test fix and similar-records caching

- PR [#1144](https://github.com/abucalip/navi-librarian/pull/1144), squash `1c3d0af4`, head `c78612a1`, merged 2026-11-16 22:43 UTC. `tests/test_efficiency_baseline.py` rewritten for unittest (CI's `unittest discover` has no pytest; `compile` and `test-and-build` failed on `05963eda` and `e09a4adc`). `discovery/search/artist_sections.py` `similar_items` now caches the provider records when every provider answered, even if tag lookups were rate-limited (owner decision 2026-11-16); a failed provider still writes nothing. The old rule came from the #622 review (sections 5.2 and 8.1 applied to the whole section); the cache holds only provider records, and tags are cached on their own. Contract line in `docs/contracts/SEARCH_CONTRACT.md` and `similar_precompute.py` docstrings updated.
- Tests run: `test_efficiency_baseline` under unittest (8 OK); `test_discovery_search_similar.py`, `_similar_precompute.py`, `_artist_sections.py`, `_album_page.py` (105 passed) and `_genre.py` (32 passed). The two new similar tests fail without the fix. Lint changed files: 0 new findings. Full suite not run locally.
- CI on `c78612a1`: `container-smoke`, `lint-changed`, `validate-container` passed; `compile` and `test-and-build` pending at merge.
- Limitations: not deployed; no live run after the fix, so the drop in ListenBrainz calls is not yet measured; no warm baseline yet.


- PR [#1143](https://github.com/abucalip/navi-librarian/pull/1143), squash `05963eda`, head `c9d138d2`, merged 2026-11-16 20:15 UTC. Adds `scripts/efficiency_baseline.py` (stdlib only: logs in, reads `/api/diagnostics/runtime`, times seven fixed routes N times with wall and `Server-Timing` medians and p95, writes JSON and a table) and `tests/test_efficiency_baseline.py`. Route fixes in `9cfb05de`: the artist route needs the artist name and `id`, the album route needs the `id` query parameter.
- Tests run: `tests/test_efficiency_baseline.py`, 8 passed (against a stub HTTP server). Lint changed files: 0 new findings. Full suite not run. The script was run against a fresh local test instance (port 8090, isolated data) with the owner account from the local config; outputs are in the local test folder, not committed.
- CI: the PR rollup still showed `compile`, `container-smoke`, `lint-changed`, `test-and-build` and `validate-container` as pending at merge; no conclusion was recorded here, so check them on `05963eda`.
- Live findings (not warm-cache): the album page makes one ListenBrainz request per request (caller not yet pinned); release groups with no ListenBrainz listen data are never cached (`integrations/listenbrainz/popularity.py`, read from code, not yet seen live); about 185 s of MusicBrainz gate wait per run; the "other" counter is the LAN Navidrome server; the knowledge routes 404 on this instance because no MusicBrainz data is ingested for the test album.
- Limitations: not deployed; no warm-cache baseline yet; the knowledge routes measure the not-found path on this instance; per-route attribution was done with one request per route, not a profiler.

## 2026-11-16 — Server efficiency M1 follow-up: all httpx and urllib requests, statement timing

- PR [#1142](https://github.com/abucalip/navi-librarian/pull/1142), squash `53a8f656`, head `af5bded8`, merged 2026-11-16 (after 19:37 UTC). `install()` also patches `httpx.Client.send`, `httpx.AsyncClient.send` and `urllib.request.OpenerDirector.open`, so every httpx and urllib caller is counted without touching `navidrome_server.py`. `intelligence/store/db.py` adds `_TimedConnection`, which times `execute` and `executemany` per verb (`sql_select`, `sql_insert`, …); slow statements log verb and first table name only.
- Tests run: `tests/test_runtime_metrics.py` (focused, including the new cases). Lint changed files: 0 new findings. Full suite not run.
- CI: `container-smoke`, `lint-changed`, `validate-release-workflow` and `validate-container` passed on head `af5bded8`; `compile` and `test-and-build` had no recorded conclusion in the PR rollup at the time of this entry, and the `main` push runs were still in progress.
- Limitations: not deployed; Navidrome client (P2) not counted; cursor-level calls, `executescript` and row fetching are not timed.

## 2026-11-16 — Server efficiency M1: runtime counters and diagnostics route

- PR [#1141](https://github.com/abucalip/navi-librarian/pull/1141), squash `a1407e69`, head `7f8b8512`, merged 2026-11-16 19:34 UTC. New `app/services/runtime_metrics.py` (counters by provider from a fixed host table and outcome class, gate reservations/refusals/waits, store opens with slow >250 ms and locked logged), `MeteredClient` on `_EXTERNAL_HTTP`, observer hooks in `integrations/provider_gate.py` and `intelligence/store/db.py`, `GET /api/diagnostics/runtime` (`app/api/diagnostics.py`), worker snapshot to `meta` every 5 minutes and at shutdown.
- Tests run (focused only): new `tests/test_runtime_metrics.py` (6: host table, outcomes without URL leakage, gate waits, store opens, snapshot round trip, route 401 without login and both processes with it), `test_provider_gate.py`, `test_musicbrainz_gate_boundary.py`, `test_worker_lock.py`, `test_worker_shutdown.py`, `test_store_readonly_access.py`, four `test_metadata_*` files: all passed. Lint changed files: 0 new findings.
- CI: `container-smoke`, `lint-changed`, `validate-release-workflow` and `validate-container` passed; `compile` and `test-and-build` were still in progress at merge.
- Limitations: not deployed; no live two-process run; Navidrome client (P2) and clients outside `_EXTERNAL_HTTP` not counted; store counters cover opens, not statements.

## 2026-11-16 — Server efficiency R5: worker loop lifecycle

- PR [#1140](https://github.com/abucalip/navi-librarian/pull/1140), squash `034341ea`, head `efd564d4`, merged 2026-11-16 19:08 UTC. The insights refresh loop stores the time of each completed refresh in `meta` (`insights_refresh.last_run_at`) and waits out the rest of `CHECK_SECONDS` on a restart; a stored time ahead of the clock counts as due. `refresh_provider_lenses` takes an optional `should_stop`, checked before each provider request and ended like an exhausted budget; the Navidrome ingest step checks it per artist. Loops wait on the stop event; the worker joins both loop threads against one 25 s deadline while it still holds `worker.lock`. Compose sets `stop_grace_period: 30s`. Module docstring corrected. A run cut short by shutdown is not recorded.
- Deviation recorded in the PR: the due time uses `meta`, not `job_runs.last_good`, because a budget-stopped provider tick is recorded `succeeded` (`work()` always returns True), so `last_good` would count it as done anyway; the plan's premise that it ends `queued` was wrong.
- Tests run (focused only): `tests/test_insights_refresh_schedule.py` (new), `tests/test_worker_shutdown.py` (new), `test_worker_lock.py`, `test_insights_refresh.py`, `test_insights_refresh_status.py`, `test_insights_provider_runtime.py`, `test_intelligence_musicbrainz_auto_fill.py`: 75 passed. Lint `check_lint_changed.py --base origin/main`: 6 files, 0 new finding groups. Full suite not run.
- CI: `validate-release-workflow`, `container-smoke`, `lint-changed` and `validate-container` passed. `compile` and `test-and-build` were still in progress when the PR merged (19:08 UTC) and had not concluded at 19:12 UTC.
- Limitations: not deployed; no real `docker stop` / SIGTERM test; the library-enrich (MusicBrainz auto-fill) job does not stop mid-run (R1 recovers a hard kill); `lens_refresh_status` `retry_after` still keys off `last_good` and can differ from the loop's due time.

## 2026-11-16 — Server efficiency R4 follow-up: paths read-only, writer only for the cache save

- PR [#1139](https://github.com/abucalip/navi-librarian/pull/1139), squash `e11f81c7`, merged. `GET /api/knowledge/paths` (non-Gaps) now reads through `open_readonly`; `cached_path`, `cached_album_path` and `path_page` take an optional `save_db` factory, so a writer is opened and closed only on a cache miss. Cache hits and Gaps never open a writer. No API shape change; `navidrome_server.py` untouched.
- Tests run (focused only): `test_api_knowledge_paths_route.py` (new test: the read connection runs no INSERT/UPDATE/DELETE and the cache row is still saved), `test_store_readonly_access.py`, `test_intelligence_paths.py`, `test_intelligence_album_paths.py`, `test_api_paths_warm_routes.py`, 84 passed; lint changed files 0 new findings. Full suite not run.
- Limitations: not deployed. R4 is complete.

## 2026-11-16 — Server efficiency R4: read-only knowledge reads

- PR [#1138](https://github.com/abucalip/navi-librarian/pull/1138), squash `961f002f`, merged. New `ensure_store` (once per process and path, called at web and worker startup), `open_writer` (no migration, no legacy move); `open_readonly` wired into the read routes (`/api/knowledge/*`, capabilities, GET insights/taste/suppression, popularity, taste-refresh, refresh and paths-warm status, update-store status, smart-playlist GETs). Write routes use `open_writer`. Compose and worker wording corrected to "only writer of knowledge facts". `docs/ARCHITECTURE.md` amended.
- Tests run (focused only): new `tests/test_store_readonly_access.py` (read while `BEGIN IMMEDIATE` is held, trace shows no write statements on the listed GETs, ensure once, writer writes) and the route, store and worker tests of every touched module, about 110 passed; seven existing test files now call `ensure_store` in setUp. Lint changed files clean. Full suite not run.
- Limitations: `GET /api/knowledge/paths` (non-Gaps) still writes the path cache; not deployed.

## 2026-11-16 — Server efficiency R3 part 2: web-side MusicBrainz through the gate

- PR [#1137](https://github.com/abucalip/navi-librarian/pull/1137), squash `cdd34851`, CI passed. Every web-side MusicBrainz caller takes slots from the shared gate (`Lane`): `discovery/` (`candidate_gathering`, `new_releases`, `artist_profiles`, `artist_links`, `artist_tag_fallback`, `mbid_popularity`), `integrations/musicbrainz/` (`album_year`, `rating_client`, `recording_album`), `discovery/search/providers.py` (request deadline as max wait) and the MusicBrainz host of the artwork `HostPacer`. 429/503 penalize the gate (Retry-After honoured); retry pauses are held on the gate; retry counts and budgets unchanged. Removed: `album_year` lock and `_last_request`, spacing sleeps, the `musicbrainz` entry of `SourceLimiter`, `MUSICBRAINZ_SPACING_SECONDS` in `mbid_popularity` and `artist_tag_fallback`. `navidrome_server.py` net -2 lines. New `Lane.acquire(max_wait)`, `Lane.penalize_response`, `tests/conftest.py` (private no-wait gate per test), `tests/gate_fakes.py`. Boundary test `PENDING` is empty.
- Tests run (focused only): about 670 across the changed modules and neighbours (discovery search/candidate/genre/popularity/artist files, album year, rating client, radio, artwork fetchers, provider gate, boundary test), all passed; lint changed files 0 new findings. The full suite was not run locally.
- Limitations: the live two-process timestamp check (gaps >= 1.1 s with web and worker active) is not done; not deployed.

## 2026-11-16 — Server efficiency R3 part 1: worker-side MusicBrainz through the gate

- PR [#1136](https://github.com/abucalip/navi-librarian/pull/1136), squash `78153260`, head `44b7f094`, CI passed (5 checks). `api_fill.Paced` (auto-fill, update requests, release search), `insights/provider_runtime._paced_json` and `insights/set_fetchers._request` (MusicBrainz calls) take a slot from the shared gate through a `Lane` (`provider_gate.musicbrainz_lane()`) and `penalize` it on 429/503 (Retry-After when sent); retry counts and budgets unchanged. `MIN_INTERVAL` and the private timers removed. ListenBrainz keeps its 0.5 s sleep. Wikidata ingest had borrowed `Paced`; it now has its own timed pacer (behaviour unchanged). New `tests/test_musicbrainz_gate_boundary.py` fails on a MusicBrainz URL module that does not use the gate; its `PENDING` list holds the web-side modules and may only shrink.
- Tests run (focused only): api_fill, auto_fill, update_requests, wikidata ingest, insights provider_runtime, insights refresh, set_fetchers, set_job, provider_gate, boundary test, all passed; lint changed files 0 new findings.
- Limitations: web side not routed yet (`discovery/` callers, `integrations/musicbrainz/album_year.py`, `rating_client.py`, `recording_album.py`, artwork `HostPacer`, the `SourceLimiter` musicbrainz entry); the two-process fake-provider timing check is not done. Not deployed.

## 2026-11-16 — Server efficiency R2: shared provider gate, and its review fix

- PR [#1134](https://github.com/abucalip/navi-librarian/pull/1134), squash `bbf3bab7`, head `9c6d6f67`, merged without review. Adds `integrations/provider_gate.py`: a dedicated SQLite file (`DATA_DIR/provider_gate.sqlite3`, WAL, `synchronous=NORMAL`, busy timeout 5 s, one connection per thread) holding per-provider slots (`reserve(provider, max_wait)`, `penalize`, `snapshot`, `default_gate(data_dir)`); MusicBrainz 1.1 s, other names only counted; in-process pacer at 2x the interval if the file is unusable. No callers yet.
- Review of #1134 found that a wall-clock step back after a penalty froze the provider (reproduced: 30 s penalty plus a 1 h step back refused every reservation for 3630 s), a fresh penalty after a step back was absorbed into the stale block, and the fallback pacer had no clamp. Fixed in PR [#1135](https://github.com/abucalip/navi-librarian/pull/1135), squash `aa157c2f`, head `3d19b443`: one `_clamp` in shared and fallback `reserve` and `penalize`. After the owner's review of #1135, a block more than `MAX_PENALTY` (1 h) ahead is capped at `now + MAX_PENALTY`, not cleared, so a valid 3600 s penalty survives a 1 s step back; a large step back delays a provider by at most 1 h. The multi-process test now asserts on granted slot starts, not wake-up times, with no jitter allowance.
- Tests run: `pytest tests/test_provider_gate.py` only (14 tests, 3 consecutive local runs after the final fix; the three cap tests fail on the previous clamp). The spec's 20 consecutive multi-process runs were done locally for #1134 only, not again after #1135, and not 20 times in CI. CI passed on both final heads (compile, test-and-build, container-smoke, lint-changed, validate-container).
- Limitations: no callers, so nothing is paced by the gate yet (R3). Not published or deployed.

## 2026-11-16 — Server efficiency R1: single-worker lock and restart recovery

- PR [#1133](https://github.com/abucalip/navi-librarian/pull/1133), squash `254c74fc`, head `760e022f`. `app/worker.py` takes an exclusive non-blocking `flock` on `DATA_DIR/worker.lock` (a second worker exits 1); then, before any thread starts, `recover_running` (new, `intelligence/jobs/runner.py`) requeues `running` rows of `WORKER_JOBS` (insights gems, provider lenses, API fill, Wikidata ingest, popularity) with progress kept, and marks an interrupted `musicbrainz_slice` run `failed`; web-owned jobs are untouched. `prune_finished` runs at start and daily. `paths_warm` recovers by age (`max_seconds` + 600 s).
- Tests run: `test_worker_lock.py` (new), `test_intelligence_jobs.py`, `test_intelligence_musicbrainz_auto_fill.py`, `test_intelligence_paths_warm.py`, `test_api_paths_warm_routes.py`, `test_server_v2_phase6_exit.py`. CI passed on the head (compile, test-and-build, container-smoke, lint-changed, validate-container, validate-release-workflow). The first head failed the Phase 6 gate because the worker imported `intelligence.taste`; the popularity job is now named by string, pinned by a test.
- Limitations: not published or deployed; not run against a real killed worker in the container. `insights_refresh._loop` still ignores the stop event (F4, W1). The "only writer" wording in `compose.yaml` is left to R4.

## 2026-11-16 — Android: app version 1.8.2

- Pushed to `main` at the owner's request (no PR). Version bump only: app 1.8.2 (versionCode 20).

## 2026-11-16 — Android: the response cache no longer scans its folder on every save (all themes), app 1.8.1

- Pushed to `main` at the owner's request (no PR). Cause of the Android-only slowness on every theme (slow page opens, pictures arriving one by one), while the web and macOS clients stayed fast: `FileResponseCache.put` ran `trim()` after every save. `trim()` listed the whole cache folder and sorted it, reading a file's date on every comparison, and summed every size. It held the same lock every `get` waits on. Every request saves its answer, including each artist-image, artwork and year lookup, so the folder holds thousands of small files (they are only deleted past 20 MB), and each save and read queued behind a full scan. Timing of the same scan on a Mac SSD: 105 ms per save at 2,000 files, 0.7 s at 10,000, 2.4 s at 30,000. #1127 (top bar inside the page) was ruled out from the code.
- Fix (`data/ResponseCache.kt`): the folder is listed once, on the first save; sizes and age order are then kept in memory, and the oldest files are deleted from that order only when the total passes the limit. Reads take no lock: a file is replaced by a rename, so a read sees the old answer or the new one. Leftover `.tmp` files are deleted when the folder is first listed.
- Tests: `ResponseCacheTest` (2 new: entries saved before a restart count toward the limit; rewriting a key makes it the newest), `OfflineReadTest`, `StreamSeedTest`, 16 pass, JDK 17. No APK built; not run on a device.
- App version 1.8.1 (versionCode 19).

## 2026-11-16 — Android: a revisited Album or Artist page no longer empties while it reloads (all themes) (PR open)

- Branch `claude/stream-keeps-saved-page`. Cause of the slow Album and Artist pages, found from the code and one timing of the live server's streams (curl, no emulator): `streamSections` started each live load from an empty page. The screen shows the saved copy first, so the first live section (the header) replaced the whole page; tracks, description, similar albums, top songs and missing albums vanished and came back one by one as the server sent them. On the live server an owned album's stream sends the header at 0.13 s, tracks at 0.75 s, description at 1.7 s and similar albums at 2.8 s when its provider caches are cold (0.09 s for everything when warm); an artist's stream finishes at 0.75 s. The page now starts from the saved copy's sections and each live section replaces its saved one, so a page seen before stays whole. The random five similar artists were also reshuffled on every section; they are now picked again only when the similar list itself changes.
- The top bar changes (#1126, #1127) did not cause or fix this; they are left in place (the bar no longer leaves the layout mid-transition, which is harmless).
- Server side, unchanged here: on a first view the album page waits on providers for tracks (even for an owned album, `race_tracks`), description and similar albums, then caches them. The worker does not prefetch them into the knowledge store or the provider cache; that is plan item K3 in `docs/plans/efficiency.md` (worker prefetch for owned entities), not built.
- Server, **temporary until the efficiency plan is implemented** (`docs/plans/efficiency.md` K3, which needs K1, K2 and W1 first): an owned album's stream now sends the library's own tracklist right after the header, then the provider's tracklist as a second `tracks` section that replaces it; a provider that fails or times out sends no second section, so the library list stays (`discovery/search/album_page.py` `early_tracks`; note in `docs/contracts/SEARCH_CONTRACT.md`). Android keeps the last section of each name, the web app refills its track list on each `tracks` event, and the plain JSON answer (macOS) keeps the last one. Description and similar albums still arrive late on a first view. Tests: `EarlyLibraryTracksTests` (3 new) and the album, search-route, artwork-choice, quality and UI-contract suites, 157 pass.
- Tests: `StreamSeedTest` (new; fails without the fix), `OfflineReadTest` (8 pass), JDK 17. `compileDebugKotlin` builds. Not run on a device.

## 2026-11-16 — Android: top bar belongs to the page on every theme (PR open)

- Branch `claude/topbar-in-page`. The cause of the slow Album and Artist opens from Home in Gallery (see the entry below) was not Gallery-only: the shell drew the app bar in the `Scaffold` `topBar` slot on Home, Discover and Library for every other theme too. Opening a page from them removed the bar in the same frame, so the page under it re-measured and grew mid-transition. Gallery had been fixed by giving Home its own bar. Now the bar (and the offline banner) is drawn by the page: `TopLevelPage` in `MainShell` wraps Home, Discover and Library (Flow keeps its "Discover" / "Library" titles; Gallery draws none, its pages carry their own heads) and the `Scaffold` has no `topBar`. The bar leaves with its page, so nothing re-measures. Pages that are not top-level keep the banner in the shell column as before.
- Checks: `compileDebugKotlin` builds. Not run on a device or emulator; the owner's phone check decides, as for Gallery.

## 2026-11-16 — Android Gallery: Home bar, Discover in Flow's design with tiles, hero slideshow (PR open)

- Branch `claude/gallery-home-speed-discover`. Slow Album and Artist pages from Home (Gallery only): Gallery's Home was the only Gallery page under the shell's top bar (Discover and Library carry their own heads). Opening a page from Home removed the bar in the same frame, so Home jumped up, re-measured its list and composed the rows that came into view while the page transition ran (seen in a screen recording on the emulator). Home now draws `GalleryHomeBar` above its own list and the shell draws no bar on a Gallery page (`MainShell` `galleryHead`; `HomeScreen` passes Settings and Discover through). Measured on an emulator against the live server (temporary timing logs, removed): tap to first page frame and to the page drawn with data were alike from Home and Library before and after (about 0.1 s and 0.4 to 0.7 s warm; about 0.95 s cold, both janky on a cold start); the emulator did not reproduce a Home-only delay, so the owner's phone check decides. Ruled out on the emulator: server time (artist page 0.05 s for both parameter forms), Home drawing frames while idle (none, also while playing), shared prints from Home (turning them off did not change the cold frames).
- Discover in Gallery takes Flow's one-switch design (`docs/archive/completed/Discover_page.md`) in Gallery's type: under the date line and title, the list's short name in Fraunces italic with a chevron and one hairline dash per list; it opens a list sheet (the seven lists, Saved and Insights under "Yours", current one checked). Lists are a two-column grid of matted tiles under hairline section heads with an album count: Get on the print's corner, "No. 01 · genre", the work in italic with Save and the three dots, the maker, then the reason over up to four lines. `GalleryListsRules.tileReason` takes the first of: the pick's `because` / `similar_to`, the server's `reason` (Deep dives, New releases, Personal), the lens and its seed tag (Daily picks lenses: "From the acid house you keep repeating"), the artist's albums in the library (Collection), else "In your library" for an owned album. `DiscoveryItem` gains `lens` and `artist_library_album_count` (optional). Insights: taste card, then every card with its lens named on it, then one muted line for the lenses that are off or have nothing today. The Lists / Insights tabs and the source switch are gone from Gallery's Discover; sideways swipes move between all seven lists.
- Home hero: a `HorizontalPager`, so the print, placard and actions follow the finger and settle to the next or previous album (380 ms on Gallery's travel curve, `GalleryMotion.heroSlide`); the chevrons slide the same way (a wrap from the last album to the first jumps); only the settled album's print is a shared element.
- Now Playing (Gallery): swipe down also lowers the page from the Queue and Lyrics views. A nested-scroll connection on the page frame lets the list scroll first; once it is at its top the rest of a downward drag lowers the page, an upward drag lifts a lowered page before the list moves, and the release uses the same rule as before (a quarter of the screen or a quick flick closes, otherwise it springs back). A fling that reaches the list's top does not lower it. Checked on the emulator: Queue (short drag springs back, long drag closes) and Lyrics on a song without lyrics; Lyrics with a scrolling list of lines not seen.
- Fixed on the way: an anniversary Insights card read "Anniversarie" (`removeSuffix("s")`); `GalleryListsRules.lensLine` makes it "Anniversary".
- Tests run (focused, JDK 17): `GalleryListsRulesTest` (new cases), `GalleryMotionTest` (new case), `GalleryHomeRulesTest`, `FlowDiscoverRulesTest`, `DiscoveryTest`, `GalleryTest`, `ExistingLayoutsTest`, `FlowHomeRulesTest`, `NavRulesTest`: 80 pass. Seen on the emulator (Gallery White): Discover grid, list sheet, Insights, hero swipe. Not run on the owner's phone. Covers stayed blank on the emulator for lookup-only albums (also before this change).

## 2026-11-16 — Android Gallery fixes after G7: Home overlap, row prints, page speed, Paths sheets, player swipe, hero swipe (PR open)

- Branch `claude/gallery-fixes`. Home overlap: G7 wrapped each Home block in `Box(Modifier.galleryArrive(n))`; the blocks emit several root children (heading, row, list), which a Box stacks on top of each other. They are now `Column`s (also on the Album and Artist page items that had the same wrapper).
- `GalleryPrint` never applied its `size` to a matted print, so Top songs and Missing albums drew full-width covers and prints in a LazyRow had no width bound (covers decoded at full size). It now sets `width(size)`; a caller's own width still wins. The print shadow paints and blur filters are built once per size (`drawWithCache`) instead of on every draw. Both are the likely cause of slow Album and Artist pages; not measured on a device.
- Missing albums on the Gallery Artist page: one row of prints, like Similar albums on the Album page; Get is on the album page they open.
- Paths sheets (artist and album) take Gallery's type and look through `isGallery()` branches in `PathTrail.kt` (header, tabs, link, step rows, open step, notes) and the description lines.
- Gallery Now Playing: swipe down lowers the page (past a quarter of the screen or a quick flick), otherwise springs back.
- Home hero swipe: the gesture was keyed on the item count and kept a stale step closure, so every other swipe landed on the same page; it now reads the current step.
- `compileDebugKotlin` builds. Unit tests not run locally (only JDK 27 on this machine, which Gradle cannot parse); CI runs them. Not run on a device.

## 2026-11-16 — Android Gallery theme G7: the motion and the skipped pieces (PR open)

- Branch `claude/gallery-motion`. Builds the section 8 motion that G1 to G6 left out, and the menu sheets G6 drew as plain rows. New `ui/theme/GalleryMotion.kt` (pure values pinned to `tokens.json`, `riseFraction`). Shared print: `GalleryPrint(sharedKey)` makes the whole print (mat and shadow) the shared element, over 420ms on cubic-bezier(0.3, 0, 0.1, 1) (`SharedCover.kt` Gallery branch); added on Home's hero and Played lately, Album (page print and Similar albums), Artist, Genre, Library and Discover, each with one key per page (Played lately skips the hero's album, Similar skips the page's own, Discover keys an album's first entry only). Page arrival: Gallery pages no longer slide; the leaving page fades out (180ms), the new one fades in (260ms after 80ms), and its first six blocks rise 10dp, 40ms apart from 120ms (`GalleryArrival` per destination in `MainShell.Opaque`, `Modifier.galleryArrive` on Home, Album, Artist, Genre, Library, Discover, Radio and Heard; the clock is read in the draw layer only). Now Playing: the mini cover flies into the 300dp print over the 440ms rise and back over the 360ms fall, drawn over the player window from `GalleryFlight` (the mini cover's screen bounds) and the print's own bounds, the print faded until it lands; the dock leaves when the player opens and slides back up over the fall. Snackbar: `GallerySnackbarHost` fades in and rises 14dp over 280ms and holds 4s (accessibility timeouts respected) instead of Material's scale. Menus: `GalleryMenuSheet` gains the 58dp print header with title and catalogue line, icons and explanations (`GalleryMenuItem`, `GalleryMenuHeader`, `GalleryPagesRules.menuLine`); the Home pick and play menus are now sheets (were drop-downs), and the song menus (Album, Artist) and Library artist menu carry headers and icons.
- Not built: the sheet's own timing (scrim 260ms, glide 380ms, close 260ms): Material 1.3.2 (BOM 2025.04.01) fixes ModalBottomSheet's animation at its defaults and offers no parameter; replacing it would mean a custom sheet for every sheet in the app. Search results keep no shared print (Search is a sheet outside the navigation). Discover's entry menu stays a drop-down (its More / Less like this items are shared drop-down items). "Why this pick?" is not added (it would need a page to explain the pick).
- Tests run (focused, JDK 17): `GalleryMotionTest` (new), `GalleryPagesRulesTest`, `GalleryTest`, `MotionTest`, `ExistingLayoutsTest`, `GalleryPlayerRulesTest`; `compileDebugKotlin` builds. No device or emulator was connected: none of the motion has been seen running, and the cover flight assumes the app and player windows share their screen origin (both full-screen).

## 2026-11-16 — Android Gallery theme G6: Downloads, Stats, Server, Settings, sheets (merged; Gallery closed out)

- Branch `claude/gallery-g6`. `ui/downloads/GalleryDownloads.kt` (hairline entries: 64dp print, Fraunces italic work, state in words, four-segment tracker with its names, actions; `GalleryDownloadsRules` pure), `ui/stats/GalleryStats.kt` (word switch for the range, Fraunces numeral, hairline sections; chart titles take the section heading in `ChartFrame`), `ui/settings/GallerySettings.kt` (Settings groups, Server, Appearance with Day/Night swatch prints, shared row/switch/head blocks; `GallerySettingsRules` pure), `ui/player/GalleryEqCrossfade.kt` (Equalizer dot plot, Crossfade length), sheets: `GalleryMenuSheet` (pick and song menus as 62dp-row bottom sheets) and a Gallery layout in `ConfirmSheet` (catalogue line, italic question, Keep and destructive buttons, both outlined; `ConfirmSpec.eyebrow`). One `isGallery()` branch each in `DownloadsScreen`, `StatsScreen`, `SettingsScreen`, `SettingsRow`, `ServerScreen`, `AppearanceScreen`, `EqualizerScreen`, `CrossfadeScreen`; `GalleryRow` gained `subColor`.
- Differences from `pages/downloads-stats-server`, `pages/settings`, `pages/sheets`: the Fade row (Smooth, Even, Quick) is not drawn (no such setting, as in Flow); stats keeps the 3-month range the mockup omits; Appearance has a theme-group word switch (the app has eight themes, the mockup draws only Gallery's) and a Type section; Server shows a plain Check now row with a check mark when all is well; the menu sheets show option rows only (no print header, icons or explanations, the call sites pass labels only); confirmation wording stays the app's own (mockup labels are shorter); the stage names and "Skip this source" carry the live countdown; Settings shows the connection check lines only when a check failed.
- Tests run (focused, JDK 17): `GalleryStatusRulesTest` (new), `ConfirmSheetTest`, `GalleryTest`, `DownloadsRulesTest`. Not run on a device; no screenshot comparison yet.

## 2026-11-16 — Android Gallery theme G5: Now Playing, Queue, Lyrics and Radio (PR open)

- Branch `claude/gallery-g5`, PR [#1121](https://github.com/abucalip/navi-librarian/pull/1121). `ui/player/GalleryNowPlaying.kt`: `GalleryPlayerFrame` (full-screen dialog that rises in 440ms and falls in 360ms, durations through `MotionRules`), `GalleryPlayer` with three views of one page (player: 300dp print with 14dp mat and the night spot, work in Fraunces italic, "Artist — Album" links, quality tag, seek, transport, four tools; queue: playing song, "Next · N songs" with Clear, rows with remove, sound-alike button; lyrics: small song row, Photos switch, Fraunces 24/32 lines sung / current in italic / waiting), `GalleryPlayerRules` (pure). `ui/radio/GalleryRadio.kt`: stations (52dp logo prints, the playing one shows the bars, hearts), Heard (catalogue line by time of day, rows with Get / In library / Requested), live radio (300dp plate, "On air · FIP", song, heart / Play / Heard, Get this song), `GalleryRadioRules` (pure). One `isGallery()` branch each in `NowPlayingSheet` (new `PlayerContainer` gallery frame), `RadioScreen`, `HeardScreen`, `RadioNowPlayingSheet`; `OnArtwork(keepBrutal)` keeps Gallery's own palette; `TransparentSystemBars` gained `lightBars` for light pages.
- Differences from `pages/player` and `pages/radio`: the mini player's cover does not travel into the 300dp print (the player is a dialog window, so it rises as a page; docs/archive/completed/GALLERY_THEME.md G3 allows this fallback); the shuffle and repeat buttons carry a small `accent` mark when on (the mockup draws them alike); the queue has no Move up / Move down / sonic-path buttons beside the X, they are a long press and screen-reader actions; the queue shows only the songs after the playing one and keeps the album's track images below the list; the live page keeps the sleep timer, stream status and Sign in / Retry buttons the mockup does not draw, and has no "The Colour of Spring is not in your library." note (the live data carries no album); the by-line under the live song is the artist only for the same reason; the lyrics page shows the Photos switch only when the playing album has photos, and with photos on the page uses the dark override that every theme's photo backdrop has; the player bar's three dots offer the lyric line and facts switches and Open artist / Open album (the mockup draws no menu contents).
- Tests run (focused, JDK 17): `GalleryPlayerRulesTest` (new), `GalleryTest`, `ExistingLayoutsTest`, `RadioScreenTest`. Not run on a device; no screenshot comparison with the mockup PNGs yet.

## 2026-11-16 — Android Gallery theme G4: Discover, Library and Search (merged)

- PR [#1120](https://github.com/abucalip/navi-librarian/pull/1120), squash `700adbba`, required CI passed (compile, test-and-build, container-smoke, validate-container, lint-changed). `ui/discover/GalleryDiscover.kt` (date line and title, tabs Lists / Insights, list names as the Fraunces source switch, catalogue entries with a 104dp print, "No. 01 · genre", the work in italic, maker, reason, Get / Save / three dots; Insights as hairline sections with the taste card, ranked bars and lens cards), `ui/library/GalleryLibrary.kt` (count line, title, tabs, order line with Sort, artist rows with photo prints, albums as captioned prints), `ui/search/GallerySearch.kt` (underline field, grouped results with counts, owned in words, small Get), `ui/common/GalleryListsRules.kt` (pure) with `GalleryListsRulesTest`. One `isGallery()` branch each in `DiscoverScreen`, `InsightsPage`, `TasteCard` (card and sheet), `LibraryScreen`, `SearchScreen`; `GalleryGetAlbumButton` gained `small`, `GallerySourceSwitch` gained `inset`.
- Differences from `pages/discover` and `pages/library-search`: Discover and Library draw no wordmark bar (the mockups have none), so Settings and Downloads are reached from Home; the source switch shows the six lists (Daily picks, Deep dives, New releases, Collection, Personal, Saved) instead of the mockup's three, and Daily picks and Deep dives show a hairline heading per lens or genre row instead of a pager; lens headings are the app's lens names, not "This week" or "Never played", and only an anniversary card carries the accent eyebrow; cards say "Open album" (no library id to play from) and "Dismiss" where the mockup says Play and "Not now"; the taste sheet keeps the listed movers above the tabs; library artist rows keep a three-dot play menu beside the chevron; a Library artist's album count and the order line are the app's own words (`By name`, `Newest first`, `By album count · Most first`); a genre result has a chevron and no print.
- Tests run (focused, JDK 17): `GalleryListsRulesTest` (new), `ExistingLayoutsTest`. Not run on a device; no screenshot comparison with the mockup PNGs yet.

## 2026-11-16 — Android Gallery theme G3: Album, Artist and Genre (merged)

- PR [#1119](https://github.com/abucalip/navi-librarian/pull/1119), squash `c1b40568`. `ui/album/GalleryAlbum.kt` (228dp print with the flip and edition stack, catalogue line, title, artist and genre links, Play / Shuffle / Paths or Get album / Save, note, tabs Songs / Info / Reviews / Booklet, similar albums and artists), `ui/artist/GalleryArtist.kt` (200dp photo print, catalogue line with the year span, genres, Play / Shuffle / Paths, Top songs, In your library, Missing albums with Get, About, photo strip, similar artists), `ui/GalleryGenre.kt` (head, Albums / Artists tabs, captioned prints, artist rows), `ui/common/GalleryPages.kt` and `GalleryPagesRules.kt` (pure) with `GalleryPagesRulesTest`. One `isGallery()` branch each in `AlbumScreen`, `ArtistScreen`, `GenreScreen`; `ArtistPhoto` gained an optional `rect`; `rememberServiceMenu` beside `ServiceLinks`.
- Differences from `pages/album-artist-genre`: no label in the catalogue line (the server sends none); genre stays in the "artist · genre" line on both album frames so it stays a link; Paths only on an album in the library (the server builds paths from a library album), so frame 2 shows Get album and Save only; "Why this pick" is not drawn (the album page has no pick reasoning); the three dots on an album also hold the Apple Music, Deezer, MusicBrainz and Qobuz links (the logo row is not drawn), and hide when a page has nothing to offer (artist or genre not in the library; the genre page has no actions); song listen counts and the per-album Play badge are not drawn; Similar artists, About, the photo strip, the Missing albums, the partial-library note with its Get, owned states in words and the disc headings are built from the existing page with Gallery's components, since the mockup does not draw them; the song list has no summary line (the catalogue line carries songs and length).
- Tests run (focused, JDK 17): `GalleryPagesRulesTest` (new), `GalleryTest`, `ExistingLayoutsTest`, `PaletteTest`. Not run on a device; no screenshot comparison with `pages/album-artist-genre.png` yet.

## 2026-11-16 — Android Gallery theme G2: Home with the Radio section (merged)

- PR [#1118](https://github.com/abucalip/navi-librarian/pull/1118), squash `68426668`. `ui/home/GalleryHome.kt` (source switch, hero print and placard with pager, Played lately, Artists you return to, Radio plates and "Heard on" rows, This week, Arrivals, Genres line, library line, loading/failing/no-listening states), `GalleryHomeRules.kt` (pure), one `Layout.Gallery` branch in `HomeScreen`, optional `onOpenPlayer` so a station plate opens that station live, `GalleryPrint` `small` option.
- Differences from `pages/home` (data Home lacks): library line shows albums, artists and new this month (no listening hours); Played eyebrow is "Recently played" (no played time); This week button is "Open album" (an insight has no library album id); artist album counts come from one extra library artists request and are left out when unknown.
- Tests run (focused, JDK 17): `GalleryHomeRulesTest` (new), `GalleryTest`, `ExistingLayoutsTest`, `FlowHomeRulesTest`. Not run on a device; no screenshot comparison with `pages/home.png` yet. Next: owner checks G2 on the phone, then G3 Album, Artist, Genre.

## 2026-11-16 — Android Gallery theme G1: palettes, fonts, icons, kit and shell (merged)

- PR [#1117](https://github.com/abucalip/navi-librarian/pull/1117), squash `d6868845`. `Layout.Gallery`, eight palettes, optional `control`/`onControl`/`mat` roles, `FontPairs.Gallery` with three subset font files, `GalleryIcons`, `GalleryKit`, `GalleryShell` (dock bar with sliding marker, mini player, bars, snackbar, sheet), Gallery branches in the shared controls, chart, seek, nav rules, motion family and a Gallery group in Appearance. Pages are unchanged until G2 to G6.
- Deviation: Day 1 muted text is `5D6169` (draft `5E626A` was 4.4996:1 on PaletteTest's hue-120 pastel wash); `tokens.json`, `palettes.css` and the spec carry it, the mockup pages still show the old value.
- Tests run (focused, JDK 17): `GalleryTest` (new), `PaletteTest`, `ExistingLayoutsTest`, `NavRulesTest`, `FlowTest`, `SoftBrutTest`, `CoverStackSettingsRulesTest`; `assembleDebug` builds. Not run on a device; no screenshot comparison with `pages/components` yet; the print shadow and bar marker are unchecked visually. Next: owner checks G1 on the phone, then G2 Home.

## 2026-11-16 — Android Gallery theme: design system and mockups (merged, #1116)

- Three theme proposals (Gallery, Aura, Index) shown to the owner; Gallery chosen, Radio section added to Home, palettes reviewed in three rounds (eight kept). Docs only: `docs/archive/completed/GALLERY_THEME.md` and `docs/design/gallery/` (tokens.json, palettes.css, gallery.css, pages/*.html and .png, icons, fonts, _src/build.py, _src/check_contrast.py).
- Checks run: `check_contrast.py` (all eight palettes pass the PaletteTest rules plus Gallery roles); the live motion page click-tested headless in Chrome (album open and back, Now Playing rise and fall, sheet, snackbar). No app code changed; no Android tests run (none affected). Fonts: Fraunces and Manrope from Google Fonts (OFL), subset with fontTools.

## 2026-11-16 — macOS: queue panel add-songs buttons are equal tiles, description on hover (PR open)

- Radio bars: the player bar and the Radio page asked `player.isPlaying`, which is false for a station (its state is `live.phase`), so the bars never moved; both now use `live.phase == .playing`.
- The two buttons at the top of the queue panel show only icon and name, in tiles of equal width and height (36 pt); what each adds shows as a hover tip and as the accessibility hint. Tests: `swift test --filter CupertinoPagesRenderTests` passed. Not run: full suite, a look in the installed app.

## 2026-11-16 — macOS: library reloads after a Get, moving playing bars, album page alignment, queue controls, handoff window (PR open)

- Library: when a poll sees a Get become imported, `AppState.reloadLibraryAfterImport` waits 15 s (the server resyncs 10 s after an import, PR #698) then reads only the newest albums (`getAlbumList2` newest, 24) and replaces Recently Added; nothing else is re-read. A failed read keeps the list.
- Playing bars: the AppKit symbol effect was requested before the view had a window and was dropped, so the bars stayed still. `PlayingBars` now starts the effect when the view joins a window. The Radio page's playing row shows the bars beside the station name.
- Album page: the "More by", "Not in your library" blocks are one 620 pt column from the left edge; circles and squares sit in equal slots, so a short row keeps the slots of a full one and squares line up under the circles.
- Queue panel: "Similar artists" and "Sounds alike" are labelled tiles that say what they add; Autoplay has its own full-width line with its explanation.
- Continue on this Mac: offered only when the phone saved its queue within 2 hours (was 24). The cause of "does nothing" was not reproduced; failures to read the queue or an empty queue now show a notice instead of nothing.
- Tests: `swift test --filter "AcquisitionModelTests|HomeScreenTests|GetFinishedDetectorTests|CupertinoPagesRenderTests"` passed (84); added one import-reload case, changed one handoff age. Not run: full suite, installed-app A/B of CPU (rule 6), a live phone handoff.

## 2026-11-15 — macOS: the ⌘K palette also searches music beyond the library (PR open)

- The palette now lists a "Not in your library" section, last, with artists, albums and songs the library lacks. Source: the server's `GET /api/search` (`scope=all`), read whole (the stream ends within about 3 s) and parsed in `DiscairLibrarian/CatalogSearch.swift`; only `owned: false` results count. Requests start 450 ms after typing stops, need two characters, and a newer query cancels the older one; a failure leaves the rows as they were.
- Rows: an artist opens an artist page built from Librarian data; an album opens its page and has the Get icon; a song opens its (unowned) album, with no Play or Get icon. Anything the library already lists (owned artists, owned or missing albums) is left out.
- The Library search field is unchanged: it reads `LibrarySearch` and `songHits` only, so it stays owned-only.
- Tests: `swift test --filter "CatalogSearchTests|CommandPaletteTests"` passed (4 new client cases, 5 new palette cases). Not run: full suite, the live app against a real server (provider results and timing not seen).

## 2026-11-15 — Album page: owned songs matched to the provider tracklist by title likeness (PR open)

- Symptom (Android, owner screenshot): on an album page some owned tracks showed the download prompt in place, and the same songs were appended owned at the bottom. Cause: `mark_owned_tracks` matched a library song to a provider track only by exact normalized title, or same number with a length within 3 s. A renamed song ("Excerpt From the Blues" / "Excerpts From The Blues", "You'd Be So Easy to Love" / "Easy To Love") whose length differed by 6 s matched neither, so the provider track stayed unowned and the song was appended as an extra.
- Fix: a third pass owns a song on the same track number (disc 1 when multi-disc) whose title is alike (`titles_alike`: spelling ratio >= 0.85, or one title holds every word of the other, at least two words). The Android client only renders the server's list; the fix is server-side, so the web page gains it too. Whether the macOS client uses this endpoint was not checked.
- Tests: `pytest tests/test_discovery_search_album_page.py tests/test_disc_layout.py` passed (37); two cases added. Not run: full suite, a live device.

## 2026-11-15 — macOS: Play after Stop resumes the song, Continue on this Mac starts at the phone's place (PR open)

- Radio: #1090 made Play return to a song only when the station had paused it. A song the owner had already paused, a queue restored at launch, or a song still loading was missed, so Play restarted the station. Now Play after stopping a station goes to the queue's current song whenever there is one; only an empty queue restarts the station. `songPausedForStation` removed (dead). A song still loading when a station starts goes back to idle, not a false "paused".
- Continue on this Mac: the position was applied by a seek after start, which a growing download clamps to what has arrived (so it landed near the start), and was dropped after 6 s of loading. `PlayerModel.play(_:startAt:position:)` now carries the position into the load, and a start part-way in skips the growing download and uses the whole file. Continue re-reads `getPlayQueue` at click time (falls back to the copy Home read).
- Tests: `swift test --filter "LiveSessionTests|PlayerModelTests"` passed (53); added three station cases and two handoff cases. Not run: full suite, a live phone handoff, a run in the installed app. The owner's exact symptoms are not confirmed reproduced; these are the defects found by reading the code.
- Docs: `RADIO_PLAYBACK_PROPOSAL.md` S2.6 queue rule updated.

## 2026-11-15 — macOS: played queue songs play on double-click, moving bars beside LIVE in the player bar (PR open)

- Queue: played songs are no longer dimmed or single-click buttons; double-click plays one again (same as up-next rows). VoiceOver keeps a "Play again" action. The queue's playing mark already used the AppKit `PlayingBars` from #1088.
- Player bar: while a station plays, `PlayingBars` (AppKit symbol effect, still when paused or under Reduce Motion) sits left of the LIVE tag, so no SwiftUI continuous motion.
- Checked: `swift build --target DiscairUI` passes. No tests run (no logic changed; `PlayQueueTests` already covers `jump(played:)`). CPU with a station playing not measured; not run in the live app.

## 2026-11-15 — Flow Home: Threads and Shelf mixer plan (documentation only, direct to main)

- The owner chose A's Threads and C's Shelf mixer from three Home proposals (A Threads, B Time, C Shelves). Added `docs/plans/Home_threads_mixer.md` (design system: colour roles for all seven Flow palettes, type, shapes, icons with paths, constellation and mixer geometry, motion; behaviour; server additions S0a and S0b; steps and models) and the spec mockups `docs/design/android-art-themes/flow/home-threads-mixer/` with their generator `_src/build_home_threads_mixer.py`.
- No code, no tests run. Next: S0a.

## 2026-11-15 — Star Operation S4b: safer and deeper values from a replay measurement (merged #1102, squash `1e39cd98`, head `25428964`; CI passed: compile, container-smoke, lint-changed, test-and-build, validate-container)

- Measurement: one live run, approved by the owner, through the existing gatherer (`lens_service.build`, nothing stored) and one personal-list capture (`recommend_new_music`), both on a copy of the local test data; the inputs are private, outside the repository, mode 0600. `scripts/discovery_mode_sweep.py` then replayed them offline over a grid (no further provider traffic). Aggregates only below.
- Personal list (10 picks, 156 candidates: 30 adjacent, 116 adventurous, 10 cross-genre): `balanced` already picks 7 adventurous, above the floor of 2, so floor divisors 10 to 2 change nothing; divisor 1 (floor 10) makes every pick adventurous and cuts genre families from 6 to 3 (entropy 2.16 to 0.92). The floor is a floor: it cannot make a list safer, and raising it only reduces spread. Decision proposed: the floor is the same in every mode.
- Lens lists (Genre spread was not built on this run, so the lens floor was not measured): audience band maximum x2.0 lifts Deep cuts fill 8 to 10 and moves its obscure share (at most 50 000 listeners) from 1.0 to 0.7, Repeated tracks median audience 6 186 to 14 823 (share 0.7), Obsessions fill 8 to 9. Maximum x0.5 leaves Deep cuts unchanged and trims Obsessions (fill 8 to 7, median 4 364 to 3 621) and Repeated tracks (10 to 9, median 6 186 to 2 752). Band minimum x0.5 changes nothing; x2.0 only moves Repeated tracks. Current tastes (band 0 to 500 000) is unchanged in every setting.
- Proposed values: `safer` maximum x2.0, `deeper` maximum x0.5, everything else `balanced`. `safer` makes the lists better known and fuller; `deeper` makes the narrower lenses shorter, which is the cost of a stricter ceiling.
- Owner decisions (2026-11-15): the numbers are approved and the mode scales the Deep cuts band. Genre spread and a floor change remain unmeasured.
- Tests run (filtered): `test_discovery_mode` (new value tests), `test_discovery_lenses`, `test_discovery_lens_lists`: 74 pass. Full suite not run. One sample, one profile: not a quality claim.

## 2026-11-15 — Star Operation S4a: discovery mode setting and knob wiring (merged #1101, squash `040e5da0`)

- Head `ddf16a88`. `discovery/discovery_mode.py` holds the `discovery_mode` values, the `DiscoveryKnobs` (adventurous floor divisor, audience-band scales) and the stored-value reader; settings in `settings/service.py`, routes `GET`/`PUT /api/settings/discovery-mode` (DISC-14).
- Wired into `selection_policy.selection_request_options` (personal list floor), `lenses.run_lens` / `partition_lenses` / `partition_lens_pools` (Genre spread floor, gate-lens audience band), `lens_lists.build_lens_lists` and `lens_service.build`.
- `balanced` is today's behaviour and is tested equal to the setting absent; `safer` and `deeper` carry the balanced numbers until S4b. Lens definitions are unchanged; unknown audience is never obscure.
- Tests: focused only (`test_discovery_mode` new, plus selection, lens, lens-list, settings and characterization suites, 197 pass); the owner runs the full suite. No client shows the setting.

## 2026-11-15 — Star Operation S3b: Navidrome stars as a taste seed (merged #1100, squash `f11dffda`)

- `discovery/star_seeds.py`: `starred_seed_weights` (artist key to weight; 1.0 fresh (owner decision), 180-day half-life, 365-day expiry, 0.5 flat when undated) and `cached_starred` (one `getStarred2` per six-hour metadata-cache window). `candidate_gathering._star_seed_weights` merges them into the existing seed map (larger weight wins per artist) only when `star_seed_enabled` is on; any failure returns no stars. Counter `star_seed.starred_artists`. Query budget unchanged: a star can replace a planned tag query, never add one.
- Setting `star_seed_enabled` (default on, owner decision 2026-11-15) in `settings/service.py`, `GET`/`PUT /api/settings/star-seed`; requirement DISC-13. New `RecommendationProviders.settings_read`; the one wiring change in `navidrome_server.py` is net zero lines (D-016).
- Tests run (filtered): `test_star_seeds` (16), `test_discovery_save_tag_seed`, `test_navidrome_starred`, `test_settings_routes`, `test_server_size_guard`, and the 239 tests that import `candidate_gathering` or the replay tape, all pass. Three pre-existing pytest collection errors in `test_service_settings.py` (functions named `test_*` imported from `settings.service`) are unchanged by this PR.
- Owner decisions (2026-11-15): the setting is on by default and a fresh star weighs 1.0, equal to a save. Head `e659e4f6`.
- Not done: the live replay comparison with and without stars (it needs ListenBrainz and MusicBrainz traffic, which needs the owner's approval and `config.env`), so the weights carry no quality claim. No client shows the setting yet. With the setting on, a recorded tape would see extra `api_call` and cache events and not replay an older capture.

## 2026-11-15 — Star Operation S3a: getStarred2 read and parser (merged #1099, squash `2790e50b`)

- `integrations/navidrome/starred.py`: `fetch_starred` makes one `getStarred2` call through an injected `api_call`; `parse_starred` returns starred artists and albums with `starred_at` as epoch seconds or `None`. Songs ignored; errors propagate. Exported from `integrations/navidrome/__init__.py`. No caller, no behaviour change, no requirement row yet (S3b).
- Tests run (filtered): `test_navidrome_starred` (8 pass), `test_navidrome_client` (10 pass). Full suite not run. pylint not installed locally; `check_lint_changed.py` left to CI.
- Not verified: no live Navidrome call.

## 2026-11-15 — Star Operation S2c: blocklist screen and menu entries on the three clients (merged #1097, #1098)

- #1097 (squash `de3cfb1f`, head `4f98e4e9`): `discovery/artist_block.py` and `GET`/`DELETE /api/discovery/blocked-artists` (DISC-12, lists and lifts "Not this artist"; no schema change). Web More menu (`createFeedbackMenuButton`) and Blocklist page; Android `PickFeedbackItems` on the three Discover card menus and `BlocklistSettings` in all three settings layouts (`LibrarianClient.delete` with a JSON body); macOS `CupertinoPickFeedbackMenu`, `CupertinoBlocklist`, `BlocklistModel`, `SettingsTab.blocklist`. #1097 merged at its first head, before the review fixes were pushed.
- #1098 (squash `f0493185`, head `bf36de3c`): review fixes. Web menu width, lean stores the item's own `lens`, Not this artist hides the row and is offered only on reloading lists, Block genre reloads them; Android reads lens `tags` and sends `lens`; macOS no menu on Saved rows, Discover reloads after Block genre; `macos/DESIGN.md` section.
- Tests run (filtered): Python `test_discovery_artist_block` (4), `test_blocklist_ui_contract` (5), all `*ui_contract*` tests (481), routes and S2a/S2b suites; Android `BlocklistTest` (6), `DiscoveryTest`; macOS `BlocklistModelTests` (7) with the Home, pages and services render suites (111). CI passed on both heads. Full suite not run.
- Not verified: nothing seen in a browser, on a device or in the app (menu placement and focus, themed web layouts, Android menus and TalkBack, macOS menus, Night mode, VoiceOver). Open: Android Home pick menus not changed; macOS offers only a pick's first genre (none on lens picks); web dashboard strip and shelf have no Not this artist.

## 2026-11-15 — Star Operation S2b: More like this and Less like this (merged #1096)

- `discovery/artist_lean.py`: one row per artist (scope `artist_lean`), newer lean replaces older; `combined_seed_weights` and `combined_seed_genres` feed tag selection in `candidate_gathering`; `lean_boost` and `lean_penalty` feed `apply_feedback_signal`. `GET`/`POST`/`DELETE /api/discovery/artist-lean`. Requirement DISC-11.
- Tests run: `test_discovery_artist_lean` (11), `test_discovery_routes`, `test_discovery_genre_block`, `test_recommendation_feedback`, `test_recommendation_feedback_fixture`, `test_discovery_save_tag_seed`, `test_discovery_lens_feedback`, `test_api_discovery_injection`. Full suite not run locally. CI lint ratchet failed once on an unused import in the new test and passed after the fix. No client UI yet.

## 2026-11-15 — Star Operation S2a: block a genre (merged #1095)

- `discovery/genre_block.py`: blocked-genre rows (scope `genre`), exclusion from the personal pool (`prepare_ranking_inputs`) and lens pools (`build_lens_lists`), read-time hiding in `list_payload.py`, and `GET`/`POST`/`DELETE /api/discovery/blocked-genres`. Requirement DISC-10.
- Tests run: `test_discovery_genre_block` (8), `test_discovery_list_payload`, `test_discovery_lens_storage`, `test_discovery_lens_lists`, `test_recommendation_feedback`, `test_recommendation_cooldown`, `test_discovery_lens_feedback_api`, `test_discovery_routes`. Full suite not run locally; CI passed on the head. No client UI yet.

## 2026-11-15 — Star Operation S1c: reason line on macOS

- `DashboardPick.because` (lenient `PickBecause`, never throws) and `pickReason` in `DiscairLibrarian/LibrarianClient.swift`, same wording as web and Android: `tag` "Because you listen to {names}", `similar_artists` "Shares genres with {names}", older server `similar_to` falls back to the overlap wording, otherwise nothing. `AlbumItem.reasonLine` carries it; Cupertino Home (today's pick) and Discover rows draw it above the longer prose reason.
- Tests run: `swift test --filter DiscairLibrarianTests.LibrarianClientTests` (14 pass, new `reasonLineWording`); `swift build --build-tests` (compiles the UI target). The `DiscairUITests` suite was started but not finished, so it is not claimed. Not seen in the running app; the owner checks Home and Discover.

## 2026-11-15 — Star Operation S1c: reason line on web and Android (merged #1093)

- Web `reasonLine` (`static/app.js`) and Android `pickReason` (`model/Discovery.kt`) draw the server's `because`: `tag` reads "Because you listen to {tag}", `similar_artists` reads "Shares genres with {names}". Older servers that send only `similar_to` get the overlap wording (adjacent on web, any pick on Android). Without a reason the web keeps the category label.
- Android: `because` is decoded as JSON, so a malformed value drops only the reason line. The reason line is added to the classic `DiscoverCard`, which did not draw it before. Flow and CoverStack replace "Similar to:".
- Tests run: `tests/test_discovery_because_display_ui_contract.py` (new, 5 pass); `tests/test_discovery_similar_artists.py` (wording updated, passes); every module that reads `static/app.js` or the other static UI files (44, all pass, with `.venv`); `DiscoveryTest` under JDK 17 (10 pass, 4 new); `test_discovery_pick_because.py` (pass); `scripts/check_lint_changed.py --base origin/main` (2 files, 0 new findings, pylint run from a scratch install). The formatter was run under Node with seven cases (tag, overlap, unknown kind, malformed, older server, none).
- Not run: browser checks, a device, the macOS client (not in this slice), the full suite. Wording of a multi-tag `tag` reason ("shoegaze, dream pop") is not confirmed by the owner.
- Merged as squash `73938ac8` (PR #1093, head `c42f68c6`, after a docs-comment fix commit `c42f68c6`). CI on the head passed: compile, container-smoke, lint-changed, test-and-build, validate-container, validate-release-workflow.

## 2026-11-15 — Star Operation S1b: seed tags on tag-search picks (merged #1092)

- The owner chose option 1 for the reason wording: "Because you play" for a real seed, "Shares genres with" for tag-overlap names. For the `tag` kind the owner chose "Because you listen to {tag}".
- Open question answered by reading `candidate_gathering.py`: ListenBrainz CF items carry only `recording_mbid` and `score`, so CF candidates have no seed to carry. Tag-search candidates do: the profile tag. `record_seed_tag` (`discovery/pick_because.py`) stores profile-derived tags as `seed_tags` in `lb_tag_lane.py` and the MusicBrainz lane in `candidate_gathering.py` (exploration tags are not recorded, they do not come from the owner's listening). `because` gains kind `tag` (up to three names), which wins over `similar_artists`. No change to `navidrome_server.py`; no new provider requests.
- Tests run: `pytest tests/test_discovery_pick_because.py tests/test_discovery_lb_tag_lane.py tests/test_discovery_mb_tag_seed.py tests/test_discovery_deep_cuts_supply.py` (37 pass). Not run: full suite (owner rule), `check_lint_changed.py` (nothing committed when run; CI runs it).
- Merged as squash `55d4b4ac` (PR #1092, head `e9b23a9b`). CI passed on the head: container-smoke, lint-changed, compile, validate-container, test-and-build.

## 2026-11-15 — Star Operation S1a: `because` field on personal picks (merged #1091)

- New `discovery/pick_because.py` returns `similar_to` plus `because` (`{kind: "similar_artists", names}`) for each personal pick; `because` is omitted when there are no similar artists. `navidrome_server.py` swaps one import, one builder line and two assignments for the same number of lines (net 0, D-016). `similar_to` is unchanged.
- Tests: `tests/test_discovery_pick_because.py` (new), with `test_discovery_similar_artists.py` and `test_discovery_recommendation_payload.py` re-run (21 pass). `scripts/check_server_size.py` passes. `check_lint_changed.py` not run (pylint not installed).
- Android `ApiJson` and `LibrarianClient` ignore unknown keys; macOS Codable ignores them by default. Web and Android Discover are not changed.
- Merged as squash `5340e0b0` (PR #1091, head `b6ff5e4c`). CI passed on the head: compile, container smoke, lint-changed, test-and-build, validate-container, validate-release-workflow.

## 2026-11-15 — Client efficiency: Now Playing slideshow and artist collage on Core Animation (PR open)

- `SlideshowBackdrop`: the 20 Hz `TimelineView` (blur 36 and saturation per frame) is replaced by `SlideshowLayers`, one layer per photo with looping keyframes for opacity, zoom and pan, paused in place like the disc. Each photo is blurred and saturated once at the backdrop's size, in sRGB (checked side by side against SwiftUI's blur). The timing is the same as `slideshowFrame`. `CollageHeroBackdrop`: each slot is a `CollageSlotLayer` (a Core Animation zoom toward its corner, and a 1.4 s layer cross-fade on swap) instead of a SwiftUI `.animation` and `.transition`. In both, the offscreen screenshot keeps a still SwiftUI drawing.
- Before (installed build, playing, `top`): Now Playing with photos on 9 to 10 %, off 8.5 to 9 % (about 0.5 points); artist page with the collage 22 to 25 % for about 16 s while the tiles zoomed, then about 10 % (about 14 points; with more than five photos, swaps keep it moving). Standalone window (the new code verbatim, local photos, 4 `top` samples): slideshow 3.9 to 4.6 % before, 0.0 % after; collage 4.7 to 5.8 % before, 0.0 to 0.1 % after. Screenshots showed the photos upright, the zoom, the swap cross-fade and the slideshow cross-fade at the expected time.
- Test: new `SlideshowKeyframesTests` (the layered keyframes against `slideshowFrame` at every 0.25 s over two cycles, 2, 3, 5 and 12 photos); `swift test --filter "NowPlayingArtworkUITests|SlideshowKeyframesTests|CupertinoPagesRenderTests|CupertinoRound1Tests|BugBatchTests|ArtistCollage|Collage"`, 60 passed. Full suite not run. App A/B after the change not yet run (needs the owner to install the build).
- Workflow rule 7 now lists the examples in the code instead of the slideshow exception.

## 2026-11-15 — Workflow: macOS client motion and CPU rules

- Docs only, direct to `main` on the owner's instruction. New section "macOS client motion and CPU rules" in `docs/DEVELOPMENT_WORKFLOW.md`, with the lessons of #1071 to #1073 and #1088: no looping SwiftUI motion; use Core Animation or AppKit instead; read fast state in leaf views; stop motion when not needed; fallbacks for the offscreen screenshot and for the hosting-view environment; measure CPU on several pages and states, not only Home; `SlideshowBackdrop` is the known exception.
- PR #1088 merged as `242d5d0f`. The owner installed it and reports CPU much lower (by eye; no scripted three-run table).

## 2026-11-15 — Client efficiency: playing-row mark and player-bar marquee off the per-frame SwiftUI path (PR #1088, merged)

- `MarqueeLine` (player bar lyric or fact line that scrolls): `TimelineView(.animation)` replaced by `MarqueeStrip`, an `NSHostingView` slid by a repeating `CABasicAnimation`; still copy in the offscreen screenshot. Scrolling added about 10 points on Home (9.5 to 10 % against 17.5 to 22 %, window narrowed); standalone 5.3 to 6.1 % against 0.0 %.
- `PlayingBars` (album and queue rows) used SwiftUI's repeating `.symbolEffect`, which re-renders the whole window's display list on the main thread every frame, including when the row is scrolled out of sight. Now an `NSImageView` with the same symbol effect through AppKit; still SwiftUI symbol in the offscreen screenshot; still under Reduce Motion. Callers pass the row colour and font size.
- Evidence: album page playing 42 to 44 %, Home playing 10 to 11 %, album page paused 2 to 2.5 % (installed build, same track, `top`); 8 s `sample` showed the main thread about 95 % in the display cycle, blocked on render-server commits, which is the clock lag. Standalone 40-row window: SwiftUI effect 17 to 18.5 %, `NSImageView` effect about 2 %. Details in `docs/plans/client_efficiency_results.md` section 5. Earlier A/Bs were taken on Home, where the mark is not drawn.
- Test: `swift test --filter DiscairUITests` (before the marquee change), 779 tests, 777 passed; 2 failures in tests that do not touch these files (`settingsTabsAreTheFourOfTheMockupsAndAppearance` expects no Radio tab, from #1062; `dismissQueuesOneCardEventKeyedBySubject` 60 s timing window, ran at 126 s). After the marquee change `swift test --filter "CupertinoPagesRenderTests|PlayerBarRefinementTests"`, 20 passed. Full suite not run. App A/B after the change not yet run (needs the owner to install the build).

## 2026-11-14 — macOS Home marquee: pick chevrons (PR open)

- Owner change after H3: chevron buttons at the marquee's top right step back and forward through the picks (wrapping); ← and → do the same; ↓ does nothing; Space unchanged. Key glyphs removed from Get album, Save and Not for me, and the arrow keys no longer Get, Save or dismiss. `HomeScreen.steppedPick` replaces `pickKey`/`PickKey`/`PickArrow`; the Space notice now says "Use Get album to get it." Plan 3.1, `redesign.md` 5.1, `macos/DESIGN.md` and the mockup updated.
- Test: filtered run `HomeRenderTests|HomeScreenTests|HomeDashboardTests`, 85 passed (new `chevronsAndArrowsStepThroughThePicksAndWrap` replaces the arrow-key mapping test). Narrow render seen with the chevrons; keys not tried in a running window. Full suite not run. Not published or deployed.

## 2026-11-14 — macOS Home marquee H3 items 6 to 8: accessibility, seven-state renders, documents (merged)

- PR [#1083](https://github.com/abucalip/navi-librarian/pull/1083), squash `36ee2b35`. Plan slice H3, items 6 to 8; H3 is complete. Item 6: section 6 was mostly built; changes are `HomeScreen.tileLabel` for tile labels, the radio tile's status as its accessibility value, the marquee's blurred background and large cover hidden from VoiceOver, and a key hint on the marquee. Checked in code, not with VoiceOver. Item 7: `HomeRenderTests` renders default (Day and Night), notice, no pick, first run, Librarian unreachable, loading and narrow, each after checking its inputs; fixtures fixed (no phone notice in the default, empty library for first run, album list loaded via new `LibraryModel.setAllAlbums`, so Waiting longest is filled); the two radio card renders kept. Item 8: `redesign.md` 5.1 rewritten, `macos/DESIGN.md`, plan, `ACTIVE_WORK.md`, `PROJECT_STATUS.md`.
- Test: filtered run `swift test --filter "HomeRenderTests|HomeScreenTests|HomeDashboardTests"` on a Mac, 85 passed. Full suite not run. Renders compared with the mockups by eye (default Day and Night, notice, first run, unreachable); no pick, loading and narrow were rendered but not looked at. CI on the head: compile, container-smoke, lint-changed, test-and-build and validate-container passed. Not published or deployed.
- Known gap: with Librarian unreachable an arrived, unplayed album appears in neither shelf list. Not changed.
- Next action: H4, the owner checks Home against the real server.

## 2026-11-14 — macOS Home marquee H3 items 4 and 5: unused helpers deleted, skeleton and narrow checked (merged)

- PR [#1082](https://github.com/abucalip/navi-librarian/pull/1082), squash `40f5b4a8`. Plan slice H3, items 4 and 5. Deleted, after a search for each: `HomeStat`, `HomeChange`, `HomeKeyHint`; `HomeScreen` `addedLine`, `neverPlayedLine`, `listensTile`, `listensLine`, `waitingTile`, `lenses`, `ageText` and their types; `HomeDashboard.Waiting` and the `picksCount` input that only fed it (`AppState` and tests updated), with their tests. Kept `HomeSplit` (Insights uses it) and `neverPlayedChange` (not in the plan's list). Item 5 was already built; two details aligned with the mockups: 12 under the skeleton title block, and narrow Next picks keep the two-row block.
- Test: filtered run `HomeRenderTests|HomeScreenTests|HomeDashboardTests`, 81 passed. Full suite not run. Not compared on screen. Not published or deployed.
- Not done: item 6 (accessibility check), item 7 (seven-state render tests), item 8 (docs).
- Next action: H3 item 6.

## 2026-11-14 — macOS Home marquee H3 items 2 and 3: old Home modules and lens request removed (merged)

- PR [#1081](https://github.com/abucalip/navi-librarian/pull/1081), squash `574d33a9`. Plan slice H3, items 2 and 3. Removed from `CupertinoHome.swift` the briefing band and its stats, the Arrivals panel, the lens rows, the Recently added row and the helpers only they used (`split`, `FlowChips`, `stageWords`, local cover helpers); about 275 lines, none added. Home's task is now `loadHomeFeeds()` only (no `loadInsights`); `refreshHomeDashboard` and `reshufflePicks` are kept.
- Test: `swift build` clean; filtered run `HomeRenderTests`, 7 passed. Full suite not run. Not compared on screen. Not published or deployed.
- Not done: item 4 (delete `HomeStat`, `HomeChange`, `HomeKeyHint`, `HomeSplit`, old `HomeScreen` helpers, `HomeDashboard.Waiting` and their tests, after a search for each), the seven-state render tests (item 7), docs (item 8).
- Next action: H3 item 4.

## 2026-11-14 — macOS Home marquee H3 item 1: the new Home page (merged)

- PR [#1080](https://github.com/abucalip/navi-librarian/pull/1080), squash `192d3fda`. Plan: `docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` slice H3, item 1 only. The `page` of `CupertinoHome` is rewritten: notice, marquee (blurred cover, 55% black wash, white text, Get as the one primary button with keys inside the buttons, Next picks covers instead of chevrons), radio card (between marquee and shelf), New on the shelf, Waiting longest, summary line, Liner note; empty marquee, skeleton and narrow layout. New file `CupertinoHomeMarquee.swift` (shelf, waiting, summary views); `FlowLayout` is no longer private.
- Test: filtered run `HomeRenderTests|HomeScreenTests|HomeDashboardTests`, 91 passed. Default and narrow renders compared with the mockup by eye; the render fixture does not load `allNavidromeAlbums`, so Waiting longest showed its empty sentence. Night and the other states not checked. Full suite not run. Not published or deployed.
- Not done: the old briefing, arrivals, lenses and recently-added code is still in `CupertinoHome.swift`, unused (items 2 and 4); `loadInsights` still runs on Home (item 3); render tests for the seven states (item 7); docs (item 8).
- Next action: H3 item 2 (remove the unused code).

## 2026-11-14 — macOS Home marquee H2 items 3 to 5: Server activity in Settings, Services (merged)

- PR [#1079](https://github.com/abucalip/navi-librarian/pull/1079), squash `606b606c`. Plan: `docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` slice H2, items 3 to 5. `CupertinoServices` ends with `ServerActivityPanel` (new `onServicesPage` flag hides the "Services" and "Open Services" buttons, since the page is the destination) and loads insights and Home feeds in a `.task`. Home still draws the panel through the same view (item 4: nothing disappears between merges).
- Test: `ConnectionsServicesRenderTests/rendersServicesServerActivity` (Insights render test already existed from items 1-2). Filtered run on a Mac: `HomeRenderTests|ConnectionsServicesRenderTests|CupertinoPagesRenderTests|ConnectionsServicesTests`: all passed except `settingsTabsAreTheFourOfTheMockupsAndAppearance`, which expects five tabs and fails on `main` because the Radio tab exists; not touched here. Full suite not run. Not published or deployed.
- **Next action:** H3, the new Home.

## 2026-11-14 — macOS Home marquee H2 items 1 and 2 merged; duplicate taste panel removed

- PR [#1078](https://github.com/abucalip/navi-librarian/pull/1078) squash-merged as `897d6bfa`. After the merge the owner asked to remove the duplicated taste panel from Insights: "Your collection" repeated the headline and shifts that `CupertinoTaste` already shows. Removed `TastePanel` from `CupertinoInsights`; the section is now collection 2:1 decades, then shelf life full width. `TastePanel` stays in `CupertinoCollectionPanels.swift` because Home still draws it until H3.
- Pushed directly to `main` on the owner's instruction. Filtered run on a Mac: `swift test --filter "CupertinoPagesRenderTests/rendersInsightsYourCollection"`. Full suite not run (owner rule). Not published or deployed.
- Docs: plan (status, section 1 table, H2 item 2 and acceptance), `ACTIVE_WORK.md`.
- **Next action:** H2 item 3 (Server activity in Settings, Services), then items 4 and 5.

## 2026-11-14 — macOS Home marquee H2 items 1 and 2: panels moved, Insights "Your collection" (PR pending)

- Plan: `docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` slice H2, items 1 and 2 only (the owner limited this task to those two).
- New `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoCollectionPanels.swift`: `CollectionOverTimePanel`, `OwnAndPlayByDecadePanel`, `TastePanel`, `ShelfLifePanel` and `ServerActivityPanel`, moved out of `CupertinoHome.swift` with their helpers and `@State`. Draws the same as before, except Shelf life no longer shows its four small "Longest since a play" covers (they become "Waiting longest" in H3); `longestCovers` deleted.
- `CupertinoInsights`: new "Your collection" section above "Lenses" (collection 2:1 decades, taste 1:1 shelf life; one column under 860 wide); `.task` calls `state.refreshHomeDashboard()`.
- Home still shows the panels through the new views.
- Not done, by the owner's scope: item 3 (Server activity in Settings, Services), items 4 and 5 of H2. `ServerActivityPanel` is moved (item 1) but only Home uses it.
- Tests: added `rendersInsightsYourCollection` (wide and stacked). Filtered run on a Mac: `swift test --filter "HomeRenderTests|CupertinoPagesRenderTests|ConnectionsServicesRenderTests"`, 32 tests in 3 suites, passing. Full suite not run (owner rule). Not published or deployed.
- **Next action:** H2 items 3 to 5, then H3 (the new Home).

## 2026-11-14 — macOS Home marquee H1 items 3 and 4: tests and filtered run (PR #1077)

- PR [#1077](https://github.com/abucalip/navi-librarian/pull/1077), squash-merged as `304ae87a`. Plan: `docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` slice H1, items 3 and 4.
- Added: a singular "1 listen in 7 days" figure test, and a test that summary figures are left out when nil (no added dates, no listen series).
- Filtered run on a Mac: `swift test --filter "HomeDashboardTests|HomeScreenTests"`, 84 tests in 2 suites, all passing. Full suite not run (owner rule). No visible change; not published or deployed.
- **Next action:** H2 (charts to Insights, Server activity to Settings), Sonnet, Medium.

## 2026-11-14 — macOS Home marquee H1 item 2: HomeScreen rules (PR #1076)

- PR [#1076](https://github.com/abucalip/navi-librarian/pull/1076), squash-merged as `92a73182`. Plan: `docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` slice H1, item 2.
- `HomeScreen` (`macos/Sources/DiscairUI/Model/HomeScreen.swift`): `shelfTiles` (arrivals then recently added, capped at six), `shelfStatus` and `shelfSubtitle`, `stageFraction`, `waitingCaption` and `waitingSubtitle` (with `monthAndYear`), `nextPicks` (wrapping, current pick left out, at most six), and `summaryFigures` (nil figures left out; stale listens name their last day).
- **Choices:** arrived tiles take an `arrivedDates` map from the caller, since `ArrivalRow.arrived` has no date (no date gives "Arrived recently"); recently added takes resolved `NavidromeAlbum`s, and undated albums are skipped.
- **Tests:** `swift test --filter "HomeScreenTests|HomeDashboardTests|HomeRenderTests"` on a Mac, 89 tests in 3 suites, pass. Full suite not run (owner rule). CI on the head: compile, container-smoke, lint-changed, test-and-build and validate-container passed.
- **Next action:** H2 (charts to Insights, Server activity to Settings), Sonnet, Medium.

## 2026-11-14 — macOS Home marquee H1 item 1: Home dashboard data (PR #1075)

- PR [#1075](https://github.com/abucalip/navi-librarian/pull/1075), squash-merged as `ed3faa84`. Code PR, not a docs commit. Plan: `docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` slice H1, item 1.
- `HomeDashboard` (`macos/Sources/DiscairUI/Model/HomeDashboard.swift`): `longestUnplayed` rises from four to six (`longestUnplayedLimit`), filled from the oldest-played albums when never-played ones run short. New `recentlyAdded` (`recentlyAddedLimit` = 6): newest dated albums, excluding albums shown in the capped `arrivals` rows; empty when the album list was not read; independent of Librarian reachability.
- `CupertinoHome.swift`: the four small covers under Shelf life take `prefix(4)`, so Home is unchanged.
- **Tests:** `swift test --filter "HomeDashboardTests|HomeRenderTests"` on a Mac, 41 tests in 2 suites, pass. Full suite not run (owner rule). CI on the head `f7863970`: `compile`, `container-smoke`, `lint-changed` and `validate-container` passed; `test-and-build` passed later; all five checks passed (recorded 2026-11-14). The macOS Swift tests run locally only (owner removed the macOS CI workflow).
- **Interpretation to confirm:** "already shown in step 1" read as the capped arrival rows only, so an arrived album past the cap can appear in recently added.
- **Next action:** H1 item 2 (`HomeScreen` pure functions and tests), Haiku, High.

## 2026-11-14 — Client efficiency: player-bar position readers split out (PR #1073)

- PR [#1073](https://github.com/abucalip/navi-librarian/pull/1073), merged as `a25c3460`. Docs direct to `main` on the owner's instruction. `CupertinoPlayerBar`: the progress fill and the waveform, the two readers of the 4 Hz `position`/`fraction` in the bar, are now their own views (`BarProgress`, `BarWaveform`), so a tick no longer rebuilds the whole bar (cover, disc lookup, text).
- **Why:** a 10 s `sample` of the installed build playing a track (10.8 % of one core) showed the main thread mostly idle; the Discair work left was `PlayerBarCover.body` and `CupertinoPlayerBar.body` re-evaluating every tick.
- **Result (owner, by eye on Activity Monitor, one track, not a scripted A/B):** playing 10 to 15 % after #1072, 8 to 11 % after this change; about 40 % before #1072. Judged close to the floor (audio decode and the 4 Hz tick); further cuts would need a slower tick or fewer features, not recommended. No `macos_cheap.sh` three-run table recorded.
- Tests not run (view-structure refactor only).
- **Next action:** S3 to S5 re-baseline with the clock, disc and bar fixed, the hidden-window check for G2, then M1 and M2.

## 2026-11-14 — Client efficiency: spinning disc moved to Core Animation (PR #1072)

- PR [#1072](https://github.com/abucalip/navi-librarian/pull/1072), merged as `179a8e33`. Docs direct to `main` on the owner's instruction. `DiscView` (`macos/Sources/DiscairUI/Chrome/NowPlayingArtwork.swift`) no longer uses a 30 Hz `TimelineView(.animation)`; the disc is drawn once to a bitmap (`ImageRenderer`) and turned by a `CABasicAnimation` on a child layer kept centred in an `NSViewRepresentable`, paused in place when not playing, still off under Reduce Motion. The sleeve slide (`DiscSleeve`) is unchanged.
- **Why:** after #1071 the owner still saw about 40 % CPU and a lagging track clock while a track played. A 10 s `sample` of the playing app showed the main thread mostly waiting on Core Animation commits (`CA::Transaction::commit`), with the player-bar disc `TimelineView` the only per-frame driver; per-frame main-thread work delays the 4 Hz `position` tick, which is the lag. The #1071 A/B (Home, same track) did not catch it, probably because that track's disc was not drawn.
- **First version was wrong:** it rotated the SwiftUI-managed layer, so the disc orbited the artwork instead of turning in place. Fixed in the same PR by rotating a centred child layer.
- **Not measured:** no CPU A/B is recorded for this change; the owner merged after trying a build. Re-measure S3 with a disc image present before quoting a number. The other `TimelineView(.animation)` user, `SlideshowBackdrop` (20 Hz, Now Playing only), is untouched.
- **Next action:** S3 to S5 re-baseline with the clock and disc fixed, the hidden-window check for G2, then M1 and M2.

## 2026-11-14 — Client efficiency: M7 merged (PlaybackClock without a TimelineView)

- PR [#1071](https://github.com/abucalip/navi-librarian/pull/1071), merged as `5edb1b27`. `PlaybackClock` now renders `content(player.displayPosition())` from the observed `position`; no `TimelineView`. Docs direct to `main` on the owner's instruction.
- A/B on four Release builds, same track, three runs each (Discair CPU, median, share of one core): playing 7.95 % before #900, 31.85 % at #900, 38.40 % on `main`, 7.05 % with the change; paused 1.70 % with the change (1.5 % before #900). The owner saw no lag or jumps while playing, after a seek, or after pause and resume, so the gate fallback was not used. Table in `docs/plans/client_efficiency_results.md` ("M7 A/B").
- Tests: `swift test --filter PlayerModelTests` (32 passed); full suite not run. Not published.
- **Next action:** S3 to S5 re-baseline with the clock fixed, the hidden-window check for G2, then M1 and M2.

## 2026-11-14 — Client efficiency: PlaybackClock regression pinned to PR #900

- Docs direct to `main` on the owner's instruction. No app code changed. `docs/plans/client_efficiency_results.md` gains "S2 A/B across PR #900"; `docs/plans/client_efficiency.md` M7 gains the evidence and a preferred variant.
- **Result:** paused idle CPU on Home, same track, three runs each: 1.50 % of one core on `be9738d0^` and 30.45 % on `be9738d0` (PR #900, which introduced `PlaybackClock` for the clock-lag fix). The idle cost arrived with that wrapper. A bare 4 Hz `TimelineView` in a throwaway app ran at 4 Hz (2 to 4 % CPU), so the display-rate behaviour is specific to Discair's window or bar and is still unexplained.
- **Added to M7:** preferred variant, drop the `TimelineView` and render from the observed `position` with `displayPosition` kept as a computed value; gate on `.playing` as the fallback. Needs a playing-state A/B first (S3 on `be9738d0^`, `be9738d0`, `main`) and the owner's go-ahead.
- Not measured: playing state across the three builds; whether the timeline closure itself runs at display rate. The clock-lag link (main thread saturated, model tick late) is an inference.

## 2026-11-14 — Client efficiency P0-2: macOS S1 and S8 to S10 (PR #1069)

- PR [#1069](https://github.com/abucalip/navi-librarian/pull/1069), merged as `43a29414`; this entry and the plan's progress line are docs direct to `main` on the owner's instruction. Adds `scripts/perf/macos_launch.sh` and fills S1 and S8 to S10 in `docs/plans/client_efficiency_results.md`. No app code changed.
- Short protocol agreed with the owner, one run each (no spreads): S1 0.88 s to first window (10 s pauses); S8 footprint 147 to 380 MB and nothing released a minute later, `leaks` only 22 KB (supports M3); S9 +31 MB open, about 14 MB retained; S10 CPU does not follow bitrate. A hang occurred during S10 (cause unknown, no crash report); the owner relaunched the app.
- **Next action:** S11 needs a throttling tool; three-run repeats of S8 to S10, the S3/S5, S8/S9 and S6 traces and the G2 hidden-window check remain; P0-3 not started.

## 2026-11-14 — Client efficiency: M7 recorded (PlaybackClock fix)

- Docs direct to `main` on the owner's instruction, after PR #1068 merged (`f5fdb638`). `docs/plans/client_efficiency.md` gains step M7 (`PlaybackClock` renders its `TimelineView` only while playing), placed after A1 in the order table (later steps renumbered); `docs/PROJECT_STATUS.md` notes the finding. No code changed.
- **Next action:** the owner decides whether to start M7; then S3 to S5 traces, the hidden-window check for G2, S1, S8 to S11.

## 2026-11-14 — Client efficiency P0-2: SwiftUI-instrument trace of idle Home

- Docs only. Adds the trace findings to `docs/plans/client_efficiency_results.md` (S2) and updates the P0-2 status in `docs/plans/client_efficiency.md`. No code changed; the trace file is not committed.
- **Method:** `xctrace record --template SwiftUI --attach` on the running Release build, 15 s, Home with a paused track loaded, window visible; one trace.
- **Result:** the main thread is saturated by AttributeGraph updates (`ViewGraphRootValueUpdater.render`, about 70 % of samples) with no Discair-module frames on top. SwiftUI view-body updates are not the cost: 4,394 timeline-filter updates, 86 ms in total. The graph updates about 120 times a second (`External: UInt32` and `External: Time` changes; `ForEach` and `GlassContainer` evictors re-run each frame). The driver is not identified.
- **Limits:** one trace, with profiler overhead; empty backtraces; window visible, so G2's hidden-window evaluation count is still not measured. S3 and S5 traces, Allocations and the Time Profiler run of S6 are not done.
- **Next action (superseded by the bisect below):** bisect idle Home by element.
- **Bisect result (same day, same PR):** a throwaway copy of `macos/` outside the repository with an environment switch per element, Release build, one run per variant (reference ranged 24 to 36 %). Removing the whole player bar takes Discair from about 26 % to 0.3 % and updates to 0; making `PlaybackClock` static, or skipping its `TimelineView` unless the phase is `.playing`, does the same. Glass, waveform graph, blurred plate, bar cover, large cover, notice banner, sidebar, switches, tint animation and a fixed timeline start date have no effect; Home content removal saves about 13 points. Why a 4 Hz timeline updates the graph at display rate is not explained. First four runs had a stray second instance running and are marked as such. Full table in `docs/plans/client_efficiency_results.md`. No app code changed; the owner must authorise a fix step. Not measured: playing state, hidden window (G2), repeats.

## 2026-11-14 — Client efficiency P0-2: macOS S3–S7 baseline and gate decisions (PR #1067)

- PR [#1067](https://github.com/abucalip/navi-librarian/pull/1067), merged as `fd4757cf`. Fills the macOS S3–S7 rows and an S7 Reduce Motion reference, three runs each, plus short probes. Docs only.
- **Gates:** G1 not met (S5 − S4 = −2.1 points), so M5 closes without work. G2 met by the letter but marginal (S7 26.8 % vs 24.8 % with Reduce Motion); the owner opened M6.
- **Finding:** Discair uses about 25 to 29 % of one core in nearly every state (S6 paused on Now Playing 13.75 %), regardless of screen, window visibility or Reduce Motion; the cause is unidentified. Slideshow photos add about 170 MB (207 to 376 MB). The earlier marquee lead was rejected. WindowServer varied between about 3 and 30 % without a found cause. S2 had a paused track loaded.
- **Next action:** the owner runs the SwiftUI-instrument trace of idle Home in a new session; then S1, S8 to S11 and the other required traces. P0-2 is still in progress; P0-3 not started.

## 2026-11-14 — Client efficiency P0-2: macOS S2 idle baseline (PR #1066)

- PR [#1066](https://github.com/abucalip/navi-librarian/pull/1066), merged as `2f9a55e2`. Fills the macOS S2 row of `docs/plans/client_efficiency_results.md` and fixes `scripts/perf/macos_cheap.sh`, whose wakeups column printed top's running IDLEW total (about 38,000) instead of a per-second rate.
- **Result (Release build, inferred SHA `fab8032d`, M2 16 GB, macOS 26.2, AC power, Discair reopened on Home, nothing played, Firefox closed, no other audio; three five-minute runs):** Discair median 31.7 % of one core (28.2, 31.7, 31.8), WindowServer 5.4 % (2.9, 5.6, 5.4), about 0.02 idle wakeups per second, footprint 115 MB. A steady load with almost no wakeups points to continuous drawing or computing, not a timer; the plan's section 3 did not predict it. Cause not identified.
- **Discarded attempts, recorded in the results file:** the app was not on Home (Discair 23.4 %, WindowServer 2.8 %, 212 MB); then Firefox and `coreaudiod` were busy (Discair 41.8 %, WindowServer 31.6 %), so most of that WindowServer load was not Discair's.
- **Limits:** the SHA is inferred (the binary was built three minutes after the `fab8032d` merge and `macos/` is unchanged since); refresh rate, server version and library not recorded; run 1 sits about 3.5 points below runs 2 and 3, unexplained. S1, S3–S11, the gates G1 and G2 and the three traces are not done. No app code changed.
- **Next action:** Time Profiler and SwiftUI instrument trace on idle Home, then S7 (minimized), then S3–S6. A 5 s `sample` of idle Home (follow-up PR) shows SwiftUI/AttributeGraph updates; the marquee guess was rejected and S2 had a paused track loaded; cause unknown.

## 2026-11-14 — Client efficiency P0-1: baseline protocol and results file

- Direct to `main` (owner instruction). Adds `docs/plans/client_efficiency_results.md` (scenarios S1–S11 with numbered manual steps, cheap-tool commands, run header, and empty macOS and Android result tables with gate-decision rows) and `scripts/perf/macos_cheap.sh` and `scripts/perf/android_cheap.sh`, which each print one markdown row per run. Raw output goes to `~/discair-perf-raw` by default, outside the repository. No measured value exists yet; every result cell is blank.
- **Tests run:** `bash -n` on both scripts. `macos_cheap.sh` run against a live process (short two-sample run) and against the running Discair process; `android_cheap.sh` run with no device (clean error) and with a mock `adb` that returned canned `meminfo`, `gfxinfo` and `top -H` output (parsing checked; the mock is not recorded). No device run and no release-build measurement.
- **Next action:** P0-2 (macOS baseline, owner-driven UI scenarios) and P0-3 (Android baseline on the Galaxy S20 FE); the first Android run must check the parsed `meminfo` and `top -H` values against the raw files.

## 2026-11-14 — Opportunistic simplification rule and CI lint ratchet (PR #1065)

- Docs direct to `main`: `7606ae53` (the rule in `docs/DEVELOPMENT_WORKFLOW.md`, plus a "Simplification candidates" section in `docs/ACTIVE_WORK.md`) and `65f49fd6` (lint-style checks).
- PR [#1065](https://github.com/abucalip/navi-librarian/pull/1065), merged as `f28a132e8de477a9130755445bcda91d60ed2a71`. New `Lint changed files` workflow and `scripts/check_lint_changed.py`: pylint 4.1.3 (installed in the job only) runs a small set of simplification checks on the Python files a PR changes and fails only on findings that are more frequent than in the base version of the file. Not gated: unused arguments, size checks, broad `except`. `tests/test_check_lint_changed.py` and the script were added to the `python-syntax.yml` compile list.
- **Tests run (filtered):** `tests.test_check_lint_changed`: 5 passed. End to end locally against `origin/main`: a new file with an unused import and a needless else failed; a one-line change to `navidrome_server.py` passed. Full suite not run (owner rule).
- **CI on the final PR head `aa61ac6f`:** `compile`, `container-smoke`, `lint-changed`, `test-and-build` and `validate-container` passed. The first run of `lint-changed` (head `8b0a14a1`) failed on an unused `Counter` import in the new script; fixed in `aa61ac6f`.
- **Limits:** findings are counted per file and message, so a moved finding, or one fixed while an identical one is added, is not flagged. Workflows on `main` at `f28a132e` were still running when this was written.
- **Next action:** the first real PR that changes Python files will show whether the ratchet is quiet enough for normal work.

## 2026-11-14 — Radio stage 2, S2-5: menu bar item (PR #1063)

- PR [#1063](https://github.com/abucalip/navi-librarian/pull/1063), merged as `59ca29194f1ec099c2f19e8a74ba1e1d1f69df04`. A `MenuBarExtra` in window style: `radio` symbol while a station plays, a note for a library song, the title cut at 30 characters while "Show title" is on. Popover (mockup D2): cover or logo, LIVE and station (or album), title, artist; Stop or Play/Pause, Next (library song), the shared `DownloadButton`, Retry when unreachable, the sleep timer (new `.neutral` pill); the first four favourites with ⌘1 to ⌘4; Open Discair. Settings › Radio gained the two switches (`UserDefaults`, on by default). It reads `AppState` only; no new requests.
- **Tests run (filtered):** `MenuBarContentTests|rendersMenuBarPopover|RadioSettingsModelTests|rendersRadioSettings|SleepTimerTests|MiniPlayerTests`: 38 passed; package builds, bundle built; full suite not run. Popover renders looked at against the mockup.
- **Not verified:** the item in the real menu bar, popover focus and dismissal, Open Discair raising the window, Download against a real station, Night mode, VoiceOver, the switches.
- **State:** all stage 2 slices (S2-0 to S2-5) are built. Next: the owner's live checks, S2.10.

## 2026-11-14 — Radio stage 2, S2-4 items 3 to 5: Settings › Radio, station shortcuts, tests (PR #1062)

- PR [#1062](https://github.com/abucalip/navi-librarian/pull/1062), merged as `dbad617299498c36b2fa7351b3c679247d68c599`. **Settings › Radio:** a tab after Playback (`CupertinoRadioSettings`, `RadioSettingsModel`): the server's scrobbling switch (disabled with "Last.fm is not set up on the server"; a refusal restores it and shows the server's sentence), the app address read only ("Changed on the web Radio page"), and a logo Change… (open panel, one image, size checked before the file is read, over 2 MB refused unsent) and Reset for each station; the logo store forgets the station and the list reloads afterwards.
- **Shortcuts (E1):** Controls › Stations lists the first nine favourites with ⌘1 to ⌘9 and "Stop Radio"; menu shortcuts, so they work from any screen. The playing station is left alone, an unreachable one is retried (`StationRules.shortcutTarget`). **Request added:** one station-list read after connecting when nothing has read it (`loadStationsForShortcuts`), so the keys work before the Radio page is opened.
- Tests actually run: `swift test --skip-update --filter "StationRulesTests|RadioSettingsModelTests|ReconnectPolicyTests|SleepTimerTests|rendersRadioSettings"`, 50 passed. The package builds; the bundle was not rebuilt; full suite not run (owner rule).
- Not verified: the open panel, a real upload and reset, the switch against a real Last.fm setup, the shortcuts in the real menu and from another screen, Night mode, VoiceOver.
- Next: S2-5, the menu bar item (D2), including the menu bar switches in Settings › Radio.

## 2026-11-14 — Radio stage 2, S2-2 items 1 to 3: tap spike, live engine, PlayerModel station state (PR #1053)

- PR [#1053](https://github.com/abucalip/navi-librarian/pull/1053), merged as `3e8c12ebae605f85b2fcf89baed2a42aeead0ad7`. **Item 1, the tap spike, failed:** `MTAudioProcessingTap` got no samples on live MP3 and AAC (public Icecast streams, a local pass-through relay, and two real relayed stations, Radio Krimi and Radio Swiss Jazz, run by the owner). The same tap code gave samples on a local file, so the code is sound; AVFoundation does not feed taps on live progressive streams. Table in `macos/DESIGN.md`. **Owner decision (2026-11-14): B1 everywhere** (the 3 pt hairline, no level meter); the tap and `levels` were not built. Tap callbacks built inside a `@MainActor` class trap at run time on the audio thread, so they need a `nonisolated` context (noted in `DESIGN.md`).
- **Item 2:** `DiscairAudio/LiveStreamPlayer.swift`: the `LiveOutput` protocol (`start(url:)`, `stop()`, `volume`, `onState`) and `LiveStreamPlayer` (AVPlayer; state connecting, playing, stalled, failed only). The `discair-audio-spike live` command plays streams or `--relayed` stations through it.
- **Item 3:** `PlayerModel` gains `live` (`LiveSession`: station id, name, logo path, started at, phase connecting, playing, reconnecting, unreachable), `playStation(_:)` and `stopStation()` (in `PlayerModel+Live.swift`). Play/Pause stops or restarts the station; Next and Previous step through favourites in server order and wrap (a station that is not a favourite goes to the first or last; nothing with fewer than two favourites); seek is ignored; a playing library song is paused and the queue is untouched; a library song stops the station; the last station id is in `UserDefaults` (`discair.radio.lastStation`) and nothing is saved with the queue. A non-relayed `.pls` or `.m3u` address gets the S2.6 sentence without the address. `AppState` supplies the Librarian base address (the relay path is relative) and the favourites.
- Tests actually run: `swift test --skip-update --filter "LiveSessionTests|PlayerModelTests|GrowingFailureTests|MiniPlayerTests|SystemMediaTests|CrossfadeIntegration|PlaybackSkipFeedback|BugBatchTests|StationsModelTests"`, 105 passed, 13 of them new `LiveSessionTests` with a `FakeLiveOutput`. `swift build` of the package succeeded. Full suite not run (owner rule). `Package.swift` changed (the spike target depends on `DiscairLibrarian` and `DiscairAudio`), so `select-tests.sh` would call for the full suite.
- Not verified: that sound plays through `LiveStreamPlayer` inside the app (no UI yet; only the spike was heard); `LiveStreamPlayer` has no unit test. `config.env` has a typo in `LIBRARIAN_URL` (`192.168.1..12`), left unedited.
- Next: S2-2 items 4 to 8 (Radio page row click and On Air panel, the live bar with the B1 hairline, `SystemMedia`, mini player and widget `isLive`, tests), then S2-3.

## 2026-11-14 — Radio stage 2, S2-1 items 8 to 10: Edit Tags, states, tests (PR #1052)

- PR [#1052](https://github.com/abucalip/navi-librarian/pull/1052), merged as `522d2fbfa8c8b6698b5fad99c3c40e0d1503a3d4`. Edit Tags (E5): right-click "Edit Tags…" (and a VoiceOver action) opens `StationTagsSheet`: removable tag chips over a field, Return adds, Save sends the whole list (a tag still typed is added first), Cancel closes; a rejected tag stays typed with its sentence. The logic is the pure `TagDraft` on `StationRules.check`; Save goes through `StationsModel.setTags`, so a refusal restores the old tags and shows the server's sentence on the page. The row menu also toggles the favourite. Item 9 (loading, empty, error with Try again) was already built in #1051; this PR only adds its render test. The PR also carries the Android version bump to 1.3 (`versionCode` 13) in `android/app/build.gradle.kts`. No server change.
- Changed from the mockup: no tag reordering; a count line ("3 of 10 tags. Up to 24 characters each.") was added.
- Tests actually run: `swift test --skip-update --filter "RadioClientTests|StationRulesTests|StationsModelTests|rendersStations"`, 63 passed, including five new `TagDraft` tests and the Day renders of the empty page and the sheet. Full suite not run (owner rule). No macOS CI exists. CI on the PR head: `compile`, `container-smoke` and `validate-container` passed; `test-and-build` was still pending when last checked, before the merge.
- Not verified: the right-click menu, sheet focus and Return/Escape in a real window; Night mode; the error-state render; VoiceOver. The Android version bump was not built.
- S2-1 is complete apart from those checks. Next: S2-2 (live playback), which starts with the tap spike.

## 2026-11-13 — Radio stage 2, S2-1 item 7: the Radio page (PR #1051)

- PR [#1051](https://github.com/abucalip/navi-librarian/pull/1051), merged as `e07189cc0be4b0aa651e28d414473536d368ce4a`. `CupertinoStations` is now mockup A2: title and count, tag chips, station list (logo 34 pt, name, status sentence, first tag, star with the spoken label "Favourite, on/off"), and the On Air panel ("Nothing playing. Choose a station."), which moves under the list below 880 pt. A row click only selects; arrow keys move the selection. `StationLogoStore` and `StationLogo` fetch each logo once per station and size (memory, plus disk when the media cache is on; cleared by Reset saved data). `StationsModel.showForPreview` serves the render test. Simple loading, empty and error (Try again) states were added so the page is not blank. No server change.
- Changed from the plan: first tag only per row (the mockup lists two); no playing hero in the panel (needs S2-2); no Edit Tags yet.
- Tests actually run: `swift test --filter "RadioClientTests|StationRulesTests|StationsModelTests|CupertinoPagesRenderTests"`, 61 passed, including `rendersStations` (Day). Full suite not run (owner rule). No macOS CI exists. The owner saw the Day render.
- Not verified: Night mode; logos against a real server (the render shows blank squares); keyboard use in a real window; "window hidden or minimised" polling.
- Not done: S2-1 items 8 and 9 (Edit Tags, states checked against the plan).

## 2026-11-13 — Radio stage 2, S2-1 items 4 to 6: rules, stations model, navigation (PR #1050)

- PR [#1050](https://github.com/abucalip/navi-librarian/pull/1050), merged as `579fbc9268d146674d17e71ebb22754fc3603334`. `macos/Sources/DiscairUI/Model/Stations.swift`: `StationRules` (row sentence, tag chips, tag checks) and `DownloadState` (S2.7 table, Owned first), pure. `StationsModel` (`AppState.stations`, behind a `StationsSource` protocol): list in server order, live titles, tag filter, loading/empty/error states, S2.5 polling (list once a minute, titles every 15 s) driven by `pageVisible`; favourite and tag changes show at once, send, then reload, and a refusal restores the old value with the server's sentence. `Screen.stations` and the sidebar row "Radio" under Library. No server change.
- Changed from the plan: no Go/View menu entry (no other page has one; E2 not chosen). `CupertinoStations` is a placeholder (title and count) so the new `Screen` case compiles. `pageVisible` follows the screen only; window hidden or minimised comes with the page.
- Tests actually run: `swift test --filter "StationRulesTests|StationsModelTests"` passed locally, 37 tests. Full suite not run (owner rule). No macOS CI exists. Nothing was looked at in a window; no render test yet (item 7).
- Not done: S2-1 items 7 to 10 (the page, Edit Tags, states, render test).

## 2026-11-13 — Radio stage 2, S2-1 items 2 and 3: client calls and tests (PR #1049)

- PR [#1049](https://github.com/abucalip/navi-librarian/pull/1049), merged as `8695091a78ce981ff26a703138d6490dd8e53e5d`. `macos/Sources/DiscairLibrarian/RadioClient.swift`: `radioStations`, `radioNow(station:)`, `radioNowAll`, `setRadioFavourite`, `setRadioTags`, `radioLogo(station:size:)`, `radioScrobbling`, `setRadioScrobbling`, `uploadRadioLogo`, `resetRadioLogo`, `radioSettings` (`RadioSettings`, `RadioLogoSize`). No server change.
- `LibrarianClient` send path takes an optional content type (default JSON) so a logo upload sends the raw image; existing calls unchanged. An unreadable `/now` body reads as unavailable; an empty or over-2 MB logo is refused before sending.
- Tests actually run: `swift test --skip-update --filter "RadioClientTests|RadioDecoderTests"` passed locally (all radio fixtures covered, plus paths, bodies, id encoding, refusals, 401 re-login on a write). Full suite not run (owner rule). Required CI (compile, container-smoke, test-and-build, validate-container) passed; no macOS CI exists, so the Swift tests were not run there.
- Not done: S2-1 items 4 to 10 (`StationRules`, `StationsModel`, navigation, the page, Edit Tags, states, render test).

## 2026-11-13 — Radio stage 2, S2-1 item 1: decoders (PR #1048)

- PR [#1048](https://github.com/abucalip/navi-librarian/pull/1048), merged as `8c17aaae5a7a1b8dc770063e72b1dfdfdec4971c`. `macos/Sources/DiscairLibrarian/Radio.swift`: `RadioStation` (no `stream_url`; description, debug description and mirror leave the address out), `RadioNow` with `RadioNowState` (unknown words decode as `unknown`), `RadioNowAll`, `RadioScrobbling`; lossy list decoding.
- Tests actually run: `swift test --skip-update --filter RadioDecoderTests`, 9 passed. Full suite not run (owner rule). No macOS CI exists.
- Not covered yet: the client calls and their per-fixture tests (`RadioClientTests`) and the `radio_station_favourite`, `_tags` and `_logo` fixtures, which belong to item 2.
- Next: S2-1 items 2 to 10.

## 2026-11-13 — Radio stage 2 documents, S2-0 (PR #1047)

- PR [#1047](https://github.com/abucalip/navi-librarian/pull/1047), merged as `567932f50c6a1053e3337deea3543ff55deeb388`. Docs only: `RADIO_PLAYBACK_CONTRACT.md` section 5 (owner choices, corrections, request budget, live playback rules, Download states, slices) and section 11 (owner's deployment report); `MACOS_CLIENT_CONTRACT.md` scope and window list; `macos/DESIGN.md` "Radio (stage 2)"; `ACTIVE_WORK.md` slice lines.
- Checks: relative links in the four files resolve; `git diff --check` clean. No code, tests or CI-relevant files changed.
- The owner's deployment checks are recorded as reported by the owner; not re-run by the agent.
- Follow-up on `main` (docs only, same rule): the active queue now says stage 2 started and S2-0 merged, with this log entry.
- Next: S2-1 (stations, Radio page, favourites, tags) on the Mac.

---

## 2026-11-13 — Archive completed proposals and plans

- Reviewed the current GitHub `main`, recent commits, open PR search results, the project status and active-work queue, requirements, development workflow, test plan, and the candidate proposal/plan documents.
- Moved the full contents of eight closed documents into `docs/archive/completed/`: album and artist page redesign records, album paths, Android art themes, colour palettes, Brut layouts, hard-coded taste replacement, and artwork.
- Kept short pointer files at the original paths because source comments, tests, contracts, or documentation refer to those paths. Updated active-work links and the archive index. Updated the project-status check date and archived palette reference.
- Completion means the planned implementation/build slices are merged; it does not claim outstanding owner device/browser checks, publication, deployment, or runtime verification. Those gates remain explicitly recorded in the active queue and archived document status.
- Documentation-only change, committed directly to `main` under the repository workflow. No application code, tests, configuration, provider traffic, publication, or deployment changed. No application tests or CI were run because no executable files changed.

---

## 2026-11-13 — Colour palettes P4 and P5: Flow night palettes and closeout (PR #1045)

- PR [#1045](https://github.com/abucalip/navi-librarian/pull/1045), merged as `8c10438897f3b16873916848149bde1f3c636028` from head `05967dc67a07872ec191e1cbc82d4d179436b0b7`; required CI passed (compile, container-smoke, test-and-build, validate-container). `Palette.kt` gained `FlowEmber`, `FlowMoss`, `FlowPlum` (in `Palettes.Dark`, after the Soft Brut night palettes). `FlowRules.chevron` has their greys; `FlowRules.barHairline` (new) is white at 10% on a dark palette and black at 8% on a light one, used by `flowBar`. The wash behind the album and player was checked and left as is: artwork tints are always dark, and a dark palette uses them unchanged. P5: `ACTIVE_WORK.md`, `PROJECT_STATUS.md`, this log and `docs/archive/completed/palettes.md` updated; `android/DESIGN.md` has a short palettes note.
- Verified, filtered (JDK 17): `FlowTest` (16), `PaletteTest` (19, counts 42/25/17), `SoftBrutTest` (16), `ExistingLayoutsTest` (3), all passed. Full suite not run. Not seen on a device; no screenshot comparison with the palette PNGs.
- Palettes plan closed (P1 to P5 merged). Next action: the owner's phone check of the 13 palettes.

## 2026-11-13 — Colour palettes P2 and P3: Soft Brut night and Flow day palettes (PR #1044)

- Merged as `e3c804eafa2c5ef608e99646888a3ddceefe7907` from head `e960749b25638ede830db30cb59c35ec0cbf51c6`; required CI passed (compile, container-smoke, test-and-build, validate-container). `Palette.kt` gained `SoftBrutMidnightMint`, `SoftBrutPlumPeach`, `SoftBrutNavySky` (in `Palettes.Dark`) and `FlowForest`, `FlowRaspberry`, `FlowViolet` (after `Flow` in `Palettes.Light`). Cover Stack content on an accent fill now uses `onAccent` (nav cell icon, Home and Discover tags, Discover small buttons). `FlowRules.switchOff` and `FlowRules.chevron` replace the two Flow literals; the current `flow` palette keeps its values.
- Verified, filtered (JDK 17): `SoftBrutTest`, `FlowTest`, `PaletteTest` (counts 39/25/14), `ExistingLayoutsTest`, `AppearanceRulesTest`. Full suite not run. Not seen on a device; no screenshot comparison. On night palettes `accentText` is the accent (it passes 4.5:1 on the dark page), so the test asserts that instead of `text`.
- Next action: P4 (Flow night palettes, the bar hairline and the night checks of section 5.3).

## 2026-11-13 — Colour palettes P1: Soft Brut day palettes (PR #1043)

- Merged as `398cbb0ba925c9875d1f725ded595f9705414c24` from head `6628c4f5aaacb0d7d3ffe52e634df5acc9b38dee`; required CI passed (compile, container-smoke, test-and-build, validate-container). `Palette.kt` gained `SoftBrutMint`, `SoftBrutPeach`, `SoftBrutSky`, `SoftBrutLemon` (values from `docs/design/android-art-themes/palettes/roles.md`), listed after `SoftBrut` in `Palettes.Light`. No screen code changed.
- Verified, filtered (JDK 17): `SoftBrutTest` (12, new cases for spec values, shared status colours, contrast floors), `PaletteTest` (19, counts 33/22/20), `ExistingLayoutsTest`, `AppearanceRulesTest`. Full suite not run. Not seen on a device; no screenshot comparison with `docs/design/android-art-themes/palettes/`.
- Next action: P2 (Soft Brut night palettes and the `onAccent` audit), then the owner's phone check.

## 2026-11-13 — Paths Trail steps 3 to 5: artist sheet, artist pane bodies, album sheet (PR #1031)

- Merged as `04afccf076e9a469c90c08dc5a4d183b4edef623` (steps 1 and 2 had merged in PR #1030). Both Paths sheets now show the Trail from `docs/archive/completed/pathsredesign.md`: header with the start's picture, text tabs with a mark, links with their steps under them, a step that opens in place. `PathDetail`, `AlbumPathDetail`, the Back button, "Step n of N" and the arrows are removed; Back closes an open step first; the saved step stays an index into the server's list. Pane bodies lose their hero rows (the opened step's 72dp header carries them) and their cards sit on the sheet's ground. Sideman and Scene rows say the library state. New `TrailEntry`, `entries()` and `TrailList` (scrolls an opened step into view).
- Verified, filtered (JDK 17): `PathTrailTest` (new cases), `PathsTest`, `AlbumPathStepsTest`, `AlbumPathsTest`. Full suite not run. Not seen on a device.
- Next action: step 6 (`AlbumStep.detail` without the via, with `AlbumPathStepsTest`), the `Text` on `AccentDim` contrast case, then the owner's phone check (section 10 of the proposal).

## 2026-11-13 — Art themes F4 part 1: Flow Now Playing, Queue and Lyrics (PR #1026)

- Merged as `96b2162dfb6e5bd97a6df17c2eb831ff0c2322de` from head `c6cb1a3bfdae41010e2fb412b575588cf7c53b73`; required CI passed (compile, container-smoke, test-and-build, validate-container). `ui/player/FlowNowPlaying.kt` (top bar, 312dp cover at level 3 depth over the pastel wash, plain transport with a round Play, Queue/Lyrics/Equalizer/Crossfade entries), a Flow branch in `SeekBar` (4dp line, round thumb), a `flow` option in `CoverStackLyricsPanel`, one `flow` branch in `NowPlayingSheet`. Queue and Lyrics open as a sheet over Now Playing, as Soft Brut's now do (PR #1017), not as the full pages the mockup draws. Not drawn: the heart (no favourite action) and Sonic path (Crossfade takes its slot). Kept beyond the mockup: quality tag, lyric/fact line, status and sign-in, Earlier songs, long-press row actions, Track images, the sound graph. Other themes unchanged.
- Verified, filtered (JDK 17): `FlowPlayerRulesTest` (new), `FlowTest`, `ExistingLayoutsTest`, `CoverStackPlayerRulesTest`. Full suite not run. Not seen on a device; no screenshot comparison with `flow/player`; the Photos switch over the lyrics is untested.
- Next action: the owner checks Now Playing, Queue and Lyrics on the phone; then the rest of F4 (Radio, Downloads, Stats, Server, Settings, Equalizer, Crossfade).

## 2026-11-13 — Art themes F3 part 2: Flow Discover, Library and Search (PR #1025)

- Merged as `867fc559f9ae6781a46c74e6734b137f38a2b91a` from head `c4ded7e22630f709d67d47247879ccbc78efc17c`. Flow pages from `flow/discover` and `flow/library-search`, behind `isFlow()`; other themes unchanged. Details and differences from the mockups in `docs/ACTIVE_WORK.md` section 2l.
- Verified, filtered (JDK 17): `FlowPagesRulesTest` (new cases), `FlowTest`, `ExistingLayoutsTest`, `SoftBrutTest`, `InsightsTest`, `DiscoveryTest`, `NavRulesTest`. Full suite not run. CI result on the final head not re-checked by the agent. Not seen on a device; no screenshot comparison with the mockups.
- Next action: the owner checks Discover, Library and Search on the phone; then F4 (Flow player and the rest).

## 2026-11-13 — Art themes F3 part 1: Flow Album, Artist and Genre, and the bar blur (PR #1024)

- Merged as `70567d503a16ab50980a5e752b398d94ecb6d6b8` from head `2ab4ee84c8afeac3d94e5546537a586a023cbe2a`. Flow pages from `flow/album-artist-genre` (wash on the album, full-width photo on the artist, Paths beside Play, white status bar icons over the photo, genre grid) and the D3 bar blur on the navigation capsule and mini player. Other themes unchanged. Details in `docs/ACTIVE_WORK.md` section 2l.
- Verified, filtered (JDK 17): `FlowPagesRulesTest` (new), `FlowTest`, `ExistingLayoutsTest`. Full suite not run. CI result on the final head not re-checked by the agent. Not seen on a device; no screenshot comparison with the mockup.
- Next action: the owner checks the album wash, the blur and the artist status bar on the phone; then F3 Discover, Library and Search.

## 2026-11-13 — Art themes F1 follow-up: Flow grouped list and small controls (PR #1021)

- Merged as `7648531aba224cf5b4a188561176d5e432ad2ac2`. `FlowKit.kt` gains `FlowGroup`, `FlowListRow`, `FlowIconTile`, `FlowCircleButton` and `FlowTag` from `flow.css`; depth levels, capsule buttons and chips were already in #1020. No screen uses them yet.
- Verified, filtered (JDK 17): `FlowTest` (new depth and row-number test) and `ExistingLayoutsTest`. No screenshots; not seen on a device.
- Next action: F2 (Flow Home).

## 2026-11-13 — Soft Brut fixes batch 1 and Today's picks from the week's Current tastes lists (PR #1017)

- Merged as `b855d91c5d6724927eb8f892b2a1e40d0070f98b` from head `b8399386944dfd4031986ac3500230532417a8be`. Android (Soft Brut): genre on the same line as year and song count (album, artist); Queue and Lyrics open as sheets over Now Playing (`CoverStackPanel`); radio Now Playing sheet fills the screen, and the Paths step bar's extra rule is hidden in Soft Brut; artist Play narrowed with a Paths button (new `PlayerIcons.Paths`) beside Shuffle; album Paths replaces the album-level download; Home Recently added is a sideways row of the last 30 days, link "More" opens the full list.
- Both clients: `/api/dashboard-picks` draws only from the last 7 days of Current tastes lists and reshuffles on every request. New `discovery/lens_week.py` and `app/services/lens_week_picks.py` keep each day's list under `lens_week:current_tastes:<day>` (written on lens refresh and on read; not pruned); no list means empty picks. `build_dashboard_picks` is no longer called by the route. macOS Home refetches picks on each visit after the first (`LibraryModel.reshufflePicks`); Android reloads on each Home open.
- Verified, filtered: Python `test_lens_week`, `test_dashboard_routes`, `test_dashboard_service`, `test_discovery_lens_storage` (51 passed); Android `CoverStackPlayerRulesTest`, `CoverStackHomeRulesTest`, `SoftBrutTest`; macOS `LibraryModelTests`. Full suites not run. Not seen on a device or the Mac.
- Next action: the owner checks the fixes on the phone and Today's picks on both clients.

## 2026-11-13 — Another booklet button on macOS and Android, `booklets` in the artwork index (PR #1016)

- Merged as `a7f4e658600244282b4fb11b0bb6855aa279c92d`. Server: `intelligence/artwork/index.py` gains `_booklets` (every release's booklet by the existing rule: most pages, then the owned release, then the earlier date, then MBID; at most `BOOKLETS_CAP` = 8) and `to_response` adds `booklets`; `booklet` is unchanged and equals the first entry. Contract section and the five `artwork_index*.json` fixtures updated. macOS: `ArtworkIndex.booklets` and `bookletViews`, `BookletSheet` takes `booklets` and has the button and notice. Android: `ArtworkIndex.booklets`, `BookletView.others`, `anotherBooklet`, button and live-region notice in `BookletTab`.
- Verified, filtered: Python `test_intelligence_artwork_index` and `test_artwork_fixtures` (40 passed); macOS `BookletTests`, `ArtworkTests`, `NowPlayingArtworkTests`, `EditionPickerTests`, `LinerNoteTests` (51 passed); Android (JDK 17) `BookletTest`, `ArtworkIndexTest`, `NowPlayingArtworkTest`, `DiscoverPeekTest`. Full suites not run (owner rule). Not seen in a window or on a device. Not published or deployed.
- Next action: the owner looks at the button on the Mac and on a device.

## 2026-11-13 — macOS: remove Zine, add Night mode and the Appearance tab (PR #1015)

- Merged as `3fc8d652e32d02964158684684028fcb1f97b5b4`. Deleted `Themes/Zine`, the Anton, Space Mono and Source Serif 4 fonts with the `Resources/Fonts` package resource, the Zine Dock icon, the Theme menu and the Zine branches in the shared chrome; `ThemeID` keeps `cupertino`. Added `CUPalette` (Day, Night, optional accent hue; `CU.*` now reads it), `AppearanceModel` (saved in UserDefaults), `CupertinoAppearance` and a `SettingsTab.appearance`. `RootView` rebuilds the window on a change. Night is `#0B0B0D` with coral `#FF7A8F`; Day keeps `#D61F4A`.
- Verified locally, filtered: `AppearanceTests` (new), `CupertinoTokensTests`, `CommandPaletteTests`, `MiniPlayerTests`, `PipelineDockTests`, `ConnectionsServicesTests`, `GraphExplorerTests`, `OfflineTests`, `ScreenshotTests`, `BugBatchTests`, `LiveScreenshotTests`: 150 passed. Every slider hue reaches 4.5:1 for the text and accent pairs in both modes (5 degree steps). Full suite not run (owner rule); `Package.swift` changed, so `select-tests.sh` selects it.
- Night rendered offscreen for Home, Settings, Library and Album and viewed once; no Night screenshot test, because the palette is process-wide. Not checked: VoiceOver, every screen at every hue, a live window on the Mac. Not published or deployed.
- Next action: the owner runs the full macOS suite and looks at Night in the app.

## 2026-11-12 — Android art themes S4 part 2: Soft Brut Radio, Downloads and Library stats (PR #1012)

- Merged as `4652b1007a4e54c610708d765c2016ba9da7a56e` from head `2d7357e416f4950cd2b80ca7130fa064e00ddfba`. Added `ui/radio/CoverStackRadio.kt`, `ui/downloads/CoverStackDownloads.kt`, `ui/stats/CoverStackStats.kt` and `CoverStackRadioDownloadsStatsRulesTest`; `isCoverStack()` branches in the five screens; Cover Stack-only branches in the shared chart frame, line chart and chart style.
- Verified with JDK 17, filtered: `CoverStackRadioDownloadsStatsRulesTest`, `ExistingLayoutsTest`, `SoftBrutTest`, `ChartMathTest`, `RadioScreenTest`, `DownloadsRulesTest`, `StatsModelTest`. Full suite not run (owner rule).
- Differences from the mockups: 3-month range chip kept; decades stay paired-bar rows; Shelf life keeps its "not available" sentence; Download button words unchanged; Sleep timer and stream status kept on the live sheet.
- Not checked: no screenshots beside the mockups and no device check.
- Next action: the owner checks these on the phone; then Server, Settings, Equalizer and Crossfade, or F1.

## 2026-11-12 — Android art themes S3 part 3: Soft Brut Library and Search (PR #1010)

- Merged as `06d107c0cad9ff30390476cc33e0b4d93c408b43` from head `38f846bc5d79834330e0a2d6506e2c9b93804b3a`. Added `ui/library/CoverStackLibrary.kt`, `ui/search/CoverStackSearch.kt` and `PlayerIcons.Sort`; one `isCoverStack()` branch each in `LibraryScreen` and `SearchScreen`; a few helpers made internal.
- Verified with JDK 17, filtered: `compileDebugKotlin`, `ExistingLayoutsTest`, `SoftBrutTest`. Full suite not run (owner rule).
- Differences from the mockup: artist Play and queue actions in a three-dot menu; owned results first within each group; placeholder instead of a floating label.
- Not checked: no screenshots beside the mockup and no device check.
- Next action: the owner checks Library and Search on the phone; then S4 or F1.

## 2026-11-12 — Android art themes S2: Soft Brut Home (PR #1007)

- Merged as `2ea52f6548de9cf49450005876bf900ee918f045` from head `1657a6e9fddd79ca89a606e834cf183e220a62a8`. Added `ui/home/CoverStackHome.kt` and `CoverStackHomeRules.kt`, a `Layout.CoverStack` branch in `HomeScreen.kt`, `onLibrary` in `MainShell.kt`, and an optional shadow offset in `coverStackShadow`. No other theme's Home path changed.
- Verified with JDK 17, filtered: `CoverStackHomeRulesTest`, `HomeArtistsTest`, `SoftBrutTest`, `NavRulesTest`. Full suite not run; no screenshots against the mockup, nothing seen on a device; the composables have no automated test beyond compiling.
- Differences from the mockup: Insight button "Open album" (no Play without a library id); "new this month" is the trailing 30 days; Radio says "Stations" until a song is heard.
- Documents updated: `docs/ACTIVE_WORK.md` section 2l, `docs/PROJECT_STATUS.md`, `docs/archive/completed/ANDROID_ART_THEMES_PROPOSAL.md`. Next: owner phone check, then S3.

## 2026-11-12 — Android art themes S1: Soft Brut palette and shell (PR #1006)

- Merged as `d9417fa7c831c62b64d777ed978066aa30e54640` from head `7e4d2e6838755ffa56b757e03d1135126fa3f981`; compile, container-smoke, test-and-build and validate-container passed. Added palette `softbrut`, `Layout.CoverStack` (`ui/common/CoverStack.kt`, `ui/player/CoverStackPlayer.kt`), the outlined navigation bar and mini player, and layout-guarded branches in buttons, chips, tabs, switch, progress, tags, dividers, snackbar and sheet. `PaletteTest` and `NavRulesTest` were updated for the new theme; every other palette's layout and shape is still pinned by `ExistingLayoutsTest`.
- Verified with JDK 17, filtered: `SoftBrutTest`, `PaletteTest`, `ExistingLayoutsTest`, `NavRulesTest`, `AppearanceRulesTest`, `MotionTest`; `assembleDebug` clean. Full suite not run. No screenshots against the mockups and nothing seen on a device; the new control branches have no automated test beyond compiling.
- D4 taken as proposed (font pair suggested, not forced). D6 still open before F1. Not themed yet: Home, pages, player (S2 to S4).
- Documents updated: `docs/ACTIVE_WORK.md` section 2l, `docs/PROJECT_STATUS.md`, `docs/archive/completed/ANDROID_ART_THEMES_PROPOSAL.md`.

## 2026-11-12 — Android art themes step 0 (PR #1005)

- Merged as `35bb9a75d2d5d5442da3cfb4cce70c50b9401b03`. `ui/home/HomeArtists.kt` (distinct artists from Recent then Frequent, up to 8, unwired), `BrutalShape` now Float with the whole-number constructor kept (D1 as proposed), and `ExistingLayoutsTest` pinning every existing palette's layout and exact shape. `PaletteTest` adjusted for the Float radius. No screen changed.
- Verified with JDK 17, filtered: `HomeArtistsTest`, `ui.theme.*`, `NavRulesTest`; `compileDebugKotlin` clean. Full suite not run; nothing seen on a device.
- Open: D4 (font pair suggested or forced) before S1, D6 (Flow accent `#C2410C`) before F1. Documents updated: `docs/ACTIVE_WORK.md` section 2l, `docs/archive/completed/ANDROID_ART_THEMES_PROPOSAL.md` status and step table.

## 2026-11-12 — Redesign S3: check of D4 (album added dates) and D5 (phone handoff)

- Checked in code and the recorded fixture; no code changed.
- **D4 (added dates):** `GET /api/library/albums` serves `added` on each item, from Navidrome's album `created` (`discovery/search/index.py`, `discovery/search/query.py`). The Android DTO reads it and `RecentlyAdded.kt` uses it. The fixture `android/contract-fixtures/librarian/library_albums.json` has a value on all three items. No server change was needed. The field may be null; clients must treat null as unknown.
- **D5 (phone handoff):** Android did not call `savePlayQueue`. Built in the same PR: `player/NavidromeQueueSaver.kt` (signed `rest/savePlayQueue`, client name `discair-android`), `player/PlayQueueSync.kt` (newest-only send, up to 100 songs from the current one), hooks in `PlayerController` (pause, song change, queue edit, every 30 s while playing), wiring in `AppContainer.kt`, `Subsonic.PHONE_CLIENT`.
- Focused Android tests run locally with JDK 17: `PlayQueueSyncTest` (6), `NavidromeQueueSaverTest` (3), `PlayerQueueSyncTest` (4), `PlayerControllerTest` (22), `NavidromeScrobblerTest` (7); all pass.
- Documents updated: `docs/plans/redesign.md` (sections 9 and 11), `docs/ACTIVE_WORK.md` section 2k.
- Evidence boundary: D4 is static reading and the recorded fixture. D5 is unit-tested only; no live Navidrome call was made, so the `savePlayQueue` request is not yet confirmed against the real server.

## 2026-11-11 — Discair client efficiency proposal

- Added [`docs/plans/client_efficiency.md`](docs/plans/client_efficiency.md), a source-level proposal for macOS and Android CPU, memory and GPU efficiency. It covers the macOS 50 Hz audio ticker and decoded-image cache accounting; Android's per-frame slideshow state updates, Coil hardware-bitmap/cache policy, blur rendering and PDF handling; and ExoPlayer buffer/crossfade measurement.
- GPU guidance: prefer SwiftUI/Core Animation and Compose hardware layers for transforms; consider cached Core Image/Metal or Android RenderEffect only if profiling shows blur is a bottleneck; do not move real-time audio DSP to the GPU without a separate proven design. GPU/texture memory must be counted as part of total memory.
- Baseline source revision: `ce01596fb8f3d6daf615a401e12bf3a5bc38c313`. The four main workflows on that revision passed: Python syntax, container runtime smoke, Docker packaging validation and Docker image validation (publishing paused).
- Evidence boundary: no Instruments, Android Studio Profiler, Perfetto or physical-device/window profiling was run. No application code, settings, artwork behavior or audio buffer values were changed. The proposal is not implementation approval.
- Documentation commits: proposal `950a60089ba8403711f1e102ff71fe20a262ddb2`; status update `6a5d5262735c8a2b6900c5bc03b328629b63a4cd`. Final docs-only closeout and post-push workflow state to be checked on the resulting main head.
- Next: establish repeatable before/after baselines from section 6 of the proposal, then choose one focused optimization slice.

# Project log

## 2026-11-12 — macOS redesign follow-ups F6, F7, F11, F12 (plus F9 and F3 owner decisions)

- F6: Home's Never played tile now opens the Albums tab filtered to never-played albums; tile and list share `HomeDashboard.neverPlayedIndices`. F7: the Services edit sheet's Test asks the service directly with the typed values (`ServiceDraftProbe`, from this Mac); nothing is saved. The server's test routes take no body, so a server-side version was not built. A changed address or username with an empty secret reports that it cannot be tested. F11: `CU.muted/ink/card/fill` aliases removed, backdrop and glass tint are tokens, shell geometry named in `CU.Shell`. F12: `CupertinoTheme.content` is exhaustive over `Screen`.
- Owner decisions built here: F9 (Route and Server contract lines on the Librarian row, from the address and `/api/capabilities` `contract_version` and `generation`) and F3 (work, recording, event and instrument nodes take the sector Crew).
- Tests run (filtered, `swift test --filter`): GraphExplorer, ConnectionsServices, ServicesModel, ServiceDraftProbe, LibrarianStatusLines, HomeDashboard, HomeScreen, CupertinoPages, CupertinoTokens: 142 passed. Not run: full suite, live-data checks, visual comparison against mockups. Route reads "Direct address" for a non-Tailscale address (wording not in the mockup).

## 2026-11-10 — Internet radio playback, slice 5 gap: `in_library` on the Heard list

- PR [#971](https://github.com/abucalip/navi-librarian/pull/971) merged as `5aee5fbd7ded4aa617ab24fdb9697de8abc6ef40`. `GET /api/radio/plays` now adds `in_library` to every play (exact artist and title match through `find_song`), cached per song in `OwnedCache` (found songs kept, misses re-checked after 5 minutes, failed searches not kept, plays without an artist false).
- Tests (focused): two route tests in `tests/test_api_radio_routes.py` plus the existing plays and clear-all tests, passing. Full suite not run by the agent.
- Open: the first Heard list load can run one Navidrome search per distinct song; not seen on a device or against a live library. Not published or deployed.

## 2026-11-10 — Internet radio playback, stage 1 slice 6 (Android reconnect, sleep timer, settings)

- PR [#970](https://github.com/abucalip/navi-librarian/pull/970) merged as `99e33671aa0067ee2f19905dde521e91c25f36cb`. Stage 1 is complete; the deployment gate is next.
- Built: reconnect policy in `RadioPlayback` (drop or 20 s stall, retries after 2, 5, 10, 20, 30 s, then "Station unreachable" with Retry; none in the background or after a pause; relay/station error statuses count as a drop); new generic `SleepTimer` (no timer existed) on the radio Now Playing sheet; Radio settings (scrobbling switch, per-station logo Change/Reset up to 2 MB, app address read only).
- Tests (focused, JDK 17): `RadioPlaybackTest`, `SleepTimerTest`, `RadioTest`, `PlayerControllerTest`, `RadioScreenTest`, all passing. Full suite not run by the agent.
- Open: not seen on a device; a pause during buffering is invisible to the stall watcher and may retry after 20 s; the Heard list lacked `in_library` from the server (fixed in PR #971); `/mobile-design` pass in `android/DESIGN.md` pending.
- Next: record the deployment gate items (image tag, new `radio.sqlite3` tables, logo cache folder, rollback reference) and wait for the owner's authorization.

## 2026-11-10 — Internet radio playback, stage 1 slice 5 (Android playback, live Now Playing, Download and Heard states)

- PR [#969](https://github.com/abucalip/navi-librarian/pull/969) merged as `71ee8602b59005a534be39ee6a9bd77fa319d17d`. Owner merged it; docs closeout follows on `main`.
- Built: a station plays through the existing Media3 service as a live item (`QueueItem.liveUrl`, not saved with the queue; no seek, Navidrome scrobble or duration); `RadioPlayback` asks `/now` every 5 s only while sounding or buffering and updates the title and picture in place (also in the notification and lock screen); Download states (Download, Downloading, Downloaded, Owned, Try again) follow the contract rule, one request per song; new Heard screen; radio Now Playing built like the song sheet (neutral layout for every theme); station tap opens it.
- Tests (focused, JDK 17): `RadioTest` (11), `RadioPlaybackTest` (8, new), `PlayerControllerTest` (22), `QueueCodecTest` (6), `RadioScreenTest` (3). Full suite not run by the agent.
- Open: not seen on a device; in-place notification update relies on Media3 updating the item without a restart; a non-relayed station that redirects may fail (the service client does not follow redirects); `GET /api/radio/plays` does not send `in_library`, so Owned does not show in the Heard list; the `/mobile-design` pass in `android/DESIGN.md` is pending.
- Next: slice 6 (reconnect, sleep timer, settings).

## 2026-11-10 — Internet radio playback, stage 1 slice 4 (Android decoders, Radio page, logos, favourites)

- PR [#968](https://github.com/abucalip/navi-librarian/pull/968) merged as `65ed988b1397002477f38c259eb779ced871b8e0`. Owner merged it; docs closeout follows on `main`.
- Built: `model/Radio.kt` decoders (stations, `/now`, `/api/radio/now`, favourite) read against the shared contract fixtures; repository calls; `ui/radio/RadioScreen.kt` (server logos, favourites first in the server's order, live title strip refreshed every 15 s only while visible, favourite toggle with rollback and message); a Radio row on Home opens it. An unknown `/now` state reads as unreachable.
- Tests (focused, JDK 17): `RadioTest` (8), `RadioScreenTest` (3), `TapeDeckTest`; build passed. Full suite not run by the agent.
- Open: not seen on a device or any theme; the `/mobile-design` pass in `android/DESIGN.md` is pending; not run against the real server. Tapping a station does nothing until slice 5.
- Next: slice 5 (playback service, live Now Playing, Download and Heard states).

## 2026-11-10 — Internet radio playback, stage 1 slice 3 (scrobble on threshold, love)

- PR [#967](https://github.com/abucalip/navi-librarian/pull/967) merged as `ae69fcf0` (head `9f5c9ba3`). Owner merged it; docs closeout follows on `main`.
- Built: `integrations/radio/scrobble.py` sends Last.fm `track.scrobble` and `track.love` directly, signed with `LASTFM_SHARED_SECRET` and `LASTFM_SESSION_KEY`. Scrobbling is off by default (`GET`/`PUT /api/radio/scrobbling`) and cannot be switched on without both keys. `POST /api/radio/plays/{id}/love` works whether or not scrobbling is on. The `ListenTracker` reports each logged play through `on_logged`; the relay hands it to a background thread.
- Once per play: the `scrobbled` flag is claimed before the request, and a failed request is not retried. `radio_plays` gains `scrobbled` and `loved`, added to existing databases with `ALTER TABLE`.
- Deviation: the repository had no Last.fm write code, so the slice added it rather than reusing existing code. Recorded in the contract, section 3.7.
- Tests (focused, run on the branch): `tests/test_radio_scrobble.py` 15 passed; `tests/test_radio_*.py` and `tests/test_api_radio_routes.py` 128 passed in total. Full suite not run by the agent; CI on the PR head.
- Open: `LASTFM_SESSION_KEY` is not in the owner's `config.env`, so scrobble and love cannot run until it is added. The double-count check with Navidrome is by design only; a live check is still needed. Last.fm's guideline (half the track or four minutes) is not applied to radio, which has no length; the owner's 30-second rule stands.
- Not checked: live Last.fm, Docker image, browser.

## 2026-11-10 — Internet radio playback, stage 1 slice 2 (live now holder, /now, /api/radio/now)

- PR [#966](https://github.com/abucalip/navi-librarian/pull/966) merged as `f3a5a2d756ad98d67e0b2b27c72b5b9140e4e093` (head `e12258ef`). Owner merged it; docs closeout follows on `main`.
- Built: in-memory "now" holder (`integrations/radio/now.py`) fed by the relay's `ListenTracker`; `GET /api/radio/stations/{id}/now` and `GET /api/radio/now`, states `ok`, `no_metadata`, `unparsed`, `not_proxied`, `unavailable`, `idle`. A song is logged at 30 seconds of listening, so `play_id` exists while it plays; the rest of the listen is added on change or close (`store.add_listened`). `in_library` and `cover_url` from one Navidrome search per song (`integrations/radio/library_match.py`), cached per song; a failed lookup is retried.
- Decisions recorded in the contract (section 3.2 slice 2 note): `idle` and `unavailable` added to `/now`; `cover_url` only for library songs; `/api/radio/now` items carry `id`.
- Fixtures: eight `android/contract-fixtures/librarian/radio_now_*` files, generated from the real router with a temporary store (not captured from a live server); `captured_at` is the generation time.
- Tests run (focused): `test_radio_*.py` (88, OK), `test_api_radio_routes.py` (25, OK), `test_android_contract_fixtures.py` (6, OK, run after the fixture fix). CI on the final head `e12258ef`: Python syntax check, Container runtime smoke test, Validate Docker packaging, Validate Docker image (publishing paused), Publish Docker release (build only, `push: false`) all passed. Earlier head `2bb2a02` failed the acquisition-regression job on the fixture envelope; fixed in `e12258ef`. Full suite not run (owner rule).
- Open from this slice: not run against a live Navidrome or a real station; the first `/now` for each song makes one Navidrome search; a logged song appears in the Heard list once it passes 30 seconds, even while it still plays; a relay that stops sending data stops showing as live after 20 seconds.
- Next: slice 3 (scrobble on threshold, off by default, and love).

## 2026-11-10 — Internet radio playback, stage 1 slice 1 (server stations list, favourites, tags, logos)

- PR [#965](https://github.com/abucalip/navi-librarian/pull/965) merged as `b3eef2a35eedf57c99b762cd85865e2f5f3499ff` (head `d5f652d0`). Owner merged it; docs closeout follows on `main`.
- Built: stations list fields (`logo_url`, `homepage_url`, `favourite`, `tags`, `last_played_at`, `playable_url`) with favourites-first order; `PUT .../favourite`, `PUT .../tags`; logo resolver (`GET/PUT/DELETE .../logo`: owner override, Radio Browser favicon, homepage icon, generated PNG tile) with on-disk cache and 7-day negative cache; `integrations/radio/safe_fetch.py` (public http(s) only, redirects re-checked, image sniffing, size cap). Additive tables `radio_station_prefs` and `radio_logo_state`.
- Fixtures: five `android/contract-fixtures/librarian/radio_*` files, recorded from a fake Navidrome in a sandbox folder. `test_android_contract_fixtures` now allows PUT.
- Tests run (focused, 92, all passing): `tests.test_radio_stations_contract`, `tests.test_android_contract_fixtures`, `tests.test_api_radio_routes`, `tests.test_radio_stations`, `tests.test_radio_logos`, `tests.test_radio_icy`, `tests.test_radio_log`, `tests.test_radio_ui_contract`, `tests.test_discovery_daily_radio_scope`. Full suite not run (owner rule).
- Open from this slice: Radio Browser endpoint paths are unverified against the live API; logos are not resized (no image library, Pillow not approved); the fetch guard has a DNS-rebinding window.
- Next: slice 2 (live "now" holder, `/now`, `/api/radio/now`, `in_library`, `cover_url`).

## 2026-11-10 — Internet radio playback contract (stage 1, slice 0)

- Docs only, committed directly to `main` per the documentation rule. New `docs/contracts/RADIO_PLAYBACK_CONTRACT.md` turns `docs/plans/RADIO_PLAYBACK_PROPOSAL.md` (owner decisions of 2026-11-10) into the server, Android and macOS rules, the slice list and the deployment gate.
- Scope lines lifted to point at the contract: `PRODUCT.md`, `docs/contracts/ANDROID_PLAYER_CONTRACT.md`. `docs/contracts/MACOS_CLIENT_CONTRACT.md` keeps radio out of scope until stage 2 starts.
- No code, no endpoint, no migration. Checks: link targets exist; no personal names in the new text. No tests run (docs only).
- Next: slice 1 (server stations list fields, favourites, tags, logo resolver and cache).

## 2026-11-10 — Artwork Timeline filmstrip and Atlas disc nodes on macOS (slice 6, idea 11)

- Merged as PR [#958](https://github.com/abucalip/navi-librarian/pull/958), squash `ca38227d0a76788b51dde1b201795ff5da171b95`, and PR [#959](https://github.com/abucalip/navi-librarian/pull/959), squash `a4b3217832ec27101da7b9e1f4f9002e1a7246b2`. macOS only; no server change.
- New: Timeline "Pictures" filmstrip on the selected album card (`ArtworkIndex.filmstrip`, `Chrome/TimelineFilmstrip.swift`); a Discs switch (off by default) for the Atlas place inspector and for album nodes on the Connections graph (`AlbumDisc`, `GraphNodeFace.discs`). Only UUID release groups are asked; nothing is drawn for an album without the pictures.
- Tests actually run, filtered: `swift test --filter` on `ArtworkTests`, `AtlasDiscTests`, `AtlasGeometryTests`, `TimelineGroupingTests`, `ScreenshotTests` (35 pass) and `GraphDiscTests`, `GraphExplorerTests`, `ScreenshotTests` (16 pass). Not run: the full suites. CI: #959 `validate-container` failed once on a Docker Hub 502 (not the change) and passed on re-run. Not seen in a window or against the real server.
- Next: ideas 12 and 13 (liner note of the day, edition check in Get).

## 2026-11-10 — Artwork Paths covers and Same Room on Android and macOS (slice 6, idea 10)

- Merged as PR [#957](https://github.com/abucalip/navi-librarian/pull/957), squash `e84d3327a422a5a1bd422c682c62488d683bbc5a`.
- New: path rows cycle through the album's alternate Front covers (never a PDF, at least two): macOS hover (`Chrome/PathArtwork.swift`, `PathRowThumb`; held still under Reduce Motion), Android long press and a TalkBack action (`ui/common/PathArtwork.kt`, `PathRowCover`), on the album and artist Paths sheets. Same Room (`SameRoomPhotos`) shows the start album's and the step's session photos side by side. Rules in `ArtworkIndex.pathCoverFaces` / `roomPhotos` (macOS) and `model/PathArtwork.kt` (Android). The release group comes from the Librarian album page; no server change.
- Tests actually run, filtered: Android `PathArtworkTest` (5 pass, JDK 17); macOS `swift test --filter ArtworkTests` (30 pass, four new). Not run: the full suites. Not checked on a device or in a window.
- Next: Timeline filmstrip and Atlas disc nodes (rest of slice 6).

## 2026-11-10 — Artwork Discover covers peek on Android and macOS (slice 6, idea 9)

- Merged as PR [#956](https://github.com/abucalip/navi-librarian/pull/956), merge commit `b311115d92839ff9f555ffa52181dadb65d1d9d6` (tested head `7c6942e45be9181a3febfe7ca76564c1d2fa2c92`).
- New: rows show up to three covers (Back, first booklet page never a PDF, Medium) at thumb size. Android: `model/DiscoverPeek.kt`, `ui/common/DiscoverPeek.kt`, a "Covers" control in `RankedRow`. macOS: `Chrome/DiscoverPeek.swift` (hover plus a "Covers" button) in the Cupertino and Zine Discover rows, `ArtworkIndex.discoverPeek`, `DashboardPick` release group fields, `DiscoveryModel` hover state. Release group: `release_group_mbid`, or `mbid` on new releases; non-UUID values are ignored.
- Tests actually run, filtered: Android `DiscoverPeekTest` (6 pass, JDK 17); macOS `swift test --filter ArtworkTests` (26 pass, two new peek cases); `swift build` compiled the whole package. Required CI on the tested head passed: compile, container-smoke, test-and-build, validate-container. Not run: the full suites. Not checked on a device or in a window; Home new-release tiles have no peek.
- Next: Paths covers and Same Room, Timeline filmstrip and Atlas disc nodes (rest of slice 6).

## 2026-11-10 — Artwork artist photo strip on Android (slice 6, idea 8)

- Merged as PR [#955](https://github.com/abucalip/navi-librarian/pull/955), squash `74964145d1dbee98076cc76f19bb143ea28ab49e` (Android only, plus `docs/archive/completed/artwork.md`).
- New: `model/ArtistCollage.kt` (`qualifiesForCollage`, `artistCollage`: the macOS picture rules and round-robin, at most 8 owned albums, 3 per album, 12 in all, nothing under 4), `OwnedAlbum.releaseGroupMbid` (`model/Dto.kt`), `ui/artist/ArtistPhotoStrip.kt` (per-album index lookups in parallel, a row under the bio, each picture opens its album), one line in `ui/artist/ArtistScreen.kt`.
- Tests actually run, filtered, Android with JDK 17: `ArtistCollageTest` (8), `DtoFixtureTest` (8), `ArtworkIndexTest` (11), all pass. Required CI on the PR head passed: compile, container-smoke, test-and-build, validate-container. Not run: the full Android suite (owner runs it). Not checked on a device; not deployed.
- Next: Discover peeks, Paths covers and Same Room, Timeline filmstrip and Atlas disc nodes (rest of slice 6).

## 2026-11-10 — Artwork artist collage on macOS (slice 6, first step)

- Merged as PR [#953](https://github.com/abucalip/navi-librarian/pull/953), squash `caccc9746f133c12e1946e8826a4f44ca3c9f481` (server), and PR [#954](https://github.com/abucalip/navi-librarian/pull/954), squash `cfd674c3ac5b9530bbb8103ac1b1385f33c1be2d` (macOS).
- New: `release_group_mbid` on artist-page `owned_albums` items (`discovery/search/query.py`, contract line in `SEARCH_CONTRACT.md`); macOS `ArtistAlbumEntry` reads `id` and `release_group_mbid`, `RelatedModel.ownedGroups`, `ArtworkStore.artistCollage`, `qualifiesForCollage` and `artistCollage` in `DiscairLibrarian/Artwork.swift`, `Chrome/ArtistCollage.swift` (Zine contact sheet, Cupertino banner that rotates and holds still under Reduce Motion).
- Finding: the artist page `albums` section already carries the album id and release group for owned albums, so the Mac does not need the #953 field; it stays for owned albums missing from `albums`.
- Tests actually run, filtered: `tests.test_discovery_search_query`, `tests.test_api_search_routes` (82 pass); macOS `DiscairLibrarianTests` (155 pass, 7 new in `ArtistCollageTests`), `DiscairUITests` (366 pass). Not run: full suites. Not checked in a window; not deployed.
- Next: Android photo strip, Discover peeks, Paths, Timeline and Atlas (rest of slice 6).

## 2026-11-10 — Artwork flip cover and spine strip (slice 3, first step)

- Merged as PR [#949](https://github.com/abucalip/navi-librarian/pull/949), squash `2c29e6986a41cd8ee6b8b34ec0f50612a372fb3e`.
- New: Android `model/CoverFaces.kt` and `ui/album/FlipCover.kt` (swipe or tap, TalkBack action, cross-fade when animations are off); macOS `Chrome/FlipCover.swift` (click, Reduce Motion cross-fade, Cupertino and Zine headers, 12 pt Spine strip), `ArtworkIndex.coverBackFaces`, and `release_group_mbid` read from the album page into `RelatedModel`. No Back image means no flip.
- Tests actually run, filtered: Android `CoverFacesTest`, `ArtworkIndexTest`; macOS `ArtworkTests`, `FlipCoverTests`, `BugBatchTests`. Not run: full suites, lint, release build. Not checked on a device or in a window; the strip has no test.
- Open: the owned release is not passed to the index lookup, so a Back from another edition can win over the owned one.
- Next: booklet and zoom.

## 2026-11-10 — Artwork client decoders and image store (slice 2)

- Merged as PR [#948](https://github.com/abucalip/navi-librarian/pull/948), squash `d1ac2f79a6a4b5dddaa79b333c811dac9ae2be6e`, tested head `a3755269862a3d13492707ffbaf458a1ce79494f`; required CI passed (compile, container-smoke, test-and-build, validate-container). Not published or deployed. Clients only; server untouched; no screen uses the new code yet.
- New: Android `model/Artwork.kt` (`parseArtworkIndex`, `loadArtworkIndex`), `Repository.artworkIndex` and `artworkImageUrl`; macOS `DiscairLibrarian/Artwork.swift` (`ArtworkIndexResult`, `ArtworkPicture`, `LibrarianClient.artworkIndex` and `artworkImage`) and `ArtworkStore` album images. `unavailable` is never read as `empty`; one bad entry never drops the rest; comments stay plain text; `pending` is read as `not_loaded` to stay compatible with [`efficiency.md`](docs/plans/efficiency.md) part E.
- Tests actually run, filtered: Android `app.discair.ArtworkIndexTest` (11 pass), macOS `ArtworkTests` (8 pass). Not run: the full suites (owner rule). Not covered: the macOS image store has no unit test; nothing checked on a device or in a window.
- Environment note: Gradle needs JDK 17 here (the default JDK 27 breaks the Kotlin compiler) and a copied `android/local.properties` in a worktree.
- Open risk: the contract types `image_id` as an integer while the efficiency plan may move to content-addressed storage; recorded as a rule in `docs/archive/completed/artwork.md`.
- Next: slice 3, flip cover, booklet and zoom (ideas 1 and 2).

## 2026-11-10 — Artwork fixtures, contract section and `format` (slice 1, third step)

- Merged as PR [#947](https://github.com/abucalip/navi-librarian/pull/947), squash `2de5b2931ecdff17a89f07f0e0f48382d15b57e4`, tested head `f78284cad98e2769d11c9b24a085a319b97a7f7e`; required CI passed (compile, container-smoke, test-and-build, validate-container). Not published or deployed. Server and docs only; no client uses the routes yet.
- New: `format` (`jpg`, `png`, `gif`, `webp`, `pdf`) on each index entry, read from the CAA image URL (default `jpg`, as the store does); fixtures `android/contract-fixtures/librarian/artwork_index*.json` (`ok`, `empty`, `unavailable`, `not_loaded`, `truncated` as `partial`, `release_cap`, `served_cap`, and a `400`), written by `scripts/write_artwork_fixtures.py` through the real route with canned provider answers; `tests/test_artwork_fixtures.py`, which rebuilds them to catch drift; and the "Album artwork" section of `docs/contracts/SERVER_V2_CONTRACT.md`.
- The fixtures are synthetic: invented ids, dates and comments, no provider traffic and no owner data, so shapes are exact and values are not real. The two cap fixtures use lowered caps (2 releases, 3 images) to stay small. They should be replaced by recorded ones only if the owner approves a live capture.
- Finding: the route rebuilds the index from the per-release cache, where a release the build did not reach counts as failed, so a build that stopped on its time bound is served as `partial`; `time` never reaches clients. Decided with the owner: drop `time` from the docs rather than change the route. The service still sets `time` internally. No `time` fixture.
- Tests actually run, filtered: `tests.test_artwork_fixtures`, `tests.test_android_contract_fixtures`, `tests.test_api_artwork_routes`, `tests.test_intelligence_artwork_index`, `tests.test_intelligence_artwork_cache` (71 pass). Not run locally: the full suite (owner rule; CI ran it).
- Next: slice 2, Android and macOS decoders for the index and the image store, following the album paths decoder pattern (PR #931).

## 2026-11-10 — Artwork cache and endpoints (slice 1, second step)

- Merged as PR [#946](https://github.com/abucalip/navi-librarian/pull/946), squash `f5ea0f6c9ba52c949739cd6dc0c1f50432807cde`, tested head `d1fc1a91963917ae17e9747dd17623abd77fbcee`; required CI passed (compile, container-smoke, test-and-build, validate-container, validate-release-workflow). Not published or deployed. New: `intelligence/artwork/store.py` (SQLite plus `images/` under `DATA_DIR/artwork`), `service.py`, `fetchers.fetch_image`, and `app/api/artwork.py` (`GET /api/artwork/index?rgid=&release=`, `GET /api/artwork/image/{image_id}?size=thumb|display|full`). Session auth comes from the app login middleware (tested: both routes answer 401 without a session). No client uses them yet.
- Index: `not_loaded` (with `retry_after` 5) until a background worker (one at a time, one build per group) has built the group; builds never run in a request. Per-release answers cached with the documented TTLs (30 d images, 7 d empty, 1 d partial, 15 min then 1 h for errors, up to 10% jitter); an errored release or group is stored as `unavailable`, never `empty`. An expired group is served stale and refreshed in the background.
- Images: served from disk; a miss is fetched once (per-image lock, one download at a time), checked by file signature (JPEG, PNG, GIF, WebP, and PDF originals, kept at the owner's request because booklet scans such as Somethin' Else's come as PDFs; a PDF is only stored as `full` and is served with a sandbox CSP; anything else rejected; the upstream Content-Type is not trusted), size-limited per size (2, 4, 100 MB) and stored. Redirects are limited to the CAA and archive.org hosts (existing `_SafeRedirect`). The 1.5 GB budget is shared; eviction drops unprotected full-resolution files first, then least recently used, then protected files last. The best front of a group whose owned release was passed is protected. A file larger than the budget is not stored.
- **Decisions made here, for the owner to confirm:** no image library is in `requirements.txt`, so there is no resizing: `thumb` is the CAA 250 px file and `display` is the CAA 500 px file (not 640); `full` is the original. Adding Pillow would be needed for 640 px. The warm-up is not built (open decision 3 is unanswered). The per-host pacer paces the first host (coverartarchive.org); redirected archive.org hosts are not separately paced. The owned release comes from an optional `release` query parameter; nothing reads the library yet to supply it.
- Tests actually run, filtered: `tests.test_intelligence_artwork_cache`, `tests.test_api_artwork_routes`, `tests.test_intelligence_artwork_index`, `tests.test_intelligence_artwork_fetchers` (56 pass, fake openers, no network). Not run: live CAA image fetch, the full suite (owner rule). Test count after the PDF change: 58. Real byte sizes are still unmeasured.
- PDF booklets: the archive makes thumbnails of PDFs, so `thumb`/`display` are first-page previews and clients need a PDF viewer (PDFKit, `PdfRenderer`) for `full` only; described in `docs/archive/completed/artwork.md` idea 2. Open follow-up: the index entry carries no file `format` yet; add it before client decoders. Thumbnails of a real PDF not yet fetched.
- Next: fixtures (`ok`, `empty`, `unavailable`, `truncated`, plus `not_loaded`) and the contract section.

## 2026-11-10 — Artwork index and merge, and provider fetchers (slice 1, first step, PR #945)

- Merged as `e5131a631eb9f7fb928e18430538264a8c10f526` from tested head `3f2d7477761fb061f57bfdf6360ad26b1839f32c`; required CI passed (compile, container-smoke, test-and-build, validate-container). New package `intelligence/artwork/`; `navidrome_server.py` untouched. Not wired to any endpoint or client; not published or deployed.
- `index.py`: merges the CAA images of every release in a release group (owned release first, then newest; 60-release ceiling, 180 s bound, resume from cached per-release answers), collapses an image shared by several releases, picks the best front (approved, Front type, larger side, earlier date, image id; none when no Front image), per-type slots (owned release preferred, fallback labelled with its edition), the booklet as one ordered set from the release with most pages, 400 stored and 250 served caps, and `truncated` with a reason (`release_cap`, `time`, `partial`, `stored_cap`, `served_cap`). A failed release is `unavailable`, never `empty`.
- `fetchers.py`: one paged MusicBrainz browse per group (`inc=media`), one CAA index per release, per-host 1 request per second pacing, 429/503 back-off (`Retry-After`, else 60 s doubling to 15 minutes), redirects only to coverartarchive.org and archive.org over https, no image bytes.
- Checked live: the release browse rejects `inc=cover-art-archive`, so cover-art counts are unavailable and no release request is skipped.
- Tests actually run, filtered: `tests.test_intelligence_artwork_index` and `tests.test_intelligence_artwork_fetchers` (31 pass, fetchers use a fake opener, no network). Full suite not run (owner rule).
- Limits: CAA indexes carry no width or height, so "larger side" only applies when present; booklet pages per release and image byte sizes are still unmeasured; the time and cache TTL behavior has no persistent per-release cache yet.
- Next: slice 1 cache and endpoints (1.5 GB budget, eviction, byte validation, auth), then fixtures and the contract section.

## 2026-11-10 — Artwork caps, TTLs and rate limits set from the probe (slice 0 closed)

- Documentation only, committed directly to `main`; no code, tests or CI. Set in [`docs/archive/completed/artwork.md`](docs/archive/completed/artwork.md), section "Limits (set from the probe)": 60 releases fetched per group (probe max 59), 400 images stored and 250 served (probe max 341, p90 133) with `truncated_reason`, a 180 s build bound (probe max 120 s), 100 booklet pages shown. TTLs: 30 days with images, 7 days empty, 1 day partial, 15 minutes then 1 hour for errors (never stored as empty). One shared 1 request per second queue per host, foreground before warm-up, warm-up capped at 600 requests per day, 429/503 backoff. Caps limit what is served, not what is fetched.
- Limits: from a 30-group sample. Booklet pages per release, image byte sizes, the 640 px source and whether the MusicBrainz batch lookup exposes cover-art counts (would skip the 21.5% empty releases) were not measured; slice 1 records them. Not published or deployed.
- Next: slice 1 (server index and cache), Opus 5.5.

## 2026-11-10 — Artwork probe (slice 0) merged (PR #944)

- Merged as `42f118f4b084b860af36fcf152adf9f161f9a14e` from tested head `96493c41e95541a3b9b2e579db2e60ea353ac4ea`; required CI passed (compile, container-smoke, test-and-build, validate-container). Adds `scripts/artwork_probe.py` for slice 0 of [`docs/archive/completed/artwork.md`](docs/archive/completed/artwork.md). Not wired into the server or any client; `navidrome_server.py` untouched.
- Live run (30 owned release groups, about 40 minutes, 1 request per second per host, index JSON only): all 30 groups have an image, 21 have a non-Front type; releases per group median 5.5, p90 23, max 59; unique images per group median 7.5, p90 133, max 341; 21.5% of release indexes empty, 0.3% errored. Full numbers in `docs/archive/completed/artwork.md`. The owner approved per-type slots (booklet as a single-release set) on the same day.
- Tests: `py_compile` and a re-run of `summarize()` on the saved results; no unit-test file (live network calls); full suite not run (owner rule). Probe sample is small (30 groups). Not published or deployed.
- Next: set the caps, TTLs and rate limits from the results, then slice 1 (server index and cache).

## 2026-11-10 — Album paths build closed

- All album path kinds are built, wired and shown on both clients (PRs #921 to #937). Docs only in this closeout; no code or tests run.
- Left for the owner after deploy, not queued: screens on a device and in a window; Same Room probe thresholds re-run; Neighbours by Ear wider-sample re-measure.
- Not published or deployed.

## 2026-11-10 — Path row covers merged (PR #937)

- Merged as `68f1a97d10300ba3468f530d177df4092fdd0b2c`. Path rows no longer show placeholders. Android: `ownedAlbumArtwork` (exact title and artist match in the library list, cached) and `PathAlbumCover` put the library's own cover first on the artist and album Paths sheets and panes, then fall back to the `/api/artwork` lookup for albums not owned. macOS: `PathsSheet.item(_:)` borrows the library album's cover id by title and artist, or looks the cover up for albums outside the library. No server or contract change (public responses still carry `mbid` only).
- Tests: Android compile (Homebrew JDK 17) plus `AlbumPathStepsTest`, `AlbumPathsTest`, `PathsTest`, `LibraryViewModelTest`; macOS build plus `PathsModelTests`. No new unit test for `ownedAlbumArtwork`.
- Limits: not checked on a device or in a running window. Not published or deployed.

## 2026-11-10 — Same Room and Gaps client tabs merged (PR #936)

- Merged as `02816e448b6f928102a50814a01d37b49f741eca`. Android and macOS offer Same Room and Listen-through Gaps on the album Paths sheet; decoders read `play` and `history`. Gaps labels only (order is the server's) and says in words when history is thin or unavailable, what was left out, and when every album was already played.
- Tests: filtered only. Android `AlbumPath*` and `PathsTest*` (JDK 17); macOS `AlbumPathsTests` and `PathsModelTests` (24 passed). An old Android test now uses `paths_error_album_unknown_entity` (its 501 fixture was removed in #933).
- Limits: not checked on a device or in a running window; 7 segments in the 820 pt macOS sheet may be tight. Not published or deployed.
- Next: look at the screens; re-run the Same Room probe thresholds; Neighbours by Ear re-measure.

## 2026-11-10 — Same Room album path merged (PR #933)

PR [#933](https://github.com/abucalip/navi-librarian/pull/933), squash `96053809ed55dce79a6c0324dcb3afd44aea7dd5`. `album_room` is built in `intelligence/graph/album_paths.py` and served by `GET /api/knowledge/paths?type=release&kind=album_room` (it no longer answers `501`; `album_gaps` still does). Owned albums with a recording made at a place or event that also holds a recording of the start (`recorded at`, `mixed at`, `engineered at`, credit-grade only, never an area); reason `recorded_at`; hub places keep 50 albums with the rest in `capped[]`; overlap with the artist paths dropped. Fixtures `paths_album_room.json` and `_empty` recorded through the route on a scratch copy of the store; the stale `paths_error_album_room_not_built.json` removed. Contract and proposal updated. Filtered tests only; full suite and required CI ran on the PR. The probe thresholds were not re-run on the built path. Not published or deployed.
## 2026-11-10 — Album and artist Paths screens merged (PR #932)

PR [#932](https://github.com/abucalip/navi-librarian/pull/932), squash `4b69308f1982f0558600d0f193c11e7e541c0411`. Android album Paths button and sheet; macOS Paths sheet for albums and artists with buttons in Cupertino and Zine and a Paths menu; macOS ticker scrolls long lines right to left; only the playing version of a repeated title is marked (macOS song id, Android track and disc); restored queue songs without a cover id show their album's cover. Filtered tests only: Android `AlbumPathStepsTest`, `AlbumPathsTest`, `PathsTest`, `PlayingNowTest`; macOS `PathsModelTests`, `AlbumPathsTests`, `KnowledgeTests`, `QueueItemDecodingTests`, `SameTitleHighlightTests`. Not run on a device or in a window; the artwork fix assumes old saved queue items lacked a cover id. Not published or deployed. Limits: graph rows have no cover art id from the server; an album outside the library has no Paths button.

## 2026-11-09 — Album paths route and fixtures merged (PR #929)

PR [#929](https://github.com/abucalip/navi-librarian/pull/929), squash `cca08807bc93267f784bdffdbafe851c66e905ca`. `GET /api/knowledge/paths` now serves `album_crew`, `album_guests`, `album_works` and `album_moment` for `type=release`; `album_room` and `album_gaps` answer `501`; a kind/type mismatch is `400`; `release_group` is `404` or `400` until a release-group builder exists (the contract said it selects an album start, a gap to settle). Fixtures recorded through the route: `paths_album_*` (`ok` and `_empty` per kind), four `paths_error_*` album cases, and `sonic_album_neighbours*.json` (`ok`, `empty` with a skipped unanalysed seed, `404`) from a copy of the owner's store and the owner's Navidrome (read-only). Contract section updated. Filtered tests only (paths route, album paths, paths, sonic neighbours, sonic routes, Android contract fixtures); full suite and required CI ran on the PR. Not published or deployed. Not done: `album_gaps` and `album_room` route/fixtures, fixture-based server tests, decoders, client screens, the Sonic wider-sample re-measure.

## 2026-11-09 — Listen-through Gaps filter merged (PR #927)

PR #927, squash `b257a07db070e7f1086732015bedc6d90d6723de`. `intelligence/graph/album_gaps.py`: Studio Crew and Guest List stops filtered to fewer than 2 plays, labelled in a `play` field; never adds stops or reorders; thin or unavailable history returns unfiltered stops marked as such. Filtered tests only; not wired to the route, contract or cache; not published or deployed.

## 2026-11-09 — Neighbours by Ear composition merged (PR #926)

- Squash-merged PR [#926](https://github.com/abucalip/navi-librarian/pull/926) to `main` as `934a1c0786f78f4daa2ce257888ee6b189278e3b`. Adds `intelligence/sonic/neighbours.py` (`album_neighbours`) and `GET /api/sonic/album-neighbours`: up to 8 deterministic evenly spaced seeds (first and last included), unanalysed seeds skipped, reported and replaced (max 16 calls), own album dropped, albums ranked by distinct seeds matched then earliest track year then id, `similarity` never read, 5 s bound gives `truncated: "time"` (not cached), one-hour sonic cache.
- Tests: filtered only, `tests/test_sonic_neighbours.py` (9) and `tests/test_api_sonic_routes.py`. Not run against live Navidrome; coverage not re-measured on a wider sample. Not published or deployed. Remaining: route test for the endpoint, wider-sample coverage re-measure (build-time requirement), contract section, Same Room, Listen-through Gaps, fixtures, clients.

## 2026-11-09 — Same Year, Same Scene builder merged (PR #925)

- Squash-merged PR [#925](https://github.com/abucalip/navi-librarian/pull/925) to `main` as `adf7454da321543e78aff8d3526f0987b7e7c497`. Adds `album_moment` to `intelligence/graph/album_paths.py` (2-year window by year, stated label, credited artist or non-country area, overlap with the artist paths dropped, same bounds and cache as the other album kinds).
- Measured read-only on the store copy, 884 owned albums: coverage 58.4% (at least 35%), median stops 3 (at least 3), no `truncated: time` 100% (slowest 1.3 s), label-only share 0% (at most 50%). Label links from a credited start are always dropped because the artist's label path reaches them; the area link requires two different artists, stricter than the probe.
- Tests: filtered only, `tests/test_intelligence_album_paths.py` and `tests/test_intelligence_paths.py` (53 passed). Not published or deployed. Remaining: contract section, route extension, Same Room, Neighbours by Ear, Listen-through Gaps, fixtures, clients.

## 2026-11-09 — Album path builders merged (PR #924)

- Squash-merged PR [#924](https://github.com/abucalip/navi-librarian/pull/924) to `main` as `3901673d599079e80cfa41319d4e6d2fe55751fe`. Adds `intelligence/graph/album_paths.py` (`album_crew`, `album_guests`, `album_works`: credit-grade evidence, per-person and per-work caps, overlap dropped against the artist paths, bounds, cache) and `kind_rows()` in `paths.py` (behaviour unchanged).
- Tests run (filtered): `tests/test_intelligence_album_paths.py` (18) plus `test_intelligence_paths.py`, `test_intelligence_paths_warm.py`, `test_api_knowledge_paths_route.py` (51 passed in total). Full suite not run locally (owner rule); CI status as reported at merge.
- Read-only run on a copy of the owner's store (884 owned albums), after overlap dropping: Studio Crew 54.5% coverage, median 7; Guest List 48.8%, median 11; Covers and Sources 36.7%, median 3; builds within the 2 s bound 100%, 99.8%, 100%. All pass the Balanced thresholds; Covers and Sources is thin.
- Not done: contract section, route extension, fixtures, Android and macOS clients. Not published or deployed. Updated `docs/archive/completed/ALBUM_PATHS_PROPOSAL.md`, `docs/PROJECT_STATUS.md`.

## 2026-11-09 — macOS bug batch 3 and release types on the timeline

- Branch `macos/bug-batch-3`. macOS: gapless/tail segment fix (the display no longer advances mid-song and the next song plays to its own length), quality badge, artwork aligned with the sidebar, space bar, instrumental lyrics, grouped ⌘K palette, whole-library search with punctuation ignored (Somethin' Else), artist search on Connections and Timeline, album cover fallback in Now Playing, Insights layout/font/auto-refresh, Up Next double-click.
- Server: migration 5 adds `release_group_facts` (MusicBrainz primary and secondary type), filled from the dump (`release_group.type` plus the secondary-type join) and from a live release lookup; the timeline page returns `release_type` per album. The macOS Timeline keeps albums typed "Album" with no secondary type, and falls back to title wording only where no type is stored. Existing stores need a dump re-import (or release-group sweep) before types appear.
- Tests run: `python3 -m unittest` for the timeline, release-group, loader, store, migration and API modules; `swift test --filter` for DiscairAudioTests, DiscairNavidromeTests, DiscairLibrarianTests and DiscairUITests. Full suite not run (owner rule). No visual, audio or live-server check was performed. Not published or deployed.

## 2026-11-09 — Server V2 Phase 6 taste presentation closed (slice 9)

- Re-ran the `check_no_weight_effect` guard (`scripts/server_v2_phase6_exit.py`) on `main` at `2fec5809`: it passed, so no module outside the taste, API, store, scripts and tests packages imports `intelligence.taste` and profiles cannot change ranking.
- The owner waived the remaining macOS Cupertino/Zine visual checks, Android device/emulator and accessibility checks, and the live-server refresh (including the Android 30-second timeout concern); none was performed.
- Updated `docs/plans/ServerV2.md` and `docs/PROJECT_STATUS.md`. Not published, deployed or runtime-verified.

## 2026-11-09 — Server V2 Phase 6 macOS Zine taste cards merged (PR #910)

- Squash-merged PR [#910](https://github.com/abucalip/navi-librarian/pull/910) to `main` as `4052f96533bc427e82b6e5dfa5a0159f0ba29142`, from exact PR head `e36bf7d03e226edb33688bb85ac9de7e106071cd`.
- Adds the Zine Insights taste presentation (`ZineTaste`): server-authored headline and shifts, selectable time windows and dimensions, decade comparison, playlist/Library actions for supported genre and decade values, and honest low-sample/empty states. Reuses the shared `TasteModel` and action behavior; no server or recommendation-ranking changes.
- All four required GitHub workflows passed on the exact PR head. No separate focused-test count was recorded in the PR review evidence; full suite not run locally under the owner's rule.
- The owner explicitly waived manual macOS visual verification; it was not performed. No live-server check. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/plans/ServerV2.md`; Phase 6 slice 6 is complete and remaining slice 9 retains its number.

## 2026-11-09 — Server V2 Phase 6 macOS taste card actions merged (PR #909)

- Squash-merged PR [#909](https://github.com/abucalip/navi-librarian/pull/909) to `main` as `872ad8c8ae9a1c5412f92c54484eba5efa3be874`, from exact PR head `e0ae1c3d6b8bd1519e11900b6e336d314032f0af`.
- Adds genre/decade actions to Cupertino taste shift and window cards: create and open a prefilled smart playlist for editing, or open the Library Songs tab with a clearable taste filter. Area, label and collaborator are unsupported because they do not map to a Library song field. The playlist is not saved to Navidrome until the owner saves it; recommendation ranking is unchanged.
- PR-reported focused Swift tests: 7 passed (`TasteActionTests`, `TasteModelTests`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging, and non-publishing image validation.
- No manual visual Mac or live-server verification; no macOS CI exists by owner decision. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/plans/ServerV2.md`; Phase 6 slice 7 is complete and remaining slices 6 and 9 retain their numbers.

## 2026-11-09 — Server V2 work queue condensed

- Rewrote `docs/plans/ServerV2.md` as a concise active tracker containing only remaining Phase 6 client slices and Phase 7 verification.
- Preserved taste presentation slice numbers and names (5–9), including the existing execution order.
- Moved the complete previous Server V2 plan to `docs/archive/ServerV2_HISTORY_2026-11-09.md`.
- Preserved the complete pre-existing project log as `docs/archive/PROJECT_LOG_HISTORY.md`; this root file is now a short current index so the historical log remains intact without keeping a very large active file.
- Updated `docs/PROJECT_STATUS.md` with the active/archive pointers.
- Documentation-only change. No application code or tests changed. No publication or deployment.

## 2026-11-09 — Server V2 Phase 6 macOS taste cards merged (PR #907)

- Squash-merged PR [#907](https://github.com/abucalip/navi-librarian/pull/907) to `main` as `95af941e6b293e010da93926df89760404800f17`, from exact PR head `a41bdce98a19e2660fb0a3ea7167ae00b5230885`.
- Adds the macOS taste response models/client, once-per-launch background refresh, and Cupertino Insights cards for headline/shifts, time windows, dimensions, decades, low-sample and empty states.
- PR-reported focused Swift tests: 16 passed; full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head (Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation). No macOS CI exists by owner decision.
- No live-server or manual visual verification on the Mac. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/plans/ServerV2.md`; slice 5 is complete and remaining slice numbers 6–9 are unchanged.

## 2026-11-09 — Server V2 Phase 6 Android taste cards merged (PR #908)

- Squash-merged PR [#908](https://github.com/abucalip/navi-librarian/pull/908) to `main` as `2e220280ea45d729b9b37afc441673b8ddd752bb`, from exact PR head `598ac7c2f8e73b14ad63f4645e568b621b5c0927`.
- Adds the Android taste response decoder and repository calls, one background refresh per app launch, the compact Insights card, and a bottom sheet with recent, past-year (`mid`) and all-time windows, dimension selection, listed movers, and low-sample/empty states. Server-authored prose is displayed as supplied; no recommendation-ranking behavior changes.
- PR-reported focused Android tests: 17 passed (`TasteTest`, `InsightsTest`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation.
- No device/emulator, accessibility or live-server verification. The shared HTTP client's 30-second read timeout may expire before a long refresh completes; saved profiles remain available. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/plans/ServerV2.md`; slice 8 is complete and remaining slice numbers 6, 7 and 9 are unchanged.

## Historical entries

Earlier project log entries are preserved verbatim in [PROJECT_LOG_HISTORY.md](docs/archive/PROJECT_LOG_HISTORY.md).

## 2026-11-10 — Artwork booklet and zoom (slice 3, second step)

- Merged as PR [#950](https://github.com/abucalip/navi-librarian/pull/950), squash `d76ce6ea1dc29a8ad6922aece19390fc5cfd957b`.
- New: Android `model/Booklet.kt`, `ui/album/Booklet.kt` (Booklet tab, pager, pinch and double-tap zoom with the full file asked for after the first zoom, TalkBack zoom actions, `PdfRenderer` viewer), `LibrarianClient.download`, `artworkDownload`; macOS `Chrome/BookletSheet.swift` (two-page spread, arrow keys, hover zoom lens, PDFKit for PDF booklets, links never opened), `BookletView`, `ArtworkStore.albumPDF`, Booklet button on the Cupertino and Zine headers. Sticker, Obi and Poster follow the pages.
- Tests actually run, filtered: Android `BookletTest`, `CoverFacesTest`; macOS `BookletTests`, `ArtworkTests`, `FlipCoverTests` (21 pass). Not run: full suites, lint, release build. Not checked on a device or in a window; the PDF paths and the lens have no test beyond the pure helpers.
- Open: Android Brut themes share one Booklet tab; macOS has only Cupertino and Zine.
- Next: slice 4, edition picker and grid fallback.

## 2026-11-10 — Artwork edition picker and grid fallback (slice 4)

- Merged as PR [#951](https://github.com/abucalip/navi-librarian/pull/951), squash `641888e64c1f091912597aa611ea52a4391363a9`. The first CI run failed (Python syntax and Docker packaging, two `test_api_search_routes` album tests: a fake librarian without `DATA_DIR`); the album page now treats an unreadable pick as no pick, and all required workflows then passed.
- New: server `album_choice` table (`intelligence/artwork/store.py`), `intelligence/artwork/cover.py` (JPEG/PNG size from the header, Front-only pick rule, best-front fallback), routes in `app/api/artwork.py`, pick and fallback in `app/api/owned_artwork.py`, `artwork_choice` on the album page; contract section in `SERVER_V2_CONTRACT.md`. Android `model/EditionPicker.kt`, `ui/album/EditionPicker.kt`, `LibrarianClient.delete`, `setArtworkChoice`/`clearArtworkChoice`. macOS `Chrome/EditionPicker.swift`, `ArtworkStore` choices, `ownedCover` and the grid fallback in `ArtworkImage`, client calls in `Artwork.swift`.
- Tests actually run, filtered: pytest `test_artwork_choice`, `test_api_owned_artwork`, `test_api_artwork_routes`, `test_artwork_fixtures`, `test_discovery_search_album_page`, `test_discovery_search_query`, `test_api_search_routes`; Android `EditionPickerTest`, `CoverFacesTest`; macOS `EditionPickerTests`, `ArtworkTests`, `FlipCoverTests`. Not run: full suites, lint, release build. Not checked on a device or in a window.
- Open: the small-cover rule assumes Navidrome does not upscale; other lists can show the old cover for up to 5 minutes after a pick; the owned release is still not passed to the index lookup; macOS reads picks from `/choices`, not the album page.
- Next: slice 5 (Now Playing: disc, slideshow, system artwork). Done below.

## 2026-11-10 — Artwork Now Playing (slice 5)

- Merged as PR [#952](https://github.com/abucalip/navi-librarian/pull/952), squash `47acca05d41a56d4437b7f77aa1d5bb1be071362`; required CI passed on the PR head (compile, container-smoke, test-and-build, validate-container).
- New: macOS `Chrome/NowPlayingArtwork.swift` (`DiscView`, `DiscSleeve`, `SlideshowBackdrop`), pure rules in `DiscairLibrarian/Artwork.swift` (`discImage(disc:)`, `slideshowImages`, `slideshowFrame`, `discAngle`), `ArtworkStore.nowPlayingIndex` and `libraryCover` (also used by `ArtworkImage` and `SystemMedia`), `PlayerBarOptions.showSlideshow`; Cupertino chip and Zine disc. Android `model/NowPlayingArtwork.kt`, `ui/player/NowPlayingArtwork.kt` (`rememberAlbumArtIndex`, `DiscImage`, `DiscSleeve`, `SlideshowBackdrop`), Photos button in the sheet header, `PlayerSettings.showSlideshow`, disc on the Standard and Cassette Deck players.
- Tests actually run, filtered: macOS `NowPlayingArtworkTests` (12), `NowPlayingArtworkUITests` (4), `SystemMediaTests`, `ArtworkBackdropTests`, `FlipCoverTests`, `EditionPickerTests`, `PlayerBarRefinementTests`; Android `NowPlayingArtworkTest` (10), `CoverFacesTest`, `PlayerSettingsTest`, `PlayerLineTest`. Not run: full suites, lint, release build. Not checked on a device or in a window.
- Open: disc motion, the blurred drift, the button placement and TalkBack wording are owner checks; the Mac's system tile picks up a new cover pick at the next Now Playing update; no disc on Android Sheet Stack or Sticker Wall; alternate sleeves per play not built (open decision 2).
- Next: slice 6 (artist collage, Discover peeks, Paths, Timeline).

## 2026-11-10 — Artwork liner note of the day and edition covers (slice 7); artwork plan closed

- Merged as PR [#962](https://github.com/abucalip/navi-librarian/pull/962) (idea 12), squash `0b80701f55d60ffcf515bdd1abd0a2090ab4686c`, and PR [#961](https://github.com/abucalip/navi-librarian/pull/961) (idea 13), squash `7eba84257a07a66a2b8ab24150617982ab627d2d`; required CI passed on both heads.
- Review before merge: both diffs read in full; both PRs mergeable with no conflicts (they make the same one-line `MBID` visibility change); Android Get already sends the release group through `pageMetadata`. No defects found.
- Tests actually run, filtered: macOS `swift test --filter LinerNote` (5 pass) and `--filter EditionCover` (6 pass), re-run during review; the authors report Android `LinerNoteTest`, `EditionCoversTest`, `PathArtworkTest` passing. Not run: full suites, anything on a device or in a window.
- Open: the Sticker Wall peel-off look for the liner note is not built; the Downloads covers show the album's editions, not the fetched pressing (the server does not record it); open decisions 1 to 4 in `artwork.md` stay with the owner.
- `docs/archive/completed/artwork.md` marked complete: every slice and client idea is merged. Next: the owner's manual checks; no artwork code is left to build.

## 2026-11-11 — Redesign M1: Cupertino tokens (macOS)

- Merged as PR [#975](https://github.com/abucalip/navi-librarian/pull/975), squash `f0aba3d6`, from head `61fda98a`; GitHub confirms the merge. Plan: `docs/plans/redesign.md` section 11, step M1.
- Changed: `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoTheme.swift` (colour roles from section 4.1, `CU.Font` roles from 4.2 with `Text.cuRole`, `CU.Space` 4/8/16/24/32; old names kept as aliases). New `macos/Tests/DiscairUITests/CupertinoTokensTests.swift`.
- Tests actually run, filtered, on a Mac: `swift test --filter CupertinoTokensTests` (6 pass); `swift test --filter "CupertinoRound1Tests|CupertinoTokensTests"` (11 pass in 2 suites). One of the agent's own assertions failed on first run (a line-height rule not in the plan) and was removed before merge.
- Not checked: a screenshot against `components--tokens-and-controls`; CI on the PR head was not recorded in this session.
- Side effect, accepted by the owner: shared Chrome components that read `CU` (for example `OfflineBanner`, `ArtistPageParts`) change colour, including under the Zine theme. Zine's own tokens are untouched.
- Left for later steps: literal colours outside the table (`Color.green`/`Color.orange` status dots, the `#F6F6F8` row shade, taste colours), to M2, M3 and M10.
- Next: M2 (controls), Sonnet, Medium.

## 2026-11-11 — Redesign M2: Cupertino controls (macOS)

- Merged as PR [#976](https://github.com/abucalip/navi-librarian/pull/976), squash `e3e69220`; GitHub confirms the merge. Plan: `docs/plans/redesign.md` section 11, step M2.
- Changed: new `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoKit.swift` (`CapsuleButtonStyle` moved here from `CupertinoHome.swift`, `CUPanel`, `CUSegmented`, `CUStatus`, `CUStatusLabel`, `CUNotice`, `CUField`, `CUSwitchRow`); `CupertinoSettings.swift` (switches, segmented controls, labelled fields, notices); `CupertinoHome.swift` (error notice, neutral tile Get); `CupertinoLibrary.swift` (old `CUSegmented` removed). New `CupertinoControlsTests`.
- Tests actually run, filtered, on a Mac: `swift build`; `swift test --filter "CupertinoControlsTests|CupertinoTokensTests|LibraryHubTests"` (17 tests, 3 suites, pass).
- Not checked: a screenshot against `components--tokens-and-controls`; CI on the PR head was not recorded in this session; full suite not run (owner rule).
- Side effect: the regular button is 32 high (was 36), also where shared Chrome components use `CapsuleButtonStyle` under Zine.
- Left for later steps: pages with several filled primaries per view (Discover, Gap Radar, Artist, Insights tiles) to M8 and M10.
- Next: M3 (shell), Haiku, Medium.

## 2026-11-11 — Redesign M4: Cupertino charts (macOS)

- Merged as PR [#978](https://github.com/abucalip/navi-librarian/pull/978), squash `2480b3a2`, from head `1902590526c68255bc0fb99773004fab5f35b8e9`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/plans/redesign.md` section 11, step M4.
- Changed: new `macos/Sources/DiscairUI/Chrome/CupertinoCharts.swift` (`CUChartMath`, `CUChartPhase`, `CUValueFormat`, `CUChartFrame`, `CUTooltip`, `CULineChart`, `CUColumnChart`, `CUPairedBars`, `CUDumbbell`, `CURankedBars`, `CUHeatmap`, `CUHeatmapKey`, `CUStageTracker`); `CU.trackerTrack` (`#DCDCE2`) added to `CupertinoTheme.swift`. New `CupertinoChartsTests` (29 tests) and `CupertinoChartSpecimenTests` (renders the `charts--specimens` sheet from the real views).
- Tests actually run, filtered, on a Mac: `swift test --filter "CupertinoChartsTests|CupertinoChartSpecimenTests|CupertinoTokensTests|CupertinoControlsTests"` (40 tests, 4 suites, pass). Full suite not run (owner rule).
- Visual: the rendered specimen sheet was compared by eye with `charts--specimens.png`; every type and state is present. Not signed off by the owner. Not checked: VoiceOver reading, keyboard focus ring, draw-in motion.
- Choices: Swift Charts for the line, column and dumbbell charts, plain SwiftUI for paired bars, ranked bars, heatmap and tracker (fixed geometry); value axes have at most 5 ticks including the baseline; paired bars carry the two-series legend of rule 4.4; heatmap dates are written day first.
- Nothing calls the charts yet; no Zine file changed.
- Next: M5 (home data) or M6 (services data), Sonnet; M8 builds Home from M2, M4 and M5.

## 2026-11-11 — Redesign M10a: drawn pages (macOS)

- Merged as PR [#984](https://github.com/abucalip/navi-librarian/pull/984), squash `16cb3d9d`, from head `62eb745b` (the first commit `90e81523` restyled the five pages; `62eb745b` built the deviations). GitHub confirms the merge. Plan: `docs/plans/redesign.md` sections 5.3 and 11, step M10a.
- Changed: `CupertinoInsights.swift` (lens pills, lens cards with neutral actions), `CupertinoTaste.swift` (four panels, time of day and the morning-vs-night contrast read from the server's `context`, four top-value dimensions), `CupertinoHistory.swift` (`CUHeatmap`, day panels), `CupertinoDownloads.swift` (filter, tracker rows, weekly arrival count, Try again as the only primary), `CupertinoGapRadar.swift` (ink completeness bar, one neutral Get per card), `CupertinoSettings.swift` (Playback rows, Clear confirmation), `DiscairLibrarian/Taste.swift` (`TasteContext`, `TasteContrast`), `Model/TasteModel.swift`.
- Server: no change. `intelligence/api/fixture_set.py` gained the `taste_context` and `taste_context_contrast` cases, which the server's own context builder writes; `scripts/write_intelligence_fixtures.py` regenerated them and the existing fixtures are unchanged.
- Tests actually run, filtered, on a Mac: `swift test --filter Cupertino` (45), `TasteContextClientTests` and `TasteClientTests` (11), the Cupertino, TasteModel and HomeDashboard suites (72), `CupertinoPagesRenderTests` (4, PNGs of Insights, History, Downloads and Gap Radar). Python: `tests/test_intelligence_contract_fixtures.py` and `tests/test_intelligence_api_insights.py` (20). Full suite not run (owner rule).
- Visual check: the four rendered pages were read against the mockups by eye; Settings Playback was not rendered (its tab needs a live session). The owner has not approved the look.
- Limits: no live Librarian run; the morning-vs-night and time-of-day numbers come from fixtures; the Top values picker no longer offers Collaborator (mockup's four); the Clear confirmation and the Playback layout are not exercised in a window.
- Next: M10b (token-only pages), Haiku, High.

## 2026-11-11: Redesign S1, listens by day (D2)

- PR #986 merged as squash `41449e29cb6cc8c6842e130264a564aff6c0d445` from head `e7001cf799137df7a875b89dea22c9d74d8a2a8a`. `listens_by_day` on `GET /api/insights/taste`: 84 complete UTC days before the refresh day, oldest first, zero days included; absent until a refresh saves it. Built by `intelligence/taste/listens_by_day.py`, saved by the taste refresh as one `taste_listens_by_day` row (no migration, no new provider call).
- Tests actually run, filtered: listens-by-day, taste refresh, taste persistence and contract-fixture suites (44 pass). Full suite not run (owner rule). Not checked live or against the macOS client.
- Next: S2, Haiku, High.

## 2026-11-11 — Redesign M9: Connections and Services screens (macOS)

- Merged as PR [#983](https://github.com/abucalip/navi-librarian/pull/983), squash `344252e3`, from head `393e7d4f06fa6d8749ebd63bee20a6482042cc86`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/plans/redesign.md` sections 5.2, 6 and 11, step M9.
- Changed: new `Themes/Cupertino/CupertinoConnections.swift` and `CupertinoServices.swift`, new `Model/ServicesController.swift` and `AppState+Services.swift`; `GraphExplorerView.swift` (`GraphStyle.redesigned`), `GraphExplorer.swift` (view mode, start name, load failure and retry, requested and failed update, summary, footer and truncated wording, Also on), `CupertinoSettings.swift` (four tabs), `CupertinoTheme.swift` (status button), `ServicesModel.swift` (name and noun lookups), `AppState.swift` (`services`, `settingsTab`, a services check after connect), `ServiceSettings.swift` (`saveSlskd` folders, optional).
- Tests actually run, filtered, on a Mac: `ConnectionsScreenModelTests`, `ServicesScreenTests`, `ConnectionsServicesRenderTests`, `GraphLayoutTests`, `GraphExplorer`, `ServicesModel`, `ScreenshotTests`, `CupertinoControlsTests`, `CupertinoTokensTests`, `ServiceSettingsClientTests` (123 in the last run). Full suite not run (owner rule).
- Visual check: sample-data renders of connections graph, selected, list, empty, not loaded, truncated and failed, and services healthy, degraded, Librarian unreachable, edit sheet and popover, compared with the mockups by eye; the graph's labels were moved to the outer side of each node after the first render collided. Zine before and after screenshots were not taken (owner waived).
- Limits: no live server or window run, no VoiceOver or keyboard pass, owner has not approved the look. The server sends no connection total, so the footer counts what was read. Disconnect exists for Discogs and ListenBrainz only. The edit sheet's Test tests the saved settings. Status now shows Answer, Since, Last good read and Checked from the Mac's own history; Route and Server contract are not drawn. "Also on, in your library" is derived from the walk's structure (owned albums next to the node), not from a server field.
- Next: M10 (remaining pages, two PRs), Haiku, High.

## 2026-11-11 — Redesign M8: Home screen (macOS)

- Merged as PR [#982](https://github.com/abucalip/navi-librarian/pull/982), squash `f9bccff8`, from head `1abfecbafcb6dadf0f252aa12b87a5117152ee98`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/plans/redesign.md` sections 5.1 and 11, step M8.
- Changed: `CupertinoHome.swift` rewritten, new `CupertinoHomeParts.swift`, new pure `Model/HomeScreen.swift` (state choice and wording); `HomeDashboard` gains radio rows, a listens figure and the handoff notice; `AppState` gains `loadHomeFeeds()`, capabilities, a once-a-day never-played reading, Never played playlist, Play something unplayed, popularity fill and Continue on this Mac; new `DiscairLibrarian/HomeFeeds.swift` and `DiscairNavidrome/PlayQueue.swift`; `listens_by_day` on the taste body; D2 and D3 contract proposals in `docs/contracts/SERVER_V2_CONTRACT.md`.
- Tests actually run, filtered, on a Mac: `HomeScreenTests`, `HomeDashboardTests`, `HomeRenderTests`, `HomeFeedsClientTests`, `PlayQueueTests`, `TasteClientTests`, `TasteModelTests`, `InsightsModelTests`, `CupertinoControlsTests`, `CupertinoTokensTests`, `ScreenshotTests` (110 in the last run). Full suite not run (owner rule).
- Visual check: five sample-data renders (default, first run, Librarian unreachable, loading, stacked) compared with the `home--*` mockups by eye; the degraded mockup is the M9 popover.
- Limits: D2 and D3 are tested from the proposed contract only, the server does not serve them; the handoff needs the Android app to call `savePlayQueue` (D5); no live-data run, no VoiceOver pass, owner has not approved the look; Space plays only an owned album; the collection chart stays when Librarian is down (the mockup omits it).
- Next: M9 (Connections and Services screens), Sonnet, High.

## 2026-11-11 — Redesign M7: Connections model (macOS)

- Merged as PR [#981](https://github.com/abucalip/navi-librarian/pull/981), squash `7e705614`, from head `6d0f06552068f1bd2673401940e862d6537d4c94`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/plans/redesign.md` section 11, step M7.
- Changed: `macos/Sources/DiscairUI/Model/GraphExplorer.swift` (new `GraphSector`, `GraphGroup`, `GraphWording`, `GraphListRow`, `GraphListGroup`; `GraphLayout` gains `Style` with `.classic` (default, the Zine geometry) and `.sectors` (Cupertino: a sector per arc, rings at 188 and 292 pt), `spacing` and `tooManyToDraw` (under 40 pt spacing); `GraphExplorerModel` gains `tooManyToDraw`, `sectorCounts`, `sectorLayout`, `listGroups`); `macos/Tests/DiscairUITests/GraphExplorerTests.swift` (new suites).
- Tests actually run, filtered, on a Mac: `swift test --filter Graph` (44 pass, 9 suites). Full suite not run (owner rule). No UI, so no visual check.
- Limits: nothing calls the new pieces yet (M9 wires them). The 40 pt threshold is average spacing per ring; step-2 nodes are placed by fan, so their real spacing can differ. The relation and match words come from the server's vocabulary in code and fixtures, not live captures. Types the mockup does not draw (work, recording, event, instrument) fall into an "Other" sector. "member_of" reads "Member of", not the mockup's "member of Talk Talk". Zine's explorer keeps the classic geometry, so its look is unchanged.
- Next: M8 (Home screen), Sonnet, High. M9 (Connections and Services screens) is also unblocked, Sonnet, High.

## 2026-11-11 — Redesign M6: Services data (macOS)

- Merged as PR [#980](https://github.com/abucalip/navi-librarian/pull/980), squash `cf175239`, from head `843ebc1cb903d3aab39a8275398906af69872c20`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/plans/redesign.md` sections 6 and 11, step M6.
- Changed: new `macos/Sources/DiscairLibrarian/ServiceSettings.swift` (settings, test, health and capabilities calls; the Discogs test body's `error` is folded into `status` and `message`; saves for Navidrome, Last.fm, slskd and Discogs) and `macos/Sources/DiscairUI/Model/ServicesModel.swift` (pure; state per service, summary, toolbar label, diagram edges, powers, setup fields, local history).
- Tests actually run, filtered, on a Mac: `swift test --filter 'DiscairLibrarianTests.ServiceSettingsClientTests|DiscairUITests.ServicesModelTests'` (36 pass). Full suite not run (owner rule). No UI, so no visual check.
- Limits: bodies in the tests come from the server's serializers, not live captures (only `health` is a recorded fixture); nothing is wired into `AppState` or a view; no client method reads Navidrome's plugin list, so Sonic analysis with the Librarian down needs the caller to supply it; the app must run the tests and Navidrome and SMB checks itself (M9).
- Next: M7 (connections model), Sonnet; M9 builds the Services screens from M6.

## 2026-11-11 — Redesign M5: Home data (macOS)

- Merged as PR [#979](https://github.com/abucalip/navi-librarian/pull/979), squash `3bf66cb2`, from head `c1a530dd161c05340c3a2a06a4c8830e52dd7d32`; GitHub confirms the merge and compile, container-smoke, test-and-build and validate-container passed on that head. Plan: `docs/plans/redesign.md` section 11, step M5.
- Changed: new `macos/Sources/DiscairUI/Model/HomeDashboard.swift` (pure; albums owned and added against the 30 days before, never played with change against a saved baseline, six shelf-life bins plus the four longest-unplayed albums, growth series by range, decade shares with recent listen shares only from a sound taste window, arrivals rows capped at four, notice). `AppState` gains `homeDashboard` and `refreshHomeDashboard()` (no request; builds off the main thread from the shared album list). `LibraryModel.allNavidromeAlbums` keeps the raw list; `NavidromeAlbum` gains optional `playCount` and `played`; `AcquisitionModel.statusText` is `nonisolated`.
- Tests actually run, filtered, on a Mac: `swift test --filter HomeDashboardTests` (18 pass) and `--filter "DiscairNavidromeTests|LibraryModelTests|AcquisitionModelTests|OfflineTests|LibraryHubTests|BulkSongLoadTests"` (112 pass). Full suite not run (owner rule). No UI, so no visual check.
- Limits: radio plays in Arrivals not included (no client route); phone handoff (D5) and Listens last 7 days (D2) not produced; absent `playCount` is read as no plays (Navidrome omits it); Librarian reachability is inferred from the picks read until M6.
- Next: M6 (services data) or M7 (connections model), Sonnet; M8 builds Home from M2, M4 and M5.

## 2026-11-12 — A9 merged (PR #1003, squash e4f4ba1b)

- Built: cover to Album shared element (wired on Recently added, Library grid, Artist albums, Album header; off when motion is reduced; Tape 60% linear); `Palette.accentText` / `Ink.AccentText` (accent as text only at 4.5:1 on page and card, else ink text) applied to Album, Radio, the four players, Queue and Equalizer; Equalizer reset on the A5 confirmation sheet; eyebrow tracking +0.08em; `animateItem` on Radio stations.
- Tests run locally (JDK 17, filtered): `MotionTest`, `PaletteTest`, `ConfirmSheetTest`, `RadioPlaybackTest`; all pass. Full suite not run (owner rule).
- Not checked: no emulator or device, so the transition, Night, Tape and Sheet identity and 200% font scale are unseen.
- Next action: the owner reviews Night, Tape and Sheet on a device (A9 acceptance and A8b item 7); the Android track is otherwise built.

## 2026-11-12 — A8b merged (PR #1001, squash d020f7b2)

- Built: Settings rows with icon, state line and chevron; Library search field removed; Downloads tracker, state in words, one action row, Play on an arrived album (owned album id looked up by artist and album); `animateItem` on the Library grid; Taste sheet "Make a X playlist" button drawn but disabled.
- Tests run locally: `DownloadsRulesTest`, `TasteTest`, `LibraryViewModelTest`. Full suite not run (owner rule).
- Not done: item 1 needs a server route that creates a Navidrome playlist (new module), then `TasteCard.PlaylistRouteAvailable` on; item 7 device check of the three mockups and Night, Tape, Sheet (no emulator available). Nothing compared on screen.
- Next action: A9.

## 2026-11-15 — Flow Discover D1: switch row and list sheet (PR #1103, squash `8c0a97264178dd78a914048c1b5a87eadf5a5a86`, merged)

- Built: `FlowDiscoverSwitch`, `FlowListSheet` and `FlowDiscoverRules` in `ui/discover/FlowDiscover.kt`; the Flow branch of `DiscoverScreen` draws the switch instead of `FlowDiscoverHeader`. Lens/genre tabs, one-column cards and Insights lens headings are unchanged until D2 and D3.
- Tests run locally (JDK 17, filtered): `FlowDiscoverRulesTest` (new, 5), `FlowTest`, `ExistingLayoutsTest`, `DiscoveryTest`, `InsightsTest`, `FlowPagesRulesTest`, `SoftBrutTest`, `NavRulesTest`. Full suite not run (owner rule).
- Not done: no device or emulator check, no comparison with frames B1 and B2.
- Next action: D2 after the owner merges D1.

## 2026-11-15 — Flow Discover D2: sections and grid card

- Built: on Flow, `ListBody` draws `FlowDiscoverGrid` (one two-column `LazyVerticalGrid`, full-span `FlowLensHeading` and `FlowSectionNote` items) instead of `EditorTabs` and `HorizontalPager`; new `FlowDiscoverGridCard` (cover with Get on it, title, artist and year, third line, Save and the three-dot menu); section building, grid keys and the third-line rule are pure functions in `FlowDiscoverRules`. Sideways swipes already went to `switchBy`, and Flow has no pager now. `FlowSmallButton` draws an icon-only primary button's glyph in `onAccent` (it was `text`, dark on the accent). `FlowDiscoverCard` and `pagesFor` stay for D4 and the other themes. Daily picks turned off draws the whole-list note once, not once per lens.
- Open point O1 default used (36 wide, 48 tall Save and menu boxes). The third line sits under the 48 dp row, a few dp lower than the mockup.
- Tests run locally (JDK 17, filtered): `FlowDiscoverRulesTest` (13), `FlowTest`, `ExistingLayoutsTest`, `DiscoveryTest`, `InsightsTest`, `FlowPagesRulesTest`, `SoftBrutTest`, `NavRulesTest`. Full suite not run (owner rule).
- Not done: no device or emulator check, no comparison with frames B1 and B3.
- Next action: D3 after the owner merges D2.

## 2026-11-15 — Flow Discover D4: cleanup and closeout

- Built: deleted the Flow code nothing calls after D1 to D3: `FlowDiscoverHeader` (Lists | Insights and the chips), the one-column `FlowDiscoverCard`, `FlowPagesRules.DISCOVER_COVER` and `DISCOVER_GAP` (and their assertions in `FlowPagesRulesTest`), the unused imports in `FlowDiscover.kt`, and two Flow branches in the classic Insights loop of `InsightsPage` that the Flow early return made unreachable. No file was added, so `ARCHITECTURE.md` is unchanged. Other themes are untouched.
- Tests run locally (JDK 17, filtered): `FlowTest`, `ExistingLayoutsTest`, `DiscoveryTest`, `InsightsTest`, `FlowPagesRulesTest`, `SoftBrutTest`, `NavRulesTest`, `FlowDiscoverRulesTest`; all pass. Full suite not run (owner rule).
- Not done: no device check. The owner's phone check is still open: each of the seven lists, the sheet, swipes across all seven, a night palette. Open point O1 (Save and ⋯ touch size) is still the owner's.
- Next action: the owner's phone check after D4 merges.

## 2026-11-16 - Deep Dives bridge into the lens lists

- Owner request: grow each lens list (Current tastes first, and the other three) with Deep Dives albums of the same genres, with no new lookups.
- Built: `discovery/deep_dive_bridge.py` (pure). At read time `lens_service.list_response` passes the served list and the stored `artist_deep_dive` payload to it. The genre families of the list's tags and seed tags pick up to 2 Deep Dives albums per family, 10 in all, those sharing the most tags first. Owned, dismissed and blocked-genre albums are skipped through the lens list's own predicates. Extras follow the requested `count` (ranks continue, `bridged_count` reports them) and carry `source: "deep_dive"`, `lens`, `bridge_label` and `reason` set to "Discover more <artist>".
- Owner choice: the one-album-per-artist cap does not apply to the extras. The Deep Dives build now also stores `extra_items`, the ranked candidates its diversity pass held back (up to 150); Deep Dives itself still shows `items` only. A list stored before this change bridges from `items` alone until the next Deep Dives refresh.
- Clients: the web list rows and cards and the Android Daily rows show the label; Gallery tiles show it as the reason line. No other client change.
- Not changed: stored lens lists, the Today's picks week archive, Deep Dives output. A save or dismissal of an extra counts to its lens in the feedback summary.
- Tests run (filtered): `test_discovery_deep_dive_bridge`, `test_discovery_lens_storage`, `test_discovery_genre_block`, `test_discovery_list_payload`, `test_discovery_lens_lists`, `test_lens_lists_ui_contract`, `test_dashboard_service`. Not run: the full suite, a live server, a browser or phone check, the Android build.
- Next action: owner check on a running server after a Deep Dives refresh.

## 2026-11-16 - Deep Dives bridge into Personal, Classics and New releases

- Owner request: bridge the three other lists as well, after the lens lists (PR #1129, which this branch builds on).
- Built: `build_cached_discovery_list_response(bridge=...)` calls `navidrome_server._bridge_deep_dives` for `personal`, `classics` and `new_releases` only. The same caps apply (2 per genre family, 10 in all). The extras skip what the list itself hides (dismissed, saved, imported, owned, blocked genre) through one shared `hidden` check, which also covers owned albums on Personal. They follow the requested count, carry `source: "deep_dive"`, `bridge_label` and `reason` "Discover more <artist>", and no `lens`. The response gains `bridged_count`; Personal's `recommendations` includes them.
- Known mismatch: New releases extras are not new releases and carry no release date, and Classics extras keep the Deep Dives "Similar to" anchor line. Tuning these is the owner's call after a look.
- Web: `reasonLine` and the New releases card show the label; Android: the default row model shows it. Tests run (filtered): the bridge, list payload, lens storage, genre block, lens lists, dashboard service and UI-contract suites; Android `DiscoveryTest` to follow in the PR. Not run: the full suite, a live server, browser or phone.

## 2026-11-16 - Today's picks draw from the grown Current tastes list

- Owner report: the Home slideshow on both clients showed the same suggestions for days. Cause: `/api/dashboard-picks` shuffled only the week's stored Current tastes albums (a small pool once owned and dismissed albums are removed), and the Deep Dives bridge only grows the served list at read time, so the picks never saw it.
- Changed: `app/services/lens_week_picks.picks` adds the bridged Deep Dives albums of the same genres to the pool (4 per genre family, 30 in all, wider than a list's 2 and 10 because the pool is reshuffled on every visit; owned and dismissed skipped; a failed bridge leaves the week's albums). A bridged pick keeps its "Discover more <artist>" reason. Clients unchanged: they already ask again on each Home visit.
- Tests run (filtered): `test_lens_week` (new), `test_dashboard_routes`, `test_dashboard_service`, `test_discovery_deep_dive_bridge`, `test_discovery_lens_storage`: 71 passed. Not run: full suite, live server, devices. The caps 4 and 30 are my starting values, for the owner to tune.

## 2026-11-16 - Blocked genres leave Classics and Deep Dives at build time

- Owner request: apply the build-time exclusion of blocked genres to Classics, Deep Dives and New releases (it already covered Personal and the lens lists; all lists were also hidden at read time).
- Built: `genre_block.drop_blocked_items` and `current_blocked_keys` (unreadable feedback blocks nothing). Classics drops blocked-genre items after `enrich_classic_genres`, before re-sorting and diversifying. Deep Dives drops them after genre enrichment, before ranking, so neither the shown `items` nor `extra_items` holds one.
- Not done: New releases. Its candidates come from MusicBrainz release groups with no genre field at build time, so there is nothing to test; it stays hidden by the read-time check only when an item carries genres (none do). Excluding it needs a genre lookup per artist, which is the owner's call.
- Tests run (filtered): `test_discovery_genre_block` (3 new), classics and Deep Dives suites, `test_lens_week`: 58 passed. Not run: full suite, a live build.

## 2026-11-16 - Efficiency M2 warm baseline

- Owner request: run the warm baseline for M2 (`docs/plans/efficiency.md`) now that #1143 and #1144 are on `main`, and record it.
- Ran: restarted the local test instance on port 8090 from `main` at `c606b124`; one warm-up pass (2 runs), then `scripts/efficiency_baseline.py --runs 20`. Output `local-test/baseline-warm-1.json` (outside the repo, no keys in it). Table and findings in `docs/plans/efficiency.md` section 13.
- Result: no ListenBrainz, MusicBrainz or other provider requests during the measured run; album page median 410 ms, p95 1.3 s, all on the Navidrome LAN bucket. Knowledge routes 404 on this instance (no ingested MusicBrainz data), so they are not a real baseline.
- Not done: no code change, no per-route attribution of the 120 LAN requests (the script does not split them by route), no deploy. Limitation: one machine, one library, one album and one artist.
- Tests run: none (docs and a measurement only; the script was not changed).
- Merged: PR #1145, squash `f376e726`, merged 2026-11-16. CI at merge: `container-smoke`, `lint-changed`, `validate-container` passed; `compile` and `test-and-build` still pending at merge, check them. Docs-only follow-up to record the merge went straight to `main`, per CLAUDE.md.
