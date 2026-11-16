import json
import unittest

from discovery.deep_dive_bridge import bridge_albums, deep_dive_pool, lens_families
from discovery.list_payload import build_cached_discovery_list_response, build_lens_list_response


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


class OtherListsTests(unittest.TestCase):
    def test_genres_and_stored_families_drive_the_match_and_no_lens_is_set(self):
        shown = [{"artist": "P", "album": "Q", "genres": ["black metal"]}]
        out = bridge_albums(None, shown, [], PAYLOAD, music_key)
        self.assertEqual([a["album"] for a in out], ["Metal One"])
        self.assertNotIn("lens", out[0])
        stored = [{"artist": "P", "album": "Q", "genre_families": ["hip_hop"]}]
        payload = {"items": [dive("S", "Sw", ["x"], families=["hip-hop"])]}
        self.assertEqual([a["album"] for a in bridge_albums(None, stored, [], payload, music_key)], ["Sw"])

    def respond(self, name, items, *, bridge, count=10, feedback=(), key="items"):
        cached = {"generated_at": 1.0, "payload": {key: items}}
        return json.loads(build_cached_discovery_list_response(
            name, count, lambda _n: cached, list(feedback), {}, music_key,
            lambda item: bool(item.get("album")), bridge=bridge))

    def test_each_list_is_bridged_after_its_own_items(self):
        for name, key in (("personal", "recommendations"), ("classics", "items"), ("new_releases", "items")):
            items = [{"artist": "P", "album": "Q", "genres": ["black metal"]}]
            seen = []

            def bridge(shown, hidden):
                seen.append(hidden({"artist": "P", "album": "Q"}))
                return bridge_albums(None, shown, [], PAYLOAD, music_key, is_excluded=hidden)

            body = self.respond(name, items, bridge=bridge, key=key)
            self.assertEqual([i["album"] for i in body["items"]], ["Q", "Metal One"], name)
            self.assertEqual(body["bridged_count"], 1)
            self.assertEqual(body["count"], 1)
            if name == "personal":
                self.assertEqual(len(body["recommendations"]), 2)

    def test_hidden_covers_dismissed_albums(self):
        feedback = [{"scope": "album", "status": "not_for_me", "artist_key": "m1", "album_key": "metalone"}]
        items = [{"artist": "P", "album": "Q", "genres": ["black metal"]}]
        body = self.respond("classics", items, feedback=feedback, bridge=lambda shown, hidden: bridge_albums(
            None, shown, [], PAYLOAD, music_key, is_excluded=hidden))
        self.assertEqual([i["album"] for i in body["items"]], ["Q"])

    def test_other_lists_and_failures_are_untouched(self):
        items = [{"artist": "P", "album": "Q", "genres": ["black metal"]}]
        body = self.respond("artist_deep_dive", items, bridge=lambda s, h: [{"album": "no"}])
        self.assertEqual(len(body["items"]), 1)
        self.assertNotIn("bridged_count", body)

        def boom(_s, _h):
            raise RuntimeError("x")
        body = self.respond("classics", items, bridge=boom)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["bridged_count"], 0)
        self.assertNotIn("bridged_count", self.respond("classics", items, bridge=None))


if __name__ == "__main__":
    unittest.main()
