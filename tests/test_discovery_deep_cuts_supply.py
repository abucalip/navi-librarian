import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

from discovery.deep_cuts_supply import DEEP_CUTS_RADIO_BANDS, run_deep_cuts_tag_supply

QUERIES = [("q-a", "fa", "profile:a"), ("q-b", "fb", "explore:b"), ("q-c", "fc", "explore:c")]


class Harness(unittest.TestCase):
    def setUp(self):
        self.state = {"added": 0, "seen": 0, "hits": 0, "misses": 0, "request_index": 0,
                      "unavailable": False, "exhausted_run": 0}
        self.radio_calls, self.tail_calls = [], []
        self.radio_yield = {}  # (pop_begin, query) -> (added, error_class)
        self.tail_yield = {}   # query -> (added, error_class)
        self.tail_limit = len(QUERIES)  # the real tail stops early at the cap or unavailable

    def radio(self, queries, *, providers, albums, failures, state, pop_begin, pop_end):
        self.radio_calls.append((pop_begin, pop_end, [q for q, _f, _s in queries]))
        out = []
        for query, _family, _style in queries:
            added, error = self.radio_yield.get((pop_begin, query), (0, None))
            state["added"] += added
            out.append((added, error))
            if error == "retryable":
                state["unavailable"] = True
        return out

    def tail(self, queries, *, providers, client, headers, albums, failures, state):
        self.tail_calls.append(([q for q, _f, _s in queries], state["unavailable"]))
        out = []
        for query, _family, _style in queries[:self.tail_limit]:
            added, error = self.tail_yield.get(query, (0, None))
            state["added"] += added
            out.append((added, error))
        return out

    def run_supply(self, *, http_post=object()):
        @contextmanager
        def http_client(**_kwargs):
            yield object()

        providers = SimpleNamespace(http_post=http_post, http_client=http_client)
        with mock.patch("discovery.candidate_gathering.run_radio_lane", side_effect=self.radio), \
                mock.patch("discovery.candidate_gathering._run_tag_queries", side_effect=self.tail):
            return run_deep_cuts_tag_supply(
                QUERIES, providers=providers, headers={}, albums={}, failures=[], state=self.state)


class DeepCutsSupplyTests(Harness):
    def test_bands_are_the_owner_approved_order(self):
        self.assertEqual(DEEP_CUTS_RADIO_BANDS, ((50, 75), (75, 100)))

    def test_first_band_answers_stop_later_tiers_and_tail(self):
        self.radio_yield = {(50, "q-a"): (2, None), (50, "q-b"): (1, None), (50, "q-c"): (1, None)}
        out = self.run_supply()
        self.assertEqual(out, [(2, None), (1, None), (1, None)])
        self.assertEqual(self.radio_calls, [(50, 75, ["q-a", "q-b", "q-c"])])
        self.assertEqual(self.tail_calls, [])

    def test_empty_queries_go_to_the_second_band_then_the_tail(self):
        self.radio_yield = {(50, "q-a"): (1, None), (75, "q-c"): (3, None)}
        self.tail_yield = {"q-b": (2, None)}
        out = self.run_supply()
        self.assertEqual(out, [(1, None), (2, None), (3, None)])
        self.assertEqual(self.radio_calls, [(50, 75, ["q-a", "q-b", "q-c"]), (75, 100, ["q-b", "q-c"])])
        self.assertEqual(self.tail_calls[0][0], ["q-b"])

    def test_tail_runs_for_queries_radio_could_not_fill(self):
        self.tail_yield = {"q-a": (1, None), "q-b": (0, "not_found"), "q-c": (4, None)}
        out = self.run_supply()
        self.assertEqual(out[0], (1, None))
        self.assertEqual(out[1], (0, "not_found"))
        self.assertEqual(out[2], (4, None))
        self.assertEqual(self.tail_calls[0][0], ["q-a", "q-b", "q-c"])

    def test_radio_unavailable_does_not_stop_the_musicbrainz_tail(self):
        self.radio_yield = {(50, "q-a"): (0, "retryable")}
        self.tail_yield = {"q-a": (2, None)}
        out = self.run_supply()
        self.assertEqual(out[0], (2, None))
        self.assertEqual(self.tail_calls[0][1], False, "tail starts with the radio flag cleared")

    def test_retryable_first_tier_skips_the_second_radio_tier_but_runs_the_tail(self):
        self.radio_yield = {(50, "q-a"): (0, "retryable"), (50, "q-b"): (0, "retryable")}
        self.tail_yield = {"q-a": (1, None), "q-b": (2, None)}
        out = self.run_supply()
        self.assertEqual(self.radio_calls, [(50, 75, ["q-a", "q-b", "q-c"])], "no 75-100 radio call")
        self.assertEqual(self.tail_calls[0][0], ["q-a", "q-b", "q-c"])
        self.assertEqual(out, [(1, None), (2, None), (0, None)])

    def test_without_http_post_the_tail_serves_every_query(self):
        self.tail_yield = {"q-a": (1, None)}
        out = self.run_supply(http_post=None)
        self.assertEqual(self.radio_calls, [])
        self.assertEqual(self.tail_calls[0][0], ["q-a", "q-b", "q-c"])
        self.assertEqual(out[0], (1, None))

    def test_queries_the_tail_never_attempts_stay_marked_not_attempted(self):
        self.tail_limit = 1
        self.tail_yield = {"q-a": (1, None)}
        out = self.run_supply(http_post=None)
        self.assertEqual(out, [(1, None), (0, "not_attempted"), (0, "not_attempted")])


if __name__ == "__main__":
    unittest.main()
