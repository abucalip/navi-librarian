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
caller's TTLs or keys. There is no stale-while-revalidate (that is K2).
"""
import threading
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic

from app.services import persistent_metadata

DEFAULT_MAX_ENTRIES = 2000
# A waiter stops waiting for a stuck loader after this long and asks on its own. Every metadata
# loader has its own HTTP timeouts, well under this.
DEFAULT_WAIT_SECONDS = 30.0
_MISSING = object()


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

    def __init__(self, namespace, *, max_entries=DEFAULT_MAX_ENTRIES, wait_seconds=DEFAULT_WAIT_SECONDS):
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.namespace = namespace
        self.max_entries = max_entries
        self.wait_seconds = wait_seconds
        self._entries = OrderedDict()  # key -> (expires_at, value)
        self._flights = {}
        self._lock = threading.Lock()

    def _lookup(self, key):
        """The live value for `key`, or _MISSING. Caller holds the lock."""
        entry = self._entries.get(key)
        if entry is None:
            return _MISSING
        if monotonic() >= entry[0]:
            del self._entries[key]
            return _MISSING
        self._entries.move_to_end(key)
        return entry[1]

    def peek(self, key, default=None):
        """The value memory holds for `key`, or `default`. Never reads the store or loads."""
        with self._lock:
            value = self._lookup(key)
        return default if value is _MISSING else value

    def put(self, key, value, ttl):
        """Keep `value` in memory for `ttl` seconds, evicting the least recently used beyond the bound."""
        with self._lock:
            self._entries[key] = (monotonic() + ttl, value)
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

    def get_or_load(self, key, load, *, store_key=None, store_ttl=persistent_metadata.FOUND_TTL,
                    accept_stored=bool, stored_ttl=None):
        """Memory, then the store (when `store_key` is given), then `load()` under single-flight.

        A stored value that `accept_stored` approves is kept in memory for `stored_ttl` seconds and
        returned. `load()` returns a `Loaded`; its exceptions reach every caller waiting on it and
        nothing is cached for them.
        """
        with self._lock:
            value = self._lookup(key)
            if value is not _MISSING:
                return value
            flight = self._flights.get(key)
            leader = flight is None
            if leader:
                flight = self._flights[key] = _Flight()
        if not leader:
            if flight.done.wait(self.wait_seconds):
                if flight.error is not None:
                    raise flight.error
                return flight.value
            # The loader is stuck past every provider timeout; do not wait on it any longer.
            return self._resolve(key, load, store_key, store_ttl, accept_stored, stored_ttl)
        try:
            flight.value = self._resolve(key, load, store_key, store_ttl, accept_stored, stored_ttl)
            return flight.value
        except BaseException as error:
            flight.error = error
            raise
        finally:
            with self._lock:
                if self._flights.get(key) is flight:
                    del self._flights[key]
            flight.done.set()

    def _resolve(self, key, load, store_key, store_ttl, accept_stored, stored_ttl):
        if store_key is not None:
            stored = persistent_metadata.read(store_key, store_ttl)
            if accept_stored(stored):
                self.put(key, stored, stored_ttl)
                return stored
        loaded = load()
        if loaded.memory_ttl is not None:
            self.put(key, loaded.value, loaded.memory_ttl)
        if loaded.persist and store_key is not None:
            persistent_metadata.write(store_key, loaded.value)
        return loaded.value
