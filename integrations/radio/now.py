"""The live "now" holder: the current song of each relayed station, held in memory.

The relay feeds it (``ListenTracker``); the ``/now`` routes read it. Nothing here calls a provider or
opens an upstream connection, so reading a station's title costs no network traffic.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from integrations.radio.icy import split_artist_title

# A connection that has not reported for this long is treated as gone (for example a client that
# was switched off before its stream body ever started, so nothing ever withdrew it).
STALE_SECONDS = 20.0
# An unreachable mark is shown for this long, then the station goes back to idle.
UNREACHABLE_SECONDS = 20.0

STATES = ("ok", "no_metadata", "unparsed", "not_proxied", "unavailable", "idle")


class NowHolder:
    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 stale_seconds: float = STALE_SECONDS):
        self.clock = clock
        self.stale_seconds = stale_seconds
        self._lock = threading.Lock()
        self._connections: dict[str, dict[object, dict]] = {}
        self._unreachable: dict[str, float] = {}
        self._library: dict[str, tuple[str, dict]] = {}

    def publish(self, station_id: str, key: object, snapshot: dict) -> None:
        """Record what one listener's connection currently hears. ``snapshot`` holds has_metadata,
        raw (the current title or None) and play_id (the logged play, or None)."""
        with self._lock:
            entry = dict(snapshot, updated=self.clock())
            self._connections.setdefault(station_id, {})[key] = entry

    def withdraw(self, station_id: str, key: object) -> None:
        with self._lock:
            connections = self._connections.get(station_id, {})
            connections.pop(key, None)
            if not connections:
                self._connections.pop(station_id, None)

    def mark_unreachable(self, station_id: str) -> None:
        with self._lock:
            self._unreachable[station_id] = self.clock()

    def unreachable(self, station_id: str) -> bool:
        with self._lock:
            when = self._unreachable.get(station_id)
            return when is not None and self.clock() - when <= UNREACHABLE_SECONDS

    def live(self, station_id: str) -> dict | None:
        """The most recently reporting fresh connection of a station, or None when nobody listens."""
        with self._lock:
            connections = self._connections.get(station_id, {})
            now = self.clock()
            fresh = [entry for entry in connections.values() if now - entry["updated"] <= self.stale_seconds]
            return dict(max(fresh, key=lambda entry: entry["updated"])) if fresh else None

    def library(self, station_id: str, raw: str) -> dict | None:
        """The library lookup already made for this exact title, so each song is looked up once."""
        with self._lock:
            cached = self._library.get(station_id)
        return dict(cached[1]) if cached and cached[0] == raw else None

    def remember_library(self, station_id: str, raw: str, result: dict) -> None:
        with self._lock:
            self._library[station_id] = (raw, dict(result))


NOW = NowHolder()


def view(snapshot: dict | None, lookup: Callable[[str, str, str], dict | None] | None = None, *,
         proxied: bool = True, unreachable: bool = False) -> dict:
    """The contract shape of ``GET /api/radio/stations/{id}/now`` for one station.

    ``lookup(raw, artist, title)`` gives ``{"in_library", "cover_url"}`` for a parsed song, or None
    when the library could not be asked. Only a song in state ``ok`` is looked up.
    """
    result = {"state": "idle", "raw_title": None, "artist": None, "title": None,
              "play_id": None, "in_library": False, "cover_url": None}
    if not proxied:
        return {**result, "state": "not_proxied"}
    if snapshot is None:
        return {**result, "state": "unavailable" if unreachable else "idle"}
    raw = snapshot.get("raw")
    result["play_id"] = snapshot.get("play_id")
    if not snapshot.get("has_metadata") or not raw:
        return {**result, "state": "no_metadata", "play_id": None}
    result["raw_title"] = raw
    artist, title = split_artist_title(raw)
    if artist is None:
        return {**result, "state": "unparsed"}
    found = (lookup(raw, artist, title) if lookup else None) or {}
    return {**result, "state": "ok", "artist": artist, "title": title,
            "in_library": bool(found.get("in_library")), "cover_url": found.get("cover_url")}
