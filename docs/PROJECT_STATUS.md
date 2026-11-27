# Project status

Rolling snapshot of current `main` (keep ≤30 lines; older history lives in [`PROJECT_LOG.md`](../PROJECT_LOG.md) and [`docs/archive/`](archive/)).

Last checked against GitHub `main` at `46d0e538` on 2026-11-27.

## Current state

- **Repository split S0–S5 complete (2026-11-27):** PR #1287 merged as `46d0e538`, moving `macos/`, `android/`, client-only perf scripts, and client-only contracts to `abucalip/discair-macos` and `abucalip/discair-android`. Server, web client, and shared API contracts remain here.
- **ListenBrainz Playlist Inbox (LB-03 to LB-12):** Server storage, matching, rolling copies, reconciliation, downloads, and Listening Room web inbox are built (`LB-07` #1276, `LB-08` #1277, `LB-09` #1278, `LB-11` #1280 merged; `LB-03`, `LB-05`, `LB-06`, `LB-10`, `LB-12` in PR review). The owner verified live LB-10 Soulseek download, import, and in-place private playlist update with disposable services.
- **Listening Room web redesign (L0–L3):** L0 (#1221), L1 (#1222), and L2 (#1248) merged; L3 (lead, Up next, Daily picks and reasons) in review.
- **Web Docker updates (2026-11-24):** `web/docker-update-badge` in PR review; browser and Docker host verification pending.
- **FirstFM (Last.fm removal):** All slices F1.1–F5.2 built; live runtime verification pending.
- **Publication / deployment:** Paused unless explicitly authorized by the owner.

## Next action

- Review open server/web PRs (Playlist Inbox LB-10/LB-12, Listening Room L3, Web Docker updates), then proceed with Listening Room L4 (Artist Deep Dives, Personal Discoveries, Discover music).
