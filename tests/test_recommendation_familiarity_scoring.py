import math
import unittest

from discovery.recommendations import apply_familiarity_exploration_bonus


class RecommendationFamiliarityScoringTests(unittest.TestCase):
    def test_familiarity_curve_is_smooth_for_weighted_recent_artist_counts(self):
        counts = (0.0, 1.5, 2.0, 3.0, 5.0, 6.0, 10.0, 11.0)
        scores = []
        for recent_count in counts:
            with self.subTest(recent_count=recent_count):
                candidate = {"score": 2.0, "discovery_score": -1.0}
                result = apply_familiarity_exploration_bonus(
                    candidate, recent_count, [], set()
                )
                expected_multiplier = 0.82 + 0.42 * math.exp(
                    -((recent_count - 1.5) / 3.0) ** 2
                )
                self.assertAlmostEqual(result, 2.0 * expected_multiplier)
                self.assertAlmostEqual(candidate["discovery_score"], 2.0 * expected_multiplier)
                scores.append(result)
        self.assertGreater(scores[1], scores[0])
        self.assertGreater(scores[0], scores[4])
        self.assertGreater(scores[4], scores[-1])

    def test_exploration_family_bonus_applies_only_on_family_overlap(self):
        candidate = {"score": 2.0}
        result = apply_familiarity_exploration_bonus(
            candidate, 0, ["Malian desert blues"], {"african"}
        )
        self.assertAlmostEqual(result, 2.0 * (0.82 + 0.42 * math.exp(-0.25)) * 1.10)

        candidate_without_overlap = {"score": 2.0}
        result_without_overlap = apply_familiarity_exploration_bonus(
            candidate_without_overlap, 0, ["Malian desert blues"], {"jazz"}
        )
        self.assertAlmostEqual(result_without_overlap, 2.0 * (0.82 + 0.42 * math.exp(-0.25)))
        self.assertGreater(result, result_without_overlap)


if __name__ == "__main__":
    unittest.main()
