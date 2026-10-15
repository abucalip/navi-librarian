"""Discovery API routes.

HTTP adapters only: recommendation and discovery behavior remains in the
existing librarian domain functions. Preserve the API contract while the routes
are separated from app assembly.
"""
import json

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.utils import parse_result

router = APIRouter()


@router.get("/api/recommendations")
def recommendations(count: int = 10, librarian=Depends(get_librarian)):
    if not 1 <= count <= 30:
        raise HTTPException(
            status_code=400,
            detail="count must be between 1 and 30",
        )

    try:
        data = parse_result(librarian.recommend_new_music(count=count))
        if isinstance(data, dict):
            for key in ("recommendations", "items"):
                if isinstance(data.get(key), list):
                    data[key] = [
                        item for item in data[key]
                        if librarian._discovery_is_album_candidate(item)
                    ]
        return data
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not generate recommendations.",
        )


@router.get("/api/discovery/{list_name}")
def discovery_list(list_name: str, count: int = 30, librarian=Depends(get_librarian)):
    allowed = {"personal", "for_me", "classics", "artist_deep_dive", "new_releases"}
    if list_name not in allowed:
        raise HTTPException(status_code=404, detail="Unknown discovery list.")
    if not 1 <= count <= 150:
        raise HTTPException(status_code=400, detail="count must be between 1 and 150")
    try:
        return parse_result(
            librarian.discovery_get_list(list_name=list_name, count=count)
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve the discovery list.")


@router.post("/api/discovery/{list_name}/refresh")
def refresh_discovery_list(list_name: str, payload: dict | None = None, librarian=Depends(get_librarian)):
    if list_name not in {"personal", "classics", "artist_deep_dive", "new_releases", "all"}:
        raise HTTPException(status_code=404, detail="Unknown discovery list.")
    payload = payload or {}
    try:
        count = int(payload.get("count", 20))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="count must be an integer")
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    try:
        return parse_result(
            librarian.discovery_refresh_list(list_name=list_name, count=count)
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not refresh the discovery list.")


@router.post("/api/discovery/feedback")
def discovery_feedback(payload: dict, librarian=Depends(get_librarian)):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    action = str(payload.get("action") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    if action not in {"save", "dismiss", "dismiss_artist", "remove_for_me"}:
        raise HTTPException(status_code=400, detail="Unsupported feedback action")
    try:
        return parse_result(librarian.discovery_set_feedback(
            artist=artist,
            album=album,
            action=action,
            metadata_json=json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save discovery feedback.")
