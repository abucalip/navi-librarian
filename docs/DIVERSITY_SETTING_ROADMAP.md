# Recommendation diversity setting roadmap

**Status:** Proposal only; not implemented. No publishing or deployment is authorized by this document.

## Goal and slider copy

Call the setting **Recommendation diversity**, not MMR: MMR is an implementation detail. Use a 0–100 slider with plain-language endpoint copy:

- **Lower — More familiar:** “Prioritize close matches to your taste and the strongest individual recommendations. The list may contain more similar-sounding albums.”
- **Higher — More exploratory:** “Favor variety across artists and styles while keeping recommendations relevant to your taste. Some picks may be less familiar, but should still be good matches.”

Explain that this changes the balance of relevance and variety, not the user's profile or library. A one-point movement need not change every list.

## Evidence and limits

The provider-free evaluator merged in PR #320. On one private frozen pool (66 scored candidates, 10 expected recommendations), lambda 0.75 retained 7/10 baseline items and about 85.5% of baseline relevance score while reducing mean pairwise similarity about 43% versus lambda 0 (0.0591 versus 0.1044). Results were deterministic, with 10 unique artists at each tested lambda; lambda 1.0 showed no additional reported benefit.

This single comparison does not establish future-listen hit-rate/nDCG, broad satisfaction, or an optimal default. Keep the owner's fixture and identities private. Do not collect another live capture to advance this work. The known strict replay mismatch concerns cross-revision provider/cache call order, not MMR quality.

Treat lambda 0.75 as a calibration candidate, not a committed default. Higher user-facing diversity must map to a lower conventional MMR lambda. Implement that inverse mapping explicitly in one pure, tested helper. Preserve current ranking by default until calibration and rollout are approved.

## Implementation sequence

1. **Offline calibration:** compare baseline with a bounded lambda grid around 0.75. Measure baseline-item and relevance retention, pairwise similarity, artist uniqueness/cap, eligibility/ownership invariants, determinism, and shortlist completion. Test sparse pools, missing tags, ties, and heavy eligibility filtering. Frozen-pool metrics are not future-listen hit-rate/nDCG. Gate: choose the mapping and relevance floor from evidence or defer integration.
2. **Backend preference:** add a validated, bounded per-user setting with a default preserving current behavior. Follow existing persistence conventions and handle invalid values safely. Apply changes on the next explicit recommendation refresh; opening Settings must not mutate the list. Preserve API shapes, profile, library, ownership, acquisition, and eligibility.
3. **Safe MMR integration:** diversity is a soft preference after hard ownership/eligibility checks. Preserve stable artist identity, one album per artist, category behavior, deterministic ties, bounded work, and sparse-pool safety. Do not merely reorder an already-finalized shortlist. Keep allocation policy and MMR independently testable; prefer fewer valid results to weak or ineligible matches.
4. **Settings UI:** follow root `AGENTS.md`, `docs/FRONTEND_DESIGN_GUIDE.md`, and permitted files in `AGENTS.md`. Frontend agents edit only approved UI files, scoped UI tests/fixtures, and `docs/UI_BACKLOG_EXECUTION.md`; backend/API/architecture/release changes require coordinated ownership. Show endpoint copy, accessible label, visible value, keyboard support, save/error feedback, and explain that changes take effect on next refresh. Test mobile layout and persistence.
5. **Rollout:** keep ranking unchanged until calibration, backend contract, integration tests, and UI checks pass. After authorized rollout, evaluate feedback and bounded metrics; lower similarity alone does not prove better recommendations. Publishing remains paused unless explicitly authorized.

## Invariants and acceptance criteria

- Ownership, release eligibility, compilation/remix/non-album filtering, API contracts, and persisted-list behavior remain unchanged.
- Determinism and bounded work are required. Missing tags degrade gracefully; absent metadata is not evidence of similarity. Invalid settings use the documented default.
- Tests cover mapping direction, persistence, ownership, eligibility, artist cap, deterministic ties, sparse pools, and API compatibility.
- All four required workflows pass on the exact final PR-head SHA. UI changes also pass the manual browser checklist. Merge does not imply publishing, deployment, or runtime verification.

## Next action

Calibrate the diversity-to-lambda mapping and relevance floor offline around lambda 0.75. Then prepare a focused backend preference-contract/integration PR; keep the slider UI in a separate coordinated PR after API semantics are fixed.
