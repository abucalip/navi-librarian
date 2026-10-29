"""Dashboard and health API routes.

These HTTP handlers use the shared lazy librarian dependency; discovery behavior
and Navidrome connectivity remain owned by the existing service implementation.
"""
import random

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.utils import parse_result
from app.services.dashboard import build_dashboard_picks
from app.services.dashboard_sections import SHELF_TYPES, album_shelf, genre_tiles

router = APIRouter()


@router.get("/api/health")
def health(librarian=Depends(get_librarian)):
    """Check whether Navidrome responds to an authenticated API request."""
    try:
        result = librarian.api_call("ping")
        return {
            "status": "ok",
            "service": "Navidrome",
            "message": result.get("status", "Connected"),
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Navidrome is unavailable or authentication failed.",
        )


@router.get("/api/dashboard-picks")
def dashboard_picks(count: int = 10, librarian=Depends(get_librarian)):
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")

    def read_list(list_name, requested_count):
        return parse_result(
            librarian.discovery_get_list(list_name=list_name, count=requested_count)
        )

    return build_dashboard_picks(
        read_list,
        librarian._discovery_is_album_candidate,
        count,
        shuffle=random.shuffle,
    )


@router.get("/api/dashboard/genres")
def dashboard_genres(limit: int = 60, librarian=Depends(get_librarian)):
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    try:
        return {"items": genre_tiles(librarian.api_call, limit)}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not load genres from Navidrome.")


@router.get("/api/dashboard/albums/{shelf}")
def dashboard_albums(shelf: str, count: int = 20, librarian=Depends(get_librarian)):
    if shelf not in SHELF_TYPES:
        raise HTTPException(status_code=404, detail="Unknown album shelf.")
    if not 1 <= count <= 50:
        raise HTTPException(status_code=400, detail="count must be between 1 and 50")
    try:
        return {"items": album_shelf(librarian.api_call, shelf, count)}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not load albums from Navidrome.")
