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
