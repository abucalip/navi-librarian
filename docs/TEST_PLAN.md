# Test plan

Last updated: 2026-11-27.

Verification baseline for the **server and web client** (native client test plans live in `abucalip/discair-macos` and `abucalip/discair-android`). Historical test evidence belongs in [`PROJECT_LOG.md`](../PROJECT_LOG.md).

## Required checks for backend changes

1. **Focused regressions only:** run `pytest <file>` for changed modules and new direct-import tests. **Never run the full unit suite** without explicit owner approval (CI runs the full suite on the PR head). Use `pytest` (not `unittest`) for any module calling MusicBrainz so `tests/conftest.py` provides the private provider gate.
2. **Lint ratchet:** run `python scripts/check_lint_changed.py --base origin/main` on touched Python files.
3. **Safety cases:** for acquisition, import, cleanup, deletion, auth, and path validation, test both intended success and unsafe refusal (canonical-root validation, traversal/symlink escape, ambiguous paths, no-overwrite, unrelated-file preservation).
4. **Supported interfaces:** preserve public web/API contracts and shared service behavior; MCP is retired and must not be initialized.
5. **Diff review:** inspect every changed file, callers, imports, package inclusion, and error paths before pushing.

## GitHub Actions & PR handoff

CI runs on every PR head:
- Python syntax and acquisition-safety regressions
- Docker packaging, full unit suite, and image build
- Isolated container runtime smoke test
- Validation-only multi-architecture image check (`push: false`)
- Lint changed files (`scripts/check_lint_changed.py`)

Agents end the task after pushing and creating/updating the PR; the owner handles CI and merge gates unless explicitly requested otherwise.

## Deterministic recommendation replay

- Captures must freeze ordered post-gathering inputs, weighted/raw play-count maps, ranking timestamp, recommendation-history rows, and validated diversity setting.
- Replay must rank from pristine frozen inputs without live provider calls; schema-v1 captures must fail with a recapture instruction rather than silently falling back to live DB/time/settings.

## Web UI changes

- Follow the isolated browser procedure in [`LOCAL_UI_TESTING.md`](LOCAL_UI_TESTING.md).
- Verify responsive layout, keyboard/focus navigation, reduced-motion behavior, and authenticated API/error states.
- Record exact SHA tested and any skipped checks.

## Reporting states separately

Track and report these states distinctly—never conflate them:
- **Implemented** (on branch) ≠ **Focused tests passed** ≠ **CI passed** ≠ **Merged** ≠ **Published** ≠ **Deployed** ≠ **Verified at runtime**.
