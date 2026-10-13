## Discovery refresh coordination extraction — merged PR #30

- PR #30 was merged into `main` at `a12538e7f7ab2f3ec7417680d6127f5c3a1eaa5b`; final PR head was `f9256060d162ed92be0bbacc66a877c2675a5174`.
- Focused regression command: `python -m unittest tests.test_discovery_refresh -v`.
- Syntax check: `python -m py_compile navidrome_server.py discovery_refresh.py`.
- Full suite: `python -m unittest discover -s tests -v`.
- CI passed for code head `46444e3c24dc78008e3c13dfb441059e73279814` (Python syntax/acquisition-safety workflow #249 and Docker packaging workflow #156; Docker job included full unittest discovery and image build). A docs-only commit triggered Docker workflow #157; its terminal result was not confirmed at merge time. No local test run or live/UI verification is claimed.
- Refresh coordination tests cover personal payload parsing/write behavior, malformed JSON, non-blocking lock behavior, named-list success/counting, unknown-list handling, builder exceptions, and lock release.


# Test plan

Last updated: 2026-10-13

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

## Container runtime and release-artifact verification — 2026-10-13

- .github/workflows/container-smoke.yml builds the Docker image on pull requests, pushes to main, and manual dispatch, then starts it with disposable /data, /music, and /downloads storage. The smoke script verifies readiness, unauthenticated API denial, first-run owner setup, authentication-key file mode, authenticated UI access, account persistence across a container restart, and login after restart.
- The smoke job never connects to Navidrome or slskd and uses no real library/download paths. Its music/download mounts are read-only. It is a container/API integration check, not a full browser test or destructive acquisition test.
- .github/workflows/docker-publish.yml records source SHA, trigger ref, published tags, multi-architecture targets, immutable GHCR digest, and provenance/SBOM generation status in the GitHub Actions run summary.
- For a release/main publication, confirm the publish job succeeded and retain the full image digest from the run summary. Confirm the digest is associated with the intended source SHA and includes both linux/amd64 and linux/arm64.
- A successful image build or publish does not verify that a deployment host pulled or runs that digest. Host deployment, persistent-volume preservation, logs, connectivity, rollback readiness, and application smoke tests remain separate, authorization-gated checks.
- Required CI must pass on the exact PR head. Re-check the final head after changes and inspect the container-smoke job in addition to syntax, full unit-test/Docker packaging, and acquisition-safety workflows.
