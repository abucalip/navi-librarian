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

    def test_default_limits_match_legacy_eighty_and_thirty_bounds(self):
        candidates = [
            {"mbid": str(index), "lastfm_listeners": 1000 - index}
            for index in range(82)
        ]
        calls = []
        enrich_critical_ratings(
            candidates,
            lambda mbid, *, include_year: calls.append((mbid, include_year)) or None,
        )
        self.assertEqual(len(calls), 80)
        self.assertEqual(calls[0], ("0", True))
        self.assertEqual(calls[29], ("29", True))
        self.assertEqual(calls[30], ("30", False))
        self.assertEqual(calls[-1], ("79", False))

    def test_negative_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            enrich_critical_ratings([], lambda *args, **kwargs: None, shortlist_limit=-1)
        with self.assertRaises(ValueError):
            enrich_critical_ratings([], lambda *args, **kwargs: None, year_limit=-1)


class ClassicsGenreEnrichmentTests(unittest.TestCase):
    def test_enriches_prefix_and_uses_other_for_unclassified_genres(self):
        from discovery_classics_genres import enrich_classic_genres

        candidates = [
            {"artist": "Alpha", "id": 1},
            {"artist": "Beta", "id": 2},
            {"artist": "Gamma", "id": 3},
        ]
        calls = []
        enrich_classic_genres(
            candidates,
            lambda artist: calls.append(artist) or (["jazz"] if artist == "Alpha" else ["unknown"]),
            lambda tags: ["jazz"] if "jazz" in tags else [],
            limit=2,
        )
        self.assertEqual(calls, ["Alpha", "Beta"])
        self.assertEqual(candidates[0]["genres"], ["jazz"])
        self.assertEqual(candidates[0]["genre_families"], ["jazz"])
        self.assertEqual(candidates[1]["genre_families"], ["other"])
        self.assertEqual(candidates[2]["genres"], [])
        self.assertEqual(candidates[2]["genre_families"], ["other"])
        self.assertEqual([item["id"] for item in candidates], [1, 2, 3])

    def test_deduplicates_normalized_artist_lookups(self):
        from discovery_classics_genres import enrich_classic_genres

        candidates = [{"artist": "Beyoncé"}, {"artist": "Beyonce"}, {"artist": "Beyoncé"}]
        calls = []
        enrich_classic_genres(
            candidates,
            lambda artist: calls.append(artist) or ["soul"],
            lambda tags: ["rnb-soul"],
        )
        self.assertEqual(calls, ["Beyoncé"])
        self.assertTrue(all(item["genres"] == ["soul"] for item in candidates))

    def test_limit_zero_and_negative_limit(self):
        from discovery_classics_genres import enrich_classic_genres

        candidates = [{"artist": "A"}]
        enrich_classic_genres(candidates, lambda artist: self.fail("lookup should not run"), lambda tags: [], limit=0)
        self.assertEqual(candidates[0]["genres"], [])
        with self.assertRaises(ValueError):
            enrich_classic_genres(candidates, lambda artist: [], lambda tags: [], limit=-1)
