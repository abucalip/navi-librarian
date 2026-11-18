"""An owned album's place in the library by name (Index theme I0, decision I7)."""

from __future__ import annotations

from typing import Any

from discovery.search.index import OwnedData


def library_position(data: OwnedData | None, album: dict[str, Any] | None) -> tuple[int, int] | None:
    """Return ``(position, total)``, counting from 1 in album-name order, or None when it cannot be told.

    The order is the library's name sort: album name, then artist, then id. None for an album the
    index does not hold.
    """
    if data is None or album is None:
        return None
    mine = (album["name_key"], album["artist_key"], album["id"])
    if not any(a["id"] == album["id"] for a in data.albums):
        return None
    before = sum(1 for a in data.albums if (a["name_key"], a["artist_key"], a["id"]) < mine)
    return before + 1, len(data.albums)
