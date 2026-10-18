import json
import tempfile
import unittest
from pathlib import Path

from recommendation_profile_comparison import (
    IdentityLastFmReplay,
    build_profile_variant,
    compare_outputs,
    first_last_five_day_windows,
    load_history,
)


def _listen(timestamp, artist, mbid=None):
    info = {"artist_mbids": [mbid]} if mbid else {}
    return {
        "listened_at": timestamp,
        "track_metadata": {
            "artist_name": artist,
            "release_name": "Release",
            "additional_info": info,
        },
    }


class RecommendationProfileComparisonTests(unittest.TestCase):
    def test_windows_use_timestamped_first_and_last_five_days(self):
        day = 86400
        listens = [
            _listen(1000, "First"),
            _listen(1000 + 5 * day - 1, "First"),
            _listen(1000 + 5 * day, "Middle"),
            _listen(1000 + 10 * day, "Last"),
            _listen(1000 + 11 * day, "Last"),
        ]
        first, last, bounds = first_last_five_day_windows(listens)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(last), 3)
        self.assertEqual(bounds["first_start_utc"], "1970-01-01T00:16:40+00:00")
        self.assertEqual(bounds["last_end_utc"], "1970-01-12T00:16:40+00:00")

    def test_windows_reject_insufficient_nonoverlapping_history(self):
        listens = [_listen(1000, "A"), _listen(1000 + 9 * 86400, "B")]
        with self.assertRaisesRegex(ValueError, "too short"):
            first_last_five_day_windows(listens)

    def test_profile_variant_recomputes_only_listen_derived_fields(self):
        day = 86400
        listens = [
            _listen(1000, "Old Artist", "old-id"),
            _listen(1000 + day, "Recent Artist", "recent-id"),
            _listen(1000 + 2 * day, "Recent Artist", "recent-id"),
        ]
        template = {
            "listens": [],
            "recent_artists": {},
            "recent_artist_play_counts": {},
            "recent_artist_mbid_counts": {},
            "recent_family_counts": {},
            "recent_family_play_counts": {},
            "genre_cache": {
                "old-id": ["jazz"],
                "recent-id": ["soul", "r&b"],
            },
            "albums": {("candidate", "album"): {"artist": "Candidate", "album": "Album", "score": 1}},
            "library_albums": [{"artist": "Owned", "name": "Owned"}],
            "library_by_title": {"owned": [{"artist": "Owned", "name": "Owned"}]},
            "core_families": {"jazz", "rnb-soul"},
            "exploration_families": {"african"},
            "profile_families": {"jazz", "rnb-soul", "african"},
        }
        gathered, profile = build_profile_variant(template, listens)
        self.assertEqual(profile["listens"], 3)
        self.assertEqual(profile["distinct_artists"], 2)
        self.assertEqual(gathered["recent_artist_play_counts"]["recentartist"], 2)
        self.assertGreater(
            gathered["recent_artists"]["recentartist"],
            gathered["recent_artists"]["oldartist"],
        )
        self.assertGreater(gathered["recent_family_counts"]["soul"], 0)
        self.assertEqual(gathered["albums"], template["albums"])
        self.assertEqual(gathered["library_albums"], template["library_albums"])
        self.assertEqual(template["listens"], [])

    def test_history_loader_accepts_listenbrainz_json_array_and_skips_undated_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps([
                _listen(1000, "A"),
                {"track_metadata": {"artist_name": "Undated"}},
                _listen(2000, "B"),
            ]), encoding="utf-8")
            self.assertEqual(len(load_history(path)), 2)

    def test_identity_lastfm_replay_is_order_independent_and_fails_closed(self):
        replay = IdentityLastFmReplay([
            {"artist": "Artist A", "album": "Album A", "result": {"listeners": 10, "playcount": 20}},
            {"artist": "Artist B", "album": "Album B", "result": None},
        ])
        self.assertIsNone(replay("Artist B", "Album B"))
        self.assertEqual(replay("Artist A", "Album A")["listeners"], 10)
        with self.assertRaisesRegex(RuntimeError, "does not cover"):
            replay("Uncaptured", "Album")

    def test_comparison_reports_aggregates_without_identity_fields(self):
        first = {
            "recommendations": [
                {"artist": "A", "album": "One"},
                {"artist": "B", "album": "Two"},
            ],
            "debug_all_candidates": [
                {"artist": "A", "album": "One"},
                {"artist": "B", "album": "Two"},
                {"artist": "C", "album": "Three"},
            ],
        }
        last = {
            "recommendations": [
                {"artist": "B", "album": "Two"},
                {"artist": "D", "album": "Four"},
            ],
            "debug_all_candidates": [
                {"artist": "B", "album": "Two"},
                {"artist": "A", "album": "One"},
                {"artist": "D", "album": "Four"},
            ],
        }
        result = compare_outputs(first, last)
        self.assertEqual(result["recommendation_overlap"], 1)
        self.assertEqual(result["recommendation_jaccard"], 0.3333)
        self.assertTrue(result["recommendation_order_changed"])
        self.assertTrue(result["ranked_candidate_order_changed"])
        self.assertNotIn("artist", result)
        self.assertNotIn("album", result)


if __name__ == "__main__":
    unittest.main()
