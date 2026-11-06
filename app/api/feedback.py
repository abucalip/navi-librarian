"""Client feedback routes (Server V2 Phase 6 item 5, slice 10, D-027).

HTTP adapters only: ``POST /api/feedback/events`` takes a batch of skip and dismissal events from a
client and stores them in the owner-state file; ``GET /api/insights/suppression`` reads the decaying
view back. Bodies come from ``intelligence.api``. No provider traffic, and the memory is record-only:
no lens, radio, recommendation weight, card or playlist reads it. Event content is never logged.
"""
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_librarian
from intelligence.api import (
    FEEDBACK_DEFAULT_LIMIT, FEEDBACK_MAX_LIMIT, BatchTooLarge, build_intake_body, build_suppression_body,
)
from intelligence.store import open_store

router = APIRouter()

STORE_FILE = "intelligence.sqlite3"
_LOCK = threading.Lock()


class EventBatch(BaseModel):
    events: list[Any]


def _now() -> float:
    return time.time()


def _store(librarian):
    return open_store(librarian.DATA_DIR / STORE_FILE)


@router.post("/api/feedback/events")
def post_events(body: EventBatch, librarian=Depends(get_librarian)):
    now = _now()
    try:
        with _LOCK:
            db = _store(librarian)
            try:
                return build_intake_body(db, body.events, now)
            finally:
                db.close()
    except BatchTooLarge as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not store feedback events.")


@router.get("/api/insights/suppression")
def get_suppression(limit: int = FEEDBACK_DEFAULT_LIMIT, offset: int = 0, librarian=Depends(get_librarian)):
    if not 1 <= limit <= FEEDBACK_MAX_LIMIT:
        raise HTTPException(status_code=400, detail=f"limit must be between 1 and {FEEDBACK_MAX_LIMIT}")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be 0 or more")
    try:
        db = _store(librarian)
        try:
            return build_suppression_body(db, _now(), limit, offset)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read suppression memory.")
