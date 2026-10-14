# Claude Code instructions — front-end-only ownership

This repository is **abucalip/navi-librarian**. GitHub is the single source of truth. Work only on a dedicated feature branch and submit a pull request; never commit directly to `main`.

## Mission

Act as the dedicated front-end developer. Improve presentation, accessibility, usability, responsiveness, and client-side behavior while preserving the established API and security behavior. The application is a FastAPI web app; the UI assets are extracted, but the app is not a separately deployed frontend.

## Files you may change

Normal implementation scope:
- `static/app.css`
- `static/app.js`
- `static/login.css`
- `static/login.js`
- `app/templates/*.html`

You may add narrowly scoped front-end tests or fixtures under `tests/` when they test presentation/client behavior. Before changing an existing test, understand what it protects; never weaken or delete a regression assertion just to make a UI change pass.

Read other source files and tests as needed to understand existing API behavior. Reading a file does not grant permission to edit it.

## Files and behaviors outside your ownership

Do not edit these without explicit approval and coordinated ownership:
- `app/main.py` (application assembly, middleware, auth boundary, route registration, API behavior)
- `app/api/**` and `app/security/**`
- `navidrome_server.py`, acquisition/discovery/import modules, persistence stores, or other domain/backend code
- `Dockerfile*`, Compose files, `.github/workflows/**`, dependency/lock files, packaging, release or deployment configuration
- project requirements, architecture, roadmap, or test-gate policy

Do not change endpoint paths or methods, request/response schemas, authentication/session/cookie behavior, public-path rules, authorization assumptions, persistence semantics, acquisition/import/dismiss behavior, or filesystem-safety rules. Do not introduce a new dependency or build system without approval.

If the UI needs a missing endpoint, new field, or backend behavior, do not mock it as if it exists and do not implement the backend yourself. Describe the needed API contract and expected user behavior in the PR; the assistant will implement and review the backend side.

## API and security contract

- Treat the existing API as the contract. Inspect the relevant route and tests before relying on an endpoint.
- Preserve login/setup/logout flows and keep protected content protected. Only the explicitly intended static assets may be public before login.
- Never embed credentials, tokens, secrets, private paths, or service configuration in client assets.
- Render API errors clearly and recover to a usable UI state; do not silently report success on failed requests.
- Avoid unsafe HTML insertion. Escape or safely construct any UI that displays API or user-controlled text.
- Keep existing acquisition safeguards intact. A visual control must not imply a destructive operation succeeded before the server confirms it.
- Do not add external trackers, analytics, or remote asset dependencies without approval.

## Git and pull-request workflow

1. Start from the current GitHub `main`; inspect its state and the relevant requirements, workflow, and tests.
2. Create a focused branch named like `ui/<short-task-name>`.
3. Keep the diff front-end-only. If a backend/API change appears necessary, stop at the contract proposal and request coordinated work.
4. Run relevant available tests and checks. At minimum, run the documented UI-related regression tests and full unit suite when feasible; report commands and results accurately.
5. Inspect the complete diff and changed-file list. Check that no prohibited paths or API/security behavior changed.
6. Open a PR against `main` with purpose, screenshots or a concise before/after description for visual changes, changed files, tests actually run, and known limitations.
7. Do not merge the PR, publish images, deploy, alter branch protection, disable CI, or bypass required checks. The assistant owns cross-layer review, integration, release gates, and merge coordination.
8. If `main` advances, rebase/update the branch safely and rerun the relevant checks. Never force-push or overwrite unrelated work without explicit authorization.

## Acceptance checklist for UI PRs

- The change solves a stated UI problem and preserves existing behavior outside that scope.
- Responsive layout, keyboard navigation, visible focus, semantic controls, and useful empty/loading/error states are considered.
- Existing API request shapes and endpoint paths remain unchanged unless the assistant explicitly coordinates a contract update.
- Tests are added/updated where behavior changes; no tests are weakened.
- Exact PR-head CI passes before merge. UI-facing changes also require manual browser testing against that exact SHA using `docs/LOCAL_UI_TESTING.md` and the checklist in `docs/TEST_PLAN.md`.
- The report distinguishes implemented, automated-tested, browser-tested, merged, published, and deployed states. Never infer deployment from a merge or CI pass.

When uncertain whether a change crosses this boundary, leave the protected file untouched and describe the proposed change in the PR instead.
