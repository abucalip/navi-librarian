"""Direct-import tests for the sonic TTL cache (Server V2 Phase 7, slice 2): hits, expiry, bounds, status rule."""
import unittest

from intelligence.sonic.cache import CACHEABLE_STATUSES, MAX_ENTRIES, TTL_SECONDS, TTLCache


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class Hits(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.cache = TTLCache(ttl=60, max_entries=4, clock=self.clock)

    def test_stored_value_is_returned_until_ttl(self):
        self.assertTrue(self.cache.offer(("similar", "s", 10), "ok", {"x": 1}))
        self.clock.now += 59.9
        self.assertEqual(self.cache.get(("similar", "s", 10)), {"x": 1})

    def test_missing_key_is_none(self):
        self.assertIsNone(self.cache.get(("similar", "nope", 10)))

    def test_keys_differ_by_route_ids_and_count(self):
        self.cache.offer(("similar", "s", 10), "ok", "a")
        self.assertIsNone(self.cache.get(("similar", "s", 11)))
        self.assertIsNone(self.cache.get(("path", "s", 10)))
        self.assertIsNone(self.cache.get(("similar", "t", 10)))

    def test_empty_status_is_cached(self):
        self.cache.offer(("similar", "s", 10), "empty", {"status": "empty"})
        self.assertEqual(self.cache.get(("similar", "s", 10)), {"status": "empty"})


class Expiry(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.cache = TTLCache(ttl=60, max_entries=4, clock=self.clock)

    def test_entry_expires_at_ttl_and_is_removed(self):
        self.cache.offer("k", "ok", "v")
        self.clock.now += 60
        self.assertIsNone(self.cache.get("k"))
        self.assertEqual(len(self.cache), 0)

    def test_hit_does_not_extend_lifetime(self):
        self.cache.offer("k", "ok", "v")
        self.clock.now += 30
        self.assertEqual(self.cache.get("k"), "v")
        self.clock.now += 30
        self.assertIsNone(self.cache.get("k"))

    def test_reoffer_restarts_the_clock(self):
        self.cache.offer("k", "ok", "old")
        self.clock.now += 50
        self.cache.offer("k", "ok", "new")
        self.clock.now += 50
        self.assertEqual(self.cache.get("k"), "new")

    def test_defaults_are_one_hour_and_a_few_hundred_entries(self):
        self.assertEqual(TTL_SECONDS, 3600)
        self.assertTrue(100 <= MAX_ENTRIES <= 500)


class Bounds(unittest.TestCase):
    def setUp(self):
        self.cache = TTLCache(ttl=60, max_entries=3, clock=Clock())

    def test_oldest_entry_is_evicted_first(self):
        for key in "abc":
            self.cache.offer(key, "ok", key)
        self.cache.offer("d", "ok", "d")
        self.assertIsNone(self.cache.get("a"))
        self.assertEqual([self.cache.get(k) for k in "bcd"], ["b", "c", "d"])
        self.assertEqual(len(self.cache), 3)

    def test_reading_an_entry_protects_it_from_eviction(self):
        for key in "abc":
            self.cache.offer(key, "ok", key)
        self.assertEqual(self.cache.get("a"), "a")
        self.cache.offer("d", "ok", "d")
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.get("a"), "a")

    def test_never_grows_past_the_bound(self):
        for n in range(50):
            self.cache.offer(n, "ok", n)
        self.assertEqual(len(self.cache), 3)


class StatusRule(unittest.TestCase):
    def setUp(self):
        self.cache = TTLCache(ttl=60, max_entries=10, clock=Clock())

    def test_only_ok_and_empty_are_cacheable(self):
        self.assertEqual(CACHEABLE_STATUSES, ("ok", "empty"))

    def test_errors_are_never_stored(self):
        for status in ("not_found", "unavailable"):
            self.assertFalse(self.cache.offer(("similar", "s", 10), status, {"status": status}))
            self.assertIsNone(self.cache.get(("similar", "s", 10)))
        self.assertEqual(len(self.cache), 0)

    def test_an_error_does_not_replace_a_cached_answer(self):
        self.cache.offer("k", "ok", "good")
        self.assertFalse(self.cache.offer("k", "unavailable", "bad"))
        self.assertEqual(self.cache.get("k"), "good")


class Construction(unittest.TestCase):
    def test_rejects_nonsense_settings(self):
        with self.assertRaises(ValueError):
            TTLCache(ttl=0)
        with self.assertRaises(ValueError):
            TTLCache(max_entries=0)


if __name__ == "__main__":
    unittest.main()
