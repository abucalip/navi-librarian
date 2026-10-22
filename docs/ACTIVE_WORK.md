# Active work

This is the short queue of unfinished or explicitly parked work. GitHub `main` is authoritative. Check current code, open PRs, and CI before starting anything; do not infer current state from archived notes.

## 1. Runtime verification — highest priority

- Verify PR [#526](https://github.com/abucalip/navi-librarian/pull/526): a deliberately failed track retries from the same source, and the 15-minute recovery window behaves correctly.
- Verify PR [#527](https://github.com/abucalip/navi-librarian/pull/527): blocked slskd artist queries recover through masked variants, and no-match diagnostics show the attempted queries.
- These fixes are merged and CI-verified as recorded in `docs/PROJECT_STATUS.md`, but not live-runtime-verified. Use the real service only with appropriate authorization; do not publish or deploy as part of verification.

## 2. Reported bugs — owner list

- After a successful acquisition, check the cache and prevent the imported album from appearing again in suggestions.
- Mobile status/navigation bar must be narrower and show icons only, not names, so at least five icons fit.
- The album panel must show the artist's bio.
- Suggested-album bars must be equal in width on all pages; an album with many tags currently renders much wider than one with two or three.
- Acquisitions page: album artwork flickers, and album bars sometimes switch positions continuously without any interaction.
- Artwork on "Deep dives" loads too slowly.

## 3. Recommendation engine — gated

- Repeat the ListenBrainz collaborative-filtering (CF) freshness capture after imported history has been recomputed. Any live capture requires owner approval.
- Only after freshness is understood, decide whether to request approval for deeper CF pages. Do not change ranking weights or increase provider requests/budgets without evidence and approval.
- Detailed evidence, alternatives, and evaluation criteria: [archived recommendation-engine research](archive/recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md).

## 4. Parked decisions — do not start without a new decision

- **Recommendation diversity setting/UI:** paused until candidate supply supports meaningful cross-pool evaluation. See [archived diversity roadmap](archive/parked/DIVERSITY_SETTING_ROADMAP.md).
- **v0.2 release:** preparation notes exist, but publishing/deployment remain paused until explicitly authorized. See [archived release preparation](archive/release/RELEASE_v0.2.md).
- **External MCP clients:** repository MCP retirement is complete; any external-client migration is unverified and outside repository evidence. See [archived MCP retirement record](archive/completed/MCP_RETIREMENT_PLAN.md).

## Reference map

- Current status and single next action: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Permanent development rules: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Product behavior: [REQUIREMENTS.md](REQUIREMENTS.md)
- Test gates: [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and boundaries: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Chronological implementation/verification evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
- Historical roadmaps and completed plans: [archive](archive/)
