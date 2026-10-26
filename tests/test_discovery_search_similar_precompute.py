"""Daily similar-artist precompute: budget, refresh, and failure rules (contract sections 5.2 and 7)."""

import unittest

from discovery.search.artist_sections import ArtistNetwork
from discovery.search.index import build_owned_data
from discovery.search.merge import OwnedKeys
from discovery.search.similar_precompute import run_precompute


class FakeClock:
    def __init__(self, step=0.0):
        self.now = 0.0
        self.step = step

    def __call__(self):
        current = self.now
        self.now += self.step
        return current


def artists(count):
    return [{"id": f"ar{n}", "name": f"Artist {n}", "mbid": None} for n in range(count)]


def owned():
    return OwnedKeys(build_owned_data(generation=1, built_at=0, artists=[], albums=[], songs=[]))


def network():
    return ArtistNetwork(
        musicbrainz=None, popularity=None, bio=None, cache_read=None, cache_write=None,
    )


class PrecomputeTests(unittest.TestCase):
    def test_every_artist_is_computed_with_refresh_and_counted(self):
        seen = []

        def similar(net, name, artist_id, owned_keys, *, remaining, cancelled, known_mbid, refresh):
            seen.append((name, refresh))
            return {"available": True, "complete": True, "items": []}

        counts = run_precompute(artists(3), network(), owned(), similar=similar)
        self.assertEqual(counts, {"complete": 3, "partial": 0, "unavailable": 0, "failed": 0, "not_reached": 0})
        self.assertTrue(all(refresh for _, refresh in seen))

    def test_partial_and_unavailable_results_are_counted_and_nothing_is_forced(self):
        outcomes = iter([
            {"available": True, "complete": False, "items": []},
            {"available": False, "complete": False, "items": []},
        ])
        counts = run_precompute(artists(2), network(), owned(), similar=lambda *a, **k: next(outcomes))
        self.assertEqual(counts["partial"], 1)
        self.assertEqual(counts["unavailable"], 1)
        self.assertEqual(counts["complete"], 0)

    def test_a_failing_artist_does_not_stop_the_run(self):
        def similar(net, name, *args, **kwargs):
            if name == "Artist 0":
                raise RuntimeError("provider blew up")
            return {"available": True, "complete": True, "items": []}

        counts = run_precompute(artists(3), network(), owned(), similar=similar)
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["complete"], 2)

    def test_the_budget_ends_the_run_and_reports_the_rest_as_not_reached(self):
        clock = FakeClock()
        computed = []

        def similar(net, name, *args, **kwargs):
            computed.append(name)
            clock.now += 10.0  # Each artist takes ten seconds.
            return {"available": True, "complete": True, "items": []}

        counts = run_precompute(
            artists(5), network(), owned(), clock=clock, budget_seconds=25.0, similar=similar,
        )
        self.assertEqual(computed, ["Artist 0", "Artist 1", "Artist 2"])
        self.assertEqual(counts["not_reached"], 2)

    def test_each_artist_gets_its_own_deadline(self):
        clock = FakeClock()
        remaining_seen = []

        def similar(net, name, *args, remaining, **kwargs):
            clock.now += 5.0
            remaining_seen.append(remaining())
            return {"available": True, "complete": True, "items": []}

        run_precompute(artists(2), network(), owned(), clock=clock, artist_seconds=60.0, similar=similar)
        self.assertEqual(remaining_seen, [55.0, 55.0])


if __name__ == "__main__":
    unittest.main()
