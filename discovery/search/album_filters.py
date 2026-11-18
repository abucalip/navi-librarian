"""Library album filters (Index and Bento themes, I0): ``unplayed`` and ``lossless``.

Pure, over the index entries' ``plays`` (Navidrome play counts summed over the album's songs)
and ``quality`` (the album tag from ``quality_label.album_quality_label``). An album whose files
report no format is never ``lossless``; one with no recorded plays is ``unplayed``.
"""

from __future__ import annotations

from typing import Any

ALBUM_FILTERS = ("unplayed", "lossless")


def matches(album: dict[str, Any], name: str) -> bool:
    if name == "unplayed":
        return not album.get("plays")
    if name == "lossless":
        return album.get("quality") in ("FLAC", "lossless")
    return True


def apply_filter(albums: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    """The albums that match ``name``; an empty name keeps them all."""
    return [a for a in albums if matches(a, name)] if name else albums
