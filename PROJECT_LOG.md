## 2026-10-14 — PR #41 merged: frontend asset extraction

- **PR:** [#41 — refactor: extract frontend templates and static assets](https://github.com/abucalip/navi-librarian/pull/41).
- **Branch/head:** `refactor/frontend-assets`, exact tested head `b94dde68cccef776cea3813dbe7310eb857d170b`; squash-merge commit `410506ea76d7181aa300edb9c05ebbd337dd7159`.
- **Changes:** moved login/main HTML into `app/templates/login.html` and `app/templates/index.html`; moved styles/scripts to `static/`; mounted static assets and preserved public login/icon paths while keeping app/API paths protected. Updated Docker packaging, integration coverage, and tests that were coupled to inline frontend source.
- **Exact-head CI:** Python syntax `38493894120`, Docker packaging/full unit tests `38493894221`, validation-only Docker image/multi-architecture `38493894141`, and container runtime smoke `38493893959` all succeeded.
- **Manual UI report:** [published on PR #41](https://github.com/abucalip/navi-librarian/pull/41#issuecomment-6159043901). Eight checklist items passed with zero reported failures on macOS 26.2 arm64, Python 3.12.14, isolated port 8090, sandbox music/download paths, and slskd disabled. User observed noticeably snappier/smoother navigation and reported no errors during testing. A separately induced error/recovery scenario was not reported and is not claimed as completed.
- **Safety/status:** no local automated test run is claimed; no image publication, deployment, or production runtime verification. GHCR publishing remains paused.
- **Next:** inspect current GitHub main, open PRs, and roadmap/test gaps before selecting the next focused task.


## 2026-10-14 — Authentication integration coverage and route extraction (PRs #38–#39 merged)

- PR #38 was squash-merged at `84da7ebfe51199a5caf63f7689fe89df8d61b553` from exact head `1901cc68d1bb689da5257b6a51947af84b87d5ca`. The new FastAPI TestClient integration tests cover first-run setup and validation, login/logout, rate limiting, cookie attributes over HTTP/HTTPS, session reuse/tampering, and public/protected route behavior. Exact-head syntax, Docker packaging/full suite (147 tests), container runtime smoke, and validation-only multi-architecture workflows all passed. An initial test revision failed two redirect assertions; `follow_redirects=False` corrected those expectations.
- PR #39 (`refactor/auth-api-router`) extracts the authentication status/setup/login/logout endpoints and login page into `app/api/auth.py`; middleware remains in `app/main.py`, and security primitives remain in `app/security/auth.py`. Injected callbacks preserve the existing persistent settings store and runtime auth secret.
- PR #39 was squash-merged at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact head `9187a51380d2a7ed7d27276ce4505827becaed32`. All four required workflows passed on that exact head: syntax `38492677728`, Docker packaging/full suite `38492677704`, runtime smoke `38492677708`, and validation-only multi-architecture `38492677825`.
- No local test run or manual browser test was performed. No image publication, deployment, or production runtime verification occurred; GHCR publication remains disabled.
- Next: continue with the next roadmap priority after confirming the updated main state.

## 2026-10-14 — Modularization session closeout after PR #37

- Re-read the live GitHub roadmap, requirements, development workflow, architecture, test plan, project status, and project log. The current documentation records PRs #35–#37 and their exact-head CI evidence; no code changes or tests were performed in this documentation closeout.
- Main tip at review: `621295f87ab57cf1690be925cdcfd29d3f2b8fc7`. PRs #35–#37 are merged. The repository search still surfaced the older roadmap documentation PR #23, but the roadmap is already maintained on `main`; do not infer missing documentation from that search result alone.
- Next action: map auth setup/login/logout, throttling, cookie/session behavior, and middleware/public paths in `app/main.py`; add integration tests for those contracts before extracting route handlers or app assembly. Preserve the direct unit tests for primitives in `app/security/auth.py`.
- On the next UI-facing change, run the manual browser checklist after exact-head CI and explicitly record the deferred performance observation and separate error/recovery scenario.
- No local tests, manual UI run, image publication, deployment, or production runtime verification is claimed. GHCR publication remains disabled pending roadmap completion and explicit authorization.

## 2026-10-14 — PR #37 merged; authentication security helper closeout

- PR #37 squash-merged to `main` at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3` from exact head `192b084850ecbe0137b64b3dae9d07e0471198b4`.
- Extracted persistent signing-secret loading, username/password policy, PBKDF2 digest, and signed-session creation/validation into `app/security/auth.py`. Routes, cookie policy, throttling, settings access, and middleware remain in `app/main.py`.
- Replaced AST-based auth helper tests with direct unit tests for policy, digest, signing/expiry/tampering/user binding, secret persistence, permissions, and invalid-secret failure.
- All four required workflows passed on the exact head: syntax/full tests `38488744726`, Docker packaging/full tests `38488744684`, runtime smoke `38488744607`, and validation-only multi-architecture `38488744643`.
- No local test run, image publication, deployment, or production runtime verification is claimed. Next action: establish auth route/middleware integration tests before further app-assembly extraction.

## 2026-10-14 — Authentication security helper extraction started

- Branch: `refactor/auth-security-helpers`, based on updated GitHub `main` after PR #36 merged.
- Added `app/security/auth.py` for signing-secret persistence, username/password validation, PBKDF2 digest, and signed-session creation/validation. `app/main.py` retains compatibility wrappers and all route/cookie/middleware behavior.
- Reworked `tests/test_app_auth.py` from AST extraction of `app/main.py` functions to direct unit tests against the isolated primitives, including signing-secret permissions and invalid-secret handling.
- PR #37 has since been merged after all four required workflows passed on exact head `192b084850ecbe0137b64b3dae9d07e0471198b4`; see the closeout entry above. No local test run is claimed.
- No image publication, deployment, or production runtime verification. Publishing remains disabled pending roadmap completion and explicit authorization.

## 2026-10-14 — PR #36 merged; metadata API router closeout

- PR #36 squash-merged to `main` at `15011614649470c9c71734422b95ee048fbf9f3c` from corrected exact head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`.
- Extracted artist biography, album-year, album-details, and artwork endpoints plus provider/cache helpers into `app/api/metadata.py`; registered the router in `app/main.py`; added `tests/test_metadata_routes.py`.
- Initial CI caught the AST-coupled artwork retry test. Updated `tests/test_artwork_retry.py` to import and patch the extracted metadata module. All four workflows then passed on the corrected exact head: syntax/full tests `38488440438`, packaging/full tests `38488440512`, runtime smoke `38488440488`, and validation-only multi-architecture `38488440439`.
- No local test run, image publication, deployment, or production runtime verification is claimed. Manual UI testing was not required for this API-only extraction.
- Next action: map authentication dependencies and tests before a focused auth/app-assembly extraction. Keep publishing disabled pending roadmap completion and explicit authorization.

## 2026-10-14 — Metadata API route extraction started

- Branch: `refactor/metadata-api-router`, based on updated GitHub `main` after PR #35 merged.
- Moved artist bio, album-year, album-details, and artwork handlers plus their provider/cache helpers into `app/api/metadata.py`; registered the router in `app/main.py`.
- Added direct-import tests for route inventory, validation/cache behavior, MusicBrainz year preference, exact Deezer matching, and tracklist parsing.
- PR #36 was subsequently merged after all four required workflows passed on corrected exact head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`; see the closeout entry above. No local test run is claimed.
- No image publication, deployment, or production runtime verification. GHCR publishing remains disabled pending roadmap completion and explicit authorization.

## 2026-10-14 — PR #35 merged; discovery API router closeout

- PR #35 was squash-merged to `main` at `d61162b29c6f0cccc97aefe9c779567e671651b2`, from exact PR head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`.
- Changes: extracted four recommendation/discovery/refresh/feedback handlers to `app/api/discovery.py`, registered the router, added `tests/test_discovery_routes.py`, and reconciled roadmap, architecture, test plan, status, and project log.
- All four required workflows passed on the exact PR head: Python syntax/full unit tests run `38487647938`, container runtime smoke `38487647898`, Docker packaging `38487647913`, and validation-only multi-architecture `38487647952`.
- Diff review found no intended UI contract change; manual browser testing was not required. No local test run, image publication, deployment, or production runtime verification is claimed.
- Next action: begin the metadata routes/services extraction with focused tests and inspect existing callers/providers before changing code. Keep GHCR publishing disabled until the modularization roadmap is complete and explicitly authorized.

## 2026-10-14 — Discovery API route extraction started

- Branch: `refactor/discovery-api-router`, based on GitHub `main` following merged PR #34.
- Objective: extract recommendation, discovery-list, refresh, and feedback handlers into `app/api/discovery.py` without changing routes, defaults, validation/status behavior, ownership filtering, refresh coordination, or feedback semantics.
- Added `tests/test_discovery_routes.py` with direct-import checks for route inventory, candidate filtering, input validation, defaults, feedback JSON serialization, domain payload mapping, and sanitized failures.
- PR #35 was subsequently merged after all four required workflows passed on exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`; see the closeout entry above. No local test run is claimed.
- Publishing remains disabled; no image publication, deployment, or production runtime verification occurred.

## 2026-10-14 — PR #34 merged after exact-head validation completed

- PR #34 — Extract acquisition API routes — was squash-merged to `main` at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1`; exact PR head: `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`.
- All four workflows passed on that exact head: Python syntax #330 (run `38485830330`), Docker packaging/full unit tests #237 (run `38485830207`), container runtime smoke #47 (run `38485830231`), and validation-only multi-architecture #91 (run `38485830245`). The multi-architecture validation does not publish an image.
- Extracted six acquisition API endpoints into `app/api/acquisitions.py`; added `tests/test_acquisition_routes.py`; reviewed the eight-file PR diff. PR metadata reported mergeable/open before merge, and no submitted reviews or inline review threads were present.
- This is an API-only refactor with no intended UI contract change; manual browser testing was not required. No local tests, image publication, deployment, or production runtime verification are claimed.
- Next action: continue modularization from current GitHub `main` by extracting discovery API routes with regression tests. Keep publishing disabled until the roadmap is complete and separately authorized.

---

## 2026-10-14 — Acquisition API route extraction started

- Started branch `refactor/acquisition-api-router` from GitHub `main` after reviewing the project instructions, roadmap, requirements, architecture, workflow, test plan, project status, and open-PR search results. The connector's PR search did not return a reliable current open-PR inventory, so this entry does not infer PR state from that search.
- Extracted the six `/api/acquire*` and `/api/acquisitions*` route handlers into `app/api/acquisitions.py`; `app/main.py` registers the router with the settings router. The route module delegates to the existing `navidrome_server` functions, preserving domain ownership and destructive-operation safeguards.
- Added direct-import tests in `tests/test_acquisition_routes.py` for endpoint/method inventory, payload mapping and defaults, input validation, skip/dismiss status mapping, streaming headers, and sanitized errors.
- Updated `docs/MODULARIZATION_ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, and `docs/PROJECT_STATUS.md` to mark the stage in progress. CI, full-suite execution, exact final diff review, and PR creation remain pending; no test is claimed passed.
- No UI presentation change is intended, so manual browser testing is not expected unless the contract review shows otherwise. GHCR publication, deployment, and production runtime verification remain out of scope and unauthorized.

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

## 2026-10-14 — PR #31 documentation reconciled after PR #32 and #33 merges

- PR #32 merged at 8cce5a147060fa1ccc5a69eadb91e9b090c016f4; its exact reconciled head 155e7d3b18a23b919eb60098d50c639bd2962c99 passed syntax #310, Docker packaging/full-unit-test #217, container smoke #27, and validation-only multi-architecture #71.
- PR #33 merged at 25cd40eca0f20824173d7aefce76b753ef57360c from exact reconciled head 97154f6f7c482633b0cf0f71cebc2bd0afd0f558. Syntax/full-unit-test #313, container smoke #30, Docker packaging #220, and validation-only multi-architecture #74 all passed.
- PR #31's documentation branch is reconciled against main `25cd40eca0f20824173d7aefce76b753ef57360c`. Head `3eb3ec6726e0bbe03ef0df9f3d5022796feb7a0c` passed Python syntax workflow #316 (run 38482953860), container runtime smoke #33 (run 38482953883), Docker packaging/full-unit-test #223 (run 38482953864), and validation-only multi-architecture #77 (run 38482953840). A docs-only follow-up commit `2993273b633b865219818789c47160b8e2429a6f` records these results; its own exact-head reruns were in progress at closeout. PR remains open/unmerged; no merge is claimed. The report for application SHA 96b253c5f3ec2f858e02afc034365a22bac0773e recorded eight checks passing; performance observation and distinct error/recovery remain deferred to the next UI-facing PR.
- The local test account survived a server restart in the tested environment. This does not alone prove data reuse across a different PR source SHA. The local helper remains outside the repository.
- No image publication, deployment, or production runtime verification occurred. GHCR publication remains paused until modularization is complete and separately authorized.

## 2026-10-14 — PR #32 runtime smoke and publishing safeguard reconciliation

- Reconciled PR #32's runtime-verification and validation-only publishing safeguards against current main without replacing the newer PR #31–#33 closeout or local test-kit persistence notes.
- Required smoke assertions: startup/readiness, root redirects to /login before and after setup, public login/setup page, protected API returns 401, owner setup and login, private auth-key mode 0600, and account persistence across a container restart using the same named /data volume.
- Release gate remains validation-only: runtime smoke precedes the linux/amd64 and linux/arm64 build, push: false, provenance/SBOM generation, and no registry credentials/tags/publication. No deployment or production runtime verification is claimed.
- Merge/CI state is pending re-verification on the reconciled exact head. Outstanding manual UI performance and distinct error/recovery checks remain scheduled for the next UI-facing PR.

## 2026-10-13 — PR #30 merged: discovery refresh coordination

- **PR:** [#30 — Extract discovery refresh coordination](https://github.com/abucalip/navi-librarian/pull/30) merged into `main`.
- **Merge commit:** `a12538e7f7ab2f3ec7417680d6127f5c3a1eaa5b`; final PR head `f9256060d162ed92be0bbacc66a877c2675a5174`.
- **Change:** added `discovery_refresh.py` for personal and named-list refresh coordination while keeping compatibility adapters in `navidrome_server.py`. Added direct-import regression tests and updated architecture, decision D-012, test plan, and status docs.
- **Review:** complete diff reviewed with no blocking correctness issue found.
- **CI evidence:** Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156 passed on code head `46444e3c24dc78008e3c13dfb441059e73279814`; Docker CI included full unittest discovery and image build. A documentation-only commit triggered Docker workflow #157, but its terminal result was not available in the merge check. Do not infer latest-head or merge-commit CI success.
- **Boundaries:** Local_Git was unavailable (HTTP 429/404); no local test run, live refresh, manual UI test, image publication, or deployment was performed. Merge is confirmed; deployment/runtime remains unverified.

## 2026-10-13 — Discovery refresh coordination extraction started

- **Branch:** `refactor/discovery-refresh-coordination`, based on `main` at `0a3dbdc4fc09712f2c63e581244c4119ec0eda2d`.
- **Change:** added `discovery_refresh.py` for non-blocking lock coordination, personal recommendation payload validation, named-list dispatch, persistence callback invocation, response counts, and error translation. Existing server functions remain compatibility adapters and supply all external dependencies.
- **Regression coverage:** added `tests/test_discovery_refresh.py` for successful personal/other refreshes, malformed JSON, already-running locks, unknown lists, builder exceptions, and lock release.
- **Documentation:** updating architecture, decision D-012, test plan, project status, and this log as part of the PR.
- **Verification:** PR head `46444e3c24dc78008e3c13dfb441059e73279814` passed Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156. Docker CI ran full unittest discovery and built the image. Local_Git was unavailable (HTTP 429/404), so no local checkout test run is claimed. No live discovery refresh, UI verification, image publication, or deployment.
- **Review:** complete eight-file PR diff reviewed; no blocking correctness issue found. Both CI workflows passed on the reviewed head. Merge remains pending.

## 2026-10-13 — PR #29 merged; discovery list persistence extraction complete

- [PR #29](https://github.com/abucalip/navi-librarian/pull/29) was squash-merged into `main` at `001f3a7e76979d82adc62edd888d8490565b2ef3`; final PR head `518505f6dd8e233bc6aaec4b90ec42b0669f70d5`.
- Added `discovery_store.py` for cached discovery-list SQLite reads/writes and preserved the `navidrome_server.py` compatibility wrappers and schema initialization side effect.
- Added direct-import regression tests for absent/malformed rows, Unicode payloads, generation timestamps, and list replacement/isolation. Updated `docs/TEST_PLAN.md`, `docs/DECISIONS.md`, and project status.
- Final PR head passed Python syntax workflow #243 and Docker packaging workflow #150, including compilation, full unit-test discovery, and Docker image build: https://github.com/abucalip/navi-librarian/actions/runs/38434507492 and https://github.com/abucalip/navi-librarian/actions/runs/38434507399 . No workflow runs were returned for the squash merge commit at closeout.
- Local_Git returned 429/404; no local tests, live discovery refresh, UI test, image publication, or deployment. This change is merged, not deployed or runtime-verified.
- **Next:** extract discovery list construction/refresh coordination in a separate, regression-tested increment.

---

## 2026-10-13 — PR #28 merged; M4 discovery recommendation extraction complete

- **PR:** [#28 — Extract discovery recommendation rules](https://github.com/abucalip/navi-librarian/pull/28) squash-merged to `main` at `686fb393a178fe27f3806ecd5ce2138b026291cc`; final PR head `9ab8afeaed6562424b9212f2492d34f3ed9a69ee`.
- **Scope:** extracted pure discovery eligibility, normalization, genre-family, scoring, and diversity logic to `discovery_recommendations.py`; retained compatibility helpers in `navidrome_server.py` and kept owned-album filtering in orchestration. Reviewed all seven changed files.
- **Verification:** exact PR head passed Python syntax workflow #232 and Docker packaging workflow #139, including full unit-test discovery and Docker image build. No workflow runs were returned for the resulting squash merge commit at closeout.
- **Limits:** no local test execution, live discovery refresh, manual UI test, image publication, or deployment.
- **Next:** proceed with the next focused modularization roadmap priority from merged `main`.

---

## 2026-10-13 — M4 PR #28 final verification and session closeout

- **PR/state:** [#28 — Extract discovery recommendation rules](https://github.com/abucalip/navi-librarian/pull/28) remains draft/open, unmerged and undeployed. Final head before this documentation update: `63bfbff79d6a0f50264bf5b6859cbe3ce0ab1158`.
- **Reconciliation/review:** branch `refactor/discovery-recommendation-rules` incorporates latest `main` `15497d9149b80971414df26bf1b4acfbe02863cc`; compare shows 16 ahead, 0 behind and GitHub reports mergeable. Reviewed the complete seven-file diff. Extraction is limited to pure discovery recommendation rules, with compatibility helpers retained and owned-album filtering left in orchestration.
- **Final-head CI:** Python syntax/acquisition-safety workflow #230 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432040318)). Docker packaging workflow #134 passed compilation, full unit tests, and image build ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432040385)). Discovery regression tests ran as part of full unittest discovery; a separate local focused run was unavailable because Local_Git returned 404/429.
- **Boundaries:** no local test execution, live discovery refresh, manual UI smoke test, image publication, deployment, or merge. Passing CI is not evidence of deployment/runtime verification.
- **Next:** finish any remaining review and decide whether to undraft/merge as a separate authorized step.

## 2026-10-13 — M4 PR #28 reconciled with latest main; CI verification

- **PR:** [#28 — Extract discovery recommendation rules](https://github.com/abucalip/navi-librarian/pull/28), still draft/open/unmerged/undeployed.
- **Reconciliation:** merged latest `main` commit `15497d9149b80971414df26bf1b4acfbe02863cc` into `refactor/discovery-recommendation-rules` at merge commit `a713d476458bd55841f57b39f92041273fe49372`. The branch is now 15 commits ahead, 0 behind; GitHub reports it mergeable. Latest main's project log/status updates were retained alongside M4 notes.
- **Diff review:** inspected all seven changed files. Scope remains the pure discovery rules module, compatibility wrappers/server delegation, direct-import regression tests, and architecture/test/status documentation. Owned-album exclusion remains in server orchestration.
- **CI on code-bearing reconciled head:** [Python syntax check #229](https://github.com/abucalip/navi-librarian/actions/runs/38431779543) passed. [Docker packaging #133](https://github.com/abucalip/navi-librarian/actions/runs/38431779368) passed, including Python compilation, the full unit-test suite, and Docker image build. The focused discovery tests are included in full unittest discovery; no separate local run was possible because Local_Git returned 404/429.
- **Limitations:** no live discovery refresh, manual UI smoke test, image publication, or deployment. This does not authorize merge.
- **Next:** inspect CI on the documentation closeout head, then finish review and decide whether to mark PR ready; do not merge without the normal review/authorization step.

---

## 2026-10-13 — PR #27 merged; M3 acquisition import extraction complete

- **PR:** [#27 — Isolate acquisition import filesystem operations](https://github.com/abucalip/navi-librarian/pull/27), squash-merged. Merge commit on `main`: `bf6c044ab332148e537b6888b06078c5d75f059c`; final PR head `51c8ebd8736807f35deb9045b5ea92e38d874bed`.
- **Implementation:** extracted staged import of verified expected tracks, no-overwrite destination checks, storage-device identity guards, rollback, and recovery manifest handling to `acquisition_import.py`. The legacy `_discovery_import_matched_album_files` helper remains a compatibility wrapper injecting the strict matcher from `acquisition_completion.py`.
- **Regression coverage:** added direct-import tests for selective import/unrelated-file preservation, existing destination refusal, partial-move rollback, storage-device mismatch, and reserved manifest-name rejection. Updated the AST-based acquisition safety harness to exercise the extracted implementation through the wrapper.
- **Documentation:** updated architecture, decision D-010, and test plan; project status now records merge and verification state.
- **CI:** exact PR head passed Python syntax workflow #225 and Docker packaging workflow #132; Docker job completed the full unit suite and image build. GitHub returned no workflow runs for the squash merge commit at closeout, so merge-commit CI is not independently claimed.
- **Review/merge:** reviewed all nine changed files; no submitted reviews or inline review threads were present. User explicitly authorized merge.
- **Verification boundary:** connected local checkout remains untouched on `test/pr17-reconciliation`. No local test run, live import, manual UI test, image publication, or deployment was performed.
- **Next priority:** M4 — isolate discovery/recommendation scoring and eligibility behind direct-import regression tests while preserving owned-album exclusions, ranking, and diversity. Keep it as a focused PR.

---

## 2026-10-13 — PR #25 merged; M2 slskd search/quality extraction complete

- **PR:** [#25 — Extract slskd search and quality modules](https://github.com/abucalip/navi-librarian/pull/25), squash-merged. Merge commit on `main`: `84fa2f82dba562fd221a1d588e761d2cb4907749`; final PR head `39ecdc98aee5ca0ab1c096a242b700e165837e92`.
- **Implementation:** extracted quality classification to `slskd_quality.py` and query/response/path/track/candidate helpers to `slskd_search.py`; retained seven compatibility wrappers in `navidrome_server.py`. Search polling, 45-second overall budget, candidate thresholds, quality ordering, and acquisition lifecycle were kept in place.
- **Tests/docs:** added direct-import tests in `tests/test_slskd_search_modules.py` and updated `docs/TEST_PLAN.md`, `docs/PROJECT_STATUS.md`, and this log.
- **CI:** exact PR head passed Python syntax workflow #215 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38420456388)) and Docker packaging workflow #122 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38420456324), including full unit tests and image build). No workflow runs were returned for the merge commit at closeout.
- **Review:** no submitted reviews, inline review threads, or conversation comments were present at merge time. User authorized merge.
- **Verification boundary:** local checkout `test/pr17-reconciliation` was left untouched. No local tests, live slskd test, manual UI test, image publication, or deployment occurred.
- **Next:** continue with the next focused modularization priority documented by the project; PR #23 remains separate/open. Verify CI on subsequent exact heads and do not infer deployment from a merge.

---

## 2026-10-13 — M2 slskd extraction session closeout

- **PR:** [#25 — Extract slskd search and quality modules](https://github.com/abucalip/navi-librarian/pull/25) remains draft/open, unmerged and undeployed. Branch `refactor/slskd-search-quality-modules`; application-code head `e8a4256aaf34956ab1c4ca15b0b302c107689736` (later commits are documentation-only); base `main` at `0529c6912fdd9bea951334abec0f63c9cdbfd1d1`.
- **Verification confirmed:** application-code head `e8a4256aaf34956ab1c4ca15b0b302c107689736` passed Python syntax workflow #211 and Docker packaging workflow #118; the Docker workflow included the full unit-test suite and image build. Documentation-only closeout commits triggered fresh CI; Python syntax workflow #214 passed, while Docker packaging workflow #121 was still in progress at the last check. No local test run, live slskd test, manual UI test, image publication, merge, or deployment was performed.
- **Failure lesson:** first CI caught two stale private helper references in extracted callback paths. They were replaced with injected callbacks; the corrected code commit passed both workflows, and final-head workflows also passed.
- **Working tree safety:** the connected local checkout on `test/pr17-reconciliation` was left untouched.
- **Next:** inspect the complete PR #25 diff for behavioral equivalence and review readiness. Only then undraft/request review; do not merge without explicit authorization. Keep PR #23 separate/open.

---

## 2026-10-13 — M2 slskd search and quality extraction (PR #25 draft)

- **Branch/base:** `refactor/slskd-search-quality-modules` from GitHub `main` SHA `0529c6912fdd9bea951334abec0f63c9cdbfd1d1`; PR #25 is open as a draft. Local checkout `test/pr17-reconciliation` and its existing work were left untouched.
- **Files:** added `slskd_quality.py`, `slskd_search.py`, and `tests/test_slskd_search_modules.py`; replaced seven in-file helper implementations with compatibility wrappers in `navidrome_server.py`; updated `docs/TEST_PLAN.md`, `docs/PROJECT_STATUS.md`, and this log.
- **Behavior retained:** ordered query fallback and deduplication, slskd response payload normalization, six quality tiers and priority ordering, track identity and deduplication, album/path diagnostics, candidate confidence/eligibility and sort order. Search polling and the 45-second deadline, acquisition lifecycle, queue/import safeguards, settings persistence, and web behavior were not intentionally redesigned.
- **CI/root-cause correction:** the first PR CI run failed because two extracted functions still referenced the old private album-matcher/track-identity names after relocation. Replaced those references with injected callbacks. On corrected code commit `50bf72d44073b415ed07a59bc5b7707b76a59a31`, Python syntax/acquisition-safety workflow #209 and Docker packaging workflow #116 passed; Docker workflow included dependency install, compilation, full unit tests, and image build. No local run or live slskd/UI test occurred.
- **Current status:** implemented and automated-CI tested on the code commit above; PR remains draft/unmerged. Documentation updates are being recorded after the code verification, so check workflows on the final PR head before merge. No image publication or deployment.
- **Next:** review the complete PR diff, verify final-head CI, then request review and merge only after approval.

---

## 2026-10-13 — M2 slskd search and quality extraction started

- **Branch:** `refactor/slskd-search-quality-modules`, based on current GitHub `main` SHA `0529c6912fdd9bea951334abec0f63c9cdbfd1d1`; the local working checkout was left untouched because it is on `test/pr17-reconciliation` and contains unrelated work.
- **Files:** added `slskd_quality.py`, `slskd_search.py`, and direct-import tests in `tests/test_slskd_search_modules.py`; converted seven legacy slskd helper definitions in `navidrome_server.py` to compatibility wrappers.
- **Scope:** relocated quality classification, query construction, response parsing, album path matching, track identity, bounded path diagnostics, and candidate grouping/ranking. Search orchestration and its 45-second overall budget, delayed-payload polling, candidate acceptance thresholds, settings schema/order, and acquisition queue/import lifecycle remain in place.
- **Superseded implementation-stage status:** final-head Python syntax workflow #211 and Docker packaging workflow #118 subsequently passed on `e8a4256aaf34956ab1c4ca15b0b302c107689736`. See the session closeout at the top of this log for the final verification boundary and next step.

---

## 2026-10-13 — First acquisition-completion module extraction (PR #24 merged)

- **PR/branch:** [PR #24](https://github.com/abucalip/navi-librarian/pull/24), `refactor/acquisition-completion-matching`, based on `main` at `f9117811f373fd4b2b9bf1d35c57b667b0612b46`. PR #23's roadmap branch remains separate and unmerged; PR #24 does not contain that roadmap.
- **Scope:** moved safe remote folder-name normalization, NFC/casefold filename identity, and strict expected-track matching (including size checks and collision-suffix disambiguation) into root-level `acquisition_completion.py`; `navidrome_server.py` retains compatibility wrappers.
- **Tests:** matching tests now import production helpers directly instead of AST-extracting them. Added regressions for Unicode normalization, Windows-style remote paths, conflicting duplicate basenames, missing/invalid sizes, collision ambiguity, symlink exclusion, and folder-name sanitization.
- **Verification:** code-bearing head `a969ec4df6db2c5d45943c091401a5b26f9566d0` passed Python syntax/full-unit-test workflow #190 and Docker packaging workflow #97, including compilation, full unit tests, and image build. Subsequent branch commits only update documentation; the workflow lookup returned no PR-triggered runs for those docs-only commits. No local test run, manual UI test, merge, publication, or deployment.
- **Lessons learned:** GitHub API file-by-file edits caused avoidable iteration and 14 commits for a narrow extraction; context-based replacements caused intermediate source/test-fixture mistakes; status notes lagged behind the final head. Prefer a verified checkout/worktree and one coherent patch/test/review loop where available, inspect the entire diff before committing, and update status only after confirming final SHA and CI. Make branch dependencies explicit when parallel PRs are intentionally independent.
- **Merge result:** PR #24 squash-merged to `main` at `225add7405bfd72b3254af23745d0dd9a84b621c` from final head `b826ae14d917431d07aacf97200990d57133cba0`. Final-head Python syntax workflow #202 and Docker packaging workflow #109 passed; the latter includes the full unit suite and Docker image build. GitHub PR metadata and `main` commit search confirmed the merge commit is the current tip at verification time. No deployment or manual UI test was performed.
- **Priority next:** begin M2 — extract slskd search and quality evaluation into focused modules, preserving query fallback, delayed-response polling, timeout budgets, and quality ordering with regression tests.

---

## 2026-10-13 — Wait for delayed slskd peer payloads

- **Branch:** `fix/slskd-search-payload-wait`, based on PR #21 head `2876098ed222cc8803f292c55aa8e3474331e3e5`; not yet a PR, merged, or deployed.
- **Evidence:** for all three reported Tinariwen searches, the user's read-only diagnostic found the expected response shape from both slskd endpoints after the searches completed (26–33 peer records, hundreds of files). The acquisition result was generated while the searches were still reported as `inprogress` and had zero collected payloads. The evidence supports premature polling/fallback, not a response-shape mismatch.
- **Change:** extend the overall search budget from 30 to 45 seconds and, after slskd reports peers but has not yet exposed their file payloads, continue polling that same query rather than immediately moving to broader queries. Keep timeout values, candidate matching, quality ranking, queue behavior, and import safety unchanged.
- **Regression coverage:** mocked search reports peers for longer than the initial 18-second window, then returns payloads. Test expects a single query and successful payload collection.
- **Verification:** on code/test commit `1aad9fc90d2ceeb1659473131d4f4a867f739b63`, Python syntax/acquisition-safety workflow #177 passed, including the delayed-payload regression; Docker packaging workflow #84 passed compilation, full unit tests, and image build. Documentation-only commits followed. Local test execution and live slskd retest remain pending. No deployment or acquisition/import was performed.
- **Next:** check CI on this branch, then retest Tinariwen in the established port-8089 test checkout. If the fix passes, reconcile it into PR #21 before merging PR #22.

## 2026-10-13 — Broaden zero-response slskd acquisition searches

- **Branch/PR:** fix/flac-hires-acquisition-diagnostics, PR #21; PR #22 remains stacked and unmerged.
- **User clarification:** the Tinariwen Idrache (Traces of the Past) query inspected in slskd was automatically launched by Librarian.
- **Fix:** if a query yields no usable peer file payloads, try exact artist+album, punctuation-normalized artist+album, then artist+primary title with a parenthetical subtitle removed. Stop at the first usable payload set. Total search budget is capped at 30 seconds, with shorter timeouts on fallback attempts. Candidate matching and queue/import safeguards remain unchanged.
- **Diagnostics:** per-query records include query text, search ID/state, slskd-reported response/file counts, and collected response count. The no-match card message also prints the attempted query sequence and distinguishes reported counts from collected payloads.
- **DroppedNeedle:** adapted the bounded-search principle and separation between retrieval and candidate validation. No code copied.
- **Automated verification:** Python syntax/acquisition-safety workflow #166 and Docker packaging/full unittest/image-build workflow #73 passed on code/test commit 40e29bf93a661e4724674e2e9297b60549b21c9e. Later code/test commits add the visible query-sequence message and assertion; CI for the latest revision is pending. The mocked regression confirms the exact query gets zero usable payloads, the punctuation-normalized fallback is tried, and search stops after a usable payload is collected.
- **Remaining:** live Tinariwen retest in prox-mcp-pr17-test is pending. No merge or deployment.

## 2026-10-13 — Hi-Res FLAC priority and acquisition failure diagnostics (in review)

- **Branch:** `fix/flac-hires-acquisition-diagnostics`, based on GitHub `main`; PR/CI pending at implementation time.
- **Changes:** added a sixth sortable quality tier for FLAC Hi-Res (24-bit or sample rate above 44.1 kHz); recognized paired filename resolution labels including `[24-44.1]`; preserved user ordering when migrating four- and five-tier settings; exposed bounded candidate summaries in eligibility/queue failures and path/artist match signals when no source folders are recognized.
- **Regression coverage:** exact Tinariwen `Idrache (Traces of the Past)` folder variants, candidate completeness, 16/44 metadata classification, Hi-Res filename/metadata classification, and legacy quality-priority migrations.
- **Root-cause finding:** the Tinariwen folder variants pass the existing album-token matcher in an isolated fixture. Queue handling now retries on 400/404/422, returns a clear global error for 401/403, and monitors timeouts/5xx conservatively. Follow-up Bombino — Agamgam report showed `no_matches` with zero peer responses despite four sources visible to the user; the branch now normalizes response payload wrappers, briefly retries when slskd reports responses before payloads are visible, and records slskd-reported response/file counts. Live confirmation remains pending.
- **Validation:** Python syntax/acquisition-safety workflow #150 passed on queue-failover code commit `8df498909ca4ac1e1df6fe1b726e5f018ff749d3`; Docker packaging workflow #57 passed compilation, full unit tests, and Docker image build. A subsequent documentation-only commit records these results. No production deployment or live slskd calls performed.
- **Next:** review the PR diff and CI, test the reported album in `prox-mcp-pr17-test`, then use `candidate_diagnostics` and `attempts` to identify the remaining stage if it still fails.

## 2026-10-13 — PR #20 merged: FLAC 16/44 and sortable quality priorities

- **PR:** [#20 — Add FLAC 16/44 and sortable quality priorities](https://github.com/abucalip/navi-librarian/pull/20), squash-merged into `main`.
- **Merge commit:** `a9218bb5cb5c663b7ef26dc5f42cd69bbeadba45`.
- **Behavior:** added FLAC 16-bit/44.1 kHz as the fifth quality tier; existing four-tier settings retain their order and append the new tier. Replaced quality dropdowns with a draggable priority list plus Move up/Move down controls; ordering persists through the existing Settings API. Classification requires explicit FLAC sample-rate/bit-depth metadata or an explicit filename label.
- **Regression coverage:** added `tests/test_quality_priority.py`; updated requirements, test plan, v0.2 quality notes, and syntax CI coverage.
- **CI:** Python syntax/full unittest workflow #141 and Docker packaging workflow #48 passed on PR head `ac43126efdea9a6ac5cbe36d81b26b11c23da509`. Docker packaging included the full unit suite and image build.
- **Manual test:** user tested PR20 in the existing `prox-mcp-pr17-test` environment and reports all is good, including the UI interaction. Credentials/configuration were preserved by reusing that environment.
- **Deployment:** no image publication or production deployment was performed in this session.
- **Next:** continue from GitHub `main`; if release is requested, publish/deploy separately and verify the running image digest.

## 2026-10-13 — PR #20 quality priority implementation and CI

- **PR #20:** [Add FLAC 16/44 and sortable quality priorities](https://github.com/abucalip/navi-librarian/pull/20), branch `feature/flac-16-44-drag-sort-priority`.
- **Implementation:** added `flac_16_44` as the fifth tier; migrated legacy four-tier settings by appending the new tier; added metadata/filename-based FLAC 16/44 classification; replaced dropdowns with drag-sortable settings plus Move up/Move down alternatives.
- **Regression tests:** `tests/test_quality_priority.py` covers FLAC classification, legacy migration, order persistence, strict five-tier validation, and sortable UI hooks.
- **Verification on code/test head `9cbb5b054dbe52921df9ed044ddb763e0dcf0b76`:** Python syntax/full unittest workflow #140 passed; Docker packaging workflow #47 passed, including full unit tests and image build.
- **Documentation:** updated requirements, test plan, v0.2 quality backlog, project status, and CI compile list.
- **Remaining:** manual UI drag/drop and save/reload verification. PR is open and not merged; no image publication or deployment performed.

## 2026-10-13 — Five-tier quality priority and drag-sort Settings (in progress)

- **Branch:** `feature/flac-16-44-drag-sort-priority`, based on GitHub `main` at `7dfe5e620ff5c9941f9aa359b4c0f3fe2bec9d1e`.
- **Changes:** added `flac_16_44`; existing four-tier persisted settings append it without reordering existing priorities; quality validation requires five distinct supported tiers; FLAC 16/44 classification requires explicit metadata or a filename label; Settings now provides drag-and-drop order plus Move up/Move down alternatives.
- **Regression coverage:** added `tests/test_quality_priority.py` for FLAC classification, legacy settings migration, five-tier persistence/validation, and presence of the sortable accessible UI.
- **Docs/CI:** updated `docs/REQUIREMENTS.md`, `docs/TEST_PLAN.md`, the v0.2 quality backlog, and Python CI's compile list.
- **Status:** implementation committed to the feature branch; tests, CI, PR review, and UI smoke test pending. Not merged, published, or deployed.

## 2026-10-12 — PR #19 merged; PR #18 superseded after merge conflict

- **PR #17:** merged at `9f4ff509d6a336823912c49d8c049eeea8761b8f`; user manually reports completed downloads appear imported. No-source acquisition failures are expected.
- **PR #18:** original documentation branch conflicted with the PR #17 update to `docs/PROJECT_STATUS.md`; closed without merging so no existing handoff content was overwritten.
- **Replacement PR #19:** [docs: reconcile GitHub-first workflow and project handoff](https://github.com/abucalip/navi-librarian/pull/19), squash-merged at `fe60dd3aaf323bd6f3489f89b13ee9946ba7f382`. Added `docs/DEVELOPMENT_WORKFLOW.md`, decision D-009, and the session handoff updates in `docs/PROJECT_STATUS.md` and this log.
- **CI:** Python syntax/acquisition-safety workflow #136 and Docker packaging workflow #43 passed on PR head `bca1b143f45b870492f99c86ecdc5ef9ed9d6ec7`; Docker build and unit tests passed. No application code changed in PR #19.
- **Deployment:** not performed. No new image publication or production container verification is claimed.

## 2026-10-12 — PR #17 merged; acquisition completion manually verified

- **PR:** [#17 — Diagnose acquisition completion and handle missing slskd transfers](https://github.com/abucalip/navi-librarian/pull/17), squash-merged into `main` at `9f4ff509d6a336823912c49d8c049eeea8761b8f`.
- **Behavior:** missing slskd per-peer transfer entries (HTTP 404) now produce an empty current transfer list, while filesystem completion inspection continues. Other HTTP failures remain errors; import safeguards are unchanged. Bounded diagnostics identify absent, incomplete, ambiguous, or mismatched completed-download folders.
- **Validation:** CI Python syntax/full unit suite #134 and Docker packaging #41 passed on tested PR head `ff2153bbaf790b2c0bbfce03c8c7fdb6c7decc12`. User manually reports that completed downloads now appear imported. Acquisitions failing due to no available sources are expected.
- **Deployment:** no image publication or production deployment was performed in this session.
- **Documentation:** GitHub-first workflow guidance from PR #18 is being reapplied on a branch based on the post-merge `main`, because the original PR branch conflicts after PR #17.

## 2026-10-12 — GitHub-first development workflow documentation

- Added `docs/DEVELOPMENT_WORKFLOW.md` and decision D-009: GitHub is the sole source of truth; the assistant authors/commits changes; local checkouts are for testing exact GitHub revisions; local-only commits are never reconciled into authoritative PR branches; merge, publish, deploy, and verify are distinct states.
- The original PR #18 branch conflicted with the updated main in `docs/PROJECT_STATUS.md`. The documentation is being transferred to a fresh branch based on current main to preserve the PR #17 handoff without overwriting it.

## 2026-10-12 — PR #17 follow-up: slskd monitor errors

- **User-observed error:** multiple acquisitions entered `monitor_error` with `HTTPStatusError: 404 Not Found` from slskd's per-peer transfer-list endpoint.
- **Root cause:** the watcher treated a missing current transfer-list entry as an exceptional failure. The completed-download filesystem is already checked independently on each poll, so an absent transfer record should not stop monitoring.
- **Fix:** `_slskd_download_transfer_files` returns an empty list for HTTP 404 and continues to raise for other HTTP errors. The strict file/folder checks before import are unchanged.
- **Regression tests:** added `tests/test_slskd_transfer_lookup.py` for 404, non-404 error propagation, and successful payload parsing.
- **Commits:** implementation `4ced0a22b980325dde58609087700d0926b65bde`; test `e946d460acc11fb675bd25c1358ef3d243c32dd5`; test-plan update `4ee60d4151899ad5406da979c00d7995e7e8f768`; handoff update `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd`.
- **PR:** [#17 — Diagnose acquisition completion and handle missing slskd transfers](https://github.com/abucalip/navi-librarian/pull/17), open, not merged/deployed. Latest head is `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd`.
- **Verification:** GitHub Actions Python syntax/test workflow #131 passed on code commit `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd` (compile plus full `unittest discover`); Docker packaging workflow #38 passed on that same commit (dependencies, compile, tests, image build). The user has not yet retested acquisition behavior. Later commits update documentation only.
- **Next:** have the user test the latest PR revision and check the acquisition statuses. If monitor errors persist, capture updated `details.error_message` values; don't assume this is the only possible failure.

## 2026-10-12 — Local feature branch merged into main for testing

- **Local branch:** `fix/artwork-size-and-artist-bios` merged into `main` with merge commit `90e1d97` (`Merge local artwork and acquisition fixes`).
- **Validation:** user reports that local `main` passed their tests. Exact commands and output were not captured, so no more specific automated-test claim is made.
- **Workflow decision:** `main` is now intended to be the single local testing ground. Keep the source feature branch temporarily; do not delete it or clean up worktrees until no longer needed.
- **Scope boundary:** this is a local merge. No push to GitHub or deployment was confirmed in this session. Do not infer remote or server state from local commit `90e1d97`.
- **Documentation:** updated the project handoff on GitHub because the available local Git connector is read-only; these documentation commits do not push the local application merge.
- **Next:** continue testing from local `main`. Before publishing, inspect the local-vs-remote diff, push intentionally, and confirm CI on the pushed commit.

## 2026-10-12 — PR #16 merged and Docker image published

- **PR:** [#16 — Fix artwork loading after transient provider failures](https://github.com/abucalip/navi-librarian/pull/16), squash-merged to `main` at `ac0eec1e628caa0b300e651fcbdbe25535515395`.
- **Code:** transient artwork-provider failures are marked retryable and are not negative-cached; frontend retries with bounded backoff. Fixed a separate frontend cache collision by isolating `albumYearRequests` from `artworkRequests`.
- **Tests/CI:** `tests/test_artwork_retry.py` and `tests/test_artwork_cache_isolation.py`; Python syntax/test workflow #114 and Docker packaging workflow #22 passed. Docker publication workflow #11 passed.
- **Image:** `ghcr.io/abucalip/navi-librarian:latest`, `ghcr.io/abucalip/navi-librarian:sha-ac0eec1`, digest `sha256:7a9415a7e6d10bd9864a2e03db8c452cfdc35cb69359eaa0e9b0552552afb5b1`.
- **Manual test:** user reports album artwork loads very fast in the tested PR build.
- **Not done:** production container was not pulled/recreated; no direct shell/deployment connection to the media VM was available. Do not label host deployment verified until Compose update and post-deploy smoke test are recorded.
- **Next:** update the host container safely and sync local Git without disturbing the user's existing modified checkout.

# Navidrome Librarian — Development Log & Handoff

Update this file at the end of every GitHub development session. Keep entries concise: current branch/PR, changed behavior, validation, known caveats, and the next step.

## 2026-10-12 — Artwork loading reliability fix (in review)

- **Branch:** `fix/artwork-loading-retries`.
- **Manual-test regression discovered:** user reported that no artwork loaded when testing the PR. The frontend reused a shared artist+album promise cache for both `/api/album-year` and `/api/artwork`; when the year request populated the key first, artwork received the year-only response and never assigned an image URL.
- **Fix:** isolate year lookups in `albumYearRequests`, leaving `artworkRequests` dedicated to `/api/artwork`. Added `tests/test_artwork_cache_isolation.py` to guard the separation.
- **Status:** fix and regression guard committed to this PR branch; CI and user retest are pending. Do not merge/deploy until verified.
- **Root cause:** `/api/artwork` swallowed provider exceptions and cached them as a normal negative result for five minutes. The browser marked a card requested and unobserved it on the first attempt, so a transient Deezer outage could leave artwork blank for the rest of the page session.
- **Change:** provider exceptions now return a retryable marker and are not cached; browser retries up to three times with bounded backoff. Ordinary no-match responses remain cached as before.
- **Regression coverage:** `tests/test_artwork_retry.py` tests that provider timeouts are retryable and not negative-cached.
- **Validation:** GitHub Actions passed Python compilation and the full unittest suite (run #110) and Docker packaging validation (run #17) on code commit `fabcd1fb6563ef9cd65aa12005f2f77f3f90e07d`. Manual UI behavior remains unverified.
- **Status:** open PR #16; not merged or deployed. The local checkout on `fix/artwork-size-and-artist-bios` was not modified.
- **Next:** create/check the PR, run the full automated suite and CI, and manually verify artwork on Discoveries and Artist Deep Dives against the deployed app.

## 2026-10-12 — Successful server installation and baseline smoke tests reported

- **User-reported deployment:** Librarian is installed on the server; the Docker package has been made public.
- **User-reported working flows:** first-run account creation, entering service credentials through Settings, downloads, and imports all work as intended.
- **Documentation updates:** corrected `docs/PROJECT_STATUS.md` and `docs/DEPLOYMENT.md`. The earlier GHCR `unauthorized` note is no longer an active blocker according to the user's update.
- **Evidence boundary:** these are the user's direct test results. This session did not independently inspect the live host, container logs, published image digest, or repeat application tests. The deployed image tag/digest and host details remain to be recorded at the next release/update.
- **Changes in this session:** documentation only; no application code or server configuration changed. No tests were run in this documentation session.
- **Next:** preserve the working flows as regression baselines. Before v0.2 implementation, inspect the actual current code and tests, then prioritize a narrowly scoped acquisition-completion reliability fix with regression coverage. Record the exact image tag/digest at the next deployment.

## 2026-10-12 — PR #15 merged: v0.2 planning from DroppedNeedle review

- **PR:** [#15](https://github.com/abucalip/navi-librarian/pull/15), `docs: plan v0.2 improvements from DroppedNeedle review`, squash-merged into `main`.
- **Merge commit:** `f32b02a13b582e23699bde294eb94b51e5f646cc`; follow-up project-status documentation commit: `5f879818a0d3ea315c88dd302610d990eba32602`.
- **Document:** `docs/V0.2_DROPPEDNEEDLE_LESSONS.md` records prioritized proposals for acquisition completion evidence/diagnostics, safe lifecycle boundaries, consistent quality evaluation, recommendation pipeline clarity, caching review, and regression/performance guardrails.
- **Constraints captured:** DroppedNeedle has often been slow and buggy in the user's experience; smoothness and stability must not be sacrificed. Keep Librarian focused on the Navidrome–slskd bridge and library-/taste-aware recommendations. Split Python modules incrementally by clear responsibility. Review AGPL-3.0 implications before copying any code.
- **Validation:** GitHub Actions reported Python syntax check and Docker packaging validation successful on PR head `3e1f005e413a5522ec2866f30baebf1914cc4868`. Documentation-only change; no application tests or UI smoke tests were run.
- **Deployment:** not performed because no application code or image changed. Runtime remains unverified and the existing GHCR `unauthorized` pull blocker remains unresolved.
- **Local checkout:** preserved on `fix/artwork-size-and-artist-bios`, clean and six commits ahead of its recorded origin. No local checkout, reset, or cleanup was performed.
- **Next:** before implementing v0.2, inspect the actual current code/tests and start with a narrowly scoped acquisition-completion reliability fix plus regression tests. Resolve GHCR authorization before the next application deployment.

## 2026-10-12 — New releases and recommendation quality

- **Branch:** `feature/new-releases-and-recommendation-quality` (based on `main`).
- **Scope:** active-download count in navigation; exclude non-album releases/compilations/remixes; show release years consistently; improve slskd album-folder matching and diagnostics; one deep-dive card per artist per genre row; replace Listening Profile UI with New Releases; refresh the listening-profile summary automatically in the background.
- **New Releases definition:** MusicBrainz release groups from the previous 730 days, only artists represented in the Navidrome library who have at least one owned album with six or more tracks. Initial scan is bounded to 120 library artists, ranked by library album count; lookups are cached.
- **Acquisition matching:** preserve file-size and expected-track completeness safeguards; relax album-name matching for punctuation/edition suffixes and avoid conflating same-named folders from different remote paths. Import safety remains unchanged.
- **Validation:** regression tests added for album eligibility, edition-suffix matching, and token-boundary false positives. GitHub reports no check runs/statuses yet; the workflow branch-filter change is in this PR, while GitHub evaluates PR workflows using the base branch's workflow configuration.
- **Deployment:** not deployed or merged. The branch is available for local sync and tests; do not merge until the Python tests and UI smoke tests pass.
- **Next:** sync this branch into a separate local worktree, run `python -m py_compile navidrome_server.py app/main.py tests/test_acquisition_safety.py` and `python -m unittest discover -s tests -v`, then smoke-test New Releases, album filtering, deep-dive rows, acquisition badge/year, and a known slskd search.

## 2026-10-12 — Acquisition test harness fix

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 (still open; not merged or deployed).
- **Issue:** Local test run compiled successfully but 11 acquisition/import tests errored because the AST-based test harness did not load the newly used `_discovery_filename_key` helper or provide its `unicodedata` dependency. This was a test-harness dependency omission, not a Python syntax error.
- **Fix committed:** `4e1498a` adds the helper to the selected test definitions and injects `unicodedata` into the isolated namespace.
- **Validation:** Not yet rerun after this fix. Next: fetch/pull the latest PR branch into the test worktree and rerun compile plus the full unittest suite. Do not merge until tests and UI smoke tests pass.

## 2026-10-12 — Card details, year coverage, and New Releases artist matching

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 (open draft; not merged or deployed).
- **User smoke-test feedback:** album years were visible only on New Releases; non-album filtering and one-artist-per-Deep-Dive-row behavior looked correct. New Releases included several purported 2026 releases for Queen, suggesting artist-name search collisions.
- **Year coverage:** all album-card types now request a year when metadata does not already provide one. Artwork lookup requires both artist and album to match closely before its release year is accepted, preventing an unrelated album by the same artist from supplying the year.
- **New Releases fix:** require an exact normalized artist name in MusicBrainz artist-credit data instead of a substring match (which could admit names such as “Queen Tribute”). Candidate albums still must pass the full-album/non-album exclusion filter.
- **Album details popup:** clicking the non-button area of dashboard, recommendation, discovery, or acquisition cards opens a modal with artwork, album/artist/year, tracklist, durations, and a Get button beside the artwork. Get-button clicks do not open the modal; Escape/backdrop/close button dismiss it. Tracklist lookup uses an exact artist+album match in Deezer and fails safely when no exact match is found.
- **Regression test:** added coverage proving exact `Queen` artist credits match while `Queen Tribute` and `The Queens` do not.
- **Validation:** code changes committed through GitHub; local syntax compilation, full unit tests, and UI smoke test for popup/year coverage/Queen results remain pending. Keep PR unmerged until validation passes.

## 2026-10-12 — All-card year rendering and platform links

- **Root cause of years appearing only on New Releases:** some renderers call `makeAlbumCardInteractive` before creating the card's `h3`. If the item already had a year, `applyAlbumYear` saved it in `data-release-year` but could not attach the badge because the title did not exist yet. The title was then created without the badge.
- **Fix:** all card types now default to a year lookup when metadata has no year. The shared `addTextElement` helper now checks for a saved `data-release-year` when an `h3` is created and adds the year badge at that point. This handles both asynchronous lookup results and years available before the title exists. Dashboard cards keep their existing explicit year rendering.
- **Popup platform buttons:** added ListenBrainz, Apple Music, Spotify, Qobuz, and Bandcamp buttons directly beneath the popup artwork. They open targeted artist+album searches in each service in a new tab (the app does not yet have authenticated/platform-specific album IDs to promise a canonical album URL).
- **Validation:** Python syntax CI, local full unit suite, and UI smoke test for card-year coverage and platform links remain to be checked. PR #12 stays draft, unmerged, and undeployed.


## 2026-10-12 — Rework year lookup, platform icons, and Various Artists exclusion

- **Year lookup:** separated year retrieval from artwork loading. Cards call a dedicated `/api/album-year` endpoint. MusicBrainz release groups are primary; only exact normalized album titles and exact credited artist names qualify. Deezer is a fallback only for an exact artist-and-album match. Positive results cache for 180 days; misses cache for six hours.
- **Year display:** added a shared badge-enforcement helper after title creation, including renderers that create headings manually instead of using `addTextElement`.
- **Platform links:** replaced text panels with compact, fixed-size logo icon buttons beneath the artwork; links keep accessible labels.
- **New Releases:** exclude Various Artists pseudo-artist entries before querying and again during candidate filtering; regression tests cover common aliases.
- **Validation:** automated syntax/unit tests and visual browser smoke tests have not yet been run against this update. PR #12 remains draft and is not merged or deployed.


- **CI update:** GitHub Actions Python syntax check passed on commit `dae861ee538f8b5837ef1c538f0ed1cf575aecb0` after the year-fetch and Various Artists changes. Official ListenBrainz/Qobuz image URLs were adjusted afterward; full unit tests and visual browser verification remain pending.

- **Additional year-rendering audit:** found that some metadata can contain a full date string (for example, `YYYY-MM-DD`), which `Number(value)` rejected, and one card renderer manually created its title without rechecking a late-arriving year. Added a shared year parser and applied the badge helper after every manually-created album heading.


## 2026-10-12 — Service settings and deployment configuration groundwork

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 remains open and unmerged.
- **Settings UI:** reorganized Settings into four service tabs: Navidrome, slskd, Last.fm, and ListenBrainz. Navidrome owns the library path; slskd retains its server URL, API key, completed-download path, and quality preferences.
- **Configuration:** added persistent Navidrome URL/username/password settings, optional Last.fm API key settings, and a configurable ListenBrainz username. Blank secret fields preserve existing credentials; settings APIs never return saved secrets. Navidrome credentials are resolved dynamically, so updates take effect without a process restart.
- **Persistence groundwork:** added `NAVIDROME_LIBRARIAN_DATA_DIR` for application SQLite state, preparing for a Docker-mounted `/data` volume. The discovery settings database remains permission-restricted.
- **Validation:** GitHub Actions passed Python compilation, acquisition safety regressions, and the new service-settings regression tests on commit `3c25182`. Browser UI/API smoke testing remains pending. Docker packaging is intentionally deferred.

## 2026-10-12 — First-run app account and login protection

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 remains open and unmerged.
- **First-run setup:** a fresh installation prompts the owner to create a username and password; setup is disabled after the first account is saved. Username is validated and passwords must be at least 12 characters.
- **Authentication:** app routes and APIs are protected by a signed, HTTP-only, SameSite=Strict cookie with a 12-hour expiry. Passwords are stored only as PBKDF2-HMAC-SHA256 hashes with per-account random salts; the signing key is created in the persistent data directory with restrictive file permissions. Login attempts are rate-limited per client IP.
- **Session UX:** successful setup/login signs in immediately; a Log out button clears the browser cookie. Auth is required for API calls, acquisition actions, settings, and the web interface.
- **Tests:** added `tests/test_app_auth.py` for username/password policy, salted password hashing, signed session integrity, expiry, and username binding. GitHub Actions run #83 passed compilation and the full unittest suite, including the new authentication tests. Browser testing remains pending.
- **Operational note:** back up the persistent data directory, including `app_auth.key`; losing that key invalidates active sessions. The app account is separate from Navidrome credentials. Do not merge/deploy until CI and unauthenticated/login/setup/logout smoke tests pass.
- **Next:** run syntax compilation and all unit tests in the isolated test worktree, then verify first-run setup, rejected unauthenticated API access, successful login, refresh persistence, and logout before proceeding to Docker packaging. Use HTTPS (for example, the existing Tailscale HTTPS endpoint) when signing in over a network; plain HTTP does not protect passwords in transit.

## 2026-10-12 — Cassette app icon

- Used the user-provided vintage cassette image as the browser favicon and the app's header brand icon; also added it to the login/setup page.
- Current implementation references the provided Vecteezy-hosted image URL directly. Before final Docker packaging, preferably bundle a local copy under the app's static assets so the icon does not depend on external hosting. The image could not be fetched into the repository through the available runtime, so the URL remains external for now.
- No merge or deployment performed.


## 2026-10-12 — Rainbow cassette icon

- Replaced the previous cassette image URL in the favicon, app header, and login/setup page with the user-provided Vexels rainbow cassette image.
- **Local asset still pending:** the image is viewable through web browsing, but direct download from this runtime fails due to unavailable DNS/network access. The app still references the remote image; do not treat the icon as fully bundled for Docker yet. To complete the local-copy requirement, provide the PNG as a chat attachment or place it in the repository worktree, then update the page to reference the bundled static asset.
- No merge or deployment performed.


## 2026-10-12 — Bundle rainbow cassette icon locally

- Confirmed `cassette.png` is present at the repository root on PR #12's branch (31,390 bytes).
- Updated the favicon, login/setup image, and app header CSS to use the local `/assets/cassette.png` endpoint instead of the external Vexels URL.
- Added a FastAPI endpoint serving the repository-root PNG as `image/png`; this avoids external-host dependency. Docker packaging must include the root-level `cassette.png` file alongside the app source.
- No merge or deployment performed. Runtime/browser smoke test and CI for this change are still pending.


## 2026-10-12 — Project handoff documentation merged

- **PR:** [#14](https://github.com/abucalip/navi-librarian/pull/14), `docs: add project handoff and engineering runbooks`, merged into `main` via squash merge.
- **Merge commit:** `74264b29062504fce3bf6f7a65121fa43b9f8ec5`.
- **Files added:** `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/DECISIONS.md`, and `docs/TEST_PLAN.md`.
- **CI:** GitHub reported Python syntax check and Docker packaging validation passed for PR head `97e887fa8295fff55f05ac72101907bf08819a99`. This was documentation-only; no application tests or deployment were performed during the merge session.
- **Deployment:** still unverified. The previously reported GHCR `unauthorized` pull remains unresolved; do not treat merge/CI as deployment evidence.
- **Next:** review current PRs and local branches/worktrees before choosing the next implementation task; prioritize required regression testing and resolve GHCR package visibility/authentication before a registry-based deployment.


## 2026-10-13 — PR #21 and PR #22 merged; acquisition fixes verified

- **PR #21:** squash-merged at `049a1e94ea782fa473fc4f394711dda1afec6fbe`. Adds the sixth sortable FLAC Hi-Res priority, preserves saved ordering on settings migration, improves bounded slskd query fallback/diagnostics and source failover, and keeps polling while reported peer payloads are delayed. Search budget is 45 seconds; matching and import-safety rules remain unchanged.
- **Live test:** user tested the combined PR #21/#22 checkout and reports Tinariwen — `Idrache (Traces of the Past)` started downloading.
- **PR #21 CI:** Python syntax/acquisition-safety workflow #179 and Docker packaging workflow #86 passed on head `2d617091390f81c05ff6c40d5a8fa140c6217b68`, including the full unit suite and Docker image build.
- **PR #22:** squash-merged at `7d6094042f0beb4538313011594539a34254fbd9`. Explicit Get now reactivates a safely dismissed record only when the guarded persisted-state update succeeds, clearing stale candidate/settings before searching again. Added successful and failed reactivation regression tests and updated `docs/TEST_PLAN.md`.
- **PR #22 CI:** Python syntax/full unittest workflow #182 and Docker packaging workflow #89 passed on head `04a11671862e1e3544ac878760f2223a42058ed9`. The first CI attempt found the test fixture was invoking the real acquisition implementation; the fixture was corrected and final CI passed.
- **Verification boundary:** the live Tinariwen test is user-confirmed. No separate live retest of a previously dismissed acquisition was reported. No image publication or production deployment was performed.
- **Next:** session complete. Treat publishing/deploying the merged code as a separate task, and record the image digest plus running-app verification if requested.


## 2026-10-13 — PR #24 ambiguous exact-match fallback fixed

- **PR/branch:** [#24](https://github.com/abucalip/navi-librarian/pull/24), `refactor/acquisition-completion-matching`; open and unmerged.
- **Finding:** the matcher previously attempted collision-suffix fallback both when no exact file matched and when multiple exact files matched. The latter could allow a suffix alternative to conceal an ambiguous exact-name/size match.
- **Fix:** return `None` immediately when more than one exact match exists; only attempt collision suffixes when there are zero exact matches. Existing size validation and symlink exclusion remain unchanged.
- **Regression:** add case-variant exact-name files and a same-size suffixed alternative, asserting fail-closed behavior; skip only where the filesystem cannot represent distinct case variants. Add the scenario to `docs/TEST_PLAN.md`.
- **Commits:** code `b8fad33cfaad87b1ed8d2b4fc3d84166f396b15f`; test `e163a20fe4407491398ce56e1f4c9777f8aa53bf`; documentation commits follow on the PR branch.
- **Verification:** corrected head `86705c64cbd3d794082528d58d0fd2b49fcbc4c1` passed Python syntax workflow #198 and Docker packaging workflow #105. The Docker job confirms Python compilation, full unit tests, and image build succeeded. No local execution or manual UI verification was performed. No merge, image publication, or deployment is claimed.
- **Session close:** corrected-head CI passed and the full PR diff was reviewed for this extraction and edge case. The documentation records the verified scope and the boundary of testing. PR #24 remains open/unmerged; PR #23 remains separate/open. No local test run, manual UI verification, image publication, or deployment occurred.
- **Next priority:** assess PR #24 merge readiness and decide whether to merge; preserve PR #23 as a separate roadmap PR unless the dependency/order is explicitly revisited.


## 2026-10-13 — PR #24 merge session closeout

- **Final code merge:** PR #24 squash merge `225add7405bfd72b3254af23745d0dd9a84b621c`, from final PR head `b826ae14d917431d07aacf97200990d57133cba0`.
- **Documentation commits:** `docs/PROJECT_STATUS.md` closeout commit `7fe6cbb746fbeaae4addb35478f4cae54f451879`; this `PROJECT_LOG.md` entry is committed separately immediately afterward. The code merge and both documentation updates are on `main`.
- **Verification boundary:** final PR-head Python syntax workflow #202 and Docker packaging workflow #109 passed, including the full unit suite and image build. GitHub verified the merge and extracted module on `main`. No local test execution, manual UI verification, image publication, or deployment was performed.
- **Outstanding roadmap:** PR #23 (`docs/modularization-web-only-roadmap`) remains open/unmerged and separate from PR #24. Next implementation priority is M2: extract slskd search and quality evaluation into focused modules with regression tests, preserving fallback order, delayed-response polling, timeout budgets, and quality priority ordering.


## 2026-10-13 — PR #31–#33 verification and manual UI gate closeout

- **PR #31:** exact head `572d98d18e051bcbed7f3e74242abe1df6d0540c`; Python syntax and Docker packaging workflows passed. The uploaded manual UI report recorded eight items passing on application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`. Performance observation and a distinct error/recovery scenario were not separately recorded and remain deferred to the next UI-facing PR.
- **PR #32:** exact head `46db021db1367ef1e1f5e53dffdbd78bc09a880a`; Python syntax, container runtime smoke, Docker packaging, and validation-only multi-architecture workflows passed. This infrastructure/runtime-verification change does not require an additional manual browser run. Registry publishing remains paused.
- **PR #33:** exact head `22ee23d406284d59c37334f99883bb9e848bd929`; Python syntax and Docker packaging/full-unit-test workflows passed. Settings routes were extracted behind regression tests without intended UI contract changes, so no manual browser test is required for this PR. The local test helper's PR 33 account was confirmed to persist after a server restart; this is local-test evidence only.
- **Merge recommendation:** PR #33 is CI-ready but should follow PR #32, whose Docker image-content/runtime fix addresses a correctness gap on the base. Integrate PR #31's testing-gate documentation as part of this closeout. No PR was merged in this session; verify the exact head and checks again immediately before each merge.
- **Not performed:** no image publication, deployment, or production runtime verification. Do not treat local app persistence or CI as production verification.
- **Next:** reconcile/merge PR #32 and PR #31, then merge PR #33 if its head and checks remain valid. Run the complete manual checklist on the next UI-facing PR, explicitly recording performance and error/recovery results.


## 2026-10-14 — Authentication route extraction and CI closeout (PR #39)

- Added integration contract coverage in PR #38 (merged at `84da7ebfe51199a5caf63f7689fe89df8d61b553`) for setup validation, login/logout, throttling, cookie attributes, session persistence/tampering, and public/protected paths.
- PR #39 extracts auth status/setup/login/logout and the login page into `app/api/auth.py`; middleware and security primitives remain in their existing modules. Exact code head `a78272da8f82aa83716367aa7fcd7a43729267a7` passed all four required workflows: Python syntax, Docker packaging/full unit suite, container runtime smoke, and validation-only multi-architecture build.
- PR #39 is open/unmerged. Documentation updates in this closeout create a new PR head; exact-head CI must be checked again before merge. No local tests, manual browser testing, image publication, deployment, or production runtime verification were performed. Publishing remains disabled.
- **Next action:** verify all required checks on the documentation-updated PR head and review mergeability before deciding to merge.