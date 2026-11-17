"""The bounded, single-flight metadata cache helper (efficiency P4)."""
import threading
import unittest
from unittest.mock import patch

from app.services import layered_cache, persistent_metadata
from app.services.layered_cache import LayeredCache, Loaded


class _Store:
    def __init__(self):
        self.data = {}
        self.reads = []

    def get(self, key, ttl_seconds):
        self.reads.append((key, ttl_seconds))
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


class LayeredCacheTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        clock = patch.object(layered_cache, "monotonic", lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.store = _Store()
        persistent_metadata.attach(self.store.get, self.store.set)
        self.addCleanup(persistent_metadata.detach)

    def test_memory_entries_never_exceed_the_bound_and_a_recent_read_survives(self):
        cache = LayeredCache("t", max_entries=3)
        for key in "abc":
            cache.put(key, key.upper(), 60)
        self.assertEqual(cache.peek("a"), "A")
        cache.put("d", "D", 60)
        self.assertEqual(len(cache), 3)
        self.assertNotIn("b", cache)
        self.assertEqual([cache.peek(k) for k in "acd"], ["A", "C", "D"])
        for i in range(50):
            cache.get_or_load(i, lambda i=i: Loaded(i, memory_ttl=60))
            self.assertLessEqual(len(cache), 3)

    def test_the_default_bound_is_two_thousand(self):
        cache = LayeredCache("t")
        for i in range(2100):
            cache.put(i, i, 60)
        self.assertEqual(len(cache), 2000)
        self.assertNotIn(99, cache)
        self.assertIn(100, cache)

    def test_each_answer_keeps_its_own_ttl(self):
        cache = LayeredCache("t")
        cache.get_or_load("short", lambda: Loaded("s", memory_ttl=10))
        cache.get_or_load("long", lambda: Loaded("l", memory_ttl=100))
        self.now += 9.9
        self.assertEqual((cache.peek("short"), cache.peek("long")), ("s", "l"))
        self.now += 0.2
        self.assertIsNone(cache.peek("short"))
        self.assertEqual(cache.peek("long"), "l")
        self.assertEqual(len(cache), 1)

    def test_an_answer_with_no_ttl_is_not_kept_and_is_asked_again(self):
        cache = LayeredCache("t")
        calls = []

        def load():
            calls.append(1)
            return Loaded({"retryable": True})

        self.assertEqual(cache.get_or_load("k", load, store_key="s"), {"retryable": True})
        cache.get_or_load("k", load, store_key="s")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(cache), 0)
        self.assertEqual(self.store.data, {})

    def test_an_exception_is_not_cached(self):
        cache = LayeredCache("t")
        with self.assertRaises(RuntimeError):
            cache.get_or_load("k", lambda: (_ for _ in ()).throw(RuntimeError("down")))
        self.assertEqual(cache.get_or_load("k", lambda: Loaded("v", memory_ttl=1)), "v")

    def test_the_store_is_read_with_its_ttl_and_written_only_when_asked(self):
        cache = LayeredCache("t")
        self.store.data["s:hit"] = "stored"
        self.assertEqual(cache.get_or_load("hit", lambda: self.fail("loaded"), store_key="s:hit",
                                           store_ttl=7, stored_ttl=50), "stored")
        self.assertEqual(self.store.reads, [("s:hit", 7)])
        self.store.data.clear()
        self.now += 49
        self.assertEqual(cache.peek("hit"), "stored")
        cache.get_or_load("a", lambda: Loaded("x", memory_ttl=1, persist=False), store_key="s:a")
        cache.get_or_load("b", lambda: Loaded("y", memory_ttl=1, persist=True), store_key="s:b")
        cache.get_or_load("c", lambda: Loaded("z", memory_ttl=1, persist=True))
        self.assertEqual(self.store.data, {"s:b": "y"})

    def test_a_stored_value_the_caller_rejects_is_ignored(self):
        cache = LayeredCache("t")
        self.store.data["s"] = {"artwork_url": None}
        value = cache.get_or_load("k", lambda: Loaded({"artwork_url": "u"}, memory_ttl=1, persist=True),
                                  store_key="s", accept_stored=lambda v: bool(v and v.get("artwork_url")),
                                  stored_ttl=1)
        self.assertEqual(value, {"artwork_url": "u"})
        self.assertEqual(self.store.data["s"], {"artwork_url": "u"})

    def _counting_flights(self):
        """Make each flight report a waiter that has started waiting on it."""
        arrived = threading.Semaphore(0)

        class Done(threading.Event):
            def wait(self, timeout=None):
                arrived.release()
                return super().wait(timeout)

        class Flight(layered_cache._Flight):
            def __init__(self):
                super().__init__()
                self.done = Done()

        flights = patch.object(layered_cache, "_Flight", Flight)
        flights.start()
        self.addCleanup(flights.stop)
        return arrived

    def _wait_for(self, arrived, count):
        for _ in range(count):
            self.assertTrue(arrived.acquire(timeout=5))

    def test_concurrent_identical_requests_share_one_load(self):
        cache = LayeredCache("t")
        arrived = self._counting_flights()
        started, release = threading.Event(), threading.Event()
        calls, results = [], []

        def load():
            calls.append(1)
            started.set()
            release.wait(5)
            return Loaded("v")  # not kept in memory, so only the flight can share it

        leader = threading.Thread(target=lambda: results.append(cache.get_or_load("k", load)))
        leader.start()
        started.wait(5)
        waiters = [threading.Thread(target=lambda: results.append(cache.get_or_load("k", load))) for _ in range(4)]
        for thread in waiters:
            thread.start()
        self._wait_for(arrived, 4)
        release.set()
        for thread in [leader, *waiters]:
            thread.join(5)
        self.assertEqual(len(calls), 1)
        self.assertEqual(results, ["v"] * 5)
        self.assertEqual(cache._flights, {})

    def test_waiters_get_the_leader_s_exception_and_the_next_call_retries(self):
        cache = LayeredCache("t")
        arrived = self._counting_flights()
        started, release = threading.Event(), threading.Event()
        calls, errors = [], []

        def load():
            calls.append(1)
            started.set()
            release.wait(5)
            raise RuntimeError("down")

        def call():
            try:
                cache.get_or_load("k", load)
            except RuntimeError as error:
                errors.append(str(error))

        threads = [threading.Thread(target=call)]
        threads[0].start()
        started.wait(5)
        threads += [threading.Thread(target=call) for _ in range(3)]
        for thread in threads[1:]:
            thread.start()
        self._wait_for(arrived, 3)
        release.set()
        for thread in threads:
            thread.join(5)
        self.assertEqual(errors, ["down"] * len(threads))
        self.assertEqual(len(calls), 1)
        self.assertEqual(cache.get_or_load("k", lambda: Loaded("ok")), "ok")

    def test_a_waiter_asks_on_its_own_when_the_leader_is_stuck(self):
        cache = LayeredCache("t", wait_seconds=0.05)
        started, release = threading.Event(), threading.Event()

        def stuck():
            started.set()
            release.wait(5)
            return Loaded("late")

        leader = threading.Thread(target=lambda: cache.get_or_load("k", stuck))
        leader.start()
        started.wait(5)
        self.assertEqual(cache.get_or_load("k", lambda: Loaded("own")), "own")
        release.set()
        leader.join(5)

    def test_peek_put_and_clear(self):
        cache = LayeredCache("t")
        self.assertIsNone(cache.peek("k"))
        self.assertEqual(cache.peek("k", "d"), "d")
        cache.put("k", "", 10)
        self.assertEqual(cache.peek("k", "d"), "")
        self.assertIn("k", cache)
        cache.clear()
        self.assertEqual(len(cache), 0)
        with self.assertRaises(ValueError):
            LayeredCache("t", max_entries=0)


if __name__ == "__main__":
    unittest.main()
