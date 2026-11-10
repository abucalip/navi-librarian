"""Turn one client's stream connection into logged plays: only songs heard long enough count.

A song is logged as soon as it has been heard for MIN_LISTEN_SECONDS, so the live "now" holder can
hand the client a play id while the song is still on. The rest of the listen is added when the
song changes or the connection closes.
"""
from __future__ import annotations

import time
from typing import Callable

from integrations.radio.icy import split_artist_title

MIN_LISTEN_SECONDS = 30
# How often a connection re-reports to the holder while nothing changes, so it does not go stale.
HEARTBEAT_SECONDS = 5.0


class ListenTracker:
    """Follows the song title of one connection and records each song the listener stayed on."""

    def __init__(
        self, store, station_id: str, station_name: str, *,
        clock: Callable[[], float] = time.time, min_seconds: int = MIN_LISTEN_SECONDS,
        holder=None, has_metadata: bool = True, on_logged: Callable[[int], None] | None = None,
    ):
        self.store = store
        self.station_id = station_id
        self.station_name = station_name
        self.clock = clock
        self.min_seconds = min_seconds
        self.holder = holder
        self.has_metadata = has_metadata
        # Told each play id when a song is logged (at the threshold, or at the end of a short-enough
        # listen). It may be told the same id again after a reconnect; the caller must be idempotent.
        self.on_logged = on_logged
        self._raw: str | None = None
        self._since = 0.0
        self._play_id: int | None = None
        self._logged_seconds = 0
        self._published_at = float("-inf")
        self._publish()

    def set_title(self, raw: str | None) -> None:
        raw = (raw or "").strip()
        if raw == (self._raw or ""):
            return
        self._finish()
        if raw and raw.casefold() != self.station_name.casefold():
            self._raw, self._since = raw, self.clock()
        self._publish()

    def tick(self) -> None:
        """Called for every chunk relayed: logs the current song once it passes the threshold."""
        if self.holder is None:
            return
        if self._raw is not None and self._play_id is None:
            elapsed = int(self.clock() - self._since)
            if elapsed >= self.min_seconds:
                self._play_id = self._record(self._raw, elapsed)
                self._logged_seconds = elapsed
                self._publish()
                return
        if self.holder.clock() - self._published_at >= HEARTBEAT_SECONDS:
            self._publish()

    def close(self) -> None:
        self._finish()
        if self.holder is not None:
            self.holder.withdraw(self.station_id, self)

    def _finish(self) -> None:
        raw, self._raw = self._raw, None
        if raw is None:
            return
        seconds = int(self.clock() - self._since)
        if self._play_id is not None:
            extra = seconds - self._logged_seconds
            if extra > 0:
                self.store.add_listened(self._play_id, extra, now=self.clock())
        elif seconds >= self.min_seconds:
            self._record(raw, seconds)
        self._play_id, self._logged_seconds = None, 0

    def _record(self, raw: str, seconds: int) -> int:
        artist, title = split_artist_title(raw)
        play_id = self.store.record_play(
            self.station_id, self.station_name, raw, artist, title, seconds, now=self.clock())
        if self.on_logged is not None:
            try:
                self.on_logged(play_id)
            except Exception:  # a follow-up (scrobbling) must never stop the audio relay
                pass
        return play_id

    def _publish(self) -> None:
        if self.holder is None:
            return
        self.holder.publish(self.station_id, self, {
            "has_metadata": self.has_metadata, "raw": self._raw, "play_id": self._play_id,
        })
        self._published_at = self.holder.clock()
