"""Insight lens refresh status route (redesign D3, docs/SERVER_V2_CONTRACT.md).

HTTP adapter only; logic is ``intelligence.insights.refresh_status``. Read-only: no provider call and
no job is started. The loop cadence (``CHECK_SECONDS`` in ``app/services/insights_refresh.py``) is the
``min_interval`` the answer reports.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from app.services.insights_refresh import CHECK_SECONDS
from intelligence.insights.refresh_status import lens_refresh_status
from intelligence.store import open_store

router = APIRouter()


@router.get("/api/insights/refresh/status")
def insights_refresh_state(librarian=Depends(get_librarian)):
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            return lens_refresh_status(db, min_interval=CHECK_SECONDS)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read insight refresh status.")
