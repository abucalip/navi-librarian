# Project status

Last reviewed: 2026-10-17 (MCP removal PR prepared; verification pending)

## Current focus

**Modularization roadmap complete.** The final audit found no remaining concrete correctness, safety, or testability gap that justifies another extraction. Remaining recommendation and acquisition code is documented orchestration/compatibility wiring. No further size-only extraction is planned.

The service-default audit found personal/private-network defaults for ListenBrainz, Navidrome, and slskd, and fixed regional recommendation behavior worth revisiting. PR #292 removed the unintended personal/network defaults and added regression assertions; recommendation behavior itself was not changed. Findings and proposed next-session work are recorded in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.

**MCP retirement implementation:** the focused removal branch deletes the MCP registry, SDK dependency, and standalone transport; preserves the shared service functions; adds web-startup scheduler lifecycle; and replaces registry tests with MCP-free architecture regressions. The audit and changed-file dispositions are recorded in `docs/MCP_RETIREMENT_PLAN.md`. PR #296 is open; exact-head CI and merge remain pending.

**Next action:** verify focused tests and all four required workflows on the exact final PR head, then review and merge only if every gate passes.

## Delivery and verification state

- **MCP retirement plan merged:** PR #295, final PR head `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`, merge commit `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- **CI on exact PR head:** all four required workflows passed: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remains paused.
- **Local tests:** not run; this was a documentation-only planning change.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP:** removal implementation is prepared on `retire/remove-mcp-runtime`; exact PR-head verification and merge remain pending.

## Documentation map

| Need | Canonical document |
|---|---|
| Current snapshot and next action | This file |
| MCP retirement evidence and migration gates | `docs/MCP_RETIREMENT_PLAN.md` |
| Recommendation engine audit and next-session proposals | `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` |
| Remaining extraction work and exit criteria | `docs/MODULARIZATION_ROADMAP.md` |
| Detailed historical PR, commit, and verification evidence | Root `PROJECT_LOG.md` |
| User-visible behavior and product invariants | `docs/REQUIREMENTS.md` |
| Required automated and manual verification | `docs/TEST_PLAN.md` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
