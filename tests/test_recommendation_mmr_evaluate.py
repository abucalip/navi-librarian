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
                "gathered_inputs": {},
                "provider_events": [],
                "lastfm_calls": [],
                "expected_output": {
                    "recommendations": pool[:5],
                    "debug_all_candidates": pool,
                },
            },
        }

    def test_evaluates_lambda_grid_and_checks_hard_artist_and_eligibility_gates(self):
        report = evaluate_capture(self._envelope(), limit=4, lambdas=[0, 0.5, 1])
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

    def test_rejects_missing_scored_pool_instead_of_guessing_scores(self):
        envelope = self._envelope()
        envelope["payload"]["expected_output"].pop("debug_all_candidates")
        with self.assertRaisesRegex(ValueError, "debug_all_candidates"):
            evaluate_capture(envelope)

    def test_rejects_invalid_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            evaluate_capture(self._envelope(), limit=0)


if __name__ == "__main__":
    unittest.main()
