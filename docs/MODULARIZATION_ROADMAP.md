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
