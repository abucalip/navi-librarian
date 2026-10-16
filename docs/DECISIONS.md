# Architecture and workflow decisions

Last updated: 2026-10-14

Record decisions here when they constrain future implementation. Add new entries rather than silently rewriting history.

## D-001 — Keep existing discovery logic as the domain layer

**Decision:** The FastAPI web UI calls existing librarian functions in `navidrome_server.py` rather than maintaining a second copy of discovery/acquisition logic.

**Reason:** Avoid behavior drift between MCP and web access.

**Consequence:** Changes to shared functions require regression testing for both web and MCP behavior.

## D-002 — Web UI is a separate containerized service

**Decision:** Run the web app in Docker alongside, but separate from, Navidrome and slskd.

**Reason:** Keep service responsibilities isolated and make upgrades/rollback independent.

**Consequence:** Use reachable service URLs/network names and explicit bind mounts; do not bundle duplicate Navidrome or slskd instances into this image.

## D-003 — Persistent state lives outside the image

**Decision:** Mount a named volume at `/data` for the application database and authentication key.

**Reason:** Container replacement must not reset the account or saved state.

**Consequence:** Never delete this volume during routine upgrades or rollback. Back it up before migrations.

## D-004 — Separate implementation from verification status

**Decision:** Track Planned, In progress, Implemented, Tested, Merged, Deployed, and Verified as distinct states.

**Reason:** Code on a branch, code merged to `main`, and behavior running successfully on the VM are different facts.

**Consequence:** Every handoff must state the exact branch/commit, tests actually run, deployment evidence, and outstanding uncertainty.

## D-005 — Use narrow, reviewable changes

**Decision:** Prefer feature/fix branches and small diffs; use isolated worktrees for experiments. Do not reset, force-push, or overwrite unrelated local changes without explicit approval.

**Reason:** The development process has multiple active checkouts and in-progress work that must not be lost.

**Consequence:** Before editing, inspect branch, status, recent commits, and diff. Before handoff, inspect the final diff and tests.

## D-006 — Acquisition dismissal is a destructive operation

**Decision:** The requested dismiss behavior may delete the files associated with the acquisition's album folder.

**Reason:** The user explicitly requested cleanup when dismissing an acquisition card.

**Consequence:** Resolve the exact folder under an approved root; reject traversal, symlink escapes, ambiguous matches, and unrelated paths. Add positive and negative tests. Do not mark this behavior Verified without a controlled test.

## D-007 — Keep external metadata optional

**Decision:** Artwork, release-year, biography, and third-party music metadata enrich discovery but must not be required for the core recommendation flow.

**Reason:** External services can be unavailable, slow, ambiguous, or missing an album.

**Consequence:** Use exact/normalized matching where appropriate, bounded timeouts/caches, and graceful fallbacks.

## D-008 — Private registry errors are not tag errors

**Decision:** Treat GHCR `unauthorized` as an access/visibility/authentication issue until proven otherwise.

**Reason:** Choosing a commit tag or digest cannot grant registry access.

**Consequence:** Verify package visibility or authenticate before changing deployment tags.

## D-009 — GitHub is authoritative; assistant owns code changes and commits

**Decision:** GitHub is the sole source of truth for code, commits, pull requests, documentation, and release history. The assistant alone modifies project code and creates commits. The user's local checkout is for fetching and testing GitHub revisions, not for originating authoritative code changes.

**Reason:** Keep a single auditable history and avoid divergence between a local testing baseline and the shared repository.

**Consequence:** Base authoritative work on GitHub refs. Use focused GitHub branches and PRs; report exact commit SHAs and actual CI results. The user tests a specific GitHub branch/commit locally and reports results; the assistant makes any required fix on GitHub. Do not merge local-only commits back into GitHub or merge local `main` into a PR simply to reconcile histories. For testing against a divergent local baseline, use a temporary/disposable branch or worktree and never push that test-only combination. Local changes must be inspected and preserved, not reset or discarded without explicit authorization. Merge, image publication, deployment, and production verification remain separate states.


## D-010 — Separate album import filesystem mechanics from acquisition orchestration

**Decision:** Put staging, verified-track movement, storage-identity checks, no-overwrite behavior, rollback, and import-manifest handling in the directly importable `acquisition_import.py` module. Keep acquisition status transitions, dismissal synchronization, candidate selection, and retry/failover orchestration in `navidrome_server.py`.

**Reason:** The filesystem transaction is safety-critical and benefits from deterministic temporary-directory tests independent of MCP/server initialization.

**Consequence:** Keep the legacy server helper as a compatibility wrapper that injects the existing strict completion matcher. Direct-import tests must exercise the module implementation; retain the broader lifecycle safety tests until orchestration is extracted separately. Do not change import semantics as part of this relocation.


## D-011 — Isolate cached discovery-list persistence

**Decision:** Put the SQLite read/write mechanics for cached discovery-list payloads in the directly importable `discovery_store.py`. Keep `_discovery_read_list` and `_discovery_write_list` as compatibility wrappers in `navidrome_server.py`, including the existing `_discovery_init()` call.

**Reason:** Discovery list storage can be regression-tested independently without importing the MCP server or initializing external services.

**Consequence:** The module owns only the `discovery_lists` table's read/write behavior. Feedback, acquisition state, settings, refresh locks, list building, and provider calls remain in the server for later focused extractions. Do not change payload shape, timestamp semantics, or cache/error behavior during relocation.


## D-012 — Separate discovery refresh coordination from list construction

**Decision:** Put the lock/dispatch/error/response coordination for cached discovery-list refreshes in directly importable `discovery_refresh.py`. Keep legacy `_discovery_refresh_personal` and `_discovery_refresh_other` entry points in `navidrome_server.py` as thin adapters.

**Reason:** Refresh control flow can be tested independently without importing MCP initialization or calling providers, while list-building and persistence remain distinct responsibilities.

**Consequence:** Inject existing locks, recommendation/list-builder callables, and the persistence wrapper. Preserve lock acquisition and release, list identifiers, response shapes, count fields, JSON-error handling, and error reporting. Do not move provider logic or alter list payload semantics in this extraction.


## D-013 — Split Claude front-end work from backend integration

**Decision:** Claude may implement UI-only changes in `static/app.css`, `static/app.js`, `static/login.css`, `static/login.js`, `app/templates/*.html`, and narrowly scoped UI tests/fixtures. Backend/domain/security, API contracts, application assembly, persistence, acquisition/import/filesystem safety, CI, packaging, release, and deployment remain outside that role. All work is proposed through GitHub PRs; the assistant owns cross-layer integration, release gates, and merge coordination.

**Reason:** The UI assets are now extracted into dedicated paths, enabling focused frontend iteration without allowing parallel agents to silently change server contracts or safety-critical behavior.

**Consequence:** Root `CLAUDE.md` is the operational instruction source for Claude. This decision supersedes only the single-agent ownership wording in D-009; it does not change GitHub authority, the local-testing-only rule, branch/PR requirements, or the distinction between merge, publication, deployment, and runtime verification.

## D-014 — Keep MCP registration outside the shared web service module

**Decision:** Keep the legacy MCP tool names and callables, but register them only in mcp_registry.py when the MCP entry point is explicitly run. The shared navidrome_server.py module must not import or initialize the MCP SDK merely because the web application needs its service functions.

**Reason:** The web application and MCP server share domain functions today, but importing the service should not itself load the MCP runtime. This is a safe incremental boundary before eventual MCP retirement.

**Consequence:** Keep an explicit ordered registry and regression tests for all existing tool names and callable references. Do not remove the MCP dependency, tool surface, or runtime entry point until web callers and release gates demonstrate that removal is safe.

**PR #138 verification record:** implementation/documentation head `fe71a9a19188a018a2ee65d5b313a99413d239f2` passed all four required workflows (syntax/acquisition safety `38783091362`, Docker packaging/full suite/build `38783091326`, runtime smoke `38783091309`, validation-only multi-architecture `38783091337`). The final documentation-updated PR head `05d0eaf9a2e1ca94f3f03251208059540d06772f` passed all four required workflows (syntax `38783296279`, Docker packaging/full suite/build `38783296173`, runtime smoke `38783296256`, validation-only multi-architecture `38783296249`) and PR #138 merged at `197863830471bbd63eed57a11cafd815aede7f00`.


## D-015 — Retire legacy source-patching and process-restart MCP tools

**Decision:** Remove `restart_server` and `apply_server_patch` from `navidrome_server.py` and the ordered MCP registry. Preserve the MCP runtime and all other registered tools.

**Reason:** The owner identified these as early-development legacy functions and requested removal if safe. Current-source inspection found no internal callers; they were exposed only as MCP tools. `restart_server` kills/relaunches a process on hardcoded port 8000, and `apply_server_patch` rewrites the running service's source file. Their risk outweighs the value of preserving these two legacy operations.

**Consequence:** Regression tests pin the registry at 25 unique tools and verify both retired functions are absent from the service module and registry. This does not retire MCP or authorize removal of other MCP capabilities. Reintroducing either tool requires a new explicit owner decision and security review.
