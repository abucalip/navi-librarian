"""Tests for the Star Operation S1a "because" field on personal picks."""
import unittest

from discovery.pick_because import (
    build_because, build_pick_context_lookup, build_seed_because, record_seed_tag,
)


def _key(value):
    return str(value).strip().casefold()


def _listen(name, mbid):
    return {"track_metadata": {"artist_name": name, "additional_info": {"artist_mbid": mbid}}}


class BuildBecauseTests(unittest.TestCase):
    def test_no_names_gives_no_because(self):
        self.assertIsNone(build_because([]))
        self.assertIsNone(build_because(["", None]))

    def test_names_give_similar_artists_kind_and_drop_empty_values(self):
        self.assertEqual(
            build_because(["Jazz One", "", "Jazz Two"]),
            {"kind": "similar_artists", "names": ["Jazz One", "Jazz Two"]},
        )


class PickContextLookupTests(unittest.TestCase):
    def setUp(self):
        listens = [_listen("Jazz One", "j1")] * 3 + [_listen("Soul One", "s1")]
        self.genres = {"j1": ["jazz", "bebop"], "s1": ["soul"], "candidate": ["jazz"]}
        self.lookup = build_pick_context_lookup(listens, self.genres, _key)

    def test_shared_tags_give_similar_to_and_because(self):
        context = self.lookup({"artist_mbid": "candidate", "primary_artist": "New Artist"})
        self.assertEqual(context["similar_to"], ["Jazz One"])
        self.assertEqual(context["because"], {"kind": "similar_artists", "names": ["Jazz One"]})

    def test_no_shared_tag_gives_empty_similar_to_and_no_because_key(self):
        context = self.lookup({"artist_mbid": "unknown", "primary_artist": "New Artist"})
        self.assertEqual(context, {"similar_to": []})
        self.assertNotIn("because", context)

    def test_candidate_only_overlapping_its_own_artist_gives_no_because(self):
        # The profile artist is the candidate's own artist, which is never listed.
        lookup = build_pick_context_lookup(
            [_listen("Same Artist", "c")], {"c": ["jazz"]}, _key)
        context = lookup({"artist_mbid": "c", "primary_artist": "Same Artist"})
        self.assertEqual(context, {"similar_to": []})

    def test_similar_to_matches_the_existing_lookup_exactly(self):
        from discovery.similar_artists import build_similar_to_lookup
        listens = [_listen("Jazz One", "j1"), _listen("Jazz Two", "j2")]
        genres = {"j1": ["jazz"], "j2": ["jazz", "bebop"], "candidate": ["jazz", "bebop"]}
        candidate = {"artist_mbid": "candidate", "primary_artist": "New Artist"}
        expected = build_similar_to_lookup(listens, genres, _key)(candidate)
        context = build_pick_context_lookup(listens, genres, _key)(candidate)
        self.assertEqual(context["similar_to"], expected)


class SeedTagTests(unittest.TestCase):
    def test_profile_style_records_tag_and_ignores_duplicates(self):
        candidate = {}
        record_seed_tag(candidate, "profile:jazz", "jazz")
        record_seed_tag(candidate, "profile:jazz_2", "jazz")
        record_seed_tag(candidate, "profile:cafe_jazz", "café jazz")
        self.assertEqual(candidate["seed_tags"], ["jazz", "café jazz"])

    def test_exploration_style_and_empty_tag_record_nothing(self):
        candidate = {}
        record_seed_tag(candidate, "explore:rai", "rai")
        record_seed_tag(candidate, "profile:rai", "")
        record_seed_tag(candidate, "profile:rai", None)
        self.assertNotIn("seed_tags", candidate)

    def test_build_seed_because_shape_cap_and_absence(self):
        self.assertIsNone(build_seed_because(None))
        self.assertIsNone(build_seed_because([]))
        self.assertEqual(build_seed_because(["a", "b", "c", "d"]),
                         {"kind": "tag", "names": ["a", "b", "c"]})

    def test_seed_tag_wins_over_similar_artists(self):
        listens = [_listen("Jazz One", "j1")]
        lookup = build_pick_context_lookup(listens, {"j1": ["jazz"], "c": ["jazz"]}, _key)
        context = lookup({"artist_mbid": "c", "primary_artist": "New", "seed_tags": ["jazz"]})
        self.assertEqual(context["because"], {"kind": "tag", "names": ["jazz"]})
        self.assertEqual(context["similar_to"], ["Jazz One"])

    def test_seed_tag_alone_gives_because_without_similar_artists(self):
        lookup = build_pick_context_lookup([], {}, _key)
        context = lookup({"artist_mbid": "c", "primary_artist": "New", "seed_tags": ["rai"]})
        self.assertEqual(context, {"similar_to": [], "because": {"kind": "tag", "names": ["rai"]}})

    def test_candidate_without_seed_keeps_similar_artists_form(self):
        lookup = build_pick_context_lookup(
            [_listen("Jazz One", "j1")], {"j1": ["jazz"], "c": ["jazz"]}, _key)
        context = lookup({"artist_mbid": "c", "primary_artist": "New"})
        self.assertEqual(context["because"]["kind"], "similar_artists")


if __name__ == "__main__":
    unittest.main()
