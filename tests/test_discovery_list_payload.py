import json
import unittest

from discovery.list_payload import build_cached_discovery_list_response


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

    def test_new_releases_hides_stored_future_items_only_when_today_given(self):
        rows = [
            {"artist": "A", "album": "Past", "first_release_date": "2026-10-01"},
            {"artist": "A", "album": "Today", "first_release_date": "2026-10-22"},
            {"artist": "A", "album": "Future", "first_release_date": "2026-12-01"},
        ]
        read = lambda _name: {"generated_at": 1, "payload": {"items": rows}}
        def albums(**kw):
            return [i["album"] for i in json.loads(build_cached_discovery_list_response(
                "new_releases", 10, read, [], {}, music_key, is_album_candidate, **kw))["items"]]
        self.assertEqual(albums(today="2026-10-22"), ["Past", "Today"])
        self.assertEqual(albums(), ["Past", "Today", "Future"])

    def test_hides_imported_and_library_owned_albums_on_non_personal_lists(self):
        rows = [
            {"artist": "A", "album": "Imported"},
            {"artist": "A", "album": "Owned"},
            {"artist": "A", "album": "Keep"},
        ]
        read = lambda _name: {"generated_at": 1, "payload": {"items": rows}}
        snapshot = lambda: {"albums": [{"artist": "A", "album": "Owned"}]}
        for name in ("classics", "artist_deep_dive", "new_releases"):
            result = json.loads(build_cached_discovery_list_response(
                name, 10, read, [], {}, music_key, is_album_candidate, snapshot,
                acquired={("a", "imported")}, today="2026-10-22",
            ))
            self.assertEqual([i["album"] for i in result["items"]], ["Keep"], name)

    def test_acquired_hides_albums_even_when_library_snapshot_fails(self):
        def boom():
            raise RuntimeError("navidrome down")
        read = lambda _name: {"generated_at": 1, "payload": {"items": [
            {"artist": "A", "album": "Imported"}, {"artist": "A", "album": "Keep"}]}}
        result = json.loads(build_cached_discovery_list_response(
            "classics", 10, read, [], {}, music_key, is_album_candidate, boom,
            acquired={("a", "imported")},
        ))
        self.assertEqual([i["album"] for i in result["items"]], ["Keep"])

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


class PersonalReadTimeOwnershipTests(unittest.TestCase):
    def _read(self, items, library):
        def snapshot():
            if isinstance(library, Exception):
                raise library
            return {"albums": library}
        return json.loads(build_cached_discovery_list_response(
            "personal", 10,
            lambda _name: {"generated_at": 100, "payload": {
                "recommendations": items, "source": "listenbrainz",
            }},
            [], {}, music_key, is_album_candidate, library_snapshot=snapshot,
        ))

    def test_owned_album_added_after_build_is_hidden_and_ranks_kept(self):
        items = [
            {"rank": 1, "artist": "Artist A", "album": "Now Owned"},
            {"rank": 2, "artist": "Artist B", "album": "Still New"},
        ]
        result = self._read(items, [{"artist": "artist a", "album": "now owned"}])
        self.assertEqual(result["recommendations"], [items[1]])
        self.assertEqual(result["recommendations"][0]["rank"], 2)
        self.assertEqual(result["diagnostics"]["read_filter"], {
            "ownership_checked": True, "kept": 1, "owned": 1,
            "duplicate": 0, "unidentified": 0,
        })

    def test_duplicate_identities_are_removed_on_read(self):
        items = [
            {"artist": "Artist A", "album": "Same"},
            {"artist": " artist a ", "album": "SAME"},
        ]
        result = self._read(items, [])
        self.assertEqual(len(result["recommendations"]), 1)
        self.assertEqual(result["diagnostics"]["read_filter"]["duplicate"], 1)

    def test_library_read_failure_serves_stored_items_and_says_so(self):
        items = [{"artist": "Artist A", "album": "Kept"}]
        result = self._read(items, RuntimeError("navidrome down"))
        self.assertEqual(result["recommendations"], items)
        self.assertEqual(result["diagnostics"]["read_filter"], {"ownership_checked": False})
        self.assertNotIn("navidrome down", json.dumps(result))

    def test_without_library_snapshot_response_is_unchanged(self):
        items = [{"artist": "Artist A", "album": "Owned Here"}]
        result = json.loads(build_cached_discovery_list_response(
            "personal", 10,
            lambda _name: {"generated_at": 1, "payload": {"recommendations": items}},
            [], {}, music_key, is_album_candidate,
        ))
        self.assertEqual(result["recommendations"], items)
        self.assertNotIn("read_filter", result["diagnostics"])
