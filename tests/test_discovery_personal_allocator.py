import unittest

from discovery.allocation_contract import (
    AllocationCandidate, AllocationRequest, OwnershipStatus,
)
from discovery.personal_allocator import allocate_personal_recommendations


def item(cid, artist=None, album=None, category="adjacent", score=1.0,
         style="other", family=None, ownership=OwnershipStatus.CLEAR, tags=(),
         genre=None):
    return AllocationCandidate(
        candidate_id=cid, artist_key=artist or cid, album_key=album or cid,
        category=category, score=score, diversity_style=style,
        recent_profile_family=family, ownership=ownership, tags=tags,
        genre_family=genre,
    )


def request(items, count=3, targets=None, styles=None, max_checks=60, diversity_penalty=0.0):
    return AllocationRequest(
        candidates=tuple(items), count=count,
        category_targets=targets or {"adjacent": 1, "cross_genre": 1, "adventurous": 1},
        diversity_style_targets=styles or {}, max_checks=max_checks,
        diversity_penalty=diversity_penalty,
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

    def test_mmr_penalty_changes_candidate_choice_inside_category_allocation(self):
        candidates = [
            item("anchor", artist="a", category="adjacent", score=10.0, tags=("jazz", "soul")),
            item("similar", artist="b", category="adjacent", score=9.8, tags=("jazz", "soul")),
            item("different", artist="c", category="adjacent", score=9.7, tags=("funk", "afrobeat")),
        ]
        legacy = allocate_personal_recommendations(request(
            candidates, count=3,
            targets={"adjacent": 3, "cross_genre": 0, "adventurous": 0},
        ))
        diverse = allocate_personal_recommendations(request(
            candidates, count=3,
            targets={"adjacent": 3, "cross_genre": 0, "adventurous": 0},
            diversity_penalty=0.5,
        ))
        self.assertEqual(legacy.selected_candidate_ids, ("anchor", "similar", "different"))
        self.assertEqual(diverse.selected_candidate_ids, ("anchor", "different", "similar"))
        self.assertEqual(dict(diverse.category_counts)["adjacent"], 3)

    def test_mmr_keeps_hard_ownership_gate_and_artist_cap(self):
        candidates = [
            item("owned", artist="owned-artist", category="adjacent", score=10.0,
                 tags=("jazz",), ownership=OwnershipStatus.EXACT_OWNED),
            item("anchor", artist="a", category="adjacent", score=9.9, tags=("jazz", "soul")),
            item("similar", artist="b", category="adjacent", score=9.8, tags=("jazz", "soul")),
            item("different", artist="c", category="adjacent", score=9.7, tags=("funk", "afrobeat")),
            item("same-artist-alt", artist="a", category="adjacent", score=9.6, tags=("funk",)),
        ]
        result = allocate_personal_recommendations(request(
            candidates, count=3,
            targets={"adjacent": 3, "cross_genre": 0, "adventurous": 0},
            diversity_penalty=0.5,
        ))
        self.assertEqual(result.selected_candidate_ids, ("anchor", "different", "similar"))
        self.assertNotIn("owned", result.selected_candidate_ids)
        self.assertNotIn("same-artist-alt", result.selected_candidate_ids)
        self.assertEqual(result.checked_count, 4)

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

    def test_duplicate_identity_takes_precedence_over_family_cap_diagnostic(self):
        result = allocate_personal_recommendations(request([
            item("selected-jazz", artist="artist-a", album="same",
                 category="adjacent", score=10, family="jazz"),
            item("duplicate-jazz", artist="artist-a", album="same",
                 category="cross_genre", score=8, family="jazz"),
            item("other-family", artist="artist-b", album="other",
                 category="cross_genre", score=7, family="jazz"),
            item("adventure", artist="artist-c", album="adventure",
                 category="adventurous", score=6, family="ambient"),
        ], count=3, targets={
            "adjacent": 1, "cross_genre": 1, "adventurous": 1,
        }))
        statuses = {decision.candidate_id: decision.status for decision in result.decisions}
        self.assertEqual(
            result.selected_candidate_ids,
            ("selected-jazz", "adventure", "other-family"),
        )
        self.assertEqual(statuses["duplicate-jazz"], "duplicate_candidate")
        self.assertNotEqual(statuses["duplicate-jazz"], "recent_genre_cap_reached")

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

    def test_sparse_categories_and_family_cap_fallback_fill_requested_count(self):
        candidates = []
        # Match the observed 19-candidate category shape: 8 adjacent, 6
        # cross-genre, and 5 unclassified candidates, with no adventurous pool.
        categories = (
            ["adjacent"] * 8
            + ["cross_genre"] * 6
            + ["unclassified"] * 5
        )
        for index, category in enumerate(categories):
            ownership = (
                OwnershipStatus.EXACT_OWNED if index < 4
                else OwnershipStatus.CLEAR
            )
            family = "jazz" if 4 <= index < 14 else None
            candidates.append(item(
                f"candidate-{index}",
                artist=f"artist-{index}",
                album=f"album-{index}",
                category=category,
                score=100 - index,
                family=family,
                ownership=ownership,
            ))

        result = allocate_personal_recommendations(request(
            candidates,
            count=10,
            targets={"adjacent": 4, "cross_genre": 3, "adventurous": 3},
        ))

        self.assertEqual(len(result.selected_candidate_ids), 10)
        self.assertEqual(len(set(result.selected_candidate_ids)), 10)
        self.assertFalse(set(result.selected_candidate_ids) & {
            candidate.candidate_id for candidate in candidates
            if candidate.ownership is not OwnershipStatus.CLEAR
        })
        self.assertLessEqual(result.checked_count, 60)
        self.assertEqual(result.phase_diagnostics["final_fallback_entered"], 0)
        self.assertGreater(result.phase_diagnostics["unclassified_fallback_attempts"], 0)
        self.assertEqual(result.phase_diagnostics["final_fallback_attempts"], 0)

    # The phase counters must explain why a shortlist can stop below its target.
    def test_final_fallback_phase_is_reported_when_category_and_family_caps_block_fill(self):
        candidates = [
            item("selected-a", artist="artist-a", category="adjacent", score=10),
            item("selected-x", artist="artist-x", category="cross_genre", score=9),
            item("family-a", artist="artist-b", category="adjacent", score=8, family="jazz"),
            item("family-x", artist="artist-c", category="cross_genre", score=7, family="rock"),
            item("family-u", artist="artist-d", category="unclassified", score=6, family="jazz"),
        ]
        result = allocate_personal_recommendations(request(
            candidates, count=4,
            targets={"adjacent": 1, "cross_genre": 1, "adventurous": 2},
        ))
        self.assertEqual(result.phase_diagnostics["final_fallback_entered"], 1)
        self.assertGreater(result.phase_diagnostics["final_fallback_attempts"], 0)
        self.assertLessEqual(result.checked_count, 60)

    def test_check_budget_is_bounded(self):
        items = [item(f"a{i}", category="adjacent", score=100-i) for i in range(60)]
        items += [item("cross", category="cross_genre"), item("adventure", category="adventurous")]
        result = allocate_personal_recommendations(request(
            items, count=10, targets={"adjacent": 10, "cross_genre": 0, "adventurous": 0},
            max_checks=3,
        ))
        self.assertLessEqual(result.checked_count, 3)
        self.assertEqual(len(result.selected_candidate_ids), 3)


def coverage_request(items, count=6, cap=2, floors=None, target=None, ratio=0.4,
                     unknown_cap=1, max_checks=60):
    return AllocationRequest(
        candidates=tuple(items), count=count, category_targets={},
        diversity_style_targets={}, max_checks=max_checks, genre_family_cap=cap,
        unknown_family_cap=unknown_cap, category_floors=floors or {},
        coverage_target=count if target is None else target,
        coverage_floor_ratio=ratio,
    )


class FamilyCoveragePolicyTests(unittest.TestCase):
    def test_genre_family_cap_limits_each_family_and_unknown_bucket(self):
        items = [item(f"r{i}", score=10 - i, genre="rock") for i in range(5)]
        items += [item(f"u{i}", score=4 - i * 0.1) for i in range(3)]
        items += [item("j", score=1.0, genre="jazz")]
        result = allocate_personal_recommendations(coverage_request(items, count=4, target=0))
        self.assertEqual(result.selected_candidate_ids, ("r0", "r1", "u0", "j"))
        decisions = {d.candidate_id: d.status for d in result.decisions}
        self.assertEqual(decisions["r2"], "genre_family_cap_reached")
        self.assertEqual(decisions["u1"], "genre_family_cap_reached")

    def test_coverage_adds_new_families_above_the_relevance_floor(self):
        items = [item(f"r{i}", score=10 - i * 0.1, genre="rock") for i in range(4)]
        items += [item("metal", score=9.0, genre="metal"),
                  item("jazz", score=5.0, genre="jazz"),
                  item("tiny", score=3.0, genre="polka")]
        result = allocate_personal_recommendations(coverage_request(
            items, count=4, cap=2, target=4, ratio=0.4,
        ))
        # r0, then the best of each unseen family above 0.4 * top score (4.0).
        self.assertEqual(result.selected_candidate_ids, ("r0", "metal", "jazz", "r1"))
        self.assertEqual(result.phase_diagnostics["family_coverage_attempts"], 3)

    def test_wider_supply_adds_a_family_only_when_it_clears_the_floor(self):
        base = [item(f"r{i}", score=10 - i * 0.1, genre="rock") for i in range(6)]
        base += [item("m", score=8.0, genre="metal")]
        wider = base + [item("late", score=6.0, genre="reggae")]
        narrow = allocate_personal_recommendations(coverage_request(base, count=3, cap=1))
        broad = allocate_personal_recommendations(coverage_request(wider, count=3, cap=1))
        self.assertNotIn("late", narrow.selected_candidate_ids)
        self.assertIn("late", broad.selected_candidate_ids)

    def test_category_floor_reserves_exploration_without_a_quota(self):
        items = [item(f"r{i}", score=10 - i, genre=f"g{i}") for i in range(5)]
        items += [item("adv", category="adventurous", score=1.0, genre="polka")]
        floored = allocate_personal_recommendations(coverage_request(
            items, count=3, floors={"adventurous": 1}, target=0,
        ))
        plain = allocate_personal_recommendations(coverage_request(items, count=3, target=0))
        self.assertIn("adv", floored.selected_candidate_ids)
        self.assertNotIn("adv", plain.selected_candidate_ids)
        self.assertEqual(dict(floored.category_counts).get("adventurous"), 1)

    def test_owned_candidates_do_not_use_the_check_budget(self):
        owned = [item(f"o{i}", score=100 - i, genre="rock", ownership=OwnershipStatus.EXACT_OWNED)
                 for i in range(20)]
        clear = [item(f"c{i}", score=10 - i, genre=f"g{i}") for i in range(3)]
        result = allocate_personal_recommendations(coverage_request(
            owned + clear, count=3, max_checks=3,
        ))
        self.assertEqual(result.selected_candidate_ids, ("c0", "c1", "c2"))
        self.assertEqual(result.checked_count, 3)
        statuses = {d.candidate_id: d.status for d in result.decisions}
        self.assertEqual(statuses["o0"], "already_owned")

    def test_one_album_per_artist_and_final_fallback_fills_short_lists(self):
        items = [item("a1", artist="a", score=5, genre="rock"),
                 item("a2", artist="a", score=4, genre="rock"),
                 item("b", artist="b", score=3, genre="rock"),
                 item("c", artist="c", score=2, genre="rock")]
        result = allocate_personal_recommendations(coverage_request(items, count=3, cap=1))
        # Cap 1 would stop at one rock album; the relaxed fallback fills to count.
        self.assertEqual(result.selected_candidate_ids, ("a1", "b", "c"))
        self.assertEqual(result.phase_diagnostics["final_fallback_entered"], 1)

    def test_legacy_policy_is_unchanged_when_no_genre_cap_is_set(self):
        items = [item("x", score=3, genre="rock"), item("y", score=2, genre="rock")]
        result = allocate_personal_recommendations(request(
            items, count=2, targets={"adjacent": 2},
        ))
        self.assertEqual(result.selected_candidate_ids, ("x", "y"))
        self.assertNotIn("family_coverage_attempts", result.phase_diagnostics)

    def test_contract_rejects_invalid_coverage_settings(self):
        for kwargs in ({"cap": 0}, {"ratio": 1.5}, {"target": 99}, {"floors": {"bogus": 1}}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                coverage_request([item("x")], count=3, **kwargs)


if __name__ == "__main__":
    unittest.main()
