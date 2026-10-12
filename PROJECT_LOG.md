# Navidrome Librarian — Development Log & Handoff

Update this file at the end of every GitHub development session. Keep entries concise: current branch/PR, changed behavior, validation, known caveats, and the next step.

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
- **Tests:** added `tests/test_app_auth.py` for username/password policy, salted password hashing, signed session integrity, expiry, and username binding. CI and browser testing for this authentication change are still pending.
- **Operational note:** back up the persistent data directory, including `app_auth.key`; losing that key invalidates active sessions. The app account is separate from Navidrome credentials. Do not merge/deploy until CI and unauthenticated/login/setup/logout smoke tests pass.
- **Next:** run syntax compilation and all unit tests in the isolated test worktree, then verify first-run setup, rejected unauthenticated API access, successful login, refresh persistence, and logout before proceeding to Docker packaging.
