"""Direct tests for profile-derived supplementary MusicBrainz queries."""
import unittest

from discovery.tag_queries import select_supplementary_tag_queries


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

    def test_style_slug_folds_accents_but_the_query_keeps_the_tag(self):
        result = select_supplementary_tag_queries(
            {"a": 1}, {"a": ["raï", "café jazz", "音楽"]}, [], profile_limit=3)
        by_tag = {item[0].split("tag:", 1)[1].strip('"'): item for item in result}
        self.assertEqual(by_tag["raï"][2], "profile:rai")
        self.assertEqual(by_tag["raï"][0], "primarytype:album AND tag:raï")
        self.assertEqual(by_tag["café jazz"][2], "profile:cafe_jazz")
        self.assertEqual(by_tag["音楽"][2], "profile:other")

    def test_distinct_tags_never_share_a_style_key(self):
        result = select_supplementary_tag_queries(
            {"a": 4, "b": 3, "c": 2, "d": 1},
            {"a": ["raï"], "b": ["rai"], "c": ["hip hop"], "d": ["hip-hop"]}, [],
            profile_limit=4)
        styles = [item[2] for item in result]
        self.assertEqual(len(set(styles)), 4)
        self.assertEqual(styles[0], "profile:rai")
        self.assertEqual(styles[1], "profile:rai_2")
        self.assertEqual(styles[2], "profile:hip_hop")
        self.assertEqual(styles[3], "profile:hip_hop_2")
        self.assertEqual(len({item[0] for item in result}), 4)

    def test_profile_and_exploration_styles_stay_separate(self):
        result = select_supplementary_tag_queries(
            {"a": 1}, {"a": ["raï"]}, ["rai"], profile_limit=1, exploration_limit=1)
        self.assertEqual([item[2] for item in result], ["profile:rai", "explore:rai"])

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
                ("primarytype:album AND tag:ambient", "electronic", "explore:ambient"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
