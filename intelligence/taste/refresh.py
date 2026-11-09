"""Refresh of the saved taste profiles (Phase 6 presentation slice 3).

A client calls the refresh when the app opens. This module recomputes the profiles from listens the
caller supplies, saves them, and says what happened. It makes no provider call itself: ``read_listens``
is injected and returns raw ListenBrainz-shaped listens. Guards:

* **Minimum interval:** a refresh within ``min_interval`` seconds of the last successful one answers
  ``too_soon`` without reading listens. Failed attempts do not start the interval.
* **Overlap lock:** the job runner allows one queued or running ``taste_refresh`` run; a second caller
  gets ``skipped``. A run left ``running`` by a crash is returned to the queue after ``STALE_AFTER``.
* **Idempotent:** the windows end at the start of the current UTC day (the payload carries ``config.now``), and an unchanged payload writes nothing and keeps ``data_version`` (``changed`` is False).

Profiles change no recommendation weight and no ownership flag.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from ..jobs import runner
from .loader import load_listens
from .persistence import save_profiles
from .profiles import ProfileConfig, build_profiles

JOB = "taste_refresh"
DEFAULT_MIN_INTERVAL = 3600.0
STALE_AFTER = 900.0
DAY = 86400.0


@dataclass(frozen=True)
class RefreshResult:
    state: str                  # refreshed, unchanged, too_soon, skipped, failed
    run_id: int | None = None
    changed: bool = False
    retry_after: float = 0.0    # seconds until another refresh is allowed (too_soon)
    progress: Mapping[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"state": self.state, "run_id": self.run_id, "changed": self.changed,
                "retry_after": self.retry_after, "progress": dict(self.progress or {}), "error": self.error}


def _next_allowed(db: sqlite3.Connection, min_interval: float) -> float | None:
    good = runner.last_good(db, JOB)
    if good is None or good.get("finished_at") is None:
        return None
    return float(good["finished_at"]) + min_interval


def refresh_taste(
    db: sqlite3.Connection,
    *,
    read_listens: Callable[[], Iterable[Mapping[str, Any]]],
    genres_by_recording: Mapping[str, Iterable[str]] | None = None,
    config: ProfileConfig | None = None,
    min_interval: float = DEFAULT_MIN_INTERVAL,
    clock: Callable[[], float] = time.time,
) -> RefreshResult:
    now = clock()
    runner.recover_stale(db, now, STALE_AFTER)
    allowed = _next_allowed(db, min_interval)
    if allowed is not None and now < allowed:
        return RefreshResult("too_soon", retry_after=round(allowed - now, 3))

    def work(ctx: runner.JobContext) -> bool:
        loaded = load_listens(db, read_listens(), genres_by_recording=genres_by_recording)
        base = config or ProfileConfig()
        day_start = now - now % DAY   # windows move by whole days, so a same-day replay is byte-identical
        profiles = build_profiles(loaded.listens, ProfileConfig(**{**base.__dict__, "now": day_start}))
        changed = save_profiles(db, profiles, loaded, now=now)
        ctx.checkpoint({"changed": changed, "listens": loaded.total, "unusable": loaded.unusable,
                        "unmatched": loaded.unmatched}, items=1)
        return True

    result = runner.run_job(db, JOB, work, clock=clock)
    if result.state == "skipped":
        return RefreshResult("skipped", result.run_id, progress=result.progress)
    if result.state == "failed":
        return RefreshResult("failed", result.run_id, progress=result.progress, error=result.error)
    changed = bool(result.progress.get("changed"))
    return RefreshResult("refreshed" if changed else "unchanged", result.run_id, changed, 0.0, result.progress)


def refresh_status(db: sqlite3.Connection, *, min_interval: float = DEFAULT_MIN_INTERVAL,
                   clock: Callable[[], float] = time.time) -> dict[str, Any]:
    """Newest run, last good run, whether one is running, and when the next refresh is allowed (0 = now)."""
    newest = runner.status(db, JOB)
    allowed = _next_allowed(db, min_interval)
    return {
        "status": newest,
        "last_good": runner.last_good(db, JOB),
        "running": bool(newest and newest["state"] == "running"),
        "min_interval": min_interval,
        "retry_after": round(max(0.0, allowed - clock()), 3) if allowed is not None else 0.0,
    }
