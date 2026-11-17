"""Dashboard and health API routes.

These HTTP handlers use the shared lazy librarian dependency; discovery behavior
and Navidrome connectivity remain owned by the existing service implementation.
"""
import functools
import random

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from discovery import week_plays
from app.services import lens_week_picks
from app.services.dashboard_sections import SHELF_TYPES, album_shelf, genre_tiles

router = APIRouter()
_WEEK_PLAYS = week_plays.WeekPlays()


def _week_reader(librarian):
    """A reader of the last week's ListenBrainz listens, or None without a configured username."""
    import httpx
    from discovery import history_fetch
    from integrations.listenbrainz.client import request_headers

    username = str(librarian._listenbrainz_username() or "").strip()
    if not username:
        return None
    return functools.partial(history_fetch.listenbrainz_window, username, get=httpx.get, headers=request_headers())


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

    # Only the week's Current tastes lists (docs/ACTIVE_WORK.md, owner request); each call shuffles again.
    return lens_week_picks.picks(librarian, count, shuffle=random.shuffle)


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
        items = album_shelf(librarian.api_call, shelf, count)
        if shelf == "recent":
            # Plays in the last seven days (Index theme); left off when the listens cannot be read.
            try:
                items = week_plays.attach(items, _WEEK_PLAYS.counts(_week_reader(librarian)))
            except Exception:
                pass
        return {"items": items}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not load albums from Navidrome.")
