"""Album artwork routes (docs/artwork.md, slice 1: server cache and endpoints).

``GET /api/artwork/index?rgid=&release=``: the merged Cover Art Archive index for a MusicBrainz release
group. ``status`` is ``ok``, ``empty``, ``unavailable`` or ``not_loaded`` (a background build is running;
ask again after ``retry_after`` seconds). ``release`` is the owned release MBID (optional): it makes the
owned edition win the slots and protects that album's best front in the cache.

``GET /api/artwork/image/{image_id}?size=thumb|display|full``: cached bytes of one image (JPEG, PNG, GIF, WebP, or a PDF original with ``size=full``). The image id
must appear in an index the server has built. Session auth applies (app login middleware); the bytes are
never public. Clients never contact MusicBrainz or the CAA.
"""
import re
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from fastapi.responses import Response

from app.api.dependencies import get_librarian
from intelligence.artwork import cover
from intelligence.artwork.fetchers import ArtworkFetchers
from intelligence.artwork.service import ArtworkService
from intelligence.artwork.store import SIZES, ArtworkStore

router = APIRouter()

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
RETRY_AFTER_SECONDS = 5
_SERVICES: dict[str, ArtworkService] = {}
_LOCK = threading.Lock()


def get_service(librarian=Depends(get_librarian)) -> ArtworkService:
    root = str(librarian.DATA_DIR / "artwork")
    with _LOCK:
        if root not in _SERVICES:
            _SERVICES[root] = ArtworkService(ArtworkStore(librarian.DATA_DIR / "artwork"), ArtworkFetchers())
        return _SERVICES[root]


@router.get("/api/artwork/index")
def artwork_index(rgid: str = Query(...), release: str | None = None, service: ArtworkService = Depends(get_service)):
    if not _UUID.fullmatch(rgid):
        raise HTTPException(status_code=400, detail="rgid must be a MusicBrainz release group id.")
    if release is not None and not _UUID.fullmatch(release):
        raise HTTPException(status_code=400, detail="release must be a MusicBrainz release id.")
    body = service.index(rgid.lower(), release)
    if body["status"] == "not_loaded":
        body["retry_after"] = RETRY_AFTER_SECONDS
    return Response(content=_json(body), media_type="application/json", headers={"Cache-Control": "no-store"})


@router.get("/api/artwork/image/{image_id}")
def artwork_image(image_id: int, size: str = Query("display"), service: ArtworkService = Depends(get_service)):
    if size not in SIZES:
        raise HTTPException(status_code=400, detail="size must be thumb, display or full.")
    if image_id <= 0:
        raise HTTPException(status_code=400, detail="image id is not valid.")
    state, body, content_type = service.image(image_id, size)
    if state == "ok":
        headers = {"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"}
        if content_type == "application/pdf":      # third-party PDF: never let a browser run it with our origin
            headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return Response(content=body, media_type=content_type, headers=headers)
    if state == "unavailable":
        raise HTTPException(status_code=503, detail="Artwork is temporarily unavailable.")
    raise HTTPException(status_code=404, detail="No such image.")


class ChoiceBody(BaseModel):
    rgid: str
    image_id: int


_ALBUM_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


@router.get("/api/artwork/choices")
def artwork_choices(service: ArtworkService = Depends(get_service)):
    """Every owner pick, ``{album_id: image_id}``, for clients that load library covers themselves."""
    return Response(content=_json({"choices": service.store.all_choices()}), media_type="application/json",
                    headers={"Cache-Control": "no-store"})


@router.put("/api/artwork/choice/{album_id}")
def set_choice(album_id: str, body: ChoiceBody, service: ArtworkService = Depends(get_service)):
    """The owner's cover pick for an owned album. The image must be a Front image of the album's release group."""
    if not _ALBUM_ID.fullmatch(album_id) or not _UUID.fullmatch(body.rgid) or body.image_id <= 0:
        raise HTTPException(status_code=400, detail="album id, rgid or image id is not valid.")
    outcome = cover.choose(service, album_id, body.rgid.lower(), body.image_id)
    if outcome == "not_loaded":
        raise HTTPException(status_code=409, detail="The artwork index is not built yet; try again shortly.")
    if outcome != "ok":
        raise HTTPException(status_code=404, detail="That image is not a front cover of this album.")
    return {"album_id": album_id, "image_id": body.image_id}


@router.delete("/api/artwork/choice/{album_id}")
def clear_choice(album_id: str, service: ArtworkService = Depends(get_service)):
    if not _ALBUM_ID.fullmatch(album_id):
        raise HTTPException(status_code=400, detail="album id is not valid.")
    service.store.clear_choice(album_id)
    return {"album_id": album_id, "image_id": None}


def _json(body: dict) -> bytes:
    import json
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
