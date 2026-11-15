"""Navidrome starred artists and albums (Subsonic ``getStarred2``), parsed for seed input.

Provider I/O only: the caller decides what a star means for recommendations. The
``api_call`` and ``items`` callables are injected, as in ``fetch_album_inventory``,
so importing this module makes no request and reads no configuration.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any


def _starred_epoch(value: Any) -> float | None:
    """Return a Navidrome star timestamp as epoch seconds, or ``None`` if absent or unreadable."""
    if not value or str(value).startswith("0001"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_starred(
    root: dict[str, Any],
    items: Callable[[Any], list[Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Normalize a ``getStarred2`` response into starred ``artists`` and ``albums``.

    Songs are ignored. Rows without an ID are dropped. A missing or unreadable star
    date keeps the row with ``starred_at`` set to ``None``.
    """
    starred = root.get("starred2") or {}
    return {
        "artists": [
            {"id": item["id"], "name": item.get("name"),
             "starred_at": _starred_epoch(item.get("starred"))}
            for item in items(starred.get("artist"))
            if item.get("id")
        ],
        "albums": [
            {"id": item["id"], "name": item.get("name"), "artist": item.get("artist"),
             "artist_id": item.get("artistId"),
             "starred_at": _starred_epoch(item.get("starred"))}
            for item in items(starred.get("album"))
            if item.get("id")
        ],
    }


def fetch_starred(
    api_call: Callable[..., dict[str, Any]],
    items: Callable[[Any], list[Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Read the owner's starred artists and albums with one ``getStarred2`` call.

    Errors from ``api_call`` propagate unchanged; callers decide how to degrade.
    """
    root = api_call("getStarred2")
    return parse_starred(root, items)
