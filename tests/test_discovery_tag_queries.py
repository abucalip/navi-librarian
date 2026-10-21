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


class TagQueryRotationTests(unittest.TestCase):
    PROFILE = {"a": 1.0}
    TAGS = {"a": [f"tag{i}" for i in range(10)]}
    POOL = [f"pool{i}" for i in range(6)]

    def _styles(self, rotation):
        return [i[2] for i in select_supplementary_tag_queries(
            self.PROFILE, self.TAGS, self.POOL, rotation=rotation)]

    def test_none_matches_default_and_counts_are_unchanged(self):
        base = select_supplementary_tag_queries(self.PROFILE, self.TAGS, self.POOL)
        self.assertEqual(base, select_supplementary_tag_queries(
            self.PROFILE, self.TAGS, self.POOL, rotation=None))
        for r in range(8):
            self.assertEqual(len(self._styles(r)), len(base))

    def test_rotation_is_deterministic_keeps_anchors_and_varies(self):
        self.assertEqual(self._styles(3), self._styles(3))
        seen = {tuple(self._styles(r)) for r in range(6)}
        self.assertGreater(len(seen), 1)
        for r in range(6):
            self.assertEqual(self._styles(r)[:3], self._styles(None)[:3])

    def test_rotation_with_short_supply_does_not_fail(self):
        result = select_supplementary_tag_queries(
            {"a": 1.0}, {"a": ["x"]}, ["p"], rotation=5)
        self.assertEqual(len(result), 2)
