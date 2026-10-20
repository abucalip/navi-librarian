import unittest

import recommendation_run_metrics as metrics


class RunMetricsTests(unittest.TestCase):
    def setUp(self):
        metrics.snapshot_and_reset()

    def test_counts_calls_by_provider_and_type(self):
        metrics.record_provider_call("lastfm", "api")
        metrics.record_provider_call("lastfm", "api")
        metrics.record_provider_call("musicbrainz", "release_group_rating")
        snap = metrics.snapshot_and_reset()
        self.assertEqual(
            snap["provider_calls"],
            {"lastfm.api": 2, "musicbrainz.release_group_rating": 1},
        )

    def test_snapshot_resets_counters(self):
        metrics.record_provider_call("lastfm", "api")
        metrics.snapshot_and_reset()
        self.assertEqual(metrics.snapshot_and_reset()["provider_calls"], {})

    def test_stage_timer_accumulates_seconds(self):
        with metrics.stage_timer("gather"):
            pass
        snap = metrics.snapshot_and_reset()
        self.assertIn("gather", snap["stage_seconds"])
        self.assertGreaterEqual(snap["stage_seconds"]["gather"], 0.0)


if __name__ == "__main__":
    unittest.main()
