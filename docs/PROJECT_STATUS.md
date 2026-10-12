# Project status and handoff

Last updated: 2026-10-12

## Source of truth

- Repository: [abucalip/navi-librarian](https://github.com/abucalip/navi-librarian)
- Default branch: `main`
- PR #14 documentation merged at `74264b29062504fce3bf6f7a65121fa43b9f8ec5`; PR #15 v0.2 planning merged at `f32b02a13b582e23699bde294eb94b51e5f646cc`.
- Latest documentation handoff commit before this update: `8153c3b05f1f84725a4d537d7417c95433bb040c`.
- **Deployment and manual verification:** the user reports Librarian is installed on the server and tested successfully; the GHCR Docker package has been made public. Account creation, entering service credentials in Settings, downloads, and imports all work as intended.
- The user report supersedes the earlier GHCR `unauthorized` blocker. The current image digest, deployed commit/tag, and host-side logs have not been independently recorded in this documentation session; do not invent them.
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
| Web UI and API | Deployed; user reports successful installation/use | Record exact deployed image tag/digest and commit when convenient |
| First-run account creation and login | User reports working successfully on the server | Preserve as a regression-smoke-test baseline |
| Settings and service credentials | User reports entering credentials through Settings works | Keep secret-handling and persistence tests in the automated suite |
| Recommendation/discovery logic | Existing logic is in `navidrome_server.py` | Test representative outputs against the real library |
| Discovery lists, feedback, refresh | API routes exist | Verify list persistence, dismiss/save behavior, and refresh |
| slskd downloads/acquisition | User reports downloads work as intended | Continue regression coverage for matching, queueing, status, and safe cleanup |
| Album imports | User reports imports work as intended | Preserve import-safety regression tests |
| Album artwork, release years, biographies, platform search links | Implemented in development history; verify exact default-branch coverage | Visual smoke test when UI changes affect these cards |
| Unit tests | Tests exist under `tests/` | Run the exact commands in [TEST_PLAN.md](TEST_PLAN.md) for code changes |
| Docker image build/publication | User reports package is now public; prior authorization blocker considered resolved | Check workflow and record image tag/digest for a future release |
| Production deployment | Installed and manually tested according to user report; exact image digest/host evidence not captured in this session | Record tag/digest and deployment details at next release/update |

## Latest session — 2026-10-12 (handoff updated from user verification)

- **New operational evidence from user:** Librarian is installed on the server and has been tested successfully. The Docker package has been made public.
- **Working baseline confirmed by user:** first-run account creation, entering service credentials through Settings, downloads, and imports work as intended.
- **Status correction:** previous notes that treated deployment as unverified and GHCR `unauthorized` as an active blocker are superseded by this report. Deployment and the named workflows are user-verified; the exact deployed image tag/digest and independent host evidence remain undocumented.
- **This documentation session:** no application code, settings, or server deployment changed. Updated project handoff and deployment notes to reflect the user's report; no automated application tests or live host checks were run.
- **Next:** keep these working flows as regression baselines. Before v0.2 implementation, inspect the actual code/tests and begin with a narrowly scoped acquisition-completion reliability improvement plus regression tests. At the next image update, record the deployed tag and digest.

## Previous session — 2026-10-12 (PR #15 merged)

- **PR:** [#15 — docs: plan v0.2 improvements from DroppedNeedle review](https://github.com/abucalip/navi-librarian/pull/15), squash-merged into `main`.
- **Merge commit:** `f32b02a13b582e23699bde294eb94b51e5f646cc`.
- **Documentation:** added [`docs/V0.2_DROPPEDNEEDLE_LESSONS.md`](V0.2_DROPPEDNEEDLE_LESSONS.md), a prioritized planning backlog covering acquisition completion evidence, safe lifecycle boundaries, consistent quality evaluation, recommendation pipeline clarity, caching review, and regression/performance guardrails.
- **Constraints recorded:** preserve Librarian's Navidrome–slskd bridge and library-/taste-aware recommendations; prioritize smoothness and stability; modularize Python responsibilities incrementally; do not copy DroppedNeedle code without reviewing AGPL-3.0 implications.
- **CI:** GitHub Actions reported both Python syntax check and Docker packaging validation successful for PR head `3e1f005e413a5522ec2866f30baebf1914cc4868`. This was documentation-only; application tests and UI smoke tests were not run.
- **Local checkout:** previously recorded as preserved on `fix/artwork-size-and-artist-bios`; inspect its current state before any Git operations.

## Latest session — 2026-10-12 (artwork loading reliability fix in review)

- **Branch:** `fix/artwork-loading-retries`; application change and regression test committed, not merged or deployed.
- **Follow-up from manual test:** the user reported that all covers disappeared when testing this branch. Root cause found in the frontend: album-year lookups and artwork lookups shared `artworkRequests`, keyed by artist+album, so the artwork renderer could reuse the `/api/album-year` promise and receive no `artwork_url`. Fixed by giving year lookups their own `albumYearRequests` cache; added `tests/test_artwork_cache_isolation.py`.
- **Follow-up validation:** fix and regression guard are committed on the PR branch, but CI and live UI retest are pending. Do not merge or deploy until covers are confirmed.
- **Observed failure mode in code:** artwork provider exceptions were converted into a normal no-artwork response and negative-cached for five minutes. The browser's one-shot IntersectionObserver unobserved the card immediately and marked it requested permanently, so transient provider outages left cards blank for the rest of the page session.
- **Change:** distinguish transient provider failures with a `retryable` response, do not negative-cache those failures, and retry in the browser up to three times with bounded backoff. Genuine no-match responses retain the existing negative cache and placeholder behavior.
- **Regression test:** added `tests/test_artwork_retry.py` to verify a provider timeout is marked retryable and does not populate the negative cache.
- **Validation:** GitHub Actions passed Python compilation and the full unittest suite (run #110) and Docker packaging validation (run #17) on tested code commit `fabcd1fb6563ef9cd65aa12005f2f77f3f90e07d`. The later documentation-only handoff commits do not change application code. Manual UI behavior remains unverified; not merged or deployed.
- **Next:** open/check the PR, run the full test plan and CI, then manually load Discoveries and Artist Deep Dives and confirm covers appear and that provider outages do not block browsing.

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
