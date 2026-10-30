"""Navidrome artist/album inventory snapshot assembly."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


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
