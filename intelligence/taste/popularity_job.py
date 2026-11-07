"""Bounded fill job for sitewide artist popularity (Phase 6 item 2, slice 17).

Reads the owned artists' MBIDs from the knowledge store, asks ListenBrainz for the pending ones
(100 per batch POST, see :mod:`.popularity_fetch`) and saves each batch at once, so a stop or a failure
keeps everything fetched so far and the last good figures of every other artist.

Bounds: at most ``max_requests`` batch requests per run; the job framework's own budget and cancel apply.
A run that stops with MBIDs still pending goes back to ``queued`` and resumes. A transport or HTTP
failure raises, which fails the run and leaves saved figures untouched.

**Unwired:** no route, scheduler or startup path calls :func:`run_popularity_fill`. It makes provider
traffic only when a caller runs it, which stays owner-gated. The caller injects ``post``, headers and
``sleep``; no credentials are read here.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Callable, Mapping

from ..jobs import runner
from .popularity_fetch import POPULARITY_CHUNK_SIZE, fetch_artist_popularity
from .popularity_persistence import owned_artist_mbids, pending_mbids, save_popularity

JOB = "taste_popularity"
DEFAULT_MAX_REQUESTS = 5


def run_popularity_fill(
    db: sqlite3.Connection,
    *,
    post: Callable[..., Any],
    headers: Mapping[str, str],
    sleep: Callable[[float], Any] | None = None,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    clock: Callable[[], float] = time.time,
) -> runner.RunResult:
    def work(ctx: runner.JobContext) -> bool:
        pending = pending_mbids(db, owned_artist_mbids(db), clock())
        requests = filled = absent = 0
        summary = {"requests": 0, "filled": 0, "absent": 0, "pending": len(pending)}
        for start in range(0, len(pending), POPULARITY_CHUNK_SIZE):
            if requests >= max_requests or not ctx.has_budget():
                break
            chunk = pending[start:start + POPULARITY_CHUNK_SIZE]
            figures = fetch_artist_popularity(chunk, post=post, headers=headers, sleep=sleep)
            requests += 1
            save_popularity(db, figures, clock())
            filled += sum(1 for v in figures.values() if v is not None)
            absent += sum(1 for v in figures.values() if v is None)
            summary = {"requests": requests, "filled": filled, "absent": absent,
                       "pending": len(pending) - min(len(pending), start + len(chunk))}
            ctx.checkpoint(summary, items=1)
        ctx.checkpoint(summary)
        return summary["pending"] == 0

    return runner.run_job(db, JOB, work, clock=clock)
