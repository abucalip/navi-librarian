"""Status of the insight lens refresh (redesign D3, docs/SERVER_V2_CONTRACT.md).

The lens refresh loop (``app/services/insights_refresh.py``) runs two jobs: Forgotten Gems
(``insights_forgotten_gems``) and the provider-backed lenses (``insights_provider_lenses``). This
module reads both and answers one status for "the lens refresh", shaped like the taste one:
``status`` (newest run of either job), ``last_good`` (newest succeeded run of either job),
``running`` and ``retry_after`` (seconds until the loop is next due, 0 = now).

Read-only: it reads ``job_runs`` and never calls a provider, never starts a job and never changes
a card. Run ids are global and increase, so the newest run is the one with the highest id.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Callable

from ..jobs import runner

LENS_JOBS = ("insights_forgotten_gems", "insights_provider_lenses")


def _newest(runs: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    present = [run for run in runs if run is not None]
    return max(present, key=lambda run: run["id"]) if present else None


def lens_refresh_status(
    db: sqlite3.Connection,
    *,
    min_interval: float,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Newest run, last good run, whether one is running, and when the loop is next due (0 = now).

    ``min_interval`` is the loop's cadence in seconds. The next run is due ``min_interval`` after the
    last good run finished; with no good run yet it is due now.
    """
    latest = [runner.status(db, job) for job in LENS_JOBS]
    newest = _newest(latest)
    good = _newest([runner.last_good(db, job) for job in LENS_JOBS])
    running = any(run is not None and run["state"] == "running" for run in latest)
    if good is None or good.get("finished_at") is None:
        retry_after = 0.0
    else:
        retry_after = round(max(0.0, float(good["finished_at"]) + min_interval - clock()), 3)
    return {
        "status": newest,
        "last_good": good,
        "running": running,
        "min_interval": min_interval,
        "retry_after": retry_after,
    }
