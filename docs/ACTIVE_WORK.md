# Active work

Short queue of open or parked **server and web** work. GitHub `main` is authoritative.

> **Repository split (2026-11-27):** `macos/` and `android/` moved to [`abucalip/discair-macos`](https://github.com/abucalip/discair-macos) and [`abucalip/discair-android`](https://github.com/abucalip/discair-android) ([`plans/split.md`](plans/split.md)). Native client queues and plans now live in those repositories (archived snapshots in [`archive/native-clients/`](archive/native-clients/)). Completed pre-2026-11-18 items are in [`archive/completed/ACTIVE_WORK_DONE_2026-11-18.md`](archive/completed/ACTIVE_WORK_DONE_2026-11-18.md).

## 2h. Round 2 Neobrut layouts — P7 closeout open

- P1–P6 and revisit merged; P7 closeout (docs and owner-authorized release) not started ([`BRUT_LAYOUTS_PLAN.md`](archive/completed/BRUT_LAYOUTS_PLAN.md)).

## 2i. Round 3 Neobrut themes — web phases not started

- Plan: [`BRUT_ROUND3_PLAN.md`](plans/BRUT_ROUND3_PLAN.md) (D-024). Zine Spread (P1) merged; Pipeline Board dropped.
- Not started (wait for owner): **P3a** web Window Manager, **P3b** second album window (spike first), **V** optional palette variants, **P6** closeout.

## 2l-2. Flow Home server additions — not started

- Two server additions for Android Flow Home: **S0a** (smart-playlist preview endpoint and song-list cache) and **S0b** (`album_label` album path kind). **Next:** S0a.

## 2m-2. Star Operation — open decisions

- S1–S4b merged (2026-11-15). Open: owner approval for star-seed half-life (180 d), expiry (365 d), undated factor (0.5), and with/without-stars replay (needs provider traffic approval).
- Web gaps: dashboard strip and shelf lack "Not this artist"; no client exposes star-seed or discovery-mode settings; S1c reason lines and blocklist screens not yet checked in a browser.

## 2p. Server efficiency — Phase K decisions open

- Plan: [`efficiency.md`](plans/efficiency.md). K2–K6 and #1177 merged; not deployed.
- Open: owner approval for K3 `reviews` prefetch cap and K4/K5/K6 restart side-by-side pass (provider traffic); waiting on evidence for S1 retention, C3 memory limits, wider K2 scope, and M2 album route latency.

## 2q. Web Listening Room redesign — L0–L2 merged, L3 in review

- Plan: [`LISTENING_ROOM_WEB.md`](plans/LISTENING_ROOM_WEB.md); design package in [`design/listening-room/`](design/listening-room/).
- L0 (#1221), L1 (#1222), and L2 (#1248) merged; L3 (lead, Up next, Daily picks and reasons) in review (Genre spread tab omitted until stored lens endpoint serves it).
- **Next:** review L3, complete browser checklist and lead-cover fallback check, then build L4 (Artist Deep Dives, Personal Discoveries, Discover music).

## 2t. FirstFM — Last.fm removal built, runtime checks open

- Plan: [`FirstFM.md`](plans/FirstFM.md). F1.1–F5.2 built. Open: live runtime verification (ListenBrainz popularity, Deezer fallback, ListenBrainz radio scrobbling/love) and deployment.

## 2u. LB-19 Web radio mixes — implemented, browser check open

- Artist Radio/Discovery Mix previews, private saves and discovery downloads: [`contract`](contracts/RADIO_MIX_ACTIONS_CONTRACT.md). Isolated browser checks pending: browser host unavailable in the implementation session.

## 2n. Simplification candidates

One line each: file, simplification, why deferred. Remove when done.

- `navidrome_server.py`: acquisition adapters (`_slskd_track_identity`, `_slskd_path_match_diagnostics`, `_slskd_extract_candidates`, `_discovery_import_matched_album_files`, `_discovery_switch_to_next_source(_locked)`, `_discovery_import_completed_source(_locked)`) — safety-critical, patched in `tests/test_acquisition_safety.py`.
- `navidrome_server.py`: `_discovery_is_various_artists` — plain forward to `discovery.recommendations.is_various_artists` (3 callers).
- `navidrome_server.py`: `_bridge_deep_dives` — 1 caller, 6 lines (would move to `discovery/deep_dive_bridge.py`).
- `navidrome_server.py`: `discovery_skip_acquisition_source` — 1 caller (`app/api/acquisitions.py`), binds acquisition lock/DB/lifecycle.

## 3. Recommendation engine — gated

- `CF_MAX_PAGES` stays 4; `recommendation_selection_policy = family_coverage` is backend-only opt-in (PR #573, default `quota`, genre-tag lookups 120/135). Plan: [`engine2.md`](plans/engine2.md).
- Open/optional: examine why recent-genre cap removes ~60% of candidates; 8 CF pages only if owner wants more supply. Do not change ranking weights or run live captures without owner approval.

## 4. Parked decisions — do not start without a new decision

- **Material 3 ordinary themes (2026-11-03):** Workspace (web) and Android M3 mockups not approved.
- **Recommendation settings UI:** paused; replay captures do not yet freeze policy setting ([`DIVERSITY_SETTING_ROADMAP.md`](archive/parked/DIVERSITY_SETTING_ROADMAP.md)).
- **Gap Radar full discography endpoint (2026-11-04):** needs new decision; must be a new module (D-016).
- **Server V2 Music Intelligence:** Phases 0–7 server work merged; remaining items in [`ServerV2.md`](plans/ServerV2.md). Optional owner step: install AudioMuse-AI Navidrome plugin.
- **Releases:** v0.2.2 published 2026-10-22, not deployed; further publication/deployment requires owner authorization.
- **External MCP clients:** retired ([`MCP_RETIREMENT_PLAN.md`](archive/completed/MCP_RETIREMENT_PLAN.md)).
