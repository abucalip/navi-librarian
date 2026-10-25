"""Deadline runner for external search: shared provider work and the source-event stream.

Contract sections 2, 3.7 and 5.2. One search has one deadline (3.0 s from receipt). Each
provider call is a ``SharedFetch`` keyed like its cache entry, so identical concurrent
searches share one set of calls. A shared call is cancelled only when its last consumer
leaves, and cancelled or unfinished work is never written to the cache.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from discovery.search.cache import read_cached, write_cached
from discovery.search.index import OwnedData
from discovery.search.merge import OwnedKeys, fresh_candidates, shape_result
from discovery.search.providers import ProviderError

SEARCH_DEADLINE_SECONDS = 3.0
BAD_STATES = ("failed", "timeout", "rate_limited")
# Worst state first: a source that has one failing part reports that failure.
_STATE_PRIORITY = ("timeout", "failed", "rate_limited")


class SharedFetch:
    """One provider call shared by every consumer that asked for the same cache key."""

    def __init__(self, key: str, deadline_at: float):
        self.key = key
        self.deadline_at = deadline_at
        self.cancelled = threading.Event()
        self.refs = 0
        self.finished = False
        self.state: str | None = None
        self.records: list[dict[str, Any]] = []
        self.ms = 0
        self._waiters: list[tuple[Any, queue.Queue]] = []


class FetchRegistry:
    """Process-wide table of in-flight provider calls. All state changes take one lock."""

    def __init__(self):
        # Reentrant so a start callback may report completion without deadlocking.
        self._lock = threading.RLock()
        self._inflight: dict[str, SharedFetch] = {}

    def join(
        self,
        key: str,
        deadline_at: float,
        start: Callable[[SharedFetch], None],
        inbox: queue.Queue,
        token: Any,
    ) -> SharedFetch:
        """Attach a consumer. The first consumer starts the call; later ones share it.

        The shared call runs until the latest deadline among its consumers, so a later consumer
        with time left keeps a call alive after an earlier consumer has timed out. Each consumer
        still stops waiting at its own deadline.

        ``inbox`` receives ``(token, work)`` when the work finishes. A call that has already
        finished is no longer in flight, so a later search starts a new one (the cache serves it).
        """
        with self._lock:
            work = self._inflight.get(key)
            is_new = work is None
            if is_new:
                work = SharedFetch(key, deadline_at)
                self._inflight[key] = work
            else:
                work.deadline_at = max(work.deadline_at, deadline_at)
            # Register this consumer before the worker can run, so a call that finishes at once
            # still notifies it.
            work.refs += 1
            work._waiters.append((token, inbox))
            if is_new:
                start(work)
            return work

    def leave(self, work: SharedFetch) -> None:
        """Detach a consumer. The call is cancelled only when no consumer remains."""
        with self._lock:
            work.refs -= 1
            if work.refs <= 0 and not work.finished:
                work.cancelled.set()

    def finish(self, work: SharedFetch, state: str, records: list[dict[str, Any]], ms: int) -> None:
        with self._lock:
            work.state = state
            work.records = records
            work.ms = ms
            work.finished = True
            if self._inflight.get(work.key) is work:
                del self._inflight[work.key]
            for token, inbox in work._waiters:
                inbox.put((token, work))
            work._waiters.clear()


@dataclass
class Part:
    """One provider call a search needs: a source, a kind, its cache key and its fetch."""

    source: str
    kind: str
    key: str
    fetch: Callable[..., list[dict[str, Any]]]


@dataclass
class RunState:
    """What the runner learned while streaming; read by the caller to build ``done``."""

    deadline_hit: bool = False
    degraded: bool = False


def _worst(states: Sequence[str]) -> str:
    if all(state == "cached" for state in states):
        return "cached"
    for state in _STATE_PRIORITY:
        if state in states:
            return state
    return "done"


class ExternalSearch:
    """Provider side of one search request. Built per request; the registry and limiter are shared."""

    def __init__(
        self,
        *,
        parts_for: Callable[[str, Sequence[str]], list[Part]],
        sources: Mapping[str, dict[str, Any]],
        registry: FetchRegistry,
        cache_read: Callable[[str], Any],
        cache_write: Callable[[str, Any], None],
        clock: Callable[[], float] = time.monotonic,
        deadline_seconds: float = SEARCH_DEADLINE_SECONDS,
    ):
        self._parts_for = parts_for
        self._sources = dict(sources)
        self._registry = registry
        self._cache_read = cache_read
        self._cache_write = cache_write
        self._clock = clock
        self._deadline_seconds = deadline_seconds

    def source_capabilities(self) -> dict[str, dict[str, Any]]:
        return {name: dict(cap) for name, cap in self._sources.items()}

    def _run(self, part: Part, work: SharedFetch) -> None:
        """Worker body for a shared call. Runs on its own thread, never on the request thread."""
        started = self._clock()

        def remaining() -> float:
            return work.deadline_at - self._clock()

        state, records = "done", []
        try:
            records = part.fetch(remaining=remaining, cancelled=work.cancelled)
        except ProviderError as exc:
            state = exc.state
        except Exception:
            state = "failed"
        if self._clock() > work.deadline_at:
            # A late answer is a timeout: the request has already moved on, so it is not cached.
            state, records = "timeout", []
        elif state == "done" and not work.cancelled.is_set():
            write_cached(self._cache_write, part.key, records, time.time())
        self._registry.finish(work, state, records, int((self._clock() - started) * 1000))

    def stream(
        self,
        *,
        query: str,
        types: Sequence[str],
        limit: int,
        owned: OwnedData | None,
        started: float,
        run: RunState,
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``source`` and ``result`` events for the network sources, within the deadline."""
        parts = self._parts_for(query, types)
        if not parts:
            return
        deadline_at = started + self._deadline_seconds
        owned_keys = OwnedKeys(owned)
        emitted: list[dict[str, Any]] = []
        shown: dict[str, int] = {}
        sources: list[str] = []
        for part in parts:
            if part.source not in sources:
                sources.append(part.source)
                yield "source", {"source": part.source, "state": "pending", "count": None, "ms": None}

        inbox: queue.Queue = queue.Queue()
        works: dict[int, SharedFetch] = {}
        ready: list[tuple[int, str, list[dict[str, Any]], int]] = []
        waiting = set(range(len(parts)))
        part_state: dict[int, tuple[str, int, int]] = {}
        t0 = self._clock()

        try:
            for index, part in enumerate(parts):
                hit = read_cached(self._cache_read, part.key, time.time())
                if hit is not None:
                    ready.append((index, "cached", hit, 0))
                    continue
                works[index] = self._registry.join(
                    part.key,
                    deadline_at,
                    lambda work, p=part: threading.Thread(
                        target=self._run, args=(p, work), daemon=True
                    ).start(),
                    inbox,
                    index,
                )

            def complete(index: int, state: str, records: list[dict[str, Any]], ms: int):
                part = parts[index]
                waiting.discard(index)
                part_state[index] = (state, len(records), ms)
                if state in BAD_STATES:
                    run.degraded = True
                for candidate in fresh_candidates(
                    records, query=query, owned=owned_keys, emitted=emitted
                ):
                    if shown.get(candidate["type"], 0) >= limit:
                        continue
                    shown[candidate["type"]] = shown.get(candidate["type"], 0) + 1
                    yield "result", shape_result(candidate)
                if not any(p.source == part.source for i, p in enumerate(parts) if i in waiting):
                    states = [part_state[i][0] for i in part_state if parts[i].source == part.source]
                    counts = [part_state[i][1] for i in part_state if parts[i].source == part.source]
                    times = [part_state[i][2] for i in part_state if parts[i].source == part.source]
                    yield "source", {
                        "source": part.source,
                        "state": _worst(states),
                        "count": sum(counts),
                        "ms": max(times),
                    }

            for index, state, records, ms in ready:
                yield from complete(index, state, records, ms)

            while waiting:
                remaining = deadline_at - self._clock()
                if remaining <= 0:
                    break
                try:
                    index, work = inbox.get(timeout=remaining)
                except queue.Empty:
                    break
                yield from complete(index, work.state, work.records, work.ms)

            if waiting:
                run.deadline_hit = True
                for index in sorted(waiting):
                    yield from complete(index, "timeout", [], int((self._clock() - t0) * 1000))
        finally:
            for work in works.values():
                self._registry.leave(work)
