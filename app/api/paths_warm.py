"""Manual path cache warm-up routes (Server V2 Phase 7 carry-over).

HTTP adapters for ``intelligence.graph.paths_warm.run_paths_warm`` and a read of its job status. The warm-up
runs only when the owner calls ``POST /api/knowledge/paths/warm``; no scheduler, no startup hook, no provider
traffic. Optional JSON body: ``max_seconds`` (default 300, cap 1800) and ``kinds`` (default all). A
process-wide lock refuses a second run while one is in progress (409). A run that stops early answers
``state: "queued"`` and the next call resumes it.
"""
import threading
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.graph.paths import PATH_KINDS
from intelligence.graph.paths_warm import DEFAULT_MAX_SECONDS, JOB, run_paths_warm
from intelligence.jobs import runner
from intelligence.store import open_store

router = APIRouter()

MAX_SECONDS_CAP = 1800.0
_LOCK = threading.Lock()


def _body_args(body: dict[str, Any] | None) -> tuple[float, tuple[str, ...]]:
    body = body or {}
    seconds = body.get("max_seconds", DEFAULT_MAX_SECONDS)
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds <= 0:
        raise HTTPException(status_code=422, detail="max_seconds must be a positive number")
    kinds = body.get("kinds", list(PATH_KINDS))
    if not isinstance(kinds, list) or not kinds or any(k not in PATH_KINDS for k in kinds):
        raise HTTPException(status_code=422, detail=f"kinds must be a non-empty list of: {', '.join(PATH_KINDS)}")
    return min(float(seconds), MAX_SECONDS_CAP), tuple(dict.fromkeys(kinds))


@router.post("/api/knowledge/paths/warm")
def warm_paths(body: dict[str, Any] | None = Body(default=None), librarian=Depends(get_librarian)):
    max_seconds, kinds = _body_args(body)
    if not _LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A path warm-up is already running.")
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            result = run_paths_warm(db, kinds=kinds, max_seconds=max_seconds)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Path warm-up could not run.")
    finally:
        _LOCK.release()
    if result.state == "skipped":
        raise HTTPException(status_code=409, detail="A path warm-up is already running.")
    return {"run_id": result.run_id, "state": result.state, "progress": result.progress, "error": result.error,
            "max_seconds": max_seconds, "kinds": list(kinds)}


@router.get("/api/knowledge/paths/warm/status")
def warm_status(librarian=Depends(get_librarian)):
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            status = runner.status(db, JOB)
            return {"status": status, "last_good": runner.last_good(db, JOB),
                    "running": bool(status and status["state"] == "running")}
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read path warm-up status.")
