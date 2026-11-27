"""Direct-import tests for discovery.new_count (Bento B0)."""
from datetime import datetime, timezone
import unittest

from discovery.new_count import count_new_items, parse_since


class DiscoveryNewCountTests(unittest.TestCase):
    def test_parse_since_accepts_utc_offset_and_naive_iso(self):
        expected = datetime(2026, 11, 27, 8, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(parse_since("2026-11-27T08:30:00Z"), expected)
        self.assertEqual(parse_since("2026-11-27T08:30:00+00:00"), expected)
        self.assertEqual(parse_since("2026-11-27T09:30:00+01:00"), expected)
        self.assertEqual(parse_since("2026-11-27T08:30:00"), expected)

    def test_parse_since_rejects_empty_and_invalid_values(self):
        for bad in ("", "   ", "not-a-date", "2026-13-45"):
            with self.assertRaises(ValueError):
                parse_since(bad)

    def test_count_new_items_uses_list_generated_at(self):
        payload = {
            "generated_at": "2026-11-27T10:00:00Z",
            "items": [{"artist": "A", "album": "1"}, {"artist": "B", "album": "2"}],
        }
        self.assertEqual(count_new_items(payload, parse_since("2026-11-27T09:00:00Z")), 2)
        self.assertEqual(count_new_items(payload, parse_since("2026-11-27T10:00:00Z")), 0)
        self.assertEqual(count_new_items(payload, parse_since("2026-11-27T11:00:00Z")), 0)

    def test_count_new_items_prefers_per_item_timestamp(self):
        payload = {
            "generated_at": "2026-11-27T08:00:00Z",
            "items": [
                {"artist": "A", "album": "Old", "added_at": "2026-11-27T07:00:00Z"},
                {"artist": "B", "album": "New", "added_at": "2026-11-27T10:00:00Z"},
                {"artist": "C", "album": "Fallback"},
            ],
        }
        self.assertEqual(count_new_items(payload, parse_since("2026-11-27T09:00:00Z")), 1)
        self.assertEqual(count_new_items(payload, parse_since("2026-11-27T07:30:00Z")), 2)

    def test_count_new_items_returns_zero_for_disabled_empty_or_ungenerated(self):
        since = parse_since("2026-11-27T09:00:00Z")
        self.assertEqual(count_new_items({"disabled": True, "generated_at": "2026-11-27T12:00:00Z", "items": [{}]}, since), 0)
        self.assertEqual(count_new_items({"generated_at": None, "items": [{}]}, since), 0)
        self.assertEqual(count_new_items({"generated_at": "2026-11-27T12:00:00Z", "items": []}, since), 0)


if __name__ == "__main__":
    unittest.main()
