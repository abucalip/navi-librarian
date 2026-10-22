# Active work

This is the short queue of unfinished or explicitly parked work. GitHub `main` is authoritative. Check current code, open PRs, and CI before starting anything; do not infer current state from archived notes.

## 1. Runtime verification — highest priority

- **Attempted 2026-10-22; blocked by access.** Repository review confirms PRs #526 and #527 are merged and CI-verified, but this session has no connection to the running Librarian host or slskd API. These changes have not been published/deployed, and no live search or transfer was attempted.
- For PR [#526](https://github.com/abucalip/navi-librarian/pull/526), verify a deliberately failed test track is re-queued alone from the same source, retry cadence/limit is respected, and the 15-minute recovery grace works. This changes the slskd queue, so use an isolated test acquisition/folder; do not create a production transfer just to test it.
- For PR [#527](https://github.com/abucalip/navi-librarian/pull/527), compare an unmasked blocked artist query with masked variants and confirm candidates are returned where available; on no-match, confirm diagnostics list attempted queries and response counts.
- **Next:** arrange authorized access to an isolated Librarian test instance connected to the real slskd service. Do not publish/deploy or claim runtime verification until these checks are actually run.

## 2. Reported bugs — status

- Imported-album suggestion suppression is merged in PR [#530](https://github.com/abucalip/navi-librarian/pull/530) as `0b2bda011b86d2c08a0179e5df801c7891c10f9a`; it preserves the future-release filter from PR #528. Required CI, including the full unit suite, passed on tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`.
- UI fixes from original PRs #531–#535 are integrated: icon-only mobile navigation (#546), artist bio in the album panel (#547), equal-width ranked rows (#533), stable acquisition rendering (#534), and smaller/faster card artwork (#535). Required workflows passed on each final reconciled head; details are recorded in `PROJECT_LOG.md`.
- The owner waived manual browser checks for this merge batch; they were not performed. Artwork performance was not measured, and live browser/runtime behavior is not claimed. No image publication or deployment occurred.

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
