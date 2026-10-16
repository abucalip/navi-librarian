# Modularization roadmap

Last reviewed: 2026-10-16 (AST test inventory completed; dependency map CI run pending)  
Baseline: GitHub `main` at `be01d3ebe41abc888de24b4e5bd01d54628bb0ff`

## Purpose

This file is the **active plan**, not an extraction diary. It lists only work that remains useful after checking the current implementation. Completed extraction details and verification evidence belong in the root `PROJECT_LOG.md`; current session state belongs in `docs/PROJECT_STATUS.md`.

Do not add a roadmap entry merely because a function or file is large. Extract only a cohesive responsibility with a clear owner, meaningful direct-import tests, and a compatibility boundary that is simpler than the current design.

## Current priorities

These are audit targets, not permission to refactor without inspecting current `main`. Reconfirm each target against current callers, tests, and open PRs before implementation.

### 1. Application assembly and test coupling — scripted audit in progress

Run `scripts/dep_map.py` in CI against this baseline and retain the JSON as the `modularization-dependency-map` artifact. Review the generated graph against actual callers, runtime wiring, package/Docker inclusion, and open PRs; static imports do not capture dynamic imports or dependency injection. The workflow change adds this repeatable audit artifact without changing application code.

Complete these gates in order; do not jump straight to another extraction:
1. Generate and review the import map for `app/main.py`, all `app/api/*.py`, and `navidrome_server.py`.
2. AST/source-reading inventory is recorded in `docs/architecture/AST_TEST_INVENTORY.md`: three tests parse/compile functions from `navidrome_server.py`. Migrate these incrementally to direct imports; preserve the acquisition-safety lifecycle, concurrency, persistence, and recovery cases.
3. Add the application-import boundary check to `docs/TEST_PLAN.md` and CI, allowing only explicitly documented MCP compatibility shims if those remain necessary.
4. Then evaluate the thin settings wrappers around `service_settings.py`; remove wrappers only after confirming and redirecting every API/MCP caller and preserving compatibility where required.
5. Audit `_discovery_acquire_album_impl()` using the binary policy-vs-orchestration question below.

Acceptance criteria:
- The committed dependency map corresponds to the exact source revision audited and is regenerated when relevant imports change.
- AST-coupled tests are listed by filename and purpose; behavior tests target production modules directly, with adapter tests retained where compatibility requires them.
- No domain API depends on `navidrome_server.py` except a documented, intentional compatibility seam; static graph and source grep are reviewed together.
- Preserve MCP compatibility; retirement requires a separate explicit decision and migration gate.

### 2. Acquisition coordinator — conditional, high risk

After the import-map and AST-test gates, answer one binary question: does `_discovery_acquire_album_impl()` contain policy (candidate selection, conditional source-switch thresholds, retry/state-transition rules) or only orchestration of already-extracted modules? If only orchestration, retain it. Extract only a demonstrated policy seam with direct-import tests.

Preserve concurrency and lock behavior, conditional state transitions, persistence, queue uncertainty, recovery, dismissal/import exclusion, watcher startup, mount identity, rollback, no-overwrite behavior, cleanup refusal, and path safety. Add tests for both safe success and unsafe refusal. Do not bundle this work with unrelated refactors.

### 3. slskd integration — no size-only work

Search polling, quality, transfer matching, progress, and connectivity responsibilities have already been extracted in prior work. Treat remaining code as adapter/wiring unless a concrete duplicated policy or independently testable orchestration responsibility is demonstrated.

## Definition of done

Modularization is complete when:
- cohesive domain responsibilities have clear owners and usable direct-import tests;
- remaining server code is primarily justified orchestration, provider access, dependency wiring, or compatibility adapters;
- imports and package/Docker inclusion are intentional;
- critical acquisition/import/deletion paths retain regression coverage for success and unsafe failure;
- application assembly and AST-based tests have been audited for accidental coupling;
- no higher-priority correctness, security, automated verification, or delivery gap is being bypassed;
- the remaining work would not make the architecture simpler or safer enough to justify its cost.

The number of extractions is not a goal or quota. A documented decision to retain a responsibility in an adapter is a valid outcome.

## Verification and release constraints

For each code PR, follow `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`: focused regressions, full unit suite, syntax/package/API checks where applicable, complete diff review, and all four required workflows on the exact final PR-head SHA. UI changes also require the documented manual browser checks.

Publishing remains paused until the roadmap is complete and publishing is explicitly authorized. CI/build success is not publication, deployment, or production runtime verification. Acquisition-dismissal HTTP 409 remains deferred unless it becomes reproducible or is explicitly re-prioritized.

## History

Use the root `PROJECT_LOG.md` to retrieve completed extraction records by PR, module, or responsibility. Do not append completed work or CI run IDs here.