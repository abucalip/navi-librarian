"""Synthetic tests: the tag-lane early stop is off by default and continues past single exhaustions only when enabled."""
import unittest
from unittest import mock

import discovery_candidate_gathering as gathering
from test_discovery_candidate_replenishment import (
    BASE_QUERIES,
    EXTRA_QUERIES,
    ReplenishmentTests,
    _group,
)

_HELPER = ReplenishmentTests(methodName="test_meeting_the_target_issues_no_extra_queries")


def _run(responses, *, cf_artists=(("Alpha", "A1"),), shortlist_target=10):
    return _HELPER._run(
        cf_artists=list(cf_artists), responses=responses, shortlist_target=shortlist_target,
    )


def _empty_responses():
    return {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}


class TagLaneEarlyStopTests(unittest.TestCase):
    def test_flag_is_off_by_default(self):
        self.assertFalse(gathering.TAG_LANE_EARLY_STOP_ENABLED)
        self.assertEqual(gathering.TAG_LANE_EXHAUSTION_THRESHOLD, 2)

    def test_flag_off_stops_at_first_exhausted_query(self):
        responses = _empty_responses()
        responses["q-base-1"] = 503

        _result, mb_client = _run(responses)

        self.assertNotIn("q-base-2", mb_client.queries)
        self.assertNotIn("q-extra-1", mb_client.queries)

    def test_flag_on_continues_past_a_single_exhausted_query(self):
        responses = _empty_responses()
        responses["q-base-1"] = 503
        responses["q-base-2"] = [_group("Beta", "B2")]

        with mock.patch.object(gathering, "TAG_LANE_EARLY_STOP_ENABLED", True):
            result, mb_client = _run(responses)

        self.assertIn("q-base-2", mb_client.queries)
        self.assertNotIsInstance(result, str)

    def test_flag_on_stops_after_consecutive_exhausted_queries(self):
        responses = _empty_responses()
        responses["q-base-1"] = 503
        responses["q-base-2"] = 503
        responses["q-extra-1"] = [_group("Gamma", "G2")]

        with mock.patch.object(gathering, "TAG_LANE_EARLY_STOP_ENABLED", True):
            result, mb_client = _run(responses, shortlist_target=10)

        self.assertNotIn("q-extra-1", mb_client.queries)
        self.assertFalse(result["candidate_supply"]["replenishment"]["triggered"])

    def test_flag_on_success_resets_the_exhausted_run(self):
        responses = _empty_responses()
        responses["q-base-1"] = 503
        responses["q-base-2"] = []
        responses["q-extra-1"] = 503
        responses["q-extra-2"] = [_group("Delta", "D2")]

        with mock.patch.object(gathering, "TAG_LANE_EARLY_STOP_ENABLED", True):
            result, mb_client = _run(responses, shortlist_target=10)

        self.assertIn("q-extra-2", mb_client.queries)
        summary = result["candidate_supply"]["replenishment"]
        self.assertTrue(summary["triggered"])
        self.assertEqual(summary["extra_candidates_added"], 1)

    def test_flag_on_request_count_stays_bounded(self):
        responses = _empty_responses()
        for query, _f, _s in BASE_QUERIES + EXTRA_QUERIES:
            responses[query] = 503

        with mock.patch.object(gathering, "TAG_LANE_EARLY_STOP_ENABLED", True):
            _result, mb_client = _run(responses, shortlist_target=10)

        # Each query makes at most the bounded retry attempts; the lane stops after
        # the threshold of consecutive exhaustions, so later queries are never sent.
        self.assertLessEqual(len(mb_client.queries), 2 * gathering.TAG_LANE_EXHAUSTION_THRESHOLD)
        self.assertNotIn("q-extra-2", mb_client.queries)


if __name__ == "__main__":
    unittest.main()
