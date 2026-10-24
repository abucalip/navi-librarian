import unittest

from discovery.history_windows import (
    artists_with_tags, burst_artist_weights, dominant_tags, dormant_artist_weights,
    listen_artist_mbid, new_artist_weights, repeated_track_artist_weights,
    window_artist_weights,
)

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


class IdleArtistProfileTests(unittest.TestCase):
    def setUp(self):
        self.listens = [
            listen(0, "now"), listen(10, "now"),
            listen(100, "mid"), listen(120, "mid"), listen(130, "mid"),
            listen(500, "old"), listen(520, "old"),
            listen(900, "once"),
            listen(0, None), listen(600, None),
        ]

    def test_dormant_keeps_artists_silent_for_the_whole_period(self):
        self.assertEqual(dict(dormant_artist_weights(self.listens)), {"old": 2, "once": 1})

    def test_dormant_min_listens_means_heavily_played(self):
        self.assertEqual(dict(dormant_artist_weights(self.listens, min_listens=2)), {"old": 2})

    def test_boundary_listen_inside_the_period_counts_as_active(self):
        listens = [listen(0, "a"), listen(365, "b"), listen(366, "c")]
        self.assertEqual(dict(dormant_artist_weights(listens)), {"c": 1})

    def test_undated_and_empty_input_give_nothing(self):
        undated = [{"track_metadata": {"additional_info": {"artist_mbid": "a"}}}]
        self.assertEqual(dormant_artist_weights(undated), {})
        self.assertEqual(dormant_artist_weights([]), {})

    def test_invalid_arguments_are_rejected(self):
        for bad in (0, -1, float("nan"), True, "30"):
            with self.assertRaises(ValueError):
                dormant_artist_weights(self.listens, dormant_days=bad)
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                dormant_artist_weights(self.listens, min_listens=bad)


def track_listen(days_before_newest, artist_mbid, track):
    item = listen(days_before_newest, artist_mbid)
    item["track_metadata"]["track_name"] = track
    return item


class MbidMappingFallbackTests(unittest.TestCase):
    def test_falls_back_to_mbid_mapping(self):
        mapped = {"listened_at": 1, "track_metadata": {"additional_info": {},
                  "mbid_mapping": {"artist_mbids": ["m1", "m2"]}}}
        self.assertEqual(listen_artist_mbid(mapped), "m1")

    def test_additional_info_wins_over_mapping(self):
        item = listen(0, "a1")
        item["track_metadata"]["mbid_mapping"] = {"artist_mbids": ["m1"]}
        self.assertEqual(listen_artist_mbid(item), "a1")

    def test_malformed_mapping_is_empty(self):
        for mapping in (None, "x", {"artist_mbids": "m1"}, {"artist_mbids": []}):
            item = {"track_metadata": {"mbid_mapping": mapping}}
            self.assertEqual(listen_artist_mbid(item), "")


class TagHelperTests(unittest.TestCase):
    TAGS = {"a": ["metal", "rock"], "b": ["metal"], "c": ["jazz"], "d": []}

    def test_dominant_tags_come_from_the_heaviest_artists(self):
        weights = {"a": 10, "b": 5, "c": 1, "d": 1}
        self.assertEqual(dominant_tags(weights, self.TAGS, top_artists=2, count=1), {"metal"})
        self.assertEqual(dominant_tags(weights, self.TAGS, top_artists=3, count=3),
                         {"metal", "rock", "jazz"})
        self.assertEqual(dominant_tags(weights, self.TAGS, top_artists=1, count=5), {"metal", "rock"})

    def test_artists_with_tags(self):
        self.assertEqual(artists_with_tags(self.TAGS, {"jazz", "rock"}), {"a", "c"})
        self.assertEqual(artists_with_tags(self.TAGS, set()), set())

    def test_invalid_counts_are_rejected(self):
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                dominant_tags({}, {}, count=bad)
            with self.assertRaises(ValueError):
                dominant_tags({}, {}, top_artists=bad)


class RepeatedTrackTests(unittest.TestCase):
    def setUp(self):
        self.listens = (
            [track_listen(i, "a", "Loop") for i in range(5)]
            + [track_listen(i, "a", " loop ") for i in range(5, 6)]
            + [track_listen(i, "b", "Once") for i in range(2)]
            + [track_listen(i, "c", "Song") for i in range(6)]
            + [track_listen(0, None, "No artist"), listen(0, "a")]
        )

    def test_only_tracks_at_or_above_the_threshold_count(self):
        self.assertEqual(dict(repeated_track_artist_weights(self.listens)), {"a": 6, "c": 6})
        self.assertEqual(dict(repeated_track_artist_weights(self.listens, min_track_plays=2)),
                         {"a": 6, "b": 2, "c": 6})

    def test_exclude_and_only_artists(self):
        self.assertEqual(dict(repeated_track_artist_weights(self.listens, exclude_artists={"a"})), {"c": 6})
        self.assertEqual(dict(repeated_track_artist_weights(self.listens, only_artists={"a"})), {"a": 6})
        self.assertEqual(dict(repeated_track_artist_weights(self.listens, only_artists=[])), {})

    def test_invalid_threshold_is_rejected(self):
        for bad in (0, -1, True, 2.5):
            with self.assertRaises(ValueError):
                repeated_track_artist_weights(self.listens, min_track_plays=bad)


class BurstTests(unittest.TestCase):
    def test_artist_with_most_listens_in_one_span_is_an_obsession(self):
        burst = [listen(i, "burst") for i in range(20)]
        steady = [listen(i * 40, "steady") for i in range(20)]
        mixed = [listen(i, "mixed") for i in range(10)] + [listen(300 + i * 40, "mixed") for i in range(10)]
        weights = burst_artist_weights(burst + steady + mixed)
        self.assertEqual(dict(weights), {"burst": 20})
        self.assertEqual(dict(burst_artist_weights(burst + steady + mixed, min_share=0.5)),
                         {"burst": 20, "mixed": 20})

    def test_thresholds(self):
        few = [listen(i, "few") for i in range(5)]
        self.assertEqual(dict(burst_artist_weights(few)), {})
        self.assertEqual(dict(burst_artist_weights(few, min_listens=5)), {"few": 5})
        self.assertEqual(dict(burst_artist_weights(few, min_listens=5, span_days=2, min_share=0.5)), {"few": 5})
        self.assertEqual(dict(burst_artist_weights(few, min_listens=5, span_days=2, min_share=1)), {})

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            burst_artist_weights([], min_listens=0)
        for bad in (0, 1.5, -0.1, True, float("nan")):
            with self.assertRaises(ValueError):
                burst_artist_weights([], min_share=bad)
        with self.assertRaises(ValueError):
            burst_artist_weights([], span_days=0)


class NewArtistTests(unittest.TestCase):
    def test_first_heard_at_or_after_the_cutoff(self):
        listens = [listen(100, "old"), listen(0, "old"), listen(50, "new"), listen(10, "new"), listen(50, None)]
        cutoff = NEWEST - 60 * DAY
        self.assertEqual(dict(new_artist_weights(listens, first_heard_since=cutoff)), {"new": 2})
        self.assertEqual(dict(new_artist_weights(listens, first_heard_since=NEWEST - 50 * DAY)), {"new": 2})
        self.assertEqual(dict(new_artist_weights(listens, first_heard_since=NEWEST - 49 * DAY)), {})

    def test_invalid_cutoff_is_rejected(self):
        for bad in (None, "2018", True, float("inf")):
            with self.assertRaises(ValueError):
                new_artist_weights([], first_heard_since=bad)
