"""``GET /api/capabilities`` (Server V2 contract): which intelligence features have data.

HTTP adapter over ``intelligence.api.build_capabilities``. Never cached, so a client can poll it
to decide which sections to show. ``listenbrainz_connected`` reflects whether a ListenBrainz
username is saved; ``graph_coverage`` stays at its unknown value until a later phase measures it.
``sonic_available`` is true when Navidrome lists the ``sonicSimilarity`` extension (checked at most every
five minutes; any failure reads as false), so this route makes one cached Navidrome call besides reading
the Server V2 store; no provider traffic.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.api import ServerFacts, build_capabilities
from intelligence.sonic.detect import SonicDetector
from intelligence.store import open_store

router = APIRouter()
SONIC = SonicDetector()


def _listenbrainz_connected(librarian):
    try:
        return bool(librarian._listenbrainz_username())
    except Exception:
        return False


def _sonic_available(librarian):
    try:
        return SONIC.available(librarian.api_call)
    except Exception:
        return False


@router.get("/api/capabilities")
def capabilities(librarian=Depends(get_librarian)):
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            body = build_capabilities(db, ServerFacts(
                sonic_available=_sonic_available(librarian),
                listenbrainz_connected=_listenbrainz_connected(librarian)))
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read capabilities.")
    return JSONResponse(body, headers={"Cache-Control": "no-store"})
