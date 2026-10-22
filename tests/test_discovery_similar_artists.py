"""Tests for the pure "similar to" lookup."""
import unittest

from discovery.similar_artists import build_profile_artists, similar_library_artists


def _key(value):
    return str(value).strip().casefold()


def _listen(name, mbid):
    return {"track_metadata": {"artist_name": name, "additional_info": {"artist_mbid": mbid}}}


class BuildProfileArtistsTests(unittest.TestCase):
    def test_counts_plays_and_skips_artists_without_tags_or_ids(self):
        listens = [_listen("A", "a"), _listen("A", "a"), _listen("B", "b"), _listen("C", "c"),
                   {"track_metadata": {"artist_name": "NoId"}}]
        profile = build_profile_artists(listens, {"a": ["jazz"], "b": ["soul"], "c": []}, _key)
        self.assertEqual([(p["name"], p["plays"]) for p in profile], [("A", 2), ("B", 1)])

    def test_reads_the_first_of_artist_mbids(self):
        listen = {"track_metadata": {"artist_name": "A", "additional_info": {"artist_mbids": ["a"]}}}
        self.assertEqual(len(build_profile_artists([listen], {"a": ["jazz"]}, _key)), 1)


class SimilarLibraryArtistsTests(unittest.TestCase):
    def setUp(self):
        listens = [_listen("Jazz One", "j1")] * 3 + [_listen("Jazz Two", "j2")] + [
            _listen("Soul One", "s1"), _listen("Rock One", "r1")]
        self.profile = build_profile_artists(listens, {
            "j1": ["jazz", "bebop"], "j2": ["jazz", "bebop", "hard bop"],
            "s1": ["soul"], "r1": ["rock"]}, _key)

    def test_ranks_by_shared_tags_then_plays_and_ignores_unrelated(self):
        names = similar_library_artists(["Jazz", "Bebop", "Hard Bop"], "candidate", self.profile)
        self.assertEqual(names, ["Jazz Two", "Jazz One"])

    def test_ties_go_to_the_artist_played_more(self):
        self.assertEqual(similar_library_artists(["jazz"], "candidate", self.profile),
                         ["Jazz One", "Jazz Two"])

    def test_never_lists_the_candidates_own_artist(self):
        self.assertNotIn("Jazz One", similar_library_artists(["jazz"], "jazz one", self.profile))

    def test_no_tags_or_no_overlap_gives_an_empty_list(self):
        self.assertEqual(similar_library_artists([], "candidate", self.profile), [])
        self.assertEqual(similar_library_artists(["polka"], "candidate", self.profile), [])

    def test_limit_applies(self):
        self.assertEqual(len(similar_library_artists(["jazz", "soul", "rock"], "c", self.profile, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()


class SimilarToUiContractTests(unittest.TestCase):
    def setUp(self):
        with open("static/app.js", encoding="utf-8") as handle:
            self.js = handle.read()

    def test_adjacent_rows_show_similar_to_and_other_categories_keep_their_label(self):
        self.assertIn("item.discovery_category === 'adjacent' && similar.length", self.js)
        self.assertIn("'Similar to: ' + similar.join(', ')", self.js)
        self.assertIn("return categoryLabel(item.discovery_category);", self.js)

    def test_discover_and_personal_rows_use_the_same_line(self):
        self.assertGreaterEqual(self.js.count("categoryLine("), 3)
