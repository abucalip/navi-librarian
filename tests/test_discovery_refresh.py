import unittest
from threading import Lock

from discovery_refresh import refresh_other, refresh_personal


class DiscoveryRefreshTests(unittest.TestCase):
    def test_personal_refresh_parses_and_persists_payload(self):
        writes = []
        result = refresh_personal(
            Lock(),
            lambda **kwargs: '{"recommendations": [{"artist": "Björk"}]}',
            lambda name, payload: writes.append((name, payload)),
            count=7,
            clock=lambda: 123.5,
        )
        self.assertEqual(result, {
            "ok": True, "list": "personal", "generated_at": 123.5,
            "recommendations": 1,
        })
        self.assertEqual(writes, [("personal", {"recommendations": [{"artist": "Björk"}]})])

    def test_personal_invalid_json_returns_error_without_write_and_releases_lock(self):
        lock = Lock()
        writes = []
        result = refresh_personal(lock, lambda **kwargs: "{broken",
                                  lambda *args: writes.append(args))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["details"], {
            "error": "Recommendation engine returned invalid JSON."
        })
        self.assertEqual(writes, [])
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()

    def test_personal_running_lock_returns_existing_status(self):
        lock = Lock()
        lock.acquire()
        try:
            result = refresh_personal(lock, lambda **kwargs: self.fail("must not call"),
                                      lambda *args: self.fail("must not write"))
            self.assertEqual(result, {
                "ok": False, "status": "already_running", "list": "personal"
            })
        finally:
            lock.release()

    def test_other_refresh_writes_payload_and_counts_items(self):
        lock = Lock()
        writes = []
        result = refresh_other(
            "classics", {"classics": lock},
            {"classics": lambda: {"items": [1, 2]}},
            lambda name, payload: writes.append((name, payload)),
            clock=lambda: 9.0,
        )
        self.assertEqual(result, {
            "ok": True, "list": "classics", "generated_at": 9.0, "items": 2
        })
        self.assertEqual(writes, [("classics", {"items": [1, 2]})])
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()

    def test_other_refresh_unknown_list_does_not_build_or_write(self):
        result = refresh_other("unknown", {}, {}, lambda *args: self.fail("must not write"))
        self.assertEqual(result, {"ok": False, "error": "Unknown discovery list"})

    def test_other_refresh_builder_failure_is_reported_and_lock_released(self):
        lock = Lock()
        def fail():
            raise RuntimeError("provider failed")
        result = refresh_other("new_releases", {"new_releases": lock},
                               {"new_releases": fail},
                               lambda *args: self.fail("must not write"))
        self.assertEqual(result, {
            "ok": False, "list": "new_releases", "error": "provider failed"
        })
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()


if __name__ == "__main__":
    unittest.main()
