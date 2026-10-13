# Development and Git workflow

Last updated: 2026-10-13

## Authority and responsibilities

- **GitHub is the only source of truth** for project code, commits, branches, pull requests, documentation, and release history.
- **Do not use the outdated Local_Git integration or checkout.** It is dismissed for this project and must not be queried for repository status, branches, diffs, edits, tests, or verification. Do not attempt to reconcile its state with GitHub.
- **The persistent local environment is for testing only.** The manual UI harness runs from `~/navi-librarian-test/test-pr.sh <PR-number>` and fetches the exact current GitHub PR head. Local-only edits/commits and testing merges are not authoritative and must never be pushed or merged as project changes.
- The assistant makes authoritative changes through GitHub feature/fix branches and pull requests, then records what was actually tested.
- **Production is separate.** A merge or passing CI does not mean an image is published, deployed, or verified on the server.

## Manual UI smoke-test gate

For UI-facing changes and release candidates, run the local PR tester after exact-head CI is green:

```sh
~/navi-librarian-test/test-pr.sh <PR-number>
```

- The helper reads the current PR head SHA from GitHub, downloads that exact source archive, and uses a per-PR/per-SHA virtual environment and app-data directory. It serves the app only on `127.0.0.1:8089` by default.
- Music and download paths are redirected to the private test sandbox. slskd is disabled by default; keep it disabled for ordinary UI smoke tests. Do not change paths to real media/download directories or perform destructive live-acquisition tests without explicit authorization.
- Complete the terminal Pass/Fail/Skip checklist after using the browser UI. The Markdown report records the tested SHA and CI run state, is saved under `~/navi-librarian-test/reports/`, and can be posted to the PR through the helper's `gh` confirmation prompt.
- A UI startup confirms only that the app starts. Each checklist item must be recorded separately; skipped/unattempted checks are not passes. If the PR head changes after testing, rerun against the new head or clearly explain why the tested SHA remains applicable.
- This manual check supplements, and never replaces, automated regression tests, full unit-test discovery, exact-head CI, or separate deployment/runtime verification.

See [`docs/LOCAL_UI_TESTING.md`](LOCAL_UI_TESTING.md) for the operator checklist and report semantics.

## Normal change cycle

1. Inspect GitHub `main`, open PRs, recent commits, latest CI, and relevant project docs/code/tests.
2. Define one concrete objective and acceptance criteria.
3. Create a focused branch from current GitHub `main` (or another explicitly justified GitHub ref).
4. Implement the smallest focused change and regression tests; preserve unrelated behavior and compatibility.
5. Run focused tests, the full suite, syntax checks, safety tests, and Docker/package checks where applicable. Report unavailable checks honestly.
6. Inspect the complete diff; confirm required CI has completed successfully on the exact candidate head. Re-check after any new commit.
7. Open/update a GitHub PR with scope, acceptance criteria, tests, CI evidence, and known limitations. Merge only under the agreed authorization/review process.
8. Verify the resulting `main` commit and applicable CI independently; do not infer merge-commit CI from PR-head CI.
9. If publishing/deployment is authorized, record image tag and digest, deployment target/configuration, health/log checks, smoke-test outcomes, and rollback reference.
10. Close out by updating status and log with the exact state: Planned, Implemented, Tested, Merged, Published, Deployed, Verified. These are separate states.

## Test-gap closure / release gate

Before calling the workflow complete, the repository must have a repeatable gate that distinguishes:

- **Unit/regression:** focused tests plus full unittest discovery.
- **Static/package checks:** Python syntax/compilation, dependency/install checks, Compose validation where applicable, and Docker build.
- **Safety:** path traversal, symlink escape, ambiguous folder, no-overwrite, rollback, and unrelated-file preservation tests.
- **Integration/UI:** fresh setup/login, discovery loading/refresh, Get/requested/duplicate prevention/error recovery, acquisition progress/completion/dismiss/retry, settings save/reload, restart persistence, and external-service failure behavior.
- **Release provenance:** exact tested commit, CI URLs/status, image tag/digest, and target architecture.
- **Operations:** deployment authorization, running version verification, logs/health, smoke tests, persistent data, and rollback readiness.

Not every integration test must run on every unit-test PR, but the required release gate must be explicit and repeatable. A skipped/unavailable check is not a pass; record it and keep release status unverified until the gate is satisfied.

Destructive cleanup tests must use temporary/disposable test directories and prove that files outside the intended target remain untouched. Do not run destructive smoke tests against real media/download data without explicit authorization.

## Local testing without making local code authoritative

- Create a clean, isolated test environment from the exact GitHub PR head or `main` SHA.
- Record the tested SHA, Python/runtime versions, commands, outcomes, and skipped tests.
- Do not push test-only commits or local merge commits; if a combined test tree is necessary, label it as experimental and separately test the exact proposed GitHub commit.
- Do not reset, clean, overwrite, or delete existing local work as part of creating the new environment without explicit authorization.

## Reporting requirements

For every meaningful handoff, report:
- GitHub PR/branch and exact commit SHA;
- tests and CI actually observed, with links/status;
- implementation, merge, publication, deployment, and runtime verification states separately;
- exact local testing instructions for the intended revision;
- unresolved issues, skipped checks, rollback notes, and the next concrete action.

Project status and durable decisions belong in `docs/PROJECT_STATUS.md`, `docs/DECISIONS.md`, and this file. Never record credentials or other secrets.
