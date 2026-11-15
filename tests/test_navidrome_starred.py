import unittest

from integrations.navidrome import fetch_starred, items, parse_starred


class StarredParserTests(unittest.TestCase):
    def test_parses_starred_artists_and_albums_with_star_dates(self):
        root = {"starred2": {
            "artist": [{"id": "ar-1", "name": "Band", "starred": "2024-05-01T10:00:00Z",
                        "albumCount": 3}],
            "album": [{"id": "al-1", "name": "Record", "artist": "Band",
                       "artistId": "ar-1", "starred": "2023-01-02T03:04:05.5+02:00",
                       "songCount": 9}],
        }}
        result = parse_starred(root, items)
        self.assertEqual(result, {
            "artists": [{"id": "ar-1", "name": "Band", "starred_at": 1714557600.0}],
            "albums": [{"id": "al-1", "name": "Record", "artist": "Band",
                        "artist_id": "ar-1", "starred_at": 1672621445.5}],
        })

    def test_scalar_collection_values_are_normalized_to_lists(self):
        root = {"starred2": {
            "artist": {"id": "ar-1", "name": "Band"},
            "album": {"id": "al-1", "name": "Record", "artist": "Band", "artistId": "ar-1"},
        }}
        result = parse_starred(root, items)
        self.assertEqual([row["id"] for row in result["artists"]], ["ar-1"])
        self.assertEqual([row["id"] for row in result["albums"]], ["al-1"])

    def test_missing_or_unreadable_star_dates_keep_the_row(self):
        root = {"starred2": {
            "artist": [
                {"id": "ar-1", "name": "No date"},
                {"id": "ar-2", "name": "Bad date", "starred": "last tuesday"},
                {"id": "ar-3", "name": "Zero date", "starred": "0001-01-01T00:00:00Z"},
                {"id": "ar-4", "name": "Empty date", "starred": ""},
            ],
        }}
        result = parse_starred(root, items)
        self.assertEqual(
            [(row["id"], row["starred_at"]) for row in result["artists"]],
            [("ar-1", None), ("ar-2", None), ("ar-3", None), ("ar-4", None)],
        )

    def test_nanosecond_fraction_timestamp_is_accepted(self):
        root = {"starred2": {
            "album": [{"id": "al-1", "starred": "2024-05-01T10:00:00.123456789Z"}],
        }}
        result = parse_starred(root, items)
        self.assertAlmostEqual(result["albums"][0]["starred_at"], 1714557600.123456, places=5)

    def test_rows_without_an_id_are_dropped_and_songs_are_ignored(self):
        root = {"starred2": {
            "artist": [{"name": "No id"}, {"id": "", "name": "Empty id"},
                       {"id": "ar-1", "name": "Kept"}],
            "album": [{"name": "No id album"}],
            "song": [{"id": "tr-1", "title": "Track", "starred": "2024-05-01T10:00:00Z"}],
        }}
        result = parse_starred(root, items)
        self.assertEqual(result, {
            "artists": [{"id": "ar-1", "name": "Kept", "starred_at": None}],
            "albums": [],
        })

    def test_empty_library_with_absent_or_empty_starred2(self):
        empty = {"artists": [], "albums": []}
        self.assertEqual(parse_starred({"status": "ok"}, items), empty)
        self.assertEqual(parse_starred({"status": "ok", "starred2": {}}, items), empty)
        self.assertEqual(parse_starred({"starred2": {"artist": None, "album": None}}, items), empty)


class FetchStarredTests(unittest.TestCase):
    def test_makes_one_get_starred2_call_and_parses_the_response(self):
        calls = []

        def fake_api_call(method, **params):
            calls.append((method, params))
            return {"status": "ok", "starred2": {"artist": [{"id": "ar-1", "name": "Band"}]}}

        result = fetch_starred(fake_api_call, items)
        self.assertEqual(calls, [("getStarred2", {})])
        self.assertEqual(result, {
            "artists": [{"id": "ar-1", "name": "Band", "starred_at": None}],
            "albums": [],
        })

    def test_api_errors_propagate_unchanged(self):
        def failing_api_call(method, **params):
            raise RuntimeError("Navidrome API error 40: Wrong username or password")

        with self.assertRaisesRegex(RuntimeError, "Navidrome API error 40"):
            fetch_starred(failing_api_call, items)


if __name__ == "__main__":
    unittest.main()
