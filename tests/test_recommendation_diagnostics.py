import json
import tempfile
import unittest
from pathlib import Path

from discovery_store import record_recommendation_pool_diagnostic
from recommendation_diagnostics import evaluate_replay_fixture, jaccard_overlap


class RecommendationDiagnosticsTests(unittest.TestCase):
    def test_pool_jaccard_and_empty_pool(self):
        self.assertAlmostEqual(jaccard_overlap(["a", "b"], ["b", "c"]), 1 / 3)
        self.assertIsNone(jaccard_overlap([], []))

    def test_pool_diagnostic_persists_only_hashes_and_compares_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "diagnostics.sqlite3"
            first = record_recommendation_pool_diagnostic(
                db, ["recording-a", "recording-b"], ["Artist|Album"],
                {"cf_recordings_returned": 2, "cf_recordings_resolved": 1, "resolved_album_count": 1},
                generated_at=100,
            )
            second = record_recommendation_pool_diagnostic(
                db, ["recording-b", "recording-c"], ["Artist|Album"],
                {"cf_recordings_returned": 2, "cf_recordings_resolved": 2, "resolved_album_count": 2},
                generated_at=200,
            )
            self.assertIsNone(first["cf_recording_jaccard_previous"])
            self.assertAlmostEqual(second["cf_recording_jaccard_previous"], 1 / 3)
            self.assertEqual(second["final_list_jaccard_previous"], 1.0)
            import sqlite3
            with sqlite3.connect(db) as connection:
                row = connection.execute("SELECT recording_hashes_json FROM recommendation_pool_diagnostics").fetchone()
            self.assertNotIn("recording-b", row[0])

    def test_frozen_replay_metrics_are_deterministic_and_exclude_owned_artists(self):
        fixture_path = Path(__file__).parent / "fixtures" / "recommendation_replay.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        first = evaluate_replay_fixture(fixture, k=10)
        self.assertEqual(first, evaluate_replay_fixture(fixture, k=10))
        self.assertEqual(first["case_count"], 2)
        self.assertEqual(first["cases"][0]["owned_artist_recommendations_excluded"], 1)
        self.assertAlmostEqual(first["mean_candidate_pool_overlap"], 1 / 3)
        self.assertAlmostEqual(first["mean_ranking_overlap"], 1 / 6)


if __name__ == "__main__":
    unittest.main()
