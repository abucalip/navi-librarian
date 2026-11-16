import json
import unittest

from discovery.deep_dive_bridge import bridge_albums, deep_dive_pool, lens_families
from discovery.list_payload import build_lens_list_response


def music_key(value):
    return "".join(str(value or "").casefold().split())


def dive(artist, album, genres, families=None):
    item = {"artist": artist, "album": album, "genres": genres, "reason": "Missing album"}
    if families is not None:
        item["genre_families"] = families
    return item


LENS_ALBUMS = [
    {"artist": "L1", "album": "A1", "tags": ["ethiopian jazz", "jazz"], "rank": 1},
    {"artist": "L2", "album": "A2", "tags": ["black metal"], "rank": 2},
]
PAYLOAD = {
    "items": [
        dive("J1", "Jazz One", ["jazz"]),
        dive("J2", "Jazz Two", ["jazz", "ethiopian jazz"]),
        dive("J3", "Jazz Three", ["jazz"]),
        dive("M1", "Metal One", ["black metal"]),
        dive("P1", "Pop One", ["pop"]),
    ],
    "extra_items": [dive("J1", "Jazz One Again", ["jazz"])],
}


class FamiliesTests(unittest.TestCase):
    def test_families_of_albums_and_seeds_most_common_first(self):
        found = lens_families(LENS_ALBUMS, ["ethiopian jazz"])
        self.assertEqual(set(found), {"jazz", "african", "metal"})
        self.assertEqual(found[-1], "metal")  # one album, against two for the others

    def test_nothing_represented_gives_nothing(self):
        self.assertEqual(lens_families([], []), [])
        self.assertEqual(lens_families([{"tags": None}, "x"], [None]), [])


class PoolTests(unittest.TestCase):
    def test_pool_is_items_then_extra_items_and_tolerates_old_payloads(self):
        self.assertEqual(len(deep_dive_pool(PAYLOAD)), 6)
        self.assertEqual(len(deep_dive_pool({"items": [dive("A", "B", [])]})), 1)
        self.assertEqual(deep_dive_pool(None), [])
        self.assertEqual(deep_dive_pool({"items": "bad"}), [])


class BridgeTests(unittest.TestCase):
    def bridge(self, **kwargs):
        return bridge_albums("current_tastes", LENS_ALBUMS, [], PAYLOAD, music_key, **kwargs)

    def test_per_family_cap_and_tag_overlap_first(self):
        out = self.bridge()
        # "ethiopian jazz" is both an african and a jazz tag: african takes Jazz Two (it shares the
        # most tags with the list), then jazz takes two more, the Deep Dives order deciding.
        jazz = [a["album"] for a in out if "jazz" in a["tags"]]
        self.assertEqual(jazz, ["Jazz Two", "Jazz One", "Jazz Three"])
        self.assertIn("Metal One", [a["album"] for a in out])
        self.assertNotIn("Pop One", [a["album"] for a in out])

    def test_one_artist_may_supply_several_albums(self):
        out = self.bridge(per_family=5)
        self.assertEqual([a["album"] for a in out if a["artist"] == "J1"], ["Jazz One", "Jazz One Again"])

    def test_labelled_and_in_lens_shape(self):
        first = self.bridge()[0]
        self.assertEqual(first["bridge_label"], "Discover more " + first["artist"])
        self.assertEqual(first["reason"], first["bridge_label"])
        self.assertEqual(first["deep_dive_reason"], "Missing album")
        self.assertEqual(first["source"], "deep_dive")
        self.assertEqual(first["lens"], "current_tastes")
        self.assertEqual(first["primary_artist"], first["artist"])
        self.assertIsNone(first["seed_tag"])
        self.assertEqual(first["tags"], ["jazz", "ethiopian jazz"])

    def test_total_cap(self):
        self.assertEqual(len(self.bridge(total=1)), 1)
        self.assertEqual(self.bridge(total=0), [])

    def test_skips_albums_already_listed_and_excluded_ones(self):
        listed = [{"artist": "J2", "album": "Jazz Two", "tags": ["jazz"]}]
        out = bridge_albums("deep_cuts", listed, [], PAYLOAD, music_key,
                            is_excluded=lambda item: item["artist"] == "J1", per_family=9)
        self.assertEqual([a["album"] for a in out], ["Jazz Three"])

    def test_no_deep_dives_list_gives_nothing(self):
        self.assertEqual(bridge_albums("deep_cuts", LENS_ALBUMS, [], None, music_key), [])

    def test_stored_families_are_used_and_underscores_match(self):
        payload = {"items": [dive("S", "Sw", ["whatever"], families=["hip_hop"])]}
        albums = [{"artist": "X", "album": "Y", "tags": ["hip hop"]}]
        out = bridge_albums("obsessions", albums, [], payload, music_key)
        self.assertEqual([a["album"] for a in out], ["Sw"])


class ResponseTests(unittest.TestCase):
    cached = {"generated_at": 1.0, "payload": {
        "label": "Current tastes", "day": "2026-11-16", "seed_tags": ["jazz"],
        "albums": [{"artist": "L1", "album": "A1", "tags": ["jazz"]}]}}

    def test_extras_follow_the_count_and_continue_ranks(self):
        body = json.loads(build_lens_list_response(
            "current_tastes", 10, self.cached, None,
            bridge=lambda albums, seeds: [{"artist": "J", "album": "Z", "bridge_label": "Discover more J"}]))
        self.assertEqual([i["rank"] for i in body["items"]], [1, 2])
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["bridged_count"], 1)

    def test_a_failing_bridge_leaves_the_list_alone(self):
        def boom(_albums, _seeds):
            raise RuntimeError("x")
        body = json.loads(build_lens_list_response("current_tastes", 10, self.cached, None, bridge=boom))
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["bridged_count"], 0)

    def test_no_bridge_changes_nothing_but_the_zero_count(self):
        body = json.loads(build_lens_list_response("current_tastes", 10, self.cached, None))
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["bridged_count"], 0)


if __name__ == "__main__":
    unittest.main()
