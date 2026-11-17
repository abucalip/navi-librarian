"""Efficiency K2 part 2: stale-while-revalidate for the artist and album pages' provider rows.

The rows live in the discovery search cache (``{"at", "results"}``) and are read through
``discovery.search.cache``. These tests use a synchronous fake refresher so each refresh runs
exactly when the test says.
"""

import threading
import time
import unittest

from app.services.stale_refresh import DISCOVERY_REFRESHER, REFRESHER, BackgroundRefresher
from discovery.search import cache
from discovery.search.album_page import race_tracks
from discovery.search.artist_sections import ArtistNetwork, TAG_TTL_SECONDS, _tags_for, resolve_identity
from discovery.search.cache import (
    NEGATIVE_TTL_SECONDS,
    POSITIVE_TTL_SECONDS,
    REFRESH_KEY_PREFIX,
    SIMILAR_TTL_SECONDS,
    STALE_FACTOR,
    provider_cache_key,
    read_cached_state,
    read_or_revalidate,
)
from discovery.search.providers import ProviderError
from discovery.search.top_songs import top_songs

DAY = 24 * 60 * 60
LB_KEY = provider_cache_key("listenbrainz", 0, "artist-top:mb-rh", "top-recordings")


class Store:
    def __init__(self):
        self.data = {}
        self.writes = 0

    def read(self, key):
        return self.data.get(key)

    def write(self, key, payload):
        self.writes += 1
        self.data[key] = payload


class Refresher:
    """Records submitted refreshes; ``run()`` runs them in order. One per key, like the real pool."""

    def __init__(self):
        self.pending = {}
        self.keys = []

    def submit(self, key, refresh):
        self.keys.append(key)
        if key in self.pending:
            return False
        self.pending[key] = refresh
        return True

    def run(self):
        pending, self.pending = self.pending, {}
        for refresh in pending.values():
            try:
                refresh()
            except Exception:
                pass  # the real pool swallows a failed refresh


def song(name, count):
    return {"name": name, "listen_count": count, "recording_mbid": None, "album": None}


class FakeListenBrainz:
    def __init__(self, records=(), fail=False):
        self.records, self.fail, self.calls, self.budgets = list(records), fail, 0, []

    def top_recordings(self, mbid, *, remaining, cancelled):
        self.calls += 1
        self.budgets.append((remaining(), cancelled.is_set()))
        if self.fail:
            raise ProviderError("failed")
        return list(self.records)


class FakeMusicBrainz:
    def __init__(self, artists=(), tags=(), tracks=()):
        self._artists, self._tags, self._tracks = list(artists), list(tags), list(tracks)
        self.tag_calls = self.artist_calls = self.track_calls = 0

    def artists(self, query, *, remaining, cancelled):
        self.artist_calls += 1
        return list(self._artists)

    def artist_tags(self, mbid, *, remaining, cancelled):
        self.tag_calls += 1
        return list(self._tags)

    def release_group_tracks(self, mbid, *, remaining, cancelled):
        self.track_calls += 1
        return list(self._tracks)


def network(store, refresher=None, listenbrainz=None, musicbrainz=None):
    return ArtistNetwork(
        musicbrainz=musicbrainz or FakeMusicBrainz(), popularity=lambda mbids, can_cache: {},
        bio=lambda name: None, cache_read=store.read, cache_write=store.write,
        listenbrainz=listenbrainz, refresh_submit=refresher.submit if refresher else None,
    )


def stored(store, key, records, age):
    store.data[key] = {"at": time.time() - age, "results": records}


def top(net, cancelled=None):
    return top_songs(
        net, "Radiohead", "ar1", None, mbid="mb-rh",
        remaining=lambda: 5.0, cancelled=cancelled or threading.Event(),
    )


class ReadCachedStateTests(unittest.TestCase):
    def test_fresh_stale_and_past_maximum(self):
        store = Store()
        stored(store, "k", [{"name": "a"}], POSITIVE_TTL_SECONDS - 60)
        self.assertEqual(read_cached_state(store.read, "k", time.time()), ([{"name": "a"}], False))
        stored(store, "k", [{"name": "a"}], 3 * DAY)
        self.assertEqual(read_cached_state(store.read, "k", time.time()), ([{"name": "a"}], True))
        stored(store, "k", [{"name": "a"}], POSITIVE_TTL_SECONDS * STALE_FACTOR + 60)
        self.assertEqual(read_cached_state(store.read, "k", time.time()), (None, False))

    def test_empty_answer_uses_the_negative_ttl(self):
        store = Store()
        stored(store, "k", [], NEGATIVE_TTL_SECONDS * 3)
        self.assertEqual(read_cached_state(store.read, "k", time.time()), ([], True))
        stored(store, "k", [], NEGATIVE_TTL_SECONDS * STALE_FACTOR + 60)
        self.assertEqual(read_cached_state(store.read, "k", time.time()), (None, False))

    def test_missing_and_malformed_rows_are_misses(self):
        store = Store()
        self.assertEqual(read_cached_state(store.read, "k", time.time()), (None, False))
        store.data["k"] = {"at": "yesterday", "results": []}
        self.assertEqual(read_cached_state(store.read, "k", time.time()), (None, False))

    def test_read_cached_is_unchanged(self):
        store = Store()
        stored(store, "k", [{"name": "a"}], 3 * DAY)
        self.assertIsNone(cache.read_cached(store.read, "k", time.time()))


class ReadOrRevalidateTests(unittest.TestCase):
    def test_without_submit_an_expired_row_is_a_miss(self):
        store = Store()
        stored(store, "k", [{"name": "a"}], 3 * DAY)
        self.assertIsNone(read_or_revalidate(store.read, "k", submit=None, refetch=lambda r, c: None))

    def test_stale_row_is_served_and_one_refresh_submitted(self):
        store, refresher = Store(), Refresher()
        stored(store, "k", [{"name": "a"}], 3 * DAY)
        for _ in range(2):
            hit = read_or_revalidate(store.read, "k", submit=refresher.submit, refetch=lambda r, c: None)
            self.assertEqual(hit, [{"name": "a"}])
        self.assertEqual(refresher.keys, [REFRESH_KEY_PREFIX + "k"] * 2)
        self.assertEqual(len(refresher.pending), 1)

    def test_fresh_and_too_old_rows_submit_nothing(self):
        store, refresher = Store(), Refresher()
        stored(store, "k", [{"name": "a"}], 60)
        self.assertEqual(read_or_revalidate(store.read, "k", submit=refresher.submit, refetch=None), [{"name": "a"}])
        stored(store, "k", [{"name": "a"}], 11 * DAY)
        self.assertIsNone(read_or_revalidate(store.read, "k", submit=refresher.submit, refetch=None))
        self.assertEqual(refresher.keys, [])

    def test_refused_submit_still_serves_the_stale_row(self):
        store = Store()
        stored(store, "k", [{"name": "a"}], 3 * DAY)
        hit = read_or_revalidate(store.read, "k", submit=lambda key, refresh: False, refetch=None)
        self.assertEqual(hit, [{"name": "a"}])

    def test_refresh_gets_its_own_budget(self):
        remaining, cancelled = cache.refresh_budget()
        self.assertGreater(remaining(), cache.REFRESH_DEADLINE_SECONDS - 1)
        self.assertFalse(cancelled.is_set())


class TopSongsTests(unittest.TestCase):
    def test_stale_row_is_served_then_refreshed(self):
        store, refresher = Store(), Refresher()
        stored(store, LB_KEY, [song("Old", 1)], 3 * DAY)
        listenbrainz = FakeListenBrainz([song("New", 2)])
        section = top(network(store, refresher, listenbrainz))
        self.assertEqual([item["name"] for item in section["items"]], ["Old"])
        self.assertEqual(listenbrainz.calls, 0)
        refresher.run()
        self.assertEqual(listenbrainz.calls, 1)
        self.assertEqual(store.data[LB_KEY]["results"][0]["name"], "New")
        self.assertGreater(store.data[LB_KEY]["at"], time.time() - 60)

    def test_refresh_writes_after_the_request_is_cancelled(self):
        store, refresher = Store(), Refresher()
        stored(store, LB_KEY, [song("Old", 1)], 3 * DAY)
        listenbrainz = FakeListenBrainz([song("New", 2)])
        request_cancelled = threading.Event()
        top(network(store, refresher, listenbrainz), cancelled=request_cancelled)
        request_cancelled.set()  # the page has returned; its budget is spent
        refresher.run()
        self.assertEqual(listenbrainz.budgets[0][1], False)
        self.assertGreater(listenbrainz.budgets[0][0], 0)
        self.assertEqual(store.data[LB_KEY]["results"][0]["name"], "New")

    def test_failed_refresh_keeps_the_stale_row(self):
        store, refresher = Store(), Refresher()
        stored(store, LB_KEY, [song("Old", 1)], 3 * DAY)
        before = dict(store.data[LB_KEY])
        top(network(store, refresher, FakeListenBrainz(fail=True)))
        refresher.run()
        self.assertEqual(store.data[LB_KEY], before)
        self.assertEqual(store.writes, 0)

    def test_without_refresher_an_expired_row_is_fetched_in_the_request(self):
        store = Store()
        stored(store, LB_KEY, [song("Old", 1)], 3 * DAY)
        listenbrainz = FakeListenBrainz([song("New", 2)])
        section = top(network(store, None, listenbrainz))
        self.assertEqual([item["name"] for item in section["items"]], ["New"])
        self.assertEqual(listenbrainz.calls, 1)

    def test_row_past_maximum_staleness_is_fetched_in_the_request(self):
        store, refresher = Store(), Refresher()
        stored(store, LB_KEY, [song("Old", 1)], 11 * DAY)
        listenbrainz = FakeListenBrainz([song("New", 2)])
        section = top(network(store, refresher, listenbrainz))
        self.assertEqual([item["name"] for item in section["items"]], ["New"])
        self.assertEqual(refresher.keys, [])


class TagTests(unittest.TestCase):
    KEY = provider_cache_key("musicbrainz", 0, "artist-tags:mb-x", "tags")

    def test_seed_tags_are_served_stale(self):
        store, refresher = Store(), Refresher()
        stored(store, self.KEY, [{"name": "rock"}], TAG_TTL_SECONDS + DAY)
        musicbrainz = FakeMusicBrainz(tags=[{"name": "jazz"}])
        tags, hit = _tags_for(network(store, refresher, musicbrainz=musicbrainz), "mb-x",
                              remaining=lambda: 5.0, cancelled=threading.Event(), seed=True)
        self.assertEqual((tags, hit, musicbrainz.tag_calls), ({"rock"}, False, 0))
        refresher.run()
        self.assertEqual(store.data[self.KEY]["results"], [{"name": "jazz"}])

    def test_candidate_tags_expire_as_before(self):
        store, refresher = Store(), Refresher()
        stored(store, self.KEY, [{"name": "rock"}], TAG_TTL_SECONDS + DAY)
        musicbrainz = FakeMusicBrainz(tags=[{"name": "jazz"}])
        tags, _ = _tags_for(network(store, refresher, musicbrainz=musicbrainz), "mb-x",
                            remaining=lambda: 5.0, cancelled=threading.Event())
        self.assertEqual((tags, musicbrainz.tag_calls, refresher.keys), ({"jazz"}, 1, []))


class IdentityAndTracksTests(unittest.TestCase):
    def test_stale_artist_lookup_is_served(self):
        store, refresher = Store(), Refresher()
        key = provider_cache_key("musicbrainz", 0, "radiohead", "artist")
        stored(store, key, [{"key": "radiohead", "mbid": "mb-old"}], 3 * DAY)
        musicbrainz = FakeMusicBrainz(artists=[{"key": "radiohead", "mbid": "mb-new"}])
        mbid = resolve_identity(network(store, refresher, musicbrainz=musicbrainz), "Radiohead", None,
                                remaining=lambda: 5.0, cancelled=threading.Event())
        self.assertEqual((mbid, musicbrainz.artist_calls), ("mb-old", 0))
        refresher.run()
        self.assertEqual(store.data[key]["results"][0]["mbid"], "mb-new")

    def test_stale_tracklist_is_served_then_raced_again(self):
        store, refresher = Store(), Refresher()
        key = provider_cache_key("tracks", 0, "radiohead/ok computer", "tracks")
        old = [{"track_number": 1, "title": "Airbag", "duration_seconds": 1}]
        new = [{"track_number": 1, "title": "Airbag", "duration_seconds": 284}]
        stored(store, key, old, SIMILAR_TTL_SECONDS + DAY)
        musicbrainz = FakeMusicBrainz(tracks=new)
        net = network(store, refresher, musicbrainz=musicbrainz)
        tracks = race_tracks(net, "Radiohead", "OK Computer", "rg-1", remaining=lambda: 5.0, cancelled=threading.Event())
        self.assertEqual((tracks, musicbrainz.track_calls), (old, 0))
        refresher.run()
        self.assertEqual(store.data[key]["results"], new)


class RefresherWiringTests(unittest.TestCase):
    def test_pages_use_their_own_pool(self):
        self.assertIsInstance(DISCOVERY_REFRESHER, BackgroundRefresher)
        self.assertIsNot(DISCOVERY_REFRESHER, REFRESHER)

    def test_overflow_drops_the_refresh_and_serves_stale(self):
        store = Store()
        refresher = BackgroundRefresher(max_pending=1, executor=_Held())
        stored(store, "a", [{"name": "a"}], 3 * DAY)
        stored(store, "b", [{"name": "b"}], 3 * DAY)
        read_or_revalidate(store.read, "a", submit=refresher.submit, refetch=lambda r, c: None)
        hit = read_or_revalidate(store.read, "b", submit=refresher.submit, refetch=lambda r, c: None)
        self.assertEqual(hit, [{"name": "b"}])
        self.assertEqual((refresher.submitted, refresher.dropped), (1, 1))

    def test_page_network_carries_the_discovery_refresher(self):
        from app.api import search

        class Librarian:
            def _discovery_settings_read(self):
                return {}

            def _discovery_read_list(self, name):
                return None

            def _discovery_write_list(self, name, payload):
                pass

            def api_call(self, *args, **kwargs):
                return {}

            _metadata_cache_get = staticmethod(lambda key, ttl: None)
            _metadata_cache_set = staticmethod(lambda key, value: None)

        net = search.artist_network_for(Librarian())
        self.assertEqual(net.refresh_submit, DISCOVERY_REFRESHER.submit)
        # The worker's precompute keeps today's expiry.
        from app.services.similar_precompute import precompute_network
        self.assertIsNone(precompute_network(Librarian()).refresh_submit)


class _Held:
    """An executor that keeps submitted work queued, so the pending count stays up."""

    def submit(self, fn, *args):
        return None


if __name__ == "__main__":
    unittest.main()
