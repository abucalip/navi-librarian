"""Stale-while-revalidate read path for the stored personal snapshot (roadmap 3.4)."""
import json
import unittest
from unittest.mock import patch

import discovery_refresh
from discovery_list_payload import build_cached_discovery_list_response

import navidrome_server as server

NOW = 1_000_000.0
DAY = discovery_refresh.STALE_MAX_AGE_SECONDS
ENABLED = lambda: {"automatic_refill_enabled": True}  # noqa: E731
DISABLED = lambda: {"automatic_refill_enabled": False}  # noqa: E731


def music_key(value):
    return "".join(str(value or "").casefold().split())


def row(age):
    return {
        "generated_at": NOW - age,
        "payload": {"recommendations": [
            {"artist": "A", "album": "Owned Later", "mbid": "1"},
            {"artist": "B", "album": "Still Missing", "mbid": "2"},
        ]},
    }


class RevalidateOnReadTests(unittest.TestCase):
    def setUp(self):
        discovery_refresh._revalidate_in_flight.clear()
        discovery_refresh._revalidate_last_start.clear()
        self.refreshed, self.queued = [], []

    def call(self, cached, settings=ENABLED, clock=lambda: 0.0, name="personal"):
        return discovery_refresh.revalidate_on_read(
            name, cached, lambda n: self.refreshed.append(n), settings,
            now=NOW, clock=clock, start=self.queued.append,
        )

    def test_stale_snapshot_starts_one_rebuild_without_running_it_inline(self):
        self.assertEqual(self.call(row(DAY + 1)), "started")
        self.assertEqual(self.refreshed, [])  # the read never waits for the build
        self.queued.pop()()
        self.assertEqual(self.refreshed, ["personal"])

    def test_fresh_and_missing_snapshots_start_nothing(self):
        self.assertEqual(self.call(row(DAY - 1)), "fresh")
        self.assertEqual(self.call(None), "missing")
        self.assertEqual(self.queued, [])

    def test_invalid_timestamp_counts_as_stale(self):
        self.assertEqual(self.call({"generated_at": "bad", "payload": {}}), "started")

    def test_setting_off_runs_no_background_work(self):
        self.assertEqual(self.call(row(DAY + 1), settings=DISABLED), "disabled")
        self.assertEqual(self.queued, [])

    def test_unreadable_setting_never_raises_into_the_read(self):
        def broken():
            raise OSError("settings store down")
        self.assertEqual(self.call(row(DAY + 1), settings=broken), "error")
        self.assertEqual(self.queued, [])

    def test_rebuild_in_flight_is_not_started_again(self):
        self.assertEqual(self.call(row(DAY + 1)), "started")
        self.assertEqual(self.call(row(DAY + 1), clock=lambda: 10_000.0), "already_running")
        self.assertEqual(len(self.queued), 1)

    def test_cooldown_blocks_retry_after_failed_rebuild_then_allows_it(self):
        def failing(_name):
            raise RuntimeError("provider down")
        discovery_refresh.revalidate_on_read(
            "personal", row(DAY + 1), failing, ENABLED, now=NOW,
            clock=lambda: 0.0, start=lambda run: run(),
        )
        self.assertEqual(discovery_refresh._revalidate_in_flight, set())
        self.assertEqual(self.call(row(DAY + 1), clock=lambda: 60.0), "cooldown")
        after = discovery_refresh.REVALIDATE_COOLDOWN_SECONDS + 1
        self.assertEqual(self.call(row(DAY + 1), clock=lambda: after), "started")

    def test_start_failure_releases_the_in_flight_slot(self):
        def no_threads(_run):
            raise RuntimeError("can't start new thread")
        status = discovery_refresh.revalidate_on_read(
            "personal", row(DAY + 1), lambda n: None, ENABLED, now=NOW, start=no_threads,
        )
        self.assertEqual(status, "start_failed")
        self.assertEqual(discovery_refresh._revalidate_in_flight, set())


class ServedSnapshotTests(unittest.TestCase):
    def setUp(self):
        discovery_refresh._revalidate_in_flight.clear()
        discovery_refresh._revalidate_last_start.clear()

    def serve(self, cached, owned, on_stale):
        return json.loads(build_cached_discovery_list_response(
            "personal", 10, lambda _n: cached, [], {}, music_key, lambda _i: True,
            lambda: {"albums": owned}, on_stale=on_stale,
        ))

    def test_stale_snapshot_is_served_while_rebuild_is_triggered(self):
        queued, refreshed = [], []
        result = self.serve(row(DAY + 1), [], lambda c: discovery_refresh.revalidate_on_read(
            "personal", c, refreshed.append, ENABLED, now=NOW, start=queued.append))
        self.assertEqual([i["album"] for i in result["items"]], ["Owned Later", "Still Missing"])
        self.assertEqual(len(queued), 1)
        self.assertEqual(refreshed, [])

    def test_stale_snapshot_after_library_change_excludes_newly_owned_albums(self):
        queued = []
        result = self.serve(
            row(DAY + 1), [{"artist": "A", "album": "Owned Later"}],
            lambda c: discovery_refresh.revalidate_on_read(
                "personal", c, lambda n: None, ENABLED, now=NOW, start=queued.append))
        self.assertEqual([i["album"] for i in result["items"]], ["Still Missing"])
        self.assertEqual(len(queued), 1)

    def test_failing_hook_does_not_fail_the_read(self):
        def boom(_cached):
            raise RuntimeError("hook failed")
        result = self.serve(row(DAY + 1), [], boom)
        self.assertEqual(len(result["items"]), 2)

    def test_hook_is_not_called_for_other_lists(self):
        calls = []
        build_cached_discovery_list_response(
            "classics", 10, lambda _n: {"generated_at": 0, "payload": {"items": []}},
            [], {}, music_key, lambda _i: True, on_stale=calls.append,
        )
        self.assertEqual(calls, [])


class ServerWiringTests(unittest.TestCase):
    """The real discovery_get_list starts the same default rebuild the scheduler uses."""

    def setUp(self):
        discovery_refresh._revalidate_in_flight.clear()
        discovery_refresh._revalidate_last_start.clear()

    def read_stale(self, settings):
        started = []
        stale = {"generated_at": 1.0, "payload": {"recommendations": [
            {"artist": "B", "album": "Still Missing", "mbid": "2"}]}}
        real_start = discovery_refresh.threading.Thread.start
        with patch.object(server, "_discovery_read_list", lambda _n: stale), \
                patch.object(server, "_discovery_feedback_rows", lambda: []), \
                patch.object(server, "_discovery_library_snapshot", lambda: {"albums": []}), \
                patch.object(server, "_discovery_settings_read", lambda: settings), \
                patch.object(server, "_discovery_scheduler_refresh_one",
                             lambda name: started.append(name)), \
                patch.object(discovery_refresh.threading.Thread, "start",
                             lambda self: (real_start(self), self.join(5))):
            body = json.loads(server.discovery_get_list("personal", 10))
        return body, started

    def test_stale_read_serves_snapshot_and_rebuilds_personal_in_background(self):
        body, started = self.read_stale({})
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(started, ["personal"])

    def test_stale_read_with_refill_off_does_no_background_work(self):
        body, started = self.read_stale({"automatic_refill_enabled": False})
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(started, [])


if __name__ == "__main__":
    unittest.main()
