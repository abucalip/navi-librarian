# Test plan

Last updated: 2026-10-22 (full-suite execution requires explicit owner approval)

This document defines the **verification baseline**, not a chronological record of past PRs. Exact historical test evidence belongs in the root `PROJECT_LOG.md`. Always verify current results for the exact revision being proposed.

## Required checks for backend changes

- **Project references:** all documentation, source comments, commit/PR text, reviews, and other project communications must refer to the person directing the project exclusively as “the owner”; never use their personal name or account username/handle.
1. **Focused regressions:** run the tests covering the changed behavior and new direct-import tests for extracted logic.
2. **Full unit suite — owner approval required:** `python -m unittest discover -s tests -v` may be run manually only with the owner's explicit approval. Without that approval, agents must not run it; run focused modules instead and report exactly which. The `test-and-build` GitHub Actions workflow runs the full unit suite as part of CI on the PR head. A few modules import siblings and need `discover -s tests -p <file>`.
3. **Syntax and static checks:** run the repository's Python syntax/acquisition-safety workflow and applicable syntax checks.
4. **API and package checks:** exercise relevant API contracts and verify changed modules are included by Docker/package configuration.
5. **Safety cases:** for acquisition, import, cleanup, and deletion, test intended success and unsafe refusal. Cover canonical-root validation, traversal/symlink escape, ambiguous paths, unrelated-file preservation, no-overwrite behavior, incomplete files, and relevant state/race boundaries.
6. **Supported interfaces:** verify the web application imports and starts without MCP SDK/runtime initialization; preserve public web/API contracts and shared service behavior. MCP compatibility is retired.
7. **Full diff review:** inspect every changed file, callers, test fixtures, imports, package inclusion, error paths, and unintended changes.

## Deterministic recommendation replay

- New captures must freeze the ordered post-gathering inputs, including both weighted and raw play-count maps, plus the ranking timestamp, effective recommendation-history rows, and validated diversity setting.
- Replay must rank from pristine frozen post-gathering inputs and use the captured Last.fm response tape without live calls. Candidate dictionaries are mutated by scoring, so freeze/thaw must remove ranking-derived fields (including prior profile and Last.fm bonuses) while preserving provider/gathering metadata and candidate order. Provider events are provenance only in snapshot-authoritative replay and must not be reported as consumed.
- Schema-v1 captures lack complete ranking context and must fail with an explicit recapture instruction; they must not silently use current database history, time, or settings.
- Regression tests must verify snapshot authority, ranking-context validation, schema-version refusal, full Last.fm tape consumption, and unchanged live-provider isolation.

## Required GitHub Actions workflows

After the final code or documentation commit, verify all four workflows on the **exact final PR-head SHA**:

- Python syntax and acquisition-safety regressions.
- Docker packaging, full unit suite, and image build.
- Isolated container runtime smoke test.
- Validation-only multi-architecture image validation.

The multi-architecture workflow must remain non-publishing (`push: false`). A workflow existing, a successful compile, or a container starting does not prove all required checks passed. If a workflow is missing, skipped, cancelled, or associated with another SHA, state that explicitly and do not claim the gate is complete.

## Modularization completion audit

Run the AST dependency map from the repository root and review its output with the runtime/import inspection:

```sh
python scripts/dep_map.py --output docs/architecture/dependency-map.json
```

The Python syntax workflow also generates `dependency-map.json` and uploads it as the `modularization-dependency-map` artifact (14-day retention). Review that artifact against the exact source revision before treating the graph gate as complete. Commit a repository copy only when it has been reviewed against the exact source revision. It is a static-import aid, not proof of runtime reachability; inspect dynamic imports, dependency injection, package/Docker inclusion, and compatibility entry points separately.

Use `docs/architecture/AST_TEST_INVENTORY.md` as the current inventory of tests that read `navidrome_server.py` as source or parse it with `ast`; update the inventory as coupling changes. Behavior tests should import the extracted production module directly; keep narrowly scoped source-contract tests only where the source layout itself is the requirement, and retain adapter/public web-contract tests as applicable. Never delete or weaken acquisition safety coverage as part of decoupling tests.

Before declaring modularization complete, inspect all Python references under `app/`. The CI guard `scripts/check_app_legacy_imports.py` enforces the current reviewed exception: only `app/api/dependencies.py:get_librarian` may contain a direct `navidrome_server` import, and it must remain lazy. Its regression tests must cover the allowed adapter and rejection of other paths, functions, and module-level imports. Update the allowlist only with an explicit architecture review. Inspect all Python references under `app/`:

```sh
grep -r "navidrome_server" app/ --include="*.py"
```

Expected result: no domain-policy imports of `navidrome_server.py`; only explicitly documented compatibility adapters may remain. On the current audit baseline, `app/api/dependencies.py` intentionally performs a lazy import in `get_librarian()` to preserve the web API's legacy-service adapter, and the legacy service adapter remains; MCP registration/runtime is retired. Review every match and its import timing; do not treat a grep exit code alone as proof. The allowlist-aware CI check is implemented in `scripts/check_app_legacy_imports.py` (PR #254). The only permitted direct import is the lazy compatibility adapter `app/api/dependencies.py:get_librarian`; review every match and import timing when architecture changes. The AST map traverses imports inside functions and therefore reports this lazy edge in the static `app.main` closure even though `tests/test_auth_routes_integration.py` verifies that importing the web app does not initialize `navidrome_server`.

## Recommendation characterization and size ratchet

The directly imported `discovery_refresh` tests cover freshness classification and per-list scheduler failure isolation. Keep scheduler diagnostics bounded: report list, stage, status, and exception type only; do not include provider exception messages, URLs, credentials, or raw recommendation identities.

The enforced size check is `python scripts/check_server_size.py`. Its ceiling is 2,650 lines for `navidrome_server.py`, with a 280-line default top-level-function limit and a temporary named 450-line ceiling for `recommend_new_music()`. `tests/test_server_size_guard.py` must cover in-limit acceptance, file growth, generic function growth, exception-specific boundaries/diagnostics, and invalid Python. The Python syntax workflow runs the guard before the full unit suite; the guard must not change the non-publishing image-validation setting.


Before extracting any part of `recommend_new_music()`, add deterministic tests with fake provider callables/responses and a fixed listen/library fixture. Assert stable candidate ordering, ownership exclusions, scoring/bonus effects, provider failure behavior, and the public result shape where those behaviors apply. Existing tests that mock the entire function do not characterize its internals. Compare the library-inventory path with `discovery_library_snapshot.py` before creating another inventory implementation.

`scripts/check_server_size.py` enforces the ceiling measured against the exact reviewed GitHub revision; do not substitute the older audit estimate. The guard tests prove acceptance at thresholds and failure above them, and diagnostics name the offending function and measured size. Explicit temporary exceptions require a documented reason and follow-up.

## Recommendation capture/replay

The replay harness is part of recommendation correctness verification. Run its focused tests with:

```sh
python -m unittest discover -s tests -p 'test_recommendation_replay_capture.py' -v
```

For a real baseline, run capture only in an isolated environment pinned to an identified GitHub revision and configured with test settings. Keep the capture outside the repository with directory mode 700 and file mode 600. Then run `python -m recommendation.replay /absolute/private/path/capture.json`. The replay must pass checksum/schema validation, consume every provider/cache and Last.fm tape event in order, make zero live provider calls, and reproduce stable recommendation output. A synthetic fixture test does not substitute for this real-capture check. Never attach a private capture to a public PR; CI uses synthetic fixtures only.


### Full-engine profile chronology comparison

Use the offline comparison harness when an owner-only schema-v2 capture and timestamped ListenBrainz history are available:

```sh
python -m recommendation.profile_comparison /absolute/private/path/capture.json /path/to/listenbrainz-history.json
```

The harness compares the first five days and last five days of the supplied history against the same frozen post-gathering candidate and library snapshot. It recomputes listen-derived artist/family weights with the production 14-day half-life while holding the ranking timestamp, recommendation history, diversity setting, candidate pool, and ownership snapshot fixed. Captured Last.fm values are replayed by artist/album identity; missing tape coverage fails closed and never falls back to a live provider. Output is aggregate-only and excludes artist/album identities.

This is a profile-responsiveness experiment, not a chronological future-listen hit-rate/nDCG evaluation when the capture postdates the windows. A successful deterministic baseline replay remains a separate gate. Keep both the capture and any identity-bearing reports outside the repository with owner-only permissions.

## Global search P1 focused checks

Run these focused modules for changes to the owned search index, routes and settings generation (contract P1, `docs/SEARCH_CONTRACT.md` section 11):

```sh
python -m unittest discover -s tests -p 'test_discovery_search_*.py' -v
python -m unittest discover -s tests -p 'test_api_search_routes.py' -v
python -m unittest discover -s tests -p 'test_navidrome_generation.py' -v
python -m unittest discover -s tests -p 'test_navidrome_cover_art.py' -v
python -m unittest discover -s tests -p 'test_api_owned_artwork.py' -v
python -m unittest discover -s tests -p 'test_navidrome_client.py' -v
python -m unittest discover -s tests -p 'test_library_search_ui_contract.py' -v
python -m unittest discover -s tests -p 'test_discovery_library_snapshot.py' -v
```

The index tests run builds inline (`background=False`); the route tests inject an index and a fake librarian, so none of them calls Navidrome. A live check against a real Navidrome server is a separate, owner-approved step.

## Global search P2 to P4 focused checks

Focused modules per phase (contract `docs/SEARCH_CONTRACT.md` section 8.1 lists the required cases). None calls a live provider; stubs and fakes stand in.

```sh
# P2 network sources, deadline runner, artist-page sections, provider cache
python -m unittest discover -s tests -p 'test_discovery_search_providers.py' -v
python -m unittest discover -s tests -p 'test_discovery_search_runner.py' -v
python -m unittest discover -s tests -p 'test_discovery_search_merge.py' -v
python -m unittest discover -s tests -p 'test_discovery_search_artist_sections.py' -v
# P3 and P3b similar artists, shared tags, owner boost, daily precompute and its cursor
python -m unittest discover -s tests -p 'test_discovery_search_similar.py' -v
python -m unittest discover -s tests -p 'test_discovery_search_similar_precompute.py' -v
python -m unittest discover -s tests -p 'test_similar_precompute_schedule.py' -v
# P4 Discogs, genre search and genre pages, Settings
python -m unittest discover -s tests -p 'test_discovery_search_genre.py' -v
python -m unittest discover -s tests -p 'test_api_search_routes.py' -v
```

`FakeLibrarian` in `tests/test_api_search_routes.py` must return list-store entries in the real shape (`{"payload": entry, ...}`); a fake that returns the raw entry hid a bug where the provider cache never hit (fixed in PR #628). Live provider checks are separate, owner-approved steps; their results are in `PROJECT_LOG.md`. Browser checks follow the UI section below.

## Library pages and album page focused checks

For changes to the artist, album and genre pages, the in-app links, the album page endpoints and the album service links (`docs/SEARCH_CONTRACT.md` section 14). None calls a live provider.

```sh
python -m unittest discover -s tests -p 'test_discovery_search_album_page.py' -v
python -m unittest discover -s tests -p 'test_discovery_search_artist_sections.py' -v
python -m unittest discover -s tests -p 'test_api_search_routes.py' -v
python -m unittest discover -s tests -p 'test_album_links.py' -v
python -m unittest discover -s tests -p 'test_apple_description.py' -v
python -m unittest discover -s tests -p 'test_metadata_routes.py' -v
python -m unittest discover -s tests -p 'test_fallback_artwork.py' -v
python -m unittest discover -s tests -p 'test_quality_label.py' -v
python -m unittest discover -s tests -p 'test_library_search_ui_contract.py' -v
```

Also run every test module that reads `static/app.js`, `static/app.css`, `app/templates/index.html` or `static/icons.svg`, not only files named `*ui_contract*`: `grep -l "app.js\|app.css\|index.html\|icons.svg" tests/*.py`. `test_ui_keyboard_and_feedback_contract.py` was missed by the name pattern in PR #630 and failed CI. Source-contract tests pin exact lines, so a UI edit should be followed by this grep-based run.

Manual (owner): artist page for an owned and an unowned artist; album page for an owned and an unowned album (tracklist, year, description with Read more, service links, Get button size and place); every name and tag link on cards, rows, the album panel and search results; Back through artist, album and genre pages; the library-only toggle; Library tab at phone width. Live data to try: an artist with many live recordings (for example Radiohead) must show studio albums with years and listen counts.

## Global search P5 latency measurement

Measure the section 2.1 targets of `docs/SEARCH_CONTRACT.md` with the script, against the owner's real Navidrome library, using an isolated data directory so the app's own data is untouched:

```sh
set -a; source /path/to/config.env; set +a
DISCAIR_DATA_DIR=/tmp/search-latency-data python scripts/search_latency.py --builds 3 --queries 20
python scripts/search_latency.py --network --network-queries 5 --network-gap 5   # live providers: owner-approved runs only
```

Focused tests: `python -m unittest discover -s tests -p 'test_search_latency_script.py' -v`. A stub run does not count for the index build time. Record each result against its target in `PROJECT_LOG.md`, and say which targets were not measured (browser-side targets need a real browser). The script prints aggregate timings only, so reports can be kept in the repository.

## Android player focused checks (PLAYER-01 to PLAYER-04)

Contract: `docs/ANDROID_PLAYER_CONTRACT.md`. Unit tests in `android/app/src/test`; focused runs only, the owner runs the full suite.

- **Stream URL builder:** only `id`, allowlisted `maxBitRate` and `format`; `format=raw`, repeats and unknown values are rejected; fresh salt per URL; no password, token or salt in logs, errors or exception text.
- **Queue:** restore paused; corrupt or old data dropped; shuffle off restores order; 500 cap message; play album replaces, play next and add to queue append.
- **Failures:** Subsonic error-as-200 bodies, 404, auth codes 40/41/44/50 (one "Sign in again", no loop), network drop and resume, unsupported-format fallback once without changing the setting. A fake player and connection must report zero open handles after service stop, cancellation and every failure path; a happy-path-only implementation must fail that assertion.
- **Scrobble tracker:** tracks under 30 s, missing or zero duration, duration disagreement over 10 %, seek forward and back, buffering, repeat-one, repeated playback, toggle off and on mid-track, no scrobble for a skip at 10 s.
- **Scrobble retry:** a request that was sent and whose response was lost is not retried and cannot duplicate; a connect failure before any bytes is retried at most 3 times with the original `time`; now-playing is never retried.
- **Device (owner):** the manual list in contract section 7. Do not claim device results from unit tests.

## Android lyrics focused checks (LYRICS-01 to LYRICS-04)

Contract: `docs/ANDROID_LYRICS_CONTRACT.md`. Unit tests in `android/app/src/test`; focused runs only, the owner runs the full suite. Fixtures use placeholder text with the structure of the real answer; no real lyrics anywhere in the repository.

- **Parsing and choice:** timed, plain and empty answers; several entries; phone-language preference; timed before plain.
- **Cleaning:** unsorted starts, missing or negative `start`, an `offset`, over-long lines (500), over-many lines (2,000), control characters, equal or backward starts treated as plain.
- **Source:** a bad song id makes no request; error code 70 is "none"; auth codes are "login rejected"; a network failure is "unreachable"; no `songLyrics` extension makes no lyrics request; no password, token or lyrics text in any error or log.
- **Cache:** hit, miss, size and count limits, another server or user does not read it, cleared at sign-out, "none" expires after 24 hours.
- **Timeline:** exact boundaries, before the first and after the last line, seek backward and forward, an offset, pause, empty and one-line cases; the 250 ms check stops when the view is hidden or playback pauses.
- **Screen:** the state choice from the data layer's results.
- **Device (owner):** the manual list in contract section 10. Do not claim device results from unit tests.

## Android equalizer focused checks (EQ-01 to EQ-04)

Contract: `docs/ANDROID_EQ_CONTRACT.md`. Unit tests in `android/app/src/test`; focused runs only, the owner runs the full suite.

- **Filter:** each band's response at several sample rates within 0.1 dB at its centre; a flat curve is bit-exact bypass; bands above Nyquist bypassed; coefficient changes are smooth.
- **Headroom:** automatic pre-gain for several curves; a full-scale sine through +12 dB does not exceed full scale after the limiter.
- **Formats:** 16-bit and float input; mono, stereo and six channels; a format change recomputes coefficients; unsupported formats pass through untouched.
- **Gapless:** no samples added or removed over a long buffer and across a simulated song change; filter state is not reset at a join.
- **Settings:** round trip, clamping of hostile values, corrupt data falls back to Flat and off, sign-out does not clear them.
- **Service:** a thrown error becomes bypass, not a crash; the processor is released with the player.
- **Screen:** preset-to-bands mapping, the move-to-Custom rule, dB text and TalkBack text.
- **Device (owner):** the manual list in contract section 10. Do not claim device results from unit tests.

## Android crossfade focused checks (XFADE-01 to XFADE-04)

Contract: `docs/ANDROID_CROSSFADE_CONTRACT.md`. Unit tests in `android/app/src/test`; focused runs only, the owner runs the full suite.

- **Curve:** gains at progress 0, 0.5 and 1; the sum of squares is 1 across the ramp; monotonic; no step larger than the set bound per update.
- **Planner:** every refusal reason has a test (crossfade off, manual change, no next song, repeat-one, unknown or short duration, next song not ready, same-album rule); a short song gets a shorter fade; repeat-all at the end of the queue; shuffle; hostile lengths are clamped.
- **Off means off:** with crossfade off the second path is never created.
- **Service:** a thrown error becomes "play as today"; both players are released exactly once; a manual skip during the overlap snaps to the incoming song; one scrobble and one now-playing per join; both equalizer processors follow one setting.
- **Settings and screen:** round trip, clamping, corrupt data, defaults, sign-out does not clear them; length text and TalkBack text; the quality line shows only below Original.
- **Device (owner):** the manual list in contract section 10. Anything needing a real `ExoPlayer` or `AudioTrack` is a device check; do not claim device results from unit tests.

## UI changes

After automated CI succeeds, run the full manual browser checklist in `docs/LOCAL_UI_TESTING.md` against the exact tested SHA. Cover affected workflows and record the actual result. Do not claim manual verification from source inspection or automated tests alone.

For UI changes, also:
- Verify affected workflows at representative desktop and narrow/mobile widths, including long names, missing artwork, empty/error/loading states, and horizontal overflow where relevant.
- Inspect browser console/network errors and keyboard/focus behavior on the exact tested SHA.
- Check text/control contrast for color changes; preserve visible focus, reduced-motion support, accessible labels, and status distinctions that do not rely on color alone.
- Update UI contract tests narrowly when structure changes intentionally; never weaken behavioral assertions merely to pass a test.
- Use self-hosted assets and do not introduce third-party runtime requests without explicit approval.

## Reporting states separately

Track these states independently:
- Implemented.
- Focused tests run.
- Full suite run.
- Required CI passed on exact final PR-head SHA.
- Merged.
- Published.
- Deployed.
- Runtime verified.

Never infer a later state from an earlier one. Record unavailable or skipped tests and any unverified behavior.

## Documentation-only changes

Documentation-only changes are pushed directly to `main` (owner rule, 2026-10-21; see [`handoff.md`](../handoff.md)). Before pushing:
- inspect the changed docs against current GitHub code and PR state;
- check internal paths, names, SHA references, and claims for accuracy;
- search for duplicated or stale active instructions;
- review the complete diff and ensure no application behavior changed;
- run applicable documentation/link/lint checks if configured;
- confirm the workflows on `main` pass after the push, and report any unavailable gates honestly.

## Historical evidence

Search the root `PROJECT_LOG.md` by PR number, module, or responsibility to find past test runs. Historical success is context, not a substitute for running required checks on the current revision.

## Agent session context search

The standard agent workflow uses `scripts/session_search.py` to retrieve focused documentation and source snippets rather than ingesting the whole repository. Its regression suite is `tests/test_session_search.py`. Run:

```sh
python -m unittest discover -s tests -p 'test_session_search.py' -v
python scripts/session_search.py "session workflow" --scope docs
python scripts/session_search.py "path traversal symlink" --scope code --json
```

Verify all-terms and any-term matching, quoted phrase parsing, scope filtering, snippet output, and exclusion of virtual environments/oversized files. Search output is navigation only; code review must still trace callers, configuration, tests, and safety behavior.

## Selection-policy evaluation (offline)

Use when comparing allocator policies or lenses on frozen owner-only captures (see "Recommendation capture/replay"). Build the allocator request from a replayed capture, label candidates with `primary_genre_family`, and run each policy through the real `allocate_personal_recommendations`. Report, per capture arm: distinct genre families, largest-family count, entropy, mean pairwise tag Jaccard, mean and minimum engine score, overlap with the production list, untagged picks, adventurous count, and checked count. Required: every arm must return the requested count. Compare arms with the same tag-lookup budget; a different budget changes the pool, so state it. Replay captures do not freeze the selection-policy setting, so a family-coverage capture does not reproduce under default settings. Engine score is not a listening-quality measure; make no quality claim from these metrics. Captures and any identity-bearing output stay outside the repository. The 2026-10-23 harness was a one-off script and is not committed.
