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

### 1. Offline slider calibration — next action, before UI

Use the existing evaluator and existing frozen fixture only. Run an identity-free lambda sweep over the full candidate slider range (0–100, step 5 or 10) and record the mapping, relevance-retention, and similarity curves. Do not capture live data, replay providers, commit fixture identities, or reopen the dismissed 35-combination result.

Use the curve to:
- choose a mapping that gives useful control where results actually change;
- cap or compress the slider's upper end when benefit plateaus (the current evidence shows no measured gain from lambda 0.75 to 1.0);
- identify flat regions where a linear slider would imply a false sense of precision;
- document the limitations of this single fixture rather than presenting it as general quality proof.

Do not set a numeric relevance threshold by intuition. Propose a minimum relevance-retention guardrail from the observed baseline and have it explicitly reviewed before UI copy or rollout is approved.

### 2. Correct relevance normalization and prove pool stability

The current min-max relevance normalization depends on the candidate pool: one high-scoring outlier can compress other scores, changing the effective relevance/diversity trade-off for the same lambda. Evaluate and adopt rank-based relevance normalization (preferred initial option) or a clipped z-score alternative with defined behavior for ties, small pools, and constant scores.

Add deterministic tests that apply the same setting to at least two deliberately different candidate pools and verify the intended cross-pool behavior. Document what “the same setting means” operationally; do not claim perfect invariance where the underlying candidate distributions genuinely differ.

### 3. Remove the missing-tag diversity advantage

Currently, `candidate_similarity` returns 0 when either album lacks genre tags. That treats unknown metadata as maximum novelty and can unfairly promote untagged candidates. Replace this with a neutral prior or exclude unknown-tag pairs from the diversity penalty, choosing a policy that does not award a diversity bonus merely for missing tags.

Add regression tests for one or both candidates missing tags, both candidates missing tags, and genuinely dissimilar known-tag pairs. Track the share/count of selected or promoted untagged albums in evaluator output so the effect is visible. Preserve graceful behavior for sparse metadata.

Precompute each candidate's normalized tag set as a `frozenset` once per rerank/allocator operation rather than rebuilding sets inside every pairwise `tag_jaccard` call. Keep this optimization scoped and covered by equivalence tests.

### 4. Add final-shortlist quality and category guardrails

MMR is applied inside allocator passes (adjacent, cross-genre, adventurous), so lower pairwise similarity within a pass does not prove that the final shortlist has a healthier overall mix. Extend the offline evaluator to report:
- relevance-score retention against lambda 0;
- final-shortlist genre/tag coverage;
- category counts/mix compared with the baseline and existing allocator policy;
- mean pairwise similarity;
- selected/promoted untagged-candidate share;
- baseline top-k retention and selected count/eligibility.

Define a rollout gate with a reviewed minimum relevance-retention threshold and a category-mix check that prevents diversity settings from unexpectedly collapsing or over-concentrating the shortlist. Do not change existing hard category quotas or allocator behavior merely to make a metric look better. A lower similarity score alone is not success.

### 5. Backend implementation follow-up

After calibration design is agreed, implement rank-based (or approved alternative) normalization, missing-tag neutrality, precomputed tag sets, evaluator metrics, and regression tests in focused PR(s). Inspect all callers and preserve the current contract: setting 0 exactly bypasses MMR; ownership, release eligibility, artist cap, category policy, deterministic behavior, bounded work, API responses, and persistence remain unchanged.

Update the stale `navidrome_server.py` comment that says “Phase 3 will add measured relevance/diversity re-ranking” once the new behavior is actually implemented and verified. Do not make the comment-only correction a substitute for fixing the substantive issues.

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

Run the identity-free 0–100 lambda sweep, step 5 or 10, against the **existing private frozen fixture only**, then document the curves and propose the slider mapping/cap and relevance-retention gate. Do not run the dismissed 35-combination reproduction, collect a new live capture, publish fixture identities, implement the UI, publish an image, or deploy.
