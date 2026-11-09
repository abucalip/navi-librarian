"""Raw listens for the taste refresh, read from ListenBrainz (owner decision 2026-11-09).

Pages the owner's ListenBrainz history backwards with ``max_ts`` in the largest batches the API allows
(1000 listens per call) until a page comes back empty, so the all-time window is the whole history however
long it is and however large the gaps in it are, and returns the listens in the ListenBrainz shape the loader reads. Read-only: it writes nothing and uses only the ``get`` and ``headers``
the caller injects; the token is never read, logged or returned here. Only aggregate counts are logged.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)
BATCH = 1000          # ListenBrainz MAX_ITEMS_PER_GET: the largest page the API serves
MAX_BATCHES = 5000    # safety stop only: 5 million listens
RETRIES = 3
PAUSE_SECONDS = 0.25


def listenbrainz_reader(
    username: str,
    *,
    get: Callable[..., Any],
    headers: Mapping[str, str],
    clock: Callable[[], float] = time.time,
    pause: Callable[[float], None] = time.sleep,
) -> Callable[[], list[dict[str, Any]]]:
    """A zero-argument reader of the user's full ListenBrainz history; raises when it cannot be read whole."""
    url = f"https://api.listenbrainz.org/1/user/{username}/listens"

    def fetch(max_ts: int) -> list[dict[str, Any]]:
        for attempt in range(RETRIES):
            try:
                response = get(url, params={"count": BATCH, "max_ts": max_ts}, headers=dict(headers), timeout=30)
                response.raise_for_status()
                return response.json().get("payload", {}).get("listens", [])
            except Exception:
                if attempt == RETRIES - 1:
                    raise
                pause(PAUSE_SECONDS * (attempt + 1) * 4)
        return []

    def read() -> list[dict[str, Any]]:
        listens: list[dict[str, Any]] = []
        seen: set[tuple] = set()
        max_ts = int(clock())
        for batches in range(1, MAX_BATCHES + 1):
            page = fetch(max_ts)   # a failed batch raises: a hole would read as a taste change
            if not page:
                break
            for item in page:
                meta = item.get("track_metadata") or {}
                key = (item.get("listened_at"), meta.get("artist_name"), meta.get("track_name"))
                if key not in seen:
                    seen.add(key)
                    listens.append(item)
            oldest = min(int(item.get("listened_at", 0)) for item in page)
            if oldest >= max_ts:   # no progress; avoid looping forever
                break
            max_ts = oldest
            pause(PAUSE_SECONDS)
        else:
            raise RuntimeError("ListenBrainz history exceeded the batch safety limit")
        logger.info("Taste history: %d listens in %d batches", len(listens), batches)
        return listens

    return read
