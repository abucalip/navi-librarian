import json
import tempfile
import unittest
from pathlib import Path

from discovery_store import (
    record_discovery_refresh_outcome,
    record_recommendation_pool_diagnostic,
)
from recommendation_diagnostics import (
    evaluate_replay_fixture, jaccard_overlap, summarize_candidate_diagnostics,
)


class RecommendationDiagnosticsTests(unittest.TestCase):
    def test_refresh_outcome_keeps_latest_manual_and_scheduler_states_without_details(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "diagnostics.sqlite3"
            first = record_discovery_refresh_outcome(
                db, list_name="personal", origin="manual", status="error",
                generated_at=100, error_type="RuntimeError",
            )
            record_discovery_refresh_outcome(
                db, list_name="personal", origin="manual", status="success",
                generated_at=200, item_count=10,
            )
            scheduled = record_discovery_refresh_outcome(
                db, list_name="personal", origin="scheduler", status="already_running",
                generated_at=201,
            )
            self.assertEqual(first["status"], "error")
            self.assertEqual(scheduled["origin"], "scheduler")
            import sqlite3
            with sqlite3.connect(db) as connection:
                rows = connection.execute(
                    "SELECT origin, status, generated_at, item_count, error_type "
                    "FROM discovery_refresh_outcomes ORDER BY origin"
                ).fetchall()
            self.assertEqual(rows, [
                ("manual", "success", 200.0, 10, None),
                ("scheduler", "already_running", 201.0, None, None),
            ])

    def test_refresh_outcome_rejects_unbounded_origin_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "diagnostics.sqlite3"
            with self.assertRaises(ValueError):
                record_discovery_refresh_outcome(
                    db, list_name="personal", origin="https://private.example/token",
                    status="error",
                )
            with self.assertRaises(ValueError):
                record_discovery_refresh_outcome(
                    db, list_name="personal", origin="manual", status="failed with secret",
                )

    def test_pool_jaccard_and_empty_pool(self):
        self.assertEqual(jaccard_overlap(["a", "b"], ["b", "c"]), 0.333333)
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
                {"cf_recordings_returned": 2, "cf_recordings_resolved": 2, "resolved_album_count": 2,
                 "refresh_origin": "scheduler"},
                generated_at=200,
            )
            self.assertIsNone(first["cf_recording_jaccard_previous"])
            self.assertEqual(second["cf_recording_jaccard_previous"], 0.333333)
            self.assertEqual(second["final_list_jaccard_previous"], 1.0)
            self.assertNotIn("refresh_origin", second)
            import sqlite3
            with sqlite3.connect(db) as connection:
                stored = connection.execute(
                    "SELECT metrics_json FROM recommendation_pool_diagnostics"
                ).fetchone()[0]
            self.assertEqual(json.loads(stored)["refresh_origin"], "scheduler")
            import sqlite3
            with sqlite3.connect(db) as connection:
                row = connection.execute("SELECT recording_hashes_json FROM recommendation_pool_diagnostics").fetchone()
            self.assertNotIn("recording-b", row[0])

    def test_aggregate_candidate_diagnostics_are_bounded_and_identity_free(self):
        gathered = {
            "listens": [{}, {}, {}],
            "recent_artists": {"artist-a": 2, "artist-b": 1},
            "recent_artist_mbid_counts": {"mbid-a": 2},
            "recent_family_counts": {"jazz": 3, "soul": 1},
            "supplementary_cache_hits": 4,
            "supplementary_cache_misses": 2,
        }
        candidates = [
            {
                "artist": "Private Artist", "album": "Private Album",
                "discovery_source": "listenbrainz", "score": 0.5,
                "discovery_score": 0.75, "recent_profile_bonus": 1.1,
                "lastfm_popularity_bonus": 1.04, "genre_metadata_available": True,
                "exact_owned": True, "same_title_library_matches": 1,
                "assigned_category": "adjacent", "selection_decision": "selected",
            },
            {
                "artist": "Other Private Artist", "album": "Other Private Album",
                "discovery_source": "musicbrainz_tag_search", "score": 0.25,
                "discovery_score": 0.3, "recent_profile_bonus": 1.0,
                "lastfm_popularity_bonus": 1.0, "genre_metadata_available": False,
                "exact_owned": False, "same_title_library_matches": 0,
                "assigned_category": "unclassified", "selection_decision": "not_considered",
            },
        ]
        result = summarize_candidate_diagnostics(gathered, candidates)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["candidate_counts_by_source"], {
            "listenbrainz": 1, "musicbrainz_tag_search": 1,
        })
        self.assertEqual(result["score_components"]["base_score"]["mean"], 0.375)
        self.assertEqual(result["profile_evidence"]["listens_seen"], 3)
        self.assertEqual(result["profile_evidence"]["recent_family_counts"], {"jazz": 3, "soul": 1})
        self.assertEqual(result["eligibility_rejections"]["exact_owned"], 1)
        self.assertEqual(result["eligibility_rejections"]["same_title_artist_conflicts"], 1)
        self.assertEqual(result["eligibility_rejections"]["unclassified"], 1)
        encoded = json.dumps(result)
        self.assertNotIn("Private Artist", encoded)
        self.assertNotIn("Private Album", encoded)

    def test_frozen_replay_metrics_are_deterministic_and_exclude_owned_artists(self):
        fixture_path = Path(__file__).parent / "fixtures" / "recommendation_replay.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        first = evaluate_replay_fixture(fixture, k=10)
        self.assertEqual(first, evaluate_replay_fixture(fixture, k=10))
        self.assertEqual(first["case_count"], 2)
        self.assertEqual(first["cases"][0]["owned_artist_recommendations_excluded"], 1)
        self.assertEqual(first["mean_candidate_pool_overlap"], 0.333333)
        self.assertEqual(first["mean_ranking_overlap"], 0.166667)


if __name__ == "__main__":
    unittest.main()
