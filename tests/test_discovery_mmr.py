import unittest

from discovery_mmr import (
    candidate_similarity,
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
        result = mmr_rerank(items, limit=3, lambda_=0.5)
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
