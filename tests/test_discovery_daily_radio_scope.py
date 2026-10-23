import unittest
from types import SimpleNamespace

from discovery.lb_tag_lane import _radio_cache_key, run_lb_tag_queries
from discovery.tag_queries import _query_for_tag


class Resp:
    def __init__(self, body):
        self.status_code, self._b = 200, body

    def json(self):
        return self._b


class DailyScopeTests(unittest.TestCase):
    """A tag's radio answer is fixed within a lens and day, fresh the next day, and separate per lens."""

    def setUp(self):
        self.cache, self.gets, self.counter = {}, [], 0
        self.state = {"added": 0, "seen": 0, "hits": 0, "misses": 0, "request_index": 0,
                      "unavailable": False, "exhausted_run": 0}

    def fresh_draw_providers(self):
        def get(url, params, headers, timeout):
            self.gets.append(params["tag"])
            self.counter += 1  # every call returns a recording nobody has seen before
            return Resp([{"recording_mbid": f"m{self.counter}", "tag_count": 1}])
        return SimpleNamespace(
            http_get=get, music_key=str.casefold,
            metadata_cache_get=lambda k, ttl_seconds: self.cache.get(k),
            metadata_cache_set=self.cache.__setitem__)

    def run_scope(self, providers, scope):
        albums = {}
        recordings = {}

        def resolve(items):
            for item in items:
                mbid = item["recording_mbid"]
                recordings[mbid] = {"title": "t", "artist-credit": [{"name": "A-" + mbid, "joinphrase": "",
                                    "artist": {"id": "a"}}],
                                    "releases": [{"release-group": {"id": "g" + mbid, "title": "T-" + mbid,
                                                                    "primary-type": "Album", "secondary-types": []}}]}
            return recordings
        run_lb_tag_queries(
            [(_query_for_tag("jazz"), "jazz", "profile:jazz")], providers=providers, headers={},
            albums=albums, failures=[], state=self.state, resolve=resolve,
            rejection=lambda g: None, merge_source=lambda c, s: None,
            classify_error=lambda e: "err", candidate_cap=60, scope=scope)
        return {key[1] for key in albums}

    def test_default_key_is_unchanged(self):
        self.assertEqual(_radio_cache_key("Jazz", 0, 100), "lb:tag-radio:jazz")
        self.assertEqual(_radio_cache_key("Jazz", 50, 75), "lb:tag-radio:jazz:pop50-75")

    def test_scope_is_part_of_the_key(self):
        self.assertEqual(_radio_cache_key("Jazz", 50, 75, "deep_cuts:2026-10-23"),
                         "lb:tag-radio:jazz:pop50-75:deep_cuts:2026-10-23")

    def test_same_lens_and_day_reuse_one_fixed_sample(self):
        providers = self.fresh_draw_providers()
        first = self.run_scope(providers, "deep_cuts:2026-10-23")
        second = self.run_scope(providers, "deep_cuts:2026-10-23")
        self.assertEqual(first, second, "same day gives the same albums")
        self.assertEqual(self.gets, ["jazz"], "second run is served from the day's cache")

    def test_next_day_draws_fresh(self):
        providers = self.fresh_draw_providers()
        monday = self.run_scope(providers, "deep_cuts:2026-10-23")
        tuesday = self.run_scope(providers, "deep_cuts:2026-10-24")
        self.assertEqual(len(self.gets), 2)
        self.assertNotEqual(monday, tuesday)

    def test_two_lenses_sharing_a_tag_get_separate_samples(self):
        providers = self.fresh_draw_providers()
        now_lens = self.run_scope(providers, "now:2026-10-23")
        deep_lens = self.run_scope(providers, "deep_cuts:2026-10-23")
        self.assertEqual(len(self.gets), 2, "the second lens does not reuse the first lens's answer")
        self.assertFalse(now_lens & deep_lens, "the two lists share no albums from this tag")


if __name__ == "__main__":
    unittest.main()
