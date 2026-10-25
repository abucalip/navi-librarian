"""Per-source call spacing for external search (contract section 5.1).

Each source reserves its next call slot here. A call that would have to wait past the
remaining request deadline is refused rather than queued, so the caller reports the
source as ``rate_limited`` and moves on.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping


class SourceLimiter:
    """Space calls to each source by a fixed interval, shared by every request in the process."""

    def __init__(
        self,
        intervals: Mapping[str, float],
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._intervals = dict(intervals)
        self._clock = clock
        self._sleep = sleep
        self._next_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def admit(self, source: str, remaining: float) -> bool:
        """Reserve the next slot for ``source``; return False if the wait exceeds ``remaining``.

        The reservation is made under the lock and the wait happens outside it, so one slow
        caller does not hold up the reservations of other sources.
        """
        interval = self._intervals.get(source, 0.0)
        with self._lock:
            now = self._clock()
            start = max(now, self._next_at.get(source, now))
            wait = start - now
            if wait > remaining:
                return False
            self._next_at[source] = start + interval
        if wait > 0:
            self._sleep(wait)
        return True
