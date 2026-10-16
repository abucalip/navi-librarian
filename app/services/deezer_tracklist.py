"""Pure shaping of Deezer album tracklist payloads."""

from collections.abc import Iterable
from typing import Any


def shape_tracklist(tracks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize provider track rows to the existing album-details response shape."""
    return [
        {
            "track_number": int(track.get("track_position") or index + 1),
            "title": str(track.get("title") or "").strip(),
            "duration_seconds": int(track.get("duration") or 0),
        }
        for index, track in enumerate(tracks)
        if str(track.get("title") or "").strip()
    ]
