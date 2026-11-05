import unittest

from intelligence.insights import GemsConfig, PlayRecord, find_forgotten_gems, gem_card

NOW = 1_800_000_000.0
DAY = 86400.0


def rec(key, plays=10, days=800, starred=False, rating=None, last=True):
    return PlayRecord(key, "album", key.upper(), "Artist", plays, NOW - days * DAY if last else None, starred, rating)


def cfg(**kw):
    kw.setdefault("min_records_with_history", 3)
    return GemsConfig(now=NOW, **kw)


class GemsTests(unittest.TestCase):
    def test_sparse_history_is_empty_not_a_guess(self):
        result = find_forgotten_gems([rec("a"), rec("b")], cfg())
        self.assertEqual((result.gems, result.empty_reason), ((), "sparse_history"))

    def test_recent_plays_are_never_gems(self):
        result = find_forgotten_gems([rec("a", days=10), rec("b", days=179), rec("c", days=800), rec("d", days=900)], cfg())
        self.assertEqual(sorted(g.record.key for g in result.gems), ["c", "d"])
        self.assertNotIn("a", [g.record.key for g in result.gems])
        self.assertNotIn("b", [g.record.key for g in result.gems])

    def test_score_is_affinity_times_dormancy_and_ranked(self):
        result = find_forgotten_gems(
            [rec("loved", plays=50, days=730, starred=True, rating=5), rec("meh", plays=5, days=730), rec("x", plays=9, days=400)],
            cfg(),
        )
        loved, *rest = result.gems
        self.assertEqual(loved.record.key, "loved")
        self.assertAlmostEqual(loved.affinity, 1.0)
        self.assertAlmostEqual(loved.dormancy, 1.0)
        self.assertAlmostEqual(loved.score, 1.0)
        self.assertEqual([g.score for g in result.gems], sorted((g.score for g in result.gems), reverse=True))

    def test_low_plays_without_star_or_rating_is_not_once_loved(self):
        result = find_forgotten_gems([rec("a", plays=2), rec("b"), rec("c"), rec("d", plays=1, starred=True)], cfg())
        self.assertEqual(sorted(g.record.key for g in result.gems), ["b", "c", "d"])

    def test_never_played_is_skipped(self):
        result = find_forgotten_gems([rec("a", last=False, starred=True), rec("b"), rec("c"), rec("d")], cfg())
        self.assertNotIn("a", [g.record.key for g in result.gems])

    def test_dismissals_are_suppressed_and_counted(self):
        result = find_forgotten_gems([rec("a"), rec("b"), rec("c")], cfg(), dismissed=["b"])
        self.assertEqual(sorted(g.record.key for g in result.gems), ["a", "c"])
        self.assertEqual(result.suppressed, 1)

    def test_all_dismissed_is_no_candidates(self):
        result = find_forgotten_gems([rec("a"), rec("b"), rec("c")], cfg(), dismissed=["a", "b", "c"])
        self.assertEqual(result.empty_reason, "no_candidates")

    def test_limit_and_deterministic_ties(self):
        records = [rec(k) for k in "dcba"] + [rec("e")]
        first = find_forgotten_gems(records, cfg(limit=3))
        self.assertEqual([g.record.key for g in first.gems], ["a", "b", "c"])
        self.assertEqual(first, find_forgotten_gems(list(reversed(records)), cfg(limit=3)))

    def test_tunable_weights(self):
        star_only = cfg(w_plays=0, w_star=1, w_rating=0)
        result = find_forgotten_gems([rec("s", plays=5, starred=True), rec("p", plays=50), rec("q", plays=40)], star_only)
        self.assertEqual(result.gems[0].record.key, "s")

    def test_card_is_generic_with_reasons(self):
        [gem] = find_forgotten_gems([rec("a", plays=12, starred=True), rec("b", days=1), rec("c", days=1)], cfg()).gems
        card = gem_card(gem)
        self.assertEqual(card["kind"], "forgotten_gem")
        self.assertTrue(card["dismissible"])
        self.assertEqual([r["kind"] for r in card["reasons"]], ["dormant", "played_often", "starred"])
        self.assertEqual(card["subject"]["key"], "a")
        self.assertNotIn("path", str(card).lower())


if __name__ == "__main__":
    unittest.main()
