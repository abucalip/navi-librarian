"""Persistent cache for provider search results (contract sections 5.2 and 6).

One entry holds the complete result set of one source for one kind at fixed depth 50.
``scope`` and ``limit`` are applied per request after the read. Only complete results are
written: failures, timeouts and cancelled work never reach this module.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

DEPTH = 50
POSITIVE_TTL_SECONDS = 24 * 60 * 60
NEGATIVE_TTL_SECONDS = 60 * 60
SIMILAR_TTL_SECONDS = 7 * 24 * 60 * 60


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
    return delete_except(f"search:{source}:", f"search:{source}:{generation}:")


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
