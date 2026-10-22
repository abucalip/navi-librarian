# Project status

Last checked: 2026-10-22. GitHub `main` is authoritative.

## Current state

- PR #528 (hide future-dated New Releases) is merged as `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750` from exact PR head `295148dcf817479f4098195200ada4c4173733fe`. All four required CI workflows passed on that exact head; the Docker packaging workflow ran the full unit suite successfully. Future-dated releases are filtered both during candidate selection and when serving cached New Releases. Not published or deployed; no live-library/browser verification claimed.
- PR #530 (hide imported albums from cached discovery lists) merged as `0b2bda011b86d2c08a0179e5df801c7891c10f9a` from tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`. All required workflows passed on that exact head, including the full unit suite and Docker build; release publishing was skipped and validation-only multi-architecture passed. No publication, deployment, or live-library verification.
- UI changes originally proposed in PRs #531–#535 are integrated. PRs #531 and #532 were superseded by reconciled replacements #546 and #547 (merge commits `f884f004de83a6c373c16699b560e25312b41a3d` and `4e11053ae5d203a4287a27abb162b4a9d093bf60`); PRs #533–#535 merged as `8beb5baac431e6916d434efd111d96d98c4b8d9b`, `871d3dd4401e493315e38f021bcdeec7918e0900`, and `785715320c45b0e79d5f93873953b85859d4891f`. Required workflows, including the full unit suite/Docker build, passed on each final reconciled head. The owner waived manual browser checks for this merge batch; they were not performed. Artwork performance was not measured. No publication, deployment, or live-runtime verification.
- PR #554 (larger row artwork and artist bio on Recommendations, New releases, and Personal discoveries rows; bio clamps to two lines and expands on click) merged as `c9fcf3289f37984258aca5b62891d700c569d5c1` from exact head `8c8d473f3b9576fbf0dc278c702b9843b422d991`. Syntax check, container smoke, and release validation passed; the Docker packaging/full-suite run and the image validation run had not finished at merge time, so confirm them on `main`. The owner manually checked it in the browser. Not published or deployed.
- PR #555 (artist bios and dashboard discovery UI refinements) merged as `f80254550369ed56b66e114faebb2b9fb72ed6bf` from exact head `58bbe0e4ef7320c14146a6fa4ea5a3ef0d266953`. All four required workflows passed on that exact head, including the full unit suite and Docker build; release validation passed with publishing skipped. The owner reported successful manual browser testing. Not published or deployed.
- PR #556 (“Similar to” labels) was a stacked PR based on the now-merged PR #555 branch, so it was closed as superseded. Reconciled replacement PR [#557](https://github.com/abucalip/navi-librarian/pull/557) is based on `main`, head `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`. The full unit suite/Docker build passed, as did Python syntax/size and safety checks, container smoke, validation-only multi-architecture image validation, and release-workflow validation (publishing skipped). The initial size-guard failure was fixed by extracting a reusable, directly tested lookup helper. **Manual browser verification remains required and has not been performed; PR #557 is not merged.** No publication or deployment.
- PR #526 (failed-track retry) and PR #527 (masked slskd artist queries) are merged and CI-verified, but live-runtime verification is blocked: this session has no connection to the running Librarian host or slskd API, and these changes have not been published or deployed. No live search or transfer was attempted. Keep publication/deployment paused.
- Python package-layout work is complete through PR #524. The earlier modularization roadmap is closed; do not restart size-only extraction work.
- MCP is retired as a supported repository interface. External-client migration is not verifiable from repository evidence.
- The front-end redesign is complete. Its design briefs, phase plans, and agent-specific restrictions have been archived.
- Image publication and deployment remain paused until explicitly authorized.

## Next action

Arrange authorized access to an isolated Librarian test instance connected to the real slskd service, then verify PRs [#526](https://github.com/abucalip/navi-librarian/pull/526) and [#527](https://github.com/abucalip/navi-librarian/pull/527) without publishing or deploying. Current session has no connection to the running Librarian host or slskd API, and these merged changes are not deployed; live verification remains incomplete. Do not enqueue production transfers as a substitute for an isolated test.

## Where to look

- Outstanding work and parked decisions: [ACTIVE_WORK.md](ACTIVE_WORK.md)
- Permanent workflow: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Requirements and test gates: [REQUIREMENTS.md](REQUIREMENTS.md), [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Historical implementation evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
