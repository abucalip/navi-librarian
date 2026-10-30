"""Discovery API routes.

HTTP adapters only: recommendation and discovery behavior remains in the
existing librarian domain functions. Preserve the API contract while the routes
are separated from app assembly.
"""
import json

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.utils import parse_result
from discovery import lens_service
from discovery.new_releases import enrich_new_release_listeners
from discovery.taste_families import deep_dive_row

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


# Registered before the {list_name} route below, which would otherwise match this path.
@router.get("/api/discovery/lens-feedback")
def lens_feedback(librarian=Depends(get_librarian)):
    try:
        return lens_service.feedback_summary(librarian)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read lens feedback.")


@router.get("/api/discovery/{list_name}")
def discovery_list(list_name: str, count: int = 30, librarian=Depends(get_librarian)):
    allowed = {"personal", "for_me", "classics", "artist_deep_dive", "new_releases"}
    is_lens = list_name in lens_service.lens_names()
    if list_name not in allowed and not is_lens:
        raise HTTPException(status_code=404, detail="Unknown discovery list.")
    if not 1 <= count <= 150:
        raise HTTPException(status_code=400, detail="count must be between 1 and 150")
    try:
        if is_lens:
            data = parse_result(lens_service.list_response(librarian, list_name, count))
        else:
            data = parse_result(
                librarian.discovery_get_list(list_name=list_name, count=count)
            )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve the discovery list.")
    if list_name == "artist_deep_dive" and isinstance(data, dict):
        for key in ("items", "recommendations"):
            for item in data.get(key) or []:
                if isinstance(item, dict):
                    item.update(deep_dive_row(item))
    if list_name == "new_releases" and isinstance(data, dict):
        # Last.fm audience from the existing Last.fm cache only: no provider request is made, and an
        # album the cache does not hold simply carries no count.
        lookup = getattr(getattr(librarian, "_lastfm_client", None), "cached_album_popularity", None)
        if lookup is not None:
            for key in ("items", "recommendations"):
                enrich_new_release_listeners([i for i in data.get(key) or [] if isinstance(i, dict)], lookup)
    return data


@router.post("/api/discovery/{list_name}/refresh")
def refresh_discovery_list(list_name: str, payload: dict | None = None, librarian=Depends(get_librarian)):
    if list_name not in {"personal", "classics", "artist_deep_dive", "new_releases", "all"}:
        raise HTTPException(status_code=404, detail="Unknown discovery list.")
    payload = payload or {}
    count = payload.get("count", 20)
    # JSON booleans are Python integers, and int(...) silently truncates floats
    # or accepts numeric strings. Require an actual JSON integer at this boundary.
    if type(count) is not int:
        raise HTTPException(status_code=400, detail="count must be an integer")
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    try:
        result = parse_result(
            librarian.discovery_refresh_list(list_name=list_name, count=count)
        )
        if list_name == "all":
            # Lens lists are built in the app layer (lens_service), so the manual "all" refresh
            # starts them too. It returns at once; the setting decides whether anything runs.
            lens_service.start_refresh(librarian)
        return result
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
