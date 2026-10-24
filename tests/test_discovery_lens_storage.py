"""Offline tests for lens-list storage and serving (Engine 2, Phase 4, slice 3).

No provider, database or network call is made: stores are in-memory dicts and the policy is pure.
"""
import json
import threading
import unittest
from datetime import datetime

from discovery import lens_service, lens_storage
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


class LensDismissalTests(unittest.TestCase):
    """"Not for me" removes albums from a lens list at read time, like owned albums."""

    def test_dismissed_album_is_dropped_and_counted_separately(self):
        payload = _payload([_album(1, "A", "X"), _album(2, "B", "Y"), _album(3, "C", "Z")])
        is_dismissed = lambda item: (item["artist"], item["album"]) == ("B", "Y")  # noqa: E731
        served, counts = lens_storage.serve_lens_list(payload, _owned(), is_dismissed)
        self.assertEqual([item["rank"] for item in served["albums"]], [1, 3])
        self.assertEqual(counts["dismissed"], 1)
        self.assertEqual(counts["owned"], 0)

    def test_response_reports_dismissal_check_only_when_it_ran(self):
        cached = {"payload": _payload([_album(1, "A", "X"), _album(2, "B", "Y")]), "generated_at": 1.0}
        is_dismissed = lambda item: item["album"] == "Y"  # noqa: E731
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, _owned(), is_dismissed))
        self.assertEqual([item["album"] for item in body["items"]], ["X"])
        self.assertEqual(body["read_filter"]["dismissed"], 1)
        self.assertTrue(body["read_filter"]["ownership_checked"])

    def test_unreadable_feedback_serves_the_list_without_claiming_a_dismissal_check(self):
        cached = {"payload": _payload([_album(1, "A", "X")]), "generated_at": 1.0}
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, _owned(), None))
        self.assertNotIn("dismissed", body["read_filter"])
        self.assertEqual(body["count"], 1)

    def test_ranks_restart_at_one_when_the_first_album_is_dismissed(self):
        cached = {"payload": _payload([_album(1, "A", "X"), _album(2, "B", "Y")]), "generated_at": 1.0}
        is_dismissed = lambda item: item["album"] == "X"  # noqa: E731
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, _owned(), is_dismissed))
        self.assertEqual([(item["rank"], item["album"]) for item in body["items"]], [(1, "Y")])

    def test_both_checks_unavailable_serves_a_valid_response_for_malformed_entries(self):
        # Ownership and feedback both unreadable: nothing is filtered, but a malformed cache entry
        # must not turn the read into an error. Non-album entries are dropped; ranks stay 1..n.
        cached = {"payload": _payload(["not-an-album", _album(2, "A", "X"), None, _album(4, "B", "Y")]),
                  "generated_at": 1.0}
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, None, None))
        self.assertEqual([(item["rank"], item["album"]) for item in body["items"]], [(1, "X"), (2, "Y")])
        self.assertEqual(body["read_filter"], {"ownership_checked": False})

    def test_a_cache_entry_with_a_non_list_albums_field_serves_no_items(self):
        cached = {"payload": {"lens": "deep_cuts", "label": "Deep cuts", "day": "2026-10-24",
                              "albums": "corrupt"}, "generated_at": 1.0}
        body = json.loads(build_lens_list_response("deep_cuts", 10, cached, None, None))
        self.assertEqual(body["items"], [])

    def test_dismissed_predicate_matches_album_and_artist_feedback_like_discover(self):
        from discovery.list_payload import dismissed_predicate

        feedback = [
            {"scope": "album", "status": "not_for_me", "artist_key": "b", "album_key": "y"},
            {"scope": "artist", "status": "not_for_me_artist", "artist_key": "c", "album_key": ""},
            {"scope": "album", "status": "saved", "artist_key": "d", "album_key": "w"},
        ]
        is_dismissed = dismissed_predicate(feedback, lambda text: str(text).strip().lower())
        self.assertTrue(is_dismissed({"artist": "B", "album": "Y"}))
        self.assertTrue(is_dismissed({"artist": "C", "album": "Anything"}))
        self.assertFalse(is_dismissed({"artist": "D", "album": "W"}))
        self.assertFalse(is_dismissed({"artist": "B", "album": "Other"}))


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


class RefreshLensGatingTests(unittest.TestCase):
    def test_disabled_build_never_evaluates_the_ownership_provider(self):
        def provider():
            raise AssertionError("ownership provider must not run while disabled")

        result = refresh_lens_lists(lambda: {"status": "disabled"},
                                    lambda name: self.fail("store must not be read"),
                                    lambda name, payload: self.fail("store must not be written"),
                                    threading.Lock(), excluded_provider=provider)
        self.assertEqual(result["status"], "disabled")

    def test_failed_gather_keeps_stored_lists_and_reports_failure_not_disabled(self):
        previous = _payload([_album(1, "A", "X")])
        writes = []
        result = refresh_lens_lists(
            lambda: {"status": "failed", "reason": "gather_status_error"},
            lambda name: {"payload": previous, "generated_at": 1.0},
            lambda name, payload: writes.append(name),
            threading.Lock(),
            excluded_provider=lambda: self.fail("ownership must not run after a failed gather"),
        )
        self.assertEqual(writes, [])
        self.assertEqual(result, {"ok": False, "status": "failed", "list": "lens_lists",
                                  "reason": "gather_status_error"})


def _librarian(**overrides):
    """A stand-in librarian whose every helper fails the test if the disabled path reaches it."""
    from types import SimpleNamespace

    def forbidden(name):
        def call(*args, **kwargs):
            raise AssertionError(name + " must not run while the setting is off")
        return call

    names = ("_discovery_library_snapshot", "_listenbrainz_recent", "_listenbrainz_username",
             "_discovery_read_list", "_discovery_write_list", "api_call", "items", "_music_key",
             "_discovery_is_album_candidate", "_metadata_cache_get", "_metadata_cache_set",
             "_discovery_feedback_rows")
    attributes = {name: forbidden(name) for name in names}
    attributes["_discovery_settings_read"] = lambda: {}
    attributes.update(overrides)
    return SimpleNamespace(**attributes)


class LensServiceDisabledPathTests(unittest.TestCase):
    """The default-off setting must not reach the library, providers or the store."""

    def test_disabled_setting_touches_no_library_provider_or_store(self):
        from unittest import mock

        touched = []

        def forbidden(name):
            def call(*args, **kwargs):
                touched.append(name)
                raise AssertionError(name + " must not run while the setting is off")
            return call

        with mock.patch("discovery.lens_pool_gatherer.gather_lens_pools", side_effect=forbidden("gather")):
            result = lens_service.refresh(_librarian())
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(touched, [])

    def test_gather_that_does_not_finish_is_reported_as_failure_and_stores_nothing(self):
        from unittest import mock

        writes = []
        librarian = _librarian(
            _discovery_settings_read=lambda: {"engine2_lens_lists_enabled": True},
            _listenbrainz_recent=lambda **kwargs: [],
            _discovery_read_list=lambda name: {"payload": _payload([_album(1, "A", "X")]),
                                               "generated_at": 1.0},
            _discovery_write_list=lambda name, payload: writes.append(name),
        )
        with mock.patch("discovery.lens_pool_gatherer.gather_lens_pools",
                        return_value={"status": "errored"}):
            result = lens_service.refresh(librarian)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "gather_status_errored")
        self.assertEqual(writes, [])


class LensReadGatingTests(unittest.TestCase):
    def test_read_while_off_touches_neither_store_nor_library(self):
        from app.api import discovery

        for lens in ("deep_cuts", "repeated_tracks", "obsessions"):
            with self.subTest(lens=lens):
                body = json.loads(lens_service.list_response(_librarian(), lens, 5))
                self.assertTrue(body["disabled"])
                self.assertEqual(body["items"], [])
                self.assertIsNone(body["generated_at"])
                route_body = discovery.discovery_list(lens, 5, librarian=_librarian())
                self.assertEqual(route_body["items"], [])
                self.assertTrue(route_body["disabled"])

    def test_read_while_on_serves_the_stored_list(self):
        cached = {"payload": _payload([_album(1, "A", "X")]), "generated_at": 1.0}
        librarian = _librarian(
            _discovery_settings_read=lambda: {"engine2_lens_lists_enabled": True},
            _discovery_read_list=lambda name: cached,
            _discovery_library_snapshot=lambda: {"albums": []},
            _music_key=lambda value: str(value).strip().lower(),
        )
        body = json.loads(lens_service.list_response(librarian, "deep_cuts", 5))
        self.assertEqual([item["album"] for item in body["items"]], ["X"])


class LensRouteDispatchTests(unittest.TestCase):
    def test_lens_names_go_to_the_lens_service_and_not_the_server_list(self):
        from unittest import mock
        from unittest.mock import Mock
        from app.api import discovery

        librarian = Mock()
        with mock.patch("discovery.lens_service.list_response", return_value='{"list": "deep_cuts"}') as served:
            body = discovery.discovery_list("deep_cuts", 5, librarian=librarian)
        served.assert_called_once_with(librarian, "deep_cuts", 5)
        self.assertEqual(body, {"list": "deep_cuts"})
        librarian.discovery_get_list.assert_not_called()


class ManualLensRefreshTests(unittest.TestCase):
    def test_all_refresh_also_starts_the_lens_refresh_in_the_app_layer(self):
        from unittest import mock
        from unittest.mock import Mock
        from app.api import discovery

        librarian = Mock()
        librarian.discovery_refresh_list.return_value = '{"ok": true}'
        with mock.patch("discovery.lens_service.start_refresh") as started:
            body = discovery.refresh_discovery_list("all", librarian=librarian)
        started.assert_called_once_with(librarian)
        self.assertEqual(body, {"ok": True})

    def test_other_refreshes_do_not_start_the_lens_refresh(self):
        from unittest import mock
        from unittest.mock import Mock
        from app.api import discovery

        librarian = Mock()
        librarian.discovery_refresh_list.return_value = '{"ok": true}'
        with mock.patch("discovery.lens_service.start_refresh") as started:
            discovery.refresh_discovery_list("classics", librarian=librarian)
        started.assert_not_called()

    def test_start_refresh_returns_at_once_and_refresh_is_not_run_on_the_caller_thread(self):
        from unittest import mock

        ran = threading.Event()
        with mock.patch("discovery.lens_service.refresh", side_effect=lambda librarian: ran.set()):
            thread = lens_service.start_refresh(_librarian())
            thread.join(5)
        self.assertTrue(ran.is_set())
        self.assertNotEqual(thread.ident, threading.get_ident())


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
