"""Efficiency P5: the cached album inventory keyed by the Navidrome scan marker."""
import unittest
import unittest.mock
from collections import Counter

from discovery.library_snapshot import AlbumInventoryLimitError, AlbumInventorySnapshot


def items(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class FakeNavidrome:
    def __init__(self):
        self.calls = Counter()
        self.status = {"scanning": False, "lastScan": "2026-11-17T00:00:00Z", "count": 10}
        self.albums = [{"id": "a1", "name": "One", "playCount": 1}, {"id": "a2", "name": "Two"}]
        self.fail_paging = False
        self.fail_status = False

    def api_call(self, method, **params):
        self.calls[method] += 1
        if method == "getScanStatus":
            if self.fail_status:
                raise RuntimeError("Navidrome API error")
            return {"scanStatus": dict(self.status)}
        if method == "getAlbumList2":
            if self.fail_paging:
                raise RuntimeError("Navidrome API error")
            offset, size = params["offset"], params["size"]
            return {"albumList2": {"album": [dict(a) for a in self.albums[offset:offset + size]]}}
        raise AssertionError(method)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class AlbumInventorySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.nd = FakeNavidrome()
        self.clock = Clock()
        self.snap = AlbumInventorySnapshot(now=self.clock)

    def get(self):
        return self.snap.get(self.nd.api_call, items)

    def test_second_read_inside_the_recheck_window_makes_no_call(self):
        first = self.get()
        self.assertEqual([a["id"] for a in first], ["a1", "a2"])
        self.assertEqual(self.nd.calls, Counter({"getScanStatus": 1, "getAlbumList2": 1}))
        self.clock.t += 29
        self.assertEqual(self.get(), first)
        self.assertEqual(self.nd.calls, Counter({"getScanStatus": 1, "getAlbumList2": 1}))

    def test_after_the_recheck_window_one_status_call_and_no_paging(self):
        self.get()
        self.clock.t += 31
        self.get()
        self.assertEqual(self.nd.calls, Counter({"getScanStatus": 2, "getAlbumList2": 1}))
        self.clock.t += 10   # the check time moved on, so this one is free again
        self.get()
        self.assertEqual(self.nd.calls, Counter({"getScanStatus": 2, "getAlbumList2": 1}))

    def test_a_changed_marker_pages_again(self):
        self.get()
        self.nd.status["count"] = 11
        self.nd.albums.append({"id": "a3", "name": "Three"})
        self.clock.t += 31
        self.assertEqual([a["id"] for a in self.get()], ["a1", "a2", "a3"])
        self.assertEqual(self.nd.calls["getAlbumList2"], 2)

    def test_play_data_older_than_the_maximum_age_is_paged_again(self):
        self.get()
        self.nd.albums[0]["playCount"] = 7   # a play, no scan: the marker stays the same
        self.clock.t += 5 * 60
        self.assertEqual(self.get()[0]["playCount"], 7)
        self.assertEqual(self.nd.calls["getAlbumList2"], 2)

    def test_nothing_is_cached_while_a_scan_runs(self):
        self.nd.status["scanning"] = True
        self.get()
        self.get()
        self.assertEqual(self.nd.calls["getAlbumList2"], 2)

    def test_nothing_is_cached_when_the_marker_cannot_be_read(self):
        self.nd.fail_status = True
        self.get()
        self.get()
        self.assertEqual(self.nd.calls["getAlbumList2"], 2)

    def test_a_failure_is_not_cached_and_drops_the_old_copy(self):
        self.get()
        self.nd.status["count"] = 11
        self.nd.fail_paging = True
        self.clock.t += 31
        with self.assertRaises(RuntimeError):
            self.get()
        self.nd.fail_paging = False
        self.get()
        self.assertEqual(self.nd.calls["getAlbumList2"], 3)

    def test_the_safety_limit_is_raised_not_cached(self):
        snap = AlbumInventorySnapshot(now=self.clock)
        self.nd.albums = [{"id": f"a{i}"} for i in range(3)]
        with unittest.mock.patch("discovery.library_snapshot.fetch_album_inventory",
                                 side_effect=AlbumInventoryLimitError(3)):
            with self.assertRaises(AlbumInventoryLimitError):
                snap.get(self.nd.api_call, items)
        self.assertEqual(len(snap.get(self.nd.api_call, items)), 3)

    def test_callers_cannot_change_the_cached_copy(self):
        self.get()[0]["name"] = "changed"
        self.assertEqual(self.get()[0]["name"], "One")

    def test_clear_drops_the_copy(self):
        self.get()
        self.snap.clear()
        self.get()
        self.assertEqual(self.nd.calls["getAlbumList2"], 2)


if __name__ == "__main__":
    unittest.main()
