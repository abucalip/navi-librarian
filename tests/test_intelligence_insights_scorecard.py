import unittest

from intelligence.insights import (
    CanonConfig, Scorecard, ScorecardConfig, WorldAlbum, canon_card, find_hidden_canon, score_lens,
)


def card(i, artist=None, **subject):
    return {"kind": "k", "subject": {"key": f"k:{i}", "artist": artist or f"A{i}", **subject}}


CFG = ScorecardConfig(min_cards=3, min_outcomes=4)


class ScorecardTests(unittest.TestCase):
    def test_pass_enables_by_default(self):
        cards = [card(i) for i in range(6)]
        s = score_lens("x", cards, accepted=["k:0", "k:1", "k:2"], dismissed=["k:3"], config=CFG)
        self.assertEqual((s.verdict, s.enable_by_default, s.precision, s.unjudged), ("pass", True, 0.75, 2))
        self.assertEqual((s.accepted, s.dismissed, s.diversity, s.failures), (3, 1, 1.0, ()))

    def test_few_outcomes_is_insufficient_not_guessed(self):
        s = score_lens("x", [card(i) for i in range(6)], accepted=["k:0"], config=CFG)
        self.assertEqual((s.verdict, s.enable_by_default), ("insufficient_evidence", False))
        self.assertEqual(s.precision, 1.0)

    def test_no_cards(self):
        s = score_lens("x", [], config=CFG)
        self.assertEqual((s.verdict, s.precision, s.diversity, s.enable_by_default), ("insufficient_evidence", None, None, False))

    def test_low_precision_fails(self):
        s = score_lens("x", [card(i) for i in range(6)], accepted=["k:0"], dismissed=["k:1", "k:2", "k:3"], config=CFG)
        self.assertEqual((s.verdict, s.failures, s.enable_by_default), ("fail", ("low_precision",), False))

    def test_dismissal_wins_over_accept(self):
        s = score_lens("x", [card(1)], accepted=["k:1"], dismissed=["k:1"], config=CFG)
        self.assertEqual((s.accepted, s.dismissed), (0, 1))

    def test_duplicates_fail(self):
        cards = [card(1), card(1), card(2), card(3)]
        s = score_lens("x", cards, config=CFG)
        self.assertEqual((s.duplicate_rate, s.verdict, s.failures), (0.25, "fail", ("duplicates",)))

    def test_owned_leak_by_key_or_group_mbid_fails(self):
        cards = [card(1, group_mbid="G1"), card(2), card(3), card(4)]
        s = score_lens("x", cards, owned=["g1", "K:2"], config=CFG)
        self.assertEqual((s.owned_leak_rate, s.failures), (0.5, ("owned_leak",)))

    def test_low_diversity_fails(self):
        cards = [card(i, artist="Same") for i in range(4)]
        s = score_lens("x", cards, config=CFG)
        self.assertEqual((s.diversity, s.top_artist_share, s.failures), (0.25, 1.0, ("low_diversity",)))

    def test_as_dict_is_plain(self):
        d = score_lens("x", [card(1)], config=CFG).as_dict()
        self.assertEqual(d["lens"], "x")
        self.assertIsInstance(d["failures"], list)
        self.assertNotIn("config", d)

    def test_scores_real_hidden_canon_cards(self):
        pool = [WorldAlbum(f"G{i}", f"T{i}", f"A{i}", 1970, ("jazz",), 5000) for i in range(6)]
        r = find_hidden_canon(pool, ["g0"], ["jazz", "soul"], CanonConfig())
        cards = [canon_card(p) for p in r.picks]
        s = score_lens("hidden_canon", cards, owned=["g0"], config=CFG)
        self.assertEqual((s.cards, s.owned_leak_rate, s.duplicate_rate), (5, 0.0, 0.0))
        self.assertIsInstance(s, Scorecard)


if __name__ == "__main__":
    unittest.main()
