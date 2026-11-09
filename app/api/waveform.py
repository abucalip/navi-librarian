"""Song peaks route for the player's sound graph (docs/design/macos-player-refinements, Android port).

``GET /api/songs/{id}/peaks``: 200 ``{"bins": 1000, "peaks": [0..65535, ...]}`` when ready, 202 ``{"status": "pending"}`` while the
server decodes the song (ask again in a few seconds), 404 when the song or its file is unknown, silent or cannot be decoded.
HTTP adapter only: decoding, caching and path safety live in ``intelligence.waveform``. Read-only; the audio never leaves the server.
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_librarian
from intelligence.waveform import BINS, PeakService, PeaksUnavailable

router = APIRouter()

_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_service: PeakService | None = None


def _peaks(librarian) -> PeakService:
    global _service
    path = librarian.DATA_DIR / "song_peaks.sqlite3"
    if _service is None or _service.db_path != path:
        _service = PeakService(path)
    return _service


@router.get("/api/songs/{song_id}/peaks")
def song_peaks(song_id: str, librarian=Depends(get_librarian)):
    if not _ID.fullmatch(song_id):
        raise HTTPException(status_code=400, detail="song id is not valid.")
    try:
        root = librarian.api_call("getSong", id=song_id)
    except RuntimeError:
        raise HTTPException(status_code=404, detail="Unknown song.")
    except Exception:
        raise HTTPException(status_code=502, detail="Navidrome did not answer.")
    song = (root or {}).get("song") or {}
    if not song.get("id"):
        raise HTTPException(status_code=404, detail="Unknown song.")
    try:
        peaks = _peaks(librarian).get(song_id, librarian.MUSIC_DIR, song.get("path"))
    except PeaksUnavailable:
        raise HTTPException(status_code=404, detail="No peaks for this song.")
    if peaks is None:
        return JSONResponse({"status": "pending"}, status_code=202, headers={"Retry-After": "5"})
    return JSONResponse({"bins": BINS, "peaks": peaks}, headers={"Cache-Control": "private, max-age=86400"})
