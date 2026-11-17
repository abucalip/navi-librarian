"""A bounded in-memory cache with single-flight, in front of the persistent metadata store.

Efficiency P4 (finding F8). Each metadata route used to keep its own unbounded dict and repeat the
same lookup by hand: memory, then `persistent_metadata`, then the provider. `LayeredCache` is that
lookup once:

1. memory: a least-recently-used map of at most `max_entries` entries, each with its own expiry;
2. the persistent store, when the caller gives a `store_key` and the stored value passes `accept_stored`;
3. the caller's `load()`, run by one caller at a time per key. Callers that arrive while it runs wait
   for it and get the same answer, or the same exception, so concurrent identical requests make one
   provider call.

`load()` decides what happens to its answer with a `Loaded`: how long memory keeps it (`None`: not at
all, as for a provider failure) and whether it is written to the store. Nothing here changes a
caller's TTLs or keys.

Stale-while-revalidate (efficiency K2) is opt-in per call with `max_stale`: a stored value past
`store_ttl` but no older than `max_stale` is returned at once, kept in memory for at most
`STALE_MEMORY_TTL`, and one background refresh runs `refresh()` (default `load`) through
`stale_refresh`. Its answer replaces the value under the same `Loaded` rules; a failure leaves the
stale value. Past `max_stale` the value is missing and `load()` runs as before. Without `max_stale`,
or when the store cannot report ages, expiry is unchanged. With `stale_fetched_at` as well, a stale
dict answer is a copy carrying `fetched_at` (UTC, ISO 8601), when the store last wrote it; a fresh
answer and the stored value never carry it.
"""
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic

from app.services import persistent_metadata, stale_refresh

DEFAULT_MAX_ENTRIES = 2000
# A waiter stops waiting for a stuck loader after this long and asks on its own. Every metadata
# loader has its own HTTP timeouts, well under this.
DEFAULT_WAIT_SECONDS = 30.0
# A stale value is kept in memory this long at most, so a failed refresh is retried after it, not on
# every request.
STALE_MEMORY_TTL = 10 * 60
_MISSING = object()
FETCHED_AT = "fetched_at"


def iso_utc(epoch_seconds):
    """`epoch_seconds` as the contracts' UTC timestamp, for example ``2026-10-25T16:00:00Z``."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_seconds))


def with_fetched_at(value, epoch_seconds):
    """A shallow copy of a dict `value` with `fetched_at` added; any other value unchanged."""
    if not isinstance(value, dict):
        return value
    return {**value, FETCHED_AT: iso_utc(epoch_seconds)}


@dataclass(frozen=True)
class Loaded:
    """A loader's answer: the value, how long memory keeps it (None: not kept), and whether to store it."""

    value: object
    memory_ttl: float | None = None
    persist: bool = False


class _Flight:
    def __init__(self):
        self.done = threading.Event()
        self.value = None
        self.error = None


class LayeredCache:
    """One namespace of cached metadata answers. Safe to share across threads."""

    def __init__(self, namespace, *, max_entries=DEFAULT_MAX_ENTRIES, wait_seconds=DEFAULT_WAIT_SECONDS,
                 refresher=None):
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.namespace = namespace
        self.max_entries = max_entries
        self.wait_seconds = wait_seconds
        self._refresher = refresher
        self._entries = OrderedDict()  # key -> (expires_at, value, stale)
        self._flights = {}
        self._lock = threading.Lock()

    def _lookup(self, key, allow_stale=True):
        """``(value, stale)`` for `key`, or _MISSING. A stale entry counts only with `allow_stale`. Caller holds the lock."""
        entry = self._entries.get(key)
        if entry is None:
            return _MISSING
        if monotonic() >= entry[0]:
            del self._entries[key]
            return _MISSING
        if entry[2] and not allow_stale:
            return _MISSING
        self._entries.move_to_end(key)
        return entry[1], entry[2]

    def peek(self, key, default=None):
        """The value memory holds for `key`, or `default`. Never reads the store or loads."""
        with self._lock:
            found = self._lookup(key)
        return default if found is _MISSING else found[0]

    def put(self, key, value, ttl, *, stale=False):
        """Keep `value` in memory for `ttl` seconds, evicting the least recently used beyond the bound."""
        with self._lock:
            self._entries[key] = (monotonic() + ttl, value, stale)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self):
        with self._lock:
            self._entries.clear()

    def __len__(self):
        with self._lock:
            return len(self._entries)

    def __contains__(self, key):
        return self.peek(key, _MISSING) is not _MISSING

    def get_or_load(self, key, load, **options):
        """Memory, then the store (when `store_key` is given), then `load()` under single-flight.

        See `get_or_load_state` for the options; this returns the value only.
        """
        return self.get_or_load_state(key, load, **options)[0]

    def get_or_load_state(self, key, load, *, store_key=None, store_ttl=persistent_metadata.FOUND_TTL,
                          accept_stored=bool, stored_ttl=None, max_stale=None, refresh=None,
                          stale_fetched_at=False):
        """``(value, stale)``: memory, then the store, then `load()` under single-flight.

        A stored value that `accept_stored` approves is kept in memory for `stored_ttl` seconds and
        returned. `load()` returns a `Loaded`; its exceptions reach every caller waiting on it and
        nothing is cached for them. With `max_stale`, a stored value older than `store_ttl` is returned
        with ``stale`` True and refreshed in the background (see the module docstring); with
        `stale_fetched_at`, that answer is a copy stating when it was fetched.
        """
        allow_stale = max_stale is not None
        flight_key = (key, allow_stale)
        with self._lock:
            found = self._lookup(key, allow_stale)
            if found is not _MISSING:
                return found
            flight = self._flights.get(flight_key)
            leader = flight is None
            if leader:
                flight = self._flights[flight_key] = _Flight()
        resolve = (key, load, store_key, store_ttl, accept_stored, stored_ttl, max_stale, refresh, stale_fetched_at)
        if not leader:
            if flight.done.wait(self.wait_seconds):
                if flight.error is not None:
                    raise flight.error
                return flight.value
            # The loader is stuck past every provider timeout; do not wait on it any longer.
            return self._resolve(*resolve)
        try:
            flight.value = self._resolve(*resolve)
            return flight.value
        except BaseException as error:
            flight.error = error
            raise
        finally:
            with self._lock:
                if self._flights.get(flight_key) is flight:
                    del self._flights[flight_key]
            flight.done.set()

    def _resolve(self, key, load, store_key, store_ttl, accept_stored, stored_ttl, max_stale, refresh,
                 stale_fetched_at=False):
        if store_key is not None:
            if max_stale is not None and persistent_metadata.can_read_age():
                found = persistent_metadata.read_with_age(store_key, max(max_stale, store_ttl))
                if found is not None and accept_stored(found[0]):
                    stored, age = found
                    if age <= store_ttl:
                        self.put(key, stored, stored_ttl)
                        return stored, False
                    memory_ttl = STALE_MEMORY_TTL if stored_ttl is None else min(stored_ttl, STALE_MEMORY_TTL)
                    if stale_fetched_at:
                        # A copy: the stored value and a later fresh answer never carry the field.
                        stored = with_fetched_at(stored, time.time() - age)
                    self.put(key, stored, memory_ttl, stale=True)
                    self._schedule_refresh(key, refresh or load, store_key)
                    return stored, True
            else:
                stored = persistent_metadata.read(store_key, store_ttl)
                if accept_stored(stored):
                    self.put(key, stored, stored_ttl)
                    return stored, False
        return self._apply(key, load(), store_key), False

    def _apply(self, key, loaded, store_key):
        if loaded.memory_ttl is not None:
            self.put(key, loaded.value, loaded.memory_ttl)
        if loaded.persist and store_key is not None:
            persistent_metadata.write(store_key, loaded.value)
        return loaded.value

    def _schedule_refresh(self, key, refresh, store_key):
        def run():
            # A failure raises inside the refresher and leaves the stale entry as it is.
            self._apply(key, refresh(), store_key)

        refresher = self._refresher or stale_refresh.REFRESHER
        refresher.submit((self.namespace, store_key), run)
