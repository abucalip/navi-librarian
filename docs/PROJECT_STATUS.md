## Latest session — 2026-10-13 (retry after Dismiss; implementation in progress)

- **Branch:** `fix/retry-dismissed-acquisitions`, based on `fix/flac-hires-acquisition-diagnostics`; not merged or deployed.
- **Observed cause:** user confirmed the albums that would not create a new acquisition card had previously been dismissed. The current acquisition entry point rejects every dismissed record, so Get cannot restart it.
- **Change:** a fresh Get now attempts to reopen a dismissed record only after Dismiss had successfully completed its safety cleanup. The stale candidate and settings are cleared before a new search; if the guarded status update fails, the retry remains blocked. Added lifecycle regression tests for successful reactivation and refusal when reactivation fails.
- **Verification:** implementation and regression tests are committed, but CI and local test results for this new branch are pending. User's earlier unittest run was on local branch `pr21-test` and predates this change; it does not validate this patch. PR #21's response-normalization changes remain part of the base branch.
- **Next:** check syntax/full unittest CI on this branch, then test a previously dismissed album in `prox-mcp-pr17-test`. Do not merge/deploy until verified.

## Latest session — 2026-10-13 (Hi-Res FLAC priority and acquisition diagnostics in progress)

- **Branch:** `fix/flac-hires-acquisition-diagnostics`, based on GitHub `main`; not merged or deployed.
- **Scope:** add a reorderable FLAC Hi-Res quality tier, recognize common resolution labels including `[24-44.1]`, preserve prior quality ordering when migrating four- or five-tier settings, and expose bounded candidate summaries plus path/artist match signals when no source folders are recognized.
- **Regression coverage:** added tests for the reported Tinariwen folder-name variants, explicit 16/44 metadata, 24/44.1 filename labels, high-resolution metadata, and settings migration/order preservation.
- **Root-cause boundary:** the Tinariwen folder variants pass the album-token matcher in a fixture. Queue handling now retries other eligible peers after explicit 400/404/422 rejections, treats 401/403 as global auth/permission failures, and conservatively monitors timeouts/5xx. Follow-up report for Bombino — Agamgam: the card says `no_matches` with 0 peer responses although the user saw four sources. Added normalized slskd response parsing and a short grace retry when search state reports peers before response payloads are visible; diagnostics retain slskd-reported response/file counts. Live confirmation still requires retesting.
- **Verification:** on queue-failover code commit `8df498909ca4ac1e1df6fe1b726e5f018ff749d3`, Python syntax/acquisition-safety workflow #150 passed and Docker packaging workflow #57 passed compilation, the full unit-test suite, and Docker image build. A later documentation-only commit records the results. No local test runner was available through the connected read-only Git checkout, and no live slskd request was made.
- **Next:** review CI on the PR head, then test in the existing `prox-mcp-pr17-test` environment with the Tinariwen acquisition (or another known result). If it still fails, capture the returned status, `candidate_diagnostics`, and `attempts` before changing the queue logic.

## Latest session — 2026-10-13 (PR #20 merged; five-tier quality priority verified)

- **PR #20:** [Add FLAC 16/44 and sortable quality priorities](https://github.com/abucalip/navi-librarian/pull/20), squash-merged into `main` at merge commit `a9218bb5cb5c663b7ef26dc5f42cd69bbeadba45`.
- **Implemented:** added FLAC 16-bit/44.1 kHz as a fifth acquisition quality tier. Existing four-tier settings migrate by appending the new tier without changing the prior order; quality priority remains five unique supported tiers and persists in the existing Settings API.
- **Settings UI:** replaced the per-tier dropdowns with a draggable ordered list and accessible Move up/Move down controls. FLAC 16/44 classification requires explicit sample-rate/bit-depth metadata or a filename label; unknown FLAC retains the existing fallback.
- **Automated verification:** on exact PR head `ac43126efdea9a6ac5cbe36d81b26b11c23da509`, Python syntax/full unittest workflow #141 and Docker packaging workflow #48 both passed. The Docker workflow included dependency installation, compilation, full unit tests, and image build.
- **Manual verification:** user tested the PR20 build in the existing `prox-mcp-pr17-test` environment and reports all is good, including Settings behavior. This is user-reported UI verification.
- **Deployment:** PR merge is complete. No image publication or production deployment was performed as part of this session; do not infer the server is running this commit.
- **Next:** continue from GitHub `main`. Publish/deploy separately if requested, then record the exact image digest and verify the running service.

## Latest session — 2026-10-12 (PR #17 merged; workflow documentation merged)

- **PR #17:** squash-merged at `9f4ff509d6a336823912c49d8c049eeea8761b8f`. User reports completed downloads now appear imported; acquisitions failing due to unavailable sources are expected. No import-safety checks were weakened.
- **PR #18:** could not be merged because its project-status edit conflicted with the PR #17 update. Closed as superseded, with its workflow content preserved in replacement PR #19.
- **PR #19:** [docs: reconcile GitHub-first workflow and project handoff](https://github.com/abucalip/navi-librarian/pull/19), squash-merged at `fe60dd3aaf323bd6f3489f89b13ee9946ba7f382`. Added `docs/DEVELOPMENT_WORKFLOW.md`, recorded decision D-009, and updated this status and `PROJECT_LOG.md`.
- **CI on PR #19 head** `bca1b143f45b870492f99c86ecdc5ef9ed9d6ec7`: Python syntax/acquisition-safety workflow #136 passed; Docker packaging workflow #43 passed, including compilation, unit tests, and Docker image build. Documentation-only change.
- **Deployment:** no image publication or production deployment was performed. The merges and packaging validation do not prove that the server is running a new image.
- **Next:** continue from GitHub `main`. If a release is requested, separately publish/pull the image, record its digest, and verify the running service.

## Latest session — 2026-10-12 (PR #17 merged; acquisition behavior manually verified)

- **PR #17:** [Diagnose acquisition completion and handle missing slskd transfers](https://github.com/abucalip/navi-librarian/pull/17) was squash-merged into GitHub `main` at merge commit `9f4ff509d6a336823912c49d8c049eeea8761b8f`.
- **Manual verification:** the user reports completed downloads now appear imported. Some acquisitions failed because no sources were available; the user confirmed this is expected and not a regression.
- **Fixes retained:** bounded acquisition-completion diagnostics; HTTP 404 from slskd's per-peer transfer endpoint is treated as an empty current transfer list while filesystem completion checks continue; non-404 HTTP errors still surface. Import-safety checks were not relaxed.
- **CI:** Python syntax/full unittest workflow #134 and Docker packaging workflow #41 passed on PR #17 head `ff2153bbaf790b2c0bbfce03c8c7fdb6c7decc12` before merge. User's manual report adds runtime evidence for completed imports.
- **Deployment:** merge does not establish that a new Docker image was published or that the server was updated. No deployment was performed in this session.
- **Documentation workflow:** PR #18's GitHub-first workflow content is being carried forward in a fresh branch based on the updated `main`, because its original branch conflicted after PR #17 merged. The replacement PR will be the merge target; no local-only code or commits are involved.
- **Next:** merge the reconciled documentation PR, then treat image publication/deployment as a separate step if requested.

## Latest session — 2026-10-12 (slskd monitor-error follow-up; fix in progress)

- **User-reported failure:** several acquisitions entered `monitor_error`. Their persisted details showed `HTTPStatusError: 404 Not Found` from `GET /api/v0/transfers/downloads/{username}` for multiple peers.
- **Root cause:** the watcher treated a missing per-peer transfer-list entry as an exception even though slskd may no longer expose a peer under that endpoint after its transfer records disappear. This caused an ordinary “no current transfer records” condition to surface as a monitor failure.
- **Fix committed on the existing PR #17 branch:** `_slskd_download_transfer_files` now returns an empty list for HTTP 404. The watcher continues its filesystem checks on each polling cycle; all other HTTP errors still raise and remain diagnosable. No import or folder-matching safety checks were relaxed.
- **Regression test added:** `tests/test_slskd_transfer_lookup.py` covers the 404 case, a non-404 HTTP error, and successful transfer parsing.
- **Commits:** fix `4ced0a22b980325dde58609087700d0926b65bde`; test `e946d460acc11fb675bd25c1358ef3d243c32dd5`; test-plan documentation `4ee60d4151899ad5406da979c00d7995e7e8f768`.
- **Verification:** user previously reported 47 tests passed on the earlier PR #17 revision (`17a2bdc`). On code commit `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd`, GitHub Actions Python syntax/test workflow #131 passed (compile plus full `unittest discover`) and Docker packaging workflow #38 passed (dependency install, compile, unit tests, Docker build). Subsequent commit `221dcaca3fe23f44dc69e68e3a5eef694a8754d8` changed only `PROJECT_LOG.md`; no local test run or manual acquisition retest has occurred.
- **State:** PR #17 remains open; this branch is not merged or deployed. The current task is to run the full test suite and CI on the new head, then have the user retest acquisitions. If monitor errors persist, capture the new status details rather than assuming this is the only possible failure.
- **Next:** verify the updated branch with syntax checks, the full unittest suite, and CI; inspect the final diff before merging.

---

## Latest session — 2026-10-12 (v0.2 P0: completed-folder diagnostics in progress)

- **Objective:** diagnose why a transfer reported complete remains in `download_complete_waiting_for_folder`, without weakening folder identity or track-completeness checks.
- **Branch:** `fix/v02-acquisition-completion-diagnostics`, based on GitHub `main`; this is separate from the user's local-only testing baseline `main` at `90e1d97`. Do not assume the two baselines are identical.
- **Implementation in progress:** added `acquisition_completion.py` to inspect completed-download folders and return a bounded set of actionable reasons; integrated those diagnostics into the watcher status details; added focused tests in `tests/test_acquisition_completion.py`.
- **Safety invariant:** only a unique folder with the expected basename and all expected files accepted by the existing strict matcher can be imported. Diagnostics do not relax matching.
- **Verification state:** GitHub Actions Python syntax/test workflow #123 passed on code commit `53309559c4e910779575fee3fc9941a596f78ac1`, including the full unittest discovery run. Docker packaging workflow #30 also passed, including Docker image build. This verifies packaging only, not deployment. No local test run was performed. The folder-name mismatch is a diagnostic fixture, not proof that it is the production failure's actual cause.
- **Next:** inspect the full diff, run syntax and full unit tests in CI, address failures, then use the emitted diagnostics to establish the real-world root cause before deciding whether a matching behavior change is justified.
- **Deployment:** not merged, published, or deployed.

---

## Latest session — 2026-10-12 (local main consolidated for testing)

- **Local merge:** the user merged `fix/artwork-size-and-artist-bios` into local `main`; the local merge commit is `90e1d97` (`Merge local artwork and acquisition fixes`). Local branch listing confirms this commit is the head of `main`.
- **Testing workflow:** the user reports that `main` passed their tests. The exact commands, test names, and output were not provided in this session, so this is recorded as user-reported validation rather than independently reproduced test evidence.
- **Purpose:** use local `main` as the sole testing ground going forward. Keep the feature branch as a temporary reference until the merged state is comfortably established; avoid deleting branches or cleaning worktrees without checking their contents first.
- **Remote/deployment boundary:** this local merge has not been confirmed pushed to GitHub and this session did not deploy anything. The remote default branch and server must not be assumed to contain commit `90e1d97`.
- **Session actions:** inspected the available local branch/status/log views and current GitHub documentation. The connected local Git tool is read-only, so the documentation handoff is being recorded on GitHub; local working-tree documentation was not edited directly.
- **Next:** continue development/testing from local `main`. If this merged code should become the shared release baseline, review the diff against remote `main`, then push through the normal Git workflow and verify CI before considering deployment.

## Latest session — 2026-10-12 (PR #16 merged; image published)

- **PR:** [#16 — Fix artwork loading after transient provider failures](https://github.com/abucalip/navi-librarian/pull/16), squash-merged into `main`.
- **Merge commit:** `ac0eec1e628caa0b300e651fcbdbe25535515395`.
- **Fix:** artwork provider failures are retryable and not negative-cached; browser retries transient failures with bounded backoff. Album-year and artwork request promises now use separate caches, fixing the all-covers-missing regression discovered during manual testing.
- **Regression tests:** `tests/test_artwork_retry.py` and `tests/test_artwork_cache_isolation.py`.
- **CI:** Python syntax/test workflow run #114 passed; Docker packaging run #22 passed. Docker publish workflow run #11 passed for merge commit `ac0eec1e628caa0b300e651fcbdbe25535515395`.
- **Published image:** `ghcr.io/abucalip/navi-librarian:latest` and `ghcr.io/abucalip/navi-librarian:sha-ac0eec1`; manifest digest `sha256:7a9415a7e6d10bd9864a2e03db8c452cfdc35cb69359eaa0e9b0552552afb5b1`.
- **UI verification:** user tested the PR build and reports album artwork now loads very fast.
- **Deployment distinction:** image is published, but this session did not have access to the media VM's Docker/Compose shell and did not pull/recreate the production container. Host deployment is pending; follow `docs/DEPLOYMENT.md` and record the running image digest after the host update.
- **Next:** pull and recreate only `navidrome-librarian` on the media VM, then verify container health and artwork in the deployed UI. Sync local Git without overwriting unrelated local changes.

# Project status and handoff

Last updated: 2026-10-13

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
| Audio quality priorities | PR #20 merged; automated CI and user manual Settings drag/drop/save/reload testing passed | Deployment of the merged commit is separate and not verified here |
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
