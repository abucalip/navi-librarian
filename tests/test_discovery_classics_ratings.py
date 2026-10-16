import unittest

from discovery_classics_ratings import enrich_critical_ratings


class ClassicsCriticalRatingTests(unittest.TestCase):
    def test_queries_listener_ranked_shortlist_and_bounds_year_lookups(self):
        candidates = [
            {"mbid": "low", "lastfm_listeners": 10, "year": 1990},
            {"mbid": "high", "lastfm_listeners": 100},
            {"mbid": "mid", "lastfm_listeners": 50},
        ]
        calls = []

        def lookup(mbid, *, include_year):
            calls.append((mbid, include_year))
            return {"rating": 4.2, "votes": 17, "year": 2001} if include_year else {
                "rating": 3.8, "votes": 5
            }

        enrich_critical_ratings(candidates, lookup, shortlist_limit=2, year_limit=1)

        self.assertEqual(calls, [("high", True), ("mid", False)])
        self.assertEqual(candidates[1]["musicbrainz_rating"], 4.2)
        self.assertEqual(candidates[1]["musicbrainz_rating_votes"], 17)
        self.assertEqual(candidates[1]["year"], 2001)
        self.assertEqual(candidates[2]["musicbrainz_rating"], 3.8)
        self.assertNotIn("year", candidates[2])
        self.assertNotIn("musicbrainz_rating", candidates[0])
        self.assertEqual(candidates[0]["year"], 1990)

    def test_missing_rating_leaves_candidate_unchanged(self):
        candidate = {"mbid": "missing", "lastfm_listeners": 1, "year": 1984}
        calls = []
        enrich_critical_ratings(
            [candidate],
            lambda mbid, *, include_year: calls.append((mbid, include_year)) or None,
        )
        self.assertEqual(calls, [("missing", True)])
        self.assertEqual(candidate, {"mbid": "missing", "lastfm_listeners": 1, "year": 1984})

    def test_stable_order_for_equal_listener_counts(self):
        candidates = [
            {"mbid": "first", "lastfm_listeners": 10},
            {"mbid": "second", "lastfm_listeners": 10},
        ]
        calls = []
        enrich_critical_ratings(candidates, lambda mbid, *, include_year: calls.append(mbid))
        self.assertEqual(calls, ["first", "second"])

    def test_negative_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            enrich_critical_ratings([], lambda *args, **kwargs: None, shortlist_limit=-1)
        with self.assertRaises(ValueError):
            enrich_critical_ratings([], lambda *args, **kwargs: None, year_limit=-1)
