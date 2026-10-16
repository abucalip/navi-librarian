# Test plan

Last updated: 2026-10-16

This document defines the **verification baseline**, not a chronological record of past PRs. Exact historical test evidence belongs in the root \`PROJECT_LOG.md\`. Always verify current results for the exact revision being proposed.

## Required checks for backend changes

1. **Focused regressions:** run the tests covering the changed behavior and new direct-import tests for extracted logic.
2. **Full unit suite:** run \`python -m unittest discover -s tests -v\`.
3. **Syntax and static checks:** run the repository's Python syntax/acquisition-safety workflow and applicable syntax checks.
4. **API and package checks:** exercise relevant API contracts and verify changed modules are included by Docker/package configuration.
5. **Safety cases:** for acquisition, import, cleanup, and deletion, test intended success and unsafe refusal. Cover canonical-root validation, traversal/symlink escape, ambiguous paths, unrelated-file preservation, no-overwrite behavior, incomplete files, and relevant state/race boundaries.
6. **Compatibility:** for extracted code, test direct imports and the legacy adapter/public interface. Preserve MCP behavior until a separate retirement decision authorizes a change.
7. **Full diff review:** inspect every changed file, callers, test fixtures, imports, package inclusion, error paths, and unintended changes.

## Required GitHub Actions workflows

After the final code or documentation commit, verify all four workflows on the **exact final PR-head SHA**:

- Python syntax and acquisition-safety regressions.
- Docker packaging, full unit suite, and image build.
- Isolated container runtime smoke test.
- Validation-only multi-architecture image validation.

The multi-architecture workflow must remain non-publishing (\`push: false\`). A workflow existing, a successful compile, or a container starting does not prove all required checks passed. If a workflow is missing, skipped, cancelled, or associated with another SHA, state that explicitly and do not claim the gate is complete.

## UI changes

After automated CI succeeds, run the full manual browser checklist in \`docs/LOCAL_UI_TESTING.md\` against the exact tested SHA. Cover affected workflows and record the actual result. Do not claim manual verification from source inspection or automated tests alone.

## Reporting states separately

Track these states independently:
- Implemented.
- Focused tests run.
- Full suite run.
- Required CI passed on exact final PR-head SHA.
- Merged.
- Published.
- Deployed.
- Runtime verified.

Never infer a later state from an earlier one. Record unavailable or skipped tests and any unverified behavior.

## Documentation-only changes

For documentation-only PRs:
- inspect the changed docs against current GitHub code and PR state;
- check internal paths, names, SHA references, and claims for accuracy;
- search for duplicated or stale active instructions;
- review the complete diff and ensure no application behavior changed;
- run applicable documentation/link/lint checks if configured;
- verify the required PR workflows when repository policy requires them, and report any unavailable gates honestly.

## Historical evidence

Search the root \`PROJECT_LOG.md\` by PR number, module, or responsibility to find past test runs. Historical success is context, not a substitute for running required checks on the current revision.