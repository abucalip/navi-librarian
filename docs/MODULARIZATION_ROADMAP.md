## 2026-10-16 — PR #235 merged: New Releases response projection

- Squash merge commit: `0d77f7d99a89660ea1d9a38635e93343538e93b8`; exact tested PR head: `f3e7ec7c14deac8136b5066011623e00dffca134`.
- Extracted sorting, the 200-item visible cap, the 20-error cap, and response shaping into `discovery_new_releases.build_new_release_response()`. Provider/cache/rate-limit access, date-window policy, candidate selection, and error collection remain in the server adapter.
- Added direct-import tests for newest-first ordering/tie behavior, response metadata, error/item caps, and non-mutation. Docker packaging already included `discovery_new_releases.py`, so no packaging change was needed.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety run `38937239432`; Docker packaging/full unit suite/build run `38937239481`; container runtime smoke run `38937239444`; validation-only multi-architecture image validation run `38937239482` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — New Releases global candidate merge complete (PR #234)

PR #234 merged as `c44ea572354b4714e5e2577f5eb21b091be97cc8` from exact tested head `56bb5b6835d03860124f2dbdff4dbb13a813d5c8`. The pure merge helper deduplicates cross-artist candidate identities, selects the newest release, and preserves existing winners on ties. Direct-import regression tests added. All four required workflows passed on that exact head (syntax 38935716487, Docker/full suite/build 38935717026, runtime smoke 38935716420, validation-only multi-architecture 38935716622). No assistant-side local test run or publication/deployment/runtime verification claimed. Reassess the remaining discovery, slskd, and acquisition boundaries from current main before choosing the next extraction.

## 2026-10-16 — New Releases global candidate merge (PR #234 in progress)

PR #233 completed the pure library qualification boundary and merged at `08e20f502e10f829bf9ae7920106b7e8427668eb` from tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`; all four required workflows passed. The next seam extracts cross-artist identity deduplication/newest-release winner selection into `discovery_new_releases.merge_release_candidates()`. Provider/cache/rate-limit behavior, per-artist eligibility, final sorting, and response assembly stay in the adapter. PR #234 CI pending; no publication/deployment/runtime verification.

## 2026-10-16 — PR #232 merged: classics candidate collection

- Squash merge commit: `451944c9056eeb50ec7d8b1744bbf435d653b70b`. `discovery_classics_candidates.collect_classic_candidates()` owns candidate collection, normalized duplicate resolution, ownership/eligibility filtering, metadata, and fifth-artist pacing; the server retains library/provider access, scoring, enrichment, diversity, and response assembly.
- The latest four workflow runs inspected for the PR reported success (syntax/acquisition safety, Docker packaging/full suite/build, container smoke, and non-publishing multi-architecture validation). The connector evidence did not independently expose each run's head SHA, so this closeout does not label them exact-head verified. Assistant-side local tests were not run. Publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — New Releases library qualification extraction in progress

The next candidate moves normalized ownership identity construction and full-album artist qualification/sorting into `discovery_new_releases.prepare_new_release_library_scope()`. It preserves the six-track threshold, Various Artists exclusion, stable descending album-count order, all-owned-album identity set, and untruncated qualified count. The adapter retains the 120-artist request cap, date-window policy, MusicBrainz requests/cache/rate limit, error reporting, and global merge. Direct-import contract tests are added. PR #233 is open on tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`. All four required workflows passed on that head: Python syntax/acquisition safety run 38934044235, Docker packaging/full unit suite/build run 38934044270, container runtime smoke run 38934044253, and validation-only multi-architecture validation run 38934044237. Assistant-side local tests were not run. Merge remains pending; publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — Classics genre enrichment extracted (PR #231 merged)

PR #231 moved the bounded genre annotation stage to `discovery_classics_genres.enrich_classic_genres(ranked, genre_lookup, family_classifier, limit=300)`. It retains normalized-artist lookup deduplication, order, the 300-candidate boundary, and empty/`other` fallback metadata. Last.fm provider/cache access and family classification remain injected; scoring, refresh jitter, and diversity selection remain in the builder. All four required workflows passed on exact PR head `0856f2a9a91e8b3aff88f933d845b182007997d4`; squash merge `b23d76712a04dcbfc461ceb7245a0676738fca7a`. Publishing and deployment remain paused.

## 2026-10-16 — Watcher progress-accounting seam completed (PR #230)

The narrow helper `acquisition_progress_accounting.observe_progress()` owns only the byte-counter comparison and progress-marker/timer update. The watcher retains its two-minute stall policy, 15-second switch countdown, source-switch/reset orchestration, slskd polling, filesystem verification, and import safety decisions. Direct-import tests cover progress increase, unchanged/decreasing observations, and the exact timeout boundary. PR #230 merged at `57f9776b1b517c7c86119b2a11d7f919b8cab631` from tested head `47fb2a5bb18d4101dde910dd30e5bad2ed13e2e7`. All four required exact-head workflows passed: syntax 1202, Docker packaging/full unit suite/build 1110, runtime smoke 919, and validation-only multi-architecture 963. Local test execution was not performed; publishing/deployment remain paused.

## 2026-10-16 — Classics-list critical-rating extraction completed (PR #229)

The first independently testable seam is critical-rating enrichment, not the whole builder. `discovery_classics_ratings.enrich_critical_ratings(candidates, rating_lookup, shortlist_limit=80, year_limit=30)` owns stable listener-ranked shortlist selection and candidate metadata updates; the adapter retains cached MusicBrainz access, library inventory, Last.fm gathering, scoring/jitter, genre enrichment, diversity selection, and response assembly. Tests inject a deterministic lookup and assert ordering, bounds, missing-rating behavior, and metadata updates. Keep this narrow; do not extract the whole provider/cache-backed pipeline with a large callback surface.

PR #229 merged at `925eb16cba7d2387cd0a17c7690e36d35f17e8f1` from exact tested head `28c364dca41971ea90667c175663de17b41ca7ab`. All four required workflows passed: syntax/acquisition safety run 1194, Docker packaging/full suite/build run 1102, runtime smoke run 911, and validation-only multi-architecture run 955. Provider/cache access remains in the adapter. Publishing/deployment remain paused.
## 2026-10-16 — Session closeout: PRs #225 and #226 merged

- **PR #225:** cached discovery-list filtering/projection moved to `discovery_list_payload.build_cached_discovery_list_response()`; exact head `573fe05d31dae422c25188688cd2fa949339e487`, squash merge `4d968b381d1f541b81a4a46d1753b5145347e33d`. All four workflows passed: syntax/acquisition safety 1187, Docker/full suite/build 1095 (477 tests), runtime smoke 904, validation-only multi-architecture 948.
- **PR #226:** background listening-profile refresh moved to `listening_profile.refresh_and_persist_background_profile()`; exact head `740979f1b4da4f5c13632ab3598c13bc09ed413e`, squash merge `f5a95338e978a14d01fb6a1c3741e2e6c8bea11c`. All four workflows passed: syntax/acquisition safety 1189, Docker/full suite/build 1097 (481 tests), runtime smoke 906, validation-only multi-architecture 950.
- Both retain server-owned validation/provider/persistence dependencies at the adapter boundary. No publication, deployment, or production runtime verification.

## 2026-10-16 — Session closeout: PRs #223 and #224 merged

- **PR #223 — personal recommendation allocation:** exact final tested head `b604940e4b7a20160d4f3710b009c6ca718c57c5`; squash merge `1ccb11485bf1efce3ff201fb7337407c3e668c47`. All four required workflows passed: syntax/acquisition safety 1171, Docker/full suite/build 1079 (468 tests), runtime smoke 888, validation-only multi-architecture 932.
- **PR #224 — personal recommendation payload shaping:** exact final tested head `6d2e0ccc8d24cd11b727255f171fd405384a8729`; squash merge `f795239589e6dd78f0f5e6d98cf2eadc897d6f49`. All four required workflows passed: syntax/acquisition safety 1177, Docker/full suite/build 1085 (473 tests), runtime smoke 894, validation-only multi-architecture 938.
- Both preserve the adapter boundary: provider/library access, ownership lookup, payload annotations, and diagnostics remain in the server. Docker packaging includes the extracted modules. Assistant-side local tests were not run.
- Publishing/deployment remain paused; no production runtime verification is claimed. The unreproduced acquisition-dismissal HTTP 409 remains deferred per user direction.
- **Next action:** refresh current main/open PRs/CI and choose the next small, low-coupling seam only if no higher-priority correctness or verification gap remains. Do not treat extraction count as a quota.

## 2026-10-16 — Session closeout: PRs #208–#210 merged

- **PR #208 — page/asset routes:** merged as `8ed54b0cc3750dc0aae1bc20efda61bba7dd71cd` from exact tested head `75305491eb12ff1796569f51e364aace41796292`. All four required workflows passed (syntax 1121, Docker/full suite/build 1028, runtime smoke 837, validation-only multi-architecture 881).
- **PR #209 — login-gate middleware:** merged as `669379aaed12092b1f826d46e0c3f8675e6ea6eb` from exact tested head `1b248dcb20d7a0f8622f32de6ae0bcfc3e5795ed`. All four required workflows passed (syntax 1123, Docker/full suite/build 1030, runtime smoke 839, validation-only multi-architecture 883).
- **PR #210 — session-cookie policy:** merged as `21cd2bc19e9af66bb155b0d036f3b1f9ffb8d28f` from exact tested head `a394b6ea75fff91fcd4828f1946c14b98bbcf827`. All four required workflows passed (syntax 1125, Docker/full suite/build 1032, runtime smoke 841, validation-only multi-architecture 885).
- Regression tests added for page routes/assets, authentication-gate decisions, and session-cookie security attributes. These are code merges only; publishing, deployment, and production runtime verification are not claimed.
- **Session outcome:** no further extraction started. Next session should refresh GitHub state and read the current requirements/workflow/test-plan/roadmap before choosing another candidate. Keep PR #194 unchanged as previously requested; review other open PRs against current priorities rather than assuming they are ready to merge.

## 2026-10-16 — Independent discovery policy extractions completed (PRs #205 and #207)

- **PR #205** extracted per-artist MusicBrainz release-group filtering/candidate construction to `discovery_new_releases.py`; exact tested head `079d355e972ea39d792c1dfa6fca6eab902800e3`, squash merge `32b39be400ec046e8310a87260346b1959141609`. All four required workflows passed (syntax 1111, Docker/full suite/build 1018, runtime smoke 827, validation-only multi-architecture 871).
- **PR #207** extracted Artist Deep Dives scoring/ranking/diversity policy to `discovery_recommendations.rank_and_diversify_deep_dive_candidates()`; exact tested head `20e565582579f4097eed3803748c87bb3d932a98`, squash merge `a5b0d865060c3d069a865be7a1cb43c1a072ae91`. All four required workflows passed (syntax 1114, Docker/full suite/build 1021, runtime smoke 830, validation-only multi-architecture 874).
- Both are independently reviewable, backend-only changes. Provider I/O and orchestration remain in the server adapter; direct-import regressions were added. Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.

## Next step

Refresh current GitHub main, open PRs, and exact-head CI. Continue with one small, low-coupling remaining application-assembly/domain-service seam; do not treat extraction count as a quota. Keep acquisition-dismissal HTTP 409 deferred unless it recurs or the user reopens it.


## 2026-10-16 — Library overview and source redaction extractions completed (PRs #202 and #203)

- **PR #202** merged at `7a95364a31f360bb20dd8d2919a9bfea93ec893c` from exact tested head `6903f40578f40fec08f1efde92d6577fcaeeced0`. Pure library-overview response shaping moved to `navidrome_client.library_overview_payload()`; the server retains API I/O and the compatibility/MCP response wrapper. All four exact-head workflows passed (syntax 1104, Docker/full suite/build 1011, runtime smoke 820, validation-only multi-architecture 864).
- **PR #203** merged at `89e639394122aebe29bfb8602a1135722ea28bbe` from exact tested head `14019b8beeca9b71fbb8167117dafea3f60c74ea`. Sensitive assignment redaction moved to `server_source_redaction.redact_assignment()`; source bounds and MCP response assembly remain in `get_server_source()`. Docker packaging includes the helper. All four exact-head workflows passed (syntax 1106, Docker/full suite/build 1013, runtime smoke 822, validation-only multi-architecture 866).
- Assistant-side local tests were not run; CI packaging jobs ran the full unit suite. No publication, deployment, or production runtime verification is claimed. Publishing remains paused and acquisition-dismissal HTTP 409 remains deferred.
- Next: refresh main/open PRs/CI and choose the next low-coupling seam; do not treat extraction count as a quota.


## 2026-10-16 — Navidrome response shaping extracted (PRs #196 and #198)

- **PR #196** merged at 277499ec949353f5f24542a8033a481283814782 from exact tested head 4b501c64c82a69af1805a7f6195b4fc15ef0c836. navidrome_client.search_result_payload() now owns pure search response shaping; search_music() remains the compatibility adapter. Direct-import tests cover category filtering, fields, and output ordering.
- **PR #198** merged at 92cdd6309244e78e78bd0f6f8d2e38ea929e434b from exact tested head a718780edcb85eb8f4453e44a2d5a4925a512314. navidrome_client.album_details_payload() now owns pure album/track response shaping; get_album_details() remains the compatibility adapter.
- All four required workflows passed on each exact final head. PR #196: syntax 1088, packaging/full suite/build 995, runtime smoke 804, validation-only multi-architecture 848. PR #198: syntax 1090, packaging/full suite/build 997, runtime smoke 806, validation-only multi-architecture 850.
- No assistant-side local tests, image publication, deployment, or production runtime verification are claimed. Acquisition-dismissal HTTP 409 remains deferred; publishing remains paused.
- Next: refresh main/open PRs/CI and identify the next low-coupling seam. Do not treat extraction count as a quota.
## 2026-10-16 — Artist-biography identity matching extracted (PR #190)

PR #190 merged at `b829fa953d979563a8ace6e5529eace8cb80ac43` from exact tested head `6c04d8a67944568a3e2b280deafb4eb2c66c2391`. Pure Wikidata/Wikipedia identity matching and biography text selection moved into `app/services/artist_bio.py`; provider I/O, concurrent retrieval, cache ownership, and HTTP behavior remain in `app/api/metadata.py`. All four exact-head workflows passed: syntax 1059, Docker packaging/full suite/build 966, runtime smoke 775, and validation-only multi-architecture 819. No local test run, publication, or deployment is claimed.
## 2026-10-16 — Dashboard-pick service extraction merged (PR #189)

PR #189 merged at `f5f355f8bdc0599bb240933e248177c7b0517ff5` from exact tested head `d28aaa33f7096ba764232d6bd435cc68d5d85f98`. Dashboard candidate aggregation and category balancing moved to `app/services/dashboard.py`, with injected list-reading, eligibility, and shuffle dependencies. Route validation and response contract remain in `app/api/dashboard.py`. All four required exact-head workflows passed: syntax 1052, Docker packaging/full suite/build 959, runtime smoke 768, and validation-only multi-architecture 812. No local test run, publication, or deployment is claimed. Acquisition dismissal HTTP 409 remains deferred.

## 2026-10-16 — slskd connection probe extraction merged (PR #187)

PR #187 merged as `b7ae6458adda3650f178fc64457914beb66ece9c` from exact final PR head `920590871883aa8c75c29a1b16131bd88519072d`. `slskd_client.test_connection()` owns the connection probe with injected configuration and HTTP access; `discovery_test_slskd_connection()` remains the compatibility adapter. Direct-import tests cover success, 401/403, HTTP/configuration failures, and API-key redaction. All four required exact-head GitHub Actions workflows passed (syntax run 1041, Docker packaging/full suite/build run 948, runtime smoke run 757, validation-only image run 801). Assistant-side local tests were not independently run. No publishing/deployment/runtime-on-production verification is claimed.

## 2026-10-16 — slskd connection probe boundary in progress (PR #187)

The configured slskd connection probe is being extracted into `slskd_client.test_connection()`. The legacy `discovery_test_slskd_connection()` remains the adapter; settings lookup remains injected, and no acquisition lifecycle or filesystem behavior is changed. Direct-import tests cover success, authentication failures, HTTP/configuration errors, and secret redaction. Docker packaging includes the new module. Final-head CI and merge remain pending; publishing/deployment are paused.

## 2026-10-16 — slskd progress aggregation and speed calculations extracted

- **PR #182:** extracted pure matched-record progress aggregation into `slskd_transfers.summarize_transfer_progress()`. Exact tested head `045131f58365dd0e6538c1712f37f56f639c65ad`; merge `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`. All four required exact-head workflows passed: syntax 1016, Docker packaging/full suite/build 923, runtime smoke 732, validation-only multi-architecture 776.
- **PR #183:** extracted delta-based speed estimation into `slskd_transfers.estimate_transfer_speed()`. Exact final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`; merge `e4e9bd1fad9536f00f3908d753b66147d30ca03f`. All four required workflows passed: syntax 1019, Docker packaging/full suite/build 926 (342 tests), runtime smoke 735, validation-only multi-architecture 779. A failing initial expectation was corrected before the final passing head.
- Both extractions preserve the public progress schema and keep snapshot locking/state ownership in `navidrome_server.py`. Local assistant-side tests were not run. Publishing/deployment/runtime verification remain unperformed.
- Keep acquisition-dismissal HTTP 409 deferred until modularization is complete, as directed. Do not weaken cleanup safety.
- **Next:** refresh current main/open PRs/CI and choose one independent low-coupling seam; do not treat throughput as a quota.

## 2026-10-16 — slskd queue and progress transfer matching completed

- **Queue request boundary (PR #180):** `slskd_transfers.queue_download_files()` now owns the slskd queue POST. The existing service adapter and `acquisition_orchestration` retain dismissal locking and decision flow. Tested head `ce0e635cc77c687958d6ad1c1a852e55476c14b2`; merged `7c670f2eac838934bc9afa7f40f892ff595ca4ca`. All four required exact-head workflows passed.
- **Progress transfer matching (PR #181):** `slskd_transfers.match_expected_transfer_records()` owns case-folded basename matching and duplicate transfer-state precedence. The live-progress service retains byte accounting, speed snapshots, and output schema. Tested head `cf78b4188a549d6e1b2b98c76a63a6bc0826d129`; merged `3df14d3c59bb7e5a689d797028e45468c6a87ee7`. All four required exact-head workflows passed.
- Both changes include direct-import regression coverage; assistant-side local tests were not run. Publishing/deployment/runtime verification remain separate and unclaimed.
- Keep acquisition-dismissal HTTP 409 deferred until modularization is complete, as directed. Do not weaken filesystem safety or infer a fix.
- **Next:** refresh main/open PRs/CI and select one small, independently testable seam.

## 2026-10-16 — Last.fm similar-artist parsing extraction completed

- PR #178 merged as `f18574b74a564031c5268cf04c956475d64dc30c`, from tested head `a97be052d3a1e74843feaacd6403d10ce5aad6af`.
- `LastFmClient.similar_artists()` now owns cached `artist.getSimilar` response normalization; `_lastfm_similar_artists()` remains the compatibility adapter.
- Exact-head CI succeeded for syntax, Docker packaging, container runtime smoke, and validation-only Docker image build (publishing paused). Local full-suite execution was not independently verified in this session.
- Continue with a fresh main/PR/CI inspection before selecting the next small extraction. Keep publishing paused; acquisition-dismissal HTTP 409 remains deferred.

---

## 2026-10-16 — Last.fm similar-artist parsing extraction in progress

- Based on refreshed GitHub `main` at `86b2ac60416ed725755fc6c57200e1c3123b7606`, after PR #175/#176 closeout.
- `LastFmClient.similar_artists()` owns cached `artist.getSimilar` response normalization; `_lastfm_similar_artists()` remains the legacy compatibility adapter.
- Added direct-import and adapter regressions for scalar/list payloads, invalid/blank records, similarity values, request parameters, 60-day TTL/cache behavior, and missing payloads.
- Verify full suite, syntax, packaging, runtime smoke, and non-publishing multi-architecture CI on the exact final PR head before merge. Keep publishing paused and the acquisition-dismissal HTTP 409 deferred.

---

## 2026-10-16 — Last.fm top-albums parsing extraction in progress (PR pending)

- Based on refreshed GitHub `main` after PR #174 merge: `4dd8b926a7a6cf76e248420860d7c29c892da3c0`.
- `LastFmClient.artist_top_albums()` owns cached `artist.getTopAlbums` retrieval and record normalization. The legacy `_lastfm_top_albums()` adapter retains discovery-specific album eligibility filtering.
- Added direct-import regression coverage for scalar/list payloads, blank-title filtering, metadata normalization, request parameters, cache TTL/hits, missing payloads, and compatibility adapter filtering.
- CI, merge, publication, deployment, and production runtime verification pending. Acquisition dismissal HTTP 409 remains deferred as directed.

---

## 2026-10-16 — Three additional extractions completed (PRs #170–#172)

These were implemented and merged sequentially, refreshing GitHub `main` between each PR.

- **MusicBrainz tag audit, PR #170:** `music_tag_audit.py` now owns the bounded, read-only missing-MBID scan. `navidrome_server.find_missing_mbids()` remains the JSON/error-string adapter. Tested head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07`; merge `dbbdda35792fd569cfdeec2c4c7b42fc106f84e3`. All four exact-head workflows passed: syntax `38827001217`, full suite/build `38827001215`, runtime smoke `38827001195`, validation-only multi-architecture `38827001227`.
- **Recommendation style classification, PR #171:** `discovery_recommendations.py` now owns the pure broad genre-family, recent listening-style, primary-family, and regional diversity-style classifiers previously nested in `recommend_new_music()`. Final tested head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9`; merge `6d00562405320affcb1a04b4359397b332cd5bf5`. All four exact-head workflows passed: syntax `38827709662`, full suite/build `38827709650` (319 tests), runtime smoke `38827709649`, validation-only multi-architecture `38827709610`.
- **Last.fm album popularity, PR #172:** `LastFmClient.album_popularity()` now owns the cached `album.getInfo` request, response parsing, and error mapping. `navidrome_server._lastfm_album_popularity()` remains the adapter that updates the legacy `LASTFM_LAST_ERROR` diagnostic. Final tested head `d2808d44825e949ff71ed8471d25cee6570b54f1`; merge `d5153a3fe0625bc52b5896e87846b55cabe58e81`. All four exact-head workflows passed: syntax `38827973048`, full suite/build `38827972941` (324 tests), runtime smoke `38827972940`, validation-only multi-architecture `38827972938`.

Assistant-side local tests were not run; CI ran the full unit suite for each final head. Publishing remains paused and no deployment/runtime verification is claimed.

**Acquisition-dismissal HTTP 409 deferral:** the user explicitly directed that the unreproducible 409 investigation wait until modularization is complete. Keep PRs #44 and #45 closed, do not claim a fix, and do not weaken cleanup validation. Revisit the issue after the planned modularization is complete and reproduce/root-cause it before changing behavior.

**Next:** re-audit the current `main` and remaining independent application-assembly/domain-service seams before selecting the next extraction. PR #23 remains open as the roadmap.

---

## 2026-10-16 — Three integration client extractions completed

The following independent seams were extracted sequentially and merged to GitHub main. Each PR kept a compatibility adapter in `navidrome_server.py`, added direct-import/adapter regressions, and updated Docker packaging.

- **ListenBrainz:** PR #163; tested head `4c494a2679884579df5d6bc204287637e45e2ccd`; merge `7be68c74b8a97ed4d9c50e6a7e22e296b25e79e2`. Bounded recent-listen paging and cursor logic moved to `listenbrainz_client.py`. Exact-head CI: compile `38822823853`, full suite/build `38822823922`, runtime smoke `38822823751`, non-publishing multi-architecture validation `38822823989` — all passed.
- **Last.fm:** PR #164; tested head `957f3a56afe15e4dd665b041f1fbf7803921d3b6`; merge `9f174c6086c0d2b9749e53e38cbe8e1eb337e22f`. Cached provider requests, API-key handling, cache-key identity, and request pacing moved to `lastfm_client.py`. Exact-head CI: compile `38823469617`, full suite/build `38823470035`, runtime smoke `38823469896`, non-publishing multi-architecture validation `38823469762` — all passed.
- **MusicBrainz rating:** PR #165; tested head `4888bd08fdf05007cc74ad7005a196fd678305b5`; merge `a0cd3d8ff5dcdf6acb7d678c9fc8f1aa0d537629`. Cached rating/vote/year lookup moved to `musicbrainz_rating_client.py`, preserving TTL, pacing, 404 caching, and output shape. Exact-head CI: compile `38823643925`, full suite/build `38823643703`, runtime smoke `38823643931`, non-publishing multi-architecture validation `38823643848` — all passed.

Assistant-side local test execution was not performed; the full unit suite was run by CI on each exact final PR head. Publishing and deployment remain separate and unverified.

**Deferred acquisition-dismissal HTTP 409 (user direction, 2026-10-16):** the user cannot currently reproduce the issue and explicitly directed that it remain deferred until modularization is complete. Keep PRs #44 and #45 closed. Do not claim a fix or weaken safety checks; revisit after planned modularization is complete, and reproduce/root-cause the issue before changing behavior.

---

## 2026-10-15 — PR #160 merged: discovery refresh orchestration extraction

- PR: https://github.com/abucalip/navi-librarian/pull/160. Exact tested head: `5aafc1a9c5835e2d9e2959a36e7419d09913403a`; squash merge commit: `dba172d5747607e65e8fadd32442b12d32054749`.
- Extracted ordered refresh-all orchestration into `discovery_refresh.refresh_all`; retained `navidrome_server._discovery_refresh_all()` as the compatibility adapter.
- Added regression coverage for callback order, personal count (20), and returned results. The existing module packaging was unchanged.
- All four required workflows passed on the exact PR head: Python syntax `38818349092`, Docker packaging/full unit suite/image build `38818349082`, container runtime smoke `38818349397`, and validation-only Docker/multi-architecture validation `38818349076`.
- MCP registrations, signatures, names, response shapes, provider calls, lock ownership, and persistence behavior remain unchanged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.

---

## slskd transfer listing extraction — completed (PR #157 merged, 2026-10-15)

`slskd_transfers.py` owns the HTTP transfer-list request and recursive normalization into file records carrying `_transfer_directory`. It uses an injected HTTP client. `navidrome_server._slskd_download_transfer_files(base_url, headers, username)` remains the compatibility adapter used by candidate-start validation. The implementation preserves URL encoding, 8-second timeout, 404-as-empty behavior, HTTP error propagation, nested directory inheritance, copied file records, and transfer-directory identity. Direct-import and adapter tests cover these contracts. PR #157 merged at `17922f878f0ea391b47652012a38530e9eb044fc` from exact tested head `504b10392061dbc44d28d66e663b88cbefb8f1a4`. All four required workflows passed: syntax `38816375215`, Docker/full suite/build `38816375266`, runtime smoke `38816375339`, multi-architecture validation `38816375410`.

## Expected slskd track-count extraction — completed (PR #155 merged, 2026-10-15)

Moved expected track-count metadata parsing into `slskd_search.py`; retained `_discovery_expected_track_count(metadata)` as the compatibility adapter. PR #155 merged at `d732241de9edfd3c643a8fa89fb25c42b2a93c67` from exact tested head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`; all four required workflows passed.

## Next gate before further modularization

PR #156's manual browser checklist was completed and published for exact tested head `47d33cbecadf64ed4b434764883cec6ae99d30bc`; PR #156 merged at `c560c28063f26a1a72d7016c951bf265d2ddd158`. The former UI verification gate is resolved. Re-check current main/open PRs/CI and prioritize remaining safety or verification gaps before routine extraction. Publishing remains paused.

## Music path default policy — completed (PR #151)

Extracted environment override and mount-path fallback into pure `music_paths.py`, retaining `navidrome_server._default_music_dir()` and existing initialization. Direct-import regressions and Docker packaging are in place. All four required workflows passed on exact PR head `07cf1ab7dab46a1409236f7134881011dc31cac2`; merge commit `6a7678bd04ef539ae5f4c118b6707524fd569280`. Publishing remains paused; deployment is unverified.

## Navidrome API transport boundary — completed (PR #150 merged, 2026-10-15)

The Navidrome HTTP transport has been extracted from `navidrome_server.py` into `navidrome_client.py`. The module owns token creation, request construction, HTTP execution, and response-status interpretation with the existing settings provider injected by the caller. `api_call(method, **params)` remains the legacy adapter, preserving discovery/MCP callers and API error semantics. Direct-import tests cover authentication parameters, request options, successful responses, and error messages; Docker packaging includes the module. All four required workflows passed on exact PR head `be9a2558bd87eb8e7e2fbf25593936aa8c671a1a`: Python syntax `38802307579`, Docker packaging/full suite/build `38802307812`, container runtime smoke `38802307700`, and validation-only multi-architecture validation `38802307683`. PR #150 merged to main at `efc2acb93e3edb570e77419daa866f4a228c85d2`. Publishing/deployment remain separate and are not claimed. Next: inspect the current open-PR list and remaining application-assembly/domain-service seams to choose the next focused change.

## Metadata cache / domain-service boundary — completed (PR #148 merged, 2026-10-15)

The SQLite TTL cache now lives in `metadata_cache.py` with injected database path and clock. Legacy `_metadata_cache_get` / `_metadata_cache_set` adapters preserve the existing table/schema, cache keys, TTL behavior, and non-fatal storage-error semantics. Direct-import regressions and Docker packaging were included; PR #148 merged at `99e8da326fb0e2c4a8cf22acf9000e28647ec20f` after the four required workflows passed on the exact final PR head.


## Settings persistence boundary — completed (PR #143 merged, 2026-10-15)

The settings persistence implementation has been extracted from `navidrome_server.py` into `settings_persistence.py`. The store owns SQLite initialization, restrictive database permissions, persistence reads/writes, saved music-path application, and existing legacy quality/download-path migrations, using injected defaults and path callbacks. Legacy `_discovery_settings_*` wrappers preserve callers and MCP behavior; Docker packaging includes the module. Direct-import regression tests cover persistence round trips, malformed data, migration order, music-path application, and permissions.

PR #143 exact final head `e28cd12d3736fd2eb368b53c98e3cbddb5438166` passed all four required workflows: Docker packaging/full tests/build `38791730058`, Python syntax `38791730078`, container runtime smoke `38791729963`, and validation-only multi-architecture image validation `38791730017`. Squash merge: `409f634a20ba67c5a39dfec0e5bf57995a3fefbe`. Publishing, deployment, and production runtime verification remain separate and paused.
## 2026-10-15 — MCP tool registration separated from shared service imports

- Moved the 27 existing MCP tool registrations into the new mcp_registry.py; navidrome_server.py no longer imports MCPServer, constructs an MCP server, or decorates service functions at import time.
- The legacy MCP entry point remains compatible: when navidrome_server.py is executed directly, it creates the server through create_mcp_server() and runs on the existing streamable HTTP host/port. Tool names and function objects are kept in an explicit ordered registry.
- The web service can now import navidrome_server.py without loading mcp.server.mcpserver. MCP registration is deferred to explicit server startup; the MCP package and legacy tool surface are retained.
- Added tests/test_mcp_registry.py to assert the registry contains 27 unique tools, registers each provided function exactly once, and importing the legacy service keeps all registered functions callable without importing the MCP SDK.
- Branch: refactor/separate-mcp-tool-registration. All four required workflows passed on exact implementation/documentation head fe71a9a19188a018a2ee65d5b313a99413d239f2: Python syntax/acquisition safety run 38783091362; Docker packaging/full suite/build run 38783091326; container runtime smoke run 38783091309; validation-only multi-architecture run 38783091337. Publishing remains paused. No separate local test execution, deployment, or production runtime verification is claimed. PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00 from exact final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f. All four required workflows passed on that exact head: syntax/acquisition safety 38783296279; Docker packaging/full suite/build 38783296173; container runtime smoke 38783296256; validation-only multi-architecture 38783296249. Publishing/deployment remain paused; no production runtime verification is claimed.

## 2026-10-15 — PR #116 merged: Proxmox MCP SDK compatibility and handler regression

- PR #116 merged at `9e6979203cbdb6f2d38225584952136170eb2df5` from exact tested PR head `a14accac574d1997e6785ffbf170be136b95c5b9`.
- Corrected the host-side entry point to use `mcp.server.mcpserver.MCPServer`, matching pinned `mcp==2.3.0` and the main MCP server. MCP startup now occurs only when `server.py` is executed as a script.
- Added handler regressions proving rejected shell-composed commands never invoke SSH, accepted commands retain the existing SSH argument/timeout/output behavior, and output remains capped at 20,000 characters.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety `38742736856`; Docker packaging/full suite/build `38742737079` (243 tests passed); container runtime smoke `38742737082`; validation-only multi-architecture image validation `38742736770`.
- An earlier CI cycle exposed the stale FastMCP import; the defect was corrected and all four workflows passed on the final head. No local test run or live Proxmox command, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — Security priority completed: Proxmox MCP command allowlist

- PR #114 merged at `6ab848d444373dfa37e6d46528a2840a53a8f763` from exact tested head `cd8319696180875a3cb6f0dc151d88e0c8c490d7`.
- The host-side Proxmox MCP now accepts only explicitly approved diagnostic command forms and rejects arbitrary shell execution before SSH. Direct-import regressions cover accepted and rejected inputs.
- All four required exact-head workflows passed: syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`. Publishing/deployment remain paused; the host-side MCP is not part of the application image.
- **Next (superseded 2026-10-16):** continue the modularization roadmap using current main/open-PR/CI evidence. Per the user's direction, keep the acquisition-dismissal HTTP 409 investigation deferred until modularization is complete; do not reopen PRs #44/#45 or claim a fix without reproduction and root-cause evidence.


---

## 2026-10-15 — PR #108 merged: discovery router service injection

- Merged PR #108 at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` from exact tested head `a5170e50080c0ca94b4068155ace83fd33c6f029`.
- Discovery routes now use the shared lazy `get_librarian` dependency. Domain behavior and MCP wrappers remain in the legacy service boundary.
- Updated legacy discovery route tests to inject fake services instead of patching a removed module-level `librarian` attribute.
- All four required exact-head workflows passed: syntax/acquisition safety (`38733725606`), Docker packaging/full suite/build (`38733725816`, 227 tests), container runtime smoke (`38733725595`), and validation-only multi-architecture image validation (`38733725591`). Publishing/deployment remain paused.

---

## 2026-10-15 — PR #107 merged: acquisition router service injection

- **PR:** https://github.com/abucalip/navi-librarian/pull/107; final tested PR head `67174e8026f44382a4a6bea48ff1df80744dda35`; squash merge / main SHA at closeout `1cc15dd6343370ce0915bf7228a745d3558b393b`.
- **Change:** added `app/api/dependencies.py` with lazy `get_librarian()` and injected it into all acquisition routes. This removes the acquisition router's import-time import of `navidrome_server` while preserving endpoint paths/methods, existing service calls, payload mapping, HTTP error behavior, and SSE response headers. Added regression tests for route contracts, dependency wiring, fake-service handler calls, validation, and sanitized errors.
- **Exact-head CI:** all four required workflows passed on `67174e8026f44382a4a6bea48ff1df80744dda35`: Python syntax `38732084595`; Docker packaging/full unit suite `38732084663`; container runtime smoke `38732084579`; validation-only multi-architecture image build `38732084589`. An earlier test-only assertion failure on `d6a1696c06f594e2c4025e0eff54bb8496fd8e29` was corrected before these passing runs.
- **Status:** Implemented, tested, CI passed, merged. Publishing remains paused; this did not publish an image, deploy the application, or verify production runtime. `app/main.py`, discovery, and settings still import `navidrome_server`; MCP tools and domain logic were not removed or duplicated.
- **Next priority:** continue the narrow web service-injection audit at the discovery router, preserving API behavior and MCP compatibility. Keep deployment/runtime verification as a separate gate; do not resume routine modularization if a higher-priority safety or delivery gap appears.

---

## 2026-10-15 — Web dependency audit and next safe seam

- Read-only audit complete: the FastAPI app imports `navidrome_server` in the app assembly and the acquisition, discovery, and settings routers. Metadata and auth route modules are independent; auth already demonstrates dependency injection.
- Next narrow task: introduce a shared, injectable web service dependency/factory while keeping `navidrome_server` as the default adapter. Preserve MCP wrappers, route contracts, error mapping, and persistence ownership. Do not move or duplicate domain logic in the HTTP layer.
- Do not reopen the deferred dismissal HTTP 409 investigation unless the user reports recurrence. Continue verifying current-main CI and open PR state before starting the next code change.

---

## 2026-10-15 — Acquisition import source-root safety merged (PR #103)

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- The import boundary now pins source and destination-parent directories, performs descriptor-relative moves/rollback, and retains cross-filesystem fallback. Regressions cover source-root symlink swaps, collision-suffixed names, cross-filesystem behavior, and rollback; all four required exact-head workflows passed.
- **Next:** continue the highest-priority safety/test audit across remaining filesystem operations and external boundaries before routine service-boundary extraction. Publishing remains paused; no deployment/runtime verification.

---

## 2026-10-15 — Cleanup root traversal hardening merged (PR #100)

- PR #100 merged at `6e8e861cc84d5951b0d177ffea256a0dd88fe4b4` from exact tested head `89813bd3802b1f8920715aaeca55ccb5e461c9c9`.
- The configured root is now traversed component-by-component without following symlinks; directory and file identities plus the exact planned file set are revalidated before descriptor-relative deletion. Both target and ancestor symlink-swap regressions pass in exact-head CI.
- Resume the remaining highest-priority safety/test audit before routine service-boundary extraction. Publishing remains paused; no deployment/runtime verification.

---

## 2026-10-15 — PR #99 safety hardening merged

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- The acquisition cleanup TOCTOU window is hardened and regression-tested; all four required workflows passed on the exact PR head. Publishing and deployment remain paused.
- **Next:** continue the highest-priority safety/test audit, especially remaining filesystem operations that cross external callbacks or filesystem boundaries, before routine modularization.

---

## 2026-10-15 — PR #98 merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- The top-level acquisition request decision sequence now lives in `acquisition_request_coordinator.py`; adapters, persistence ownership, shared locks, and watcher lifecycle remain in the legacy server boundary.
- All four required workflows passed on that exact head. Continue with the highest-priority safety/test gaps before routine service extractions.

---

## 2026-10-15 — PR #97 merged: Last.fm save policy

- Merged at `ad239a59b77612b812ca842406fee7b47cf80889` from exact tested PR head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`.
- Last.fm API-key normalization, blank-input preservation, configured-status serialization, and settings-write invocation now live in `service_settings.py` behind injected callbacks. MCP/web adapter compatibility and SQLite ownership remain in `navidrome_server.py`.
- All four required workflows passed on the exact PR head: syntax `38721333335`, Docker packaging/full unit suite `38721333353`, runtime smoke `38721333332`, validation-only multi-architecture `38721333418`. Publishing remains paused; no deployment/runtime verification.
- Next: resume the highest-priority remaining test/coordination audit from the roadmap and inspect callers/tests on current main before selecting the next narrow change.

---

## 2026-10-15 — slskd settings policy extraction (PR #96)

- PR #96 extracts slskd configuration validation, safe settings serialization, and settings update policy into `service_settings.py`. The legacy MCP functions remain adapters; connection checks, SQLite persistence/schema, and global `MUSIC_DIR` ownership remain in `navidrome_server.py`.
- Added direct-import tests for missing/invalid configuration, secret redaction and blank-key preservation, exact quality-tier validation (including malformed non-string values), path validation before writes, and music-path callback updates. Migrated quality-priority policy assertions off the AST-executed settings adapter while preserving the AST-based persistence fixture.
- Exact implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four workflows: syntax `38665710740`, Docker packaging/full suite `38665710718` (208 tests), runtime smoke `38665710761`, validation-only multi-architecture `38665710769`. Publishing remains paused; no deployment/runtime verification.
- Before merge, verify all four workflows on the final documentation-updated PR head and review the complete diff. Continue with a caller-driven audit of remaining settings persistence and service integration boundaries; do not remove MCP while web callers still import the legacy module.

---

## 2026-10-15 — PR #95 merged; slskd settings-policy extraction next

- PR #95 merged at `2193306ce6ee2ff3ed087b2f490594f2d5ee2c68` from exact head `92d304d06713ec0f73253a5db48cf835ff93a063`; all four required workflows passed on that head (syntax `38665121156`, Docker packaging/full suite `38665121160`, runtime smoke `38665121170`, validation-only multi-architecture `38665121255`). Publishing remains paused.
- The next narrow seam is `_slskd_config`, `discovery_get_slskd_settings`, and `discovery_set_slskd_settings`. Move validation/serialization/update policy into `service_settings.py` with injected settings read/write and current/set music-directory callbacks.
- Preserve the MCP-decorated function names/signatures and JSON response strings, including blank API-key preservation, supported quality tiers, default quality labels, absolute download-path behavior, existing music-library directory validation, and path-update timing. Keep live HTTP connection checks and persistence/schema ownership in `navidrome_server.py`.
- Direct tests must cover secret redaction, blank-key preservation, invalid URL/quality/path no-write behavior, defaults, and the callback updating the runtime music directory only after a successful persisted write. Keep the Docker image/module list synchronized.
- No local test run, publication, deployment, or production runtime verification is claimed for PR #95.

---

## 2026-10-15 — Service settings policy extraction (PR #95)

- Extracted six settings-policy/configuration functions into importable `service_settings.py` with injected persistence/path callbacks. The AST-coupled test harness was replaced with direct imports against the real module.
- Preserved legacy MCP/web adapter names and signatures. Kept SQLite initialization/migrations, global `MUSIC_DIR` mutation, service connectivity requests, and other service settings in `navidrome_server.py` to keep this step narrow.
- Added `service_settings.py` to the Docker image file list. Final PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9` passed all four required workflows (syntax/acquisition safety `38664285319`, Docker packaging/full suite `38664285227`, runtime smoke `38664285195`, validation-only multi-architecture `38664285194`; publishing paused). The earlier callback-injection mismatch was corrected before this final-head verification. No local test run, publication, deployment, or production runtime verification is claimed.
- After PR #95's review/merge decision, continue a caller-driven audit for the next safe direct-import seam. Do not retire MCP while the web app still imports the legacy module.

---

## 2026-10-15 — Web dependency audit complete; settings policy is next seam

- Traced the current web callers of `navidrome_server.py` across `app/main.py`, `app/api/acquisitions.py`, `app/api/discovery.py`, and `app/api/settings.py`. They use shared persistence/configuration, recommendation/list operations, acquisition lifecycle functions, and service settings/connectivity methods. `app/main.py` imports the legacy module directly, so importing the web app also initializes/registers MCP tool definitions.
- `server.py` is a separate MCP entry point and `requirements.txt` pins the MCP dependency; the Dockerfile does not copy or launch `server.py`. Do not remove MCP code or dependency until a repository-wide caller/entry-point audit and compatibility decision support it.
- **Smallest next extraction:** move the six functions currently AST-executed by `tests/test_service_settings.py` into a direct-import settings-policy module with injected read/write and music-directory dependencies. Preserve the existing `discovery_*` functions as thin MCP/web compatibility adapters. Leave database initialization/migrations, global path mutation, and live connectivity checks where they are for this focused step.
- Acceptance: direct-import tests cover validation, blank-secret preservation, redaction, invalid-input no-write behavior, path handling, and response compatibility; adapter tests preserve names/signatures; full unit suite, syntax check, Docker/API smoke, and all four required CI workflows pass on exact PR head. No secrets or production data are touched.
- This session was audit-only; no code changes or tests claimed. The next step is implementation of that narrowly scoped extraction.

---

## 2026-10-15 — Acquisition AST-boundary audit complete

- Reviewed remaining AST-coupled lifecycle tests against the direct-import suites and current orchestration helpers.
- No further test migration was safe: the remaining cases protect shared-lock/reservation integration, persist-before-import ordering, top-level handling of incomplete saved state, dismissed-Get adapter/status behavior, stale watcher recovery without requeue, and end-to-end broad-query retry diagnostics. The isolated helpers are covered directly, but those tests do not replace the integration assertions.
- No application/test code changed in this audit. Do not treat baseline `main` CI as validation of a future branch.
- **Next implementation priority:** read-only audit of `navidrome_server.py` dependencies from `app/main.py`, `app/api/acquisitions.py`, `app/api/discovery.py`, `app/api/settings.py`, and `server.py`. Use the findings to select the smallest service boundary for independent web tests; do not retire MCP code/dependencies as part of the audit.

---

## 2026-10-15 — PR #92 merged: dismissed-acquisition preflight seam

- PR #92 merged at `60698f7bf1413e4c643309e200d1ace2e268bee3` from exact tested head `1f0ce2174e1e60f3aab7c898dd534b8b1f11e858`.
- Dismissal/reactivation preflight and retry-metadata normalization now live in `acquisition_orchestration.reactivate_dismissed_acquisition_if_needed`.
- The server retains shared transition-lock ownership and the existing refusal response. State-store conditional update and stale-source clearing remain unchanged. Direct helper tests supplement—not replace—the top-level AST success/refusal cases.
- All four required workflows passed on the exact PR head: syntax/acquisition safety `38661883721`, Docker packaging/full suite `38661883755` (203 tests), runtime smoke `38661883730`, and multi-architecture validation `38661883723` with publishing paused.
- Next: continue the remaining acquisition lifecycle AST-coupled test audit before routine modularization proceeds. Publishing, deployment, and production runtime verification remain separate uncompleted states.

---



## 2026-10-15 — PR #90 merged; request reservation seam extracted

- PR #90 merged at `4756ad6a7669ab77e284309ca9cd0f178e7f032a` from exact tested head `c0b4a0ebcc5fa4ef8b71441fb38d55aed8fce097`; all four workflows passed (199 tests, publishing paused).
- `acquisition_orchestration.reserve_acquisition_request` now owns the active-request identity check/add; `discovery_acquire_album` retains transition-lock ownership, ensuring persisted-state preflight and reservation stay atomic.
- `run_reserved_acquisition` owns callback execution outside the lock and reservation cleanup under the lock. The end-to-end concurrent-request AST test remains.
- Next focused seam: dismissal/reactivation preflight and metadata normalization. Preserve safe refusal when reactivation fails, conditional state persistence, and the legacy MCP adapter. Do not migrate the wrapper-level success/failure tests unless equivalent direct coverage preserves the same integration boundary.

---

## 2026-10-15 — Watcher-start concurrency regression verified

- PR #84 exact tested head: `398486476aacdbbefefeaee5cb79182cc0835fb8`; all four required workflows passed (syntax 38656927551, Docker packaging/full suite 38656927436, runtime smoke 38656927801, multi-architecture validation-only 38656927516).
- Added direct-import concurrency coverage without production behavior changes. The remaining AST lifecycle cases remain because they cover coordinator races, persistence-before-import, dismissed-job reactivation, incomplete saved state, and stale watcher recovery.
- Next: merge PR #84 after exact-head status confirmation, then continue identifying genuinely helper-only AST tests for safe migration. Publishing and deployment remain unverified and paused.

---

## 2026-10-15 — Session closeout and next test-audit boundary

- Reconciled against GitHub `main` at `f46b3618eaa8abc98b7f077698439b304a0005b7`; PR #82's documentation closeout is merged. PR #76 polling extraction and PR #78 dismissal-serialized import guard remain merged with exact-head CI evidence documented below.
- No implementation or test changes in this closeout. The next step is a test-boundary audit, not an automatic extraction: identify which remaining AST cases are pure helper behavior versus real coordinator integration.
- Prioritize duplicate-request reservation/concurrency, incomplete persisted candidate details, explicit reactivation and failed-reactivation refusal, and stale watcher recovery. Preserve conditional persistence, shared locks, filesystem safety, and recovery integration checks unless replacement coverage demonstrably exercises the same boundary.

---

## 2026-10-15 — PR #78 merged: import dismissal guard extraction

- PR #78 merged at `5d638c7adf5a42fdac8052cb4fc223236564cd72` from tested head `e6a609ca7381d0751d529b52f55aeebd56d76661`.
- `acquisition_orchestration.import_source_unless_dismissed` now owns the lock/check/callback guard; the shared transition lock spans the entire import callback.
- Filesystem path/mount identity validation, destination checks, persistent status transition, import staging, and rollback remain in their existing safety owners. Only the dismissal-only AST regression moved to direct tests.
- All four required workflows passed on exact head (syntax `38653493244`, package/full suite `38653493312`, runtime smoke `38653493285`, image validation/publishing paused `38653493279`); 186 tests passed.
- Next: audit the remaining AST lifecycle tests for safe direct-import migration, focusing on duplicate-request reservation, dismissed-job reactivation/refusal, incomplete saved candidate details, and stale watcher recovery. Preserve the end-to-end concurrency and persistence tests until equivalent direct tests exercise the same boundaries.

---


## 2026-10-15 — PR #76 merged: slskd polling extraction

- PR #76 merged at `a55a9fa7eed1e221f52434b50f44d0c415fd491a` from exact tested head `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6`.
- Extracted progressive query/poll/wait behavior into `slskd_search_polling.py`; direct tests cover fallback, delayed payloads, legacy endpoint compatibility, and unexpected HTTP errors. The AST-based end-to-end retry test remains for coordinator output semantics.
- All four required workflows passed on the exact head (syntax `38652846800`, packaging/full unit suite `38652846779`, runtime smoke `38652846790`, image validation/publishing paused `38652846819`); 184 tests passed.
- Next: audit remaining AST lifecycle tests for duplicates versus genuine coordination boundaries: simultaneous requests, conditional importing-state persistence, dismissal/import exclusion, incomplete saved details, dismissed-job reactivation/refusal, and stale watcher recovery. Preserve races, conditional writes, cancellation/cleanup refusal, and recovery behavior.

---

## 2026-10-15 — PR #73 merged: candidate extraction test migration complete

- PR #73 merged at `df2f79b3d18df7d13484f7e3b5e7f550a39323d3` from tested head `a33772ca1da0b6628da490b69f1dc305b6794de3`.
- Candidate grouping/ranking scenario now directly exercises `slskd_search.extract_candidates` in `tests/test_slskd_candidates.py`; no production implementation changed.
- All four required workflows passed on exact head: syntax `38652066842`, Docker packaging/full unit suite `38652066649`, runtime smoke `38652066755`, and Docker image validation with publishing paused `38652066683`.
- Next priority: inspect the remaining acquisition coordinator and AST tests for a small safe extraction seam. Preserve end-to-end query sequencing, shared-lock races, persistence transitions, cancellation outcomes, dismissal/reactivation, and watcher recovery. Do not split coordination state just to remove AST coupling.

---

## 2026-10-14 — PR #72 merged: pure slskd search helper test migration

- PR #72 squash-merged at `6c6157a8238691b18d2209ea2d2e1306385ec9a2` from tested head `17be72e52b39e63cad63391fb2c4e63ea55d3c26`.
- Moved six pure query/payload/path matching/diagnostic cases to `tests/test_slskd_search.py`; retained acquisition retry/wait and candidate extraction coverage in the AST harness at that point.
- All four required workflows passed on the exact tested head: syntax `38651547240`, Docker packaging/full unit suite `38651547229`, runtime smoke `38651547283`, and Docker image validation with publishing paused `38651547264`.
- No publication, deployment, or production runtime verification is claimed.

---

## 2026-10-14 — Candidate-start validation extraction (PR #71 merged)

- Extracted candidate-start path/state validation to `acquisition_candidate_start.py` with injected external boundaries; the server compatibility adapter remains in place.
- Moved traversal and mixed-directory tests to direct imports; added active-transfer, queued cancellation, and fail-closed uncertainty tests.
- PR #71 was squash-merged at `b10650aa6a8889610b5734c5a1cf02c3197f1ad0` from tested head `f53e8ceffc8307c7b8dbcbf837e123b51671bbda`.
- All four required workflows passed on that exact head (syntax, packaging/full unit suite, runtime smoke, and Docker image validation with publishing paused). No standalone local or live slskd tests, publication, deployment, or production runtime verification is claimed.
- Remaining AST-coupled coordination tests stay in place until equivalent direct-import coverage tests the same races and persistence/transition boundaries.

- Extracted slskd candidate-start path/state checks into `acquisition_candidate_start.py` with injected transfer lookup, HTTP, and timing dependencies. The server keeps its existing helper name as an adapter.
- Moved the two AST path-validation tests to direct-import coverage; added tests for active transfers and conservative handling of queued-transfer cancellation outcomes.
- No change intended to safety semantics. Review exact diff and require focused tests, full suite, syntax checks, and all four CI workflows on exact PR head before merge.
- Remaining AST-coupled coordination tests are intentionally retained where they still exercise races or persistence/transition boundaries.

---

## 2026-10-14 — Completed import safety tests migrated to direct imports (PR #70 merged)

- Removed the redundant `CompletedAlbumMatchingTests` cases from the AST-based `tests/test_acquisition_safety.py` harness. Equivalent or stronger coverage already exercises the production modules directly in `tests/test_acquisition_completion.py` and `tests/test_acquisition_import.py`.
- The direct-import suites cover strict positive-size matching, Unicode/case and Windows path normalization, duplicate-basename ambiguity, symlink refusal, collision-suffix matching, exact folder diagnostics, unrelated-file preservation, destination no-overwrite, storage identity mismatch, reserved manifest rejection, and rollback after a partial move.
- The AST harness retains its separate lifecycle coordination tests. Its injected import callback is now a test spy for transition behavior; filesystem import behavior is tested against `acquisition_import.import_matched_album_files` directly.
- Test-only migration: no production code, queue/cleanup behavior, path validation, rollback implementation, or MCP compatibility changed.
- PR #70 was squash-merged at `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161` after all four required CI workflows passed on exact tested head `0916a7e9d767808bf4f65d3b034e290e5aba4703`. No standalone local test commands or manual browser tests were run for this test-only migration; no image publication, deployment, or production runtime verification is claimed.
- Next: audit remaining AST-coupled acquisition safety cases for duplicate coverage; preserve dismissal/import coordination, conditional state transitions, cleanup refusal, uncertain queue outcomes, and rollback protections.

---

## 2026-10-14 — Queue failure classification test migration in progress

- Branch `test/migrate-queue-failure-classification` removes two AST-harness cases for `_slskd_queue_failure_action`; its production adapter is a thin delegation to `acquisition_lifecycle.queue_failure_action`.
- Existing direct-import coverage in `tests/test_acquisition_lifecycle.py` covers retryable 400/404/422 responses, fatal 401/403 responses, uncertain HTTP statuses including 503, and transport errors. No production code or safety semantics change.
- Exact-head test and CI verification are pending. Continue with the next AST-coupled case only after reviewing the test diff and confirming direct coverage exercises the actual extracted implementation.

## 2026-10-14 — Queue dismissal regression migrated (PR #64)

- PR #64 merged at `1596161aa525896d43c37c85533e8056a742439b` from tested head `3bde365e43acbe1cc95f68d7014d899046e735f6`.
- The redundant AST-harness queue-dismissal case, adapter shim, and unused HTTP helper were removed. Direct-import coverage against `acquisition_orchestration.queue_candidate_unless_dismissed` preserves the safety assertion and tests critical-section ordering, return propagation, and exceptions.
- All four required CI workflows passed on the exact tested head; publishing remains paused. Continue with the next AST-coupled case only where direct-import coverage is equivalent or stronger.

## 2026-10-14 — Acquisition safety test migration follow-up

- After PR #62, removed one redundant AST-harness queue-dismissal case and its shim; equivalent dismissal-refusal coverage remains in direct-import tests against `acquisition_orchestration.queue_candidate_unless_dismissed`.
- This is a test-only migration step. Continue with the next AST-coupled case only when it can be moved to a direct-import test without reducing safety coverage.

## 2026-10-14 — Queue/dismissal guard extraction merged (PR #62)

- PR #62: https://github.com/abucalip/navi-librarian/pull/62
- Branch: `refactor/acquisition-queue-guard`; exact tested head `4e121eb7977bb1a51ad31f9c87d0d4984497af4d`.
- Squash merge commit: `d4a16e80f6978a58c3305bf341e370ba9708bb34`.
- Reviewed the focused eight-file diff. Extracted `queue_candidate_unless_dismissed` into `acquisition_orchestration.py`; preserved the server compatibility adapter, HTTP request construction, shared transition lock, and dismissal predicate. Added direct-import regressions for lock scope, dismissal refusal, return propagation, and exceptions; retained the AST-based safety regression.
- All four required workflows passed on the exact tested PR head: Python syntax `38619152587`, Docker packaging/full unit suite/build `38619152213`, container runtime smoke `38619152754`, and validation-only multi-architecture image `38619152728`. Image publishing remains paused.
- No local helper/manual slskd test, production filesystem operation, image publication, deployment, or production runtime verification is claimed.
- Next: continue the acquisition-coordination audit and migrate remaining AST-coupled safety tests incrementally; keep correctness and verification ahead of routine modularization.

## 2026-10-14 — Acquisition transition guard merged (PR #61)

- The dismissal-serialized source-switch guard is now extracted into `acquisition_orchestration.py`; the server function remains a compatibility adapter.
- PR #61 exact head `aa554ff2be2a19e215538ed2e699b8036764dca1` passed all four required workflows: syntax/acquisition safety `38617537652`, Docker packaging/full suite/build `38617538490`, container runtime smoke `38617537978`, and validation-only multi-architecture build `38617538229`. Squash merge: `73172847535d3683facfbe559706c26a8637a3d4`.
- Publishing remains paused. CI does not establish live slskd behavior, production filesystem safety, deployment, or production runtime health.
- Continue acquisition-coordination audit and migrate remaining AST-coupled safety tests to direct-import tests without reducing coverage.

# Roadmap reconciliation — authoritative status as of 2026-10-14

This section supersedes any older “in progress”, “next”, or “pending” statements later in this document when they conflict with the merged-state summary below. Historical entries are retained as a record of what was true at the time they were written.

## Verified current state

- PR #57 (watcher loop) is merged to `main` at `ae1e8b8f582c0ca0b882566d883d9a68bb2ca589`.
- PR #58 (watcher startup/reservation) is merged to `main` at `066fff8e7ef88364b1dc9cc909bfb2722118880e` as recorded by the latest repository history. Its exact tested PR head was `3f072159ef9e61f70554d315277a612005b8de4e`; all four required workflows passed on that head.
- PR #59 (acquisition-state SQLite save/list persistence) is merged to `main` at `730ae16e613f3962c488f87c8de54034db7463dd`. All four required workflows passed on exact tested head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d`.
- The latest recorded main documentation commits include `99da8ef0a9d4346b065092d6ea95002c7457bd4f`. Open PRs #44 and #45 concern the deferred dismissal HTTP 409 diagnostic/decision; PR #23 is older roadmap documentation. They are not evidence that PRs #57–#59 remain unmerged.
- No local helper test, live slskd interaction, production filesystem action, image publication, deployment, or production runtime verification is claimed for PRs #57–#59. GHCR publication remains paused pending completion of the roadmap and explicit authorization.

## Remaining roadmap, in order

1. **Acquisition coordination and test migration.** The watcher loop, watcher startup, and SQLite save/list mechanics have been extracted, but top-level acquisition coordination and shared transition responsibilities still need a focused audit/extraction. PR #61 extracted the dismissal-serialized source-switch guard into the importable orchestration module with direct-import tests and was squash-merged after all four required workflows passed; the shared lock, queue logic, cleanup, and persistence were preserved. Preserve the shared transition lock, conditional state writes, dismissal/import coordination, uncertain queue outcomes, cleanup refusal, strict completion matching, filesystem identity checks, and rollback. Continue migrating AST-coupled tests to direct-import tests without reducing safety coverage.
2. **Settings/configuration/service boundaries.** Move persistent settings and Navidrome, slskd, Last.fm, and ListenBrainz service access behind independently importable interfaces. Preserve secret handling, defaults, validation, data-directory behavior, and errors.
3. **Discovery orchestration.** Connect existing recommendation, discovery-store, and refresh modules through service boundaries; extract remaining list construction, feedback, provider integration, and inventory access without duplicating domain behavior in FastAPI routes.
4. **Application assembly.** Remove the remaining `app/main.py` dependency on `navidrome_server.py` for settings/auth persistence, health checks, and dashboard discovery behavior; preserve middleware and public/protected route behavior.
5. **MCP retirement.** Only after web callers and tests no longer depend on the monolith, audit all imports, entry points, dependencies, tests, docs, and compatibility needs. Remove MCP registration/runtime dependencies only after every web-required behavior has a tested owner.

## Manual verification boundary

The local browser helper is required for UI-facing changes after automated CI succeeds on the exact tested SHA; backend-only modularization does not trigger the full browser checklist. The performance observation and distinct error/recovery exercise remain deferred to the next UI-facing change. The dismissal HTTP 409 investigation remains deferred until it recurs. Ordinary helper runs must keep slskd disabled and use sandbox paths; do not use real library/download folders for destructive browser checks.

---

## 2026-10-14 — PR #57 merged: acquisition watcher lifecycle

PR #57 was squash-merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. The watcher loop now lives in acquisition_watcher.py behind injected services, with the legacy MCP/web adapter preserved. Direct-import regression tests cover dismissal/recovery exits, completed transfer evidence without a verified folder (no import), and verified-path handoff to the existing safe import coordinator. Docker packaging is updated. All four required workflows passed on that exact head: syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, runtime smoke 38605511271, and validation-only multi-architecture 38605510906 (publishing paused). No separate local test run, live slskd test, production filesystem action, publication, deployment, or production runtime verification is claimed.

**Next priority:** persistent acquisition-state coordination after extracting watcher startup. Keep the strict completion matcher, safe import coordinator, cancellation/cleanup refusal behavior, and MCP compatibility unchanged.

# Modularization Roadmap

Last updated: 2026-10-14

## Historical record — acquisition state persistence extraction (now merged as PR #59)

`acquisition_state.py` owns the SQLite mechanics for saving and listing acquisition rows behind injected initialization, database path, identity-key, and clock dependencies. Legacy `_discovery_save_acquisition_job` and `_discovery_list_acquisition_jobs` remain compatibility adapters. The transition lock, conditional dismissed-state checks, secondary For Me feedback projection, dismissal/import coordination, and all filesystem safety operations remain in `navidrome_server.py`; this extraction must not be interpreted as moving those responsibilities. Direct-import tests cover round-trip persistence, normalized identity, preservation of candidate/settings/quality metadata on partial updates, invalid identity rejection, and malformed stored JSON. Initial CI on code head `2e7ef60177ff61cb080dfad9fa422773938159ef` caught a regression-fixture expectation mismatch (`json.loads('null')` returns `None`, matching the prior implementation); the fixture was corrected without changing production behavior. On corrected code head `29c5e6a460f1f61296680af7b1230fd5561496b4`, all four required workflows passed: compile `116019144533`, test/build `116019140196`, container smoke `116019141476`, and validation-only multi-architecture `116019141889` (publishing paused). At the time of this historical entry, documentation-updated-head verification was still required; PR #59 was subsequently verified and merged as recorded in the authoritative status section above.


## Priority override — acquisition lifecycle correctness and safety

PR #51 and PR #53 established refusal and neighbor-preservation coverage for destructive dismissal cleanup. PR #54 extracted cleanup to `acquisition_cleanup.py` with direct-import regression tests; exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows and merged at `982e39122a401b8b68d75e38423dbb93711b4abd`. PR #55 extracted interrupted-import recovery to `acquisition_recovery.py`; exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed all four workflows and merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`. PR #56 extracted source-switch orchestration to `acquisition_source_switch.py`; exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed all four workflows and merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`. All three retain the legacy MCP/web adapters and were added to Docker packaging. The next safety priority is to extract the watcher loop and top-level acquisition coordination with direct-import tests, while preserving cleanup refusal, mount identity, manifest/rollback, and uncertain-queue invariants. The reported HTTP 409 remains deferred because it was not reproduced. No live slskd or production-folder recovery/cleanup is claimed.

## Goal and guardrails

Reduce coupling in the Python application through small, behavior-preserving extractions. GitHub is the source of truth. Preserve the web API/UI, authentication, settings and persistent state, acquisition safety, and any existing caller until its replacement is verified. New extracted modules should have direct-import regression tests. Do not remove tests simply because their current AST-based setup is awkward.

The delivered product's target is web-only. MCP retirement is a later step: the web application still imports navidrome_server.py, so do not remove the legacy module/runtime until web callers have been redirected to importable domain/service modules and a repository-wide usage audit confirms MCP-only code can be removed safely.

## Completed domain extractions

- PR #24 — acquisition completion matching: acquisition_completion.py; direct tests for filename identity and completed-folder inspection.
- PR #25 — slskd search and quality: slskd_search.py and slskd_quality.py.
- PR #27 — acquisition import safety: acquisition_import.py, including path/storage guards, no-overwrite behavior and rollback.
- PR #28 — discovery recommendation rules: discovery_recommendations.py.
- PR #29 — discovery list persistence: discovery_store.py.
- PR #30 — discovery refresh coordination: discovery_refresh.py.

These extractions are merged to main. They do not mean the monolithic server or web module is fully modularized.

## Acquisition lifecycle extraction — in progress

PR #47 introduces `acquisition_lifecycle.py` as a dependency-light, directly importable owner for monitor-resume eligibility, conservative cleanup classification, skip-request validation, fallback queue payload normalization, and uncertain queue-error classification. Legacy MCP functions remain compatibility adapters and continue to own database/network/filesystem I/O.

This is the first lifecycle seam, not completion of the whole orchestration extraction. Cleanup, interrupted-import recovery, and source-switching now have directly importable implementations with compatibility adapters. The watcher loop, persistent state coordination, watcher startup, and top-level acquire coordinator still live in `navidrome_server.py`. Next, extract those paths behind injected service dependencies and migrate remaining AST-coupled tests incrementally. Keep the existing completion/import safety modules as the filesystem authorities.

## Current route-separation stage

1. Settings routes (merged in PR #33): move the Navidrome, Last.fm, ListenBrainz and slskd settings handlers to app/api/settings.py; preserve URLs, methods, payload defaults, error codes/messages and calls into existing domain functions. Keep parse_result importable from app.main while moving its implementation to app/api/utils.py.
2. Acquisition routes: extract /api/acquire* and /api/acquisitions* with safety and streaming tests. Keep destructive logic in domain services. **PR #34 (`refactor/acquisition-api-router`):** merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`. Syntax, Docker packaging/full unit tests, runtime smoke, and validation-only multi-architecture checks all passed on that exact head.
3. Discovery routes: **PR #35 merged** at `d61162b29c6f0cccc97aefe9c779567e671651b2` from exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`. Extracted recommendations, discovery-list retrieval, refresh, and feedback handlers into `app/api/discovery.py`; direct-import regression coverage is in `tests/test_discovery_routes.py`. All four required workflows passed on that exact head. Preserve ownership filtering and refresh/feedback semantics.
4. Metadata routes/services: **PR #36 merged** at `15011614649470c9c71734422b95ee048fbf9f3c` from exact head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`. Artist bio, artwork, album details/year, and external HTTP/cache helpers now live in `app/api/metadata.py`; regression coverage is in `tests/test_metadata_routes.py` and `tests/test_artwork_retry.py`. All four required workflows passed on the corrected exact head.
5. Authentication and app assembly: only split auth after explicit dependencies for persistent settings, session signing and middleware have been identified and covered. Keep middleware/public-path behavior unchanged. **PR #37 merged** at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3` from exact head `192b084850ecbe0137b64b3dae9d07e0471198b4`. Security primitives (persistent signing secret, username/password validation, PBKDF2 digest, signed-session generation/validation) now live in `app/security/auth.py`; routes, cookie setup, and middleware remain in `app/main.py`. All four required workflows passed on the exact head. PR #38 merged at `84da7ebfe51199a5caf63f7689fe89df8d61b553` after all four exact-head workflows passed; its new `tests/test_auth_routes_integration.py` covers setup, login/logout, rate limiting, cookie policy, session reuse/tampering, and public/protected paths. PR #39 (`refactor/auth-api-router`) was squash-merged at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact head `9187a51380d2a7ed7d27276ce4505827becaed32`. It extracts status/setup/login/logout and the login page into `app/api/auth.py`; middleware and signing helpers remain in `app/main.py` and `app/security/auth.py`. All four required workflows passed on the exact final head: syntax (`38492677728`), Docker packaging/full suite (`38492677704`), runtime smoke (`38492677708`), and validation-only multi-architecture (`38492677825`).
6. Frontend assets: **completed in PR #41**, squash-merged to `main` at `410506ea76d7181aa300edb9c05ebbd337dd7159` from exact tested head `b94dde68cccef776cea3813dbe7310eb857d170b`. Login/main HTML is in `app/templates/`; CSS/JavaScript is in `static/`; Docker packaging and auth middleware public-asset rules are updated, with regression coverage for asset delivery and external references. All four required exact-head workflows passed, and the manual report recorded eight checklist items passing. User reports navigation is noticeably snappier and no errors occurred. A distinct deliberately induced error/recovery scenario was not reported and is not claimed. See `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md` for the verification boundary.
7. MCP retirement: audit all imports, entry points, dependencies, tests and docs. Remove MCP registration and MCP-only runtime/dependencies only after the web app no longer relies on navidrome_server.py as its domain API. Keep compatibility wrappers until every consumer is migrated.

## Remaining `navidrome_server.py` dependencies — audit 2026-10-14

The current web application still imports the monolith as its domain API. Treat this as the dependency inventory and sequence for remaining work; re-check current `main` and callers before implementation.

### Direct web callers

- `app/main.py`: imports `navidrome_server as librarian`; uses `DATA_DIR`, settings read/write, `api_call` for health, discovery-list retrieval, and album-candidate filtering for dashboard picks.
- `app/api/settings.py`: delegates Navidrome, Last.fm, ListenBrainz, and slskd settings reads/writes and connection tests to legacy functions.
- `app/api/discovery.py`: delegates recommendation generation, discovery-list retrieval/refresh, feedback, and album eligibility.
- `app/api/acquisitions.py`: delegates acquisition status, source skipping, dismissal, album acquisition, and slskd candidate queueing.
- `app/api/metadata.py` no longer imports the monolith; its route/provider helpers are extracted.

### Hidden runtime and test coupling

- Importing `navidrome_server.py` also imports/instantiates `MCPServer` and registers MCP tools. Therefore the FastAPI runtime pulls in MCP code despite the web Docker entry point running Uvicorn.
- The web Dockerfile copies `navidrome_server.py`; `requirements.txt` includes the MCP package. `server.py` is another MCP-related entry point and must be checked before any repository-wide claim that MCP is unused.
- `tests/test_acquisition_safety.py` uses AST parsing to extract named functions from `navidrome_server.py`, remove decorators, and execute them in a stub namespace. This makes tests sensitive to function location and names. Replace this coverage incrementally with direct-import tests of extracted implementations; preserve lifecycle, cleanup, path-validation, no-overwrite, rollback, and unsafe-failure cases.

### Recommended implementation order

1. **Acquisition lifecycle/orchestration and test migration.** Extract state transitions, persistence coordination, candidate/source selection, queue/skip/dismiss/failover, completed-import coordination, and recovery behind importable domain interfaces. Keep destructive operations fail-safe and preserve existing callers with adapters until verified.
2. **Settings, configuration, and service access.** Separate persistent settings operations and Navidrome/slskd/Last.fm/ListenBrainz integration from MCP registration. Preserve secret handling, data-directory behavior, defaults, validation, and errors.
3. **Discovery orchestration.** Connect existing recommendation, store, and refresh modules through service interfaces; extract remaining list construction, feedback, provider integration, and inventory access without duplicating domain logic in routes.
4. **Application assembly.** Remove `app/main.py`'s remaining dependency on the monolith for settings/auth persistence, health checks, and dashboard discovery behavior. Keep middleware and public/protected route behavior unchanged.
5. **MCP retirement.** Only after web callers and tests no longer depend on the monolith, audit all imports, entry points, dependencies, tests, docs, and compatibility needs. Remove MCP registration/runtime dependencies only when each web-required behavior has an independent tested owner.

### Acceptance gates for each extraction

- Direct-import regression tests exercise the extracted implementation; no parallel copy of domain behavior in the web layer.
- Preserve MCP compatibility until the separately verified retirement step.
- For acquisition changes, cover both successful behavior and unsafe failure cases, including traversal/symlink escape, ambiguous targets, unrelated files, cleanup refusals, import rollback, and interrupted lifecycle recovery where applicable.
- Run focused tests, `python -m unittest discover -s tests -v`, syntax checks, and applicable Docker/API/runtime checks. Verify all required CI on the exact final PR-head SHA.
- Review all changed callers and the complete diff. Update this roadmap, project status/log, and test/architecture docs with actual evidence; never infer test success from compilation or a successful container start.

## Testing and release gates

For each route extraction:
- Add direct-import tests for payload adaptation, status codes, sanitized failures and compatibility defaults.
- Run focused tests, full python -m unittest discover -s tests -v, syntax checks, and Docker build/runtime CI.
- Review the complete diff and verify CI on the exact final PR head.
- UI-affecting changes require manual browser testing after automated CI succeeds.

Docker runtime smoke and multi-architecture build validation remain enabled. GHCR publication is intentionally disabled until the modularization roadmap is complete and the user explicitly authorizes release. Validation/build success does not mean an image was published or deployed.

## Current status

Domain extractions through PR #30 and route/frontend stages through PR #41 are merged as recorded above. Acquisition safety/orchestration has since advanced through merged PRs #47, #50, and #54–#56. PR #54 extracted safe dismissal cleanup, PR #55 extracted interrupted-import recovery, and PR #56 extracted source-switch orchestration; each exact PR head passed all four required workflows and each final diff was reviewed before merge. The watcher loop, watcher startup, and SQLite save/list persistence have since been extracted in PRs #57–#59. Remaining top-level/shared acquisition coordination is still outstanding. The next implementation priority is to extract those lifecycle paths behind injected dependencies with direct-import regression tests, preserving cancellation/cleanup refusal, uncertain queue outcomes, import rollback and filesystem identity checks, persistent state transitions, and MCP compatibility. Then continue with settings/service boundaries, discovery orchestration, application assembly, and only then assess MCP retirement. GHCR publication remains disabled until the roadmap is complete and release is explicitly authorized. No local test run, live slskd interaction, production filesystem recovery/cleanup, publication, deployment, or production runtime verification is claimed for PRs #54–#56.


## Stage 7 — FastAPI route separation: settings routes

PR #33 extracts settings handlers to app/api/settings.py and the shared response adapter to app/api/utils.py. The app.main.parse_result symbol remains available as an imported compatibility name. Regression coverage in tests/test_settings_routes.py checks all 12 endpoint/method pairs, payload mapping, defaults, validation failures, and sanitized errors. Remaining route groups and later MCP retirement stay separate roadmap items; do not remove the legacy server until callers and compatibility are verified.


## 2026-10-14 — Acquisition lifecycle/orchestration dependency status

- PR #47's lifecycle policy extraction is merged at `1877dca3187f7cbde85b211d5414e558f12da502`.
- PR #48's orchestration extraction remains pending. Its current branch/head `refactor/acquisition-lifecycle-orchestration` / `115e1f9373744d361a20f0ba20c35589db0ca099` retains the pre-squash PR #47 history; the diff against current `main` includes both lifecycle and orchestration changes, and GitHub reports it is not mergeable.
- The four required workflows passed on that existing head only; do not carry that CI claim over to a reconstructed branch. No merge of PR #48, publication, deployment, or runtime verification is claimed.
- **Required next step:** reconstruct PR #48 as an orchestration-only change based on current `main`; inspect all callers, direct regression tests, Docker packaging, MCP compatibility, and filesystem safety behavior; then verify all required workflows on the exact new head before merge.


## 2026-10-14 — Reconstructed acquisition orchestration slice

PR #49 has been merged to `main` at `c972278566d8ec68f3755f464df1afb5a8a18f56`. PR #48's original branch still contains pre-squash history and is not the source for a direct merge. The reconstructed branch `refactor/acquisition-orchestration-reconstructed` starts from updated `main` and carries only the persisted source-skip orchestration seam, its direct regression tests, Docker packaging, and focused documentation. Keep the MCP adapter, shared transition lock, conditional downloading-state update, and existing filesystem safety modules unchanged. All four required workflows passed on final PR #50 head `9185f3c12ace7c82a61ff04c062044ab9c33cdf6` (syntax `38587910860`, Docker packaging/full unit suite `38587910842`, runtime smoke `38587911440`, multi-architecture validation `38587911187`). The reconstructed diff is ready for merge review; no reviewer submissions or inline threads were present at the time of inspection. PR #50 remains unmerged.


## 2026-10-14 — Persisted acquisition source-skip orchestration merged (PR #50)

PR #50 was squash-merged at `a37d29cf11657dce6d5cbc6cb928ca840fe5b206` from exact PR head `c8610fdc44ea93bcfb55a654598792aee78e7ecb`. All four required workflows passed on that exact head: Python syntax `38589006636`, Docker packaging/full unit suite `38589006609`, container runtime smoke `38589006569`, and validation-only multi-architecture image validation `38589006620`. The extracted module owns only the persisted manual source-skip transition; the MCP adapter, shared transition lock, conditional downloading-state update, and existing filesystem safety authorities remain. Watcher orchestration, source switching, cleanup execution, interrupted-import recovery, and top-level acquisition coordination remain future work. No image publication, deployment, or production runtime verification occurred.


## 2026-10-14 — Watcher extraction merged (PR #57)

PR #57 was squash-merged at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. The watcher loop now lives in acquisition_watcher.py behind injected services, with the legacy adapter preserved. All four required workflows passed on the exact head. See the merge closeout below for run IDs and verification boundaries.


## Acquisition watcher startup extraction — PR #58

- PR: https://github.com/abucalip/navi-librarian/pull/58; branch `refactor/acquisition-watcher-startup`; tested head `3f072159ef9e61f70554d315277a612005b8de4e`.
- Extracted reserve → persist → status → start into `acquisition_watcher_startup.py` with injected locks, active set, persistence/status callbacks, and watcher entry point. `navidrome_server.py` retains `_discovery_start_import_watcher` as a compatibility adapter with its existing return contract.
- Direct-import regressions cover dismissed/duplicate starts, credential filtering in persisted settings, persistence failure releasing the reservation, and thread-start failure recording `monitor_error` and releasing the active marker. Docker packaging and architecture documentation are updated.
- All four required workflows passed on the exact head: syntax/acquisition safety `38609940832`, Docker packaging/full unit suite/build `38609940860`, container runtime smoke `38609940739`, and validation-only multi-architecture build `38609940737` (publishing paused).
- State: implementation and CI passed; PR #58 was subsequently merged to main at `066fff8e7ef88364b1dc9cc909bfb2722118880e`. No separate local test run, live slskd test, publication, deployment, or production runtime verification is claimed.
- Next priority: persistent acquisition-state coordination with direct-import regression coverage, preserving conditional writes, shared transition-lock behavior, and dismissal/import safety.


### Acquisition state persistence — PR #59 merged

- Extracted SQLite save/list mechanics into `acquisition_state.py`; legacy server wrappers remain compatible.
- Exact PR head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed compile, full test/build, container smoke, and validation-only multi-architecture workflows (`116019930318`, `116019925188`, `116019924747`, `116019926066`); squash merge `730ae16e613f3962c488f87c8de54034db7463dd`.
- The next task must be selected after reviewing the live open-PR list and current roadmap. Do not assume watcher-startup PR #58 is merged; confirm its current status and exact-head checks.


## Front-end quality follow-up — PR #66 merged (2026-10-14)

- Login-page alignment is complete: `static/login.css` now shares the app's design tokens, type system, primary-control treatment, and focus-visible styles. PR #66 merged at `717b1ad08e5de54e2dd8c11c2734976d75ce2e5f` from tested head `d0b13b7411b9b300b78b24a8944348b7e57d4b65`.
- Exact-head syntax, Docker packaging/full suite, runtime smoke, and validation-only multi-architecture CI all passed. Manual screenshots/report are published on the PR; keyboard-focus modality and first-run setup variant remain explicitly skipped in that report.
- This visual improvement does not change the backend modularization priority or authorize image publication/deployment. Continue the safety-first acquisition coordination/test migration roadmap.

## 2026-10-15 — Settings router is the next injection seam

After discovery-router injection (PR #108), the next narrow step is to inject the existing service into all settings routes through `get_librarian`. Keep settings policy, SQLite persistence, runtime path mutation, and network connection checks in the existing service module; do not duplicate or relocate domain behavior. Verify endpoint paths/methods, payload/default mapping, validation and sanitized error contracts, plus all four required CI workflows on the exact PR head. `app/main.py` still imports the legacy server and remains a separate follow-up boundary.


## 2026-10-15 — PR #109 merged: settings router service injection

- PR #109: https://github.com/abucalip/navi-librarian/pull/109; exact tested head `a6c919a4d6c45f98394ee683095888f27513f1d6`; squash merge / current main at closeout `9a2aaea98cff38a1ad3da130d0958f945bec9673`.
- The settings router now uses the shared lazy `get_librarian` dependency for all twelve endpoints. Route/method contracts, service calls, payload mapping, quality defaults, optional path trimming, validation responses, and sanitized connection errors are preserved.
- All four required workflows passed on the exact final PR head: Python syntax `38734569394`, Docker packaging/full suite `38734569197`, container runtime smoke `38734569168`, and validation-only multi-architecture image validation `38734569302`. Image publishing remains paused.
- No separate local test run, publication, deployment, or production runtime verification is claimed.

## 2026-10-15 — Dashboard/health router injection in progress

- Following merged PR #109, `/api/health` and `/api/dashboard-picks` are the next small HTTP boundary in `app/main.py`. The branch moves both handlers into `app/api/dashboard.py` and injects `get_librarian`.
- Regression tests cover the endpoint/method inventory, injected Navidrome ping and sanitized failure, dashboard category balance, list-call arguments, deduplication, album-candidate filtering, and count validation.
- Read-only AST audit found the remaining lifecycle AST tests still verify the legacy `discovery_acquire_album` adapter wiring; keep them until equivalent direct coverage proves the adapter's lock/state/watcher dependency mapping.
- PR #109 merged at `9a2aaea98cff38a1ad3da130d0958f945bec9673` after all four required workflows passed on exact PR head `a6c919a4d6c45f98394ee683095888f27513f1d6`. Publishing remains paused.


## 2026-10-15 — PR #110 merged: dashboard and health router injection

- PR #110 squash-merged at `b4015b8619f3c0db169722c347f72612996b9a1c` from exact tested head `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e`.
- `app/api/dashboard.py` now owns `/api/health` and `/api/dashboard-picks`, using `get_librarian`; domain logic remains in the existing service. All four required exact-head workflows passed (syntax `38735208616`, package/full suite `38735208619`, runtime smoke `38735208830`, multi-architecture validation `38735208682`).
- The remaining acquisition lifecycle AST tests were retained because they verify the legacy MCP adapter's dependency wiring beyond the direct-import coordinator tests.
- **Next:** audit the remaining `app/main.py` direct `navidrome_server` dependency for auth settings reads/writes and `DATA_DIR`/secret initialization. Design a small testable injection seam that preserves setup/login/logout, cookie/session semantics, persistent settings ownership, and MCP compatibility. Do not retire MCP or move persistence without a separate evidence-based plan.



## 2026-10-15 — PR #112: lazy authentication service dependency verified

- Removed the direct `navidrome_server.py` import from `app/main.py`; auth settings and signing-key storage resolve through the shared lazy `get_librarian` dependency.
- Kept persistent settings, `DATA_DIR`, secret-file permissions, MCP adapters, auth route contracts, cookie/session semantics, and middleware behavior unchanged.
- Migrated auth integration tests to an injected fake service and added a subprocess regression proving importing `app.main` alone does not load `navidrome_server`.
- Exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed syntax `38737672741`, Docker packaging/full suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture validation `38737672689`. No publication/deployment. PR #112 merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. Next priority: continue the web dependency audit with the remaining `app/main.py` responsibilities and keep auth/persistence ownership intact.


## 2026-10-15 — PR #121 merged: reject ambiguous acquisition cleanup paths

- PR #121 merged to `main` at `8e53fe83c11db6592d4716e6b5002a360cf8b763` from exact tested PR head `cbba06ce919cab8bd97d939544f489ab8e859ae7`.
- `acquisition_cleanup.py` now rejects absolute paths, Windows drive-qualified paths, repeated separators, and explicit dot segments instead of silently normalizing malformed remote paths into a different source identity. Parent traversal remains rejected; ordinary relative paths using either slash style remain supported.
- Added direct-import regression cases proving malformed paths refuse cleanup before transfer lookup and leave local files untouched.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `38750890697`; Docker packaging/full unit suite/build `38750890576`; container runtime smoke `38750890609`; validation-only multi-architecture image validation `38750890533`. The full unit-test and build job passed; no separate local test run is claimed.
- No live slskd operation, production deletion test, image publication, deployment, or production runtime verification. This change does not diagnose or claim to fix the deferred acquisition-dismissal HTTP 409.


## 2026-10-15 — PR #122 merged: validate remote transfer source identity

- PR #122 merged at 3bb8a5154915d82cc8b831af7a1dacb4a9384864 from exact tested PR head 55a14c0f9c6c7dbe35e4b3deee4b33b9ffd9c28d.
- Acquisition cleanup now validates a transfer filename even when slskd supplies _transfer_directory. If both filename and directory identify a folder, they must agree; unsafe absolute and drive-qualified filenames are refused before cancellation. The same identity check runs during post-cancellation verification, while basename-only transfer filenames remain supported when an explicit directory is present.
- Direct-import regressions prove mismatched directory metadata, absolute paths, and Windows drive-qualified paths refuse cancellation and preserve local files.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety 38751732156; Docker packaging/full unit suite/build 38751732263; container runtime smoke 38751732282; validation-only multi-architecture image validation 38751732196. Publishing remained paused.
- No separate local test run, live slskd operation, production deletion test, image publication, deployment, or production runtime verification is claimed. This is not a diagnosis or fix for the deferred acquisition-dismissal HTTP 409.


## Next settings/domain boundary — connection-check service extraction (2026-10-15)

Extract the settings connection-check logic into `service_settings.py` behind injected HTTP/service dependencies. Keep SQLite persistence, settings migration, runtime path mutation, and the legacy MCP-facing function signatures in `navidrome_server.py`. Verify secret redaction and preserve the existing JSON result contract before continuing to the remaining application assembly/domain dependencies.


## Completed — settings connection checks (2026-10-15, PR #140)

Navidrome, Last.fm, and ListenBrainz connection-check logic is extracted into `service_settings.py` with injected dependencies; legacy public entry points remain adapters. Regression tests cover response mapping, missing configuration/profile, and Last.fm key redaction. All four required workflows passed on PR head `cacdbc809f35040f0cc1bc70a39251ff80b7315e`; merged as `aabd7d1347d8e4c363d8b97bb6c106310f1135bb`. Continue with the remaining application-assembly/domain-service boundaries; do not treat this as completion of all modularization.


## 2026-10-15 — Data-directory resolution extraction in progress

The next small application-assembly seam is pure resolution of `NAVIDROME_LIBRARIAN_DATA_DIR` versus the source-directory fallback. `data_directory.py` resolves the path without creating it; `navidrome_server.py` retains the legacy `DATA_DIR` symbol and the existing `mkdir` side effect, so data persistence and permissions remain owned by the existing service. Direct-import tests cover explicit path expansion, empty configuration, and fallback behavior. Docker packaging is updated. Verify the focused tests, full suite, syntax, and all four required workflows on the exact final PR head before merge. Publishing remains paused.


## Completed — data-directory resolution (PR #152, 2026-10-15)

Extracted the pure `NAVIDROME_LIBRARIAN_DATA_DIR` / source-directory fallback resolver to `data_directory.py`. The legacy `navidrome_server.DATA_DIR` and directory-creation behavior remain intact. Three direct-import regression tests and Docker packaging were added. All four required workflows passed on exact PR head `756ef13f6946299e2eacccbf5f9a55ebaf092aae`; merged by squash as `567409bb90f240667575a3730976e4c52676bc02`. Publishing remains paused; no deployment or production runtime verification is claimed.


## Subsonic response collection normalization — implementation in progress

Move the small shared response-normalization rule into `navidrome_client.items()`, keeping `navidrome_server.items()` as a compatibility adapter for existing discovery and MCP callers. Direct-import tests cover missing, scalar, empty, and populated collection values. This is a deliberately narrow step after the API transport extraction; preserve response semantics and run all four required workflows on the exact final PR head before merge. Publishing and deployment remain separate.


## Subsonic response collection normalization — completed (PR #153 merged, 2026-10-15)

Moved the shared response-normalization rule into `navidrome_client.items()` and retained `navidrome_server.items()` as the compatibility adapter. Direct-import tests cover missing, scalar, empty, and populated collection values. All four required workflows passed on exact PR head `c834383b7484f3c149679d62812f1c81f6133625`; squash merge commit `b7d8ec989e2a3d398b2ca4d14a30c59ae60543cc`. Publishing and deployment remain separate and are not claimed.


## Completed — Last.fm artist genre parsing (PR #174, 2026-10-16)

`LastFmClient.artist_genres()` now owns cached `artist.getTopTags` retrieval, normalization, case-insensitive deduplication, and the existing eight-tag limit. `navidrome_server._lastfm_artist_genres()` remains the compatibility adapter. Exact tested head `08c260e2a166a744bbde4009196b53d238afb647`; squash merge `4dd8b926a7a6cf76e248420860d7c29c892da3c0`. All four required exact-head workflows passed. No publication, deployment, or production runtime verification claimed.

## Completed — Last.fm top albums (PR #175, 2026-10-16)

`LastFmClient.artist_top_albums()` now owns cached `artist.getTopAlbums` retrieval and response normalization. `navidrome_server._lastfm_top_albums()` remains the compatibility adapter and retains discovery-specific album eligibility filtering. Direct-import regressions cover scalar/list payloads, empty titles, normalized metadata, request parameters and limit, timeout/cache TTL, cache hits/missing payloads, and adapter filtering. Exact tested head `6b5e32b1144e9f3517247110ea4383b287ce33f4`; squash merge `f922631e0393063bde02b1e0bd93d30b2d38bd2a`. All four required exact-head workflows passed. Publishing remains paused; no deployment or production runtime verification claimed.

## Next step

Refresh current GitHub main, inspect open PRs and the current requirements/test plan, then select the next smallest safe extraction from the remaining application-assembly/domain-service seams. Keep the acquisition dismissal HTTP 409 investigation deferred unless it recurs or the user explicitly reopens it.


## 2026-10-16 — Reviewed candidate normalization extracted (PR #195)

Moved reviewed slskd file-record and quality-summary normalization into `acquisition_candidate_queue.py`, with direct-import regression tests. The compatibility adapter still owns network queueing and watcher startup. Exact tested head `f60d682b2ebcd94ecfbcfd0b4beb77c628643fc5`; squash merge `5629d259468a0f748fb5d3fdb78819a0fb00d73c`. All four required exact-head workflows passed. No acquisition cleanup or dismissal behavior changed.

## 2026-10-16 — MusicBrainz album-year lookup extracted (PR #193)

Moved exact release-year lookup and matching into `musicbrainz_album_year.py`; the metadata route retains its compatibility adapter and endpoint contract. Exact tested head `2b426587e6cb4dc011c85099021041d9f9450744`; squash merge `bce1e32b4ca4c2df86f51dd6102931ed8299dcfe`. All four required exact-head workflows passed. Publishing/deployment remain paused.

## Next step

Refresh GitHub main, open PRs, and CI. Continue the remaining acquisition lifecycle/orchestration modularization; keep acquisition-dismissal HTTP 409 deferred as directed.


## 2026-10-16 — Acquisition progress snapshot extraction completed (PR #199)

Merged at a18889b7aa45dd8ef0a9e99a12236cedf5ed5a41 from tested head f7157cb28d5e753a97bb9c24eea209b767d74066. The process-local map and lock used to estimate slskd transfer speed now live in acquisition_progress_snapshots.py. The service retains polling, identity construction, monotonic clock selection, and the existing estimator. Direct-import tests cover initial/previous snapshots, key isolation, and exception behavior; all four required workflows passed on the exact head. Publishing and deployment remain paused.


## 2026-10-16 — Acquisition search diagnostics extraction completed (PR #200)

Merged at 9b3cf481a46282d2f980709091d57aea36144029 from exact tested head b74f6a3f4f8290d6e8d7123399185e9692dd053c. Pure shaping for candidate diagnostics, audio-file counts, and the user-facing empty-search message is isolated in acquisition_search_diagnostics.py. Search execution, persistence, path-match diagnostics, and API serialization remain in the server adapter. All four required exact-head workflows passed (syntax 1099, full suite/build 1006, runtime smoke 815, validation-only multi-architecture 859). Publishing and deployment remain paused.


## 2026-10-16 — Independent extraction session closeout: PRs #199 and #200

- PR #199 extracted thread-safe acquisition progress snapshots; exact tested head f7157cb28d5e753a97bb9c24eea209b767d74066 passed all four required workflows and merged as a18889b7aa45dd8ef0a9e99a12236cedf5ed5a41.
- PR #200 extracted slskd search diagnostic shaping; after correcting the AST-test import seam, exact tested head b74f6a3f4f8290d6e8d7123399185e9692dd053c passed all four required workflows and merged as 9b3cf481a46282d2f980709091d57aea36144029.
- Both are backend-only. No local test run, live slskd operation, publication, deployment, or production runtime verification is claimed. Acquisition-dismissal HTTP 409 remains deferred.


## 2026-10-16 — PR #213 merged: Deezer album-matching policy

- Extracted catalog-name normalization, exact artist+album matching, release-year validation, and artwork relevance scoring from `app/api/metadata.py` into pure `app/services/deezer_album_matching.py`.
- The metadata router retains HTTP validation, provider requests, cache behavior, response shapes, tracklist retrieval, and transient-provider failure handling. Docker already packages the helper through `COPY app/ ./app/`.
- Added direct-import regressions for punctuation/case normalization, exact two-field identity, empty names, plausible release years, and unchanged artwork score weights. Existing metadata-route regressions remain.
- PR #213 final tested head: `8760f068b9ab0e28f8a578d1b39bf326010d6fbb`. All four required workflows passed on that exact head: Python syntax run 1131, Docker packaging/full unit suite/build run 1038, container runtime smoke run 847, and validation-only multi-architecture image validation run 891 (`push: false)).
- Squash merge: `c8d82c227ca7bac22feaf03e0f61b12bbe3ae88e`. Assistant-side local tests were not run independently. No image publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — PR #214 merged: Deezer tracklist shaping

- Extracted pure track-row-to-response shaping into `app/services/deezer_tracklist.py`; `app/api/metadata.py` retains provider I/O, matching, response assembly, and error handling.
- Direct-import tests cover track numbering/fallback, title trimming/filtering, missing durations, and invalid numeric conversion.
- Exact tested head `59c8d13ba57930400675e4f9ff90ccba919b63aa`; all four workflows passed: Python syntax run 1144, Docker packaging/full suite/build run 1051, container runtime smoke run 860, and validation-only multi-architecture validation run 904.
- Merged at `51c4e03ac3a65cd74a25c6aced897bfa4d74a989`. No publication or deployment.

## 2026-10-16 — PR #215 merged: Discover recommendations control hierarchy

- Front-end-only layout change separates recommendation request inputs from result-refinement controls without changing JavaScript behavior or API contracts.
- Exact tested head `e8d2e2d462092dcf8cc92beffaa33181aa6758bc`; all four required workflows passed: syntax run 1143, Docker packaging/full suite/build run 1050, container runtime smoke run 859, validation-only multi-architecture validation run 903.
- The operator completed the manual browser checklist and published the report before merge. Merge commit `7317a006e495099fbb733d8d73e425396ec1eaa4`. No publication or deployment.

## 2026-10-16 — PR #216 merged: Deezer artwork selection

- Extracted pure album-artwork relevance selection/payload shaping and exact-artist photo fallback shaping into `app/services/deezer_artwork.py`. `app/api/metadata.py` retains request sequencing, cache ownership, provider-failure/retry behavior, and HTTP validation.
- Added direct-import tests for relevance threshold, best candidate, resolution preference, HTTPS normalization, release-year handling, exact artist identity, missing photos, and empty results; route regressions cover album selection and artist-photo fallback.
- Exact final tested head `aa1099e8ed43b9afcce483a50be31226a66218f4`; all four workflows passed: Python syntax run 1148, Docker packaging/full suite/build run 1055, container runtime smoke run 864, and validation-only multi-architecture image validation run 908. Assistant-side local tests were not run.
- Squash merge commit `ad61b1b91a5c351a73c02e37d7639bc47c61a52f`. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — PR #217 merged: Deezer matched album payload shaping

- Extracted the pure projection of a matched Deezer album row into `app/services/deezer_album_details.py`. The metadata route retains provider requests, exact matching, tracklist retrieval, error handling, and endpoint response assembly.
- Direct-import tests cover cover-size preference, HTTP-to-HTTPS normalization, release-year parsing, and missing fields; the route regression asserts the existing artwork field.
- Exact final tested head `b631f4c6367c68357cbd91f75b986770edfeee0e`; all four workflows passed: Python syntax run 1151, Docker packaging/full suite/build run 1058, container runtime smoke run 867, and validation-only multi-architecture image validation run 911. Assistant-side local tests were not run.
- Squash merge commit `37f04d0a863f69f5596f6a46406cc8bd64bde039`. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — PR #218 merged: exact Deezer release-year selection

- Extracted the pure rule that returns the first plausible year among exact artist+album matches into `exact_album_release_year()` in `app/services/deezer_album_matching.py`. Provider requests and the `MusicBrainz`-first response contract remain in the metadata route.
- Direct-import regressions cover skipping non-exact/invalid-year results and preserving result order; a route-level regression covers the Deezer fallback source/year contract.
- Exact final tested head `0293e4fe4eab7dd66dc82280720183dab3b913ed`; all four workflows passed: Python syntax run 1153, Docker packaging/full suite/build run 1060, container runtime smoke run 869, and validation-only multi-architecture image validation run 913. Assistant-side local tests were not run.
- Squash merge commit `6dc6adae89169638da9a158c79ccee5d2e1ddfb7`. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — Personal recommendation allocation boundary probe

- Added `docs/PERSONAL_RECOMMENDATION_ALLOCATION_CONTRACT.md` and immutable data-contract types in `discovery_allocation_contract.py`, with direct-import contract tests.
- The proposed interface supplies prepared candidate values, explicit ownership status, policy targets, and count limits; returns candidate IDs, review IDs, decisions, counts, and checked count. It requires no callbacks or shared mutable state.
- **Do not move the shortlist-selection loops in this change.** Current `consider()` mixes selection policy with candidate identity tracking, ownership lookup, manual-review payload creation, response shaping, and diagnostics. The contract tests only validate the interface invariants, not allocator semantics. Proceed to a separate extraction only after this contract is tested and the implementation can remain pure; refine/stop if that cannot be achieved without callbacks or mutable shared state.

## 2026-10-16 — Personal recommendation allocation contract probe merged (PR #221)

- PR #221 merged at `820556799fa9d3ec663e5117b36c68084281b20a` from exact tested head `9d17a0ef32782db35b19b5226d3b8c052f8775d6`.
- Defined immutable prepared-candidate/request/result types in `discovery_allocation_contract.py`; added direct-import contract invariant tests and the boundary decision document. All four exact-head workflows passed (syntax `38916419736`, Docker/full unit suite/build `38916419709`, runtime smoke `38916419958`, validation-only multi-architecture `38916419701`).
- The shortlist-selection loops remain in `navidrome_server.py`. The interface probe has no callbacks or shared mutable counters, but it is not proof that the actual policy can be extracted unchanged. Next extraction must first demonstrate parity for reservations, quotas, duplicate/artist limits, ownership review, fallback order, diagnostics, and the 60-check cap; stop/refine if this cannot be achieved within the boundary.

