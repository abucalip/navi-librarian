# Test plan

Last updated: 2026-10-13

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
