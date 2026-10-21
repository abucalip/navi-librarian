import unittest

from discovery.recommendations import apply_lastfm_popularity_bonus


class LastFMRecommendationScoringTests(unittest.TestCase):
    def test_popularity_bonus_is_capped_and_applied_to_existing_score(self):
        candidate = {
            "primary_artist": "Artist",
            "album": "Album",
            "discovery_score": 2.0,
        }

        checked = apply_lastfm_popularity_bonus(
            [candidate],
            {},
            lambda _artist, _album: {
                "listeners": 1_000_000,
                "playcount": 10_000_000,
                "tags": [],
            },
        )

        self.assertEqual(checked, 1)
        self.assertEqual(candidate["lastfm_popularity_bonus"], 1.12)
        self.assertAlmostEqual(candidate["discovery_score"], 2.24)
        self.assertEqual(candidate["lastfm_listeners"], 1_000_000)
        self.assertEqual(candidate["lastfm_playcount"], 10_000_000)

    def test_missing_stats_skip_candidate_and_do_not_increment_counter(self):
        candidate = {"artist": "Artist", "album": "Album", "discovery_score": 1.0}
        checked = apply_lastfm_popularity_bonus(
            [candidate], {}, lambda _artist, _album: None
        )
        self.assertEqual(checked, 0)
        self.assertNotIn("lastfm_popularity_bonus", candidate)
        self.assertEqual(candidate["discovery_score"], 1.0)

    def test_lastfm_tags_recalculate_recent_profile_bonus_before_popularity(self):
        candidate = {
            "artist": "Artist",
            "album": "Album",
            "discovery_score": 3.3,
            "recent_profile_bonus": 1.1,
        }
        checked = apply_lastfm_popularity_bonus(
            [candidate],
            {"jazz": 10},
            lambda _artist, _album: {
                "listeners": 0,
                "playcount": 0,
                "tags": ["soul"],
            },
        )
        self.assertEqual(checked, 1)
        self.assertEqual(candidate["recent_profile_families"], [])
        self.assertEqual(candidate["recent_profile_family"], "soul")
        self.assertEqual(candidate["recent_profile_bonus"], 1.0)
        self.assertAlmostEqual(candidate["discovery_score"], 3.0)
        self.assertEqual(candidate["lastfm_popularity_bonus"], 1.0)

    def test_only_top_forty_candidates_are_queried_in_score_order(self):
        candidates = [
            {"artist": "Artist", "album": str(score), "discovery_score": float(score)}
            for score in range(41)
        ]
        queried = []

        def lookup(_artist, album):
            queried.append(album)
            return {"listeners": 0, "playcount": 0, "tags": []}

        checked = apply_lastfm_popularity_bonus(candidates, {}, lookup)

        self.assertEqual(checked, 40)
        self.assertEqual(queried, [str(score) for score in range(40, 0, -1)])
        self.assertNotIn("0", queried)


if __name__ == "__main__":
    unittest.main()
