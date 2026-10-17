# Project status

Last reviewed: 2026-10-17 (PR #298 replay fidelity fix under verification)

## Current focus

**Modularization roadmap complete.** The final audit found no remaining concrete correctness, safety, or testability gap that justifies another extraction. Remaining recommendation and acquisition code is documented orchestration/compatibility wiring. No further size-only extraction is planned.

The service-default audit found personal/private-network defaults for ListenBrainz, Navidrome, and slskd, and fixed regional recommendation behavior worth revisiting. PR #292 removed the unintended personal/network defaults and added regression assertions; recommendation behavior itself was not changed. Findings and proposed next-session work are recorded in `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.

**MCP retirement:** PR #296 is merged at `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. The registry, SDK dependency, standalone transport/startup path, Docker registry inclusion, and unrelated Proxmox MCP entry point were removed; shared web/service logic and command-policy safety tests remain. The four required workflows were reported passing on the final PR head. See `docs/MCP_RETIREMENT_PLAN.md` for the consumer audit and closeout.

**Recommendation Phase 0 is implemented but not complete.** Open PR #298 adds bounded pool diagnostics, synthetic offline metrics, private capture, and strict offline replay. The private baseline confirmed identical recommendation outputs (10 expected and 10 actual) and ten HTTP 503 metadata failures, but exposed a stable `metadata_lookup_errors` discrepancy. Root cause was confirmed in `recommendation_replay.py`: the HTTP cassette stored status/body but rebuilt requests as GET using the first URL argument, losing the original response request's fully resolved URL/query string. The fix and synthetic regression test are now on the PR branch; exact-head CI and user replay remain pending. Do not change ranking, candidate selection, scoring, or allocation until the private replay succeeds and Phase 0 evidence is reviewed. Publishing/deployment remain paused.

## Delivery and verification state

- **Recommendation capture/replay:** PR #298 remains open at code head `794013c3966c4d2dd9f736ccee4089c8621df943`. All four required workflows passed on that exact SHA: Python syntax `39022880718`, Docker packaging/full unit suite/build `39022880732` (602 tests), container runtime smoke `39022880724`, and validation-only multi-architecture image validation `39022880734`. No real private capture/replay, merge, publication, deployment, or production-runtime verification is claimed.
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
