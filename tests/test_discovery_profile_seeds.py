import unittest

from discovery.profile_seeds import obsession_seed_queries, repeated_track_seed_queries
from discovery.tag_queries import tag_from_query

DAY = 24 * 60 * 60


def plays(artist_mbid, track, count, start=0):
    return [{"listened_at": 1_000_000 * DAY - (start + i) * DAY,
             "track_metadata": {"track_name": track,
                                "additional_info": {"artist_mbid": artist_mbid}}}
            for i in range(count)]


class RepeatedTrackSeedTests(unittest.TestCase):
    TAGS = {
        "core1": ["metal", "rock"], "core2": ["metal", "prog"], "core3": ["rock"],
        "rai": ["raï", "world"], "jazz": ["jazz fusion"], "untagged": [], "once": ["blues"],
    }

    def listens(self):
        return (
            plays("core1", "c1", 50) + plays("core2", "c2", 40) + plays("core3", "c3", 30)
            + plays("rai", "r1", 12) + plays("jazz", "j1", 7) + plays("untagged", "u1", 20)
            + plays("once", "b1", 2)
        )

    def tags_of(self, queries):
        return [tag_from_query(query) for query, _family, _style in queries]

    def test_seeds_come_from_repeated_tracks_outside_the_dominant_tags(self):
        queries = repeated_track_seed_queries(
            self.listens(), self.TAGS, dominant_top_artists=3, dominant_tag_count=2)
        self.assertEqual(self.tags_of(queries), ["raï", "world", "jazz fusion"])
        self.assertTrue(all(style.startswith("profile:") for _q, _f, style in queries))

    def test_threshold_and_limit(self):
        listens = self.listens()
        kwargs = {"dominant_top_artists": 3, "dominant_tag_count": 2}
        self.assertEqual(self.tags_of(repeated_track_seed_queries(
            listens, self.TAGS, min_track_plays=10, **kwargs)), ["raï", "world"])
        self.assertEqual(self.tags_of(repeated_track_seed_queries(
            listens, self.TAGS, limit=1, **kwargs)), ["raï"])
        self.assertEqual(repeated_track_seed_queries(
            listens, self.TAGS, min_track_plays=100, **kwargs), [])

    def test_no_listens_or_tags_give_no_seeds(self):
        self.assertEqual(repeated_track_seed_queries([], self.TAGS), [])
        self.assertEqual(repeated_track_seed_queries(self.listens(), {}), [])

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            repeated_track_seed_queries(self.listens(), self.TAGS, min_track_plays=0)
        with self.assertRaises(ValueError):
            repeated_track_seed_queries(self.listens(), self.TAGS, dominant_tag_count=0)
        with self.assertRaises(ValueError):
            repeated_track_seed_queries(self.listens(), self.TAGS, limit=-1)


class ObsessionSeedTests(unittest.TestCase):
    TAGS = {"burst": ["blues rock", "rock"], "steady": ["jazz"], "few": ["folk"], "untagged": []}

    def listens(self):
        burst = plays("burst", "b", 25)
        steady = [item for i in range(25) for item in plays("steady", "s", 1, start=i * 40)]
        few = plays("few", "f", 5)
        untagged = plays("untagged", "u", 25)
        return burst + steady + few + untagged

    def tags_of(self, queries):
        return [tag_from_query(query) for query, _family, _style in queries]

    def test_seeds_come_from_artists_with_a_listening_burst(self):
        queries = obsession_seed_queries(self.listens(), self.TAGS)
        self.assertEqual(sorted(self.tags_of(queries)), ["blues rock", "rock"])
        self.assertTrue(all(style.startswith("profile:") for _q, _f, style in queries))

    def test_thresholds_and_limit(self):
        self.assertEqual(len(obsession_seed_queries(self.listens(), self.TAGS, limit=1)), 1)
        self.assertEqual(sorted(self.tags_of(obsession_seed_queries(
            self.listens(), self.TAGS, min_listens=5))), ["blues rock", "folk", "rock"])
        self.assertEqual(obsession_seed_queries(self.listens(), self.TAGS, min_listens=100), [])

    def test_no_listens_or_tags_give_no_seeds(self):
        self.assertEqual(obsession_seed_queries([], self.TAGS), [])
        self.assertEqual(obsession_seed_queries(self.listens(), {}), [])

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            obsession_seed_queries(self.listens(), self.TAGS, min_listens=0)
        with self.assertRaises(ValueError):
            obsession_seed_queries(self.listens(), self.TAGS, min_share=0)
        with self.assertRaises(ValueError):
            obsession_seed_queries(self.listens(), self.TAGS, span_days=0)


if __name__ == "__main__":
    unittest.main()
