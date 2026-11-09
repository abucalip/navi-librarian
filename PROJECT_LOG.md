# Project log

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
