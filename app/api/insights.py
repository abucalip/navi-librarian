"""Insight card routes (Server V2 Phase 3, docs/SERVER_V2_CONTRACT.md).

HTTP adapters only: bodies come from ``intelligence.api.build_insights_body`` and the dismiss,
restore and accept actions are the existing service functions in ``intelligence.insights``.
Reads and writes touch only the dedicated Server V2 SQLite file (D-026); no provider traffic,
no ownership flags, no recommendation weights. A lens returns cards only when listed in the
``NAVI_INSIGHT_LENSES`` environment variable (comma separated lens kinds); none is on by default
because no lens scorecard verdict is ``pass`` yet.
"""
import os
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_librarian
from intelligence.api import INSIGHTS_DEFAULT_LIMIT, INSIGHTS_MAX_LIMIT, build_insights_body
from intelligence.insights import (
    accept_card, dismiss_anniversary, dismiss_blind_spot, dismiss_canon, dismiss_gem, dismiss_series,
    restore_anniversary, restore_blind_spot, restore_canon, restore_gem, restore_series, unaccept_card,
)
from intelligence.insights.anniversaries import CARD_KIND as ANNIVERSARY_KIND
from intelligence.insights.blind_spots import CARD_KIND as BLIND_SPOT_KIND
from intelligence.insights.forgotten_gems import CARD_KIND as GEM_KIND
from intelligence.insights.hidden_canon import CARD_KIND as CANON_KIND
from intelligence.insights.series_completion import CARD_KIND as SERIES_KIND
from intelligence.store import open_store

router = APIRouter()

STORE_FILE = "intelligence.sqlite3"
LENSES_ENV = "NAVI_INSIGHT_LENSES"

def _set_key(key):
    """Blind-spot card keys are ``blind_spot:<set key>``; the service functions add that prefix themselves."""
    return key[len(BLIND_SPOT_KIND) + 1:] if key.startswith(BLIND_SPOT_KIND + ":") else key


_ACTIONS = {
    GEM_KIND: (dismiss_gem, restore_gem),
    BLIND_SPOT_KIND: (lambda db, key: dismiss_blind_spot(db, _set_key(key)),
                      lambda db, key: restore_blind_spot(db, _set_key(key))),
    SERIES_KIND: (dismiss_series, restore_series),
    CANON_KIND: (dismiss_canon, restore_canon),
    ANNIVERSARY_KIND: (dismiss_anniversary, restore_anniversary),
}
_LOCK = threading.Lock()


class CardKey(BaseModel):
    key: str


def enabled_lenses(environ=None):
    """Lens kinds the owner switched on; unknown names are ignored by the body builder."""
    raw = (os.environ if environ is None else environ).get(LENSES_ENV, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _store(librarian):
    return open_store(librarian.DATA_DIR / STORE_FILE)


def _kind(kind):
    if kind not in _ACTIONS:
        raise HTTPException(status_code=404, detail="Unknown insight kind.")
    return kind


@router.get("/api/insights")
def insights(limit: int = INSIGHTS_DEFAULT_LIMIT, librarian=Depends(get_librarian)):
    if not 1 <= limit <= INSIGHTS_MAX_LIMIT:
        raise HTTPException(status_code=400, detail=f"limit must be between 1 and {INSIGHTS_MAX_LIMIT}")
    try:
        db = _store(librarian)
        try:
            return build_insights_body(db, enabled=enabled_lenses(), limit=limit)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read insights.")


def _change(librarian, kind, action):
    try:
        with _LOCK:
            db = _store(librarian)
            try:
                return {"changed": bool(action(db))}
            finally:
                db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not update insights.")


@router.post("/api/insights/{kind}/dismiss")
def dismiss(kind: str, body: CardKey, librarian=Depends(get_librarian)):
    fn = _ACTIONS[_kind(kind)][0]
    return _change(librarian, kind, lambda db: fn(db, body.key))


@router.post("/api/insights/{kind}/restore")
def restore(kind: str, body: CardKey, librarian=Depends(get_librarian)):
    fn = _ACTIONS[_kind(kind)][1]
    return _change(librarian, kind, lambda db: fn(db, body.key))


@router.post("/api/insights/{kind}/accept")
def accept(kind: str, body: CardKey, librarian=Depends(get_librarian)):
    return _change(librarian, _kind(kind), lambda db: accept_card(db, kind, body.key))


@router.post("/api/insights/{kind}/unaccept")
def unaccept(kind: str, body: CardKey, librarian=Depends(get_librarian)):
    return _change(librarian, _kind(kind), lambda db: unaccept_card(db, kind, body.key))
