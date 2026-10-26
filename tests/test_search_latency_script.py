"""Tests for the pure helpers of the search latency script (contract P5)."""
from __future__ import annotations

import unittest

from scripts.search_latency import parse_sse, percentile, pick_queries, summarize


class _Data:
    artists = [{"name": f"Artist {i}"} for i in range(40)]
    albums = [{"name": f"Album {i}"} for i in range(40)]


class SearchLatencyHelpersTests(unittest.TestCase):
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
