"""Matching, ranking and result shaping over one owned index build (contract sections 3.1 to 3.3, 4.2)."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from typing import Any

from discovery.search.index import OwnedData

SEARCH_TYPES = ("artist", "album", "song", "genre")
OWNED_TYPES = ("artist", "album", "song")
SOURCE_NAME = "navidrome"
DEFAULT_LIMIT = 10
LIBRARY_SORTS = ("name", "album_count")


class CursorError(ValueError):
    """Raised for a library cursor that is malformed or does not match its query."""


def _tier(key: str, query: str) -> int | None:
    """Ranking tier for an entry key: exact, prefix, contains, or no match."""
    if key == query:
        return 0
    if key.startswith(query):
        return 1
    if query in key:
        return 2
    return None


def _artist_result(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "artist",
        "owned": True,
        "id": entry["id"],
        "key": entry["key"],
        "name": entry["name"],
        "mbid": None,
        "album_count": entry["album_count"],
        "sources": [SOURCE_NAME],
        "artwork_url": None,
    }


def _album_result(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "album",
        "owned": True,
        "id": entry["id"],
        "key": entry["key"],
        "name": entry["name"],
        "mbid": None,
        "artist": entry["artist"],
        "artist_key": entry["artist_key"],
        "year": entry["year"],
        "release_group_mbid": None,
        "sources": [SOURCE_NAME],
        "artwork_url": None,
    }


def _song_result(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "song",
        "owned": True,
        "id": entry["id"],
        "key": entry["key"],
        "name": entry["name"],
        "mbid": None,
        "album": entry["album"],
        "duration": entry["duration"],
        "track_number": entry["track_number"],
        "sources": [SOURCE_NAME],
        "artwork_url": None,
    }


_SHAPERS = {"artist": _artist_result, "album": _album_result, "song": _song_result}


def search_owned(
    data: OwnedData,
    query: str,
    types: Iterable[str],
    limit: int = DEFAULT_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    """Return up to ``limit`` owned results per requested type, best match first."""
    pools = {
        "artist": (data.artists, "key"),
        "album": (data.albums, "name_key"),
        "song": (data.songs, "name_key"),
    }
    results: dict[str, list[dict[str, Any]]] = {}
    for kind in types:
        if kind not in pools:
            continue
        entries, field = pools[kind]
        ranked = []
        for entry in entries:
            tier = _tier(entry[field], query)
            if tier is not None:
                ranked.append((tier, entry["name"].casefold(), entry["id"], entry))
        ranked.sort(key=lambda row: row[:3])
        results[kind] = [_SHAPERS[kind](row[3]) for row in ranked[:limit]]
    return results


def library_page(
    data: OwnedData,
    *,
    query: str,
    sort: str,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int | None, int]:
    """Return one page of artists, the next offset (or None), and the filtered total."""
    matching = [a for a in data.artists if not query or query in a["key"]]
    if sort == "album_count":
        matching.sort(key=lambda a: (-a["album_count"], a["key"], a["id"]))
    else:
        matching.sort(key=lambda a: (a["key"], a["id"]))
    total = len(matching)
    page = matching[offset:offset + limit]
    next_offset = offset + limit if offset + limit < total else None
    items = [
        {
            "id": a["id"],
            "key": a["key"],
            "name": a["name"],
            "album_count": a["album_count"],
            "artwork_url": None,
        }
        for a in page
    ]
    return items, next_offset, total


def encode_cursor(*, offset: int, query: str, sort: str) -> str:
    raw = json.dumps({"o": offset, "q": query, "s": sort}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str, *, query: str, sort: str) -> int:
    """Return the offset stored in ``cursor``; refuse one issued for another query or sort."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        offset = payload["o"]
        matches = payload["q"] == query and payload["s"] == sort
    except (ValueError, KeyError, TypeError):
        raise CursorError("cursor is not valid")
    if not isinstance(offset, int) or offset < 0 or not matches:
        raise CursorError("cursor does not match this query")
    return offset


def find_artist(
    data: OwnedData,
    key: str,
    artist_id: str | None,
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]]]:
    """Resolve an artist route key, returning ``(status, artist, candidates)``.

    ``status`` is ``ok``, ``unknown`` or ``ambiguous``. The optional Navidrome ID
    selects one artist exactly when two artists share a key (contract section 3.3).
    """
    matches = [a for a in data.artists if a["key"] == key]
    if artist_id:
        matches = [a for a in matches if a["id"] == artist_id]
    if not matches:
        return "unknown", None, []
    if len(matches) > 1:
        candidates = [
            {"id": a["id"], "name": a["name"], "album_count": a["album_count"]}
            for a in matches
        ]
        return "ambiguous", None, candidates
    return "ok", matches[0], []


def owned_albums(data: OwnedData, artist_id: str) -> list[dict[str, Any]]:
    """Albums of one artist, year ascending with unknown years last, then by name."""
    albums = sorted(
        data.by_artist_id.get(artist_id, ()),
        key=lambda a: (a["year"] is None, a["year"] or 0, a["name"].casefold(), a["id"]),
    )
    return [
        {"name": a["name"], "year": a["year"], "song_count": a["song_count"], "key": a["key"]}
        for a in albums
    ]
