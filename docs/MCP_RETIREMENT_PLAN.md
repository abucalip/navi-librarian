# MCP Retirement Plan

Last updated: 2026-10-17
Status: **Removal implementation prepared in PR; verification and merge pending**

## Objective

Retire the remaining Model Context Protocol (MCP) server interface and its runtime-specific dependencies without removing or regressing Librarian's shared service logic or web application functionality.

This is a dedicated migration following completion of the modularization roadmap. GitHub `main` remains the source of truth. Do not treat this plan as authorization to deploy or publish an image.

## Current evidence and baseline

The current repository has not fully retired MCP:

- `mcp_registry.py` defines `TOOL_NAMES` and `create_mcp_server()`, registering 25 remaining tools.
- `navidrome_server.py` retains a standalone `if __name__ == "__main__"` path that imports the registry and starts a streamable HTTP MCP server on `127.0.0.1:8000`.
- `requirements.txt` still declares `mcp==2.3.0`.
- The web app uses the lazy adapter in `app/api/dependencies.py:get_librarian` to access shared service logic in `navidrome_server.py`. That adapter is not itself proof that the web app requires MCP.
- `Dockerfile` packages `mcp_registry.py` and the application dependencies. `compose.yaml` configures the web service on its own port and does not declare a separate MCP service.
- `tests/test_mcp_registry.py` tests the remaining registry and verifies that importing the legacy service does not load the MCP SDK.
- `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/TEST_PLAN.md`, and `docs/DEVELOPMENT_WORKFLOW.md` currently require preserving MCP compatibility unless a separate retirement decision authorizes its removal.
- Earlier work removed the high-risk `restart_server` and `apply_server_patch` tools. Do not restore them.

These are repository-source observations; they do not establish whether any external MCP client or live installation currently uses the interface. Verify consumers before removal.

## Consumer/reference audit (2026-10-17)

Audited the current GitHub `main` source and package/runtime configuration before editing:

| Reference | Finding | Disposition |
|---|---|---|
| `mcp_registry.py` | Registers 25 service functions; includes no longer supported restart/patch tools. | Delete registry. The underlying service functions remain available to the web layer. |
| `navidrome_server.py` standalone block | Only direct MCP transport startup; binds streamable HTTP to loopback port 8000 and starts the scheduler as a side effect. | Remove transport/startup block. Keep shared service and scheduler functions. |
| `requirements.txt` | `mcp==2.3.0` is the only declared MCP SDK dependency found in the inspected package manifest. | Remove dependency. |
| `Dockerfile` | Explicit COPY list includes `mcp_registry.py`; no separate MCP service exists in `compose.yaml`. | Remove registry from image contents. Web service remains on its configured port. |
| `tests/test_mcp_registry.py` | Tests registration behavior and the old 25-tool registry. | Replace with retirement regressions; keep existing API, recommendation, acquisition, and safety tests intact. |
| `app/api/dependencies.py` and `app/main.py` | Web routes lazily call shared `navidrome_server` functions; no need for MCP registration. The web entry point did not start the scheduler, while the removed standalone block did. | Keep lazy adapter; start the idempotent scheduler from web application startup. |
| Requirements, test plan, workflow docs, status, and project log | Some still described MCP as supported or required compatibility. | Update to the web-only supported interface and MCP-free verification contract. |

No repository-defined external MCP consumer or separate Compose MCP service was found in the inspected configuration. GitHub source inspection cannot establish whether an external client or existing user configuration still targets the former loopback endpoint; that remains unverified. The existing Compose deployment exposes the web port, not port 8000. The 25 registered function implementations were not deleted; they remain shared service functionality.

## Principles and constraints

1. Remove the MCP transport, registry, startup path, and unnecessary SDK dependency—not shared business logic used by the web application.
2. Keep the migration focused. Do not use it to reopen completed modularization or perform unrelated recommendation/acquisition refactors.
3. Preserve existing web routes, authentication, settings persistence, discovery/recommendation behavior, acquisition lifecycle, and recovery behavior.
4. Preserve acquisition/import/deletion safety checks and their regression coverage. Do not delete or weaken safety tests to make the migration pass.
5. Do not restore `restart_server` or `apply_server_patch`.
6. Do not publish or deploy as part of this migration. Publishing remains paused unless separately authorized.
7. Update the product requirements and architecture documentation to reflect the approved retirement. Replace MCP compatibility tests with tests for the intended MCP-free architecture rather than simply deleting coverage.
8. Report implementation, tests, CI, merge, publication, deployment, and runtime verification as separate states.

## Migration plan

### 1. Audit consumers and references

Before changing implementation, inspect current `main` and trace:

- All entries in `mcp_registry.py::TOOL_NAMES` and their underlying functions/callers.
- References to `mcp_registry`, the `mcp` package, MCP transports, port 8000, and MCP-specific startup/configuration across source, tests, scripts, docs, workflows, and deployment examples.
- Whether any external integrations, user configuration, or documented workflows rely on the MCP endpoint.
- Whether the discovery scheduler's startup and lifecycle are correctly handled by the web application or another intended entry point; do not accidentally remove required background behavior when removing the standalone MCP startup path.
- Docker/package inclusion and dependency use, confirming the SDK has no remaining legitimate consumers before removing it.

Record every discovered reference and its disposition in the PR description or project log. If a real consumer is found, clarify migration expectations before removing its interface.

### 2. Remove MCP-specific runtime code

Subject to the consumer audit:

- Remove `mcp_registry.py` and its registration API if no longer needed.
- Remove the MCP-only standalone startup code from `navidrome_server.py`, while preserving any necessary supported application/service entry point and scheduler behavior.
- Remove `mcp==2.3.0` from `requirements.txt` only after confirming no remaining code requires it.
- Remove MCP-only packaging references from `Dockerfile` and any other build/deployment configuration.
- Remove or update MCP-only docs, scripts, CI references, and examples.
- Do not change shared service behavior merely to eliminate the legacy filename; the web adapter and business logic are outside scope unless the audit identifies a direct MCP dependency.

### 3. Replace compatibility tests with retirement and regression tests

Add or adapt tests to verify:

- The web app can be imported and started without importing or initializing the MCP SDK/runtime.
- No supported application entry point starts an MCP listener.
- MCP registry/runtime code and dependency are absent from the intended application package/dependency set.
- The app's supported routes still expose required discovery, settings, connection-test, recommendation, and acquisition behavior.
- Authentication and persistent settings continue to work.
- Background refresh/scheduler behavior remains available through its intended lifecycle, if applicable.
- Acquisition, import, cleanup, and recovery safety tests still pass, including unsafe-path refusal and unrelated-file preservation.
- No tests retain accidental assumptions about MCP registration; preserve tests for shared behavior and public web/API contracts.

Use focused tests first, then the full suite. Do not claim live external-client compatibility or production behavior unless actually tested.

### 4. Update durable documentation

Update, as applicable:

- `docs/REQUIREMENTS.md`: replace the goal of preserving the MCP entry point with the approved supported-interface policy.
- `docs/TEST_PLAN.md`: remove the requirement to preserve MCP compatibility and specify the new MCP-free architecture checks.
- `docs/DEVELOPMENT_WORKFLOW.md`: replace the temporary MCP-retirement gate with the final decision and any remaining supported interfaces.
- `docs/PROJECT_STATUS.md`: record PR, exact SHA, actual tests/CI, merge state, and remaining next action.
- Root `PROJECT_LOG.md`: record the rationale, audited references, implementation, test evidence, and limitations.
- Any README, deployment guide, or architecture document that describes MCP as a supported interface.

Do not state the migration is complete until the final PR has been verified and merged.

### 5. Verification and review gates

Follow `docs/TEST_PLAN.md` and verify the final PR-head SHA:

1. Focused retirement regressions and affected API contract tests.
2. Full unit suite: `python -m unittest discover -s tests -v`.
3. Python syntax and acquisition-safety workflow.
4. Docker/package checks, including removal of unnecessary SDK/runtime dependency.
5. Isolated container runtime smoke test.
6. Validation-only multi-architecture image workflow, keeping `push: false`.
7. Full diff review covering imports, call sites, startup/lifecycle behavior, persistence, package inclusion, safety paths, docs, and unintended changes.

All four required GitHub Actions workflows must pass on the exact final PR-head SHA after the last code or documentation change. Report missing, skipped, cancelled, or mismatched-SHA checks explicitly. Do not treat compilation or a successful container start as proof that the migration is correct.

### 6. Merge and closeout

- Open a focused PR against current `main`.
- Review the complete diff and acceptance criteria.
- Merge only after the caller audit, required tests, and all four CI gates pass.
- Refresh GitHub state after merge and verify the merge commit.
- Update project status and root project log with exact evidence.
- Leave publishing and production deployment untouched unless separately authorized.

## Definition of done

MCP retirement is complete only when:

- The consumer/reference audit has no unresolved dependency that blocks removal.
- MCP runtime, registry, startup, and unused SDK/package references are removed.
- Shared web/service functionality and required background behavior remain operational.
- Retirement-specific tests and existing safety/regression tests pass.
- Product and development documentation accurately describe the new architecture.
- The final diff is reviewed and all four required workflows pass on the exact final PR-head SHA.
- The PR is merged and the merge SHA is recorded.
- Publication, deployment, and runtime verification are reported separately and are not claimed unless actually performed.

## Current next action

PR #296 is open. Complete focused tests and verify all four required workflows on the exact final PR-head SHA. Merge only after those gates pass. This document records a plan, not evidence that any retirement implementation or verification has occurred.
