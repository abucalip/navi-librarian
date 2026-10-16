# Project status

Last reviewed: 2026-10-16  
GitHub source of truth: \`main\` at review baseline \`b0c63b267c834516b419d7e8183d007d2dbb2f5b\`

## Current focus

Backend modularization remains in progress. Recent work has extracted discrete discovery and application-assembly responsibilities, including New Releases policy/provider helpers and authentication configuration/secret/settings helpers. See the root \`PROJECT_LOG.md\` for exact PRs, tested SHAs, test evidence, and merge commits.

## Next action

1. Refresh \`main\`, open PRs, recent commits, and CI before selecting work.
2. Trace \`_build_classics_list()\`, callers, tests, and the already-extracted classics helpers. Select one narrow, independently testable remaining responsibility only if it improves ownership.
3. Reassess application-assembly dependencies and AST-coupled acquisition tests as a completion audit.
4. Treat the acquisition coordinator as conditional, high-risk work; do not force an extraction. Do not perform size-only slskd refactors.

The active candidate list and acceptance criteria live in \`docs/MODULARIZATION_ROADMAP.md\`.

## Delivery and verification state

- **Implemented / merged:** see \`PROJECT_LOG.md\` and current GitHub history for exact revisions.
- **Automated verification:** required CI gates must be checked on each exact final PR-head SHA; historical success is not evidence for a new revision.
- **Local execution:** do not claim assistant-side local tests unless actually run. Record unavailable or skipped checks explicitly.
- **Publishing:** paused; multi-architecture validation must remain non-publishing (\`push: false\`).
- **Deployment / production runtime:** not implied by merge or CI. No new deployment or production-runtime verification is claimed by this documentation update.
- **Deferred issue:** acquisition-dismissal HTTP 409 remains deferred because it has not been reproducibly demonstrated.
- **MCP:** preserve current compatibility seams during routine modularization. Retirement requires a separate explicit decision and migration gate.

## Documentation map

| Need | Canonical document |
|---|---|
| Current snapshot and next action | This file |
| Remaining extraction work and exit criteria | \`docs/MODULARIZATION_ROADMAP.md\` |
| Detailed historical PR, commit, and verification evidence | Root \`PROJECT_LOG.md\` |
| User-visible behavior and product invariants | \`docs/REQUIREMENTS.md\` |
| Required automated and manual verification | \`docs/TEST_PLAN.md\` |
| Development, review, merge, and release process | \`docs/DEVELOPMENT_WORKFLOW.md\` |
| Current module boundaries and architectural decisions | \`docs/ARCHITECTURE.md\`, \`docs/DECISIONS.md\`, and source code |

## Status update rule

Keep this file short and current. Update it after meaningful development sessions with the present state, verified blockers, and one next action. Do not copy long historical extraction reports here; put those in \`PROJECT_LOG.md\`.