"""Navidrome artist/album inventory snapshot assembly."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

RECHECK_SECONDS = 30.0
MAX_AGE_SECONDS = 5 * 60.0


class AlbumInventoryLimitError(RuntimeError):
    """Raised when a complete album inventory cannot fit within the safety cap."""

    def __init__(self, albums_retrieved: int):
        self.albums_retrieved = albums_retrieved
        super().__init__("Navidrome album inventory exceeded the safety limit.")


def fetch_album_inventory(
    api_call: Callable[..., dict[str, Any]],
    items: Callable[[Any], list[Any]],
    *,
    page_size: int = 500,
    max_albums: int = 50000,
) -> list[dict[str, Any]]:
    """Fetch a complete raw Navidrome album inventory with stable ID deduplication.

    This low-level boundary deliberately does not cache or normalize records.
    Callers own their freshness, schema, and error-response contracts.
    """
    albums = []
    seen_ids = set()
    complete = False

    for offset in range(0, max_albums, page_size):
        root = api_call(
            "getAlbumList2",
            type="alphabeticalByName",
            size=page_size,
            offset=offset,
        )
        page = items(root.get("albumList2", {}).get("album"))
        for album in page:
            album_id = album.get("id")
            if album_id and album_id in seen_ids:
                continue
            if album_id:
                seen_ids.add(album_id)
            albums.append(album)

        if len(page) < page_size:
            complete = True
            break

    if not complete:
        raise AlbumInventoryLimitError(len(albums))
    return albums


class AlbumInventorySnapshot:
    """A process-level copy of the raw album inventory, keyed by the Navidrome scan marker (efficiency P5).

    The marker is ``getScanStatus`` ``lastScan`` and ``count``. Within ``recheck_seconds`` of the last
    check the copy is served with no Navidrome call; after that one ``getScanStatus`` call decides: an
    unchanged marker (and no scan running) keeps the copy. Play counts, last-played times, stars and
    ratings change without a scan, so a copy older than ``max_age_seconds`` is paged again whatever the
    marker says. Failures are not cached, nothing is cached while a scan runs or when the marker cannot
    be read, and callers get their own copies of the album dicts.
    """

    def __init__(self, *, recheck_seconds: float = RECHECK_SECONDS, max_age_seconds: float = MAX_AGE_SECONDS,
                 now: Callable[[], float] = time.monotonic):
        self._recheck = recheck_seconds
        self._max_age = max_age_seconds
        self._now = now
        self._lock = threading.Lock()
        self.clear()

    def clear(self) -> None:
        """Drop the copy (tests, or when the Navidrome connection changes)."""
        self._albums: list[dict[str, Any]] | None = None
        self._marker: tuple[Any, Any] | None = None
        self._fetched_at = 0.0
        self._checked_at = 0.0

    def get(self, api_call: Callable[..., dict[str, Any]], items: Callable[[Any], list[Any]]) -> list[dict[str, Any]]:
        """The album inventory, from the copy when it is still valid; raises what ``fetch_album_inventory`` raises."""
        with self._lock:
            now = self._now()
            if self._albums is not None and now - self._fetched_at < self._max_age:
                if now - self._checked_at < self._recheck:
                    return self._copy()
                marker = self._read_marker(api_call)
                if marker is not None and marker == self._marker:
                    self._checked_at = now
                    return self._copy()
            else:
                marker = self._read_marker(api_call)
            self._albums = None
            albums = fetch_album_inventory(api_call, items)
            if marker is not None:   # read before paging, so a scan ending mid-page is caught next time
                self._albums, self._marker = albums, marker
                self._fetched_at = self._checked_at = now
            return [dict(album) for album in albums]

    def _copy(self) -> list[dict[str, Any]]:
        return [dict(album) for album in self._albums or ()]

    @staticmethod
    def _read_marker(api_call: Callable[..., dict[str, Any]]) -> tuple[Any, Any] | None:
        """``(lastScan, count)``, or None when it cannot be read or a scan is running."""
        try:
            status = api_call("getScanStatus").get("scanStatus") or {}
        except Exception:  # pylint: disable=broad-except  # an unreadable marker only means "do not cache"
            return None
        if status.get("scanning"):
            return None
        return (status.get("lastScan"), status.get("count"))


def build_library_snapshot(
    api_call: Callable[..., dict[str, Any]],
    items: Callable[[Any], list[Any]],
    read_list: Callable[[str], dict[str, Any] | None],
    write_list: Callable[[str, dict[str, Any]], None],
    *,
    now: Callable[[], float] = time.time,
    cache_ttl_seconds: int = 10 * 60,
    page_size: int = 500,
    max_albums: int = 50000,
) -> dict[str, Any]:
    """Return a cached or freshly paged library snapshot.

    All application services are injected so importing this module performs no
    network requests, persistence initialization, or Navidrome configuration.
    """
    cached = read_list("library_snapshot")
    if (
        cached
        and now() - cached["generated_at"] < cache_ttl_seconds
        and (
            not cached["payload"].get("albums")
            or (
                "song_count" in cached["payload"]["albums"][0]
                and "artist_id" in cached["payload"]["albums"][0]
                and "genre" in cached["payload"]["albums"][0]
                and "release_mbid" in cached["payload"]["albums"][0]
                and "created" in cached["payload"]["albums"][0]
            )
        )
    ):
        return cached["payload"]

    root = api_call("getArtists")
    indexes = root.get("artists", {}).get("index", [])
    artists = [
        {
            "id": artist.get("id"),
            "name": artist.get("name", "").strip(),
            "album_count": int(artist.get("albumCount") or 0),
        }
        for index in indexes
        for artist in items(index.get("artist"))
        if artist.get("name")
    ]

    raw_albums = fetch_album_inventory(
        api_call, items, page_size=page_size, max_albums=max_albums
    )
    albums = [
        {
            "id": album.get("id"),
            "artist": album.get("artist", ""),
            "artist_id": album.get("artistId"),
            "genre": album.get("genre"),
            "album": album.get("name", ""),
            "year": album.get("year"),
            "song_count": int(album.get("songCount") or 0),
            "coverArt": album.get("coverArt"),
            # The release MBID Navidrome tags on the album (not the release-group MBID).
            "release_mbid": album.get("musicBrainzId") or None,
            # When Navidrome first saw the album (ISO 8601); the library sorts by it as "date added".
            "created": album.get("created") or None,
        }
        for album in raw_albums
    ]

    snapshot = {"artists": artists, "albums": albums}
    write_list("library_snapshot", snapshot)
    return snapshot
