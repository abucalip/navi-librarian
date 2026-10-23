import unittest

from discovery.history_windows import listen_artist_mbid, window_artist_weights

DAY = 24 * 60 * 60
NEWEST = 1_000_000 * DAY


def listen(days_before_newest, artist_mbid="a1", **extra):
    info = {"artist_mbid": artist_mbid} if artist_mbid else {}
    info.update(extra)
    return {"listened_at": NEWEST - days_before_newest * DAY,
            "track_metadata": {"artist_name": "x", "additional_info": info}}


class ListenArtistMbidTests(unittest.TestCase):
    def test_prefers_artist_mbid_then_first_of_list(self):
        self.assertEqual(listen_artist_mbid(listen(0, "a1")), "a1")
        self.assertEqual(listen_artist_mbid(listen(0, None, artist_mbids=["b2", "c3"])), "b2")

    def test_missing_mbid_is_empty(self):
        self.assertEqual(listen_artist_mbid(listen(0, None)), "")
        self.assertEqual(listen_artist_mbid({"track_metadata": {}}), "")


class WindowArtistWeightsTests(unittest.TestCase):
    def test_bounded_window_keeps_only_recent_artists(self):
        listens = [listen(0, "recent"), listen(29, "recent"), listen(90, "old")]
        weights = window_artist_weights(listens, window_days=30)
        self.assertEqual(dict(weights), {"recent": 2.0})

    def test_all_time_flat_counts_every_listen(self):
        listens = [listen(0, "a"), listen(400, "a"), listen(3, "b")]
        self.assertEqual(dict(window_artist_weights(listens)), {"a": 2.0, "b": 1.0})

    def test_decay_within_window_weights_listens(self):
        listens = [listen(0, "a"), listen(14, "a")]
        weights = window_artist_weights(listens, window_days=365, half_life_days=14)
        self.assertAlmostEqual(weights["a"], 1.5)

    def test_listens_without_mbid_are_skipped(self):
        self.assertEqual(dict(window_artist_weights([listen(0, None)])), {})

    def test_undated_listen_is_excluded_from_bounded_window(self):
        undated = {"track_metadata": {"additional_info": {"artist_mbid": "u"}}}
        self.assertEqual(dict(window_artist_weights([undated], window_days=30)), {})
        self.assertEqual(dict(window_artist_weights([undated])), {"u": 1.0})


if __name__ == "__main__":
    unittest.main()


class DensestWindowTests(unittest.TestCase):
    def test_picks_the_span_with_most_listens_not_the_newest(self):
        from discovery.history_windows import densest_window_listens
        # Old burst of three in 10 days, then two far later.
        listens = [
            {"listened_at": 100 * DAY}, {"listened_at": 105 * DAY}, {"listened_at": 110 * DAY},
            {"listened_at": 900 * DAY}, {"listened_at": 905 * DAY},
        ]
        chosen = densest_window_listens(listens, 30)
        self.assertEqual([item["listened_at"] for item in chosen], [100 * DAY, 105 * DAY, 110 * DAY])

    def test_ties_go_to_the_earliest_span(self):
        from discovery.history_windows import densest_window_listens
        listens = [{"listened_at": DAY}, {"listened_at": 2 * DAY},
                   {"listened_at": 500 * DAY}, {"listened_at": 501 * DAY}]
        chosen = densest_window_listens(listens, 30)
        self.assertEqual([item["listened_at"] for item in chosen], [DAY, 2 * DAY])

    def test_undated_listens_are_ignored(self):
        from discovery.history_windows import densest_window_listens
        self.assertEqual(densest_window_listens([{"track": 1}, {"listened_at": "bad"}], 30), [])
        self.assertEqual(densest_window_listens([{}], 30), [])

    def test_rejects_invalid_width(self):
        from discovery.history_windows import densest_window_listens
        with self.assertRaises(ValueError):
            densest_window_listens([], 0)


class MalformedInputTests(unittest.TestCase):
    def test_non_mapping_nesting_yields_empty_mbid(self):
        malformed = [
            {"track_metadata": "not a mapping"},
            {"track_metadata": {"additional_info": "not a mapping"}},
            {"track_metadata": ["list"]},
            {"track_metadata": {"additional_info": 42}},
            "not a listen",
            None,
        ]
        for item in malformed:
            self.assertEqual(listen_artist_mbid(item), "")

    def test_non_string_mbid_yields_empty(self):
        self.assertEqual(listen_artist_mbid(listen(0, ["a1"])), "")
        self.assertEqual(listen_artist_mbid(listen(0, {"x": 1})), "")

    def test_window_weights_skip_malformed_listens(self):
        listens = [{"track_metadata": "bad", "listened_at": NEWEST}, listen(0, "good")]
        self.assertEqual(dict(window_artist_weights(listens)), {"good": 1.0})


class WindowWidthValidationTests(unittest.TestCase):
    def test_non_numeric_width_raises_value_error(self):
        from discovery.history_windows import densest_window_listens
        for bad in ["30", None, [30], {"days": 30}, True]:
            with self.assertRaises(ValueError):
                densest_window_listens([listen(0)], bad)

    def test_numeric_width_still_accepted(self):
        from discovery.history_windows import densest_window_listens
        self.assertEqual(len(densest_window_listens([listen(0)], 30)), 1)
        self.assertEqual(len(densest_window_listens([listen(0)], 30.5)), 1)
