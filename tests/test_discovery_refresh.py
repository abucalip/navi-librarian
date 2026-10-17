import unittest
from threading import Lock

from discovery_refresh import (
    cache_staleness_reason,
    refresh_all,
    refresh_other,
    refresh_personal,
    refresh_stale_lists,
)


class DiscoveryRefreshTests(unittest.TestCase):
    def test_cache_staleness_classifies_missing_expired_fresh_and_bad_timestamps(self):
        self.assertEqual(
            cache_staleness_reason(None, now=100, max_age_seconds=24),
            "missing",
        )
        self.assertEqual(
            cache_staleness_reason({"generated_at": 76}, now=100, max_age_seconds=24),
            "expired",
        )
        self.assertIsNone(
            cache_staleness_reason({"generated_at": 77}, now=100, max_age_seconds=24)
        )
        self.assertIsNone(
            cache_staleness_reason({"generated_at": 101}, now=100, max_age_seconds=24)
        )
        for cached in ({}, {"generated_at": None}, {"generated_at": "bad"}, {"generated_at": "nan"}, {"generated_at": "inf"}):
            with self.subTest(cached=cached):
                self.assertEqual(
                    cache_staleness_reason(cached, now=100, max_age_seconds=24),
                    "invalid_timestamp",
                )

    def test_scheduler_refreshes_stale_lists_and_keeps_fresh_lists(self):
        reads = {
            "missing": None,
            "expired": {"generated_at": 10},
            "fresh": {"generated_at": 95},
        }
        refreshed = []
        outcomes = refresh_stale_lists(
            ["missing", "expired", "fresh"],
            reads.__getitem__,
            lambda name: refreshed.append(name) or {"ok": True},
            now=100,
            max_age_seconds=24,
        )
        self.assertEqual(refreshed, ["missing", "expired"])
        self.assertEqual(
            outcomes,
            [
                {"list": "missing", "status": "refreshed", "reason": "missing"},
                {"list": "expired", "status": "refreshed", "reason": "expired"},
                {"list": "fresh", "status": "fresh"},
            ],
        )

    def test_scheduler_read_failure_does_not_block_later_lists(self):
        refreshed = []

        def read(name):
            if name == "broken":
                raise OSError("private provider URL must not be surfaced")
            return None

        outcomes = refresh_stale_lists(
            ["broken", "later"],
            read,
            lambda name: refreshed.append(name) or {"ok": True},
            now=100,
            max_age_seconds=24,
        )
        self.assertEqual(refreshed, ["later"])
        self.assertEqual(outcomes[0], {
            "list": "broken",
            "status": "read_failed",
            "stage": "read",
            "error_type": "OSError",
        })
        self.assertNotIn("private provider URL", repr(outcomes))

    def test_scheduler_refresh_failure_does_not_block_later_lists(self):
        refreshed = []

        def refresh(name):
            if name == "broken":
                raise RuntimeError("private details")
            refreshed.append(name)
            return {"ok": True}

        outcomes = refresh_stale_lists(
            ["broken", "later"],
            lambda name: None,
            refresh,
            now=100,
            max_age_seconds=24,
        )
        self.assertEqual(refreshed, ["later"])
        self.assertEqual(outcomes[0], {
            "list": "broken",
            "status": "refresh_failed",
            "stage": "refresh",
            "reason": "missing",
            "error_type": "RuntimeError",
        })

    def test_scheduler_records_failed_refresh_result_without_provider_details(self):
        outcomes = refresh_stale_lists(
            ["personal"],
            lambda name: None,
            lambda name: {"ok": False, "status": "error", "details": "secret"},
            now=100,
            max_age_seconds=24,
        )
        self.assertEqual(outcomes, [{
            "list": "personal",
            "status": "refresh_failed",
            "stage": "refresh",
            "reason": "missing",
        }])

    def test_scheduler_preserves_already_running_status(self):
        outcomes = refresh_stale_lists(
            ["personal"],
            lambda name: None,
            lambda name: {"ok": False, "status": "already_running"},
            now=100,
            max_age_seconds=24,
        )
        self.assertEqual(outcomes[0]["status"], "already_running")

    def test_refresh_all_preserves_callback_order_and_results(self):
        calls = []
        def personal(count):
            calls.append(("personal", count))
            return "personal-result"
        def other(name):
            calls.append(("other", name))
            return name

        result = refresh_all(personal, other)

        self.assertEqual(calls, [
            ("personal", 20),
            ("other", "classics"),
            ("other", "artist_deep_dive"),
            ("other", "new_releases"),
        ])
        self.assertEqual(result, ["personal-result", "classics", "artist_deep_dive", "new_releases"])

    def test_personal_refresh_parses_persists_and_records_origin(self):
        writes = []
        outcomes = []
        calls = []
        def recommend(**kwargs):
            calls.append(kwargs)
            return '{"recommendations": [{"artist": "Björk"}]}'
        result = refresh_personal(
            Lock(),
            recommend,
            lambda name, payload: writes.append((name, payload)),
            count=7,
            clock=lambda: 123.5,
            origin="scheduler",
            record_outcome=outcomes.append,
        )
        self.assertEqual(result, {
            "ok": True, "list": "personal", "generated_at": 123.5,
            "recommendations": 1,
        })
        self.assertEqual(writes, [("personal", {"recommendations": [{"artist": "Björk"}]})])
        self.assertEqual(calls, [{"count": 7}])
        self.assertEqual(outcomes, [{
            "list_name": "personal", "origin": "scheduler", "status": "success",
            "generated_at": 123.5, "item_count": 1, "error_type": None,
        }])

    def test_personal_error_records_bounded_outcome_without_persisting_payload(self):
        outcomes = []
        result = refresh_personal(
            Lock(),
            lambda **kwargs: '{"error": "private provider URL"}',
            lambda *args: self.fail("failed recommendation must not be persisted"),
            origin="manual",
            record_outcome=outcomes.append,
            clock=lambda: 456.0,
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(outcomes, [{
            "list_name": "personal", "origin": "manual", "status": "error",
            "generated_at": 456.0, "item_count": None, "error_type": None,
        }])
        self.assertNotIn("private provider URL", repr(outcomes))

    def test_refresh_outcome_callback_failure_does_not_fail_successful_refresh(self):
        writes = []
        def broken_diagnostics(_outcome):
            raise OSError("private diagnostic backend detail")
        result = refresh_personal(
            Lock(),
            lambda **kwargs: '{"recommendations": [{"artist": "Björk"}]}',
            lambda name, payload: writes.append((name, payload)),
            record_outcome=broken_diagnostics,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(writes), 1)

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
