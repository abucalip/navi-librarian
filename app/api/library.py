"""Library browsing route (contract section 3.2). HTTP adapter only."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.search import owned_view
from discovery.search.normalize import normalize_query
from discovery.search.query import (
    ALBUM_SORTS,
    ARTIST_SORTS,
    LIBRARY_ORDERS,
    CursorError,
    decode_cursor,
    encode_cursor,
    library_albums_page,
    library_page,
)

router = APIRouter()


def iso_timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_limit(raw: str | None) -> int:
    if raw is None:
        return 60
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if not 1 <= value <= 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")
    return value


def _library_response(sorts, page_fn, q, sort, order, cursor, limit, librarian):
    """Shared body of the artist and album library routes."""
    if sort not in sorts:
        raise HTTPException(status_code=400, detail="sort must be one of: " + ", ".join(sorts) + ".")
    if order is not None and order not in LIBRARY_ORDERS:
        raise HTTPException(status_code=400, detail="order must be asc or desc.")
    page_size = _parse_limit(limit)
    query = normalize_query(q or "")
    # The effective direction goes into the cursor, so a page request cannot change it midway.
    effective = order or sorts[sort]

    view = owned_view(librarian)
    if view.data is None:
        # building and unavailable are never reported as an empty library.
        return {
            "items": [],
            "next_cursor": None,
            "total": None,
            "index_state": view.state,
            "snapshot_at": None,
        }

    offset = 0
    if cursor:
        try:
            offset = decode_cursor(cursor, query=query, sort=sort, order=effective)
        except CursorError:
            raise HTTPException(status_code=400, detail="cursor is not valid for this request.")

    items, next_offset, total = page_fn(
        view.data, query=query, sort=sort, offset=offset, limit=page_size, order=effective,
    )
    return {
        "items": items,
        "next_cursor": None if next_offset is None else encode_cursor(
            offset=next_offset, query=query, sort=sort, order=effective,
        ),
        "total": total,
        "index_state": view.state,
        "snapshot_at": iso_timestamp(view.data.built_at),
    }


@router.get("/api/library/artists")
def library_artists(
    q: str | None = None,
    sort: str = "name",
    order: str | None = None,
    cursor: str | None = None,
    limit: str | None = None,
    librarian=Depends(get_librarian),
):
    return _library_response(
        ARTIST_SORTS, library_page, q, sort, order, cursor, limit, librarian,
    )


@router.get("/api/library/albums")
def library_albums(
    q: str | None = None,
    sort: str = "name",
    order: str | None = None,
    cursor: str | None = None,
    limit: str | None = None,
    librarian=Depends(get_librarian),
):
    return _library_response(
        ALBUM_SORTS, library_albums_page, q, sort, order, cursor, limit, librarian,
    )
