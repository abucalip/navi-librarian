import unittest

from discovery_recommendations import apply_familiarity_exploration_bonus


class RecommendationFamiliarityScoringTests(unittest.TestCase):
    def test_recent_artist_count_thresholds_preserve_existing_multipliers(self):
        cases = (
            (0, 1.35),
            (1, 1.20),
            (2, 1.20),
            (3, 1.05),
            (5, 1.05),
            (6, 0.90),
            (10, 0.90),
            (11, 0.75),
        )
        for recent_count, multiplier in cases:
            with self.subTest(recent_count=recent_count):
                candidate = {"score": 2.0, "discovery_score": -1.0}
                result = apply_familiarity_exploration_bonus(
                    candidate, recent_count, [], set()
                )
                self.assertAlmostEqual(result, 2.0 * multiplier)
                self.assertAlmostEqual(candidate["discovery_score"], 2.0 * multiplier)

    def test_exploration_family_bonus_applies_only_on_family_overlap(self):
        candidate = {"score": 2.0}
        result = apply_familiarity_exploration_bonus(
            candidate, 0, ["Malian desert blues"], {"african"}
        )
        self.assertAlmostEqual(result, 2.0 * 1.35 * 1.10)

        candidate_without_overlap = {"score": 2.0}
        result_without_overlap = apply_familiarity_exploration_bonus(
            candidate_without_overlap, 0, ["Malian desert blues"], {"jazz"}
        )
        self.assertAlmostEqual(result_without_overlap, 2.0 * 1.35)
        self.assertGreater(result, result_without_overlap)


if __name__ == "__main__":
    unittest.main()
