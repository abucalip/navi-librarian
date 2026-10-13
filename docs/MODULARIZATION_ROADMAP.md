# Modularization Roadmap

Last updated: 2026-10-13

## Purpose

Reduce coupling in Librarian's Python implementation so developers can isolate bugs, write deterministic tests, and change one behavior without risking unrelated parts of the app. This is a staged plan, not a record of completed code changes.

## Current baseline

The GitHub `main` source inspected on 2026-10-13 contains approximately:

- `navidrome_server.py`: 6,741 lines; MCP entry point, Navidrome access, discovery, recommendation, settings, slskd search, acquisition lifecycle, import safety, and background tasks.
- `app/main.py`: 2,969 lines; FastAPI routes, authentication, external metadata/cache logic, and inline frontend code.
- `tests/test_acquisition_safety.py`: 930 lines; safety and lifecycle tests that currently extract functions with AST/stub machinery.

These line counts are approximate and should be rechecked before each implementation stage.

## Product direction: web-only

MCP is a remnant of the original prototype, not a requirement of the delivered application. The target is to ship and run the authenticated web application/API without an MCP server or MCP tool registration.

Do not delete MCP code first: the current web layer calls functions in `navidrome_server.py`. Extract shared domain behavior into normal importable modules and redirect the web layer first. Then audit all repository references, dependencies, tests, and deployment commands before removing MCP-only runtime pieces. Preserve the web API/UI, authentication, settings, persistent data, and acquisition safety. This target has not yet been implemented.

## Target modules and responsibilities

- `app/services/acquisition_completion.py`: completion inspection, expected-track matching, normalized filename identity, folder ambiguity diagnostics.
- `app/services/acquisition_matching.py`: candidate/album matching and eligibility decisions, separate from queueing or file movement.
- `app/services/slskd_search.py`: bounded query generation, response normalization, delayed-payload polling, search diagnostics.
- `app/services/acquisition_import.py`: canonical path validation, safe moves, no-overwrite guarantees, rollback, interrupted-import reconciliation.
- `app/services/acquisition.py`: orchestration of candidate search, queue, progress, failover, completion, import, and lifecycle status.
- `app/services/recommendations.py`: candidate scoring, eligibility, ranking, diversity rules.
- `app/services/discovery.py`: list construction, refresh, persistence, and user feedback coordination.
- `app/api/*.py`: route groups for acquisitions, discovery, settings, and metadata.
- `app/main.py`: application creation, middleware and router registration, with presentation assets moved later as a separate step.

Names and locations can be adjusted to fit existing package conventions after the import graph is inspected. Do not create empty abstractions simply to match this sketch.

## Priority order

1. **Review PR #24 before further extraction:** inspect the complete diff against its stated relocation-only objective, confirm wrapper behavior and regression coverage, and verify CI on the exact head. Resolve any unnecessary churn or behavioral differences before merge. PR #24 is open and unmerged; passing CI is not merge approval.
2. **Inventory and establish a clean baseline for the next change:** inspect current GitHub `main`, open PRs, shared globals, locks, configuration, callers, tests, and exact behavior. Record the exact base SHA and acceptance criteria before editing.
3. **Completion and matching:** the first extraction is implemented on PR #24. After review/merge, retain its direct-import regression coverage and address any review findings before starting the next boundary.
4. **slskd search and quality:** isolate query fallback, delayed response polling, response parsing, candidate matching, and quality classification. Preserve time budgets and saved priority ordering.
5. **Import safety and lifecycle:** isolate destructive filesystem work from orchestration. Preserve traversal/symlink checks, filesystem identity, no-overwrite, rollback, failover, dismissal/retry, and restart reconciliation.
6. **Discovery and recommendations:** separate ranking from list-building/refresh/persistence; preserve ownership exclusions and diversity behavior.
7. **FastAPI routes:** split by feature after domain services have stable interfaces; preserve API contracts, auth, settings and UI behavior.
8. **MCP retirement:** after the web app no longer depends on MCP initialization, remove MCP server/tool registration, dependencies, obsolete tests/docs and entry-point commands only where a usage audit confirms they are MCP-only.

## Testing strategy

- Test newly extracted modules through normal imports; avoid new AST-extraction tests.
- Use temporary filesystem fixtures for completion/import logic and mocked HTTP clients for slskd/provider logic.
- Retain existing tests until their coverage is migrated; do not delete a test merely because its implementation mechanism is awkward.
- For every stage, run focused tests, `python -m unittest discover -s tests -v`, syntax checks, and Docker build/CI where available. Review the exact commit's CI and final diff.
- Verify web/API/auth/UI behavior when applicable. Compilation alone is not sufficient.

## Non-goals and guardrails

- No framework rewrite, microservices split, or generic repository/DI layer without evidence of need.
- No simultaneous behavioral redesign of recommendation ranking, search heuristics, quality matching, import semantics, or UI during code relocation.
- No weakening of path validation, destructive-operation safeguards, or persistent-data compatibility.
- No copying DroppedNeedle implementation code without a licensing review; use its architecture as inspiration and independently implement the design.

## Status

**Planned only (2026-10-13).** Documentation updated on branch `docs/modularization-web-only-roadmap`. No application code was changed and no tests were run for a code change. The next implementation task is the completion/matching extraction on a fresh, verified current-main branch, with direct regression tests and no user-visible behavior change.
