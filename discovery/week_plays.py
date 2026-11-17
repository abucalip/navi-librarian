"""Plays per album over the last seven days, from the owner's ListenBrainz listens (Index theme I0-1).

The owner chose a real windowed count for the Home "Played" rows ("14 plays" this week). Navidrome keeps
only an all-time ``playCount``, so the week comes from listen timestamps. One ListenBrainz window read
(``history_fetch.listenbrainz_window``, its own paging and pacing) is cached for ``CACHE_SECONDS``, so Home
loads cost at most one read per cache period. When the read fails or no username is set, nothing is
attached: a client hides the count rather than showing a made-up 0.

Pure apart from the injected window reader and clock; no listen, artist or album is logged.
"""
from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from recommendation.music_key import music_key

WINDOW_DAYS = 7
CACHE_SECONDS = 600
WindowReader = Callable[[int, int], list[dict[str, Any]]]


def album_counts(listens: Sequence[Mapping[str, Any]]) -> Counter:
    """Listens per (artist key, album key); a listen without both names is not counted."""
    counts: Counter = Counter()
    for listen in listens:
        meta = listen.get("track_metadata") if isinstance(listen.get("track_metadata"), Mapping) else {}
        artist, album = music_key(meta.get("artist_name")), music_key(meta.get("release_name"))
        if artist and album:
            counts[(artist, album)] += 1
    return counts


class WeekPlays:
    """Cached weekly album counts; ``counts`` returns None when the history could not be read."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._cached: tuple[float, Counter] | None = None

    def counts(self, reader: WindowReader | None) -> Counter | None:
        if reader is None:
            return None
        with self._lock:
            now = self._clock()
            if self._cached and now - self._cached[0] < CACHE_SECONDS:
                return self._cached[1]
            try:
                listens = reader(int(now) - WINDOW_DAYS * 86400, int(now))
            except Exception:
                return self._cached[1] if self._cached else None  # a stale count beats none
            counts = album_counts(listens)
            self._cached = (now, counts)
            return counts


def attach(items: list[dict[str, Any]], counts: Counter | None) -> list[dict[str, Any]]:
    """Add ``play_count`` and ``window: "week"`` to each shelf item; unchanged when counts are unknown."""
    if counts is None:
        return items
    return [
        {**item, "play_count": counts.get((music_key(item.get("artist")), music_key(item.get("name"))), 0), "window": "week"}
        for item in items
    ]
