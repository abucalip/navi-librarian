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


    def test_add_stage_seconds_accumulates_measured_time(self):
        metrics.add_stage_seconds("resolution", 1.25)
        metrics.add_stage_seconds("resolution", 0.5)
        self.assertEqual(metrics.snapshot_and_reset()["stage_seconds"], {"resolution": 1.75})

    def test_record_count_accumulates_integers_and_resets(self):
        metrics.record_count("save_seed.saved_artists", 2)
        metrics.record_count("save_seed.saved_artists")
        self.assertEqual(metrics.snapshot_and_reset()["counts"], {"save_seed.saved_artists": 3})
        self.assertEqual(metrics.snapshot_and_reset()["counts"], {})


if __name__ == "__main__":
    unittest.main()


class TimedStageTests(unittest.TestCase):
    def test_decorator_records_stage_and_returns_value(self):
        metrics.snapshot_and_reset()

        @metrics.timed_stage("unit_stage")
        def add(a, b):
            return a + b

        self.assertEqual(add(2, 3), 5)
        self.assertIn("unit_stage", metrics.snapshot_and_reset()["stage_seconds"])
