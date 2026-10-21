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
