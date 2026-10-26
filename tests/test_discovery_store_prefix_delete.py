"""Prefix delete of cached search entries, against a real SQLite file (contract section 5.2)."""

import tempfile
import unittest
from pathlib import Path

from discovery import store
from discovery.search.cache import purge_stale_generations


class PrefixDeleteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "discovery.sqlite3"
        for name in (
            "search:lastfm:1:ash:artist:depth50",
            "search:lastfm:2:ash:artist:depth50",
            "search:lastfm:10:ash:artist:depth50",
            "search:musicbrainz:0:ash:artist:depth50",
            "library_snapshot:navidrome1",
        ):
            store.write_list(self.db, name, {"x": 1})

    def tearDown(self):
        self.tmp.cleanup()

    def names_left(self):
        return sorted(
            name for name in ("search:lastfm:1:ash:artist:depth50", "search:lastfm:2:ash:artist:depth50",
                              "search:lastfm:10:ash:artist:depth50", "search:musicbrainz:0:ash:artist:depth50",
                              "library_snapshot:navidrome1")
            if store.read_list(self.db, name) is not None
        )

    def test_removes_other_generations_only(self):
        removed = store.delete_prefix_except(self.db, "search:lastfm:", "search:lastfm:2:")
        self.assertEqual(removed, 2)
        self.assertIsNotNone(store.read_list(self.db, "search:lastfm:2:ash:artist:depth50"))
        self.assertIsNone(store.read_list(self.db, "search:lastfm:1:ash:artist:depth50"))

    def test_generation_1_does_not_keep_generation_10(self):
        # "search:lastfm:1:" is not a prefix of "search:lastfm:10:", so generation 10 is removed.
        store.delete_prefix_except(self.db, "search:lastfm:", "search:lastfm:1:")
        self.assertIsNotNone(store.read_list(self.db, "search:lastfm:1:ash:artist:depth50"))
        self.assertIsNone(store.read_list(self.db, "search:lastfm:10:ash:artist:depth50"))

    def test_other_sources_and_unrelated_lists_are_untouched(self):
        store.delete_prefix_except(self.db, "search:lastfm:", "search:lastfm:2:")
        self.assertIsNotNone(store.read_list(self.db, "search:musicbrainz:0:ash:artist:depth50"))
        self.assertIsNotNone(store.read_list(self.db, "library_snapshot:navidrome1"))

    def test_prefix_is_compared_as_text_not_as_a_like_pattern(self):
        store.write_list(self.db, "search:li%ka:9:x", {"x": 1})
        store.write_list(self.db, "search:likaa:9:x", {"x": 1})
        store.delete_prefix_except(self.db, "search:li%ka:", "search:li%ka:9:")
        self.assertIsNotNone(store.read_list(self.db, "search:likaa:9:x"))

    def test_keep_prefix_must_start_with_the_prefix(self):
        with self.assertRaises(ValueError):
            store.delete_prefix_except(self.db, "search:lastfm:", "search:musicbrainz:0:")

    def test_purge_helper_uses_the_source_and_generation(self):
        calls = []
        purge_stale_generations(lambda prefix, keep: calls.append((prefix, keep)) or 0, "lastfm", 4)
        self.assertEqual(calls, [
            ("search:lastfm:", "search:lastfm:4:"),
            ("genre:lastfm:", "genre:lastfm:4:"),
        ])


class PrefixReadAndBatchWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "discovery.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_prefix_returns_only_matching_lists_and_skips_malformed_json(self):
        store.write_list(self.db, "identity:navidrome1:artist:ar1", {"mbid": "a"})
        store.write_list(self.db, "identity:navidrome1:album:al1", {"release_group_mbid": "b"})
        store.write_list(self.db, "identity:navidrome2:artist:ar1", {"mbid": "c"})
        found = store.read_prefix(self.db, "identity:navidrome1:")
        self.assertEqual(sorted(found), ["identity:navidrome1:album:al1", "identity:navidrome1:artist:ar1"])

    def test_write_many_stores_every_list_and_overwrites_existing_ones(self):
        store.write_list(self.db, "identity:navidrome1:artist:ar1", {"mbid": "old"})
        store.write_many(self.db, {
            "identity:navidrome1:artist:ar1": {"mbid": "new"},
            "identity:navidrome1:artist:ar2": {"mbid": "b"},
        })
        found = store.read_prefix(self.db, "identity:navidrome1:")
        self.assertEqual(found["identity:navidrome1:artist:ar1"], {"mbid": "new"})
        self.assertEqual(found["identity:navidrome1:artist:ar2"], {"mbid": "b"})

    def test_write_many_with_nothing_to_write_is_a_no_op(self):
        store.write_many(self.db, {})
        self.assertEqual(store.read_prefix(self.db, ""), {})


if __name__ == "__main__":
    unittest.main()
