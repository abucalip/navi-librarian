"""Pure matching policy for Deezer album metadata payloads."""

from collections.abc import Iterable
from typing import Any


def normalize_catalog_name(value: Any) -> str:
    """Normalize catalog names for conservative exact-match comparisons."""
    return "".join(char.casefold() for char in str(value or "") if char.isalnum())


def exact_album_matches(
    albums: Iterable[dict[str, Any]], artist: str, album: str
) -> list[dict[str, Any]]:
    """Keep only catalog rows whose artist and album both match exactly."""
    artist_key = normalize_catalog_name(artist)
    album_key = normalize_catalog_name(album)
    if not artist_key or not album_key:
        return []
    return [
        item for item in albums
        if normalize_catalog_name((item.get("artist") or {}).get("name")) == artist_key
        and normalize_catalog_name(item.get("title")) == album_key
    ]


def release_year(value: Any) -> int | None:
    """Return a plausible four-digit release year, otherwise None."""
    year_text = str(value or "")[:4]
    if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
        return int(year_text)
    return None


def artwork_match_score(item: dict[str, Any], artist: str, album: str) -> int:
    """Score a Deezer album for artwork lookup, preserving the existing ranking."""
    candidate_artist = str((item.get("artist") or {}).get("name") or "").casefold()
    candidate_album = str(item.get("title") or "").casefold()
    artist_key = artist.casefold()
    album_key = album.casefold()
    score = 0
    if artist_key == candidate_artist:
        score += 5
    elif artist_key and artist_key in candidate_artist:
        score += 2
    if album_key == candidate_album:
        score += 8
    elif album_key and (album_key in candidate_album or candidate_album in album_key):
        score += 4
    return score
