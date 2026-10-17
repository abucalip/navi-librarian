"""Direct tests for profile-derived supplementary MusicBrainz queries."""
import unittest

from discovery_tag_queries import select_supplementary_tag_queries


class SupplementaryTagQueryTests(unittest.TestCase):
    def test_contrasting_profiles_select_different_queries_with_same_cache(self):
        cached = {"artist-jazz": ["jazz", "hard bop"], "artist-rock": ["indie rock", "post-punk"]}
        pool = ["jazz", "indie rock", "afrobeat"]

        jazz = select_supplementary_tag_queries(
            {"artist-jazz": 5.0}, cached, pool
        )
        rock = select_supplementary_tag_queries(
            {"artist-rock": 5.0}, cached, pool
        )

        self.assertNotEqual([item[0] for item in jazz], [item[0] for item in rock])
        self.assertIn("primarytype:album AND tag:jazz", [item[0] for item in jazz])
        self.assertIn('primarytype:album AND tag:"indie rock"', [item[0] for item in rock])

    def test_profile_weight_and_exploration_quota_are_deterministic(self):
        result = select_supplementary_tag_queries(
            {"a": 3.0, "b": 1.0},
            {"a": ["soul", "jazz"], "b": ["jazz", "rock"]},
            ["afrobeat", "ambient", "soul"],
            profile_limit=2,
            exploration_limit=1,
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0][2], "profile:jazz")
        self.assertEqual(result[1][2], "profile:soul")
        self.assertEqual(result[2][2], "explore:afrobeat")

    def test_query_escaping_and_invalid_tags(self):
        result = select_supplementary_tag_queries(
            {"a": 1}, {"a": ['bossa nova', 'bad\nvalue', "x" * 65]}, []
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 'primarytype:album AND tag:"bossa nova"')

    def test_limits_are_bounded_and_validated(self):
        with self.assertRaises(ValueError):
            select_supplementary_tag_queries({}, {}, [], profile_limit=-1)
        self.assertEqual(
            select_supplementary_tag_queries(
                {"a": 10}, {"a": ["jazz", "soul", "rock"]}, ["ambient"],
                profile_limit=1, exploration_limit=1,
            ),
            [
                ("primarytype:album AND tag:jazz", "jazz", "profile:jazz"),
                ("primarytype:album AND tag:ambient", "other", "explore:ambient"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
