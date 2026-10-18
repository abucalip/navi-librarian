# Recommendation diversity setting roadmap

**Status:** Backend preference contract and allocator-level MMR integration are merged in PR #326 (merge commit `ef8173a4ce47b0b4b1ec72fc567377dbd0cf1dd0`; exact tested PR head `f502e6c3e2877ec88b8e8f1a744e4d0fdf6b9c1f`). The persistent batch-history foundation is merged in PR #329. The Settings UI is **not ready to implement** until the calibration and correctness gates below are addressed. Publishing and deployment remain paused.

## Product goal and eventual UI

Name the setting **Recommendation diversity**, not MMR. MMR is an implementation detail. The intended control is a 0–100 slider, but its final value-to-penalty mapping and upper endpoint are deliberately **not yet approved**.

Provisional endpoint copy (revise after evidence-based calibration):

- **Lower — More familiar:** “Prioritize close matches to your taste and the strongest individual recommendations. The list may contain more similar-sounding albums.”
- **Higher — More exploratory:** “Favor variety across artists and styles while keeping recommendations relevant to your taste. Some picks may be less familiar.”

Do not promise that high settings “still give good matches” until a relevance-retention guardrail has been established. Explain that the setting balances relevance and variety; it does not change the user's profile or library. A one-point change need not change every list.

## Current implementation and evidence

### Merged backend contract

PR #326 persists `recommendation_diversity` as a strict integer 0–100, exposes `GET/PUT /api/settings/recommendation-diversity`, rejects missing/boolean/float/string/out-of-range writes, and safely reads absent or corrupt stored values as 0. At 0, MMR is bypassed and legacy ordering is preserved. Nonzero settings apply dynamic MMR within the existing allocator passes and only among ownership-clear candidates.

The integration preserves ownership gates, existing category/style/family policy, the one-album-per-artist cap, deterministic ties, sparse-pool behavior, and the bounded 60-check budget. The UI is not implemented.

### Existing frozen-fixture evidence (not a quality guarantee)

The owner ran `recommendation_mmr_evaluate.py --identity-free` in the isolated environment using source revision `acb437f85d8d5c8ae2e6cdb5240457423e9b6e64` against the existing private fixture captured from source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`. The command exited 0, reported 83 gathered albums, 1,733 library albums, 66 scored candidates, 17 rejected rows, 10 baseline recommendations, zero network providers, and no provider-tape replay. No fixture or identity-bearing report was committed.

Measured lambda points were only `0, 0.1, 0.25, 0.5, 0.75, 1.0`:
- `0`: mean pairwise similarity 0.1044; 7/10 baseline items retained; baseline relevance-score retention 85.6%.
- `0.25` and `0.5`: similarity 0.1007; 7/10 retained; relevance retention 85.5%.
- `0.75` and `1.0`: similarity 0.0591; 7/10 retained; relevance retention 85.5%. Lambda 1.0 showed no additional measured benefit.
- All tested points returned 10 eligible items, 10 unique artists, no duplicate non-empty artist keys, and deterministic repeated results.

This is one 66-candidate frozen pool with a 10-item baseline, not evidence of future-listen hit-rate/nDCG, stable trade-offs across pools, or broad user satisfaction. The slider currently implies a linear 0–1 mapping that the evidence does not justify. In the current implementation, larger lambda increases the similarity penalty. Treat 0.75 as a candidate point, not a production default.

**Explicit boundary:** the earlier “35-combination”/relevance-floor reproduction is dismissed as a decision input. The actual recorded CLI output has six lambda results and no relevance-floor dimension. Do not rerun that reproduction or collect another live capture to reconcile it. The calibration step below is a distinct, explicitly scoped offline sweep against the already-existing fixture; it must not create or publish a new capture or disclose candidate identities. If the owner later decides not to run any further fixture evaluation, keep the UI blocked and do not pretend the slider is calibrated.

## Revised implementation sequence and gates

### 1. Offline slider calibration — measured, single-fixture result

Completed the identity-free sweep against the existing private frozen fixture only. The fixture checksum/schema validated; no provider events were replayed and zero network providers were used. The run used 66 scored candidates, 17 rows rejected for explicit hard-rejection/missing-score handling, and the captured 10-item baseline. All 21 settings returned 10 candidates from the evaluator's rankable pool, 10 unique artists, and deterministic repeated selections. No selected candidates lacked tags in this fixture.

| Slider setting (penalty λ) | Mean pairwise similarity | Baseline items retained | Mean selected raw-score retention vs setting 0 | Baseline relevance-score retention |
|---|---:|---:|---:|---:|
| 0 (0.00) | 0.1044 | 7/10 | 100.0% | 85.6% |
| 5–15 (0.05–0.15) | 0.1016 | 6/10 | 99.99% | 80.6% |
| 20–70 (0.20–0.70) | 0.1007 | 7/10 | 99.92% | 85.5% |
| 75–100 (0.75–1.00) | 0.0591 | 7/10 | 91.72% | 85.5% |

The grouped ranges represent every tested setting in steps of five: metrics were identical within each range. Compared with setting 0, similarity falls only about 2.7–3.5% through λ=0.70, then falls about 43.4% at λ=0.75. There is no measured additional benefit from λ=0.80 through 1.00. Mean selected raw discovery score at λ=0.75 is about 8.3% lower than at λ=0; baseline top-10 retention remains 7/10. At λ=0.05–0.15, only 6/10 baseline items are retained, and baseline relevance-score retention falls to 80.6%.

**Calibration recommendation (provisional, not production approval):** cap the effective penalty at λ=0.75; values above that are indistinguishable on this fixture and add no measured benefit. Do not ship a simple linear 0–1 mapping as if each slider increment has a meaningful effect. The evidence supports a clear high-diversity transition near 75, but does not identify a useful smooth mapping through the broad flat middle. Treat any piecewise mapping as provisional until normalization and cross-pool behavior are tested.

**Candidate relevance guardrail for explicit review:** require at least 90% of setting-0 mean selected raw discovery score and retain at least 7/10 baseline items. λ=0.75 passes those observed single-fixture checks (91.72%, 7/10); λ=0.05–0.15 fails the baseline-retention part. This is a candidate review threshold derived from this observed trade-off, not a future-listen hit-rate/nDCG guarantee or an approved rollout gate.

Limitations: one frozen 66-candidate pool, a 10-item output, and one captured baseline; captured discovery scores are not future user outcomes. The baseline relevance-score-retention metric is distinct from mean selected raw-score retention versus setting 0. Identity-bearing rows and the raw report remain local/private and are not committed.
### 2. Correct relevance normalization and prove pool stability

The prior min-max relevance normalization depended on score magnitude and could let one high-scoring outlier compress other scores. The first implementation now uses descending average ranks normalized to [0, 1]: equal scores receive equal relevance, a one-item pool receives relevance 1, and constant-score pools remain deterministic. This makes the lambda scale independent of raw score gaps, though rank changes caused by a genuinely different candidate pool can still change relevance. Cross-pool tests are required before treating the setting as calibrated.

Add deterministic tests that apply the same setting to at least two deliberately different candidate pools and verify the intended cross-pool behavior. Document what “the same setting means” operationally; do not claim perfect invariance where the underlying candidate distributions genuinely differ.

### 3. Remove the missing-tag diversity advantage

PR #340 merged the conservative policy: exact same-artist identity is authoritative; when either candidate lacks tags, similarity is treated conservatively as 1.0 so missing metadata does not earn a novelty bonus. Synthetic regression tests cover missing-tag neutrality and known disjoint tags. The frozen fixture selected no untagged candidates, so its aggregate result does not exercise this edge case beyond the synthetic tests.

Add regression tests for one or both candidates missing tags, both candidates missing tags, and genuinely dissimilar known-tag pairs. Track the share/count of selected or promoted untagged albums in evaluator output so the effect is visible. Preserve graceful behavior for sparse metadata.

Precompute each candidate's normalized tag set as a `frozenset` once per rerank/allocator operation rather than rebuilding sets inside every pairwise `tag_jaccard` call. Keep this optimization scoped and covered by equivalence tests.

### 4. Add final-shortlist quality and category guardrails

**Evaluator metrics and captured-category lookup merged in PR #341 and PR #345.** PR #345 fixed a schema mismatch: captured debug candidate rows store `assigned_category`, while the evaluator previously recognized only `discovery_category` and `category`, silently returning `unknown` for shortlist category metrics. The identity-free run below uses the existing frozen fixture after that fix. The evaluator reports per-shortlist category counts/shares, unique normalized tag coverage, selected untagged count/share, untagged promotions versus score-ordered top-k, baseline top-k retention, and mean raw-score retention against lambda 0 at the same relevance floor.

MMR runs inside allocator passes (adjacent, cross-genre, adventurous), so lower pairwise similarity alone does not prove that the final shortlist has a healthier overall mix. The evaluator's lambda-zero result is the within-pool reference; compare settings only when candidate inputs, eligibility rules, requested shortlist size, and relevance floor are identical.

**Provisional rollout gate applied with owner approval for this evaluation (not an approval to expose the UI):**
1. **Relevance:** mean selected raw discovery score must be at least 90% of the lambda-zero result, using the same pool and floor. This is a relative ranking-score guardrail, not a future-listen quality metric.
2. **Baseline continuity:** retain at least 7 of the baseline top 10 items for a 10-item baseline. For other baseline sizes, require at least 70% retention, rounded up; report both count and fraction so small baselines cannot hide a large regression.
3. **Category mix:** no category that represented at least two baseline items may disappear from the shortlist; no category share may rise by more than 10 percentage points versus lambda zero. Compare category counts and shares, not just a global similarity score. These are regression guardrails, not instructions to alter existing allocator quotas.
4. **Coverage and missing metadata:** report unique normalized tag coverage, selected untagged count/share, and untagged promotions beyond score-ranked top-k. Any unexplained increase in untagged promotion blocks approval for review; do not award a setting credit merely for reducing similarity.
5. **Safety and stability:** preserve requested shortlist length when the eligible pool can fill it, ownership/release eligibility, artist uniqueness, deterministic repeated output, and bounded work. Any violation blocks rollout regardless of aggregate scores.

**Evaluation result (existing private fixture only):** the capture checksum/schema validated. Fixture file SHA-256: `d74877fd8635cfbd390a66f338389a3c8d91aa27c10ad10cc11e78b10182eb21`; payload SHA-256: `5dc522d622ada3bbe3fc12a2bf674b05b1345c7a02b9d67bed20b62549368d8e`; captured source SHA: `d8c1f3de5180b35919f55c304d55e5c939dad373`. The run used 83 gathered albums, 1,733 library albums, 66 scored candidates, 17 rejected rows, and the captured 10-item baseline. It evaluated all 21 settings from 0 to 100 in increments of 5 with relevance floor fixed at 0, used zero network providers, replayed no provider tape, and emitted identity-free output only. Baseline categories were adjacent 4, adventurous 3, cross-genre 3; baseline tag coverage was 72 and baseline untagged count was zero.

| Settings | Mean pairwise similarity | Baseline retained | Mean raw-score retention vs 0 | Category mix | Gate |
|---|---:|---:|---:|---|---|
| 0–10 | 0.10440 | 7/10 | 100.00% | 40/30/30% | Pass |
| 15 | 0.06719 | 8/10 | 91.80% | 50/20/30% | Pass |
| 20–75 | 0.06275 | 7/10 | 91.79% | 50/20/30% | Pass |
| 80–85 | 0.04104 | 7/10 | 81.14% | 60/20/20% | Fail: score and category concentration |
| 90–95 | 0.03883 | 6/10 | 81.10% | 60/20/20% | Fail: score, baseline, and category concentration |
| 100 | 0.02753 | 6/10 | 72.17% | 60/20/20% | Fail: score, baseline, and category concentration |

All settings returned 10 eligible candidates with 10 unique artists, zero duplicate non-empty artist keys, deterministic repeated selections, and zero untagged selections/promotions. The category share increase is +10 percentage points at settings 15–75 (the proposed limit) and +20pp at 80–100. The provisional gate therefore passes per setting through 75 and fails at 80 and above on this fixture. The similarity reduction is about 40% at settings 20–75 and about 60% at setting 100 versus setting 0.

The 90% raw-score and 7/10 baseline-retention values remain provisional thresholds motivated by single-fixture evidence, not universal quality guarantees. This is not future-listen hit-rate/nDCG evidence or proof of cross-pool stability. Do not rerun the dismissed 35-combination/floor reproduction, collect a new live capture, or disclose candidate identities. Keep the Settings UI blocked until cross-pool behavior and a reviewed setting-to-penalty mapping are established; do not change allocator quotas merely to make metrics pass.

### 5. Backend implementation follow-up

The foundational implementation is merged: PR #338 added rank-based relevance normalization, PR #340 removed the missing-tag novelty advantage, PR #341 added final-shortlist quality/category metrics, and PR #345 fixed captured `assigned_category` lookup in the evaluator. Do not repeat those implementation tasks. The next backend priority is deterministic cross-pool tests using at least two materially different candidate pools, including score outliers, ties, sparse metadata, and different pool sizes. Define the operational interpretation of the same setting across pools and use those tests to choose/review a non-linear setting-to-penalty mapping consistent with the observed provisional cap at 0.75.

Preserve the current contract: setting 0 exactly bypasses MMR; ownership, release eligibility, artist cap, category policy, deterministic behavior, bounded work, API responses, and persistence remain unchanged. Update the stale `navidrome_server.py` comment that says “Phase 3 will add measured relevance/diversity re-ranking” only as part of a focused follow-up after the substantive cross-pool work is addressed.

### 6. Settings UI — only after gates 1–5

Coordinate a separate frontend PR under root `AGENTS.md`, `docs/FRONTEND_DESIGN_GUIDE.md`, and the permitted UI file boundaries. Do not combine the UI with backend correctness changes.

UI acceptance criteria:
- accessible label and keyboard-operable slider;
- visible selected value and calibrated endpoint descriptions;
- save/error feedback and persistence on reload;
- explain that changes apply on the next generation/refresh;
- either show a “last generated with diversity X” indicator or trigger a safe refresh when the setting changes, so users can tell which setting produced the displayed list;
- mobile layout and browser/manual verification using `docs/LOCAL_UI_TESTING.md`.

Avoid implying each one-point change must alter the list. Keep the control disabled or clearly marked unavailable until the mapping and guardrails are ready.

### 7. Bounded feedback and later expansion

After the single global setting has passed rollout gates, consider using existing Get/Skip/Dismiss actions as implicit feedback about recommendations generated at a given diversity setting. Treat actions as noisy signals, not definitive satisfaction labels. Store only bounded, privacy-preserving aggregates or pseudonymous hashes with explicit retention limits; never commit identity-bearing recommendation data or credentials. Define how feedback is attributed to the setting used for that generation.

Only after the global setting is validated should per-surface diversity (for example Discover versus library-depth lists) be considered. Do not multiply controls before there is evidence users need different behaviors per surface.

## Invariants and acceptance criteria

- Value 0 continues to preserve legacy ordering exactly.
- Ownership checks, release eligibility, compilation/remix/non-album filtering, category/style/family policy, artist cap, API/persistence contracts, and existing list behavior remain unchanged.
- Missing metadata never earns an unearned diversity bonus.
- The same setting has a documented, tested relevance/diversity interpretation across different pools.
- Determinism, sparse-pool safety, and bounded work remain mandatory.
- Evaluation reports relevance retention, similarity, genre coverage, category mix, untagged-candidate share, and baseline retention without exposing candidate identities.
- All four required GitHub workflows pass on the exact final PR-head SHA. UI changes additionally pass the documented manual browser checklist.
- Merge, image publication, deployment, and runtime verification remain separate states. Publishing/deployment require explicit authorization.

## Verification and provenance notes

The audit reported that a shallow clone could not establish the ancestry of `ef8173a4ce47b0b4b1ec72fc567377dbd0cf1dd0`. GitHub currently exposes that SHA as the PR #326 merge commit and records PR #326 as merged, but this documentation task has not independently checked a full commit ancestry chain or rerun its CI. Preserve that distinction; do not mark the audit item verified without direct evidence.

## Next action

PR #345 fixed the evaluator's `assigned_category` lookup and merged at `490afbaca5ed48cfbe8c78a6c5622cf9e6a0de04` from final CI-verified head `80f6fb881e0da32fa0088153eca374e3c21cf416`. All four required workflows passed on that exact head; the Docker packaging workflow ran 704 unit tests successfully. The owner-approved provisional rollout gate was then evaluated identity-free against the existing private fixture at relevance floor 0: settings 0–75 pass the per-setting thresholds, settings 80–100 fail. This remains one frozen pool, not cross-pool or future-listen quality evidence. Next action: add deterministic cross-pool rank-normalization tests and review a setting-to-penalty mapping; keep the Settings UI blocked. Do not rerun the dismissed 35-combination/floor reproduction, collect a new live capture, publish fixture identities, implement the UI, publish an image, or deploy.
