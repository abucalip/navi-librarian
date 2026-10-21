"""Direct-import tests for raw Navidrome album inventory pagination."""

import unittest

from discovery.library_snapshot import (
    AlbumInventoryLimitError,
    fetch_album_inventory,
)


def items(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class FetchAlbumInventoryTests(unittest.TestCase):
    def test_pages_raw_records_and_deduplicates_nonempty_ids(self):
        calls = []

        def api_call(method, **params):
            calls.append((method, params))
            pages = {
                0: [
                    {"id": "a1", "name": "One", "songCount": "9"},
                    {"id": "a2", "name": "Two", "songCount": "8"},
                ],
                2: [
                    {"id": "a2", "name": "Duplicate", "songCount": "1"},
                    {"id": "a3", "name": "Three", "songCount": "7"},
                ],
                4: [],
            }
            self.assertEqual(method, "getAlbumList2")
            return {"albumList2": {"album": pages[params["offset"]]}}

        result = fetch_album_inventory(api_call, items, page_size=2, max_albums=6)

        self.assertEqual([album["name"] for album in result], ["One", "Two", "Three"])
        self.assertEqual(result[0], {"id": "a1", "name": "One", "songCount": "9"})
        self.assertEqual([params["offset"] for _, params in calls], [0, 2, 4])
        self.assertTrue(all(params["type"] == "alphabeticalByName" for _, params in calls))
        self.assertTrue(all(params["size"] == 2 for _, params in calls))

    def test_raises_typed_limit_error_when_every_page_is_full(self):
        def api_call(_method, **params):
            return {"albumList2": {"album": [{"id": str(params["offset"])}]}}

        with self.assertRaises(AlbumInventoryLimitError) as caught:
            fetch_album_inventory(api_call, items, page_size=1, max_albums=2)

        self.assertIsInstance(caught.exception, RuntimeError)
        self.assertEqual(caught.exception.albums_retrieved, 2)
        self.assertRegex(str(caught.exception), "safety limit")

    def test_api_errors_propagate_without_partial_inventory(self):
        def api_call(*_args, **_kwargs):
            raise OSError("Navidrome unavailable")

        with self.assertRaisesRegex(OSError, "Navidrome unavailable"):
            fetch_album_inventory(api_call, items, page_size=2, max_albums=4)


if __name__ == "__main__":
    unittest.main()
