# Modularization roadmap

Last reviewed: 2026-10-16 (PR #270 exact-head CI passed; awaiting merge)
Audit base: GitHub `main` at commit `5a05ca4a389673896f8263758aacecaad79f28b0`

## Purpose

This file is the **active plan**, not an extraction diary. It lists only work that remains useful after checking the current implementation. Completed extraction details and verification evidence belong in the root `PROJECT_LOG.md`; current session state belongs in `docs/PROJECT_STATUS.md`.

Do not add a roadmap entry merely because a function or file is large. Extract only a cohesive responsibility with a clear owner, meaningful direct-import tests, and a compatibility boundary that is simpler than the current design.

## Current priorities

### 0. Characterize and extract the new-music candidate-gathering pipeline

The audit identifies `recommend_new_music()` in `navidrome_server.py` (approximately lines 282–1340; about 1,058 lines in the audited revision) as a major live responsibility used by the `/discovery` route and an MCP tool. Its tail already composes `discovery_personal_allocator`, `discovery_allocation_contract`, and `discovery_recommendation_payload`; the front half still combines ListenBrainz fetches, regional MusicBrainz queries, library inventory paging, family scoring, and Last.fm bonuses. Existing tests mocked the whole function, leaving internal policy without a characterization baseline. PR #255 established inventory ownership, duplicate-ID, response-shape, and inventory-failure cases; PR #257 added score-based ordering and ListenBrainz failure/empty-result behavior; PR #259 pins the Last.fm popularity bonus and regional MusicBrainz HTTP-failure diagnostics. Reconfirm all line references and call paths against current `main` before implementation.

**Inventory overlap assessment (PR #259):** both the recommendation adapter and `discovery_library_snapshot.py` page `getAlbumList2` in batches of 500 up to 50,000 records and deduplicate non-empty album IDs. They do not have interchangeable contracts. The snapshot first reads/writes a 10-minute cache, also loads artists, and normalizes album records to `album`/`song_count`/`coverArt`; `recommend_new_music()` intentionally reads a fresh raw inventory, indexes `name` and `artist`, and converts retrieval exceptions and safety-limit exhaustion into distinct JSON error payloads. Reusing `build_library_snapshot()` directly would change freshness, record shape, and failure behavior. PR #261 extracted `fetch_album_inventory()` as the shared **raw pagination helper**, with injected API/items, stable ID deduplication, and a typed limit error carrying the retrieved count. The snapshot adapter retains its cache and normalization; the recommendation adapter retains fresh raw records and its JSON error shapes.

Required sequence:
1. Characterization now covers inventory ownership, duplicate IDs, response shape, inventory failure/limit behavior, score-based output ordering, early ListenBrainz failure/empty-result behavior, the Last.fm bonus, and regional MusicBrainz HTTP failure. PR #261 adds direct tests for the shared raw inventory helper.
2. **Completed by PR #261:** share raw pagination without reusing `build_library_snapshot()` directly; keep the snapshot's 10-minute cache/normalized schema and the recommendation adapter's fresh raw inventory/error payloads distinct.
3. **Implemented by PR #263; verification regression found:** the provider module omitted `regional_candidates_added` and `regional_results_seen` from its returned mapping, breaking the downstream public response contract. PR #264 returns the regional counters and raw library inventory from the provider mapping, unpacks them in the compatibility adapter, and asserts the response diagnostics in characterization coverage; do not proceed until its exact final PR-head CI passes.
4. After the response-contract fix is verified, continue to the measurable size ratchet below, using measurements from the exact current main revision rather than the older audit estimate.

Acceptance: fixed-provider characterization coverage exists before extraction; inventory overlap is explicitly resolved; candidate gathering is independently testable; route and MCP compatibility remain intact.

### 0a. Measurable size ratchet

The older audit estimate (3,514 lines / roughly 1,058 lines for `recommend_new_music()`) is stale after extraction. PR #265 measures the current source at 3,031 lines and adds `scripts/check_server_size.py`: a 3,031-line server ceiling, a 280-line general top-level-function ceiling, and a temporary named 575-line exception for `recommend_new_music()`. The guard uses AST `end_lineno` measurements, reports offending function names and sizes, and prints the ten largest functions in CI. The exception includes a rationale and follow-up plan; lower it as the recommendation adapter is decomposed.

**Implemented and merged by PR #265.** The CI guard in `scripts/check_server_size.py` enforces a 3,031-line file ceiling, a 280-line default top-level-function ceiling, and a temporary named 575-line exception for `recommend_new_music()`. On the verified source, AST sizes are 568 lines for `recommend_new_music()` and 278 for `_discovery_acquire_album_impl()`. Tests prove accepted and rejected boundaries, including exception diagnostics. Update ceilings only through a reviewed change with a rationale; never raise them just to accommodate unrelated growth. As `recommend_new_music()` is decomposed, tighten its exception rather than normalizing its current size as acceptable architecture.

### 0b. Operational MCP functions — owner decision required

`restart_server` and `apply_server_patch` are MCP-exposed operational capabilities. The audit reports no references to either name in `tests/`; `apply_server_patch` rewrites the server's own source, while `restart_server` launches a helper that kills the process and relaunches it on hardcoded port 8000.

**Do not refactor, broaden, or silently remove these capabilities before the product owner decides what authorizes them and whether they should remain exposed.** This is a product/security decision, not an agent-level modularization choice. Ask the owner to decide:
- which authenticated/authorized caller may invoke each operation and under what deployment conditions;
- whether source rewriting and process-killing/relaunch behavior are still required;
- whether either MCP tool should be disabled or retired.

After that decision, if retained, move them to a dedicated operations module with explicit authorization checks and safety tests: unique-match rejection, no-op on mismatch, and occupied-port/restart failure handling. Do not execute either operation against a live service as part of tests.

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
2. AST/source-reading inventory is recorded in `docs/architecture/AST_TEST_INVENTORY.md`. PR #249 migrated transfer lookup tests and PR #250 decoupled pure helper tests. `tests/test_acquisition_safety.py` now calls the extracted request coordinator directly for duplicate-request concurrency, persisted-job recovery, and dismissed-job reactivation. The import-status persistence guard now has direct-import coverage in PR #270; its AST adapter test remains to preserve lock/dismissal compatibility. Broader-search orchestration remains source-executed until a production boundary can preserve real search/retry behavior.
3. **Completed by PR #254:** `scripts/check_app_legacy_imports.py` enforces the app-to-legacy-server boundary in CI. The only allowlisted direct import is `app/api/dependencies.py:get_librarian`, the existing lazy compatibility adapter. Regression tests reject module-level imports, imports from other functions/paths, `from` imports, and submodule imports. All four required workflows passed on final PR head `908783f0a46618c53e4f3e4c4dcf298ec33850fc`; merged as `8bfd6a57179aec46a672343745b494dff60fec02`.
4. **Completed:** shared raw inventory helper (PR #261), provider/candidate-gathering extraction (PR #263), response-contract regression fix (PR #264), and `MUSIC_DIR` read/write audit (PR #267). No separate settings wrapper is justified while operational adapters intentionally snapshot the current path at invocation time.
5. **Completed:** audit `_discovery_acquire_album_impl()`; retain it as orchestration because no discrete policy seam justified extraction. PR #270's import-completion extraction is the active change. After merge, re-evaluate the remaining broader-query fallback AST-coupled test only when real search/retry behavior can be tested through a suitable production boundary.
6. In parallel only where file/dependency overlap is absent, run separate PRs for the AST-test migration, app-import boundary guard, and settings-wrapper audit. Each PR must still branch from a suitable current base, pass exact-head CI, and refresh main before dependent work.

Acceptance criteria:
- The committed dependency map corresponds to the exact source revision audited and is regenerated when relevant imports change.
- AST-coupled tests are listed by filename and purpose; behavior tests target production modules directly, with adapter tests retained where compatibility requires them.
- No domain/API imports of `navidrome_server.py` remain except explicitly documented compatibility adapters. The current graph has one direct edge: `app/api/dependencies.py` lazily imports the legacy service inside `get_librarian()`; this is a runtime service-adapter dependency, not an import-time app initialization. The boundary guard must allow only reviewed adapter locations, not only MCP shims.
- Preserve MCP compatibility; retirement requires a separate explicit decision and migration gate.

### 2. Acquisition coordinator — audited; retain orchestration

Audit against GitHub `main` at `cd5d0240c1ac696417727de938736a1b15f7582b` (2026-10-16), with `_discovery_acquire_album_impl()` at lines 2341–2618 (278 lines by AST size, consistent with the CI size report). The function validates input and settings, calls `slskd_search_polling.collect_search_responses()`, delegates candidate extraction to `_slskd_extract_candidates()`, and delegates queue-error classification to `acquisition_lifecycle.queue_failure_action()`. It then coordinates the existing queue-unless-dismissed adapter, start-state probe, cleanup guard, watcher startup, and public response/status updates.

The remaining inline decisions are tightly coupled to that sequence: only the first ten clear candidates are attempted; a rejected queue source can fall through to the next peer, a fatal authorization/configuration response terminates, and uncertain queue/start outcomes are monitored rather than blindly retried. A definitively stopped source is cleaned before trying another peer, and cleanup refusal terminates fallback. These are consequential state transitions, but the function does not expose a cohesive independent policy API that can be moved without reproducing the orchestration or widening the dependency surface. The existing extracted modules already own the independently testable search, candidate, queue-error, source-switch, cleanup, and watcher responsibilities.

**Decision: retain `_discovery_acquire_album_impl()` as orchestration.** No application code changed. Do not extract it for size alone. Revisit only if a focused characterization effort identifies a smaller policy function with independent callers and direct-import tests. The next useful task is the remaining AST-coupled import-safety test in `tests/test_acquisition_safety.py`, preserving filesystem and persistence guards.

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