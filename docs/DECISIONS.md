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
