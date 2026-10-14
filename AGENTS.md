# Project instructions — ZCode front-end ownership

Repository: `abucalip/navi-librarian`.

**Read this file before making changes.** GitHub is the single source of truth. The app is a FastAPI web application with extracted UI templates/assets; it is not a separately deployed frontend. Your role is front-end implementation only.

## Mission and product context

Improve the Librarian UI's clarity, speed, accessibility, responsive behavior, and reliability while preserving the established API, authentication, and domain behavior. The product helps a user explore their Navidrome library and listening taste, discover music, and request acquisitions through existing backend services. Keep the interface smooth and stable; do not duplicate discovery, recommendation, acquisition, or import logic in browser code.

Before starting a task:
1. Read this file and the relevant sections of `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, and `docs/TEST_PLAN.md`.
2. Inspect current GitHub `main`, open PRs, recent commits, and checks that affect your work.
3. Inspect the relevant template, stylesheet, script, API caller, and tests before deciding on an implementation.
4. Write down a narrow objective and acceptance criteria in your own working notes or PR description.

## Files you may change

Normal implementation scope:
- `static/app.css`
- `static/app.js`
- `static/login.css`
- `static/login.js`
- `app/templates/*.html`
- narrowly scoped front-end tests/fixtures under `tests/`

Do not expand this scope silently. If a task requires a new frontend file outside these paths, explain why in the PR and coordinate first. Reading backend code or tests is allowed to understand behavior; reading a file does not grant permission to edit it.

## Protected ownership boundaries

Do not edit these without explicit approval and coordinated ownership:
- `app/main.py`, including application assembly, middleware, route registration, and authentication boundaries
- `app/api/**` and `app/security/**`
- `navidrome_server.py`, domain/service modules, discovery/recommendation logic, acquisition/import lifecycle, persistence, and filesystem operations
- `Dockerfile*`, Compose files, `.github/workflows/**`, dependencies/lockfiles, packaging, release, or deployment configuration
- requirements, architecture, roadmap, test-gate, or deployment policy

Do not change endpoint paths/methods, request or response schemas, auth/session/cookie behavior, public-path rules, authorization, persistence semantics, acquisition/Get/Skip/Dismiss behavior, or filesystem-safety guarantees. Do not add dependencies, a build system, analytics, trackers, or external asset dependencies without approval.

## API and security contract

- Treat the existing API as authoritative. Inspect its route and regression tests before relying on an endpoint or field.
- Keep login/setup/logout flows and protected content protected. Public access is limited to the existing explicitly allowed login assets and static resources.
- Never place credentials, tokens, secrets, private paths, or service configuration in client-side files or rendered markup.
- Never invent a backend endpoint or field. Do not present mock behavior as working integration.
- If a new API field, endpoint, or server behavior is needed, stop at a concise proposal in the PR: describe the user need, proposed request/response contract, failure cases, and why the existing contract is insufficient. The assistant owns the backend/API implementation and cross-layer integration.
- Avoid unsafe HTML insertion. Treat API/user-controlled strings as untrusted; prefer text APIs and safe DOM construction.
- Show loading, empty, success, and error states accurately. Do not report success until the server confirms it, especially for acquisition or other consequential actions.
- Preserve existing acquisition and file-safety protections; UI controls must not bypass server-side validation.

## UI implementation principles

- Follow the existing visual system and components before introducing new patterns. Prefer a coherent, professional interface over one-off styling.
- Preserve the established type, color, spacing, artwork, and navigation patterns unless the task explicitly targets them.
- Make responsive behavior intentional; avoid overflow, layout shifts, and controls that become inaccessible on narrow screens.
- Use semantic HTML, accessible names, keyboard-operable controls, visible focus, and sufficient contrast. Do not rely on color alone to communicate state.
- Keep client behavior predictable: prevent duplicate submissions where appropriate, handle failed/slow requests, and leave the interface usable after errors.
- Avoid unnecessary full-page reloads or repeated requests when the current architecture supports a smaller update. Do not add premature complexity or duplicate domain state in the browser.
- Preserve existing behavior outside the requested scope. Keep changes focused and explain material trade-offs in the PR.

## Design-tool workflow (Impeccable)

Use Impeccable as a design critique and implementation aid when available in ZCode. Start with its critique/audit guidance before styling; use its design-system, hierarchy, spacing, typography, contrast, responsive, and accessibility guidance rather than applying a generic template. Apply only recommendations that fit this product and its existing components. Do not blindly run broad redesign commands, add a frontend framework, or introduce new dependencies. Prefer one cohesive, reviewable improvement over sweeping visual churn. Record which Impeccable guidance was applied and what was intentionally rejected in the PR summary.

## Git and pull-request workflow

1. Work from current GitHub `main`, unless a different GitHub base is explicitly justified.
2. Create a focused feature branch, for example `ui/<short-task-name>`. Never commit directly to `main`.
3. Keep the diff front-end-only. If backend/API changes are necessary, stop and propose the contract rather than editing protected files.
4. Add/update focused UI tests where behavior changes. Understand what existing tests protect; never delete or weaken regression assertions merely to make a change pass.
5. Run relevant available checks. Follow `docs/TEST_PLAN.md`; run focused tests, the full unit suite when feasible, and any relevant syntax checks. Report the exact commands and actual results.
6. Review the complete diff and changed-file list. Verify no protected files, API contracts, security rules, or domain behavior changed.
7. Open a PR against `main`. Include purpose, changed files, acceptance criteria, tests actually run, limitations, and screenshots or before/after notes for visual changes.
8. Do not merge, publish images, deploy, alter branch protection, disable CI, or bypass required checks. The assistant owns cross-layer review, release controls, merge coordination, and project-level verification.
9. Never force-push, overwrite unrelated work, or delete branches/worktrees without explicit authorization. If `main` advances, update the branch safely and rerun relevant checks.

## Initial assigned task — visual quality audit and focused polish

Audit the existing web UI and implement one focused, visible improvement that makes it feel intentionally designed and less generic, using Impeccable guidance where available. Begin by identifying the highest-impact issue in the existing UI; prefer improving hierarchy, typography, spacing, component consistency, or responsive behavior over adding features. Preserve the existing dark visual direction and yellow/red accents, existing font choices, album artwork, and established product interactions. Do not redesign every screen in one PR.

Acceptance criteria:
- State the chosen problem and why it matters before implementation.
- Make a focused change only within the allowed UI files and narrow front-end tests.
- No backend/API/authentication, acquisition, or domain behavior changes.
- Verify desktop and narrow viewport behavior, keyboard/focus states, loading/empty/error states where relevant, and browser console/network errors.
- Add/update tests for any changed client behavior.
- Open a PR with before/after screenshots and a concise explanation of the design decisions; do not merge it yourself.

## Testing and acceptance checklist

- UI-facing changes require passing automated checks on the exact PR-head SHA, followed by manual browser testing against that exact SHA using `docs/LOCAL_UI_TESTING.md` and `docs/TEST_PLAN.md`.
- Use the documented isolated test helper, sandbox music/download paths, and disabled slskd for ordinary UI checks. Never point UI testing at live download folders or perform destructive acquisition actions on real data without explicit authorization.
- Consider login/setup, navigation, artwork, discovery, album details, settings, Get/request state, acquisition cards, empty/loading/error/recovery states, performance, and browser/server errors as relevant to the change. Record skips as skips, not passes.
- Add tests for changed client behavior and preserve existing assertions. Server-side safety remains enforced and tested in backend/domain tests; browser checks do not replace those tests.
- If the PR head changes after manual testing, retest the new SHA or state clearly that the report covers the earlier SHA.
- Report implemented, automated-tested, browser-tested, merged, published, deployed, and runtime-verified as separate states. A merge or CI pass is not deployment evidence.

## Handoff format

At completion, provide the PR URL, branch, exact head SHA, files changed, tests/checks actually run, manual UI report if required, known limitations, and the next action. Do not claim a check passed unless its result was observed. If blocked by a missing backend contract or protected-file change, describe the proposal and stop.
