# Development and Git workflow

Last updated: 2026-11-14.

## Authority and responsibilities

- **Exclusive reference rule:** in all repository documentation, source comments, commit messages, PR titles/descriptions/reviews, issue discussions, and other project communications, refer to the person directing this project exclusively as **“the owner”**. Do not use their personal name, account username/handle, or another label for that person. Apply this rule to new text and to any existing text being edited; quote historical text only when necessary to preserve evidence, and avoid expanding or repeating identifying references.
- **GitHub is the single source of truth** for code, commits, branches, PRs, documentation, and release history. Never use a local checkout as the source for authoritative changes; local environments test identifiable GitHub revisions only.
- Start each task by checking current `main`, recent commits, open PRs, and relevant CI. Read [`PROJECT_STATUS.md`](PROJECT_STATUS.md), then [`ACTIVE_WORK.md`](ACTIVE_WORK.md), and define one concrete objective with acceptance criteria.
- **Mandatory architecture-first navigation:** before opening source files, running broad grep/search commands, or choosing implementation files, read [`ARCHITECTURE.md`](ARCHITECTURE.md) in full. Use its module-ownership map to identify the responsible package and likely entry points. Then open those specific files, their callers, tests, configuration and contracts. Do not use repository-wide grep as the first way to discover ownership or module boundaries.
- If the ownership map does not identify the needed file, use the task-specific documentation and [`scripts/session_search.py`](../scripts/session_search.py) to narrow the search; only then use targeted source search. Search results are navigation aids, not proof: trace actual imports/callers and inspect relevant tests, configuration and safety behavior. If ownership is genuinely unclear or crosses boundaries, update the map only after confirming the current code and dependencies.
- Read [`REQUIREMENTS.md`](REQUIREMENTS.md), [`TEST_PLAN.md`](TEST_PLAN.md), and [`DECISIONS.md`](DECISIONS.md) for the task's behavior, verification and constraints. Search root [`PROJECT_LOG.md`](../PROJECT_LOG.md) for prior evidence.
- MCP is retired as a supported interface. Do not reintroduce MCP runtime, registration, or startup paths. Preserve the supported web interface and shared service behavior.
- UI work follows the same repository, testing, safety, and review rules as backend work. Keep domain/discovery/acquisition/import logic server-side; do not duplicate it in browser code. Preserve established API, authentication, accessibility, keyboard/focus, responsive, and reduced-motion behavior. UI work must use the isolated procedure in [`LOCAL_UI_TESTING.md`](LOCAL_UI_TESTING.md), plus the UI acceptance gates in [`TEST_PLAN.md`](TEST_PLAN.md). Historical redesign direction and phase evidence are in [`archive/redesign/`](archive/redesign/).

## Owner learning note after successful merges

- **Every successful PR merge must be followed by a beginner-friendly `Did you know?` section in the agent's final response to the owner.** This is required even when the merge is documentation-only; if a task merges multiple PRs, include a learning section after reporting the merges (one lesson per merged PR is ideal, and do not omit the section).
- Teach one basic Python idea per lesson, using plain language for someone with no coding background. Prefer a concept connected to the merged change when possible, but the lesson itself must be about Python.
- Keep each lesson short and concrete: explain the idea in everyday terms, show a tiny Python example when useful, and explain what the example does. Avoid unexplained jargon, assume no prior knowledge, and vary topics over time rather than repeating the same lesson.
- **Model-cost notice (owner rule, 2026-11-06):** after the `Did you know?` section, the final response must also say whether the next slice or task could be done by Haiku, and at which effort (low, medium or high), or that it needs a stronger model, with one line of reasoning, so the owner can save usage.
- Only claim a merge occurred when GitHub confirms it. If no PR was successfully merged, this post-merge requirement is not triggered.

## Normal change cycle

1. Inspect repository state, relevant documentation, implementation, all callers, tests, configuration, packaging, and compatibility boundaries.
2. Define the objective, acceptance criteria, risks, and dependencies.
3. Branch from current GitHub `main`, unless another GitHub base is explicitly justified.
4. Make the smallest reviewable change and add regression tests. Preserve behavior, response shapes, side effects, persistence, and compatibility interfaces unless an approved requirement says otherwise.
5. Run focused tests, syntax checks, and applicable API/Docker checks where execution is available. **Agents must never run the full unit suite** (owner rule); the owner runs it independently and CI runs it on the PR head. Report exactly which focused tests ran and all skipped/unavailable checks.
   - **Selective testing (owner rule, 2026-11-04):** run only the tests for code you changed (for Swift, `swift test --filter <suite or target>`). Do not re-run tests for code that is already tested and unmodified. For the macOS client, Swift tests run only on a Mac, locally, and are not run on GitHub: the owner removed the macOS CI workflow on 2026-11-04 (`.github/workflows/macos-package.yml`). Choose the targets with the dependency map in `macos/scripts/select-tests.sh` (keep it in step with `macos/Package.swift`); an unrecognised path, `Package.swift` or `Package.resolved` means run the full suite, and report it as not run if it was not.
6. Review the complete diff, changed-file list, callers, package inclusion, unsafe failure cases, secrets, and unintended changes.
7. For code, tests, Docker/Compose, or workflow changes, open/update a focused PR and verify required CI on the exact final PR-head SHA after the last change. Merge only when acceptance criteria, diff review, and required gates pass.
8. **Documentation-only owner rule:** documentation-only changes are committed directly to `main`, not through a PR. Review links, current state, and the complete documentation diff before committing.
9. After merge, refresh `main`, PRs, and CI before dependent work. Record exact branch/PR/SHA, tests and CI, limitations, merge state, and next action in project documentation.

- **Server module rule (owner decision, D-016):** `navidrome_server.py` takes no additions. New code goes in new modules with direct-import tests; a change that touches the server must remove or move lines, not add them. PR #592 added adapters to the server; they were moved to `discovery/lens_service.py` afterwards.

## Testing and safety

- Use [`TEST_PLAN.md`](TEST_PLAN.md) as the verification baseline. Never claim a test passed unless it was actually run. A successful import, build, startup, or workflow definition alone is not proof of correctness.
- UI changes require automated CI first, then manual browser checks against the exact tested SHA using `LOCAL_UI_TESTING.md`. Record actual results; if the head changes, retest or clearly identify the earlier SHA.
- Treat acquisition, import, cleanup, and deletion as safety-critical. Validate canonical paths under configured roots; reject traversal, symlink escapes, ambiguous targets, and unsafe paths; prevent overwriting/deleting unrelated files. Test safe success and unsafe refusal.
- **Provider requests (owner rule, 2026-11-05):** every provider request (MusicBrainz, ListenBrainz, Last.fm, Discogs, and any other external service) must use a batch lookup whenever the provider offers one (for example one MusicBrainz browse per artist instead of one lookup per release). Fall back to single lookups only when no batch form exists, and say so in the PR. Existing budgets, pacing and owner approvals for provider traffic still apply.
- **Provider credentials for agents (owner rule, 2026-11-05):** agents always read provider credentials from the `config.env` file in the local working folder (never committed, never printed, never copied into the repository, docs, logs or PRs). Do not look for credentials elsewhere or ask for them to be pasted into the conversation.
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

## Local toolchain notes

- **Android Gradle needs JDK 17.** The system default JDK on the owner's Mac (27) fails the build. Use the Homebrew `openjdk@17`: `JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew testDebugUnitTest --tests '<filter>'` from `android/`.
