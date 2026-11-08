import unittest

from app.services import library_enrich
from intelligence.graph import paths
from intelligence.ingest.navidrome import REL_CREDITED_TO
from intelligence.musicbrainz import auto_fill
from intelligence.musicbrainz.api_fill import ApiError, Paced
from intelligence.store import generations, repositories as repo
from intelligence.store.db import open_store
from tests.test_intelligence_musicbrainz_api_fill import ARTIST, REL, REL2, release_payload

DAY = 86400.0
REC1 = "cccccccc-0000-4000-8000-0000000000aa"


def stub(album_id, mbid=None):
    return {"id": album_id, "artistId": "ar1", "musicBrainzId": mbid}


def album_obj(album_id, mbid, tagged=False):
    song = {"id": f"s-{album_id}", "title": "Song", "artist": "Alpha", "duration": 180, "track": 1,
            "musicBrainzId": REC1 if tagged else None}
    return {"id": album_id, "name": f"Album {album_id}", "artistId": "ar1", "artist": "Alpha",
            "musicBrainzId": mbid, "songCount": 1, "song": [song]}


class Navidrome:
    """Fake server: ``albums`` in oldest-to-newest order; counts the calls each poll makes."""

    def __init__(self):
        self.albums = {"a1": REL}
        self.scan = {"scanning": False, "lastScan": "t1", "count": 10}
        self.calls = []
        self.tagged = set()

    def newest(self, offset, size):
        self.calls.append("newest")
        rows = [stub(i, m) for i, m in reversed(list(self.albums.items()))]
        return rows[offset:offset + size]

    def full(self):
        self.calls.append("full")
        return [stub(i, m) for i, m in self.albums.items()]

    def get_album(self, album_id):
        self.calls.append("getAlbum")
        return album_obj(album_id, self.albums[album_id], album_id in self.tagged) if album_id in self.albums else None

    def add(self, album_id, mbid):
        self.albums[album_id] = mbid
        self.scan = {**self.scan, "lastScan": self.scan["lastScan"] + "x"}


class AutoFillCycleTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        with self.db:
            self.db.execute("INSERT INTO meta (key, value) VALUES ('musicbrainz_slice.loaded_at', '1')")
        self.urls = []
        self.nd = Navidrome()
        self.t = 1000.0
        self.search_hits = []

    def fetch(self, url):
        self.urls.append(url)
        if "/release?" in url:  # identity-ladder search
            return {"releases": self.search_hits}
        if "inc=recordings" in url and "recording-level" not in url:
            return {"media": [{"tracks": [{"length": 180000}]}]}
        if "/artist?" in url:
            return {"artists": [{"id": ARTIST, "life-span": {"begin": "1970"}}]}
        return release_payload(url.split("/release/")[1].split("?")[0])

    def poll(self, **kw):
        nd = self.nd
        return auto_fill.run_cycle(
            self.db, scan_status=lambda: nd.scan, newest=nd.newest, full=nd.full, get_album=nd.get_album,
            get_artist=lambda i: {"name": "Alpha", "musicBrainzId": ARTIST},
            paced=Paced(lambda u: self.fetch(u), interval=0, retry_pause=0, sleep=lambda s: None),
            clock=lambda: self.t, **kw)

    def test_first_poll_is_a_silent_baseline(self):
        out = self.poll()
        self.assertTrue(out["baseline"])
        self.assertEqual((self.urls, out["ingested"]), ([], 0))

    def test_idle_poll_only_reads_scan_status(self):
        self.poll()
        self.nd.calls.clear()
        self.assertEqual(self.poll(), {"idle": True})
        self.assertEqual(self.nd.calls, [])

    def test_scan_in_progress_is_waited_out(self):
        self.poll()
        self.nd.add("a2", REL2)
        self.nd.scan["scanning"] = True
        self.assertTrue(self.poll()["idle"])
        self.nd.scan["scanning"] = False
        self.assertEqual(self.poll()["ingested"], 1)

    def test_new_album_is_ingested_filled_and_published(self):
        self.poll()
        before = generations.data_version(self.db, paths.SLICE_RESOURCE)
        self.nd.add("a2", REL2)
        self.nd.calls.clear()
        out = self.poll()
        self.assertEqual((out["mode"], out["new"], out["ingested"]), ("incremental", 1, 1))
        self.assertEqual(self.nd.calls, ["newest", "getAlbum"])  # no full inventory
        self.assertTrue(any(REL2 in u for u in self.urls))
        self.assertFalse(any(REL in u and REL2 not in u for u in self.urls))
        self.assertEqual(out["filled"]["releases_filled"], 1)
        self.assertGreater(generations.data_version(self.db, paths.SLICE_RESOURCE), before)
        self.assertGreater(out["paths_rebuilt"], 0)
        self.assertEqual(auto_fill._get(self.db, auto_fill.QUEUE_KEY, None), {"releases": [], "artists": []})
        self.assertEqual(self.poll(), {"idle": True})

    def test_album_without_mbid_is_counted_and_not_filled(self):
        self.poll()
        self.nd.add("a2", "")
        out = self.poll()
        self.assertEqual((out["ingested"], out["no_mbid"], out["queued_releases"]), (1, 1, 0))
        self.assertFalse(any("/release/" in u for u in self.urls))

    def test_dump_covered_release_is_not_queued(self):
        self.poll()
        rel = repo.upsert_entity(self.db, "release", "x", mbid=REL2, owned=True)[0]
        other = repo.upsert_entity(self.db, "artist", "dump artist", mbid="9" * 8 + "-0000-4000-8000-000000000009")[0]
        repo.add_edge(self.db, other, rel, "producer", role=None, evidence_class="source_explicit",
                      match_quality="exact_mbid", source="musicbrainz_dump", observation_id=None,
                      source_url=None, valid_from=None, valid_to=None)
        self.nd.add("a2", REL2)
        out = self.poll()
        self.assertEqual((out["queued_releases"], out["covered"]), (0, 1))
        self.assertFalse(any("/release/" in u for u in self.urls))

    def test_failed_fill_stays_queued_and_does_not_publish(self):
        self.poll()
        before = generations.data_version(self.db, paths.SLICE_RESOURCE)

        def down(url):
            raise ApiError(503)
        self.fetch = down
        self.nd.add("a2", REL2)
        self.poll()
        self.assertEqual(generations.data_version(self.db, paths.SLICE_RESOURCE), before)
        self.assertIn(REL2, auto_fill._get(self.db, auto_fill.QUEUE_KEY, {})["releases"])
        self.assertEqual(self.poll(), {"idle": True})  # backed off, not hammered

    def test_missing_getalbum_is_retried_after_the_pause(self):
        self.poll()
        self.nd.add("a2", REL2)
        real = self.nd.albums.pop("a2")
        self.nd.albums["a2"] = real
        broken = self.nd.get_album
        self.nd.get_album = lambda i: None
        self.assertEqual(self.poll()["ingested"], 0)
        self.assertTrue(self.poll()["idle"])               # inside the retry pause
        self.t += auto_fill.RETRY_SECONDS + 1
        self.nd.get_album = broken
        self.assertEqual(self.poll()["ingested"], 1)

    def test_burst_over_the_per_poll_cap_is_fully_ingested_without_the_daily_pass(self):
        self.poll()
        self.nd.calls.clear()
        ids = [f"n{i:02d}" for i in range(60)]
        for album_id in ids:
            self.nd.albums[album_id] = ""
        self.nd.scan = {**self.nd.scan, "lastScan": "burst"}
        total = 0
        for _ in range(5):
            total += self.poll().get("ingested", 0)
            self.t += 6
        self.assertEqual(total, 60)
        seen = auto_fill._get(self.db, auto_fill.SEEN_KEY, {})
        self.assertTrue(all(i in seen for i in ids))
        self.assertEqual(auto_fill._get(self.db, auto_fill.PENDING_KEY, None), [])
        self.assertNotIn("full", self.nd.calls)
        self.assertEqual(self.poll(), {"idle": True})

    def test_failed_getalbum_in_a_burst_does_not_lose_the_rest(self):
        self.poll()
        for i in range(30):
            self.nd.albums[f"n{i:02d}"] = ""
        self.nd.scan = {**self.nd.scan, "lastScan": "burst"}
        real = self.nd.get_album
        self.nd.get_album = lambda i: None if i == "n29" else real(i)   # n29 is the newest
        self.poll()
        self.nd.get_album = real
        self.t += auto_fill.RETRY_SECONDS + 1
        total = self.poll()["ingested"]
        total += self.poll().get("ingested", 0)
        self.assertEqual(total, 30 - 25 + 1)  # the 5 beyond the cap, plus the one that failed
        self.assertEqual(auto_fill._get(self.db, auto_fill.PENDING_KEY, None), [])

    def test_daily_full_pass_removes_deleted_and_picks_up_new_tags(self):
        self.nd.albums = {"a1": REL, "a2": ""}
        self.poll()
        self.nd.albums = {"a1": REL, "a2": REL2}   # a2 got tagged; a3 appeared silently; a1 stays
        self.nd.albums["a3"] = ""
        self.t += DAY * 1.5
        out = self.poll()
        self.assertEqual((out["mode"], out["new"], out["ingested"]), ("full", 2, 2))
        self.nd.albums.pop("a3")
        self.t += DAY * 1.5
        self.assertEqual(self.poll()["removed"], 1)


    def hit(self, album_id, mbid=REL2):
        return {"id": mbid, "title": f"Album {album_id}", "track-count": 1,
                "artist-credit": [{"name": "Alpha", "joinphrase": ""}]}

    def untagged_then_midnight(self, tagged):
        self.poll()
        self.nd.add("a2", "")
        if tagged:
            self.nd.tagged.add("a2")
        self.assertEqual(self.poll()["no_mbid"], 1)
        self.assertFalse(any("/release?" in u for u in self.urls))  # no search on arrival
        self.t += DAY * 1.5
        return self.poll()

    def test_untagged_album_is_searched_after_tagging_and_filled(self):
        self.search_hits = [self.hit("a2")]
        out = self.untagged_then_midnight(tagged=True)
        self.assertEqual((out["searched"], out["resolved_by_search"]), (1, 1))
        self.assertTrue(any("/release/" + REL2 in u for u in self.urls))
        self.assertEqual(out["filled"]["releases_filled"], 1)
        self.assertEqual(auto_fill._get(self.db, auto_fill.UNTAGGED_KEY, None), {})

    def test_album_with_no_tagged_track_is_not_searched(self):
        self.search_hits = [self.hit("a2")]
        out = self.untagged_then_midnight(tagged=False)
        self.assertEqual(out["searched"], 0)
        self.assertFalse(any("/release?" in u for u in self.urls))

    def test_ambiguous_search_is_not_accepted_and_not_retried_for_30_days(self):
        self.search_hits = [self.hit("a2", REL2), self.hit("a2", REL)]
        out = self.untagged_then_midnight(tagged=True)
        self.assertEqual((out["searched"], out["resolved_by_search"]), (1, 0))
        self.urls.clear()
        self.t += DAY * 1.5
        self.assertEqual(self.poll()["searched"], 0)
        self.assertFalse(any("/release?" in u for u in self.urls))

    def test_search_failure_is_retried_next_pass(self):
        real = self.fetch

        def down(url):
            if "/release?" in url:
                raise ApiError(503)
            return real(url)
        self.fetch = down
        out = self.untagged_then_midnight(tagged=True)
        self.assertEqual(out["searched"], 1)
        self.fetch = real
        self.search_hits = [self.hit("a2")]
        self.t += DAY * 1.5
        self.assertEqual(self.poll()["resolved_by_search"], 1)


class WorkerTests(unittest.TestCase):
    def test_worker_runs_the_loop_in_its_own_process_and_stops(self):
        import threading
        import app.worker as worker
        stop = threading.Event()
        stop.set()
        self.assertEqual(worker.main(librarian=object(), stop=stop), 0)

    def test_web_startup_starts_no_knowledge_store_writer(self):
        from pathlib import Path
        source = (Path(__file__).parent.parent / "app" / "main.py").read_text()
        self.assertNotIn("library_enrich", source)
        self.assertNotIn("insights_refresh", source)

    def test_worker_owns_the_insights_refresh_and_the_auto_fill(self):
        from unittest import mock
        import threading
        import app.worker as worker
        stop = threading.Event()
        lib = object()
        with mock.patch.object(worker.insights_refresh, "start") as insights, \
                mock.patch.object(worker.library_enrich, "run_forever") as fill:
            worker.main(librarian=lib, stop=stop)
        insights.assert_called_once_with(lib)
        fill.assert_called_once_with(lib, stop)


class PollTests(unittest.TestCase):
    def test_on_by_default_clamped_and_switchable_off(self):
        self.assertEqual(library_enrich.poll_seconds({}), 5.0)
        self.assertIsNone(library_enrich.poll_seconds({library_enrich.POLL_ENV: "off"}))
        self.assertIsNone(library_enrich.poll_seconds({library_enrich.POLL_ENV: "0"}))
        self.assertEqual(library_enrich.poll_seconds({library_enrich.POLL_ENV: "1"}), library_enrich.MIN_POLL)
        self.assertEqual(library_enrich.poll_seconds({library_enrich.POLL_ENV: "5"}), 5.0)


if __name__ == "__main__":
    unittest.main()
