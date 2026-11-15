"""Discovery mode (Star Operation S4a): setting, balanced regression, knob wiring."""
import json
import unittest

from discovery.discovery_mode import (
    BALANCED, DEFAULT_DISCOVERY_MODE, DISCOVERY_MODES, DiscoveryKnobs,
    discovery_knobs, discovery_mode_value, knobs_for_mode,
)
from discovery.lenses import (
    CURRENT_TASTES, DEEP_CUTS, GENRE_SPREAD, partition_lenses, run_lens,
)
from discovery.selection_policy import quota_targets, selection_request_options
from settings.service import get_discovery_mode_settings, set_discovery_mode_settings
from tests.test_discovery_lenses import item


def _pool():
    return [item(f"c{i}", audience=[100, 400, 5000, 60_000, 900_000][i % 5],
                 strength=1.0 - i / 40, genre=f"g{i % 4}",
                 category=("adjacent", "cross_genre", "adventurous")[i % 3]) for i in range(20)]


class ModeSettingTests(unittest.TestCase):
    def test_absent_invalid_and_unreadable_values_mean_balanced(self):
        self.assertEqual(discovery_mode_value(lambda: {}), "balanced")
        for bad in ("", "BALANCED", "wild", 3, None, ["deeper"], True):
            self.assertEqual(discovery_mode_value(lambda bad=bad: {"discovery_mode": bad}), "balanced")

        def broken():
            raise RuntimeError("settings unavailable")
        self.assertEqual(discovery_mode_value(broken), "balanced")
        self.assertIs(discovery_knobs(broken), BALANCED)
        self.assertIs(discovery_knobs(None), BALANCED)

    def test_known_modes_round_trip(self):
        for mode in DISCOVERY_MODES:
            self.assertEqual(discovery_mode_value(lambda mode=mode: {"discovery_mode": mode}), mode)
        self.assertEqual(DEFAULT_DISCOVERY_MODE, "balanced")

    def test_get_and_set_payloads(self):
        self.assertEqual(json.loads(get_discovery_mode_settings(lambda: {})),
                         {"discovery_mode": "balanced", "modes": ["safer", "balanced", "deeper"]})
        written = []
        result = json.loads(set_discovery_mode_settings(written.append, "deeper"))
        self.assertTrue(result["ok"])
        self.assertEqual(written, [{"discovery_mode": "deeper"}])

    def test_set_refuses_unknown_values_without_writing(self):
        written = []
        for bad in ("wild", "", None, 1, "Balanced"):
            self.assertFalse(json.loads(set_discovery_mode_settings(written.append, bad))["ok"])
        self.assertEqual(written, [])


class BalancedRegressionTests(unittest.TestCase):
    """balanced matches the output with the setting absent, and today's numbers."""

    def test_every_mode_currently_carries_the_balanced_knobs(self):
        for mode in DISCOVERY_MODES:
            self.assertIs(knobs_for_mode(mode), BALANCED)

    def test_selection_options_match_with_setting_absent_and_balanced(self):
        for policy in ("quota", "family_coverage"):
            for count in (1, 5, 7, 10, 20):
                absent = selection_request_options(policy, count)
                balanced = selection_request_options(
                    policy, count, discovery_knobs(lambda: {"discovery_mode": "balanced"}))
                self.assertEqual(absent, balanced)
        self.assertEqual(selection_request_options("quota", 10), (quota_targets(10), {}))
        for count in (1, 5, 10, 20):
            self.assertEqual(selection_request_options("family_coverage", count)[1]["category_floors"],
                             {"adventurous": count // 5})

    def test_lens_results_match_with_setting_absent_and_balanced(self):
        pool = _pool()
        balanced = discovery_knobs(lambda: {"discovery_mode": "balanced"})
        for lens in (DEEP_CUTS, CURRENT_TASTES, GENRE_SPREAD):
            self.assertEqual(run_lens(lens, pool, 5), run_lens(lens, pool, 5, knobs=balanced))
        self.assertEqual(partition_lenses(pool, 3), partition_lenses(pool, 3, knobs=balanced))


class KnobWiringTests(unittest.TestCase):
    def test_floor_knob_moves_only_the_family_coverage_floor(self):
        knobs = DiscoveryKnobs(adventurous_floor_divisor=2)
        self.assertEqual(selection_request_options("family_coverage", 10, knobs)[1]["category_floors"],
                         {"adventurous": 5})
        self.assertEqual(selection_request_options("quota", 10, knobs), (quota_targets(10), {}))

    def test_band_scale_moves_gate_lenses_and_leaves_the_definitions_alone(self):
        pool = [item("mid", audience=40_000, strength=0.9), item("small", audience=100, strength=0.8)]
        self.assertEqual(run_lens(DEEP_CUTS, pool, 2).selected_candidate_ids, ("mid",))
        wide = DiscoveryKnobs(audience_min_scale=0.1, audience_max_scale=0.5)
        # max 50_000 * 0.5 = 25_000 drops "mid"; min 300 * 0.1 = 30 admits "small".
        self.assertEqual(run_lens(DEEP_CUTS, pool, 2, knobs=wide).selected_candidate_ids, ("small",))
        self.assertEqual((DEEP_CUTS.min_audience, DEEP_CUTS.max_audience), (300, 50_000))

    def test_unknown_audience_is_never_obscure_in_any_scale(self):
        pool = [item("none", strength=0.9)]
        for knobs in (BALANCED, DiscoveryKnobs(audience_min_scale=0.0, audience_max_scale=100.0)):
            self.assertEqual(run_lens(DEEP_CUTS, pool, 1, knobs=knobs).selected_candidate_ids, ())

    def test_knobs_reach_partition_lenses(self):
        pool = [item("mid", audience=40_000, strength=0.9)]
        self.assertEqual(partition_lenses(pool, 1, (DEEP_CUTS,))[0].selected_candidate_ids, ("mid",))
        narrow = DiscoveryKnobs(audience_max_scale=0.5)
        self.assertEqual(partition_lenses(pool, 1, (DEEP_CUTS,), knobs=narrow)[0].selected_candidate_ids, ())


class ModeRouteTests(unittest.TestCase):
    def setUp(self):
        from app.api import settings as routes
        self.routes = routes
        self.store = {}

        class Librarian:
            _discovery_settings_read = staticmethod(lambda: dict(self.store))
            _discovery_settings_write = staticmethod(lambda values: self.store.update(values))
        self.librarian = Librarian()

    def test_get_defaults_to_balanced_then_put_round_trips(self):
        self.assertEqual(self.routes.get_discovery_mode_settings(self.librarian)["discovery_mode"], "balanced")
        self.assertTrue(self.routes.set_discovery_mode_settings({"discovery_mode": "safer"}, self.librarian)["ok"])
        self.assertEqual(self.routes.get_discovery_mode_settings(self.librarian)["discovery_mode"], "safer")

    def test_put_rejects_unknown_mode_without_writing(self):
        from fastapi import HTTPException
        for payload in ({"discovery_mode": "wild"}, {}):
            with self.assertRaises(HTTPException) as caught:
                self.routes.set_discovery_mode_settings(payload, self.librarian)
            self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.store, {})

    def test_stored_invalid_value_reads_as_balanced(self):
        self.store["discovery_mode"] = "wild"
        self.assertEqual(self.routes.get_discovery_mode_settings(self.librarian)["discovery_mode"], "balanced")


if __name__ == "__main__":
    unittest.main()
