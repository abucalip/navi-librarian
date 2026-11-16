"""Runtime diagnostics route (docs/efficiency.md M1).

HTTP adapter only; counters live in ``app.services.runtime_metrics``. Read-only, and behind the same
login as every other ``/api/`` route (``app_login_middleware``). Reports this web process's counters and
the worker's last saved snapshot; no provider call is made.
"""
from fastapi import APIRouter, Depends

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from app.services import runtime_metrics
from intelligence.store import open_readonly

router = APIRouter()


@router.get("/api/diagnostics/runtime")
def runtime_diagnostics(librarian=Depends(get_librarian)):
    worker = None
    try:
        db = open_readonly(librarian.DATA_DIR / STORE_FILE)
        try:
            worker = runtime_metrics.load_worker_snapshot(db)
        finally:
            db.close()
    except Exception:
        worker = None
    return {"web": runtime_metrics.snapshot(), "worker": worker}
