import unittest

from recommendation.taste_profile_evaluation import SYNTHETIC_PROFILES, evaluate_all


class TasteProfileEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate_all()

    def test_report_covers_every_profile(self):
        self.assertEqual(set(self.report), set(SYNTHETIC_PROFILES))
        for result in self.report.values():
            self.assertEqual(result["profile_source"], "derived")
            self.assertEqual(sum(result["category_counts"].values()), 10)

    def test_report_is_deterministic(self):
        self.assertEqual(self.report, evaluate_all())

    def test_non_jazz_profiles_have_few_vocabulary_miss_adventurous_candidates(self):
        # Adventurous that is neither core nor exploration: the old vocabulary-miss symptom.
        for name in ("metal", "k-pop", "classical"):
            self.assertLess(self.report[name]["adventurous_outside_exploration_share"], 0.5, name)

    def test_exploration_does_not_depend_on_a_regional_set(self):
        for name in ("metal", "classical"):
            self.assertFalse(
                {"african", "north-african-middle-eastern"}
                & set(self.report[name]["exploration_families"]), name)

    def test_aggregates_only(self):
        self.assertNotIn("synthetic", str(self.report))


if __name__ == "__main__":
    unittest.main()
