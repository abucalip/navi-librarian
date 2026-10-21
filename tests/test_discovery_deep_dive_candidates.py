import unittest

from discovery.deep_dive_candidates import (
    collect_missing_album_candidates,
    collect_similar_artist_candidates,
    enrich_candidate_genres,
    merge_resolved_pool_candidates,
)


def key(value):
    return str(value).lower().strip()


def album(artist, name, listeners=1):
    return {"artist": artist, "album": name, "lastfm_listeners": listeners}


class MissingAlbumTests(unittest.TestCase):
    def test_skips_owned_and_prefers_larger_anchor_and_paces(self):
        anchors = [{"name": f"A{i}", "album_count": 3 + i} for i in range(7)]
        tops = {"A6": [album("X", "One"), album("X", "Owned")], "A5": [album("x", "one")]}
        pauses = []
        out = {}
        collect_missing_album_candidates(
            anchors, {("x", "owned")}, out,
            top_albums_lookup=lambda n, limit: tops.get(n, []),
            music_key=key, pause=lambda: pauses.append(1),
        )
        self.assertEqual(list(out), [("x", "one")])
        self.assertEqual(out[("x", "one")]["anchor_artist"], "A6")
        self.assertEqual(len(pauses), 1)  # index 5 only

    def test_equal_anchor_count_keeps_first(self):
        anchors = [{"name": "A", "album_count": 3}, {"name": "B", "album_count": 3}]
        out = {}
        collect_missing_album_candidates(
            anchors, set(), out,
            top_albums_lookup=lambda n, limit: [album("X", "One")], music_key=key,
        )
        self.assertEqual(out[("x", "one")]["anchor_artist"], "A")


class ResolvedPoolTests(unittest.TestCase):
    anchors = {"band": {"name": "Band", "album_count": 4}}

    def test_filters_and_enriches(self):
        pool = [
            {"artist": "Band", "album": "New", "score": "bad", "mbid": "m"},
            {"artist": "Band", "album": "Sel", "selection_decision": "selected"},
            {"artist": "Band", "album": "Own", "exact_owned": True},
            {"artist": "Band", "album": "Have"},
            {"artist": "Other", "album": "X"},
            {"artist": "Band", "album": ""},
        ]
        out = {}
        merge_resolved_pool_candidates(
            pool, self.anchors, {("band", "have")}, out, music_key=key)
        self.assertEqual(list(out), [("band", "new")])
        self.assertEqual(out[("band", "new")]["candidate_pool_score"], 0.0)
        self.assertEqual(out[("band", "new")]["anchor_album_count"], 4)

    def test_existing_candidate_is_annotated_not_replaced(self):
        existing = {"artist": "Band", "album": "New", "marker": 1}
        out = {("band", "new"): existing}
        merge_resolved_pool_candidates(
            [{"artist": "Band", "album": "New", "discovery_score": 2.5,
              "assigned_category": "adjacent"}],
            self.anchors, set(), out, music_key=key)
        self.assertIs(out[("band", "new")], existing)
        self.assertTrue(existing["also_found_in_resolved_candidate_pool"])
        self.assertEqual(existing["candidate_pool_score"], 2.5)

    def test_non_list_pool_is_ignored(self):
        out = {}
        merge_resolved_pool_candidates(None, self.anchors, set(), out, music_key=key)
        merge_resolved_pool_candidates({"a": 1}, self.anchors, set(), out, music_key=key)
        self.assertEqual(out, {})


class SimilarArtistTests(unittest.TestCase):
    def test_scores_best_anchor_and_skips_owned(self):
        anchors = [{"name": "Big", "album_count": 20}, {"name": "Small", "album_count": 3}]
        sims = {
            "Big": [{"artist": "Sim", "similarity": 0.5}, {"artist": "Mine", "similarity": 1}],
            "Small": [{"artist": "Sim", "similarity": 0.5}],
        }
        out = {}
        collect_similar_artist_candidates(
            anchors, {"mine": 1}, {("sim", "own")}, out,
            similar_artists_lookup=lambda n, limit: sims[n],
            top_albums_lookup=lambda n, limit: [album("Sim", "Rec"), album("Sim", "Own")],
            music_key=key)
        self.assertEqual(list(out), [("sim", "rec")])
        item = out[("sim", "rec")]
        self.assertEqual(item["anchor_artist"], "Big")
        self.assertEqual(item["similar_artist_score"], round(0.5 * (1 + 15 / 30), 4))
        self.assertEqual(item["discovery_type"], "similar_artist")


class GenreTests(unittest.TestCase):
    def test_inherits_from_anchor_and_caches_lookups(self):
        calls = []
        tags = {"Anchor": ["post-rock"], "Sparse": []}

        def lookup(name):
            calls.append(name)
            return tags[name]

        items = [
            {"artist": "Sparse", "anchor_artist": "Anchor"},
            {"artist": "Sparse", "anchor_artist": "Anchor"},
        ]
        enrich_candidate_genres(
            items, artist_genres=lookup,
            genre_families=lambda t: ["rock"] if t else [], music_key=key)
        self.assertEqual(items[0]["genres"], ["post-rock"])
        self.assertTrue(items[0]["genre_inherited_from_anchor"])
        self.assertEqual(items[1]["genre_families"], ["rock"])
        self.assertEqual(calls.count("Sparse"), 1)
        self.assertEqual(calls.count("Anchor"), 1)

    def test_generic_tags_fall_back_to_anchor_families(self):
        tags = {"Sparse": ["seen live"], "Anchor": ["jazz"]}
        fam = lambda t: ["jazz"] if "jazz" in t else []
        item = {"artist": "Sparse", "anchor_artist": "Anchor"}
        enrich_candidate_genres(
            [item], artist_genres=lambda n: tags[n], genre_families=fam, music_key=key)
        self.assertEqual(item["genres"], ["jazz"])
        self.assertEqual(item["genre_families"], ["jazz"])
        self.assertTrue(item["genre_inherited_from_anchor"])

    def test_existing_genres_make_no_lookup(self):
        item = {"artist": "A", "genres": ["x"], "genre_families": ["f"]}
        enrich_candidate_genres(
            [item], artist_genres=lambda n: self.fail("lookup"),
            genre_families=lambda t: self.fail("families"), music_key=key)
        self.assertEqual(item["genres"], ["x"])


if __name__ == "__main__":
    unittest.main()
