import unittest

from discovery.allocation_contract import (
    AllocationCandidate, AllocationRequest, OwnershipStatus,
)
from discovery.lenses import (
    DEEP_CUTS, GENRE_SPREAD, NOW, partition_lenses, run_lens, select_deep_cuts,
)
from discovery.personal_allocator import allocate_personal_recommendations


def item(cid, artist=None, album=None, category="adjacent", score=1.0, genre=None,
         audience=None, seed=None, strength=0.0, tags=("a", "b"),
         ownership=OwnershipStatus.CLEAR):
    return AllocationCandidate(
        candidate_id=cid, artist_key=artist or cid, album_key=album or cid,
        category=category, score=score, genre_family=genre, audience=audience,
        seed=seed, tag_strength=strength, tags=tags, ownership=ownership,
    )


class LensContractTests(unittest.TestCase):
    def test_lens_defaults_to_now_and_is_carried_to_the_result(self):
        request = AllocationRequest((item("a"),), 1, {}, {})
        self.assertEqual(request.lens, "now")
        self.assertEqual(allocate_personal_recommendations(request).lens, "now")
        named = AllocationRequest((item("a"),), 1, {}, {}, lens="genre_spread")
        self.assertEqual(allocate_personal_recommendations(named).lens, "genre_spread")

    def test_blank_lens_and_bad_audience_are_rejected(self):
        with self.assertRaises(ValueError):
            AllocationRequest((), 1, {}, {}, lens=" ")
        with self.assertRaises(ValueError):
            item("a", audience=-1)


class DeepCutsTests(unittest.TestCase):
    def test_gates_and_decision_reasons(self):
        pool = [
            item("ok", audience=5000, strength=0.9),
            item("none"),
            item("low", audience=10),
            item("high", audience=900_000),
            item("thin", audience=5000, tags=("a",)),
            item("owned", audience=5000, ownership=OwnershipStatus.EXACT_OWNED),
            item("conflict", audience=5000, ownership=OwnershipStatus.TITLE_CONFLICT),
        ]
        result = select_deep_cuts(pool, 5)
        status = {d.candidate_id: d.status for d in result.decisions}
        self.assertEqual(result.selected_candidate_ids, ("ok",))
        self.assertEqual(result.lens, "deep_cuts")
        self.assertEqual(result.ownership_review_candidate_ids, ("conflict",))
        self.assertEqual(status["none"], "audience_unknown")
        self.assertEqual(status["low"], "audience_out_of_range")
        self.assertEqual(status["high"], "audience_out_of_range")
        self.assertEqual(status["thin"], "too_few_tags")
        self.assertEqual(status["owned"], "already_owned")

    def test_ranked_by_tag_strength_one_per_artist_and_seed_cap(self):
        pool = [
            item("a1", artist="a", audience=1000, seed="s", strength=0.9),
            item("a2", artist="a", audience=1000, seed="s", strength=0.8),
            item("b", audience=1000, seed="s", strength=0.7),
            item("c", audience=1000, seed="s", strength=0.6),
            item("d", audience=1000, seed="t", strength=0.5),
        ]
        result = select_deep_cuts(pool, 10)
        self.assertEqual(result.selected_candidate_ids, ("a1", "b", "d"))
        status = {d.candidate_id: d.status for d in result.decisions}
        self.assertEqual(status["a2"], "artist_already_selected")
        self.assertEqual(status["c"], "seed_cap_reached")

    def test_invalid_count_and_max_checks_are_rejected_before_work(self):
        for count in (0, 21, True):
            with self.assertRaises(ValueError):
                select_deep_cuts([], count)
        for checks in (0, 61):
            with self.assertRaises(ValueError):
                select_deep_cuts([], 3, max_checks=checks)
        with self.assertRaises(ValueError):
            run_lens(DEEP_CUTS, [], 0)

    def test_check_limit_bounds_examined_candidates(self):
        pool = [item(f"x{i}", audience=10, strength=1 - i / 100) for i in range(70)]
        pool.append(item("late", audience=1000, strength=0.0))
        result = select_deep_cuts(pool, 5)
        self.assertEqual(result.checked_count, 60)
        self.assertEqual(result.selected_candidate_ids, ())
        status = {d.candidate_id: d.status for d in result.decisions}
        self.assertEqual(status["late"], "not_considered")
        limited = run_lens(DEEP_CUTS, [item(f"y{i}", audience=1000) for i in range(5)], 5, max_checks=2)
        self.assertEqual((limited.checked_count, len(limited.selected_candidate_ids)), (2, 2))

    def test_duplicate_candidate_ids_rejected(self):
        with self.assertRaises(ValueError):
            select_deep_cuts([item("a"), item("a")], 1)

    def test_count_bound(self):
        pool = [item(f"x{i}", audience=1000, strength=1 - i / 10) for i in range(5)]
        self.assertEqual(len(select_deep_cuts(pool, 3).selected_candidate_ids), 3)


class PartitionTests(unittest.TestCase):
    def pool(self):
        deep = [item(f"d{i}", score=0.035, audience=2000, seed=f"s{i}", strength=1 - i / 10,
                     category="adventurous") for i in range(4)]
        main = [item(f"m{i}", score=5 - i * 0.1, genre=("rock", "jazz", "soul")[i % 3],
                     category=("adjacent", "cross_genre", "adventurous")[i % 3])
                for i in range(12)]
        return deep + main

    def test_no_artist_or_candidate_appears_in_two_lists(self):
        results = partition_lenses(self.pool(), 3)
        self.assertEqual([r.lens for r in results], ["deep_cuts", "now", "genre_spread"])
        chosen = [cid for r in results for cid in r.selected_candidate_ids]
        self.assertEqual(len(chosen), len(set(chosen)))
        self.assertTrue(all(len(r.selected_candidate_ids) == 3 for r in results))

    def test_earlier_lens_takes_a_shared_candidate(self):
        pool = [item("only", score=9, audience=2000, strength=1, genre="rock")]
        for order in ((DEEP_CUTS, NOW), (NOW, DEEP_CUTS)):
            first, second = partition_lenses(pool, 1, order)
            self.assertEqual(first.selected_candidate_ids, ("only",))
            self.assertEqual(second.selected_candidate_ids, ())

    def test_same_album_title_under_other_artist_is_not_repeated(self):
        pool = [
            item("one", artist="a", album="shared", score=9, audience=2000, strength=1),
            item("two", artist="b", album="shared", score=8, audience=2000, strength=0.5, genre="rock"),
        ]
        first, second = partition_lenses(pool, 1, (DEEP_CUTS, NOW))
        self.assertEqual(first.selected_candidate_ids, ("one",))
        self.assertEqual(second.selected_candidate_ids, ())

    def test_duplicate_lens_names_rejected(self):
        with self.assertRaises(ValueError):
            partition_lenses([], 1, (NOW, NOW))

    def test_pool_is_not_mutated_and_results_name_their_lens(self):
        pool = tuple(self.pool())
        before = list(pool)
        self.assertEqual(run_lens(GENRE_SPREAD, pool, 3).lens, "genre_spread")
        self.assertEqual(run_lens(NOW, pool, 3).lens, "now")
        self.assertEqual(list(pool), before)


if __name__ == "__main__":
    unittest.main()
