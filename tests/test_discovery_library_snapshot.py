import unittest

from discovery.library_snapshot import build_library_snapshot


def items(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class DiscoveryLibrarySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.cache = {}
        self.calls = []
        self.writes = []

    def read_list(self, name):
        return self.cache.get(name)

    def write_list(self, name, payload):
        self.writes.append((name, payload))
        self.cache[name] = {"payload": payload, "generated_at": 1000}

    def test_builds_snapshot_deduplicates_album_ids_and_preserves_shape(self):
        def api_call(method, **params):
            self.calls.append((method, params))
            if method == "getArtists":
                return {"artists": {"index": [
                    {"artist": [{"id": "ar1", "name": " Artist ", "albumCount": "2"}]},
                    {"artist": {"id": "ar2", "name": "", "albumCount": 1}},
                ]}}
            if params["offset"] == 0:
                return {"albumList2": {"album": [
                    {"id": "al1", "artist": "Artist", "name": "One", "songCount": "9", "year": 1999, "coverArt": "c1"},
                    {"id": "al1", "artist": "Artist", "name": "Duplicate", "songCount": 1},
                    {"id": "al2", "artist": "Other", "name": "Two", "songCount": 4},
                ]}}
            return {"albumList2": {"album": []}}

        result = build_library_snapshot(
            api_call, items, self.read_list, self.write_list, now=lambda: 1000,
            page_size=3, max_albums=6,
        )

        self.assertEqual(result["artists"], [{"id": "ar1", "name": "Artist", "album_count": 2}])
        self.assertEqual(result["albums"], [
            {"id": "al1", "artist": "Artist", "album": "One", "year": 1999, "song_count": 9, "coverArt": "c1"},
            {"id": "al2", "artist": "Other", "album": "Two", "year": None, "song_count": 4, "coverArt": None},
        ])
        self.assertEqual([method for method, _ in self.calls], ["getArtists", "getAlbumList2", "getAlbumList2"])
        self.assertEqual(self.calls[1][1], {"type": "alphabeticalByName", "size": 3, "offset": 0})
        self.assertEqual(self.writes, [("library_snapshot", result)])

    def test_uses_fresh_cache_when_album_schema_is_current(self):
        payload = {"artists": [], "albums": [{"song_count": 12}]}
        self.cache["library_snapshot"] = {"payload": payload, "generated_at": 950}
        result = build_library_snapshot(
            lambda *_a, **_k: self.fail("API should not be called"),
            items, self.read_list, self.write_list, now=lambda: 1000,
        )
        self.assertIs(result, payload)
        self.assertEqual(self.writes, [])

    def test_rebuilds_old_cached_album_schema(self):
        self.cache["library_snapshot"] = {
            "payload": {"artists": [], "albums": [{"songCount": 12}]},
            "generated_at": 990,
        }
        def api_call(method, **params):
            if method == "getArtists":
                return {"artists": {"index": []}}
            return {"albumList2": {"album": []}}
        result = build_library_snapshot(
            api_call, items, self.read_list, self.write_list, now=lambda: 1000,
        )
        self.assertEqual(result, {"artists": [], "albums": []})
        self.assertEqual(len(self.writes), 1)

    def test_refuses_inventory_that_reaches_safety_limit(self):
        def api_call(method, **params):
            if method == "getArtists":
                return {"artists": {"index": []}}
            return {"albumList2": {"album": [{"id": str(params["offset"])}]}}
        with self.assertRaisesRegex(RuntimeError, "safety limit"):
            build_library_snapshot(
                api_call, items, self.read_list, self.write_list,
                now=lambda: 1000, page_size=1, max_albums=2,
            )
        self.assertEqual(self.writes, [])


if __name__ == "__main__":
    unittest.main()
