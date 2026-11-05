import unittest

from intelligence.insights import CanonConfig, WorldAlbum, canon_card, find_hidden_canon
from intelligence.insights.hidden_canon import dismiss_key

TASTE = ["Jazz", "Soul", "Funk"]


def album(i, listens=5000, genres=("jazz",), artist=None, **kw):
    return WorldAlbum(f"G{i}", f"T{i}", artist or f"A{i}", 1970 + i, genres, listens, **kw)


class HiddenCanonTests(unittest.TestCase):
    def test_no_candidates_supplied(self):
        self.assertEqual(find_hidden_canon([], [], TASTE).empty_reason, "no_candidates_supplied")

    def test_sparse_taste_is_empty_not_guessed(self):
        r = find_hidden_canon([album(1)], [], ["jazz"])
        self.assertEqual((r.picks, r.empty_reason), ((), "sparse_taste"))

    def test_owned_excluded_case_insensitive_and_counted(self):
        r = find_hidden_canon([album(1), album(2)], ["g1"], TASTE)
        self.assertEqual([p.album.group_mbid for p in r.picks], ["g2"])
        self.assertEqual(r.owned_excluded, 1)

    def test_genre_must_match_top_genres_only(self):
        r = find_hidden_canon([album(1, genres=("metal",)), album(2, genres=("SOUL",))], [], TASTE,
                              CanonConfig(top_genres=2))
        self.assertEqual([p.album.group_mbid for p in r.picks], ["g2"])
        r = find_hidden_canon([album(3, genres=("funk",))], [], TASTE, CanonConfig(top_genres=2))
        self.assertEqual(r.empty_reason, "no_candidates")

    def test_drops_missing_mbid_duplicates_and_low_listens(self):
        pool = [WorldAlbum(None, "x", "a", None, ("jazz",), 9000), album(1), album(1), album(2, listens=10)]
        r = find_hidden_canon(pool, [], TASTE)
        self.assertEqual(len(r.picks), 1)
        self.assertEqual(r.dropped, 3)

    def test_score_is_popularity_times_genre_weight(self):
        r = find_hidden_canon([album(1, 10000, ("jazz",)), album(2, 10000, ("funk",))], [], TASTE)
        by = {p.album.group_mbid: p for p in r.picks}
        self.assertEqual(by["g1"].score, 1.0)
        self.assertAlmostEqual(by["g2"].score, 1 - 2 / 3, places=5)
        self.assertEqual([p.album.group_mbid for p in r.picks], ["g1", "g2"])

    def test_best_matching_genre_is_used(self):
        (p,) = find_hidden_canon([album(1, genres=("funk", "soul"))], [], TASTE).picks
        self.assertEqual((p.matched_genre, p.genre_rank), ("soul", 1))

    def test_max_per_artist(self):
        pool = [album(i, 9000 - i, artist="Same") for i in range(1, 5)] + [album(9, 100000, artist="Other")]
        r = find_hidden_canon(pool, [], TASTE, CanonConfig(max_per_artist=2))
        self.assertEqual(sorted(p.album.artist for p in r.picks), ["Other", "Same", "Same"])

    def test_dismissed_is_suppressed(self):
        r = find_hidden_canon([album(1), album(2)], [], TASTE, dismissed=[dismiss_key("g1")])
        self.assertEqual([p.album.group_mbid for p in r.picks], ["g2"])
        self.assertEqual(r.suppressed, 1)

    def test_limit(self):
        r = find_hidden_canon([album(i) for i in range(1, 8)], [], TASTE, CanonConfig(limit=3))
        self.assertEqual(len(r.picks), 3)

    def test_card_states_facts_without_advice(self):
        (p,) = find_hidden_canon([album(1, 12345)], [], TASTE).picks
        c = canon_card(p)
        self.assertEqual(c["kind"], "hidden_canon")
        self.assertIn("12,345", c["body"])
        self.assertIn("not in your library", c["body"])
        self.assertNotIn("should", c["body"].lower())
        self.assertEqual(c["actions"], [{"kind": "dismiss"}])
        self.assertEqual(c["subject"]["key"], "hidden_canon:g1")


if __name__ == "__main__":
    unittest.main()
