"""Daily lens-list builder: gates, partition, known artists, fallback tags, payload."""
import copy
import json
import unittest

from discovery.lens_lists import (
    LENS_LIST_ORDER, LENS_LIST_SIZE, build_lens_lists, history_artist_mbids, lens_seed_queries,
    merge_artist_tags,
)
from discovery.lenses import DEEP_CUTS, NOW, OBSESSIONS, REPEATED_TRACKS, Lens
from discovery.tag_queries import tag_from_query

DAY = "2026-01-15"
SECONDS_PER_DAY = 24 * 60 * 60
TWO_TAGS = ["tag one", "tag two"]


def lane(n, artist=None, *, mbid=None, seed="profile:tag_one", strength=1.0, title=None):
    """One album shaped like the tag lane's output (placeholder names only)."""
    artist = artist or f"Artist {n}"
    return {
        "artist": artist, "primary_artist": artist,
        "artist_mbid": mbid if mbid is not None else f"mbid-{n}",
        "album": title or f"Album {n}", "release_group_mbid": f"group-{n}",
        "score": 0.035, "tag_strength": strength, "tracks": [],
        "discovery_source": "listenbrainz_tag_radio", "discovery_sources": ["profile_tag_search"],
        "regional_families": ["other"], "regional_styles": [seed],
    }


def listeners(albums, value=1_000):
    return {album["release_group_mbid"]: {"album_listeners": value} for album in albums}


def tagged(albums, tags=TWO_TAGS):
    return {album["artist_mbid"]: list(tags) for album in albums if album["artist_mbid"]}


def build(pools, *, popularity=None, tags=None, library=None, **kwargs):
    albums = [album for pool in pools.values() for album in pool]
    return build_lens_lists(
        pools, day=DAY,
        popularity=listeners(albums) if popularity is None else popularity,
        artist_tags=tagged(albums) if tags is None else tags,
        library_by_title=library or {}, **kwargs)


def picked(lists, lens):
    return [album["album"] for album in lists[lens]["albums"]]


class RecordedFixtureTests(unittest.TestCase):
    """A recorded-style day: three lens pools with the rejections a live pool shows."""

    def fixture(self):
        repeated = [lane(f"r{i}", seed=f"profile:seed_r{i % 3}", strength=20 - i) for i in range(8)]
        deep = [lane(f"d{i}", seed=f"profile:seed_d{i % 4}", strength=20 - i) for i in range(8)]
        obsessions = [lane(f"o{i}", seed=f"profile:seed_o{i % 2}", strength=20 - i) for i in range(8)]
        albums = repeated + deep + obsessions
        popularity = listeners(albums)
        popularity["group-r1"] = {"album_listeners": 120}          # under the floor
        popularity["group-d2"] = {"album_listeners": 900_000}      # over the ceiling
        del popularity["group-o3"]                                 # unresolved
        tags = tagged(albums)
        tags["mbid-d5"] = ["tag one"]                              # too few tags
        library = {"albumr3": [{"artist": "Artist r3", "artistId": "lib-1"}]}  # owned
        return ({"repeated_tracks": repeated, "deep_cuts": deep, "obsessions": obsessions},
                popularity, tags, library)

    def test_each_lens_gets_its_own_list_under_its_own_name(self):
        pools, popularity, tags, library = self.fixture()
        lists = build(pools, popularity=popularity, tags=tags, library=library,
                      known_artist_mbids={"mbid-o0"})
        self.assertEqual(list(lists), ["repeated_tracks", "deep_cuts", "obsessions"])
        self.assertEqual([lists[n]["label"] for n in lists], ["Repeated tracks", "Deep cuts", "Obsessions"])
        # Seed cap of 2: seed_r0 holds r0, r3 (owned), r6; seed_r1 holds r1 (too few
        # listeners), r4, r7; seed_r2 holds r2, r5.
        self.assertEqual(picked(lists, "repeated_tracks"),
                         ["Album r0", "Album r2", "Album r4", "Album r5", "Album r6", "Album r7"])
        self.assertEqual(picked(lists, "deep_cuts"),
                         ["Album d0", "Album d1", "Album d3", "Album d4", "Album d6", "Album d7"])
        # seed_o0: o0 (known), o2, o4 -> cap; seed_o1: o1, o3 (unresolved), o5 -> cap.
        self.assertEqual(picked(lists, "obsessions"), ["Album o1", "Album o2", "Album o4", "Album o5"])
        self.assertEqual(lists["repeated_tracks"]["decisions"],
                         {"already_owned": 1, "audience_out_of_range": 1, "selected": 6})
        self.assertEqual(lists["deep_cuts"]["decisions"],
                         {"audience_out_of_range": 1, "selected": 6, "too_few_tags": 1})
        self.assertEqual(lists["obsessions"]["decisions"], {
            "artist_already_known": 1, "audience_unknown": 1, "seed_cap_reached": 2, "selected": 4})

    def test_payload_fields(self):
        pools, popularity, tags, library = self.fixture()
        seeds = {"repeated_tracks": [("primarytype:album AND tag:\"seed r0\"", "other", "profile:seed_r0")]}
        lists = build(pools, popularity=popularity, tags=tags, library=library, seeds=seeds)
        payload = lists["repeated_tracks"]
        self.assertEqual({k: payload[k] for k in ("lens", "day", "requested", "pool_size",
                                                   "skipped_entries", "checked")},
                         {"lens": "repeated_tracks", "day": DAY, "requested": LENS_LIST_SIZE,
                          "pool_size": 8, "skipped_entries": 0, "checked": 8})
        self.assertEqual(payload["seed_tags"], ["seed r0"])
        self.assertEqual(payload["albums"][0], {
            "rank": 1, "artist": "Artist r0", "primary_artist": "Artist r0", "album": "Album r0",
            "artist_mbid": "mbid-r0", "release_group_mbid": "group-r0", "seed": "profile:seed_r0",
            "seed_tag": "seed r0", "album_listeners": 1_000, "tag_strength": 20.0,
            "tags": TWO_TAGS,
        })
        self.assertIsNone(payload["albums"][1]["seed_tag"])
        self.assertEqual([a["rank"] for a in payload["albums"]], list(range(1, 7)))

    def test_same_inputs_give_the_same_output_and_inputs_are_not_mutated(self):
        pools, popularity, tags, library = self.fixture()
        before = copy.deepcopy((pools, popularity, tags, library))
        first = build(pools, popularity=popularity, tags=tags, library=library)
        second = build(*before[:1], popularity=before[1], tags=before[2], library=before[3])
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first), json.dumps(second))
        self.assertEqual((pools, popularity, tags, library), before)

    def test_payload_is_json_serialisable(self):
        pools, popularity, tags, library = self.fixture()
        lists = build(pools, popularity=popularity, tags=tags, library=library)
        self.assertEqual(json.loads(json.dumps(lists)), lists)

    def test_ten_is_the_default_list_size(self):
        pool = [lane(f"x{i}", seed=f"profile:s{i}") for i in range(14)]
        lists = build({"deep_cuts": pool})
        self.assertEqual(len(lists["deep_cuts"]["albums"]), 10)
        self.assertEqual(lists["deep_cuts"]["decisions"], {"not_considered": 4, "selected": 10})


class PartitionTests(unittest.TestCase):
    def test_an_artist_selected_by_one_lens_is_not_in_another_list(self):
        shared = "Artist shared"
        pools = {
            "repeated_tracks": [lane("r1", shared, mbid="mbid-shared")],
            "deep_cuts": [lane("d1", shared, mbid="mbid-shared"), lane("d2")],
            "obsessions": [lane("o1", shared, mbid="mbid-shared"), lane("o2")],
        }
        lists = build(pools)
        artists = [album["primary_artist"] for payload in lists.values() for album in payload["albums"]]
        self.assertEqual(artists.count(shared), 1)
        self.assertEqual(picked(lists, "repeated_tracks"), ["Album r1"])
        self.assertEqual(picked(lists, "deep_cuts"), ["Album d2"])
        self.assertEqual(picked(lists, "obsessions"), ["Album o2"])
        # The partitioned candidate is not offered at all, so it leaves no decision.
        self.assertEqual(lists["deep_cuts"]["decisions"], {"selected": 1})

    def test_same_title_by_another_artist_is_not_repeated(self):
        pools = {"repeated_tracks": [lane("r1", title="Same Title")],
                 "deep_cuts": [lane("d1", title="Same Title"), lane("d2")]}
        lists = build(pools)
        self.assertEqual(picked(lists, "deep_cuts"), ["Album d2"])

    def test_order_decides_who_keeps_a_shared_artist(self):
        pools = {"repeated_tracks": [lane("r1", "Artist s", mbid="mbid-s")],
                 "obsessions": [lane("o1", "Artist s", mbid="mbid-s")]}
        reordered = build(pools, lenses=(OBSESSIONS, REPEATED_TRACKS))
        self.assertEqual(list(reordered), ["obsessions", "repeated_tracks"])
        self.assertEqual(picked(reordered, "obsessions"), ["Album o1"])
        self.assertEqual(picked(reordered, "repeated_tracks"), [])

    def test_default_order_is_scarcest_supply_first(self):
        self.assertEqual(LENS_LIST_ORDER, (REPEATED_TRACKS, DEEP_CUTS, OBSESSIONS))


class KnownArtistTests(unittest.TestCase):
    def statuses(self, album, **kwargs):
        return build({"deep_cuts": [album]}, **kwargs)["deep_cuts"]["decisions"]

    def test_library_artist_name_is_known(self):
        library = {"otheralbum": [{"artist": "artist k"}]}
        self.assertEqual(self.statuses(lane("k", "Artist K"), library=library),
                         {"artist_already_known": 1})

    def test_library_artist_mbid_decides_a_same_name_match(self):
        library = {"otheralbum": [{"artist": "Artist K", "artistId": "lib-1"}]}
        same = lane("k", "Artist K", mbid="mbid-same")
        other = lane("k", "Artist K", mbid="mbid-other")
        self.assertEqual(self.statuses(same, library=library, library_artist_mbids={"lib-1": "mbid-same"}),
                         {"artist_already_known": 1})
        self.assertEqual(self.statuses(other, library=library, library_artist_mbids={"lib-1": "mbid-same"}),
                         {"selected": 1})
        # Without a library MBID the name decides.
        self.assertEqual(self.statuses(other, library=library), {"artist_already_known": 1})

    def test_history_artist_is_known_by_mbid_only(self):
        self.assertEqual(self.statuses(lane("k", "Artist K", mbid="mbid-k"), known_artist_mbids={"mbid-k"}),
                         {"artist_already_known": 1})
        self.assertEqual(self.statuses(lane("k", "Artist K", mbid="mbid-namesake"),
                                       known_artist_mbids={"mbid-k"}), {"selected": 1})

    def test_owned_album_is_excluded(self):
        library = {"albumk": [{"artist": "Artist K"}]}
        self.assertEqual(self.statuses(lane("k", "Artist K"), library=library), {"already_owned": 1})


class FallbackTagTests(unittest.TestCase):
    def test_fallback_tags_rescue_a_candidate_with_one_genre_tag(self):
        album = lane("f")
        tags = {"mbid-f": ["tag one"]}
        without = build({"deep_cuts": [album]}, tags=tags)["deep_cuts"]
        self.assertEqual(without["decisions"], {"too_few_tags": 1})
        rescued = build({"deep_cuts": [album]}, tags=tags,
                        fallback_tags={"mbid-f": ["tag one", "tag fallback"]})["deep_cuts"]
        self.assertEqual(rescued["decisions"], {"selected": 1})
        self.assertEqual(rescued["albums"][0]["tags"], ["tag one", "tag fallback"])

    def test_fallback_for_an_artist_without_genre_tags(self):
        album = lane("f")
        lists = build({"deep_cuts": [album]}, tags={}, fallback_tags={"mbid-f": TWO_TAGS})
        self.assertEqual(picked(lists, "deep_cuts"), ["Album f"])

    def test_merge_keeps_existing_tags_first_without_duplicates(self):
        merged = merge_artist_tags({"a": ["x", None, "y"], "b": []}, {"a": ["y", "z"], "c": ["w"]})
        self.assertEqual(merged, {"a": ["x", "y", "z"], "b": [], "c": ["w"]})
        self.assertEqual(merge_artist_tags({"a": ["x"]}, None), {"a": ["x"]})


class EmptyAndEdgeTests(unittest.TestCase):
    def test_empty_and_missing_pools_give_empty_lists(self):
        lists = build({"deep_cuts": []})
        self.assertEqual(list(lists), [lens.name for lens in LENS_LIST_ORDER])
        for payload in lists.values():
            self.assertEqual((payload["albums"], payload["decisions"], payload["pool_size"],
                              payload["checked"], payload["seed_tags"]), ([], {}, 0, 0, []))

    def test_a_lens_with_no_survivors_reports_its_rejections(self):
        pool = [lane(f"p{i}") for i in range(3)]
        lists = build({"obsessions": pool, "deep_cuts": [lane("d")]},
                      popularity={**listeners(pool, 5_000_000), **listeners([lane("d")])})
        self.assertEqual(lists["obsessions"]["albums"], [])
        self.assertEqual(lists["obsessions"]["decisions"], {"audience_out_of_range": 3})
        self.assertEqual(picked(lists, "deep_cuts"), ["Album d"])

    def test_entries_that_are_not_albums_are_skipped_and_counted(self):
        pool = [lane("ok"), {"album": "", "primary_artist": "Artist x"},
                {"album": "Album y"}, "not a mapping"]
        payload = build({"deep_cuts": pool}, popularity=listeners(pool[:1]),
                        tags=tagged(pool[:1]))["deep_cuts"]
        self.assertEqual((payload["pool_size"], payload["skipped_entries"]), (1, 3))
        self.assertEqual(payload["decisions"], {"selected": 1})

    def test_allocator_fields_already_present_are_kept_when_valid(self):
        album = {**lane("c"), "discovery_category": "adventurous", "discovery_score": float("nan")}
        self.assertEqual(picked(build({"deep_cuts": [album]}), "deep_cuts"), ["Album c"])

    def test_missing_popularity_means_unknown_audience(self):
        payload = build({"deep_cuts": [lane("u")]}, popularity={})["deep_cuts"]
        self.assertEqual(payload["decisions"], {"audience_unknown": 1})


class InvalidArgumentTests(unittest.TestCase):
    def call(self, **overrides):
        kwargs = {"day": DAY, "popularity": {}, "artist_tags": {}, "library_by_title": {}}
        kwargs.update(overrides)
        pools = kwargs.pop("pools", {})
        return build_lens_lists(pools, **kwargs)

    def test_count(self):
        for count in (0, 21, True, 2.0):
            with self.assertRaises(ValueError):
                self.call(count=count)
        self.assertEqual(len(self.call(count=20)), 3)

    def test_day(self):
        for day in ("2026-13-01", "20260115", "2026-1-15", "", 20260115, None):
            with self.assertRaises(ValueError):
                self.call(day=day)

    def test_lenses(self):
        for lenses in ((NOW,), (DEEP_CUTS, DEEP_CUTS), (Lens("deep_cuts", "Copy", "deep_cuts"),)):
            with self.assertRaises(ValueError):
                self.call(lenses=lenses)
        self.assertEqual(self.call(lenses=()), {})

    def test_pools(self):
        with self.assertRaises(ValueError):
            self.call(pools={"genre_spread": []})
        with self.assertRaises(ValueError):
            self.call(pools={"obsessions": []}, lenses=(DEEP_CUTS,))
        with self.assertRaises(ValueError):
            self.call(pools=[("deep_cuts", [])])


def listen(mbid, day_offset, track="t", base=20_000):
    return {"listened_at": (base + day_offset) * SECONDS_PER_DAY,
            "track_metadata": {"track_name": track, "additional_info": {"artist_mbid": mbid}}}


class SeedTests(unittest.TestCase):
    TAGS = {"dense": ["tag dense"], "spread": ["tag spread"], "burst": ["tag burst"]}

    def test_seeds_for_every_lens(self):
        listens = (
            [listen("dense", i % 20) for i in range(30)]
            + [listen("spread", 1_000 + i * 60, track="loop") for i in range(10)]
            + [listen("burst", 400 + i % 10) for i in range(25)]
        )
        seeds = lens_seed_queries(listens, self.TAGS)
        self.assertEqual(list(seeds), [lens.name for lens in LENS_LIST_ORDER])
        tags = {name: [tag_from_query(q) for q, _f, _s in queries] for name, queries in seeds.items()}
        self.assertEqual(tags["deep_cuts"], ["tag dense"])
        self.assertIn("tag burst", tags["obsessions"])
        self.assertIn("tag dense", tags["obsessions"])
        self.assertNotIn("tag spread", tags["obsessions"])
        self.assertTrue(all(style.startswith("profile:")
                            for queries in seeds.values() for _q, _f, style in queries))

    def test_listens_stamped_before_1971_are_dropped(self):
        bad = [{**listen("burst", 0), "listened_at": i} for i in range(30)]
        good = [listen("dense", i % 5) for i in range(3)]
        seeds = lens_seed_queries(bad + good, self.TAGS)
        tags = [tag_from_query(q) for q, _f, _s in seeds["deep_cuts"]]
        self.assertEqual(tags, ["tag dense"])
        self.assertEqual(seeds["obsessions"], [])

    def test_no_history_gives_no_seeds(self):
        self.assertEqual(lens_seed_queries([], self.TAGS),
                         {"repeated_tracks": [], "deep_cuts": [], "obsessions": []})

    def test_history_artist_mbids(self):
        listens = [listen("a", 0), listen("b", 1), {"listened_at": 5, "track_metadata": {}}]
        self.assertEqual(history_artist_mbids(listens), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
