# Development and Git workflow

Last updated: 2026-11-27.

## Core rules

- **Exclusive reference rule:** refer to the person directing this project exclusively as **“the owner”** everywhere (docs, comments, commits, PRs). Never use their name or handle.
- **GitHub is the single source of truth.** Branch from current GitHub `main`. Never restart archived/completed work or bypass owner-approval gates.
- **Architecture-first navigation:** read [`ARCHITECTURE.md`](ARCHITECTURE.md) in full before opening source files or searching. Use its map to jump straight to source files and focused tests; fall back to `scripts/session_search.py` or targeted search only if needed. Update [`ARCHITECTURE.md`](ARCHITECTURE.md) in the same change whenever adding or moving a module/subsystem.
- **MCP is retired.** Do not reintroduce MCP runtime, registration, or startup paths. Keep domain logic server-side; UI only presents it.
- **Server module rule (D-016):** `navidrome_server.py` takes no additions. New code goes in new modules with direct-import tests; changes touching `navidrome_server.py` must remove or move lines overall.

## Change cycle

1. Check `main`, [`PROJECT_STATUS.md`](PROJECT_STATUS.md), [`ACTIVE_WORK.md`](ACTIVE_WORK.md), and [`ARCHITECTURE.md`](ARCHITECTURE.md).
2. Branch from current `main`, make the smallest reviewable change, and add regression tests.
3. **Run focused tests only** (`pytest <file>`). **Never run the full unit suite** (the owner and CI run it). Report exactly what ran and what did not.
4. Run `python scripts/check_lint_changed.py --base origin/main` if touching Python files (CI fails on new pylint findings in touched files; do not add suppression comments).
5. Push and open/update a focused PR. **End the task after pushing and creating/updating the PR** — do not wait for, watch, or poll CI unless the owner explicitly asks.
6. **Documentation-only changes** go straight to `main`, no PR.

## Opportunistic simplification

While modifying code, you may include a small, behaviour-preserving simplification in the same PR **only when all 7 conditions hold**:
1. **Identical behaviour** (outputs, shapes, side effects, persistence, errors, ordering).
2. **Covered by a focused test** (existing or added first); otherwise list it in `ACTIVE_WORK.md` under "Simplification candidates".
3. **Small scope:** touched files or direct imports only, ≤1/3 of the diff.
4. **Own commit:** titled `simplify: ...`, with a **Simplifications** section in the PR description.
5. **Never in safety-critical or paced code:** acquisition, import, cleanup/deletion, auth, path validation, or provider-request code.
6. **Real simplification only:** dead code, local duplication, needless `else` after `return`/`raise`, idiomatic comparisons, flatter nesting. No taste renames/moves; do not change broad `except Exception` (report as candidate).
7. **Contracts and public names untouched.**

## Testing, safety, and providers

- **Safety-critical code** (acquisition, import, cleanup, deletion, auth, path validation): validate canonical paths under configured roots; reject traversal, symlink escapes, and ambiguous targets; test safe success and unsafe refusal.
- **Provider requests:** use batch lookups whenever the provider offers one; keep existing pacing, budgets, and owner-approval gates.
- **Credentials:** read provider credentials from workspace `config.env` only; never print, log, or commit them.
- **Web UI changes:** follow [`LOCAL_UI_TESTING.md`](LOCAL_UI_TESTING.md) and [`TEST_PLAN.md`](TEST_PLAN.md).
- **Release safety:** merge ≠ publish ≠ deploy ≠ verified at runtime. Image publication and deployment stay paused unless explicitly authorized.

## Post-merge response (only when GitHub confirms a merge)

1. **`Did you know?`** — one beginner-friendly Python concept in plain language with a tiny example (vary topics).
2. **Model-cost notice** — whether the next slice can use Haiku (low/medium/high effort) or needs a stronger model, with one line of reasoning.

## Documentation ownership

- `docs/ACTIVE_WORK.md` — open server/web tasks and parked decisions (1–3 bullets per item).
- `docs/PROJECT_STATUS.md` — rolling snapshot (≤30 lines) and single next action.
- `docs/ARCHITECTURE.md` — module-to-file and focused-test map.
- `docs/REQUIREMENTS.md` — concise user-facing behavior ledger.
- `docs/TEST_PLAN.md` — verification baseline.
- `docs/DECISIONS.md` — active architectural constraints.
- `PROJECT_LOG.md` — recent chronological evidence; rotate older entries to `docs/archive/`.
- `docs/archive/` — completed plans and historical logs (ignored by default search via `.rgignore`).
