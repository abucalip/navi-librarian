# Navi Librarian agent instructions

This repository (`abucalip/navi-librarian`) contains the Python/FastAPI server, the web client, and shared server API contracts (`docs/contracts/`). Native clients live in `abucalip/discair-macos` and `abucalip/discair-android`.

## Start of task (2 reads)
1. Read [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) (rolling snapshot + next action) and the relevant section of [`docs/ACTIVE_WORK.md`](docs/ACTIVE_WORK.md).
2. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) in full before searching or opening source files; use it to jump directly to source files and focused `pytest` modules.

## Hard rules
- Refer to the project director exclusively as **"the owner"** everywhere.
- **Never run the full unit suite.** Run only focused tests (`pytest <file>`) for changed code.
- **`navidrome_server.py` takes no additions** (D-016); new code goes in new modules with direct-import tests.
- Update [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) in the same change when adding or moving a module.
- End the task after pushing and creating/updating the PR; do not wait for or poll CI unless asked.
- Documentation-only changes go straight to `main`, no PR.
- **Do not bloat documentation:** keep doc updates to the necessary minimum—short factual bullets, no long PR/CI narratives, respect line caps (`PROJECT_STATUS.md` ≤30 lines), and never duplicate rules across files.

Full workflow, opportunistic simplification, and safety rules: [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md).
