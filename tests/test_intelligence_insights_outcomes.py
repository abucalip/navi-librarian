import tempfile
import unittest
from pathlib import Path

from intelligence.insights import (
    accept_card, accepted_keys, dismiss_series, dismissed_series_keys, lens_outcomes,
    list_series_cards, save_series, score_lens, unaccept_card, ComparisonSet, SeriesConfig, SetItem,
    find_series_progress,
)
from intelligence.insights import outcomes
from intelligence.insights import series_completion as sc
from intelligence.store import generations, open_store


def run_series(db, keys):
    sets = [ComparisonSet(k, "series", k, tuple(SetItem(f"{k}-{i}", f"T{i}", 2000 + i) for i in range(4))) for k in keys]
    own = [f"{k}-0" for k in keys]
    return save_series(db, find_series_progress(sets, own, SeriesConfig(), dismissed_series_keys(db)), now=1.0)


class OutcomesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "o.sqlite3")
        self.addCleanup(self.db.close)
        self.kind = sc.CARD_KIND

    def test_accept_is_recorded_once_and_survives_refresh(self):
        run_series(self.db, ["a"])
        key = sc.dismiss_key("a")
        self.assertTrue(accept_card(self.db, self.kind, key, now=2.0))
        self.assertFalse(accept_card(self.db, self.kind, key))
        run_series(self.db, ["a"])
        self.assertEqual(accepted_keys(self.db, self.kind), {key})
        self.assertEqual([c["subject"]["key"] for c in list_series_cards(self.db)], [key])

    def test_accept_does_not_suppress_or_touch_dismissals(self):
        accept_card(self.db, self.kind, "k1")
        self.assertEqual(dismissed_series_keys(self.db), set())

    def test_dismissed_key_cannot_be_accepted(self):
        run_series(self.db, ["a"])
        key = sc.dismiss_key("a")
        dismiss_series(self.db, key)
        self.assertFalse(accept_card(self.db, self.kind, key))
        self.assertEqual(accepted_keys(self.db, self.kind), set())

    def test_dismiss_after_accept_wins_in_scorecard(self):
        run_series(self.db, ["a"])
        key = sc.dismiss_key("a")
        accept_card(self.db, self.kind, key)
        dismiss_series(self.db, key)
        out = lens_outcomes(self.db, self.kind)
        card = score_lens("series", out["cards"], out["accepted"], out["dismissed"])
        self.assertEqual((card.accepted, card.dismissed), (0, 0))  # the live card was dismissed away
        self.assertIn(key, out["dismissed"])
        self.assertIn(key, out["accepted"])

    def test_unaccept(self):
        accept_card(self.db, self.kind, "k1")
        self.assertTrue(unaccept_card(self.db, self.kind, "k1"))
        self.assertFalse(unaccept_card(self.db, self.kind, "k1"))
        self.assertEqual(accepted_keys(self.db, self.kind), set())

    def test_kinds_are_separate_and_unknown_raises(self):
        accept_card(self.db, self.kind, "k1")
        self.assertEqual(accepted_keys(self.db, "forgotten_gem"), set())
        for fn in (lambda: accept_card(self.db, "nope", "k"), lambda: accepted_keys(self.db, "nope"),
                   lambda: lens_outcomes(self.db, "nope"), lambda: unaccept_card(self.db, "nope", "k")):
            with self.assertRaises(ValueError):
                fn()
        self.assertFalse(accept_card(self.db, self.kind, ""))

    def test_accept_bumps_data_version(self):
        before = generations.data_version(self.db, outcomes.RESOURCE)
        accept_card(self.db, self.kind, "k1")
        self.assertGreater(generations.data_version(self.db, outcomes.RESOURCE), before)

    def test_lens_outcomes_feed_the_scorecard(self):
        run_series(self.db, ["a", "b", "c"])
        keys = [sc.dismiss_key(k) for k in "abc"]
        accept_card(self.db, self.kind, keys[0])
        accept_card(self.db, self.kind, keys[1])
        dismiss_series(self.db, keys[2])
        out = lens_outcomes(self.db, self.kind)
        card = score_lens("series", out["cards"], out["accepted"], out["dismissed"])
        self.assertEqual(card.cards, 2)
        self.assertEqual(card.accepted, 2)
        self.assertEqual(card.verdict, "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
