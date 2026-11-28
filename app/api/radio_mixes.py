"""Authenticated preview, explicit save and download actions for Web radio mixes."""

import sqlite3
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.artist_radio import artist_radio
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from app.api.lb_radio import discovery_mix
from app.api.search import owned_view
from discovery.lb_radio import radio_seed
from discovery.playlist_download import InboxDownloadError
from discovery.radio_mixes import (
    MixActionError, download_preview_track, preview_rows, read_preview, save_preview, store_preview,
)
from discovery.search.index import SongInventoryError
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError

router = APIRouter(prefix="/api/radio-mixes")


class PreviewRequest(BaseModel):
    kind: Literal["artist", "discovery"]
    artist_mbid: UUID | None = None
    tag: str | None = Field(default=None, min_length=1, max_length=80)
    familiarity: Literal["familiar", "explore", "deep_cuts"] = "familiar"
    mode: Literal["easy", "medium", "hard"] = "easy"


def _action(call):
    try:
        return call()
    except (MixActionError, InboxDownloadError) as error:
        raise HTTPException(error.status, detail=str(error)) from error
    except (PlaylistProviderError, SongInventoryError, ValueError, sqlite3.Error, OSError) as error:
        raise HTTPException(503, detail="Could not confirm the mix action. Retry this preview.") from error


@router.post("/preview")
def preview_mix(request: PreviewRequest, response: Response, librarian=Depends(get_librarian)):
    response.headers["Cache-Control"] = "no-store"
    try:
        seed, _ = radio_seed(request.artist_mbid, request.tag)
    except ValueError as error:
        raise HTTPException(422, detail=str(error)) from error
    if request.kind == "artist":
        if request.artist_mbid is None:
            raise HTTPException(422, detail="Artist Radio requires an artist MusicBrainz ID.")
        result = artist_radio(response, artist_mbid=request.artist_mbid,
                              familiarity=request.familiarity, count=40, librarian=librarian)
        result["tracks"] = [{**row, "position": position, "match_state": "owned",
                             "duration_ms": round(row["duration"] * 1000) if row.get("duration") is not None else None}
                            for position, row in enumerate(result["tracks"])]
        result["total_count"] = len(result["tracks"])
        result["owned_count"] = len(result["tracks"]) if result["state"] == "ready" else None
        title = "Discair · Artist Radio · " + request.familiarity.replace("_", " ").title()
    else:
        result = discovery_mix(response, artist_mbid=request.artist_mbid, tag=request.tag,
                               mode=request.mode, librarian=librarian)
        if isinstance(result, JSONResponse):
            return result
        title = "Discair · Discovery Mix · " + (seed["value"] if seed["kind"] == "tag" else "Artist")
    body = {**result, "kind": request.kind, "title": title, "seed": seed}
    if result["state"] != "ready":
        return body
    def store():
        navidrome = PlaylistClient(librarian._navidrome_config())
        return store_preview(librarian.DATA_DIR / STORE_FILE, navidrome, body)
    return {**body, "preview_id": _action(store)}


@router.post("/{preview_id}/save")
def save_mix(response: Response, preview_id: str = Path(pattern=r"^[0-9a-f]{32}$"),
             librarian=Depends(get_librarian)):
    response.headers["Cache-Control"] = "no-store"
    return _action(lambda: save_preview(librarian, librarian.DATA_DIR / STORE_FILE, preview_id))


@router.get("/{preview_id}")
def mix_detail(response: Response, preview_id: str = Path(pattern=r"^[0-9a-f]{32}$"),
               librarian=Depends(get_librarian)):
    response.headers["Cache-Control"] = "no-store"
    def detail():
        preview = read_preview(librarian.DATA_DIR / STORE_FILE,
                               PlaylistClient(librarian._navidrome_config()), preview_id)
        payload = preview["payload"]
        view = owned_view(librarian)
        rows = preview_rows(librarian, preview, view.data)
        return {**payload, "preview_id": preview_id, "tracks": rows, "index_state": view.state,
                "owned_count": sum(bool(row["song_id"]) for row in rows) if view.data is not None else None}
    return _action(detail)


@router.post("/{preview_id}/tracks/{position}/download")
def download_mix_track(response: Response, preview_id: str = Path(pattern=r"^[0-9a-f]{32}$"),
                       position: int = Path(ge=0, le=199), librarian=Depends(get_librarian)):
    response.headers["Cache-Control"] = "no-store"
    return _action(lambda: download_preview_track(librarian, librarian.DATA_DIR / STORE_FILE, preview_id, position))
