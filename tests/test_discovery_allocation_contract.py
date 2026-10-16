import unittest

from discovery_allocation_contract import (
    AllocationCandidate,
    AllocationRequest,
    AllocationResult,
    CandidateDecision,
    OwnershipStatus,
)


def candidate(candidate_id="c1", **overrides):
    values = {
        "candidate_id": candidate_id,
        "artist_key": "artist-a",
        "album_key": "album-a",
        "category": "adjacent",
        "score": 1.25,
        "diversity_style": "other",
        "recent_profile_family": "jazz",
        "ownership": OwnershipStatus.CLEAR,
    }
    values.update(overrides)
    return AllocationCandidate(**values)


class AllocationContractTests(unittest.TestCase):
    def test_candidate_carries_normalized_identity_and_precomputed_ownership(self):
        row = candidate(ownership=OwnershipStatus.TITLE_CONFLICT)
        self.assertEqual((row.artist_key, row.album_key), ("artist-a", "album-a"))
        self.assertIs(row.ownership, OwnershipStatus.TITLE_CONFLICT)
        self.assertEqual(row.category, "adjacent")

    def test_candidate_rejects_missing_identity_and_unknown_category(self):
        with self.assertRaisesRegex(ValueError, "artist_key"):
            candidate(artist_key=" ")
        with self.assertRaisesRegex(ValueError, "unsupported recommendation category"):
            candidate(category="unknown")

    def test_candidate_rejects_non_finite_scores_and_unclassified_ownership_values(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            candidate(score=float("nan"))
        with self.assertRaisesRegex(ValueError, "OwnershipStatus"):
            candidate(ownership="clear")

    def test_request_accepts_all_prepared_candidates_without_callbacks(self):
        request = AllocationRequest(
            candidates=(
                candidate("a", category="adjacent"),
                candidate("b", category="cross_genre"),
                candidate("c", category="unclassified"),
            ),
            count=10,
            category_targets={"adjacent": 4, "cross_genre": 3, "adventurous": 3},
            diversity_style_targets={"north_african": 1, "afrobeats": 1},
        )
        self.assertEqual(len(request.candidates), 3)
        self.assertEqual(request.count, 10)
        self.assertEqual(request.family_cap, 1)
        self.assertEqual(request.max_checks, 60)

    def test_request_freezes_policy_mappings_against_shared_mutation(self):
        targets = {"adjacent": 4, "cross_genre": 3, "adventurous": 3}
        styles = {"north_african": 1}
        request = AllocationRequest((candidate(),), 10, targets, styles)
        targets["adjacent"] = 0
        styles["north_african"] = 0
        self.assertEqual(request.category_targets["adjacent"], 4)
        self.assertEqual(request.diversity_style_targets["north_african"], 1)
        with self.assertRaises(TypeError):
            request.category_targets["adjacent"] = 0

    def test_request_rejects_duplicate_ids_and_non_tuple_candidates(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            AllocationRequest((candidate("same"), candidate("same", album_key="album-b")),
                              10, {"adjacent": 4}, {})
        with self.assertRaisesRegex(TypeError, "tuple"):
            AllocationRequest([candidate()], 10, {"adjacent": 4}, {})

    def test_request_validates_count_quota_and_check_cap(self):
        for count in (0, 21):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "count"):
                AllocationRequest((), count, {}, {})
        with self.assertRaisesRegex(ValueError, "unsupported category"):
            AllocationRequest((), 10, {"unclassified": 2}, {})
        with self.assertRaisesRegex(ValueError, "non-negative"):
            AllocationRequest((), 10, {"adjacent": -1}, {})
        with self.assertRaisesRegex(ValueError, "max_checks"):
            AllocationRequest((), 10, {}, {}, max_checks=61)

    def test_result_keeps_selected_and_manual_review_ids_separate(self):
        result = AllocationResult(
            requested_count=2,
            selected_candidate_ids=("c1",),
            ownership_review_candidate_ids=("c2",),
            decisions=(
                CandidateDecision("c1", "selected", "clear ownership"),
                CandidateDecision("c2", "held_for_ownership_review", "title conflict"),
            ),
            category_counts={"adjacent": 1},
            checked_count=2,
        )
        self.assertEqual(result.selected_candidate_ids, ("c1",))
        self.assertEqual(result.ownership_review_candidate_ids, ("c2",))
        self.assertEqual(result.checked_count, 2)

    def test_result_rejects_overlapping_or_duplicate_ids_and_overfilled_shortlist(self):
        base = {
            "requested_count": 1,
            "decisions": (),
            "category_counts": {},
            "checked_count": 0,
        }
        with self.assertRaisesRegex(ValueError, "disjoint"):
            AllocationResult(**base, selected_candidate_ids=("c1",),
                             ownership_review_candidate_ids=("c1",))
        with self.assertRaisesRegex(ValueError, "unique"):
            AllocationResult(**base, selected_candidate_ids=("c1", "c1"),
                             ownership_review_candidate_ids=())
        with self.assertRaisesRegex(ValueError, "exceed"):
            AllocationResult(**base, selected_candidate_ids=("c1", "c2"),
                             ownership_review_candidate_ids=())

    def test_result_freezes_diagnostics_and_bounds_check_count(self):
        counts = {"adjacent": 1}
        result = AllocationResult(1, ("c1",), (), (), counts, 1)
        counts["adjacent"] = 0
        self.assertEqual(result.category_counts["adjacent"], 1)
        with self.assertRaises(TypeError):
            result.category_counts["adjacent"] = 0
        with self.assertRaisesRegex(ValueError, "checked_count"):
            AllocationResult(1, (), (), (), {}, 61)

    def test_decision_requires_candidate_id_and_status(self):
        with self.assertRaisesRegex(ValueError, "candidate_id"):
            CandidateDecision("", "selected", "ok")
        with self.assertRaisesRegex(ValueError, "status"):
            CandidateDecision("c1", " ", "reason")


if __name__ == "__main__":
    unittest.main()
