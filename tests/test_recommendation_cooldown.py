import unittest

from discovery_cooldown import cooldown_adjusted_score
from discovery_store import recommendation_identity_hash


class RecommendationCooldownTests(unittest.TestCase):
    def setUp(self):
        self.now = 2_000_000.0
        self.artist = "Beyoncé"
        self.album = "Déjà vu"
        self.identity = recommendation_identity_hash({
            "artist": self.artist, "album": self.album,
        })

    def row(self, *, age=0, rank=1, identity=None):
        return {
            "identity_hash": self.identity if identity is None else identity,
            "generated_at": self.now - age,
            "rank": rank,
        }

    def test_no_history_preserves_score(self):
        self.assertEqual(
            cooldown_adjusted_score(0.8, self.artist, self.album, [], now=self.now),
            0.8,
        )

    def test_recent_top_rank_exposure_gets_soft_penalty_not_exclusion(self):
        adjusted = cooldown_adjusted_score(
            0.8, self.artist, self.album, [self.row()], now=self.now,
        )
        self.assertAlmostEqual(adjusted, 0.72)
        self.assertGreater(adjusted, 0.0)

    def test_penalty_has_seven_day_half_life(self):
        fresh = cooldown_adjusted_score(
            1.0, self.artist, self.album, [self.row(age=0)], now=self.now,
        )
        after_one_half_life = cooldown_adjusted_score(
            1.0, self.artist, self.album,
            [self.row(age=7 * 24 * 60 * 60)], now=self.now,
        )
        self.assertAlmostEqual(1.0 - after_one_half_life, (1.0 - fresh) / 2)

    def test_lower_rank_exposure_has_weaker_penalty(self):
        top = cooldown_adjusted_score(
            1.0, self.artist, self.album, [self.row(rank=1)], now=self.now,
        )
        twentieth = cooldown_adjusted_score(
            1.0, self.artist, self.album, [self.row(rank=20)], now=self.now,
        )
        self.assertGreater(1.0 - top, 1.0 - twentieth)
        self.assertAlmostEqual(1.0 - twentieth, 0.005)

    def test_penalty_expires_after_thirty_days_and_ignores_future_rows(self):
        history = [
            self.row(age=30 * 24 * 60 * 60 + 1),
            self.row(age=-1),
        ]
        self.assertEqual(
            cooldown_adjusted_score(
                0.8, self.artist, self.album, history, now=self.now,
            ),
            0.8,
        )

    def test_repeated_exposures_are_bounded(self):
        history = [self.row(age=0, rank=1) for _ in range(20)]
        adjusted = cooldown_adjusted_score(
            1.0, self.artist, self.album, history, now=self.now,
        )
        self.assertAlmostEqual(adjusted, 0.75)

    def test_other_identity_and_malformed_history_do_not_change_score(self):
        history = [
            self.row(identity="not-this-identity"),
            {"identity_hash": self.identity, "generated_at": "invalid", "rank": 1},
            {"identity_hash": self.identity, "generated_at": self.now, "rank": 21},
            None,
        ]
        self.assertEqual(
            cooldown_adjusted_score(
                0.8, self.artist, self.album, history, now=self.now,
            ),
            0.8,
        )

    def test_missing_identity_and_non_finite_scores_are_safe(self):
        self.assertEqual(
            cooldown_adjusted_score(0.8, "", self.album, [self.row()], now=self.now),
            0.8,
        )
        with self.assertRaises(ValueError):
            cooldown_adjusted_score(float("nan"), self.artist, self.album, [], now=self.now)


if __name__ == "__main__":
    unittest.main()
