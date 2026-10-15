## slskd transfer listing extraction — verification gate

Run `python -m unittest tests.test_slskd_transfers -v`, `python -m unittest discover -s tests -v`, syntax/acquisition-safety checks, Docker packaging/full suite/image build, isolated container runtime smoke, and validation-only multi-architecture image validation on the exact final PR head. Review that `_slskd_download_transfer_files` keeps its signature and delegates to `slskd_transfers.download_transfer_files`, the new module is copied into the image, and no watcher/candidate-start semantics changed. Publishing must remain disabled. No results are claimed until the checks complete.

## Expected slskd track-count extraction — completed verification (PR #155)

Exact final PR head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6` passed all four required workflows: Python syntax/acquisition-safety regressions `38814733899`; Docker packaging, full unit suite, and image build `38814734001`; isolated container runtime smoke `38814733916`; validation-only multi-architecture image validation `38814733954`. PR #155 merged by squash at `d732241de9edfd3c643a8fa89fb25c42b2a93c67`. No separate local test execution, image publication, deployment, or production runtime verification is claimed.

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
