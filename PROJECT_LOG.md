## 2026-10-12 — PR #17 merged; acquisition completion manually verified

- **PR:** [#17 — Diagnose acquisition completion and handle missing slskd transfers](https://github.com/abucalip/navi-librarian/pull/17), squash-merged into `main` at `9f4ff509d6a336823912c49d8c049eeea8761b8f`.
- **Behavior:** missing slskd per-peer transfer entries (HTTP 404) now produce an empty current transfer list, while filesystem completion inspection continues. Other HTTP failures remain errors; import safeguards are unchanged. Bounded diagnostics identify absent, incomplete, ambiguous, or mismatched completed-download folders.
- **Validation:** CI Python syntax/full unit suite #134 and Docker packaging #41 passed on tested PR head `ff2153bbaf790b2c0bbfce03c8c7fdb6c7decc12`. User manually reports that completed downloads now appear imported. Acquisitions failing due to no available sources are expected.
- **Deployment:** no image publication or production deployment was performed in this session.
- **Documentation:** GitHub-first workflow guidance from PR #18 is being reapplied on a branch based on the post-merge `main`, because the original PR branch conflicts after PR #17.

## 2026-10-12 — GitHub-first development workflow documentation

- Added `docs/DEVELOPMENT_WORKFLOW.md` and decision D-009: GitHub is the sole source of truth; the assistant authors/commits changes; local checkouts are for testing exact GitHub revisions; local-only commits are never reconciled into authoritative PR branches; merge, publish, deploy, and verify are distinct states.
- The original PR #18 branch conflicted with the updated main in `docs/PROJECT_STATUS.md`. The documentation is being transferred to a fresh branch based on current main to preserve the PR #17 handoff without overwriting it.

## 2026-10-12 — PR #17 follow-up: slskd monitor errors

- **User-observed error:** multiple acquisitions entered `monitor_error` with `HTTPStatusError: 404 Not Found` from slskd's per-peer transfer-list endpoint.
- **Root cause:** the watcher treated a missing current transfer-list entry as an exceptional failure. The completed-download filesystem is already checked independently on each poll, so an absent transfer record should not stop monitoring.
- **Fix:** `_slskd_download_transfer_files` returns an empty list for HTTP 404 and continues to raise for other HTTP errors. The strict file/folder checks before import are unchanged.
- **Regression tests:** added `tests/test_slskd_transfer_lookup.py` for 404, non-404 error propagation, and successful payload parsing.
- **Commits:** implementation `4ced0a22b980325dde58609087700d0926b65bde`; test `e946d460acc11fb675bd25c1358ef3d243c32dd5`; test-plan update `4ee60d4151899ad5406da979c00d7995e7e8f768`; handoff update `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd`.
- **PR:** [#17 — Diagnose acquisition completion and handle missing slskd transfers](https://github.com/abucalip/navi-librarian/pull/17), open, not merged/deployed. Latest head is `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd`.
- **Verification:** GitHub Actions Python syntax/test workflow #131 passed on code commit `9bfa12c42a4cf73f4eafd627be90949f7dd11bbd` (compile plus full `unittest discover`); Docker packaging workflow #38 passed on that same commit (dependencies, compile, tests, image build). The user has not yet retested acquisition behavior. Later commits update documentation only.
- **Next:** have the user test the latest PR revision and check the acquisition statuses. If monitor errors persist, capture updated `details.error_message` values; don't assume this is the only possible failure.

## 2026-10-12 — Local feature branch merged into main for testing

- **Local branch:** `fix/artwork-size-and-artist-bios` merged into `main` with merge commit `90e1d97` (`Merge local artwork and acquisition fixes`).
- **Validation:** user reports that local `main` passed their tests. Exact commands and output were not captured, so no more specific automated-test claim is made.
- **Workflow decision:** `main` is now intended to be the single local testing ground. Keep the source feature branch temporarily; do not delete it or clean up worktrees until no longer needed.
- **Scope boundary:** this is a local merge. No push to GitHub or deployment was confirmed in this session. Do not infer remote or server state from local commit `90e1d97`.
- **Documentation:** updated the project handoff on GitHub because the available local Git connector is read-only; these documentation commits do not push the local application merge.
- **Next:** continue testing from local `main`. Before publishing, inspect the local-vs-remote diff, push intentionally, and confirm CI on the pushed commit.

## 2026-10-12 — PR #16 merged and Docker image published

- **PR:** [#16 — Fix artwork loading after transient provider failures](https://github.com/abucalip/navi-librarian/pull/16), squash-merged to `main` at `ac0eec1e628caa0b300e651fcbdbe25535515395`.
- **Code:** transient artwork-provider failures are marked retryable and are not negative-cached; frontend retries with bounded backoff. Fixed a separate frontend cache collision by isolating `albumYearRequests` from `artworkRequests`.
- **Tests/CI:** `tests/test_artwork_retry.py` and `tests/test_artwork_cache_isolation.py`; Python syntax/test workflow #114 and Docker packaging workflow #22 passed. Docker publication workflow #11 passed.
- **Image:** `ghcr.io/abucalip/navi-librarian:latest`, `ghcr.io/abucalip/navi-librarian:sha-ac0eec1`, digest `sha256:7a9415a7e6d10bd9864a2e03db8c452cfdc35cb69359eaa0e9b0552552afb5b1`.
- **Manual test:** user reports album artwork loads very fast in the tested PR build.
- **Not done:** production container was not pulled/recreated; no direct shell/deployment connection to the media VM was available. Do not label host deployment verified until Compose update and post-deploy smoke test are recorded.
- **Next:** update the host container safely and sync local Git without disturbing the user's existing modified checkout.

# Navidrome Librarian — Development Log & Handoff

Update this file at the end of every GitHub development session. Keep entries concise: current branch/PR, changed behavior, validation, known caveats, and the next step.

## 2026-10-12 — Artwork loading reliability fix (in review)

- **Branch:** `fix/artwork-loading-retries`.
- **Manual-test regression discovered:** user reported that no artwork loaded when testing the PR. The frontend reused a shared artist+album promise cache for both `/api/album-year` and `/api/artwork`; when the year request populated the key first, artwork received the year-only response and never assigned an image URL.
- **Fix:** isolate year lookups in `albumYearRequests`, leaving `artworkRequests` dedicated to `/api/artwork`. Added `tests/test_artwork_cache_isolation.py` to guard the separation.
- **Status:** fix and regression guard committed to this PR branch; CI and user retest are pending. Do not merge/deploy until verified.
- **Root cause:** `/api/artwork` swallowed provider exceptions and cached them as a normal negative result for five minutes. The browser marked a card requested and unobserved it on the first attempt, so a transient Deezer outage could leave artwork blank for the rest of the page session.
- **Change:** provider exceptions now return a retryable marker and are not cached; browser retries up to three times with bounded backoff. Ordinary no-match responses remain cached as before.
- **Regression coverage:** `tests/test_artwork_retry.py` tests that provider timeouts are retryable and not negative-cached.
- **Validation:** GitHub Actions passed Python compilation and the full unittest suite (run #110) and Docker packaging validation (run #17) on code commit `fabcd1fb6563ef9cd65aa12005f2f77f3f90e07d`. Manual UI behavior remains unverified.
- **Status:** open PR #16; not merged or deployed. The local checkout on `fix/artwork-size-and-artist-bios` was not modified.
- **Next:** create/check the PR, run the full automated suite and CI, and manually verify artwork on Discoveries and Artist Deep Dives against the deployed app.

## 2026-10-12 — Successful server installation and baseline smoke tests reported

- **User-reported deployment:** Librarian is installed on the server; the Docker package has been made public.
- **User-reported working flows:** first-run account creation, entering service credentials through Settings, downloads, and imports all work as intended.
- **Documentation updates:** corrected `docs/PROJECT_STATUS.md` and `docs/DEPLOYMENT.md`. The earlier GHCR `unauthorized` note is no longer an active blocker according to the user's update.
- **Evidence boundary:** these are the user's direct test results. This session did not independently inspect the live host, container logs, published image digest, or repeat application tests. The deployed image tag/digest and host details remain to be recorded at the next release/update.
- **Changes in this session:** documentation only; no application code or server configuration changed. No tests were run in this documentation session.
- **Next:** preserve the working flows as regression baselines. Before v0.2 implementation, inspect the actual current code and tests, then prioritize a narrowly scoped acquisition-completion reliability fix with regression coverage. Record the exact image tag/digest at the next deployment.

## 2026-10-12 — PR #15 merged: v0.2 planning from DroppedNeedle review

- **PR:** [#15](https://github.com/abucalip/navi-librarian/pull/15), `docs: plan v0.2 improvements from DroppedNeedle review`, squash-merged into `main`.
- **Merge commit:** `f32b02a13b582e23699bde294eb94b51e5f646cc`; follow-up project-status documentation commit: `5f879818a0d3ea315c88dd302610d990eba32602`.
- **Document:** `docs/V0.2_DROPPEDNEEDLE_LESSONS.md` records prioritized proposals for acquisition completion evidence/diagnostics, safe lifecycle boundaries, consistent quality evaluation, recommendation pipeline clarity, caching review, and regression/performance guardrails.
- **Constraints captured:** DroppedNeedle has often been slow and buggy in the user's experience; smoothness and stability must not be sacrificed. Keep Librarian focused on the Navidrome–slskd bridge and library-/taste-aware recommendations. Split Python modules incrementally by clear responsibility. Review AGPL-3.0 implications before copying any code.
- **Validation:** GitHub Actions reported Python syntax check and Docker packaging validation successful on PR head `3e1f005e413a5522ec2866f30baebf1914cc4868`. Documentation-only change; no application tests or UI smoke tests were run.
- **Deployment:** not performed because no application code or image changed. Runtime remains unverified and the existing GHCR `unauthorized` pull blocker remains unresolved.
- **Local checkout:** preserved on `fix/artwork-size-and-artist-bios`, clean and six commits ahead of its recorded origin. No local checkout, reset, or cleanup was performed.
- **Next:** before implementing v0.2, inspect the actual current code/tests and start with a narrowly scoped acquisition-completion reliability fix plus regression tests. Resolve GHCR authorization before the next application deployment.

## 2026-10-12 — New releases and recommendation quality

- **Branch:** `feature/new-releases-and-recommendation-quality` (based on `main`).
- **Scope:** active-download count in navigation; exclude non-album releases/compilations/remixes; show release years consistently; improve slskd album-folder matching and diagnostics; one deep-dive card per artist per genre row; replace Listening Profile UI with New Releases; refresh the listening-profile summary automatically in the background.
- **New Releases definition:** MusicBrainz release groups from the previous 730 days, only artists represented in the Navidrome library who have at least one owned album with six or more tracks. Initial scan is bounded to 120 library artists, ranked by library album count; lookups are cached.
- **Acquisition matching:** preserve file-size and expected-track completeness safeguards; relax album-name matching for punctuation/edition suffixes and avoid conflating same-named folders from different remote paths. Import safety remains unchanged.
- **Validation:** regression tests added for album eligibility, edition-suffix matching, and token-boundary false positives. GitHub reports no check runs/statuses yet; the workflow branch-filter change is in this PR, while GitHub evaluates PR workflows using the base branch's workflow configuration.
- **Deployment:** not deployed or merged. The branch is available for local sync and tests; do not merge until the Python tests and UI smoke tests pass.
- **Next:** sync this branch into a separate local worktree, run `python -m py_compile navidrome_server.py app/main.py tests/test_acquisition_safety.py` and `python -m unittest discover -s tests -v`, then smoke-test New Releases, album filtering, deep-dive rows, acquisition badge/year, and a known slskd search.

## 2026-10-12 — Acquisition test harness fix

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 (still open; not merged or deployed).
- **Issue:** Local test run compiled successfully but 11 acquisition/import tests errored because the AST-based test harness did not load the newly used `_discovery_filename_key` helper or provide its `unicodedata` dependency. This was a test-harness dependency omission, not a Python syntax error.
- **Fix committed:** `4e1498a` adds the helper to the selected test definitions and injects `unicodedata` into the isolated namespace.
- **Validation:** Not yet rerun after this fix. Next: fetch/pull the latest PR branch into the test worktree and rerun compile plus the full unittest suite. Do not merge until tests and UI smoke tests pass.

## 2026-10-12 — Card details, year coverage, and New Releases artist matching

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 (open draft; not merged or deployed).
- **User smoke-test feedback:** album years were visible only on New Releases; non-album filtering and one-artist-per-Deep-Dive-row behavior looked correct. New Releases included several purported 2026 releases for Queen, suggesting artist-name search collisions.
- **Year coverage:** all album-card types now request a year when metadata does not already provide one. Artwork lookup requires both artist and album to match closely before its release year is accepted, preventing an unrelated album by the same artist from supplying the year.
- **New Releases fix:** require an exact normalized artist name in MusicBrainz artist-credit data instead of a substring match (which could admit names such as “Queen Tribute”). Candidate albums still must pass the full-album/non-album exclusion filter.
- **Album details popup:** clicking the non-button area of dashboard, recommendation, discovery, or acquisition cards opens a modal with artwork, album/artist/year, tracklist, durations, and a Get button beside the artwork. Get-button clicks do not open the modal; Escape/backdrop/close button dismiss it. Tracklist lookup uses an exact artist+album match in Deezer and fails safely when no exact match is found.
- **Regression test:** added coverage proving exact `Queen` artist credits match while `Queen Tribute` and `The Queens` do not.
- **Validation:** code changes committed through GitHub; local syntax compilation, full unit tests, and UI smoke test for popup/year coverage/Queen results remain pending. Keep PR unmerged until validation passes.

## 2026-10-12 — All-card year rendering and platform links

- **Root cause of years appearing only on New Releases:** some renderers call `makeAlbumCardInteractive` before creating the card's `h3`. If the item already had a year, `applyAlbumYear` saved it in `data-release-year` but could not attach the badge because the title did not exist yet. The title was then created without the badge.
- **Fix:** all card types now default to a year lookup when metadata has no year. The shared `addTextElement` helper now checks for a saved `data-release-year` when an `h3` is created and adds the year badge at that point. This handles both asynchronous lookup results and years available before the title exists. Dashboard cards keep their existing explicit year rendering.
- **Popup platform buttons:** added ListenBrainz, Apple Music, Spotify, Qobuz, and Bandcamp buttons directly beneath the popup artwork. They open targeted artist+album searches in each service in a new tab (the app does not yet have authenticated/platform-specific album IDs to promise a canonical album URL).
- **Validation:** Python syntax CI, local full unit suite, and UI smoke test for card-year coverage and platform links remain to be checked. PR #12 stays draft, unmerged, and undeployed.


## 2026-10-12 — Rework year lookup, platform icons, and Various Artists exclusion

- **Year lookup:** separated year retrieval from artwork loading. Cards call a dedicated `/api/album-year` endpoint. MusicBrainz release groups are primary; only exact normalized album titles and exact credited artist names qualify. Deezer is a fallback only for an exact artist-and-album match. Positive results cache for 180 days; misses cache for six hours.
- **Year display:** added a shared badge-enforcement helper after title creation, including renderers that create headings manually instead of using `addTextElement`.
- **Platform links:** replaced text panels with compact, fixed-size logo icon buttons beneath the artwork; links keep accessible labels.
- **New Releases:** exclude Various Artists pseudo-artist entries before querying and again during candidate filtering; regression tests cover common aliases.
- **Validation:** automated syntax/unit tests and visual browser smoke tests have not yet been run against this update. PR #12 remains draft and is not merged or deployed.


- **CI update:** GitHub Actions Python syntax check passed on commit `dae861ee538f8b5837ef1c538f0ed1cf575aecb0` after the year-fetch and Various Artists changes. Official ListenBrainz/Qobuz image URLs were adjusted afterward; full unit tests and visual browser verification remain pending.

- **Additional year-rendering audit:** found that some metadata can contain a full date string (for example, `YYYY-MM-DD`), which `Number(value)` rejected, and one card renderer manually created its title without rechecking a late-arriving year. Added a shared year parser and applied the badge helper after every manually-created album heading.


## 2026-10-12 — Service settings and deployment configuration groundwork

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 remains open and unmerged.
- **Settings UI:** reorganized Settings into four service tabs: Navidrome, slskd, Last.fm, and ListenBrainz. Navidrome owns the library path; slskd retains its server URL, API key, completed-download path, and quality preferences.
- **Configuration:** added persistent Navidrome URL/username/password settings, optional Last.fm API key settings, and a configurable ListenBrainz username. Blank secret fields preserve existing credentials; settings APIs never return saved secrets. Navidrome credentials are resolved dynamically, so updates take effect without a process restart.
- **Persistence groundwork:** added `NAVIDROME_LIBRARIAN_DATA_DIR` for application SQLite state, preparing for a Docker-mounted `/data` volume. The discovery settings database remains permission-restricted.
- **Validation:** GitHub Actions passed Python compilation, acquisition safety regressions, and the new service-settings regression tests on commit `3c25182`. Browser UI/API smoke testing remains pending. Docker packaging is intentionally deferred.

## 2026-10-12 — First-run app account and login protection

- **Branch/PR:** `feature/new-releases-and-recommendation-quality`, PR #12 remains open and unmerged.
- **First-run setup:** a fresh installation prompts the owner to create a username and password; setup is disabled after the first account is saved. Username is validated and passwords must be at least 12 characters.
- **Authentication:** app routes and APIs are protected by a signed, HTTP-only, SameSite=Strict cookie with a 12-hour expiry. Passwords are stored only as PBKDF2-HMAC-SHA256 hashes with per-account random salts; the signing key is created in the persistent data directory with restrictive file permissions. Login attempts are rate-limited per client IP.
- **Session UX:** successful setup/login signs in immediately; a Log out button clears the browser cookie. Auth is required for API calls, acquisition actions, settings, and the web interface.
- **Tests:** added `tests/test_app_auth.py` for username/password policy, salted password hashing, signed session integrity, expiry, and username binding. GitHub Actions run #83 passed compilation and the full unittest suite, including the new authentication tests. Browser testing remains pending.
- **Operational note:** back up the persistent data directory, including `app_auth.key`; losing that key invalidates active sessions. The app account is separate from Navidrome credentials. Do not merge/deploy until CI and unauthenticated/login/setup/logout smoke tests pass.
- **Next:** run syntax compilation and all unit tests in the isolated test worktree, then verify first-run setup, rejected unauthenticated API access, successful login, refresh persistence, and logout before proceeding to Docker packaging. Use HTTPS (for example, the existing Tailscale HTTPS endpoint) when signing in over a network; plain HTTP does not protect passwords in transit.

## 2026-10-12 — Cassette app icon

- Used the user-provided vintage cassette image as the browser favicon and the app's header brand icon; also added it to the login/setup page.
- Current implementation references the provided Vecteezy-hosted image URL directly. Before final Docker packaging, preferably bundle a local copy under the app's static assets so the icon does not depend on external hosting. The image could not be fetched into the repository through the available runtime, so the URL remains external for now.
- No merge or deployment performed.


## 2026-10-12 — Rainbow cassette icon

- Replaced the previous cassette image URL in the favicon, app header, and login/setup page with the user-provided Vexels rainbow cassette image.
- **Local asset still pending:** the image is viewable through web browsing, but direct download from this runtime fails due to unavailable DNS/network access. The app still references the remote image; do not treat the icon as fully bundled for Docker yet. To complete the local-copy requirement, provide the PNG as a chat attachment or place it in the repository worktree, then update the page to reference the bundled static asset.
- No merge or deployment performed.


## 2026-10-12 — Bundle rainbow cassette icon locally

- Confirmed `cassette.png` is present at the repository root on PR #12's branch (31,390 bytes).
- Updated the favicon, login/setup image, and app header CSS to use the local `/assets/cassette.png` endpoint instead of the external Vexels URL.
- Added a FastAPI endpoint serving the repository-root PNG as `image/png`; this avoids external-host dependency. Docker packaging must include the root-level `cassette.png` file alongside the app source.
- No merge or deployment performed. Runtime/browser smoke test and CI for this change are still pending.


## 2026-10-12 — Project handoff documentation merged

- **PR:** [#14](https://github.com/abucalip/navi-librarian/pull/14), `docs: add project handoff and engineering runbooks`, merged into `main` via squash merge.
- **Merge commit:** `74264b29062504fce3bf6f7a65121fa43b9f8ec5`.
- **Files added:** `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/DECISIONS.md`, and `docs/TEST_PLAN.md`.
- **CI:** GitHub reported Python syntax check and Docker packaging validation passed for PR head `97e887fa8295fff55f05ac72101907bf08819a99`. This was documentation-only; no application tests or deployment were performed during the merge session.
- **Deployment:** still unverified. The previously reported GHCR `unauthorized` pull remains unresolved; do not treat merge/CI as deployment evidence.
- **Next:** review current PRs and local branches/worktrees before choosing the next implementation task; prioritize required regression testing and resolve GHCR package visibility/authentication before a registry-based deployment.
