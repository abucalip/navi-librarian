## 2026-10-15 — PR #136 merged: acquisition monitor payload preparation

- PR #136: https://github.com/abucalip/navi-librarian/pull/136. Final PR head `c963bb6a1510d86ebb2cfe5bb9514fccbc478efa`; squash merge `5f28823d0c279d49947912f9fbce0a160a7a5bc3`.
- Extracted repeated selected-source/fallback-source payload normalization from `_discovery_acquire_album_impl` into `acquisition_monitor_payload.py`; added direct-import regression tests for minimal file records, quality summary normalization, fallback metadata preservation, and input immutability. Docker packaging updated.
- All four required workflows associated with the exact final head succeeded: Python syntax, Docker packaging/full suite/build, container runtime smoke, and validation-only multi-architecture image validation (publishing paused).
- No separate local test execution, image publication, deployment, or production runtime verification is claimed.
- Next priority: safety/verification audit before routine modularization. Keep acquisition-dismissal HTTP 409 deferred unless it recurs; if it recurs, collect stage-specific evidence and review open diagnostic/defer PRs #44/#45 before modifying cleanup behavior.

---

## 2026-10-15 — Acquisition monitor payload extraction (PR preparation)

- Extracted repeated selected-source/fallback-source payload normalization from `_discovery_acquire_album_impl` into `acquisition_monitor_payload.py`.
- Added direct-import regressions for filename/size-only file records, quality summary normalization, preservation of fallback metadata, and no mutation of source candidates.
- The MCP-facing function and orchestration decisions remain in place; queue handling, cancellation/cleanup, shared locks, persistence, and watcher lifecycle were not moved.
- Dockerfile includes the new module. Exact PR head `f3d444fce0902637d394b48680e4274e2b513f6f` passed syntax `38780380213`, Docker packaging/full unit suite/build `38780380196`, runtime smoke `38780380199`, and validation-only multi-architecture image validation `38780380566` (publishing paused). Documentation updates create a new head, so all four checks must be re-verified on the final PR head before merge. No local test execution, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #134 merged: concurrent login rate-limit race

- PR: https://github.com/abucalip/navi-librarian/pull/134. Added a deterministic integration regression before implementation, then reserved each login attempt atomically under a dedicated lock while keeping password verification outside the lock.
- Regression-first test commit: `d829d6450ac39257a0177cf768e70a3de8937e7a`; implementation commit: `e7ff4b454d9478d4ca147913d356db545bfb2fed`.
- Final tested PR head: `a15fa4e9b588e7fa96d36242f51b55b23fba9e70`; all four required workflows passed: Python syntax `38776917077`, Docker packaging/test-and-build `38776916979`, container runtime smoke `38776917024`, and Docker image validation `38776917027` (publishing paused).
- Squash merge: `ef6ce0ff4faa9fffca66a7e43294eee6a0847dbd`. No local test execution, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #133 merged: malformed session token fail-closed regression

- Audited app assembly and auth integration; existing import-isolation coverage asserts that importing `app.main` does not initialize `navidrome_server`, and auth routes use dependency injection.
- Fixed `session_username()` so non-ASCII token segments and non-string inputs are rejected safely instead of leaking `UnicodeEncodeError`; regression test was committed before the implementation change.
- PR #133: https://github.com/abucalip/navi-librarian/pull/133. Exact tested head `60df367eb4004fe439d1abcd61957c5986111b90`; all four required workflows passed on that SHA: syntax `38775004824`, Docker packaging/test-and-build `38775004877`, container smoke `38775004963`, and image validation (publishing paused) `38775004827`.
- Squash merge: `ae49bacf3c793fac70688f55c2d1d7c9ed54cc13`. Post-merge workflows were queued at closeout; no local test run, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #131 merged: Get/request state reporting

- PR: https://github.com/abucalip/navi-librarian/pull/131
- Tested head: `7eb009c92821b6eb9dfb33326e7dfc3d81fd7244`; squash merge: `5fafad0b5a2d94ef2473c0a7c121d647cf8bdc76`.
- Unified the three Get/request control variants and fixed lost status messages, premature success state, and `ok: false` handling. API contract and acquisition semantics unchanged.
- Exact-head CI: syntax `38763416411`; Docker packaging `38763416267`; runtime smoke `38763416429`; image validation (publishing paused) `38763416356` — all passed.
- Manual report: https://github.com/abucalip/navi-librarian/pull/131#issuecomment-6196528875. All eight checklist items passed; no real download was triggered.
- No image publication, deployment, or production runtime verification.

## 2026-10-15 — PR #128 merged: acquisition status layout

- PR #128 (https://github.com/abucalip/navi-librarian/pull/128) merged by squash at `424929410b0324313e9aee5e59da73803d4b32bb`, from final head `653984684be4e2da28e6de6955b43299143f1141`.
- Acquisition cards now use a wider status-board composition appropriate for progress, transport details, quality profile, and actions; discovery layouts and backend/API behavior are unchanged.
- Manual report (https://github.com/abucalip/navi-librarian/pull/128#issuecomment-6195576007) records all eight acceptance checks passing on UI commit `4b2d30a510d5b850be25e059641eee29d9d7dde9`. After the report, a documentation-only conflict resolution corrected the UI backlog record; no UI files changed.
- All four required GitHub Actions workflows passed on final PR head `653984684be4e2da28e6de6955b43299143f1141`: syntax `38760144749`, container runtime smoke `38760144797`, Docker packaging `38760144678`, and image validation (publishing paused) `38760144644`.
- Status: implemented, manually tested on the UI commit, CI passed on final PR head, merged. Not published, deployed, or runtime-verified in production.

## 2026-10-15 — PR #124 merged: shared UI status states

- PR #124 (https://github.com/abucalip/navi-librarian/pull/124) merged by squash at `9a3aa7bd295de0de7d9408b01db22ab700e4d101`, from exact tested head `28e5a88ae362043171aaabb1f8667f6cf5ef10f7`.
- Standardized loading, empty, error, success, progress, and neutral status text using the existing design tokens and state glyphs; applied `aria-live` to dynamically updated status regions. No API, authentication, acquisition, or domain behavior changed.
- The published local manual report on PR #124 records all eight checklist items as PASS on the exact tested SHA, including first-run setup, dashboard/artwork, discovery, navigation/album details, settings secret handling, Get/request without a real download, acquisition cards, and no unexpected browser/server errors. Report: https://github.com/abucalip/navi-librarian/pull/124#issuecomment-6194989181.
- All four required GitHub Actions workflows passed on the exact PR head: Python syntax `38753222840`, container runtime smoke `38753222934`, Docker packaging `38753222902`, and validation-only image validation `38753222878` (publishing paused).
- A separate keyboard-focus reach issue was observed during verification (25 Tab presses reached only three dashboard controls); it remains unfixed and should be tracked as a focused UI follow-up by the front-end owner. The state-classifier remains heuristic.
- State: implemented, automated CI passed, manual browser checklist passed and report published, merged. No image publication, deployment, or production runtime verification is claimed.
- Next: prioritize the documented keyboard-focus reach defect for front-end follow-up; continue to keep publication/deployment as separate gates.

---

## 2026-10-15 — PR #114 merged: Proxmox MCP command execution guard

- Found a mismatch between `server.py`'s read-only/allowlist promise and its implementation, which forwarded arbitrary input to SSH. Prioritized this command-execution risk ahead of routine modularization.
- Added strict exact-match command validation and direct-import regression tests for approved diagnostics and malicious/disallowed inputs. Preserved the MCP tool signature and accepted-command SSH execution shape.
- PR #114: https://github.com/abucalip/navi-librarian/pull/114; exact tested head `cd8319696180875a3cb6f0dc151d88e0c8c490d7`; squash merge `6ab848d444373dfa37e6d46528a2840a53a8f763`.
- All four exact-head workflows passed: syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, validation-only multi-architecture validation `38740491281`.
- No local tests or live Proxmox command were run. The host-side MCP is not included in the application Docker image; no publication or deployment.
- Next: continue the highest-priority safety/verification audit. The previously deferred HTTP 409 investigation remains deferred unless the user reports recurrence.


---

## 2026-10-15 — PR #108 merged: discovery router service injection

- Replaced discovery router's import-time `navidrome_server` import with the shared lazy `get_librarian` dependency; kept route behavior and domain/MCP ownership unchanged.
- Added direct-import regression tests and migrated existing route tests to explicit fake-service injection after initial CI found six tests coupled to the removed module attribute.
- PR: https://github.com/abucalip/navi-librarian/pull/108
- Exact tested head: `a5170e50080c0ca94b4068155ace83fd33c6f029`; squash merge/main at merge: `be51f0ce17fe8eccd1b57714e869db69a5f1ba78`.
- All four required exact-head workflows passed: syntax/acquisition safety `38733725606`; Docker packaging/full suite/build `38733725816` (227 tests passed); container runtime smoke `38733725595`; validation-only multi-architecture image validation `38733725591`.
- No local tests, publication, deployment, or production runtime verification. Publishing remains paused.

---

## 2026-10-15 — PR #107 merged: acquisition router service injection

- **PR:** https://github.com/abucalip/navi-librarian/pull/107; final tested PR head `67174e8026f44382a4a6bea48ff1df80744dda35`; squash merge / main SHA at closeout `1cc15dd6343370ce0915bf7228a745d3558b393b`.
- **Change:** added `app/api/dependencies.py` with lazy `get_librarian()` and injected it into all acquisition routes. This removes the acquisition router's import-time import of `navidrome_server` while preserving endpoint paths/methods, existing service calls, payload mapping, HTTP error behavior, and SSE response headers. Added regression tests for route contracts, dependency wiring, fake-service handler calls, validation, and sanitized errors.
- **Exact-head CI:** all four required workflows passed on `67174e8026f44382a4a6bea48ff1df80744dda35`: Python syntax `38732084595`; Docker packaging/full unit suite `38732084663`; container runtime smoke `38732084579`; validation-only multi-architecture image build `38732084589`. An earlier test-only assertion failure on `d6a1696c06f594e2c4025e0eff54bb8496fd8e29` was corrected before these passing runs.
- **Status:** Implemented, tested, CI passed, merged. Publishing remains paused; this did not publish an image, deploy the application, or verify production runtime. `app/main.py`, discovery, and settings still import `navidrome_server`; MCP tools and domain logic were not removed or duplicated.
- **Next priority:** continue the narrow web service-injection audit at the discovery router, preserving API behavior and MCP compatibility. Keep deployment/runtime verification as a separate gate; do not resume routine modularization if a higher-priority safety or delivery gap appears.

---

## 2026-10-15 — Read-only web dependency audit

- Audited current `main` after the acquisition import source-root fix. `app/main.py` and three API routers import `navidrome_server` as `librarian`; route modules call the existing service wrappers rather than reimplementing domain logic.
- Main-app dependencies include `DATA_DIR`, settings read/write, Navidrome ping, discovery-list retrieval, and album-candidate filtering. Acquisition routes call status/skip/dismiss/acquire/queue wrappers; discovery routes call recommendation/list/refresh/feedback wrappers; settings routes call provider get/set/test wrappers.
- Metadata routes are independent of `navidrome_server`; auth route handlers are dependency-injected already, although the app assembly supplies their settings and signing dependencies from the server boundary.
- No code was changed. PR #44/#45 remain open; the user's documented decision to defer the dismissal HTTP 409 investigation until recurrence was respected. Next candidate: a narrow app/router service-dependency seam, with no MCP/domain behavior removal until contract tests prove parity.

---

## 2026-10-15 — PR #103 merged: acquisition import source-root safety

- **PR:** [#103 — fix: pin acquisition import source directory](https://github.com/abucalip/navi-librarian/pull/103) — merged.
- **Squash merge commit:** `cf40df35a76d669421dcddbafd21ea22652bd0b1`; exact tested PR head `9de78c268af1b640a2a08afecb25a22502322a85`.
- **Changes:** pinned source and destination-parent directory chains with no-follow descriptors; added descriptor-relative staging, track moves, cross-filesystem copy fallback, and rollback; added source-root swap, collision-suffix, cross-filesystem, and rollback regressions.
- **Exact-head CI:** syntax/acquisition safety `38726626891`, Docker packaging/full unit suite/build `38726626846`, container runtime smoke `38726626956`, validation-only multi-architecture image validation `38726626910` — all successful.
- **Limitations:** no separate local test run, production-folder test, image publication, deployment, or production runtime verification. Publishing remains paused.

---

## 2026-10-15 — PR #100 merged: cleanup root path traversal hardening

- **PR:** [#100 — fix: pin acquisition cleanup root without symlink traversal](https://github.com/abucalip/navi-librarian/pull/100) — merged.
- **Squash merge commit:** `6e8e861cc84d5951b0d177ffea256a0dd88fe4b4`; exact tested PR head `89813bd3802b1f8920715aaeca55ccb5e461c9c9`.
- **Changes:** extended PR #99's descriptor-relative cleanup by walking the absolute configured root component-by-component with no-follow flags, checking root identity, verifying the exact planned file set and file identity/size, and adding a parent-directory symlink-swap regression.
- **Exact-head CI:** syntax/acquisition safety `38724953760`, Docker packaging/full unit suite/build `38724953699`, container runtime smoke `38724953828`, validation-only multi-architecture image validation `38724953678` — all successful.
- **Limitations:** no separate local test run, production-folder deletion test, image publication, deployment, or production runtime verification. Publishing remains paused.

---

## 2026-10-15 — PR #99 merged: acquisition cleanup directory-swap hardening

- **PR:** [#99 — fix: harden acquisition cleanup against directory swaps](https://github.com/abucalip/navi-librarian/pull/99) — merged.
- **Squash merge commit:** `6a5d42148813d3b2725f5d79ca45bdecaee97c25`; exact tested PR head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- **Changes:** replaced path-based post-callback deletion with no-follow directory-descriptor traversal, device/inode identity checks, descriptor-relative unlink/rmdir, and a regression for a symlink swap during transfer lookup.
- **Exact-head CI:** syntax/acquisition safety `38724377954`, Docker packaging/full unit suite/build `38724378021`, container runtime smoke `38724378097`, validation-only multi-architecture image validation `38724377870` — all successful.
- **Limitations:** no separate local test run, production-folder deletion test, image publication, deployment, or production runtime verification. Publishing remains paused.

---

## 2026-10-15 — PR #98 merged: acquisition request coordinator

- **PR:** [#98 — refactor: extract acquisition request coordinator](https://github.com/abucalip/navi-librarian/pull/98) — merged.
- **Squash merge commit:** `ae6635573aa57eb9303909701e6f0a5834066495`; exact tested PR head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- Extracted the top-level `discovery_acquire_album` decision sequence behind injected dependencies, preserved the MCP/web adapter contract, and added direct-import regression tests and Docker packaging.
- All four workflows passed on that exact PR head: syntax/acquisition safety `38723927107`, Docker packaging/full unit suite `38723927072`, runtime smoke `38723927058`, and validation-only multi-architecture validation `38723927057`. No local test run, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #97 merged: Last.fm settings policy

- **PR:** [#97 — refactor: extract Last.fm settings policy](https://github.com/abucalip/navi-librarian/pull/97)
- **Branch:** `refactor/lastfm-settings-policy-direct-import`
- **Exact tested PR head:** `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`
- **Merge commit:** `ad239a59b77612b812ca842406fee7b47cf80889`
- **Changes:** moved Last.fm API-key trimming, blank-key preservation, settings-write invocation, and configured-status serialization to `service_settings.py`; retained the MCP/web adapter contract and SQLite ownership in `navidrome_server.py`; added direct-import regression coverage; updated architecture, roadmap, status, test plan, and log.
- **Exact-head CI:** syntax/acquisition safety `38721333335`, container runtime smoke `38721333332`, validation-only multi-architecture `38721333418`, Docker packaging/full unit suite `38721333353` — all completed successfully on the exact PR head.
- **Boundaries:** no separate local test run, image publication, deployment, or production runtime verification. Publishing remains paused.
- **Next:** inspect current GitHub main, roadmap, open PRs, and relevant tests; prioritize unresolved safety/test/verification gaps before another routine extraction.

---

## 2026-10-15 — PR #96 slskd settings-policy extraction

- PR #96 opened: [refactor: extract slskd settings policy](https://github.com/abucalip/navi-librarian/pull/96), branch `refactor/slskd-settings-policy-direct-import`.
- Extracted `_slskd_config`, slskd settings serialization, and update validation into `service_settings.py` with injected settings and music-directory callbacks. Legacy MCP function names/signatures and JSON payloads remain adapters. SQLite persistence, network connection testing, and runtime path ownership remain in `navidrome_server.py`.
- Added direct-import coverage for blank-key preservation, secret redaction, URL and quality tier validation, invalid path/no-write behavior, and callback updates. Migrated quality-priority policy tests away from AST-executing the adapter; retained AST persistence helpers for SQLite-specific coverage.
- Exact tested head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four required workflows: syntax/acquisition safety `38665710740`, Docker packaging/full suite `38665710718` (208 tests passed), runtime smoke `38665710761`, and validation-only multi-architecture `38665710769`. The first CI attempt revealed a test harness that lacked the new adapter dependency; after moving the tests to the direct-import policy, all four workflows passed.
- No local tests, publication, deployment, or production runtime verification. Publishing remains paused.
- Final docs update requires a new exact-head CI cycle before merge. PR #96 is open, not merged.

---

## 2026-10-15 — PR #95 merge verification correction and next task

- Correction to the earlier session-closeout note below: PR #95 was subsequently verified on its actual final head `92d304d06713ec0f73253a5db48cf835ff93a063`, not the earlier documentation-recorded head `b0a9d4df97723bc05983fb362a9b3060587f0df9`. All four required workflows passed on `92d304d06713ec0f73253a5db48cf835ff93a063`: syntax/acquisition safety `38665121156`, Docker packaging/full unit suite `38665121160`, runtime smoke `38665121170`, and validation-only multi-architecture `38665121255`.
- PR #95 merged to main at `2193306ce6ee2ff3ed087b2f490594f2d5ee2c68`. No image publication, deployment, or production runtime verification.
- Next implementation: extract slskd settings/config policy into direct-import `service_settings.py`, retaining the existing MCP/web wrappers and leaving network checks, SQLite persistence, and runtime path ownership where they are.

---

## 2026-10-15 — Service settings policy extraction (PR #95)

- Implemented on branch `refactor/service-settings-policy-direct-import`, PR #95. New `service_settings.py` owns six injected settings-policy/configuration functions. Existing MCP/web wrappers in `navidrome_server.py` retain names/signatures and delegate to the module.
- Replaced AST execution in `tests/test_service_settings.py` with direct-import tests for secret redaction, blank-password preservation, invalid URL/user/path no-write behavior, library-path update callback, and ListenBrainz validation. Dockerfile now includes the module.
- Reviewed the focused implementation diff and the exact final PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9`. All four required workflows passed on that exact head: syntax/acquisition safety `38664285319`, Docker packaging/full unit suite/build `38664285227`, container runtime smoke `38664285195`, and validation-only multi-architecture image validation `38664285194` (publishing paused). The initial callback-injection mismatch was caught and corrected in an earlier CI cycle. No local tests were run.
- PR #95 remains open and mergeable, not merged. No image publication, deployment, or production runtime verification is claimed.
- Session closeout: docs reconciled to the verified final-head evidence. Next action is review PR #95's full diff and checks, then decide whether to merge; after that, continue the next narrow service-boundary extraction while preserving MCP compatibility.

---

## 2026-10-15 — Web dependency audit and settings extraction seam

- After PR #93 merged at `e5d908b11e2a70e8294d0781c630238d4361e503`, audited the current GitHub `main` web/entry-point dependency graph and relevant docs/tests.
- `app/main.py` and the acquisition, discovery, and settings routers import `navidrome_server.py`; calls span shared settings persistence, Navidrome API access, discovery list/recommendation behavior, acquisition lifecycle, and service configuration/connectivity. The import also loads MCP tool registration. `server.py` is a separate MCP entry point; the Dockerfile does not copy/run it, while `requirements.txt` pins MCP.
- Identified the smallest existing AST-coupled seam: six service-settings/configuration functions in `tests/test_service_settings.py`. Proposed next step is to extract these into an importable settings-policy module with injected storage/path dependencies, preserve legacy MCP/web adapters, and keep database initialization, global path updates, and live network checks out of scope.
- Audit only: no code/tests changed and no local tests run. PR #93's four required workflows passed on exact head `616c4af7fb17c3d287fca596ddcbba09f7fd7736`; merged main is `e5d908b11e2a70e8294d0781c630238d4361e503`. Main merge-commit CI must be checked independently; no image publication/deployment/runtime verification claimed.
- Next: implement the narrow settings-policy extraction with direct-import regression tests.

---

## 2026-10-15 — Acquisition lifecycle AST-boundary audit

- Based on GitHub `main` `c6017f7a59e2aaec09e498ca4bda9315b0325cd3`, reviewed the remaining AST-coupled cases in `tests/test_acquisition_safety.py` against direct-import orchestration/lifecycle/watcher/import/recovery tests.
- No test migration was made because each remaining case protects an integration boundary: simultaneous request reservation under the shared transition lock; persistence-before-filesystem-import; top-level refusal for incomplete saved candidates; explicit dismissed-job Get success and refusal; stale watcher recovery without requeue; and broad-query retry sequencing/result diagnostics.
- Existing direct helper tests remain useful complementary coverage, not substitutes for the coordinator-level assertions. No production behavior changed and no local tests were run.
- Baseline `main` `c6017f7a59e2aaec09e498ca4bda9315b0325cd3` has all four required workflows green (syntax, Docker packaging/full suite, runtime smoke, validation-only multi-architecture; publishing paused). This does not validate the documentation branch.
- Next: read-only audit of web and entry-point dependencies on `navidrome_server.py`, then select one narrow independently tested service boundary. MCP retirement remains deferred until all web callers and compatibility needs are verified.

---

## 2026-10-15 — PR #92 merged: dismissed-acquisition preflight extraction

- PR: https://github.com/abucalip/navi-librarian/pull/92
- Branch: `refactor/extract-dismissed-reactivation-preflight`; exact tested head: `1f0ce2174e1e60f3aab7c898dd534b8b1f11e858`; squash merge / updated main commit: `60698f7bf1413e4c643309e200d1ace2e268bee3`.
- Extracted dismissal detection, retry-metadata normalization, and conditional reactivation decision into the injected orchestration helper. The server retains the shared transition lock and existing refusal response; state-store conditional update and stale-source clearing are unchanged.
- Added four direct-import regression cases and retained AST-level explicit-Get success and failed-reactivation refusal cases.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety `38661883721`, Docker packaging/full suite `38661883755` (203 tests), runtime smoke `38661883730`, and multi-architecture validation `38661883723` with publishing paused.
- Initial namespace-alias defect was caught by the acquisition-safety workflow and fixed before final verification. The final documentation-inclusive PR head passed all four workflows.
- No image publication, deployment, or production runtime verification. PR merged; project status, test plan, roadmap, and log updated on main.
- Next priority: continue the acquisition lifecycle AST-coupled test audit; keep direct helper tests paired with top-level integration tests for transition boundaries.

---



## 2026-10-15 — PR #90 merged: atomic acquisition reservation

- PR: https://github.com/abucalip/navi-librarian/pull/90
- Exact tested PR head: `c0b4a0ebcc5fa4ef8b71441fb38d55aed8fce097`; squash merge / updated `main`: `4756ad6a7669ab77e284309ca9cd0f178e7f032a`.
- Extracted the active-request identity check/add into `acquisition_orchestration.reserve_acquisition_request`; the coordinator retains the shared transition lock so existing-state checks and reservation remain one atomic decision.
- Direct tests cover new reservations, duplicate refusal without mutation, and preserving other active identities. `run_reserved_acquisition` retains callback result/exception behavior and guaranteed cleanup.
- All four required workflows passed on the exact PR head: syntax/acquisition safety `38659706561`, Docker packaging/full suite `38659706115` (199 tests), runtime smoke `38659706074`, and multi-architecture image validation with publishing paused `38659706150`.
- No publication, deployment, or production runtime verification. Next: a focused dismissal/reactivation preflight extraction with wrapper-level success/failure coverage preserved.

---

## 2026-10-15 — PR #84 verification closeout

- Exact PR head `398486476aacdbbefefeaee5cb79182cc0835fb8` passed all four required workflows: syntax/acquisition safety run 38656927551, Docker packaging/full unit suite run 38656927436, runtime smoke run 38656927801, and validation-only multi-architecture image run 38656927516.
- Full unit-test and acquisition safety regression steps passed. Diff reviewed: threaded watcher-start race test plus documentation only; no production changes.
- Merge pending final status confirmation. No image publication, deployment, or production runtime verification.

---

## 2026-10-15 — Session closeout: acquisition AST-test audit handoff

- Reconciled project documentation against GitHub `main` at `f46b3618eaa8abc98b7f077698439b304a0005b7`; PR #82 is merged and the four relevant documents now agree on the next task.
- PR #82 is documentation-only, with no new application test result. Publishing remains paused; no deployment or production runtime verification is claimed.
- Next action: continue the acquisition lifecycle AST-test audit across duplicate-request reservation/concurrency, incomplete persisted candidate details, dismissed-job reactivation/refusal, and stale watcher recovery. Retain unique coordinator, lock/race, persistence-transition, and recovery integration assertions.

## 2026-10-15 — PR #82 merged: reconcile acquisition audit closeout

- PR #82: https://github.com/abucalip/navi-librarian/pull/82
- Exact tested head: `5fdad1045ba04db84aea05a477a51dce38733f5c`; squash merge: `f46b3618eaa8abc98b7f077698439b304a0005b7`.
- Reconciled `docs/PROJECT_STATUS.md`, `PROJECT_LOG.md`, `docs/TEST_PLAN.md`, and `docs/MODULARIZATION_ROADMAP.md` after PR #81 merged; the next engineering task remains the acquisition lifecycle AST-test audit.
- All four required workflows passed on the exact tested head: Python syntax `38656400677`, Docker packaging `38656400827`, container runtime smoke `38656400743`, and Docker image validation with publishing paused `38656400766`.
- Documentation-only; no new application tests were run. No publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #78 merged: dismissal-serialized import guard

- PR #78 squash-merged at `5d638c7adf5a42fdac8052cb4fc223236564cd72` from exact tested head `e6a609ca7381d0751d529b52f55aeebd56d76661`.
- Extracted the existing dismissal check + import callback guard into `acquisition_orchestration.import_source_unless_dismissed`, with the transition lock held for the full callback. Filesystem safety and persistent status semantics were not moved or changed.
- Added direct tests for lock ordering, dismissal refusal, result propagation, and exceptions; retained the status-persistence failure integration test.
- All four required workflows passed on the exact head: syntax `38653493244`, Docker packaging/full unit suite `38653493312`, runtime smoke `38653493285`, and image validation with publishing paused `38653493279`. Full suite: 186 tests passed.
- No live slskd, publication, deployment, or production runtime verification is claimed.

---


## 2026-10-15 — PR #76 merged: slskd search polling extraction

- PR #76 squash-merged at `a55a9fa7eed1e221f52434b50f44d0c415fd491a` from exact tested head `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6`.
- Extracted progressive query submission, polling, response/file count aggregation, delayed payload waiting, payload deduplication, and per-query diagnostics into `slskd_search_polling.py`. HTTP, time, ID generation, and response normalization are injected. The server coordinator still owns candidate interpretation, status reporting, queueing, and acquisition state.
- Direct-import regressions cover fallback queries, delayed payloads, 404/405 compatibility, and unexpected HTTP error propagation. The AST end-to-end retry test remains.
- All four required workflows passed on the exact head: syntax `38652846800`, Docker packaging/full unit suite `38652846779`, runtime smoke `38652846790`, and image validation with publishing paused `38652846819`; full suite reported 184 tests.
- No local standalone test command, live slskd, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #73 merged: candidate extraction direct-import test

- PR #73 squash-merged at `df2f79b3d18df7d13484f7e3b5e7f550a39323d3`; exact tested PR head `a33772ca1da0b6628da490b69f1dc305b6794de3`.
- Migrated the Tinariwen/Idrache folder-variant candidate grouping/ranking scenario from `tests/test_acquisition_safety.py` to `tests/test_slskd_candidates.py`, exercising the extracted search algorithm with production helpers. No production code changed.
- All four required workflows passed on that exact head: syntax `38652066842`, Docker packaging/full unit suite `38652066649`, runtime smoke `38652066755`, and Docker image validation with publishing paused `38652066683`.
- No standalone local test command, live slskd interaction, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-14 — PR #72 merged: pure slskd search-helper test migration

- PR #72 squash-merged at `6c6157a8238691b18d2209ea2d2e1306385ec9a2`; exact tested PR head `17be72e52b39e63cad63391fb2c4e63ea55d3c26`.
- Added direct-import regressions in `tests/test_slskd_search.py` and removed six redundant pure-helper cases from `tests/test_acquisition_safety.py`. Acquisition retry/wait and candidate extraction remained covered at that point.
- All four required workflows passed on the exact tested head: syntax `38651547240`, Docker packaging/full unit suite `38651547229`, runtime smoke `38651547283`, and Docker image validation with publishing paused `38651547264`.
- No standalone local tests, live slskd interaction, publication, deployment, or production runtime verification is claimed.

---

## 2026-10-14 — PR #71 merged: candidate-start validation extraction

- PR: https://github.com/abucalip/navi-librarian/pull/71; branch `refactor/extract-candidate-start-validation`.
- Tested PR head: `f53e8ceffc8307c7b8dbcbf837e123b51671bbda`; squash merge commit: `b10650aa6a8889610b5734c5a1cf02c3197f1ad0`.
- Extracted `acquisition_candidate_start.py` with injected transfer lookup, HTTP, and timing dependencies; retained `_slskd_candidate_start_state` as a compatibility adapter. Added direct tests for traversal, mixed directories, active transfers, cancellation, and fail-closed uncertain outcomes.
- All four required workflows passed on exact PR head: syntax `38648719075`, Docker packaging/full unit suite `38648719066`, runtime smoke `38648719107`, and Docker image validation (publishing paused) `38648719074`.
- No standalone local tests, live slskd interaction, image publication, deployment, or production runtime verification claimed.
- Next: continue auditing AST-coupled tests, preserving acquisition coordination and persistence safety coverage.

- Branch `refactor/extract-candidate-start-validation` is based on post-PR #70 main commit `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161`.
- Extracted the candidate-start validator into `acquisition_candidate_start.py`, retaining the server adapter and injecting external dependencies for isolated tests.
- Migrated traversal and mixed-directory tests out of the AST harness and added direct tests for active transfers, successful cancellation, and uncertain cancellation/lookup outcomes.
- CI, focused tests, full suite, and final diff review remain pending until run on the exact PR head. No local execution or live slskd test is claimed.

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
- **Branch / tested PR head:** `docs/frontend-design-guide` / `a31997baa65d02b36ea7b85aaf6bab52ddfbeee5`.
- **Squash merge commit:** `fd9ceb17480e08e84d2e93ab84defb32c7af1b0a`.
- Added `docs/FRONTEND_DESIGN_GUIDE.md` as the canonical agent-independent design specification and backlog. Root `AGENTS.md` requires front-end agents to read it; development workflow and test plan link to it.
- The guide preserves the dark-grey/yellow/red identity, Barlow Condensed / IBM Plex Sans / IBM Plex Mono typography, anti-patterns, Impeccable critique workflow, accessibility/responsive expectations, front-end ownership boundaries, and prioritized backlog. Login alignment is complete; state craft is next.
- All four required workflows passed on the exact PR head: container runtime smoke (run `38644811862`), Python syntax (`38644811890`), Docker image validation with publishing paused (`38644811875`), and Docker packaging (`38644811793`).
- Documentation-only change; no local tests or manual browser verification were run. No image publication, deployment, or runtime verification is claimed.
---

## 2026-10-14 — Queue failure classification test migration in progress

- Branch `test/migrate-queue-failure-classification` starts from GitHub `main` at `23798189e058c97a2080c64ae6ad6468b0ce3645`.
- Removed the AST-harness's two `_slskd_queue_failure_action` cases and stopped AST-compiling its thin compatibility wrapper. The production wrapper delegates to `acquisition_lifecycle.queue_failure_action`; `tests/test_acquisition_lifecycle.py` already tests the real policy directly for explicit retryable rejections, fatal authentication failures, uncertain HTTP statuses, and transport failures.
- This is a test-only migration. No production code, acquisition semantics, cleanup/import behavior, or safety checks changed.
- Focused tests, full suite, syntax checks, exact-head CI, and final diff review are pending. No tests are claimed to have passed at this point.
- Next: verify the migration and continue the AST-harness audit incrementally without dropping safety coverage.

## 2026-10-14 — PR #64 merged: queue dismissal test migration

- PR #64 `test: migrate queue dismissal regression from AST harness` was squash-merged to `main` at `1596161aa525896d43c37c85533e8056a742439b`; exact tested PR head `3bde365e43acbe1cc95f68d7014d899046e735f6`.
- Removed the redundant AST queue-dismissal case, its adapter shim, and the now-unused HTTP queue helper. Equivalent direct-import coverage remains in `tests/test_acquisition_orchestration.py` for dismissed refusal, shared-lock ordering, return propagation, and exception propagation.
- All four required workflows passed on the exact final head: syntax `38636360130`, Docker packaging/full unit suite/build `38636360145`, container runtime smoke `38636360164`, and validation-only multi-architecture build `38636360139` (publishing paused).
- Test-only change; no separate local test run, live slskd, production filesystem operation, publication, deployment, or production runtime verification is claimed.
- Next: continue the highest-priority acquisition coordination/test migration audit, preserving every safety invariant and direct-import regression.

## 2026-10-14 — Acquisition queue guard test migration

- Branch `test/migrate-queue-dismissal-regression` starts from current GitHub `main` after PR #62 and the ZCode ownership handoff.
- Removed the AST-harness test for dismissed queue refusal and its adapter shim from `tests/test_acquisition_safety.py`. The extracted implementation is already exercised directly in `tests/test_acquisition_orchestration.py`, including dismissed refusal, critical-section ordering, return value, and exception behavior.
- Test-only change; no production code, deletion/import logic, or safety checks changed. Exact-head CI and final diff review are required before merge. No local test execution, live slskd test, publication, deployment, or production runtime verification is claimed.
- Next: continue migrating remaining AST-coupled safety cases incrementally where direct-import production-module coverage exists or can be added safely.

## 2026-10-14 — PR #62 merged: acquisition queue/dismissal guard

- **PR:** https://github.com/abucalip/navi-librarian/pull/62
- **Branch:** `refactor/acquisition-queue-guard`; exact tested head `4e121eb7977bb1a51ad31f9c87d0d4984497af4d`.
- **Squash merge commit:** `d4a16e80f6978a58c3305bf341e370ba9708bb34`.
- **Reviewed diff:** eight files. Extracted queue/dismissal coordination into `acquisition_orchestration.py`; retained the legacy server adapter, HTTP request construction, shared transition lock, and dismissal predicate. Added direct-import regressions for lock scope, dismissal refusal, return propagation, and exception propagation. Retained the AST safety regression. Updated modularization roadmap, test plan, and project status.
- **Exact-head CI:** Python syntax `38619152587`; Docker packaging/full unit suite/build `38619152213`; container runtime smoke `38619152754`; validation-only multi-architecture image `38619152728`. All four succeeded. Publishing remains paused.
- **Verification boundaries:** no separate local helper/manual slskd test, production filesystem operation, image publication, deployment, or production runtime verification was performed or claimed.
- **Next:** continue the acquisition-coordination audit and migrate remaining AST-coupled safety tests incrementally, prioritizing correctness and verification.

## 2026-10-14 — PR #61 merged: acquisition transition guard

- **PR:** https://github.com/abucalip/navi-librarian/pull/61
- **Branch:** `refactor/acquisition-transition-guard`; exact tested PR head `aa554ff2be2a19e215538ed2e699b8036764dca1`.
- **Merge commit:** `73172847535d3683facfbe559706c26a8637a3d4` (squash merge).
- **Diff reviewed:** seven files. Extracted dismissal-serialized source switching into `acquisition_orchestration.py`, preserved the legacy server adapter and shared transition lock, and added direct-import regression tests for critical-section ordering, dismissal refusal, return-value preservation, and exception propagation. Updated roadmap, status, test plan, and project log.
- **Exact-head CI:** Python syntax/acquisition safety `38617537652`, Docker packaging/full unit suite/build `38617538490`, container runtime smoke `38617537978`, and validation-only multi-architecture build `38617538229` all succeeded on `aa554ff2be2a19e215538ed2e699b8036764dca1`; publishing remains paused.
- **Safety/verification limits:** no queue, cleanup, persistence, or filesystem algorithm was changed. No separate local test run, live slskd interaction, production filesystem operation, publication, deployment, or production runtime verification is claimed.
- **Next:** continue the highest-priority acquisition-coordination audit and move remaining AST-coupled safety coverage to direct-import tests without weakening invariants. HTTP 409 investigation remains deferred until recurrence.

## 2026-10-14 — Acquisition transition guard extraction proposed

- Branch: `refactor/acquisition-transition-guard`, based on current GitHub main after PR #60 merge.
- Extracted the dismissal-serialized source-switch guard into `acquisition_orchestration.py`; the legacy server function remains a compatibility adapter.
- Added direct-import regression tests for critical-section ordering, refusal to switch after dismissal, return-value preservation, and exception propagation.
- Safety boundary: both the dismissal check and callback remain under the existing shared transition lock. No live queue, cleanup, persistence, or filesystem behavior was changed.
- Exact-head CI and final review are pending. No local test execution, live slskd test, publication, deployment, or production runtime verification is claimed.

## 2026-10-14 — PR #59 merged: acquisition state persistence

- **PR:** https://github.com/abucalip/navi-librarian/pull/59
- **Branch:** `refactor/acquisition-state-store`; exact tested PR head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d`.
- **Merge commit:** `730ae16e613f3962c488f87c8de54034db7463dd` (squash merge).
- **Diff review:** nine files; added `acquisition_state.py`, retained legacy save/list functions as compatibility adapters, added direct-import persistence regressions, updated Docker packaging, and revised architecture/roadmap/test/status docs.
- **Exact-head CI:** compile `116019930318`, test/build `116019925188`, container smoke `116019924747`, and validation-only multi-architecture `116019926066` all succeeded on `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d`. Publishing remains paused.
- **Safety:** transition locking, dismissed-state conditional writes, secondary feedback projection, dismissal/import coordination, and filesystem safety were not moved or weakened.
- **Limits:** no separate local test run, live slskd test, production filesystem action, image publication, deployment, or production runtime verification.
- **Next:** re-inspect main and open PRs, then follow the highest-priority unresolved requirement in the roadmap.

## 2026-10-14 — Acquisition state persistence extraction proposed

- Branch: `refactor/acquisition-state-store`, based on GitHub main `066fff8e7ef88364b1dc9cc909bfb2722118880e`.
- Extracted SQLite save/list mechanics for acquisition rows into `acquisition_state.py`, preserving legacy server functions as adapters and adding direct-import persistence tests. Docker packaging and architecture, roadmap, test plan, and project status documentation updated.
- Explicitly retained the shared transition lock, dismissed-state conditional checks, secondary feedback projection, dismissal/import coordination, and filesystem safety logic in `navidrome_server.py`.
- Initial CI on `2e7ef60177ff61cb080dfad9fa422773938159ef` caught a test fixture mismatch for JSON `null`; corrected the fixture only on `29c5e6a460f1f61296680af7b1230fd5561496b4`. All four required workflows passed on that corrected code head: test/build `116019140196` (180 tests passed), compile `116019144533`, container smoke `116019141476`, and validation-only multi-architecture `116019141889` (publishing paused). Documentation closeout now requires all four workflows on the new exact PR head, followed by final diff review. No separate local test run, merge, publication, deployment, or production runtime verification is claimed.

## 2026-10-14 — Acquisition watcher startup extraction proposed

- Branch: refactor/acquisition-watcher-startup from GitHub main.
- Scope: move watcher reservation, persisted downloading state, safe-settings persistence, and thread-start failure handling into acquisition_watcher_startup.py; keep the legacy function as a compatibility adapter and package the new module in Docker.
- Regression coverage: direct-import cases cover dismissal/duplicate suppression, credential filtering, persistence failure reservation cleanup, and thread-start failure status cleanup. Focused and full tests, four exact-head workflows, final diff review, and docs verification remain required.
- Exact-head CI passed on the final documentation-updated PR head 3f072159ef9e61f70554d315277a612005b8de4e: Python syntax/acquisition safety 38609940832, Docker packaging/full unit suite/build 38609940860, container runtime smoke 38609940739, and validation-only multi-architecture build 38609940737 (publishing paused). Historical note: PR #58 was open and unmerged at the time this entry was written; it was subsequently merged to main at `066fff8e7ef88364b1dc9cc909bfb2722118880e` after all four required workflows passed on exact tested head `3f072159ef9e61f70554d315277a612005b8de4e`. No separate local test run, live slskd test, merge, publication, deployment, or production runtime verification is claimed.

## 2026-10-14 — PR #57 merged: acquisition watcher lifecycle

- **PR:** https://github.com/abucalip/navi-librarian/pull/57
- **Branch:** refactor/acquisition-watcher-domain
- **Exact tested PR head:** f4b92a98bae942ac6080316c3f1803d1b6bcff76
- **Merge commit:** ae1e8b8f582c0ca0b882566d883d9a68bb2ca589
- **Diff review:** eight files. Extracted the watcher loop into acquisition_watcher.py with injected dependencies; preserved the existing _discovery_watch_and_import_album compatibility adapter; packaged the module in Docker; added direct-import regression tests and updated lifecycle docs.
- **Exact-head CI:** Python syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, container runtime smoke 38605511271, validation-only multi-architecture build 38605510906 (all succeeded; publishing paused).
- **Failure and correction:** the first CI attempt caught a test assertion looking for status details in keyword arguments rather than the fourth positional argument. The test was corrected and all four workflows passed on the final tested head.
- **State:** implemented, tested in CI, CI passed, merged. Not published, deployed, or production-runtime-verified. No assistant-local test run, live slskd test, or production filesystem action is claimed.
- **Next:** extract persistent acquisition-state coordination and watcher startup behind tested interfaces while preserving MCP callers, safe import coordination, and cleanup refusal behavior.

## 2026-10-14 — PR #50 acquisition orchestration merged

- **PR:** https://github.com/abucalip/navi-librarian/pull/50
- **Branch:** `refactor/acquisition-orchestration-reconstructed`
- **Verified PR head:** `c8610fdc44ea93bcfb55a654598792aee78e7ecb`
- **Merge commit:** `a37d29cf11657dce6d5cbc6cb928ca840fe5b206`
- **Diff reviewed:** nine files; extracted persisted source-skip transition into `acquisition_orchestration.py`, preserved the MCP adapter, shared transition lock and conditional `status='downloading'` write, added direct regression tests, included the module in Docker packaging, and updated focused docs.
- **Exact-head CI:** Python syntax run `38589006636`, Docker packaging/full unit suite `38589006609`, container runtime smoke `38589006569`, and validation-only multi-architecture image validation `38589006620` all succeeded on the exact final PR head.
- **Review gate:** GitHub reported the PR open, ready, and mergeable; no review submissions or inline review threads were present. Squash merge completed successfully.
- **Verification boundaries:** no separate local test run is claimed. The multi-architecture image was validated with publishing paused. No image publication, deployment, or production runtime verification occurred.
- **Remaining work:** watcher orchestration, source switching, cleanup execution, interrupted-import recovery, and top-level acquisition coordination remain on the roadmap. Next, inspect the roadmap priorities and select the highest-priority unresolved requirement.


## 2026-10-14 — Safety-first acquisition dismissal verification

- Started branch `test/acquisition-dismissal-safety` from current GitHub `main` (`95fbce1654209368af82989efe87bc38fa3f02e2`).
- Added six regression cases around `_discovery_cancel_and_clean_source` for verified cleanup, unrelated files, traversal, ambiguous duplicate folders, symlink targets, and cancellation failure. The change is test-only; no cleanup safeguards were relaxed.
- Exact test commits: `6f35761504ca86702ec3863cc44d9fd8699d347b`, then `d8bffdf0989c530994a4ac9e01a8ab6a0a46dcdc` to correct the ambiguous-folder fixture.
- Initial exact-head CI on `b8e1c9a398853851e1a8140a9724600800f42c3b` exposed a test harness collision: loading the real cleanup helper replaced a stub expected by an existing source-switch test. The helper now has a distinct AST namespace name, preserving isolation; corrected-head CI and review remain pending. The reported HTTP 409 remains deferred because it was not reproduced. No merge, publication, deployment, or production runtime verification.


## 2026-10-14 — PR #51 merged: acquisition dismissal safety

- PR #51 (`test: cover acquisition dismissal cleanup safety`) was squash-merged to `main` at `790d690ca99866878ee6204f9d101dec5f099994`; tested PR head was `58021141472c85c9fa33c431cba15cb66792bc1c`.
- Added six regression cases for safe dismissal cleanup and refusal/preservation on unrelated files, traversal, ambiguous folders, symlinked targets, and failed transfer cancellation. Test-only change; no production behavior or safety checks altered.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety `38590192829`, Docker packaging/full unit suite `38590192830`, container runtime smoke `38590192905`, validation-only multi-architecture image build `38590192858` (publishing paused).
- The first CI attempt failed due to a test-harness namespace collision; the helper was renamed in the AST test namespace and corrected-head CI passed. No separate local test run is claimed.
- The reported HTTP 409 was not reproduced and remains deferred. No live slskd test, real download-folder deletion, publication, deployment, or production runtime verification was performed.


## 2026-10-14 — Acquisition dismissal neighbor-preservation regression

- Branch `test/acquisition-dismissal-neighbor-preservation` starts from main commit `7f05363c3b9abec29ef7c7d516bad2796813b11e` after PR #52's exact-head CI passed and merge completed.
- Added a regression proving successful cleanup removes only the selected album folder and preserves a neighboring artwork file plus a different album folder. Existing tests cover refusal before deletion when the selected folder contains an unexpected file.
- Test-only change; no production cleanup logic altered. All four required workflows passed on exact head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7`: syntax `38594117785`, Docker packaging/full unit suite `38594117579`, runtime smoke `38594117489`, and validation-only multi-architecture `38594117597` (publishing paused). HTTP 409 remains deferred. No local test execution, live slskd, real production-folder deletion, publication, deployment, or runtime verification.

- CI follow-up: the initial assertion expected one transfer lookup, but the implementation performs two preflight checks. Corrected the test to expect both; corrected earlier test head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7` passed all four workflows.
- Earlier tested PR head `6413d7cd94919a9983a381a398787b4301443d1b` passed all four required workflows: Python syntax run `38594465611`, Docker packaging/full unit suite `38594465538`, container runtime smoke `38594465673`, and validation-only multi-architecture image build `38594465580` (publishing paused).
- No local test execution, live slskd test, real production-folder deletion, publication, deployment, or runtime verification. HTTP 409 remains deferred because it was not reproduced.

- Final PR #53 head `ef6ec7347f69c0be04331d7bd671d9f56f3c137d` passed all four required workflows: syntax/acquisition safety `38599666003`, Docker packaging/full unit suite `38599666001`, container runtime smoke `38599665955`, and validation-only multi-architecture image build `38599665933` (publishing paused). Squash-merged at `a7c8dd469c76b340706ba65db8b4315aac60e62b`. No workflow runs were returned for the merge commit itself. No local test run, live slskd, real production-folder deletion, publication, deployment, or production runtime verification is claimed.

## 2026-10-14 — Direct-import acquisition cleanup extraction

- Started `refactor/acquisition-cleanup-domain` from GitHub main `7a81a5dedff8e9e7245309770b4b1fe34b46be9e`.
- Moved the unchanged cleanup algorithm from `navidrome_server.py` into `acquisition_cleanup.py`, injecting the existing canonical folder sanitizer, slskd transfer listing, and HTTP client. Preserved the old function as an adapter and included the module in Docker packaging.
- Moved seven cleanup regression cases to `tests/test_acquisition_cleanup.py`, which imports the implementation directly. The previous AST harness no longer extracts the cleanup function; the rest of the safety suite remains intact.
- Final exact PR head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows: syntax/acquisition safety `38600688719`, Docker packaging/full unit suite/image build `38600688787`, runtime smoke `38600688814`, and validation-only multi-architecture image validation `38600688667` (publishing paused). PR #54 was squash-merged at `982e39122a401b8b68d75e38423dbb93711b4abd` after reviewing the complete diff; GitHub reported mergeable and no review submissions or inline threads.
- No separate local test run, live slskd request, real production-folder deletion, publication, deployment, or production runtime verification is claimed. HTTP 409 remains deferred because it was not reproduced.
- Next: extract source-switch/interrupted-import orchestration behind injected dependencies, preserving direct-import tests and every existing filesystem safety invariant.

## 2026-10-14 — Direct-import interrupted-import recovery

- Extracted the existing reconciliation algorithm into `acquisition_recovery.py`; injected the lock, dismissal/state readers, music root, folder sanitizer, strict completion matcher, persistence, clock, JSON, and move operation. Preserved the legacy adapter.
- Moved four existing recovery cases out of `tests/test_acquisition_safety.py` and added a direct-import test for dismissed/non-importing states. Docker packaging updated.
- Final exact PR head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety `38601516322`, Docker packaging/full unit suite/image build `38601516096`, runtime smoke `38601516565`, and validation-only multi-architecture build `38601516203` (publishing paused). PR #55 was squash-merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30` after complete diff review; no review submissions or inline threads were present.
- No production filesystem recovery, live service interaction, publication, deployment, or production runtime verification is claimed.
- Next: extract source-switch orchestration behind injected dependencies, preserving cleanup failure as a hard stop and uncertain queue outcomes as monitored rather than retried.

## 2026-10-14 — Direct-import source-switch orchestration

- Extracted the source-switch loop into `acquisition_source_switch.py` behind injected config, lifecycle, cleanup, HTTP, candidate-start, status, and persistence dependencies. The legacy wrapper remains.
- Moved the ambiguous-queue test out of the AST harness and added direct tests for cleanup hard stops, no-fallback status, failed fallback cleanup, and successful fallback persistence. Docker packaging updated.
- Final exact PR head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety `38602255318`, Docker packaging/full unit suite/image build `38602255282`, runtime smoke `38602255326`, and validation-only multi-architecture build `38602255378` (publishing paused). PR #56 was squash-merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda` after final diff review; no review submissions or inline threads were present.
- No live slskd interaction, production cleanup, publication, deployment, or production runtime verification is claimed.
- Next: extract the watcher loop and top-level lifecycle coordination behind injected dependencies; keep cancellation/cleanup failure a hard stop, uncertain queue outcomes monitored, and import rollback/safety tests intact.


## 2026-10-14 — Acquisition watcher lifecycle extraction (PR #57)

- **PR:** https://github.com/abucalip/navi-librarian/pull/57
- **Branch:** `refactor/acquisition-watcher-domain`, based on `main` `09c5c884ffbfba035a6ee698f7192b1e9bbb6282`.
- **Implementation:** extracted the watcher loop to `acquisition_watcher.py` with injected dependencies; preserved `_discovery_watch_and_import_album` as the compatibility adapter and included the module in Docker packaging.
- **Regression coverage:** direct tests for dismissal, interrupted-import reconciliation, completed transfer evidence without verified folder (no import), and verified-path handoff to the safe import coordinator.
- **First CI attempt:** syntax compilation passed, but the full suite failed one new test because it read status details from keyword arguments rather than the existing positional fourth argument. Corrected the test and reran the four required workflows.
- **Corrected exact-head CI:** `6793c339464c9d573c02f5e7dc91d15b5f568348` passed Python syntax/acquisition safety run `38604931720`, Docker packaging/full unit suite/build `38604931649`, container runtime smoke `38604931792`, and validation-only multi-architecture `38604932002` (publishing paused).
- **Final-head CI:** after the documentation updates, exact PR head `9f201e247c092ca74f805b8ca8a1cb6f872b3cba` passed Python syntax/acquisition safety `38605193852`, Docker packaging/full suite/build `38605193845`, runtime smoke `38605193808`, and validation-only multi-architecture `38605193820` (publishing paused).
- **State:** PR #57 was subsequently squash-merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589. No assistant-local test run, live slskd behavior, production filesystem operation, image publication, deployment, or production runtime verification.


## 2026-10-14 — Modularization roadmap reconciliation and session closeout

- Reconciled the roadmap against current GitHub main and the open-PR list after PRs #57–#59.
- Marked watcher-loop extraction (#57), watcher-startup extraction (#58), and acquisition-state save/list persistence (#59) as merged, with their known merge SHAs and exact-head CI boundaries.
- Reordered remaining work: acquisition coordination and AST-test migration; settings/configuration/service boundaries; discovery orchestration; application assembly; MCP retirement last.
- Clarified manual testing: no full local-helper browser run is required for backend-only modularization. Performance observation and a distinct error/recovery exercise remain for the next UI-facing change. The HTTP 409 investigation remains deferred until recurrence.
- Verification boundary: documentation-only change; no application tests were run in this session. No local helper run, live slskd interaction, production filesystem operation, publication, deployment, or runtime verification is claimed.
- Next action: inspect current callers and tests on GitHub main, then implement the smallest safe acquisition-coordination extraction with direct-import regression coverage.


## 2026-10-14 — Front-end ownership transferred to ZCode

- Added root `AGENTS.md` with front-end scope, protected paths, API/security contract, design workflow using Impeccable where available, exact-SHA verification requirements, and an initial focused visual-polish task.
- Updated `docs/DEVELOPMENT_WORKFLOW.md`, `docs/PROJECT_STATUS.md`, and historical handoff wording to identify ZCode as the front-end owner. Retired the previous root-specific instruction file so there is one authoritative instruction file.
- Backend/domain, safety, integration, merge, publishing, deployment, and project-level verification ownership remains with the assistant. The acquisition-coordination roadmap remains the main engineering priority.
- Documentation-only change. No application tests or UI checks were run; verify required CI on the exact PR head before merge.

## 2026-10-14 — PR #66 merged: login-page design-system alignment

- **PR:** https://github.com/abucalip/navi-librarian/pull/66; branch `ui/login-alignment`; tested head `d0b13b7411b9b300b78b24a8944348b7e57d4b65`; squash merge `717b1ad08e5de54e2dd8c11c2734976d75ce2e5f`.
- Updated only `static/login.css`: aligned color tokens and typography with the app, refined panel/button treatment, and added input/button focus-visible rings. Authentication and application behavior were unchanged.
- All four required workflows passed on the exact PR head: syntax `38639793800`, Docker packaging/full unit suite `38639793772`, runtime smoke `38639793518`, and validation-only multi-architecture `38639793667` (publishing paused). Reported test runs: 15 focused tests; 185 full-suite tests, one pre-existing skip.
- Manual report and screenshots were published on the PR. Desktop/narrow viewport, failed-sign-in state, and asset/network checks passed. The report explicitly marks keyboard-focus modality and first-run setup variant as skipped, so these are not logged as independently exercised.
- No image publication, deployment, or production runtime verification. Next: continue acquisition-safety test migration/audit; keep front-end work within the ZCode ownership boundary.


## 2026-10-15 — Session closeout: service settings policy extraction

- PR #95 (`refactor: extract service settings policy`) remains open; final verified PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9` passed all four required workflows: syntax/acquisition safety `38664285319`, Docker packaging/full unit suite/build `38664285227`, container runtime smoke `38664285195`, and validation-only multi-architecture image validation `38664285194` (publishing paused).
- Extracted six settings-policy functions into `service_settings.py` with injected storage/path callbacks; legacy MCP/web function signatures remain adapters. Direct-import regression tests replace AST-executed tests. Docker packaging includes the new module.
- No local tests were run. No image publication, deployment, or production runtime verification. PR #95 is not merged.
- **Next action:** review PR #95's full diff and exact-head checks, then make an explicit merge decision; continue service-boundary modularization only after preserving the web/MCP compatibility contract.


## 2026-10-15 — PR #103 merged: acquisition import source-root race hardening

- **PR:** https://github.com/abucalip/navi-librarian/pull/103; tested final head `9de78c268af1b640a2a08afecb25a22502322a85`; squash merge `cf40df35a76d669421dcddbafd21ea22652bd0b1`.
- **Change:** pin the source directory and destination parent with no-follow directory descriptors; perform staging, moves, and rollback relative to pinned descriptors so replacing the source path with a symlink cannot redirect imports. Preserve collision-suffixed matching, cross-filesystem fallback, no-overwrite checks, and recovery behavior. Added direct-import regression coverage for source-root replacement, collision suffixes, cross-filesystem fallback, and rollback.
- **Exact-head CI:** all four required workflows passed on `9de78c268af1b640a2a08afecb25a22502322a85`: Python syntax `38726626891`, Docker packaging/full unit suite/build `38726626846`, container runtime smoke `38726626956`, and validation-only multi-architecture image validation `38726626910`. Image publishing remains paused.
- **Verification boundary:** no separate assistant-local test run, live slskd test, production filesystem operation, image publication, deployment, or production runtime verification is claimed.
- **State:** implemented, exact-head CI passed, merged. Main was observed at `5cf853cbd85cd9aec88ea6276522e86f83b7935c` immediately after merge; documentation closeout follows in a separate PR.
- **Next:** continue the highest-priority remaining acquisition-coordination/test audit from the current GitHub main and roadmap; inspect current PRs and checks before choosing the next code change.


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



## 2026-10-15 — PR #112 lazy auth service dependency verification

- Branch: `refactor/lazy-auth-service-dependency`; verified exact head `ded9aef759c87ccf07d71cd777b366af424cc06c`, based on main `41c050b86aded92dafb101165ed14aadd1e6c720`.
- The app assembly resolves the legacy librarian service lazily for auth settings and signing-key storage. Persistent storage and MCP adapter ownership are unchanged.
- Added a subprocess regression for import-time decoupling and converted auth integration tests to fake-service injection while retaining existing auth behavior assertions.
- All four required workflows passed on the exact head: syntax `38737672741`, Docker packaging/full suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture image validation `38737672689`.
- No separate local tests, image publication, deployment, or production runtime verification. PR #112 merged by squash at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four required workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No separate local tests, image publication, deployment, or production runtime verification. Publishing remains paused.


## 2026-10-15 — PR #116 merged: Proxmox MCP SDK compatibility and handler regression

- PR #116 merged at `9e6979203cbdb6f2d38225584952136170eb2df5` from exact tested PR head `a14accac574d1997e6785ffbf170be136b95c5b9`.
- Corrected the host-side entry point to use `mcp.server.mcpserver.MCPServer`, matching pinned `mcp==2.3.0` and the main MCP server. MCP startup now occurs only when `server.py` is executed as a script.
- Added handler regressions proving rejected shell-composed commands never invoke SSH, accepted commands retain the existing SSH argument/timeout/output behavior, and output remains capped at 20,000 characters.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety `38742736856`; Docker packaging/full suite/build `38742737079` (243 tests passed); container runtime smoke `38742737082`; validation-only multi-architecture image validation `38742736770`.
- An earlier CI cycle exposed the stale FastMCP import; the defect was corrected and all four workflows passed on the final head. No local test run or live Proxmox command, image publication, deployment, or production runtime verification is claimed.

---



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


## 2026-10-15 — Discovery refresh API count validation

- Root cause: the refresh route used `int(payload.get("count", 20))`; Python accepts booleans as integers, numeric strings as parseable integers, and truncates floats. Replaced coercion with strict JSON integer validation before service invocation.
- Added route regression cases for malformed types and out-of-range values. The default count and valid integer behavior remain unchanged.
- Branch: `fix/discovery-refresh-strict-count`. Implementation head `859bf10b1bbaececd2045596287c7680bb66d514` passed Python syntax `38762625902`, container runtime smoke `38762625878`, Docker packaging/full unit suite/build `38762625612`, and validation-only multi-architecture image validation `38762625568`. Re-run all four after the documentation closeout changes and before merge.


## 2026-10-15 — PR #129 merged: discovery refresh input validation

- Merged PR #129 at `b3db4d1d3ac3367a306435e0e3e50e7e3286ce22` from exact final PR head `d6f57b95f1cd77f58d1636f471a8f80bc9776f61`.
- Replaced coercive `int(...)` handling with strict JSON integer validation on the discovery refresh count. Regression tests cover malformed types and range failures; default count and valid integer behavior remain unchanged.
- All four required workflows passed on that exact head: syntax `38762802954`, Docker packaging/full suite/build `38762802863`, container runtime smoke `38762803101`, and validation-only multi-architecture validation `38762803211`.
- No separate local test run, image publication, deployment, or production runtime verification.


## 2026-10-15 — PR #132 merged: sliding navigation indicator

- PR: https://github.com/abucalip/navi-librarian/pull/132
- Tested head: `b4982260a4e5697ee02766f47d35f7182303387a`; squash merge: `44b03d6e6293e1a1ba34803104f52c4e443d245b`.
- Replaced the static navigation active marker with a sliding, transform-only indicator and a scoped SVG goo filter. Preserved reduced-motion support, mobile horizontal navigation, and accessible current-page semantics. Changed files were limited to `app/templates/index.html`, `static/app.css`, `static/app.js`, and `docs/UI_BACKLOG_EXECUTION.md`.
- All four required workflows passed on the exact PR head: Docker packaging `38766740766`, runtime smoke `38766741159`, Python syntax `38766741253`, and validation-only image validation `38766741247` (publishing paused).
- Manual browser report: https://github.com/abucalip/navi-librarian/pull/132#issuecomment-6196780079. All eight checklist items passed on the exact tested commit; zero failures.
- No image publication, deployment, or production runtime verification.

## 2026-10-15 — PR #126 merged: acquire `auto_queue` validation

- PR #126: https://github.com/abucalip/navi-librarian/pull/126; exact final tested head `a67be60e8f35a3a6e9430ac3ad30700532d958cc`; squash merge `3b3a9d47538d51820b6ce162f524812d0800f3c1`.
- `POST /api/acquire` now accepts only a JSON boolean for `auto_queue`; omitted input still defaults to `true`, explicit `false` is preserved, and invalid strings, numbers, null, arrays, or objects return HTTP 400 before the service call. Regression tests cover those cases.
- All four required workflows passed on the exact final PR head: Python syntax `38756653450`, Docker packaging/full suite/build `38756653379`, container runtime smoke `38756653406`, and validation-only multi-architecture image validation `38756653398` (publishing paused).
- No separate local test run, image publication, deployment, or production runtime verification is claimed.
