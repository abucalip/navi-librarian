"""Turn one client's stream connection into logged plays: only songs heard long enough count."""
from __future__ import annotations

import time
from typing import Callable

from integrations.radio.icy import split_artist_title

MIN_LISTEN_SECONDS = 30


class ListenTracker:
    """Follows the song title of one connection and records each song the listener stayed on."""

    def __init__(
        self, store, station_id: str, station_name: str, *,
        clock: Callable[[], float] = time.time, min_seconds: int = MIN_LISTEN_SECONDS,
    ):
        self.store = store
        self.station_id = station_id
        self.station_name = station_name
        self.clock = clock
        self.min_seconds = min_seconds
        self._raw: str | None = None
        self._since = 0.0

    def set_title(self, raw: str | None) -> None:
        raw = (raw or "").strip()
        if raw == (self._raw or ""):
            return
        self._finish()
        if raw and raw.casefold() != self.station_name.casefold():
            self._raw, self._since = raw, self.clock()

    def close(self) -> None:
        self._finish()

    def _finish(self) -> None:
        raw, self._raw = self._raw, None
        if raw is None:
            return
        seconds = int(self.clock() - self._since)
        if seconds < self.min_seconds:
            return
        artist, title = split_artist_title(raw)
        self.store.record_play(self.station_id, self.station_name, raw, artist, title, seconds,
                               now=self.clock())
