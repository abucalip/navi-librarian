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

Goal: several complementary lists of 10 ("lenses") from one shared candidate pool, including obscure-album lists and lists driven by different history windows. Evidence and phases are in `engine2.md`; measurements are in `PROJECT_LOG.md` (2026-10-23, two entries). Provider budget increases and live captures still need the owner's approval.

First steps (Phase 1), in order:

1. ~~MBID-keyed popularity~~ — measured and implemented in PR [#574](https://github.com/abucalip/navi-librarian/pull/574) (merged as `eb4cb16`, not wired into runtime): album listeners by release MBID cover 166 of 203, artist listeners 203 of 203; Deezer and Discogs are weaker cross-checks. Live run of the module: 186 of 203 albums, the rest on the artist fallback. Required CI passed on the merged head. Step 1 is done; using the signal in a lens or ranking is a later, separate decision. See `PROJECT_LOG.md` (2026-10-23).
2. **Evaluated 2026-10-23 (see `PROJECT_LOG.md`):** tag/family cosine against the recent profile is a weak taste signal (AUC 0.53-0.59, owned vs unowned) and a third of tag-lane artists have no tags; a second signal (similar-artist links, artist tags for the lane) is needed. Original goal: a taste-fit score for tag-lane candidates, evaluated offline. They currently all score 0.035 and never surface, and they are where obscure candidates come from (29 of 40 obscure, against 4 of 163 from CF).
3. **Done 2026-10-23 (window test added):** a dense 2012-04 window gave six seeds with no overlap with the current ones, and a lane median artist audience of about 10k; see `PROJECT_LOG.md`. Original finding: the lane is seeded from the top 15 weighted recent artists (6 profile tags plus 2 explore tags); a history window can drive the seeds by replacing the weight map. See `PROJECT_LOG.md`.
4. Offline "deep cuts" prototype on existing captures: how many obscure, well-fitting candidates exist.

Remaining Phase 0 decisions that come first or alongside: whether to raise `CF_MAX_PAGES` to 8 when coverage is on, add a settings control, or add extra data sources. The family-coverage policy itself is merged in PR #573, remains opt-in, and leaves `CF_MAX_PAGES` at 4. Listed in `engine2.md` under "Open decisions". Nothing in Phase 1 changes ranking weights or defaults.

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
