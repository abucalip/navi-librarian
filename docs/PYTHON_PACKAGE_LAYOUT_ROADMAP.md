# Python package layout roadmap

Last reviewed: 2026-10-21
Status: In progress; first move merged in PR #508.

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

## Completed moves

### PR #508 — Navidrome client package

- Merged to `main` as `f171a4e73915222292642ba17d6dcb568b8c929a` from exact tested head `a6fe1bd656f77ae4fbd65cb94c067949d14cf140`.
- Canonical implementation: `integrations/navidrome/client.py`; legacy `navidrome_client.py` is a tested re-export shim.
- Production imports, direct-import regression tests, and Docker package inclusion were updated. The application entry point was unchanged.
- All four required workflows passed on the exact PR head. Agent-side focused tests and syntax compilation were not run; see `PROJECT_LOG.md` for evidence and limitation.


## Current-main inventory and second move (2026-10-21)

### Evidence baseline

- Current GitHub `main` before this change: `2acb6d5fb2b52329df03cc73233fcc963c768f6d`.
- Refreshed dependency-map artifact: workflow run [39644560119](https://github.com/abucalip/navi-librarian/actions/runs/39644560119), artifact `modularization-dependency-map`, SHA-256 `8844d4cf9b10595837068cc32569be990cbfa236be6aa6b77911246fb7e35562`. The artifact was reviewed as a local audit input, not committed as tracked generated output.
- The map covers 237 Python modules and records 67 root-level Python modules. It reports static AST imports, including imports inside functions; it does not resolve arbitrary string-based imports or dependency injection. The current tree and direct callers were inspected separately.
- Four required workflows passed on this exact baseline: syntax [39644560119](https://github.com/abucalip/navi-librarian/actions/runs/39644560119), Docker packaging [39644560099](https://github.com/abucalip/navi-librarian/actions/runs/39644560099), runtime smoke [39644560116](https://github.com/abucalip/navi-librarian/actions/runs/39644560116), and validation-only image [39644560399](https://github.com/abucalip/navi-librarian/actions/runs/39644560399). These are baseline results, not results for the package-move PR.

### Root-module inventory by responsibility

The root modules fall into these existing groups; these are inventory categories, not instructions to move whole groups together.

- **Acquisition (18):** `acquisition_candidate_queue`, `acquisition_candidate_start`, `acquisition_cleanup`, `acquisition_completion`, `acquisition_import`, `acquisition_import_service`, `acquisition_lifecycle`, `acquisition_monitor_payload`, `acquisition_orchestration`, `acquisition_progress_accounting`, `acquisition_progress_snapshots`, `acquisition_recovery`, `acquisition_request_coordinator`, `acquisition_search_diagnostics`, `acquisition_source_switch`, `acquisition_state`, `acquisition_watcher`, `acquisition_watcher_startup`. High safety sensitivity; do not combine with provider moves.
- **Discovery (20):** `discovery_allocation_contract`, `discovery_batch_metadata`, `discovery_candidate_gathering`, `discovery_candidate_supply`, `discovery_classics_candidates`, `discovery_classics_genres`, `discovery_classics_ratings`, `discovery_deep_dive_candidates`, `discovery_lb_tag_lane`, `discovery_library_snapshot`, `discovery_list_payload`, `discovery_mmr`, `discovery_new_releases`, `discovery_personal_allocator`, `discovery_recommendation_payload`, `discovery_recommendations`, `discovery_refresh`, `discovery_snapshot`, `discovery_store`, `discovery_tag_queries`. Several are high-fan-in or orchestration modules; select seams only after caller-level review.
- **Recommendation support (7):** `recommendation_cooldown`, `recommendation_diagnostics`, `recommendation_feedback`, `recommendation_mmr_evaluate`, `recommendation_profile_comparison`, `recommendation_replay`, `recommendation_run_metrics`. Keep shared metric imports and replay contracts stable.
- **External providers (10):** `lastfm_client`, `listenbrainz_client`, `listenbrainz_popularity`, `musicbrainz_album_year`, `musicbrainz_rating_client`, `slskd_client`, `slskd_quality`, `slskd_search`, `slskd_search_polling`, `slskd_transfers`. These are not one interchangeable group: each provider and its caller/test contracts must be traced separately.
- **Settings, paths, metadata, and policy (10):** `data_directory`, `diagnose_categories`, `listening_profile`, `metadata_cache`, `music_paths`, `music_tag_audit`, `read_only_command_policy`, `server_source_redaction`, `service_settings`, `settings_persistence`. Several are cross-cutting or path/state-sensitive; avoid a catch-all package.
- **Legacy server and Navidrome compatibility (2):** `navidrome_server`, `navidrome_client`. The server remains the legacy adapter and must not be moved as part of a provider extraction; the client shim is retained from PR #508.

### Selected boundary: MusicBrainz integration

The second move groups `musicbrainz_album_year.py` and `musicbrainz_rating_client.py` into `integrations/musicbrainz/`.

- The refreshed AST map showed exactly one production import site per module: `app/api/metadata.py` for album years and `navidrome_server.py` for rating lookups. Each also had one focused direct-import test module.
- Both modules call the MusicBrainz service, have no `__file__`-based filesystem assumptions, and have no repository-local dependencies except the rating client's lazy metrics import. No dynamic import or source-reading test was identified for either module in the current AST/caller audit.
- The Dockerfile already copies `integrations/`; its explicit root-module COPY list removes the moved album-year module. The rating module remains as a small compatibility shim because the legacy server imports it by its old path; the shim delegates to the canonical implementation.
- The album-year production import and direct-import test use the canonical package path. The rating test covers the canonical implementation and the compatibility shim. The package move changes no request behavior or cache policy.
- `slskd_*` remains a separate future candidate, not a size-driven bulk move. The five modules have several direct tests and legacy-server call sites; do not move them until their exact wrappers and path contracts are reviewed.

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

## Next task handoff

See the **Current handoff: Python module package layout** section at the top of `CLAUDE_CLI.md`. After PR #508, refresh the dependency map on current main and complete the remaining root-module inventory (production/test callers, dynamic imports, AST/source-reading tests, path assumptions, Docker/CI references). Then select one cohesive next package move with a documented caller map; do not bulk-move files or rewrite behavior.
