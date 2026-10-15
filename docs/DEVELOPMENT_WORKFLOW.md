# Development and Git workflow

Last updated: 2026-10-15

## Authority and responsibilities

- **GitHub is the single source of truth** for project code, commits, branches, pull requests, documentation, and release history.
- **Work is split by ownership boundary.** ZCode owns front-end implementation only, within the permitted UI paths defined in root `AGENTS.md`; every front-end agent must read `AGENTS.md` and `docs/FRONTEND_DESIGN_GUIDE.md` plus relevant project docs before starting. The design guide is the canonical agent-independent source for visual principles and the UI backlog. The assistant owns backend/domain/security changes, shared integration, release controls, and final cross-layer verification. Either agent's code changes must be made on a focused GitHub branch and proposed through a PR; neither should bypass the repository's review, testing, or merge gates.
- **GitHub remains authoritative regardless of agent.** The assistant coordinates integration and project-level verification. ZCode must not independently change backend behavior, merge PRs, publish images, deploy, or alter project-wide safety/release controls. Local-only edits or commits are not authoritative.
- **The user's local checkout is a testing environment only.** The user may fetch/check out a GitHub branch or commit locally and run the app/tests to verify behavior. Local-only edits or commits are not authoritative and must not be treated as changes to merge back into GitHub.
- **Production is a separate state.** A GitHub merge or passing CI does not mean the Docker image is published, deployed, or verified on the server.

## Normal change cycle

1. At session start, inspect GitHub `main`, open PRs, recent commits, CI, and relevant project docs/code/tests.
2. Define a narrow objective and acceptance criteria.
3. Create a focused branch from the current GitHub `main` (or another explicitly justified GitHub base). Do not use a divergent local branch as the base for authoritative changes.
4. Implement the change and regression tests. Keep the diff focused; preserve unrelated behavior and user data.
5. Run relevant tests and syntax/package checks available to the assistant. Inspect the final diff and verify CI for the exact commit.
6. Open or update a GitHub PR. State clearly what is implemented, what is tested, and what remains uncertain. Do not describe diagnostic instrumentation as a confirmed fix until evidence establishes the root cause and behavior.
7. Merge only through the agreed GitHub workflow; merging is distinct from deployment.
8. Give the user the exact branch/PR/commit and concise local testing instructions.
9. Use the user's local test results as evidence about behavior, not as a source of code. If a test finds a problem, the assistant makes the fix on GitHub, commits it, and provides the new revision to test.
10. For releases, separately verify image publication, deployment configuration, running image tag/digest, logs, and application behavior.


## Multi-extraction sessions (standard workflow)

A session may deliver **two or three small extractions**, but the session is a planning/coordination unit—not a reason to combine unrelated changes into one PR. Default to **one independently reviewable extraction per PR**. Use one PR for multiple extractions only when they share a boundary or cannot be validated independently, and explain that coupling in the PR description.

### Session start and selection

1. Re-check current GitHub `main`, recent commits, open PRs, and required CI; read this workflow, `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/TEST_PLAN.md`, and the relevant architecture/decision/roadmap documents.
2. Trace each proposed seam through its implementation, callers, tests, configuration/package files, and compatibility interfaces. Pick one concrete acceptance criterion per extraction and identify risks/dependencies before coding.
3. Select up to three **small, low-coupling** candidates. Do not set a quota: stop at one if a safety issue, failing gate, unclear ownership boundary, or unexpected dependency appears. Acquisition/import/deletion and shared-state/locking changes need stricter isolation and must not be bundled with unrelated refactors.
4. Order dependent extractions explicitly. Branch each PR from the current GitHub `main`; never use the local checkout as an authoritative base. Prefer sequential implementation/merge. Parallel work is appropriate for independent audits or reviews, not for concurrently editing the same files or assuming multiple PRs remain mergeable.

### Per-extraction verification gates

For **each PR separately**:

1. Add direct-import tests for the extracted owner and adapter/compatibility tests for the old public interface. Preserve existing semantics, response shapes, side effects, persistence, and MCP compatibility unless a separately reviewed requirement authorizes a change.
2. Run focused regressions, the full `python -m unittest discover -s tests -v` suite, Python syntax checks, and applicable API/Docker checks where execution is available. Report skipped/unavailable tests explicitly; never infer a pass from a successful import, build, or startup.
3. Review the entire diff, changed-file list, call sites, Docker/package inclusion, unsafe-path and failure behavior where relevant, and any unintended changes. Check for secrets and unrelated modifications.
4. After the **last code or documentation commit**, verify all four required workflows on that exact final PR-head SHA: Python syntax/acquisition-safety regressions; Docker packaging plus full unit suite/image build; isolated container runtime smoke; validation-only multi-architecture image validation. The multi-architecture workflow must remain non-publishing (`push: false`); do not publish or deploy as part of modularization.
5. For UI-facing changes, after automated gates pass, run the full manual browser checklist against the exact tested SHA and record evidence. For non-UI changes, run the relevant automated/API/integration checks; do not claim manual UI verification that was not performed.
6. Merge only when acceptance criteria, final diff review, and required exact-head gates are satisfied. After each merge, refresh `main`, open PRs, and CI before starting or retargeting the next dependent PR. If a branch's base changes, re-verify the new exact final head before merge.

### Session closeout

- Record each extraction separately with branch, PR, exact tested head SHA, test commands actually run, all four workflow results, merge SHA/state, and any skipped checks.
- Keep **implemented, tested, CI passed, merged, published, deployed, and runtime verified** as distinct states. Do not claim deployment or production behavior from CI.
- Update `docs/PROJECT_STATUS.md`, `PROJECT_LOG.md`, and relevant roadmap/test/architecture documents with verified evidence and remaining risks. Identify one next action, not a speculative queue of work.
- A session is successful when every merged PR met its own gates—not when a target number of extractions was reached. If any gate fails, fix or stop at that PR and report the remaining work before continuing.

## Local testing without reconciling local code into GitHub

Do not merge local `main` into a GitHub PR branch merely to make the local histories line up. A local branch may contain testing-only merges or commits absent from GitHub `main`.

Prefer a separate worktree or disposable local branch based on the exact GitHub PR head. This allows testing the PR as proposed without disturbing the user's existing checkout. If testing specifically requires combining a PR with a local-only baseline, treat that as a temporary test experiment only: do not push it, do not treat its merge commit as authoritative, and report that the tested tree differs from the PR.

Before any local Git operation, inspect status and existing worktrees. Never reset, clean, force-push, overwrite uncommitted work, or delete a branch/worktree without explicit authorization.

## Reporting requirements

For each meaningful handoff, report:
- GitHub PR/branch and exact commit SHA;
- CI and test results actually observed;
- whether the change is implemented, tested, merged, published, deployed, and/or verified;
- what the user should test locally and how to obtain the exact revision;
- unresolved questions and the next concrete action.

Project status and durable decisions belong in `docs/PROJECT_STATUS.md`, `docs/DECISIONS.md`, and this file. Never record credentials or other secrets.


## Container and release verification

- Verify runtime behavior, not only image compilation: run the isolated container smoke test on the exact PR head and retain checks for readiness, authentication/setup boundaries, auth-key permissions, and persistence across restart.
- The Docker workflow is validation-only while modularization is underway: run smoke before the multi-architecture build, use push: false, and do not add registry login, tags, or publication without separate authorization after the roadmap is complete.


## Manual UI and test-kit gates

- Run the full manual browser checklist for UI-facing changes only after required automated checks pass on the exact tested SHA. The outstanding performance observation and distinct error/recovery exercise are scheduled for the next UI-facing change. Non-UI PRs still require relevant automated/API/integration tests; do not rerun the full visual checklist solely due to a SHA change.
- Use the documented local helper with sandbox music/download paths and slskd disabled for ordinary checks. Keep application data isolated by PR; verify separately before claiming that it persists across different source SHAs. A server-restart persistence observation does not prove cross-SHA helper reuse.


## Front-end design reference and acceptance

Before any UI task, consult [`FRONTEND_DESIGN_GUIDE.md`](FRONTEND_DESIGN_GUIDE.md) for the established visual identity, anti-patterns, Impeccable workflow, accessibility/responsive expectations, ownership boundaries, PR checklist, and prioritized backlog. Keep the guide current through reviewable documentation PRs; do not treat historical PR comments as the canonical specification. For UI changes, report the backlog item addressed, design-tool recommendations applied/rejected, exact tested SHA, screenshots where visual, and any skipped checks.

## Frontend assets and authentication boundary

When extracting templates/styles/scripts, serve only the dedicated static directory under `/static/` and retain authentication for application pages and APIs. Public static access should be explicitly scoped to `/static/*` and the existing bundled `/assets/cassette.png` endpoint. Add integration tests for asset loading before setup/login and protected-route behavior. UI-facing asset delivery changes require exact-head CI followed by the full manual browser checklist, including the outstanding performance and error/recovery checks.


## Settings router injection acceptance (2026-10-15)

- The settings router must use `Depends(get_librarian)` and be importable without a direct import of `navidrome_server.py`.
- Keep all twelve endpoint path/method pairs and existing service calls, request mapping, default quality priorities, optional-path trimming, 400 validation errors, and sanitized 502 errors unchanged.
- Unit tests must exercise the router with injected fakes and verify dependency wiring. Require exact-final-head results for all four CI workflows before merge. Do not claim local tests, publication, deployment, or runtime verification unless performed.

