"""Efficiency K2: artist and album page sections built from a stale discovery cache row state ``fetched_at``.

A section served from rows past their TTL (``read_or_revalidate``) carries the oldest such row's store
time; a fresh or fetched section, an unavailable one, and the stored rows never carry it.
"""

import time
import unittest

from app.services.layered_cache import iso_utc
from discovery.search import cache
from discovery.search.cache import (
    FETCHED_AT,
    fetched_at_text,
    provider_cache_key,
    read_or_revalidate,
    run_noting_stale,
    with_fetched_at,
)
from discovery.search.artist_sections import network_sections
from tests.test_discovery_search_album_page import FakeLastFm, make_network, run, track
from tests.test_discovery_search_artist_sections import (
    ALBUMS,
    RADIOHEAD,
    FakeMusicBrainz,
    Store,
    network,
    radiohead_owned,
)

DAY = 24 * 60 * 60
IDENTITY_KEY = provider_cache_key("musicbrainz", 0, "radiohead", "artist")
ALBUMS_KEY = provider_cache_key("musicbrainz", 0, "artist-mbid:mb-rh", "studio-albums")
TRACKS_KEY = provider_cache_key("tracks", 0, "radiohead/kid a", "tracks")


def accept(key, refresh):
    return True


def put(store, key, records, at):
    store.data[key] = {"at": at, "results": records}


class NotingTests(unittest.TestCase):
    def test_oldest_stale_row_is_noted(self):
        store, now = Store(), time.time()
        put(store, "a", [{"name": "a"}], now - 3 * DAY)
        put(store, "b", [{"name": "b"}], now - 5 * DAY)
        put(store, "fresh", [{"name": "c"}], now - 60)

        def job():
            for key in ("a", "b", "fresh"):
                read_or_revalidate(store.read, key, submit=accept, refetch=None)
            return "done"

        self.assertEqual(run_noting_stale(job), ("done", now - 5 * DAY))

    def test_fresh_rows_note_nothing(self):
        store = Store()
        put(store, "fresh", [{"name": "c"}], time.time() - 60)
        _, oldest = run_noting_stale(lambda: read_or_revalidate(store.read, "fresh", submit=accept, refetch=None))
        self.assertIsNone(oldest)

    def test_unnoted_read_and_reads_outside_a_job_are_ignored(self):
        store = Store()
        put(store, "a", [{"name": "a"}], time.time() - 3 * DAY)
        _, oldest = run_noting_stale(
            lambda: read_or_revalidate(store.read, "a", submit=accept, refetch=None, note_stale=False))
        self.assertIsNone(oldest)
        self.assertEqual(read_or_revalidate(store.read, "a", submit=accept, refetch=None), [{"name": "a"}])

    def test_marks_do_not_leak_into_the_next_job_on_the_same_thread(self):
        store = Store()
        put(store, "a", [{"name": "a"}], time.time() - 3 * DAY)
        run_noting_stale(lambda: read_or_revalidate(store.read, "a", submit=accept, refetch=None))
        self.assertIsNone(run_noting_stale(lambda: None)[1])
        self.assertIsNone(cache._stale_marks.get())

    def test_marks_reset_when_the_job_raises(self):
        def job():
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            run_noting_stale(job)
        self.assertIsNone(cache._stale_marks.get())


class StampTests(unittest.TestCase):
    def test_format_matches_the_metadata_routes(self):
        self.assertEqual(fetched_at_text(1761408000), "2025-10-25T16:00:00Z")
        self.assertEqual(fetched_at_text(1761408000.7), iso_utc(1761408000.7))

    def test_available_section_gets_a_copy(self):
        section = {"section": "similar", "available": True, "complete": True, "reason": None, "items": []}
        stamped = with_fetched_at(section, 1761408000)
        self.assertEqual(stamped[FETCHED_AT], "2025-10-25T16:00:00Z")
        self.assertNotIn(FETCHED_AT, section)

    def test_unavailable_or_fresh_section_is_unchanged(self):
        failed = {"section": "similar", "available": False, "complete": False, "reason": "deadline", "items": []}
        self.assertIs(with_fetched_at(failed, 1761408000), failed)
        fresh = {"section": "similar", "available": True, "complete": True, "reason": None, "items": []}
        self.assertIs(with_fetched_at(fresh, None), fresh)


def artist_net(store):
    net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), store=store)
    net.refresh_submit = accept
    return net


class ArtistPageTests(unittest.TestCase):
    def test_catalog_sections_state_the_stale_row_time(self):
        store, now = Store(), time.time()
        at = now - 3 * DAY
        put(store, IDENTITY_KEY, RADIOHEAD, now - 60)
        put(store, ALBUMS_KEY, ALBUMS, at)
        sections = network_sections(artist_net(store), "Radiohead", None, radiohead_owned())
        expected = fetched_at_text(at)
        self.assertEqual(sections["albums"][FETCHED_AT], expected)
        self.assertEqual(sections["missing_albums"][FETCHED_AT], expected)
        self.assertNotIn(FETCHED_AT, sections["bio"])
        self.assertNotIn(FETCHED_AT, store.data[ALBUMS_KEY])

    def test_fresh_rows_state_nothing(self):
        store, now = Store(), time.time()
        put(store, IDENTITY_KEY, RADIOHEAD, now - 60)
        put(store, ALBUMS_KEY, ALBUMS, now - 60)
        sections = network_sections(artist_net(store), "Radiohead", None, radiohead_owned())
        self.assertFalse([name for name, section in sections.items() if FETCHED_AT in section])

    def test_a_stale_identity_row_alone_stamps_no_section(self):
        store, now = Store(), time.time()
        put(store, IDENTITY_KEY, RADIOHEAD, now - 3 * DAY)
        put(store, ALBUMS_KEY, ALBUMS, now - 60)
        for _ in range(3):  # whichever job looks the MBID up first, the answer is the same
            sections = network_sections(artist_net(store), "Radiohead", None, radiohead_owned())
            self.assertFalse([name for name, section in sections.items() if FETCHED_AT in section])

    def test_without_a_refresher_an_expired_row_is_fetched_and_not_stamped(self):
        store, now = Store(), time.time()
        put(store, IDENTITY_KEY, RADIOHEAD, now - 60)
        put(store, ALBUMS_KEY, ALBUMS, now - 3 * DAY)
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), store=store)
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertNotIn(FETCHED_AT, sections["albums"])


class AlbumPageTests(unittest.TestCase):
    def test_stale_tracklist_section_states_its_time(self):
        net = make_network(lastfm=FakeLastFm(tracks=[track(1, "New")]), refresh_submit=accept)
        at = time.time() - 8 * DAY
        put(net.store, TRACKS_KEY, [track(1, "Old")], at)
        sections = run(net)
        self.assertEqual([t["title"] for t in sections["tracks"]["items"]], ["Old"])
        self.assertEqual(sections["tracks"][FETCHED_AT], fetched_at_text(at))
        for name in ("album", "year", "description"):
            self.assertNotIn(FETCHED_AT, sections[name])
        self.assertNotIn(FETCHED_AT, net.store.data[TRACKS_KEY])

    def test_fresh_tracklist_states_nothing(self):
        net = make_network(lastfm=FakeLastFm(tracks=[track(1, "New")]), refresh_submit=accept)
        put(net.store, TRACKS_KEY, [track(1, "Old")], time.time() - 60)
        self.assertNotIn(FETCHED_AT, run(net)["tracks"])


if __name__ == "__main__":
    unittest.main()
