# Project status

Last checked: 2026-10-22. GitHub `main` is authoritative.

## Current state

- PR #528 (hide future-dated New Releases) is merged as `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750` from exact PR head `295148dcf817479f4098195200ada4c4173733fe`. All four required CI workflows passed on that exact head; the Docker packaging workflow ran the full unit suite successfully. Future-dated releases are filtered both during candidate selection and when serving cached New Releases. Not published or deployed; no live-library/browser verification claimed.
- PR #529 was closed as stale and superseded by PR #530. PR #530 reconciles imported-album filtering with PR #528's future-date filtering. On exact head `34b926249a6e71aeab4e2243500fa91eb47e226b`, Python syntax/acquisition-safety, full unit suite and Docker build, container runtime smoke, and validation-only multi-architecture image checks passed. Release publishing was skipped; its validation-only job passed. PR #530 remains open and unmerged; no publication, deployment, or live-runtime verification.
- PR #526 (failed-track retry) and PR #527 (masked slskd artist queries) are merged and CI-verified. Neither fix has been verified against a live slskd runtime.
- Python package-layout work is complete through PR #524. The earlier modularization roadmap is closed; do not restart size-only extraction work.
- MCP is retired as a supported repository interface. External-client migration is not verifiable from repository evidence.
- The front-end redesign is complete. Its design briefs, phase plans, and agent-specific restrictions have been archived.
- Image publication and deployment remain paused until explicitly authorized.

## Next action

Review and merge PR [#530](https://github.com/abucalip/navi-librarian/pull/530) after checking the final PR state; its required CI passed on exact head `34b926249a6e71aeab4e2243500fa91eb47e226b`. Then verify merged PR #526 and #527 behavior against the real slskd service, following [ACTIVE_WORK.md](ACTIVE_WORK.md). Do not publish or deploy as part of either step.

## Where to look

- Outstanding work and parked decisions: [ACTIVE_WORK.md](ACTIVE_WORK.md)
- Permanent workflow: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Requirements and test gates: [REQUIREMENTS.md](REQUIREMENTS.md), [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Historical implementation evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
