# Project status

Last reviewed: 2026-10-17 (MCP retirement plan drafted)

## Current focus

**Modularization roadmap complete.** The final audit found no remaining concrete correctness, safety, or testability gap that justifies another extraction. Remaining recommendation and acquisition code is documented orchestration/compatibility wiring. No further size-only extraction is planned.

The service-default audit found personal/private-network defaults for ListenBrainz, Navidrome, and slskd, and fixed regional recommendation behavior worth revisiting. PR #292 removed the unintended personal/network defaults and added regression assertions; recommendation behavior itself was not changed. Findings and proposed next-session work are recorded in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.

**MCP retirement planning:** `docs/MCP_RETIREMENT_PLAN.md` records the current MCP surface, consumer-audit requirements, focused removal approach, regression expectations, required CI gates, and definition of done. This is planning only; no MCP implementation has been removed in this change.

**Next action:** audit remaining MCP consumers and references on current `main`, then implement a focused retirement PR without removing shared web/service behavior.

## Delivery and verification state

- **Previously implemented / merged:** PR #292, merge commit `0db291970fbeff2ed192d73b04fe1efc8ecb3cb6`, based on final PR head `51f3a0e1ee55334020bc26793ca1d86a6c145a7c`.
- **Current change:** documentation-only MCP retirement plan; branch `docs/mcp-retirement-plan`. PR/merge/CI status to be recorded after verification.
- **Prior CI evidence:** all four required workflows passed on PR #292's exact final head. This is not verification of the current documentation commit.
- **Local tests:** not run for this documentation-only planning change.
- **Publishing:** paused; multi-architecture validation must remain non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP:** full retirement remains pending the separate audit, implementation, and required verification described in `docs/MCP_RETIREMENT_PLAN.md`.

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
