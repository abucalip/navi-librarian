"""Runtime diagnostics route (docs/efficiency.md M1).

HTTP adapter only; counters live in ``app.services.runtime_metrics``. Read-only, and behind the same
login as every other ``/api/`` route (``app_login_middleware``). Reports this web process's counters and
the worker's last saved snapshot and each worker schedule entry's last run (``schedule``, efficiency W1) and the owned prefetch's last coverage
counts (``prefetch``, efficiency K3; null until it has run);
no provider call is made.
"""
from fastapi import APIRouter, Depends

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from app import worker_schedule
from app.services import prefetch_state, runtime_metrics
from intelligence.store import open_readonly

router = APIRouter()


@router.get("/api/diagnostics/runtime")
def runtime_diagnostics(librarian=Depends(get_librarian)):
    worker, schedule, prefetch = None, {}, None
    try:
        db = open_readonly(librarian.DATA_DIR / STORE_FILE)
        try:
            worker = runtime_metrics.load_worker_snapshot(db)
            schedule = worker_schedule.last_runs(db)
            prefetch = prefetch_state.read_coverage(db)
        finally:
            db.close()
    except Exception:
        worker, schedule, prefetch = None, {}, None
    return {"web": runtime_metrics.snapshot(), "worker": worker, "schedule": schedule, "prefetch": prefetch}
