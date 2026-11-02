"""Resync the app's library copy from Navidrome shortly after an import.

Navidrome notices a new album within seconds, but the Librarian keeps its own library snapshot
for ten minutes, so a freshly imported album can be missing from the app for that long. After an
import this waits a short time for Navidrome to finish scanning, drops the cached snapshot and
rebuilds the owned index. Imports that finish close together share one resync.

All services are injected, so importing this module does no network or database work.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

# Navidrome waits 5 seconds after the last file change before it scans (Scanner.WatcherWait).
# Twice that leaves room for the scan itself.
SETTLE_SECONDS = 10.0


class LibraryResync:
    def __init__(
        self,
        *,
        enabled: Callable[[], bool],
        resync: Callable[[], None],
        delay: float = SETTLE_SECONDS,
        timer_factory: Callable[..., Any] = threading.Timer,
    ) -> None:
        self._enabled = enabled
        self._resync = resync
        self._delay = delay
        self._timer_factory = timer_factory
        self._lock = threading.Lock()
        self._pending = False

    def on_imported(self, artist: str, album: str) -> None:
        """Schedule one resync unless the option is off or one is already waiting."""
        try:
            if not self._enabled():
                return
        except Exception:
            return
        with self._lock:
            if self._pending:
                return
            self._pending = True
        timer = self._timer_factory(self._delay, self._run)
        timer.daemon = True
        timer.start()

    def _run(self) -> None:
        # Clear the flag first so an import that lands during the resync schedules another one.
        with self._lock:
            self._pending = False
        try:
            self._resync()
        except Exception:
            # The next TTL expiry rebuilds the snapshot anyway.
            pass
