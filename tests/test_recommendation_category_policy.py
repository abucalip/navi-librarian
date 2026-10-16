import unittest

from discovery_recommendations import classify_recommendation_category


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

    def test_regional_artist_override_can_make_candidate_adjacent_without_tags(self):
        category, families = self.classify(
            {"primary_artist": "Tinariwen"}, [],
            exploration={"african"},
        )
        self.assertEqual(category, "adjacent")
        self.assertEqual(families, {"african"})

    def test_adventurous_tag_precedes_core_family_overlap(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["free jazz"],
            core={"jazz"}, exploration={"jazz"},
        )
        self.assertEqual(category, "adventurous")
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

    def test_non_overlapping_classified_candidate_falls_back_to_adventurous(self):
        category, families = self.classify(
            {"primary_artist": "Artist"}, ["electronic"],
        )
        self.assertEqual(category, "adventurous")
        self.assertEqual(families, {"electronic"})


if __name__ == "__main__":
    unittest.main()
