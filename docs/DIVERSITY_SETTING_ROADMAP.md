# Recommendation diversity setting roadmap

**Status:** Proposal only; not implemented. No publishing or deployment is authorized by this document.

## Goal and slider copy

Call the setting **Recommendation diversity**, not MMR: MMR is an implementation detail. Use a 0–100 slider with plain-language endpoint copy:

- **Lower — More familiar:** “Prioritize close matches to your taste and the strongest individual recommendations. The list may contain more similar-sounding albums.”
- **Higher — More exploratory:** “Favor variety across artists and styles while keeping recommendations relevant to your taste. Some picks may be less familiar, but should still be good matches.”

Explain that this changes the balance of relevance and variety, not the user's profile or library. A one-point movement need not change every list.

## Evidence and limits

**Identity-free Python CLI run completed (2026-10-18):** the owner ran `recommendation_mmr_evaluate.py --identity-free` in the isolated environment using source revision `acb437f85d8d5c8ae2e6cdb5240457423e9b6e64` against the existing private fixture captured from source SHA `d8c1f3de5180b35919f55c304d55e5c939dad373`. Exit status was 0. The output reports 83 gathered albums, 1,733 library albums, 66 scored candidates, 17 candidate rows rejected for hard eligibility or missing score, 10 baseline recommendations with captured scores, zero network providers, and no provider-tape replay. No fixture or identity-bearing report was committed.

The actual CLI output contains six lambda results (0, 0.1, 0.25, 0.5, 0.75, 1.0), not a relevance-floor sweep. At lambda 0, mean pairwise similarity was 0.1044, 7/10 baseline items were retained, and baseline relevance-score retention was 85.6%. At lambda 0.25/0.5, similarity was 0.1007, 7/10 baseline items were retained, and relevance-score retention was 85.5%. At lambda 0.75/1.0, similarity was 0.0591, 7/10 baseline items were retained, and relevance-score retention was 85.5%; lambda 1.0 showed no additional measured benefit. Lambda 0.75 lowers mean pairwise similarity by about 43% versus lambda 0 and about 41% versus lambda 0.25. Every tested setting selected 10 eligible items with 10 unique artists, zero duplicate non-empty artist keys, and deterministic repeated results.

**Decision boundary:** this is one frozen-pool comparison, not future-listen hit-rate/nDCG or proof of broad satisfaction. The earlier 35-combination/floor-sweep reproduction is dismissed as a decision input; the actual CLI run did not report a floor dimension, and no further test will be run to reconcile it. Keep the relevance floor at its default of 0 and leave production ranking unchanged until the preference contract, integration tests, and rollout gates are complete. In this implementation, `mmr_rerank` subtracts lambda × similarity, so larger lambda means more diversity. Treat 0.75 as a candidate mapping point, not a production default. Do not collect another live capture or publish fixture identities.

## Implementation sequence

1. **Offline calibration:** the evaluator in PR #322 sweeps seven lambda values (0, 0.25, 0.5, 0.65, 0.75, 0.85, 1) against five normalized relevance floors (0, 0.05, 0.1, 0.15, 0.2). The owner-fixture sweep has been reviewed using a JavaScript reproduction of the inspected Python implementation, but the Python CLI still needs an actual isolated-runtime execution. The results do not support a nonzero floor: 0.05 is indistinguishable from 0, while floors ≥0.1 reduce the shortlist to seven and materially worsen baseline retention and pairwise similarity. Keep floor 0; do not promote lambda 0.75 to a production default yet. Test sparse pools, missing tags, ties, and heavy eligibility filtering in the automated suite. Frozen-pool metrics are not future-listen hit-rate/nDCG.
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

Run recommendation_mmr_evaluate.py with --identity-free against the existing owner-only frozen fixture in the isolated Python test environment and compare its output with the reviewed aggregates recorded here. Do not collect another live capture or commit fixture/report identities. Keep relevance floor at 0 and production ranking unchanged. After CLI verification, prepare a focused backend preference-contract/integration PR; keep the slider UI in a separate coordinated PR after API semantics are fixed.
