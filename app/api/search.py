"""Global search and artist routes (contract sections 3.1 and 3.3).

HTTP adapters only. Matching, ranking and index lifecycle live in ``discovery/search``.
"""

from __future__ import annotations

import threading
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.dependencies import get_librarian
from discovery.library_snapshot import build_library_snapshot
from discovery.search.artist_page import artist_page, json_sections, section_events
from discovery.search.events import search_events, sse
from discovery.search.index import OwnedIndex, fetch_song_inventory
from discovery.search.network import external_search
from discovery.search.normalize import normalize_key, normalize_query
from discovery.search.query import SEARCH_TYPES
from settings.service import navidrome_generation

router = APIRouter()

_owned_index: OwnedIndex | None = None
_owned_index_lock = threading.Lock()


def _snapshot_lists(librarian, generation):
    """Artists and albums from the library snapshot, keyed by Navidrome generation (section 5.2)."""
    suffix = f":navidrome{generation}"

    def read(name):
        return librarian._discovery_read_list(name + suffix)

    def write(name, payload):
        librarian._discovery_write_list(name + suffix, payload)

    snapshot = build_library_snapshot(librarian.api_call, librarian.items, read, write)
    return snapshot["artists"], snapshot["albums"]


def owned_index_for(librarian) -> OwnedIndex:
    """Return the process-wide owned index, creating it on first use with the given service."""
    global _owned_index
    with _owned_index_lock:
        if _owned_index is None:
            _owned_index = OwnedIndex(
                load_library=lambda: _snapshot_lists(
                    librarian, navidrome_generation(librarian._discovery_settings_read)
                ),
                load_songs=lambda: fetch_song_inventory(librarian.api_call, librarian.items),
            )
        return _owned_index


def owned_view(librarian):
    """Trigger a background refresh if needed, then read the last known-good state."""
    index = owned_index_for(librarian)
    index.ensure(navidrome_generation(librarian._discovery_settings_read))
    return index.view()


def _wants_stream(request: Request) -> bool:
    return "text/event-stream" in request.headers.get("accept", "")


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _parse_types(raw: str | None) -> list[str]:
    if raw is None:
        return list(SEARCH_TYPES)
    requested = [part.strip() for part in raw.split(",")]
    if not requested or any(part not in SEARCH_TYPES for part in requested):
        raise HTTPException(
            status_code=400,
            detail="types must be a comma list of artist, album, song or genre.",
        )
    return list(dict.fromkeys(requested))


def _parse_limit(raw: str | None) -> int:
    if raw is None:
        return 10
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if not 1 <= value <= 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50.")
    return value


@router.get("/api/search")
def search(
    q: str | None = None,
    types: str | None = None,
    scope: str = "all",
    limit: str | None = None,
    librarian=Depends(get_librarian),
):
    raw_query = (q or "").strip()
    if not 1 <= len(raw_query) <= 200:
        raise HTTPException(status_code=400, detail="q must be 1 to 200 characters.")
    query = normalize_query(raw_query)
    if not query:
        raise HTTPException(status_code=400, detail="q must contain a letter or digit.")
    if scope not in ("owned", "all"):
        raise HTTPException(status_code=400, detail="scope must be owned or all.")
    requested_types = _parse_types(types)
    max_per_type = _parse_limit(limit)

    view = owned_view(librarian)
    started = time.monotonic()
    # scope=owned never reads or writes the provider cache and makes no network call (section 8.1).
    external = None
    if scope == "all":
        external = external_search(
            settings_read=librarian._discovery_settings_read,
            cache_read=librarian._discovery_read_list,
            cache_write=librarian._discovery_write_list,
        )

    def stream():
        for name, payload in search_events(
            view,
            query=query,
            types=requested_types,
            limit=max_per_type,
            elapsed_ms=lambda: _elapsed_ms(started),
            external=external,
            started=started,
        ):
            yield sse(name, payload)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/artists/{key}")
def artist(
    key: str,
    request: Request,
    id: str | None = None,
    mbid: str | None = None,
    librarian=Depends(get_librarian),
):
    """Artist page. ``mbid`` is accepted for provider lookups; it never selects the owned artist."""
    started = time.monotonic()
    try:
        page = artist_page(owned_view(librarian), normalize_key(key), id)
    except Exception:
        return JSONResponse(
            status_code=502,
            content={"code": "artist_failed", "message": "Owned index read failed."},
        )

    if page.status == "unknown":
        return JSONResponse(
            status_code=404,
            content={"code": "unknown_artist", "message": "No artist matches this key."},
        )
    if page.status == "ambiguous":
        return JSONResponse(
            status_code=409,
            content={
                "code": "ambiguous_artist",
                "message": "More than one artist has this key. Pass the artist ID.",
                "candidates": page.candidates,
            },
        )

    done = {
        "elapsed_ms": _elapsed_ms(started),
        "deadline_hit": False,
        "partial": page.partial,
    }
    if _wants_stream(request):
        def stream():
            yield sse("capabilities", page.capabilities)
            for section in section_events(page):
                yield sse("section", section)
            yield sse("done", done)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )
    return {
        "capabilities": page.capabilities,
        "sections": json_sections(page),
        "done": done,
    }
