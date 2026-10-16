import unittest

from discovery_recommendation_payload import build_personal_recommendation_payload


def candidate(**overrides):
    value = {
        "artist": "Artist",
        "album": "Album",
        "discovery_category": "adjacent",
        "diversity_style": "other",
        "genres": ["jazz"],
        "genre_families": ["jazz"],
        "recent_profile_family": "jazz",
        "recent_profile_families": ["jazz", "soul"],
        "recent_profile_bonus": 1.23456,
        "genre_metadata_available": True,
        "score": 0.75,
        "discovery_source": "listenbrainz",
        "discovery_score": 0.12345678,
        "lastfm_listeners": 123,
        "lastfm_playcount": 456,
        "lastfm_tags": ["soul"],
        "lastfm_popularity_bonus": 1.12345,
        "tracks": ["one", "two", "three", "four"],
    }
    value.update(overrides)
    return value


class PersonalRecommendationPayloadTests(unittest.TestCase):
    def test_projects_legacy_fields_rounding_and_track_limit(self):
        result = build_personal_recommendation_payload(candidate(), 7)
        self.assertEqual(result["artist"], "Artist")
        self.assertEqual(result["album"], "Album")
        self.assertEqual(result["recent_artist_listens"], 7)
        self.assertEqual(result["recent_profile_bonus"], 1.235)
        self.assertEqual(result["discovery_score"], 0.123457)
        self.assertEqual(result["lastfm_popularity_bonus"], 1.123)
        self.assertEqual(result["suggested_tracks"], ["one", "two", "three"])
        self.assertEqual(result["listenbrainz_score"], 0.75)
        self.assertNotIn("ownership_check", result)
        self.assertNotIn("ownership_note", result)

    def test_lastfm_candidates_do_not_expose_a_listenbrainz_score(self):
        result = build_personal_recommendation_payload(
            candidate(discovery_source="lastfm", score=0.9), 0
        )
        self.assertIsNone(result["listenbrainz_score"])
        self.assertEqual(result["discovery_source"], "lastfm")

    def test_defaults_match_legacy_payload(self):
        row = candidate()
        for key in (
            "diversity_style", "recent_profile_family", "recent_profile_families",
            "recent_profile_bonus", "discovery_source", "lastfm_listeners",
            "lastfm_playcount", "lastfm_tags", "lastfm_popularity_bonus",
        ):
            row.pop(key, None)
        result = build_personal_recommendation_payload(row, 0)
        self.assertEqual(result["diversity_style"], "other")
        self.assertIsNone(result["recent_profile_family"])
        self.assertEqual(result["recent_profile_families"], [])
        self.assertEqual(result["recent_profile_bonus"], 1.0)
        self.assertEqual(result["discovery_source"], "listenbrainz")
        self.assertEqual(result["lastfm_tags"], [])
        self.assertEqual(result["lastfm_popularity_bonus"], 1.0)
        self.assertIsNone(result["lastfm_listeners"])
        self.assertIsNone(result["lastfm_playcount"])

    def test_category_reason_and_low_confidence_suffix(self):
        cases = {
            "adjacent": "Genre tags connect this artist to your established musical interests.",
            "cross_genre": "Genre tags suggest a bridge between multiple musical families in your profile.",
            "adventurous": "Available genre tags suggest a departure from the strongest mapped genre matches.",
            "unclassified": "Genre metadata is unavailable, so this candidate's musical fit is uncertain.",
        }
        for category, expected in cases.items():
            with self.subTest(category=category):
                result = build_personal_recommendation_payload(
                    candidate(discovery_category=category, genre_metadata_available=False),
                    0,
                )
                self.assertEqual(
                    result["reason"],
                    expected + " Genre metadata was unavailable, so this classification has low confidence.",
                )

    def test_optional_metadata_values_are_preserved(self):
        genres = ["jazz", "soul"]
        families = ["jazz", "rnb-soul"]
        tags = ["neo-soul"]
        row = candidate(genres=genres, genre_families=families, lastfm_tags=tags)
        result = build_personal_recommendation_payload(row, 3)
        self.assertIs(result["genres"], genres)
        self.assertIs(result["genre_families"], families)
        self.assertIs(result["lastfm_tags"], tags)


if __name__ == "__main__":
    unittest.main()
