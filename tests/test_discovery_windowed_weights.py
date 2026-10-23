import unittest

from discovery.recommendations import decayed_listen_weights, windowed_listen_weights

DAY = 24 * 60 * 60
NEWEST = 1_000_000 * DAY


def listen(days_before_newest):
    return {"listened_at": NEWEST - days_before_newest * DAY}


class WindowedListenWeightsTests(unittest.TestCase):
    def test_all_time_flat_gives_every_listen_weight_one(self):
        self.assertEqual(windowed_listen_weights([listen(0), listen(400)]), [1.0, 1.0])

    def test_bounded_window_zeroes_listens_older_than_the_window(self):
        listens = [listen(0), listen(29), listen(30), listen(365)]
        self.assertEqual(windowed_listen_weights(listens, window_days=30), [1.0, 1.0, 1.0, 0.0])

    def test_window_is_anchored_to_newest_listen_not_to_now(self):
        listens = [{"listened_at": 5 * DAY}, {"listened_at": 9 * DAY}]
        self.assertEqual(windowed_listen_weights(listens, window_days=3), [0.0, 1.0])

    def test_half_life_decays_within_the_window(self):
        listens = [listen(0), listen(14), listen(60)]
        weights = windowed_listen_weights(listens, window_days=365, half_life_days=14)
        self.assertAlmostEqual(weights[0], 1.0)
        self.assertAlmostEqual(weights[1], 0.5)
        self.assertAlmostEqual(weights[2], 0.5 ** (60 / 14))

    def test_half_life_matches_existing_decay_without_a_window(self):
        listens = [listen(0), listen(7), listen(90)]
        self.assertEqual(
            windowed_listen_weights(listens, half_life_days=14),
            decayed_listen_weights(listens, half_life_days=14),
        )

    def test_undated_listens_are_kept_only_when_unbounded(self):
        listens = [listen(0), {"track": "no timestamp"}]
        self.assertEqual(windowed_listen_weights(listens), [1.0, 1.0])
        self.assertEqual(windowed_listen_weights(listens, window_days=30), [1.0, 0.0])

    def test_no_dated_listens_keeps_legacy_behaviour(self):
        self.assertEqual(windowed_listen_weights([{}, {}]), [1.0, 1.0])
        self.assertEqual(windowed_listen_weights([{}, {}], window_days=30), [0.0, 0.0])

    def test_empty_history(self):
        self.assertEqual(windowed_listen_weights([], window_days=30), [])

    def test_invalid_parameters_are_rejected(self):
        for kwargs in [{"window_days": 0}, {"window_days": -1}, {"window_days": float("nan")},
                       {"half_life_days": 0}, {"half_life_days": float("inf")}]:
            with self.assertRaises(ValueError):
                windowed_listen_weights([listen(0)], **kwargs)


if __name__ == "__main__":
    unittest.main()
