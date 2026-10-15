## 2026-10-15 — Acquisition cleanup directory-swap hardening (verification pending)

- Safety audit found a time-of-check/time-of-use gap in `clean_acquisition_source`: the code preflighted a target folder, called external transfer lookups, then deleted via path-based operations. Replacing that folder with a symlink during the callback could redirect deletion outside the intended folder.
- The fix pins the verified directory through no-follow, descriptor-relative traversal, compares device/inode identities, and unlinks only verified basenames relative to the pinned directory. Added a regression that swaps the album folder for a symlink during transfer lookup and asserts both the outside target and moved original album files remain intact.
- Branch: `fix/acquisition-cleanup-directory-race`. Implementation and regression are committed; exact-head CI and focused/full test results are pending. No production data or deployment was touched.

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
- **Next:** pull and recreate only `navidrome-librarian` on the media VM, then verify container health and artwork in the deployed UI. Sync local Git without overwriting unrelated local changes.

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

Navidrome Librarian combines a web UI with existing music-discovery and acquisition logic in `navidrome_server.py`. The web app is served by FastAPI from `app/main.py`. It connects to an existing Navidrome instance and slskd service; neither is bundled into the app container.

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
