import unittest
from types import SimpleNamespace

from discovery_lb_tag_lane import TAG_RADIO_COUNT, run_lb_tag_queries
from discovery_tag_queries import _query_for_tag, tag_from_query

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

    def run_lane(self, queries, radio, recordings, status=200):
        def get(url, params, headers, timeout):
            self.gets.append(params["tag"])
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
            classify_error=lambda e: "err", candidate_cap=60)

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


if __name__ == "__main__":
    unittest.main()
