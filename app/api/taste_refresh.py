"""Taste refresh routes (Server V2 Phase 6 presentation slice 3).

HTTP adapters only; logic is ``intelligence.taste.refresh``. A client calls ``POST /api/insights/taste/refresh``
when the app opens. There is no scheduler and no startup hook, and the route makes no provider call: raw
listens come from ``listens_source(librarian)``, which returns a reader of already-held listens, or ``None``
when the server holds none (the answer is then ``no_listens_source`` and nothing is written). A process
lock refuses an overlapping call (409); the persisted job state covers other workers.
"""
import threading

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from intelligence.store import open_store
from intelligence.taste.refresh import DEFAULT_MIN_INTERVAL, refresh_status, refresh_taste

router = APIRouter()

STORE_FILE = "intelligence.sqlite3"
_LOCK = threading.Lock()


def listens_source(librarian):
    """A zero-argument reader of raw listens held locally, or None. No local listen store exists yet."""
    return None


def _store(librarian):
    return open_store(librarian.DATA_DIR / STORE_FILE)


@router.post("/api/insights/taste/refresh")
def refresh(librarian=Depends(get_librarian)):
    if not _LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A taste refresh is already running.")
    try:
        read = listens_source(librarian)
        if read is None:
            return {"state": "no_listens_source", "run_id": None, "changed": False,
                    "retry_after": 0.0, "progress": {}, "error": None}
        db = _store(librarian)
        try:
            result = refresh_taste(db, read_listens=read, min_interval=DEFAULT_MIN_INTERVAL)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Taste refresh could not run.")
    finally:
        _LOCK.release()
    if result.state == "skipped":
        raise HTTPException(status_code=409, detail="A taste refresh is already running.")
    return result.as_dict()


@router.get("/api/insights/taste/refresh/status")
def refresh_state(librarian=Depends(get_librarian)):
    try:
        db = _store(librarian)
        try:
            return refresh_status(db)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read taste refresh status.")
