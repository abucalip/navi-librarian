import unittest
from threading import Lock

from discovery.refresh import refresh_personal
from discovery.snapshot import (
    filter_snapshot,
    replacement_decision,
    serve_snapshot,
)


def _rec(artist, album, rank=None):
    item = {"artist": artist, "album": album}
    if rank is not None:
        item["rank"] = rank
    return item


def _payload(*items):
    return {"recommendations": list(items)}


GOOD = _payload(_rec("A", "One", 1), _rec("B", "Two", 2), _rec("C", "Three", 3))


class ReplacementDecisionTests(unittest.TestCase):
    def test_degraded_builds_never_replace_a_stored_snapshot(self):
        cases = {
            "error": ({"error": "provider text"}, 0, "build_error"),
            "malformed": ("not a payload", 0, "build_error"),
            "missing_list": ({"other": []}, 0, "build_error"),
            "provider_failures": (GOOD, 1, "provider_failures"),
            "empty": (_payload(), 0, "empty_build"),
        }
        for label, (candidate, failures, reason) in cases.items():
            with self.subTest(label):
                self.assertEqual(
                    replacement_decision(GOOD, candidate, provider_failures=failures),
                    (False, reason),
                )

    def test_build_with_fewer_items_than_snapshot_is_rejected(self):
        smaller = _payload(_rec("A", "One", 1))
        self.assertEqual(
            replacement_decision(GOOD, smaller),
            (False, "fewer_items_than_snapshot"),
        )

    def test_equal_or_larger_healthy_build_replaces_snapshot(self):
        larger = _payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)])
        self.assertEqual(replacement_decision(GOOD, larger), (True, "accepted"))
        self.assertEqual(replacement_decision(GOOD, GOOD), (True, "accepted"))

    def test_first_build_without_snapshot_is_accepted(self):
        self.assertEqual(replacement_decision(None, GOOD), (True, "no_previous"))

    def test_degraded_stored_snapshot_is_replaced_by_a_healthy_build(self):
        self.assertEqual(
            replacement_decision({"error": "old"}, GOOD), (True, "no_previous")
        )

    def test_comparison_counts_only_currently_eligible_items(self):
        owned = {("A", "One")}

        def excluded(item):
            return (item["artist"], item["album"]) in owned

        # Stored list has 3 items, one now owned: 2 eligible.
        # A 2-item healthy build is not fewer eligible items than the stored snapshot.
        build = _payload(_rec("D", "Four", 1), _rec("E", "Five", 2))
        self.assertEqual(
            replacement_decision(GOOD, build, is_excluded=excluded),
            (True, "accepted"),
        )
        one = _payload(_rec("D", "Four", 1))
        self.assertEqual(
            replacement_decision(GOOD, one, is_excluded=excluded),
            (False, "fewer_items_than_snapshot"),
        )


class SnapshotFilterTests(unittest.TestCase):
    def test_owned_and_duplicate_identities_are_removed_at_read_time(self):
        stored = _payload(
            _rec("Björk", "Homogenic", 1),
            _rec("  björk ", "HOMOGENIC", 2),  # duplicate after normalization
            _rec("Radiohead", "Kid A", 3),      # owned now
            _rec("Autechre", "Tri Repetae", 4),
        )
        owned = {("radiohead", "kid a")}

        def excluded(item):
            key = (" ".join(item["artist"].casefold().split()),
                   " ".join(item["album"].casefold().split()))
            return key in owned

        served, counts = serve_snapshot(stored, excluded)
        self.assertEqual(
            [(r["artist"], r["rank"]) for r in served["recommendations"]],
            [("Björk", 1), ("Autechre", 4)],
        )
        self.assertEqual(counts, {"kept": 2, "owned": 1, "duplicate": 1, "unidentified": 0})

    def test_items_without_identity_are_dropped_and_counted_not_shown(self):
        kept, counts = filter_snapshot(
            [_rec("", "No Artist", 1), "bad", _rec("A", "One", 2)],
            lambda item: False,
        )
        self.assertEqual(kept, [_rec("A", "One", 2)])
        self.assertEqual(counts["unidentified"], 2)

    def test_serve_returns_copy_and_leaves_stored_payload_unchanged(self):
        stored = _payload(_rec("A", "One", 1), _rec("B", "Two", 2))
        serve_snapshot(stored, lambda item: item["artist"] == "A")
        self.assertEqual(len(stored["recommendations"]), 2)


class RefreshPersonalSnapshotGuardTests(unittest.TestCase):
    def _refresh(self, previous, recommend_output, writes, outcomes, **kwargs):
        return refresh_personal(
            Lock(),
            lambda **_: recommend_output,
            lambda name, payload: writes.append((name, payload)),
            clock=lambda: 900.0,
            record_outcome=outcomes.append,
            read_previous=lambda name: (
                None if previous is None else {"payload": previous, "generated_at": 1.0}
            ),
            **kwargs,
        )

    def test_degraded_build_keeps_previous_snapshot_and_reports_rejection(self):
        writes, outcomes = [], []
        result = self._refresh(GOOD, _payload(), writes, outcomes)
        self.assertEqual(writes, [])
        self.assertEqual(result, {
            "ok": False, "status": "rejected", "reason": "empty_build", "list": "personal",
        })
        self.assertEqual(outcomes, [{
            "list_name": "personal", "origin": "manual", "status": "rejected",
            "generated_at": 900.0, "item_count": None, "error_type": None,
        }])

    def test_healthy_build_replaces_snapshot(self):
        writes, outcomes = [], []
        bigger = _payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)])
        result = self._refresh(GOOD, bigger, writes, outcomes)
        self.assertTrue(result["ok"])
        self.assertEqual(len(writes), 1)

    def test_failures_within_threshold_share_do_not_block_refresh(self):
        writes, outcomes = [], []
        build = dict(_payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)]))
        build["provider_failure_count"] = 2
        build["provider_lookup_count"] = 20  # 10% is within the 20% threshold
        result = self._refresh(GOOD, build, writes, outcomes)
        self.assertTrue(result["ok"])
        self.assertEqual(len(writes), 1)

    def test_failures_above_threshold_share_keep_previous_snapshot(self):
        writes, outcomes = [], []
        build = dict(_payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)]))
        build["provider_failure_count"] = 5
        build["provider_lookup_count"] = 20  # 25% exceeds the 20% threshold
        result = self._refresh(GOOD, build, writes, outcomes)
        self.assertEqual(writes, [])
        self.assertEqual(result["reason"], "provider_failures")

    def test_failures_without_usable_lookup_count_fail_safe(self):
        for lookups in (None, 0):
            self.assertEqual(
                replacement_decision(GOOD, _payload(_rec("A", "One", 1)),
                                     provider_failures=1, provider_lookups=lookups),
                (False, "provider_failures"),
            )

    def test_threshold_boundary_is_inclusive(self):
        from discovery.snapshot import PROVIDER_FAILURE_SHARE_THRESHOLD
        lookups = 10
        failures = int(PROVIDER_FAILURE_SHARE_THRESHOLD * lookups)
        self.assertEqual(
            replacement_decision(GOOD, GOOD,
                                 provider_failures=failures, provider_lookups=lookups),
            (True, "accepted"),
        )

    def test_build_reporting_provider_failures_keeps_previous_snapshot(self):
        writes, outcomes = [], []
        bigger = dict(_payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)]))
        bigger["provider_failure_count"] = 2
        result = self._refresh(GOOD, bigger, writes, outcomes)
        self.assertEqual(writes, [])
        self.assertEqual(result["reason"], "provider_failures")
        self.assertEqual(outcomes[0]["status"], "rejected")

    def test_zero_or_missing_provider_failure_count_does_not_block_refresh(self):
        for value in (0, None):
            writes, outcomes = [], []
            build = dict(_payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)]))
            if value is not None:
                build["provider_failure_count"] = value
            result = self._refresh(GOOD, build, writes, outcomes)
            self.assertTrue(result["ok"], value)

    def test_malformed_provider_failure_count_is_ignored(self):
        for value in (True, -1, "3", 1.5):
            writes, outcomes = [], []
            build = dict(_payload(*[_rec(f"Artist {i}", f"Album {i}", i) for i in range(4)]))
            build["provider_failure_count"] = value
            result = self._refresh(GOOD, build, writes, outcomes)
            self.assertTrue(result["ok"], repr(value))

    def test_failing_snapshot_read_fails_closed(self):
        writes = []

        def broken_read(name):
            raise RuntimeError("database locked: /private/path")

        result = refresh_personal(
            Lock(),
            lambda **_: GOOD,
            lambda name, payload: writes.append((name, payload)),
            read_previous=broken_read,
        )
        self.assertEqual(writes, [])
        self.assertEqual(result["reason"], "previous_read_failed")
        self.assertNotIn("private", str(result))

    def test_without_read_previous_behavior_is_unchanged(self):
        writes = []
        result = refresh_personal(
            Lock(), lambda **_: _payload(), lambda n, p: writes.append((n, p)),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(writes), 1)


if __name__ == "__main__":
    unittest.main()
