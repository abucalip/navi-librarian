"""Acquisition API routes.

HTTP adapters only: acquisition lifecycle, slskd interaction, and filesystem safety
remain owned by the existing librarian domain functions. Keep this module free of
filesystem mutations and provider orchestration.
"""
import json
from time import sleep

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from acquisition import track_service
from app.api.dependencies import get_librarian
from app.api.utils import parse_result

router = APIRouter()


@router.get("/api/acquisitions")
def acquisition_status(librarian=Depends(get_librarian)):
    try:
        return track_service.augment_status(
            librarian, parse_result(librarian.discovery_get_acquisition_status()))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve acquisition status.")


@router.post("/api/acquisitions/skip")
def skip_acquisition_source(payload: dict, librarian=Depends(get_librarian)):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    try:
        result = parse_result(librarian.discovery_skip_acquisition_source(
            artist=artist, album=album,
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=409, detail=result.get("error", "Could not skip source."))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not request a source switch.")


@router.post("/api/acquisitions/dismiss")
def dismiss_acquisition(payload: dict, librarian=Depends(get_librarian)):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    try:
        # A song removes only its own download; anything else takes the album path.
        result = track_service.dismiss_track(librarian, artist, album)
        if result is None:
            result = parse_result(librarian.discovery_dismiss_acquisition(artist=artist, album=album))
        if isinstance(result, dict) and not result.get("ok"):
            message = result.get("error", "Could not dismiss acquisition.")
            status_code = 404 if message == "Acquisition not found." else 409
            raise HTTPException(status_code=status_code, detail=message)
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not dismiss acquisition.")


@router.get("/api/acquisitions/stream")
def acquisition_status_stream(librarian=Depends(get_librarian)):
    def events():
        while True:
            try:
                payload = track_service.augment_status(
                    librarian, parse_result(librarian.discovery_get_acquisition_status()))
                yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
            except Exception:
                yield "event: error\ndata: {}\n\n"
            sleep(1)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/acquire")
def acquire_album(payload: dict, librarian=Depends(get_librarian)):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    auto_queue = payload.get("auto_queue", True)
    if not isinstance(auto_queue, bool):
        raise HTTPException(status_code=400, detail="auto_queue must be a boolean")
    try:
        return parse_result(librarian.discovery_acquire_album(
            artist=artist,
            album=album,
            metadata_json=json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
            auto_queue=auto_queue,
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not search slskd for this album.")


@router.post("/api/acquire/queue")
def queue_reviewed_candidate(payload: dict, librarian=Depends(get_librarian)):
    username = str(payload.get("username") or "").strip()
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    folder = str(payload.get("folder") or "").strip()
    files = payload.get("files")
    if not username or not isinstance(files, list) or not files:
        raise HTTPException(status_code=400, detail="username and a non-empty files list are required")
    try:
        return parse_result(librarian.discovery_queue_slskd_candidate(
            username=username,
            files_json=json.dumps(files, ensure_ascii=False),
            artist=artist,
            album=album,
            folder=folder,
            quality_summary_json=json.dumps(payload.get("quality_summary") or [], ensure_ascii=False),
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not queue the selected candidate.")


@router.post("/api/acquire/track")
def acquire_track(payload: dict, librarian=Depends(get_librarian)):
    """Get one song of an album: the best clear file is chosen automatically."""
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not artist or not album or not title:
        raise HTTPException(status_code=400, detail="artist, album and title are required")
    number = payload.get("track_number")
    if number is not None and (isinstance(number, bool) or not isinstance(number, int) or number < 1):
        raise HTTPException(status_code=400, detail="track_number must be a positive integer")
    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")
    try:
        return track_service.request_track(
            librarian, artist, album, title, number, payload.get("year"), metadata)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not search slskd for this song.")
