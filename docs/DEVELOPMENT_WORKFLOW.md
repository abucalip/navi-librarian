# Development and Git workflow

Last updated: 2026-10-24.

## Authority and responsibilities

- **Exclusive reference rule:** in all repository documentation, source comments, commit messages, PR titles/descriptions/reviews, issue discussions, and other project communications, refer to the person directing this project exclusively as **“the owner”**. Do not use their personal name, account username/handle, or another label for that person. Apply this rule to new text and to any existing text being edited; quote historical text only when necessary to preserve evidence, and avoid expanding or repeating identifying references.
- **GitHub is the single source of truth** for code, commits, branches, PRs, documentation, and release history. Never use a local checkout as the source for authoritative changes; local environments test identifiable GitHub revisions only.
- Start each task by checking current `main`, recent commits, open PRs, and relevant CI. Read [`PROJECT_STATUS.md`](PROJECT_STATUS.md), then [`ACTIVE_WORK.md`](ACTIVE_WORK.md), and define one concrete objective with acceptance criteria.
- Read [`REQUIREMENTS.md`](REQUIREMENTS.md), [`TEST_PLAN.md`](TEST_PLAN.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and [`DECISIONS.md`](DECISIONS.md) as relevant. Search root `PROJECT_LOG.md` for prior evidence. Use `python scripts/session_search.py "<task-specific concepts>"` when available; search is navigation, not proof that callers or safety cases have been inspected.
- MCP is retired as a supported interface. Do not reintroduce MCP runtime, registration, or startup paths. Preserve the supported web interface and shared service behavior.
- UI work follows the same repository, testing, safety, and review rules as backend work. Keep domain/discovery/acquisition/import logic server-side; do not duplicate it in browser code. Preserve established API, authentication, accessibility, keyboard/focus, responsive, and reduced-motion behavior. UI work must use the isolated procedure in [`LOCAL_UI_TESTING.md`](LOCAL_UI_TESTING.md), plus the UI acceptance gates in [`TEST_PLAN.md`](TEST_PLAN.md). Historical redesign direction and phase evidence are in [`archive/redesign/`](archive/redesign/).

## Normal change cycle

1. Inspect repository state, relevant documentation, implementation, all callers, tests, configuration, packaging, and compatibility boundaries.
2. Define the objective, acceptance criteria, risks, and dependencies.
3. Branch from current GitHub `main`, unless another GitHub base is explicitly justified.
4. Make the smallest reviewable change and add regression tests. Preserve behavior, response shapes, side effects, persistence, and compatibility interfaces unless an approved requirement says otherwise.
5. Run focused tests, syntax checks, and applicable API/Docker checks where execution is available. **Agents must never run the full unit suite** (owner rule); the owner runs it independently and CI runs it on the PR head. Report exactly which focused tests ran and all skipped/unavailable checks.
6. Review the complete diff, changed-file list, callers, package inclusion, unsafe failure cases, secrets, and unintended changes.
7. For code, tests, Docker/Compose, or workflow changes, open/update a focused PR and verify required CI on the exact final PR-head SHA after the last change. Merge only when acceptance criteria, diff review, and required gates pass.
8. **Documentation-only owner rule:** documentation-only changes are committed directly to `main`, not through a PR. Review links, current state, and the complete documentation diff before committing.
9. After merge, refresh `main`, PRs, and CI before dependent work. Record exact branch/PR/SHA, tests and CI, limitations, merge state, and next action in project documentation.

- **Server module rule (owner decision, D-016):** `navidrome_server.py` takes no additions. New code goes in new modules with direct-import tests; a change that touches the server must remove or move lines, not add them. PR #592 added adapters to the server; moving them out is a required follow-up before slice 4.

## Testing and safety

- Use [`TEST_PLAN.md`](TEST_PLAN.md) as the verification baseline. Never claim a test passed unless it was actually run. A successful import, build, startup, or workflow definition alone is not proof of correctness.
- UI changes require automated CI first, then manual browser checks against the exact tested SHA using `LOCAL_UI_TESTING.md`. Record actual results; if the head changes, retest or clearly identify the earlier SHA.
- Treat acquisition, import, cleanup, and deletion as safety-critical. Validate canonical paths under configured roots; reject traversal, symlink escapes, ambiguous targets, and unsafe paths; prevent overwriting/deleting unrelated files. Test safe success and unsafe refusal.
- Preserve configuration and persistent data. Never weaken safety checks, overwrite unrelated work, force-push, or delete production data to make tests pass.
- Stop when a boundary is unclear, tests fail, or a higher-priority correctness/security/verification issue exists. Avoid size-only refactors and speculative extraction work.

## Release and production safety

- Image publication and deployment remain paused until explicitly authorized.
- Track implementation, testing, CI, merge, publication, deployment, and runtime verification separately. A merge is not publication; publication is not deployment; deployment is not runtime verification.
- For authorized deployment, verify image tag/digest, Compose configuration, persistent storage, logs, connectivity, and application behavior. Preserve a rollback reference and obtain appropriate authorization before consequential production actions.

## Documentation ownership and closeout

Keep one canonical home for each kind of information:
- outstanding tasks and parked decisions: [`ACTIVE_WORK.md`](ACTIVE_WORK.md);
- current snapshot and single next action: [`PROJECT_STATUS.md`](PROJECT_STATUS.md);
- product behavior: [`REQUIREMENTS.md`](REQUIREMENTS.md);
- verification requirements: [`TEST_PLAN.md`](TEST_PLAN.md);
- current boundaries and rationale: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`DECISIONS.md`](DECISIONS.md);
- chronological completed work and verification evidence: root [`PROJECT_LOG.md`](../PROJECT_LOG.md);
- historical or completed plans: [`archive/`](archive/).

At meaningful session closeout, update `PROJECT_STATUS.md` and root `PROJECT_LOG.md`, plus only the relevant requirements, test, workflow, architecture, or deployment documents. Record facts only: exact PR/commit, tests actually run, CI evidence, UI results when applicable, merge/publication/deployment/runtime state, limitations, and one next action. Do not duplicate long PR/CI narratives across the active queue and status snapshot.
