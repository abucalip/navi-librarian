"""Raw listens for the taste refresh, read from ListenBrainz (owner decision 2026-11-09).

Walks the owner's ListenBrainz history back one year at a time to the 13-year floor of the lens history
(``discovery.history_fetch``), so the all-time window is the whole history, and returns the listens in the
ListenBrainz shape the loader reads. Read-only: it writes nothing and uses only the ``get`` and ``headers``
the caller injects; the token is never read, logged or returned here. Only aggregate counts are logged.
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Mapping

from discovery import history_fetch

logger = logging.getLogger(__name__)
WALK_ALL = 10 ** 9   # never stop early: the all-time window needs the whole history


def listenbrainz_reader(
    username: str,
    *,
    get: Callable[..., Any],
    headers: Mapping[str, str],
    clock: Callable[[], float] = time.time,
    pause: Callable[[float], None] = time.sleep,
) -> Callable[[], list[dict[str, Any]]]:
    """A zero-argument reader of the user's full ListenBrainz history; raises when no window answers."""
    source = functools.partial(history_fetch.listenbrainz_window, username, get=get, headers=headers, pause=pause)

    def read() -> list[dict[str, Any]]:
        result = history_fetch.fetch_lens_history([("listenbrainz", source)], now=clock(), min_usable=WALK_ALL)
        windows = result["windows"]
        logger.info("Taste history: %d listens in %d windows (%d unanswered)",
                    len(result["listens"]), len(windows), result["unanswered"])
        if windows and result["unanswered"] == len(windows):
            raise RuntimeError("ListenBrainz answered no window")
        if result["unanswered"]:
            # A hole in the history would read as a taste change; fail so the saved profiles stay as they were.
            raise RuntimeError(f"ListenBrainz left {result['unanswered']} window(s) unanswered")
        return result["listens"]

    return read
