"""Offline tests for the cold-start batch path (no provider calls)."""
import unittest
from threading import Lock
from unittest import mock

import discovery_candidate_gathering as gathering
from discovery import candidate_supply as supply
from discovery.refresh import refresh_personal
from test_discovery_batch_lookup import _Harness


class ColdStartGateTests(unittest.TestCase):
    def test_cold_start_batches_with_warm_switch_off(self):
        harness = _Harness(3)
        gathering.gather_recommendation_candidates(harness.providers(), cold_start=True)

        self.assertEqual(len(harness.posts), 1)
        self.assertEqual(len(harness.mb_client.requested), 0)

    def test_steady_state_with_warm_switch_off_does_not_batch(self):
        harness = _Harness(3)
        with mock.patch.object(gathering, "WARM_BATCH_ENABLED", False):
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
            supply.batch_title_marker_rejection("Live at the Garden"), "batch_title_marker",
        )


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


class _CachingHarness(_Harness):
    """Harness whose metadata cache actually stores values."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = {}

    def providers(self):
        base = super().providers()
        return gathering.RecommendationProviders(**{
            **base.__dict__,
            "metadata_cache_get": lambda key, **kw: self.store.get(key),
            "metadata_cache_set": lambda key, value, **kw: self.store.__setitem__(key, value),
        })


class WarmBatchTests(unittest.TestCase):
    def test_warm_path_batches_by_default_and_skips_per_recording_calls(self):
        harness = _Harness(3)
        gathering.gather_recommendation_candidates(harness.providers(), cold_start=False)

        self.assertEqual(len(harness.posts), 1)
        self.assertEqual(harness.mb_client.requested, [])

    def test_warm_switch_off_does_not_batch(self):
        harness = _Harness(3)
        with mock.patch.object(gathering, "WARM_BATCH_ENABLED", False):
            gathering.gather_recommendation_candidates(harness.providers(), cold_start=False)

        self.assertEqual(harness.posts, [])
        self.assertEqual(len(harness.mb_client.requested), 3)

    def test_batch_hits_are_cached_under_their_own_key(self):
        harness = _CachingHarness(3)
        gathering.gather_recommendation_candidates(harness.providers(), cold_start=True)

        prefix = gathering.BATCH_RECORDING_CACHE_PREFIX
        self.assertEqual(sorted(k for k in harness.store if k.startswith(prefix)),
                         [f"{prefix}rec-{i}" for i in range(3)])
        # Never the key the full per-recording lookup trusts.
        self.assertFalse(any(k.startswith("mb:recording:") for k in harness.store))

    def test_second_run_reuses_cached_batch_hits_without_any_lookup(self):
        harness = _CachingHarness(3)
        gathering.gather_recommendation_candidates(harness.providers(), cold_start=True)
        posts_after_first = len(harness.posts)
        gets_after_first = len(harness.rg_gets)

        result = gathering.gather_recommendation_candidates(harness.providers(), cold_start=False)

        self.assertEqual(len(harness.posts), posts_after_first)
        self.assertEqual(len(harness.rg_gets), gets_after_first)
        self.assertEqual(harness.mb_client.requested, [])
        self.assertEqual(len(result["albums"]), 3)

    def test_cached_batch_hits_do_not_spend_the_budget_on_a_larger_pool(self):
        harness = _CachingHarness(150)
        gathering.gather_recommendation_candidates(harness.providers(), cold_start=True)
        harness.posts.clear()

        gathering.gather_recommendation_candidates(harness.providers(), cold_start=False)

        self.assertEqual(harness.posts, [])
        self.assertEqual(harness.mb_client.requested, [])

    def test_cache_write_failure_does_not_fail_the_run(self):
        harness = _Harness(2)
        base = harness.providers()

        def broken(key, value, **kw):
            raise OSError("disk full")

        providers = gathering.RecommendationProviders(**{**base.__dict__, "metadata_cache_set": broken})
        result = gathering.gather_recommendation_candidates(providers, cold_start=True)

        self.assertEqual(len(result["albums"]), 2)
