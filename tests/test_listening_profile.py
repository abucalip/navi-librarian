import unittest

from listening_profile import build_listening_profile


class ListeningProfileTests(unittest.TestCase):
    def test_aggregates_artists_and_albums_with_existing_payload_shape(self):
        listens = [
            {"track_metadata": {"artist_name": "A", "release_name": "One", "track_name": "x"}},
            {"track_metadata": {"artist_name": "A", "release_name": "One", "track_name": "y"}},
            {"track_metadata": {"artist_name": "B", "release_name": "Two"}},
            {"track_metadata": {"artist_name": "A", "release_name": ""}},
            {"track_metadata": {}},
        ]

        result = build_listening_profile(listens, "listener", 30)

        self.assertEqual(result["source"], "ListenBrainz")
        self.assertEqual(result["username"], "listener")
        self.assertEqual(result["period_days"], 30)
        self.assertEqual(result["listens_retrieved"], 5)
        self.assertEqual(result["distinct_artists"], 2)
        self.assertEqual(result["top_artists"], [
            {"artist": "A", "listens": 3},
            {"artist": "B", "listens": 1},
        ])
        self.assertEqual(result["top_albums"], [
            {"artist": "A", "album": "One", "listens": 2},
            {"artist": "B", "album": "Two", "listens": 1},
        ])
        self.assertTrue(result["read_only"])
        self.assertIn("three pages", result["note"])

    def test_empty_history_returns_empty_rankings(self):
        result = build_listening_profile([], "", 7)
        self.assertEqual(result["listens_retrieved"], 0)
        self.assertEqual(result["distinct_artists"], 0)
        self.assertEqual(result["top_artists"], [])
        self.assertEqual(result["top_albums"], [])

    def test_top_rankings_keep_first_seen_order_for_ties(self):
        listens = [
            {"track_metadata": {"artist_name": "First", "release_name": "Album"}},
            {"track_metadata": {"artist_name": "Second", "release_name": "Album"}},
        ]
        result = build_listening_profile(listens, "x", 1)
        self.assertEqual([row["artist"] for row in result["top_artists"]], ["First", "Second"])


if __name__ == "__main__":
    unittest.main()
