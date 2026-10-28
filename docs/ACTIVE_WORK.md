# Active work

This is the short queue of unfinished or explicitly parked work. GitHub `main` is authoritative. Check current code, open PRs, and CI before starting anything; do not infer current state from archived notes.

## 1. Runtime verification — complete

- The owner confirmed that failed-track retry/recovery and masked slskd artist-query behavior have been tested and approved. These are no longer active verification tasks.
- Keep publication and deployment decisions separate from test approval; no deployment is implied by this confirmation.

## 2. Reported bugs — status

- Imported-album suggestion suppression is merged in PR [#530](https://github.com/abucalip/navi-librarian/pull/530) as `0b2bda011b86d2c08a0179e5df801c7891c10f9a`; it preserves the future-release filter from PR #528. Required CI, including the full unit suite, passed on tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`.
- UI fixes from original PRs #531–#535 are integrated: icon-only mobile navigation (#546), artist bio in the album panel (#547), equal-width ranked rows (#533), stable acquisition rendering (#534), and smaller/faster card artwork (#535). Required workflows passed on each final reconciled head; details are recorded in `PROJECT_LOG.md`.
- The owner waived manual browser checks for this merge batch; they were not performed. Artwork performance was not measured, and live browser/runtime behavior is not claimed. No image publication or deployment occurred.

## 2a. Dashboard UI bugs/changes — reported by the owner

- **Bios in album rows — done in PR [#554](https://github.com/abucalip/navi-librarian/pull/554)** (`c9fcf3289f37984258aca5b62891d700c569d5c1`): larger artwork and the artist bio in the middle of Recommendations, New releases, and Personal discoveries rows; fixed row height with click-to-expand bios. Remaining check: confirm the Docker packaging/full-suite run for the merged head finished green.
- **“Similar to:” label — merged in PR [#557](https://github.com/abucalip/navi-librarian/pull/557)** as `45cf5abe0257e70fe0d0573365259c2d0c7c2c10`, from tested head `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`. The server now supplies similar listened-to artists for adjacent recommendations; Recommendations and Personal discovery rows display “Similar to: …” when available. Full suite and required CI passed on the exact PR head. The owner waived manual browser checks; they were not performed. Not published or deployed.

- **Remaining 2a items — done.** Adventurous rows, New releases rows, dashboard album-card bios, and Deep Dives bio/year were integrated earlier (PR #555 and related; the owner browser-tested #555). The owner confirmed the smaller section labels and the Deep Dives card spacing are done.

- **Deep Dives server-provided row keys/labels — merged in PR [#562](https://github.com/abucalip/navi-librarian/pull/562)** as `650a72718bfcd40a63ce67c5f869e71fd3a18d85`, from reconciled and fully tested PR head `76142e1d0f2d48b59a1355e36c7372c4ed6f7123`. Backend now supplies `genre_row` and `genre_row_label`; the frontend consumes those values rather than duplicating genre-family classification. Regression tests cover normalization, fallback, and display labels. All required CI workflows passed on the exact PR head, including the full unit suite/Docker build, container smoke, image validation, and release-workflow validation (publishing skipped). The owner waived manual browser verification; it was not performed. Not published or deployed.
- **Album panel bio — fixed in PR [#560](https://github.com/abucalip/navi-librarian/pull/560)** (`ffff550c2336ca3dcd56a301c9ae7fffe9f0104b`, head `0f2ae27562a175e237a7c7364d380dae7b49f5a0`). Root cause: the server's artist-bio filter rejected Wikidata descriptions without band/singer-type words, so "jazz saxophonist", "pianist", and similar returned no bio. Not browser-verified.
- **Deep Dives artwork speed — code change merged in PR [#558](https://github.com/abucalip/navi-librarian/pull/558)** (`d44c01669611bd11acfaa4f1197905afed7f9f08`, tested head `976c86e77034322e53cc7aea9691fa840c2d6146`). Full suite and required automated workflows passed. The owner waived manual browser verification; artwork timing was not re-measured and the change is not browser-verified. No publication/deployment. If the issue persists after an authorized deployment, measure browser timings before another fix.
- Follow UI acceptance gates in `TEST_PLAN.md` and `LOCAL_UI_TESTING.md`; keep bio/similarity logic server-side.

## 2b. Replace hard-coded taste with derived behavior — closed

The plan in [HARDCODE_REPLACEMENT.md](HARDCODE_REPLACEMENT.md) is over; no phases remain and nothing from it is queued. Derived is the only taste-profile mode and the fixed taste tables and mode switch are removed (PRs #561-#572). Evidence and limits are in `PROJECT_LOG.md`.

## 2c. Engine 2 — next priority (draft roadmap: [engine2.md](engine2.md))

**Phase 4 status (2026-10-24):** built and merged (slices 1 to 4, PRs #590 to #598); PR #605 makes `engine2_lens_lists_enabled` default to on, with explicit `False` still supported. The owner approved enabling daily lens lists and deferred remaining browser checks (keyboard/focus, Get, Save/dismiss, reduced motion and screen readers). A Last.fm account Settings control remains parked; empty artwork and quality measurement are not active follow-ups. Phase 5 feedback loop is closed (PRs #600 to #603; see `engine2.md`). Play/download attribution and a UI display were dropped by the owner. Publication and deployment are separate decisions.

Goal: several complementary lists of 10 ("lenses") from one shared candidate pool, including obscure-album lists and lists driven by different history windows. Evidence and phases are in `engine2.md`; measurements are in `PROJECT_LOG.md` (2026-10-23, two entries). Provider budget increases and live captures still need the owner's approval.

**Phase 1 is complete (2026-10-23); the Deep cuts lens is defined in `engine2.md` (owner-approved). Phase 2 (lens framework and evaluation metrics) is complete:** the lens field, the Now, Genre spread and Deep cuts lenses, partitioning, Deep cuts pool adapter, and per-lens/set metrics are merged (PRs #575, #577, and #578; not wired into runtime; see `PROJECT_LOG.md`). Phase 3 is underway: PR [#580](https://github.com/abucalip/navi-librarian/pull/580) added pure history-window helpers (merged as `ede38e969956d1907ba25e579203c6d4b5805c3b`); PR [#581](https://github.com/abucalip/navi-librarian/pull/581) added the unwired Deep cuts tiered supply; PR [#582](https://github.com/abucalip/navi-librarian/pull/582) keys radio answers by lens and day (merged as `5018446c45c000fefcde6a4955a6bcb6e1943f77`). Repeated live runs show a window changes the pool only through its seed tags. Time-window profiles were reopened by the owner on 2026-10-24: the history profiles (repeated tracks outside the dominant tags, obsessions, new since 2018, dormant) are merged in PR #583 and unwired. Run through the real seed selection, the repeated-track profile shares no seed tag with Now, Long-term or Rediscovery, while Long-term and Rediscovery share 5 of 6; the repeated-tracks lens is defined and unwired (PRs #584 and #585); the owner approved the Repeated tracks gates on 2026-10-24 (tag count at least 2, album listeners 300 to 50,000, one album per artist, at most 2 per seed, known artists excluded), decided that Obsessions becomes a lens, and skipped the radio-path secondary-type fix (see `PROJECT_LOG.md`, 2026-10-24). The Obsessions lens definition was approved by the owner on 2026-10-24 (PR #587, unwired). The tag source for artists with no genre tags is merged (Last.fm top tags restricted to MusicBrainz genres, PR #588, unwired), the Deep cuts radio tiers keep 10 albums per seed (PR #589), and live runs of Repeated tracks and Obsessions with the radio working filled 6 of 10 slots at 5 albums per seed and 10 of 10 at 10 in a single draw (see `PROJECT_LOG.md`, 2026-10-24). Tier fall-through was measured and left unchanged. Phase 3 is complete (2026-10-24). The Phase 4 plan (precompute and serve the Deep cuts, Repeated tracks and Obsessions lists once a day, behind a setting that defaults to off) was approved by the owner on 2026-10-24. Slice 1, the pure list builder, is merged (PR #590) and unwired; slice 2 (pool gatherer, PR [#591](https://github.com/abucalip/navi-librarian/pull/591), merged as `cca42e3cfde534571d319206eff8ab4fa0c461ff`) is merged and unwired; slice 3 (storage and serving, PR [#592](https://github.com/abucalip/navi-librarian/pull/592), merged as `0a8f9090fbb218f6508b33d9e72ebedbcdc64fd1`) is merged and unwired; slice 4 (UI) has not been started; the lens adapters live in `discovery/lens_service.py` (PR [#593](https://github.com/abucalip/navi-librarian/pull/593), D-016), and the manual "all" refresh trigger is merged (PR [#594](https://github.com/abucalip/navi-librarian/pull/594)); see `engine2.md`, Phase 4. Helpers and supply remain unwired into runtime. Done in Phase 3: the 50 to 75% radio band parameter and tiers (PRs #580 and #581), the MusicBrainz tail (#581, measured alone 2026-10-24), and the title-marker check (recorded 2026-10-23; the radio-path secondary-type gap is measured and the owner decided to skip the fix). Runtime wiring is Phase 4. Phase 1 steps and results, in order:

1. ~~MBID-keyed popularity~~ — measured and implemented in PR [#574](https://github.com/abucalip/navi-librarian/pull/574) (merged as `eb4cb16`, not wired into runtime): album listeners by release MBID cover 166 of 203, artist listeners 203 of 203; Deezer and Discogs are weaker cross-checks. Live run of the module: 186 of 203 albums, the rest on the artist fallback. Required CI passed on the merged head. Step 1 is done; using the signal in a lens or ranking is a later, separate decision. See `PROJECT_LOG.md` (2026-10-23).
2. **Evaluated 2026-10-23 (see `PROJECT_LOG.md`; re-checked against four listening months, AUC 0.43-0.60, no reliable prediction):** tag/family cosine against the recent profile is a weak taste signal (AUC 0.53-0.59, owned vs unowned) and a third of tag-lane artists have no tags; a second signal (similar-artist links, artist tags for the lane) is needed. Original goal: a taste-fit score for tag-lane candidates, evaluated offline. They currently all score 0.035 and never surface, and they are where obscure candidates come from (29 of 40 obscure, against 4 of 163 from CF).
3. **Done 2026-10-23 (window test added):** a dense 2012-04 window gave six seeds with no overlap with the current ones, and a lane median artist audience of about 10k; see `PROJECT_LOG.md`. Original finding: the lane is seeded from the top 15 weighted recent artists (6 profile tags plus 2 explore tags); a history window can drive the seeds by replacing the weight map. See `PROJECT_LOG.md`.
4. **Prototype done 2026-10-23 (see `PROJECT_LOG.md`):** windows give different lists (0 to 1 shared artists), but two candidate sources trade off (MusicBrainz tag search: very obscure, junk risk; ListenBrainz tag radio: moderately known, noisy tags); gates matter more than the ranking signal. Follow-up: the radio's popularity band is inverted (low percent = most popular); 50 to 75% is the sweet spot; run end to end across five windows in about 35 s each (lists of 10 for four windows, 7 for the current profile; 0 shared artists across the first four). Needs an owner decision on the Deep cuts lens definition before Phase 2. Original goal: offline "deep cuts" prototype on existing captures.

Remaining Phase 0 decisions that come first or alongside: whether to raise `CF_MAX_PAGES` to 8 when coverage is on, add a settings control, or add extra data sources. The family-coverage policy itself is merged in PR #573, remains opt-in, and leaves `CF_MAX_PAGES` at 4. Listed in `engine2.md` under "Open decisions". Nothing in Phase 1 changes ranking weights or defaults.

## 2d. Global search and library browsing — P1 closed

- Contract: [SEARCH_CONTRACT.md](SEARCH_CONTRACT.md), approved by the owner on 2026-10-25. Section 11 is the P1 record; section 11.7 is the completion check; section 11.8 lists the follow-ups.
- **Merged:** P1 backend in PR [#609](https://github.com/abucalip/navi-librarian/pull/609) (squash `52b0010`); P1 UI in PR [#610](https://github.com/abucalip/navi-librarian/pull/610) (squash `f26ad96`, manual checklist waived); artist genre in PR [#611](https://github.com/abucalip/navi-librarian/pull/611) (squash `cf517fc`); the Various Artists and 502 gaps in PR [#612](https://github.com/abucalip/navi-librarian/pull/612) (squash `bf67e68`).
- **Carried forward, not P1 work:**
  - Index build time on the owner's server, recorded against section 2.1 (P5).
  - Manual refresh route, proposed in 11.8 and not approved.
  - Album artwork on owned-album items, proposed in 11.6 and not approved.
  - "Not in your library" results group, waiting for the P2 network sources.
  - Recommendation snapshot generation key, accepted as a deferred follow-up.
  - Safari, VoiceOver and keyboard-only checks in a real browser.
- **P2 (network sources):** complete (PRs #613 to #620). Limits carried forward are in `SEARCH_CONTRACT.md` section 12.10.
- **P3 (similar artists) and P3b:** merged in PRs [#621](https://github.com/abucalip/navi-librarian/pull/621) (squash `7f1b44f`, fusion slice) and [#622](https://github.com/abucalip/navi-librarian/pull/622) (squash `05b259c`, shared tags, owner boost, daily precompute). Contract: `SEARCH_CONTRACT.md` sections 7, 8.1 and 10. Closed out in the owner's direction on 2026-10-26.
- **P3 follow-ups, not yet verified (P4 did not change them):**
  - **Live provider check.** Nothing has run against the live MusicBrainz, ListenBrainz or Last.fm services or the owner's library. The first precompute pass should be timed and its call volume recorded: about 733 ListenBrainz radio calls at 2 s spacing, plus up to 10 MusicBrainz tag lookups per artist at 1 req/s. Record the results in `PROJECT_LOG.md`.
  - **Tuning.** The tag and boost weights (0.5), the 100-play scale, the 10-candidate tag limit, and the 6 h / 120 s precompute budgets are starting values. Check them against real results before treating them as settled.
  - **Partial artist pages until the tag cache is warm.** Tag lookups run at 1 req/s inside the 3 s page deadline, so artist pages often return `similar` as incomplete with reason `deadline` until precompute has filled the tag cache.
  - **Fixed precompute order.** Each daily pass starts from the same point in the library list. If a full pass ever runs past the 6 h budget, the artists at the end are never reached. Rotate the start point, or record the last artist reached, before this matters.
  - **Precompute is on by default**, with no settings switch. It runs only while the app process is running and the owned index is usable.
- **P4 (Discogs and genre pages): complete.** PRs [#623](https://github.com/abucalip/navi-librarian/pull/623) to [#625](https://github.com/abucalip/navi-librarian/pull/625) are merged: Discogs token settings and client, Discogs styles as a shared-tag source, global genre search, genre pages, and the Settings/genre UI. Record: `SEARCH_CONTRACT.md` section 13. Exact SHAs and CI: `PROJECT_STATUS.md` and `PROJECT_LOG.md`.
- **P4 follow-ups, not closed:**
  - **Owner decisions: approved (2026-10-26).** `tag_source: "navidrome"` for owned genre results and owned-before-unowned ordering on genre pages (`SEARCH_CONTRACT.md` 3.4, 3.8, 13.3).
  - **Live Discogs check: partly done (2026-10-26); the remaining live run tests are scheduled for the end of P5 (owner direction).** The auth header, Test call, style lookup, style browse, text search and bad-token failure were confirmed with a real token. Not run live: Discogs genre extraction, a real 429, the `Ash (2)` suffix, the Settings Test button in the app, and the whole app against live providers (13.2).
  - **Browser checks** were waived for the P4 batch and not performed: Settings tab, genre view, search genre results, keyboard and focus, narrow widths.
- **P5: closed with exceptions (2026-10-26).** PRs #626 to #629 are merged. Still open and deferred by the owner: real-browser checks; the 3.0 s `done` target with a slow MusicBrainz; P3 follow-ups (weight and scale tuning, full-library precompute timing, two artists whose precompute failed, a settings switch for precompute). Fixed: provider cache reads (#628), precompute start rotation (#629). Evidence in `PROJECT_LOG.md`.
- **Library pages: merged in PR [#630](https://github.com/abucalip/navi-librarian/pull/630)** (squash `70b5330`, tested head `327c477`; all required checks and the full unit suite passed in CI). Artist, album and genre pages reachable from everywhere; contract section 14. The manual browser checklist ([LOCAL_UI_TESTING.md](LOCAL_UI_TESTING.md)) has not been done. Not published or deployed.

### 2e. Refresh keeps the current page — implemented on branch `ui/refresh-keeps-page`, not merged

Today a browser refresh always returns to the dashboard, because the current page lives only in script state. Goal: a refresh returns to the page the owner was on. PR #630 (the library navigation it depends on) is merged.

Acceptance: refresh on any top-level page, and on an artist, album or genre page, reloads that same page; a bad or stale address falls back to the dashboard without an error; no secret or token ever goes into the address.

1. **Top-level pages.** Write the page name to the address hash (`#library`, `#settings`, and so on) in `showPage`, and read it at startup in place of the fixed `dashboard` default. Ignore a hash that is not a known page. Small change in `static/app.js`.
2. **Library pages.** Encode the artist, album and genre targets (`libraryNav.current`) in the hash, for example `#library/artist/<key>?id=&name=&mbid=` and `#library/album/<artist_key>/<album_key>?id=&artist=&name=&year=&mbid=`, with every part URI-encoded. Decode at startup and call `libraryOpen` for the target. Cover album names with slashes, quotes and accents.
3. **Back stack.** After a refresh only the current page is known, so Back returns to the library list. Record this as a known limit.
4. **Login.** If the session has expired, return to the same address after login (the login redirect must keep the hash).
5. **Browser Back and Forward (optional follow-up).** Push a history entry per page change and handle `popstate`, so the browser buttons step through the in-app pages. Decide separately; without it Back leaves the app.
6. **Tests.** Source-contract tests for the hash read and write, a round-trip test of the encode and decode helpers with awkward names, and a fallback test for an unknown hash. Then the manual refresh check on each page type.
7. **Docs.** Add the address format to `REQUIREMENTS.md` once agreed.

- **Status:** steps 1 to 7 (automated part of 6) are implemented on the branch. Step 5 (browser Back and Forward via pushState and popstate) is implemented too. The manual refresh check on each page type has not been done. Focused tests only (`tests/test_refresh_keeps_page_ui_contract.py`, login and library-search contract tests); the full suite is left to the owner and CI.
- Not published or deployed.

## 3. Recommendation engine — gated

- CF freshness capture repeated 2026-10-23 after the imported history was recomputed: outcome "mixed", defaults kept. Deeper CF pages measured at 4 / 6 / 8: the larger pool changed the final list by one album (9/10 overlap), so `CF_MAX_PAGES` stays 4. A recent-30-days vs all-time profile comparison showed ranking responds to listening habits but the final list barely does. Evidence and limits: `PROJECT_LOG.md` (2026-10-23 entry).
- **Family-coverage policy — merged in PR #573** (backend-only opt-in `recommendation_selection_policy = family_coverage`; default remains `quota`; genre-tag lookups 120/135). `CF_MAX_PAGES` remains 4. Evidence is limited to one profile and individual captures; replay captures do not freeze the policy setting, and listening-quality impact is unmeasured. A settings/UI control remains a parked decision. Measurements and roadmap: [engine2.md](engine2.md) and `PROJECT_LOG.md`.
- Open and optional, not started: examine why the recent-genre cap removes about 60% of candidates in both profiles; 8 CF pages only if the owner wants more candidate supply (the 2026-10-23 branch work shows 8 pages helps only with 120 tag lookups and the coverage policy; see `engine2.md`). Any live capture or higher provider budget needs owner approval. Do not change ranking weights without evidence and approval.
- Detailed older evidence, alternatives, and evaluation criteria: [archived recommendation-engine research](archive/recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md).

## 4. Parked decisions — do not start without a new decision

- **Other historical branches checked (2026-10-23):** `docs/ghcr-latest-fix` has no commits that `main` lacks, and `taste-profile-evaluation` differs from its remote only by merge commits (its work was squash-merged in #565). The former `diversity/family-coverage-allocator` work was pushed and merged in PR #573; it is no longer an unmerged work item.

- **Recommendation settings UI:** still paused; PR #573 added a backend-only opt-in `recommendation_selection_policy = family_coverage` setting while preserving `quota` as the default. It is merged but not published/deployed, and the evidence does not establish better listening outcomes. Replay captures do not yet freeze the policy setting. See the [archived diversity roadmap](archive/parked/DIVERSITY_SETTING_ROADMAP.md) and `PROJECT_LOG.md`.
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
