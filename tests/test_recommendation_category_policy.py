import unittest

from discovery.recommendations import classify_recommendation_category


class RecommendationCategoryPolicyTests(unittest.TestCase):
    def classify(self, candidate, tags, core=(), exploration=()):
        return classify_recommendation_category(
            candidate,
            tags,
            set(core),
            set(exploration),
        )

    def test_no_tags_or_regional_override_is_unclassified(self):
        category, families = self.classify(
            {"primary_artist": "Unknown Artist"}, []
        )
        self.assertEqual(category, "unclassified")
        self.assertEqual(families, set())

    def test_artist_names_do_not_classify_candidates_without_tags(self):
        category, families = self.classify(
            {"primary_artist": "Tinariwen"}, [], exploration={"african"},
        )
        self.assertEqual((category, families), ("unclassified", set()))

    def test_free_jazz_overlapping_a_core_family_is_not_forced_adventurous(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["free jazz"],
            core={"jazz"}, exploration=set(),
        )
        self.assertEqual(category, "adjacent")
        self.assertEqual(families, {"jazz"})

    def test_two_core_family_overlaps_are_cross_genre(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["jazz", "bossa nova"],
            core={"jazz", "brazilian"},
        )
        self.assertEqual(category, "cross_genre")
        self.assertEqual(families, {"jazz", "brazilian"})

    def test_single_core_overlap_is_adjacent(self):
        category, _families = self.classify(
            {"primary_artist": "Artist"}, ["jazz"], core={"jazz"}
        )
        self.assertEqual(category, "adjacent")

    def test_exploration_thread_makes_a_core_candidate_adventurous(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["jazz", "electronic"],
            core={"jazz"}, exploration={"electronic"},
        )
        self.assertEqual((category, families), ("adventurous", {"jazz", "electronic"}))

    def test_two_core_clusters_beat_an_exploration_thread(self):
        category, _ = self.classify(
            {"primary_artist": "Artist"}, ["jazz", "bossa nova", "electronic"],
            core={"jazz", "brazilian"}, exploration={"electronic"},
        )
        self.assertEqual(category, "cross_genre")

    def test_exploration_overlap_is_adventurous_but_keeps_its_bonus(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["electronic"],
            core={"jazz"}, exploration={"electronic"},
        )
        self.assertEqual((category, families), ("adventurous", {"electronic"}))

    def test_non_overlapping_classified_candidate_falls_back_to_adventurous(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["electronic"],
        )
        self.assertEqual(category, "adventurous")
        self.assertEqual(families, {"electronic"})


if __name__ == "__main__":
    unittest.main()
