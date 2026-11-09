# Project log

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
