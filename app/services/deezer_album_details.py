"""Pure shaping of a matched Deezer album into the album-details payload."""

from typing import Any

from app.services.deezer_album_matching import release_year


def shape_album_match(match: dict[str, Any]) -> dict[str, Any]:
    """Project a matched catalog row into the existing album-details fields."""
    artwork = (
        match.get("cover_xl")
        or match.get("cover_big")
        or match.get("cover_medium")
        or ""
    )
    return {
        "matched_artist": (match.get("artist") or {}).get("name"),
        "matched_album": match.get("title"),
        "year": release_year(match.get("release_date")),
        "artwork_url": artwork.replace("http://", "https://", 1) or None,
    }
