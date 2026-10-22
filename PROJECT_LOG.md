## 2026-10-22 — PR #560 merged: artist bios for instrumentalists

- PR #560 squash-merged as `ffff550c2336ca3dcd56a301c9ae7fffe9f0104b` from exact head `0f2ae27562a175e237a7c7364d380dae7b49f5a0`. Root cause of the missing album-panel bio: `_ARTIST_DESCRIPTION_RE` in `app/services/artist_bio.py` had no instrument terms, so Wikidata descriptions such as "American jazz saxophonist" were rejected and the bio came back empty. Added instrumentalist and ensemble terms.
- Tests actually run: `tests/test_artist_bio_service.py` (7 pass), plus a direct endpoint call returning bios for John Coltrane, Bill Evans, and Art Blakey. Required CI (compile, container-smoke, test-and-build, validate-container, validate-release-workflow) passed on that exact head; publishing skipped. No browser check; not published or deployed.
- The owner confirmed the section-label size and Deep Dives card spacing items are done, which closes the 2a list.

## 2026-10-22 — Published image v0.2.2

- Owner explicitly authorized publication. Annotated tag `v0.2.2` was pushed at `0b1111114e0e751928312e76a287123061640343`, the then-current `main` head. All four required workflows had passed on that exact commit.
- Release workflow "Publish Docker release" run [39835121956](https://github.com/abucalip/navi-librarian/actions/runs/39835121956) succeeded (`publish-release`; the validation job was skipped for a tag push). It enforces tag == current `main`, runs the container smoke test, and builds `linux/amd64` and `linux/arm64` with provenance and SBOM.
- **Published:** `ghcr.io/abucalip/navi-librarian:v0.2.2` and `ghcr.io/abucalip/navi-librarian:sha-0b1111114e0e751928312e76a287123061640343`; package version digest `sha256:8ec36eaea585292f73ff7ec3546d96e4c5bc135b08fb3ccbcee789675f3f3ea2` (from the GitHub Packages API). `latest` was not moved.
- **Not verified:** per-platform manifests were not inspected, the image was not pulled or run, and no GitHub Release was created. Not deployed; no live-runtime verification. Manual browser checks for the included UI changes remain waived/not performed; PR #526/#527 runtime checks remain outstanding.

## 2026-10-22 — PR #558 merged: Deep Dives artwork loading improvements

- PR [#558](https://github.com/abucalip/navi-librarian/pull/558) squash-merged to `main` as `d44c01669611bd11acfaa4f1197905afed7f9f08`, from exact tested PR head `976c86e77034322e53cc7aea9691fa840c2d6146`.
- Review blockers were resolved before merge: capped MusicBrainz result sets are recursively split so a truncated response cannot cause a missing album year to be negatively cached, and regression coverage exercises that case. The PR was aligned to current `main`.
- **Automated verification on the exact PR head:** full unit suite and Docker build passed in workflow `39827794898`; Python syntax passed in `39827794888`; container runtime smoke passed in `39827794833`; validation-only multi-architecture image check passed in `39827794825`; release-workflow validation passed in `39827794824`. The publishing job was skipped as intended.
- **Manual browser verification:** explicitly waived by the owner and not performed. Deep Dives artwork performance was not re-measured in a browser, so UI behavior/performance is not claimed as verified.
- No image was published, no deployment occurred, and live runtime was not verified. Publishing/deployment remain paused.
- Documentation closeout commits: `docs/PROJECT_STATUS.md` `05cd398b17055cf8724c44f9fdf5fd3892a704eb`; `docs/ACTIVE_WORK.md` `64fd0b6f9b29dab956ef14656dbf8a84e14b8a7c`; `PROJECT_LOG.md` `1ecf065b69384711de24cba31c71e7bd89f272a5`.

## 2026-10-22 — PR #557 merged: similar-to discovery labels

- Merged PR [#557](https://github.com/abucalip/navi-librarian/pull/557) by squash. Merge commit on `main`: `45cf5abe0257e70fe0d0573365259c2d0c7c2c10`; exact tested PR head: `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`.
- Adds `discovery/similar_artists.py` and tests for similar-artist matching; the server includes `similar_to` in recommendation payloads, and Recommendations/Personal discovery rows show “Similar to: …” when related listening-profile artists are available.
- Required workflows passed on the exact PR head: Python syntax/acquisition safety run 39807842253; container runtime smoke 39807842257; Docker packaging, full unit suite and image build 39807842282; release workflow validation 39807842267 (the `publish-release` job was skipped); validation-only multi-architecture image check 39807842351. No claim that the suite was rerun on the merge commit.
- The owner explicitly waived manual browser verification; it was not performed. No image was published, no deployment occurred, and production runtime was not verified.
- Also retired the old `~/navi-librarian-test/test-pr.sh` workflow in `docs/LOCAL_UI_TESTING.md`; the guide now refers to the replacement local test environment without relying on the obsolete helper.
- Documentation closeout commits: `docs/PROJECT_STATUS.md` bfd8a25d06f7475a88f2e1bfc8c8fa10570ff653; `docs/ACTIVE_WORK.md` 8cbed8f810792d713be9cb30b843c79c484099ec; `PROJECT_LOG.md` pending this entry.

## 2026-10-22 — Retire obsolete local UI test helper instructions

- Updated `docs/LOCAL_UI_TESTING.md` in commit `a8a63764036c265a30e322adccf134b5485f8f6d`: explicitly marked `~/navi-librarian-test/test-pr.sh` obsolete, removed its commands and helper-specific setup/report assumptions, and retained a current browser checklist requiring exact-SHA identification, isolated test data, disabled acquisition services unless authorized, and recording pass/fail/skip results. The document points to the replacement local test environment without inventing an unverified launcher command.
- Updated `docs/PROJECT_STATUS.md` in commit `ee15bacdac965442c85fd4999faf15343024b581` to reflect the documentation change and PR #557's outstanding manual browser gate.
- PR #557 head remains `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`; automated full-suite and required CI evidence previously passed on that head. Manual browser testing has not been performed. The instruction to merge did not explicitly waive the documented manual UI gate, so the PR remains unmerged pending the browser check or an explicit waiver. No publishing or deployment occurred.

## 2026-10-22 — PR #556 review; reconciled replacement PR #557

- Reviewed PR #556, “Add ‘Similar to’ labels to Recommendations and Personal rows.” Its base was the feature branch from merged PR #555, so retargeting it to `main` would include duplicated/conflicting stacked changes. Closed #556 as superseded and created replacement PR [#557](https://github.com/abucalip/navi-librarian/pull/557) directly from current `main`, preserving only the intended four-file change.
- Replacement PR head: `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`. It adds a directly tested `build_similar_to_lookup` helper, attaches `similar_to` to normal and ownership-review payloads, and updates the UI labels. No provider calls or recommendation ranking budgets were added.
- The first syntax/guard run failed because `recommend_new_music()` reached 461 lines, above its 450-line ceiling. The lookup construction was moved into the reusable helper, with a regression test. The next run showed 452 lines, so redundant blank lines were removed; the final exact-head syntax/size guard passed. No guard thresholds were changed.
- **Full unit suite:** passed on the exact final head in Docker packaging workflow run `39807842282`, job `test-and-build`; Docker image build also passed.
- **Required workflows on exact final head:** Python syntax/acquisition-safety run `39807842253` passed; container runtime smoke `39807842257` passed; Docker packaging/full unit suite/build `39807842282` passed; validation-only multi-architecture image check `39807842351` passed. Release workflow validation `39807842267` passed with its publishing job skipped.
- **Manual UI verification:** not performed in this session. `docs/LOCAL_UI_TESTING.md` requires browser checks against the exact tested SHA for UI-facing changes. PR #557 remains open and unmerged pending that gate. The owner may test with `~/navi-librarian-test/test-pr.sh 557` or explicitly waive the manual gate.
- No image publication, deployment, or live-runtime verification.
- **Next action:** complete or explicitly waive manual browser testing for exact head `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`; then recheck PR state and merge only if the gate is satisfied.

## 2026-10-22 — PR #555: artist bios and dashboard discovery UI refinements

- **PR #555** squash-merged as `f80254550369ed56b66e114faebb2b9fb72ed6bf` from exact head `58bbe0e4ef7320c14146a6fa4ea5a3ef0d266953`.
- Changes include the Wikidata `Accept: application/json` header and avoiding a 24-hour empty-bio cache when the Wikidata search request fails; artist bios on dashboard and discovery cards; removal of New Releases source/reason text; more specific low-confidence genre messaging; consistent “Adventurous discovery” labels; responsive row artwork sizing; Deep Dives album-year placement; smaller one-line category tags; and yellow year styling. Three artist-bio regression tests were added.
- **Full unit suite:** passed in GitHub Actions on the exact PR head, run `39806088731`, job `test-and-build` (“Run unit tests” succeeded). Docker image build succeeded in the same job.
- **Required workflows on exact head:** Python syntax check `39806088756` passed; container runtime smoke test `39806088730` passed; Docker packaging/full unit suite/build `39806088731` passed; validation-only multi-architecture image check `39806088814` passed. Release workflow validation `39806088786` passed with the publishing job skipped.
- **Manual UI verification:** the owner reported the PR was manually tested in the browser and all is working well. No separate browser test was run in this session.
- No image publication, deployment, or live-runtime verification. The existing publication/deployment pause remains in effect.
- **Next action:** retain the runtime-verification priority in `docs/ACTIVE_WORK.md`; do not publish or deploy.

## 2026-10-22 — PR #554: larger row artwork and artist bio on discovery rows

- **PR #554** squash-merged as `c9fcf3289f37984258aca5b62891d700c569d5c1` from exact head `8c8d473f3b9576fbf0dc278c702b9843b422d991` (branch `feat/dashboard-row-bios`, two feature commits plus one review fix). Ranked-row artwork is 96px (80px up to 1200px wide, 64px up to 620px wide). The artist bio now shows in the middle of every row on Recommendations, New releases, and Personal discoveries (previously only genre-connected Personal rows). "Add to your collection" and Saved rows are unchanged.
- Rows keep one height (the artwork size). The bio is clamped to two lines with an ellipsis; a bio that does not fit becomes a keyboard-operable toggle (`role="button"`, `aria-expanded`, Enter/Space) that grows only its own row and does not open the album panel. A review pass caught that the first CSS edit had also enlarged acquisition-row artwork; this was reverted before merge.
- **Tests run (focused only):** all `tests/*ui_contract.py` (251 passed) and `node --check static/app.js`. New contract file `tests/test_row_bio_expand_ui_contract.py`; the title-clamp count test now allows the bio clamp. The full unit suite was not run locally.
- **CI on the exact head:** Python syntax check, container runtime smoke test, and release-workflow validation passed. Docker packaging (`Validate Docker packaging`, run `39796796155`, which runs the full unit suite) and `Validate Docker image (publishing paused)` (run `39796795957`) had **not completed** when this entry was written, and the PR was merged before they finished. Their results are not recorded here; check them on `main`.
- **Manual browser check (`LOCAL_UI_TESTING.md`, `test-pr.sh 554`):** performed by the owner against this head, reported as "tested and working". Specific checklist items were not itemized, and performance was not measured.
- No image publication, deployment, or live-runtime verification.
- **Next action:** confirm the remaining CI runs for `c9fcf3289f37984258aca5b62891d700c569d5c1` finished green, then continue with the next item in `docs/ACTIVE_WORK.md` section 2a ("Similar to:" labels).

## 2026-10-22 — Live-runtime verification attempt for PRs #526 and #527 blocked by access

- Re-read current project status, requirements, development workflow, test plan, active work, and the merged PRs. Current `main` before this documentation update was `fbc806badd9006853d2ccab45af19101809cb15a`.
- Confirmed PR #526 is merged as `4fcd5ff78dc7cfebe99d289a49cd8505c6ca9138`; it retries only failed tracks from the same source, at most three times 30 seconds apart, and keeps a 15-minute recovery grace. Its automated regression tests and CI do not establish behavior against real slskd state strings or queue operations.
- Confirmed PR #527 is merged as `e03f4b35c66745f71b45f01481dbed5547c7a45e`; masked artist variants are inserted after the unmasked query. Its automated tests do not establish live search behavior or real no-match diagnostics.
- **Runtime verification not performed:** this session has no connection to the running Librarian host or slskd API. These changes have not been published/deployed. No live search was issued, no transfer was queued, and no production data was changed. Publishing/deployment remain paused.
- **Next action:** arrange authorized access to an isolated Librarian test instance connected to the real slskd service. Test failed-track retry/recovery using an isolated test acquisition, then test masked queries and no-match diagnostics. Do not claim completion until results are captured; do not use a production transfer as a test substitute.

## 2026-10-22 — Reconciled and merged PRs #530–#535

- **PR #530 — imported-album filtering:** squash-merged as `0b2bda011b86d2c08a0179e5df801c7891c10f9a` from exact tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`. Required workflow runs passed: syntax/acquisition safety `39780311719`, Docker packaging/full unit suite/build `39780311736`, container smoke `39780311752`, validation-only multi-architecture `39780311800`, and release validation `39780311809` (publishing skipped).
- **PR #531 — mobile navigation:** original stacked PR closed as superseded. Reconciled replacement PR #546 merged as `f884f004de83a6c373c16699b560e25312b41a3d`, tested head `53026bcbff794c04b6f901aefeb4fa939403cd7e`. Required workflows passed on that exact head: syntax `39782554896`, Docker packaging/full unit suite/build `39782554899`, container smoke `39782554893`, validation-only multi-architecture `39782554867`, release validation `39782554862` (publishing skipped).
- **PR #532 — artist bio in album panel:** original stacked PR closed as superseded. Reconciled replacement PR #547 merged as `4e11053ae5d203a4287a27abb162b4a9d093bf60`, tested head `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a`. Required workflows passed on that exact head: syntax `39782630505`, Docker packaging/full unit suite/build `39782630071`, container smoke `39782630499`, validation-only multi-architecture `39782630190`, release validation `39782630442` (publishing skipped).
- **PR #533 — equal-width ranked rows:** reconciled original branch without force-pushing and merged as `8beb5baac431e6916d434efd111d96d98c4b8d9b` from exact final head `2948e56185608c8c3d798f38690f022253831940`. Required workflows passed on that exact head: syntax `39783301040`, Docker packaging/full unit suite/build `39783300845`, container smoke `39783300851`, validation-only multi-architecture `39783300775`, release validation `39783301000` (publishing skipped).
- **PR #534 — stable acquisition rendering:** reconciled original branch without force-pushing and merged as `871d3dd4401e493315e38f021bcdeec7918e0900` from exact final head `aea6b57045f2de06cf2eba89d99663d58b6dc699`. Required workflows passed on that exact head: syntax `39783571973`, Docker packaging/full unit suite/build `39783572017`, container smoke `39783571955`, validation-only multi-architecture `39783572002`, release validation `39783571972` (publishing skipped).
- **PR #535 — card artwork loading:** reconciled original branch without force-pushing and merged as `785715320c45b0e79d5f93873953b85859d4891f` from exact final head `15a2195685af26eaab69246a4069e928336692a6`. Required workflows passed on that exact head: syntax `39783827113`, Docker packaging/full unit suite/build `39783827065`, container smoke `39783827116`, validation-only multi-architecture `39783827092`, release validation `39783827150` (publishing skipped).
- The owner explicitly waived manual browser checks for this merge batch; none were performed. No artwork before/after performance measurement was made. No image publication, deployment, or live-runtime verification occurred. All temporary validation PRs were closed. The original #531/#532 PRs were closed as superseded; #530 and #533–#535 were merged directly.
- **Next action:** verify the already-merged #526 and #527 behavior against the live slskd runtime only with appropriate authorization; do not publish or deploy.

## 2026-10-22 — Open PR review and full-suite validation for PRs #530–#535

- Reviewed all six open product PRs. PR #530 (imported-album cache filtering) has no code-review blocker identified and its exact final head `df3dd651051826f483831b5a868dd16483f75fa4` passed all required CI, including the full unit suite: syntax/acquisition-safety run 39772679218; Docker packaging/full suite/build 39772679339; container smoke 39772679292; validation-only multi-architecture image 39772679145; release workflow 39772679160 (publishing job skipped; validation-only job passed).
- Reviewed UI stack PRs #531–#535. Main findings: all five are stacked on branches rather than `main`, starting from closed stale PR #529; required workflows filter pull requests to `main`, so there were no CI runs on their original head SHAs. Manual browser checks required by `docs/LOCAL_UI_TESTING.md` have not been performed. Do not merge these original PR heads until the stack is rebased/reconciled and final-head CI plus browser checks are complete.
- To exercise the cumulative UI changes against current `main` without altering original PR branches, created temporary validation-only commits by overlaying the changed-file state through each PR onto current main, then closed the temporary validation PRs after testing. These commits are integration test candidates, not the original PR heads:
  - Through #531: `53026bcbff794c04b6f901aefeb4fa939403cd7e`; all four workflows passed (syntax 39779026542; full suite/build 39779026314; smoke 39779026388; non-publishing multi-arch 39779026309; release validation 39779026400).
  - Through #532: `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a`; all four passed (syntax 39779175672; full suite/build 39779175738; smoke 39779175835; non-publishing multi-arch 39779175783; release validation 39779175705).
  - Through #533: `da4a3e72146ec60c8c0c700f4ed5f387bf864723`; all four passed (syntax 39779276986; full suite/build 39779276674; smoke 39779276863; non-publishing multi-arch 39779276675; release validation 39779276967).
  - Through #534: `d319d8c5cc5f661a834035dabf99a26a1431655a`; all four passed (syntax 39779388308; full suite/build 39779388280; smoke 39779388596; non-publishing multi-arch 39779388383; release validation 39779388204).
  - Through #535: `1d803c6f1daf198d3c77741cbbb5c51eb5c490e0`; all four passed (syntax 39779671933; full suite/build 39779672016; smoke 39779672162; non-publishing multi-arch 39779671942; release validation 39779672201).
- Release workflow publishing jobs were skipped; validation-only multi-architecture builds passed. No image was published, no deployment occurred, and no manual browser or live-runtime verification is claimed. The local checkout attempt failed because the environment could not resolve github.com; full-suite evidence above comes from GitHub Actions.
- No product PR was merged. Next action: review/merge #530 if desired, then reconcile #531–#535 onto current main and run required checks on the actual final PR heads plus manual browser checks.

## 2026-10-22 — PR #529 reconciled; full CI suite passed on replacement PR #530

- Closed stale PR #529 because its branch predated the current `main` and its `discovery/list_payload.py` version omitted PR #528's cached future-release filter. Replacement PR #530 is based on current `main` and retains both behaviors.
- Exact tested PR #530 head: `34b926249a6e71aeab4e2243500fa91eb47e226b`; compare reported 3 commits ahead, 0 behind at review time. Changed files: `discovery/list_payload.py`, `navidrome_server.py`, `tests/test_discovery_list_payload.py`.
- Regression coverage hides imported acquisition identities across lists, excludes library-owned items from non-personal lists, preserves the future-date filter, and keeps imported items hidden when the library snapshot fails.
- Exact-head CI: Python syntax/acquisition safety run 39772357314 passed; Docker packaging/full unit suite/image build run 39772357012 passed (the full unit-test step succeeded); container runtime smoke run 39772356995 passed; validation-only multi-architecture image run 39772356972 passed. Release workflow run 39772357053 skipped the publishing job; its validation-only build completed successfully. No image was published.
- PR #530 remains open and unmerged. No manual browser or live-library/runtime check was performed; not published or deployed. Next action: review final PR state and merge #530 if all gates remain green, then continue live-runtime verification of #526/#527.

## 2026-10-22 — PR #528 merged: hide future-dated New Releases

- Squash merge commit on `main`: `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750`; exact tested PR head: `295148dcf817479f4098195200ada4c4173733fe`.
- Candidate selection now excludes release groups dated after today, including partial dates using their earliest possible day. Cached New Releases responses also hide stored future-dated items, so stale cached lists are corrected on read.
- Regression coverage: `tests/test_discovery_new_releases.py` and `tests/test_discovery_list_payload.py`; PR report records 46 focused tests passing and `py_compile` on `navidrome_server.py`.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety run 39770936745; Docker packaging/full unit suite/build 39770936858 (unit tests and image build passed); container runtime smoke 39770936556; validation-only multi-architecture image validation 39770936564. The release workflow's publishing job was skipped; its validation job passed.
- Full unit suite was run by CI on the exact PR head, not separately in the agent environment. No manual browser check or live-library verification was performed. Not published, deployed, or runtime-verified.
- Removed the resolved future-release bug from `docs/ACTIVE_WORK.md`; `docs/PROJECT_STATUS.md` records the merge. Next action remains live-runtime verification of PRs #526 and #527.

## 2026-10-22 — Exclusive “the owner” reference convention

- Added a permanent rule requiring all repository documentation, source comments, commit/PR text, reviews, issues, and other project communications to refer to the person directing the project exclusively as “the owner”; personal names and account usernames/handles must not be used for that person.
- Recorded the rule in `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, and `handoff.md`. Documentation-only changes committed directly to `main` as required. No application code changed; no application tests or CI were run.

## 2026-10-22 — Wildcard-masked artist queries for blocked slskd searches (PR #527 merged)

- PR #527 squash-merged as `e03f4b3` from head `8f51626677473aa069c81e34eaa9007f18cd6623`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Why: slskd blocks some artist names (e.g. "Gorillaz Plastic Beach" returns zero) although the music is on the network; replacing a first letter with `*` ("*orillaz Plastic Beach") bypasses it.
- Change: `integrations/slskd/search.py` adds `masked_artist_variants()`; `search_queries()` inserts the first-word-masked and every-word-masked artist queries right after the unmasked one, before the existing punctuation/parenthetical fallbacks. Words under 3 characters are not masked. No change to `search_polling.py`, candidate extraction or diagnostics.
- Tests: new cases in `tests/test_slskd_search.py` (single word, multi-word, short words); old query-list expectations updated in `test_slskd_search`, `test_slskd_search_modules` and `test_slskd_search_polling` (the latter two were missed on the first head and failed CI). Focused run of five slskd/acquisition modules with `.venv`: 32 OK. Live slskd behavior not verified.

## 2026-10-22 — Failed-track retry in the acquisition watcher (PR #526 merged)

- PR #526 squash-merged as `4fcd5ff78dc7cfebe99d289a49cd8505c6ca9138` from head `360e84287c01622fc19ba844954f55594a218ea9`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Bug: one errored slskd track stopped byte progress, so the watcher ended in `download_failed` or, after 120s, switched to a fallback source and re-downloaded the whole album. `acquisition/watcher.py` now re-queues failed tracks alone from the same source (3 tries, 30s apart) through the injected `queue_files` service, suppresses the stall switch meanwhile, keeps watching 15 minutes before `download_failed` so a manual slskd retry can recover, and ranks completed > live > failed records per file. Without `queue_files` the old immediate-failure behavior is kept.
- Tests: three regression tests in `tests/test_acquisition_watcher.py`; focused run only (13 OK). Not verified against a live slskd; real failure state strings are assumed (`Errored`, `Failed`, `Cancelled`, `TimedOut`, including slskd's `Completed, Errored` form).

## 2026-10-21 — Discovery package PR 4: gathering core (PR #524 merged); layout roadmap complete

- PR #524 squash-merged as `a5b14191c02007db376b0642ecceeef0426bdbd5` from head `69c9359e80aa4ff192a073f69b39bf6ffcdc02f1`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `candidate_gathering`, `batch_metadata`, `lb_tag_lane`, `tag_queries`, `library_snapshot`, `recommendations` into `discovery/`; `mock.patch` string targets rewritten. Root Python modules 9. Focused tests and `py_compile` only.

## 2026-10-21 — Discovery package PR 3: store, refresh and cooldown (PR #523 merged)

- PR #523 squash-merged as `04c0798ea528e53ce5485ea0410b4620b00b3098` from head `279eeee39559dd469238c60be84faef95e8fdbe4`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `store`, `snapshot`, `refresh`, `list_payload`, `candidate_supply` and `recommendation_cooldown` (as `discovery/cooldown.py`) into `discovery/`; root Python modules 15. `navidrome_server.py` keeps the `discovery_store` and `discovery_refresh` names via `from discovery import ... as`. Focused tests and `py_compile` only.

## 2026-10-21 — Discovery package PR 2: allocator (PR #522 merged)

- PR #522 squash-merged as `bcd34c956e177ae43fcb895cb79dbfb095ec6463` from head `d989557adb9d78f83cfc73bb50b212faef4ad984`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `allocation_contract`, `personal_allocator`, `mmr` into `discovery/`; root Python modules 21. Focused tests and `py_compile` only (104 tests OK locally).

## 2026-10-21 — Discovery package PR 1: leaf cluster (PR #521 merged)

- PR #521 squash-merged as `7fbea3a22d65cb5e3406981803392e91b7c15288` from head `2cf623a6ad24e4a8014eef9f4dae3ec8e7960d1d`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.

- Moved `classics_candidates`, `classics_genres`, `classics_ratings`, `deep_dive_candidates`, `new_releases`, `recommendation_payload` from `discovery_*.py` into the new `discovery/` package (no re-export shims; the only callers were `navidrome_server.py` and five test modules, all updated). Dockerfile gains `discovery/ ./discovery/` and drops the six root names. Root Python modules 24. Packaging test `test_discovery_leaf_modules_live_in_discovery_package` added.
- Local: `py_compile`, `scripts/check_server_size.py` and the focused modules (`test_docker_packaging` plus the five moved-module tests) pass except 4 `test_discovery_new_releases` provider tests that need `httpx`, which the local python3 lacks (same 4 errors on clean `main`). Full suite not run. CI, merge, publish and deploy not done.

## 2026-10-21 — Acquisition PR 3 merged (PR #519); music_key inversion (PR #520 merged)

- PR #519 squash-merged as `6e12466` after compile, test-and-build, container-smoke and validate-container passed on head `c2f584b4f09e9e264268fb644f7f4b4900a7a27f`. Not published or deployed.
- PR #520 squash-merged as `b5e0622043737c89ccd4d4bfacb9881c366594f9` from head `886fb03c3a354738b1b51ced393783fe1aac80d5`; four checks passed; not published or deployed.
- `music_key` moved to stdlib-only `recommendation/music_key.py`; `integrations/lastfm/client.py`, `recommendation_feedback.py` and `recommendation/profile_comparison.py` import it from there. `discovery_recommendations` re-exports the same function (other callers and tests use it). `tests/test_music_key.py` proves output identical to the previous implementation. Behavior unchanged; focused tests only; `httpx` missing locally so the Last.fm client was checked by AST, not import.

## 2026-10-21 — Acquisition package PR 3 (open, not merged)

- Moved the five import/cleanup modules into `acquisition/`: `completion`, `import_files` (was `acquisition_import`; `import` is a Python keyword, so `acquisition/import.py` is not importable), `import_service`, `cleanup`, `recovery`. Callers, tests, Dockerfile COPY line and the `python-syntax.yml` compile entry updated; packaging test added. Behavior unchanged. Focused tests and `py_compile` only; the one failure is the known macOS `/var` case. Root Python modules 30. Not merged, published or deployed.

## 2026-10-21 — Acquisition package PR 2 (PR #518 merged)

- Moved five monitor modules into `acquisition/`; details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `32b23176e1c22317ad1ce662b8ca22cb8970409d` from head `29e7879beb162098cc612e27e4781e1ba40bf6e4`; four required checks passed. Not published or deployed.

## 2026-10-21 — Acquisition package PR 1 (PR #517 merged)

- Moved eight request/queue modules into `acquisition/`; owner approved this order and the `music_key` fix, and `recommendation_cooldown` moving with the store modules. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `2411740dc74d57b1a4fddbd33eeef80a461b40dd`, exact head `cd39e83ee7abe50378c015d4486b6306d4690270`, four required workflows passed. Root modules 40. Publication, deployment and runtime verification not performed. Next steps in `CLAUDE_CLI.md`.

## 2026-10-21 — Package layout design note (docs-only)

- Audited `main` `f84dfce` with an AST import graph plus grep. slskd: nothing left to move. `acquisition_*` (18): no outward dependencies, only `navidrome_server.py` calls them; proposed `acquisition/` in three PRs. `discovery_*` (20): six server-only leaves and the 3-module allocator are safe; store/refresh and the gathering core are blocked by the `integrations/lastfm` -> `discovery_recommendations.music_key` inversion (needs an owner decision). `navidrome_server` stays. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. No code changed, no tests run. Next: owner picks the first move (recommended: `acquisition/` PR 1).

## 2026-10-21 — Listening profile move (PR #516 merged)

- Moved `listening_profile` into `recommendation/listening_profile.py` (no shim). Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `adc66e88d522b0240ffc1c271643d7ba0a90e403`, exact head `462ffcb28456ff734522266c7f5fc4f8cae7ff93`, all four required workflows passed. Root modules 48. Next: design note for slskd leftovers, acquisition, discovery and the legacy server. See `CLAUDE_CLI.md`.


## 2026-10-21 — Settings package move (PR #515 merged)

- Moved `service_settings`, `settings_persistence`, `music_paths`, `data_directory` into `settings/` (no shims). Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only; Also archived `diagnose_categories.py` to `docs/archive/`; `read_only_command_policy` stays in root. Squash merge `766ffe487baa28f23f3880e42f6aa4689a9284ad`, exact head `1e5020dfcd7bd6551bf705588f9bb34f1b3c17d8`, all four required workflows passed. Root modules 49. Next: `listening_profile` -> `recommendation/`. See `CLAUDE_CLI.md`.
## 2026-10-21 — Recommendation replay/diagnostics package move (PR #514 merged)

- Moved `recommendation_replay`, `recommendation_diagnostics`, `recommendation_mmr_evaluate`, `recommendation_profile_comparison` into `recommendation/` (no shims). `replay._REPOSITORY_ROOT` adjusted to the repo root. Merge `431c152642809e2aad1a36a556ac47610d0ddaa2`, exact final head `b636fcf2298f27b76befc3285034fe03285a32a0`, four required workflows passed. Root Python modules 54. `run_metrics`, `cooldown`, `feedback` stay in root. Focused tests and `py_compile` run locally; full suite not run. Publishing, deployment and runtime verification not performed.
- Next task: audit settings/paths group. See `CLAUDE_CLI.md`.

## 2026-10-21 — ListenBrainz integration package move (PR #513 merged)

- Moved `listenbrainz_client.py` and `listenbrainz_popularity.py` into `integrations/listenbrainz/` with canonical imports, no shims. Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Merge `4e392e6660706191d080a5a2e9c66739377a5c33` from head `935d8984002bc6d690a2a6c09c315816dea9e16e` (owner named PR 513). Not published, deployed or runtime-verified.

## 2026-10-21 — PR #512 merged: Last.fm integration package

- Squash merge commit on `main`: `7282cbb740dba6e27fa79aecfe0de5519c18d859`; exact final PR head `84b4f04b27025f35d1f8f353b152a78ee886ef59`, all four required workflows passed on it (syntax 39653199481, Docker packaging/full unit suite/build 39653199482, container smoke 39653199327, validation-only multi-architecture 39653199280). Merged on the owner's instruction naming PR 512.
- Owner rules added to `CLAUDE_CLI.md` (2026-10-21): agents never run the full test suite; documentation-only updates are pushed directly to `main`.
- Main also contains owner-merged PR #506 (`8e29044`, tag-triggered release workflow); out of scope here. Publishing, deployment and production-runtime verification remain unperformed.
- Next task: audit the ListenBrainz modules as their own boundary. See `CLAUDE_CLI.md`.

## Last.fm integration package move details (before merge)

- Base: `main` `13790f8` (all four workflows green on it). Moved `lastfm_client.py` to `integrations/lastfm/client.py` (new `integrations/lastfm/__init__.py`); `navidrome_server.py` now imports the canonical module and keeps its `_lastfm_*` adapters unchanged. No root shim: AST/grep audit found exactly one production importer (`navidrome_server.py`) and one direct test module (`tests/test_lastfm_client.py`, switched to the canonical path); no dynamic/string imports, no `__file__` or path assumptions, no workflow or script references besides the syntax compile list.
- Dependencies: the client imports `recommendation_run_metrics` and `discovery_recommendations.music_key` from the root. Both are stdlib-only leaf modules (no cycle) and resolve from `/app` in the image. `music_key` is only the default for the injectable `key_normalizer`; left as is to keep behavior unchanged. Decoupling it is a possible later cleanup, not part of this move.
- ListenBrainz modules (`listenbrainz_client`, `listenbrainz_popularity`) were inspected separately and not moved: three production call sites across `navidrome_server.py` and `discovery_candidate_gathering.py`, plus lazy imports, so they need their own audit.
- Docker: root `COPY` list drops `lastfm_client.py`; `integrations/` is already copied. Added a packaging regression test. Root-level Python modules: 61 to 60.
- Agent-side checks (macOS, venv from `requirements.txt`): `py_compile` on changed Python files; focused `tests.test_lastfm_client`, `tests.test_docker_packaging`, `tests.test_lastfm_recommendation_scoring` (26 tests OK); `scripts/check_server_size.py` OK. Full suite not run. CI on code head `76e5979d` (before this docs-only evidence commit): syntax [39652945862](https://github.com/abucalip/navi-librarian/actions/runs/39652945862), Docker packaging/full unit suite/build [39652945820](https://github.com/abucalip/navi-librarian/actions/runs/39652945820), container smoke [39652945713](https://github.com/abucalip/navi-librarian/actions/runs/39652945713), validation-only multi-architecture [39652945728](https://github.com/abucalip/navi-librarian/actions/runs/39652945728): all passed. PR is #512; the final head after this commit is re-verified in the PR checks.
- Not merged, published, deployed, or runtime-verified.

## 2026-10-21 — PR #511 merged: slskd integration package

- Squash merge commit on `main`: `84fbb68afa7929a0bedae4e178d37ad2b6255c5a`; exact final PR head: `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`.
- Moved `slskd_client.py`, `slskd_quality.py`, `slskd_search.py`, `slskd_search_polling.py`, and `slskd_transfers.py` to `integrations/slskd/{client,quality,search,search_polling,transfers}.py`. Updated production imports in `navidrome_server.py`, preserving its adapters; updated direct-import tests, Docker packaging regression coverage, and the syntax workflow compile list. No old root-level shims were retained because the caller audit found no remaining direct imports requiring them.
- Root-level Python module count: 61 after the move, down from 66 before it.
- Four required workflows passed on exact PR head `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`: syntax/acquisition safety [39649756998](https://github.com/abucalip/navi-librarian/actions/runs/39649756998); Docker packaging/full unit suite/build [39649757098](https://github.com/abucalip/navi-librarian/actions/runs/39649757098); container runtime smoke [39649756971](https://github.com/abucalip/navi-librarian/actions/runs/39649756971); validation-only multi-architecture image [39649757030](https://github.com/abucalip/navi-librarian/actions/runs/39649757030).
- The Docker packaging workflow's full unit suite passed. Agent-side focused tests and `py_compile` were not run because no fresh isolated checkout was available. Do not infer tests on the merge commit beyond the verified PR-head evidence.
- Published, deployed, and production-runtime verified: no. Publishing/deployment remain paused.
- Next task: refresh the dependency map on post-merge `main` and audit `lastfm_client.py` plus its callers, direct tests, dynamic imports, path assumptions, and Docker/CI references before deciding whether to move it to `integrations/lastfm/`. See `CLAUDE_CLI.md`.

## 2026-10-21 — Python package-layout PR #509 merged

- Squash merge commit on `main`: `8fe825a41c0122bd3fd6d3260ca8978cdbf0d27f`; tested PR head `c045865fea13e8944512fc5c987e609cbc41e443`.
- Moved the canonical MusicBrainz album-year and rating helpers into `integrations/musicbrainz/`; retained `musicbrainz_rating_client.py` as a compatibility shim for the legacy server; updated the album-year caller, focused tests, and Docker COPY list.
- Four required workflows passed on the exact PR head: syntax 39646429894, Docker packaging/full unit suite/build 39646429876, container smoke 39646429872, and non-publishing multi-architecture image validation 39646429885. Agent-side focused tests and `py_compile` were not run because a fresh checkout was unavailable.
- Root-level Python module count decreased from 67 to 66. Publishing/deployment remain paused; no release or production runtime verification was performed.
- Next action: audit the five `slskd_*` modules and all callers/tests before deciding whether a cohesive package move is safe; see `CLAUDE_CLI.md`.

## 2026-10-21 — v0.2 release preparation (PR #505)

- PR #505 merged by squash as `99c0b88ed885de8b3c36686d63736b19a9235392`, exact PR head `fb34440b4893cc7f65678c90ba6e333616c0479d`. Added `docs/RELEASE_v0.2.md`: draft user-facing notes, configuration migration cautions, and a release/deployment checklist. No application code changed.
- All four required workflows passed on exact merge SHA `99c0b88ed885de8b3c36686d63736b19a9235392`: Python syntax `39634236552`; Docker packaging/full unit suite/build `39634236630`; container runtime smoke `39634236733`; validation-only multi-architecture image validation `39634236750` (`push: false`).
- Modularization roadmap is closed. No GitHub Release was present at preparation time; an existing tag was not confirmed. The current workflow remains validation-only; no tag, release, image publication, deployment, or runtime verification was performed.
- Release state is prepared, not released. The release notes disclose that the PR #503/#504 Settings browser checks were waived. After this closeout commit, the exact final main SHA still needs all four required workflows checked before tagging. A deliberate publishing workflow path and explicit authorization are still required before publication/deployment.

## 2026-10-21 — PRs #504 and #503 merged

- **PR #504 — neutral LAN defaults:** squash merge `af78c9e9796c27c65f9503a64d61ca9c58357dba`; exact tested PR head `4263f9c5bf3400cf6a5846c0f81a253a177e9543`. Removes the private LAN IP default and uses neutral placeholders/docs; blank slskd URLs fail validation. All four required workflows passed on the exact head: Python syntax `39631742346`, Docker packaging/full unit suite/build `39631742366`, runtime smoke `39631742152`, and validation-only multi-architecture validation `39631742470`.
- **PR #503 — ListenBrainz token setting:** reconciled after #504, then squash merged as `c3d5e02a4e5f113bb2914b12986cdef41e5863b5` from exact final PR head `cd0d53cb9f962b361f7ea84abba12b32b7efb17a`. Reconciliation commits `f1b136669dc790842d86aa9e16a56abd28fc5aee` and `cd0d53cb9f962b361f7ea84abba12b32b7efb17a` carried the token API/service changes onto current main while preserving #504's blank-URL validation. Token is optional, validated against `[A-Za-z0-9_-]{1,200}`, stored in the existing settings DB, never returned by the API, and not sent to MusicBrainz; blank input preserves a saved token and the environment fallback remains. All four required workflows passed on the exact final head: Python syntax `39632632729`, Docker packaging/full unit suite/build `39632632823`, runtime smoke `39632632791`, and validation-only multi-architecture validation `39632633039`.
- The Docker packaging workflow ran the full unit suite for each tested head. No separate agent-side full-suite run was performed (standing workflow rule). Manual UI checks were waived by the owner and not performed. Publishing remains paused; no image publication, deployment, or production-runtime verification is claimed.

## 2026-10-21 — P1a deeper CF pool measured (PR #502, docs only)

- Owner waived P0h and approved one cold plus one warm run for `CF_MAX_PAGES` 4 vs 6 (test-only harness, not committed, fresh data dirs, slskd off, aggregate only).
- 4 pages: cold 25.2 s, warm 5.1 s, 117 candidate albums / 85 artists, 0 uncached recording lookups. 6 pages: cold 183.6 s (2 ListenBrainz 429s, batch fallback, 100 lookups, 47 albums), warm 10.0 s (162 albums / 109 artists). Final list 10 in all runs; overlap 4 of 10.
- Decision: keep `CF_MAX_PAGES = 4`. Single samples, order effect not excluded. No code change. PR #502 merged by squash as `6e0718699740ce96539321e6b82ce15c0f632c06` from exact final PR head `ba29be2429484620415232db91ef97471470826a`.

## 2026-10-21 — PRs #500 and #501 merged

- **PR #500** (`ui/deepdive-save-render-check`) merged by squash as `e911a26b87cf8d9c11bb2502d8f1c074190b7a4c`, from exact final head `97e0bbbffbf3efb7c47860d980e49b023323bd0c`. Docs-only rendered verification record: Playwright/Chromium observed four 44 px Save controls, unobstructed hit targets, `save`/`remove_for_me` behavior without acquire or list reload, retry state on HTTP 500, and no overflow at 375 px. Screen-reader/live-data checks not done. All four required workflows passed on exact head: Python syntax/acquisition safety `39622877712`, Docker packaging `39622877775`, runtime smoke `39622877823`, validation-only multi-architecture image `39622877814` (publishing paused).
- **PR #501** (`ui/saved-page`) merged by squash as `990c83d3c0fdee816d7b511a7c6bd347bc715532`, from exact final head `10d0defec37479606ebb9bca143a21eb9d5cfd7c`. Adds the Saved page to the header menu, reading existing `/api/discovery/for_me`; supports refresh/revisit, saved dates, owned-album indication, remove/undo, loading/empty/error states, and hides Get for owned albums. Also removes the footer copy per owner request. PR report says 5 focused UI-contract tests and all UI-contract modules passed, `node --check static/app.js` passed, and Playwright/Chromium checks covered menu/navigation, rows, save/remove without acquisition/reload, refresh/revisit, empty/failure states, and 375 px layout. Live Navidrome data and screen-reader checks not done. All four required workflows passed on exact head: Python syntax `39626079394`, Docker packaging/full unit suite/build `39626079244`, runtime smoke `39626079346`, validation-only multi-architecture image `39626079497` (publishing paused).
- Publishing, deployment, and production-runtime verification remain unperformed. Exact PR heads were CI-verified before merge; no separate local full-suite run was performed.

## 2026-10-21 — PR #499 merged: P0i stale-flag audit (documentation only)

- PR #499 (`docs/p0i-stale-flag-audit`) merged by squash from exact final head `b5404cfcb80f65d36d61f309bb8c90b54d40b091`; merge commit `90d127eb46b0528a12ea0255ba81f25e1617ac4a`.
- Updated active status wording to reflect the current genre circuit-breaker and batch/title-filter defaults after PRs #495–#498. Corrected the tag-lane early-stop test docstring. No application code or defaults changed; dated historical experiment records were retained.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `39621883615`; Docker packaging/full unit suite/build `39621883770` (`test-and-build`, unit tests and image build succeeded); container runtime smoke `39621883534`; validation-only multi-architecture image validation `39621883758` (non-publishing).
- No separate local full-suite run (owner rule); CI ran the full suite. Publishing, deployment, and production-runtime verification remain unperformed.
- Next action: continue the active recommendation-engine roadmap from its top item; do not infer recommendation-quality or stable performance improvements from single samples.

## 2026-10-21 — Handoff: next task P0i (stale-flag audit, read-only then docs PR) (docs only)

- Pushed straight to `main` at the owner's instruction. `CLAUDE_CLI.md` hands off P0i: audit docs and comments against the post-#495 to #498 code defaults (known suspect: `docs/PROJECT_STATUS.md` still says the batch/breaker PRs are off by default), fix contradictions in a docs PR, no code or default changes, no network. P0h stays parked until ListenBrainz recomputes CF. No tests run (docs only).


## 2026-10-21 — Python package layout, first slice (PR #508 open)

- Branch: `refactor/package-navidrome-client`, based on main `86ad8de2bc1f08b86c4821969e017c15c3ef97bd`. PR: https://github.com/abucalip/navi-librarian/pull/508.
- Moved the Navidrome client implementation to `integrations/navidrome/client.py`, added package initializers, updated production imports, retained `navidrome_client.py` as a compatibility shim, updated direct-import tests, and added the package to Docker COPY.
- Regression coverage added for identity of the legacy re-export and canonical callable. Agent-side focused tests and `py_compile` were not run: the execution environment could not resolve github.com for a fresh checkout. No stale local checkout was used.
- All four required workflows passed on exact head `cffb5486d6fedb091979e397ff545a22fd0502cf`: Python syntax/acquisition safety `39639446692`; Docker packaging/full unit suite/build `39639446681` (unit tests and image build succeeded); container runtime smoke `39639446683`; validation-only multi-architecture image validation `39639446720` (non-publishing). This documentation closeout advances the PR head, so the four workflows must be checked again on the new exact head. Not merged, published, deployed, or runtime-verified.


## 2026-10-21 — Python package-layout first move merged (PR #508)

- Squash merge: `f171a4e73915222292642ba17d6dcb568b8c929a`; exact tested PR head: `a6fe1bd656f77ae4fbd65cb94c067949d14cf140`.
- Moved the Navidrome/Subsonic client implementation to `integrations/navidrome/client.py`; added package initializers, switched production imports, retained and tested `navidrome_client.py` as a compatibility shim, updated direct-import tests, and added `integrations/` to Docker packaging. ASGI entry point unchanged.
- Required CI passed on exact PR head: syntax/acquisition safety run 39639612889; Docker packaging/full unit suite/build 39639612870; container runtime smoke 39639612822; non-publishing multi-architecture validation 39639612866.
- Agent-side focused tests and `py_compile` not run because the execution environment could not obtain a fresh GitHub checkout. No stale local checkout used. No publishing, deployment, or production runtime verification.
- Next: regenerate/review the dependency map against post-merge main, finish the remaining module/caller/path/test inventory, and choose the next cohesive move only after checking dynamic imports, compatibility, and Docker assumptions.


## 2026-10-21 — slskd integration package move opened as PR #511

- Code commit: `2530192b703cdc023406ad8415008a5aa37fcbd5`, based on current main `ea4d50e2384617ba365d11b93f5f4f789af6e019`. Moved the five slskd modules into `integrations/slskd/`, updated lazy/top-level legacy-server imports and direct-import test paths, removed the root module copies, added a Docker package-presence regression test, and updated the syntax workflow compile list.
- Refreshed dependency-map artifact ID `12368421891` from the audit workflow confirms independent module imports; exact artifact SHA-256 is `22440f9cabed53f77f21abbdeb0593a9553fbdcc5bc0791d0ff46498d5185ca5`. The artifact source SHA is audit head `8ba095c17040ea5dd40ab19ad36e132acb4ab2ee`, whose application source matches the main baseline.
- All four required workflows passed on code head `664639724ef9d1cbf5edd1603a41ccb14a372ce3`: syntax/acquisition safety `39649449299`, Docker packaging/full unit suite/build `39649449147`, container smoke `39649449405`, and validation-only multi-architecture `39649449373`. A docs-only follow-up changes the PR head, so exact-final-head CI must be rechecked. Agent-side focused tests and `py_compile` were not run due lack of a fresh checkout. Not merged; publishing/deployment/runtime verification not performed.


## 2026-10-22 — Documentation consolidation and redesign archive

- Documentation-only commits on `main`: `96e2c0d445e6b63523700dbb209849fef69ab14a` (archive and active-doc rewrite) and `04d5be51aa6d54e17499517a31ad731c09c6771a` (remove stale redesign/modularization references). This log closeout is a follow-up commit.
- Created `docs/ACTIVE_WORK.md` as the short current task queue; reduced `CLAUDE_CLI.md` to a pointer; shortened `docs/PROJECT_STATUS.md` to a current snapshot; reduced `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` to remaining gates; moved permanent process and UI safety/accessibility rules into `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`.
- Archived redesign-specific files, including root `AGENTS.md`, `DESIGN.md`, the Impeccable surface brief, design system, front-end guide, roadmap, UI backlog, and status-icon task notes. Archived completed modularization/package-layout/MCP-retirement plans, historical recommendation research, parked diversity/backlog proposals, CF/repeat-rate reports, and v0.2 release preparation under `docs/archive/`. Original file blobs were preserved.
- Updated `PRODUCT.md`, `docs/ARCHITECTURE.md`, and `docs/TEST_PLAN.md` to remove stale references to active redesign and modularization roadmaps.
- Closed superseded documentation PRs [#358](https://github.com/abucalip/navi-librarian/pull/358) and [#368](https://github.com/abucalip/navi-librarian/pull/368) with explanatory comments; their proposed status corrections are retained in the archive.
- Verification: re-read the resulting GitHub tree and active work/handoff/workflow files; confirmed archived files exist at their new paths and active handoff no longer points to redesign roadmaps. No automated link checker or application tests were run because this was documentation-only. No CI, publication, deployment, or runtime verification is claimed.
- Next action remains live-runtime verification of merged PRs #526 and #527; see `docs/ACTIVE_WORK.md`. Image publication/deployment remain paused.


## 2026-10-22 — Rename agent entry point

- Renamed the root `CLAUDE_CLI.md` handoff pointer to `handoff.md` in two documentation-only commits: `c2df9e820fff4ee3610eeb88988af51c0706a8ca` (add new path) and `b931899cca0b02cf27fb728865ce6d62b17a3fc0` (remove old path). The handoff content is unchanged; current queue and permanent rules remain in `docs/ACTIVE_WORK.md` and `docs/DEVELOPMENT_WORKFLOW.md`.
- No application tests or CI run; this was a documentation-only rename. No publication, deployment, or runtime verification performed.


## 2026-10-22 — Full test suite requires owner approval

- Updated `docs/TEST_PLAN.md` to state that manually running `python -m unittest discover -s tests -v` requires explicit owner approval. Without approval, agents run focused tests only; CI's `test-and-build` workflow continues to run the full suite on the PR head. Updated the stale handoff reference to `handoff.md`.
- Documentation-only commit: `841c8b2d912eac7032473558601bd7ec7ee87138`. No tests or CI run for this documentation-only change; no publication, deployment, or runtime verification performed.

## 2026-10-22 — Reconcile and merge PR #562

- Reconciled stacked branch `taste-families-server-labels` with the then-current `main` after PR #561 merged, preserving the PR branch as a parent and avoiding a force-push. Final tested PR head: `76142e1d0f2d48b59a1355e36c7372c4ed6f7123`.
- Reviewed the final diff: server API adds `genre_row` and `genre_row_label`; the UI consumes those fields rather than maintaining duplicate classification rules. The fallback behavior change for a small set of tags is described in the PR.
- Required workflows on the exact final head all passed: Python syntax (`39860454090`), Docker packaging/full unit suite (`39860454167`), container runtime smoke (`39860454213`), and validation-only Docker image validation (`39860454082`). Release-workflow validation (`39860454120`) passed; the publishing job was skipped. Manual browser verification was explicitly waived by the owner and was not performed.
- PR #562 squash-merged as `650a72718bfcd40a63ce67c5f869e71fd3a18d85`. Documentation closeout commit: `82f9be0c41455c035a1abf729d7a290483e1fdce`. No image publication, deployment, or live-runtime verification.


## 2026-10-22 — Close approved runtime verification tasks

- The owner confirmed that failed-track retry/recovery and masked slskd artist-query behavior have been tested and approved. These are removed from the active work queue; no further verification task remains for those behaviors.
- Updated `docs/ACTIVE_WORK.md` in `22c54d99e118eb89ba9fff143c26419b78fbf8b6` and `docs/PROJECT_STATUS.md` in `6157b273155264db880dbecc78b53239465e29c5` to reflect the confirmation and remove stale outstanding-verification references.
- The v0.2.2 image remains published and not deployed. Approval of the behavior tests does not itself authorize deployment.
- Next eligible repository task: begin the behavior-preserving taste-family vocabulary consolidation described in `docs/HARDCODE_REPLACEMENT.md`; document current mapping differences and do not change canonical behavior without the owner's decision.


## 2026-10-22 — Merge PR #563 and review PR #564

- PR #563 externalized the existing taste-family defaults to `settings/taste_defaults.json`; squash-merged as `9a659f6e9da175e475aa22f86c69492f40206869` from exact PR head `0de6a16c6058c053f0948c6b46c74f50092b7bf9`. All four required workflows passed on that head: Python syntax `39861151203`, Docker packaging/full unit suite/build `39861151000`, container runtime smoke `39861150857`, and validation-only multi-architecture image validation `39861150831`. The Docker packaging workflow's full unit suite passed on the exact head. No publication or deployment.
- Retargeted PR #564 to `main` after #563 merged. Review of head `9cae06937a4dc65e9a3f12be484f008a0a49d839` found that sparse-history fallback returns fixed core/exploration sets but retains `profile_mode="derived"`, so fixed-mode classification exceptions remain disabled. Posted a review comment requesting an effective-mode fix and regression coverage. GitHub rejected a formal REQUEST_CHANGES review because the PR was authored by the connected account; the finding was posted as a COMMENT review instead.
- No workflow runs are visible for PR #564's current head after retargeting, so the requested full suite and four required CI workflows are **not verified** on that head. The repository workflow says agents do not run the full suite manually; it must run in CI. PR #564 remains open and unmerged. Derived mode remains off by default; multi-profile replay evidence and owner approval are still required before enabling it.
- No manual UI checks, publication, deployment, or runtime verification were performed.
