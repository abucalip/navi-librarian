"""Popularity fill routes (Server V2 Phase 6 item 2, slice 18).

HTTP adapters only: a manual trigger for ``intelligence.taste.popularity_job.run_popularity_fill`` and a
read of its job status. The fill runs only when the owner calls ``POST /api/insights/popularity/fill``;
there is no scheduler and no startup hook. ``max_requests`` comes from an optional JSON body field
(default 5, capped at 20). A process-wide lock refuses a second run while one is in progress (409).

Requests send a descriptive User-Agent and the ListenBrainz token from ``config.env`` in the working
folder (``LISTENBRAINZ_TOKEN``); the token is never logged or returned. The HTTP call is ``httpx.post``,
the client the rest of the server already uses, rather than ``requests.post``: ``requests`` is not a
project dependency, and importing it would break app startup. The call has the same shape the fetch
module expects.
"""
import threading
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values
from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.dependencies import get_librarian
from intelligence.jobs import runner
from intelligence.store import open_store
from intelligence.taste.popularity_job import DEFAULT_MAX_REQUESTS, JOB, run_popularity_fill

router = APIRouter()

STORE_FILE = "intelligence.sqlite3"
CONFIG_FILE = "config.env"
TOKEN_KEY = "LISTENBRAINZ_TOKEN"
MAX_REQUESTS_CAP = 20
USER_AGENT = "Discair/1.0 (personal music discovery; manual ListenBrainz popularity fill)"
_LOCK = threading.Lock()


def _store(librarian):
    return open_store(librarian.DATA_DIR / STORE_FILE)


def _headers() -> dict[str, str]:
    """Request headers: the descriptive User-Agent, plus the ListenBrainz token from config.env when set.

    The token is read from ``config.env`` in the working folder only and is never logged, returned or stored.
    """
    headers = {"User-Agent": USER_AGENT}
    token = (dotenv_values(Path.cwd() / CONFIG_FILE).get(TOKEN_KEY) or "").strip()
    if token:
        headers["Authorization"] = f"Token {token}"
    return headers


def _max_requests(body: dict[str, Any] | None) -> int:
    """The requested batch-request bound: default when absent, capped at 20, 422 when not a positive integer."""
    raw = (body or {}).get("max_requests", DEFAULT_MAX_REQUESTS)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise HTTPException(status_code=422, detail="max_requests must be a positive integer")
    return min(raw, MAX_REQUESTS_CAP)


def _run_body(result: runner.RunResult, max_requests: int) -> dict[str, Any]:
    return {"run_id": result.run_id, "state": result.state, "progress": result.progress,
            "error": result.error, "max_requests": max_requests}


@router.post("/api/insights/popularity/fill")
def fill_popularity(body: dict[str, Any] | None = Body(default=None), librarian=Depends(get_librarian)):
    max_requests = _max_requests(body)
    if not _LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A popularity fill is already running.")
    try:
        db = _store(librarian)
        try:
            result = run_popularity_fill(
                db,
                post=httpx.post,
                headers=_headers(),
                sleep=time.sleep,
                max_requests=max_requests,
            )
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Popularity fill could not run.")
    finally:
        _LOCK.release()
    if result.state == "skipped":
        raise HTTPException(status_code=409, detail="A popularity fill is already running.")
    return _run_body(result, max_requests)


@router.get("/api/insights/popularity/status")
def popularity_status(librarian=Depends(get_librarian)):
    try:
        db = _store(librarian)
        try:
            return {
                "status": runner.status(db, JOB),
                "last_good": runner.last_good(db, JOB),
                "running": _LOCK.locked(),
            }
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read popularity fill status.")
