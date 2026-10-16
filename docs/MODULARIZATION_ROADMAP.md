# Modularization roadmap

Last reviewed: 2026-10-16 (PR #280 merged; current main `3dc999b872bdf12db30c43ee73b5e726c4ea494b`)
Audit base: GitHub `main` at commit `3dc999b872bdf12db30c43ee73b5e726c4ea494b`

## Purpose

This file is the **active plan**, not an extraction diary. It lists only work that remains useful after checking the current implementation. Completed extraction details and verification evidence belong in the root `PROJECT_LOG.md`; current session state belongs in `docs/PROJECT_STATUS.md`.

Do not add a roadmap entry merely because a function or file is large. Extract only a cohesive responsibility with a clear owner, meaningful direct-import tests, and a compatibility boundary that is simpler than the current design.

## Current priorities

### 0. Recommendation candidate gathering — provider seam complete; policy cleanup remains

`recommend_new_music()` remains the live adapter used by the `/discovery` route and MCP tool. On current `main`, it spans source lines 282–704 (423 physical lines; 416 AST-measured lines) and delegates provider calls to `discovery_candidate_gathering.py`, allocation to `discovery_personal_allocator.py`, category policy and Last.fm scoring to `discovery_recommendations.py`, and payload construction to `discovery_recommendation_payload.py`. It still coordinates familiarity/exploration score adjustments, allocation input preparation, and diagnostic projection. PRs #255/#257/#259 established deterministic characterization coverage for ownership, duplicate IDs, response shape, inventory failures, score ordering, provider failures, Last.fm bonus, and regional MusicBrainz diagnostics.

**Inventory overlap assessment (PR #259):** both the recommendation adapter and `discovery_library_snapshot.py` page `getAlbumList2` in batches of 500 up to 50,000 records and deduplicate non-empty album IDs. They do not have interchangeable contracts. The snapshot first reads/writes a 10-minute cache, also loads artists, and normalizes album records to `album`/`song_count`/`coverArt`; `recommend_new_music()` intentionally reads a fresh raw inventory, indexes `name` and `artist`, and converts retrieval exceptions and safety-limit exhaustion into distinct JSON error payloads. Reusing `build_library_snapshot()` directly would change freshness, record shape, and failure behavior. PR #261 extracted `fetch_album_inventory()` as the shared **raw pagination helper**, with injected API/items, stable ID deduplication, and a typed limit error carrying the retrieved count. The snapshot adapter retains its cache and normalization; the recommendation adapter retains fresh raw records and its JSON error shapes.

Required sequence:
1. Characterization now covers inventory ownership, duplicate IDs, response shape, inventory failure/limit behavior, score-based output ordering, early ListenBrainz failure/empty-result behavior, the Last.fm bonus, and regional MusicBrainz HTTP failure. PR #261 adds direct tests for the shared raw inventory helper.
2. **Completed by PR #261:** share raw pagination without reusing `build_library_snapshot()` directly; keep the snapshot's 10-minute cache/normalized schema and the recommendation adapter's fresh raw inventory/error payloads distinct.
3. **Completed by PRs #263/#264:** provider calls are behind `RecommendationProviders`; PR #264 restored the regional counters and raw library inventory in the provider mapping and compatibility adapter, preserving the public response contract.
4. **Completed by PR #265:** the measurable size ratchet is enforced. Current `main` measures `navidrome_server.py` at 2,768 lines, `recommend_new_music()` at 568 AST lines against its temporary 575-line exception, and `_discovery_acquire_album_impl()` at 278 lines against the 280-line default limit.
5. **Completed by PR #278:** selection and diagnostic projection now share `discovery_recommendations.classify_recommendation_category()`. Direct-import tests pin unclassified handling, regional artist overrides, adventurous-tag precedence, cross-genre, adjacent, and fallback adventurous. PR #278 also asserts that the selected recommendation category agrees with diagnostic projection.
6. **Completed by PR #280:** the bounded Last.fm score/profile adjustment loop now lives in `discovery_recommendations.apply_lastfm_popularity_bonus()`. Direct tests pin top-40 score-order lookup, missing-stat behavior, tag-driven recent-family recomputation, the capped 1.12 multiplier, and the checked count. The adapter still owns `lastfm_api_configured`, `LASTFM_LAST_ERROR`, provider/cache implementation, and response shaping.
7. **Current extraction in PR review:** move the familiarity multiplier thresholds and exploration-family boost into `discovery_recommendations.apply_familiarity_exploration_bonus()`. Preserve all threshold boundaries (0, 1–2, 3–5, 6–10, >10), 1.10 exploration boost only on family overlap, and score multiplication order. The adapter continues to own recent-artist lookup and genre-cache access.

Acceptance: fixed-provider characterization remains green; the shared raw inventory contract remains distinct from the cached snapshot; category policy has direct-import tests; both selection and diagnostics use the same production helper; route/MCP response fields, category ordering, ownership checks, scoring, and failure behavior remain unchanged.

### 0a. Measurable size ratchet

PR #265 added `scripts/check_server_size.py`: a 3,031-line server ceiling, a 280-line general top-level-function ceiling, and a temporary named 575-line exception for `recommend_new_music()`. On current main after PR #280, the server is 2,616 lines. The guard uses AST `end_lineno` measurements, reports offending function names and sizes, and prints the ten largest functions in CI. The exception includes a rationale and follow-up plan; lower it as the recommendation adapter is decomposed.

**Implemented and merged by PR #265.** The CI guard in `scripts/check_server_size.py` enforces a 3,031-line file ceiling, a 280-line default top-level-function ceiling, and a temporary named 575-line exception for `recommend_new_music()`. On current main after PR #280, AST sizes are 416 lines for `recommend_new_music()` and 278 for `_discovery_acquire_album_impl()`. Tests prove accepted and rejected boundaries, including exception diagnostics. Update ceilings only through a reviewed change with a rationale; never raise them just to accommodate unrelated growth. As `recommend_new_music()` is decomposed, tighten its exception rather than normalizing its current size as acceptable architecture.

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

This audit did not change application code. The acquisition coordinator audit is now complete; no discrete policy boundary justified extracting it. The next active task is to migrate the remaining AST-coupled import-safety test only after mapping the production owner and preserving its destination validation and persistence-failure guard.


These are audit targets, not permission to refactor without inspecting current main. Reconfirm each target against current callers, tests, and open PRs before implementation.

### 1. Application assembly and test coupling — map generated; lifecycle AST migration remains

The dependency map was generated in CI and reviewed from artifact `12068042162` on initial PR head `1f9e6313310c691e9d9844d22136182e51ca6fee`: 159 local Python modules, 71 modules in the static `app.main` closure, and one direct `app/` import edge to `navidrome_server` (`app/api/dependencies.py`). The edge is inside lazy `get_librarian()` and does not imply eager import-time initialization; the app-import isolation regression covers that distinction. The workflow retains the full JSON as a 14-day `modularization-dependency-map` artifact. Static imports still do not capture runtime dependency injection.

Complete these gates in order; do not jump straight to another extraction:
1. Generate and review the import map for `app/main.py`, all `app/api/*.py`, and `navidrome_server.py`.
2. AST/source-reading inventory is recorded in `docs/architecture/AST_TEST_INVENTORY.md`. PR #249 migrated transfer lookup tests and PR #250 decoupled pure helper tests. `tests/test_acquisition_safety.py` now calls the extracted request coordinator directly for duplicate-request concurrency, persisted-job recovery, and dismissed-job reactivation. The import-status persistence guard now has direct-import coverage in PR #270; its AST adapter test remains to preserve lock/dismissal compatibility. Broader-query fallback has been moved to direct-import tests of `slskd_search.search_queries()`, `slskd_search_polling.collect_search_responses()`, and `acquisition_search_diagnostics.no_match_message()`. The regression pins generated query order, the 15,000/6,000 ms timeouts, zero/one collected responses, and ordered query diagnostics. The AST harness no longer compiles `_discovery_acquire_album_impl()`; candidate eligibility and queue/lifecycle safety remain separately covered. The remaining AST harness is retained for acquisition lifecycle/import adapter behavior until those real owners can be tested directly.
3. **Completed by PR #254:** `scripts/check_app_legacy_imports.py` enforces the app-to-legacy-server boundary in CI. The only allowlisted direct import is `app/api/dependencies.py:get_librarian`, the existing lazy compatibility adapter. Regression tests reject module-level imports, imports from other functions/paths, `from` imports, and submodule imports. All four required workflows passed on final PR head `908783f0a46618c53e4f3e4c4dcf298ec33850fc`; merged as `8bfd6a57179aec46a672343745b494dff60fec02`.
4. **Completed:** shared raw inventory helper (PR #261), provider/candidate-gathering extraction (PR #263), response-contract regression fix (PR #264), and `MUSIC_DIR` read/write audit (PR #267). No separate settings wrapper is justified while operational adapters intentionally snapshot the current path at invocation time.
5. **Completed:** audit `_discovery_acquire_album_impl()`; retain it as orchestration because no discrete policy seam justified extraction. PR #270's import-completion extraction is complete. PR #272 moves the broader-query fallback regression to direct-import query-generation, polling, and diagnostics tests; retain the remaining lifecycle/import AST cases. PR #272 was squash-merged as `9b97f447adc602a3be3b5ac496633430f3eb3cb4`; all four required workflows passed on exact final PR head `7b1257e0ceb9368063de025a2758f48a344efbcb`. The final AST coupling migration merged as `cae95e74c9910c512392de80b337eb4b21de67a5`; all four required workflows passed on exact final PR head `ad6864ea1f5f70b7f9d8b852bbc4bb02e7c2d395`.
6. **Completed audits:** the app-to-legacy import boundary guard is merged in PR #254; the `MUSIC_DIR` read/write audit is complete with no new settings object justified; the final AST-coupled acquisition test migration is tracked in PR #274. Do not reopen these items unless current source or CI evidence reveals a regression.

Acceptance criteria:
- The committed dependency map corresponds to the exact source revision audited and is regenerated when relevant imports change.
- AST-coupled tests are listed by filename and purpose; behavior tests target production modules directly, with adapter tests retained where compatibility requires them.
- No domain/API imports of `navidrome_server.py` remain except explicitly documented compatibility adapters. The current graph has one direct edge: `app/api/dependencies.py` lazily imports the legacy service inside `get_librarian()`; this is a runtime service-adapter dependency, not an import-time app initialization. The boundary guard must allow only reviewed adapter locations, not only MCP shims.
- Preserve MCP compatibility; retirement requires a separate explicit decision and migration gate.

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

## History

Use the root `PROJECT_LOG.md` to retrieve completed extraction records by PR, module, or responsibility. Do not append completed work or CI run IDs here.