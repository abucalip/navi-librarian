import unittest

from discovery_allocation_contract import (
    AllocationCandidate, AllocationRequest, OwnershipStatus,
)
from discovery_personal_allocator import allocate_personal_recommendations


def item(cid, artist=None, album=None, category="adjacent", score=1.0,
         style="other", family=None, ownership=OwnershipStatus.CLEAR):
    return AllocationCandidate(
        candidate_id=cid, artist_key=artist or cid, album_key=album or cid,
        category=category, score=score, diversity_style=style,
        recent_profile_family=family, ownership=ownership,
    )


def request(items, count=3, targets=None, styles=None, max_checks=60):
    return AllocationRequest(
        candidates=tuple(items), count=count,
        category_targets=targets or {"adjacent": 1, "cross_genre": 1, "adventurous": 1},
        diversity_style_targets=styles or {}, max_checks=max_checks,
    )


class PersonalAllocatorTests(unittest.TestCase):
    def test_category_quotas_and_score_order_are_respected(self):
        result = allocate_personal_recommendations(request([
            item("a-low", category="adjacent", score=1),
            item("a-high", category="adjacent", score=3),
            item("x", category="cross_genre", score=2),
            item("z", category="adventurous", score=1),
        ]))
        self.assertEqual(result.selected_candidate_ids, ("a-high", "x", "z"))
        self.assertEqual(dict(result.category_counts), {
            "adjacent": 1, "cross_genre": 1, "adventurous": 1,
        })

    def test_diversity_style_reservation_precedes_category_fill(self):
        result = allocate_personal_recommendations(request([
            item("ordinary", category="adjacent", score=10),
            item("regional", category="adventurous", score=1, style="north_african"),
            item("bridge", category="cross_genre", score=5),
        ], count=2, targets={"adjacent": 1, "cross_genre": 0, "adventurous": 1},
           styles={"north_african": 1}))
        self.assertEqual(result.selected_candidate_ids, ("regional", "ordinary"))

    def test_duplicate_identity_and_artist_cap_are_applied(self):
        result = allocate_personal_recommendations(request([
            item("first", artist="same", album="one", category="adjacent", score=5),
            item("duplicate", artist="same", album="one", category="adjacent", score=4),
            item("second-album", artist="same", album="two", category="adjacent", score=3),
            item("other", artist="other", album="other", category="cross_genre"),
            item("last", category="adventurous"),
            item("fallback", category="unclassified", score=0.5),
        ], count=5))
        self.assertEqual(
            result.selected_candidate_ids, ("first", "other", "last", "fallback")
        )
        statuses = {decision.candidate_id: decision.status for decision in result.decisions}
        self.assertEqual(statuses["duplicate"], "duplicate_candidate")
        self.assertEqual(statuses["second-album"], "artist_already_selected")

    def test_owned_candidates_are_rejected_and_title_conflicts_go_to_review(self):
        result = allocate_personal_recommendations(request([
            item("owned", category="adjacent", ownership=OwnershipStatus.EXACT_OWNED),
            item("review", category="adjacent", ownership=OwnershipStatus.TITLE_CONFLICT),
            item("cross", category="cross_genre"),
            item("adventure", category="adventurous"),
        ]))
        self.assertEqual(result.ownership_review_candidate_ids, ("review",))
        self.assertNotIn("owned", result.selected_candidate_ids)
        self.assertEqual(result.checked_count, 4)

    def test_family_cap_is_relaxed_before_fallback(self):
        result = allocate_personal_recommendations(request([
            item("jazz-a", category="adjacent", family="jazz", score=5),
            item("jazz-b", category="adjacent", family="jazz", score=4),
            item("rock", category="cross_genre", family="rock", score=3),
            item("adventure", category="adventurous", family="ambient", score=2),
        ], count=3, targets={"adjacent": 2, "cross_genre": 1, "adventurous": 0}))
        self.assertEqual(result.selected_candidate_ids, ("jazz-a", "rock", "jazz-b"))

    def test_unclassified_candidates_are_used_before_final_cross_category_fallback(self):
        result = allocate_personal_recommendations(request([
            item("adj", category="adjacent", score=5),
            item("unknown", category="unclassified", score=2),
            item("cross", category="cross_genre", score=4),
        ], count=3, targets={"adjacent": 2, "cross_genre": 2, "adventurous": 0}))
        self.assertEqual(result.selected_candidate_ids, ("adj", "cross", "unknown"))


    def test_final_fallback_preserves_legacy_category_tie_order(self):
        result = allocate_personal_recommendations(request([
            item("cross-first", category="cross_genre", score=1),
            item("adjacent-second", category="adjacent", score=1),
            item("adventurous-third", category="adventurous", score=1),
        ], count=2, targets={
            "adjacent": 0, "cross_genre": 0, "adventurous": 0,
        }))
        self.assertEqual(
            result.selected_candidate_ids, ("adjacent-second", "cross-first")
        )

    def test_check_budget_is_bounded(self):
        items = [item(f"a{i}", category="adjacent", score=100-i) for i in range(60)]
        items += [item("cross", category="cross_genre"), item("adventure", category="adventurous")]
        result = allocate_personal_recommendations(request(
            items, count=10, targets={"adjacent": 10, "cross_genre": 0, "adventurous": 0},
            max_checks=3,
        ))
        self.assertLessEqual(result.checked_count, 3)
        self.assertEqual(len(result.selected_candidate_ids), 3)


if __name__ == "__main__":
    unittest.main()
