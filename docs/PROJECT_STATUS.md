# Project status

Last checked: 2026-10-22. GitHub `main` is authoritative.

## Current state

- PR #528 (hide future-dated New Releases) is merged as `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750` from exact PR head `295148dcf817479f4098195200ada4c4173733fe`. All four required CI workflows passed on that exact head; the Docker packaging workflow ran the full unit suite successfully. Future-dated releases are filtered both during candidate selection and when serving cached New Releases. Not published or deployed; no live-library/browser verification claimed.
- PR #530 (hide imported albums from cached discovery lists) merged as `0b2bda011b86d2c08a0179e5df801c7891c10f9a` from tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`. All required workflows passed on that exact head, including the full unit suite and Docker build; release publishing was skipped and validation-only multi-architecture passed. No publication, deployment, or live-library verification.
- UI changes originally proposed in PRs #531–#535 are integrated. PRs #531 and #532 were superseded by reconciled replacements #546 and #547 (merge commits `f884f004de83a6c373c16699b560e25312b41a3d` and `4e11053ae5d203a4287a27abb162b4a9d093bf60`); PRs #533–#535 merged as `8beb5baac431e6916d434efd111d96d98c4b8d9b`, `871d3dd4401e493315e38f021bcdeec7918e0900`, and `785715320c45b0e79d5f93873953b85859d4891f`. Required workflows, including the full unit suite/Docker build, passed on each final reconciled head. The owner waived manual browser checks for this merge batch; they were not performed. Artwork performance was not measured. No publication, deployment, or live-runtime verification.
- PR #526 (failed-track retry) and PR #527 (masked slskd artist queries) are merged and CI-verified. Neither fix has been verified against a live slskd runtime.
- Python package-layout work is complete through PR #524. The earlier modularization roadmap is closed; do not restart size-only extraction work.
- MCP is retired as a supported repository interface. External-client migration is not verifiable from repository evidence.
- The front-end redesign is complete. Its design briefs, phase plans, and agent-specific restrictions have been archived.
- Image publication and deployment remain paused until explicitly authorized.

## Next action

Continue with live-runtime verification of merged PRs [#526](https://github.com/abucalip/navi-librarian/pull/526) and [#527](https://github.com/abucalip/navi-librarian/pull/527), as described in `docs/ACTIVE_WORK.md`. The #530–#535 change set is merged and required CI passed on each final tested head. Manual browser checks for the UI batch were waived by the owner and not performed. Do not publish or deploy.

## Where to look

- Outstanding work and parked decisions: [ACTIVE_WORK.md](ACTIVE_WORK.md)
- Permanent workflow: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Requirements and test gates: [REQUIREMENTS.md](REQUIREMENTS.md), [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Historical implementation evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
