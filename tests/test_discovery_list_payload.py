import json
import unittest

from discovery_list_payload import build_cached_discovery_list_response


def music_key(value):
    return "".join(str(value or "").casefold().split())


def is_album_candidate(item):
    return bool(item.get("album")) and item.get("type", "album") == "album"


class DiscoveryListPayloadTests(unittest.TestCase):
    def test_missing_cache_preserves_empty_list_response(self):
        result = json.loads(build_cached_discovery_list_response(
            "classics", 10, lambda _name: None, [], {}, music_key, is_album_candidate
        ))
        self.assertEqual(result, {
            "list": "classics", "generated_at": None, "items": [],
            "message": "No saved list yet. Use discovery_refresh_list or wait for the daily background refresh.",
        })

    def test_filters_dismissed_saved_and_non_album_items(self):
        rows = [
            {"artist": "Artist A", "album": "Keep"},
            {"artist": "Artist A", "album": "Dismissed"},
            {"artist": "Artist B", "album": "Saved"},
            {"artist": "Artist C", "album": "Dismiss Artist"},
            {"artist": "Artist D", "album": "Single", "type": "single"},
        ]
        feedback = [
            {"scope": "album", "artist_key": "artista", "album_key": "dismissed", "status": "not_for_me"},
            {"scope": "artist", "artist_key": "artistc", "album_key": "", "status": "not_for_me_artist"},
        ]
        result = json.loads(build_cached_discovery_list_response(
            "classics", 10,
            lambda _name: {"generated_at": 42, "payload": {"items": rows, "source": "test"}},
            feedback, {("artistb", "saved"): {}}, music_key, is_album_candidate,
        ))
        self.assertEqual(result["items"], [rows[0]])
        self.assertEqual(result["total_before_feedback"], 5)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["source"], "test")

    def test_personal_response_keeps_recommendations_and_diagnostics(self):
        item = {"artist": "Björk", "album": "Debut"}
        result = json.loads(build_cached_discovery_list_response(
            "personal", 1,
            lambda _name: {"generated_at": 100, "payload": {
                "recommendations": [item, {"artist": "Other", "album": "EP", "type": "single"}],
                "source": "listenbrainz", "recent_listens_retrieved": 7,
                "limitations": ["limited metadata"], "library_albums_indexed": 12,
            }},
            [], {}, music_key, is_album_candidate,
        ))
        self.assertEqual(result["items"], [item])
        self.assertEqual(result["recommendations"], [item])
        self.assertEqual(result["diagnostics"], {
            "source": "listenbrainz", "recent_listens_retrieved": 7,
            "library_albums_indexed": 12, "limitations": ["limited metadata"],
        })

    def test_count_limits_visible_items_not_source_total(self):
        rows = [{"artist": "A", "album": str(i)} for i in range(4)]
        result = json.loads(build_cached_discovery_list_response(
            "classics", 2,
            lambda _name: {"generated_at": 1, "payload": {"items": rows}},
            [], {}, music_key, is_album_candidate,
        ))
        self.assertEqual(result["total_before_feedback"], 4)
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["items"]), 2)


if __name__ == "__main__":
    unittest.main()
