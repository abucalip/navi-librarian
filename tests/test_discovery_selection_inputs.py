"""Direct tests for allocation-input building and selection-policy options."""
import unittest

from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
from discovery.allocation_inputs import build_allocation_inputs, classify_ownership
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
