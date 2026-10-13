# Development and Git workflow

Last updated: 2026-10-12

## Authority and responsibilities

- **GitHub is the single source of truth** for project code, commits, branches, pull requests, documentation, and release history.
- **The assistant is the only code editor and committer** for this project. The assistant makes changes in GitHub feature/fix branches, commits them, runs available automated checks, reviews the diff, and opens or updates pull requests.
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
