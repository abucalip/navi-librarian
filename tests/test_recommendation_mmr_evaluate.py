import unittest

from recommendation_mmr_evaluate import evaluate_capture


def row(artist, album, score, tags=None, **extra):
    return {
        "artist": artist,
        "album": album,
        "artist_mbid": artist.casefold().replace(" ", "-"),
        "discovery_score": score,
        "genres": tags or [],
        **extra,
    }


class RecommendationMmrEvaluateTests(unittest.TestCase):
    def _envelope(self):
        pool = [
            row("Artist A", "Album 1", 10, ["jazz", "soul"]),
            row("Artist A", "Album 2", 9.8, ["jazz"]),
            row("Artist B", "Album 3", 9.7, ["jazz", "soul"]),
            row("Artist C", "Album 4", 9.6, ["afrobeat", "funk"]),
            row("Artist D", "Album 5", 8.0, []),
            row("Owned Artist", "Owned Album", 12, ["jazz"], exact_owned=True),
            row("Bad Artist", "EP", 11, ["rock"], selection_decision="ineligible_release"),
        ]
        return {
            "git_sha": "synthetic-fixture",
            "schema_version": 1,
            "payload": {
                "gathered_inputs": {"albums": [{}, {}, {}], "library_albums": [{}]},
                "provider_events": [],
                "lastfm_calls": [],
                "expected_output": {
                    "recommendations": pool[:5],
                    "debug_all_candidates": pool,
                },
            },
        }

    def test_evaluates_lambda_grid_and_checks_hard_artist_and_eligibility_gates(self):
        report = evaluate_capture(self._envelope(), limit=4, lambdas=[0, 0.5, 1], relevance_floors=[0])
        self.assertEqual(report["network_providers_used"], 0)
        self.assertFalse(report["provider_tape_replayed"])
        self.assertEqual(report["scored_candidate_pool_size"], 5)
        self.assertEqual([row["lambda"] for row in report["lambda_results"]], [0, 0.5, 1])
        for result in report["lambda_results"]:
            self.assertTrue(result["all_selected_from_eligible_pool"])
            self.assertEqual(result["duplicate_nonempty_artist_keys"], 0)
            self.assertTrue(result["deterministic_repeat"])
            self.assertNotIn(("owned artist", "owned album"), result["selected_identities"])
            self.assertNotIn(("bad artist", "ep"), result["selected_identities"])

    def test_relevance_floor_sweep_can_expose_shortlist_completion_tradeoff(self):
        report = evaluate_capture(self._envelope(), limit=4, lambdas=[0.75], relevance_floors=[0, 0.5, 0.9])
        results = report["lambda_results"]
        self.assertEqual([item["relevance_floor"] for item in results], [0, 0.5, 0.9])
        self.assertGreaterEqual(results[0]["selected_count"], results[-1]["selected_count"])
        self.assertTrue(all(item["all_selected_from_eligible_pool"] for item in results))

    def test_reports_identity_free_quality_and_category_metrics(self):
        envelope = self._envelope()
        pool = envelope["payload"]["expected_output"]["debug_all_candidates"]
        pool[0]["discovery_category"] = "adjacent"
        pool[1]["discovery_category"] = "adjacent"
        pool[2]["discovery_category"] = "cross_genre"
        pool[3]["discovery_category"] = "adventurous"
        pool[4]["discovery_category"] = "adventurous"
        report = evaluate_capture(envelope, limit=4, lambdas=[0.5, 0], relevance_floors=[0])
        results = {item["lambda"]: item for item in report["lambda_results"]}
        baseline = results[0]
        diversified = results[0.5]
        self.assertIn("adjacent", baseline["category_counts"])
        self.assertAlmostEqual(sum(baseline["category_mix"].values()), 1.0)
        self.assertGreaterEqual(baseline["genre_coverage_count"], 1)
        self.assertGreaterEqual(baseline["untagged_selected_count"], 0)
        self.assertGreaterEqual(baseline["untagged_selected_share"], 0.0)
        self.assertIsNotNone(diversified["mean_raw_score_retention_vs_lambda_0"])
        self.assertAlmostEqual(baseline["mean_raw_score_retention_vs_lambda_0"], 1.0)
        self.assertIn("category_counts", diversified)
        self.assertIn("untagged_promoted_vs_score_top_k", diversified)
        self.assertIn("baseline_category_mix", report)
        self.assertIn("baseline_genre_coverage_count", report)
        self.assertIn("baseline_untagged_share", report)

    def test_rejects_missing_scored_pool_instead_of_guessing_scores(self):
        envelope = self._envelope()
        envelope["payload"]["expected_output"].pop("debug_all_candidates")
        with self.assertRaisesRegex(ValueError, "debug_all_candidates"):
            evaluate_capture(envelope)

    def test_rejects_invalid_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            evaluate_capture(self._envelope(), limit=0)



    def test_uses_assigned_category_from_captured_debug_pool(self):
        envelope = self._envelope()
        pool = envelope["payload"]["expected_output"]["debug_all_candidates"]
        for item in pool[:5]:
            item["assigned_category"] = "adjacent"
            item.pop("discovery_category", None)
        report = evaluate_capture(envelope, limit=4, lambdas=[0], relevance_floors=[0])
        self.assertEqual(report["lambda_results"][0]["category_counts"], {"adjacent": 4})
        self.assertEqual(report["baseline_category_counts"], {"adjacent": 5})

if __name__ == "__main__":
    unittest.main()
