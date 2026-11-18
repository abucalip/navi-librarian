# Active work

This is the short queue of unfinished or explicitly parked work. GitHub `main` is authoritative. Check current code, open PRs, and CI before starting anything; do not infer current state from archived notes.

Finished and merged work, and owner checks on work merged before 2026-11-11, were moved on 2026-11-18 to [`archive/completed/ACTIVE_WORK_DONE_2026-11-18.md`](archive/completed/ACTIVE_WORK_DONE_2026-11-18.md) (full text, PR numbers and SHAs). Section numbers below are the old ones, so references still match. Entries here are either not started, not finished, or merged within the last week with the owner's check still open.

## 2e. macOS radio stage 2 — built, owner's live checks open

- All slices S2-0 to S2-5 are merged (2026-11-13 to 2026-11-14). Open: the owner's live checks in [`RADIO_PLAYBACK_PROPOSAL.md`](plans/RADIO_PLAYBACK_PROPOSAL.md), S2.10. Never verified against a real station: sound, the live mini player, the widget LIVE state, the menu bar item and popover, Download from the bar, media keys and Control Centre, reconnect and sleep timer, ⌘1 to ⌘9, Night mode, VoiceOver, narrow window. Full macOS suite not run.

## 2h. Round 2 Neobrut layouts — P7 closeout not done

- P1 to P6 and the revisit are merged. P7 (closeout: documents, and a published release only when the owner authorises it) is "not started" in the plan table ([`BRUT_LAYOUTS_PLAN.md`](archive/completed/BRUT_LAYOUTS_PLAN.md)).

## 2i. Round 3 Neobrut themes — remaining phases not started

- Plan: [`BRUT_ROUND3_PLAN.md`](plans/BRUT_ROUND3_PLAN.md) (D-024). Zine Spread (P1) is merged; Pipeline Board is dropped. Not started, to begin only when the owner asks: **P3a** web Window Manager (shell, taskbar, single windows), **P3b** second album window (spike first), **P4** Android Receipt Roll, **P5** Android Binder, **V** optional palette variants, **P6** closeout.

## 2j. macOS client (Discair for Mac) — open decisions and recent checks

- **Keychain and first release:** the owner decides whether to accept one Keychain prompt per update, get an Apple Developer ID, or move logins out of the Keychain (`macos/DESIGN.md`, "Keychain partition finding"). The first release waits for the owner's authorisation (`macos/Packaging/RELEASING.md`). M7 (Bento Block, Native Glass v2) stays later and is not started.
- **Night mode and Appearance tab (#1015, 2026-11-13):** the full macOS suite was not run; the owner looks at Night across the screens, decides whether releasing the hue slider (not live drag) is acceptable, and checks the Mini Player staying dark.
- **Another booklet button (#1016, 2026-11-13):** the owner looks at the button on the Mac and on a device; full suites not run.

## 2k. macOS and Android redesign (`docs/plans/redesign.md`) — open items

- Android A8b: the playlist route (item 1) and the device check (item 7) remain; the A9 device review is open. D5 (`savePlayQueue`) has no live Navidrome check yet. macOS audit follow-ups F1 to F13 are listed in the plan as not started. Not published or deployed.
- **macOS Home "Marquee":** H1 to H3 are merged; **H4, the owner checks Home against the real server** (plan section 8: [`MACOS_HOME_MARQUEE_PLAN.md`](archive/completed/MACOS_HOME_MARQUEE_PLAN.md)). Simplification candidate: `HomeDashboard.neverPlayedChange` and its baseline input now feed nothing on Home.

## 2l. Android art-led themes (Soft Brut, Flow) — owner phone checks open

- All build steps are merged (Soft Brut S1 to S4, Flow F1 to F4, 13 palettes, Flow Discover option B D1 to D4). Open for the owner: the phone check of Soft Brut and Flow pages against the mockups in [`design/android-art-themes/`](design/android-art-themes/) (including the Flow bar blur and status bar icons, and Soft Brut fixes batch 1 from #1017), the 13 palettes against the PNGs in `design/android-art-themes/palettes/`, and Flow Discover (each of the seven lists, the sheet, swipes across all seven, a night palette). Flow Discover open point O1 (Save and ⋯ touch size) is for the owner. Filtered tests only throughout; nothing screenshot-compared.

## 2l-2. Flow Home: Threads and Shelf mixer — plan approved, no code yet

- Plan and design system: [`Home_threads_mixer.md`](plans/Home_threads_mixer.md); mockups (spec) in [`design/android-art-themes/flow/home-threads-mixer/`](design/android-art-themes/flow/home-threads-mixer/). The owner picked A's Threads and C's Shelf mixer on 2026-11-15 from three Home proposals (A Threads, B Time, C Shelves). Flow only on Android, plus two server additions.
- Steps: S0a (smart-playlist preview endpoint and song-list cache), S0b (`album_label` album path kind), H1 (Android data and rules), H2 (Threads section), H3 (Why they connect sheet), M1 (Shelf mixer), M2 (Save and Saved), C (closeout). **Next:** S0a. Open points O1 to O3 (whole albums on Play, play-count thresholds, default centre) have defaults and wait for the owner.

## 2m. Android Paths sheets (Trail) — built, owner's phone check open

- Steps 1 to 6 are merged (2026-11-13). Left: the owner's phone check of the Album and Artist Paths sheets.

## 2m-2. Star Operation — built, open decisions

- S1 to S4b are merged (2026-11-15). Open: the star-seed half-life (180 days), expiry (365 days) and undated factor (0.5) are proposed and need the owner's approval, and the with/without-stars replay was not run (needs provider traffic and approval). No client shows the star-seed or discovery-mode settings. Not seen in a browser, on a device or in the app: S1c reason lines (web, Android card, macOS), the blocklist screens. Known gaps: Android Home pick menus lack the new entries; macOS offers a pick's first genre only; the web dashboard strip and shelf have no "Not this artist". Genre spread under the discovery mode is unmeasured.

## 2o. Android Gallery theme — owner's phone check open

- G1 to G7 and the follow-ups #1125 and #1126 are merged. Open: the owner checks the Gallery theme on the phone (all eight palettes, the motion, the Radio section on Home). Differences from the mockups are in `PROJECT_LOG.md`.

## 2o-2. Android Bento and Index themes

- Specs: [`BENTO_THEME.md`](plans/BENTO_THEME.md) (B1 to B6) and [`INDEX_THEME.md`](plans/INDEX_THEME.md) (I1 to I6); owner decisions B1 to B7 and I1 to I7 taken as proposed (2026-11-17). Palettes: Bento Sorbet (default), Licorice, Riviera; Index Signal Blue (default), Newsprint Red, Graphite Orange, Field Green. By owner rule, every missing server route or field is built in its own PR before the client step that draws it.
- **Bento: not started.** B0 (server data audit, spec section 11a) has not run; then B1 to B6. Bento and Index first steps must not run at the same time (both branch `Palette.kt`, `Theme.kt`, `Motion.kt`).
- **Index: I0 to I6 merged** (#1192 to #1204; I1 to I6 are #1197 to #1202, then #1203 Paths and #1204 Home swipe). Open: the owner checks I3 to I6 on the phone (not checked: the other three palettes, Server version and ping because the I0 server is not deployed, a download in progress, the live radio page, timed lyrics, Insights lens rows and the anniversary block). Owner decisions on new `INDEX_THEME.md` 11a rows: Stats hours this month, Stats lossless share, the pick sheet's "Why this pick?", artist library position, unowned album "PICK 03 / 12", genre artist album counts, live radio Save and previous/next station, and whether to build the discover mockup's lettered taste sheet (Discovery mode, Blocked genres, More like this, Refresh lists). Then the Index closeout. Known shared bug, not in scope: system Back with a Paths step open closes the whole sheet on every theme.

## 2p. Server efficiency — evidence and decisions open

- Plan and evidence: [`efficiency.md`](plans/efficiency.md), Phase K. K2 to K6, the K3 parts, the no-decision follow-ups and finishing-up #1177 are merged; nothing is deployed (the K3 caps are the `compose.yaml` default, so the job runs on the next worker deployment).
- Open: the K3 album-reviews prefetch stays off until the owner approves a `reviews` cap; waiting on evidence: S1 retention, C3 memory limits, wider K2 scope; M2 acceptance (album route time independent of provider latency) not measured; the restart side-by-side pass (K4/K5/K6) needs the owner's approval for provider traffic.

## 2q. Web client Listening Room redesign: design proposed, no code yet

- The owner picked direction A ("Listening Room") on 2026-11-17 from three Home mockups, and asked for fuller reasons for each pick (as in direction C). The design system and build plan are in [`LISTENING_ROOM_WEB.md`](plans/LISTENING_ROOM_WEB.md), with the package in [`design/listening-room/`](design/listening-room/): tokens, components, icons, fonts, and Home, reasons and states mockups at 1440 and 390. The owner asked for a docs PR.
- Open owner decisions D1 to D4 are in section 10 of the plan. The recommendations: the server builds a shared `why` object; Listening Room becomes the web default, and the old web layouts are retired only after the owner's check; Discover music stays on Home; covers that cannot be sampled get the fallback tint.
- 2026-11-17, second round: the owner asked for mockups of all pages, with no Paths on the web, and for the reasons behind each pick to be showcased (prominent, not centre-aligned). Now drawn:
  - 25 pages at 1440 and 390: Discover (six lists), Library (two views), Artist, Album (two states), Album modal, Genre, Search, Saved, Blocklist, Acquisitions, Radio, Settings (six tabs) and Sign in;
  - the reason panel (plan 5.6 and 6.3);
  - page specs in section 8;
  - slices L7 to L14.

  Paths is gone from the web design.
- **Next action:** after the owner's review, start L0 (server audit and missing fields, plan section 9), then L1 to L6 (Home), then L7 to L14.

## 2r. macOS Paths and Booklet sheets — owner check open

- All slices are merged (P0 to P2, B1 to B4; 2026-11-17 to 2026-11-18). Open: the owner's check of both sheets in a real window and the CPU measurements (Paths five cases from P1; Booklet open after B2 and B3). D4 unanswered (recommended: no language tag). Details: [`MACOS_PATHS_BOOKLET.md`](plans/MACOS_PATHS_BOOKLET.md).

## 2s. macOS design details polish: plan written, no code yet

- The owner asked on 2026-11-18 for a fine-detail review of the Cupertino macOS client from 12 screenshots. The issues covered are alignment, overlaps, spacing, text sizes and small navigation details, including the album and artist hero not meeting the window's round corners.
- The plan is [`MACOS_DESIGN_DETAILS.md`](plans/MACOS_DESIGN_DETAILS.md). It has slices D1 to D8:
  - D1: shell, corners and hero edges
  - D2: hero alignment
  - D3: bottom insets and the Pipeline dock
  - D4: control consistency
  - D5: list columns
  - D6: Now Playing
  - D7: graph and map labels
  - D8: copy
- The owner's decisions (2026-11-18), all as recommended:
  - the hero fades in the sidebar gutter and collapses on scroll;
  - selected tabs use the dark neutral style in Night and a white chip on a light grey track in Day;
  - inspectors run full height;
  - the artist bio is left-aligned.
- The cover stays shown twice (sidebar slot and player bar). No questions remain. Next: D1.

## 2n. Simplification candidates

One line each: file, what could be simplified, why it was not done in the PR that found it (see "Opportunistic simplification" in [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)). Remove the line when it is done or no longer true.

- `navidrome_server.py`: acquisition adapters `_slskd_track_identity`, `_slskd_path_match_diagnostics`, `_slskd_extract_candidates`, `_discovery_import_matched_album_files`, `_discovery_switch_to_next_source(_locked)`, `_discovery_import_completed_source(_locked)`. Not done in #1172: they bind `_music_key`, locks and other module callbacks, several are patched in `tests/test_acquisition_safety.py`, and the code is safety-critical.
- `navidrome_server.py`: `_discovery_is_various_artists`, a plain forward to `discovery.recommendations.is_various_artists`. Not done in #1172: it has three callers, and that pass only took single-caller code.
- `navidrome_server.py`: `_bridge_deep_dives` (one caller, six lines of logic). Not done in #1172: it would have to move into `discovery/deep_dive_bridge.py`, which is a move, not a removal.
- `navidrome_server.py`: `discovery_skip_acquisition_source` (one caller, `app/api/acquisitions.py`). Not done in #1172: it binds the acquisition lock, the database connection and the lifecycle.

## 3. Recommendation engine — gated

- CF freshness capture repeated 2026-10-23 after the imported history was recomputed: outcome "mixed", defaults kept. Deeper CF pages measured at 4 / 6 / 8: the larger pool changed the final list by one album (9/10 overlap), so `CF_MAX_PAGES` stays 4. A recent-30-days vs all-time profile comparison showed ranking responds to listening habits but the final list barely does. Evidence and limits: `PROJECT_LOG.md` (2026-10-23 entry).
- **Family-coverage policy — merged in PR #573** (backend-only opt-in `recommendation_selection_policy = family_coverage`; default remains `quota`; genre-tag lookups 120/135). `CF_MAX_PAGES` remains 4. Evidence is limited to one profile and individual captures; replay captures do not freeze the policy setting, and listening-quality impact is unmeasured. A settings/UI control remains a parked decision. Measurements and roadmap: [engine2.md](plans/engine2.md) and `PROJECT_LOG.md`.
- Open and optional, not started: examine why the recent-genre cap removes about 60% of candidates in both profiles; 8 CF pages only if the owner wants more candidate supply (the 2026-10-23 branch work shows 8 pages helps only with 120 tag lookups and the coverage policy; see `engine2.md`). Any live capture or higher provider budget needs owner approval. Do not change ranking weights without evidence and approval.
- Detailed older evidence, alternatives, and evaluation criteria: [archived recommendation-engine research](archive/recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md).

## 4. Parked decisions — do not start without a new decision

- **Material 3 ordinary themes (parked 2026-11-03):** Workspace (web), Expressive, Seeded, Thumb Zone and Triage (Android) were mocked in `docs/design/brut-round3/mockups.html` (tabs 6 to 10) and are not approved; do not build them without a new owner decision.

- **Recommendation settings UI:** still paused; PR #573 added a backend-only opt-in `recommendation_selection_policy = family_coverage` setting while preserving `quota` as the default. It is merged but not published/deployed, and the evidence does not establish better listening outcomes. Replay captures do not yet freeze the policy setting. See the [archived diversity roadmap](archive/parked/DIVERSITY_SETTING_ROADMAP.md) and `PROJECT_LOG.md`.
- **Gap Radar full discography (parked 2026-11-04):** the macOS Gap Radar (PR #745) only shows gaps among Librarian picks, which carry no year. A later server endpoint returning an artist's discography (for example MusicBrainz release groups with year and type) would let it show every album an artist released, placed on a real year axis. Not started; needs a new decision, and per D-016 the code would go in a new module, not `navidrome_server.py`.

- **Server V2 Music Intelligence:** Phases 0 to 7 server work is merged (store, editions, insight lenses, knowledge pages and paths, sonic proxy, sideman paths), and the macOS client gate (graph explorer, atlas, timeline) is built. Remaining client slices and verification are in [ServerV2.md](plans/ServerV2.md); history is in [archive/ServerV2_HISTORY_2026-11-09.md](archive/ServerV2_HISTORY_2026-11-09.md) and the moved entries in the done archive. Do not add provider traffic beyond the approved samples or change an existing API without the owner's approval. Not published or deployed. Optional owner step: install the AudioMuse-AI Navidrome plugin (D-6, proxy first).

- **Releases:** v0.2.2 image published 2026-10-22 (see `PROJECT_STATUS.md`); not deployed. Further publication or deployment requires explicit owner authorization. See [archived release preparation](archive/release/RELEASE_v0.2.md).
- **External MCP clients:** repository MCP retirement is complete; any external-client migration is unverified and outside repository evidence. See [archived MCP retirement record](archive/completed/MCP_RETIREMENT_PLAN.md).

## Reference map

- Current status and single next action: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Permanent development rules: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Product behavior: [REQUIREMENTS.md](REQUIREMENTS.md)
- Test gates: [TEST_PLAN.md](TEST_PLAN.md)
- Current architecture and boundaries: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
- Chronological implementation/verification evidence: root [PROJECT_LOG.md](../PROJECT_LOG.md)
- Historical roadmaps and completed plans: [archive](archive/)
