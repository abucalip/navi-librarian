"""Short-lived marks in the metadata store for "asked recently, nothing usable came back" (efficiency K4, K5).

A mark lives under its own key, never under the key of a real answer, so a mark can never be read back as an
answer or overwrite a stale one that is still being served. Its value is ``{"negative": True, "at": <time>}``:
truthy, so a store miss (None) is never mistaken for a mark, and dated, so freshness is checked here and does
not depend on how a store applies its TTL.

Callers check a mark before asking and write one only after a real answer (or, for K4, a real failure), so a
live mark never renews itself: once it is older than its TTL the provider is asked again.
"""
import time


def mark(write, key) -> None:
    """Write a mark under `key` now, through ``write(key, value)``."""
    write(key, {"negative": True, "at": time.time()})


def is_live(read, key, ttl_seconds) -> bool:
    """Whether ``read(key, ttl)`` returns a mark younger than `ttl_seconds`."""
    stored = read(key, ttl_seconds)
    if not isinstance(stored, dict) or not stored.get("negative"):
        return False
    try:
        return time.time() - float(stored.get("at") or 0) < ttl_seconds
    except (TypeError, ValueError):
        return False
