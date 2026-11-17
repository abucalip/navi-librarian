"""Bounded background refreshes for stale-while-revalidate (efficiency K2).

When a cached metadata answer is past its TTL but inside its namespace's maximum staleness, the
request is answered with it at once and one refresh is handed to `submit`. Each refresh runs the
same provider lookup the request would have made, so provider traffic does not rise: it moves off
the request path.

- One refresh per key at a time: a second `submit` for a key already queued or running is ignored.
- The queue is bounded: past `max_pending` keys (queued plus running) a refresh is dropped, and the
  stale value keeps being served until a later request finds room.
- A refresh that raises is swallowed: the stale value stays and nothing is written.

The pool is separate from the review-outlet pool, so a backlog of refreshes cannot delay a
foreground lookup.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

DEFAULT_WORKERS = 2
DEFAULT_MAX_PENDING = 32


class BackgroundRefresher:
    """Runs refreshes on a small pool, one per key, dropping them when the queue is full."""

    def __init__(self, *, workers=DEFAULT_WORKERS, max_pending=DEFAULT_MAX_PENDING, executor=None):
        if max_pending < 1:
            raise ValueError("max_pending must be at least 1")
        self.workers = workers
        self.max_pending = max_pending
        self._executor = executor
        self._keys = set()
        self._lock = threading.Lock()
        self.submitted = 0
        self.dropped = 0
        self.failed = 0

    def _pool(self):
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="stale-refresh")
            return self._executor

    def submit(self, key, refresh):
        """Run `refresh()` in the background unless `key` is already pending or the queue is full.

        Returns True when the refresh was queued.
        """
        with self._lock:
            if key in self._keys:
                return False
            if len(self._keys) >= self.max_pending:
                self.dropped += 1
                return False
            self._keys.add(key)
            self.submitted += 1
        try:
            self._pool().submit(self._run, key, refresh)
        except RuntimeError:  # the pool is shutting down
            with self._lock:
                self._keys.discard(key)
                self.dropped += 1
            return False
        return True

    def _run(self, key, refresh):
        try:
            refresh()
        except Exception:
            with self._lock:
                self.failed += 1
        finally:
            with self._lock:
                self._keys.discard(key)

    def pending(self):
        with self._lock:
            return len(self._keys)


REFRESHER = BackgroundRefresher()
