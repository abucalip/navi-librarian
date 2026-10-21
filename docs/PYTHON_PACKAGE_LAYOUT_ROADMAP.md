# Python package layout roadmap

Last reviewed: 2026-10-21
Status: Planned; no module moves have been made under this roadmap.

## Goal

Reduce clutter from the many root-level Python modules by organizing related code into clear packages, while preserving Librarian's runtime behavior, supported web/API interfaces, tests, and Docker deployment. This is a package-layout improvement, not a rewrite and not a reason to reopen the completed `docs/MODULARIZATION_ROADMAP.md`.

GitHub is authoritative. All changes must be made on a branch from current GitHub `main`, reviewed in a focused PR, and verified against the exact final PR-head SHA.

## Constraints and known risks

- The application starts through `uvicorn app.main:app`; keep this entry point working unless a separately approved migration proves necessary.
- The Dockerfile explicitly copies `app/`, `static/`, and a long list of root-level Python modules. Moving files without updating packaging can cause container startup or runtime failures.
- Imports may be absolute, lazy, dynamic, or relied on by scripts/tests. Source-reading and AST tests may assume current paths.
- Configuration, static/template assets, data directories, and runtime file paths must not accidentally become relative to a new module directory.
- Preserve supported web/API contracts, persistence, side effects, acquisition/import safety, and existing service behavior. MCP runtime/registration is retired; do not restore it.
- Do not run the full unit suite as an agent. The owner and the Docker packaging CI workflow run it. Run focused tests, syntax checks, and applicable package/API checks.
- Publishing and deployment remain separate gated activities. This roadmap does not authorize either.

## Proposed direction (subject to repository inventory)

Use a small number of packages aligned to real responsibilities and existing boundaries. Possible groupings include:

- `app/`: current application assembly, routes, and web-layer dependencies; preserve `app.main:app`.
- `integrations/` or an existing equivalent: external-service clients (for example Navidrome, slskd, ListenBrainz, MusicBrainz, Last.fm), only if the inventory shows a cohesive package boundary.
- `services/` or an existing equivalent: application/domain workflows such as acquisition lifecycle/orchestration, settings persistence, and discovery/recommendation coordination, keeping each cohesive responsibility together.
- `tests/`: remain separate from production packages; update import fixtures and any source-path contracts deliberately.
- Root: keep project configuration, Docker/Compose files, scripts and documentation; retain only compatibility entry points when they serve a real purpose.

These are options, not a mandate to create every directory. Prefer existing `app/` structure and current domain boundaries where appropriate. Avoid a giant `core/` or `utils/` catch-all, circular imports, deep package nesting, and wrappers that add no compatibility value.

## Execution plan

### 1. Inventory and dependency map — first task

- Refresh `main`, recent commits, open PRs, and CI. Coordinate around any concurrent PRs before selecting a base.
- List all root-level Python modules and classify each by responsibility, import direction, callers, and likely destination.
- Trace production and test imports, including lazy/dynamic imports and imports inside functions.
- Identify CLI/ASGI entry points, public compatibility imports, source-reading/AST tests, path assumptions, Docker COPY/package inclusion, and CI scripts that name files directly.
- Check existing architecture and modularization decisions; do not repeat completed extractions.
- Produce a proposed move map with dependencies and risk, then choose one cohesive, low-risk first group. If no safe group is evident, stop for a design review.

**Deliverable:** a short inventory in the first PR description or a small roadmap appendix, plus one focused initial package move. Do not make a repository-wide move in one step.

### 2. Move one cohesive group per PR

For each batch:

1. Create a focused branch from refreshed `main`.
2. Move files without changing their business logic.
3. Add `__init__.py` only where required by the selected package design.
4. Update imports, lazy imports, test imports/fixtures, scripts, Docker COPY/package rules, and documentation references.
5. Keep compatibility shims only when actual callers require them; test both the new canonical import and any retained public/legacy import.
6. Add regression coverage for importability and relevant behavior. Do not weaken or delete tests merely because they assume old paths; replace source-layout assertions only when the layout itself is no longer a requirement and behavior remains covered.
7. Review all changed paths and search for stale references to moved modules.
8. Open a PR and verify required CI on its exact final head. Rebase/reconcile if main advanced, then re-run required CI on the final head.
9. Wait for explicit owner authorization naming the PR before merging. Refresh main before dependent batches.

Prefer a sequence of small, independently reviewable moves. Group modules only when their dependencies and responsibilities justify moving them together.

### 3. Verification for each move

- Focused unit/regression tests for affected modules and direct-import behavior.
- Python syntax checks and applicable static checks.
- Application import/startup and relevant API contract checks.
- Docker build/runtime smoke to prove the moved modules are present in the image and importable.
- Search for old paths in production code, tests, scripts, Docker/Compose, workflows, and docs.
- Review path resolution for static assets, templates, databases, configured data roots, and mounted media/download folders.
- Confirm no unrelated behavioral changes and no weakening of acquisition/import/deletion safety.
- Verify the four required workflows on the exact final PR-head SHA: Python syntax/acquisition safety, Docker packaging/full unit suite/build, isolated container runtime smoke, and validation-only multi-architecture image validation. Keep image validation non-publishing.
- Report focused tests actually run, skipped checks, exact SHA, CI evidence, and limitations. Never claim the full suite was run by the agent.

### 4. Closeout and maintainability check

After the planned moves:
- Confirm the root-level Python module count decreased for a meaningful reason and the resulting packages have clear, documented boundaries.
- Verify `uvicorn app.main:app`, Docker packaging/runtime, supported web/API contracts, and representative acquisition/discovery workflows.
- Search for stale import paths and redundant compatibility wrappers.
- Update `docs/PROJECT_STATUS.md`, root `PROJECT_LOG.md`, this roadmap, and architecture documentation only where the actual boundaries or decisions changed.
- Keep implementation, test/CI, merge, publication, deployment, and runtime-verification states distinct.

## Acceptance criteria

The effort is complete only when:

- Related Python modules live in logical packages rather than an arbitrary catch-all.
- Imports are explicit and no unexpected circular imports or import-time side effects were introduced.
- Existing application entry points and supported web/API behavior remain compatible.
- Docker and runtime packaging include every moved module and the application starts in the built image.
- Tests continue to cover behavior, import compatibility where needed, and safety-critical failure paths.
- The complete diff has been reviewed and required CI passed on the exact final PR heads.
- Documentation records the actual resulting layout, verified evidence, remaining exceptions, and merge SHAs.
- No publication, deployment, or production-runtime verification is inferred from successful tests or merges.

## First task handoff

See the **Current handoff: Python module package layout** section at the top of `CLAUDE_CLI.md`. The first task is inventory plus one carefully selected package move in a PR—not a bulk move and not a behavior rewrite.
