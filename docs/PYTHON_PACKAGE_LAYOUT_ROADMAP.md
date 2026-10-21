# Python package layout roadmap

Last reviewed: 2026-10-21
Status: In progress; provider integration moves merged in PRs #508, #509, #511, #512, #513; recommendation replay/diagnostics package merged in PR #514.

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


## PR #509 closeout and next candidate (2026-10-21)

- PR #509 squash-merged as `8fe825a41c0122bd3fd6d3260ca8978cdbf0d27f`; exact tested head `c045865fea13e8944512fc5c987e609cbc41e443`.
- The canonical MusicBrainz helpers now live under `integrations/musicbrainz/`. The root `musicbrainz_rating_client.py` remains intentionally as a compatibility shim for the legacy server. The album-year root module was removed, reducing root-level Python modules from 67 to 66.
- Required CI passed on the exact PR head: syntax 39646429894, Docker packaging/full unit suite/build 39646429876, container smoke 39646429872, and validation-only multi-architecture image 39646429885. Agent-side focused tests and `py_compile` were not run because a fresh checkout was unavailable.
- Next candidate is the slskd integration, but no move is pre-approved. Audit `slskd_client.py`, `slskd_search.py`, `slskd_search_polling.py`, `slskd_transfers.py`, and `slskd_quality.py` with all callers, direct tests, dynamic imports, legacy-server compatibility, path assumptions, and Docker/CI references. Decide whether one package or a smaller boundary is justified before implementation.
- Publishing, deployment, and production-runtime verification remain paused/unperformed.


## PR #511 — slskd integration package move (2026-10-21)

- Current source baseline: `main` SHA `ea4d50e2384617ba365d11b93f5f4f789af6e019`; dependency-map artifact generated by the syntax workflow on audit head `8ba095c17040ea5dd40ab19ad36e132acb4ab2ee` (the application source is unchanged from that main baseline). Artifact ID `12368421891`, SHA-256 `22440f9cabed53f77f21abbdeb0593a9553fbdcc5bc0791d0ff46498d5185ca5`.
- The AST map confirms all five slskd modules are independent of repository-local modules. Direct callers in `navidrome_server.py` are the top-level transfer-module import and lazy imports for connection, quality, search, transfer lookup, and polling. The five helpers do not resolve files relative to their module paths; the search helper uses `Path` only to normalize filename strings.
- Direct-import behavior coverage exists in `tests/test_slskd_client.py`, `tests/test_slskd_candidates.py`, `tests/test_slskd_search.py`, `tests/test_slskd_search_modules.py`, `tests/test_slskd_search_polling.py`, `tests/test_slskd_transfer_lookup.py`, `tests/test_slskd_transfers.py`, and `tests/test_quality_priority.py`. The quality tests were found in these files; there is no `tests/test_slskd_quality.py`.
- Move under review in PR #511: canonical modules now live in `integrations/slskd/`; legacy-server adapters are preserved, all identified direct test imports are switched to canonical paths, Docker uses its existing `integrations/` copy, and the syntax workflow compiles the moved modules. No root-level compatibility shims are retained because repository AST/caller evidence found no remaining production/test imports that require them.
- Root-level Python module count is verified at 61 on code head `664639724ef9d1cbf5edd1603a41ccb14a372ce3` (down from 66). All four required workflows passed on that exact code head:
  - Python syntax/acquisition safety: [39649449299](https://github.com/abucalip/navi-librarian/actions/runs/39649449299)
  - Docker packaging, full unit suite and image build: [39649449147](https://github.com/abucalip/navi-librarian/actions/runs/39649449147)
  - Container runtime smoke: [39649449405](https://github.com/abucalip/navi-librarian/actions/runs/39649449405)
  - Validation-only multi-architecture image: [39649449373](https://github.com/abucalip/navi-librarian/actions/runs/39649449373)
- This verification commit updates documentation only, so the workflows must be checked again on the resulting final PR head before merge. Agent-side focused tests and `py_compile` were not run because no fresh checkout was available. Do not merge without explicit owner instruction. Publishing/deployment remain paused.


## PR #511 closeout — slskd integration package (2026-10-21)

- Squash-merged to `main` as `84fbb68afa7929a0bedae4e178d37ad2b6255c5a` from exact final PR head `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`.
- The five canonical helpers now live under `integrations/slskd/`. Legacy `navidrome_server.py` adapter functions remain and delegate to canonical imports. Direct-import tests, Docker package regression coverage, and the syntax workflow compile list were updated.
- Root-level Python module count is 61 after the move, down from 66 before it. No compatibility shims remain for the old five root paths because the caller audit found no production/test imports that still required them.
- All four required workflows passed on exact final PR head `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`: syntax/acquisition safety [39649756998](https://github.com/abucalip/navi-librarian/actions/runs/39649756998), Docker packaging/full unit suite/build [39649757098](https://github.com/abucalip/navi-librarian/actions/runs/39649757098), container runtime smoke [39649756971](https://github.com/abucalip/navi-librarian/actions/runs/39649756971), and validation-only multi-architecture image [39649757030](https://github.com/abucalip/navi-librarian/actions/runs/39649757030).
- Docker packaging CI ran the full unit suite successfully. Agent-side focused tests and `py_compile` were not run because no fresh isolated checkout was available. Publication, deployment, and production runtime verification remain unperformed.
- Next: refresh the dependency map on post-merge `main`; audit `lastfm_client.py` and its callers as the next candidate, keeping ListenBrainz as a separate provider boundary. Do not move code until the current-main caller/path/test/packaging audit supports it.


## Last.fm integration package move (2026-10-21, PR #512 merged)

- Baseline: `main` `13790f8`, four workflows green. The AST map plus direct grep of the tree found: one production importer (`navidrome_server.py`, top-level import, adapters `_lastfm_cached_call`, `_lastfm_top_albums`, `_lastfm_artist_genres`, `_lastfm_similar_artists`, album popularity), one direct test module, no lazy/dynamic/string imports, no `__file__`/path use, no workflow or script reference other than the syntax compile list, and the Docker root `COPY` list.
- Dependencies: `recommendation_run_metrics` and `discovery_recommendations.music_key` (both stdlib-only leaves, no cycle). Same direction as the existing MusicBrainz and ListenBrainz helpers, which lazily import `recommendation_run_metrics`.
- Result: canonical module `integrations/lastfm/client.py`; no root shim (no remaining importer needs the old path); test and compile list use the canonical path; Docker `COPY` entry removed; regression test asserts the package is copied and the old root file is gone. Root-level Python modules: 60.
- ListenBrainz is not bundled: `listenbrainz_client` and `listenbrainz_popularity` have separate callers (including `discovery_candidate_gathering.py` and lazy imports in `navidrome_server.py`) and tests; audit next as its own boundary.
- PR #512. CI on code head `76e5979d` (before this docs-only evidence commit): syntax [39652945862](https://github.com/abucalip/navi-librarian/actions/runs/39652945862), Docker packaging/full unit suite/build [39652945820](https://github.com/abucalip/navi-librarian/actions/runs/39652945820), container smoke [39652945713](https://github.com/abucalip/navi-librarian/actions/runs/39652945713), validation-only multi-architecture [39652945728](https://github.com/abucalip/navi-librarian/actions/runs/39652945728): all passed. PR is #512; the final head after this commit is re-verified in the PR checks.
- Merged as `7282cbb740dba6e27fa79aecfe0de5519c18d859` from exact final head `84b4f04b27025f35d1f8f353b152a78ee886ef59` (owner named PR 512). Next: ListenBrainz audit (see `CLAUDE_CLI.md`); no move pre-approved.

## ListenBrainz integration package move

- Audit (current `main` `0d26c9b`): `listenbrainz_client` imports only `httpx` plus a lazy `recommendation_run_metrics` leaf; `listenbrainz_popularity` is stdlib plus the same lazy leaf; neither imports the other or any root domain module (no cycle). Callers: `navidrome_server.py` (top-level client import, `set_token_source` wiring, `recent_listens` adapter, lazy imports of `request_headers` and the popularity helpers) and `discovery_candidate_gathering.py` (`request_headers`). Tests: `test_listenbrainz_client`, `test_listenbrainz_popularity`, `test_discovery_listenbrainz_headers`, `test_recommend_new_music_characterization` (string patch target). Docker: two explicit `COPY` entries.
- Result: `integrations/listenbrainz/client.py` and `integrations/listenbrainz/popularity.py` (new package `__init__.py`); no root shims; canonical imports in callers and tests; the string patch target now names the canonical module; the two Docker `COPY` entries are removed (the `integrations/` directory copy covers them); regression test asserts packaging and absence of the root files. Token-source and header contracts, request shapes and cache keys unchanged. Root Python modules 58.
- Not changed: `discovery_lb_tag_lane.py`, `discovery_batch_metadata.py` and `discovery_candidate_gathering.py` stay in the root (domain logic that calls ListenBrainz, not provider clients).
- Merged as `4e392e6660706191d080a5a2e9c66739377a5c33` from exact final head `935d8984002bc6d690a2a6c09c315816dea9e16e` (owner named PR 513); four required workflows passed on it. Next: re-inventory remaining root modules and pick the next boundary (see `CLAUDE_CLI.md`); no move pre-approved.

## Recommendation replay/diagnostics package move (PR #514 merged)

- Audit (`main` `bbe4104`): the seven `recommendation_*` modules are not one boundary. `recommendation_run_metrics` is a cross-cutting leaf used by the provider clients and discovery; `recommendation_cooldown` and `recommendation_feedback` are tied to the discovery group (design note needed). They stay in the root.
- Moved to the new `recommendation/` package: `replay.py`, `diagnostics.py`, `mmr_evaluate.py`, `profile_comparison.py` (no root shims; no remaining importer needs the old paths). Callers updated: `navidrome_server.py` (lazy imports), `discovery_store.py` (lazy import), `scripts/recommendation_replay.py`, tests.
- Path contract: `replay._REPOSITORY_ROOT` used `Path(__file__).parent`; it is now `.parent.parent` so the "capture must be outside the repository" check and the `git rev-parse` cwd still refer to the repository root.
- CLIs are now run as `python -m recommendation.replay`, `-m recommendation.mmr_evaluate`, `-m recommendation.profile_comparison` (TEST_PLAN and diversity roadmap updated; archived findings keep the historical commands).
- Docker: new `COPY recommendation/` line; the two root modules removed from the explicit list. Syntax workflow compile list updated. Packaging regression test added. Root Python modules: 54.
- Focused tests run locally: replay_capture, diagnostics, mmr_evaluate, profile_comparison, docker_packaging, recommend_new_music_characterization, discovery_store; `py_compile` on changed files; `check_server_size.py` OK. Full suite not run.

- Merged as `431c152642809e2aad1a36a556ac47610d0ddaa2` from exact final head `b636fcf2298f27b76befc3285034fe03285a32a0` (owner named PR 514); four required workflows passed on it (compile 39659386420, test-and-build 39659386566, container-smoke 39659385916, validate-container 39659386022). Next: audit the settings/paths group; the discovery and acquisition groups still need a design note before any move.
