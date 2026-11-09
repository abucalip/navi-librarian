"""Taste refresh routes (Server V2 Phase 6 presentation slice 3).

HTTP adapters only; logic is ``intelligence.taste.refresh``. A client calls ``POST /api/insights/taste/refresh``
when the app opens. There is no scheduler and no startup hook. Raw listens come from the owner's ListenBrainz
history (owner decision 2026-11-09), read only after the minimum interval has passed. With no ListenBrainz
username configured the answer is ``no_listens_source`` and nothing is written. A process lock refuses an
overlapping call (409); the persisted job state covers other workers.
"""
import threading

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from intelligence.store import open_store
from intelligence.taste.listenbrainz_listens import listenbrainz_reader
from intelligence.taste.refresh import DEFAULT_MIN_INTERVAL, refresh_status, refresh_taste

router = APIRouter()

STORE_FILE = "intelligence.sqlite3"
_LOCK = threading.Lock()


def listens_source(librarian):
    """A zero-argument reader of the owner's ListenBrainz history, or None without a configured username."""
    import httpx
    from integrations.listenbrainz.client import request_headers

    username = str(librarian._listenbrainz_username() or "").strip()
    if not username:
        return None
    return listenbrainz_reader(username, get=httpx.get, headers=request_headers())


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
