"""Offline tests for lens-list storage and serving (Engine 2, Phase 4, slice 3).

No provider, database or network call is made: stores are in-memory dicts and the policy is pure.
"""
import json
import threading
import unittest
from datetime import datetime

from discovery import lens_storage
from discovery.list_payload import build_lens_list_response
from discovery.refresh import refresh_all, refresh_lens_lists


def _album(rank, artist, album):
    return {"rank": rank, "artist": artist, "primary_artist": artist, "album": album,
            "album_listeners": 1000, "tags": ["indie"]}


def _payload(albums, day="2026-10-24"):
    return {"lens": "deep_cuts", "label": "Deep cuts", "day": day, "requested": 10,
            "albums": albums, "seed_tags": ["indie"]}


def _owned(*pairs):
    """Predicate for ownership: exact (artist, album) match, lower-cased."""
    owned = {(a.lower(), b.lower()) for a, b in pairs}
    return lambda item: (item["artist"].lower(), item["album"].lower()) in owned


class LensStorageNamesTests(unittest.TestCase):
    def test_storage_name_round_trips_only_known_lenses(self):
        self.assertEqual(lens_storage.lens_storage_name("deep_cuts"), "lens:deep_cuts")
        self.assertEqual(lens_storage.lens_name_from_storage("lens:obsessions"), "obsessions")
        self.assertIsNone(lens_storage.lens_name_from_storage("lens:unknown"))
        self.assertIsNone(lens_storage.lens_name_from_storage("personal"))


class LensDayTests(unittest.TestCase):
    def test_day_rolls_over_at_four_am_local(self):
        self.assertEqual(lens_storage.lens_day(datetime(2026, 10, 24, 3, 59)), "2026-10-23")
        self.assertEqual(lens_storage.lens_day(datetime(2026, 10, 24, 4, 0)), "2026-10-24")
        self.assertEqual(lens_storage.lens_day(datetime(2026, 1, 1, 0, 30)), "2025-12-31")

    def test_day_rejects_timezone_aware_input(self):
        from datetime import timezone
        with self.assertRaises(ValueError):
            lens_storage.lens_day(datetime(2026, 10, 24, 5, tzinfo=timezone.utc))


class LensReplacementTests(unittest.TestCase):
    def test_first_usable_build_is_accepted(self):
        candidate = _payload([_album(1, "A", "X")])
        self.assertEqual(lens_storage.lens_replacement_decision(None, candidate), (True, "no_previous"))

    def test_errored_or_empty_build_keeps_stored_list(self):
        stored = _payload([_album(1, "A", "X")])
        self.assertEqual(
            lens_storage.lens_replacement_decision(stored, {"error": "boom", "albums": []}),
            (False, "build_error"),
        )
        self.assertEqual(
            lens_storage.lens_replacement_decision(stored, _payload([])),
            (False, "empty_build"),
        )

    def test_build_with_fewer_eligible_albums_keeps_stored_list(self):
        stored = _payload([_album(1, "A", "X"), _album(2, "B", "Y")])
        candidate = _payload([_album(1, "C", "Z")])
        self.assertEqual(
            lens_storage.lens_replacement_decision(stored, candidate),
            (False, "fewer_items_than_snapshot"),
        )

    def test_owned_albums_do_not_count_toward_eligibility(self):
        stored = _payload([_album(1, "A", "X"), _album(2, "B", "Y")])
        candidate = _payload([_album(1, "C", "Z"), _album(2, "D", "W")])
        owned = _owned(("A", "X"))
        # Stored list has one eligible album left; the candidate has two.
        self.assertEqual(
            lens_storage.lens_replacement_decision(stored, candidate, is_excluded=owned),
            (True, "accepted"),
        )


class LensServeTests(unittest.TestCase):
    def test_owned_albums_are_dropped_and_ranks_are_kept(self):
        payload = _payload([_album(1, "A", "X"), _album(2, "B", "Y"), _album(3, "C", "Z")])
        served, counts = lens_storage.serve_lens_list(payload, _owned(("b", "y")))
        self.assertEqual([item["rank"] for item in served["albums"]], [1, 3])
        self.assertEqual(counts["owned"], 1)
        self.assertEqual(counts["kept"], 2)
        # The stored payload is not mutated.
        self.assertEqual(len(payload["albums"]), 3)

    def test_serving_a_payload_without_albums_returns_it_unchanged(self):
        served, counts = lens_storage.serve_lens_list({"error": "x"}, _owned())
        self.assertEqual(served, {"error": "x"})
        self.assertEqual(counts["kept"], 0)


class LensResponseTests(unittest.TestCase):
    def test_missing_list_says_so_without_items(self):
        body = json.loads(build_lens_list_response("deep_cuts", 10, None, None))
        self.assertEqual(body["items"], [])
        self.assertIsNone(body["generated_at"])

    def test_response_reports_checked_ownership_and_counts_only(self):
        cached = {"payload": _payload([_album(1, "A", "X"), _album(2, "B", "Y")]),
                  "generated_at": 123.0}
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, _owned(("A", "X"))))
        self.assertEqual(body["day"], "2026-10-24")
        self.assertEqual(body["total_before_filter"], 2)
        self.assertEqual([item["album"] for item in body["items"]], ["Y"])
        self.assertEqual(body["read_filter"], {"ownership_checked": True, "kept": 1, "owned": 1,
                                               "duplicate": 0, "unidentified": 0})

    def test_unreadable_library_serves_stored_albums_and_says_unchecked(self):
        cached = {"payload": _payload([_album(1, "A", "X")]), "generated_at": 1.0}
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, None))
        self.assertEqual(body["read_filter"], {"ownership_checked": False})
        self.assertEqual(body["count"], 1)


class RefreshLensListsTests(unittest.TestCase):
    def _store(self, initial=None):
        store = dict(initial or {})
        writes = []

        def read_list(name):
            return {"payload": store[name], "generated_at": 1.0} if name in store else None

        def write_list(name, payload):
            writes.append(name)
            store[name] = payload

        return store, writes, read_list, write_list

    def test_disabled_build_writes_nothing(self):
        store, writes, read_list, write_list = self._store()
        result = refresh_lens_lists(lambda: {"status": "disabled"}, read_list, write_list,
                                    threading.Lock())
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(writes, [])

    def test_failed_build_leaves_previous_lists_in_place(self):
        previous = _payload([_album(1, "A", "X")])
        store, writes, read_list, write_list = self._store({"lens:deep_cuts": previous})

        def boom():
            raise RuntimeError("provider exploded")

        result = refresh_lens_lists(boom, read_list, write_list, threading.Lock())
        self.assertEqual(result, {"ok": False, "list": "lens_lists", "error_type": "RuntimeError"})
        self.assertEqual(writes, [])
        self.assertIs(store["lens:deep_cuts"], previous)

    def test_partial_build_replaces_accepted_lenses_and_keeps_the_rest(self):
        previous_deep = _payload([_album(1, "A", "X"), _album(2, "B", "Y")])
        previous_obs = _payload([_album(1, "E", "V")])
        store, writes, read_list, write_list = self._store({
            "lens:deep_cuts": previous_deep, "lens:obsessions": previous_obs,
        })
        built = {"status": "built", "day": "2026-10-25", "lists": {
            "deep_cuts": _payload([_album(1, "C", "Z")], day="2026-10-25"),  # fewer than stored
            "obsessions": _payload([_album(1, "F", "U"), _album(2, "G", "T")], day="2026-10-25"),
        }}
        result = refresh_lens_lists(lambda: built, read_list, write_list, threading.Lock(),
                                    clock=lambda: 99.0)
        self.assertEqual(writes, ["lens:obsessions"])
        self.assertIs(store["lens:deep_cuts"], previous_deep)
        self.assertEqual(store["lens:obsessions"]["day"], "2026-10-25")
        self.assertEqual(result["lists"], {
            "deep_cuts": {"replaced": False, "reason": "fewer_items_than_snapshot"},
            "obsessions": {"replaced": True, "reason": "accepted"},
        })
        self.assertEqual(result["generated_at"], 99.0)
        self.assertEqual(result["day"], "2026-10-25")

    def test_outcome_carries_no_album_identities(self):
        _, _, read_list, write_list = self._store()
        built = {"status": "built", "day": "2026-10-24",
                 "lists": {"deep_cuts": _payload([_album(1, "Secret Artist", "Secret Album")])}}
        result = refresh_lens_lists(lambda: built, read_list, write_list, threading.Lock())
        self.assertNotIn("Secret", json.dumps(result))

    def test_concurrent_refresh_is_refused_while_lock_is_held(self):
        lock = threading.Lock()
        lock.acquire()
        try:
            result = refresh_lens_lists(lambda: self.fail("must not build"), lambda n: None,
                                        lambda n, p: None, lock)
        finally:
            lock.release()
        self.assertEqual(result["status"], "already_running")


class RefreshAllLensHookTests(unittest.TestCase):
    def test_lens_callback_runs_last_and_is_optional(self):
        calls = []
        result = refresh_all(
            lambda count: calls.append("personal") or "p",
            lambda name: calls.append(name) or name,
            lambda: calls.append("lens_lists") or "lens",
        )
        self.assertEqual(calls[-1], "lens_lists")
        self.assertEqual(result[-1], "lens")
        self.assertEqual(len(result), 5)


if __name__ == "__main__":
    unittest.main()
