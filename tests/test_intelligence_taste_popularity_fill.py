"""Popularity table, fill job and obscurity lookups (Server V2 Phase 6 slice 17). No network."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from intelligence.api import smart_playlists as api
from intelligence.store import open_store
from intelligence.store import repositories as repo
from intelligence.taste import popularity_persistence as pp
from intelligence.taste.popularity_job import run_popularity_fill

NOW = 1_800_000_000.0


def mbid(n):
    return f"00000000-0000-4000-8000-{n:012d}"


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.text = status, body, "x" if body is not None else ""

    def json(self):
        return self._body


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)

    def add_artist(self, n, nav=None, owned=True):
        repo.upsert_entity(self.db, "artist", f"A{n}", mbid=mbid(n), navidrome_id=nav, owned=owned)
        self.db.commit()


class Persistence(Base):
    def test_save_load_and_skip_malformed(self):
        wrote = pp.save_popularity(self.db, {mbid(1): 500, mbid(2): None, "BAD": 3, mbid(3): -1, mbid(4): True}, NOW)
        self.assertEqual(wrote, 2)
        self.assertEqual(pp.load_popularity(self.db), {mbid(1): 500, mbid(2): None})
        pp.save_popularity(self.db, {mbid(1): 900}, NOW + 1)
        self.assertEqual(pp.load_popularity(self.db)[mbid(1)], 900)

    def test_pending_orders_unseen_then_oldest_and_honours_ttls(self):
        pp.save_popularity(self.db, {mbid(1): 5}, NOW - 40 * 86400)     # found, stale
        pp.save_popularity(self.db, {mbid(2): None}, NOW - 8 * 86400)   # absent, stale
        pp.save_popularity(self.db, {mbid(3): 5}, NOW - 10 * 86400)     # fresh
        got = pp.pending_mbids(self.db, [mbid(1), mbid(2), mbid(3), mbid(9), mbid(9)], NOW)
        self.assertEqual(got, [mbid(9), mbid(1), mbid(2)])

    def test_owned_artists_and_navidrome_map(self):
        self.add_artist(1, "ar-1")
        self.add_artist(2, None)
        self.add_artist(3, "ar-3", owned=False)
        self.assertEqual(pp.owned_artist_mbids(self.db), [mbid(1), mbid(2)])
        self.assertEqual(pp.artist_mbids_by_navidrome_id(self.db), {"ar-1": mbid(1)})


class FillJob(Base):
    def fill(self, post, **kw):
        return run_popularity_fill(self.db, post=post, headers={}, clock=lambda: NOW, **kw)

    def test_fills_in_batches_and_resumes_within_the_request_bound(self):
        for n in range(1, 251):
            self.add_artist(n)
        calls = []

        def post(url, json, headers, timeout):
            calls.append(len(json["artist_mbids"]))
            return Resp(200, [{"artist_mbid": m, "total_listen_count": 7} for m in json["artist_mbids"]])

        first = self.fill(post, max_requests=2)
        self.assertEqual((first.state, calls), ("queued", [100, 100]))
        self.assertEqual(len(pp.load_popularity(self.db)), 200)
        second = self.fill(post, max_requests=2)
        self.assertEqual((second.state, calls[2:]), ("succeeded", [50]))
        self.assertEqual(len(pp.load_popularity(self.db)), 250)

    def test_failure_keeps_earlier_batches_and_last_good(self):
        for n in range(1, 151):
            self.add_artist(n)
        pp.save_popularity(self.db, {mbid(150): 42}, NOW - 40 * 86400)
        seen = []

        def post(url, json, headers, timeout):
            seen.append(1)
            if len(seen) == 2:
                return Resp(500)
            return Resp(200, [{"artist_mbid": m, "total_listen_count": 3} for m in json["artist_mbids"]])

        result = self.fill(post)
        self.assertEqual(result.state, "failed")
        figures = pp.load_popularity(self.db)
        self.assertEqual(figures[mbid(1)], 3)
        self.assertEqual(figures[mbid(150)], 42)   # stale row untouched by the failed batch

    def test_no_owned_artists_makes_no_request(self):
        def post(*a, **k):
            raise AssertionError("no request expected")
        self.assertEqual(self.fill(post).state, "succeeded")


class Lookups(Base):
    def test_band_comes_from_saved_figures_and_store_ids(self):
        self.add_artist(1, "ar-1")
        self.add_artist(2, "ar-2")
        pp.save_popularity(self.db, {mbid(1): 5_000_000, mbid(2): None}, NOW)
        songs = [{"id": "s1", "artist_id": "ar-1"}, {"id": "s2", "artist_id": "ar-2"},
                 {"id": "s3", "artist_id": "zz"}, {"id": "s4"}]
        got = api.build_insights(self.db, songs)
        self.assertEqual(got["obscurity_band"], {"s1": "mainstream"})

    def test_no_saved_figures_leaves_the_lookup_absent(self):
        self.add_artist(1, "ar-1")
        self.assertNotIn("obscurity_band", api.build_insights(self.db, [{"id": "s1", "artist_id": "ar-1"}]))

    def test_songs_from_subsonic_keeps_artist_id(self):
        rows = api.songs_from_subsonic([{"id": "s1", "artistId": "ar-1"}, {"id": "s2"}])
        self.assertEqual(rows, [{"id": "s1", "artist_id": "ar-1"}, {"id": "s2"}])


if __name__ == "__main__":
    unittest.main()
