"""Star Operation S1b: the MusicBrainz tag-search lane records profile tags as seeds."""
import unittest
from types import SimpleNamespace

from discovery.candidate_gathering import _run_tag_queries
from discovery.tag_queries import _query_for_tag


def _group(artist, title, gid):
    return {"id": gid, "title": title, "primary-type": "Album", "secondary-types": [],
            "artist-credit": [{"name": artist, "joinphrase": "", "artist": {"id": "a-" + artist}}]}


class MbTagSeedTests(unittest.TestCase):
    def run_queries(self, queries, answers):
        providers = SimpleNamespace(
            music_key=str.casefold, is_album_candidate=lambda _item: True,
            metadata_cache_get=lambda key, ttl_seconds: answers.get(key),
            metadata_cache_set=lambda *_a: None, sleep=lambda _s: None)
        albums = {}
        state = {"added": 0, "seen": 0, "hits": 0, "misses": 0, "request_index": 0,
                 "unavailable": False, "exhausted_run": 0}
        _run_tag_queries(queries, providers=providers, client=None, headers={}, albums=albums,
                         failures=[], state=state)
        return {c["primary_artist"]: c for c in albums.values()}

    def test_profile_tag_is_seed_and_explore_tag_is_not(self):
        jazz, rai = _query_for_tag("jazz"), _query_for_tag("rai")
        answers = {
            f"mb:release-group-search:{jazz}": {"release-groups": [_group("A", "One", "g1"), _group("B", "Two", "g2")]},
            f"mb:release-group-search:{rai}": {"release-groups": [_group("B", "Two", "g2"), _group("C", "Three", "g3")]},
        }
        by_artist = self.run_queries(
            [(jazz, "jazz", "profile:jazz"), (rai, "rai", "explore:rai")], answers)
        self.assertEqual(by_artist["A"]["seed_tags"], ["jazz"])
        self.assertEqual(by_artist["B"]["seed_tags"], ["jazz"])
        self.assertNotIn("seed_tags", by_artist["C"])


if __name__ == "__main__":
    unittest.main()
