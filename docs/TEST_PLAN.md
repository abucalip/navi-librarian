

## Acquisition watcher startup extraction

- acquisition_watcher_startup.py owns the reserve → persist → status → start sequence behind injected locks, active-set, persistence/status callbacks, and watcher entry point. navidrome_server.py retains _discovery_start_import_watcher as a compatibility adapter.
- Direct-import tests cover dismissed and duplicate starts, credential filtering in persisted settings, persistence failure releasing the reservation, and thread-start failure recording monitor_error and releasing the active marker.
- Next: extract the remaining persistent acquisition-state coordination with direct-import tests; preserve existing conditional state writes and dismissal/import transition lock.
- This extraction is not live slskd or production-runtime verification.
## PR #57 merged — acquisition watcher lifecycle

- Merged to main at ae1e8b8f582c0ca0b882566d883d9a68bb2ca589; exact tested PR head f4b92a98bae942ac6080316c3f1803d1b6bcff76.
- All four required workflows passed on the exact PR head: syntax/acquisition safety 38605510990, Docker packaging/full unit suite/build 38605510819, container runtime smoke 38605511271, and validation-only multi-architecture build 38605510906 (publishing paused).
- Regression coverage directly imports the watcher module and verifies dismissal and recovery exits, that completed transfer evidence without a verified folder does not import, and that only the verified folder is passed to the existing safe import coordinator. A first CI attempt exposed an assertion reading status details from the wrong argument position; the test was corrected before final verification.
- No separate local test run, live slskd behavior, or production filesystem behavior is claimed. Image publication and deployment remain unperformed.

## ACQ-04/ACQ-06 — dismissal cleanup safety regression coverage (PR #51 merged)

- Six focused cases exercise the actual `_discovery_cancel_and_clean_source` helper via the existing AST harness: successful cleanup only after transfers stop; refusal with unrelated files; remote `..` traversal rejection before transfer lookup; duplicate same-name folders rejected without touching either; symlinked album folder rejected without touching the target; failed transfer cancellation preserving local files.
- Initial CI on `b8e1c9a398853851e1a8140a9724600800f42c3b` failed because loading the real helper replaced a stub used by an existing source-switch test. The test harness now gives the helper a distinct namespace name; all four workflows passed on final PR head `58021141472c85c9fa33c431cba15cb66792bc1c`.
- CI runs: syntax/safety `38590192829`; Docker packaging/full unit tests `38590192830`; container runtime smoke `38590192905`; validation-only multi-architecture build, publishing paused, `38590192858`.
- Merged to `main` at `790d690ca99866878ee6204f9d101dec5f099994`. PR #52's documentation closeout passed all four required workflows on exact head `4684fb257685aec90025af0b02a7dff5eacfe10a` and merged at `7f05363c3b9abec29ef7c7d516bad2796813b11e`.
- Follow-up PR #53 adds a regression that successful cleanup preserves sibling artwork and another album folder. All four required workflows passed on exact head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7`: syntax `38594117785`, Docker packaging/full unit suite `38594117579`, container runtime smoke `38594117489`, and validation-only multi-architecture `38594117597` (publishing paused). Existing coverage also proves an unexpected file inside the target folder aborts before deletion of expected tracks.
- Assistant did not run tests locally. No live slskd, real production-folder deletion, publication, deployment, or production runtime testing. The HTTP 409 was not reproduced and remains deferred.

## Acquisition lifecycle policy module (PR #47)

- Direct-import tests in `tests/test_acquisition_lifecycle.py` cover monitor-recovery eligibility, conservative cleanup requirements, skip-request rejection states, queue-failure retry classification, and fallback candidate/payload normalization.
- Preserve the invariant that ambiguous queue outcomes remain monitored rather than triggering duplicate source retries; only explicit peer-level rejections may retry another source.
- These tests cover the extracted policy seam only. They do not replace the remaining AST-based orchestration/safety cases; migrate those as the watcher, source-switch, cleanup, and recovery implementations move into domain modules.

## Legacy-server dependency audit — test implications (2026-10-14)

- The read-only audit found `tests/test_acquisition_safety.py` extracts selected function bodies from `navidrome_server.py` using AST parsing and executes them in a stub namespace after stripping MCP decorators.
- Treat these as real safety/lifecycle regression tests, not disposable test scaffolding. When extracting functions, migrate cases to direct imports of the new domain module and ensure they exercise the actual implementation.
- Keep coverage for acquisition state transitions, dismissal/cleanup, candidate/source failover, completed-folder matching, safe imports, traversal/symlink rejection, ambiguous targets, no-overwrite behavior, and rollback. Add unsafe-failure cases alongside success cases.
- Direct-import tests already exist for acquisition completion/import, slskd search/quality, discovery persistence/refresh/recommendation rules, and extracted API routers. Their existence does not prove the remaining orchestration is independent of the legacy server.
- Audit verification only: GitHub source/docs inspected; no tests were run. No CI pass is claimed for audited main SHA `edc6239c0a01573e1eaa3161a4485ca03a9851da`.

## PR #44 — acquisition dismissal diagnostics: manual report (2026-10-14)

- Tested exact PR head `4c505423afef8c6959063ddea7e5672a0b9894ef` in the isolated local helper environment on macOS 26.2 arm64, Python 3.12.14, port 8089, per-commit app data, sandbox music/download paths, and slskd disabled by default.
- User-reported manual checklist passed: setup/login, dashboard/artwork, discovery, navigation/album details, settings save/load without secret exposure, Get/request without a real download, acquisition cards/status, and no unexpected browser/server errors.
- Dismiss attempts all succeeded; HTTP 409 was **not reproduced**. No cleanup refusal stage was captured, so this is not evidence of a root-cause fix.
- The report's trailing console detail was truncated (`console showed 2$`); no inference is made from it. Full suite and CI claims remain limited to the exact-head GitHub Actions results recorded in PR #44.
- PR remains draft/unmerged pending reproduction or other concrete evidence. No live slskd test, image publication, deployment, or production runtime verification.
 
## Authentication security helper extraction — PR #37 merged (2026-10-14)

- Branch: `refactor/auth-security-helpers`, based on updated GitHub `main` after PR #36 and documentation closeout.
- Added `app/security/auth.py` for persistent signing-secret loading, username/password policy, PBKDF2 digest, and signed-session creation/validation. `app/main.py` imports these primitives and retains compatibility wrappers; HTTP routes, cookie settings, login throttling, and middleware are intentionally unchanged.
- Updated `tests/test_app_auth.py` to import the extracted primitives directly without AST-loading functions from `app/main.py` or starting the service. Tests cover username/password policy, deterministic salt-sensitive digest, signed token expiry/tampering/user binding, persistent secret reuse, private POSIX permissions, and invalid-secret failure.
- Exact-head verification on `192b084850ecbe0137b64b3dae9d07e0471198b4`: Python syntax/full-unit-test workflow `38488744726` passed; Docker packaging/full-unit-test workflow `38488744684` passed; container runtime smoke `38488744607` passed; validation-only multi-architecture `38488744643` passed. No local test execution is claimed.
- Security-sensitive extraction: no intended auth behavior change. PR #37 was squash-merged at `cb6b1d1d17a6ea3b4dc0099a7588b8752b5d84b3`. No local test run is claimed.

## Metadata API route extraction — PR #36 merged (2026-10-14)

- Branch: `refactor/metadata-api-router`, based on the updated GitHub `main` after PR #35 and documentation closeout.
- Moved `/api/artist-bio`, `/api/album-year`, `/api/album-details`, and `/api/artwork` with provider/cache helpers into `app/api/metadata.py`; registered the router in `app/main.py`.
- Added `tests/test_metadata_routes.py` for endpoint/method inventory, artist bio cache and validation, MusicBrainz year preference, exact Deezer album matching and tracklist parsing, and artwork cache/validation.
- Verification on corrected exact PR head `19d88637d110ecee8fb2c7c8c4ba2053c6b6113c`: Python syntax/full-unit-test workflow `38488440438` passed; Docker packaging/full-unit-test workflow `38488440512` passed; container runtime smoke `38488440488` passed; validation-only multi-architecture `38488440439` passed. The initial full suite revealed the AST-coupled artwork retry test; after migration to the extracted module, the corrected full suite passed. No local test execution is claimed.
- No intended UI contract change; manual browser testing was not required. PR #36 was squash-merged at `15011614649470c9c71734422b95ee048fbf9f3c`. No image publication or deployment occurred.

## Discovery API route extraction — PR #35 merged (2026-10-14)

- Branch: `refactor/discovery-api-router` (based on GitHub `main`).
- Added `app/api/discovery.py` and `tests/test_discovery_routes.py`; `app.main` registers the router and no longer defines the four discovery/recommendation handlers inline.
- Focused command: `python -m unittest tests.test_discovery_routes -v`.
- Baseline commands: `python -m py_compile navidrome_server.py app/main.py app/api/discovery.py` and `python -m unittest discover -s tests -v`.
- Direct-import tests cover route/method inventory, recommendation count defaults and album-candidate filtering, discovery list validation/defaults, refresh count parsing/defaults, feedback validation and Unicode metadata serialization, domain payload mapping, and sanitized errors.
- This is an API-only extraction with no intended UI contract change. Manual browser testing is not required unless review/CI reveals a UI behavior change. PR #35 was squash-merged from exact head `eac2a79e3e993d57edc22e86ea50f47e38cf300d` at `d61162b29c6f0cccc97aefe9c779567e671651b2`. Python syntax/full-unit-test workflow run `38487647938`, container runtime smoke `38487647898`, Docker packaging `38487647913`, and validation-only multi-architecture `38487647952` all completed successfully on that exact head. No local test execution is claimed. These CI results do not indicate image publication or deployment.

## Current verification state — PR #34 merged (2026-10-14)

- PR #34 was squash-merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact PR head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`.
- All required exact-head workflows passed: Python syntax #330 (run `38485830330`), Docker packaging/full unit tests #237 (run `38485830207`), container runtime smoke #47 (run `38485830231`), and validation-only multi-architecture #91 (run `38485830245`).
- Focused test coverage is in `tests/test_acquisition_routes.py`; route-only change, no intended UI contract change, so manual browser testing was not required. Local test execution is not claimed.
- No image publication, deployment, or production runtime verification. Keep publishing disabled until modularization is complete and separately authorized.

## Current verification state — PR #31 merged (2026-10-14)

- PR #31 was squash-merged at `87e5816c4273e720352931402a223f0b61ecbf27` from exact head `135b719bfecf9ad698862d41034d927083426f99`.
- Exact-head CI passed: Python syntax #318, container runtime smoke #35, Docker packaging/full unit tests #225, and validation-only multi-architecture #79. See `docs/PROJECT_STATUS.md` for workflow run IDs.
- Manual UI evidence remains tied to application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`: eight recorded checks passed, zero failures. Performance observation and distinct error/recovery remain deferred to the next UI-facing PR.
- Documentation handoff commits after the merge are recorded, but workflow lookup returned no PR-triggered runs for those documentation commit SHAs; their CI is not claimed.
- Image publication and deployment were not performed. Keep publishing paused pending modularization completion and separate authorization.

## Current verification state — PR #32/#33 merged; PR #31 documentation follow-up

- PR #32 and PR #33 are merged. Their exact-head checks passed, including syntax, full unittest discovery/Docker packaging, container runtime smoke, and validation-only multi-architecture build. See the top of docs/PROJECT_STATUS.md and PROJECT_LOG.md for exact commit/run references.
- PR #31's operator guide is reconciled against main `25cd40eca0f20824173d7aefce76b753ef57360c`. Head `3eb3ec6726e0bbe03ef0df9f3d5022796feb7a0c` passed Python syntax workflow #316, full unit tests/Docker packaging workflow #223, container runtime smoke workflow #33, and validation-only multi-architecture workflow #77. Docs-only follow-up `2993273b633b865219818789c47160b8e2429a6f` triggered new exact-head CI runs; these were still in progress at closeout, so wait for their conclusions before merge.
- Manual browser checks remain a gate for UI-facing changes after exact-head CI. The performance observation and distinct error/recovery scenario not recorded in the October 13 report are deferred to the next UI-facing PR. Do not repeat the full visual checklist solely because a non-UI PR changes SHA.
- GHCR publishing stays disabled until the modularization roadmap is complete and release is explicitly authorized.

## Discovery refresh coordination extraction — merged PR #30

- PR #30 was merged into `main` at `a12538e7f7ab2f3ec7417680d6127f5c3a1eaa5b`; final PR head was `f9256060d162ed92be0bbacc66a877c2675a5174`.
- Focused regression command: `python -m unittest tests.test_discovery_refresh -v`.
- Syntax check: `python -m py_compile navidrome_server.py discovery_refresh.py`.
- Full suite: `python -m unittest discover -s tests -v`.
- CI passed for code head `46444e3c24dc78008e3c13dfb441059e73279814` (Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156; Docker job included full unittest discovery and image build). A docs-only commit triggered Docker workflow #157; its terminal result was not confirmed at merge time. No local test run or live/UI verification is claimed.
- Refresh coordination tests cover personal payload parsing/write behavior, malformed JSON, non-blocking lock behavior, named-list success/counting, unknown-list handling, builder exceptions, and lock release.


# Test plan

Last updated: 2026-10-14

## Discovery store extraction — merged PR #29

- PR #29 was squash-merged to `main` at `001f3a7e76979d82adc62edd888d8490565b2ef3`. The final PR head `518505f6dd8e233bc6aaec4b90ec42b0669f70d5` passed Python syntax workflow #243 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507492)) and Docker packaging workflow #150 ([run](https://github.com/abucalip/navi-librarian/actions/runs/38434507399)); the latter ran Python compilation, the full unit-test suite, and Docker image build.
- No workflow runs were returned for the squash merge commit at closeout. Do not infer merge-commit CI from PR-head CI. No local test execution or live/UI validation was performed.
- Focused commands for future changes:

```sh
python -m unittest tests.test_discovery_store -v
python -m py_compile navidrome_server.py discovery_store.py
python -m unittest discover -s tests -v
```

## Latest CI evidence — PR #28

- PR #28 final head `9ab8afeaed6562424b9212f2492d34f3ed9a69ee`: Python syntax workflow #232 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390630)); Docker packaging workflow #139 passed ([run](https://github.com/abucalip/navi-librarian/actions/runs/38432390704)), including Python compilation, full unit-test discovery, and image build.
- PR #28 was squash-merged to `main` at `686fb393a178fe27f3806ecd5ce2138b026291cc`. No workflow runs were returned for the merge commit at closeout; CI evidence above is for the exact PR head, not the merge commit.
- No local test execution or live/manual runtime checks were performed during closeout.

## Source-switch orchestration extraction — PR #56 merged

- Moved the existing locked source-switch implementation into `acquisition_source_switch.py` with injected config, lifecycle, cleanup, HTTP, candidate-start, status, and persistence dependencies. `navidrome_server.py` retains the compatibility wrapper; the caller still owns dismissal/transition locking.
- Added direct-import tests for uncertain queue outcome (monitor the same peer, never queue another), cleanup refusal before queue, no fallback, failed fallback cleanup stopping the loop, and confirmed fallback persistence.
- PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety `38602255318`, Docker packaging/full unit suite/image build `38602255282`, runtime smoke `38602255326`, and validation-only multi-architecture build `38602255378` (publishing paused). Squash-merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- No live slskd interaction or production cleanup is claimed.

## Interrupted-import recovery domain extraction — PR #55 merged

- Moved `_discovery_reconcile_interrupted_import` into `acquisition_recovery.py` with injected state, path, matcher, persistence, clock, JSON, and move dependencies. The legacy MCP function remains a compatibility adapter.
- Added direct-import tests for exact completed-destination reconciliation, changed mount-device refusal, partial staging rollback to the source folder, wrong/incomplete destination refusal, and dismissed/non-importing state refusal.
- The direct tests assert no unintended status updates and preserve source/destination files on refusal. Docker packaging includes `acquisition_recovery.py`.
- PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety `38601516322`, Docker packaging/full unit suite/image build `38601516096`, runtime smoke `38601516565`, and validation-only multi-architecture build `38601516203` (publishing paused). Squash-merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- No production filesystem recovery or live service interaction is claimed.

## Acquisition cleanup domain extraction — PR #54 merged

- Extracted the existing fail-safe cleanup implementation into `acquisition_cleanup.py` with injected folder-name validation, slskd transfer lookup, and HTTP client dependencies. `navidrome_server.py` retains its existing MCP-compatible wrapper and delegates to the extracted function.
- Moved all seven dismissal cleanup cases out of the AST-based `tests/test_acquisition_safety.py` harness into directly imported `tests/test_acquisition_cleanup.py`: verified cleanup after transfers stop; unexpected-entry refusal; neighbor artwork/album preservation; traversal rejection; duplicate-folder refusal; symlink-target refusal; failed cancellation preservation.
- The direct tests use the canonical `acquisition_completion.safe_folder_name` helper. Docker packaging includes the new module.
- PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed syntax/acquisition safety `38600688719`, Docker packaging/full unit suite/image build `38600688787`, container runtime smoke `38600688814`, and validation-only multi-architecture build `38600688667` (publishing paused). Squash-merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- No live slskd request, production-folder deletion, image publication, deployment, or runtime verification is performed. HTTP 409 remains deferred because it was not reproduced.

## Acquisition dismissal neighbor-preservation regression — PR #53

- Final PR head `ef6ec7347f69c0be04331d7bd671d9f56f3c137d` passed all four required workflows: Python syntax/acquisition safety `38599666003`, Docker packaging/full unit suite `38599666001`, container runtime smoke `38599665955`, and validation-only multi-architecture image build `38599665933` (publishing paused).
- PR #53 was squash-merged at `a7c8dd469c76b340706ba65db8b4315aac60e62b`. No workflow runs were returned for the merge commit itself.
- The new regression proves successful cleanup preserves a sibling artwork file and a separate album folder. Existing cases continue to cover refusal for unrelated entries, traversal, duplicate folders, symlinks, and failed cancellation.
- Tests use the existing AST harness; migrate them to direct-import tests alongside a tested cleanup implementation extraction, preserving all assertions. The reported HTTP 409 remains deferred because it was not reproduced.
- No separate local test run, live slskd test, real production-folder deletion, publication, deployment, or production runtime verification is claimed.

## Automated baseline

Run from the repository root using the project's supported Python environment.

```sh
python -m py_compile navidrome_server.py app/main.py
python -m unittest discover -s tests -v
```

The Docker CI workflow also installs `requirements.txt`, compiles the Python modules, runs the unit tests, and builds the image. Check the actual GitHub Actions run; the existence of a workflow is not evidence that a given commit passed it.

## Required regression areas

### Discovery and recommendations

- Recommendation endpoint accepts valid counts and rejects out-of-range counts.
- Discovery lists return expected structure and safely handle empty/error responses.
- Owned albums are excluded from new-acquisition recommendations.
- Artist and album matching does not accept substring collisions (for example, an artist name embedded in a tribute act's name).
- Various Artists/compilation and non-album releases are excluded where required.
- New Releases use the agreed date window and library-artist eligibility rules.
- Deep Dive rows obey the one-album-per-artist-per-row constraint.
- Missing or unavailable external metadata does not break discovery.

### Acquisition and filesystem safety

- A slskd per-peer transfer lookup returning HTTP 404 is treated as an empty current transfer list; filesystem polling continues, while other HTTP errors remain visible as monitor errors.
- Regression-test both the 404 response and non-404 HTTP failures in `tests/test_slskd_transfer_lookup.py`.
- Completed-transfer folder diagnosis distinguishes unavailable download root, absent expected folder, incomplete/mismatched tracks, track-matching folders with a different basename, and ambiguous matches.
- A complete album is still selected only when both the strict track matcher and unique expected-folder-name check pass; diagnostic output must not authorize import by itself.
- Folder diagnostics are bounded and include only a small number of candidate folders and filename mismatches.

- Search matching handles punctuation, edition suffixes, and Unicode normalization.
- Candidates from different remote folders are not incorrectly merged.
- Incomplete/unsafe candidates are rejected before queue/import.
- Queueing the selected candidate passes the expected user, folder, and file list to slskd.
- Get does not navigate away; the button changes to the requested state and prevents duplicate requests.
- Every acquisition card has a dismiss control in each relevant state.
- Dismissal resolves the intended album folder and deletes only the files permitted by the requirement.
- Negative tests cover path traversal, symlink escape, ambiguous folders, empty/root paths, and unrelated files.
- API errors restore a usable UI state and show a clear message.

### Authentication and settings

- The slskd quality-priority list contains all six supported tiers exactly once and saves the displayed order.
- Existing four-tier settings append FLAC 16/44 and FLAC Hi-Res; existing five-tier settings append FLAC Hi-Res, without reordering prior choices.
- FLAC 16/44 and Hi-Res are classified from metadata or explicit resolution labels such as `[24-44.1]`; unverified FLAC remains accepted in the fallback tier.
- The Settings quality list can be reordered by drag-and-drop and by Move up/Move down controls; save/reload preserves the order.
- When candidate checks reject sources or queue attempts fail, acquisition status exposes bounded candidate diagnostics (folder, track counts, quality tiers, and eligibility reason).
- Explicit slskd queue rejection statuses 400/404/422 allow safe source failover; 401/403 stop as global credential/permission errors; timeouts and 5xx responses remain monitored as uncertain to prevent duplicate downloads.
- When no folder candidate is recognized, status includes a bounded sample of source paths and the album/artist match signals used by the matcher.
- Normalize slskd search results whether returned as a list or a `responses`/`items` wrapper; if search state reports peers but response payloads are temporarily absent, retry briefly before reporting no matches.
- If an exact slskd query returns no usable peer file payloads, retry a bounded broader-query sequence (30-second total budget); verify mocked zero-response-to-fallback behavior, query order, duplicate elimination, blank-input handling, shorter fallback timeouts, unchanged candidate matching, and card/API diagnostics showing attempted queries and separating reported counts from collected payloads.
- First-run setup creates the owner account.
- Invalid login is rejected; rate limiting and session expiry behave as designed.
- Restarting the container preserves authentication and application data.
- Secret values are not included in API responses or logs.
- Blank secret fields preserve existing secrets unless explicit clearing is supported.
- Settings validation rejects invalid values; service connection tests report failure clearly.

### Docker and deployment

- `docker compose config --quiet` passes against the actual deployment Compose file.
- Image builds successfully for the supported runtime and the intended architecture.
- Container starts as the intended non-root UID/GID.
- `/data` survives container recreation.
- Navidrome and slskd are reachable from the app container.
- Bind mounts point to the real music/download directories; permissions match the minimum required for the feature.
- GHCR pull succeeds on the deployment host with the intended visibility/authentication setup.
- Running UI smoke test passes on the actual host/port.

### Dismissed acquisition retry regression

- Dismiss an acquisition and confirm dismissal succeeds only after its source cleanup completes.
- Click Get again for that same album. Confirm the dismissed record is reset to a retry-requested state with no stale source candidate/settings, then transitions into a fresh search/acquisition card.
- Simulate a failed reactivation guard and confirm no new source search is started.
- Confirm albums already importing/imported and active downloads remain protected from duplicate acquisition requests.

## Manual UI smoke test

**When manual browser testing is required:** run this checklist after automated CI passes on the exact head of a UI-facing PR or release candidate. Documentation-only, API-only refactors with no UI contract changes, and infrastructure changes covered by a successful automated container runtime smoke test do not independently require a manual browser run. Record the exact application SHA for every manual run.

**Deferred checks:** the PR #31 report recorded eight items as passed on application SHA `96b253c5f3ec2f858e02afc034365a22bac0773e`, but did not separately record performance observation or a distinct error/recovery scenario. Do not mark those as passed retroactively; include both in the next UI-facing PR's manual run.

After the automated suite passes:

1. Log in and navigate between the main pages.
2. Load each discovery list; test empty and populated states.
3. Confirm artwork and release years do not shift or mislabel cards.
4. Open an album details popup; verify tracklist and external search links where available.
5. Click Get and confirm the requested state appears without navigation.
6. Check acquisition progress/status and confirm cards update correctly.
7. Test Dismiss only against a disposable known test folder; verify intended cleanup and preservation of neighboring files.
8. Change a service setting, reload the page, and confirm it persisted without exposing secrets.
9. Restart the container and confirm login/data remain intact.

## Evidence to record

For each release candidate, record:

- branch and full commit SHA;
- Python version and test commands;
- test result and any skipped tests;
- CI run URL/status;
- manual smoke-test environment and outcome;
- image tag and full SHA-256 digest;
- deployment date/host and rollback reference;
- unresolved failures.

Never claim a test passed unless it was run against the stated commit.


## M1 implementation note — acquisition completion/matching

The first extraction keeps `navidrome_server.py` compatibility wrappers while the implementation lives in `acquisition_completion.py`. `tests/test_acquisition_completion.py` must exercise the production helpers via direct imports. Retain the legacy lifecycle/import safety suite and ensure it uses the same imported matcher rather than a duplicate AST-extracted implementation. Required regression cases include Unicode NFC/casefold identity, Windows-style remote paths, strict positive sizes, conflicting duplicate basenames, collision-suffix uniqueness by size, symlink exclusion, incomplete folders, and ambiguous named folders. Also verify that multiple exact basename/size matches fail closed even when a unique collision-suffixed file is present; collision-suffix fallback is permitted only when there are zero exact matches.


## M2 — slskd search and quality module extraction

For changes touching `slskd_quality.py` or `slskd_search.py`, run the focused direct-import tests first:

```sh
python -m unittest discover -s tests -p 'test_slskd_search_modules.py' -v
python -m unittest discover -s tests -p 'test_acquisition_safety.py' -v
python -m py_compile navidrome_server.py slskd_quality.py slskd_search.py
python -m unittest discover -s tests -v
```

The new tests cover MP3/FLAC classification, user-configured tier ordering, bounded fallback query generation, slskd response-shape normalization, album-path/track identity matching, candidate track deduplication and ranking, and bounded diagnostics. The legacy acquisition-safety suite remains a compatibility guard because existing callers still use wrappers in `navidrome_server.py`. Confirm the Docker packaging workflow passes on the exact PR head before merge. No live slskd or UI behavior should be inferred from unit tests alone.


## M4 — discovery eligibility and recommendation scoring

- `discovery_recommendations.py` contains pure name/artist/release eligibility, genre-family classification, exploration scoring, and classic-list diversity rules.
- Run focused regression coverage with `python -m unittest tests.test_discovery_recommendations -v`, then syntax checks and the full unit suite below.
- Review score weights, jitter bounds, exact artist-credit matching, compilation/non-album exclusions, and the two-per-artist/eight-per-family caps when changing these helpers.
- Network calls, cache access, Navidrome inventory, metadata enrichment, and persistence remain in `navidrome_server.py`.

## M3 — acquisition import filesystem module

For changes touching `acquisition_import.py`, run the direct-import tests first:

```sh
python -m unittest tests.test_acquisition_import -v
python -m unittest tests.test_acquisition_safety -v
python -m py_compile acquisition_import.py navidrome_server.py
python -m unittest discover -s tests -v
```

The module owns staging/move/rollback mechanics only. Acquisition orchestration remains in `navidrome_server.py`; its compatibility wrapper injects the existing strict completion matcher. Preserve the existing checks for verified expected tracks, reserved manifest names, existing destinations (including broken symlinks), real destination parents, mount/device identity, rollback, and recovery manifests. Do not treat a successful unit suite as proof of a live import or deployment.


## Discovery list persistence extraction

For changes touching `discovery_store.py`, run the direct-import tests first:

```sh
python -m unittest tests.test_discovery_store -v
python -m py_compile navidrome_server.py discovery_store.py
python -m unittest discover -s tests -v
```

The store owns only SQLite persistence for cached discovery-list payloads. The server compatibility wrappers retain `_discovery_init()` so existing schema initialization and callers are unchanged. Cover missing rows, malformed JSON, Unicode payload round-trips, timestamp preservation, and per-list replacement/isolation. CI must pass on the exact PR head, including Docker packaging; unit tests do not establish live refresh/UI behavior.


## Acquisition API router extraction — PR #34

Focused regression command:

```sh
python -m unittest tests.test_acquisition_routes -v
python -m py_compile app/main.py app/api/acquisitions.py
python -m unittest discover -s tests -v
```

`tests/test_acquisition_routes.py` checks route/method preservation, acquire and queue payload mapping/defaults, invalid payloads, skip/dismiss status translation, streaming response headers, and sanitized upstream errors. PR #34 was squash-merged at `3aac576c42465420b9c2144c2cd2f4377c5e0ff1` from exact head `b80b7b5178f0e4c2173ac486b97453e3b5d18af5`. All four required workflows passed on that exact head: Python syntax #330 (run 38485830330), Docker packaging/full unit tests #237 (run 38485830207), runtime smoke #47 (run 38485830231), and validation-only multi-architecture #91 (run 38485830245). This route-only change is not expected to alter UI presentation, so manual browser testing was not required.


## Frontend asset extraction regression gates

For changes that move templates, stylesheets, or scripts out of `app/main.py`:

- Run `python -m unittest tests.test_auth_routes_integration -v` and the full `python -m unittest discover -s tests -v` suite.
- Confirm login and home responses reference their external CSS/JS assets and contain no inline `<style>` or inline `<script>` blocks.
- Confirm `/static/login.css`, `/static/login.js`, `/static/app.css`, `/static/app.js`, and `/assets/cassette.png` are reachable before first-run setup/login; verify protected application/API routes remain protected.
- Run syntax checks and all required Docker packaging/full-test, runtime-smoke, and validation-only multi-architecture workflows on the exact final PR head. Publishing remains disabled.
- After CI succeeds, perform the full manual browser checklist on that exact SHA, including the deferred performance observation and distinct error/recovery scenario. Record results; do not infer them from unit tests.


## Persisted acquisition source-skip orchestration — reconstructed PR #48

Run focused regression tests with `python -m unittest tests.test_acquisition_orchestration -v`, then the full `python -m unittest discover -s tests -v` suite and syntax checks. Direct tests must cover successful persistence for a downloading acquisition with eligible fallback candidates and rejection of missing, dismissed, non-downloading, and no-fallback states without mutation. Verify the MCP adapter still serializes the same JSON response shape, the transition remains under the shared lock, and the SQL update is conditional on `status='downloading'`. Run all four required exact-head workflows: Python syntax, Docker packaging/full unit suite, container runtime smoke, and validation-only multi-architecture image validation. Do not publish or deploy.


## Acquisition cleanup, recovery, and source-switch extractions — PRs #54–#56

- `tests/test_acquisition_cleanup.py` directly imports `acquisition_cleanup.py`; it covers successful cleanup of the identified album folder, refusal for unsafe/ambiguous targets and unexpected files, and preservation of neighboring content. PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed syntax/acquisition safety (run `38600688719`), Docker packaging/full unit suite/image build (`38600688787`), container runtime smoke (`38600688814`), and validation-only multi-architecture build (`38600688667`). Merged at `982e39122a401b8b68d75e38423dbb93711b4abd`.
- `tests/test_acquisition_recovery.py` directly imports `acquisition_recovery.py`; preserve checks for dismissed/non-importing states, strict completion matching, mount/filesystem identity, exact destination, manifest validation, symlink refusal, and staged-file rollback. PR #55 exact head `92a1bce84f7a826dc7d0e45cf0be05a51fd47fd5` passed syntax/acquisition safety (`38601516322`), Docker packaging/full unit suite/image build (`38601516096`), container runtime smoke (`38601516565`), and validation-only multi-architecture build (`38601516203`). Merged at `7d9ef435ce9b74db2bd93aec305209cd9cbb6e30`.
- `acquisition_source_switch.py` is exercised by direct-import regression tests for cleanup refusal as a hard stop, no-fallback handling, failed fallback cleanup, and successful fallback persistence. PR #56 exact head `15c0c237585dc4037df1e3e4d1f98b261d0415d9` passed syntax/acquisition safety (`38602255318`), Docker packaging/full unit suite/image build (`38602255282`), container runtime smoke (`38602255326`), and validation-only multi-architecture build (`38602255378`). Merged at `0387b8247d3dbd8d44d64392d9400b42c56e0fda`.
- For future changes to these modules, run the relevant focused direct-import tests, `python -m py_compile acquisition_cleanup.py acquisition_recovery.py acquisition_source_switch.py navidrome_server.py`, and `python -m unittest discover -s tests -v`, then all four required workflows on the exact final PR head. Keep the legacy adapters/MCP callers and Docker packaging in sync.
- These CI results do not establish live slskd behavior or production filesystem recovery/deletion. No separate local test run, production cleanup/recovery, image publication, deployment, or production runtime verification is claimed. The reported dismissal HTTP 409 remains deferred because it was not reproduced. GHCR publication remains paused until the roadmap is complete and the user explicitly authorizes release.


## Acquisition watcher lifecycle extraction

- Direct-import regression tests in `tests/test_acquisition_watcher.py` exercise dismissal and interrupted-import early exits, strict separation between transfer-completion evidence and verified-folder import, and passing only the folder returned by the existing completion matcher into the existing safe import coordinator.
- The legacy `_discovery_watch_and_import_album` name remains as an adapter. Watcher state, slskd access, folder matching, import coordination and status updates are injected; existing cleanup, source-switch and import modules remain the safety authorities.
- Required verification: focused watcher and acquisition safety tests, full `python -m unittest discover -s tests -v`, syntax check including `acquisition_watcher.py`, then all four exact-head CI workflows. Do not infer real slskd or production filesystem behavior from unit tests.


### Acquisition watcher extraction — PR #57

- First CI attempt failed one test assertion: status details are passed as the fourth positional argument, not keyword arguments. The test was corrected.
- Corrected head `6793c339464c9d573c02f5e7dc91d15b5f568348`: syntax/acquisition safety run `38604931720`, Docker packaging/full suite/build `38604931649`, container runtime smoke `38604931792`, and validation-only multi-architecture build `38604932002` all succeeded. Publishing remains paused.
- After the final documentation update, all four workflows passed on exact head 9f201e247c092ca74f805b8ca8a1cb6f872b3cba; PR #57 was subsequently squash-merged from tested head f4b92a98bae942ac6080316c3f1803d1b6bcff76. No separate local test run or live slskd/production filesystem verification is claimed.


- **Final documentation-updated PR head:** `9f201e247c092ca74f805b8ca8a1cb6f872b3cba` passed syntax/acquisition safety `38605193852`, Docker packaging/full suite/build `38605193845`, runtime smoke `38605193808`, and validation-only multi-architecture build `38605193820`. All four required workflows succeeded; image publishing remains paused.


## Acquisition state persistence extraction

- `tests/test_acquisition_state.py` directly imports the extracted SQLite state store and covers round-trip state, normalized identity, preservation of candidate/settings/quality fields on partial updates, invalid identity rejection, and conservative malformed-JSON decoding.
- Preserve the legacy transition lock, dismissed-state conditional behavior, secondary feedback projection, and compatibility adapters. These are not moved by this extraction.
- On corrected code head `29c5e6a460f1f61296680af7b1230fd5561496b4`, CI ran the full suite (`180` tests, passed), compile, container smoke, and validation-only multi-architecture build; all four required workflows passed (runs `116019140196`, `116019144533`, `116019141476`, `116019141889`, respectively; publishing paused). The initial attempt exposed only an incorrect test fixture expectation for JSON `null`; the fixture was corrected and no production behavior changed. Because this closeout updates documentation, rerun all four workflows on the new exact PR head before merge. No separate assistant-local test run is claimed.
