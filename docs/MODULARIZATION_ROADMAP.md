# Modularization roadmap

Last reviewed: 2026-10-17 (completion audit closed)
Audit base: GitHub main code at PR #288 final head `92042dd9d7fbb755e4898b1bd1d1a35b97e41b7c`; later main change was documentation closeout.

## Purpose

This roadmap is **closed** after the final transitive-import and dependency-map audit. It is retained as an architecture decision record; completed extraction details and verification evidence belong in the root `PROJECT_LOG.md`. Do not reopen it for size-only work or speculative extractions. Reopen only when a concrete correctness, safety, testability, or product requirement establishes a worthwhile change.

Do not add a roadmap entry merely because a function or file is large. Extract only a cohesive responsibility with a clear owner, meaningful direct-import tests, and a compatibility boundary that is simpler than the current design.

## Audited work and retained boundaries

### 0. Recommendation candidate gathering — policy seams extracted; retain orchestration

`recommend_new_music()` remains the live adapter used by the `/discovery` route and MCP tool. On current `main`, it has 396 AST-measured lines and delegates provider calls to `discovery_candidate_gathering.py`, allocation to `discovery_personal_allocator.py`, category, Last.fm, and familiarity/exploration scoring to `discovery_recommendations.py`, and payload construction to `discovery_recommendation_payload.py`. It coordinates candidate ordering, allocator inputs, ownership/decision maps, diagnostic projection, and the public response. PRs #255/#257/#259 established deterministic characterization coverage for ownership, duplicate IDs, response shape, inventory failures, score ordering, provider failures, Last.fm bonus, and regional MusicBrainz diagnostics.

**Inventory overlap assessment (PR #259):** both the recommendation adapter and `discovery_library_snapshot.py` page `getAlbumList2` in batches of 500 up to 50,000 records and deduplicate non-empty album IDs. They do not have interchangeable contracts. The snapshot first reads/writes a 10-minute cache, also loads artists, and normalizes album records to `album`/`song_count`/`coverArt`; `recommend_new_music()` intentionally reads a fresh raw inventory, indexes `name` and `artist`, and converts retrieval exceptions and safety-limit exhaustion into distinct JSON error payloads. Reusing `build_library_snapshot()` directly would change freshness, record shape, and failure behavior. PR #261 extracted `fetch_album_inventory()` as the shared **raw pagination helper**, with injected API/items, stable ID deduplication, and a typed limit error carrying the retrieved count. The snapshot adapter retains its cache and normalization; the recommendation adapter retains fresh raw records and its JSON error shapes.

Required sequence:
1. Characterization now covers inventory ownership, duplicate IDs, response shape, inventory failure/limit behavior, score-based output ordering, early ListenBrainz failure/empty-result behavior, the Last.fm bonus, and regional MusicBrainz HTTP failure. PR #261 adds direct tests for the shared raw inventory helper.
2. **Completed by PR #261:** share raw pagination without reusing `build_library_snapshot()` directly; keep the snapshot's 10-minute cache/normalized schema and the recommendation adapter's fresh raw inventory/error payloads distinct.
3. **Completed by PRs #263/#264:** provider calls are behind `RecommendationProviders`; PR #264 restored the regional counters and raw library inventory in the provider mapping and compatibility adapter, preserving the public response contract.
4. **Completed by PR #265:** the measurable size ratchet is enforced. Current `main` measures `navidrome_server.py` at 2,596 lines, `recommend_new_music()` at 396 AST lines against its tightened 450-line exception, and `_discovery_acquire_album_impl()` at 278 lines against the 280-line default limit.
5. **Completed by PR #278:** selection and diagnostic projection now share `discovery_recommendations.classify_recommendation_category()`. Direct-import tests pin unclassified handling, regional artist overrides, adventurous-tag precedence, cross-genre, adjacent, and fallback adventurous. PR #278 also asserts that the selected recommendation category agrees with diagnostic projection.
6. **Completed by PR #280:** the bounded Last.fm score/profile adjustment loop now lives in `discovery_recommendations.apply_lastfm_popularity_bonus()`. Direct tests pin top-40 score-order lookup, missing-stat behavior, tag-driven recent-family recomputation, the capped 1.12 multiplier, and the checked count. The adapter still owns `lastfm_api_configured`, `LASTFM_LAST_ERROR`, provider/cache implementation, and response shaping.
7. **Completed by PR #281:** familiarity thresholds and exploration-family boost now live in `discovery_recommendations.apply_familiarity_exploration_bonus()`. Direct tests cover all boundaries (0, 1–2, 3–5, 6–10, >10) and verify the 1.10 bonus applies only on family overlap. The adapter still owns recent-artist lookup and genre-cache access.
8. **Completed by PR #283:** reduce the temporary `recommend_new_music()` size exception from 575 to 450 AST lines after the category, Last.fm, and familiarity/exploration policy extractions. Current size is 396 lines, leaving 54 lines of headroom. The general 280-line and server 3,031-line limits remain unchanged.


**Retention decision after PR #283:** do not extract the remaining diagnostic projection solely to reduce the adapter further. That loop combines allocation outcomes, candidate decisions, ownership lookup results, genre/family metadata, and public diagnostic fields; splitting it now would require passing a broad shared-state context into another helper. The adapter is now under its tightened exception, all distinct provider/category/Last.fm/familiarity scoring policies have direct owners, and response characterization remains in place. Revisit only if a concrete behavior change or defect establishes a smaller testable boundary.

Acceptance: fixed-provider characterization remains green; the shared raw inventory contract remains distinct from the cached snapshot; category policy has direct-import tests; both selection and diagnostics use the same production helper; route/MCP response fields, category ordering, ownership checks, scoring, and failure behavior remain unchanged.

### 0a. Measurable size ratchet

PR #265 added `scripts/check_server_size.py`: a 3,031-line server ceiling, a 280-line general top-level-function ceiling, and a temporary named 450-line exception for `recommend_new_music()` (tightened by PR #283). On current main after PR #283, the server is 2,596 lines. The guard uses AST `end_lineno` measurements, reports offending function names and sizes, and prints the ten largest functions in CI. The exception includes a rationale and follow-up plan; lower it as the recommendation adapter is decomposed.

**Implemented and merged by PR #265.** The CI guard in `scripts/check_server_size.py` enforces a 3,031-line file ceiling, a 280-line default top-level-function ceiling, and a temporary named 450-line exception for `recommend_new_music()` (tightened after the policy extractions in PR #283). On current main after PR #283, AST sizes are 396 lines for `recommend_new_music()` and 278 for `_discovery_acquire_album_impl()`. The recommendation exception is now 450 lines. Keep this exception only while the remaining compatibility orchestration/diagnostic projection has no narrower independently testable boundary; never extract for size alone. Tests prove accepted and rejected boundaries, including exception diagnostics. Update ceilings only through a reviewed change with a rationale; never raise them just to accommodate unrelated growth. As `recommend_new_music()` is decomposed, tighten its exception rather than normalizing its current size as acceptable architecture.

### 0b. Legacy operational MCP functions — retired

The owner requested removal of the early-development `restart_server` and `apply_server_patch` capabilities if safe. The audit found no internal callers; their only runtime exposure was the ordered MCP registry. `restart_server` killed/relaunched the process on hardcoded port 8000, and `apply_server_patch` rewrote the running service's own source file. PR #276 removed both definitions and registry entries while preserving the remaining 25 MCP tools and the MCP runtime.

**Status: implemented, tested, and merged.** PR #276 exact head `67320d555d2ce5f26868b57f8d46a5b46b295f81` passed all four required workflows and the full 554-test suite; merge commit `fb5085f7b62b4b9616372c4d044fd974320b2f76`. Do not restore either capability without a new explicit owner decision and a separate security review. The MCP server itself is not being retired.


### 0c. Mutable settings coupling — audited; no state-object extraction justified

The current MUSIC_DIR audit found this dependency pattern in navidrome_server.py:

- **Initialization:** MUSIC_DIR is initialized from the environment/default-path helper, then SettingsPersistence.read() runs during module initialization and may apply an absolute persisted music_library_path.
- **Central persistence adapter:** SettingsPersistence receives a getter for MUSIC_DIR and a setter callback. Its read() applies an absolute saved path through the setter; its migration logic reads the current path to derive legacy downloads-path candidates.
- **Writers:** _set_music_dir(), plus nested setters in discovery_set_navidrome_settings() and discovery_set_slskd_settings(), mutate the same module global. Both public settings writers validate/persist the new path through service_settings.py and then update the runtime path.
- **Readers:** the default settings mapping derives music_library_path and fallback slskd downloads path from the initial path; find_missing_mbids() passes the current path to tag scanning; settings-get adapters serialize the current path; acquisition/import adapters pass the current path into recovery and watcher service dependencies.
- **Tests and extracted boundaries:** tests/test_service_settings.py tests settings policy with injected getter/setter callbacks and temporary directories. settings_persistence.py has its own callback-based persistence boundary. Existing acquisition modules accept music_dir explicitly at invocation time, so the legacy adapter is where the global is read.

**Decision:** do not introduce a settings object or extract the remaining wrappers now. The existing persistence and service-settings modules already accept explicit path callbacks, while navidrome_server.py acts as the mutable runtime owner and compatibility adapter. A new object would duplicate the same getter/setter wiring without eliminating the legacy boundary. The nested settings setters are thin adapters, not independent policy. Revisit only if a broader app-state lifecycle change gives the object a clear owner and can prove that long-running watcher/recovery work observes path changes with the same semantics.

This audit did not justify another extraction: the acquisition coordinator remains orchestration, and the AST-coupled import-safety migration is already complete in PR #274. The next active task is the final modularization completion audit, not another size-driven refactor. PR #286 fixed the missing `acquisition_import_service.py`; PR #288 fixed the missing `discovery_candidate_gathering.py` and generalized the Docker packaging regression. All four required workflows passed on PR #288's exact head. A post-merge direct-import comparison confirms all 48 root-level modules imported by `navidrome_server.py` are included in the current Docker COPY list.


These are audit targets, not permission to refactor without inspecting current main. Reconfirm each target against current callers, tests, and open PRs before implementation.

### 1. Application assembly and test coupling — AST migration complete; final packaging audit active

The dependency-map artifact and import-boundary work established the expected static edge: `app/api/dependencies.py:get_librarian()` lazily imports `navidrome_server`, while `scripts/check_app_legacy_imports.py` rejects other app-to-legacy imports. `docs/architecture/AST_TEST_INVENTORY.md` confirms the source-layout migration is complete; do not reopen those tests without new evidence.

**Completion-audit finding (current main `1f8f37ba7f9c289b694b1089492ba7a3cfdacf82`):** the Dockerfile explicitly enumerates root-level Python modules copied into the image. `navidrome_server.py` lazily imports `acquisition_import_service.import_completed_source_locked()`, but `acquisition_import_service.py` is absent from that COPY list. The focused runtime smoke test may not trigger the delayed import-completion path, so the existing green history is not evidence that this module is available when that path runs in the container.

**Active task:** add `acquisition_import_service.py` to the Docker COPY list and add a regression that asserts the required module is packaged. Verify the final PR head through all four required workflows, including the container runtime smoke test. No local tests have been run as part of this audit.

After that fix merges, complete the audit against exact current `main`: review the dependency-map artifact generated for that revision, inspect all Python references under `app/`, distinguish dynamic imports and injected dependencies from static edges, verify all imported root modules are packaged, and confirm direct-import plus compatibility/safety regressions remain in place. If this audit finds no additional concrete defect or independently testable boundary, mark modularization complete; do not invent another extraction.

Acceptance criteria:
- The generated dependency map is reviewed against the exact source revision, with runtime/dynamic imports checked separately.
- The only app-to-legacy-server import remains the documented lazy adapter at `app/api/dependencies.py:get_librarian`.
- Every root-level module required at runtime is included in the Docker image, with regression coverage for the discovered missing module.
- AST-coupled behavior tests target production modules directly; adapter/MCP compatibility tests remain.
- Acquisition/import/deletion safety and compatibility contracts remain unchanged.
- No additional extraction is undertaken unless it improves correctness, safety, or testability enough to justify its dependency surface.

### 2. Acquisition coordinator — audited; retain orchestration

Audit against GitHub `main` at `cd5d0240c1ac696417727de938736a1b15f7582b` (2026-10-16), with `_discovery_acquire_album_impl()` at lines 2341–2618 (278 lines by AST size, consistent with the CI size report). The function validates input and settings, calls `slskd_search_polling.collect_search_responses()`, delegates candidate extraction to `_slskd_extract_candidates()`, and delegates queue-error classification to `acquisition_lifecycle.queue_failure_action()`. It then coordinates the existing queue-unless-dismissed adapter, start-state probe, cleanup guard, watcher startup, and public response/status updates.

The remaining inline decisions are tightly coupled to that sequence: only the first ten clear candidates are attempted; a rejected queue source can fall through to the next peer, a fatal authorization/configuration response terminates, and uncertain queue/start outcomes are monitored rather than blindly retried. A definitively stopped source is cleaned before trying another peer, and cleanup refusal terminates fallback. These are consequential state transitions, but the function does not expose a cohesive independent policy API that can be moved without reproducing the orchestration or widening the dependency surface. The existing extracted modules already own the independently testable search, candidate, queue-error, source-switch, cleanup, and watcher responsibilities.

**Decision: retain `_discovery_acquire_album_impl()` as orchestration.** No application code changed. Do not extract it for size alone. Revisit only if a focused characterization effort identifies a smaller policy function with independent callers and direct-import tests. PR #274 removed the final AST/source-layout coupling from `tests/test_acquisition_safety.py`; direct-import production-owner tests preserve persistence-before-import, dismissal-lock, concurrency/recovery, and filesystem safety. The migration is merged and verified. Re-run the repository source search after future test changes.

Preserve concurrency and lock behavior, conditional state transitions, persistence, queue uncertainty, recovery, dismissal/import exclusion, watcher startup, mount identity, rollback, no-overwrite behavior, cleanup refusal, and path safety. Add tests for both safe success and unsafe refusal. Do not bundle this work with unrelated refactors.

### 3. slskd integration — no size-only work

Search polling, quality, transfer matching, progress, and connectivity responsibilities have already been extracted in prior work. Treat remaining code as adapter/wiring unless a concrete duplicated policy or independently testable orchestration responsibility is demonstrated.

## Definition of done

Modularization is complete when:
- cohesive domain responsibilities have clear owners and usable direct-import tests, including characterization coverage for recommendation internals before extracting candidate gathering;
- remaining server code is primarily justified orchestration, provider access, dependency wiring, or compatibility adapters;
- imports and package/Docker inclusion are intentional;
- critical acquisition/import/deletion paths retain regression coverage for success and unsafe failure;
- application assembly and AST-based tests have been audited for accidental coupling;
- no higher-priority correctness, security, automated verification, or delivery gap is being bypassed;
- a CI size ratchet prevents unreviewed growth in `navidrome_server.py` and top-level functions, with explicit temporary exceptions only where necessary;
- operational MCP capabilities have an explicit owner decision and, if retained, authorization and safety coverage;
- the remaining work would not make the architecture simpler or safer enough to justify its cost.

The number of extractions is not a goal or quota. A documented decision to retain a responsibility in an adapter is a valid outcome.

## Verification and release constraints

For each code PR, follow `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`: focused regressions, full unit suite, syntax/package/API checks where applicable, complete diff review, and all four required workflows on the exact final PR-head SHA. UI changes also require the documented manual browser checks.

Publishing remains paused until the roadmap is complete and publishing is explicitly authorized. CI/build success is not publication, deployment, or production runtime verification. Acquisition-dismissal HTTP 409 remains deferred unless it becomes reproducible or is explicitly re-prioritized.

## Final completion audit — 2026-10-17

**Decision: complete; no further modularization work is scheduled.**

- **Transitive import graph:** reviewed the deterministic AST graph generator `scripts/dep_map.py`, the CI generation/upload step in `.github/workflows/python-syntax.yml`, and the documented dependency-map artifact evidence. The graph covers repository-local modules transitively from `app.main`, including app/API modules and `navidrome_server.py`; its own notes correctly flag dynamic imports and dependency injection as requiring manual review. The map is an audit artifact, not a committed source-of-truth graph.
- **App-to-legacy boundary:** `scripts/check_app_legacy_imports.py` enforces the only permitted app edge: the lazy import in `app/api/dependencies.py:get_librarian()`. The app-import isolation regression remains documented in the AST inventory. No additional permitted edge was justified.
- **Docker transitive-risk follow-up:** PR #286 fixed the lazy `acquisition_import_service.py` omission; PR #288 fixed `discovery_candidate_gathering.py` and generalized `tests/test_docker_packaging.py` to compare AST-visible root-module imports from `navidrome_server.py` against Docker COPY sources. The latest documented audit found all 48 imported root-level modules present. Container startup alone is not treated as proof of delayed import coverage.
- **Test coupling:** `docs/architecture/AST_TEST_INVENTORY.md` records that the behavioral AST/source harnesses were migrated. `tests/test_acquisition_safety.py` retains direct production-owner tests for concurrency, recovery, persistence-before-import, and unsafe refusal; compatibility tests remain separate. No assertions or filesystem-safety coverage were intentionally weakened.
- **Dynamic imports and runtime behavior:** manually reviewed the documented lazy compatibility import, service wiring, MCP registry, and Docker's explicit copy boundary. Static AST analysis cannot prove all runtime reachability; the four required CI workflows remain the repository's release gate. No local test run, deployment, publication, or production-runtime verification is claimed for this documentation audit.
- **Retained orchestration:** the remaining `recommend_new_music()` projection/allocation sequence and `_discovery_acquire_album_impl()` are kept as compatibility/orchestration boundaries. Extracting them further would widen shared-state/dependency surfaces without a concrete independent policy or testability gain.
- **Outcome:** acceptance criteria in Definition of done are satisfied by merged implementation, regression coverage, CI evidence recorded in the project log, explicit package/import boundaries, and documented retain decisions. No new extraction, test, or dependency layer is warranted.

Publishing remains paused pending separate explicit authorization. This completion decision does not imply publication, deployment, or production-runtime verification.

## History

Use the root `PROJECT_LOG.md` to retrieve completed extraction records by PR, module, or responsibility. Do not append completed work or CI run IDs here.