"""Matching, ranking and result shaping over one owned index build (contract sections 3.1 to 3.3, 4.2)."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from typing import Any

from discovery.search.index import OwnedData
from discovery.search.normalize import normalize_key

ARTWORK_PATH = "/api/owned/artwork/"
SEARCH_TYPES = ("artist", "album", "song", "genre")
OWNED_TYPES = ("artist", "album", "song")
SOURCE_NAME = "navidrome"
DEFAULT_LIMIT = 10


class CursorError(ValueError):
    """Raised for a library cursor that is malformed or does not match its query."""


def artwork_url(cover_id: str | None) -> str | None:
    """Return the app route that serves this item's Navidrome cover, or None without an ID."""
    return f"{ARTWORK_PATH}{cover_id}" if cover_id else None


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
        "mbid": entry.get("mbid"),
        "album_count": entry["album_count"],
        "genre": entry["genre"],
        "sources": [SOURCE_NAME],
        "artwork_url": artwork_url(entry["id"]),
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
        "release_group_mbid": entry.get("release_group_mbid"),
        "sources": [SOURCE_NAME],
        "artwork_url": artwork_url(entry["id"]),
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
        "album_id": entry["album_id"] or None,
        "artist": entry["artist"],
        "artist_key": entry["artist_key"],
        "duration": entry["duration"],
        "track_number": entry["track_number"],
        "sources": [SOURCE_NAME],
        "artwork_url": artwork_url(entry["album_id"] or None),
    }


def owned_genres(data: OwnedData) -> list[dict[str, Any]]:
    """Distinct album genres of the library, one entry per normalized key (first spelling kept)."""
    found: dict[str, dict[str, Any]] = {}
    for album in data.albums:
        name = str(album.get("genre") or "").strip()
        key = normalize_key(name)
        if key and key not in found:
            found[key] = {"id": key, "key": key, "name": name, "name_key": key}
    return list(found.values())


def _genre_result(entry: dict[str, Any]) -> dict[str, Any]:
    # An owned genre has no provider of its own, so its tag source is the library (section 3.8 amendment).
    return {
        "type": "genre",
        "owned": True,
        "id": entry["id"],
        "key": entry["key"],
        "name": entry["name"],
        "mbid": None,
        "tag": entry["key"],
        "tag_source": SOURCE_NAME,
        "sources": [SOURCE_NAME],
        "artwork_url": None,
    }


_SHAPERS = {"genre": _genre_result, "artist": _artist_result, "album": _album_result, "song": _song_result}


def search_owned(
    data: OwnedData,
    query: str,
    types: Iterable[str],
    limit: int = DEFAULT_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    """Return up to ``limit`` owned results per requested type, best match first."""
    types = list(types)
    pools = {
        "artist": (data.artists, "key"),
        "album": (data.albums, "name_key"),
        "song": (data.songs, "name_key"),
        "genre": (owned_genres(data) if "genre" in types else (), "name_key"),
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


# The direction each sort starts in; the caller's ``order`` overrides it.
ARTIST_SORTS = {"name": "asc", "album_count": "desc", "added": "desc"}
ALBUM_SORTS = {"name": "asc", "artist": "asc", "year": "desc", "added": "desc", "song_count": "desc"}
LIBRARY_ORDERS = ("asc", "desc")


def _sorted(entries: list[dict[str, Any]], field: str, order: str, tie: tuple[str, ...]) -> list[dict[str, Any]]:
    """Sort by ``field`` in ``order``; entries without a value go last in either direction."""
    reverse = order == "desc"
    present = [e for e in entries if e.get(field) is not None]
    missing = [e for e in entries if e.get(field) is None]
    present.sort(key=lambda e: tuple(e[name] for name in tie))
    present.sort(key=lambda e: e[field], reverse=reverse)
    missing.sort(key=lambda e: tuple(e[name] for name in tie))
    return present + missing


def library_page(
    data: OwnedData,
    *,
    query: str,
    sort: str,
    offset: int,
    limit: int,
    order: str | None = None,
) -> tuple[list[dict[str, Any]], int | None, int]:
    """Return one page of artists, the next offset (or None), and the filtered total."""
    order = order or ARTIST_SORTS[sort]
    matching = [a for a in data.artists if not query or query in a["key"]]
    matching = _sorted(matching, "key" if sort == "name" else sort, order, ("key", "id"))
    total = len(matching)
    page = matching[offset:offset + limit]
    next_offset = offset + limit if offset + limit < total else None
    items = [
        {
            "id": a["id"],
            "key": a["key"],
            "name": a["name"],
            "album_count": a["album_count"],
            "added": a.get("added"),
            "artwork_url": artwork_url(a["id"]),
        }
        for a in page
    ]
    return items, next_offset, total


def library_albums_page(
    data: OwnedData,
    *,
    query: str,
    sort: str,
    offset: int,
    limit: int,
    order: str | None = None,
) -> tuple[list[dict[str, Any]], int | None, int]:
    """Return one page of albums, the next offset (or None), and the filtered total.

    The query matches the album name or its artist's name.
    """
    order = order or ALBUM_SORTS[sort]
    matching = [a for a in data.albums if not query or query in a["name_key"] or query in a["artist_key"]]
    field = {"name": "name_key", "artist": "artist_key"}.get(sort, sort)
    tie = ("name_key", "id") if sort == "artist" else ("artist_key", "name_key", "id")
    matching = _sorted(matching, field, order, tie)
    total = len(matching)
    page = matching[offset:offset + limit]
    next_offset = offset + limit if offset + limit < total else None
    items = [
        {
            "id": a["id"],
            "key": a["key"],
            "name": a["name"],
            "artist": a["artist"],
            "artist_key": a["artist_key"],
            "year": a["year"],
            "added": a["added"],
            "song_count": a["song_count"],
            "artwork_url": artwork_url(a["id"]),
        }
        for a in page
    ]
    return items, next_offset, total


def encode_cursor(*, offset: int, query: str, sort: str, order: str = "") -> str:
    raw = json.dumps({"o": offset, "q": query, "s": sort, "r": order}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str, *, query: str, sort: str, order: str = "") -> int:
    """Return the offset stored in ``cursor``; refuse one issued for another query, sort or order."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        offset = payload["o"]
        matches = payload["q"] == query and payload["s"] == sort and payload.get("r", "") == order
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
        {"name": a["name"], "year": a["year"], "song_count": a["song_count"], "key": a["key"],
         "id": a["id"], "artwork_url": artwork_url(a["id"])}
        for a in albums
    ]
