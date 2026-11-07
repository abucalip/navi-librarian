"""Sonic similarity and path routes (Server V2 Phase 7, slice 2, docs/ServerV2.md).

HTTP adapters only: the logic lives in ``intelligence.sonic.proxy`` (Navidrome's sonic endpoints with
Librarian's rules) and answers are kept for an hour by ``intelligence.sonic.cache``. Read-only: no writes,
no provider traffic, no store access.

Statuses: ``ok`` and ``empty`` answer 200; ``not_found`` answers 404; ``unavailable`` and any Navidrome
failure answer 502 with a fixed message (the Navidrome error text is never sent to the client).
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_librarian
from intelligence.sonic import sonic_path, similar_tracks
from intelligence.sonic.cache import TTLCache

router = APIRouter()

SIMILAR_COUNT = (1, 50)
PATH_COUNT = (2, 50)
CACHE = TTLCache()


def _answer(key, call):
    """Serve ``key`` from the cache, or run ``call()`` and map its status to an HTTP answer."""
    cached = CACHE.get(key)
    if cached is not None:
        return cached
    try:
        result = call()
    except ValueError:
        raise HTTPException(status_code=400, detail="start and end must be different songs.")
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Navidrome did not answer the sonic request.")
    if result.status == "not_found":
        raise HTTPException(status_code=404, detail="Unknown song.")
    if result.status == "unavailable":
        raise HTTPException(status_code=502, detail="Sonic similarity is unavailable.")
    payload = result.payload()
    CACHE.offer(key, result.status, payload)
    return payload


@router.get("/api/sonic/similar")
def similar(id: str = Query(..., min_length=1), count: int = Query(10, ge=SIMILAR_COUNT[0], le=SIMILAR_COUNT[1]),
            librarian=Depends(get_librarian)):
    """Owned tracks that sound like one song (Navidrome's order, near-duplicates of the song removed)."""
    return _answer(("similar", id, count),
                   lambda: similar_tracks(librarian.api_call, id, count=count))


@router.get("/api/sonic/path")
def path(start: str = Query(..., min_length=1), end: str = Query(..., min_length=1),
         count: int = Query(10, ge=PATH_COUNT[0], le=PATH_COUNT[1]), librarian=Depends(get_librarian)):
    """Ordered steps from one song to another through sound; the first step is the start song."""
    return _answer(("path", start, end, count),
                   lambda: sonic_path(librarian.api_call, start, end, count=count))
