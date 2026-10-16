"""Direct-import regressions for dashboard pick assembly."""

import unittest

from app.services.dashboard import build_dashboard_picks


class DashboardPickServiceTests(unittest.TestCase):
    def setUp(self):
        self.lists = {
            "personal": {"items": [{"artist": "Artist A", "album": "Album A"}]},
            "classics": {"items": [{"artist": "Artist B", "album": "Album B"}]},
            "artist_deep_dive": {"items": [{"artist": "Artist C", "album": "Album C"}]},
        }
        self.calls = []

    def read_list(self, name, count):
        self.calls.append((name, count))
        return self.lists[name]

    @staticmethod
    def no_shuffle(values):
        return None

    def test_balances_categories_and_preserves_read_contract(self):
        result = build_dashboard_picks(
            self.read_list, lambda item: True, 3, shuffle=self.no_shuffle
        )
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["pool_size"], 3)
        self.assertEqual(
            {item["dashboard_category"] for item in result["items"]},
            {"Personal discoveries", "Add to your collection", "Artist Deep Dives"},
        )
        self.assertEqual(self.calls, [
            ("personal", 150), ("classics", 150), ("artist_deep_dive", 150),
        ])

    def test_deduplicates_case_insensitively_and_filters_ineligible_items(self):
        self.lists["classics"] = {"recommendations": [
            {"artist": " artist a ", "album": "album a"},
            {"artist": "Artist D", "album": "Exclude"},
            {"artist": "Artist D", "album": "Album D"},
        ]}
        result = build_dashboard_picks(
            self.read_list, lambda item: item.get("album") != "Exclude",
            20, shuffle=self.no_shuffle,
        )
        identities = [
            (item["artist"].casefold(), item["album"].casefold())
            for item in result["items"]
        ]
        self.assertEqual(result["pool_size"], 3)
        self.assertEqual(len(identities), len(set(identities)))
        self.assertNotIn(("artist d", "exclude"), identities)
        self.assertIn(("artist a", "album a"), identities)

    def test_failed_lane_is_skipped_and_remaining_lanes_survive(self):
        def read_with_failure(name, count):
            if name == "classics":
                raise RuntimeError("upstream detail must not escape")
            return self.read_list(name, count)

        result = build_dashboard_picks(
            read_with_failure, lambda item: True, 10, shuffle=self.no_shuffle
        )
        self.assertEqual(result["pool_size"], 2)
        self.assertEqual(result["count"], 2)

    def test_invalid_payload_rows_and_missing_identity_are_ignored(self):
        self.lists["personal"] = {"items": [
            "bad", {"artist": "", "album": "No artist"},
            {"artist": "Artist A", "album": "Album A"},
        ]}
        result = build_dashboard_picks(
            self.read_list, lambda item: True, 10, shuffle=self.no_shuffle
        )
        self.assertEqual(result["pool_size"], 3)
        self.assertTrue(all(item["artist"] and item["album"] for item in result["items"]))


if __name__ == "__main__":
    unittest.main()
