"""Direct-import regressions for pure slskd search helpers."""

import re
import unittest

from slskd_search import (
    album_path_match,
    path_match_diagnostics,
    response_items,
    expected_track_count,
    search_queries,
)


def music_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


class ExpectedTrackCountTests(unittest.TestCase):
    def test_reads_common_positive_count_fields(self):
        for key in ("track_count", "trackCount", "number_of_tracks", "numberOfTracks",
                    "total_tracks", "totalTracks", "tracks_count", "tracksCount", "trackcount"):
            with self.subTest(key=key):
                self.assertEqual(expected_track_count({key: "12"}), 12)

    def test_reads_nested_metadata_and_track_object_lists(self):
        self.assertEqual(expected_track_count({"release": {"metadata": {"totalTracks": 9}}}), 9)
        self.assertEqual(expected_track_count({"album": {"tracks": [{"title": "a"}, {"title": "b"}]}}), 2)
        self.assertEqual(expected_track_count({"tracklist": [{"title": "a"}]}), 1)

    def test_ignores_invalid_counts_and_unrelated_arrays(self):
        self.assertIsNone(expected_track_count(None))
        self.assertIsNone(expected_track_count([]))
        self.assertIsNone(expected_track_count({"track_count": 0, "metadata": {"trackCount": "bad"}}))
        self.assertIsNone(expected_track_count({"tracks": ["not", "track", "objects"]}))

    def test_handles_recursive_metadata_cycle(self):
        metadata = {}
        metadata["metadata"] = metadata
        self.assertIsNone(expected_track_count(metadata))

class SlskdSearchQueryTests(unittest.TestCase):
    def test_queries_broaden_without_dropping_artist_immediately(self):
        queries = search_queries("Tinariwen", "Idrache (Traces of the Past)")
        self.assertEqual(queries, [
            "Tinariwen Idrache (Traces of the Past)",
            "Tinariwen Idrache Traces of the Past",
            "Tinariwen Idrache",
        ])
        self.assertEqual(len({query.casefold() for query in queries}), len(queries))

    def test_queries_reject_blank_artist_or_album(self):
        self.assertEqual(search_queries("", "Album"), [])
        self.assertEqual(search_queries("Artist", "  "), [])

    def test_query_whitespace_is_normalized(self):
        self.assertEqual(search_queries("  Tinariwen  ", " Idrache   (Traces of the Past) ")[0],
                         "Tinariwen Idrache (Traces of the Past)")


class SlskdSearchPayloadTests(unittest.TestCase):
    def test_response_payload_normalization(self):
        peer = {"username": "peer", "files": [{"filename": "Bombino/Agamgam/01.flac"}]}
        self.assertEqual(response_items([peer]), [peer])
        self.assertEqual(response_items({"responses": [peer]}), [peer])
        self.assertEqual(response_items({"items": [peer]}), [peer])
        self.assertEqual(response_items({"responses": "not-a-list"}), [])
        self.assertEqual(response_items(None), [])
        self.assertEqual(response_items([peer, "invalid"]), [peer])

    def test_path_matching_handles_edition_suffix_and_partial_wording(self):
        self.assertTrue(album_path_match(
            "A Moon Shaped Pool", "Radiohead/A Moon Shaped Pool (FLAC Deluxe Edition)"
        ))
        self.assertTrue(album_path_match("A Moon Shaped Pool", "Radiohead/Moon Shaped Pool"))

    def test_path_matching_rejects_unrelated_album_names(self):
        self.assertFalse(album_path_match("Moon River", "Radiohead/Moonlight River"))
        self.assertFalse(album_path_match("AM", "Sam"))
        self.assertFalse(album_path_match("", "Radiohead/Album"))

    def test_diagnostics_explain_album_and_artist_match_signals(self):
        result = path_match_diagnostics([{
            "username": "peer",
            "files": [{
                "filename": r"Music\\Tinariwen\\Tinariwen - Idrache (Traces Of The Past) - 2024\\01 - Soixante Trois.flac"
            }],
        }], "Tinariwen", "Idrache (Traces of the past)",
            music_key=music_key, album_path_match=album_path_match)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["album_path_match"])
        self.assertTrue(result[0]["artist_path_match"])
        self.assertFalse(result[0]["album_filename_match"])

    def test_diagnostics_ignore_non_audio_and_bound_results(self):
        files = [
            {"filename": f"Artist/Album/{index:02d}.flac"}
            for index in range(12)
        ] + [{"filename": "Artist/Album/cover.jpg"}]
        result = path_match_diagnostics(
            [{"username": "peer", "files": files}], "Artist", "Album",
            limit=50, music_key=music_key, album_path_match=album_path_match)
        self.assertEqual(len(result), 10)
        self.assertTrue(all(item["filename"].endswith(".flac") for item in result))


if __name__ == "__main__":
    unittest.main()
