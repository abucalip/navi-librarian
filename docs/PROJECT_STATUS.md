# Project status

Last reviewed: 2026-10-17 (PR #305 merged; private baseline review next)

## Current focus

**Recommendation roadmap — Phase 0.3 observability.** PR #302 merged at `bb473e99855208606e3bcb76dbf7c1cb9eb09b43`, making `scripts/session_search.py` the standard focused retrieval workflow. PR #303 merged at `a04d4f4c3b5beed3e29969c75cf812591222dc08`, adding bounded persisted outcomes for manual versus scheduled personal-list refreshes and recording the origin in persisted recommendation-pool metrics without expanding the public API response. PR #304 merged at `19435d5deea69b188d920cf375ef924ec3b14a97`, adding aggregate candidate provenance, score, profile, cache, and eligibility metrics.

**Privacy correction merged:** PR #305 removes raw family/tag names from persisted aggregate recommendation diagnostics, replacing them with `recent_family_count` and `recent_family_listen_count`. Regression tests confirm representative raw tags are absent from returned and persisted diagnostics. No ranking behavior or public API response shape changed. PR #305 merged at `909eac617368f18a0ec4ff196f7eb83bb9a9a9c6` from exact final PR head `4b9e0ad77b89aac144bbf5505666381a49a2af69`; all four required workflows passed on that exact head: Python syntax run 1539 (`39044014509`), Docker packaging/full unit suite/build run 1447 (`39044014507`), container runtime smoke run 1256 (`39044014508`), and validation-only multi-architecture image validation run 1300 (`39044014541`).

The private PR #298 replay reproduced 10/10 recommendations using 197 provider events and 40 Last.fm events with zero network calls, but its full metric report has not been inspected in this session. Recommendation-policy changes remain gated until that report and its limitations are reviewed.

PR #304's four required workflows passed on exact final head `808ed2621ec5a3e9db3a05083e5fb1dcc828e4cb`: Python syntax/size/import-boundary run 1531 (`39042482100`), Docker packaging/full unit suite/build run 1439 (`39042482020`), container runtime smoke run 1248 (`39042481923`), and validation-only multi-architecture build run 1292 (`39042481930`). PR #305's final-head workflow evidence is recorded above. Publishing remains paused; no deployment or production-runtime verification is claimed.

**Next action after this privacy fix:** review the private replay baseline metrics and limitations, then decide whether Phase 0 has enough evidence to advance before changing recommendation policy.

## Recommendation baseline and prior work

**Recommendation Phase 0 capture/replay is implemented and the private baseline replay succeeded.** On capture/source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`, offline replay reproduced 10/10 recommendations, consumed 197 provider events and 40 Last.fm events, and used zero network providers. The comparator checks all stable top-level fields except `pool_diagnostics` and `lastfm_last_error`. PR #298 merged at `68a0ee365778dab790ec54e04b54c8c72bd4552c` from final PR head `a3bdfd7bff6785c1fd17e422a26a7fde36170fad`; all four required workflows passed on that exact head. Review baseline metrics and limitations before changing ranking, candidate selection, scoring, or allocation.

PR #299 is merged and provides baseline-independent scheduled-refresh diagnostics: freshness classification for missing, expired, malformed, and non-finite timestamps; per-list cache/read/refresh failure isolation; bounded warnings that omit exception messages; and regression coverage. It preserves the 24-hour threshold, hourly cadence, list order, refresh callbacks, and API response contracts. Ranking and candidate selection are unchanged.

**PR #299 verification:** final PR head `e830adc7b014a915d31756619e5fadc90106696c`; merge commit `22820fb534ce243c78b1bb30d1f7cbbaaabd36cd`. All four required workflows passed on the exact final head: Python syntax run 1497, Docker packaging/full unit suite/build run 1405, container runtime smoke run 1214, and validation-only multi-architecture validation run 1258. No assistant-side local tests were run. Publishing, deployment, and production-runtime verification are not claimed.

## Delivery and verification state

- **Recommendation Phase 0 diagnostics/capture/replay merged:** PR #298, final PR head `a3bdfd7bff6785c1fd17e422a26a7fde36170fad`, merge commit `68a0ee365778dab790ec54e04b54c8c72bd4552c`. Exact-head workflows passed: Python syntax/size guard `39037807384`, Docker packaging/full unit suite/build `39037807392`, container runtime smoke `39037807378`, validation-only multi-architecture build `39037807401`. Publishing remains paused.
- **MCP retirement plan merged:** PR #295, final PR head `6fe8a2c11c73da5c95a296cca8bc29657fef7f19`, merge commit `82146d3c14bb4106ea445eed8d7931eda1eec587`.
- **CI on exact PR head:** all four required workflows passed: Python syntax `38989332620`, Docker packaging/full unit suite/build `38989332628`, container runtime smoke `38989332661`, and validation-only multi-architecture `38989332681`. Publishing remains paused.
- **Local tests:** not run in this GitHub-only workflow.
- **Publishing:** paused; multi-architecture validation remains non-publishing (`push: false`).
- **Deployment / production runtime:** no deployment or production-runtime verification is claimed.
- **Configuration note:** existing persisted settings were not migrated; previously saved URLs/usernames may remain until the user changes them.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred unless reproducibly demonstrated.
- **MCP retirement:** repository-level plan complete; PR #296 merged at `f5cb56cbb4712bc9919e74e94e7ccf5cbe7effb7`. External client/config migration and production runtime are unverified.

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
| Focused documentation/code retrieval for agent sessions | `docs/SESSION_CONTEXT_SEARCH.md` and `scripts/session_search.py` |
| Development, review, merge, and release process | `docs/DEVELOPMENT_WORKFLOW.md` |
