# Archived modularization records

This file preserves historical extraction and verification notes that were present in the former diary-style versions of `docs/TEST_PLAN.md`, `docs/ARCHITECTURE.md`, and `docs/MODULARIZATION_ROADMAP.md` but were not represented by PR number in the root `PROJECT_LOG.md` when the documentation cleanup began.

These records are historical evidence, not current status or active instructions. When an old entry conflicts with current GitHub `main`, current code and the current project documents take precedence. For current verification rules use `docs/TEST_PLAN.md`; for architecture use `docs/ARCHITECTURE.md`; for remaining work use `docs/MODULARIZATION_ROADMAP.md`; for current history use root `PROJECT_LOG.md`.

## UI accessibility PRs — 2026-10-15

- PR #144 landmark naming merged at `f1008bb3af25c7c76dac8bae67177a07b21df147` from exact tested head `4b44cdb98485a93ba86ac102f29081b917d4e4fe`; manual report was published.
- PR #142 contrast merged at `77faf5e03fdc4985541b0da5952568d0925336df` from conflict-resolved exact PR head `dd5561bff2ca8b89ca934a60f8348e67a044093c`. All four required workflows passed on that exact head: Docker packaging `38794146977`, validation-only multi-architecture image validation `38794146985`, Python syntax `38794147000`, and container runtime smoke `38794146979`.
- Conflict resolution retained the merged landmark documentation and the `--subtle: #94958b` contrast fix. The contrast manual report applies to prior head `38addc52dfb14ccbf95a72ffad2dbd0713d9fcf9`; the combined resolution head did not receive a separate manual browser pass.
- Publishing remains paused. No deployment or production runtime verification is claimed.

---

## Settings persistence extraction — PR #143 merged

- PR #143 exact final head `e28cd12d3736fd2eb368b53c98e3cbddb5438166`; squash merge `409f634a20ba67c5a39dfec0e5bf57995a3fefbe`.
- Direct-import regressions cover Unicode round trips, corrupt JSON fallback, append-only legacy quality-tier migration, configured absolute music-path application, and restrictive SQLite file mode. Legacy `_discovery_settings_init/read/write` wrappers and MCP-facing settings functions remain available.
- All four required exact-head workflows passed: Docker packaging/full suite/build `38791730058`, Python syntax `38791730078`, container runtime smoke `38791729963`, and validation-only multi-architecture image validation `38791730017`.
- No separate local test execution, publishing, deployment, or production runtime verification is claimed. Publishing remains paused.

---

## MCP registration isolation — current PR

- Run python -m unittest tests.test_mcp_registry tests.test_auth_routes_integration -v and the full python -m unittest discover -s tests -v suite.
- The regression must prove all 27 existing MCP tool functions remain callable through the explicit registry, registry names are unique and stable, and importing navidrome_server does not load mcp.server.mcpserver.
- First verification cycle passed on implementation head fe71a9a19188a018a2ee65d5b313a99413d239f2: syntax/acquisition safety 38783091362; Docker packaging/full suite/build 38783091326; runtime smoke 38783091309; validation-only multi-architecture 38783091337. The final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f also passed all four workflows (38783296279, 38783296173, 38783296256, 38783296249) and PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00. Publishing remains paused.

---

## Authentication signing-key symlink refusal — PR #137 merged

- `tests/test_app_auth.py::test_signing_secret_refuses_symlink_without_chmodding_target` checks an existing `app_auth.key` symlink is rejected and the target contents and permissions remain unchanged.
- Exact final PR head `f6458af4b84b957902a2da1960cdafc06d0f7594` passed all four required workflows: Python syntax, Docker packaging/full unit suite/build, container runtime smoke, and validation-only multi-architecture image build. Publishing remains paused. No separate local test run is claimed.

---

---

## Concurrent authentication rate-limit regression — PR #134

- `tests/test_auth_routes_integration.py::test_concurrent_login_attempts_cannot_race_past_rate_limit` holds one password-verification call while another request reaches the last available per-client attempt slot.
- Expected HTTP outcomes are one `401` for the in-flight bad password and one `429` for the request that would exceed the limit. This catches check-then-record races without timing-only assertions.
- Run `python -m unittest tests.test_app_auth tests.test_auth_routes_integration` and all four required CI workflows on the exact final PR head before merge. PR #134 final head `a15fa4e9b588e7fa96d36242f51b55b23fba9e70` passed Python syntax `38776917077`, Docker packaging/test-and-build `38776916979`, container runtime smoke `38776917024`, and Docker image validation `38776917027` (publishing paused). PR #134 was squash-merged at `ef6ce0ff4faa9fffca66a7e43294eee6a0847dbd`. No local test execution is claimed; publishing, deployment, and production runtime verification are separate.

---

---

## 2026-10-15 — PR #116 merged: Proxmox MCP SDK compatibility and handler regression

- PR #116 merged at `9e6979203cbdb6f2d38225584952136170eb2df5` from exact tested PR head `a14accac574d1997e6785ffbf170be136b95c5b9`.
- Corrected the host-side entry point to use `mcp.server.mcpserver.MCPServer`, matching pinned `mcp==2.3.0` and the main MCP server. MCP startup now occurs only when `server.py` is executed as a script.
- Added handler regressions proving rejected shell-composed commands never invoke SSH, accepted commands retain the existing SSH argument/timeout/output behavior, and output remains capped at 20,000 characters.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety `38742736856`; Docker packaging/full suite/build `38742737079` (243 tests passed); container runtime smoke `38742737082`; validation-only multi-architecture image validation `38742736770`.
- An earlier CI cycle exposed the stale FastMCP import; the defect was corrected and all four workflows passed on the final head. No local test run or live Proxmox command, image publication, deployment, or production runtime verification is claimed.

---

---

## Proxmox MCP command allowlist — PR #114 verified and merged

- Direct-import regressions accept only explicitly approved diagnostic forms and reject arbitrary commands, shell operators, command substitution, newlines, invalid container IDs, unsafe device paths, and non-string input.
- The `server.py` handler refuses rejected input before invoking SSH. The `run(command: str)` MCP signature, SSH target/options, timeout, and output truncation for accepted commands remain unchanged.
- Exact tested PR head: `cd8319696180875a3cb6f0dc151d88e0c8c490d7`; squash merge: `6ab848d444373dfa37e6d46528a2840a53a8f763`.
- All four required workflows passed on that exact head: syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`.
- No local test execution or live Proxmox command is claimed.


---

---

## 2026-10-15 — PR #108 verified and merged

- Migrated discovery route unit tests from patching `discovery.librarian` to explicit fake-service injection, consistent with the new lazy dependency seam.
- Final tested PR head: `a5170e50080c0ca94b4068155ace83fd33c6f029`; squash merge: `be51f0ce17fe8eccd1b57714e869db69a5f1ba78`.
- All four required workflows passed on that exact head: Python syntax/acquisition safety `38733725606`; Docker packaging/full unit suite/build `38733725816` (227 tests); container runtime smoke `38733725595`; validation-only multi-architecture image validation `38733725591`.
- No separate local test run, image publication, deployment, or production runtime verification is claimed.

---

---

## 2026-10-15 — PR #107 merged: acquisition router service injection

- **PR:** https://github.com/abucalip/navi-librarian/pull/107; final tested PR head `67174e8026f44382a4a6bea48ff1df80744dda35`; squash merge / main SHA at closeout `1cc15dd6343370ce0915bf7228a745d3558b393b`.
- **Change:** added `app/api/dependencies.py` with lazy `get_librarian()` and injected it into all acquisition routes. This removes the acquisition router's import-time import of `navidrome_server` while preserving endpoint paths/methods, existing service calls, payload mapping, HTTP error behavior, and SSE response headers. Added regression tests for route contracts, dependency wiring, fake-service handler calls, validation, and sanitized errors.
- **Exact-head CI:** all four required workflows passed on `67174e8026f44382a4a6bea48ff1df80744dda35`: Python syntax `38732084595`; Docker packaging/full unit suite `38732084663`; container runtime smoke `38732084579`; validation-only multi-architecture image build `38732084589`. An earlier test-only assertion failure on `d6a1696c06f594e2c4025e0eff54bb8496fd8e29` was corrected before these passing runs.
- **Status:** Implemented, tested, CI passed, merged. Publishing remains paused; this did not publish an image, deploy the application, or verify production runtime. `app/main.py`, discovery, and settings still import `navidrome_server`; MCP tools and domain logic were not removed or duplicated.
- **Next priority:** continue the narrow web service-injection audit at the discovery router, preserving API behavior and MCP compatibility. Keep deployment/runtime verification as a separate gate; do not resume routine modularization if a higher-priority safety or delivery gap appears.

---

---

## 2026-10-15 — PR #103 verified and merged: import source-root guard

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- Regression coverage verifies a source-folder symlink swap fails closed while preserving outside files and original tracks; collision-suffixed matching, cross-filesystem fallback, and partial-move rollback remain covered.
- All four required workflows passed on the exact head: syntax/acquisition safety `38726626891`, Docker packaging/full unit suite/build `38726626846`, runtime smoke `38726626956`, and validation-only multi-architecture image validation `38726626910`. No local or production-folder test is claimed.

---

---

## 2026-10-15 — PR #100 verified and merged: cleanup root traversal

- PR #100 merged at `6e8e861cc84d5951b0d177ffea256a0dd88fe4b4` from exact tested head `89813bd3802b1f8920715aaeca55ccb5e461c9c9`.
- The regression suite covers target-directory and parent-directory symlink replacement during transfer lookup; both the outside target and moved original album file must survive. Cleanup uses no-follow root traversal, descriptor-relative unlink/rmdir, exact planned-entry validation, and device/inode/size checks.
- All four required workflows passed on that exact head: syntax/acquisition safety `38724953760`, Docker packaging/full unit suite/build `38724953699`, runtime smoke `38724953828`, validation-only multi-architecture image validation `38724953678`. No local or production-folder deletion test is claimed.

---

---

## 2026-10-15 — PR #99 cleanup directory-swap regression verified

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- Regression covers replacement of the preflighted album folder with a symlink during external transfer lookup; cleanup must fail closed while preserving both the outside target and moved original album track.
- All four required workflows passed on the exact head: syntax/acquisition safety `38724377954`, Docker packaging/full unit suite/build `38724378021`, runtime smoke `38724378097`, and validation-only multi-architecture image validation `38724377870`. No separate local test or production-folder deletion test is claimed.

---

---

## 2026-10-15 — PR #98 verified and merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- All four required workflows passed on that exact head: syntax/acquisition safety `38723927107`, Docker packaging/full unit suite `38723927072`, runtime smoke `38723927058`, and validation-only multi-architecture validation `38723927057`. Existing AST adapter integration coverage remains alongside direct-import coordinator tests.
- No separate local tests, publishing, deployment, or production runtime verification.

---

---

## 2026-10-15 — PR #97 verification complete

- Added direct-import regression coverage for Last.fm key trimming, blank-input preservation, and response redaction while preserving the existing success JSON contract.
- All four required workflows passed on exact PR head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`: Python syntax/acquisition safety `38721333335`, Docker packaging/full unit suite `38721333353`, container runtime smoke `38721333332`, and validation-only multi-architecture image validation `38721333418` (publishing paused).
- No assistant-local test run, image publication, deployment, or production runtime verification is claimed.

---

---

## 2026-10-15 — PR #96 slskd settings policy validation

- `service_settings.py` is the direct-import owner for slskd config validation and settings read/update policy; MCP wrappers remain in `navidrome_server.py`.
- Regression coverage includes blank API-key preservation, no API-key serialization, invalid URL refusal, exact quality-tier set validation (including malformed JSON values that are not strings), invalid music/download path refusal without writes, default serialization, and successful runtime music-path callback.
- `tests/test_quality_priority.py` now invokes the extracted policy directly for quality-order save/rejection tests; AST-executed SQLite settings helpers remain for storage migration/persistence behavior only.
- Implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed syntax/acquisition safety (`38665710740`), Docker packaging/full unit suite (`38665710718`, 208 tests), runtime smoke (`38665710761`), and validation-only multi-architecture image validation (`38665710769`). The initial failure was a stale AST namespace assumption and was fixed before this passing head.
- Required before merge: rerun all four workflows on the final docs-updated PR head. No local test run, image publication, or deployment is claimed.

---

---

## 2026-10-15 — Service settings policy direct-import migration (PR #95)

- `tests/test_service_settings.py` now imports `service_settings.py` directly instead of parsing and executing selected functions from `navidrome_server.py`.
- Regressions cover password/API-key redaction, Navidrome credential validation, blank-password preservation, invalid URL/user/path refusal without writes, library-directory update callback behavior, and ListenBrainz username validation/no-write behavior.
- The legacy adapter signatures remain unchanged; SQLite and global runtime path ownership are not extracted.
- Final PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9` passed all four required workflows: syntax/acquisition safety (`38664285319`), Docker packaging/full unit suite and build (`38664285227`), container runtime smoke (`38664285195`), and validation-only multi-architecture image validation (`38664285194`). An earlier implementation revision exposed a callback-injection mismatch; it was corrected before final-head verification. No local tests were run. Publishing remains paused; no deployment or production runtime verification is claimed.

---

---

## 2026-10-15 — Web dependency audit and next test seam

- Dependency audit found web routes call the legacy server for settings, Navidrome service checks, recommendation/list orchestration, and all acquisition lifecycle actions. Keep these integration boundaries intact during modularization.
- `tests/test_service_settings.py` currently uses AST extraction to execute six real functions in a stub namespace. Next migration candidate: extract those six settings-policy/configuration functions to an importable module with injected settings read/write and music-directory dependencies, then test the actual module directly.
- Required regression assertions for that extraction: Navidrome URL and credential validation; blank-password preservation; no password/API-key leakage in returned payloads; ListenBrainz username validation and no write on invalid input; existing response shapes/messages; music-library path handling; and unchanged MCP wrapper signatures. Keep storage/migration/global path ownership in the legacy server.
- Do not combine settings policy with live network checks, SQLite schema changes, or MCP dependency removal. Test the new module directly and add adapter tests for compatibility.
- Audit only in this session: no code/tests changed and no local tests were run. PR #93 CI was green on its exact head; current merge-main workflow status must be verified independently.

---

---

## 2026-10-15 — PR #92 merged: dismissed-acquisition preflight coverage

- PR #92 merged as `60698f7bf1413e4c643309e200d1ace2e268bee3` from exact tested head `1f0ce2174e1e60f3aab7c898dd534b8b1f11e858`.
- Direct-import tests cover non-dismissed bypass, valid metadata forwarding, malformed/non-object metadata normalization to `{}`, and refusal when reactivation fails.
- All four required workflows passed on that exact PR head: syntax/acquisition safety `38661883721`; Docker packaging/full suite `38661883755` (203 tests); runtime smoke `38661883730`; multi-architecture validation `38661883723` (publishing paused).
- Retain AST integration tests `test_explicit_get_reactivates_safely_dismissed_job` and `test_dismissed_job_stays_blocked_if_reactivation_fails`; they protect the top-level Get flow and response behavior. Preserve shared transition-lock ownership.
- Next: continue auditing remaining AST-coupled acquisition lifecycle tests for safe direct-import seams without weakening end-to-end transition coverage.

---

---

## 2026-10-15 — Acquisition reservation lifecycle verified

- PR #90 merged at `4756ad6a7669ab77e284309ca9cd0f178e7f032a` from exact tested head `c0b4a0ebcc5fa4ef8b71441fb38d55aed8fce097`; all four workflows passed, with 199 unit tests.
- Direct tests verify reservation of a fresh identity, duplicate refusal without mutation, and preservation of unrelated active identities. Reservation still occurs while the coordinator owns the shared transition lock.
- The callback runs outside the lock; `run_reserved_acquisition` guarantees cleanup under the lock on success and exception. Keep the top-level simultaneous-request regression.
- Next: cover dismissal/reactivation preflight through an injected orchestration helper, retaining coordinator-level success and refusal tests. Any further extraction requires focused/full tests and all four exact-head workflows.

---

---

## 2026-10-15 — Watcher-start concurrency regression verified

- PR #84 exact tested head: `398486476aacdbbefefeaee5cb79182cc0835fb8`; all four required workflows passed: syntax/acquisition safety run 38656927551, Docker packaging/full suite run 38656927436, runtime smoke run 38656927801, and multi-architecture validation-only run 38656927516.
- The full unit-test step and acquisition safety regression step passed. The new race test asserts exactly one successful watcher reservation, persisted job, and thread start under simultaneous calls.
- Diff review found no production changes. Retain remaining AST integration tests until direct-import tests cover equivalent coordinator, persistence, and recovery boundaries.
- Publishing remains paused; no deployment or production runtime verification.

---

---

## 2026-10-15 — Session closeout: remaining AST-coupled lifecycle coverage

- Baseline reconciled against GitHub `main` at `f46b3618eaa8abc98b7f077698439b304a0005b7`; PR #82's documentation closeout is merged. Its exact tested head `5fdad1045ba04db84aea05a477a51dce38733f5c` passed all four required workflows; this session adds no new test result.
- Continue comparing the remaining AST cases with direct-import coverage for duplicate-request reservation/concurrency, incomplete saved candidate details, dismissed-job reactivation and failed-reactivation refusal, and stale watcher recovery.
- Do not remove tests that uniquely verify shared-lock races, conditional persistence before filesystem import, or watcher/coordinator integration. Any migration must preserve the same failure-path assertions and be followed by focused tests, the full suite, syntax checks, final diff review, and all four required workflows on the exact PR head.

---

---

## 2026-10-15 — PR #78 merged: import dismissal coordination

- PR #78 exact tested head: `e6a609ca7381d0751d529b52f55aeebd56d76661`; squash merge: `5d638c7adf5a42fdac8052cb4fc223236564cd72`.
- Direct tests cover the dismissal-serialized import callback: lock spans the check and callback, dismissed state prevents callback execution, and return values/exceptions propagate.
- The AST integration test `test_import_does_not_move_files_if_importing_status_cannot_be_persisted` remains to verify the full server adapter does not enter filesystem import before the persisted importing transition succeeds.
- All four required workflows passed on exact head: syntax `38653493244`, Docker packaging/full unit suite `38653493312`, runtime smoke `38653493285`, and image validation with publishing paused `38653493279`. Full suite: 186 tests passed.
- No live slskd, publication, deployment, or production runtime verification is claimed.

---

---

## 2026-10-15 — PR #76 merged: slskd polling regressions

- PR #76 exact tested head: `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6`; squash merge: `a55a9fa7eed1e221f52434b50f44d0c415fd491a`.
- Direct-import tests cover progressive query fallback, delayed peer payloads after reported response/file counts, legacy 404/405 endpoint behavior, and propagation of unexpected HTTP errors.
- All four required workflows passed on the exact head: syntax `38652846800`, Docker packaging/full unit suite `38652846779`, runtime smoke `38652846790`, and image validation with publishing paused `38652846819`. The full suite reported 184 tests passed.
- The end-to-end AST retry test remains to assert the coordinator's final response and query diagnostics. No live slskd, publication, deployment, or production runtime verification is claimed.

---

---

## 2026-10-15 — PR #73 merged: candidate extraction direct-import regression

- PR #73 exact tested head: `a33772ca1da0b6628da490b69f1dc305b6794de3`; squash merge: `df2f79b3d18df7d13484f7e3b5e7f550a39323d3`.
- Direct-import regression preserves the four Tinariwen/Idrache folder variants, twelve unique tracks, clear-match eligibility, and FLAC quality-tier assertions against `slskd_search.extract_candidates`.
- All four required workflows passed on the exact head: syntax `38652066842`, Docker packaging/full unit suite `38652066649`, runtime smoke `38652066755`, and Docker image validation with publishing paused `38652066683`.
- Remaining AST tests intentionally retain orchestration retry/wait and lifecycle coordination behavior. No live slskd, publication, deployment, or production runtime verification is claimed.

---

---

## 2026-10-14 — PR #72 merged: direct-import slskd search helper coverage

- PR #72 squash merge: `6c6157a8238691b18d2209ea2d2e1306385ec9a2`; tested head `17be72e52b39e63cad63391fb2c4e63ea55d3c26`.
- Added direct-import tests for query progression, blank/whitespace input, payload normalization, album path matching, path-match diagnostics, audio filtering, and result bounds. Removed six corresponding pure-helper cases from the AST harness.
- All four required workflows passed on the exact tested head: syntax `38651547240`, Docker packaging/full unit suite `38651547229`, runtime smoke `38651547283`, and Docker image validation with publishing paused `38651547264`.
- No local standalone test run, live slskd interaction, publication, deployment, or production runtime verification is claimed.

---

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

---

## 2026-10-14 — Completed import safety tests migrated to direct imports (PR #70 merged)

- Removed the redundant `CompletedAlbumMatchingTests` cases from the AST-based `tests/test_acquisition_safety.py` harness. Equivalent or stronger coverage already exercises the production modules directly in `tests/test_acquisition_completion.py` and `tests/test_acquisition_import.py`.
- The direct-import suites cover strict positive-size matching, Unicode/case and Windows path normalization, duplicate-basename ambiguity, symlink refusal, collision-suffix matching, exact folder diagnostics, unrelated-file preservation, destination no-overwrite, storage identity mismatch, reserved manifest rejection, and rollback after a partial move.
- The AST harness retains its separate lifecycle coordination tests. Its injected import callback is now a test spy for transition behavior; filesystem import behavior is tested against `acquisition_import.import_matched_album_files` directly.
- Test-only migration: no production code, queue/cleanup behavior, path validation, rollback implementation, or MCP compatibility changed.
- PR #70 was squash-merged at `78e7f01dc8bf011e3c77e3d6316f6ee565ca6161` after all four required CI workflows passed on exact tested head `0916a7e9d767808bf4f65d3b034e290e5aba4703`. No standalone local test commands or manual browser tests were run for this test-only migration; no image publication, deployment, or production runtime verification is claimed.
- Next: audit remaining AST-coupled acquisition safety cases for duplicate coverage; preserve dismissal/import coordination, conditional state transitions, cleanup refusal, uncertain queue outcomes, and rollback protections.

---

---

## Acquisition queue guard test migration — verified (2026-10-14)

- PR #64 merged at `1596161aa525896d43c37c85533e8056a742439b` from exact tested head `3bde365e43acbe1cc95f68d7014d899046e735f6`.
- The AST-harness queue refusal test and its adapter/HTTP helper were removed; direct-import tests continue to cover the production `queue_candidate_unless_dismissed` guard for dismissed refusal, lock ordering, return propagation, and exception propagation.
- All four required workflows passed on the exact final head: syntax `38636360130`, full test/build `38636360145`, runtime smoke `38636360164`, and validation-only multi-architecture build `38636360139` (publishing paused). No production behavior changed.

---

## Acquisition queue/dismissal coordination extraction (2026-10-14)

- `queue_candidate_unless_dismissed` in `acquisition_orchestration.py` is tested directly for shared-lock scope, dismissal refusal, successful return propagation, and exception propagation.
- The legacy server adapter retains the HTTP request construction and `raise_for_status()`; the guard retains the same shared transition lock and dismissal predicate.
- The AST-based safety case remains in place but delegates to the extracted implementation, avoiding loss of the prior dismissed-job/no-queue regression.
- Exact PR #62 head `4e121eb7977bb1a51ad31f9c87d0d4984497af4d` passed all four required workflows: Python syntax `38619152587`; Docker packaging/full unit suite/build `38619152213`; container runtime smoke `38619152754`; validation-only multi-architecture image `38619152728`. The PR was squash-merged as `d4a16e80f6978a58c3305bf341e370ba9708bb34`. Publishing remains paused. No local helper/manual slskd test, production filesystem operation, deployment, or production runtime verification is implied by CI.

---

## PR #57 merged — acquisition watcher lifecycle

- Merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589; exact tested PR head f4b92a98bae942ac6080316c3f1803d1b6bcff76.
- All four required workflows passed on the exact PR head: syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, container runtime smoke 38605511271, and validation-only multi-architecture build 38605510906 (publishing paused).
- Regression coverage directly imports the watcher module and verifies dismissal and recovery exits, that completed transfer evidence without a verified folder does not import, and that only the verified folder is passed to the existing safe import coordinator. A first CI attempt exposed an assertion reading status details from the wrong argument position; the test was corrected before final verification.
- No separate local test run, live slskd behavior, or production filesystem behavior is claimed. Image publication and deployment remain unperformed.

---

## ACQ-04/ACQ-06 — dismissal cleanup safety regression coverage (PR #51 merged)

- Six focused cases exercise the actual `_discovery_cancel_and_clean_source` helper via the existing AST harness: successful cleanup only after transfers stop; refusal with unrelated files; remote `..` traversal rejection before transfer lookup; duplicate same-name folders rejected without touching either; symlinked album folder rejected without touching the target; failed transfer cancellation preserving local files.
- Initial CI on `b8e1c9a398853851e1a8140a9724600800f42c3b` failed because loading the real helper replaced a stub used by an existing source-switch test. The test harness now gives the helper a distinct namespace name; all four workflows passed on final PR head `58021141472c85c9fa33c431cba15cb66792bc1c`.
- CI runs: syntax/safety `38590192829`; Docker packaging/full unit tests `38590192830`; container runtime smoke `38590192905`; validation-only multi-architecture build, publishing paused, `38590192858`.
- Merged to `main` at `790d690ca99866878ee6204f9d101dec5f099994`. PR #52's documentation closeout passed all four required workflows on exact head `4684fb257685aec90025af0b02a7dff5eacfe10a` and merged at `7f05363c3b9abec29ef7c7d516bad2796813b11e`.
- Follow-up PR #53 adds a regression that successful cleanup preserves sibling artwork and another album folder. All four required workflows passed on exact head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7`: syntax `38594117785`, Docker packaging/full unit suite `38594117579`, container runtime smoke `38594117489`, and validation-only multi-architecture `38594117597` (publishing paused). Existing coverage also proves an unexpected file inside the target folder aborts before deletion of expected tracks.
- Assistant did not run tests locally. No live slskd, real production-folder deletion, publication, deployment, or production runtime testing. The HTTP 409 was not reproduced and remains deferred.

---

## Acquisition lifecycle policy module (PR #47)

- Direct-import tests in `tests/test_acquisition_lifecycle.py` cover monitor-recovery eligibility, conservative cleanup requirements, skip-request rejection states, queue-failure retry classification, and fallback candidate/payload normalization.
- Preserve the invariant that ambiguous queue outcomes remain monitored rather than triggering duplicate source retries; only explicit peer-level rejections may retry another source.
- These tests cover the extracted policy seam only. They do not replace the remaining AST-based orchestration/safety cases; migrate those as the watcher, source-switch, cleanup, and recovery implementations move into domain modules.

---

## Authentication security helper extraction — PR #37 merged (2026-10-14)

- Branch: `refactor/auth-security-helpers`, based on updated GitHub `main` after PR #36 and documentation closeout.
- Added `app/security/auth.py` for persistent signing-secret loading, username/password policy, PBKDF2 digest, and signed-session creation/validation. `app/main.py` imports these primitives and retains compatibility wrappers; HTTP routes, cookie settings, login throttling, and middleware are intentionally unchanged.
- Updated `tests/test_app_auth.py` to import the extracted primitives directly without AST-loading functions from `app/main.py` or starting the service. Tests cover username/password policy, deterministic salt-sensitive digest, signed token expiry/tampering/user binding, persistent secret reuse, private POSIX permissions, and invalid-secret failure.
- Exact-head verification on `192b084850ecbe0137b64b3dae9d07e0471198b4`: Python syntax/full-unit-test workflow `38488744726` passed; Docker packaging/full-unit-test workflow `38488744684` passed; container runtime smoke `38488744607` passed; validation-only multi-architecture `38488744643` passed. No local test execution is claimed.
- Security-sensitive extraction: no intended auth behavior change. PR #37 was squash-merged at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3`. No local test run is claimed.

---

## Metadata API route extraction — PR #36 merged (2026-10-14)

- Branch: `refactor/metadata-api-router`, based on the updated GitHub `main` after PR #35 and documentation closeout.
- Moved `/api/artist-bio`, `/api/album-year`, `/api/album-details`, and `/api/artwork` with provider/cache helpers into `app/api/metadata.py`; registered the router in `app/main.py`.
- Added `tests/test_metadata_routes.py` for endpoint/method inventory, artist bio cache and validation, MusicBrainz year preference, exact Deezer album matching and tracklist parsing, and artwork cache/validation.
- Verification on corrected exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`: Python syntax/full-unit-test workflow `38488440438` passed; Docker packaging/full-unit-test workflow `38488440512` passed; container runtime smoke `38488440488` passed; validation-only multi-architecture `38488440439` passed. The initial full suite revealed the AST-coupled artwork retry test; after migration to the extracted module, the corrected full suite passed. No local test execution is claimed.
- No intended UI contract change; manual browser testing was not required. PR #36 was squash-merged at `15011614649470c9c71734422b95ee048fbf9f3c`. No image publication or deployment occurred.

---

## Discovery API route extraction — PR #35 merged (2026-10-14)

- Branch: `refactor/discovery-api-router` (based on GitHub `main`).
- Added `app/api/discovery.py` and `tests/test_discovery_routes.py`; `app.main` registers the router and no longer defines the four discovery/recommendation handlers inline.
- Focused command: `python -m unittest tests.test_discovery_routes -v`.
- Baseline commands: `python -m py_compile navidrome_server.py app/main.py app/api/discovery.py` and `python -m unittest discover -s tests -v`.
- Direct-import tests cover route/method inventory, recommendation count defaults and album-candidate filtering, discovery list validation/defaults, refresh count parsing/defaults, feedback validation and Unicode metadata serialization, domain payload mapping, and sanitized errors.
- This is an API-only extraction with no intended UI contract change. Manual browser testing is not required unless review/CI reveals a UI behavior change. PR #35 was squash-merged from exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d` at `d61162b29c6f0cccc97aefe9c779567e671651b2`. Python syntax/full-unit-test workflow run `38487647938`, container runtime smoke `38487647898`, Docker packaging `38487647913`, and validation-only multi-architecture `38487647952` all completed successfully on that exact head. No local test execution is claimed. These CI results do not indicate image publication or deployment.

---

## Current verification state — PR #34 merged (2026-10-14)

- PR #34 was squash-merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`.
- All required exact-head workflows passed: Python syntax #330 (run `38485830330`), Docker packaging/full unit tests #237 (run `38485830207`), container runtime smoke #47 (run `38485830231`), and validation-only multi-architecture #91 (run `38485830245`).
- Focused test coverage is in `tests/test_acquisition_routes.py`; route-only change, no intended UI contract change, so manual browser testing was not required. Local test execution is not claimed.
- No image publication, deployment, or production runtime verification. Keep publishing disabled until modularization is complete and separately authorized.

---

## Current verification state — PR #31 merged (2026-10-14)

- PR #31 was squash-merged at `87e5816c4273e720352931402a223f0b61ecbf27` from exact head `135b719bfecf9ad698862d41034d927083426f99`.
- Exact-head CI passed: Python syntax #318, container runtime smoke #35, Docker packaging/full unit tests #225, and validation-only multi-architecture #79. See `docs/PROJECT_STATUS.md` for workflow run IDs.
- Manual UI evidence remains tied to application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`: eight recorded checks passed, zero failures. Performance observation and distinct error/recovery remain deferred to the next UI-facing PR.
- Documentation handoff commits after the merge are recorded, but workflow lookup returned no PR-triggered runs for those documentation commit SHAs; their CI is not claimed.
- Image publication and deployment were not performed. Keep publishing paused pending modularization completion and separate authorization.

---

## Current verification state — PR #32/#33 merged; PR #31 documentation follow-up

- PR #32 and PR #33 are merged. Their exact-head checks passed, including syntax, full unittest discovery/Docker packaging, container runtime smoke, and validation-only multi-architecture build. See the top of docs/PROJECT_STATUS.md and PROJECT_LOG.md for exact commit/run references.
- PR #31's operator guide is reconciled against main `25cd40eca0f20824173d7aefce76b753ef57360c`. Head `3eb3ec6726e0bbe03ef0df9f3d5022796feb7a0c` passed Python syntax workflow #316, full unit tests/Docker packaging workflow #223, container runtime smoke workflow #33, and validation-only multi-architecture workflow #77. Docs-only follow-up `2993273b633b865219818789c47160b8e2429a6f` triggered new exact-head CI runs; these were still in progress at closeout, so wait for their conclusions before merge.
- Manual browser checks remain a gate for UI-facing changes after exact-head CI. The performance observation and distinct error/recovery scenario not recorded in the October 13 report are deferred to the next UI-facing PR. Do not repeat the full visual checklist solely because a non-UI PR changes SHA.
- GHCR publishing stays disabled until the modularization roadmap is complete and release is explicitly authorized.

---

## Discovery refresh coordination extraction — merged PR #30

- PR #30 was merged into `main` at `a12538e7f7ab2f3ec7417680d6127f5c3a1eaa5b`; final PR head was `f9256060d162ed92be0bbacc66a877c2675a5174`.
- Focused regression command: `python -m unittest tests.test_discovery_refresh -v`.
- Syntax check: `python -m py_compile navidrome_server.py discovery_refresh.py`.
- Full suite: `python -m unittest discover -s tests -v`.
- CI passed for code head `46444e3c24dc78008e3c13dfb441059e73279814` (Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156; Docker job included full unittest discovery and image build). A docs-only commit triggered Docker workflow #157; its terminal result was not confirmed at merge time. No local test run or live/UI verification is claimed.
- Refresh coordination tests cover personal payload parsing/write behavior, malformed JSON, non-blocking lock behavior, named-list success/counting, unknown-list handling, builder exceptions, and lock release.

---

## Discovery store extraction — merged PR #29

- PR #29 was squash-merged to `main` at `001f3a7e76979d82adc62edd888d8490565b2ef3`. The final PR head `518505f6dd8e233bc6aaec4b90ec42b0669f70d5` passed Python syntax workflow #243 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507492)) and Docker packaging workflow #150 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507399)); the latter ran Python compilation, the full unit-test suite, and Docker image build.
- No workflow runs were returned for the squash merge commit at closeout. Do not infer merge-commit CI from PR-head CI. No local test execution or live/UI validation was performed.
- Focused commands for future changes:

```sh
python -m unittest tests.test_discovery_store -v
python -m py_compile navidrome_server.py discovery_store.py
python -m unittest discover -s tests -v
```

---

## Latest CI evidence — PR #28

- PR #28 final head `9ab8afeaed6562424b9212f2492d34f3ed9a69ee`: Python syntax workflow #232 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390630)); Docker packaging workflow #139 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390704)), including Python compilation, full unit-test discovery, and image build.
- PR #28 was squash-merged to `main` at `686fb393a178fe27f3806ecd5ce2138b026291cc`. No workflow runs were returned for the merge commit at closeout; CI evidence above is for the exact PR head, not the merge commit.
- No local test execution or live/manual runtime checks were performed during closeout.

---

## Source-switch orchestration extraction — PR #56 merged

- Moved the existing locked source-switch implementation into `acquisition_source_switch.py` with injected config, lifecycle, cleanup, HTTP, candidate-start, status, and persistence dependencies. `navidrome_server.py` retains the compatibility wrapper; the caller still owns dismissal/transition locking.
- Added direct-import tests for uncertain queue outcome (monitor the same peer, never queue another), cleanup refusal before queue, no fallback, failed fallback cleanup stopping the loop, and confirmed fallback persistence.
- PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety `38602255318`, Docker packaging/full unit suite/image build `38602255282`, runtime smoke `38602255326`, and validation-only multi-architecture build `38602255378` (publishing paused). Squash-merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- No live slskd interaction or production cleanup is claimed.

---

## Interrupted-import recovery domain extraction — PR #55 merged

- Moved `_discovery_reconcile_interrupted_import` into `acquisition_recovery.py` with injected state, path, matcher, persistence, clock, JSON, and move dependencies. The legacy MCP function remains a compatibility adapter.
- Added direct-import tests for exact completed-destination reconciliation, changed mount-device refusal, partial staging rollback to the source folder, wrong/incomplete destination refusal, and dismissed/non-importing state refusal.
- The direct tests assert no unintended status updates and preserve source/destination files on refusal. Docker packaging includes `acquisition_recovery.py`.
- PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety `38601516322`, Docker packaging/full unit suite/image build `38601516096`, runtime smoke `38601516565`, and validation-only multi-architecture build `38601516203` (publishing paused). Squash-merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- No production filesystem recovery or live service interaction is claimed.

---

## Acquisition cleanup domain extraction — PR #54 merged

- Extracted the existing fail-safe cleanup implementation into `acquisition_cleanup.py` with injected folder-name validation, slskd transfer lookup, and HTTP client dependencies. `navidrome_server.py` retains its existing MCP-compatible wrapper and delegates to the extracted function.
- Moved all seven dismissal cleanup cases out of the AST-based `tests/test_acquisition_safety.py` harness into directly imported `tests/test_acquisition_cleanup.py`: verified cleanup after transfers stop; unexpected-entry refusal; neighbor artwork/album preservation; traversal rejection; duplicate-folder refusal; symlink-target refusal; failed cancellation preservation.
- The direct tests use the canonical `acquisition_completion.safe_folder_name` helper. Docker packaging includes the new module.
- PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed syntax/acquisition safety `38600688719`, Docker packaging/full unit suite/image build `38600688787`, container runtime smoke `38600688814`, and validation-only multi-architecture build `38600688667` (publishing paused). Squash-merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- No live slskd request, production-folder deletion, image publication, deployment, or runtime verification is performed. HTTP 409 remains deferred because it was not reproduced.

---

## Acquisition dismissal neighbor-preservation regression — PR #53

- Final PR head `ef6ec7347f69c0be04331d7bd671d9f56f3c137d` passed all four required workflows: Python syntax/acquisition safety `38599666003`, Docker packaging/full unit suite `38599666001`, container runtime smoke `38599665955`, and validation-only multi-architecture image build `38599665933` (publishing paused).
- PR #53 was squash-merged at `a7c8dd469c76b340706ba65db8b4315aac60e62b`. No workflow runs were returned for the merge commit itself.
- The new regression proves successful cleanup preserves a sibling artwork file and a separate album folder. Existing cases continue to cover refusal for unrelated entries, traversal, duplicate folders, symlinks, and failed cancellation.
- Tests use the existing AST harness; migrate them to direct-import tests alongside a tested cleanup implementation extraction, preserving all assertions. The reported HTTP 409 remains deferred because it was not reproduced.
- No separate local test run, live slskd test, real production-folder deletion, publication, deployment, or production runtime verification is claimed.

---

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

---

## Acquisition API router extraction — PR #34

Focused regression command:

```sh
python -m unittest tests.test_acquisition_routes -v
python -m py_compile app/main.py app/api/acquisitions.py
python -m unittest discover -s tests -v
```

`tests/test_acquisition_routes.py` checks route/method preservation, acquire and queue payload mapping/defaults, invalid payloads, skip/dismiss status translation, streaming response headers, and sanitized upstream errors. PR #34 was squash-merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`. All four required workflows passed on that exact head: Python syntax #330 (run 38485830330), Docker packaging/full unit tests #237 (run 38485830207), runtime smoke #47 (run 38485830231), and validation-only multi-architecture #91 (run 38485830245). This route-only change is not expected to alter UI presentation, so manual browser testing was not required.

---

## Persisted acquisition source-skip orchestration — reconstructed PR #48

Run focused regression tests with `python -m unittest tests.test_acquisition_orchestration -v`, then the full `python -m unittest discover -s tests -v` suite and syntax checks. Direct tests must cover successful persistence for a downloading acquisition with eligible fallback candidates and rejection of missing, dismissed, non-downloading, and no-fallback states without mutation. Verify the MCP adapter still serializes the same JSON response shape, the transition remains under the shared lock, and the SQL update is conditional on `status='downloading'`. Run all four required exact-head workflows: Python syntax, Docker packaging/full unit suite, container runtime smoke, and validation-only multi-architecture image validation. Do not publish or deploy.

---

## Acquisition cleanup, recovery, and source-switch extractions — PRs #54–#56

- `tests/test_acquisition_cleanup.py` directly imports `acquisition_cleanup.py`; it covers successful cleanup of the identified album folder, refusal for unsafe/ambiguous targets and unexpected files, and preservation of neighboring content. PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed syntax/acquisition safety (run `38600688719`), Docker packaging/full unit suite/image build (`38600688787`), container runtime smoke (`38600688814`), and validation-only multi-architecture build (`38600688667`). Merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- `tests/test_acquisition_recovery.py` directly imports `acquisition_recovery.py`; preserve checks for dismissed/non-importing states, strict completion matching, mount/filesystem identity, exact destination, manifest validation, symlink refusal, and staged-file rollback. PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety (`38601516322`), Docker packaging/full unit suite/image build (`38601516096`), container runtime smoke (`38601516565`), and validation-only multi-architecture build (`38601516203`). Merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- `acquisition_source_switch.py` is exercised by direct-import regression tests for cleanup refusal as a hard stop, no-fallback handling, failed fallback cleanup, and successful fallback persistence. PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety (`38602255318`), Docker packaging/full unit suite/image build (`38602255282`), container runtime smoke (`38602255326`), and validation-only multi-architecture build (`38602255378`). Merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- For future changes to these modules, run the relevant focused direct-import tests, `python -m py_compile acquisition_cleanup.py acquisition_recovery.py acquisition_source_switch.py navidrome_server.py`, and `python -m unittest discover -s tests -v`, then all four required workflows on the exact final PR head. Keep the legacy adapters/MCP callers and Docker packaging in sync.
- These CI results do not establish live slskd behavior or production filesystem recovery/deletion. No separate local test run, production cleanup/recovery, image publication, deployment, or production runtime verification is claimed. The reported dismissal HTTP 409 remains deferred because it was not reproduced. GHCR publication remains paused until the roadmap is complete and the user explicitly authorizes release.

---

### Acquisition watcher extraction — PR #57

- First CI attempt failed one test assertion: status details are passed as the fourth positional argument, not keyword arguments. The test was corrected.
- Corrected head `6793c339464c9d573c02f5e7dc91d15b5f568348`: syntax/acquisition safety run `38604931720`, Docker packaging/full suite/build `38604931649`, container runtime smoke `38604931792`, and validation-only multi-architecture build `38604932002` all succeeded. Publishing remains paused.
- After the final documentation update, all four workflows passed on exact head 9f201e247c092ca74f805b8ca8a1cb6f872b3cba; PR #57 was subsequently squash-merged from tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. No separate local test run or live slskd/production filesystem verification is claimed.


- **Final documentation-updated PR head:** `9f201e247c092ca74f805b8ca8a1cb6f872b3cba` passed syntax/acquisition safety `38605193852`, Docker packaging/full suite/build `38605193845`, runtime smoke `38605193808`, and validation-only multi-architecture build `38605193820`. All four required workflows succeeded; image publishing remains paused.

---

## Acquisition state persistence extraction — PR #59

- `tests/test_acquisition_state.py` directly imports `acquisition_state.py` and covers persistence round-trip, normalized identity, metadata preservation on partial updates, invalid identity rejection, and malformed JSON decoding.
- For changes to this module, run focused `tests.test_acquisition_state`, syntax checks, the full unit suite, and all four required exact-head workflows (compile/acquisition safety, Docker packaging/full suite/build, container runtime smoke, validation-only multi-architecture).
- PR #59 exact head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed all four workflows: compile `116019930318`, test/build `116019925188`, smoke `116019924747`, multi-architecture validation `116019926066`. Merge commit: `730ae16e613f3962c488f87c8de54034db7463dd`.
- Tests do not establish live slskd behavior, production filesystem operations, publication, deployment, or production runtime health.

---

## Acquisition transition guard — PR #61 closeout

- Exact tested PR head: `aa554ff2be2a19e215538ed2e699b8036764dca1`; squash merge `73172847535d3683facfbe559706c26a8637a3d4`.
- All four required exact-head workflows passed: Python syntax/acquisition safety `38617537652`, Docker packaging/full unit suite/build `38617538490`, container runtime smoke `38617537978`, and validation-only multi-architecture image validation `38617538229` (publishing paused).
- Direct-import regressions cover shared-lock critical-section ordering, no source switch after dismissal, callback result preservation, and exception propagation. No separate local test run or live slskd/production filesystem behavior is claimed.

---

## Login-page design-system alignment — PR #66 (merged 2026-10-14)

- Change is limited to `static/login.css`; no template, JavaScript, auth/API behavior, or data model changes.
- Exact tested PR head: `d0b13b7411b9b300b78b24a8944348b7e57d4b65`; squash merge: `717b1ad08e5de54e2dd8c11c2734976d75ce2e5f`.
- All four required exact-head workflows passed: syntax `38639793800`, Docker packaging/full unit suite `38639793772`, container runtime smoke `38639793518`, and validation-only multi-architecture `38639793667` (publishing paused). Reported tests: 15 focused auth/integration tests and 185 full-suite tests with one pre-existing skip.
- Manual report/screenshots were published in PR #66 comments. Reported pass: desktop 1280×900, narrow 375×720, failed sign-in message/layout/button recovery, and login assets/auth-status network responses. The report marks keyboard-focus modality and first-run setup variant as skipped; do not treat those two as verified by the report.
- Future UI PRs should retain desktop/narrow responsive checks, keyboard Tab confirmation for focus-visible styling, setup and sign-in variants where applicable, status/error recovery, and the outstanding performance observation on the next UI-facing change.

---

## Acquisition import source-root race hardening — PR #103

- The import module pins source and destination-parent directory descriptors without following symlinks, then uses descriptor-relative staging/moves/rollback to prevent a source-root path swap from redirecting file movement.
- Regression coverage includes source-root symlink replacement after matching, collision-suffixed matching, cross-filesystem fallback, and rollback. Preserve existing no-overwrite destination checks, verified track matching, mount/device checks, and recovery-manifest behavior.
- PR #103 final tested head `9de78c268af1b640a2a08afecb25a22502322a85` passed all four required workflows: syntax `38726626891`, Docker packaging/full suite/build `38726626846`, runtime smoke `38726626956`, and validation-only multi-architecture validation `38726626910`. Squash merge: `cf40df35a76d669421dcddbafd21ea22652bd0b1`. Publishing remains paused.
- No separate assistant-local test run or live slskd/production filesystem verification is claimed.

---

## 2026-10-15 — Settings router service injection in progress

- Current implementation branch: `refactor/settings-router-service-injection`, based on `main` at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` (PR #108 merge).
- `app/api/settings.py` now uses the shared lazy `get_librarian` dependency for all twelve settings endpoints instead of importing `navidrome_server` at module import time. Existing settings functions remain the service implementation; payload mapping, defaults, response parsing, validation status codes, and sanitized 502 errors are intentionally unchanged.
- `tests/test_settings_routes.py` now supplies fake services directly and checks route/method contracts, dependency wiring, payload mapping, slskd defaults/path trimming, client validation errors, and sanitized connection failures.
- Verification state at documentation update: no local tests run; CI not yet verified for the final branch head. No image publication, deployment, or production runtime verification. Preserve the MCP adapters and legacy persistence ownership.

---

## 2026-10-15 — PR #109 implementation CI result

- Implementation commit `5a5a78aed24916aeddf01b306300850b95a56aa7` passed all four required workflows: Python syntax (`38734406727`), Docker packaging/full suite (`38734407126`), container runtime smoke (`38734406616`), and validation-only multi-architecture image validation (`38734407120`). The validation workflow's multi-architecture build step and overall job both completed successfully.
- This is evidence for the implementation commit only. Documentation closeout commits are being added afterward; the exact final PR head must be rechecked before merge. No local test run, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #109 merged: settings router service injection

- PR #109: https://github.com/abucalip/navi-librarian/pull/109; exact tested head `a6c919a4d6c45f98394ee683095888f27513f1d6`; squash merge / current main at closeout `9a2aaea98cff38a1ad3da130d0958f945bec9673`.
- The settings router now uses the shared lazy `get_librarian` dependency for all twelve endpoints. Route/method contracts, service calls, payload mapping, quality defaults, optional path trimming, validation responses, and sanitized connection errors are preserved.
- All four required workflows passed on the exact final PR head: Python syntax `38734569394`, Docker packaging/full suite `38734569197`, container runtime smoke `38734569168`, and validation-only multi-architecture image validation `38734569302`. Image publishing remains paused.
- No separate local test run, publication, deployment, or production runtime verification is claimed.

---

## Dashboard and health router injection — PR #110

- Exact tested head: `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e`; squash merge `b4015b8619f3c0db169722c347f72612996b9a1c`.
- All four required workflows passed on that exact head: syntax `38735208616`, Docker packaging/full unit suite/build `38735208619`, runtime smoke `38735208830`, validation-only multi-architecture image validation `38735208682`.
- Direct-import regressions cover route inventory, injected Navidrome ping success and sanitized failure, dashboard category balance, three list reads at count 150, case-insensitive deduplication, candidate filtering, and invalid count rejection. The first CI run exposed a wrong expected pool size; the test was corrected before the passing final head.
- No separate local test execution, publication, deployment, or production runtime verification is claimed.

---

## Lazy auth service dependency regression — PR #112 verified

- Authentication integration tests inject a fake librarian service rather than patching a module-level `app.main.librarian` binding.
- A subprocess test asserts that importing `app.main` does not import `navidrome_server.py`. Existing setup, duplicate setup refusal, credential validation, login failure/success, rate limiting, logout cookie clearing, session reuse/tampering, HTTPS cookie policy, public assets, and protected page/API behavior remain covered.
- Exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed the required workflows: syntax/acquisition safety `38737672741`, Docker packaging/full unit suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture validation `38737672689`.
- PR #112 was squash-merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No separate local test execution, image publication, deployment, or production runtime verification.

---

## 2026-10-15 — PR #118: discovery eligibility tests use direct imports

- PR #118 moves the duplicate album-eligibility, exact artist-credit, and Various Artists regression checks out of the AST harness in `tests/test_acquisition_safety.py`; their existing direct-import coverage in `tests/test_discovery_recommendations.py` remains authoritative.
- The direct-import suite now retains the removed edge cases: live/remix/EP/compilation rejection, exact artist-credit false matches and empty credits, plus all five Various Artists aliases. The legacy AST harness now focuses on orchestration/lifecycle paths that still require the monolithic adapter's shared state and stubbed I/O. No runtime code or MCP behavior changed.
- Branch: `test/migrate-discovery-eligibility-direct-import`. Code/test head `873f47328de0808c8d18e034d5a7d04e39a083f2` passed all four required workflows: syntax `38745139119`; Docker packaging/full suite/build `38745139114` (238 tests passed); runtime smoke `38745139370`; validation-only multi-architecture image validation `38745139332`. Final PR head `4db6654678f9ce091caf43b650c04039c15dd6ef` also passed all four: syntax `38745425843`, Docker packaging/full suite/build `38745426466`, runtime smoke `38745425909`, and validation-only multi-architecture image validation `38745426093`. PR #118 merged to `main` at `9b1ba91923321a835e8bd3a210dd6aaf01caefc2`. No local test run, image publication, or deployment is claimed.

---

## 2026-10-15 — PR #121 merged: reject ambiguous acquisition cleanup paths

- PR #121 merged to `main` at `8e53fe83c11db6592d4716e6b5002a360cf8b763` from exact tested PR head `cbba06ce919cab8bd97d939544f489ab8e859ae7`.
- `acquisition_cleanup.py` now rejects absolute paths, Windows drive-qualified paths, repeated separators, and explicit dot segments instead of silently normalizing malformed remote paths into a different source identity. Parent traversal remains rejected; ordinary relative paths using either slash style remain supported.
- Added direct-import regression cases proving malformed paths refuse cleanup before transfer lookup and leave local files untouched.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `38750890697`; Docker packaging/full unit suite/build `38750890576`; container runtime smoke `38750890609`; validation-only multi-architecture image validation `38750890533`. The full unit-test and build job passed; no separate local test run is claimed.
- No live slskd operation, production deletion test, image publication, deployment, or production runtime verification. This change does not diagnose or claim to fix the deferred acquisition-dismissal HTTP 409.

---

## 2026-10-15 — PR #122 merged: validate remote transfer source identity

- PR #122 merged at 3bb8a5154915d82cc8b831af7a1dacb4a9384864 from exact tested PR head 55a14c0f9c6c7dbe35e4b3deee4b33b9ffd9c28d.
- Acquisition cleanup now validates a transfer filename even when slskd supplies _transfer_directory. If both filename and directory identify a folder, they must agree; unsafe absolute and drive-qualified filenames are refused before cancellation. The same identity check runs during post-cancellation verification, while basename-only transfer filenames remain supported when an explicit directory is present.
- Direct-import regressions prove mismatched directory metadata, absolute paths, and Windows drive-qualified paths refuse cancellation and preserve local files.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety 38751732156; Docker packaging/full unit suite/build 38751732263; container runtime smoke 38751732282; validation-only multi-architecture image validation 38751732196. Publishing remained paused.
- No separate local test run, live slskd operation, production deletion test, image publication, deployment, or production runtime verification is claimed. This is not a diagnosis or fix for the deferred acquisition-dismissal HTTP 409.

---

## 2026-10-15 — PR #129 verification and merge

- PR #129 merged at `b3db4d1d3ac3367a306435e0e3e50e7e3286ce22` from final tested head `d6f57b95f1cd77f58d1636f471a8f80bc9776f61`.
- All four required exact-head workflows passed: syntax `38762802954`, Docker packaging/full unit suite/build `38762802863`, runtime smoke `38762803101`, and validation-only multi-architecture image validation `38762803211`.
- No separate local tests, publication, deployment, or production runtime verification are claimed.

---

## 2026-10-15 — PR #132 navigation indicator verification

- Exact tested PR head: `b4982260a4e5697ee02766f47d35f7182303387a`; merged by squash at `44b03d6e6293e1a1ba34803104f52c4e443d245b`.
- All four required workflows passed on the tested head: Docker packaging `38766740766`, container runtime smoke `38766741159`, Python syntax `38766741253`, and validation-only Docker image validation `38766741247`.
- Manual browser checklist passed 8/8 on the exact tested head. Report: https://github.com/abucalip/navi-librarian/pull/132#issuecomment-6196780079.
- Headless checks recorded in the PR body covered indicator alignment, transform-only animation, one `aria-current`, scoped filter, mobile layout, reduced motion, keyboard reachability, all eight page headings, viewport overflow, and browser/page errors. No separate local test run, image publication, deployment, or production runtime verification is claimed.

---

## PR #140 — settings connection extraction (2026-10-15)

- Exact PR head `cacdbc809f35040f0cc1bc70a39251ff80b7315e`: all required CI workflows passed — Python syntax `38784634643`; Docker packaging/full unit suite/build `38784634599`; container runtime smoke `38784635107`; validation-only multi-architecture image validation `38784634797`.
- PR #140 merged as `aabd7d1347d8e4c363d8b97bb6c106310f1135bb`. These results are CI evidence only; no separate local test run or production runtime verification is claimed.

---

## 2026-10-15 — PR #145 UI verification

- PR #145 tested head `421d1d2860945548aa01677847ce0953b7c9f263` passed the manual browser checklist 8/8 with zero failures; report: https://github.com/abucalip/navi-librarian/pull/145#issuecomment-6200647429.
- The report covers app startup/setup, dashboard/artwork, discovery, navigation/modal, settings, Get/request, acquisition cards, and unexpected browser/server errors. It is tied to the exact PR head.
- The report does not claim real screen-reader testing; isolated artwork checks used a placeholder. Four required CI workflows passed on that exact head: syntax `38794301415`, runtime smoke `38794301446`, Docker packaging `38794301460`, and validation-only image validation `38794301405`. Publishing remains paused.

---

## Subsonic collection normalization extraction — completed (PR #153)

PR #153 merged at `b7d8ec989e2a3d398b2ca4d14a30c59ae60543cc` from exact tested head `c834383b7484f3c149679d62812f1c81f6133625`. Direct-import regression cases cover `None`, scalar, empty-list, and populated-list values. All four required exact-head CI workflows passed: Python syntax check, Docker packaging validation/full suite/build, container runtime smoke, and validation-only multi-architecture image validation. No separate local test execution, image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — MCP tool registration separated from shared service imports

- Moved the 27 existing MCP tool registrations into the new mcp_registry.py; navidrome_server.py no longer imports MCPServer, constructs an MCP server, or decorates service functions at import time.
- The legacy MCP entry point remains compatible: when navidrome_server.py is executed directly, it creates the server through create_mcp_server() and runs on the existing streamable HTTP host/port. Tool names and function objects are kept in an explicit ordered registry.
- The web service can now import navidrome_server.py without loading mcp.server.mcpserver. MCP registration is deferred to explicit server startup; the MCP package and legacy tool surface are retained.
- Added tests/test_mcp_registry.py to assert the registry contains 27 unique tools, registers each provided function exactly once, and importing the legacy service keeps all registered functions callable without importing the MCP SDK.
- Branch: refactor/separate-mcp-tool-registration. All four required workflows passed on exact implementation/documentation head fe71a9a19188a018a2ee65d5b313a99413d239f2: Python syntax/acquisition safety run 38783091362; Docker packaging/full suite/build run 38783091326; container runtime smoke run 38783091309; validation-only multi-architecture run 38783091337. Publishing remains paused. No separate local test execution, deployment, or production runtime verification is claimed. PR #138 merged at 197863830471bbd63eed57a11cafd815aede7f00 from exact final PR head 05d0eaf9a2e1ca94f3f03251208059540d06772f. All four required workflows passed on that exact head: syntax/acquisition safety 38783296279; Docker packaging/full suite/build 38783296173; container runtime smoke 38783296256; validation-only multi-architecture 38783296249. Publishing/deployment remain paused; no production runtime verification is claimed.

---

## Proxmox MCP command allowlist — PR #114 merged

The separate root-level `server.py` is a host-side Proxmox MCP entry point and is not copied into the Librarian application image. Its `run(command)` tool previously forwarded arbitrary caller input to SSH despite describing the input as allowlisted. PR #114 adds a standalone strict allowlist for the documented diagnostic forms and refuses all other input before subprocess invocation. The MCP tool schema, SSH target/options, timeout, and output truncation for accepted commands are unchanged.

PR #114 exact head `cd8319696180875a3cb6f0dc151d88e0c8c490d7` passed syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`. Squash merge: `6ab848d444373dfa37e6d46528a2840a53a8f763`. No live Proxmox command, publication, or deployment was performed.


---

---

## 2026-10-15 — PR #108 merged: discovery router service injection

- `app/api/discovery.py` uses `Depends(get_librarian)` from the shared lazy dependency module, matching the acquisition router. Importing the discovery router no longer imports `navidrome_server.py` directly.
- Existing discovery functions still own recommendations, list generation, candidate filtering, and feedback persistence. `app/main.py`, settings routes, and MCP runtime retain their legacy server integration; no MCP tools or domain behavior were removed.
- PR #108 merged at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` from tested head `a5170e50080c0ca94b4068155ace83fd33c6f029`; all four required CI workflows passed. PR #112 was squash-merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. No publication, deployment, or production runtime verification.

---

---

## 2026-10-15 — Import source-root safety merged (PR #103)

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- Import pins source and destination-parent directory chains with no-follow flags, validates matched file identities, and uses descriptor-relative staging, publication, and rollback. Cross-filesystem copy fallback remains supported.
- The source-root symlink-swap, collision-suffix, cross-filesystem, and rollback regressions pass with all four exact-head workflows. No production-folder test or deployment is claimed.

---

---

## 2026-10-15 — Cleanup root traversal hardening merged (PR #100)

- PR #100 extends the directory-swap defense by opening the configured absolute root from `/` one component at a time with no-follow directory flags and checking its preflight device/inode identity after external callbacks.
- Cleanup validates the exact planned entries and file identities/sizes, then unlinks relative to the pinned target descriptor. Regressions cover target-folder and ancestor-folder symlink swaps. Exact-head CI passed; no production-folder deletion test is claimed.

---

---

## 2026-10-15 — Acquisition cleanup filesystem boundary hardened

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- `acquisition_cleanup.py` now uses no-follow directory descriptors and descriptor-relative unlink/rmdir after external transfer callbacks; device/inode checks reject a changed directory or file. The symlink-swap regression and all four required exact-head workflows passed. No production deletion test or deployment is claimed.

---

---

## 2026-10-15 — Acquisition request coordinator merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- The coordinator owns request decision sequencing through injected dependencies. The legacy MCP/web adapter, shared locks/state, persistence, watcher lifecycle, and acquisition implementation retain their existing ownership boundaries. All four required workflows passed on the exact PR head.

---

---

## 2026-10-15 — Last.fm settings policy boundary merged

- PR #97 merged at `ad239a59b77612b812ca842406fee7b47cf80889` from exact tested head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`.
- `service_settings.py` owns Last.fm API-key update policy behind injected settings read/write callbacks. `discovery_set_lastfm_settings` remains the MCP/web adapter with its existing signature and JSON response; SQLite persistence/schema and connectivity testing remain in `navidrome_server.py`.
- Responses expose only `api_key_configured`, never the key. Exact-head CI passed all four required workflows; no publication, deployment, or production runtime verification.

---

---

## 2026-10-15 — slskd settings policy extracted (PR #96)

- `service_settings.py` now owns the pure slskd configuration validation, safe settings serialization, and update policy behind injected persistence/path callbacks. `navidrome_server.py` retains MCP adapters and remains the owner of SQLite persistence, connection tests, and runtime `MUSIC_DIR`.
- Quality priority validation rejects invalid tiers before writes. The API key remains write-only in settings responses, and the runtime music directory changes only after settings persistence succeeds.
- Exact implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four required workflows; the documentation-updated head must be checked again before merge. The web app still imports the legacy module, so MCP retirement is not in scope.

---

---

## 2026-10-15 — Settings-policy boundary follow-up

- PR #95 moved Navidrome, ListenBrainz, and Last.fm settings policy to direct-import `service_settings.py`; legacy MCP/web adapters and persistence ownership remain in `navidrome_server.py`.
- The next extraction moves only slskd configuration validation and settings read/update policy behind injected callbacks. HTTP connection testing, SQLite persistence, and the global music-path owner stay in the legacy module. This remains an incremental boundary; the web app still imports `navidrome_server.py` and MCP retirement is not in scope.

---

---

## 2026-10-15 — Dismissal-serialized import guard merged (PR #78)

- `acquisition_orchestration.import_source_unless_dismissed` owns the transition-lock/dismissal/callback guard. `navidrome_server.py` retains the compatibility adapter and the filesystem-safe import coordinator.
- PR #78 exact tested head `e6a609ca7381d0751d529b52f55aeebd56d76661` passed all four required workflows; squash merge `5d638c7adf5a42fdac8052cb4fc223236564cd72`. No filesystem safety logic was moved.

---

---

## 2026-10-15 — Search polling extraction merged (PR #76)

- `slskd_search_polling.py` now owns progressive query submission, search-state/response polling, count aggregation, peer payload deduplication, delayed-payload waiting, and per-attempt diagnostics behind injected external dependencies.
- `navidrome_server.py` remains responsible for configuration, candidate interpretation, acquisition status, queueing, and lifecycle transitions. The legacy MCP/web adapter contract is unchanged.
- PR #76 exact tested head `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6` passed all four required workflows; squash merge `a55a9fa7eed1e221f52434b50f44d0c415fd491a`.

---

---

## Settings route boundary — PR #33

The settings endpoints for Navidrome, Last.fm, ListenBrainz, and slskd are grouped in app/api/settings.py. The route module adapts HTTP payloads and delegates behavior to existing librarian domain functions. app/api/utils.py owns the shared parse_result adapter; app.main imports that symbol to preserve callers while registering the router. Authentication middleware, URL paths, methods, and response/error contracts are intended to remain unchanged.

---

## Acquisition route boundary — merged PR #34

The acquisition endpoints (`/api/acquisitions*` and `/api/acquire*`) are being moved to `app/api/acquisitions.py`. The router delegates to existing `navidrome_server` acquisition functions; it does not duplicate lifecycle, slskd, streaming state, or filesystem safety logic. `app.main` registers the router alongside settings routes. This behavior-preserving route extraction is merged. Direct-import regression tests cover route inventory, payload/default mapping, input validation, skip/dismiss status translation, streaming headers, and sanitized errors. All required CI workflows passed on exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`; merge commit is `3aac576c42465420b9c2144c2cd2f4377c5e0ff1`.

---

## Discovery API route boundary — merged PR #35

The recommendations, cached discovery-list, refresh, and feedback HTTP handlers are grouped in `app/api/discovery.py`. The router adapts request parameters and responses while delegating recommendation filtering, ownership behavior, persistence, refresh coordination, and feedback semantics to existing `navidrome_server` functions. `app.main` registers the router alongside settings and acquisition routes. Direct-import route tests cover route inventory, defaults, validation, payload mapping, and sanitized failures. This extraction preserves existing URLs and delegates domain behavior to existing functions. All four required CI workflows passed on exact PR head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`; merge commit is `d61162b29c6f0cccc97aefe9c779567e671651b2`.

---

## Metadata API route boundary — merged PR #36

Artist biography, album-year, album-details, and artwork endpoints plus their external-provider HTTP client and in-memory cache/rate-limit helpers are being separated into `app/api/metadata.py`. The router preserves provider matching rules, cache TTLs, MusicBrainz request pacing, and the non-fatal fallback behavior for optional metadata. Regression coverage is in `tests/test_metadata_routes.py` and `tests/test_artwork_retry.py`. All four required workflows passed on exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`; merge commit is `15011614649470c9c71734422b95ee048fbf9f3c`. The initial CI run exposed an AST-based test coupled to the old handler location; the test was updated to exercise the extracted module directly, and all required workflows passed on the corrected head.

---

## Authentication security primitives — merged PR #37

Pure authentication primitives are being separated into `app/security/auth.py`: persistent signing-secret loading, username/password policy checks, PBKDF2 password digest, and signed-session creation/validation. `app/main.py` retains compatibility wrappers and continues to own persistent-settings access, cookie policy, login/setup/logout routes, rate limiting, and HTTP middleware. The split intentionally avoids changing middleware ordering or public-path behavior. Direct tests cover token signing/expiry, username binding, password hashing, signing-secret persistence, file permissions, and fail-closed handling of an invalid secret; All four required workflows passed on exact PR head `192b084850ecbe0137b64b3dae9d07e0471198b4`; merge commit is `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3`.

---

## Persisted acquisition orchestration seam — reconstructed PR #48

`acquisition_orchestration.py` owns the persisted manual source-skip transition through injected initialization, lock, database connection, key normalization, lifecycle policy, clock, and JSON dependencies. `navidrome_server.py` retains the MCP-compatible `discovery_skip_acquisition_source` adapter. The shared transition lock and conditional update requiring `status='downloading'` are preserved. Filesystem cleanup/import authorities are unchanged; watcher orchestration, source switching, interrupted-import recovery, and top-level acquisition coordination remain outstanding.

---

## Acquisition state persistence extraction — PR #59 merged

`acquisition_state.py` now owns SQLite save/list mechanics for acquisition rows behind injected dependencies. Legacy server adapters remain. Shared transition locking, conditional dismissed-state checks, feedback projection, dismissal/import coordination, and filesystem safety remain in `navidrome_server.py`. PR #59 exact head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed all four required workflows and was squash-merged at `730ae16e613f3962c488f87c8de54034db7463dd`. Publishing/deployment/runtime verification are not claimed.

---

## Dashboard and health router boundary — PR #110 merged

PR #110 moved `/api/health` and `/api/dashboard-picks` into `app/api/dashboard.py` behind the shared lazy `get_librarian` dependency. The extraction preserves the legacy service calls, response shapes, count validation, category balance, deduplication, randomization, and sanitized health errors. Exact tested head `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e` passed all four required workflows and was squash-merged at `b4015b8619f3c0db169722c347f72612996b9a1c`. `app/main.py` still imports the legacy module for authentication settings and data-directory/auth-secret initialization; MCP compatibility and persistence ownership remain unchanged.

---

## Lazy authentication service dependency — PR #112 verification

`app/main.py` no longer imports `navidrome_server.py` to define the web app. Authentication settings access and signing-key initialization call the existing service lazily through `get_librarian`. SQLite persistence, `DATA_DIR` ownership, settings migrations, MCP wrappers, and auth semantics remain unchanged. Direct integration coverage verifies app import does not initialize the legacy server and auth routes work with an injected fake service.

PR #112 exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed all four required workflows: syntax `38737672741`, Docker packaging/full suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture image validation `38737672689`. No publication, deployment, or production runtime verification.

---

## Settings persistence boundary — completed (PR #143 merged, 2026-10-15)

The settings persistence implementation has been extracted from `navidrome_server.py` into `settings_persistence.py`. The store owns SQLite initialization, restrictive database permissions, persistence reads/writes, saved music-path application, and existing legacy quality/download-path migrations, using injected defaults and path callbacks. Legacy `_discovery_settings_*` wrappers preserve callers and MCP behavior; Docker packaging includes the module. Direct-import regression tests cover persistence round trips, malformed data, migration order, music-path application, and permissions.

PR #143 exact final head `e28cd12d3736fd2eb368b53c98e3cbddb5438166` passed all four required workflows: Docker packaging/full tests/build `38791730058`, Python syntax `38791730078`, container runtime smoke `38791729963`, and validation-only multi-architecture image validation `38791730017`. Squash merge: `409f634a20ba67c5a39dfec0e5bf57995a3fefbe`. Publishing, deployment, and production runtime verification remain separate and paused.

---

## 2026-10-15 — Security priority completed: Proxmox MCP command allowlist

- PR #114 merged at `6ab848d444373dfa37e6d46528a2840a53a8f763` from exact tested head `cd8319696180875a3cb6f0dc151d88e0c8c490d7`.
- The host-side Proxmox MCP now accepts only explicitly approved diagnostic command forms and rejects arbitrary shell execution before SSH. Direct-import regressions cover accepted and rejected inputs.
- All four required exact-head workflows passed: syntax `38740491280`, Docker packaging/full suite/build `38740491274`, runtime smoke `38740491268`, and validation-only multi-architecture validation `38740491281`. Publishing/deployment remain paused; the host-side MCP is not part of the application image.
- **Next (superseded 2026-10-16):** continue the modularization roadmap using current main/open-PR/CI evidence. Per the user's direction, keep the acquisition-dismissal HTTP 409 investigation deferred until modularization is complete; do not reopen PRs #44/#45 or claim a fix without reproduction and root-cause evidence.


---

---

## 2026-10-15 — PR #108 merged: discovery router service injection

- Merged PR #108 at `be51f0ce17fe8eccd1b57714e869db69a5f1ba78` from exact tested head `a5170e50080c0ca94b4068155ace83fd33c6f029`.
- Discovery routes now use the shared lazy `get_librarian` dependency. Domain behavior and MCP wrappers remain in the legacy service boundary.
- Updated legacy discovery route tests to inject fake services instead of patching a removed module-level `librarian` attribute.
- All four required exact-head workflows passed: syntax/acquisition safety (`38733725606`), Docker packaging/full suite/build (`38733725816`, 227 tests), container runtime smoke (`38733725595`), and validation-only multi-architecture image validation (`38733725591`). Publishing/deployment remain paused.

---

---

## 2026-10-15 — Acquisition import source-root safety merged (PR #103)

- PR #103 merged at `cf40df35a76d669421dcddbafd21ea22652bd0b1` from exact tested head `9de78c268af1b640a2a08afecb25a22502322a85`.
- The import boundary now pins source and destination-parent directories, performs descriptor-relative moves/rollback, and retains cross-filesystem fallback. Regressions cover source-root symlink swaps, collision-suffixed names, cross-filesystem behavior, and rollback; all four required exact-head workflows passed.
- **Next:** continue the highest-priority safety/test audit across remaining filesystem operations and external boundaries before routine service-boundary extraction. Publishing remains paused; no deployment/runtime verification.

---

---

## 2026-10-15 — Cleanup root traversal hardening merged (PR #100)

- PR #100 merged at `6e8e861cc84d5951b0d177ffea256a0dd88fe4b4` from exact tested head `89813bd3802b1f8920715aaeca55ccb5e461c9c9`.
- The configured root is now traversed component-by-component without following symlinks; directory and file identities plus the exact planned file set are revalidated before descriptor-relative deletion. Both target and ancestor symlink-swap regressions pass in exact-head CI.
- Resume the remaining highest-priority safety/test audit before routine service-boundary extraction. Publishing remains paused; no deployment/runtime verification.

---

---

## 2026-10-15 — PR #99 safety hardening merged

- PR #99 merged at `6a5d42148813d3b2725f5d79ca45bdecaee97c25` from exact tested head `a62cdae8fa8cf916b7a5a50038e7ae8a6dfd6df1`.
- The acquisition cleanup TOCTOU window is hardened and regression-tested; all four required workflows passed on the exact PR head. Publishing and deployment remain paused.
- **Next:** continue the highest-priority safety/test audit, especially remaining filesystem operations that cross external callbacks or filesystem boundaries, before routine modularization.

---

---

## 2026-10-15 — PR #98 merged

- PR #98 merged at `ae6635573aa57eb9303909701e6f0a5834066495` from exact tested head `9a326a095f9572cd8d50984981084d1f3f119cb4`.
- The top-level acquisition request decision sequence now lives in `acquisition_request_coordinator.py`; adapters, persistence ownership, shared locks, and watcher lifecycle remain in the legacy server boundary.
- All four required workflows passed on that exact head. Continue with the highest-priority safety/test gaps before routine service extractions.

---

---

## 2026-10-15 — PR #97 merged: Last.fm save policy

- Merged at `ad239a59b77612b812ca842406fee7b47cf80889` from exact tested PR head `91e33bf1dc15d7b5ef4712e5c06e8869509f79c7`.
- Last.fm API-key normalization, blank-input preservation, configured-status serialization, and settings-write invocation now live in `service_settings.py` behind injected callbacks. MCP/web adapter compatibility and SQLite ownership remain in `navidrome_server.py`.
- All four required workflows passed on the exact PR head: syntax `38721333335`, Docker packaging/full unit suite `38721333353`, runtime smoke `38721333332`, validation-only multi-architecture `38721333418`. Publishing remains paused; no deployment/runtime verification.
- Next: resume the highest-priority remaining test/coordination audit from the roadmap and inspect callers/tests on current main before selecting the next narrow change.

---

---

## 2026-10-15 — slskd settings policy extraction (PR #96)

- PR #96 extracts slskd configuration validation, safe settings serialization, and settings update policy into `service_settings.py`. The legacy MCP functions remain adapters; connection checks, SQLite persistence/schema, and global `MUSIC_DIR` ownership remain in `navidrome_server.py`.
- Added direct-import tests for missing/invalid configuration, secret redaction and blank-key preservation, exact quality-tier validation (including malformed non-string values), path validation before writes, and music-path callback updates. Migrated quality-priority policy assertions off the AST-executed settings adapter while preserving the AST-based persistence fixture.
- Exact implementation head `9ccc28c7ad5fb51b7409b4f9beb5dfb1a6039c5f` passed all four workflows: syntax `38665710740`, Docker packaging/full suite `38665710718` (208 tests), runtime smoke `38665710761`, validation-only multi-architecture `38665710769`. Publishing remains paused; no deployment/runtime verification.
- Before merge, verify all four workflows on the final documentation-updated PR head and review the complete diff. Continue with a caller-driven audit of remaining settings persistence and service integration boundaries; do not remove MCP while web callers still import the legacy module.

---

---

## 2026-10-15 — PR #95 merged; slskd settings-policy extraction next

- PR #95 merged at `2193306ce6ee2ff3ed087b2f490594f2d5ee2c68` from exact head `92d304d06713ec0f73253a5db48cf835ff93a063`; all four required workflows passed on that head (syntax `38665121156`, Docker packaging/full suite `38665121160`, runtime smoke `38665121170`, validation-only multi-architecture `38665121255`). Publishing remains paused.
- The next narrow seam is `_slskd_config`, `discovery_get_slskd_settings`, and `discovery_set_slskd_settings`. Move validation/serialization/update policy into `service_settings.py` with injected settings read/write and current/set music-directory callbacks.
- Preserve the MCP-decorated function names/signatures and JSON response strings, including blank API-key preservation, supported quality tiers, default quality labels, absolute download-path behavior, existing music-library directory validation, and path-update timing. Keep live HTTP connection checks and persistence/schema ownership in `navidrome_server.py`.
- Direct tests must cover secret redaction, blank-key preservation, invalid URL/quality/path no-write behavior, defaults, and the callback updating the runtime music directory only after a successful persisted write. Keep the Docker image/module list synchronized.
- No local test run, publication, deployment, or production runtime verification is claimed for PR #95.

---

---

## 2026-10-15 — Service settings policy extraction (PR #95)

- Extracted six settings-policy/configuration functions into importable `service_settings.py` with injected persistence/path callbacks. The AST-coupled test harness was replaced with direct imports against the real module.
- Preserved legacy MCP/web adapter names and signatures. Kept SQLite initialization/migrations, global `MUSIC_DIR` mutation, service connectivity requests, and other service settings in `navidrome_server.py` to keep this step narrow.
- Added `service_settings.py` to the Docker image file list. Final PR head `b0a9d4df97723bc05983fb362a9b3060587f0df9` passed all four required workflows (syntax/acquisition safety `38664285319`, Docker packaging/full suite `38664285227`, runtime smoke `38664285195`, validation-only multi-architecture `38664285194`; publishing paused). The earlier callback-injection mismatch was corrected before this final-head verification. No local test run, publication, deployment, or production runtime verification is claimed.
- After PR #95's review/merge decision, continue a caller-driven audit for the next safe direct-import seam. Do not retire MCP while the web app still imports the legacy module.

---

---

## 2026-10-15 — PR #92 merged: dismissed-acquisition preflight seam

- PR #92 merged at `60698f7bf1413e4c643309e200d1ace2e268bee3` from exact tested head `1f0ce2174e1e60f3aab7c898dd534b8b1f11e858`.
- Dismissal/reactivation preflight and retry-metadata normalization now live in `acquisition_orchestration.reactivate_dismissed_acquisition_if_needed`.
- The server retains shared transition-lock ownership and the existing refusal response. State-store conditional update and stale-source clearing remain unchanged. Direct helper tests supplement—not replace—the top-level AST success/refusal cases.
- All four required workflows passed on the exact PR head: syntax/acquisition safety `38661883721`, Docker packaging/full suite `38661883755` (203 tests), runtime smoke `38661883730`, and multi-architecture validation `38661883723` with publishing paused.
- Next: continue the remaining acquisition lifecycle AST-coupled test audit before routine modularization proceeds. Publishing, deployment, and production runtime verification remain separate uncompleted states.

---

---

## 2026-10-15 — PR #90 merged; request reservation seam extracted

- PR #90 merged at `4756ad6a7669ab77e284309ca9cd0f178e7f032a` from exact tested head `c0b4a0ebcc5fa4ef8b71441fb38d55aed8fce097`; all four workflows passed (199 tests, publishing paused).
- `acquisition_orchestration.reserve_acquisition_request` now owns the active-request identity check/add; `discovery_acquire_album` retains transition-lock ownership, ensuring persisted-state preflight and reservation stay atomic.
- `run_reserved_acquisition` owns callback execution outside the lock and reservation cleanup under the lock. The end-to-end concurrent-request AST test remains.
- Next focused seam: dismissal/reactivation preflight and metadata normalization. Preserve safe refusal when reactivation fails, conditional state persistence, and the legacy MCP adapter. Do not migrate the wrapper-level success/failure tests unless equivalent direct coverage preserves the same integration boundary.

---

---

## 2026-10-15 — Watcher-start concurrency regression verified

- PR #84 exact tested head: `398486476aacdbbefefeaee5cb79182cc0835fb8`; all four required workflows passed (syntax 38656927551, Docker packaging/full suite 38656927436, runtime smoke 38656927801, multi-architecture validation-only 38656927516).
- Added direct-import concurrency coverage without production behavior changes. The remaining AST lifecycle cases remain because they cover coordinator races, persistence-before-import, dismissed-job reactivation, incomplete saved state, and stale watcher recovery.
- Next: merge PR #84 after exact-head status confirmation, then continue identifying genuinely helper-only AST tests for safe migration. Publishing and deployment remain unverified and paused.

---

---

## 2026-10-15 — Session closeout and next test-audit boundary

- Reconciled against GitHub `main` at `f46b3618eaa8abc98b7f077698439b304a0005b7`; PR #82's documentation closeout is merged. PR #76 polling extraction and PR #78 dismissal-serialized import guard remain merged with exact-head CI evidence documented below.
- No implementation or test changes in this closeout. The next step is a test-boundary audit, not an automatic extraction: identify which remaining AST cases are pure helper behavior versus real coordinator integration.
- Prioritize duplicate-request reservation/concurrency, incomplete persisted candidate details, explicit reactivation and failed-reactivation refusal, and stale watcher recovery. Preserve conditional persistence, shared locks, filesystem safety, and recovery integration checks unless replacement coverage demonstrably exercises the same boundary.

---

---

## 2026-10-15 — PR #78 merged: import dismissal guard extraction

- PR #78 merged at `5d638c7adf5a42fdac8052cb4fc223236564cd72` from tested head `e6a609ca7381d0751d529b52f55aeebd56d76661`.
- `acquisition_orchestration.import_source_unless_dismissed` now owns the lock/check/callback guard; the shared transition lock spans the entire import callback.
- Filesystem path/mount identity validation, destination checks, persistent status transition, import staging, and rollback remain in their existing safety owners. Only the dismissal-only AST regression moved to direct tests.
- All four required workflows passed on exact head (syntax `38653493244`, package/full suite `38653493312`, runtime smoke `38653493285`, image validation/publishing paused `38653493279`); 186 tests passed.
- Next: audit the remaining AST lifecycle tests for safe direct-import migration, focusing on duplicate-request reservation, dismissed-job reactivation/refusal, incomplete saved candidate details, and stale watcher recovery. Preserve the end-to-end concurrency and persistence tests until equivalent direct tests exercise the same boundaries.

---

---

## 2026-10-15 — PR #76 merged: slskd polling extraction

- PR #76 merged at `a55a9fa7eed1e221f52434b50f44d0c415fd491a` from exact tested head `dc6800bd40c7142a3d7e0d3505dd7c43309d7ab6`.
- Extracted progressive query/poll/wait behavior into `slskd_search_polling.py`; direct tests cover fallback, delayed payloads, legacy endpoint compatibility, and unexpected HTTP errors. The AST-based end-to-end retry test remains for coordinator output semantics.
- All four required workflows passed on the exact head (syntax `38652846800`, packaging/full unit suite `38652846779`, runtime smoke `38652846790`, image validation/publishing paused `38652846819`); 184 tests passed.
- Next: audit remaining AST lifecycle tests for duplicates versus genuine coordination boundaries: simultaneous requests, conditional importing-state persistence, dismissal/import exclusion, incomplete saved details, dismissed-job reactivation/refusal, and stale watcher recovery. Preserve races, conditional writes, cancellation/cleanup refusal, and recovery behavior.

---

---

## 2026-10-15 — PR #73 merged: candidate extraction test migration complete

- PR #73 merged at `df2f79b3d18df7d13484f7e3b5e7f550a39323d3` from tested head `a33772ca1da0b6628da490b69f1dc305b6794de3`.
- Candidate grouping/ranking scenario now directly exercises `slskd_search.extract_candidates` in `tests/test_slskd_candidates.py`; no production implementation changed.
- All four required workflows passed on exact head: syntax `38652066842`, Docker packaging/full unit suite `38652066649`, runtime smoke `38652066755`, and Docker image validation with publishing paused `38652066683`.
- Next priority: inspect the remaining acquisition coordinator and AST tests for a small safe extraction seam. Preserve end-to-end query sequencing, shared-lock races, persistence transitions, cancellation outcomes, dismissal/reactivation, and watcher recovery. Do not split coordination state just to remove AST coupling.

---

---

## 2026-10-14 — PR #72 merged: pure slskd search helper test migration

- PR #72 squash-merged at `6c6157a8238691b18d2209ea2d2e1306385ec9a2` from tested head `17be72e52b39e63cad63391fb2c4e63ea55d3c26`.
- Moved six pure query/payload/path matching/diagnostic cases to `tests/test_slskd_search.py`; retained acquisition retry/wait and candidate extraction coverage in the AST harness at that point.
- All four required workflows passed on the exact tested head: syntax `38651547240`, Docker packaging/full unit suite `38651547229`, runtime smoke `38651547283`, and Docker image validation with publishing paused `38651547264`.
- No publication, deployment, or production runtime verification is claimed.

---

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

---

## 2026-10-14 — Queue dismissal regression migrated (PR #64)

- PR #64 merged at `1596161aa525896d43c37c85533e8056a742439b` from tested head `3bde365e43acbe1cc95f68d7014d899046e735f6`.
- The redundant AST-harness queue-dismissal case, adapter shim, and unused HTTP helper were removed. Direct-import coverage against `acquisition_orchestration.queue_candidate_unless_dismissed` preserves the safety assertion and tests critical-section ordering, return propagation, and exceptions.
- All four required CI workflows passed on the exact tested head; publishing remains paused. Continue with the next AST-coupled case only where direct-import coverage is equivalent or stronger.

---

## 2026-10-14 — Acquisition safety test migration follow-up

- After PR #62, removed one redundant AST-harness queue-dismissal case and its shim; equivalent dismissal-refusal coverage remains in direct-import tests against `acquisition_orchestration.queue_candidate_unless_dismissed`.
- This is a test-only migration step. Continue with the next AST-coupled case only when it can be moved to a direct-import test without reducing safety coverage.

---

## 2026-10-14 — Queue/dismissal guard extraction merged (PR #62)

- PR #62: https://github.com/abucalip/navi-librarian/pull/62
- Branch: `refactor/acquisition-queue-guard`; exact tested head `4e121eb7977bb1a51ad31f9c87d0d4984497af4d`.
- Squash merge commit: `d4a16e80f6978a58c3305bf341e370ba9708bb34`.
- Reviewed the focused eight-file diff. Extracted `queue_candidate_unless_dismissed` into `acquisition_orchestration.py`; preserved the server compatibility adapter, HTTP request construction, shared transition lock, and dismissal predicate. Added direct-import regressions for lock scope, dismissal refusal, return propagation, and exceptions; retained the AST-based safety regression.
- All four required workflows passed on the exact tested PR head: Python syntax `38619152587`, Docker packaging/full unit suite/build `38619152213`, container runtime smoke `38619152754`, and validation-only multi-architecture image `38619152728`. Image publishing remains paused.
- No local helper/manual slskd test, production filesystem operation, image publication, deployment, or production runtime verification is claimed.
- Next: continue the acquisition-coordination audit and migrate remaining AST-coupled safety tests incrementally; keep correctness and verification ahead of routine modularization.

---

## 2026-10-14 — Acquisition transition guard merged (PR #61)

- The dismissal-serialized source-switch guard is now extracted into `acquisition_orchestration.py`; the server function remains a compatibility adapter.
- PR #61 exact head `aa554ff2be2a19e215538ed2e699b8036764dca1` passed all four required workflows: syntax/acquisition safety `38617537652`, Docker packaging/full suite/build `38617538490`, container runtime smoke `38617537978`, and validation-only multi-architecture build `38617538229`. Squash merge: `73172847535d3683facfbe559706c26a8637a3d4`.
- Publishing remains paused. CI does not establish live slskd behavior, production filesystem safety, deployment, or production runtime health.
- Continue acquisition-coordination audit and migrate remaining AST-coupled safety tests to direct-import tests without reducing coverage.

---

## Verified current state

- PR #57 (watcher loop) is merged to `main` at `ae1e8b8f582c0ca0b882566d883d9a68bb2ca589`.
- PR #58 (watcher startup/reservation) is merged to `main` at `066fff8e7ef88364b1dc9cc909bfb2722118880e` as recorded by the latest repository history. Its exact tested PR head was `3f072159ef9e61f70554d315277a612005b8de4e`; all four required workflows passed on that head.
- PR #59 (acquisition-state SQLite save/list persistence) is merged to `main` at `730ae16e613f3962c488f87c8de54034db7463dd`. All four required workflows passed on exact tested head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d`.
- The latest recorded main documentation commits include `99da8ef0a9d4346b065092d6ea95002c7457bd4f`. Open PRs #44 and #45 concern the deferred dismissal HTTP 409 diagnostic/decision; PR #23 is older roadmap documentation. They are not evidence that PRs #57–#59 remain unmerged.
- No local helper test, live slskd interaction, production filesystem action, image publication, deployment, or production runtime verification is claimed for PRs #57–#59. GHCR publication remains paused pending completion of the roadmap and explicit authorization.

---

## Remaining roadmap, in order

1. **Acquisition coordination and test migration.** The watcher loop, watcher startup, and SQLite save/list mechanics have been extracted, but top-level acquisition coordination and shared transition responsibilities still need a focused audit/extraction. PR #61 extracted the dismissal-serialized source-switch guard into the importable orchestration module with direct-import tests and was squash-merged after all four required workflows passed; the shared lock, queue logic, cleanup, and persistence were preserved. Preserve the shared transition lock, conditional state writes, dismissal/import coordination, uncertain queue outcomes, cleanup refusal, strict completion matching, filesystem identity checks, and rollback. Continue migrating AST-coupled tests to direct-import tests without reducing safety coverage.
2. **Settings/configuration/service boundaries.** Move persistent settings and Navidrome, slskd, Last.fm, and ListenBrainz service access behind independently importable interfaces. Preserve secret handling, defaults, validation, data-directory behavior, and errors.
3. **Discovery orchestration.** Connect existing recommendation, discovery-store, and refresh modules through service boundaries; extract remaining list construction, feedback, provider integration, and inventory access without duplicating domain behavior in FastAPI routes.
4. **Application assembly.** Remove the remaining `app/main.py` dependency on `navidrome_server.py` for settings/auth persistence, health checks, and dashboard discovery behavior; preserve middleware and public/protected route behavior.
5. **MCP retirement.** Only after web callers and tests no longer depend on the monolith, audit all imports, entry points, dependencies, tests, docs, and compatibility needs. Remove MCP registration/runtime dependencies only after every web-required behavior has a tested owner.

---

## 2026-10-14 — PR #57 merged: acquisition watcher lifecycle

PR #57 was squash-merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. The watcher loop now lives in acquisition_watcher.py behind injected services, with the legacy MCP/web adapter preserved. Direct-import regression tests cover dismissal/recovery exits, completed transfer evidence without a verified folder (no import), and verified-path handoff to the existing safe import coordinator. Docker packaging is updated. All four required workflows passed on that exact head: syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, runtime smoke 38605511271, and validation-only multi-architecture 38605510906 (publishing paused). No separate local test run, live slskd test, production filesystem action, publication, deployment, or production runtime verification is claimed.

**Next priority:** persistent acquisition-state coordination after extracting watcher startup. Keep the strict completion matcher, safe import coordinator, cancellation/cleanup refusal behavior, and MCP compatibility unchanged.

---

## Historical record — acquisition state persistence extraction (now merged as PR #59)

`acquisition_state.py` owns the SQLite mechanics for saving and listing acquisition rows behind injected initialization, database path, identity-key, and clock dependencies. Legacy `_discovery_save_acquisition_job` and `_discovery_list_acquisition_jobs` remain compatibility adapters. The transition lock, conditional dismissed-state checks, secondary For Me feedback projection, dismissal/import coordination, and all filesystem safety operations remain in `navidrome_server.py`; this extraction must not be interpreted as moving those responsibilities. Direct-import tests cover round-trip persistence, normalized identity, preservation of candidate/settings/quality metadata on partial updates, invalid identity rejection, and malformed stored JSON. Initial CI on code head `2e7ef60177ff61cb080dfad9fa422773938159ef` caught a regression-fixture expectation mismatch (`json.loads('null')` returns `None`, matching the prior implementation); the fixture was corrected without changing production behavior. On corrected code head `29c5e6a460f1f61296680af7b1230fd5561496b4`, all four required workflows passed: compile `116019144533`, test/build `116019140196`, container smoke `116019141476`, and validation-only multi-architecture `116019141889` (publishing paused). At the time of this historical entry, documentation-updated-head verification was still required; PR #59 was subsequently verified and merged as recorded in the authoritative status section above.

---

## Priority override — acquisition lifecycle correctness and safety

PR #51 and PR #53 established refusal and neighbor-preservation coverage for destructive dismissal cleanup. PR #54 extracted cleanup to `acquisition_cleanup.py` with direct-import regression tests; exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows and merged at `982e39122a401b8b68d75e38423dbb93711b4abd`. PR #55 extracted interrupted-import recovery to `acquisition_recovery.py`; exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed all four workflows and merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`. PR #56 extracted source-switch orchestration to `acquisition_source_switch.py`; exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed all four workflows and merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`. All three retain the legacy MCP/web adapters and were added to Docker packaging. The next safety priority is to extract the watcher loop and top-level acquisition coordination with direct-import tests, while preserving cleanup refusal, mount identity, manifest/rollback, and uncertain-queue invariants. The reported HTTP 409 remains deferred because it was not reproduced. No live slskd or production-folder recovery/cleanup is claimed.

---

## Completed domain extractions

- PR #24 — acquisition completion matching: acquisition_completion.py; direct tests for filename identity and completed-folder inspection.
- PR #25 — slskd search and quality: slskd_search.py and slskd_quality.py.
- PR #27 — acquisition import safety: acquisition_import.py, including path/storage guards, no-overwrite behavior and rollback.
- PR #28 — discovery recommendation rules: discovery_recommendations.py.
- PR #29 — discovery list persistence: discovery_store.py.
- PR #30 — discovery refresh coordination: discovery_refresh.py.

These extractions are merged to main. They do not mean the monolithic server or web module is fully modularized.

---

## Acquisition lifecycle extraction — in progress

PR #47 introduces `acquisition_lifecycle.py` as a dependency-light, directly importable owner for monitor-resume eligibility, conservative cleanup classification, skip-request validation, fallback queue payload normalization, and uncertain queue-error classification. Legacy MCP functions remain compatibility adapters and continue to own database/network/filesystem I/O.

This is the first lifecycle seam, not completion of the whole orchestration extraction. Cleanup, interrupted-import recovery, and source-switching now have directly importable implementations with compatibility adapters. The watcher loop, persistent state coordination, watcher startup, and top-level acquire coordinator still live in `navidrome_server.py`. Next, extract those paths behind injected service dependencies and migrate remaining AST-coupled tests incrementally. Keep the existing completion/import safety modules as the filesystem authorities.

---

## Current route-separation stage

1. Settings routes (merged in PR #33): move the Navidrome, Last.fm, ListenBrainz and slskd settings handlers to app/api/settings.py; preserve URLs, methods, payload defaults, error codes/messages and calls into existing domain functions. Keep parse_result importable from app.main while moving its implementation to app/api/utils.py.
2. Acquisition routes: extract /api/acquire* and /api/acquisitions* with safety and streaming tests. Keep destructive logic in domain services. **PR #34 (`refactor/acquisition-api-router`):** merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`. Syntax, Docker packaging/full unit tests, runtime smoke, and validation-only multi-architecture checks all passed on that exact head.
3. Discovery routes: **PR #35 merged** at `d61162b29c6f0cccc97aefe9c779567e671651b2` from exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d`. Extracted recommendations, discovery-list retrieval, refresh, and feedback handlers into `app/api/discovery.py`; direct-import regression coverage is in `tests/test_discovery_routes.py`. All four required workflows passed on that exact head. Preserve ownership filtering and refresh/feedback semantics.
4. Metadata routes/services: **PR #36 merged** at `15011614649470c9c71734422b95ee048fbf9f3c` from exact head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`. Artist bio, artwork, album details/year, and external HTTP/cache helpers now live in `app/api/metadata.py`; regression coverage is in `tests/test_metadata_routes.py` and `tests/test_artwork_retry.py`. All four required workflows passed on the corrected exact head.
5. Authentication and app assembly: only split auth after explicit dependencies for persistent settings, session signing and middleware have been identified and covered. Keep middleware/public-path behavior unchanged. **PR #37 merged** at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3` from exact head `192b084850ecbe0137b64b3dae9d07e0471198b4`. Security primitives (persistent signing secret, username/password validation, PBKDF2 digest, signed-session generation/validation) now live in `app/security/auth.py`; routes, cookie setup, and middleware remain in `app/main.py`. All four required workflows passed on the exact head. PR #38 merged at `84da7ebfe51199a5caf63f7689fe89df8d61b553` after all four exact-head workflows passed; its new `tests/test_auth_routes_integration.py` covers setup, login/logout, rate limiting, cookie policy, session reuse/tampering, and public/protected paths. PR #39 (`refactor/auth-api-router`) was squash-merged at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact head `9187a51380d2a7ed7d27276ce4505827becaed32`. It extracts status/setup/login/logout and the login page into `app/api/auth.py`; middleware and signing helpers remain in `app/main.py` and `app/security/auth.py`. All four required workflows passed on the exact final head: syntax (`38492677728`), Docker packaging/full suite (`38492677704`), runtime smoke (`38492677708`), and validation-only multi-architecture (`38492677825`).
6. Frontend assets: **completed in PR #41**, squash-merged to `main` at `410506ea76d7181aa300edb9c05ebbd337dd7159` from exact tested head `b94dde68cccef776cea3813dbe7310eb857d170b`. Login/main HTML is in `app/templates/`; CSS/JavaScript is in `static/`; Docker packaging and auth middleware public-asset rules are updated, with regression coverage for asset delivery and external references. All four required exact-head workflows passed, and the manual report recorded eight checklist items passing. User reports navigation is noticeably snappier and no errors occurred. A distinct deliberately induced error/recovery scenario was not reported and is not claimed. See `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md` for the verification boundary.
7. MCP retirement: audit all imports, entry points, dependencies, tests and docs. Remove MCP registration and MCP-only runtime/dependencies only after the web app no longer relies on navidrome_server.py as its domain API. Keep compatibility wrappers until every consumer is migrated.

---

## Current status

Domain extractions through PR #30 and route/frontend stages through PR #41 are merged as recorded above. Acquisition safety/orchestration has since advanced through merged PRs #47, #50, and #54–#56. PR #54 extracted safe dismissal cleanup, PR #55 extracted interrupted-import recovery, and PR #56 extracted source-switch orchestration; each exact PR head passed all four required workflows and each final diff was reviewed before merge. The watcher loop, watcher startup, and SQLite save/list persistence have since been extracted in PRs #57–#59. Remaining top-level/shared acquisition coordination is still outstanding. The next implementation priority is to extract those lifecycle paths behind injected dependencies with direct-import regression tests, preserving cancellation/cleanup refusal, uncertain queue outcomes, import rollback and filesystem identity checks, persistent state transitions, and MCP compatibility. Then continue with settings/service boundaries, discovery orchestration, application assembly, and only then assess MCP retirement. GHCR publication remains disabled until the roadmap is complete and release is explicitly authorized. No local test run, live slskd interaction, production filesystem recovery/cleanup, publication, deployment, or production runtime verification is claimed for PRs #54–#56.

---

## Stage 7 — FastAPI route separation: settings routes

PR #33 extracts settings handlers to app/api/settings.py and the shared response adapter to app/api/utils.py. The app.main.parse_result symbol remains available as an imported compatibility name. Regression coverage in tests/test_settings_routes.py checks all 12 endpoint/method pairs, payload mapping, defaults, validation failures, and sanitized errors. Remaining route groups and later MCP retirement stay separate roadmap items; do not remove the legacy server until callers and compatibility are verified.

---

## 2026-10-14 — Acquisition lifecycle/orchestration dependency status

- PR #47's lifecycle policy extraction is merged at `1877dca3187f7cbde85b211d5414e558f12da502`.
- PR #48's orchestration extraction remains pending. Its current branch/head `refactor/acquisition-lifecycle-orchestration` / `115e1f9373744d361a20f0ba20c35589db0ca099` retains the pre-squash PR #47 history; the diff against current `main` includes both lifecycle and orchestration changes, and GitHub reports it is not mergeable.
- The four required workflows passed on that existing head only; do not carry that CI claim over to a reconstructed branch. No merge of PR #48, publication, deployment, or runtime verification is claimed.
- **Required next step:** reconstruct PR #48 as an orchestration-only change based on current `main`; inspect all callers, direct regression tests, Docker packaging, MCP compatibility, and filesystem safety behavior; then verify all required workflows on the exact new head before merge.

---

## 2026-10-14 — Reconstructed acquisition orchestration slice

PR #49 has been merged to `main` at `c972278566d8ec68f3755f464df1afb5a8a18f56`. PR #48's original branch still contains pre-squash history and is not the source for a direct merge. The reconstructed branch `refactor/acquisition-orchestration-reconstructed` starts from updated `main` and carries only the persisted source-skip orchestration seam, its direct regression tests, Docker packaging, and focused documentation. Keep the MCP adapter, shared transition lock, conditional downloading-state update, and existing filesystem safety modules unchanged. All four required workflows passed on final PR #50 head `9185f3c12ace7c82a61ff04c062044ab9c33cdf6` (syntax `38587910860`, Docker packaging/full unit suite `38587910842`, runtime smoke `38587911440`, multi-architecture validation `38587911187`). The reconstructed diff is ready for merge review; no reviewer submissions or inline threads were present at the time of inspection. PR #50 remains unmerged.

---

## 2026-10-14 — Persisted acquisition source-skip orchestration merged (PR #50)

PR #50 was squash-merged at `a37d29cf11657dce6d5cbc6cb928ca840fe5b206` from exact PR head `c8610fdc44ea93bcfb55a654598792aee78e7ecb`. All four required workflows passed on that exact head: Python syntax `38589006636`, Docker packaging/full unit suite `38589006609`, container runtime smoke `38589006569`, and validation-only multi-architecture image validation `38589006620`. The extracted module owns only the persisted manual source-skip transition; the MCP adapter, shared transition lock, conditional downloading-state update, and existing filesystem safety authorities remain. Watcher orchestration, source switching, cleanup execution, interrupted-import recovery, and top-level acquisition coordination remain future work. No image publication, deployment, or production runtime verification occurred.

---

## 2026-10-14 — Watcher extraction merged (PR #57)

PR #57 was squash-merged at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589 from exact tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. The watcher loop now lives in acquisition_watcher.py behind injected services, with the legacy adapter preserved. All four required workflows passed on the exact head. See the merge closeout below for run IDs and verification boundaries.

---

## Acquisition watcher startup extraction — PR #58

- PR: https://github.com/abucalip/navi-librarian/pull/58; branch `refactor/acquisition-watcher-startup`; tested head `3f072159ef9e61f70554d315277a612005b8de4e`.
- Extracted reserve → persist → status → start into `acquisition_watcher_startup.py` with injected locks, active set, persistence/status callbacks, and watcher entry point. `navidrome_server.py` retains `_discovery_start_import_watcher` as a compatibility adapter with its existing return contract.
- Direct-import regressions cover dismissed/duplicate starts, credential filtering in persisted settings, persistence failure releasing the reservation, and thread-start failure recording `monitor_error` and releasing the active marker. Docker packaging and architecture documentation are updated.
- All four required workflows passed on the exact head: syntax/acquisition safety `38609940832`, Docker packaging/full unit suite/build `38609940860`, container runtime smoke `38609940739`, and validation-only multi-architecture build `38609940737` (publishing paused).
- State: implementation and CI passed; PR #58 was subsequently merged to main at `066fff8e7ef88364b1dc9cc909bfb2722118880e`. No separate local test run, live slskd test, publication, deployment, or production runtime verification is claimed.
- Next priority: persistent acquisition-state coordination with direct-import regression coverage, preserving conditional writes, shared transition-lock behavior, and dismissal/import safety.

---

### Acquisition state persistence — PR #59 merged

- Extracted SQLite save/list mechanics into `acquisition_state.py`; legacy server wrappers remain compatible.
- Exact PR head `d22dea2dd39f287cd0c634ffbc1d276b9d735b5d` passed compile, full test/build, container smoke, and validation-only multi-architecture workflows (`116019930318`, `116019925188`, `116019924747`, `116019926066`); squash merge `730ae16e613f3962c488f87c8de54034db7463dd`.
- The next task must be selected after reviewing the live open-PR list and current roadmap. Do not assume watcher-startup PR #58 is merged; confirm its current status and exact-head checks.

---

## Front-end quality follow-up — PR #66 merged (2026-10-14)

- Login-page alignment is complete: `static/login.css` now shares the app's design tokens, type system, primary-control treatment, and focus-visible styles. PR #66 merged at `717b1ad08e5de54e2dd8c11c2734976d75ce2e5f` from tested head `d0b13b7411b9b300b78b24a8944348b7e57d4b65`.
- Exact-head syntax, Docker packaging/full suite, runtime smoke, and validation-only multi-architecture CI all passed. Manual screenshots/report are published on the PR; keyboard-focus modality and first-run setup variant remain explicitly skipped in that report.
- This visual improvement does not change the backend modularization priority or authorize image publication/deployment. Continue the safety-first acquisition coordination/test migration roadmap.

---

## 2026-10-15 — Settings router is the next injection seam

After discovery-router injection (PR #108), the next narrow step is to inject the existing service into all settings routes through `get_librarian`. Keep settings policy, SQLite persistence, runtime path mutation, and network connection checks in the existing service module; do not duplicate or relocate domain behavior. Verify endpoint paths/methods, payload/default mapping, validation and sanitized error contracts, plus all four required CI workflows on the exact PR head. `app/main.py` still imports the legacy server and remains a separate follow-up boundary.

---

## 2026-10-15 — Dashboard/health router injection in progress

- Following merged PR #109, `/api/health` and `/api/dashboard-picks` are the next small HTTP boundary in `app/main.py`. The branch moves both handlers into `app/api/dashboard.py` and injects `get_librarian`.
- Regression tests cover the endpoint/method inventory, injected Navidrome ping and sanitized failure, dashboard category balance, list-call arguments, deduplication, album-candidate filtering, and count validation.
- Read-only AST audit found the remaining lifecycle AST tests still verify the legacy `discovery_acquire_album` adapter wiring; keep them until equivalent direct coverage proves the adapter's lock/state/watcher dependency mapping.
- PR #109 merged at `9a2aaea98cff38a1ad3da130d0958f945bec9673` after all four required workflows passed on exact PR head `a6c919a4d6c45f98394ee683095888f27513f1d6`. Publishing remains paused.

---

## 2026-10-15 — PR #110 merged: dashboard and health router injection

- PR #110 squash-merged at `b4015b8619f3c0db169722c347f72612996b9a1c` from exact tested head `a2bc06ac2ca6a4ca60341f3857135b97d2d6e68e`.
- `app/api/dashboard.py` now owns `/api/health` and `/api/dashboard-picks`, using `get_librarian`; domain logic remains in the existing service. All four required exact-head workflows passed (syntax `38735208616`, package/full suite `38735208619`, runtime smoke `38735208830`, multi-architecture validation `38735208682`).
- The remaining acquisition lifecycle AST tests were retained because they verify the legacy MCP adapter's dependency wiring beyond the direct-import coordinator tests.
- **Next:** audit the remaining `app/main.py` direct `navidrome_server` dependency for auth settings reads/writes and `DATA_DIR`/secret initialization. Design a small testable injection seam that preserves setup/login/logout, cookie/session semantics, persistent settings ownership, and MCP compatibility. Do not retire MCP or move persistence without a separate evidence-based plan.

---

## 2026-10-15 — PR #112: lazy authentication service dependency verified

- Removed the direct `navidrome_server.py` import from `app/main.py`; auth settings and signing-key storage resolve through the shared lazy `get_librarian` dependency.
- Kept persistent settings, `DATA_DIR`, secret-file permissions, MCP adapters, auth route contracts, cookie/session semantics, and middleware behavior unchanged.
- Migrated auth integration tests to an injected fake service and added a subprocess regression proving importing `app.main` alone does not load `navidrome_server`.
- Exact head `ded9aef759c87ccf07d71cd777b366af424cc06c` passed syntax `38737672741`, Docker packaging/full suite/build `38737672443`, runtime smoke `38737672507`, and validation-only multi-architecture validation `38737672689`. No publication/deployment. PR #112 merged at `16c39ff11438f7a4237afa58f225777afcde6b82` after all four workflows passed on exact head `5c92f1106917fdb69f61faf959d060c0d5d64065`. Next priority: continue the web dependency audit with the remaining `app/main.py` responsibilities and keep auth/persistence ownership intact.

---

## Completed — settings connection checks (2026-10-15, PR #140)

Navidrome, Last.fm, and ListenBrainz connection-check logic is extracted into `service_settings.py` with injected dependencies; legacy public entry points remain adapters. Regression tests cover response mapping, missing configuration/profile, and Last.fm key redaction. All four required workflows passed on PR head `cacdbc809f35040f0cc1bc70a39251ff80b7315e`; merged as `aabd7d1347d8e4c363d8b97bb6c106310f1135bb`. Continue with the remaining application-assembly/domain-service boundaries; do not treat this as completion of all modularization.

---

## Subsonic response collection normalization — completed (PR #153 merged, 2026-10-15)

Moved the shared response-normalization rule into `navidrome_client.items()` and retained `navidrome_server.items()` as the compatibility adapter. Direct-import tests cover missing, scalar, empty, and populated collection values. All four required workflows passed on exact PR head `c834383b7484f3c149679d62812f1c81f6133625`; squash merge commit `b7d8ec989e2a3d398b2ca4d14a30c59ae60543cc`. Publishing and deployment remain separate and are not claimed.
