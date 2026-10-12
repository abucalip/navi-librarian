# Navidrome Librarian — Development Log & Handoff

Update this file at the end of every GitHub development session. Keep entries concise: current branch/PR, changed behavior, validation, known caveats, and the next step.

## 2026-10-12 — New releases and recommendation quality

- **Branch:** `feature/new-releases-and-recommendation-quality` (based on `main`).
- **Scope:** active-download count in navigation; exclude non-album releases/compilations/remixes; show release years consistently; improve slskd album-folder matching and diagnostics; one deep-dive card per artist per genre row; replace Listening Profile UI with New Releases; refresh the listening-profile summary automatically in the background.
- **New Releases definition:** MusicBrainz release groups from the last two calendar years, only artists represented in the Navidrome library who have at least one owned album with six or more tracks. Initial scan is bounded to 120 library artists, ranked by library album count; lookups are cached.
- **Acquisition matching:** preserve file-size and expected-track completeness safeguards; relax album-name matching for punctuation/edition suffixes and avoid conflating same-named folders from different remote paths. Import safety remains unchanged.
- **Validation:** regression tests added for album eligibility and tolerant slskd album-title matching. GitHub reports no check runs/statuses yet; the workflow branch-filter change is in this PR, while GitHub evaluates PR workflows using the base branch's workflow configuration.
- **Deployment:** not deployed or merged. The branch is available for local sync and tests; do not merge until the Python tests and UI smoke tests pass.
- **Next:** sync this branch into a separate local worktree, run `python -m py_compile navidrome_server.py app/main.py tests/test_acquisition_safety.py` and `python -m unittest discover -s tests -v`, then smoke-test New Releases, album filtering, deep-dive rows, acquisition badge/year, and a known slskd search.
