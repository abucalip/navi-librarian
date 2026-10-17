# Recommendation diversity setting roadmap

**Status:** Proposal only; not implemented. No publishing or deployment is authorized by this document.

## Goal and slider copy

Call the setting **Recommendation diversity**, not MMR: MMR is an implementation detail. Use a 0–100 slider with plain-language endpoint copy:

- **Lower — More familiar:** “Prioritize close matches to your taste and the strongest individual recommendations. The list may contain more similar-sounding albums.”
- **Higher — More exploratory:** “Favor variety across artists and styles while keeping recommendations relevant to your taste. Some picks may be less familiar, but should still be good matches.”

Explain that this changes the balance of relevance and variety, not the user's profile or library. A one-point movement need not change every list.

## Evidence and limits

**Owner-fixture calibration review (2026-10-17):** the existing private capture has 83 gathered candidate albums, 1,733 library albums, 66 scored/rankable candidates, 10 baseline recommendations, and 10/10 baseline recommendations with captured scores. The 7 × 5 sweep covered lambda values 0, 0.25, 0.5, 0.65, 0.75, 0.85, 1 and relevance floors 0, 0.05, 0.1, 0.15, 0.2. At floors 0 and 0.05, all lambda settings returned 10 recommendations and retained 7/10 baseline items (70%). Mean pairwise similarity ranged from 0.1044 at lambda 0 to 0.0591 at lambda 0.75/0.85/1; baseline relevance-score retention was 85.5% at lambda ≥0.25. Lambda 0.75 reduced similarity about 41% versus lambda 0.25, with mean selected raw score about 8.2% lower. Lambda 1.0 did not improve on 0.75.

A floor of 0.05 changed nothing. Floors 0.1, 0.15 and 0.2 each returned only 7 recommendations, retained 4/10 baseline items (40%), retained 70.3% of baseline relevance score, and raised mean pairwise similarity to about 0.216. **Do not select a nonzero relevance floor from this evidence.** Keep floor 0 and production ranking unchanged. This is one frozen capture, not future-listen hit-rate/nDCG or evidence of broad user satisfaction. Keep the fixture and candidate identities private; do not collect another live capture. The known strict replay mismatch is cross-revision provider/cache call order, not an MMR quality result.

**Verification limitation:** the fixture was retrieved from the owner's private repository and the evaluator/reranking logic was reproduced in JavaScript from the inspected merged Python source. The Python CLI itself was not executed in a Python runtime during this session; these metrics are not a verified Python CLI run. In this implementation, mmr_rerank subtracts lambda × similarity, so a larger lambda means more diversity. Treat lambda 0.75 as a calibration candidate only, not a production default. Preserve current ranking until the actual CLI result and backend preference/integration gates are verified.

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
