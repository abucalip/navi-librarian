# Development and Git workflow

Last updated: 2026-10-17 (agent session context search adopted)

## Authority and responsibilities

- **GitHub is the single source of truth** for code, commits, branches, PRs, documentation, and release history. Do not use a local checkout as the source for authoritative changes.
- **Front-end contribution boundaries:** Any agent working on front-end matters must read root `AGENTS.md`, `docs/FRONTEND_DESIGN_GUIDE.md`, and relevant project docs, and may edit only the permitted UI files listed in `AGENTS.md` (plus narrowly scoped UI tests/fixtures and `docs/UI_BACKLOG_EXECUTION.md`). Do not edit protected backend/API/security, architecture, workflow, dependency, packaging, or release files without explicit approval and coordinated ownership. Shared integration, backend/domain/security changes, release controls, and final cross-layer verification require coordinated review.
- All authoritative changes go through focused GitHub branches and PRs. Local environments are for testing identifiable GitHub revisions only.
- Production is separate from GitHub state: merge, CI, image publication, deployment, and runtime verification are distinct states.

## Efficient session start and documentation retrieval

Start every task by checking current GitHub `main`, recent commits, open PRs, and relevant CI. Establish one concrete objective and acceptance criteria.

**Use the session search tool as the standard retrieval workflow** after checking repository state and reading the project snapshot. See `docs/SESSION_CONTEXT_SEARCH.md`.

1. Read `docs/PROJECT_STATUS.md` for current state and the next action.
2. Run `python scripts/session_search.py "<task-specific concepts>"` from the repository root to retrieve relevant documentation and code snippets. Use `--scope docs` or `--scope code` to narrow results; use `--any` if an all-terms search is too restrictive.
3. Read all of `docs/MODULARIZATION_ROADMAP.md` when choosing extraction work.
4. Consult `docs/REQUIREMENTS.md` for requirements affected by the change.
5. Consult `docs/TEST_PLAN.md` for mandatory gates and tests relevant to the change.
6. Read the applicable architecture/decision docs and inspect actual implementation, callers, tests, configuration, and package/Docker inclusion. Use search hits as navigation, not as proof that all references have been found.
7. Search the root `PROJECT_LOG.md` for the relevant module, PR, regression, or decision. Do not read the full chronological log unless the task requires it.
8. For large legacy responsibilities, inspect actual current line ranges, every production caller, tests that mock the function, and nearby extracted modules before selecting a seam. Specifically check inventory overlap before duplicating library snapshot behavior.
9. Read this workflow in full when changing the workflow itself; otherwise consult the applicable section.

If a document is stale or contradicts current code or GitHub evidence, verify the discrepancy and update the canonical document. Never use search or a shorter reading path to skip code inspection, tests, safety checks, or CI.

## Normal change cycle

1. Inspect current repository state and relevant documentation/code/tests.
2. Define a narrow objective, acceptance criteria, and risk/dependency notes.
3. Branch from current GitHub `main`, unless another GitHub base is explicitly justified.
4. Implement the smallest reviewable change and add regression tests. Preserve existing behavior, response shapes, side effects, persistence, and compatibility interfaces unless an approved requirement says otherwise.
5. Run focused tests, the full unit suite, syntax checks, and applicable API/Docker checks where execution is available. Report unavailable/skipped tests honestly.
6. Review the complete diff, changed-file list, call sites, package inclusion, unsafe failure cases, secrets, and unintended changes.
7. Open or update a focused PR. Verify required CI against the exact final PR-head SHA after the last code or documentation commit.
8. Merge only when acceptance criteria, diff review, and required gates pass. After merge, refresh `main`, PRs, and CI before beginning dependent work.
9. Record the exact branch/PR/SHA, tests and CI, limitations, merge state, and next action in the project docs.
10. For releases, separately verify publication, image tag/digest, Compose configuration, persistent storage, logs, connectivity, and application behavior. Preserve rollback references and obtain authorization for consequential production actions.

## Extraction selection

- A session may complete two or three small extractions, but there is no quota. Default to one independently reviewable extraction per PR. Independent audit gates may run in parallel as separate PRs when their changed files and prerequisites do not overlap; verify the dependency graph first, and refresh main between dependent merges.
- Trace the proposed seam through implementation, callers, tests, configuration, packaging, and compatibility interfaces before editing.
- Prefer pure or explicitly dependency-injected policy with direct-import tests and a narrow adapter. Do not extract a whole builder or create a broad callback surface just to reduce file size.
- Stop when the boundary is unclear, tests fail, higher-priority correctness/security/verification work exists, or the extraction adds more complexity than it removes.
- Treat acquisition/import/deletion and shared-state/locking changes as high risk; isolate them and test safe success and unsafe refusal.
- MCP has been retired as a supported interface. Do not reintroduce MCP runtime, registration, or startup paths; preserve the supported web interface and shared service logic.
- Do not perform size-only slskd refactors. The modularization completion audit is a gated sequence: generate/review `scripts/dep_map.py` output; inventory and decouple AST/source-reading tests; add and enforce the app-to-legacy-server import boundary; audit mutable `MUSIC_DIR` and settings wrappers; then evaluate the acquisition coordinator. Do not skip ahead to extraction.
- The active roadmap now includes characterization and a provider-injected candidate-gathering seam for `recommend_new_music()`. Characterize behavior before extraction and inspect `discovery_library_snapshot.py` for overlap first.
- The MCP registry, SDK dependency, and standalone MCP transport have been removed. Do not restore MCP runtime or registration without a new explicit owner decision and security review.
- Add a measurable CI size ratchet for `navidrome_server.py` and recorded top-level-function limits. Verify the line-count baseline against the exact main SHA, report offending names/sizes, and permit only explicit temporary exceptions with a removal plan.

## Required verification gates

The Python syntax workflow also runs `scripts/check_server_size.py`; its thresholds and named temporary exception are reviewed architecture controls. The server ceiling is 2,650 lines; new domain logic belongs in a module with direct-import tests, not in `navidrome_server.py`. Size-only changes are not an extraction goal, and the exception must be reduced as the recommendation adapter is decomposed.

For each code PR, follow `docs/TEST_PLAN.md`. At minimum:
- focused regression tests and `python -m unittest discover -s tests -v`;
- Python syntax checks and applicable API/Docker/package checks;
- direct-import tests for extracted logic and adapter/compatibility tests for the old interface;
- full diff and changed-file review;
- all four required workflows on the exact final PR-head SHA: Python syntax/acquisition safety, Docker packaging/full unit suite/build, isolated container runtime smoke, and validation-only multi-architecture image validation.

The multi-architecture workflow must remain non-publishing (`push: false`). A successful import, build, startup, or workflow definition alone is not proof of correctness. Never claim a test passed unless it ran.

UI changes require the full manual browser checklist after automated CI succeeds, against the exact tested SHA; record the result. Non-UI changes require relevant automated/API/integration checks, not invented UI evidence.

## Documentation ownership and closeout

Keep one canonical home for each kind of information:
- roadmap: outstanding extraction work and exit criteria;
- project status: current snapshot, blockers, and one next action;
- root `PROJECT_LOG.md`: completed work and durable evidence;
- requirements: user-visible behavior and invariants;
- test plan: verification requirements;
- architecture/decision docs: current boundaries and rationale.

When an extraction is completed, remove it from the active roadmap and record it in `PROJECT_LOG.md`. Do not duplicate full PR/CI narratives across the roadmap and status. Update architecture docs only when the actual boundary or decision changes. Keep the status concise; search historical records as needed.

At meaningful session closeout, update `docs/PROJECT_STATUS.md` and root `PROJECT_LOG.md`, plus only the relevant roadmap, requirements, test, workflow, architecture, or deployment documents. Record facts only: branch, PR, exact SHA, tests actually run, CI evidence, UI results when applicable, merge/publication/deployment/runtime state, limitations, and the single most useful next action. For audit-driven work, also record the exact measured line/function sizes and whether the thresholds were verified against the audited SHA.

## Release and production safety

- Publishing remains paused until modularization is complete and publishing is explicitly authorized.
- A merge is not publication; publication is not deployment; deployment is not runtime verification.
- Preserve configuration, persistent data, and a rollback reference. Do not weaken safety checks or delete production data to make tests pass.
- Obtain appropriate authorization before consequential production actions.