"""The owned-entity prefetch (efficiency K3 part 1): off by default, capped, resumable, no provider is contacted.

``httpx.get`` and ``httpx.post`` are patched, so no test reaches the network. The page builders are patched
where a test is about the walk, and used for real (with the real network classes) where it is about refusal.
"""
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httpx

from app import worker_schedule
from app.services import owned_prefetch as op
from app.services import prefetch_state as ps
from discovery.search.index import build_owned_data
from intelligence.store import ensure_store, open_store

NOON = datetime(2026, 11, 17, 12).timestamp()
NEXT_DAY = datetime(2026, 11, 18, 12).timestamp()
BUDGETS = {"OWNED_PREFETCH_BUDGETS": "musicbrainz=3,lastfm=100"}


def owned(artists=3, albums=3):
    return build_owned_data(
        generation=1, built_at=0.0, songs=[],
        artists=[{"id": f"ar{n}", "name": f"Artist {n}"} for n in range(artists)],
        albums=[{"id": f"al{n}", "album": f"Album {n}", "artist": f"Artist {n % artists}",
                 "artist_id": f"ar{n % artists}", "created": f"2026-01-0{n + 1}T00:00:00Z"} for n in range(albums)])


class StoreCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "knowledge.sqlite3"
        ensure_store(self.path)

    def read(self, fn, *args):
        db = open_store(self.path)
        try:
            return fn(db, *args)
        finally:
            db.close()


class BudgetTextTests(unittest.TestCase):
    def test_only_named_positive_provider_caps_count(self):
        self.assertEqual(ps.parse_budgets("musicbrainz=300, LastFM=5,qobuz=9,discogs=0,listenbrainz=x,=4,lastfm"),
                         {"musicbrainz": 300, "lastfm": 5})
        self.assertEqual(ps.parse_budgets(None), {})
        self.assertEqual(ps.parse_budgets("musicbrainz=-4"), {})

    def test_the_job_is_never_due_without_caps_and_daily_with_them(self):
        off, on = ps.due({}), ps.due(BUDGETS)
        self.assertFalse(off(NOON, None))
        self.assertTrue(on(NOON, None))
        self.assertFalse(on(NOON, NOON - 3600))
        self.assertTrue(on(NEXT_DAY, NOON))


class RecommendedCapsTests(unittest.TestCase):
    """The full cap string in ``docs/DEPLOYMENT.md`` (owner-approved, efficiency K3) switches every part 2 hook on."""

    RECOMMENDED = "musicbrainz=600,listenbrainz=300,lastfm=600,deezer=600,apple=400,wikipedia=300"

    def test_every_provider_parses(self):
        self.assertEqual(ps.parse_budgets(self.RECOMMENDED), {
            "musicbrainz": 600, "listenbrainz": 300, "lastfm": 600, "deezer": 600, "apple": 400, "wikipedia": 300})

    def test_the_part_2_hooks_and_extras_are_all_given_to_the_walk(self):
        spend = ps.Spend(ps.parse_budgets(self.RECOMMENDED))
        librarian = SimpleNamespace(_metadata_cache_get=lambda key: None, _metadata_cache_set=lambda key, value: None)
        self.assertEqual(set(op.album_page_hooks(librarian, spend)), {"album_year", "deezer_tracks", "album_description"})
        extras = op.entity_extras(librarian, spend)
        self.assertEqual((len(extras["artists"]), len(extras["albums"])), (1, 1))

    def test_each_hook_host_is_counted_under_its_named_cap(self):
        for url, provider in (("https://api.deezer.com/search/album?q=x", "deezer"),
                              ("https://itunes.apple.com/search", "apple"),
                              ("https://music.apple.com/us/album/x/1", "apple"),
                              ("https://en.wikipedia.org/w/rest.php/v1/search/page", "wikipedia"),
                              ("https://musicbrainz.org/ws/2/release-group", "musicbrainz")):
            self.assertEqual(ps.provider_of(url), provider, url)


class SpendTests(unittest.TestCase):
    def test_a_request_past_the_cap_or_to_an_unlisted_provider_is_refused_before_it_is_sent(self):
        spend = ps.Spend({"musicbrainz": 2})
        with mock.patch("httpx.get") as get, mock.patch("httpx.post") as post:
            spend.get("https://musicbrainz.org/ws/2/artist")
            spend.get("https://musicbrainz.org/ws/2/artist")
            for call, url in ((spend.get, "https://musicbrainz.org/ws/2/artist"),
                              (spend.get, "https://api.deezer.com/search"),
                              (spend.get, "https://ws.audioscrobbler.com/2.0/"),   # lastfm: no cap given
                              (spend.post, "https://api.listenbrainz.org/1/popularity/release-group")):
                with self.assertRaises(httpx.TransportError):
                    call(url)
        self.assertEqual(get.call_count, 2)
        post.assert_not_called()
        self.assertEqual(spend.snapshot()["musicbrainz"], 2)
        self.assertTrue(spend.exhausted())
        self.assertEqual(spend.cap_reached, {"musicbrainz"})
        self.assertEqual(spend.not_named, {"deezer", "lastfm", "listenbrainz"})

    def test_spent_counts_are_per_provider_and_start_from_the_stored_day(self):
        spend = ps.Spend({"lastfm": 5, "musicbrainz": 5}, {"lastfm": 4})
        self.assertFalse(spend.exhausted())
        with mock.patch("httpx.get"):
            spend.get("https://ws.audioscrobbler.com/2.0/?method=x")      # Last.fm's API host counts as lastfm
        self.assertEqual(spend.snapshot()["lastfm"], 5)
        self.assertTrue(spend.exhausted())
        self.assertEqual(ps.provider_of("https://api.discogs.com/database/search"), "discogs")
        self.assertEqual(ps.provider_of("https://api.listenbrainz.org/1/x"), "listenbrainz")
        self.assertEqual(ps.provider_of("not a url"), "other")


class StateTests(StoreCase):
    def test_spent_resets_on_a_new_date_and_survives_a_restart_on_the_same_date(self):
        db = open_store(self.path)
        try:
            ps.save_spent(db, "2026-11-17", {"musicbrainz": 7})
            self.assertEqual(ps.load_spent(db, "2026-11-17")["musicbrainz"], 7)
            self.assertEqual(ps.load_spent(db, "2026-11-18"), {})
            ps.save_cursor(db, {"artists": 4, "albums": 2})
            self.assertEqual(ps.load_cursor(db), {"artists": 4, "albums": 2})
        finally:
            db.close()

    def test_malformed_state_reads_as_empty(self):
        db = open_store(self.path)
        try:
            with db:
                for key in (ps.SPENT_KEY, ps.CURSOR_KEY, ps.COVERAGE_KEY):
                    db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (key, "not json"))
            self.assertEqual(ps.load_spent(db, "2026-11-17"), {})
            self.assertEqual(ps.load_cursor(db), {"artists": 0, "albums": 0})
            self.assertIsNone(ps.read_coverage(db))
        finally:
            db.close()


class OrderTests(unittest.TestCase):
    def test_newest_first_then_most_listened(self):
        artists = [{"id": "a", "key": "a", "plays": 1, "added": "2026-01-01"},
                   {"id": "b", "key": "b", "plays": 9, "added": "2020-01-01"},
                   {"id": "c", "key": "c", "plays": 5, "added": "2026-06-01"}]
        with mock.patch.object(op, "NEW_FIRST", 1):
            self.assertEqual([a["id"] for a in op.order_artists(artists)], ["c", "b", "a"])
        albums = [{"id": "x", "key": "x", "artist_id": "a", "added": "2026-01-01"},
                  {"id": "y", "key": "y", "artist_id": "b", "added": "2020-01-01"},
                  {"id": "z", "key": "z", "artist_id": "c", "added": "2026-06-01"}]
        with mock.patch.object(op, "NEW_FIRST", 1):
            self.assertEqual([a["id"] for a in op.order_albums(albums, artists)], ["z", "y", "x"])


class RunTests(StoreCase):
    def run_job(self, environ=BUDGETS, wall=NOON, stop=None, data=None, warm=None, **kwargs):
        built = mock.Mock(return_value=owned() if data is None else data)
        warmed = []

        def fake_warm(kind):
            def run(network, view_or_data, entry):
                warmed.append((kind, entry["id"]))
                return (warm or (lambda *_: True))(kind, entry, network)
            return run

        with mock.patch.object(op, "prefetch_network", side_effect=lambda lib, spend: spend), \
                mock.patch.object(op, "_warm_artist", side_effect=fake_warm("artist")), \
                mock.patch.object(op, "_warm_album", side_effect=fake_warm("album")):
            result = op.run_once(SimpleNamespace(), self.path, stop, environ=environ, wall=lambda: wall,
                                 build_owned=built, **kwargs)
        return result, warmed, built

    def test_with_no_caps_nothing_is_read_or_requested_and_nothing_is_stored(self):
        for environ in ({}, {"OWNED_PREFETCH_BUDGETS": ""}, {"OWNED_PREFETCH_BUDGETS": "qobuz=50"}):
            result, warmed, built = self.run_job(environ)
            self.assertIsNone(result)
            self.assertEqual(warmed, [])
            built.assert_not_called()
        self.assertIsNone(self.read(ps.read_coverage))

    def test_an_unreadable_library_is_not_ready(self):
        built = mock.Mock(return_value=None)
        with mock.patch.object(op, "prefetch_network"):
            result = op.run_once(SimpleNamespace(), self.path, environ=BUDGETS, build_owned=built)
        self.assertIs(result, worker_schedule.NOT_READY)

    def test_one_pass_alternates_artists_and_albums_and_saves_coverage(self):
        result, warmed, _ = self.run_job()
        self.assertEqual([kind for kind, _ in warmed], ["artist", "album"] * 3)
        self.assertEqual(result["stopped"], "pass")
        self.assertEqual(result["counts"], {"complete": 6, "partial": 0, "failed": 0})
        self.assertEqual(self.read(ps.read_coverage)["artists"], {"total": 3, "next": 0, "handled": 3})
        self.assertEqual(self.read(ps.load_cursor), {"artists": 0, "albums": 0})

    def test_the_run_halts_at_a_cap_and_the_cut_short_entity_is_not_passed_over(self):
        def warm(kind, entry, spend):
            with mock.patch("httpx.get"):
                spend.get("https://musicbrainz.org/ws/2/x")     # every entity asks MusicBrainz once; the cap is 3
            return True

        result, warmed, _ = self.run_job(warm=warm)
        self.assertEqual(result["stopped"], "budget")
        self.assertEqual(result["spent"]["musicbrainz"], 3)
        self.assertEqual(len(warmed), 3)                                   # no fourth entity starts at the cap
        self.assertEqual(self.read(ps.load_cursor), {"artists": 2, "albums": 1})
        self.assertEqual(self.read(ps.load_spent, "2026-11-17")["musicbrainz"], 3)

    def test_an_entity_cut_short_by_the_cap_is_not_passed_over(self):
        def warm(kind, entry, spend):
            with mock.patch("httpx.get"):
                spend.get("https://musicbrainz.org/ws/2/x")
                spend.get("https://musicbrainz.org/ws/2/y")     # two per entity: the second entity's second is refused
            return True

        result, warmed, _ = self.run_job(warm=warm)
        self.assertEqual(result["stopped"], "budget")
        self.assertEqual(len(warmed), 2)
        self.assertEqual(result["counts"], {"complete": 1, "partial": 0, "failed": 0})
        self.assertEqual(self.read(ps.load_cursor), {"artists": 1, "albums": 0})   # the album is tried again tomorrow

    def test_a_restart_the_same_day_keeps_the_spent_count_and_a_new_day_resets_it(self):
        def warm(kind, entry, spend):
            with mock.patch("httpx.get"):
                spend.get("https://musicbrainz.org/ws/2/x")
            return True

        self.run_job(warm=warm)
        again, warmed, built = self.run_job(warm=warm)                 # same day: no budget left
        self.assertEqual(again["stopped"], "budget")
        self.assertEqual(warmed, [])
        built.assert_not_called()
        next_day, warmed, _ = self.run_job(warm=warm, wall=NEXT_DAY)
        self.assertEqual(next_day["spent"]["musicbrainz"], 3)
        self.assertEqual(len(warmed), 3)

    def test_the_walk_resumes_from_the_checkpoint(self):
        stop = threading.Event()
        count = []

        def warm(kind, entry, spend):
            count.append(entry["id"])
            if len(count) == 3:
                stop.set()
            return True

        first, _, _ = self.run_job(stop=stop, warm=warm)
        self.assertEqual(first["stopped"], "shutdown")
        saved = self.read(ps.load_cursor)
        self.assertEqual(saved, {"artists": 1, "albums": 1})               # the third (cut short) was not passed over
        _, resumed, _ = self.run_job()
        walk = [e["id"] for e in op.order_artists(owned().artists)]
        artists = [e for k, e in resumed if k == "artist"]
        self.assertEqual(artists, walk[1:] + walk[:1])                     # starts where the first run stopped
        self.assertEqual(self.read(ps.load_cursor), saved)                 # one full pass wraps around

    def test_a_failed_entity_is_counted_and_passed_over(self):
        def warm(kind, entry, spend):
            if entry["id"] == "ar1":
                raise RuntimeError("provider detail that must not be logged")
            return entry["id"] != "al2"

        result, _, _ = self.run_job(warm=warm)
        self.assertEqual(result["counts"], {"complete": 4, "partial": 1, "failed": 1})
        self.assertEqual(result["stopped"], "pass")


    # A provider the owner did not name must never freeze the walk on one entity.
    def test_a_refused_unnamed_provider_fails_that_source_and_the_walk_moves_on(self):
        def warm(kind, entry, spend):
            with mock.patch("httpx.get"):
                spend.get("https://musicbrainz.org/ws/2/x")
                try:
                    spend.get("https://api.listenbrainz.org/1/x")      # always used, but no cap was given
                except httpx.TransportError:
                    return False
            return True

        result, warmed, _ = self.run_job({"OWNED_PREFETCH_BUDGETS": "musicbrainz=100"}, warm=warm)
        self.assertEqual(result["stopped"], "pass")
        self.assertEqual(len(warmed), 6)
        self.assertEqual(result["counts"], {"complete": 0, "partial": 6, "failed": 0})
        self.assertEqual(self.read(ps.load_cursor), {"artists": 0, "albums": 0})   # moved past every entity and wrapped

    def test_sources_without_a_cap_are_switched_off_in_the_network(self):
        librarian = SimpleNamespace(
            _discovery_read_list=lambda name: None, _discovery_write_list=mock.Mock(),
            _discovery_settings_read=lambda: {"lastfm_api_key": "k", "discogs_token": "t"},
            api_call=mock.Mock(), _metadata_cache_get=lambda key, ttl: None, _metadata_cache_set=mock.Mock())
        with mock.patch.object(op.similar_precompute, "network_kwargs", side_effect=lambda lib: {
                "cache_read": lambda name: None, "cache_write": mock.Mock(), "navidrome_mbid": None,
                "lastfm_api_key": "k", "lastfm_gen": 1, "discogs_token": "t", "discogs_gen": 1}):
            bare = op.prefetch_network(librarian, ps.Spend({"musicbrainz": 5, "listenbrainz": 5}))
            full = op.prefetch_network(librarian, ps.Spend({"musicbrainz": 5, "lastfm": 5, "discogs": 5}))
        self.assertIsNone(bare.lastfm)
        self.assertIsNone(bare.discogs)
        self.assertIsNotNone(full.lastfm)
        self.assertIsNotNone(full.discogs)


class RealPagesTests(StoreCase):
    """The real page builders and network classes, with every outbound call refused or failed."""

    def test_a_zero_cap_provider_is_never_contacted_through_the_real_artist_page(self):
        librarian = SimpleNamespace(
            _discovery_read_list=lambda name: None, _discovery_write_list=mock.Mock(),
            _discovery_settings_read=lambda: {}, api_call=mock.Mock(return_value={"artist": {}}),
            _metadata_cache_get=lambda key, ttl: None, _metadata_cache_set=mock.Mock())
        data = owned(artists=1, albums=1)
        spend = ps.Spend({"lastfm": 5})                                   # MusicBrainz and ListenBrainz are not capped
        with mock.patch("httpx.get") as get, mock.patch("httpx.post") as post:
            network = op.prefetch_network(librarian, spend)
            from discovery.search.index import STATE_FRESH, IndexView
            page = op.artist_page(IndexView(STATE_FRESH, data, None), data.artists[0]["key"], data.artists[0]["id"],
                                  network=network)
            list(op.album_sections(network, data, album=data.albums[0], artist="Artist 0",
                                   artist_key=data.albums[0]["artist_key"], name="Album 0", year=None,
                                   release_group_mbid=None))
        get.assert_not_called()
        post.assert_not_called()
        self.assertEqual(page.status, "ok")
        librarian._discovery_write_list.assert_not_called()               # a refused request stores nothing
        self.assertEqual(spend.snapshot()["musicbrainz"], 0)


if __name__ == "__main__":
    unittest.main()
