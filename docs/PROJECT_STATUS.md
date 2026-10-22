# Project status

Last checked: 2026-10-22. GitHub `main` is authoritative.

## Current state

- PR #528 (hide future-dated New Releases) is merged as `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750` from exact PR head `295148dcf817479f4098195200ada4c4173733fe`. All four required CI workflows passed on that exact head; the Docker packaging workflow ran the full unit suite successfully. Future-dated releases are filtered both during candidate selection and when serving cached New Releases. Not published or deployed; no live-library/browser verification claimed.
- PR #529 was closed as stale and superseded by PR #530. PR #530 reconciles imported-album filtering with PR #528's future-date filtering. On exact final head `df3dd651051826f483831b5a868dd16483f75fa4`, Python syntax/acquisition-safety, full unit suite and Docker build, container runtime smoke, and validation-only multi-architecture image checks passed. Release publishing was skipped; its validation-only job passed. PR #530 remains open and unmerged; no publication, deployment, or live-runtime verification.
- Open UI PR stack #531–#535 covers the mobile icon-only navigation, album-panel artist bio, equal-width ranked rows, stable acquisition rendering, and smaller/faster card artwork. The original PR branches target stacked feature branches, so the required workflows (which only run for PRs targeting `main`) have no runs on their exact heads. Temporary current-main integration candidates reconstructed from each cumulative changed-file state passed all four required workflows, including the full unit suite, at SHAs `53026bcbff794c04b6f901aefeb4fa939403cd7e` (#531), `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a` (#532), `da4a3e72146ec60c8c0c700f4ed5f387bf864723` (#533), `d319d8c5cc5f661a834035dabf99a26a1431655a` (#534), and `1d803c6f1daf198d3c77741cbbb5c51eb5c490e0` (#535). These are reconstructed validation commits, not the original PR heads; no claim that the original heads themselves passed CI. Temporary validation PRs were closed after checks. Manual browser testing remains required, and PRs #531–#535 still need their stale stacked base (starting at closed PR #529) reconciled before merge.
- PR #526 (failed-track retry) and PR #527 (masked slskd artist queries) are merged and CI-verified. Neither fix has been verified against a live slskd runtime.
- Python package-layout work is complete through PR #524. The earlier modularization roadmap is closed; do not restart size-only extraction work.
- MCP is retired as a supported repository interface. External-client migration is not verifiable from repository evidence.
- The front-end redesign is complete. Its design briefs, phase plans, and agent-specific restrictions have been archived.
- Image publication and deployment remain paused until explicitly authorized.

## Next action

Review and merge PR [#530](https://github.com/abucalip/navi-librarian/pull/530) after checking the final PR state; required CI and the full unit suite passed on exact head `df3dd651051826f483831b5a868dd16483f75fa4`. Next, rebase the UI stack #531–#535 off closed PR #529 onto current `main` (preserving the intended order), then run required CI on the actual final PR heads and perform the manual browser checks in `docs/LOCAL_UI_TESTING.md`. Do not publish or deploy. Live-runtime verification of #526/#527 remains outstanding.

## Where to look

- Outstanding work and parked decisions: [ACTIVE_WORK.md](ACTIVE_WORK.md)
- Permanent workflow: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Requirements and test gates: [REQUIREMENTS.md](REQUIREMENTS.md), [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Historical implementation evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
