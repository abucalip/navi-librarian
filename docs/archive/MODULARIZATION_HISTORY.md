# Archived legacy documentation snapshots

This archive preserves the former diary-style contents of the active roadmap, project status, test plan, and architecture document before they were rewritten as concise current-purpose documents on 2026-10-16. It is intentionally not part of routine session-start reading.

The snapshots below are preserved for traceability and to avoid losing unique historical notes. They are not current instructions or a source of truth for current status. Current GitHub `main`, current CI evidence, and the replacement documents take precedence. For current history, start with root `PROJECT_LOG.md`; search this archive only when the primary log lacks a specific historical detail.


---

# Legacy snapshot: `docs/MODULARIZATION_ROADMAP.md`

## 2026-10-16 — New Releases lookup construction completed (PR #236)

Merged at `aaa748f2dfdc307d79faf5397a51dbfbcd75ec6c` from exact tested head `990e3ddfe08b6b1590860e8fd07d0ac13882be3e`. `discovery_new_releases.build_new_release_lookup()` now owns the pure query and cache-key rule; provider/cache/rate-limit/error behavior stays in the adapter. Direct-import regressions added. All four required exact-head workflows passed: syntax/acquisition safety `38938238608`, Docker/full suite/build `38938238694`, runtime smoke `38938238678`, validation-only multi-architecture `38938238904`. No assistant-side local test run or publication/deployment/runtime verification claimed.

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

The next small application-assembly seam is pure resolution of `DISCAIR_DATA_DIR` versus the source-directory fallback. `data_directory.py` resolves the path without creating it; `navidrome_server.py` retains the legacy `DATA_DIR` symbol and the existing `mkdir` side effect, so data persistence and permissions remain owned by the existing service. Direct-import tests cover explicit path expansion, empty configuration, and fallback behavior. Docker packaging is updated. Verify the focused tests, full suite, syntax, and all four required workflows on the exact final PR head before merge. Publishing remains paused.


## Completed — data-directory resolution (PR #152, 2026-10-15)

Extracted the pure `DISCAIR_DATA_DIR` / source-directory fallback resolver to `data_directory.py`. The legacy `navidrome_server.DATA_DIR` and directory-creation behavior remain intact. Three direct-import regression tests and Docker packaging were added. All four required workflows passed on exact PR head `756ef13f6946299e2eacccbf5f9a55ebaf092aae`; merged by squash as `567409bb90f240667575a3730976e4c52676bc02`. Publishing remains paused; no deployment or production runtime verification is claimed.


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



## 2026-10-16 — New Releases date-window policy extraction completed (PR #237)

- Extracted deterministic cutoff/year-bound calculation into `discovery_new_releases.new_release_window(today)`; adapter retains clock access and provider/cache orchestration.
- Added direct-import tests for the 730-day cutoff and leap-day behavior. All four required workflows passed on exact PR head `8d42c9f5f320fd7b4c0653fa09da8eda12f03f78`: syntax `38938867862`, Docker/full unit suite/build `38938867879`, runtime smoke `38938867737`, validation-only multi-architecture `38938867550` (publishing paused).
- Merged as `2d11e52b78004ee51a6ce70a6a6ac6c2b451f397`. Assistant-side local test commands were not run independently; no deployment/runtime verification is claimed.


## 2026-10-16 — PR #238 merged: New Releases provider lookup

- Squash merge commit: `59430bba44bd32a9dfbbe51f19c3e2e8a1441c13`; exact tested PR head: `a26614489d1407792ba959461537f4e8d87fee06`.
- Extracted the cache/read-through MusicBrainz request into `discovery_new_releases.fetch_artist_release_groups()`. The server adapter retains artist iteration, the pacing decision, query construction, candidate selection/merging, and response assembly.
- Direct-import regressions cover cache hits, request parameters/timeout, pacing, cache writes, malformed payload normalization, and safe error-type reporting.
- All four required workflows passed on the exact PR head: Python syntax run `38939659986`; Docker packaging/full unit suite/build run `38939659632`; container runtime smoke run `38939659664`; validation-only multi-architecture image validation run `38939660017` (publishing paused).
- No assistant-side local test commands were run independently. No image publication, deployment, or production runtime verification is claimed.
- **Next action:** refresh main and inspect the remaining acquisition lifecycle/application-assembly boundaries before choosing another independently testable extraction.


## 2026-10-16 — Application-assembly seam: auth configuration predicate (PR #239)

The pure check that determines whether all three persisted owner-auth fields are present is extracted to `app/security/auth_configuration.py`. The app assembly retains settings access and its compatibility wrapper. Direct-import tests preserve existing truthiness behavior. All four required workflows passed on the exact final PR head: syntax `38940305016`, Docker/full suite/build `38940304930`, runtime smoke `38940304907`, validation-only multi-architecture `38940305045`. This completes only the narrow predicate seam; broader application-assembly accounting and auth-flow verification remain.


## 2026-10-16 — Lazy auth-secret provider (PR #240 merged)

Merged at `78547fd47c1b155255c1da6ef57120b76513a0fc` from exact tested head `e3542c6a8fa3b2fc3ddf07a0268563ae5946064a`. `app/security/auth_secret.py` now owns lazy, lock-protected loading and successful-result caching. The app assembly injects the data-directory getter and existing `load_auth_secret`; `_AUTH_SECRET` remains as a compatibility seam. Direct-import tests cover lazy initialization, cache behavior, retry after exceptions/None, and concurrent first use. All four exact-head workflows passed (syntax `38941505550`, Docker/full suite/build `38941505440`, runtime smoke `38941505508`, validation-only multi-architecture `38941505516`). No publishing/deployment/runtime verification. Next: continue the application-assembly dependency inventory; do not remove MCP until web callers have tested domain/service owners.



---

# Legacy snapshot: `docs/PROJECT_STATUS.md`

## 2026-10-16 — PR #240 merged: lazy auth-secret provider

- Squash merge commit: `78547fd47c1b155255c1da6ef57120b76513a0fc`; exact final tested PR head: `e3542c6a8fa3b2fc3ddf07a0268563ae5946064a`.
- Extracted lazy, thread-safe persistent signing-secret loading into `app/security/auth_secret.py`. `app/main.py` retains the `_AUTH_SECRET` compatibility seam, dependency wiring, and all auth route/session/middleware/cookie behavior.
- Added direct-import tests for lazy loading, successful caching, retry after exceptions/None, and concurrent first use.
- Initial CI found that auth integration tests patch `app.main._AUTH_SECRET`; restored that compatibility seam and re-ran CI on the corrected final head.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety `38941505550`; Docker packaging/full unit suite/build `38941505440`; container runtime smoke `38941505508`; validation-only multi-architecture image validation `38941505516` (publishing paused).
- Assistant-side local tests were not run. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — PR #236 merged: New Releases lookup construction

- Squash merge commit: `aaa748f2dfdc307d79faf5397a51dbfbcd75ec6c`; exact tested PR head: `990e3ddfe08b6b1590860e8fd07d0ac13882be3e`.
- Extracted pure MusicBrainz query and versioned cache-key construction into `discovery_new_releases.build_new_release_lookup()`. Provider requests, cache access, throttling, date-window policy, and error handling remain in `_build_new_releases_list()`.
- Added direct-import regressions for date-bounded query shape, quote/backslash escaping, and cache-key stability.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `38938238608`; Docker packaging/full unit suite/build `38938238694`; container runtime smoke `38938238678`; validation-only multi-architecture image validation `38938238904` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — PR #235 merged: New Releases response projection

- Squash merge commit: `0d77f7d99a89660ea1d9a38635e93343538e93b8`; exact tested PR head: `f3e7ec7c14deac8136b5066011623e00dffca134`.
- Extracted sorting, the 200-item visible cap, the 20-error cap, and response shaping into `discovery_new_releases.build_new_release_response()`. Provider/cache/rate-limit access, date-window policy, candidate selection, and error collection remain in the server adapter.
- Added direct-import tests for newest-first ordering/tie behavior, response metadata, error/item caps, and non-mutation. Docker packaging already included `discovery_new_releases.py`, so no packaging change was needed.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety run `38937239432`; Docker packaging/full unit suite/build run `38937239481`; container runtime smoke run `38937239444`; validation-only multi-architecture image validation run `38937239482` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — PR #234 merged: New Releases global candidate merge

- Squash merge commit: `c44ea572354b4714e5e2577f5eb21b091be97cc8`; exact final PR head `56bb5b6835d03860124f2dbdff4dbb13a813d5c8`.
- Extracted `discovery_new_releases.merge_release_candidates()` to own cross-artist identity merging and newest-date winner selection. Existing candidate wins ties; inputs are not mutated. Direct-import regressions cover newer winner, tie stability, non-mutation, empty inputs, and missing dates.
- All four required workflows passed on the exact final PR head: Python syntax run 38935716487, Docker packaging/full suite/build run 38935717026, container runtime smoke run 38935716420, validation-only multi-architecture run 38935716622. Assistant-side local tests were not run. Publishing, deployment, and production runtime verification remain unclaimed.

## 2026-10-16 — PR #233 merged; New Releases global merge extraction in progress

- PR #233 squash merge: `08e20f502e10f829bf9ae7920106b7e8427668eb`, from exact tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`. All four required workflows passed: syntax/acquisition safety 38934044235, Docker/full suite/build 38934044270, runtime smoke 38934044253, validation-only multi-architecture 38934044237. Local test commands were not run; publishing/deployment/runtime verification remain unclaimed.
- PR #234 extracts cross-artist candidate merging to `discovery_new_releases.merge_release_candidates()`, preserving newest-date winner and existing winner on ties. Direct-import regressions added. CI pending on exact final head.

## 2026-10-16 — PR #232 merged: classics candidate collection

- Squash merge commit: `451944c9056eeb50ec7d8b1744bbf435d653b70b`. `discovery_classics_candidates.collect_classic_candidates()` owns candidate collection, normalized duplicate resolution, ownership/eligibility filtering, metadata, and fifth-artist pacing; the server retains library/provider access, scoring, enrichment, diversity, and response assembly.
- The latest four workflow runs inspected for the PR reported success (syntax/acquisition safety, Docker packaging/full suite/build, container smoke, and non-publishing multi-architecture validation). The connector evidence did not independently expose each run's head SHA, so this closeout does not label them exact-head verified. Assistant-side local tests were not run. Publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — New Releases library qualification extraction in progress

The next candidate moves normalized ownership identity construction and full-album artist qualification/sorting into `discovery_new_releases.prepare_new_release_library_scope()`. It preserves the six-track threshold, Various Artists exclusion, stable descending album-count order, all-owned-album identity set, and untruncated qualified count. The adapter retains the 120-artist request cap, date-window policy, MusicBrainz requests/cache/rate limit, error reporting, and global merge. Direct-import contract tests are added. PR #233 is open on tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`. All four required workflows passed on that head: Python syntax/acquisition safety run 38934044235, Docker packaging/full unit suite/build run 38934044270, container runtime smoke run 38934044253, and validation-only multi-architecture validation run 38934044237. Assistant-side local tests were not run. Merge remains pending; publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — PR #231 merged: classics genre enrichment

- Merged PR #231 from `extract/classics-genre-enrichment`; exact tested PR head `0856f2a9a91e8b3aff88f933d845b182007997d4`; squash merge commit `b23d76712a04dcbfc461ceb7245a0676738fca7a`.
- Extracted bounded genre enrichment into `discovery_classics_genres.enrich_classic_genres()`. Last.fm provider/cache access and family classification remain injected; the helper owns normalized artist lookup deduplication, the 300-candidate limit, and empty/`other` fallback metadata.
- Added direct-import regression tests and Docker packaging. All four required exact-head workflows passed: Python syntax run 1208, Docker packaging/full unit suite/build run 1116, container runtime smoke run 925, and validation-only multi-architecture validation run 969 (publishing paused). Assistant-side local test execution was not performed.
- No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — PR #230 merged: watcher progress accounting

- Extracted the pure byte-counter progress/timer transition into `acquisition_progress_accounting.observe_progress()`; watcher polling, stall thresholds/countdown, source switching, transfer-state interpretation, filesystem verification, and safe import remain in `acquisition_watcher.py`.
- Added direct-import tests for increased, unchanged, and decreasing counters and the exact 120-second boundary; included the helper in Docker packaging.
- PR #230 exact tested head: `47fb2a5bb18d4101dde910dd30e5bad2ed13e2e7`; squash merge: `57f9776b1b517c7c86119b2a11d7f919b8cab631`.
- All four required workflows passed on the exact tested head: Python syntax run 1202; Docker packaging/full unit suite/build run 1110; container runtime smoke run 919; validation-only multi-architecture image validation run 963 (publishing paused). Assistant-side local test commands were not run.
- No image publication, deployment, or production runtime verification is claimed. Publishing remains paused.

## 2026-10-16 — PR #229 merged: classics critical-rating extraction

- Audited `_build_classics_list()` and isolated the critical-rating enrichment stage as `discovery_classics_ratings.enrich_critical_ratings()`. The helper receives candidates and the existing cached/provider lookup callable; it preserves listener-descending stable shortlist ordering, the 80-candidate request bound, `include_year` for the first 30, rating/vote defaults, and year overwrite only when supplied.
- Added direct-import contract tests for shortlist order/bounds, year lookup cap, missing ratings, stable ties, and invalid limits; added Docker packaging and delegated the existing builder stage without changing the surrounding pipeline.
- Contract is independently testable with one injected provider lookup and explicit in-place candidate mutation. PR #229 merged at `925eb16cba7d2387cd0a17c7690e36d35f17e8f1` from exact tested head `28c364dca41971ea90667c175663de17b41ca7ab`.
- All four required workflows passed on that exact head: Python syntax/acquisition safety run 1194; Docker packaging/full unit suite/build run 1102; runtime smoke run 911; validation-only multi-architecture run 955. Local test execution was not performed.
- Publishing/deployment remain paused and are not claimed. Next: choose the next independent boundary from the remaining modularization priorities.
## 2026-10-16 — Session closeout: PRs #225 and #226 merged

- **PR #225 — cached discovery-list payload shaping:** exact final tested head `573fe05d31dae422c25188688cd2fa949339e487`; squash merge `4d968b381d1f541b81a4a46d1753b5145347e33d`. Extracted cached-list filtering and response projection to `discovery_list_payload.build_cached_discovery_list_response()`; server-side validation, feedback persistence/read, For Me inventory lookup, and dependency wiring remain in the adapter. All four exact-head workflows passed: syntax/acquisition safety 1187; Docker packaging/full suite (477 tests)/build 1095; runtime smoke 904; validation-only multi-architecture 948.
- **PR #226 — background listening-profile refresh:** exact final tested head `740979f1b4da4f5c13632ab3598c13bc09ed413e`; squash merge `f5a95338e978a14d01fb6a1c3741e2e6c8bea11c`. Extracted refresh parsing, success/error normalization, background marker, and persistence to `listening_profile.refresh_and_persist_background_profile()`; scheduler timing and server callbacks remain in the adapter. All four exact-head workflows passed: syntax/acquisition safety 1189; Docker packaging/full suite (481 tests)/build 1097; runtime smoke 906; validation-only multi-architecture 950.
- PR #225's initial CI found an incorrect fixture assertion about a legacy top-level field; corrected before final verification. Assistant-side local test commands were not run. No image publication, deployment, or production runtime verification is claimed. Publishing remains paused.
- **Next action:** refresh GitHub main/open PRs/CI and select the next independently testable seam; do not treat extraction count as a quota.

## 2026-10-16 — PR #224 merged: personal recommendation payload shaping

- PR #224 merged as `f795239589e6dd78f0f5e6d98cf2eadc897d6f49` from exact final tested head `6d2e0ccc8d24cd11b727255f171fd405384a8729`.
- Extracted pure base payload projection to `discovery_recommendation_payload.py`. The server adapter still supplies recent-listen counts and applies the distinct `ownership_check` (selected) / `ownership_note` (manual review) annotations.
- All four required workflows passed on that exact head: syntax + acquisition safety run 1177; Docker packaging/full suite (473 tests)/build run 1085; runtime smoke run 894; validation-only multi-architecture image validation run 938 (`push: false`).
- No independent local test run, image publication, deployment, or production runtime verification is claimed. Publishing remains paused.

## 2026-10-16 — Personal recommendation payload projection extraction (verification pending)

- Started from current GitHub main after PR #223. Moved the pure base recommendation response projection from the nested `recommend_new_music()` helper into `discovery_recommendation_payload.py`; the adapter still computes recent-listen counts and adds selection-specific ownership annotations.
- Added direct-import field/default/rounding/reason tests and included the helper in the Docker module list.
- No local tests were run. Exact-head CI and full diff review remain pending; no merge, publication, deployment, or runtime verification is claimed.

## 2026-10-16 — PR #223 merged: personal recommendation allocation

- PR #223 merged as `1ccb11485bf1efce3ff201fb7337407c3e668c47` from exact final tested head `b604940e4b7a20160d4f3710b009c6ca718c57c5`.
- Extracted the shortlist allocation policy to `discovery_personal_allocator.py`, with immutable candidate/result contracts in `discovery_allocation_contract.py`. The server adapter retains identity normalization, Navidrome ownership lookup, response payload construction, ownership-review shaping, and diagnostics. Docker packaging includes both modules.
- All four required workflows passed on the exact final head: Python syntax + acquisition safety run 1171; Docker packaging/full unit suite (468 tests)/build run 1079; container runtime smoke run 888; validation-only multi-architecture image validation run 932 (`push: false`).
- Initial CI caught two test-fixture expectation errors; both were corrected before the final passing head. Adapter review also preserved distinct selected vs ownership-review payload fields. No independent local test run, publication, deployment, or production runtime verification is claimed.
- Publishing remains paused. Next action: refresh GitHub main/open PRs and choose the next smallest safe independent extraction; do not treat extraction count as a quota.


## 2026-10-16 — Personal allocator boundary investigation (pre-integration history)

- This records the exploratory stage before PR #223. The immutable contract was merged in PR #221, then the allocator policy and direct-import tests were developed on a separate branch.
- Tie-order analysis found that regional-style reservations preserve original candidate insertion order, while final fallback concatenates category lists already sorted by score and then uses a stable global score sort. The final allocator preserves that behavior with `source_order`.
- The investigation was completed by PR #223, which integrated the adapter, added Docker packaging, and passed all four required exact-head workflows. See the PR #223 entry above for the verified final state.
- Publishing and deployment remain paused.



## 2026-10-16 — PR #194 merged: token cleanup and touch targets

- Refreshed PR #194 against current main and merged the reviewed CSS/documentation diff. Exact tested PR head: `0cf2e4329015fd9159213fbe25561decb16dbdb8`; squash merge commit: `10b14c1ed37bfc20930bf642f511065404dfb379`.
- Manual browser report was published by the operator in PR #194 comments for that exact head. All 8 checklist items passed with zero failures: first-run setup, dashboard/artwork, discovery lists, navigation/album details, settings load/save and secret handling, Get/request behavior without a real download, acquisition cards/status, and absence of unexpected browser/server errors.
- All four required workflows passed on the exact tested head: Python syntax run 38900816052; Docker packaging/full unit suite/build run 38900816045; container runtime smoke run 38900816210; validation-only multi-architecture image validation run 38900816039 (`push: false`).
- Scope remained `static/app.css` and `docs/UI_BACKLOG_EXECUTION.md`. Merge is verified; publishing remains paused. No image publication, deployment, or production runtime verification is claimed.
- **Next action:** refresh current main/open PRs/CI and review outstanding work against the requirements and priority order before choosing the next task.

## 2026-10-16 — Session closeout: PRs #208–#210 merged

- **PR #208 — page/asset routes:** merged as `8ed54b0cc3750dc0aae1bc20efda61bba7dd71cd` from exact tested head `75305491eb12ff1796569f51e364aace41796292`. All four required workflows passed (syntax 1121, Docker/full suite/build 1028, runtime smoke 837, validation-only multi-architecture 881).
- **PR #209 — login-gate middleware:** merged as `669379aaed12092b1f826d46e0c3f8675e6ea6eb` from exact tested head `1b248dcb20d7a0f8622f32de6ae0bcfc3e5795ed`. All four required workflows passed (syntax 1123, Docker/full suite/build 1030, runtime smoke 839, validation-only multi-architecture 883).
- **PR #210 — session-cookie policy:** merged as `21cd2bc19e9af66bb155b0d036f3b1f9ffb8d28f` from exact tested head `a394b6ea75fff91fcd4828f1946c14b98bbcf827`. All four required workflows passed (syntax 1125, Docker/full suite/build 1032, runtime smoke 841, validation-only multi-architecture 885).
- Regression tests added for page routes/assets, authentication-gate decisions, and session-cookie security attributes. These are code merges only; publishing, deployment, and production runtime verification are not claimed.
- **Session outcome:** no further extraction started. Next session should refresh GitHub state and read the current requirements/workflow/test-plan/roadmap before choosing another candidate. Keep PR #194 unchanged as previously requested; review other open PRs against current priorities rather than assuming they are ready to merge.

## 2026-10-16 — Independent extraction session closeout: PRs #205 and #207

- **PR #205** extracted pure per-artist MusicBrainz release-group eligibility/candidate shaping into `discovery_new_releases.select_artist_release_candidates()`. Exact final tested head `079d355e972ea39d792c1dfa6fca6eab902800e3`; all four required workflows passed: syntax 1111, Docker packaging/full unit suite/build 1018, runtime smoke 827, validation-only multi-architecture 871. Squash merge: `32b39be400ec046e8310a87260346b1959141609`.
- **PR #207** extracted pure Artist Deep Dives scoring, exploration ranking, eligibility filtering, and two-pass artist/anchor/genre diversity into `discovery_recommendations.rank_and_diversify_deep_dive_candidates()`. Exact final tested head `20e565582579f4097eed3803748c87bb3d932a98`; all four required workflows passed: syntax 1114, Docker packaging/full unit suite/build 1021, runtime smoke 830, validation-only multi-architecture 874. Squash merge: `a5b0d865060c3d069a865be7a1cb43c1a072ae91`.
- Both preserve server-side provider access, cache/rate limiting, and existing compatibility wrappers. Direct-import regression tests were added; assistant-side local tests were not run. No publication, deployment, live provider integration, or production runtime verification is claimed. Publishing remains paused and acquisition-dismissal HTTP 409 remains deferred.
- PR #206 was closed as superseded when refreshing its branch from current main; its work was recreated and merged as PR #207.
- **Next action:** refresh main/open PRs/CI and choose the next small, low-coupling seam; do not treat extraction count as a quota.


## 2026-10-16 — Independent extraction session closeout: PRs #202 and #203

- **PR #202** extracted pure Navidrome library-overview payload shaping into `navidrome_client.library_overview_payload()`; `navidrome_server.library_overview()` retains API calls, collection normalization, JSON serialization, and the MCP-facing contract. Exact tested head `6903f40578f40fec08f1efde92d6577fcaeeced0`; all four required workflows passed: syntax/acquisition safety 1104, Docker packaging/full unit suite/build 1011, runtime smoke 820, validation-only multi-architecture 864. Squash merge: `7a95364a31f360bb20dd8d2919a9bfea93ec893c`.
- **PR #203** extracted source-preview sensitive-assignment redaction into `server_source_redaction.redact_assignment()`. `get_server_source()` retains source selection, range validation, 250-line bound, numbering, and JSON response shape. Docker packaging includes the helper. Exact tested head `14019b8beeca9b71fbb8167117dafea3f60c74ea`; all four required workflows passed: syntax/acquisition safety 1106, Docker packaging/full unit suite/build 1013, runtime smoke 822, validation-only multi-architecture 866. Squash merge: `89e639394122aebe29bfb8602a1135722ea28bbe`.
- Both changes include direct-import regression tests and preserve legacy compatibility. Assistant-side local tests were not run; full unit suites were run by the Docker packaging CI jobs. No live Navidrome integration, source-secret access, image publication, deployment, or production runtime verification is claimed.
- Acquisition-dismissal HTTP 409 remains deferred. Publishing remains paused.
- **Next action:** refresh main/open PRs/CI and select the next small, low-coupling extraction; do not treat extraction count as a quota.


## 2026-10-16 — PRs #196 and #198 merged: Navidrome response shaping

- **PR #196** (branch refactor/extract-navidrome-search-shaping): exact tested head 4b501c64c82a69af1805a7f6195b4fc15ef0c836; squash merge 277499ec949353f5f24542a8033a481283814782. Extracted pure Subsonic search-result shaping into navidrome_client.search_result_payload(); search_music() remains the compatibility/MCP-facing adapter.
- **PR #198** (branch refactor/extract-navidrome-album-details-main): exact tested head a718780edcb85eb8f4453e44a2d5a4925a512314; squash merge 92cdd6309244e78e78bd0f6f8d2e38ea929e434b. Extracted album/track payload shaping into navidrome_client.album_details_payload(); get_album_details() retains API access, JSON serialization, and the compatibility interface.
- Both PRs added direct-import regression coverage and preserved response field names, scalar/list handling, and formatting. All four exact-head workflows passed separately:
  - PR #196: syntax run 1088; Docker packaging/full unit suite/build run 995; runtime smoke run 804; validation-only multi-architecture run 848.
  - PR #198: syntax run 1090; Docker packaging/full unit suite/build run 997; runtime smoke run 806; validation-only multi-architecture run 850.
- Assistant-side local test commands were not run. CI packaging workflows ran the full unit suite. No image publication, deployment, or production runtime verification is claimed.
- PR #197 was closed as superseded while recreating its follow-up branch from the post-#196 main; replacement PR #198 was merged. Main after the two code merges: 92cdd6309244e78e78bd0f6f8d2e38ea929e434b.
- Acquisition-dismissal HTTP 409 remains deferred per user direction. Publishing remains paused.
- **Next:** refresh main/open PRs/CI and select the next small, low-coupling extraction; continue keeping each extraction independently tested and preserve MCP compatibility.
## 2026-10-16 — PR #192 merged: settings tabs and skip-link accessibility

- Replacement for conflicted PR #188, refreshed from main `470b232977b45ee1cf1bf1b399c2c43843062c1f`; PR #192 exact tested head: `75c13b0099285747c9da75c5c3879e6594e5fe36`; squash merge/current main: `4fc72001807e0afc40ebc99bf1be9a502f87e0f8`.
- Added a first-tab-stop skip link targeting `main#content`; completed settings tabs keyboard behavior (roving tabindex, arrow/Home/End navigation, wrap-around), and accessible names for all four tab panels. Updated `docs/UI_BACKLOG_EXECUTION.md`.
- All four required exact-head workflows passed: Python syntax (run 1069), Docker packaging/full unit suite/build (run 976), container runtime smoke (run 785), and validation-only image workflow with publishing paused (run 829).
- User-published manual browser report in PR #192 comment confirms checklist passed with zero failures on exact head `75c13b0099285747c9da75c5c3879e6594e5fe36`. No assistant-side local tests, image publication, deployment, or production runtime verification are claimed.
- PR #188 was closed as superseded; PR #192 merged. Main was verified at merge SHA `4fc72001807e0afc40ebc99bf1be9a502f87e0f8`.
- Next: refresh GitHub main/open PRs/CI and follow the current priority order; acquisition-dismissal HTTP 409 remains deferred as previously directed.

## 2026-10-16 — PR #190 merged: artist-biography resolution

- PR #190 merged at `b829fa953d979563a8ace6e5529eace8cb80ac43` from exact tested PR head `6c04d8a67944568a3e2b280deafb4eb2c66c2391`.
- Moved pure Wikidata/Wikipedia identity matching, music-entity filtering/ranking, first-sentence normalization, and summary truncation into `app/services/artist_bio.py`. The metadata route retains concurrent provider requests, caching, input validation, and response shape.
- Added direct-import regressions in `tests/test_artist_bio_service.py`; retained `tests/test_metadata_routes.py`. All four exact-head workflows passed: syntax/acquisition safety run 1059; Docker packaging/full suite/build run 966; runtime smoke run 775; validation-only multi-architecture run 819.
- Assistant-side local tests were not independently run. No publication, deployment, or production runtime verification is claimed.
- PR #190 code merge SHA: `b829fa953d979563a8ace6e5529eace8cb80ac43`; documentation closeout commits followed on main. Acquisition-dismissal HTTP 409 remains deferred.
- Next: refresh main/open PRs/CI before selecting another independent extraction.

## 2026-10-16 — PR #189 merged: dashboard-pick service extraction

- PR #189 merged at `f5f355f8bdc0599bb240933e248177c7b0517ff5` from exact tested PR head `d28aaa33f7096ba764232d6bd435cc68d5d85f98`.
- Extracted dashboard-pick assembly into `app/services/dashboard.py`: three discovery lanes, album eligibility, case-insensitive artist/album deduplication, balanced category selection, and random fill. `app/api/dashboard.py` retains HTTP validation, lazy dependency injection, and the endpoint response contract.
- Direct-import regressions are in `tests/test_dashboard_service.py`; existing route tests remain. All four required exact-head workflows passed: Python syntax/acquisition safety run 1052; Docker packaging/full suite/build run 959; container runtime smoke run 768; validation-only multi-architecture image run 812.
- Assistant-side local tests were not independently run. No image publication, deployment, or production runtime verification is claimed. Acquisition-dismissal HTTP 409 remains deferred.
- During setup, the new test file was briefly written to main by an omitted branch argument; it was immediately removed in commit `039b5ed14834aeb63627f141c1bafa1d96c8589b`, confirmed absent from main, and committed correctly on the PR branch. The merge contains the intended test file; no accidental test file remains on main.
- Main tip at closeout: `f5f355f8bdc0599bb240933e248177c7b0517ff5`. Next: refresh main/open PRs/CI and select the next independent low-coupling extraction.

## 2026-10-16 — PRs #186 and #187 merged

- **PR #186 — empty-state copy/state kinds:** manual browser report published in PR comments for tested head `0c12a43cd40211d522868dab7caa70c8a5fbf6e6`; checklist passed with zero failures. All four GitHub Actions workflows passed on that exact tested head (syntax run 1041, Docker packaging run 948, runtime smoke run 757, validation-only image run 801). Squash merge: `d42618b63f141049d5b0e6558e81174ef5c1418f`.
- **PR #187 — slskd connection probe extraction:** extracted `slskd_client.test_connection()`, retained `discovery_test_slskd_connection()` as the compatibility adapter, added direct-import regression tests and Docker packaging. All four required GitHub Actions workflows passed on final PR head `920590871883aa8c75c29a1b16131bd88519072d` (syntax run 1041, Docker packaging/full suite/build run 948, runtime smoke run 757, validation-only image run 801). Squash merge: `b7ae6458adda3650f178fc64457914beb66ece9c`.
- Assistant-side local tests were not independently run. CI is the verification evidence; no image publication, deployment, or production runtime verification is claimed.
- Acquisition dismissal HTTP 409 remains deferred per user direction; neither PR changed acquisition cleanup behavior.
- GitHub main tip at closeout: `b7ae6458adda3650f178fc64457914beb66ece9c`.
- **Next action:** refresh main, open PRs and exact-head CI, then select the next two or three low-coupling extractions under the roadmap. Keep publishing paused.

## 2026-10-16 — slskd connectivity probe extraction in progress (PR #187)

- Branch `refactor/extract-slskd-connection-check`, based on GitHub main `d66257586b69c4cb03641f5ce67050c3f4defd76`; current implementation head before this documentation update: `73be3bf8fa1211edff3689bfd1a9c820bf6770d6`.
- Extracted the slskd connection probe into `slskd_client.test_connection()`; `discovery_test_slskd_connection()` remains the compatibility adapter. Added direct-import tests for success, 401/403, HTTP/configuration errors, and API-key redaction; Docker packaging includes the module.
- Assistant-side test execution and exact-head CI are not yet verified. Publishing, deployment, and production runtime verification are not claimed. No live slskd request or credential was used.
- Acquisition dismissal HTTP 409 remains deferred per user direction; no cleanup behavior changed.
- Next action: verify the final PR-head checks and review the complete diff before merge; do not begin a conflicting server-file extraction before this gate is resolved.

## 2026-10-16 — Two slskd progress calculation extractions merged

- **PR #182 — progress summary:** extracted matched transfer byte/track aggregation into `slskd_transfers.summarize_transfer_progress()`; kept HTTP retrieval, transfer matching invocation, speed snapshots/locking, and public progress schema in the legacy service. Exact tested head `045131f58365dd0e6538c1712f37f56f639c65ad`; squash merge `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`. Exact-head CI passed: Python syntax run 1016, Docker packaging/full suite/build run 923, container runtime smoke run 732, validation-only multi-architecture run 776.
- **PR #183 — speed estimator:** extracted pure delta-based speed calculation into `slskd_transfers.estimate_transfer_speed()`; snapshot identity, shared state, and locking remain in the server. Final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`; squash merge `e4e9bd1fad9536f00f3908d753b66147d30ca03f`. Exact-head CI passed: Python syntax run 1019, Docker packaging/full suite/build run 926 (342 tests passed), container runtime smoke run 735, validation-only multi-architecture run 779. An earlier test run caught an incorrect expected speed in the new test (the elapsed interval was 1 second); corrected the fixture expectation and verified all gates on the final head.
- Both PRs retained the legacy progress output contract and added direct-import regressions. Assistant-side local test commands were not run. No image publication, deployment, or production runtime verification is claimed.
- GitHub main code tip at merge closeout: `e4e9bd1fad9536f00f3908d753b66147d30ca03f`. The initial open-PR audit found only PR #23, the modularization roadmap; PRs #44/#45 remain closed. During this session, UI PR #184 (`ui/artist-deep-dive`) appeared against the earlier `9f05bed` base; comparison with current main showed it 7 commits behind. Its own description explicitly records the required manual browser checklist as NOT RUN, so it remains unmerged and needs a refreshed exact-head CI run plus the human checklist before merge. This UI work was not modified in this backend session. The acquisition-dismissal HTTP 409 stays deferred per user direction; no cleanup semantics or safety checks were changed.
- **Next action:** refresh main/open PRs/CI, then select the next low-coupling roadmap seam. Keep publishing paused.

---

## 2026-10-16 — Two slskd transfer-boundary extractions merged

- Main code merge #180: `7c670f2eac838934bc9afa7f40f892ff595ca4ca`. Exact tested PR head: `ce0e635cc77c687958d6ad1c1a852e55476c14b2`. Queue HTTP request extracted to `slskd_transfers.queue_download_files()`; legacy adapter and dismissal/orchestration contract retained. Exact-head CI passed: syntax run 1008, Docker packaging/full suite/build run 915, runtime smoke run 724, validation-only image run 768.
- Main code merge #181: `3df14d3c59bb7e5a689d797028e45468c6a87ee7`. Exact tested PR head: `cf78b4188a549d6e1b2b98c76a63a6bc0826d129`. Expected/tracked transfer matching extracted to `slskd_transfers.match_expected_transfer_records()`; live progress response and byte/speed calculations retained. Exact-head CI passed: syntax run 1010, Docker packaging/full suite/build run 917, runtime smoke run 726, validation-only image run 770.
- Local assistant-side test commands were not run. Full unit tests ran as part of the CI packaging jobs. Publishing, deployment, and production runtime verification remain unperformed.
- The reported acquisition-dismissal HTTP 409 remains deferred; no cleanup or dismissal behavior was changed.
- Next action: refresh GitHub main/open PRs and select the next independent roadmap seam.

## 2026-10-16 — Last.fm similar-artist extraction merged

- PR #178 merged; merge commit `f18574b74a564031c5268cf04c956475d64dc30c`. PR head verified at `a97be052d3a1e74843feaacd6403d10ce5aad6af`.
- Extracted cached `artist.getSimilar` normalization into `LastFmClient.similar_artists()`; kept `_lastfm_similar_artists()` compatibility adapter and added regression coverage.
- Exact PR-head GitHub Actions gates observed successful: Python syntax check (run 1003), Docker packaging validation (run 910), container runtime smoke test (run 719), and Docker image validation with publishing paused (run 763). No image publication or deployment was performed. Local full-unit-suite result was not independently run/verified in this session.
- Next action: refresh main and select the next focused extraction only after confirming current PR/CI state. Acquisition-dismissal HTTP 409 remains deferred per user direction.

---

## 2026-10-16 — Last.fm similar-artist parsing extraction in progress

- Branch `refactor/extract-lastfm-similar-artists-current`, based on refreshed GitHub `main` at `86b2ac60416ed725755fc6c57200e1c3123b7606` after the #175/#176 closeout.
- Moved cached `artist.getSimilar` retrieval and record normalization into `LastFmClient.similar_artists()`; retained `_lastfm_similar_artists()` as a compatibility adapter.
- Added direct-import regressions for list/scalar payloads, blank/malformed records, similarity normalization, cache hits/misses, request parameters, TTL, and adapter delegation. Existing Docker packaging already includes `lastfm_client.py`.
- Exact-head tests/CI, PR review, and merge pending. Publishing/deployment remain paused. Acquisition-dismissal HTTP 409 remains deferred as directed.

---

## 2026-10-16 — Last.fm top-albums parsing extraction in progress (PR pending)

- Based on refreshed GitHub `main` after PR #174 merge: `4dd8b926a7a6cf76e248420860d7c29c892da3c0`.
- `LastFmClient.artist_top_albums()` owns cached `artist.getTopAlbums` retrieval and record normalization. The legacy `_lastfm_top_albums()` adapter retains discovery-specific album eligibility filtering.
- Added direct-import regression coverage for scalar/list payloads, blank-title filtering, metadata normalization, request parameters, cache TTL/hits, missing payloads, and compatibility adapter filtering.
- CI, merge, publication, deployment, and production runtime verification pending. Acquisition dismissal HTTP 409 remains deferred as directed.

---

## 2026-10-16 — Last.fm artist tag extraction completed (PR #174)

- Started from `ffa2b441e7543b2778d1835cfc42386e53c37225`; merged commit `4dd8b926a7a6cf76e248420860d7c29c892da3c0`.
- `LastFmClient.artist_genres()` now owns cached artist top-tag parsing; the legacy adapter remains intact.
- Exact final PR head `08c260e2a166a744bbde4009196b53d238afb647` passed syntax/acquisition safety, full unit suite and Docker build, runtime smoke, and non-publishing multi-architecture validation. Initial fixture logging error was corrected before this passing head.
- Publishing/deployment remain paused and unverified. Acquisition dismissal HTTP 409 remains deferred by explicit user direction.

---

## 2026-10-16 — Three-extraction session closeout (PRs #170–#172)

- Session started from GitHub `main` at `098c5d9d8536070c1115ec2a7c25b99490efb312`. Final code `main` after the three sequential merges: `d5153a3fe0625bc52b5896e87846b55cabe58e81`.
- **PR #170 — MusicBrainz tag audit:** tested head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07`; squash merge `dbbdda35792fd569cfdeec2c4c7b42fc106f84e3`. Extracted the bounded, read-only missing-MBID scan into `music_tag_audit.py`; kept `find_missing_mbids()` as the JSON/error-string compatibility adapter and added direct-import regressions. All four required workflows passed on the exact head: syntax `38827001217`, full suite/build `38827001215`, runtime smoke `38827001195`, validation-only multi-architecture `38827001227`.
- **PR #171 — Recommendation style rules:** tested head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9`; squash merge `6d00562405320affcb1a04b4359397b332cd5bf5`. Moved pure genre-family, recent-style-family, primary-family, and regional diversity-style classification helpers into `discovery_recommendations.py`. An initial CI run caught an incorrect test fixture; the fixture was corrected and all four workflows passed on the final exact head: syntax `38827709662`, full suite/build `38827709650` (319 tests passed), runtime smoke `38827709649`, validation-only multi-architecture `38827709610`.
- **PR #172 — Last.fm album popularity:** tested head `d2808d44825e949ff71ed8471d25cee6570b54f1`; squash merge `d5153a3fe0625bc52b5896e87846b55cabe58e81`. Moved cached `album.getInfo` retrieval, parsing, and diagnostics into `LastFmClient.album_popularity()`; retained `_lastfm_album_popularity()` as the compatibility adapter, including the legacy cache key, 30-day TTL, 12-second timeout, response shape, error messages, and silent 404 handling. An initial CI run caught a test-fixture logging issue; after correction all four workflows passed on the final exact head: syntax `38827973048`, full suite/build `38827972941` (324 tests passed), runtime smoke `38827972940`, validation-only multi-architecture `38827972938`.
- Each extraction was reviewed sequentially against refreshed GitHub `main`; all final-head CI gates passed. Assistant-side local test execution was not performed. These backend-only changes did not require manual browser checks. No image publication, deployment, or production runtime verification is claimed.
- Only PR #23 remains open as the modularization roadmap. PRs #44 and #45 remain closed. Per the user's explicit direction, the currently unreproducible acquisition-dismissal HTTP 409 investigation remains deferred until modularization is complete; no fix is claimed and cleanup safety checks were not weakened.
- Next action: inspect the refreshed roadmap and current `main` for the next small, independent extraction. Keep the 409 investigation deferred as directed and keep publishing paused.

---

## 2026-10-16 — Listening profile aggregation extraction completed (PR #167)

- Branch `refactor/extract-listening-profile`; exact tested head `ca8f9e4b7decb3404c78f1ee8b8d3078815fd71f`; squash merge `6b656dc7218280aa0d37e738a881061ceefde55e`.
- Extracted pure ListenBrainz listening-history aggregation into `listening_profile.py`; retained `recent_listening_profile(days)` as the compatibility/MCP adapter for validation, provider retrieval/error mapping, and JSON serialization.
- Added direct-import tests for payload shape, artist/album counts, empty history, and tie ordering; included the module in Docker packaging.
- All four required workflows passed on the exact final head: syntax `38825137244`; Docker packaging/full unit suite/image build `38825137296`; runtime smoke `38825137346`; validation-only multi-architecture validation `38825137280`. The full unit suite passed in CI. Assistant-side local tests were not run.
- No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — Discovery library snapshot extraction completed (PR #168)

- Branch `refactor/extract-discovery-library-snapshot`; exact tested head `fc69943301c5065a54a0128c8b82ae214cd69dd1`; squash merge `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`.
- Extracted cached Navidrome artist/album inventory assembly into `discovery_library_snapshot.py`, preserving `_discovery_library_snapshot()` as the compatibility adapter.
- Direct-import tests cover cache reuse, outdated cache schema, album ID deduplication, inventory shape/pagination, and safety-limit refusal. Docker packaging was updated.
- All four required workflows passed on the exact final head: syntax `38825386951`; Docker packaging/full unit suite/image build `38825387005`; runtime smoke `38825386785`; validation-only multi-architecture validation `38825386797`. The full unit suite passed in CI. Assistant-side local tests were not run.
- No image publication, deployment, or production runtime verification is claimed. PR #44 and #45 are closed as requested; the HTTP 409 investigation remains deferred until it recurs. PR #23 remains open as the modularization roadmap.

---

## 2026-10-16 — Multi-extraction session closeout

- Starting main SHA: `8dbb1e3125d2422e69bb30fa7ecb5bebdf652eed`. Final main SHA after two sequential extractions: `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`.
- PR #167 extracted ListenBrainz listening-profile aggregation; exact tested head `ca8f9e4b7decb3404c78f1ee8b8d3078815fd71f`; merge `6b656dc7218280aa0d37e738a881061ceefde55e`. All four required workflows passed: syntax `38825137244`, full suite/build `38825137296`, runtime smoke `38825137346`, validation-only multi-architecture `38825137280`.
- PR #168 extracted cached Navidrome library snapshot assembly; exact tested head `fc69943301c5065a54a0128c8b82ae214cd69dd1`; merge `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`. All four required workflows passed: syntax `38825386951`, full suite/build `38825387005`, runtime smoke `38825386785`, validation-only multi-architecture `38825386797`.
- Both PRs retained compatibility adapters, added direct-import regressions, and updated Docker packaging. Assistant-side local tests were not run. Publishing/deployment/runtime verification remain separate and unclaimed.
- Only PR #23 remains open; it is the modularization roadmap. PRs #44 and #45 are closed per the user's direction. The dismissal HTTP 409 investigation remains deferred until it recurs.
- Next action: continue selecting the next smallest low-coupling application-assembly/domain-service seam from current main, after verifying the documentation closeout PR.

---

## 2026-10-16 — Multi-extraction session closeout (three backend PRs merged)

- Session base: GitHub `main` at `383228e333b1222bb2696b1514f9584ea60d0654`; final code main after the three merges: `a0cd3d8ff5dcdf6acb7d678c9fc8f1aa0d537629`.
- PR #163, ListenBrainz HTTP client: tested head `4c494a2679884579df5d6bc204287637e45e2ccd`; all four required workflows passed (compile `38822823853`, unit suite/Docker build `38822823922`, container smoke `38822823751`, non-publishing multi-architecture validation `38822823989`); merge `7be68c74b8a97ed4d9c50e6a7e22e296b25e79e2`.
- PR #164, cached/rate-limited Last.fm client: tested head `957f3a56afe15e4dd665b041f1fbf7803921d3b6`; all four required workflows passed (compile `38823469617`, unit suite/Docker build `38823470035`, container smoke `38823469896`, non-publishing multi-architecture validation `38823469762`); merge `9f174c6086c0d2b9749e53e38cbe8e1eb337e22f`.
- PR #165, cached MusicBrainz rating client: tested head `4888bd08fdf05007cc74ad7005a196fd678305b5`; all four required workflows passed (compile `38823643925`, unit suite/Docker build `38823643703`, container smoke `38823643931`, non-publishing multi-architecture validation `38823643848`); merge `a0cd3d8ff5dcdf6acb7d678c9fc8f1aa0d537629`.
- Each extraction retained the prior `navidrome_server.py` adapter and added deterministic direct-import and adapter regression tests. Docker packaging includes all three modules. CI's full unit suite passed on each exact final PR head. Assistant-side local test commands were not run. These were backend-only changes, so no manual browser checks were required.
- The code changes are implemented, CI-tested, and merged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Open PRs after the session: #23 documentation/modularization plan, #44 draft acquisition dismissal diagnostics, and #45 deferral note for the dismissal HTTP 409 investigation.
- Next action: prioritize the outstanding acquisition dismissal 409 safety/diagnostic gap and its verification state before routine extraction; continue to treat it as unresolved unless reproduced and root-caused.

---

## 2026-10-16 — Acquisition Get/request and Dismiss regression coverage (in progress)

- Branch: test/acquisition-get-dismiss-regressions, based on current GitHub main after the verification-audit follow-up.
- Added tests/test_acquisition_ui_contract.py to guard Get request count/no-navigation, pending/requested/retryable states, server-declared failure handling, and Dismiss visibility/removal/error handling. Extended tests/test_acquisition_routes.py with Dismiss success mapping and missing-identity rejection.
- Filesystem safety implementation is unchanged. Existing tests/test_acquisition_cleanup.py remains in the required focused/full suite and covers traversal, symlink and race refusal, ambiguous targets, unexpected contents, and preservation of neighboring files.
- UI automation currently asserts source-level contracts; it does not run a browser. Focused tests, full suite, all four exact-final-head workflows, and the required manual browser checklist are pending. No production filesystem or live slskd operations are used by the new UI tests.
- The acquisition dismissal HTTP 409 investigation remains deferred unless it recurs. This task does not claim to fix that issue. Publishing/deployment remain paused and unverified.

---

## 2026-10-15 — PR #160 merged: discovery refresh orchestration extraction

- PR: https://github.com/abucalip/navi-librarian/pull/160. Exact tested head: `5aafc1a9c5835e2d9e2959a36e7419d09913403a`; squash merge commit: `dba172d5747607e65e8fadd32442b12d32054749`.
- Extracted ordered refresh-all orchestration into `discovery_refresh.refresh_all`; retained `navidrome_server._discovery_refresh_all()` as the compatibility adapter.
- Added regression coverage for callback order, personal count (20), and returned results. The existing module packaging was unchanged.
- All four required workflows passed on the exact PR head: Python syntax `38818349092`, Docker packaging/full unit suite/image build `38818349082`, container runtime smoke `38818349397`, and validation-only Docker/multi-architecture validation `38818349076`.
- MCP registrations, signatures, names, response shapes, provider calls, lock ownership, and persistence behavior remain unchanged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #156 merged: footer landmark and reading-order fix

- PR: https://github.com/abucalip/navi-librarian/pull/156. Tested head: `47d33cbecadf64ed4b434764883cec6ae99d30bc`; squash merge: `c560c28063f26a1a72d7016c951bf265d2ddd158`.
- All four required workflows passed on the exact tested head: Python syntax `38815023255`; Docker packaging `38815023085`; isolated container runtime smoke `38815023444`; validation-only Docker image/multi-architecture validation `38815023661` (publishing paused).
- Manual browser checklist report was published in PR #156 by the user for that exact head. All eight checklist items passed; zero failures. The report records browser checks across eight routes and widths 1440/1200/1100/900/760/620/390/360px, with no overflow, console errors, or page errors.
- Fix moved `<footer>` outside `<main>`, making `contentinfo` a landmark and keeping footer order below content on all eight routes. No CSS change was needed.
- Limitations/backlog: no real screen reader was tested; the missing skip link remains separately documented in `docs/UI_BACKLOG_EXECUTION.md`. No publishing, deployment, or production runtime verification is claimed.
- Next action: re-check current GitHub main, open PRs and CI; choose the highest-priority remaining safety/verification gap before routine modularization.

---

## 2026-10-15 — Backend session closeout: PRs #155 and #157 merged

- PR #155 extracted expected slskd track-count metadata into `slskd_search.py`; exact tested head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`; squash merge `d732241de9edfd3c643a8fa89fb25c42b2a93c67`.
- PR #157 extracted slskd transfer listing/normalization into `slskd_transfers.py`; legacy `_slskd_download_transfer_files` remains the adapter. Exact tested head `504b10392061dbc44d28d66e663b88cbefb8f1a4`; squash merge `17922f878f0ea391b47652012a38530e9eb044fc`.
- All four required workflows passed on PR #157's exact final head: syntax/acquisition safety `38816375215`, Docker packaging/full unit suite/image build `38816375266`, isolated runtime smoke `38816375339`, and validation-only multi-architecture validation `38816375410`.
- A packaging-only commit `08c0703ed1dea19eae1aa84f8a18b4a3ea8f8666` had added the module to Docker COPY before the module was merged. PR #157 supplied the missing module and tests; current `main` now contains both the Docker reference and module. The packaging gap is resolved and verified by the final Docker build.
- At the time of this historical closeout, PR #156's manual browser checklist was still recorded as NOT RUN. It was subsequently completed and published for exact head `47d33cbecadf64ed4b434764883cec6ae99d30bc`; PR #156 merged at `c560c28063f26a1a72d7016c951bf265d2ddd158`. See the newer PR #156 closeout entry above.
- Publishing remains paused. No image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #155 merged: expected slskd track count

- Extracted expected track-count metadata parsing into `slskd_search.py`; retained `navidrome_server._discovery_expected_track_count` as the compatibility adapter.
- PR #155: https://github.com/abucalip/navi-librarian/pull/155. Exact tested head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`; squash merge `d732241de9edfd3c643a8fa89fb25c42b2a93c67`.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety `38814733899`, Docker packaging/full unit suite/image build `38814734001`, isolated runtime smoke `38814733916`, and validation-only multi-architecture validation `38814733954`.
- Publishing remains paused. No deployment or production runtime verification is claimed.

## 2026-10-15 — Historical closeout: PR #154 and PR #149 merged

- PR #154 merged at b547ff5c647d8bacd8bf17fd6cd760dc9c41980a from tested head 6de27ec137e9f859424eca0928fca25500852471. All four required workflows passed on that exact head.
- PR #149 was subsequently brought current, manually tested, and merged. Its recommendation-count accessibility fix is recorded by merge commit f3ac971e6c04b9c9caa8d4d20f50d0c25302556e; closeout commits ecf0a607394a7e9209ebf76ce29ef8c2f496bcc7 and 463f27ea06ca33f06cc1b32798f3019901322075 follow it. The earlier warning below is historical and superseded.
- Publishing remains paused. No deployment or production runtime verification is claimed.

---

## 2026-10-15 — PR #151 merged: music path default policy extraction

- PR: https://github.com/abucalip/navi-librarian/pull/151. Tested head: `07cf1ab7dab46a1409236f7134881011dc31cac2`; squash merge commit: `6a7678bd04ef539ae5f4c118b6707524fd569280`.
- Extracted environment override and host mount fallback into pure `music_paths.py`, preserving `navidrome_server._default_music_dir()` and `MUSIC_DIR` initialization. Added direct-import regression tests and Docker packaging.
- All four required exact-head workflows passed: Python syntax and acquisition safety regressions `38805068326`; Docker packaging, full unit suite, and image build `38805068317`; container runtime smoke `38805068315`; validation-only multi-architecture image build `38805068337`.
- State: implemented, CI passed, merged. Publishing remains paused; no deployment or production runtime verification is claimed.
- Next: review current main and open PRs before selecting the next smallest application-assembly/domain-service dependency.

## 2026-10-15 — PR #150 merged: Navidrome API client extraction

- PR: https://github.com/abucalip/navi-librarian/pull/150. Tested PR head: `be9a2558bd87eb8e7e2fbf25593936aa8c671a1a`; squash merge commit: `efc2acb93e3edb570e77419daa866f4a228c85d2`.
- Extracted Subsonic-compatible authentication, HTTP request execution, and API error interpretation into `navidrome_client.py`. The legacy `navidrome_server.api_call(method, **params)` remains as a compatibility adapter; Docker packaging and direct-import regression tests were updated.
- All four required workflows passed on the exact final PR head: Python syntax `38802307579`, Docker packaging/full unit suite/build `38802307812`, container runtime smoke `38802307700`, and validation-only multi-architecture image validation `38802307683`.
- State: implemented, tested, CI passed, merged. Image publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next: continue with the smallest remaining application-assembly/domain-service boundary after reviewing current main and open PRs; preserve the legacy MCP interface until retirement is separately justified and verified.

## 2026-10-15 — Navidrome API client extraction: pre-merge record

- Branch: `refactor/extract-navidrome-api-client`. Extracted Subsonic-compatible HTTP transport/authentication into `navidrome_client.py`; `navidrome_server.api_call(method, **params)` remains a compatibility adapter using the existing `_navidrome_config` provider.
- Added direct-import unit tests for token construction, request URL/options/query parameters, successful responses, and legacy API-error messages. Added the module to Docker packaging.
- Initial exact implementation head `555da7027ae0aa9f636ba66e18b33d549cd787d6` passed all four required workflows: Python syntax `38802076122`, Docker packaging/full unit suite `38802076327`, container runtime smoke `38802076229`, and validation-only multi-architecture image validation `38802076245`. The documentation follow-up changes the PR head; all four workflows must be rechecked on that final head before merge.
- This is an implementation PR only. Merge, publication, deployment, and production runtime verification are pending and separate.

## 2026-10-15 — PR #148 merged

- Merged metadata-cache service extraction to `main` via squash merge commit `99e8da326fb0e2c4a8cf22acf9000e28647ec20f` (PR head `972376953444502fb1a372648adc8c58157403c9`).
- All four required PR-head workflows passed on the exact final head: Python syntax/acquisition safety, Docker packaging and full unit suite, isolated container runtime smoke, and validation-only multi-architecture Docker build.
- Publishing remains paused; no image publication, deployment, or production runtime verification is claimed. Next modularization step: inspect remaining application-assembly and domain-service dependencies in `navidrome_server.py` and choose the smallest seam consistent with the roadmap.

## 2026-10-15 — Metadata cache extraction CI follow-up

- Initial PR-head CI exposed a regression-test fixture issue: the malformed-JSON test inserted directly before creating the cache table. The fixture now initializes the table through the public cache service before inserting malformed JSON.
- Corrected test commit: d6e28b665a3b16cbd3aba68744e1943a73d1cda1. All required workflows must be rechecked on this exact updated head; the initial failed run is not evidence of a passing suite.

## 2026-10-15 — Metadata cache service extraction in progress

- The persistent MusicBrainz metadata cache is being moved behind metadata_cache.py with an injected database path and clock. navidrome_server.py retains _metadata_cache_get / _metadata_cache_set compatibility adapters and the existing SQLite filename and non-fatal cache-failure behavior.
- Direct-import regressions cover Unicode JSON round-trips, missing/expired entries, malformed cached JSON, and storage errors. Docker packaging includes the new module.
- Branch: refactor/extract-metadata-cache. CI, merge, publication, deployment, and runtime verification are pending; do not infer them from the code or documentation changes.

## 2026-10-15 — PR #147 merged: strict slskd settings boolean validation

- PR: https://github.com/abucalip/navi-librarian/pull/147
- Tested PR head: `22db7e7b4414f1ff3df7440bc47aece41bf0ae1d`
- Squash merge commit: `9ce0ae37ae207f79180d98b10f71147736fe2a75`
- Root cause: the slskd settings HTTP route ignored `auto_acquire_for_me`; forwarding without type validation would allow truthiness coercion (for example, `"false"` becoming true).
- Fix: validate supplied values as JSON booleans, return HTTP 400 for invalid types, forward explicit booleans, and preserve omitted settings. Regression tests cover true/false and rejected string, number, null, list, and object inputs.
- Exact PR-head CI: Python syntax check, container runtime smoke test, Docker packaging validation, and Docker image validation all completed successfully. Image publishing remains paused by workflow configuration.
- State: implemented, tested, CI passed, merged. Publication, deployment, and production runtime verification were not part of this task and are not claimed.

## 2026-10-15 — PR in progress: strict slskd auto-acquire settings validation

- Backend audit found `PUT /api/settings/slskd` did not forward `auto_acquire_for_me` to the service. If it were forwarded without type validation, the service's boolean coercion would treat strings such as `"false"` as true.
- The focused fix validates a supplied value as a JSON boolean, returns HTTP 400 for strings/numbers/null/containers, and forwards explicit true/false while leaving an omitted value unchanged.
- Regression tests cover invalid values and both valid booleans. Exact-head CI and full-suite results are pending; no merge, publication, deployment, or runtime verification is claimed.

## 2026-10-15 — PR #142 merged after conflict resolution

- PR #142, “fix: raise --subtle to meet WCAG AA contrast,” was rebased by preserving both parent histories in a merge-resolution commit and integrating the contrast changes with the already-merged PR #144 landmark accessibility changes. Resolved head: `dd5561bff2ca8b89ca934a60f8348e67a044093c`; squash merge: `77faf5e03fdc4985541b0da5952568d0925336df`.
- The resolved tree preserves PR #144’s landmark documentation and keeps `--subtle: #94958b` plus its measured-contrast rationale. PR #142 is closed and merged.
- All four required workflows passed on the exact resolved PR head: Docker packaging `38794146977`; validation-only multi-architecture image build (publishing paused) `38794146985`; Python syntax `38794147000`; container runtime smoke `38794146979`.
- Manual browser reports exist for the original contrast head `38addc52dfb14ccbf95a72ffad2dbd0713d9fcf9` and PR #144’s separately tested head `4b44cdb98485a93ba86ac102f29081b917d4e4fe`. The combined conflict-resolution head was not manually retested as one combined revision; no new visual result is claimed.
- Publishing/deployment remain paused. No production runtime verification is claimed.


## 2026-10-15 — PR #143 merged: settings persistence extraction

- PR #143: https://github.com/abucalip/navi-librarian/pull/143. Exact final PR head `e28cd12d3736fd2eb368b53c98e3cbddb5438166`; squash merge `409f634a20ba67c5a39dfec0e5bf57995a3fefbe`.
- Extracted SQLite settings initialization, restrictive file permissions, reads/writes, saved music-path application, and legacy quality/download-path migrations into `settings_persistence.py`. The legacy `_discovery_settings_*` wrappers remain in `navidrome_server.py`; service and MCP-facing interfaces are preserved. Docker packaging includes the module.
- Added direct-import regression tests for Unicode persistence, malformed JSON fallback, append-only quality-tier migration, music-path application, and restrictive database permissions. Corrected the AST-based quality-priority test fixture to inject the extracted persistence dependency.
- All four required workflows passed on the exact final PR head: Docker packaging/full tests/build `38791730058`, Python syntax `38791730078`, container runtime smoke `38791729963`, and validation-only multi-architecture image validation `38791730017`. Publishing remains paused.
- No separate local test run, image publication, deployment, or production runtime verification is claimed. Next: continue reviewing remaining application-assembly/domain-service seams against the roadmap and higher-priority verification gaps.

## 2026-10-15 — MCP tool registration separated from shared service imports

- Moved the 27 existing MCP tool registrations into the new mcp_registry.py; navidrome_server.py no longer imports MCPServer, constructs an MCP server, or decorates service functions at import time.
- The legacy MCP entry point remains compatible: when navidrome_server.py is executed directly, it creates the server through create_mcp_server() and runs on the existing streamable HTTP host/port. Tool names and function objects are kept in an explicit ordered registry.
- The web service can now import navidrome_server.py without loading mcp.server.mcpserver. MCP registration is deferred to explicit server startup; the MCP package and legacy tool surface are retained.
- Added tests/test_mcp_registry.py to assert the registry contains 27 unique tools, registers each provided function exactly once, and importing the legacy service keeps all registered functions callable without importing the MCP SDK.
- Branch: refactor/separate-mcp-tool-registration. All four required workflows passed on exact implementation/documentation head fe71a9a19188a018a2ee65d5b313a99413d239f2: Python syntax/acquisition safety run 38783091362; Docker packaging/full suite/build run 38783091326; container runtime smoke run 38783091309; validation-only multi-architecture run 38783091337. Publishing remains paused. No separate local test execution, deployment, or production runtime verification is claimed. PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00 from exact final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f. All four required workflows passed on that exact head: syntax/acquisition safety 38783296279; Docker packaging/full suite/build 38783296173; container runtime smoke 38783296256; validation-only multi-architecture 38783296249. Publishing/deployment remain paused; no production runtime verification is claimed.

## 2026-10-15 — PR #137 merged: authentication signing-key symlink safety

- PR #137: https://github.com/abucalip/navi-librarian/pull/137. Exact PR head `f6458af4b84b957902a2da1960cdafc06d0f7594`; squash merge `d7b75567ce8d3729c1ed92f091e89a794fff2341`.
- Fixed `load_auth_secret()` following an existing `app_auth.key` symlink and potentially changing its target permissions. Existing keys are opened with `O_NOFOLLOW`, verified as regular files through `fstat`, and permission tightening uses the open descriptor. Added regression coverage for refusal without modifying target bytes or mode.
- All four required workflows on the exact final PR head succeeded: Python syntax, Docker packaging (including full unit suite/build), container runtime smoke, and validation-only multi-architecture image build (publishing paused). No separate local test execution, image publication, deployment, or production runtime verification is claimed.
- Next backend priority: continue safety and verification audit before routine modularization; preserve evidence-first handling for any recurrence of acquisition dismissal HTTP 409.

---

## 2026-10-15 — Authentication signing-key symlink hardening in review

- Safety audit found `load_auth_secret()` followed an existing `app_auth.key` symlink and could read the target and change its permissions. Added a regression that requires symlink refusal and verifies the target content and mode remain unchanged; the test was committed before the implementation change.
- Implementation opens an existing key with `O_NOFOLLOW`, verifies the opened object is a regular file, and uses descriptor-based permission tightening. Failure remains closed with a generic invalid-key error.
- Branch `fix/auth-key-symlink-safety`; exact-head CI and full-suite results are pending. No local tests, merge, publication, deployment, or runtime verification are claimed.

---

## 2026-10-15 — PR #136 merged: acquisition monitor payload preparation

- PR: https://github.com/abucalip/navi-librarian/pull/136; final head: `c963bb6a1510d86ebb2cfe5bb9514fccbc478efa`; squash merge: `5f28823d0c279d49947912f9fbce0a160a7a5bc3`.
- Extracted selected/fallback candidate payload normalization into `acquisition_monitor_payload.py`; direct-import tests cover file-record shape, quality-summary defaults, fallback metadata preservation, and input immutability. Docker packaging includes the module.
- All four required workflows associated with the exact final PR head succeeded: Python syntax, Docker packaging/full unit suite/build, container runtime smoke, and validation-only multi-architecture image validation (publishing paused). No separate local test run, image publication, deployment, or production runtime verification is claimed.
- Next backend priority: continue the safety/verification audit before routine modularization. Keep the acquisition-dismissal HTTP 409 investigation deferred unless it recurs; if it recurs, capture the refusal stage and evidence before changing cleanup behavior. Review the still-open diagnostic/defer PRs (#44/#45) as part of that follow-up.

---

## 2026-10-15 — Acquisition monitor payload extraction (PR preparation)

- Modularization seam: extracted the repeated construction of selected/fallback source payloads passed to the acquisition import watcher into `acquisition_monitor_payload.py`.
- Added direct-import regression coverage for minimal filename/size records, quality-summary normalization, fallback metadata preservation, and input immutability. The legacy MCP adapter, shared locks, watcher lifecycle, queue/fallback decisions, and persisted acquisition state remain unchanged.
- Docker packaging includes the new module.
- Exact PR head `f3d444fce0902637d394b48680e4274e2b513f6f` passed all four required workflows: Python syntax `38780380213`, Docker packaging/full unit suite/build `38780380196`, container runtime smoke `38780380199`, and validation-only multi-architecture image validation `38780380566` (publishing paused).
- This verifies the listed checks on that head only. No local test execution, merge, image publication, deployment, or production runtime verification is claimed.
- Before merge, re-run all four required workflows on the final PR head after documentation updates and review the complete diff.

---

## 2026-10-15 — PR #134: concurrent login rate-limit race

- PR: https://github.com/abucalip/navi-librarian/pull/134
- Authentication boundary audit found that simultaneous login requests could pass the per-client attempt-count check before either failed request recorded its timestamp.
- Added a deterministic integration regression before implementation. It blocks the first password-digest call after the final available slot is reserved, then verifies the concurrent request receives HTTP 429 while the in-flight invalid login receives HTTP 401.
- Implementation adds a dedicated lock and atomically reserves attempt slots before password verification; successful authentication clears the client's attempt bucket under the same lock. Expensive password verification remains outside the lock.
- Regression-first test commit: `d829d6450ac39257a0177cf768e70a3de8937e7a`; implementation commit: `e7ff4b454d9478d4ca147913d356db545bfb2fed`.
- The final PR head `a15fa4e9b588e7fa96d36242f51b55b23fba9e70` passed all four required workflows: Python syntax `38776917077`, Docker packaging/test-and-build `38776916979`, container runtime smoke `38776917024`, and Docker image validation `38776917027` (publishing paused).
- PR #134 was squash-merged to `main` at `ef6ce0ff4faa9fffca66a7e43294eee6a0847dbd`. No local test execution is claimed. Image publication, deployment, and production runtime verification remain separate and paused.

---

## 2026-10-15 — PR #133 merged: malformed authentication session tokens

- PR: https://github.com/abucalip/navi-librarian/pull/133
- Found and fixed a correctness gap where a non-ASCII untrusted session-token segment could raise `UnicodeEncodeError` before the authentication parser's exception guard. Added the regression test before changing implementation; malformed/non-string tokens now fail closed.
- Exact tested PR head: `60df367eb4004fe439d1abcd61957c5986111b90`. All four required workflows passed on that exact SHA: container runtime smoke `38775004963`, Docker image validation (publishing paused) `38775004827`, Python syntax `38775004824`, and Docker packaging/test-and-build `38775004877`.
- Squash merge: `ae49bacf3c793fac70688f55c2d1d7c9ed54cc13`. Post-merge workflows were queued at closeout; merge does not imply those checks have completed.
- Status: implemented, regression added first, exact-head CI passed, merged. No local test run, image publication, deployment, or production runtime verification is claimed.
- Next: continue the backend safety/verification audit before routine modularization.

---

## 2026-10-15 — PR #131 merged: Get/request state reporting

- PR #131 merged to `main` by squash at `5fafad0b5a2d94ef2473c0a7c121d647cf8bdc76`, from tested head `7eb009c92821b6eb9dfb33326e7dfc3d81fd7244`.
- Consolidated the modal, artwork-overlay, and card-action Get/request controls. Fixed swallowed acquisition outcomes, premature requested-state reporting, and HTTP 200 responses with `ok: false`; API payload and acquisition semantics remain unchanged.
- Exact-head CI passed: Python syntax `38763416411`, Docker packaging `38763416267`, container runtime smoke `38763416429`, and Docker image validation with publishing paused `38763416356`.
- Manual report published on PR #131: https://github.com/abucalip/navi-librarian/pull/131#issuecomment-6196528875. All eight checklist items passed on the exact tested head, including Get/request behavior without starting a real download.
- Status: implemented, tested, CI passed, manually verified, merged. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-15 — PR #128 merged: acquisition status layout

- PR #128 (https://github.com/abucalip/navi-librarian/pull/128) merged to `main` at `424929410b0324313e9aee5e59da73803d4b32bb`, from exact final PR head `653984684be4e2da28e6de6955b43299143f1141`.
- Acquisition cards now use a wider status-board composition rather than the shared four-column artwork grid; discovery layouts and acquisition behavior/API semantics are unchanged.
- Manual browser report: https://github.com/abucalip/navi-librarian/pull/128#issuecomment-6195576007. All eight checklist items passed on the pre-documentation-fix UI commit `4b2d30a510d5b850be25e059641eee29d9d7dde9`; the only subsequent change on the PR branch was documentation reconciliation.
- All four required workflows passed on final PR head `653984684be4e2da28e6de6955b43299143f1141`: Python syntax run `38760144749`, container runtime smoke `38760144797`, Docker packaging `38760144678`, and Docker image validation with publishing paused `38760144644`.
- Image publication, deployment, and production runtime verification were not performed. The PR also reconciles `docs/UI_BACKLOG_EXECUTION.md` with the withdrawn keyboard-focus finding; acquisition is the first completed section under per-section layouts, with artist exploration, library, and settings still candidates.

## 2026-10-15 — PR #126 merged: `auto_queue` API input validation

- Identified a correctness issue in `POST /api/acquire`: Python truthiness conversion treated values such as the JSON string `"false"` and number `0` as booleans, potentially requesting unintended queue behavior.
- The focused fix validates that `auto_queue` is a JSON boolean before invoking the shared librarian service; omitted values still default to `true`, and explicit `false` is preserved.
- Added route regressions for explicit false and invalid strings, numbers, null, lists, and objects; invalid inputs must return HTTP 400 without calling the service.
- Implementation branch: `fix/acquire-auto-queue-boolean-validation`. Final PR head `a67be60e8f35a3a6e9430ac3ad30700532d958cc` passed all four required exact-head workflows: Python syntax `38756653450`, Docker packaging/full suite/build `38756653379`, container runtime smoke `38756653406`, and validation-only multi-architecture image validation `38756653398`. PR #126 merged by squash at `3b3a9d47538d51820b6ce162f524812d0800f3c1`. No separate local test run, image publication, deployment, or production runtime verification is claimed. No local test run, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #124 merged: shared UI status states

- PR #124 (https://github.com/abucalip/navi-librarian/pull/124) merged by squash at `9a3aa7bd295de0de7d9408b01db22ab700e4d101`, from exact tested head `28e5a88ae362043171aaabb1f8667f6cf5ef10f7`.
- Standardized loading, empty, error, success, progress, and neutral status text using the existing design tokens and state glyphs; applied `aria-live` to dynamically updated status regions. No API, authentication, acquisition, or domain behavior changed.
- The published local manual report on PR #124 records all eight checklist items as PASS on the exact tested SHA, including first-run setup, dashboard/artwork, discovery, navigation/album details, settings secret handling, Get/request without a real download, acquisition cards, and no unexpected browser/server errors. Report: https://github.com/abucalip/navi-librarian/pull/124#issuecomment-6194989181.
- All four required GitHub Actions workflows passed on the exact PR head: Python syntax `38753222840`, container runtime smoke `38753222934`, Docker packaging `38753222902`, and validation-only image validation `38753222878` (publishing paused).
- A separate keyboard-focus reach issue was observed during verification (25 Tab presses reached only three dashboard controls); it remains unfixed and should be tracked as a focused UI follow-up by the front-end owner. The state-classifier remains heuristic.
- State: implemented, automated CI passed, manual browser checklist passed and report published, merged. No image publication, deployment, or production runtime verification is claimed.
- Next: prioritize the documented keyboard-focus reach defect for front-end follow-up; continue to keep publication/deployment as separate gates.

---

## 2026-10-15 — PR #116 merged: Proxmox MCP SDK compatibility and handler regression

- PR #116 merged at `9e6979203cbdb6f2d38225584952136170eb2df5` from exact tested PR head `a14accac574d1997e6785ffbf170be136b95c5b9`.
- Corrected the host-side entry point to use `mcp.server.mcpserver.MCPServer`, matching pinned `mcp==2.3.0` and the main MCP server. MCP startup now occurs only when `server.py` is executed as a script.
- Added handler regressions proving rejected shell-composed commands never invoke SSH, accepted commands retain the existing SSH argument/timeout/output behavior, and output remains capped at 20,000 characters.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety `38742736856`; Docker packaging/full suite/build `38742737079` (243 tests passed); container runtime smoke `38742737082`; validation-only multi-architecture image validation `38742736770`.
- An earlier CI cycle exposed the stale FastMCP import; the defect was corrected and all four workflows passed on the final head. No local test run or live Proxmox command, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #114 merged: Proxmox MCP command allowlist

- **Finding/fix:** the separate host-side `server.py` MCP described `run(command)` as allowlisted but forwarded arbitrary text to SSH. Added `read_only_command_policy.py` with exact-match allowlisting for the documented diagnostic forms; arbitrary commands, shell composition, substitutions, newlines, and unsafe arguments are refused before SSH invocation.
- **Regression coverage:** direct-import tests cover permitted diagnostic commands, arbitrary command refusal, shell operators/substitution/newlines, container IDs, device paths, and non-string input.
- **PR:** https://github.com/abucalip/navi-librarian/pull/114; exact tested PR head `cd8319696180875a3cb6f0dc151d88e0c8c490d7`; squash merge `6ab848d444373dfa37e6d46528a2840a53a8f763`.
- **Exact-head CI:** Python syntax `38740491280`; Docker packaging/full unit suite/build `38740491274`; container runtime smoke `38740491268`; validation-only multi-architecture image validation `38740491281` — all passed on the exact PR head.
- **Limits:** no local test execution or live Proxmox command. Root-level host-side `server.py` is not copied into the Librarian application Docker image; no publication, deployment, or production runtime verification occurred.
- **Next:** continue the highest-priority safety/verification audit before routine modularization. Keep the acquisition-dismissal HTTP 409 investigation deferred unless the user reports recurrence.


---

## 2026-10-15 — PR #108 merged: discovery router service injection

- **PR:** https://github.com/abucalip/navi-librarian/pull/108; exact tested head `a5170e50080c0ca94b4068155ace83fd33c6f029`; squash merge `be51f0ce17fe8eccd1b57714e869db69a5f1ba78`.
- **Change:** discovery routes use the shared lazy `get_librarian` FastAPI dependency instead of importing `navidrome_server` at module load. Domain calls, route paths, validation, response parsing, candidate filtering, feedback persistence, and HTTP error mapping remain in the existing service boundary.
- **Regression coverage:** direct-import tests exercise fake-service injection for recommendations (including candidate filtering), list retrieval, refresh, feedback, and validation. Updated the pre-existing discovery route tests to pass explicit fake services instead of patching the removed `discovery.librarian` module attribute.
- **Exact-head CI:** all four required workflows passed on `a5170e50080c0ca94b4068155ace83fd33c6f029`: Python syntax/acquisition safety `38733725606`; Docker packaging/full unit suite/build `38733725816` (227 tests passed); container runtime smoke `38733725595`; validation-only multi-architecture image validation `38733725591`.
- **State:** implemented, tested, all required CI passed, merged. No local test run, image publication, deployment, or production runtime verification is claimed. Publishing remains paused.
- **Next:** continue the service-boundary audit with the next narrow route extraction only after checking current roadmap and higher-priority safety/test gaps.

---

## 2026-10-15 — PR #107 merged: acquisition router service injection

- **PR:** https://github.com/abucalip/navi-librarian/pull/107; final tested PR head `67174e8026f44382a4a6bea48ff1df80744dda35`; squash merge / main SHA at closeout `1cc15dd6343370ce0915bf7228a745d3558b393b`.
- **Change:** added `app/api/dependencies.py` with lazy `get_librarian()` and injected it into all acquisition routes. This removes the acquisition router's import-time import of `navidrome_server` while preserving endpoint paths/methods, existing service calls, payload mapping, HTTP error behavior, and SSE response headers. Added regression tests for route contracts, dependency wiring, fake-service handler calls, validation, and sanitized errors.
- **Exact-head CI:** all four required workflows passed on `67174e8026f44382a4a6bea48ff1df80744dda35`: Python syntax `38732084595`; Docker packaging/full unit suite `38732084663`; container runtime smoke `38732084579`; validation-only multi-architecture image build `38732084589`. An earlier test-only assertion failure on `d6a1696c06f594e2c4025e0eff54bb8496fd8e29` was corrected before these passing runs.
- **Status:** Implemented, tested, CI passed, merged. Publishing remains paused; this did not publish an image, deploy the application, or verify production runtime. `app/main.py`, discovery, and settings still import `navidrome_server`; MCP tools and domain logic were not removed or duplicated.
- **Next priority:** continue the narrow web service-injection audit at the discovery router, preserving API behavior and MCP compatibility. Keep deployment/runtime verification as a separate gate; do not resume routine modularization if a higher-priority safety or delivery gap appears.

---

## 2026-10-15 — Read-only web dependency audit completed

- Before any MCP retirement, the FastAPI app still imports `navidrome_server` directly from `app/main.py`, `app/api/acquisitions.py`, `app/api/discovery.py`, and `app/api/settings.py`.
- The main app uses server-owned data/settings, Navidrome ping, discovery-list, and album-candidate helpers. The route modules are thin adapters around existing `discovery_*` service functions; they do not duplicate the domain logic. `app/api/metadata.py`, `app/api/auth.py`, and `app/security/auth.py` do not directly import the server; auth routes already receive dependencies through a router factory.
- Existing route tests patch module-level `librarian` references and verify endpoint contracts. A future injection seam must preserve paths/methods, payload mapping, error/status mapping, streaming, persistence, and MCP compatibility. No code changes were made during this read-only audit.
- PRs #44/#45 remain open. The documented decision to defer the HTTP 409 investigation until it recurs is unchanged.

---

## 2026-10-15 — PR #103 merged: acquisition import source-root safety

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- Import now pins source and destination-parent directory chains with no-follow descriptors, validates matched source file identities, performs descriptor-relative staging/publication/rollback, and retains cross-filesystem copy fallback. Regressions cover source-folder symlink replacement, collision-suffixed matching, cross-filesystem fallback, and rollback.
- All four required workflows passed on that exact head: syntax/acquisition safety `38726626891`, Docker packaging/full unit suite/build `38726626846`, container runtime smoke `38726626956`, and validation-only multi-architecture image validation `38726626910`. No separate local test, production-folder test, image publication, deployment, or production runtime verification.

---

## 2026-10-15 — PR #100 merged: cleanup root path traversal hardening

- PR #100 merged at `6e8e861cc84d5951b0d177ffea256a0dd88fe4b4` from exact tested head `89813bd3802b1f8920715aaeca55ccb5e461c9c9`.
- Builds on PR #99's directory-swap fix by opening the absolute configured download root one component at a time with no-follow flags and checking the root identity captured before external transfer callbacks. Cleanup revalidates the exact planned file set and file device/inode/size before descriptor-relative deletion.
- Regression coverage includes replacing the album folder with a symlink and replacing an ancestor of the configured download root with a symlink; outside targets and the moved original album track must remain untouched.
- All four required workflows passed on the exact PR head: syntax/acquisition safety `38724953760`, Docker packaging/full unit suite/build `38724953699`, container runtime smoke `38724953828`, and validation-only multi-architecture image validation `38724953678`. No local test run, production deletion test, image publication, deployment, or production runtime verification.

---

## 2026-10-15 — PR #99 merged: acquisition cleanup directory-swap hardening

- PR #99 (https://github.com/abucalip/navi-librarian/pull/99) merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25`, from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- Cleanup now opens the verified directory using no-follow, descriptor-relative traversal; validates device/inode identity; and unlinks verified files relative to the pinned directory. Added a regression that replaces the album folder with a symlink during transfer lookup and verifies the outside target and moved original album files remain untouched.
- All four required workflows passed on the exact PR head: syntax/acquisition safety `38724377954`, Docker packaging/full unit suite/build `38724378021`, runtime smoke `38724378097`, and validation-only multi-architecture image validation `38724377870` (publishing paused). No separate local test run, production deletion test, publication, deployment, or runtime verification.

---

## 2026-10-15 — PR #98 merged: acquisition request coordinator

- PR #98 ([acquisition request coordinator extraction](https://github.com/abucalip/navi-librarian/pull/98)) merged at `ae6635573aa57eb9303909701e6f0a5834066495`, from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- `acquisition_request_coordinator.py` owns the top-level request decision sequence behind injected dependencies; the MCP/web adapter retains the legacy interface, while shared state, persistence, watcher lifecycle, and acquisition implementation remain injected.
- All four required workflows passed on the exact head: syntax/acquisition safety `38723927107`, Docker packaging/full unit suite `38723927072`, container runtime smoke `38723927058`, and validation-only multi-architecture validation `38723927057`. Publishing remains paused; no deployment/runtime verification.

---

## 2026-10-15 — PR #97 merged: Last.fm settings-policy extraction

- PR #97 (`refactor: extract Last.fm settings policy`) merged at `ad239a59b77612b812ca842406fee7b47cf80889`; exact tested PR head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`.
- `service_settings.py` now owns Last.fm API-key trimming, blank-input preservation, settings-write invocation, and configured-status response serialization through injected callbacks. The legacy `discovery_set_lastfm_settings` adapter keeps its signature/JSON contract; SQLite persistence/schema and connectivity testing remain in `navidrome_server.py`.
- Direct-import regression covers trimmed replacement, blank-input preservation, and secret redaction. All four required workflows passed on the exact PR head: syntax `38721333335`, runtime smoke `38721333332`, validation-only multi-architecture `38721333418`, and Docker packaging/full unit suite `38721333353`.
- No separate local test run, image publication, deployment, or production runtime verification. Publishing remains paused.
- Next: continue the highest-priority remaining test/coordination audit from the current roadmap; do not start another routine extraction ahead of higher-priority verification gaps.

---

## 2026-10-15 — PR #96: slskd settings policy extraction

- PR #96: [refactor: extract slskd settings policy](https://github.com/abucalip/navi-librarian/pull/96), branch `refactor/slskd-settings-policy-direct-import`. Implementation moves slskd config validation, safe settings serialization, and settings update policy to `service_settings.py` with injected read/write and music-directory callbacks; MCP adapters and network connection testing remain in `navidrome_server.py`.
- Direct-import regressions cover API-key redaction/preservation, URL and quality validation, malformed quality items, path validation/no-write behavior, settings defaults, and runtime music-directory callback. Quality-priority tests now call the extracted policy directly while retaining AST-based SQLite persistence checks.
- Exact head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four required workflows: syntax/acquisition safety `38665710740`, Docker packaging/full unit suite `38665710718` (208 tests passed), runtime smoke `38665710761`, and validation-only multi-architecture image validation `38665710769`. The first CI cycle exposed an AST test harness coupling; it was fixed by migrating the affected policy tests to direct imports.
- Publishing remains paused. No image publication, deployment, or production runtime verification. No local test execution is claimed.
- Next: review and verify the documentation-updated exact PR head; then decide whether to merge PR #96. Continue settings/service boundaries without removing MCP dependencies prematurely.

---

## 2026-10-15 — PR #95 merged; next settings boundary in progress

- PR #95 merged to `main` at `2193306ce6ee2ff3ed087b2f490594f2d5ee2c68` from exact tested head `92d304d06713ec0f73253a5db48cf835ff93a063`.
- All four required workflows passed on that exact PR head: Python syntax/acquisition safety `38665121156`, Docker packaging/full unit suite `38665121160`, container runtime smoke `38665121170`, and validation-only multi-architecture image validation `38665121255` (publishing paused). No local test run, image publication, deployment, or production runtime verification is claimed.
- The settings-policy extraction preserved MCP/web adapters and moved six Navidrome/ListenBrainz/Last.fm policy functions into direct-import `service_settings.py`.
- Current task on branch `refactor/slskd-settings-policy-direct-import`: extract slskd configuration validation, safe settings serialization, and settings-update policy behind injected callbacks. Keep HTTP connection testing, persistence implementation, global path ownership, route payload/error contracts, and MCP adapter signatures in the legacy layer.
- Acceptance: direct-import tests for secret redaction, blank-key preservation, exact quality-tier validation, invalid path/URL/no-write behavior, default serialization, and path callback updates; focused/full test suite and all four exact-head CI workflows. Do not publish or deploy.

---

## 2026-10-15 — Service settings policy extracted (PR #95)

- Added `service_settings.py` with injected settings-read/write and runtime-path callbacks. Moved Navidrome config validation, ListenBrainz username validation, safe Navidrome settings serialization/update, Last.fm configured-status serialization, and ListenBrainz settings update policy out of the monolith.
- Existing MCP/web function names and signatures remain in `navidrome_server.py` as adapters. SQLite persistence/schema, `MUSIC_DIR` ownership, connection checks, other service settings, and route behavior remain unchanged. Added the module to the Docker image.
- Replaced AST-executed tests in `tests/test_service_settings.py` with direct-import tests covering credential/key redaction, blank-password preservation, URL and username validation, invalid-input no-write behavior, and library path validation.
- All four required workflows passed on the final PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9`: Python syntax/acquisition safety (run `38664285319`), Docker packaging/full unit suite/build (run `38664285227`), container runtime smoke (run `38664285195`), and validation-only multi-architecture image validation (run `38664285194`). The implementation revision `3cca45ed09bd4364cf1bfe78b026d4ea2cd48f0a` initially exposed a callback-injection test mismatch; the correction passed all four workflows. No local tests were run.
- PR #95 remains open and mergeable, not merged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next: review PR #95's final diff and exact-head CI before deciding to merge; then continue the caller-driven service-boundary extraction without removing MCP dependencies prematurely.

---

## 2026-10-15 — Web dependency audit of the legacy server

- Reviewed current GitHub `main` after PR #93, including `app/main.py`, all three service API routers, `server.py`, `navidrome_server.py`, `tests/test_service_settings.py`, the Dockerfile, requirements, and the architecture/development/requirements docs.
- Web coupling is broad, not just an import accident: `app/main.py` uses `DATA_DIR`, settings read/write, `api_call`, discovery list retrieval, and album eligibility; acquisition routes call the acquisition lifecycle API; discovery routes call recommendation/list/refresh/feedback functions; settings routes call all four services' get/set/test functions. The web app imports the monolith at module import time, which constructs/registers MCP tools.
- `server.py` is a separate MCP entry point using `FastMCP`; `requirements.txt` pins `mcp==2.3.0`; the Dockerfile intentionally copies `navidrome_server.py` and domain modules but does not copy/run `server.py`. Therefore MCP retirement is not a safe first extraction and must not be inferred from the web dependency audit.
- Smallest existing extraction seam identified: the six functions currently AST-loaded by `tests/test_service_settings.py` (`_navidrome_config`, `_listenbrainz_username`, Navidrome settings get/set, Last.fm settings get, ListenBrainz settings set). Their test currently executes copied function AST with fake storage, which is an explicit migration opportunity. A follow-up should move their real implementation into an importable settings-policy/service module with injected settings read/write and music-directory dependencies, preserve the MCP-named functions as thin compatibility adapters, and replace AST execution with direct-import tests.
- Keep the extraction narrow: leave SQLite schema/migrations and `MUSIC_DIR` mutation owned by existing persistence/runtime code; do not duplicate settings storage, expose secret values, or move network connection tests in the same change. Expand only after callers and behavior are covered directly.
- Audit only: no production or test code changed and no local tests were run. PR #93's four required workflows passed on exact head `616c4af7fb17c3d287fca596ddcbba09f7fd7736`; PR #93 has since merged at `e5d908b11e2a70e8294d0781c630238d4361e503`. Merge-commit CI is being checked separately; neither result implies publication or deployment.
- Next implementation objective: extract the six settings-policy functions behind injected storage/path dependencies, add direct-import regression tests, preserve MCP adapter signatures and web response contracts, then run focused tests, the full suite, syntax checks, and all four workflows on the exact PR head.

---

## 2026-10-15 — Acquisition lifecycle AST-boundary audit

- Audited the remaining acquisition lifecycle cases in `tests/test_acquisition_safety.py` against direct-import coverage in `tests/test_acquisition_orchestration.py`, `tests/test_acquisition_lifecycle.py`, `tests/test_acquisition_watcher.py`, and the focused import/recovery suites.
- **No AST lifecycle test was removed.** Each remaining case still proves a coordinator or adapter boundary that helper-only tests do not fully cover:
  - simultaneous Get requests: shared transition-lock / reservation ordering and duplicate prevention across the top-level coordinator;
  - import status persistence failure: the actual import adapter must not enter filesystem import until the `importing` transition is persisted;
  - incomplete saved candidate: top-level Get must return `recovery_unavailable` without starting a new search or watcher;
  - dismissed-job Get success/refusal: adapter wiring, returned status, and no retry when reactivation fails;
  - stale downloading job: top-level recovery starts the watcher and does not requeue;
  - broader-query retry: end-to-end query sequencing and diagnostic/result contract beyond polling-helper unit coverage.
- Direct-import coverage is already present for the pure decisions and helpers (request reservation, existing-job recovery decision, dismissal/reactivation preflight, polling, and lifecycle policy). Removing any of the coordinator cases now would reduce coverage rather than complete a safe migration.
- Scope of this audit: GitHub source and tests only. No application code or tests changed, and no local test execution is claimed. Existing `main` CI for `c6017f7a59e2aaec09e498ca4bda9315b0325cd3` is green across all four required workflows; this is baseline evidence, not CI for this documentation branch.
- **Next priority:** perform the read-only web dependency audit of `navidrome_server.py` callers before any MCP retirement, starting with `app/main.py`, `app/api/acquisitions.py`, `app/api/discovery.py`, `app/api/settings.py`, and `server.py`. Identify the smallest independently testable service boundary; do not remove MCP dependencies yet.

---

## 2026-10-15 — PR #92 merged: dismissed-acquisition preflight extracted

- PR: https://github.com/abucalip/navi-librarian/pull/92
- Exact tested PR head: `1f0ce2174e1e60f3aab7c898dd534b8b1f11e858`; squash merge commit: `60698f7bf1413e4c643309e200d1ace2e268bee3`.
- Extracted dismissal detection, retry-metadata normalization, and conditional reactivation decision into `_acquisition_orchestration.reactivate_dismissed_acquisition_if_needed`. The coordinator retains shared transition-lock ownership and the existing refusal response; state-store conditional update and stale-source clearing remain unchanged.
- Four direct-import regression cases cover non-dismissed bypass, valid metadata, malformed/non-object metadata fallback, and failed-reactivation refusal. Existing AST-level Get success/refusal integration cases remain.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety `38661883721`; Docker packaging/full unit suite `38661883755` (203 tests passed); runtime smoke `38661883730`; validation-only multi-architecture `38661883723` (publishing paused).
- The initial draft's namespace-alias error was caught by CI and fixed before the final tested head. PR #92 is merged. No image publication, deployment, or production runtime verification.
- Next priority: continue the remaining acquisition lifecycle AST-coupled test audit, guided by `docs/TEST_PLAN.md` and `docs/MODULARIZATION_ROADMAP.md`.

---



## 2026-10-15 — PR #90 merged; acquisition reservation lifecycle verified

- PR #90 merged to `main` at `4756ad6a7669ab77e284309ca9cd0f178e7f032a` from exact tested head `c0b4a0ebcc5fa4ef8b71441fb38d55aed8fce097`.
- Extracted active-request identity check/add into `acquisition_orchestration.reserve_acquisition_request`; the server continues to own the shared transition lock across persisted-state checks and reservation. `run_reserved_acquisition` handles callback execution outside the lock and guaranteed cleanup under the lock.
- All four required workflows passed on the exact PR head: syntax/acquisition safety `38659706561`, Docker packaging/full suite `38659706115` (199 tests passed), runtime smoke `38659706074`, and validation-only multi-architecture `38659706150` (publishing paused).
- The end-to-end simultaneous-request AST regression remains; direct helper tests do not replace the shared-lock integration boundary.
- Next: extract the dismissal/reactivation preflight decision behind injected dependencies while retaining the top-level Get/reactivation success/failure tests. No publication, deployment, or production runtime verification.

---

## 2026-10-15 — Watcher-start concurrency regression verified

- PR #84 exact tested head: `398486476aacdbbefefeaee5cb79182cc0835fb8`. All four required workflows passed: Python syntax and acquisition safety regressions (run 38656927551), Docker packaging/full unit suite (38656927436), container runtime smoke (38656927801), and multi-architecture image validation with publishing paused (38656927516).
- The full unit-test step and focused acquisition safety regression step both succeeded. The new concurrent watcher-start regression is included in the exact tested head; CI workflow evidence is green.
- Final diff reviewed: one threaded test plus documentation updates; no production code changed. The remaining AST lifecycle tests are retained where they uniquely exercise coordinator sequencing, races, persistence-before-import, or recovery behavior.
- No image publication, deployment, or production runtime verification is claimed.
- Next: merge PR #84 after final exact-head status confirmation, then continue the AST audit against the updated main.

---

## 2026-10-15 — Session closeout: acquisition AST-test audit handoff

- Reconciled the project status against GitHub `main` at `f46b3618eaa8abc98b7f077698439b304a0005b7`. PR #82 is merged; it updates the status, log, test plan, and modularization roadmap after PR #81's closeout.
- PR #82 was documentation-only. Exact tested head: `5fdad1045ba04db84aea05a477a51dce38733f5c`; all four required workflows passed (syntax `38656400677`, Docker packaging/full suite `38656400827`, runtime smoke `38656400743`, image validation with publishing paused `38656400766`). No application tests were newly run specifically for the documentation change.
- **Next action:** continue the remaining AST-coupled acquisition lifecycle test audit: duplicate-request reservation/concurrency, incomplete saved candidate details, dismissed-job reactivation and refusal on failed reactivation, and stale watcher recovery. Keep persistence-transition integration coverage and true lock/race tests unless equivalent direct tests cover the same boundary.
- Publishing remains paused. No deployment or production runtime verification is claimed.

---

## 2026-10-15 — PR #78 merged: dismissal-serialized import guard

- PR #78: https://github.com/abucalip/navi-librarian/pull/78
- Exact tested head: `e6a609ca7381d0751d529b52f55aeebd56d76661`; squash merge: `5d638c7adf5a42fdac8052cb4fc223236564cd72`.
- Extracted the dismissal check plus callback into `acquisition_orchestration.import_source_unless_dismissed`. The shared transition lock still spans the entire callback; filesystem validation, mount identity, persistence, import staging, and rollback remain unchanged.
- Moved only the dismissal-only AST test to direct-import coverage. Kept the AST integration test proving import does not begin if the `importing` status cannot be persisted.
- All four required workflows passed on the exact tested head: syntax (run `38653493244`), Docker packaging/full unit suite (run `38653493312`), runtime smoke (run `38653493285`), and Docker image validation with publishing paused (run `38653493279`). The full suite reported 186 tests passed.
- Final diff reviewed. No live slskd, publication, deployment, or production runtime verification is claimed.
- Next: continue the AST audit of acquisition request concurrency, reactivation, and watcher-recovery coordination; preserve all state and lock boundaries.

---


## 2026-10-15 — PR #76 merged: slskd polling extracted

- PR #76: https://github.com/abucalip/navi-librarian/pull/76
- Exact tested head: `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6`; squash merge: `a55a9fa7eed1e221f52434b50f44d0c415fd491a`.
- Extracted progressive query submission, polling, delayed peer-payload waiting, count aggregation, peer deduplication, and per-attempt diagnostics into `slskd_search_polling.py` with injected HTTP/time/ID/normalization dependencies. Added four direct-import tests; retained the AST end-to-end broad-query regression.
- All four required workflows passed on the exact tested head: Python syntax (run `38652846800`), Docker packaging/full unit suite (run `38652846779`), runtime smoke (run `38652846790`), and Docker image validation with publishing paused (run `38652846819`). The full suite reported 184 tests passed.
- Final diff reviewed; Docker packaging and syntax workflow include the new module. No live slskd interaction, publication, deployment, or production runtime verification is claimed.
- Next: audit remaining AST-coupled acquisition lifecycle tests, keeping true coordination/race/persistence integration cases unless equivalent direct-import coverage tests the same boundary.

---

## 2026-10-15 — PR #73 merged: candidate extraction direct-import test

- PR #73: https://github.com/abucalip/navi-librarian/pull/73
- Exact tested head: `a33772ca1da0b6628da490b69f1dc305b6794de3`; squash merge: `df2f79b3d18df7d13484f7e3b5e7f550a39323d3`.
- Moved the Tinariwen/Idrache candidate grouping/ranking scenario from the AST harness to `tests/test_slskd_candidates.py`, directly calling `slskd_search.extract_candidates` with production helper functions. Removed the empty AST test class left by the migration. No production code changed.
- All four required workflows passed on the exact tested head: Python syntax (run `38652066842`), Docker packaging/full unit suite (run `38652066649`), container runtime smoke (run `38652066755`), and Docker image validation with publishing paused (run `38652066683`).
- Final diff reviewed: only project status/log/test-plan/roadmap docs and the two test files changed. No live slskd test, image publication, deployment, or production runtime verification is claimed.
- Next: continue the AST-coupled acquisition-coordination audit; preserve sequencing, lock/race, persistence, cancellation, dismissal/reactivation, and watcher recovery coverage.

---

## 2026-10-14 — PR #72 merged: pure slskd search-helper tests

- PR #72: https://github.com/abucalip/navi-librarian/pull/72
- Tested PR head: `17be72e52b39e63cad63391fb2c4e63ea55d3c26`; squash merge commit: `6c6157a8238691b18d2209ea2d2e1306385ec9a2`.
- Migrated six pure query/payload/path-matching/diagnostic cases into `tests/test_slskd_search.py`; retained acquisition retry/wait and candidate extraction coverage in the AST harness at merge time.
- All four required workflows passed on the exact tested head: Python syntax `38651547240`, Docker packaging/full unit suite `38651547229`, runtime smoke `38651547283`, and Docker image validation with publishing paused `38651547264`.
- Test-only change. No standalone local test commands, live slskd interaction, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-14 — PR #71 merged: candidate-start validation extraction

- PR: https://github.com/abucalip/navi-librarian/pull/71
- Tested PR head: `f53e8ceffc8307c7b8dbcbf837e123b51671bbda`; squash merge commit: `b10650aa6a8889610b5734c5a1cf02c3197f1ad0`.
- Extracted slskd candidate-start validation into `acquisition_candidate_start.py`, retaining the server compatibility adapter and injecting I/O/timing dependencies for direct tests. Migrated traversal and mixed-directory cases out of the AST harness and added active-transfer, cancellation, and uncertain-outcome coverage.
- All four required workflows passed on the exact tested PR head: Python syntax (`38648719075`), Docker packaging/full unit suite (`38648719066`), container runtime smoke (`38648719107`), and Docker image validation with publishing paused (`38648719074`).
- No standalone local test run, live slskd interaction, image publication, deployment, or production runtime verification is claimed.
- Remaining AST audit: retain coordination tests where they cover races or persistence/transition boundaries; continue evaluating pure-helper cases for direct-import migration.

- Branch: `refactor/extract-candidate-start-validation`, based on main after PR #70 merge `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161`.
- Extracted `_slskd_candidate_start_state` into `acquisition_candidate_start.py`; the legacy server function remains as a compatibility adapter injecting the existing transfer lookup, HTTP client, clock, and sleep dependencies.
- Migrated the two AST-harness tests for traversal rejection and mixed remote directories to direct-import tests in `tests/test_acquisition_candidate_start.py`. Added direct coverage for active transfer recognition, safe queued-transfer cancellation, and uncertain cancellation/lookup outcomes.
- This changes module boundaries, not intended behavior. Conservative failure semantics remain: ambiguous paths are rejected before lookup, and uncertain cancellation never authorizes fallback.
- Validation still pending on this branch: focused tests, full unit suite, syntax checks, review of the complete diff, and all four required CI workflows on the exact final PR head. No tests are claimed passed until observed.
- Remaining AST audit: retain concurrency and dismissal/import coordination cases until equivalent direct-import tests cover the actual coordination boundaries; next compare search/candidate extraction cases against their direct module owners.
- PR #70 was squash-merged at `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161` after all four required workflows passed on exact tested head `0916a7e9d767808bf4f65d3b034e290e5aba4703`.

---

## 2026-10-14 — Completed import safety tests migrated to direct imports (PR #70 merged)

- Removed the redundant `CompletedAlbumMatchingTests` cases from the AST-based `tests/test_acquisition_safety.py` harness. Equivalent or stronger coverage already exercises the production modules directly in `tests/test_acquisition_completion.py` and `tests/test_acquisition_import.py`.
- The direct-import suites cover strict positive-size matching, Unicode/case and Windows path normalization, duplicate-basename ambiguity, symlink refusal, collision-suffix matching, exact folder diagnostics, unrelated-file preservation, destination no-overwrite, storage identity mismatch, reserved manifest rejection, and rollback after a partial move.
- The AST harness retains its separate lifecycle coordination tests. Its injected import callback is now a test spy for transition behavior; filesystem import behavior is tested against `acquisition_import.import_matched_album_files` directly.
- Test-only migration: no production code, queue/cleanup behavior, path validation, rollback implementation, or MCP compatibility changed.
- PR #70 was squash-merged at `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161` after all four required CI workflows passed on exact tested head `0916a7e9d767808bf4f65d3b034e290e5aba4703`. No standalone local test commands or manual browser tests were run for this test-only migration; no image publication, deployment, or production runtime verification is claimed.
- Next: audit remaining AST-coupled acquisition safety cases for duplicate coverage; preserve dismissal/import coordination, conditional state transitions, cleanup refusal, uncertain queue outcomes, and rollback protections.

---

## 2026-10-14 — PR #69 merged: canonical front-end design guide

- **PR:** https://github.com/abucalip/navi-librarian/pull/69
- **State:** Documentation-only change reviewed and squash-merged. Tested PR head: `a31997baa65d02b36ea7b85aaf6bab52ddfbeee5`; merge commit: `fd9ceb17480e08e84d2e93ab84defb32c7af1b0a`.
- Added `docs/FRONTEND_DESIGN_GUIDE.md` as the canonical agent-independent design specification and backlog. Root `AGENTS.md` requires front-end agents to read it; development workflow and test plan link to it.
- The guide preserves the dark-grey/yellow/red identity, Barlow Condensed / IBM Plex Sans / IBM Plex Mono typography, anti-patterns, Impeccable critique workflow, accessibility/responsive expectations, front-end ownership boundaries, and prioritized backlog. Login alignment is complete; state craft is next.
- All four required workflows passed on the exact PR head: container runtime smoke (run `38644811862`), Python syntax (`38644811890`), Docker image validation with publishing paused (`38644811875`), and Docker packaging (`38644811793`).
- No local test commands or manual browser tests were run for this documentation-only change. No image publication, deployment, or runtime verification is claimed.

---

## 2026-10-14 — Queue failure classification test migration in progress

- Branch: `test/migrate-queue-failure-classification`, based on current GitHub `main` at `23798189e058c97a2080c64ae6ad6468b0ce3645`.
- Removed two AST-harness tests for `_slskd_queue_failure_action` and removed that compatibility adapter from the AST harness's selected-function list. The production wrapper delegates directly to `acquisition_lifecycle.queue_failure_action`.
- Equivalent direct-import coverage already exists in `tests/test_acquisition_lifecycle.py::AcquisitionLifecyclePolicyTests.test_queue_failure_classification_never_retries_uncertain_errors`, covering retryable explicit rejections (400/404/422), fatal authentication failures (401/403), uncertain HTTP outcomes (408/429/500/503/missing status), and transport errors.
- Test-only change; no production behavior or safety checks changed. Exact-head focused/full tests and all four required workflows remain pending; no test pass is claimed yet.
- Next: verify direct-import coverage and the complete diff, then migrate the next AST-coupled case only where existing direct-import tests exercise the real implementation with equivalent or stronger safety assertions.

---

## 2026-10-14 — PR #64 merged: queue dismissal test migration

- **PR:** https://github.com/abucalip/navi-librarian/pull/64
- **Tested PR head:** `3bde365e43acbe1cc95f68d7014d899046e735f6`; **squash merge:** `1596161aa525896d43c37c85533e8056a742439b`.
- Removed the redundant dismissed-queue-refusal case, adapter shim, and now-unused HTTP queue helper from the AST-based safety harness. Equivalent direct-import coverage remains in `tests/test_acquisition_orchestration.py` against `queue_candidate_unless_dismissed`, including dismissal refusal, lock ordering, return propagation, and exception behavior.
- All four required workflows passed on the exact final PR head: syntax `38636360130`, Docker packaging/full unit suite `38636360145`, container runtime smoke `38636360164`, and validation-only multi-architecture image `38636360139` (publishing paused).
- Test-only change; no production behavior or safety checks changed. No local test run, live slskd interaction, production filesystem operation, publication, deployment, or production runtime verification is claimed.
- **Next:** continue the acquisition coordination/test-migration audit, selecting the next AST-coupled case only when direct-import tests can preserve or improve coverage.

---

## 2026-10-14 — Acquisition queue guard test migrated

- Continued the acquisition safety-test migration after PR #62. Removed the AST-harness case for dismissed queue refusal and its injected queue adapter because `tests/test_acquisition_orchestration.py` already tests the actual `queue_candidate_unless_dismissed` implementation directly, including lock ordering, dismissed refusal, return propagation, and exception propagation.
- Test-harness cleanup only: no production code or safety behavior changed, and equivalent direct-import refusal coverage remains.
- Exact-head CI and diff review are required before merge. No local test run, live slskd behavior, publication, deployment, or production runtime verification is claimed.
- Next: migrate AST-coupled orchestration/lifecycle cases only when equivalent direct-import coverage exercises the production implementation.

---

## 2026-10-14 — Front-end ownership transferred to ZCode

- ZCode is now the designated front-end implementation owner; root instructions live in `AGENTS.md`.
- ZCode may change only `static/app.css`, `static/app.js`, `static/login.css`, `static/login.js`, `app/templates/*.html`, and narrowly scoped UI tests/fixtures unless the project owner explicitly approves a scope expansion.
- Backend/domain/security/API behavior, release controls, cross-layer integration, merge decisions, publishing, deployment, and final project-level verification remain assistant-owned.
- Initial ZCode task: audit the existing UI and deliver one focused visual-quality improvement using Impeccable guidance where available. Preserve product behavior; provide a PR with before/after screenshots and exact-SHA test evidence. No frontend task has been implemented or verified by this documentation update.
- This handoff does not change the roadmap's highest-priority backend work: continue acquisition-coordination safety/test migration on the main project track.

---

## 2026-10-14 — PR #62 merged: acquisition queue/dismissal guard

- **PR:** https://github.com/abucalip/navi-librarian/pull/62
- **State:** Implemented, focused diff reviewed, all four required workflows passed on exact PR head, and squash-merged.
- **Branch / tested head:** `refactor/acquisition-queue-guard` / `4e121eb7977bb1a51ad31f9c87d0d4984497af4d`.
- **Merge commit:** `d4a16e80f6978a58c3305bf341e370ba9708bb34`.
- **CI:** Python syntax `38619152587`; Docker packaging/full unit suite/build `38619152213`; container runtime smoke `38619152754`; validation-only multi-architecture image `38619152728`. All succeeded on the exact tested head. Publishing remains paused.
- **Change:** extracted queue/dismissal critical-section coordination into `acquisition_orchestration.py`; retained the server adapter, HTTP request semantics, shared transition lock, and dismissal predicate. Added direct-import tests for lock scope, dismissal refusal, return value, and exception propagation; retained the AST safety regression.
- **Not verified:** no separate local helper/manual slskd test, production filesystem operation, image publication, deployment, or production runtime verification.
- **Next:** continue acquisition-coordination audit and migrate remaining AST-coupled safety tests incrementally.

## 2026-10-14 — PR #61 merged: acquisition transition guard

- **PR:** https://github.com/abucalip/navi-librarian/pull/61
- **State:** Implemented, final diff reviewed, all four required workflows passed on exact final PR head, and squash-merged.
- **Exact tested PR head:** `aa554ff2be2a19e215538ed2e699b8036764dca1`; **merge commit:** `73172847535d3683facfbe559706c26a8637a3d4`.
- **CI:** Python syntax/acquisition safety run `38617537652`; Docker packaging/full unit suite/build `38617538490`; container runtime smoke `38617537978`; validation-only multi-architecture image `38617538229`. All succeeded on the exact tested head; publishing remains paused.
- **Change:** moved the dismissal-serialized source-switch guard into `acquisition_orchestration.py`; retained the server compatibility adapter and the existing shared lock; added direct-import regression coverage for lock scope, dismissal refusal, return values, and exception propagation.
- **Limits:** no separate assistant-local test run, live slskd interaction, production filesystem operation, image publication, deployment, or production runtime verification is claimed.
- **Next:** continue acquisition-coordination audit and migrate remaining AST-coupled safety tests to direct-import tests without reducing safety coverage.

## 2026-10-14 — Acquisition transition guard extraction in progress

- PR pending: `refactor/acquisition-transition-guard` extracts the dismissal-serialized source-switch guard into `acquisition_orchestration.py`, with direct-import tests for lock scope, dismissal refusal, return-value preservation, and exception propagation.
- Safety boundary: the shared transition lock remains authoritative; the dismissal check and source-switch callback remain inside one critical section. No queue, cleanup, persistence, or filesystem behavior is otherwise changed.
- Verification: implementation is awaiting focused tests and all four exact-head CI workflows. No live slskd interaction, production filesystem operation, publication, deployment, or runtime verification is claimed.
- Next: review the exact PR diff and merge only after all required gates pass.

## 2026-10-14 — PR #59 merged: acquisition state persistence

- **State:** Implemented, final diff reviewed, all four required workflows passed on exact final PR head, and squash-merged.
- **PR:** https://github.com/abucalip/navi-librarian/pull/59
- **Branch / tested PR head:** `refactor/acquisition-state-store` / `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d`.
- **Merge commit:** `730ae16e613f3962c488f87c8de54034db7463dd`.
- **Implementation:** extracted SQLite acquisition-row save/list mechanics into `acquisition_state.py`; legacy server functions remain compatibility adapters. Docker packaging and architecture, roadmap, test plan, project status, and project log were updated.
- **Regression coverage:** direct-import tests cover save/list round-trip, normalized identity, preservation of candidate/settings/quality metadata on partial updates, invalid identity rejection, and malformed stored JSON.
- **Safety boundary:** shared transition locking, conditional dismissed-state checks, secondary feedback projection, dismissal/import coordination, and filesystem safety remain in `navidrome_server.py`.
- **Exact-head CI on `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d`:** compile run `116019930318`, full test/build run `116019925188`, container smoke run `116019924747`, and validation-only multi-architecture run `116019926066` all succeeded. The corrected code head previously ran 180 tests; the docs-updated final head's test/build workflow also succeeded. Publishing remains paused.
- **Limits:** no separate assistant-local test run, live slskd test, production filesystem action, image publication, deployment, or production runtime verification is claimed.
- **Next:** inspect current GitHub main, open PRs, and the updated roadmap before selecting the next priority; keep correctness/safety and exact-head verification ahead of routine modularization.

## 2026-10-14 — Acquisition state persistence extraction (verification update)

- PR #59 branch `refactor/acquisition-state-store`; corrected code head `29c5e6a460f1f61296680af7b1230fd5561496b4`.
- Extracted acquisition-row SQLite save/list mechanics into `acquisition_state.py`; legacy wrappers remain, and transition locking, conditional dismissed-state checks, feedback projection, dismissal/import coordination, and filesystem safety remain in `navidrome_server.py`.
- Initial CI found one incorrect test expectation for JSON `null`; the fixture was corrected without changing production code. Corrected code head CI passed all four required workflows: full unit suite/build `116019140196` (180 tests passed), compile `116019144533`, container smoke `116019141476`, and validation-only multi-architecture `116019141889` (publishing paused).
- The docs closeout itself creates a new PR head; final exact-head CI, diff review, merge, publication, deployment, and production runtime verification remain unclaimed until rechecked.

## 2026-10-14 — Acquisition state persistence extraction (in progress)

- Branch `refactor/acquisition-state-store` starts from main `066fff8e7ef88364b1dc9cc909bfb2722118880e`.
- Extracted acquisition-row SQLite save/list mechanics into `acquisition_state.py` behind injected initialization, DB path, key normalization, and clock; legacy functions remain adapters. Added direct-import tests and Docker packaging.
- Safety boundary intentionally retained in the server: transition lock, conditional dismissed-state checks, feedback projection, dismissal/import coordination, and filesystem operations. Acceptance requires exact-head CI and diff review before merge.
- No local tests, CI, merge, publication, deployment, or production verification are claimed at this stage.

## 2026-10-14 — Acquisition watcher startup extraction (in progress)

- Extracted watcher reservation/persistence/thread startup into acquisition_watcher_startup.py with injected services. The legacy _discovery_start_import_watcher function remains the adapter used by existing MCP/web call paths.
- Added direct-import tests for duplicate/dismissed startup, persisted-settings credential filtering, persistence failure cleanup, and thread-start failure handling. Added the module to Docker packaging.
- All four required workflows passed on the documentation-updated PR head 3f072159ef9e61f70554d315277a612005b8de4e: Python syntax/acquisition safety 38609940832, Docker packaging/full unit suite/build 38609940860, container runtime smoke 38609940739, and validation-only multi-architecture build 38609940737 (publishing paused). No separate local test run, live slskd test, publication, deployment, or production runtime verification is claimed. Historical note: PR #58 was open and unmerged at the time this entry was written; it was subsequently merged to main at `066fff8e7ef88364b1dc9cc909bfb2722118880e` after all four required workflows passed on exact tested head `3f072159ef9e61f70554d315277a612005b8de4e`.
- Next: persistent acquisition-state coordination extraction, preserving shared transition-lock and conditional-write semantics.

## 2026-10-14 — PR #57 merged: acquisition watcher lifecycle

- **State:** Implemented, exact-head CI passed, final diff reviewed, and squash-merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from tested PR head f4b92a98bae942ac6080316c3f1803d1b6bcff76.
- Extracted the watcher loop into acquisition_watcher.py behind injected services; retained _discovery_watch_and_import_album as the compatibility adapter and included the module in Docker packaging. Direct-import tests cover dismissal, interrupted-import recovery, waiting when completion evidence lacks a verified folder, and handing only a verified folder to the safe import coordinator.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, container runtime smoke 38605511271, and validation-only multi-architecture build 38605510906 (publishing paused).
- **Limits:** no separate assistant-local test run, live slskd test, production filesystem action, image publication, deployment, or production runtime verification. The first CI attempt caught a test assertion using the wrong argument location; the test was corrected and the final exact head passed all four workflows.
- **Next:** continue the roadmap with persistent acquisition-state coordination and watcher startup, preserving MCP compatibility and all existing cleanup/import safety boundaries.

## 2026-10-14 — Acquisition dismissal cleanup safety (PR #51)

- **Implemented and merged:** PR #51 added six regression cases around the actual `_discovery_cancel_and_clean_source` helper: cleanup after transfers stop, unrelated-file refusal, traversal refusal, ambiguous duplicate-folder refusal, symlink-target refusal, and cancellation-failure preservation.
- **Branch/head:** `test/acquisition-dismissal-safety`, exact tested PR head `58021141472c85c9fa33c431cba15cb66792bc1c`; squash-merged to `main` as `790d690ca99866878ee6204f9d101dec5f099994`.
- **Exact-head CI:** all four required workflows passed: Python syntax + acquisition safety regressions (run `38590192829`), Docker packaging/full unit tests/image build (`38590192830`), container runtime smoke (`38590192905`), and validation-only multi-architecture build with publishing paused (`38590192858`). The earlier failing attempt exposed a test-harness stub collision; the helper was isolated under a distinct AST namespace name and the corrected head passed all gates.
- **Review:** final PR diff reviewed; no production code changed. GitHub reported the PR mergeable; no review submissions or inline threads were present.
- **Remaining limits:** tests were run in CI, not separately by the assistant locally. No live slskd test, real-download-folder deletion, image publication, deployment, or production runtime verification. The previously reported HTTP 409 remains deferred because it was not reproduced.
- **Next:** continue from the roadmap with correctness/safety/verification priorities; retain these tests when moving the cleanup helper into a directly importable domain module.

## 2026-10-14 — Acquisition lifecycle extraction started (PR #47)

- PR #46 was squash-merged to `main` at `9b6792206cc3e4241fb0bb5e1fec784f49f44d25` after all four required workflows passed on exact head `5b050abac235d729df01cc04703ce70140398be6`.
- PR #47 adds a dependency-light `acquisition_lifecycle.py` policy module and direct-import regression tests, then routes selected legacy lifecycle decisions through it while preserving existing MCP function names.
- Scope intentionally stops short of claiming full orchestration extraction: watcher orchestration, state persistence, cleanup execution, source switching, and interrupted-import recovery still depend on `navidrome_server.py`. Exact code head `581823b96ba6888da4c5ff99c007afb0c633cc36` passed all four required workflows: Python syntax, Docker packaging/full unit suite, container runtime smoke, and validation-only multi-architecture image build. The final documentation-only head still requires its own exact-head CI confirmation.
- No image publication, deployment, or production runtime verification is performed.

## 2026-10-14 — Read-only audit: remaining `navidrome_server.py` dependencies

- Audited GitHub `main` at `edc6239c0a01573e1eaa3161a4485ca03a9851da`; the legacy module was approximately 6,179 lines. This was a source/documentation inspection only: no application changes or tests were run.
- Direct web imports remain in `app/main.py`, `app/api/settings.py`, `app/api/discovery.py`, and `app/api/acquisitions.py`. Metadata routes are already separated in `app/api/metadata.py`.
- `app/main.py` still uses the legacy module for `DATA_DIR`, persistent settings reads/writes, Navidrome health checks, discovery-list retrieval, and album-candidate eligibility. Settings routes delegate Navidrome, Last.fm, ListenBrainz, and slskd configuration/testing to legacy functions. Discovery routes delegate recommendations, list retrieval/refresh, feedback, and eligibility. Acquisition routes delegate status, skip, dismiss, acquire, and queue operations.
- The web import initializes MCP-related code because `navidrome_server.py` imports and instantiates `MCPServer` and registers tools. The web Dockerfile copies the legacy module and `requirements.txt` includes the MCP package. `server.py` is another MCP-related entry point whose role and callers must be checked before repository-wide dependency removal.
- Safety regression coupling remains: `tests/test_acquisition_safety.py` parses the legacy file with `ast`, extracts named functions, strips decorators, and executes them in a stub namespace. Do not delete this coverage wholesale; migrate each case to direct tests against extracted implementations and preserve lifecycle/safety assertions.
- **Next implementation priority:** extract acquisition lifecycle/orchestration behind an importable domain module, retaining existing web/MCP adapters and filesystem safety. Then separate settings/configuration and service access, finish discovery orchestration, and remove remaining `app/main.py` dependencies. Retire MCP only after a fresh repository-wide usage/entry-point/dependency/test/docs audit.
- Verification boundary: GitHub source and selected docs were inspected; no tests were run. Workflow/status lookups for the audited `main` SHA returned no runs/status entries, so no CI result is claimed. No merge, publication, deployment, or runtime verification occurred.

## 2026-10-14 — PR #44 dismissal diagnostics: local manual report published; 409 not reproduced

- PR #44 remains open as a draft at exact tested head `4c505423afef8c6959063ddea7e5672a0b9894ef`; it is not merged.
- Published the user's local manual report as a PR conversation comment. Test environment: macOS 26.2 arm64, Python 3.12.14, isolated port 8089, per-commit app data, sandbox music/download paths, and slskd disabled by default.
- All reported manual checklist items passed: first-run setup/login, dashboard/artwork, discovery, navigation/album details, settings, Get/request without a real download, acquisition cards/status, and no unexpected browser/server errors.
- Crucially, every Dismiss attempt succeeded; the reported HTTP 409 was not reproduced. This does not identify a cleanup refusal stage or verify a fix for the original failure. The report's final console detail was truncated, so no meaning is inferred from it.
- PR #44's four required exact-head workflows were already confirmed successful: Python syntax, Docker packaging/full unit suite, container runtime smoke, and validation-only Docker image/multi-architecture (publishing remains paused).
- **State:** instrumentation implemented; automated CI passed; isolated manual UI checklist passed but original 409 scenario unverified; PR not merged; no image publication, deployment, or production runtime verification.
- **Next action:** leave PR #44 draft/unmerged until the failure is reproduced with its diagnostic warning, or new evidence supports a focused change. If it recurs, capture the HTTP response body and matching server warning before retrying. Do not relax cleanup safety checks.
 
## 2026-10-14 — ZCode front-end project instructions merged; expanded handoff in progress

- PR #42 defined the initial ownership boundary and was squash-merged to `main` at `b23e0da128d63bee2bef7f47ed3350cf1be2e613` from exact head `663d826f02c12e0dbf9b1832570b60f20864ecbc`.
- The root `AGENTS.md` is being expanded into a practical project-instructions document: product context, allowed/protected paths, API/security boundaries, UI conventions, branch/PR workflow, exact-SHA testing, and required handoff reporting.
- This follow-up is documentation-only; no application behavior changes. PR #42's four required workflows passed on its exact head. The current follow-up must pass its own exact-head checks before merge.
- Publishing and deployment remain paused/not performed. Next: review this documentation PR, verify all required checks and mergeability, then give ZCode the task-specific objective and have it follow `AGENTS.md`.

## 2026-10-14 — PR #41 merged: frontend asset extraction

- PR #41 was squash-merged to `main` at `410506ea76d7181aa300edb9c05ebbd337dd7159` from exact tested head `b94dde68cccef776cea3813dbe7310eb857d170b`.
- Extracted login and main-page HTML into `app/templates/`, and CSS/JavaScript into `static/`; FastAPI serves the extracted assets, and Docker packaging includes them. Auth middleware permits the public login assets and bundled cassette icon while continuing to protect app/API routes.
- Added/updated integration and source-based regression tests for public asset delivery, external asset references, artwork-cache isolation, and quality-priority behavior.
- All four required workflows passed on the exact tested head: Python syntax (run `38493894120`), Docker packaging/full unit tests (run `38493894221`), validation-only Docker image/multi-architecture (run `38493894141`), and container runtime smoke (run `38493893959`).
- Manual report published in [PR #41 comment](https://github.com/abucalip/navi-librarian/pull/41#issuecomment-6159043901): all eight checklist items passed with zero reported failures on macOS 26.2 arm64, Python 3.12.14, isolated port 8090, sandbox music/download paths, and slskd disabled. User additionally reports navigation is noticeably snappier/smoother and no errors occurred during testing. A separate deliberately induced error/recovery scenario was not reported, so do not claim that scenario was exercised.
- No local tests are claimed beyond the published browser report. No image publication, deployment, or production runtime verification occurred; GHCR publishing remains disabled.
- Next: continue the modularization roadmap from the current GitHub `main`, starting with a fresh review of open PRs, requirements, and remaining verification gaps.


## 2026-10-14 — PR #39 merged: authentication API routes

- PR #39 was squash-merged to `main` at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact PR head `9187a51380d2a7ed7d27276ce4505827becaed32`.
- All four required GitHub Actions workflows passed on that exact head: container runtime smoke (run `38492677708`), Python syntax (run `38492677728`), Docker packaging/full unit tests (run `38492677704`), and validation-only multi-architecture image validation (run `38492677825`). The combined commit-status endpoint returned no legacy status entries; workflow-run conclusions were successful.
- Extracted `/api/auth/status`, `/api/auth/setup`, `/api/auth/login`, `/api/auth/logout`, and `/login` into `app/api/auth.py`. Middleware remains in `app/main.py`; signing/session primitives remain in `app/security/auth.py`. Injected dependencies preserve app-owned settings, cookie setup, and authentication helpers.
- PR #38's integration tests cover first-run setup, login/logout, rate limiting, HTTP/HTTPS cookie attributes, session reuse/tampering, and public/protected route behavior; its exact-head CI passed before this extraction.
- No local test run or manual browser test was performed. This route-only change has no intended UI changes. No image publication, deployment, or production runtime verification occurred; GHCR publishing remains disabled.
- Next: continue with the next roadmap priority, frontend asset extraction, only after reviewing remaining verification gates and preserving MCP compatibility.


## 2026-10-14 — Session closeout: modularization handoff after PR #37

- Reviewed the current GitHub documentation and roadmap after PRs #35–#37. The existing entries accurately record their merge commits, exact PR heads, CI results, and verification limits; no new implementation or test run was performed in this closeout.
- Current documented main tip at session start: `621295f87ab57cf1690be925cdcfd29d3f2b8fc7`. PRs #35, #36, and #37 are recorded as merged. The repository search still surfaces the older documentation roadmap PR #23; the roadmap itself is already present and maintained on `main`, so do not treat that PR as proof of missing roadmap content.
- Next task: before extracting auth routes or app assembly, inspect `app/main.py` and existing auth tests/config, then add integration coverage for first-run setup, login/logout, throttling, cookie attributes/expiry, session persistence, and middleware/public-path rules. Extract only after those boundaries are tested and behavior can be preserved.
- Preserve the full-suite and exact-final-head CI gates in `docs/TEST_PLAN.md`. The next UI-facing change must also include the deferred manual UI performance observation and a distinct error/recovery exercise.
- No local tests, manual UI tests, image publication, deployment, or production runtime verification were performed in this closeout. GHCR publishing remains disabled until the roadmap is complete and release is explicitly authorized.

## 2026-10-14 — PR #37 merged: authentication security primitives

- PR #37 was squash-merged to `main` at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3` from exact PR head `192b084850ecbe0137b64b3dae9d07e0471198b4`.
- Added `app/security/auth.py` for persistent signing-secret loading, username/password validation, PBKDF2 digest, and signed-session creation/validation. `app/main.py` retains compatibility wrappers and keeps routes, cookies, throttling, settings access, and middleware unchanged.
- Replaced AST-based auth tests with direct tests in `tests/test_app_auth.py`, including signing-secret persistence, permissions, and invalid-secret handling.
- All four required workflows passed on exact head: syntax/full tests (`38488744726`), Docker packaging/full tests (`38488744684`), runtime smoke (`38488744607`), and validation-only multi-architecture (`38488744643`). No local test run is claimed.
- Next auth step: map and test setup/login/logout routes, throttling, cookie policy, and middleware/public-path behavior before extracting routes or app assembly.
- No image publication, deployment, or production runtime verification; GHCR publishing remains disabled pending roadmap completion and explicit authorization.

## Historical note — Authentication security helper extraction

- Branch: `refactor/auth-security-helpers`, based on updated GitHub `main` after PR #36 merged.
- Objective: separate cryptographic/session primitives and persistent signing-secret file handling into `app/security/auth.py` while leaving HTTP routes, settings persistence access, cookie policy, throttling, and middleware in `app/main.py` unchanged.
- Replaced AST-based tests in `tests/test_app_auth.py` with direct unit tests for validation, PBKDF2, signed sessions, expiry/tampering/user binding, secret persistence, POSIX permissions, and invalid-secret failure.
- PR #37 has since been merged after all four required workflows passed on the exact head; see the closeout entry above. No local tests are claimed as run.
- Publishing remains disabled; no image publication, deployment, or production runtime verification.

## 2026-10-14 — PR #36 merged: metadata API router

- PR #36 was squash-merged to `main` at `15011614649470c9c71734422b95ee048fbf9f3c`, from corrected exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`.
- Moved artist biography, album-year, album-details, and artwork endpoints plus provider/cache helpers to `app/api/metadata.py`; registered the router from `app/main.py`.
- Initial CI exposed an AST-based artwork retry test tied to the previous handler location. Migrated `tests/test_artwork_retry.py` to test the extracted module directly.
- All four required workflows passed on the corrected exact head: syntax/full unit tests (`38488440438`), Docker packaging/full unit tests (`38488440512`), container runtime smoke (`38488440488`), and validation-only multi-architecture (`38488440439`). No local test run is claimed.
- This API-only extraction has no intended UI contract change; no manual browser test was required. No image publication, deployment, or production runtime verification occurred.
- Next roadmap task: inspect and extract authentication/app assembly only after mapping persistent-settings, signing-key, session, middleware, and public-path dependencies with regression tests.
- GHCR publishing remains disabled until roadmap completion and explicit authorization.

## Historical note — Metadata API router extraction

- Branch: `refactor/metadata-api-router`, based on updated GitHub `main` after PR #35 merged and documentation was reconciled.
- Objective: move artist biography, album-year, album-details, and artwork routes plus provider/cache helpers from `app/main.py` into `app/api/metadata.py` without changing URLs or provider matching/fallback behavior.
- Added `tests/test_metadata_routes.py` for route inventory, input validation, cache behavior, MusicBrainz year preference, exact Deezer matching, and tracklist parsing.
- PR #36 has since been merged after all four required workflows passed on the corrected exact head; see the closeout entry above. No local tests are claimed as run.
- Publishing remains disabled; no image publication, deployment, or production runtime verification.

## 2026-10-14 — PR #35 merged: discovery API router

- PR #35 was squash-merged to `main` at `d61162b29c6f0cccc97aefe9c779567e671651b2` from exact PR head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`.
- Extracted recommendations, discovery-list retrieval, refresh, and feedback routes into `app/api/discovery.py`; added `tests/test_discovery_routes.py`; registered the router from `app/main.py`.
- All four required exact-head workflows passed: Python syntax/full unit tests (run `38487647938`), container runtime smoke (`38487647898`), Docker packaging (`38487647913`), and validation-only multi-architecture (`38487647952`). No local test run is claimed.
- This API-only extraction has no intended UI contract change; no manual browser test was required. No image publication, deployment, or production runtime verification occurred.
- Next roadmap task: separate metadata routes/services (artist bio, artwork, album details/year and external HTTP/cache helpers) in a focused, regression-tested PR.
- GHCR publishing remains disabled until the modularization roadmap is complete and release is explicitly authorized.

## Historical note — Discovery API router extraction

- Branch: `refactor/discovery-api-router`, created from GitHub `main` after PR #34 merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1`.
- Objective: move `/api/recommendations`, `/api/discovery/{list_name}`, `/api/discovery/{list_name}/refresh`, and `/api/discovery/feedback` from `app/main.py` to `app/api/discovery.py`, preserving route contracts and delegation to existing domain functions.
- Added direct-import regression tests in `tests/test_discovery_routes.py` for route inventory, defaults, validation, filtering, feedback serialization, payload mapping, and sanitized errors.
- PR #35 has since been merged after all four required workflows passed on exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`; see the closeout entry above. No local test run is claimed.
- Publishing remains disabled until the modularization roadmap is complete and separately authorized. No image publication, deployment, or production runtime verification.

## 2026-10-14 — PR #34 merged: acquisition API router

- PR #34 was squash-merged to `main` at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`.
- Exact-head workflows all passed: Python syntax #330 (run `38485830330`), Docker packaging/full unit tests #237 (run `38485830207`), container runtime smoke #47 (run `38485830231`), and validation-only multi-architecture #91 (run `38485830245`). The multi-architecture job completed successfully; publishing remained disabled.
- Changes: extracted six `/api/acquire*` and `/api/acquisitions*` endpoints to `app/api/acquisitions.py`; added direct-import regression coverage in `tests/test_acquisition_routes.py`; reconciled architecture, roadmap, test plan, status, and log.
- Review state before merge: PR open, mergeable, no submitted reviews or inline review threads. This API-only extraction has no intended UI contract change; no manual browser test was required.
- No local test execution, image publication, deployment, or production runtime verification is claimed. CI runtime smoke is the workflow's container test, not proof of deployment.
- Next roadmap task: extract discovery API routes from `app/main.py` into a focused router with regression tests, preserving ownership filtering and refresh/feedback semantics.

---

## 2026-10-14 — Acquisition API route extraction started

- Branch: `refactor/acquisition-api-router` (based on GitHub `main` at branch creation).
- Objective: move `/api/acquire*` and `/api/acquisitions*` handlers out of `app/main.py` into `app/api/acquisitions.py` without changing URLs, methods, payload adaptation, response/status behavior, or the existing domain implementation.
- Added `tests/test_acquisition_routes.py` for route registration, payload/default mapping, invalid inputs, skip/dismiss status translation, streaming headers, and sanitized failures.
- Exact-head CI on `5b60975d690b619e2b32fdc3835bdc9feb38af8d` passed: Python syntax workflow #326 (run 38485095323), Docker packaging/full unit tests #233 (run 38485095296), container runtime smoke #43 (run 38485095246), and validation-only multi-architecture #87 (run 38485095805).
- This is an API/module extraction with no intended visual change; manual browser testing is not planned unless CI/review reveals a UI contract change. The deferred performance and distinct error/recovery checks remain for the next UI-facing PR.
- Superseded by the merged-PR #34 closeout at the top of this file: final-head checks passed and the PR was merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1`. No image publication, deployment, or production runtime verification occurred. Publishing remains disabled pending roadmap completion and separate authorization.

---

## 2026-10-14 — PR #31 merged; session closeout

- PR #31 (testing workflow documentation) was squash-merged to `main` at `87e5816c4273e720352931402a223f0b61ecbf27`, from exact PR head `135b719bfecf9ad698862d41034d927083426f99`.
- All four required workflows passed on that exact PR head: Python syntax #318 (run 38483634023), container runtime smoke #35 (run 38483633957), Docker packaging/full-unit-test #225 (run 38483633973), and validation-only multi-architecture #79 (run 38483633974).
- The manual UI report for application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e` recorded eight passing items and zero failures. Performance observation and a distinct error/recovery exercise were not recorded; defer them to the next UI-facing PR.
- Updated durable handoff records after merge. These documentation commits are `f18285dbed22675f4ab07febb40e19462265fc82` (`docs/PROJECT_STATUS.md`) and `29d3cacd974de0a9463f1c04dc7c729bb92b11cd` (`PROJECT_LOG.md`). Workflow lookup returned no PR-triggered runs for either documentation commit; do not claim their CI passed.
- No image publication, deployment, or production runtime verification was performed. Keep publication paused until modularization is complete and separately authorized.
- Next action: continue from GitHub `main` using `docs/MODULARIZATION_ROADMAP.md`; keep manual UI testing for the next UI-facing change and include the two deferred checks.

## 2026-10-14 — PR #31 merged after exact-head CI completed

- PR #31 (testing workflow documentation) was squash-merged to `main`; merge commit: `87e5816c4273e720352931402a223f0b61ecbf27`. Final PR head verified for merge: `135b719bfecf9ad698862d41034d927083426f99`.
- All four workflows completed successfully on that exact head: Python syntax #318 (run 38483634023), container runtime smoke #35 (run 38483633957), Docker packaging/full-unit-test #225 (run 38483633973), and validation-only multi-architecture #79 (run 38483633974). The merge was guarded by the expected head SHA.
- Manual UI report remains scoped to application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`: eight recorded items passed, zero failures. Performance observation and a distinct error/recovery exercise were not recorded and remain deferred to the next UI-facing PR.
- `docs/LOCAL_UI_TESTING.md` and testing workflow documentation are now on main. PR #31 was documentation-focused; no new manual browser run was needed for the documentation-only merge.
- No image publication, deployment, or production runtime verification occurred. GHCR publication remains paused pending completion of modularization and separate authorization.

## 2026-10-14 — PR #32 and #33 merged; PR #31 documentation reconciliation

- PR #32 is merged at 8cce5a147060fa1ccc5a69eadb91e9b090c016f4. Exact reconciled head 155e7d3b18a23b919eb60098d50c639bd2962c99 passed Python syntax #310, Docker packaging/full-unit-test #217, container smoke #27, and validation-only multi-architecture #71.
- PR #33 is merged at 25cd40eca0f20824173d7aefce76b753ef57360c from exact head 97154f6f7c482633b0cf0f71cebc2bd0afd0f558. Python syntax #313, container smoke #30, Docker packaging/full-unit-test #220, and validation-only multi-architecture #74 passed.
- PR #31's documentation branch is reconciled against main `25cd40eca0f20824173d7aefce76b753ef57360c` and includes `docs/LOCAL_UI_TESTING.md`. Code/documentation head `3eb3ec6726e0bbe03ef0df9f3d5022796feb7a0c` passed Python syntax #316, container runtime smoke #33, Docker packaging/full-unit-test #223, and validation-only multi-architecture #77. A follow-up documentation-only commit `2993273b633b865219818789c47160b8e2429a6f` records those results; its exact-head CI reruns were in progress at closeout. PR #31 remains open/unmerged pending exact-head CI and merge decision.
- Manual browser checks are required after exact-head CI for UI-facing changes. The outstanding performance observation and distinct error/recovery check are deferred to the next UI-facing PR; they do not block non-UI API/infrastructure changes by default.
- GHCR publication remains paused. No image publication, deployment, or production runtime verification is claimed.

## Latest verification closeout — 2026-10-13 (PRs #31–#33)

- **PR #31 — testing workflow documentation:** exact head `572d98d18e051bcbed7f3e74242abe1df6d0540c`; Python syntax and Docker packaging workflows both passed. The uploaded manual UI report recorded all eight tested items as passing on application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`. Performance observation and a distinct error/recovery scenario were not separately recorded; defer these to the next UI-facing PR's manual test rather than treating them as passed.
- **PR #32 — container runtime verification and paused publishing:** exact head `46db021db1367ef1e1f5e53dffdbd78bc09a880a`; Python syntax, container runtime smoke, Docker packaging, and validation-only multi-architecture workflows all passed. The smoke test covers startup, auth/setup, authenticated UI response, and account/data persistence across a container restart. No manual browser test is required for this infrastructure-only PR. Publishing remains paused until modularization is complete and separately authorized.
- **PR #33 — settings API route extraction:** exact head `22ee23d406284d59c37334f99883bb9e848bd929`; Python syntax and Docker packaging/full-unit-test workflows passed. This is an API/module refactor with regression tests and no intended UI contract change, so no manual browser test is required for this PR.
- **Merge recommendation:** PR #33 is ready for merge from the observed CI/test perspective, but merge PR #32 first because it fixes missing modules in the Docker image and adds runtime verification; integrate PR #31's testing-gate documentation as part of the same closeout. No PR was merged in this session.
- **Runtime/release boundary:** local PR #33 app account setup was verified to persist across a server restart in `~/navi-librarian-test/environments/pr-33/data`. This verifies that local test instance only, not production. No image publication, deployment, or production runtime verification occurred.
- **Next:** merge/reconcile PR #32 and PR #31, then merge PR #33 after checking its final head/CI remains valid; run the full manual browser checklist on the next UI-facing change, including performance and distinct error/recovery checks.

---

## Latest session closeout — 2026-10-13 (PR #30 merged: discovery refresh coordination)

- **PR:** [#30 — Extract discovery refresh coordination](https://github.com/abucalip/navi-librarian/pull/30) merged into `main`.
- **Merge commit:** `a12538e7f7ab2f3ec7417680d6127f5c3a1eaa5b`; final PR head: `f9256060d162ed92be0bbacc66a877c2675a5174`.
- **Implemented:** added `discovery_refresh.py` to coordinate personal and named cached-list refreshes. `navidrome_server.py` retains compatibility entry points and injects existing locks, builders, recommendation calls, and persistence.
- **Regression tests:** `tests/test_discovery_refresh.py` covers personal success and malformed JSON, lock contention, named-list success/counting, unknown lists, builder errors, and lock release.
- **Review:** complete eight-file diff reviewed; no blocking correctness issue found.
- **CI:** Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156 passed on the reviewed code head `46444e3c24dc78008e3c13dfb441059e73279814`. Docker CI ran full unittest discovery and built the image. A documentation-only update subsequently triggered Docker workflow #157; its final status was not available in the checks used during merge. Do not claim latest-head CI or merge-commit CI passed without confirming the run.
- **Limits:** connected Local_Git was unavailable (HTTP 429/404), so no local tests are claimed. No live discovery refresh, manual UI verification, image publication, deployment, or runtime verification was performed.
- **Status:** implemented and merged; deployment/runtime verification remains outstanding.
- **Next:** continue the next focused modularization boundary from merged `main`, using `docs/MODULARIZATION_ROADMAP.md` and the test plan.


## Session closeout — 2026-10-13 (PR #29 merged: discovery list persistence)

- **Merge:** [PR #29 — Isolate discovery list persistence](https://github.com/abucalip/navi-librarian/pull/29) was squash-merged to `main`. Merge commit: `001f3a7e76979d82adc62edd888d8490565b2ef3`; final PR head: `518505f6dd8e233bc6aaec4b90ec42b0669f70d5`.
- **Implemented:** `discovery_store.py` now owns SQLite persistence for cached discovery-list payloads. `navidrome_server.py` retains the compatibility wrappers and calls `_discovery_init()` as before. Added `tests/test_discovery_store.py` for missing rows, malformed JSON, Unicode, timestamp preservation, and list replacement/isolation.
- **Documentation:** added decision D-011 and updated the discovery-store test plan and project log.
- **CI:** final PR head passed Python syntax workflow #243 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507492)) and Docker packaging workflow #150 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507399)), including Python compilation, full unit-test discovery, and Docker image build. No workflow runs were returned for the squash merge commit at closeout; PR-head CI is not represented as merge-commit CI.
- **Limits:** Local_Git was unavailable (429/404), so no local tests were run. No live discovery refresh, manual UI test, image publication, or deployment occurred. Merge does not establish deployment/runtime verification.
- **Next priority:** continue the roadmap with a focused extraction of discovery-list construction/refresh coordination, keeping provider calls, persistence, and API routes separate.

---

## Session closeout — 2026-10-13 (PR #28 merged: M4 discovery recommendation extraction)

- **Merge:** [PR #28 — Extract discovery recommendation rules](https://github.com/abucalip/navi-librarian/pull/28) was squash-merged into `main`. Merge commit: `686fb393a178fe27f3806ecd5ce2138b026291cc`; final PR head: `9ab8afeaed6562424b9212f2492d34f3ed9a69ee`.
- **CI on exact PR head:** Python syntax workflow #232 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390630)); Docker packaging workflow #139 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390704)), including Python compilation, full unit-test discovery, and Docker image build. No workflow runs were returned for the squash merge commit at closeout; do not infer merge-commit CI from PR-head CI.
- **Implemented:** extracted pure discovery eligibility, normalization, genre-family, scoring, and diversity rules to `discovery_recommendations.py`; retained compatibility helpers in `navidrome_server.py`; owned-album filtering remains in orchestration. Direct-import regression tests cover the extracted rules. The complete seven-file PR diff was reviewed.
- **Review state:** PR was marked ready for review before merging. Merge was explicitly requested by the user.
- **Not performed:** no local test execution, live discovery refresh, manual UI smoke test, image publication, or deployment. Merge and CI do not prove production is running this version.
- **Next:** continue with the next priority in `docs/MODULARIZATION_ROADMAP.md`, using merged `main` as the baseline.

---

## Session closeout — M4 PR #28 reconciliation and final-head CI (2026-10-13)

- **PR:** [#28 — Extract discovery recommendation rules](https://github.com/abucalip/navi-librarian/pull/28) remains draft/open, unmerged and undeployed.
- **Final PR head:** `63bfbff79d6a0f50264bf5b6859cbe3ce0ab1158`; branch `refactor/discovery-recommendation-rules`. Reconciled with latest `main` `15497d9149b80971414df26bf1b4acfbe02863cc`; GitHub comparison reports 16 commits ahead, 0 behind, mergeable.
- **Review:** inspected the complete seven-file diff. The extraction isolates pure discovery eligibility, normalization, genre-family, scoring and diversity rules in `discovery_recommendations.py`; compatibility helpers remain in `navidrome_server.py`, and owned-album filtering remains in server orchestration.
- **Final-head CI:** Python syntax/acquisition-safety workflow #230 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432040318)). Docker packaging workflow #134 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432040385)), including Python compilation, the full unit-test suite, and Docker image build. The focused discovery regression tests are included in full unittest discovery; they were not separately invoked locally because the connected Local_Git service returned 404/429.
- **Not performed:** no local test run, live discovery refresh, manual UI smoke test, image publication, deployment, or merge. CI does not establish runtime behavior.
- **Next:** complete any remaining review and decide separately whether to undraft/merge. Do not treat this PR as deployed.

---

## Session closeout — 2026-10-13 (PR #27 merged: M3 acquisition import extraction)

- **Merge:** [PR #27 — Isolate acquisition import filesystem operations](https://github.com/abucalip/navi-librarian/pull/27) was squash-merged. Merge commit on `main`: `bf6c044ab332148e537b6888b06078c5d75f059c`; PR head: `51c8ebd8736807f35deb9045b5ea92e38d874bed`.
- **Implemented:** added `acquisition_import.py` for staged movement of verified expected tracks, destination no-overwrite checks, storage-device identity checks, rollback, and recovery manifest handling. `navidrome_server.py` retains the compatibility wrapper and injects the existing strict completion matcher.
- **Regression coverage:** added `tests/test_acquisition_import.py` for selective import/unrelated-file preservation, no-overwrite, partial-move rollback, storage identity mismatch, and reserved-manifest rejection. The existing acquisition safety harness now runs the extracted helper through the compatibility wrapper.
- **CI:** on the exact PR head, Python syntax workflow #225 passed and Docker packaging workflow #132 completed successfully, including the full unit suite and image build. No workflow runs were returned for the resulting squash merge commit at closeout; do not infer merge-commit CI from PR-head CI.
- **Review/merge state:** the complete nine-file diff was reviewed; no submitted reviews or inline review threads were present. PR #27 is merged.
- **Safety boundary:** lifecycle/status transitions, locking, dismissal/retry, failover, and interrupted-import reconciliation remain in `navidrome_server.py`. No behavioral redesign was intended.
- **Working tree/runtime boundary:** connected local checkout remains untouched on `test/pr17-reconciliation`. No local tests, live import, manual UI test, image publication, or deployment occurred.
- **Next priority:** M4 — extract discovery/recommendation scoring and eligibility behind direct-import regression tests, preserving owned-album exclusions, ranking, and diversity behavior. Keep it as a separate focused PR.

---

## Session closeout — 2026-10-13 (PR #25 merged: M2 slskd extraction)

- **Merge:** [PR #25 — Extract slskd search and quality modules](https://github.com/abucalip/navi-librarian/pull/25) was squash-merged. Resulting merge commit on `main`: `84fa2f82dba562fd221a1d588e761d2cb4907749`; PR head: `39ecdc98aee5ca0ab1c096a242b700e165837e92`.
- **Implemented:** `slskd_quality.py` owns MP3/FLAC quality classification; `slskd_search.py` owns bounded query generation, response normalization, album-path matching, track identity, bounded diagnostics, and candidate grouping/ranking. Seven existing helper names remain as compatibility wrappers in `navidrome_server.py`. Search polling/orchestration, the 45-second overall budget, thresholds, priority order, and acquisition lifecycle remain in the server.
- **Regression coverage:** added `tests/test_slskd_search_modules.py`; `docs/TEST_PLAN.md` documents focused and full test commands and the compatibility-safety boundary.
- **CI evidence:** exact PR head `39ecdc98aee5ca0ab1c096a242b700e165837e92` passed Python syntax workflow #215 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38420456388)) and Docker packaging workflow #122 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38420456324)); the Docker workflow includes the full unit suite and image build. No workflow runs were returned for the resulting merge commit at closeout; do not represent merge-commit CI as separately verified.
- **Review/merge state:** no submitted reviews, inline review threads, or PR conversation comments were recorded at merge time. The merge was explicitly authorized by the user.
- **Working tree and runtime boundary:** connected local checkout remains on `test/pr17-reconciliation` and was not changed. No local test run, live slskd acquisition, manual UI test, image publication, or deployment was performed. Merge/CI does not prove production is running this code.
- **Roadmap:** PR #23 remains separate/open. Continue from the merged `main` baseline and follow the remaining modularization priorities in project documentation; keep subsequent work focused and regression-tested.

---

## Session closeout — 2026-10-13 (M2 extraction; PR #25 ready for next review step)

- **Current state:** PR [#25](https://github.com/abucalip/navi-librarian/pull/25) is open, draft, unmerged, and not deployed. Branch `refactor/slskd-search-quality-modules`; base `main` at `0529c6912fdd9bea951334abec0f63c9cdbfd1d1`; application-code head `e8a4256aaf34956ab1c4ca15b0b302c107689736`; subsequent commits update documentation only.
- **Implemented:** extracted quality classification to `slskd_quality.py` and query/response/path/candidate helpers to `slskd_search.py`; retained seven legacy helper names as compatibility wrappers in `navidrome_server.py`; added direct-import regression tests and updated the test plan.
- **Verification:** final head `e8a4256aaf34956ab1c4ca15b0b302c107689736` passed Python syntax workflow #211 and Docker packaging workflow #118. The Docker workflow includes the full unit suite and image build. Earlier code CI caught stale callback helper references; these were fixed before passing runs. The documentation closeout triggered fresh workflows #213 and #120, which were in progress at the last check. No local test execution, live slskd test, or manual UI test was performed.
- **Preserved state:** local checkout remains untouched on `test/pr17-reconciliation`; no merge, image publication, or deployment.
- **Next priority:** inspect the full PR #25 diff and confirm review readiness, then undraft/request review as appropriate. Merge only with explicit authorization. PR #23 remains separate/open.

---

## Latest session — 2026-10-13 (M2 slskd extraction; CI passed, PR #25 draft)

- **PR:** [#25 — Extract slskd search and quality modules](https://github.com/abucalip/navi-librarian/pull/25), draft and unmerged. Branch `refactor/slskd-search-quality-modules`, based on current `main` SHA `0529c6912fdd9bea951334abec0f63c9cdbfd1d1`; latest code commit with passing CI is `50bf72d44073b415ed07a59bc5b7707b76a59a31`.
- **Implementation:** `slskd_quality.py` contains MP3/FLAC tier classification. `slskd_search.py` contains query generation, response normalization, album-path matching, track identity, bounded path diagnostics, and candidate grouping/ranking. Seven existing helper names in `navidrome_server.py` remain as compatibility wrappers. Search polling/orchestration, the 45-second total budget, delayed-payload handling, thresholds, saved priority order, and queue/import lifecycle remain in the server.
- **Regression coverage:** added `tests/test_slskd_search_modules.py` using direct imports; the legacy acquisition safety suite still passes through the compatibility wrappers.
- **CI:** on code commit `50bf72d44073b415ed07a59bc5b7707b76a59a31`, Python syntax/acquisition-safety workflow #209 passed and Docker packaging workflow #116 passed, including the full unit suite and Docker image build. The initial draft CI caught stale helper names left in two extracted callback paths; these were corrected in `50bf72d`, and both workflows passed on that exact code commit. No local test run or live slskd/UI test was performed.
- **Local checkout/deployment:** local checkout remains untouched on `test/pr17-reconciliation`. Not merged or deployed. PR #23 remains separate/open.
- **Next:** inspect the final PR diff and check CI on the latest documentation-updated head; then request review/undraft only when ready. Do not merge or deploy without the normal review and merge authorization.

---

## Latest session — 2026-10-13 (M2 slskd search/quality extraction in review)

- **Branch/base:** `refactor/slskd-search-quality-modules`, created from current GitHub `main` at `0529c6912fdd9bea951334abec0f63c9cdbfd1d1`. The connected local checkout remains on `test/pr17-reconciliation` with pre-existing work; it was not switched or modified.
- **Implementation:** added importable `slskd_quality.py` for MP3/FLAC tier classification and `slskd_search.py` for query generation, response normalization, album-path matching, track identity, bounded path diagnostics, and candidate grouping/ranking. Existing private helper names remain as compatibility wrappers in `navidrome_server.py`; the search deadline, polling loop, candidate thresholds, quality order, and queue/import orchestration were not intentionally changed.
- **Regression coverage:** added `tests/test_slskd_search_modules.py` using direct imports for quality tier/priority behavior, query order/deduplication, response shapes, path/track normalization, candidate deduplication/ranking, and bounded diagnostics. Existing acquisition lifecycle tests remain in place.
- **Superseded status:** this implementation-stage note is retained as history; final-head CI subsequently passed on `e8a4256aaf34956ab1c4ca15b0b302c107689736` (Python syntax workflow #211 and Docker packaging workflow #118). See the session closeout above for current verification and next steps.

---

## Latest session — 2026-10-13 (PR #24 merged; resulting main commit verified)

- **PR:** [#24 — Extract acquisition completion matching helpers](https://github.com/abucalip/navi-librarian/pull/24), squash-merged from `refactor/acquisition-completion-matching` at head `b826ae14d917431d07aacf97200990d57133cba0`. Merge commit: `225add7405bfd72b3254af23745d0dd9a84b621c`.
- **Extraction:** filename identity, safe folder-name normalization, and strict completed-track matching live in importable `acquisition_completion.py`; compatibility wrappers remain in `navidrome_server.py`; direct-import tests replace AST extraction for the migrated matcher.
- **Review correction:** when multiple local files match the expected basename identity and advertised size, the matcher now returns `None` immediately. Collision-suffix fallback is allowed only when no exact match exists, preventing an alternative filename from masking an ambiguous exact match.
- **Regression test:** added a case-variant exact-name pair plus a same-size `Track_1.flac` alternative; the matcher must fail closed. The test skips on filesystems that cannot represent distinct case-variant names.
- **Current code/test commits:** source fix `b8fad33cfaad87b1ed8d2b4fc3d84166f396b15f`; regression test `e163a20fe4407491398ce56e1f4c9777f8aa53bf`. Documentation is updated on this PR branch, including the test plan, this status record, and `PROJECT_LOG.md`.
- **Verification status:** final PR head `b826ae14d917431d07aacf97200990d57133cba0` passed Python syntax workflow #202 and Docker packaging workflow #109, including compilation, full unit tests, and image build. After squash merge, GitHub confirmed PR #24 is merged and `main` points to `225add7405bfd72b3254af23745d0dd9a84b621c`; the commit contains `acquisition_completion.py` and updated project docs. No local test run, manual UI test, image publication, or deployment was performed.
- **Branch relationship:** PR #23 contains the modularization roadmap but remains separate/open; PR #24 is based on `main` and does not include that roadmap.
- **Session close:** PR #24 is merged and the resulting `main` commit was verified through GitHub PR metadata, commit retrieval, recent-commit search, and file reads. PR #23 remains a separate roadmap PR. No local test run, manual UI test, image publication, or deployment occurred.
- **Next priority:** proceed with M2 on the verified baseline: extract slskd search and quality evaluation into focused modules with regression tests. Keep PR #23 separate unless its dependency/order is explicitly revisited.
- **Documentation closeout:** the session's status and log updates are committed to `main`; latest documentation commit is recorded in `PROJECT_LOG.md`. PR #23 remains open and unmerged. No additional code change, local test run, manual UI test, image publication, or deployment occurred during closeout.
---

## Latest session — 2026-10-13 (PR #21 and #22 merged; acquisition fixes verified)

- **PR #21:** [Add Hi-Res FLAC priority and acquisition diagnostics](https://github.com/abucalip/navi-librarian/pull/21) squash-merged to `main` at `049a1e94ea782fa473fc4f394711dda1afec6fbe`.
- **PR #21 behavior:** added the sixth sortable FLAC Hi-Res tier, preserved saved quality order during migration, improved bounded slskd query fallback/diagnostics and safe source failover, and kept polling when slskd reports peers before exposing their file payloads. Overall search budget is 45 seconds; matching and acquisition safety rules were not relaxed.
- **Live verification:** user tested the combined PR #21/#22 checkout and reports Tinariwen — `Idrache (Traces of the Past)` started downloading. This verifies the delayed slskd peer-payload fix in the tested environment.
- **PR #21 CI:** Python syntax/acquisition-safety workflow #179 and Docker packaging workflow #86 passed on head `2d617091390f81c05ff6c40d5a8fa140c6217b68`. Docker workflow includes compilation, full unit tests, and image build.
- **PR #22:** [Allow retrying dismissed acquisitions](https://github.com/abucalip/navi-librarian/pull/22) squash-merged to `main` at `7d6094042f0beb4538313011594539a34254fbd9`.
- **PR #22 behavior:** an explicit Get can reopen only a persisted `dismissed` acquisition when its guarded update succeeds; the stale source candidate and settings are cleared before a fresh search. Failed reactivation remains blocked. Added regression coverage for successful reactivation and failed reactivation; `docs/TEST_PLAN.md` now includes the retry lifecycle check.
- **PR #22 CI:** Python syntax/full unittest workflow #182 and Docker packaging workflow #89 passed on head `04a11671862e1e3544ac878760f2223a42058ed9`. The first test attempt exposed a test-fixture issue (the real acquisition implementation ran instead of the stub); the fixture was corrected, and both workflows passed on the final head.
- **Verification boundary:** the user explicitly confirmed the Tinariwen download. No separate live result for retrying a previously dismissed album was reported, although the regression tests passed. No image publication or production deployment was performed; do not infer the server is running these merges.
- **Next:** no further action for this session. For a future release, publish/deploy separately and verify the running image digest and application behavior.

## Latest session — 2026-10-13 (wait for slskd peer payloads before query fallback)

- **Branch:** `fix/slskd-search-payload-wait`, created from PR #21's latest observed head `2876098ed222cc8803f292c55aa8e3474331e3e5`. Not yet opened as a PR, merged, or deployed. PR #21 and stacked PR #22 remain unchanged.
- **Root cause evidence:** the user's three slskd search IDs returned HTTP 200 from both state-with-responses and the dedicated `/responses` endpoint. Once completed, they exposed 26–33 peer records and hundreds of files. During Librarian's bounded search window, the card had recorded zero collected peer payloads while each search was still `inprogress`. This points to premature fallback/termination while slskd was still exposing results, not a payload-shape mismatch.
- **Implementation:** increased the overall search budget from 30 to 45 seconds. Once slskd reports at least one peer but no file payload has yet been collected, continue polling the same search through the overall deadline instead of immediately spending the remaining time on fallback queries. Search timeout values and album/quality matching rules are unchanged.
- **Regression test:** added a mocked delayed-payload scenario where slskd reports 26 peers for more than the initial 18-second query window and only later returns peer records. The test asserts Librarian keeps polling the same query and collects the payload.
- **Verification:** on code/test commit `1aad9fc90d2ceeb1659473131d4f4a867f739b63`, Python syntax/acquisition-safety workflow #177 passed, including the delayed-payload regression, and Docker packaging workflow #84 passed compilation, the full unit suite, and Docker image build. The two documentation-only follow-up commits do not change application behavior. No local test run or live slskd retest has occurred. Do not merge until the Tinariwen live retest passes.
- **Next:** run CI on this branch and test Tinariwen in the existing `prox-mcp-pr17-test` data environment using the isolated port-8089 checkout. Keep the port-8088 app untouched and do not run two instances against the same SQLite data simultaneously.

## Latest session — 2026-10-13 (zero-response slskd search fallback implemented; automated verification passed)

- **Branch/PR:** fix/flac-hires-acquisition-diagnostics, PR #21; PR #22 remains stacked on this branch. Neither PR is merged or deployed.
- **User clarification:** the Tinariwen Idrache (Traces of the Past) search inspected in slskd was launched automatically by Librarian, not separately initiated.
- **Implementation:** when a query returns no usable peer file payloads, try up to three ordered queries: exact artist+album, punctuation-normalized artist+album, then artist+primary title with a parenthetical subtitle removed. Stop at the first usable file payload set. The total search budget is capped at 30 seconds; fallback attempts use shorter slskd timeouts. Candidate matching and queue/import safety remain unchanged.
- **Diagnostics:** no-match state records each attempted query, search ID/state, slskd-reported response/file counts, and collected peer payload counts. The acquisition card message also shows the attempted query sequence, distinguishing collected payloads from slskd-reported counts.
- **DroppedNeedle review:** adapted the bounded-query-plan principle and separation between retrieval and candidate validation; no code copied.
- **Automated verification:** on code/test commit dd22005da57225ec788e6e8290501b15b7f0a602, Python syntax/acquisition-safety workflow #172 passed and Docker workflow #79 passed compilation, the full unittest suite, and Docker image build. On the later docs-only head 9f4e82721a330826a1d5f91c6027428cd01362f6, Python syntax/acquisition-safety workflow #175 passed; Docker workflow #82 passed compilation and the full unittest suite, with image build still in progress at the last check. Regression coverage includes mocked exact-query-empty → broader-query-response fallback, visible query diagnostics, query order, blank inputs, and shorter fallback timeouts.
- **Remaining verification:** no live slskd retest or production deployment has occurred. Retest Tinariwen in prox-mcp-pr17-test before merging. If it still fails, inspect search_queries_attempted to distinguish query recall from response-payload collection.

## Latest session — 2026-10-13 (Hi-Res FLAC priority and acquisition diagnostics in progress)

- **Branch:** `fix/flac-hires-acquisition-diagnostics`, based on GitHub `main`; not merged or deployed.
- **Scope:** add a reorderable FLAC Hi-Res quality tier, recognize common resolution labels including `[24-44.1]`, preserve prior quality ordering when migrating four- or five-tier settings, and expose bounded candidate summaries plus path/artist match signals when no source folders are recognized.
- **Regression coverage:** added tests for the reported Tinariwen folder-name variants, explicit 16/44 metadata, 24/44.1 filename labels, high-resolution metadata, and settings migration/order preservation.
- **Root-cause boundary:** the Tinariwen folder variants pass the album-token matcher in a fixture. Queue handling now retries other eligible peers after explicit 400/404/422 rejections, treats 401/403 as global auth/permission failures, and conservatively monitors timeouts/5xx. Follow-up report for Bombino — Agamgam: the card says `no_matches` with 0 peer responses although the user saw four sources. Added normalized slskd response parsing and a short grace retry when search state reports peers before response payloads are visible; diagnostics retain slskd-reported response/file counts. Live confirmation still requires retesting.
- **Verification:** on queue-failover code commit `8df498909ca4ac1e1df6fe1b726e5f018ff749d3`, Python syntax/acquisition-safety workflow #150 passed and Docker packaging workflow #57 passed compilation, the full unit-test suite, and Docker image build. A later documentation-only commit records the results. No local test runner was available through the connected read-only Git checkout, and no live slskd request was made.
- **Next:** review CI on the PR head, then test in the existing `prox-mcp-pr17-test` environment with the Tinariwen acquisition (or another known result). If it still fails, capture the returned status, `candidate_diagnostics`, and `attempts` before changing the queue logic.

## Latest session — 2026-10-13 (PR #20 merged; five-tier quality priority verified)

- **PR #20:** [Add FLAC 16/44 and sortable quality priorities](https://github.com/abucalip/navi-librarian/pull/20), squash-merged into `main` at merge commit `a9218bb5cb5c663b7ef26dc5f42cd69bbeadba45`.
- **Implemented:** added FLAC 16-bit/44.1 kHz as a fifth acquisition quality tier. Existing four-tier settings migrate by appending the new tier without changing the prior order; quality priority remains five unique supported tiers and persists in the existing Settings API.
- **Settings UI:** replaced the per-tier dropdowns with a draggable ordered list and accessible Move up/Move down controls. FLAC 16/44 classification requires explicit sample-rate/bit-depth metadata or a filename label; unknown FLAC retains the existing fallback.
- **Automated verification:** on exact PR head `ac43126efdea9a6ac5cbe36d81b26b11c23da509`, Python syntax/full unittest workflow #141 and Docker packaging workflow #48 both passed. The Docker workflow included dependency installation, compilation, full unit tests, and image build.
- **Manual verification:** user tested the PR20 build in the existing `prox-mcp-pr17-test` environment and reports all is good, including Settings behavior. This is user-reported UI verification.
- **Deployment:** PR merge is complete. No image publication or production deployment was performed as part of this session; do not infer the server is running this commit.
- **Next:** continue from GitHub `main`. Publish/deploy separately if requested, then record the exact image digest and verify the running service.

## Latest session — 2026-10-12 (PR #17 merged; workflow documentation merged)

- **PR #17:** squash-merged at `9f4ff509d6a336823912c49d8c049eeea8761b8f`. User reports completed downloads now appear imported; acquisitions failing due to unavailable sources are expected. No import-safety checks were weakened.
- **PR #18:** could not be merged because its project-status edit conflicted with the PR #17 update. Closed as superseded, with its workflow content preserved in replacement PR #19.
- **PR #19:** [docs: reconcile GitHub-first workflow and project handoff](https://github.com/abucalip/navi-librarian/pull/19), squash-merged at `fe60dd3aaf323bd6f3489f89b13ee9946ba7f382`. Added `docs/DEVELOPMENT_WORKFLOW.md`, recorded decision D-009, and updated this status and `PROJECT_LOG.md`.
- **CI on PR #19 head** `bca1b143f45b870492f99c86ecdc5ef9ed9d6ec7`: Python syntax/acquisition-safety workflow #136 passed; Docker packaging workflow #43 passed, including compilation, unit tests, and Docker image build. Documentation-only change.
- **Deployment:** no image publication or production deployment was performed. The merges and packaging validation do not prove that the server is running a new image.
- **Next:** continue from GitHub `main`. If a release is requested, separately publish/pull the image, record its digest, and verify the running service.

## Latest session — 2026-10-12 (PR #17 merged; acquisition behavior manually verified)

- **PR #17:** [Diagnose acquisition completion and handle missing slskd transfers](https://github.com/abucalip/navi-librarian/pull/17) was squash-merged into GitHub `main` at merge commit `9f4ff509d6a336823912c49d8c049eeea8761b8f`.
- **Manual verification:** the user reports completed downloads now appear imported. Some acquisitions failed because no sources were available; the user confirmed this is expected and not a regression.
- **Fixes retained:** bounded acquisition-completion diagnostics; HTTP 404 from slskd's per-peer transfer endpoint is treated as an empty current transfer list while filesystem completion checks continue; non-404 HTTP errors still surface. Import-safety checks were not relaxed.
- **CI:** Python syntax/full unittest workflow #134 and Docker packaging workflow #41 passed on PR #17 head `ff2153bbaf790b2c0bbfce03c8c7fdb6c7decc12` before merge. User's manual report adds runtime evidence for completed imports.
- **Deployment:** merge does not establish that a new Docker image was published or that the server was updated. No deployment was performed in this session.
- **Documentation workflow:** PR #18's GitHub-first workflow content is being carried forward in a fresh branch based on the updated `main`, because its original branch conflicted after PR #17 merged. The replacement PR will be the merge target; no local-only code or commits are involved.
- **Next:** merge the reconciled documentation PR, then treat image publication/deployment as a separate step if requested.

## Latest session — 2026-10-12 (slskd monitor-error follow-up; fix in progress)

- **User-reported failure:** several acquisitions entered `monitor_error`. Their persisted details showed `HTTPStatusError: 404 Not Found` from `GET /api/v0/transfers/downloads/{username}` for multiple peers.
- **Root cause:** the watcher treated a missing per-peer transfer-list entry as an exception even though slskd may no longer expose a peer under that endpoint after its transfer records disappear. This caused an ordinary “no current transfer records” condition to surface as a monitor failure.
- **Fix committed on the existing PR #17 branch:** `_slskd_download_transfer_files` now returns an empty list for HTTP 404. The watcher continues its filesystem checks on each polling cycle; all other HTTP errors still raise and remain diagnosable. No import or folder-matching safety checks were relaxed.
- **Regression test added:** `tests/test_slskd_transfer_lookup.py` covers the 404 case, a non-404 HTTP error, and successful transfer parsing.
- **Commits:** fix `4ced0a22b980325dde58609087700d0926b65bde`; test `e946d460acc11fb675bd25c1358ef3d243c32dd5`; test-plan documentation `4ee60d4151899ad5406da979c00d7995e7e8f768`.
- **Verification:** user previously reported 47 tests passed on the earlier PR #17 revision (`17a2bdc`). On code commit `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd`, GitHub Actions Python syntax/test workflow #131 passed (compile plus full `unittest discover`) and Docker packaging workflow #38 passed (dependency install, compile, unit tests, Docker build). Subsequent commit `221dcaca3fe23f44dc69e68e3a5eef694a8754d8` changed only `PROJECT_LOG.md`; no local test run or manual acquisition retest has occurred.
- **State:** PR #17 remains open; this branch is not merged or deployed. The current task is to run the full test suite and CI on the new head, then have the user retest acquisitions. If monitor errors persist, capture the new status details rather than assuming this is the only possible failure.
- **Next:** verify the updated branch with syntax checks, the full unittest suite, and CI; inspect the final diff before merging.

---

## Latest session — 2026-10-12 (v0.2 P0: completed-folder diagnostics in progress)

- **Objective:** diagnose why a transfer reported complete remains in `download_complete_waiting_for_folder`, without weakening folder identity or track-completeness checks.
- **Branch:** `fix/v02-acquisition-completion-diagnostics`, based on GitHub `main`; this is separate from the user's local-only testing baseline `main` at `90e1d97`. Do not assume the two baselines are identical.
- **Implementation in progress:** added `acquisition_completion.py` to inspect completed-download folders and return a bounded set of actionable reasons; integrated those diagnostics into the watcher status details; added focused tests in `tests/test_acquisition_completion.py`.
- **Safety invariant:** only a unique folder with the expected basename and all expected files accepted by the existing strict matcher can be imported. Diagnostics do not relax matching.
- **Verification state:** GitHub Actions Python syntax/test workflow #123 passed on code commit `53309559c4e910779575fee3fc9941a596f78ac1`, including the full unittest discovery run. Docker packaging workflow #30 also passed, including Docker image build. This verifies packaging only, not deployment. No local test run was performed. The folder-name mismatch is a diagnostic fixture, not proof that it is the production failure's actual cause.
- **Next:** inspect the full diff, run syntax and full unit tests in CI, address failures, then use the emitted diagnostics to establish the real-world root cause before deciding whether a matching behavior change is justified.
- **Deployment:** not merged, published, or deployed.

---

## Latest session — 2026-10-12 (local main consolidated for testing)

- **Local merge:** the user merged `fix/artwork-size-and-artist-bios` into local `main`; the local merge commit is `90e1d97` (`Merge local artwork and acquisition fixes`). Local branch listing confirms this commit is the head of `main`.
- **Testing workflow:** the user reports that `main` passed their tests. The exact commands, test names, and output were not provided in this session, so this is recorded as user-reported validation rather than independently reproduced test evidence.
- **Purpose:** use local `main` as the sole testing ground going forward. Keep the feature branch as a temporary reference until the merged state is comfortably established; avoid deleting branches or cleaning worktrees without checking their contents first.
- **Remote/deployment boundary:** this local merge has not been confirmed pushed to GitHub and this session did not deploy anything. The remote default branch and server must not be assumed to contain commit `90e1d97`.
- **Session actions:** inspected the available local branch/status/log views and current GitHub documentation. The connected local Git tool is read-only, so the documentation handoff is being recorded on GitHub; local working-tree documentation was not edited directly.
- **Next:** continue development/testing from local `main`. If this merged code should become the shared release baseline, review the diff against remote `main`, then push through the normal Git workflow and verify CI before considering deployment.

## Latest session — 2026-10-12 (PR #16 merged; image published)

- **PR:** [#16 — Fix artwork loading after transient provider failures](https://github.com/abucalip/navi-librarian/pull/16), squash-merged into `main`.
- **Merge commit:** `ac0eec1e628caa0b300e651fcbdbe25535515395`.
- **Fix:** artwork provider failures are retryable and not negative-cached; browser retries transient failures with bounded backoff. Album-year and artwork request promises now use separate caches, fixing the all-covers-missing regression discovered during manual testing.
- **Regression tests:** `tests/test_artwork_retry.py` and `tests/test_artwork_cache_isolation.py`.
- **CI:** Python syntax/test workflow run #114 passed; Docker packaging run #22 passed. Docker publish workflow run #11 passed for merge commit `ac0eec1e628caa0b300e651fcbdbe25535515395`.
- **Published image:** `ghcr.io/abucalip/navi-librarian:latest` and `ghcr.io/abucalip/navi-librarian:sha-ac0eec1`; manifest digest `sha256:7a9415a7e6d10bd9864a2e03db8c452cfdc35cb69359eaa0e9b0552552afb5b1`.
- **UI verification:** user tested the PR build and reports album artwork now loads very fast.
- **Deployment distinction:** image is published, but this session did not have access to the media VM's Docker/Compose shell and did not pull/recreate the production container. Host deployment is pending; follow `docs/DEPLOYMENT.md` and record the running image digest after the host update.
- **Next:** pull and recreate only `discair` on the media VM, then verify container health and artwork in the deployed UI. Sync local Git without overwriting unrelated local changes.

## Latest session — 2026-10-13 (broaden zero-response slskd searches in progress)

- **Objective:** resolve acquisitions that stop at no_matches because Librarian's exact artist+album query yields no usable peer payloads, as reported for Tinariwen — Idrache (Traces of the Past).
- **Change committed to PR #21 branch** fix/flac-hires-acquisition-diagnostics: search exact title first, then retry with punctuation-normalized text, then with the primary album title (parenthetical subtitle removed) only when the preceding query yielded no usable peer file payloads. Artist+album candidate matching, quality checks, and import/queue safety remain unchanged.
- **Diagnostics:** record each query attempted, its search ID/state, slskd-reported peer/file counts, and collected peer payload count. The no-match message distinguishes collected responses from slskd-reported counts rather than blaming album-folder matching when no payload was collected.
- **DroppedNeedle review:** its modular search/acquisition service design reinforces keeping the query plan bounded and matching/safety checks separate. No code copied; the existing Librarian/slskd integration remains in place.
- **Verification:** regression tests for query ordering and blank inputs are committed. CI and live test in prox-mcp-pr17-test are pending. Do not merge PR #21/#22 or deploy until the new CI and Tinariwen retest are complete.
- **Next:** run full syntax and unittest CI, then retest the exact Tinariwen acquisition in the existing test environment and inspect search_queries_attempted if it still fails.

# Project status and handoff

Last updated: 2026-10-13

## Source of truth

- Repository: [abucalip/navi-librarian](https://github.com/abucalip/navi-librarian)
- Default branch: `main`
- PR #14 documentation merged at `74264b29062504fce3bf6f7a65121fa43b9f8ec5`; PR #15 v0.2 planning merged at `f32b02a13b582e23699bde294eb94b51e5f646cc`.
- Latest documentation handoff commit before this update: `8153c3b05f1f84725a4d537d7417c95433bb040c`.
- **Deployment and manual verification:** the user reports Librarian is installed on the server and tested successfully; the GHCR Docker package has been made public. Account creation, entering service credentials in Settings, downloads, and imports all work as intended.
- The user report supersedes the earlier GHCR `unauthorized` blocker. The current image digest, deployed commit/tag, and host-side logs have not been independently recorded in this documentation session; do not invent them.
- The developer's local checkout has a separate in-progress branch with commits not necessarily present on `main`. Do not assume local changes are merged or deployed.

## Product summary

Discair combines a web UI with existing music-discovery and acquisition logic in `navidrome_server.py`. The web app is served by FastAPI from `app/main.py`. It connects to an existing Navidrome instance and slskd service; neither is bundled into the app container.

## Feature ledger

Use the following meanings consistently:

- **Planned** — agreed requirement, no implementation evidence yet.
- **In progress** — being changed; do not rely on it.
- **Implemented** — code exists, but no adequate test evidence recorded.
- **Tested** — automated or manual validation passed and the scope is recorded.
- **Merged** — change is present on the default branch.
- **Deployed** — a specific image/commit was installed in the target environment.
- **Verified** — deployed behavior was checked in the running app.

| Area | Known state at this baseline | Next verification |
|---|---|---|
| Web UI and API | Deployed; user reports successful installation/use | Record exact deployed image tag/digest and commit when convenient |
| First-run account creation and login | User reports working successfully on the server | Preserve as a regression-smoke-test baseline |
| Settings and service credentials | User reports entering credentials through Settings works | Keep secret-handling and persistence tests in the automated suite |
| Audio quality priorities | PR #20 merged; automated CI and user manual Settings drag/drop/save/reload testing passed | Deployment of the merged commit is separate and not verified here |
| Recommendation/discovery logic | Existing logic is in `navidrome_server.py` | Test representative outputs against the real library |
| Discovery lists, feedback, refresh | API routes exist | Verify list persistence, dismiss/save behavior, and refresh |
| slskd downloads/acquisition | User reports downloads work as intended | Continue regression coverage for matching, queueing, status, and safe cleanup |
| Album imports | User reports imports work as intended | Preserve import-safety regression tests |
| Album artwork, release years, biographies, platform search links | Implemented in development history; verify exact default-branch coverage | Visual smoke test when UI changes affect these cards |
| Unit tests | Tests exist under `tests/` | Run the exact commands in [TEST_PLAN.md](TEST_PLAN.md) for code changes |
| Docker image build/publication | User reports package is now public; prior authorization blocker considered resolved | Check workflow and record image tag/digest for a future release |
| Production deployment | Installed and manually tested according to user report; exact image digest/host evidence not captured in this session | Record tag/digest and deployment details at next release/update |

## Latest session — 2026-10-12 (handoff updated from user verification)

- **New operational evidence from user:** Librarian is installed on the server and has been tested successfully. The Docker package has been made public.
- **Working baseline confirmed by user:** first-run account creation, entering service credentials through Settings, downloads, and imports work as intended.
- **Status correction:** previous notes that treated deployment as unverified and GHCR `unauthorized` as an active blocker are superseded by this report. Deployment and the named workflows are user-verified; the exact deployed image tag/digest and independent host evidence remain undocumented.
- **This documentation session:** no application code, settings, or server deployment changed. Updated project handoff and deployment notes to reflect the user's report; no automated application tests or live host checks were run.
- **Next:** keep these working flows as regression baselines. Before v0.2 implementation, inspect the actual code/tests and begin with a narrowly scoped acquisition-completion reliability improvement plus regression tests. At the next image update, record the deployed tag and digest.

## Previous session — 2026-10-12 (PR #15 merged)

- **PR:** [#15 — docs: plan v0.2 improvements from DroppedNeedle review](https://github.com/abucalip/navi-librarian/pull/15), squash-merged into `main`.
- **Merge commit:** `f32b02a13b582e23699bde294eb94b51e5f646cc`.
- **Documentation:** added [`docs/V0.2_DROPPEDNEEDLE_LESSONS.md`](V0.2_DROPPEDNEEDLE_LESSONS.md), a prioritized planning backlog covering acquisition completion evidence, safe lifecycle boundaries, consistent quality evaluation, recommendation pipeline clarity, caching review, and regression/performance guardrails.
- **Constraints recorded:** preserve Librarian's Navidrome–slskd bridge and library-/taste-aware recommendations; prioritize smoothness and stability; modularize Python responsibilities incrementally; do not copy DroppedNeedle code without reviewing AGPL-3.0 implications.
- **CI:** GitHub Actions reported both Python syntax check and Docker packaging validation successful for PR head `3e1f005e413a5522ec2866f30baebf1914cc4868`. This was documentation-only; application tests and UI smoke tests were not run.
- **Local checkout:** previously recorded as preserved on `fix/artwork-size-and-artist-bios`; inspect its current state before any Git operations.

## Latest session — 2026-10-12 (artwork loading reliability fix in review)

- **Branch:** `fix/artwork-loading-retries`; application change and regression test committed, not merged or deployed.
- **Follow-up from manual test:** the user reported that all covers disappeared when testing this branch. Root cause found in the frontend: album-year lookups and artwork lookups shared `artworkRequests`, keyed by artist+album, so the artwork renderer could reuse the `/api/album-year` promise and receive no `artwork_url`. Fixed by giving year lookups their own `albumYearRequests` cache; added `tests/test_artwork_cache_isolation.py`.
- **Follow-up validation:** fix and regression guard are committed on the PR branch, but CI and live UI retest are pending. Do not merge or deploy until covers are confirmed.
- **Observed failure mode in code:** artwork provider exceptions were converted into a normal no-artwork response and negative-cached for five minutes. The browser's one-shot IntersectionObserver unobserved the card immediately and marked it requested permanently, so transient provider outages left cards blank for the rest of the page session.
- **Change:** distinguish transient provider failures with a `retryable` response, do not negative-cache those failures, and retry in the browser up to three times with bounded backoff. Genuine no-match responses retain the existing negative cache and placeholder behavior.
- **Regression test:** added `tests/test_artwork_retry.py` to verify a provider timeout is marked retryable and does not populate the negative cache.
- **Validation:** GitHub Actions passed Python compilation and the full unittest suite (run #110) and Docker packaging validation (run #17) on tested code commit `fabcd1fb6563ef9cd65aa12005f2f77f3f90e07d`. The later documentation-only handoff commits do not change application code. Manual UI behavior remains unverified; not merged or deployed.
- **Next:** open/check the PR, run the full test plan and CI, then manually load Discoveries and Artist Deep Dives and confirm covers appear and that provider outages do not block browsing.

## Session start checklist

1. Read this file and [REQUIREMENTS.md](REQUIREMENTS.md).
2. Check the GitHub default branch, active PRs, and the exact commit being tested.
3. Inspect `git status`, current branch, recent commits, and the actual diff before editing.
4. Identify the acceptance criteria and regression tests for the task.
5. Keep unrelated local work untouched; use a separate branch/worktree for experiments.

## Session end checklist

Update this file and [PROJECT_LOG.md](../PROJECT_LOG.md) with:

- branch, PR, and commit SHA;
- files and behavior changed;
- tests run and exact pass/fail result;
- status transitions (do not equate implemented, merged, deployed, and verified);
- unresolved defects and the next concrete action.

Never record credentials, API keys, cookies, or other secrets in documentation.


## 2026-10-14 — Authentication route extraction CI closeout (PR #39)

- **PR/branch:** [PR #39 — refactor: extract authentication API routes](https://github.com/abucalip/navi-librarian/pull/39), `refactor/auth-api-router`.
- **Code base:** merged main `84da7ebfe51199a5caf63f7689fe89df8d61b553`; auth integration contract tests were merged in PR #38 before extraction.
- **Verified code head:** `a78272da8f82aa83716367aa7fcd7a43729267a7`. All four required GitHub Actions workflows completed successfully on that exact head: Python syntax, Docker packaging (including full unit suite), container runtime smoke, and validation-only multi-architecture build.
- **Change:** moved `/api/auth/status`, `/api/auth/setup`, `/api/auth/login`, `/api/auth/logout`, and `/login` route handlers into `app/api/auth.py`. Middleware and session/auth primitives remain in `app/main.py` and `app/security/auth.py`; dependency injection keeps app-owned settings, cookies, and password/session behavior explicit.
- **State:** implemented and CI-verified on `a78272d`; PR #39 remains open and unmerged. The documentation closeout itself adds a new PR-head commit, so recheck all required workflows against the resulting exact head before merging. No local test run, manual UI test, image publication, deployment, or production runtime verification was performed. Publishing remains paused.
- **Next:** wait for CI on the documentation-updated PR head, review the final diff and mergeability, then merge only if all required checks pass.

## 2026-10-14 — Acquisition extraction dependency closeout (PRs #47–#48)

- **PR #47:** merged to `main` at `1877dca3187f7cbde85b211d5414e558f12da502` (squash merge). The extracted `acquisition_lifecycle.py` policy and its direct regression tests are now on the authoritative branch.
- **PR #48:** remains open and unmerged at head `115e1f9373744d361a20f0ba20c35589db0ca099`. Its branch was based on the pre-squash history and diverges from updated `main`; comparison reports 31 commits ahead and one behind, and GitHub reports it is not mergeable. The displayed combined diff still includes PR #47's lifecycle files/changes alongside the intended orchestration extraction.
- **CI evidence:** the four required workflows passed on the existing PR #48 head (Python syntax, Docker packaging, container runtime smoke, validation-only Docker image build). These results apply only to that old, unreconciled head and are not evidence for a cleaned branch.
- **Safety decision:** PR #48 was not merged, force-pushed, or rewritten. No tests were run in a local checkout during this closeout. No publishing, deployment, or production runtime verification occurred.
- **Next action:** reconstruct/rebase the orchestration extraction onto current `main`, retaining only its intended implementation, direct regression tests, packaging changes, and relevant documentation. Review the full diff and run all required workflows on the exact new head before reconsidering merge.


## 2026-10-14 — PR #49 merged; PR #48 orchestration reconstructed

- PR #49 documentation closeout was squash-merged at `c972278566d8ec68f3755f464df1afb5a8a18f56` after all four required workflows passed on exact head `f4712aa2703d4f1deae6a0532502f27123b80fc6`.
- The original PR #48 branch remains unsuitable for merge because it carries pre-squash history. A clean reconstruction was started from updated `main` on `refactor/acquisition-orchestration-reconstructed`.
- Intended scope: extract only the persisted manual source-skip transition into `acquisition_orchestration.py`, keep the MCP adapter and safety boundaries, add direct-import tests, and package the module in Docker. No cleanup/import implementation or filesystem safety rule is changed.
- Reconstructed final head `9185f3c12ace7c82a61ff04c062044ab9c33cdf6` passed all four required workflows: Python syntax (`38587910860`), Docker packaging/full unit suite (`38587910842`), container runtime smoke (`38587911440`), and validation-only multi-architecture image validation (`38587911187`). The final diff was reviewed; no PR review submissions or inline review threads were present. PR #50 is open and ready for review; it has not been merged.
- No separate local test run is claimed. No publication, deployment, or production runtime verification occurred.


## 2026-10-14 — PR #50 acquisition orchestration merged

- PR #50 was squash-merged after the complete final diff review and all four required workflows passed on exact PR head `c8610fdc44ea93bcfb55a654598792aee78e7ecb`.
- **Merge commit:** `a37d29cf11657dce6d5cbc6cb928ca840fe5b206`.
- CI evidence on the exact PR head: Python syntax (`38589006636`), Docker packaging/full unit suite (`38589006609`), container runtime smoke (`38589006569`), and validation-only multi-architecture image validation (`38589006620`) all succeeded.
- Scope merged: extracted persisted source-skip transition into `acquisition_orchestration.py`, kept the MCP compatibility adapter and safety boundaries, added direct regression tests, and updated Docker packaging and documentation.
- No PR reviews or inline review threads were present at merge time. No separate local test run is claimed. No image publication, deployment, or production runtime verification occurred.
- **Next action:** continue with the next highest-priority roadmap item; do not infer publication or deployment from this merge.


## 2026-10-14 — Follow-up regression: preserve neighboring acquisition files

- PR #51's six dismissal cleanup regression cases passed all four required workflows on exact head `58021141472c85c9fa33c431cba15cb66792bc1c`; PR #51 merged at `790d690ca99866878ee6204f9d101dec5f099994`.
- PR #52's documentation closeout passed all four required workflows on exact head `4684fb257685aec90025af0b02a7dff5eacfe10a`; merged at `7f05363c3b9abec29ef7c7d516bad2796813b11e`.
- Branch `test/acquisition-dismissal-neighbor-preservation` adds a regression proving successful dismissal removes only the identified album folder while preserving a sibling artwork file and another album folder. Test-only change. All four required workflows passed on exact head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7`: syntax `38594117785`, Docker packaging/full unit suite `38594117579`, container runtime smoke `38594117489`, validation-only multi-architecture build `38594117597` (publishing paused).
- The tests still invoke the legacy cleanup helper through the AST harness. Migrate to direct-import tests only alongside a tested extraction, without weakening assertions. HTTP 409 remains deferred because it was not reproduced.
- No local test run, live slskd test, real production-folder deletion, image publication, deployment, or production runtime verification is claimed.
- The first CI attempt caught an incorrect transfer-preflight call-count expectation; the test now expects both checks. The earlier test head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7` passed all four workflows, and the earlier tested PR head `6413d7cd94919a9983a381a398787b4301443d1b` also passed all four: syntax `38594465611`, Docker packaging/full unit suite `38594465538`, runtime smoke `38594465673`, and validation-only multi-architecture build `38594465580` (publishing paused).

- Final PR #53 head `ef6ec7347f69c0be04331d7bd671d9f56f3c137d` passed all four required workflows: syntax/acquisition safety `38599666003`, Docker packaging/full unit suite `38599666001`, container runtime smoke `38599665955`, and validation-only multi-architecture image build `38599665933` (publishing paused). Squash-merged at `a7c8dd469c76b340706ba65db8b4315aac60e62b`. No workflow runs were returned for the merge commit itself; no local test run, live slskd, production-folder deletion, publication, deployment, or production runtime verification is claimed.

## 2026-10-14 — Direct-import acquisition cleanup extraction

- Branch: `refactor/acquisition-cleanup-domain`, based on current GitHub main at `7a81a5dedff8e9e7245309770b4b1fe34b46be9e`.
- Extracted the existing safe cleanup implementation to `acquisition_cleanup.py`; `navidrome_server.py` keeps the MCP-compatible wrapper and injects the canonical folder sanitizer, transfer lookup, and HTTP client. Docker packaging includes the new module.
- Moved seven cleanup success/refusal cases into direct-import `tests/test_acquisition_cleanup.py`; the AST harness no longer extracts the destructive cleanup function. Existing lifecycle tests still use their isolated stub and other AST-extracted helpers; no other behavior was migrated.
- PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows: Python syntax/acquisition safety `38600688719`, Docker packaging/full unit suite/image build `38600688787`, container runtime smoke `38600688814`, and validation-only multi-architecture image build `38600688667` (publishing paused). Final diff reviewed; GitHub reported mergeable and no review submissions/inline threads. Squash-merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- Verification boundary: no separate local test run, live slskd request, production-folder deletion, publication, deployment, or production runtime verification. HTTP 409 remains deferred because it was not reproduced.
- Next priority: extract source-switch and interrupted-import orchestration behind injected dependencies with direct-import regression tests, preserving all cleanup/import safety assertions and MCP compatibility.

## 2026-10-14 — Interrupted-import recovery extraction

- Branch `refactor/acquisition-recovery-domain` starts from current main after PR #54.
- Extracted `_discovery_reconcile_interrupted_import` to `acquisition_recovery.py` with injected dependencies; retained the existing adapter and MCP interface. Docker packaging includes the new module.
- Moved four recovery regressions from the AST harness to direct-import `tests/test_acquisition_recovery.py` and added a refusal test for dismissed/non-importing jobs. Preserved mount identity, exact destination, manifest, track-size, symlink, and staged-file rollback checks.
- PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed all four required workflows: syntax/acquisition safety `38601516322`, Docker packaging/full unit suite/image build `38601516096`, runtime smoke `38601516565`, and validation-only multi-architecture image build `38601516203` (publishing paused). Final diff reviewed; GitHub reported mergeable and no review submissions/inline threads. Squash-merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- Verification boundary: no production filesystem recovery, live service interaction, publication, deployment, or production runtime verification is claimed.
- Next priority: extract source-switch orchestration behind injected dependencies, preserving cleanup failure as a hard stop and uncertain queue outcomes as monitored rather than retried.

## 2026-10-14 — Source-switch orchestration extraction

- Branch `refactor/acquisition-source-switch-domain` starts from current main after PR #55.
- Extracted the locked source-switch implementation to `acquisition_source_switch.py` with injected service dependencies. Kept the legacy wrapper and caller-owned transition lock; Docker packaging updated.
- Migrated the ambiguous-queue regression out of the AST harness and added direct-import tests for cleanup refusal, no fallback, failed fallback cleanup, and successful fallback persistence.
- PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety `38602255318`, Docker packaging/full unit suite/image build `38602255282`, runtime smoke `38602255326`, and validation-only multi-architecture build `38602255378` (publishing paused). Final diff reviewed; GitHub reported mergeable and no review submissions/inline threads. Squash-merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- No live slskd interaction, production cleanup, publication, deployment, or production runtime verification is claimed.
- Next priority: extract the acquisition watcher loop and top-level lifecycle coordination behind injected dependencies, migrating direct-import tests while preserving cancellation, import rollback, status persistence, and MCP compatibility.


## 2026-10-14 — Acquisition watcher lifecycle extraction (PR #57)

- **Branch:** `refactor/acquisition-watcher-domain`; based on `main` `09c5c884ffbfba035a6ee698f7192b1e9bbb6282`.
- **Implementation:** extracted the 200+ line watcher loop into `acquisition_watcher.py` behind injected service dependencies. The legacy `_discovery_watch_and_import_album` remains a compatibility adapter. Docker packaging and lifecycle documentation are updated.
- **Regression tests:** direct-import tests cover dismissal and interrupted-import exits, completed transfers without a verified folder (wait without import), and passing only a verified path to the existing safe import coordinator.
- **Exact-head CI:** corrected PR head `6793c339464c9d573c02f5e7dc91d15b5f568348` passed Python syntax/acquisition safety (run `38604931720`), Docker packaging/full unit suite/build (run `38604931649`), container runtime smoke (run `38604931792`), and validation-only multi-architecture build (run `38604932002`; publishing paused). The first CI attempt exposed a test assertion reading status details from the wrong argument position; the test was corrected and the subsequent four workflows passed.
- **Final-head verification:** after the documentation updates, PR head `9f201e247c092ca74f805b8ca8a1cb6f872b3cba` passed all four workflows: Python syntax/acquisition safety `38605193852`, Docker packaging/full unit suite/build `38605193845`, container runtime smoke `38605193808`, and validation-only multi-architecture build `38605193820` (publishing paused). PR #57 was squash-merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. No assistant-local test run, live slskd test, production filesystem action, image publication, deployment, or production runtime verification is claimed.
- **Next:** continue with persistent acquisition-state coordination and watcher startup; PR #57 exact-head CI and final diff review are complete.


## 2026-10-14 — Modularization roadmap reconciliation and session closeout

- Reconciled the roadmap against current GitHub main and the open-PR list after PRs #57–#59.
- Marked watcher-loop extraction (#57), watcher-startup extraction (#58), and acquisition-state save/list persistence (#59) as merged, with their known merge SHAs and exact-head CI boundaries.
- Reordered remaining work: acquisition coordination and AST-test migration; settings/configuration/service boundaries; discovery orchestration; application assembly; MCP retirement last.
- Clarified manual testing: no full local-helper browser run is required for backend-only modularization. Performance observation and a distinct error/recovery exercise remain for the next UI-facing change. The HTTP 409 investigation remains deferred until recurrence.
- Verification boundary: documentation-only change; no application tests were run in this session. No local helper run, live slskd interaction, production filesystem operation, publication, deployment, or runtime verification is claimed.
- Next action: inspect current callers and tests on GitHub main, then implement the smallest safe acquisition-coordination extraction with direct-import regression coverage.


## 2026-10-14 — PR #66 merged: login-page design-system alignment

- **PR:** https://github.com/abucalip/navi-librarian/pull/66 — squash-merged to `main` at `717b1ad08e5de54e2dd8c11c2734976d75ce2e5f` from exact tested PR head `d0b13b7411b9b300b78b24a8944348b7e57d4b65`.
- **Change:** `static/login.css` now uses the app's dark/yellow/red tokens, Barlow Condensed display heading, IBM Plex Sans body, IBM Plex Mono labels, consistent primary-button states, and visible `:focus-visible` styling. No HTML, JavaScript, authentication, API, or data behavior changed.
- **Automated verification on the exact PR head:** Python syntax run `38639793800`; Docker packaging/full unit suite run `38639793772`; container runtime smoke run `38639793518`; validation-only multi-architecture run `38639793667`. All four succeeded. The PR's reported tests were 15 focused auth/integration tests and 185 full-suite tests with one pre-existing skip.
- **Manual UI evidence:** report and screenshots are published in PR comments against the exact tested head. Desktop and 375×720 viewport, failed-sign-in layout, and asset/network checks passed. The published checklist marks keyboard focus-modality confirmation and the first-run setup variant as skipped; the stylesheet's focus rule was verified, but those two observations are not represented as fully exercised in the report.
- **State:** Implemented, automated CI passed, manual UI report published, merged. Image publishing remains paused; no deployment or production runtime verification is claimed.
- **Next:** continue the highest-priority acquisition-safety test migration/audit; do not infer deployed UI behavior from merge or CI.

## 2026-10-15 — Settings router service injection in progress

- Current implementation branch: `refactor/settings-router-service-injection`, based on `main` at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` (PR #108 merge).
- `app/api/settings.py` now uses the shared lazy `get_librarian` dependency for all twelve settings endpoints instead of importing `navidrome_server` at module import time. Existing settings functions remain the service implementation; payload mapping, defaults, response parsing, validation status codes, and sanitized 502 errors are intentionally unchanged.
- `tests/test_settings_routes.py` now supplies fake services directly and checks route/method contracts, dependency wiring, payload mapping, slskd defaults/path trimming, client validation errors, and sanitized connection failures.
- Verification state at documentation update: no local tests run; CI not yet verified for the final branch head. No image publication, deployment, or production runtime verification. Preserve the MCP adapters and legacy persistence ownership.


## 2026-10-15 — PR #109 implementation CI result

- Implementation commit `5a5a78aed24916aeddf01b306300850b95a56aa7` passed all four required workflows: Python syntax (`38734406727`), Docker packaging/full suite (`38734407126`), container runtime smoke (`38734406616`), and validation-only multi-architecture image validation (`38734407120`). The validation workflow's multi-architecture build step and overall job both completed successfully.
- This is evidence for the implementation commit only. Documentation closeout commits are being added afterward; the exact final PR head must be rechecked before merge. No local test run, image publication, deployment, or production runtime verification is claimed.


## 2026-10-15 — PR #109 merged: settings router service injection

- PR #109: https://github.com/abucalip/navi-librarian/pull/109; exact tested head `a6c919a4d6c45f98394ee683095888f27513f1d6`; squash merge / current main at closeout `9a2aaea98cff38a1ad3da130d0958f945bec9673`.
- The settings router now uses the shared lazy `get_librarian` dependency for all twelve endpoints. Route/method contracts, service calls, payload mapping, quality defaults, optional path trimming, validation responses, and sanitized connection errors are preserved.
- All four required workflows passed on the exact final PR head: Python syntax `38734569394`, Docker packaging/full suite `38734569197`, container runtime smoke `38734569168`, and validation-only multi-architecture image validation `38734569302`. Image publishing remains paused.
- No separate local test run, publication, deployment, or production runtime verification is claimed.

## 2026-10-15 — Remaining acquisition AST lifecycle test audit

- Reviewed the remaining lifecycle cases in `tests/test_acquisition_safety.py` against direct-import tests for `acquisition_request_coordinator.py` and `acquisition_orchestration.py`.
- The simultaneous-request, incomplete-saved-candidate, dismissed-job reactivation/refusal, and stale-watcher cases in the AST harness still exercise the legacy `discovery_acquire_album` adapter wiring as well as the coordinator. Direct-import coordinator tests cover the extracted coordinator's own logic but do not independently prove the adapter passes the production locks, active sets, persistence readers, and watcher callbacks correctly.
- Decision: do not delete these tests as redundant. Keep the adapter-level AST cases until an equivalent non-MCP adapter test seam can verify the same integration boundary; preserve concurrency and persisted-state checks.
- Next narrow service-boundary task: move the two remaining `/api/health` and `/api/dashboard-picks` HTTP handlers into an injected dashboard router, leaving Navidrome ping, discovery-list retrieval, and album eligibility in the existing librarian service. This does not remove the remaining `app.main` settings/auth dependency on `navidrome_server.py`.


## 2026-10-15 — PR #110 merged: dashboard and health router injection

- PR #110: https://github.com/abucalip/navi-librarian/pull/110; exact tested head `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e`; squash merge / main SHA `b4015b8619f3c0db169722c347f72612996b9a1c`.
- Moved `/api/health` and `/api/dashboard-picks` from `app/main.py` into `app/api/dashboard.py`, injecting the shared lazy `get_librarian` dependency. Service ownership, route/methods, response shapes, count validation, list count 150, category balancing, deduplication, album filtering, randomization, and sanitized 503 behavior remain unchanged.
- Added direct-import API tests. All four required workflows passed on the exact final PR head: syntax `38735208616`, Docker packaging/full suite/build `38735208619`, runtime smoke `38735208830`, and validation-only multi-architecture image validation `38735208682`. Image publishing remains paused.
- The first CI attempt caught an incorrect expected pool size in the new deduplication test; it was corrected before the final head, which passed all four workflows.
- No separate local test run, image publication, deployment, or production runtime verification is claimed.
- `app/main.py` still imports `navidrome_server.py` for authentication settings and `DATA_DIR`/auth-secret initialization. Next: audit that remaining authentication/configuration dependency and identify a narrow injectable seam without changing cookie, session, setup/login, or persistent settings behavior.



## 2026-10-15 — PR #112 implementation and exact-head CI verified

- PR #112: https://github.com/abucalip/navi-librarian/pull/112; branch `refactor/lazy-auth-service-dependency`; initial implementation head: `ded9aef759c87ccf07d71cd777b366af424cc06c`. The documentation-updated final PR head was `5c92f1106917fdb69f61faf959d060c0d5d64065`.
- `app/main.py` no longer imports `navidrome_server.py` at module load. Auth settings and the persistent signing key resolve the existing librarian service lazily; settings storage, `DATA_DIR`, MCP adapters, and domain ownership remain unchanged.
- Authentication integration tests inject a fake service and include a subprocess regression asserting that importing `app.main` does not load `navidrome_server`. Existing setup/login/logout, cookie/session, rate-limit, and middleware tests remain.
- All four required workflows passed on exact head `ded9aef759c87ccf07d71cd777b366af424cc06c`: syntax `38737672741`; Docker packaging/full suite/build `38737672443`; container runtime smoke `38737672507`; validation-only multi-architecture image validation `38737672689`.
- PR #112 merged by squash at `16c39ff11438f7a4237afa58f225777afcde6b82` after final diff review and all four required workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No separate local test execution, image publication, deployment, or production runtime verification. Publishing remains paused.


## 2026-10-15 — PR #118: discovery eligibility tests use direct imports

- PR #118 moves the duplicate album-eligibility, exact artist-credit, and Various Artists regression checks out of the AST harness in `tests/test_acquisition_safety.py`; their existing direct-import coverage in `tests/test_discovery_recommendations.py` remains authoritative.
- The direct-import suite now retains the removed edge cases: live/remix/EP/compilation rejection, exact artist-credit false matches and empty credits, plus all five Various Artists aliases. The legacy AST harness now focuses on orchestration/lifecycle paths that still require the monolithic adapter's shared state and stubbed I/O. No runtime code or MCP behavior changed.
- Branch: `test/migrate-discovery-eligibility-direct-import`. Code/test head `873f47328de0808c8d18e034d5a7d04e39a083f2` passed all four required workflows: syntax `38745139119`; Docker packaging/full suite/build `38745139114` (238 tests passed); runtime smoke `38745139370`; validation-only multi-architecture image validation `38745139332`. Final PR head `4db6654678f9ce091caf43b650c04039c15dd6ef` also passed all four: syntax `38745425843`, Docker packaging/full suite/build `38745426466`, runtime smoke `38745425909`, and validation-only multi-architecture image validation `38745426093`. PR #118 merged to `main` at `9b1ba91923321a835e8bd3a210dd6aaf01caefc2`. No local test run, image publication, or deployment is claimed.


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


## 2026-10-15 — Discovery refresh API count validation in progress

- Backend audit found that `POST /api/discovery/{list_name}/refresh` converted `count` with `int(...)`, silently accepting numeric strings and booleans and truncating floats. This could turn malformed input into a different refresh request.
- Branch `fix/discovery-refresh-strict-count` now requires a real JSON integer from 1 through 20 (while preserving the omitted default of 20) and adds direct-route regression cases for strings, floats, booleans, null, arrays, objects, and range violations.
- Exact implementation head `859bf10b1bbaececd2045596287c7680bb66d514` passed all four workflows: Python syntax `38762625902`, container runtime smoke `38762625878`, Docker packaging/full unit suite/build `38762625612`, and validation-only multi-architecture image validation `38762625568`. The documentation-updated final head must pass all four again before merge.
- No separate local test execution, merge, publication, deployment, or production runtime verification is claimed.


## 2026-10-15 — PR #129 merged: strict discovery refresh count validation

- PR #129 merged to `main` at `b3db4d1d3ac3367a306435e0e3e50e7e3286ce22` from exact final PR head `d6f57b95f1cd77f58d1636f471a8f80bc9776f61`.
- `POST /api/discovery/{list_name}/refresh` now accepts only a JSON integer from 1–20; omitted count remains 20. Numeric strings, other strings, floats, booleans, null, arrays, objects, and out-of-range integers are rejected with HTTP 400 before the service call.
- Direct-route regression cases were added in `tests/test_discovery_routes.py`. The unit-test step and Docker build passed on the final head.
- All four required workflows passed on exact final PR head: Python syntax `38762802954`, container runtime smoke `38762803101`, Docker packaging/full unit suite/build `38762802863`, and validation-only multi-architecture image validation `38762803211`.
- No separate local test execution, publication, deployment, or production runtime verification is claimed.


## 2026-10-15 — PR #132 merged: sliding navigation indicator

- PR #132 merged by squash at `44b03d6e6293e1a1ba34803104f52c4e443d245b` from exact tested PR head `b4982260a4e5697ee02766f47d35f7182303387a`.
- Replaced the static active-nav bar/dot with a transform-only sliding indicator and isolated SVG goo filter on the seven content items. Preserved the horizontal mobile navigation below 620px, reduced-motion behavior, and `aria-current="page"`; no route/API/auth/domain behavior changed.
- All four required workflows passed on the exact PR head: Docker packaging `38766740766`, container runtime smoke `38766741159`, Python syntax `38766741253`, and Docker image validation with publishing paused `38766741247`.
- Manual browser report published on PR #132: https://github.com/abucalip/navi-librarian/pull/132#issuecomment-6196780079. All eight checklist items passed on the exact tested SHA; zero failed items.
- Status: implemented, CI passed, manually verified, merged. No image publication, deployment, or production runtime verification is claimed.


## 2026-10-15 — Settings connection checks extracted (PR preparation)

- Moved Navidrome ping, Last.fm API-key verification, and ListenBrainz profile reachability/result mapping into directly importable `service_settings.py` functions with injected HTTP/service dependencies.
- `navidrome_server.py` retains the existing public MCP/web functions as compatibility adapters; endpoint response JSON/status/message contracts, timeouts, request headers, and credential redaction are intended to remain unchanged.
- Added direct-import regression tests for successful/failed Navidrome ping mapping, Last.fm missing-key/authentication failure with secret redaction, and ListenBrainz missing-profile handling.
- Branch: `refactor/extract-settings-connection-services`. Focused and full test runs plus all four required exact-head CI workflows are pending. No merge, publication, deployment, or production runtime verification claimed.


## 2026-10-15 — PR #140 merged and verified

- PR: https://github.com/abucalip/navi-librarian/pull/140 — settings connection checks extracted into `service_settings.py`; legacy MCP/web entry points remain compatibility adapters.
- Exact tested PR head: `cacdbc809f35040f0cc1bc70a39251ff80b7315e`.
- All four required GitHub Actions workflows passed on that exact head: Python syntax `38784634643`, Docker packaging/full unit suite/build `38784634599`, container runtime smoke `38784635107`, and validation-only multi-architecture image validation `38784634797`.
- Merged by squash; merge commit: `aabd7d1347d8e4c363d8b97bb6c106310f1135bb`. PR state verified closed/merged.
- No local test execution, image publication, deployment, or production runtime verification is claimed. Publishing remains paused.
- Next useful step: continue separating remaining settings/application-assembly and domain-service dependencies from `navidrome_server.py`, starting with repository status and docs review.


## 2026-10-15 — PR #145 merged: modal artwork accessibility and navigation scope

- PR #145: https://github.com/abucalip/navi-librarian/pull/145; exact tested PR head `421d1d2860945548aa01677847ce0953b7c9f263`; squash merge commit `d8abea9502c88312326835c40889b63062adc1b3`.
- Modal artwork now receives album/artist-specific alternative text when artwork resolves and an empty alt when it does not. Scoped the “YOUR COLLECTION” pseudo-element to the sidebar navigation, preventing it from leaking into the modal's platform links. No API/routing/domain behavior changed.
- Manual browser report published on PR #145: https://github.com/abucalip/navi-librarian/pull/145#issuecomment-6200647429. All eight checklist items passed against the exact tested head; zero failures.
- All four required workflows passed on the exact PR head: Python syntax `38794301415`, container runtime smoke `38794301446`, Docker packaging `38794301460`, and validation-only Docker image validation `38794301405` (publishing paused).
- Status: implemented, CI passed, manual browser checklist passed, merged. The report notes that no real screen reader was tested and artwork used a placeholder in isolated checks. No image publication, deployment, or production runtime verification is claimed.
- Next UI follow-up noted by the PR: assess the remaining C4 recommendation-count live-region font-size issue.


## 2026-10-15 — Data-directory resolution extraction in progress

- Branch `refactor/extract-data-directory-config` extracts only the selection of `DISCAIR_DATA_DIR` versus the source-directory fallback into `data_directory.py`. The legacy `DATA_DIR` name and directory creation remain in `navidrome_server.py`; persistence ownership and import-time initialization behavior are unchanged.
- Added direct-import tests for explicit home expansion, empty environment fallback, and resolved source-directory fallback. Docker packaging includes the new module.
- Pending: run focused and full tests, verify syntax plus all four required CI workflows on the exact final PR head, review the full diff, then update the closeout record. No test/CI success, merge, publication, deployment, or runtime verification is claimed yet.


## 2026-10-15 — PR #152 merged: data-directory resolution extraction

- PR: https://github.com/abucalip/navi-librarian/pull/152. Exact tested PR head: `756ef13f6946299e2eacccbf5f9a55ebaf092aae`; squash merge commit: `567409bb90f240667575a3730976e4c52676bc02`.
- Extracted `DISCAIR_DATA_DIR` resolution and the source-directory fallback into pure `data_directory.py`; retained `navidrome_server.DATA_DIR`, `mkdir` behavior, persistence ownership, and MCP compatibility. Added three direct-import regression tests and Docker packaging.
- All four required workflows passed on the exact PR head: Python syntax `38807325467`, Docker packaging/full unit suite/build `38807325564`, container runtime smoke `38807325555`, and validation-only multi-architecture image validation `38807325557`.
- State: implemented, CI passed, merged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next: inspect current GitHub main, open PRs, and the roadmap before selecting the next small application-assembly/domain-service dependency.


## 2026-10-15 — Subsonic collection normalization extraction in progress

- Branch: `refactor/extract-subsonic-list-normalizer`. Moved optional API collection normalization (`None` to `[]`, scalar to one-element list, list unchanged) into `navidrome_client.items()` because it is part of interpreting Subsonic response values.
- Kept `navidrome_server.items()` as a compatibility adapter so existing discovery/MCP callers retain the same behavior. Added direct-import regression cases for missing, scalar, empty-list, and multi-item values.
- Implementation commits: `3f97f2bafc29265d12a8a4bf858a1e27384f16b3`, `2f0ae7939f0ea3052faa237b2246cf3d32206bdf`, `e7e105a850928705339613780fb55641ac44f72c`.
- CI, merge, publication, deployment, and runtime verification are pending. Do not claim tests passed until the four required workflows complete on the exact final PR head.


## 2026-10-15 — PR #153 merged: Subsonic collection normalization

- PR #153: https://github.com/abucalip/navi-librarian/pull/153; exact tested head `c834383b7484f3c149679d62812f1c81f6133625`; squash merge commit `b7d8ec989e2a3d398b2ca4d14a30c59ae60543cc`.
- Moved optional Subsonic collection normalization into `navidrome_client.items()` while retaining `navidrome_server.items()` as a compatibility adapter. Added direct-import regressions for `None`, scalar, empty-list, and multi-item inputs.
- All four required workflows passed on the exact PR head: Python syntax check, Docker packaging validation (including full unit suite/build), container runtime smoke test, and validation-only multi-architecture image validation.
- State: implemented, CI passed, merged. Image publishing remains paused; no deployment or production runtime verification is claimed.
- Next session: review current main, recent commits, open PRs, and the modularization roadmap before selecting the next smallest application-assembly/domain-service seam.


## 2026-10-15 — PR #149 merged: recommendation-count readability and status semantics

- PR #149: https://github.com/abucalip/navi-librarian/pull/149. Final tested head: `c71d28e74bbdfadbedef4ec3e30fdba5181feb5a`; squash merge commit: `f3ac971e6c04b9c9caa8d4d20f50d0c25302556e`.
- Refreshed the original PR branch onto current main without force-pushing. Increased recommendation-count text from 11px monospace to 13px body type with tabular numerals and added `role="status"` while retaining explicit `aria-live="polite"`.
- Updated `docs/UI_BACKLOG_EXECUTION.md` to record the accessibility rationale and keep the manual verification evidence tied to the commit actually tested.
- The operator-published manual browser report is attached to PR #149 and records the exact final head `c71d28e74bbdfadbedef4ec3e30fdba5181feb5a`; all checklist items passed.
- All four required workflows passed on that exact head: Python syntax, container runtime smoke, Docker packaging (including full unit suite/build), and validation-only Docker image validation. Publishing remains paused.
- State: implemented, manually tested, CI passed, merged. No image publication, deployment, or production runtime verification is claimed.
- Next: review current main, open PRs, and the modularization roadmap before selecting the next smallest safe dependency extraction.


## 2026-10-15 — Focused verification audit before modularization

- Current GitHub `main` SHA at audit: `678bfa001181d53190004d1c437b1344225082cf` (tip commit: “docs: close out merged discovery refresh extraction PR 160”). The preceding extraction merge is `dba172d5747607e65e8fadd32442b12d32054749`.
- All four required GitHub Actions checks passed on the exact current-main SHA: Python syntax `38818751753`; Docker packaging/full suite/build `38818751792`; container runtime smoke `38818751871`; validation-only multi-architecture image validation `38818751791`. This verifies CI at that SHA only; no image publication, deployment, or production runtime verification is claimed.
- Open PR inventory: #23 (documentation roadmap, branch `docs/modularization-web-only-roadmap`, head `273feea13477af3b82f93fcb8bca7b302ebe1c83`, 11 commits ahead / 341 behind main; only two older checks visible); #44 (draft acquisition cleanup diagnostics, head `54a0195d18009ffaa48303bcd712e05ec5b357b8`, 13 ahead / 259 behind, no check runs on exact head); #45 (defer 409 investigation, head `8462f67cc43d444445e8643301d9787e0602e752`, 4 ahead / 256 behind, four older checks succeeded on its exact head but it is stale relative to main). Treat the divergence counts as audit-time evidence; do not merge these branches without refreshing/reviewing them and re-running required gates.
- #44 remains draft and diagnostic, not a confirmed fix. The HTTP 409 investigation stays deferred unless the issue recurs. No evidence supports relaxing cleanup safety.
- Accessibility: PR #156's manual browser checklist passed 8/8 on its exact tested head and all four workflows passed. The skip link remains outstanding in `docs/UI_BACKLOG_EXECUTION.md`; no real screen-reader test is recorded.
- Release: publishing remains intentionally paused; the main-branch validation workflow is validation-only. No image publication, deployment, or production runtime verification is claimed.
- **Selected highest-priority gap before routine modularization:** regression coverage for acquisition UI Get/request and Dismiss transitions (requirements ACQ-01/02/03), with the ACQ-04/06 backend safety boundary preserved. The repository has no dedicated automated front-end test files. Exact acceptance criteria are recorded in `docs/TEST_PLAN.md` under “Verification audit — highest-priority gap: acquisition UI request/dismiss regression.”
- Status: audit completed; acceptance criteria documented on a focused documentation branch/PR. No application behavior was changed and no application tests were run for this audit. Next: implement the focused UI regression coverage and run exact-head CI plus the required manual browser checklist before returning to modularization.


## 2026-10-16 — Modularization session closeout: PRs #174 and #175

- PR #174 extracted cached Last.fm artist top-tag parsing into `LastFmClient.artist_genres()`, retaining `navidrome_server._lastfm_artist_genres()` as a compatibility adapter. Merged to main at `4dd8b926a7a6cf76e248420860d7c29c892da3c0`.
- PR #175 extracted cached Last.fm top-album retrieval and normalization into `LastFmClient.artist_top_albums()`, retaining `navidrome_server._lastfm_top_albums()` and discovery-specific eligibility filtering. Exact tested PR head: `6b5e32b1144e9f3517247110ea4383b287ce33f4`; squash merge/current main: `f922631e0393063bde02b1e0bd93d30b2d38bd2a`.
- All four required CI workflows passed on PR #175's exact head: Python syntax, Docker packaging/full unit suite/build, container runtime smoke, and validation-only multi-architecture image validation. No separate assistant-side local test run is claimed.
- Documentation updates for these extractions are recorded in the architecture, modularization roadmap, test plan, and project log.
- State: both extractions implemented, tested by required exact-head CI, and merged. Publishing remains paused; no deployment or production runtime verification is claimed.
- Acquisition Dismiss HTTP 409 remains explicitly deferred.
- Next session: refresh current main and open PRs, read the required workflow/testing docs, then select the next smallest roadmap-aligned extraction. Do not resume the deferred 409 investigation unless asked or it recurs.


## 2026-10-16 — Modularization closeout: PRs #193 and #195

- **PR #193** extracted exact MusicBrainz release-year lookup, artist-credit/title matching, request pacing, and positive/negative cache ownership into `musicbrainz_album_year.py`. The legacy `app.api.metadata._musicbrainz_album_year()` remains a compatibility adapter. Tested head `2b426587e6cb4dc011c85099021041d9f9450744`; squash merge `bce1e32b4ca4c2df86f51dd6102931ed8299dcfe`.
- **PR #195** extracted reviewed slskd file-list and quality-summary normalization into `acquisition_candidate_queue.py`. `discovery_queue_slskd_candidate()` retains JSON response mapping, slskd network I/O, and watcher startup. Tested head `f60d682b2ebcd94ecfbcfd0b4beb77c628643fc5`; squash merge `5629d259468a0f748fb5d3fdb78819a0fb00d73c`.
- All four required exact-head workflows passed for each PR: Python syntax/acquisition safety, Docker packaging/full unit suite/build, container runtime smoke, and validation-only multi-architecture image build. PR #193 run IDs: `38881961573`, `38881961574`, `38881961553`, `38881961580`. PR #195 run IDs: `38882195745`, `38882195774`, `38882195700`, `38882195820`.
- No separate assistant-side local test run, image publication, deployment, or production runtime verification is claimed. Publishing remains paused. Acquisition-dismissal HTTP 409 remains deferred; neither extraction changes cleanup behavior.
- Next: refresh GitHub main, open PRs, and CI; continue the remaining acquisition lifecycle/orchestration modularization without touching the deferred 409 investigation.


## 2026-10-16 — Acquisition progress snapshot extraction completed (PR #199)

- PR #199 squash-merged at a18889b7aa45dd8ef0a9e99a12236cedf5ed5a41 from exact tested head f7157cb28d5e753a97bb9c24eea209b767d74066.
- acquisition_progress_snapshots.py now owns the per-process, per-acquisition byte-snapshot map and lock. navidrome_server.py retains live slskd polling and compatibility behavior; the manager delegates speed math to slskd_transfers.estimate_transfer_speed.
- Direct-import regressions cover first/next samples, identity isolation, and retaining the current sample if the estimator raises. All four exact-head workflows passed: syntax/acquisition safety run 1096; Docker packaging/full suite/build run 1003; runtime smoke run 812; validation-only multi-architecture run 856.
- Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Acquisition search diagnostics extraction completed (PR #200)

- PR #200 squash-merged at 9b3cf481a46282d2f980709091d57aea36144029 from exact tested head b74f6a3f4f8290d6e8d7123399185e9692dd053c.
- acquisition_search_diagnostics.py now owns the bounded candidate diagnostic projection, recognized audio-file count, and no-match explanation. Search execution, path-match diagnostics, persistence, queueing, and JSON/API serialization remain in navidrome_server.py.
- The first CI attempt exposed a compatibility issue in the AST-based acquisition safety test harness: its extracted function namespace did not include a module-level helper alias. The import was moved into the function, preserving production behavior and allowing the legacy test harness to execute it. The exact final head passed all four workflows: syntax/acquisition safety run 1099; Docker packaging/full suite/build run 1006; runtime smoke run 815; validation-only multi-architecture run 859.
- Direct-import tests cover diagnostic field projection and 10-item cap, copied quality summaries, recognized audio extensions, and no-match message/query ordering. Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


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

## 2026-10-16 — Modularization session closeout: PRs #216–#218

- **PR #216 — Deezer artwork selection:** exact final tested head `aa1099e8ed43b9afcce483a50be31226a66218f4`; syntax 1148, Docker/full suite/build 1055, runtime smoke 864, validation-only multi-architecture 908 all passed; merge `ad61b1b91a5c351a73c02e37d7639bc47c61a52f`.
- **PR #217 — matched Deezer album payload shaping:** exact final tested head `b631f4c6367c68357cbd91f75b986770edfeee0e`; syntax 1151, Docker/full suite/build 1058, runtime smoke 867, validation-only multi-architecture 911 all passed; merge `37f04d0a863f69f5596f6a46406cc8bd64bde039`.
- **PR #218 — exact Deezer release-year selection:** exact final tested head `0293e4fe4eab7dd66dc82280720183dab3b913ed`; syntax 1153, Docker/full suite/build 1060, runtime smoke 869, validation-only multi-architecture 913 all passed; merge `6dc6adae89169638da9a158c79ccee5d2e1ddfb7`.
- All three PRs added direct-import regression coverage and preserved route/provider/cache ownership. Assistant-side local test commands were not run; the Docker packaging workflows ran the full unit suite. No publication, deployment, or production runtime verification is claimed.
- Publishing remains paused. Acquisition-dismissal HTTP 409 remains deferred per user direction; no acquisition/import/deletion semantics were changed.
- **Next action:** refresh GitHub main/open PRs/CI and inspect remaining application-assembly/domain-service boundaries before selecting the next independent seam. Do not treat extraction count as a quota.

## 2026-10-16 — Personal recommendation allocation contract designed

- Current GitHub base: `9376d5f0d55815067aeb5cadf9015b4b775a9848` (PR #220 merge). Open PR audit was empty at session start; recent `main` workflow run `38915170332` succeeded.
- Added `discovery_allocation_contract.py`, `tests/test_discovery_allocation_contract.py`, and `docs/PERSONAL_RECOMMENDATION_ALLOCATION_CONTRACT.md` on branch `refactor/personal-allocation-contract`.
- The contract is data-only: prepared candidates have stable IDs, normalized identity keys, category/style/family/score, and precomputed ownership status; request contains immutable policy mappings and bounded count/check limits; result carries selected IDs, ownership-review IDs, decision reasons, category counts, and check count. No callbacks, provider/library access, candidate payload copies, or shared mutable counters are part of the interface.
- **The shortlist-selection loops remain unchanged and have not been moved.** This is a contract-design PR, not an allocator implementation. Tests cover input/output invariants, ownership-state representation, duplicate IDs, immutable mappings, and bounds; they do not claim to test allocation policy.
- Test execution and exact-head CI are pending PR creation. No publication, deployment, or runtime verification.
- **Next action:** run the focused direct-import contract tests and required exact-head workflows; only then decide whether to move loops in a separate PR. If actual policy needs callbacks/shared mutable state beyond this interface, stop and refine the seam.

## 2026-10-16 — PR #221 merged: personal allocation interface contract

- PR #221 (`test: define personal recommendation allocation contract`) merged from exact tested head `9d17a0ef32782db35b19b5226d3b8c052f8775d6`; squash merge/current main at closeout `820556799fa9d3ec663e5117b36c68084281b20a`.
- Added `discovery_allocation_contract.py`, direct-import tests in `tests/test_discovery_allocation_contract.py`, and `docs/PERSONAL_RECOMMENDATION_ALLOCATION_CONTRACT.md`. Updated status, test plan, roadmap, and project log.
- All four required workflows passed on exact PR head `9d17a0ef32782db35b19b5226d3b8c052f8775d6`: Python syntax run `38916419736`; Docker packaging/full unit suite/build run `38916419709`; container runtime smoke run `38916419958`; validation-only multi-architecture image validation run `38916419701` (publishing remains paused). The packaging workflow's unit-test step passed. Assistant-side local test commands were not run independently.
- **Important scope boundary:** this PR only defines and tests the immutable data contract. It does not move or test the actual shortlist-selection loops, and does not prove allocation policy parity. No provider/library I/O, response assembly, legacy caller, or MCP interface changed.
- No publication, deployment, or production runtime verification is claimed.
- **Next action:** use this interface for a separate allocator implementation only if the existing policy can be moved without callbacks or shared mutable state, with direct-import policy-parity tests for style reservations, quotas, duplicates/per-artist limits, ownership/manual review, fallback ordering, diagnostics, and the 60-check cap. If not, refine or abandon the boundary.



## 2026-10-16 — PR #233 merged: New Releases library qualification

- PR #233 merged to `main` from exact final PR head `2512a638001e922f5c507994b2f1e667bab9615a`; squash merge commit `08e20f502e10f829bf9ae7920106b7e8427668eb`.
- Extracted `prepare_new_release_library_scope()` to `discovery_new_releases.py`, with direct-import tests for the six-track full-album threshold, Various Artists/blank-name exclusions, stable descending album-count order, and normalized owned-album identities. Provider/cache/rate-limit operations, date policy, adapter cap, error reporting, and candidate merging remain in the adapter.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety run `38934216294`; Docker packaging/full unit suite/build run `38934216395`; container runtime smoke run `38934216347`; validation-only multi-architecture build (`push: false`) run `38934216280`.
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed; publishing remains paused.
- **Next action:** refresh GitHub main, open PRs, docs, and CI, then select the next independently testable remaining roadmap boundary. Do not treat extraction count as a quota.


## 2026-10-16 — PR #237 merged: New Releases date-window policy

- Merged PR #237 from `extract/new-release-window-policy`; merge commit `2d11e52b78004ee51a6ce70a6a6ac6c2b451f397` (tested PR head `8d42c9f5f320fd7b4c0653fa09da8eda12f03f78`).
- Extracted deterministic 730-day cutoff and year bounds to `discovery_new_releases.new_release_window(today)`; added direct-import regressions for cutoff and leap-day arithmetic.
- All four required workflows passed on the exact PR head: syntax `38938867862`, container runtime smoke `38938867737`, Docker packaging/full unit suite/build `38938867879`, validation-only multi-architecture image validation `38938867550` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.
- **Next action:** refresh GitHub main, open PRs, docs, and CI before selecting the next independently testable roadmap boundary.


## 2026-10-16 — PR #238 merged: New Releases provider lookup

- Squash merge commit: `59430bba44bd32a9dfbbe51f19c3e2e8a1441c13`; exact tested PR head: `a26614489d1407792ba959461537f4e8d87fee06`.
- Extracted the cache/read-through MusicBrainz request into `discovery_new_releases.fetch_artist_release_groups()`. The server adapter retains artist iteration, the pacing decision, query construction, candidate selection/merging, and response assembly.
- Direct-import regressions cover cache hits, request parameters/timeout, pacing, cache writes, malformed payload normalization, and safe error-type reporting.
- All four required workflows passed on the exact PR head: Python syntax run `38939659986`; Docker packaging/full unit suite/build run `38939659632`; container runtime smoke run `38939659664`; validation-only multi-architecture image validation run `38939660017` (publishing paused).
- No assistant-side local test commands were run independently. No image publication, deployment, or production runtime verification is claimed.
- **Next action:** refresh main and inspect the remaining acquisition lifecycle/application-assembly boundaries before choosing another independently testable extraction.


## 2026-10-16 — Authentication configuration predicate extraction (PR #239 merged)

- Isolated the pure three-field owner-auth configuration check in `app/security/auth_configuration.py`; `app/main.py` retains the settings read and compatibility wrapper.
- Added direct-import regressions for complete credentials, each missing/empty required field, absent settings, and unrelated keys. Existing truthiness semantics are intentionally preserved.
- Scope is limited to application assembly policy; no routes, cookies, session behavior, persistence, or auth-secret handling changed.
- All four required workflows passed on the exact final PR head: Python syntax `38940305016`; Docker packaging/full unit suite/build `38940304930`; container runtime smoke `38940304907`; validation-only multi-architecture image validation `38940305045` (publishing paused). Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Auth settings reader extraction (verification pending)

- Extracted the lazy, uncached read of persisted auth settings into `app/security/auth_settings.py` via an injected settings getter. `app.main._auth_settings()` remains as the compatibility adapter used by middleware and auth routes.
- Added direct-import tests for fresh reads and error propagation. This must remain uncached so setup and credential changes are visible on subsequent reads.
- Acceptance: focused tests, full unit suite, syntax checks, and all four required workflows must pass on the exact final PR head before merge. No local test execution, CI pass, merge, publication, deployment, or runtime verification is claimed yet.



---

# Legacy snapshot: `docs/TEST_PLAN.md`

## New Releases query construction extraction — completed (PR #236)

Direct-import tests cover date-bounded query shape, quote/backslash escaping, and cache-key stability. Exact tested head `990e3ddfe08b6b1590860e8fd07d0ac13882be3e` passed all four required workflows: syntax/acquisition safety `38938238608`, Docker packaging/full unit suite/build `38938238694`, container runtime smoke `38938238678`, and validation-only multi-architecture validation `38938238904`. Assistant-side local tests were not run. Publishing/deployment remain paused.

## 2026-10-16 — PR #235 merged: New Releases response projection

- Squash merge commit: `0d77f7d99a89660ea1d9a38635e93343538e93b8`; exact tested PR head: `f3e7ec7c14deac8136b5066011623e00dffca134`.
- Extracted sorting, the 200-item visible cap, the 20-error cap, and response shaping into `discovery_new_releases.build_new_release_response()`. Provider/cache/rate-limit access, date-window policy, candidate selection, and error collection remain in the server adapter.
- Added direct-import tests for newest-first ordering/tie behavior, response metadata, error/item caps, and non-mutation. Docker packaging already included `discovery_new_releases.py`, so no packaging change was needed.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety run `38937239432`; Docker packaging/full unit suite/build run `38937239481`; container runtime smoke run `38937239444`; validation-only multi-architecture image validation run `38937239482` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## New Releases global candidate merge — merged (PR #234)

PR #234 merged at `c44ea572354b4714e5e2577f5eb21b091be97cc8` from exact tested head `56bb5b6835d03860124f2dbdff4dbb13a813d5c8`. Direct-import regressions cover newest-release winner per identity, stable existing winner on equal dates, input non-mutation, and empty/missing-date cases. All four required workflows passed on that exact head: syntax 38935716487, Docker/full suite/build 38935717026, runtime smoke 38935716420, validation-only multi-architecture 38935716622. Assistant-side local test commands were not run.

## New Releases global candidate merge — verification pending (PR #234)

Focused tests in `tests/test_discovery_new_releases.py` cover newest-release winner per identity, stable existing winner on equal dates, input non-mutation, and empty/missing-date cases. Run `python -m unittest tests.test_discovery_new_releases -v` and the full suite; require all four workflows on exact final PR head. Assistant-side local tests have not been run.

## New Releases library qualification extraction — verification pending

Focused tests: `python -m unittest tests.test_discovery_new_releases -v`. Contract coverage includes the six-track full-album threshold, Various Artists/blank-name exclusion, stable descending album-count order, normalized owned identities, and empty qualified results. The full unit suite and all four required workflows passed on tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`: syntax/acquisition safety 38934044235, Docker packaging/full suite/build 38934044270, runtime smoke 38934044253, and validation-only multi-architecture validation 38934044237 (`push: false`). Assistant-side local tests were not run. PR #233 remains open; merge pending.

## Classics candidate collection extraction (PR #232 merged)

Direct-import tests cover ordering, top-album limit, normalized duplicate identity/highest-listener winner, owned/ineligible filtering, metadata, empty results, and pacing. PR #232 merged at `451944c9056eeb50ec7d8b1744bbf435d653b70b`. The four workflow runs inspected succeeded, but exact-head association was not independently confirmed. Assistant-side local tests were not run.
## 2026-10-16 — Classics genre enrichment extraction (PR #231 merged)

Direct-import tests cover bounded enrichment, candidate order preservation, normalized artist lookup deduplication, unclassified-genre fallback, zero/negative limits, and candidates beyond the 300-item default. Last.fm access and genre-family classification are injected. All four required workflows passed on exact PR head `0856f2a9a91e8b3aff88f933d845b182007997d4`: syntax run 1208, Docker packaging/full unit suite/build run 1116, container runtime smoke run 925, and validation-only multi-architecture validation run 969. Assistant-side local execution was not performed. Squash merge: `b23d76712a04dcbfc461ceb7245a0676738fca7a`.

## 2026-10-16 — Watcher progress-accounting extraction (PR #230 merged)

Direct-import tests in `tests/test_acquisition_progress_accounting.py` cover progress increase resetting the timer and clearing a stall marker, unchanged/decreasing counters preserving the previous progress time, and the exact 120-second boundary. The helper is included in Docker packaging. On exact tested head `47fb2a5bb18d4101dde910dd30e5bad2ed13e2e7`, all four required workflows passed: syntax/acquisition safety run 1202, Docker packaging/full unit suite/build run 1110, container runtime smoke run 919, and validation-only multi-architecture validation run 963. Assistant-side local test execution was not performed; publishing and deployment remain paused.
## 2026-10-16 — Classics critical-rating helper (PR #229 merged)

Added direct-import tests in `tests/test_discovery_classics_ratings.py` for listener-ranked shortlist ordering, the default 80-item cap (configurable in focused tests), the first-30 year-lookup policy, stable tie order, missing-rating no-op behavior, rating/vote/year updates, and invalid negative limits. The provider is injected so tests require no network or credentials. Exact PR head `28c364dca41971ea90667c175663de17b41ca7ab`: syntax/acquisition safety run 1194 passed; Docker packaging, unit tests, and build run 1102 passed; container runtime smoke run 911 passed; validation-only multi-architecture run 955 passed. All reported steps succeeded. Local test execution was not performed.
## 2026-10-16 — Verification closeout: PRs #225 and #226

- **PR #225 — cached discovery-list payload:** direct-import tests cover missing cache, dismissed albums/artists, saved albums, non-album filtering, personal diagnostics, and count/total behavior. Exact head `573fe05d31dae422c25188688cd2fa949339e487` passed syntax/acquisition safety 1187, Docker packaging/full suite (477 tests)/build 1095, runtime smoke 904, and validation-only multi-architecture image validation 948. Squash merge `4d968b381d1f541b81a4a46d1753b5145347e33d`.
- **PR #226 — background listening-profile refresh:** direct-import tests cover success/persistence, error payloads, malformed JSON, and sanitized provider exceptions. Exact head `740979f1b4da4f5c13632ab3598c13bc09ed413e` passed syntax/acquisition safety 1189, Docker packaging/full suite (481 tests)/build 1097, runtime smoke 906, and validation-only multi-architecture image validation 950. Squash merge `f5a95338e978a14d01fb6a1c3741e2e6c8bea11c`.
- No assistant-side local test commands, image publication, deployment, or production runtime verification are claimed. Publishing remains paused.

## 2026-10-16 — PR #224 verification: personal recommendation payload projection

- Direct-import tests in `tests/test_discovery_recommendation_payload.py` cover legacy field mapping, defaults, score rounding, category-specific reason strings and low-confidence suffix, ListenBrainz-vs-Last.fm score behavior, track truncation, and optional metadata preservation.
- Exact final head `6d2e0ccc8d24cd11b727255f171fd405384a8729` passed syntax/acquisition safety run 1177; Docker packaging/full unit suite (473 tests)/build run 1085; isolated runtime smoke run 894; validation-only multi-architecture image validation run 938. Squash merge: `f795239589e6dd78f0f5e6d98cf2eadc897d6f49`.
- No independent local test run, publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — Independent extraction verification closeout (PRs #205 and #207)

- **PR #205 — New Releases candidate selection:** direct-import tests cover eligible payload shape, invalid/non-album/out-of-window/future releases, similar-artist credit rejection, owned album exclusion, Various Artists rejection, and duplicate identity release-date precedence. Exact final head `079d355e972ea39d792c1dfa6fca6eab902800e3` passed syntax run 1111, Docker packaging/full unit suite/build run 1018, runtime smoke run 827, and validation-only multi-architecture run 871. Squash merge `32b39be400ec046e8310a87260346b1959141609`.
- **PR #207 — Artist Deep Dives ranking/diversity:** direct-import tests cover candidate-pool scoring influence, eligibility filtering, artist/anchor repetition caps, and primary-pass genre diversity. Exact final head `20e565582579f4097eed3803748c87bb3d932a98` passed syntax run 1114, Docker packaging/full unit suite/build run 1021, runtime smoke run 830, and validation-only multi-architecture run 874. Squash merge `a5b0d865060c3d069a865be7a1cb43c1a072ae91`.
- Assistant-side local test commands were not run; the Docker packaging workflows ran the full unit suite. No live MusicBrainz/Last.fm integration, publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — Extraction verification closeout (PRs #202 and #203)

- **PR #202 — library overview payload:** direct-import tests in `tests/test_navidrome_client.py` cover projected album fields, artist count/note, empty input, and unchanged payload shape. Exact final head `6903f40578f40fec08f1efde92d6577fcaeeced0` passed syntax/acquisition safety run 1104, Docker packaging/full unit suite/build run 1011, runtime smoke run 820, and validation-only multi-architecture run 864. Squash merge `7a95364a31f360bb20dd8d2919a9bfea93ec893c`.
- **PR #203 — source preview redaction:** direct-import tests in `tests/test_server_source_redaction.py` cover case-insensitive sensitive names, non-sensitive assignments, non-assignment lines, and legacy indentation behavior. Exact final head `14019b8beeca9b71fbb8167117dafea3f60c74ea` passed syntax/acquisition safety run 1106, Docker packaging/full unit suite/build run 1013, runtime smoke run 822, and validation-only multi-architecture run 866. Squash merge `89e639394122aebe29bfb8602a1135722ea28bbe`.
- Assistant-side local test commands were not run; the Docker packaging CI jobs ran the full unit suite. No live integration, publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — Artist-biography resolution verification (PR #190)

Exact PR head `6c04d8a67944568a3e2b280deafb4eb2c66c2391` passed all four required GitHub Actions workflows: syntax/acquisition-safety regressions (run 1059), Docker packaging/full unit suite/image build (run 966), isolated container runtime smoke (run 775), and validation-only multi-architecture image validation (run 819). Direct-import tests in `tests/test_artist_bio_service.py` cover exact QID matching, mismatched identities, disambiguation, entity filtering/ranking, empty payloads, and truncation. Existing `tests/test_metadata_routes.py` remains in place for route/input/cache contracts. PR #190 merged at `b829fa953d979563a8ace6e5529eace8cb80ac43`. Assistant-side local tests were not run independently; no publication, deployment, or production runtime verification is claimed.
## 2026-10-16 — Dashboard-pick service extraction verification (PR #189)

Exact PR head `d28aaa33f7096ba764232d6bd435cc68d5d85f98` passed all four required GitHub Actions workflows: Python syntax/acquisition-safety regressions (run 1052), Docker packaging plus full unit suite/image build (run 959), isolated container runtime smoke (run 768), and validation-only multi-architecture image validation (run 812). Direct-import tests in `tests/test_dashboard_service.py` cover balanced categories, source call count/arguments, case-insensitive deduplication, eligibility filtering, failed-lane tolerance, and malformed/missing-identity rows. Existing `tests/test_dashboard_routes.py` remains in place for endpoint contract and input validation. PR #189 merged at `f5f355f8bdc0599bb240933e248177c7b0517ff5`. Assistant-side local tests were not run independently; no publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — slskd connection probe verification closeout (PR #187)

Final PR head `920590871883aa8c75c29a1b16131bd88519072d` passed all four GitHub Actions workflows: Python syntax check (run 1041), Docker packaging/full unit suite/build (run 948), container runtime smoke test (run 757), and validation-only multi-architecture image build with publishing paused (run 801). Direct-import regressions in `tests/test_slskd_client.py` cover successful request parameters and response shape, 401/403 authentication failures, HTTP errors, missing configuration, and API-key redaction. Squash merge: `b7ae6458adda3650f178fc64457914beb66ece9c`. Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — slskd connection probe (PR #187, pending verification)

Focused regression file: `tests/test_slskd_client.py`. It covers successful request parameters/response shape, 401/403 authentication failure, HTTP errors, invalid/missing configuration, and API-key redaction. Run `python -m unittest tests.test_slskd_client -v`, `python -m unittest discover -s tests -v`, syntax checks, and all four exact-final-head workflows (syntax/acquisition safety; Docker packaging/full suite/build; isolated runtime smoke; validation-only multi-architecture build). These tests and CI are not yet verified for the final PR head. Do not publish or deploy.

## 2026-10-16 — Progress-calculation extraction verification (PRs #182–#183)

- **PR #182**, final tested head `045131f58365dd0e6538c1712f37f56f639c65ad`: syntax/acquisition-safety run 1016, Docker packaging/full unit suite/build run 923, container runtime smoke run 732, and validation-only multi-architecture run 776 all succeeded. Merged as `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`.
- Direct-import tests cover completed-state inference, byte-counter aliases, invalid/negative values, size clamping, and actual-counter snapshots. The full suite ran in the packaging workflow.
- **PR #183**, final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`: syntax/acquisition-safety run 1019, Docker packaging/full unit suite/build run 926, container runtime smoke run 735, and validation-only multi-architecture run 779 all succeeded. Merged as `e4e9bd1fad9536f00f3908d753b66147d30ca03f`.
- The initial PR #183 head failed one newly added assertion because the fixture used a 1-second elapsed interval but expected the half-second rate. Corrected the expected value to 200 bytes/second; the final exact head passed all four workflows, including 342 unit tests.
- Assistant-side local test commands were not run. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — slskd queue and progress-matching extraction verification

- **PR #180**, exact final head `ce0e635cc77c687958d6ad1c1a852e55476c14b2`: syntax/acquisition-safety run 1008, Docker packaging/full unit suite/build run 915, container runtime smoke run 724, and validation-only multi-architecture image validation run 768 all succeeded. Merged as `7c670f2eac838934bc9afa7f40f892ff595ca4ca`.
- **PR #181**, exact final head `cf78b4188a549d6e1b2b98c76a63a6bc0826d129`: syntax/acquisition-safety run 1010, Docker packaging/full unit suite/build run 917, container runtime smoke run 726, and validation-only multi-architecture image validation run 770 all succeeded. Merged as `3df14d3c59bb7e5a689d797028e45468c6a87ee7`.
- PR #180 direct-import tests cover request URL, headers, payload, timeout, returned response, HTTP failure propagation, and legacy adapter delegation. PR #181 tests cover case-folded basename matching across Windows/POSIX separators, exclusion of unrequested records, and duplicate-state precedence.
- The CI packaging jobs passed the full unit suite on both exact heads. Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed. Neither PR changed acquisition cleanup or dismissal semantics; the HTTP 409 remains deferred.

## 2026-10-16 — Last.fm similar-artist extraction verification closeout

PR #178 head `a97be052d3a1e74843feaacd6403d10ce5aad6af` was merged as `f18574b74a564031c5268cf04c956475d64dc30c`. GitHub Actions succeeded for Python syntax (run 1003), Docker packaging validation (run 910), container runtime smoke (run 719), and validation-only Docker image build with publishing paused (run 763). These are CI results for the exact PR head. A separate assistant-side local full unit-test run was not performed; do not record one as passed. No publication/deployment/runtime-on-production verification is claimed.

---

## 2026-10-16 — Last.fm similar-artist extraction in progress

`LastFmClient.similar_artists()` direct-import regressions cover scalar/list response shapes, blank names, malformed similarity values/records, request method/artist/limit, 60-day cache TTL, cache hits, provider errors, and the `_lastfm_similar_artists()` compatibility adapter. Required exact-final-head gates remain: syntax/acquisition safety, full unit suite plus Docker build, isolated runtime smoke, and validation-only multi-architecture build (`push: false`). Assistant-side local test execution is not claimed.

---

## 2026-10-16 — Last.fm top albums extraction in progress (PR #175)

- `LastFmClient.artist_top_albums()` tests cover scalar/list payloads, blank-title filtering, normalized metadata, requested limit, 30-day cache TTL/hits, missing payloads, and compatibility adapter filtering.
- Exact-head syntax/acquisition safety, full unit suite and Docker build, runtime smoke, and non-publishing multi-architecture checks are required. CI pending; assistant-side local tests not run.

---

## 2026-10-16 — Modularization extraction verification: PRs #170–#172

- **PR #170, MusicBrainz tag audit:** direct-import tests cover sorted bounded batches, populated/missing/empty MBID tags, unreadable audio, validation/error strings, the legacy JSON adapter, and read-only behavior. Exact final head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07` passed syntax `38827001217`, full suite/build `38827001215`, runtime smoke `38827001195`, and validation-only multi-architecture `38827001227`.
- **PR #171, recommendation style rules:** direct-import tests cover broad family mapping, jazz-rap versus specific-jazz prioritization, regional artist/style overrides, and fallback classification. Exact final head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9` passed syntax `38827709662`, full suite/build `38827709650` (319 tests), runtime smoke `38827709649`, and validation-only multi-architecture `38827709610`. An incorrect initial test fixture was corrected before the final passing run.
- **PR #172, Last.fm album popularity:** direct-import tests cover the legacy cache key and TTL, HTTP request contract, stats and tag normalization, cached responses, provider errors, missing stats, silent 404s, non-404 HTTP failures, and adapter diagnostic state. Exact final head `d2808d44825e949ff71ed8471d25cee6570b54f1` passed syntax `38827973048`, full suite/build `38827972941` (324 tests), runtime smoke `38827972940`, and validation-only multi-architecture `38827972938`. An initial test fixture that did not record the injected HTTP call was corrected before the final passing run.
- The full unit suite, syntax, isolated container smoke, and non-publishing multi-architecture validation were verified by GitHub Actions on each exact final PR head. Assistant-side local test commands were not run. No image publication or deployment occurred.

---

## Acquisition Get/request and Dismiss regression coverage — in progress (2026-10-16)

Branch: test/acquisition-get-dismiss-regressions. Added browser-side source-contract regressions in tests/test_acquisition_ui_contract.py for one POST per Get click, no navigation, pending/requested/retryable transitions, server-declared failures, persistent Dismiss controls, and removal only after a successful dismissal response. Extended tests/test_acquisition_routes.py for successful Dismiss response mapping and required identity validation. Existing tests/test_acquisition_cleanup.py remains the destructive filesystem safety suite, including path traversal, symlink/race refusal, ambiguous folders, unexpected entries, and neighboring-file preservation.

The UI contract tests do not call a live API or perform filesystem deletion. They inspect the browser JavaScript source rather than execute a real browser; therefore manual browser verification against the exact final PR-head SHA remains required after CI passes. Focused/full test results and exact-head workflow results are pending. The reported dismissal HTTP 409 remains deferred unless it recurs; this work does not claim to fix its root cause.

---

## slskd transfer listing extraction — completed verification (PR #157)

Exact final PR head `504b10392061dbc44d28d66e663b88cbefb8f1a4` passed all four required workflows: Python syntax/acquisition-safety regressions `38816375215`; Docker packaging, full unit suite, and image build `38816375266`; isolated container runtime smoke `38816375339`; validation-only multi-architecture image validation `38816375410`. PR #157 merged at `17922f878f0ea391b47652012a38530e9eb044fc`. No separate local test execution, image publication, deployment, or production runtime verification is claimed.

## Expected slskd track-count extraction — completed verification (PR #155)

Exact final PR head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6` passed all four required workflows: syntax/acquisition-safety `38814733899`; Docker packaging/full suite/build `38814734001`; runtime smoke `38814733916`; validation-only multi-architecture validation `38814733954`. PR #155 merged at `d732241de9edfd3c643a8fa89fb25c42b2a93c67`.

## Session priority gate — PR #156 completed

PR #156's manual browser checklist was completed and published against exact head `47d33cbecadf64ed4b434764883cec6ae99d30bc`; all eight items passed with zero failures. Its four required CI workflows passed on that same head (syntax `38815023255`, Docker packaging `38815023085`, runtime smoke `38815023444`, validation-only Docker image/multi-architecture validation `38815023661`). PR #156 merged at `c560c28063f26a1a72d7016c951bf265d2ddd158`. No real screen reader was tested; the missing skip link remains a separate backlog item. Before another routine backend extraction, re-check current main/open PRs/CI and choose the highest-priority remaining safety or verification gap. See `docs/DEVELOPMENT_WORKFLOW.md` for merge gates.

---

## Standard multi-extraction session protocol

A session may complete two or three small extractions, but each extraction must pass its own independent acceptance and verification gates. The default is one extraction per PR; combine extractions only when they are tightly coupled and explain why independent review/testing is not practical. Do not treat throughput as a quota.

For each extraction, before merge:

1. Trace production callers, compatibility adapters, tests, configuration and Docker packaging. Add direct-import tests for the extracted module and compatibility tests for the existing public/MCP-facing adapter. For acquisition/import/cleanup, retain positive and refusal cases, including traversal/symlink escapes, ambiguous targets, unrelated-file preservation, rollback and interrupted recovery as applicable.
2. Run focused regression tests, `python -m unittest discover -s tests -v`, syntax checks, and relevant API/Docker checks when available. Record commands and real outcomes; list skipped or unavailable checks explicitly.
3. Review the full diff and ensure no unrelated changes, weakened safety validation, secrets, or missing packaged modules.
4. On the exact **final PR-head SHA after all edits**, require all four workflows to pass: (a) Python syntax and acquisition-safety regressions; (b) Docker packaging, full unit suite and image build; (c) isolated container runtime smoke; (d) validation-only multi-architecture image validation. Publishing remains disabled. A result from an earlier SHA does not verify a later documentation or code commit.
5. For UI-facing PRs, run the documented manual browser checklist after automated CI passes, against that exact tested SHA. Non-UI changes require relevant automated/API/integration checks but not an unrelated full visual pass.
6. Merge only after acceptance, diff review, and all required checks pass. Refresh GitHub `main`, PR list, and CI after each merge before proceeding to the next extraction. If later work depends on a merge, retarget/update the branch safely and rerun required checks on its new exact head.

For the session closeout, record each PR separately in `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md`: branch, PR, exact tested SHA, focused/full test outcomes, four workflow outcomes, merge SHA, skipped checks, and distinct publication/deployment/runtime status. Stop rather than bundle additional work if a safety issue, unexpected coupling, or failed gate appears. See `docs/DEVELOPMENT_WORKFLOW.md` for the operational sequence.

---

## 2026-10-15 — Music path default policy extraction (verified)

Direct-import regression tests in `tests/test_music_paths.py` cover explicit environment override and home expansion, server mount preference, Mac mount fallback, and production fallback. All four required workflows passed on exact PR head `07cf1ab7dab46a1409236f7134881011dc31cac2`: syntax plus acquisition safety regressions (`38805068326`), Docker packaging/full unit suite/build (`38805068317`), container runtime smoke (`38805068315`), and validation-only multi-architecture build (`38805068337`). Publishing remains paused; no production deployment/runtime verification is claimed.

## 2026-10-15 — Navidrome API client extraction (pending verification)

Run `python -m unittest tests.test_navidrome_client -v` and the full `python -m unittest discover -s tests -v` suite. Direct-import tests must cover deterministic token generation, base URL and method path, authentication/version/client/format parameters, forwarded caller parameters, HTTP client timeout and redirect policy, successful response handling, and exact legacy API error messages. Then verify Python syntax, Docker packaging/full tests/build, isolated container runtime smoke, and validation-only multi-architecture Docker image validation on the exact final PR head. Initial exact implementation head `555da7027ae0aa9f636ba66e18b33d549cd787d6` passed the four workflows (syntax `38802076122`, Docker packaging/full suite `38802076327`, runtime smoke `38802076229`, multi-architecture validation `38802076245`). Because this note is a documentation-only follow-up, rerun and confirm all four workflows on the resulting final PR head before merge.

## 2026-10-15 — Metadata cache extraction CI follow-up

- Initial PR-head CI exposed a regression-test fixture issue: the malformed-JSON test inserted directly before creating the cache table. The fixture now initializes the table through the public cache service before inserting malformed JSON.
- Corrected test commit: d6e28b665a3b16cbd3aba68744e1943a73d1cda1. All required workflows must be rechecked on this exact updated head; the initial failed run is not evidence of a passing suite.

## 2026-10-15 — Metadata cache extraction (pending CI)

Direct-import tests in tests/test_metadata_cache.py cover Unicode JSON round-trips, cache misses/expiry, malformed cached JSON, and non-fatal storage failures for the extracted MetadataCache. Run this focused test, the full unit suite, syntax checks, Docker packaging, runtime smoke, and validation-only multi-architecture build on the exact PR head before merge. No result is claimed until those checks complete.

## 2026-10-15 — Completed: slskd settings boolean validation

- `PUT /api/settings/slskd` accepts explicit JSON booleans for `auto_acquire_for_me`, rejects strings (including `"false"`), numbers, null, arrays, and objects with HTTP 400 before service invocation, and preserves the existing value when the field is omitted.
- Regression test coverage was added in PR #147 and merged at `9ce0ae37ae207f79180d98b10f71147736fe2a75`.
- Exact tested PR head `22db7e7b4414f1ff3df7440bc47aece41bf0ae1d`: syntax, container runtime smoke, Docker packaging, and Docker image validation all passed.
- Docker image publishing remains paused; deployment/runtime verification was not performed.

## slskd settings boolean validation — PR in progress

- For `PUT /api/settings/slskd`, an omitted `auto_acquire_for_me` must remain omitted/unchanged; explicit JSON `true` and `false` must be forwarded as booleans.
- Reject strings (including `"false"`), numbers, null, arrays, and objects with HTTP 400 before invoking the service. This prevents truthiness coercion from enabling a setting unintentionally.
- Run focused settings route/service tests, the full unit suite, syntax checks, container runtime smoke, and validation-only multi-architecture build on the exact final PR head. Do not claim results until the workflows complete.

## UI accessibility PRs — 2026-10-15

- PR #144 landmark naming merged at `f1008bb3af25c7c76dac8bae67177a07b21df147` from exact tested head `4b44cdb98485a93ba86ac102f29081b917d4e4fe`; manual report was published.
- PR #142 contrast merged at `77faf5e03fdc4985541b0da5952568d0925336df` from conflict-resolved exact PR head `dd5561bff2ca8b89ca934a60f8348e67a044093c`. All four required workflows passed on that exact head: Docker packaging `38794146977`, validation-only multi-architecture image validation `38794146985`, Python syntax `38794147000`, and container runtime smoke `38794146979`.
- Conflict resolution retained the merged landmark documentation and the `--subtle: #94958b` contrast fix. The contrast manual report applies to prior head `38addc52dfb14ccbf95a72ffad2dbd0713d9fcf9`; the combined resolution head did not receive a separate manual browser pass.
- Publishing remains paused. No deployment or production runtime verification is claimed.


## Settings persistence extraction — PR #143 merged

- PR #143 exact final head `e28cd12d3736fd2eb368b53c98e3cbddb5438166`; squash merge `409f634a20ba67c5a39dfec0e5bf57995a3fefbe`.
- Direct-import regressions cover Unicode round trips, corrupt JSON fallback, append-only legacy quality-tier migration, configured absolute music-path application, and restrictive SQLite file mode. Legacy `_discovery_settings_init/read/write` wrappers and MCP-facing settings functions remain available.
- All four required exact-head workflows passed: Docker packaging/full suite/build `38791730058`, Python syntax `38791730078`, container runtime smoke `38791729963`, and validation-only multi-architecture image validation `38791730017`.
- No separate local test execution, publishing, deployment, or production runtime verification is claimed. Publishing remains paused.

## MCP registration isolation — current PR

- Run python -m unittest tests.test_mcp_registry tests.test_auth_routes_integration -v and the full python -m unittest discover -s tests -v suite.
- The regression must prove all 27 existing MCP tool functions remain callable through the explicit registry, registry names are unique and stable, and importing navidrome_server does not load mcp.server.mcpserver.
- First verification cycle passed on implementation head fe71a9a19188a018a2ee65d5b313a99413d239f2: syntax/acquisition safety 38783091362; Docker packaging/full suite/build 38783091326; runtime smoke 38783091309; validation-only multi-architecture 38783091337. The final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f also passed all four workflows (38783296279, 38783296173, 38783296256, 38783296249) and PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00. Publishing remains paused.

## Authentication signing-key symlink refusal — PR #137 merged

- `tests/test_app_auth.py::test_signing_secret_refuses_symlink_without_chmodding_target` checks an existing `app_auth.key` symlink is rejected and the target contents and permissions remain unchanged.
- Exact final PR head `f6458af4b84b957902a2da1960cdafc06d0f7594` passed all four required workflows: Python syntax, Docker packaging/full unit suite/build, container runtime smoke, and validation-only multi-architecture image build. Publishing remains paused. No separate local test run is claimed.

---

## Authentication signing-key symlink refusal

- `tests/test_app_auth.py::test_signing_secret_refuses_symlink_without_chmodding_target` verifies an existing `app_auth.key` symlink is rejected and its target contents and permissions remain unchanged.
- Run `python -m unittest tests.test_app_auth -v`, the full unit suite, syntax checks, container runtime smoke, and validation-only multi-architecture workflow on the exact final PR head. No local test execution should be claimed unless actually performed.

---

## Concurrent authentication rate-limit regression — PR #134

- `tests/test_auth_routes_integration.py::test_concurrent_login_attempts_cannot_race_past_rate_limit` holds one password-verification call while another request reaches the last available per-client attempt slot.
- Expected HTTP outcomes are one `401` for the in-flight bad password and one `429` for the request that would exceed the limit. This catches check-then-record races without timing-only assertions.
- Run `python -m unittest tests.test_app_auth tests.test_auth_routes_integration` and all four required CI workflows on the exact final PR head before merge. PR #134 final head `a15fa4e9b588e7fa96d36242f51b55b23fba9e70` passed Python syntax `38776917077`, Docker packaging/test-and-build `38776916979`, container runtime smoke `38776917024`, and Docker image validation `38776917027` (publishing paused). PR #134 was squash-merged at `ef6ce0ff4faa9fffca66a7e43294eee6a0847dbd`. No local test execution is claimed; publishing, deployment, and production runtime verification are separate.

---

## Authentication malformed-token regression

- `tests/test_app_auth.py::test_malformed_non_ascii_session_token_is_rejected_without_exception` verifies a non-ASCII session-token segment returns `None` rather than leaking `UnicodeEncodeError` from the authentication boundary.
- Run `python -m unittest tests.test_app_auth tests.test_auth_routes_integration` plus the full Docker packaging/unit-test workflow and the other required exact-head CI workflows before merge. Report only tests actually run; no local test execution is claimed for the initial PR preparation.

---

## 2026-10-15 — API boolean input validation

- For `POST /api/acquire`, test omitted `auto_queue` defaults to true, explicit JSON false remains false, and non-boolean JSON values (including strings, numbers, null, arrays, and objects) return HTTP 400 without invoking the service.
- Run focused acquisition route tests and all four required exact-head workflows before merge. No local test execution should be claimed unless actually performed.

---

## 2026-10-15 — PR #116 merged: Proxmox MCP SDK compatibility and handler regression

- PR #116 merged at `9e6979203cbdb6f2d38225584952136170eb2df5` from exact tested PR head `a14accac574d1997e6785ffbf170be136b95c5b9`.
- Corrected the host-side entry point to use `mcp.server.mcpserver.MCPServer`, matching pinned `mcp==2.3.0` and the main MCP server. MCP startup now occurs only when `server.py` is executed as a script.
- Added handler regressions proving rejected shell-composed commands never invoke SSH, accepted commands retain the existing SSH argument/timeout/output behavior, and output remains capped at 20,000 characters.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety `38742736856`; Docker packaging/full suite/build `38742737079` (243 tests passed); container runtime smoke `38742737082`; validation-only multi-architecture image validation `38742736770`.
- An earlier CI cycle exposed the stale FastMCP import; the defect was corrected and all four workflows passed on the final head. No local test run or live Proxmox command, image publication, deployment, or production runtime verification is claimed.

---

## Proxmox MCP command allowlist — PR #114 verified and merged

- Direct-import regressions accept only explicitly approved diagnostic forms and reject arbitrary commands, shell operators, command substitution, newlines, invalid container IDs, unsafe device paths, and non-string input.
- The `server.py` handler refuses rejected input before invoking SSH. The `run(command: str)` MCP signature, SSH target/options, timeout, and output truncation for accepted commands remain unchanged.
- Exact tested PR head: `cd8319696180875a3cb6f0dc151d88e0c8c490d7`; squash merge: `6ab848d444373dfa37e6d46528a2840a53a8f763`.
- All four required workflows passed on that exact head: syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`.
- No local test execution or live Proxmox command is claimed.


---

## 2026-10-15 — PR #108 verified and merged

- Migrated discovery route unit tests from patching `discovery.librarian` to explicit fake-service injection, consistent with the new lazy dependency seam.
- Final tested PR head: `a5170e50080c0ca94b4068155ace83fd33c6f029`; squash merge: `be51f0ce17fe8eccd1b57714e869db69a5f1ba78`.
- All four required workflows passed on that exact head: Python syntax/acquisition safety `38733725606`; Docker packaging/full unit suite/build `38733725816` (227 tests); container runtime smoke `38733725595`; validation-only multi-architecture image validation `38733725591`.
- No separate local test run, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #107 merged: acquisition router service injection

- **PR:** https://github.com/abucalip/navi-librarian/pull/107; final tested PR head `67174e8026f44382a4a6bea48ff1df80744dda35`; squash merge / main SHA at closeout `1cc15dd6343370ce0915bf7228a745d3558b393b`.
- **Change:** added `app/api/dependencies.py` with lazy `get_librarian()` and injected it into all acquisition routes. This removes the acquisition router's import-time import of `navidrome_server` while preserving endpoint paths/methods, existing service calls, payload mapping, HTTP error behavior, and SSE response headers. Added regression tests for route contracts, dependency wiring, fake-service handler calls, validation, and sanitized errors.
- **Exact-head CI:** all four required workflows passed on `67174e8026f44382a4a6bea48ff1df80744dda35`: Python syntax `38732084595`; Docker packaging/full unit suite `38732084663`; container runtime smoke `38732084579`; validation-only multi-architecture image build `38732084589`. An earlier test-only assertion failure on `d6a1696c06f594e2c4025e0eff54bb8496fd8e29` was corrected before these passing runs.
- **Status:** Implemented, tested, CI passed, merged. Publishing remains paused; this did not publish an image, deploy the application, or verify production runtime. `app/main.py`, discovery, and settings still import `navidrome_server`; MCP tools and domain logic were not removed or duplicated.
- **Next priority:** continue the narrow web service-injection audit at the discovery router, preserving API behavior and MCP compatibility. Keep deployment/runtime verification as a separate gate; do not resume routine modularization if a higher-priority safety or delivery gap appears.

---

## 2026-10-15 — Web service-injection acceptance criteria (planning)

- Existing web route modules import `navidrome_server` directly. A future dependency seam must preserve all route paths/methods and payload mapping, provider error handling, status codes, SSE streaming, settings persistence, and the existing MCP tool surface.
- Keep domain behavior in shared service functions; do not duplicate it in FastAPI. The current auth router factory is an example of injected dependencies; metadata routes are already independent of the legacy server.
- Add tests proving routers can be constructed with a fake service without importing/initializing the MCP server, while the production app still uses the existing server-backed adapter. Run focused route/auth tests, full unit suite, syntax/acquisition safety, Docker packaging/full suite, runtime smoke, and validation-only multi-architecture checks on the exact final PR head.

---

## 2026-10-15 — PR #103 verified and merged: import source-root guard

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- Regression coverage verifies a source-folder symlink swap fails closed while preserving outside files and original tracks; collision-suffixed matching, cross-filesystem fallback, and partial-move rollback remain covered.
- All four required workflows passed on the exact head: syntax/acquisition safety `38726626891`, Docker packaging/full unit suite/build `38726626846`, runtime smoke `38726626956`, and validation-only multi-architecture image validation `38726626910`. No local or production-folder test is claimed.

---

## 2026-10-15 — PR #100 verified and merged: cleanup root traversal

- PR #100 merged at `6e8e861cc84d5951b0d177ffea256a0dd88fe4b4` from exact tested head `89813bd3802b1f8920715aaeca55ccb5e461c9c9`.
- The regression suite covers target-directory and parent-directory symlink replacement during transfer lookup; both the outside target and moved original album file must survive. Cleanup uses no-follow root traversal, descriptor-relative unlink/rmdir, exact planned-entry validation, and device/inode/size checks.
- All four required workflows passed on that exact head: syntax/acquisition safety `38724953760`, Docker packaging/full unit suite/build `38724953699`, runtime smoke `38724953828`, validation-only multi-architecture image validation `38724953678`. No local or production-folder deletion test is claimed.

---

## 2026-10-15 — PR #99 cleanup directory-swap regression verified

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- Regression covers replacement of the preflighted album folder with a symlink during external transfer lookup; cleanup must fail closed while preserving both the outside target and moved original album track.
- All four required workflows passed on the exact head: syntax/acquisition safety `38724377954`, Docker packaging/full unit suite/build `38724378021`, runtime smoke `38724378097`, and validation-only multi-architecture image validation `38724377870`. No separate local test or production-folder deletion test is claimed.

---

## 2026-10-15 — PR #98 verified and merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- All four required workflows passed on that exact head: syntax/acquisition safety `38723927107`, Docker packaging/full unit suite `38723927072`, runtime smoke `38723927058`, and validation-only multi-architecture validation `38723927057`. Existing AST adapter integration coverage remains alongside direct-import coordinator tests.
- No separate local tests, publishing, deployment, or production runtime verification.

---

## 2026-10-15 — PR #97 verification complete

- Added direct-import regression coverage for Last.fm key trimming, blank-input preservation, and response redaction while preserving the existing success JSON contract.
- All four required workflows passed on exact PR head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`: Python syntax/acquisition safety `38721333335`, Docker packaging/full unit suite `38721333353`, container runtime smoke `38721333332`, and validation-only multi-architecture image validation `38721333418` (publishing paused).
- No assistant-local test run, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #96 slskd settings policy validation

- `service_settings.py` is the direct-import owner for slskd config validation and settings read/update policy; MCP wrappers remain in `navidrome_server.py`.
- Regression coverage includes blank API-key preservation, no API-key serialization, invalid URL refusal, exact quality-tier set validation (including malformed JSON values that are not strings), invalid music/download path refusal without writes, default serialization, and successful runtime music-path callback.
- `tests/test_quality_priority.py` now invokes the extracted policy directly for quality-order save/rejection tests; AST-executed SQLite settings helpers remain for storage migration/persistence behavior only.
- Implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed syntax/acquisition safety (`38665710740`), Docker packaging/full unit suite (`38665710718`, 208 tests), runtime smoke (`38665710761`), and validation-only multi-architecture image validation (`38665710769`). The initial failure was a stale AST namespace assumption and was fixed before this passing head.
- Required before merge: rerun all four workflows on the final docs-updated PR head. No local test run, image publication, or deployment is claimed.

---

## 2026-10-15 — slskd settings-policy extraction (next PR)

- Directly import `service_settings.py`; do not use AST extraction or initialize MCP in policy tests.
- Verify `slskd_config` rejects invalid HTTP(S) URLs and missing keys, and never serializes the API key in settings responses.
- Verify get-settings defaults and quality labels, blank API-key preservation, and successful write/path callback behavior.
- Invalid URL, malformed/duplicate/missing quality tiers, relative/nonexistent music-library paths, and relative download paths must return the existing error contract without settings writes or runtime path mutation. Malformed quality elements must fail safely rather than raise from set conversion.
- Keep connection tests, SQLite persistence/schema, and global `MUSIC_DIR` ownership in the legacy adapter. Run focused `python -m unittest tests.test_service_settings -v`, full `python -m unittest discover -s tests -v`, syntax checks, and all four required workflows on the exact final PR head. Publishing remains paused.

---

## 2026-10-15 — Service settings policy direct-import migration (PR #95)

- `tests/test_service_settings.py` now imports `service_settings.py` directly instead of parsing and executing selected functions from `navidrome_server.py`.
- Regressions cover password/API-key redaction, Navidrome credential validation, blank-password preservation, invalid URL/user/path refusal without writes, library-directory update callback behavior, and ListenBrainz username validation/no-write behavior.
- The legacy adapter signatures remain unchanged; SQLite and global runtime path ownership are not extracted.
- Final PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9` passed all four required workflows: syntax/acquisition safety (`38664285319`), Docker packaging/full unit suite and build (`38664285227`), container runtime smoke (`38664285195`), and validation-only multi-architecture image validation (`38664285194`). An earlier implementation revision exposed a callback-injection mismatch; it was corrected before final-head verification. No local tests were run. Publishing remains paused; no deployment or production runtime verification is claimed.

---

## 2026-10-15 — Web dependency audit and next test seam

- Dependency audit found web routes call the legacy server for settings, Navidrome service checks, recommendation/list orchestration, and all acquisition lifecycle actions. Keep these integration boundaries intact during modularization.
- `tests/test_service_settings.py` currently uses AST extraction to execute six real functions in a stub namespace. Next migration candidate: extract those six settings-policy/configuration functions to an importable module with injected settings read/write and music-directory dependencies, then test the actual module directly.
- Required regression assertions for that extraction: Navidrome URL and credential validation; blank-password preservation; no password/API-key leakage in returned payloads; ListenBrainz username validation and no write on invalid input; existing response shapes/messages; music-library path handling; and unchanged MCP wrapper signatures. Keep storage/migration/global path ownership in the legacy server.
- Do not combine settings policy with live network checks, SQLite schema changes, or MCP dependency removal. Test the new module directly and add adapter tests for compatibility.
- Audit only in this session: no code/tests changed and no local tests were run. PR #93 CI was green on its exact head; current merge-main workflow status must be verified independently.

---

## 2026-10-15 — Acquisition lifecycle AST-boundary audit

- Compared the remaining AST-coupled acquisition lifecycle regressions with direct-import tests on `main`. No test was deleted because each still covers top-level orchestration/adapter behavior not fully exercised by isolated helper tests.
- Keep the simultaneous-request test for shared-lock/reservation integration; keep the import-persistence-failure test for persist-before-filesystem-import ordering; keep incomplete-saved-candidate coverage for top-level no-search/no-watcher behavior; keep both dismissed-job Get outcomes for adapter/status behavior; keep stale-watcher recovery for coordinator routing/no-requeue behavior; and keep broad-query retry for end-to-end sequencing/diagnostics.
- Direct tests for reservation, recovery decisions, reactivation preflight, polling, and lifecycle policy remain complementary. Any future migration must prove equivalent integration-boundary assertions before removing an AST case.
- Audit only; no code/tests changed and no local tests were run. The four required workflows passed on baseline `main` `c6017f7a59e2aaec09e498ca4bda9315b0325cd3`; these are not results for this documentation branch.
- Next: read-only audit of web and entry-point dependencies on `navidrome_server.py` before proposing any MCP retirement. Keep MCP compatibility and runtime dependencies intact until web-required behavior has independently tested owners.

---

## 2026-10-15 — PR #92 merged: dismissed-acquisition preflight coverage

- PR #92 merged as `60698f7bf1413e4c643309e200d1ace2e268bee3` from exact tested head `1f0ce2174e1e60f3aab7c898dd534b8b1f11e858`.
- Direct-import tests cover non-dismissed bypass, valid metadata forwarding, malformed/non-object metadata normalization to `{}`, and refusal when reactivation fails.
- All four required workflows passed on that exact PR head: syntax/acquisition safety `38661883721`; Docker packaging/full suite `38661883755` (203 tests); runtime smoke `38661883730`; multi-architecture validation `38661883723` (publishing paused).
- Retain AST integration tests `test_explicit_get_reactivates_safely_dismissed_job` and `test_dismissed_job_stays_blocked_if_reactivation_fails`; they protect the top-level Get flow and response behavior. Preserve shared transition-lock ownership.
- Next: continue auditing remaining AST-coupled acquisition lifecycle tests for safe direct-import seams without weakening end-to-end transition coverage.

---



## 2026-10-15 — Acquisition reservation lifecycle verified

- PR #90 merged at `4756ad6a7669ab77e284309ca9cd0f178e7f032a` from exact tested head `c0b4a0ebcc5fa4ef8b71441fb38d55aed8fce097`; all four workflows passed, with 199 unit tests.
- Direct tests verify reservation of a fresh identity, duplicate refusal without mutation, and preservation of unrelated active identities. Reservation still occurs while the coordinator owns the shared transition lock.
- The callback runs outside the lock; `run_reserved_acquisition` guarantees cleanup under the lock on success and exception. Keep the top-level simultaneous-request regression.
- Next: cover dismissal/reactivation preflight through an injected orchestration helper, retaining coordinator-level success and refusal tests. Any further extraction requires focused/full tests and all four exact-head workflows.

---

## 2026-10-15 — Watcher-start concurrency regression verified

- PR #84 exact tested head: `398486476aacdbbefefeaee5cb79182cc0835fb8`; all four required workflows passed: syntax/acquisition safety run 38656927551, Docker packaging/full suite run 38656927436, runtime smoke run 38656927801, and multi-architecture validation-only run 38656927516.
- The full unit-test step and acquisition safety regression step passed. The new race test asserts exactly one successful watcher reservation, persisted job, and thread start under simultaneous calls.
- Diff review found no production changes. Retain remaining AST integration tests until direct-import tests cover equivalent coordinator, persistence, and recovery boundaries.
- Publishing remains paused; no deployment or production runtime verification.

---

## 2026-10-15 — Session closeout: remaining AST-coupled lifecycle coverage

- Baseline reconciled against GitHub `main` at `f46b3618eaa8abc98b7f077698439b304a0005b7`; PR #82's documentation closeout is merged. Its exact tested head `5fdad1045ba04db84aea05a477a51dce38733f5c` passed all four required workflows; this session adds no new test result.
- Continue comparing the remaining AST cases with direct-import coverage for duplicate-request reservation/concurrency, incomplete saved candidate details, dismissed-job reactivation and failed-reactivation refusal, and stale watcher recovery.
- Do not remove tests that uniquely verify shared-lock races, conditional persistence before filesystem import, or watcher/coordinator integration. Any migration must preserve the same failure-path assertions and be followed by focused tests, the full suite, syntax checks, final diff review, and all four required workflows on the exact PR head.

---

## 2026-10-15 — PR #78 merged: import dismissal coordination

- PR #78 exact tested head: `e6a609ca7381d0751d529b52f55aeebd56d76661`; squash merge: `5d638c7adf5a42fdac8052cb4fc223236564cd72`.
- Direct tests cover the dismissal-serialized import callback: lock spans the check and callback, dismissed state prevents callback execution, and return values/exceptions propagate.
- The AST integration test `test_import_does_not_move_files_if_importing_status_cannot_be_persisted` remains to verify the full server adapter does not enter filesystem import before the persisted importing transition succeeds.
- All four required workflows passed on exact head: syntax `38653493244`, Docker packaging/full unit suite `38653493312`, runtime smoke `38653493285`, and image validation with publishing paused `38653493279`. Full suite: 186 tests passed.
- No live slskd, publication, deployment, or production runtime verification is claimed.

---


## 2026-10-15 — PR #76 merged: slskd polling regressions

- PR #76 exact tested head: `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6`; squash merge: `a55a9fa7eed1e221f52434b50f44d0c415fd491a`.
- Direct-import tests cover progressive query fallback, delayed peer payloads after reported response/file counts, legacy 404/405 endpoint behavior, and propagation of unexpected HTTP errors.
- All four required workflows passed on the exact head: syntax `38652846800`, Docker packaging/full unit suite `38652846779`, runtime smoke `38652846790`, and image validation with publishing paused `38652846819`. The full suite reported 184 tests passed.
- The end-to-end AST retry test remains to assert the coordinator's final response and query diagnostics. No live slskd, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #73 merged: candidate extraction direct-import regression

- PR #73 exact tested head: `a33772ca1da0b6628da490b69f1dc305b6794de3`; squash merge: `df2f79b3d18df7d13484f7e3b5e7f550a39323d3`.
- Direct-import regression preserves the four Tinariwen/Idrache folder variants, twelve unique tracks, clear-match eligibility, and FLAC quality-tier assertions against `slskd_search.extract_candidates`.
- All four required workflows passed on the exact head: syntax `38652066842`, Docker packaging/full unit suite `38652066649`, runtime smoke `38652066755`, and Docker image validation with publishing paused `38652066683`.
- Remaining AST tests intentionally retain orchestration retry/wait and lifecycle coordination behavior. No live slskd, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-14 — PR #72 merged: direct-import slskd search helper coverage

- PR #72 squash merge: `6c6157a8238691b18d2209ea2d2e1306385ec9a2`; tested head `17be72e52b39e63cad63391fb2c4e63ea55d3c26`.
- Added direct-import tests for query progression, blank/whitespace input, payload normalization, album path matching, path-match diagnostics, audio filtering, and result bounds. Removed six corresponding pure-helper cases from the AST harness.
- All four required workflows passed on the exact tested head: syntax `38651547240`, Docker packaging/full unit suite `38651547229`, runtime smoke `38651547283`, and Docker image validation with publishing paused `38651547264`.
- No local standalone test run, live slskd interaction, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-14 — Candidate-start validation extraction (PR #71 merged)

- Exact tested PR head: `f53e8ceffc8307c7b8dbcbf837e123b51671bbda`; squash merge: `b10650aa6a8889610b5734c5a1cf02c3197f1ad0`.
- All four required workflows passed on the exact PR head: Python syntax (`38648719075`), Docker packaging and full unit suite (`38648719066`), container runtime smoke (`38648719107`), and Docker image validation with publishing paused (`38648719074`).
- Coverage added in `tests/test_acquisition_candidate_start.py`: traversal rejected before lookup, mixed remote directories rejected, active transfer recognized, queued transfer cancelled before safe fallback, and uncertain cancellation/lookup outcomes fail closed.
- No standalone local test run or live slskd interaction was performed; no image publication, deployment, or production runtime verification is claimed.

- Direct-import tests now target `acquisition_candidate_start.candidate_start_state`; the AST harness no longer owns the traversal and multi-directory tests.
- Coverage includes pre-lookup traversal rejection, mixed remote directories, active transfer recognition, queued transfer cancellation, and fail-closed handling of uncertain cancellation or transfer lookup.
- Required before merge: run focused and full test suites, syntax/package checks, inspect the final diff, and verify all four required CI workflows on the exact final PR head. Do not infer test success from a successful build alone.

---

## 2026-10-14 — Completed import safety tests migrated to direct imports (PR #70 merged)

- Removed the redundant `CompletedAlbumMatchingTests` cases from the AST-based `tests/test_acquisition_safety.py` harness. Equivalent or stronger coverage already exercises the production modules directly in `tests/test_acquisition_completion.py` and `tests/test_acquisition_import.py`.
- The direct-import suites cover strict positive-size matching, Unicode/case and Windows path normalization, duplicate-basename ambiguity, symlink refusal, collision-suffix matching, exact folder diagnostics, unrelated-file preservation, destination no-overwrite, storage identity mismatch, reserved manifest rejection, and rollback after a partial move.
- The AST harness retains its separate lifecycle coordination tests. Its injected import callback is now a test spy for transition behavior; filesystem import behavior is tested against `acquisition_import.import_matched_album_files` directly.
- Test-only migration: no production code, queue/cleanup behavior, path validation, rollback implementation, or MCP compatibility changed.
- PR #70 was squash-merged at `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161` after all four required CI workflows passed on exact tested head `0916a7e9d767808bf4f65d3b034e290e5aba4703`. No standalone local test commands or manual browser tests were run for this test-only migration; no image publication, deployment, or production runtime verification is claimed.
- Next: audit remaining AST-coupled acquisition safety cases for duplicate coverage; preserve dismissal/import coordination, conditional state transitions, cleanup refusal, uncertain queue outcomes, and rollback protections.

---

## Front-end design acceptance baseline (2026-10-14)

Use [`FRONTEND_DESIGN_GUIDE.md`](FRONTEND_DESIGN_GUIDE.md) as the canonical visual-design specification and backlog for every UI-facing change. The following are verification gates, not claims that a particular change has passed:

- Automated checks must pass on the exact PR-head SHA before manual browser verification.
- Inspect the rendered UI on desktop and a narrow viewport with realistic artist/album names and artwork; check for overflow, layout shifts, and inaccessible controls.
- Verify relevant hover, focus/keyboard, active, disabled, loading, empty, success, error, and recovery states. Record unsupported or unavailable scenarios as skips.
- Inspect browser console, network requests, and server logs for relevant failures; verify existing login/setup and protected-route boundaries when assets or authentication-related UI are affected.
- Use the documented isolated helper, sandbox music/download paths, and disabled slskd for ordinary UI checks. Never perform destructive acquisition actions against live user data without explicit authorization.
- Include before/after screenshots for visual changes, summarize Impeccable guidance applied and rejected, and state the exact tested SHA. If the head changes after manual testing, retest or identify the earlier SHA explicitly.
- Report implementation, automated testing, manual browser testing, merge, publication, deployment, and runtime verification separately.

---

## Queue failure classification test migration — in progress (2026-10-14)

- Removed two tests that compiled the thin `_slskd_queue_failure_action` adapter through the AST harness. The adapter delegates to `acquisition_lifecycle.queue_failure_action`.
- Existing direct-import test `tests/test_acquisition_lifecycle.py::AcquisitionLifecyclePolicyTests.test_queue_failure_classification_never_retries_uncertain_errors` exercises retryable 400/404/422 statuses, fatal 401/403 statuses, uncertain missing/408/429/500/503 statuses, and transport errors.
- This is test-only; no production behavior or safety assertions are intentionally changed. Focused tests, full suite, syntax, exact-head CI and diff review are pending. Do not record this migration as verified until those checks complete.

## Acquisition queue guard test migration — verified (2026-10-14)

- PR #64 merged at `1596161aa525896d43c37c85533e8056a742439b` from exact tested head `3bde365e43acbe1cc95f68d7014d899046e735f6`.
- The AST-harness queue refusal test and its adapter/HTTP helper were removed; direct-import tests continue to cover the production `queue_candidate_unless_dismissed` guard for dismissed refusal, lock ordering, return propagation, and exception propagation.
- All four required workflows passed on the exact final head: syntax `38636360130`, full test/build `38636360145`, runtime smoke `38636360164`, and validation-only multi-architecture build `38636360139` (publishing paused). No production behavior changed.

## Acquisition queue guard test migration (2026-10-14)

- The dismissed-queue-refusal case was removed from the AST-based `tests/test_acquisition_safety.py` harness because `tests/test_acquisition_orchestration.py::AcquisitionQueueGuardTests::test_dismissed_acquisition_does_not_queue` directly tests the extracted production guard.
- Direct-import coverage also verifies shared-lock ordering, return propagation, and exception propagation. No safety assertion was dropped; no production behavior changed.
- Required verification: exact-head syntax/acquisition safety, full unit/build workflow, container runtime smoke, and validation-only multi-architecture workflow. Publishing remains unauthorized.

## Acquisition queue/dismissal coordination extraction (2026-10-14)

- `queue_candidate_unless_dismissed` in `acquisition_orchestration.py` is tested directly for shared-lock scope, dismissal refusal, successful return propagation, and exception propagation.
- The legacy server adapter retains the HTTP request construction and `raise_for_status()`; the guard retains the same shared transition lock and dismissal predicate.
- The AST-based safety case remains in place but delegates to the extracted implementation, avoiding loss of the prior dismissed-job/no-queue regression.
- Exact PR #62 head `4e121eb7977bb1a51ad31f9c87d0d4984497af4d` passed all four required workflows: Python syntax `38619152587`; Docker packaging/full unit suite/build `38619152213`; container runtime smoke `38619152754`; validation-only multi-architecture image `38619152728`. The PR was squash-merged as `d4a16e80f6978a58c3305bf341e370ba9708bb34`. Publishing remains paused. No local helper/manual slskd test, production filesystem operation, deployment, or production runtime verification is implied by CI.



## Acquisition watcher startup extraction

- acquisition_watcher_startup.py owns the reserve → persist → status → start sequence behind injected locks, active-set, persistence/status callbacks, and watcher entry point. navidrome_server.py retains _discovery_start_import_watcher as a compatibility adapter.
- Direct-import tests cover dismissed and duplicate starts, credential filtering in persisted settings, persistence failure releasing the reservation, and thread-start failure recording monitor_error and releasing the active marker.
- Next: extract the remaining persistent acquisition-state coordination with direct-import tests; preserve existing conditional state writes and dismissal/import transition lock.
- This extraction is not live slskd or production-runtime verification.
## PR #57 merged — acquisition watcher lifecycle

- Merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589; exact tested PR head f4b92a98bae942ac6080316c3f1803d1b6bcff76.
- All four required workflows passed on the exact PR head: syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, container runtime smoke 38605511271, and validation-only multi-architecture build 38605510906 (publishing paused).
- Regression coverage directly imports the watcher module and verifies dismissal and recovery exits, that completed transfer evidence without a verified folder does not import, and that only the verified folder is passed to the existing safe import coordinator. A first CI attempt exposed an assertion reading status details from the wrong argument position; the test was corrected before final verification.
- No separate local test run, live slskd behavior, or production filesystem behavior is claimed. Image publication and deployment remain unperformed.

## ACQ-04/ACQ-06 — dismissal cleanup safety regression coverage (PR #51 merged)

- Six focused cases exercise the actual `_discovery_cancel_and_clean_source` helper via the existing AST harness: successful cleanup only after transfers stop; refusal with unrelated files; remote `..` traversal rejection before transfer lookup; duplicate same-name folders rejected without touching either; symlinked album folder rejected without touching the target; failed transfer cancellation preserving local files.
- Initial CI on `b8e1c9a398853851e1a8140a9724600800f42c3b` failed because loading the real helper replaced a stub used by an existing source-switch test. The test harness now gives the helper a distinct namespace name; all four workflows passed on final PR head `58021141472c85c9fa33c431cba15cb66792bc1c`.
- CI runs: syntax/safety `38590192829`; Docker packaging/full unit tests `38590192830`; container runtime smoke `38590192905`; validation-only multi-architecture build, publishing paused, `38590192858`.
- Merged to `main` at `790d690ca99866878ee6204f9d101dec5f099994`. PR #52's documentation closeout passed all four required workflows on exact head `4684fb257685aec90025af0b02a7dff5eacfe10a` and merged at `7f05363c3b9abec29ef7c7d516bad2796813b11e`.
- Follow-up PR #53 adds a regression that successful cleanup preserves sibling artwork and another album folder. All four required workflows passed on exact head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7`: syntax `38594117785`, Docker packaging/full unit suite `38594117579`, container runtime smoke `38594117489`, and validation-only multi-architecture `38594117597` (publishing paused). Existing coverage also proves an unexpected file inside the target folder aborts before deletion of expected tracks.
- Assistant did not run tests locally. No live slskd, real production-folder deletion, publication, deployment, or production runtime testing. The HTTP 409 was not reproduced and remains deferred.

## Acquisition lifecycle policy module (PR #47)

- Direct-import tests in `tests/test_acquisition_lifecycle.py` cover monitor-recovery eligibility, conservative cleanup requirements, skip-request rejection states, queue-failure retry classification, and fallback candidate/payload normalization.
- Preserve the invariant that ambiguous queue outcomes remain monitored rather than triggering duplicate source retries; only explicit peer-level rejections may retry another source.
- These tests cover the extracted policy seam only. They do not replace the remaining AST-based orchestration/safety cases; migrate those as the watcher, source-switch, cleanup, and recovery implementations move into domain modules.

## Legacy-server dependency audit — test implications (2026-10-14)

- The read-only audit found `tests/test_acquisition_safety.py` extracts selected function bodies from `navidrome_server.py` using AST parsing and executes them in a stub namespace after stripping MCP decorators.
- Treat these as real safety/lifecycle regression tests, not disposable test scaffolding. When extracting functions, migrate cases to direct imports of the new domain module and ensure they exercise the actual implementation.
- Keep coverage for acquisition state transitions, dismissal/cleanup, candidate/source failover, completed-folder matching, safe imports, traversal/symlink rejection, ambiguous targets, no-overwrite behavior, and rollback. Add unsafe-failure cases alongside success cases.
- Direct-import tests already exist for acquisition completion/import, slskd search/quality, discovery persistence/refresh/recommendation rules, and extracted API routers. Their existence does not prove the remaining orchestration is independent of the legacy server.
- Audit verification only: GitHub source/docs inspected; no tests were run. No CI pass is claimed for audited main SHA `edc6239c0a01573e1eaa3161a4485ca03a9851da`.

## PR #44 — acquisition dismissal diagnostics: manual report (2026-10-14)

- Tested exact PR head `4c505423afef8c6959063ddea7e5672a0b9894ef` in the isolated local helper environment on macOS 26.2 arm64, Python 3.12.14, port 8089, per-commit app data, sandbox music/download paths, and slskd disabled by default.
- User-reported manual checklist passed: setup/login, dashboard/artwork, discovery, navigation/album details, settings save/load without secret exposure, Get/request without a real download, acquisition cards/status, and no unexpected browser/server errors.
- Dismiss attempts all succeeded; HTTP 409 was **not reproduced**. No cleanup refusal stage was captured, so this is not evidence of a root-cause fix.
- The report's trailing console detail was truncated (`console showed 2$`); no inference is made from it. Full suite and CI claims remain limited to the exact-head GitHub Actions results recorded in PR #44.
- PR remains draft/unmerged pending reproduction or other concrete evidence. No live slskd test, image publication, deployment, or production runtime verification.
 
## Authentication security helper extraction — PR #37 merged (2026-10-14)

- Branch: `refactor/auth-security-helpers`, based on updated GitHub `main` after PR #36 and documentation closeout.
- Added `app/security/auth.py` for persistent signing-secret loading, username/password policy, PBKDF2 digest, and signed-session creation/validation. `app/main.py` imports these primitives and retains compatibility wrappers; HTTP routes, cookie settings, login throttling, and middleware are intentionally unchanged.
- Updated `tests/test_app_auth.py` to import the extracted primitives directly without AST-loading functions from `app/main.py` or starting the service. Tests cover username/password policy, deterministic salt-sensitive digest, signed token expiry/tampering/user binding, persistent secret reuse, private POSIX permissions, and invalid-secret failure.
- Exact-head verification on `192b084850ecbe0137b64b3dae9d07e0471198b4`: Python syntax/full-unit-test workflow `38488744726` passed; Docker packaging/full-unit-test workflow `38488744684` passed; container runtime smoke `38488744607` passed; validation-only multi-architecture `38488744643` passed. No local test execution is claimed.
- Security-sensitive extraction: no intended auth behavior change. PR #37 was squash-merged at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3`. No local test run is claimed.

## Metadata API route extraction — PR #36 merged (2026-10-14)

- Branch: `refactor/metadata-api-router`, based on the updated GitHub `main` after PR #35 and documentation closeout.
- Moved `/api/artist-bio`, `/api/album-year`, `/api/album-details`, and `/api/artwork` with provider/cache helpers into `app/api/metadata.py`; registered the router in `app/main.py`.
- Added `tests/test_metadata_routes.py` for endpoint/method inventory, artist bio cache and validation, MusicBrainz year preference, exact Deezer album matching and tracklist parsing, and artwork cache/validation.
- Verification on corrected exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`: Python syntax/full-unit-test workflow `38488440438` passed; Docker packaging/full-unit-test workflow `38488440512` passed; container runtime smoke `38488440488` passed; validation-only multi-architecture `38488440439` passed. The initial full suite revealed the AST-coupled artwork retry test; after migration to the extracted module, the corrected full suite passed. No local test execution is claimed.
- No intended UI contract change; manual browser testing was not required. PR #36 was squash-merged at `15011614649470c9c71734422b95ee048fbf9f3c`. No image publication or deployment occurred.

## Discovery API route extraction — PR #35 merged (2026-10-14)

- Branch: `refactor/discovery-api-router` (based on GitHub `main`).
- Added `app/api/discovery.py` and `tests/test_discovery_routes.py`; `app.main` registers the router and no longer defines the four discovery/recommendation handlers inline.
- Focused command: `python -m unittest tests.test_discovery_routes -v`.
- Baseline commands: `python -m py_compile navidrome_server.py app/main.py app/api/discovery.py` and `python -m unittest discover -s tests -v`.
- Direct-import tests cover route/method inventory, recommendation count defaults and album-candidate filtering, discovery list validation/defaults, refresh count parsing/defaults, feedback validation and Unicode metadata serialization, domain payload mapping, and sanitized errors.
- This is an API-only extraction with no intended UI contract change. Manual browser testing is not required unless review/CI reveals a UI behavior change. PR #35 was squash-merged from exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d` at `d61162b29c6f0cccc97aefe9c779567e671651b2`. Python syntax/full-unit-test workflow run `38487647938`, container runtime smoke `38487647898`, Docker packaging `38487647913`, and validation-only multi-architecture `38487647952` all completed successfully on that exact head. No local test execution is claimed. These CI results do not indicate image publication or deployment.

## Current verification state — PR #34 merged (2026-10-14)

- PR #34 was squash-merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`.
- All required exact-head workflows passed: Python syntax #330 (run `38485830330`), Docker packaging/full unit tests #237 (run `38485830207`), container runtime smoke #47 (run `38485830231`), and validation-only multi-architecture #91 (run `38485830245`).
- Focused test coverage is in `tests/test_acquisition_routes.py`; route-only change, no intended UI contract change, so manual browser testing was not required. Local test execution is not claimed.
- No image publication, deployment, or production runtime verification. Keep publishing disabled until modularization is complete and separately authorized.

## Current verification state — PR #31 merged (2026-10-14)

- PR #31 was squash-merged at `87e5816c4273e720352931402a223f0b61ecbf27` from exact head `135b719bfecf9ad698862d41034d927083426f99`.
- Exact-head CI passed: Python syntax #318, container runtime smoke #35, Docker packaging/full unit tests #225, and validation-only multi-architecture #79. See `docs/PROJECT_STATUS.md` for workflow run IDs.
- Manual UI evidence remains tied to application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`: eight recorded checks passed, zero failures. Performance observation and distinct error/recovery remain deferred to the next UI-facing PR.
- Documentation handoff commits after the merge are recorded, but workflow lookup returned no PR-triggered runs for those documentation commit SHAs; their CI is not claimed.
- Image publication and deployment were not performed. Keep publishing paused pending modularization completion and separate authorization.

## Current verification state — PR #32/#33 merged; PR #31 documentation follow-up

- PR #32 and PR #33 are merged. Their exact-head checks passed, including syntax, full unittest discovery/Docker packaging, container runtime smoke, and validation-only multi-architecture build. See the top of docs/PROJECT_STATUS.md and PROJECT_LOG.md for exact commit/run references.
- PR #31's operator guide is reconciled against main `25cd40eca0f20824173d7aefce76b753ef57360c`. Head `3eb3ec6726e0bbe03ef0df9f3d5022796feb7a0c` passed Python syntax workflow #316, full unit tests/Docker packaging workflow #223, container runtime smoke workflow #33, and validation-only multi-architecture workflow #77. Docs-only follow-up `2993273b633b865219818789c47160b8e2429a6f` triggered new exact-head CI runs; these were still in progress at closeout, so wait for their conclusions before merge.
- Manual browser checks remain a gate for UI-facing changes after exact-head CI. The performance observation and distinct error/recovery scenario not recorded in the October 13 report are deferred to the next UI-facing PR. Do not repeat the full visual checklist solely because a non-UI PR changes SHA.
- GHCR publishing stays disabled until the modularization roadmap is complete and release is explicitly authorized.

## Discovery refresh coordination extraction — merged PR #30

- PR #30 was merged into `main` at `a12538e7f7ab2f3ec7417680d6127f5c3a1eaa5b`; final PR head was `f9256060d162ed92be0bbacc66a877c2675a5174`.
- Focused regression command: `python -m unittest tests.test_discovery_refresh -v`.
- Syntax check: `python -m py_compile navidrome_server.py discovery_refresh.py`.
- Full suite: `python -m unittest discover -s tests -v`.
- CI passed for code head `46444e3c24dc78008e3c13dfb441059e73279814` (Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156; Docker job included full unittest discovery and image build). A docs-only commit triggered Docker workflow #157; its terminal result was not confirmed at merge time. No local test run or live/UI verification is claimed.
- Refresh coordination tests cover personal payload parsing/write behavior, malformed JSON, non-blocking lock behavior, named-list success/counting, unknown-list handling, builder exceptions, and lock release.


# Test plan

Last updated: 2026-10-14

## Discovery store extraction — merged PR #29

- PR #29 was squash-merged to `main` at `001f3a7e76979d82adc62edd888d8490565b2ef3`. The final PR head `518505f6dd8e233bc6aaec4b90ec42b0669f70d5` passed Python syntax workflow #243 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507492)) and Docker packaging workflow #150 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507399)); the latter ran Python compilation, the full unit-test suite, and Docker image build.
- No workflow runs were returned for the squash merge commit at closeout. Do not infer merge-commit CI from PR-head CI. No local test execution or live/UI validation was performed.
- Focused commands for future changes:

```sh
python -m unittest tests.test_discovery_store -v
python -m py_compile navidrome_server.py discovery_store.py
python -m unittest discover -s tests -v
```

## Latest CI evidence — PR #28

- PR #28 final head `9ab8afeaed6562424b9212f2492d34f3ed9a69ee`: Python syntax workflow #232 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390630)); Docker packaging workflow #139 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390704)), including Python compilation, full unit-test discovery, and image build.
- PR #28 was squash-merged to `main` at `686fb393a178fe27f3806ecd5ce2138b026291cc`. No workflow runs were returned for the merge commit at closeout; CI evidence above is for the exact PR head, not the merge commit.
- No local test execution or live/manual runtime checks were performed during closeout.

## Source-switch orchestration extraction — PR #56 merged

- Moved the existing locked source-switch implementation into `acquisition_source_switch.py` with injected config, lifecycle, cleanup, HTTP, candidate-start, status, and persistence dependencies. `navidrome_server.py` retains the compatibility wrapper; the caller still owns dismissal/transition locking.
- Added direct-import tests for uncertain queue outcome (monitor the same peer, never queue another), cleanup refusal before queue, no fallback, failed fallback cleanup stopping the loop, and confirmed fallback persistence.
- PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety `38602255318`, Docker packaging/full unit suite/image build `38602255282`, runtime smoke `38602255326`, and validation-only multi-architecture build `38602255378` (publishing paused). Squash-merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- No live slskd interaction or production cleanup is claimed.

## Interrupted-import recovery domain extraction — PR #55 merged

- Moved `_discovery_reconcile_interrupted_import` into `acquisition_recovery.py` with injected state, path, matcher, persistence, clock, JSON, and move dependencies. The legacy MCP function remains a compatibility adapter.
- Added direct-import tests for exact completed-destination reconciliation, changed mount-device refusal, partial staging rollback to the source folder, wrong/incomplete destination refusal, and dismissed/non-importing state refusal.
- The direct tests assert no unintended status updates and preserve source/destination files on refusal. Docker packaging includes `acquisition_recovery.py`.
- PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety `38601516322`, Docker packaging/full unit suite/image build `38601516096`, runtime smoke `38601516565`, and validation-only multi-architecture build `38601516203` (publishing paused). Squash-merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- No production filesystem recovery or live service interaction is claimed.

## Acquisition cleanup domain extraction — PR #54 merged

- Extracted the existing fail-safe cleanup implementation into `acquisition_cleanup.py` with injected folder-name validation, slskd transfer lookup, and HTTP client dependencies. `navidrome_server.py` retains its existing MCP-compatible wrapper and delegates to the extracted function.
- Moved all seven dismissal cleanup cases out of the AST-based `tests/test_acquisition_safety.py` harness into directly imported `tests/test_acquisition_cleanup.py`: verified cleanup after transfers stop; unexpected-entry refusal; neighbor artwork/album preservation; traversal rejection; duplicate-folder refusal; symlink-target refusal; failed cancellation preservation.
- The direct tests use the canonical `acquisition_completion.safe_folder_name` helper. Docker packaging includes the new module.
- PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed syntax/acquisition safety `38600688719`, Docker packaging/full unit suite/image build `38600688787`, container runtime smoke `38600688814`, and validation-only multi-architecture build `38600688667` (publishing paused). Squash-merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- No live slskd request, production-folder deletion, image publication, deployment, or runtime verification is performed. HTTP 409 remains deferred because it was not reproduced.

## Acquisition dismissal neighbor-preservation regression — PR #53

- Final PR head `ef6ec7347f69c0be04331d7bd671d9f56f3c137d` passed all four required workflows: Python syntax/acquisition safety `38599666003`, Docker packaging/full unit suite `38599666001`, container runtime smoke `38599665955`, and validation-only multi-architecture image build `38599665933` (publishing paused).
- PR #53 was squash-merged at `a7c8dd469c76b340706ba65db8b4315aac60e62b`. No workflow runs were returned for the merge commit itself.
- The new regression proves successful cleanup preserves a sibling artwork file and a separate album folder. Existing cases continue to cover refusal for unrelated entries, traversal, duplicate folders, symlinks, and failed cancellation.
- Tests use the existing AST harness; migrate them to direct-import tests alongside a tested cleanup implementation extraction, preserving all assertions. The reported HTTP 409 remains deferred because it was not reproduced.
- No separate local test run, live slskd test, real production-folder deletion, publication, deployment, or production runtime verification is claimed.

## Automated baseline

Run from the repository root using the project's supported Python environment.

```sh
python -m py_compile navidrome_server.py app/main.py
python -m unittest discover -s tests -v
```

The Docker CI workflow also installs `requirements.txt`, compiles the Python modules, runs the unit tests, and builds the image. Check the actual GitHub Actions run; the existence of a workflow is not evidence that a given commit passed it.

## Required regression areas

### Discovery and recommendations

- Recommendation endpoint accepts valid counts and rejects out-of-range counts.
- Discovery lists return expected structure and safely handle empty/error responses.
- Owned albums are excluded from new-acquisition recommendations.
- Artist and album matching does not accept substring collisions (for example, an artist name embedded in a tribute act's name).
- Various Artists/compilation and non-album releases are excluded where required.
- New Releases use the agreed date window and library-artist eligibility rules.
- Deep Dive rows obey the one-album-per-artist-per-row constraint.
- Missing or unavailable external metadata does not break discovery.

### Acquisition and filesystem safety

- A slskd per-peer transfer lookup returning HTTP 404 is treated as an empty current transfer list; filesystem polling continues, while other HTTP errors remain visible as monitor errors.
- Regression-test both the 404 response and non-404 HTTP failures in `tests/test_slskd_transfer_lookup.py`.
- Completed-transfer folder diagnosis distinguishes unavailable download root, absent expected folder, incomplete/mismatched tracks, track-matching folders with a different basename, and ambiguous matches.
- A complete album is still selected only when both the strict track matcher and unique expected-folder-name check pass; diagnostic output must not authorize import by itself.
- Folder diagnostics are bounded and include only a small number of candidate folders and filename mismatches.

- Search matching handles punctuation, edition suffixes, and Unicode normalization.
- Candidates from different remote folders are not incorrectly merged.
- Incomplete/unsafe candidates are rejected before queue/import.
- Queueing the selected candidate passes the expected user, folder, and file list to slskd.
- Get does not navigate away; the button changes to the requested state and prevents duplicate requests.
- Every acquisition card has a dismiss control in each relevant state.
- Dismissal resolves the intended album folder and deletes only the files permitted by the requirement.
- Negative tests cover path traversal, symlink escape, ambiguous folders, empty/root paths, and unrelated files.
- API errors restore a usable UI state and show a clear message.

### Authentication and settings

- The slskd quality-priority list contains all six supported tiers exactly once and saves the displayed order.
- Existing four-tier settings append FLAC 16/44 and FLAC Hi-Res; existing five-tier settings append FLAC Hi-Res, without reordering prior choices.
- FLAC 16/44 and Hi-Res are classified from metadata or explicit resolution labels such as `[24-44.1]`; unverified FLAC remains accepted in the fallback tier.
- The Settings quality list can be reordered by drag-and-drop and by Move up/Move down controls; save/reload preserves the order.
- When candidate checks reject sources or queue attempts fail, acquisition status exposes bounded candidate diagnostics (folder, track counts, quality tiers, and eligibility reason).
- Explicit slskd queue rejection statuses 400/404/422 allow safe source failover; 401/403 stop as global credential/permission errors; timeouts and 5xx responses remain monitored as uncertain to prevent duplicate downloads.
- When no folder candidate is recognized, status includes a bounded sample of source paths and the album/artist match signals used by the matcher.
- Normalize slskd search results whether returned as a list or a `responses`/`items` wrapper; if search state reports peers but response payloads are temporarily absent, retry briefly before reporting no matches.
- If an exact slskd query returns no usable peer file payloads, retry a bounded broader-query sequence (30-second total budget); verify mocked zero-response-to-fallback behavior, query order, duplicate elimination, blank-input handling, shorter fallback timeouts, unchanged candidate matching, and card/API diagnostics showing attempted queries and separating reported counts from collected payloads.
- First-run setup creates the owner account.
- Invalid login is rejected; rate limiting and session expiry behave as designed.
- Restarting the container preserves authentication and application data.
- Secret values are not included in API responses or logs.
- Blank secret fields preserve existing secrets unless explicit clearing is supported.
- Settings validation rejects invalid values; service connection tests report failure clearly.

### Docker and deployment

- `docker compose config --quiet` passes against the actual deployment Compose file.
- Image builds successfully for the supported runtime and the intended architecture.
- Container starts as the intended non-root UID/GID.
- `/data` survives container recreation.
- Navidrome and slskd are reachable from the app container.
- Bind mounts point to the real music/download directories; permissions match the minimum required for the feature.
- GHCR pull succeeds on the deployment host with the intended visibility/authentication setup.
- Running UI smoke test passes on the actual host/port.

### Dismissed acquisition retry regression

- Dismiss an acquisition and confirm dismissal succeeds only after its source cleanup completes.
- Click Get again for that same album. Confirm the dismissed record is reset to a retry-requested state with no stale source candidate/settings, then transitions into a fresh search/acquisition card.
- Simulate a failed reactivation guard and confirm no new source search is started.
- Confirm albums already importing/imported and active downloads remain protected from duplicate acquisition requests.

## Manual UI smoke test

**When manual browser testing is required:** run this checklist after automated CI passes on the exact head of a UI-facing PR or release candidate. Documentation-only, API-only refactors with no UI contract changes, and infrastructure changes covered by a successful automated container runtime smoke test do not independently require a manual browser run. Record the exact application SHA for every manual run.

**Deferred checks:** the PR #31 report recorded eight items as passed on application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`, but did not separately record performance observation or a distinct error/recovery scenario. Do not mark those as passed retroactively; include both in the next UI-facing PR's manual run.

After the automated suite passes:

1. Log in and navigate between the main pages.
2. Load each discovery list; test empty and populated states.
3. Confirm artwork and release years do not shift or mislabel cards.
4. Open an album details popup; verify tracklist and external search links where available.
5. Click Get and confirm the requested state appears without navigation.
6. Check acquisition progress/status and confirm cards update correctly.
7. Test Dismiss only against a disposable known test folder; verify intended cleanup and preservation of neighboring files.
8. Change a service setting, reload the page, and confirm it persisted without exposing secrets.
9. Restart the container and confirm login/data remain intact.

## Evidence to record

For each release candidate, record:

- branch and full commit SHA;
- Python version and test commands;
- test result and any skipped tests;
- CI run URL/status;
- manual smoke-test environment and outcome;
- image tag and full SHA-256 digest;
- deployment date/host and rollback reference;
- unresolved failures.

Never claim a test passed unless it was run against the stated commit.


## M1 implementation note — acquisition completion/matching

The first extraction keeps `navidrome_server.py` compatibility wrappers while the implementation lives in `acquisition_completion.py`. `tests/test_acquisition_completion.py` must exercise the production helpers via direct imports. Retain the legacy lifecycle/import safety suite and ensure it uses the same imported matcher rather than a duplicate AST-extracted implementation. Required regression cases include Unicode NFC/casefold identity, Windows-style remote paths, strict positive sizes, conflicting duplicate basenames, collision-suffix uniqueness by size, symlink exclusion, incomplete folders, and ambiguous named folders. Also verify that multiple exact basename/size matches fail closed even when a unique collision-suffixed file is present; collision-suffix fallback is permitted only when there are zero exact matches.


## M2 — slskd search and quality module extraction

For changes touching `slskd_quality.py` or `slskd_search.py`, run the focused direct-import tests first:

```sh
python -m unittest discover -s tests -p 'test_slskd_search_modules.py' -v
python -m unittest discover -s tests -p 'test_acquisition_safety.py' -v
python -m py_compile navidrome_server.py slskd_quality.py slskd_search.py
python -m unittest discover -s tests -v
```

The new tests cover MP3/FLAC classification, user-configured tier ordering, bounded fallback query generation, slskd response-shape normalization, album-path/track identity matching, candidate track deduplication and ranking, and bounded diagnostics. The legacy acquisition-safety suite remains a compatibility guard because existing callers still use wrappers in `navidrome_server.py`. Confirm the Docker packaging workflow passes on the exact PR head before merge. No live slskd or UI behavior should be inferred from unit tests alone.


## M4 — discovery eligibility and recommendation scoring

- `discovery_recommendations.py` contains pure name/artist/release eligibility, genre-family classification, exploration scoring, and classic-list diversity rules.
- Run focused regression coverage with `python -m unittest tests.test_discovery_recommendations -v`, then syntax checks and the full unit suite below.
- Review score weights, jitter bounds, exact artist-credit matching, compilation/non-album exclusions, and the two-per-artist/eight-per-family caps when changing these helpers.
- Network calls, cache access, Navidrome inventory, metadata enrichment, and persistence remain in `navidrome_server.py`.

## M3 — acquisition import filesystem module

For changes touching `acquisition_import.py`, run the direct-import tests first:

```sh
python -m unittest tests.test_acquisition_import -v
python -m unittest tests.test_acquisition_safety -v
python -m py_compile acquisition_import.py navidrome_server.py
python -m unittest discover -s tests -v
```

The module owns staging/move/rollback mechanics only. Acquisition orchestration remains in `navidrome_server.py`; its compatibility wrapper injects the existing strict completion matcher. Preserve the existing checks for verified expected tracks, reserved manifest names, existing destinations (including broken symlinks), real destination parents, mount/device identity, rollback, and recovery manifests. Do not treat a successful unit suite as proof of a live import or deployment.


## Discovery list persistence extraction

For changes touching `discovery_store.py`, run the direct-import tests first:

```sh
python -m unittest tests.test_discovery_store -v
python -m py_compile navidrome_server.py discovery_store.py
python -m unittest discover -s tests -v
```

The store owns only SQLite persistence for cached discovery-list payloads. The server compatibility wrappers retain `_discovery_init()` so existing schema initialization and callers are unchanged. Cover missing rows, malformed JSON, Unicode payload round-trips, timestamp preservation, and per-list replacement/isolation. CI must pass on the exact PR head, including Docker packaging; unit tests do not establish live refresh/UI behavior.


## Acquisition API router extraction — PR #34

Focused regression command:

```sh
python -m unittest tests.test_acquisition_routes -v
python -m py_compile app/main.py app/api/acquisitions.py
python -m unittest discover -s tests -v
```

`tests/test_acquisition_routes.py` checks route/method preservation, acquire and queue payload mapping/defaults, invalid payloads, skip/dismiss status translation, streaming response headers, and sanitized upstream errors. PR #34 was squash-merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`. All four required workflows passed on that exact head: Python syntax #330 (run 38485830330), Docker packaging/full unit tests #237 (run 38485830207), runtime smoke #47 (run 38485830231), and validation-only multi-architecture #91 (run 38485830245). This route-only change is not expected to alter UI presentation, so manual browser testing was not required.


## Frontend asset extraction regression gates

For changes that move templates, stylesheets, or scripts out of `app/main.py`:

- Run `python -m unittest tests.test_auth_routes_integration -v` and the full `python -m unittest discover -s tests -v` suite.
- Confirm login and home responses reference their external CSS/JS assets and contain no inline `<style>` or inline `<script>` blocks.
- Confirm `/static/login.css`, `/static/login.js`, `/static/app.css`, `/static/app.js`, and `/assets/cassette.png` are reachable before first-run setup/login; verify protected application/API routes remain protected.
- Run syntax checks and all required Docker packaging/full-test, runtime-smoke, and validation-only multi-architecture workflows on the exact final PR head. Publishing remains disabled.
- After CI succeeds, perform the full manual browser checklist on that exact SHA, including the deferred performance observation and distinct error/recovery scenario. Record results; do not infer them from unit tests.


## Persisted acquisition source-skip orchestration — reconstructed PR #48

Run focused regression tests with `python -m unittest tests.test_acquisition_orchestration -v`, then the full `python -m unittest discover -s tests -v` suite and syntax checks. Direct tests must cover successful persistence for a downloading acquisition with eligible fallback candidates and rejection of missing, dismissed, non-downloading, and no-fallback states without mutation. Verify the MCP adapter still serializes the same JSON response shape, the transition remains under the shared lock, and the SQL update is conditional on `status='downloading'`. Run all four required exact-head workflows: Python syntax, Docker packaging/full unit suite, container runtime smoke, and validation-only multi-architecture image validation. Do not publish or deploy.


## Acquisition cleanup, recovery, and source-switch extractions — PRs #54–#56

- `tests/test_acquisition_cleanup.py` directly imports `acquisition_cleanup.py`; it covers successful cleanup of the identified album folder, refusal for unsafe/ambiguous targets and unexpected files, and preservation of neighboring content. PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed syntax/acquisition safety (run `38600688719`), Docker packaging/full unit suite/image build (`38600688787`), container runtime smoke (`38600688814`), and validation-only multi-architecture build (`38600688667`). Merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- `tests/test_acquisition_recovery.py` directly imports `acquisition_recovery.py`; preserve checks for dismissed/non-importing states, strict completion matching, mount/filesystem identity, exact destination, manifest validation, symlink refusal, and staged-file rollback. PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety (`38601516322`), Docker packaging/full unit suite/image build (`38601516096`), container runtime smoke (`38601516565`), and validation-only multi-architecture build (`38601516203`). Merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- `acquisition_source_switch.py` is exercised by direct-import regression tests for cleanup refusal as a hard stop, no-fallback handling, failed fallback cleanup, and successful fallback persistence. PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety (`38602255318`), Docker packaging/full unit suite/image build (`38602255282`), container runtime smoke (`38602255326`), and validation-only multi-architecture build (`38602255378`). Merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- For future changes to these modules, run the relevant focused direct-import tests, `python -m py_compile acquisition_cleanup.py acquisition_recovery.py acquisition_source_switch.py navidrome_server.py`, and `python -m unittest discover -s tests -v`, then all four required workflows on the exact final PR head. Keep the legacy adapters/MCP callers and Docker packaging in sync.
- These CI results do not establish live slskd behavior or production filesystem recovery/deletion. No separate local test run, production cleanup/recovery, image publication, deployment, or production runtime verification is claimed. The reported dismissal HTTP 409 remains deferred because it was not reproduced. GHCR publication remains paused until the roadmap is complete and the user explicitly authorizes release.


## Acquisition watcher lifecycle extraction

- Direct-import regression tests in `tests/test_acquisition_watcher.py` exercise dismissal and interrupted-import early exits, strict separation between transfer-completion evidence and verified-folder import, and passing only the folder returned by the existing completion matcher into the existing safe import coordinator.
- The legacy `_discovery_watch_and_import_album` name remains as an adapter. Watcher state, slskd access, folder matching, import coordination and status updates are injected; existing cleanup, source-switch and import modules remain the safety authorities.
- Required verification: focused watcher and acquisition safety tests, full `python -m unittest discover -s tests -v`, syntax check including `acquisition_watcher.py`, then all four exact-head CI workflows. Do not infer real slskd or production filesystem behavior from unit tests.


### Acquisition watcher extraction — PR #57

- First CI attempt failed one test assertion: status details are passed as the fourth positional argument, not keyword arguments. The test was corrected.
- Corrected head `6793c339464c9d573c02f5e7dc91d15b5f568348`: syntax/acquisition safety run `38604931720`, Docker packaging/full suite/build `38604931649`, container runtime smoke `38604931792`, and validation-only multi-architecture build `38604932002` all succeeded. Publishing remains paused.
- After the final documentation update, all four workflows passed on exact head 9f201e247c092ca74f805b8ca8a1cb6f872b3cba; PR #57 was subsequently squash-merged from tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. No separate local test run or live slskd/production filesystem verification is claimed.


- **Final documentation-updated PR head:** `9f201e247c092ca74f805b8ca8a1cb6f872b3cba` passed syntax/acquisition safety `38605193852`, Docker packaging/full suite/build `38605193845`, runtime smoke `38605193808`, and validation-only multi-architecture build `38605193820`. All four required workflows succeeded; image publishing remains paused.


## Acquisition state persistence extraction

- `tests/test_acquisition_state.py` directly imports the extracted SQLite state store and covers round-trip state, normalized identity, preservation of candidate/settings/quality fields on partial updates, invalid identity rejection, and conservative malformed-JSON decoding.
- Preserve the legacy transition lock, dismissed-state conditional behavior, secondary feedback projection, and compatibility adapters. These are not moved by this extraction.
- On corrected code head `29c5e6a460f1f61296680af7b1230fd5561496b4`, CI ran the full suite (`180` tests, passed), compile, container smoke, and validation-only multi-architecture build; all four required workflows passed (runs `116019140196`, `116019144533`, `116019141476`, `116019141889`, respectively; publishing paused). The initial attempt exposed only an incorrect test fixture expectation for JSON `null`; the fixture was corrected and no production behavior changed. Because this closeout updates documentation, rerun all four workflows on the new exact PR head before merge. No separate assistant-local test run is claimed.


## Acquisition state persistence extraction — PR #59

- `tests/test_acquisition_state.py` directly imports `acquisition_state.py` and covers persistence round-trip, normalized identity, metadata preservation on partial updates, invalid identity rejection, and malformed JSON decoding.
- For changes to this module, run focused `tests.test_acquisition_state`, syntax checks, the full unit suite, and all four required exact-head workflows (compile/acquisition safety, Docker packaging/full suite/build, container runtime smoke, validation-only multi-architecture).
- PR #59 exact head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed all four workflows: compile `116019930318`, test/build `116019925188`, smoke `116019924747`, multi-architecture validation `116019926066`. Merge commit: `730ae16e613f3962c488f87c8de54034db7463dd`.
- Tests do not establish live slskd behavior, production filesystem operations, publication, deployment, or production runtime health.


## Acquisition transition guard

For changes to `acquisition_orchestration.py`, run:

```sh
python -m unittest tests.test_acquisition_orchestration -v
python -m py_compile acquisition_orchestration.py navidrome_server.py
python -m unittest discover -s tests -v
```

The source-switch guard tests must prove the dismissal check and switch callback execute within one transition-lock critical section, dismissed acquisitions never invoke the callback, and callback return values/exceptions pass through unchanged. Keep the shared lock, conditional persistence writes, source cleanup, and MCP adapter contract unchanged. All four required CI workflows must pass on the exact final PR head; this does not establish live slskd or production filesystem behavior.


## Acquisition transition guard — PR #61 closeout

- Exact tested PR head: `aa554ff2be2a19e215538ed2e699b8036764dca1`; squash merge `73172847535d3683facfbe559706c26a8637a3d4`.
- All four required exact-head workflows passed: Python syntax/acquisition safety `38617537652`, Docker packaging/full unit suite/build `38617538490`, container runtime smoke `38617537978`, and validation-only multi-architecture image validation `38617538229` (publishing paused).
- Direct-import regressions cover shared-lock critical-section ordering, no source switch after dismissal, callback result preservation, and exception propagation. No separate local test run or live slskd/production filesystem behavior is claimed.


## Login-page design-system alignment — PR #66 (merged 2026-10-14)

- Change is limited to `static/login.css`; no template, JavaScript, auth/API behavior, or data model changes.
- Exact tested PR head: `d0b13b7411b9b300b78b24a8944348b7e57d4b65`; squash merge: `717b1ad08e5de54e2dd8c11c2734976d75ce2e5f`.
- All four required exact-head workflows passed: syntax `38639793800`, Docker packaging/full unit suite `38639793772`, container runtime smoke `38639793518`, and validation-only multi-architecture `38639793667` (publishing paused). Reported tests: 15 focused auth/integration tests and 185 full-suite tests with one pre-existing skip.
- Manual report/screenshots were published in PR #66 comments. Reported pass: desktop 1280×900, narrow 375×720, failed sign-in message/layout/button recovery, and login assets/auth-status network responses. The report marks keyboard-focus modality and first-run setup variant as skipped; do not treat those two as verified by the report.
- Future UI PRs should retain desktop/narrow responsive checks, keyboard Tab confirmation for focus-visible styling, setup and sign-in variants where applicable, status/error recovery, and the outstanding performance observation on the next UI-facing change.


## Acquisition import source-root race hardening — PR #103

- The import module pins source and destination-parent directory descriptors without following symlinks, then uses descriptor-relative staging/moves/rollback to prevent a source-root path swap from redirecting file movement.
- Regression coverage includes source-root symlink replacement after matching, collision-suffixed matching, cross-filesystem fallback, and rollback. Preserve existing no-overwrite destination checks, verified track matching, mount/device checks, and recovery-manifest behavior.
- PR #103 final tested head `9de78c268af1b640a2a08afecb25a22502322a85` passed all four required workflows: syntax `38726626891`, Docker packaging/full suite/build `38726626846`, runtime smoke `38726626956`, and validation-only multi-architecture validation `38726626910`. Squash merge: `cf40df35a76d669421dcddbafd21ea22652bd0b1`. Publishing remains paused.
- No separate assistant-local test run or live slskd/production filesystem verification is claimed.

## 2026-10-15 — Settings router service injection in progress

- Current implementation branch: `refactor/settings-router-service-injection`, based on `main` at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` (PR #108 merge).
- `app/api/settings.py` now uses the shared lazy `get_librarian` dependency for all twelve settings endpoints instead of importing `navidrome_server` at module import time. Existing settings functions remain the service implementation; payload mapping, defaults, response parsing, validation status codes, and sanitized 502 errors are intentionally unchanged.
- `tests/test_settings_routes.py` now supplies fake services directly and checks route/method contracts, dependency wiring, payload mapping, slskd defaults/path trimming, client validation errors, and sanitized connection failures.
- Verification state at documentation update: no local tests run; CI not yet verified for the final branch head. No image publication, deployment, or production runtime verification. Preserve the MCP adapters and legacy persistence ownership.


## 2026-10-15 — PR #109 implementation CI result

- Implementation commit `5a5a78aed24916aeddf01b306300850b95a56aa7` passed all four required workflows: Python syntax (`38734406727`), Docker packaging/full suite (`38734407126`), container runtime smoke (`38734406616`), and validation-only multi-architecture image validation (`38734407120`). The validation workflow's multi-architecture build step and overall job both completed successfully.
- This is evidence for the implementation commit only. Documentation closeout commits are being added afterward; the exact final PR head must be rechecked before merge. No local test run, image publication, deployment, or production runtime verification is claimed.


## 2026-10-15 — PR #109 merged: settings router service injection

- PR #109: https://github.com/abucalip/navi-librarian/pull/109; exact tested head `a6c919a4d6c45f98394ee683095888f27513f1d6`; squash merge / current main at closeout `9a2aaea98cff38a1ad3da130d0958f945bec9673`.
- The settings router now uses the shared lazy `get_librarian` dependency for all twelve endpoints. Route/method contracts, service calls, payload mapping, quality defaults, optional path trimming, validation responses, and sanitized connection errors are preserved.
- All four required workflows passed on the exact final PR head: Python syntax `38734569394`, Docker packaging/full suite `38734569197`, container runtime smoke `38734569168`, and validation-only multi-architecture image validation `38734569302`. Image publishing remains paused.
- No separate local test run, publication, deployment, or production runtime verification is claimed.

## Dashboard and health route injection (2026-10-15)

- Direct-import suite: `tests/test_dashboard_routes.py`.
- Verify the two route/method pairs; injected `api_call("ping")`; sanitized HTTP 503 on Navidrome failure; dashboard's three list reads at count 150; category-balanced picks; case-insensitive artist/album deduplication; album-candidate filtering; and HTTP 400 for out-of-range count.
- Required: focused route tests, full unit suite, syntax check, container runtime smoke, and validation-only multi-architecture workflow on the exact final PR head. No separate local test run is claimed unless performed.
- The dashboard route extraction changes no UI assets or user-facing route contracts; manual browser testing is not required by the current API-only gate.

## Acquisition lifecycle AST audit disposition (2026-10-15)

The remaining AST-based lifecycle tests in `tests/test_acquisition_safety.py` exercise the legacy MCP adapter's integration with the extracted request coordinator. Direct-import coordinator tests do not independently validate that adapter's production locks, active sets, saved-job reader, reactivation callback, and watcher-start callback are wired correctly. Keep these tests until an equivalent adapter seam and regression coverage exist. Do not remove tests solely to eliminate AST usage.


## Dashboard and health router injection — PR #110

- Exact tested head: `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e`; squash merge `b4015b8619f3c0db169722c347f72612996b9a1c`.
- All four required workflows passed on that exact head: syntax `38735208616`, Docker packaging/full unit suite/build `38735208619`, runtime smoke `38735208830`, validation-only multi-architecture image validation `38735208682`.
- Direct-import regressions cover route inventory, injected Navidrome ping success and sanitized failure, dashboard category balance, three list reads at count 150, case-insensitive deduplication, candidate filtering, and invalid count rejection. The first CI run exposed a wrong expected pool size; the test was corrected before the passing final head.
- No separate local test execution, publication, deployment, or production runtime verification is claimed.



## Lazy auth service dependency regression — PR #112 verified

- Authentication integration tests inject a fake librarian service rather than patching a module-level `app.main.librarian` binding.
- A subprocess test asserts that importing `app.main` does not import `navidrome_server.py`. Existing setup, duplicate setup refusal, credential validation, login failure/success, rate limiting, logout cookie clearing, session reuse/tampering, HTTPS cookie policy, public assets, and protected page/API behavior remain covered.
- Exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed the required workflows: syntax/acquisition safety `38737672741`, Docker packaging/full unit suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture validation `38737672689`.
- PR #112 was squash-merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No separate local test execution, image publication, deployment, or production runtime verification.


## 2026-10-15 — PR #118: discovery eligibility tests use direct imports

- PR #118 moves the duplicate album-eligibility, exact artist-credit, and Various Artists regression checks out of the AST harness in `tests/test_acquisition_safety.py`; their existing direct-import coverage in `tests/test_discovery_recommendations.py` remains authoritative.
- The direct-import suite now retains the removed edge cases: live/remix/EP/compilation rejection, exact artist-credit false matches and empty credits, plus all five Various Artists aliases. The legacy AST harness now focuses on orchestration/lifecycle paths that still require the monolithic adapter's shared state and stubbed I/O. No runtime code or MCP behavior changed.
- Branch: `test/migrate-discovery-eligibility-direct-import`. Code/test head `873f47328de0808c8d18e034d5a7d04e39a083f2` passed all four required workflows: syntax `38745139119`; Docker packaging/full suite/build `38745139114` (238 tests passed); runtime smoke `38745139370`; validation-only multi-architecture image validation `38745139332`. Final PR head `4db6654678f9ce091caf43b650c04039c15dd6ef` also passed all four: syntax `38745425843`, Docker packaging/full suite/build `38745426466`, runtime smoke `38745425909`, and validation-only multi-architecture image validation `38745426093`. PR #118 merged to `main` at `9b1ba91923321a835e8bd3a210dd6aaf01caefc2`. No local test run, image publication, or deployment is claimed.


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


## Discovery refresh count validation

- For `POST /api/discovery/{list_name}/refresh`, accept an omitted count as the existing default of 20 and accept only JSON integers from 1 through 20.
- Reject strings (including numeric strings), floats, booleans, null, arrays, objects, and out-of-range integers with HTTP 400 before invoking the service.
- Run `python -m unittest tests.test_discovery_routes -v`, the full unit suite, syntax checks, and all four required workflows on the exact final PR head. No local test execution should be claimed unless actually run.


## Discovery refresh count validation — exact-head gate

- Implementation head `859bf10b1bbaececd2045596287c7680bb66d514` passed all four workflows: syntax `38762625902`, Docker packaging/full unit suite/build `38762625612`, runtime smoke `38762625878`, and validation-only multi-architecture validation `38762625568`.
- Documentation closeout changes require all four workflows to pass again on the final PR head before merge.


## 2026-10-15 — PR #129 verification and merge

- PR #129 merged at `b3db4d1d3ac3367a306435e0e3e50e7e3286ce22` from final tested head `d6f57b95f1cd77f58d1636f471a8f80bc9776f61`.
- All four required exact-head workflows passed: syntax `38762802954`, Docker packaging/full unit suite/build `38762802863`, runtime smoke `38762803101`, and validation-only multi-architecture image validation `38762803211`.
- No separate local tests, publication, deployment, or production runtime verification are claimed.


## 2026-10-15 — PR #132 navigation indicator verification

- Exact tested PR head: `b4982260a4e5697ee02766f47d35f7182303387a`; merged by squash at `44b03d6e6293e1a1ba34803104f52c4e443d245b`.
- All four required workflows passed on the tested head: Docker packaging `38766740766`, container runtime smoke `38766741159`, Python syntax `38766741253`, and validation-only Docker image validation `38766741247`.
- Manual browser checklist passed 8/8 on the exact tested head. Report: https://github.com/abucalip/navi-librarian/pull/132#issuecomment-6196780079.
- Headless checks recorded in the PR body covered indicator alignment, transform-only animation, one `aria-current`, scoped filter, mobile layout, reduced motion, keyboard reachability, all eight page headings, viewport overflow, and browser/page errors. No separate local test run, image publication, deployment, or production runtime verification is claimed.


## Settings connection service extraction — PR preparation

- Direct-import tests cover Navidrome ping success and ValueError mapping, Last.fm missing-key and authentication-failure handling without leaking the configured key, and ListenBrainz 404 profile handling.
- Run `python -m unittest tests.test_service_settings -v`, the full `python -m unittest discover -s tests -v` suite, syntax/acquisition safety, Docker packaging/full suite/build, container runtime smoke, and validation-only multi-architecture validation on the exact final PR head. Do not claim tests passed unless CI evidence exists for that SHA; publishing remains paused.


## PR #140 — settings connection extraction (2026-10-15)

- Exact PR head `cacdbc809f35040f0cc1bc70a39251ff80b7315e`: all required CI workflows passed — Python syntax `38784634643`; Docker packaging/full unit suite/build `38784634599`; container runtime smoke `38784635107`; validation-only multi-architecture image validation `38784634797`.
- PR #140 merged as `aabd7d1347d8e4c363d8b97bb6c106310f1135bb`. These results are CI evidence only; no separate local test run or production runtime verification is claimed.


## 2026-10-15 — PR #145 UI verification

- PR #145 tested head `421d1d2860945548aa01677847ce0953b7c9f263` passed the manual browser checklist 8/8 with zero failures; report: https://github.com/abucalip/navi-librarian/pull/145#issuecomment-6200647429.
- The report covers app startup/setup, dashboard/artwork, discovery, navigation/modal, settings, Get/request, acquisition cards, and unexpected browser/server errors. It is tied to the exact PR head.
- The report does not claim real screen-reader testing; isolated artwork checks used a placeholder. Four required CI workflows passed on that exact head: syntax `38794301415`, runtime smoke `38794301446`, Docker packaging `38794301460`, and validation-only image validation `38794301405`. Publishing remains paused.


## Data-directory resolution extraction — PR verification required

Run `python -m unittest tests.test_data_directory -v` and `python -m unittest discover -s tests -v`. The direct-import regressions verify configured-path home expansion, empty-value fallback, and source-directory fallback. Also verify Python syntax, Docker packaging/full suite/build, isolated container runtime smoke, and validation-only multi-architecture build on the exact final PR head. Confirm the Docker image contains `data_directory.py`. Preserve `navidrome_server.DATA_DIR`, directory creation, configured relative-path semantics, and legacy persistence ownership. Do not claim tests passed until actual CI results are observed.


## Completed — data-directory resolution extraction (PR #152)

- Added direct-import regression coverage for configured path home expansion, empty configuration fallback, and resolved source-directory fallback in `tests/test_data_directory.py`.
- Exact PR head `756ef13f6946299e2eacccbf5f9a55ebaf092aae` passed all four required workflows: Python syntax `38807325467`, Docker packaging/full unit suite/build `38807325564`, container runtime smoke `38807325555`, and validation-only multi-architecture image validation `38807325557`.
- PR #152 merged by squash at `567409bb90f240667575a3730976e4c52676bc02`. No separate local test run, image publication, deployment, or production runtime verification is claimed.


## Subsonic collection normalization extraction — pending verification

Run `python -m unittest tests.test_navidrome_client -v` and the full `python -m unittest discover -s tests -v` suite. The direct-import regression must cover `None`, a scalar value, an empty list, and a multi-item list, while the legacy `navidrome_server.items()` adapter remains compatible. Verify Python syntax/acquisition safety, Docker packaging/full suite/build, isolated container runtime smoke, and validation-only multi-architecture build on the exact final PR head. No results are claimed until the workflows complete.


## Subsonic collection normalization extraction — completed (PR #153)

PR #153 merged at `b7d8ec989e2a3d398b2ca4d14a30c59ae60543cc` from exact tested head `c834383b7484f3c149679d62812f1c81f6133625`. Direct-import regression cases cover `None`, scalar, empty-list, and populated-list values. All four required exact-head CI workflows passed: Python syntax check, Docker packaging validation/full suite/build, container runtime smoke, and validation-only multi-architecture image validation. No separate local test execution, image publication, deployment, or production runtime verification is claimed.


## Verification audit — highest-priority gap: acquisition UI request/dismiss regression

Audit baseline: GitHub main `678bfa001181d53190004d1c437b1344225082cf` (2026-10-15). Requirements ACQ-01, ACQ-02, and ACQ-03 still call for regression verification. The repository currently has no dedicated automated front-end test files, so browser evidence alone does not protect these transitions from later regressions.

Before routine modularization, add focused regression coverage for the Get/request and acquisition-card Dismiss lifecycle. Keep UI state tests separate from filesystem safety tests; do not invoke destructive cleanup against production paths.

### Acceptance criteria

1. **No navigation / one request (ACQ-01):** clicking Get does not change the active discovery page or route and issues exactly one acquisition request for that click.
2. **Pending and success state (ACQ-02):** while the request is pending, the control visibly uses the red `requested` state and prevents duplicate submissions. On success, the state remains requested and duplicate clicks cannot create another request.
3. **Failure recovery (ACQ-02):** on a failed or rejected request, the UI shows a useful error, restores a usable/retryable control, and does not falsely display a successful requested state.
4. **Persistent Dismiss control (ACQ-03):** every acquisition card exposes Dismiss in each supported lifecycle state (including downloading, completed, failed/stalled), including after the acquisition view is reloaded.
5. **Dismiss success/failure:** after a successful server response, the corresponding card is removed; when the server refuses or errors, the card is not silently removed and the user receives a useful failure indication.
6. **Safety boundary (ACQ-04/ACQ-06):** UI tests mock the API and never delete real files. The existing backend cleanup tests must continue to prove configured-root/path validation and preservation of unrelated files; cleanup failure must remain conservative.
7. **Verification evidence:** run focused automated regressions and the full `python -m unittest discover -s tests -v` suite plus all four required exact-final-head workflows. Because this is UI-facing, complete the documented manual browser checklist against that same final PR-head SHA after CI passes. Record skips explicitly; do not claim screen-reader verification unless performed.

### Audit disposition

This is the selected next work item. The dismissal HTTP 409 root-cause investigation remains deferred unless the user reports recurrence; this acceptance gate does not claim that issue is fixed. Publishing/deployment remain separate and paused.


## Last.fm top album extraction — completed (PR #175, 2026-10-16)

Direct-import regression coverage verifies scalar and list API payloads, empty-title filtering, normalized metadata, request parameters/limit/timeout/cache TTL, cache hits, missing payloads, and compatibility-adapter album eligibility filtering. The exact final PR head `6b5e32b1144e9f3517247110ea4383b287ce33f4` passed all four required workflows: Python syntax check (38829855110), Docker packaging validation including the full unit suite/build (38829855077), container runtime smoke test (38829855100), and validation-only multi-architecture image validation (38829855093). PR #175 was squash-merged at `f922631e0393063bde02b1e0bd93d30b2d38bd2a`. No separate assistant-side local test execution, image publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Extraction regression coverage: PRs #193 and #195

- PR #193 direct-import tests in `tests/test_musicbrainz_album_year.py` cover exact title/artist-credit matching, earliest valid year selection, missing input, and negative-cache reuse. Tested head `2b426587e6cb4dc011c85099021041d9f9450744`; all four required workflows passed: syntax/acquisition safety `38881961573`, Docker/full suite/build `38881961574`, runtime smoke `38881961553`, validation-only multi-architecture `38881961580`.
- PR #195 direct-import tests in `tests/test_acquisition_candidate_queue.py` cover list and filename validation, normalized sizes, optional quality-summary fallback, and malformed-size exception behavior. Tested head `f60d682b2ebcd94ecfbcfd0b4beb77c628643fc5`; all four required workflows passed: syntax/acquisition safety `38882195745`, Docker/full suite/build `38882195774`, runtime smoke `38882195700`, validation-only multi-architecture `38882195820`.
- These are GitHub CI results; no separate assistant-side local test execution is claimed. No real slskd operation, destructive filesystem test, publication, deployment, or production runtime verification occurred.


## 2026-10-16 — Navidrome response-shaping extraction verification (PRs #196 and #198)

- PR #196 exact head 4b501c64c82a69af1805a7f6195b4fc15ef0c836: syntax/acquisition-safety workflow 1088 passed; Docker packaging/full unit suite/build 995 passed; container runtime smoke 804 passed; validation-only multi-architecture image validation 848 passed.
- PR #198 exact head a718780edcb85eb8f4453e44a2d5a4925a512314: syntax/acquisition-safety workflow 1090 passed; Docker packaging/full unit suite/build 997 passed; container runtime smoke 806 passed; validation-only multi-architecture image validation 850 passed.
- Direct-import regressions were added to tests/test_navidrome_client.py for search categories/output fields and album details with scalar tracks/missing fields. CI's packaging workflow ran the full unit suite for both exact heads. Assistant-side local test commands were not run.
- Backend-only changes; no manual UI checklist required. No live Navidrome integration test, publication, deployment, or production runtime verification is claimed. Publishing remains paused.


## 2026-10-16 — Acquisition progress snapshot extraction completed (PR #199)

- PR #199 squash-merged at a18889b7aa45dd8ef0a9e99a12236cedf5ed5a41 from exact tested head f7157cb28d5e753a97bb9c24eea209b767d74066.
- acquisition_progress_snapshots.py now owns the per-process, per-acquisition byte-snapshot map and lock. navidrome_server.py retains live slskd polling and compatibility behavior; the manager delegates speed math to slskd_transfers.estimate_transfer_speed.
- Direct-import regressions cover first/next samples, identity isolation, and retaining the current sample if the estimator raises. All four exact-head workflows passed: syntax/acquisition safety run 1096; Docker packaging/full suite/build run 1003; runtime smoke run 812; validation-only multi-architecture run 856.
- Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Acquisition search diagnostics extraction completed (PR #200)

- PR #200 squash-merged at 9b3cf481a46282d2f980709091d57aea36144029 from exact tested head b74f6a3f4f8290d6e8d7123399185e9692dd053c.
- acquisition_search_diagnostics.py now owns the bounded candidate diagnostic projection, recognized audio-file count, and no-match explanation. Search execution, path-match diagnostics, persistence, queueing, and JSON/API serialization remain in navidrome_server.py.
- The first CI attempt exposed a compatibility issue in the AST-based acquisition safety test harness: its extracted function namespace did not include a module-level helper alias. The import was moved into the function, preserving production behavior and allowing the legacy test harness to execute it. The exact final head passed all four workflows: syntax/acquisition safety run 1099; Docker packaging/full suite/build run 1006; runtime smoke run 815; validation-only multi-architecture run 859.
- Direct-import tests cover diagnostic field projection and 10-item cap, copied quality summaries, recognized audio extensions, and no-match message/query ordering. Assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed.


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

## 2026-10-16 — Personal recommendation allocation contract (pre-extraction)

- Added direct-import contract tests in `tests/test_discovery_allocation_contract.py` for candidate identity/category/score/ownership validation; immutable request policy mappings; unique candidate IDs; requested-count, category-target and 60-check bounds; selected-vs-review result separation; diagnostics mapping immutability; and result/decision invariants.
- These tests validate the proposed interface only. They do not exercise the existing shortlist-selection loops or prove allocation policy equivalence. Those policy regressions are acceptance criteria for a later, separate allocator extraction: style reservations, category quotas, duplicate/artist caps, exact-owned vs title-conflict behavior, family-cap relaxation, unclassified/final fallback ordering, diagnostics, and check-cap behavior.
- Assistant-side execution and GitHub Actions exact-head results: pending.

## 2026-10-16 — Personal recommendation allocation contract verification (PR #221)

- Exact tested PR head: `9d17a0ef32782db35b19b5226d3b8c052f8775d6`; merged at `820556799fa9d3ec663e5117b36c68084281b20a`.
- Direct-import contract tests cover candidate identity/category/score/ownership validation; immutable request policy mappings; unique candidate IDs; requested-count, category-target and 60-check bounds; selected-vs-review separation; immutable diagnostic mappings; and result/decision invariants.
- All four exact-head workflows passed: syntax `38916419736`, Docker packaging/full unit suite/build `38916419709`, runtime smoke `38916419958`, and validation-only multi-architecture image validation `38916419701` (non-publishing). Assistant-side local test commands were not run independently.
- These tests validate the interface model only, not shortlist-selection semantics. A future allocator extraction must add policy regressions for regional/style reservations, category quotas, duplicate/per-artist limits, exact-owned vs title-conflict behavior, family-cap relaxation, unclassified/final fallback ordering, diagnostics, and check-cap behavior.



## New Releases date-window policy extraction — PR #237 merged

- Added direct-import regression coverage for the exact 730-day cutoff, earliest query year/current year, and leap-day arithmetic in `tests/test_discovery_new_releases.py`.
- All four exact-head CI workflows passed on PR head `8d42c9f5f320fd7b4c0653fa09da8eda12f03f78`: syntax run `38938867862`, Docker packaging/full unit suite/build run `38938867879`, container runtime smoke run `38938867737`, and validation-only multi-architecture image validation run `38938867550` (non-publishing).
- Assistant-side local test commands were not run independently. No publishing, deployment, or production runtime verification is claimed.


## Authentication configuration predicate extraction (PR #239 merged)

Focused regression command: `python -m unittest tests.test_auth_configuration -v`. Coverage includes a complete configuration, each missing/empty required field, absent/partial settings, and preservation of the existing truthiness behavior. The Docker packaging workflow (including the full unit suite) and all four required workflows passed on the final tested PR head: syntax `38940305016`, Docker/full suite/build `38940304930`, runtime smoke `38940304907`, and validation-only multi-architecture `38940305045`. Assistant-side local test commands were not run.


## Auth-secret provider extraction (PR #240 merged)

Focused command: `python -m unittest tests.test_auth_secret -v`. Direct-import tests cover lazy loading, successful caching, retry after exceptions or `None`, and concurrent first access. On exact final PR head `e3542c6a8fa3b2fc3ddf07a0268563ae5946064a`, all four workflows passed: syntax/acquisition safety `38941505550`, Docker packaging/full unit suite/build `38941505440`, container runtime smoke `38941505508`, and validation-only multi-architecture image validation `38941505516`. An initial run exposed a legacy integration-test dependency on `app.main._AUTH_SECRET`; the compatibility seam was restored before final verification. Assistant-side local test commands were not run. Image publication remains paused.


## Auth settings reader extraction — verification pending

Run `python -m unittest tests.test_auth_settings tests.test_auth_configuration tests.test_auth_secret -v`, then `python -m unittest discover -s tests -v` and Python syntax checks. Verify all four required workflows on the exact final PR head: syntax/acquisition safety, Docker packaging/full suite/build, container runtime smoke, and validation-only multi-architecture validation (`push: false`). Confirm auth setup/login/session behavior remains unchanged; do not claim browser or runtime verification unless performed.



---

# Legacy snapshot: `docs/ARCHITECTURE.md`

## New Releases global candidate merge — extracted (PR #234 merged)

`discovery_new_releases.merge_release_candidates(existing, incoming)` owns pure cross-artist candidate merging: newest release wins per identity; existing candidates win equal-date ties; inputs are not mutated. Provider/cache/rate limiting, per-artist eligibility, final sorting, and response assembly remain in the server adapter. Direct-import regression tests cover winner precedence, ties, non-mutation, empty and missing-date inputs. PR #234 merged at `c44ea572354b4714e5e2577f5eb21b091be97cc8` from tested head `56bb5b6835d03860124f2dbdff4dbb13a813d5c8`; all four required workflows passed on that exact head. No local tests or production verification claimed.

## New Releases global candidate merge — extraction in progress (PR #234)

`discovery_new_releases.merge_release_candidates(existing, incoming)` is a pure merge policy: preserve the newest candidate per identity and retain the existing candidate on equal dates. The server continues provider access, cache/rate limiting, per-artist filtering, final sorting, and response assembly. Direct-import tests cover newest winner, tie stability, input non-mutation, and empty/missing-date inputs. Exact-head CI pending.

## Classics candidate collection — extracted (PR #232 merged)

`discovery_classics_candidates.collect_classic_candidates()` owns candidate gathering and duplicate resolution; the server retains provider/cache access, inventory acquisition, and downstream scoring/enrichment/diversity/response assembly. PR #232 merged at `451944c9056eeb50ec7d8b1744bbf435d653b70b`. The four workflow runs inspected reported success, but their exact head-SHA association was not independently confirmed in the available connector result.

## New Releases library qualification — extraction in progress

The helper `discovery_new_releases.prepare_new_release_library_scope(artists, albums, ...)` owns normalized owned-album identities and pure full-album artist qualification/order. The adapter retains MusicBrainz/cache/rate limiting, date-window policy, 120-artist cap, and global candidate merge. Direct-import regression tests are added. PR #233 is open on tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`. All four required workflows passed on that head: Python syntax/acquisition safety run 38934044235, Docker packaging/full unit suite/build run 38934044270, container runtime smoke run 38934044253, and validation-only multi-architecture validation run 38934044237. Assistant-side local tests were not run. Merge remains pending; publishing/deployment/runtime verification remain paused/unclaimed.
## New Releases candidate selection — extracted (PR #205)

`discovery_new_releases.select_artist_release_candidates()` owns pure per-artist release-group eligibility, candidate shaping, exact-credit/Various Artists filtering, owned-album exclusion, and duplicate-date precedence. `_build_new_releases_list()` retains inventory, MusicBrainz requests, caching, rate limiting, lookup error reporting, and global merge. PR #205 merged at `32b39be400ec046e8310a87260346b1959141609` from exact tested head `079d355e972ea39d792c1dfa6fca6eab902800e3`; all four required exact-head workflows passed (syntax 1111, Docker/full suite/build 1018, runtime smoke 827, validation-only multi-architecture 871).

## Artist Deep Dives ranking and diversity — extracted (PR #207)

`discovery_recommendations.rank_and_diversify_deep_dive_candidates()` owns pure candidate scoring, exploration penalties/jitter, album eligibility filtering, ranking, and the existing two-pass artist/anchor/genre diversity policy. The server retains provider/cache access, genre enrichment, MusicBrainz year lookups, and response assembly. PR #207 merged at `a5b0d865060c3d069a865be7a1cb43c1a072ae91` from exact tested head `20e565582579f4097eed3803748c87bb3d932a98`; all four required exact-head workflows passed (syntax 1114, Docker/full suite/build 1021, runtime smoke 830, validation-only multi-architecture 874).

## Library overview payload shaping — extracted (PR #202)

`navidrome_client.library_overview_payload(artists, albums)` owns pure projection of normalized Navidrome artist/album rows into the existing library-overview payload. `navidrome_server.library_overview()` retains API calls, Subsonic collection normalization, JSON serialization, and the MCP-facing interface. PR #202 merged at `7a95364a31f360bb20dd8d2919a9bfea93ec893c` from tested head `6903f40578f40fec08f1efde92d6577fcaeeced0`; all four required exact-head workflows passed (syntax 1104, Docker/full suite/build 1011, runtime smoke 820, validation-only multi-architecture 864).

## Server source preview redaction — extracted (PR #203)

`server_source_redaction.redact_assignment()` owns the pure, case-insensitive sensitive-assignment-name redaction used by the read-only `get_server_source()` MCP tool. The server retains source-path selection, range and 250-line validation, line numbering, and JSON serialization. The helper is included in Docker packaging; direct-import tests cover redaction and unchanged non-sensitive lines. PR #203 merged at `89e639394122aebe29bfb8602a1135722ea28bbe` from tested head `14019b8beeca9b71fbb8167117dafea3f60c74ea`; all four required workflows passed (syntax 1106, Docker/full suite/build 1013, runtime smoke 822, validation-only multi-architecture 866). No source secrets were used or exposed by testing.

## Artist-biography resolution — extracted (PR #190)

`app/services/artist_bio.py` owns pure matching after provider retrieval: it filters/ranks music-related Wikidata entities, accepts a Wikipedia extract only when its `wikibase_item` matches a music entity, avoids disambiguation-page extracts, and falls back to a music-related description. `app/api/metadata.py` retains external requests, concurrent retrieval, cache lifetime, input validation, and response payload. PR #190 merged at `b829fa953d979563a8ace6e5529eace8cb80ac43` from exact tested head `6c04d8a67944568a3e2b280deafb4eb2c66c2391`; all four required exact-head workflows passed (syntax 1059, Docker/full suite/build 966, runtime smoke 775, validation-only multi-architecture 819). No publication or deployment is claimed.
## Dashboard-pick service — extracted (PR #189)

`app/services/dashboard.py` owns the dashboard's three-lane candidate assembly, album eligibility callback, case-insensitive artist/album deduplication, balanced per-category selection, and random fill. `app/api/dashboard.py` retains HTTP count validation, dependency injection, the response contract, and the route-level service adapter. List reads, eligibility, and shuffle are injected; the module does not initialize FastAPI, Navidrome, persistence, or MCP. PR #189 merged at `f5f355f8bdc0599bb240933e248177c7b0517ff5` from exact tested head `d28aaa33f7096ba764232d6bd435cc68d5d85f98`; all four required exact-head workflows passed (syntax 1052, Docker/full suite/build 959, runtime smoke 768, validation-only multi-architecture 812). No publication or deployment is claimed.

## slskd connectivity probe — extraction in progress (PR #187)

`slskd_client.test_connection(config_reader, http_get=...)` owns the connection probe request and the established JSON status mapping. `navidrome_server.discovery_test_slskd_connection()` remains the compatibility adapter and supplies the existing configuration reader. The API-key header is used only for the outbound request and is not returned in responses. Direct-import regressions and Docker packaging are added. Exact-head CI and merge are pending; no live slskd call was made.

## slskd live progress calculations — extracted (PRs #182–#183)

`slskd_transfers.summarize_transfer_progress()` owns pure aggregation of matched expected/tracked records into completed-track count, total/transferred bytes, and actual-counter snapshots. Completed states may infer a file's transferred bytes for display totals, but those inferred bytes are deliberately excluded from speed snapshots. `slskd_transfers.estimate_transfer_speed()` calculates the delta-based bytes/second estimate from current counters and a prior snapshot/time. `navidrome_server.py` still owns the HTTP call, expected/tracked matching invocation, snapshot key, shared snapshot storage/lock, and public progress response.

- PR #182 tested head `045131f58365dd0e6538c1712f37f56f639c65ad`, merged `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`; all four required exact-head workflows passed.
- PR #183 final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`, merged `e4e9bd1fad9536f00f3908d753b66147d30ca03f`; all four required exact-head workflows passed. Docker packaging CI ran 342 unit tests successfully.
- The legacy progress response, snapshot locking, and counter-reset behavior remain in place. No publication, deployment, or production runtime verification is claimed.

## Recommendation style classification — extracted (PR #171)

`discovery_recommendations.py` owns the pure `genre_families()`, `recent_style_families()`, `primary_recent_family()`, and `classify_diversity_style()` rules used by `recommend_new_music()`. The server imports these helpers inside the recommendation operation; scoring, provider I/O, candidate quotas, persistence, and the legacy MCP response remain in their existing owners. PR #171 merged at `6d00562405320affcb1a04b4359397b332cd5bf5` from exact tested head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9`. All four required workflows passed on that exact head.

## Last.fm album popularity — extracted (PR #172)

`lastfm_client.LastFmClient.album_popularity()` owns the cached Last.fm `album.getInfo` request, statistics/tag normalization, and lookup diagnostic mapping. It preserves the legacy `lastfm:album-info-v2` cache identity, 30-day TTL, 12-second timeout, direct/nested stats compatibility, and 404-as-silent-miss behavior. `navidrome_server._lastfm_album_popularity()` remains the compatibility adapter that updates `LASTFM_LAST_ERROR`. PR #172 merged at `d5153a3fe0625bc52b5896e87846b55cabe58e81` from exact tested head `d2808d44825e949ff71ed8471d25cee6570b54f1`; all four required workflows passed on that exact head.

## MusicBrainz tag audit — extracted (PR #170)

`music_tag_audit.scan_missing_mbids()` owns the bounded, read-only scan and receives the audio reader as a dependency. `navidrome_server.find_missing_mbids()` remains the legacy JSON/error-string adapter. The module is included in Docker packaging; direct-import tests cover tag interpretation, pagination, unreadable files, validation, and read-only behavior. PR #170 merged at `dbbdda35792fd569cfdeec2c4c7b42fc106f84e3` from exact tested head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07`; all four required workflows passed on that exact head.

---

## slskd transfer listing service — extracted (PR #157)

`slskd_transfers.py` owns the HTTP transfer-list request and recursive normalization into flat file records carrying `_transfer_directory`. It receives the HTTP client as an injected dependency and does not initialize the application. `navidrome_server._slskd_download_transfer_files(base_url, headers, username)` remains the compatibility adapter used by candidate-start validation. PR #157 merged at `17922f878f0ea391b47652012a38530e9eb044fc` from exact tested head `504b10392061dbc44d28d66e663b88cbefb8f1a4`. All four required workflows passed on that exact head. Deployment remains unverified.

## Expected slskd track count — extracted (PR #155)

`slskd_search.py` owns expected track-count metadata parsing. `navidrome_server._discovery_expected_track_count()` remains a compatibility adapter for the acquisition coordinator. PR #155 merged at `d732241de9edfd3c643a8fa89fb25c42b2a93c67` after all four required workflows passed on exact head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`. Deployment remains unverified.

## Music path default policy — extracted (PR #151)

`music_paths.py` owns the pure decision policy for configured music path and host mount fallback. It receives environment and directory-existence behavior from the caller, so importing it does not initialize application state. `navidrome_server._default_music_dir()` remains a compatibility adapter. Direct-import tests and Docker packaging are included; all four required exact-head workflows passed before merge. Deployment remains unverified.

## 2026-10-15 — Navidrome HTTP client extraction in progress

- `navidrome_client.py` owns Subsonic-compatible request authentication, HTTP request execution, and API response error interpretation.
- The client receives the existing settings provider as a dependency; it does not load settings or initialize the application itself.
- `navidrome_server.api_call(method, **params)` remains the compatibility adapter, preserving the legacy callable signature and existing callers, including MCP-facing discovery functions.
- Direct-import tests cover deterministic token generation, request parameters/options, successful payloads, and API error formatting. Docker packaging includes the module. CI and merge are pending; no test result is claimed before workflows run on the exact final PR head.

## 2026-10-15 — MCP tool registration separated from shared service imports

- Moved the 27 existing MCP tool registrations into the new mcp_registry.py; navidrome_server.py no longer imports MCPServer, constructs an MCP server, or decorates service functions at import time.
- The legacy MCP entry point remains compatible: when navidrome_server.py is executed directly, it creates the server through create_mcp_server() and runs on the existing streamable HTTP host/port. Tool names and function objects are kept in an explicit ordered registry.
- The web service can now import navidrome_server.py without loading mcp.server.mcpserver. MCP registration is deferred to explicit server startup; the MCP package and legacy tool surface are retained.
- Added tests/test_mcp_registry.py to assert the registry contains 27 unique tools, registers each provided function exactly once, and importing the legacy service keeps all registered functions callable without importing the MCP SDK.
- Branch: refactor/separate-mcp-tool-registration. All four required workflows passed on exact implementation/documentation head fe71a9a19188a018a2ee65d5b313a99413d239f2: Python syntax/acquisition safety run 38783091362; Docker packaging/full suite/build run 38783091326; container runtime smoke run 38783091309; validation-only multi-architecture run 38783091337. Publishing remains paused. No separate local test execution, deployment, or production runtime verification is claimed. PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00 from exact final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f. All four required workflows passed on that exact head: syntax/acquisition safety 38783296279; Docker packaging/full suite/build 38783296173; container runtime smoke 38783296256; validation-only multi-architecture 38783296249. Publishing/deployment remain paused; no production runtime verification is claimed.

## Proxmox MCP command allowlist — PR #114 merged

The separate root-level `server.py` is a host-side Proxmox MCP entry point and is not copied into the Librarian application image. Its `run(command)` tool previously forwarded arbitrary caller input to SSH despite describing the input as allowlisted. PR #114 adds a standalone strict allowlist for the documented diagnostic forms and refuses all other input before subprocess invocation. The MCP tool schema, SSH target/options, timeout, and output truncation for accepted commands are unchanged.

PR #114 exact head `cd8319696180875a3cb6f0dc151d88e0c8c490d7` passed syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`. Squash merge: `6ab848d444373dfa37e6d46528a2840a53a8f763`. No live Proxmox command, publication, or deployment was performed.


---

## 2026-10-15 — PR #108 merged: discovery router service injection

- `app/api/discovery.py` uses `Depends(get_librarian)` from the shared lazy dependency module, matching the acquisition router. Importing the discovery router no longer imports `navidrome_server.py` directly.
- Existing discovery functions still own recommendations, list generation, candidate filtering, and feedback persistence. `app/main.py`, settings routes, and MCP runtime retain their legacy server integration; no MCP tools or domain behavior were removed.
- PR #108 merged at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` from tested head `a5170e50080c0ca94b4068155ace83fd33c6f029`; all four required CI workflows passed. PR #112 was squash-merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No publication, deployment, or production runtime verification.

---

## 2026-10-15 — Web/MCP dependency boundary audit

- Direct server coupling remains in `app/main.py`, `app/api/acquisitions.py`, `app/api/discovery.py`, and `app/api/settings.py`. These are adapters around the existing `discovery_*` service surface, and preserving that surface is important for MCP compatibility.
- `app/api/auth.py` already uses a router factory with injected settings/session/password dependencies; `app/api/metadata.py` is independent of the legacy server. These are useful patterns for a future service-injection boundary.
- The main app still uses server-owned `DATA_DIR`, settings access, Navidrome ping, discovery list retrieval, and album-candidate filtering. Route tests currently patch each module's `librarian` binding, so an injection refactor must migrate these test seams deliberately.
- This was a read-only audit. No MCP retirement, domain relocation, route behavior change, or code extraction was performed.

---

## 2026-10-15 — Import source-root safety merged (PR #103)

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- Import pins source and destination-parent directory chains with no-follow flags, validates matched file identities, and uses descriptor-relative staging, publication, and rollback. Cross-filesystem copy fallback remains supported.
- The source-root symlink-swap, collision-suffix, cross-filesystem, and rollback regressions pass with all four exact-head workflows. No production-folder test or deployment is claimed.

---

## 2026-10-15 — Cleanup root traversal hardening merged (PR #100)

- PR #100 extends the directory-swap defense by opening the configured absolute root from `/` one component at a time with no-follow directory flags and checking its preflight device/inode identity after external callbacks.
- Cleanup validates the exact planned entries and file identities/sizes, then unlinks relative to the pinned target descriptor. Regressions cover target-folder and ancestor-folder symlink swaps. Exact-head CI passed; no production-folder deletion test is claimed.

---

## 2026-10-15 — Acquisition cleanup filesystem boundary hardened

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- `acquisition_cleanup.py` now uses no-follow directory descriptors and descriptor-relative unlink/rmdir after external transfer callbacks; device/inode checks reject a changed directory or file. The symlink-swap regression and all four required exact-head workflows passed. No production deletion test or deployment is claimed.

---

## 2026-10-15 — Acquisition request coordinator merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- The coordinator owns request decision sequencing through injected dependencies. The legacy MCP/web adapter, shared locks/state, persistence, watcher lifecycle, and acquisition implementation retain their existing ownership boundaries. All four required workflows passed on the exact PR head.

---

## 2026-10-15 — Last.fm settings policy boundary merged

- PR #97 merged at `ad239a59b77612b812ca842406fee7b47cf80889` from exact tested head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`.
- `service_settings.py` owns Last.fm API-key update policy behind injected settings read/write callbacks. `discovery_set_lastfm_settings` remains the MCP/web adapter with its existing signature and JSON response; SQLite persistence/schema and connectivity testing remain in `navidrome_server.py`.
- Responses expose only `api_key_configured`, never the key. Exact-head CI passed all four required workflows; no publication, deployment, or production runtime verification.

---

## 2026-10-15 — slskd settings policy extracted (PR #96)

- `service_settings.py` now owns the pure slskd configuration validation, safe settings serialization, and update policy behind injected persistence/path callbacks. `navidrome_server.py` retains MCP adapters and remains the owner of SQLite persistence, connection tests, and runtime `MUSIC_DIR`.
- Quality priority validation rejects invalid tiers before writes. The API key remains write-only in settings responses, and the runtime music directory changes only after settings persistence succeeds.
- Exact implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four required workflows; the documentation-updated head must be checked again before merge. The web app still imports the legacy module, so MCP retirement is not in scope.

---

## 2026-10-15 — Settings-policy boundary follow-up

- PR #95 moved Navidrome, ListenBrainz, and Last.fm settings policy to direct-import `service_settings.py`; legacy MCP/web adapters and persistence ownership remain in `navidrome_server.py`.
- The next extraction moves only slskd configuration validation and settings read/update policy behind injected callbacks. HTTP connection testing, SQLite persistence, and the global music-path owner stay in the legacy module. This remains an incremental boundary; the web app still imports `navidrome_server.py` and MCP retirement is not in scope.

---

## 2026-10-15 — Service settings policy extracted

- `service_settings.py` now owns injected, directly testable policy for Navidrome configuration validation/settings serialization/update, ListenBrainz username validation/settings update, and Last.fm configured-status serialization.
- `navidrome_server.py` keeps its existing MCP-decorated public functions and private compatibility helpers as adapters. It remains the owner of SQLite settings persistence, global `MUSIC_DIR` updates via an injected callback, network connectivity checks, and the remaining settings functions.
- The Dockerfile copies `service_settings.py`; tests now import it directly rather than AST-executing functions from the legacy server. This is an incremental seam, not removal of MCP initialization from the web import path.

---

## 2026-10-15 — Web dependency audit: settings-policy boundary

- The web layer currently imports `navidrome_server.py` directly in `app/main.py` and in the acquisitions, discovery, and settings routers. Main uses legacy persistence/configuration, Navidrome API access, discovery-list retrieval, and album eligibility; routers delegate to the corresponding legacy settings/discovery/acquisition functions.
- The legacy module both owns domain orchestration and registers MCP tools, so the web process imports MCP setup as a side effect. Separately, `server.py` starts a read-only MCP server and `requirements.txt` pins `mcp==2.3.0`; the Docker image does not include `server.py`. These are distinct compatibility/deployment facts, not authorization to remove MCP.
- The first small seam is settings policy currently covered by AST execution in `tests/test_service_settings.py`. Move the six functions to a directly importable module using injected persistence and path dependencies. Keep database lifecycle, global `MUSIC_DIR` updates, connection tests, and the existing MCP-facing adapters in the legacy layer for now.
- Do not make a broad import inversion in the same change. Expand service/domain separation incrementally with direct tests for each extracted behavior.

---

## 2026-10-15 — Dismissal-serialized import guard merged (PR #78)

- `acquisition_orchestration.import_source_unless_dismissed` owns the transition-lock/dismissal/callback guard. `navidrome_server.py` retains the compatibility adapter and the filesystem-safe import coordinator.
- PR #78 exact tested head `e6a609ca7381d0751d529b52f55aeebd56d76661` passed all four required workflows; squash merge `5d638c7adf5a42fdac8052cb4fc223236564cd72`. No filesystem safety logic was moved.

---


## 2026-10-15 — Search polling extraction merged (PR #76)

- `slskd_search_polling.py` now owns progressive query submission, search-state/response polling, count aggregation, peer payload deduplication, delayed-payload waiting, and per-attempt diagnostics behind injected external dependencies.
- `navidrome_server.py` remains responsible for configuration, candidate interpretation, acquisition status, queueing, and lifecycle transitions. The legacy MCP/web adapter contract is unchanged.
- PR #76 exact tested head `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6` passed all four required workflows; squash merge `a55a9fa7eed1e221f52434b50f44d0c415fd491a`.

---

## 2026-10-15 — Search polling boundary

- `slskd_search_polling.py` owns the slskd progressive-query/poll/wait algorithm behind injected HTTP, clock, sleep, ID-generation, and response-normalization dependencies. The server coordinator continues to own configuration, candidate interpretation, status reporting, queueing, and acquisition state transitions.
- The Docker image and Python syntax workflow must include this module. Keep the legacy server adapter and MCP/web return contract unchanged.

---

# Architecture

Last updated: 2026-10-14

## Overview

```text
Browser
  │ HTTP
  ▼
FastAPI web app (app/main.py) ───────► Navidrome API
  │                                    (external service)
  │ calls existing Python functions
  ▼
navidrome_server.py ─────────────────► slskd API
  │                                    (external service)
  ├── discovery orchestration and external-data enrichment
  │     └── discovery_recommendations.py (pure eligibility/scoring/diversity rules)
  ├── acquisition and import helpers
  ├── settings and persistent state
  └── MCP tool definitions (separate entry point)

Docker volume /data  ──► app database and authentication key
Host music directory ──► /music
Host completed downloads ──► /downloads
```

The diagram is logical, not a promise that every helper uses only those mount paths. Confirm actual path resolution in code before changing mounts or permissions.

## Remaining legacy-server coupling (audit 2026-10-14)

The diagram above shows the logical boundary, but the current implementation still imports `navidrome_server.py` from `app/main.py`, `app/api/settings.py`, `app/api/discovery.py`, and `app/api/acquisitions.py`. Metadata routes have been separated. These imports make the web runtime initialize MCP-related code because the legacy module creates an `MCPServer` and registers tools.

The web application still delegates settings persistence and service checks, discovery generation/list/feedback behavior, and acquisition lifecycle orchestration to the monolith. The Dockerfile copies the legacy module and `requirements.txt` includes MCP. `server.py` is also an MCP-related entry point and needs a caller/usage check before MCP dependencies are removed.

`tests/test_acquisition_safety.py` is coupled to the monolith's source layout through AST extraction. Migrate this coverage incrementally to direct-import tests of extracted domain modules; do not drop safety or lifecycle cases during migration.

Retirement condition: all web-required behavior must have an independent tested domain/service owner, all web callers must use those interfaces, and a repository-wide audit of imports, entry points, dependencies, tests, docs, and compatibility must establish that MCP-specific code can be removed safely.

## Main components

- **`app/main.py`** — FastAPI routes and the web UI. It adapts existing librarian functions for browser/API use.
- **`navidrome_server.py`** — discovery orchestration, Navidrome/slskd integration, acquisition lifecycle, settings, persistence, and legacy MCP tools.
- **`acquisition_completion.py`** — strict completed-track matching, filename identity, and completed-folder inspection.
- **`slskd_search.py` / `slskd_quality.py`** — importable slskd query/candidate helpers and audio-quality classification.
- **`discovery_refresh.py`** — refresh coordination for personal and named cached discovery lists; list builders, provider calls, server-owned locks, and persistence are injected.
- **`discovery_recommendations.py`** — pure discovery eligibility, normalization, scoring, and diversity helpers with direct-import tests.
- **`acquisition_lifecycle.py`** — importable lifecycle policy for monitor recovery, cleanup-required classification, skip validation, fallback payload normalization, and queue-error classification. The legacy server adapts these policies while database/network/filesystem orchestration is extracted incrementally.
- **`acquisition_state.py`** — dependency-injected SQLite persistence and decoding for acquisition job rows; legacy server adapters retain transition locks, conditional state transitions, and secondary feedback projections.
- **`acquisition_watcher_startup.py`** — dependency-injected watcher reservation, persisted state/status, and thread startup; the legacy adapter supplies locks and runtime callbacks.
- **`acquisition_import.py`** — staged filesystem import of verified album tracks, no-overwrite checks, storage-identity guards, and rollback; acquisition status/orchestration remains in `navidrome_server.py`.
- **`server.py`** — MCP/server entry point; inspect it before changing how the MCP integration is launched.
- **`tests/`** — automated tests, including acquisition safety, authentication, and service settings.
- **`Dockerfile` / `compose.yaml`** — web-app image and local Compose deployment.
- **`.github/workflows/`** — Python syntax, test/build, and image publishing automation.
- **`PROJECT_LOG.md`** — chronological development handoff; update at the end of each session.

## Runtime boundaries

- Navidrome and slskd are separate services. In the Docker Compose network, use service DNS names where services share that network; otherwise use a reachable LAN URL.
- The app container exposes port 8080 internally. The host port is configurable using `WEB_PORT`.
- `/data` must be persistent. It stores application state and authentication material; deleting the volume can reset both.
- `/music` and `/downloads` are bind mounts. Their host paths are deployment-specific.
- The image runs as UID/GID 1000. File operations depend on host ownership, mount options, and permissions.
- The web app is started with Uvicorn as `app.main:app`; this does not start the separate MCP server.

## Data and integrations

- Navidrome supplies the user's library context and service API.
- slskd is used for acquisition search, candidate selection/queueing, and download status.
- Last.fm and ListenBrainz are optional discovery/listening-profile integrations, depending on configured credentials and username.
- External metadata/artwork/year/biography lookups are enrichment only. Network failures or missing matches should not break the core discovery flow.
- Some responses are cached in memory for performance; persistent application state is held under the configured data directory. Check the implementation before relying on a particular cache's lifetime.

## Security and file safety

- Never bake `.env`, credentials, auth keys, or local databases into the image.
- Never log or return API keys/passwords to the browser.
- Validate user-provided artist/album/folder data at the API boundary and again where it becomes a filesystem path.
- Acquisition imports and dismiss cleanup are write/destructive operations. Limit them to configured roots and retain tests for traversal, ambiguous paths, incomplete albums, and unrelated files.
- Do not expose the web port directly to the public internet. Prefer LAN access or a trusted private overlay/VPN.

## Architecture change rules

1. Reuse existing domain logic instead of duplicating recommendation/acquisition behavior in the UI layer.
2. Keep route handlers thin: validate input, call a domain function, translate the result to an HTTP response.
3. Add tests at the domain/safety boundary and API boundary for behavior changes.
4. Preserve MCP behavior when refactoring code shared with the web app.
5. Do not modify unrelated services or replace the host's whole Compose file for a one-service change.


## Settings route boundary — PR #33

The settings endpoints for Navidrome, Last.fm, ListenBrainz, and slskd are grouped in app/api/settings.py. The route module adapts HTTP payloads and delegates behavior to existing librarian domain functions. app/api/utils.py owns the shared parse_result adapter; app.main imports that symbol to preserve callers while registering the router. Authentication middleware, URL paths, methods, and response/error contracts are intended to remain unchanged.


## Acquisition route boundary — merged PR #34

The acquisition endpoints (`/api/acquisitions*` and `/api/acquire*`) are being moved to `app/api/acquisitions.py`. The router delegates to existing `navidrome_server` acquisition functions; it does not duplicate lifecycle, slskd, streaming state, or filesystem safety logic. `app.main` registers the router alongside settings routes. This behavior-preserving route extraction is merged. Direct-import regression tests cover route inventory, payload/default mapping, input validation, skip/dismiss status translation, streaming headers, and sanitized errors. All required CI workflows passed on exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`; merge commit is `3aac576c42465420b9c2144c2cd2f4377c5e0ff1`.


## Discovery API route boundary — merged PR #35

The recommendations, cached discovery-list, refresh, and feedback HTTP handlers are grouped in `app/api/discovery.py`. The router adapts request parameters and responses while delegating recommendation filtering, ownership behavior, persistence, refresh coordination, and feedback semantics to existing `navidrome_server` functions. `app.main` registers the router alongside settings and acquisition routes. Direct-import route tests cover route inventory, defaults, validation, payload mapping, and sanitized failures. This extraction preserves existing URLs and delegates domain behavior to existing functions. All four required CI workflows passed on exact PR head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`; merge commit is `d61162b29c6f0cccc97aefe9c779567e671651b2`.


## Metadata API route boundary — merged PR #36

Artist biography, album-year, album-details, and artwork endpoints plus their external-provider HTTP client and in-memory cache/rate-limit helpers are being separated into `app/api/metadata.py`. The router preserves provider matching rules, cache TTLs, MusicBrainz request pacing, and the non-fatal fallback behavior for optional metadata. Regression coverage is in `tests/test_metadata_routes.py` and `tests/test_artwork_retry.py`. All four required workflows passed on exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`; merge commit is `15011614649470c9c71734422b95ee048fbf9f3c`. The initial CI run exposed an AST-based test coupled to the old handler location; the test was updated to exercise the extracted module directly, and all required workflows passed on the corrected head.


## Authentication security primitives — merged PR #37

Pure authentication primitives are being separated into `app/security/auth.py`: persistent signing-secret loading, username/password policy checks, PBKDF2 password digest, and signed-session creation/validation. `app/main.py` retains compatibility wrappers and continues to own persistent-settings access, cookie policy, login/setup/logout routes, rate limiting, and HTTP middleware. The split intentionally avoids changing middleware ordering or public-path behavior. Direct tests cover token signing/expiry, username binding, password hashing, signing-secret persistence, file permissions, and fail-closed handling of an invalid secret; All four required workflows passed on exact PR head `192b084850ecbe0137b64b3dae9d07e0471198b4`; merge commit is `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3`.


## Persisted acquisition orchestration seam — reconstructed PR #48

`acquisition_orchestration.py` owns the persisted manual source-skip transition through injected initialization, lock, database connection, key normalization, lifecycle policy, clock, and JSON dependencies. `navidrome_server.py` retains the MCP-compatible `discovery_skip_acquisition_source` adapter. The shared transition lock and conditional update requiring `status='downloading'` are preserved. Filesystem cleanup/import authorities are unchanged; watcher orchestration, source switching, interrupted-import recovery, and top-level acquisition coordination remain outstanding.


## Acquisition state persistence extraction — PR #59 merged

`acquisition_state.py` now owns SQLite save/list mechanics for acquisition rows behind injected dependencies. Legacy server adapters remain. Shared transition locking, conditional dismissed-state checks, feedback projection, dismissal/import coordination, and filesystem safety remain in `navidrome_server.py`. PR #59 exact head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed all four required workflows and was squash-merged at `730ae16e613f3962c488f87c8de54034db7463dd`. Publishing/deployment/runtime verification are not claimed.

## Settings router dependency seam (2026-10-15)

The settings router now obtains the existing librarian service through `app.api.dependencies.get_librarian`, consistent with acquisition and discovery routers. It no longer imports `navidrome_server.py` directly. The existing service functions remain responsible for settings policy, persistence, and live connectivity checks; HTTP handlers retain request/response adaptation and error mapping. This change does not retire MCP or change the application assembly dependency in `app/main.py`.


## Dashboard and health router boundary (2026-10-15)

The `/api/health` and `/api/dashboard-picks` handlers are grouped in `app/api/dashboard.py` and use the shared lazy `get_librarian` dependency. Navidrome ping, discovery-list reads, and album-candidate eligibility remain delegated to the existing service. Response shapes, count validation, category balancing, deduplication, randomization, and sanitized health errors are preserved. `app/main.py` still imports the legacy server for authentication settings and secret data-directory setup; this extraction is not MCP retirement.


## Dashboard and health router boundary — PR #110 merged

PR #110 moved `/api/health` and `/api/dashboard-picks` into `app/api/dashboard.py` behind the shared lazy `get_librarian` dependency. The extraction preserves the legacy service calls, response shapes, count validation, category balance, deduplication, randomization, and sanitized health errors. Exact tested head `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e` passed all four required workflows and was squash-merged at `b4015b8619f3c0db169722c347f72612996b9a1c`. `app/main.py` still imports the legacy module for authentication settings and data-directory/auth-secret initialization; MCP compatibility and persistence ownership remain unchanged.



## Lazy authentication service dependency — PR #112 verification

`app/main.py` no longer imports `navidrome_server.py` to define the web app. Authentication settings access and signing-key initialization call the existing service lazily through `get_librarian`. SQLite persistence, `DATA_DIR` ownership, settings migrations, MCP wrappers, and auth semantics remain unchanged. Direct integration coverage verifies app import does not initialize the legacy server and auth routes work with an injected fake service.

PR #112 exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed all four required workflows: syntax `38737672741`, Docker packaging/full suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture image validation `38737672689`. No publication, deployment, or production runtime verification.


## Listening profile aggregation — completed (PR #167)

The pure aggregation of ListenBrainz history into the recent-listening profile payload lives in `listening_profile.py`; `recent_listening_profile(days)` remains the legacy MCP-facing adapter. Direct-import tests cover payload shape, counts, empty history, and stable tie order. All four required workflows passed on exact head `ca8f9e4b7decb3404c78f1ee8b8d3078815fd71f`; PR #167 merged at `6b656dc7218280aa0d37e738a881061ceefde55e`.

## Discovery library snapshot — completed (PR #168)

`discovery_library_snapshot.py` owns cached artist/album inventory assembly with injected Navidrome API, collection-normalization, and discovery-store callbacks. The legacy `_discovery_library_snapshot()` wrapper remains in `navidrome_server.py`. Direct-import tests cover cache reuse/schema compatibility, album-ID deduplication, pagination, and the 50,000-album safety stop. All four required workflows passed on exact head `fc69943301c5065a54a0128c8b82ae214cd69dd1`; PR #168 merged at `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`. Publishing/deployment remain paused and unverified.


## Last.fm artist genre parsing — completed (PR #174)

`LastFmClient.artist_genres()` owns cached top-tag retrieval, normalization, case-insensitive deduplication, and the existing eight-tag limit. `navidrome_server._lastfm_artist_genres()` remains a compatibility adapter. Exact-head CI passed on `08c260e2a166a744bbde4009196b53d238afb647`; merged to main at `4dd8b926a7a6cf76e248420860d7c29c892da3c0`. Cache/pacing behavior and discovery grouping remain unchanged.


## Last.fm top albums — extraction in progress

`LastFmClient.artist_top_albums()` owns cached `artist.getTopAlbums` retrieval and response normalization. The legacy `_lastfm_top_albums()` adapter retains discovery-specific eligibility filtering. Exact-head CI and merge pending.


## Last.fm top album retrieval — completed (PR #175)

`LastFmClient.artist_top_albums()` owns cached `artist.getTopAlbums` requests and normalization of returned album metadata. The legacy `navidrome_server._lastfm_top_albums()` remains a compatibility adapter and continues applying discovery-specific album-candidate eligibility filtering. The extraction preserves request pacing, timeout, the 30-day cache TTL, caller-requested limit, and normalized output contract. Exact tested head `6b5e32b1144e9f3517247110ea4383b287ce33f4`; merged to main at `f922631e0393063bde02b1e0bd93d30b2d38bd2a`. All four required CI workflows passed on the exact head. No publication, deployment, or production runtime verification is claimed.


## Reviewed candidate normalization — PR #195

`acquisition_candidate_queue.py` owns pure validation and normalization of user-reviewed slskd file records and optional quality-summary JSON. The legacy `discovery_queue_slskd_candidate()` remains the adapter for response mapping, slskd queue I/O, and watcher startup. Invalid file-list and filename messages, malformed quality-summary fallback, and malformed file-size exception mapping are preserved. PR #195 tested head `f60d682b2ebcd94ecfbcfd0b4beb77c628643fc5`, merged at `5629d259468a0f748fb5d3fdb78819a0fb00d73c`; all four required exact-head workflows passed.

## MusicBrainz album-year lookup — PR #193

`musicbrainz_album_year.py` owns the exact release-group query, title and artist-credit matching, request pacing, and positive/negative cache. `app/api/metadata.py` retains `_musicbrainz_album_year()` as a compatibility adapter and preserves the album-year endpoint contract. PR #193 tested head `2b426587e6cb4dc011c85099021041d9f9450744`, merged at `bce1e32b4ca4c2df86f51dd6102931ed8299dcfe`; all four required exact-head workflows passed. No publication or deployment is claimed.


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

## Deezer artwork selection boundary (PR #216 merged)

`app/services/deezer_artwork.py` owns pure selection and response shaping for relevant Deezer album artwork and exact-name artist-photo fallback. `app/api/metadata.py` remains responsible for provider I/O, the cache and its TTLs, transient failure/retry behavior, and endpoint response flow. The helper reuses the existing album relevance/year policy. PR #216 merged at `ad61b1b91a5c351a73c02e37d7639bc47c61a52f` from exact tested head `aa1099e8ed43b9afcce483a50be31226a66218f4`; all four workflows passed (syntax 1148, Docker/full suite/build 1055, runtime smoke 864, validation-only multi-architecture 908).

## Deezer album-details shaping boundary (PR #217 merged)

`app/services/deezer_album_details.py` owns the pure projection of a matched Deezer album row into the established matched-artist, matched-album, year, and artwork URL fields. `app/api/metadata.py` retains provider I/O, exact catalog matching, tracklist retrieval, error handling, and response assembly. PR #217 merged at `37f04d0a863f69f5596f6a46406cc8bd64bde039` from exact tested head `b631f4c6367c68357cbd91f75b986770edfeee0e`; all four workflows passed (syntax 1151, Docker/full suite/build 1058, runtime smoke 867, validation-only multi-architecture 911).

## Exact Deezer release-year selection boundary (PR #218 merged)

`exact_album_release_year()` in `app/services/deezer_album_matching.py` selects the first plausible year among normalized exact artist-and-album matches. The metadata route retains provider access and the MusicBrainz-first response contract. PR #218 merged at `6dc6adae89169638da9a158c79ccee5d2e1ddfb7` from exact tested head `0293e4fe4eab7dd66dc82280720183dab3b913ed`; all four workflows passed (syntax 1153, Docker/full suite/build 1060, runtime smoke 869, validation-only multi-architecture 913).


## Authentication configuration predicate (PR #239 merged)

`app/security/auth_configuration.py` owns only the pure predicate over persisted owner-auth settings. `app/main.py` still owns reading settings from the service, secret loading, middleware/router assembly, and session-cookie integration. The extraction intentionally preserves truthiness checks and does not alter the authentication flow.


## Lazy auth-secret provider (PR #240 merged)

Merged from exact tested head `e3542c6a8fa3b2fc3ddf07a0268563ae5946064a` at `78547fd47c1b155255c1da6ef57120b76513a0fc`. `app/security/auth_secret.py` encapsulates lazy, lock-protected loading and successful-result caching of the persistent app-auth signing secret. The provider takes an injected data-directory getter and secret loader, avoiding app initialization or filesystem access at module import. `app/main.py` retains dependency wiring, the `_AUTH_SECRET` compatibility seam, settings access, session token creation, middleware, routes, and cookie integration. Loading failures and `None` results remain retryable. All four required workflows passed on the exact PR head; publishing/deployment remain paused.
