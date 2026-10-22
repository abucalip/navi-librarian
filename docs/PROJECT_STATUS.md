# Project status

Last checked: 2026-10-22. GitHub `main` is authoritative.

## Current state

- PR #528 (hide future-dated New Releases) is merged as `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750` from exact PR head `295148dcf817479f4098195200ada4c4173733fe`. All four required CI workflows passed on that exact head; the Docker packaging workflow ran the full unit suite successfully. Future-dated releases are filtered both during candidate selection and when serving cached New Releases. Not published or deployed; no live-library/browser verification claimed.
- PR #526 (failed-track retry) and PR #527 (masked slskd artist queries) are merged and CI-verified. Neither fix has been verified against a live slskd runtime.
- Python package-layout work is complete through PR #524. The earlier modularization roadmap is closed; do not restart size-only extraction work.
- MCP is retired as a supported repository interface. External-client migration is not verifiable from repository evidence.
- The front-end redesign is complete. Its design briefs, phase plans, and agent-specific restrictions have been archived.
- Image publication and deployment remain paused until explicitly authorized.

## Next action

Verify the merged PR #526 and #527 behavior against the real slskd service, following the gates in [ACTIVE_WORK.md](ACTIVE_WORK.md). Do not publish or deploy as part of that verification.

## Where to look

- Outstanding work and parked decisions: [ACTIVE_WORK.md](ACTIVE_WORK.md)
- Permanent workflow: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Requirements and test gates: [REQUIREMENTS.md](REQUIREMENTS.md), [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Historical implementation evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
