"""Tests for the pure helpers of the search latency script (contract P5)."""
from __future__ import annotations

import unittest

from scripts.search_latency import parse_sse, percentile, pick_queries, summarize, validate_isolated_data_dir


class _Data:
    artists = [{"name": f"Artist {i}"} for i in range(40)]
    albums = [{"name": f"Album {i}"} for i in range(40)]


class SearchLatencyHelpersTests(unittest.TestCase):
    def test_isolated_data_dir_requires_existing_copy_outside_repository(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        root = Path(__file__).resolve().parent.parent
        with self.assertRaisesRegex(ValueError, "Set NAVIDROME_LIBRARIAN_DATA_DIR"):
            validate_isolated_data_dir(None, root)
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            validate_isolated_data_dir(str(root), root)
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "copied navidrome_discovery.sqlite3"):
                validate_isolated_data_dir(temporary, root)
            Path(temporary, "navidrome_discovery.sqlite3").touch()
            with self.assertRaisesRegex(ValueError, "confirm it is isolated"):
                validate_isolated_data_dir(temporary, root)
            Path(temporary, ".navi-librarian-search-latency-isolated").touch()
            self.assertEqual(validate_isolated_data_dir(temporary, root), Path(temporary).resolve())

    def test_percentile_is_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(percentile(values, 0.95), 95)
        self.assertEqual(percentile(values, 0.50), 50)
        self.assertEqual(percentile([7], 0.95), 7)
        self.assertIsNone(percentile([], 0.95))

    def test_summarize_empty_has_no_numbers(self):
        self.assertEqual(summarize([]), {"n": 0, "p50": None, "p95": None, "max": None})

    def test_parse_sse_yields_each_event_once(self):
        lines = ["event: result", 'data: {"a": 1}', "", "event: done", 'data: {"b": 2}', ""]
        self.assertEqual(list(parse_sse(lines)), [("result", {"a": 1}), ("done", {"b": 2})])

    def test_parse_sse_drops_an_unterminated_event(self):
        self.assertEqual(list(parse_sse(["event: result", 'data: {"a": 1}'])), [])

    def test_pick_queries_adds_a_prefix_and_is_bounded(self):
        queries = pick_queries(_Data, 10)
        self.assertLessEqual(len(queries), 20)
        self.assertTrue(any(q.startswith("Artist") and len(q) < len("Artist 0") + 1 for q in queries))
        self.assertEqual(len(queries) % 2, 0)


if __name__ == "__main__":
    unittest.main()
