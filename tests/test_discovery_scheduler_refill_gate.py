"""Regression tests for the scheduler's automatic-refill gate (roadmap 3.4).

These run one cycle of the real scheduler loop. The sleep after the cycle raises
a non-Exception to break out of the infinite loop, and the settings, cache read,
and refresh callbacks are replaced with recorders.
"""
import unittest
from unittest.mock import patch

import navidrome_server as server


class _StopScheduler(BaseException):
    """Raised from the patched sleep to end the scheduler loop after one cycle."""


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

        with patch.object(server, "_discovery_settings_read", lambda: settings), \
                patch.object(server, "_discovery_read_list", read_list), \
                patch.object(server, "_discovery_scheduler_refresh_one", refresh_one), \
                patch.object(server.time, "sleep", side_effect=_StopScheduler):
            with self.assertRaises(_StopScheduler):
                server._discovery_scheduler()
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
