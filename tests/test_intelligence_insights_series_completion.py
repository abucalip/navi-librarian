import unittest

from intelligence.insights import ComparisonSet, SeriesConfig, SetItem, find_series_progress, series_card
from intelligence.insights.series_completion import dismiss_key


def make_series(key, n=10, kind="series", **kw):
    return ComparisonSet(key, kind, f"Series {key}", tuple(SetItem(f"G{i}", f"T{i}", 1970 + i) for i in range(1, n + 1)), **kw)


def owned(*idx):
    return [f"g{i}" for i in idx]  # case differs on purpose


class SeriesCompletionTests(unittest.TestCase):
    def test_no_series_is_empty(self):
        self.assertEqual(find_series_progress([], []).empty_reason, "no_series")

    def test_counts_and_missing_runs_in_series_order(self):
        r = find_series_progress([make_series("a")], owned(1, 2, 6, 7, 10))
        (p,) = r.progress
        self.assertEqual((p.owned, p.total, p.missing), (5, 10, 5))
        self.assertEqual([(x.first_position, x.last_position) for x in p.runs], [(3, 5), (8, 9)])
        self.assertEqual([i.title for i in p.runs[0].items], ["T3", "T4", "T5"])

    def test_left_out_reasons(self):
        r = find_series_progress(
            [make_series("small", 2), make_series("disc", kind="studio_discography")], owned(1))
        self.assertEqual(r.progress, ())
        self.assertEqual(dict(r.left_out)["small"], "series_too_small")
        self.assertEqual(dict(r.left_out)["disc"], "not_a_series")
        self.assertEqual(r.empty_reason, "no_candidates")

    def test_not_started_when_nothing_owned(self):
        r = find_series_progress([make_series("none")], owned())
        self.assertEqual(dict(r.left_out), {"none": "not_started"})

    def test_barely_started_series_is_left_out_with_a_reason(self):
        r = find_series_progress([make_series("list", 40), make_series("cat", 10)], owned(1, 2, 3, 4, 5, 6, 7, 8, 9))
        self.assertEqual([p.set.key for p in r.progress], ["cat"])
        self.assertEqual(dict(r.left_out), {"list": "barely_started"})
        # exactly at the threshold stays; the threshold is configurable
        edge = find_series_progress([make_series("e", 8)], owned(1, 2))
        self.assertEqual(len(edge.progress), 1)
        off = find_series_progress([make_series("list", 40)], owned(1), SeriesConfig(min_share_owned=0))
        self.assertEqual(len(off.progress), 1)

    def test_complete_series_is_not_a_card(self):
        r = find_series_progress([make_series("done", 4)], owned(1, 2, 3, 4))
        self.assertEqual(r.complete, ("done",))
        self.assertEqual(r.progress, ())

    def test_dismissed_series_is_suppressed(self):
        r = find_series_progress([make_series("a"), make_series("b")], owned(1, 2, 3), dismissed=[dismiss_key("a")])
        self.assertEqual([p.set.key for p in r.progress], ["b"])
        self.assertEqual(r.suppressed, 1)

    def test_duplicates_and_missing_mbids_are_skipped_not_counted(self):
        items = (SetItem("G1", "A"), SetItem("g1", "A again"), SetItem(None, "No id"), SetItem("G2", "B"), SetItem("G3", "C"))
        s = ComparisonSet("dup", "series", "Dup", items)
        (p,) = find_series_progress([s], owned(1)).progress
        self.assertEqual((p.owned, p.total, p.skipped_items), (1, 3, 2))

    def test_ranks_closest_to_finished_first(self):
        r = find_series_progress([make_series("low"), make_series("high")], owned(1, 2, 3, 4, 5, 6, 7, 8, 9))
        self.assertEqual(len(r.progress), 2)
        low = find_series_progress([make_series("low")], owned(1, 2, 3)).progress[0]
        high = find_series_progress([make_series("high")], owned(1, 2, 3, 4, 5, 6, 7, 8, 9)).progress[0]
        self.assertGreater(high.score, low.score)

    def test_card_states_counts_never_advice(self):
        r = find_series_progress([make_series("a")], owned(1, 2, 6))
        card = series_card(r.progress[0])
        self.assertEqual(card["kind"], "series_completion")
        self.assertEqual(card["body"], "You own 3 of 10 in this series; 7 not in your library.")
        self.assertEqual(card["actions"], [{"kind": "dismiss"}])
        self.assertNotIn("should", card["body"].lower())
        self.assertEqual(card["subject"]["key"], dismiss_key("a"))
        self.assertEqual([(m["first_position"], m["last_position"]) for m in card["missing_runs"]], [(3, 5), (7, 10)])

    def test_card_caps_listed_runs(self):
        r = find_series_progress([make_series("a", 9)], owned(1, 3, 5, 7, 9))
        card = series_card(r.progress[0], SeriesConfig(max_runs_listed=2))
        self.assertEqual(len(card["missing_runs"]), 2)
        self.assertEqual(card["missing_total"], 4)

    def test_limit_applies(self):
        sets = [make_series(f"s{i}") for i in range(5)]
        r = find_series_progress(sets, owned(1, 2, 3), SeriesConfig(limit=2))
        self.assertEqual(len(r.progress), 2)


if __name__ == "__main__":
    unittest.main()
