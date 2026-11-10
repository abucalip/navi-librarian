"""Manual "Request update" routes: ask the worker to add one artist or album to the knowledge store.

``POST /api/knowledge/update-store`` records a request (the worker does the work); ``GET`` reads its state.
Both take ``subject`` (artist|album) and the Navidrome ``navidrome_id``.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.musicbrainz import update_requests
from intelligence.store import open_store

router = APIRouter()


def _key(body: dict) -> str:
    """The request key: the Navidrome id, or ``mbid:<id>`` for an artist known only by MusicBrainz id."""
    nid, mbid = body.get("navidrome_id"), body.get("mbid")
    if isinstance(nid, str) and nid:
        return nid
    if isinstance(mbid, str) and mbid:
        return update_requests.MBID_PREFIX + mbid.strip().lower()
    raise HTTPException(status_code=422, detail="give navidrome_id or mbid")


def _with_store(librarian, call):
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            return call(db)
        finally:
            db.close()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not use the knowledge store.")


@router.post("/api/knowledge/update-store")
def request_update(body: dict = Body(...), librarian=Depends(get_librarian)):
    return _with_store(librarian, lambda db: update_requests.enqueue(db, str(body.get("subject")), _key(body)))


@router.get("/api/knowledge/update-store")
def update_status(subject: str = Query(...), navidrome_id: str | None = None, mbid: str | None = None,
                  librarian=Depends(get_librarian)):
    key = _key({"navidrome_id": navidrome_id, "mbid": mbid})
    result = _with_store(librarian, lambda db: update_requests.status(db, subject, key))
    return result or {"state": "none"}
