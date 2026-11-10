# Project log

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

- Merged as PR [#955](https://github.com/abucalip/navi-librarian/pull/955), squash `74964145d1dbee98076cc76f19bb143ea28ab49e` (Android only, plus `docs/artwork.md`).
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
- New: Android `model/Artwork.kt` (`parseArtworkIndex`, `loadArtworkIndex`), `Repository.artworkIndex` and `artworkImageUrl`; macOS `DiscairLibrarian/Artwork.swift` (`ArtworkIndexResult`, `ArtworkPicture`, `LibrarianClient.artworkIndex` and `artworkImage`) and `ArtworkStore` album images. `unavailable` is never read as `empty`; one bad entry never drops the rest; comments stay plain text; `pending` is read as `not_loaded` to stay compatible with [`efficiency.md`](docs/efficiency.md) part E.
- Tests actually run, filtered: Android `app.discair.ArtworkIndexTest` (11 pass), macOS `ArtworkTests` (8 pass). Not run: the full suites (owner rule). Not covered: the macOS image store has no unit test; nothing checked on a device or in a window.
- Environment note: Gradle needs JDK 17 here (the default JDK 27 breaks the Kotlin compiler) and a copied `android/local.properties` in a worktree.
- Open risk: the contract types `image_id` as an integer while the efficiency plan may move to content-addressed storage; recorded as a rule in `docs/artwork.md`.
- Next: slice 3, flip cover, booklet and zoom (ideas 1 and 2).

## 2026-11-10 — Artwork fixtures, contract section and `format` (slice 1, third step)

- Merged as PR [#947](https://github.com/abucalip/navi-librarian/pull/947), squash `2de5b2931ecdff17a89f07f0e0f48382d15b57e4`, tested head `f78284cad98e2769d11c9b24a085a319b97a7f7e`; required CI passed (compile, container-smoke, test-and-build, validate-container). Not published or deployed. Server and docs only; no client uses the routes yet.
- New: `format` (`jpg`, `png`, `gif`, `webp`, `pdf`) on each index entry, read from the CAA image URL (default `jpg`, as the store does); fixtures `android/contract-fixtures/librarian/artwork_index*.json` (`ok`, `empty`, `unavailable`, `not_loaded`, `truncated` as `partial`, `release_cap`, `served_cap`, and a `400`), written by `scripts/write_artwork_fixtures.py` through the real route with canned provider answers; `tests/test_artwork_fixtures.py`, which rebuilds them to catch drift; and the "Album artwork" section of `docs/SERVER_V2_CONTRACT.md`.
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
- PDF booklets: the archive makes thumbnails of PDFs, so `thumb`/`display` are first-page previews and clients need a PDF viewer (PDFKit, `PdfRenderer`) for `full` only; described in `docs/artwork.md` idea 2. Open follow-up: the index entry carries no file `format` yet; add it before client decoders. Thumbnails of a real PDF not yet fetched.
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

- Documentation only, committed directly to `main`; no code, tests or CI. Set in [`docs/artwork.md`](docs/artwork.md), section "Limits (set from the probe)": 60 releases fetched per group (probe max 59), 400 images stored and 250 served (probe max 341, p90 133) with `truncated_reason`, a 180 s build bound (probe max 120 s), 100 booklet pages shown. TTLs: 30 days with images, 7 days empty, 1 day partial, 15 minutes then 1 hour for errors (never stored as empty). One shared 1 request per second queue per host, foreground before warm-up, warm-up capped at 600 requests per day, 429/503 backoff. Caps limit what is served, not what is fetched.
- Limits: from a 30-group sample. Booklet pages per release, image byte sizes, the 640 px source and whether the MusicBrainz batch lookup exposes cover-art counts (would skip the 21.5% empty releases) were not measured; slice 1 records them. Not published or deployed.
- Next: slice 1 (server index and cache), Opus 5.5.

## 2026-11-10 — Artwork probe (slice 0) merged (PR #944)

- Merged as `42f118f4b084b860af36fcf152adf9f161f9a14e` from tested head `96493c41e95541a3b9b2e579db2e60ea353ac4ea`; required CI passed (compile, container-smoke, test-and-build, validate-container). Adds `scripts/artwork_probe.py` for slice 0 of [`docs/artwork.md`](docs/artwork.md). Not wired into the server or any client; `navidrome_server.py` untouched.
- Live run (30 owned release groups, about 40 minutes, 1 request per second per host, index JSON only): all 30 groups have an image, 21 have a non-Front type; releases per group median 5.5, p90 23, max 59; unique images per group median 7.5, p90 133, max 341; 21.5% of release indexes empty, 0.3% errored. Full numbers in `docs/artwork.md`. The owner approved per-type slots (booklet as a single-release set) on the same day.
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
- Not done: contract section, route extension, fixtures, Android and macOS clients. Not published or deployed. Updated `docs/ALBUM_PATHS_PROPOSAL.md`, `docs/PROJECT_STATUS.md`.

## 2026-11-09 — macOS bug batch 3 and release types on the timeline

- Branch `macos/bug-batch-3`. macOS: gapless/tail segment fix (the display no longer advances mid-song and the next song plays to its own length), quality badge, artwork aligned with the sidebar, space bar, instrumental lyrics, grouped ⌘K palette, whole-library search with punctuation ignored (Somethin' Else), artist search on Connections and Timeline, album cover fallback in Now Playing, Insights layout/font/auto-refresh, Up Next double-click.
- Server: migration 5 adds `release_group_facts` (MusicBrainz primary and secondary type), filled from the dump (`release_group.type` plus the secondary-type join) and from a live release lookup; the timeline page returns `release_type` per album. The macOS Timeline keeps albums typed "Album" with no secondary type, and falls back to title wording only where no type is stored. Existing stores need a dump re-import (or release-group sweep) before types appear.
- Tests run: `python3 -m unittest` for the timeline, release-group, loader, store, migration and API modules; `swift test --filter` for DiscairAudioTests, DiscairNavidromeTests, DiscairLibrarianTests and DiscairUITests. Full suite not run (owner rule). No visual, audio or live-server check was performed. Not published or deployed.

## 2026-11-09 — Server V2 Phase 6 taste presentation closed (slice 9)

- Re-ran the `check_no_weight_effect` guard (`scripts/server_v2_phase6_exit.py`) on `main` at `2fec5809`: it passed, so no module outside the taste, API, store, scripts and tests packages imports `intelligence.taste` and profiles cannot change ranking.
- The owner waived the remaining macOS Cupertino/Zine visual checks, Android device/emulator and accessibility checks, and the live-server refresh (including the Android 30-second timeout concern); none was performed.
- Updated `docs/ServerV2.md` and `docs/PROJECT_STATUS.md`. Not published, deployed or runtime-verified.

## 2026-11-09 — Server V2 Phase 6 macOS Zine taste cards merged (PR #910)

- Squash-merged PR [#910](https://github.com/abucalip/navi-librarian/pull/910) to `main` as `4052f96533bc427e82b6e5dfa5a0159f0ba29142`, from exact PR head `e36bf7d03e226edb33688bb85ac9de7e106071cd`.
- Adds the Zine Insights taste presentation (`ZineTaste`): server-authored headline and shifts, selectable time windows and dimensions, decade comparison, playlist/Library actions for supported genre and decade values, and honest low-sample/empty states. Reuses the shared `TasteModel` and action behavior; no server or recommendation-ranking changes.
- All four required GitHub workflows passed on the exact PR head. No separate focused-test count was recorded in the PR review evidence; full suite not run locally under the owner's rule.
- The owner explicitly waived manual macOS visual verification; it was not performed. No live-server check. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; Phase 6 slice 6 is complete and remaining slice 9 retains its number.

## 2026-11-09 — Server V2 Phase 6 macOS taste card actions merged (PR #909)

- Squash-merged PR [#909](https://github.com/abucalip/navi-librarian/pull/909) to `main` as `872ad8c8ae9a1c5412f92c54484eba5efa3be874`, from exact PR head `e0ae1c3d6b8bd1519e11900b6e336d314032f0af`.
- Adds genre/decade actions to Cupertino taste shift and window cards: create and open a prefilled smart playlist for editing, or open the Library Songs tab with a clearable taste filter. Area, label and collaborator are unsupported because they do not map to a Library song field. The playlist is not saved to Navidrome until the owner saves it; recommendation ranking is unchanged.
- PR-reported focused Swift tests: 7 passed (`TasteActionTests`, `TasteModelTests`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging, and non-publishing image validation.
- No manual visual Mac or live-server verification; no macOS CI exists by owner decision. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; Phase 6 slice 7 is complete and remaining slices 6 and 9 retain their numbers.

## 2026-11-09 — Server V2 work queue condensed

- Rewrote `docs/ServerV2.md` as a concise active tracker containing only remaining Phase 6 client slices and Phase 7 verification.
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
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; slice 5 is complete and remaining slice numbers 6–9 are unchanged.

## 2026-11-09 — Server V2 Phase 6 Android taste cards merged (PR #908)

- Squash-merged PR [#908](https://github.com/abucalip/navi-librarian/pull/908) to `main` as `2e220280ea45d729b9b37afc441673b8ddd752bb`, from exact PR head `598ac7c2f8e73b14ad63f4645e568b621b5c0927`.
- Adds the Android taste response decoder and repository calls, one background refresh per app launch, the compact Insights card, and a bottom sheet with recent, past-year (`mid`) and all-time windows, dimension selection, listed movers, and low-sample/empty states. Server-authored prose is displayed as supplied; no recommendation-ranking behavior changes.
- PR-reported focused Android tests: 17 passed (`TasteTest`, `InsightsTest`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation.
- No device/emulator, accessibility or live-server verification. The shared HTTP client's 30-second read timeout may expire before a long refresh completes; saved profiles remain available. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; slice 8 is complete and remaining slice numbers 6, 7 and 9 are unchanged.

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
- `docs/artwork.md` marked complete: every slice and client idea is merged. Next: the owner's manual checks; no artwork code is left to build.
