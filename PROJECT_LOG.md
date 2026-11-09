# Project log

## 2026-11-09 — Neighbours by Ear composition merged (PR #926)

- Squash-merged PR [#926](https://github.com/abucalip/navi-librarian/pull/926) to `main` as `934a1c0786f78f4daa2ce257888ee6b189278e3b`. Adds `intelligence/sonic/neighbours.py` (`album_neighbours`) and `GET /api/sonic/album-neighbours`: up to 8 deterministic evenly spaced seeds (first and last included), unanalysed seeds skipped, reported and replaced (max 16 calls), own album dropped, albums ranked by distinct seeds matched then earliest track year then id, `similarity` never read, 5 s bound gives `truncated: "time"` (not cached), one-hour sonic cache.
- Tests: filtered only, `tests/test_sonic_neighbours.py` (9) and `tests/test_api_sonic_routes.py`. Not run against live Navidrome; coverage not re-measured on a wider sample. Not published or deployed. Remaining: route test for the endpoint, wider-sample coverage re-measure (build-time requirement), contract section, Same Room, Listen-through Gaps, fixtures, clients.

## 2026-11-09 — Same Year, Same Scene builder merged (PR #925)

- Squash-merged PR [#925](https://github.com/abucalip/navi-librarian/pull/925) to `main` as `adf7454da321543e78aff8d3526f0987b7e7c497`. Adds `album_moment` to `intelligence/graph/album_paths.py` (2-year window by year, stated label, credited artist or non-country area, overlap with the artist paths dropped, same bounds and cache as the other album kinds).
- Measured read-only on the store copy, 884 owned albums: coverage 58.4% (at least 35%), median stops 3 (at least 3), no `truncated: time` 100% (slowest 1.3 s), label-only share 0% (at most 50%). Label links from a credited start are always dropped because the artist's label path reaches them; the area link requires two different artists, stricter than the probe.
- Tests: filtered only, `tests/test_intelligence_album_paths.py` and `tests/test_intelligence_paths.py` (53 passed). Not published or deployed. Remaining: contract section, route extension, Same Room, Neighbours by Ear, Listen-through Gaps, fixtures, clients.

## 2026-11-09 — Album path builders merged (PR #924)

- Squash-merged PR [#924](https://github.com/abucalip/navi-librarian/pull/924) to `main` as `3901673d599079e80cfa41319d4e6d2fe55751fe`. Adds `intelligence/graph/album_paths.py` (`album_crew`, `album_guests`, `album_works`: credit-grade evidence, per-person and per-work caps, overlap dropped against the artist paths, bounds, cache) and `kind_rows()` in `paths.py` (behaviour unchanged).
- Tests run (filtered): `tests/test_intelligence_album_paths.py` (18) plus `test_intelligence_paths.py`, `test_intelligence_paths_warm.py`, `test_api_knowledge_paths_route.py` (51 passed in total). Full suite not run locally (owner rule); CI status as reported at merge.
- Read-only run on a copy of the owner's store (884 owned albums), after overlap dropping: Studio Crew 54.5% coverage, median 7; Guest List 48.8%, median 11; Covers and Sources 36.7%, median 3; builds within the 2 s bound 100%, 99.8%, 100%. All pass the Balanced thresholds; Covers and Sources is thin.
- Not done: contract section, route extension, fixtures, Android and macOS clients. Not published or deployed. Updated `docs/ALBUM_PATHS_PROPOSAL.md`, `docs/PROJECT_STATUS.md`.

## 2026-11-09 — macOS bug batch 3 and release types on the timeline

- Branch `macos/bug-batch-3`. macOS: gapless/tail segment fix (the display no longer advances mid-song and the next song plays to its own length), quality badge, artwork aligned with the sidebar, space bar, instrumental lyrics, grouped ⌘K palette, whole-library search with punctuation ignored (Somethin' Else), artist search on Connections and Timeline, album cover fallback in Now Playing, Insights layout/font/auto-refresh, Up Next double-click.
- Server: migration 5 adds `release_group_facts` (MusicBrainz primary and secondary type), filled from the dump (`release_group.type` plus the secondary-type join) and from a live release lookup; the timeline page returns `release_type` per album. The macOS Timeline keeps albums typed "Album" with no secondary type, and falls back to title wording only where no type is stored. Existing stores need a dump re-import (or release-group sweep) before types appear.
- Tests run: `python3 -m unittest` for the timeline, release-group, loader, store, migration and API modules; `swift test --filter` for DiscairAudioTests, DiscairNavidromeTests, DiscairLibrarianTests and DiscairUITests. Full suite not run (owner rule). No visual, audio or live-server check was performed. Not published or deployed.

## 2026-11-09 — Server V2 Phase 6 taste presentation closed (slice 9)

- Re-ran the `check_no_weight_effect` guard (`scripts/server_v2_phase6_exit.py`) on `main` at `2fec5809`: it passed, so no module outside the taste, API, store, scripts and tests packages imports `intelligence.taste` and profiles cannot change ranking.
- The owner waived the remaining macOS Cupertino/Zine visual checks, Android device/emulator and accessibility checks, and the live-server refresh (including the Android 30-second timeout concern); none was performed.
- Updated `docs/ServerV2.md` and `docs/PROJECT_STATUS.md`. Not published, deployed or runtime-verified.

## 2026-11-09 — Server V2 Phase 6 macOS Zine taste cards merged (PR #910)

- Squash-merged PR [#910](https://github.com/abucalip/navi-librarian/pull/910) to `main` as `4052f96533bc427e82b6e5dfa5a0159f0ba29142`, from exact PR head `e36bf7d03e226edb33688bb85ac9de7e106071cd`.
- Adds the Zine Insights taste presentation (`ZineTaste`): server-authored headline and shifts, selectable time windows and dimensions, decade comparison, playlist/Library actions for supported genre and decade values, and honest low-sample/empty states. Reuses the shared `TasteModel` and action behavior; no server or recommendation-ranking changes.
- All four required GitHub workflows passed on the exact PR head. No separate focused-test count was recorded in the PR review evidence; full suite not run locally under the owner's rule.
- The owner explicitly waived manual macOS visual verification; it was not performed. No live-server check. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; Phase 6 slice 6 is complete and remaining slice 9 retains its number.

## 2026-11-09 — Server V2 Phase 6 macOS taste card actions merged (PR #909)

- Squash-merged PR [#909](https://github.com/abucalip/navi-librarian/pull/909) to `main` as `872ad8c8ae9a1c5412f92c54484eba5efa3be874`, from exact PR head `e0ae1c3d6b8bd1519e11900b6e336d314032f0af`.
- Adds genre/decade actions to Cupertino taste shift and window cards: create and open a prefilled smart playlist for editing, or open the Library Songs tab with a clearable taste filter. Area, label and collaborator are unsupported because they do not map to a Library song field. The playlist is not saved to Navidrome until the owner saves it; recommendation ranking is unchanged.
- PR-reported focused Swift tests: 7 passed (`TasteActionTests`, `TasteModelTests`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging, and non-publishing image validation.
- No manual visual Mac or live-server verification; no macOS CI exists by owner decision. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; Phase 6 slice 7 is complete and remaining slices 6 and 9 retain their numbers.

## 2026-11-09 — Server V2 work queue condensed

- Rewrote `docs/ServerV2.md` as a concise active tracker containing only remaining Phase 6 client slices and Phase 7 verification.
- Preserved taste presentation slice numbers and names (5–9), including the existing execution order.
- Moved the complete previous Server V2 plan to `docs/archive/ServerV2_HISTORY_2026-11-09.md`.
- Preserved the complete pre-existing project log as `docs/archive/PROJECT_LOG_HISTORY.md`; this root file is now a short current index so the historical log remains intact without keeping a very large active file.
- Updated `docs/PROJECT_STATUS.md` with the active/archive pointers.
- Documentation-only change. No application code or tests changed. No publication or deployment.

## 2026-11-09 — Server V2 Phase 6 macOS taste cards merged (PR #907)

- Squash-merged PR [#907](https://github.com/abucalip/navi-librarian/pull/907) to `main` as `95af941e6b293e010da93926df89760404800f17`, from exact PR head `a41bdce98a19e2660fb0a3ea7167ae00b5230885`.
- Adds the macOS taste response models/client, once-per-launch background refresh, and Cupertino Insights cards for headline/shifts, time windows, dimensions, decades, low-sample and empty states.
- PR-reported focused Swift tests: 16 passed; full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head (Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation). No macOS CI exists by owner decision.
- No live-server or manual visual verification on the Mac. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; slice 5 is complete and remaining slice numbers 6–9 are unchanged.

## 2026-11-09 — Server V2 Phase 6 Android taste cards merged (PR #908)

- Squash-merged PR [#908](https://github.com/abucalip/navi-librarian/pull/908) to `main` as `2e220280ea45d729b9b37afc441673b8ddd752bb`, from exact PR head `598ac7c2f8e73b14ad63f4645e568b621b5c0927`.
- Adds the Android taste response decoder and repository calls, one background refresh per app launch, the compact Insights card, and a bottom sheet with recent, past-year (`mid`) and all-time windows, dimension selection, listed movers, and low-sample/empty states. Server-authored prose is displayed as supplied; no recommendation-ranking behavior changes.
- PR-reported focused Android tests: 17 passed (`TasteTest`, `InsightsTest`); full suite not run under the owner's rule. All four required GitHub workflows passed on the exact PR head: Python syntax, container runtime smoke, Docker packaging/full Python unit suite, and non-publishing image validation.
- No device/emulator, accessibility or live-server verification. The shared HTTP client's 30-second read timeout may expire before a long refresh completes; saved profiles remain available. Not published, deployed or runtime-verified.
- Updated `docs/PROJECT_STATUS.md` and `docs/ServerV2.md`; slice 8 is complete and remaining slice numbers 6, 7 and 9 are unchanged.

## Historical entries

Earlier project log entries are preserved verbatim in [PROJECT_LOG_HISTORY.md](docs/archive/PROJECT_LOG_HISTORY.md).
