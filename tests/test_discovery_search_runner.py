"""Deadline runner, shared provider calls and streamed source events (contract sections 3.7 and 5.2)."""

import queue
import threading
import time
import unittest

from discovery.search.events import search_events
from discovery.search.index import IndexView, STATE_FRESH, build_owned_data
from discovery.search.providers import ProviderError, artist_candidate
from discovery.search.runner import ExternalSearch, FetchRegistry, Part, RunState, SharedFetch


def owned_ash():
    return build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Ash", "album_count": 1}],
        albums=[], songs=[],
    )


class Store:
    """A dict standing in for the persistent list store."""

    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, payload):
        self.data[key] = payload


def make_search(parts, store=None, registry=None, deadline=1.0):
    store = store or Store()
    return ExternalSearch(
        parts_for=lambda query, types: parts,
        sources={name: {"available": True, "reason": None} for name in ("navidrome", "musicbrainz", "lastfm")},
        registry=registry or FetchRegistry(),
        cache_read=store.read,
        cache_write=store.write,
        deadline_seconds=deadline,
    )


def run_stream(search, types=("artist",), limit=10, owned=None):
    run = RunState()
    events = list(search.stream(
        query="ash", types=list(types), limit=limit, owned=owned,
        started=time.monotonic(), run=run,
    ))
    return events, run


def fast(records):
    return lambda remaining, cancelled: records


def slow(seconds, records):
    def fetch(remaining, cancelled):
        cancelled.wait(seconds)
        return records
    return fetch


def failing(state):
    def fetch(remaining, cancelled):
        raise ProviderError(state)
    return fetch


def part(source, fetch, query="ash", kind="artist"):
    return Part(source=source, kind=kind, key=f"search:{source}:0:{query}:{kind}:depth50", fetch=fetch)


MB_ASH = [artist_candidate("musicbrainz", "Ash", "mb-1")]
LF_ASH_RA = [artist_candidate("lastfm", "Ash Ra", None)]


class StreamTests(unittest.TestCase):
    def test_each_source_reports_pending_then_results_then_its_terminal_state(self):
        events, run = run_stream(make_search([
            part("musicbrainz", fast(MB_ASH)),
            part("lastfm", slow(0.1, LF_ASH_RA)),
        ]))
        names = [(name, payload.get("source"), payload.get("state")) for name, payload in events]
        self.assertEqual(names[:2], [("source", "musicbrainz", "pending"), ("source", "lastfm", "pending")])
        self.assertEqual(names[2], ("result", None, None))
        self.assertEqual(names[3], ("source", "musicbrainz", "done"))
        self.assertEqual(names[-1], ("source", "lastfm", "done"))
        self.assertFalse(run.deadline_hit)
        self.assertFalse(run.degraded)

    def test_slow_source_times_out_at_the_deadline_and_other_results_are_kept(self):
        events, run = run_stream(make_search([
            part("musicbrainz", fast(MB_ASH)),
            part("lastfm", slow(5.0, LF_ASH_RA)),
        ], deadline=0.3))
        results = [p for name, p in events if name == "result"]
        lastfm = [p for name, p in events if name == "source" and p["source"] == "lastfm" and p["state"] != "pending"]
        self.assertEqual([r["name"] for r in results], ["Ash"])
        self.assertEqual(lastfm[0]["state"], "timeout")
        self.assertEqual(lastfm[0]["count"], 0)
        self.assertTrue(run.deadline_hit)
        self.assertTrue(run.degraded)

    def test_failing_source_does_not_affect_another(self):
        events, run = run_stream(make_search([
            part("musicbrainz", failing("failed")),
            part("lastfm", fast(LF_ASH_RA)),
        ]))
        states = {p["source"]: p["state"] for name, p in events if name == "source" and p["state"] != "pending"}
        self.assertEqual(states, {"musicbrainz": "failed", "lastfm": "done"})
        self.assertEqual([p["name"] for name, p in events if name == "result"], ["Ash Ra"])
        self.assertTrue(run.degraded)

    def test_rate_limited_source_is_reported_and_skipped(self):
        events, run = run_stream(make_search([part("musicbrainz", failing("rate_limited"))]))
        terminal = [p for name, p in events if name == "source" and p["state"] != "pending"]
        self.assertEqual(terminal, [{"source": "musicbrainz", "state": "rate_limited", "count": 0, "ms": terminal[0]["ms"]}])
        self.assertTrue(run.degraded)

    def test_owned_artist_is_not_emitted_from_a_provider(self):
        events, _ = run_stream(make_search([part("musicbrainz", fast(MB_ASH))]), owned=owned_ash())
        self.assertEqual([p for name, p in events if name == "result"], [])

    def test_limit_applies_per_type_to_provider_results(self):
        many = [artist_candidate("musicbrainz", f"Ash {i}", f"mb-{i}") for i in range(5)]
        events, _ = run_stream(make_search([part("musicbrainz", fast(many))]), limit=2)
        self.assertEqual(len([1 for name, _ in events if name == "result"]), 2)


class CacheAndSharingTests(unittest.TestCase):
    def test_completed_results_are_cached_under_the_contract_key(self):
        store = Store()
        run_stream(make_search([part("musicbrainz", fast(MB_ASH))], store=store))
        self.assertIn("search:musicbrainz:0:ash:artist:depth50", store.data)

    def test_cache_hit_is_reported_cached_and_no_provider_call_is_made(self):
        store = Store()
        store.write("search:musicbrainz:0:ash:artist:depth50", {"at": time.time(), "results": MB_ASH})

        def must_not_run(remaining, cancelled):
            raise AssertionError("provider called on a cache hit")

        events, _ = run_stream(make_search([part("musicbrainz", must_not_run)], store=store))
        source = [p for name, p in events if name == "source" and p["state"] != "pending"]
        self.assertEqual(source[0]["state"], "cached")
        self.assertEqual([p["name"] for name, p in events if name == "result"], ["Ash"])

    def test_timed_out_work_is_never_cached(self):
        store = Store()
        run_stream(make_search([part("lastfm", slow(5.0, LF_ASH_RA))], store=store, deadline=0.2))
        time.sleep(0.05)
        self.assertNotIn("search:lastfm:0:ash:artist:depth50", store.data)

    def test_identical_concurrent_searches_share_one_provider_call(self):
        registry = FetchRegistry()
        calls = []
        gate = threading.Event()

        def counted(remaining, cancelled):
            calls.append(1)
            gate.wait(2)
            return MB_ASH

        results = []
        threads = [
            threading.Thread(target=lambda: results.append(run_stream(
                make_search([part("musicbrainz", counted)], registry=registry, store=Store())
            )))
            for _ in range(2)
        ]
        for thread in threads:
            thread.start()
        time.sleep(0.1)
        gate.set()
        for thread in threads:
            thread.join(5)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(results), 2)
        for events, _ in results:
            self.assertEqual([p["name"] for name, p in events if name == "result"], ["Ash"])

    def test_shared_call_is_cancelled_only_when_its_last_consumer_leaves(self):
        registry = FetchRegistry()
        started = []
        work = registry.join("k", time.monotonic() + 9, lambda w: started.append(w), queue.Queue(), 0)
        second = registry.join("k", time.monotonic() + 9, lambda w: started.append(w), queue.Queue(), 1)
        self.assertIs(work, second)
        self.assertEqual(len(started), 1)
        registry.leave(work)
        self.assertFalse(work.cancelled.is_set())
        registry.leave(second)
        self.assertTrue(work.cancelled.is_set())

    def test_a_finished_call_is_not_shared_and_the_next_search_starts_a_new_one(self):
        registry = FetchRegistry()
        work = registry.join("k", time.monotonic() + 9, lambda w: None, queue.Queue(), 0)
        registry.finish(work, "done", MB_ASH, 3)
        started = []
        again = registry.join("k", time.monotonic() + 9, lambda w: started.append(w), queue.Queue(), 7)
        self.assertIsNot(again, work)
        self.assertEqual(len(started), 1)

    def test_consumer_is_notified_when_the_call_finishes_during_startup(self):
        registry = FetchRegistry()
        inbox = queue.Queue()
        work = registry.join(
            "k", time.monotonic() + 9,
            lambda w: registry.finish(w, "done", MB_ASH, 0),
            inbox, 4,
        )
        self.assertEqual(inbox.get_nowait(), (4, work))
        self.assertEqual(work.state, "done")

    def test_consumer_is_notified_when_a_thread_finishes_before_join_returns(self):
        registry = FetchRegistry()
        inbox = queue.Queue()
        registry.join(
            "k", time.monotonic() + 9,
            lambda w: threading.Thread(target=registry.finish, args=(w, "done", MB_ASH, 0)).start(),
            inbox, 5,
        )
        token, work = inbox.get(timeout=2)
        self.assertEqual((token, work.state), (5, "done"))

    def test_result_that_arrives_after_the_deadline_is_a_timeout_and_never_cached(self):
        store = Store()
        search = make_search([], store=store)
        work = SharedFetch("search:musicbrainz:0:ash:artist:depth50", time.monotonic() + 0.05)
        late = part("musicbrainz", lambda remaining, cancelled: (time.sleep(0.2), MB_ASH)[1])
        search._run(late, work)
        self.assertEqual(work.state, "timeout")
        self.assertEqual(work.records, [])
        self.assertEqual(store.data, {})

    def test_consumer_waiting_on_a_call_is_woken_when_it_finishes(self):
        registry = FetchRegistry()
        inbox = queue.Queue()
        work = registry.join("k", time.monotonic() + 9, lambda w: None, inbox, 3)
        registry.finish(work, "done", MB_ASH, 3)
        token, got = inbox.get_nowait()
        self.assertEqual((token, got.state), (3, "done"))


class EventsIntegrationTests(unittest.TestCase):
    def test_done_is_partial_when_a_network_source_fails_even_with_owned_results(self):
        view = IndexView(STATE_FRESH, owned_ash(), None)
        search = make_search([part("musicbrainz", failing("failed"))])
        events = list(search_events(
            view, query="ash", types=("artist",), limit=10,
            elapsed_ms=lambda: 5, external=search, started=time.monotonic(),
        ))
        names = [name for name, _ in events]
        self.assertEqual(names[0], "capabilities")
        self.assertEqual(names[-1], "done")
        self.assertEqual(names.count("done"), 1)
        self.assertTrue(events[-1][1]["partial"])
        self.assertFalse(events[-1][1]["deadline_hit"])

    def test_capabilities_report_the_external_sources(self):
        view = IndexView(STATE_FRESH, owned_ash(), None)
        search = make_search([])
        capabilities = next(payload for name, payload in search_events(
            view, query="ash", types=("artist",), limit=10,
            elapsed_ms=lambda: 0, external=search, started=time.monotonic(),
        ) if name == "capabilities")
        self.assertTrue(capabilities["sources"]["musicbrainz"]["available"])


if __name__ == "__main__":
    unittest.main()
