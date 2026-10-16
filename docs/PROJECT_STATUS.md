# Project status

Last reviewed: 2026-10-17 (service-default cleanup merged)

## Current focus

**Modularization roadmap complete.** The final audit found no remaining concrete correctness, safety, or testability gap that justifies another extraction. Remaining recommendation and acquisition code is documented orchestration/compatibility wiring. No further size-only extraction is planned.

The service-default audit found personal/private-network defaults for ListenBrainz, Navidrome, and slskd, and fixed regional recommendation behavior worth revisiting. PR #292 removed the unintended personal/network defaults and added regression assertions; recommendation behavior itself was not changed. Findings and proposed next-session work are recorded in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.

**Next action:** in the next session, use the recommendation-engine proposal document to select a focused behavior change and define tests before implementation.

## Delivery and verification state

- **Implemented / merged:** PR #292, merge commit `0db291970fbeff2ed192d73b04fe1efc8ecb3cb6`, based on final PR head `51f3a0e1ee55334020bc26793ca1d86a6c145a7c`.
- **CI:** all four required workflows passed on that exact PR head: `compile`, `test-and-build`, `container-smoke`, and `validate-container`. These cover syntax/size checks, the full unit suite and Docker build, isolated container smoke, and non-publishing multi-architecture validation.
- **Local tests:** not run in this session; CI provides the verification above.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP:** preserve the remaining MCP compatibility surface unless a separately approved migration changes it.

## Documentation map

| Need | Canonical document |
|---|---|
| Current snapshot and next action | This file |
| Recommendation engine audit and next-session proposals | `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` |
| Remaining extraction work and exit criteria | `docs/MODULARIZATION_ROADMAP.md` |
| Detailed historical PR, commit, and verification evidence | Root `PROJECT_LOG.md` |
| User-visible behavior and product invariants | `docs/REQUIREMENTS.md` |
| Required automated and manual verification | `docs/TEST_PLAN.md` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
