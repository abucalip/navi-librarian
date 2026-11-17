"""Regression tests for the scheduler's automatic-refill gate (roadmap 3.4).

These run one pass of the discovery scheduler, now the worker's ``discovery_lists`` entry
(``app/services/discovery_schedule.py``, efficiency W3). The settings, cache read, and refresh
callbacks are replaced with recorders on a stand-in librarian.
"""
import unittest
from types import SimpleNamespace

from app.services import discovery_schedule


class SchedulerRefillGateTests(unittest.TestCase):
    EXPECTED_LISTS = (
        "personal", "classics", "artist_deep_dive", "new_releases",
        "listening_profile",
    )

    def run_one_cycle(self, settings):
        reads, refreshes = [], []

        def read_list(list_name):
            reads.append(list_name)
            return None

        def refresh_one(list_name):
            refreshes.append(list_name)
            return {"ok": True}

        librarian = SimpleNamespace(
            _discovery_settings_read=lambda: settings,
            _discovery_read_list=read_list,
            _discovery_scheduler_refresh_one=refresh_one,
        )
        discovery_schedule.refresh_stale_lists_once(librarian)
        return reads, refreshes

    def test_disabled_switch_reads_no_caches_and_refreshes_nothing(self):
        reads, refreshes = self.run_one_cycle({"automatic_refill_enabled": False})
        self.assertEqual(reads, [])
        self.assertEqual(refreshes, [])

    def test_enabled_switch_refreshes_every_stale_list_in_order(self):
        reads, refreshes = self.run_one_cycle({"automatic_refill_enabled": True})
        self.assertEqual(reads, list(self.EXPECTED_LISTS))
        self.assertEqual(refreshes, list(self.EXPECTED_LISTS))

    def test_missing_switch_defaults_to_enabled(self):
        reads, refreshes = self.run_one_cycle({})
        self.assertEqual(reads, list(self.EXPECTED_LISTS))
        self.assertEqual(refreshes, list(self.EXPECTED_LISTS))

    def test_corrupt_switch_value_defaults_to_enabled(self):
        reads, refreshes = self.run_one_cycle({"automatic_refill_enabled": "false"})
        self.assertEqual(refreshes, list(self.EXPECTED_LISTS))


if __name__ == "__main__":
    unittest.main()
