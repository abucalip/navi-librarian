# Project instructions — shared front-end contribution boundaries

Repository: `abucalip/navi-librarian`.

**Read this file before making changes.** GitHub is the single source of truth. The app is a FastAPI web application with extracted UI templates/assets; it is not a separately deployed frontend. Agents working on front-end matters may implement UI changes, but must stay within the allowed paths below and respect protected ownership boundaries.

## Mission and product context

Improve the Librarian UI's clarity, speed, accessibility, responsive behavior, and reliability while preserving the established API, authentication, and domain behavior. The current front-end mission is the phased redesign defined by `docs/DESIGN_SYSTEM.md` ("Chart Rundown") and sequenced in `docs/REDESIGN_ROADMAP.md`. The redesign may replace the visual identity (color, type, icons, motion, layout) of every page; it may not change behavior, API contracts, or security. The product helps a user explore their Navidrome library and listening taste, discover music, and request acquisitions through existing backend services. Keep the interface smooth and stable; do not duplicate discovery, recommendation, acquisition, or import logic in browser code.

## Before you start a task

1. Read this file, **`docs/DESIGN_SYSTEM.md`** (the canonical visual system: tokens, type, icons, motion, components), **`docs/REDESIGN_ROADMAP.md`** (phases, per-PR checklist, definition of done), and **`docs/FRONTEND_DESIGN_GUIDE.md`** (interaction, accessibility, and boundary rules). Also read `PRODUCT.md` and the Impeccable surface brief under `.impeccable/surfaces/` if present. Do not rely on PR comments or agent memory as a substitute.
2. Read `docs/UI_BACKLOG_EXECUTION.md`, which records the verified front-end baseline, the
   current backlog state, and the session protocol. It is an index into the project docs,
   not a replacement for them; read the additional docs below only when the task needs them.
3. Read the relevant sections of `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, and `docs/TEST_PLAN.md`.
4. Inspect current GitHub `main`, open PRs, recent commits, and checks that affect your work.
5. Inspect the relevant template, stylesheet, script, API caller, and tests before deciding on an implementation.
6. Write down a narrow objective and acceptance criteria in your own working notes or PR description, and identify the roadmap phase and item it addresses and the `docs/DESIGN_SYSTEM.md` sections it applies. If the design system and the code disagree, the design system wins for appearance and the existing API and tests win for behavior.

## Files you may change

Normal implementation scope:
- `static/app.css`
- `static/app.js`
- `static/login.css`
- `static/login.js`
- `app/templates/*.html`
- narrowly scoped front-end tests/fixtures under `tests/` (including the existing `tests/*_ui_contract.py` files, which may be updated narrowly when a redesign step intentionally changes class names or structure)
- vendored, self-hosted front-end assets served from `/static`: `static/fonts/**`, `static/icons.svg`, and `static/vendor/**`. Each vendored asset ships with its license file; nothing is loaded from a CDN or third-party origin at runtime
- front-end design documents, updated in the same PR as the work they record: `docs/DESIGN_SYSTEM.md`, `docs/REDESIGN_ROADMAP.md`, `docs/FRONTEND_DESIGN_GUIDE.md`, `docs/UI_BACKLOG_EXECUTION.md`, `PRODUCT.md`, `DESIGN.md`, and `.impeccable/surfaces/**`
- `docs/TEST_PLAN.md` sections that govern UI verification (the "UI changes" section only)

Do not expand this scope silently. If a task requires a new frontend file outside these paths, explain why in the PR and coordinate first. Reading backend code or tests is allowed to understand behavior; reading a file does not grant permission to edit it.

Documentation changes outside the files listed above follow the same rule as code: propose them rather than editing them unasked.

## Protected ownership boundaries

Do not edit these without explicit approval and coordinated ownership:
- `app/main.py`, including application assembly, middleware, route registration, and authentication boundaries
- `app/api/**` and `app/security/**`
- `navidrome_server.py`, domain/service modules, discovery/recommendation logic, acquisition/import lifecycle, persistence, and filesystem operations
- `Dockerfile*`, Compose files, `.github/workflows/**`, dependencies/lockfiles, packaging, release, or deployment configuration
- requirements, architecture, modularization/backend roadmap, test-gate, or deployment policy (the front-end design documents and the UI verification section named above are the exceptions)

Do not change endpoint paths/methods, request or response schemas, auth/session/cookie behavior, public-path rules, authorization, persistence semantics, acquisition/Get/Skip/Dismiss behavior, or filesystem-safety guarantees. Do not add dependencies, a build system, analytics, trackers, or runtime third-party asset dependencies (CDN fonts, remote icons, remote scripts) without approval. The vendored fonts and icon sprite named above are approved; any other new vendored library, or any JavaScript dependency, still needs approval. The existing Google Fonts `@import` is to be removed by redesign Phase 1, not extended.

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

- Follow `docs/DESIGN_SYSTEM.md` for tokens, type, icons, motion, and components. Until a roadmap phase lands, the shipped tokens in `static/app.css` remain what the app renders; do not mix old and new values within one component. Prefer a coherent, professional interface over one-off styling, and add no value that is not a token.
- The type, color, icon, motion, and layout identity is replaceable under the roadmap. Behavior is not: preserve workflows, terminology that users rely on, accessibility properties (landmarks, names, focus, 44px targets), and the Get/request, Dismiss, and settings-secret behaviors exactly.
- Rank numerals and any other ordering cue must reflect a real order the API returns; never invent one (see `docs/DESIGN_SYSTEM.md` section 8).
- Make responsive behavior intentional; avoid overflow, layout shifts, and controls that become inaccessible on narrow screens.
- Use semantic HTML, accessible names, keyboard-operable controls, visible focus, and sufficient contrast. Do not rely on color alone to communicate state.
- Keep client behavior predictable: prevent duplicate submissions where appropriate, handle failed/slow requests, and leave the interface usable after errors.
- Avoid unnecessary full-page reloads or repeated requests when the current architecture supports a smaller update. Do not add premature complexity or duplicate domain state in the browser.
- Preserve existing behavior outside the requested scope. Keep changes focused and explain material trade-offs in the PR.

## Design-tool workflow (Impeccable)

Use Impeccable as a design critique and implementation aid when available in your working environment. Impeccable's product record is `PRODUCT.md` and the direction contract is `.impeccable/surfaces/app-templates-index-html.md`; the "Chart Rundown" direction is already chosen, so do not re-roll or replace it unless the owner asks. Start each phase with `/impeccable critique` or `/impeccable audit` on the affected page, use `/impeccable typeset`, `layout`, `animate`, `polish`, `harden`, and `adapt` as the roadmap phase calls for them, and run `impeccable detect` once on the changed files when a UI slice is finished. Regenerate `DESIGN.md` with `/impeccable document` at the end of Phase 1 and the end of Phase 7, from the built system. Apply only recommendations that fit this design system; detector output is not a mandate. Do not add a frontend framework or introduce new dependencies. Prefer one cohesive, reviewable slice per PR over sweeping visual churn. Record which Impeccable guidance was applied and what was intentionally rejected in the PR summary. If Impeccable is unavailable, say so and continue with `docs/DESIGN_SYSTEM.md`; do not claim to have used it.

## Git and pull-request workflow

1. Work from current GitHub `main`, unless a different GitHub base is explicitly justified.
2. Create a focused feature branch, for example `ui/<short-task-name>`. Never commit directly to `main`.
3. Keep the diff front-end-only. If backend/API changes are necessary, stop and propose the contract rather than editing protected files.
4. Add/update focused UI tests where behavior changes. Understand what existing tests protect; never delete or weaken regression assertions merely to make a change pass.
5. Run relevant available checks. Follow `docs/TEST_PLAN.md`; run focused tests and any relevant syntax checks. **Never run the full unit suite** (owner rule, 2026-10-20): the owner runs it independently and CI runs it on the PR head. Report the exact commands and actual results, and never report a full-suite result you did not observe.
6. Review the complete diff and changed-file list. Verify no protected files, API contracts, security rules, or domain behavior changed.
7. Open a PR against `main`. Include purpose, changed files, acceptance criteria, tests actually run, limitations, and screenshots or before/after notes for visual changes.
8. Do not merge, publish images, deploy, alter branch protection, disable CI, or bypass required checks. The assistant owns cross-layer review, release controls, merge coordination, and project-level verification.
9. Never force-push, overwrite unrelated work, or delete branches/worktrees without explicit authorization. If `main` advances, update the branch safely and rerun relevant checks.

## Current assigned work — the Chart Rundown redesign

Implement `docs/REDESIGN_ROADMAP.md` in order, one phase item per PR. Phase 0 (baseline) and Phase 1 (tokens, self-hosted fonts, icon sprite) come first; do not start a later phase before its predecessor is merged unless the roadmap says the items are independent. The earlier "one focused polish" task and the backlog items recorded in `docs/UI_BACKLOG_EXECUTION.md` are history, not the current queue.

Each PR must:
- name the roadmap phase and item, the `docs/DESIGN_SYSTEM.md` sections applied, and acceptance criteria before implementation;
- stay within the files allowed above, with no backend, API, authentication, acquisition, or domain behavior change;
- follow the per-PR checklist in `docs/REDESIGN_ROADMAP.md` section 5 (checks, five-width rendering, keyboard, console and network, exact-head manual checklist);
- update `docs/REDESIGN_ROADMAP.md` (status and PR link) and `docs/UI_BACKLOG_EXECUTION.md` in the same PR;
- include before/after screenshots and the Impeccable guidance applied and rejected;
- not be merged, published, or deployed by the author.

If a phase needs a new endpoint, field, or server behavior, stop at a contract proposal in the PR (roadmap section 6) and do not edit protected files.

## Testing and acceptance checklist

- UI-facing changes require passing automated checks on the exact PR-head SHA, followed by manual browser testing against that exact SHA using `docs/LOCAL_UI_TESTING.md` and `docs/TEST_PLAN.md`.
- Use the documented isolated test helper, sandbox music/download paths, and disabled slskd for ordinary UI checks. Never point UI testing at live download folders or perform destructive acquisition actions on real data without explicit authorization.
- Consider login/setup, navigation, artwork, discovery, album details, settings, Get/request state, acquisition cards, empty/loading/error/recovery states, performance, and browser/server errors as relevant to the change. Record skips as skips, not passes.
- Add tests for changed client behavior and preserve existing assertions. Server-side safety remains enforced and tested in backend/domain tests; browser checks do not replace those tests.
- If the PR head changes after manual testing, retest the new SHA or state clearly that the report covers the earlier SHA.
- Report implemented, automated-tested, browser-tested, merged, published, deployed, and runtime-verified as separate states. A merge or CI pass is not deployment evidence.

## Handoff format

At completion, provide the PR URL, branch, exact head SHA, files changed, tests/checks actually run, manual UI report if required, known limitations, and the next action. Do not claim a check passed unless its result was observed. If blocked by a missing backend contract or protected-file change, describe the proposal and stop.
