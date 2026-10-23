"""Direct tests for allocation-input building and selection-policy options."""
import unittest

from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
from discovery.allocation_inputs import (
    build_allocation_inputs, classify_ownership, deep_cuts_fields,
)
from discovery.selection_policy import (
    quota_targets, selection_policy_report, selection_request_options,
)


def key(value):
    return str(value).casefold().replace(" ", "")


def album(title, artist, mbid="m", category="adjacent", score=1.0):
    return {
        "album": title, "primary_artist": artist, "artist_mbid": mbid,
        "discovery_category": category, "discovery_score": score,
    }


class OwnershipTests(unittest.TestCase):
    def test_same_title_same_artist_is_exact_owned(self):
        library = {"bluetrain": [{"artist": "John Coltrane"}]}
        title_key, status = classify_ownership(album("Blue Train", "john coltrane"), library, key)
        self.assertEqual((title_key, status), ("bluetrain", OwnershipStatus.EXACT_OWNED))

    def test_same_title_other_artist_is_a_conflict(self):
        library = {"bluetrain": [{"artist": "Someone Else"}]}
        _, status = classify_ownership(album("Blue Train", "John Coltrane"), library, key)
        self.assertEqual(status, OwnershipStatus.TITLE_CONFLICT)

    def test_unknown_title_is_clear(self):
        _, status = classify_ownership(album("Kind of Blue", "Miles Davis"), {}, key)
        self.assertEqual(status, OwnershipStatus.CLEAR)


class BuildInputsTests(unittest.TestCase):
    def test_ids_order_tags_and_genre_family_are_stable(self):
        albums = {
            "a": album("Alpha", "A", mbid="1", score=2.0),
            "b": album("Beta", "B", mbid="2", category="adventurous", score=1.0),
        }
        genre_cache = {"1": ["alternative rock", "indie rock", None, "boom bap"], "2": []}
        by_id, candidates = build_allocation_inputs(
            albums.values(), library_by_title={"alpha": [{"artist": "A"}]},
            genre_cache=genre_cache, music_key=key,
            artist_identity=lambda c: key(c["primary_artist"]),
        )
        self.assertEqual(list(by_id), ["0", "1"])
        first, second = candidates
        self.assertIsInstance(first, AllocationCandidate)
        self.assertEqual(first.ownership, OwnershipStatus.EXACT_OWNED)
        self.assertEqual(first.tags, ("alternative rock", "indie rock", "boom bap"))
        self.assertEqual(first.genre_family, "rock")
        self.assertEqual((second.genre_family, second.tags), (None, ()))
        self.assertEqual(second.category, "adventurous")
        self.assertEqual(second.source_order, 1)


class DeepCutsFieldsTests(unittest.TestCase):
    lane = {"regional_styles": ["profile:post_punk", "explore:x"], "release_group_mbid": "g1"}

    def test_audience_is_album_level_only(self):
        pop = {"g1": {"album_listeners": 900, "artist_listeners": 5000, "basis": "album"}}
        self.assertEqual(deep_cuts_fields(self.lane, pop)["audience"], 900)
        pop = {"g1": {"album_listeners": None, "artist_listeners": 5000, "basis": "artist"}}
        self.assertIsNone(deep_cuts_fields(self.lane, pop)["audience"])
        pop = {"g1": {"album_listeners": None, "artist_listeners": None, "basis": "none"}}
        self.assertIsNone(deep_cuts_fields(self.lane, pop)["audience"])

    def test_seed_is_first_style_and_missing_popularity_leaves_audience_unset(self):
        self.assertEqual(deep_cuts_fields(self.lane, None), {"seed": "profile:post_punk"})
        self.assertEqual(deep_cuts_fields(self.lane, {}), {"seed": "profile:post_punk"})
        self.assertIsNone(deep_cuts_fields(self.lane, {"other": {}}).get("audience"))

    def test_non_lane_candidates_are_not_eligible(self):
        pop = {"g1": {"album_listeners": 900, "artist_listeners": 900, "basis": "album"}}
        self.assertEqual(deep_cuts_fields({"release_group_mbid": "g1"}, pop), {"seed": None})

    def test_tag_strength_is_read_when_present(self):
        pop = {"g1": {"album_listeners": 900, "artist_listeners": None, "basis": "album"}}
        out = deep_cuts_fields({**self.lane, "tag_strength": 0.7}, pop)
        self.assertEqual(out["tag_strength"], 0.7)

    def test_build_inputs_threads_fields_into_candidates_and_the_lens(self):
        from discovery.lenses import DEEP_CUTS, run_lens
        albums = [
            {**album("Deep", "A", mbid="1"), **self.lane},
            {**album("Popular", "B", mbid="2"), "regional_styles": ["profile:x"],
             "release_group_mbid": "g2"},
            album("Cf", "C", mbid="3"),
        ]
        pop = {"g1": {"album_listeners": 900, "artist_listeners": 1, "basis": "album"},
               "g2": {"album_listeners": 5_000_000, "artist_listeners": 1, "basis": "album"}}
        _, candidates = build_allocation_inputs(
            albums, library_by_title={}, genre_cache={"1": ["x", "y"], "2": ["x", "y"], "3": ["x", "y"]},
            music_key=key, artist_identity=lambda c: key(c["primary_artist"]), popularity=pop,
        )
        self.assertEqual([c.audience for c in candidates], [900, 5_000_000, None])
        self.assertEqual(candidates[0].seed, "profile:post_punk")
        self.assertEqual(run_lens(DEEP_CUTS, candidates, 5).selected_candidate_ids, ("0",))

    def test_artist_only_popularity_cannot_qualify_and_strength_orders_the_list(self):
        from discovery.lenses import DEEP_CUTS, run_lens
        albums = [
            {**album("Weak", "A", mbid="1"), "regional_styles": ["profile:x"],
             "release_group_mbid": "g1", "tag_strength": 2.0},
            {**album("Strong", "B", mbid="2"), "regional_styles": ["profile:y"],
             "release_group_mbid": "g2", "tag_strength": 9.0},
            {**album("ArtistOnly", "C", mbid="3"), "regional_styles": ["profile:z"],
             "release_group_mbid": "g3", "tag_strength": 99.0},
        ]
        pop = {"g1": {"album_listeners": 900, "artist_listeners": None, "basis": "album"},
               "g2": {"album_listeners": 900, "artist_listeners": None, "basis": "album"},
               "g3": {"album_listeners": None, "artist_listeners": 900, "basis": "artist"}}
        _, candidates = build_allocation_inputs(
            albums, library_by_title={}, genre_cache={k: ["x", "y"] for k in "123"},
            music_key=key, artist_identity=lambda c: key(c["primary_artist"]), popularity=pop,
        )
        self.assertEqual(run_lens(DEEP_CUTS, candidates, 5).selected_candidate_ids, ("1", "0"))


class SelectionPolicyTests(unittest.TestCase):
    def test_quota_targets_match_the_legacy_split(self):
        self.assertEqual(quota_targets(10), {"adjacent": 4, "cross_genre": 3, "adventurous": 3})
        self.assertEqual(quota_targets(7), {"adjacent": 2, "cross_genre": 2, "adventurous": 3})

    def test_default_and_unknown_policies_use_quotas_and_no_extra_options(self):
        for policy in ("quota", "anything-else"):
            self.assertEqual(selection_request_options(policy, 10), (quota_targets(10), {}))

    def test_family_coverage_options(self):
        targets, options = selection_request_options("family_coverage", 10)
        self.assertEqual(targets, {})
        self.assertEqual(options, {
            "genre_family_cap": 2, "category_floors": {"adventurous": 2},
            "coverage_target": 10, "coverage_floor_ratio": 0.4,
        })

    def test_report_only_under_family_coverage(self):
        candidates = [
            AllocationCandidate("0", "a", "x", "adjacent", 1.0, genre_family="rock"),
            AllocationCandidate("1", "b", "y", "adjacent", 1.0),
        ]
        self.assertEqual(selection_policy_report("quota", ["0"], candidates), {})
        self.assertEqual(
            selection_policy_report("family_coverage", ["1", "0"], candidates),
            {"selection_policy": "family_coverage", "selected_genre_families": [None, "rock"]},
        )


if __name__ == "__main__":
    unittest.main()
