"""Persistent cache for provider search results (contract sections 5.2 and 6).

One entry holds the complete result set of one source for one kind at fixed depth 50.
``scope`` and ``limit`` are applied per request after the read. Only complete results are
written: failures, timeouts and cancelled work never reach this module.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

DEPTH = 50
POSITIVE_TTL_SECONDS = 24 * 60 * 60
NEGATIVE_TTL_SECONDS = 60 * 60
SIMILAR_TTL_SECONDS = 7 * 24 * 60 * 60


def genre_cache_key(source: str, generation: int, tag: str, kind: str) -> str:
    """Genre-page entry (section 5.2): one source's records for one tag and kind. Holds no credential."""
    return f"genre:{source}:{generation}:{tag}:{kind}"


def provider_cache_key(source: str, generation: int, query: str, kind: str) -> str:
    """Key shape from section 5.2. Holds no credential, only the source's generation counter."""
    return f"search:{source}:{generation}:{query}:{kind}:depth{DEPTH}"


def purge_stale_generations(
    delete_except: Callable[[str, str], int],
    source: str,
    generation: int,
) -> int:
    """Delete every cached entry for ``source`` whose generation is not ``generation``.

    Old-generation entries are already unreachable (section 5.2); this only reclaims their
    storage. ``delete_except(prefix, keep_prefix)`` is the store's prefix delete.
    """
    removed = delete_except(f"search:{source}:", f"search:{source}:{generation}:")
    return removed + delete_except(f"genre:{source}:", f"genre:{source}:{generation}:")


def read_cached(
    read: Callable[[str], Any],
    key: str,
    now: float,
    positive_ttl: int = POSITIVE_TTL_SECONDS,
) -> list[dict[str, Any]] | None:
    """Return the cached records for ``key``, or None when missing or expired.

    A definitive empty answer is cached for an hour; a non-empty one for ``positive_ttl``
    (24 hours for search results, 7 days for similar artists).
    """
    entry = read(key)
    if not isinstance(entry, dict):
        return None
    records = entry.get("results")
    at = entry.get("at")
    if not isinstance(records, list) or not isinstance(at, (int, float)):
        return None
    ttl = positive_ttl if records else NEGATIVE_TTL_SECONDS
    if now - at > ttl:
        return None
    return records


def write_cached(
    write: Callable[[str, Any], None],
    key: str,
    records: list[dict[str, Any]],
    now: float,
) -> None:
    write(key, {"at": now, "results": records})


# Stale-while-revalidate for the artist and album pages' provider rows (efficiency K2 part 2).
# An entry past its TTL but under STALE_FACTOR times that TTL is served while one background
# refresh asks the provider again; past that it is a miss, as before.
STALE_FACTOR = 10
REFRESH_DEADLINE_SECONDS = 20.0
REFRESH_KEY_PREFIX = "discovery:"


def read_cached_state(
    read: Callable[[str], Any],
    key: str,
    now: float,
    positive_ttl: int = POSITIVE_TTL_SECONDS,
) -> tuple[list[dict[str, Any]] | None, bool]:
    """``(records, stale)``: like ``read_cached``, but an entry past its TTL and under
    ``STALE_FACTOR`` times it comes back with ``stale=True``. Older, missing or malformed
    entries are ``(None, False)``. The TTL is the one ``read_cached`` applies (one hour for an
    empty answer)."""
    entry = read(key)
    if not isinstance(entry, dict):
        return None, False
    records = entry.get("results")
    at = entry.get("at")
    if not isinstance(records, list) or not isinstance(at, (int, float)):
        return None, False
    ttl = positive_ttl if records else NEGATIVE_TTL_SECONDS
    age = now - at
    if age <= ttl:
        return records, False
    if age <= ttl * STALE_FACTOR:
        return records, True
    return None, False


def refresh_budget(
    clock: Callable[[], float] = time.monotonic,
    seconds: float = REFRESH_DEADLINE_SECONDS,
) -> tuple[Callable[[], float], threading.Event]:
    """A fresh ``(remaining, cancelled)`` pair for one background refresh. The request's own pair
    is spent or set by the time the refresh runs, and would block its write."""
    deadline = clock() + seconds
    return (lambda: max(0.0, deadline - clock())), threading.Event()


def read_or_revalidate(
    read: Callable[[str], Any],
    key: str,
    *,
    submit: Callable[[str, Callable[[], None]], bool] | None,
    refetch: Callable[[Callable[[], float], threading.Event], Any],
    positive_ttl: int = POSITIVE_TTL_SECONDS,
    now: float | None = None,
) -> list[dict[str, Any]] | None:
    """Fresh records, or stale ones with one refresh handed to ``submit``, or None for a miss.

    ``refetch(remaining, cancelled)`` is the caller's own fetch-and-store, so the refresh keeps
    the caller's write rules (nothing is written when it fails). Without ``submit`` an expired
    entry is a miss, as before. A refresh ``submit`` refuses (already pending, queue full) still
    serves the stale records.
    """
    at = time.time() if now is None else now
    if submit is None:
        return read_cached(read, key, at, positive_ttl=positive_ttl)
    records, stale = read_cached_state(read, key, at, positive_ttl=positive_ttl)
    if records is not None and stale:
        submit(REFRESH_KEY_PREFIX + key, lambda: refetch(*refresh_budget()))
    return records
