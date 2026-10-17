## 2026-10-17 — Recommendation Phase 0 diagnostics and offline replay harness

- Started from GitHub main `06c4407f7185db1abfecdad256d7bfd6821327e1`, after confirming no open PRs. Objective: implement recommendation roadmap Phase 0.1/0.2 without changing ranking.
- Added bounded pool fingerprints and one-snapshot SQLite diagnostics. Recording MBIDs and album identities are SHA-256 hashed before persistence; only the latest snapshot is retained. Diagnostics compare current and prior CF pools and final recommendation lists using Jaccard overlap and include provider/cache/source counts.
- Added deterministic offline replay metric helpers and a frozen synthetic fixture. The harness reports unowned-artist hit rate@k, nDCG@k, artist/style spread, ownership exclusions, eligibility counts, and pool/ranking overlap across contrasting cases. The fixture explicitly documents that it is synthetic, not evidence of live recommendation quality.
- Wired diagnostics into the existing recommendation response without changing selection/scoring logic. Automated tests and CI are pending; no tests have yet been run in this GitHub-only editing step. Publishing, deployment, and production runtime verification remain paused/unperformed.
- Branch: `feat/recommendation-baseline-diagnostics`. Next: inspect PR diff, run all four required workflows on the exact final PR-head SHA, fix any regressions, and only then decide whether to merge.

---

## 2026-10-17 — MCP retirement closeout

- Refreshed GitHub `main`: PR #296's retirement implementation is present at commit `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`; the earlier status/plan text incorrectly still described the PR as open and verification as pending.
- Confirmed the merged source/configuration state: `requirements.txt` no longer declares the MCP SDK; the Dockerfile no longer copies `mcp_registry.py`; Compose exposes only the web service; the web app is the supported interface. The implementation removes the MCP registry/transport and the separate un-packaged Proxmox MCP entry point while retaining shared Librarian functions and `read_only_command_policy.py` safety coverage.
- PR #296's four required workflows were reported passing on its final PR head: Python syntax/acquisition safety; Docker packaging/full unit suite/build; isolated container runtime smoke; validation-only multi-architecture. Publishing remains paused. A follow-up workflow/status query returned no records, so no new run IDs or fresh execution are claimed here.
- No local tests were run during this documentation closeout. No publication, deployment, or production-runtime verification is claimed.
- Updated `docs/MCP_RETIREMENT_PLAN.md` and `docs/PROJECT_STATUS.md` to mark repository-level retirement complete and distinguish it from external-client/configuration migration. Repository inspection cannot identify user-specific or external clients still pointing at the retired endpoint; persisted settings were not migrated.
- Documentation-only closeout branch: `docs/closeout-mcp-retirement`, based on `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. CI for this documentation follow-up remains to be checked on its final PR head. No merge/publication/deployment is claimed for this follow-up.
- Next action: verify required CI for the documentation closeout PR, merge if all required gates pass, then treat any external client migration as a separate user-environment check.

---

## 2026-10-17 — MCP retirement implementation prepared

- Audited current GitHub `main` against `docs/MCP_RETIREMENT_PLAN.md`. The 25-entry registry in `mcp_registry.py`, the `mcp==2.3.0` requirement, the Docker COPY reference, and the `navidrome_server.py` streamable-HTTP startup block were the Librarian runtime/package references. The broader audit also found `server.py`, a separate un-packaged Proxmox MCP entry point with a hardcoded SSH identity/host. `compose.yaml` defines only the web service and exposes its configured web port; no separate Librarian MCP service is configured.
- All 25 registry-referenced function definitions are retained in this focused change to avoid deleting behavior based solely on MCP registration. Web routes continue using shared service functions through the lazy adapter; any MCP-only helper definitions are no longer registered or exposed by a transport and may be reviewed separately for dead-code cleanup. Removed MCP registration/transport/package wiring, replaced the registry tests with MCP-free architecture checks, and left existing acquisition/import/cleanup safety tests intact.
- Audit uncovered that the standalone MCP block also started the discovery scheduler, while the supported Uvicorn web entry point did not. Added idempotent scheduler startup from the FastAPI startup hook so scheduled refresh remains available under the supported entry point.
- Removed the unrelated `server.py` Proxmox MCP entry point and its handler tests; retained `read_only_command_policy.py` and its rejection tests for shell composition, invalid IDs, and unsafe device paths. Updated the MCP retirement plan, requirements, test plan, workflow, status, and project log. External MCP clients or user-specific configuration cannot be determined from repository inspection; no such consumer is defined in the inspected Compose configuration.
- Branch: `retire/remove-mcp-runtime`. PR #296 is open; exact-head CI and verification evidence are pending. No local tests have been run from this GitHub-only workflow; do not infer passing tests or CI. Publishing remains paused. No deployment or production runtime verification is claimed.

---

## 2026-10-17 — Post-closeout hygiene: remove orphan patch scripts and tighten server ceiling

- Starting from `main` after PR #290 merge (`c20e931de22fe30cc3378867cbbebe56b28a91a4`), reviewed the closed modularization roadmap and size-guard/testing documentation.
- GitHub code search found no references to `patch_recommender.py` or `patch_recommender_v2.py`; neither script is part of the Docker COPY list or current server/app imports. Both are one-off source-rewriting experiments with backup/compile behavior rather than maintained runtime code, so removing them reduces ambiguity and audit surface.
- Tightened `scripts/check_server_size.py` from 3,031 to 2,650 lines, leaving 53 lines above the current 2,597-line server count measured from the fetched source with `splitlines()`. Updated the guard's docstring/comment to direct new domain logic into modules and added a regression assertion for the ceiling. Updated status, roadmap, test plan, and workflow references.
- This entry records intent only; PR/commit SHA, focused/full test results, exact-head CI, and merge state will be added after verification. Publishing remains paused; no deployment or runtime verification is claimed.

---

## 2026-10-16 — PR #288 merged: Docker recommendation import packaging fixed

- Follow-up audit after PR #286 found a second missing Docker dependency: `navidrome_server.py` imports `discovery_candidate_gathering.py`, but the explicit Docker COPY list omitted it.
- PR #288 added the module and generalized `tests/test_docker_packaging.py` to AST-inspect the legacy server and require every imported root-level Python module to appear in the Docker COPY sources. This also guards the earlier `acquisition_import_service.py` omission fixed by PR #286.
- Exact PR head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c`; merge commit `047822df81b134084383ed370205b1a3554c706a`.
- All four required workflows passed on that exact head: syntax `38978049684`, Docker packaging/full unit suite/build `38978049670`, runtime smoke `38978049793`, and validation-only multi-architecture `38978049589` (publishing paused). No local tests, deployment, or production-runtime verification are claimed.
- Post-merge review compared current `navidrome_server.py` root-level imports with the Docker COPY list: all 48 distinct imported root modules are included. This does not yet prove transitive or dynamic imports are fully packaged; the final modularization audit remains open.
- Next: inspect transitive imports of packaged root modules and the exact-main dependency-map artifact, then review dynamic/runtime imports and compatibility/safety coverage. Do not declare modularization complete or invent size-only extractions before that audit finishes.

---

## 2026-10-16 — Follow-up audit found another missing Docker module

- After PR #286 merged as `1cf9d66ad57364eec855b2425263e9a59b011d9a`, continued the modularization completion audit by comparing `navidrome_server.py` imports with the explicit root-level Docker COPY list.
- Found that `discovery_candidate_gathering.py` is imported by `navidrome_server.py` at line 305 but is absent from the Docker image source list. This affects the recommendation path and was not detected by the earlier audit because it focused on the import-completion module.
- The follow-up fix adds the missing module and generalizes `tests/test_docker_packaging.py` to AST-inspect `navidrome_server.py` and assert that every imported root-level Python module is copied into the image, including imports nested inside functions.
- PR and CI evidence are pending; no local tests were run. Continue the packaging/runtime audit after this fix and do not declare modularization complete until the exact-main dependency map, dynamic imports, Docker inclusion, and safety/compatibility tests have been reviewed. Publishing remains paused.

---

## 2026-10-16 — PR #286 merged: Docker acquisition import service packaging fixed

- Completion audit of GitHub `main` at `1f8f37ba7f9c289b694b1089492ba7a3cfdacf82` found that `navidrome_server.py` lazily imports `acquisition_import_service.import_completed_source_locked()` during import completion, but the explicit root-module COPY list in `Dockerfile` omitted `acquisition_import_service.py`. Startup alone did not exercise this delayed import.
- PR #286 added the missing module to the Docker image and added `tests/test_docker_packaging.py` to guard the COPY list. Merge commit: `1cf9d66ad57364eec855b2425263e9a59b011d9a`; exact PR head: `de68aa4cd5cbd657bcdd1c59cdde4e2b7e1df283`.
- All four required workflows passed on that exact head: Python syntax `38977669838`, Docker packaging/full unit suite/build `38977669928`, container runtime smoke `38977669818`, and validation-only multi-architecture image validation `38977669844`. Publishing remained paused. No local tests, deployment, or production-runtime verification are claimed.
- Confirmed the AST/source-layout migration is complete in PR #274 and the documented lazy `app/api/dependencies.py:get_librarian()` import remains the only permitted app-to-legacy edge.
- Next: finish the modularization completion audit against exact current `main`, including the generated dependency-map artifact, dynamic/runtime imports, Docker module inclusion, and compatibility/safety coverage. If no concrete gap remains, close modularization without inventing another extraction.

---

## 2026-10-16 — UI PRs #222, #279, and #282 merged

- Owner confirmed all three UI changes were manually tested and explicitly waived the older manual-report requirement for this merge set. The changes were reviewed as UI-only; #222 updates the dashboard coverflow ring and its keyboard contract, #279 adds the async Get-button visual/state treatment, and #282 removes the redundant colored toast side border.
- PR #222 exact head `5b55527ec3a13aaa137ed3d56341fb029913f09f`: all four required workflows passed (Python syntax, Docker packaging/full unit suite, container runtime smoke, and non-publishing multi-architecture validation). Squash-merged as `880fc34b43012f235fd0920bacd6ba644ecf3713`.
- PR #279 exact head `b3f44942724b6f9c6865f6c9160a69e58715b28a`: all four required workflows passed. Squash-merged as `48675a803ef6a74dbb5782a1c87fdacd2c278b76`.
- PR #282 exact head `cbe30a5bf26e503f1cb455861b32a5064b3604ab`: all four required workflows passed. Squash-merged as `71eb20bc734f1113f81b62eef35e17d53b8adf8e`.
- Merge order was #222, #279, then #282. GitHub reported successful merges and each PR is now closed/merged. The commits were reviewed as non-overlapping functional regions despite shared UI asset files; GitHub mergeability was refreshed before the final merge.
- No assistant-side local tests or browser tests were run in this session; manual testing is recorded as owner-reported. No publishing, deployment, or production runtime verification was performed. Publishing remains paused.
- Next: continue from the modularization roadmap only where a concrete, testable responsibility boundary justifies the work.

---

## 2026-10-16 — PR #270 merged: import-completion service extraction

- Based on GitHub main after PR #268 merge `d5f48cd5666ccbe2ab318516b7ed9fba0fa37fee`. Added `acquisition_import_service.import_completed_source_locked()` with injected path naming, authoritative status persistence, hardened import operation, and clock dependencies. The legacy `_discovery_import_completed_source_locked()` is now a narrow adapter; the outer transition-lock/dismissal guard is unchanged.
- Added direct-import tests for failure to persist `importing` (no filesystem mutation), successful status ordering and mount identity arguments, symlinked artist destination refusal, existing destination preservation, and unavailable library roots. The existing AST-based compatibility test remains in place and now executes the thin adapter, so this extraction does not remove lock/dismissal coverage.
- PR #270 was rebased onto current main (`d5f48cd5666ccbe2ab318516b7ed9fba0fa37fee`) on branch `refactor/acquisition-import-service-main`; final PR head is tracked by GitHub. All four required workflows passed on exact final PR head `6f2a32656f399b1bde64e4746d6f5626a60678d0`: Python syntax/acquisition safety, Docker packaging and full unit suite, container runtime smoke, and non-publishing multi-architecture validation. No separate local tests were run. Publishing remains paused; deployment/runtime on production is unverified.
- Status: merged as `d84d74c1cfa295e3c3fd2ff1594fa1758dc69949` after final diff review; all four required workflows passed on exact PR head `6f2a32656f399b1bde64e4746d6f5626a60678d0`. PR #269 was closed as superseded to avoid merging its stale base. Publishing remains paused; no deployment/runtime verification.


---

## 2026-10-16 — Acquisition coordinator policy/orchestration audit

- Audited GitHub `main` at `cd5d0240c1ac696417727de938736a1b15f7582b`. `_discovery_acquire_album_impl()` spans lines 2341–2618 and is 278 lines by the existing AST size measurement.
- Traced its responsibilities to extracted owners: `slskd_search_polling.collect_search_responses()` handles search polling; `_slskd_extract_candidates()` handles candidate policy; `acquisition_lifecycle.queue_failure_action()` classifies queue errors; existing adapters/services handle dismissal-serialized queueing, source-start checks, safe cleanup/source switching, and watcher startup.
- Remaining inline rules are interleaved with the orchestration: cap attempts at ten clear candidates; distinguish source rejection from fatal HTTP authorization/configuration errors; monitor uncertain queue outcomes rather than risk duplicate downloads; clean a definitively stopped source before fallback; and terminate when cleanup cannot be confirmed. These are safety-critical transitions, but no smaller cohesive policy API was identified that would reduce coupling rather than duplicate the orchestration.
- **Decision: retain `_discovery_acquire_album_impl()` as orchestration.** No application code changed and no tests were run for this audit. The size guard already tracks its 278-line size; do not extract it for size alone.
- Next: trace and migrate the remaining AST-coupled import-safety test in `tests/test_acquisition_safety.py` only after identifying a direct-import production owner and preserving destination path, filesystem mount identity, no-overwrite, and importing-status persistence-failure coverage. Operational MCP functions remain blocked on explicit owner decision.

---

## 2026-10-16 — Mutable MUSIC_DIR coupling audit

- Audited every MUSIC_DIR occurrence in the current navidrome_server.py source fetched from GitHub main (3,031 source lines; 3,032 split fields including the trailing empty element): initialization at line 88; persistence callback wiring at 218; raw library tag scan at 230; settings defaults and downloads fallback at 1517/1531; central and nested writers at 1545–1546, 1591–1592, and 1665–1666; settings-get adapters at 1580 and 1651; and acquisition recovery/watcher dependency injection at 2271/2286. Line references are audit-time references and should be refreshed before a later code change.
- Traced SettingsPersistence: its injected getter/setter separates SQLite persistence from runtime path ownership. read() applies a saved absolute path, while migration logic uses the current path to identify legacy downloads locations. service_settings.py similarly receives path getter/setter callbacks; tests/test_service_settings.py directly tests settings behavior and path updates.
- **Decision: no new settings object or wrapper extraction.** The remaining global reads are concentrated in the legacy compatibility/runtime owner, and the existing service and persistence modules already expose explicit callbacks. A new object would add indirection without removing the compatibility boundary; acquisition watcher/recovery adapters currently pass a path snapshot at invocation time, so changing ownership needs a broader lifecycle design and behavior tests, not a mechanical refactor.
- Documentation-only audit. No application tests or local commands were run. PR #267 was opened at head `e1df4f783c217fadecae57c002b8ad1a9d92766c`; the first workflow/status lookup returned no runs or status checks, so required CI is not yet verified. Recheck the final head before merge. No merge, publication, deployment, or production runtime verification is claimed.
- Next: audit _discovery_acquire_album_impl() for actual candidate-selection, source-switch, retry, and state-transition policy; keep it intact if it is only orchestration. Operational MCP functions remain blocked on explicit owner decision.

---

## 2026-10-16 — PR #265 merged: measurable legacy-server size ratchet

- Baseline measured against main after PR #264 merge commit `cb4f5aef3534e06128401ef3eed3e9ce2908b5f4`: `navidrome_server.py` has 3,031 source lines (`splitlines()`, matching the guard). On the first PR #265 CI run, AST measurements were `recommend_new_music`: 568 lines and `_discovery_acquire_album_impl`: 278 lines. The initial 3,032 count included the trailing empty element produced by splitting on a newline; the enforced ceiling is corrected to 3,031.
- Added `scripts/check_server_size.py` with a 3,031-line file ceiling, 280-line default top-level function ceiling, and a named temporary 575-line `recommend_new_music()` exception with reason and follow-up. Added pass/fail regression tests for file/function limits, exception diagnostics, and parse failures; wired compile and guard execution into the Python syntax workflow.
- Final PR head `0ac078656cf8af78cb507a9a7dfa337e1a173db7` passed all four required workflows: Python syntax/acquisition safety (`38965190861`), Docker packaging/full unit suite/build (`38965190744`), container runtime smoke (`38965190728`), and validation-only multi-architecture image validation (`38965190622`, publishing paused). The full unit suite ran 550 tests successfully; the size guard reported 3,031 source lines, `recommend_new_music()` at 568 AST lines, and `_discovery_acquire_album_impl()` at 278 AST lines.
- PR #265 squash-merged as `57ec3a594df22bba77895934535530c37d833087`. No assistant-side local tests were run. Publishing, deployment, and production runtime verification were not performed.
- Next: audit mutable `MUSIC_DIR` readers/writers before deciding whether settings-wrapper extraction is worthwhile.

---

## 2026-10-16 — PR #264 merged: recommendation provider diagnostics restored

- CI on merged PR #263 exact head `a0d0afcdc1c54b73c2227a24735f8a606bb38f6a` failed in both the Docker/unit and Python syntax/unit workflows. The unit suite ran 545 tests and reported six errors in `tests/test_recommend_new_music_characterization.py`: `recommend_new_music()` read `regional_candidates_added`, which the new provider-gathering result mapping did not return. Syntax compilation and the app-to-legacy import-boundary guard passed; Docker build was skipped after unit failure. Container smoke and validation-only multi-architecture workflows passed on that head.
- PR #264 returns `regional_candidates_added`, `regional_results_seen`, and `library_albums` from `gather_recommendation_candidates()`, unpacks them in `recommend_new_music()` before response shaping, and extends the stable response-shape characterization test to assert the regional counters. The first follow-up attempt restored the regional counter mapping but still failed because the adapter did not unpack those counters; the second CI run then exposed the same extraction-boundary issue for `library_albums`. The current follow-up fixes the provider result and adapter unpacking for all three values without changing candidate policy.
- PR #264 final head `c9635675005d995c368100688e0a8eaf5abb75ad` passed all four required workflows: Python syntax/acquisition safety (`38964596901`), Docker packaging/full unit suite/build (`38964597032`), container runtime smoke (`38964596886`), and validation-only multi-architecture image validation (`38964596916`, publishing paused). The full unit suite and syntax workflow passed on this exact head.
- PR #264 squash-merged as `cb4f5aef3534e06128401ef3eed3e9ce2908b5f4`. No assistant-side local tests were run. Publishing, deployment, and production runtime verification were not performed.

---

## 2026-10-16 — PR #263 merged: recommendation provider orchestration

- Merged PR #263 with merge commit `20728507774a210123ef91d72b7cd2370668659d`. Added `discovery_candidate_gathering.py` with an immutable `RecommendationProviders` dependency bundle for ListenBrainz, MusicBrainz, cache, Navidrome inventory, album eligibility, HTTP, and sleep dependencies. The public `recommend_new_music(count=10)` adapter remains; scoring, ownership allocation, and payload shaping remain downstream.
- CI verification is **unconfirmed**: the workflow-run lookup returned no runs for the merge commit. The initial PR run exposed six characterization failures from downstream imports; the adapter imports were restored in a follow-up commit, but no successful post-fix CI result was confirmed here. No local tests were run. Do not describe this revision as verified until characterization, full unit suite, and required workflows pass.
- Publishing, deployment, and runtime verification were not performed.

---

## 2026-10-16 — Shared raw Navidrome album inventory pagination

- Added `discovery_library_snapshot.fetch_album_inventory()`, a direct-import raw pagination helper with injected API/items callables, non-empty album-ID deduplication, and `AlbumInventoryLimitError.albums_retrieved`. Both `build_library_snapshot()` and `recommend_new_music()` now use it.
- Preserved the adapters' distinct contracts: snapshot cache, artist inventory, normalization, and persistence remain in `build_library_snapshot()`; the recommendation path still fetches fresh raw records and returns separate JSON error payloads for API failure and safety-limit exhaustion.
- Added `tests/test_discovery_album_inventory.py` for pagination, deduplication, raw record shape, safety-limit reporting, and API exception propagation. Extended recommendation characterization to pin the safety-limit response.
- PR #261 final head `4c8b621a26b9d8c4bceb8fa7e4be6d8956146fd1` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38962780709`), Docker packaging/full unit suite/build (`38962780687`), isolated container runtime smoke (`38962780674`), and validation-only multi-architecture image validation (`38962780692`, `push: false`). Full suite: 543 tests passed. No separate assistant-side local test command ran.
- PR #261 was squash-merged as `a9bc864df85a8fb643864cb128d6b70f10eb7dce`. No publishing, deployment, or production runtime verification was performed.
- Next: extract candidate gathering/provider orchestration from `recommend_new_music()` behind injected provider dependencies and verify output parity against the characterization fixtures.

---

## 2026-10-16 — Characterized Last.fm scoring and regional MusicBrainz failure

- PR #259 added deterministic tests for the current capped Last.fm popularity bonus and the behavior when regional MusicBrainz release-group searches return HTTP 503. The test asserts the personalized ListenBrainz candidate remains available and the regional failure is reported; the test HTTP client is fake.
- PR #259 final head `d39ee50b2ec0483da2a415ef81793d20d644a439` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38962391039`), Docker packaging/full unit suite/build (`38962391189`), isolated container runtime smoke (`38962391035`), and validation-only multi-architecture image validation (`38962391062`, `push: false`). Full suite: 539 tests passed. No separate assistant-side local test command ran.
- PR #259 was squash-merged as `4a82ce01cf37d0e9cff27a9f67f9a037cad23e2e`. Tests only; no production behavior changed. Publishing, deployment, and production runtime verification were not performed.
- Compared the inventory paths: both paginate `getAlbumList2` in batches of 500 up to 50,000 and deduplicate non-empty album IDs. However, `discovery_library_snapshot.build_library_snapshot()` uses a 10-minute cache, also reads artists, normalizes album records, and propagates API/safety exceptions; `recommend_new_music()` reads fresh raw records and maps inventory failures and safety-limit exhaustion to distinct JSON responses. Directly reusing the snapshot builder would change freshness, schema, and error semantics.
- Next: extract a small shared raw album-pagination helper with direct tests, preserving the two adapters' distinct cache, normalization, and error contracts. Only after that should the larger provider/candidate-gathering seam be extracted.

---

## 2026-10-16 — Expanded new-music ranking and provider characterization

- Extended `tests/test_recommend_new_music_characterization.py` with a fixed two-recording fixture proving recommendation output is ordered by discovery score rather than raw ListenBrainz order. Added assertions for the existing ListenBrainz recent-history error response and the empty-recommendation message.
- PR #257 final head `4de3a9e0488552e2f3452c00fe691fb8ce084e61` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38961968775`), Docker packaging/full unit suite/build (`38961968720`), isolated container runtime smoke (`38961968596`), and validation-only multi-architecture image validation (`38961968694`, `push: false)). Full suite: 537 tests passed. No separate assistant-side local test command ran.
- PR #257 was squash-merged as `2bbe5c28887e16c249c119634c7b33396351f540`. Tests only; no production behavior changed. Publishing, deployment, and production runtime verification were not performed.
- Remaining before extraction: characterize scoring/bonus effects and regional MusicBrainz failure behavior, and complete the comparison with `discovery_library_snapshot.py` so any inventory-schema/cache/safety-limit mismatch is explicit.

---

## 2026-10-16 — Initial new-music inventory characterization

- Added `tests/test_recommend_new_music_characterization.py` with deterministic mocked provider/cache responses. It pins the public response shape for a clear inventory, exclusion of an exact artist+album ownership match, duplicate album-ID deduplication before ownership indexing, and fail-closed behavior when Navidrome inventory retrieval raises.
- The first CI attempt on `4e52318afed32ccbfdcc61e43799a4bf72d76702` exposed one incorrect expected allocator decision (`exact_owned`); the assertion was corrected to the production contract (`already_owned`). The corrected code-only PR head `97798f8bb12bdfba9ad735ca4b5e900e634e1ca0` passed all four required workflows: Python syntax/acquisition safety and dependency map (`38961591461`), Docker packaging/full unit suite/build (`38961591460`), isolated container runtime smoke (`38961591458`), and validation-only multi-architecture image validation (`38961591546`, publishing remains disabled / `push: false`). The full suite ran 534 tests. No separate assistant-side local test command ran.
- PR #255 was squash-merged as `4d21627f4d01c7129298fa2753c518006db5ba45`. This is test-only; no production behavior changed. No publishing, deployment, or production runtime verification was performed.
- Remaining before extracting the candidate-gathering pipeline: characterize stable candidate ordering/scoring and provider failure behavior, and finish comparing the inventory semantics with `discovery_library_snapshot.py`. This PR is the initial characterization slice, not the complete acceptance gate.

---

## 2026-10-16 — Migrated slskd transfer lookup tests to direct imports

- Replaced the AST harness in `tests/test_slskd_transfer_lookup.py` with direct imports of `slskd_transfers.download_transfer_files()`. Coverage retains the missing-peer 404 behavior, propagation of other HTTP errors, URL-escaped usernames and timeout, and successful parsing with remote-directory metadata.
- Kept the legacy `navidrome_server._slskd_download_transfer_files` compatibility contract in `tests/test_slskd_transfers.py`; no production behavior changed.
- Updated `docs/architecture/AST_TEST_INVENTORY.md`, `docs/MODULARIZATION_ROADMAP.md`, and `docs/PROJECT_STATUS.md`: two AST-coupled test files remain.
- Branch: `test/migrate-slskd-transfer-lookup`. Required CI passed on final PR head `66ef76b30e3c3b0a8a30169e3fa349f75b1c6d9e`: Python syntax/acquisition-safety and dependency map (`38954108967`), Docker packaging/full suite/build (`38954109155`), container runtime smoke (`38954109044`), and validation-only multi-architecture image validation (`38954108939`, `push: false`). No assistant-side local test command ran. PR #249 merged by squash as `60cf07ffa05416355053660c1823f6af5b18716b`. Publishing, deployment, and production runtime verification were not performed.

---

## 2026-10-16 — Dependency-map execution and AST-coupled test inventory

- Audit baseline: current GitHub `main` at `be01d3ebe41abc888de24b4e5bd01d54628bb0ff`. A local `git clone` could not run because this execution environment cannot resolve `github.com`; no local checkout was used as source of truth.
- Added a step to `.github/workflows/python-syntax.yml` that runs `scripts/dep_map.py`, prints key graph metrics and direct `app/** -> navidrome_server` imports, and uploads the full JSON as the `modularization-dependency-map` artifact (14-day retention). CI executed the script on initial PR head `1f9e6313310c691e9d9844d22136182e51ca6fee`: 159 local Python modules, 71 modules in the static `app.main` closure, `navidrome_server` included in that closure, and one direct app edge (`app/api/dependencies.py`). Artifact ID `12068042162` was downloaded and inspected. This is a static graph; the edge is a lazy import inside `get_librarian()`, and `tests/test_auth_routes_integration.py` verifies the app import does not eagerly initialize the legacy server. The final PR head `25324a25643e7f688eb1be057ba62cd6222a4c04` passed all four required workflows: Python syntax + unit suite (`38951397693`), Docker packaging/full suite/build (`38951397752`), container runtime smoke (`38951397876`), and non-publishing multi-architecture validation (`38951397770`). The final artifact is `12068282349`. PR #247 merged as `26009d1321c2169859f06c75c0a8abb409425325`. No local test command ran separately; CI did execute the full suite and dependency-map script.
- Added `docs/architecture/AST_TEST_INVENTORY.md`. A repository-wide review of the 77 Python test files found three tests that parse/compile function definitions from `navidrome_server.py`: `tests/test_acquisition_safety.py`, `tests/test_quality_priority.py`, and `tests/test_slskd_transfer_lookup.py`.
- Inventory conclusion: transfer-list behavior can move directly to `slskd_transfers.download_transfer_files()`; quality policy has an existing direct implementation in `slskd_quality.quality_tier()`; search helpers have direct implementations in `slskd_search.py`. The acquisition-safety AST harness combines pure helper checks with high-risk lifecycle/concurrency/persistence/recovery behavior and must be migrated in smaller slices without deleting or weakening those cases.
- Classified other `navidrome_server` references as compatibility tests rather than AST source coupling, including lazy API service injection, app-import isolation, Last.fm/ListenBrainz/metadata adapters, slskd adapter contracts, and MCP registry behavior. Those remain valid unless the corresponding compatibility contract changes.
- Updated the roadmap, status, test plan, and architecture doc to point at the inventory and distinguish the pending generated map from completed source-test inventory.
- No test or CI result is claimed yet for this PR. No application behavior was changed; publishing, deployment, and runtime verification are not part of this audit.

## 2026-10-16 — Adopt scripted modularization audit workflow

- Adopted the audit recommendations as a gated workflow rather than treating them as permission for immediate extraction. Added `scripts/dep_map.py`, which emits deterministic AST import edges for repository Python modules and calculates the transitive local import closure from `app.main`; added focused tests for import parsing and local import resolution in `tests/test_dep_map.py`.
- Updated `docs/MODULARIZATION_ROADMAP.md`, `docs/TEST_PLAN.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/PROJECT_STATUS.md`, and `docs/ARCHITECTURE.md`. The sequence is now: generate/review the map; inventory AST/source-reading tests and move behavior coverage to direct imports without weakening safety coverage; establish an allowlist-aware `navidrome_server` app-import guard; then assess settings wrappers and the acquisition coordinator.
- Tightened the coordinator decision to one question: does `_discovery_acquire_album_impl()` contain policy (candidate selection, retry/source-switch thresholds, state transitions) or only orchestration? Keep pure orchestration in place; extract only a demonstrated policy seam.
- The generated `docs/architecture/dependency-map.json` is intentionally not fabricated in this change: it must be produced and reviewed from the exact source revision by running `python scripts/dep_map.py --output docs/architecture/dependency-map.json`.
- No local test commands were run in this session. All four required GitHub Actions workflows passed on the exact final PR head `9fc7059341d13e40ef2a800299f8e6db84c61e59`: Python syntax/acquisition-safety (`38949122909`), Docker packaging/full suite/build (`38949122831`), container runtime smoke (`38949122830`), and non-publishing multi-architecture validation (`38949122845`). PR #245 was squash-merged as `cc2613e1a03e2084f9cbce4febb83a3a24d77600`. No local tests were run separately; no publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — Classics builder boundary audit: no further extraction justified

- Traced `_build_classics_list()` on main at `b9a97b5e37aff297c836d2039763de7b166441ba`. Its only direct production reference is the classics builder registration in the discovery-list dispatch table; that call is an orchestration entry point, not a reusable policy function.
- The builder now composes already-separated responsibilities: `discovery_classics_candidates.collect_classic_candidates()` (candidate collection, normalized duplicate resolution, ownership/eligibility filtering, metadata, pacing), `discovery_classics_ratings.enrich_critical_ratings()` (bounded shortlist enrichment), `discovery_recommendations.score_classic_candidates()` / `refresh_exploration_scores()` / `diversify_classic_candidates()` (ranking and diversity), and `discovery_classics_genres.enrich_classic_genres()` (bounded genre metadata). The provider/cache lookups, inventory snapshot, stage order, jitter, and response envelope are adapter/orchestration responsibilities.
- Direct-import regression suites already exist for the extracted candidate and rating helpers; the genre helper was likewise introduced with direct-import coverage in PR #231. I found no remaining self-contained policy stage in the builder that would improve ownership if moved. Extracting the response dictionary alone would be a mechanical relocation; extracting the whole pipeline would create a broad callback interface and obscure orchestration.
- **Decision:** no application-code PR for classics. Removed this stale candidate from the active roadmap and made the application-assembly / AST-coupled test audit the next action. Acquisition coordination remains conditional and safety-critical.
- This session's work is documentation-only. No application tests or local test commands were run. Required workflow status must be verified on the final documentation PR head before merge. No publication, deployment, or production runtime verification is claimed.

---

## 2026-10-16 — Documentation consolidation

- Re-established canonical document roles: `docs/MODULARIZATION_ROADMAP.md` is the short active plan; `docs/PROJECT_STATUS.md` is the current snapshot; `docs/TEST_PLAN.md` is the verification baseline; `docs/ARCHITECTURE.md` describes current responsibilities; this file remains the primary detailed project history.
- Older extraction/verification sections found in the former diary-style roadmap, test plan, and architecture document that were not represented by PR number here were preserved in `docs/archive/MODULARIZATION_HISTORY.md`. Archived records are historical evidence, not current status; verify current state against GitHub `main` and exact CI runs.
- Updated the workflow to use targeted historical search instead of reading the full log every session.
- The read-only boundary audit found the next candidate should be a trace of `_build_classics_list()` and its tests, followed by an application-assembly/AST-test dependency audit. Acquisition coordinator extraction remains conditional on a narrow safe seam; slskd work is not justified by file size alone. PR #228's audit findings are incorporated here and in the roadmap; the PR can be closed as superseded once this consolidation is reviewed.
- This was a documentation-only change; no application tests or CI have been run yet. No publication, deployment, or runtime verification is claimed.

---

## 2026-10-16 — PR #240 merged: lazy auth-secret provider

PR #240 squash-merged at `78547fd47c1b155255c1da6ef57120b76513a0fc` from exact final tested head `e3542c6a8fa3b2fc3ddf07a0268563ae5946064a`. Extracted lazy, lock-protected signing-secret loading to `app/security/auth_secret.py`, with injected data-directory lookup and existing secret loader; retained `app.main._AUTH_SECRET` for integration-test compatibility. Direct-import tests cover laziness, caching, retry after exceptions/None, and concurrent first use. Initial CI caught the removed compatibility attribute; it was restored and the corrected head passed all four workflows: syntax/acquisition safety `38941505550`, Docker/full suite/build `38941505440`, runtime smoke `38941505508`, and validation-only multi-architecture `38941505516`. Assistant-side local tests were not run. Publishing remains paused; no deployment or production runtime verification claimed.

## 2026-10-16 — PR #236 merged: New Releases lookup construction

- Squash merge: `aaa748f2dfdc307d79faf5397a51dbfbcd75ec6c`; exact tested head: `990e3ddfe08b6b1590860e8fd07d0ac13882be3e`.
- Extracted `discovery_new_releases.build_new_release_lookup()` and added direct-import tests for date-bounded query shape, quote/backslash escaping, and cache-key stability.
- All four required exact-head workflows passed: syntax/acquisition safety `38938238608`, Docker/full suite/build `38938238694`, runtime smoke `38938238678`, validation-only multi-architecture `38938238904` (publishing paused).
- No assistant-side local tests, image publication, deployment, or production runtime verification claimed.

## 2026-10-16 — PR #235 merged: New Releases response projection

- Squash merge commit: `0d77f7d99a89660ea1d9a38635e93343538e93b8`; exact tested PR head: `f3e7ec7c14deac8136b5066011623e00dffca134`.
- Extracted sorting, the 200-item visible cap, the 20-error cap, and response shaping into `discovery_new_releases.build_new_release_response()`. Provider/cache/rate-limit access, date-window policy, candidate selection, and error collection remain in the server adapter.
- Added direct-import tests for newest-first ordering/tie behavior, response metadata, error/item caps, and non-mutation. Docker packaging already included `discovery_new_releases.py`, so no packaging change was needed.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety run `38937239432`; Docker packaging/full unit suite/build run `38937239481`; container runtime smoke run `38937239444`; validation-only multi-architecture image validation run `38937239482` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.

## 2026-10-16 — PR #234 merged: New Releases global candidate merge

- Squash merge commit `c44ea572354b4714e5e2577f5eb21b091be97cc8`; exact tested PR head `56bb5b6835d03860124f2dbdff4dbb13a813d5c8`.
- `discovery_new_releases.merge_release_candidates()` now owns cross-artist identity merge policy; newest release wins and the existing candidate remains on date ties. Added direct-import tests for precedence, tie behavior, non-mutation, empty inputs, and missing dates.
- All four required workflows passed on the exact final PR head: syntax 38935716487, Docker/full suite/build 38935717026, runtime smoke 38935716420, validation-only multi-architecture 38935716622. Local test commands were not run by the assistant. No image publication, deployment, or production runtime verification claimed.

## 2026-10-16 — PR #233 merged; PR #234 global merge extraction started

- PR #233 merged at `08e20f502e10f829bf9ae7920106b7e8427668eb` from tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`; all four required workflows passed on that exact head (syntax 38934044235, Docker/full suite/build 38934044270, runtime smoke 38934044253, validation-only multi-architecture 38934044237). No local test execution or production verification claimed.
- PR #234 (`extract/new-releases-global-merge`) isolates pure cross-artist identity merging. It preserves the newest candidate per identity and stable existing-winner tie behavior; tests cover newer wins, ties, non-mutation, empty inputs, and missing dates. Exact-head CI pending.

## 2026-10-16 — PR #232 merged: classics candidate collection

- Squash merge commit: `451944c9056eeb50ec7d8b1744bbf435d653b70b`. `discovery_classics_candidates.collect_classic_candidates()` owns candidate collection, normalized duplicate resolution, ownership/eligibility filtering, metadata, and fifth-artist pacing; the server retains library/provider access, scoring, enrichment, diversity, and response assembly.
- The latest four workflow runs inspected for the PR reported success (syntax/acquisition safety, Docker packaging/full suite/build, container smoke, and non-publishing multi-architecture validation). The connector evidence did not independently expose each run's head SHA, so this closeout does not label them exact-head verified. Assistant-side local tests were not run. Publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — New Releases library qualification extraction in progress

The next candidate moves normalized ownership identity construction and full-album artist qualification/sorting into `discovery_new_releases.prepare_new_release_library_scope()`. It preserves the six-track threshold, Various Artists exclusion, stable descending album-count order, all-owned-album identity set, and untruncated qualified count. The adapter retains the 120-artist request cap, date-window policy, MusicBrainz requests/cache/rate limit, error reporting, and global merge. Direct-import contract tests are added. PR #233 is open on tested head `4d7fa4b09bbfa59a8c7a4e4a48aec5b76585a7e1`. All four required workflows passed on that head: Python syntax/acquisition safety run 38934044235, Docker packaging/full unit suite/build run 38934044270, container runtime smoke run 38934044253, and validation-only multi-architecture validation run 38934044237. Assistant-side local tests were not run. Merge remains pending; publishing/deployment/runtime verification remain paused/unclaimed.

## 2026-10-16 — PR #231 merged: classics genre enrichment

- Branch: `extract/classics-genre-enrichment`; exact tested head `0856f2a9a91e8b3aff88f933d845b182007997d4`; squash merge `b23d76712a04dcbfc461ceb7245a0676738fca7a`.
- Extracted bounded genre annotation to `discovery_classics_genres.enrich_classic_genres()`; injected Last.fm lookup and family classification remain adapter responsibilities. Added direct-import tests for the limit, order, normalized lookup deduplication, fallback metadata, and invalid limits; added Docker packaging.
- All four required exact-head workflows passed: Python syntax run 1208, Docker packaging/full unit suite/build run 1116, container runtime smoke run 925, and validation-only multi-architecture validation run 969 (publishing paused). Assistant-side local tests were not run.
- No publication, deployment, or production runtime verification. Next: resume the remaining acquisition-coordination boundary audit; do not start broader extractions before reviewing safety and independent testability.

## 2026-10-16 — PR #230 merged: watcher progress accounting

- Branch: `refactor/extract-watcher-progress-accounting`; exact tested head `47fb2a5bb18d4101dde910dd30e5bad2ed13e2e7`; squash merge `57f9776b1b517c7c86119b2a11d7f919b8cab631`.
- Extracted the deterministic byte-counter/progress-timer update into `acquisition_progress_accounting.observe_progress()`; the watcher retains slskd polling, transfer interpretation, stall policy/countdown, source switching, filesystem verification, and import decisions. Added direct-import regression tests and Docker packaging.
- All four required exact-head workflows passed: Python syntax run 1202; Docker packaging/full unit suite/build run 1110; container runtime smoke run 919; validation-only multi-architecture image validation run 963 (`push: false`). Assistant-side local tests were not run.
- No image publication, deployment, or production runtime verification is claimed. Publishing remains paused.

## 2026-10-16 — PR #229 merged: classics critical-rating extraction

- Branch: `refactor/extract-classics-rating-enrichment`; tested head `28c364dca41971ea90667c175663de17b41ca7ab`; squash merge `925eb16cba7d2387cd0a17c7690e36d35f17e8f1`.
- Extracted listener-ranked shortlist and critical-rating enrichment to `discovery_classics_ratings.py`; added five direct-import regression tests, Docker packaging, and documentation updates.
- All four required exact-head workflows passed: Python syntax/acquisition safety run 1194; Docker packaging/full suite/build run 1102; runtime smoke run 911; validation-only multi-architecture run 955. Local test execution was not performed.
- Publishing/deployment remain paused; no runtime deployment is claimed.

## 2026-10-16 — Classics-list rating enrichment extraction implementation notes

- Branch: `refactor/extract-classics-rating-enrichment`, based on GitHub main at `80935c5bc97cc56bc6fd54efc7416c3a2ed6978e`.
- Extracted the critical-rating shortlist/enrichment stage into `discovery_classics_ratings.py`; kept provider/cache access in `_musicbrainz_critical_rating` and retained the surrounding `_build_classics_list()` pipeline.
- Added direct-import regression tests and Docker packaging. Docs updated in status, roadmap, and test plan.
- Final verification and merge are recorded in the subsequent PR #229 closeout entry above. Local test execution was not performed; publishing/deployment remain paused.

## 2026-10-16 — Session closeout: PRs #225 and #226 merged

- **PR #225:** https://github.com/abucalip/navi-librarian/pull/225 — cached discovery-list projection extracted to `discovery_list_payload.build_cached_discovery_list_response()`. Exact tested head `573fe05d31dae422c25188688cd2fa949339e487`; squash merge `4d968b381d1f541b81a4a46d1753b5145347e33d`. Four required workflows passed: syntax/acquisition safety 1187, Docker/full suite (477 tests)/build 1095, runtime smoke 904, validation-only multi-architecture 948.
- **PR #226:** https://github.com/abucalip/navi-librarian/pull/226 — background listening-profile refresh extracted to `listening_profile.refresh_and_persist_background_profile()`. Exact tested head `740979f1b4da4f5c13632ab3598c13bc09ed413e`; squash merge `f5a95338e978a14d01fb6a1c3741e2e6c8bea11c`. Four required workflows passed: syntax/acquisition safety 1189, Docker/full suite (481 tests)/build 1097, runtime smoke 906, validation-only multi-architecture 950.
- Both changes preserve the server adapter/compatibility boundary and include direct-import regression coverage. PR #225's initial test-fixture assertion was corrected before final CI. No independent local tests, publication, deployment, or production runtime verification are claimed.

## 2026-10-16 — PR #224 merged: personal recommendation payload shaping

- PR #224 squash-merged at `f795239589e6dd78f0f5e6d98cf2eadc897d6f49` from exact tested head `6d2e0ccc8d24cd11b727255f171fd405384a8729`.
- Pure personal-recommendation payload projection moved to `discovery_recommendation_payload.py`; the server retains recent-listen count lookup and selection-specific ownership annotations.
- Exact-head CI passed syntax/acquisition safety run 1177, Docker packaging/full suite (473 tests)/build run 1085, runtime smoke run 894, and validation-only multi-architecture build run 938. Assistant-side local tests were not run.
- No image publication, deployment, or production runtime verification. Publishing remains paused.

## 2026-10-16 — Personal recommendation payload projection extraction (in progress)

- Branch `refactor/personal-recommendation-payload`, based on current GitHub main after PR #223. Extracted the base personal-recommendation payload mapping to `discovery_recommendation_payload.py`; selection-specific `ownership_check` / `ownership_note` annotations remain in the adapter.
- Added direct-import tests for legacy fields, defaults, score rounding, category reason text, ListenBrainz-vs-Last.fm score handling, and the three-track limit. Docker packaging includes the new module.
- Tests and exact-head CI have not yet been verified. Next: review the complete diff, open a focused PR, and run all four required workflows on its exact final head.

## 2026-10-16 — PR #223 merged: personal recommendation allocation

- PR #223 squash-merged as `1ccb11485bf1efce3ff201fb7337407c3e668c47` from exact final tested head `b604940e4b7a20160d4f3710b009c6ca718c57c5`.
- Moved shortlist allocation loops into the pure `discovery_personal_allocator.allocate_personal_recommendations()`; the immutable contract keeps candidate identity, ownership classification, quotas, style targets, family cap, and check budget explicit. Server-side payload/diagnostic shaping and Navidrome ownership lookup remain in the adapter.
- Exact-head CI passed all four required workflows: syntax/acquisition safety run 1171; Docker packaging/full suite (468 tests)/build run 1079; runtime smoke run 888; validation-only multi-architecture build run 932. No assistant-side local tests were run.
- The first CI attempt exposed two incorrect test fixture expectations; corrected them before final verification. Also reviewed and preserved the distinct selected/review payload shapes. No image publication, deployment, or production runtime verification.
- Next: refresh GitHub main/open PRs and identify one small, independently testable seam. Publishing remains paused.


## 2026-10-16 — Personal recommendation allocator boundary investigation (pre-integration history)

- PR #221 established the immutable contract, deliberately leaving allocation loops untouched. A follow-up investigation identified the stable tie-order distinction between regional-style reservations and final fallback; `source_order` was added to preserve the legacy behavior.
- This exploratory stage was superseded by PR #223, which integrated the pure allocator through the server adapter, added Docker packaging and policy tests, and passed all four required workflows on exact final head `b604940e4b7a20160d4f3710b009c6ca718c57c5`. See the PR #223 entry above for verification details.
- Publishing/deployment remain paused.



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

## 2026-10-16 — Independent extraction session: PRs #205 and #207

- **PR #205:** https://github.com/abucalip/navi-librarian/pull/205 — extracted per-artist MusicBrainz release-group candidate filtering to `discovery_new_releases.select_artist_release_candidates()`. Exact tested head `079d355e972ea39d792c1dfa6fca6eab902800e3`; all four workflows passed (syntax 1111, Docker/full suite/build 1018, runtime smoke 827, validation-only multi-architecture 871); squash merge `32b39be400ec046e8310a87260346b1959141609`.
- **PR #207:** https://github.com/abucalip/navi-librarian/pull/207 — extracted Artist Deep Dives score/rank/diversity policy to `discovery_recommendations.rank_and_diversify_deep_dive_candidates()`. Exact tested head `20e565582579f4097eed3803748c87bb3d932a98`; all four workflows passed (syntax 1114, Docker/full suite/build 1021, runtime smoke 830, validation-only multi-architecture 874); squash merge `a5b0d865060c3d069a865be7a1cb43c1a072ae91`.
- Both are backend-only and preserve provider access, cache/rate-limit behavior, legacy server entry points, and MCP response contracts. Direct-import tests added. Assistant-side local test commands were not run; no publication, deployment, live provider integration, or production runtime verification is claimed. PR #206 was superseded and closed before PR #207 was opened from updated main. Acquisition-dismissal HTTP 409 remains deferred; publishing remains paused.


## 2026-10-16 — Independent extraction session: PRs #202 and #203

- **PR #202:** https://github.com/abucalip/navi-librarian/pull/202 — extracted pure library-overview payload shaping to `navidrome_client.library_overview_payload()`; exact tested head `6903f40578f40fec08f1efde92d6577fcaeeced0`, squash merge `7a95364a31f360bb20dd8d2919a9bfea93ec893c`. All four required exact-head workflows passed: syntax 1104, Docker packaging/full unit suite/build 1011, runtime smoke 820, validation-only multi-architecture 864.
- **PR #203:** https://github.com/abucalip/navi-librarian/pull/203 — extracted pure source-preview redaction to `server_source_redaction.redact_assignment()`; exact tested head `14019b8beeca9b71fbb8167117dafea3f60c74ea`, squash merge `89e639394122aebe29bfb8602a1135722ea28bbe`. All four required exact-head workflows passed: syntax 1106, Docker packaging/full unit suite/build 1013, runtime smoke 822, validation-only multi-architecture 866.
- Assistant-side local tests were not run; full unit suites ran in CI. No publication, deployment, or production runtime verification. Acquisition-dismissal HTTP 409 remains deferred; publishing remains paused.


## 2026-10-16 — Navidrome response-shaping extractions (PRs #196 and #198)

- **PR #196:** https://github.com/abucalip/navi-librarian/pull/196 — branch refactor/extract-navidrome-search-shaping; exact tested head 4b501c64c82a69af1805a7f6195b4fc15ef0c836; squash merge 277499ec949353f5f24542a8033a481283814782.
- Extracted pure search-result payload shaping into navidrome_client.search_result_payload(). Kept search validation, API request, JSON formatting, and legacy tool interface in search_music(). Added direct-import tests for per-category output, field filtering, and all-category ordering.
- Exact-head workflows all passed: Python syntax run 1088; Docker packaging/full unit suite/build run 995; container runtime smoke run 804; validation-only multi-architecture build run 848.

- **PR #198:** https://github.com/abucalip/navi-librarian/pull/198 — branch refactor/extract-navidrome-album-details-main; exact tested head a718780edcb85eb8f4453e44a2d5a4925a512314; squash merge 92cdd6309244e78e78bd0f6f8d2e38ea929e434b.
- Extracted pure album/track payload shaping into navidrome_client.album_details_payload(). Kept API access, JSON serialization, and legacy tool interface in get_album_details(). Added direct-import tests for scalar track records and missing fields.
- Exact-head workflows all passed: Python syntax run 1090; Docker packaging/full unit suite/build run 997; container runtime smoke run 806; validation-only multi-architecture build run 850.

- Both changes are backend-only, require no manual UI checklist, and preserve the existing MCP-facing response shapes. The full unit suite was run in the packaging workflows; assistant-side local tests were not run. No publication, deployment, or production runtime verification is claimed. PR #197 was closed as superseded before its clean-main replacement PR #198.
- Acquisition-dismissal HTTP 409 remains deferred per explicit user direction. Keep publishing paused.
- Next action: refresh GitHub main/open PRs/exact-head CI and select the next independent low-coupling extraction.
## 2026-10-16 — PR #192 merged: settings tabs and skip-link accessibility

- PR: https://github.com/abucalip/navi-librarian/pull/192
- Supersedes conflicted PR #188, which was closed without merging. Branch: `a11y/refresh-188-from-main`; base main `470b232977b45ee1cf1bf1b399c2c43843062c1f`; exact tested head `75c13b0099285747c9da75c5c3879e6594e5fe36`; squash merge/current main `4fc72001807e0afc40ebc99bf1be9a502f87e0f8`.
- Reapplied four focused changes on current-main files: skip link and main target, accessible names for four settings tab panels, keyboard-operable roving tabindex tabs, and UI backlog evidence. Existing current-main content was retained.
- All four exact-head workflows passed: Python syntax run 1069; Docker packaging/full unit suite/build run 976; container runtime smoke run 785; validation-only Docker image validation run 829.
- User-published manual browser report comment in PR #192 tested the exact head and recorded all checklist items passing with zero failures. No assistant-side local test run, publication, deployment, or production runtime verification is claimed.
- PR #188 closed as superseded after #192 merged. Acquisition dismissal HTTP 409 remains deferred by explicit user direction.
- Next: refresh GitHub main, open PRs, and CI before selecting further work; do not claim deployment or production runtime verification.

## 2026-10-16 — PR #190 merged: artist-biography resolution

- PR: https://github.com/abucalip/navi-librarian/pull/190
- Branch: `refactor/extract-artist-bio-resolution`; exact tested head `6c04d8a67944568a3e2b280deafb4eb2c66c2391`; squash merge `b829fa953d979563a8ace6e5529eace8cb80ac43`.
- Extracted pure biography selection into `app/services/artist_bio.py`, preserving provider I/O, concurrent retrieval, cache ownership, validation, and response schema in `app/api/metadata.py`.
- Direct-import tests cover matching QIDs, mismatched page identity, disambiguation, ranking/filtering, empty payloads, and truncation. All four required workflows passed: syntax 1059, Docker/full suite/build 966, runtime smoke 775, validation-only multi-architecture 819.
- No assistant-side local test execution, publication, deployment, or production runtime verification is claimed.
- PR #190 code merge SHA: `b829fa953d979563a8ace6e5529eace8cb80ac43`; documentation closeout commits followed on main.
- Next: refresh GitHub main/open PRs/CI before selecting another independent extraction.

## 2026-10-16 — Artist-biography resolution extraction opened

- Branch `refactor/extract-artist-bio-resolution`, based on refreshed main `7bfcbebfa66e7d00d20f78e25d8b998b7a617bd0` after PR #189.
- Added `app/services/artist_bio.py` with pure artist-biography resolution from already-fetched Wikidata entities and Wikipedia page payloads. `app/api/metadata.py` still owns provider requests, parallel retrieval, caching, input validation, and the response contract.
- Added `tests/test_artist_bio_service.py`; retained `tests/test_metadata_routes.py` for HTTP routes and provider integration.
- Verification pending on the exact PR head; no assistant-side test execution, merge, publication, deployment, or production runtime verification is claimed.
- Next: inspect the complete diff and all four required exact-head workflows before merge.

## 2026-10-16 — PR #189 merged: dashboard-pick service

- PR: https://github.com/abucalip/navi-librarian/pull/189
- Branch: `refactor/extract-dashboard-pick-service`; exact tested head `d28aaa33f7096ba764232d6bd435cc68d5d85f98`; squash merge/main commit `f5f355f8bdc0599bb240933e248177c7b0517ff5`.
- `app/services/dashboard.py` now owns three-lane dashboard candidate assembly, album eligibility, case-insensitive artist/album deduplication, category balancing, and random fill. The API route retains count validation, the lazy librarian dependency, and the response contract.
- Direct-import service tests added; route tests retained. Exact-head workflows passed: syntax/acquisition safety 1052, Docker packaging/full unit suite/build 959, container runtime smoke 768, and non-publishing multi-architecture validation 812.
- No assistant-side local test run, image publication, deployment, or production runtime verification is claimed. Acquisition-dismissal HTTP 409 remains deferred.
- Process note: a test-file creation omitted the branch argument and briefly committed the new test on main; the file was immediately removed by `039b5ed14834aeb63627f141c1bafa1d96c8589b`, verified absent on main, and then created on the PR branch. The intended file is included in the merged PR.
- Next: refresh GitHub main/open PRs/CI before selecting another independent extraction.

## 2026-10-16 — Dashboard-pick assembly extraction opened

- Branch `refactor/extract-dashboard-pick-service`, based on refreshed GitHub main `2b9eb6a88c752aa1d2e65687641d05629aa89427`.
- `app/services/dashboard.py` now owns dashboard candidate aggregation, case-insensitive artist/album deduplication, album eligibility filtering, balanced category picks, and random fill. `app/api/dashboard.py` remains the HTTP adapter and preserves the endpoint path, count validation, service calls, and response schema.
- Added `tests/test_dashboard_service.py` for direct-import behavior. Existing `tests/test_dashboard_routes.py` remains in place to cover route inventory, injected service calls, sanitized health failures, category balance, filtering/deduplication, and invalid counts.
- Verification is pending until the final PR head. No assistant-side test execution, merge, image publication, deployment, or production runtime verification is claimed.
- Acquisition-dismissal HTTP 409 remains deferred and unchanged.
- Next: open PR, inspect full diff, and wait for all four required workflows on the exact final PR head.
## 2026-10-16 — PRs #186 and #187 merged

- **PR #186 — UI empty-state copy/state kinds:** published local manual report for tested head `0c12a43cd40211d522868dab7caa70c8a5fbf6e6`; all manual checklist items passed, zero failures. All four GitHub Actions workflows succeeded on that exact head (syntax 1041, Docker packaging 948, runtime smoke 757, validation-only image 801). Squash merge `d42618b63f141049d5b0e6558e81174ef5c1418f`.
- **PR #187 — slskd connection probe:** extracted the connection check to `slskd_client.py`, preserved the legacy adapter, added direct-import regressions and Docker packaging. Exact final PR head `920590871883aa8c75c29a1b16131bd88519072d` passed all four workflows (syntax 1041, Docker packaging/full suite/build 948, runtime smoke 757, validation-only image 801). Squash merge `b7ae6458adda3650f178fc64457914beb66ece9c`.
- Assistant-side local tests were not run independently. No image publication, deployment, or production runtime verification is claimed. Acquisition dismissal HTTP 409 remains deferred and unchanged.
- Main tip at closeout: `b7ae6458adda3650f178fc64457914beb66ece9c`.
- Next: refresh GitHub main/open PRs/CI and choose the next low-coupling roadmap extractions; keep publishing paused.

## 2026-10-16 — slskd connectivity probe extraction opened (PR #187)

- Branch: `refactor/extract-slskd-connection-check`; base main `d66257586b69c4cb03641f5ce67050c3f4defd76`.
- Current code head before this log update: `73be3bf8fa1211edff3689bfd1a9c820bf6770d6`.
- Added `slskd_client.py` with an injected config reader/HTTP getter; preserved the legacy MCP/web adapter and response JSON; added `tests/test_slskd_client.py`; updated Docker packaging.
- Exact-head local tests have not been run. CI results are pending/unverified; no publishing, deployment, or production runtime verification is claimed.
- PR: https://github.com/abucalip/navi-librarian/pull/187.
- Next: verify all four exact-head CI workflows and review before merge. Keep the dismissal HTTP 409 deferred and preserve all cleanup safety checks.

## 2026-10-16 — Open-PR refresh after extraction session

- PR #184, `ui: make Artist Deep Dive artist-led and drop its dead controls`, appeared during this session. Its branch `ui/artist-deep-dive` is based on `9f05bed`; comparison against the refreshed main showed it 7 commits behind and one commit ahead of its merge base.
- The PR description explicitly says the required human manual browser checklist is NOT RUN. Treat its automated/browser-agent measurements as separate evidence, not a substitute for the documented human checklist. Do not merge until the branch is refreshed, required exact-head CI is verified, and the human checklist is recorded on that exact head.
- This backend session did not modify PR #184. PR #23 remains the modularization roadmap; PRs #44/#45 remain closed per user direction.

## 2026-10-16 — slskd progress summary and speed estimator extracted (PRs #182–#183)

- **PR #182 — progress summary:** extracted matched-record aggregation into `slskd_transfers.summarize_transfer_progress()`; preserved the legacy HTTP and matching adapters, speed snapshot lock, and response schema. Tested head `045131f58365dd0e6538c1712f37f56f639c65ad`; all four required workflows passed (syntax 1016, Docker/full suite/build 923, runtime smoke 732, non-publishing multi-architecture validation 776). Squash merge `d706b084bc85d78f48ddd9b7d958ce04613fdc3e`.
- **PR #183 — speed estimator:** extracted pure delta-based bytes/second calculation into `slskd_transfers.estimate_transfer_speed()`; snapshot state/identity/locking remain in `navidrome_server.py`. Final tested head `fac29c108a1d630f2ffbc6af8dad8a5e88c5368f`; all four required workflows passed (syntax 1019, Docker/full suite/build 926 with 342 tests, runtime smoke 735, non-publishing multi-architecture validation 779). Initial test assertion was corrected after CI showed the fixture elapsed 1 second; exact final head passed. Squash merge `e4e9bd1fad9536f00f3908d753b66147d30ca03f`.
- Assistant-side local test commands were not run. No image publication, deployment, or production runtime verification is claimed.
- Acquisition dismissal HTTP 409 remains deferred per explicit user direction. No cleanup behavior was changed and safety checks were not weakened.
- Next action: refresh main/open PRs/CI and choose the next focused, low-coupling extraction.

## 2026-10-16 — Two slskd transfer-boundary extractions merged

- **PR #180 — queue request extraction:** moved the slskd queue POST into `slskd_transfers.queue_download_files()`; retained the dismissal guard and orchestration in `acquisition_orchestration` and `navidrome_server.py`. Exact final tested head `ce0e635cc77c687958d6ad1c1a852e55476c14b2`; syntax run 1008, Docker packaging/full unit suite/build run 915, container runtime smoke run 724, and validation-only Docker image run 768 all succeeded. Squash merge `7c670f2eac838934bc9afa7f40f892ff595ca4ca`.
- **PR #181 — live progress transfer matching:** moved normalized expected/tracked basename matching and duplicate state precedence into `slskd_transfers.match_expected_transfer_records()`; byte/speed calculation and public progress shape remain unchanged. Exact final tested head `cf78b4188a549d6e1b2b98c76a63a6bc0826d129`; syntax run 1010, Docker packaging/full unit suite/build run 917, container runtime smoke run 726, and validation-only Docker image run 770 all succeeded. Squash merge `3df14d3c59bb7e5a689d797028e45468c6a87ee7`.
- Both PRs added direct-import regression tests and preserved compatibility paths. Assistant-side local test commands were not run; the full unit suite ran in CI on each exact final head. Publishing remained paused; no deployment or production runtime verification is claimed.
- Acquisition dismissal HTTP 409 remains deferred per user direction. No change was made to filesystem cleanup or dismissal behavior.
- Next action: refresh main/open PRs/CI and choose the next small seam from the modularization roadmap.

## 2026-10-16 — Last.fm similar-artist parsing extraction merged

- PR #178 merged as `f18574b74a564031c5268cf04c956475d64dc30c`; tested PR head `a97be052d3a1e74843feaacd6403d10ce5aad6af`.
- Moved cached Last.fm similar-artist parsing into `LastFmClient.similar_artists()` and retained the legacy adapter. Added regression tests for response shape/normalization, malformed values, request contract, cache TTL/hits/misses, and adapter delegation.
- Exact-head CI successes: Python syntax check run 1003, Docker packaging validation run 910, container runtime smoke run 719, and Docker image validation with publishing paused run 763. Local full unit suite not independently run; publishing/deployment not performed.
- Next action: refresh GitHub state before selecting another extraction. Acquisition-dismissal HTTP 409 remains deferred by user direction.

## 2026-10-16 — Last.fm similar-artist parsing extraction (in progress)

- Branch: `refactor/extract-lastfm-similar-artists-current`, based on main `86b2ac60416ed725755fc6c57200e1c3123b7606`.
- Extracted cached `artist.getSimilar` response parsing into `LastFmClient.similar_artists()`; `_lastfm_similar_artists()` remains a compatibility adapter. Existing Docker packaging already copies `lastfm_client.py`.
- Added direct-import regressions for scalar/list responses, blank and malformed records, invalid similarity values, request parameters, 60-day TTL/cache behavior, missing/provider-error responses, and adapter delegation.
- PR/CI/merge pending; do not claim tests passed until actually observed. Publishing/deployment remain paused. HTTP 409 investigation stays deferred per user direction.

## 2026-10-16 — Last.fm top albums extraction (PR #175)

- Branch `refactor/extract-lastfm-top-albums`, based on main `4dd8b926a7a6cf76e248420860d7c29c892da3c0`.
- Moved cached `artist.getTopAlbums` response normalization into `LastFmClient.artist_top_albums()` while retaining discovery-specific filtering in `_lastfm_top_albums()`.
- Added direct-import tests and updated architecture/roadmap/status documentation. PR #175 open; exact-head CI pending. No local test, publishing, deployment, or production runtime verification claimed.
- Acquisition dismissal HTTP 409 remains deferred by explicit direction.

---

## 2026-10-16 — Three-extraction session closeout (PRs #170–#172)

- Starting GitHub `main`: `098c5d9d8536070c1115ec2a7c25b99490efb312`. Final code `main`: `d5153a3fe0625bc52b5896e87846b55cabe58e81`.
- **PR #170 — MusicBrainz tag audit.** Branch `refactor/extract-music-tag-audit`; tested head `3ce122d2e950aaf9b8ddd56f8dfecc927255ba07`; squash merge `dbbdda35792fd569cfdeec2c4c7b42fc106f84e3`. Extracted a bounded read-only scan into `music_tag_audit.py`, retained the legacy MCP adapter/output contract, added direct-import regression tests, and updated Docker packaging. Exact-head workflows all passed: syntax `38827001217`; Docker/full suite/build `38827001215`; runtime smoke `38827001195`; validation-only multi-architecture `38827001227`.
- **PR #171 — Recommendation style rules.** Branch `refactor/extract-recommendation-style-rules`; final tested head `24e2e27f7af3bd3be6b96d725bc72b577f8f78d9`; squash merge `6d00562405320affcb1a04b4359397b332cd5bf5`. Extracted four pure classification helpers into the existing `discovery_recommendations.py`; no Docker file-list change was needed because that module was already packaged. The first CI run caught a mistaken test fixture (the classifier recognizes `Afrobeats`, not `Afrobeat`); the fixture was corrected and final exact-head workflows passed: syntax `38827709662`; Docker/full suite/build `38827709650` (319 tests); runtime smoke `38827709649`; validation-only multi-architecture `38827709610`.
- **PR #172 — Last.fm album popularity.** Branch `refactor/extract-lastfm-album-popularity`; final tested head `d2808d44825e949ff71ed8471d25cee6570b54f1`; squash merge `d5153a3fe0625bc52b5896e87846b55cabe58e81`. Extracted `album.getInfo` transport/response handling into `LastFmClient.album_popularity()`, preserving the old cache key, TTL, timeout, tags/stat normalization, diagnostic strings, and 404 behavior. The first CI run caught a test fixture that did not record the injected HTTP call; the test helper was corrected and final exact-head workflows passed: syntax `38827973048`; Docker/full suite/build `38827972941` (324 tests); runtime smoke `38827972940`; validation-only multi-architecture `38827972938`.
- All three PRs were merged only after the final exact PR-head workflows passed and the changed-file diffs were reviewed. Assistant-side local test execution was not performed. No manual UI tests were required. Publishing remained paused; no image publication, deployment, or production runtime verification is claimed.
- Current open PR inventory after the code merges: only PR #23, the modularization roadmap. PRs #44 and #45 remain closed. The acquisition-dismissal HTTP 409 remains unresolved and deferred until modularization is complete at the user's direction; do not claim a fix or relax filesystem safeguards.
- Next action: review current `main` and the roadmap, then select the next small independent seam. Keep publishing paused.

---

## 2026-10-16 — Two-extraction session closeout

- Starting main SHA `8dbb1e3125d2422e69bb30fa7ecb5bebdf652eed`; final main SHA `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`.
- **PR #167 — listening profile aggregation:** tested head `ca8f9e4b7decb3404c78f1ee8b8d3078815fd71f`; merge `6b656dc7218280aa0d37e738a881061ceefde55e`. All four required workflows passed: syntax `38825137244`, full suite/build `38825137296`, runtime smoke `38825137346`, validation-only multi-architecture `38825137280`.
- **PR #168 — discovery library snapshot:** tested head `fc69943301c5065a54a0128c8b82ae214cd69dd1`; merge `89f7ec7eb291d4dd4f62784bae6f6d30af06ccae`. All four required workflows passed: syntax `38825386951`, full suite/build `38825387005`, runtime smoke `38825386785`, validation-only multi-architecture `38825386797`.
- Both extractions retained legacy adapters, added direct-import regressions, and updated Docker packaging. The full unit suite passed in CI for each exact final head. Assistant-side local test commands were not run.
- Only PR #23 remains open as the modularization roadmap. PRs #44 and #45 are closed as requested; dismissal HTTP 409 investigation is deferred until it recurs. Publishing and deployment remain paused/unverified.

## 2026-10-16 — Multi-extraction session: PRs #163, #164, and #165 merged

Three independent integration-client extractions were completed sequentially, refreshing GitHub main after each merge.

- **PR #163 — ListenBrainz client.** Branch `refactor/extract-listenbrainz-client`; tested head `4c494a2679884579df5d6bc204287637e45e2ccd`; merge `7be68c74b8a97ed4d9c50e6a7e22e296b25e79e2`. Added bounded paging with injected clock/client/sleep, compatibility adapter tests, and Docker packaging. All required exact-head workflows passed: compile `38822823853`, unit suite/build `38822823922`, smoke `38822823751`, multi-architecture validation (publishing paused) `38822823989`.
- **PR #164 — Last.fm client.** Branch `refactor/extract-lastfm-client`; tested head `957f3a56afe15e4dd665b041f1fbf7803921d3b6`; merge `9f174c6086c0d2b9749e53e38cbe8e1eb337e22f`. Extracted cached/rate-limited HTTP calls with injected settings/cache/transport/time dependencies. All required exact-head workflows passed: compile `38823469617`, unit suite/build `38823470035`, smoke `38823469896`, multi-architecture validation `38823469762`.
- **PR #165 — MusicBrainz rating client.** Branch `refactor/extract-musicbrainz-rating-client`; tested head `4888bd08fdf05007cc74ad7005a196fd678305b5`; merge `a0cd3d8ff5dcdf6acb7d678c9fc8f1aa0d537629`. Extracted cached release-group rating/year lookup, preserving cache TTL/key, request pacing, 404 caching, and result shape. All required exact-head workflows passed: compile `38823643925`, unit suite/build `38823643703`, smoke `38823643931`, multi-architecture validation `38823643848`.
- The full unit suite and Docker build passed on all three final PR heads. Assistant-side local test execution was not performed. No manual UI testing was applicable. All multi-architecture validation workflows were non-publishing.
- These merges do not indicate image publication, deployment, or production runtime verification; those states remain paused/unverified.

Next: prioritize the outstanding acquisition-dismissal HTTP 409 investigation/diagnostic gate before more routine modularization.

---

## 2026-10-15 — PR #160 merged: discovery refresh orchestration extraction

- PR: https://github.com/abucalip/navi-librarian/pull/160. Exact tested head: `5aafc1a9c5835e2d9e2959a36e7419d09913403a`; squash merge commit: `dba172d5747607e65e8fadd32442b12d32054749`.
- Extracted ordered refresh-all orchestration into `discovery_refresh.refresh_all`; retained `navidrome_server._discovery_refresh_all()` as the compatibility adapter.
- Added regression coverage for callback order, personal count (20), and returned results. The existing module packaging was unchanged.
- All four required workflows passed on the exact PR head: Python syntax `38818349092`, Docker packaging/full unit suite/image build `38818349082`, container runtime smoke `38818349397`, and validation-only Docker/multi-architecture validation `38818349076`.
- MCP registrations, signatures, names, response shapes, provider calls, lock ownership, and persistence behavior remain unchanged. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.

---

## 2026-10-15 — PR #156 merged: footer placement and accessibility verification

- PR #156: https://github.com/abucalip/navi-librarian/pull/156; exact tested head `47d33cbecadf64ed4b434764883cec6ae99d30bc`; squash merge `c560c28063f26a1a72d7016c951bf265d2ddd158`.
- Manual browser report published in the PR conversation for that exact SHA. All eight manual acceptance checklist items passed, with zero failures. Browser verification measured footer placement/reading order on all eight routes, the `contentinfo` landmark, expected headings, keyboard order, responsive overflow at eight widths, and absence of console/page errors.
- Exact-head CI passed: syntax `38815023255`, Docker packaging `38815023085`, runtime smoke `38815023444`, and validation-only Docker image/multi-architecture validation `38815023661`. Publishing remains paused.
- Limitations: Chromium only; no real screen reader test. The missing skip link remains a separate UI backlog item. No image publication, deployment, or production runtime verification is claimed.
- Session closeout: implementation, manual test, CI, and merge are complete. Next: re-check main/open PRs/CI and prioritize any remaining safety or verification gap before routine modularization.

## 2026-10-15 — Backend session closeout: PRs #155 and #157 merged

- PR #155: expected track-count metadata extracted to `slskd_search.py`; tested head `19c729db8a6ed5f9461fb5d9afc16fecdccfe1d6`; merge `d732241de9edfd3c643a8fa89fb25c42b2a93c67`. All four required workflows passed on that exact head.
- PR #157: slskd transfer listing/normalization extracted to `slskd_transfers.py`; `_slskd_download_transfer_files` retained as the adapter. Tested head `504b10392061dbc44d28d66e663b88cbefb8f1a4`; merge `17922f878f0ea391b47652012a38530e9eb044fc`.
- Exact-head PR #157 CI passed: syntax/acquisition safety `38816375215`; Docker packaging/full unit suite/image build `38816375266`; runtime smoke `38816375339`; validation-only multi-architecture validation `38816375410`.
- A packaging-only Dockerfile commit landed on `main` before the module; PR #157 added the missing module and tests. The current main tree now packages the module and the exact-head Docker build passed.
- Historical next action at the time: complete PR #156's manual browser checklist. This gate was later completed and the PR merged; see the newer closeout entry above. Publishing/deployment/runtime verification remain separate and unclaimed.

## 2026-10-15 — Multi-extraction workflow closeout; PR #149 blocked on UI gate

- PR #154 merged: https://github.com/abucalip/navi-librarian/pull/154; tested head `6de27ec137e9f859424eca0928fca25500852471`; merge commit `b547ff5c647d8bacd8bf17fd6cd760dc9c41980a`. All four required workflows passed on that exact tested head. Publishing/deployment/runtime verification remain separate and were not performed.
- PR #149 was not merged. All four workflows passed on head `600c75475cfbe1d28230345835aee2316519365f`, but the PR explicitly records its required manual browser checklist as NOT RUN, and the branch is 26 commits behind current `main`. Merge remains blocked pending safe branch refresh, exact-head CI, and the required manual UI checklist.

## 2026-10-15 — Standard multi-extraction session workflow (PR #154)

- PR: https://github.com/abucalip/navi-librarian/pull/154; branch: `docs/multi-extraction-session-workflow`.
- Documented the standard multi-extraction process in `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`: target two or three small extractions without quota pressure, default one independent extraction per PR, per-extraction regression and compatibility tests, full-diff review, four exact-final-head CI gates, UI-specific manual verification, sequential merge/refresh, and evidence-based closeout.
- Verification status at this entry: documentation-only; required CI is pending on the final PR head. No application tests, publishing, deployment, or production runtime verification are claimed.

## 2026-10-15 — Music path default policy extraction merged

- PR #151: https://github.com/abucalip/navi-librarian/pull/151; tested head `07cf1ab7dab46a1409236f7134881011dc31cac2`; merge commit `6a7678bd04ef539ae5f4c118b6707524fd569280`.
- Extracted pure music path selection, retained the legacy helper and initialization semantics, added four direct-import regression tests, and updated Docker packaging.
- All four required CI workflows passed on the exact tested head: `38805068326`, `38805068317`, `38805068315`, and `38805068337` (syntax/safety regressions, Docker packaging/full unit suite/build, runtime smoke, validation-only multi-architecture build).
- Publishing remains paused. Deployment and production runtime verification are not claimed.

## 2026-10-15 — PR #150 merged: Navidrome API client extraction

- PR: https://github.com/abucalip/navi-librarian/pull/150. Tested PR head: `be9a2558bd87eb8e7e2fbf25593936aa8c671a1a`; squash merge commit: `efc2acb93e3edb570e77419daa866f4a228c85d2`.
- Extracted Subsonic-compatible authentication, HTTP request execution, and API error interpretation into `navidrome_client.py`. The legacy `navidrome_server.api_call(method, **params)` remains as a compatibility adapter; Docker packaging and direct-import regression tests were updated.
- All four required workflows passed on the exact final PR head: Python syntax `38802307579`, Docker packaging/full unit suite/build `38802307812`, container runtime smoke `38802307700`, and validation-only multi-architecture image validation `38802307683`.
- State: implemented, tested, CI passed, merged. Image publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next: continue with the smallest remaining application-assembly/domain-service boundary after reviewing current main and open PRs; preserve the legacy MCP interface until retirement is separately justified and verified.

## 2026-10-15 — Navidrome API client extraction: pre-merge record

- Branch: `refactor/extract-navidrome-api-client`.
- Extracted the Subsonic-compatible request transport and authentication from `navidrome_server.py` into `navidrome_client.py`, leaving `api_call(method, **params)` as a compatibility adapter.
- Added direct-import regressions and included the new module in Docker packaging.
- Initial exact implementation head `555da7027ae0aa9f636ba66e18b33d549cd787d6` passed all four required workflows: syntax `38802076122`, Docker packaging/full suite `38802076327`, container runtime smoke `38802076229`, and validation-only multi-architecture validation `38802076245`. The subsequent documentation-only updates require a fresh exact-final-head CI check. PR #150 is open; merge, publication, deployment, and production runtime verification remain pending.

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

## 2026-10-15 — PR #147 merged: slskd settings boolean validation

- Audited the settings API and identified that `PUT /api/settings/slskd` silently dropped `auto_acquire_for_me`; unvalidated forwarding could cause string truthiness to enable a setting unintentionally.
- Added strict JSON-boolean validation, explicit boolean forwarding, omission preservation, and regression tests for accepted and rejected values.
- PR #147 merged by squash. Tested head: `22db7e7b4414f1ff3df7440bc47aece41bf0ae1d`; merge commit: `9ce0ae37ae207f79180d98b10f71147736fe2a75`.
- All four required PR-head workflows passed: syntax, container runtime smoke, Docker packaging, and Docker image validation. Image publication remains paused. No deployment or production runtime verification claimed.



## 2026-10-15 — Data-directory resolution extraction started

- Branch: `refactor/extract-data-directory-config`.
- Added `data_directory.py` as a pure resolver for `NAVIDROME_LIBRARIAN_DATA_DIR` and the legacy source-directory fallback. `navidrome_server.py` retains `DATA_DIR` and the existing directory-creation side effect; no persistence logic or MCP-facing API was moved.
- Added `tests/test_data_directory.py` for configured path expansion, empty setting fallback, and missing setting fallback. Updated Docker packaging to include the module.
- Implementation commits: `b46adec455eb2a889df523591a1c454f7200e805`, `7eaadcc7e3c88119f16101e4b6e2217948ab8edc`, `c4eecffc46fc312c5949c56043acfb0abdcb7e49`, `a5ff011456e05ce98a81c17074732ce81f7b4a39`.
- Verification, PR, merge, publishing, deployment, and production runtime status are pending; do not infer success from the changes being committed.


## 2026-10-15 — PR #152 merged: data-directory resolution extraction

- PR #152: https://github.com/abucalip/navi-librarian/pull/152; tested head `756ef13f6946299e2eacccbf5f9a55ebaf092aae`; squash merge commit `567409bb90f240667575a3730976e4c52676bc02`.
- Extracted configured/fallback data-directory resolution to `data_directory.py`; retained the legacy `DATA_DIR` symbol and directory-creation behavior. Added three direct-import regression tests and updated Docker packaging.
- All four required exact-head workflows passed: syntax `38807325467`; Docker packaging/full suite/build `38807325564`; runtime smoke `38807325555`; validation-only multi-architecture image validation `38807325557`.
- Merged and CI-verified. Publishing remains paused; no image publication, deployment, or production runtime verification is claimed.
- Next action: review current main, open PRs, and the modularization roadmap to select the next smallest safe dependency seam.


## 2026-10-15 — PR #149 merged: recommendation-count accessibility fix

- PR #149: https://github.com/abucalip/navi-librarian/pull/149; exact tested head `c71d28e74bbdfadbedef4ec3e30fdba5181feb5a`; squash merge commit `f3ac971e6c04b9c9caa8d4d20f50d0c25302556e`.
- Brought the original PR branch up to current GitHub main without force-pushing. Made the recommendation count readable at 13px in the body font, retained stable numeric figures with `tabular-nums`, and assigned `role="status"` to its polite live region.
- Reviewed the three-file diff: `app/templates/index.html`, `static/app.css`, and `docs/UI_BACKLOG_EXECUTION.md`.
- Manual browser report published by the operator for the exact final tested head; checklist reports zero failed items. All four required GitHub Actions workflows passed on that same SHA: syntax, runtime smoke, Docker packaging/full unit suite/build, and validation-only multi-architecture image validation.
- Merged after both the exact-head CI and manual verification gates passed. Image publishing remains paused; no deployment or production runtime verification claimed.
- Next session: inspect current main, open PRs, and the modularization roadmap before choosing the next smallest safe application-assembly/domain-service seam.


## 2026-10-15 — Focused verification audit before modularization

- Audited GitHub main, recent commits, open PRs, exact-head check-runs, requirements, workflow, test plan, modularization roadmap, and UI backlog. Main at audit was `678bfa001181d53190004d1c437b1344225082cf`; all four required workflows passed on that exact SHA (syntax `38818751753`, Docker packaging/full suite/build `38818751792`, runtime smoke `38818751871`, validation-only multi-architecture `38818751791`).
- Open PRs are stale relative to main: #23 is 341 commits behind, #44 is 259 behind and has no exact-head check runs, and #45 is 256 behind despite four older successful checks on its own head. No stale PR was merged or modified during this audit.
- Kept the acquisition dismissal HTTP 409 investigation deferred as directed. PR #44 remains draft diagnostics only; it is not a verified fix. Publishing/deployment/runtime verification remain separate and paused.
- Highest-priority next gap: automated regression coverage for ACQ-01/02/03 Get/request and Dismiss UI state transitions, while retaining backend ACQ-04/06 safe-cleanup tests. Acceptance criteria are specified in `docs/TEST_PLAN.md`. UI automation must mock acquisition API calls and never delete production files; complete manual browser verification against the exact final PR-head SHA after CI passes.
- Audit documentation only. No app code/tests were changed or run in this session. The next action is to implement this single focused regression-coverage task, not another routine backend extraction.


## 2026-10-16 — Acquisition Get/request and Dismiss regression coverage (in progress)

- Started branch test/acquisition-get-dismiss-regressions from current GitHub main following the verification audit.
- Added source-contract tests for Get's no-navigation/one-request behavior, pending/requested/retryable state transitions, and Dismiss visibility, successful card removal, and refusal/error handling. Added API adapter tests for successful Dismiss mapping and required artist/album validation.
- Existing destructive-cleanup regressions remain unchanged and required; no safety validation or production data was altered.
- Automated execution and exact-head CI have not yet been verified. UI tests are source-contract assertions, not browser execution; the manual checklist remains required after CI. No live slskd, production deletion, image publication, deployment, or runtime verification is claimed. The reported HTTP 409 remains deferred unless it recurs.


## 2026-10-16 — Last.fm artist tags extraction started

Started from GitHub main `ffa2b441e7543b2778d1835cfc42386e53c37225`. Moving cached `artist.getTopTags` response normalization into `LastFmClient.artist_genres()` while preserving `_lastfm_artist_genres()` as the compatibility adapter. Added direct-import and adapter regression cases. The initial CI run caught a test-fixture logging error because the custom fake HTTP function did not record its call; corrected the fixture in a follow-up commit. Final-head CI and merge are pending. No local tests, publication, deployment, or production runtime verification are claimed. The acquisition dismissal HTTP 409 remains deferred until modularization is complete.


## 2026-10-16 — Modularization session closeout: Last.fm extraction pair

- PR #174, `refactor: extract Last.fm artist tag parsing`, merged at `4dd8b926a7a6cf76e248420860d7c29c892da3c0` from exact tested head `08c260e2a166a744bbde4009196b53d238afb647`. Cached `artist.getTopTags` retrieval and normalization moved to `LastFmClient.artist_genres()`; legacy adapter remains.
- PR #175, `refactor: extract Last.fm top album parsing`, merged at `f922631e0393063bde02b1e0bd93d30b2d38bd2a` from exact tested head `6b5e32b1144e9f3517247110ea4383b287ce33f4`. Cached `artist.getTopAlbums` retrieval and response normalization moved to `LastFmClient.artist_top_albums()`; legacy adapter retains discovery eligibility filtering.
- Exact-head CI for PR #175 passed: Python syntax (run 38829855110), container runtime smoke (38829855100), validation-only multi-architecture image validation (38829855093), and Docker packaging/full suite/build (38829855077). PR #174's final-head checks also passed after correcting a fake-HTTP test fixture.
- Both extractions preserve legacy entry points and include direct regression coverage. No assistant-side local test run, image publication, deployment, or production runtime verification is claimed.
- Publishing remains paused. Acquisition dismissal HTTP 409 remains deferred by explicit instruction.
- Next action: on the next session, refresh GitHub main and open PRs, reread the required project workflow/testing/roadmap docs, and choose the next smallest safe extraction.


## 2026-10-16 — Two modularization extractions merged (PRs #193 and #195)

- PR #193: `musicbrainz_album_year.py` now owns exact MusicBrainz release-year lookup, artist-credit/title matching, request pacing, and positive/negative caching. The metadata route retains its compatibility adapter and response behavior. Tested head `2b426587e6cb4dc011c85099021041d9f9450744`; squash merge `bce1e32b4ca4c2df86f51dd6102931ed8299dcfe`.
- PR #195: `acquisition_candidate_queue.py` now owns pure normalization/validation for reviewed slskd file records and quality summaries. The legacy adapter retains network I/O, response mapping, and watcher startup. Tested head `f60d682b2ebcd94ecfbcfd0b4beb77c628643fc5`; squash merge `5629d259468a0f748fb5d3fdb78819a0fb00d73c`.
- All four required exact-head workflows passed on each tested SHA. PR #193: syntax/acquisition safety `38881961573`, Docker packaging/full suite/build `38881961574`, runtime smoke `38881961553`, validation-only multi-architecture `38881961580`. PR #195: syntax/acquisition safety `38882195745`, Docker packaging/full suite/build `38882195774`, runtime smoke `38882195700`, validation-only multi-architecture `38882195820`.
- No assistant-side local test execution, publication, deployment, or production runtime verification is claimed. Acquisition dismissal HTTP 409 remains deferred.
- Next: refresh main and open PRs/CI, then continue the remaining acquisition lifecycle/orchestration seams.


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

## 2026-10-16 — Modularization session closeout: PRs #216–#218

- **PR #216 — Deezer artwork selection:** exact final tested head `aa1099e8ed43b9afcce483a50be31226a66218f4`; syntax 1148, Docker/full suite/build 1055, runtime smoke 864, validation-only multi-architecture 908 all passed; merge `ad61b1b91a5c351a73c02e37d7639bc47c61a52f`.
- **PR #217 — matched Deezer album payload shaping:** exact final tested head `b631f4c6367c68357cbd91f75b986770edfeee0e`; syntax 1151, Docker/full suite/build 1058, runtime smoke 867, validation-only multi-architecture 911 all passed; merge `37f04d0a863f69f5596f6a46406cc8bd64bde039`.
- **PR #218 — exact Deezer release-year selection:** exact final tested head `0293e4fe4eab7dd66dc82280720183dab3b913ed`; syntax 1153, Docker/full suite/build 1060, runtime smoke 869, validation-only multi-architecture 913 all passed; merge `6dc6adae89169638da9a158c79ccee5d2e1ddfb7`.
- All three PRs added direct-import regression coverage and preserved route/provider/cache ownership. Assistant-side local test commands were not run; the Docker packaging workflows ran the full unit suite. No publication, deployment, or production runtime verification is claimed.
- Publishing remains paused. Acquisition-dismissal HTTP 409 remains deferred per user direction; no acquisition/import/deletion semantics were changed.
- **Next action:** refresh GitHub main/open PRs/CI and inspect remaining application-assembly/domain-service boundaries before selecting the next independent seam. Do not treat extraction count as a quota.

## 2026-10-16 — Personal recommendation allocation contract designed (pre-extraction)

- Based on GitHub main `9376d5f0d55815067aeb5cadf9015b4b775a9848`, traced `recommend_new_music()` and its policy loops. Added branch `refactor/personal-allocation-contract` with `discovery_allocation_contract.py`, `tests/test_discovery_allocation_contract.py`, and `docs/PERSONAL_RECOMMENDATION_ALLOCATION_CONTRACT.md`.
- Contract inputs are immutable prepared candidate records with stable IDs and precomputed ownership classification, plus explicit count/targets/caps. Contract output uses ordered candidate IDs and explicit decision diagnostics; adapter remains responsible for payload construction. No callbacks, provider/library access, or shared mutable counters.
- The selection loops are intentionally untouched. Contract tests are interface tests, not proof of allocation behavior. Focused execution and exact-head CI are pending. No publishing/deployment/runtime verification.
- Next: verify this contract PR; only if it passes and the seam stays independent, move the actual loops in a subsequent focused PR with policy parity regressions.

## 2026-10-16 — PR #221 merged: personal recommendation allocation contract

- Branch `refactor/personal-allocation-contract`; exact tested head `9d17a0ef32782db35b19b5226d3b8c052f8775d6`; squash merge/current main at merge `820556799fa9d3ec663e5117b36c68084281b20a`.
- Added immutable data-contract types, direct-import interface tests, and contract documentation. The four required exact-head workflows passed: syntax run `38916419736`, Docker packaging/full unit suite/build `38916419709`, runtime smoke `38916419958`, validation-only multi-architecture `38916419701` (`push: false`). Assistant-side local tests were not run independently; CI packaging ran the unit suite.
- This was a contract-design stage, not the allocation extraction. Selection loops, public signature, response construction, and provider/library operations remain unchanged. No publishing, deployment, or production runtime verification.
- Next: if the interface still fits once policy behavior is mapped to it, make the actual allocator a separate PR with comprehensive policy-parity tests. Do not add callbacks/shared mutable state to force the extraction; refine or stop if the boundary proves inadequate.



## 2026-10-16 — PR #233 merged: New Releases library qualification

- PR #233 merged to `main` from exact final PR head `2512a638001e922f5c507994b2f1e667bab9615a`; squash merge commit `08e20f502e10f829bf9ae7920106b7e8427668eb`.
- Extracted `prepare_new_release_library_scope()` to `discovery_new_releases.py`, with direct-import tests for the six-track full-album threshold, Various Artists/blank-name exclusions, stable descending album-count order, and normalized owned-album identities. Provider/cache/rate-limit operations, date policy, adapter cap, error reporting, and candidate merging remain in the adapter.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety run `38934216294`; Docker packaging/full unit suite/build run `38934216395`; container runtime smoke run `38934216347`; validation-only multi-architecture build (`push: false`) run `38934216280`.
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed; publishing remains paused.
- **Next action:** refresh GitHub main, open PRs, docs, and CI, then select the next independently testable remaining roadmap boundary. Do not treat extraction count as a quota.


## 2026-10-16 — PR #237 merged: New Releases date-window policy

- Merged PR #237; merge commit `2d11e52b78004ee51a6ce70a6a6ac6c2b451f397`, tested PR head `8d42c9f5f320fd7b4c0653fa09da8eda12f03f78`.
- Extracted deterministic 730-day cutoff/year-bound calculation into `discovery_new_releases.new_release_window(today)`; added direct-import cutoff and leap-day regressions.
- All four required workflows passed on the exact PR head: syntax `38938867862`, Docker packaging/full unit suite/build `38938867879`, container runtime smoke `38938867737`, validation-only multi-architecture image validation `38938867550` (publishing paused).
- Assistant-side local test commands were not run independently. No image publication, deployment, or production runtime verification is claimed.


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


## 2026-10-16 — Auth settings reader extraction (PR verification pending)

The lazy persisted-settings read used by authentication now delegates through `AuthSettingsReader`, with `app.main._auth_settings()` retained as the compatibility adapter. Direct-import regressions cover fresh reads (no caching) and propagation of settings-store failures. Verification and merge remain pending until focused/full tests and all four required workflows pass on the exact final PR head. Publishing remains paused.


## 2026-10-16 — PR #250 merged: pure-helper test decoupling

- Starting from GitHub main after PR #249, migrated `tests/test_quality_priority.py` away from AST extraction: quality tier assertions call `slskd_quality.quality_tier()` directly, and legacy quality-order migration uses `SettingsPersistence` directly. The UI source-contract assertions remain unchanged.
- In `tests/test_acquisition_safety.py`, pure slskd search/path/candidate/quality helper bindings now point to `slskd_search.py` and `slskd_quality.py` implementations rather than compiling those wrappers from `navidrome_server.py`. The AST harness remains for acquisition lifecycle/orchestration behavior, preserving concurrency, persistence-before-import, incomplete recovery details, dismissed-job reactivation, and stale watcher recovery tests.
- Updated the AST inventory, roadmap, and status to distinguish completed-on-branch pure-helper decoupling from the still-pending lifecycle AST removal. No application production code changed.
- Branch: `test/migrate-acquisition-pure-helpers`; PR #250 squash-merged as `c71a330ee6b5d44595c0c70299e8a61a45b15ab4` from exact final tested PR head `b14b63194da7f06737d3bc3d8c70bc3e4bc64e53`. All four required workflows passed on that exact head: Python syntax/acquisition safety and dependency map (`38955482760`), Docker packaging/full unit suite/build (`38955482766`), container runtime smoke (`38955482782`), and validation-only multi-architecture image validation (`38955483052`, publishing paused). No assistant-side local test execution was performed. No publication, deployment, or production runtime verification is claimed.


## 2026-10-16 — Migrate acquisition request lifecycle tests to the production coordinator

- Traced the lifecycle test cases in `tests/test_acquisition_safety.py` to their actual owner, `acquisition_request_coordinator.acquire_album_request()`, which is the function used by the legacy `discovery_acquire_album()` adapter.
- Changed duplicate-request concurrency, incomplete saved-download recovery refusal, dismissed-job reactivation, failed reactivation refusal, and stale-download watcher recovery tests to invoke the extracted coordinator directly with injected state. The coordinator remains responsible for the real reservation, response, and recovery decisions; the tests no longer execute the AST-compiled legacy wrapper for these cases.
- Retained the broader-search orchestration test and the import-status persistence guard in the AST harness: these still exercise behavior owned by the legacy search implementation/import adapter, and no equivalent extracted owner currently represents the full tested behavior. Existing assertions were not removed or weakened.
- Updated `docs/architecture/AST_TEST_INVENTORY.md`, `docs/MODULARIZATION_ROADMAP.md`, and `docs/PROJECT_STATUS.md` to reflect the remaining boundary accurately.
- Branch: `test/direct-import-acquisition-lifecycle`, based on GitHub main `d5e3b77aded4f32cd2d188598747b9dac820a9e6`. Tests were not executed in this authoring environment; verify focused and full suite plus all four required workflows on the exact final PR-head SHA before merge. No merge, publication, deployment, or runtime verification is claimed.


## 2026-10-16 — Adopt recommendation and operational-surface audit

- Added `recommend_new_music()` to the active roadmap as a major live responsibility (audit estimate: about 1,058 lines, roughly lines 282–1340). The required order is deterministic fake-provider characterization first, inventory-overlap review against `discovery_library_snapshot.py`, then extraction of provider-injected candidate gathering while preserving route/MCP compatibility and existing allocator/payload modules.
- Added a measurable CI size-ratchet task for `navidrome_server.py` and recorded top-level-function limits. The audit estimate of 3,514 server lines must be verified against the exact current main SHA before it becomes a threshold; limits need explicit, temporary exceptions and pass/fail tests.
- Flagged MCP-exposed `restart_server` and `apply_server_patch` as an owner decision, not an automatic refactor. No authorization or exposure decision is assumed. If retained after owner approval, the roadmap calls for a dedicated ops module and tests for unique-match rejection, no-op on mismatch, and occupied-port/restart failure.
- Added an explicit audit of mutable `MUSIC_DIR` before settings-wrapper work, and a concise line-referenced policy-vs-orchestration decision for `_discovery_acquire_album_impl()`.
- Updated workflow guidance to allow independent audit gates to run as separate concurrent PRs only when dependencies and file overlap have been checked. Each still requires exact-head verification and documented evidence.
- This documentation change does not modify application behavior or make the product decision about the operational MCP tools. Test/CI, merge, publishing, deployment, and runtime status must be recorded after PR verification; none is claimed here.


## 2026-10-16 — Enforce app-to-legacy-server import boundary (PR #254)

- Initial implementation and branch notes are superseded by the final verified merge record below. PR #254 ultimately passed all four required workflows on final head `908783f0a46618c53e4f3e4c4dcf298ec33850fc` and merged as `8bfd6a57179aec46a672343745b494dff60fec02`.
- No assistant-side local tests ran. Publishing, deployment, and production runtime verification were not performed.


## 2026-10-16 — Enforced app-to-legacy-server import boundary (PR #254 merged)

- Added `scripts/check_app_legacy_imports.py` to reject direct `navidrome_server` imports from `app/` except the narrowly allowlisted lazy import inside `app/api/dependencies.py:get_librarian()`. Added regression tests for the allowed adapter, module-level imports, wrong paths/functions, `from` imports, submodule imports, and unparsable source. Wired the guard and compile checks into `.github/workflows/python-syntax.yml`.
- Final PR head `908783f0a46618c53e4f3e4c4dcf298ec33850fc` passed all four required workflows: Python syntax/acquisition safety (`38959799724`), Docker packaging/full unit suite/build (`38959799777`), container runtime smoke (`38959799720`), and validation-only multi-architecture image validation (`38959799806`, publishing paused). The import-boundary CI step passed. No assistant-side local test command ran.
- PR #254 merged by squash as `8bfd6a57179aec46a672343745b494dff60fec02`. Verified GitHub reports the PR closed and merged. No image publication, deployment, or production-runtime verification was performed.
- Next task: characterize `recommend_new_music()` deterministically with fake provider responses and a fixed listen/library fixture; trace `discovery_library_snapshot.py` and resolve inventory overlap before extracting candidate gathering.


---

## 2026-10-16 — PR #272 merged: broader-query fallback test decoupling

- Based on GitHub main commit `de94d9bbb9790129ed86dc9fefd28a1850a9c721`. Branch: `test/direct-search-fallback-regression`.
- Moved the broader-query fallback regression out of the AST harness in `tests/test_acquisition_safety.py` into direct-import coverage in `tests/test_slskd_search_polling.py`. The direct test uses the production query generator and polling implementation, asserts the exact Tinariwen query pair, request timeouts (15,000 ms then 6,000 ms), per-attempt collected response counts (0 then 1), aggregate counts, and ordered query diagnostics via `acquisition_search_diagnostics.no_match_message()`.
- The AST harness no longer compiles `_discovery_acquire_album_impl()`; it remains for the import/dismissal adapter and other acquisition lifecycle cases. No production acquisition code, candidate eligibility, queueing, concurrency, persistence, or filesystem-safety behavior was changed or removed.
- First CI attempts exposed two test-only defects: an empty class left after removing the AST test, and an assertion that overlooked the third generated query variant. Both were corrected; the fallback search stops after the second query returns a usable payload.
- Final code/test head `8a464edf8313594ddde69f0be90135fce4782f07` passed all four required workflows: Python syntax/acquisition safety (`38969125353`), Docker packaging/full unit suite/build (`38969125409`), isolated container runtime smoke (`38969125262`), and validation-only multi-architecture image validation (`38969125387`, publishing paused). The full suite passed 554 tests in both unit-test workflows. The latest code head has no production behavior changes. No live slskd search/download, filesystem mutation, deployment, or production runtime verification was performed.
- PR #272 was squash-merged as `9b97f447adc602a3be3b5ac496633430f3eb3cb4`. All four required workflows passed on the exact final PR head `7b1257e0ceb9368063de025a2758f48a344efbcb`: Python syntax/acquisition safety (`38969292510`), Docker packaging/full unit suite/build (`38969292338`), isolated container runtime smoke (`38969292382`), and validation-only multi-architecture image validation (`38969292490`, non-publishing). The full suite passed 554 tests. Publishing, deployment, and production runtime verification were not performed.


## 2026-10-16 — PR #274 merged: final acquisition safety AST coupling removed

- Based on current GitHub main `5a74b12d489ae30cfad923af7b68985ebede87dc`. Branch: `test/remove-acquisition-safety-ast`.
- Removed the `ast.parse()` of the legacy server source test harness from `tests/test_acquisition_safety.py`. The test fixture now creates isolated state directly; the import persistence-failure regression composes the production `acquisition_orchestration.import_source_unless_dismissed()` guard with `acquisition_import_service.import_completed_source_locked()`.
- Preserved assertions that failed persistence prevents the importer callback and destination creation. Existing direct tests continue to cover dismissal/lock behavior, request concurrency, recovery/retry refusal, source validation, rollback, symlink escapes, no-overwrite, and unrelated-file preservation. No production code changed.
- Exact final PR head `ad6864ea1f5f70b7f9d8b852bbc4bb02e7c2d395` passed all four required workflows: Python syntax/acquisition safety (`38970088355`), Docker packaging/full unit suite/build (`38970088327`), container runtime smoke (`38970088307`), and validation-only multi-architecture image validation (`38970088322`, publishing paused). The full suite passed 554 tests. PR #274 squash-merged as `cae95e74c9910c512392de80b337eb4b21de67a5`.
- No production code changed. Publishing, deployment, and production runtime verification were not performed.
- Next: obtain the owner decision on MCP-exposed `restart_server` and `apply_server_patch`; no changes to those capabilities before authorization.


## 2026-10-16 — PR #276 merged: retire legacy operational MCP tools

- Based on GitHub main `fc73958eac7b3e1b95ab29493fb023f63b76bd41`. Branch: `remove/legacy-operational-mcp-tools`.
- Safety audit found `restart_server` and `apply_server_patch` had no internal callers and were exposed only through `mcp_registry.TOOL_NAMES`. The former kills/relaunches the server on hardcoded port 8000; the latter rewrites `navidrome_server.py` on disk. Per the owner's earlier direction to remove these if safe, both definitions and registry entries are removed; the other 25 tools and MCP runtime remain.
- Updated `tests/test_mcp_registry.py` to assert 25 unique tools and that the two retired functions are neither registered nor exposed by the legacy service. Added a decision record and updated the active roadmap/workflow/status docs.
- Exact final PR head `67320d555d2ce5f26868b57f8d46a5b46b295f81` passed all four required workflows: Python syntax/acquisition safety (`38970741140`), Docker packaging/full unit suite/build (`38970741125`), container runtime smoke (`38970741243`), and validation-only multi-architecture image validation (`38970741035`, publishing paused). The full suite passed 554 tests. PR #276 squash-merged as `fb5085f7b62b4b9616372c4d044fd974320b2f76`.
- No live service restart, source rewrite, deployment, or publication was performed.
- Next: run the modularization completion audit against current main, including the dependency-map artifact, remaining legacy references, and size-ratchet measurements.


## 2026-10-16 — PR #277 merged and modularization completion audit

- PR #277 merged as `d6e32aadfbca6e1d746ced657bdc124b9d472251`. All four required workflows passed on its exact final PR head `246355b556bdb0d95830a5d504186fc1a14961f0`: syntax/acquisition safety `38970922948`, Docker packaging/full unit suite/build `38970922994`, runtime smoke `38970923035`, and validation-only multi-architecture image validation `38970923009`. Publishing remained paused.
- Current-main CI on `d6e32aadfbca6e1d746ced657bdc124b9d472251` passed all four workflows. The syntax workflow's dependency-map artifact `12077720422` (SHA-256 `4231dc3f9e23161c1d593c781758dd6ac834ebf0f10d14088880761211150879`) was reviewed: 168 repository modules, 73 modules in the app import closure, and one AST-visible app-to-`navidrome_server` edge at `app/api/dependencies.py:10`, the intended lazy service import. The map notes dynamic imports/dependency injection require manual review.
- The current size-guard log reports `navidrome_server.py` at 2,768 lines (limit 3,031), `recommend_new_music()` at 568 AST lines (temporary limit 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280); guard passed. The two retired operational tool names are absent from the service source and MCP registry; registry contains 25 tools. Their intentional mentions remain in tests and decision/history docs.
- PR #278 centralized the duplicated category classification in `discovery_recommendations.classify_recommendation_category()`. Exact PR head `d17f9b52823a7dbc7a5f291441bddef9061f4e7a` passed all four required workflows: syntax/acquisition safety (`38971546874`), Docker packaging/full unit suite/build (`38971547354`), runtime smoke (`38971547239`), and validation-only multi-architecture image validation (`38971546979`, publishing paused). The full suite passed 560 tests. Merge commit: `d619a83c064f3cc106356d96bf83747755c8072a`.


## 2026-10-16 — PR #278 merged and current-main audit refreshed

- PR #278 merged as `d619a83c064f3cc106356d96bf83747755c8072a`. The shared category policy reduced `recommend_new_music()` from 568 to 466 AST lines while preserving the existing characterization tests and adding six direct policy tests plus a selection/diagnostic category consistency assertion. Exact PR head `d17f9b52823a7dbc7a5f291441bddef9061f4e7a` passed all four required workflows; the full suite passed 560 tests.
- Current-main dependency-map artifact `12076627980` (SHA-256 `31105d5ff631b58093855dbfb7e6b62237fd44454c4327b3996be4f211976c94`) on `d619a83c064f3cc106356d96bf83747755c8072a` reports 169 Python modules and a 73-module app import closure. The only AST-visible app import of `navidrome_server` remains the intentional lazy import at `app/api/dependencies.py:10`. Dynamic imports/dependency injection remain outside the static graph and are covered by manual review and tests.
- Current size guard passes at 2,666 `navidrome_server.py` lines (limit 3,031), `recommend_new_music()` at 466 AST lines (temporary limit 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280). The retired operational functions are absent from service source and MCP registry; registry remains 25 tools.
- Next seam: extract the bounded Last.fm scoring/profile-adjustment loop from `recommend_new_music()` into a directly testable policy helper, preserving lookup cap/order, score multipliers, missing-stat behavior, tag-driven profile adjustment, and checked-count diagnostics.


## 2026-10-16 — PR #280 merged: Last.fm recommendation scoring extracted

- PR #280 merged as `3dc999b872bdf12db30c43ee73b5e726c4ea494b`. Exact PR head `ce2fc91612d6fbb8deb25e2222830db3ff0c8fd5` passed all four required workflows: syntax/acquisition safety (`38971979899`), Docker packaging/full suite/build (`38971979883`), runtime smoke (`38971979880`), and validation-only multi-architecture image validation (`38971979885`, publishing paused). The full suite passed 564 tests.
- The direct-import `apply_lastfm_popularity_bonus()` helper preserves top-40 score order, missing-stat skips, recent-family recomputation from Last.fm tags, capped popularity score multiplier, and the diagnostic checked count. A first CI attempt on an earlier head exposed the accidentally removed `lastfm_api_configured` assignment; it was restored before final verification. No provider calls or production data were used.
- Current-main dependency-map artifact `12076948070` (SHA-256 `5f56d6735f0416674aa853435f1ce1d126d015d930ad604c96226341ce185682`) on `3dc999b872bdf12db30c43ee73b5e726c4ea494b` reports 170 repository modules and a 73-module app import closure; the only AST-visible app-to-legacy-server edge remains the lazy import at `app/api/dependencies.py:10`.
- Current size guard passes at 2,616 server lines (limit 3,031), `recommend_new_music()` at 416 AST lines (temporary limit 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280).
- Next seam: extract the familiarity multiplier thresholds and exploration-family boost into `discovery_recommendations.apply_familiarity_exploration_bonus()`, with direct tests for every threshold and the family-overlap condition.


## 2026-10-16 — PR #281 merged: familiarity/exploration scoring extracted

- PR #281 merged as `93519c403ac2c301c46acddf6a64d59059d3f683`. Exact PR head `176914b3e4712d3090cb2fa80a4246fb12e89b2b` passed all four required workflows: syntax/acquisition safety (`38972398532`), Docker packaging/full suite/build (`38972398406`), runtime smoke (`38972398402`), and validation-only multi-architecture image validation (`38972398450`, publishing paused). The full suite passed 566 tests.
- `discovery_recommendations.apply_familiarity_exploration_bonus()` now owns the recent-artist multipliers and 1.10 exploration-family boost. Direct tests cover every threshold boundary and both overlap/no-overlap cases. No public response fields, provider calls, allocation policy, or production behavior changed beyond extracting the same scoring operations.
- Current-main dependency-map artifact `12078000327` (SHA-256 `cd9c931dd7e3ccb740f1ab24c01686a27c8f6b51ed7be58c87e301b6b6e0b58e`) on `93519c403ac2c301c46acddf6a64d59059d3f683` reports 171 Python modules and a 73-module app import closure. The sole AST-visible app import of `navidrome_server` remains the intentional lazy import at `app/api/dependencies.py:10`.
- Current size guard passes at 2,596 server lines (limit 3,031), `recommend_new_music()` at 396 AST lines (current temporary exception 575), and `_discovery_acquire_album_impl()` at 278 AST lines (limit 280).
- Next: tighten the recommendation adapter exception from 575 to 450 lines, then audit the remaining function for a clear independent seam rather than extracting solely for size.


## 2026-10-16 — PR #283 merged: recommendation size ratchet tightened

- PR #283 merged as `767ac3efd4e02eab15c04fd033fabeb619f4b1ff`. Exact PR head `992405682a8a942738ab354393e70a3fb8c89ab8` passed all four required workflows: syntax/acquisition safety (`38972838143`), Docker packaging/full suite/build (`38972838173`), runtime smoke (`38972838187`), and validation-only multi-architecture image validation (`38972838218`, publishing paused). The full suite passed 567 tests.
- The `recommend_new_music()` exception is now 450 AST lines; a regression accepts 450 and rejects 451 using the default exception configuration. The current function is 396 lines, leaving 54 lines of headroom. The 280-line general function ceiling and 3,031-line server ceiling are unchanged.
- Current-main CI on `767ac3efd4e02eab15c04fd033fabeb619f4b1ff` passed all four workflows. Size measurements: `navidrome_server.py` 2,596 lines, `recommend_new_music()` 396 AST lines, and `_discovery_acquire_album_impl()` 278 AST lines. Size guard passed.
- Current-main dependency-map artifact `12077488636` (SHA-256 `39b6b2854789f0273b117adb1b9357e4765e420f87f61b05b4932f4b45c5ad49`) reports 171 Python modules and a 73-module app import closure. The sole AST-visible app-to-legacy import remains the intentionally lazy import at `app/api/dependencies.py:10`.
- **Modularization completion decision:** after extracting provider gathering, category classification, Last.fm scoring, and familiarity/exploration scoring, the remaining `recommend_new_music()` code coordinates candidate ordering, allocation/ownership decisions, diagnostic projection, and public response shaping. Extracting the diagnostic loop now would require a broad shared-state context and would not simplify the boundary enough to justify it. Retain it under the 450-line ratchet; revisit only with a concrete bug or feature that reveals a smaller independently testable seam. No more size-only extraction work is planned.


## 2026-10-17 — Modularization completion audit closed

- Reviewed the current-main completion state after PR #288 and the subsequent documentation-only closeout: dependency-map generator and CI artifact step, app-to-legacy import guard and lazy compatibility edge, AST-test inventory, Docker COPY inclusion test, current Dockerfile root-module list, recommendation/acquisition retained orchestration, and the roadmap's definition of done.
- The dependency map is generated in CI rather than committed as a mutable snapshot. It traverses repository-local AST imports from `app.main`; its documented limitation is that dynamic imports and dependency injection require manual inspection. The only reviewed app-to-legacy import remains `app/api/dependencies.py:get_librarian()`.
- The packaging regression checks all AST-visible root-level imports in `navidrome_server.py` against Docker COPY sources. The post-PR #288 audit records all 48 imported modules present; PR #286 and PR #288 fixed the two delayed-import omissions found during this audit sequence.
- The AST-coupled test inventory records the migration to direct imports without weakening acquisition concurrency, recovery, persistence, or filesystem-safety coverage. The recommendation adapter and acquisition lifecycle coordinator remain justified orchestration; no narrower boundary emerged from this audit.
- **Decision: modularization roadmap complete.** No further concrete correctness, safety, or testability gap was identified. No size-only or speculative extraction is scheduled. Reopen only for a concrete defect or requirement.
- Verification evidence available in GitHub: PR #288 exact head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c` passed all four required workflows (syntax `38978049684`, Docker packaging/full unit suite/build `38978049670`, runtime smoke `38978049793`, validation-only multi-architecture `38978049589`, publishing paused). This audit did not run local tests or re-run those workflows on the documentation-only commit. No publishing, deployment, or production runtime verification is claimed.


## 2026-10-17 — Service configuration defaults audit

- Started focused branch `fix/remove-personal-network-defaults` from main `bf27b86069e5acb420f7e5663783a01fa4e36076`.
- Removed the personal ListenBrainz username fallback and the private `192.168.1.12` Navidrome/slskd URL fallbacks from Python settings defaults, the slskd settings tool signature, Compose defaults, and `.env.example`. Unconfigured service URLs/usernames now rely on existing validation to report configuration errors rather than silently targeting a personal account or private host.
- Added regression assertions that blank Navidrome/slskd URLs and a blank ListenBrainz username fail validation.
- Added `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` with audit findings and next-session proposals: remove fixed regional targets, make supplementary discovery responsive to recent listening, reduce artist-specific overrides, and test ranking variability/refresh/cache behavior while preserving ownership and eligibility safeguards.
- **PR #292 merged:** final PR head `51f3a0e1ee55334020bc26793ca1d86a6c145a7c`; merge commit `0db291970fbeff2ed192d73b04fe1efc8ecb3cb6`.
- **CI:** all four required workflows passed on the exact final PR head: `compile`, `test-and-build`, `container-smoke`, and `validate-container`. Local test commands were not run. Publishing remains paused; no deployment or production runtime verification is claimed.
- **Configuration caveat:** existing persisted settings were not migrated, so values previously saved in an installation may remain until explicitly changed.

## 2026-10-17 — MCP retirement plan drafted

- Inspected current GitHub `main` documentation and implementation relevant to MCP retirement: project status, product requirements, development workflow, test plan, `mcp_registry.py`, `navidrome_server.py`, the lazy web-service adapter, MCP registry tests, `requirements.txt`, Dockerfile, and Compose configuration.
- Confirmed that MCP is not fully retired: `mcp_registry.py` still registers 25 tools, `navidrome_server.py` retains a standalone streamable-HTTP MCP startup path on `127.0.0.1:8000`, and `requirements.txt` still declares `mcp==2.3.0`.
- Recorded that the web app shares service logic through `app/api/dependencies.py:get_librarian`; retiring MCP must not remove recommendation, discovery, settings, acquisition, recovery, persistence, or filesystem-safety behavior. The consumer audit must establish whether any external clients rely on the MCP endpoint before removal.
- Added `docs/MCP_RETIREMENT_PLAN.md` with the audit sequence, focused removal approach, regression requirements, packaging checks, required four-workflow CI gate, and definition of done. The plan explicitly does not authorize publishing or deployment.
- No implementation code changed and no tests were run locally in this documentation-planning session. Existing historical CI results do not verify this new commit; record exact PR-head CI evidence before merge. Publishing remains paused; no deployment or production runtime verification is claimed.
- Next action: complete the consumer/reference audit and prepare a focused MCP retirement implementation PR.

## 2026-10-17 — PR #295 merged: MCP retirement plan

- Added `docs/MCP_RETIREMENT_PLAN.md` and updated `docs/PROJECT_STATUS.md` to record the focused migration plan and next action.
- PR #295 final head: `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`; merge commit: `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- All four required GitHub Actions workflows passed on the exact final PR head: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remained paused.
- Local tests were not run because this was a documentation-only planning change. No MCP implementation was removed. No publishing, deployment, or production runtime verification is claimed.
- Next action: complete the MCP consumer/reference audit, then prepare a focused implementation PR preserving shared web/service behavior and safety coverage.
