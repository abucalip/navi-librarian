import unittest

from intelligence.insights import BlindSpotsConfig, ComparisonSet, SetItem, blind_spot_card, find_blind_spots
from intelligence.insights.blind_spots import dismiss_key


def make_set(key, n=10, kind="studio_discography", **kw):
    return ComparisonSet(key, kind, f"Set {key}", tuple(SetItem(f"G{i}", f"T{i}", 1970 + i) for i in range(n)), **kw)


def owned(*idx):
    return [f"g{i}" for i in idx]  # case differs on purpose


class BlindSpotTests(unittest.TestCase):
    def test_no_sets_is_empty(self):
        self.assertEqual(find_blind_spots([], [], BlindSpotsConfig()).empty_reason, "no_sets")

    def test_counts_and_missing_in_set_order(self):
        r = find_blind_spots([make_set("a")], owned(0, 1, 2, 5), BlindSpotsConfig())
        (spot,) = r.spots
        self.assertEqual((spot.owned, spot.total), (4, 10))
        self.assertEqual([i.title for i in spot.missing], ["T3", "T4", "T6", "T7", "T8", "T9"])

    def test_small_and_uncollected_sets_are_left_out_with_reason(self):
        r = find_blind_spots([make_set("small", 3), make_set("none"), make_set("one")], owned(0), BlindSpotsConfig())
        self.assertEqual(r.spots, ())
        self.assertEqual(dict(r.left_out), {"small": "set_too_small", "none": "not_collected", "one": "not_collected"})
        self.assertEqual(r.empty_reason, "no_candidates")

    def test_complete_set_is_not_a_card(self):
        r = find_blind_spots([make_set("a", 5)], owned(*range(5)), BlindSpotsConfig())
        self.assertEqual((r.spots, r.complete), ((), ("a",)))

    def test_titles_never_match_only_mbids_and_bad_items_are_skipped(self):
        s = ComparisonSet("a", "series", "S", (
            SetItem("G0", "x"), SetItem("g0", "dup"), SetItem(None, "no id"), SetItem(" ", "blank"),
            SetItem("G1", "y"), SetItem("G2", "z"), SetItem("G3", "w"), SetItem("G4", "v")))
        (spot,) = find_blind_spots([s], ["g0", "g1"], BlindSpotsConfig()).spots
        self.assertEqual((spot.owned, spot.total, spot.skipped_items), (2, 5, 3))

    def test_dismissed_set_is_suppressed(self):
        r = find_blind_spots([make_set("a")], owned(0, 1), BlindSpotsConfig(), dismissed=[dismiss_key("a")])
        self.assertEqual((r.spots, r.suppressed), ((), 1))

    def test_unknown_kind_left_out(self):
        r = find_blind_spots([make_set("a", kind="mystery")], owned(0, 1), BlindSpotsConfig())
        self.assertEqual(r.left_out, (("a", "unknown_kind"),))

    def test_ranked_by_share_owned_then_key_and_limited(self):
        sets = [make_set("b"), make_set("a"), make_set("c")]
        r = find_blind_spots(sets, owned(0, 1, 2), BlindSpotsConfig(limit=2))
        self.assertEqual([s.set.key for s in r.spots], ["a", "b"])

    def test_card_states_counts_never_advice_and_caps_list(self):
        r = find_blind_spots([make_set("a", 20, artist="Miles")], owned(0, 1, 2), BlindSpotsConfig())
        card = blind_spot_card(r.spots[0], BlindSpotsConfig(max_missing_listed=4))
        self.assertEqual(card["kind"], "blind_spot")
        self.assertEqual(card["body"], "You own 3 of 20 in this set; 17 not in your library.")
        self.assertEqual((len(card["missing"]), card["missing_total"]), (4, 17))
        self.assertNotIn("should", card["body"].lower())
        self.assertEqual(card["actions"], [{"kind": "dismiss"}])
        self.assertEqual(card["subject"]["key"], "blind_spot:a")
        self.assertEqual(card["reasons"][0]["evidence"], {"set_kind": "studio_discography", "source": "musicbrainz", "owned": 3, "total": 20})


if __name__ == "__main__":
    unittest.main()
