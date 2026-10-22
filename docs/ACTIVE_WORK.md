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

## 2b. Replace hard-coded taste with derived behavior — gated

Plan: [HARDCODE_REPLACEMENT.md](HARDCODE_REPLACEMENT.md). PR #563 externalized the shipped defaults (`9a659f6e9da175e475aa22f86c69492f40206869`); PR #564 then merged the opt-in `taste_profile_mode=derived` implementation as `508269f1177e35075330c903775f74e23c2f14af`. Its sparse-history fallback regression is fixed and all four required workflows passed on the exact PR head, including the full unit suite.

- **Phases 2-4 evidence merged** in PRs #565-#568 (details in `PROJECT_LOG.md`): ancestry grouping, taste clusters, a synthetic evaluator, and a fixed-vs-derived frozen-capture comparison. On the owner's live capture the top 10 shares 8 of 10 picks between modes, but 44 candidates receive an exploration bonus that the fixed profile never gives.
- **Complete.** Derived is the only mode (PR #569 made it the default; PRs #570 and #571, `b0a0132578e729edfaeec2303f68e67366c78fda` and `ba2f235a4f9e82fdb98139c50b5c512c83438824`, moved Deep Dives and tag-query labels to the derived vocabulary, corrected the ancestry table, and removed the fixed taste tables and the mode switch). Evidence is limited to one real jazz-leaning profile plus synthetic profiles.
- **Optional follow-ups, each needing its own go-ahead:** browser-check the new Deep Dives rows and "Style:" label; decide whether to drop the tag-to-family grouping rules in `settings/taste_defaults.json` (would lose regional families like African and Brazilian); extend the ancestry table with more tags via `scripts/build_genre_ancestry.py`; capture a non-jazz profile if one becomes available. See [HARDCODE_REPLACEMENT.md](HARDCODE_REPLACEMENT.md).

## 3. Recommendation engine — gated

- Repeat the ListenBrainz collaborative-filtering (CF) freshness capture after imported history has been recomputed. Any live capture requires owner approval.
- Only after freshness is understood, decide whether to request approval for deeper CF pages. Do not change ranking weights or increase provider requests/budgets without evidence and approval.
- Detailed evidence, alternatives, and evaluation criteria: [archived recommendation-engine research](archive/recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md).

## 4. Parked decisions — do not start without a new decision

- **Recommendation diversity setting/UI:** paused until candidate supply supports meaningful cross-pool evaluation. See [archived diversity roadmap](archive/parked/DIVERSITY_SETTING_ROADMAP.md).
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
