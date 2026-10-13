# Architecture and workflow decisions

Last updated: 2026-10-12

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
