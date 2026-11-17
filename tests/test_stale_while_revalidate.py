"""Efficiency K2: stale-while-revalidate for album reviews, outlet answers, album links and Apple pages."""
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.api import metadata
from app.services import layered_cache, persistent_metadata, stale_refresh
from app.services.layered_cache import LayeredCache, Loaded
from metadata_cache import MetadataCache

DAY = 24 * 60 * 60


class _QueuedExecutor:
    """Holds submitted work until the test runs it, so a refresh never races the assertion."""

    def __init__(self):
        self.tasks = []

    def submit(self, fn, *args):
        self.tasks.append((fn, args))

    def run_all(self):
        while self.tasks:
            fn, args = self.tasks.pop(0)
            fn(*args)


class _AgedStore:
    """A persistent store whose rows have ages, like `MetadataCache`."""

    def __init__(self, clock):
        self.clock = clock
        self.rows = {}
        self.writes = []

    def get(self, key, ttl_seconds):
        row = self.rows.get(key)
        if row is None or self.clock() - row[1] > ttl_seconds:
            return None
        return row[0]

    def get_with_age(self, key, max_age):
        row = self.rows.get(key)
        if row is None or self.clock() - row[1] > max_age:
            return None
        return row[0], self.clock() - row[1]

    def set(self, key, value):
        self.writes.append(key)
        self.rows[key] = (value, self.clock())

    def age(self, key, seconds):
        value, _ = self.rows[key]
        self.rows[key] = (value, self.clock() - seconds)


class _Case(unittest.TestCase):
    def setUp(self):
        self.now = 1_000_000.0
        self.store = _AgedStore(lambda: self.now)
        persistent_metadata.attach(self.store.get, self.store.set, self.store.get_with_age)
        self.addCleanup(persistent_metadata.detach)
        self.executor = _QueuedExecutor()
        refresher = patch.object(stale_refresh, "REFRESHER", stale_refresh.BackgroundRefresher(executor=self.executor))
        self.refresher = refresher.start()
        self.addCleanup(refresher.stop)
        for clock in (patch.object(layered_cache, "monotonic", lambda: self.now),
                      patch.object(metadata.time, "time", lambda: self.now)):
            clock.start()
            self.addCleanup(clock.stop)


class RefresherTests(unittest.TestCase):
    def test_one_refresh_per_key_and_overflow_is_dropped(self):
        executor = _QueuedExecutor()
        refresher = stale_refresh.BackgroundRefresher(max_pending=2, executor=executor)
        calls = []
        self.assertTrue(refresher.submit("a", lambda: calls.append("a")))
        self.assertFalse(refresher.submit("a", lambda: calls.append("a2")), "already pending")
        self.assertTrue(refresher.submit("b", lambda: calls.append("b")))
        self.assertFalse(refresher.submit("c", lambda: calls.append("c")), "queue full")
        self.assertEqual(refresher.dropped, 1)
        executor.run_all()
        self.assertEqual(calls, ["a", "b"])
        self.assertEqual(refresher.pending(), 0)
        self.assertTrue(refresher.submit("c", lambda: calls.append("c")), "room again after the run")

    def test_a_failing_refresh_is_counted_and_frees_its_key(self):
        executor = _QueuedExecutor()
        refresher = stale_refresh.BackgroundRefresher(executor=executor)
        refresher.submit("a", lambda: 1 / 0)
        executor.run_all()
        self.assertEqual((refresher.failed, refresher.pending()), (1, 0))

    def test_the_real_pool_runs_refreshes_off_the_calling_thread(self):
        refresher = stale_refresh.BackgroundRefresher(workers=1)
        ran = threading.Event()
        names = []
        refresher.submit("a", lambda: (names.append(threading.current_thread().name), ran.set()))
        self.assertTrue(ran.wait(5))
        self.assertTrue(names[0].startswith("stale-refresh"))


class LayeredCacheStaleTests(_Case):
    def lookup(self, cache, load, **extra):
        return cache.get_or_load_state("k", load, store_key="s", store_ttl=7 * DAY, stored_ttl=3600,
                                       max_stale=70 * DAY, **extra)

    def test_a_stale_value_is_returned_at_once_and_refreshed_once(self):
        cache = LayeredCache("t")
        self.store.set("s", "old")
        self.store.age("s", 8 * DAY)
        calls = []

        def load():
            calls.append(1)
            return Loaded("new", memory_ttl=3600, persist=True)

        self.assertEqual(self.lookup(cache, load), ("old", True))
        cache.clear()
        self.assertEqual(self.lookup(cache, load), ("old", True), "a second request while the refresh is queued")
        self.assertEqual(calls, [], "no provider call on the request path")
        self.assertEqual(len(self.executor.tasks), 1, "one refresh for both requests")
        self.executor.run_all()
        self.assertEqual(calls, [1])
        self.assertEqual(self.lookup(cache, load), ("new", False))
        self.assertEqual(self.store.rows["s"], ("new", self.now))

    def test_a_fresh_value_is_not_refreshed(self):
        cache = LayeredCache("t")
        self.store.set("s", "v")
        self.store.age("s", 6 * DAY)
        self.assertEqual(self.lookup(cache, lambda: self.fail("loaded")), ("v", False))
        self.assertEqual(self.executor.tasks, [])

    def test_past_the_maximum_staleness_the_value_is_missing(self):
        cache = LayeredCache("t")
        self.store.set("s", "ancient")
        self.store.age("s", 71 * DAY)
        self.assertEqual(self.lookup(cache, lambda: Loaded("new", memory_ttl=60)), ("new", False))
        self.assertEqual(self.executor.tasks, [])

    def test_a_failed_refresh_keeps_the_stale_value_and_writes_nothing(self):
        cache = LayeredCache("t")
        self.store.set("s", "old")
        self.store.age("s", 8 * DAY)
        self.lookup(cache, lambda: Loaded(None), refresh=lambda: 1 / 0)
        self.executor.run_all()
        self.assertEqual(self.lookup(cache, self.fail), ("old", True))
        self.assertEqual(self.store.rows["s"][0], "old")
        self.store.writes.clear()
        self.lookup(cache, lambda: Loaded(None), refresh=lambda: Loaded("x"))  # an unanswered provider
        self.executor.run_all()
        self.assertEqual(self.store.writes, [])
        self.assertEqual(cache.peek("k"), "old")

    def test_a_stale_value_leaves_memory_after_ten_minutes_so_a_failed_refresh_is_retried(self):
        cache = LayeredCache("t")
        self.store.set("s", "old")
        self.store.age("s", 8 * DAY)
        self.lookup(cache, lambda: Loaded(None), refresh=lambda: 1 / 0)
        self.executor.run_all()
        self.now += layered_cache.STALE_MEMORY_TTL - 1
        self.lookup(cache, self.fail)
        self.assertEqual(self.executor.tasks, [], "no new refresh while memory holds it")
        self.now += 2
        self.lookup(cache, self.fail, refresh=lambda: Loaded("new", memory_ttl=60, persist=True))
        self.assertEqual(len(self.executor.tasks), 1)

    def test_a_dropped_refresh_still_serves_the_stale_value(self):
        cache = LayeredCache("t", refresher=stale_refresh.BackgroundRefresher(max_pending=1, executor=self.executor))
        for key in ("s", "s2"):
            self.store.set(key, key)
            self.store.age(key, 8 * DAY)
        cache.get_or_load_state("a", self.fail, store_key="s", store_ttl=7 * DAY, stored_ttl=3600, max_stale=70 * DAY)
        found = cache.get_or_load_state("b", self.fail, store_key="s2", store_ttl=7 * DAY, stored_ttl=3600,
                                        max_stale=70 * DAY)
        self.assertEqual(found, ("s2", True))
        self.assertEqual(len(self.executor.tasks), 1)

    def test_without_max_stale_an_expired_row_is_a_miss_as_before(self):
        cache = LayeredCache("t")
        self.store.set("s", "old")
        self.store.age("s", 8 * DAY)
        value = cache.get_or_load("k", lambda: Loaded("new"), store_key="s", store_ttl=7 * DAY, stored_ttl=3600)
        self.assertEqual(value, "new")
        self.assertEqual(self.executor.tasks, [])

    def test_a_caller_that_refuses_stale_values_skips_a_stale_memory_entry(self):
        cache = LayeredCache("t")
        self.store.set("s", "old")
        self.store.age("s", 8 * DAY)
        self.lookup(cache, self.fail)
        value = cache.get_or_load("k", lambda: Loaded("new"), store_key="s", store_ttl=7 * DAY, stored_ttl=3600)
        self.assertEqual(value, "new")

    def test_a_store_without_ages_never_serves_stale(self):
        persistent_metadata.attach(self.store.get, self.store.set)
        cache = LayeredCache("t")
        self.store.set("s", "old")
        self.store.age("s", 8 * DAY)
        self.assertEqual(self.lookup(cache, lambda: Loaded("new")), ("new", False))


def review(source):
    return {"source": source, "quote": source + " says yes.", "url": "https://example.com/" + source}


class ReviewTests(_Case):
    def setUp(self):
        super().setUp()
        metadata._review_cache.clear()
        self.addCleanup(metadata._review_cache.clear)
        env = patch.dict(os.environ, {"GUARDIAN_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)

    def test_stale_outlet_misses_answer_at_once_and_each_outlet_is_asked_once_in_the_background(self):
        with patch.object(metadata, "_pitchfork_review", return_value=None) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None) as wordpress:
            self.assertEqual(metadata.album_reviews_for("Opeth", "Watershed"), {"reviews": []})
            outlets = 1 + len(metadata._WORDPRESS_REVIEW_SITES)
            self.assertEqual(pitchfork.call_count + wordpress.call_count, outlets)
            self.now += metadata._SOURCE_MISS_TTL + 60
            metadata._review_cache.clear()
            started = time.monotonic()
            self.assertEqual(metadata.album_reviews_for("Opeth", "Watershed"), {"reviews": []})
            self.assertLess(time.monotonic() - started, 2.0)
            self.assertEqual(pitchfork.call_count + wordpress.call_count, outlets, "no outlet asked on the request path")
            self.assertEqual(len(self.executor.tasks), outlets)
            self.executor.run_all()
            self.assertEqual(pitchfork.call_count + wordpress.call_count, 2 * outlets, "one ask per outlet, as before")

    def test_a_list_built_from_a_stale_outlet_is_not_stored_as_fresh(self):
        old = review("Pitchfork")
        with patch.object(metadata, "_pitchfork_review", return_value=old), \
                patch.object(metadata, "_wordpress_review", return_value=None):
            metadata.album_reviews_for("Opeth", "Watershed")
        top = "album-reviews:v1:opeth:watershed"
        self.store.age(top, 40 * DAY)
        for key in list(self.store.rows):
            if key.startswith("album-review-source:"):
                self.store.age(key, 40 * DAY)
        metadata._review_cache.clear()
        self.store.writes.clear()
        with patch.object(metadata, "_pitchfork_review", side_effect=AssertionError("asked inline")), \
                patch.object(metadata, "_wordpress_review", side_effect=AssertionError("asked inline")):
            self.assertEqual(metadata.album_reviews_for("Opeth", "Watershed")["reviews"], [old])
        self.assertEqual(self.store.writes, [], "nothing re-stamped on the request path")
        new = review("Pitchfork") | {"quote": "Updated."}
        with patch.object(metadata, "_pitchfork_review", return_value=new), \
                patch.object(metadata, "_wordpress_review", return_value=None):
            self.executor.run_all()
        self.assertEqual(self.store.rows[top][0]["reviews"], [new], "the background refresh stores the new list")

    def test_an_outlet_answer_past_seventy_days_is_asked_inline(self):
        with patch.object(metadata, "_pitchfork_review", return_value=review("Pitchfork")) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None):
            sources = metadata._review_sources("Opeth", "Watershed", allow_stale=True, stale=[])
            sources[0]()
            key = next(k for k in self.store.rows if "Pitchfork" in k)
            self.store.age(key, 71 * DAY)
            sources[0]()
        self.assertEqual(pitchfork.call_count, 2)
        self.assertEqual(self.executor.tasks, [])

    def test_a_failed_background_ask_leaves_the_stale_outlet_answer(self):
        with patch.object(metadata, "_pitchfork_review", return_value=review("Pitchfork")):
            metadata._review_sources("Opeth", "Watershed", allow_stale=True)[0]()
        key = next(k for k in self.store.rows if "Pitchfork" in k)
        self.store.age(key, 31 * DAY)
        stale = []
        with patch.object(metadata, "_pitchfork_review", side_effect=TimeoutError()):
            self.assertEqual(metadata._review_sources("Opeth", "Watershed", True, stale)[0](), review("Pitchfork"))
            self.executor.run_all()
        self.assertEqual(stale, ["Pitchfork"])
        self.assertEqual(self.store.rows[key][0]["review"], review("Pitchfork"))
        self.assertEqual(self.refresher.failed, 1)


class LinksTests(_Case):
    def setUp(self):
        super().setUp()
        for cache in (metadata._album_links_cache, metadata._apple_url_cache):
            cache.clear()
            self.addCleanup(cache.clear)

    def test_a_stale_apple_page_is_used_without_waiting_and_the_links_are_not_stored(self):
        self.store.set("apple-album-url:v1:a:b", "https://music.apple.com/old")
        self.store.age("apple-album-url:v1:a:b", 8 * DAY)
        with patch.object(metadata, "_json_or_none", return_value=None) as provider, \
                patch.object(metadata.album_links, "deezer_url", return_value="https://deezer.com/1"):
            links = metadata.album_page_links("A", "B", mbid="m")
            self.assertEqual(links["apple_music"], "https://music.apple.com/old")
            self.assertEqual(provider.call_count, 1, "only Deezer on the request path")
            self.assertNotIn("album-links:v1:a|b|m", self.store.rows)
            with patch.object(metadata.album_links, "apple_music_url", return_value="https://music.apple.com/new"):
                self.executor.run_all()
            self.assertEqual(provider.call_count, 2, "one Apple ask, now in the background")
        self.assertEqual(self.store.rows["apple-album-url:v1:a:b"][0], "https://music.apple.com/new")

    def test_stale_links_are_served_and_refreshed_with_a_fresh_apple_lookup(self):
        self.store.set("album-links:v1:a|b|m", {"deezer": "d"})
        self.store.age("album-links:v1:a|b|m", 8 * DAY)
        self.store.set("apple-album-url:v1:a:b", "https://music.apple.com/old")
        self.store.age("apple-album-url:v1:a:b", 8 * DAY)
        with patch.object(metadata, "_load_album_links", wraps=metadata._load_album_links) as load:
            self.assertEqual(metadata.album_page_links("A", "B", mbid="m"), {"deezer": "d"})
            load.assert_not_called()
            with patch.object(metadata, "_json_or_none", return_value=None), \
                    patch.object(metadata.album_links, "deezer_url", return_value="https://deezer.com/1"), \
                    patch.object(metadata.album_links, "apple_music_url", return_value="https://music.apple.com/new"):
                self.executor.run_all()
            load.assert_called_once_with("A", "B", "m")
        stored = self.store.rows["album-links:v1:a|b|m"][0]
        self.assertEqual(stored["apple_music"], "https://music.apple.com/new")


class MetadataCacheAgeTests(unittest.TestCase):
    def test_get_with_age_reports_the_row_age_and_honours_the_limit(self):
        now = [1000.0]
        with tempfile.TemporaryDirectory() as folder:
            cache = MetadataCache(Path(folder) / "c.sqlite3", clock=lambda: now[0])
            cache.set("k", {"a": 1})
            now[0] += 50
            self.assertEqual(cache.get_with_age("k", 60), ({"a": 1}, 50.0))
            self.assertIsNone(cache.get_with_age("k", 49))
            self.assertIsNone(cache.get("k", 49), "get is unchanged")
            self.assertIsNone(cache.get_with_age("missing", 60))

    def test_a_storage_error_is_a_miss(self):
        def broken(*args, **kwargs):
            raise sqlite3.OperationalError("disk")

        self.assertIsNone(MetadataCache("unused", connect=broken).get_with_age("k", 60))


if __name__ == "__main__":
    unittest.main()
