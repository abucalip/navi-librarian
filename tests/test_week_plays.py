"""Direct-import tests for discovery.week_plays and its use on the recent dashboard shelf."""
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import dashboard
from app.api.dependencies import get_librarian
from discovery import week_plays


def listen(artist, album):
    return {"listened_at": 1, "track_metadata": {"artist_name": artist, "release_name": album}}


class AlbumCountsTest(unittest.TestCase):
    def test_groups_by_normalised_artist_and_album(self):
        counts = week_plays.album_counts([
            listen("Björk", "Homogenic"), listen("bjork", "HOMOGENIC!"), listen("Björk", "Post"),
            listen("Björk", ""), {"track_metadata": None},
        ])
        self.assertEqual(counts[("bjork", "homogenic")], 2)
        self.assertEqual(counts[("bjork", "post")], 1)
        self.assertEqual(sum(counts.values()), 3)


class WeekPlaysCacheTest(unittest.TestCase):
    def test_reads_one_week_window_once_per_cache_period(self):
        now = [10_000_000.0]
        calls = []

        def reader(start, end):
            calls.append((start, end))
            return [listen("A", "B")]

        plays = week_plays.WeekPlays(clock=lambda: now[0])
        self.assertEqual(plays.counts(reader)[("a", "b")], 1)
        plays.counts(reader)
        self.assertEqual(calls, [(10_000_000 - 7 * 86400, 10_000_000)])
        now[0] += week_plays.CACHE_SECONDS + 1
        plays.counts(reader)
        self.assertEqual(len(calls), 2)

    def test_failure_gives_none_then_the_stale_count(self):
        now = [1_000_000.0]
        plays = week_plays.WeekPlays(clock=lambda: now[0])

        def boom(start, end):
            raise RuntimeError("down")

        self.assertIsNone(plays.counts(boom))
        self.assertIsNone(plays.counts(None))
        plays.counts(lambda s, e: [listen("A", "B")])
        now[0] += week_plays.CACHE_SECONDS + 1
        self.assertEqual(plays.counts(boom)[("a", "b")], 1)


class AttachTest(unittest.TestCase):
    ITEMS = [{"name": "Post", "artist": "Björk"}, {"name": "Other", "artist": "X"}]

    def test_adds_count_and_window_with_zero_when_unplayed(self):
        out = week_plays.attach(self.ITEMS, week_plays.album_counts([listen("bjork", "post")]))
        self.assertEqual([(i["play_count"], i["window"]) for i in out], [(1, "week"), (0, "week")])

    def test_unknown_counts_leave_items_untouched(self):
        self.assertEqual(week_plays.attach(self.ITEMS, None), self.ITEMS)


class RecentShelfRouteTest(unittest.TestCase):
    def client(self):
        app = FastAPI()
        app.include_router(dashboard.router)
        app.dependency_overrides[get_librarian] = lambda: type("L", (), {"api_call": staticmethod(lambda *a, **k: {})})()
        return TestClient(app)

    def shelf(self, counts):
        base = [{"id": "1", "name": "Post", "artist": "Björk"}]
        return (patch.object(dashboard, "album_shelf", return_value=base),
                patch.object(dashboard, "_week_reader", return_value=None),
                patch.object(dashboard._WEEK_PLAYS, "counts", return_value=counts))

    def test_recent_shelf_gets_week_counts_other_shelves_do_not(self):
        a, b, c = self.shelf(week_plays.album_counts([listen("Bjork", "Post")]))
        with a, b, c:
            recent = self.client().get("/api/dashboard/albums/recent").json()["items"][0]
            newest = self.client().get("/api/dashboard/albums/newest").json()["items"][0]
        self.assertEqual((recent["play_count"], recent["window"]), (1, "week"))
        self.assertNotIn("play_count", newest)

    def test_unreadable_history_keeps_the_shelf_without_counts(self):
        a, b, c = self.shelf(None)
        with a, b, c:
            item = self.client().get("/api/dashboard/albums/recent").json()["items"][0]
        self.assertNotIn("play_count", item)


if __name__ == "__main__":
    unittest.main()
