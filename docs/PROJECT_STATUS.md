# Project status and handoff

Last updated: 2026-10-12

## Source of truth

- Repository: [abucalip/navi-librarian](https://github.com/abucalip/navi-librarian)
- Default branch: `main`
- Documentation/handoff update merged in PR #14 at `74264b29062504fce3bf6f7a65121fa43b9f8ec5` (2026-10-12). PR #15's v0.2 planning document merged in `f32b02a13b582e23699bde294eb94b51e5f646cc`.
- Current deployed version: **not verified**.
- GHCR pull from the Debian media VM recently failed with `unauthorized`. Package visibility/authentication must be resolved before a deployment can be considered verified.
- The developer's local checkout has a separate in-progress branch with commits not necessarily present on `main`. Do not assume local changes are merged or deployed.

## Product summary

Navidrome Librarian combines a web UI with existing music-discovery and acquisition logic in `navidrome_server.py`. The web app is served by FastAPI from `app/main.py`. It connects to an existing Navidrome instance and slskd service; neither is bundled into the app container.

## Feature ledger

Use the following meanings consistently:

- **Planned** — agreed requirement, no implementation evidence yet.
- **In progress** — being changed; do not rely on it.
- **Implemented** — code exists, but no adequate test evidence recorded.
- **Tested** — automated or manual validation passed and the scope is recorded.
- **Merged** — change is present on the default branch.
- **Deployed** — a specific image/commit was installed in the target environment.
- **Verified** — deployed behavior was checked in the running app.

| Area | Known state at this baseline | Next verification |
|---|---|---|
| Web UI and API | Implemented in `app/main.py` | Run automated tests and UI smoke test |
| Recommendation/discovery logic | Existing logic is in `navidrome_server.py` | Test representative outputs against the real library |
| Discovery lists, feedback, refresh | API routes exist | Verify list persistence, dismiss/save behavior, and refresh |
| slskd acquisition | Search, candidate queueing, settings, status, and dismiss routes exist | Test matching, queueing, import safety, and destructive cleanup |
| Album artwork, release years, biographies, platform search links | Code exists in the current development history; verify exact default-branch coverage | Visual smoke test for each card type |
| First-run web account and persistent app state | Authentication tests and persistent data volume are present | Verify fresh install, restart, and upgrade preserve login/data |
| Unit tests | Tests exist under `tests/` | Run the exact commands in [TEST_PLAN.md](TEST_PLAN.md) |
| Docker image build | Docker packaging and CI workflow are on `main` | Confirm current workflow run and build |
| GHCR publication/pull | Not verified; deployment VM reported `unauthorized` | Check package visibility/authentication and pull an exact tag |
| Production deployment | Not verified | Record image digest, Compose config, logs, and UI smoke-test result |

## Latest session — 2026-10-12 (PR #15 merged)

- **PR:** [#15 — docs: plan v0.2 improvements from DroppedNeedle review](https://github.com/abucalip/navi-librarian/pull/15), squash-merged into `main`.
- **Merge commit:** `f32b02a13b582e23699bde294eb94b51e5f646cc`.
- **Documentation:** added [`docs/V0.2_DROPPEDNEEDLE_LESSONS.md`](V0.2_DROPPEDNEEDLE_LESSONS.md), a prioritized planning backlog covering acquisition completion evidence, safe lifecycle boundaries, consistent quality evaluation, recommendation pipeline clarity, caching review, and regression/performance guardrails.
- **Constraints recorded:** preserve Librarian's Navidrome–slskd bridge and library-/taste-aware recommendations; prioritize smoothness and stability; modularize Python responsibilities incrementally; do not copy DroppedNeedle code without reviewing AGPL-3.0 implications.
- **CI:** GitHub Actions reported both Python syntax check and Docker packaging validation successful for PR head `3e1f005e413a5522ec2866f30baebf1914cc4868`. This was documentation-only; application tests and UI smoke tests were not run.
- **Deployment:** not performed. A documentation-only change does not require rebuilding/restarting the application. The existing GHCR `unauthorized` blocker remains unresolved; deployed runtime version remains unverified.
- **Local checkout:** left untouched on `fix/artwork-size-and-artist-bios`, clean and six commits ahead of its recorded origin; no checkout, reset, or cleanup performed.
- **Next:** for v0.2 implementation, inspect current code and tests and begin with a narrowly scoped acquisition-completion reliability fix plus regression tests. Resolve GHCR authorization before the next registry-based application deployment.

## Previous session — 2026-10-12

- **Completed:** PR #14 merged into `main` using squash merge. It adds the six project handoff/runbook documents listed below; merge commit: `74264b29062504fce3bf6f7a65121fa43b9f8ec5`.
- **CI evidence:** GitHub reported the Python syntax-check and Docker-packaging validation workflows passed for PR head `97e887fa8295fff55f05ac72101907bf08819a99`. The PR was documentation-only; no application tests or deployment were run as part of the merge session.
- **Deployment state:** unchanged and still unverified. GHCR authorization remains unresolved; do not infer that merge or successful CI means the app is deployed.
- **Next priority:** inspect current open PRs and local branches/worktrees, then resume the highest-priority implementation/testing task. Resolve GHCR package visibility/authentication before attempting registry-based deployment.

## Known blocker

The media VM's `docker compose pull navidrome-librarian` returned a GHCR `unauthorized` error. A published package can still be private. Resolve package visibility or authenticate with a GitHub token that has package-read permission. A tag or SHA digest does not bypass registry authorization.

## Session start checklist

1. Read this file and [REQUIREMENTS.md](REQUIREMENTS.md).
2. Check the GitHub default branch, active PRs, and the exact commit being tested.
3. Inspect `git status`, current branch, recent commits, and the actual diff before editing.
4. Identify the acceptance criteria and regression tests for the task.
5. Keep unrelated local work untouched; use a separate branch/worktree for experiments.

## Session end checklist

Update this file and [PROJECT_LOG.md](../PROJECT_LOG.md) with:

- branch, PR, and commit SHA;
- files and behavior changed;
- tests run and exact pass/fail result;
- status transitions (do not equate implemented, merged, deployed, and verified);
- unresolved defects and the next concrete action.

Never record credentials, API keys, cookies, or other secrets in documentation.
