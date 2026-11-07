"""Small in-memory TTL cache for sonic routes (Server V2 Phase 7, slice 2).

Only answers that will not change soon are kept: status ``ok`` and ``empty``. Errors (``not_found``,
``unavailable``) and refused requests are never stored, so a sonic plugin that recovers is used on the next call.

The clock is a parameter so tests can move time forward without sleeping. Entries expire after ``ttl``
seconds and the cache holds at most ``max_entries``; the least recently used entry is dropped first.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Callable, Hashable

TTL_SECONDS = 3600
MAX_ENTRIES = 256
CACHEABLE_STATUSES = ("ok", "empty")


class TTLCache:
    def __init__(self, *, ttl: float = TTL_SECONDS, max_entries: int = MAX_ENTRIES,
                 clock: Callable[[], float] = time.monotonic):
        if ttl <= 0 or max_entries < 1:
            raise ValueError("ttl must be positive and max_entries at least 1")
        self._ttl, self._max, self._clock = ttl, max_entries, clock
        self._items: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._items)

    def get(self, key: Hashable) -> Any | None:
        """The stored value, or ``None`` when the key is missing or expired (expired entries are removed)."""
        entry = self._items.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if self._clock() - stored_at >= self._ttl:
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return value

    def offer(self, key: Hashable, status: str, value: Any) -> bool:
        """Store ``value`` only when ``status`` is cacheable. Returns whether it was stored."""
        if status not in CACHEABLE_STATUSES:
            return False
        self._items[key] = (self._clock(), value)
        self._items.move_to_end(key)
        while len(self._items) > self._max:
            self._items.popitem(last=False)
        return True
