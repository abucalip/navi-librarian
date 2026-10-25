import json
import unittest

from discovery.allocation_contract import AllocationCandidate, AllocationResult
from discovery.lens_metrics import lens_evaluation, lens_list_metrics, lens_set_metrics
from discovery.lenses import partition_lenses


def item(cid, artist=None, album=None, category="adjacent", score=1.0, genre=None, tags=(), audience=None, seed=None):
    return AllocationCandidate(
        candidate_id=cid, artist_key=artist or cid, album_key=album or cid, category=category,
        score=score, genre_family=genre, tags=tags, audience=audience, seed=seed,
    )


def result(lens, ids):
    return AllocationResult(requested_count=5, selected_candidate_ids=tuple(ids),
                            ownership_review_candidate_ids=(), decisions=(),
                            category_counts={}, checked_count=0, lens=lens)


POOL = [
    item("a", genre="rock", tags=("x", "y"), score=2.0, audience=1000),
    item("b", genre="rock", tags=("x", "z"), score=1.0, audience=200_000, category="adventurous"),
    item("c", genre="jazz", tags=("q",), score=3.0),
    item("d", score=0.5),
]


class ListMetricsTests(unittest.TestCase):
    def test_spread_score_tags_and_obscurity(self):
        m = lens_list_metrics(result("now", "abcd"), POOL)
        self.assertEqual((m["size"], m["distinct_families"], m["largest_family"]), (4, 2, 2))
        self.assertEqual(m["family_entropy"], 0.9183)
        self.assertEqual(m["mean_pairwise_tag_jaccard"], 0.1111)  # tagged pairs ab 1/3, ac 0, bc 0; d is untagged
        self.assertEqual((m["mean_score"], m["min_score"]), (1.625, 0.5))
        self.assertEqual((m["untagged_picks"], m["unknown_family_picks"], m["adventurous_picks"]), (1, 1, 1))
        self.assertEqual((m["known_audience_picks"], m["median_audience"], m["obscure_share"]), (2, 100500.0, 0.5))
        self.assertEqual(lens_list_metrics(result("now", "a"), POOL, obscure_ceiling=500)["obscure_share"], 0.0)

    def test_empty_list_has_no_averages(self):
        m = lens_list_metrics(result("now", []), POOL)
        self.assertEqual((m["size"], m["mean_score"], m["obscure_share"], m["family_entropy"]), (0, None, None, 0.0))


class SetMetricsTests(unittest.TestCase):
    def test_union_overlap_and_reference(self):
        pool = POOL + [item("e", artist="a")]
        lists = [result("one", "ab"), result("two", "be"), result("three", "c")]
        m = lens_set_metrics(lists, pool, reference=result("prod", "bc"))
        self.assertEqual((m["lists"], m["total_picks"], m["union_albums"], m["union_artists"]), (3, 5, 4, 3))
        self.assertEqual(m["pairwise_overlap"]["one|two"], {"albums": 1, "artists": 2})
        self.assertEqual(m["pairwise_overlap"]["one|three"], {"albums": 0, "artists": 0})
        self.assertEqual(m["overlap_with_reference"], {"one": 1, "two": 1, "three": 1})

    def test_same_album_under_different_candidate_ids_counts_once(self):
        pool = [item("p", artist="x", album="shared"), item("q", artist="y", album="shared"),
                item("r", artist="z", album="solo"), item("s", artist="w", album="shared")]
        lists = [result("one", ["p", "r"]), result("two", ["q"])]
        m = lens_set_metrics(lists, pool, reference=result("prod", ["s"]))
        self.assertEqual(m["pairwise_overlap"]["one|two"], {"albums": 1, "artists": 0})
        self.assertEqual((m["total_picks"], m["union_albums"]), (3, 2))
        self.assertEqual(m["overlap_with_reference"], {"one": 1, "two": 1})

    def test_repeated_album_identity_within_one_list_still_counts_each_pick(self):
        pool = [item("p", artist="x", album="shared"), item("q", artist="y", album="shared")]
        m = lens_set_metrics([result("one", ["p", "q"])], pool)
        self.assertEqual((m["total_picks"], m["union_albums"]), (2, 1))

    def test_duplicate_lens_names_rejected(self):
        with self.assertRaises(ValueError):
            lens_set_metrics([result("x", "a"), result("x", "b")], POOL)


class EvaluationTests(unittest.TestCase):
    def test_partitioned_lists_have_zero_overlap_and_serialize(self):
        pool = [item(f"d{i}", score=0.035, audience=2000, seed=f"s{i}", tags=("a", "b"), category="adventurous")
                for i in range(3)]
        pool += [item(f"m{i}", score=5 - i * 0.1, genre=("rock", "jazz", "soul")[i % 3], tags=(f"t{i}",))
                 for i in range(9)]
        results = partition_lenses(pool, 3)
        report = lens_evaluation(results, pool)
        self.assertEqual([m["lens"] for m in report["lists"]], ["deep_cuts", "current_tastes", "genre_spread"])
        self.assertTrue(all(v == {"albums": 0, "artists": 0} for v in report["set"]["pairwise_overlap"].values()))
        self.assertEqual(report["set"]["union_albums"], report["set"]["total_picks"])
        json.dumps(report)


if __name__ == "__main__":
    unittest.main()
