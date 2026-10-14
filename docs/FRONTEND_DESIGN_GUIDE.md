# Front-end design guide

Last updated: 2026-10-14

This is the canonical, agent-independent design reference for Navidrome Librarian's web UI. Read it before planning or implementing any front-end change. Root `AGENTS.md` defines mandatory entry instructions, ownership, and protected paths; this document defines the visual direction, design workflow, and prioritized UI backlog.

## 1. Product objective

Make Navidrome Librarian feel like a deliberately designed, specialist music-discovery and collection-management application—not a generic AI SaaS dashboard. Prioritize identity, typography, composition, hierarchy, usability, and detail over decoration. Improve clarity, speed, accessibility, responsive behavior, and reliability while preserving the established API, authentication, and domain behavior.

The interface helps a user explore their Navidrome library and listening taste, discover music, and request acquisitions through existing backend services. The UI must present those capabilities clearly without duplicating discovery, recommendation, acquisition, or import logic in browser code.

## 2. Established visual identity

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
- Unnecessary icons, emojis, badges, or colorful status pills for every metadata value.
- Gratuitous animation, decorative noise, or dashboard grids imposed on every screen.
- One-off styles that duplicate existing tokens or component behavior.
- External asset dependencies, analytics, trackers, frontend frameworks, build systems, or new packages without approval.

A visual treatment is justified when it improves hierarchy, comprehension, feedback, or interaction—not merely because a design tool suggests it.

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

Use Impeccable as a critique and implementation aid when available in ZCode. Start with its critique/audit guidance before styling. Use focused guidance such as `polish`, `layout`, `typeset`, `quieter`, or `distill` when appropriate. Consider its design-system, hierarchy, spacing, typography, contrast, responsive, and accessibility recommendations.

Apply only recommendations that fit this product and its existing components. Do not run broad redesign commands blindly or treat detector output as a mandate. Prefer one cohesive, reviewable improvement over sweeping visual churn. In the PR summary, record the guidance applied and important recommendations intentionally rejected. If Impeccable is unavailable, state that limitation and continue using this guide; do not claim to have used it.

## 6. Ownership and architecture boundaries

Root `AGENTS.md` is authoritative for allowed files and protected ownership. In brief, normal front-end implementation is limited to:

- `static/app.css`
- `static/app.js`
- `static/login.css`
- `static/login.js`
- `app/templates/*.html`
- narrowly scoped front-end tests/fixtures under `tests/`

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

## 8. Prioritized design backlog

This is the working front-end backlog, reconciled with PR #66 and its follow-up verification recorded in the project documentation. Re-inspect current `main` and open UI PRs before starting an item; update this list when priorities or completion evidence change.

1. **State craft** — establish consistent, purposeful loading, empty, error, success, and recovery presentation across the app. Preserve correct semantics and actionable feedback.
2. **Per-section layouts** — refine artist exploration, library, acquisition, and settings into distinct task-appropriate compositions that share the established design language.
3. **Get/request button consolidation** — align the modal, artwork-overlay, and card-action variants into one consistent interaction pattern without changing API or acquisition semantics.
4. **Type/token cleanup** — consolidate duplicated values into shared tokens and tighten the type scale without broad visual churn.
5. **Responsive controls** — improve navigation, filters, and acquisition cards at narrow viewport widths.
6. **Continue visual audit** — after the above, inspect for the next highest-impact issue and re-prioritize based on evidence.

**Completed:** Login-page alignment (PR #66, merged as recorded in `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md`). The page now follows the app's design tokens, typography, button treatment, and focus styling. Manual verification reported desktop/narrow viewport and failed-sign-in behavior passing; keyboard focus modality and the first-run setup variant were explicitly recorded as skips in the test report. Do not reopen this item unless new evidence identifies a regression or remaining defect.

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
- [ ] The PR identifies the backlog item addressed and any backlog changes.

## 10. Source of truth and maintenance

This file on GitHub `main` is the canonical design guide. Do not rely on PR #66 comments, chat history, local-only files, or an agent-specific memory as the sole source of design instructions. Root `AGENTS.md` must link here, and the development workflow and test plan must keep pointing to this guide.

When a design decision or priority changes, update this guide and the relevant project status/log documentation through a focused PR. Keep historical verification evidence in the project log; do not convert skipped or unverified work into a pass.
