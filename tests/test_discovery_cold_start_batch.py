"""Offline tests for the cold-start batch path (no provider calls)."""
import unittest
from threading import Lock
from unittest import mock

import discovery_candidate_gathering as gathering
import discovery_candidate_supply as supply
from discovery_refresh import refresh_personal
from test_discovery_batch_lookup import _Harness


class ColdStartGateTests(unittest.TestCase):
    def test_cold_start_batches_with_steady_state_flags_off(self):
        harness = _Harness(3)
        with mock.patch.object(gathering, "CF_BATCH_RESOLUTION_ENABLED", False), \
                mock.patch.object(supply, "BATCH_TITLE_FILTER_ENABLED", False):
            gathering.gather_recommendation_candidates(harness.providers(), cold_start=True)

        self.assertEqual(len(harness.posts), 1)
        self.assertEqual(len(harness.mb_client.requested), 0)

    def test_steady_state_with_flags_off_does_not_batch(self):
        harness = _Harness(3)
        with mock.patch.object(gathering, "CF_BATCH_RESOLUTION_ENABLED", False), \
                mock.patch.object(supply, "BATCH_TITLE_FILTER_ENABLED", False):
            gathering.gather_recommendation_candidates(harness.providers(), cold_start=False)

        self.assertEqual(harness.posts, [])
        self.assertEqual(len(harness.mb_client.requested), 3)

    def test_cold_start_without_post_client_does_not_batch(self):
        harness = _Harness(3)
        providers = harness.providers()
        providers = gathering.RecommendationProviders(**{**providers.__dict__, "http_post": None})
        gathering.gather_recommendation_candidates(providers, cold_start=True)

        self.assertEqual(harness.posts, [])

    def test_cold_start_switch_off_does_not_batch(self):
        harness = _Harness(3)
        with mock.patch.object(gathering, "COLD_START_BATCH_ENABLED", False):
            gathering.gather_recommendation_candidates(harness.providers(), cold_start=True)

        self.assertEqual(harness.posts, [])

    def test_cold_start_still_filters_marked_titles(self):
        self.assertEqual(
            supply.batch_title_marker_rejection("Live at the Garden", enabled=True),
            "batch_title_marker",
        )
        self.assertIsNone(supply.batch_title_marker_rejection("Live at the Garden", enabled=False))


class ColdStartRefreshTests(unittest.TestCase):
    def _refresh(self, read_previous):
        seen = []

        def recommend(**kwargs):
            seen.append(kwargs)
            return '{"recommendations": []}'

        refresh_personal(
            Lock(), recommend, lambda name, payload: None,
            read_previous=read_previous,
        )
        return seen[0]

    def test_no_stored_list_is_cold_start(self):
        self.assertEqual(self._refresh(lambda name: None).get("_cold_start"), True)

    def test_stored_list_is_not_cold_start(self):
        self.assertNotIn("_cold_start", self._refresh(lambda name: {"payload": {}}))

    def test_unreadable_store_is_not_cold_start(self):
        def broken(name):
            raise OSError("unreadable")
        self.assertNotIn("_cold_start", self._refresh(broken))

    def test_without_read_previous_behavior_is_unchanged(self):
        seen = []
        refresh_personal(Lock(), lambda **kwargs: seen.append(kwargs) or "{}", lambda n, p: None)
        self.assertEqual(seen, [{"count": 20}])


if __name__ == "__main__":
    unittest.main()
