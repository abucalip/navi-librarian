"""Album covers from Apple Music and Qobuz, for albums Deezer does not have.

Pure selection policy. A cover is returned only when the service's artist and album names both
match the request exactly (ignoring case, punctuation and a trailing "- Single"/"- EP"). A near
match would put another record's cover on the album, so no match means no cover.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable
from typing import Any

from app.services.deezer_album_matching import normalize_catalog_name

_EDITION_SUFFIX = re.compile(r"\s+-\s+(single|ep)$", re.IGNORECASE)
_LIVE_PROPS = re.compile(r'data-live-props-value="([^"]*)"')


def select_apple_artwork(results: Iterable[dict[str, Any]], artist: str, album: str) -> dict[str, Any] | None:
    """The 600px cover of the iTunes Search collection whose artist and album match exactly."""
    artist_key, album_key = normalize_catalog_name(artist), normalize_catalog_name(album)
    if not artist_key or not album_key:
        return None
    for item in results:
        title = _EDITION_SUFFIX.sub("", str(item.get("collectionName") or ""))
        small = str(item.get("artworkUrl100") or "")
        if (
            normalize_catalog_name(item.get("artistName")) == artist_key
            and normalize_catalog_name(title) == album_key
            and small.startswith("https://")
        ):
            return {
                "artwork_url": re.sub(r"/\d+x\d+(bb)?\.(jpg|png)$", r"/600x600bb.\2", small),
                "image_kind": "album",
                "source": "Apple Music",
                "matched_artist": item.get("artistName"),
                "matched_album": item.get("collectionName"),
                "year": _year(item.get("releaseDate")),
            }
    return None


def parse_qobuz_albums(page: str) -> list[dict[str, Any]]:
    """The albums embedded in a Qobuz search results page, or [] when the layout is not recognised."""
    for raw in _LIVE_PROPS.findall(page):
        try:
            albums = json.loads(html.unescape(raw)).get("albums")
            albums = json.loads(albums) if isinstance(albums, str) else albums
        except (ValueError, AttributeError):
            continue
        if isinstance(albums, dict):
            return [item for item in albums.values() if isinstance(item, dict)]
    return []


def select_qobuz_artwork(albums: Iterable[dict[str, Any]], artist: str, album: str) -> dict[str, Any] | None:
    """The large cover of the Qobuz album whose artist and album match exactly."""
    artist_key, album_key = normalize_catalog_name(artist), normalize_catalog_name(album)
    if not artist_key or not album_key:
        return None
    for item in albums:
        cover = str((item.get("image") or {}).get("large") or "")
        names = [normalize_catalog_name(a.get("name")) for a in item.get("artists") or [] if isinstance(a, dict)]
        if artist_key in names and normalize_catalog_name(item.get("title")) == album_key and cover.startswith("https://"):
            return {
                "artwork_url": cover,
                "image_kind": "album",
                "source": "Qobuz",
                "matched_artist": artist,
                "matched_album": item.get("title"),
                "year": _year(item.get("releasedAt")),
            }
    return None


def _year(value: Any) -> int | None:
    text = str(value or "")
    if text.isdigit() and len(text) >= 9:  # Qobuz gives a Unix timestamp
        from datetime import datetime, timezone
        year = datetime.fromtimestamp(int(text), timezone.utc).year
    elif text[:4].isdigit():
        year = int(text[:4])
    else:
        return None
    return year if 1900 <= year <= 2100 else None
