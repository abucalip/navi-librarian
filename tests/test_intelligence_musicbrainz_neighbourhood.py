import unittest

from intelligence.musicbrainz import neighbourhood as nb
from intelligence.store.db import open_store
from intelligence.store import repositories as repo


class FakeDump:
    """Tables as lists of rows; counts how many times the 'archive' is read."""

    def __init__(self, tables):
        self.tables = tables
        self.reads = 0

    def __call__(self, wanted):
        self.reads += 1
        for name in wanted:
            if name in self.tables:
                yield name, iter(self.tables[name])


def ents(kind, *pairs):
    return [{"id": str(i), "gid": g} for i, g in pairs]


def link(a, b):
    return {"entity0": str(a), "entity1": str(b)}


def world():
    return FakeDump({
        "artist": ents("artist", (1, "A"), (2, "B"), (3, "C"), (4, "D")),
        "release": ents("release", (10, "R1")),
        "release_group": [], "recording": ents("recording", (20, "REC1"), (21, "REC2")),
        "l_artist_recording": [link(2, 20), link(3, 21), link(4, 21)],
        "l_artist_artist": [link(1, 2)],
        "l_artist_label": [link(2, 90)],
        "l_recording_work": [link(21, 70)],
        "l_artist_work": [link(5, 70)],
        "l_label_release": [link(90, 11)],
    })


class SelectTests(unittest.TestCase):
    def test_one_hop_adds_direct_neighbours_only(self):
        result = nb.select_neighbourhood(world(), {"artist": ["a"], "recording": ["REC1"]}, hops=1)
        self.assertEqual(result.selected["artist"], {1, 2})
        self.assertEqual(result.selected["recording"], {20})
        self.assertNotIn("label", result.selected)
        self.assertEqual(result.passes, 2)

    def test_second_hop_expands_recordings_but_not_artists_or_labels(self):
        # A -> B (hop 1). B is an artist, so B's recording 20 is NOT pulled in by B at hop 2,
        # and B's label 90 (reached at hop 1 only through B) is not reached at all.
        result = nb.select_neighbourhood(world(), {"artist": ["A"], "recording": ["REC2"]}, hops=2)
        self.assertEqual(result.selected["artist"], {1, 2, 3, 4, 5})  # 3, 4 play on seed REC2; 5 wrote work 70
        self.assertEqual(result.selected["work"], {70})
        self.assertNotIn(20, result.selected["recording"])
        self.assertNotIn("label", result.selected)
        self.assertEqual(result.passes, 3)

    def test_second_hop_reaches_composer_through_work(self):
        result = nb.select_neighbourhood(world(), {"recording": ["REC2"]}, hops=2)
        self.assertIn(5, result.selected["artist"])  # REC2 -> work 70 -> artist 5

    def test_each_entity_once_and_passes_are_fixed(self):
        source = world()
        result = nb.select_neighbourhood(source, {"artist": ["A", "B"]}, hops=2)
        self.assertEqual(source.reads, result.passes)
        self.assertEqual(result.selected["artist"], {1, 2})

    def test_missing_seed_is_counted_not_fatal(self):
        result = nb.select_neighbourhood(world(), {"artist": ["A", "GONE"]}, hops=1)
        self.assertEqual((result.seeds_requested, result.seeds_found, result.seeds_missing), (2, 1, 1))

    def test_no_seeds_reads_nothing(self):
        source = world()
        result = nb.select_neighbourhood(source, {}, hops=2)
        self.assertEqual((source.reads, result.count()), (0, 0))

    def test_entity_cap_stops_and_says_so(self):
        result = nb.select_neighbourhood(world(), {"recording": ["REC2"]}, hops=2, max_entities=2)
        self.assertEqual(result.truncated, "entity_cap")
        self.assertLessEqual(result.count(), 2)

    def test_gid_match_ignores_case(self):
        result = nb.select_neighbourhood(world(), {"artist": ["a"]}, hops=1)
        self.assertEqual(result.seeds_found, 1)

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            nb.select_neighbourhood(world(), {}, hops=3)

    def test_summary_is_plain_data(self):
        summary = nb.select_neighbourhood(world(), {"artist": ["A"]}, hops=1).summary()
        self.assertEqual(summary["by_type"]["artist"], 2)
        self.assertIsNone(summary["truncated"])


class OwnedSeedTests(unittest.TestCase):
    def test_only_owned_resolvable_types_with_mbids(self):
        db = open_store(":memory:")
        repo.upsert_entity(db, "artist", "Owned", mbid="AAAA", owned=True)
        repo.upsert_entity(db, "artist", "Not owned", mbid="BBBB", owned=False)
        repo.upsert_entity(db, "release", "No mbid", owned=True)
        repo.upsert_entity(db, "label", "Label", mbid="CCCC", owned=True)
        seeds = nb.owned_seeds(db)
        self.assertEqual(seeds["artist"], {"aaaa"})
        self.assertEqual(seeds["release"], set())
        self.assertNotIn("label", seeds)


if __name__ == "__main__":
    unittest.main()
