import unittest

from recommendation.taste_profile_evaluation import SYNTHETIC_PROFILES, evaluate_all


class TasteProfileEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate_all()

    def test_report_covers_every_profile_in_both_modes(self):
        self.assertEqual(set(self.report), set(SYNTHETIC_PROFILES))
        for result in self.report.values():
            self.assertEqual(result["profile_source"], "derived")
            for mode in ("fixed", "derived"):
                self.assertEqual(sum(result[mode]["category_counts"].values()), 10)

    def test_report_is_deterministic(self):
        self.assertEqual(self.report, evaluate_all())

    def test_derived_reduces_vocabulary_miss_for_non_jazz_profiles(self):
        for name in ("metal", "k-pop", "classical"):
            r = self.report[name]
            self.assertLess(r["derived"]["adventurous_share"], r["fixed"]["adventurous_share"], name)
        self.assertLess(self.report["metal"]["derived"]["adventurous_share"], 0.5)

    def test_derived_exploration_does_not_depend_on_fixed_regional_set(self):
        for name in ("metal", "classical"):
            self.assertFalse(
                {"african", "north-african-middle-eastern"}
                & set(self.report[name]["derived"]["exploration_families"]), name)

    def test_aggregates_only(self):
        self.assertNotIn("synthetic", str(self.report))


if __name__ == "__main__":
    unittest.main()
