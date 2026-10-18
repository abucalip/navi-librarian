import unittest

from discovery_mmr import (
    candidate_similarity,
    diversity_setting_to_penalty,
    diversity_metrics,
    mmr_rerank,
    tag_jaccard,
)


def candidate(name, artist, score, tags):
    return {"id": name, "artist_key": artist, "score": score, "tags": tags}


class DiscoveryMmrTests(unittest.TestCase):
    def test_tag_jaccard_is_case_insensitive_and_empty_safe(self):
        self.assertEqual(tag_jaccard(["Jazz", "Soul"], ["soul", "Funk"]), 1 / 3)
        self.assertEqual(tag_jaccard([], []), 0.0)

    def test_same_artist_similarity_precedes_tags(self):
        self.assertEqual(
            candidate_similarity(
                candidate("a", "same", 1, ["jazz"]),
                candidate("b", "SAME", 1, ["funk"]),
            ),
            1.0,
        )

    def test_missing_tags_do_not_earn_novelty_bonus(self):
        tagged = candidate("tagged", "a", 1, ["jazz"])
        untagged_left = candidate("untagged-left", "b", 1, [])
        untagged_right = candidate("untagged-right", "c", 1, [])
        partially_missing = candidate("partially-missing", "d", 1, ["jazz"])

        self.assertEqual(candidate_similarity(tagged, untagged_left), 1.0)
        self.assertEqual(candidate_similarity(untagged_left, tagged), 1.0)
        self.assertEqual(candidate_similarity(untagged_left, untagged_right), 1.0)
        self.assertEqual(candidate_similarity(partially_missing, untagged_left), 1.0)

    def test_genuinely_disjoint_tagged_candidates_remain_dissimilar(self):
        self.assertEqual(
            candidate_similarity(
                candidate("jazz", "a", 1, ["jazz", "bebop"]),
                candidate("afrobeat", "b", 1, ["afrobeat", "funk"]),
            ),
            0.0,
        )

    def test_mmr_does_not_promote_untagged_candidate_over_tagged_alternative(self):
        items = [
            candidate("anchor", "a", 10, ["jazz"]),
            candidate("untagged", "b", 9.8, []),
            candidate("dissimilar", "c", 9.7, ["afrobeat"]),
        ]
        result = mmr_rerank(items, limit=3, lambda_=0.6)
        self.assertEqual([item["id"] for item in result], ["anchor", "dissimilar", "untagged"])

    def test_lambda_zero_preserves_relevance_order_with_artist_cap(self):
        items = [
            candidate("first", "a", 10, ["jazz"]),
            candidate("same-artist", "a", 9, ["soul"]),
            candidate("second", "b", 8, ["jazz"]),
        ]
        self.assertEqual(
            [item["id"] for item in mmr_rerank(items, limit=3, lambda_=0)],
            ["first", "second"],
        )

    def test_mmr_prefers_less_similar_candidate_when_relevance_is_close(self):
        items = [
            candidate("anchor", "a", 10, ["jazz", "soul"]),
            candidate("similar", "b", 9.8, ["jazz", "soul"]),
            candidate("different", "c", 9.7, ["funk", "afrobeat"]),
        ]
        result = mmr_rerank(items, limit=3, lambda_=0.6)
        self.assertEqual([item["id"] for item in result], ["anchor", "different", "similar"])

    def test_ties_are_deterministic_and_input_is_not_mutated(self):
        items = [
            candidate("first", "a", 4, ["jazz"]),
            candidate("second", "b", 4, ["funk"]),
        ]
        before = [dict(item) for item in items]
        self.assertEqual(
            [item["id"] for item in mmr_rerank(items, limit=2)],
            ["first", "second"],
        )
        self.assertEqual(items, before)

    def test_diversity_setting_maps_to_this_implementation_penalty_direction(self):
        self.assertEqual(diversity_setting_to_penalty(0), 0.0)
        self.assertEqual(diversity_setting_to_penalty(75), 0.75)
        self.assertEqual(diversity_setting_to_penalty(100), 1.0)
        for value in (-1, 101, 1.5, True):
            with self.assertRaises(ValueError):
                diversity_setting_to_penalty(value)

    def test_rank_normalization_is_invariant_to_score_scale_and_gaps(self):
        first_pool = [
            candidate("top", "a", 100, ["jazz"]),
            candidate("middle", "b", 90, ["jazz"]),
            candidate("bottom", "c", 80, ["funk"]),
        ]
        rescaled_pool = [
            candidate("top", "a", 10000, ["jazz"]),
            candidate("middle", "b", 9999, ["jazz"]),
            candidate("bottom", "c", 1, ["funk"]),
        ]
        first = mmr_rerank(first_pool, limit=3, lambda_=0)
        rescaled = mmr_rerank(rescaled_pool, limit=3, lambda_=0)
        self.assertEqual([item["id"] for item in first], [item["id"] for item in rescaled])
        self.assertEqual(
            [item["id"] for item in mmr_rerank(first_pool, limit=3, lambda_=0.6)],
            [item["id"] for item in mmr_rerank(rescaled_pool, limit=3, lambda_=0.6)],
        )

    def test_equal_scores_share_rank_relevance_and_constant_pool_is_safe(self):
        tied = [
            candidate("first", "a", 5, []),
            candidate("second", "b", 5, []),
            candidate("third", "c", 1, []),
        ]
        self.assertEqual(
            [item["id"] for item in mmr_rerank(tied, limit=3, lambda_=0)],
            ["first", "second", "third"],
        )
        constant = [
            candidate("first", "a", 5, []),
            candidate("second", "b", 5, []),
            candidate("third", "c", 5, []),
        ]
        self.assertEqual(
            [item["id"] for item in mmr_rerank(constant, limit=3, lambda_=0.5)],
            ["first", "second", "third"],
        )

    def test_relevance_floor_uses_original_pool_normalization_and_can_return_sparse_list(self):
        items = [candidate("high", "a", 10, []), candidate("mid", "b", 7, []), candidate("low", "c", 0, [])]
        result = mmr_rerank(items, limit=3, lambda_=0, relevance_floor=0.4)
        self.assertEqual([item["id"] for item in result], ["high", "mid"])
        self.assertEqual(mmr_rerank(items, limit=3, relevance_floor=1.0)[0]["id"], "high")
        with self.assertRaises(ValueError):
            mmr_rerank(items, limit=3, relevance_floor=1.1)

    def test_invalid_lambda_and_non_finite_scores_are_rejected(self):
        with self.assertRaises(ValueError):
            mmr_rerank([], limit=1, lambda_=1.1)
        with self.assertRaises(ValueError):
            mmr_rerank([candidate("bad", "a", float("nan"), [])], limit=1)

    def test_metrics_report_relevance_and_diversity(self):
        metrics = diversity_metrics([
            candidate("a", "artist-a", 10, ["jazz"]),
            candidate("b", "artist-b", 8, ["funk"]),
        ])
        self.assertEqual(metrics["count"], 2)
        self.assertEqual(metrics["unique_artists"], 2)
        self.assertEqual(metrics["mean_pairwise_similarity"], 0.0)
        self.assertEqual(metrics["mean_relevance_score"], 9.0)


if __name__ == "__main__":
    unittest.main()
