# Project status

Last reviewed: 2026-10-17 (MCP retirement PR #296 merged; repository-level closeout recorded)

## Current focus

**Modularization roadmap complete.** The final audit found no remaining concrete correctness, safety, or testability gap that justifies another extraction. Remaining recommendation and acquisition code is documented orchestration/compatibility wiring. No further size-only extraction is planned.

The service-default audit found personal/private-network defaults for ListenBrainz, Navidrome, and slskd, and fixed regional recommendation behavior worth revisiting. PR #292 removed the unintended personal/network defaults and added regression assertions; recommendation behavior itself was not changed. Findings and proposed next-session work are recorded in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.

**MCP retirement:** PR #296 is merged at `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. The registry, SDK dependency, standalone transport/startup path, Docker registry inclusion, and unrelated Proxmox MCP entry point were removed; shared web/service logic and command-policy safety tests remain. The four required workflows were reported passing on the final PR head. See `docs/MCP_RETIREMENT_PLAN.md` for the consumer audit and closeout.

**Recommendation improvement:** PR #298 adds pool-fingerprint diagnostics and a deterministic offline metrics harness without ranking changes. CI passed on code head `57011aa17b798b9173dfa9b1a3bc493a4a29f9a2` (596 tests, all four workflows); documentation closeout and a real captured baseline remain outstanding. The checked-in replay fixture is synthetic and proves harness determinism only. Publishing and deployment remain paused.

## Delivery and verification state

- **MCP retirement plan merged:** PR #295, final PR head `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`, merge commit `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- **CI on exact PR head:** all four required workflows passed: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remains paused.
- **Local tests:** not run; this was a documentation-only planning change.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP retirement:** repository-level plan complete; PR #296 merged at `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. Four required workflows were reported passing on the final PR head. External client/config migration and production runtime are unverified.

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
