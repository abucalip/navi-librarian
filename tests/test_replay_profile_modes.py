import unittest

from recommendation.replay import KeyedLastFmReplay, rederive_profile


def _gathered(n_listens=12):
    listens = [{
        "listened_at": 1000 + i,
        "track_metadata": {"additional_info": {"artist_mbid": "a1"}},
    } for i in range(n_listens)]
    return {
        "listens": listens,
        "genre_cache": {"a1": ["heavy metal", "thrash metal"], "a2": ["folk"]},
        "albums": {("x", "y"): {"artist_mbid": "a2"}},
        "core_families": {"jazz"},
        "exploration_families": {"african"},
        "profile_families": {"jazz", "african"},
    }


class RederiveProfileTests(unittest.TestCase):
    def test_derives_from_captured_listens_and_marks_mode(self):
        result = rederive_profile(_gathered())
        self.assertEqual(result["profile_mode"], "derived")
        self.assertEqual(result["core_families"], {"metal"})
        self.assertEqual(result["profile_families"], result["core_families"] | result["exploration_families"])

    def test_sparse_capture_falls_back_to_fixed(self):
        original = _gathered(n_listens=1)
        result = rederive_profile(original)
        self.assertEqual((result["profile_mode"], result["profile_source"]), ("fixed", "defaults_sparse_history"))

    def test_input_is_not_mutated(self):
        original = _gathered()
        rederive_profile(original)
        self.assertEqual(original["core_families"], {"jazz"})
        self.assertNotIn("profile_mode", original)


class KeyedLastFmReplayTests(unittest.TestCase):
    def test_known_keys_replay_and_unknown_are_counted_empty(self):
        replay = KeyedLastFmReplay([{"artist": "A", "album": "B", "result": [1, 2]}])
        self.assertEqual(replay("A", "B"), (1, 2))
        self.assertIsNone(replay("A", "C"))
        self.assertEqual(replay.uncaptured, 1)


if __name__ == "__main__":
    unittest.main()
