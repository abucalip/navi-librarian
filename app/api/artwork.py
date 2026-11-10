"""Album artwork routes (docs/artwork.md, slice 1: server cache and endpoints).

``GET /api/artwork/index?rgid=&release=``: the merged Cover Art Archive index for a MusicBrainz release
group. ``status`` is ``ok``, ``empty``, ``unavailable`` or ``not_loaded`` (a background build is running;
ask again after ``retry_after`` seconds). ``release`` is the owned release MBID (optional): it makes the
owned edition win the slots and protects that album's best front in the cache.

``GET /api/artwork/image/{image_id}?size=thumb|display|full``: cached bytes of one image. The image id
must appear in an index the server has built. Session auth applies (app login middleware); the bytes are
never public. Clients never contact MusicBrainz or the CAA.
"""
import re
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.dependencies import get_librarian
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
        return Response(content=body, media_type=content_type, headers={
            "Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})
    if state == "unavailable":
        raise HTTPException(status_code=503, detail="Artwork is temporarily unavailable.")
    raise HTTPException(status_code=404, detail="No such image.")


def _json(body: dict) -> bytes:
    import json
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
