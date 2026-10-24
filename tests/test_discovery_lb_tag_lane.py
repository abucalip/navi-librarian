import threading
import unittest
from unittest import mock
from types import SimpleNamespace

from discovery.lb_tag_lane import TAG_RADIO_COUNT, run_lb_tag_queries
from discovery.tag_queries import _query_for_tag, tag_from_query

R1, R2, R3 = "r1", "r2", "r3"


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._b = status, body

    def json(self):
        return self._b


def recording(artist, title, gid):
    return {"title": "t", "artist-credit": [{"name": artist, "joinphrase": "", "artist": {"id": "a-" + artist}}],
            "releases": [{"release-group": {"id": gid, "title": title, "primary-type": "Album", "secondary-types": []}}]}


class LaneTests(unittest.TestCase):
    def setUp(self):
        self.cache, self.gets = {}, []
        self.state = {"added": 0, "seen": 0, "hits": 0, "misses": 0, "request_index": 0,
                      "unavailable": False, "exhausted_run": 0}
        self.failures, self.albums = [], {}
        self.params = []

    def run_lane(self, queries, radio, recordings, status=200, **band):
        def get(url, params, headers, timeout):
            self.gets.append(params["tag"])
            self.params.append(params)
            return Resp(status, radio.get(params["tag"], []))
        providers = SimpleNamespace(
            http_get=get, music_key=str.casefold,
            metadata_cache_get=lambda k, ttl_seconds: self.cache.get(k),
            metadata_cache_set=self.cache.__setitem__)
        return run_lb_tag_queries(
            queries, providers=providers, headers={}, albums=self.albums, failures=self.failures,
            state=self.state, resolve=lambda items: {i["recording_mbid"]: recordings[i["recording_mbid"]]
                                                     for i in items if i["recording_mbid"] in recordings},
            rejection=lambda g: None if g.get("primary-type") == "Album" else "no",
            merge_source=lambda c, s: c.setdefault("discovery_sources", []).append(s),
            classify_error=lambda e: "err", candidate_cap=60, **band)

    def test_tag_round_trip(self):
        for tag in ["jazz", "ethio-jazz", 'Hip Hop "x"', "a\\b"]:
            self.assertEqual(tag_from_query(_query_for_tag(tag)), tag)

    def test_adds_candidates_merges_and_caches(self):
        queries = [(_query_for_tag("jazz"), "jazz", "profile:jazz"), (_query_for_tag("rai"), "rai", "explore:rai")]
        radio = {"jazz": [{"recording_mbid": R1}, {"recording_mbid": R2}], "rai": [{"recording_mbid": R2}, {"recording_mbid": R3}]}
        recs = {R1: recording("A", "One", "g1"), R2: recording("B", "Two", "g2"), R3: recording("C", "Three", "g3")}
        out = self.run_lane(queries, radio, recs)
        self.assertEqual(out, [(2, None), (1, None)])
        self.assertEqual(len(self.albums), 3)
        two = self.albums[("b", "two")]
        self.assertEqual(two["discovery_sources"], ["profile_tag_search", "exploration_tag_search"])
        self.assertEqual(two["release_group_mbid"], "g2")
        self.assertEqual(two["discovery_source"], "listenbrainz_tag_radio")
        self.run_lane(queries, radio, recs)
        self.assertEqual(self.gets, ["jazz", "rai"], "second run is served from cache")

    def test_per_query_caps_the_albums_kept_per_query(self):
        queries = [(_query_for_tag("jazz"), "jazz", "profile:jazz")]
        ids = [f"r{i}" for i in range(8)]
        radio = {"jazz": [{"recording_mbid": i} for i in ids]}
        recs = {i: recording(f"Artist{n}", f"Album{n}", f"g{n}") for n, i in enumerate(ids)}
        self.assertEqual(self.run_lane(queries, radio, recs), [(5, None)], "default keeps 5")
        self.albums.clear(); self.cache.clear(); self.state["added"] = 0
        self.assertEqual(self.run_lane(queries, radio, recs, per_query=8), [(8, None)])
        self.albums.clear(); self.cache.clear(); self.state["added"] = 0
        self.assertEqual(self.run_lane(queries, radio, recs, per_query=2), [(2, None)])

    def test_per_query_must_be_a_positive_integer(self):
        for bad in (0, -1, 2.5, True, None):
            with self.assertRaises(ValueError):
                self.run_lane([(_query_for_tag("jazz"), "jazz", "profile:jazz")], {}, {}, per_query=bad)

    def test_radio_tag_count_reaches_candidates_and_survives_the_cache(self):
        queries = [(_query_for_tag("jazz"), "jazz", "profile:jazz"), (_query_for_tag("rai"), "rai", "explore:rai")]
        radio = {"jazz": [{"recording_mbid": R1, "tag_count": 7}, {"recording_mbid": R2, "tag_count": 3}],
                 "rai": [{"recording_mbid": R2, "tag_count": 9}, {"recording_mbid": R3}]}
        recs = {R1: recording("A", "One", "g1"), R2: recording("B", "Two", "g2"), R3: recording("C", "Three", "g3")}
        self.run_lane(queries, radio, recs)
        strengths = {key[1]: album["tag_strength"] for key, album in self.albums.items()}
        self.assertEqual(strengths, {"one": 7.0, "two": 9.0, "three": 0.0})
        self.albums.clear()
        self.run_lane(queries, radio, recs)
        self.assertEqual(self.gets, ["jazz", "rai"], "second run is served from cache")
        self.assertEqual(self.albums[("a", "one")]["tag_strength"], 7.0)

    def test_old_cache_entries_of_plain_mbids_still_work(self):
        self.cache["lb:tag-radio:jazz"] = [R1]
        self.run_lane([(_query_for_tag("jazz"), "jazz", "profile:jazz")], {}, {R1: recording("A", "One", "g1")})
        self.assertEqual(self.albums[("a", "one")]["tag_strength"], 0.0)

    def test_http_failure_marks_unavailable_and_records_failure(self):
        out = self.run_lane([(_query_for_tag("jazz"), "jazz", "profile:jazz")], {}, {}, status=502)
        self.assertEqual(out, [(0, "err")])
        self.assertTrue(self.state["unavailable"])
        self.assertEqual(self.failures[0]["source"], "listenbrainz_tag_radio")

    def test_per_query_cap_and_non_album_rejected(self):
        ids = [f"r{i}" for i in range(10)]
        recs = {i: recording(f"X{i}", f"T{i}", f"g{i}") for i in ids}
        recs["r0"]["releases"][0]["release-group"]["primary-type"] = "Single"
        out = self.run_lane([(_query_for_tag("jazz"), "jazz", "profile:jazz")],
                            {"jazz": [{"recording_mbid": i} for i in ids]}, recs)
        self.assertEqual(out, [(5, None)])
        self.assertNotIn(("x0", "t0"), self.albums)
        self.assertGreater(TAG_RADIO_COUNT, 0)

    def test_slow_tag_is_dropped_after_first_answer_and_not_cached(self):
        release = threading.Event()

        def get(url, params, headers, timeout):
            if params["tag"] == "slow":
                release.wait(5)
                return Resp(200, [{"recording_mbid": R3}])
            return Resp(200, [{"recording_mbid": R1}])
        providers = SimpleNamespace(
            http_get=get, music_key=str.casefold,
            metadata_cache_get=lambda k, ttl_seconds: self.cache.get(k),
            metadata_cache_set=self.cache.__setitem__)
        queries = [(_query_for_tag("slow"), "f", "profile:slow"), (_query_for_tag("fast"), "f", "explore:fast")]
        with mock.patch("discovery.lb_tag_lane.TAG_RADIO_STRAGGLER_SECONDS", 0.05):
            out = run_lb_tag_queries(
                queries, providers=providers, headers={}, albums=self.albums, failures=self.failures,
                state=self.state, resolve=lambda items: {"r1": recording("A", "One", "g1")},
                rejection=lambda g: None, merge_source=lambda c, s: None,
                classify_error=lambda e: type(e).__name__, candidate_cap=60)
        self.assertEqual(out, [(0, "TimeoutError"), (1, None)])
        self.assertNotIn("lb:tag-radio:slow", self.cache)
        release.set()
        for _ in range(100):
            if "lb:tag-radio:slow" in self.cache:
                break
            threading.Event().wait(0.02)
        self.assertEqual(self.cache["lb:tag-radio:slow"], [[R3, 0]], "late answer still warms the cache")
        self.assertFalse(self.state["unavailable"])

    def test_default_band_sends_full_range_and_keeps_original_cache_key(self):
        self.run_lane([(_query_for_tag("rock"), "rock", "profile:rock")], {"rock": [[R1, 3]]}, {R1: recording("A", "B", R1)})
        self.assertEqual((self.params[0]["pop_begin"], self.params[0]["pop_end"]), (0, 100))
        self.assertIn("lb:tag-radio:rock", self.cache)

    def test_deep_cuts_band_is_sent_and_cached_separately(self):
        queries = [(_query_for_tag("rock"), "rock", "profile:rock")]
        radio, recordings = {"rock": [[R1, 3]]}, {R1: recording("A", "B", R1)}
        self.run_lane(queries, radio, recordings, pop_begin=50, pop_end=75)
        self.assertEqual((self.params[0]["pop_begin"], self.params[0]["pop_end"]), (50, 75))
        self.assertIn("lb:tag-radio:rock:pop50-75", self.cache)
        self.assertNotIn("lb:tag-radio:rock", self.cache)
        # A later default-band run must not reuse the 50-75 answer.
        self.run_lane(queries, radio, recordings)
        self.assertEqual(self.gets, ["rock", "rock"])
        self.assertEqual((self.params[1]["pop_begin"], self.params[1]["pop_end"]), (0, 100))

    def test_invalid_band_is_rejected(self):
        for begin, end in [(75, 50), (50, 50), (-1, 10), (0, 101)]:
            with self.assertRaises(ValueError):
                self.run_lane([(_query_for_tag("rock"), "rock", "profile:rock")], {}, {}, pop_begin=begin, pop_end=end)


if __name__ == "__main__":
    unittest.main()
