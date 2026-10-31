# Front-end design guide

Last updated: 2026-10-18

This is the canonical, agent-independent design reference for Discair's web UI. Read it before planning or implementing any front-end change. Root `AGENTS.md` defines mandatory entry instructions, ownership, and protected paths; this document defines interaction, accessibility, and boundary rules and the design workflow.

> **Redesign notice (2026-10-18).** The visual identity (color, type, icons, motion, layout) and the prioritized backlog are now defined by `docs/DESIGN_SYSTEM.md` and `docs/REDESIGN_ROADMAP.md`. Where this guide and those documents disagree about appearance, they win. Sections 4, 6, 7 and 9 remain in force for interaction, accessibility, boundaries and workflow.

## 1. Product objective

Make Discair feel like a deliberately designed, specialist music-discovery and collection-management application—not a generic AI SaaS dashboard. Prioritize identity, typography, composition, hierarchy, usability, and detail over decoration. Improve clarity, speed, accessibility, responsive behavior, and reliability while preserving the established API, authentication, and domain behavior.

The interface helps a user explore their Navidrome library and listening taste, discover music, and request acquisitions through existing backend services. The UI must present those capabilities clearly without duplicating discovery, recommendation, acquisition, or import logic in browser code.

## 2. Pre-redesign visual identity (superseded by `docs/DESIGN_SYSTEM.md`)

This section records the identity the shipped app still renders until each roadmap phase lands. It is no longer the target. Yellow and red, Barlow Condensed, IBM Plex Sans and Mono, 4–6px radii and the neutral grey ground are replaced by the Chart Rundown tokens, type, icons and layout. The product character (confident, functional, music-focused, artwork-led) carries over.

- **Foundation:** dark grey surfaces and backgrounds.
- **Accents:** yellow for deliberate emphasis, primary actions, and selected states; red for destructive actions and errors. Never communicate state by color alone.
- **Typography:** Barlow Condensed for display headings; IBM Plex Sans for interface text; IBM Plex Mono for technical metadata and compact labels.
- **Character:** confident, editorial, functional, music-focused—not decorative or template-like.
- **Artwork:** music artwork is a primary visual element in discovery. Preserve aspect ratio, use consistent sizing, and keep artist/album names readable.
- **Hierarchy:** establish a consistent type scale and spacing rhythm; keep secondary metadata quieter than titles and actions.
- **Composition:** use one coherent design language but allow artist exploration, library, acquisition, and settings to have layouts suited to their distinct tasks. Do not force every page into the same dashboard grid.
- **Existing components and tokens:** reuse the current design system before creating new patterns. Changes should strengthen it rather than casually replace it.

## 3. Anti-patterns to avoid

Do not introduce these by default:

- Purple/blue gradients, neon glows, or glassmorphism.
- Rounded cards around every section, nested cards, or excessive borders and shadows.
- Oversized headings or repetitive icon + heading + description layouts.
- Unnecessary icons, emojis, badges, or colorful status pills for every metadata value. (The approved Lucide sprite is for navigation and actions with labels; decorative icons are still out.)
- Gratuitous animation, decorative noise, or dashboard grids imposed on every screen.
- One-off styles that duplicate existing tokens or component behavior.
- Runtime third-party asset dependencies (CDN fonts, remote icons or scripts), analytics, trackers, frontend frameworks, build systems, or new packages without approval. Self-hosted fonts and the icon sprite named in `AGENTS.md` are approved.

A visual treatment is justified when it improves hierarchy, comprehension, feedback, or interaction—not merely because a design tool suggests it. `docs/DESIGN_SYSTEM.md` section 13 lists the anti-patterns specific to the new world.

## 4. Interaction, accessibility, and responsive craft

For affected components, consider and implement the relevant states: hover, focus, active, disabled, loading, success, empty, error, and recovery. Give actions clear feedback and prevent accidental duplicate submissions where appropriate. Do not claim success before the server confirms it, especially for acquisition or other consequential actions.

- Use semantic HTML and accessible names; controls must be keyboard-operable.
- Preserve visible focus indicators and sufficient contrast.
- Do not rely on color alone to communicate state.
- Test realistic long artist/album names, artwork, and metadata at desktop and narrow viewport widths.
- Avoid horizontal overflow, inaccessible controls, layout shifts, and unnecessary full-page reloads.
- Respect reduced-motion preferences when motion is used.
- Treat API/user-controlled text as untrusted; prefer safe DOM construction and text APIs over unsafe HTML insertion.
- Show loading, empty, success, and error states accurately; leave the interface usable after failed or slow requests.

Do not add mock behavior or invent backend endpoints/fields to make the UI appear functional.

## 5. Design-tool workflow: Impeccable

Use Impeccable as a critique and implementation aid when available in the working environment. Start with its critique/audit guidance before styling. Use focused guidance such as `polish`, `layout`, `typeset`, `quieter`, or `distill` when appropriate. Consider its design-system, hierarchy, spacing, typography, contrast, responsive, and accessibility recommendations.

Apply only recommendations that fit `docs/DESIGN_SYSTEM.md` and the existing components. The Chart Rundown direction is already chosen (`PRODUCT.md`, `.impeccable/surfaces/`); do not re-roll it. Do not run broad redesign commands blindly or treat detector output as a mandate. Prefer one cohesive, reviewable improvement over sweeping visual churn. In the PR summary, record the guidance applied and important recommendations intentionally rejected. If Impeccable is unavailable, state that limitation and continue using this guide; do not claim to have used it.

## 6. Ownership and architecture boundaries

Root `AGENTS.md` is authoritative for allowed files and protected ownership. In brief, normal front-end implementation is limited to:

- `static/app.css`
- `static/app.js`
- `static/login.css`
- `static/login.js`
- `app/templates/*.html`
- narrowly scoped front-end tests/fixtures under `tests/`, including the `*_ui_contract.py` files
- vendored self-hosted assets: `static/fonts/**`, `static/icons.svg`, `static/vendor/**` (with license files)
- the front-end design documents listed in `AGENTS.md`

Reading backend code or tests to understand behavior does not grant permission to edit them. Do not change application assembly, routes, authentication/security, API paths or schemas, domain services, discovery/recommendation logic, acquisition/import lifecycle, persistence, filesystem operations, dependencies, workflows, deployment, or project-wide safety/release controls without explicit approval and coordinated ownership.

The existing API is authoritative. If a UI need requires a new endpoint, field, or server behavior, stop and propose the user need, contract, failure cases, and reason the existing API is insufficient. Do not bypass server-side authorization or filesystem safety.

## 7. Required workflow for front-end changes

1. **Inspect:** read root `AGENTS.md`, this guide, and relevant sections of `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, and `docs/TEST_PLAN.md`. Inspect current GitHub `main`, recent commits, open PRs, relevant CI, source callers, and tests.
2. **Define:** state one narrow problem, why it matters, and observable acceptance criteria before implementation.
3. **Evaluate:** use Impeccable critique/audit when available; select a focused recommendation consistent with this guide.
4. **Implement:** branch from current GitHub `main` and make a focused front-end-only change. Preserve existing behavior outside scope. Add/update tests for changed client behavior.
5. **Review:** inspect the complete diff and changed-file list. Confirm protected files, API contracts, auth/security, acquisition behavior, and safety guarantees are unchanged.
6. **Automated verification:** run relevant focused tests, syntax checks, the full unit suite when feasible, and required CI workflows. Report exact commands and observed results; never infer a pass.
7. **Rendered verification:** after required automated checks pass, inspect the exact PR-head revision in the documented isolated local helper. Verify desktop and narrow viewport behavior, relevant interaction states, keyboard/focus behavior, and browser console/network/server errors. Use sandbox music/download paths and keep slskd disabled for ordinary UI tests. Never test destructive acquisition actions against real user data without explicit authorization.
8. **Refine and report:** fix observed defects, re-review the final diff, and open a PR with purpose, acceptance criteria, changed files, Impeccable guidance applied/rejected, before/after screenshots for visual changes, exact head SHA, tests actually run, manual UI report, limitations, and next action. Do not merge the PR yourself.

If the PR head changes after manual testing, retest the new SHA or explicitly state that the report covers an earlier SHA. Record implemented, automated-tested, browser-tested, merged, published, deployed, and runtime-verified as separate states. CI or a merge is not deployment evidence.

## 8. Backlog and roadmap

The working backlog is `docs/REDESIGN_ROADMAP.md` (Phases 0–7), applying `docs/DESIGN_SYSTEM.md`. Re-inspect current `main` and open UI PRs before starting an item, and update the roadmap's status and PR links in the same PR as the work.

**Previously completed (history, do not redo):** login-page alignment (PR #66), state craft, Get/request consolidation, per-section layouts for acquisition, deep dive, recommendations and classics, token naming and 44px targets, accessibility items C1–C7, skip link and tabs ARIA. Evidence and measurements are in `docs/UI_BACKLOG_EXECUTION.md`. The redesign restyles these without changing the behavior and accessibility properties they established.

## 9. Front-end PR acceptance checklist

- [ ] One clear user-facing design problem and rationale are stated.
- [ ] The change is focused and stays within authorized front-end paths.
- [ ] Existing design identity and relevant API/product behavior are preserved.
- [ ] Loading/empty/error/success and keyboard/focus states are handled where relevant.
- [ ] Desktop and narrow viewport behavior is verified against realistic content.
- [ ] Relevant tests, syntax checks, full unit suite when feasible, and exact-head CI are reported accurately.
- [ ] Rendered UI and browser console/network errors are inspected on the exact tested SHA.
- [ ] Before/after screenshots and Impeccable decisions are included for visual changes.
- [ ] Complete diff is reviewed; skipped checks and limitations are explicit.
- [ ] The PR identifies the roadmap phase and item addressed, the design-system sections applied, and any roadmap changes.

## 10. Source of truth and maintenance

This file on GitHub `main` is the canonical guide for interaction, accessibility, boundaries and workflow; `docs/DESIGN_SYSTEM.md` is canonical for appearance and `docs/REDESIGN_ROADMAP.md` for sequencing. Do not rely on PR #66 comments, chat history, local-only files, or an agent-specific memory as the sole source of design instructions. Root `AGENTS.md` must link here, and the development workflow and test plan must keep pointing to this guide.

When a design decision or priority changes, update this guide and the relevant project status/log documentation through a focused PR. Keep historical verification evidence in the project log; do not convert skipped or unverified work into a pass.
