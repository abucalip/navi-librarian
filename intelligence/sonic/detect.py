"""Is the sonic extension served? (Server V2 Phase 7, slice 3.)

Reads Navidrome's ``getOpenSubsonicExtensions`` through the injected ``api_call`` and looks for
``sonicSimilarity``. Any failure means "not available": the capabilities route must never fail because
Navidrome is slow or down. The answer is kept briefly so polling clients do not hit Navidrome each time.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

EXTENSION = "sonicSimilarity"
TTL_SECONDS = 300.0


def sonic_extension_listed(root: dict[str, Any] | None) -> bool:
    """True when the extensions answer lists ``sonicSimilarity``."""
    items = (root or {}).get("openSubsonicExtensions") or []
    if isinstance(items, dict):
        items = [items]
    return any(isinstance(e, dict) and e.get("name") == EXTENSION for e in items)


class SonicDetector:
    """Caches the yes/no answer for ``ttl`` seconds (failures are cached too, so a down Navidrome is not hammered)."""

    def __init__(self, ttl: float = TTL_SECONDS, clock: Callable[[], float] = time.monotonic):
        self._ttl, self._clock = ttl, clock
        self._lock = threading.Lock()
        self._value: bool | None = None
        self._at = 0.0

    def available(self, api_call: Callable[..., dict]) -> bool:
        with self._lock:
            if self._value is not None and self._clock() - self._at < self._ttl:
                return self._value
        try:
            value = sonic_extension_listed(api_call("getOpenSubsonicExtensions"))
        except Exception:
            value = False
        with self._lock:
            self._value, self._at = value, self._clock()
        return value
