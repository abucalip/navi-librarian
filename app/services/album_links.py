"""Pure helpers that pick an album's own page on each music service from search results.

A page is returned only when the service's artist and album names both match the request
exactly (ignoring case, accents of punctuation and edition suffixes). Anything less would send
the reader to the wrong record, so the caller keeps its search link instead.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.services.deezer_album_matching import exact_album_matches, normalize_catalog_name

_EDITION_SUFFIX = re.compile(r"\s+-\s+(single|ep)$", re.IGNORECASE)


def apple_music_url(results: list[dict[str, Any]], artist: str, album: str) -> str | None:
    """The Apple Music page of an exactly matching iTunes Search collection, without tracking parameters."""
    artist_key, album_key = normalize_catalog_name(artist), normalize_catalog_name(album)
    for item in results:
        title = _EDITION_SUFFIX.sub("", str(item.get("collectionName") or ""))
        if (
            normalize_catalog_name(item.get("artistName")) == artist_key
            and normalize_catalog_name(title) == album_key
            and str(item.get("collectionViewUrl") or "").startswith("https://music.apple.com/")
        ):
            parts = urlsplit(item["collectionViewUrl"])
            return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return None


def deezer_url(albums: list[dict[str, Any]], artist: str, album: str) -> str | None:
    matches = exact_album_matches(albums, artist, album)
    album_id = matches[0].get("id") if matches else None
    return f"https://www.deezer.com/album/{album_id}" if album_id else None


def musicbrainz_group_id(groups: list[dict[str, Any]], artist: str, album: str) -> str | None:
    """The release-group ID of an exactly matching MusicBrainz result."""
    artist_key, album_key = normalize_catalog_name(artist), normalize_catalog_name(album)
    for group in groups:
        credit = "".join(
            str(part.get("name") or "") + str(part.get("joinphrase") or "")
            for part in group.get("artist-credit") or []
            if isinstance(part, dict)
        )
        if group.get("id") and normalize_catalog_name(group.get("title")) == album_key \
                and normalize_catalog_name(credit) == artist_key:
            return str(group["id"])
    return None
