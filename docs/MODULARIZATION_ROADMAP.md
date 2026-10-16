# Modularization roadmap

Last reviewed: 2026-10-16  
Baseline: GitHub `main` at `b0c63b267c834516b419d7e8183d007d2dbb2f5b`

## Purpose

This file is the **active plan**, not an extraction diary. It lists only work that remains useful after checking the current implementation. Completed extraction details and verification evidence belong in the root `PROJECT_LOG.md`; current session state belongs in `docs/PROJECT_STATUS.md`.

Do not add a roadmap entry merely because a function or file is large. Extract only a cohesive responsibility with a clear owner, meaningful direct-import tests, and a compatibility boundary that is simpler than the current design.

## Current priorities

These are audit targets, not permission to refactor without inspecting current `main`. Reconfirm each target against current callers, tests, and open PRs before implementation.

### 1. Discovery builder responsibilities — first to assess

Trace `_build_classics_list()`, its callers, and tests. Identify the smallest remaining independently testable policy stage, if one still exists after the already-merged classics extractions.

Acceptance criteria:
- Name one responsibility and its inputs/outputs before changing code.
- Keep provider/cache access, rate limiting, ranking, response shape, and persistence at their existing owners unless the selected seam explicitly requires otherwise.
- Add direct-import contract tests plus adapter/compatibility regressions.
- Stop if the boundary requires a broad callback surface or merely moves code without improving ownership.

### 2. Application assembly and test coupling — completion audit

Reconcile current `app/main.py` and API dependencies on `navidrome_server.py`, package configuration, compatibility adapters, and AST-coupled acquisition tests.

Acceptance criteria:
- Identify remaining runtime dependencies from actual imports/callers.
- Distinguish intentional compatibility seams from accidental coupling.
- Prefer a dependency map and targeted test improvements over another extraction when no cohesive behavior boundary exists.
- Do not retire MCP compatibility as part of routine modularization; that requires its own explicit decision and migration gate.

### 3. Acquisition coordinator — conditional, high risk

Audit `_discovery_acquire_album_impl()` only after the discovery and assembly audits. Extract only if a narrow, independently testable policy/coordination boundary is evident.

Preserve concurrency and lock behavior, conditional state transitions, persistence, queue uncertainty, recovery, dismissal/import exclusion, watcher startup, mount identity, rollback, no-overwrite behavior, cleanup refusal, and path safety. Add tests for both safe success and unsafe refusal. Do not bundle this work with unrelated refactors.

### 4. slskd integration — no size-only work

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