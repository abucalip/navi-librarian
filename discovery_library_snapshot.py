"""Navidrome artist/album inventory snapshot assembly."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


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
            or "song_count" in cached["payload"]["albums"][0]
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

    albums = []
    seen_ids = set()
    complete = False
    for offset in range(0, max_albums, page_size):
        album_root = api_call(
            "getAlbumList2",
            type="alphabeticalByName",
            size=page_size,
            offset=offset,
        )
        page = items(album_root.get("albumList2", {}).get("album"))
        for album in page:
            album_id = album.get("id")
            if album_id and album_id in seen_ids:
                continue
            if album_id:
                seen_ids.add(album_id)
            albums.append({
                "id": album_id,
                "artist": album.get("artist", ""),
                "album": album.get("name", ""),
                "year": album.get("year"),
                "song_count": int(album.get("songCount") or 0),
                "coverArt": album.get("coverArt"),
            })
        if len(page) < page_size:
            complete = True
            break
    if not complete:
        raise RuntimeError("Navidrome album inventory exceeded the safety limit.")

    snapshot = {"artists": artists, "albums": albums}
    write_list("library_snapshot", snapshot)
    return snapshot
