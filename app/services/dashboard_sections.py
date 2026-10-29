"""Navidrome-backed dashboard sections: genre tiles and album shelves.

The Navidrome call is injected so these functions can be tested without
FastAPI or a running server. Every album returned here is in the library.
"""

from collections.abc import Callable
from typing import Any

from discovery.search.query import ARTWORK_PATH
from integrations.navidrome.client import items

# Public shelf name -> Subsonic getAlbumList2 type.
SHELF_TYPES = {
    "newest": "newest",
    "recent": "recent",
    "frequent": "frequent",
}


def genre_tiles(api_call: Callable[..., Any], limit: int) -> list[dict[str, Any]]:
    """Genres with albums, largest first; ties and case variants fold to one tile."""
    root = api_call("getGenres")
    merged: dict[str, dict[str, Any]] = {}
    for entry in items((root.get("genres") or {}).get("genre")):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("value") or "").strip()
        albums = int(entry.get("albumCount") or 0)
        if not name or albums <= 0:
            continue
        tile = merged.setdefault(name.casefold(), {"name": name, "tag": name.casefold(), "album_count": 0})
        tile["album_count"] += albums
    ranked = sorted(merged.values(), key=lambda tile: (-tile["album_count"], tile["tag"]))
    return ranked[:limit]


def album_shelf(api_call: Callable[..., Any], shelf: str, count: int) -> list[dict[str, Any]]:
    """One page of albums in Navidrome's own order for the shelf."""
    root = api_call("getAlbumList2", type=SHELF_TYPES[shelf], size=count, offset=0)
    albums = []
    for album in items((root.get("albumList2") or {}).get("album")):
        if not isinstance(album, dict):
            continue
        album_id = str(album.get("id") or "")
        name = str(album.get("name") or album.get("title") or "").strip()
        artist = str(album.get("artist") or "").strip()
        if not album_id or not name:
            continue
        cover_id = str(album.get("coverArt") or album_id)
        year = album.get("year")
        albums.append({
            "id": album_id,
            "name": name,
            "artist": artist,
            "artist_id": str(album.get("artistId") or ""),
            "year": year if isinstance(year, int) and year > 0 else None,
            "artwork_url": f"{ARTWORK_PATH}{cover_id}",
            "owned": True,
        })
    return albums
